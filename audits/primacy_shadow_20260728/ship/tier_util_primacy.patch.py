# -*- coding: utf-8 -*-
"""PATCH SPEC for fec/tier_util.py — primacy tier + graduated conduct ladder.

`tier_util` is already documented as "DISPLAY-ONLY … writes nothing, touches no engine", and
`moneyball_core.overall_display_tier()` already reads `Tier 1 => Champion`. So gating and
re-scoring the tier changes the Champion crown for free, with ZERO rank delta.

WHAT CHANGED FROM THE 2026-07-28 DRAFT
--------------------------------------
The first draft consumed only `severity >= 3` and produced a single binary verdict:
"ineligible for Tier 1." But the ledger schema ALREADY carries `leverage_mult` on every
event, and it was being collected and thrown away. Two problems followed from that:

  1. Barr and Hill received the identical consequence though their leverage differs
     (Hill: full-committee chair AND vehicle sponsor, 2.0. Barr: subcommittee chair of
     jurisdiction, 1.75). The ledger recorded the difference; the code erased it.
  2. Severity-2 events (credit appropriation) counted for nothing at all, so a member
     could accumulate an unbounded number of them at no cost. BOTH of the severity-2
     events now in the ledger were worth exactly zero under the old rule.

The ladder fixes both by summing the ledger's own numbers instead of thresholding one field:

    effective_severity(member) = Σ  severity × leverage_mult   over OPEN, unexpired events

    eff >= 3  ->  tier ceiling 2      (cannot be a Champion)
    eff >= 6  ->  tier ceiling 3
    eff >= 9  ->  untiered

A ceiling is a FLOOR ON SLOT INDEX, not a fixed demotion: the member is barred from slots
above their ceiling's first slot and then re-enters at their own score position among the
remainder. A capped member whose score already sits below the ceiling does not move at all.

DELIVERY (added 2026-07-29). The grievance ledger could only ever punish. `delivery_ledger.ndjson`
is its positive mirror — institutional effort SPENT on the agenda, priced by the beneficiary class
of the bill moved, so managing a crypto bill earns nothing. The ladder reads the NET:

    net_severity = effective_severity - delivered_credit

Current ledgers:  French Hill  gross 3×2.00 + 2×1.00 = 8.00, delivered 3.00 -> net 5.00 -> ceiling 2
                  Andy Barr    gross 3×1.75 + 2×1.00 = 7.25, delivered 0.00 -> net 7.25 -> ceiling 3

Evidence, arithmetic and the one judgment call (Hill's 2.0 multiplier vs Barr's 1.0) are in
CONDUCT_LADDER.md §4-5. Note the ladder sums LOGGED events, so it measures the ledger, not
the world — see CONDUCT_LADDER.md §6 before adding events.

Drop these functions into tier_util.py, then replace the body of
`legislative_press_tiers()` with the block at the bottom.
"""
import os, json

PRIMACY_PATH  = 'primacy_factors.json'
LEDGER_PATH   = 'grievance_ledger.ndjson'
DELIVERY_PATH = 'delivery_ledger.ndjson'

# (effective_severity threshold, tier ceiling). Descending; 0 == untiered. Ratified in the spec.
CONDUCT_LADDER = ((9.0, 0), (6.0, 3), (3.0, 2))

# NOTE FOR THE INTEGRATOR — DELETE THE NEXT LINE when folding this into tier_util.py.
# tier_util.py already defines `BUCKETS = (12, 24, 48)` at line 18 as TIER SIZES, and
# `apply_tier_overrides(order, overrides, buckets=BUCKETS)` consumes it in that form. The value
# below is identical, and exists only so this file runs standalone for the test suite. Everything
# here uses the SIZES convention and derives cumulative cutoffs internally, exactly as
# tier_util.py line 187 already does. Never redefine BUCKETS as (12, 36, 84) — the cumulative
# form — or apply_tier_overrides will silently place Tier 2 at slot 37.
BUCKETS = (12, 24, 48)


def load_primacy_factors(root, path=None):
    """{member: factor_shrunk}. Missing file -> {} (FAIL OPEN: tier degrades to pure Leg%).
    Present-but-malformed -> raise (never treat corrupt evidence as absent)."""
    p = os.path.join(root, path or PRIMACY_PATH)
    if not os.path.exists(p):
        return {}
    try:
        doc = json.load(open(p, encoding='utf-8'))
        return {str(k): float(v['factor_shrunk']) for k, v in (doc.get('members') or {}).items()}
    except Exception as exc:
        raise ValueError('primacy_factors.json is present but invalid; refusing to treat '
                         'malformed primacy evidence as absent') from exc


def load_open_breaches(root, path=None):
    """{member: {'effective_severity': float, 'events': [(event_id, severity, mult)]}}.

    Sums severity x leverage_mult over OPEN events. Missing file -> {} (no gating).
    A missing `leverage_mult` defaults to 1.0 — the neutral multiplier, so an event logged
    without one still counts at face severity rather than vanishing."""
    p = os.path.join(root, path or LEDGER_PATH)
    out = {}
    if not os.path.exists(p):
        return out
    with open(p, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            if str(ev.get('status', 'open')) != 'open':
                continue
            sev = float(ev.get('severity', 0) or 0)
            if sev <= 0:
                continue
            mult = float(ev.get('leverage_mult', 1.0) or 1.0)
            rec = out.setdefault(str(ev.get('member')), {'effective_severity': 0.0, 'events': []})
            rec['effective_severity'] += sev * mult
            rec['events'].append((str(ev.get('event_id')), sev, mult))
    for rec in out.values():
        rec['effective_severity'] = round(rec['effective_severity'], 4)
    return out


def load_delivery_credit(root, path=None):
    """{member: {'delivered': float, 'events': [(event_id, bill, class, credit)]}}.

    The POSITIVE mirror of the grievance ledger: institutional effort SPENT on the agenda,
    priced by the beneficiary class of the bill so that moving a crypto bill earns nothing.
    Missing file -> {} (no offsets, ladder behaves as before). Each row already carries its
    own `delivered_credit`; it is recomputed here only if absent.

    Delivery offsets conduct. It does NOT enter the primacy factor and does NOT change any
    score — primacy answers "champion for whom", delivery answers "did you spend your
    position." Mixing them would corrupt the beneficiary ratio."""
    p = os.path.join(root, path or DELIVERY_PATH)
    out = {}
    if not os.path.exists(p):
        return out
    with open(p, encoding='utf-8') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            if str(ev.get('status', 'open')) != 'open':
                continue
            credit = ev.get('delivered_credit')
            if credit is None:
                credit = float(ev.get('act_weight', 0.0) or 0.0) * float(ev.get('instrument_mult', 0.0) or 0.0)
            credit = float(credit)
            if credit <= 0:                       # out-of-universe / offtopic rows carry 0.0
                continue
            rec = out.setdefault(str(ev.get('member')), {'delivered': 0.0, 'events': []})
            rec['delivered'] += credit
            rec['events'].append((str(ev.get('event_id')), str(ev.get('bill')),
                                  str(ev.get('beneficiary_class')), credit))
    for rec in out.values():
        rec['delivered'] = round(rec['delivered'], 4)
    return out


def tier_ceiling(effective_severity, ladder=CONDUCT_LADDER):
    """Best tier a member may occupy. 1 = unconstrained, 0 = untiered. Monotone in severity."""
    for threshold, ceiling in ladder:
        if effective_severity >= threshold:
            return ceiling
    return 1


def _cutoffs(buckets):
    """(12, 24, 48) sizes -> (12, 36, 84) cumulative cutoffs. Same derivation as tier_util L187."""
    b1, b2, b3 = buckets
    return b1, b1 + b2, b1 + b2 + b3


def _first_slot_of_tier(tier, buckets):
    """First slot index a member of this ceiling may occupy. `buckets` is SIZES, not cutoffs."""
    c1, c2, c3 = _cutoffs(buckets)
    return {1: 0, 2: c1, 3: c2}.get(tier, c3)


def primacy_scores(pcts, factors):
    """score = Leg% x primacy factor. Press weight is 0.00 in this policy.
    A member absent from `factors` keeps a neutral 1.0 (never silently zeroed)."""
    out = {}
    for member, values in (pcts or {}).items():
        try:
            leg = float(values['leg'])
        except (KeyError, TypeError, ValueError):
            continue
        out[member] = leg * float(factors.get(member, 1.0))
    return out


def apply_conduct_ladder(order, breaches, delivered=None, buckets=None):
    """Re-seat `order` (best-first) honoring each member's NET conduct ceiling.

        net_severity = effective_severity  -  delivered_credit

    Greedy and stable: walk the slots in order and take the best-scoring unplaced member
    permitted in that slot. Equivalent to giving each member a minimum slot index and
    otherwise preserving score order — so the ladder can only ever push a member DOWN,
    never up, and an uncapped member never loses a seat to a capped one. Delivery credit
    can therefore only ever RESTORE a member toward their own score position; it can never
    lift anyone above it, and a member with delivery but no grievance is unaffected.

    `buckets` is the SIZES tuple (12, 24, 48), i.e. tier_util's own BUCKETS. Defaults to it.

    Returns (final_order, detail). `detail` covers every member with a grievance OR a
    delivery record, so the desk can render both sides of the ledger."""
    if buckets is None:
        buckets = BUCKETS          # tier_util.BUCKETS — sizes (12, 24, 48)
    delivered = delivered or {}
    floor = {}
    detail = {}
    for m in order:
        g = breaches.get(m)
        d = delivered.get(m)
        if not g and not d:
            continue
        gross = float(g['effective_severity']) if g else 0.0
        credit = float(d['delivered']) if d else 0.0
        net = round(gross - credit, 4)
        ceil = tier_ceiling(net)
        detail[m] = {
            'gross_severity': gross, 'delivered_credit': credit, 'net_severity': net,
            'effective_severity': net,           # back-compat alias: the value the ladder reads
            'tier_ceiling': ceil,
            'open_events': [e[0] for e in g['events']] if g else [],
            'delivery_events': [e[0] for e in d['events']] if d else [],
        }
        if ceil != 1:
            floor[m] = _first_slot_of_tier(ceil, buckets)
    if not floor:
        return list(order), detail
    remaining, final = list(order), []
    for slot in range(len(order)):
        for i, m in enumerate(remaining):
            if floor.get(m, 0) <= slot:
                final.append(remaining.pop(i))
                break
        else:
            break                       # everyone left is floored past the board; drop through
    final.extend(remaining)             # unreachable for buckets <= len(order); kept for totality
    return final, detail


# ---------------------------------------------------------------------------
# REPLACE the body of legislative_press_tiers() with the block below.
#
# SIGNATURE IS UNCHANGED BY DEFAULT. Seven call sites unpack a 2-tuple —
#   audit_full.py:57 · make_member_desk.py:1542 · money_response.py:15 ·
#   outcome_snapshot.py:33 · sync_stance_g.py:20 · tests/test_audit_completion_20260716.py:120 ·
#   build_dashboard_bundle.py:67 (import)
# — so the conduct detail is returned ONLY when a caller opts in with with_detail=True.
# Returning a bare 3-tuple would break all seven.
#
#     def legislative_press_tiers(members, root=None, with_detail=False):
#         root = root or _ROOT
#         with open(os.path.join(root, 'ranks_python.json'), encoding='utf-8') as handle:
#             rp = json.load(handle)
#         pcts = rp.get('pcts', {})
#
#         # NOTE: load_tier_weights() is NOT called. This policy is legislation-only
#         # (press weight 0.00) and load_tier_weights() raises on a non-positive weight.
#         # Leave the ratified 0.84/0.16 in tier_overrides.json untouched — other code and
#         # tests/test_audit_completion_20260716.py:96 still read it.
#         factors   = load_primacy_factors(root)         # {} -> fail open to pure Leg%
#         breaches  = load_open_breaches(root)
#         delivered = load_delivery_credit(root)
#         all_scores = primacy_scores(pcts, factors)
#
#         rankable    = [m for m in members if m in all_scores]
#         score_order = sorted(rankable, key=lambda m: (-all_scores[m], m))  # deterministic tie-break
#         order       = apply_tier_overrides(score_order, load_tier_overrides(),
#                                            positions=load_tier_positions())
#
#         final, detail = apply_conduct_ladder(order, breaches, delivered)   # buckets defaults to BUCKETS
#
#         b1, b2, b3 = BUCKETS[0], BUCKETS[0] + BUCKETS[1], BUCKETS[0] + BUCKETS[1] + BUCKETS[2]
#         tier, tierrank = {}, {}
#         for i, m in enumerate(final):
#             tierrank[m] = i + 1
#             tier[m] = 1 if i < b1 else 2 if i < b2 else 3 if i < b3 else 0
#         return (tier, tierrank, detail) if with_detail else (tier, tierrank)
#
# The desk and dashboard pass with_detail=True to render the "why not a Champion" line.
# ---------------------------------------------------------------------------
