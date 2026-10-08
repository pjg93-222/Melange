# -*- coding: utf-8 -*-
"""N14 Q5.  If the desk rendered the OVERLAP from the CSV instead of the sheet.  READ-ONLY.

Runs the desk's OWN press loop (make_member_desk.load_press_and_bills, lifted as text -- the
module executes at import and rewrites the live desk, so it is never imported) twice over the
same 2,376 shared release keys: once on the SHEET's rows, once on the tone CSV's rows mapped into
the sheet's tuple shape by surfaces.desk_press_source._engine_tuple.  Every desk rule therefore
applies on both sides: billstatus routing, the stance_src=='bill' branch, _press_corr, PDATE
recovery, norm_cats, graded_label.

Dates are measured TWICE, because the brief's two statements are both true of different code:
  * WITH  desk_press_source.engine_date -- the shape the helper actually hands the desk today;
  * WITHOUT it -- the raw 'M/D/YYYY' the base CSV stores, which the desk's fdate() BLANKS.
"""
import ast
import collections
import io
import json
import os

import n14_common as C
from members.member_identity import Resolver

C.banner('N14 Q5  WHAT WOULD CHANGE IF THE CSV WON THE OVERLAP')

nodes, loop_src, span = C.lift_desk_pieces()
print('lifted the desk press loop from make_member_desk.py lines %d-%d' % span)

PDATE = json.load(io.open(os.path.join(C.LIVE, 'data', 'stance', 'press_date_overrides.json'),
                          encoding='utf-8'))
live_ov, wt_ov = C.desk_overrides()
print('press_date_overrides rows %d | press_stance_overrides corrections %d (production position)'
      % (len(PDATE), len(live_ov)))
bundle = json.load(io.open(os.path.join(C.LIVE, 'member_desk_bundle.json'), encoding='utf-8'))
NAMES = [m.get('name') for m in bundle.get('members') or []]
BIO = {m.get('name'): m.get('bioguide') for m in bundle.get('members') or []}
resolver = Resolver(NAMES, BIO)
print('roster %d members (shipped bundle)' % len(NAMES))

rows, ph = C.sheet_rows()
sheet_first, _ = C.sheet_index_by_key(rows, ph)
tone_rows = C.PS.load_tone_rows()
width = max(ph.values()) + 1

# the shared keys, and one CSV row per key (ingest order, first wins -- the sheet side already
# takes the first sheet row under a key, so both sides are first-wins)
csv_first = {}
for row in tone_rows:
    key = C.DPS.row_key(row.get('url'), row.get('bioguide'), row.get('member'))
    if key[0] and key in sheet_first:
        csv_first.setdefault(key, row)
shared = sorted(csv_first)
print('\nshared release keys: %d' % len(shared))

LOOP = compile(loop_src, C.DESK_SRC, 'exec')


def run(row_list):
    ns = {'os': os, 're': __import__('re'), 'PDATE': PDATE, 'PRESSOV': live_ov}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), C.DESK_SRC, 'exec'), ns)
    ns.update({
        '_press_rows': row_list,
        'pv': (lambda r, k: r[ph[k]] if k in ph else None),
        'canon': (lambda name, bioguide: resolver.resolve(name, bioguide)),
        'fdate': (lambda d: '' if d is None else
                  (str(d)[:10] if str(d)[:4].isdigit() else '')),
        'arts': {}, 'press_source_rows': 0, 'press_unknown_member': 0,
        'press_billstatus_excluded': 0,
        'exclusion_samples': {'press_unknown_member': []},
    })
    exec(LOOP, ns)
    return ns


def csv_tuple(row, normalise_date=True):
    out = [None] * width
    for name, index in ph.items():
        if name is None or name not in row:
            continue
        value = row[name]
        out[index] = (C.DPS.engine_date(value) if (name == 'date' and normalise_date) else value)
    return tuple(out)


sheet_list = [sheet_first[k] for k in shared]
csv_list_norm = [csv_tuple(csv_first[k], True) for k in shared]
csv_list_raw = [csv_tuple(csv_first[k], False) for k in shared]

ns_sheet = run(sheet_list)
ns_csv = run(csv_list_norm)
ns_csv_raw = run(csv_list_raw)
for tag, ns in (('SHEET', ns_sheet), ('CSV (engine_date applied)', ns_csv),
                ('CSV (raw M/D/YYYY)', ns_csv_raw)):
    displayed = sum(len(v) for v in ns['arts'].values())
    print('   [%-26s] rows walked %4d -> displayed %4d, unknown member %3d, billstatus %3d,'
          ' members %3d'
          % (tag, ns['press_source_rows'], displayed, ns['press_unknown_member'],
             ns['press_billstatus_excluded'], len(ns['arts'])))

# both runs walk the SAME key order, so index i on one side is index i on the other
FIELDS = ('date', 'dest', 'title', 'url', 'cats', 'pol', 'label', 'stance', 'sconf',
          'ssrc', 'corr', 'rel')


def flat(ns):
    """(member, built row) in walk order, so the two runs line up index for index."""
    out = []
    for nm, built in ns['arts'].items():
        for row in built:
            out.append((nm, row))
    return out


def by_key(ns, row_list):
    """key -> built row, by re-walking the same list and re-resolving the member."""
    out = {}
    order = []
    for i, key in enumerate(shared):
        raw = row_list[i]
        nm = resolver.resolve(raw[ph['member']], raw[ph['bioguide']])
        order.append((key, nm))
    pos = collections.defaultdict(int)
    for key, nm in order:
        if not nm:
            continue
        built = ns['arts'].get(nm) or []
        idx = pos[nm]
        if idx < len(built):
            out[key] = (nm, built[idx])
        pos[nm] += 1
    return out


sheet_by = by_key(ns_sheet, sheet_list)
csv_by = by_key(ns_csv, csv_list_norm)
csv_raw_by = by_key(ns_csv_raw, csv_list_raw)
common = sorted(set(sheet_by) & set(csv_by))
print('\nkeys built on BOTH sides (a key whose member the roster does not carry is dropped by')
print('the desk on both sides identically): %d of %d' % (len(common), len(shared)))

changed = collections.Counter()
changed_members = collections.defaultdict(set)
samples = collections.defaultdict(list)
for key in common:
    nm, a = sheet_by[key]
    _, b = csv_by[key]
    for field in FIELDS:
        if a.get(field) != b.get(field):
            changed[field] += 1
            changed_members[field].add(nm)
            if len(samples[field]) < 4:
                samples[field].append((nm, str(a.get(field))[:42], str(b.get(field))[:42]))

print('\n' + '-' * 100)
print('-- WHAT THE DESK WOULD DISPLAY DIFFERENTLY (CSV with engine_date, as the helper hands it) --')
print('%-10s %8s %9s   %s' % ('field', 'rows', 'members', 'example  sheet -> csv'))
for field, n in changed.most_common():
    ex = samples[field][0] if samples[field] else ('', '', '')
    print('%-10s %8d %9d   %-22s %r -> %r'
          % (field, n, len(changed_members[field]), ex[0][:22], ex[1], ex[2]))
if not changed:
    print('   (nothing)')

# dates, without the helper's normalisation
raw_changed = 0
raw_blanked = 0
raw_members = set()
for key in common:
    if key not in csv_raw_by:
        continue
    nm, a = sheet_by[key]
    _, b = csv_raw_by[key]
    if a.get('date') != b.get('date'):
        raw_changed += 1
        raw_members.add(nm)
        if not b.get('date'):
            raw_blanked += 1
print('\n-- DATES WITHOUT desk_press_source.engine_date (the raw base-CSV \'M/D/YYYY\') --')
print('   displayed dates that would CHANGE : %d rows across %d members'
      % (raw_changed, len(raw_members)))
print('   of those, would render BLANK      : %d' % raw_blanked)
print('   with engine_date applied          : %d rows' % changed.get('date', 0))
print('   -> the 2,138-key date figure in fec/surfaces/desk_press_source.py\'s docstring is the')
print('      RAW-shape count; engine_date is exactly what collapses it.')

# the three headline answers
print('\n' + '-' * 100)
print('-- HEADLINE --')
stance_members = changed_members['stance'] | changed_members['pol']
print('   displayed STANCE labels that change : %d rows across %d members'
      % (changed.get('stance', 0), len(changed_members['stance'])))
print('   displayed DIRECTION (pol) changes   : %d rows across %d members'
      % (changed.get('pol', 0), len(changed_members['pol'])))
print('   displayed GRADED labels that change : %d rows across %d members'
      % (changed.get('label', 0), len(changed_members['label'])))
print('   displayed DATES that change         : %d rows (engine_date) / %d rows (raw)'
      % (changed.get('date', 0), raw_changed))
print('   displayed stance_src that changes   : %d rows across %d members'
      % (changed.get('ssrc', 0), len(changed_members['ssrc'])))
print('   ANY displayed field changes         : %d rows across %d members'
      % (sum(1 for key in common
             if any(sheet_by[key][1].get(f) != csv_by[key][1].get(f) for f in FIELDS)),
         len({sheet_by[key][0] for key in common
              if any(sheet_by[key][1].get(f) != csv_by[key][1].get(f) for f in FIELDS)})))

# graded-label movement, in detail
moves = collections.Counter()
for key in common:
    nm, a = sheet_by[key]
    _, b = csv_by[key]
    if a.get('label') != b.get('label'):
        moves['%s -> %s' % (a.get('label'), b.get('label'))] += 1
print('\n-- GRADED-LABEL MOVEMENT (top 14 shapes of %d) --' % len(moves))
for shape, n in moves.most_common(14):
    print('   %-56s %6d' % (shape, n))

C.dump('n14_q5_if_csv_won.json', {
    'schema': 'n14-q5-if-csv-won-v1',
    'shared_keys': len(shared), 'keys_built_both_sides': len(common),
    'rows_changed_by_field': dict(changed),
    'members_changed_by_field': {k: sorted(v) for k, v in changed_members.items()},
    'date_without_engine_date': {'rows_changed': raw_changed,
                                 'rows_blanked': raw_blanked,
                                 'members': len(raw_members)},
    'graded_label_moves': dict(moves),
    'walk_counts': {
        'sheet': {'walked': ns_sheet['press_source_rows'],
                  'displayed': sum(len(v) for v in ns_sheet['arts'].values()),
                  'members': len(ns_sheet['arts'])},
        'csv_engine_date': {'walked': ns_csv['press_source_rows'],
                            'displayed': sum(len(v) for v in ns_csv['arts'].values()),
                            'members': len(ns_csv['arts'])},
        'csv_raw_date': {'walked': ns_csv_raw['press_source_rows'],
                         'displayed': sum(len(v) for v in ns_csv_raw['arts'].values()),
                         'members': len(ns_csv_raw['arts'])}},
})
print('DONE N14 Q5')
