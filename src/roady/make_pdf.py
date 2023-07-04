from pathlib import Path
import requests
import shutil
from reportlab.lib.pagesizes import A4

from reportlab.lib.colors import blue, black, red, green, grey
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas

from PIL import Image
from PIL.ExifTags import TAGS


def make_front_pages(stage_dict, img_url, riders, canvas, imgs_dir=None):
    """
    List of stages and map
    """
    i_dict = get_image(img_url, imgs_dir)

    h, w = scale_image(i_dict['height'], i_dict['width'],
                       20, 16)

    canvas.drawInlineImage(
        i_dict['path'].as_posix(),
        x = 2*cm,
        y = 15*cm,
        height = h * cm,
        width = w * cm,
    )

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
