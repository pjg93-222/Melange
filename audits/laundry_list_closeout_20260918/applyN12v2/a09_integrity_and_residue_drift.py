# -*- coding: utf-8 -*-
"""Post-write hygiene and the one drift the idempotency run exposed.  READ-ONLY on the data.

  1. PRAGMA integrity_check on the written database, and journal_mode after my checkpoint.
  2. RESIDUE DRIFT.  The plus7 dry run BEFORE the apply listed 807 refused rows.  A fresh dry run
     AFTER the apply flags only 657.  Nothing was written to those rows, so the difference is
     DETECTION, not data: build_lexicon() derives SPEAKER_LEX from the corpus itself, and the
     surnames that only ever appeared inside text the apply removed are no longer in the lexicon,
     so some tags in the remaining rows no longer resolve to a speaker.  This script proves the
     rows that dropped out of the residue are byte-identical to the backup, i.e. still exactly as
     the owner left them -- only less visible to a future dry run.  The full 807-row list is kept
     in applyN12v2/dry_plus7/v2_residue.jsonl.
"""
import io
import json
import os
import sqlite3
import sys

LIVE_ROOT = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = os.path.join(LIVE_ROOT, 'social_media.db')
BAK = os.path.join(LIVE_ROOT, 'backups', 'social_media.PRE-TURNSPLIT-20260919.db')
HERE = os.path.dirname(os.path.abspath(__file__))
RES_BEFORE = os.path.join(HERE, 'dry_plus7', 'v2_residue.jsonl')
RES_AFTER = os.path.join(HERE, 'dry_after', 'v2_residue.jsonl')


def uri(path):
    return 'file:%s?mode=ro' % path.replace('\\', '/')


def rowids(path):
    out = {}
    with io.open(path, encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                out[r['rowid']] = r
    return out


def main():
    con = sqlite3.connect(uri(DB), uri=True, timeout=600)
    print('journal_mode after my wal_checkpoint(TRUNCATE): %s'
          % con.execute('PRAGMA journal_mode').fetchone()[0])
    ic = [r[0] for r in con.execute('PRAGMA integrity_check')]
    print('PRAGMA integrity_check -> %s' % ic)
    integrity_ok = ic == ['ok']
    fk = con.execute('PRAGMA foreign_key_check').fetchall()
    print('PRAGMA foreign_key_check -> %s' % (fk if fk else 'no violations'))
    con.close()

    before, after = rowids(RES_BEFORE), rowids(RES_AFTER)
    gone = sorted(set(before) - set(after))
    new = sorted(set(after) - set(before))
    print('\nresidue rows planned before the apply: %d' % len(before))
    print('residue rows a fresh dry run flags now:  %d' % len(after))
    print('dropped out of the residue: %d    newly in the residue: %d' % (len(gone), len(new)))

    con = sqlite3.connect(uri(DB), uri=True, timeout=300)
    con.execute('ATTACH DATABASE ? AS bak', (uri(BAK),))
    con.execute('PRAGMA query_only=ON')
    changed = []
    for rid in gone + new:
        same = con.execute('SELECT COUNT(*) FROM main.speeches a JOIN bak.speeches b '
                           'ON a.rowid=b.rowid WHERE a.rowid=? AND a.text IS b.text '
                           'AND a.nwords IS b.nwords', (rid,)).fetchone()[0]
        if same != 1:
            changed.append(rid)
    print('of those %d rows, how many differ from the backup: %d %s'
          % (len(gone) + len(new), len(changed), changed[:10]))

    from collections import Counter
    print('\nbinding reason of the rows that dropped out: %s'
          % dict(Counter(before[r]['reason'] for r in gone)))
    print('binding reason of the 657 still flagged:      %s'
          % dict(Counter(r['reason'] for r in after.values())))
    prot_before = sum(1 for r in gone
                      if before[r]['reason'] in ('label_or_gold_record_points_here',
                                                 'credit_union_stance_channel_row'))
    print('of the rows that dropped out, protected-by-inventory ones: %d (they stay protected: '
          'the inventory is a file, not a detection)' % prot_before)
    con.close()

    ok = integrity_ok and not fk and not changed and not new
    print('\nVERDICT: %s' % ('integrity ok; the residue shrank purely by DETECTION and every '
                             'affected row is byte-identical to the backup' if ok
                             else 'see above -- something is not accounted for'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
