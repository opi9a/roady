from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import cm
import re

from .Rect import Rect
from .layouts import PORTRAIT
from ..Image import draw_img


def make_stage_page(stage, canvas=None, fp=None, gc=False,
                    km_to_go=True, profile_margins=[4, 4]):
    """
    Draw all elements
    """
    if canvas is None:
        can = Canvas(fp.as_posix())
    else:
        can = canvas

    used = {}

    # TITLE
    used['title'] = draw_title(stage, canvas=can)

    # PROFILE
    imgs = stage.imgs()
    if imgs['pcs']['profile'] is not None:
        img_fp = imgs['pcs']['profile'].fpath
    elif imgs['cs']['profile'] is not None:
        img_fp = imgs['cs']['profile'].fpath
    else:
        img_fp is None

    if img_fp is not None:
        used['profile'] = draw_img(
            img_fp=img_fp,
            canvas=can,
            rect=Rect(left=PORTRAIT.left, top=used['title'].bottom - 0.5,
                      width=PORTRAIT.width, height=13),
            trim_bottom_cm=0.4,
            km_to_go=km_to_go,
            profile_margins=profile_margins,
            stage_km=stage.data['distance']
            
        )

    # ROUTE MAP
    if imgs['pcs']['route'] is not None:
        img = imgs['pcs']['route']

    elif imgs['cs']['route'] is not None:
        img = imgs['cs']['route']
    else:
        img = None

    if img is not None:
        # choose rect on basis of whether is wide or tall
        wid, hei = img.width_height

        if wid > hei:  # leave a gap at bottom
            rect = Rect(left=PORTRAIT.left, right=PORTRAIT.right,
                        top=used['profile'].bottom - 1, bottom=5)
            route_tall = False
        else:  # leave a gap on right
            rect = Rect(left=PORTRAIT.left, right=15,
                        top=used['profile'].bottom - 1, bottom=PORTRAIT.bottom,
                        from_bottom=True)
            route_tall = True
        
        used['route'] = draw_img(img_fp=img.fpath, canvas=can, rect=rect)

    else:
        can.setFont('Helvetica-Bold', 18)
        can.drawString(1*cm, used['profile'].bottom - 1, 'no route imgs found')
        used['route'] = used['profile']
        used['route'].bottom -= 1
        route_tall = False

    # CLIMBS
    if route_tall:
        # gap at right for climbs and gc
        climbs_rect = Rect(
            left=used['route'].right + 0.5,
            right=20,
            top=used['route'].top - 1,
            bottom=5
        )
        used['climbs'] = draw_climbs(stage.climbs_df, climbs_rect, can)

        gc_rect = Rect(
            left=used['route'].right,
            right=PORTRAIT.right,
            top=used['climbs'].bottom - 1,
            bottom=PORTRAIT.bottom,
        )

    else:
        # gap at bottom
        climbs_rect = Rect(
            left=1,
            right=10,
            top=used['route'].bottom - 1,
            bottom=1
        )
        used['climbs'] = draw_climbs(stage.climbs_df, climbs_rect, can)
        gc_rect = Rect(
            left=used['climbs'].right,
            right=PORTRAIT.right,
            top=used['climbs'].top,
            bottom=PORTRAIT.bottom,
        )

    if gc:
        df = stage.get_gc_df()
        if df is None:
            print('no gc yet')
        else:
            draw_gc_df(df, can, gc_rect)

    can.showPage()
    if canvas is None:
        print('saving to', fp)
        can.save()

    return used

def draw_climbs(climbs_df, rect, canvas):
    """
    Put the climbs in the passed space
    """
    if climbs_df.empty:
        rect.height = 0
        return rect

    can = canvas

    x = rect.left
    y = rect.top

    can.setFont('Helvetica-Bold', 10)
    can.setFillColor('black')
    ints = [0, 6, 7, 8, 9, 10]
    ints = [i * rect.width / max(ints) for i in ints]
    can.drawString((x + ints[0])* cm, y * cm, 'climb')
    can.drawRightString((x + ints[1])* cm, y * cm, 'start')
    can.drawRightString((x + ints[2])* cm, y * cm, 'peak')
    can.drawRightString((x + ints[3])* cm, y * cm, 'len')
    can.drawRightString((x + ints[4])* cm, y * cm, 'perc')

    can.setFont('Helvetica', 10)
    for km_to_go, cl in climbs_df.iterrows():
        y -= 0.5
        name = sanitize_climb(cl['name'])
        can.drawString((x + ints[0])* cm, y * cm, name[:20])
        can.drawRightString((x + ints[1]) * cm,
                       y * cm, str(cl['start_km_to_go']))
        can.drawRightString((x + ints[2]) * cm, y * cm, str(km_to_go))
        can.drawRightString((x + ints[3]) * cm, y * cm,
                            str(cl['length_km']))
        can.drawRightString((x + ints[4]) * cm, y * cm,
                            str(cl['perc']))

    return Rect(left=rect.left, right=x + ints[4], top=rect.top, bottom=y)


def sanitize_climb(climb_str):
    """
    Drop Col, Cote etc
    """
    return re.sub(r"C[\u00F4|o][t|l]e? d[e|u]s? ", "", climb_str).strip()


def draw_gc_df(df, canvas, rect):
    """
    Put a gc df in the passed rect
    columns: position [df index], rider_name, team_name, gap
    """
    can = canvas
    ints = [0, 1, 8, 13, 13.7]  # nb need a max int for right limit
    ints = [i * (rect.width - 1) / max(ints) for i in ints]

    x = rect.left + 1
    y = rect.top

    can.setFont('Helvetica-Bold', 10)
    can.drawString((x + ints[0])* cm, y * cm, 'pos')
    can.drawString((x + ints[1])* cm, y * cm, 'rider')
    can.drawString((x + ints[2])* cm, y * cm, 'team')
    can.drawString((x + ints[3])* cm, y * cm, 'gap')
    y -= 0.5

    can.setFont('Helvetica', 10)
    for pos, data in df.iterrows():
        can.drawString((x + ints[0])* cm, y * cm, str(pos))
        can.drawString((x + ints[1])* cm, y * cm, data['rider_name'][:12])
        can.drawString((x + ints[2]) * cm, y * cm, data['team_name'][:10])
        can.drawString((x + ints[3]) * cm, y * cm, data['gap'])
        y -= 0.5
        if y < 1:
            break


def draw_title(stage, canvas=None, fp=None):
    """
    Draw all the title gubbins in the passed rect / canvas

    """
    if canvas is None:
        can = Canvas(fp.as_posix())
    else:
        can = canvas

    rect = Rect(left=PORTRAIT.left, right=PORTRAIT.right,
                top=PORTRAIT.top, height=1)

    data = stage.data

    can.setFont('Helvetica-Bold', 16)
    can.drawString((rect.left + 0) * cm,
                   (rect.top - 0) * cm,
                   f"Stage {stage.stage_no}"
                  )
    can.drawCentredString((rect.left + 8) * cm,
                   (rect.top - 0) * cm,
                   f"{data['departure']} -> {data['arrival']}"
                  )

    can.drawRightString((rect.right) * cm,
                   (rect.top - 0) * cm,
                   data['dt'].strftime("%a %b %m")
                  )

    can.setFont('Helvetica', 14)
    can.drawString((rect.left) * cm,
                   (rect.top - 0.7) * cm,
                   f"{data['distance']} km {data['stage_type']}, "
                   f"{data['vertical_meters']}m climbing"
                  )

    if canvas is None:
        can.showPage()
        print('saving to', fp)
        can.save()

    return rect


def get_space(used_dict, page_rect=PORTRAIT):
    """
    NOT USED
    For a passed dict with rects as values,
    return the available space
    """

    # keep track of whats used, from top left
    bottom = page_rect.top
    right = page_rect.left

    for rect in used_dict.values():
        bottom = min(bottom, rect.bottom)
        right = min(right, rect.right)

    return Rect(
        left = right,
        top = bottom,
        right = page_rect.right,
        bottom = page_rect.bottom,
    )
