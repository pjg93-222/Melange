# -*- coding: utf-8 -*-
"""F4 desk metrics (Paul 2026-09-30: "F4. Proceed"; the ROI gate follows "F1. Yes").

FIXTURE ONLY. Synthetic rows, no live tree read, nothing written outside tmp_path.

make_member_desk.py, build_dashboard_bundle.py, flip_model.py and efficiency_layers.py all execute on
import (workbook, network and artifact reads), so every function under test is lifted out of the shipped
source with ast and run on its own -- the real function bodies, none of those modules imported. Only the
import-safe kernel (moneyball_core) and district.demographic_normalization are imported.

  gap       desk_plan_fields: the plan's increment above existing CU money, never negative.
  eff_value desk_eff_values: midrank percentiles, so a row shuffle changes nothing.
  rounding  build_dashboard_bundle.opt_alloc_thousands keeps a $500 allocation non-zero, and
            efficiency_layers._load_dashboard rebuilds its exact dollars.
  ROI       desk_roi equals flip_model's own topic_setup + pflip on a fixture, counts Highly Skeptical
            as anti like the engine, and is 0 for a member the optimizer's stance gate excludes.
  peer max  2026-10-01 (Paul: "Match backend"): desk_roi and the dashboard template's flipModel divide
            peer pressure by the REAL camp maximum, 1 only when it is 0, like flip_model.topic_setup.
            Checked on a fixture whose maxima all lie strictly between 0 and 1, on the system logic
            review's own three-member fixture, and desk-vs-browser by running the template's JS in node.
Each carries a negative control showing the test fails on the pre-fix rule.
"""
from __future__ import annotations

import ast
import inspect
import json
import math
import os
import random
import shutil
import subprocess
import sys
import types

import pytest

FEC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if FEC not in sys.path:
    sys.path.insert(0, FEC)
import moneyball_core as MC  # noqa: E402  import-safe kernel: lazy loaders, reads no data at import
import district.demographic_normalization as DN  # noqa: E402  pure helpers (the desk's midrank rule)

DESK = os.path.join(FEC, 'surfaces', 'make_member_desk.py')
BUNDLE = os.path.join(FEC, 'surfaces', 'build_dashboard_bundle.py')
EFFICIENCY = os.path.join(FEC, 'engine', 'efficiency_layers.py')
FLIP_MODEL = os.path.join(FEC, 'engine', 'flip_model.py')
KERNEL = os.path.join(FEC, 'moneyball_core.py')
DASH_TPL = os.path.join(FEC, 'surfaces', 'templates', 'make_dashboard_html_00.tpl')
# The node lookup test_dashboard_honors uses for the same template.
NODE = shutil.which('node') or os.path.join(os.path.expanduser('~'), '.cache', 'codex-runtimes',
                                            'codex-primary-runtime', 'dependencies', 'node', 'bin', 'node.exe')


def _source(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def _targets(node):
    return {sub.id for target in node.targets for sub in ast.walk(target) if isinstance(sub, ast.Name)}


def _lift(path, functions=(), assigns=(), classes=(), namespace=None):
    """Compile ONLY the named module-level defs, classes and assignments of a file."""
    tree = ast.parse(_source(path), filename=path)
    body = [node for node in tree.body
            if (isinstance(node, ast.FunctionDef) and node.name in functions)
            or (isinstance(node, ast.ClassDef) and node.name in classes)
            or (isinstance(node, ast.Assign) and _targets(node) & set(assigns))]
    found = {getattr(node, 'name', None) for node in body} | {t for node in body
                                                              if isinstance(node, ast.Assign)
                                                              for t in _targets(node)}
    missing = (set(functions) | set(classes) | set(assigns)) - found
    assert not missing, '%s no longer defines %s at module scope' % (path, sorted(missing))
    ns = dict(namespace or {})
    exec(compile(ast.Module(body=body, type_ignores=[]), path, 'exec'), ns)  # noqa: S102 - vetted defs
    return ns


DESK_NS = _lift(DESK, functions=('desk_roi', 'desk_eff_values', 'desk_plan_fields'), assigns=('TIERNAME',))
DESK_ROI, EFF_VALUES, PLAN = DESK_NS['desk_roi'], DESK_NS['desk_eff_values'], DESK_NS['desk_plan_fields']
TIERNAME = DESK_NS['TIERNAME']
LETTER = {name: letter for letter, name in TIERNAME.items()}
ENCODE = _lift(BUNDLE, functions=('opt_alloc_thousands',))['opt_alloc_thousands']


# ---------------------------------------------------------------- gap
def test_gap_is_the_plan_increment_and_never_negative():
    assert list(inspect.signature(PLAN).parameters) == ['planned']   # gap cannot depend on invested
    for planned in (0, 500, 10000, 7500.0, None):
        opt_alloc, gap = PLAN(planned)
        assert gap >= 0 and gap == opt_alloc == round(planned or 0)
    assert PLAN(-500) == (-500, 0)                         # defensive: never shown as negative
    # Sherman on the 2026-09-20 chain: $35,500 already invested, the plan adds $10,000. The desk used to
    # show opt_alloc - invested = -$25,500 in red; it now shows the $10,000 the plan adds.
    assert PLAN(10000) == (10000, 10000)


def test_desk_no_longer_subtracts_invested_from_the_increment():
    compact = _source(DESK).replace(' ', '')
    assert "rec['opt_alloc'],rec['gap']=desk_plan_fields(OPT_ALLOC.get(rec['name'],0))" in compact
    assert "oa-round(rec.get('invested')" not in compact


# ---------------------------------------------------------------- eff_value
def _pre_fix_eff_values(scores, invested):
    """The rule before 2026-09-30, verbatim from make_member_desk.py: stable sort, ties by row order."""
    n = len(scores)

    def pct_rank(values):
        order = sorted(range(n), key=lambda i: (values[i] or 0))
        pr = {}
        for r, i in enumerate(order): pr[i] = (r / (n - 1)) if n > 1 else 0
        return pr
    spct, ipct = pct_rank(scores), pct_rank(invested)
    return [round(spct[i] - ipct[i], 3) for i in range(n)]


def _tied_rows():
    rng = random.Random(20260930)
    rows = []
    for k in range(80):
        invested = 0 if k < 30 else 1000 if k < 50 else 5000 if k < 60 else 7000 + 250 * k
        score = round(rng.uniform(10, 90), 1) if k % 7 else 50.0    # a tie block in score as well
        rows.append(('member %02d' % k, score, invested if k != 5 else None))
    return rows


def _by_member(rows, rule):
    values = rule([score for _n, score, _i in rows], [inv for _n, _s, inv in rows])
    return {name: value for (name, _s, _i), value in zip(rows, values)}


def _midrank(scores, invested):
    return EFF_VALUES(scores, invested, DN.midrank_percentiles)


def test_eff_value_is_order_invariant_under_ties():
    rows = _tied_rows()
    base = _by_member(rows, _midrank)
    changed = 0
    for seed in range(40):
        shuffled = list(rows)
        random.Random(seed).shuffle(shuffled)
        again = _by_member(shuffled, _midrank)
        changed += sum(1 for name in base if again[name] != base[name])
    assert changed == 0


def test_pre_fix_rule_fails_the_same_shuffle():
    rows = _tied_rows()
    base = _by_member(rows, _pre_fix_eff_values)
    shuffled = list(rows)
    random.Random(1).shuffle(shuffled)
    again = _by_member(shuffled, _pre_fix_eff_values)
    assert sum(1 for name in base if again[name] != base[name]) > 0   # the suite can fail


def test_tied_members_share_one_percentile_and_untied_rows_are_unchanged():
    rows = _tied_rows()
    values = _by_member(rows, _midrank)
    same_score_zero_invested = [name for name, score, inv in rows if score == 50.0 and not inv]
    assert len(same_score_zero_invested) >= 2
    assert len({values[name] for name in same_score_zero_invested}) == 1
    distinct = [('m%d' % k, 10.0 + k * 1.5, 100 * k + 1) for k in range(40)]
    assert (_by_member(distinct, _midrank) == _by_member(distinct, _pre_fix_eff_values))   # no ties: identical


# ---------------------------------------------------------------- rounding
def test_rounding_keeps_a_500_allocation_non_zero_and_exact():
    for dollars in range(0, 20001, 500):
        value = ENCODE(dollars)
        assert value * 1000 == dollars
        if dollars % 1000 == 0:
            assert isinstance(value, int)                  # whole thousands keep the old bytes
    assert ENCODE(500) == 0.5 and ENCODE(10500) == 10.5
    assert round(500 / 1000) == 0 and round(10500 / 1000) == 10   # negative control: the old encoding lost both
    assert abs(ENCODE(1234) * 1000 - 1234) < 1e-9
    assert json.loads(json.dumps([ENCODE(500), ENCODE(10000), ENCODE(10500)])) == [0.5, 10, 10.5]


def _load_dashboard():
    ns = _lift(EFFICIENCY, functions=('_load_json', '_number', '_integer', '_load_dashboard'),
               classes=('EfficiencyLayersError',), namespace={'json': json, 'math': math})
    return ns['_load_dashboard']


def _dashboard(tmp_path, alloc_pairs):
    doc = {'name': ['Planned Ten', 'Planned Five Hundred', 'Planned Fifteen Hundred'],
           'party': 'DRD', 'engine': {'cu': [0, 0, 0], 'ind': [0, 0, 0]},
           'opt': {'alloc': alloc_pairs}}
    path = tmp_path / 'dashboard_data.json'
    path.write_text(json.dumps(doc), encoding='utf-8')
    return str(path)


def test_efficiency_layers_rebuilds_exact_dollars_from_the_bundle(tmp_path):
    plan = {0: 10000, 1: 500, 2: 1500}
    load = _load_dashboard()
    _doc, records, present = load(_dashboard(tmp_path, [[i, ENCODE(v)] for i, v in plan.items()]))
    assert present
    assert [records[name]['engine_allocation_dollars'] for name in
            ('Planned Ten', 'Planned Five Hundred', 'Planned Fifteen Hundred')] == [10000.0, 500.0, 1500.0]
    _doc, old, _present = load(_dashboard(tmp_path, [[i, round(v / 1000)] for i, v in plan.items()]))
    assert old['Planned Five Hundred']['engine_allocation_dollars'] == 0.0      # negative control
    assert old['Planned Fifteen Hundred']['engine_allocation_dollars'] == 2000.0


# ---------------------------------------------------------------- ROI
NAMES = ['Ann Pro', 'Ben Swing', 'Cal Swing', 'Dee Deep', 'Eve Opp', 'Fay Mild']
PARTY = {'Ann Pro': 'D', 'Ben Swing': 'D', 'Cal Swing': 'R', 'Dee Deep': 'R', 'Eve Opp': 'R', 'Fay Mild': 'I'}
ISSUES = ('Interchange', 'Payments')
# Per-category cells. Dee's two Highly Skeptical cells make an overall Opponent; Eve is an overall
# Opponent who still holds a mild Payments cell. Both are behind the optimizer's stance gate.
MATRIX = {
    'Ann Pro': {'Interchange': 'Champion', 'Payments': 'Ally'},
    'Ben Swing': {'Interchange': 'Persuadable', 'Payments': 'Lean Persuadable'},
    'Cal Swing': {'Interchange': 'Highly Persuadable', 'Payments': 'True Neutral'},
    'Dee Deep': {'Interchange': 'Highly Skeptical', 'Payments': 'Highly Skeptical'},
    'Eve Opp': {'Interchange': 'Opponent', 'Credit Card Mandates': 'Opponent', 'Payments': 'Persuadable'},
    'Fay Mild': {'Payments': 'Lean Persuadable'},
}
EDGES = [('Ann Pro', 'Ben Swing', 2.0), ('Ann Pro', 'Cal Swing', 1.5), ('Ben Swing', 'Dee Deep', 1.2),
         ('Cal Swing', 'Dee Deep', 2.5), ('Ben Swing', 'Eve Opp', 1.0), ('Cal Swing', 'Fay Mild', 0.8),
         ('Dee Deep', 'Eve Opp', 1.1), ('Ann Pro', 'Fay Mild', 0.9)]
CU = [0, 5000, 0, 20000, 0, 0]
IND = [50000, 60000, 45000, 50000, 55000, 40000]
RECEIPTS = [1000000, 800000, 1200000, 1000000, 900000, 1000000]
ENGAGEMENT = [[0.5, 1.2, 0.8, 0.3, 0.9, 0.4], [0.2, 0.6, 1.1, 0.1, 0.7, 0.5]]
PRIORITY = [[1.0, 0.7, 0.6, 0.2, 0.3, 0.4], [0.9, 0.5, 0.8, 0.1, 0.2, 0.6]]
BPF = [0.3, 0.2, 0.25, 0.1, 0.15, 0.2]
PMULT = [1.0, 1.1, 0.9, 1.0, 1.2, 0.95]
DMULT = [1.0, 0.9, 1.0, 0.85, 1.0, 0.95]


def _engine_const():
    fm = _lift(FLIP_MODEL, assigns=('WM', 'WP', 'HALFF', 'BASE'), namespace={'os': os})
    return {'WM': fm['WM'], 'WP': fm['WP'], 'HALFF': fm['HALFF'], 'BASE': fm['BASE'],
            'SRCPRO': 1.7, 'SRCANTI': 0.5}


def _desk_inputs(scale=1.0):
    """The dashboard bundle's shapes: issue rows plus the appended Overall row the ROI loop skips.
    `scale` multiplies every edge weight; SUB_ONE puts every camp maximum strictly between 0 and 1."""
    overall = [MC.overall_tier(MATRIX[n]) for n in NAMES]
    stance = [''.join(LETTER[MATRIX[n].get(c, '—')] for c in ISSUES) + LETTER[o] for n, o in zip(NAMES, overall)]
    mean = [round(sum(row[k] for row in ENGAGEMENT) / len(ENGAGEMENT), 3) for k in range(len(NAMES))]
    eng = {'const': _engine_const(), 'pers': dict(MC.PERS), 'cu': CU, 'ind': IND, 'rcp': RECEIPTS,
           'tierp': [0.5] * len(NAMES), 'bpf': BPF, 'eng': ENGAGEMENT + [mean],
           'priority': PRIORITY + [PRIORITY[0]], 'pmult': PMULT, 'dmult': DMULT}
    idx = {n: i for i, n in enumerate(NAMES)}
    adj = {}
    for a, b, w in EDGES:
        adj.setdefault(idx[a], []).append((idx[b], w * scale))
        adj.setdefault(idx[b], []).append((idx[a], w * scale))
    return eng, stance, adj, ''.join(PARTY[n] for n in NAMES)


SUB_ONE = 0.1


def _engine_roi(anti=None, scale=1.0, floor_at_one=False):
    """flip_model's OWN topic_setup + pflip (lifted), summed like optimize.marg_at for one $10k chunk.
    Returns the ROI and each issue's (mAt, mBt). floor_at_one replays the desk/browser rule before
    2026-10-01, max(1, camp maximum), on the engine's own arithmetic: the negative control."""
    cpf = _lift(KERNEL, functions=('cpf_pressure',), namespace={'party': lambda: PARTY})['cpf_pressure']
    idx = {n: i for i, n in enumerate(NAMES)}
    stub_mc = types.SimpleNamespace(priority_base_signal=MC.priority_base_signal,
                                    delivery_mult=lambda n: DMULT[idx[n]])
    namespace = {
        'os': os, 'members': list(NAMES), '_cache': {}, '_rowcache': {}, 'PERS': MC.PERS, 'MC': stub_mc,
        'adj': {n: {} for n in NAMES}, 'cpf': cpf, 'bpf': {n: BPF[idx[n]] for n in NAMES},
        'cat2sc': {c: k for k, c in enumerate(ISSUES)},
        'eng': {k: {n: ENGAGEMENT[k][idx[n]] for n in NAMES} for k in range(len(ISSUES))},
        'topic_priority': lambda cat, mode: {n: PRIORITY[ISSUES.index(cat)][idx[n]] for n in NAMES},
    }
    for a, b, w in EDGES:
        namespace['adj'][a][b] = w * scale
        namespace['adj'][b][a] = w * scale
    fm = _lift(FLIP_MODEL, functions=('pflip', 'camp', 'topic_setup', '_stance_rows'),
               assigns=('WM', 'WP', 'HALFF', 'BASE', 'PRO', 'ANTI'), namespace=namespace)
    if anti is not None:
        fm['ANTI'] = anti
    rows = {n: dict(MATRIX[n]) for n in NAMES}
    roi = [0.0] * len(NAMES)
    maxima = []
    for c in ISSUES:
        _cs, _camp, nA, nB, mAt, mBt, tgt = fm['topic_setup'](c, rows)
        if floor_at_one:
            mAt, mBt = max(1.0, mAt), max(1.0, mBt)
        maxima.append((mAt, mBt))
        for n in NAMES:
            i = idx[n]
            args = (IND[i], RECEIPTS[i], nA[n], nB[n], mAt, mBt, PMULT[i])
            roi[i] += tgt[n] * (fm['pflip'](CU[i] + 10000.0, *args) - fm['pflip'](CU[i], *args))
    return roi, maxima


def test_desk_roi_matches_the_engine_on_a_fixture():
    # 2026-10-01 (Paul: "Match backend"): the desk divides by the real camp maximum, as flip_model does.
    # Until then it floored each maximum at 1 and this test could only use a fixture with every maximum
    # >= 1; parity now has to hold there AND on the same fixture scaled so every maximum is below 1.
    for scale in (1.0, SUB_ONE):
        engine, maxima = _engine_roi(scale=scale)
        eng, stance, adj, party = _desk_inputs(scale)
        desk = DESK_ROI(eng, stance, TIERNAME, adj, party)
        assert all(abs(d - e) <= 1e-12 for d, e in zip(desk, engine)), (scale, list(zip(desk, engine)))
        assert sum(1 for value in engine if value > 0) >= 4              # a non-trivial fixture
    assert all(0.0 < m < 1.0 for pair in maxima for m in pair), maxima     # the case the ruling changed


def test_pre_ruling_floor_fails_the_sub_one_parity():
    eng, stance, adj, party = _desk_inputs(SUB_ONE)
    desk = DESK_ROI(eng, stance, TIERNAME, adj, party)
    floored, _maxima = _engine_roi(scale=SUB_ONE, floor_at_one=True)
    assert max(abs(d - f) for d, f in zip(desk, floored)) > 1e-6       # the parity test can fail
    compact = _source(DESK).replace(' ', '')
    assert 'mA=max(nA)or1.0;mB=max(nB)or1.0' in compact
    assert 'max(1.0,max(nA))' not in compact and 'max(1.0,max(nB))' not in compact


# The system logic review's independent fixture (audits/qme_fix_round_20260930/SYSTEM_LOGIC_REVIEW.md,
# P2 finding; quant_logic_review/quant_logic_review.py): a pro, an anti and a neutral member, CU $1,000,
# industry $2,000, receipts $200,000, persuadability .5, engagement 1, priority contribution .15. The
# neutral member's next-$10,000 ROI is 0.575 * (pflip(11000) - pflip(1000)). The review spelled True
# Neutral with a private letter 'N'; the shipped letter is 'T' (TIERNAME and the template's SCN), so the
# same fixture runs through the desk and the browser unchanged.
REVIEW_BACKEND = 0.021468455244484982    # backend algebra; the same at camp maximum .1 and 2
REVIEW_FLOORED = 0.11724112402938276     # the desk at camp maximum .1 before the ruling


def _review_fixture(weight):
    eng = {'const': {'WM': .35, 'WP': .65, 'HALFF': .1, 'BASE': .15, 'SRCPRO': 1., 'SRCANTI': 1.},
           'pers': {'Champion': 0., 'Opponent': 0., 'True Neutral': .5},
           'cu': [1000.] * 3, 'ind': [2000.] * 3, 'rcp': [200000.] * 3, 'tierp': [1.] * 3, 'bpf': [0.] * 3,
           'eng': [[1.] * 3, [1.] * 3]}
    adj = {0: [(2, weight)], 1: [(2, weight)], 2: [(0, weight), (1, weight)]}
    return eng, ['CC', 'OO', 'TT'], adj, 'DDD'


def _review_algebra(weight, floor_at_one=False):
    """Independent flip_model algebra for the neutral member: both camp maxima equal `weight`."""
    peak = max(1.0, weight) if floor_at_one else (weight or 1.0)
    def pf(cu):
        a = .35 * (cu + 1) / (cu + 1 + .1 * 200000) + .65 * weight / peak
        b = .35 * 2001 / (2001 + .1 * 200000) + .65 * weight / peak
        return a / (a + b)
    return (1 + .15 * 1) * .5 * (pf(11000) - pf(1000))


def test_review_fixture_desk_equals_backend_algebra():
    for weight in (0.1, 2.0):                    # the exposed camp maximum, and the max-2 control
        eng, stance, adj, party = _review_fixture(weight)
        desk = DESK_ROI(eng, stance, TIERNAME, adj, party)
        assert abs(desk[2] - _review_algebra(weight)) <= 1e-12, (weight, desk)
        assert abs(desk[2] - REVIEW_BACKEND) <= 1e-12, (weight, desk)
        assert desk[0] == desk[1] == 0.0                                  # zero persuadability
        assert DESK_ROI(eng, stance, TIERNAME, adj, party, gated={2})[2] == 0.0
    # Negative control: the old floor reproduces the review's pre-ruling desk value, at .1 only.
    assert abs(_review_algebra(0.1, floor_at_one=True) - REVIEW_FLOORED) <= 1e-12
    assert abs(_review_algebra(2.0, floor_at_one=True) - REVIEW_BACKEND) <= 1e-12
    assert REVIEW_FLOORED - REVIEW_BACKEND > 0.09


def _browser_roi(eng, stance, adj, party):
    """The dashboard template's OWN flipModel and align, sliced from the .tpl as test_dashboard_honors
    does, run under node: the next-$10k finite difference per member over the real issues, plus each
    issue's (mA, mB)."""
    if not os.path.isfile(NODE):
        pytest.skip('Node runtime unavailable')
    source = _source(DASH_TPL)
    engine = source[source.index('const SCN='):source.index('// stance-integrity gates')]
    align = next(line for line in source.splitlines() if line.startswith('function align('))
    n = len(stance)
    fixture = {'DATA': {'stance': stance},
               'EG': {'pers': eng['pers'], 'theta': {}, 'eng': eng['eng'], 'priority': eng.get('priority'),
                      'tierp': eng['tierp'], 'rcp': eng['rcp']},
               'K': eng['const'], 'PM': eng.get('pmult'), 'DM': eng.get('dmult'), 'BPF': eng['bpf'],
               'ADJ': [{str(v): w for v, w in adj.get(u, [])} for u in range(n)], 'PTY': list(party),
               'cu': eng['cu'], 'ind': eng['ind']}
    script = '''
const F=__FIXTURE__;const DATA=F.DATA,EG=F.EG,K=F.K,PM=F.PM,DM=F.DM,BPF=F.BPF,ADJ=F.ADJ,PTY=F.PTY,N=DATA.stance.length;
__ALIGN__
__ENGINE__
const roi=new Array(N).fill(0),peaks=[];
for(let i=0;i<EG.eng.length-1;i++){const t=baseTiers(i),base=flipModel(i,t,F.cu,F.ind);peaks.push([base.mA,base.mB]);
  for(let u=0;u<N;u++){const cu=F.cu.slice();cu[u]+=10000;roi[u]+=base.tg[u]*(flipModel(i,t,cu,F.ind).pf[u]-base.pf[u]);}}
console.log(JSON.stringify({roi,peaks}));
'''.replace('__FIXTURE__', json.dumps(fixture)).replace('__ALIGN__', align).replace('__ENGINE__', engine)
    result = subprocess.run([NODE, '-e', script], capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    return out['roi'], [tuple(pair) for pair in out['peaks']]


def test_browser_flip_model_matches_the_desk_and_the_backend_peer_maximum():
    for scale in (1.0, SUB_ONE):
        eng, stance, adj, party = _desk_inputs(scale)
        desk = DESK_ROI(eng, stance, TIERNAME, adj, party)
        browser, peaks = _browser_roi(eng, stance, adj, party)
        _engine, maxima = _engine_roi(scale=scale)
        assert all(abs(b - d) <= 1e-12 for b, d in zip(browser, desk)), (scale, list(zip(browser, desk)))
        assert all(abs(p - m) <= 1e-12 for pp, mm in zip(peaks, maxima) for p, m in zip(pp, mm)), (peaks, maxima)
    for weight in (0.1, 2.0):
        eng, stance, adj, party = _review_fixture(weight)
        browser, peaks = _browser_roi(eng, stance, adj, party)
        assert abs(browser[2] - REVIEW_BACKEND) <= 1e-12, (weight, browser)
        assert peaks == [(weight, weight)]
    # Negative control: the template no longer floors its maxima at 1.
    source = _source(DASH_TPL).replace(' ', '')
    assert 'constmA=Math.max(...nA)||1,mB=Math.max(...nB)||1;' in source
    assert 'letmA=1,mB=1;' not in source


def test_highly_skeptical_neighbours_count_as_anti_like_the_engine():
    eng, stance, adj, party = _desk_inputs()
    desk = DESK_ROI(eng, stance, TIERNAME, adj, party)
    pre_fix, _floors = _engine_roi(anti={'Opponent', 'Skeptic'})     # 'K' neutral, the old desk letters
    assert max(abs(d - p) for d, p in zip(desk, pre_fix)) > 1e-6         # the parity test can fail
    assert "'anti'iftin'OSK'" in _source(DESK).replace(' ', '')


def test_stance_gated_members_show_no_roi():
    eng, stance, adj, party = _desk_inputs()
    tiers = MC.stance_gate_tiers({'matrix': MATRIX, 'gate': {}}, NAMES)
    gated = frozenset(i for i, n in enumerate(NAMES) if tiers[n] in MC.STANCE_GATE_BLOCKED)
    assert {NAMES[i] for i in gated} == {'Dee Deep', 'Eve Opp'}
    open_roi = DESK_ROI(eng, stance, TIERNAME, adj, party)
    gated_roi = DESK_ROI(eng, stance, TIERNAME, adj, party, gated=gated)
    assert all(open_roi[i] > 0 for i in gated)                           # the gate is not vacuous here
    assert all(gated_roi[i] == 0.0 for i in gated)
    assert all(gated_roi[i] == open_roi[i] for i in range(len(NAMES)) if i not in gated)


def test_desk_reads_the_gate_from_the_kernel_helper():
    compact = _source(DESK).replace(' ', '')
    assert '_GATE_TIERS=MBC.stance_gate_tiers(CS,snames)' in compact
    assert 'if_GATE_TIERS.get(n)inMBC.STANCE_GATE_BLOCKED' in compact
    assert 'ROI=desk_roi(eng,STANCE,TIERNAME,ADJ,PARTY_SNA,gated=ROI_GATED,chunk=CHUNK)' in compact
