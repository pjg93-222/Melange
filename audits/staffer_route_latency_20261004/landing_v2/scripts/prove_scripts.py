"""Prove the three operator scripts on a scratch tree of LIVE pre-images (never on LIVE itself):
apply_landing.py (dry run, then --apply), rollback_landing.py (plan, then --rollback), and the dry run against LIVE (read-only)."""
import hashlib
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
import json  # noqa: E402

summary = json.load(open(os.path.join(LANDING, 'route_latency.summary.json'), encoding='utf-8'))
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


scratch = os.path.join(WORK, 'scratch_scripts')
if os.path.exists(scratch):
    shutil.rmtree(scratch)
os.makedirs(scratch)
lp._assert_outside_repository(scratch)
edits = [f for f in summary['files'] if f['kind'] == 'edit']
news = [f for f in summary['files'] if f['kind'] == 'new']
for item in edits:
    target = os.path.join(scratch, *item['file'].split('/'))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copyfile(os.path.join(LIVE, *item['file'].split('/')), target)

print('== dry run against LIVE itself (apply_landing.py without --apply: git apply --check, read-only)')
rc, out = script('apply_landing.py')
print(out.strip())
check(rc == 0, 'dry run against LIVE: rc=%s' % rc)

print('\n== apply_landing.py on the scratch tree')
rc, out = script('apply_landing.py', '--root', scratch)
check(rc == 0 and 'rc=0' in out, 'dry run on the scratch tree: %s' % out.strip())
check(all(sha(os.path.join(scratch, *i['file'].split('/'))) == i['live_pre_sha256'] for i in edits), 'the dry run wrote nothing')
rc, out = script('apply_landing.py', '--root', scratch, '--apply')
print(out.strip())
check(rc == 0 and "'ok': True" in out, '--apply on the scratch tree: rc=%s' % rc)
check(all(sha(os.path.join(scratch, *i['file'].split('/'))) == i['post_sha256'] for i in summary['files']), 'every post-image hash matches the manifest')
rc, out = script('apply_landing.py', '--root', scratch, '--apply')
check(rc == 1 and 'moved since the patch was cut' in out, 'a second --apply is refused (the targets moved): %s' % out.strip().splitlines()[0])

print('\n== rollback_landing.py on the scratch tree')
rc, out = script('rollback_landing.py', '--root', scratch)
print(out.strip())
check(rc == 0 and 'plan only' in out, 'plan only: rc=%s' % rc)
check(all(sha(os.path.join(scratch, *i['file'].split('/'))) == i['post_sha256'] for i in summary['files']), 'the plan wrote nothing')
edited = os.path.join(scratch, *edits[0]['file'].split('/'))
with open(edited, 'ab') as handle:
    handle.write(b'# edited after the apply\n')
rc, out = script('rollback_landing.py', '--root', scratch, '--rollback')
check(rc == 1 and 'edited since the apply' in out.replace('(edited since the apply)', 'edited since the apply'), 'a file edited after the apply stops the rollback and nothing changes')
check(sha(edited) != edits[0]['post_sha256'] and all(sha(os.path.join(scratch, *i['file'].split('/'))) is not None for i in summary['files']), '   (the edited file and the rest are untouched)')
with open(edited, 'wb') as handle:
    handle.write(open(os.path.join(LANDING, 'post_images', *edits[0]['file'].split('/')), 'rb').read())
rc, out = script('rollback_landing.py', '--root', scratch, '--rollback')
print(out.strip().splitlines()[-1])
check(rc == 0, '--rollback: rc=%s' % rc)
check(all(sha(os.path.join(scratch, *i['file'].split('/'))) == i['live_pre_sha256'] for i in edits), 'every pre-image is back, byte for byte')
check(all(sha(os.path.join(scratch, *i['file'].split('/'))) is None for i in news), 'the %d new files are gone' % len(news))
rc, out = script('rollback_landing.py', '--root', scratch, '--rollback')
check(rc == 0 and 'already original' in out, 'a second rollback changes nothing')
print('\nresult: %s' % ('ALL PASS' if not FAILS else 'FAILURES: %r' % FAILS))
sys.exit(1 if FAILS else 0)
