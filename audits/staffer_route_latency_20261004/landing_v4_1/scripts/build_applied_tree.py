"""Overlay LIVE's current bytes onto a clean export of LIVE's HEAD (3366a7840), for every file the landings landing_v2, landing_v3_ids and landing_v4 touched (read-only on LIVE; writes only under <dest>).

usage: python build_applied_tree.py <dest>      (dest holds `git archive 3366a7840 fec` already)

After this the tree is "LIVE as it is now" for every file those landings touched, terminators and all, so v4.1's own apply script can be run on it. Each copied file is checked against the
hash it must have: the post-image of the last landing that touched it (landing_v4's, where v4 touched it; otherwise landing_v3_ids's, otherwise landing_v2's). A LIVE that had moved would stop here.
Every other file of the tree is the one 3366a7840 holds, which is what LIVE holds for it too. That commit (another lane's: "Land the people-network latency work") committed exactly the 45 files
of the three landings under fec/ (as LF blobs: autocrlf) and 128 files of an audit packet outside fec/; the working files it committed were not touched, so the overlay still puts LIVE's own bytes
(with their terminators) where those 45 files are. 3248a6a02 + this overlay gives the same tree; the proof records the check.
"""
import hashlib
import json
import os
import sys

LIVE = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems'
SP = r'C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems/4f30368b-c2d1-47f6-a368-3d68b2892c85/scratchpad'
dest = os.path.abspath(sys.argv[1])
want, origin = {}, {}
for folder, name in (('landing_v2', 'route_latency.summary.json'), ('landing_v3_ids', 'ids_followup.summary.json'), ('landing_v4', 'staffer_route_v4.summary.json')):   # the later landing overrides
    for item in json.load(open(os.path.join(SP, folder, name), encoding='utf-8'))['files']:
        want[item['file']] = item['post_sha256']
        origin[item['file']] = folder
for rel, expected in sorted(want.items()):
    path = os.path.join(LIVE, *rel.split('/'))
    if not os.path.isfile(path):
        raise SystemExit('LIVE has moved: %s is missing' % rel)
    data = open(path, 'rb').read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit('LIVE has moved: %s is not the post-image of %s' % (rel, origin[rel]))
    target = os.path.join(dest, *rel.split('/'))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'wb') as handle:
        handle.write(data)
by = {}
for rel, folder in origin.items():
    by[folder] = by.get(folder, 0) + 1
print('overlaid %d files with LIVE\'s current bytes, each equal to the post-image of the last landing that touched it (%s)' % (len(want), ', '.join('%s: %d' % kv for kv in sorted(by.items()))))
