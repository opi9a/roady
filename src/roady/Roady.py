
import re
import requests
import json
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from .constants import DATA_DIR, make_urls
from .make_pdf import make_pdf, make_front_page, print_teams
from .scraping import (get_stages_overview, get_teams, download_img,
                       make_stage_urls, scrape_stage)

class Roady:
    """
    Scrapes and holds data for making a roadbook

    >>> rd = Roady('tour', 2023)
    >>> rd.make_roadbook_pdf()

    this will make a roadbook and save it by default at
    ~/.tour_roadbooks/tour_2023/roadbook.pdf

    may need to pass teams url or tour_map_url separately
    """

    def __init__(self, tour, year, data_dir=None,
                 reload_main_urls=False,
                 reload_route_jpgs=False,
                 reload_profile_jpgs=False,
                 reload_teams=False, reload_stages_overview=False,
                 reload_stages=False, teams_url=None, tour_map_url=None):
        """ 
        Scraping:
            High level:
                overview map (img)
                teams data (json)
                stage urls (json)
            Stages:
                data (json)
                route map (img)
                profile map (img)
                [gpx ?]

            First get high level, incl stage urls
            Then stages - folder for each
                - for each dl: make url and fp, then check if fp exists

        Make roadbook
        """

        self.tour = tour
        self.year = year

        # MAKE / CHECK DIRECTORIES
        if data_dir is None:
            self.data_dir = DATA_DIR
        else:
            self.data_dir = Path(data_dir).expanduser()

        self.tour_dir = self.data_dir / f'{tour}_{year}'
        if not self.tour_dir.exists():
            print('creating dir', self.tour_dir)
            self.tour_dir.mkdir()

        # MAIN ELEMENTS (ie not stages)
        # urls and fps - need to check if fps exist,
        # in which case assume they're already scraped etc
        # - this allows for editing of the jsons if reqd
        self.urls_json_fp = self.tour_dir / 'urls.json'

        if not self.urls_json_fp.exists() or reload_main_urls:
            print('making main urls json and saving')
            self.urls = make_urls(tour, year)
            with open(self.urls_json_fp, 'w') as fp:
                json.dump(self.urls, fp, indent=4)

        else:
            print('loading urls json from', self.urls_json_fp)
            with open(self.urls_json_fp, 'r') as fp:
                self.urls = json.load(fp)

        # overview map img
        self.route_fp = self.tour_dir / 'route.jpg'
        if not self.route_fp.exists():
            download_img(self.urls['route'], self.route_fp)

        # teams data json
        self.teams_json_fp = self.tour_dir / 'teams.json'

        if self.teams_json_fp.exists() and not reload_teams:
            with open(self.teams_json_fp, 'r') as fp:
                self.teams = json.load(fp)
        else:
            self.teams = get_teams(self.urls['riders'])

            with open(self.teams_json_fp, 'w') as fp:
                print('saving teams to', self.teams_json_fp)
                json.dump(self.teams, fp, indent=4)

        # STAGES
        # scrape the stages overview - scrape if not already saved
        # this comes from the front page. a bit redundant but only
        # place to get the 'type' of the stage (and something else?)
        # - it forms a component of the final stage info (with raw stage)
        self.stages_overview_path = self.tour_dir / 'stages_overview.json'
        if not self.stages_overview_path.exists() or reload_stages_overview:
            self.stages_overview = get_stages_overview(self.urls['main'])
            with open(self.stages_overview_path, 'w') as fp:
                json.dump(self.stages_overview, fp, indent=4)
        else:
            with open(self.stages_overview_path, 'r') as fp:
                self.stages_overview = json.load(fp)

        # scrape stage data if not already saved
        # then compose to make final stage and dl imgs
        self.stages = []
        for i, overview in enumerate(self.stages_overview):
            stage_no = i + 1
            print('stage', overview)
            stage_dir = self.tour_dir / 'stages' / f'stage_{i+1}'

            if not stage_dir.exists():
                stage_dir.mkdir(parents=True)

            data_fp = stage_dir / 'data.json'
            if not data_fp.exists() or reload_stages:
                url = self.urls['stage_bases']['main'].format(stage_no)
                data = scrape_stage(url)
                for k,v in self.urls['stage_bases'].items():
                    data[k] = v.format(stage_no)
                with open(data_fp, 'w') as fp:
                    json.dump(data, fp, indent=4)
            else:
                with open(data_fp, 'r') as fp:
                    data = json.load(fp)

            stage = compose_stage(data, overview)
            self.stages.append(stage)

            route_jpg_fp = stage_dir / 'route.jpg'
            if not route_jpg_fp.exists() or reload_route_jpgs:
                download_img(stage['route'], route_jpg_fp)

            profile_jpg_fp = stage_dir / 'profile.jpg'
            if not profile_jpg_fp.exists() or reload_profile_jpgs:
                download_img(stage['profile'], profile_jpg_fp)

        # pdf location
        self.pdf_fp = self.tour_dir / 'roadbook.pdf'

    def __get_value__(self, name):
        """ 
        Make the thing a dict for eg 'urls'
        """
        return self.__dict__[name]


    def pre_pdf_check(self):
        """ 
        Make sure all images etc are present
        Invite to supply if not
        """
        pass

    def make_roadbook_pdf(self, pdf_fp=None):
        """
        Write it out
        """
        if pdf_fp is None:
            pdf_fp = self.pdf_fp
        else:
            pdf_fp = Path(pdf_fp).expanduser()

        # set up the pdf canvas
        print('Now making roadbook pdf at', pdf_fp)

        canvas = Canvas(pdf_fp.as_posix(), pagesize=A4, bottomup=True)

        # do the front page(s)
        try:
            make_front_page(self.stages, self.tour_map_url,
                            canvas, imgs_dir=self.imgs_dir) 
        except:
            print('cannot make front page')

        # print teams
        print_teams(self.teams, canvas=canvas)

        # iterate over stages
        print('stage', end=" ")
        for i, stage in enumerate(self.stages):
            make_pdf(stage, canvas=canvas, imgs_dir=self.imgs_dir)
            print(i+1, end=" ", flush=True)
        print()

        canvas.save()


def make_tour_map_url(tour, year, imgs_dir=None):
    """
    Return the url
    """

    if tour == 'tour':
        tour = 'tour-de-france'

    url = f"https://cdn.cyclingstage.com/images/{tour}/{year}/route.jpg"

    req = requests.get(url)

    if not req.ok:
        raise ValueError("Looks like overall map url is not right. "
                         "Can pass directly when instantiating Roady")

    return url


def make_raw_stages_list(base_stage_url):
    """
    Get the urls, then scrape each to make jsons of resources
    Also scrapes the front page overview which has info on length,
    type of stage etc.
    """

    urls = make_stage_urls(base_stage_url)

    stages = [scrape_stage(url) for url in urls]

    return stages


def compose_stage(raw_stage, overview):
    """
    Add the overview data to the raw_stage
    """

    stage = raw_stage.copy()

    stage['date2'] = overview['date']
    stage['title2'] = overview['title']
    stage['distance'] = overview['distance']
    stage['type'] = overview['type']

    stage['date'] = fix_date(stage['date'])

    return stage


def compose_stages(raw_stages, overview):
    """
    Add the overview data to the raw_stages
    """

    assert len(raw_stages) == len(overview)

    stages = raw_stages.copy()

    for i, stage in enumerate(stages):
        stage['date2'] = overview[i]['date']
        stage['title2'] = overview[i]['title']
        stage['distance'] = overview[i]['distance']
        stage['type'] = overview[i]['type']

        stage['date'] = fix_date(stage['date'])

    return stages


def fix_date(dt_str):
    """ 
    Fix up any errors found in the site's dates - it happens
    """

    if 'dag' in dt_str:
        dt_str = dt_str.replace('dag', 'day')

    if 'Juli' in dt_str:
        dt_str = dt_str.replace('Juli', 'July')

    return dt_str


