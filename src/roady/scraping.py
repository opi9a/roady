"""
Scripts to scrape:
    the list of stages
    the riders
"""
import requests
from bs4 import BeautifulSoup
import re
import shutil

from .constants import ROOT


def get_stages_overview(url=None, soup=None):
    """
    The list of stages, with date, title, distance, type
    """

    if soup is None:
        req = requests.get(url)
        soup = BeautifulSoup(req.text, 'html.parser')

    tds = soup.find_all('td')

    out = []
    stage = 1
    i = 0
    while i < len(tds):
        td = tds[i]
        cl = td.get('class', [None])[0]

        if td.text == str(stage) and cl == 'left':
            out.append({
                'stage': stage,
                'date': tds[i+1].text,
                'title': tds[i+2].text.split(str(stage))[-1].strip(),
                'distance': float(tds[i+3].text.replace(',', '.')),
                'type': tds[i+4].text,
            })
            i += 5
            stage += 1
        else:
            i += 1

    return out


def get_teams(url=None, soup=None, just_return_soup=False):
    """
    Return a dict of riders with numbers by team
    """

    if soup is None:
        req = requests.get(url)
        soup = BeautifulSoup(req.text, 'html.parser')

        if just_return_soup:
            return soup

    # this makes a list of block elements, one per team
    blocks = soup.find_all(attrs={'class': 'block'})

    teams = {}
    for block in blocks:
        team = block.find('i').text
        teams[team] = {}

        riders_str = block.text.split(team)[1]
        riders = re.split(" \d{1,3}\.? ", riders_str)[1:]
        numbers = re.split("\D*\s", riders_str)[1:-1]

        teams[team] = dict(zip(numbers, riders))

    return teams

def xget_teams(url=None, soup=None, just_return_soup=False):
    """
    Return a dict of riders with numbers by team
    """

    if soup is None:
        req = requests.get(url)
        soup = BeautifulSoup(req.text, 'html.parser')

        if just_return_soup:
            return soup

    # this makes a list of block elements, one per team
    itals = soup.find_all('i')

    teams = {}
    for ital in itals:
        team = ital.text
        # teams[team] = {}

        riders_str = ital.next_sibling.next_sibling
        # riders = [x.strip() for x in riders_str.split(",")]
        riders = {
            str(i+1): x.strip()
            for i,x in enumerate(riders_str.split(","))
        } 
        # numbers = re.split"\D*\s", riders_str[1:-1]

        # teams[team] = dict(zip(numbers, riders))
        teams[team] = riders

    return teams


def scrape_stage(url, soup=None, return_soup=False):
    """
    Gets available info from the stage url.
    (Much of this not used yet)
    """

    stage_no = re.search('stage-(\d*)-', url).groups()[0]

    if soup is None:
        req = requests.get(url)

        if not req.ok:
            return None

        soup = BeautifulSoup(req.text, features='html.parser')
        
        if return_soup:
            return soup

    stage_date, description = get_description(soup)

    out = {
        "url": url,
        "date": stage_date,
        "stage_no": int(stage_no),
        "from_to": None,
        "description": None,
        "times": None,
        "climbs": None,
        "imap": None,
        "extra_jpgs": None,
    }

    title_text = soup.find('h1').text
    out['from_to'] = title_text.split(':')[1].strip()
    out['description'] = description

    # scheduled times
    res = soup.find(attrs={'title': re.compile('scheduled')})

    if res:
        out['times'] = ROOT + res['data-cb']
    else:
        out['times'] = None

    # climbs
    res = soup.find(attrs={'title': re.compile('climbs')})

    try:
        out['climbs'] = ROOT + res['data-cb']
    except:
        out['climbs'] = None

    # the interactive map
    res = soup.find(attrs={'title': re.compile('interactive')})

    if res:
        out['imap'] = ROOT + res['data-cb']
    else:
        out['imap'] = None

    # get all poss useful jpgs
    # replace '-100' which makes it a thumbnail I think
    # this will prob include route.jpg, profile.jpg which are sorted elsewhere
    jpgs = [x['src'].replace('-100', '') for x in soup.find_all('img')
            if "jpg" in x['src']
            and f"stage-" in x['src']]

        
    out['extra_jpgs'] = [j for j in jpgs if not
                   (j.endswith('-profile.jpg') or j.endswith('-route.jpg'))]

    return out


def get_description(soup):
    """
    This is a bit tricky so separate function
    Returns date, description
    """

    out = soup.find_all(attrs={'itemprop': 'headline'})[1].text
    date = out.split(' - ')[0].strip()
    desc = out[(len(date) + 2):].strip()

    return date, desc


def download_img(url, img_fp):
    """ 
    Download an img from the requested url and save to fp
    """
    req = requests.get(url, stream=True)
    print('img downloading', url, end="..")
    
    with open(img_fp, 'wb') as fp:
        shutil.copyfileobj(req.raw, fp)

    print('OK')

    del req


