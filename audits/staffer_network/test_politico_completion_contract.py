import contextlib
import copy
import io
import json
import sys
from pathlib import Path

import pytest

from audits.staffer_network import politico_profile_crawl_api as api
from audits.staffer_network import verify_politico_profile_crawl as verify
from audits.staffer_network.politico_completion_contract import completion_accepted, SOURCE_EXCEPTION_POLICY


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    monkeypatch.setattr(verify, 'EXPECTED_CORPUS_TOTAL', 1)
    expected = {'profile_uuid': 'abc', 'name': 'Test Person', 'roles': [], 'issue_areas': [], 'partition': 'Unknown'}
    evidence = {'status': 200, 'url': api.API_BASE + 'abc', 'data': {
        'lexiconId': 'abc', 'name': {'displayName': 'Test Person'},
        'stafferPositions': [{'title': 'Advisor', 'member': {'name': {'displayName': 'Sen. Example'}}}],
        'employmentItems': [], 'educationItems': [], 'issueAreas': []}}
    row = api.normalize(evidence, expected, allow_source_gaps=True)
    observation = {'profile_uuid': 'abc', 'projected_api_sha256': row['projected_api_sha256'],
        'source_missing_collections': ['employment_history'], 'loading': False,
        'method': 'BROWSER_RENDERED_PROFILE', 'observed_url': row['source_url'],
        'observed_at': '2026-09-05T17:26:35Z', 'outcome': 'RENDERED_SOURCE_MISSING_COLLECTIONS',
        'headings': ['Test Person', 'Biographical']}
    state = {'schema_id': 'politico-profile-crawl-state-v1', 'scope': 'ALL_CURRENT_PROFILES',
        'queue_total': 1, 'total_succeeded': 1, 'total_failed': 0, 'remaining': 0,
        'halted': False, 'max_requests_per_minute': 40}
    for name, value in [('directory.ndjson', expected), ('profiles.ndjson', row),
                        ('api_projected_evidence_20260905.ndjson', evidence),
                        ('exceptions.ndjson', observation), ('state.json', state)]:
        (tmp_path / name).write_text(json.dumps(value) + '\n', encoding='utf-8')
    return tmp_path, observation


def run_verifier(root, monkeypatch, exceptions=True):
    argv = ['verify', '--directory', str(root / 'directory.ndjson'), '--profiles', str(root / 'profiles.ndjson'),
            '--state', str(root / 'state.json'), '--output', str(root / 'receipt.json'), '--require-complete']
    if exceptions:
        argv += ['--source-exceptions', str(root / 'exceptions.ndjson')]
    monkeypatch.setattr(sys, 'argv', argv)
    with contextlib.redirect_stdout(io.StringIO()):
        code = verify.main()
    return code, json.loads((root / 'receipt.json').read_text())


def test_source_empty_release_is_explicit_and_preserves_empty_fields(corpus, monkeypatch):
    root, _ = corpus
    before = (root / 'profiles.ndjson').read_bytes()
    code, receipt = run_verifier(root, monkeypatch)
    assert code == 0, receipt['verification_failures']
    assert receipt['completion_status'] == 'COMPLETE_WITH_EXCEPTIONS'
    assert receipt['counts']['content_bearing_profiles'] == 0
    assert receipt['counts']['accepted_source_exceptions'] == 1
    assert completion_accepted(receipt)
    assert (root / 'profiles.ndjson').read_bytes() == before


def test_api_omission_without_browser_check_cannot_close(corpus, monkeypatch):
    root, _ = corpus
    code, receipt = run_verifier(root, monkeypatch, exceptions=False)
    assert code == 2 and receipt['integrity_status'] == 'PASS'
    assert not completion_accepted(receipt)


@pytest.mark.parametrize('change', [
    {'loading': True}, {'observed_url': 'https://example.org/abc'},
    {'projected_api_sha256': '0' * 64}, {'outcome': 'TIMEOUT'},
    {'headings': ['Test Person', 'Employment History']},
    {'headings': ['Login']}, {'source_missing_collections': []},
])
def test_failed_or_mismatched_browser_evidence_blocks_release(corpus, monkeypatch, change):
    root, observation = corpus
    (root / 'exceptions.ndjson').write_text(json.dumps({**observation, **change}) + '\n')
    code, receipt = run_verifier(root, monkeypatch)
    assert code == 1 and receipt['integrity_status'] == 'FAIL'
    assert not completion_accepted(receipt)


def test_unavailable_rendered_page_is_separate_from_api_history(corpus, monkeypatch):
    root, observation = corpus
    observation.update(outcome='RENDERED_SOURCE_UNAVAILABLE', headings=['404 Error', 'We’re sorry, but the page cannot be found'])
    (root / 'exceptions.ndjson').write_text(json.dumps(observation, ensure_ascii=False) + '\n', encoding='utf-8')
    code, receipt = run_verifier(root, monkeypatch)
    assert code == 0
    assert receipt['counts']['allowed_profile_unavailable_404'] == 0
    assert receipt['source_exception_verification']['rows'][0]['outcome'] == 'RENDERED_SOURCE_UNAVAILABLE'


def test_label_alone_does_not_authorize_downstream_release():
    assert not completion_accepted({'completion_status': 'COMPLETE_WITH_EXCEPTIONS'})
