"""Research-only paths; earlier experiments and production remain read-only."""
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

CODE=Path(__file__).resolve().parent
ROOT=CODE.parents[2]
OLD=ROOT/'outputs/cosponsor_challengers_20260905'
PREVIOUS=ROOT/'outputs/cosponsor_refinement_20260905'
OUT=ROOT/'outputs/cosponsor_universe_20260905'
OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(CODE.parent/'cosponsor_refinement'))
sys.path.insert(0,str(CODE.parent/'cosponsor_challengers'))


def stamp():return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def read_json(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path,value):Path(path).write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')


def log(message):
    line=stamp()+' '+message;print(line,flush=True)
    with (OUT/'run.log').open('a',encoding='utf-8') as f:f.write(line+'\n')
