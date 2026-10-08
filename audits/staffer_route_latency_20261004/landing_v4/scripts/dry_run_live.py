"""Read-only report of what the Staffer route v4 patch (landing_v4) meets in a real tree, LIVE by default. Nothing is written and nothing is applied.

  python dry_run_live.py [--root <tree>]

It prints, in order: the tree's git HEAD; for every file the patch names, the sha256 of the tree's bytes against the pre-image in the summary (SAME or DIFFERENT);
the shipped dry run (`apply_landing.py`: pre-image check, then `git apply --check`); the same check typed out as the raw git command; and the rollback plan
(`rollback_landing.py` without --rollback, which only reports). Run it before the apply to see what the apply will meet; the dry run is also the first step of the README.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LANDING = os.path.dirname(HERE)
LIVE = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems'
NAME = 'staffer_route_v4'


def sha_of(path):
    if not os.path.isfile(path):
        return None
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def run(argv):
    env = dict(os.environ, PYTHONIOENCODING='utf-8', GIT_OPTIONAL_LOCKS='0', PYTHONDONTWRITEBYTECODE='1')
    done = subprocess.run(argv, capture_output=True, env=env)
    return done.returncode, (done.stdout + done.stderr).decode('utf-8', 'replace').rstrip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=LIVE, help='the tree to inspect (default: LIVE)')
    args = parser.parse_args()
    root = os.path.abspath(args.root)
    patch = os.path.join(LANDING, NAME + '.patch')
    summary = json.load(open(os.path.join(LANDING, NAME + '.summary.json'), encoding='utf-8'))
    print('# %s: read-only against %s. Nothing is written; --apply is not run.' % (time.strftime('%Y-%m-%d %H:%M:%S %Z'), root))
    print('# patch %s  sha256 %s' % (NAME + '.patch', hashlib.sha256(open(patch, 'rb').read()).hexdigest()))
    print()
    print('## the tree\'s git HEAD, and the bytes of the files the patch names against their pre-images')
    code, head = run(['git', '-C', root, 'rev-parse', 'HEAD'])
    print(head)
    for item in summary['files']:
        have = sha_of(os.path.join(root, *item['file'].split('/')))
        want = item['pre_sha256']
        print('%-4s %-66s tree %s  pre-image %s  %s' % (item['kind'], item['file'], '(absent)' if have is None else have[:12],
                                                       '(absent)' if want is None else want[:12], 'SAME' if have == want else 'DIFFERENT'))
    print()
    print('## python scripts/apply_landing.py   (dry run, read-only)')
    code, out = run([sys.executable, os.path.join(HERE, 'apply_landing.py'), '--root', root])
    print(out)
    print('rc=%d' % code)
    print()
    print('## the same check typed out: git -C <tree> -c core.autocrlf=false -c core.safecrlf=false apply --check %s.patch' % NAME)
    code, out = run(['git', '-C', root, '-c', 'core.autocrlf=false', '-c', 'core.safecrlf=false', 'apply', '--check', patch])
    if out:
        print(out)
    print('rc=%d' % code)
    print()
    print('## python scripts/rollback_landing.py   (plan, read-only): a tree that has not had this patch applied reports \'already original\' and \'already absent\'')
    code, out = run([sys.executable, os.path.join(HERE, 'rollback_landing.py'), '--root', root])
    print(out)
    print('rc=%d' % code)
    return 0


if __name__ == '__main__':
    sys.exit(main())
