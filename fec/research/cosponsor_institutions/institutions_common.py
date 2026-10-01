"""Paths and receipts for the separate institutional-evidence experiment."""
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
ROOT = CODE.parents[2]
OUT = ROOT / 'outputs/cosponsor_institutions_20260905'
UNIVERSE = ROOT / 'outputs/cosponsor_universe_20260905'
OLD = ROOT / 'outputs/cosponsor_challengers_20260905'
REFINEMENT = ROOT / 'outputs/cosponsor_refinement_20260905'
OUT.mkdir(exist_ok=True)
for name in ['cosponsor_universe', 'cosponsor_refinement', 'cosponsor_challengers']:
    sys.path.insert(0, str(CODE.parent / name))


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def log(message):
    line = stamp() + ' ' + message
    print(line, flush=True)
    with (OUT / 'run.log').open('a', encoding='utf-8') as handle:
        handle.write(line + '\n')
