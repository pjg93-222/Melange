# -*- coding: utf-8 -*-
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from paths import ROOT as MB_ROOT, DRAFT as MB_DRAFT
"""PRESS STANCE STACK — production scorer (user 2026-07-04: "wire in the most accurate stack",
zero new API spend). Mirrors tweet_stance_stack.py.
Instrument: meta-LogReg(C=1, untuned) over corpus-wide fields only —
  registry-compose (Fable target x cu_valence_registry) + Fable flat/hop/valence/conf + DEBATE +
  two TF-IDF readers (inp = target/speaker/headline, fulltext = title+body) trained on ALL 760
  user golds. Measured (pre-registered, GroupKFold dedup): 0.837 acc on the 760-gold frame /
  0.765 on the adversarial goldeval frame; DEBATE alone = 0.796/0.571 on the same frames.
Tiers (production trust levels, measured): unanimous(stack==fable==debate) 0.955 · 44%,
  majority(stack matches one) 0.776 · 44%, review 0.638 · 12%.
Output: press_stance_final.csv sidecar (url, member, stack_label, tier). build_media_blend.py
consumes it: sign from stack label (UNRELATED -> 0 — kills trade-digest mention noise), intensity
x tier weight, DEBATE fallback when a url is missing.
Usage: python press_stance_stack.py            (train on golds + score full corpus + write sidecar)"""
import csv, hashlib, io, json, os, re, sys, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
B = MB_ROOT
CL = ["support", "oppose", "neutral", "unrelated"]

fable = {}
for ln in open(B + r"\api_press_cache_fable.jsonl", encoding="utf-8"):
    try:
        d = json.loads(ln); fable[d["k"]] = d["out"]
    except Exception: pass
REG = json.load(open(B + r"\cu_valence_registry.json"))["entries"]
FT = {}
for _cp in (B + r"\press_text_cache.jsonl", B + r"\press_text_cache_priority.jsonl"):
    if not os.path.exists(_cp): continue
    for ln in open(_cp, encoding="utf-8"):
        try:
            d = json.loads(ln)
            u = (d.get("url") or "").strip().rstrip("/")
            if d.get("text"): FT[u] = d["text"]
        except Exception: pass

POLICY_KEYS = {e["key"] for e in REG if e.get("policy_force")}   # user-legislated axes bind the final label
def reg_lookup(target, text):
    blob = ((target or "") + " " + (text or "")).lower()
    for e in REG:
        if any(m in blob for m in e["match"]): return e["valence"]
    return None
def reg_key(target, text):
    blob = ((target or "") + " " + (text or "")).lower()
    for e in REG:
        if any(m in blob for m in e["match"]): return e["key"]
    return None
def compose(s, v):
    s = (s or "").lower()
    if s == "unrelated": return "unrelated"
    if s == "neutral" or v == 0: return "neutral"
    if s == "support": return "support" if v > 0 else "oppose"
    if s == "oppose": return "oppose" if v > 0 else "support"
    return "neutral"
def onehot(l, dom): return [1.0 if l == c else 0.0 for c in dom]
def vnum(v):
    try: return float(int(str(v).strip()))
    except (ValueError, TypeError): return 0.0
CONF = {"high": 2.0, "medium": 1.0, "low": 0.0}

def featurize(recs):
    """recs: [{url,title,body,debate}] -> (FBASE, inps, fts) with fields from the fable cache."""
    FB = []; inps = []; fts = []
    for r in recs:
        k = hashlib.md5((r["url_raw"]).strip().encode()).hexdigest()
        fb = fable.get(k, {})
        tgt = (fb.get("target") or "Credit Unions (direct)").strip()
        f_flat = (fb.get("cu_alignment") or "").strip().lower()
        f_hop = (fb.get("stance_toward_target") or "").strip().lower()
        v = reg_lookup(fb.get("target") or "", (r["title"] or "") + " " + (r["body"] or "")[:300])
        A = compose(f_hop, v) if (v is not None and f_hop) else f_flat
        hit = 1.0 if v is not None and f_hop else 0.0
        FB.append(onehot(A, CL) + onehot(f_flat, CL) + onehot(r["debate"], CL) + onehot(f_hop, CL) +
                  [vnum(fb.get("target_cu_valence", "")), CONF.get((fb.get("confidence") or "").strip().lower(), 1.0), hit])
        inps.append("target: %s. speaker: %s. %s" % (tgt, fb.get("attribution") or "member", (r["body"] or "")[:1500]))
        u = r["url_raw"].strip().rstrip("/")
        fts.append(((r["title"] or "") + ". " + (FT.get(u) or r["body"] or ""))[:6000])
    return np.array(FB), inps, fts

# ---- train on ALL golds ----
gold = [r for r in csv.DictReader(open(B + r"\cu_golden_labels.csv", encoding="utf-8-sig"))
        if (r.get("label") or "").strip().lower() in CL]
tone_rows = list(csv.DictReader(io.open(os.path.join(MB_DRAFT, "cu_press_stance_tone.csv"), encoding="utf-8-sig", newline="")))
tone = {(r.get("url") or "").strip().rstrip("/"): r for r in tone_rows}
grecs = [{"url_raw": (r.get("url") or ""), "title": r.get("title") or "",
          "body": (r.get("text") or "").strip() or (r.get("title") or ""),
          "debate": ((tone.get((r.get("url") or "").strip().rstrip("/")) or {}).get("stance") or "").strip().lower()}
         for r in gold]
y = np.array([(r.get("label") or "").strip().lower() for r in gold])
FB, inps, fts = featurize(grecs)
rd1 = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
                    LogisticRegression(C=4.0, max_iter=3000, class_weight="balanced")).fit(inps, y)
rd2 = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
                    LogisticRegression(C=4.0, max_iter=3000, class_weight="balanced")).fit(fts, y)
def pb(mdl, X):
    P = np.zeros((len(X), 4)); pr = mdl.predict_proba(X)
    for j, c in enumerate(list(mdl.classes_)):
        if c in CL: P[:, CL.index(c)] = pr[:, j]
    return P
X = np.hstack([FB, pb(rd1, inps), pb(rd2, fts)])
meta = LogisticRegression(C=1.0, max_iter=3000, class_weight="balanced").fit(X, y)
print("trained on %d golds (meta + 2 in-set readers)" % len(y))

# ---- score the full corpus ----
crecs = [{"url_raw": (r.get("url") or ""), "title": r.get("title") or "",
          "body": r.get("title") or "",   # corpus rows carry no body col; fulltext cache supplies it in fts
          "debate": (r.get("stance") or "").strip().lower()} for r in tone_rows if (r.get("url") or "").strip()]
FBc, inpc, ftc = featurize(crecs)
Xc = np.hstack([FBc, pb(rd1, inpc), pb(rd2, ftc)])
pred = meta.predict(Xc)
out = []
tiern = collections.Counter()
for i, r in enumerate([t for t in tone_rows if (t.get("url") or "").strip()]):
    k = hashlib.md5((r.get("url") or "").strip().encode()).hexdigest()
    f_flat = (fable.get(k, {}).get("cu_alignment") or "").strip().lower()
    deb = (r.get("stance") or "").strip().lower()
    s = pred[i]
    # POLICY-FORCE override (user-directed 2026-07-07): registry entries flagged policy_force BIND
    # the composed label; learned readers trained on superseded golds cannot outvote a legislated
    # axis. Currently: CFPB agency-existence axis + bare mentions -> neutral.
    if reg_key(fable.get(k, {}).get("target"), r.get("title")) in POLICY_KEYS and s in ("support", "oppose"):
        s = "neutral"
    tier = "unanimous" if (s == f_flat == deb) else ("majority" if (s == f_flat or s == deb) else "review")
    tiern[tier] += 1
    out.append({"url": r.get("url"), "member": r.get("member"), "date": r.get("date"),
                "title": r.get("title"), "stack_label": s, "tier": tier, "debate_stance": deb})
tmp = B + r"\press_stance_final.csv.tmp"
with io.open(tmp, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
    w.writeheader(); w.writerows(out)
os.replace(tmp, B + r"\press_stance_final.csv")
lab = collections.Counter(o["stack_label"] for o in out)
chg = sum(1 for o in out if o["stack_label"] != o["debate_stance"])
print("scored %d articles -> press_stance_final.csv" % len(out))
print("labels: %s | tiers: %s | changed vs DEBATE: %d (%.0f%%)" % (dict(lab), dict(tiern), chg, 100*chg/len(out)))
