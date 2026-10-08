"""Put a tree back the way it was before the Staffer route v4 patch (landing_v4): restore the saved pre-images (LIVE's bytes as they were, which are the landing_v2 and landing_v3_ids
post-images where those landings touch the file) byte for byte and remove the files v4 created. It does not undo landing_v3_ids or landing_v2.

  python rollback_landing.py               plan only, writes nothing
  python rollback_landing.py --rollback    restore

A file is touched only if it is still exactly the post-image the patch produced (its sha256 matches the summary). A file that was edited after the apply is
reported and left alone; --force overwrites it anyway. The other way back, for a tree whose files are still exactly the post-images, is:
  git -C "<LIVE>" -c core.autocrlf=false -c core.safecrlf=false apply -R "<landing_v4>\\staffer_route_v4.patch"
Roll back in reverse order: landing_v3_ids's own rollback refuses while this patch is on.
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

NAME = 'staffer_route_v4'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=LIVE)
    parser.add_argument('--rollback', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    summary = json.load(open(os.path.join(LANDING, NAME + '.summary.json'), encoding='utf-8'))
    actions, problems = [], []
    for item in summary['files']:
        rel = item['file']
        target = os.path.join(args.root, *rel.split('/'))
        current = open(target, 'rb').read() if os.path.isfile(target) else None
        if item['kind'] == 'edit':
            pre = open(os.path.join(LANDING, 'pre_images', *rel.split('/')), 'rb').read()
            if current is None:
                problems.append('%s is missing' % rel)
            elif sha(current) == item['pre_sha256']:
                actions.append(('already original', rel, None))
            elif sha(current) == item['post_sha256'] or args.force:
                actions.append(('restore pre-image', rel, pre))
            else:
                problems.append('%s is neither the pre-image nor the post-image (edited since the apply)' % rel)
        else:
            if current is None:
                actions.append(('already absent', rel, None))
            elif sha(current) == item['post_sha256'] or args.force:
                actions.append(('remove new file', rel, None))
            else:
                problems.append('%s was edited since the apply' % rel)
    for what, rel, _data in actions:
        print('%-18s %s' % (what, rel))
    for text in problems:
        print('PROBLEM:', text)
    if problems:
        print('nothing was changed: resolve the problems above, or rerun with --force')
        return 1
    if not args.rollback:
        print('plan only; rerun with --rollback to restore')
        return 0
    for what, rel, data in actions:
        target = os.path.join(args.root, *rel.split('/'))
        if what == 'restore pre-image':
            lp._write_atomic(target, data)
        elif what == 'remove new file':
            os.remove(target)
    print('rolled back %d files' % sum(1 for what, _r, _d in actions if what in ('restore pre-image', 'remove new file')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
