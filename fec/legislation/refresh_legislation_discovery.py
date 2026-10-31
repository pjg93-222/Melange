#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh the canonical Congress.gov bill-ID discovery checkpoint.

This is a thin scheduled wrapper around the audited Advanced Search collector.
It discovers candidates only; it never ratifies, scores, or promotes them.
The Excel ledger sync records the output as pending until the existing human
adjudication workflow clears a bill.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

import os as _bootstrap_os, sys as _bootstrap_sys
_bootstrap_sys.path.insert(0, _bootstrap_os.path.dirname(_bootstrap_os.path.dirname(_bootstrap_os.path.abspath(__file__))))
from paths import ROOT as ROOT_TEXT


ROOT = Path(ROOT_TEXT)
# Paul 2026-10-27: "Restore original" -- the member x section x role design of
# Draft Systems\congress_member_scraper.R (the 62-query collect_congress_advanced_pages.mjs stays
# on disk, unused by discovery).
COLLECTOR = ROOT / "fec" / "collect" / "collect_congress_member_pages.mjs"
GOVINFO_FALLBACK = ROOT / "fec" / "legislation" / "govinfo_discovery_fallback.py"
REGISTRY = ROOT / "source_data" / "legislation" / "acu_legislation_search_registry.json"
DEFAULT_OUT = ROOT / "data" / "legislation" / "congress_advanced_current"
PIPELINE_LOCK = ROOT / ".pipeline_run.lock"   # pipeline_lock's single writer lease
CYCLE_FILE = "discovery_refresh_cycle.json"
# Written every run that produces a checkpoint. PASS only when Congress.gov itself served the
# result pages; the GovInfo fallback is DEGRADED and named (memory rule 2026-10-27, D-295).
STATUS_FILE = "discovery_status.json"
STATUS_SCHEMA = "congress-discovery-status-v1"
# Exact manifest primary_instrument of a Congress.gov run (the weekly compares the same string).
CONGRESS_SOURCE = "Congress.gov Advanced Search - Legislation"
GOVINFO_SOURCE = "GovInfo BILLSTATUS/BILLS official bulk fallback"


def _write_cycle(out_dir: Path, cycle: dict) -> None:
    target = out_dir / CYCLE_FILE
    temporary = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(cycle, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, target)


def _complete_manifest_hash(out_dir: Path) -> str | None:
    manifest = out_dir / "manifest.json"
    if not manifest.is_file():
        return None
    body = manifest.read_bytes()
    value = json.loads(body.decode("utf-8-sig"))
    return hashlib.sha256(body).hexdigest() if value.get("status") == "complete" else None


def prepare_discovery_cycle(out_dir: Path, registry: Path, categories: str | None) -> dict:
    """Resume only this collection cycle, never a completed prior query cache.

    The browser's --resume accepts old complete queries without contacting the
    source. Preserve those query/page artifacts outside its active cache before
    every new cycle. Canonical cumulative ledgers and GovInfo's version-bound
    cache stay in place so the fallback retains all previously discovered bills.
    A preparing marker makes an interrupted cache move safe to finish on retry.
    """
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    scope = {
        "registry_sha256": hashlib.sha256(registry.read_bytes()).hexdigest(),
        "categories": sorted(set(filter(None, (part.strip() for part in (categories or "").split(","))))),
    }
    state_path = out_dir / CYCLE_FILE
    cycle = json.loads(state_path.read_text(encoding="utf-8")) if state_path.is_file() else {}
    if cycle and (
        cycle.get("schema") != "congress-discovery-refresh-cycle-v1"
        or cycle.get("status") not in {"preparing", "running", "complete"}
        or len(str(cycle.get("id", ""))) != 32
        or any(char not in "0123456789abcdef" for char in str(cycle.get("id", "")))
    ):
        raise RuntimeError("invalid Congress discovery refresh cycle marker")
    manifest_hash = _complete_manifest_hash(out_dir)
    completed_during_interruption = bool(
        cycle.get("status") == "running"
        and manifest_hash
        and manifest_hash != cycle.get("previous_manifest_sha256")
    )
    if (
        not cycle
        or cycle.get("status") == "complete"
        or cycle.get("scope") != scope
        or completed_during_interruption
    ):
        cycle = {
            "schema": "congress-discovery-refresh-cycle-v1",
            "id": uuid.uuid4().hex,
            "status": "preparing",
            "started_at": time.time(),
            "scope": scope,
            "previous_manifest_sha256": manifest_hash,
        }
        _write_cycle(out_dir, cycle)
    if cycle["status"] == "preparing":
        archive = out_dir / ".refresh_cycles" / cycle["id"]
        for relative in (Path("queries"), Path("raw") / "pages", Path("raw") / "member_pages",
                         Path("roster_119_names.json")):
            source = out_dir / relative
            destination = archive / relative
            if not source.exists():
                continue
            # Resolve both sides before moving a directory, including symlinks.
            source.resolve().relative_to(out_dir)
            destination.resolve().relative_to(out_dir)
            if destination.exists():
                raise RuntimeError(f"discovery cache changed during cycle preparation: {relative}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(source, destination)
        cycle["status"] = "running"
        _write_cycle(out_dir, cycle)
    return cycle


def complete_discovery_cycle(out_dir: Path, cycle: dict, outcome: dict | None = None) -> None:
    manifest_hash = _complete_manifest_hash(out_dir)
    if not manifest_hash or manifest_hash == cycle.get("previous_manifest_sha256"):
        raise RuntimeError("Congress.gov discovery did not produce a new complete manifest")
    cycle.update(status="complete", completed_at=time.time(), manifest_sha256=manifest_hash)
    if outcome:
        cycle.update(outcome=outcome["status"], outcome_source=outcome["source"])
    _write_cycle(out_dir, cycle)


def write_discovery_status(out_dir: Path, cycle: dict, *, degraded: bool, reason: str | None = None,
                           browser_failure: Path | None = None, source: str | None = None) -> dict:
    """The step's verdict, read by the congress pipeline, the weekly and the daily seal."""
    status = {
        "schema": STATUS_SCHEMA,
        "status": "DEGRADED" if degraded else "PASS",
        "source": source or (GOVINFO_SOURCE if degraded else CONGRESS_SOURCE),
        "primary_instrument": CONGRESS_SOURCE,
        "primary_instrument_used": not degraded,
        "reason": reason,
        "browser_failure": str(browser_failure) if browser_failure else None,
        "fallback_receipt": "govinfo_fallback_receipt.json" if degraded else None,
        "cycle_id": cycle.get("id"),
        "written_at": datetime.now().astimezone().isoformat(),
    }
    target = out_dir / STATUS_FILE
    temporary = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, target)
    return status


def read_discovery_status(out_dir: Path = DEFAULT_OUT, *, since: float | None = None) -> dict:
    """This run's discovery verdict. Missing, unreadable or older than `since` is never PASS:
    it is reported DEGRADED with the reason, so a seal can never claim Congress.gov silently."""
    path = Path(out_dir) / STATUS_FILE
    try:
        if since is not None and path.stat().st_mtime < since - 2:
            raise ValueError("discovery status predates this run")
        status = json.loads(path.read_text(encoding="utf-8-sig"))
        if status.get("schema") != STATUS_SCHEMA or status.get("status") not in {"PASS", "DEGRADED"}:
            raise ValueError("discovery status has an unknown shape")
        return status
    except (OSError, ValueError) as error:
        return {"schema": STATUS_SCHEMA, "status": "DEGRADED", "source": "unknown (no fresh %s)" % STATUS_FILE,
                "reason": "%s: %s" % (type(error).__name__, error)}


def node_runtime() -> tuple[str, dict[str, str]]:
    environment = os.environ.copy()
    node_root = Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "node"
    bundled = node_root / "bin" / ("node.exe" if os.name == "nt" else "node")
    node = str(bundled) if bundled.is_file() else shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required for Congress.gov discovery")
    modules = node_root / "node_modules"
    if modules.is_dir() and not environment.get("NODE_PATH"):
        environment["NODE_PATH"] = str(modules)
    return node, environment


def latest_automatic_verification_failure(
    out_dir: Path, *, started_after: float
) -> Path | None:
    """Return this run's fail-closed verification receipt, never a stale one."""
    matches: list[Path] = []
    for path in out_dir.glob("manifest.partial.*.json"):
        try:
            if path.stat().st_mtime < started_after - 2:
                continue
            manifest = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if (
            manifest.get("status") == "failed"
            and (manifest.get("error") or {}).get("code")
            == "CONGRESS_AUTOMATIC_VERIFICATION_TIMEOUT"
            and (manifest.get("automatic_verification_timeout") or {}).get(
                "collection_stopped_without_result_acceptance"
            )
            is True
        ):
            matches.append(path)
    return max(matches, key=lambda path: path.stat().st_mtime) if matches else None


def active_cooldown_failure(out_dir: Path, *, now: float | None = None) -> Path | None:
    """Use the official fallback while an evidenced Congress cooldown remains active.

    This neither contacts Congress nor changes its cooldown. Require the exact
    immutable timeout receipt, its manifest hash, and the current no-interaction
    state to agree before reusing an earlier failure as fallback authorization.
    """
    out_dir = out_dir.resolve()
    now = time.time() if now is None else now
    try:
        state = json.loads((out_dir / "automatic_verification_cooldown.json").read_text(encoding="utf-8-sig"))
        observed = datetime.fromisoformat(state["observed_at"].replace("Z", "+00:00"))
        retry = datetime.fromisoformat(state["next_retry_not_before"].replace("Z", "+00:00"))
        policy = state.get("policy") or {}
        classification = state.get("classification") or {}
        if not (
            state.get("schema") == "congress-automatic-verification-cooldown-v1"
            and state.get("status") == "active"
            and observed.tzinfo is not None and retry.tzinfo is not None
            and observed.timestamp() <= now < retry.timestamp()
            and isinstance(state.get("consecutive_timeouts"), int)
            and state["consecutive_timeouts"] >= 1
            and isinstance(state.get("cooldown_ms"), (int, float))
            and state["cooldown_ms"] >= 0
            and round((retry - observed).total_seconds() * 1000) == state["cooldown_ms"]
            and policy.get("kind") == "exponential_backoff"
            and policy.get("reset_after_validated_result_page") is True
            and all(policy.get(key) is False for key in (
                "automatic_refresh_or_reload_during_cooldown", "captcha_bypass_allowed",
                "verification_interaction_allowed"))
            and classification.get("kind") == "automatic_security_verification"
            and all(classification.get(key) is False for key in (
                "interactive", "captcha_bypass_attempted", "verification_interaction_performed"))
        ):
            return None
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None
    for path in sorted(out_dir.glob("manifest.partial.*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            manifest = json.loads(path.read_text(encoding="utf-8-sig"))
            timeout = manifest.get("automatic_verification_timeout") or {}
            if not (
                manifest.get("schema") == "acu-congress-advanced-pages-manifest-v1"
                and manifest.get("status") == "failed"
                and (manifest.get("error") or {}).get("code") == "CONGRESS_AUTOMATIC_VERIFICATION_TIMEOUT"
                and timeout.get("classification") == "automatic_verification_timeout"
                and timeout.get("collection_stopped_without_result_acceptance") is True
                and timeout.get("interaction_performed") is False
                and timeout.get("captcha_bypass_attempted") is False
                and timeout.get("state_file") == "automatic_verification_cooldown.json"
                and all(timeout.get(key) == state.get(key) for key in (
                    "consecutive_timeouts", "cooldown_ms", "next_retry_not_before"))
            ):
                continue
            receipt = (out_dir / timeout["receipt_file"]).resolve()
            receipt.relative_to(out_dir)
            raw = receipt.read_bytes()
            if (
                hashlib.sha256(raw).hexdigest() == timeout.get("receipt_sha256")
                and json.loads(raw.decode("utf-8-sig")) == state
            ):
                return path
        except (OSError, ValueError, TypeError, KeyError, AttributeError):
            continue
    return None


def collector_command(node, out, delay_ms, categories, headless):
    """The visible Chrome is the design (Cloudflare never clears headless, D-295); a headless
    request is passed through and refused by the collector rather than silently ignored.
    delay_ms is kept for the CLI's compatibility; politeness lives in the collector."""
    command = [node, str(COLLECTOR), "--registry", str(REGISTRY), "--out", str(out),
               "--headless" if headless else "--headed", "--resume"]
    if categories:
        command.extend(["--categories", categories])
    return command


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--categories")
    parser.add_argument("--delay-ms", type=int, default=0)
    parser.add_argument("--fallback-workers", type=int, default=8)
    parser.add_argument("--fallback-timeout-seconds", type=float, default=60.0)
    parser.add_argument("--headless", action="store_true",
                        default=os.environ.get("MELANGE_CONGRESS_HEADLESS") == "1")
    args = parser.parse_args()
    # Shared writer lease: inside the congress pipeline this step runs under the pipeline's own
    # .pipeline_run.lock (inherited token). Run standalone (the full Congress.gov walk), it takes that
    # SAME lease, so a daily or weekly that starts mid-walk refuses at its first line and writes nothing
    # to this output; and a standalone run never starts while a chain holds it.
    from pipeline_lock import child_lock_environment, pipeline_run_lock, valid_inherited_lease
    if valid_inherited_lease(PIPELINE_LOCK):
        return _discover(args, {})
    with pipeline_run_lock(PIPELINE_LOCK, owner_kind="congress_discovery") as lease:
        # The collector re-checks that the lease is still this run's before it writes anything.
        return _discover(args, child_lock_environment(lease))


def _discover(args, lease_environment: dict) -> int:
    cycle = prepare_discovery_cycle(args.out, REGISTRY, args.categories)
    (args.out / STATUS_FILE).unlink(missing_ok=True)   # a crash below must not leave last run's verdict
    failure = active_cooldown_failure(args.out)
    environment = os.environ.copy()
    if failure is not None:
        print("Congress.gov verification cooldown remains active; honoring it without a browser retry.")
    else:
        node, environment = node_runtime()
        environment.update(lease_environment)
        command = collector_command(node, args.out, args.delay_ms, args.categories, args.headless)
        browser_started_at = time.time()
        completed = subprocess.run(command, cwd=ROOT, env=environment, check=False)
        if completed.returncode:
            failure = latest_automatic_verification_failure(
                args.out.resolve(), started_after=browser_started_at
            )
            if failure is None:
                raise SystemExit(completed.returncode)
    if failure is not None:
        fallback = [
            sys.executable,
            str(GOVINFO_FALLBACK),
            "--registry",
            str(REGISTRY),
            "--out",
            str(args.out),
            "--browser-failure",
            str(failure),
            "--workers",
            str(max(1, args.fallback_workers)),
            "--timeout-seconds",
            str(args.fallback_timeout_seconds),
        ]
        if args.categories:
            fallback.extend(["--categories", args.categories])
        print(
            "Congress.gov stopped at automatic security verification; "
            "running the official GovInfo pending-only discovery fallback."
        )
        fallback_completed = subprocess.run(
            fallback, cwd=ROOT, env=environment, check=False
        )
        if fallback_completed.returncode:
            raise SystemExit(fallback_completed.returncode)
    records = args.out / "congress_advanced_records.ndjson"
    if not records.is_file() or records.stat().st_size == 0:
        raise RuntimeError("Congress.gov discovery completed without a records ledger")
    # The checkpoint's own manifest names its source: anything but Congress.gov itself is DEGRADED
    # (the GovInfo fallback, or a Congress.gov walk that left pages uncollected).
    manifest = json.loads((args.out / "manifest.json").read_text(encoding="utf-8-sig"))
    instrument = manifest.get("primary_instrument") or "unnamed source"
    outcome = write_discovery_status(
        args.out, cycle, degraded=instrument != CONGRESS_SOURCE, source=instrument,
        reason=("CONGRESS_AUTOMATIC_VERIFICATION_TIMEOUT" if failure is not None
                else "%s page(s) not collected" % manifest.get("coverage_gaps") if manifest.get("coverage_gaps") else None),
        browser_failure=failure)
    complete_discovery_cycle(args.out, cycle, outcome)
    if outcome["status"] != "PASS":
        print(f"DISCOVERY DEGRADED: source used: {instrument}.")
    print(f"Canonical pending-only discovery checkpoint: {records} (discovery {outcome['status']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
