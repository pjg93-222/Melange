# -*- coding: utf-8 -*-
"""N12-v2: WHAT EXACTLY DIFFERS after --apply then --restore?

The contract asks for a byte-for-byte restore.  At the level of the DATA that is achievable and
is proved here.  At the level of the FILE it is not, and this script says exactly why: SQLite
stamps its own counters into the 100-byte database header on every write (file change counter at
offset 24, schema cookie at 40, version-valid-for at 92), and the ledger table itself is a new
btree.  This script builds a tiny database in SCRATCH, applies, restores, drops the ledger,
VACUUMs, and prints every differing byte offset with the header field it belongs to.

Touches ONLY the directory named on the command line, which it creates.  The live database is
never opened.
"""
import hashlib
import os
import shutil
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
WT = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\unfinished-work-handoff-a3bbad'
sys.path.insert(0, os.path.join(WT, 'fec'))
from members import migrate_interview_turn_bleed as MIG   # noqa: E402

SCHEMA = ('CREATE TABLE speeches(member TEXT,date TEXT,source TEXT,chamber TEXT,'
          'package TEXT,nwords INTEGER,text TEXT)')
ROW = ('Ada Alpher', '2021-07-14', 'INTERVIEW', 'msnow', 'p', 33,
       'My own words are deliberately long enough to clear the eight-word floor here. '
       'LAWRENCE O`DONNELL, MS NOW HOST: The host speaks next and this sentence is long '
       'enough to clear the floor.')
HDR = {24: 'file change counter', 28: 'database size in pages', 40: 'schema cookie',
       44: 'schema format number', 48: 'default page cache size', 64: 'freelist page count',
       92: 'version-valid-for number', 96: 'SQLITE_VERSION_NUMBER'}


def field(off):
    for base, name in HDR.items():
        if base <= off < base + 4:
            return name
    return '(page body)' if off >= 100 else '(other header byte)'


def main(work):
    os.makedirs(work, exist_ok=True)
    db = os.path.join(work, 'hdr_work.db')
    bk = os.path.join(work, 'hdr_backup.db')
    for p in (db, bk, db + '-journal', db + '-wal', db + '-shm'):
        if os.path.exists(p):
            os.remove(p)
    con = sqlite3.connect(db)
    con.execute(SCHEMA)
    con.execute('INSERT INTO speeches VALUES (?,?,?,?,?,?,?)', ROW)
    con.commit()
    con.execute('VACUUM')
    con.close()
    orig = open(db, 'rb').read()
    shutil.copy2(db, bk)
    print('apply  :', MIG.run_apply(db, bk, protection=MIG.Protection(), roster=['Ada Alpher']))
    print('restore:', MIG.run_restore(db))
    con = sqlite3.connect(db)
    rows_now = con.execute('SELECT member,date,source,chamber,package,nwords,text '
                           'FROM speeches ORDER BY rowid').fetchall()
    con.execute('DROP TABLE %s' % MIG.LEDGER)
    con.execute('VACUUM')
    con.close()
    now = open(db, 'rb').read()
    print()
    print('speeches content identical to the original row: %s' % (rows_now == [ROW]))
    print('original sha256 %s (%d bytes)' % (hashlib.sha256(orig).hexdigest(), len(orig)))
    print('restored sha256 %s (%d bytes)' % (hashlib.sha256(now).hexdigest(), len(now)))
    diffs = [i for i in range(min(len(orig), len(now))) if orig[i] != now[i]]
    print('differing byte offsets: %s' % diffs)
    for i in diffs:
        print('   offset %4d  %02x -> %02x   %s' % (i, orig[i], now[i], field(i)))
    print('differing offsets at or past byte 100 (i.e. OUTSIDE the header): %s'
          % [i for i in diffs if i >= 100])


if __name__ == '__main__':
    main(sys.argv[1])
