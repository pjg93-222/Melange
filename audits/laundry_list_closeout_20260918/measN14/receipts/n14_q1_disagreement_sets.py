# -*- coding: utf-8 -*-
"""N14 Q1.  Reproduce the three disagreement sets and list the 57.  READ-ONLY.

Reproduces fixN1/n1_desk_press_union.py section 5 exactly, then splits the census the way the
two prior receipts disagree about: the module docstring in fec/surfaces/desk_press_source.py
says '2,376 keys ... 1,207 / 493 / 57'; fixN1/n1_desk_press_union.out.txt says '2377 shared ...
1208 / 494 / 57'.  Both are counted here -- per shared RELEASE KEY and per shared ENGINE ROW --
so which basis each published number is on is on the record.
"""
import collections
import io
import json
import os

import n14_common as C

C.banner('N14 Q1  THE THREE DISAGREEMENT SETS')
print('live root   : %s' % C.LIVE)
print('base tone   : %s' % C.PS.BASE_TONE_PATH)
print('refresh tone: %s' % C.PS.REFRESH_TONE_PATH)
print('workbook cp : %s' % C.WB_SCRATCH)
print('PRESS_URL_CANON as imported: %r' % C.PS.PRESS_URL_CANON)

rows, ph = C.sheet_rows()
print('\nsheet rows %d, header %d columns' % (len(rows), len(ph)))
first, count = C.sheet_index_by_key(rows, ph)
print('sheet release keys (billstatus rows skipped) : %d' % len(first))
print('sheet keys carrying MORE than one sheet row  : %d'
      % sum(1 for k, n in count.items() if n > 1))

tone_ledger = {}
engine_rows = C.PS.load_tone_rows(ledger=tone_ledger)
# Key every engine row ONCE: row_key() parses and rewrites the URL, so recomputing it inside a
# per-key scan is 16M regex passes.  engine_by_key preserves ingest order.
engine_keys = [C.DPS.row_key(r.get('url'), r.get('bioguide'), r.get('member'))
               for r in engine_rows]
engine_by_key = collections.defaultdict(list)
for _k, _r in zip(engine_keys, engine_rows):
    engine_by_key[_k].append(_r)
print('engine tone rows returned by load_tone_rows   : %d' % len(engine_rows))
print('  ingest: read %d -> returned %d (exact %d, url-form %d, conflict-kept %d,'
      ' official-mention %d, no-url %d)'
      % (tone_ledger['rows_read'], tone_ledger['rows_returned'],
         tone_ledger['exact_url_turn_collapsed'],
         tone_ledger['duplicate_url_form_collapsed'],
         tone_ledger['release_key_conflict_kept'],
         tone_ledger['official_mention_skipped'], tone_ledger['no_url_skipped']))

# ---- the comparison -------------------------------------------------------------------
by_row = collections.Counter()          # field -> disagreeing ENGINE ROWS
by_key = collections.defaultdict(set)   # field -> disagreeing RELEASE KEYS
shared_rows = 0
shared_keys = set()
detail = collections.defaultdict(list)  # field -> [(key, sheet, csv)]
stance_hits = []
for key, row in zip(engine_keys, engine_rows):
    sheet = first.get(key)
    if sheet is None:
        continue
    shared_rows += 1
    shared_keys.add(key)
    row_fields = []
    for field in C.DESK_READ:
        sv, ev = C.norm_field(field,
                              sheet[ph[field]] if field in ph else None,
                              row.get(field))
        if sv != ev:
            by_row[field] += 1
            by_key[field].add(key)
            detail[field].append((key, sv, ev))
            row_fields.append(field)
    if 'stance' in row_fields:
        stance_hits.append((key, sheet, row))

print('\nshared: %d ENGINE ROWS over %d distinct RELEASE KEYS  (delta %d)'
      % (shared_rows, len(shared_keys), shared_rows - len(shared_keys)))
print('\n%-14s %8s %8s' % ('field', 'by ROW', 'by KEY'))
for field, n in by_row.most_common():
    print('%-14s %8d %8d' % (field, n, len(by_key[field])))

print('\nREPRODUCTION CHECK against the two prior publications')
for field, doc_keys, receipt_rows in (('stance', 57, 57), ('stance_sign', 57, 57),
                                      ('stance_src', 493, 494), ('score_graded', 1207, 1208)):
    print('  %-13s docstring(keys)=%5d measured(keys)=%5d %s   |   receipt(rows)=%5d'
          ' measured(rows)=%5d %s'
          % (field, doc_keys, len(by_key[field]),
             'MATCH' if doc_keys == len(by_key[field]) else 'DIFF',
             receipt_rows, by_row[field],
             'MATCH' if receipt_rows == by_row[field] else 'DIFF'))

# the row/key delta, named
extra = [k for k in shared_keys if len(engine_by_key[k]) > 1]
print('\nshared keys carrying more than ONE engine row: %d' % len(extra))
for k in extra:
    ident = k[1]
    hits = engine_by_key[k]
    print('   %s  %s' % (ident, k[0][:70]))
    for h in hits:
        print('      engine row: date=%-11s title=%s' % (h.get('date'), (h.get('title') or '')[:58]))
    print('      sheet rows under this key: %d' % count.get(k, 0))

# ---- the 57 ----------------------------------------------------------------------------
print('\n' + '-' * 100)
print('-- THE %d RELEASES WHERE THE DISPLAYED STANCE DISAGREES --' % len(by_key['stance']))
print('%-26s %-10s %-70s %-34s %-22s %-22s'
      % ('member', 'date', 'title[:70]', 'url tail', 'SHEET stance/sign/src', 'CSV stance/sign/src'))
listing = []
seen_keys = set()
for key, sheet, row in sorted(stance_hits,
                              key=lambda t: (str(t[1][ph['member']] or ''), str(t[2].get('date')))):
    dup = key in seen_keys
    seen_keys.add(key)
    member = str(sheet[ph['member']] or '')
    sdate, edate = C.norm_field('date', sheet[ph['date']], row.get('date'))
    title = str(sheet[ph['title']] or '')
    url = str(sheet[ph['url']] or '')
    tail = url.rstrip('/').rsplit('/', 1)[-1]
    s_st, e_st = C.norm_field('stance', sheet[ph['stance']], row.get('stance'))
    s_sg, e_sg = C.norm_field('stance_sign', sheet[ph['stance_sign']], row.get('stance_sign'))
    s_sr, e_sr = C.norm_field('stance_src', sheet[ph['stance_src']], row.get('stance_src'))
    print('%-26s %-10s %-70s %-34s %-22s %-22s'
          % (member[:26], sdate or edate, title[:70], tail[-34:],
             '%s/%s/%s' % (s_st, s_sg, s_sr), '%s/%s/%s' % (e_st, e_sg, e_sr)))
    listing.append({
        'release_key': key[0], 'identity': key[1], 'member': member,
        'sheet_date': sdate, 'csv_date': edate,
        'title': title, 'csv_title': row.get('title'), 'url': url, 'csv_url': row.get('url'),
        'url_tail': tail, 'bioguide': str(sheet[ph['bioguide']] or ''),
        'sheet_stance': s_st, 'sheet_stance_sign': s_sg, 'sheet_stance_src': s_sr,
        'sheet_score': str(sheet[ph['score']] or ''),
        'sheet_score_graded': str(sheet[ph['score_graded']] or ''),
        'sheet_stance_conf': str(sheet[ph['stance_conf']] or ''),
        'csv_stance': e_st, 'csv_stance_sign': e_sg, 'csv_stance_src': e_sr,
        'csv_score': str(row.get('score') or ''),
        'csv_score_graded': str(row.get('score_graded') or ''),
        'csv_stance_conf': str(row.get('stance_conf') or ''),
        'csv_press_value': str(row.get('press_value') or ''),
        'second_engine_row_under_key': dup,
    })

# stance_src: quantify the 'human_label' -> 'debate' flattening the docstring names
flat = collections.Counter()
for key, sv, ev in detail['stance_src']:
    flat['sheet=%s <- csv=%s' % (sv or '(blank)', ev or '(blank)')] += 1
print('\n' + '-' * 100)
print('-- stance_src DISAGREEMENT SHAPES (%d rows / %d keys) --'
      % (by_row['stance_src'], len(by_key['stance_src'])))
for shape, n in flat.most_common():
    print('   %-46s %6d' % (shape, n))

graded = collections.Counter()
for key, sv, ev in detail['score_graded']:
    try:
        graded['sheet %s csv' % ('>' if float(sv) > float(ev) else
                                 ('<' if float(sv) < float(ev) else '='))] += 1
    except ValueError:
        graded['unparseable'] += 1
print('\n-- score_graded DISAGREEMENT DIRECTION (%d rows / %d keys) --'
      % (by_row['score_graded'], len(by_key['score_graded'])))
for shape, n in graded.most_common():
    print('   %-30s %6d' % (shape, n))
zero_csv = sum(1 for k, sv, ev in detail['score_graded'] if float(ev) == 0.0)
zero_sheet = sum(1 for k, sv, ev in detail['score_graded'] if float(sv) == 0.0)
print('   csv side is exactly 0.000000  : %6d' % zero_csv)
print('   sheet side is exactly 0.000000: %6d' % zero_sheet)

C.dump('n14_q1_disagreement_sets.json', {
    'schema': 'n14-q1-disagreement-sets-v1',
    'sheet_rows': len(rows), 'sheet_release_keys': len(first),
    'engine_tone_rows': len(engine_rows), 'tone_ingest_ledger': tone_ledger,
    'shared_engine_rows': shared_rows, 'shared_release_keys': len(shared_keys),
    'disagreement_by_engine_row': dict(by_row),
    'disagreement_by_release_key': {k: len(v) for k, v in by_key.items()},
    'stance_disagreement_rows': listing,
    'stance_src_shapes': dict(flat), 'score_graded_direction': dict(graded),
    'score_graded_csv_zero': zero_csv, 'score_graded_sheet_zero': zero_sheet,
    'keys_with_two_engine_rows': [list(k) for k in extra],
})
print('DONE N14 Q1')
