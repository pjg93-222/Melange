# -*- coding: utf-8 -*-
# F3 r3: SOCIAL + the three OWN-SOURCE channels (speech / hearing / interview), closed against the
# STANCE path.  For each: items in -> per-rule exclusion buckets -> items reaching >=1 STANCE cell
# vs items that only reach a non-stance column ('CU-Bank Competitive Dynamics' / 'General Credit
# Union').  Plus the per-category social SHRINK factor and the same-cell duplicate classes.
# READ-ONLY.  Nothing under LIVE\fec is imported; hash-verified COPIES of the two pure helper
# modules (media_rules.py, member_identity.py) are used, exactly as lane A did.
import os, sys, io, csv, json, collections, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LIB = r"C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\F3\lib"
sys.path.insert(0, LIB)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import f_lib as F
import media_rules as MR                       # hash-verified copy
from member_identity import Resolver           # hash-verified copy
import pandas as pd

LIVE = F.LIVE
STANCE_ELIGIBLE = set(MR.RAW_TO_STANCE)
NON_STANCE = {MR.COMPETITIVE, MR.GENERAL}
SIGN = {"support": 1.0, "oppose": -1.0, "neutral": 0.0}      # blend.py:54
TODAY = datetime.date.today()

print("=" * 108)
print("F3 r3  SOCIAL + OWN-SOURCE channels -> stance cells    run %s"
      % datetime.datetime.now().isoformat(timespec="seconds"))
print("=" * 108)
print("hash-verified helper copies: media_rules %s / member_identity %s"
      % (F.sha256_file(os.path.join(LIB, "media_rules.py"))[:16],
         F.sha256_file(os.path.join(LIB, "member_identity.py"))[:16]))
print("NOTE  build_media_blend.py uses datetime.date.today() for decay (blend.py:48); this replay")
print("      runs on %s.  Decay affects MAGNITUDE only, never which bucket a row falls in." % TODAY)

roster = json.load(io.open(os.path.join(LIVE, "data", "engine", "congestion.json"), encoding="utf-8"))
resolver = Resolver([x["member"] for x in roster], {x["member"]: x.get("bioguide") for x in roster})
print("roster: %d members" % len(roster))

def split_report(name, cat_counter, item_rows):
    """Report how a channel's scored items divide between stance and non-stance columns."""
    any_st = none_st = mixed = 0
    w_st = w_tot = 0.0
    dest = collections.Counter()
    for cats in item_rows:
        st = [c for c in cats if c in STANCE_ELIGIBLE]
        ns = [c for c in cats if c in NON_STANCE]
        unk = [c for c in cats if c not in STANCE_ELIGIBLE and c not in NON_STANCE]
        for c in ns: dest[c] += 1
        for c in unk: dest["!!UNKNOWN:" + str(c)] += 1
        w_tot += 1.0
        w_st += len(st) / float(len(cats)) if cats else 0.0
        if st:
            any_st += 1
            if ns or unk: mixed += 1
        else:
            none_st += 1
    print("    items scored by the channel                        : %d" % len(item_rows))
    print("    ... reaching >=1 STANCE cell                        : %d" % any_st)
    print("        of which also split into a non-stance column    : %d" % mixed)
    print("    ... reaching NO stance cell (sheet-only)            : %d" % none_st)
    print("    unaccounted                                        : %d" % (len(item_rows) - any_st - none_st))
    print("    item-weight reaching stance columns (1/n split)     : %.2f of %.2f = %.1f%%"
          % (w_st, w_tot, 100.0 * w_st / w_tot if w_tot else 0.0))
    print("    non-stance destinations: %s" % (dict(dest) or "none"))
    return {"scored": len(item_rows), "reach_stance": any_st, "sheet_only": none_st,
            "mixed": mixed, "weight_stance": w_st, "weight_total": w_tot, "dest": dict(dest)}

OUT = {}

# =====================================================================  SOCIAL
print("\n" + "-" * 108)
print("SOCIAL  -- LIVE fec/stance/build_media_blend.py:63-125")
print("-" * 108)
corp = pd.read_excel(os.path.join(LIVE, "Social Master.xlsx"), sheet_name="Corpus", dtype=str)
n_all = len(corp)
print("    RULE blend.py:64  corp=corp[(corp['stance'].fillna('')!='')&(corp['verified_handle'].astype(str)=='1')]")
corp = corp[(corp["stance"].fillna("") != "") & (corp["verified_handle"].astype(str) == "1")]
print("    Corpus rows %d -> after the verified/stance filter: %d  (dropped %d)"
      % (n_all, len(corp), n_all - len(corp)))

# STACK: blend.py:71-90, majority-vote collapse
STACK = {}
_sf = os.path.join(LIVE, "data", "stance", "tweet_stance_final.csv")
_TIERW = {"unanimous": 1.0, "majority": 0.7, "review": 0.35}     # blend.py:89
if os.path.exists(_sf):
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
print("    stance-stack keys loaded (blend.py:79-88 majority collapse): %d" % len(STACK))

b = collections.Counter(); zero_lab = collections.Counter()
soc = collections.defaultdict(lambda: collections.defaultdict(float))
scored_cats = []; scored_events = []
_seen = set(); ndupe = 0
for _, r in corp.iterrows():
    _st = r["stance"]; _io_ = None
    _s = STACK.get((r["member"], MR.normalized_text(r["text"]))) if STACK else None
    if _s:
        _st = _s["stack_stance"]; _io_ = _TIERW.get(_s["tier"], 0.5); b["stack_override"] += 1
    sg = SIGN.get(_st, 0.0)
    if sg == 0.0:
        b["A zero-sign (blend.py:102 `if sg==0.0: continue`)"] += 1; zero_lab[_st] += 1; continue
    _m = resolver.resolve(r["member"])
    if not _m:
        b["B unresolved identity (blend.py:104 `if not _member: nunknown+=1; continue`)"] += 1; continue
    _event = (_m, MR.normalized_text(r["text"]))
    if _event in _seen: ndupe += 1
    _seen.add(_event)
    if not _event[1]:
        b["C link-only, empty normalised text (blend.py:111 `elif not _event[1]: nlinkonly+=1; continue`)"] += 1; continue
    try:
        age = (TODAY - datetime.date.fromisoformat(str(r["date"])[:10])).days / 365.25
    except Exception:
        b["D unparseable date (blend.py:112-113 `except Exception: continue`)"] += 1; continue
    inten = _io_ if _io_ is not None else 0.5
    if _io_ is None:
        try: inten = max(0.25, min(1.5, float(r["stance_margin"])))
        except (TypeError, ValueError): inten = 0.5
    if str(r.get("is_rt", "")).strip().lower() in ("1", "true", "yes"):
        inten *= 0.5; b["(retweets down-weighted RT_W=0.5, blend.py:119)"] += 1
    decay = 0.5 ** (max(0.0, age) / 0.5)
    hits = MR.route_raw_categories(r["text"] or "")
    if not hits:
        b["E no routable category (blend.py:122 `if not hits: continue`)"] += 1; continue
    b["Z SCORED"] += 1
    scored_cats.append(hits); scored_events.append((_m, _event[1], tuple(sorted(hits))))
    for c in hits:
        soc[_m][c] += sg * inten * decay / len(hits)

print("\n    per-row disposition of the %d filtered rows:" % len(corp))
for k in sorted(b):
    if k.startswith("("): continue
    print("       %-78s %6d" % (k, b[k]))
print("       %-78s %6s" % ("zero-sign label breakdown", dict(zero_lab)))
tot_b = sum(v for k, v in b.items() if not k.startswith("(") and k != "stack_override")
print("    CLOSES? %d filtered rows == %d bucketed -> %s" % (len(corp), tot_b, len(corp) == tot_b))
print("    exact cross-post duplicates seen (ndupe, RETAINED at CROSSPOST_DEDUP=0, blend.py:47/107): %d" % ndupe)
print("\n    stance reach:")
OUT["social"] = split_report("social", None, scored_cats)
OUT["social"]["ndupe"] = ndupe
OUT["social"]["buckets"] = {k: v for k, v in b.items()}

# ---- SHRINK: the per-category social weight, blend.py:449-450 / 466
print("\n    RULE blend.py:449-450  nz=#members with nonzero social in the category;"
      " f=min(1.0,nz/15.0)")
print("    RULE blend.py:466      nv=(1.0-0.5*f)*press_side + 0.5*f*social_side")
print("    %-40s %-6s %-8s %s" % ("raw category", "nz", "f", "social share of the cell"))
shrink = {}
for c in list(MR.RAW_TO_STANCE) + [MR.COMPETITIVE, MR.GENERAL]:
    nz = sum(1 for m in soc if abs(soc[m].get(c, 0.0)) > 1e-12)
    f = min(1.0, nz / 15.0)
    shrink[c] = {"nz": nz, "f": f, "social_share": 0.5 * f}
    flag = "  <- THIN (social discounted)" if f < 1.0 else ""
    print("    %-40s %-6d %-8.4f %.4f%s" % (c, nz, f, 0.5 * f, flag))
OUT["social"]["shrink"] = shrink

# ---- same-cell duplicate classes
print("\n    DUPLICATES reaching the SAME (member, stance category) cell:")
twin = collections.Counter()
for m, txt, cats in scored_events:
    for c in cats:
        if c in STANCE_ELIGIBLE:
            twin[(m, MR.RAW_TO_STANCE[c], txt)] += 1
rep = {k: v for k, v in twin.items() if v > 1}
print("       (member, stance-category, normalised text) keys scoring >1x: %d   surplus contributions: %d"
      % (len(rep), sum(v - 1 for v in rep.values())))
print("       RULE blend.py:47  DEDUP=os.environ.get('CROSSPOST_DEDUP','0')=='1'  -> default 0: the")
print("            duplicate is COUNTED, not dropped (ratified D-034 / Q11)")
print("       top repeats:")
for k, v in sorted(rep.items(), key=lambda kv: -kv[1])[:8]:
    print("          %-22s %-26s x%d  %s" % (k[0][:22], k[1], v, k[2][:44]))
OUT["social"]["same_cell_repeat_keys"] = len(rep)
OUT["social"]["same_cell_surplus"] = sum(v - 1 for v in rep.values())

# =====================================================================  OWN-SOURCE
def own_source(name, path, deps, tier_fn, tier_desc, weight, lines):
    print("\n" + "-" * 108)
    print("%s  -- LIVE fec/stance/build_media_blend.py:%s   own-source weight %.2f" % (name, lines, weight))
    print("-" * 108)
    stl = [os.path.basename(d) for d in deps if os.path.exists(d) and os.path.getmtime(d) > os.path.getmtime(path)]
    print("    RULE blend.py:135-142 _cu_stale(): channel SKIPPED if stance_final is OLDER than its inputs")
    print("    stale inputs newer than %s: %s -> channel %s"
          % (os.path.basename(path), stl or "none", "SKIPPED" if stl else "ACTIVE"))
    rows = list(csv.DictReader(io.open(path, encoding="utf-8-sig", newline="")))
    print("    rows in file: %d" % len(rows))
    bb = collections.Counter(); scored = []
    if name == "HEARING":
        elig = [r for r in rows if tier_fn(r.get("tier")) > 0.0]
        bb["A0 non-gold excluded (blend.py:197-198 `_eligible=[... hearing_tier_weight>0]`)"] = len(rows) - len(elig)
    else:
        elig = rows
    ev = collections.Counter((x.get("member"), (x.get("date") or "")[:10]) for x in elig)
    for r in elig:
        if SIGN.get((r.get("stance") or "").strip().lower(), 0.0) == 0.0:
            bb["A zero-sign neutral/unrelated (`if _sg==0.0: continue`)"] += 1; continue
        if not resolver.resolve(r.get("member"), r.get("bioguide")):
            bb["B unresolved identity (`if not _m: continue`)"] += 1; continue
        try:
            datetime.date.fromisoformat((r.get("date") or "")[:10])
        except Exception:
            bb["C unparseable date (`except Exception: continue`)"] += 1; continue
        if tier_fn(r.get("tier")) == 0.0:
            bb["D tier weight 0, fail closed (`if _inten==0.0: continue`)"] += 1; continue
        cats = [c.strip() for c in (r.get("categories") or "").split(";") if c.strip()]
        if not cats:
            bb["E no categories column (`if not _cats: continue`)"] += 1; continue
        bb["Z SCORED"] += 1
        scored.append((resolver.resolve(r.get("member"), r.get("bioguide")),
                       (r.get("date") or "")[:10], tuple(sorted(cats)),
                       max(1, ev[(r.get("member"), (r.get("date") or "")[:10])])))
    print("    tier policy: %s" % tier_desc)
    print("    per-row disposition:")
    for k in sorted(bb):
        print("       %-74s %6d" % (k, bb[k]))
    print("    CLOSES? %d rows == %d bucketed -> %s" % (len(rows), sum(bb.values()), len(rows) == sum(bb.values())))
    print("    RULE blend.py per-event normalisation: each row weighted 1/n over (member,date) so one"
          " EVENT contributes one unit")
    print("\n    stance reach:")
    res = split_report(name, None, [s[2] for s in scored])
    res["buckets"] = dict(bb)
    # unknown category tokens = a mechanical routing failure (lookup is by RAW header name)
    toks = collections.Counter(c for s in scored for c in s[2])
    bad = {c: n for c, n in toks.items() if c not in STANCE_ELIGIBLE and c not in NON_STANCE}
    print("    category tokens NOT a Raw-sheet header (would silently score nothing at blend.py:452-457"
          " lookup): %s" % (bad or "none"))
    res["unknown_tokens"] = bad
    # same-cell repeats within a channel
    rr = collections.Counter()
    for m, d, cats, _n in scored:
        for c in cats:
            if c in STANCE_ELIGIBLE:
                rr[(m, MR.RAW_TO_STANCE[c], d)] += 1
    reps = {k: v for k, v in rr.items() if v > 1}
    print("    (member, stance-category, date) keys with >1 scored row: %d  surplus: %d"
          " -- collapsed to one unit by the 1/n event divisor" % (len(reps), sum(v - 1 for v in reps.values())))
    res["same_cell_keys"] = len(reps); res["same_cell_surplus"] = sum(v - 1 for v in reps.values())
    return res

def own_tier(t):   # media_rules.py:90-97
    return {"gold": 1.0, "unanimous": 0.9, "majority": 0.6, "review": 0.35}.get(str(t or "").strip().lower(), 0.0)
def hear_tier(t):  # media_rules.py:81-87
    return 1.0 if str(t or "").strip().lower() == "gold" else 0.0

OUT["speech"] = own_source("SPEECH", os.path.join(LIVE, "speech_stance_final.csv"),
    [os.path.join(LIVE, "speeches_cu.csv"), os.path.join(LIVE, "data", "stance", "speech_gold_queue.csv")],
    own_tier, "gold 1.0 / unanimous 0.9 / majority 0.6 / review 0.35 (media_rules.py:90-97)", 1.0, "145-174")
OUT["hearing"] = own_source("HEARING", os.path.join(LIVE, "data", "stance", "hearing_stance_final.csv"),
    [os.path.join(LIVE, "data", "stance", "hearings_cu.csv"), os.path.join(LIVE, "data", "stance", "hearing_gold_queue.csv")],
    hear_tier, "GOLD ONLY; every other tier = 0.0 (media_rules.py:81-87)", 0.85, "188-219")
OUT["interview"] = own_source("INTERVIEW", os.path.join(LIVE, "data", "stance", "interview_stance_final.csv"),
    [os.path.join(LIVE, "data", "stance", "interviews_cu.csv"), os.path.join(LIVE, "data", "stance", "interview_gold_queue.csv")],
    own_tier, "gold 1.0 / unanimous 0.9 / majority 0.6 / review 0.35 (media_rules.py:90-97)", 1.0, "231-259")

print("\n" + "-" * 108)
print("BLUESKY  -- LIVE fec/stance/build_media_blend.py:262-278")
print("-" * 108)
print("    CHANNEL DELIBERATELY NOT WIRED.  blend.py:274  blc=... # intentionally EMPTY -- never injected")
print("    blend.py:272  BLUESKY_ON=os.environ.get('CU_BLUESKY_CHANNEL','0')=='1'  -> default OFF")
print("    even at 1, blend.py:276-278 logs a refusal and adds nothing.  Items reaching a stance cell"
      " from this channel: 0")
print("    Bluesky posts DO reach stance via the SOCIAL corpus instead (76 Corpus rows, platform='bluesky')")

# reconcile against the producer's own ledger
META = json.load(open(os.path.join(LIVE, "data", "stance", "press_component_meta.json"), encoding="utf-8"))
osc = META["own_source_channels"]
print("\n" + "=" * 108)
print("RECONCILIATION vs the producer's own ledger (press_component_meta.json 'own_source_channels')")
print("=" * 108)
print("    %-12s %-16s %-16s %s" % ("channel", "meta signed rows", "this replay", "match"))
for k, mk in (("speech", "signed_rows"), ("hearing", "signed_gold_rows"), ("interview", "signed_rows")):
    mv = osc[k][mk]; rv = OUT[k]["scored"]
    print("    %-12s %-16d %-16d %s" % (k, mv, rv, "YES" if mv == rv else "NO  <-- DIVERGENCE"))
print("    %-12s %-16s %-16s %s" % ("hearing non-gold excluded", osc["hearing"]["non_gold_rows_excluded"],
      OUT["hearing"]["buckets"].get("A0 non-gold excluded (blend.py:197-198 `_eligible=[... hearing_tier_weight>0]`)"),
      "YES" if osc["hearing"]["non_gold_rows_excluded"] ==
      OUT["hearing"]["buckets"].get("A0 non-gold excluded (blend.py:197-198 `_eligible=[... hearing_tier_weight>0]`)") else "NO"))
print("    SOCIAL: the producer writes NO on-disk ledger for the social channel -- press_component_meta")
print("            records press + the three own-source channels only.  Social counts are therefore")
print("            reproduced, not reconciled; lane A r4 independently got the same closure.")

json.dump(OUT, open(os.path.join(HERE, "f3_social_and_ownsource.json"), "w", encoding="utf-8"),
          indent=1, sort_keys=True, default=str)
print("\nDONE F3 r3")
