"""Glass Box event emission (shape copied from the sector-growth-build events of 2026-09-25, schema_version 1).

File name: evt-<UTC yyyyMMddTHHmmss + 7-digit fraction>Z-<10-digit pid>.json, written atomically (temp + rename),
UTF-8 without BOM, compact JSON, keys in the order of the existing events.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import sys
import uuid
from pathlib import Path

from . import config


def _stamp(now: _dt.datetime):
    frac7 = f"{now.microsecond * 10:07d}"
    compact = now.strftime("%Y%m%dT%H%M%S") + frac7 + "Z"
    iso = now.strftime("%Y-%m-%dT%H:%M:%S") + "." + frac7 + "Z"
    return compact, iso


def emit(kind: str, status: str, stage: str, summary: str, run_id: str, correlation_id: str = "",
         parent_id: str = "", detail: str = "", duration_ms: int = -1, cwd: str = "",
         events_dir: Path | None = None, metadata=None) -> str | None:
    """Write one event; returns its id, or None (with a stderr warning) if the event could not be written."""
    events_dir = Path(events_dir or config.GLASSBOX_EVENTS_DIR)
    now = _dt.datetime.now(_dt.timezone.utc)
    compact, iso = _stamp(now)
    eid = f"evt-{compact}-{os.getpid():010d}"
    event = {
        "schema_version": 1,
        "id": eid,
        "timestamp_utc": iso,
        "run_id": run_id,
        "correlation_id": correlation_id or eid,
        "parent_id": parent_id,
        "lane": config.GLASSBOX_LANE,
        "source": config.GLASSBOX_SOURCE,
        "kind": kind,
        "status": status,
        "stage": stage,
        "summary": summary[:320],
        "detail": detail[:2400],
        "cwd": cwd or os.getcwd(),
        "duration_ms": int(duration_ms),
        "bytes": -1,
        "metadata": metadata,
    }
    try:
        events_dir.mkdir(parents=True, exist_ok=True)
        final = events_dir / f"{eid}.json"
        tmp = events_dir / f"{eid}.json.{uuid.uuid4().hex}.tmp"
        tmp.write_bytes(json.dumps(event, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
        os.replace(tmp, final)
        return eid
    except OSError as exc:
        print(f"WARNING: Glass Box event not written ({exc})", file=sys.stderr)
        return None
