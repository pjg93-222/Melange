"""leg_evidence_recompute.claim_e14 pins three counts of manual_bill_evidence.csv at the reported base (296 LTR rows, 297 sponsor-substring
rows, 297 manual rows). After D-263 promotions each pin is that base PLUS the auto-letter rows counted in the CSV itself (Note starts
'auto-letter'): exact, never 'at least', and never taken from a receipt that could disagree with the file."""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from legislation import leg_evidence_recompute as LER   # noqa: E402


def row(i, bill="LTR-119-X", role="original-cosponsor", note="hand"):
    return {"Member": "m%d" % i, "Role": role, "Bill": bill, "Category": "CDFI Fund", "Note": note}


def ctx(auto_rows=0, hand_extra=0):
    manual = [row(i) for i in range(296 + hand_extra)] + [row(900, bill="H.R.1", role="sponsor")]            # the report's 297-row base
    manual += [row(1000 + i, bill="LTR-119-AUTO", note="auto-letter LTR-119-AUTO sha256=abc via L2:acu-letter") for i in range(auto_rows)]
    return SimpleNamespace(manual=manual, category_stance={}, selected=[], vote_lean={})


def flags(entry):
    return entry["delta"]["flags"][:3]


def test_the_base_pins_are_unchanged_without_auto_letter_rows():
    assert flags(LER.claim_e14(ctx())) == ["MATCH", "MATCH", "MATCH"]
    assert flags(LER.claim_e14(ctx(hand_extra=1))) == ["DRIFT", "DRIFT", "DRIFT"]


def test_all_three_pins_are_the_base_plus_the_auto_letter_rows_counted_in_the_csv():
    entry = LER.claim_e14(ctx(auto_rows=89))
    assert flags(entry) == ["MATCH", "MATCH", "MATCH"]
    assert entry["delta"]["ltr_rows_any_role"] == 0 and entry["delta"]["manual_rows"] == 0 and entry["delta"]["total_sponsor_substring_pass"] == 0
    assert entry["recomputed"]["auto_letter_rows"] == 89


def test_a_hand_row_that_merely_mentions_auto_letter_is_not_counted():
    c = ctx(auto_rows=0)
    c.manual.append(row(2000, bill="LTR-119-HAND", note="Congressional letter (auto-letter packet)"))   # Note does not START with it
    assert flags(LER.claim_e14(c)) == ["DRIFT", "DRIFT", "DRIFT"]


@pytest.mark.parametrize("extra", [-1, 1])
def test_the_pin_is_exact_never_at_least(extra):
    c = ctx(auto_rows=89)
    if extra < 0:
        c.manual.pop(0)                 # a hand row lost: the auto-letter count is read from the file, so only hand drift can show
    else:
        c.manual.append(row(3000, bill="LTR-119-HAND"))
    assert flags(LER.claim_e14(c)) == ["DRIFT", "DRIFT", "DRIFT"]
