from pathlib import Path
import requests
from datetime import datetime
import json
import pandas as pd
import procyclingstats

from .constants import DATA_DIR
from .urls import make_pcs_url, infer_name_edition_stage
from .Image import Image, tag_stage_imgs
from .parse_cs import parse_cs_stage_html
from .get_resources import get_resource


class Stage:

    def __init__(self, cs_url, race_dpath=None):
        """

        Wrapper for cs and pcs data using passed cs_url and race dpath
        >>> st = Stage(<cyclinstage cs_url>, '../dauphine_2025')

        cs_url is required, as this is not easily inferred.
        race, edition, pcs_url and race_dpath inferred from it

        has all attrs for describing and drawing the stage
        >>> st.distance
        >>> st.type
        >>> st.climbs_df

        Caches cs html and pcs jsons (so all the rest parsed on fly)
        Instantiates Image objects which do similar with the image files

        Tags image urls as 'profile', 'route', 'other'
        """
        # main input parameter and source for cs data
        self._cs_url = cs_url

        # infer main things from the cs_url
        deets = infer_name_edition_stage(cs_url)
        self._name, self._edition, self.stage_no = deets
        self._race = f"{self._name}_{self._edition}"
        self._stage_int = int(self.stage_no) - 1

        # pcs source urls
        self._pcs_url = make_pcs_url(
            self._race, kind='stage', stage_no=self.stage_no)
        self._pcs_data_url = make_pcs_url(self._race, 'stage', self.stage_no)
        self._pcs_img_urls_source_url = make_pcs_url(
            self._race, 'stage_resources', self.stage_no)

        # paths
        if race_dpath is None:
            race_dpath = DATA_DIR / f"{self._name}_{self._edition}"

        self.dpath = Path(race_dpath) / f"stage_{self.stage_no}"

        if not self.dpath.exists():
            self.dpath.mkdir()

        # DATA MODEL
        # xresources
        # the cs source html (file hidden)
        self._cs_html = get_resource(
            url=self._cs_url,
            fpath=self.dpath / '.cs.html',
            parser='html',
        )

        # the main pcs Stage api data (file hidden)
        self._pcs_data = get_resource(
            url=self._pcs_data_url,
            fpath=self.dpath / '.pcs_data.json',
            parser='pcs_stage_api',
        )

        # pcs img urls (file hidden - see tagged version on disk)
        self._pcs_img_urls = get_resource(
            url=self._pcs_img_urls_source_url,
            fpath=self.dpath / '.pcs_img_urls.json',
            parser='pcs_stage_img_urls',
        )

        # processing
        self._cs_data = parse_cs_stage_html(self._cs_html)
        self._pcs_img_urls_tags = self._tag_imgs('pcs')
        self._cs_img_urls_tags = self._tag_imgs('cs')
        self.cs_imgs = self._get_cs_imgs()
        self.pcs_imgs = self._get_pcs_imgs()

        # # public stuff
        self.departure = self._pcs_data.get('departure')
        self.arrival = self._pcs_data.get('arrival')
        self.date = self._pcs_data.get('date')
        if self.date is not None:
            self.dt = datetime.strptime(self.date, "%Y-%m-%d")
        else:
            self.dt = None
        self.distance = self._pcs_data.get('distance')
        self.type = self._pcs_data.get('stage_type')  # 'RR'/ 'ITT'/'TTT'
        self.vertical_meters = self._pcs_data.get('vertical_meters')
        self.profile_icon = self._pcs_data.get('profile_icon')
        self.start_time = self._pcs_data.get('start_time')
        self.climbs_df = self._get_climbs_df()
        self.climbs = self.climbs_df.T.to_dict()
        self.description = self._cs_data.get('description')
        self.blurb = self._cs_data.get('blurb')

    def _get_climbs_df(self):
        """
        Get the race climbs from race dir
        """

        if not self._pcs_data.get('climbs'):
            return pd.DataFrame()

        # need to load the full detailed climbs from race dir above
        race_climbs_fp = self.dpath.parent / '.pcs_race_climbs.json'

        if not race_climbs_fp.exists():
            print('cannot find a parent directory with pcs climb details')
            return pd.DataFrame()

        with open(race_climbs_fp, 'r') as fp:
            race_climbs = json.load(fp)

        out = []

        # go through the stage climbs (less detailed)
        for stage_climb in self._pcs_data['climbs']:

            # use the climb url as key to get its detail
            records = [x for x in race_climbs
                       if x['climb_url'] ==  stage_climb['climb_url']]
            out.extend(records)

        df = pd.DataFrame(out)
        df.columns = ['name', 'url', 'length_km',
                      'perc', 'alt_m', 'km_to_go']
        df['start_km_to_go'] = df['km_to_go'] + df['length_km']
        df['km'] = self.distance - df['km_to_go']
        df['start_km'] = df['km'] - df['length_km']
        df = df.set_index('km_to_go').drop('url', axis=1)
        df = df.sort_index(ascending=False)

        return df

    def _get_pcs_imgs(self):
        """
        Return a list of Image objects made from urls in data
        """
        download_dir = self.dpath / 'pcs_imgs'

        if not download_dir.exists():
            download_dir.mkdir()

        out = []
        for img in self._pcs_img_urls_tags:
            out.append(Image(img['url'], download_dir, img['tag']))

        return out

    def _tag_imgs(self, source):
        """
        Useful to have these separate from rest of cs_data,
        so can edit on disk.  The imgs are created from this, not
        cs_data

        Source is cs or pcs
        """
        
        fpath = self.dpath / f'{source}_img_urls_tags.json'
        
        if not fpath.exists():
            if source == 'cs':
                data = tag_stage_imgs(self._cs_data['img_urls'])
            elif source == 'pcs':
                with open(self.dpath.parent
                          / '.pcs_profile_img_urls.json', 'r') as fp:
                    pcs_profile_urls = json.load(fp)

                profile_url = pcs_profile_urls[self._stage_int]

                data = tag_stage_imgs(self._pcs_img_urls, profile_url)

            with open(fpath, 'w') as fp:
                json.dump(data, fp, indent=4)

        else:
            with open(fpath, 'r') as fp:
                data = json.load(fp)

        return data

    def _get_cs_imgs(self):
        """
        Return a list of Image objects made from urls in cs data
        """
        data = self._cs_img_urls_tags
        download_dir = self.dpath / 'cs_imgs'

        if not download_dir.exists():
            download_dir.mkdir()

        return [Image(img['url'], download_dir, img['tag'])
                for img in data]
    
    def check(self):
        """
        cs and pcs data (how much?)
        imgs - profile and route
        climbs
        gc?
        """
        pass

    def make_pdf(self, pages=2):
        """
        Page 1:
            title (incl some info eg date, dist, type, climbs, elev)
            profile img
            climbs table
            route img
            blurb
        Page 1:
            other imgs
        """
        pass

    def __repr__(self):
        return f"Stage('{self._cs_url}')"
