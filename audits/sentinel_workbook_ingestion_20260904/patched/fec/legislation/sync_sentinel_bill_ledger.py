#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persist the verified bill sentinel into the canonical Excel workbook.

The Congress/GovInfo repository is the collected fact store.  The verifier is
the admission gate.  This adapter makes Excel the durable, human-readable bill
ledger and writes accepted member relationships into the legacy interaction
tabs used by the dashboard.  Spreadsheet mutation is delegated exclusively to
``sync_sentinel_bill_ledger_artifact.cjs`` and ``@oai/artifact-tool``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import os as _bootstrap_os, sys as _bootstrap_sys
_bootstrap_sys.path.insert(0, _bootstrap_os.path.dirname(_bootstrap_os.path.dirname(_bootstrap_os.path.abspath(__file__))))

import bill_rules as BR
from legislation.verify_collector_roster_updates import gate_repository
from moneyball_core import dump_atomic
from paths import ROOT as ROOT_TEXT


ROOT = Path(ROOT_TEXT)
LEDGER_BASENAME = "Sentinel Bill Ledger.xlsx"
WORKBOOK = ROOT / LEDGER_BASENAME
UPDATES = ROOT / "data" / "members" / "collector_roster_updates.ndjson"
PENDING = ROOT / "data" / "members" / "collector_roster_pending.ndjson"
REPOSITORY = ROOT / "bill_repository_live.json"
REFRESH_RECEIPT = ROOT / "data" / "engine" / "congress_bill_refresh_receipt.json"
BUNDLE = ROOT / "member_desk_bundle.json"
RECEIPT = ROOT / "data" / "engine" / "sentinel_bill_workbook_receipt.json"
HELPER = ROOT / "fec" / "sync_sentinel_bill_ledger_artifact.cjs"
DISCOVERY_CURRENT = ROOT / "data" / "legislation" / "congress_advanced_current" / "congress_advanced_records.ndjson"
DISCOVERY_FALLBACK = ROOT / "audits" / "legfix5" / "congress_advanced_pages_20260725" / "congress_advanced_records.ndjson"
ADJUDICATIONS = ROOT / "legislation_adjudication_ledger.ndjson"
SCHEMA = "sentinel-bill-workbook-plan-v1"
# Runtime resolution order (2026-09-04): an explicit env override, then the
# pinned repository config, then the historical Codex cache.  The cache is a
# developer convenience that simply does not exist on a clean machine, so it is
# the LAST resort and its absence is a clean skip, never a chain halt.
RUNTIME_CONFIG = ROOT / "data" / "engine" / "artifact_tool_runtime.json"
RUNTIME_CONFIG_SCHEMA = "artifact-tool-runtime-v1"
CODEX_RUNTIME_ROOT = (Path.home() / ".cache" / "codex-runtimes"
                      / "codex-primary-runtime" / "dependencies" / "node")

HEADERS = [
    "Record Type", "Review Status", "Scoring Eligible", "Canonical Bill ID",
    "Bill", "Congress", "Measure Type", "Number", "Section", "Member",
    "Bioguide", "Role", "Join Date", "Title", "Sponsor",
    "Cosponsor Count", "Introduced Date", "Repository Updated Date",
    "Latest Action Date", "Latest Action", "Policy Area", "Source",
    "Detail Link", "Summary", "Verified At", "Pending Reason",
    "Repository SHA256", "DecayWeight",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def decay_weight(congress):
    """Per-Congress evidence weight -- the same rule legacy archive rows carry.

    ``congress_bills_archive_*.xlsx`` stores DecayWeight = congress_decay(Congress)
    (119 -> 1.0, 118 -> 0.8, 117 -> 0.64), which is the frozen production schedule
    audit_legislation_decay_propagation enforces.  Sentinel rows previously shipped
    a literal 1.0, scoring an old Congress at full strength.  A row with no
    parseable Congress gets a blank cell rather than a fabricated weight.
    """
    try:
        return BR.congress_decay(congress)
    except (TypeError, ValueError):
        return ""


def load_ndjson(path: Path) -> list[dict]:
    rows = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError(f"{path}:{number}: row is not an object")
            rows.append(value)
    return rows


def _repo_fields(bill: dict) -> list:
    action = bill.get("latest_action") or {}
    sponsor = bill.get("sponsor") or {}
    return [
        bill.get("display") or "", bill.get("congress") or "",
        bill.get("type") or "", bill.get("number") or "",
        bill.get("title") or "", sponsor.get("name") or "",
        bill.get("cosponsor_count") or 0, bill.get("introduced_date") or "",
        bill.get("update_date") or "", action.get("date") or "",
        action.get("text") or "", bill.get("policy_area") or "",
        bill.get("source") or "", bill.get("url") or "",
        bill.get("summary") or "", bill.get("updated_at") or "",
    ]


def build_plan(repository: dict, updates: list[dict], pending: list[dict], *,
               discovery: list[dict] | None = None,
               adjudications: list[dict] | None = None,
               discovery_sha256: str | None = None,
               input_path: Path, output_path: Path) -> dict:
    bills = repository.get("bills") or {}
    repo_hash = sha256(REPOSITORY)
    ledger = [HEADERS]
    for key, bill in sorted(bills.items()):
        base = _repo_fields(bill)
        ledger.append([
            "bill", "tracked", False, key, base[0], base[1], base[2], base[3],
            "", "", "", "", "", base[4], base[5], base[6], base[7],
            base[8], base[9], base[10], base[11], base[12], base[13], base[14],
            base[15], "", repo_hash, decay_weight(base[1]),
        ])

    decisions = {
        str(row.get("canonical_key") or ""): row
        for row in (adjudications or [])
        if row.get("canonical_key")
    }
    discovery_by_key = {}
    for row in discovery or []:
        key = str(row.get("canonical_key") or "")
        if key and key not in discovery_by_key:
            discovery_by_key[key] = row
    # Discovery rows are stamped with the file they actually came from; the
    # repository sha describes bills the repository contains, which these are not.
    discovery_hash = discovery_sha256 or repo_hash
    discovery_only = 0
    discovery_pending = 0
    for key, row in sorted(discovery_by_key.items()):
        if key in bills:
            continue
        decision = decisions.get(key) or {}
        status = str(decision.get("integration_state") or row.get("candidate_status") or "pending review")
        if not decision:
            discovery_pending += 1
        categories = list(row.get("matched_scoring_categories") or []) + list(row.get("matched_monitor_categories") or [])
        ledger.append([
            "discovery candidate", status, False, key,
            row.get("display_number") or "", row.get("congress") or "",
            row.get("type") or "", row.get("number") or "",
            "; ".join(str(value) for value in categories), "", "", "sponsor candidate",
            row.get("initial_action_date_iso") or "", row.get("title") or row.get("heading") or "",
            row.get("sponsor") or "", row.get("cosponsor_count") or 0, "", "",
            row.get("latest_action_date") or "", row.get("latest_action") or "", "",
            "Congress.gov Advanced Search", row.get("canonical_url") or row.get("result_url") or "",
            row.get("purpose") or row.get("raw_text") or "", "", "", discovery_hash,
            decay_weight(row.get("congress")),
        ])
        discovery_only += 1

    accepted_rows = []
    for row in sorted(updates, key=lambda item: (
        str(item.get("repository_key") or ""), str(item.get("member") or ""),
        str(item.get("role") or ""))):
        key = str(row.get("repository_key") or "")
        bill = bills.get(key)
        if not isinstance(bill, dict):
            raise RuntimeError(f"verified update references absent repository bill: {key}")
        base = _repo_fields(bill)
        areas = [str(value).strip() for value in (row.get("areas") or []) if str(value).strip()]
        if not areas:
            areas = [""]
        for area in areas:
            ledger.append([
                "membership", "verified", True, key, base[0], base[1], base[2],
                base[3], area, row.get("member") or "", row.get("bioguide") or "",
                row.get("role") or "", row.get("join_date") or "", base[4],
                base[5], base[6], base[7], base[8], base[9], base[10], base[11],
                row.get("source") or base[12], row.get("url") or base[13],
                row.get("summary") or base[14], row.get("verified_at") or base[15],
                "", row.get("repository_sha256") or repo_hash, decay_weight(base[1]),
            ])
            role = str(row.get("role") or "").strip().lower()
            if role not in {"original", "cosponsor"}:
                raise RuntimeError(f"verified row has inadmissible role: {role}")
            accepted_rows.append({
                "sheet": ("Original Co-Sponsor Interaction" if role == "original"
                          else "Co-Sponsor Interactions"),
                "values": [
                    area, "original-cosponsor" if role == "original" else "cosponsor",
                    row.get("member") or "", base[0], base[4], base[5], base[6],
                    "", base[10], str(base[1]),
                    decay_weight(base[1]),
                    row.get("url") or base[13], row.get("summary") or base[14],
                ],
            })

    for row in sorted(pending, key=lambda item: (
        str(item.get("repository_key") or ""), str(item.get("member") or ""),
        str(item.get("role") or ""))):
        key = str(row.get("repository_key") or "")
        bill = bills.get(key) or {}
        base = _repo_fields(bill) if bill else [row.get("bill") or "", row.get("congress") or "", "", "", "", "", 0, "", "", "", "", "", row.get("source") or "", "", "", row.get("verified_at") or ""]
        ledger.append([
            "membership", "pending review", False, key, base[0], base[1], base[2],
            base[3], "", row.get("member") or "", row.get("bioguide") or "",
            row.get("role") or "", row.get("date") or "", base[4], base[5],
            base[6], base[7], base[8], base[9], base[10], base[11],
            row.get("source") or base[12], base[13], base[14],
            row.get("verified_at") or base[15], row.get("reason") or "", repo_hash,
            decay_weight(base[1]),
        ])

    return {
        "schema": SCHEMA,
        "input_workbook": str(input_path.resolve()),
        "output_workbook": str(output_path.resolve()),
        "ledger_sheet": "Sentinel Bill Ledger",
        "ledger_rows": ledger,
        "accepted_interactions": accepted_rows,
        "counts": {
            "repository_bills": len(bills),
            "verified_memberships": len(updates),
            "verified_interaction_rows": len(accepted_rows),
            "pending_memberships": len(pending),
            "ledger_rows_excluding_header": len(ledger) - 1,
            "discovery_candidates": len(discovery_by_key),
            "discovery_only_ids": discovery_only,
            "discovery_pending_review": discovery_pending,
        },
        "repository_sha256": repo_hash,
    }


def _codex_cache_pair() -> tuple[str, str]:
    node = CODEX_RUNTIME_ROOT / "bin" / ("node.exe" if os.name == "nt" else "node")
    return str(node), str(CODEX_RUNTIME_ROOT / "node_modules")


def _config_pair(config_path: Path | None = None) -> tuple[str, str] | None:
    """Read the pinned runtime config, or None when it is absent/unusable."""
    path = RUNTIME_CONFIG if config_path is None else config_path
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(document, dict) or document.get("schema") != RUNTIME_CONFIG_SCHEMA:
        return None
    node = str(document.get("node") or "").strip()
    modules = str(document.get("node_modules") or "").strip()
    return (node, modules) if node and modules else None


def runtime_candidates(config_path: Path | None = None) -> list[tuple[str, str, str]]:
    """Ordered (source, node, node_modules) candidates: env, pinned config, Codex cache."""
    config = _config_pair(config_path)
    cache = _codex_cache_pair()
    fallback = config or cache
    candidates = []
    env_node = os.environ.get("ARTIFACT_TOOL_NODE")
    env_modules = os.environ.get("ARTIFACT_TOOL_NODE_MODULES")
    if env_node or env_modules:
        # A half-set env override keeps its historical partner default.
        candidates.append(("env", env_node or fallback[0], env_modules or fallback[1]))
    if config:
        candidates.append(("config", config[0], config[1]))
    candidates.append(("codex_cache", cache[0], cache[1]))
    return candidates


def runtime(config_path: Path | None = None) -> tuple[str, str, str] | None:
    """First candidate that resolves to a real node binary + modules dir, else None.

    Returning None (rather than raising) is deliberate: an absent runtime is an
    ENVIRONMENT gap, not corrupt evidence, and the caller answers it with a clean
    skip that leaves the last-good ledger in place.
    """
    for source, node, modules in runtime_candidates(config_path):
        if Path(node).is_file() and Path(modules).is_dir():
            return source, node, modules
    return None


def live_ledger_block(workbook: Path) -> dict | None:
    """Describe the installed ledger for the receipt, or None when it is absent."""
    if not workbook.is_file():
        return None
    stat = workbook.stat()
    return {
        "path": str(workbook.resolve()), "sha256": sha256(workbook), "size": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                         .isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def skip_runtime_absent(workbook: Path) -> int:
    """Record the skip and leave the last-good ledger byte-for-byte untouched."""
    tried = "; ".join("%s: node=%s modules=%s" % candidate for candidate in runtime_candidates())
    block = live_ledger_block(workbook)
    receipt = {
        "schema": "sentinel-bill-workbook-receipt-v1", "status": "SKIPPED_RUNTIME_ABSENT",
        "skipped_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "engine": "@oai/artifact-tool", "runtime_source": None, "installed": False,
        "live_ledger_workbook": block,
        "reason": "no artifact-tool runtime resolved -- tried %s" % tried,
    }
    dump_atomic(receipt, str(RECEIPT))
    print("sync_sentinel_bill_ledger: SKIPPED runtime absent; last-good ledger retained (%s)"
          % (block["sha256"][:12] if block else "none"))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, default=WORKBOOK,
                        help="Installed standalone Excel bill-ledger path.")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--no-install", action="store_true")
    parser.add_argument("--reuse-pass-output", action="store_true",
                        help="Promote an already generated PASS artifact in --output-dir.")
    args = parser.parse_args()
    # This script REPLACES the file it is pointed at.  A typo'd --workbook would
    # silently overwrite an unrelated workbook, so refuse anything but the ledger.
    if args.workbook.name != LEDGER_BASENAME:
        parser.error("--workbook must name %r, got %r" % (LEDGER_BASENAME, args.workbook.name))

    gate_repository(BUNDLE, REPOSITORY, REFRESH_RECEIPT)
    # An absent artifact-tool runtime is an environment gap, not corrupt evidence:
    # skip cleanly and keep the last-good ledger rather than halting the chain.
    # audit_full's sentinel_ledger_freshness check is what stops that skip from
    # becoming permanent silence.  --reuse-pass-output never launches the helper,
    # so it must not be gated on a runtime it does not use.
    resolved = None if args.reuse_pass_output else runtime()
    if resolved is None and not args.reuse_pass_output:
        return skip_runtime_absent(args.workbook)
    updates = load_ndjson(UPDATES)
    pending = load_ndjson(PENDING)
    discovery_path = DISCOVERY_CURRENT if DISCOVERY_CURRENT.is_file() else DISCOVERY_FALLBACK
    discovery = load_ndjson(discovery_path)
    discovery_sha256 = sha256(discovery_path) if discovery_path.is_file() else ""
    adjudications = load_ndjson(ADJUDICATIONS)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = (args.output_dir or (ROOT / "outputs" / f"sentinel_bill_ledger_{stamp}")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "Sentinel Bill Ledger.xlsx"
    plan_path = out_dir / "sentinel_bill_workbook_plan.json"
    report_path = out_dir / "sentinel_bill_workbook_artifact_report.json"
    plan = build_plan(json.loads(REPOSITORY.read_text(encoding="utf-8")), updates, pending,
                      discovery=discovery, adjudications=adjudications,
                      discovery_sha256=discovery_sha256,
                      input_path=args.workbook, output_path=output)
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    runtime_source, node, modules = resolved if resolved else (None, None, None)
    environment = os.environ.copy()
    completed = None
    if not args.reuse_pass_output:
        environment["ARTIFACT_TOOL_NODE_MODULES"] = modules
        completed = subprocess.run([node, "--max-old-space-size=16384", str(HELPER), str(plan_path), str(report_path)],
                                   cwd=ROOT, env=environment, check=False)
    elif not report_path.is_file() or not output.is_file():
        raise RuntimeError("--reuse-pass-output requires an existing report and workbook")
    # No report at all means the helper never reached its own PASS write: a crash, a
    # bad plan, a broken runtime.  That is a REAL failure and must never be confused
    # with the runtime-absent skip above, which does not launch the helper at all.
    if not report_path.is_file():
        print("sync_sentinel_bill_ledger: FAILED artifact-tool wrote no report at %s (process exit %s)"
              % (report_path, completed.returncode if completed is not None else "n/a"),
              file=sys.stderr)
        return 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "PASS" or not output.is_file():
        raise RuntimeError("artifact-tool workbook sync did not produce a PASS workbook")
    # Windows Node can terminate abnormally while freeing the very large
    # imported workbook after it has already written the PASS report and XLSX.
    # The immutable report/output checks above are the publication authority;
    # a nonzero teardown is recorded rather than discarding verified bytes.
    teardown_exit = completed.returncode if completed is not None else None
    inspect_spill = Path(str(output) + ".inspect.ndjson")
    inspect_spill.unlink(missing_ok=True)

    backup = None
    if not args.no_install:
        backup = ROOT / "backups" / f"Sentinel Bill Ledger.PRE-{stamp}.xlsx"
        backup.parent.mkdir(parents=True, exist_ok=True)
        if args.workbook.is_file():
            shutil.copy2(args.workbook, backup)
        else:
            backup = None
        handle, candidate = tempfile.mkstemp(prefix=args.workbook.name + ".", suffix=".candidate", dir=args.workbook.parent)
        os.close(handle)
        try:
            shutil.copy2(output, candidate)
            os.replace(candidate, args.workbook)
        finally:
            if os.path.exists(candidate):
                os.unlink(candidate)

    receipt = {
        "schema": "sentinel-bill-workbook-receipt-v1", "status": "PASS",
        "completed_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "engine": "@oai/artifact-tool", "counts": plan["counts"],
        "repository_sha256": plan["repository_sha256"],
        "discovery": {"path": str(discovery_path), "sha256": discovery_sha256, "rows": len(discovery)},
        "updates_sha256": sha256(UPDATES), "pending_sha256": sha256(PENDING),
        "output": {"path": str(output), "sha256": sha256(output), "size": output.stat().st_size},
        "runtime_source": runtime_source,
        "installed": not args.no_install,
        "live_ledger_workbook": (live_ledger_block(args.workbook) if not args.no_install else None),
        "backup": str(backup) if backup else None,
        "artifact_report": str(report_path),
        "artifact_process_exit": teardown_exit,
        "artifact_process_exit_hex": (hex(teardown_exit & 0xFFFFFFFF) if isinstance(teardown_exit, int) else None),
        "artifact_process_teardown_nonzero": bool(teardown_exit),
    }
    dump_atomic(receipt, str(RECEIPT))
    print(json.dumps({"status": "PASS", **plan["counts"], "output": str(output), "installed": not args.no_install}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
