"""R-set targeting (2026-10-28): --keys-file, and explicitly targeted tracked bills entering the admission pool.

A tracked bill is otherwise scored via the archive/ledger path; it reaches the classifier only when named. Frozen-ledger
and excluded_false_positive keys stay refused. Offline: B's fake collect and fake CLI only.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from legislation import refresh_sentinel_admissions as R  # noqa: E402
import test_sentinel_classifier_budget as B  # noqa: E402

TRACKED, OTHER = '119:hr:12', '119:hr:14'


def setup(root, monkeypatch, tracked=(TRACKED,)):
    order = B.build(root, monkeypatch, keys=B.KEYS)
    R.write_json(root / 'bill_repository_live.json', {'bills': {k: {} for k in tracked}})
    B.fake_cli(monkeypatch, [B.held])
    return order


def keys_file(root, text):
    path = root / 'keys.txt'
    path.write_text(text, encoding='utf-8')
    return str(path)


def test_untargeted_run_never_collects_a_tracked_key(tmp_path, monkeypatch):
    order = setup(tmp_path, monkeypatch)
    B.run_main(tmp_path)
    assert TRACKED not in order and OTHER in order


def test_keys_file_collects_a_tracked_key(tmp_path, monkeypatch):
    order = setup(tmp_path, monkeypatch)
    path = keys_file(tmp_path, f'# R-set\n\n  {TRACKED}  \n{TRACKED}\n# {OTHER}\n')
    B.run_main(tmp_path, '--keys-file', path)
    assert order == [TRACKED]


def test_keys_flag_collects_a_tracked_key(tmp_path, monkeypatch):
    order = setup(tmp_path, monkeypatch)
    B.run_main(tmp_path, '--keys', TRACKED)
    assert order == [TRACKED]


def test_a_tracked_key_not_in_discovery_is_still_collected(tmp_path, monkeypatch):
    order = setup(tmp_path, monkeypatch, tracked=('118:hr:99',))
    B.run_main(tmp_path, '--keys', '118:hr:99')
    assert order == ['118:hr:99']


@pytest.mark.parametrize('ledger,record', [
    ('legislation_adjudication_ledger.ndjson', {}),
    ('data/legislation/supplemental_adjudications.ndjson', {'integration_state': 'excluded_false_positive'}),
])
def test_frozen_and_excluded_keys_stay_refused_even_when_tracked(tmp_path, monkeypatch, ledger, record):
    setup(tmp_path, monkeypatch)
    path = tmp_path / ledger
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'canonical_key': TRACKED, **record}) + '\n', encoding='utf-8')
    with pytest.raises(ValueError, match=TRACKED):
        R.main(['--root', str(tmp_path), '--keys-file', keys_file(tmp_path, f'{OTHER}\n{TRACKED}\n')])


def test_keys_and_keys_file_together_are_refused(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    with pytest.raises(SystemExit):
        R.main(['--root', str(tmp_path), '--keys', TRACKED, '--keys-file', keys_file(tmp_path, TRACKED)])


@pytest.mark.parametrize('text', ['', '\n  \n', '# only a comment\n'])
def test_an_empty_keys_file_is_an_error_not_the_whole_pool(tmp_path, monkeypatch, text):
    order = setup(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='no keys'):
        R.main(['--root', str(tmp_path), '--keys-file', keys_file(tmp_path, text)])
    assert order == []
