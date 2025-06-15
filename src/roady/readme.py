"""
refactoring to orient around source scrapes
eg do a cyclingstage scrape just using the main url
this then picks up all sub urls, including img urls,
plus some data like distance, blurb and so on

when doing the whole thing, get this essentially as an api for the cyclingstage data
can pull info from it, and download the imgs

may want to also do a procycling stats equivalent

it caches html, rather than saving stuff to disk at this point (do that later,
though could conceivably do on the fly)

then eg get:
    teams and main data from procycling
    imgs from cyclingstage


current status / todo:
    cyclingstage.Race working
    cyclingstage.Stage scrapes the img urls but not data

todo:
    cyclingstage.Stage data like distance
    cyclingstage.Stage blurb would be useful probably
"""
