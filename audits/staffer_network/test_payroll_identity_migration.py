"""Regression controls for source-row migration and uncertain date semantics."""
import copy
import pytest
from audits.staffer_network.verify_payroll_identity_migration import (
    row_owners, expected_episodes, expected_pairs, episode_counter, strings,
    checked_sources, pair_components,
)
from audits.staffer_network.rebuild_payroll_identity import run


def ep(person='old', rows=None, start='2020-01-01', end='2020-04-01', basis='printed_service_dates'):
    return [person, 'office', 'title', start, end, basis, rows or ['row1']]


def test_duplicate_source_owners_rejected():
    with pytest.raises(ValueError, match='Repeated source row'):
        row_owners([{'spine_person_id': 'a', 'source_row_ids': ['r']},
                    {'spine_person_id': 'b', 'source_row_ids': ['r']}])


def test_rekey_uses_source_rows_not_old_person_id():
    actual = expected_episodes([ep()], {'row1': 'new'})
    assert actual == [ep(person='new')]


def test_unsafely_split_episode_fails_closed():
    with pytest.raises(ValueError, match='raw date reconstruction'):
        expected_episodes([ep(rows=['a', 'b'])], {'a': 'new1', 'b': 'new2'})


def test_day_intervals_union_after_identity_rekey():
    actual = expected_episodes([ep(rows=['a']), ep(rows=['b'], start='2020-03-01', end='2020-05-01')],
                               {'a': 'new', 'b': 'new'})
    assert actual == [ep(person='new', rows=['a', 'b'], end='2020-05-01')]


def test_uncertain_windows_never_union_when_merely_overlapping():
    source = [ep(rows=['a'], basis='presence_within_report'),
              ep(rows=['b'], start='2020-03-01', end='2020-05-01', basis='presence_within_report')]
    assert len(expected_episodes(source, {'a': 'new', 'b': 'new'})) == 2


def test_episode_comparison_detects_dropped_source_rows_and_date_drift():
    original = [ep(rows=['a', 'b'])]
    assert episode_counter(original) != episode_counter([ep(rows=['a'])])
    assert episode_counter(original) != episode_counter([ep(rows=['a', 'b'], end='2020-05-01')])


def test_collapsed_identity_cannot_create_self_pair():
    original = [{'node_ids': ['old1', 'old2'], 'records': [
        {'row_id': 'a', 'person_id': 'old1'}, {'row_id': 'b', 'person_id': 'old2'}]}]
    saved = copy.deepcopy(original)
    assert expected_pairs(original, {'a': 'new', 'b': 'new'}) == ([], 1)
    assert original == saved


def test_rekeyed_pairs_retain_row_provenance():
    original = [{'node_ids': ['old1', 'old2'], 'records': [
        {'row_id': 'a', 'person_id': 'old1'}, {'row_id': 'b', 'person_id': 'old2'}]}]
    actual, collapsed = expected_pairs(original, {'a': 'new2', 'b': 'new1'})
    assert collapsed == 0
    assert actual[0]['node_ids'] == ['new1', 'new2']
    assert actual[0]['records'][0] == {'row_id': 'b', 'person_id': 'new1'}


def test_nested_assertion_id_scan():
    assert list(strings({'group': [{'ids': ['hill:person:a']}]})) == ['hill:person:a']


def test_builder_refuses_existing_generation(tmp_path):
    with pytest.raises(ValueError, match='already exists'):
        run(tmp_path / 'spine', tmp_path)


def test_source_hash_mismatch_is_rejected(tmp_path):
    source = tmp_path / 'source'
    source.write_bytes(b'changed')
    with pytest.raises(ValueError, match='Source hash mismatch'):
        checked_sources({'sources': [{'path': str(source), 'sha256': '0' * 64}]})


def test_indirect_pair_merge_is_visible():
    components = pair_components([{'node_ids': ['a', 'bridge']}, {'node_ids': ['b', 'bridge']}])
    assert components['a'] == components['b']
