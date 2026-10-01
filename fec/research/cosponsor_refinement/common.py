"""Read frozen phase-one inputs; write only this refinement's artifacts."""
import datetime as dt
import json
from pathlib import Path
import sys

CODE = Path(__file__).resolve().parent
ROOT = CODE.parents[2]
ORIGINAL_CODE = CODE.parent / "cosponsor_challengers"
sys.path.insert(0, str(ORIGINAL_CODE))
from audit_data import digest

OLD = ROOT / "outputs/cosponsor_challengers_20260905"
OUT = ROOT / "outputs/cosponsor_refinement_20260905"
OUT.mkdir(parents=True, exist_ok=True)


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def log(message):
    line = stamp() + " " + str(message)
    print(line, flush=True)
    with (OUT / "run.log").open("a", encoding="utf-8") as f:
        f.write(line + "\n")
