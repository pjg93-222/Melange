"""Offline read reuse must preserve source integrity and incomplete-data semantics."""
import csv
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from osc import config as C, validate as V
from osc.extract import Extractor, SCHEMAS
from osc.fetch import Fetcher
from osc.util import sha256_bytes
from test_reviews import lobby_pages, mk, serve


@pytest.mark.parametrize('source', ['valid', 'challenge', 'corrupt', 'missing'])
def test_split_reads_once_and_keeps_cache_rejection(tmp_path, monkeypatch, source):
    monkeypatch.setattr(C, 'YEARS', [2026])
    clients = [('A Corp', '1', 100)]
    pages = lobby_pages(100, 1, clients, {'1': {'total': 100, 'parts': {'In-house operations': 60, 'Outside firms': 40}}})
    split_url = C.u_client_split('1-slug', '1', 2026)
    if source == 'challenge':
        pages[split_url] = b'<html><title>Just a moment...</title></html>'
    writer, _ = mk(tmp_path, serve(pages), max_attempts=1)
    for url in pages:
        if source != 'missing' or url != split_url:
            writer.get(url)
    if source == 'corrupt':
        body_path, _ = writer._paths(writer.get(split_url).key)
        body_path.write_bytes(b'tampered')
    f = Fetcher(tmp_path, cache_only=True, request_fn=lambda u: pytest.fail('offline network request'))
    loads = []
    original_load = f.load_cached

    def counted_load(url):
        loads.append(url)
        return original_load(url)

    monkeypatch.setattr(f, 'load_cached', counted_load)
    scope = {'scope_id': 'ins', 'name': 'Insurance', 'opensecrets_code': 'F09', 'relation': 'requested',
             'lobby_category_id': 'F09', 'lobby_slug': 'insurance'}
    ex = Extractor(f, {'scopes': [scope]})
    ex.asof = {'as_of': '', 'start': '', 'end': '', 'note': ''}
    ex._modern_lobby(scope, ex.idf(scope), 'F09', 'insurance')
    assert loads.count(split_url) == 1
    assert f.stats['transport_calls'] == 0
    splits = ex.T['lobbying_client_splits']
    annual = ex.T['lobbying_annual'][0]
    if source == 'valid':
        assert splits[0]['split_sum_usd'] == 100
        assert annual['in_house_outside_status'] == 'complete_exact'
    else:
        assert annual['in_house_usd'] == annual['outside_firm_usd'] == ''
        assert annual['in_house_outside_status'] != 'complete_exact'
        if source == 'challenge':
            assert splits[0]['reason_code'] == 'http200_challenge_content'
            assert splits[0]['in_house_usd'] == ''
        else:
            assert splits == []


@pytest.mark.parametrize('tamper', [False, True])
def test_validation_reuses_inspected_metadata_and_still_hashes_bodies(tmp_path, monkeypatch, tamper):
    cache = tmp_path / 'cache' / 'ab'
    cache.mkdir(parents=True)
    meta_path = cache / 'abc.meta.json'
    original = b'primary source'
    (cache / 'abc.body').write_bytes(b'tampered' if tamper else original)
    meta = {'source_url': 'https://www.opensecrets.org/original', 'http_status': 200,
            'sha256': sha256_bytes(original), 'retrieved_utc': '2026-10-01T00:00:00+00:00'}
    meta_path.write_text(json.dumps(meta), encoding='utf-8')
    reads = []
    original_read = Path.read_text

    def counted_read(path, *args, **kwargs):
        if path == meta_path:
            reads.append(path)
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', counted_read)
    monkeypatch.setattr(V, 'national_checks', lambda *a: None)
    monkeypatch.setattr(V, 'pac_checks', lambda *a: None)
    monkeypatch.setattr(V, 'write_registry', lambda *a: None)

    def change_after_integrity_check(*args):
        meta_path.write_text(json.dumps({**meta, 'source_url': 'https://www.opensecrets.org/later'}), encoding='utf-8')

    monkeypatch.setattr(V, 'rest_checks', change_after_integrity_check)
    ex = SimpleNamespace(f=SimpleNamespace(cache_dir=cache.parent))
    out = tmp_path / 'out'
    checks = V.run_validation(None, ex, {k: [] for k in SCHEMAS}, out)
    integrity = next(c for c in checks.rows if c['check_id'] == 'cache_sha256_byte_exact')
    assert integrity['status'] == ('FAIL' if tamper else 'pass')
    assert len(reads) == 1
    with (out / 'request_manifest.csv').open(encoding='utf-8-sig', newline='') as stream:
        manifest = list(csv.DictReader(stream))
    assert manifest[0]['source_url'] == meta['source_url']
    assert manifest[0]['sha256'] == meta['sha256']
