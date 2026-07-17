# -*- coding: utf-8 -*-
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))  # centralized root
from paths import ROOT as _ROOT
# Legislative+Press TIER — a DISPLAY-ONLY re-rank on 2 of the 4 rank pillars. Shared by
# build_dashboard_bundle.py and make_member_desk.py so the tier definition lives in ONE place (no drift).
#
# The overall rank blends four pillars (Leg 30 / Press 25 / Committee 40 / Demo 5). A "tier" drops Committee +
# Demo and re-ranks members on legislative + press ALONE using the source-controlled display-tier weights
# (user-ratified 2026-07-16: 80% Legislative / 20% Press), then buckets the top 12 / next 24 / next 48
# (Tier 1/2/3; the remaining ~449 are untiered = 0). Both pillar values are already normalized model
# inputs in ranks_python.json and are the exact inputs used by the overall rank. Re-percentile-ranking
# them here used a second, unrelated scale that exaggerated narrow rank differences and promoted Daniel
# Meuser to Tier rank #1. The display tier now drops Committee + Demo but otherwise preserves the model's
# Legislative/Press inputs under the explicit tier policy. Pure: reads ranks_python.json, returns dicts; writes
# nothing, touches no engine. Import-safe (unlike most fec/*.py) — no work at import time.
import os, json

BUCKETS = (12, 24, 48)   # Tier 1 / 2 / 3 sizes; cumulative cutoffs 12 / 36 / 84, rest untiered (tier 0)
_CODE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_OVERRIDE_PATH = os.path.join(_CODE_ROOT, 'tier_overrides.json')


def legislative_press_scores(pcts, legislative_weight, press_weight):
    """Blend the already-normalized Legislative and Press pillar inputs without rescaling them."""
    out = {}
    for member, values in (pcts or {}).items():
        try:
            leg = float(values['leg'])
            press = float(values['press'])
        except (KeyError, TypeError, ValueError):
            continue
        out[member] = float(legislative_weight) * leg + float(press_weight) * press
    return out


def _load_tier_policy(path=None):
    """Load the source-controlled display-tier policy document."""
    path = path or _OVERRIDE_PATH
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def load_tier_weights(path=None, fallback=(0.30, 0.25)):
    """Return (Legislative, Press) display-tier weights.

    The explicit policy must be a positive, unit-sum pair. The legacy workbook ratio remains a fallback
    only for installations that do not yet carry ``tier_overrides.json``.
    """
    doc = _load_tier_policy(path)
    weights = doc.get('weights') if isinstance(doc, dict) else None
    if not weights:
        return tuple(float(value) for value in fallback)
    try:
        legislative = float(weights['legislation'])
        press = float(weights['press'])
    except (KeyError, TypeError, ValueError):
        raise ValueError('tier weights require numeric legislation and press values')
    if legislative <= 0.0 or press <= 0.0 or abs(legislative + press - 1.0) > 1e-9:
        raise ValueError('tier weights must be positive and sum to 1.0')
    return legislative, press


def load_tier_overrides(path=None):
    """Load exact member->tier placements from the source-controlled display-tier contract."""
    doc = _load_tier_policy(path)
    rows = doc if isinstance(doc, list) else doc.get('placements', [])
    out = {}
    for row in rows:
        member = str(row.get('member') or '').strip()
        try:
            tier = int(row.get('tier'))
        except (TypeError, ValueError):
            tier = 0
        if not member or tier not in (1, 2, 3):
            raise ValueError('invalid tier override row: %r' % row)
        if member in out:
            raise ValueError('duplicate tier override member: %s' % member)
        out[member] = tier
    return out


def apply_tier_overrides(order, overrides=None, buckets=BUCKETS):
    """Return a fixed-size display order honoring exact placements.

    Forced members occupy their named bucket. Remaining seats are filled from the unmodified
    score order, excluding members forced into another bucket. Within each bucket, members retain
    their relative score order so the override changes placement, not the underlying score.
    """
    order = list(order)
    pos = {member: i for i, member in enumerate(order)}
    # FAIL LOUD on unresolved placement names (rank-integrity audit 2026-07-17): a typo'd or
    # rolled-over member in tier_overrides.json used to be silently dropped, quietly changing
    # Tier buckets and the Champion crown. Paul's placement contract must bind exactly.
    _unknown = sorted(m for m in (overrides or {}) if m not in pos)
    if _unknown:
        raise ValueError('tier placement names not in the rankable roster: %s' % _unknown)
    overrides = {member: int(tier) for member, tier in (overrides or {}).items()}
    if any(tier not in (1, 2, 3) for tier in overrides.values()):
        raise ValueError('tier overrides must be 1, 2, or 3')
    assigned = set()
    display_order = []
    for tier, capacity in enumerate(tuple(buckets), start=1):
        forced = [member for member in order if overrides.get(member) == tier]
        if len(forced) > capacity:
            raise ValueError('tier %d has %d forced members for %d seats' %
                             (tier, len(forced), capacity))
        eligible = [member for member in order
                    if member not in assigned and member not in overrides]
        selected = forced + eligible[:capacity - len(forced)]
        selected.sort(key=pos.__getitem__)
        assigned.update(selected)
        display_order.extend(selected)
    display_order.extend(member for member in order if member not in assigned)
    return display_order


def legislative_press_tiers(members, root=None):
    """Return (tier, tierrank): dict member -> tier int (1/2/3, 0 = untiered) and dict member -> 1-based
    legislative+press rank. `members` bounds and names the pool; any member absent from ranks_python.json's
    pcts is untiered and gets no leg+press rank."""
    root = root or _ROOT
    with open(os.path.join(root, 'ranks_python.json'), encoding='utf-8') as handle:
        rp = json.load(handle)
    pcts = rp.get('pcts', {}); abw = rp.get('ab_weights', {})
    default_wL = float(abw.get('2', 0.30)); default_wP = float(abw.get('3', 0.25))
    wL, wP = load_tier_weights(fallback=(default_wL, default_wP))

    all_scores = legislative_press_scores(pcts, wL, wP)
    rankable = [m for m in members if m in all_scores]
    tsc = {m: all_scores[m] for m in rankable}
    score_order = sorted(rankable, key=lambda m: (-tsc[m], m))   # score desc; deterministic name tie-break
    order = apply_tier_overrides(score_order, load_tier_overrides())
    b1, b2, b3 = BUCKETS[0], BUCKETS[0] + BUCKETS[1], BUCKETS[0] + BUCKETS[1] + BUCKETS[2]
    tier = {}; tierrank = {}
    for i, m in enumerate(order):
        tierrank[m] = i + 1
        tier[m] = 1 if i < b1 else 2 if i < b2 else 3 if i < b3 else 0
    return tier, tierrank
