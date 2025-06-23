"""
Set page layouts (for different orientations?)

Composed of rect 4-tuples with x, y, wid, hei
"""
from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import cm

from ..constants import DATA_DIR
from .Rect import Rect

PORTRAIT = Rect(
    left=1,
    right=20,
    top=28,
    bottom=1
)

MAIN_STAGE = {
    'title': Rect(
        left=PORTRAIT.left + 1,
        bottom=PORTRAIT.top - 3,
        width=PORTRAIT.right - 4.5,
        height=3,
        name='title'
    ),
    'profile': Rect(
        name='profile',
        left=PORTRAIT.left,
        bottom=15,
        width=PORTRAIT.width,
        height=9,
    ),
    'route': Rect(
        name='route',
        left=PORTRAIT.left,
        bottom=PORTRAIT.bottom,
        width=10,
        height=12
    ),
    'climbs': Rect(
        name='climbs',
        left=PORTRAIT.left + 11,
        bottom=PORTRAIT.bottom + 6.5,
        width=PORTRAIT.width - 11,
        height=5.5,
    ),
    'blurb': Rect(
        name='blurb',
        left=PORTRAIT.left + 11,
        bottom=PORTRAIT.bottom,
        width=PORTRAIT.width - 11,
        height=6,
    ),
    # 'climbs': (2, 25, 15, 2)
    # 'route': (2, 25, 15, 2)
    # 'chat': (2, 25, 15, 2)

}

def show_layout(layout=MAIN_STAGE, fp=None):
    """
    Draw each rect (with a label) in the layout
    """
    if fp is None:
        fp = DATA_DIR / 'testing' / "layout.pdf"

    can = Canvas(fp.as_posix())

    for name, rect in layout.items():
        
        # print(rect.name)
        rect.draw(can)
        can.drawString(cm*(rect.x+0.5), cm*(rect.y+0.5),
                       f"{name}: {rect.dims}")

    can.showPage()
    print('saving to', can._filename)
    can.save()
