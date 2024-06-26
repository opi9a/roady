
import re
import requests
import json
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from .constants import DATA_DIR, make_urls
from .make_pdf import make_pdf, make_front_page, print_teams
from .scraping import (get_stages_overview, get_teams, xget_teams,
                       download_img, scrape_stage)

class Roady:
    """
    Scrapes and holds data for making a roadbook

    >>> rd = Roady('france', 2023)
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
        data_dir/                       - eg 'tour_roadbooks'
            tour_dir/                   - eg 'france_2024'
                urls.json
                route.jpg               - the overall route
                teams.json
                stages_overview.json    - overview info from main tour page
                stages/
                    1/
                        data.jsons      - scraped data for stage
                        route.jpg
                        profile.jpg

        Make roadbook
        """

        self.tour = tour  # eg 'italy'
        self.year = year  # eg 'italy'

        # MAKE / CHECK DIRECTORIES
        if data_dir is None:
            self.data_dir = DATA_DIR
        else:
            self.data_dir = Path(data_dir).expanduser()

        self.tour_dir = self.data_dir / f'{tour}_{year}'
        if not self.tour_dir.exists():
            print('creating dir', self.tour_dir)
            self.tour_dir.mkdir()

        # first specify the filepaths - each of which will then be populated
        # if required / possible
        self.fps = {
            'urls': self.tour_dir / 'urls.json',
            'route': self.tour_dir / 'route.jpg',
            'teams': self.tour_dir / 'teams.json',
            'stages_overview': self.tour_dir / 'stages_overview',
            'stages_dir': self.tour_dir / 'stages/',
            'roadbook': self.tour_dir / 'roadbook.pdf',
        }

        # make the URLS we are going to need, if not already there
        if not self.fps['urls'].exists() or reload_main_urls:
            print('making main urls json and saving')
            self.urls = make_urls(tour, year)
            with open(self.fps['urls'], 'w') as fp:
                json.dump(self.urls, fp, indent=4)

        else:
            print('loading urls json from', self.fps['urls'])
            with open(self.fps['urls'], 'r') as fp:
                self.urls = json.load(fp)

        # download the OVERALL ROUTE jpg
        if not self.fps['route'].exists():
            download_img(self.urls['route'], self.fps['route'])

        # TEAMS data (sometimes referred to as riders)
        if self.fps['teams'].exists() and not reload_teams:
            with open(self.fps['teams'], 'r') as fp:
                self.teams = json.load(fp)
        else:
            # this works for the usual format for big tours
            teams = get_teams(self.urls['riders'])

            # small tours or big tours before start can use a different format
            if teams:
                self.teams = teams

            else:
                print('cannot use main teams parser - trying alternate')
                self.teams = xget_teams(self.urls['riders'])

            if self.teams:
                with open(self.fps['teams'], 'w') as fp:
                    print('saving teams to', self.fps['teams'])
                    json.dump(self.teams, fp, indent=4)
            else:
                print('COULD NOT SCRAPE / PARSE TEAMS - may not be fatal')

        # STAGES OVERVIEW is sometimes available
        # only place to get the distance and 'type' of the stage 
        if not self.fps['stages_overview'].exists() or reload_stages_overview:
            self.stages_overview = get_stages_overview(self.urls['main'])
            if self.stages_overview:
                with open(self.fps['stages_overview'], 'w') as fp:
                    json.dump(self.stages_overview, fp, indent=4)
            else:
                print('CANNOT SCRAPE / PARSE STAGES OVERVIEW'
                      ' - may not be fatal')
        else:
            with open(self.fps['stages_overview'], 'r') as fp:
                self.stages_overview = json.load(fp)

        # INDIVIDUAL STAGES
        self.stages = []
        stage_no = 0

        while True:
            if self.stages_overview and stage_no == len(self.stages_overview):
                print('Already got', len(self.stages), 'stages, so stopping')
                break

            stage_no += 1
            print('\nStage', stage_no)

            # make dir if required
            stage_dir = self.fps['stages_dir']/ f'stage_{stage_no}'

            if not stage_dir.exists():
                stage_dir.mkdir(parents=True)

            # load stage data or scrape if not already saved
            data_fp = stage_dir / 'data.json'
            if not data_fp.exists() or reload_stages:
                url = self.urls['stage_bases']['main'].format(stage_no)
                data = scrape_stage(url)

                if data is None:
                    print('looks like the last stage, no data from', url)
                    stage_dir.unlink()
                    break
                for k,v in self.urls['stage_bases'].items():
                    data[k] = v.format(stage_no)
                with open(data_fp, 'w') as fp:
                    json.dump(data, fp, indent=4)
            else:
                with open(data_fp, 'r') as fp:
                    data = json.load(fp)

            # compose with info from the overview if available
            if self.stages_overview:
                overview = self.stages_overview[stage_no - 1]
            else:
                overview = None

            stage = compose_stage(data, overview)
            self.stages.append(stage)

            # download the imgs
            route_jpg_fp = stage_dir / 'route.jpg'
            if not route_jpg_fp.exists() or reload_route_jpgs:
                download_img(stage['route'], route_jpg_fp)

            profile_jpg_fp = stage_dir / 'profile.jpg'
            if not profile_jpg_fp.exists() or reload_profile_jpgs:
                download_img(stage['profile'], profile_jpg_fp)


    def __get_value__(self, name):
        """ 
        Make the thing a dict for eg 'urls'
        """
        return self.__dict__[name]


    def make_roadbook_pdf(self, pdf_fp=None):
        """
        Write it out
        """
        if pdf_fp is None:
            pdf_fp = self.fps['roadbook']
        else:
            pdf_fp = Path(pdf_fp).expanduser()

        # set up the pdf canvas
        print('Now making roadbook pdf at', pdf_fp)

        canvas = Canvas(pdf_fp.as_posix(), pagesize=A4, bottomup=True)

        # do the front page(s)
        make_front_page(self.stages, self.fps['route'],
                        canvas, tour=self.tour, year=self.year) 

        # print teams
        print_teams(self.teams, canvas=canvas)

        # iterate over stages
        print('stage', end=" ")
        for i, stage in enumerate(self.stages):
            stage_dir = self.tour_dir / 'stages' / f"stage_{i+1}"
            make_pdf(stage, stage_dirpath=stage_dir, canvas=canvas)
            print(i+1, end=" ", flush=True)
        print()

        canvas.save()


def compose_stage(raw_stage, overview):
    """
    Add the overview data to the raw_stage
    """

    stage = raw_stage.copy()

    if overview is None:
        overview = {}

    stage['date2'] = overview.get('date')
    stage['title2'] = overview.get('title')
    stage['distance'] = overview.get('distance')
    stage['type'] = overview.get('type', '___')

    stage['date'] = fix_date(stage.get('date'))

    return stage


def fix_date(dt_str):
    """ 
    Fix up any errors found in the site's dates - it happens
    """

    if 'dag' in dt_str:
        dt_str = dt_str.replace('dag', 'day')

    if 'Juli' in dt_str:
        dt_str = dt_str.replace('Juli', 'July')

    return dt_str


