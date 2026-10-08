"""Apply the identifier follow-up (landing_v3_ids) to a working tree through live_patch.apply_to() (D-060).

  python apply_landing.py                  dry run: the pre-image check, then `git apply --check`; writes nothing
  python apply_landing.py --apply          apply to LIVE

This patch is cut against the bytes LIVE holds AFTER landing_v2 is applied, so it must refuse to run before that. It does, in two layers:
  1. preflight(): every file the patch edits must hash to the pre-image sha256 in the manifest (for the files landing_v2 touches, that is landing_v2's
     post-image sha256), and none of the files it creates may exist yet. One mismatch refuses the whole patch, in the dry run as well. Nothing is written.
  2. live_patch.apply_to() checks the same hashes again, runs `git -c core.autocrlf=false apply --check`, applies, verifies every post-image sha256 against
     the manifest, and puts the bytes it read back if anything is off. It never uses --index or --cached: LIVE blobs are pure LF under core.autocrlf=true and
     LIVE working files are never EOL-normalised.
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANDING = os.path.dirname(HERE)
LIVE = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems'
sys.path.insert(0, os.path.join(LIVE, 'fec', 'tools'))
import live_patch as lp  # noqa: E402

NAME = 'ids_followup'


def sha_of(path):
    if not os.path.isfile(path):
        return None
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def preflight(root, summary):
    """Returns (rows, problems). Each row: (file, kind, expected pre-image sha256 or None, actual sha256 or None, ok)."""
    rows, problems = [], []
    for item in summary['files']:
        rel = item['file']
        have = sha_of(os.path.join(root, *rel.split('/')))
        want = item['pre_sha256']
        ok = (have is None) if item['kind'] == 'new' else (have == want)
        rows.append((rel, item['kind'], want, have, ok))
        if not ok:
            if item['kind'] == 'new':
                problems.append('%s already exists' % rel)
            elif have is None:
                problems.append('%s is missing (its pre-image is %s)' % (rel, item.get('pre_source') or 'unknown'))
            else:
                problems.append('%s does not hold its pre-image (%s)' % (rel, item.get('pre_source') or 'unknown'))
    return rows, problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=LIVE, help='the tree to patch (default: LIVE)')
    parser.add_argument('--patch', default=os.path.join(LANDING, NAME + '.patch'))
    parser.add_argument('--apply', action='store_true', help='write the patch into the tree; without it only the checks run')
    args = parser.parse_args()
    summary = json.load(open(os.path.join(LANDING, NAME + '.summary.json'), encoding='utf-8'))
    rows, problems = preflight(args.root, summary)
    for rel, kind, want, have, ok in rows:
        print('%-7s %-4s %-62s expected %s  actual %s' % ('ok' if ok else 'MISMATCH', kind, rel,
                                                         '(absent)' if want is None else want[:12], '(absent)' if have is None else have[:12]))
    if problems:
        print('REFUSED: this patch is cut against the bytes LIVE holds after landing_v2 is applied. Required first: %s. Apply landing_v2 first, or find what changed these files:' % summary['requires'])
        for text in problems:
            print('  -', text)
        print('nothing was changed')
        return 2
    if not args.apply:
        outcome = lp.check_against(args.root, args.patch)
        print('dry run (git apply --check, read-only): rc=%s %s' % (outcome['rc'], outcome['stderr'].strip()))
        return 0 if outcome['rc'] == 0 else 1
    result = lp.apply_to(args.root, args.patch)
    print('apply_to:', {key: result[key] for key in ('ok', 'reason', 'check_rc', 'apply_rc', 'mismatches')})
    if result['stderr'].strip():
        print(result['stderr'].strip())
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
