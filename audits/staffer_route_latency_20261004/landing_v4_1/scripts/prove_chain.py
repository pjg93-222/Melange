"""Prove the ORDER with the real operator scripts of landing_v4 and landing_v4_1, on a scratch tree built from landing_v4's own pre-images (never on LIVE itself):

  LIVE-before-landing_v4  ->  v4.1 refused  ->  landing_v4 apply  ->  v4.1 dry run + apply  ->  back out in reverse (landing_v4's rollback refused while v4.1 is on)  ->  LIVE-before-landing_v4 again

landing_v4's pre-images are LIVE's bytes after landing_v2 and landing_v3_ids, so that part of the chain is taken as given (landing_v4's own chain proof covers it).
Every step checks every byte of every file either patch set touches. usage: python prove_chain.py <work dir outside every repository>
"""
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
V4 = SP + '/landing_v4'
WORK = sys.argv[1]
sys.path.insert(0, os.path.join(LIVE, 'fec', 'tools'))
import live_patch as lp  # noqa: E402

v4 = json.load(open(os.path.join(V4, 'staffer_route_v4.summary.json'), encoding='utf-8'))['files']
v41 = json.load(open(os.path.join(LANDING, 'staffer_route_v4_1.summary.json'), encoding='utf-8'))['files']
FAILS = []


def check(ok, text):
    print(('PASS  ' if ok else 'FAIL  ') + text)
    if not ok:
        FAILS.append(text)


def sha(root, rel):
    path = os.path.join(root, *rel.split('/'))
    return hashlib.sha256(open(path, 'rb').read()).hexdigest() if os.path.isfile(path) else None


def run(base, name, *args):
    done = subprocess.run([sys.executable, os.path.join(base, 'scripts', name), *args], capture_output=True,
                          env=dict(os.environ, PYTHONIOENCODING='utf-8', GIT_OPTIONAL_LOCKS='0', PYTHONDONTWRITEBYTECODE='1'))
    return done.returncode, done.stdout.decode('utf-8', 'replace')


def place(scratch, rel, src):
    dst = os.path.join(scratch, *rel.split('/'))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)


scratch = os.path.join(WORK, 'scratch_chain')
if os.path.exists(scratch):
    shutil.rmtree(scratch)
os.makedirs(scratch)
lp._assert_outside_repository(scratch)
# LIVE-before-landing_v4: every file landing_v4 edits at its pre-image bytes (LIVE's, after landing_v2 and landing_v3_ids); every file it or v4.1 creates absent.
for item in v4:
    if item['kind'] == 'edit':
        place(scratch, item['file'], os.path.join(V4, 'pre_images', *item['file'].split('/')))
paths = sorted({f['file'] for f in v4} | {f['file'] for f in v41})
start = {rel: sha(scratch, rel) for rel in paths}
print('scratch tree: %d files landing_v4 edits at their pre-image bytes; %d paths are watched (%d are landing_v4 files, %d landing_v4_1 files, %d in both)' % (
    sum(f['kind'] == 'edit' for f in v4), len(paths), len(v4), len(v41), len({f['file'] for f in v4} & {f['file'] for f in v41})))


def expect(label, table):
    bad = [rel for rel in paths if sha(scratch, rel) != table.get(rel)]
    check(not bad, '%s: every one of the %d watched paths is as expected%s' % (label, len(paths), (' (WRONG: %s)' % bad[:4]) if bad else ''))


v4_post = {f['file']: f['post_sha256'] for f in v4}
v41_post = {f['file']: f['post_sha256'] for f in v41}
state_start = dict(start)
expect('start (LIVE-before-landing_v4)', state_start)

print('\n== 1. v4.1 before landing_v4')
rc, out = run(LANDING, 'apply_landing.py', '--root', scratch, '--apply')
check(rc == 2 and 'REFUSED' in out, 'v4.1 --apply on the tree without landing_v4: rc=%s, REFUSED' % rc)
rc, out = run(LANDING, 'apply_landing.py', '--root', scratch)
check(rc == 2 and 'REFUSED' in out, 'v4.1 dry run on the tree without landing_v4: rc=%s, REFUSED' % rc)
expect('after the refusals', state_start)

print('\n== 2. landing_v4, then v4.1')
rc, out = run(V4, 'apply_landing.py', '--root', scratch)
check(rc == 0 and 'rc=0' in out, 'landing_v4 dry run: rc=%s' % rc)
expect('after the landing_v4 dry run', state_start)
rc, out = run(V4, 'apply_landing.py', '--root', scratch, '--apply')
check(rc == 0 and "'ok': True" in out, 'landing_v4 --apply: rc=%s' % rc)
state_v4 = {rel: v4_post.get(rel, state_start[rel]) for rel in paths}
expect('after landing_v4', state_v4)
rc, out = run(LANDING, 'apply_landing.py', '--root', scratch)
check(rc == 0 and 'rc=0' in out, 'v4.1 dry run after landing_v4: rc=%s' % rc)
expect('after the v4.1 dry run', state_v4)
rc, out = run(LANDING, 'apply_landing.py', '--root', scratch, '--apply')
print('\n'.join('      ' + line for line in out.strip().splitlines() if not line.startswith(('ok ', 'MISMATCH'))))
check(rc == 0 and "'ok': True" in out, 'v4.1 --apply: rc=%s' % rc)
state_v41 = {rel: v41_post.get(rel, state_v4[rel]) for rel in paths}
expect('after v4.1', state_v41)
check(all(state_v41[rel] != state_v4[rel] for rel in v41_post), 'every file of v4.1 changed (%d), and no other watched file did' % len(v41_post))
check(all(state_v41[rel] == state_v4[rel] for rel in paths if rel not in v41_post), 'the other %d watched files kept their landing_v4 bytes' % sum(rel not in v41_post for rel in paths))
rc, out = run(V4, 'apply_landing.py', '--root', scratch, '--apply')
check(rc == 2 and 'REFUSED' in out, 'landing_v4 --apply again, with v4.1 on: rc=%s, REFUSED (its targets moved)' % rc)
expect('after that refusal', state_v41)

print('\n== 3. back out, in reverse order')
rc, out = run(V4, 'rollback_landing.py', '--root', scratch, '--rollback')
check(rc == 1 and ('edited since the apply' in out or 'neither the pre-image nor the post-image' in out), 'landing_v4 rollback while v4.1 is still on is refused (rc=%s): v4.1 must come off first' % rc)
expect('after that refusal', state_v41)
rc, out = run(LANDING, 'rollback_landing.py', '--root', scratch, '--rollback')
check(rc == 0, 'v4.1 --rollback: rc=%s' % rc)
expect('after the v4.1 rollback', state_v4)
rc, out = run(V4, 'rollback_landing.py', '--root', scratch, '--rollback')
check(rc == 0, 'landing_v4 --rollback: rc=%s' % rc)
expect('after the landing_v4 rollback (LIVE-before-landing_v4 again)', state_start)
created = [f['file'] for f in v4 if f['kind'] == 'new'] + [f['file'] for f in v41 if f['kind'] == 'new']
check(all(sha(scratch, rel) is None for rel in created), 'every file either patch set created is gone (%d)' % len(created))
print('\nresult: %s' % ('ALL PASS' if not FAILS else 'FAILURES: %r' % FAILS))
sys.exit(1 if FAILS else 0)
