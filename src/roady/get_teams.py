from procyclingstats import RaceStartlist
from .urls import make_pcs_url

"""
I think that to get the underlying list of teams from PCS you have to
use the /teams object from procyclingstats.Stage, eg:

"""


# a list of understandable tags that can be found in full names and
# used in their place
TEAMTAGS = [
    'UAE', 'Visma', 'Jayco', 'Ineos', 'Lidl', 'Decathlon', 'Bahrain',
    'Quick-Step', 'Bora', 'FDJ', 'Alpecin', 'EF', 'Lotto', 'Israel',
    'Cofidis', 'Movistar', 'Arkéa', 'Arkea', 'Intermarché', 'Intermarche',
    'Picnic', 'Astana', 'Uno-X', 'TotalEnergies', 'Tudor',
    'dsm', 'Q36.5', 'Bardiani', 'Polti', 'Vini Fantini', 'Euskatel', 'Euskadi',
    'Burgos',
    'Caja Rural', 'Kern Pharma'
]
def sanitize_team(team):
    """
    Return a good name
    """
    tags = [x for x in TEAMTAGS if x.lower() in team.lower()]

    if tags:
        tag = tags[0]
    else:
        print('cannot find a tag for', team)
        return team

    if tag == 'Israel':
        return 'Genocidal'

    if tag in ['dsm', 'Picnic']:
        return 'Picnic-Post'

    if tag == 'Bardiani':
        return 'Voo Effay Bardiani'

    if tag == 'Euskadi':
        return 'Euskatel'

    if tag == 'FDJ':
        return 'Groupama-FDJ'

    return tag


def make_teams_dict(pcs_json=None, pcs_startlist_url=None,
                    race=None, sanitize=True):
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

        if rider['rider_number'] is None:
            number = len(teams[rider['team_name']]) + 1
        else:
            number = rider['rider_number']

        name = sanitize_rider(rider['rider_name'])
        teams[rider['team_name']][number] = name

    if not sanitize:
        return teams

    out = {}

    for team, riders in teams.items():
        out[sanitize_team(team)] = riders

    return out


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


def sanitize_rider(rider):
    """
    Make them good
    """

    if 'sepp' in rider.lower():
        return 'CUCK Sepp'

    if 'vingegaard' in rider.lower():
        return 'VINEGARED Jonas'

    if 'jhon' in rider.lower():
        return 'NARVAEZ Johnathan'

    if 'remco' in rider.lower():
        return 'REMCO'

    if 'soler' in rider.lower():
        return 'SUNSHINE Mister'

    if 'lipowitz' in rider.lower():
        return 'FLIPPOWITZ Lorian'

    if 'ganna' in rider.lower():
        return 'GAN-NA Filippo'

    return rider

