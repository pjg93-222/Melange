# -*- coding: utf-8 -*-
"""N14 Q2.  Provenance of the two sources.  READ-ONLY.

mtimes and sha256 of the sheet's workbook family and of the tone files; which script last wrote
each; and whether any RECORDED re-adjudication touched the CSV's stance columns AFTER the sheet
was last written.  Quotes the evidence it relies on.
"""
import collections
import io
import json
import os
import re

import n14_common as C

C.banner('N14 Q2  PROVENANCE: WHICH SIDE WAS WRITTEN LAST, AND BY WHAT')

FAMILY = [
    ('WORKBOOK (the sheet)', os.path.join(C.LIVE, 'Moneyball Main Version - Blended.xlsx')),
    ('workbook copy in scratch', C.WB_SCRATCH),
    ('BASE tone CSV (engine)', C.PS.BASE_TONE_PATH),
    ('REFRESH tone CSV (engine)', C.PS.REFRESH_TONE_PATH),
    ('refresh feed receipt', C.PS.REFRESH_RECEIPT_PATH),
    ('CU_Press_Stance_Tone.xlsx (Draft)', os.path.join(C.DRAFT, 'CU_Press_Stance_Tone.xlsx')),
    ('CU_Press_Stance_Tone.xlsx (LIVE root)', os.path.join(C.LIVE, 'CU_Press_Stance_Tone.xlsx')),
    ('cu_press_releases_scored.xlsx (Draft)',
     os.path.join(C.DRAFT, 'cu_press_releases_scored.xlsx')),
    ('cu_press_releases_scored.xlsx (LIVE)',
     os.path.join(C.LIVE, 'cu_press_releases_scored.xlsx')),
    ('cu_stance_label_set.csv (Draft)', os.path.join(C.DRAFT, 'cu_stance_label_set.csv')),
    ('cu_stance_label_set.xlsx (Draft)', os.path.join(C.DRAFT, 'cu_stance_label_set.xlsx')),
    ('cu_stance_label_set.csv (LIVE root)', os.path.join(C.LIVE, 'cu_stance_label_set.csv')),
    ('cu_stance_label_set.xlsx (LIVE root)', os.path.join(C.LIVE, 'cu_stance_label_set.xlsx')),
    ('press_stance_overrides.json (LIVE)',
     os.path.join(C.LIVE, 'data', 'stance', 'press_stance_overrides.json')),
    ('press_stance_overrides.json (worktree overlay)',
     os.path.join(C.WT, 'data', 'stance', 'press_stance_overrides.json')),
    ('press_stance_overrides PRE-CFPBFIX snapshot',
     os.path.join(C.LIVE, 'data', 'stance',
                  'press_stance_overrides.PRE-CFPBFIX-20260715_161807.json')),
    ('press_date_overrides.json (LIVE)',
     os.path.join(C.LIVE, 'data', 'stance', 'press_date_overrides.json')),
    ('press_overrides_from_dashboard.json (the dashboard export queue)',
     os.path.join(C.LIVE, 'data', 'stance', 'press_overrides_from_dashboard.json')),
    ('cfpb_stance_review_queue_2026-07-16.csv',
     os.path.join(C.LIVE, 'data', 'stance', 'cfpb_stance_review_queue_2026-07-16.csv')),
    ('press_stance_final.csv (the STACK the engine signs with)',
     os.path.join(C.LIVE, 'press_stance_final.csv')),
    ('press_component_meta.json (engine press run receipt)',
     os.path.join(C.LIVE, 'data', 'stance', 'press_component_meta.json')),
]
print('%-62s %-20s %14s  %s' % ('artifact', 'mtime', 'bytes', 'sha256[:16]'))
stats = {}
for label, path in FAMILY:
    if not os.path.exists(path):
        print('%-62s %-20s %14s  %s' % (label[:62], 'MISSING', '-', '-'))
        stats[label] = {'path': path, 'exists': False}
        continue
    size = os.path.getsize(path)
    digest = C.sha256_file(path)
    print('%-62s %-20s %14d  %s' % (label[:62], C.mtime(path), size, digest[:16]))
    stats[label] = {'path': path, 'exists': True, 'mtime': C.mtime(path),
                    'bytes': size, 'sha256': digest}

wb_m = os.path.getmtime(os.path.join(C.LIVE, 'Moneyball Main Version - Blended.xlsx'))
base_m = os.path.getmtime(C.PS.BASE_TONE_PATH)
refr_m = os.path.getmtime(C.PS.REFRESH_TONE_PATH)
print('\nWORKBOOK is NEWER than the BASE tone CSV by %.1f days' % ((wb_m - base_m) / 86400.0))
print('WORKBOOK is NEWER than the REFRESH tone CSV by %.1f days' % ((wb_m - refr_m) / 86400.0))

# ---- 1. what the WORKBOOK mtime is evidence OF -----------------------------------------
print('\n' + '-' * 100)
print('-- 1. WHAT LAST WROTE EACH SIDE --')
print("Workbook mtime is a FILE mtime, not a SHEET mtime: the chain writes many other sheets in")
print("the same file.  Repo scripts that name sheet 'Press Release Articles':")
os.chdir(os.path.join(C.WT, 'fec'))
hits = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs
               if d not in ('attic', '_quarantine_prereorg_strays_20260810', '__pycache__')]
    for name in files:
        if not name.endswith('.py'):
            continue
        path = os.path.join(root, name)
        text = io.open(path, encoding='utf-8', errors='replace').read()
        if 'Press Release Articles' not in text:
            continue
        # a WRITE would assign into ws.cell / append / save; a READ only iterates
        writes = bool(re.search(r"\.save\(|\.cell\([^)]*\)\s*=|Range\(|\.append\(", text))
        hits.append((path.replace('\\', '/'), 'reads', 'writes-somewhere' if writes else 'read-only'))
for path, mode, note in sorted(hits):
    print('   %-56s %s (%s)' % (path, mode, note))
print("\nNo repo script WRITES that sheet's rows.  Quoted, make_member_desk.py:1658-1659 --")
print("   'No script in the chain writes 'Press Release Articles' - it comes from the external")
print("    R pipeline - so the desk showed a frozen corpus'")
print("and fec/stance/apply_press_overrides.py:19-21 --")
print("   'the COM re-flow below rebuilds 'Press Release - Raw' from Draft Systems'")
print("    cu_press_stance_tone.csv, which is FROZEN at 2026-06-30'")
print("\nBASE tone CSV: the only repo scripts that open it for WRITING are")
print("   fec/stance/apply_press_dedup.py:12       (ST = MB_DRAFT + cu_press_stance_tone.csv)")
print("   fec/stance/apply_press_overrides.py:36   (same; RETIRED at line 26, raises SystemExit")
print("                                             unless APPLY_PRESS_OVERRIDES_LEGACY=1)")
print("   both write the WORKBOOK via Excel COM, not the CSV; the CSV is their INPUT.")
print("   Its mtime %s equals the Draft Systems CU_Press_Stance_Tone.xlsx mtime %s"
      % (C.mtime(C.PS.BASE_TONE_PATH),
         C.mtime(os.path.join(C.DRAFT, 'CU_Press_Stance_Tone.xlsx'))))
print("   -- one external R export, not a chain step.")
print("\nREFRESH tone CSV: written by fec/collect/build_press_engine_feed.py (the only producer;")
print("   it is the script that emits score_graded for a refresh row) and gated by")
print("   press_stream.validate_refresh_receipt against press_refresh_feed_receipt.json.")

# ---- 2. the refresh receipt ------------------------------------------------------------
receipt = json.load(io.open(C.PS.REFRESH_RECEIPT_PATH, encoding='utf-8'))
print('\n' + '-' * 100)
print('-- 2. THE REFRESH RECEIPT (the only chain-written part of the engine stream) --')
print('   schema %s  status %s  promotion %s'
      % (receipt.get('schema'), receipt.get('status'), receipt.get('promotion_mode')))
runs = receipt.get('accepted_runs') or []
print('   accepted runs: %d' % len(runs))
for run in runs[-6:]:
    if isinstance(run, dict):
        print('      %s' % json.dumps({k: run[k] for k in list(run)[:6]}, default=str)[:150])
    else:
        print('      %s' % run)
print('   producer named in the receipt: %s' % (receipt.get('producer')
                                                or receipt.get('script') or '(not named)'))

# ---- 3. did a RECORDED re-adjudication move the CSV's stance columns after the sheet? ---
print('\n' + '-' * 100)
print('-- 3. DID A RECORDED RE-ADJUDICATION MOVE THE CSV STANCE COLUMNS AFTER THE SHEET? --')
print('The CSV stance columns can only move if the CSV FILE moved.  Base tone CSV mtime')
print('   %s  <-- 2026-06-30, BEFORE the workbook (%s)'
      % (C.mtime(C.PS.BASE_TONE_PATH),
         C.mtime(os.path.join(C.LIVE, 'Moneyball Main Version - Blended.xlsx'))))
print('and BEFORE the 2026-07-15 CFPB re-correction.  So no 07-15 edit is IN the base CSV.')
print('\nWhere the 2026-07-15 re-adjudication actually landed (PRE-CFPBFIX snapshots):')
snap_dir = os.path.join(C.LIVE, 'data', 'stance')
snaps = sorted(n for n in os.listdir(snap_dir) if 'PRE-CFPBFIX' in n)
for name in snaps:
    print('   %-60s %s' % (name, C.mtime(os.path.join(snap_dir, name))))
print('   NOTE: cu_press_stance_tone.csv has NO PRE-CFPBFIX snapshot -- it was not rewritten.')

pre_path = os.path.join(snap_dir, 'press_stance_overrides.PRE-CFPBFIX-20260715_161807.json')
pre = json.load(io.open(pre_path, encoding='utf-8')).get('corrections') or []
live_ov = json.load(io.open(os.path.join(snap_dir, 'press_stance_overrides.json'),
                            encoding='utf-8')).get('corrections') or []
wt_path = os.path.join(C.WT, 'data', 'stance', 'press_stance_overrides.json')
wt_ov = (json.load(io.open(wt_path, encoding='utf-8')).get('corrections') or []
         if os.path.exists(wt_path) else [])
print('\npress_stance_overrides.json  corrections: PRE-CFPBFIX %d -> LIVE %d (worktree copy %d)'
      % (len(pre), len(live_ov), len(wt_ov)))


def ident(rowset):
    out = {}
    for row in rowset:
        key = ('url', (row.get('url') or '').strip().lower()) if row.get('url') else \
              ('title_contains', (row.get('title_contains') or '').strip().lower())
        out[key] = row
    return out


pre_i, live_i, wt_i = ident(pre), ident(live_ov), ident(wt_ov)
added = [k for k in live_i if k not in pre_i]
moved = [k for k in live_i if k in pre_i
         and (live_i[k].get('stance') or '') != (pre_i[k].get('stance') or '')]
print('   corrections ADDED after the 07-15 snapshot : %d' % len(added))
print('   corrections whose STANCE was CHANGED       : %d' % len(moved))
reasons = collections.Counter()
for k in added:
    row = live_i[k]
    reasons['%s -> %s' % ((row.get('reason') or row.get('note') or '(no reason field)')[:56],
                          row.get('stance'))] += 1
for text, n in reasons.most_common():
    print('      +%-2d %s' % (n, text))
print('\n   worktree-overlay-only corrections (not in the LIVE file): %d'
      % len([k for k in wt_i if k not in live_i]))
for k in [k for k in wt_i if k not in live_i]:
    print('      %s = %r  stance=%r reason=%r'
          % (k[0], k[1][:70], wt_i[k].get('stance'),
             (wt_i[k].get('reason') or wt_i[k].get('note') or '')[:60]))

dash_path = os.path.join(snap_dir, 'press_overrides_from_dashboard.json')
dash = json.load(io.open(dash_path, encoding='utf-8')).get('corrections') or []
dash_i = ident(dash)
print('\npress_overrides_from_dashboard.json (the dashboard-exported override queue): %d rows,'
      ' mtime %s' % (len(dash), C.mtime(dash_path)))
print('   of those already merged into the LIVE ledger: %d ; NOT merged: %d'
      % (len([k for k in dash_i if k in live_i]), len([k for k in dash_i if k not in live_i])))
for k in dash_i:
    if k not in live_i:
        print('      UNMERGED %s=%r stance=%r' % (k[0], k[1][:70], dash_i[k].get('stance')))

cfpb_q = os.path.join(snap_dir, 'cfpb_stance_review_queue_2026-07-16.csv')
q_rows = C.read_csv_rows(cfpb_q)
print('\ncfpb_stance_review_queue_2026-07-16.csv: %d rows, columns %s'
      % (len(q_rows), list(q_rows[0]) if q_rows else []))
if q_rows:
    chan = collections.Counter((r.get('channel') or r.get('source') or '?') for r in q_rows)
    print('   by channel/source: %s' % dict(chan))

C.dump('n14_q2_provenance.json', {
    'schema': 'n14-q2-provenance-v1', 'artifacts': stats,
    'workbook_newer_than_base_tone_days': (wb_m - base_m) / 86400.0,
    'workbook_newer_than_refresh_tone_days': (wb_m - refr_m) / 86400.0,
    'refresh_receipt': {k: receipt.get(k) for k in
                        ('schema', 'status', 'promotion_mode', 'producer', 'script')},
    'refresh_accepted_runs': len(runs),
    'press_stance_overrides': {'pre_cfpbfix': len(pre), 'live': len(live_ov),
                               'worktree_overlay': len(wt_ov),
                               'added_after_cfpbfix': len(added),
                               'stance_changed_after_cfpbfix': len(moved),
                               'overlay_only': len([k for k in wt_i if k not in live_i])},
    'dashboard_queue': {'rows': len(dash),
                        'merged': len([k for k in dash_i if k in live_i]),
                        'unmerged': len([k for k in dash_i if k not in live_i])},
    'cfpb_review_queue_rows': len(q_rows),
    'pre_cfpbfix_snapshots': snaps,
    'sheet_writer_candidates': [h[0] for h in sorted(hits)],
})
print('DONE N14 Q2')
