# -*- coding: utf-8 -*-
"""FIX A5 step 1 -- enumerate the press rows that are one release under two URL forms,
and classify HOW the two forms differ.  READ-ONLY against LIVE.

Nothing under LIVE\\fec is imported: press_stream.py is byte-identical in the worktree,
so the worktree copy is imported with MONEYBALL_ROOT/MONEYBALL_DRAFT pointed at LIVE.
"""
import collections
import io
import json
import os
import re
import sys
from urllib.parse import urlsplit, parse_qsl

LIVE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
DRAFT = r"C:\Users\pgoff\OneDrive\Desktop\Draft Systems"
WT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  os.pardir, os.pardir, os.pardir))
os.environ["MONEYBALL_ROOT"] = LIVE
os.environ["MONEYBALL_DRAFT"] = DRAFT
sys.path.insert(0, os.path.join(WT, "fec"))
import press_stream as PS                                    # noqa: E402  (no top-level I/O)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = {}


def ntitle(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def pdate(value):
    value = str(value or "").strip()
    for rx, order in ((r"^(\d{4})-(\d{2})-(\d{2})", (1, 2, 3)),
                      (r"^(\d{1,2})/(\d{1,2})/(\d{4})$", (3, 1, 2))):
        m = re.match(rx, value)
        if m:
            a, b, c = (m.group(i) for i in order)
            return "%s-%02d-%02d" % (a, int(b), int(c))
    return "(unparsed)"


def classify(urls):
    """Name every dimension on which a set of URL strings for one release differ."""
    parts = [urlsplit(u.strip()) for u in urls]
    classes = []
    if len({p.scheme.lower() for p in parts}) > 1:
        classes.append("scheme")
    hosts = {p.netloc.lower() for p in parts}
    if len({h[4:] if h.startswith("www.") else h for h in hosts}) > 1:
        classes.append("host")
    elif len(hosts) > 1:
        classes.append("www.")
    paths = [p.path for p in parts]
    if len({q.lower() for q in paths}) > 1 and len({q for q in paths}) > 1:
        stripped = {q.rstrip("/") for q in paths}
        if len(stripped) == 1:
            classes.append("trailing slash")
        elif len({q.rstrip("/").lower() for q in stripped}) == 1:
            classes.append("path case")
        else:
            classes.append("path alias")
    elif len({q for q in paths}) > 1:
        classes.append("path case")
    queries = [p.query for p in parts]
    if len(set(queries)) > 1:
        keys = [frozenset(k.lower() for k, _v in parse_qsl(q, keep_blank_values=True))
                for q in queries]
        if len(set(keys)) > 1:
            classes.append("query keys differ")
        else:
            classes.append("query values differ")
    frags = [p.fragment for p in parts]
    if len(set(frags)) > 1:
        classes.append("fragment")
    return classes or ["identical after strip"]


rows = PS.load_tone_rows()
print("=" * 108)
print("M1  PRESS: one release under two URL FORMS -- enumeration + difference classes")
print("=" * 108)
print("tone rows after load_tone_rows() (url,identity) dedup: %d" % len(rows))

groups = collections.defaultdict(list)
for row in rows:
    ident = (row.get("bioguide") or row.get("member") or "").strip().upper()
    groups[(ident, ntitle(row.get("title")), pdate(row.get("date")))].append(row)
multi = {k: v for k, v in groups.items() if len(v) > 1}
print("(member, normalised title, date) groups with 2+ surviving rows: %d   surplus rows: %d"
      % (len(multi), sum(len(v) - 1 for v in multi.values())))

FRAG_ONLY = re.compile(r"^[A-Z]\d{6}$")          # a bioguide-shaped fragment
ledger = []
for (ident, _t, date), members in sorted(multi.items()):
    urls = [(r.get("url") or "").strip() for r in members]
    classes = classify(urls)
    ledger.append({"identity": ident, "member": members[0].get("member"),
                   "date": date, "title": (members[0].get("title") or "")[:90],
                   "classes": classes, "urls": urls,
                   "canonical": [PS.canonical_url(u, keep_fragment=True) for u in urls]})

print("\n--- the groups, with their difference class ---")
for item in ledger:
    print("  %-22s %-12s  %s" % ((item["member"] or "")[:22], item["date"],
                                 " + ".join(item["classes"])))
    print("      title: %s" % item["title"])
    for url, canon in zip(item["urls"], item["canonical"]):
        print("      raw : %s" % url)
        print("      canon: %s" % canon)

print("\n--- difference-class census over the %d groups ---" % len(ledger))
census = collections.Counter(" + ".join(i["classes"]) for i in ledger)
for cls, n in census.most_common():
    print("  %-42s %d" % (cls, n))

# Does the group's own URL set expose a tracking/fragment-only difference?
print("\n--- per-group detail for the classes that matter ---")
for item in ledger:
    qs = [dict(parse_qsl(urlsplit(u).query, keep_blank_values=True)) for u in item["urls"]]
    fr = [urlsplit(u).fragment for u in item["urls"]]
    print("  %-22s %-12s queries=%s fragments=%s"
          % ((item["member"] or "")[:22], item["date"],
             json.dumps(qs, ensure_ascii=False), json.dumps(fr, ensure_ascii=False)))

OUT["tone_rows"] = len(rows)
OUT["groups"] = ledger
OUT["class_census"] = dict(census)
with io.open(os.path.join(HERE, "m1_url_form_classes.json"), "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, ensure_ascii=False)
print("\nDONE M1")
