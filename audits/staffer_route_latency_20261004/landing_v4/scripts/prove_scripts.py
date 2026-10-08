"""Prove the operator scripts of landing_v4 on scratch trees (never on LIVE itself):
  apply_landing.py   refused on a tree that does not hold landing_v3_ids's post-images (a tree as LIVE was before landing_v3_ids, and a tree with one moved target), dry run, --apply,
                     a second --apply refused;
  rollback_landing.py  plan, refused after a later edit, --rollback, a second rollback a no-op.
usage: python prove_scripts.py <work dir outside every repository>"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANDING = os.path.dirname(HERE)
LIVE = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems'
SP = r'C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems/4f30368b-c2d1-47f6-a368-3d68b2892c85/scratchpad'
V3 = SP + '/landing_v3_ids'
WORK = sys.argv[1]
sys.path.insert(0, os.path.join(LIVE, 'fec', 'tools'))
import live_patch as lp  # noqa: E402

summary = json.load(open(os.path.join(LANDING, 'staffer_route_v4.summary.json'), encoding='utf-8'))
v3 = {f['file']: f for f in json.load(open(os.path.join(V3, 'ids_followup.summary.json'), encoding='utf-8'))['files']}
FAILS = []


def check(ok, text):
    print(('PASS  ' if ok else 'FAIL  ') + text)
    if not ok:
        FAILS.append(text)


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest() if os.path.isfile(path) else None


def script(name, *args):
    done = subprocess.run([sys.executable, os.path.join(HERE, name), *args], capture_output=True,
                          env=dict(os.environ, PYTHONIOENCODING='utf-8', GIT_OPTIONAL_LOCKS='0', PYTHONDONTWRITEBYTECODE='1'))
    return done.returncode, done.stdout.decode('utf-8', 'replace')


def fresh(name):
    path = os.path.join(WORK, name)
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    lp._assert_outside_repository(path)
    return path


def put(root, rel, data):
    target = os.path.join(root, *rel.split('/'))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'wb') as handle:
        handle.write(data)


edits = [f for f in summary['files'] if f['kind'] == 'edit']
news = [f for f in summary['files'] if f['kind'] == 'new']
pre = {f['file']: open(os.path.join(LANDING, 'pre_images', *f['file'].split('/')), 'rb').read() for f in edits}


def at(root, item, key):
    return sha(os.path.join(root, *item['file'].split('/'))) == item[key]


print('== before landing_v3_ids: a tree that holds what LIVE held before it (the apply refuses, writes nothing)')
# landing_v3_ids's own pre-images are LIVE's bytes as they were before it, so this does not depend on whether it was applied to LIVE since. A file landing_v3_ids edits is put
# back to that pre-image; a file it creates is absent; every other file v4 edits is as it is now (neither landing_v3_ids nor v4's pre-image differs there).
before_v3 = fresh('scratch_before_v3')
for item in edits:
    rel = item['file']
    if rel in v3 and v3[rel]['kind'] == 'edit':
        put(before_v3, rel, open(os.path.join(V3, 'pre_images', *rel.split('/')), 'rb').read())
    elif rel in v3:
        continue
    else:
        put(before_v3, rel, pre[rel])
held = {item['file']: sha(os.path.join(before_v3, *item['file'].split('/'))) for item in summary['files']}
check(sum(1 for item in edits if item['file'] in v3) >= 5, 'the tree differs from LIVE-now in the %d files landing_v3_ids touches that v4 edits' % sum(1 for item in edits if item['file'] in v3))
rc, out = script('apply_landing.py', '--root', before_v3)
check(rc == 2 and 'REFUSED' in out and 'nothing was changed' in out, 'dry run on LIVE-before-landing_v3_ids: rc=%s, REFUSED' % rc)
rc, out = script('apply_landing.py', '--root', before_v3, '--apply')
print('\n'.join('      ' + line for line in out.strip().splitlines() if 'MISMATCH' in line or 'REFUSED' in line or line.startswith('  -')))
check(rc == 2 and 'REFUSED' in out, '--apply on LIVE-before-landing_v3_ids: rc=%s, REFUSED' % rc)
check(held == {item['file']: sha(os.path.join(before_v3, *item['file'].split('/'))) for item in summary['files']}, 'nothing was written (every hash is as it was, new files still absent)')

print('\n== a tree that holds both landings except for one file v4 edits (a moved target)')
moved = fresh('scratch_moved_target')
for item in edits:
    put(moved, item['file'], pre[item['file']])
victim = edits[0]
put(moved, victim['file'], pre[victim['file']] + b'// a later edit\n')
held = {item['file']: sha(os.path.join(moved, *item['file'].split('/'))) for item in summary['files']}
rc, out = script('apply_landing.py', '--root', moved, '--apply')
check(rc == 2 and 'MISMATCH' in out and victim['file'] in out, '--apply on a moved target: rc=%s, MISMATCH named %s' % (rc, victim['file']))
check(held == {item['file']: sha(os.path.join(moved, *item['file'].split('/'))) for item in summary['files']}, 'nothing was written, the other files included')

print('\n== after both landings: a tree that holds their post-images (LIVE as it is now)')
tree = fresh('scratch_after_v3')
for item in edits:
    put(tree, item['file'], pre[item['file']])
rc, out = script('apply_landing.py', '--root', tree)
print('\n'.join('      ' + line for line in out.strip().splitlines()))
check(rc == 0 and 'rc=0' in out, 'dry run: rc=%s' % rc)
check(all(at(tree, i, 'pre_sha256') for i in edits) and all(sha(os.path.join(tree, *i['file'].split('/'))) is None for i in news), 'the dry run wrote nothing')
rc, out = script('apply_landing.py', '--root', tree, '--apply')
print('\n'.join('      ' + line for line in out.strip().splitlines() if not line.startswith(('ok ', 'MISMATCH'))))
check(rc == 0 and "'ok': True" in out, '--apply: rc=%s' % rc)
check(all(at(tree, i, 'post_sha256') for i in summary['files']), 'every post-image hash matches the manifest (%d files)' % len(summary['files']))
rc, out = script('apply_landing.py', '--root', tree, '--apply')
check(rc == 2 and 'REFUSED' in out and 'nothing was changed' in out, 'a second --apply is refused (the targets moved): rc=%s' % rc)
check(all(at(tree, i, 'post_sha256') for i in summary['files']), '   and it changed nothing')

print('\n== rollback_landing.py on that tree')
rc, out = script('rollback_landing.py', '--root', tree)
print('\n'.join('      ' + line for line in out.strip().splitlines()))
check(rc == 0 and 'plan only' in out, 'plan only: rc=%s' % rc)
check(all(at(tree, i, 'post_sha256') for i in summary['files']), 'the plan wrote nothing')
edited = os.path.join(tree, *edits[0]['file'].split('/'))
with open(edited, 'ab') as handle:
    handle.write(b'// edited after the apply\n')
rc, out = script('rollback_landing.py', '--root', tree, '--rollback')
check(rc == 1 and 'edited since the apply' in out, 'a file edited after the apply stops the rollback and nothing changes: rc=%s' % rc)
check(sha(edited) != edits[0]['post_sha256'] and all(at(tree, i, 'post_sha256') for i in summary['files'] if i['file'] != edits[0]['file']), '   (the edited file and the rest are untouched)')
with open(edited, 'wb') as handle:
    handle.write(open(os.path.join(LANDING, 'post_images', *edits[0]['file'].split('/')), 'rb').read())
rc, out = script('rollback_landing.py', '--root', tree, '--rollback')
print('      ' + out.strip().splitlines()[-1])
check(rc == 0, '--rollback: rc=%s' % rc)
check(all(at(tree, i, 'pre_sha256') for i in edits), 'every pre-image is back, byte for byte (%d files)' % len(edits))
check(all(sha(os.path.join(tree, *i['file'].split('/'))) is None for i in news), 'the %d new files are gone' % len(news))
rc, out = script('rollback_landing.py', '--root', tree, '--rollback')
check(rc == 0 and 'already original' in out, 'a second rollback changes nothing')
print('\nresult: %s' % ('ALL PASS' if not FAILS else 'FAILURES: %r' % FAILS))
sys.exit(1 if FAILS else 0)
