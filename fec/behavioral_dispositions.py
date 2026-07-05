# -*- coding: utf-8 -*-
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from paths import ROOT as MB_ROOT
"""BEHAVIORAL DISPOSITIONS (2026-07-04 nomological fix, user: 'fix it — do whatever it takes').
The pre-registered label-free validation (big5_nomological_prereg.md) INDICTED the lexical Big5
for behavioral prediction (C reversed on participation, E measures broadcast talkativeness,
r_alerting -0.76). The research-correct replacement: measure dispositions FROM BEHAVIOR — the
criteria were better measures than the instruments. Each score maps to the construct ROLE the
receptivity layer needs, using the panel outcomes whose validity is definitional (they ARE the
behavior) plus the interaction channel where the literature grounds it:

  cooperation_z  bipartisanship + cosponsor breadth + cosponsor count      [A-role: the ONE corner
                 lexical A validated on (+.11 FDR-sig) — measured directly instead of inferred]
  diligence_z    roll-call participation (votes_cast, z-log within chamber) [C-role: RKH's
                 strongest C criterion; our lexical C REVERSED on it]
  dominance_z    interaction channel (verbal output + floor-holding Gini + floor defense,
                 per-program z) + committee leadership                      [E-dominance role:
                 turn statistics are the replicated dominance signal (Rienks&Heylen; Valente)]
  visibility_z   broadcast engagement (interview count + program breadth)   [E-sociability role:
                 'takes meetings' proxied by demonstrably taking interviews]
  breadth_z      legislative portfolio breadth (# distinct issue sections   [O-role: engages
                 with any sponsor/cosponsor role in the bills archive)       across novel domains]

All z within chamber where the raw scale differs by chamber. Missing data -> None (consumers fall
back to neutral 0 — never an invented disposition). Output: behavioral_dispositions.json."""
import csv, glob, json, math, os, sys, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl
B = MB_ROOT
C = {m['member']: m for m in json.load(open(B + r'\congestion.json'))}
PANEL = json.load(open(B + r'\behavior_panel.json'))['members']
chamber = {m: (C.get(m) or {}).get('chamber') or '?' for m in C}

def zscore(vals, log=False):
    """vals {m: raw} -> z within chamber (pooled if chamber unknown)."""
    out = {}
    for ch in ('House', 'Senate'):
        ms = [m for m in vals if chamber.get(m) == ch and vals[m] is not None]
        if len(ms) < 5: continue
        xs = {m: (math.log1p(max(0.0, float(vals[m]))) if log else float(vals[m])) for m in ms}
        mu = sum(xs.values()) / len(xs)
        sd = (sum((v - mu) ** 2 for v in xs.values()) / max(1, len(xs) - 1)) ** 0.5 or 1.0
        for m in ms: out[m] = (xs[m] - mu) / sd
    return out

def mean_z(zdicts, need=1):
    """average available z-scores per member; None if fewer than `need` components."""
    out = {}
    for m in C:
        vs = [z[m] for z in zdicts if m in z]
        if len(vs) >= need: out[m] = sum(vs) / len(vs)
    return out

# cooperation: bipartisanship (raw ratio) + cosponsor degree + cosponsor count
coop = mean_z([zscore({m: d.get('bipartisanship') for m, d in PANEL.items() if d.get('bipartisanship') is not None}),
               zscore({m: d.get('cosponsor_degree') for m, d in PANEL.items() if d.get('cosponsor_degree') is not None}, log=True),
               zscore({m: d.get('n_cosponsored') for m, d in PANEL.items() if d.get('n_cosponsored') is not None}, log=True)], need=2)

# diligence: roll-call participation volume. Volume only signals diligence for FULL-TERM voting
# members: non-voting delegates and mid-term entrants (special elections) sit far below chamber
# median through no disposition of their own -> neutral (None), never scored. z clipped +/-3.
_vc = {m: d.get('votes_cast') for m, d in PANEL.items() if d.get('votes_cast')}
_med = {}
for _ch in ('House', 'Senate'):
    _vs = sorted(v for m, v in _vc.items() if chamber.get(m) == _ch)
    if _vs: _med[_ch] = _vs[len(_vs) // 2]
dil = zscore({m: v for m, v in _vc.items() if v >= 0.25 * _med.get(chamber.get(m), 1e9)}, log=True)
dil = {m: max(-3.0, min(3.0, v)) for m, v in dil.items()}

# dominance: interaction channel + committee leadership
dom_parts = []
ixp = B + r'\interaction_features.json'
if os.path.exists(ixp):
    IX = {m: d for m, d in json.load(open(ixp))['members'].items() if d.get('turns', 0) >= 30}
    dom_parts.append({m: (d['wpt_mean'] + d['gini'] + d['defense']) / 3.0 for m, d in IX.items()})
dom_parts.append(zscore({m: d.get('committee_leader', 0) for m, d in PANEL.items()}))
dom = mean_z(dom_parts, need=1)

# visibility: broadcast engagement. INTERIM GUARD (until the nickname-fixed re-ingest lands):
# members with <3 attributed interviews are indistinguishable from alias-dropped members
# (Bernie/Bernard-class) — neutral (None), never penalized for a resolver gap.
vis = mean_z([zscore({m: d.get('n_interviews') for m, d in PANEL.items() if (d.get('n_interviews') or 0) >= 3}, log=True),
              zscore({m: d.get('n_interview_programs') for m, d in PANEL.items() if (d.get('n_interviews') or 0) >= 3}, log=True)], need=1)

# breadth: distinct issue sections with any legislative role (bills archive)
bp = max(glob.glob(B + r'\congress_bills_archive_*.xlsx'), key=os.path.getmtime)
ws = openpyxl.load_workbook(bp, read_only=True)['All Bills']
rows = ws.iter_rows(min_row=1, values_only=True)
hdr = [str(h or '') for h in next(rows)]
iS, iM = hdr.index('Section'), hdr.index('Member')
secs = collections.defaultdict(set)
for r in rows:
    if r[iM] in C and r[iS]: secs[r[iM]].add(str(r[iS]))
bre = zscore({m: len(s) for m, s in secs.items()}, log=False)

from moneyball_core import dump_atomic
out = {}
for m in C:
    d = {}
    for k, src in (('cooperation_z', coop), ('diligence_z', dil), ('dominance_z', dom),
                   ('visibility_z', vis), ('breadth_z', bre)):
        if m in src: d[k] = round(src[m], 3)
    if d: out[m] = d
cov = {k: sum(1 for m in out if k in out[m]) for k in
       ('cooperation_z', 'diligence_z', 'dominance_z', 'visibility_z', 'breadth_z')}
dump_atomic({'members': out, 'coverage': cov,
             'method': 'dispositions measured from behavior (nomological fix 2026-07-04): cooperation='
                       'bipartisanship+cosponsor embedding; diligence=roll-call participation; dominance='
                       'interaction turn-stats+leadership; visibility=broadcast engagement; breadth='
                       'legislative portfolio sections; z within chamber; missing -> neutral downstream'},
            B + r'\behavioral_dispositions.json')
print('behavioral dispositions: %d members | coverage %s' % (len(out), cov))
for k in cov:
    vals = sorted(((out[m][k], m) for m in out if k in out[m]), reverse=True)
    print('  %-14s hi: %-40s lo: %s' % (k.replace('_z', ''),
          ', '.join('%s %+0.1f' % (m, v) for v, m in vals[:2]),
          ', '.join('%s %+0.1f' % (m, v) for v, m in vals[-2:])))
