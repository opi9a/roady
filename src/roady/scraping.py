"""
Scripts to scrape:
    the list of stages
    the riders
"""
import requests
from bs4 import BeautifulSoup
import re

from .constants import BASE_URLS, ROOT


def get_overview(tour, year, soup=None):
    """
    The list of stages
    """

    long_url = BASE_URLS[tour].format(year, 'x', 'x')

    url = long_url.split('/stage-x')[0]

    req = requests.get(url)

    soup = BeautifulSoup(req.text, 'html.parser')

    tds = soup.find_all('td')

    out = []
    stage = 1
    i = 0
    while i < len(tds):
        print('looking for stage', stage)
        print('line', i)
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


def get_stage_urls(base_url, start=1, end=21):
    """
    Return the main urls
    """

    print('\nGetting stage urls for', base_url)
    out = []
    for stage in range(start, end+1):
        url = base_url.format(stage)
        print(url)
        out.append(url)

    return out


def scrape_stage(url, soup=None, return_soup=False):
    """
    Just get urls of resources?
    """


    stage_no = re.search('stage-(\d*)-', url).groups()[0]
    print('in stage', stage_no)

    if soup is None:
        req = requests.get(url)
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
        "route": None,
        "profile": None,
        "times": None,
        "climbs": None,
        "imap": None,
    }


    title_text = soup.find('h1').text
    out['from_to'] = title_text.split(':')[1].strip()
    out['description'] = description

    # all useful jpegs urls
    jpgs = [
        x['content']
        for x in soup.find_all(attrs={'content': re.compile('cdn.*stage')})
    ]

    for jpg in jpgs:
        if 'route.jpg' in jpg:
            out['route'] = jpg
        if 'profile.jpg' in jpg:
            out['profile'] = jpg

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


