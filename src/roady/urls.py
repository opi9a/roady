import re

# note irregularity
CS_URL_BASES = {
    'dauphine': 'https://www.cyclingstage.com/criterium-du-dauphine-{}/',
    'tour': 'https://www.cyclingstage.com/tour-de-france-{}-route/',
    'vuelta': 'https://www.cyclingstage.com/vuelta-{}-route/',
    'giro': 'https://www.cyclingstage.com/giro-{}-route/',
}

PCS_URL_BASES = {
    'dauphine': 'race/dauphine/{}',
    'tour': 'race/tour-de-france/{}',
    'giro': 'race/giro-d-italia/{}',
    'vuelta': 'race/vuelta-a-espana/{}',
}

PCS_MAIN = "https://www.procyclingstats.com"


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


def infer_name_edition_stage(cs_url):
    """
    From a cyclinstage url
    """
    name, edition, stage_no = None, None, None

    if 'tour-de-france' in cs_url: name = 'tour'
    elif 'dauphine' in cs_url: name = 'dauphine'
    elif 'vuelta' in cs_url: name = 'vuelta'
    elif 'giro' in cs_url: name = 'giro'
    elif 'romandy' in cs_url: name = 'romandy'

    edition = int(re.search(r'20(\d\d)', cs_url).groups()[0]) + 2000

    stage_no = re.search(r'stage-(\d{1,2})-', cs_url).groups()[0]

    return name, edition, stage_no

        
