"""
Handy functions used in debugging, rather than do them in ipython
"""

def print_all_img_urls(race, cs=True, pcs=True):
    """
    Print all the img urls
    """
    for stage in race.stages:
        print(f"\nSTAGE {stage.stage_no}")
        print_stage_img_urls(stage, cs, pcs)

def print_stage_img_urls(stage, cs=True, pcs=True):
    """
    Print all the img urls
    """

    if cs:
        print('cs')
        for img in stage.cs_imgs:
            print(img.url.split('/')[-1])

    if pcs:
        print('pcs')
        for img in stage.pcs_imgs:
            print(img.url.split('/')[-1])
