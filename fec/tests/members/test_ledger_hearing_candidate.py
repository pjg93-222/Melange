"""Hearing antagonism: the live file by default (no live promotion); the ratified HA-ATTRIB-v1 candidate only behind
--hearing-candidate, with its sha256 enforced (Paul 2026-10-24 ratification, applied 2026-10-28 item 1)."""
import sys

import pytest

from fec.members import build_member_narrative_ledger as ledger


def run_main(monkeypatch, *flags):
    monkeypatch.setattr(sys, "argv", ["build_member_narrative_ledger.py", *flags])
    with pytest.raises(SystemExit) as caught:
        ledger.main()
    return str(caught.value)


def missing_inputs(message):
    assert message.startswith("missing required input(s): ")
    return message.split(": ", 1)[1].split(", ")


@pytest.fixture
def roots(tmp_path, monkeypatch):
    candidate = tmp_path / "melange-data" / "hearing_antagonism.candidate.json"
    monkeypatch.setattr(ledger, "ROOT", tmp_path / "repo")
    monkeypatch.setattr(ledger, "HEARING_CANDIDATE", candidate)
    return tmp_path / "repo", candidate


def test_default_reads_the_live_hearing_file_not_the_candidate(roots, monkeypatch):
    root, candidate = roots
    missing = missing_inputs(run_main(monkeypatch))
    assert str(root / "data" / "stance" / "hearing_antagonism.json") in missing
    assert str(candidate) not in missing


def test_opt_in_reads_only_the_candidate_and_enforces_its_sha(roots, monkeypatch):
    root, candidate = roots
    missing = missing_inputs(run_main(monkeypatch, "--hearing-candidate"))
    assert str(candidate) in missing
    assert str(root / "data" / "stance" / "hearing_antagonism.json") not in missing

    for path in missing:                       # every input present; the candidate has the wrong bytes
        path = ledger.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    assert "not the ratified HA-ATTRIB-v1 file" in run_main(monkeypatch, "--hearing-candidate")
    # without the opt-in the candidate is not consulted: only the absent live file is reported
    assert missing_inputs(run_main(monkeypatch)) == [str(root / "data" / "stance" / "hearing_antagonism.json")]
