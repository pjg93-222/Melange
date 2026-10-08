"""Small independent fixtures for September 5 audit repairs; no live DB or builds."""
from datetime import date
from pathlib import Path
import sys

import numpy as np
import pytest
from scipy import sparse

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from audits.staffer_network import build_staffer_social_network as builder
from audits.staffer_network import verify_staffer_social_network as verifier
from fec.surfaces import build_staffer_network_section as section


def test_possible_overlap_unions_duplicates_adjacent_and_disjoint_containers():
    keys, days = builder.union_pair_days([20,10,20,10,10,30], [10,0,15,5,30,1], [20,10,30,20,35,99], [30])
    assert keys.tolist() == [10,20]
    assert days.tolist() == [25,20]
    empty, durations = builder.union_pair_days([], [], [])
    assert empty.size == durations.size == 0


def test_possible_pair_exclusion_works_across_chunk_boundaries_without_isin(monkeypatch):
    monkeypatch.setattr(np, 'isin', lambda *args, **kw: (_ for _ in ()).throw(AssertionError('unbounded isin')))
    keys = np.repeat([1, 21_000_000_000], 250_001)
    kept, days = builder.union_pair_days(keys, np.ones(keys.size), np.full(keys.size, 5), [21_000_000_000])
    assert kept.tolist() == [1] and days.tolist() == [4]


@pytest.mark.parametrize('tiers', [{}, {'person':'UNKNOWN'}, {'person':None}])
def test_missing_or_unknown_tiers_cannot_become_strongest(tiers):
    with pytest.raises(builder.BuildError, match='identity tier'):
        builder.validated_person_tiers(['person'], tiers)


def test_valid_tiers_preserve_order_and_strength():
    assert builder.validated_person_tiers(['b','a'], {'a':'S1','b':'S3'}) == ['S3','S1']


def test_repair_matches_dense_eigenpair_and_is_rng_independent():
    matrix = sparse.csr_matrix([[0.,2,0],[2,0,1],[0,1,0]])
    expected, _ = np.linalg.eigh(matrix.toarray())
    np.random.seed(3)
    value, vector = builder.deterministic_leading_eigenpair(matrix)
    np.random.seed(916)
    again, second = builder.deterministic_leading_eigenpair(matrix)
    assert value == pytest.approx(expected[-1], abs=1e-12)
    assert np.linalg.norm(matrix @ vector - value*vector) < 1e-12
    assert vector.sum() == pytest.approx(1)
    assert value == again and np.array_equal(vector, second)


def test_tenure_union_does_not_join_a_gap_or_double_count_assignments():
    d=lambda day:date(2026,1,day)
    assert section.union_tenure_days([(d(1),d(5)),(d(3),d(8)),(d(8),d(10)),(d(12),d(14))]) == 11
    assert section.union_tenure_days([]) == 0
    with pytest.raises(section.InputContradiction):
        section.union_tenure_days([(d(8),d(1))])


def score_fixture():
    transition=verifier.independent_transition(4,[0,0],[1,2],[2.,1.],[0,1])
    expected=np.array([[0,.5,.5,0],[1,0,0,0],[1,0,0,0],[0,0,0,0]])
    assert np.array_equal(transition.toarray(),expected)
    v=np.array([1/6,1/6,1/3,1/3])
    dangling=np.array([0.,0,0,1])
    p=expected.T+np.outer(v,dangling)
    ranks={a:np.linalg.solve(np.eye(4)-a*p,(1-a)*v) for a in (.7,.85,.95)}
    values,vectors=np.linalg.eigh((expected[:3,:3]+expected[:3,:3].T)/2)
    vec=np.abs(vectors[:,-1]);vec/=vec.sum()
    eigen=np.r_[vec,0.]
    return transition,['person','person','container','organization'],ranks,eigen,np.array([.75,0,0,0])


def test_independent_equations_match_dense_solution():
    assert verifier.independent_score_checks(*score_fixture())['failures'] == []


@pytest.mark.parametrize('corruption', ['pagerank','eigen','bridging'])
def test_equations_reject_corrupted_scores(corruption):
    transition,kinds,rank,eigen,bridge=score_fixture()
    if corruption=='pagerank':rank[.85][0]+=.02;rank[.85][1]-=.02
    elif corruption=='eigen':eigen[0]+=.02;eigen[1]-=.02
    else:bridge[0]+=.02
    assert verifier.independent_score_checks(transition,kinds,rank,eigen,bridge)['failures']


def test_duplicate_undirected_edge_is_not_laundered_as_extra_weight():
    with pytest.raises(ValueError,match='duplicate'):
        verifier.independent_transition(2,[0,1],[1,0],[1.,1.],[0,0])


@pytest.mark.parametrize('field', ['nodes','components','isolates','largest_component'])
def test_component_counts_assert_the_entire_node_universe(field):
    graph=sparse.csr_matrix([[0,1,0],[1,0,0],[0,0,0]])
    expected={'nodes':3,'components':2,'isolates':1,'largest_component':2}
    assert verifier.component_count_check(graph,expected)['match']
    expected[field]+=1
    assert not verifier.component_count_check(graph,expected)['match']


@pytest.mark.parametrize('path,scope', [
    ('fec/surfaces/staffer_graph_snapshot.py','explicit_receipt_consumer'),
    ('fec\\surfaces\\staffer_graph_snapshot.py','explicit_receipt_consumer'),
    ('fec/surfaces/unreviewed_consumer.py','unexpected_reference'),
    ('fec/surfaces/staffer_graph_snapshot.py.bak','unexpected_reference'),
    ('fec/surfaces/test_staffer_graph_snapshot.py','regression_test'),
    ('audits/staffer_live_runtime/backups/prior.py','retained_audit_or_backup'),
    ('audits/staffer_live_runtime/new_reader.py','unexpected_reference'),
    ('audits/staffer_network/sna_review_20260905/verify_candidate_summary.py','retained_audit_or_backup'),
])
def test_direct_reference_scope_accepts_known_consumers_and_rejects_unknown_paths(path,scope):
    assert verifier.reference_scope(path)==scope
