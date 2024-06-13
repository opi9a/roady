from pathlib import Path

ROOT = "https://www.cyclingstage.com/"

DATA_DIR = Path('~/tour_roadbooks').expanduser()

URL_ELEMENTS = {
    'france': {
        'main': 'tour-de-france',
        'abbr': 'tdf',
        'stage_base': 'default',
    },
    'italy': {
        'main': 'giro',
        'abbr': 'italy',
        'stage_base': 'default',
    },
    'dauphine': {
        'main': 'criterium-du-dauphine',
        'abbr': 'cdd',
        'stage_base': 'alt',
    },
    'spain': {
        'main': 'vuelta',
        'abbr': 'spain',
        'stage_base': 'default',
    },
    'suisse': {
        'main': 'tour-de-suisse',
        'abbr': 'tds',
        'stage_base': 'alt',
    },
    'basque': {
        'main': 'tour-of-the-basque-country',
        'abbr': 'eus',
        'stage_base': 'alt',
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

    # eg https://www.cyclingstage.com/tour-de-france-2024
    stem = "".join([ROOT, elems['main'], '-', str(year)])

    # eg https://www.cyclingstage.com/tour-de-france-2024-route/
    main = "".join([stem, '-route/'])

    # eg https://www.cyclingstage.com/tour-de-france-2024/riders-tdf-2024
    riders = "".join([stem, '/riders-', elems['abbr'], '-', str(year)])

    if elems['stage_base'] == 'default':
        # eg https://www.cyclingstage.com/tour-de-france-2024-route/stage-{}-tdf-2024
        stage_base = "".join([main, 'stage-{}-', elems['abbr'], '-', str(year)])
    elif elems['stage_base'] == 'alt':
        # eg https://www.cyclingstage.com/criterium-du-dauphine-2024/stage-{}-route-cdd-2024
        stage_base = "".join([stem, '/stage-{}-route-', elems['abbr'], '-', str(year)])

    # the remainder use a root of form 'https://cdn.cyclingstage.com'
    # eg https://cdn.cyclingstage.com/images/tour-de-france/2024
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
