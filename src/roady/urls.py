import re
import procyclingstats
"""
CS urls have a weirdness where they put 'route' at different places,
depending on if its a grand tour or not.  The main function here takes
care of that:

>>> make_cs_url('tour_2024')
"https://www.cyclingstage.com/tour-de-france-2024-route"

>>> make_cs_url('tour_2024', 4)
"https://www.cyclingstage.com/tour-de-france-2024-route/stage-4-tdf-2024

>>> make_cs_url('basque_2024')
"https://www.cyclingstage.com/tour-de-france-2024-route"

>>> make_cs_url('basque_2024', 4)
"https://www.cyclingstage.com/tour-of-the-basque-country-2024/stage-4-route-eus-2024"

Note that cs img urls are currently all scraped, not constructed like this.


PCS stuff is a lot simpler - see function signature

>>> make_pcs_url('giro_2024', kind='stage', stage_no=8)
'race/giro-d-italia/2024/stage-8'

>>> make_pcs_url('giro_2024', kind='stage_resources', stage_no=6)
'https://www.procyclingstats.com/race/giro-d-italia/2024/stage-6/info/profiles'
"""

CS_BASE = "https://www.cyclingstage.com"

# keeping stage_egs for now, but only fields used are 'main', 'sub', 'grand'
# these should be complete for all tours
CS_PARTS = {
    'uae': {
        'main': 'uae-tour',
        'stage_eg': 'uae-tour-2025/stage-5-route-uae-2025/',
        'sub': 'uae',
        'grand': False,
    },
    'paris-nice': {
        'main': 'paris-nice',
        'stage_eg': 'paris-nice-2025/stage-2-route-pn-2025/',
        'sub': 'pn',
        'grand': False,
    },
    'tirreno-adriatico': {
        'main': 'tirreno-adriatico',
        'stage_eg': 'tirreno-adriatico-2025/stage-1-route-ta-2025/',
		'sub': 'ta',
        'grand': False,
    },
    'catalunya': {
        'main': 'volta-a-catalunya',
        'stage_eg': 'volta-a-catalunya-2025/stage-2-route-cat-2025/',
		'sub': 'cat',
        'grand': False,
    },
    'alps': {
        'main': 'tour-of-the-alps',
        'stage_eg': 'tour-of-the-alps-2025/stage-3-route-tota-2025/',
		'sub': 'tota',
        'grand': False,
    },
    'basque': {
        'main': 'tour-of-the-basque-country',
        'stage_eg': 'tour-of-the-basque-country-2025/stage-2-route-eus-2025/',
		'sub': 'eus',
        'grand': False,
    },
    'romandy': {
        'stage_eg': 'tour-de-romandie-2025/stage-1-route-tdr-2025/',
        'main': 'tour-de-romandie',
		'sub': 'tdr',
        'grand': False,
    },
    'giro': {
        'stage_eg': 'giro-2025-route/stage-3-italy-2025/',
        'main': 'giro',
		'sub': 'italy',
        'grand': True,
    },
    'dauphine': {
        'stage_eg': 'criterium-du-dauphine-2025/stage-5-route-cdd-2025/',
        'main': 'criterium-du-dauphine',
		'sub': 'cdd',
        'grand': False,
    },
    'suisse': {
        'stage_eg': 'tour-de-suisse-2025/stage-4-route-tds-2025/',
        'main': 'tour-de-suisse',
		'sub': 'tds',
        'grand': False,
    },
    'tour': {
        'stage_eg': 'tour-de-france-2025-route/stage-4-tdf-2025/',
        'main': 'tour-de-france',
		'sub': 'tdf',
        'grand': True,
    },
    'vuelta': {
        'stage_eg': 'vuelta-2025-route/stage-4-spain-2025/',
        'main': 'vuelta',
		'sub': 'spain',
        'grand': True,
    },
    'britain': {
        'stage_eg': 'tour-of-britain-2024/stage-2-route-gb-2024/',
        'main': 'tour-of-britain',
		'sub': 'gb',
        'grand': False,
    },
}

def make_cs_url(race, stage_no=None):
    """
    Return main or stage urls for the passed race, eg "giro_2024"

    Pass a stage_no to get the stage url, eg:
        https://www.cyclingstage.com/vuelta-2025-route/stage-4-spain-2025/
        https://www.cyclingstage.com/paris-nice-2025/stage-2-route-pn-2025/

    Otherwise will be the main url (with stage links etc), which is
    just the first part of the stage url actually.

    This function accounts for the oddity that the string 'route' appears
    in different places, depending on if its a grand tour or not.

    For grand tours it appears in the main url, eg:
        https://www.cyclingstage.com/vuelta-2025-route
        https://www.cyclingstage.com/vuelta-2025-route/stage-4-spain-2025/

    For others it doesn't but it DOES get put in the stage
        https://www.cyclingstage.com/paris-nice-2025/
        https://www.cyclingstage.com/paris-nice-2025/stage-2-route-pn-2025/

    Note also that all races have a kind of secondary name that is used
    in the stage urls, eg for paris-nice -> pn
    """

    name, edition = race.split('_')

    data = CS_PARTS[name]

    if data['grand']:
        main_url = f"{CS_BASE}/{data['main']}-{edition}-route"
        if stage_no is not None:
            stage_url = f"{main_url}/stage-{stage_no}-{data['sub']}-{edition}"
            return stage_url
    else:
        main_url = f"{CS_BASE}/{data['main']}-{edition}"
        if stage_no is not None:
            stage_url = f"{main_url}/stage-{stage_no}-route-{data['sub']}-{edition}"
            return stage_url

    return main_url

PCS_URL_BASES = {
    'dauphine': 'race/dauphine/{}',
    'paris-nice': 'paris-nice',
    'basque': 'race/itzulia-basque-country/{}',
    'romandy': 'race/tour-de-romandie/{}',
    'algarve': 'race/volta-ao-algarve/{}',
    'tour': 'race/tour-de-france/{}',
    'giro': 'race/giro-d-italia/{}',
    'vuelta': 'race/vuelta-a-espana/{}',
    'suisse': 'race/tour-de-suisse/{}',
    'uae': 'race/uae-tour/{}',
    'catalunya': 'race/volta-a-catalunya/{}',
    'tirreno-adriatico': 'tirreno-adriatico',
    'alps': 'tour-of-the-alps',
    'britain': 'tour-of-britain',
}

PCS_MAIN = "https://www.procyclingstats.com"


def get_pcs_race_names(rider_name='tadej-pogacar'):
    """
    A handy way to return a big chunk of pcs race names by parsing
    rider results
    """

    res = procyclingstats.RiderResults(
        f"rider/{rider_name}/results").parse()['results']

    return set([x['stage_url'].split('/')[1] for x in res])


def make_pcs_url(race, kind='race', stage_no=None):
    """
    Pass race eg 'tour_2023'
    Return a url
    kinds:
        'race', 'stage', 'climbs', 'startlist', 'route_img',
        'stage_resources'
        (the latter has everything, results etc, but not able to parse yet,
         and much is in the js etc)
    """

    name, edition = race.split('_')

    race_url = PCS_URL_BASES[name].format(edition)

    if kind == 'race':
        return race_url

    if kind == 'stage':
        return "/".join([race_url, f"stage-{stage_no}"])

    if kind == 'climbs':
        return "/".join([race_url, 'route', 'climbs'])

    if kind == 'startlist':
        return "/".join([race_url, 'startlist'])

    if kind == 'route_img':
        if stage_no is None:
            return "/".join([PCS_MAIN, race_url, 'route/overview-map'])
        else:
            # route for stage
            pass

    if kind == 'stage_profile_urls':
            return "/".join([PCS_MAIN, race_url, 'route/stage-profiles'])

    if kind == 'stage_resources':
        # has everything there, but need to parse it
        return "/".join([PCS_MAIN, race_url,
                         f"stage-{stage_no}/info/profiles"])

