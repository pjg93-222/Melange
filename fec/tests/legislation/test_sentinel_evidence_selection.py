"""M5a section-aware evidence selection (D-366 design, approved as D-369).

Pins: each selection step (S1 statute notes, S2 statute selection, S3 bill sections); that nothing is ever cut inside a
document or a section and no step fills to a budget; that every omission is recorded in the evidence manifest, the
verdict and the run receipt; that a bill still over the envelope is FAILED (never held) and makes the run DEGRADED;
that a bill which fits is byte-identical to before (no config read, same 3-tuple, same fingerprint); and that a sealed
selection replays exactly. No test touches the network or claude.exe.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from legislation import refresh_sentinel_admissions as R  # noqa: E402
from legislation import sentinel_evidence_selection as SEL  # noqa: E402
from legislation import sentinel_admissions as SA  # noqa: E402
import refresh_failure  # noqa: E402
import refresh_state  # noqa: E402
import test_sentinel_classifier_budget as B  # noqa: E402

KEY = '119:hr:7'
BILL_URL = 'https://www.govinfo.gov/content/pkg/BILLS-119hr7ih/xml/BILLS-119hr7ih.xml'
STATUS_URL = 'https://www.govinfo.gov/bulkdata/BILLSTATUS/119/hr/BILLSTATUS-119hr7.xml'
STAMP = '2026-10-27T00:00:00+00:00'
FILLER = ' '.join(['The Secretary of Agriculture shall report on rural broadband deployment grants.'] * 40)


def section(enum, header, body, quoted=''):
    return (f'<section><enum>{enum}.</enum><header>{header}</header><text>{body}</text>{quoted}</section>')


def bill_xml(*sections):
    return ('<?xml version="1.0"?><bill><metadata><dublinCore><dc:title xmlns:dc="http://purl.org/dc/elements/1.1/">'
            '119 HR 7 IH: Fixture Act</dc:title></dublinCore></metadata><form><official-title>To do things.</official-title>'
            '</form><legis-body>' + ''.join(sections) + '</legis-body></bill>').encode('utf-8')


def statute_page(title, sec, operative, notes='Amendments 2010 Pub. L. 111-203 struck out things. ' * 30,
                 footnote='1 So in original.'):
    return (f'<html><head><title>U.S.C. Title {title} - FIXTURE</title></head><body>'
            f'<h3 class="section-head">&sect;{sec}. Fixture</h3>'
            f'<!-- field-start:statute --><p class="statutory-body">{operative}</p><!-- field-end:statute -->'
            f'<!-- field-start:sourcecredit --><p class="source-credit">(Pub. L. 1)</p><!-- field-end:sourcecredit -->'
            f'<h4 class="note-head"><strong>Editorial Notes</strong></h4><p class="note-body">{notes}</p>'
            f'<h4 class="note-head"><strong>Statutory Notes and Related Subsidiaries</strong></h4><p class="note-body">{notes}</p>'
            f'<!-- field-start:footnote --><p class="footnote">{footnote}</p><!-- field-end:footnote -->'
            f'</body></html>').encode('utf-8')


def statute_url(title, sec):
    return (f'https://www.govinfo.gov/content/pkg/USCODE-2024-title{title}/html/'
            f'USCODE-2024-title{title}-chapX-sec{sec}.htm')


@pytest.fixture
def config():
    return SEL.load_config()[0]


def harness(monkeypatch, bill, statutes):
    """collect() offline: the bill is served from memory, House Code is skipped (run-level outage already seen) and
    govinfo_statute serves crafted GovInfo pages. Returns the list of statute sections fetched."""
    fetched = []

    def fetcher(timeout):
        def fetch(url, cap):
            return bill if url == BILL_URL else b'<billstatus/>'
        return fetch

    def govinfo(title, sec):
        fetched.append(f'{title} USC {sec}')
        raw = statutes.get((title, sec)) or statute_page(title, sec, f'Operative text of {title} USC {sec}.')
        url = statute_url(title, sec)
        return url, raw, R.govinfo_statute_text(raw, title, sec), {'statute_source': 'govinfo_uscode', 'edition': 'USCODE-2024'}

    monkeypatch.setattr(R.GF, 'network_fetcher', fetcher)
    monkeypatch.setattr(R.BS, 'parse_billstatus_xml', lambda *a, **k: {'canonical_key': KEY})
    monkeypatch.setattr(R.GF, '_bill_text_urls', lambda parsed: ([BILL_URL], None))
    monkeypatch.setattr(R.GF, '_select_title', lambda parsed: 'Fixture')
    monkeypatch.setattr(R, '_govinfo_snapshot', lambda *a, **k: {'key': KEY})
    monkeypatch.setattr(R, 'govinfo_statute', govinfo)
    R._STATUTE_RUN.update(house_down='fixture: House Code down', integrity_failures=0,
                          counts={'house_code': 0, 'govinfo_uscode': 0})
    return fetched


def cites(*pairs):
    return ' '.join(f'section {s} of title {t}, {t} U.S.C. {s},' for t, s in pairs)


# ---- vocabulary and map ----------------------------------------------------------------------------------------

def test_identifiers_match_only_inside_their_window(config):
    near = 'This Act concerns check fraud at banks.'
    far = 'check ' + 'word ' * 30 + 'fraud'
    assert any(hit.startswith('fraud_prevention') for hit in SEL.matches(near, config, 'narrow'))
    assert not any('check fraud' in hit for hit in SEL.matches(far, config, 'narrow'))


def test_narrow_and_wide_vocabularies_differ(config):
    text = 'A financial institution shall verify each account.'
    assert SEL.matches(text, config, 'narrow') == []
    assert 'financial institution' in SEL.matches(text, config, 'wide')
    assert 'credit union' in SEL.matches('Each insured credit union shall', config, 'narrow')


@pytest.mark.parametrize('title,sec,label', [
    ('12', '1757a', 'Federal Credit Union Act'), ('12', '1795k', 'Federal Credit Union Act'),
    ('15', '1693o-2', 'Electronic Fund Transfer Act'), ('12', '5512', 'Consumer Financial Protection Act'),
    ('12', '1796', None), ('42', '1395x', None)])
def test_the_cu_statute_map(config, title, sec, label):
    got = SEL.map_label(config, title, sec)
    assert (got is None) if label is None else got.startswith(label)


# ---- bill sections (S3) ----------------------------------------------------------------------------------------

def test_sections_are_top_level_and_a_quoted_block_stays_with_its_section():
    amended = '<quoted-block><section><enum>99.</enum><header>Inserted</header><text>Inserted text.</text></section></quoted-block>'
    raw = bill_xml(section('1', 'Short title', 'This Act may be cited as the Fixture Act.'),
                   section('2', 'Amendment', 'Section 5 is amended by adding:', amended))
    _, sections = SEL.bill_sections(raw)
    assert [label for label, _, _ in sections] == ['Sec. 1 Short title', 'Sec. 2 Amendment']
    assert 'Inserted text.' in sections[1][2]


def test_no_omission_rebuild_equals_the_production_bill_text(config):
    raw = bill_xml(section('1', 'Short title', 'Fixture Act.'), section('2', 'Rural', FILLER))
    full = R.GF._parse_bill_text(raw, url=BILL_URL, canonical_key=KEY)
    root, _ = SEL.bill_sections(raw)
    assert SEL._join(SEL._text_parts(root, {})) == full


def test_s3_replaces_whole_sections_with_markers_and_never_cuts_inside_one(config):
    keep_cu = 'An insured credit union may offer the product to members.'
    raw = bill_xml(section('1', 'Short title', 'Fixture Act.'), section('2', 'Rural', FILLER),
                   section('3', 'Credit unions', keep_cu), section('4', 'Definitions', 'The term X means Y.'),
                   section('5', 'More rural', FILLER + ' tail'))
    full = R.GF._parse_bill_text(raw, url=BILL_URL, canonical_key=KEY)
    texts, record = SEL.select_sections(config, {BILL_URL: full}, {BILL_URL: raw})
    selected = texts[BILL_URL]
    _, sections = SEL.bill_sections(raw)
    assert [row['section'] for row in record['omitted']] == ['Sec. 2 Rural', 'Sec. 5 More rural']
    assert record['kept'] == 3
    for label, _, text in sections:                  # every section is either present whole or named by a marker
        if label in ('Sec. 2 Rural', 'Sec. 5 More rural'):
            assert text not in selected and f'{SEL.MARKER_PREFIX} v1: {label}, {len(text)} chars' in selected
        else:
            assert text in selected
    assert selected.count(SEL.MARKER_PREFIX) == 2 and selected.startswith(full[:40])


def test_s3_leaves_a_version_it_cannot_rebuild_whole(config):
    texts, record = SEL.select_sections(config, {BILL_URL: 'not the parse'}, {BILL_URL: bill_xml(section('1', 'A', 'B'))})
    assert texts[BILL_URL] == 'not the parse' and record['not_separable'] == [BILL_URL]


# ---- statute notes (S1) ----------------------------------------------------------------------------------------

def _source(title, sec):
    return {'url': statute_url(title, sec), 'title': title, 'section': sec, 'kind': 'statute'}


def test_s1_keeps_operative_text_source_credit_and_footnotes_and_drops_notes():
    raw = statute_page('12', '1757', 'A Federal credit union shall have power to lend.')
    source = _source('12', '1757')
    full = R.statute_document_text(raw, source)
    texts, record = SEL.strip_notes({source['url']: full}, [(source['url'], raw, source)], ['bill text'], R.statute_document_text)
    kept = texts[source['url']]
    assert 'shall have power to lend' in kept and '(Pub. L. 1)' in kept and 'So in original' in kept
    assert 'Editorial Notes' not in kept and 'struck out things' not in kept
    assert record['omitted'][0]['id'] == '12 USC 1757' and record['omitted'][0]['chars_omitted'] == len(full) - len(kept)
    assert full.startswith(kept.split(' 1 So in original')[0])     # a prefix of the document: a structural cut only


def test_s1_keeps_notes_of_a_section_the_bill_cites_as_a_note():
    raw = statute_page('12', '1757', 'Operative.')
    source = _source('12', '1757')
    full = R.statute_document_text(raw, source)
    texts, record = SEL.strip_notes({source['url']: full}, [(source['url'], raw, source)],
                                    ['amending section 3 (12 U.S.C. 1757 note)'], R.statute_document_text)
    assert texts[source['url']] == full and record['kept_for_note_citation'] == ['12 USC 1757']


def test_s1_keeps_a_page_without_note_headings_whole():
    raw = b'<html><head><title>U.S.C. Title 12 - X</title></head><body><h3 class="section-head">&sect;1757. X</h3><p>Only law.</p></body></html>'
    source = _source('12', '1757')
    full = R.statute_document_text(raw, source)
    texts, record = SEL.strip_notes({source['url']: full}, [(source['url'], raw, source)], [''], R.statute_document_text)
    assert texts[source['url']] == full and record['not_separable'] == ['12 USC 1757']


# ---- statute selection (S2) ------------------------------------------------------------------------------------

def test_s2_keeps_mapped_and_narrow_cited_statutes_only(config):
    raw = bill_xml(section('1', 'Short title', 'Fixture Act.'),
                   section('2', 'Credit unions', 'An insured credit union, as defined in 7 U.S.C. 1a, may act.'),
                   section('3', 'Accounts', 'A financial institution account under 42 U.S.C. 1395x is covered.'),
                   section('4', 'Powers', 'Section 107 of the Act (12 U.S.C. 1757) is amended.'))
    text = R.GF._parse_bill_text(raw, url=BILL_URL, canonical_key=KEY)
    cited = R.statute_references({BILL_URL: text})
    kept, omitted = SEL.relevant_statutes(config, {BILL_URL: raw}, {BILL_URL: text}, cited, R.statute_references)
    assert kept['12 USC 1757'].startswith('on the CU statute map')
    assert kept['7 USC 1a'].startswith('cited from a CU-relevant bill section: Sec. 2 Credit unions')
    assert omitted == {'42 USC 1395x': SEL.STATUTE_OMITTED}       # a wide-only section never pulls a statute in


# ---- collect(): the gates --------------------------------------------------------------------------------------

def test_a_bill_that_fits_never_reads_the_config_and_returns_the_old_3_tuple(tmp_path, monkeypatch):
    harness(monkeypatch, bill_xml(section('1', 'Short title', 'Fixture. ' + cites(('12', '1757')))), {})
    monkeypatch.setattr(SEL, 'load_config', lambda *a: (_ for _ in ()).throw(AssertionError('config read')))
    result = R.collect(KEY, tmp_path, STAMP)
    assert len(result) == 3


def test_too_many_citations_fetches_only_cu_statutes_and_records_the_rest(tmp_path, monkeypatch):
    many = [('42', str(1000 + n)) for n in range(30)]
    raw = bill_xml(section('1', 'Short title', 'Fixture.'), section('2', 'Health', cites(*many)),
                   section('3', 'Credit unions', 'Each federal credit union, 12 U.S.C. 1757, may act.'))
    fetched = harness(monkeypatch, raw, {})
    snapshot, texts, sources, manifest = R.collect(KEY, tmp_path, STAMP)
    assert fetched == ['12 USC 1757']
    assert manifest['trigger'] == 'statutes' and manifest['steps'] == ['S2'] and manifest['cited_statutes'] == 31
    assert len(manifest['statutes']['omitted']) == 30
    assert all(row['reason'] == SEL.STATUTE_OMITTED and row['fetched'] is False for row in manifest['statutes']['omitted'])
    config_copy = Path(manifest['config']['path'])
    assert config_copy.parent == tmp_path.resolve() and hashlib.sha256(config_copy.read_bytes()).hexdigest() == manifest['config']['sha256']


def test_too_many_cu_citations_is_failed_not_held(tmp_path, monkeypatch):
    raw = bill_xml(section('1', 'Short title', 'Fixture. ' + cites(*[('12', str(1751 + n)) for n in range(25)])))
    harness(monkeypatch, raw, {})
    with pytest.raises(SEL.EvidenceEnvelopeExceeded) as failed:
        R.collect(KEY, tmp_path, STAMP)
    assert failed.value.gate == 'statutes' and len(failed.value.manifest['statutes']['kept']) == 25


def _big_bill():
    return bill_xml(section('1', 'Short title', 'Fixture Act.'),
                    section('2', 'Credit unions', 'An insured credit union, 12 U.S.C. 1757, may act.'),
                    section('3', 'Health', cites(('42', '1395x'))),
                    section('4', 'Rural', FILLER), section('5', 'More rural', FILLER))


def test_char_gate_stops_at_s1_when_notes_were_the_bulk(tmp_path, monkeypatch):
    harness(monkeypatch, _big_bill(), {})
    monkeypatch.setattr(SEL, 'CHAR_LIMIT', 9000)
    snapshot, texts, sources, manifest = R.collect(KEY, tmp_path, STAMP)
    assert manifest['steps'] == ['S1'] and manifest['trigger'] == 'chars'
    assert manifest['chars_before'] > 9000 >= manifest['chars_after'] == sum(map(len, texts.values()))
    assert {row['id'] for row in manifest['notes']['omitted']} == {'12 USC 1757', '42 USC 1395x'}
    assert texts[BILL_URL] == R.GF._parse_bill_text(_big_bill(), url=BILL_URL, canonical_key=KEY)   # bill text whole


def test_char_gate_escalates_s1_s2_s3_and_then_fails(tmp_path, monkeypatch):
    harness(monkeypatch, _big_bill(), {})
    monkeypatch.setattr(SEL, 'CHAR_LIMIT', 1500)
    snapshot, texts, sources, manifest = R.collect(KEY, tmp_path, STAMP)
    assert manifest['steps'] == ['S1', 'S2', 'S3']
    assert [row['id'] for row in manifest['statutes']['omitted']] == ['42 USC 1395x']
    assert [row['section'] for row in manifest['bill_sections']['omitted']] == ['Sec. 3 Health', 'Sec. 4 Rural', 'Sec. 5 More rural']
    assert statute_url('42', '1395x') not in texts and all(s['url'] != statute_url('42', '1395x') for s in sources)
    assert [n['id'] for n in manifest['notes']['omitted']] == ['12 USC 1757']        # pruned with S2
    monkeypatch.setattr(SEL, 'CHAR_LIMIT', 50)
    with pytest.raises(SEL.EvidenceEnvelopeExceeded) as failed:
        R.collect(KEY, tmp_path, STAMP)
    assert failed.value.gate == 'chars' and failed.value.manifest['steps'] == ['S1', 'S2', 'S3']
    assert failed.value.manifest['chars_after'] > 50


def test_no_step_fills_to_the_budget(tmp_path, monkeypatch):
    harness(monkeypatch, _big_bill(), {})
    outcomes = []
    for limit in (1500, 3000):          # both reach S3; the omissions are a rule, not a fill to the limit
        monkeypatch.setattr(SEL, 'CHAR_LIMIT', limit)
        _, texts, _, manifest = R.collect(KEY, tmp_path, STAMP)
        outcomes.append((manifest['steps'], manifest['bill_sections'], texts))
    assert outcomes[0] == outcomes[1]


# ---- fingerprint, replay, reuse, validation --------------------------------------------------------------------

def test_an_unselected_fingerprint_is_the_old_formula_byte_for_byte():
    texts = {'https://example.invalid/text': 'official text'}
    old = hashlib.sha256(json.dumps({'texts': texts, 'policy': R.POLICY, 'model': 'fixture', 'transport': 'claude-cli',
                                     'schema': R.FINGERPRINT_SCHEMA}, sort_keys=True).encode()).hexdigest()
    assert R.evidence_fingerprint(texts, model='fixture', transport='claude-cli') == old == B.PINNED_FINGERPRINT
    assert R.evidence_fingerprint(texts, model='fixture', transport='claude-cli', selection=None) == old


def _sealed(tmp_path, monkeypatch, limit=1500):
    harness(monkeypatch, _big_bill(), {})
    monkeypatch.setattr(SEL, 'CHAR_LIMIT', limit)
    snapshot, texts, sources, manifest = R.collect(KEY, tmp_path / 'evidence', STAMP)
    decision = {'canonical_key': KEY, 'evidence': sources, 'evidence_selection': manifest,
                'evidence_fingerprint': R.evidence_fingerprint(texts, model='m', transport='claude-cli', selection=manifest),
                'fingerprint_parameters': {'policy': R.POLICY, 'model': 'm', 'transport': 'claude-cli'},
                'disposition': 'hold', 'confidence': 'low', 'rationale': 'fixture', 'categories': [], 'classifier': {}}
    return texts, manifest, decision


def test_a_sealed_selection_replays_to_exactly_what_the_classifier_saw(tmp_path, monkeypatch):
    texts, manifest, decision = _sealed(tmp_path, monkeypatch)
    assert R.bound_decision_texts(decision) == texts
    complete = R.bound_decision_texts(decision, apply_selection=False)
    assert SEL.MARKER_PREFIX not in complete[BILL_URL]
    assert R.evidence_fingerprint(texts, model='m', transport='claude-cli', selection=manifest) != \
        R.evidence_fingerprint(texts, model='m', transport='claude-cli')
    reused = R.reusable_decision(KEY, texts, [], published=decision, checkpoint=None, model='m', transport='claude-cli',
                                 selection=manifest)
    assert reused is not None and reused[1]['cache_hit'] is True


def test_replay_refuses_a_changed_config_and_skips_another_version(tmp_path, monkeypatch):
    texts, manifest, decision = _sealed(tmp_path, monkeypatch)
    Path(manifest['config']['path']).write_bytes(b'{}')
    with pytest.raises(ValueError, match='config hash mismatch'):
        R.bound_decision_texts(decision)
    other = {**decision, 'evidence_selection': {**manifest, 'version': 'sentinel-evidence-selection-v0'}}
    with pytest.raises(SEL.SelectionReplayUnavailable):
        R.bound_decision_texts(other)
    assert R.reusable_decision(KEY, texts, [], published=other, checkpoint=None, model='m', transport='claude-cli',
                               selection=manifest) is None


def test_a_quote_across_an_omission_marker_is_refused():
    marker = f'{SEL.MARKER_PREFIX} v1: Sec. 4 Rural, 10 chars, reason: x]'
    text = 'An insured credit union may act. ' + marker + ' More text follows here.'
    decision = {'canonical_key': KEY, 'disposition': 'exclude', 'confidence': 'high', 'rationale': 'r',
                'categories': [], 'exclusion_source_url': BILL_URL, 'exclusion_quote': 'may act. ' + marker}
    with pytest.raises(ValueError, match='affirmative official evidence'):
        R.validate_decision(decision, KEY, {BILL_URL: text}, [])


# ---- main(): records, FAILED, DEGRADED, migration, parking -------------------------------------------------------

def _manifest(config_sha='c' * 64):
    return {'version': SEL.VERSION, 'config': {'path': 'x', 'sha256': config_sha}, 'trigger': 'chars',
            'limits': {'chars': 1, 'statutes': 24}, 'steps': ['S1'], 'cited_statutes': 1,
            'statutes': {'kept': {}, 'omitted': []},
            'notes': {'omitted': [{'id': '12 USC 1757', 'url': 'u', 'chars_omitted': 9, 'reason': 'notes'}],
                      'kept_for_note_citation': [], 'not_separable': []},
            'bill_sections': None, 'chars_before': 2, 'chars_after': 1}


def test_omissions_are_recorded_in_the_prompt_the_verdict_and_the_receipt(tmp_path, monkeypatch):
    B.build(tmp_path, monkeypatch, keys=['119:hr:11'])
    manifest = _manifest()
    real_collect = R.collect
    monkeypatch.setattr(R, 'collect', lambda key, d, s: (*real_collect(key, d, s), manifest))
    prompts = []

    def run(argv, **kwargs):
        prompts.append(json.loads(kwargs['input']))
        return B.held(prompts[-1]['canonical_key'])
    monkeypatch.setattr(R.subprocess, 'run', run)
    code, generation, checkpoint, _ = B.run_main(tmp_path)
    assert prompts[0]['evidence_selection']['omitted_statute_notes'] == ['12 USC 1757']
    assert 'Omitted text was not supplied' in prompts[0]['evidence_selection']['notice']
    for document in (generation, checkpoint):
        assert document['decisions']['119:hr:11']['evidence_selection'] == manifest


def test_an_unselected_prompt_is_unchanged(tmp_path, monkeypatch):
    B.build(tmp_path, monkeypatch, keys=['119:hr:11'])
    prompts = []

    def run(argv, **kwargs):
        prompts.append(json.loads(kwargs['input']))
        return B.held(prompts[-1]['canonical_key'])
    monkeypatch.setattr(R.subprocess, 'run', run)
    B.run_main(tmp_path)
    assert sorted(prompts[0]) == ['allowed_categories', 'canonical_key', 'official_documents', 'output_shape']


def test_a_failed_bill_is_listed_not_held_and_the_run_is_degraded(tmp_path, monkeypatch, capsys):
    B.build(tmp_path, monkeypatch, keys=['119:hr:11', '119:hr:12'])

    def collect(key, d, s):
        if key == '119:hr:12':
            raise SEL.EvidenceEnvelopeExceeded('chars', _manifest())
        (tmp_path / 'text.xml').write_bytes(b'official text')
        return B.snapshot(key), dict(B.TEXTS), [{'url': 'https://example.invalid/text', 'path': str(tmp_path / 'text.xml'),
                                                 'sha256': hashlib.sha256(b'official text').hexdigest()}]
    monkeypatch.setattr(R, 'collect', collect)
    B.fake_cli(monkeypatch, [B.held])
    code, generation, checkpoint, installed = B.run_main(tmp_path)
    out = capsys.readouterr().out
    assert code == 0 and generation['status'] == 'PASS' and installed
    assert generation['run_verdict'] == 'DEGRADED'
    failed = generation['evidence_failed']['119:hr:12']
    assert failed['gate'] == 'chars' and failed['selection']['steps'] == ['S1'] and failed['config_sha256'] == 'c' * 64
    assert '119:hr:12' not in generation['decisions'] and '119:hr:12' not in checkpoint['decisions']
    assert '119:hr:12' not in generation['deferred_keys']
    assert 'FAILED (evidence envelope, D-366)' in out
    assert refresh_failure.evidence_failed_count(out) == 1


def test_a_clean_run_is_not_degraded(tmp_path, monkeypatch, capsys):
    B.build(tmp_path, monkeypatch, keys=['119:hr:11'])
    B.fake_cli(monkeypatch, [B.held])
    _, generation, _, _ = B.run_main(tmp_path)
    assert generation['run_verdict'] == 'PASS' and generation['evidence_failed'] == {}
    assert refresh_failure.evidence_failed_count(capsys.readouterr().out) == 0


def test_legacy_envelope_holds_become_failed_and_are_retried(tmp_path, monkeypatch):
    legacy = {k: {**B.hold_record(k, '2026-09-01T00:00:00+00:00'), 'rationale': reason,
                  'authority': 'automated_evidence_availability_gate'}
              for k, reason in (('119:hr:11', 'ValueError: complete evidence exceeds model envelope; not silently clipped'),
                                ('119:hr:12', 'ValueError: statutory context exceeds envelope; no partial classification'))}
    order = B.build(tmp_path, monkeypatch, keys=['119:hr:11', '119:hr:12'], published={'decisions': legacy})

    def collect(key, d, s):
        order.append(key)
        raise SEL.EvidenceEnvelopeExceeded('statutes' if key.endswith('12') else 'chars', _manifest())
    monkeypatch.setattr(R, 'collect', collect)
    _, generation, _, _ = B.run_main(tmp_path)
    assert sorted(order) == ['119:hr:11', '119:hr:12']          # a migrated hold is never parked
    assert generation['decisions'] == {}
    assert sorted(generation['evidence_failed']) == ['119:hr:11', '119:hr:12']


def test_the_legacy_migration_is_idempotent_across_runs(tmp_path, monkeypatch):
    # Production shape: the same legacy holds sit in the published generation AND the checkpoint. A second run must not
    # re-migrate them over the first run's selection record (which would un-park them and relabel them as awaiting).
    legacy = {k: {**B.hold_record(k, '2026-09-01T00:00:00+00:00'), 'rationale': reason,
                  'authority': 'automated_evidence_availability_gate'}
              for k, reason in (('119:hr:11', 'ValueError: complete evidence exceeds model envelope; not silently clipped'),
                                ('119:hr:12', 'ValueError: statutory context exceeds envelope; no partial classification'))}
    B.build(tmp_path, monkeypatch, keys=sorted(legacy), published={'decisions': legacy})
    R.write_json(tmp_path / 'data/legislation/sentinel_admission_checkpoint.json',
                 {'schema': 'sentinel-admission-checkpoint-v1', 'decisions': legacy, 'errors': {}})

    def collect(key, d, s):
        raise SEL.EvidenceEnvelopeExceeded('chars', _manifest())
    monkeypatch.setattr(R, 'collect', collect)
    for _ in range(2):
        shutil.rmtree(tmp_path / 'audits', ignore_errors=True)   # both runs may share one second-resolution run dir
        code = R.main(['--root', str(tmp_path)])
        installed = json.loads((tmp_path / SA.RELATIVE).read_text(encoding='utf-8'))
        checkpoint = json.loads((tmp_path / 'data/legislation/sentinel_admission_checkpoint.json').read_text(encoding='utf-8'))
        assert code == 0 and installed['run_verdict'] == 'DEGRADED'
        assert installed['decisions'] == {} and checkpoint['decisions'] == {}
        assert sorted(installed['evidence_failed']) == sorted(legacy)
        assert installed['evidence_failed_awaiting_selection_retry'] == []
        assert not any(v.get('migrated_from_hold') for v in installed['evidence_failed'].values())


def test_a_failed_key_is_parked_until_the_rules_change_or_a_week_passes(tmp_path, monkeypatch):
    sha = SEL.load_config()[2]
    recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    previous = {'evidence_failed': {
        '119:hr:11': {'gate': 'chars', 'reason': 'r', 'checked_at': recent, 'config_sha256': sha, 'selection': None},
        '119:hr:12': {'gate': 'chars', 'reason': 'r', 'checked_at': recent, 'config_sha256': 'other', 'selection': None},
        '119:hr:13': {'gate': 'chars', 'reason': 'r', 'checked_at': old, 'config_sha256': sha, 'selection': None}}}
    order = B.build(tmp_path, monkeypatch, keys=['119:hr:11', '119:hr:12', '119:hr:13'], published=previous)
    B.fake_cli(monkeypatch, [B.held])
    _, generation, _, _ = B.run_main(tmp_path)
    assert sorted(order) == ['119:hr:12', '119:hr:13']
    assert generation['parked_evidence_failed_keys'] == ['119:hr:11']
    assert list(generation['evidence_failed']) == ['119:hr:11']   # the other two were decided this run


def test_an_admitted_bill_that_fails_leaves_the_scored_set(tmp_path, monkeypatch):
    key = '119:hr:11'
    published = {'bills': {key: B.snapshot(key)}, 'bill_catalog': {key: B.snapshot(key)},
                 'decisions': {key: {**B.hold_record(key, STAMP), 'disposition': 'include', 'confidence': 'high'}}}
    B.build(tmp_path, monkeypatch, keys=[key], published=published)
    monkeypatch.setattr(R, 'collect', lambda k, d, s: (_ for _ in ()).throw(SEL.EvidenceEnvelopeExceeded('chars', _manifest())))
    _, generation, _, _ = B.run_main(tmp_path)
    assert key not in generation['bills'] and key not in generation['decisions']
    assert generation['evidence_failed'][key]['previously_admitted_checked_at'] == STAMP
    assert key in generation['bill_catalog']


# ---- the refresh row ---------------------------------------------------------------------------------------------

def test_the_refresh_freshness_row_is_degraded_while_bills_are_failed():
    now = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)
    entry = {'state': refresh_state.OK, 'last_ok_utc': refresh_state.stamp(now - timedelta(hours=1)), 'torn': False,
             'coverage': refresh_state.COVERAGE_OK, 'evidence_failed': 4}
    record = refresh_state.freshness_record('CORE', 24, entry, now, 8)
    assert record['status'] == refresh_state.DEGRADED and '4 bill(s) FAILED the evidence envelope' in record['detail']
    clean = refresh_state.freshness_record('CORE', 24, {**entry, 'evidence_failed': None}, now, 8)
    assert clean['status'] == refresh_state.FRESH


def test_evidence_failed_count_reads_only_the_summary_line():
    assert refresh_failure.evidence_failed_count('119:hr:1 include\n{"status": "PASS", "evidence_failed": 3}\n') == 3
    assert refresh_failure.evidence_failed_count('evidence_failed: 9 in prose\n') == 0
    assert refresh_failure.evidence_failed_count('') == 0


# ---- review round 1 ----------------------------------------------------------------------------------------------

def test_a_failed_key_whose_evidence_now_fits_is_not_failed_whatever_follows(tmp_path, monkeypatch):
    previous = {'evidence_failed': {'119:hr:11': {'gate': 'chars', 'reason': 'r', 'checked_at': '2026-09-01T00:00:00+00:00',
                                                  'config_sha256': 'other', 'selection': None}}}
    B.build(tmp_path, monkeypatch, keys=['119:hr:11'], published=previous)
    medium = B.cli(0, json.dumps({'is_error': False, 'uuid': 'u', 'usage': {}, 'structured_output': {
        'canonical_key': '119:hr:11', 'disposition': 'include', 'confidence': 'medium', 'rationale': 'x', 'categories': []}}))
    B.fake_cli(monkeypatch, [medium])
    _, generation, _, _ = B.run_main(tmp_path)
    assert generation['decisions']['119:hr:11']['disposition'] == 'hold'
    assert generation['evidence_failed'] == {} and generation['run_verdict'] == 'PASS'


def test_a_migrated_legacy_hold_is_counted_as_awaiting_its_selection_retry(tmp_path, monkeypatch, capsys):
    legacy = {'119:hr:11': {**B.hold_record('119:hr:11', '2026-09-01T00:00:00+00:00'),
                            'rationale': 'ValueError: complete evidence exceeds model envelope; not silently clipped'}}
    B.build(tmp_path, monkeypatch, keys=['119:hr:11'], published={'decisions': legacy})
    monkeypatch.setattr(R, 'collect', lambda k, d, s: (_ for _ in ()).throw(R.SourceUnavailable('fixture outage')))
    _, generation, _, _ = B.run_main(tmp_path)        # attempted, but selection never ran: still awaiting its retry
    assert generation['evidence_failed_awaiting_selection_retry'] == ['119:hr:11']
    assert generation['run_verdict'] == 'DEGRADED'
    assert 'awaiting its first selection retry' in generation['evidence_failed']['119:hr:11']['reason']
    summary = json.loads(capsys.readouterr().out.strip().split('\n')[-1])
    assert summary['evidence_failed_awaiting_selection_retry'] == ['119:hr:11'] and summary['evidence_failed'] == 1


def test_a_quote_that_starts_inside_a_marker_is_refused_and_one_beside_it_is_not():
    marker = f'{SEL.MARKER_PREFIX} v1: Sec. 4 Rural, 10 chars, reason: {SEL.NO_CU_TERM}]'
    text = 'An insured credit union may act now. ' + marker + ' SEC. 5. The Secretary shall act.'
    assert SEL.quote_overlaps_marker(text, f'reason: {SEL.NO_CU_TERM}] SEC. 5. The Secretary')
    assert not SEL.quote_overlaps_marker(text, 'An insured credit union may act now.')
    assert not SEL.quote_overlaps_marker(text, 'SEC. 5. The Secretary shall act.')
    decision = {'canonical_key': KEY, 'disposition': 'exclude', 'confidence': 'high', 'rationale': 'r', 'categories': [],
                'exclusion_source_url': BILL_URL, 'exclusion_quote': f'{SEL.NO_CU_TERM}] SEC. 5. The Secretary'}
    with pytest.raises(ValueError, match='affirmative official evidence'):
        R.validate_decision(decision, KEY, {BILL_URL: text}, [])


def test_s1_needs_the_end_of_the_operative_text_before_its_cut():
    no_end = b'<html><body><h3 class="section-head">&sect;1. X</h3><p>law</p><h4 class="note-head">N</h4><p>n</p></body></html>'
    assert SEL.operative_html(no_end) is None
    early_head = (b'<h4 class="note-head">early</h4><!-- field-start:statute --><p>law</p><!-- field-end:statute -->'
                  b'<!-- field-end:sourcecredit --><h4 class="note-head">Editorial Notes</h4><p>notes</p>')
    cut = SEL.operative_html(early_head)
    assert cut.endswith(b'<!-- field-end:sourcecredit -->') and b'law' in cut


def test_replay_reads_the_config_snapshot_through_to_host(tmp_path, monkeypatch):
    texts, manifest, decision = _sealed(tmp_path, monkeypatch)
    seen = []
    monkeypatch.setattr(SEL, 'to_host', lambda p: seen.append(p) or p)
    assert R.bound_decision_texts(decision) == texts
    assert manifest['config']['path'] in seen


def test_statute_gate_then_char_gate_replays(tmp_path, monkeypatch):
    many = [('42', str(1000 + n)) for n in range(30)]
    raw = bill_xml(section('1', 'Short title', 'Fixture.'), section('2', 'Health', cites(*many)),
                   section('3', 'Credit unions', 'Each federal credit union, 12 U.S.C. 1757, may act.'),
                   section('4', 'Rural', FILLER))
    harness(monkeypatch, raw, {})
    monkeypatch.setattr(SEL, 'CHAR_LIMIT', 1500)
    _, texts, sources, manifest = R.collect(KEY, tmp_path / 'evidence', STAMP)
    assert manifest['steps'] == ['S2', 'S1', 'S3'] and manifest['chars_before_scope'].startswith('after S2')
    decision = {'canonical_key': KEY, 'evidence': sources, 'evidence_selection': manifest}
    assert R.bound_decision_texts(decision) == texts


# Golden: the selection of this fixture is pinned. A change here is a behaviour change to selection: bump SEL.VERSION.
GOLDEN_SELECTION = '2cfedffeb175c71d01c015abd4fc1128c98ee3edfe4d632d4a3b56fb64a7a14d'


def test_golden_selection_is_pinned(tmp_path, monkeypatch):
    texts, manifest, _ = _sealed(tmp_path, monkeypatch)
    stable = {k: v.replace(str(tmp_path.resolve()), '<tmp>') for k, v in texts.items()}
    digest = hashlib.sha256(json.dumps({'texts': stable, 'view': SEL.fingerprint_view(
        {**manifest, 'config': {'sha256': 'fixed'}})}, sort_keys=True).encode()).hexdigest()
    print('GOLDEN', digest)
    assert digest == GOLDEN_SELECTION, digest


def test_sa_load_validates_a_selected_include_against_what_the_classifier_saw(tmp_path, monkeypatch):
    B.build(tmp_path, monkeypatch, keys=[KEY])
    R.write_json(tmp_path / 'source_data/legislation/acu_legislation_search_registry.json',
                 {'categories': [{'id': 'payments'}]})
    harness(monkeypatch, _big_bill(), {})
    monkeypatch.setattr(R, '_govinfo_snapshot', lambda *a, **k: {**B.snapshot(KEY), 'title': 'Fixture', 'summary': '',
                                                                 'latest_action': {'text': 'x'}, 'cosponsor_count': 0,
                                                                 'url': 'u', 'introduced_date': '2026-01-01'})
    monkeypatch.setattr(R, 'collect', REAL_COLLECT)
    monkeypatch.setattr(R, 'reusable_decision', REAL_REUSABLE)
    monkeypatch.setattr(SEL, 'CHAR_LIMIT', 1500)
    quote = 'An insured credit union, 12 U.S.C. 1757, may act.'
    include = B.cli(0, json.dumps({'is_error': False, 'uuid': 'u', 'usage': {}, 'structured_output': {
        'canonical_key': KEY, 'disposition': 'include', 'confidence': 'high', 'beneficiary_class': 'cu_primary',
        'rationale': 'fixture include', 'categories': [{'category': 'Payments', 'direction': 1, 'source_url': BILL_URL,
                                                         'quote': quote, 'rationale': 'helps credit unions offer payments'}]}}))
    B.fake_cli(monkeypatch, [include])
    code, generation, _, installed = B.run_main(tmp_path)
    assert code == 0 and installed
    assert generation['decisions'][KEY]['evidence_selection']['steps'] == ['S1', 'S2', 'S3']
    document = SA.load(tmp_path)
    assert KEY in document['bills']
    # D-366: a generation that lists an admitted bill as FAILED is refused.
    tampered = json.loads((tmp_path / SA.RELATIVE).read_text(encoding='utf-8'))
    tampered['evidence_failed'] = {KEY: {'gate': 'chars'}}
    R.write_json(tmp_path / SA.RELATIVE, tampered)
    with pytest.raises(ValueError, match='D-366'):
        SA.load(tmp_path)


REAL_COLLECT = R.collect
REAL_REUSABLE = R.reusable_decision


# Goldens for the two paths the first golden does not reach. A change here is a behaviour change to selection: bump
# SEL.VERSION (review round 2).
GOLDEN_STATUTE_THEN_CHARS = '9430e18975166ed07f73eb801ad7de3621956712b7d41c191bfb7139deb83c4b'
GOLDEN_OPERATIVE = '3d3ef555d759ee065fa596003db582d6971046bdea15eb5677ad6e9fc09dcbb3'


def test_golden_statute_gate_then_char_gate_is_pinned(tmp_path, monkeypatch):
    many = [('42', str(1000 + n)) for n in range(30)]
    raw = bill_xml(section('1', 'Short title', 'Fixture.'), section('2', 'Health', cites(*many)),
                   section('3', 'Credit unions', 'Each federal credit union, 12 U.S.C. 1757, may act.'),
                   section('4', 'Rural', FILLER))
    harness(monkeypatch, raw, {})
    monkeypatch.setattr(SEL, 'CHAR_LIMIT', 1500)
    _, texts, _, manifest = R.collect(KEY, tmp_path / 'evidence', STAMP)
    digest = hashlib.sha256(json.dumps({'texts': texts, 'view': SEL.fingerprint_view(
        {**manifest, 'config': {'sha256': 'fixed'}}), 'kept': manifest['statutes']['kept']}, sort_keys=True).encode()).hexdigest()
    print('GOLDEN_STATUTE_THEN_CHARS', digest)
    assert digest == GOLDEN_STATUTE_THEN_CHARS, digest


def test_golden_operative_cut_is_pinned():
    page = statute_page('12', '1757', 'A Federal credit union shall have power to lend.')
    source = _source('12', '1757')
    text = R.statute_document_text(SEL.operative_html(page), source)
    digest = hashlib.sha256(text.encode('utf-8')).hexdigest()
    print('GOLDEN_OPERATIVE', digest)
    assert digest == GOLDEN_OPERATIVE, digest
