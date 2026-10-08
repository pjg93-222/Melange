"""Overlay LIVE's current bytes onto a clean 3248a6a02 export, for every file the three patch sets touch that LIVE already holds (read-only on LIVE; writes only under <dest>).

usage: python build_applied_tree.py <dest>      (dest holds `git archive 3248a6a02 fec` already)

"The patched files" are the 31 files landing_v2 and landing_v3_ids touched (13 + 15 from landing_v2, 5 + 2 from landing_v3_ids, 4 in both) and the 15 files v4 edits (12 of them among
those 31; the other 3 are LIVE's own files that neither landing touched: closeness_math.py, staffer_work_sources.py and test_staffer_route_models.cjs, the last of which LIVE holds with
mixed terminators where the clean export holds the pure-LF blob). After this the tree is "LIVE as it is now" for every file v4 touches, terminators and all, and v4's own apply script can be
run on it. Each copied file is checked against the hash it must have: the post-image of the last landing that touched it, or v4's own pre-image for a file neither touched, and for a file
both an earlier landing and v4 name, the two must agree. A LIVE that had moved would stop here.
"""
import hashlib
import json
import os
import sys

LIVE = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems'
SP = r'C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems/4f30368b-c2d1-47f6-a368-3d68b2892c85/scratchpad'
dest = os.path.abspath(sys.argv[1])
want = {}
for folder, name in (('landing_v2', 'route_latency.summary.json'), ('landing_v3_ids', 'ids_followup.summary.json')):   # the later landing overrides
    for item in json.load(open(os.path.join(SP, folder, name), encoding='utf-8'))['files']:
        want[item['file']] = item['post_sha256']
earlier = len(want)
v4 = json.load(open(os.path.join(SP, 'landing_v4', 'staffer_route_v4.summary.json'), encoding='utf-8'))['files']
agree = unlisted = 0
for item in v4:
    if item['kind'] != 'edit':
        continue
    if item['file'] in want:
        if want[item['file']] != item['pre_sha256']:
            raise SystemExit('%s: v4\'s pre-image is not the post-image of the last earlier landing' % item['file'])
        agree += 1
    else:
        want[item['file']] = item['pre_sha256']
        unlisted += 1
for rel, expected in sorted(want.items()):
    data = open(os.path.join(LIVE, *rel.split('/')), 'rb').read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit('LIVE has moved: %s is not the file the patch sets were cut against' % rel)
    target = os.path.join(dest, *rel.split('/'))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'wb') as handle:
        handle.write(data)
print('overlaid %d files with LIVE\'s current bytes: the %d the two earlier landings touched (each equal to its post-image) and %d more that v4 edits and neither landing touched (each equal to v4\'s pre-image); '
      'the %d v4 edits among the first group agree with v4\'s pre-images' % (len(want), earlier, unlisted, agree))
