"""Write SHA256SUMS.txt for the landing_v4 directory: every file except SHA256SUMS.txt itself, relative paths with forward slashes, sorted.
Check later with:  python make_sums.py --check"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANDING = os.path.dirname(HERE)
OUT = os.path.join(LANDING, 'SHA256SUMS.txt')


def listing():
    rows = []
    for folder, _dirs, names in os.walk(LANDING):
        if '__pycache__' in folder:
            continue
        for name in names:
            path = os.path.join(folder, name)
            rel = os.path.relpath(path, LANDING).replace(os.sep, '/')
            if rel == 'SHA256SUMS.txt':
                continue
            with open(path, 'rb') as handle:
                rows.append((rel, hashlib.sha256(handle.read()).hexdigest()))
    return sorted(rows)


if '--check' in sys.argv:
    want = dict((line.split(' *', 1)[1].strip(), line.split(' *', 1)[0]) for line in open(OUT, encoding='utf-8') if ' *' in line)
    have = dict(listing())
    bad = [rel for rel in sorted(set(want) | set(have)) if want.get(rel) != have.get(rel)]
    print('checked %d files: %s' % (len(have), 'all match' if not bad else 'MISMATCH %r' % bad))
    sys.exit(1 if bad else 0)
rows = listing()
with open(OUT, 'w', encoding='utf-8', newline='\n') as handle:
    for rel, digest in rows:
        handle.write('%s *%s\n' % (digest, rel))
print('wrote %d lines to %s' % (len(rows), OUT))
