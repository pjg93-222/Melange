# -*- coding: utf-8 -*-
"""
build_generation_registry.py
=============================

READ-ONLY inventory tool for the Melange staffer-network stores. Produces a
generation registry so Paul can see what is active and what can go. This
script never deletes, moves, renames, or compresses anything -- it only
walks directories, os.stat()s files, reads small JSON/text files, and writes
three small output files back into Store 1.

Outputs (written next to this script, in audits/staffer_network/):
  - generation_registry_20260906.json           full structured registry
  - generation_registry_20260906.md             compact human-readable report
  - generation_registry_20260906_inactive.txt   delete-candidate list (path + bytes)

-----------------------------------------------------------------------------
CLASS RULE (verbatim, also restated in the .md report)
-----------------------------------------------------------------------------
A generation directory is ACTIVE if ANY of the following hold:
  1. referenced_by is non-empty (its name appears verbatim, case-sensitive,
     in the content of a file under one of the CODE PATHS below).
  2. It is the newest (stamp, version) of its family. All roles that share
     that newest (stamp, version) tuple count as active together.
  3. It (or its family/role) is a raw capture: its name contains one of
     raw, crawl, download, snapshot, sod, ledger_source -- or it holds
     .pdf/.csv/.html source files anywhere under it. Raw inputs are never
     delete candidates.
  4. Its newest mtime is within the last 48 hours (it may be in flight).
Otherwise it is INACTIVE.

CODE PATHS (content is loaded once and grepped, case-sensitive substring,
for every generation directory's exact name; up to 10 hits are kept):
  - LIVE\\fec\\**\\*.py
  - LIVE\\fec\\**\\*.tpl
  - LIVE\\data\\engine\\*.json          (top-level only)
  - LIVE\\audits\\staffer_network\\*.py (top-level only, this script excluded)
  - LIVE\\data\\staffer_network\\**\\*.json
  - LIVE\\audits\\*.md                  (top-level only)

-----------------------------------------------------------------------------
NAME PARSING ALGORITHM (family / stamp / version / role)
-----------------------------------------------------------------------------
1. stamp = the first regex match of \\d{8}T\\d{6}Z (ISO) else \\d{8} (plain
   8-digit date) found anywhere in the name. Everything before it is
   `before`, everything after is `after` (each underscore-trimmed).
2. `after` is split on "_" into tokens. The first token matching ^v\\d+$
   (case-insensitive) is taken as `version`; every token matching that
   pattern is removed from the token list (a second trailing vN, seen on a
   few re-verified directories, is dropped from grouping but does not
   overwrite the recorded version).
3. Of the remaining tokens, if the LAST one case-insensitively equals
   primary, twin, verification, or raw, that is `role` and it is removed
   from the list. Otherwise role = "other" and nothing further is removed.
4. `family` = `before` plus whatever tokens are left, rejoined with "_".
   Falls back to the full original name if this would be empty.

KNOWN LIMITATIONS (see also the Notes section of the .md):
  - Only "vN" is recognized as a version marker. Alternate iteration
    vocabularies seen in this store (generationN, checkpointN, r2/r3,
    prev1, a second trailing _v2, _failed_*, _rebuild) are NOT recognized
    as versions and stay embedded in the family string. A directory whose
    family string is thereby made unique becomes trivially "the newest of
    its own (singleton) family" and defaults to ACTIVE. This is a
    deliberate conservative bias -- never silently suggest deleting
    something the parser cannot confidently place in a lineage -- but it
    means some SUPERSEDED/FAILED/DEFECT-labeled directories still show as
    ACTIVE here. They are called out separately in a "flagged for manual
    review" table despite their ACTIVE classification; that flagging is
    informational only and does not change class.
  - A naming-convention change within one semantic family (e.g. a
    "..._generation_<ISO>" convention alongside an older "..._<date>_vN"
    convention for what is arguably the same underlying data) produces two
    distinct family buckets rather than one merged lineage.
  - Directories with no date stamp at all (schema/reference dirs, scratch
    dirs, __pycache__) become singleton families and default to ACTIVE via
    the same trivial-newest-of-family path. Nothing is ever auto-deleted by
    this script regardless -- these are reported for Paul's own review.

Run: python build_generation_registry.py
"""

import ctypes
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SCRIPT_NAME = os.path.basename(__file__)

LIVE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
STORE1 = os.path.join(LIVE, "audits", "staffer_network")
STORE2 = os.path.join(LIVE, "data", "staffer_network")
STORE3 = r"C:\Users\pgoff\AppData\Local\Melange\staffer_network"
FEC_DIR = os.path.join(LIVE, "fec")

OUT_JSON = os.path.join(STORE1, "generation_registry_20260906.json")
OUT_MD = os.path.join(STORE1, "generation_registry_20260906.md")
OUT_INACTIVE = os.path.join(STORE1, "generation_registry_20260906_inactive.txt")

# ---------------------------------------------------------------------------
# Win32 file-attribute bits used to detect OneDrive cloud-only placeholders.
# ---------------------------------------------------------------------------
FILE_ATTRIBUTE_REPARSE_POINT = 0x400
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x40000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x400000
PLACEHOLDER_MASK = (
    FILE_ATTRIBUTE_REPARSE_POINT
    | FILE_ATTRIBUTE_OFFLINE
    | FILE_ATTRIBUTE_RECALL_ON_OPEN
    | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
)

STAMP_RE = re.compile(r"(\d{8}T\d{6}Z|\d{8})")
VERSION_TOKEN_RE = re.compile(r"^v\d+$", re.IGNORECASE)
ROLE_KEYWORDS = {"primary", "twin", "verification", "raw"}
RECEIPT_RE = re.compile(r"^(receipt.*\.json|.*_receipt\.json)$", re.IGNORECASE)
RAW_EXT = {".pdf", ".csv", ".html", ".htm"}
RAW_NAME_TOKENS = ("raw", "crawl", "download", "snapshot", "sod", "ledger_source")
RECEIPT_FIELDS = ("status", "verdict", "promotion_policy", "review_status")
SUSPECT_TOKENS = ("superseded", "failed", "defect", "unusable", "defunct", "deprecated", "broken")

STORE3_LITERAL_PATTERNS = [
    "Melange\\staffer_network",
    "Local\\Melange",
    "MELANGE_STAFFER",
    "staffer_network_store",
]
CONST_NAMES = [
    "STAFFER_NETWORK_LOCAL",
    "STAFFER_NETWORK_RAW",
    "STAFFER_NETWORK_NORMALIZED",
    "STAFFER_NETWORK_CORPUS",
    "STAFFER_NETWORK_LEDGER",
    "STAFFER_NETWORK_ADJUDICATION",
    "DATA_STAFFER_NETWORK",
]


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


def stamp_sort_key(stamp):
    if not stamp:
        return "00000000T000000Z"
    if "T" in stamp:
        return stamp
    return stamp + "T000000Z"


def version_num(version):
    if not version:
        return 0
    m = re.match(r"v(\d+)", version, re.IGNORECASE)
    return int(m.group(1)) if m else 0


def parse_generation_name(name):
    m = STAMP_RE.search(name)
    if m:
        stamp = m.group(1)
        before = name[: m.start()].rstrip("_")
        after = name[m.end():].lstrip("_")
    else:
        stamp = ""
        before = name
        after = ""

    tokens = [t for t in after.split("_") if t] if after else []
    version = ""
    remaining = []
    for t in tokens:
        if VERSION_TOKEN_RE.match(t):
            if not version:
                version = t.lower()
            continue  # drop every vN-shaped token from the family string
        remaining.append(t)

    role = "other"
    if remaining and remaining[-1].lower() in ROLE_KEYWORDS:
        role = remaining[-1].lower()
        remaining = remaining[:-1]

    family_suffix = "_".join(remaining)
    if before and family_suffix:
        family = before + "_" + family_suffix
    elif before:
        family = before
    elif family_suffix:
        family = family_suffix
    else:
        family = name

    return family, stamp, version, role


def is_raw_capture(name, has_raw_ext):
    lname = name.lower()
    if any(tok in lname for tok in RAW_NAME_TOKENS):
        return True
    return has_raw_ext


# ---------------------------------------------------------------------------
# Code corpus (for referenced_by grep)
# ---------------------------------------------------------------------------

def _add_file(corpus, path, max_bytes=25 * 1024 * 1024):
    try:
        if os.path.getsize(path) > max_bytes:
            return
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError:
        return
    rel = os.path.relpath(path, LIVE)
    corpus.append((rel, content))


def load_code_corpus():
    """One-time load of every 'code that pins generations' file's content.
    Returns a list of (relpath-from-LIVE, content) tuples."""
    corpus = []

    for dirpath, _dirnames, filenames in os.walk(FEC_DIR):
        for fn in filenames:
            low = fn.lower()
            if low.endswith(".py") or low.endswith(".tpl"):
                _add_file(corpus, os.path.join(dirpath, fn))

    engine_dir = os.path.join(LIVE, "data", "engine")
    if os.path.isdir(engine_dir):
        for fn in os.listdir(engine_dir):
            fp = os.path.join(engine_dir, fn)
            if fn.lower().endswith(".json") and os.path.isfile(fp):
                _add_file(corpus, fp)

    if os.path.isdir(STORE1):
        for fn in os.listdir(STORE1):
            fp = os.path.join(STORE1, fn)
            if fn.lower().endswith(".py") and os.path.isfile(fp) and fn != SCRIPT_NAME:
                _add_file(corpus, fp)

    for dirpath, _dirnames, filenames in os.walk(STORE2):
        for fn in filenames:
            if fn.lower().endswith(".json"):
                _add_file(corpus, os.path.join(dirpath, fn))

    audits_dir = os.path.join(LIVE, "audits")
    if os.path.isdir(audits_dir):
        for fn in os.listdir(audits_dir):
            fp = os.path.join(audits_dir, fn)
            if fn.lower().endswith(".md") and os.path.isfile(fp):
                _add_file(corpus, fp)

    return corpus


def find_referenced_by(name, corpus, limit=10):
    hits = []
    for relpath, content in corpus:
        if name in content:
            hits.append(relpath)
            if len(hits) >= limit:
                break
    return hits


# ---------------------------------------------------------------------------
# Store 1: per-generation-directory walk
# ---------------------------------------------------------------------------

def walk_generation(path):
    total_bytes = 0
    file_count = 0
    newest_mtime = 0.0
    has_raw_ext = False
    receipts = []
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
            if RECEIPT_RE.match(fn):
                receipts.append(fp)
    if newest_mtime == 0.0:
        try:
            newest_mtime = os.stat(path).st_mtime
        except OSError:
            pass
    return {
        "bytes": total_bytes,
        "file_count": file_count,
        "newest_mtime": newest_mtime,
        "has_raw_ext": has_raw_ext,
        "receipts": receipts,
    }


def read_receipt_fields(receipt_paths):
    fields = {}
    names = []
    for rp in receipt_paths:
        names.append(os.path.basename(rp))
        try:
            with open(rp, "r", encoding="utf-8", errors="replace") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict):
            for field in RECEIPT_FIELDS:
                if field not in fields and data.get(field) is not None:
                    fields[field] = data.get(field)
    return names, fields


def build_store1_registry(corpus, now_ts):
    generations = []
    for name in sorted(os.listdir(STORE1)):
        path = os.path.join(STORE1, name)
        if not os.path.isdir(path):
            continue
        stats = walk_generation(path)
        family, stamp, version, role = parse_generation_name(name)
        receipt_names, receipt_fields = read_receipt_fields(stats["receipts"])
        referenced_by = find_referenced_by(name, corpus)
        gen = {
            "name": name,
            "family": family,
            "stamp": stamp,
            "version": version,
            "role": role,
            "bytes": stats["bytes"],
            "file_count": stats["file_count"],
            "newest_mtime_utc": iso(stats["newest_mtime"]),
            "newest_mtime_epoch": stats["newest_mtime"],
            "receipt_files": receipt_names,
            "receipt_paths": stats["receipts"],
            "receipt_status": receipt_fields.get("status"),
            "receipt_verdict": receipt_fields.get("verdict"),
            "receipt_promotion_policy": receipt_fields.get("promotion_policy"),
            "receipt_review_status": receipt_fields.get("review_status"),
            "is_raw_capture": is_raw_capture(name, stats["has_raw_ext"]),
            "referenced_by": referenced_by,
            "referenced_by_truncated_at_10": len(referenced_by) >= 10,
        }
        generations.append(gen)

    family_groups = defaultdict(list)
    for g in generations:
        family_groups[g["family"]].append(g)
    for _fam, members in family_groups.items():
        newest_key = max(
            (stamp_sort_key(g["stamp"]), version_num(g["version"])) for g in members
        )
        for g in members:
            g["is_newest_of_family"] = (
                stamp_sort_key(g["stamp"]),
                version_num(g["version"]),
            ) == newest_key

    age_floor_ts = now_ts - 48 * 3600
    for g in generations:
        reasons = []
        if g["referenced_by"]:
            reasons.append("referenced_by")
        if g["is_newest_of_family"]:
            reasons.append("newest_of_family")
        if g["is_raw_capture"]:
            reasons.append("raw_capture")
        if g["newest_mtime_epoch"] and g["newest_mtime_epoch"] >= age_floor_ts:
            reasons.append("recent_mtime_48h")
        g["active_reasons"] = reasons
        g["class"] = "ACTIVE" if reasons else "INACTIVE"

    return generations


# ---------------------------------------------------------------------------
# Store 2 report
# ---------------------------------------------------------------------------

def build_store2_report():
    subdirs = []
    top_level_loose_files = 0
    if os.path.isdir(STORE2):
        for name in sorted(os.listdir(STORE2)):
            path = os.path.join(STORE2, name)
            if not os.path.isdir(path):
                top_level_loose_files += 1
                continue
            total_bytes = 0
            file_count = 0
            newest_mtime = 0.0
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
            subdirs.append(
                {
                    "name": name,
                    "bytes": total_bytes,
                    "file_count": file_count,
                    "newest_mtime_utc": iso(newest_mtime),
                }
            )

    all_files = []
    for dirpath, _dirnames, filenames in os.walk(STORE2):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            try:
                st = os.stat(fp)
            except OSError:
                continue
            all_files.append((st.st_mtime, os.path.relpath(fp, STORE2), st.st_size))
    all_files.sort(reverse=True)
    newest10 = [
        {"path": p, "bytes": b, "mtime_utc": iso(m)} for m, p, b in all_files[:10]
    ]
    return {
        "subdirs": subdirs,
        "top_level_loose_files": top_level_loose_files,
        "newest_10_files": newest10,
    }


# ---------------------------------------------------------------------------
# Store 3 report
# ---------------------------------------------------------------------------

def build_store3_report():
    top_level = []
    if os.path.isdir(STORE3):
        for name in sorted(os.listdir(STORE3)):
            path = os.path.join(STORE3, name)
            total_bytes = 0
            file_count = 0
            newest_mtime = 0.0
            is_dir = os.path.isdir(path)
            if is_dir:
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
            else:
                try:
                    st = os.stat(path)
                    total_bytes = st.st_size
                    file_count = 1
                    newest_mtime = st.st_mtime
                except OSError:
                    pass
            top_level.append(
                {
                    "name": name,
                    "is_dir": is_dir,
                    "bytes": total_bytes,
                    "file_count": file_count,
                    "newest_mtime_utc": iso(newest_mtime) if newest_mtime else None,
                }
            )

    sqlite_files = []
    if os.path.isdir(STORE3):
        for dirpath, _dirnames, filenames in os.walk(STORE3):
            for fn in filenames:
                if not fn.lower().endswith(".sqlite"):
                    continue
                base = os.path.join(dirpath, fn)
                try:
                    main_bytes = os.path.getsize(base)
                except OSError:
                    main_bytes = None
                wal_path = base + "-wal"
                shm_path = base + "-shm"
                wal_bytes = os.path.getsize(wal_path) if os.path.exists(wal_path) else 0
                shm_bytes = os.path.getsize(shm_path) if os.path.exists(shm_path) else 0
                sqlite_files.append(
                    {
                        "path": os.path.relpath(base, STORE3),
                        "bytes": main_bytes,
                        "wal_present": os.path.exists(wal_path),
                        "wal_bytes": wal_bytes,
                        "shm_present": os.path.exists(shm_path),
                        "shm_bytes": shm_bytes,
                    }
                )

    return {"top_level": top_level, "sqlite_files": sqlite_files}


def find_store3_readers(corpus):
    """Literal-pattern grep over the fec/ portion of the already-loaded
    corpus, plus every paths.py line that defines a Store-3 location, plus
    a supplementary scan for consumers of the paths.py Store-3 constants."""
    literal_hits = []
    fec_prefix = "fec" + os.sep
    for relpath, content in corpus:
        if not relpath.startswith(fec_prefix):
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            for pat in STORE3_LITERAL_PATTERNS:
                if pat in line:
                    literal_hits.append(
                        {
                            "file": relpath,
                            "line": i,
                            "pattern": pat,
                            "text": line.strip()[:200],
                        }
                    )

    paths_py_entries = []
    const_consumers = []
    for relpath, content in corpus:
        if relpath != os.path.join("fec", "paths.py"):
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if "STAFFER_NETWORK" in line or "staffer_network" in line.lower():
                paths_py_entries.append({"file": relpath, "line": i, "text": line.strip()[:200]})

    for relpath, content in corpus:
        if not relpath.startswith(fec_prefix):
            continue
        if relpath == os.path.join("fec", "paths.py"):
            continue
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            for const in CONST_NAMES:
                if const in line:
                    const_consumers.append(
                        {"file": relpath, "line": i, "const": const, "text": line.strip()[:200]}
                    )

    return literal_hits, paths_py_entries, const_consumers


# ---------------------------------------------------------------------------
# Disk free space
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# OneDrive placeholder check for Store 1
# ---------------------------------------------------------------------------

def check_onedrive_placeholders():
    total_files = 0
    placeholder_files = 0
    placeholder_bytes = 0
    local_files = 0
    local_bytes = 0
    sample_placeholders = []
    for dirpath, _dirnames, filenames in os.walk(STORE1):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            try:
                st = os.stat(fp)
            except OSError:
                continue
            total_files += 1
            attrs = getattr(st, "st_file_attributes", 0)
            if attrs & PLACEHOLDER_MASK:
                placeholder_files += 1
                placeholder_bytes += st.st_size
                if len(sample_placeholders) < 10:
                    sample_placeholders.append(os.path.relpath(fp, STORE1))
            else:
                local_files += 1
                local_bytes += st.st_size
    return {
        "total_files": total_files,
        "placeholder_files": placeholder_files,
        "placeholder_bytes": placeholder_bytes,
        "locally_present_files": local_files,
        "locally_present_bytes": local_bytes,
        "sample_placeholder_paths": sample_placeholders,
    }


# ---------------------------------------------------------------------------
# Currency report
# ---------------------------------------------------------------------------

def _safe_load_json(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _pick_primary_receipt(generations, family_name):
    candidates = [
        g for g in generations if g["family"] == family_name and g["is_newest_of_family"]
    ]
    primaries = [g for g in candidates if g["role"] == "primary"]
    pool = primaries or candidates
    for g in pool:
        for rp in g["receipt_paths"]:
            data = _safe_load_json(rp)
            if data is not None:
                return g["name"], rp, data
    return (pool[0]["name"] if pool else None), None, None


def latest_politico_profile_date():
    best = None
    best_source = None
    if os.path.isdir(STORE1):
        for name in sorted(os.listdir(STORE1)):
            if "politico_profile_crawl" not in name:
                continue
            pf = os.path.join(STORE1, name, "profiles.ndjson")
            if not os.path.isfile(pf):
                continue
            try:
                with open(pf, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rec = json.loads(line)
                        except ValueError:
                            continue
                        val = rec.get("observed_at")
                        if isinstance(val, str) and (best is None or val > best):
                            best = val
                            best_source = os.path.join(name, "profiles.ndjson")
            except OSError:
                continue
    return best, best_source


def build_currency_report(generations):
    hps_name, hps_path, hps_data = _pick_primary_receipt(generations, "hill_personnel_spine")
    hpl_name, hpl_path, hpl_data = _pick_primary_receipt(generations, "house_personnel_ledger")

    house_quarter_hps = None
    senate_period_hps = None
    if isinstance(hps_data, dict):
        lpbc = hps_data.get("latest_period_by_chamber") or {}
        house_quarter_hps = lpbc.get("house")
        senate_period_hps = lpbc.get("senate")

    house_quarter_hpl = None
    if isinstance(hpl_data, dict):
        q = hpl_data.get("quarters") or {}
        house_quarter_hpl = q.get("latest_quarter_on_disk")

    politico_date, politico_source = latest_politico_profile_date()

    return {
        "hill_personnel_spine": {
            "generation": hps_name,
            "receipt_path": os.path.relpath(hps_path, LIVE) if hps_path else None,
            "latest_house_payroll_quarter": house_quarter_hps,
            "latest_senate_report_period": senate_period_hps,
        },
        "house_personnel_ledger": {
            "generation": hpl_name,
            "receipt_path": os.path.relpath(hpl_path, LIVE) if hpl_path else None,
            "latest_house_payroll_quarter": house_quarter_hpl,
        },
        "politico_crawl": {
            "newest_profile_observed_at": politico_date,
            "source": politico_source,
        },
    }


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------

def write_json(doc):
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2, sort_keys=False, ensure_ascii=False)


def write_inactive_txt(inactive_sorted):
    total_bytes = sum(g["bytes"] for g in inactive_sorted)
    with open(OUT_INACTIVE, "w", encoding="utf-8") as f:
        f.write(
            "# {} inactive directories, {} bytes total ({}) -- delete candidates, "
            "largest first. Format: <bytes>\\t<absolute path>\n".format(
                len(inactive_sorted), total_bytes, human_bytes(total_bytes)
            )
        )
        for g in inactive_sorted:
            f.write("{}\t{}\n".format(g["bytes"], os.path.join(STORE1, g["name"])))


def md_table(headers, rows):
    out = []
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        out.append("| " + " | ".join(str(c) if c is not None else "" for c in row) + " |")
    return "\n".join(out)


def write_md(doc):
    s1 = doc["store1"]
    generations = s1["generations"]
    totals_class = s1["totals_by_class"]
    totals_family = s1["totals_by_family"]
    top10 = s1["top10_largest_inactive"]
    flagged = s1["flagged_active_for_review"]
    store2 = doc["store2"]
    store3 = doc["store3"]
    disk = doc["disk"]
    onedrive = doc["onedrive"]
    currency = doc["currency"]

    lines = []
    lines.append("# Staffer-Network Generation Registry -- {}".format(doc["generated_at_utc"]))
    lines.append("")
    lines.append(
        "Read-only inventory. Nothing was deleted, moved, renamed, or compressed. "
        "Generated by `build_generation_registry.py`."
    )
    lines.append("")

    lines.append("## Class rule")
    lines.append("")
    lines.append("A generation directory is **ACTIVE** if any of:")
    lines.append("1. `referenced_by` is non-empty (its name appears in a pinning code file).")
    lines.append(
        "2. It is the newest (stamp, version) of its family -- all roles of that newest "
        "generation count as active together."
    )
    lines.append(
        "3. It is a raw capture -- name contains raw/crawl/download/snapshot/sod/"
        "ledger_source, or it holds .pdf/.csv/.html files. Raw inputs are never delete "
        "candidates."
    )
    lines.append("4. Its newest mtime is within the last 48 hours (possibly in flight).")
    lines.append("")
    lines.append("Otherwise it is **INACTIVE**. See the script's module docstring for the exact "
                  "family/stamp/version/role parsing algorithm and its documented limitations.")
    lines.append("")

    lines.append("## Store 1 -- audits\\staffer_network (generation directories)")
    lines.append("")
    lines.append(
        "Total subdirectories scanned: **{}**".format(len(generations))
    )
    lines.append("")
    class_rows = []
    for cls in ("ACTIVE", "INACTIVE"):
        t = totals_class.get(cls, {"dirs": 0, "bytes": 0})
        class_rows.append([cls, t["dirs"], human_bytes(t["bytes"]), t["bytes"]])
    lines.append(md_table(["Class", "Dirs", "Bytes (human)", "Bytes (exact)"], class_rows))
    lines.append("")

    lines.append("### Ten largest INACTIVE directories")
    lines.append("")
    rows = [
        [g["name"], human_bytes(g["bytes"]), g["file_count"], g["newest_mtime_utc"]]
        for g in top10
    ]
    lines.append(md_table(["Name", "Bytes", "Files", "Newest mtime (UTC)"], rows))
    lines.append("")

    lines.append("### Per-family totals")
    lines.append("")
    fam_rows = []
    for fam in sorted(totals_family.keys()):
        t = totals_family[fam]
        fam_rows.append(
            [
                fam,
                t["dirs"],
                t["active_dirs"],
                t["inactive_dirs"],
                human_bytes(t["bytes"]),
                human_bytes(t["inactive_bytes"]),
            ]
        )
    lines.append(
        md_table(
            ["Family", "Dirs", "Active", "Inactive", "Total bytes", "Inactive bytes"],
            fam_rows,
        )
    )
    lines.append("")

    lines.append(
        "### Flagged for manual review (ACTIVE by the mechanical rule, but the name carries "
        "a superseded/failed/defect-style marker)"
    )
    lines.append("")
    if flagged:
        rows = [
            [g["name"], human_bytes(g["bytes"]), ", ".join(g["active_reasons"])]
            for g in flagged
        ]
        lines.append(md_table(["Name", "Bytes", "Why it is ACTIVE"], rows))
    else:
        lines.append("(none)")
    lines.append("")

    lines.append("### Full generation listing")
    lines.append("")
    lines.append(
        "One row per actual subdirectory (the `Name` column is the literal directory name "
        "under Store 1 -- use it to find the folder on disk). Two directories can share the "
        "same derived family/stamp/version/role (see Notes) so `Name` is the only column "
        "guaranteed unique."
    )
    lines.append("")
    rows = []
    for g in sorted(generations, key=lambda g: (g["family"], g["stamp"], g["version"], g["role"], g["name"])):
        rows.append(
            [
                g["name"],
                g["family"],
                g["stamp"],
                g["version"],
                g["role"],
                human_bytes(g["bytes"]),
                g["file_count"],
                (g["newest_mtime_utc"] or "")[:10],
                g["class"],
                ",".join(g["active_reasons"]),
            ]
        )
    lines.append(
        md_table(
            ["Name", "Family", "Stamp", "Ver", "Role", "Bytes", "Files", "Newest date", "Class", "Why"],
            rows,
        )
    )
    lines.append("")

    lines.append("### Receipts (status / verdict / promotion_policy where present)")
    lines.append("")
    receipt_rows = []
    for g in generations:
        if not g["receipt_files"]:
            continue
        if not any(
            g.get(k) is not None
            for k in ("receipt_status", "receipt_verdict", "receipt_promotion_policy", "receipt_review_status")
        ):
            continue
        receipt_rows.append(
            [
                g["name"],
                ", ".join(g["receipt_files"]),
                g.get("receipt_status") or "",
                g.get("receipt_verdict") or "",
                g.get("receipt_promotion_policy") or "",
                g.get("receipt_review_status") or "",
            ]
        )
    lines.append(
        md_table(
            ["Name", "Receipt file(s)", "status", "verdict", "promotion_policy", "review_status"],
            receipt_rows,
        )
    )
    lines.append("")

    lines.append("## Store 2 -- data\\staffer_network")
    lines.append("")
    rows = [
        [d["name"], human_bytes(d["bytes"]), d["file_count"], d["newest_mtime_utc"]]
        for d in store2["subdirs"]
    ]
    lines.append(md_table(["Subdirectory", "Bytes", "Files", "Newest mtime (UTC)"], rows))
    lines.append("")
    lines.append("Newest 10 files:")
    lines.append("")
    rows = [[f["path"], human_bytes(f["bytes"]), f["mtime_utc"]] for f in store2["newest_10_files"]]
    lines.append(md_table(["Path (relative to Store 2)", "Bytes", "Mtime (UTC)"], rows))
    lines.append("")

    lines.append("## Store 3 -- AppData\\Local\\Melange\\staffer_network (off-repo, ~17 GB)")
    lines.append("")
    rows = [
        [
            e["name"] + ("/" if e["is_dir"] else ""),
            human_bytes(e["bytes"]),
            e["file_count"],
            e["newest_mtime_utc"],
        ]
        for e in store3["top_level"]
    ]
    lines.append(md_table(["Top-level entry", "Bytes", "Files", "Newest mtime (UTC)"], rows))
    lines.append("")

    lines.append("### *.sqlite files and their -wal / -shm sidecars")
    lines.append("")
    rows = [
        [
            s["path"],
            human_bytes(s["bytes"]),
            human_bytes(s["wal_bytes"]) if s["wal_present"] else "(none)",
            human_bytes(s["shm_bytes"]) if s["shm_present"] else "(none)",
        ]
        for s in store3["sqlite_files"]
    ]
    lines.append(md_table(["sqlite file", "Main bytes", "-wal bytes", "-shm bytes"], rows))
    wal_total = sum(s["wal_bytes"] + s["shm_bytes"] for s in store3["sqlite_files"])
    lines.append("")
    lines.append(
        "**WAL/SHM finding:** {} bytes ({}) currently reclaimable by a checkpoint across "
        "{} *.sqlite file(s). No checkpoint was run.".format(
            wal_total, human_bytes(wal_total), len(store3["sqlite_files"])
        )
    )
    lines.append("")

    lines.append("### fec\\ code that reads Store 3")
    lines.append("")
    lines.append(
        "Literal grep for `Melange\\\\staffer_network`, `Local\\\\Melange`, `MELANGE_STAFFER`, "
        "`staffer_network_store`:"
    )
    lines.append("")
    hits = doc["store3_readers"]["literal_hits"]
    if hits:
        rows = [[h["file"] + ":" + str(h["line"]), h["pattern"], h["text"]] for h in hits]
        lines.append(md_table(["file:line", "pattern", "text"], rows))
    else:
        lines.append("(no literal substring hits)")
    lines.append("")
    lines.append("`fec\\paths.py` entries that define the Store-3 location:")
    lines.append("")
    rows = [[h["file"] + ":" + str(h["line"]), h["text"]] for h in doc["store3_readers"]["paths_py_entries"]]
    lines.append(md_table(["file:line", "text"], rows))
    lines.append("")
    lines.append(
        "Supplementary -- other fec\\ files consuming the paths.py Store-3 constants "
        "(STAFFER_NETWORK_* / DATA_STAFFER_NETWORK) by name:"
    )
    lines.append("")
    consumers = doc["store3_readers"]["const_consumers"]
    if consumers:
        rows = [[c["file"] + ":" + str(c["line"]), c["const"], c["text"]] for c in consumers]
        lines.append(md_table(["file:line", "constant", "text"], rows))
    else:
        lines.append("(none found)")
    lines.append("")

    lines.append("## Disk")
    lines.append("")
    inactive_bytes = totals_class.get("INACTIVE", {}).get("bytes", 0)
    rows = [
        ["Free on C: right now", human_bytes(disk["free_bytes_before"]), disk["free_bytes_before"]],
        [
            "Would be freed by deleting all INACTIVE Store-1 dirs",
            human_bytes(inactive_bytes),
            inactive_bytes,
        ],
        [
            "Would be freed by checkpointing the *.sqlite WAL/SHM files",
            human_bytes(wal_total),
            wal_total,
        ],
    ]
    lines.append(md_table(["Item", "Bytes (human)", "Bytes (exact)"], rows))
    lines.append("")

    lines.append("## OneDrive placeholder check (Store 1)")
    lines.append("")
    rows = [
        ["Total files scanned", onedrive["total_files"], ""],
        [
            "Locally present",
            onedrive["locally_present_files"],
            human_bytes(onedrive["locally_present_bytes"]),
        ],
        [
            "Cloud-only placeholders",
            onedrive["placeholder_files"],
            human_bytes(onedrive["placeholder_bytes"]),
        ],
    ]
    lines.append(md_table(["Item", "Count", "Bytes"], rows))
    lines.append("")

    lines.append("## Currency")
    lines.append("")
    hps = currency["hill_personnel_spine"]
    hpl = currency["house_personnel_ledger"]
    pol = currency["politico_crawl"]
    rows = [
        [
            "Latest House payroll quarter (hill_personnel_spine receipt)",
            hps["latest_house_payroll_quarter"],
            hps["generation"],
        ],
        [
            "Latest House payroll quarter (house_personnel_ledger receipt)",
            hpl["latest_house_payroll_quarter"],
            hpl["generation"],
        ],
        [
            "Latest Senate report period (hill_personnel_spine receipt)",
            hps["latest_senate_report_period"],
            hps["generation"],
        ],
        [
            "Politico crawl newest profile observed_at",
            pol["newest_profile_observed_at"],
            pol["source"],
        ],
    ]
    lines.append(md_table(["Metric", "Value", "Source generation"], rows))
    lines.append("")

    lines.append("## Notes and known limitations")
    lines.append("")
    lines.append(
        "- A second, trailing `vN` token (e.g. `..._v5_verification_v2`) is dropped rather than "
        "kept in the family string, so that directory and its plain `..._v5_verification` "
        "sibling can be compared for recency as the same lineage. The side effect: both then "
        "report the identical (family, stamp, version, role) tuple in the table below even "
        "though they are two different directories -- always key off the `Name` column, never "
        "off family/stamp/version/role alone, when mapping a row back to disk."
    )
    lines.append(
        "- Only `vN` tokens are recognized as version markers. Alternate iteration markers "
        "(generationN, checkpointN, r2/r3, prev1, a trailing second _v2, _failed_*, _rebuild) "
        "stay embedded in the family string, so a directory carrying one becomes its own "
        "singleton family and defaults to ACTIVE via the trivial newest-of-family rule. "
        "Search the JSON for family strings containing `generation` or `checkpoint` to review "
        "these lineages by hand."
    )
    lines.append(
        "- Directories with no date stamp at all (schema/reference dirs, scratch dirs, "
        "`__pycache__`) are singleton families and default to ACTIVE the same way."
    )
    lines.append(
        "- `referenced_by` is capped at 10 matches per directory and stops scanning once 10 "
        "are found; `referenced_by_truncated_at_10=true` means there may be more."
    )
    lines.append(
        "- This script never deletes, moves, renames, or compresses anything. The "
        "`_inactive.txt` file is a candidate list for Paul's own review, not an action taken."
    )
    lines.append("")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t0 = time.time()
    log("build_generation_registry.py starting")
    now_ts = time.time()

    log("Loading code corpus for referenced_by grep ...")
    corpus = load_code_corpus()
    total_chars = sum(len(c) for _, c in corpus)
    log("  loaded {} files, {:,} characters".format(len(corpus), total_chars))

    log("Walking Store 1 generation directories ...")
    generations = build_store1_registry(corpus, now_ts)
    log("  found {} subdirectories".format(len(generations)))

    log("Building Store 2 report ...")
    store2 = build_store2_report()

    log("Building Store 3 report (this walks ~17 GB, may take a minute) ...")
    store3 = build_store3_report()
    log("  Store 3: {} top-level entries, {} sqlite files".format(
        len(store3["top_level"]), len(store3["sqlite_files"])
    ))

    log("Scanning fec\\ for Store 3 references ...")
    literal_hits, paths_py_entries, const_consumers = find_store3_readers(corpus)

    log("Checking disk free space ...")
    free_before, total_c = get_disk_free_bytes("C:\\")

    log("Checking OneDrive placeholder status for Store 1 ...")
    onedrive = check_onedrive_placeholders()

    log("Building currency report ...")
    currency = build_currency_report(generations)

    log("Computing aggregates ...")
    totals_by_class = defaultdict(lambda: {"dirs": 0, "bytes": 0})
    totals_by_family = defaultdict(
        lambda: {
            "dirs": 0,
            "bytes": 0,
            "active_dirs": 0,
            "inactive_dirs": 0,
            "active_bytes": 0,
            "inactive_bytes": 0,
        }
    )
    for g in generations:
        totals_by_class[g["class"]]["dirs"] += 1
        totals_by_class[g["class"]]["bytes"] += g["bytes"]
        tf = totals_by_family[g["family"]]
        tf["dirs"] += 1
        tf["bytes"] += g["bytes"]
        if g["class"] == "ACTIVE":
            tf["active_dirs"] += 1
            tf["active_bytes"] += g["bytes"]
        else:
            tf["inactive_dirs"] += 1
            tf["inactive_bytes"] += g["bytes"]

    inactive = [g for g in generations if g["class"] == "INACTIVE"]
    inactive_sorted_by_bytes = sorted(inactive, key=lambda g: -g["bytes"])
    top10_inactive = inactive_sorted_by_bytes[:10]

    flagged_active = [
        g
        for g in generations
        if g["class"] == "ACTIVE"
        and any(tok in g["name"].lower() for tok in SUSPECT_TOKENS)
    ]

    # Strip the absolute receipt_paths (internal use only) before the JSON dump
    # keeps things relative/portable; keep a relative echo instead.
    for g in generations:
        g["receipt_paths_relative"] = [os.path.relpath(p, LIVE) for p in g["receipt_paths"]]
        del g["receipt_paths"]

    doc = {
        "generated_at_utc": iso(now_ts),
        "live_root": LIVE,
        "store1_path": STORE1,
        "store2_path": STORE2,
        "store3_path": STORE3,
        "code_paths_scanned": {
            "fec_py_and_tpl": True,
            "data_engine_json_top_level": True,
            "audits_staffer_network_py_top_level": True,
            "data_staffer_network_json_recursive": True,
            "audits_md_top_level": True,
            "files_loaded": len(corpus),
            "characters_loaded": total_chars,
        },
        "store1": {
            "generations": generations,
            "totals_by_class": dict(totals_by_class),
            "totals_by_family": dict(totals_by_family),
            "top10_largest_inactive": top10_inactive,
            "flagged_active_for_review": flagged_active,
        },
        "store2": store2,
        "store3": {
            "top_level": store3["top_level"],
            "sqlite_files": store3["sqlite_files"],
        },
        "store3_readers": {
            "literal_hits": literal_hits,
            "paths_py_entries": paths_py_entries,
            "const_consumers": const_consumers,
        },
        "disk": {
            "drive": "C:\\",
            "free_bytes_before": free_before,
            "total_bytes": total_c,
        },
        "onedrive": onedrive,
        "currency": currency,
    }

    log("Writing outputs ...")
    write_json(doc)
    write_inactive_txt(inactive_sorted_by_bytes)
    write_md(doc)

    elapsed = time.time() - t0
    active_t = totals_by_class.get("ACTIVE", {"dirs": 0, "bytes": 0})
    inactive_t = totals_by_class.get("INACTIVE", {"dirs": 0, "bytes": 0})
    wal_total = sum(s["wal_bytes"] + s["shm_bytes"] for s in store3["sqlite_files"])

    log("Done in {:.1f}s".format(elapsed))
    log(
        "ACTIVE: {} dirs / {} ; INACTIVE: {} dirs / {}".format(
            active_t["dirs"], human_bytes(active_t["bytes"]), inactive_t["dirs"], human_bytes(inactive_t["bytes"])
        )
    )
    log("Wrote: {}".format(OUT_JSON))
    log("Wrote: {}".format(OUT_MD))
    log("Wrote: {}".format(OUT_INACTIVE))

    return {
        "elapsed_s": elapsed,
        "active_dirs": active_t["dirs"],
        "active_bytes": active_t["bytes"],
        "inactive_dirs": inactive_t["dirs"],
        "inactive_bytes": inactive_t["bytes"],
        "wal_reclaim_bytes": wal_total,
        "free_bytes_before": free_before,
        "onedrive_placeholder_files": onedrive["placeholder_files"],
        "onedrive_local_files": onedrive["locally_present_files"],
    }


if __name__ == "__main__":
    summary = main()
    print("SUMMARY_JSON=" + json.dumps(summary))
