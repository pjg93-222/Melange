# -*- coding: utf-8 -*-
"""N14 final checks.  READ-ONLY.  Two things the other receipts leave unresolved:

  A. THE Q5 GAP.  Q1 measures 57 stance / 493 stance_src disagreements; Q5 measures 56 / 491
     displayed changes, and Q6 proves the 2 roster-dropped keys are in NEITHER set.  Identify the
     rows the desk's own press_stance_overrides correction neutralises, which is the only other
     way a raw disagreement can fail to reach the screen.
  B. THE OWNER-RECORD CONFLICT.  cu_stance_label_set.csv (2026-06-30) puts the owner's label on
     the CSV side for all 57.  cu_golden_labels.csv (2026-07-04, NEWER) puts it on the SHEET side
     for 4.  Print both records for those 4 verbatim, with their provenance columns, so the
     conflict is on the record.  This lane does NOT resolve it -- press classification is the
     owner's domain.
"""
import collections
import io
import json
import os

import n14_common as C

C.banner('N14 FINAL CHECKS: THE Q5 GAP AND THE OWNER-RECORD CONFLICT')

q1 = json.load(io.open(os.path.join(C.HERE, 'n14_q1_disagreement_sets.json'), encoding='utf-8'))
the57 = q1['stance_disagreement_rows']
live_ov, _ = C.desk_overrides()
desk_corr = C.press_corr_factory(live_ov)

rows, ph = C.sheet_rows()
sheet_first, _ = C.sheet_index_by_key(rows, ph)
tone_rows = C.PS.load_tone_rows()
shared = {}
for row in tone_rows:
    key = C.DPS.row_key(row.get('url'), row.get('bioguide'), row.get('member'))
    if key[0] and key in sheet_first:
        shared.setdefault(key, row)

# ---- A. the gap --------------------------------------------------------------------------
print('-- A. WHICH RAW DISAGREEMENTS THE DESK\'S OWN CORRECTION NEUTRALISES --')
print('   When _press_corr hits, the desk sets stance = the override and ssrc = \'corrected\' on')
print('   BOTH sides, so a raw disagreement on that release never reaches the screen.')
in57 = {(r['release_key'], r['identity']) for r in the57}
hits_stance = []
hits_src = []
for key, crow in shared.items():
    srow = sheet_first[key]
    title = str(srow[ph['title']] or '')
    url = str(srow[ph['url']] or '')
    corr = desk_corr(title, url)
    if not corr:
        continue
    sheet_src = str(srow[ph['stance_src']] or '').strip()
    csv_src = (crow.get('stance_src') or '').strip()
    if key in in57:
        hits_stance.append((key, srow, crow, corr))
    if sheet_src == 'debate' and csv_src == 'human_label':
        hits_src.append((key, srow, crow, corr))
print('\n   _press_corr hits inside the 57 stance disagreements : %d' % len(hits_stance))
for key, srow, crow, corr in hits_stance:
    print('      %-22s %-52s sheet=%-8s csv=%-8s override=%s'
          % (str(srow[ph['member']] or '')[:22], str(srow[ph['title']] or '')[:52],
             str(srow[ph['stance']] or ''), (crow.get('stance') or ''), corr.get('stance')))
print('   _press_corr hits inside the 493 stance_src keys     : %d' % len(hits_src))
for key, srow, crow, corr in hits_src:
    print('      %-22s %-52s override=%s (ssrc becomes \'corrected\' on both sides)'
          % (str(srow[ph['member']] or '')[:22], str(srow[ph['title']] or '')[:52],
             corr.get('stance')))
print('\n   ARITHMETIC CHECK')
print('      57 raw stance disagreements  - %d corrected = %d displayed changes   (Q5 measured 56)'
      % (len(hits_stance), 57 - len(hits_stance)))
print('      493 raw stance_src keys      - %d corrected = %d displayed changes   (Q5 measured 491)'
      % (len(hits_src), 493 - len(hits_src)))

# ---- B. the owner-record conflict --------------------------------------------------------
print('\n' + '-' * 100)
print('-- B. THE FOUR RELEASES WHERE TWO OWNER RECORDS DISAGREE --')


def url_key(value):
    return C.PS.release_url_key(value)


ls_rows = C.read_csv_rows(os.path.join(C.SCRATCH, 'cu_stance_label_set.csv'))
ls_by_url = collections.defaultdict(list)
for r in ls_rows:
    uk = url_key(r.get('url'))
    if uk:
        ls_by_url[uk].append(r)
gl_rows = C.read_csv_rows(os.path.join(C.LIVE, 'data', 'stance', 'cu_golden_labels.csv'))
gl_by_url = collections.defaultdict(list)
for r in gl_rows:
    uk = url_key(r.get('url'))
    if uk:
        gl_by_url[uk].append(r)
print('   cu_stance_label_set.csv  %s  %d rows'
      % (C.mtime(os.path.join(C.DRAFT, 'cu_stance_label_set.csv')), len(ls_rows)))
print('   cu_golden_labels.csv     %s  %d rows'
      % (C.mtime(os.path.join(C.LIVE, 'data', 'stance', 'cu_golden_labels.csv')), len(gl_rows)))
print('   cu_golden_labels source census: %s'
      % dict(collections.Counter((r.get('source') or '?') for r in gl_rows).most_common()))

conflicts = []
agree_both_csv = 0
for rec in the57:
    uks = [url_key(rec['url']), url_key(rec['csv_url'])]
    ls = [r for uk in uks for r in ls_by_url.get(uk, [])]
    gl = [r for uk in uks for r in gl_by_url.get(uk, [])]
    ls_lab = {(r.get('human_label') or '').strip().lower() for r in ls}
    gl_lab = {(r.get('label') or '').strip().lower() for r in gl}
    if not gl:
        continue
    if ls_lab and gl_lab and ls_lab != gl_lab:
        conflicts.append((rec, ls, gl))
    elif ls_lab == gl_lab:
        agree_both_csv += 1
print('\n   of the 57, releases present in BOTH owner records : %d'
      % sum(1 for rec in the57
            if (ls_by_url.get(url_key(rec['url'])) or ls_by_url.get(url_key(rec['csv_url'])))
            and (gl_by_url.get(url_key(rec['url'])) or gl_by_url.get(url_key(rec['csv_url'])))))
print('   the two records AGREE on                         : %d' % agree_both_csv)
print('   the two records CONFLICT on                      : %d' % len(conflicts))
for rec, ls, gl in conflicts:
    print('\n   %s' % ('.' * 96))
    print('   %s  |  %s' % (rec['member'], rec['title'][:72]))
    print('   url   %s' % rec['url'])
    print('   SHEET stance=%-8s  CSV stance=%-8s' % (rec['sheet_stance'], rec['csv_stance']))
    for r in ls:
        print('   cu_stance_label_set.csv  row=%-5s split=%-8s pre_label=%-8s human_label=%-8s'
              % (r.get('row'), r.get('split'), r.get('pre_label'), r.get('human_label')))
    for r in gl:
        print('   cu_golden_labels.csv     label=%-8s split=%-6s source=%-24s conflict=%-6s'
              ' review_flag=%s'
              % (r.get('label'), r.get('split'), (r.get('source') or '')[:24],
                 r.get('conflict'), r.get('review_flag')))
        print('                            gold_stance_toward_target=%-10s'
              ' gold_target_cu_valence=%-10s gold_target=%s'
              % (r.get('gold_stance_toward_target'), r.get('gold_target_cu_valence'),
                 (r.get('gold_target') or '')[:40]))
print('\n   THIS LANE DOES NOT RESOLVE THESE FOUR.  Two files both recorded by the owner give')
print('   different labels for the same release; which is current is the owner\'s call.')

# what the ENGINE actually scored for those four
stack, _ = C.stack_map()
print('\n   what the ENGINE scored for those four (press_stance_final.csv stack_label/tier):')
for rec, ls, gl in conflicts:
    turn = (C.PS.canonical_url(rec['csv_url'], keep_fragment=True), rec['identity'])
    print('      %-22s %-44s stack=%s' % (rec['member'][:22], rec['title'][:44],
                                          stack.get(turn)))

C.dump('n14_q7_gap_and_conflict.json', {
    'schema': 'n14-gap-and-conflict-v1',
    'press_corr_hits_in_57': [{'member': str(s[ph['member']] or ''),
                               'title': str(s[ph['title']] or ''),
                               'sheet_stance': str(s[ph['stance']] or ''),
                               'csv_stance': c.get('stance'),
                               'override_stance': o.get('stance')}
                              for k, s, c, o in hits_stance],
    'press_corr_hits_in_493': [{'member': str(s[ph['member']] or ''),
                                'title': str(s[ph['title']] or ''),
                                'override_stance': o.get('stance')}
                               for k, s, c, o in hits_src],
    'displayed_stance_changes': 57 - len(hits_stance),
    'displayed_stance_src_changes': 493 - len(hits_src),
    'owner_record_conflicts': [{'member': r['member'], 'title': r['title'], 'url': r['url'],
                                'sheet_stance': r['sheet_stance'],
                                'csv_stance': r['csv_stance'],
                                'label_set_human_label': [x.get('human_label') for x in ls],
                                'golden_labels_label': [x.get('label') for x in gl],
                                'golden_labels_source': [x.get('source') for x in gl],
                                'golden_labels_split': [x.get('split') for x in gl]}
                               for r, ls, gl in conflicts],
    'owner_records_agree': agree_both_csv,
})
print('DONE N14 FINAL CHECKS')
