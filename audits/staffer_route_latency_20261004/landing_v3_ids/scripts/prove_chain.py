"""Prove the ORDER with the real operator scripts of both patch sets, on a scratch tree built from LIVE's own pre-images (never on LIVE itself):

  LIVE-as-it-is  ->  v3 refused  ->  landing_v2 apply  ->  v3 dry run + apply  ->  v3 rollback  ->  landing_v2 rollback  ->  LIVE-as-it-is again

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
V2 = r'C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems/4f30368b-c2d1-47f6-a368-3d68b2892c85/scratchpad/landing_v2'
WORK = sys.argv[1]
sys.path.insert(0, os.path.join(LIVE, 'fec', 'tools'))
import live_patch as lp  # noqa: E402

v2 = json.load(open(os.path.join(V2, 'route_latency.summary.json'), encoding='utf-8'))['files']
v3 = json.load(open(os.path.join(LANDING, 'ids_followup.summary.json'), encoding='utf-8'))['files']
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
                          env=dict(os.environ, PYTHONIOENCODING='utf-8', GIT_OPTIONAL_LOCKS='0'))
    return done.returncode, done.stdout.decode('utf-8', 'replace')


scratch = os.path.join(WORK, 'scratch_chain')
if os.path.exists(scratch):
    shutil.rmtree(scratch)
os.makedirs(scratch)
lp._assert_outside_repository(scratch)
# LIVE-as-it-is: the 13 files landing_v2 edits at LIVE's exact pre-image bytes, plus the one extra file the follow-up edits that landing_v2 does not (LIVE's own).
extra = [f for f in v3 if f['kind'] == 'edit' and f['file'] not in {x['file'] for x in v2}]
for item in v2:
    if item['kind'] == 'edit':
        src = os.path.join(V2, 'pre_images', *item['file'].split('/'))
        dst = os.path.join(scratch, *item['file'].split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
for item in extra:
    dst = os.path.join(scratch, *item['file'].split('/'))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(os.path.join(LIVE, *item['file'].split('/')), dst)
paths = sorted({f['file'] for f in v2} | {f['file'] for f in v3})
start = {rel: sha(scratch, rel) for rel in paths}
print('scratch tree: %d files edited by landing_v2 at LIVE pre-image bytes, %d extra file(s) the follow-up edits (LIVE\'s own); %d paths are watched' % (sum(f['kind'] == 'edit' for f in v2), len(extra), len(paths)))


def expect(label, table):
    bad = [rel for rel in paths if sha(scratch, rel) != table.get(rel)]
    check(not bad, '%s: every one of the %d watched paths is as expected%s' % (label, len(paths), (' (WRONG: %s)' % bad[:4]) if bad else ''))


v2_pre = {f['file']: f['live_pre_sha256'] for f in v2}
v2_post = {f['file']: f['post_sha256'] for f in v2}
state_start = {rel: v2_pre.get(rel, start.get(rel)) for rel in paths}
expect('start (LIVE-as-it-is)', state_start)

print('\n== 1. the follow-up before landing_v2')
rc, out = run(LANDING, 'apply_landing.py', '--root', scratch, '--apply')
check(rc == 2 and 'REFUSED' in out, 'v3 --apply on the tree without landing_v2: rc=%s, REFUSED' % rc)
expect('after the refusal', state_start)

print('\n== 2. landing_v2, then the follow-up')
rc, out = run(V2, 'apply_landing.py', '--root', scratch, '--apply')
check(rc == 0 and "'ok': True" in out, 'landing_v2 --apply: rc=%s' % rc)
state_v2 = {rel: v2_post.get(rel, start.get(rel)) for rel in paths}
expect('after landing_v2', state_v2)
rc, out = run(LANDING, 'apply_landing.py', '--root', scratch)
check(rc == 0 and 'rc=0' in out, 'v3 dry run after landing_v2: rc=%s' % rc)
expect('after the v3 dry run', state_v2)
rc, out = run(LANDING, 'apply_landing.py', '--root', scratch, '--apply')
print('\n'.join('      ' + line for line in out.strip().splitlines()))
check(rc == 0 and "'ok': True" in out, 'v3 --apply: rc=%s' % rc)
v3_post = {f['file']: f['post_sha256'] for f in v3}
state_v3 = {rel: v3_post.get(rel, state_v2[rel]) for rel in paths}
expect('after v3', state_v3)
check(all(state_v3[rel] != state_v2[rel] for rel in v3_post), 'every file of the follow-up changed (%d), and no other watched file did' % len(v3_post))
check(all(state_v3[rel] == state_v2[rel] for rel in paths if rel not in v3_post), 'the other %d watched files kept their landing_v2 bytes' % sum(rel not in v3_post for rel in paths))

print('\n== 3. back out, in reverse order')
rc, out = run(V2, 'rollback_landing.py', '--root', scratch, '--rollback')
check(rc == 1 and 'edited since the apply' in out or 'neither the pre-image nor the post-image' in out, 'landing_v2 rollback while the follow-up is still on is refused (rc=%s): the follow-up must come off first' % rc)
expect('after that refusal', state_v3)
rc, out = run(LANDING, 'rollback_landing.py', '--root', scratch, '--rollback')
check(rc == 0, 'v3 --rollback: rc=%s' % rc)
expect('after the v3 rollback', state_v2)
rc, out = run(V2, 'rollback_landing.py', '--root', scratch, '--rollback')
check(rc == 0, 'landing_v2 --rollback: rc=%s' % rc)
expect('after the landing_v2 rollback (LIVE-as-it-is again)', state_start)
new_v2 = [f['file'] for f in v2 if f['kind'] == 'new']
check(all(sha(scratch, rel) is None for rel in new_v2 + [f['file'] for f in v3 if f['kind'] == 'new']), 'every file either patch set created is gone')
print('\nresult: %s' % ('ALL PASS' if not FAILS else 'FAILURES: %r' % FAILS))
sys.exit(1 if FAILS else 0)
