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

from .draw_img import draw_rect_img, stand_alone, draw_km_to_go, draw_img
from .Rect import Rect


@stand_alone
def make_front_page(stages, img_fp, canvas=None, fp_out=None, tour=None, year=None, no_map=False):
    """
    List of stages and map
    Pass no_map = True to not print that jpg eg to save ink
    """
    top = 29
    bottom = 2
    left = 1
    right = 20
    width = right - left

    title_h = 1.5
    route_h = 17


    # title - have to infer tour and year
    if tour is None and year is None:
        tour, year = re.search(
            r"roadbooks/(\S*)_(\d*)/route.jpg", str(img_fp)).groups()

    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString((left + 5) * cm, (top - title_h) * cm,
                      text=f"{tour} {year}")


    rect = Rect(top=(top - title_h - 0.5), height=14, right=right, left=left)
    # route map
    if not no_map:
        route_dims = draw_rect_img(
            img_fp=img_fp,
            canvas=canvas,
            rect=rect,
        )


    new_stages = []

    prev_stage_dt = None
    for stage in stages:
        dt = datetime.fromisoformat(stage['dt'])

        if prev_stage_dt is not None:
            gap = (dt - prev_stage_dt).days
        else:
            gap = 1

        if gap > 1:
            new_dt = dt - timedelta(days=1)
            new_stages.append({'type': 'rest day', 
                               'weekday': new_dt.strftime("%a"),
                               'date': new_dt.strftime("%d %b")})
        new_stages.append(stage)
        new_stages[-1]['stage_no'] = str(new_stages[-1]['stage_no'])
        new_stages[-1]['distance'] = str(new_stages[-1]['distance'])
        new_stages[-1]['weekday'] = dt.strftime("%a")
        new_stages[-1]['date'] = dt.strftime("%d %b")

        prev_stage_dt = dt


    # stages
    y0 = top - route_h - title_h + 2 # this is frigged tbf
    lh = min(1, (y0 - bottom) / len(new_stages))

    # column headings
    col_xs = {
        'weekday': 2,
        'date': 3,
        'stage_no': 4.5,
        'from_to': 5.5,
        'distance': 14,
        'type': 16,
    }

    canvas.setFont("Helvetica-Bold", 10)

    for col, x in col_xs.items():
        if col == 'from_to':text = "from-to"
        elif col == 'weekday': text = "date"
        elif col == 'date': text = ""
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
            canvas.setFillAlpha(0.5)
            canvas.drawString(col_xs['weekday'] * cm, y * cm, text=stage['weekday'])
            canvas.drawString(col_xs['date'] * cm, y * cm, text=stage['date'])
            canvas.drawString(col_xs['stage_no'] * cm, y * cm,
                              text=f'{"-"*48} REST DAY {"-"*48}')
            i += 1
            canvas.setFillAlpha(1)
            continue

        for col, x in col_xs.items():
            canvas.drawString(x * cm, y * cm, text=stage[col] or 'not found')

        i += 1

    canvas.showPage()

# def calibrate_profile():
#     # PROFILE
#     rect = Rect(top=(top - top_margin), height=14, right=right, left=left)
#     print('rect in scale', rect.height / rect.width)
#     prof_rect = draw_rect_img(
#         img_fp=Path(stage_dirpath) / 'profile.jpg',
#         canvas=canvas,
#         rect=rect
#     )

@stand_alone
def make_stage_page(stage_dict, stage_dirpath, canvas=None, fp_out=None, 
             km_to_go=False, l_kms_marg=0, r_kms_marg=0, 
             start_finish_km_only=False, calibrate_profile=False):
    """
    Compose a pdf page for a stage.
    Pass a canvas or an outpath
    l_kms_marg and r_kms_marg for aligning the kms to go with start and
    end within profile img
    start_finish_km_only just shows those, for aligning / debug

    test with a stage dict element of roady and its dirpath
    on disk eg rd.stages[4],
               DATA_DIR / 'france_25/stages/stage_3'
    """

    x, y = 0, 0

    top = 27
    bottom = 1
    left = 2
    right = 18
    top_margin = 1

    # TITLE
    canvas.setFont("Helvetica-Bold", 20)
    title = (f"Stage {stage_dict['stage_no']} - {stage_dict['date']}")
    canvas.drawString((left + 4.5)*cm, top*cm, title)

    # PROFILE
    rect = Rect(top=(top - top_margin), height=14, right=right, left=left)
    print('rect in scale', rect.height / rect.width)
    prof_rect = draw_rect_img(
        img_fp=Path(stage_dirpath) / 'profile.jpg',
        canvas=canvas,
        rect=rect
    )

    print('prof_rect scale', prof_rect.height / prof_rect.width)

    # calibration
    # add lines to manually check where km0 / finish are
    if calibrate_profile:
        mm_inward = 31
        seg_l = 0.4
        i = 0
        canvas.setFontSize(3)
        canvas.setStrokeColor('red', alpha=0.5)

        while i < mm_inward:

            x_left = prof_rect.left + (i * 0.1)
            x_right = rect.right - (i * 0.1)
            cal_top = prof_rect.bottom + 3

            # mm marks above
            canvas.drawCentredString(
                x_left*cm, (cal_top+0.1)*cm, str(i%10))
            canvas.drawCentredString(
                x_right*cm, (cal_top+0.1)*cm, str(i%10))

            for j in range(10):

                l_top = cal_top - (j * seg_l)

                # left scale
                canvas.line((x_left + (j * 0.01)) * cm,
                            l_top * cm,
                            (x_left + (j * 0.01)) * cm,
                            (l_top - seg_l) * cm,
                            )

                # right scale
                canvas.line((x_right - (j * 0.01)) * cm,
                            l_top * cm,
                            (x_right - (j * 0.01)) * cm,
                            (l_top - seg_l) * cm,
                            )
                
                if i == 0:
                    # tenth of mm marks on side
                    canvas.drawString(
                        (x_left - 0.1) *cm,
                        (cal_top - ((j + 0.5) * seg_l)) *cm,
                        str(j%10))
                    canvas.drawString(
                        (x_right + 0.1) *cm,
                        (cal_top - ((j + 0.5) * seg_l)) *cm,
                        str(j%10))


            i += 1

        # canvas.showPage()
        return


    # ADD A TO-GO SCALE TO THE PROFILE
    # set up dimensions and location of to-go scale

    # get the stage distance, d, and the width of the image
    # draw a vertical line each 10km from end
    scale_l = left + l_kms_marg
    scale_r = left + prof_rect.width - r_kms_marg
    scale_w = scale_r - scale_l

    # if drawing the scale, check distance is available
    if km_to_go:
        try:
            distance = float(stage_dict['distance'])
        except:
            km_to_go = False
            distance = None

    # draw the scale
    if km_to_go and not start_finish_km_only:
        draw_km_to_go(
            canvas=canvas,
            start_x=scale_r, scale_w=scale_w,
            stage_km=distance,
            y0=prof_rect.bottom,
            y1=prof_rect.top,
            minor_unit=1,
        )
    
    # debug only
    elif start_finish_km_only:
        canvas.setStrokeColor("red")
        canvas.line(
            scale_l * cm,  # x1
            prof_rect.bottom * cm,
            scale_l * cm,  # x2
            prof_rect.top * cm,
        )
        canvas.line(
            scale_r * cm,  # x1
            prof_rect.bottom * cm,
            scale_r * cm,  # x2
            prof_rect.top * cm,
        )

    canvas.setFillAlpha(1)

    # ROUTE
    route_dims = draw_rect_img(
        img_fp=stage_dirpath / 'route.jpg',
        canvas=canvas,
        rect=Rect(bottom=bottom, height=10, right=right, left=left),
    )

    # ends the page
    canvas.showPage()



@stand_alone
def make_teams_page(teams, canvas=None, fp_out=None, cols=4):
    """
    Teams with riders by number on single page
    """

    # make a canvas to print out independently if one isn't passed
    if canvas is None:
        stand_alone = True
        canvas = Canvas(Path(fp_out).as_posix(), pagesize=A4, bottomup=True)
    else:
        stand_alone = False

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

    if stand_alone:
        canvas.save()

@stand_alone
def draw_multi_page(img_fps, canvas=None, fp_out=None,
               **kwargs):
    """ 
    Arrange the images at the passed fps and print them
    kwargs for any formatting stuff eg margins
    """

    if len(img_fps) > 10:
        print('have too many imgs in this stage')
        print('will omit:')
        for img in img_fps[10:]:
            print(img.name)

        img_fps = img_fps[:9]


    cols, rows = {
        1: (1, 2), 2: (1, 2),
        3: (1, 3), 4: (2, 2),
        5: (2, 3), 6: (2, 3),
        7: (2, 4), 8: (2, 4),
        8: (2, 5), 9: (2, 5),
        10: (3, 4), 11: (3, 4),
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
    canvas.drawString(x, y, team.replace('Israel', 'Genocidal'))

    
    i = 1
    for num, rider in riders.items():
        new_y = y - (lh * i)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(x, new_y, f"{num:>3} {rider}")
        i += 1


