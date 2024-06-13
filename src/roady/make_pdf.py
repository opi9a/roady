from pathlib import Path
import requests
import shutil
import re
from collections import namedtuple
from datetime import datetime, timedelta
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4

from reportlab.lib.colors import blue, black, red, green
from reportlab.lib.units import cm

from PIL import Image
from PIL.ExifTags import TAGS

from .draw_img import draw_rect_img


def make_front_page(stages, img_fp, canvas=None, fp_out=None, tour=None, year=None):
    """
    List of stages and map
    """
    top = 29
    bottom = 2
    left = 1
    right = 20
    width = right - left

    title_h = 1.5
    route_h = 17

    # make a canvas to print out independently if one isn't passed
    if canvas is None and fp_out is not None:
        stand_alone = True
        canvas = Canvas(Path(fp_out).as_posix(), pagesize=A4, bottomup=True)
    else:
        stand_alone = False

    # title - have to infer tour and year
    if tour is None and year is None:
        tour, year = re.search(
            "roadbooks/(\S*)_(\d*)/route.jpg", str(img_fp)).groups()

    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString((left + 5) * cm, (top - title_h) * cm,
                      text=f"{tour} {year}")


    # route map
    route_dims = draw_rect_img(
        img_fp=img_fp,
        canvas=canvas,
        top=(top - title_h - 0.5), height=14,
        right=right, left=left,
    )


    new_stages = []

    fmt = "%A %d %B"
    prev_stage_dt = None
    for stage in stages:
        dt = datetime.strptime(stage['date'], fmt)

        if prev_stage_dt is not None:
            gap = (dt - prev_stage_dt).days
        else:
            gap = 1

        if gap > 1:
            new_dt = dt - timedelta(days=1)
            new_stages.append({'type': 'rest day', 
                               'date': new_dt.strftime(fmt)})
        new_stages.append(stage)
        new_stages[-1]['stage_no'] = str(new_stages[-1]['stage_no'])
        new_stages[-1]['distance'] = str(new_stages[-1]['distance'])

        prev_stage_dt = dt


    # stages
    y0 = top - route_h - title_h + 2 # this is frigged tbf
    lh = min(1, (y0 - bottom) / len(new_stages))

    # column headings
    col_xs = {
        'date': 2,
        'stage_no': 6.5,
        'from_to': 7.5,
        'distance': 15,
        'type': 17,
    }

    canvas.setFont("Helvetica-Bold", 10)

    for col, x in col_xs.items():
        if col == 'from_to': text = "from-to"
        elif col == 'stage_no': text = "no"
        elif col == 'distance': text = "km"
        else: text = col
        canvas.drawString(x * cm, y0 * cm, text=text)

    # stages
    canvas.setFont("Helvetica", 10)

    i = 1
    for stage in new_stages:

        y = (y0 - (lh * i))

        if stage['type'] == 'rest day':
            canvas.drawString(col_xs['date'] * cm, y * cm, text=stage['date'])
            canvas.drawString(col_xs['stage_no'] * cm, y * cm,
                              text=f'{"-"*48} REST DAY {"-"*48}')
            i += 1
            continue

        for col, x in col_xs.items():
            canvas.drawString(x * cm, y * cm, text=stage[col] or 'not found')

        i += 1

    canvas.showPage()

    if stand_alone:
        canvas.save()


def make_pdf(stage_dict, stage_dirpath, canvas=None, outpath=None, 
             km_to_go=False, l_kms_marg=0, r_kms_marg=0, 
             start_finish_km_only=False):
    """
    Compose a pdf page for a stage.
    Pass a canvas or an outpath
    l_kms_marg and r_kms_marg for aligning the kms to go with start and
    end within profile img
    start_finish_km_only just shows those, for aligning / debug
    """

    file_output = False
    if canvas is None:
        out_fp = Path(outpath).as_posix()
        canvas = Canvas(out_fp, pagesize=A4, bottomup=True)
        canvas.setFontSize(18)
        file_output = True

    x, y = 0, 0

    top = 27
    bottom = 2
    left = 2
    right = 18
    top_margin = 1

    # TITLE
    canvas.setFont("Helvetica-Bold", 20)
    title = (f"Stage {stage_dict['stage_no']} - {stage_dict['date']}")
    canvas.drawString((left + 4.5)*cm, top*cm, title)

    # PROFILE
    prof_dims = draw_rect_img(
        img_fp=stage_dirpath / 'profile.jpg',
        canvas=canvas,
        top = top - top_margin, height=12,
        right=right, left=left,
    )


    # ADD A TO-GO SCALE TO THE PROFILE
    # set up dimensions and location of to-go scale

    # get the stage distance, d, and the width of the image
    # draw a vertical line each 10km from end
    scale_l = left + l_kms_marg
    scale_r = scale_l + prof_dims['width'] - r_kms_marg
    scale_w = scale_r - scale_l

    # draw the scale
    if km_to_go and not start_finish_km_only:
        print_km_to_go(
            canvas=canvas,
            start_x=scale_r, scale_w=scale_w,
            stage_km=stage_dict['distance'],
            y0=prof_dims['bottom'],
            y1=prof_dims['top'],
            minor_unit=1,
        )
    
    # debug only
    elif start_finish_km_only:
        canvas.setStrokeColor("red")
        canvas.line(
            scale_l * cm,  # x1
            prof_dims['bottom'] * cm,
            scale_l * cm,  # x2
            prof_dims['top'] * cm,
        )
        canvas.line(
            scale_r * cm,  # x1
            prof_dims['bottom'] * cm,
            scale_r * cm,  # x2
            prof_dims['top'] * cm,
        )

    canvas.setFillAlpha(1)

    # ROUTE
    route_dims = draw_rect_img(
        img_fp=stage_dirpath / 'route.jpg',
        canvas=canvas,
        bottom=bottom, height=14,
        right=right, left=left,
    )

    # ends the page
    canvas.showPage()

    if file_output:
        canvas.save()



def add_extras(extra_jpgs, stage_dirpath, canvas=None, fp_out=None):
    """ 
    Make an additional page
    if 1 or 2 imgs, do 1 per half
    if 3 split page to 3
    if 4 do 2 pages
    """
    # make a canvas to print out independently if one isn't passed
    if canvas is None:
        stand_alone = True
        canvas = Canvas(Path(fp_out).as_posix(), pagesize=A4, bottomup=True)
    else:
        stand_alone = False


    top = 27
    bottom = 3
    left = 2
    right = 18
    top_margin = 1

    title_h = 1
    max_h = 11
    margin = 0.5

    img_h = min(max_h,
                ((top - bottom) / len(extra_jpgs)) - (margin*len(extra_jpgs)))

    last = top

    for jpg in extra_jpgs:
        # print a title
        title = jpg.split('/')[-1]
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString((left + 4.5)*cm, last*cm, title)

        last -= title_h

        # now the img
        dims = draw_rect_img(
            img_fp=stage_dirpath / title,
            canvas=canvas,
            bottom=last - img_h, top=last,
            right=right, left=left,
        )

        last -= (dims['height'] + margin)

    canvas.showPage()

    if stand_alone:
        canvas.save()



def print_km_to_go(canvas, start_x, scale_w, stage_km, y0, y1,
                   minor_unit=1):
    """
    Make the togo scale
    """
    # work out the decrement for the chosen interval (kms)
    dec_1k = scale_w / float(stage_km)
    decrement = dec_1k * minor_unit

    canvas.setStrokeColor("lightblue")
    canvas.setFillColor("lightblue", alpha=0.9)  # for text
    canvas.setFontSize(8)

    k_to_go = 0
    line_x = start_x

    while k_to_go < float(stage_km):
        if k_to_go > 0:
            
            # major units are thicker (by alpha)
            if k_to_go % 10 == 0:
                canvas.setStrokeAlpha(0.4)
            elif k_to_go % 5 == 0:
                canvas.setStrokeAlpha(0.2)
            else:
                canvas.setStrokeAlpha(0.0)

            canvas.line(
                line_x * cm,  # x1
                y0 * cm,  # y1
                line_x * cm,  # x2
                y1 * cm  # y2
            )

        # always draw top number
        if k_to_go % 10 == 0:
            x_nudge = calc_x_nudge(k_to_go)
            canvas.drawString(
                (line_x - x_nudge)*cm,
                y1 * cm,  # y2
                str(k_to_go)
            )
        # at bottom, 0 and 10 overlap the stage length in img
            if k_to_go >= 20:
                canvas.drawString(
                    (line_x - x_nudge)*cm,
                    (y0-0.2)*cm,
                    # (y_start-0.2)*cm,
                    str(k_to_go)
                )

        k_to_go += minor_unit
        line_x -= decrement


def print_teams(teams, canvas=None, fp_out=None, cols=4):
    """
    Teams with riders by number on single page
    """

    # make a canvas to print out independently if one isn't passed
    if canvas is None:
        stand_alone = True
        canvas = Canvas(Path(fp_out).as_posix(), pagesize=A4, bottomup=True)
    else:
        stand_alone = False

    top = 28
    bottom = 2
    left = 2
    right = 21

    pg_h = top - bottom
    pg_w = right - left

    col_w = pg_w / cols
    team_h = pg_h / ((len(teams) // cols) + 1)
    # make lines

    i = 0
    for team, riders in teams.items():
        row = i // cols
        col = i % cols

        print_team(team, riders,
                   x = left + (col_w * col),
                   y = top - (team_h * row),
                   h = team_h,
                   w = col_w,
                   canvas = canvas,
              )
        i += 1

    canvas.showPage()

    if stand_alone:
        canvas.save()


def print_team(team, riders,
               x, y, h, w,
               canvas):
    """
    Print the individual team in a column
    """

    x = x * cm
    y = y * cm
    h = h * cm
    w = w * cm

    lh = (h / (len(riders) + 2))
    
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(x, y, team)

    
    i = 1
    for num, rider in riders.items():
        new_y = y - (lh * i)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(x, new_y, f"{num:>3} {rider}")
        i += 1


def calc_x_nudge(k_to_go):
    """
    Return the amount to nudge the k_to_go leftwards to align
    with the line that was drawn
    """
    # just set the nudges manually
    nudge_by_dig = [0, 0.25, 0.41]

    if k_to_go < 10:
        return nudge_by_dig[0]

    if k_to_go < 100:
        return nudge_by_dig[1]

    return nudge_by_dig[2]


