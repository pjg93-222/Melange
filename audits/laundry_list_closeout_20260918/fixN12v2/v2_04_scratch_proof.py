# -*- coding: utf-8 -*-
"""N12-v2 SCRATCH PROOF.

Copies the LIVE database into SCRATCH twice (a work copy and the backup --apply demands), runs
--apply on the WORK COPY, proves exactly what changed, then runs --restore and proves the work
copy is back.  The live database is opened read-only, once, only to copy its bytes.

WHAT IS PROVED
  * the speeches row count is unchanged (nothing inserted, nothing deleted);
  * the ONLY rows that differ are the ones the ledger names, and in those rows the ONLY columns
    that differ are `text` and `nwords`;
  * every other table's content digest is byte-identical;
  * after --restore, every table's content digest matches the pre-apply digest exactly, and the
    whole speeches projection hashes back to its original value.

A raw file sha256 cannot come back equal and this script does not pretend otherwise: SQLite
stamps its own counters into the 100-byte file header on every write.  v2_02_header_delta.py
measures that separately and shows the difference is confined to three header counters with not
one byte differing at or past offset 100.  Here the file hash is REPORTED at every stage and the
CONTENT digest is what is asserted.

Everything this script writes lives under the directory given on the command line.
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
LIVE_DB = os.path.join(LIVE_DIR, 'social_media.db')
ROSTER = os.path.join(LIVE_DIR, 'data', 'engine', 'congestion.json')
SKIPSET = os.path.join(HERE, 'v2_skipset.json')


def file_sha256(path):
    h = hashlib.sha256()
    with io.open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 22), b''):
            h.update(block)
    return h.hexdigest()


def table_names(con):
    return [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        'ORDER BY name')]


def table_digest(con, name):
    """A content digest over one table: every row, every column, in rowid order where possible."""
    h = hashlib.sha256()
    n = 0
    try:
        cur = con.execute('SELECT * FROM "%s" ORDER BY rowid' % name)
    except sqlite3.OperationalError:
        cur = con.execute('SELECT * FROM "%s"' % name)
    for row in cur:
        h.update(json.dumps(row, ensure_ascii=False, default=str,
                            separators=(',', ':')).encode('utf-8', 'replace'))
        h.update(b'\n')
        n += 1
    return h.hexdigest(), n


def all_digests(path):
    con = sqlite3.connect('file:%s?mode=ro' % path.replace('\\', '/'), uri=True, timeout=300)
    con.execute('PRAGMA query_only=ON')
    out = {t: table_digest(con, t) for t in table_names(con)}
    con.close()
    return out


def speeches_rows(path):
    con = sqlite3.connect('file:%s?mode=ro' % path.replace('\\', '/'), uri=True, timeout=300)
    con.execute('PRAGMA query_only=ON')
    rows = {r[0]: r[1:] for r in con.execute(
        'SELECT rowid,member,date,source,chamber,package,nwords,text FROM speeches')}
    con.close()
    return rows


def main(work_dir):
    os.makedirs(work_dir, exist_ok=True)
    work = os.path.join(work_dir, 'social_media.WORK.db')
    backup = os.path.join(work_dir, 'social_media.BACKUP.db')
    prot = MIG.Protection.load(SKIPSET)
    roster = [m['member'] for m in json.load(io.open(ROSTER, encoding='utf-8'))]

    print('=' * 92)
    print('STAGE 0  copy the live database into SCRATCH twice (live opened read-only)')
    print('=' * 92)
    t0 = time.time()
    for dst in (work, backup):
        for extra in ('', '-wal', '-shm', '-journal'):
            if os.path.exists(dst + extra):
                os.remove(dst + extra)
        shutil.copyfile(LIVE_DB, dst)
    t_copy = time.time() - t0
    live_sha = file_sha256(LIVE_DB)
    work_sha_0 = file_sha256(work)
    backup_sha = file_sha256(backup)
    print('copy of %d bytes x2                 : %.1fs' % (os.path.getsize(LIVE_DB), t_copy))
    print('live    sha256 %s' % live_sha)
    print('work    sha256 %s  (equal to live: %s)' % (work_sha_0, work_sha_0 == live_sha))
    print('backup  sha256 %s  (equal to live: %s)' % (backup_sha, backup_sha == live_sha))

    t0 = time.time()
    before_digests = all_digests(work)
    before_rows = speeches_rows(work)
    t_digest = time.time() - t0
    print('content digest of %d tables / %d speeches rows : %.1fs'
          % (len(before_digests), len(before_rows), t_digest))

    print()
    print('=' * 92)
    print('STAGE 1  --apply on the WORK COPY')
    print('=' * 92)
    t0 = time.time()
    result = MIG.run_apply(work, backup, protection=prot, roster=roster)
    t_apply = time.time() - t0
    print('elapsed: %.1fs' % t_apply)
    print(json.dumps(result, indent=1, sort_keys=True))
    print('work sha256 after apply  %s' % file_sha256(work))

    after_rows = speeches_rows(work)
    after_digests = all_digests(work)
    con = sqlite3.connect('file:%s?mode=ro' % work.replace('\\', '/'), uri=True)
    con.execute('PRAGMA query_only=ON')
    led = {r[0]: (r[1], r[2], r[3]) for r in con.execute(
        'SELECT speech_rowid, kept_raw, removed_raw, original_text_sha256 FROM %s' % MIG.LEDGER)}
    con.close()

    print()
    print('-- row count')
    print('   before %d   after %d   UNCHANGED: %s'
          % (len(before_rows), len(after_rows), len(before_rows) == len(after_rows)))
    print('   rowid set identical (nothing inserted, nothing deleted): %s'
          % (set(before_rows) == set(after_rows)))
    changed = sorted(r for r in before_rows if before_rows[r] != after_rows[r])
    print('-- which rows changed')
    print('   rows whose stored tuple changed : %d' % len(changed))
    print('   ledger rows                     : %d' % len(led))
    print('   changed set == ledger set       : %s' % (set(changed) == set(led)))
    print('   == the migration report         : %s' % (len(changed) == result['rows_truncated']))
    COLS = ('member', 'date', 'source', 'chamber', 'package', 'nwords', 'text')
    offenders = []
    for r in changed:
        diff = {COLS[i] for i in range(len(COLS)) if before_rows[r][i] != after_rows[r][i]}
        if not diff <= {'text', 'nwords'}:
            offenders.append((r, sorted(diff)))
    print('-- which COLUMNS changed')
    print('   rows where anything other than text/nwords moved : %d  %s'
          % (len(offenders), offenders[:5]))
    bad_prefix = [r for r in changed if not before_rows[r][6].startswith(after_rows[r][6])]
    bad_nwords = [r for r in changed if after_rows[r][5] != len((after_rows[r][6] or '').split())]
    bad_recon = [r for r in changed
                 if MIG.reconstruct(led[r][0], led[r][1]) != before_rows[r][6]]
    bad_sha = [r for r in changed
               if led[r][2] != hashlib.sha256(
                   (before_rows[r][6] or '').encode('utf-8', 'replace')).hexdigest()]
    print('   new text is NOT a prefix of the old text : %d  %s' % (len(bad_prefix),
                                                                    bad_prefix[:5]))
    print('   nwords != len(text.split())              : %d  %s' % (len(bad_nwords),
                                                                    bad_nwords[:5]))
    print('   ledger does NOT reconstruct the original : %d  %s' % (len(bad_recon),
                                                                    bad_recon[:5]))
    print('   ledger original_text_sha256 mismatch     : %d  %s' % (len(bad_sha), bad_sha[:5]))
    print('-- every OTHER table')
    for t in sorted(set(before_digests) | set(after_digests)):
        b = before_digests.get(t)
        a = after_digests.get(t)
        mark = 'IDENTICAL' if b == a else ('NEW (the ledger)' if b is None else 'CHANGED')
        print('   %-34s %-18s before=%s after=%s'
              % (t, mark, (b or ('-', 0))[1], (a or ('-', 0))[1]))

    print()
    print('=' * 92)
    print('STAGE 2  --restore on the WORK COPY')
    print('=' * 92)
    t0 = time.time()
    back = MIG.run_restore(work)
    t_restore = time.time() - t0
    print('elapsed: %.1fs' % t_restore)
    print(json.dumps(back, indent=1, sort_keys=True))
    restored_rows = speeches_rows(work)
    restored_digests = all_digests(work)
    print()
    print('speeches content identical to the pre-apply state : %s'
          % (restored_rows == before_rows))
    print('speeches digest  before %s' % (before_digests['speeches'],))
    print('speeches digest  after  %s' % (restored_digests['speeches'],))
    diffs = [r for r in before_rows if before_rows[r] != restored_rows.get(r)]
    print('rows still differing after restore (must be 0)    : %d  %s' % (len(diffs), diffs[:5]))
    for t in sorted(before_digests):
        same = before_digests[t] == restored_digests.get(t)
        print('   %-34s restored identical: %s' % (t, same))
    print()
    print('work file sha256 after restore  %s' % file_sha256(work))
    print('live file sha256 (untouched)    %s  (live unchanged: %s)'
          % (file_sha256(LIVE_DB), file_sha256(LIVE_DB) == live_sha))
    print()
    print('TIMINGS  copy %.1fs | digest %.1fs | apply %.1fs | restore %.1fs'
          % (t_copy, t_digest, t_apply, t_restore))
    print('DONE')


if __name__ == '__main__':
    main(sys.argv[1])
