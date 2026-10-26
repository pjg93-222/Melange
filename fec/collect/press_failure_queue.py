"""Press site-failure queue: the hand-off from the unattended refresh to a Claude session (D-294).

Paul's ruling: a press 403 (or any one site being unavailable) must never fail the whole run; log
it and send it to Claude for adjustment.  The R collector records each unavailable member site in
``press_site_failures.json`` beside the run's receipt (the receipt itself is untouched).  After a
sealed walk the stream wrapper calls ``record_run``, which upserts those failures into
``data/press/press_failure_queue.ndjson`` and writes ``press_site_failure_receipt.json`` into the
run folder.  Process the queue as ``collect/PRESS_FAILURE_TRIAGE.md`` says.

One row per (member_id, url, error_class).  The file is rewritten atomically on every update, but
no row is ever removed: a failure that stops recurring becomes ``recovered``, a Claude-handled one
``adjusted`` (with a note), and either re-opens if the same key fails again.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paths import ROOT  # noqa: E402

QUEUE_PATH = os.path.join(ROOT, "data", "press", "press_failure_queue.ndjson")
FAILURES_ARTIFACT = "press_site_failures.json"
RECEIPT_ARTIFACT = "press_site_failure_receipt.json"
FAILURES_SCHEMA = "press-site-failures-v1"
RECEIPT_SCHEMA = "press-site-failure-receipt-v1"


def _key(row):
    return (row["member_id"], row["url"], row["error_class"])


def _read(path):
    path = Path(path)
    if not path.is_file():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except ValueError as error:
            # Refuse rather than rewrite around a damaged line: history is never dropped.
            raise ValueError("%s line %d is not JSON (%s); repair it, the queue is not rewritten"
                             % (path, number, error)) from error
    return rows


def _write(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".%d.tmp" % os.getpid())
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(str(tmp), str(path))


def upsert(failures, run_id, now=None, queue_path=None):
    """Fold one run's failures into the queue; returns the full row list."""
    path = queue_path or QUEUE_PATH
    stamp = (now or datetime.now(timezone.utc)).isoformat()
    rows = _read(path)
    index = {_key(row): row for row in rows}
    seen = set()
    for failure in failures:
        key = _key(failure)
        seen.add(key)
        row = index.get(key)
        if row is None:
            row = {"member_id": failure["member_id"], "url": failure["url"],
                   "error_class": failure["error_class"], "first_seen": stamp,
                   "consecutive_runs": 0, "run_id": None}
            index[key] = row
            rows.append(row)
        if row["run_id"] != run_id:           # the same run recorded twice counts once
            row["consecutive_runs"] = row["consecutive_runs"] + 1 if row.get("status") == "open" else 1
        row.update(status="open", last_seen=stamp, run_id=run_id,
                   source=failure.get("source"), http_status=failure.get("http_status"),
                   last_error=str(failure.get("last_error") or "")[:300])
    for row in rows:                          # a sealed run that did not fail this key: it recovered
        if _key(row) not in seen and row.get("status") == "open" and row.get("run_id") != run_id:
            row.update(status="recovered", consecutive_runs=0)
    _write(path, rows)
    return rows


def open_count(queue_path=None):
    try:
        return sum(1 for row in _read(queue_path or QUEUE_PATH) if row.get("status") == "open")
    except (OSError, ValueError):
        return -1                             # unreadable: say so, never report a clean zero


def record_run(run_root, queue_path=None, now=None):
    """Ingest ``run_root``'s collector file; returns the receipt dict, or None with no file."""
    run_root = Path(run_root)
    source = run_root / FAILURES_ARTIFACT
    if not source.is_file():
        return None
    document = json.loads(source.read_text(encoding="utf-8"))
    if document.get("schema") != FAILURES_SCHEMA:
        raise ValueError("unexpected press site failures schema in %s" % source)
    failures = document.get("failures") or []
    path = queue_path or QUEUE_PATH
    upsert(failures, run_root.name, now, path)
    receipt = {"schema": RECEIPT_SCHEMA, "run_id": run_root.name,
               "generated_at": (now or datetime.now(timezone.utc)).isoformat(),
               "status": "PARTIAL" if failures else "CLEAN",
               "failures_this_run": len(failures),
               "press_failures_open": open_count(path), "queue_path": str(path),
               "failures": failures}
    tmp = run_root / (RECEIPT_ARTIFACT + ".part")
    tmp.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(run_root / RECEIPT_ARTIFACT))
    return receipt
