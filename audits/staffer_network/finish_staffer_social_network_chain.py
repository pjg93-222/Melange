#!/usr/bin/env python3
"""Post-crawl finishing chain for the staffer social network (steps 5-10 + dashboard).

This runner is a driver, not a decision maker.  It reproduces the owner's handoff
sequence exactly once the Politico profile crawl reaches terminal completion, and it
stops the moment any gate is unmet.  It never promotes anything to canonical, never
deletes or overwrites an existing generation directory, never kills a process, and
never launches a crawler.

Every command it will run is derivable from receipts that already exist on disk:

  * ``RAW/crawl_verification.json`` -> the four crawl-verifier input paths, so the
    terminal rerun is argument-identical to the checkpoint reruns.
  * ``politico_payroll_direct_links_20260903_v3_primary/...receipt.json`` -> the five
    required bridge inputs (directory rows, crawl receipt, spine, spans, roster).
  * ``staffer_social_network_20260903_v4_primary/...receipt.json`` -> the spine,
    House-ledger, Senate-committee and exploratory roots the v4 network build used.

Usage
-----
  python finish_staffer_social_network_chain.py                     # dry run (default)
  python finish_staffer_social_network_chain.py --wait --execute    # wait, then run
  python finish_staffer_social_network_chain.py --from bridge_primary --execute
  python finish_staffer_social_network_chain.py --from verify_partial --once

Standard library only.
"""

from __future__ import annotations

try:
    from .politico_completion_contract import completion_accepted, validate_browser_exception, SOURCE_EXCEPTION_POLICY
except ImportError:
    from politico_completion_contract import completion_accepted, validate_browser_exception, SOURCE_EXCEPTION_POLICY


import argparse
import ctypes
import datetime as _dt
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

# --------------------------------------------------------------------------- paths

LT = Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")
SN = LT / "audits" / "staffer_network"
RAW = SN / "politico_profile_crawl_20260903_raw"

CRAWL_VERIFICATION = RAW / "crawl_verification.json"
STATE_JSON = RAW / "state.json"

BRIDGE_V3_PRIMARY = SN / "politico_payroll_direct_links_20260903_v3_primary"
BRIDGE_V3_RECEIPT = BRIDGE_V3_PRIMARY / "politico_payroll_direct_link_receipt.json"
NETWORK_V4_PRIMARY = SN / "staffer_social_network_20260903_v4_primary"
NETWORK_V4_RECEIPT = NETWORK_V4_PRIMARY / "staffer_social_network_receipt.json"
NETWORK_V4_MANIFEST = NETWORK_V4_PRIMARY / "staffer_social_network_manifest.json"
V4_COMPLETION_DOC = SN / "STAFFER_SOCIAL_NETWORK_COMPLETION_20260903_V4.md"

VERIFY_CRAWL = SN / "verify_politico_profile_crawl.py"
WRITE_COMPLETION_REPORT = SN / "write_politico_profile_completion_report.py"
BUILD_BRIDGE = SN / "build_politico_payroll_direct_links.py"
VERIFY_BRIDGE = SN / "verify_politico_payroll_direct_links.py"
BUILD_NETWORK = SN / "build_staffer_social_network.py"
VERIFY_NETWORK = SN / "verify_staffer_social_network.py"

DASHBOARD_SECTION = LT / "fec" / "surfaces" / "build_staffer_network_section.py"
RUN_PIPELINE = LT / "fec" / "run_pipeline.py"
PIPELINE_LOCK = LT / ".pipeline_run.lock"

EMIT_PS1 = Path(r"C:\Users\pgoff\.claude\glassbox\emit.ps1")
GLASSBOX_LANE = "claude"
GLASSBOX_SOURCE = "staffer-finish-chain"

EXPECTED_CORPUS_TOTAL = 18_618
CRAWLER_PROCESS_MARKER = "politico_profile_crawl_playwright"
RUN_PIPELINE_MARKER = "run_pipeline.py"

NETWORK_MANIFEST_NAME = "staffer_social_network_manifest.json"
NETWORK_RECEIPT_NAME = "staffer_social_network_receipt.json"
BRIDGE_RECEIPT_NAME = "politico_payroll_direct_link_receipt.json"

# Manifest keys that are allowed to differ between a primary and its twin.  Proven
# against the v4 pair: the two manifests are identical except for generation_id,
# which is the output directory name by construction.
MANIFEST_ALLOWED_DIFF = {"generation_id"}

# OneDrive rename contention.
RENAME_RETRIES = 12
RENAME_BACKOFF_START = 0.25
RENAME_BACKOFF_MAX = 4.0
RETRYABLE_WINERRORS = {5, 32}


# --------------------------------------------------------------------------- utils


def utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def utc_stamp(moment: _dt.datetime | None = None) -> str:
    return (moment or utc_now()).strftime("%Y%m%dT%H%M%SZ")


def iso_utc(moment: _dt.datetime | None = None) -> str:
    return (moment or utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    """Write via a sibling temp file and os.replace, retrying OneDrive lock races."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{int(time.time() * 1000)}.tmp")
    with tmp.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    delay = RENAME_BACKOFF_START
    last: OSError | None = None
    for _ in range(RENAME_RETRIES):
        try:
            os.replace(tmp, path)
            return
        except OSError as exc:
            if getattr(exc, "winerror", None) not in RETRYABLE_WINERRORS:
                try:
                    tmp.unlink()
                except OSError:
                    pass
                raise
            last = exc
            time.sleep(delay)
            delay = min(delay * 2, RENAME_BACKOFF_MAX)
    try:
        tmp.unlink()
    except OSError:
        pass
    raise RuntimeError(f"could not replace {path} after {RENAME_RETRIES} tries: {last}")


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def atomic_append_text(path: Path, text: str) -> None:
    """Append by rewriting the whole file atomically (OneDrive-safe)."""
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if existing and not existing.endswith("\n"):
        existing += "\n"
    atomic_write_text(path, existing + text)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def quote_command(command: Sequence[str]) -> str:
    parts = []
    for token in command:
        parts.append(f'"{token}"' if (" " in token or "\\" in token) else token)
    return " ".join(parts)


def process_is_alive(pid: int) -> bool | None:
    """Read-only liveness probe.

    Deliberately NOT os.kill: on Windows os.kill(pid, 0) calls TerminateProcess and
    would kill the very process we are asking about.  OpenProcess with SYNCHRONIZE
    only asks whether a handle can be opened.  Returns None when the answer cannot
    be established (restricted token), so callers can fail closed.
    """
    if os.name != "nt":  # pragma: no cover - this runner is Windows-only in practice
        try:
            os.kill(pid, 0)
            return True
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        except OSError:
            return None
    SYNCHRONIZE = 0x00100000
    ERROR_ACCESS_DENIED = 5
    ERROR_INVALID_PARAMETER = 87
    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    handle = kernel32.OpenProcess(SYNCHRONIZE, False, int(pid))
    if handle:
        kernel32.CloseHandle(handle)
        return True
    err = ctypes.get_last_error() or kernel32.GetLastError()
    if err == ERROR_ACCESS_DENIED:
        return True  # it exists; we simply may not touch it
    if err == ERROR_INVALID_PARAMETER:
        return False
    return None


def query_processes(marker: str) -> list[dict[str, Any]] | None:
    """List processes whose command line contains ``marker``.  Read-only.

    Returns None if the query itself failed - callers must not read that as "none".

    The query is self-referential: the PowerShell process that runs it carries the
    marker in its own command line and would otherwise match itself.  It is excluded
    by PID and by the 'Get-CimInstance' text that only the query itself carries.
    """
    script = (
        "$me=$PID; Get-CimInstance Win32_Process | "
        "Where-Object { $_.ProcessId -ne $me -and $_.CommandLine "
        f"-and $_.CommandLine -like '*{marker}*' "
        "-and $_.CommandLine -notlike '*Get-CimInstance*' } | "
        "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            capture_output=True, text=True, timeout=60,
        )
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    if not out:
        return []
    try:
        value = json.loads(out)
    except ValueError:
        return None
    if isinstance(value, dict):
        value = [value]
    return [row for row in value if isinstance(row, dict)]


# --------------------------------------------------------------------------- glassbox


class Glassbox:
    def __init__(self, run_id: str, enabled: bool = True) -> None:
        self.run_id = run_id
        self.enabled = enabled and EMIT_PS1.exists()

    def emit(self, kind: str, status: str, summary: str, *, stage: str = "",
             metadata: dict[str, Any] | None = None) -> None:
        if not self.enabled:
            return
        args = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(EMIT_PS1),
            "-Lane", GLASSBOX_LANE,
            "-Kind", kind,
            "-Status", status,
            "-Summary", summary[:900],
            "-Source", GLASSBOX_SOURCE,
            "-RunId", self.run_id,
            "-Quiet",
        ]
        if stage:
            args += ["-Stage", stage]
        if metadata:
            args += ["-MetadataJson", json.dumps(metadata, sort_keys=True, default=str)]
        try:
            subprocess.run(args, capture_output=True, timeout=30, check=False)
        except Exception:
            return  # glassbox is never fatal


# --------------------------------------------------------------------------- logging


class ChainLog:
    def __init__(self, path: Path, echo: bool = True) -> None:
        self.path = path
        self.echo = echo
        self.lines: list[str] = []

    def write(self, message: str) -> None:
        line = f"[{iso_utc()}] {message}"
        self.lines.append(line)
        if self.echo:
            print(line, flush=True)
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError:
            pass  # never let logging kill the chain

    def plain(self, message: str = "") -> None:
        """Report text (dry-run tables); echoed and logged verbatim."""
        self.lines.append(message)
        if self.echo:
            print(message, flush=True)
        try:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(message + "\n")
        except OSError:
            pass


# --------------------------------------------------------------------------- errors


class ChainHalt(Exception):
    def __init__(self, reason: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail or {}


# --------------------------------------------------------------------------- resolution


class Resolution:
    """Every path and argument the chain needs, resolved from receipts on disk."""

    def __init__(self, date: str, python: str, generated_at: str) -> None:
        self.date = date
        self.python = python
        self.generated_at = generated_at
        self.notes: list[str] = []
        self.owner_decisions: list[str] = []

        # ---- crawl verifier inputs, taken verbatim from the existing receipt
        self.crawl_inputs: dict[str, str | None] = {
            "directory": None, "profiles": None, "failures": None, "state": None,
        }
        if CRAWL_VERIFICATION.exists():
            try:
                inputs = read_json(CRAWL_VERIFICATION).get("inputs") or {}
            except Exception as exc:
                self.notes.append(f"crawl_verification.json unreadable ({exc}); crawl inputs unresolved")
                inputs = {}
            for key in self.crawl_inputs:
                value = inputs.get(key)
                self.crawl_inputs[key] = str(value) if value else None
            if self.crawl_inputs["failures"] is None:
                self.notes.append(
                    "crawl_verification.json records inputs.failures = null, so the prior runs "
                    "did NOT pass --failures; the rerun omits it to stay argument-identical "
                    "(the verifier treats a failures file as optional)."
                )
        else:
            self.notes.append(f"{CRAWL_VERIFICATION} is absent; crawl verifier inputs unresolved")

        # ---- bridge inputs, mapped from the v3 bridge receipt by file name
        self.bridge_inputs: dict[str, str | None] = {
            "raw-directory": None, "crawl-receipt": None,
            "spine": None, "spans": None, "roster": None,
        }
        name_to_flag = {
            "directory_rows.ndjson": "raw-directory",
            "crawl_receipt.json": "crawl-receipt",
            "hill_person_spine.ndjson.gz": "spine",
            "hill_person_office_spans.ndjson.gz": "spans",
            "congestion.json": "roster",
        }
        if BRIDGE_V3_RECEIPT.exists():
            try:
                declared = read_json(BRIDGE_V3_RECEIPT).get("inputs") or {}
            except Exception as exc:
                self.notes.append(f"bridge v3 receipt unreadable ({exc}); bridge inputs unresolved")
                declared = {}
            for path_text in declared:
                flag = name_to_flag.get(Path(path_text).name)
                if flag:
                    self.bridge_inputs[flag] = path_text
        else:
            self.notes.append(f"{BRIDGE_V3_RECEIPT} is absent; bridge inputs unresolved")
        for flag, value in self.bridge_inputs.items():
            if value is None:
                self.owner_decisions.append(
                    f"bridge --{flag}: no matching entry in the v3 bridge receipt inputs; "
                    "flag left out of the resolved command"
                )

        # ---- network roots, derived from the v4 network receipt input roles
        self.network_roots: dict[str, str | None] = {
            "hill-spine-root": None, "house-ledger-root": None,
            "senate-committee-root": None, "exploratory-revolving-edges": None,
        }
        role_to_root = {
            "hill_person_spine": "hill-spine-root",
            "house_person_office_spans": "house-ledger-root",
            "senate_committee_payroll_candidates": "senate-committee-root",
        }
        self.v4_config_name: str | None = None
        self.v4_vintage: str | None = None
        self.v4_review_inputs_used = False
        if NETWORK_V4_RECEIPT.exists():
            try:
                receipt = read_json(NETWORK_V4_RECEIPT)
            except Exception as exc:
                self.notes.append(f"v4 network receipt unreadable ({exc}); network roots unresolved")
                receipt = {}
            self.v4_config_name = receipt.get("config_name")
            self.v4_vintage = receipt.get("vintage")
            roles = {}
            for entry in receipt.get("inputs") or []:
                if isinstance(entry, dict) and entry.get("role"):
                    roles[entry["role"]] = entry.get("path")
            for role, flag in role_to_root.items():
                path_text = roles.get(role)
                if path_text:
                    self.network_roots[flag] = str(Path(path_text).parent)
            if roles.get("exploratory_revolving_edges"):
                self.network_roots["exploratory-revolving-edges"] = roles["exploratory_revolving_edges"]
            self.v4_review_inputs_used = any(
                role.startswith("politico_profile_") or role == "politico_current_committee_assertions"
                or role == "politico_explicit_committee_side_assertions"
                for role in roles
            )
        else:
            self.notes.append(f"{NETWORK_V4_RECEIPT} is absent; network roots unresolved")
        for flag, value in self.network_roots.items():
            if value is None:
                self.owner_decisions.append(
                    f"network --{flag}: no matching role in the v4 network receipt inputs; "
                    "flag left out of the resolved command"
                )

        # ---- output generations
        self.bridge_primary = SN / f"politico_payroll_direct_links_{date}_v4_primary"
        self.bridge_twin = SN / f"politico_payroll_direct_links_{date}_v4_twin"
        self.bridge_verification = SN / f"politico_payroll_direct_links_{date}_v4_verification"
        self.network_primary = SN / f"staffer_social_network_{date}_v5_primary"
        self.network_twin = SN / f"staffer_social_network_{date}_v5_twin"
        self.network_verification = SN / f"staffer_social_network_{date}_v5_verification"

        # ---- report outputs
        self.completion_report = SN / f"POLITICO_PROFILE_CRAWL_COMPLETION_{date}.md"
        self.exception_review = SN / f"POLITICO_PROFILE_CRAWL_IDENTITY_EXCEPTIONS_{date}.md"
        self.reconciliation = SN / f"STAFFER_SOCIAL_NETWORK_FINAL_RECONCILIATION_{date}.md"

        # ---- the five Politico review-layer inputs the new bridge will emit.
        # build_politico_payroll_direct_links.py writes these into its own output
        # directory only when --profile-histories is supplied (see its run(): the
        # optional_file_meta block), and build_staffer_social_network.py requires
        # all five together whenever --require-complete-politico-profile-crawl is
        # set.  They are therefore NOT a separate producer script.
        self.review_inputs = {
            "politico-current-committee-assertions":
                self.bridge_primary / "politico_current_committee_assertions.ndjson.gz",
            "politico-profile-employment-assertions":
                self.bridge_primary / "politico_profile_employment_assertions.ndjson.gz",
            "politico-profile-education-assertions":
                self.bridge_primary / "politico_profile_education_assertions.ndjson.gz",
            "politico-profile-policy-deltas":
                self.bridge_primary / "politico_profile_policy_deltas.ndjson.gz",
            "politico-explicit-committee-side-assertions":
                self.bridge_primary / "politico_explicit_committee_side_assertions.ndjson.gz",
        }

    # ------------------------------------------------------------------ commands

    def cmd_verify_crawl(self, output: Path, require_complete: bool) -> list[str]:
        cmd = [self.python, str(VERIFY_CRAWL)]
        for flag in ("directory", "profiles"):
            value = self.crawl_inputs.get(flag)
            if value:
                cmd += [f"--{flag}", value]
        for flag in ("failures", "state"):
            value = self.crawl_inputs.get(flag)
            if value:
                cmd += [f"--{flag}", value]
        source_exceptions = RAW / 'browser_source_exceptions_20260905.ndjson'
        if source_exceptions.exists():
            cmd += ['--source-exceptions', str(source_exceptions)]
        cmd += ["--output", str(output)]
        if require_complete:
            cmd.append("--require-complete")
        return cmd

    def cmd_completion_report(self) -> list[str]:
        return [
            self.python, str(WRITE_COMPLETION_REPORT),
            "--verification", str(CRAWL_VERIFICATION),
            "--output", str(self.completion_report),
        ]

    def cmd_build_bridge(self, output: Path) -> list[str]:
        cmd = [self.python, str(BUILD_BRIDGE)]
        for flag in ("raw-directory", "crawl-receipt", "spine", "spans", "roster"):
            value = self.bridge_inputs.get(flag)
            if value:
                cmd += [f"--{flag}", value]
        cmd += [
            "--profile-histories", str(RAW / "profiles.ndjson"),
            "--profile-crawl-verification", str(CRAWL_VERIFICATION),
            "--require-complete-profile-crawl",
            "--output", str(output),
        ]
        return cmd

    def cmd_verify_bridge(self) -> list[str]:
        cmd = [
            self.python, str(VERIFY_BRIDGE),
            "--generation", str(self.bridge_primary),
            "--twin", str(self.bridge_twin),
        ]
        for flag in ("raw-directory", "spine", "spans", "roster"):
            value = self.bridge_inputs.get(flag)
            if value:
                cmd += [f"--{flag}", value]
        cmd += [
            "--profile-histories", str(RAW / "profiles.ndjson"),
            "--profile-crawl-verification", str(CRAWL_VERIFICATION),
            "--require-complete-profile-crawl",
            # The bridge verifier's --output is a DIRECTORY: it does
            # out.mkdir(parents=True, exist_ok=False) and then writes
            # out / "verification_report.json" itself.  Passing the file path would
            # create a directory named verification_report.json.
            "--output", str(self.bridge_verification),
        ]
        return cmd

    def cmd_build_network(self, output: Path) -> list[str]:
        cmd = [self.python, str(BUILD_NETWORK)]
        for flag in ("hill-spine-root", "house-ledger-root", "senate-committee-root",
                     "exploratory-revolving-edges"):
            value = self.network_roots.get(flag)
            if value:
                cmd += [f"--{flag}", value]
        cmd += [
            "--politico-direct-policy-memberships",
            str(self.bridge_primary / "politico_policy_memberships.ndjson.gz"),
            "--politico-direct-link-receipt",
            str(self.bridge_primary / BRIDGE_RECEIPT_NAME),
        ]
        for flag, path in self.review_inputs.items():
            cmd += [f"--{flag}", str(path)]
        cmd += ["--require-complete-politico-profile-crawl"]
        if self.v4_config_name:
            cmd += ["--config-name", self.v4_config_name]
        cmd += [
            "--vintage", self.date,
            "--generated-at", self.generated_at,
            "--no-glassbox",
            "--output", str(output),
        ]
        return cmd

    def cmd_verify_network(self) -> list[str]:
        cmd = [
            self.python, str(VERIFY_NETWORK),
            "--primary", str(self.network_primary),
            "--twin", str(self.network_twin),
            "--output", str(self.network_verification),
        ]
        if self.v4_config_name:
            cmd += ["--expected-config-name", self.v4_config_name]
        cmd += ["--expected-vintage", self.date]
        return cmd

    def cmd_dashboard_section(self) -> list[str]:
        return [
            self.python, str(DASHBOARD_SECTION),
            "--generation", self.network_primary.name,
            "--max-bytes", "5000000",
        ]

    def cmd_run_pipeline(self) -> list[str]:
        return [self.python, str(RUN_PIPELINE), "--from", "make_staffer_network_html.py"]


# --------------------------------------------------------------------------- gates


def gate_partial_verification(receipt: dict[str, Any]) -> tuple[bool, str]:
    status = receipt.get("integrity_status")
    if status != "PASS":
        return False, f"integrity_status={status!r}, required PASS"
    return True, "integrity_status=PASS"


def gate_complete_verification(receipt: dict[str, Any], exit_code: int) -> tuple[bool, str]:
    problems: list[str] = []
    if exit_code != 0:
        problems.append(f"exit code {exit_code}, required 0")
    if receipt.get("status") != "PASS":
        problems.append(f"status={receipt.get('status')!r}, required PASS")
    if not completion_accepted(receipt):
        problems.append(f"completion_status={receipt.get('completion_status')!r}, required COMPLETE or evidence-backed COMPLETE_WITH_EXCEPTIONS")
    failures = receipt.get("verification_failure_count")
    if failures != 0:
        problems.append(f"verification_failure_count={failures!r}, required 0")
    gate = receipt.get("completion_gate") or {}
    unmet = gate.get("unmet_requirements")
    if unmet:
        problems.append(f"unmet_requirements={unmet!r}, required empty")
    if gate.get("unmet_requirement_count") not in (0, None):
        problems.append(f"unmet_requirement_count={gate.get('unmet_requirement_count')!r}, required 0")
    accounted = (receipt.get("counts") or {}).get("profiles_accounted")
    if accounted != EXPECTED_CORPUS_TOTAL:
        problems.append(f"profiles_accounted={accounted!r}, required {EXPECTED_CORPUS_TOTAL}")
    if problems:
        return False, "; ".join(problems)
    return True, (
        f"status=PASS completion_status={receipt.get('completion_status')} verification_failure_count=0 "
        f"unmet_requirements=[] profiles_accounted={EXPECTED_CORPUS_TOTAL}"
    )


def compare_generation(primary: Path, twin: Path, manifest_name: str | None) -> dict[str, Any]:
    """Byte-identity of every substantive file; manifest may differ only in generation_id."""
    result: dict[str, Any] = {"files": {}, "failures": []}
    primary_names = {p.name for p in primary.iterdir() if p.is_file()}
    twin_names = {p.name for p in twin.iterdir() if p.is_file()}
    if primary_names != twin_names:
        result["failures"].append({
            "check": "file_set",
            "only_in_primary": sorted(primary_names - twin_names),
            "only_in_twin": sorted(twin_names - primary_names),
        })
    for name in sorted(primary_names & twin_names):
        a = sha256_file(primary / name)
        b = sha256_file(twin / name)
        if a == b:
            result["files"][name] = {"identical": True, "sha256": a}
            continue
        if manifest_name and name == manifest_name:
            try:
                pa = read_json(primary / name)
                pb = read_json(twin / name)
            except Exception as exc:
                result["files"][name] = {"identical": False, "note": f"unparseable: {exc}"}
                result["failures"].append({"check": "manifest_unparseable", "path": name})
                continue
            diff = {k for k in set(pa) | set(pb) if pa.get(k) != pb.get(k)}
            if diff and diff <= MANIFEST_ALLOWED_DIFF:
                result["files"][name] = {
                    "identical": False,
                    "allowed_difference": sorted(diff),
                    "note": "generation_id is the output directory name by design",
                    "primary_sha256": a, "twin_sha256": b,
                }
                continue
            result["files"][name] = {"identical": False, "differing_keys": sorted(diff),
                                     "primary_sha256": a, "twin_sha256": b}
            result["failures"].append({"check": "manifest_differs_beyond_generation_id",
                                       "path": name, "differing_keys": sorted(diff)})
            continue
        result["files"][name] = {"identical": False, "primary_sha256": a, "twin_sha256": b}
        result["failures"].append({"check": "twin_not_byte_identical", "path": name})
    result["ok"] = not result["failures"]
    return result


# --------------------------------------------------------------------------- steps


class Step:
    def __init__(self, name: str, handoff: str, title: str, *,
                 command: Callable[[], list[str]] | None = None,
                 action: Callable[["Chain"], dict[str, Any]] | None = None,
                 inputs: Callable[[], list[Path]] | None = None,
                 optional_inputs: Callable[[], list[Path]] | None = None,
                 output_dirs: Callable[[], list[Path]] | None = None,
                 output_files: Callable[[], list[Path]] | None = None,
                 rewrites: Callable[[], list[Path]] | None = None,
                 cwd: Path = LT,
                 note: str = "") -> None:
        self.name = name
        self.handoff = handoff
        self.title = title
        self.command = command
        self.action = action
        self.inputs = inputs or (lambda: [])
        self.optional_inputs = optional_inputs or (lambda: [])
        self.output_dirs = output_dirs or (lambda: [])
        self.output_files = output_files or (lambda: [])
        self.rewrites = rewrites or (lambda: [])
        self.cwd = cwd
        self.note = note


class Chain:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.started = utc_now()
        self.stamp = utc_stamp(self.started)
        self.run_id = f"run-{self.stamp}-finish"
        self.log = ChainLog(SN / f"finish_chain_{self.stamp}.log")
        self.glassbox = Glassbox(self.run_id, enabled=not args.no_glassbox)
        self.date = args.date or self.completion_date()
        self.python = args.python or sys.executable
        generated_at = args.generated_at or iso_utc(self.started)
        self.res = Resolution(self.date, self.python, generated_at)
        self.verification_output = (
            Path(args.verification_output).resolve() if args.verification_output
            else CRAWL_VERIFICATION
        )
        self.results: dict[str, dict[str, Any]] = {}
        self.steps = self.build_steps()

    # ------------------------------------------------------------------ helpers

    def completion_date(self) -> str:
        """Local completion date: watchdog DONE file, else a COMPLETE receipt, else today."""
        done = sorted(RAW.glob("WATCHDOG_DONE_*.json"))
        if done:
            try:
                stamp = read_json(done[-1]).get("completed_at")
                if stamp:
                    moment = _dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
                    return moment.astimezone().strftime("%Y%m%d")
            except Exception:
                pass
        if CRAWL_VERIFICATION.exists():
            try:
                receipt = read_json(CRAWL_VERIFICATION)
                if completion_accepted(receipt):
                    moment = _dt.datetime.fromisoformat(
                        str(receipt.get("generated_at")).replace("Z", "+00:00"))
                    return moment.astimezone().strftime("%Y%m%d")
            except Exception:
                pass
        return _dt.datetime.now().strftime("%Y%m%d")

    def halt(self, reason: str, detail: dict[str, Any] | None = None) -> None:
        raise ChainHalt(reason, detail)

    def write_halt_file(self, reason: str, detail: dict[str, Any]) -> Path:
        stamp = utc_stamp()
        path = SN / f"FINISH_CHAIN_HALT_{stamp}.json"
        # A halt record is evidence; never let a same-second collision destroy one.
        suffix = 2
        while path.exists():
            path = SN / f"FINISH_CHAIN_HALT_{stamp}_{suffix}.json"
            suffix += 1
        payload = {
            "schema_id": "staffer-network-finish-chain-halt-v1",
            "run_id": self.run_id,
            "halted_at": iso_utc(),
            "reason": reason,
            "detail": detail,
            "log": str(self.log.path),
            "date": self.date,
            "review_status": "REVIEW_REQUIRED",
        }
        atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")
        return path

    # ------------------------------------------------------------------ steps

    def build_steps(self) -> list[Step]:
        r = self.res
        return [
            Step(
                "verify_partial", "5a", "Crawl verifier, integrity only (no --require-complete)",
                command=lambda: r.cmd_verify_crawl(self.verification_output, require_complete=False),
                inputs=lambda: [VERIFY_CRAWL] + [Path(v) for k, v in r.crawl_inputs.items()
                                                 if v and k != "failures"],
                optional_inputs=lambda: [Path(v) for k, v in r.crawl_inputs.items()
                                         if v and k == "failures"],
                rewrites=lambda: [self.verification_output],
                note="gate: integrity_status must be PASS",
            ),
            Step(
                "verify_complete", "5b", "Crawl verifier terminal gate (--require-complete)",
                command=lambda: r.cmd_verify_crawl(self.verification_output, require_complete=True),
                inputs=lambda: [VERIFY_CRAWL] + [Path(v) for k, v in r.crawl_inputs.items()
                                                 if v and k != "failures"],
                rewrites=lambda: [self.verification_output],
                note=("gate: exit 0 AND status=PASS AND completion_status=COMPLETE AND "
                      "verification_failure_count=0 AND unmet_requirements=[]"),
            ),
            Step(
                "completion_report", "6", "Markdown crawl completion receipt",
                command=r.cmd_completion_report,
                inputs=lambda: [WRITE_COMPLETION_REPORT, CRAWL_VERIFICATION],
                output_files=lambda: [r.completion_report],
            ),
            Step(
                "exception_review", "7", "List every identity exception for owner review",
                action=lambda chain: chain.do_exception_review(),
                inputs=lambda: [CRAWL_VERIFICATION],
                output_files=lambda: [r.exception_review],
                note="lists LIVE_NAME_CHANGED_SAME_UUID and PROFILE_UNAVAILABLE_404; adjudicates nothing",
            ),
            Step(
                "bridge_primary", "8a", "Rebuild the strict Politico/payroll bridge (primary)",
                command=lambda: r.cmd_build_bridge(r.bridge_primary),
                inputs=lambda: ([BUILD_BRIDGE, RAW / "profiles.ndjson", CRAWL_VERIFICATION]
                                + [Path(v) for v in r.bridge_inputs.values() if v]),
                output_dirs=lambda: [r.bridge_primary],
            ),
            Step(
                "bridge_twin", "8b", "Rebuild the bridge into an independent twin directory",
                command=lambda: r.cmd_build_bridge(r.bridge_twin),
                inputs=lambda: ([BUILD_BRIDGE, RAW / "profiles.ndjson", CRAWL_VERIFICATION]
                                + [Path(v) for v in r.bridge_inputs.values() if v]),
                output_dirs=lambda: [r.bridge_twin],
            ),
            Step(
                "bridge_identity", "8c", "sha256 byte-identity of every bridge file",
                action=lambda chain: chain.do_identity(r.bridge_primary, r.bridge_twin, None,
                                                       "bridge"),
                note="the v3 pair is byte-identical in all four files; no generation_id exemption",
            ),
            Step(
                "bridge_verify", "8d", "Independent bridge verifier",
                command=r.cmd_verify_bridge,
                inputs=lambda: ([VERIFY_BRIDGE, RAW / "profiles.ndjson", CRAWL_VERIFICATION]
                                + [Path(v) for k, v in r.bridge_inputs.items()
                                   if v and k != "crawl-receipt"]),
                output_dirs=lambda: [r.bridge_verification],
            ),
            Step(
                "network_primary", "9a", "Rebuild the separated-layer network (primary)",
                command=lambda: r.cmd_build_network(r.network_primary),
                inputs=lambda: ([BUILD_NETWORK]
                                + [Path(v) for v in r.network_roots.values() if v]
                                + [r.bridge_primary / "politico_policy_memberships.ndjson.gz",
                                   r.bridge_primary / BRIDGE_RECEIPT_NAME]
                                + list(r.review_inputs.values())),
                output_dirs=lambda: [r.network_primary],
                note="bridge-produced inputs do not exist until bridge_primary has run",
            ),
            Step(
                "network_twin", "9b", "Rebuild the network into an independent twin directory",
                command=lambda: r.cmd_build_network(r.network_twin),
                inputs=lambda: ([BUILD_NETWORK]
                                + [Path(v) for v in r.network_roots.values() if v]
                                + [r.bridge_primary / "politico_policy_memberships.ndjson.gz",
                                   r.bridge_primary / BRIDGE_RECEIPT_NAME]
                                + list(r.review_inputs.values())),
                output_dirs=lambda: [r.network_twin],
            ),
            Step(
                "network_identity", "9c", "sha256 byte-identity of every network artifact",
                action=lambda chain: chain.do_identity(r.network_primary, r.network_twin,
                                                       NETWORK_MANIFEST_NAME, "network"),
                note="manifest may differ only in generation_id (proven convention from the v4 pair)",
            ),
            Step(
                "network_verify", "9d", "Independent network verifier",
                command=r.cmd_verify_network,
                inputs=lambda: [VERIFY_NETWORK],
                output_dirs=lambda: [r.network_verification],
            ),
            Step(
                "reconciliation", "10", "Final reconciliation document + V4 completion-doc addendum",
                action=lambda chain: chain.do_reconciliation(),
                inputs=lambda: [CRAWL_VERIFICATION, V4_COMPLETION_DOC],
                output_files=lambda: [r.reconciliation],
                rewrites=lambda: [V4_COMPLETION_DOC],
                note="every figure is read from a receipt; nothing is computed here",
            ),
            Step(
                "dashboard_section", "D1", "Refresh the dashboard staffer-network section data",
                command=r.cmd_dashboard_section,
                inputs=lambda: [DASHBOARD_SECTION],
                note="skipped with a clear message if the producer does not exist yet",
            ),
            Step(
                "dashboard_pipeline", "D2", "Rebuild the combined dashboard from make_combined.py",
                action=lambda chain: chain.do_pipeline(),
                inputs=lambda: [RUN_PIPELINE],
                note=("runs only when no run_pipeline.py process exists and no live "
                      ".pipeline_run.lock; otherwise WAITING, retried every 5 min for up to 2 h"),
            ),
        ]

    def step_index(self, name: str) -> int:
        for index, step in enumerate(self.steps):
            if step.name == name:
                return index
        raise SystemExit(f"unknown step {name!r}; known: {', '.join(s.name for s in self.steps)}")

    def selected(self) -> list[Step]:
        start = self.step_index(self.args.frm) if self.args.frm else 0
        chosen = self.steps[start:]
        if self.args.once:
            chosen = chosen[:1]
        return chosen

    # ------------------------------------------------------------------ dry run

    def interpreter_report(self) -> list[str]:
        lines = []
        lines.append(f"  runner interpreter        : {sys.executable}")
        lines.append(f"  chain will invoke         : {self.python}")
        recorded = None
        for path in (NETWORK_V4_RECEIPT, NETWORK_V4_MANIFEST):
            if not path.exists():
                continue
            try:
                blob = path.read_text(encoding="utf-8")
            except OSError:
                continue
            match = re.search(r'"(python[^"]*|interpreter|executable)"\s*:\s*"([^"]+)"', blob)
            if match:
                recorded = f"{match.group(1)} = {match.group(2)} (from {path.name})"
                break
        if recorded:
            lines.append(f"  v4 build interpreter      : {recorded}")
            lines.append("  match                     : compare the two lines above before executing")
        else:
            lines.append("  v4 build interpreter      : NOT RECORDED in the v4 receipt or manifest")
            lines.append("                              (neither file carries an interpreter field), so a")
            lines.append("                              same-interpreter guarantee is NOT verifiable here.")
            for candidate in (Path(r"C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe"),
                              LT / ".venv-politico" / "Scripts" / "python.exe",
                              LT / ".venv" / "Scripts" / "python.exe"):
                lines.append(f"    candidate {'present' if candidate.exists() else 'absent '} : {candidate}")
        return lines

    def dry_run(self) -> int:
        log = self.log
        log.plain("=" * 100)
        log.plain("STAFFER SOCIAL NETWORK - POST-CRAWL FINISHING CHAIN (DRY RUN, NOTHING EXECUTED)")
        log.plain("=" * 100)
        log.plain(f"run id            : {self.run_id}")
        log.plain(f"generated (UTC)   : {iso_utc(self.started)}")
        log.plain(f"vintage / date    : {self.date}"
                  + ("  (from --date)" if self.args.date else "  (derived completion date, local)"))
        log.plain(f"--generated-at    : {self.res.generated_at}  (identical for primary and twin)")
        log.plain(f"log file          : {self.log.path}")
        log.plain(f"live tree         : {LT}")
        log.plain("")
        log.plain("INTERPRETER")
        for line in self.interpreter_report():
            log.plain(line)
        log.plain("")

        # crawl state
        log.plain("CRAWL STATE (read-only)")
        if STATE_JSON.exists():
            try:
                state = read_json(STATE_JSON)
                log.plain(f"  halted={state.get('halted')}  remaining={state.get('remaining')}  "
                          f"total_succeeded={state.get('total_succeeded')}  "
                          f"queue_total={state.get('queue_total')}")
                log.plain(f"  last_updated={state.get('last_updated')}")
            except Exception as exc:
                log.plain(f"  state.json unreadable: {exc}")
        else:
            log.plain(f"  MISSING {STATE_JSON}")
        done = sorted(RAW.glob("WATCHDOG_DONE_*.json"))
        halt = sorted(RAW.glob("WATCHDOG_HALT_*.json"))
        log.plain(f"  WATCHDOG_DONE_*.json : {[p.name for p in done] or 'none'}")
        log.plain(f"  WATCHDOG_HALT_*.json : {[p.name for p in halt] or 'none'}")
        watchdog = SN / "politico_crawl_watchdog.ps1"
        log.plain(f"  watchdog script      : {'PRESENT' if watchdog.exists() else 'ABSENT'}  {watchdog}")
        if CRAWL_VERIFICATION.exists():
            try:
                receipt = read_json(CRAWL_VERIFICATION)
                counts = receipt.get("counts") or {}
                coverage = (receipt.get("coverage") or {}).get("all_profiles") or {}
                log.plain(f"  crawl_verification.json: status={receipt.get('status')} "
                          f"integrity={receipt.get('integrity_status')} "
                          f"completion={receipt.get('completion_status')} "
                          f"accounted={counts.get('profiles_accounted')} "
                          f"unresolved={coverage.get('unresolved')}")
            except Exception as exc:
                log.plain(f"  crawl_verification.json unreadable: {exc}")
        log.plain("")

        # concurrency
        log.plain("CONCURRENCY (read-only; this runner never kills or launches anything)")
        crawlers = query_processes(CRAWLER_PROCESS_MARKER)
        if crawlers is None:
            log.plain("  crawler processes    : QUERY FAILED (fail closed: execute would refuse)")
        else:
            log.plain(f"  crawler processes    : {len(crawlers)}"
                      + (f"  pids={[c.get('ProcessId') for c in crawlers]}" if crawlers else ""))
        pipes = query_processes(RUN_PIPELINE_MARKER)
        if pipes is None:
            log.plain("  run_pipeline.py      : QUERY FAILED (fail closed: dashboard step would wait)")
        else:
            log.plain(f"  run_pipeline.py      : {len(pipes)}"
                      + (f"  pids={[c.get('ProcessId') for c in pipes]}" if pipes else ""))
        status, detail = self.pipeline_lock_status()
        log.plain(f"  .pipeline_run.lock   : {status}  {detail}")
        log.plain("")

        # notes and owner decisions
        if self.res.notes:
            log.plain("RESOLUTION NOTES")
            for note in self.res.notes:
                log.plain(f"  - {note}")
            log.plain("")
        log.plain("OWNER-DECISION ITEMS (not guessed; see the report tail for the full statement)")
        owner_items = list(self.res.owner_decisions)
        if not self.res.v4_review_inputs_used:
            owner_items.append(
                "The v4 network build recorded NO Politico review-layer inputs "
                "(no current-committee, employment, education, policy-delta or explicit-side "
                "roles in its receipt), so v5 turns those five layers ON for the first time. "
                "That is a scope change, not a reproduction of v4."
            )
        if not DASHBOARD_SECTION.exists():
            owner_items.append(
                f"{DASHBOARD_SECTION} does not exist yet; step dashboard_section will SKIP "
                "with a clear message rather than fail."
            )
        for item in owner_items:
            log.plain(f"  ! {item}")
        if not owner_items:
            log.plain("  (none)")
        log.plain("")

        # per-step plan
        log.plain("=" * 100)
        log.plain("RESOLVED PLAN")
        log.plain("=" * 100)
        missing_inputs: list[str] = []
        existing_outputs: list[str] = []
        for step in self.selected():
            log.plain("")
            log.plain(f"[{step.name}]  handoff step {step.handoff} - {step.title}")
            if step.note:
                log.plain(f"    note   : {step.note}")
            if step.command:
                command = step.command()
                log.plain(f"    cwd    : {step.cwd}")
                log.plain(f"    command: {quote_command(command)}")
            else:
                log.plain(f"    action : in-process ({step.name})")
            for path in step.inputs():
                ok = path.exists()
                marker = "OK     " if ok else "MISSING"
                produced = self.produced_by_chain(path)
                if not ok and produced:
                    marker = "PENDING"
                log.plain(f"    input  {marker} {path}"
                          + (f"   (produced by step {produced})" if produced else ""))
                if not ok and not produced:
                    missing_inputs.append(f"{step.name}: {path}")
            for path in step.optional_inputs():
                log.plain(f"    input  {'OK     ' if path.exists() else 'ABSENT '} {path}   (optional)")
            for path in step.output_dirs():
                if path.exists():
                    log.plain(f"    outdir EXISTS  {path}   <-- REFUSED: never overwrite a generation")
                    existing_outputs.append(f"{step.name}: {path}")
                else:
                    log.plain(f"    outdir CLEAR   {path}")
            for path in step.output_files():
                if path.exists():
                    log.plain(f"    outfile EXISTS {path}   <-- would need --allow-overwrite-reports")
                    if not self.args.allow_overwrite_reports:
                        existing_outputs.append(f"{step.name}: {path}")
                else:
                    log.plain(f"    outfile CLEAR  {path}")
            for path in step.rewrites():
                log.plain(f"    rewrites {'EXISTS ' if path.exists() else 'ABSENT '} {path}"
                          "   (rewritten in place by the tool that owns it)")

        log.plain("")
        log.plain("=" * 100)
        log.plain("DRY-RUN SUMMARY")
        log.plain("=" * 100)
        log.plain(f"  steps planned            : {len(self.selected())}")
        log.plain(f"  missing required inputs  : {len(missing_inputs)}")
        for item in missing_inputs:
            log.plain(f"      - {item}")
        log.plain(f"  blocked outputs          : {len(existing_outputs)}")
        for item in existing_outputs:
            log.plain(f"      - {item}")
        ready = not missing_inputs and not existing_outputs
        crawl_done = self.crawl_complete()
        log.plain(f"  crawl terminal?          : {'YES' if crawl_done else 'NO - --wait would poll'}")
        log.plain(f"  chain executable now?    : "
                  f"{'YES' if (ready and crawl_done) else 'NO'}")
        log.plain("")
        log.plain("Nothing above was executed.  Add --execute (with --wait to block until the crawl")
        log.plain("reaches halted:false / remaining:0) to run it.")
        self.glassbox.emit("finish_chain.dry_run", "info",
                           f"Dry run planned {len(self.selected())} steps for vintage {self.date}",
                           stage="dry_run",
                           metadata={"steps": len(self.selected()),
                                     "missing_inputs": len(missing_inputs),
                                     "blocked_outputs": len(existing_outputs),
                                     "crawl_complete": crawl_done,
                                     "date": self.date})
        return 0

    def produced_by_chain(self, path: Path) -> str | None:
        r = self.res
        text = str(path)
        if text.startswith(str(r.bridge_primary)):
            return "bridge_primary"
        if text.startswith(str(r.bridge_twin)):
            return "bridge_twin"
        if text.startswith(str(r.network_primary)):
            return "network_primary"
        return None

    # ------------------------------------------------------------------ waiting

    def crawl_complete(self) -> bool:
        if sorted(RAW.glob("WATCHDOG_DONE_*.json")):
            return True
        if not STATE_JSON.exists():
            return False
        try:
            state = read_json(STATE_JSON)
        except Exception:
            return False
        return state.get("halted") is False and state.get("remaining") == 0

    def current_halt_files(self) -> list[Path]:
        """Watchdog halt files that are still in effect.

        A halt file is stale -- and must not block the chain forever -- when it is
        OLDER than RAW/state.json: the crawler wrote fresh state after the halt was
        recorded, meaning it recovered from the transient abort on its own.  A halt
        file that is NEWER than state.json (or present while state.json is missing)
        is still current and keeps blocking.
        """
        halts = sorted(RAW.glob("WATCHDOG_HALT_*.json"))
        if not halts or not STATE_JSON.exists():
            return halts
        state_mtime = STATE_JSON.stat().st_mtime
        current = [p for p in halts if p.stat().st_mtime >= state_mtime]
        stale = [p for p in halts if p not in current]
        if stale:
            self.log.write(
                "ignoring stale watchdog halt file(s) (older than state.json, "
                "crawler recovered): " + ", ".join(p.name for p in stale))
        return current

    def wait_for_crawl(self) -> None:
        self.log.write("waiting for terminal crawl state (poll 60 s)")
        self.glassbox.emit("finish_chain.waiting", "waiting",
                           "Waiting for halted:false and remaining:0", stage="wait")
        while True:
            halts = self.current_halt_files()
            if halts:
                self.halt("watchdog halt file present", {"halt_files": [p.name for p in halts]})
            if self.crawl_complete():
                self.log.write("crawl reached terminal state")
                return
            try:
                state = read_json(STATE_JSON)
                self.log.write(f"  remaining={state.get('remaining')} "
                               f"succeeded={state.get('total_succeeded')} "
                               f"halted={state.get('halted')}")
            except Exception as exc:
                self.log.write(f"  state.json unreadable: {exc}")
            time.sleep(60)

    # ------------------------------------------------------------------ execution

    def run_command(self, step: Step, command: list[str]) -> dict[str, Any]:
        self.log.write(f"[{step.name}] START {quote_command(command)}")
        self.glassbox.emit(f"finish_chain.{step.name}", "running",
                           f"{step.handoff} {step.title}", stage=step.name)
        began = utc_now()
        proc = subprocess.run(command, cwd=str(step.cwd), capture_output=True, text=True)
        ended = utc_now()
        record = {
            "command": command,
            "cwd": str(step.cwd),
            "started_utc": iso_utc(began),
            "ended_utc": iso_utc(ended),
            "seconds": round((ended - began).total_seconds(), 3),
            "exit_code": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
        }
        self.log.write(f"[{step.name}] END exit={proc.returncode} "
                       f"seconds={record['seconds']}")
        if proc.returncode != 0:
            for stream in ("stdout", "stderr"):
                head = (record[stream] or "").splitlines()[:40]
                for line in head:
                    self.log.write(f"[{step.name}] {stream}: {line}")
        self.glassbox.emit(
            f"finish_chain.{step.name}", "completed" if proc.returncode == 0 else "failed",
            f"{step.handoff} {step.title} exit={proc.returncode}", stage=step.name,
            metadata={"exit_code": proc.returncode, "seconds": record["seconds"]})
        return record

    @property
    def is_partial_probe(self) -> bool:
        """A single mid-crawl integrity probe: reads only, writes only to a scratch path.

        The handoff itself calls for this after every sustained crawl segment, so it is
        the one mode allowed to run while the crawler is alive.  It is refused unless
        the output goes somewhere other than the receipt the crawl tooling owns.
        """
        return (self.args.once and self.args.frm == "verify_partial"
                and self.verification_output != CRAWL_VERIFICATION)

    def execute(self) -> int:
        if self.is_partial_probe:
            self.log.write("mid-crawl integrity probe: read-only, writing to "
                           f"{self.verification_output}")
            self.log.write("RAW/crawl_verification.json is NOT touched; the crawl is not disturbed")
            step = self.steps[self.step_index("verify_partial")]
            record = self.run_command(step, step.command())  # type: ignore[misc]
            self.results[step.name] = record
            receipt = self.read_verification_output()
            ok, reason = gate_partial_verification(receipt)
            counts = receipt.get("counts") or {}
            coverage = (receipt.get("coverage") or {}).get("all_profiles") or {}
            state = receipt.get("crawl_state") or {}
            self.log.write(f"[verify_partial] status={receipt.get('status')} "
                           f"integrity_status={receipt.get('integrity_status')} "
                           f"completion_status={receipt.get('completion_status')}")
            self.log.write(f"[verify_partial] accounted={counts.get('profiles_accounted')} "
                           f"of {EXPECTED_CORPUS_TOTAL}  unresolved={coverage.get('unresolved')}  "
                           f"state.remaining={state.get('remaining')}")
            self.log.write(f"[verify_partial] GATE {'PASS' if ok else 'FAIL'}: {reason}")
            self.glassbox.emit("finish_chain.verify_partial", "completed" if ok else "blocked",
                               f"Mid-crawl integrity probe: {reason}", stage="verify_partial",
                               metadata={"accounted": counts.get("profiles_accounted"),
                                         "unresolved": coverage.get("unresolved"),
                                         "remaining": state.get("remaining"),
                                         "status": receipt.get("status")})
            return 0 if ok else 3
        if self.args.wait:
            self.wait_for_crawl()
        if not self.crawl_complete():
            self.halt("crawl has not reached halted:false / remaining:0; "
                      "pass --wait to block until it does", self.state_snapshot())
        # The crawl can report remaining:0 a moment before the crawler process itself
        # exits.  In unattended mode give it a bounded grace period to leave on its own;
        # the runner never kills it.
        deadline = time.time() + (15 * 60 if self.args.wait else 0)
        while True:
            crawlers = query_processes(CRAWLER_PROCESS_MARKER)
            if crawlers is None:
                self.halt("could not determine whether a crawler process is still running "
                          "(process query failed); refusing to read its output files")
            if not crawlers:
                break
            if time.time() >= deadline:
                self.halt("a Politico crawler process is still running; the chain will not read "
                          "profiles.ndjson or state.json underneath a live writer "
                          "(the runner never kills processes)",
                          {"pids": [c.get("ProcessId") for c in crawlers]})
            self.log.write(f"crawl is terminal but crawler pids "
                           f"{[c.get('ProcessId') for c in crawlers]} are still up; waiting 30 s")
            time.sleep(30)

        self.glassbox.emit("finish_chain.started", "running",
                           f"Finishing chain started for vintage {self.date}", stage="chain",
                           metadata={"date": self.date, "steps": len(self.selected())})
        for step in self.selected():
            for path in step.output_dirs():
                if path.exists():
                    self.halt(f"output generation already exists: {path}",
                              {"step": step.name, "path": str(path)})
            for path in step.output_files():
                if path.exists() and not self.args.allow_overwrite_reports:
                    self.halt(f"report already exists: {path} "
                              "(pass --allow-overwrite-reports to replace it)",
                              {"step": step.name, "path": str(path)})
            if step.command:
                command = step.command()
                if step.name == "dashboard_section" and not DASHBOARD_SECTION.exists():
                    self.log.write(f"[{step.name}] SKIPPED: {DASHBOARD_SECTION} does not exist yet. "
                                   "Run it by hand once the producer lands: "
                                   f"{quote_command(command)}")
                    self.glassbox.emit("finish_chain.dashboard_section", "skipped",
                                       "Dashboard section producer not present yet",
                                       stage=step.name,
                                       metadata={"expected": str(DASHBOARD_SECTION)})
                    self.results[step.name] = {"skipped": True, "reason": "producer absent"}
                    continue
                for path in step.inputs():
                    if not path.exists():
                        self.halt(f"required input missing: {path}", {"step": step.name})
                record = self.run_command(step, command)
                self.results[step.name] = record
                self.apply_gate(step, record)
            else:
                self.log.write(f"[{step.name}] START in-process action")
                self.glassbox.emit(f"finish_chain.{step.name}", "running",
                                   f"{step.handoff} {step.title}", stage=step.name)
                record = step.action(self)  # type: ignore[misc]
                self.results[step.name] = record
                self.log.write(f"[{step.name}] END {json.dumps(record, default=str)[:400]}")
                self.glassbox.emit(f"finish_chain.{step.name}", "completed",
                                   f"{step.handoff} {step.title}", stage=step.name,
                                   metadata={k: v for k, v in record.items()
                                             if isinstance(v, (int, float, str, bool))})
        self.glassbox.emit("finish_chain.completed", "completed",
                           f"Finishing chain completed for vintage {self.date}", stage="chain")
        self.log.write("chain complete")
        return 0

    def state_snapshot(self) -> dict[str, Any]:
        try:
            state = read_json(STATE_JSON)
        except Exception as exc:
            return {"state_error": str(exc)}
        return {k: state.get(k) for k in ("halted", "remaining", "total_succeeded", "last_updated")}

    def apply_gate(self, step: Step, record: dict[str, Any]) -> None:
        if step.name == "verify_partial":
            receipt = self.read_verification_output()
            ok, reason = gate_partial_verification(receipt)
            self.log.write(f"[{step.name}] GATE {'PASS' if ok else 'FAIL'}: {reason}")
            if not ok:
                self.halt(f"step 5a gate unmet: {reason}", {"step": step.name})
            return
        if step.name == "verify_complete":
            receipt = self.read_verification_output()
            ok, reason = gate_complete_verification(receipt, record["exit_code"])
            self.log.write(f"[{step.name}] GATE {'PASS' if ok else 'FAIL'}: {reason}")
            if not ok:
                self.halt(f"step 5b terminal gate unmet: {reason}", {"step": step.name})
            return
        if record["exit_code"] != 0:
            self.halt(f"{step.name} exited {record['exit_code']}",
                      {"step": step.name,
                       "stdout_head": (record["stdout"] or "").splitlines()[:40],
                       "stderr_head": (record["stderr"] or "").splitlines()[:40]})
        if step.name == "bridge_verify":
            path = self.res.bridge_verification / "verification_report.json"
            report = read_json(path)
            if report.get("status") != "PASS" or report.get("failures"):
                self.halt("bridge verification did not PASS",
                          {"path": str(path), "status": report.get("status"),
                           "failures": report.get("failures")})
            self.log.write(f"[{step.name}] GATE PASS: bridge verification status=PASS")
        if step.name == "network_verify":
            path = self.res.network_verification / "staffer_social_network_verification_receipt.json"
            report = read_json(path)
            if report.get("status") not in (None, "PASS") or report.get("failures"):
                self.halt("network verification did not PASS",
                          {"path": str(path), "status": report.get("status"),
                           "failures": report.get("failures")})
            self.log.write(f"[{step.name}] GATE PASS: network verification failures=[]")

    def read_verification_output(self) -> dict[str, Any]:
        try:
            return read_json(self.verification_output)
        except Exception as exc:
            self.halt(f"could not read the verifier receipt at {self.verification_output}: {exc}")
            raise  # unreachable

    # ------------------------------------------------------------------ actions

    def do_identity(self, primary: Path, twin: Path, manifest_name: str | None,
                    label: str) -> dict[str, Any]:
        if not primary.exists() or not twin.exists():
            self.halt(f"{label} twin comparison needs both generations",
                      {"primary": str(primary), "twin": str(twin)})
        result = compare_generation(primary, twin, manifest_name)
        for name, info in sorted(result["files"].items()):
            state = "IDENTICAL" if info.get("identical") else (
                "ALLOWED-DIFF" if info.get("allowed_difference") else "DIFFERS")
            self.log.write(f"[{label}_identity] {state:12s} {name}")
        if not result["ok"]:
            self.halt(f"{label} twin is not byte-identical", result)
        return {"label": label, "files_compared": len(result["files"]), "ok": True}

    def do_exception_review(self) -> dict[str, Any]:
        receipt = read_json(CRAWL_VERIFICATION)
        exceptions = receipt.get("identity_exceptions") or {}
        renamed = exceptions.get("live_name_changed_same_uuid") or {}
        unavailable = exceptions.get("profile_unavailable_404") or {}
        renamed_rows = renamed.get("rows") or []
        unavailable_rows = unavailable.get("rows") or []
        lines = [
            f"# Politico profile crawl - identity exceptions for review ({self.date})",
            "",
            "This file is a listing, not an adjudication. Every row below was accounted by the",
            "crawl verifier under its stated policy and is reproduced here so the owner can review",
            "each one independently. Nothing in this file promotes, merges, or rejects an identity.",
            "",
            f"Source receipt: `{CRAWL_VERIFICATION}`",
            f"Receipt SHA-256: `{sha256_file(CRAWL_VERIFICATION)}`",
            f"Receipt status: {receipt.get('status')} / integrity {receipt.get('integrity_status')} "
            f"/ completion {receipt.get('completion_status')}",
            "",
            "## LIVE_NAME_CHANGED_SAME_UUID",
            "",
            f"Count reported by the verifier: **{renamed.get('count')}**  "
            f"(rows listed here: {len(renamed_rows)})",
            "",
            f"Verifier policy: {renamed.get('policy') or 'NOT RECORDED IN RECEIPT'}",
            "",
        ]
        if renamed_rows:
            keys = sorted({key for row in renamed_rows for key in row})
            lines.append("| " + " | ".join(keys) + " |")
            lines.append("|" + "|".join(["---"] * len(keys)) + "|")
            for row in renamed_rows:
                lines.append("| " + " | ".join(str(row.get(key, "")) for key in keys) + " |")
        else:
            lines.append("_No rows reported._")
        lines += [
            "",
            "## PROFILE_UNAVAILABLE_404",
            "",
            f"Count reported by the verifier: **{unavailable.get('count')}**  "
            f"(rows listed here: {len(unavailable_rows)})",
            "",
            f"Verifier policy: {unavailable.get('policy') or 'NOT RECORDED IN RECEIPT'}",
            "",
        ]
        if unavailable_rows:
            keys = sorted({key for row in unavailable_rows for key in row})
            lines.append("| " + " | ".join(keys) + " |")
            lines.append("|" + "|".join(["---"] * len(keys)) + "|")
            for row in unavailable_rows:
                lines.append("| " + " | ".join(str(row.get(key, "")) for key in keys) + " |")
        else:
            lines.append("_No rows reported._")
        lines += ["", f"Generated by `{Path(__file__).name}` run `{self.run_id}`.", ""]
        atomic_write_text(self.res.exception_review, "\n".join(lines))
        return {"path": str(self.res.exception_review),
                "live_name_changed_same_uuid": len(renamed_rows),
                "profile_unavailable_404": len(unavailable_rows)}

    def do_reconciliation(self) -> dict[str, Any]:
        r = self.res

        def maybe(path: Path) -> dict[str, Any] | None:
            try:
                return read_json(path)
            except Exception:
                return None

        crawl = maybe(CRAWL_VERIFICATION) or {}
        bridge = maybe(r.bridge_primary / BRIDGE_RECEIPT_NAME) or {}
        bridge_verify = maybe(r.bridge_verification / "verification_report.json") or {}
        network = maybe(r.network_primary / NETWORK_RECEIPT_NAME) or {}
        manifest = maybe(r.network_primary / NETWORK_MANIFEST_NAME) or {}
        network_verify = maybe(
            r.network_verification / "staffer_social_network_verification_receipt.json") or {}

        def value(mapping: dict[str, Any], *keys: str) -> str:
            node: Any = mapping
            for key in keys:
                if not isinstance(node, dict) or key not in node:
                    return "NOT RECORDED IN RECEIPT"
                node = node[key]
            return str(node)

        counts = crawl.get("counts") or {}
        coverage = (crawl.get("coverage") or {}).get("all_profiles") or {}
        committee = (crawl.get("coverage") or {}).get("committee_profiles") or {}
        bridge_status = (bridge.get("counts") or {}).get("status") or {}
        node_universe = network.get("node_universe") or {}
        # A v6 receipt's node universe IS the person universe (D-022): containers,
        # organisations and policy areas moved out to `group_universe` and are
        # rostered in staffer_social_groups.ndjson.gz. Read the counts from
        # whichever block holds them so this report keeps printing real numbers
        # instead of three "NOT RECORDED IN RECEIPT" lines on a v6 generation.
        # Cosmetic: nothing downstream reads this document.
        group_universe = network.get("group_universe") or {}
        edge_counts = network.get("edge_counts") or {}
        overlap = network.get("overlap_rule_check") or {}

        def group_count(key: str) -> str:
            """Container/organization/policy_area counts, whichever block has them."""
            if key in node_universe:
                return value(node_universe, key)
            if key in group_universe:
                return "%s (group_universe)" % value(group_universe, key)
            return "NOT RECORDED IN RECEIPT"

        out: list[str] = []
        out.append(f"# Staffer social network - final reconciliation ({self.date})")
        out.append("")
        out.append(f"Generated {iso_utc()} by `{Path(__file__).name}`, run `{self.run_id}`.")
        out.append("Every figure below is read directly from a receipt written by the tool that")
        out.append("produced the artifact. Nothing here is recomputed, estimated, or inferred.")
        out.append("Every generation named in this document remains REVIEW_REQUIRED, and no")
        out.append("canonical identity or employment promotion was made by this chain.")
        out.append("")
        out.append("## Crawl coverage")
        out.append("")
        out.append("| Measure | Value |")
        out.append("|---|---|")
        out.append(f"| Profiles accounted | {value(counts, 'profiles_accounted')} / {EXPECTED_CORPUS_TOTAL} |")
        out.append(f"| Coverage percent | {value(coverage, 'percent')} |")
        out.append(f"| Unresolved | {value(coverage, 'unresolved')} |")
        out.append(f"| Committee-priority coverage | {value(committee, 'completed')} / {value(committee, 'expected')} |")
        out.append(f"| Content-bearing profiles | {value(counts, 'content_bearing_profiles')} |")
        out.append(f"| Employment-history records | {value(counts, 'employment_history_records')} |")
        out.append(f"| Education records | {value(counts, 'education_records')} |")
        out.append(f"| Allowed live-404 exceptions | {value(counts, 'allowed_profile_unavailable_404')} |")
        out.append(f"| Same-UUID name changes | {value(counts, 'same_uuid_name_changes')} |")
        out.append(f"| Hard crawl failures | {value(counts, 'hard_crawl_failures')} |")
        out.append(f"| Verifier status | {value(crawl, 'status')} |")
        out.append(f"| Integrity status | {value(crawl, 'integrity_status')} |")
        out.append(f"| Completion status | {value(crawl, 'completion_status')} |")
        out.append(f"| Unmet terminal requirements | {value(crawl, 'completion_gate', 'unmet_requirement_count')} |")
        out.append("")
        out.append("## Strict Politico/payroll bridge")
        out.append("")
        out.append("| Measure | Value |")
        out.append("|---|---|")
        out.append(f"| Generation | `{r.bridge_primary.name}` |")
        out.append(f"| Receipt status | {value(bridge, 'status')} |")
        out.append(f"| Review status | {value(bridge, 'review_status')} |")
        out.append(f"| Profiles | {value(bridge, 'counts', 'politico_profiles')} |")
        out.append(f"| LINKED | {bridge_status.get('LINKED', 'NOT RECORDED IN RECEIPT')} |")
        out.append(f"| AMBIGUOUS | {bridge_status.get('AMBIGUOUS', 'NOT RECORDED IN RECEIPT')} |")
        out.append(f"| NOT_ON_CURRENT_PAYROLL | {bridge_status.get('NOT_ON_CURRENT_PAYROLL', 'NOT RECORDED IN RECEIPT')} |")
        out.append(f"| NO_SUPPORTED_CURRENT_ROLE | {bridge_status.get('NO_SUPPORTED_CURRENT_ROLE', 'NOT RECORDED IN RECEIPT')} |")
        out.append(f"| Unique linked spine people | {value(bridge, 'counts', 'unique_linked_spine_people')} |")
        out.append(f"| Policy memberships | {value(bridge, 'counts', 'policy_memberships')} |")
        out.append(f"| Current committee assertions | {value(bridge, 'counts', 'current_committee_assertions')} |")
        out.append(f"| Canonical identity promotions | {value(bridge, 'canonical_identity_promotions')} |")
        out.append(f"| Canonical employment promotions | {value(bridge, 'canonical_employment_promotions')} |")
        out.append(f"| Negative-control rate | {value(bridge, 'negative_control', 'rate')} |")
        out.append(f"| Independent verifier | {value(bridge_verify, 'status')} |")
        out.append("")
        out.append("## Separated-layer social network")
        out.append("")
        out.append("| Measure | Value |")
        out.append("|---|---|")
        out.append(f"| Generation | `{r.network_primary.name}` |")
        out.append(f"| Config name | {value(network, 'config_name')} |")
        out.append(f"| Vintage | {value(network, 'vintage')} |")
        out.append(f"| Receipt status | {value(network, 'status')} |")
        out.append(f"| Review status | {value(network, 'review_status')} |")
        out.append(f"| Layers | {', '.join(network.get('layers') or []) or 'NOT RECORDED IN RECEIPT'} |")
        out.append(f"| Nodes (total) | {value(node_universe, 'total')} |")
        out.append(f"| Person nodes | {value(node_universe, 'person')} |")
        out.append(f"| Container nodes | {group_count('container')} |")
        out.append(f"| Organization nodes | {group_count('organization')} |")
        out.append(f"| Policy-area nodes | {group_count('policy_area')} |")
        out.append(f"| Groups (total) | {value(group_universe, 'total')} |")
        out.append(f"| Edge rows emitted | {value(edge_counts, 'total_rows_emitted')} |")
        out.append(f"| co_tenure guaranteed | {value(edge_counts, 'co_tenure_guaranteed')} |")
        out.append(f"| co_tenure possible-only (zero weight) | {value(edge_counts, 'co_tenure_possible_only_zero_weight')} |")
        out.append(f"| membership | {value(edge_counts, 'membership')} |")
        out.append(f"| revolving | {value(edge_counts, 'revolving')} |")
        out.append(f"| policy_area_membership | {value(edge_counts, 'policy_area_membership')} |")
        out.append(f"| **Zero-overlap pairs REJECTED** | {value(overlap, 'pairs_REJECTED_for_no_overlap')} |")
        out.append(f"| Rejection share of candidates | {value(overlap, 'rejection_share_of_candidates')} |")
        out.append(f"| Zero-overlap edges emitted | {value(network, 'zero_overlap_edges_emitted')} |")
        out.append(f"| Canonical identity promotions | {value(network, 'canonical_identity_promotions')} |")
        out.append(f"| Canonical employment promotions | {value(network, 'canonical_employment_promotions')} |")
        out.append(f"| Independent verifier failures | {len(network_verify.get('failures') or [])} |")
        out.append("")
        out.append("## Hashes")
        out.append("")
        out.append("| Artifact | SHA-256 |")
        out.append("|---|---|")
        hashed: list[tuple[str, Path]] = []
        for directory in (r.bridge_primary, r.network_primary, r.bridge_verification,
                          r.network_verification):
            if directory.exists():
                for path in sorted(directory.iterdir()):
                    if path.is_file():
                        hashed.append((f"{directory.name}/{path.name}", path))
        for label, path in hashed:
            out.append(f"| `{label}` | `{sha256_file(path)}` |")
        if not hashed:
            out.append("| _no artifacts found_ | |")
        out.append("")
        out.append("## Limitations")
        out.append("")
        out.append("Copied verbatim from the receipts; not reworded here.")
        out.append("")
        for label, text in (
            ("Network statement", network.get("statement")),
            ("Bridge identity rule", bridge.get("identity_rule")),
            ("Bridge temporal rule", bridge.get("temporal_rule")),
            ("Overlap rule", overlap.get("rule")),
            ("Overlap control", overlap.get("control")),
            ("Live-404 policy",
             ((crawl.get("identity_exceptions") or {}).get("profile_unavailable_404") or {}).get("policy")),
            ("Same-UUID rename policy",
             ((crawl.get("identity_exceptions") or {}).get("live_name_changed_same_uuid") or {}).get("policy")),
            ("Promotion policy", network.get("promotion_policy")),
            ("Dial status", (manifest.get("dials") or {}).get("every_value_above")),
        ):
            if text:
                out.append(f"- **{label}.** {text}")
        out.append("")
        out.append("## Next steps")
        out.append("")
        out.append(f"1. Refresh the dashboard section data: `python fec\\surfaces\\build_staffer_network_section.py "
                   f"--generation {r.network_primary.name}` from the live tree.")
        out.append("2. Rebuild the combined dashboard: `python fec\\run_pipeline.py --from make_combined.py` "
                   "from the live tree, only when no other `run_pipeline.py` process exists and "
                   "`.pipeline_run.lock` is not live.")
        out.append(f"3. Owner review of every identity exception listed in "
                   f"`{r.exception_review.name}` (this chain lists them; it adjudicates none).")
        out.append("4. Owner decision on whether the Politico review layers (current-committee, "
                   "employment, education, policy-delta and explicit-side assertions), which this "
                   "generation turns on for the first time, may inform any published surface.")
        out.append("5. Owner decision on dial freeze: the network manifest still reports "
                   "`UNTESTED_DEFAULTS_PENDING_FREEZE`.")
        out.append("6. Canonical promotion remains owner-gated; every generation named here stays "
                   "REVIEW_REQUIRED.")
        out.append("")
        atomic_write_text(r.reconciliation, "\n".join(out))

        addendum = [
            "",
            f"## Final reconciliation {self.date}",
            "",
            f"The post-crawl finishing chain completed on {self.date} and wrote its full",
            f"reconciliation to `{r.reconciliation.name}` in this directory. That document carries the",
            "final crawl coverage, the bridge and network counts, the SHA-256 of every primary",
            "artifact and verification receipt, the limitations copied from the receipts, and the",
            "remaining owner-gated next steps.",
            "",
            f"New generations: `{r.bridge_primary.name}`, `{r.network_primary.name}`, with byte-identical",
            "twins and independent verification receipts. Nothing was promoted to canonical and every",
            "generation remains REVIEW_REQUIRED.",
            "",
            f"Chain log: `{self.log.path.name}`. Chain run id: `{self.run_id}`.",
            "",
        ]
        atomic_append_text(V4_COMPLETION_DOC, "\n".join(addendum))
        return {"reconciliation": str(r.reconciliation),
                "appended_to": str(V4_COMPLETION_DOC),
                "artifacts_hashed": len(hashed)}

    # ------------------------------------------------------------------ dashboard

    def pipeline_lock_status(self) -> tuple[str, str]:
        if not PIPELINE_LOCK.exists():
            return "FREE", "(no lock file)"
        try:
            payload = read_json(PIPELINE_LOCK)
        except Exception as exc:
            return "BLOCKED", f"(unreadable: {exc}; failing closed)"
        pid = payload.get("pid")
        if pid is None:
            return "BLOCKED", "(lock has no pid; failing closed)"
        alive = process_is_alive(int(pid))
        if alive is True:
            return "LIVE", f"(owner pid {pid} is alive, owner_kind={payload.get('owner_kind')})"
        if alive is False:
            return "STALE", (f"(owner pid {pid} is not alive; run_pipeline recovers stale leases "
                             "itself - this runner never removes a lock)")
        return "BLOCKED", f"(owner pid {pid} liveness undeterminable; failing closed)"

    def do_pipeline(self) -> dict[str, Any]:
        deadline = time.time() + 2 * 60 * 60
        attempt = 0
        while True:
            attempt += 1
            procs = query_processes(RUN_PIPELINE_MARKER)
            status, detail = self.pipeline_lock_status()
            blocked_reasons = []
            if procs is None:
                blocked_reasons.append("run_pipeline process query failed (failing closed)")
            elif procs:
                blocked_reasons.append(
                    f"run_pipeline.py already running: pids {[p.get('ProcessId') for p in procs]}")
            if status in ("LIVE", "BLOCKED"):
                blocked_reasons.append(f".pipeline_run.lock {status} {detail}")
            if not blocked_reasons:
                step = Step("dashboard_pipeline", "D2", "combined dashboard",
                            command=self.res.cmd_run_pipeline, cwd=LT)
                record = self.run_command(step, self.res.cmd_run_pipeline())
                tail = (record["stdout"] or "").splitlines()[-40:]
                for line in tail:
                    self.log.write(f"[dashboard_pipeline] tail: {line}")
                audit_lines = [line for line in (record["stdout"] or "").splitlines()
                               if re.search(r"\bpassed\b.*\bFAILED\b|AUDIT|audit_full", line)]
                for line in audit_lines[-10:]:
                    self.log.write(f"[dashboard_pipeline] audit: {line}")
                if record["exit_code"] != 0:
                    self.halt("run_pipeline.py --from make_combined.py failed",
                              {"exit_code": record["exit_code"], "tail": tail})
                return {"ran": True, "exit_code": record["exit_code"],
                        "audit_lines": audit_lines[-10:], "tail": tail[-10:]}
            reason = "; ".join(blocked_reasons)
            self.log.write(f"[dashboard_pipeline] WAITING ({attempt}): {reason}")
            self.glassbox.emit("finish_chain.dashboard_pipeline", "waiting",
                               f"Waiting for the pipeline writer lease: {reason}"[:900],
                               stage="dashboard_pipeline", metadata={"attempt": attempt})
            if time.time() >= deadline:
                note = SN / f"FINISH_CHAIN_PIPELINE_WAITING_{utc_stamp()}.json"
                atomic_write_text(note, json.dumps({
                    "schema_id": "staffer-network-finish-chain-waiting-v1",
                    "run_id": self.run_id,
                    "written_at": iso_utc(),
                    "reason": reason,
                    "attempts": attempt,
                    "next_action": ("rerun with --from dashboard_pipeline --execute once the other "
                                    "pipeline writer has finished; never remove the lock by hand"),
                }, indent=2, sort_keys=True) + "\n")
                self.log.write(f"[dashboard_pipeline] gave up after 2 h; wrote {note}")
                return {"ran": False, "waiting_note": str(note), "reason": reason,
                        "attempts": attempt}
            time.sleep(300)


# --------------------------------------------------------------------------- cli


def build_argparser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Post-crawl finishing chain for the staffer social network.")
    ap.add_argument("--execute", action="store_true",
                    help="actually run the chain (default is a dry run)")
    ap.add_argument("--dry-run", action="store_true",
                    help="explicitly request the default dry run")
    ap.add_argument("--wait", action="store_true",
                    help="poll state.json every 60 s until halted:false and remaining:0")
    ap.add_argument("--from", dest="frm", default=None, help="resume at this named step")
    ap.add_argument("--once", action="store_true", help="run only the first selected step")
    ap.add_argument("--date", default=None, help="YYYYMMDD vintage override")
    ap.add_argument("--generated-at", default=None,
                    help="fixed ISO instant shared by the network primary and twin")
    ap.add_argument("--python", default=None, help="interpreter to invoke (default: this one)")
    ap.add_argument("--verification-output", default=None,
                    help="write the crawl verifier receipt here instead of RAW/crawl_verification.json")
    ap.add_argument("--allow-overwrite-reports", action="store_true",
                    help="permit replacing an existing markdown report (never a generation dir)")
    ap.add_argument("--no-glassbox", action="store_true", help="suppress glassbox events")
    ap.add_argument("--list-steps", action="store_true", help="print the step names and exit")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    args = build_argparser().parse_args(argv)
    if args.once and not args.frm:
        args.frm = "verify_partial"
    # A --once verify_partial run must never touch the receipt another process owns.
    if args.once and args.frm == "verify_partial" and not args.verification_output:
        scratch = SN / "finish_chain_scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        args.verification_output = str(scratch / f"crawl_verification_partial_{utc_stamp()}.json")
    chain = Chain(args)
    if args.list_steps:
        for step in chain.steps:
            print(f"{step.name:20s} handoff {step.handoff:3s} {step.title}")
        return 0
    try:
        if args.execute:
            return chain.execute()
        return chain.dry_run()
    except ChainHalt as halt:
        path = chain.write_halt_file(halt.reason, halt.detail)
        chain.log.write(f"HALT: {halt.reason}")
        chain.log.write(f"halt file: {path}")
        chain.glassbox.emit("finish_chain.halted", "blocked",
                            f"Chain halted: {halt.reason}"[:900], stage="chain",
                            metadata={"halt_file": str(path)})
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
