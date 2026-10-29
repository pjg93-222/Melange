# -*- coding: utf-8 -*-
"""One bill, one member, one category, in BOTH the archive and the verified Sentinel Bill Ledger.

Since `--keys-file` a tracked bill can be classifier-admitted, so build_archive_legislative.py can now
see the same (member, bill, Congress, category) as an archive row AND a ledger membership row. The
row loop must score that event once, keep the strongest role, and mark the other row duplicate-*.
The sentinel admission direction (SA.scoring_directions) must set the sign of the kept event.

The producer is a module-level script, so it is driven as a subprocess against a tiny tmp_path root
(MONEYBALL_ROOT); the only seam is a driver that swaps SA.load for a minimal admission document
(the real loader needs a hash-bound evidence generation). Pytest-native, tmp_path-only.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
FEC = ROOT / "fec"
SCRIPT = FEC / "legislation" / "build_archive_legislative.py"

MEMBER, BILL, CONGRESS, CATEGORY, ADMISSION_SIGN = "Richard Durbin", "H.R.2155", 119, "CFPB", -1
ROLE_WEIGHT = {"sponsor": 3.0, "original-cosponsor": 2.0, "cosponsor": 1.0}

DRIVER = """
import json, os, runpy, sys
sys.path.insert(0, {fec!r})
from legislation import sentinel_admissions as SA
SA.load = lambda root, **kw: json.load(open(os.path.join(root, 'admissions.json'), encoding='utf-8'))
runpy.run_path({script!r}, run_name='__main__')
"""


def _write_root(root, archive_role, ledger_role):
    """Tiny fixture root. Either source may be omitted by passing None."""
    (root / "data" / "engine").mkdir(parents=True)
    (root / "data" / "legislation").mkdir(parents=True)
    (root / "data" / "engine" / "congestion.json").write_text(
        json.dumps([{"member": MEMBER, "bioguide": "D000563"}]), encoding="utf-8")
    (root / "bill_repository_live.json").write_text('{"bills": {}}', encoding="utf-8")
    (root / "data" / "legislation" / "bill_directions.csv").write_text("Bill,Direction,Congress\n", encoding="utf-8")
    # Admission document: only what scoring_directions() reads.
    (root / "admissions.json").write_text(json.dumps({
        "bills": {"119:hr:2155": {"display": BILL, "congress": CONGRESS}},
        "decisions": {"119:hr:2155": {"categories": [{"category": CATEGORY, "direction": ADMISSION_SIGN}]}},
    }), encoding="utf-8")
    # The producer fails closed unless the sign-on letter evidence is present (296 rows / 7 letters / 251 members).
    letters = pd.DataFrame({
        "Category": CATEGORY, "Bill": ["LTR-%d" % (i % 7) for i in range(300)],
        "Member": ["%s %s" % (chr(97 + i // 26), chr(97 + i % 26) * 3) for i in range(300)],
    })
    letters.to_csv(root / "manual_bill_evidence.csv", index=False)
    archive = pd.DataFrame([{"Member": MEMBER, "Name": BILL, "Congress": CONGRESS, "Section": CATEGORY,
                             "Role": archive_role, "Title": "Test Act", "LastAction": "", "DecayWeight": 1.0,
                             "CosponsorCount": 0, "DetailLink": "", "bill_summary": ""}]
                           if archive_role else [], columns=["Member", "Name", "Congress", "Section", "Role", "Title",
                                                              "LastAction", "DecayWeight", "CosponsorCount",
                                                              "DetailLink", "bill_summary"])
    archive.to_excel(root / "congress_bills_archive_20260101_000000.xlsx", sheet_name="All Bills", index=False)
    ledger = pd.DataFrame([{"Member": MEMBER, "Bill": BILL, "Congress": CONGRESS, "Section": CATEGORY,
                            "Role": ledger_role, "Title": "Test Act", "Scoring Eligible": True,
                            "Review Status": "verified", "Record Type": "membership"}]
                          if ledger_role else [], columns=["Member", "Bill", "Congress", "Section", "Role", "Title",
                                                           "Scoring Eligible", "Review Status", "Record Type"])
    ledger.to_excel(root / "Sentinel Bill Ledger.xlsx", sheet_name="Sentinel Bill Ledger", index=False)


def _run(tmp_path, name, archive_role, ledger_role):
    root = tmp_path / name
    root.mkdir()
    _write_root(root, archive_role, ledger_role)
    env = dict(os.environ, MONEYBALL_ROOT=str(root), LEG_SPONSOR_FROM_COLUMN="0", CU_IDENTITY_FIX="1",
               PYTHONIOENCODING="utf-8")
    proc = subprocess.run([sys.executable, "-c", DRIVER.format(fec=str(FEC), script=str(SCRIPT))],
                          cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=180)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    leg = json.loads((root / "archive_leg.json").read_text(encoding="utf-8"))
    audit = json.loads((root / "legislation_routing_audit.json").read_text(encoding="utf-8"))
    rows = [r for r in audit["rows"] if r.get("bill") == BILL]
    return leg.get(MEMBER, {}).get(CATEGORY), rows, audit


@pytest.mark.parametrize("name,archive_role,ledger_role,single,kept_role,duplicate", [
    # single = (archive_role, ledger_role) of the one-source run holding the surviving row alone.
    ("same_role", "sponsor", "sponsor", ("sponsor", None), "sponsor", "duplicate-same-role"),
    ("ledger_original_stronger", "cosponsor", "original", (None, "original"), "original-cosponsor",
     "duplicate-lower-role"),
    ("archive_original_stronger", "original-cosponsor", "cosponsor", ("original-cosponsor", None),
     "original-cosponsor", "duplicate-lower-role"),
])
def test_archive_and_ledger_row_for_same_event_count_once(tmp_path, name, archive_role, ledger_role, single,
                                                          kept_role, duplicate):
    # The single-row contribution is the oracle: the strongest role's weight, signed by the admission.
    expected = ADMISSION_SIGN * ROLE_WEIGHT[kept_role]
    single_total, single_rows, _ = _run(tmp_path, name + "_single", *single)
    assert single_total == expected, single_rows

    total, rows, audit = _run(tmp_path, name + "_both", archive_role, ledger_role)

    assert len(rows) == 2, rows
    assert total == expected, "double count: got %r, one event is %r; rows=%r" % (total, expected, rows)
    assert audit["selected_events"] == 1
    kept = [r for r in rows if r["disposition"] == "selected"]
    dups = [r for r in rows if r["disposition"].startswith("duplicate-")]
    assert len(kept) == 1 and len(dups) == 1, rows
    assert dups[0]["disposition"] == duplicate
    assert kept[0]["effective_role"] == kept_role and dups[0]["selected_role"] == kept_role
    # Admission direction applies to both rows alike, so the kept event carries the admission sign.
    for row in rows:
        assert row["sign"] == ADMISSION_SIGN
        assert row["direction_mechanism"] == "automated-official-evidence-policy"
    assert kept[0]["contribution"] == expected
