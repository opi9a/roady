from pathlib import Path
import requests
from datetime import datetime
import json
import pandas as pd
import procyclingstats

from .constants import DATA_DIR, LOG
from .urls import make_cs_url, make_pcs_url 
from .Image import Image, tag_stage_imgs
from .parse_cs import parse_cs_stage_html
from .get_resources import get_resource
from .get_gc import get_stage_gc, print_stage_gc


class Stage:

    def __init__(self, race, stage_no, race_dpath=None, check=False,
                 get_gc=False):
        """

        Wrapper for cs and pcs data using passed race, number and optional dpath
        >>> st = Stage('dauphine_2025', 3, '../dauphine_2025')

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

        # infer main things from the cs_url
        self._name, self._edition = race.split('_')
        self.stage_no = str(stage_no)
        self._race = f"{self._name}_{self._edition}"
        self._stage_ind = stage_no - 1

        # source urls
        self._pcs_url = make_pcs_url(
            self._race, kind='stage', stage_no=self.stage_no)
        self._pcs_data_url = make_pcs_url(
            self._race, 'stage', self.stage_no)
        self._pcs_img_urls_source_url = make_pcs_url(
            self._race, 'stage_resources', self.stage_no)

        self._cs_url = make_cs_url(race, stage_no)

        # paths
        if race_dpath is None:
            race_dpath = DATA_DIR / f"{race}"

        self.dpath = Path(race_dpath) / f"stage_{self.stage_no}"

        if not self.dpath.exists():
            self.dpath.mkdir()

        # external resources
        self._cs_html = None
        self._cs_data = None
        self._pcs_data = None
        self._pcs_img_urls = None
        self._load()  # the function that assigns to attrs above

        # processing
        # NB these are 'make' or 'tag' functions
        self._img_urls_tags = None
        self.data = None
        self.climbs_df = None
        self._process()

        # probably most important: profile and route imgs
        # can edit img_urls_tags.json to get these right,
        # and call self.imgs() directly
        _ = self.imgs()

        if check:
            self.check()

    def _load(self, update=False):
        self._cs_html = get_resource(
            url=self._cs_url,
            fpath=self.dpath / '.cs.html',
            parser='html',
            update=update
        )

        # handy to finish parsing cs_html right now, so 
        if (self.dpath / '.cs_data.json').exists():
            with open(self.dpath / '.cs_data.json', 'r') as fp:
                self._cs_data = json.load(fp)
        else:
            self._cs_data = parse_cs_stage_html(self._cs_html)
            with open(self.dpath / '.cs_data.json', 'w') as fp:
                json.dump(self._cs_data, fp, indent=4)

        # the main pcs Stage api data (file hidden)
        # note this is
        self._pcs_data = get_resource(
            url=self._pcs_data_url,
            fpath=self.dpath / '.pcs_data.json',
            parser='pcs_stage_api',
            update=update
        )

        # pcs img urls (file hidden - see tagged version on disk)
        self._pcs_img_urls = get_resource(
            url=self._pcs_img_urls_source_url,
            fpath=self.dpath / '.pcs_img_urls.json',
            parser='pcs_stage_img_urls',
            update=update
        )

    def _process(self):
        self._img_urls_tags = tag_imgs(self)
        self.data = self._make_data()
        self.climbs_df = self.make_climbs_df()


    def _make_data(self):
        """
        Bring together info from cs and pcs
        """

        out = self._pcs_data

        out['description'] = self._cs_data.get('description')
        out['blurb'] = self._cs_data.get('blurb')

        if out['date'] is not None:
            out['dt'] = datetime.strptime(out['date'], "%Y-%m-%d").date()
        else:
            out['dt'] = None

        out['cs_date'] = self._cs_data.get('date')
        out['from_to'] = self._cs_data.get('from_to')
        out['cs_parsed_distance'] = self._cs_data.get('parsed_distance')

        return out

    def imgs(self):
        """
        Return dict of Images for cs and pcs profile and route,
        based on their tags in img_urls_tags.json

        Go through self._img_urls_tags and just assign
        """
        out = {
            'pcs': {'profile': None, 'route': None, 'others': []},
            'cs': {'profile': None, 'route': None, 'others': []},
        }

        for source, imgs in self._img_urls_tags.items():

            dpath = self.dpath / f"{source}_imgs"
            if not dpath.exists():
                dpath.mkdir()

            if imgs is None:
                continue

            for img in imgs:
                if img['tag'] == 'profile':
                    if out[source]['profile'] is not None:
                        print('two profiles found')
                    out[source]['profile'] = Image(
                        img['url'], dpath, tag='profile')
                elif img['tag'] == 'route':
                    if out[source]['route'] is not None:
                        print('two routes found')
                    out[source]['route'] = Image(
                        img['url'], dpath, tag='route')
                elif img['tag'] == 'other':
                    out[source]['others'].append(
                        Image(img['url'], dpath, tag='other'))

            if out[source]['profile'] is None:
                LOG.info(f'no {source} profile for stage, {self.stage_no}')

            if out[source]['route'] is None:
                LOG.info(f'no {source} route for stage, {self.stage_no}')

        # SOMTHING WAS MISSING HERE
        # incl make_climbs_df declaration

        return out

    def _get_climbs_df(self):
        """
        Get the race climbs from race dir
        """

        if not self._pcs_data.get('climbs'):
            return pd.DataFrame()

        # need to load the full detailed climbs from race dir above
        race_climbs_fp = self.dpath.parent / '.pcs_race_climbs.json'


        if out[source]_fp.exists():
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
            if not records:
                print('cannot find', stage_climb['climb_name'],
                      'in race climbs')
            out.extend(records)

        if not out:
            return pd.DataFrame()

        df = pd.DataFrame(out)
        df.columns = ['name', 'url', 'length_km',
                      'perc', 'alt_m', 'km_to_go']
        df['start_km_to_go'] = df['km_to_go'] + df['length_km']
        df['km'] = self.data['distance'] - df['km_to_go']
        df['start_km'] = df['km'] - df['length_km']
        df = df.set_index('km_to_go').drop('url', axis=1)
        df = df.sort_index(ascending=False)

        return df

    def _make_pcs_imgs(self):
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

    def _make_cs_imgs(self):
        """
        Return a list of Image objects made from urls in cs data
        """
        data = self._cs_img_urls_tags
        download_dir = self.dpath / 'cs_imgs'

        if not download_dir.exists():
            download_dir.mkdir()

        return [Image(img['url'], download_dir, img['tag'])
                for img in data]
    
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
        print('not yet implemented')

    def get_gc_df(self, make_pdf=False):
        """
        Return a df of the gc for BEFORE the stage
        """
        df = get_stage_gc(self.stage_no, self._race)

        if make_pdf:
            print_stage_gc(self.stage_no, self._race, df=df)

        return df

    def check(self, verbose=False):
        """
        cs and pcs data (how much?)
        imgs - profile and route
        climbs
        gc?
        """
        pad = 20

        print(f'Stage {self.stage_no.rjust(2)}:', end=" ")

        out = []
        for param in [
            'date', 'departure', 'arrival', 'distance', 'stage_type',
            'vertical_meters', 'description', 'blurb'
        ]:

            x = self.data.get(param)

            if x is None:
                out.append(f" {param.ljust(pad)} : X")
            elif verbose:
                out.append(f" {param}".ljust(pad), ": ok")

        # images
        imgs = self.imgs()

        for source, tags in imgs.items():
            for tag, data in tags.items():
                if tag == 'others':
                    continue
                else:
                    img = data
                if img is None or 'http' not in img.url:
                    out.append("".join([f" {source}/{tag} url".ljust(pad), ": X"]))
                elif verbose:
                    out.append(f" {source}/{tag} url".ljust(pad), ": ok")

        if len(out) == 0:
            print('OK')
        else:
            print()
            for err in out:
                print(err)
            print()


    def series(self):
        """
        Key data in a pd.Series
        """
        out = {
            k: self.data[k] for k in
            ['dt', 'departure', 'arrival', 'distance',
                  'stage_type', 'vertical_meters']
        }
        out['no_climbs'] = len(self.climbs_df)

        if len(self.climbs_df):
            out['summit_finish'] = self.climbs_df.index[-1] < 5
        else:
            out['summit_finish'] = False

        return pd.Series(out, name=int(self.stage_no))

    def update(self):
        """
        """
        self._load(update=True)
        self._process
        # imgs too??


    def __repr__(self):
        return f"Stage('{self._cs_url}')"


def tag_imgs(stage):
    """
    # unify image tagging, single json with a list of urls
      for each source.  each url has a tag that can be modified
      manually in case of problems

    # then have stage.imgs() return them all in a dict with
      fields for pcs/cs, then profile, route, others =[]

    Returns a list of {'url': url, 'tag': tag} dicts from disk,
    or making it from the raw urls, for each source.

    TODO
    If a stage is missing an image tagged as profile or route,
    can go into the disk files (img_urls_tags.json) and
    assign manually.
    """
    self = stage  # while in dev

    fpath = self.dpath / 'img_urls_tags.json'

    # if json is on disk, just return it
    if fpath.exists():
        with open(fpath, 'r') as fp:
            out = json.load(fp)
        return out

    # making it
    out = {
        'cs': None,
        'pcs': None
    }

    # cs is easy..
    out['cs'] = tag_stage_imgs(self._cs_data['img_urls'])

    # for pcs want to use the parent race list of profile urls
    with open(self.dpath.parent
              / '.pcs_profile_img_urls.json', 'r') as fp:
        pcs_profile_urls = json.load(fp)

    if self._stage_ind < len(pcs_profile_urls):
        profile_url = pcs_profile_urls[self._stage_ind]
    else:
        print(f'looking for {self._stage_ind + 1}th stage but only'
              f'{len(pcs_profile_urls)} pcs_profile_urls ')
        profile_url = None

    out['pcs'] = tag_stage_imgs(self._pcs_img_urls, profile_url)

    with open(fpath, 'w') as fp:
        json.dump(out, fp, indent=4)

    return out

