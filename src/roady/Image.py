from pathlib import Path
import re
import requests
import shutil
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import cm
from PIL import Image as PILImage

from .constants import LOG, DATA_DIR
from .drawing.Rect import Rect

"""
DATA MODEL

xresource     : pcs_imgs, cs_imgs webpages (or cdn..)
url source    : parent object (stage / race)
cached as     : img file (jpg / png)
available data: image file, url (and data in it), fp
processed to  : n/a
in memory as  : dict with url and data parsed from it, plus fp
"""


class Image:

    def __init__(self, url, dpath, tag=None, fname=None):
        """
        Hold url and fp for an image, downloading if not already at fp

        used to parse url and assign a type etc but probably better done
        when consuming
        """

        self.url = url
        self.tag = tag
        self.fpath = None

        if url is not None:
            if fname is None:
                self.fpath = dpath / self.url.split('/')[-1]
            else:
                f_ext = url.split('.')[-1]
                self.fpath = dpath / f"{fname}.{f_ext}"

            if not self.fpath.exists():
                self.download(fname)

        self._width_height = None

    @property
    def width_height(self):
        if self._width_height is None:
            i_dict = PILImage.open(self.fpath)
            self._width_height = i_dict.width, i_dict.height
        return self._width_height

    def download(self, fname=None):
        """
        Try the url
        """

        req = requests.get(self.url, stream=True)

        if not req.ok:
            LOG.info(f"cannot download image from {self.url}")
            return

        LOG.info(f"got image from {self.url}")
        with open(self.fpath, 'wb') as fp:
            shutil.copyfileobj(req.raw, fp)

        del req

    def __repr__(self):
        return f"Image('{self.url.split("/")[-1]}'', tag={self.tag}')"


def draw_img(img_fp, rect, canvas=None, fp_out=None,
             trim_bottom_cm=None,
             km_to_go=False, profile_margins=None, stage_km=None,
             add_calibration=False, cal_lims=None):
    """
    Draws the img, fitting to within the passed max coords
    Returns the dimensions actually drawn, in a rect
    """
    if canvas is None:
        can = Canvas(fp_out.as_posix())
    else:
        can = canvas

    # make scaled versions
    # take in image -> h, w and rect to draw in h, w
    # create a 3rd rect to actually draw
    i_dict = PILImage.open(img_fp)
    # print('image in - h:', img_h, 'w:', img_w, 'shape:', img_h/img_w)
    s_h, s_w = scale_image(
        i_dict.height, i_dict.width, rect.height, rect.width)
    # print('scaled -> w:', s_w, 'h:', s_h)

    actual = Rect(left=rect.left, top=rect.top, height=s_h, width=s_w)
    # print('actual shape to draw in:', actual.shape)

    if not rect.from_bottom:
        actual.top = rect.top
        actual.bottom = actual.top - s_h
    else:
        actual.bottom = rect.bottom
        actual.top = actual.bottom + s_h

    if not rect.from_right:
        actual.left = rect.left
        actual.right = actual.left + s_w
    else:
        actual.right = rect.right
        actual.left = actual.right - s_w

    # actually draw it
    can.drawInlineImage(
        img_fp.as_posix(),
        x=actual.left * cm,
        y=actual.bottom * cm,
        height=actual.height * cm,
        width=actual.width * cm,
    )

    if trim_bottom_cm is not None:
        can.setFillColor('white')
        can.setStrokeColor('white')
        can.rect(
            x=actual.left * cm,
            y=actual.bottom * cm,
            height=trim_bottom_cm * cm,
            width=actual.width * cm,
            fill=True
        )
        actual.bottom += trim_bottom_cm

    if add_calibration:
        calibrate(can, actual, cal_lims)
    elif km_to_go:
        add_to_go_scale(can, actual, profile_margins, stage_km=stage_km)

    if canvas is None:
        can.showPage()
        print('saving canvas to', can._filename)
        can.save()

    return actual


def add_to_go_scale(canvas, rect, margins, stage_km,
                    start_finish_km_only=False):
    """
    Draw on a km to go scale.
    Adjust inwards using tuple of left and right margins from calibration (mm)
    Pass the actual img rect
    TO COMPLETE
    """

    # ADD A TO-GO SCALE TO THE PROFILE
    # set up dimensions and location of to-go scale

    # get the stage distance, d, and the width of the image
    # draw a vertical line each 10km from end
    breakpoint()
    scale_l = rect.left + (margins[0] / 10)
    scale_r = rect.right - (margins[1] / 10)
    scale_width = scale_r - scale_l
    minor_unit = 1

    # work out the decrement for the chosen interval (kms)
    dec_1k = scale_width / float(stage_km)
    decrement = dec_1k * minor_unit

    canvas.setStrokeColor("lightblue")
    canvas.setFontSize(8)

    k_to_go = 0
    line_x = scale_r
    y0 = rect.bottom
    y1 = rect.top

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
                (line_x - x_nudge)* cm,
                y1 * cm,  # y2
                str(k_to_go)
            )
        # at bottom, 0 and 10 overlap the stage length in img
            if k_to_go >= 20:
                canvas.setFillColor("steelblue", alpha=0.9)  # for text
                canvas.drawString(
                    (line_x - x_nudge)* cm,
                    (y0-0.2)* cm,
                    # (y_start-0.2)* cm,
                    str(k_to_go)
                )

        k_to_go += minor_unit
        line_x -= decrement


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


def calibrate(canvas, rect, lims=None):
    """
    Add calibration marks
    Lims are (mm down from top, mm up from bottom)
    """
    if lims is None:
        lims = (5, 0.5)

    cal_top = rect.top - lims[0]
    cal_bottom = rect.bottom + lims[1]
    mm_inward = 31
    seg_l = (cal_top - cal_bottom) / 10
    i = 0
    canvas.setFontSize(3)
    canvas.setStrokeColor('red', alpha=0.5)

    while i < mm_inward:

        x_left = rect.left + (i * 0.1)
        x_right = rect.right - (i * 0.1)
        # cal_top = rect.bottom + 3
        # cal_bottom = cal_top - (seg_l * 10)

        # mm marks above
        canvas.drawCentredString(
            x_left * cm, (cal_top + 0.1) * cm, str(i % 10))
        canvas.drawCentredString(
            x_right * cm, (cal_top + 0.1) * cm, str(i % 10))
        # mm marks below
        canvas.drawCentredString(
            (x_left + 0.1) * cm, (cal_bottom - 0.1) * cm, str((i + 1) % 10))
        canvas.drawCentredString(
            (x_right - 0.1) * cm, (cal_bottom - 0.1) * cm, str((i + 1) % 10))

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
                    (x_left - 0.1) * cm,
                    (cal_top - ((j + 0.5) * seg_l)) * cm,
                    str(j % 10))
                canvas.drawString(
                    (x_right + 0.1) * cm,
                    (cal_top - ((j + 0.5) * seg_l)) * cm,
                    str(j % 10))


        i += 1

    return


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


TEST_IMG_FP = Path('~/shared/my_packages/roady/data/dauphine_2025/',
                   'stage_1/dauphine-2025-stage-1-profile-n2-ed0465bf55e713e16c31.jpg')


def test_draw(rect, img_fp=TEST_IMG_FP,
              fp_out=DATA_DIR / 'testing' / 'draw_img.pdf'):

    can = Canvas(fp_out.as_posix())

    actual = draw_img(img_fp, rect=rect, canvas=can,
                      add_calibration=True)

    # can.setStrokeColor('black')
    # rect.draw(canvas=can)

    # can.setStrokeColor('grey')
    # actual.draw(canvas=can)

    print(actual)
    can.showPage()
    can.save()


def tag_stage_imgs(urls, pcs_profile_url=None):
    """
    For a list of urls, return a list of {url: xx, tag: yy}
    NB purpose is to assign 'route' and 'profile' tags

    For PCS the profile url is known, and may be provided here
    (NB this might be in http, not https lol)
    """

    if not urls:
        print('no urls to tag')
        return

    imgs = {url: split_img_url(url) for url in urls}
    source = list(imgs.values())[0]['source']

    out = []  # will be a list of {'url': url, 'tag': tag}

    profile, route = False, False

    # first the case where a profile url is provided
    if pcs_profile_url is not None:
        url = pcs_profile_url.replace("http://", "https://")
        if url in imgs:
            out.append({'url': url, 'tag': 'profile'})
            del imgs[url]

        profile = True

    if not profile:
        for url, elems in imgs.items():
            if elems['title'] == 'profile':
                out.append({'url': url, 'tag': 'profile'})
                del imgs[url]
                break

    # now the route
    for url, elems in imgs.items():
        if elems['title'] in ['route', 'map']:
            out.append({'url': url, 'tag': 'route'})
            del imgs[url]
            break

    # for pcs, it might be the first profile remaining
    if profile and not route and source == 'pcs':
        for url, elems in imgs.items():
            if elems['title'] == 'profile':
                out.append({'url': url, 'tag': 'route'})
                del imgs[url]
                break

    # tag remaining urls as other
    for url, elems in imgs.items():
        out.append({'url': url, 'tag': 'other'})

    return out


def split_img_url(url):
    """
    Return the salient elements of the url, splitting out recognizable
    elements like f_ext.
    Does not attempt to assign a type, but the naively reported title
    may be the same as the type, especially for cs.
    """

    out = {
        'url': url.split('/')[-1],
        'title': None,  # eg 'route-finale' or 'galibier'
        'source': None,  # 'cs' or 'pcs'
        'f_ext': url.split('.')[-1],
        'ind': None,  # pcs has this
        'extra_payload': None,  # catch-all
    }

    if 'cyclingstage.com' in url:

        out['source'] = 'cs'

        # this filters out the overall route img
        if 'stage-' not in url:
            title, f_ext = out['url'].split('.')
            stage = None

        else:
            stage, title, f_ext = re.search(
                r'stage-(\d{1,2})-(.*)\.(\w*)', url).groups()

        out['title'] = title
        out['stage'] = stage
        out['f_ext'] = f_ext

    elif 'procyclingstats.com' in url:
        out['source'] = 'pcs'

        # this filters out the overall route img
        if 'stage-' not in url and 'map' in url:
            out['f_ext'] = out['url'].split('.')[-1]
            out['title'] = 'overall_route'
            out['stage'] = None

        else:
            stage, payload, f_ext = re.search(
                r'stage-(\d{1,2})-(.*)\.(\w*)', url).groups()

            elems = payload.split('-')

            for elem in elems:
                if elem in ['map', 'profile', 'finish', 'climb']:
                    out['title'] = elem
                if len(elem) == 2:  # i think always of form eg n2
                    out['ind'] = elem
                else:
                    out['extra_payload'] = elem

            out['stage'] = stage

    return out
