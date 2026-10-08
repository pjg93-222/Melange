# -*- coding: utf-8 -*-
"""N14 Q3b.  HARDEN the owner-record match.  READ-ONLY.

Q3 keyed the label set with press_stream.tone_turn_key, whose identity half is
``bioguide or member``.  The label set and the R pipeline's presentation workbooks carry NO
bioguide column, so their identity resolved to the MEMBER NAME while the 57 carry a BIOGUIDE --
every Q3 match therefore came through the TITLE fallback, and the R workbooks matched nothing at
all.  This script re-keys every owner-record source on the RELEASE URL ALONE (the member is
implied by the release) and reports, per row of the 57, whether the owner record was reached by
URL, by TITLE, or not at all -- so the load-bearing count is not resting on a title substring.

Nothing here judges a label.  It reports which source carries the owner's own recorded value.
"""
import collections
import io
import json
import os

import openpyxl

import n14_common as C

C.banner('N14 Q3b  OWNER-RECORD MATCH, RE-KEYED ON THE RELEASE URL')

q1 = json.load(io.open(os.path.join(C.HERE, 'n14_q1_disagreement_sets.json'), encoding='utf-8'))
the57 = q1['stance_disagreement_rows']


def norm_title(value):
    return ' '.join(str(value or '').split()).casefold()


def url_key(value):
    return C.PS.release_url_key(value)


# ---- the label set, re-keyed three ways -------------------------------------------------
ls_rows = C.read_csv_rows(os.path.join(C.SCRATCH, 'cu_stance_label_set.csv'))
ls_by_url = collections.defaultdict(list)
ls_by_title = collections.defaultdict(list)
for r in ls_rows:
    uk = url_key(r.get('url'))
    if uk:
        ls_by_url[uk].append(r)
    ls_by_title[norm_title(r.get('title'))].append(r)
print('cu_stance_label_set.csv  rows %d | distinct release URLs %d | distinct titles %d'
      % (len(ls_rows), len(ls_by_url), len(ls_by_title)))
print('   urls carrying MORE than one label-set row: %d'
      % sum(1 for v in ls_by_url.values() if len(v) > 1))
print('   of those, urls whose human_labels DISAGREE: %d'
      % sum(1 for v in ls_by_url.values()
            if len({(x.get('human_label') or '').strip().lower() for x in v}) > 1))

# ---- the R presentation workbooks, re-keyed on url alone --------------------------------
print('\n-- THE R PIPELINE WORKBOOKS, RE-KEYED ON URL ALONE --')
keys57_url = {url_key(r['url']): r for r in the57}
keys57_csvurl = {url_key(r['csv_url']): r for r in the57}
print('   the 57 collapse to %d distinct sheet-url keys and %d distinct csv-url keys'
      % (len(keys57_url), len(keys57_csvurl)))
r_results = {}
for label, filename in (('Draft CU_Press_Stance_Tone.xlsx', 'tone_draft.xlsx'),
                        ('LIVE  CU_Press_Stance_Tone.xlsx', 'tone_live.xlsx'),
                        ('Draft cu_press_releases_scored.xlsx', 'scored_draft.xlsx'),
                        ('LIVE  cu_press_releases_scored.xlsx', 'scored_live.xlsx'),
                        ('Draft cu_stance_label_set.xlsx', 'labelset_draft.xlsx'),
                        ('LIVE  cu_stance_label_set.xlsx', 'labelset_live.xlsx')):
    path = os.path.join(C.SCRATCH, filename)
    if not os.path.exists(path):
        continue
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    for name in wb.sheetnames:
        ws = wb[name]
        header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
        hidx = {str(h).strip().lower().replace(' ', '_'): i for i, h in enumerate(header) if h}
        col = next((c for c in ('human_label', 'stance') if c in hidx), None)
        if 'url' not in hidx or col is None:
            continue
        by_url = {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            uk = url_key(str(row[hidx['url']] or ''))
            if uk:
                by_url.setdefault(uk, row)
        agree_sheet = agree_csv = neither = found = 0
        for uk, rec in keys57_url.items():
            row = by_url.get(uk) or by_url.get(url_key(rec['csv_url']))
            if row is None:
                continue
            found += 1
            value = str(row[hidx[col]] or '').strip().lower()
            if value == rec['sheet_stance'] and value == rec['csv_stance']:
                pass
            if value == rec['sheet_stance']:
                agree_sheet += 1
            elif value == rec['csv_stance']:
                agree_csv += 1
            else:
                neither += 1
        print('   %-38s [%-20s] urls %5d | col %-11s | of 57 found %2d ->'
              ' SHEET %2d  CSV %2d  neither %2d'
              % (label, name[:20], len(by_url), col, found, agree_sheet, agree_csv, neither))
        r_results['%s::%s' % (label.strip(), name)] = {
            'urls': len(by_url), 'column': col, 'found_of_57': found,
            'matches_sheet': agree_sheet, 'matches_csv': agree_csv,
            'matches_neither': neither}
    wb.close()

# ---- the ledgers ------------------------------------------------------------------------
live_ov, _ = C.desk_overrides()
engine_gold = C.press_gold_factory(live_ov)
dash = json.load(io.open(os.path.join(C.LIVE, 'data', 'stance',
                                      'press_overrides_from_dashboard.json'),
                         encoding='utf-8')).get('corrections') or []
dash_by_url = {url_key(c.get('url')): c for c in dash if c.get('url')}
cq = C.read_csv_rows(os.path.join(C.LIVE, 'data', 'stance',
                                  'cfpb_stance_review_queue_2026-07-16.csv'))
cq_by_url = {}
for r in cq:
    ident = str(r.get('id') or '')
    if ident.startswith('http'):
        uk = url_key(ident)
        if uk:
            cq_by_url.setdefault(uk, r)
print('\nledgers: overrides %d | dashboard queue %d (url-keyed %d) | cfpb queue press rows %d'
      ' (PAUL_GOLD filled %d)'
      % (len(live_ov), len(dash), len(dash_by_url), len(cq_by_url),
         sum(1 for r in cq if (r.get('PAUL_GOLD') or '').strip())))

# ---- the adjudication -------------------------------------------------------------------
print('\n' + '-' * 100)
print('-- PER-ROW OWNER RECORD, URL FIRST, TITLE ONLY AS A NAMED FALLBACK --')
verdicts = collections.Counter()
how = collections.Counter()
sources = collections.Counter()
detail = []
for rec in the57:
    uk_sheet, uk_csv = url_key(rec['url']), url_key(rec['csv_url'])
    owner = source = match_by = None
    hit = engine_gold(rec['url'], rec['title']) or engine_gold(rec['csv_url'], rec['csv_title'])
    if hit:
        owner, source, match_by = hit, 'press_stance_overrides.json', 'ledger(url-or-title)'
    if owner is None:
        for uk in (uk_sheet, uk_csv):
            row = dash_by_url.get(uk)
            if row and (row.get('stance') or '').lower() in C.SIGN:
                owner, source, match_by = row['stance'].lower(), \
                    'press_overrides_from_dashboard.json', 'url'
                break
    if owner is None:
        for uk in (uk_sheet, uk_csv):
            row = cq_by_url.get(uk)
            if row and (row.get('PAUL_GOLD') or '').strip().lower() in C.SIGN:
                owner, source, match_by = row['PAUL_GOLD'].strip().lower(), \
                    'cfpb_stance_review_queue_2026-07-16.csv', 'url'
                break
    if owner is None:
        cands = ls_by_url.get(uk_sheet) or ls_by_url.get(uk_csv) or []
        match_by = 'url'
        if not cands:
            cands = (ls_by_title.get(norm_title(rec['title']))
                     or ls_by_title.get(norm_title(rec['csv_title'])) or [])
            match_by = 'title-fallback' if cands else None
        labels = {x for x in {(r.get('human_label') or '').strip().lower() for r in cands}
                  if x in C.SIGN}
        if len(labels) == 1:
            owner, source = labels.pop(), 'cu_stance_label_set.csv:human_label'
        elif len(labels) > 1:
            owner, source = 'AMBIGUOUS:%s' % '/'.join(sorted(labels)), \
                'cu_stance_label_set.csv:human_label'
        else:
            match_by = None
    if owner is None:
        verdict = 'no owner record found'
    elif owner.startswith('AMBIGUOUS'):
        verdict = 'owner record ambiguous'
    else:
        s_hit, c_hit = owner == rec['sheet_stance'], owner == rec['csv_stance']
        verdict = ('both' if s_hit and c_hit else
                   'CSV matches the owner record' if c_hit else
                   'sheet matches the owner record' if s_hit else 'neither')
    verdicts[verdict] += 1
    how['%s / %s' % (source or '(none)', match_by or '-')] += 1
    sources[source or '(none)'] += 1
    detail.append(dict(rec, owner_label=owner, owner_source=source,
                       owner_match_by=match_by, verdict=verdict))

print('\n%-34s %6s' % ('verdict', 'count'))
for verdict, n in verdicts.most_common():
    print('%-34s %6d' % (verdict, n))
print('\n%-58s %6s' % ('owner record source / how it was matched', 'count'))
for text, n in how.most_common():
    print('%-58s %6d' % (text, n))

print('\n-- THE AMBIGUOUS / NEITHER / NOT-FOUND ROWS, IN FULL --')
for d in detail:
    if d['verdict'] in ('owner record ambiguous', 'neither', 'no owner record found'):
        print('   %-22s %-56s' % (d['member'][:22], d['title'][:56]))
        print('      sheet=%-8s csv=%-8s owner=%-28s src=%s (%s)'
              % (d['sheet_stance'], d['csv_stance'], d['owner_label'],
                 d['owner_source'], d['owner_match_by']))
        for r in (ls_by_url.get(url_key(d['url'])) or ls_by_url.get(url_key(d['csv_url']))
                  or ls_by_title.get(norm_title(d['title'])) or []):
            print('         label-set row %-5s split=%-8s pre=%-8s human=%-8s url=%s'
                  % (r.get('row'), r.get('split'), r.get('pre_label'),
                     r.get('human_label'), (r.get('url') or '')[-52:]))

print('\n-- NEGATIVE CONTROL: does the label set ever agree with the SHEET against the CSV? --')
ctrl = collections.Counter()
for d in detail:
    if d['owner_source'] == 'cu_stance_label_set.csv:human_label' and d['owner_label']:
        if d['owner_label'].startswith('AMBIGUOUS'):
            ctrl['ambiguous'] += 1
        elif d['owner_label'] == d['csv_stance'] and d['owner_label'] == d['sheet_stance']:
            ctrl['both (impossible: the 57 disagree)'] += 1
        elif d['owner_label'] == d['csv_stance']:
            ctrl['human_label == CSV stance'] += 1
        elif d['owner_label'] == d['sheet_stance']:
            ctrl['human_label == SHEET stance'] += 1
        else:
            ctrl['human_label == neither'] += 1
print('   %s' % dict(ctrl.most_common()))
print('   A count above zero in "human_label == SHEET stance" would mean the sheet carries the')
print('   owner record for that release.  Measured: %d.' % ctrl.get('human_label == SHEET stance', 0))

print('\n-- SECOND CONTROL: on the 436 human_label keys that AGREE, does the CSV still carry')
print('   the label-set value?  (if the CSV stance is the human_label by construction, the')
print('   agreeing rows must agree with the label set too) --')
rows, ph = C.sheet_index_by_key(*C.sheet_rows())
base_rows = C.read_csv_rows(C.PS.BASE_TONE_PATH)
agree_csv = agree_sheet = agree_neither = notfound = 0
for r in base_rows:
    if (r.get('stance_src') or '').strip() != 'human_label':
        continue
    uk = url_key(r.get('url'))
    cands = ls_by_url.get(uk) or []
    labels = {x for x in {(x2.get('human_label') or '').strip().lower() for x2 in cands}
              if x in C.SIGN}
    if len(labels) != 1:
        notfound += 1
        continue
    owner = labels.pop()
    csv_stance = (r.get('stance') or '').strip().lower()
    if owner == csv_stance:
        agree_csv += 1
    else:
        agree_neither += 1
print('   base-CSV rows with stance_src=human_label: %d'
      % sum(1 for r in base_rows if (r.get('stance_src') or '').strip() == 'human_label'))
print('   of those, url-matched to exactly one label-set row: %d'
      % (agree_csv + agree_neither))
print('   CSV stance == label-set human_label : %d' % agree_csv)
print('   CSV stance != label-set human_label : %d' % agree_neither)
print('   not url-matchable in the label set  : %d' % notfound)

C.dump('n14_q3b_owner_match_hardened.json', {
    'schema': 'n14-q3b-owner-match-hardened-v1',
    'label_set_rows': len(ls_rows), 'label_set_release_urls': len(ls_by_url),
    'r_pipeline_workbooks_url_keyed': r_results,
    'verdicts': dict(verdicts), 'source_and_match_mode': dict(how),
    'negative_control': dict(ctrl),
    'human_label_csv_vs_labelset': {'csv_equals_labelset': agree_csv,
                                    'csv_differs_from_labelset': agree_neither,
                                    'not_url_matchable': notfound},
    'rows': detail,
})
print('DONE N14 Q3b')
