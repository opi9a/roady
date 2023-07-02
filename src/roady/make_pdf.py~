from pathlib import Path
import requests
import shutil
from reportlab.lib.pagesizes import A4

from reportlab.lib.colors import blue, black, red, green, grey
from reportlab.lib.units import cm
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.styles import ParagraphStyle


from .constants import THIS_DIR

IMG_DIR = THIS_DIR / 'imgs'


def make_pdf(stage_dict, canvas=None, outpath=None, imgs_dir=None):
    """
    Pass a canvas or an outpath

    """

    file_output = False
    if canvas is None:
        out_fp = Path(outpath).as_posix()
        canvas = Canvas(out_fp, pagesize=A4, bottomup=True)
        file_output = True


    x, y = 0, 0

    top = 27*cm
    bottom = 2*cm
    left = 2*cm
    right = 18*cm

    title = (f"Stage {stage_dict['stage_no']}: {stage_dict['date']} "
             f"----- {stage_dict['from_to']}")
    canvas.drawString(left, top - 1, title)

    h2 = 10*cm
    canvas.drawInlineImage(
        get_image(stage_dict['profile'], imgs_dir).as_posix(),
        x = left,
        y = 2*cm,
        width = right - left,
        height = h2,
    )

    h1 = 13*cm
    if 'route' in stage_dict.keys():
        canvas.drawInlineImage(
            get_image(stage_dict['route'], imgs_dir).as_posix(),
            x = left,
            y = top - (4*cm) - h2,
            width = right - left,
            height = h1,
        )

    # ends the page
    canvas.showPage()

    if file_output:
        canvas.save()


def get_image(url, dirpath):
    """
    download the image
    """

    img_path = Path(dirpath) / Path(url).name

    if not img_path.exists():
        req = requests.get(url, stream=True)
        print('downloading', url, end="..")
        
        with open(img_path, 'wb') as fp:
            shutil.copyfileobj(req.raw, fp)

        print('OK')

        del req

    return img_path


