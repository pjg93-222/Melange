# -*- coding: utf-8 -*-
"""M7-texture (2026-10-26): the chain step `personal_texture_layer.py --refresh-local` must classify
semantic-gate windows that are new to the corpus, not only re-run superseded local judgments.

Attempt 9 (audits/congress_pipeline/20261022T180457Z/pipeline.log:39) wrote 9490 candidates and
6244 classified against a 6545-window semantic gate, so audit_full's
'personal-texture artifact precision/schema/provenance' check failed.  The gate count is
len(select_for_semantic_gate(rows)), derived from data each run; the shortfall was the uncached
windows the refresh path skipped."""
import importlib.util, os, sys
from pathlib import Path

FEC = Path(__file__).resolve().parents[2]


def _load(tmp_path):
    (tmp_path / 'data' / 'engine').mkdir(parents=True)
    (tmp_path / 'data' / 'engine' / 'congestion.json').write_text('[]', encoding='utf-8')
    prior = os.environ.get('MONEYBALL_ROOT')
    os.environ['MONEYBALL_ROOT'] = str(tmp_path)
    sys.modules.pop('paths', None)
    try:
        spec = importlib.util.spec_from_file_location('personal_texture_under_test',
                                                      FEC / 'members' / 'personal_texture_layer.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if prior is None: os.environ.pop('MONEYBALL_ROOT', None)
        else: os.environ['MONEYBALL_ROOT'] = prior
        sys.modules.pop('paths', None)


def test_refresh_local_classifies_new_and_superseded_windows_but_never_fable(tmp_path):
    m = _load(tmp_path)
    rows = [{'key': k} for k in ('new', 'fable', 'v5', 'v6')]
    cache = {'fable': {'classifier': 'fable'},
             'v5': {'classifier': 'local_explicit_v5'},
             'v6': {'classifier': m.LOCAL_CLASSIFIER}}
    assert [r['key'] for r in m.local_todo(rows, cache, refresh=True)] == ['new', 'v5']
    # --local keeps its old meaning: uncached windows only.
    assert [r['key'] for r in m.local_todo(rows, cache)] == ['new']
    # After the refresh pass every semantic-gate window holds a judgment, so classified >= gate.
    for r in m.local_todo(rows, cache, refresh=True):
        cache[r['key']] = {'classifier': m.LOCAL_CLASSIFIER}
    assert all(r['key'] in cache for r in rows)


def test_gate_coverage_counts_semantic_gate_windows_not_every_cached_candidate(tmp_path):
    """M7-texture denominator: provenance classified_count spans every candidate row, but the gate is
    len(select_for_semantic_gate(rows)).  On the 2026-10-28 replay 485 cached non-gate rows made
    classified_count 7029 >= gate 6547 while 3 gate windows were still unjudged.  The artifact must
    report gate coverage on the gate's own denominator, and audit_full must compare that field."""
    m = _load(tmp_path)
    (tmp_path / 'data' / 'members').mkdir(parents=True)
    m.OUT = str(tmp_path / 'data' / 'members' / 'member_personal_texture.json')
    row = lambda k: {'key': k, 'member': 'A', 'source': 'CREC', 'date': '', 'locator': '', 'url': '',
                     'evidence': 'x', 'hints': ['family']}
    gate = [row('g1'), row('g2')]
    rows = gate + [row('old')]
    no = {'keep': False, 'category': 'other', 'claim': '', 'confidence': 'low', 'reason': '',
          'classifier': m.LOCAL_CLASSIFIER}
    m.write_artifact(rows, {'g1': no, 'old': no}, gate)
    import json
    pp = json.loads(open(m.OUT, encoding='utf-8').read())['provenance']
    assert (pp['classified_count'], pp['semantic_gate_count']) == (2, 2)   # the old comparison passes
    assert pp['semantic_gate_classified_count'] == 1                      # but g2 is unjudged
    audit = (FEC / 'audit' / 'audit_full.py').read_text(encoding='utf-8')
    assert "_pp.get('semantic_gate_classified_count',-1)>=_pp.get('semantic_gate_count',1)" in audit
    assert "_pp.get('classified_count',0)>=_pp.get('semantic_gate_count',1)" not in audit
