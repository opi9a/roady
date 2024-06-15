from pathlib import Path
import re

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from PIL import Image
from PIL.ExifTags import TAGS

from .Rect import Rect

""" 
Functions for drawing elements only
Will not call showPage unless as stand_alone
"""

def stand_alone(func):
    """ 
    Decorator which allows a drawing func to either use the canvas passed
    or make its own and complete printing to that
    """

    # this is what will actually be run when calling func
    def wrapper(*args, **kwargs):
        # make a canvas if reqd
        if kwargs.get('canvas') is None and kwargs.get('fp_out') is not None:
            stand_alone = True
            canvas = Canvas(Path(kwargs['fp_out']).as_posix(), pagesize=A4, bottomup=True)
            out = func(*args, canvas=canvas, **kwargs)
        else:
            stand_alone = False
            out = func(*args, **kwargs)

        if stand_alone:
            canvas.showPage()
            canvas.save()

        return out
    
    return wrapper


@stand_alone
def draw_img(img_fp, rect, title=None, canvas=None, fp_out=None, margins=0.4,
             font_size=12, font="Helvetica-Bold", title_h=0.3):
    """ 
    Draws the img at the passed fp, plus title, within the passed max coords
    Applies passed margins and accommodates and prints title.
    Returns the dimensions drawn
    does not showPage
    """
    if title is None:
        title = infer_title(str(img_fp))

    # print the title
    canvas.setFont(font, font_size)
    canvas.drawString(
        (rect.left + title_h) * cm,
        (rect.top - margins) * cm,
        text=title
    )

    actual = Rect(
        top=rect.top - title_h - (margins * 1),
        bottom=rect.bottom + margins,
        left=rect.left + margins,
        right=rect.right - margins,
    )

    draw_rect_img(img_fp, canvas, rect=actual)

    return actual


@stand_alone
def draw_rect_img(img_fp=None, canvas=None, fp_out=None, dims_only=False,
                  rect=None, from_bottom=False, from_right=False):
    """ 
    Draws the img at the passed fp, within the passed max coords
    Returns the dimensions drawn
    does not showPage
    """
    # make scaled versions
    i_dict = Image.open(img_fp)
    s_h, s_w = scale_image(i_dict.height, i_dict.width, rect.height, rect.width)

    actual = Rect(height=s_h, width=s_w)

    if not from_bottom:
        actual.top = rect.top
        actual.bottom = rect.top - s_h
    else:
        actual.bottom = rect.bottom
        actual.top = rect.bottom + s_h

    if not from_right:
        actual.left = rect.left
        actual.right = rect.left + s_h
    else:
        actual.right = rect.right
        actual.left = rect.right - s_h

    # actually draw it
    if not dims_only:
        canvas.drawInlineImage(
            img_fp.as_posix(),
            x = actual.left * cm,
            y = (actual.top - actual.height) * cm,
            height = actual.height * cm,
            width = actual.width * cm,
        )

    return actual


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

def infer_title(uri):
    """ 
    From passed fp (or url?) return an inferred title.
    Usually means a climb.
    """

    pattern = re.compile(r"stage-\d{1,2}-(.*?)\.jpg")
    match = re.search(pattern, uri)
    res = match.groups()
    out = res[0].replace('-', ' ')

    return out

