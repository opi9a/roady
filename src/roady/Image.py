"""
NOT USED - dev idea
Class to wrap images.  Can create before downloading
Attrs:
    - race (country, year)
    - stage (none means relates to overall)
    - kind (profile, route, other)
    - urls (list of urls to try)
    - log (urls tried, successes)
    - fp (where to put it when dl'd)
    - dims (h, w)
    - exists
"""
from pathlib import Path
import re
import requests
import shutil
from PIL import Image as PILImage

from .constants import LOG

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

    def __init__(self, url, dpath, tag=None,
                 fname=None):
        """
        Hold url and fp for an image, downloading if not already at fp

        used to parse url and assign a type etc but probably better done
        when consuming
        """

        self.url = url
        self.tag = tag

        if fname is None:
            self.fpath = dpath / self.url.split('/')[-1]
        else:
            f_ext = url.split('.')[-1]
            self.fpath = dpath / f"{fname}.{f_ext}"

        if url is not None and not self.fpath.exists():
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

    def draw(x, y, wid, hei, canvas=None):
        """
        Fit the image to the passed dims and draw it on the canvas
        """

    def __repr__(self):
        return f"Image('{self.url.split("/")[-1]}, tag={self.tag}')"

def tag_stage_imgs(urls, pcs_profile_url=None):
    """
    For a list of urls, return a list of {url: xx, tag: yy}
    NB purpose is to assign 'route' and 'profile' tags
    
    For PCS the profile url is known, and may be provided here
    (NB this might be in http, not https lol)
    """

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


def parse_img_url(url):
    """
    Return the salients
    Not currently used by Image but could be useful when making roadbook,
    to help choose images (profile and map especially)
    """

    out = {
        'url': url.split('/')[-1],
        'title': None,  # eg 'route-finale' or 'galibier'
        'type': None,  # eg 'profile'
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

        # only record route and profile, all else is type 'other'
        if title in ['route', 'profile']:
            out['type'] = title
        else:
            out['type'] = 'other'

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

        # only record route and profile, all else is type 'other'
        if out['title'] == 'map':
            out['type'] = 'route'
        elif out['title'] in ['profile', 'overall_route']:
            out['type'] = out['title']
        else:
            out['type'] = 'other'


    return out

def parse_img_url(url):
    """
    Return the salients
    Not currently used by Image but could be useful when making roadbook,
    to help choose images (profile and map especially)
    """

    out = {
        'url': url.split('/')[-1],
        'title': None,  # eg 'route-finale' or 'galibier'
        'type': None,  # eg 'profile'
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

        # only record route and profile, all else is type 'other'
        if title in ['route', 'profile']:
            out['type'] = title
        else:
            out['type'] = 'other'

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

        # only record route and profile, all else is type 'other'
        if out['title'] == 'map':
            out['type'] = 'route'
        elif out['title'] in ['profile', 'overall_route']:
            out['type'] = out['title']
        else:
            out['type'] = 'other'


    return out
