"""Tag sidecar for auto-promoted sign-on letters (D-263): an untagged LTR- act raises KeyError in primacy_factors, and an
extra tag breaks its 'act universe and beneficiary tags are closed' check, so the sidecar only ever serves tags whose
letter has rows in manual_bill_evidence.csv."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from legislation import letter_tags as LT          # noqa: E402
from engine import primacy_factors as PF           # noqa: E402

CLS = {'beneficiary_class': 'cu_primary', 'act_weight': 1.0, 'authority': 'L2:acu-letter', 'rationale': 'r', 'confidence': 0.9}


def row(bill='LTR-119-CDFI-WATERS-2', congress=119):
    return LT.tag_row(bill, congress, 'Sign-on letter to Treasury', CLS, ['CDFI Fund'], role_weight=45.5, member_links=89,
                      tagged='2026-10-20', source_url='https://x.house.gov/a.pdf', sha256='ab' * 32)


def write(root, tags, bills):
    d = root / 'data' / 'legislation' / 'letters'
    d.mkdir(parents=True)
    (d / 'letter_tags.ndjson').write_text(''.join(json.dumps(t) + '\n' for t in tags), encoding='utf-8')
    (root / 'manual_bill_evidence.csv').write_text('Member,Role,Bill\r\n' + ''.join('x,y,%s\r\n' % b for b in bills), encoding='utf-8')


def test_no_sidecar_means_no_tags(tmp_path):
    assert LT.load(str(tmp_path)) == {}


def test_a_tag_serves_the_act_key_primacy_reads_and_scores_as_a_letter(tmp_path):
    write(tmp_path, [row()], ['LTR-119-CDFI-WATERS-2'])
    tags = LT.load(str(tmp_path))
    assert list(tags) == ['LTR-119-CDFI-WATERS-2|119']
    assert PF.act_weight(tags['LTR-119-CDFI-WATERS-2|119'], 'LTR-119-CDFI-WATERS-2|119') == PF.LETTER_W


def test_a_tag_without_csv_rows_is_not_served(tmp_path):
    """Sidecar written, CSV rename never happened: serving the tag would make primacy raise 'extra tags'."""
    write(tmp_path, [row('LTR-119-CDFI-A'), row('LTR-119-CDFI-B')], ['LTR-119-CDFI-A'])
    assert list(LT.load(str(tmp_path))) == ['LTR-119-CDFI-A|119']


def test_duplicate_or_incomplete_rows_raise(tmp_path):
    write(tmp_path, [row(), row()], ['LTR-119-CDFI-WATERS-2'])
    with pytest.raises(ValueError, match='duplicate'):
        LT.load(str(tmp_path))
    bad = row()
    del bad['areas']
    write(tmp_path / 'b', [bad], ['LTR-119-CDFI-WATERS-2'])
    with pytest.raises(ValueError, match='areas'):
        LT.load(str(tmp_path / 'b'))


def test_the_row_has_the_shape_of_the_hand_ratified_letter_tags():
    tags = Path(__file__).resolve().parents[3].joinpath('bill_beneficiary_tags.ndjson')
    if not tags.is_file():   # the public source export ships no hand-ratified tag file; the private repo does and is checked there
        pytest.skip('hand-ratified tags absent from this checkout: bill_beneficiary_tags.ndjson')
    hand = json.loads(next(l for l in tags.read_text(encoding='utf-8').splitlines()
                           if l.startswith('{"bill":"LTR-119-CDFI-WATERS"')))
    assert set(hand) - set(row()) == set()          # every key the hand tags carry, the sidecar tag carries too


# ---- wiring into sentinel_admissions.effective_tags (D-263) --------------------------------------------------

def test_effective_tags_merges_the_sidecar_and_a_ratified_tag_wins(tmp_path):
    from legislation import sentinel_admissions as SA
    write(tmp_path, [row('LTR-119-CDFI-NEW'), row('LTR-119-CDFI-HAND')], ['LTR-119-CDFI-NEW', 'LTR-119-CDFI-HAND'])
    ratified = {'LTR-119-CDFI-HAND|119': {'bill': 'LTR-119-CDFI-HAND', 'congress': '119', 'class': 'cu_primary', 'authority': 'ratified'}}
    document = {'bills': {}, 'memberships': [], 'decisions': {}}
    merged = SA.effective_tags(ratified, document, str(tmp_path))
    assert set(merged) == {'LTR-119-CDFI-NEW|119', 'LTR-119-CDFI-HAND|119'}
    assert merged['LTR-119-CDFI-HAND|119']['authority'] == 'ratified' and merged['LTR-119-CDFI-NEW|119']['authority'] == 'L2:acu-letter'
    assert SA.effective_tags(ratified, document) == ratified                       # no root: exactly the old behaviour
    assert SA.effective_tags({}, document, str(tmp_path / 'nothing-here')) == {}   # no sidecar: no-op


# ---- review ruling 6: one definition of "what the promoter added", counted from the CSV rows ---------------------------------------

def test_auto_letter_accounting_counts_notes_that_start_auto_letter_and_collapses_categories():
    rows = [{"Member": "A", "Role": "sponsor", "Bill": "LTR-1", "Note": "auto-letter LTR-1 sha256=ab"},
            {"Member": "A", "Role": "sponsor", "Bill": "LTR-1", "Note": "auto-letter LTR-1 sha256=ab"},        # second category, same member x letter
            {"Member": "B", "Role": "original-cosponsor", "Bill": "LTR-1", "Note": "auto-letter LTR-1 sha256=ab"},
            {"Member": "C", "Role": "original-cosponsor", "Bill": "LTR-2", "Note": "Congressional letter, Paul-directed ingestion"},
            {"Member": "D", "Role": "original-cosponsor", "Bill": "H.R.1", "Note": "auto-letter but not a letter row"}]
    assert LT.auto_letter_accounting(rows) == {"rows": 3, "sponsor": 1, "original": 1, "letters": 1}
    assert LT.auto_letter_accounting([]) == {"rows": 0, "sponsor": 0, "original": 0, "letters": 0}


def test_the_csv_wrapper_reads_the_same_count(tmp_path):
    path = tmp_path / "manual_bill_evidence.csv"
    lines = ["Member,Role,Bill,Note", "A,sponsor,LTR-1,auto-letter x", "B,original-cosponsor,LTR-1,auto-letter x", "C,sponsor,LTR-2,hand"]
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    assert LT.auto_letter_accounting_from_csv(str(path)) == {"rows": 2, "sponsor": 1, "original": 1, "letters": 1}
    assert LT.auto_letter_accounting_from_csv(str(tmp_path / "missing.csv")) == {"rows": 0, "sponsor": 0, "original": 0, "letters": 0}


# ---- review ruling 11: every tag-loading site goes through effective_tags WITH the root, the verifier included -----------------------

def test_the_greenlit_primacy_verifier_loads_its_tags_through_effective_tags_with_the_root():
    import ast
    source = (Path(__file__).resolve().parents[2] / "audit" / "verify_greenlit_primacy_integration.py").read_text(encoding="utf-8")
    calls = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "effective_tags"]
    assert len(calls) == 1 and len(calls[0].args) == 3 and ast.unparse(calls[0].args[2]) == "ROOT"
    assert "PF.load_tags(" in ast.unparse(calls[0].args[0]) and "SA.load(ROOT)" in ast.unparse(calls[0].args[1])
