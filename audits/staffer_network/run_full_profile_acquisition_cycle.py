#!/usr/bin/env python3
"""Run one end-to-end incremental staffer/lobbyist profile acquisition cycle."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
import msvcrt
from pathlib import Path
import subprocess
import sys
from typing import Any


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--per-domain-delay", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--max-attempts", type=int, default=2)
    args = parser.parse_args()

    audit_root = Path(__file__).resolve().parent
    workspace = audit_root.parents[1]
    cycle_lock_path = audit_root / ".full_profile_acquisition_cycle.lock"
    cycle_lock = cycle_lock_path.open("a+b")
    if cycle_lock.seek(0, 2) == 0:
        cycle_lock.write(b"\0")
        cycle_lock.flush()
    cycle_lock.seek(0)
    try:
        msvcrt.locking(cycle_lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        print(compact({
            "schema_id": "staffer-network-full-profile-acquisition-cycle-receipt-v1",
            "status": "ALREADY_RUNNING",
            "lock_path": str(cycle_lock_path),
        }))
        return 0
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    structured_root = audit_root / "rapid_structured_discovery_20260901"
    structured_seed_root = audit_root / "rapid_public_profile_seeds_20260901_structured_auto"
    structured_seed = structured_seed_root / "legistorm_lda_profile_fanout_20260901_slice_9000.ndjson"
    continuous_root = audit_root / "rapid_public_profile_continuous_20260901"
    pdf_repair_output = audit_root / "pdf_capture_text_repairs_current"
    structured_output = audit_root / "rapid_structured_profile_evidence_20260901_current"
    fact_output = audit_root / f"incremental_public_fact_candidates_generation_{timestamp}"
    bundle_output = audit_root / f"bulk_profile_candidate_bundles_generation_{timestamp}"

    if structured_root.exists() and list(structured_root.glob("batch*.ndjson")):
        run([
            sys.executable,
            str(audit_root / "structured_discovery_to_seed_shard.py"),
            "--input-root", str(structured_root),
            "--output", str(structured_seed),
        ], workspace)

    run([
        sys.executable,
        str(audit_root / "run_incremental_public_profile_pipeline.py"),
        "--auto-discover-root", str(audit_root),
        "--output-root", str(continuous_root),
        "--workers", str(args.workers),
        "--per-domain-delay", str(args.per_domain_delay),
        "--timeout", str(args.timeout),
        "--max-attempts", str(args.max_attempts),
    ], workspace)

    run([
        sys.executable,
        str(audit_root / "build_pdf_text_repair_overlay.py"),
        "--capture-ledger", str(continuous_root / "incremental_public_page_captures.ndjson"),
        "--output-root", str(pdf_repair_output),
        "--workers", str(args.workers),
        "--per-pdf-timeout", "3",
    ], workspace)

    if structured_root.exists() and list(structured_root.glob("batch*.ndjson")):
        run([
            sys.executable,
            str(audit_root / "consolidate_rapid_structured_profile_evidence.py"),
            "--input-root", str(structured_root),
            "--output-root", str(structured_output),
        ], workspace)

    seed_roots = [audit_root / "legistorm_fanout"]
    seed_roots.extend(sorted(
        path for path in audit_root.glob("rapid_public_profile_seeds_20260901*")
        if path.is_dir()
    ))
    fact_command = [
        sys.executable,
        str(audit_root / "build_incremental_public_fact_candidates.py"),
    ]
    for seed_root in seed_roots:
        fact_command.extend(["--seed-root", str(seed_root)])
    fact_command.extend([
        "--capture-ledger", str(continuous_root / "incremental_public_page_captures.ndjson"),
        "--capture-repair-ledger", str(pdf_repair_output / "pdf_text_repair_overlay.ndjson"),
        "--output-root", str(fact_output),
    ])
    run(fact_command, workspace)

    run([
        sys.executable,
        str(audit_root / "build_bulk_profile_candidate_bundles.py"),
        "--fact-ledger", str(fact_output / "incremental_public_fact_candidates.ndjson"),
        "--output-root", str(bundle_output),
        "--batch-size", "200",
    ], workspace)

    component_receipts = {
        "incremental_capture": continuous_root / "incremental_public_profile_pipeline_receipt.json",
        "pdf_text_repair_overlay": pdf_repair_output / "pdf_text_repair_overlay_receipt.json",
        "public_fact_candidates": fact_output / "incremental_public_fact_candidates_receipt.json",
        "bulk_profile_candidate_bundles": bundle_output / "bulk_profile_candidate_bundles_receipt.json",
    }
    structured_receipt = structured_output / "rapid_structured_profile_evidence_receipt.json"
    if structured_receipt.exists():
        component_receipts["structured_profile_evidence"] = structured_receipt
    components = {
        key: {
            "path": str(path),
            "sha256": sha256(path),
            "receipt": load(path),
        }
        for key, path in component_receipts.items()
    }
    receipt = {
        "schema_id": "staffer-network-full-profile-acquisition-cycle-receipt-v1",
        "status": "PASS",
        "generation_id": f"profile-acquisition-{timestamp}",
        "generated_at": timestamp,
        "workers": args.workers,
        "per_domain_delay_seconds": args.per_domain_delay,
        "timeout_seconds": args.timeout,
        "max_attempts": args.max_attempts,
        "components": components,
    }
    cycle_receipt = audit_root / f"full_profile_acquisition_cycle_receipt_{timestamp}.json"
    cycle_receipt.write_text(compact(receipt) + "\n", encoding="utf-8", newline="\n")
    current = audit_root / "full_profile_acquisition_cycle_current.json"
    tmp = current.with_suffix(".json.tmp")
    tmp.write_text(compact(receipt) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(current)
    print(compact(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
