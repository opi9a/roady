from pathlib import Path
import re

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import cm

from my_tools.pdf.pdf_tools import stand_alone

from PIL import Image
from PIL.ExifTags import TAGS

from .Rect import Rect

""" 
Functions for drawing elements only
Will not call showPage unless as stand_alone
"""

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

    if img_fp.exists():
        draw_rect_img(img_fp, canvas, rect=actual)
    else:
        canvas.rect(actual.left*cm,
                    actual.bottom*cm,
                    actual.width*cm,
                    actual.height*cm)
        canvas.drawstring(
            (actual.left+0.5)*cm,
            (actual.top-0.5)*cm,
            f'file {img_fp} doesnt exist'
        )

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
    # take in image -> h, w and rect to draw in h, w
    # create a 3rd rect to actually draw
    i_dict = Image.open(img_fp)
    img_h = i_dict.height
    img_w = i_dict.width
    print('image in - h:', img_h, 'w:', img_w, 'shape:', img_h/img_w)
    s_h, s_w = scale_image(i_dict.height, i_dict.width, rect.height, rect.width)
    print('scaled -> w:', s_w, 'h:', s_h)

    actual = Rect(left=rect.left, top=rect.top, height=s_h, width=s_w)
    print('actual shape to draw in:', actual.shape)

    # if not from_bottom:
    #     actual.top = rect.top
    #     actual.bottom = rect.top - s_h
    # else:
    #     actual.bottom = rect.bottom
    #     actual.top = rect.bottom + s_h

    # if not from_right:
    #     actual.left = rect.left
    #     actual.right = rect.left + s_h
    # else:
    #     actual.right = rect.right
    #     actual.left = rect.right - s_h

    # actually draw it
    if not dims_only:
        canvas.drawInlineImage(
            img_fp.as_posix(),
            x = actual.left * cm,
            y = actual.bottom * cm,
            height = actual.height * cm,
            width = actual.width * cm,
        )

    return actual

@stand_alone
def draw_km_to_go(canvas, start_x, scale_w, stage_km, y0, y1,
                   minor_unit=1):
    """
    Make the togo scale
    """
    # work out the decrement for the chosen interval (kms)
    dec_1k = scale_w / float(stage_km)
    decrement = dec_1k * minor_unit

    canvas.setStrokeColor("lightblue")
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
            canvas.setFillColor("lightblue", alpha=0.9)  # for text
            canvas.drawString(
                (line_x - x_nudge)*cm,
                y1 * cm,  # y2
                str(k_to_go)
            )
        # at bottom, 0 and 10 overlap the stage length in img
            if k_to_go >= 20:
                canvas.setFillColor("steelblue", alpha=0.9)  # for text
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

    return out


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

