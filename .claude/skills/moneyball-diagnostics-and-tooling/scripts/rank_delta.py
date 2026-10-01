# -*- coding: utf-8 -*-
"""rank_delta.py — diff two ranks_*.json rank-authority files (read-only, stdlib-only).

The rank authority is written by `compute_pillars.py --write` with schema
{'score': {name: float}, 'rank': {name: int}, 'press_pillar': {...}, 'pcts': {...}, ...}.
The change-verification protocol requires ZERO rank delta after a behavior-neutral change,
so the standard move is: copy ranks_python.json aside BEFORE a run, run, then diff.

Usage:
  python rank_delta.py "<before.json>" "<after.json>" [--top N]

Prints: member add/drop count, rank-change count, score-change count (>1e-12),
and the top-N movers by |rank delta|. Exit code 1 if any delta (so it can gate),
0 if byte-equivalent on rank+score.

This script never imports fec modules and never writes anything.
"""
import json, sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2:
        print(__doc__); sys.exit(2)
    top = 15
    if '--top' in sys.argv:
        top = int(sys.argv[sys.argv.index('--top') + 1])
    a = json.load(open(args[0], encoding='utf-8'))
    b = json.load(open(args[1], encoding='utf-8'))
    ra, rb = a.get('rank', {}), b.get('rank', {})
    sa, sb = a.get('score', {}), b.get('score', {})
    added = sorted(set(rb) - set(ra)); dropped = sorted(set(ra) - set(rb))
    common = sorted(set(ra) & set(rb))
    rank_moved = [(m, ra[m], rb[m]) for m in common if ra[m] != rb[m]]
    score_moved = [m for m in common
                   if abs((sa.get(m) or 0) - (sb.get(m) or 0)) > 1e-12]
    print('members: %d before / %d after | added %d dropped %d'
          % (len(ra), len(rb), len(added), len(dropped)))
    for m in added[:5]:   print('  + added:   %s' % m)
    for m in dropped[:5]: print('  - dropped: %s' % m)
    print('rank deltas : %d / %d members' % (len(rank_moved), len(common)))
    print('score deltas: %d / %d members (>1e-12)' % (len(score_moved), len(common)))
    if rank_moved:
        rank_moved.sort(key=lambda t: -abs(t[1] - t[2]))
        print('top movers (rank before -> after, negative delta = climbed):')
        for m, r1, r2 in rank_moved[:top]:
            print('  %-30s %4d -> %4d  (%+d)' % (m, r1, r2, r2 - r1))
    if not rank_moved and not score_moved and not added and not dropped:
        print('ZERO DELTA -- rank authority unchanged.')
        sys.exit(0)
    sys.exit(1)

if __name__ == '__main__':
    main()
