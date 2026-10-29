# -*- coding: utf-8 -*-
"""Roster-drift contract for efficiency_layers (E2E attempt 6: ``current-member input coverage failure: panel=3``).

The frozen LDA ``panel.csv`` and ``member_receptivity.json`` predate the roster refresh, so a roster arrival has no row in
either.  Ruling: the arrival is WITHHELD from the layer (no row in ``efficiency_layers.json``, one logged ``!!`` line); any
non-arrival gap still raises the original ``current-member input coverage failure``.
"""
import json
import os
import sys

import pytest

FEC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if FEC not in sys.path:
    sys.path.insert(0, FEC)
import roster as roster_module
from engine import efficiency_layers as EL

SOURCE = open(os.path.join(FEC, 'engine', 'efficiency_layers.py'), encoding='utf-8').read()

ROWS = [
    {'member': 'A', 'bioguide': 'X000001', 'chamber': 'House', 'term_start': '2023-01-03'},
    {'member': 'B', 'bioguide': 'X000002', 'chamber': 'House', 'term_start': '2023-01-03'},
    {'member': 'New', 'bioguide': 'X000004', 'chamber': 'House', 'term_start': '2026-06-01'},
]


@pytest.fixture()
def root(tmp_path, monkeypatch):
    os.makedirs(tmp_path / 'data' / 'engine')
    (tmp_path / 'data' / 'engine' / 'roster.json').write_text(json.dumps(
        {'schema': roster_module.SCHEMA, 'members': ROWS, 'departed': []}), encoding='utf-8')
    (tmp_path / 'data' / 'engine' / 'collection_intake_receipt.json').write_text('{"status": "REJECTED"}', encoding='utf-8')   # before the media gate (D-330)
    monkeypatch.setattr(roster_module, 'RULED_ARRIVALS', {'X000004': 'New'})   # this fixture's arrivals stand in for the ruled three
    monkeypatch.setattr(roster_module, '_now', lambda: roster_module.datetime.datetime(2026, 10, 27, tzinfo=roster_module.datetime.timezone.utc))   # inside the 119th
    return str(tmp_path)


def test_an_arrival_missing_panel_and_receptivity_is_withheld_and_logged(root, capsys):
    panel, rec, pricing = EL._coverage_withhold(['New'], ['New'], [], root)
    assert panel == rec == pricing == []
    lines = [l for l in capsys.readouterr().out.splitlines() if '!! efficiency layers' in l]
    assert len(lines) == 1 and 'roster drift; 1 WITHHELD' in lines[0] and 'New' in lines[0]


def test_a_non_arrival_gap_is_kept_so_the_check_still_raises(root, capsys):
    panel, rec, pricing = EL._coverage_withhold(['B', 'New'], [], ['A'], root)
    assert panel == ['B'] and rec == [] and pricing == ['A']
    assert len(capsys.readouterr().out.splitlines()) == 1     # New still logged as withheld


def test_no_gap_never_reads_roster_json(tmp_path, capsys):
    assert EL._coverage_withhold([], [], [], str(tmp_path)) == ([], [], [])   # tmp_path has no roster.json
    assert capsys.readouterr().out == ''


def test_a_non_arrival_only_gap_logs_nothing(root, capsys):
    assert EL._coverage_withhold(['B'], [], [], root) == (['B'], [], [])
    assert capsys.readouterr().out == ''


def test_withhold_precedes_the_raise_in_build_from_files():
    call = '_coverage_withhold(missing_panel, missing_receptivity, missing_pricing'
    assert call in SOURCE
    assert SOURCE.index(call) < SOURCE.index('current-member input coverage failure')


def test_the_withheld_arrivals_are_counted_in_the_artifact_not_only_logged():
    # the withhold is never silent: efficiency_layers.json's panel_coverage receipt names every withheld arrival
    assert 'withheld_arrivals = sorted(gaps - set(missing_panel) - set(missing_receptivity) - set(missing_pricing))' in SOURCE
    assert '"withheld_roster_arrivals": withheld_arrivals' in SOURCE


def test_an_expired_tolerance_withholds_nobody(root, capsys):
    with open(os.path.join(root, 'data', 'engine', 'collection_intake_receipt.json'), 'w', encoding='utf-8') as f:
        f.write('{"status": "ACCEPTED"}')
    assert EL._coverage_withhold(['New'], ['New'], [], root) == (['New'], ['New'], [])   # the coverage check raises
    assert capsys.readouterr().out == ''
