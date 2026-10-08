# -*- coding: utf-8 -*-
# F3 r5: M4 duplicate classes at the STANCE CELL level (same member, same stance category),
#        split into cross-platform twins / same-platform repeats / press 2-URL-form / cross-channel;
#        plus the all-channel total of media routed to columns that have no stance cell.
# READ-ONLY.  Nothing under LIVE\fec is imported (hash-verified copies only).
import os, sys, io, csv, json, collections, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LIB = r"C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\F3\lib"
sys.path.insert(0, LIB)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import f_lib as F
import media_rules as MR
from member_identity import Resolver
import pandas as pd

LIVE = F.LIVE
STANCE_ELIGIBLE = set(MR.RAW_TO_STANCE)
NON_STANCE = {MR.COMPETITIVE, MR.GENERAL}
SIGN = {"support": 1.0, "oppose": -1.0, "neutral": 0.0}
TODAY = datetime.date.today()

print("=" * 108)
print("F3 r5  DUPLICATE CLASSES at the stance cell + all-channel non-stance routing   run %s"
      % datetime.datetime.now().isoformat(timespec="seconds"))
print("=" * 108)

roster = json.load(io.open(os.path.join(LIVE, "data", "engine", "congestion.json"), encoding="utf-8"))
resolver = Resolver([x["member"] for x in roster], {x["member"]: x.get("bioguide") for x in roster})

# ---------------------------------------------------------------- social, with platform retained
corp = pd.read_excel(os.path.join(LIVE, "Social Master.xlsx"), sheet_name="Corpus", dtype=str)
corp = corp[(corp["stance"].fillna("") != "") & (corp["verified_handle"].astype(str) == "1")]
STACK = {}
_sf = os.path.join(LIVE, "data", "stance", "tweet_stance_final.csv")
_grp = collections.defaultdict(list)
for _r in csv.DictReader(io.open(_sf, encoding="utf-8-sig", newline="")):
    _grp[(_r["member"], MR.normalized_text(_r["text"]))].append(_r)
_TR = {"unanimous": 3, "majority": 2, "review": 1}
for _k, _rows in _grp.items():
    if len(_rows) == 1:
        STACK[_k] = _rows[0]; continue
    _top = collections.Counter(_x["stack_stance"] for _x in _rows).most_common()
    _lab = _top[0][0] if (len(_top) == 1 or _top[0][1] > _top[1][1]) else "neutral"
    _c = [_x for _x in _rows if _x["stack_stance"] == _lab] or _rows
    STACK[_k] = max(_c, key=lambda _x: _TR.get(_x.get("tier", ""), 0))

scored = []      # (member, normtext, platform, date, cats)
for _, r in corp.iterrows():
    _st = r["stance"]
    _s = STACK.get((r["member"], MR.normalized_text(r["text"])))
    if _s: _st = _s["stack_stance"]
    if SIGN.get(_st, 0.0) == 0.0: continue
    _m = resolver.resolve(r["member"])
    if not _m: continue
    nt = MR.normalized_text(r["text"])
    if not nt: continue
    try: datetime.date.fromisoformat(str(r["date"])[:10])
    except Exception: continue
    hits = MR.route_raw_categories(r["text"] or "")
    if not hits: continue
    scored.append((_m, nt, str(r.get("platform") or ""), str(r["date"])[:10], tuple(sorted(hits))))
print("\nsocial scored rows replayed: %d" % len(scored))

print("\n" + "-" * 108)
print("M4.1  SOCIAL duplicates landing in the SAME (member, stance category) cell")
print("-" * 108)
print("    key = (member, stance category, normalised text)   -- normalised_text is media_rules.py:76-78")
print("    RULE blend.py:47  CROSSPOST_DEDUP default '0'  -> the duplicate is COUNTED, not dropped")
print("         (ratified decision D-034 / ruling Q11)")
cell = collections.defaultdict(list)
for m, nt, plat, d, cats in scored:
    for c in cats:
        if c in STANCE_ELIGIBLE:
            cell[(m, MR.RAW_TO_STANCE[c], nt)].append((plat, d))
rep = {k: v for k, v in cell.items() if len(v) > 1}
xplat = {k: v for k, v in rep.items() if len({p for p, _ in v}) > 1}
splat = {k: v for k, v in rep.items() if len({p for p, _ in v}) == 1}
print("    cells receiving the same statement >1x : %d   surplus contributions: %d"
      % (len(rep), sum(len(v) - 1 for v in rep.values())))
print("      CLASS A  cross-platform twins (>=2 distinct platforms) : %d keys / %d surplus"
      % (len(xplat), sum(len(v) - 1 for v in xplat.values())))
print("      CLASS B  same-platform repeats (one platform)          : %d keys / %d surplus"
      % (len(splat), sum(len(v) - 1 for v in splat.values())))
print("      check: %d + %d == %d -> %s" % (len(xplat), len(splat), len(rep), len(xplat) + len(splat) == len(rep)))
pc = collections.Counter(tuple(sorted({p for p, _ in v})) for k, v in rep.items())
print("\n    platform signature of the repeated-cell keys:")
for k, n in pc.most_common():
    print("       %-28s %d" % (" + ".join(k), n))
print("\n    CLASS B same-platform repeats, split by whether the dates differ:")
sd = sum(1 for k, v in splat.items() if len({d for _, d in v}) == 1)
print("       same platform AND same date (an exact re-ingest of one post): %d keys" % sd)
print("       same platform, DIFFERENT dates (a genuine repeat statement)  : %d keys" % (len(splat) - sd))
print("\n    top repeated cells:")
for k, v in sorted(rep.items(), key=lambda kv: -len(kv[1]))[:10]:
    print("       %-22s %-26s x%d  platforms=%s dates=%s"
          % (k[0][:22], k[1], len(v), sorted({p for p, _ in v}), sorted({d for _, d in v})[:3]))

# ---------------------------------------------------------------- press 2-URL-form (from r2)
print("\n" + "-" * 108)
print("M4.2  PRESS: one release ingested under TWO URL FORMS  (carried from receipt f2)")
print("-" * 108)
p2 = json.load(open(os.path.join(HERE, "f2_press_channel.json"), encoding="utf-8"))
print("    (member, normalised title, date) groups with 2+ rows : %d" % p2["urlform_groups"])
print("    groups where >1 row has disposition 'used'           : %d" % p2["urlform_double_scoring"])
st_dbl = {k: v for k, v in p2["urlform_double_detail"].items()
          if any(c in STANCE_ELIGIBLE for c in v) and len(v) > len(set(v)) }
ns_dbl = {k: v for k, v in p2["urlform_double_detail"].items() if k not in st_dbl}
print("    of those, doubling into an actual STANCE cell        : %d" % len(st_dbl))
for k, v in st_dbl.items():
    print("       %-40s categories=%s" % (k, v))
print("    of those, doubling only into a NON-stance column     : %d" % len(ns_dbl))
for k, v in ns_dbl.items():
    print("       %-40s categories=%s" % (k, sorted(set(v))))

# ---------------------------------------------------------------- cross-channel press vs social
print("\n" + "-" * 108)
print("M4.3  CROSS-CHANNEL: the same statement on the PRESS side and the SOCIAL side")
print("-" * 108)
print("    press and social are p80-scaled separately then mixed 50/50 (blend.py:466), so such a")
print("    pair contributes on BOTH sides of the same cell.  No rule anywhere looks for it.")
AUD = json.load(open(os.path.join(LIVE, "data", "stance", "press_domain_routing_audit.json"), encoding="utf-8"))
soc_by_member = collections.defaultdict(set)
for m, nt, plat, d, cats in scored:
    soc_by_member[m].add(nt)
hits = []
for r in AUD["rows"]:
    if r["scoring_disposition"] != "used":
        continue
    m = resolver.resolve(r.get("member_source"))
    if not m:
        continue
    nt = MR.normalized_text(r.get("title"))
    if nt and nt in soc_by_member.get(m, ()):
        cells = [MR.RAW_TO_STANCE[c] for c in r["effective_categories"] if c in STANCE_ELIGIBLE]
        hits.append((m, r.get("title"), cells, r["effective_categories"]))
print("    used press rows whose normalised TITLE equals one of the same member's social texts: %d" % len(hits))
for m, t, cells, eff in hits:
    print("       %-22s stance cells=%s  effective=%s" % (m[:22], cells or "(none)", eff))
    print("          title: %s" % str(t)[:88])

# ---------------------------------------------------------------- own-source repeats
print("\n" + "-" * 108)
print("M4.4  OWN-SOURCE channels: repeats inside one channel")
print("-" * 108)
print("    RULE blend.py:172-173 / 215-216 / 257-258  _evn=max(1,_ev[(member,date)]);"
      " contribution /= _evn")
print("    -> several passages from ONE event are normalised to ONE unit, so passage-level repeats")
print("       do NOT multiply a cell.  Counts from receipt f3:")
f3 = json.load(open(os.path.join(HERE, "f3_social_and_ownsource.json"), encoding="utf-8"))
for ch in ("speech", "hearing", "interview"):
    print("       %-10s (member,stance-cat,date) keys with >1 scored row: %-4s surplus %-4s"
          " -- absorbed by the 1/n event divisor"
          % (ch, f3[ch]["same_cell_keys"], f3[ch]["same_cell_surplus"]))
print("    CAVEAT the divisor is keyed on (member, date) over the WHOLE channel, not per category:")
print("       a member with passages in 3 categories on one date has each contribution divided by the")
print("       TOTAL passage count for that date, so a multi-category event delivers LESS than one unit")
print("       per category.  That is a magnitude effect, not a duplicate.")

# ---------------------------------------------------------------- all-channel non-stance total
print("\n" + "=" * 108)
print("ALL-CHANNEL TOTAL: media items routed to a column with NO stance cell")
print("=" * 108)
print("    %-12s %-9s %-14s %-14s %-12s %s"
      % ("channel", "scored", "reach stance", "sheet-only", "CU-Bank", "General CU"))
tot = collections.Counter()
rows = [("press", p2["used"], p2["used_reaching_stance_cell"], p2["used_sheet_only"],
         p2["nonstance_hits"].get(MR.COMPETITIVE, 0), p2["nonstance_hits"].get(MR.GENERAL, 0))]
for ch in ("social", "speech", "hearing", "interview"):
    d = f3[ch]
    rows.append((ch, d["scored"], d["reach_stance"], d["sheet_only"],
                 d["dest"].get(MR.COMPETITIVE, 0), d["dest"].get(MR.GENERAL, 0)))
for r in rows:
    print("    %-12s %-9d %-14d %-14d %-12d %d" % r)
    for i, k in enumerate(("scored", "reach", "sheet_only", "compet", "general")):
        tot[k] += r[i + 1]
print("    %-12s %-9d %-14d %-14d %-12d %d"
      % ("TOTAL", tot["scored"], tot["reach"], tot["sheet_only"], tot["compet"], tot["general"]))
print("    bluesky      0         0              0              0            0   (channel never injected)")
print("\n    'CU-Bank Competitive Dynamics' (raw col 18): %d scored items route here."
      % tot["compet"])
print("      press_matrix NORMALISES col 18 (moneyball_core.py:94 COLS=range(5,24)) and the row-535")
print("      press-pillar weight is 0.03, so it DOES reach the ranking engine -- but it has no entry")
print("      in per_category_stance.py:28-31 cats[] and no entry in media_rules.py RAW_TO_STANCE,")
print("      so it reaches NO stance cell.  156 members carry a nonzero value in it.")
print("\n    'General Credit Union' (raw col 24): %d scored items route here." % tot["general"])
print("      moneyball_core.py:98 normalises COLS only, so col 24 is never normalised; :99 routes it")
print("      to general_exclusion_ledger and per_category_stance.py:156 publishes that ledger under")
print("      media.general_credit_union_exclusions (270 members).  Row 535 carries NO weight for it,")
print("      so it reaches neither the stance path NOR the press pillar.  Nothing is hidden: the")
print("      ledger is in the artifact with applied_to_policy_domains=False.")

json.dump({"social_repeat_keys": len(rep), "social_surplus": sum(len(v) - 1 for v in rep.values()),
           "cross_platform_twin_keys": len(xplat),
           "cross_platform_twin_surplus": sum(len(v) - 1 for v in xplat.values()),
           "same_platform_keys": len(splat),
           "same_platform_surplus": sum(len(v) - 1 for v in splat.values()),
           "same_platform_same_date_keys": sd,
           "press_urlform_double_into_stance_cell": len(st_dbl),
           "press_urlform_double_nonstance_only": len(ns_dbl),
           "cross_channel_press_social": len(hits),
           "all_channel": {r[0]: {"scored": r[1], "reach": r[2], "sheet_only": r[3],
                                  "compet": r[4], "general": r[5]} for r in rows},
           "totals": dict(tot)},
          open(os.path.join(HERE, "f5_duplicate_classes.json"), "w", encoding="utf-8"),
          indent=1, sort_keys=True, default=str)
print("\nDONE F3 r5")
