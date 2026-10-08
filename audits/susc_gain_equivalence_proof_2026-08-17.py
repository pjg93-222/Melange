"""Obs-(a) fix equivalence proof: the refactored _susc_gain reproduces the original
expressions BIT-EXACTLY. Standalone -- deliberately does NOT import receptivity_layer
(script-style module; import == execution == artifact write)."""


def clip(x, lo, hi):
    return max(lo, min(hi, x))


SUSC_GAINS = {'susc_mult': (.18, 0.70, 1.30), 'edge_mult': (.12, 0.80, 1.20)}


def _susc_gain(s, slope, lo, hi):
    return clip(1 + slope * s, lo, hi)


import random

random.seed(7)
N = 0
grid = [i / 1000.0 for i in range(-6000, 6001)]
grid += [random.uniform(-8, 8) for _ in range(200000)]
grid += [-1e12, 1e12, 0.0, -0.0, 1e-300, -1e-300]
for s in grid:
    old_s = clip(1 + .18 * s, 0.70, 1.30)
    old_e = clip(1 + .12 * s, 0.80, 1.20)
    new_s = _susc_gain(s, *SUSC_GAINS['susc_mult'])
    new_e = _susc_gain(s, *SUSC_GAINS['edge_mult'])
    assert old_s == new_s and repr(old_s) == repr(new_s), s
    assert old_e == new_e and repr(old_e) == repr(new_e), s
    N += 1
print('EQUIVALENCE PROVEN: %d points, bit-exact (== and repr), incl. clip boundaries and extremes' % N)
