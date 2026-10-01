# -*- coding: utf-8 -*-
"""QME 2026-10-01 frontier / coalition fixes. FIXTURE ONLY: no live tree read, nothing written.

per_topic_coalition.py, budget_frontier.py and audit_frontier.py all execute on import (workbook, network, artifact reads), so each pure helper is
lifted out of the shipped source with ast and run alone -- the real bodies, none of those modules imported.

  stance_pool       order-preserving gate filter shared by coalition + frontier (dial off = identity).
  coal_waterfill    CAP-clipped excess re-split pro rata; identical to the old clip when nothing caps; dial off = old clip exactly.
  knee_rederive     audit_frontier's second-path knee equals the engine's forward 25% rule, raw and clamped.
  seed offset       (SEED-7)*odd constant is exactly 0 at the default seed and decorrelates other seeds (sm64 from the kernel).
  audit floor       audit_full's frontier `exp` equals the exact number of ck() calls a full audit_frontier run makes.
"""
from __future__ import annotations

import ast
import os
import random
import re
import sys

import pytest

FEC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if FEC not in sys.path:
    sys.path.insert(0, FEC)
COAL = os.path.join(FEC, 'engine', 'per_topic_coalition.py')
FRONT = os.path.join(FEC, 'engine', 'budget_frontier.py')
AFRONT = os.path.join(FEC, 'audit', 'audit_frontier.py')
AFULL = os.path.join(FEC, 'audit', 'audit_full.py')


def _lift(path, name):
    src = open(path, encoding='utf-8').read()
    node = next(n for n in ast.parse(src).body if isinstance(n, ast.FunctionDef) and n.name == name)
    ns = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), path, 'exec'), ns)  # noqa: S102 - vetted def
    return ns[name]


BLOCK = frozenset({'Skeptic', 'Highly Skeptical', 'Opponent'})


@pytest.mark.parametrize('path', [COAL, FRONT])
def test_stance_pool(path):
    f = _lift(path, 'stance_pool')
    ovt = {'a': 'Ally', 'b': 'Opponent', 'c': 'Lean Skeptic', 'd': 'Skeptic', 'e': 'Highly Skeptical'}
    assert f(['e', 'a', 'b', 'c', 'd', 'z'], ovt, BLOCK, True) == ['a', 'c', 'z']   # order kept; Lean Skeptic eligible; unknown kept
    assert f(['e', 'a', 'b'], ovt, BLOCK, False) == ['e', 'a', 'b']                  # dial off = identity
    assert f([], ovt, BLOCK, True) == []


def _old_clip(boost, cap, budget, unit):
    tot = sum(boost.values()) or 1
    return {n: min(cap, round(budget * v / tot / unit) * unit) for n, v in boost.items()}


def test_waterfill_no_cap_identical_to_old():
    wf = _lift(COAL, 'coal_waterfill')
    boost = {'a': 3.0, 'b': 2.0, 'c': 1.5, 'd': 1.0, 'e': 0.5, 'f': 0.5, 'g': 0.5, 'h': 0.5, 'i': 0.5, 'j': 0.5}
    new = wf(boost, 700_000, 2_000_000, 1000, True)
    assert new == _old_clip(boost, 700_000, 2_000_000, 1000)


def test_waterfill_spends_clipped_excess():
    wf = _lift(COAL, 'coal_waterfill')
    boost = {'a': 10.0, 'b': 5.0, 'c': 1.0, 'd': 1.0, 'e': 1.0, 'f': 1.0, 'g': 1.0, 'h': 1.0}
    cap, budget = 400_000, 2_000_000
    old = _old_clip(boost, cap, budget, 1000)
    new = wf(boost, cap, budget, 1000, True)
    assert sum(old.values()) < budget - 100_000            # negative control: the old rule underspends
    assert abs(sum(new.values()) - budget) <= 500 * len(boost)   # rounding only
    assert max(new.values()) <= cap
    assert new['a'] == cap and new['b'] == cap
    rest = [new[n] for n in 'cdefgh']
    assert max(rest) - min(rest) == 0                       # equal marginals -> equal share
    assert wf(boost, cap, budget, 1000, False) == old       # dial off = exact old clip


def test_waterfill_iterates_and_exhausts():
    wf = _lift(COAL, 'coal_waterfill')
    # second-round cap: after a is pinned, b's re-split share exceeds cap too
    boost = {'a': 100.0, 'b': 30.0, 'c': 1.0, 'd': 1.0}
    new = wf(boost, 800_000, 2_000_000, 1000, True)
    assert new['a'] == 800_000 and new['b'] == 800_000 and new['c'] == new['d'] == 200_000
    # every member caps: real headroom exhaustion, left unspent, never over cap
    tiny = wf({'a': 1.0, 'b': 1.0}, 50_000, 2_000_000, 1000, True)
    assert tiny == {'a': 50_000, 'b': 50_000}
    assert wf({}, 50_000, 2_000_000, 1000, True) == {}


def _engine_knee(path, raw, cap=50000):   # verbatim budget_frontier forward rule
    k = 'spread_raw' if raw else 'spread'
    margs = [path[i][k] - path[i - 1][k] for i in range(1, len(path))]
    peak = max(margs) if margs else 0
    knee = 0
    for i, mg in enumerate(margs):
        if mg >= 0.25 * peak:
            knee = (i + 1) * cap
    return knee, 0 < knee < path[-1]['b']


def _mkpath(raws, cap=50000):
    path, run = [], None
    for i, r in enumerate(raws):
        run = r if run is None else max(run, r)
        path.append({'b': i * cap, 'spread': round(run, 1), 'spread_raw': round(r, 1), 'seed': None if not i else 's%d' % i})
    return path


def test_knee_rederive_matches_engine_rule():
    kr = _lift(AFRONT, 'knee_rederive')
    rnd = random.Random(11)
    for _ in range(300):
        n = rnd.randint(0, 14)
        raws = [20.0]
        for _ in range(n):
            raws.append(raws[-1] + rnd.uniform(-1.5, 6.0))
        path = _mkpath(raws)
        for raw in (True, False):
            assert kr(path, raw, 50000) == _engine_knee(path, raw)


def test_knee_raw_vs_clamped_differ_and_old_artifact_fallback():
    kr = _lift(AFRONT, 'knee_rederive')
    path = _mkpath([10.0, 20.0, 18.0, 30.0, 30.4])
    assert kr(path, True)[0] != 0
    old = [{k: v for k, v in p.items() if k != 'spread_raw'} for p in path]
    assert kr(old, True) == kr(path, False)                  # artifact without spread_raw -> clamped fallback
    assert kr([{'b': 0, 'spread': 5.0, 'spread_raw': 5.0, 'seed': None}], True) == (0, False)


def test_seed_offset_zero_at_default_and_decorrelates():
    from moneyball_core import sm64
    for p in (COAL, FRONT):
        assert '_SO=(SEED-7)*0x9E3779B97F4A7C15' in open(p, encoding='utf-8').read()
    so = lambda seed: (seed - 7) * 0x9E3779B97F4A7C15
    assert so(7) == 0
    keys = [it * 533 * 533 + 12 * 533 + j for it in range(3) for j in range(50)]
    assert [sm64(k + so(7)) for k in keys] == [sm64(k) for k in keys]                    # default bytes unchanged
    assert sum(sm64(k + so(8)) == sm64(k) for k in keys) == 0 and so(8) % 2 == 1   # other seeds share no draw with seed 7
    assert all(0 <= sm64(k + so(3)) < 1 for k in keys)                                   # negative offsets stay in range


def _ck_sites(path):
    tree = ast.parse(open(path, encoding='utf-8').read())
    total = 0

    def walk(node, w):
        nonlocal total
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, ast.FunctionDef):
                continue                      # the ck() definition itself
            wt = w
            if isinstance(ch, ast.For) and isinstance(ch.iter, (ast.List, ast.Tuple)):
                wt = w * len(ch.iter.elts)
            if isinstance(ch, ast.Call) and getattr(ch.func, 'id', None) == 'ck':
                total += w
            walk(ch, wt)
    walk(tree, 1)
    return total


def test_audit_frontier_floor_is_exact():
    n = _ck_sites(AFRONT)
    m = re.search(r"audit_frontier\.py','frontier \((\d+)\)',(\d+)\)", open(AFULL, encoding='utf-8').read())
    assert m and int(m.group(1)) == int(m.group(2)) == n == 15
