# -*- coding: utf-8 -*-
"""FIX A5 step 2 -- candidate canonicalisers, measured for over-merge over EVERY live
URL population the press path keys on.  READ-ONLY against LIVE.

The 12 groups all differ by PATH ALIAS (m1), so no scheme/www/slash/case/query/fragment
rule reaches them.  Four candidates are measured here; the additional merges each one
creates are printed in full, with both URLs and both titles, for the coordinator.

Populations keyed on canonical_url() in the shipped press path:
  * tone rows            -> load_tone_rows() `seen` = (canonical_url, identity)
  * fulltext cache       -> load_fulltext() `out[url]`      (url only: a collision here
                            swaps one article's BODY for another's)
  * press_stance_final   -> _stk[(canonical_url, identity)] (stack label + tier)
  * api_press_stance     -> _api_target keyed on the RAW url.rstrip('/'), so a canon
                            change can LOSE an api-target hit; counted both ways.
"""
import collections
import csv
import io
import json
import os
import re
import sys
from urllib.parse import urlsplit, urlunsplit

LIVE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
DRAFT = r"C:\Users\pgoff\OneDrive\Desktop\Draft Systems"
HERE = os.path.dirname(os.path.abspath(__file__))
csv.field_size_limit(1 << 30)


def legacy(value, keep_fragment=True):
    """fec/press_stream.py:68-82 verbatim -- PRESS_URL_CANON=1."""
    value = (value or "").strip()
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        host = parts.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        path = parts.path.rstrip("/") or "/"
        fragment = parts.fragment if keep_fragment else ""
        return urlunsplit((parts.scheme.lower() or "https", host, path, parts.query, fragment))
    except ValueError:
        return value.rstrip("/").lower()


_DUP_SLUG = re.compile(r"^(?P<slug>.*[a-z].*)-0$", re.I)


def _slug_of(path, min_hyphens):
    segments = [s for s in path.split("/") if s]
    if not segments:
        return None
    last = segments[-1]
    if last.count("-") < min_hyphens or not re.search(r"[A-Za-z]", last):
        return None
    return last


def make_candidate(dup_slug, slug_key_hyphens):
    """dup_slug: strip a trailing '-0' duplicate-slug marker from the last segment.
    slug_key_hyphens: if not None, replace the path by its last segment when that
    segment carries at least this many hyphens."""
    def canon(value, keep_fragment=True):
        base = legacy(value, keep_fragment=keep_fragment)
        if not base:
            return base
        try:
            parts = urlsplit(base)
        except ValueError:
            return base
        path = parts.path
        segments = [s for s in path.split("/") if s]
        if segments and dup_slug:
            m = _DUP_SLUG.match(segments[-1])
            if m and "-" in m.group("slug"):
                segments[-1] = m.group("slug")
                path = "/" + "/".join(segments)
        if slug_key_hyphens is not None:
            slug = _slug_of(path, slug_key_hyphens)
            if slug:
                path = "/" + slug
        return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
    return canon


CANDIDATES = [
    ("C1 dup-slug '-0' only", make_candidate(True, None)),
    ("C2 last-segment slug >=2 hyphens", make_candidate(False, 2)),
    ("C3 dup-slug + last-segment >=2 hyphens", make_candidate(True, 2)),
    ("C4 dup-slug + last-segment >=3 hyphens", make_candidate(True, 3)),
]


def read_csv(path):
    if not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_jsonl(path, fields):
    out = []
    if not os.path.exists(path):
        return out
    with io.open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                row = json.loads(line)
            except (TypeError, ValueError):
                continue
            out.append({f: row.get(f) for f in fields})
    return out


print("=" * 108)
print("M2  candidate canonicalisers vs LIVE url populations")
print("=" * 108)

tone = [r for r in (read_csv(os.path.join(DRAFT, "cu_press_stance_tone.csv"))
                    + read_csv(os.path.join(LIVE, "data", "stance", "press_refresh_tone.csv")))
        if (r.get("source") or "").strip().upper() != "OFFICIAL_MENTION"]
print("tone rows read (pre-dedup, OFFICIAL_MENTION dropped): %d" % len(tone))

fulltext = []
for rel in ("press_text_cache.jsonl", r"data\stance\press_text_cache_priority.jsonl",
            r"data\stance\press_refresh_fulltext.jsonl"):
    rows = read_jsonl(os.path.join(LIVE, rel), ("url", "text", "body"))
    print("  fulltext %-52s %6d rows" % (rel, len(rows)))
    fulltext += [r for r in rows if (r.get("text") or r.get("body"))]
stack = read_csv(os.path.join(LIVE, "press_stance_final.csv"))
api = read_csv(os.path.join(LIVE, r"data\stance\api_press_stance.csv"))
print("  press_stance_final.csv %6d rows | api_press_stance.csv %6d rows" % (len(stack), len(api)))

KNOWN = json.load(io.open(os.path.join(HERE, "m1_url_form_classes.json"), encoding="utf-8"))
known_pairs = {frozenset(g["urls"]) for g in KNOWN["groups"]}


def ident(row):
    return (row.get("bioguide") or row.get("member") or "").strip().upper()


def merge_report(name, canon, rows, keyfn, label):
    """Groups that the candidate merges and the legacy key did not."""
    old = collections.defaultdict(list)
    new = collections.defaultdict(list)
    for row in rows:
        old[keyfn(row, legacy)].append(row)
        new[keyfn(row, canon)].append(row)
    extra = []
    for key, group in new.items():
        if len(group) < 2:
            continue
        distinct_old = {keyfn(r, legacy) for r in group}
        if len(distinct_old) > 1:
            extra.append((key, group, distinct_old))
    print("\n  [%s] %s: legacy distinct keys %d -> candidate %d  (%d newly merged groups)"
          % (name, label, len(old), len(new), len(extra)))
    return extra


results = {}
for name, canon in CANDIDATES:
    print("\n" + "-" * 108)
    print(name)
    print("-" * 108)
    entry = {}

    # (1) TONE ROWS -- the fix's target.
    extra = merge_report(name, canon, tone,
                         lambda r, c: (c(r.get("url"), keep_fragment=True), ident(r)),
                         "tone turn key (url, identity)")
    inside = outside = 0
    outside_detail = []
    for key, group, _old in extra:
        urls = {(r.get("url") or "").strip() for r in group}
        if urls in known_pairs or any(urls <= p for p in known_pairs):
            inside += 1
        else:
            outside += 1
            outside_detail.append({
                "key": list(key),
                "rows": [{"member": r.get("member"), "date": r.get("date"),
                          "title": (r.get("title") or "")[:100],
                          "url": (r.get("url") or "").strip(),
                          "stance": r.get("stance"),
                          "press_value": r.get("press_value")} for r in group]})
    print("      of those: %d are one of the 12 KNOWN groups, %d are ADDITIONAL" % (inside, outside))
    for item in outside_detail:
        print("      ADDITIONAL MERGE  key=%s" % (item["key"],))
        for row in item["rows"]:
            print("         %-20s %-12s %s" % ((row["member"] or "")[:20], row["date"] or "",
                                               row["url"]))
            print("            title: %s" % row["title"])
    entry["tone_known"] = inside
    entry["tone_additional"] = outside
    entry["tone_additional_detail"] = outside_detail

    # (2) FULLTEXT CACHE -- keyed on url ALONE, so a collision swaps bodies.
    ft_extra = merge_report(name, canon, fulltext,
                            lambda r, c: c(r.get("url"), keep_fragment=True),
                            "fulltext cache key (url only)")
    body_changes = []
    for key, group, _old in ft_extra:
        bodies = {(r.get("text") or r.get("body") or "")[:400] for r in group}
        if len(bodies) > 1:
            body_changes.append({"key": key,
                                 "urls": [(r.get("url") or "").strip() for r in group],
                                 "n_distinct_bodies": len(bodies)})
    print("      collisions whose members carry DIFFERENT body text: %d" % len(body_changes))
    for item in body_changes[:40]:
        print("      BODY COLLISION  %s" % (item["key"],))
        for url in item["urls"]:
            print("         %s" % url)
    entry["fulltext_collisions"] = len(ft_extra)
    entry["fulltext_body_collisions"] = len(body_changes)
    entry["fulltext_body_collision_detail"] = body_changes

    # (3) press_stance_final -- keyed (url, identity); a collision changes a stack label.
    st_extra = merge_report(name, canon, stack,
                            lambda r, c: (c(r.get("url"), keep_fragment=True), ident(r)),
                            "stack key (url, identity)")
    label_changes = []
    for key, group, _old in st_extra:
        labels = {((r.get("stack_label") or "").strip().lower(),
                   (r.get("tier") or "").strip().lower()) for r in group}
        if len(labels) > 1:
            label_changes.append({"key": list(key), "labels": sorted(labels),
                                  "urls": [(r.get("url") or "").strip() for r in group]})
    print("      collisions whose members carry DIFFERENT (stack_label, tier): %d" % len(label_changes))
    for item in label_changes[:40]:
        print("      LABEL COLLISION %r  %r" % (item["key"], item["labels"]))
        for url in item["urls"]:
            print("         %s" % url)
    entry["stack_collisions"] = len(st_extra)
    entry["stack_label_collisions"] = len(label_changes)
    entry["stack_label_collision_detail"] = label_changes

    # (4) api_press_stance -- keyed on the RAW url; a canon change can LOSE a target hit.
    api_keys = {(r.get("url") or "").strip().rstrip("/"): (r.get("api_target") or "").strip()
                for r in api}
    old_hits = sum(1 for r in tone if legacy(r.get("url"), keep_fragment=True) in api_keys)
    new_hits = sum(1 for r in tone if canon(r.get("url"), keep_fragment=True) in api_keys)
    print("\n      api_press_stance target hits over tone rows: legacy %d -> candidate %d"
          % (old_hits, new_hits))
    entry["api_hits_legacy"] = old_hits
    entry["api_hits_candidate"] = new_hits
    results[name] = entry

with io.open(os.path.join(HERE, "m2_canon_candidates.json"), "w", encoding="utf-8") as fh:
    json.dump(results, fh, indent=1, ensure_ascii=False)
print("\nDONE M2")
