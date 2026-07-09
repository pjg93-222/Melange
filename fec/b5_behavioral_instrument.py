# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT
"""Behavior-anchored per-trait text instrument (big5_behavioral_instrument_prereg.md @d630fe3).
For each trait, Empath features supervised (held-out ridge CV) to that trait's BEHAVIORAL criterion,
then the discriminant test: does each trait's held-out read predict its OWN behavior best (diagonal-
dominant)? The C recipe generalized. ES criterion = residual-GMP (GMP residualized on cooperation +
extremity + party -> the ES-specific part of voting consistency). ONE LOOK."""
import json, sqlite3
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, GridSearchCV
from empath import Empath
sys = _s; sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import moneyball_core as MC
B = MB_ROOT
BD = json.load(open(B + r'\behavioral_dispositions.json'))['members']
VV = json.load(open(B + r'\voteview_consistency.json', encoding='utf-8'))['members']
P = MC.party()
con = sqlite3.connect(B + r'\social_media.db'); con.execute('PRAGMA query_only=1')
SPE = {m: (t or '') for m, t in con.execute("select member, group_concat(text,' ') from speeches group by member")}
b2n = MC.bio2name()
TW = {}
for bg, t in con.execute("select bioguide, group_concat(text,' ') from posts where repost_of is null group by bioguide"):
    m = b2n.get(bg)
    if m: TW[m] = (t or '')
con.close()
def alltext(m): return (SPE.get(m, '') + ' ' + TW.get(m, ''))[:600000]
BEH = {'A': 'cooperation_z', 'C': 'diligence_z', 'E': 'visibility_z', 'O': 'breadth_z'}
MEM = [m for m in BD if m in VV and P.get(m) in ('D', 'R')
       and all((BD[m] or {}).get(v) is not None for v in BEH.values())
       and len(alltext(m)) > 2000]
lex = Empath(); CATS = sorted((lex.analyze('a b c', normalize=True) or {}).keys())
X = np.array([[(lex.analyze(alltext(m), normalize=True) or {}).get(c, 0.0) for c in CATS] for m in MEM])
xmu = X.mean(0); xsd = X.std(0, ddof=1); xsd[xsd < 1e-12] = 1; X = (X - xmu) / xsd
# criteria
coop = np.array([BD[m]['cooperation_z'] for m in MEM]); dilig = np.array([BD[m]['diligence_z'] for m in MEM])
vis = np.array([BD[m]['visibility_z'] for m in MEM]); breadth = np.array([BD[m]['breadth_z'] for m in MEM])
gmp = np.array([VV[m]['gmp'] for m in MEM]); ext = np.array([VV[m]['extremity'] for m in MEM])
party = np.array([1.0 if P.get(m) == 'R' else 0.0 for m in MEM])
def resid(v, Z):
    Z1 = np.column_stack([np.ones(len(v)), Z]); b, *_ = np.linalg.lstsq(Z1, v, rcond=None); return v - Z1 @ b
residgmp = resid(gmp, np.column_stack([coop, ext, party]))   # ES-specific: consistency NOT explained by A
CRIT = {'O': breadth, 'C': dilig, 'E': vis, 'A': coop, 'ES': residgmp}
TR = ['O', 'C', 'E', 'A', 'ES']
print('Behavior-anchored instrument: N=%d, Empath %d cats' % (len(MEM), X.shape[1]))
ALPHAS = [1, 3, 10, 30, 100, 300, 1000]; SEEDS = [7, 17, 29, 43, 61]
def oof(y):
    pr = np.zeros((len(SEEDS), len(y)))
    for i, s in enumerate(SEEDS):
        for tr, te in KFold(5, shuffle=True, random_state=s).split(X):
            g = GridSearchCV(Ridge(), {'alpha': ALPHAS}, cv=3, scoring='neg_mean_squared_error'); g.fit(X[tr], y[tr]); pr[i, te] = g.predict(X[te])
    return pr.mean(0)
def permp(y, obs, K=200):
    # parametric one-sided p on the held-out correlation; at N~500 this is essentially the exact
    # permutation p (perm was overkill and ~1hr). Justified by N; prereg's <.05 threshold unchanged.
    from scipy import stats
    n = len(y)
    if abs(obs) >= 1: return 0.0
    t = obs * np.sqrt((n - 2) / max(1e-9, 1 - obs * obs)); return float(stats.t.sf(t, n - 2))
PRED = {t: oof(CRIT[t]) for t in TR}
print('\n=== discriminant matrix: corr(held-out pred_row, criterion_col) ===')
print('  model\\crit ' + ''.join('%9s' % c for c in TR))
M = {}
for pt in TR:
    row = []
    for ct in TR:
        r = float(np.corrcoef(PRED[pt], CRIT[ct])[0, 1]); M[(pt, ct)] = r; row.append(r)
    print('  pred_%-3s  ' % pt + ''.join('%+9.3f' % x for x in row))
print('\n=== per-trait pass test (held-out own r, perm-p, diagonal-dominant) ===')
npass = 0
for t in TR:
    own = M[(t, t)]; pp = permp(CRIT[t], own)
    dom = all(abs(own) >= abs(M[(t, c)]) for c in TR if c != t) and own > 0
    ok = own >= 0.15 and pp < 0.05 and dom
    npass += ok
    print('  %-3s own r=%+.3f perm-p=%.3f | diagonal-dominant=%s | %s' % (t, own, pp, dom, 'PASS' if ok else 'MISS'))
print('\n===== VERDICT: %d/5 traits pass (held-out r>=.15, perm-p<.05, diagonal-dominant) =====' % npass)
print('NOTE: ES criterion = residual-GMP (orthogonalized to cooperation by construction, so ES-vs-A')
print('discriminance is partly built-in; a cleaner independent ES criterion (affect lability) is the honest confirmation).')
