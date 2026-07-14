# -*- coding: utf-8 -*-
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))  # centralized root
from paths import ROOT as _ROOT
# Legislative+Press TIER — a DISPLAY-ONLY re-rank on 2 of the 4 rank pillars. Shared by
# build_dashboard_bundle.py and make_member_desk.py so the tier definition lives in ONE place (no drift).
#
# The overall rank blends four pillars (Leg 30 / Press 25 / Committee 40 / Demo 5). A "tier" drops Committee +
# Demo and re-ranks members on legislative + press ALONE, then buckets the top 12 / next 24 / next 48
# (Tier 1/2/3; the remaining ~449 are untiered = 0). Both pillar scores already exist per member in
# ranks_python.json. leg% is a percentrank but press% is a bunched max-ratio, so we put BOTH on a common
# percentile scale before blending (else legislative silently dominates), then weight by the LIVE leg:press
# ratio from the workbook dials (match-the-model, Paul 2026-07-13). Pure: reads ranks_python.json, returns
# dicts; writes nothing, touches no engine. Import-safe (unlike most fec/*.py) — no work at import time.
import os, json, bisect

BUCKETS = (12, 24, 48)   # Tier 1 / 2 / 3 sizes; cumulative cutoffs 12 / 36 / 84, rest untiered (tier 0)


def legislative_press_tiers(members, root=None):
    """Return (tier, tierrank): dict member -> tier int (1/2/3, 0 = untiered) and dict member -> 1-based
    legislative+press rank. `members` bounds and names the pool; any member absent from ranks_python.json's
    pcts is untiered and gets no leg+press rank."""
    root = root or _ROOT
    rp = json.load(open(os.path.join(root, 'ranks_python.json'), encoding='utf-8'))
    pcts = rp.get('pcts', {}); abw = rp.get('ab_weights', {})
    wL = float(abw.get('2', 0.30)); wP = float(abw.get('3', 0.25))   # '2' = Legislative, '3' = Press (live dials)

    def pctile(vals):   # Excel PERCENTRANK.INC convention (as the rank model uses): (#strictly below)/(n-1)
        s = sorted(vals); n = len(s)
        return (lambda v: (bisect.bisect_left(s, v) / (n - 1)) if n > 1 else 0.0)

    rankable = [m for m in members if m in pcts]
    legf = pctile([pcts[m]['leg'] for m in rankable])
    prsf = pctile([pcts[m]['press'] for m in rankable])
    tsc = {m: wL * legf(pcts[m]['leg']) + wP * prsf(pcts[m]['press']) for m in rankable}
    order = sorted(rankable, key=lambda m: (-tsc[m], m))   # score desc; deterministic tie-break by name (stable cut)
    b1, b2, b3 = BUCKETS[0], BUCKETS[0] + BUCKETS[1], BUCKETS[0] + BUCKETS[1] + BUCKETS[2]
    tier = {}; tierrank = {}
    for i, m in enumerate(order):
        tierrank[m] = i + 1
        tier[m] = 1 if i < b1 else 2 if i < b2 else 3 if i < b3 else 0
    return tier, tierrank
