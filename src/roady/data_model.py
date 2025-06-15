"""
Race:
    xresource     : cs race webpage
    url source    : CS_URL_BASES -> self.cs_url
    cached as     : cs.html
    available data:
        -> route_img_url
        -> stage_urls  # currently the basis for creating list of stages
        -> riders_url <obsolete now use pcs?>
    processed to  :
    in memory as  : cs_html

    xresource     : procyclingstats.Race api
    url source    : PCS_URL_BASES -> self.pcs_url
    cached as     : pcs_data.json
    available data: has a ton of fields, not really used at the moment
                    'category', 'edition', 'enddate',
                    'is_one_day_race', 'name', 'nationality',
                    'prev_editions_select', 'stages', 'stages_winners',
                    'startdate', 'uci_tour', 'year'
    processed to  :
    in memory as  : pcs_data dict

    xresource     : procyclingstats.RaceClimbs api
    url source    : self.pcs_url / route/ climbs
    cached as     : pcs_race_climbs.json
    available data: has full info on all climbs
    processed to  :
    in memory as  : Not held in Race object - is used by Stage objects,
                    which don't have all the info. They load from disk.


    xresource     : procyclingstats profile_img_urls webpage
    url source    : make_pcs_url(kind='stage_profile_urls')
    cached as     : pcs_profile_img_urls.json
    available data: urls for each stage profile.
    processed to  :
    in memory as  : Not held in Race object. These are used by Stage objects,
                    which do have all the pcs img urls but stage profiles
                    are not identified

    xresource     : procyclingstats race webpage 
    url source    : 
    cached as     : 
    available data: pcs overall route img url
    processed to  :
    in memory as  : 
                    

    xresource     : procyclingstats.RaceStartlis api
    url source    : make_pcs_url(kind='startlist')
    cached as     : pcs_startlist.json
    available data: dict of all riders starting
    processed to  : self.teams
    in memory as  : self.teams
                    

Stage:
    number
    cs_url
    pcs_url
    dirpath
    parse() / data
    imgs: dict of Images
    dl_imgs()
    make_pdf()

Image:
    url
    fpath
    download
    img stuff
"""
