# -*- coding: utf-8 -*-
"""N12-v2 IDEMPOTENCY AT LIVE SCALE, on the SCRATCH work copy only.

The unit suite proves idempotency on a 14-row fixture.  This proves it on the real 270,489-row
database: apply, apply again (must be a no-op), restore, and confirm the speeches content digest
is back to where it started.  Also exercises the malformed-inventory refusal.

Touches only the work copy inside the directory given on the command line.  The live database is
never opened.
"""
import hashlib
import io
import json
import os
import shutil
import sqlite3
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(WT, 'fec'))
from members import migrate_interview_turn_bleed as MIG    # noqa: E402

LIVE_DIR = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
ROSTER = os.path.join(LIVE_DIR, 'data', 'engine', 'congestion.json')
SKIPSET = os.path.join(HERE, 'v2_skipset.json')


def speeches_digest(path):
    con = sqlite3.connect('file:%s?mode=ro' % path.replace('\\', '/'), uri=True, timeout=300)
    con.execute('PRAGMA query_only=ON')
    h = hashlib.sha256()
    n = 0
    for row in con.execute('SELECT rowid,member,date,source,chamber,package,nwords,text '
                           'FROM speeches ORDER BY rowid'):
        h.update(json.dumps(row, ensure_ascii=False, default=str,
                            separators=(',', ':')).encode('utf-8', 'replace'))
        n += 1
    con.close()
    return h.hexdigest(), n


def main(work_dir):
    work = os.path.join(work_dir, 'social_media.WORK.db')
    backup = os.path.join(work_dir, 'social_media.BACKUP.db')
    if not os.path.exists(work):
        raise SystemExit('run v2_04_scratch_proof.py first: %s is missing' % work)
    prot = MIG.Protection.load(SKIPSET)
    roster = [m['member'] for m in json.load(io.open(ROSTER, encoding='utf-8'))]

    print('malformed-inventory refusal:')
    bad = os.path.join(work_dir, 'not_the_inventory.json')
    with io.open(bad, 'w', encoding='utf-8') as fh:
        json.dump({'something_else': [1, 2, 3]}, fh)
    try:
        MIG.Protection.load(bad)
        print('  NOT REFUSED -- this is a defect')
    except MIG.Refused as e:
        print('  REFUSED: %s' % e)
    try:
        MIG.run_apply(work, backup, protection=None, roster=roster)
        print('  apply without an inventory was NOT refused -- this is a defect')
    except MIG.Refused as e:
        print('  apply without an inventory REFUSED: %s' % str(e)[:110])

    d0 = speeches_digest(work)
    print()
    print('start    speeches digest %s over %d rows' % d0)
    shutil.copyfile(work, backup)                    # a fresh size-matched backup
    t = time.time()
    a1 = MIG.run_apply(work, backup, protection=prot, roster=roster)
    print('apply 1  %.1fs  truncated=%d inserted=%d skipped=%d already=%d'
          % (time.time() - t, a1['rows_truncated'], a1['rows_inserted'], a1['rows_skipped'],
             a1['already_migrated']))
    d1 = speeches_digest(work)
    shutil.copyfile(work, backup)
    t = time.time()
    a2 = MIG.run_apply(work, backup, protection=prot, roster=roster)
    print('apply 2  %.1fs  truncated=%d inserted=%d skipped=%d already=%d'
          % (time.time() - t, a2['rows_truncated'], a2['rows_inserted'], a2['rows_skipped'],
             a2['already_migrated']))
    d2 = speeches_digest(work)
    print('  second apply was a no-op on the data: %s' % (d1 == d2))
    print('  second apply truncated nothing        : %s' % (a2['rows_truncated'] == 0))
    t = time.time()
    b = MIG.run_restore(work)
    print('restore  %.1fs  restored=%d' % (time.time() - t, b['rows_restored']))
    d3 = speeches_digest(work)
    print()
    print('end      speeches digest %s over %d rows' % d3)
    print('BACK TO THE STARTING CONTENT, BYTE FOR BYTE: %s' % (d3 == d0))
    print('DONE')


if __name__ == '__main__':
    main(sys.argv[1])
