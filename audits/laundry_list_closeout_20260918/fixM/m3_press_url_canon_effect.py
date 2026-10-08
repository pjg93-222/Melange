# -*- coding: utf-8 -*-
"""FIX A5 step 3 -- the SHIPPED release_url_key measured against LIVE.  READ-ONLY.

No producer is executed.  ``press_stream`` and ``media_rules`` are rules modules with no
top-level I/O (verified line by line); the press scoring formulas are transcribed from the
LIVE ``build_media_blend.py`` press loop (lines 354-405) so the per-row contribution of a
dropped row is computed exactly as the producer would compute it.

Because the press loop's body depends only on the row and on read-only maps keyed by
``canonical_url`` -- which this fix does NOT change -- every SURVIVING row's disposition,
routing and contribution are identical to today, and the whole effect of the fix is the
sum over the rows that ``load_tone_rows`` no longer returns.  That is what is measured.

Row-535 press-pillar weights are the ones read off the workbook in receipt
laneA/receipts/r3d_weights_and_sublayer.out.txt: 'General Credit Union' is column X, which
is OUTSIDE the E:W SUMPRODUCT range and carries no weight, so it reaches no pillar.
"""
import collections
import csv
import datetime
import io
import json
import os
import sys

LIVE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
DRAFT = r"C:\Users\pgoff\OneDrive\Desktop\Draft Systems"
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.abspath(os.path.join(HERE, os.pardir, os.pardir, os.pardir))
os.environ["MONEYBALL_ROOT"] = LIVE
os.environ["MONEYBALL_DRAFT"] = DRAFT
sys.path.insert(0, os.path.join(WT, "fec"))
csv.field_size_limit(1 << 30)
import press_stream as PS                                          # noqa: E402
import stance.media_rules as MR                                    # noqa: E402
import config_overlay as CO                                        # noqa: E402
from members.member_identity import Resolver                       # noqa: E402

# row 535 of 'Press Release - Normalized' (receipt r3d); X = General Credit Union has none.
ROW535 = {'Examination & Supervision': 0.1, 'Credit Union Capital Requirements': 0.04,
          'NCUA Budget & Share Insurance Fund': 0.1, 'Interchange': 0.3, 'Payments': 0.08,
          'Technology & Emerging Issues': 0.08, 'Fraud Prevention': 0.08,
          'Data Privacy & Cybersecurity': 0.08, 'Charter Modernization & Governance': 0.15,
          'Defense Credit Union Issues': 0.03, 'Field of Membership': 0.15,
          'Credit Union Tax Status': 0.3, 'CDFI Fund': 0.02,
          'CU-Bank Competitive Dynamics': 0.03, 'CFPB Issues & Structural Reform': 0.05,
          'Credit Card & Consumer-Fee Mandates': 0.3,
          'Telephone Consumer Protection Act': 0.03, 'Member Business Lending': 0.04,
          'Mortgage Lending & Housing': 0.08}
SIGN = {'support': 1.0, 'oppose': -1.0, 'neutral': 0.0}
TW = {'unanimous': 1.0, 'majority': 0.7, 'review': 0.35}
W3 = float(os.environ.get('PRESS_THIRD_W', '1.0'))
TODAY = datetime.date.today()

print("=" * 108)
print("M3  PRESS_URL_CANON=%s -- effect of the shipped release_url_key on LIVE" % PS.PRESS_URL_CANON)
print("=" * 108)

legacy_ledger, new_ledger = {}, {}
legacy_rows = PS.load_tone_rows(ledger=legacy_ledger, canon='1')
new_rows = PS.load_tone_rows(ledger=new_ledger)
print("\nload_tone_rows: PRESS_URL_CANON=1 -> %d rows | =2 -> %d rows"
      % (len(legacy_rows), len(new_rows)))
for name, ledger in (("canon=1", legacy_ledger), ("canon=2", new_ledger)):
    print("  %s ledger: read %d = returned %d + official_mention %d + no_url %d "
          "+ exact_url_turn %d + duplicate_url_form %d   (closes: %s)"
          % (name, ledger['rows_read'], ledger['rows_returned'],
             ledger['official_mention_skipped'], ledger['no_url_skipped'],
             ledger['exact_url_turn_collapsed'], ledger['duplicate_url_form_collapsed'],
             ledger['rows_read'] == ledger['rows_returned']
             + ledger['official_mention_skipped'] + ledger['no_url_skipped']
             + ledger['exact_url_turn_collapsed']
             + ledger['duplicate_url_form_collapsed']))

merged = new_ledger['duplicate_url_form_rows']
print("\n" + "-" * 108)
print("A.  EVERY MERGE UNDER THE NEW KEY (%d) -- complete over-merge census" % len(merged))
print("-" * 108)
known = {frozenset(g['urls']) for g in
         json.load(io.open(os.path.join(HERE, 'm1_url_form_classes.json'),
                           encoding='utf-8'))['groups']}
for entry in merged:
    pair = frozenset((entry['kept_url'], entry['dropped_url']))
    flag = "KNOWN (one of the 12)" if any(pair <= k for k in known) else "*** ADDITIONAL ***"
    print("  %-22s %-12s %s" % ((entry['member'] or '')[:22], entry['date'] or '', flag))
    print("      title : %s" % (entry['title'] or '')[:100])
    print("      kept  : %s" % entry['kept_url'])
    print("      dropped: %s" % entry['dropped_url'])
    print("      release key: %s" % entry['release_key'])
additional = [e for e in merged
              if not any(frozenset((e['kept_url'], e['dropped_url'])) <= k for k in known)]
print("\n  merges inside the 12 known groups: %d   ADDITIONAL: %d"
      % (len(merged) - len(additional), len(additional)))

# --- the press loop's read-only maps, exactly as build_media_blend.py builds them ---------
ORIG = json.load(io.open(os.path.join(LIVE, 'data', 'stance', 'press_raw_original.json'),
                         encoding='utf-8'))
api_target = {}
api_path = os.path.join(LIVE, 'data', 'stance', 'api_press_stance.csv')
if os.path.exists(api_path):
    for r in csv.DictReader(io.open(api_path, encoding='utf-8-sig', newline='')):
        api_target[(r.get('url') or '').strip().rstrip('/')] = (r.get('api_target') or '').strip()
fulltext = PS.load_fulltext()
stk = {}
stack_path = os.path.join(LIVE, 'press_stance_final.csv')
if os.path.exists(stack_path):
    for r in csv.DictReader(io.open(stack_path, encoding='utf-8-sig', newline='')):
        key = (PS.canonical_url(r.get('url'), keep_fragment=True),
               (r.get('bioguide') or r.get('member') or '').strip().upper())
        stk[key] = ((r.get('stack_label') or '').strip().lower(),
                    (r.get('tier') or '').strip().lower())
pov = CO.merged_rows('data/stance/press_stance_overrides.json', 'corrections',
                     ('url', 'title_contains'), data_root=LIVE)
roster = json.load(io.open(os.path.join(LIVE, 'data', 'engine', 'congestion.json'),
                           encoding='utf-8'))
resolver = Resolver([x['member'] for x in roster],
                    {x['member']: x.get('bioguide') for x in roster})


def press_gold(url, title):
    ul = (url or '').strip().rstrip('/')
    tl = (title or '').lower()
    for g in pov:
        st = (g.get('stance') or '').strip().lower()
        if st not in SIGN:
            continue
        if g.get('url') and (g.get('url') or '').strip().rstrip('/') == ul:
            return st
        if g.get('title_contains') and (g.get('title_contains') or '').lower() in tl:
            return st
    return None


def pdate(value):
    for fmt in ('%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y'):
        try:
            return datetime.datetime.strptime((value or '').strip(), fmt).date()
        except ValueError:
            pass
    return None


def score_row(row):
    """build_media_blend.py:354-405, one row.  Returns (disposition, cats, contribution)."""
    uk = PS.canonical_url(row.get('url'), keep_fragment=True)
    turn = (uk, (row.get('bioguide') or row.get('member') or '').strip().upper())
    declared = [c.strip() for c in (row.get('categories') or '').split(';') if c.strip()]
    route = MR.press_routing_decision(api_target.get(uk, ''), row.get('title') or '',
                                      declared, fulltext.get(uk, ''))
    cats = [c for c in route['categories'] if c in ORIG]
    hit = stk.get(turn)
    if hit is not None:
        label, tier = hit
        if label == 'unrelated':
            return 'unrelated-zeroed', cats, {}, route['basis']
        sg = SIGN.get(label, 0.0) * TW.get(tier, 0.7)
    else:
        sg = SIGN.get((row.get('stance') or '').lower(), 0.0)
    gold = press_gold(row.get('url'), row.get('title'))
    if gold is not None:
        sg = SIGN[gold]
    member = resolver.resolve(row.get('member'), row.get('bioguide'))
    if not member:
        return 'unresolved-member', cats, {}, route['basis']
    if sg == 0.0:
        return 'neutral-zeroed', cats, {}, route['basis']
    try:
        pv = min(3.0, abs(float(row.get('press_value'))))
    except (TypeError, ValueError):
        pv = 0.0
    if pv == 0.0:
        return 'zero-intensity', cats, {}, route['basis']
    day = pdate(row.get('date'))
    if day is not None:
        dec = 0.5 ** (max(0.0, (TODAY - day).days / 365.25) / 2.0)
    else:
        try:
            dec = max(0.0, min(1.0, float(row.get('recency_weight') or 0.5)))
        except (TypeError, ValueError):
            dec = 0.5
    if not cats:
        return 'no-policy-domain', cats, {}, route['basis']
    ul = (row.get('url') or '').lower()
    cw = 1.0 if ('.house.gov' in ul or '.senate.gov' in ul) else W3
    return 'used', cats, {(c, member): sg * pv * dec * cw / len(cats) for c in cats}, \
        route['basis']


by_url_identity = {}
for row in legacy_rows:
    by_url_identity[(PS.canonical_url(row.get('url'), keep_fragment=True),
                     (row.get('bioguide') or row.get('member') or '').strip().upper())] = row
dropped = []
kept_keys = {(PS.canonical_url(r.get('url'), keep_fragment=True),
              (r.get('bioguide') or r.get('member') or '').strip().upper()) for r in new_rows}
for key, row in by_url_identity.items():
    if key not in kept_keys:
        dropped.append(row)
print("\nrows that no longer reach build_media_blend: %d" % len(dropped))

print("\n" + "-" * 108)
print("B.  DISPOSITION OF EACH DROPPED ROW AND OF THE ROW THAT SURVIVES IN ITS PLACE")
print("-" * 108)
delta = collections.defaultdict(float)
pillar_movers = collections.defaultdict(float)
for entry in merged:
    kept = next((r for r in new_rows
                 if (r.get('url') or '').strip() == entry['kept_url']
                 and (r.get('bioguide') or '').strip().upper()
                 == (entry['bioguide'] or '').strip().upper()), None)
    drop = next((r for r in dropped
                 if (r.get('url') or '').strip() == entry['dropped_url']), None)
    print("  %-22s %s" % ((entry['member'] or '')[:22], (entry['title'] or '')[:74]))
    for label, row in (('KEPT   ', kept), ('DROPPED', drop)):
        if row is None:
            print("    %s (row not located)" % label)
            continue
        disposition, cats, contrib, basis = score_row(row)
        uk = PS.canonical_url(row.get('url'), keep_fragment=True)
        print("    %s %-18s basis=%-22s cats=%s  api_target=%s fulltext=%s"
              % (label, disposition, basis, cats or '[]',
                 'YES' if uk in api_target else 'no',
                 'YES' if uk in fulltext else 'no'))
        if label == 'DROPPED':
            for (cat, member), value in contrib.items():
                delta[(cat, member)] -= value
                weight = ROW535.get(cat)
                print("           removes %+.6f from press[%s][%s]  (row-535 weight %s)"
                      % (value, cat, member, weight if weight is not None
                         else 'NONE -- column X, outside E:W, reaches no pillar'))
                if weight:
                    pillar_movers[member] += abs(value) * weight

print("\n" + "-" * 108)
print("C.  PRESS-PILLAR MOVEMENT")
print("-" * 108)
print("  press-component cells that change: %d" % len(delta))
for (cat, member), value in sorted(delta.items()):
    print("    %-38s %-22s %+.6f   weight=%s"
          % (cat, member, value, ROW535.get(cat, 'NONE (col X)')))
print("\n  members whose PRESS PILLAR moves (a weighted, in-range column changes): %d"
      % len(pillar_movers))
for member, magnitude in sorted(pillar_movers.items(), key=lambda kv: -kv[1]):
    before = sum(1 for r in legacy_rows if resolver.resolve(r.get('member'),
                                                            r.get('bioguide')) == member)
    after = sum(1 for r in new_rows if resolver.resolve(r.get('member'),
                                                        r.get('bioguide')) == member)
    print("    %-22s contributing tone rows %d -> %d   |weighted delta| %.6f"
          % (member, before, after, magnitude))
print("\n  members whose only affected column is 'General Credit Union' (col X, no weight):")
for member in sorted({m for (c, m) in delta if not ROW535.get(c)}):
    before = sum(1 for r in legacy_rows if resolver.resolve(r.get('member'),
                                                            r.get('bioguide')) == member)
    after = sum(1 for r in new_rows if resolver.resolve(r.get('member'),
                                                        r.get('bioguide')) == member)
    print("    %-22s contributing tone rows %d -> %d   press pillar UNCHANGED"
          % (member, before, after))

print("\n" + "-" * 108)
print("D.  OTHER CALLERS OF load_tone_rows (row-set delta only; no key they use changes)")
print("-" * 108)
for caller in ('fec/audit/audit_full.py:506', 'fec/members/member_reference_layer.py:34',
               'fec/network/press_engagement_layer.py:25', 'fec/network/press_hcoi.py:17',
               'fec/stance/press_stance_stack.py:23 (LIVE only)',
               'fec/stance/build_media_blend.py:301'):
    print("    %-52s sees %d rows instead of %d" % (caller, len(new_rows), len(legacy_rows)))
print("    fec/collect/build_press_engine_feed.py has its OWN turn_key (line 317) built on")
print("    canonical_url(keep_fragment=False) -- untouched, so the collector is unchanged.")

print("\n" + "-" * 108)
print("E.  DOES THE REMOVED ROW MOVE A CATEGORY EXTREMUM?  (normalize_signed_extrema rescales")
print("    a whole column when its pmax/nmax moves, so this decides one cell vs one column)")
print("-" * 108)


def component(rows):
    dyn = collections.defaultdict(lambda: collections.defaultdict(float))
    for row in rows:
        disposition, cats, contrib, _basis = score_row(row)
        if disposition != 'used':
            continue
        for (cat, member), value in contrib.items():
            dyn[cat][member] += value
    return dyn


before_dyn = component(legacy_rows)
after_dyn = component(new_rows)
for cat in sorted({c for (c, _m) in delta}):
    left, right = dict(before_dyn.get(cat, {})), dict(after_dyn.get(cat, {}))


    def extrema(values):
        pmax = max((v for v in values.values() if v > 0.0), default=0.0)
        nmax = abs(min((v for v in values.values() if v < 0.0), default=0.0))
        return pmax, nmax
    lp, ln = extrema(left)
    rp, rn = extrema(right)
    norm_before = MR.normalize_signed_extrema(left)
    norm_after = MR.normalize_signed_extrema(right)
    moved = [m for m in set(norm_before) | set(norm_after)
             if abs(norm_before.get(m, 0.0) - norm_after.get(m, 0.0)) > 1e-12]
    print("  %-38s members %d | pmax %.6f->%.6f  nmax %.6f->%.6f  | extremum moved: %s"
          % (cat, len(left), lp, rp, ln, rn,
             'YES -> whole column rescales' if (lp != rp or ln != rn) else 'no'))
    print("      normalised values that change: %d of %d  %s"
          % (len(moved), len(left),
             sorted(moved)[:6] if len(moved) <= 6 else '(listed in the json)'))
    summary_moved = {"category": cat, "members": len(left), "normalised_changed": len(moved),
                     "extremum_moved": bool(lp != rp or ln != rn), "moved_members": sorted(moved)}
    print("      ", json.dumps({k: summary_moved[k] for k in
                                ("extremum_moved", "normalised_changed")}))

summary = {"legacy_rows": len(legacy_rows), "new_rows": len(new_rows),
           "merged": merged, "additional_merges": additional,
           "delta_cells": {"%s|%s" % k: v for k, v in delta.items()},
           "pillar_movers": dict(pillar_movers)}
with io.open(os.path.join(HERE, "m3_press_url_canon_effect.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, indent=1, ensure_ascii=False)
print("\nDONE M3")
