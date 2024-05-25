
import re
import json
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from .constants import DATA_DIR, BASE_URLS
from .make_pdf import make_pdf, make_front_page, print_teams
from .scraping import (get_overview, get_teams,
                       get_stage_urls, scrape_stage)

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
                 teams_url=None, tour_map_url=None):

        self.tour = tour
        self.year = year
        self.base_url = BASE_URLS[tour].format(year, {}, year)

        if data_dir is None:
            self.data_dir = DATA_DIR
        else:
            self.data_dir = Path(data_dir).expanduser()

        self.tour_dir = self.data_dir / f'{tour}_{year}'
        self.imgs_dir = self.tour_dir / 'imgs'

        if not self.tour_dir.exists():
            print('creating dir', self.tour_dir)
            self.tour_dir.mkdir()

        if not self.imgs_dir.exists():
            print('creating dir', self.imgs_dir)
            self.imgs_dir.mkdir()

        # get overall route img url
                
        if tour_map_url is None:
            self.tour_map_url = make_tour_map_url(self.tour, self.year)
        else:
            self.tour_map_url = tour_map_url

        # scrape teams
        teams_json = self.tour_dir / 'teams.json'

        if teams_json.exists():
            with open(teams_json, 'r') as fp:
                self.teams = json.load(fp)
        else:
            # nb this may not make right url - format different each year
            if teams_url is None:
                self.teams_url = make_teams_url(self.tour, self.year)
            else:
                self.teams_url = teams_url

            self.teams = get_teams(teams_url)

            with open(teams_json, 'w') as fp:
                print('saving teams to', teams_json)
                json.dump(self.teams, fp, indent=4)

        # get overview - scrape if not already saved
        self.overview_path = self.tour_dir / 'stages_overview.json'
        if not self.overview_path.exists():
            self.overview = get_overview(self.tour, self.year)
            with open(self.overview_path, 'w') as fp:
                json.dump(self.overview, fp, indent=4)
        else:
            with open(self.overview_path, 'r') as fp:
                self.overview = json.load(fp)

        # get raw stages - scrape if not already saved
        self.raw_stages_path = self.tour_dir / 'stages.json'
        if not self.raw_stages_path.exists():
            self.raw_stages = make_raw_stages_list(self.base_url)
            with open(self.raw_stages_path, 'w') as fp:
                json.dump(self.raw_stages, fp, indent=4)
        else:
            with open(self.raw_stages_path, 'r') as fp:
                self.raw_stages = json.load(fp)

        # make the composed stages
        self.stages = compose_stages(self.raw_stages, self.overview)

        # pdf location
        self.pdf_fp = self.tour_dir / 'roadbook.pdf'

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
        make_front_page(self.stages, self.tour_map_url,
                        canvas, imgs_dir=self.imgs_dir,
                        tour=self.tour, year=self.year) 

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


def make_teams_url(tour, year):
    """
    Return the url
    """

    base = BASE_URLS[tour].format(year, year, year)

    url = base.replace(f"-route/stage-{year}-", "/riders-")

    req = requests.get(url)

    if not req.ok:
        raise ValueError("Looks like teams url is not right. "
                         "Can pass directly when instantiating Roady")
    return url


def make_raw_stages_list(base_url):
    """
    Get the urls, then scrape each to make jsons of resources
    Also scrapes the front page overview which has info on length,
    type of stage etc.
    """

    urls = get_stage_urls(base_url)

    stages = [scrape_stage(url) for url in urls]

    return stages


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


