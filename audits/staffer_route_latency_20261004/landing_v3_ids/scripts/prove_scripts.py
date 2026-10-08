"""Prove the operator scripts of landing_v3_ids on scratch trees (never on LIVE itself):
  apply_landing.py   refused on a tree that does not hold landing_v2's post-images (two shapes of it), dry run, --apply, a second --apply refused;
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
WORK = sys.argv[1]
sys.path.insert(0, os.path.join(LIVE, 'fec', 'tools'))
import live_patch as lp  # noqa: E402

summary = json.load(open(os.path.join(LANDING, 'ids_followup.summary.json'), encoding='utf-8'))
FAILS = []


def check(ok, text):
    print(('PASS  ' if ok else 'FAIL  ') + text)
    if not ok:
        FAILS.append(text)


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest() if os.path.isfile(path) else None


def script(name, *args):
    done = subprocess.run([sys.executable, os.path.join(HERE, name), *args], capture_output=True,
                          env=dict(os.environ, PYTHONIOENCODING='utf-8', GIT_OPTIONAL_LOCKS='0'))
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


print('== before landing_v2: a tree that holds what LIVE held before landing_v2 (the apply refuses, writes nothing)')
# landing_v2's own pre-images are LIVE's bytes as cut, so this does not depend on whether landing_v2 has been applied to LIVE since; staffer-live.js is
# LIVE's own file, which landing_v2 does not touch. A file landing_v2 creates is absent.
V2 = r'C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems/4f30368b-c2d1-47f6-a368-3d68b2892c85/scratchpad/landing_v2'
now_tree = fresh('scratch_before_v2')
for item in edits:
    v2_pre = os.path.join(V2, 'pre_images', *item['file'].split('/'))
    live_file = os.path.join(LIVE, *item['file'].split('/'))
    if os.path.isfile(v2_pre):
        put(now_tree, item['file'], open(v2_pre, 'rb').read())
    elif os.path.isfile(live_file) and item['file'].endswith('staffer-live.js'):
        put(now_tree, item['file'], open(live_file, 'rb').read())
before = {item['file']: sha(os.path.join(now_tree, *item['file'].split('/'))) for item in summary['files']}
rc, out = script('apply_landing.py', '--root', now_tree)
check(rc == 2 and 'REFUSED' in out and 'nothing was changed' in out, 'dry run on LIVE-before-landing_v2: rc=%s, REFUSED' % rc)
rc, out = script('apply_landing.py', '--root', now_tree, '--apply')
print('\n'.join('      ' + line for line in out.strip().splitlines()))
check(rc == 2 and 'REFUSED' in out, '--apply on LIVE-before-landing_v2: rc=%s, REFUSED' % rc)
check(before == {item['file']: sha(os.path.join(now_tree, *item['file'].split('/'))) for item in summary['files']}, 'nothing was written (every hash is as it was, new files still absent)')

print('\n== a tree that holds landing_v2 except for one file the follow-up edits (a moved target)')
moved = fresh('scratch_moved_target')
for item in edits:
    put(moved, item['file'], pre[item['file']])
victim = edits[0]
put(moved, victim['file'], pre[victim['file']] + b'// a later edit\n')
before = {item['file']: sha(os.path.join(moved, *item['file'].split('/'))) for item in summary['files']}
rc, out = script('apply_landing.py', '--root', moved, '--apply')
check(rc == 2 and 'MISMATCH' in out and victim['file'] in out, '--apply on a moved target: rc=%s, MISMATCH named %s' % (rc, victim['file']))
check(before == {item['file']: sha(os.path.join(moved, *item['file'].split('/'))) for item in summary['files']}, 'nothing was written, the other files included')

print('\n== after landing_v2: a tree that holds its post-images')
tree = fresh('scratch_after_v2')
for item in edits:
    put(tree, item['file'], pre[item['file']])
rc, out = script('apply_landing.py', '--root', tree)
print('\n'.join('      ' + line for line in out.strip().splitlines()))
check(rc == 0 and 'rc=0' in out, 'dry run: rc=%s' % rc)
check(all(at(tree, i, 'pre_sha256') for i in edits) and all(sha(os.path.join(tree, *i['file'].split('/'))) is None for i in news), 'the dry run wrote nothing')
rc, out = script('apply_landing.py', '--root', tree, '--apply')
print('\n'.join('      ' + line for line in out.strip().splitlines()))
check(rc == 0 and "'ok': True" in out, '--apply: rc=%s' % rc)
check(all(at(tree, i, 'post_sha256') for i in summary['files']), 'every post-image hash matches the manifest')
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
check(all(at(tree, i, 'pre_sha256') for i in edits), 'every pre-image is back, byte for byte')
check(all(sha(os.path.join(tree, *i['file'].split('/'))) is None for i in news), 'the %d new files are gone' % len(news))
rc, out = script('rollback_landing.py', '--root', tree, '--rollback')
check(rc == 0 and 'already original' in out, 'a second rollback changes nothing')
print('\nresult: %s' % ('ALL PASS' if not FAILS else 'FAILURES: %r' % FAILS))
sys.exit(1 if FAILS else 0)
