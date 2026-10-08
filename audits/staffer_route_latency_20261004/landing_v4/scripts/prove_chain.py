"""Prove the ORDER with the real operator scripts of all three patch sets, on a scratch tree built from LIVE's own pre-images (never on LIVE itself):

  LIVE-as-it-was  ->  v4 and v3 refused  ->  landing_v2 apply  ->  v4 refused, v3 dry run + apply  ->  v4 dry run + apply  ->  back out in reverse (refused out of order)  ->  LIVE-as-it-was again

Every step checks every byte of every file any of the three patch sets touches. usage: python prove_chain.py <work dir outside every repository>
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
V2, V3 = SP + '/landing_v2', SP + '/landing_v3_ids'
WORK = sys.argv[1]
sys.path.insert(0, os.path.join(LIVE, 'fec', 'tools'))
import live_patch as lp  # noqa: E402

v2 = json.load(open(os.path.join(V2, 'route_latency.summary.json'), encoding='utf-8'))['files']
v3 = json.load(open(os.path.join(V3, 'ids_followup.summary.json'), encoding='utf-8'))['files']
v4 = json.load(open(os.path.join(LANDING, 'staffer_route_v4.summary.json'), encoding='utf-8'))['files']
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
# LIVE-as-it-was, before landing_v2: the files landing_v2 edits at LIVE's exact pre-image bytes; a file only landing_v3_ids edits at its pre-image (LIVE's own, which landing_v2 does not
# touch); a file only v4 edits at its pre-image (LIVE's own, which neither touches). A file any of them creates is absent.
in_v2 = {f['file'] for f in v2}
in_v3 = {f['file'] for f in v3}
for item in v2:
    if item['kind'] == 'edit':
        place(scratch, item['file'], os.path.join(V2, 'pre_images', *item['file'].split('/')))
extra3 = [f for f in v3 if f['kind'] == 'edit' and f['file'] not in in_v2]
for item in extra3:
    place(scratch, item['file'], os.path.join(V3, 'pre_images', *item['file'].split('/')))
extra4 = [f for f in v4 if f['kind'] == 'edit' and f['file'] not in in_v2 and f['file'] not in in_v3]
for item in extra4:
    place(scratch, item['file'], os.path.join(LANDING, 'pre_images', *item['file'].split('/')))
paths = sorted(in_v2 | in_v3 | {f['file'] for f in v4})
start = {rel: sha(scratch, rel) for rel in paths}
print('scratch tree: %d files edited by landing_v2 at LIVE pre-image bytes, %d file(s) only landing_v3_ids edits, %d file(s) only v4 edits (LIVE\'s own); %d paths are watched' % (
    sum(f['kind'] == 'edit' for f in v2), len(extra3), len(extra4), len(paths)))


def expect(label, table):
    bad = [rel for rel in paths if sha(scratch, rel) != table.get(rel)]
    check(not bad, '%s: every one of the %d watched paths is as expected%s' % (label, len(paths), (' (WRONG: %s)' % bad[:4]) if bad else ''))


v2_post = {f['file']: f['post_sha256'] for f in v2}
v3_post = {f['file']: f['post_sha256'] for f in v3}
v4_post = {f['file']: f['post_sha256'] for f in v4}
state_start = {rel: start.get(rel) for rel in paths}
expect('start (LIVE-as-it-was)', state_start)

print('\n== 1. v4 and landing_v3_ids before landing_v2')
rc, out = run(LANDING, 'apply_landing.py', '--root', scratch, '--apply')
check(rc == 2 and 'REFUSED' in out, 'v4 --apply on the tree without landing_v2 or landing_v3_ids: rc=%s, REFUSED' % rc)
rc, out = run(V3, 'apply_landing.py', '--root', scratch, '--apply')
check(rc == 2 and 'REFUSED' in out, 'landing_v3_ids --apply on the tree without landing_v2: rc=%s, REFUSED' % rc)
expect('after the refusals', state_start)

print('\n== 2. landing_v2, then v4 refused, then landing_v3_ids')
rc, out = run(V2, 'apply_landing.py', '--root', scratch, '--apply')
check(rc == 0 and "'ok': True" in out, 'landing_v2 --apply: rc=%s' % rc)
state_v2 = {rel: v2_post.get(rel, state_start[rel]) for rel in paths}
expect('after landing_v2', state_v2)
rc, out = run(LANDING, 'apply_landing.py', '--root', scratch, '--apply')
check(rc == 2 and 'REFUSED' in out, 'v4 --apply on a tree with landing_v2 but without landing_v3_ids: rc=%s, REFUSED' % rc)
expect('after that refusal', state_v2)
rc, out = run(V3, 'apply_landing.py', '--root', scratch)
check(rc == 0 and 'rc=0' in out, 'landing_v3_ids dry run after landing_v2: rc=%s' % rc)
expect('after the landing_v3_ids dry run', state_v2)
rc, out = run(V3, 'apply_landing.py', '--root', scratch, '--apply')
check(rc == 0 and "'ok': True" in out, 'landing_v3_ids --apply: rc=%s' % rc)
state_v3 = {rel: v3_post.get(rel, state_v2[rel]) for rel in paths}
expect('after landing_v3_ids', state_v3)

print('\n== 3. v4')
rc, out = run(LANDING, 'apply_landing.py', '--root', scratch)
check(rc == 0 and 'rc=0' in out, 'v4 dry run after both landings: rc=%s' % rc)
expect('after the v4 dry run', state_v3)
rc, out = run(LANDING, 'apply_landing.py', '--root', scratch, '--apply')
print('\n'.join('      ' + line for line in out.strip().splitlines() if not line.startswith(('ok ', 'MISMATCH'))))
check(rc == 0 and "'ok': True" in out, 'v4 --apply: rc=%s' % rc)
state_v4 = {rel: v4_post.get(rel, state_v3[rel]) for rel in paths}
expect('after v4', state_v4)
check(all(state_v4[rel] != state_v3[rel] for rel in v4_post), 'every file of v4 changed (%d), and no other watched file did' % len(v4_post))
check(all(state_v4[rel] == state_v3[rel] for rel in paths if rel not in v4_post), 'the other %d watched files kept their earlier bytes' % sum(rel not in v4_post for rel in paths))

print('\n== 4. back out, in reverse order')
rc, out = run(V3, 'rollback_landing.py', '--root', scratch, '--rollback')
check(rc == 1 and ('edited since the apply' in out or 'neither the pre-image nor the post-image' in out), 'landing_v3_ids rollback while v4 is still on is refused (rc=%s): v4 must come off first' % rc)
expect('after that refusal', state_v4)
rc, out = run(V2, 'rollback_landing.py', '--root', scratch, '--rollback')
check(rc == 1 and ('edited since the apply' in out or 'neither the pre-image nor the post-image' in out), 'landing_v2 rollback while v3 and v4 are still on is refused (rc=%s)' % rc)
expect('after that refusal', state_v4)
rc, out = run(LANDING, 'rollback_landing.py', '--root', scratch, '--rollback')
check(rc == 0, 'v4 --rollback: rc=%s' % rc)
expect('after the v4 rollback', state_v3)
rc, out = run(V3, 'rollback_landing.py', '--root', scratch, '--rollback')
check(rc == 0, 'landing_v3_ids --rollback: rc=%s' % rc)
expect('after the landing_v3_ids rollback', state_v2)
rc, out = run(V2, 'rollback_landing.py', '--root', scratch, '--rollback')
check(rc == 0, 'landing_v2 --rollback: rc=%s' % rc)
expect('after the landing_v2 rollback (LIVE-as-it-was again)', state_start)
created = [f['file'] for f in v2 if f['kind'] == 'new'] + [f['file'] for f in v3 if f['kind'] == 'new'] + [f['file'] for f in v4 if f['kind'] == 'new']
check(all(sha(scratch, rel) is None for rel in created), 'every file any of the three patch sets created is gone (%d)' % len(created))
print('\nresult: %s' % ('ALL PASS' if not FAILS else 'FAILURES: %r' % FAILS))
sys.exit(1 if FAILS else 0)
