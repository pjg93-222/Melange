# -*- coding: utf-8 -*-
"""Round-6 thin runner — text-N vs behavioral reactivity, SUCCESSOR to round 4 at MEM_N>=250
(prereg big5_n2_prereg.md; round-4 pin: 'successor prereg only at reactivity coverage MEM_N>=250,
same five-bar structure, fresh fingerprints'). ZERO re-implementation: every model, bar, seed,
gate, battery sim, demotion rule, noiv ship-gate, and the non-finite rule execute inside
fec/b5_n_matrix.py; this runner only re-points the prereg file and the fresh fingerprint pins.
The RESULT heading check ('\\n## RESULT-N') matches the '## RESULT-N2' heading this round appends,
so the one-look gate arms identically. LOCK-TIME: fill PIN below from the lock commit, replacing
every None; the look REFUSES (not consumed) while any None remains."""
import os as _o, sys as _s
_s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
import b5_n_matrix as NM

NM.PREREG = _o.path.join(_o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))), 'big5_n2_prereg.md')

# LOCK-TIME PINS (filled at lock; None = unlockable, the gate below refuses)
PIN2 = {
    'MEM': None, 'MEM_N': None,
    'bd_sha': None,        # behavioral_dispositions.json (fresh post-backfill)
    'ix_sha': None,        # interaction_features.json (fresh post-backfill)
    'speeches': None, 'posts': None,   # social_media.db row counts (collectors quiet)
}

if __name__ == '__main__':
    if any(v is None for v in PIN2.values()):
        import argparse
        ap = argparse.ArgumentParser(); ap.add_argument('--simulate', action='store_true')
        ap.add_argument('--look', action='store_true'); a = ap.parse_args()
        if a.look:
            print('!! LOOK REFUSED (not consumed): PIN2 lock-time fields unfilled (prereg still DRAFT)')
            raise SystemExit(2)
        # simulate/status may run against the draft (diagnostic phase); pins stay round-4 for status text
    else:
        NM.PIN = PIN2
    NM.main()
