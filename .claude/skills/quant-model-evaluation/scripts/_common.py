# -*- coding: utf-8 -*-
"""Shared plumbing for the quant-model-evaluation scripts.

Every script in this folder evaluates; none of them changes what it evaluates.
A script reads the files it is given and writes only inside a fresh run
directory under ``--out``. It never overwrites a file, and it reports through
one verdict vocabulary so results from different scripts can be stacked in a
single audit report.

Verdicts (per check):
  SURVIVES         tested, and the assumption or claim holds within the stated criterion
  WOUNDED          holds only in part: fragile, scope-limited, or repairable by rewording
  KILLED           tested and violated, and the violation is material
  UNVERIFIED-HERE  could not be tested with the access, data or tools at hand; never a pass

Exit codes:
  0  finished; every check SURVIVES
  1  finished; at least one WOUNDED or KILLED check
  2  usage error or unreadable input; nothing was evaluated
  3  finished; no negative verdicts, but at least one UNVERIFIED-HERE check,
     or no check was evaluated at all

A KILLED printed by a script is a candidate verdict: an audit report records it
only after a second independent reader confirms it.

Privacy: provenance paths under the user's home directory are written with the
home prefix replaced by "~".

Glass Box: when the shared event directory exists (``~/.claude/glassbox/events``)
or ``GLASSBOX_EVENTS_DIR`` is set, each script emits started / stage / completed
/ failed events there, one atomic JSON file per event. Set ``QME_GLASSBOX=0`` or
pass ``--no-glassbox`` to switch emission off. Emission can never break a run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import platform
import sys
import time
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from importlib import metadata as _md
from typing import Any, Callable, Iterable, Sequence

SKILL = "quant-model-evaluation"
VERSION = "1.0.0"

SURVIVES = "SURVIVES"
WOUNDED = "WOUNDED"
KILLED = "KILLED"
UNVERIFIED = "UNVERIFIED-HERE"
VERDICTS = (SURVIVES, WOUNDED, KILLED, UNVERIFIED)

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXIT_UNVERIFIED = 3


class UsageError(Exception):
    """Bad arguments or unreadable input. Maps to exit code 2."""


# --------------------------------------------------------------------------- #
# Glass Box emission
# --------------------------------------------------------------------------- #
_GLASSBOX_ON = os.environ.get("QME_GLASSBOX", "1") != "0"


def _events_dir() -> pathlib.Path | None:
    if not _GLASSBOX_ON:
        return None
    override = os.environ.get("GLASSBOX_EVENTS_DIR")
    if override:
        return pathlib.Path(override)
    default = pathlib.Path.home() / ".claude" / "glassbox" / "events"
    # Only emit on machines that already run a Glass Box; never create one.
    return default if default.parent.exists() else None


def _stamp() -> str:
    t = time.time()
    return time.strftime("%Y%m%dT%H%M%S", time.gmtime(t)) + f"{t % 1:.7f}"[2:9] + "Z"


def _iso() -> str:
    t = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + f"{t % 1:.7f}"[1:9] + "Z"


def disable_glassbox() -> None:
    global _GLASSBOX_ON
    _GLASSBOX_ON = False


def emit(kind: str, status: str, summary: str, *, run_id: str = "", source: str = SKILL,
         stage: str = "", detail: str = "", current: int = -1, total: int = -1,
         duration_ms: int = -1, metadata: dict | None = None) -> str | None:
    """Write one Glass Box event. Returns its id, or None when not emitted."""
    try:
        events = _events_dir()
        if events is None:
            return None
        events.mkdir(parents=True, exist_ok=True)
        eid = f"evt-{_stamp()}-{uuid.uuid4().hex[:10]}"
        payload: dict[str, Any] = {
            "schema_version": 1,
            "id": eid,
            "timestamp_utc": _iso(),
            "run_id": run_id,
            "correlation_id": "",
            "parent_id": "",
            "lane": os.environ.get("QME_GLASSBOX_LANE", "claude"),
            "source": source,
            "kind": kind,
            "status": status,
            "stage": stage,
            "summary": summary[:400],
            "detail": detail[:2000],
            "cwd": os.getcwd(),
            "duration_ms": int(duration_ms),
            "bytes": -1,
            "metadata": metadata,
        }
        if int(current) >= 0:
            payload["current"] = int(current)
        if int(total) >= 0:
            payload["total"] = int(total)
        final = events / f"{eid}.json"
        tmp = events / f".{eid}.{os.getpid()}.tmp"
        tmp.write_text(json.dumps(payload, ensure_ascii=False, default=str),
                       encoding="utf-8", newline="\n")
        os.replace(tmp, final)
        return eid
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Files: hashing, run directories, write-once output
# --------------------------------------------------------------------------- #
def sha256_file(path: str | os.PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def require_file(path: str | os.PathLike, what: str = "input") -> pathlib.Path:
    """Resolve an input path; refuse URLs, directories and missing files."""
    text = str(path)
    if "://" in text:
        raise UsageError(f"{what} must be a local file, not a URL: {text}")
    p = pathlib.Path(text).expanduser()
    if not p.is_file():
        raise UsageError(f"{what} not found or not a file: {text}")
    return p.resolve()


def make_run_dir(out: str | os.PathLike, script: str) -> pathlib.Path:
    """Create a fresh, uniquely named run directory under ``out``."""
    base = pathlib.Path(out).expanduser().resolve()
    if base.exists() and not base.is_dir():
        raise UsageError(f"--out must be a directory: {base}")
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run = base / f"{script}-{stamp}-{os.getpid()}"
    run.mkdir(parents=True, exist_ok=False)
    return run


def write_once(path: pathlib.Path, text: str) -> pathlib.Path:
    """Atomically write a new file; never replace an existing one.

    On Windows an indexer, antivirus scan or sync client can hold a fresh temp
    file for a moment, so the final rename is retried briefly on PermissionError.
    """
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    delay = 0.05
    for attempt in range(6):
        try:
            os.replace(tmp, path)
            return path
        except PermissionError:
            if attempt == 5:
                raise
            time.sleep(delay)
            delay *= 2
    return path


# --------------------------------------------------------------------------- #
# Environment facts for the provenance block
# --------------------------------------------------------------------------- #
def pkg_version(name: str) -> str | None:
    try:
        return _md.version(name)
    except _md.PackageNotFoundError:
        return None


def optional_import(module: str):
    """Import a module if it is installed; return None otherwise."""
    try:
        return __import__(module, fromlist=["_"])
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Checks and reports
# --------------------------------------------------------------------------- #
@dataclass
class Check:
    id: str
    title: str
    verdict: str
    criterion: str = ""
    value: Any = None
    evidence: str = "[RUN]"
    detail: str = ""

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise ValueError(f"unknown verdict {self.verdict!r}; use one of {VERDICTS}")


@dataclass
class Report:
    script: str
    argv: Sequence[str] = field(default_factory=lambda: list(sys.argv))
    seed: int | None = None
    inputs: list[dict] = field(default_factory=list)
    packages: dict[str, str | None] = field(default_factory=dict)
    checks: list[Check] = field(default_factory=list)
    sections: list[tuple[str, str]] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    started_utc: str = field(default_factory=_iso)

    def add_input(self, path: str | os.PathLike) -> None:
        p = pathlib.Path(path)
        self.inputs.append({"path": _redact_home(str(p)), "bytes": p.stat().st_size,
                            "sha256": sha256_file(p)})

    def note_packages(self, names: Iterable[str]) -> None:
        for n in names:
            self.packages[n] = pkg_version(n)

    def add(self, check: Check) -> Check:
        self.checks.append(check)
        return check

    def section(self, title: str, markdown: str) -> None:
        self.sections.append((title, markdown))

    def counts(self) -> dict[str, int]:
        return {v: sum(1 for c in self.checks if c.verdict == v) for v in VERDICTS}

    def exit_code(self) -> int:
        c = self.counts()
        if c[KILLED] or c[WOUNDED]:
            return EXIT_FINDINGS
        if c[UNVERIFIED] or not self.checks:  # nothing evaluated is never a pass
            return EXIT_UNVERIFIED
        return EXIT_OK

    def provenance(self) -> dict[str, Any]:
        return {
            "skill": SKILL,
            "skill_version": VERSION,
            "script": self.script,
            "argv": [_redact_home(str(a)) for a in self.argv],
            "started_utc": self.started_utc,
            "finished_utc": _iso(),
            "seed": self.seed,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "packages": self.packages,
            "inputs": self.inputs,
        }

    def provenance_line(self) -> str:
        pins = ", ".join(f"{pathlib.Path(i['path']).name} sha256:{i['sha256'][:12]}" for i in self.inputs) or "no file inputs"
        return (f"{SKILL} {VERSION} · {self.script} · seed {self.seed if self.seed is not None else 'n/a'} · "
                f"{pins} · python {sys.version.split()[0]} · {self.started_utc}")

    def to_json(self) -> str:
        payload = {"provenance": self.provenance(), "counts": self.counts(),
                   "checks": [asdict(c) for c in self.checks], "data": self.data}
        # Strict JSON: NaN and infinities become null instead of bare NaN tokens.
        return json.dumps(_finite(payload), indent=2, ensure_ascii=False,
                          allow_nan=False, default=_json_default)

    def to_markdown(self) -> str:
        c = self.counts()
        lines = [f"# {self.script} report", "",
                 f"Provenance: {self.provenance_line()}", "",
                 "Verdicts: " + ", ".join(f"{k} {v}" for k, v in c.items()), "",
                 "| id | check | verdict | value | criterion | evidence |",
                 "|---|---|---|---|---|---|"]
        for ch in self.checks:
            lines.append(f"| {ch.id} | {_md_cell(ch.title)} | {ch.verdict} | {_md_cell(_fmt(ch.value))} | "
                         f"{_md_cell(ch.criterion)} | {ch.evidence} |")
        details = [ch for ch in self.checks if ch.detail]
        if details:
            lines += ["", "## Details", ""]
            lines += [f"- **{ch.id}** ({ch.verdict}): {ch.detail}" for ch in details]
        for title, body in self.sections:
            lines += ["", f"## {title}", "", body.rstrip()]
        return "\n".join(lines) + "\n"

    def write(self, run_dir: pathlib.Path) -> tuple[pathlib.Path, pathlib.Path]:
        j = write_once(run_dir / "report.json", self.to_json())
        m = write_once(run_dir / "report.md", self.to_markdown())
        return j, m


def _redact_home(text: str) -> str:
    """Replace the user's home directory prefix with "~" (it carries the account name)."""
    try:
        home = str(pathlib.Path.home())
    except Exception:
        return text
    if not home or len(home) < 3:
        return text
    for variant in {home, home.replace("\\", "/")}:
        if text.lower().startswith(variant.lower()):
            return "~" + text[len(variant):]
    return text


def _fmt(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.6g}"
    return str(v)


def _md_cell(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def _json_default(o: Any) -> Any:
    for attr in ("item", "tolist"):  # numpy scalars and arrays
        if hasattr(o, attr):
            try:
                return _finite(getattr(o, attr)())
            except Exception:
                pass
    return str(o)


def _finite(o: Any) -> Any:
    """Recursively replace NaN and +/-inf with None so the output is strict JSON."""
    if isinstance(o, float):
        return o if math.isfinite(o) else None
    if isinstance(o, dict):
        return {k: _finite(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_finite(v) for v in o]
    if hasattr(o, "dtype") and hasattr(o, "tolist"):  # numpy scalars and arrays
        try:
            return _finite(o.tolist())
        except Exception:
            return o
    return o


# --------------------------------------------------------------------------- #
# CLI scaffolding
# --------------------------------------------------------------------------- #
def base_parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default="qme_out",
                   help="directory under which a fresh run folder is created (default: ./qme_out)")
    p.add_argument("--seed", type=int, default=20260930, help="random seed, recorded in the report")
    p.add_argument("--no-glassbox", action="store_true", help="do not emit Glass Box events")
    p.add_argument("--quiet", action="store_true", help="print only the report path and verdict counts")
    return p


def _harden_stdio() -> None:
    """Keep a console code page from turning a finished report into a crash.

    On Windows a piped stdout is often cp1252, and printing characters such as
    ≥, σ or √ would raise UnicodeEncodeError after the report was already
    written. Unencodable characters are escaped instead.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="backslashreplace")
        except Exception:
            pass


def run_main(script: str, main: Callable[[argparse.Namespace, Report, pathlib.Path, str], None],
             parser: argparse.ArgumentParser, argv: Sequence[str] | None = None) -> int:
    """Parse args, create the run dir, call ``main``, write the report, emit events.

    ``main(args, report, run_dir, run_id)`` fills ``report`` (checks, sections,
    data) and may write extra artifacts into ``run_dir`` with ``write_once``.
    """
    _harden_stdio()
    args = parser.parse_args(argv)
    if getattr(args, "no_glassbox", False):
        disable_glassbox()
    run_id = f"qme-{script}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{os.getpid()}"
    src = f"{SKILL}/{script}"
    t0 = time.time()
    emit("task", "started", f"{script} started", run_id=run_id, source=src)
    report = Report(script=script, seed=getattr(args, "seed", None))
    try:
        run_dir = make_run_dir(args.out, script)
        main(args, report, run_dir, run_id)
        j, m = report.write(run_dir)
    except UsageError as exc:
        print(f"usage error: {exc}", file=sys.stderr)
        emit("task", "failed", f"{script}: usage error", run_id=run_id, source=src, detail=str(exc),
             duration_ms=int((time.time() - t0) * 1000))
        return EXIT_USAGE
    except Exception as exc:  # unexpected failure: report it loudly, never as a pass
        print(f"error: {exc}", file=sys.stderr)
        traceback.print_exc()
        emit("task", "failed", f"{script}: {type(exc).__name__}", run_id=run_id, source=src,
             detail=traceback.format_exc()[-2000:], duration_ms=int((time.time() - t0) * 1000))
        return EXIT_USAGE
    counts = report.counts()
    code = report.exit_code()
    summary = f"{script}: " + (", ".join(f"{k} {v}" for k, v in counts.items() if v)
                               or "no checks evaluated")
    emit("task", "completed", summary, run_id=run_id, source=src,
         detail=str(m), duration_ms=int((time.time() - t0) * 1000), metadata={"exit_code": code})
    if getattr(args, "quiet", False):
        print(f"{m}\n{summary}")
    else:
        print(report.to_markdown())
        print(f"report: {m}")
    return code
