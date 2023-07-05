from pathlib import Path
import requests
import shutil
import re
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4

from reportlab.lib.colors import blue, black, red, green, grey
from reportlab.lib.units import cm

from PIL import Image
from PIL.ExifTags import TAGS


def make_front_page(stages, img_url, canvas, imgs_dir=None):
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
    tour, year = re.search("images/(\S*)/(\d*)/route.jpg", img_url).groups()
    tour = tour.title().replace('-', ' ').replace("De", "de")

    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString((left + 5) * cm, (top - title_h) * cm,
                      text=f"{tour} {year}")


    # route map
    i_dict = get_image(img_url, imgs_dir)

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
        'stage_no': 5.5,
        'from_to': 6.5,
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
            canvas.drawString(x * cm, y * cm, text=stage[col])

        i += 1

    canvas.showPage()


def make_pdf(stage_dict, canvas=None, outpath=None, imgs_dir=None):
    """
    Pass a canvas or an outpath

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

    canvas.setFont("Helvetica-Bold", 20)
    title = (f"Stage {stage_dict['stage_no']} - {stage_dict['date']}")
    canvas.drawString((left + 4.5)*cm, top*cm, title)

    i_dict = {}

    i_dict['route'] = get_image(stage_dict['route'], imgs_dir)
    i_dict['profile'] = get_image(stage_dict['profile'], imgs_dir)

    h, w = scale_image(
        i_dict['route']['height'],
        i_dict['route']['width'],
        max_h = 14,
        max_w = right - left,
    )

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
    canvas.drawInlineImage(
        i_dict['profile']['path'].as_posix(),
        x = left*cm,
        y = (top - (1 + i_dict['profile']['plot_height']))*cm,
        height = i_dict['profile']['plot_height'] * cm,
        width = i_dict['profile']['plot_width'] * cm,
    )

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


def get_image(url, dirpath):
    """
    download the image and return a dict with the path, height, width
    """

    img_path = Path(dirpath) / Path(url).name

    if not img_path.exists():
        req = requests.get(url, stream=True)
        print('downloading', url, end="..")
        
        with open(img_path, 'wb') as fp:
            shutil.copyfileobj(req.raw, fp)

        print('OK')

        del req

    image = Image.open(img_path)

    return {
        'path': img_path,
        'height': image.height,
        'width': image.width,
    }


def scale_image(i_h, i_w, max_h, max_w):
    """
    For passed image height and width, and max values,
    return the height and width to print
    """

    # image too tall, scale to max height
    if i_h / i_w > max_h / max_w:
        return max_h, i_w * (max_h / i_h)

    # too wide, scale to max width
    return i_h * (max_w / i_w), max_w


def print_teams(teams, canvas, cols=4):
    """
    xx
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
        canvas.drawString(x, new_y, f"{num:>3}, {rider}")
        i += 1


