from pathlib import Path
import requests
import shutil
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
    top = 28
    bottom = 2
    left = 2
    right = 21
    width = right - left
    height = top - bottom

    route_h = 14

    i_dict = get_image(img_url, imgs_dir)

    h, w = scale_image(i_dict['height'], i_dict['width'],
                       width, route_h)

    canvas.drawInlineImage(
        i_dict['path'].as_posix(),
        x = 2 * cm,
        y = 15 * cm,
        height = h * cm,
        width = w * cm,
    )

    canvas.setFont("Courier", 8)

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

        prev_stage_dt = dt



    y0 = top - route_h - 1
    lh = min(1, (y0 - bottom) / len(new_stages))
    i = 0
    for stage in new_stages:

        if stage['type'] == 'rest day':
            line = f"{stage['date']:<20}  Rest Day"
            
        else:
            line = (
                f"{stage['date']:<20} {stage['stage_no']:>3} "
                f"{stage['from_to']:<45} {stage['distance']:>4} "
                    f"{stage['type']:>12}"
                )

        canvas.drawString(
            x = 2 * cm,
            y = (y0 - (lh * i)) * cm,
            text = line,
        )

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

    title = (f"Stage {stage_dict['stage_no']}: {stage_dict['date']} "
             f"----- {stage_dict['from_to']}"
             f"  {stage_dict['type']}  : {stage_dict['distance']:.1f} km"
            )
    canvas.drawString(left*cm, top*cm, title)

    i_dict = {}

    i_dict['route'] = get_image(stage_dict['route'], imgs_dir)
    i_dict['profile'] = get_image(stage_dict['profile'], imgs_dir)

    h, w = scale_image(
        i_dict['route']['height'],
        i_dict['route']['width'],
        max_h = 15,
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
        y = (top - (2 + i_dict['profile']['plot_height']))*cm,
        height = i_dict['profile']['plot_height'] * cm,
        width = i_dict['profile']['plot_width'] * cm,
    )

    if 'route' in stage_dict.keys():
        y = top - (
                2 # allowance for title
                + i_dict['profile']['plot_height']
                + 2 # gap
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


