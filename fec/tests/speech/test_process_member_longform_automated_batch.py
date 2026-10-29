import json
import subprocess
import sys

import pytest

from fec.speech import process_member_longform_automated_batch as batch


def test_invoke_passes_step_timeout(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(batch.subprocess, 'run', lambda *a, **k: seen.update(k))
    monkeypatch.setattr(batch, 'STEP_TIMEOUT', 7)
    batch.invoke('m', [], tmp_path / 'log')
    assert seen['timeout'] == 7


def test_hung_child_holds_member_and_batch_continues(tmp_path, monkeypatch):
    members = [{'member': 'A', 'status': 'SOURCE_X', 'source_id': 's'},
               {'member': 'B', 'status': 'SOURCE_HOLD', 'reason': 'r'}]
    monkeypatch.setattr(batch, 'check_prepare', lambda root: {'roles': tmp_path / 'roles.json'})
    (tmp_path / 'roles.json').write_text(json.dumps({'members': {}}))
    monkeypatch.setattr(batch.snapshot, 'rows_by_member', lambda rows, label: {'A': {}})
    monkeypatch.setattr(batch.SMR, 'read_jsonl', lambda path, required=False: members)
    monkeypatch.setattr(batch, 'choose_transcript', lambda *a: ({'transcript_sha256': 'x' * 16}, []))
    monkeypatch.setattr(batch, 'freeze_source', lambda *a: {})

    def hang(*a, **k):
        raise subprocess.TimeoutExpired('cmd', 1)
    monkeypatch.setattr(batch, 'source_pipeline', hang)
    monkeypatch.setattr(batch.SMR, 'write_jsonl_atomic', lambda *a: None)
    monkeypatch.setattr(batch.SMR, 'write_json_atomic', lambda *a: None)
    monkeypatch.setattr(batch.SMR, 'sha256_file', lambda p: 'h')
    monkeypatch.setattr(sys, 'argv', ['x', '--batch-root', str(tmp_path), '--converted-model', 'm',
                                      '--step-timeout', '1'])
    assert batch.main() == 0


def test_effective_acquisitions_applies_only_audio_rebindings(tmp_path):
    frozen = [{'member': 'A', 'source_id': 's', 'wav': 'w', 'wav_sha256': 'old', 'frame_count': 10},
              {'member': 'B', 'source_id': 't', 'wav': 'v', 'wav_sha256': 'b'}]
    assert batch.effective_acquisitions(tmp_path, frozen) == frozen  # no overlay file: unchanged
    rebound = {**frozen[0], 'wav_sha256': 'new', 'old_sha256': 'old', 'new_sha256': 'new', 'sha_match': False,
               'rebind_reason': 'r', 'frame_count': 11, 'old_frame_count': 10}
    path = tmp_path / 'acquisitions.rebound.jsonl'

    def write(rows):
        path.write_text('\n'.join(json.dumps(row) for row in rows) + '\n')
    write([rebound, frozen[1]])
    assert batch.effective_acquisitions(tmp_path, frozen) == [rebound, frozen[1]]
    for bad in ({**rebound, 'source_id': 'other'}, {**rebound, 'old_sha256': 'x'}, {**rebound, 'rebind_reason': ''}):
        write([bad, frozen[1]])
        with pytest.raises(ValueError):
            batch.effective_acquisitions(tmp_path, frozen)
    write([rebound])
    with pytest.raises(ValueError):
        batch.effective_acquisitions(tmp_path, frozen)


def test_cli_backend_asks_for_the_same_prompt_in_both_passes(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(batch, 'invoke', lambda module, arguments, log: calls.append((module, list(arguments))))
    monkeypatch.setattr(batch.SMR, 'read_jsonl', lambda *a, **k: [{'turns': []}])
    batch.source_pipeline({'member': 'M', 'source_id': 's'}, tmp_path, None, 2, 'cli', 'low')
    module, arguments = calls[0]
    assert module.endswith('classify_member_longform_two_passes_local')
    assert '--same-prompt-both-passes' in arguments and arguments[arguments.index('--backend') + 1] == 'cli'
    local = []
    monkeypatch.setattr(batch, 'invoke', lambda module, arguments, log: local.append(list(arguments)))
    batch.source_pipeline({'member': 'M', 'source_id': 's'}, tmp_path, 'model', 2, 'local')
    assert '--same-prompt-both-passes' not in local[0]


def test_batch_root_calibration_override_is_hash_bound_and_reaches_continuity(tmp_path, monkeypatch):
    assert batch.continuity_calibration(tmp_path) == ()
    cal = tmp_path / 'cal.json'
    cal.write_text('{"false_accepts": 0}', encoding='utf-8')
    config = tmp_path / 'continuity_calibration.json'
    config.write_text(json.dumps({'calibration': str(cal), 'sha256': batch.SMR.sha256_file(cal)}), encoding='utf-8')
    override = batch.continuity_calibration(tmp_path)
    assert override == ('--calibration', cal)
    calls = []
    monkeypatch.setattr(batch, 'invoke', lambda module, arguments, log: calls.append((module, list(arguments))))
    monkeypatch.setattr(batch.SMR, 'read_jsonl', lambda *a, **k: [{'turns': [{}]}] if 'candidates' in str(a[0]) else [])
    (tmp_path / 'candidates.receipt.json').write_text('{}')
    batch.source_pipeline({'member': 'M', 'source_id': 's'}, tmp_path, None, 2, 'cli', 'low', override)
    continuity = [args for module, args in calls if module.endswith('speaker_continuity')][0]
    assert continuity[continuity.index('--calibration') + 1] == cal
    cal.write_text('{"false_accepts": 1}', encoding='utf-8')
    with pytest.raises(ValueError, match='hash mismatch'):
        batch.continuity_calibration(tmp_path)


def era_source(tmp_path, monkeypatch, *, era=None, published='2021-01-01', transcript_era=None):
    words = tmp_path / 'original.words.jsonl'
    words.write_text('{}\n', encoding='utf-8')
    source = {'member': 'Example Member', 'source_id': 'source', 'wav': 'source.wav',
              'wav_sha256': 'audio-sha', 'published': published}
    if era is not None:
        source['source_era'] = era
    transcript = {**source, 'transcript': str(words), 'transcript_sha256': batch.SMR.sha256_file(words)}
    if transcript_era is not None:
        transcript['source_era'] = transcript_era
    monkeypatch.setattr(batch.physical, 'validate_source', lambda row: ([], None))
    monkeypatch.setattr(batch.screen, 'find_name_cues', lambda words, member: [{'phrase': member}])
    return source, transcript


def test_freezing_preserves_pre_congress_source_scope(tmp_path, monkeypatch):
    source, transcript = era_source(tmp_path, monkeypatch, era='PRE_CONGRESS_LOCAL_OFFICE')
    selected = batch.freeze_source(source, transcript, None, tmp_path / 'job')
    assert selected['source_era'] == 'PRE_CONGRESS_LOCAL_OFFICE'


def test_freezing_admits_explicit_current_role_source_without_calling_it_pre_role(tmp_path, monkeypatch):
    source, transcript = era_source(tmp_path, monkeypatch, era='CURRENT_ROLE_CONDITIONED', published='2024-08-16')
    role = {'current_role': 'Whip', 'current_role_assumed_on': '2021-01-20'}
    selected = batch.freeze_source(source, transcript, role, tmp_path / 'job')
    assert selected['source_era'] == 'CURRENT_ROLE_CONDITIONED'
    assert selected['current_role'] == 'Whip'
    assert selected['current_role_assumed_on'] == '2021-01-20'


@pytest.mark.parametrize('era,published,transcript_era', [
    (None, '2024-08-16', None),
    ('CURRENT_ROLE_CONDITIONED', '2020-01-01', None),
    ('CURRENT_ROLE_CONDITIONED', None, None),
    ('PRE_CURRENT_LEADERSHIP_ROLE', '2024-08-16', None),
    ('CURRENT_ROLE_CONDITIONED', '2024-08-16', 'PRE_CURRENT_LEADERSHIP_ROLE'),
])
def test_freezing_refuses_unapproved_or_conflicting_role_eras(tmp_path, monkeypatch, era, published, transcript_era):
    source, transcript = era_source(tmp_path, monkeypatch, era=era, published=published, transcript_era=transcript_era)
    role = {'current_role': 'Whip', 'current_role_assumed_on': '2021-01-20'}
    with pytest.raises(ValueError):
        batch.freeze_source(source, transcript, role, tmp_path / 'job')
    assert not (tmp_path / 'job' / 'selection.jsonl').exists()


def filtered_run(tmp_path, monkeypatch, verified, *members):
    """Run main() on a two-member queue (A, B) with the pipeline stubbed: a member in ``verified`` gets 2 turns, others hold."""
    queue = [{'member': 'A', 'status': 'SOURCE_X', 'source_id': 'a'}, {'member': 'B', 'status': 'SOURCE_X', 'source_id': 'b'}]
    batch.SMR.write_jsonl_atomic(tmp_path / 'member_queue.jsonl', queue)
    for name in ('acquisitions.jsonl', 'transcripts.jsonl', 'primary.jsonl'):
        batch.SMR.write_jsonl_atomic(tmp_path / name, [])
    (tmp_path / 'roles.json').write_text(json.dumps({'members': {}}))
    monkeypatch.setattr(batch, 'check_prepare', lambda root: {'roles': tmp_path / 'roles.json'})
    monkeypatch.setattr(batch.selector, 'DEFAULT_PRIMARY_TRANSCRIPTS', tmp_path / 'primary.jsonl')
    monkeypatch.setattr(batch.snapshot, 'rows_by_member', lambda rows, label: {'A': {}, 'B': {}})
    monkeypatch.setattr(batch, 'choose_transcript', lambda *a: ({'transcript_sha256': 'x' * 16}, []))
    monkeypatch.setattr(batch, 'freeze_source', lambda source, transcript, role, job: {})
    monkeypatch.setattr(batch, 'source_pipeline', lambda selected, job, *a: (
        {'status': 'VERIFIED', 'verified_turns': 2} if job.name.startswith(tuple(m.lower() for m in verified))
        else {'status': 'HELD_NO_AGREED_COMPLETE_RESPONSES', 'verified_turns': 0}))
    argv = ['x', '--batch-root', str(tmp_path), '--converted-model', 'm']
    for member in members:
        argv += ['--member', member]
    monkeypatch.setattr(sys, 'argv', argv)
    assert batch.main() == 0
    rows = batch.SMR.read_jsonl(tmp_path / 'processing-results.jsonl')
    return rows, json.loads((tmp_path / 'processing-results.receipt.json').read_text(encoding='utf-8'))


def test_a_member_run_merges_into_earlier_results_and_claims_coverage_only_for_the_full_queue(tmp_path, monkeypatch):
    rows, receipt = filtered_run(tmp_path, monkeypatch, {'A'})
    assert [r['member'] for r in rows] == ['A', 'B'] and receipt['member_filter'] is None
    assert receipt['status'] == 'FINISHED_WITH_EXPLICIT_HOLDS' and receipt['all_members_verified'] is False
    first_a = rows[0]
    rows, receipt = filtered_run(tmp_path, monkeypatch, {'A', 'B'}, 'B')
    assert [r['member'] for r in rows] == ['A', 'B'] and rows[0] == first_a           # A's earlier row survives the B-only run
    assert rows[1]['verified_turns'] == 2
    assert receipt['member_filter'] == ['B'] and receipt['active_members'] == 1
    assert receipt['queue_members'] == 2 and receipt['covered_members'] == 2 and receipt['verified_members'] == 2
    assert receipt['status'] == 'FINISHED_WITH_EXPLICIT_COVERAGE' and receipt['all_members_verified'] is True


def test_a_member_run_alone_never_claims_the_full_queue(tmp_path, monkeypatch):
    rows, receipt = filtered_run(tmp_path, monkeypatch, {'A'}, 'A')
    assert [r['member'] for r in rows] == ['A'] and rows[0]['verified_turns'] == 2
    assert receipt['status'] == 'FINISHED_PARTIAL_COVERAGE' and receipt['all_members_verified'] is False
    assert receipt['member_filter'] == ['A'] and receipt['covered_members'] == 1 and receipt['queue_members'] == 2


def test_an_unknown_member_filter_refuses_before_anything_is_written(tmp_path, monkeypatch):
    with pytest.raises(SystemExit):
        filtered_run(tmp_path, monkeypatch, set(), 'Nobody')
    assert not (tmp_path / 'processing-results.jsonl').exists()
