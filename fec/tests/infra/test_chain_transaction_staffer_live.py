# -*- coding: utf-8 -*-
"""DE-078 / D-330 ruling 6 (Paul, 2026-10-26): fec/surfaces/staffer_live/approved is written by CHAIN[77]
(build_clean_workspace) and must be inside the chain transaction, so a failed chain restores it.
Synthetic temp root only."""
import contextlib
import io
import os
import sys
from pathlib import Path

import pytest

FEC = Path(__file__).resolve().parents[2]
if str(FEC) not in sys.path:
    sys.path.insert(0, str(FEC))
import chain_transaction as CT  # noqa: E402

APPROVED = 'fec/surfaces/staffer_live/approved'


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv(CT.MIN_FREE_GB_ENV, '0')
    monkeypatch.delenv(CT.TXN_DIR_ENV, raising=False)
    monkeypatch.setenv(CT.DATA_ROOT_ENV, os.path.join(os.path.dirname(os.path.abspath(__file__)), '_no_such_melange_data_root_'))


def put(root, rel, data):
    path = Path(root, *rel.split('/'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def tree(root):
    base = Path(root, *APPROVED.split('/'))
    return {p.relative_to(base).as_posix(): p.read_bytes() for p in sorted(base.rglob('*')) if p.is_file()}


def quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def test_failed_chain_restores_staffer_live_approved(tmp_path):
    put(tmp_path, APPROVED + '/network.js', b'old network')
    put(tmp_path, APPROVED + '/data/people-days/d1.json', b'{"day": 1}')
    before = tree(tmp_path)
    txn = quiet(CT.begin, tmp_path, run_id='staffer-live')
    # CHAIN[77] partial build: rewrite, delete, and create
    put(tmp_path, APPROVED + '/network.js', b'partial 535 build')
    Path(tmp_path, *(APPROVED + '/data/people-days/d1.json').split('/')).unlink()
    put(tmp_path, APPROVED + '/data/catalog.json', b'{"n": 535}')
    assert quiet(txn.rollback, 'chain[77] failed') is True
    assert tree(tmp_path) == before
