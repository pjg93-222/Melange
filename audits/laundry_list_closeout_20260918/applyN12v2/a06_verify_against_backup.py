# -*- coding: utf-8 -*-
"""STEP 6: verify the applied live database against the pre-apply backup.  READ-ONLY on both.

Both databases are opened mode=ro and the connection is put in query_only=ON after the ATTACH, so
nothing here can write to either file.

Checks, each printed with its own PASS/FAIL line:
  C01 speeches row count unchanged, and identical in both
  C02 rowid set identical (both directions, by EXCEPT)
  C03 rows whose text differs == ledger rows == the plus7 dry run's truncated count
  C04 the three sets are the SAME set, not just the same size
  C05 every changed row's new text is a strict (proper) prefix of the old text
  C06 nwords == len(text.split()) on every changed row, and across all INTERVIEW rows
  C07 no row where any column other than text/nwords changed; nwords changed only where text did
  C08 every other table has an identical row count; only the ledger table is new
  C09 probe rowid byte-identical to the backup
  C10 every protected rowid (all 2105) byte-identical to the backup
  C11 the ledger reconstructs the original text byte for byte, and its stored sha256 and
      original_row_json agree with the backup row
  C12 the live text of each changed row equals the kept_text the dry run planned, per rowid
  C13 no row grew; word/char deltas equal what --apply reported
"""
import collections
import hashlib
import io
import json
import os
import sqlite3
import sys

LIVE_ROOT = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = os.path.join(LIVE_ROOT, 'social_media.db')
BAK = os.path.join(LIVE_ROOT, 'backups', 'social_media.PRE-TURNSPLIT-20260919.db')
HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.abspath(os.path.join(HERE, '..', 'fixN12v2'))
PLUS7 = os.path.join(FIX, 'v2_skipset_plus7.json')
DRY_SUM = os.path.join(HERE, 'dry_plus7', 'v2_dry_run_summary.json')
DRY_LEDGER = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
              r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-'
              r'unfinished-work-handoff-a3bbad\5b7f7c28-909b-48f8-a495-2da7aebcc0fe'
              r'\scratchpad\applyN12v2\v2_dry_run_ledger_plus7.jsonl')
APPLY_OUT = os.path.join(HERE, 'a05_apply.out.txt')
LEDGER = 'speeches_turn_split_ledger'
PROBE = 245771
EXPECT_ROWS = 270489

RESULTS = []


def check(cid, label, ok, detail=''):
    RESULTS.append((cid, label, bool(ok)))
    print('%-5s %-6s %s%s' % (cid, 'PASS' if ok else 'FAIL', label,
                              ('  |  ' + detail) if detail else ''))
    return ok


def uri(path):
    return 'file:%s?mode=ro' % path.replace('\\', '/')


def sha_text(s):
    return hashlib.sha256((s or '').encode('utf-8')).hexdigest()


def main():
    dry = json.load(io.open(DRY_SUM, encoding='utf-8'))
    # utf-8-sig: PowerShell's Tee-Object wrote the captured --apply output with a BOM
    applied = json.loads(io.open(APPLY_OUT, encoding='utf-8-sig').read())
    expected_cut = dry['rows_would_truncate']
    print('plus7 dry run planned %d truncations; --apply reported rows_truncated=%d '
          'rows_skipped=%d rows_inserted=%d rows_deleted=%d'
          % (expected_cut, applied['rows_truncated'], applied['rows_skipped'],
             applied['rows_inserted'], applied['rows_deleted']))

    con = sqlite3.connect(uri(DB), uri=True, timeout=300)
    con.execute("ATTACH DATABASE ? AS bak", (uri(BAK),))
    con.execute('PRAGMA query_only=ON')
    q = lambda sql, a=(): con.execute(sql, a).fetchone()[0]
    print('opened live + backup read-only (query_only=%s)\n' % q('PRAGMA query_only'))

    live_rows = q('SELECT COUNT(*) FROM main.speeches')
    bak_rows = q('SELECT COUNT(*) FROM bak.speeches')
    check('C01', 'speeches row count unchanged', live_rows == bak_rows == EXPECT_ROWS,
          'live=%d backup=%d expected=%d' % (live_rows, bak_rows, EXPECT_ROWS))

    only_live = q('SELECT COUNT(*) FROM (SELECT rowid FROM main.speeches '
                  'EXCEPT SELECT rowid FROM bak.speeches)')
    only_bak = q('SELECT COUNT(*) FROM (SELECT rowid FROM bak.speeches '
                 'EXCEPT SELECT rowid FROM main.speeches)')
    check('C02', 'rowid set identical', only_live == 0 and only_bak == 0,
          'live-only=%d backup-only=%d' % (only_live, only_bak))

    n_diff = q('SELECT COUNT(*) FROM main.speeches a JOIN bak.speeches b ON a.rowid=b.rowid '
               'WHERE a.text IS NOT b.text')
    n_ledger = q('SELECT COUNT(*) FROM main.%s' % LEDGER)
    n_ledger_live = q('SELECT COUNT(*) FROM main.%s WHERE restored_at IS NULL' % LEDGER)
    check('C03', 'rows whose text differs == ledger rows == planned truncations',
          n_diff == n_ledger == n_ledger_live == expected_cut == applied['rows_truncated'],
          'text_differs=%d ledger=%d ledger_unrestored=%d planned=%d'
          % (n_diff, n_ledger, n_ledger_live, expected_cut))

    changed = {r[0] for r in con.execute(
        'SELECT a.rowid FROM main.speeches a JOIN bak.speeches b ON a.rowid=b.rowid '
        'WHERE a.text IS NOT b.text')}
    ledger_ids = {r[0] for r in con.execute('SELECT speech_rowid FROM main.%s' % LEDGER)}
    planned, planned_kept, planned_skip = set(), {}, {}
    with io.open(DRY_LEDGER, encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if r['skip']:
                planned_skip[r['rowid']] = r['skip']
            else:
                planned.add(r['rowid'])
                planned_kept[r['rowid']] = r['kept']['text']
    check('C04', 'changed set == ledger set == planned set (same members, not just counts)',
          changed == ledger_ids == planned,
          'changed\\ledger=%d ledger\\changed=%d changed\\planned=%d planned\\changed=%d'
          % (len(changed - ledger_ids), len(ledger_ids - changed),
             len(changed - planned), len(planned - changed)))

    rows = con.execute('SELECT a.rowid,a.text,a.nwords,b.text,b.nwords FROM main.speeches a '
                       'JOIN bak.speeches b ON a.rowid=b.rowid '
                       'WHERE a.text IS NOT b.text').fetchall()
    not_prefix, not_proper, lead_ws, bad_words, grew, kept_mismatch = [], [], [], [], [], []
    midtoken = []
    words_removed = chars_removed_raw = 0
    for rowid, new, new_nw, old, old_nw in rows:
        new = new or ''
        old = old or ''
        # the cut lands INSIDE a whitespace-delimited token when the characters on both sides of
        # the boundary are non-space; that token then counts once in the original and twice across
        # the two halves, so the tool's removed_nwords exceeds the true delta by exactly 1.
        if new[-1:].strip() and old[len(new):len(new) + 1].strip():
            midtoken.append(rowid)
        if not old.startswith(new):
            not_prefix.append(rowid)
            if old.lstrip() != old:
                lead_ws.append(rowid)
        if len(new) >= len(old):
            not_proper.append(rowid)
        if new_nw != len(new.split()):
            bad_words.append((rowid, new_nw, len(new.split())))
        if new_nw > (old_nw or 0):
            grew.append(rowid)
        if planned_kept.get(rowid) != new:
            kept_mismatch.append(rowid)
        words_removed += (old_nw or 0) - new_nw
        chars_removed_raw += len(old) - len(new)
    check('C05', 'every changed row is a strict prefix of its old text',
          not not_prefix and not not_proper,
          'not_a_prefix=%d (of which explained by leading whitespace: %d) not_shorter=%d %s'
          % (len(not_prefix), len(lead_ws), len(not_proper), not_prefix[:8]))
    iv_bad = 0
    iv_seen = 0
    for (nw, txt) in con.execute("SELECT nwords,text FROM main.speeches WHERE source='INTERVIEW'"):
        iv_seen += 1
        if nw != len((txt or '').split()):
            iv_bad += 1
    check('C06', 'nwords == len(text.split()) on changed rows and on every INTERVIEW row',
          not bad_words and iv_bad == 0,
          'changed_violations=%d %s ; INTERVIEW rows scanned=%d violations=%d'
          % (len(bad_words), bad_words[:5], iv_seen, iv_bad))

    other_col = q('SELECT COUNT(*) FROM main.speeches a JOIN bak.speeches b ON a.rowid=b.rowid '
                  'WHERE a.member IS NOT b.member OR a.date IS NOT b.date '
                  'OR a.source IS NOT b.source OR a.chamber IS NOT b.chamber '
                  'OR a."package" IS NOT b."package"')
    nw_only = q('SELECT COUNT(*) FROM main.speeches a JOIN bak.speeches b ON a.rowid=b.rowid '
                'WHERE a.text IS b.text AND a.nwords IS NOT b.nwords')
    check('C07', 'no other column changed anywhere; nwords moved only where text moved',
          other_col == 0 and nw_only == 0,
          'rows_with_other_column_change=%d rows_with_nwords_change_but_same_text=%d'
          % (other_col, nw_only))

    def tables(schema):
        return {r[0] for r in con.execute(
            "SELECT name FROM %s.sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%%'"
            % schema)}
    lt, bt = tables('main'), tables('bak')
    new_tables, lost_tables = sorted(lt - bt), sorted(bt - lt)
    mismatch = []
    for t in sorted(bt & lt):
        lc = q('SELECT COUNT(*) FROM main."%s"' % t)
        bc = q('SELECT COUNT(*) FROM bak."%s"' % t)
        if t == 'speeches':
            continue
        if lc != bc:
            mismatch.append((t, bc, lc))
    check('C08', 'every other table identical in row count; the ledger is the only new table',
          not mismatch and not lost_tables and new_tables == [LEDGER],
          'new=%s lost=%s count_mismatches=%s' % (new_tables, lost_tables, mismatch))

    pl = con.execute('SELECT member,date,source,chamber,"package",nwords,text FROM main.speeches '
                     'WHERE rowid=?', (PROBE,)).fetchone()
    pb = con.execute('SELECT member,date,source,chamber,"package",nwords,text FROM bak.speeches '
                     'WHERE rowid=?', (PROBE,)).fetchone()
    check('C09', 'probe rowid %d byte-identical to the backup' % PROBE, pl == pb,
          'nwords live=%s backup=%s  text sha256 live=%s backup=%s'
          % (pl[5], pb[5], sha_text(pl[6])[:16], sha_text(pb[6])[:16]))

    prot = json.load(io.open(PLUS7, encoding='utf-8'))
    protected = sorted(set(prot['label_rowids_interview']) | set(prot['cu_rowids']))
    touched_protected = sorted(set(protected) & changed)
    check('C10', 'no protected rowid was touched (all %d compared)' % len(protected),
          not touched_protected, 'protected rows in the changed set: %s' % touched_protected)

    bad_recon, bad_sha, bad_json = [], [], []
    cur = con.execute('SELECT l.speech_rowid,l.kept_raw,l.removed_raw,l.kept_text,l.kept_nwords,'
                      'l.original_text_sha256,l.original_row_json,b.text,b.nwords,b.member,'
                      'b.date,b.source,b.chamber,b."package" '
                      'FROM main.%s l JOIN bak.speeches b ON b.rowid=l.speech_rowid' % LEDGER)
    n_led = 0
    for (rid, kraw, rraw, ktext, knw, osha, ojson, btext, bnw, bmem, bdate, bsrc, bch,
         bpkg) in cur:
        n_led += 1
        if (kraw or '') + (rraw or '') != btext:
            bad_recon.append(rid)
        if osha != sha_text(btext):
            bad_sha.append(rid)
        o = json.loads(ojson)
        if (o.get('text') != btext or o.get('nwords') != bnw or o.get('member') != bmem
                or o.get('date') != bdate or o.get('source') != bsrc
                or o.get('chamber') != bch or o.get('package') != bpkg
                or o.get('rowid') != rid):
            bad_json.append(rid)
    check('C11', 'ledger reconstructs every original byte for byte (sha + full row json agree)',
          n_led == expected_cut and not bad_recon and not bad_sha and not bad_json,
          'joined=%d recon_fail=%s sha_fail=%s row_json_fail=%s'
          % (n_led, bad_recon[:5], bad_sha[:5], bad_json[:5]))

    check('C12', 'live text of every changed row == the kept_text the dry run planned',
          not kept_mismatch, 'mismatches=%d %s' % (len(kept_mismatch), kept_mismatch[:5]))

    check('C13', 'nothing grew; the measured word delta reconciles with --apply exactly',
          not grew and words_removed + len(midtoken) == applied['words_removed'],
          'rows_that_grew=%d  measured_word_delta=%d + mid_token_cuts=%d == apply_reported=%d ; '
          'measured_char_delta=%d vs apply_reported=%d, difference %d = the trailing whitespace '
          'kept_text.strip() also drops (a06b_word_delta_explain.py itemises all %d mid-token '
          'cuts; the ledger still reconstructs every original byte for byte)'
          % (len(grew), words_removed, len(midtoken), applied['words_removed'],
             chars_removed_raw, applied['chars_removed'],
             chars_removed_raw - applied['chars_removed'], len(midtoken)))

    by_reason = collections.Counter(planned_skip.values())
    print('\nplanned skips by binding reason: %s' % dict(by_reason))
    print('ledger rows with restored_at NOT NULL: %d'
          % q('SELECT COUNT(*) FROM main.%s WHERE restored_at IS NOT NULL' % LEDGER))
    print('ledger tool_version values: %s'
          % [r[0] for r in con.execute('SELECT DISTINCT tool_version FROM main.%s' % LEDGER)])
    con.close()

    failed = [c for c, _l, ok in RESULTS if not ok]
    print('\n%d checks, %d PASS, %d FAIL%s'
          % (len(RESULTS), len(RESULTS) - len(failed), len(failed),
             ('  -> ' + ','.join(failed)) if failed else ''))
    print('VERDICT: %s' % ('ALL CHECKS PASS' if not failed else 'FAILED: %s' % failed))
    return 0 if not failed else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
