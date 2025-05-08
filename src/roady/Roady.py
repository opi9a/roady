import sys
import re
import requests
import json
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from .constants import DATA_DIR, make_urls
from .make_pdf import (make_stage_page, make_front_page, make_teams_page,
                       draw_multi_page)
from .scraping import (get_stages_overview, get_teams,  # xget_teams,
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

    def __init__(self, tour, year, data_dir=None, auto=False,
                 reload_main_urls=False,
                 reload_route_jpgs=False,
                 reload_profile_jpgs=False,
                 reload_teams=False, reload_stages_overview=False,
                 reload_stages=False, teams_url=None, tour_map_url=None,
                 stages_overview_url=None,
                 no_stages=None):
        """ 
        Basic idea is:
            0. make filepaths where resources shd be on disk
            1. load resources:
                - from disk if there
                - if not download them
                    - will need urls

        The fs is:
        data_dir/                       - eg 'tour_roadbooks'
            tour_dir/                   - eg 'france_2024'
                urls.json
                route.jpg               - the overall route
                teams.json
                stages_overview.json    - overview info from
                                          main tour page
                stages/
                    1/
                        data.jsons      - scraped data for stage
                                          incl jpg urls
                        route.jpg
                        profile.jpg

        Make roadbook
        """

        self.tour = tour  # eg 'italy'
        self.year = year  # eg 'italy'

        # Make filepaths for where resources should be
        if data_dir is None:
            self.data_dir = DATA_DIR
        else:
            self.data_dir = Path(data_dir).expanduser()

        self.tour_dir = self.data_dir / f'{tour}_{year}'
        if not self.tour_dir.exists():
            print('creating dir', self.tour_dir)
            self.tour_dir.mkdir()

        self.fps = {
            'route': self.tour_dir / 'route.jpg',
            'teams': self.tour_dir / 'teams.json',
            'stages_overview': self.tour_dir / 'stages_overview',
            'stages_dir': self.tour_dir / 'stages/',
            'roadbook': self.tour_dir / 'roadbook.pdf',
            'teams_pdf': self.tour_dir / 'teams.pdf',
            'urls': self.tour_dir / 'urls.json',
        }

        # first specify the filepaths - each of which will then be populated
        # if required / possible

        # only need the URLS if downloading but may as well load
        # (wrong urls a major source of problems)
        self.urls = self.get_urls()

        print('\n1. OVERALL ROUTE IMG')
        if not self.fps['route'].exists():
            print('-> downloading..', end="")
            download_img(self.urls['route'], self.fps['route'])
            print('OK')
        else:
            print('already on disk')

        print('\n2. TEAMS')
        if self.fps['teams'].exists():
            with open(self.fps['teams'], 'r') as fp:
                self.teams = json.load(fp)
            print('loaded from disk')
        else:
            # this works for the usual format for big tours
            print('-> downloading..', end="")
            teams = get_teams(self.urls['riders'])
            print('OK')

            # small tours or big tours before start can use a different format
            if teams:
                self.teams = teams

            else:
                print('cannot use main teams parser - trying alternate')
                self.teams = get_teams(self.urls['riders'])

            if self.teams:
                with open(self.fps['teams'], 'w') as fp:
                    print('saving teams to', self.fps['teams'])
                    json.dump(self.teams, fp, indent=4)
            else:
                print('COULD NOT SCRAPE / PARSE TEAMS - may not be fatal')

        # STAGES OVERVIEW is sometimes available
        # only place to get the distance and 'type' of the stage 
        print('\n3. STAGES OVERVIEW')
        if not self.fps['stages_overview'].exists():
            print('downloading..', end=" ")
            self.stages_overview = get_stages_overview(self.urls['main'])
            print('ok')
            if self.stages_overview:
                with open(self.fps['stages_overview'], 'w') as fp:
                    json.dump(self.stages_overview, fp, indent=4)
            else:
                print('CANNOT SCRAPE / PARSE STAGES OVERVIEW'
                      ' - may not be fatal')
        else:
            with open(self.fps['stages_overview'], 'r') as fp:
                print('loading from disk')
                self.stages_overview = json.load(fp)

        # INDIVIDUAL STAGES
        self.stages = []
        stage_no = 0

        while True:
            # if have stages_overview then don't need to infer whether done yet
            if no_stages is not None and len(self.stages) == no_stages:
                print('Asked for', no_stages, 'got', len(self.stages))
                break
            if self.stages_overview and stage_no == len(self.stages_overview):
                print('Already got', len(self.stages), 'stages, so stopping')
                break

            stage_no += 1
            print('\nStage', stage_no)

            # make dir if required
            stage_dir = self.fps['stages_dir'] / f'stage_{stage_no}'

            if not stage_dir.exists():
                print('making dir')
                stage_dir.mkdir(parents=True)

            # load stage data or scrape if not already saved
            data_fp = stage_dir / 'data.json'
            if not data_fp.exists():
                url = self.urls['stage_bases']['main'].format(stage_no)
                print(f'need to download data json from {url}..')
                data = scrape_stage(url)
                print('ok')

                # this is where infer if finished, if don't have overview
                if data is None:
                    print('looks like the last stage, no data from', url)
                    stage_dir.rmdir()
                    break
                for k, v in self.urls['stage_bases'].items():
                    data[k] = v.format(stage_no)
                with open(data_fp, 'w') as fp:
                    json.dump(data, fp, indent=4)
            else:
                print('loading data json from disk')
                with open(data_fp, 'r') as fp:
                    data = json.load(fp)

            # compose with info from the overview if available
            if self.stages_overview:
                print('composing with info from overview')
                overview = self.stages_overview[stage_no - 1]
            else:
                print('no overview available')
                overview = None

            stage = compose_stage(data, overview)
            self.stages.append(stage)

            # download the imgs
            route_jpg_fp = stage_dir / 'route.jpg'
            if not route_jpg_fp.exists():
                print('looking to download route jpg..', end=" ")
                download_img(stage['route'], route_jpg_fp)
                print('ok')
            else:
                print('getting route jpg from disk')

            profile_jpg_fp = stage_dir / 'profile.jpg'
            if not profile_jpg_fp.exists():
                print('looking to download profile jpg..', end=" ")
                download_img(stage['profile'], profile_jpg_fp)
                ('ok')
            else:
                print('getting profile jpg from disk')

            # get any extras that are available
            if stage['extra_jpgs']:
                for j in stage['extra_jpgs']:
                    title = j.split('/')[-1]
                    fp = stage_dir / title
                    if not fp.exists():
                        print('getting extra jpg', title, end='.. ')
                        try:
                            download_img(j, fp)
                            ('ok')
                        except:
                            print('cannot get', j)
                    else:
                        print('already have extra jpg', title, 'on disk')

    def get_urls(self, test=True):
        if not self.fps['urls'].exists():
            print('making main urls json and saving')
            urls = make_urls(self.tour, self.year)
            with open(self.fps['urls'], 'w') as fp:
                json.dump(urls, fp, indent=4)

        else:
            print('loading urls json from', self.fps['urls'])
            with open(self.fps['urls'], 'r') as fp:
                urls = json.load(fp)

        # fails = test_urls(urls)

        # if fails:
        #     print(f'got {len(fails)} failed urls:')
        #     for fail in fails:
        #         print(fail)

        #     print('should probably look at cyclingstage.com and update',
        #           ' the templates for that tour in /constants.py or somthing')
        return urls


    def get_fps(self):
        return {
            'urls': self.tour_dir / 'urls.json',
            'route': self.tour_dir / 'route.jpg',
            'teams': self.tour_dir / 'teams.json',
            'stages_overview': self.tour_dir / 'stages_overview',
            'stages_dir': self.tour_dir / 'stages/',
            'roadbook': self.tour_dir / 'roadbook.pdf',
            'teams_pdf': self.tour_dir / 'teams.pdf',
        }

    def __get_value__(self, name):
        """
        Make the thing a dict for eg 'urls'
        """
        return self.__dict__[name]

    def make_roadbook_pdf(self, pdf_fp=None, extra_jpgs=True,
                          double_sided=True, max_teams=True):
        """
        Write it out.  Optionally print the extra jpgs (climbs)
        and enable nice layout for double sided by inserting blank pages
        By default fills any blanks with teams
        """
        if pdf_fp is None:
            pdf_fp = self.fps['roadbook']
        else:
            pdf_fp = Path(pdf_fp).expanduser()

        # set up the pdf canvas
        print('Now making roadbook pdf at', pdf_fp)

        canvas = Canvas(pdf_fp.as_posix(), pagesize=A4, bottomup=True)

        plan = make_page_order(self.stages,
                               double_sided=double_sided, max_teams=max_teams)

        for i, page in enumerate(plan):

            print(f"page {i:>2}: {page}", end=" ")

            if page == 'title':
                # do the front page(s)
                make_front_page(self.stages, self.fps['route'],
                                canvas, tour=self.tour, year=self.year) 
                print("made front")

            elif page == 'blank':
                canvas.showPage()
                print("made blank")
                pass

            elif page == 'teams':
                make_teams_page(self.teams, canvas=canvas)
                print("made teams")

            else:
                stage_str, kind = page.split()
                stage = self.stages[int(stage_str) - 1]
                stage_dir = self.tour_dir / 'stages' / f"stage_{stage['stage_no']}"

                if kind == 'main':
                    make_stage_page(stage, stage_dirpath=stage_dir,
                                    canvas=canvas, km_to_go=True)
                    print("made main for stage", stage['stage_no'])

                elif kind == 'extra':
                    fps = [stage_dir / url.split('/')[-1]
                           for url in stage['extra_jpgs']]
                    fps = [fp for fp in fps if fp.exists()]

                    # get rid of any that are actually profile or route
                    fps_to_print = []
                    for fp in fps:
                        if not fp.exists():
                            continue
                        if "route.jpg" in fp.name:
                            continue
                        if "profile.jpg" in fp.name:
                            continue
                        fps_to_print.append(fp)
                        
                    draw_multi_page(fps_to_print, canvas=canvas)
                    print("made extras for stage", stage['stage_no'])

        canvas.save()

    def make_teams_pdf_page(self, pdf_fp=None):
        """ 
        Can be handy to have an indepenent pdf of the teams
        """
        if pdf_fp is None:
            pdf_fp = self.fps['teams_pdf']

        make_teams_page(teams=self.teams, fp_out=pdf_fp)


def compose_stage(raw_stage, overview):
    """
    Add the overview data to the raw_stage
    """

    stage = raw_stage.copy()

    if overview is None:
        overview = {}

    stage['date2'] = overview.get('date')
    stage['title2'] = overview.get('title')

    stage['type'] = overview.get('type', '___')

    stage['date'] = fix_date(stage.get('date'))

    distance = overview.get('distance')

    if isinstance(distance, float):
        stage['distance'] = distance

    elif distance is None or not str(distance).replace('.', '').isnumeric():
        try:
            stage['distance'] = float(raw_stage['parsed_distance'])
        except:
            stage['distance'] = None
    else:
        stage['distance'] = None

    return stage


def fix_date(dt_str):
    """ 
    Fix up any errors found in the site's dates - it happens
    """
    date_fixes = {
        'dag': 'day',
        'Juli': 'July',
        'Augustus': 'August',
    }

    for error, fix in date_fixes.items():
        if error in dt_str:
            dt_str = dt_str.replace(error, fix)

    return dt_str


def make_page_order(stages, double_sided=True,
                    repeat_teams=True, max_teams=False):
    """
    Return a list with the printing plan
    """

    if repeat_teams:
        out = ['title', 'teams']
    else:
        out = ['title', 'blank']

    for st in stages:
        # this is the problem - when a stage with extra jpgs appears
        # on an odd page - which means its extras page would be overleaf
        # -> solution is to insert a page before, but you don't want that to 
        # mean the previous double spread has a stage only on the left.
        # So you have to go back to before that one.
        # NB no problem with interference between consecutive extra jpg stages,
        # because doing this ensures you are set up correctly for the next stage,
        # with main stage on left of double (next page) and extras facing
        if st['extra_jpgs'] and len(out) % 2 == 0:
            # print(f'stage{st["stage_no"]} has extras and out is {len(out)} so inserting blank')
            out.insert(-1, 'blank')
            # print_plan(out)
        out.append(f"{st['stage_no']} main")
        # print_plan(out)
        if st['extra_jpgs']:
            out.append(f"{st['stage_no']} extra")
            # print_plan(out)

    if len(out) % 2 == 0:
        out.append('blank')

    out.append('teams')

    if not double_sided:
        return [x for x in out if x != 'blank']

    if max_teams:
        return ['teams' if x == 'blank' else x for x in out]

    return out


def print_plan(plan):
    """ 
    Debugging make_page_order
    """

    for i, p in enumerate(plan):
        if " " in p:
            no, kind = p.split()
            print(f"{no}{kind[0]}", end="")
        else:
            print(p[0], end="")
        if i % 2 == 0:
            print('|', end="")
        else:
            print('.', end="")

    print()


def print_urls(urls):
    """
    Just print them so can check
    """

    pad = 10
    print()
    for k, v in urls.items():

        if 'http' in v:
            print(k.ljust(pad), v)

        else:
            print(f"\n{k}:")
            for k1, v1 in v.items():
                print(" ", k1.ljust(pad - 2), v1)

    print('\nif there is a problem it may be because these urls are wrong',
          ' for this tour / year')


def test_urls(urls):
    """ 
    See if they exist
    """

    fails = []
    pad = 10
    print()
    for k, v in urls.items():

        if 'http' in v:
            print(k.ljust(pad), v, end=" : ", flush=True)

            req = requests.get(v)

            if req.ok:
                print('OK')
            else:
                print('FAIL')
                fails.append(v)

        else:
            print(f"\n{k}:")
            for k1, v1 in v.items():
                print(" ", k1.ljust(pad - 2), v1, end=" : ", flush=True)

                req = requests.get(v1.format(1))

                if req.ok:
                    print('OK')
                else:
                    print('FAIL')
                    fails.append(v1)

    return fails
