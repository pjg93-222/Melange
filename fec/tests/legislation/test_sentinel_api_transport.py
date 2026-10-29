"""MELANGE_SENTINEL_TRANSPORT=api (ATTEMPT10-400, 2026-10-27): the alias the policy names is sent as a full model id, a
verdict classified over claude-cli is reused over the api (and back), and a rejected request stops the run with its body
logged instead of spending the whole call budget on identical 400s. No network: _http_bytes is stubbed."""
from __future__ import annotations

import io
import json
from pathlib import Path
import sys
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from legislation import refresh_sentinel_admissions as R
import test_sentinel_classifier_budget as B
import test_sentinel_decision_stability as S


def api_hold(key):
    text = json.dumps({'canonical_key': key, 'disposition': 'hold', 'confidence': 'low', 'rationale': 'fixture hold',
                       'categories': []})
    return json.dumps({'id': 'msg_fixture', 'model': 'claude-sonnet-5-5', 'stop_reason': 'end_turn', 'usage': {},
                       'content': [{'type': 'thinking', 'thinking': ''}, {'type': 'text', 'text': text}]}).encode()


def fake_api(monkeypatch, outcome):
    """_http_bytes stand-in: records each request body; `outcome(key)` returns bytes or raises."""
    bodies = []

    def http_bytes(request, *, timeout, source, **kwargs):
        body = json.loads(request.data)
        bodies.append(body)
        return outcome(json.loads(body['messages'][0]['content'])['canonical_key'])

    monkeypatch.setenv('ANTHROPIC_API_KEY', 'fixture-key')
    monkeypatch.setattr(R, '_http_bytes', http_bytes)
    return bodies


def http_error(code, message):
    body = json.dumps({'type': 'error', 'error': {'type': 'invalid_request_error', 'message': message}}).encode()

    def raise_it(key):
        raise urllib.error.HTTPError('https://api.anthropic.com/v1/messages', code, 'Bad Request', {}, io.BytesIO(body))
    return raise_it


# ---- model resolution ---------------------------------------------------------------------------------------------

def test_api_transport_sends_the_full_id_for_the_policy_alias(monkeypatch):
    bodies = fake_api(monkeypatch, api_hold)
    decision, meta = R.classify(B.KEYS[0], B.TEXTS, ['Payments'], model='sonnet', key_path=Path('unused'), transport='api')
    assert decision['disposition'] == 'hold' and meta['model'] == 'claude-sonnet-5-5'
    assert bodies[0]['model'] == 'claude-sonnet-5-5'
    assert bodies[0]['max_tokens'] == 16000            # thinking counts against it; 5 of 26 CLI includes ran past 5000
    R.classify(B.KEYS[0], B.TEXTS, ['Payments'], model='claude-opus-5-5', key_path=Path('unused'), transport='api')
    assert bodies[1]['model'] == 'claude-opus-5-5'     # a full id passes through unchanged


def test_the_alias_stays_the_fingerprint_identity(tmp_path, monkeypatch):
    B.build(tmp_path, monkeypatch, keys=B.KEYS[:1])
    R.write_json(tmp_path / 'data/engine/sentinel_admission_policy.json', {'transport': 'claude-cli', 'model': 'sonnet'})
    fake_api(monkeypatch, api_hold)
    _, _, checkpoint, _ = B.run_main(tmp_path, '--transport', 'api')
    assert checkpoint['decisions'][B.KEYS[0]]['fingerprint_parameters']['model'] == 'sonnet'


# ---- reuse across transports --------------------------------------------------------------------------------------

def test_a_claude_cli_verdict_is_reused_over_the_api_and_back(tmp_path):
    texts, sources = S.evidence(tmp_path)
    published = S.decision(texts, sources)                         # classified over claude-cli, model 'sonnet'
    for transport in ('api', 'claude-cli'):
        reused = R.reusable_decision(S.KEY, texts, {'Payments'}, published=published, checkpoint=None,
                                     model=S.MODEL, transport=transport)
        assert reused is not None and reused[1]['cache_source'] == 'published'
    api_sealed = {**published, 'fingerprint_parameters': {'policy': R.POLICY, 'model': S.MODEL, 'transport': 'api'},
                  'evidence_fingerprint': R.evidence_fingerprint(texts, model=S.MODEL, transport='api')}
    assert R.reusable_decision(S.KEY, texts, {'Payments'}, published=api_sealed, checkpoint=None,
                               model=S.MODEL, transport='claude-cli') is not None
    # model and policy still bind
    assert R.reusable_decision(S.KEY, texts, {'Payments'}, published=published, checkpoint=None,
                               model='claude-opus-5-5', transport='api') is None


def test_statute_switch_does_not_decline_on_transport_alone(tmp_path):
    texts, sources = S.evidence(tmp_path)
    published = S.decision(texts, sources, 'include')
    published['evidence_fingerprint'] = R.evidence_fingerprint(texts, model=S.MODEL, transport='claude-cli')
    declined = []
    # identical evidence: the switch rule steps aside (None) for the ordinary cache hit, giving no decline reason
    assert R.statute_source_switch_reuse(S.KEY, published, texts, sources, {'Payments'}, model=S.MODEL,
                                         transport='api', declined=declined) is None
    assert declined == []
    R.statute_source_switch_reuse(S.KEY, published, texts, sources, {'Payments'}, model='other',
                                  transport='api', declined=declined)
    assert declined == ['the published verdict was classified under another policy or model']


# ---- a rejected request fails fast, with its body logged ----------------------------------------------------------

def test_a_400_stops_the_run_after_one_call_and_logs_the_body(tmp_path, monkeypatch, capsys):
    B.build(tmp_path, monkeypatch)
    bodies = fake_api(monkeypatch, http_error(400, 'model: sonnet is not a valid model id'))
    code, generation, checkpoint, installed = B.run_main(tmp_path, '--transport', 'api', '--limit', '4',
                                                         '--max-classifier-calls', '48')
    out = capsys.readouterr().out
    assert len(bodies) == 1
    assert (code, generation['status'], installed) == (1, 'FAIL', False)
    assert (generation['aborted_reason'], generation['not_attempted']) == ('CLASSIFIER_REQUEST_REJECTED', 3)
    error = next(iter(checkpoint['errors'].values()))
    assert error.startswith('CLASSIFIER_REQUEST_REJECTED:') and 'not a valid model id' in error
    assert 'classifier API HTTP 400: ' in out and 'not a valid model id' in out
    assert 'Run stopped on classifier quota' not in out   # refresh_failure must not read it as a provider quota stop


def test_no_credit_is_a_quota_stop(tmp_path, monkeypatch):
    B.build(tmp_path, monkeypatch)
    bodies = fake_api(monkeypatch, http_error(400, 'Your credit balance is too low to access the Anthropic API.'))
    _, generation, _, _ = B.run_main(tmp_path, '--transport', 'api', '--limit', '4', '--max-classifier-calls', '48')
    assert len(bodies) == 1 and generation['aborted_reason'] == 'CLASSIFIER_QUOTA_EXHAUSTED'


def test_a_per_key_size_400_does_not_stop_the_run(tmp_path, monkeypatch, capsys):
    B.build(tmp_path, monkeypatch)
    bodies = fake_api(monkeypatch, http_error(400, 'prompt is too long: 1200000 tokens > 1000000 maximum'))
    _, generation, _, _ = B.run_main(tmp_path, '--transport', 'api', '--limit', '4', '--max-classifier-calls', '48')
    assert len(bodies) == 4 and generation['aborted_reason'] is None
    assert 'prompt is too long' in capsys.readouterr().out
