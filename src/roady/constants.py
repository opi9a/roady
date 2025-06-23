from pathlib import Path

from my_tools.logging import get_timelog

ROOT = "https://www.cyclingstage.com/"

APP_DIR = Path(__file__).parent.parent.parent
DATA_DIR = APP_DIR / 'data'
LOG_DIR = APP_DIR / 'logs'

LOG = get_timelog(LOG_DIR / 'main.log')


