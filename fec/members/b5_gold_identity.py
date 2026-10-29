# -*- coding: utf-8 -*-
"""Fail-closed stable-identity joins for the frozen Senate personality panels."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import hashlib
from pathlib import Path
import re

from .b5_gold_identity_registry import (
    APPENDIX_PDF_SHA256,
    REFERENCE_COMMIT,
    SOURCE_NAME_TO_BIOGUIDE,
)

PANEL_NAMES = ("senate_insiders", "academic_experts")


def registry_sha256():
    """Hash the bundled registry, not a runtime data-root copy."""
    return hashlib.sha256(
        Path(__file__).with_name("b5_gold_identity_registry.py").read_bytes()
    ).hexdigest()


def roster_records(roster):
    """Validate stable identities; a bare name roster is no longer admissible."""
    records = roster.get("members") if isinstance(roster, Mapping) else roster
    if records is None or isinstance(records, (str, bytes, Mapping)):
        raise ValueError("gold matching requires a list of current roster identity records")
    normalized = []
    ids = set()
    names = set()
    for row in records:
        if not isinstance(row, Mapping):
            raise ValueError("gold matching refuses name-only rosters; bioguide and chamber required")
        name = str(row.get("member") or row.get("full_name") or "").strip()
        bioguide = str(row.get("bioguide") or row.get("bioguide_id") or "").strip()
        chamber = str(row.get("chamber") or row.get("type") or "").strip().lower()
        chamber = {"sen": "Senate", "senate": "Senate", "rep": "House", "house": "House"}.get(chamber)
        if not name or not re.fullmatch(r"[A-Z]\d{6}", bioguide) or not chamber:
            raise ValueError("incomplete current roster identity: %r" % dict(row))
        if bioguide in ids or name in names:
            raise ValueError("duplicate current roster identity: %s / %s" % (bioguide, name))
        ids.add(bioguide)
        names.add(name)
        normalized.append({**row, "member": name, "bioguide": bioguide, "chamber": chamber})
    return normalized


def map_gold_with_receipt(gold, roster):
    """Match only pinned historic IDs to current senators, retaining every exclusion.

    The registry describes the appendix's people. Current names are display keys only;
    neither matching names nor matching surnames can confer identity.
    """
    if (gold.get("source") or {}).get("pdf_sha256") != APPENDIX_PDF_SHA256:
        raise ValueError("gold appendix is not the source pinned by the identity registry")
    current = {row["bioguide"]: row for row in roster_records(roster)}
    panels = {panel: {} for panel in PANEL_NAMES}
    excluded = []
    matched = []
    seen = set()
    for row in gold["records"]:
        panel = row["panel"]
        if panel not in panels:
            raise ValueError("unknown gold panel: %r" % panel)
        source_name = " ".join(str(row["source_name"]).split())
        bioguide = SOURCE_NAME_TO_BIOGUIDE.get(source_name)
        if row.get("bioguide") and row["bioguide"] != bioguide:
            raise ValueError("gold row disagrees with pinned identity: %s" % source_name)
        receipt_row = {"panel": panel, "source_name": source_name, "bioguide": bioguide}
        if bioguide is None:
            excluded.append({**receipt_row, "reason": "unregistered_historic_identity"})
            continue
        if (panel, bioguide) in seen:
            raise ValueError("duplicate gold panel identity: %s / %s" % (panel, bioguide))
        seen.add((panel, bioguide))
        member = current.get(bioguide)
        if member is None:
            excluded.append({**receipt_row, "reason": "not_on_current_roster"})
            continue
        if member["chamber"] != "Senate":
            excluded.append({**receipt_row, "current_member": member["member"],
                             "reason": "not_current_senator"})
            continue
        name = member["member"]
        panels[panel][name] = {**row, "bioguide": bioguide}
        matched.append({**receipt_row, "current_member": name})
    unmatched = sorted({row["source_name"] for row in excluded})
    receipt = {
        "schema": "big5-gold-identity-audit-v1",
        "rule": "pinned appendix identity to stable bioguide ID; current Senate members only",
        "registry_sha256": registry_sha256(),
        "registry_reference_commit": REFERENCE_COMMIT,
        "appendix_pdf_sha256": APPENDIX_PDF_SHA256,
        "roster_n": len(current),
        "matched_panel_n": {panel: len(rows) for panel, rows in panels.items()},
        "excluded_reason_counts": dict(sorted(Counter(row["reason"] for row in excluded).items())),
        "matched": matched,
        "excluded": excluded,
    }
    return panels, unmatched, receipt


def map_gold(gold, roster):
    """Compatibility return shape with the corrected, fail-closed identity contract."""
    panels, unmatched, _ = map_gold_with_receipt(gold, roster)
    return panels, unmatched
