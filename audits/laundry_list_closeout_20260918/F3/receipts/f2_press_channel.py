# -*- coding: utf-8 -*-
# F3 r2: PRESS channel close-out for the STANCE path.
#   items in -> disposition buckets (each a quoted LIVE rule) -> stance-eligible vs non-stance columns
#   reconciled against the producer's own ledgers (press_component_meta.json,
#   press_domain_routing_audit.json), and the 2-URL-form duplicate class traced to its stance cell.
# READ-ONLY.  Nothing under LIVE\fec is imported.
import os, sys, io, csv, json, collections, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f_lib as F

LIVE  = F.LIVE
DRAFT = r"C:\Users\pgoff\OneDrive\Desktop\Draft Systems"
HERE  = os.path.dirname(os.path.abspath(__file__))
MR    = F.media_rules()
RAW2ST, GENERAL, COMPET = MR["RAW_TO_STANCE"], MR["GENERAL"], MR["COMPETITIVE"]
STANCE_ELIGIBLE = set(RAW2ST)          # the 18 raw headers that HAVE a stance column
NON_STANCE      = {COMPET, GENERAL}    # carried on the sheet, never read into a stance cell

print("=" * 108)
print("F3 r2  PRESS channel -> stance cells    run %s" % datetime.datetime.now().isoformat(timespec="seconds"))
print("=" * 108)

# ---------------------------------------------------------------- (a) ingest accounting
BASE    = os.path.join(DRAFT, "cu_press_stance_tone.csv")
REFRESH = os.path.join(LIVE, "data", "stance", "press_refresh_tone.csv")

def canonical_url(value, keep_fragment=True):
    """Mirror of LIVE fec/press_stream.py:68-82."""
    from urllib.parse import urlsplit, urlunsplit
    value = (value or "").strip()
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        host = parts.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        path = parts.path.rstrip("/") or "/"
        frag = parts.fragment if keep_fragment else ""
        return urlunsplit((parts.scheme.lower() or "https", host, path, parts.query, frag))
    except ValueError:
        return value.rstrip("/").lower()

def turn_key(row):
    """Mirror of LIVE fec/press_stream.py:85-88."""
    return canonical_url(row.get("url"), keep_fragment=True), (row.get("bioguide") or row.get("member") or "").strip().upper()

def read_csv(path):
    if not path or not os.path.exists(path):
        return []
    with io.open(path, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))

print("\n(a) INGEST  -- LIVE fec/press_stream.py:98-118  load_tone_rows()")
print("    RULE press_stream.py:111  if (row.get('source') or '').strip().upper()=='OFFICIAL_MENTION': continue")
print("    RULE press_stream.py:114  if not key[0] or key in seen: continue   # key=(canonical_url, bioguide|member)")
tot = off = nourl = dup = 0
rows, seen = [], set()
per_src = {}
for src in (BASE, REFRESH):
    n0 = len(rows)
    raw = read_csv(src)
    a = b = c = 0
    for r in raw:
        tot += 1
        if (r.get("source") or "").strip().upper() == "OFFICIAL_MENTION":
            off += 1; a += 1; continue
        k = turn_key(r)
        if not k[0]:
            nourl += 1; b += 1; continue
        if k in seen:
            dup += 1; c += 1; continue
        seen.add(k); rows.append(r)
    per_src[os.path.basename(src)] = {"read": len(raw), "official_mention": a, "empty_url": b,
                                      "turnkey_dup": c, "kept": len(rows) - n0}
for k, v in per_src.items():
    print("    %-32s read %-6d OFFICIAL_MENTION %-5d empty-url %-4d turn-key dup %-5d kept %d"
          % (k, v["read"], v["official_mention"], v["empty_url"], v["turnkey_dup"], v["kept"]))
print("    ---- rows read %d | excluded: OFFICIAL_MENTION %d, empty url %d, duplicate turn key %d"
      % (tot, off, nourl, dup))
print("    ---- tone_rows handed to the blend: %d   unaccounted: %d"
      % (len(rows), tot - off - nourl - dup - len(rows)))

META = json.load(open(os.path.join(LIVE, "data", "stance", "press_component_meta.json"), encoding="utf-8"))
print("    producer's own count (press_component_meta.json 'tone_rows'): %d   MATCH: %s"
      % (META["tone_rows"], META["tone_rows"] == len(rows)))

# ---------------------------------------------------------------- (b) disposition buckets
AUD = json.load(open(os.path.join(LIVE, "data", "stance", "press_domain_routing_audit.json"), encoding="utf-8"))
arows = AUD["rows"]
print("\n(b) SCORING DISPOSITIONS  -- per-row ledger the producer itself wrote")
print("    press_domain_routing_audit.json rows: %d   (== tone_rows: %s)" % (len(arows), len(arows) == len(rows)))
disp = collections.Counter(r["scoring_disposition"] for r in arows)
RULE = {
 "used":              "blend.py:403  _audit['scoring_disposition']='used'   -> contributes",
 "neutral-zeroed":    "blend.py:384-385  if _sg==0.0: disposition='neutral-zeroed'; continue",
 "zero-intensity":    "blend.py:391-392  if _pv==0.0: disposition='zero-intensity'; continue",
 "no-policy-domain":  "blend.py:398-399  if not _cats: disposition='no-policy-domain'; continue",
 "unresolved-member": "blend.py:382-383  if not _m: disposition='unresolved-member'; continue",
 "unrelated-zeroed":  "blend.py:371  stack label 'unrelated' -> _sg=0.0 (then falls to neutral-zeroed)",
}
print("    %-20s %-8s %s" % ("bucket", "rows", "quoted LIVE rule"))
for k, n in disp.most_common():
    print("    %-20s %-8d %s" % (k, n, RULE.get(k, "(no rule mapped)")))
print("    ---- total %d   producer meta dispositions %s   MATCH: %s"
      % (sum(disp.values()), dict(META["routing"]["dispositions"]),
         dict(disp) == dict(META["routing"]["dispositions"])))

# ---------------------------------------------------------------- (c) does 'used' reach a STANCE cell?
print("\n(c) OF THE 'used' ROWS, WHICH REACH A STANCE CELL?")
print("    the blend writes 20 columns (blend.py:443 HDRMAP); per_category_stance reads 18")
print("    -> a row routed ONLY to 'CU-Bank Competitive Dynamics' and/or 'General Credit Union'")
print("       lands on the sheet but in NO stance cell")
used = [r for r in arows if r["scoring_disposition"] == "used"]
b_any = b_none = b_mixed = b_allst = 0
diluted_weight = 0.0; total_weight = 0.0
cat_hits = collections.Counter(); nonstance_hits = collections.Counter()
none_rows = []
for r in used:
    cats = list(r["effective_categories"])
    if not cats:
        continue
    st = [c for c in cats if c in STANCE_ELIGIBLE]
    ns = [c for c in cats if c in NON_STANCE]
    other = [c for c in cats if c not in STANCE_ELIGIBLE and c not in NON_STANCE]
    for c in st: cat_hits[c] += 1
    for c in ns: nonstance_hits[c] += 1
    total_weight += 1.0
    diluted_weight += len(st) / float(len(cats))
    if st and not ns: b_allst += 1
    if st and ns:     b_mixed += 1
    if st:            b_any += 1
    else:
        b_none += 1
        none_rows.append(r)
    if other:
        print("    !! row routed to a category that is neither stance-eligible nor declared-nonstance: %s" % other)
print("    used rows                                              : %d" % len(used))
print("    ... contributing to >=1 STANCE cell                    : %d" % b_any)
print("        of which routed ONLY to stance columns              : %d" % b_allst)
print("        of which ALSO split into a non-stance column        : %d" % b_mixed)
print("    ... contributing to NO stance cell (sheet-only)         : %d" % b_none)
print("    unaccounted                                            : %d" % (len(used) - b_any - b_none))
print("\n    per-item weight is split 1/len(_cats)  (blend.py:405  `for _c in _cats: _dyn[_c][_m]+=_sg*_pv*_dec*_cw/len(_cats)`)")
print("    sum of item-weight reaching stance columns: %.2f of %.2f  (%.1f%% ; %.2f item-equivalents"
      " are spent on non-stance columns)"
      % (diluted_weight, total_weight, 100.0 * diluted_weight / total_weight, total_weight - diluted_weight))
print("\n    non-stance destinations among used rows:")
for c, n in nonstance_hits.most_common():
    print("       %-34s %d used rows route here" % (c, n))
print("\n    sheet-only rows (no stance cell at all) by destination set:")
for k, n in collections.Counter(tuple(sorted(r["effective_categories"])) for r in none_rows).most_common():
    print("       %-60s %d" % (" + ".join(k), n))

print("\n    stance-column hit counts among used rows (item counts, before 1/n split):")
for c, n in cat_hits.most_common():
    print("       %-40s -> %-26s %d" % (c, RAW2ST[c], n))
missing = [c for c in STANCE_ELIGIBLE if c not in cat_hits]
print("    stance columns receiving ZERO press items: %s" % (missing or "none"))

# ---------------------------------------------------------------- (d) routing fidelity vs declared
print("\n(d) ROUTING FIDELITY: effective category vs the category the SOURCE ROW declared")
print("    RULE blend.py:358  _route=MR.press_routing_decision(api_target, title, _declared, fulltext)")
print("    RULE media_rules.py:139-144  target-specific hits WIN and DISCARD declared tags")
print("    RULE blend.py:360  _cats=[c for c in _route['categories'] if c in ORIG]  (ORIG = 20 sheet headers)")
basis = collections.Counter(r["routing_basis"] for r in arows)
print("    routing_basis over all %d rows: %s" % (len(arows), dict(basis)))
dd = [r for r in arows if r.get("discarded_declared")]
print("    rows where a DECLARED specific category was discarded: %d" % len(dd))
print("    ... of those with disposition 'used'                 : %d"
      % sum(1 for r in dd if r["scoring_disposition"] == "used"))
disc = collections.Counter(c for r in dd for c in r["discarded_declared"])
print("    most-discarded declared categories:")
for c, n in disc.most_common(8):
    print("       %-40s %d" % (c, n))
# mismatch = a used row whose effective set shares NOTHING with its declared-specific set
mm = []
for r in used:
    decl = [c for c in r.get("declared_categories", []) if c in STANCE_ELIGIBLE or c == COMPET]
    if not decl:
        continue
    if not (set(decl) & set(r["effective_categories"])):
        mm.append(r)
print("    used rows whose effective categories share NOTHING with their declared-specific set: %d"
      % len(mm))
print("       (that is the designed behaviour of the target/title precedence rule above, not a defect;"
      " counted because M3 asks for it)")
for r in mm[:6]:
    print("       %-22s declared=%s -> effective=%s  basis=%s"
          % (str(r.get("member_source"))[:22], r.get("declared_categories"), r["effective_categories"], r["routing_basis"]))

# ---------------------------------------------------------------- (e) 2-URL-form duplicate class
print("\n(e) DUPLICATE CLASS: one press release ingested under TWO URL FORMS")
print("    the (url,identity) turn key at press_stream.py:113 does NOT collapse these -- different path")
print("    RULE: no other de-duplication exists anywhere in the press channel")
by_url = {}
for r in arows:
    by_url[canonical_url(r.get("url"), keep_fragment=True)] = r
def ntitle(t):
    return F.normalized_text(t)
def pdate(s):
    for f in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try: return datetime.datetime.strptime((s or "").strip(), f).date().isoformat()
        except ValueError: pass
    return "(unparsed)"
url2date = {canonical_url(x.get("url"), keep_fragment=True): x.get("date") for x in rows}
grp = collections.defaultdict(list)
for r in arows:
    u = canonical_url(r.get("url"), keep_fragment=True)
    grp[(str(r.get("member_source")), ntitle(r.get("title")), pdate(url2date.get(u, "")))].append(r)
multi = {k: v for k, v in grp.items() if len(v) > 1}
print("    (member, normalised title, date) groups with 2+ rows: %d   surplus rows: %d"
      % (len(multi), sum(len(v) - 1 for v in multi.values())))
scoring = {k: [r for r in v if r["scoring_disposition"] == "used"] for k, v in multi.items()}
dbl = {k: v for k, v in scoring.items() if len(v) > 1}
print("    groups with MORE THAN ONE 'used' row -> the statement scores twice: %d" % len(dbl))
print("\n    each such group, with the STANCE CELL it double-counts into:")
for (mem, _t, d), v in sorted(dbl.items()):
    cells = collections.Counter()
    for r in v:
        for c in r["effective_categories"]:
            cells[c] += 1
    same = {c: n for c, n in cells.items() if n > 1}
    print("       %-20s date=%-12s rows_used=%d" % (mem[:20], d, len(v)))
    for c, n in sorted(cells.items()):
        tag = ("SAME CELL x%d -> stance col '%s'" % (n, RAW2ST[c])) if (n > 1 and c in STANCE_ELIGIBLE) else \
              ("SAME COLUMN x%d -> NO stance column" % n) if n > 1 else "x1"
        print("          %-40s %s" % (c, tag))
    if not same:
        print("          (the two rows route to DIFFERENT categories: no single cell is doubled)")
json.dump({"ingest": per_src, "tone_rows": len(rows), "dispositions": dict(disp),
           "used": len(used), "used_reaching_stance_cell": b_any, "used_sheet_only": b_none,
           "used_mixed": b_mixed, "stance_weight": diluted_weight, "total_weight": total_weight,
           "nonstance_hits": dict(nonstance_hits), "cat_hits": dict(cat_hits),
           "urlform_groups": len(multi), "urlform_double_scoring": len(dbl),
           "urlform_double_detail": {("%s|%s" % (k[0], k[2])): sorted(
               c for r in v for c in r["effective_categories"]) for k, v in dbl.items()}},
          open(os.path.join(HERE, "f2_press_channel.json"), "w", encoding="utf-8"), indent=1, sort_keys=True)
print("\nDONE F3 r2")
