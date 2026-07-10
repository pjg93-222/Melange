# -*- coding: utf-8 -*-
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from paths import ROOT as MB_ROOT
"""ROUND-5 SUCCESSOR-GATE WORK (big5_a_matrix_prereg.md, Addendum 1) — multi-basis stratum-power
diagnostic. SYNTHETIC ONLY, NO LOOK: no real trait x criterion pairing is ever computed;
coop_v2_candidate.json is read ONLY for its coverage mask (criterion VALUES never meet a
prediction), and behavioral criteria are never loaded at all. Question: can any text basis recover
the Addendum-1 planted true r=.40 signal on the actual MEM_A stratum (same constructor
NM.plant_set, same five pinned seeds, bars 1-4) where supervised Empath could not (median +0.132,
2/5)? Levers this tests = exactly the two the Addendum names: corpus growth (the interview corpus
3.8x'd on 07-09, AFTER the 07-07 emb cache) and richer text representation (open-vocab LSA /
sentence-transformer bases, rebuilt fresh to b5_emb_cache_r6.npz).
Selection-effect guard, pinned pre-run: bases are screened on the five PINNED Addendum seeds; any
basis reaching >=3/5 on bars 1-4 must CONFIRM >=3/5 on five FRESH seeds (below) never used for
selection. A confirmed pass licenses ONLY a successor-prereg PROPOSAL to Paul (new instrument =
new prereg + adversarial review, per the lock's instrument-of-record language); it changes no
status. Empath runs first as the baseline reproduction. No LLM calls. No audio."""
import json, re, sqlite3, collections, argparse
import numpy as np
_s.stdout.reconfigure(encoding='utf-8', errors='replace')
import b5_behavioral_instrument as BI      # import-safe (__main__-guarded): featurize/oof/exact_perm_p
import b5_n_matrix as NM                   # import-safe: rr/zz/plant_set (Addendum-1 orthogonalized constructor)
import moneyball_core as MC
B = MB_ROOT
EMB_NPZ = B + r'\b5_emb_cache_r6.npz'
EMB_META = B + r'\b5_emb_meta_r6.json'
PIN5 = [424242, 515151, 616161, 717171, 818181]    # the Addendum-1 diagnostic seeds (selection set)
FRESH5 = [131313, 272727, 393939, 515253, 676767]  # confirmation set — pinned here, never used for selection
GENRES = ('CREC', 'INTERVIEW', 'social')
CORE = NM.CORE
rr, zz = NM.rr, NM.zz

# ---------------------------------------------------------------- emb rebuild (current corpus)
RITUAL = re.compile(r'\b(i yield (back|to|the floor|myself)[^.]*|mr\.? (president|speaker)|madam (president|speaker)|'
 r'i ask unanimous consent[^.]*|the (gentleman|gentlewoman|gentlelady) from [a-z ]+|'
 r'i (rise|reserve the balance of my time)|pursuant to [^.]*|the clerk will [^.]*|'
 r'i suggest the absence of a quorum|the balance of my time)\b', re.I)

def build_emb_r6():
    """b5_emb_build.py logic verbatim (that file is import==execution, so replicated), OUT -> _r6
    files; the 07-07 cache is left untouched. Skips if the _r6 cache already exists."""
    if _o.path.exists(EMB_NPZ) and _o.path.exists(EMB_META):
        print('emb r6 cache present — reusing', flush=True); return
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import Normalizer
    b2n = MC.bio2name()
    con = sqlite3.connect(B + r'\social_media.db', timeout=30); con.execute('PRAGMA query_only=1')
    docs = collections.defaultdict(lambda: {'text': '', 'tok': 0})
    for g in ('CREC', 'INTERVIEW'):
        for m, txt in con.execute("select member, group_concat(text,' ') from speeches where source=? group by member", (g,)):
            t = RITUAL.sub(' ', txt or ''); docs[(m, g)]['text'] = t; docs[(m, g)]['tok'] = len(t.split())
    soc = collections.defaultdict(list)
    for bg, txt in con.execute("select bioguide, group_concat(text,' ') from posts where repost_of is null group by bioguide"):
        m = b2n.get(bg)
        if m: soc[m].append(txt or '')
    for m, ts in soc.items():
        t = ' '.join(ts); docs[(m, 'social')]['text'] = t; docs[(m, 'social')]['tok'] = len(t.split())
    con.close()
    pairs = [(m, g) for (m, g), d in docs.items() if d['tok'] >= 50]
    members = sorted({m for m, g in pairs})
    print('emb r6 build: %d members, %d member-genre docs' % (len(members), len(pairs)), flush=True)
    feats = {}
    toks = {(m, g): docs[(m, g)]['tok'] for (m, g) in pairs}
    corpus = [docs[(m, g)]['text'] for (m, g) in pairs]
    for K in (128, 256, 512):
        pipe = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=40000, sublinear_tf=True),
            TruncatedSVD(n_components=K, random_state=7),
            Normalizer(copy=False))
        X = pipe.fit_transform(corpus)
        feats['lsa%d' % K] = {pairs[i]: X[i] for i in range(len(pairs))}
        print('  lsa%d: %s' % (K, X.shape), flush=True)
    try:
        from sentence_transformers import SentenceTransformer
        st = SentenceTransformer('all-MiniLM-L6-v2')
        def chunks(text, w=256):
            ws = text.split()
            return [' '.join(ws[i:i + w]) for i in range(0, min(len(ws), 256 * 40), w)] or ['']
        stmean = {}
        for i, (m, g) in enumerate(pairs):
            cs = chunks(docs[(m, g)]['text'])
            emb = st.encode(cs, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
            stmean[(m, g)] = np.asarray(emb).mean(axis=0)
            if i % 100 == 0: print('  st encoding %d/%d' % (i, len(pairs)), flush=True)
        feats['st_mean'] = stmean
        from sklearn.linear_model import LinearRegression
        volctrl = {}
        for g in GENRES:
            gp = [(m, gg) for (m, gg) in pairs if gg == g]
            if len(gp) < 20:
                for k in gp: volctrl[k] = stmean[k]
                continue
            Xg = np.array([stmean[k] for k in gp]); lv = np.array([[np.log1p(toks[k])] for k in gp])
            res = Xg - LinearRegression().fit(lv, Xg).predict(lv)
            for j, k in enumerate(gp): volctrl[k] = res[j]
        feats['st_volctrl'] = volctrl
        print('  st bases built', flush=True)
    except Exception as e:
        print('  sentence-transformers unavailable (%s) — LSA bases only' % str(e)[:70], flush=True)
    bases = list(feats)
    np.savez_compressed(EMB_NPZ, **{'%s|%s|%s' % (b, m, g): feats[b][(m, g)]
                                    for b in bases for (m, g) in pairs if (m, g) in feats[b]})
    json.dump({'bases': bases, 'members': members,
               'pairs': ['%s|%s' % (m, g) for (m, g) in pairs],
               'toks': {'%s|%s' % (m, g): toks[(m, g)] for (m, g) in pairs}},
              open(EMB_META, 'w'))
    print('wrote %s (%s)' % (EMB_NPZ, ', '.join(bases)), flush=True)

def member_matrix(base, MEM):
    """b5_round4_eval composition verbatim: within-genre z, token-weighted cross-genre average.
    Returns (X rows aligned to the subset of MEM present, keep list)."""
    meta = json.load(open(EMB_META))
    npz = np.load(EMB_NPZ)
    TOK = {tuple(k.split('|')): v for k, v in meta['toks'].items()}
    pairs = [tuple(p.split('|')) for p in meta['pairs']]
    Z = {}
    for g in GENRES:
        ms = [m for (m, gg) in pairs if gg == g and ('%s|%s|%s' % (base, m, g)) in npz.files]
        if len(ms) < 20: continue
        X = np.array([npz['%s|%s|%s' % (base, m, g)] for m in ms])
        mu, sd = X.mean(0), X.std(0, ddof=1); sd[sd == 0] = 1
        Z[g] = ({m: i for i, m in enumerate(ms)}, (X - mu) / sd)
    rows, keep = [], []
    for m in MEM:
        num = None; den = 0.0
        for g in Z:
            idx, Xg = Z[g]
            if m in idx:
                w = TOK.get((m, g), 1)
                num = Xg[idx[m]] * w if num is None else num + Xg[idx[m]] * w; den += w
        if den > 0: rows.append(num / den); keep.append(m)
    return np.array(rows), keep

# ---------------------------------------------------------------- the diagnostic
def diag(name, X, mask, seeds):
    """Addendum-1 stratum-power diagnostic, verbatim semantics, parameterized by basis. Per seed:
    orthogonalized plant set (NM.plant_set, target r=.40), masked-A plant on the ACTUAL stratum;
    bars 1-4 = own>=.15 | exact perm-p<.05 | row-dominant vs O/C/E/ES plants | column-specific
    strict vs all five core-plant models. Entirely synthetic."""
    Xs = X[mask]
    out = []
    for sd in seeds:
        rng = np.random.default_rng(sd)
        yc, yn = NM.plant_set(X, Xs, mask, rng)
        pc = {t: BI.oof(X, yc[t]) for t in CORE}
        pn = BI.oof(Xs, yn)
        own, pp, _ = BI.exact_perm_p(pn, yn)
        row = all(abs(own) >= abs(rr(pn, yc[c][mask])) for c in ['O', 'C', 'E', 'ES']) and own > 0
        col = all(abs(own) > abs(rr(pc[c][mask], yn)) for c in CORE)
        b12 = (own >= 0.15) and (pp < .05)
        b14 = b12 and row and col
        out.append({'seed': sd, 'own': own, 'perm_p': pp, 'row': row, 'col': col, 'b12': b12, 'b14': b14})
        print('  [%s] seed %d: own %+.3f p %.4f row %s col %s -> bars1-4 %s'
              % (name, sd, own, pp, row, col, 'PASS' if b14 else 'miss'), flush=True)
    med = float(np.median([o['own'] for o in out]))
    n12 = sum(o['b12'] for o in out); n14 = sum(o['b14'] for o in out)
    gate = n14 >= 3
    print('  [%s] SUMMARY: median own %+.3f | bars1-2 %d/5 | bars1-4 %d/5 -> gate %s'
          % (name, med, n12, n14, 'CLEARED' if gate else 'refused'), flush=True)
    return {'basis': name, 'median_own': med, 'n12': n12, 'n14': n14, 'gate': gate, 'runs': out}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='')
    args = ap.parse_args()
    print('round-5 successor-gate diagnostic (SYNTHETIC ONLY — no look, no real pairing)', flush=True)
    BD, VV, P, MEM, alltext = BI.load_corpus()
    CV = json.load(open(B + r'\coop_v2_candidate.json'))['members']
    mask = np.array([(CV.get(m) or {}).get('cooperation_v2_z') is not None for m in MEM])
    del CV                                              # coverage mask retained; values never used
    print('rosters: MEM=%d | MEM_A=%d (Addendum-1 lock: 456/290)' % (len(MEM), int(mask.sum())), flush=True)
    results = []
    # baseline: the pinned Empath instrument (Addendum-1 reproduction)
    Xe = BI.featurize(MEM, alltext)
    print('\n--- basis: empath (Addendum-1 baseline; expected ~2/5, median ~+.132) ---', flush=True)
    results.append(diag('empath', Xe, mask, PIN5))
    # open-vocab bases on the CURRENT corpus
    build_emb_r6()
    meta = json.load(open(EMB_META))
    memset = set(MEM)
    for base in meta['bases']:
        Xb, keep = member_matrix(base, MEM)
        kmask = mask[[MEM.index(m) for m in keep]] if keep != MEM else mask
        print('\n--- basis: %s (n=%d, stratum n=%d) ---' % (base, len(keep), int(kmask.sum())), flush=True)
        results.append(diag(base, Xb, kmask, PIN5))
    # concat: empath ⊕ lsa256 (both blocks column-z-scored)
    Xb, keep = member_matrix('lsa256', MEM)
    ki = [MEM.index(m) for m in keep]
    Xc = np.hstack([np.apply_along_axis(zz, 0, Xe[ki]), np.apply_along_axis(zz, 0, Xb)])
    kmask = mask[ki]
    print('\n--- basis: empath+lsa256 (n=%d, stratum n=%d) ---' % (len(keep), int(kmask.sum())), flush=True)
    results.append(diag('empath+lsa256', Xc, kmask, PIN5))
    # confirmation on FRESH seeds for any basis that cleared selection
    winners = [r for r in results if r['gate'] and r['basis'] != 'empath']
    confirms = []
    for w in winners:
        base = w['basis']
        print('\n=== CONFIRMATION (fresh seeds %s): %s ===' % (FRESH5, base), flush=True)
        if base == 'empath+lsa256':
            Xb, keep = member_matrix('lsa256', MEM); ki = [MEM.index(m) for m in keep]
            Xw = np.hstack([np.apply_along_axis(zz, 0, Xe[ki]), np.apply_along_axis(zz, 0, Xb)]); km = mask[ki]
        else:
            Xw, keep = member_matrix(base, MEM); km = mask[[MEM.index(m) for m in keep]]
        confirms.append(diag(base + ' [FRESH]', Xw, km, FRESH5))
    print('\n===================== VERDICT =====================', flush=True)
    for r in results:
        print('  %-16s median %+.3f  bars1-4 %d/5  %s' % (r['basis'], r['median_own'], r['n14'],
              'CLEARED (selection)' if r['gate'] else ''), flush=True)
    ok = [c for c in confirms if c['gate']]
    if ok:
        print('\n  CONFIRMED on fresh seeds: %s — the successor gate condition (>=3/5 bars 1-4) is met by a'
              % ', '.join(c['basis'].replace(' [FRESH]', '') for c in ok), flush=True)
        print('  NEW instrument basis. Next step is a successor-prereg PROPOSAL to Paul (new instrument =', flush=True)
        print('  new prereg + adversarial review). No status change; no look was taken.', flush=True)
    elif winners:
        print('\n  Selection-set winners FAILED fresh-seed confirmation — selection artifact; gate stays shut.', flush=True)
    else:
        print('\n  No basis cleared the gate on the current stratum/corpus — the route stays DIAGNOSTIC-GATED;'
              '\n  levers remain coverage growth (MEM_A) and corpus growth.', flush=True)
    if args.out:
        json.dump({'results': results, 'confirms': confirms}, open(args.out, 'w'), indent=1)
        print('  wrote %s' % args.out, flush=True)

if __name__ == '__main__':
    main()
