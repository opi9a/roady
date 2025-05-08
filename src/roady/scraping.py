"""
Scripts to scrape:
    the list of stages
    the riders
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import shutil

from .constants import ROOT


def get_stages_overview(url=None, soup=None):
    """
    The list of stages, with date, title, distance, type
    """

    if soup is None:
        req = requests.get(url)
        if not req.ok:
            raise ValueError("cannot download image from", url)

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
    NB numbers may not be available before, so some pissing about reqd
    """

    if soup is None:
        req = requests.get(url)

        if not req.ok:
            raise ValueError("cannot download teams from", url)

        soup = BeautifulSoup(req.text, 'html.parser')

        if just_return_soup:
            return soup

    # this makes a list of block elements, one per team
    blocks = soup.find_all(class_='block')

    teams = {}
    for block in blocks:
        elems = re.split(r"\s(\d{1,3}\.)", block.text)
        team_name = elems.pop(0).strip()

        nums, riders = [], []
        for i, elem in enumerate(elems):
            if i % 2 == 0:
                num = int(elem.replace('.', ''))
                nums.append(num)
            else:
                riders.append(elem.strip())

        teams[team_name] = {num: rider
                            for num, rider in zip(nums, riders)}
        
    return teams



def scrape_stage(url, soup=None, return_soup=False):
    """
    Gets available info from the stage url.
    (Much of this not used yet)
    """

    stage_no = re.search(r'stage-(\d*)-', url).groups()[0]

    if soup is None:
        req = requests.get(url)

        if not req.ok:
            print('cannot get a stage from', url)
            return None

        soup = BeautifulSoup(req.text, features='html.parser')
        
        if return_soup:
            return soup

    stage_date, description, dt = get_description(soup)

    out = {
        "url": url,
        "date": stage_date,
        "dt": dt,
        "stage_no": int(stage_no),
        "from_to": None,
        "description": None,
        "parsed_distance": None,
        "times": None,
        "climbs": None,
        "imap": None,
        "extra_jpgs": None,
    }

    title_text = soup.find('h1').text
    out['from_to'] = title_text.split(':')[1].strip()
    out['description'] = description
    out['parsed_distance'] = infer_km(description)

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
    DT_RE = r"(\w*?),\s(\d{1,2})\s?(\w*?)\s"

    out = soup.find_all('p')[0].text
    weekday, day, month = re.search(DT_RE, out).groups()

    desc = "".join(out.split(month)[1:]).strip()
    desc = re.sub(rf"\s?[{chr(8211)}-]\s", '', desc)


    date = f"{weekday} {day} {month}"
    dt = datetime.strptime(date, "%A %d %B")
    dt = dt.replace(year = datetime.now().year)

    return date, desc, dt.isoformat()


def download_img(url, img_fp):
    """ 
    Download an img from the requested url and save to fp
    """
    req = requests.get(url, stream=True)

    if not req.ok:
        raise ValueError("cannot download image from", url)

    print('img downloading', url, end="..")
    
    with open(img_fp, 'wb') as fp:
        shutil.copyfileobj(req.raw, fp)

    print('OK')

    del req


def infer_km(description):
    """ 
    Its in there as eg "153.2 kilometres to go"
    """

    match = re.search(re.compile(r"\d{1,3}\.?\d*\s*kilomet"),
                      description)

    if match:
        res = match.group()
        out = res.split(' ')[0]

        if out.replace('.', '').isnumeric():
            return float(out)

    print('cannot infer km')

