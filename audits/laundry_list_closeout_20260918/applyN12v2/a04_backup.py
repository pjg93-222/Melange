# -*- coding: utf-8 -*-
"""STEP 4: take the pre-apply backup of the live database and prove it is one.

  * REFUSES to overwrite: if the destination already exists, this script stops and changes nothing.
  * hashes the live database BEFORE the copy, hashes the copy, hashes the live database AFTER the
    copy.  All three equal => nothing wrote into the file while it was being read, so the copy is
    a consistent snapshot and not a torn one.
  * re-checks that -wal is still absent/0 bytes, because a file-copy of a WAL database with
    unflushed frames is not a backup (the tool refuses on this too).
"""
import hashlib
import io
import json
import os
import shutil
import sys

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = os.path.join(LIVE, 'social_media.db')
DEST = os.path.join(LIVE, 'backups', 'social_media.PRE-TURNSPLIT-20260919.db')
OUT = os.path.dirname(os.path.abspath(__file__))


def sha256_file(path, chunk=1 << 22):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(chunk), b''):
            h.update(block)
    return h.hexdigest()


def main():
    rec = {'db': DB, 'backup': DEST}
    if os.path.exists(DEST):
        print('REFUSED: %s already exists (%d bytes). This script never overwrites a backup.'
              % (DEST, os.path.getsize(DEST)))
        return 2
    wal = DB + '-wal'
    wal_bytes = os.path.getsize(wal) if os.path.exists(wal) else 0
    rec['wal_bytes_before_copy'] = wal_bytes
    print('-wal before the copy: %d bytes' % wal_bytes)
    if wal_bytes:
        print('REFUSED: the database has unflushed WAL frames; a file copy would not be a backup.')
        return 2

    size_before = os.path.getsize(DB)
    sha_before = sha256_file(DB)
    rec['live_bytes_before_copy'] = size_before
    rec['live_sha256_before_copy'] = sha_before
    print('live BEFORE copy  bytes=%d sha256=%s' % (size_before, sha_before))

    shutil.copyfile(DB, DEST)
    print('copied -> %s' % DEST)

    size_copy = os.path.getsize(DEST)
    sha_copy = sha256_file(DEST)
    size_after = os.path.getsize(DB)
    sha_after = sha256_file(DB)
    wal_after = os.path.getsize(wal) if os.path.exists(wal) else 0
    rec.update({'backup_bytes': size_copy, 'backup_sha256': sha_copy,
                'live_bytes_after_copy': size_after, 'live_sha256_after_copy': sha_after,
                'wal_bytes_after_copy': wal_after})
    print('backup            bytes=%d sha256=%s' % (size_copy, sha_copy))
    print('live AFTER  copy  bytes=%d sha256=%s' % (size_after, sha_after))
    print('-wal after the copy: %d bytes' % wal_after)

    size_ok = size_before == size_copy == size_after
    sha_ok = sha_before == sha_copy == sha_after
    rec['sizes_equal'] = size_ok
    rec['sha256_equal'] = sha_ok
    print('\nsizes equal (live before == backup == live after): %s' % size_ok)
    print('sha256 equal (live before == backup == live after): %s' % sha_ok)
    with io.open(os.path.join(OUT, 'a04_backup.json'), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print('wrote %s' % os.path.join(OUT, 'a04_backup.json'))
    return 0 if (size_ok and sha_ok) else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
