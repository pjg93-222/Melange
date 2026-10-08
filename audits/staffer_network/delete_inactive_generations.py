# -*- coding: utf-8 -*-
"""
delete_inactive_generations.py
===============================

Safety-gate companion to build_generation_registry.py. That script is
READ-ONLY: it inventories audits\\staffer_network (Store 1) and writes
generation_registry_20260906.json / .md / _inactive.txt, the last one being
Paul's delete-candidate list. This script is the *only* thing in this repo
that is allowed to actually delete one of those candidate directories, and
it does so in two separate, explicit modes:

  --check    Fully re-verifies every directory currently listed in
             generation_registry_20260906_inactive.txt against six
             independent gates (a-f below), then writes a delete plan
             (generation_registry_20260906_delete_plan.json). DELETES
             NOTHING. Safe to run at any time, as often as needed. Its only
             side effects are: re-running build_generation_registry.py (which
             overwrites its own three output files with fresh disk-state
             data -- expected and required, not a bug) and writing the plan
             file.

  --execute  Reads a plan written by --check and deletes exactly its
             DELETE-verdict directories. THIS DELETES DATA. It must only be
             run by Paul, directly, after reading the plan and the KEEP list
             --check printed. It is never invoked automatically by an
             assistant or agent.

-----------------------------------------------------------------------------
THE SIX GATES (a candidate is KEPT -- i.e. NOT deleted -- if ANY fire)
-----------------------------------------------------------------------------
  a. Must resolve to a DIRECT child of audits\\staffer_network\\ with
     exactly that name (exact case, verified against a fresh os.listdir of
     Store 1). Symlinks, junctions, and any other reparse point are refused
     outright, whatever else is true about them.
  b. Referenced anywhere. Content grep (case-sensitive substring of the
     directory's exact name) across:
       - LIVE\\fec\\**\\*.py, *.tpl, *.json           (recursive)
       - LIVE\\data\\engine\\*.json                    (top level only)
       - LIVE\\audits\\staffer_network\\*.py           (top level only, this
         script itself excluded)
       - LIVE\\data\\staffer_network\\**\\*            (recursive, ALL files)
       - LIVE\\audits\\*.md                            (top level only)
       - any file named *_current.json anywhere under LIVE\\data\\ or
         LIVE\\audits\\ (recursive; these are the "pointer" files)
     This is intentionally BROADER than build_generation_registry.py's own
     referenced_by scan (which skips *.json under fec\\, skips non-json under
     data\\staffer_network\\, and has no *_current.json pass) -- this is the
     last gate before deletion, so it errs toward finding more references,
     not fewer.
  c. The FRESH registry (build_generation_registry.py re-run moments ago, so
     it reflects disk right now) must still class the directory INACTIVE.
     If something changed since the reviewed inactive.txt was produced --
     new code now references it, it became newest-of-family, etc. -- this
     gate alone forces KEEP.
  d. Raw capture. Name contains raw/crawl/download/snapshot/sod/
     ledger_source (case-insensitive), or the directory holds a .pdf/.csv/
     .html/.htm file anywhere inside it. Checked independently by walking
     the directory here, not by trusting the registry's is_raw_capture flag.
  e. Freshness / in-flight. Newest mtime anywhere inside is under 48h old,
     OR a *.lock file exists anywhere inside, OR a glassbox event under
     C:\\Users\\pgoff\\.claude\\glassbox\\events\\ from the last 3 hours has
     status "running" and its content mentions the directory's name.
  f. Hard denylist (substring match against the exact name):
       20260905_v5, hill_personnel_spine_20260903_v6,
       hill_personnel_spine_20260903_v5, tiered_corroboration_sidecar_20260902,
       exploratory_temporal_tier_20260902, house_personnel_ledger_20260903_v5,
       politico_profile_crawl, name_standard, generation_registry

If NONE of (a)-(f) fire, the verdict is DELETE.

-----------------------------------------------------------------------------
OUTPUTS (written into Store 1, next to this script)
-----------------------------------------------------------------------------
  --check    generation_registry_20260906_delete_plan.json
             (also indirectly rewrites generation_registry_20260906.json /
             .md / _inactive.txt, via re-running build_generation_registry.py)
  --execute  generation_registry_20260906_delete_receipt.json
             (also re-runs build_generation_registry.py again at the end)

-----------------------------------------------------------------------------
--execute DETAILS (written for completeness; NEVER invoked by an assistant)
-----------------------------------------------------------------------------
  1. Reads the plan and refuses (status "blocked", no deletions attempted)
     if sha256(plan file bytes) != the --plan-sha argument. The plan's own
     sha256 is printed by --check and must be copied verbatim.
  2. Immediately before deleting each directory, re-checks ONLY (a), (e),
     and (f) -- the three gates whose state can change in seconds. (b)/(c)/
     (d) already got a full corpus/registry rebuild moments earlier in
     --check and are not cheap enough to redo per-directory here.
  3. Deletes DELETE-verdict directories largest-first via shutil.rmtree,
     with an onerror/onexc handler that clears the read-only bit and
     retries, up to 3 attempts with 5s sleeps (OneDrive/AV transient
     locks). A directory that still exists after 3 attempts is recorded
     FAILED and left alone -- never forced.
  4. Confirms each deleted path is actually gone (does not just trust the
     absence of an exception).
  5. Writes generation_registry_20260906_delete_receipt.json: per-directory
     DELETED / FAILED / KEPT, bytes freed, free bytes on C: before/after,
     timestamps, and the plan sha256 used.
  6. Emits glassbox running/completed/failed/blocked events via
     C:\\Users\\pgoff\\.claude\\glassbox\\emit.ps1 (named CLI parameters --
     the Python-side equivalent of that script's usual hashtable splatting).
  7. Re-runs build_generation_registry.py once more so the registry reflects
     the post-delete state.

Run (read-only, safe):
    python delete_inactive_generations.py --check

Run (DESTRUCTIVE -- Paul only, never automated):
    python delete_inactive_generations.py --execute --plan-sha <hex from --check>
"""

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_ABS_PATH = os.path.abspath(__file__)
SCRIPT_NAME = os.path.basename(__file__)

# ---------------------------------------------------------------------------
# Paths -- mirrors build_generation_registry.py's own constants exactly, so
# the two scripts always agree on where Store 1 / Store 2 / fec live and on
# the registry's three output filenames.
# ---------------------------------------------------------------------------
LIVE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
STORE1 = os.path.join(LIVE, "audits", "staffer_network")
STORE2 = os.path.join(LIVE, "data", "staffer_network")
FEC_DIR = os.path.join(LIVE, "fec")

BUILD_SCRIPT_NAME = "build_generation_registry.py"
BUILD_SCRIPT_PATH = os.path.join(STORE1, BUILD_SCRIPT_NAME)

OUT_JSON = os.path.join(STORE1, "generation_registry_20260906.json")
OUT_MD = os.path.join(STORE1, "generation_registry_20260906.md")
OUT_INACTIVE = os.path.join(STORE1, "generation_registry_20260906_inactive.txt")
OUT_PLAN = os.path.join(STORE1, "generation_registry_20260906_delete_plan.json")
OUT_RECEIPT = os.path.join(STORE1, "generation_registry_20260906_delete_receipt.json")

GLASSBOX_ROOT = r"C:\Users\pgoff\.claude\glassbox"
GLASSBOX_EVENTS_DIR = os.path.join(GLASSBOX_ROOT, "events")
GLASSBOX_EMIT_PS1 = os.path.join(GLASSBOX_ROOT, "emit.ps1")
GLASSBOX_STATUS_VALUES = {
    "queued", "running", "completed", "failed", "blocked", "skipped", "waiting", "info",
}

# Win32 reparse-point bit -- same constant build_generation_registry.py uses
# for OneDrive-placeholder detection; here it is used on the top-level
# generation directory itself to refuse symlinks/junctions (rule a).
FILE_ATTRIBUTE_REPARSE_POINT = 0x400

RAW_EXT = {".pdf", ".csv", ".html", ".htm"}
RAW_NAME_TOKENS = ("raw", "crawl", "download", "snapshot", "sod", "ledger_source")

# Rule (f), verbatim from the task brief.
DENYLIST_TOKENS = (
    "20260905_v5",
    "hill_personnel_spine_20260903_v6",
    "hill_personnel_spine_20260903_v5",
    "tiered_corroboration_sidecar_20260902",
    "exploratory_temporal_tier_20260902",
    "house_personnel_ledger_20260903_v5",
    "politico_profile_crawl",
    "name_standard",
    "generation_registry",
)

MAX_CORPUS_FILE_BYTES = 25 * 1024 * 1024
FRESHNESS_WINDOW_S = 48 * 3600
GLASSBOX_EVENT_WINDOW_S = 3 * 3600
# --execute re-checks only gates (a), (e) and (f). Gates (b) referenced-by
# and (c) fresh-registry are NOT re-run per directory, so a plan may only be
# acted on while those two answers are still fresh.
PLAN_MAX_AGE_S = 6 * 3600
DELETE_RETRY_ATTEMPTS = 3
DELETE_RETRY_SLEEP_S = 5


def log(msg):
    print("[{}] {}".format(time.strftime("%H:%M:%S"), msg), flush=True)


def iso(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def human_bytes(n):
    if n is None:
        return ""
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return "{:,.1f} {}".format(n, unit)
        n /= 1024.0
    return "{:,.1f} PB".format(n)


def get_disk_free_bytes(drive="C:\\"):
    free_bytes = ctypes.c_ulonglong(0)
    total_bytes = ctypes.c_ulonglong(0)
    ok = ctypes.windll.kernel32.GetDiskFreeSpaceExW(
        ctypes.c_wchar_p(drive),
        ctypes.pointer(free_bytes),
        ctypes.pointer(total_bytes),
        None,
    )
    if not ok:
        return None, None
    return free_bytes.value, total_bytes.value


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------------------
# Rule (a): direct-child / no-reparse-point check. Shared by --check and the
# --execute delete-time re-check.
# ---------------------------------------------------------------------------

def check_rule_a(name, on_disk_names):
    """Returns (path, None) if `name` is a real, exact-case, non-reparse-point
    direct child of Store 1 right now; otherwise (None, reason)."""
    if not name or name in (".", "..") or os.sep in name or (os.altsep and os.altsep in name):
        return None, "invalid name (path separator or traversal token)"
    if name not in on_disk_names:
        return None, "not an exact-case direct child of Store 1 right now (missing or case drift)"
    candidate_path = os.path.join(STORE1, name)
    if not os.path.isdir(candidate_path):
        return None, "exists in the Store 1 listing but is not a directory"
    try:
        st = os.lstat(candidate_path)
    except OSError as exc:
        return None, "lstat failed: {}".format(exc)
    attrs = getattr(st, "st_file_attributes", 0)
    if attrs & FILE_ATTRIBUTE_REPARSE_POINT:
        return None, "top-level entry is a symlink/junction/reparse point -- refused"
    parent = os.path.dirname(os.path.normpath(candidate_path))
    if os.path.normcase(parent) != os.path.normcase(os.path.normpath(STORE1)):
        return None, "resolved path's parent is not audits\\staffer_network"
    return candidate_path, None


def check_hard_denylist(name):
    for tok in DENYLIST_TOKENS:
        if tok in name:
            return tok
    return None


def is_raw_capture_name(name):
    lname = name.lower()
    return any(tok in lname for tok in RAW_NAME_TOKENS)


def scan_directory(path):
    """One walk of a candidate directory, independent of the registry, used
    for rules (d) and (e) plus the bytes/file_count the plan reports."""
    total_bytes = 0
    file_count = 0
    newest_mtime = 0.0
    has_raw_ext = False
    has_lock = False
    for dirpath, _dirnames, filenames in os.walk(path):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            try:
                st = os.stat(fp)
            except OSError:
                continue
            total_bytes += st.st_size
            file_count += 1
            if st.st_mtime > newest_mtime:
                newest_mtime = st.st_mtime
            ext = os.path.splitext(fn)[1].lower()
            if ext in RAW_EXT:
                has_raw_ext = True
            if fn.lower().endswith(".lock"):
                has_lock = True
    if newest_mtime == 0.0:
        try:
            newest_mtime = os.stat(path).st_mtime
        except OSError:
            pass
    return {
        "bytes": total_bytes,
        "file_count": file_count,
        "newest_mtime_epoch": newest_mtime,
        "newest_mtime_utc": iso(newest_mtime) if newest_mtime else None,
        "has_raw_ext": has_raw_ext,
        "has_lock": has_lock,
    }


# ---------------------------------------------------------------------------
# Rule (b): the broader referenced-by corpus (see module docstring for
# exactly why this differs from build_generation_registry.py's own scan).
# ---------------------------------------------------------------------------

#: Files gate (b) could not read at all. One unreadable file makes the
#: referenced-by answer unsound, so --check refuses to write a plan.
CORPUS_UNREADABLE = []

#: Oversized (> MAX_CORPUS_FILE_BYTES) text-like files: recorded by path,
#: not content, and streamed on demand in bounded chunks per query so their
#: decoded text is never held in memory (see find_referenced_by).
OVERSIZED_TEXT_FILES = []

#: Files never opened as text at all -- a known-binary extension, or (when
#: oversized) an extension not on the text-like allowlist. Visibility only:
#: unlike CORPUS_UNREADABLE, a deliberate skip does not block plan-writing.
SKIPPED_BINARY = []

#: Extensions the oversized-file path is willing to chunk-read as text.
TEXT_LIKE_EXT = {
    ".json", ".ndjson", ".md", ".txt", ".py", ".ps1", ".csv", ".yaml",
    ".yml", ".toml", ".cfg", ".ini", ".sql", ".html", ".js", ".cjs",
}

#: Extensions that must never be decoded as text: they cannot contain a
#: generation-name substring match, and errors="replace" would just spend
#: time/memory turning their bytes into meaningless text.
BINARY_EXT = {
    ".gz", ".zip", ".sqlite", ".db", ".bin", ".parquet", ".wav", ".pdf",
}


def _add_file_to_corpus(corpus, path, seen):
    key = os.path.normcase(os.path.normpath(path))
    if key in seen:
        return
    seen.add(key)
    rel = os.path.relpath(path, LIVE)
    ext = os.path.splitext(path)[1].lower()
    if ext in BINARY_EXT:
        SKIPPED_BINARY.append(rel)
        return
    try:
        size = os.path.getsize(path)
        if size <= MAX_CORPUS_FILE_BYTES:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                corpus.append((rel, f.read()))
            return
        if ext not in TEXT_LIKE_EXT:
            # Oversized and not a recognized text format -- do not guess;
            # skip rather than spend a chunked read on likely-binary data.
            SKIPPED_BINARY.append(rel)
            return
        # A multi-megabyte ledger, manifest or pointer file is exactly
        # where a generation name hides. Dropping it made gate (b) silently
        # blind, which is the one failure mode that ends with a referenced
        # directory deleted. Confirm now that the whole file is actually
        # readable -- one chunked pass, each chunk discarded immediately --
        # so an unreadable file still blocks plan-writing below exactly
        # like the ones read in full above. The real per-name search
        # happens on demand in find_referenced_by, so the decoded text is
        # never retained here either.
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            while f.read(MAX_CORPUS_FILE_BYTES):
                pass
        OVERSIZED_TEXT_FILES.append((rel, path))
    except OSError as exc:
        CORPUS_UNREADABLE.append("{}: {}".format(rel, exc))


def build_referenced_by_corpus():
    corpus = []
    seen = set()

    log("  [corpus] fec\\**\\*.py, *.tpl, *.json (recursive) ...")
    for dirpath, _dirnames, filenames in os.walk(FEC_DIR):
        for fn in filenames:
            if fn.lower().endswith((".py", ".tpl", ".json")):
                _add_file_to_corpus(corpus, os.path.join(dirpath, fn), seen)

    log("  [corpus] data\\engine\\*.json (top level) ...")
    engine_dir = os.path.join(LIVE, "data", "engine")
    if os.path.isdir(engine_dir):
        for fn in os.listdir(engine_dir):
            fp = os.path.join(engine_dir, fn)
            if fn.lower().endswith(".json") and os.path.isfile(fp):
                _add_file_to_corpus(corpus, fp, seen)

    log("  [corpus] audits\\staffer_network\\*.py (top level, self excluded) ...")
    if os.path.isdir(STORE1):
        for fn in os.listdir(STORE1):
            fp = os.path.join(STORE1, fn)
            if fn.lower().endswith(".py") and os.path.isfile(fp) and fn != SCRIPT_NAME:
                _add_file_to_corpus(corpus, fp, seen)

    log("  [corpus] data\\staffer_network\\**\\* (recursive, ALL files) ...")
    for dirpath, _dirnames, filenames in os.walk(STORE2):
        for fn in filenames:
            _add_file_to_corpus(corpus, os.path.join(dirpath, fn), seen)

    log("  [corpus] audits\\*.md (top level) ...")
    audits_dir = os.path.join(LIVE, "audits")
    if os.path.isdir(audits_dir):
        for fn in os.listdir(audits_dir):
            fp = os.path.join(audits_dir, fn)
            if fn.lower().endswith(".md") and os.path.isfile(fp):
                _add_file_to_corpus(corpus, fp, seen)

    log("  [corpus] *_current.json anywhere under data\\ or audits\\ ...")
    data_dir = os.path.join(LIVE, "data")
    for root in (data_dir, audits_dir):
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # data\staffer_network was already walked in full just above
            # (every file, not only *_current.json) -- prune it here so it
            # is not traversed twice. audits\staffer_network was only
            # listdir'd at the top level above (its subdirectories were
            # never read), so it is deliberately left un-pruned and gets a
            # full recursive pass in this loop.
            if os.path.normcase(os.path.normpath(dirpath)) == os.path.normcase(os.path.normpath(data_dir)):
                dirnames[:] = [
                    d for d in dirnames
                    if os.path.normcase(os.path.join(dirpath, d)) != os.path.normcase(STORE2)
                ]
            for fn in filenames:
                if fn.lower().endswith("_current.json"):
                    _add_file_to_corpus(corpus, os.path.join(dirpath, fn), seen)

    return corpus


def _name_in_oversized_file(name, path):
    """Stream path in MAX_CORPUS_FILE_BYTES chunks, 4096-byte overlap so a
    name split across a chunk boundary is still found. Each chunk is
    discarded (the window and tail go out of scope) as soon as it has been
    checked -- the file's decoded text is never retained as a whole."""
    tail = ""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        while True:
            block = f.read(MAX_CORPUS_FILE_BYTES)
            if not block:
                return False
            window = tail + block
            if name in window:
                return True
            tail = block[-4096:]


def find_referenced_by(name, corpus, limit=10):
    hits = []
    for relpath, content in corpus:
        if name in content:
            hits.append(relpath)
            if len(hits) >= limit:
                return hits
    for relpath, path in OVERSIZED_TEXT_FILES:
        if len(hits) >= limit:
            break
        if _name_in_oversized_file(name, path):
            hits.append(relpath)
    return hits


# ---------------------------------------------------------------------------
# Rule (c): re-run build_generation_registry.py so its ACTIVE/INACTIVE
# classes reflect disk right now, then load what it wrote.
# ---------------------------------------------------------------------------

def run_build_generation_registry():
    if not os.path.isfile(BUILD_SCRIPT_PATH):
        raise RuntimeError("build_generation_registry.py not found at {}".format(BUILD_SCRIPT_PATH))
    log("Re-running build_generation_registry.py so classes reflect disk now "
        "(this rewrites its own .json/.md/_inactive.txt -- expected) ...")
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, BUILD_SCRIPT_PATH],
        cwd=STORE1,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1800,
    )
    elapsed = time.time() - t0
    log("  build_generation_registry.py exited {} in {:.1f}s".format(proc.returncode, elapsed))
    if proc.stdout:
        tail_out = "\n".join(proc.stdout.splitlines()[-15:])
        log("  --- stdout tail ---\n" + tail_out)
    if proc.returncode != 0:
        if proc.stderr:
            log("  --- stderr tail ---\n" + "\n".join(proc.stderr.splitlines()[-15:]))
        raise RuntimeError(
            "build_generation_registry.py failed with exit code {}; refusing to "
            "act on a stale/partial registry.".format(proc.returncode)
        )
    return {"returncode": proc.returncode, "elapsed_s": elapsed}


def load_registry_json():
    with open(OUT_JSON, "r", encoding="utf-8", errors="replace") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Rule (e): glassbox "running" events from the last 3 hours.
# ---------------------------------------------------------------------------

def parse_iso_utc(s):
    """Robust ISO-8601 parser for glassbox timestamp_utc values, which can
    carry more than 6 fractional-second digits (e.g. ...7279320Z) --
    truncated/padded to microseconds here rather than relying on a given
    Python version's exact fromisoformat leniency."""
    if not s:
        return None
    text = str(s).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if "." in text:
        head, rest = text.split(".", 1)
        m = re.match(r"(\d+)(.*)", rest)
        if m:
            frac, tail = m.group(1), m.group(2)
            frac = (frac + "000000")[:6]
            text = head + "." + frac + tail
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_recent_running_events(now_utc, window_s=GLASSBOX_EVENT_WINDOW_S):
    """Every *.json file directly under glassbox\\events\\ (non-recursive)
    with status "running" and a timestamp_utc within window_s of now. File
    mtime is only a cheap pre-filter (with slack) before opening a file --
    the real cutoff uses the event's own timestamp_utc field."""
    events = []
    if not os.path.isdir(GLASSBOX_EVENTS_DIR):
        return events
    mtime_floor = time.time() - window_s - 900  # 15 min slack on the cheap pre-filter
    for fn in os.listdir(GLASSBOX_EVENTS_DIR):
        if not fn.lower().endswith(".json"):
            continue
        fp = os.path.join(GLASSBOX_EVENTS_DIR, fn)
        try:
            if not os.path.isfile(fp) or os.stat(fp).st_mtime < mtime_floor:
                continue
        except OSError:
            continue
        try:
            with open(fp, "r", encoding="utf-8-sig", errors="replace") as f:
                raw_text = f.read()
            data = json.loads(raw_text)
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict) or "status" not in data or "timestamp_utc" not in data:
            continue
        if str(data.get("status", "")).lower() != "running":
            continue
        ts = parse_iso_utc(data.get("timestamp_utc"))
        if ts is None or abs((now_utc - ts).total_seconds()) > window_s:
            continue
        events.append({
            "id": data.get("id", fn),
            "timestamp_utc": data.get("timestamp_utc"),
            "raw_text": raw_text,
            "path": fp,
        })
    return events


def event_matches_name(events, name):
    for ev in events:
        if name in ev["raw_text"]:
            return ev["id"]
    return None


# ---------------------------------------------------------------------------
# Inactive-list parsing (format written by build_generation_registry.py:
# "# <n> inactive directories, ... Format: <bytes>\t<absolute path>")
# ---------------------------------------------------------------------------

def read_inactive_list(path):
    candidates = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for lineno, raw_line in enumerate(f, 1):
            line = raw_line.rstrip("\r\n")
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2:
                log("WARNING: skipping malformed inactive-list line {}: {!r}".format(lineno, line))
                continue
            bytes_str, abs_path = parts
            try:
                original_bytes = int(bytes_str)
            except ValueError:
                log("WARNING: skipping inactive-list line {} with non-integer byte count: {!r}".format(
                    lineno, line))
                continue
            candidates.append({
                "name": os.path.basename(abs_path),
                "listed_path": abs_path,
                "original_bytes": original_bytes,
            })
    return candidates


# ---------------------------------------------------------------------------
# Per-candidate verdict (gates a-f combined).
# ---------------------------------------------------------------------------

def evaluate_candidate(cand, on_disk_names, corpus, fresh_by_name, recent_events):
    name = cand["name"]
    result = {
        "name": name,
        "path": os.path.join(STORE1, name),
        "original_bytes": cand["original_bytes"],
        "bytes": None,
        "file_count": None,
        "newest_mtime_utc": None,
        "verdict": "KEEP",
        "reasons": [],
    }

    path, reason_a = check_rule_a(name, on_disk_names)
    if reason_a is not None:
        result["reasons"].append("rule_a_failed: {}".format(reason_a))
        return result  # nothing else can be safely checked without a valid path

    tok = check_hard_denylist(name)
    if tok:
        result["reasons"].append("rule_f_hard_denylist: contains '{}'".format(tok))

    stats = scan_directory(path)
    result["bytes"] = stats["bytes"]
    result["file_count"] = stats["file_count"]
    result["newest_mtime_utc"] = stats["newest_mtime_utc"]

    hits = find_referenced_by(name, corpus)
    if hits:
        shown = hits[:5]
        more = "" if len(hits) <= 5 else " (+{} more, truncated)".format(len(hits) - 5)
        result["reasons"].append("rule_b_referenced_by: " + ", ".join(shown) + more)

    fresh = fresh_by_name.get(name)
    if fresh is None:
        result["reasons"].append("rule_c_fresh_registry: directory absent from the freshly-rebuilt registry")
    elif fresh.get("class") != "INACTIVE":
        result["reasons"].append("rule_c_fresh_class_active: rebuilt registry now classes this ACTIVE ({})".format(
            ",".join(fresh.get("active_reasons") or []) or "?"))

    if is_raw_capture_name(name):
        result["reasons"].append("rule_d_raw_capture: name contains a raw-capture token")
    if stats["has_raw_ext"]:
        result["reasons"].append("rule_d_raw_capture: holds a .pdf/.csv/.html/.htm file")

    if stats["newest_mtime_epoch"] and (time.time() - stats["newest_mtime_epoch"]) < FRESHNESS_WINDOW_S:
        result["reasons"].append("rule_e_recent_mtime_48h: newest file mtime {}".format(stats["newest_mtime_utc"]))
    if stats["has_lock"]:
        result["reasons"].append("rule_e_lock_file_present")
    ev_id = event_matches_name(recent_events, name)
    if ev_id:
        result["reasons"].append("rule_e_glassbox_running_event: {} (last 3h, status=running)".format(ev_id))

    if result["reasons"]:
        result["verdict"] = "KEEP"
    else:
        result["verdict"] = "DELETE"
        result["reasons"] = [
            "eligible: verified direct child; not referenced; fresh class INACTIVE; "
            "not a raw capture; not recently modified/locked/in-flight; not denylisted"
        ]
    return result


# ---------------------------------------------------------------------------
# --check
# ---------------------------------------------------------------------------

def cmd_check():
    t0 = time.time()
    log("=" * 78)
    log("delete_inactive_generations.py --check starting")
    log("=" * 78)

    if not os.path.isdir(STORE1):
        log("ERROR: Store 1 not found at {}".format(STORE1))
        return 1
    if not os.path.isfile(OUT_INACTIVE):
        log("ERROR: no existing inactive list at {} -- run build_generation_registry.py "
            "first.".format(OUT_INACTIVE))
        return 1

    disk_free_start, _ = get_disk_free_bytes("C:\\")

    log("Snapshotting the current inactive list before build_generation_registry.py "
        "overwrites it ...")
    candidates = read_inactive_list(OUT_INACTIVE)
    log("  {} candidate director{} read from {}".format(
        len(candidates), "y" if len(candidates) == 1 else "ies", OUT_INACTIVE))
    if len(candidates) != 94:
        log("  NOTE: the task brief describes 94 candidates; found {} on disk right now "
            "-- the input file has changed since that snapshot. Proceeding with what is "
            "on disk now.".format(len(candidates)))
    candidate_names = set(c["name"] for c in candidates)

    build_info = run_build_generation_registry()
    registry_doc = load_registry_json()
    fresh_by_name = {g["name"]: g for g in registry_doc["store1"]["generations"]}

    log("Building the broader referenced-by corpus for this delete-safety gate ...")
    tcorpus0 = time.time()
    corpus = build_referenced_by_corpus()
    log("  corpus: {} files, {:,} characters, {:.1f}s".format(
        len(corpus), sum(len(c) for _, c in corpus), time.time() - tcorpus0))
    if OVERSIZED_TEXT_FILES:
        log("  corpus: {} oversized text file(s) confirmed readable; searched "
            "on demand, chunked, per candidate".format(len(OVERSIZED_TEXT_FILES)))
    if SKIPPED_BINARY:
        log("  corpus: {} file(s) skipped without decoding (binary, or an "
            "oversized file with an unrecognized extension)".format(len(SKIPPED_BINARY)))
    if CORPUS_UNREADABLE:
        log("ERROR: {} referenced-by corpus file(s) could not be read; gate (b) "
            "would be blind to any reference inside them. Refusing to write a "
            "delete plan.".format(len(CORPUS_UNREADABLE)))
        for item in CORPUS_UNREADABLE[:10]:
            log("  UNREADABLE {}".format(item))
        return 1

    now_utc = datetime.now(timezone.utc)
    log("Loading glassbox events from the last {}h with status=running ...".format(
        GLASSBOX_EVENT_WINDOW_S // 3600))
    recent_events = load_recent_running_events(now_utc)
    log("  {} running event(s) in window".format(len(recent_events)))

    try:
        on_disk_names = set(os.listdir(STORE1))
    except OSError as exc:
        log("ERROR: could not list Store 1: {}".format(exc))
        return 1

    log("Evaluating {} candidates against gates (a)-(f) ...".format(len(candidates)))
    entries = [
        evaluate_candidate(c, on_disk_names, corpus, fresh_by_name, recent_events)
        for c in candidates
    ]

    keep_entries = [e for e in entries if e["verdict"] == "KEEP"]
    delete_entries = [e for e in entries if e["verdict"] == "DELETE"]
    delete_entries.sort(key=lambda e: -(e["bytes"] or 0))

    planned_bytes = sum(e["bytes"] or 0 for e in delete_entries)
    keep_bytes = sum(e["bytes"] or 0 for e in keep_entries)

    # Safety invariants: never plan to delete more than was on the reviewed
    # candidate list, and never plan a name that was not on it.
    assert len(delete_entries) <= len(candidates), \
        "invariant violated: planned DELETE count exceeds the inactive-list size"
    assert all(e["name"] in candidate_names for e in delete_entries), \
        "invariant violated: a planned DELETE name is not in the original inactive list"

    try:
        store1_dir_count_now = sum(
            1 for n in os.listdir(STORE1) if os.path.isdir(os.path.join(STORE1, n))
        )
    except OSError:
        store1_dir_count_now = None
    disk_free_now, _disk_total = get_disk_free_bytes("C:\\")

    plan_doc = {
        "generated_at_utc": iso(time.time()),
        "tool": SCRIPT_NAME,
        "mode": "check",
        "source_inactive_list_path": OUT_INACTIVE,
        "source_inactive_list_count": len(candidates),
        "fresh_registry_rebuild": {
            "returncode": build_info["returncode"],
            "elapsed_s": round(build_info["elapsed_s"], 1),
            "registry_json_path": OUT_JSON,
            "registry_generated_at_utc": registry_doc.get("generated_at_utc"),
        },
        "gates_applied": [
            "a: direct child of Store 1, exact case, no symlink/junction/reparse point",
            "b: not referenced by fec/**.py|.tpl|.json, data/engine/*.json, "
            "audits/staffer_network/*.py, data/staffer_network/**/*, audits/*.md, "
            "or any */*_current.json under data/ or audits/",
            "c: fresh (just rebuilt) registry class is still INACTIVE",
            "d: not a raw capture (name token, or holds .pdf/.csv/.html/.htm)",
            "e: newest mtime 48h+ old, no *.lock inside, no glassbox running event "
            "in the last 3h mentioning the name",
            "f: not on the hard denylist",
        ],
        "denylist_tokens": list(DENYLIST_TOKENS),
        "entries": entries,
        "totals": {
            "planned_delete_dirs": len(delete_entries),
            "planned_delete_bytes": planned_bytes,
            "keep_dirs": len(keep_entries),
            "keep_bytes": keep_bytes,
        },
        "store1_directory_count_now": store1_dir_count_now,
        "disk_free_bytes_c_at_check_time": disk_free_now,
        "disk_free_bytes_c_at_check_start": disk_free_start,
        "note": (
            "sha256 of this exact file (raw bytes, as written) is printed by --check "
            "and is required, verbatim, as --execute's --plan-sha argument. Do not "
            "hand-edit this file -- editing it changes its hash and --execute will "
            "refuse it."
        ),
    }

    # Binary write, not text mode: avoids Windows '\n' -> '\r\n' translation,
    # so the bytes hashed below are byte-for-byte identical to what --execute
    # will later re-read and re-hash from disk.
    plan_bytes = json.dumps(plan_doc, indent=2, ensure_ascii=False, sort_keys=False).encode("utf-8")
    with open(OUT_PLAN, "wb") as f:
        f.write(plan_bytes)
    plan_sha = sha256_bytes(plan_bytes)

    elapsed_total = time.time() - t0

    log("=" * 78)
    log("CHECK COMPLETE in {:.1f}s".format(elapsed_total))
    log("=" * 78)
    log("KEEP ({} directories):".format(len(keep_entries)))
    for e in keep_entries:
        log("  KEEP    {}  [{}]".format(e["name"], "; ".join(e["reasons"])))
    log("-" * 78)
    log("DELETE planned ({} directories, {} bytes / {}):".format(
        len(delete_entries), planned_bytes, human_bytes(planned_bytes)))
    for e in delete_entries:
        log("  DELETE  {}  ({})".format(e["name"], human_bytes(e["bytes"] or 0)))
    log("-" * 78)
    log("Plan written to        : {}".format(OUT_PLAN))
    log("Plan sha256            : {}".format(plan_sha))
    log("Store1 directory count : {}".format(store1_dir_count_now))
    log("Free bytes on C:       : {} ({})".format(disk_free_now, human_bytes(disk_free_now)))
    log("")
    log("Exact --execute command line (Paul only -- never run automatically):")
    log('  python "{}" --execute --plan-sha {}'.format(SCRIPT_ABS_PATH, plan_sha))
    log("=" * 78)
    return 0


# ---------------------------------------------------------------------------
# --execute (written for completeness per spec; never invoked automatically)
# ---------------------------------------------------------------------------

def _clear_readonly_and_retry(func, path, exc):
    try:
        os.chmod(path, stat.S_IWRITE)
    except OSError:
        pass
    try:
        func(path)
    except OSError:
        pass


def _rmtree_compat(path):
    """shutil.rmtree's onerror callback was deprecated in favor of onexc in
    Python 3.12 (this host runs 3.12.10); use whichever this interpreter
    supports so no DeprecationWarning is emitted."""
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_clear_readonly_and_retry)
    else:
        def _onerror(func, p, exc_info):
            _clear_readonly_and_retry(func, p, exc_info)
        shutil.rmtree(path, onerror=_onerror)


def delete_with_retries(path, attempts=DELETE_RETRY_ATTEMPTS, sleep_s=DELETE_RETRY_SLEEP_S):
    """Never forced: after `attempts` tries the directory is left exactly as
    it is and the caller records FAILED."""
    last_exc = None
    for attempt in range(1, attempts + 1):
        try:
            _rmtree_compat(path)
        except Exception as exc:  # deliberately broad: recorded, never raised
            last_exc = exc
        if not os.path.exists(path):
            return True, None
        if attempt < attempts:
            log("    retry {}/{} for {} in {}s (still present; likely a transient "
                "OneDrive/AV lock) ...".format(attempt, attempts, path, sleep_s))
            time.sleep(sleep_s)
    reason = "still present after {} rmtree attempts".format(attempts)
    if last_exc is not None:
        reason += ": {}".format(last_exc)
    return False, reason


def emit_glassbox_event(status, summary, detail="", stage="", metadata=None, run_id=None):
    """Invokes emit.ps1 with named CLI parameters -- the Python-side
    equivalent of the hashtable splatting other callers in this repo use
    (each -Name value pair here is exactly what a splatted hashtable would
    produce)."""
    if status not in GLASSBOX_STATUS_VALUES:
        raise ValueError("invalid glassbox status: {}".format(status))
    if not os.path.isfile(GLASSBOX_EMIT_PS1):
        log("WARNING: {} not found; skipping glassbox event ({}: {})".format(
            GLASSBOX_EMIT_PS1, status, summary))
        return
    args = [
        "powershell.exe", "-NoProfile", "-NonInteractive", "-File", GLASSBOX_EMIT_PS1,
        "-Lane", "claude",
        "-Kind", "staffer_network_delete_inactive_generations",
        "-Status", status,
        "-Summary", summary,
        "-Source", SCRIPT_NAME,
        "-Cwd", STORE1,
        "-Quiet",
    ]
    if detail:
        args += ["-Detail", detail]
    if stage:
        args += ["-Stage", stage]
    if run_id:
        args += ["-RunId", run_id]
    if metadata:
        args += ["-MetadataJson", json.dumps(metadata, ensure_ascii=False)]
    try:
        subprocess.run(args, check=False, capture_output=True, text=True, timeout=60)
    except OSError as exc:
        log("WARNING: failed to invoke glassbox emit.ps1: {}".format(exc))


def recheck_at_delete_time(name, on_disk_names):
    """Re-checks ONLY (a), (e) and (f) immediately before deleting, per spec
    -- (b)/(c)/(d) already got a full corpus/registry rebuild in --check and
    are not cheap enough to redo per-directory here."""
    path, reason_a = check_rule_a(name, on_disk_names)
    if reason_a is not None:
        return False, "rule (a) failed at delete time: {}".format(reason_a)
    tok = check_hard_denylist(name)
    if tok:
        return False, "rule (f) hard denylist at delete time: contains '{}'".format(tok)
    stats = scan_directory(path)
    if stats["newest_mtime_epoch"] and (time.time() - stats["newest_mtime_epoch"]) < FRESHNESS_WINDOW_S:
        return False, "rule (e) recent mtime at delete time: {}".format(stats["newest_mtime_utc"])
    if stats["has_lock"]:
        return False, "rule (e) lock file present at delete time"
    return True, None


def cmd_execute(plan_sha_arg):
    """DESTRUCTIVE. Must only be run by Paul, directly, after reading the
    --check KEEP list and the plan file. Never invoked by an assistant."""
    if not os.path.isfile(OUT_PLAN):
        log("ERROR: no plan file at {} -- run --check first.".format(OUT_PLAN))
        return 1

    with open(OUT_PLAN, "rb") as f:
        plan_bytes = f.read()
    actual_sha = sha256_bytes(plan_bytes)
    if actual_sha.lower() != (plan_sha_arg or "").strip().lower():
        emit_glassbox_event(
            "blocked",
            "delete_inactive_generations --execute refused: --plan-sha mismatch",
            detail="expected {} got {}".format(actual_sha, plan_sha_arg),
            stage="preflight",
        )
        log("ERROR: --plan-sha does not match the plan file's current sha256.")
        log("  plan file sha256 : {}".format(actual_sha))
        log("  --plan-sha given : {}".format(plan_sha_arg))
        log("  Refusing to run. Re-run --check if the plan is meant to have changed, "
            "or pass the sha256 that --check actually printed.")
        return 1

    plan_doc = json.loads(plan_bytes.decode("utf-8"))
    plan_generated = parse_iso_utc(plan_doc.get("generated_at_utc"))
    plan_age_s = None if plan_generated is None else (
        datetime.now(timezone.utc) - plan_generated
    ).total_seconds()
    if plan_age_s is None or plan_age_s > PLAN_MAX_AGE_S or plan_age_s < -900:
        emit_glassbox_event(
            "blocked",
            "delete_inactive_generations --execute refused: stale or undated plan",
            detail="generated_at_utc {!r}, age {} s, limit {} s".format(
                plan_doc.get("generated_at_utc"), plan_age_s, PLAN_MAX_AGE_S),
            stage="preflight",
        )
        log("ERROR: the plan is stale or undated. --execute re-checks only gates "
            "(a), (e) and (f); a directory that became referenced (gate b) or "
            "ACTIVE (gate c) since the plan was written would be deleted anyway.")
        log("  plan generated_at_utc : {}".format(plan_doc.get("generated_at_utc")))
        log("  maximum plan age      : {}h".format(PLAN_MAX_AGE_S // 3600))
        log("  Re-run --check and pass the sha256 it prints.")
        return 1
    run_id = "delete-exec-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    started_utc = iso(time.time())
    disk_free_before, _ = get_disk_free_bytes("C:\\")

    emit_glassbox_event(
        "running",
        "delete_inactive_generations --execute starting ({} planned DELETE dirs)".format(
            plan_doc["totals"]["planned_delete_dirs"]),
        stage="start",
        run_id=run_id,
        metadata={
            "planned_delete_dirs": plan_doc["totals"]["planned_delete_dirs"],
            "planned_delete_bytes": plan_doc["totals"]["planned_delete_bytes"],
        },
    )

    try:
        os.listdir(STORE1)  # fail fast if Store 1 is not listable at all
    except OSError as exc:
        log("ERROR: could not list Store 1: {}".format(exc))
        emit_glassbox_event("failed", "delete_inactive_generations --execute aborted: cannot list Store 1",
                             detail=str(exc), run_id=run_id)
        return 1

    delete_candidates = [e for e in plan_doc["entries"] if e["verdict"] == "DELETE"]
    delete_candidates.sort(key=lambda e: -(e["bytes"] or 0))
    kept_from_plan = [e for e in plan_doc["entries"] if e["verdict"] != "DELETE"]

    receipt_entries = [
        {
            "name": e["name"], "path": e["path"], "bytes": e["bytes"],
            "final_status": "KEPT", "reason": "was KEEP in the plan: " + "; ".join(e["reasons"]),
        }
        for e in kept_from_plan
    ]

    deleted_bytes = 0
    deleted_count = 0
    failed_count = 0
    for e in delete_candidates:
        name, path = e["name"], e["path"]
        try:
            on_disk_names_now = set(os.listdir(STORE1))
        except OSError as exc:
            log("SKIP (cannot list Store 1 right now): {} -- {}".format(name, exc))
            receipt_entries.append({
                "name": name, "path": path, "bytes": e["bytes"],
                "final_status": "KEPT", "reason": "could not list Store 1 at delete time: {}".format(exc),
            })
            continue
        ok, reason = recheck_at_delete_time(name, on_disk_names_now)
        if not ok:
            log("SKIP (re-check failed): {} -- {}".format(name, reason))
            receipt_entries.append({
                "name": name, "path": path, "bytes": e["bytes"],
                "final_status": "KEPT", "reason": "delete-time re-check failed: " + reason,
            })
            continue
        log("DELETING {} ({}) ...".format(name, human_bytes(e["bytes"] or 0)))
        ok, fail_reason = delete_with_retries(path)
        if ok:
            deleted_count += 1
            deleted_bytes += e["bytes"] or 0
            receipt_entries.append({
                "name": name, "path": path, "bytes": e["bytes"],
                "final_status": "DELETED", "reason": None,
            })
        else:
            failed_count += 1
            log("FAILED to delete {}: {}".format(name, fail_reason))
            receipt_entries.append({
                "name": name, "path": path, "bytes": e["bytes"],
                "final_status": "FAILED", "reason": fail_reason,
            })

    disk_free_after, _ = get_disk_free_bytes("C:\\")
    finished_utc = iso(time.time())

    receipt_doc = {
        "generated_at_utc": finished_utc,
        "tool": SCRIPT_NAME,
        "mode": "execute",
        "plan_path": OUT_PLAN,
        "plan_sha256_used": actual_sha,
        "started_utc": started_utc,
        "finished_utc": finished_utc,
        "entries": receipt_entries,
        "totals": {
            "deleted_dirs": deleted_count,
            "deleted_bytes": deleted_bytes,
            "failed_dirs": failed_count,
            "kept_dirs": sum(1 for r in receipt_entries if r["final_status"] == "KEPT"),
        },
        "disk_free_bytes_c_before": disk_free_before,
        "disk_free_bytes_c_after": disk_free_after,
    }
    receipt_bytes = json.dumps(receipt_doc, indent=2, ensure_ascii=False).encode("utf-8")
    with open(OUT_RECEIPT, "wb") as f:
        f.write(receipt_bytes)

    final_status = "failed" if failed_count else "completed"
    emit_glassbox_event(
        final_status,
        "delete_inactive_generations --execute {}: {} deleted, {} failed, {} kept".format(
            final_status, deleted_count, failed_count, receipt_doc["totals"]["kept_dirs"]),
        stage="end",
        run_id=run_id,
        metadata=receipt_doc["totals"],
    )

    log("Re-running build_generation_registry.py to refresh the registry post-delete ...")
    try:
        run_build_generation_registry()
    except RuntimeError as exc:
        log("WARNING: post-delete registry rebuild failed: {}".format(exc))

    log("Receipt written to: {}".format(OUT_RECEIPT))
    log("Deleted {} dirs / {} ; Failed {} ; Kept {}".format(
        deleted_count, human_bytes(deleted_bytes), failed_count, receipt_doc["totals"]["kept_dirs"]))
    return 1 if failed_count else 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_arg_parser():
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        description=(
            "Safety-gate companion to build_generation_registry.py. --check "
            "independently re-verifies every directory on the current "
            "generation_registry_20260906_inactive.txt list against six gates "
            "(a-f, see module docstring) and writes a delete plan; it deletes "
            "nothing. --execute deletes only the plan's DELETE-verdict "
            "directories and must only be run by Paul, directly, after "
            "reviewing the plan and the KEEP list --check printed."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true",
                       help="Read-only re-verification. Writes the delete plan. Safe to run any time.")
    mode.add_argument("--execute", action="store_true",
                       help="Deletes the plan's DELETE-verdict directories. DESTRUCTIVE. Requires --plan-sha.")
    parser.add_argument("--plan-sha", dest="plan_sha", default=None,
                         help="sha256 hex digest printed by a prior --check run. Required by --execute.")
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.execute and not args.plan_sha:
        parser.error("--execute requires --plan-sha <sha256-hex-printed-by-a-prior---check-run>")
    if args.check:
        return cmd_check()
    return cmd_execute(args.plan_sha)


if __name__ == "__main__":
    sys.exit(main())
