from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import cm

from .Rect import Rect


def make_teams_page(teams, canvas=None, fp_out=None, cols=4,
                    race=None):
    """
    Teams with riders by number on single page
    """

    # make a canvas to print out independently if one isn't passed
    if canvas is None:
        can = Canvas(Path(fp_out).as_posix())
    else:
        can = canvas

    top = 28
    bottom = 2
    left = 2
    right = 21

    pg_h = top - bottom
    pg_w = right - left

    col_w = pg_w / cols
    team_h = pg_h / ((len(teams) // cols) + 1)

    if race is not None:
        can.setFont("Helvetica-Bold", 14)
        name, edition = race.split('_')
        can.drawCentredString(10*cm, top*cm, f"{name} {edition}")
        top -= 1

    # make lines
    i = 0
    for team, riders in teams.items():
        row = i // cols
        col = i % cols

        print_team(
            team,
            riders,
            x=left + (col_w * col),
            y=top - (team_h * row),
            h=team_h, w=col_w, canvas=can
        )
        i += 1

    # its a whole page draw, so do showPage()
    can.showPage()

    if canvas is None:
        print('saving to', can._filename)
        can.save()


def print_team(team, riders, x, y, h, w, canvas):
    """
    Print the individual team in a column
    """
    can = canvas

    x = x * cm
    y = y * cm
    h = h * cm
    w = w * cm

    lh = (h / (len(riders) + 2))

    can.setFont("Helvetica-Bold", 9)
    can.drawString(x, y, team)
    can.setFont("Helvetica", 9)

    i = 1
    for num, rider in riders.items():
        if 'remco' in rider.lower():
            can.setStrokeColor('red')
        new_y = y - (lh * i)
        can.drawString(x, new_y, f"{num:>3} {rider}")
        can.setFont("Helvetica", 9)
        can.setStrokeColor('black')
        i += 1
