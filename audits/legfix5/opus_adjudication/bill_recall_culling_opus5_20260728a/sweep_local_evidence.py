#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exhaustive read-only sweep of local evidence surfaces for the 23 absent measures.

Absence from discovery is neutral, so before any of these 23 may be flagged the
lane has to show it looked everywhere it actually holds evidence.  This walks
the repository and the recovered input root for every citation surface form of
each key and records where it landed.  It decides nothing.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys

OUT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(OUT, "..", "..", "..", ".."))
RECOVERED = r"C:\Users\pgoff\AppData\Local\Temp\claude\cxwt-acu-registry"

KEYS = [
    "118:hjres:195", "118:hjres:190", "119:sjres:134",
    "117:hr:3854", "117:hr:474", "117:s:2034",
    "119:s:3171", "117:hr:6732", "119:s:273", "118:s:673", "117:s:1690",
    "117:s:1587", "119:s:3136", "118:s:3302", "118:s:1159", "117:s:4004",
    "117:s:5076", "118:hr:3511", "117:hres:1076", "117:hres:634",
    "118:hr:2602", "117:hr:3155", "117:s:63",
]

TYPE_DISPLAY = {
    "hr": ["H.R.", "H. R. ", "HR"],
    "s": ["S.", "S. "],
    "hres": ["H.Res.", "H. Res. "],
    "sres": ["S.Res.", "S. Res. "],
    "hjres": ["H.J.Res.", "H. J. Res. "],
    "sjres": ["S.J.Res.", "S. J. Res. "],
}
URL_TYPE = {
    "hr": "house-bill", "s": "senate-bill",
    "hres": "house-resolution", "sres": "senate-resolution",
    "hjres": "house-joint-resolution", "sjres": "senate-joint-resolution",
}


def surface_forms(key):
    congress, mtype, number = key.split(":")
    forms = {key, "%s-%s-%s" % (congress, mtype, number),
             "%s_%s_%s" % (congress, mtype, number),
             "%s%s" % (mtype, number)}
    for disp in TYPE_DISPLAY.get(mtype, []):
        forms.add("%s%s" % (disp, number))
        forms.add("%s %s" % (disp.strip(), number))
    forms.add("%sth-congress/%s/%s" % (congress, URL_TYPE.get(mtype, mtype), number))
    forms.add('cite:"%s%s"' % (mtype, number))
    return sorted(forms)


ALL_FORMS = {k: surface_forms(k) for k in KEYS}

# Restrict to text-bearing extensions; skip the 1.8G content-addressed blob store
# and the govinfo/billstatus object trees, which are keyed by hash not citation.
TEXT_EXT = {".json", ".ndjson", ".jsonl", ".csv", ".txt", ".md", ".xml", ".htm", ".html", ".tsv"}
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "objects",           # govinfo content-addressed store
    "sha256",            # billstatus content-addressed store
}
MAX_BYTES = 400 * 1024 * 1024


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in TEXT_EXT:
                continue
            path = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(path) > MAX_BYTES:
                    continue
            except OSError:
                continue
            yield path


def main():
    hits = {k: [] for k in KEYS}
    scanned = 0
    skipped = []
    roots = [REPO, RECOVERED]
    myself = os.path.abspath(OUT)
    for root in roots:
        if not os.path.isdir(root):
            skipped.append(root)
            continue
        for path in walk(root):
            if os.path.abspath(path).startswith(myself):
                continue
            try:
                with io.open(path, encoding="utf-8", errors="ignore") as fh:
                    blob = fh.read()
            except (OSError, MemoryError):
                skipped.append(path)
                continue
            scanned += 1
            for key, forms in ALL_FORMS.items():
                for form in forms:
                    idx = blob.find(form)
                    if idx < 0:
                        continue
                    # window for eyeballing; the adjudication reads the file itself
                    start, end = max(0, idx - 220), min(len(blob), idx + 320)
                    hits[key].append({
                        "path": os.path.relpath(path, root).replace("\\", "/"),
                        "root": "repo" if root == REPO else "recovered",
                        "form": form,
                        "count": blob.count(form),
                        "excerpt": blob[start:end].replace("\n", " "),
                    })
                    break
    report = {
        "files_scanned": scanned,
        "files_skipped": len(skipped),
        "roots": roots,
        "hits": hits,
        "hit_counts": {k: len(v) for k, v in hits.items()},
    }
    with io.open(os.path.join(OUT, "_local_evidence_sweep.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False, sort_keys=True)
    print("files scanned:", scanned, "skipped:", len(skipped))
    for k in KEYS:
        paths = sorted({h["path"] for h in hits[k]})
        print("%-15s %2d files" % (k, len(paths)))
        for p in paths[:12]:
            print("      ", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
