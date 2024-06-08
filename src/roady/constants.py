from pathlib import Path

ROOT = "https://www.cyclingstage.com/"

THIS_DIR = Path(__file__).parent
DATA_DIR = Path('~/tour_roadbooks').expanduser()

BASE_URLS = {
    'tour': "/".join([ROOT, "tour-de-france-{}-route/stage-{}-tdf-{}/"]),
    'giro': "/".join([ROOT, "giro-{}-route/stage-{}-italy-{}/"]),
    'vuelta': "/".join([ROOT, "vuelta-{}-route/stage-{}-spain-{}/"]),
    'dauphine': "/".join([ROOT, "criterium-du-dauphine-{}/stage-{}-route-cdd-{}/"]),
}

URL_ELEMENTS = {
    'france': {
        'main': 'tour-de-france',
        'abbr': 'tdf',
    },
    'italy': {
        'main': 'giro',
        'abbr': 'italy',
    },
    'dauphine': {
        'main': 'criterium-du-dauphine',
        'abbr': 'cdd',
    },
    'spain': {
        'main': 'vuelta',
        'abbr': 'xxx',
    },
}

def make_urls(tour, year):
    """ 
    main url
    https://www.cyclingstage.com/tour-de-france-2024-route/

    route url
    https://cdn.cyclingstage.com/images/tour-de-france/2024/route.jpg

    riders url
    https://www.cyclingstage.com/tour-de-france-2024/riders-tdf-2024/

    stage_base
    https://www.cyclingstage.com/tour-de-france-2024-route/stage-3-tdf-2024/

    gpx_base
    https://cdn.cyclingstage.com/images/tour-de-france/2024/stage-1-route.gpx
    """

    elems = URL_ELEMENTS[tour]

    stem = "".join([ROOT, elems['main'], '-', str(year)])

    main = "".join([stem, '-route/'])

    riders = "".join([stem, '/riders-', elems['abbr'], '-', str(year)])

    stage_base = "".join([main, 'stage-{}-', elems['abbr'], '-', str(year)])

    # the remainder use a root of form 'https://cdn.cyclingstage.com'
    cdn_root = "".join([ROOT.replace('www', 'cdn'), 'images/',
                        elems['main'], '/', str(year)])

    route = "".join([cdn_root, '/route.jpg'])

    stage_route_base = "".join([cdn_root,  '/stage-{}-route.jpg'])
    stage_profile_base = "".join([cdn_root,  '/stage-{}-profile.jpg'])
    stage_gpx_base = "".join([cdn_root,  '/stage-{}-route.gpx'])

    return {
        'main': main,
        'riders': riders,
        'route': route,
        'stage_bases': {
            'main': stage_base,
            'route': stage_route_base,
            'profile': stage_profile_base,
            'gpx': stage_gpx_base,
        }
    }
    # https://cdn.cyclingstage.com/images/tour-de-france/2024/stage-6-profile.jpg
    # https://www.cyclingstage.com/tour-de-france-2024-route/stage-3-tdf-2024/
    # https://www.cyclingstage.com/tour-de-france-2024/riders-tdf-2024/
    # https://cdn.cyclingstage.com/images/tour-de-france/2024/route.jpg

