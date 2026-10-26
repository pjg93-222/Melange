"""per_area_grade records the sha256 of every input it reads. The letter tag sidecar (D-263) feeds its beneficiary weights through
sentinel_admissions.effective_tags, so it belongs in INPUT_FILES - and an absent sidecar (no letters promoted yet) must not break the
build: it hashes as the empty file, so its later appearance changes the recorded hash."""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from engine import per_area_grade as PAG        # noqa: E402
from engine.primacy_method import DIAGNOSTIC     # noqa: E402
from legislation import letter_tags as LT        # noqa: E402

EMPTY = hashlib.sha256(b"").hexdigest()


def test_the_letter_tag_sidecar_is_a_recorded_input_of_the_diagnostic_board():
    sidecar = LT.SIDECAR.replace("\\", "/")
    assert (sidecar in PAG.INPUT_FILES) == bool(DIAGNOSTIC)


def test_an_absent_sidecar_hashes_as_the_empty_file_and_a_present_one_by_its_bytes(tmp_path):
    sidecar = LT.SIDECAR.replace("\\", "/")
    assert PAG.input_sha256(str(tmp_path), sidecar) == EMPTY
    target = tmp_path.joinpath(*sidecar.split("/"))
    target.parent.mkdir(parents=True)
    target.write_bytes(b'{"bill": "x"}\n')
    assert PAG.input_sha256(str(tmp_path), sidecar) == hashlib.sha256(b'{"bill": "x"}\n').hexdigest()


def test_a_missing_required_input_still_fails_loudly(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        PAG.input_sha256(str(tmp_path), "ranks_python.json")
