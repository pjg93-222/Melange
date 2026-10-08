# -*- coding: utf-8 -*-
"""STEP 7: AFTER fingerprints.

WHY THIS IS NOT JUST ONE sha256.  The database is in WAL mode, so right after --apply part of the
committed state can still be sitting in social_media.db-wal.  A sha256 of the .db file alone would
then fingerprint a file that is NOT the whole database, and a later file-copy backup of that .db
alone would not be a backup.  So this script:

  A. fingerprints the .db as it stands, with the -wal/-shm sizes beside it, THEN
  B. runs PRAGMA wal_checkpoint(TRUNCATE) -- moves committed frames into the .db and empties the
     -wal.  It changes no logical content, and it restores the -wal-is-0-bytes precondition the
     next operator will check, THEN
  C. fingerprints the .db again, and RE-PROVES the logical state did not move across the
     checkpoint: speeches count, the 5477 changed rows, the ledger, and the probe row.
  D. re-fingerprints the interview extract + press meta, which this lane never touched.
"""
import hashlib
import io
import json
import os
import sqlite3
import sys

LIVE_ROOT = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = os.path.join(LIVE_ROOT, 'social_media.db')
BAK = os.path.join(LIVE_ROOT, 'backups', 'social_media.PRE-TURNSPLIT-20260919.db')
STANCE = os.path.join(LIVE_ROOT, 'data', 'stance')
HERE = os.path.dirname(os.path.abspath(__file__))
BEFORE = os.path.join(HERE, 'a01_before.json')
LEDGER = 'speeches_turn_split_ledger'
PROBE = 245771


def sha256_file(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(chunk), b''):
            h.update(block)
    return h.hexdigest()


def uri(path):
    return 'file:%s?mode=ro' % path.replace('\\', '/')


def sidecars(tag):
    out = {}
    for suffix in ('', '-wal', '-shm'):
        p = DB + suffix
        out[suffix or 'main'] = os.path.getsize(p) if os.path.exists(p) else None
        print('  %-8s %-24s %s' % (tag, os.path.basename(p), out[suffix or 'main']))
    return out


def logical_state():
    con = sqlite3.connect(uri(DB), uri=True, timeout=300)
    con.execute('ATTACH DATABASE ? AS bak', (uri(BAK),))
    con.execute('PRAGMA query_only=ON')
    g = lambda s: con.execute(s).fetchone()[0]
    st = {
        'speeches_rows': g('SELECT COUNT(*) FROM main.speeches'),
        'interview_rows': g("SELECT COUNT(*) FROM main.speeches WHERE source='INTERVIEW'"),
        'interview_words': g("SELECT COALESCE(SUM(nwords),0) FROM main.speeches "
                             "WHERE source='INTERVIEW'"),
        'rows_text_differs_from_backup': g(
            'SELECT COUNT(*) FROM main.speeches a JOIN bak.speeches b ON a.rowid=b.rowid '
            'WHERE a.text IS NOT b.text'),
        'ledger_rows': g('SELECT COUNT(*) FROM main.%s' % LEDGER),
        'ledger_unrestored': g('SELECT COUNT(*) FROM main.%s WHERE restored_at IS NULL' % LEDGER),
        'probe_identical_to_backup': g(
            'SELECT COUNT(*) FROM main.speeches a JOIN bak.speeches b ON a.rowid=b.rowid '
            'WHERE a.rowid=%d AND a.text IS b.text AND a.nwords IS b.nwords' % PROBE) == 1,
    }
    con.close()
    return st


def main():
    before = json.load(io.open(BEFORE, encoding='utf-8'))
    rec = {'before_db_sha256': before['db_sha256'], 'before_db_bytes': before['db_bytes']}
    print('BEFORE (recorded in a01_before.json)')
    print('  social_media.db bytes=%d sha256=%s' % (before['db_bytes'], before['db_sha256']))

    print('\nA. AFTER --apply, as it stands (WAL not yet checkpointed by me)')
    rec['after_pre_checkpoint'] = {'bytes': os.path.getsize(DB), 'sha256': sha256_file(DB),
                                  'sidecars': None}
    print('  social_media.db bytes=%d sha256=%s'
          % (rec['after_pre_checkpoint']['bytes'], rec['after_pre_checkpoint']['sha256']))
    rec['after_pre_checkpoint']['sidecars'] = sidecars('pre-ckpt')
    state_a = logical_state()
    rec['logical_state_pre_checkpoint'] = state_a
    for k, v in sorted(state_a.items()):
        print('  %-32s %s' % (k, v))

    print('\nB. PRAGMA wal_checkpoint(TRUNCATE)')
    con = sqlite3.connect(DB, timeout=300, isolation_level=None)
    res = con.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
    con.close()
    rec['wal_checkpoint_truncate'] = list(res) if res else None
    print('  returned (busy, log_frames, checkpointed_frames) = %s' % (res,))
    print('  busy=%s  -> %s' % (res[0], 'the checkpoint ran' if res[0] == 0
                                else 'BUSY: another reader blocked it, the .db is unchanged'))

    print('\nC. AFTER the checkpoint')
    rec['after'] = {'bytes': os.path.getsize(DB), 'sha256': sha256_file(DB)}
    print('  social_media.db bytes=%d sha256=%s' % (rec['after']['bytes'],
                                                   rec['after']['sha256']))
    rec['after']['sidecars'] = sidecars('post-ckpt')
    state_b = logical_state()
    rec['logical_state_after'] = state_b
    for k, v in sorted(state_b.items()):
        print('  %-32s %s' % (k, v))
    same = state_a == state_b
    rec['logical_state_unchanged_across_checkpoint'] = same
    print('  logical state identical across the checkpoint: %s' % same)
    print('  db file changed by the checkpoint: %s'
          % (rec['after']['sha256'] != rec['after_pre_checkpoint']['sha256']))

    print('\nD. interview extract + press meta -- this lane never wrote them')
    rec['stance_files_after'] = {}
    unchanged = True
    for name, b in sorted(before['stance_files'].items()):
        p = os.path.join(STANCE, name)
        e = {'bytes': os.path.getsize(p) if os.path.exists(p) else None,
             'sha256': sha256_file(p) if os.path.exists(p) else None,
             'mtime': os.path.getmtime(p) if os.path.exists(p) else None}
        rec['stance_files_after'][name] = e
        ok = (e['sha256'] == b['sha256'] and e['bytes'] == b['bytes'] and e['mtime'] == b['mtime'])
        unchanged = unchanged and ok
        print('  %-30s %s  bytes=%s sha256=%s' % (name, 'UNCHANGED' if ok else 'CHANGED',
                                                 e['bytes'], e['sha256']))
    rec['stance_files_unchanged'] = unchanged

    rec['backup'] = {'path': BAK, 'bytes': os.path.getsize(BAK), 'sha256': sha256_file(BAK)}
    print('\nbackup still intact: %s' % BAK)
    print('  bytes=%d sha256=%s' % (rec['backup']['bytes'], rec['backup']['sha256']))
    print('  equals the BEFORE fingerprint of the live database: %s'
          % (rec['backup']['sha256'] == before['db_sha256']
             and rec['backup']['bytes'] == before['db_bytes']))

    with io.open(os.path.join(HERE, 'a08_after.json'), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print('\nwrote %s' % os.path.join(HERE, 'a08_after.json'))
    ok = (same and unchanged and state_b['speeches_rows'] == 270489
          and state_b['rows_text_differs_from_backup'] == 5477
          and state_b['ledger_rows'] == 5477 and state_b['probe_identical_to_backup']
          and rec['backup']['sha256'] == before['db_sha256'])
    print('VERDICT: %s' % ('AFTER STATE CONSISTENT' if ok else 'INCONSISTENT -- read above'))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
