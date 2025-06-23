from procyclingstats import Stage, Team
import pandas as pd
from datetime import datetime
from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from .constants import DATA_DIR
from .get_teams import sanitize_team, sanitize_rider

PCS_TOURS = {
    'giro': 'giro-d-italia',
    'tour': 'tour-de-france',
    'vuelta': 'vuelta-a-espana',
    'dauphine': 'dauphine',
}


def print_stage_gc(stage_no, race='dauphine_2025', df=None):
    """
    Make a pdf of the stage gc
    """
    stage_no = int(stage_no)
    tour_dir = DATA_DIR / race
    stage_dir = tour_dir / f'stage_{stage_no}'
    csv_fp = stage_dir / 'gc.csv'
    pdf_fp = stage_dir / 'gc.pdf'

    if df is None:
        if csv_fp.exists():
            df = pd.read_csv(csv_fp, index_col='pos')
        else:
            df = get_stage_gc(stage_no, race)

    can = Canvas(pdf_fp.as_posix())

    can.setFont('Helvetica-Bold', 18)
    can.drawString(6*cm, 28*cm, f"Starting GC, Stage {stage_no}")

    y = 27
    row_h = 0.7

    # rect.draw(can)
    can.setFont('Helvetica', 14)
    for pos, rider in df.iterrows():
        x = 0.55
        can.drawString(x*cm, y*cm, str(pos))
        x += 1.5
        can.drawString(x*cm, y*cm, rider['rider_name'])
        x += 9
        can.drawString(x*cm, y*cm,
                       rider['team_name'].replace('Team', '').strip())
        x += 5
        can.drawString(x*cm, y*cm, rider['gap'])
        y -= row_h

    print('saving to', can._filename)
    can.showPage()
    can.save()


def get_stage_gc(stage_no, race='dauphine_2025',
                 return_df=True):
    """
    Gets the gc BEFORE the pased stage and saves as csv
    """
    stage_no = int(stage_no)

    if stage_no == 1:
        print('no gc before stage 1')
        return

    name, edition = race.split('_')
    pcs_tour = PCS_TOURS[name]

    stage = Stage(f'race/{pcs_tour}/{edition}/stage-{stage_no-1}')
    race_dir = DATA_DIR / f"{name}_{edition}"

    gc_dict = stage.gc()

    if not gc_dict:
        print('no gc found - presumably dont exist yet')
        return

    if not return_df:
        return gc_dict

    df = pd.DataFrame(gc_dict)

    df['time_s'] = df['time'].apply(get_secs)
    df['gap_s'] = df['time_s'] - df.loc[0, 'time_s']
    df['gap'] = df['gap_s'].apply(get_time_str)
    df['bonus_s'] = df['bonus'].apply(get_secs)

    df.index += 1
    df.index.name = 'pos'

    # look up the team's abbr
    # teams = pd.read_csv(race_dir / 'teams.csv', index_col='name')
    # df['team_abbr'] = df['team_name'].apply(
    #     lambda x: teams.loc[x, 'abbreviation'])

    df['team_name'] = df['team_name'].apply(sanitize_team)
    # df['team_name'] = df['team_name'].str.replace('Israel', 'Genocidal')
    # df['team_abbr'] = df['team_abbr'].str.replace('IPT', 'GPT')

    df = df[[
        'rider_name', 'team_name',
        # 'team_abbr',
        # 'rider_number', 'team_name', 'time', 'bonus_s',
        'gap',
    ]]

    df['rider_name'] = df['rider_name'].apply(sanitize_rider)

    stage_dir = race_dir / f'stage_{stage_no}'
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


