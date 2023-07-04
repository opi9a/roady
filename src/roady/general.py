import re
import json
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas

from .constants import DATA_DIR, BASE_URLS
from .make_pdf import make_pdf, make_front_pages
from .scraping import (get_overview, get_riders,
                       get_stage_urls, scrape_stage)


"""
Just type:
    >>> make_roadbook('tour', 2023)
to make a roadbook and save it in the DATA_DIR
also saves stuff like imgs so don't have to redo

TODO:
    - overview / front page:
        - scrapes overall route img, rider list and stage list
          but doesn't make pdf fully (just does img I think)
    - the rest is pretty good

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

    # get riders list
    riders_url = make_riders_url(tour, year)
    riders = get_riders(riders_url)

    # get overall route url
    tour_map_url = make_tour_map_url(tour, year)

    make_front_pages(stages_list, tour_map_url, riders, 
                     canvas, imgs_dir=imgs_dir) 

    print('stage', end=" ")
    for i, stage in enumerate(stages_list):
        make_pdf(stage, canvas=canvas, imgs_dir=imgs_dir)
        print(i+1, end=" ", flush=True)
    print()

    canvas.save()


def make_tour_map_url(tour, year, imgs_dir=None):
    """
    Return the url
    """

    if tour == 'tour':
        tour = 'tour-de-france'

    return f"https://cdn.cyclingstage.com/images/{tour}/{year}/route.jpg"


def make_riders_url(tour, year):
    """
    Return the url
    """

    base = BASE_URLS[tour].format(year, year, year)

    return base.replace(f"-route/stage-{year}-", "/riders-")


def make_stages_list(tour, year):
    """
    Get the urls, then scrape each to make jsons of resources
    Also scrapes the front page overview which has info on length,
    type of stage etc.
    """

    base = BASE_URLS[tour].format(year, {}, year)

    urls = get_stage_urls(base)

    stages = [scrape_stage(url) for url in urls]

    overview = get_overview(tour, year)

    assert len(stages) == len(overview)

    for i, stage in enumerate(stages):
        stage['date2'] = overview[i]['date']
        stage['title2'] = overview[i]['title']
        stage['distance'] = overview[i]['distance']
        stage['type'] = overview[i]['type']

    return stages


