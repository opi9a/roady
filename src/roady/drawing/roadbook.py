from pathlib import Path
import pandas as pd
from datetime import datetime
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import cm

from .Rect import Rect
from .stage import make_stage_page
from ..Image import draw_img
from .teams import make_teams_page
from .layouts import PORTRAIT

MAX_ROUTE_H = 12


def make_roadbook(race, fpath=None, km_to_go=False):
    """
    Draw front page
    Draw each stage
    Draw teams
    """
    if fpath == None:
        fpath = race.dpath / 'roadbook.pdf'

    can = Canvas(fpath.as_posix())

    make_front_page(race, can)

    for st in race.stages:
        if km_to_go:
            profile_margins = race._cal_df.iloc[st._stage_ind].values
        make_stage_page(st, canvas=can, km_to_go=km_to_go,
                        profile_margins=profile_margins)

    make_teams_page(race.teams, canvas=can)

    can.save()


def make_front_page(race, canvas=None, fp_out=None, no_map=False):
    """
    List of stages and map
    Pass no_map = True to not print that jpg eg to save ink
    """

    if canvas is None:
        can = Canvas(fp_out.as_posix())
    else:
        can = canvas
        
    rect = PORTRAIT

    title_h = 1

    name, edition = race._race.split('_')
    can.setFont("Helvetica-Bold", 20)
    can.drawCentredString((rect.left + 9) * cm, (rect.top) * cm,
                      text=f"{name} {edition}")

    # ROUTE
    route_rect = rect.new(top=rect.top - title_h)
    route_rect.height = MAX_ROUTE_H

    actual = draw_img(race.pcs_route_img.fpath, route_rect, canvas=can)

    # STAGES
    # titles with df cols and relative widths
    cols = [
        ('stage', 'stage_no', 1, 'left'),  # stage number
        ('date', 'dt', 1.5, 'left'),
        ('from', 'departure', 3.5, 'left'),
        ('to', 'arrival', 4, 'left'),
        ('km', 'distance', 1, 'right'),
        ('type', 'cs_type', 1.5, 'right'),
        ('climbs', 'no_climbs', 1.5, 'right'),
        ('v_m', 'vertical_meters', 0.5, 'right'),
           ]

    tab_rect = rect.new(top=actual.bottom - 2)

    adj = tab_rect.width / sum([x[2] for x in cols])
    gaps = {x[0]: x[2] * adj for x in cols}
    aligns = {x[0]: x[3] for x in cols}

    df = race.df().reset_index().copy()

    climbs = []
    for ind, row in df.iterrows():
        if row['summit_finish']:
            climbs.append(f"{row['no_climbs']}*")
        else:
            climbs.append(f"{row['no_climbs']}")
    df['no_climbs'] = climbs
    old_cols = [x[1] for x in cols]
    df = df[old_cols]
    df.columns = [x[0] for x in cols]

    df['dt'] = df['date'].copy()
    df = df.set_index('dt')
    df['date'] = df['date'].apply(lambda x: x.strftime("%a %-d"))
    df['km'] = df['km'].astype(int).astype(str)
    df['stage'] = df['stage'].astype(str)
    df['v_m'] = df['v_m'].astype(str)
    df['type'] = df['type'].apply(shorten_stage_type)

    row_h = 0.5
    y = tab_rect.top

    can.setFont("Helvetica-Bold", 10)
    x = tab_rect.left
    for col in df.columns:
        dirn = aligns[col]
        if dirn == 'right':
            can.drawRightString(x*cm, y*cm, col)
        else:
            can.drawString(x*cm, y*cm, col)
        x += gaps[col]

    can.setFont("Helvetica", 10)
    y -= row_h
    for date in pd.date_range(start=df.index[0], end=df.index[-1]):
        x = tab_rect.left
        if date.date() not in df.index:
            can.setFillColor('grey')
            can.drawString((x+gaps['stage'])*cm, y*cm,
                           f'{date.strftime("%a %-d")} {' '*5}'
                           f'{"-"*50} REST DAY {"-"*50}')
            can.setFillColor('black')
            y -= row_h
            continue
        stage = df.loc[date.date()]
        for col in df.columns:
            if aligns[col] == 'left':
                can.drawString(x*cm, y*cm, stage[col][:20])
            else:
                can.drawRightString(x*cm, y*cm, stage[col][:20])
            x += gaps[col]
        y -= row_h

    # is a whole page so..
    can.showPage()
    if canvas is None:
        print('saving to', can._filename)
        can.save()

def shorten_stage_type(stage_str):

    if stage_str is None:
        return '-'
    if 'mountain' in stage_str:
        return 'mnt'

    if stage_str == 'hilly':
        return 'hill'

    return stage_str
