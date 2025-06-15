import requests
from bs4 import BeautifulSoup
import json
import procyclingstats
import sys

from .urls import PCS_MAIN
from .constants import LOG


def get_resource(url, fpath, parser):
    """
    Base function for returning external resources:
        download if not existing, and save to disk
        else load from disk
        parse using specified parser function
        return required data
    """

    if not fpath.exists():
        # look up the parser function
        try:
            out = get_func(parser)(url)
            LOG.info(f'loaded {url} with {parser}')
        except:
            LOG.info(f'cant get {url} with {parser}, returning None')
            return None

        with open(fpath, 'w') as fp:
            if fpath.name.endswith('json'):
                json.dump(out, fp, indent=4)
            elif fpath.name.endswith('html'):
                fp.write(out)
    else:
        with open(fpath, 'r') as fp:
            if fpath.name.endswith('json'):
                out = json.load(fp)
            elif fpath.name.endswith('html'):
                out = fp.read()

    return out


# PARSER FUNCTIONS
def html(url):
    """
    Just request the html for passed url
    """
    return requests.get(url).text


def pcs_race_api(url):
    """
    API call
    """
    return procyclingstats.Race(url).parse()


def pcs_race_climbs_api(url):
    """
    API call
    """
    return procyclingstats.RaceClimbs(url).parse()['climbs']


def pcs_profile_img_urls(url):
    """
    Scrape a pcs webpage that has all the stage profiles
    """
    req = requests.get(url)
    soup = BeautifulSoup(req.text, 'html.parser')

    return [f"http://www.procyclingstats.com/{x['src']}"
            for x in soup.find_all('img')]


def pcs_route_img_url(url):
    """
    Scrape a pcs webpage that has the overall route, among other stuff.
    """

    req = requests.get(url)
    soup = BeautifulSoup(req.text, 'html.parser')
    imgs = [f"{PCS_MAIN}/{x['src']}" for x in soup.find_all('img')]

    return imgs[0]


def pcs_startlist(url):
    """
    Just scrape the html and return it
    """
    return procyclingstats.RaceStartlist(
        url).parse()['startlist']


def pcs_stage_api(url):
    """
    API call
    will often fail silently for events in future
    """
    try:
        out = procyclingstats.Stage(url).parse()
    except:
        print(f'cannot parse procyclingstats.Stage({url})', end=" ")
        print('- probably because data not there yet')
        return dict()
    return out


def pcs_stage_img_urls(url):
    """
    Scrape pcs stage webpage that has all the stage imgs

    NB route/map and profile often mislabelled which is annoying.
    There is a field / file in Race which has all the pcs profiles, which
    helps for that.
    May be able to infer from this what file the route is
    """
    req = requests.get(url)
    soup = BeautifulSoup(req.text, 'html.parser')

    imgs = [f"{PCS_MAIN}/{x['src']}" for x in soup.find_all('img')]

    return imgs


def get_func(func_name):
    """
    Look up and return the passed func_name from this module
    """
    return sys.modules[__name__].__dict__[func_name]
