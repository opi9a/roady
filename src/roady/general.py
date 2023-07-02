import requests
import re
from bs4 import BeautifulSoup
import json
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from .constants import ROOT, DATA_DIR
from .make_pdf import make_pdf


BASE_URLS = {
    'tour': "/".join([ROOT, "tour-de-france-{}-route/stage-{}-tdf-{}/"]),
    'giro': "/".join([ROOT, "giro-{}-route/stage-{}-italy-{}/"]),
    'vuelta': "/".join([ROOT, "vuelta-{}-route/stage-{}-spain-{}/"]),
}

"""
eg:
    stage_urls = get_stage_urls()

    outs = [scrape_stage(url) for url in stage_urls]

    dump_to_file(outs, TXT_FP)

"""


def make_roadbook(tour, year, data_dir=None):
    """
    Does everything
    """

    if data_dir is None:
        data_dir = DATA_DIR
    else:
        data_dir = Path(data_dir)

    tour_dir = data_dir / f'{tour}_{year}'
    imgs_dir = tour_dir / 'imgs'

    if not tour_dir.exists():
        print('creating dir', tour_dir)
        tour_dir.mkdir()

    if not imgs_dir.exists():
        print('creating dir', imgs_dir)
        imgs_dir.mkdir()

    jsons_path = tour_dir / 'stages.json'

    if not jsons_path.exists():
        stages_list = make_stages_list(tour, year)
        with open(jsons_path, 'w') as fp:
            json.dump(stages_list, fp, indent=4)

    else:
        with open(jsons_path, 'r') as fp:
            stages_list = json.load(fp)

    print(f'\nHave {len(stages_list)} stages')

    pdf_fp = tour_dir / 'roadbook.pdf'
    print('Now making roadbook pdf at', pdf_fp)

    canvas = Canvas(pdf_fp.as_posix(), pagesize=A4, bottomup=True)

    print('stage', end=" ")
    for i, stage in enumerate(stages_list):
        make_pdf(stage, canvas=canvas, imgs_dir=imgs_dir)
        print(i+1, end=" ", flush=True)
    print()

    canvas.save()


def make_stages_list(tour, year):
    """
    Get the urls, then scrape each to make jsons of resources
    """

    base = BASE_URLS[tour].format(year, {}, year)

    urls = get_stage_urls(base)

    stages = [scrape_stage(url) for url in urls]

    return stages


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

    out = {}

    stage_date, description = get_description(soup)

    out['date'] = stage_date
    out['stage_no'] = int(stage_no)

    title_text = soup.find('h1').text
    out['from_to'] = title_text.split(':')[1].strip()
    out['description'] = description

    # all useful jpegs
    jpgs = soup.find_all(attrs={'content': re.compile('cdn.*stage')})

    pattern = f'stage-{stage_no}-(.*).jpg'
    for jpg in jpgs:
        jpg_url = jpg['content']
        res = re.search(pattern, jpg_url)
        if res is not None:
            out[res.groups()[0]] = jpg_url

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


