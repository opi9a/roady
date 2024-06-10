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

class Rect:
    """
    Use this to hold coords for rectantles on the page,
    eg profile, route
    """
    def __init__(self, bottom=None, top=None, height=None,
                 left=None, right=None, width=None):

        self.bottom = bottom
        self.top = top
        self.height = height
        self.left = left
        self.right = right
        self.width = width


def make_front_page(stages, img_fp, canvas, tour=None, year=None):
    """
    List of stages and map
    """
    top = 29
    bottom = 2
    left = 2
    right = 21
    width = right - left

    title_h = 1.5
    route_h = 17

    # title - have to infer tour and year
    if tour is None and year is None:
        tour, year = re.search("images/(\S*)/(\d*)/route.jpg", img_url).groups()
        tour = tour.title().replace('-', ' ').replace("De", "de")

    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString((left + 5) * cm, (top - title_h) * cm,
                      text=f"{tour} {year}")


    # route map
    i_dict = get_image_dict(img_fp)

    h, w = scale_image(i_dict['height'], i_dict['width'],
                       width, route_h)


    canvas.drawInlineImage(
        i_dict['path'].as_posix(),
        x = left + ((width - w)/2) * cm,
        y = (top - h - title_h - 1) * cm,
        height = h * cm,
        width = w * cm,
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


def make_pdf(stage_dict, stage_dirpath, canvas=None, outpath=None, 
             km_to_go=False, l_kms_marg=0, r_kms_marg=0, 
             start_finish_km_only=False):
    """
    Compose a pdf page for a stage.
    Pass a canvas or an outpath
    l_kms_marg and r_kms_marg for aligning the kms to go with start and
    end within profile img
    start_finish_km_only just shows those, for aligning
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

    canvas.setFont("Helvetica-Bold", 20)
    title = (f"Stage {stage_dict['stage_no']} - {stage_dict['date']}")
    canvas.drawString((left + 4.5)*cm, top*cm, title)

    i_dict = {}

    i_dict['route'] = get_image_dict(stage_dirpath / 'route.jpg')
    i_dict['profile'] = get_image_dict(stage_dirpath / 'profile.jpg')
    print(f"h: {i_dict['profile']['height']}, "
          f"w: {i_dict['profile']['height']}", end=" - ")

    h, w = scale_image(
        i_dict['route']['height'],
        i_dict['route']['width'],
        max_h = 14,
        max_w = right - left,
    )
    scale_factor = h / i_dict['route']['height']
    scale_factor_w = w / i_dict['route']['width']
    print(f"scaled by {scale_factor:.4f}")

    i_dict['route']['plot_height'] = h
    i_dict['route']['plot_width'] = w

    h, w = scale_image(
        i_dict['profile']['height'],
        i_dict['profile']['width'],
        max_h = 15,
        max_w = right - left,
    )

    i_dict['profile']['plot_height'] = h
    i_dict['profile']['plot_width'] = w


    # the profile first, at top
    profile = Rect(
        bottom = top - (top_margin + i_dict['profile']['plot_height']),
        height = i_dict['profile']['plot_height'],
        width = i_dict['profile']['plot_width'],
        top = top - top_margin,
    )

    canvas.drawInlineImage(
        i_dict['profile']['path'].as_posix(),
        x = left*cm,
        y = profile.bottom * cm,
        height =  profile.height * cm,
        width = profile.width* cm,
    )


    # ADD A TO-GO SCALE TO THE PROFILE
    # set up dimensions and location of to-go scale

    # get the stage distance, d, and the width of the image
    # draw a vertical line each 10km from end
    scale_l = left + l_kms_marg
    scale_r = scale_l + i_dict['profile']['plot_width'] - r_kms_marg
    scale_w = scale_r - scale_l

    # draw the scale
    if km_to_go and not start_finish_km_only:
        print_km_to_go(
            canvas=canvas,
            start_x=scale_r, scale_w=scale_w,
            stage_km=stage_dict['distance'],
            y0=profile.bottom,
            y1=profile.top,
            minor_unit=1,
        )
    elif start_finish_km_only:
        canvas.setStrokeColor("red")
        canvas.line(
            scale_l * cm,  # x1
            profile.bottom * cm,  # y1
            scale_l * cm,  # x2
            profile.top * cm  # y2
        )
        canvas.line(
            scale_r * cm,  # x1
            profile.bottom * cm,  # y1
            scale_r * cm,  # x2
            profile.top * cm  # y2
        )

    canvas.setFillAlpha(1)

    # the route
    if 'route' in stage_dict.keys():
        y = top - (
                2 # allowance for title
                + i_dict['profile']['plot_height']
                + 0 # gap
                + i_dict['route']['plot_height']
            )
        canvas.drawInlineImage(
            i_dict['route']['path'].as_posix(),
            x = left*cm,
            y = y*cm,
            height = i_dict['route']['plot_height'] * cm,
            width = i_dict['route']['plot_width'] * cm,
        )

    # ends the page
    canvas.showPage()

    if file_output:
        canvas.save()

    return i_dict


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


def scale_image(i_h, i_w, max_h, max_w):
    """
    For passed image height and width, and max values,
    return the height and width to print
    """

    # image too tall, scale to max height
    if i_h / i_w > max_h / max_w:
        out = max_h, i_w * (max_h / i_h)

    # too wide, scale to max width
    else:
        out = i_h * (max_w / i_w), max_w

    return  out


def print_teams(teams, canvas, cols=4):
    """
    Teams with riders by number on single page
    """
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


def get_image_dict(img_path):
    """
    return a dict with the path, height, width
    """

    image = Image.open(img_path)

    return {
        'path': img_path,
        'height': image.height,
        'width': image.width,
    }


