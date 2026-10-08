import csv
import glob
import json
import os
import sys

import numpy as np

B = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
sys.path.insert(0, B + r'\fec')
import moneyball_core as MC

csv.field_size_limit(1 << 30)


def jload(p):
    return json.load(open(os.path.join(B, p), encoding='utf-8'))


cong = jload(r'data\engine\congestion.json')
roster = [m['member'] for m in cong]
idx = {m: i for i, m in enumerate(roster)}
n = len(roster)

cols = {}
miss = {}


def col(name, default=np.nan):
    cols[name] = np.full(n, default, dtype=float)
    return cols[name]


# money block
cu = col('cu'); ind = col('ind'); rec = col('receipts'); nodata = col('nodata_flag', 0.0)
chamber = col('chamber_house', 0.0)
for m in cong:
    i = idx[m['member']]
    cu[i] = m.get('cu') or 0.0
    ind[i] = (m.get('banks') or 0.0) + (m.get('finserv') or 0.0)
    rec[i] = m.get('receipts') or 0.0
    nodata[i] = 1.0 if not m.get('receipts') else 0.0
    chamber[i] = 1.0 if str(m.get('chamber', '')).upper().startswith('H') else 0.0
cols['log_receipts'] = np.log1p(rec)
cols['log_cu'] = np.log1p(cu)
cols['log_ind'] = np.log1p(ind)

# network strength from newest AUG workbook
import openpyxl
aug = sorted(glob.glob(os.path.join(B, 'congress_cosponsor_network_AUG*.xlsx')), key=os.path.getmtime)[-1]
b2n = {m['bioguide']: m['member'] for m in cong}
strength = col('net_strength', 0.0)
wb = openpyxl.load_workbook(aug, read_only=True)
ws = wb['Edges']
rows = ws.iter_rows(values_only=True)
next(rows)
for a, b2, w in rows:
    for bio in (a, b2):
        m = b2n.get(bio)
        if m is not None and isinstance(w, (int, float)):
            strength[idx[m]] += float(w)

# party, bpf
party = MC.party()
pR = col('party_R')
for m in roster:
    p = party.get(m)
    pR[idx[m]] = 1.0 if p == 'R' else (0.0 if p == 'D' else np.nan)
bpf = jload('bipartisan.json')
bpfc = col('bpf')
bmap = bpf.get('members', bpf) if isinstance(bpf, dict) else {}
for m in roster:
    v = bmap.get(m)
    if isinstance(v, dict):
        v = v.get('bpf', v.get('share'))
    if isinstance(v, (int, float)):
        bpfc[idx[m]] = v

# stance
cs = jload('category_stance.json')
scores = cs.get('scores', {})
matrix = cs.get('matrix', {})
PERS = {'Champion': 1.0, 'Strong Ally': 0.9, 'Ally': 0.8, 'Lean Ally': 0.7, 'In-Group Normal': 0.6,
        'Persuadable': 0.55, 'Neutral': 0.5, 'Lean Skeptic': 0.4, 'Skeptic': 0.3,
        'Highly Skeptical': 0.2, 'Opponent': 0.1}
sc_mean = col('stance_score_mean'); pers_mean = col('stance_pers_mean'); none_share = col('stance_none_share')
for m in roster:
    i = idx[m]
    srow = scores.get(m, {})
    vals = [v for v in srow.values() if isinstance(v, (int, float))]
    if vals:
        sc_mean[i] = float(np.mean(vals))
    trow = matrix.get(m, {})
    if trow:
        pvals = [PERS.get(t, 0.45) for t in trow.values()]
        pers_mean[i] = float(np.mean(pvals))
        none_share[i] = sum(1 for t in trow.values() if t in ('-', '\u2014', '')) / len(trow)

# say-do
try:
    sd = jload('say_do_gap.json')
    sdm = sd.get('members', sd)
    g = col('say_do_gap')
    for m in roster:
        v = sdm.get(m)
        if isinstance(v, dict):
            v = v.get('gap')
        if isinstance(v, (int, float)):
            g[idx[m]] = v
except FileNotFoundError:
    print('NOTE: say_do_gap.json not found at root')

# receptivity leaves
bd = jload('behavioral_dispositions.json')['members']
for fld in ('diligence_z', 'dominance_z', 'breadth_z', 'visibility_z', 'cooperation_z'):
    a = col(fld)
    for m in roster:
        v = (bd.get(m) or {}).get(fld)
        if isinstance(v, (int, float)):
            a[idx[m]] = v

coopv2 = None
for cand in ('coop_v2_candidate.json', r'data\members\coop_v2_candidate.json'):
    try:
        coopv2 = jload(cand)
        break
    except FileNotFoundError:
        pass
cv = col('cooperation_v2_z'); cvm = col('coopv2_missing', 1.0)
if coopv2:
    src = coopv2.get('members', coopv2)
    for m in roster:
        v = (src.get(m) or {}).get('cooperation_v2_z') if isinstance(src.get(m), dict) else src.get(m)
        if isinstance(v, (int, float)):
            cv[idx[m]] = v
            cvm[idx[m]] = 0.0

an = jload(r'data\money\affective_n.json').get('members', {})
av = col('affective_n'); avm = col('affn_missing', 1.0)
for m in roster:
    v = an.get(m)
    if isinstance(v, (int, float)):
        av[idx[m]] = v
        avm[idx[m]] = 0.0

ac = jload(r'data\members\agency_communion.json')
acs = ac.get('members', ac)
ag = col('agency'); cm = col('communion'); acm = col('persona_missing', 1.0)
for m in roster:
    row = acs.get(m)
    if isinstance(row, dict) and isinstance(row.get('agency'), (int, float)):
        ag[idx[m]] = row['agency']
        cm[idx[m]] = row.get('communion', np.nan)
        acm[idx[m]] = 0.0

el = jload(r'data\money\electoral.json')
els = el.get('members', el)
sec = col('security')
for m in roster:
    row = els.get(m)
    v = row.get('security') if isinstance(row, dict) else None
    if isinstance(v, (int, float)):
        sec[idx[m]] = v

ep = jload(r'data\money\electoral_plays.json')
eps = ep.get('members', ep)
play = col('play_defend_contest', 0.0)
for m in roster:
    row = eps.get(m)
    p = row.get('play') if isinstance(row, dict) else None
    play[idx[m]] = 1.0 if p in ('defend', 'contest') else 0.0

ret = col('retiring', 0.0)
try:
    with open(os.path.join(B, r'fec\retiring_members.txt'), encoding='utf-8') as fh:
        rset = {ln.strip() for ln in fh if ln.strip()}
    for m in roster:
        if m in rset:
            ret[idx[m]] = 1.0
except FileNotFoundError:
    print('NOTE: retiring_members.txt not found')

# composites (model's own multipliers) + confounders
rcv = jload('member_receptivity.json')['members']
for fld in ('susc_z', 'pressure_mult', 'edge_mult', 'susc_mult', 'incent_mult', 'pt_mult', 'seed_prob'):
    a = col('M_' + fld)
    for m in roster:
        v = (rcv.get(m) or {}).get(fld)
        if isinstance(v, (int, float)):
            a[idx[m]] = v

b5 = jload(r'data\members\big5_traits.json')['traits']
tok = col('C_tokens'); npo = col('C_nposts')
for m in roster:
    row = b5.get(m)
    if row:
        tok[idx[m]] = row.get('tokens', np.nan)
        npo[idx[m]] = row.get('nposts', np.nan)
cols['C_log_tokens'] = np.log1p(tok)
cols['C_log_nposts'] = np.log1p(npo)

gender = col('C_gender_F')
with open(os.path.join(B, r'fec\legislators.csv'), encoding='utf-8', errors='replace', newline='') as fh:
    rd = csv.DictReader(fh)
    gcolname = next((c for c in rd.fieldnames if 'gender' in c.lower()), None)
    bcolname = next((c for c in rd.fieldnames if 'bioguide' in c.lower()), None)
    for row in rd:
        m = b2n.get((row.get(bcolname) or '').strip())
        if m is not None and gcolname:
            gender[idx[m]] = 1.0 if (row.get(gcolname) or '').strip().upper() == 'F' else 0.0


# ---- statistics ----
def rankdata(x):
    order = np.argsort(x)
    ranks = np.empty(len(x))
    sx = x[order]
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and sx[j + 1] == sx[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0
        i = j + 1
    return ranks


def corr(a, b, spearman=False):
    ok = ~(np.isnan(a) | np.isnan(b))
    if ok.sum() < 30:
        return np.nan, int(ok.sum())
    x, y = a[ok], b[ok]
    if spearman:
        x, y = rankdata(x), rankdata(y)
    if x.std() == 0 or y.std() == 0:
        return np.nan, int(ok.sum())
    return float(np.corrcoef(x, y)[0, 1]), int(ok.sum())


def partial_party(a, b):
    ok = ~(np.isnan(a) | np.isnan(b) | np.isnan(cols['party_R']))
    if ok.sum() < 30:
        return np.nan
    x, y, p = a[ok], b[ok], cols['party_R'][ok]
    P = np.column_stack([np.ones(ok.sum()), p])
    rx = x - P @ np.linalg.lstsq(P, x, rcond=None)[0]
    ry = y - P @ np.linalg.lstsq(P, y, rcond=None)[0]
    if rx.std() == 0 or ry.std() == 0:
        return np.nan
    return float(np.corrcoef(rx, ry)[0, 1])


LEAVES = ['log_cu', 'log_ind', 'log_receipts', 'nodata_flag', 'net_strength', 'party_R', 'bpf',
          'stance_score_mean', 'stance_pers_mean', 'stance_none_share', 'say_do_gap',
          'cooperation_v2_z', 'coopv2_missing', 'affective_n', 'affn_missing',
          'diligence_z', 'dominance_z', 'breadth_z', 'visibility_z',
          'agency', 'communion', 'persona_missing', 'security', 'play_defend_contest',
          'retiring', 'chamber_house']
LEAVES = [c for c in LEAVES if c in cols and np.isfinite(cols[c]).sum() >= 100]
COMPS = [c for c in cols if c.startswith('M_')]
CONF = [c for c in cols if c.startswith('C_')]

print('== coverage (non-null of 533) ==')
for c in LEAVES + COMPS + CONF:
    print('  %-22s %d' % (c, int(np.isfinite(cols[c]).sum())))

print()
print('== FLAGGED PAIRS |spearman| >= 0.7 (pre-pinned) among leaves+composites ==')
allc = LEAVES + COMPS
flagged = []
for i in range(len(allc)):
    for j in range(i + 1, len(allc)):
        rs, nn = corr(cols[allc[i]], cols[allc[j]], spearman=True)
        if rs is not np.nan and not np.isnan(rs) and abs(rs) >= 0.7:
            rp, _ = corr(cols[allc[i]], cols[allc[j]])
            pp = partial_party(cols[allc[i]], cols[allc[j]])
            flagged.append((allc[i], allc[j], rs, rp, pp, nn))
            print('  %-22s x %-22s rho=%+.3f  r=%+.3f  party-partial=%+.3f  n=%d'
                  % (allc[i], allc[j], rs, rp, pp if pp is not None else np.nan, nn))

print()
print('== VIF over leaf set (z-scored, listwise) ==')
sub = [c for c in LEAVES]
X = np.column_stack([cols[c] for c in sub])
ok = ~np.isnan(X).any(axis=1)
Xk = X[ok]
print('  listwise n =', int(ok.sum()), 'of 533; k =', len(sub))
Z = (Xk - Xk.mean(0)) / np.where(Xk.std(0) == 0, 1, Xk.std(0))
for j, c in enumerate(sub):
    others = np.delete(Z, j, axis=1)
    A = np.column_stack([np.ones(len(Z)), others])
    beta, *_ = np.linalg.lstsq(A, Z[:, j], rcond=None)
    pred = A @ beta
    ss = ((Z[:, j] - pred) ** 2).sum()
    tt = (Z[:, j] ** 2).sum()
    r2 = 1 - ss / tt if tt > 0 else 0
    vif = 1 / (1 - r2) if r2 < 1 else float('inf')
    mark = ' <-- SEVERE' if vif >= 10 else (' <-- caution' if vif >= 5 else '')
    print('  %-22s VIF=%6.2f%s' % (c, vif, mark))

print()
print('== structural checks predicted by the formula map ==')
for a, b2 in (('M_edge_mult', 'M_susc_mult'), ('M_pressure_mult', 'M_susc_mult'),
              ('M_pressure_mult', 'security'), ('M_incent_mult', 'security'),
              ('M_pt_mult', 'security'), ('M_pt_mult', 'play_defend_contest'),
              ('M_seed_prob', 'cooperation_v2_z'), ('bpf', 'cooperation_v2_z'),
              ('net_strength', 'bpf')):
    rs, nn = corr(cols[a], cols[b2], spearman=True)
    rp, _ = corr(cols[a], cols[b2])
    print('  %-18s x %-20s rho=%+.3f r=%+.3f n=%d' % (a, b2, rs, rp, nn))

print()
print('== confounder register checks (volume / gender / chamber / retiring) ==')
targets = ['cooperation_v2_z', 'affective_n', 'diligence_z', 'dominance_z', 'breadth_z',
           'visibility_z', 'agency', 'communion', 'M_susc_z', 'M_pressure_mult', 'M_seed_prob']
for conf in ('C_log_tokens', 'C_log_nposts', 'C_gender_F', 'chamber_house', 'retiring', 'party_R'):
    hits = []
    for t in targets:
        rs, nn = corr(cols[conf], cols[t], spearman=True)
        if not np.isnan(rs) and abs(rs) >= 0.2:
            pp = partial_party(cols[conf], cols[t])
            hits.append('%s rho=%+.2f (party-partial %+.2f, n=%d)' % (t, rs, pp, nn))
    print('  %s:' % conf)
    for h in hits:
        print('     ', h)
    if not hits:
        print('      (no |rho| >= 0.2 against trait/composite targets)')

out = {'flagged_pairs': [{'a': a, 'b': b2, 'spearman': rs, 'pearson': rp, 'party_partial': pp, 'n': nn}
                         for a, b2, rs, rp, pp, nn in flagged]}
with open(r'C:\melange-data\collinearity_results.json', 'w', encoding='utf-8') as fh:
    json.dump(out, fh, indent=1)
print()
print('flagged-pair table -> C:\\melange-data\\collinearity_results.json')
