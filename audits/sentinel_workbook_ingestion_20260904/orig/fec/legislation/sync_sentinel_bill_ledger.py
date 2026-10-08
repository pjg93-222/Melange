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
WORKBOOK = ROOT / "Sentinel Bill Ledger.xlsx"
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

HEADERS = [
    "Record Type", "Review Status", "Scoring Eligible", "Canonical Bill ID",
    "Bill", "Congress", "Measure Type", "Number", "Section", "Member",
    "Bioguide", "Role", "Join Date", "Title", "Sponsor",
    "Cosponsor Count", "Introduced Date", "Repository Updated Date",
    "Latest Action Date", "Latest Action", "Policy Area", "Source",
    "Detail Link", "Summary", "Verified At", "Pending Reason",
    "Repository SHA256",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
            base[15], "", repo_hash,
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
            row.get("purpose") or row.get("raw_text") or "", "", "", repo_hash,
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
                "", row.get("repository_sha256") or repo_hash,
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
                    BR.evidence_decay(base[0], base[1], 1.0),
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


def runtime() -> tuple[str, str]:
    node_root = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node"
    node = os.environ.get("ARTIFACT_TOOL_NODE") or str(node_root / "bin" / ("node.exe" if os.name == "nt" else "node"))
    modules = os.environ.get("ARTIFACT_TOOL_NODE_MODULES") or str(node_root / "node_modules")
    if not Path(node).is_file() or not Path(modules).is_dir():
        raise RuntimeError("bundled artifact-tool runtime is unavailable")
    return node, modules


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workbook", type=Path, default=WORKBOOK,
                        help="Installed standalone Excel bill-ledger path.")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--no-install", action="store_true")
    parser.add_argument("--reuse-pass-output", action="store_true",
                        help="Promote an already generated PASS artifact in --output-dir.")
    args = parser.parse_args()

    gate_repository(BUNDLE, REPOSITORY, REFRESH_RECEIPT)
    updates = load_ndjson(UPDATES)
    pending = load_ndjson(PENDING)
    discovery_path = DISCOVERY_CURRENT if DISCOVERY_CURRENT.is_file() else DISCOVERY_FALLBACK
    discovery = load_ndjson(discovery_path)
    adjudications = load_ndjson(ADJUDICATIONS)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = (args.output_dir or (ROOT / "outputs" / f"sentinel_bill_ledger_{stamp}")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "Sentinel Bill Ledger.xlsx"
    plan_path = out_dir / "sentinel_bill_workbook_plan.json"
    report_path = out_dir / "sentinel_bill_workbook_artifact_report.json"
    plan = build_plan(json.loads(REPOSITORY.read_text(encoding="utf-8")), updates, pending,
                      discovery=discovery, adjudications=adjudications,
                      input_path=args.workbook, output_path=output)
    plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    node, modules = runtime()
    environment = os.environ.copy()
    environment["ARTIFACT_TOOL_NODE_MODULES"] = modules
    completed = None
    if not args.reuse_pass_output:
        completed = subprocess.run([node, "--max-old-space-size=16384", str(HELPER), str(plan_path), str(report_path)],
                                   cwd=ROOT, env=environment, check=False)
    elif not report_path.is_file() or not output.is_file():
        raise RuntimeError("--reuse-pass-output requires an existing report and workbook")
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
        "discovery": {"path": str(discovery_path), "sha256": sha256(discovery_path), "rows": len(discovery)},
        "updates_sha256": sha256(UPDATES), "pending_sha256": sha256(PENDING),
        "output": {"path": str(output), "sha256": sha256(output), "size": output.stat().st_size},
        "installed": not args.no_install,
        "live_ledger_workbook": ({"path": str(args.workbook.resolve()), "sha256": sha256(args.workbook), "size": args.workbook.stat().st_size} if not args.no_install else None),
        "backup": str(backup) if backup else None,
        "artifact_report": str(report_path),
        "artifact_process_exit": teardown_exit,
        "artifact_process_teardown_nonzero": bool(teardown_exit),
    }
    dump_atomic(receipt, str(RECEIPT))
    print(json.dumps({"status": "PASS", **plan["counts"], "output": str(output), "installed": not args.no_install}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
