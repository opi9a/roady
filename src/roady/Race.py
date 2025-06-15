"""
Scrape and parse the cyclingstage site just from main url
"""
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import re
import json
import procyclingstats

from .Stage import Stage
from .Image import Image
from .constants import DATA_DIR
from .urls import CS_URL_BASES, PCS_URL_BASES, make_pcs_url
from .get_teams import make_teams_dict
from .parse_cs import parse_cs_race_html
from .get_resources import get_resource

"""
TODO:
    add a method to audit data tree
        most important is probably stage.check()
        can just do this when instantiating,
        as everything in memory
        eg:
            cs_html: 25015 chars
            pcs_data: 21 keys
            cs_img_urls: profile, route, 2 others
            pcs_img_urls: profile, NO ROUTE, 3 others
"""

class Race:

    def __init__(self, race=None, dpath=None):
        """
        Essentially a wrapper around cyclingstage.com and
        procyclingstats pages / apis for a race, its stages and images

        Initialise normally with the race name, or dpath

        >>> tdf = Race('tour_24')  # or 2024
        or
        >>> tdf = Race(dpath='~/shared/my_packages/roady/data/tour_2025')
        # NB must fit this naming convention, either way

        A dict with all parsed data
        >>> dp.data

        Teams
        >>> dp.teams   # TODO

        To get the stages
        >>> stages = dp.stages

        Can then eg:
        >>> stages['4']
        >>> stages['4'].distance
        >>> stages['4'].climbs_df
        >>> stages['4'].imgs
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

        if not self.dpath.exists():
            print('making new race dir', self.dpath)
            self.dpath.mkdir()

        self._cs_url = CS_URL_BASES[self_name].format(self_edition)
        self._pcs_url = PCS_URL_BASES[self_name].format(self_edition)

        # MAKE DATA MODEL

        # load external resources or their caches
        # NB most files hidden
        
        self._cs_html = get_resource(
            url=self._cs_url,
            fpath=self.dpath / '.cs.html',
            parser='html',
        )

        self._pcs_race = get_resource(
            url=self._pcs_url,
            fpath=self.dpath / '.pcs_race.json',
            parser='pcs_race_api',
        )

        # Not used in Race object - is used by Stage objects,
        # which don't have all the info. They load from disk.
        self._pcs_race_climbs = get_resource(
            url=f"{self._pcs_url}/route/climbs",
            fpath=self.dpath / '.pcs_race_climbs.json',
            parser='pcs_race_climbs_api',
        )

        # Not used in Race object - is used by Stage objects,
        # which don't have all the info. They load from disk.
        self._pcs_profile_img_urls = get_resource(
            url=make_pcs_url(self._race, kind='stage_profile_urls'),
            fpath=self.dpath / '.pcs_profile_img_urls.json',
            parser='pcs_profile_img_urls',
        )

        # the pcs img for overall route
        self._pcs_route_img_url = get_resource(
            url=make_pcs_url(self._race, kind='route_img'),
            fpath=self.dpath / '.pcs_route_img_url.json',
            parser='pcs_route_img_url',
        )

        # the pcs startlist - used for teams
        self._pcs_startlist = get_resource(
            url=make_pcs_url(self._race, kind='startlist'),
            fpath=self.dpath / '.pcs_startlist.json',
            parser='pcs_startlist',
        )

        # processing
        self._cs_data = parse_cs_race_html(self._cs_html)
        self.teams = make_teams_dict(self._pcs_startlist)
        self.cs_route_img = Image(self._cs_data['route_img_url'],
                                  self.dpath, fname='cs_route_img')
        self.pcs_route_img = Image(self._pcs_route_img_url,
                                   self.dpath, fname='pcs_route_img')
        self.stages = [
            Stage(url, self.dpath) for url in self._cs_data['stage_urls']]

        # all data now loaded, can make roadbook
        # self.make_roadbook()

    def check(self):
        """
        cs_html
        pcs_data
        route imgs
        teams

        then call st.check() for st in self.stages
        """
        pass

    def make_roadbook(self):
        """
        Get a canvas
        Draw front page
        For each stage:
            draw stage(pages=1 or 2)
        Draw teams
        """
        pass

    def __repr__(self):

        spacing = 16

        fields = [k for k in self.__dict__
                  if 'stage' not in k and not k.startswith('_')]

        out = [f"{k.ljust(spacing)}: {self.__dict__[k]}" for k in fields]

        return "\n".join(out)
