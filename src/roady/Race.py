"""
Scrape and parse the cyclingstage site just from main url
"""
from pathlib import Path
import json
import pandas as pd
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import cm

from .Stage import Stage
from .Image import Image, draw_img
from .constants import DATA_DIR
from .urls import make_pcs_url, make_cs_url
from .get_teams import make_teams_dict
from .parse_cs import parse_cs_race_html
from .get_resources import get_resource
from .drawing.Rect import Rect
from .drawing.roadbook import print_roadbook
from .drawing.layouts import PORTRAIT

"""
TODO:
    Update function for races as they come near:
        teams
        more / missing imgs (reload urls)
        (move Stage to self._this_param = self._get_this_param() as Race.py)
    One dayers?

"""


class Race:

    def __init__(self, race=None, dpath=None,
                 check=True, verbose=False):
        """
        Essentially a wrapper around cyclingstage.com and
        procyclingstats pages / apis for a race, its stages and images

        Initialise normally with the race name, or dpath

        >>> dp = Race('dauphine_2025')  # or just 25 works

        Main use is make the roadbook pdf
        >>> dp.print_roadbook()

        Can draw in km to go lines on profile imgs, but usually needs
        calibration as the imgs have margins.  To do this, run
        >>> dp.calibrate()

        which will make a pdf with all the profiles drawn with scales
        to allow margins to be estimated by eye, and recorded in calibration.csv
        (the data are in mm)
        Can then make the roadbook use these margins
        >>> dp.print_roadbook(km_to_go=True)  # reads from calibration.csv

        Main public attrs used (type tdf. to see)
        >>> dp.teams
        >>> dp.stages
        >>> dp.df  # a table with info for everything

        Most info is in the data attr of stages:
        >>> dp.stages['4'].data['distance']
        >>> dp.stages['4'].data['vertical_meters']
        >>> dp.stages['4'].climbs_df

        The images are a main part
        >>> dp.stages['4'].imgs

        calibrate profile img km scales manually -> calibration.csv
        >>> dp.calibrate()
        """

        # filesystem and naming etc
        if dpath is not None:
            self.dpath = Path(dpath)
            self._race = self.dpath.name
        else:
            self_name, self_edition = race.split('_')

            if len(self_edition) == 2:
                self_edition = f"20{self_edition}"

            self._race = "_".join([self_name, self_edition])
            self.dpath = DATA_DIR / self._race

        self._calibration_csv_dpath = self.dpath / 'calibration.csv'

        if not self.dpath.exists():
            print('making new race dir', self.dpath)
            self.dpath.mkdir()

        # make an empty calibration.csv if not one already
        if not self._calibration_csv_dpath.exists():
            self._cal_df = make_calibration_csv(self.dpath)
        else:
            with open(self._calibration_csv_dpath, 'r') as fp:
                self._cal_df = pd.read_csv(self._calibration_csv_dpath,
                                           index_col='stage')

        self._cs_url = make_cs_url(self._race)
        self._pcs_url = make_pcs_url(self._race)

        # GET PRIMARY DATA
        # can inspect jsons on disk, see fpath params in _get functions
        self._cs_html = None
        self._pcs_race = None
        self._pcs_race_climbs = None
        self._pcs_profile_img_urls = None
        self._pcs_route_img_url = None
        self._pcs_startlist = None
        self._load()

        # PROCESSING
        self._cs_data = None
        self.teams = None
        self.cs_route_img = None
        self.pcs_route_img = None
        self.stages = None
        self._process()

        self.stages = self.make_stages()
        # all data now loaded, can make roadbook


    # load external resources or their caches with get_resource()
    # see the parsing functions for each resource in get_resource.py
    def _load(self, update=False):
        # the raw cs html is useful
        self._cs_html = get_resource(
            url=self._cs_url,
            fpath=self.dpath / '.cs.html',
            parser='html',
            update=update
        )
        # the main pcs source
        self._pcs_race = get_resource(
            url=self._pcs_url,
            fpath=self.dpath / '.pcs_race.json',
            parser='pcs_race_api',
            update=update
        )
        # pcs Race api has a list of all climbs, with full data
        # - not used in Race object - is read from disk by Stage objects
        self._pcs_race_climbs = get_resource(
            url=f"{self._pcs_url}/route/climbs",
            fpath=self.dpath / '.pcs_race_climbs.json',
            parser='pcs_race_climbs_api',
            update=update
        )
        # pcs race page has handy list of all profile imgs
        # - not used in Race object - read from disk by Stage objects
        self._pcs_profile_img_urls = get_resource(
            url=make_pcs_url(self._race, kind='stage_profile_urls'),
            fpath=self.dpath / '.pcs_profile_img_urls.json',
            parser='pcs_profile_img_urls',
            update=update
        )
        # the pcs img for overall route
        self._pcs_route_img_url = get_resource(
            url=make_pcs_url(self._race, kind='route_img'),
            fpath=self.dpath / '.pcs_route_img_url.json',
            parser='pcs_route_img_url',
            update=update
        )
        # the pcs startlist - used for teams
        self._pcs_startlist = get_resource(
            url=make_pcs_url(self._race, kind='startlist'),
            fpath=self.dpath / '.pcs_startlist.json',
            parser='pcs_startlist',
            update=update
    )

    def _process(self):
        # parse the cs html
        if (self.dpath / '.cs_data.json').exists():
            with open(self.dpath / '.cs_data.json', 'r') as fp:
                self._cs_data = json.load(fp)
        else:
            self._cs_data = parse_cs_race_html(self._cs_html)
            with open(self.dpath / '.cs_data.json', 'w') as fp:
                json.dump(self._cs_data, fp, indent=4)

        # make the teams
        self.teams = make_teams_dict(self._pcs_startlist)

        self.cs_route_img = Image(self._cs_data['route_img_url'],
                                  self.dpath, fname='cs_route_img')
        self.pcs_route_img = Image(self._pcs_route_img_url,
                                   self.dpath, fname='pcs_route_img')

    def make_stages(self):
        """
        Load the stages - now do using pcs
        """
        stages = []

        for i, stage in enumerate(self._pcs_race['stages']):
            stages.append(Stage(self._race, i + 1, check=True))

        return stages


    def check(self, verbose=False):
        """
        cs_html
        pcs_data
        route imgs
        teams

        then call st.check() for st in self.stages
        """
        pad = 20
        out = []

        if self.stages is None:
            out.append('no stages')
        else:
            for st in self.stages:
                try:
                    out.append(st.check(verbose))
                except:
                    print('cannot check stage', st.stage_no)

        print('\nchecking race..')
        if not self.cs_route_img.fpath.exists():
            out.append('cs_route_img')
        elif verbose:
            print(' cs_route_img'.ljust(pad), ': ok')

        if not self.cs_route_img.fpath.exists():
            out.append('pcs_route_img')
        elif verbose:
            print(' pcs_route_img'.ljust(pad), ': ok')

        missing = sum([len(x) for x in out])

        print(f'\nFound {missing} missing params')

    def print_roadbook(self, km_to_go=False):
        """
        Get a canvas
        Draw front page
        For each stage:
            draw stage(pages=1 or 2)
        Draw teams
        """
        print_roadbook(self, km_to_go=km_to_go)

    def df(self):
        """
        Put together the series for each stage
        """
        df = pd.concat([st.series() for st in self.stages], axis=1).T
        df.index.name = 'stage_no'

        # get the 'type' from race-level cs data
        csdf = pd.DataFrame(self._cs_data['stage_data'])
        if not csdf.empty:
            df['cs_type'] = csdf['type'].values
        else:
            df['cs_type'] = None

        return df


    def clear_jsons(self, tags=None, stages=None):
        """
        Remove the jsons from stages (not jpgs etc)
        """
        for stage in self.stages:
            if stages is not None and stage._stage_ind + 1 not in stages:
                continue
            for j in stage.dpath.iterdir():
                if j.name.endswith('json'):
                    if tags is None:
                        print('clearing', j)
                        j.unlink()
                        continue
                    for tag in tags:
                        if tag in j.name:
                            print('clearing', j)
                            j.unlink()

    def calibrate(self, left=None, right=None, source='pcs', cal_lims=None):
        """
        Make a calibration of all profiles
        Need to tell it the left and right coords of where in page the profile
        will be drawn - by default take from PORTRAIT rect

        Pass a tuple of cal_lims for (mm down from img top, mm up from img bottom)
        for how far up and down to draw the calibration (defaults are sane)
        """

        if left is None:
            left = PORTRAIT.left

        if right is None:
            right = PORTRAIT.right

        fp = self.dpath / f'calibrate_{source}_profiles.pdf'
        can = Canvas(fp.as_posix())

        MAX_PROFILE_H = 13
        GAP = 3
        rect = Rect(left=left, right=right, top=PORTRAIT.top, height=MAX_PROFILE_H)
        for st in self.stages:

            can.setFont('Helvetica-Bold', 18)
            can.drawString((rect.left+5) *cm, rect.top *cm, f"stage{st.stage_no}")
            rect.top -= 0.8
            img = st.imgs()['pcs']['profile']

            actual = draw_img(img.fpath, rect, canvas=can, add_calibration=True,
                              cal_lims=cal_lims)

            # stop after 2
            if int(st.stage_no) % 2 == 0:
                can.showPage()
                rect = Rect(left=left, right=right,
                            top=PORTRAIT.top, height=MAX_PROFILE_H)
            else:
                rect.bottom = actual.bottom - (MAX_PROFILE_H + GAP)
                rect.top = actual.bottom - GAP

        can.save()

    def update(self, update_stages=True):
        """
        Use when approaching race and full or more data is available.

        Main things are:
            teams finalized (a few days before start)
            climbs - race and stage
            missing imgs added
        """

        self._load(update=True)
        self._process

        if update_stages:
            for stage in self.stages:
                stage.update()

    def __repr__(self):

        spacing = 16

        fields = [k for k in self.__dict__
                  if 'stage' not in k and not k.startswith('_')]

        out = [f"{k.ljust(spacing)}: {self.__dict__[k]}" for k in fields]

        return "\n".join(out)


def make_calibration_csv(dpath, no_days=21, default_margins=None,
                         overwrite=False):
    """
    Make a calibration csv with the passed number of days and default
    margins (2 elements, l and r).
    Save it and return the df
    """

    if default_margins is None:
        default_margins = [0, 0]

    df = pd.DataFrame([[x] * no_days for x in default_margins]).T
    df.columns = ['l_adj_mm', 'r_adj_mm']
    df.index = list(range(1, no_days+1))
    df.index.name = 'stage'

    fpath = dpath / 'calibration.csv'

    if fpath.exists() and not overwrite:
        print('there is already a file at', fpath)
        print('pass overwrite=True if want that')
        return

    df.to_csv(fpath)

    return df 



def clean_race(race, dpath=None,
               parsed_json=True, all_json=False,
               everything=False,
               html=False):
    """
    Delete stuff
    """
    parsed_jsons = ['.cs_data.json', '']
    if dpath is None:
        dpath = DATA_DIR / race

    for stage in [x for x in dpath.iterdir()
                  if x.name.startswith('stage_') and x.is_dir()]:

        for file in [x for x in stage.iterdir() if x.is_file()]:

            if everything:
                file.unlink()
                continue

            if html and file.endswith('.html'):
                file.unlink()

            if all_json and file.name.endswith('.json'):
                file.unlink()

            if parsed_json:
                if file.name in parsed_jsons:
                    file.unlink()


        print(stage)


