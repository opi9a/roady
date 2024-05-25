from pathlib import Path

ROOT = "https://www.cyclingstage.com"

THIS_DIR = Path(__file__).parent
DATA_DIR = Path('~/tour_roadbooks').expanduser()

BASE_URLS = {
    'tour': "/".join([ROOT, "tour-de-france-{}-route/stage-{}-tdf-{}/"]),
    'giro': "/".join([ROOT, "giro-{}-route/stage-{}-italy-{}/"]),
    'vuelta': "/".join([ROOT, "vuelta-{}-route/stage-{}-spain-{}/"]),
}

