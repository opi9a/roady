from pathlib import Path
import re

from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from PIL import Image
from PIL.ExifTags import TAGS

from .Rect import Rect

def draw_multi(img_fps, canvas=None, fp_out=None,
               **kwargs):
    """ 
    Arrange the images at the passed fps and print them
    kwargs for any formatting stuff eg margins
    """
    # make a canvas to print out independently if one isn't passed
    if canvas is None and fp_out is not None:
        stand_alone = True
        canvas = Canvas(Path(fp_out).as_posix(), pagesize=A4, bottomup=True)
    else:
        stand_alone = False

    cols, rows = {
        1: (1, 2), 2: (1, 2),
        3: (1, 3), 4: (2, 2),
        5: (2, 3), 6: (2, 3),
        7: (2, 4), 8: (2, 4),
    }[len(img_fps)]

    # move left margin in special case of 1 long col
    if len(img_fps) == 2:
        left = 3
    elif len(img_fps) == 3:
        left = 5
    else:
        left = 1

    page = Rect(
        top=28,
        bottom=2,
        left=left,
        right=21,
    )

    print(len(img_fps), 'fps, ', cols, 'cols, ', rows, 'rows')

    cell_h = page.height / rows
    cell_w = page.width / cols

    for i,img in enumerate(img_fps):
        row, col = divmod(i, cols)
        print(f"{i:>2} : col {col}, row{row}")

        rect = Rect(
            top=page.top - (row * cell_h),
            height=cell_h,
            left=page.left + (col * cell_w),
            width=cell_w
        )
        draw_img(img, rect, canvas=canvas)

    canvas.showPage()

    if stand_alone:
        canvas.save()



def draw_img(img_fp, rect, title=None, canvas=None, fp_out=None, margins=0.4,
             font_size=12, font="Helvetica-Bold", title_h=0.3):
    """ 
    Draws the img at the passed fp, plus title, within the passed max coords
    Applies passed margins and accommodates and prints title.
    Returns the dimensions drawn
    """
    # make a canvas to print out independently if one isn't passed
    if canvas is None and fp_out is not None:
        stand_alone = True
        canvas = Canvas(Path(fp_out).as_posix(), pagesize=A4, bottomup=True)
    else:
        stand_alone = False

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

    if stand_alone:
        canvas.showPage()
        canvas.save()

    return actual


def draw_rect_img(img_fp=None, canvas=None, fp_out=None, dims_only=False,
                  rect=None, from_bottom=False, from_right=False):
    """ 
    Draws the img at the passed fp, within the passed max coords
    Returns the dimensions drawn
    """
    # make a canvas to print out independently if one isn't passed
    if canvas is None and fp_out is not None:
        stand_alone = True
        canvas = Canvas(Path(fp_out).as_posix(), pagesize=A4, bottomup=True)
    else:
        stand_alone = False

    # now make scaled versions
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

    if stand_alone:
        canvas.showPage()
        canvas.save()

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

