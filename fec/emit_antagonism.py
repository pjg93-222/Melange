# -*- coding: utf-8 -*-
"""Emit the RATIFIED hearing-antagonism facet (gate passed 5/5 on the full 2019-2026 corpus, 2026-07-11).
Writes hearing_antagonism.json: member -> {antagonism_z (dispositional, controlled), grandstand_z
(procedural-dominance axis), n_hearings, n_disp (Haiku dispositional-hostility events)}. This is a
DISPLAY + SECONDARY A-facet -- it does NOT feed the engine's A pillar (cooperation_v2 remains the primary
A basis), so member RANKS are unaffected. Consumed only by the dashboard display layer."""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
import hearing_antagonism_build as HB

from paths import ROOT
B = ROOT

def run():
    DW, PTY, agg, byhear, minority, opp, audit, nh = HB.build()
    SEN = HB.load_seniority()
    MIN = 20
    mem = [m for m in agg if agg[m]['turns'] >= MIN and m in DW]
    tr = np.array([agg[m]['turns'] for m in mem], float)
    def rate(k): return np.array([agg[m].get(k, 0) for m in mem]) / tr
    tot_lab = sum(agg[m].get('h_labeled', 0) for m in mem)
    disp = rate('h_disp') if tot_lab > 150 else rate('fr_personal')
    ext = np.array([DW[m]['extremity'] for m in mem]); d1 = np.array([DW[m]['dim1'] for m in mem])
    pty = np.array([1.0 if PTY.get(m) == 'R' else 0.0 for m in mem])
    minf = np.array([minority[m][0] / minority[m][1] if minority[m][1] else 0.5 for m in mem])
    sen = np.array([SEN.get(m, np.nan) for m in mem]); sen = np.where(np.isnan(sen), np.nanmean(sen), sen)
    antag = HB.resid(HB.z(rate('mm_intr')) + HB.z(rate('mm_xparty')) + HB.z(disp), [sen, ext, d1, pty, minf])
    antag = (antag - antag.mean()) / (antag.std() or 1)                 # re-standardize the residual
    grand = HB.z(rate('all_intr')) + HB.z(rate('proc')); grand = (grand - grand.mean()) / (grand.std() or 1)
    out = {}
    for i, m in enumerate(mem):
        out[m] = {'antagonism_z': round(float(antag[i]), 3), 'grandstand_z': round(float(grand[i]), 3),
                  'n_hearings': len(byhear[m]), 'n_disp': int(agg[m].get('h_disp', 0))}
    meta = {'members': out, 'n': len(out), 'corpus_hearings': nh, 'basis': 'display+secondary A-antagonism facet',
            'gate': '5/5 passed 2026-07-11 (antagonism_validate.py)', 'note': 'does NOT feed engine A pillar; ranks unaffected'}
    json.dump(meta, open(B + r'\hearing_antagonism.json', 'w'), indent=0)
    print('hearing_antagonism.json: %d members | corpus %d hearings' % (len(out), nh))
    o = sorted(mem, key=lambda m: -out[m]['antagonism_z'])
    print('top antagonism_z:', ', '.join('%s %.2f' % (m, out[m]['antagonism_z']) for m in o[:6]))
    print('top grandstand_z:', ', '.join('%s %.2f' % (m, out[m]['grandstand_z']) for m in sorted(mem, key=lambda m: -out[m]['grandstand_z'])[:6]))

if __name__ == '__main__':
    run()
