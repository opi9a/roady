"""
Functions for scraping cyclingstage.com
"""
from pathlib import Path
from bs4 import BeautifulSoup
import re
from datetime import datetime

def parse_cs_race_html(html):
    """
    Get:
        stage urls,
        overall route img url,
        riders_url
    """
    out = {
        'stage_urls': [],
        'riders_url': None,
        'route_img_url': None,
    }

    soup = BeautifulSoup(html, 'html.parser')

    # search links for stage and riders urls
    for elem in soup.find_all('a'):

        href = elem.get('href')
        if href is None:
            continue

        if 'riders' in href:
            if 'http' not in href:
                href = f"https://cdn.cyclingstage.com/images{href}"
            out['riders_url'] = href
            continue

        ST_RE = r'stage-(\d*)-'
        stage_re = re.search(ST_RE, href)

        if stage_re is not None and 'route' in href and 'http' in href:
            out['stage_urls'].append(href)

    for elem in soup.find_all('img'):
        url = elem['src']

        if re.search(r'route-.*jpg', url):
            out['route_img_url'] = url.replace('-100', '')

    return out


def parse_cs_stage_html(html):
    """
    The main cs stage data
    Can also get stage urls 
    """

    soup = BeautifulSoup(html, 'html.parser')

    stage_date, description, dt = get_description(soup)

    out = {"date": stage_date, "dt": dt}

    title_text = soup.find('h1').text
    out['from_to'] = title_text.split(':')[1].strip()
    out['description'] = description
    out['parsed_distance'] = infer_km(description)
    out['blurb'] = get_blurb(html)

    jpg_urls = [
        x.get('src') for x in soup.find_all(
            attrs={'src': re.compile('.jpg')})
    ]

    # drop non-stage ones
    jpg_urls = [x for x in jpg_urls if 'stage-' in x]

    # convert to full img from 100 pixel
    jpg_urls = [x.replace('-100', '') for x in jpg_urls]

    out['img_urls'] = jpg_urls

    return out


def get_description(soup):
    """
    This is a bit tricky so separate function
    Returns date, description
    """
    DT_RE = r"(\w*?),?\s(\d{1,2})\s?(\w*?)\s"

    out = soup.find_all('p')[0].text
    weekday, day, month = re.search(DT_RE, out).groups()

    desc = "".join(out.split(month)[1:]).strip()
    desc = re.sub(rf"\s?[{chr(8211)}-]\s", '', desc)

    date = f"{weekday} {day} {month}"
    date = date.replace('dag', 'day').replace('Juli', 'July')
    dt = datetime.strptime(date, "%A %d %B")
    dt = dt.replace(year=datetime.now().year)

    return date, desc, dt.isoformat()


def get_blurb(html):
    """
    The article text (not the headline which is 'description')
    """
    soup = BeautifulSoup(html, 'html.parser')
    paras = soup.find_all('article')[0].find_all('p')
    out = [x.text for x in paras
           if not 'Click on the images' in x.text
           or 'GPX' in x.text]

    return "\n".join(out)


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
