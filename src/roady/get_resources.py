import requests
from bs4 import BeautifulSoup
import json
import procyclingstats
import sys

from .urls import PCS_MAIN
from .constants import LOG


def get_resource(url, fpath, parser, update=False):
    """
    Base function for returning external resources:
        download if not existing, and save to disk
        else load from disk
        parse using specified parser function
        return required data
    """

    new_data, old_data = None, None

    # get new data if required
    if not fpath.exists() or update:
        # look up the parser function
        func = get_func(parser)
        try:
            new_data = func(url)
            LOG.info(f'loaded {url} with {parser}')
        except:
            LOG.info(f'cant get {url} with {parser}, returning None')
            return None

    # will always want to load existing data if its there
    if fpath.exists():
        with open(fpath, 'r') as fp:
            if fpath.name.endswith('json'):
                old_data = json.load(fp)
            elif fpath.name.endswith('html'):
                old_data = fp.read()

    # if no actually new data to save, just return now
    if new_data is None or new_data == old_data:
        return old_data

    if update and fpath.exists():
        old_path = fpath.parent / f"{fpath.name}.old"
        print('data has changed, saving old data to', old_path)
        save_json_or_html(old_data, old_path)

    # save the new data
    save_json_or_html(new_data, fpath)

    return new_data

def save_json_or_html(data, fpath):
    with open(fpath, 'w') as fp:
        if '.json' in fpath.name:
            json.dump(data, fp, indent=4)
        elif '.html' in fpath.name:
            fp.write(data)


# PARSER FUNCTIONS
def cs_race_data(url):
    """
    Get html and save
    """
    return requests.get(url).text

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

    out = [f"http://www.procyclingstats.com/{x['src']}"
            for x in soup.find_all('img')]

    if not out:
        print('cannot get the pcs profile img urls from main race page')
        return None

    return out


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
    NB parse() method is not available until after race so
    get attrs individually
    """
    st = procyclingstats.Stage(url)

    out = {
        'arrival': st.arrival(),
        'departure': st.departure(),
        'date': st.date(),
        'distance': st.distance(),
        'climbs': st.climbs(),
        'profile_icon': st.profile_icon(),
        'stage_type': st.stage_type(),
        'vertical_meters': st.vertical_meters(),
        'profile_icon': st.profile_icon(),
        'start_time': st.start_time(),
        'url': st.url,
        'pcs_points_scale': st.pcs_points_scale(),
        'profile_score': st.profile_score(),
    }

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
