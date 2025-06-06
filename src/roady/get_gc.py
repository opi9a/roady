from procyclingstats import Stage, Team, Race
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from .constants import DATA_DIR

PCS_TOURS = {
    'italy': 'giro-d-italia',
    'france': 'tour-de-france',
    'spain': 'vuelta-a-espana',
}

"""
Makes pdfs for gc PRIOR TO stages (so won't do stage 1)
Needs stage overviews etc already done
Quick start, should put a pdf in each stage:
    >>> update_tour_gcs('france', 2025)
"""

class Tour:
    def __init__(self, tour, year):
        """
        Hold things like filepaths
        """
        self.tour = tour
        self.year = year
        self.tour_dir = DATA_DIR / f"{tour}_{year}"
        self.pcs_tour = PCS_TOURS[tour]
        self.pcs_tour_url = f'race/{self.pcs_tour}/{year}'

        stages_overview_fp = self.tour_dir / 'stages_overview'

        if not stages_overview_fp.exists():
            print('cant load stages overview from', stages_overview_fp)
            self.stages_df = None
        else:
            with open(stages_overview_fp, 'r') as fp:
                stages_overview = json.load(fp)
            df = pd.DataFrame(stages_overview)
            df['dt'] = df['date'].apply(
                lambda x: datetime.strptime(f"{x}-{year}", "%d-%m-%Y")
            )
            self.stages_df = df[['stage', 'dt', 'title',
                                 'distance', 'type']].set_index('stage')

    def __repr__(self):
        return self.tour_dir.name


def update_tour_gcs(country, year=2025, race=None):
    """
    Go off date, and make gc csvs / pdfs for all
    stages that are complete and which don't have them
    """
    tour = Tour(country, year)

    print(f'updating {country} {year}')
    for stage_no, fields in tour.stages_df.iterrows():

        print(str(stage_no).rjust(3), end=": ")
        if stage_no ==1:
            print('not trying for stage 1')
            continue

        if fields['dt'] >= datetime.now():
            print(f'stage {stage_no} is today or later')
            continue

        stage_dir = tour.tour_dir / 'stages' / f'stage_{stage_no}'
        csv_fp = stage_dir / 'gc.csv'
        pdf_fp = stage_dir / 'gc.pdf'

        if pdf_fp.exists():
            print('already have pdf')
            continue

        print('..getting..', end=" ")
        print_stage_gc(stage_no, csv_fp=csv_fp, pdf_fp=pdf_fp,
                       country=country, year=year)


def print_stage_gc(stage_no, country='italy', year=2025,
                   csv_fp=None, pdf_fp=None):
    """
    Make a pdf of the stage gc
    """
    tour_dir = DATA_DIR / f"{country}_{year}"
    stage_dir = tour_dir / 'stages' / f'stage_{stage_no}'
    if csv_fp is None:
        csv_fp = stage_dir / 'gc.csv'
    if pdf_fp is None:
        pdf_fp = stage_dir / 'gc.pdf'

    if csv_fp.exists():
        df = pd.read_csv(csv_fp, index_col='pos')
    else:
        df = get_stage_gc(stage_no, country, year)

    can = Canvas(pdf_fp.as_posix())

    can.setFontSize(18)
    can.drawString(5*cm, 27*cm, f"Starting GC, Stage {stage_no}")

    y = 26
    row_h = 0.7
    l_marg = 3
    bottom = 3

    can.setFontSize(11)
    for pos, rider in df.iterrows():
        x = l_marg
        can.drawString(x*cm, y*cm, str(pos))
        x += 1.5
        can.drawString(x*cm, y*cm, rider['rider_name'])
        x += 7
        can.drawString(x*cm, y*cm, rider['team_abbr'])
        x += 2
        can.drawString(x*cm, y*cm, rider['gap'])
        y -= row_h
        if y <= bottom:
            break

    print('saving pdf to stage directory')
    can.showPage()
    can.save()


def get_stage_gc(stage_no, country='italy', year=2025):
    """
    Gets the gc BEFORE the pased stage and saves as csv
    """

    if stage_no == 1:
        print('no gc before stage 1')
        return

    pcs_tour = PCS_TOURS[country]

    stage = Stage(f'race/{pcs_tour}/{year}/stage-{stage_no-1}')
    tour_dir = DATA_DIR / f"{country}_{year}"

    df = pd.DataFrame(stage.gc())

    df['time_s'] = df['time'].apply(get_secs)
    df['gap_s'] = df['time_s'] - df.loc[0, 'time_s']
    df['gap'] = df['gap_s'].apply(get_time_str)
    df['bonus_s'] = df['bonus'].apply(get_secs)

    df.index += 1
    df.index.name = 'pos'

    # look up the team's abbr
    teams = pd.read_csv(tour_dir / 'teams.csv', index_col='name')
    df['team_abbr'] = df['team_name'].apply(
        lambda x: teams.loc[x, 'abbreviation'])

    df['team_name'] = df['team_name'].str.replace('Israel', 'Genocidal')
    df['team_abbr'] = df['team_abbr'].str.replace('IPT', 'GPT')

    df = df[[
        'rider_name', 'team_abbr',
        # 'rider_number', 'team_name', 'time', 'bonus_s',
        'gap',
    ]]


    stage_dir = tour_dir / 'stages' / f'stage_{stage_no}'
    fp = stage_dir / 'gc.csv'

    print('printing to', fp)
    df.to_csv(fp)

    return df

def get_teams(team_urls, tour_dir=None):
    """
    Return a df from the list of team urls
    Pass a tour_dir, eg ../roady/data/italy_2025, to save csv
    """

    df = pd.DataFrame(
        get_team(url) for url in set(team_urls)
    )

    if tour_dir is not None:
        fp = tour_dir / 'teams.csv'
        print('saving teams to', fp)
        df.to_csv(fp, index=False)

    return df

def get_team(team_url):
    """
    For a url return select data
    """
    team = Team(team_url).parse()

    return {
        'name': team['name'],
        'nationality': team['nationality'],
        'abbreviation': team['abbreviation'],
        'bike': team['bike'],
        'status': team['status'],
        'url': team_url
    }


def get_secs(time_str):
    """
    Convert time_str to seconds
    """

    hours, mins, secs = [int(x) for x in time_str.split(':')]

    return (hours * 60 * 60) + (mins * 60) + secs

def get_time_str(secs):
    """
    Return a string of form "HH:MM:SS"
    """

    hours, secs = divmod(secs, 3600)
    mins, secs = divmod(secs, 60)

    if hours:
        stub = f"{str(hours).zfill(2)}:"
    else:
        stub = ""

    return (f"{stub}{str(mins).zfill(2)}:"
            f"{str(secs).zfill(2)}")


