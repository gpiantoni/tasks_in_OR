from pathlib import Path
from collections.abc import Mapping


SCRIPT_DIR = Path(__file__).resolve().parent
TASKS_DIR = SCRIPT_DIR / 'tasks'
CONFIG_DIR = SCRIPT_DIR / 'configurations'
DEFAULTS_JSON = SCRIPT_DIR / 'default.json'
SOUNDS_DIR = SCRIPT_DIR / 'sounds'
LOG_DIR = SCRIPT_DIR / 'log'


def update(d, u):
    for k, v in u.items():
        if isinstance(v, Mapping):
            d[k] = update(d.get(k, {}), v)
        else:
            d[k] = v
    return d
