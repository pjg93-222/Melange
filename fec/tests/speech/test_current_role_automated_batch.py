import json
from pathlib import Path

import pytest

from fec.speech import snapshot_member_longform_ready_sources as snapshot
from fec.speech import prepare_member_longform_automated_batch as prepare
from fec.tests.speech.test_snapshot_member_longform_ready_sources import fixture_inputs


def current_role_case(tmp_path):
    paths, acquired, transcript = fixture_inputs(tmp_path, leader=True)
    acquired.update(source_era='CURRENT_ROLE_CONDITIONED', recorded_at='2024-08-16',
                    current_role_assumed_on='2023-01-03')
    transcript.update({key: acquired[key] for key in ('source_era', 'recorded_at', 'current_role_assumed_on')})
    candidate = {key: acquired[key] for key in ('member', 'source_id', 'url', 'recorded_at', 'source_era')}
    snapshot.SMR.write_jsonl_atomic(paths['leader_sources'], [candidate])
    snapshot.SMR.write_jsonl_atomic(paths['leader_acquisition'], [acquired])
    snapshot.SMR.write_jsonl_atomic(paths['leader_transcripts'], [transcript])
    decision = tmp_path / 'P7.decision.md'
    decision.write_text('L-8/P-7: approved current-role source; no pre-role baseline.\n', encoding='utf-8')
    authorization = {'schema': 'member-longform-current-role-source-authorization-v1',
                     'status': 'APPROVED_CURRENT_ROLE_CONDITIONED_SOURCE',
                     **{key: acquired[key] for key in ('member', 'source_id', 'url', 'wav_sha256', 'recorded_at',
                                                       'source_era', 'current_role_assumed_on')},
                     'decision_id': 'L-8/P-7', 'decision_path': str(decision),
                     'decision_sha256': snapshot.SMR.sha256_file(decision), 'no_pre_role_baseline': True}
    auth_path = tmp_path / 'current_role_authorizations.jsonl'
    snapshot.SMR.write_jsonl_atomic(auth_path, [authorization])
    return paths, acquired, transcript, authorization, auth_path


def test_current_role_default_stays_closed_but_bound_opt_in_can_snapshot(tmp_path):
    paths, _, _, _, auth_path = current_role_case(tmp_path)
    default = snapshot.build_snapshot(tmp_path / 'default', paths, ['Example Member'])
    assert default['counts']['ready'] == 0
    assert default['contract']['leader_pre_current_role_only'] is True
    run = tmp_path / 'approved'
    receipt = snapshot.build_snapshot(run, paths, ['Example Member'], current_role_authorizations=auth_path)
    assert receipt['counts']['ready'] == 1
    assert receipt['contract']['leader_pre_current_role_only'] is False
    row = snapshot.SMR.read_jsonl(run / 'ready_sources.jsonl')[0]
    assert row['source_era'] == 'CURRENT_ROLE_CONDITIONED'
    assert snapshot.verify_snapshot(run)['counts']['ready'] == 1


@pytest.mark.parametrize('mutation', ['audio', 'source', 'date', 'cutoff', 'era', 'decision', 'baseline'])
def test_current_role_opt_in_refuses_changed_bindings(tmp_path, mutation):
    paths, _, _, auth, auth_path = current_role_case(tmp_path)
    if mutation == 'audio':
        auth['wav_sha256'] = '0' * 64
    elif mutation == 'source':
        auth['source_id'] = 'different-source'
    elif mutation == 'date':
        auth['recorded_at'] = '2020-01-01'
    elif mutation == 'cutoff':
        auth['current_role_assumed_on'] = '2005-01-03'
    elif mutation == 'era':
        auth['source_era'] = 'PRE_CURRENT_LEADERSHIP_ROLE'
    elif mutation == 'decision':
        auth['decision_sha256'] = '0' * 64
    else:
        auth['no_pre_role_baseline'] = False
    snapshot.SMR.write_jsonl_atomic(auth_path, [auth])
    try:
        result = snapshot.build_snapshot(tmp_path / 'bad', paths, ['Example Member'],
                                         current_role_authorizations=auth_path)
    except ValueError:
        return
    assert result['counts']['ready'] == 0


def test_current_role_decision_is_frozen_and_tampering_the_copy_refuses(tmp_path):
    paths, _, _, auth, auth_path = current_role_case(tmp_path)
    run = tmp_path / 'approved'
    receipt = snapshot.build_snapshot(run, paths, ['Example Member'], current_role_authorizations=auth_path)
    Path(auth['decision_path']).write_text('Later unrelated edit.\n')
    assert snapshot.verify_snapshot(run)['counts']['ready'] == 1
    frozen = snapshot.frozen_current_role_authorizations(run, receipt)['Example Member']
    Path(frozen['decision_path']).write_text('Changed frozen approval.\n')
    with pytest.raises(ValueError, match='decision'):
        snapshot.verify_snapshot(run)


@pytest.mark.parametrize('kind,reason', [
    ('rejected', 'SUPERSEDED_OR_REJECTED_SOURCE'),
    ('hold', 'QUALITY_HOLD_REQUIRES_SEPARATE_REPAIR_REVIEW'),
])
def test_current_role_opt_in_does_not_clear_rejections_or_recording_holds(tmp_path, kind, reason):
    paths, acquired, transcript, _, auth_path = current_role_case(tmp_path)
    key = 'rejected_sources' if kind == 'rejected' else 'quality_holds'
    row = ({'member': acquired['member'], 'source_id': acquired['source_id']} if kind == 'rejected'
           else {key: transcript[key] for key in snapshot.BINDING_KEYS})
    snapshot.SMR.write_jsonl_atomic(paths[key], [row])
    run = tmp_path / 'held'
    receipt = snapshot.build_snapshot(run, paths, ['Example Member'], current_role_authorizations=auth_path)
    assert receipt['counts']['ready'] == 0
    assert snapshot.SMR.read_jsonl(run / 'source_diagnostics.jsonl')[0]['reason'] == reason


def test_prepare_derives_current_role_scope_only_from_verified_snapshot(tmp_path, monkeypatch):
    paths, acquired, transcript, _, auth_path = current_role_case(tmp_path)
    run = tmp_path / 'approved'
    snapshot.build_snapshot(run, paths, ['Example Member'], current_role_authorizations=auth_path)
    monkeypatch.setattr(prepare.selector, 'DEFAULT_PRIMARY_TRANSCRIPTS', paths['primary_transcripts'])
    out = tmp_path / 'batch'
    monkeypatch.setattr('sys.argv', ['prepare', '--snapshot', str(run), '--out-root', str(out)])
    assert prepare.main() == 0
    queue = snapshot.SMR.read_jsonl(out / 'member_queue.jsonl')[0]
    assert queue['status'] == 'REUSE_ASR_FOR_AUTOMATED_PROCESSING'
    assert queue['source_era'] == 'CURRENT_ROLE_CONDITIONED'
    assert snapshot.SMR.read_jsonl(out / 'acquisitions.jsonl') == [acquired]
    assert snapshot.SMR.read_jsonl(out / 'transcripts.jsonl') == [transcript]
    receipt = json.loads((out / 'prepare.receipt.json').read_text())
    assert receipt['contract']['current_role_conditioned_members'] == ['Example Member']
    assert receipt['contract']['current_role_sources_are_baseline'] is False
