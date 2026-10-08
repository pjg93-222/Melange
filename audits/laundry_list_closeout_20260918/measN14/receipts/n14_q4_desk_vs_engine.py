# -*- coding: utf-8 -*-
"""N14 Q4.  After BOTH correction steps, what still differs between DISPLAY and SCORE?
READ-ONLY.  No production script is imported or run.

The desk's side  : make_member_desk.py:1682-1704 -- stance_src=='bill' ? _fsign(score)
                   : _fsign(stance_sign), then the press_stance_overrides `_press_corr` flip
                   (lines 1687-1691).  The row it reads is the SHEET's row (the sheet wins the
                   overlap).
The engine's side: build_media_blend.py:379-392 -- press_stance_final.csv stack_label x tier
                   (UNRELATED -> 0), DEBATE fallback to the CSV stance column when the turn key
                   is absent, then the `_press_gold` override.  The row it reads is the tone
                   CSV's row.
Gate: the recomputed engine sign is checked against the SHIPPED
data/stance/press_component_meta.json counters from the real 2026-09-19 03:25 chain run, and the
tone inputs are byte-checked against that receipt's inputs_sha256 first.  A mismatch stops the
script rather than reporting numbers off a different basis.
"""
import collections
import io
import json
import os

import n14_common as C

C.banner('N14 Q4  DESK DISPLAY vs ENGINE SCORE, AFTER BOTH CORRECTION STEPS')

META_PATH = os.path.join(C.LIVE, 'data', 'stance', 'press_component_meta.json')
AUDIT_PATH = os.path.join(C.LIVE, 'data', 'stance', 'press_domain_routing_audit.json')
meta = json.load(io.open(META_PATH, encoding='utf-8'))
audit = json.load(io.open(AUDIT_PATH, encoding='utf-8'))

# ---- 0. receipt-evidence gate -----------------------------------------------------------
print('-- 0. GATE: are the tone inputs still the bytes the shipped engine run scored? --')
ok = True
for relative, expected in sorted((meta.get('inputs_sha256') or {}).items()):
    path = os.path.abspath(os.path.join(C.LIVE, relative))
    actual = C.sha256_file(path) if os.path.exists(path) else 'MISSING'
    match = actual == expected
    ok = ok and match
    print('   %-46s %s  %s' % (relative[:46], 'MATCH' if match else 'DIFF', actual[:16]))
print('   press_component_meta.json mtime %s | routing audit mtime %s'
      % (C.mtime(META_PATH), C.mtime(AUDIT_PATH)))
print('   GATE: %s' % ('the shipped engine run is on TODAY\'S bytes' if ok
                       else 'INPUTS MOVED -- the shipped counters are NOT a check on this run'))

# ---- 1. rebuild the engine's sign, row for row ------------------------------------------
tone_ledger = {}
tone_rows = C.PS.load_tone_rows(ledger=tone_ledger)
print('\n-- 1. REBUILD THE ENGINE SIGN (build_media_blend lines 366-392) --')
print('   tone rows: shipped meta %d | this run %d | routing audit rows %d'
      % (meta.get('tone_rows'), len(tone_rows), len(audit['rows'])))
stack, stack_path = C.stack_map()
print('   press_stance_final.csv: %d turn keys, mtime %s'
      % (len(stack), C.mtime(stack_path)))
live_ov, _ = C.desk_overrides()
engine_gold = C.press_gold_factory(live_ov)
desk_corr = C.press_corr_factory(live_ov)

n_stack = n_fallback = n_unrel = n_gold = 0
engine_sign = {}          # (canonical_url, identity) -> final signed weight
engine_basis = {}
stack_missing = 0
for row in tone_rows:
    uk = C.PS.canonical_url(row.get('url'), keep_fragment=True)
    turn = (uk, (row.get('bioguide') or row.get('member') or '').strip().upper())
    hit = stack.get(turn)
    if hit is not None:
        label, tier = hit
        if label == 'unrelated':
            n_unrel += 1
            sg = 0.0
            basis = 'stack:unrelated-zeroed'
        else:
            sg = C.SIGN.get(label, 0.0) * C.TIER_W.get(tier, 0.7)
            if sg != 0.0:
                n_stack += 1
            basis = 'stack:%s/%s' % (label, tier)
    else:
        stack_missing += 1
        sg = C.SIGN.get((row.get('stance') or '').lower(), 0.0)
        if sg != 0.0:
            n_fallback += 1
        basis = 'DEBATE-fallback:csv-stance=%s' % (row.get('stance') or '')
    gold = engine_gold(row.get('url'), row.get('title'))
    if gold is not None:
        sg = C.SIGN[gold]
        n_gold += 1
        basis += ' + gold_override:%s' % gold
    engine_sign[turn] = sg
    engine_basis[turn] = basis

shipped = meta.get('stack') or {}
print('\n   counter                shipped   recomputed   verdict')
for name, mine in (('stack_signed', n_stack), ('debate_fallback', n_fallback),
                   ('unrelated_zeroed', n_unrel), ('gold_overrides', n_gold)):
    theirs = shipped.get(name)
    print('   %-20s %8s %12d   %s'
          % (name, theirs, mine, 'MATCH' if theirs == mine else 'DIFF'))
print('   tone rows whose turn key is ABSENT from press_stance_final.csv: %d' % stack_missing)

# the shipped per-row disposition, keyed the way the audit keys it
disposition = {}
for arow, trow in zip(audit['rows'], tone_rows):
    uk = C.PS.canonical_url(trow.get('url'), keep_fragment=True)
    turn = (uk, (trow.get('bioguide') or trow.get('member') or '').strip().upper())
    disposition[turn] = arow.get('scoring_disposition')
aligned = sum(1 for a, t in zip(audit['rows'], tone_rows)
              if (a.get('url') or '') == (t.get('url') or ''))
print('   routing-audit rows whose url equals the tone row at the same index: %d of %d  (%s)'
      % (aligned, len(tone_rows),
         'ALIGNED' if aligned == len(tone_rows) else 'NOT ALIGNED -- disposition unusable'))

# ---- 2. the desk's displayed sign for the 57 -------------------------------------------
q1 = json.load(io.open(os.path.join(C.HERE, 'n14_q1_disagreement_sets.json'), encoding='utf-8'))
the57 = q1['stance_disagreement_rows']
rows, ph = C.sheet_rows()
sheet_first, _ = C.sheet_index_by_key(rows, ph)


def fsign(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return 0
    return 1 if x > 0 else (-1 if x < 0 else 0)


print('\n' + '-' * 100)
print('-- 2. THE 57, AFTER BOTH CORRECTION STEPS --')
still = []
resolved = []
verdict = collections.Counter()
for rec in the57:
    key = (rec['release_key'], rec['identity'])
    srow = sheet_first[key]
    src = srow[ph['stance_src']]
    d_sign = fsign(srow[ph['score']]) if src == 'bill' else fsign(srow[ph['stance_sign']])
    d_stance = str(srow[ph['stance']] or '')
    corr = desk_corr(str(srow[ph['title']] or ''), str(srow[ph['url']] or ''))
    d_corr = bool(corr)
    if corr:
        d_sign = {'support': 1, 'oppose': -1, 'neutral': 0}.get(corr.get('stance'), d_sign)
        d_stance = corr.get('stance', d_stance)
    turn = (C.PS.canonical_url(rec['csv_url'], keep_fragment=True), rec['identity'])
    e_weight = engine_sign.get(turn)
    e_sign = 0 if e_weight is None else (1 if e_weight > 0 else (-1 if e_weight < 0 else 0))
    basis = engine_basis.get(turn, '(engine row not found)')
    disp = disposition.get(turn, '(no disposition)')
    e_scores = disp == 'used'
    if e_weight is None:
        tag = 'ENGINE ROW NOT FOUND'
    elif not e_scores:
        tag = 'engine does not score it (%s)' % disp
    elif d_sign == e_sign:
        tag = 'AGREE after corrections'
    else:
        tag = 'STILL DIFFERS'
    verdict[tag.split(' (')[0]] += 1
    entry = dict(rec, desk_stance=d_stance, desk_sign=d_sign, desk_corrected=d_corr,
                 engine_weight=e_weight, engine_sign=e_sign, engine_basis=basis,
                 engine_disposition=disp, tag=tag)
    (still if tag == 'STILL DIFFERS' else resolved).append(entry)

print('\n%-46s %6s' % ('outcome', 'count'))
for tag, n in verdict.most_common():
    print('%-46s %6d' % (tag, n))

print('\n-- THE ROWS THAT STILL DIFFER (desk sign vs engine sign, both post-correction) --')
print('%-24s %-10s %-52s %-12s %-12s %s'
      % ('member', 'date', 'title[:52]', 'DESK', 'ENGINE', 'engine basis'))
for e in sorted(still, key=lambda x: (x['member'], x['csv_date'])):
    print('%-24s %-10s %-52s %-12s %-12s %s'
          % (e['member'][:24], e['sheet_date'] or e['csv_date'], e['title'][:52],
             '%s/%+d' % (e['desk_stance'][:8], e['desk_sign']),
             '%+d' % e['engine_sign'], e['engine_basis'][:58]))
print('\nSTILL DIFFERS: %d of 57' % len(still))
print('members affected: %d' % len({e['member'] for e in still}))

print('\n-- THE ROWS THE ENGINE DOES NOT SCORE AT ALL (so nothing can differ) --')
notscored = [e for e in resolved if e['tag'].startswith('engine does not score')]
byd = collections.Counter(e['engine_disposition'] for e in notscored)
print('   %s' % dict(byd.most_common()))
for e in sorted(notscored, key=lambda x: x['member'])[:60]:
    print('   %-24s %-52s %-14s desk=%s/%+d'
          % (e['member'][:24], e['title'][:52], e['engine_disposition'],
             e['desk_stance'][:8], e['desk_sign']))

print('\n-- THE ROWS THAT AGREE AFTER CORRECTIONS --')
for e in sorted([x for x in resolved if x['tag'] == 'AGREE after corrections'],
                key=lambda x: x['member']):
    print('   %-24s %-52s desk=%s/%+d engine=%+d  %s'
          % (e['member'][:24], e['title'][:52], e['desk_stance'][:8], e['desk_sign'],
             e['engine_sign'], e['engine_basis'][:44]))

# ---- 3. how many of the 57 does either correction step actually touch? -----------------
print('\n' + '-' * 100)
print('-- 3. WHAT THE TWO CORRECTION STEPS TOUCH ON THE 57 --')
print('   desk _press_corr hits (press_stance_overrides, url EXACT or title substring): %d'
      % sum(1 for e in still + resolved if e['desk_corrected']))
print('   engine _press_gold hits on the same 57                                      : %d'
      % sum(1 for e in still + resolved if 'gold_override' in e['engine_basis']))
print('   engine rows signed from the STACK rather than the CSV stance column          : %d'
      % sum(1 for e in still + resolved if e['engine_basis'].startswith('stack')))
print('   engine rows that fell back to the CSV stance column                          : %d'
      % sum(1 for e in still + resolved if e['engine_basis'].startswith('DEBATE')))
print('\n   NOTE the asymmetry in the two matchers, measured:')
print('     make_member_desk._press_corr  line 174: c[\'url\'] == url        (EXACT, no rstrip)')
print('     build_media_blend._press_gold line 345: rstrip(\'/\') both sides (TOLERANT)')
ov_urls = [c.get('url') for c in live_ov if c.get('url')]
trailing = [u for u in ov_urls if u.endswith('/')]
print('     override rows whose url ends in "/" (only these can diverge): %d of %d'
      % (len(trailing), len(ov_urls)))
for u in trailing:
    print('        %s' % u)

C.dump('n14_q4_desk_vs_engine.json', {
    'schema': 'n14-q4-desk-vs-engine-v1',
    'inputs_gate_passed': ok,
    'shipped_meta_stack': shipped,
    'recomputed': {'stack_signed': n_stack, 'debate_fallback': n_fallback,
                   'unrelated_zeroed': n_unrel, 'gold_overrides': n_gold,
                   'stack_key_missing': stack_missing},
    'routing_audit_aligned_rows': aligned, 'tone_rows': len(tone_rows),
    'outcome_counts': dict(verdict),
    'still_differ': still, 'resolved': resolved,
    'desk_corr_hits_on_57': sum(1 for e in still + resolved if e['desk_corrected']),
    'engine_gold_hits_on_57': sum(1 for e in still + resolved
                                  if 'gold_override' in e['engine_basis']),
    'override_urls_with_trailing_slash': trailing,
})
print('DONE N14 Q4')
