"""Apply the route-latency patch set to a working tree through live_patch.apply_to() (D-060).

  python apply_landing.py                  dry run: `git apply --check` only, writes nothing
  python apply_landing.py --apply          apply to LIVE

apply_to() refuses a target that moved since the cut (every pre-image sha256 must match the manifest, and no new file may
exist yet), checks with `git -c core.autocrlf=false apply --check`, applies, verifies every post-image sha256 against the
manifest, and puts the bytes it read back if anything is off. It never uses --index or --cached: LIVE blobs are pure LF
under core.autocrlf=true and LIVE working files are never EOL-normalised.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LANDING = os.path.dirname(HERE)
LIVE = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems'
sys.path.insert(0, os.path.join(LIVE, 'fec', 'tools'))
import live_patch as lp  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=LIVE, help='the tree to patch (default: LIVE)')
    parser.add_argument('--patch', default=os.path.join(LANDING, 'route_latency.patch'))
    parser.add_argument('--apply', action='store_true', help='write the patch into the tree; without it only --check runs')
    args = parser.parse_args()
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
