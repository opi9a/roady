from procyclingstats import RaceStartlist
from .URLS import make_pcs_url

def make_teams_dict(pcs_json=None, pcs_startlist_url=None,
                    race=None):
    """
    Pass the parsing output, return the teams in format for printing

    Usually called by Race object but can just:
    >>> teams = make_teams_dict(race='giro_2023')

    """

    if pcs_json is None:
        if pcs_startlist_url is None:
            pcs_startlist_url = make_pcs_url(race, 'startlist')

        pcs_json = get_pcs_teams(pcs_startlist_url)

    teams = {}

    for rider in pcs_json:
        if rider['team_name'] not in teams:
            teams[rider['team_name']] = {}

        teams[rider['team_name']][rider['rider_number']] = rider['rider_name']

    return teams


def get_pcs_teams(pcs_url):
    """
    Return the native list of rider dicts
    """

    return RaceStartlist(pcs_url).parse()['startlist']


def get_cs_teams(url=None, soup=None, just_return_soup=False):
    """
    Just a back up for the main pcs version above
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
        team_name = elems.pop(0).strip().replace('Israel', 'Genocidal')

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



