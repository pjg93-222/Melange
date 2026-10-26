"""Promoter for staged sign-on letters (D-263, lane L): Gate C, the CSV append, the tag sidecar, idempotence, fail-closed IO.

Every case runs on a scratch root; manual_bill_evidence.csv is only ever a tmp copy here. No network."""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import sys
from pathlib import Path

import pytest

FEC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FEC))
from collect import collect_signon_letters as C        # noqa: E402
from legislation import letter_tags as LT              # noqa: E402
from legislation import promote_staged_letters as P    # noqa: E402
from members.member_identity import Resolver           # noqa: E402

FX = FEC / "tests" / "collect" / "fixtures" / "letters"
CDFI_URL = "https://democrats-financialservices.house.gov/UploadedFiles/04.21.2025_Ltr.SecCDFI_EO.pdf"
NOW = dt.datetime(2026, 10, 20, 19, 0, 0, tzinfo=dt.timezone.utc)
HAND = dict(Member="Andy Barr", Role="sponsor", Bill="LTR-118-CFPB-SCOTT", Title="t", Sponsor="Tim Scott", Congress="118", Category="CFPB",
            Direction="+1", DecayWeight="0.8", LastAction="Letter sent 2023-04-13 to CFPB Director Chopra", DetailLink="", Summary="s", Note="hand")
BILL = dict(Member="Andy Barr", Role="original-cosponsor", Bill="H.R.1234", Title="A bill", Sponsor="X", Congress="119", Category="CFPB",
            Direction="+1", DecayWeight="1.0", LastAction="Introduced", DetailLink="https://www.congress.gov/x", Summary="s", Note="n")
ACU_SNAPSHOT = {"letters": [{"id": "1", "title": "America's Credit Unions Letter to Treasury on the CDFI Fund",
                             "fieldAdvocacyIssueTypes": [{"label": "Tax, Budget & Bank Attacks"}]}]}


def write_csv(path, rows, columns=C.CSV_COLUMNS):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=columns, lineterminator="\r\n", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


@pytest.fixture
def roster():
    rows = json.loads((FX / "roster_slice.json").read_text(encoding="utf-8"))
    bio = {r["member"]: r["bioguide"] for r in rows}
    return rows, Resolver(list(bio), bio), bio


@pytest.fixture
def make_root(tmp_path, roster):
    def make(acu=True, rows=(HAND, BILL)):
        (tmp_path / "data" / "engine").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data" / "engine" / "congestion.json").write_text(json.dumps(roster[0]), encoding="utf-8")
        write_csv(tmp_path / "manual_bill_evidence.csv", rows)
        if acu:
            (tmp_path / "source_data").mkdir(exist_ok=True)
            (tmp_path / "source_data" / "acu_letters_snapshot_20260725.json").write_text(json.dumps(ACU_SNAPSHOT), encoding="utf-8")
        return tmp_path
    return make


def record(roster, **change):
    rec = C.analyze_letter((FX / "fs_dems_cdfi_letter.pdf").read_bytes(), document_url=CDFI_URL, source_url="https://democrats-financialservices.house.gov/r",
                           source_kind="committee_site", release=None, resolver=roster[1], bio=roster[2], now=NOW)
    return dict(rec, **change)


def stage(root, *recs):
    staging = {}
    for rec in recs:
        C.stage_record(staging, rec, {"letters": [], "ids": set()})
    C.save_staging(str(root / "letters"), staging)


def staged(root):
    return {r["letter_id"]: r for r in map(json.loads, (root / "letters" / "letter_staging.jsonl").read_text(encoding="utf-8").splitlines())}


def go(root, **kw):
    return P.promote(root=str(root), letters_dir=str(root / "letters"), now=NOW, env=kw.pop("env", {}), **kw)


def snapshot(root):
    names = ["manual_bill_evidence.csv", "letters/letter_staging.jsonl", "letters/letter_tags.ndjson", "letters/promotion_receipt.json"]
    return {n: (root / n).read_bytes() if (root / n).exists() else None for n in names}


# ---- Gate C is required ---------------------------------------------------------------------------

def test_exact_without_any_classification_authority_is_never_promoted(make_root, roster):
    root = make_root(acu=False)
    stage(root, record(roster))
    before = snapshot(root)["manual_bill_evidence.csv"]
    receipt = go(root)
    assert receipt["rows_added"] == 0 and receipt["held"] == [{"letter_id": "LTR-119-CDFI-WATERS", "reason": "no_gate_c_authority"}]
    assert (root / "manual_bill_evidence.csv").read_bytes() == before
    assert not list(root.glob("manual_bill_evidence.PRE-LETTERS-*")) and not (root / "letters" / "letter_tags.ndjson").exists()
    assert staged(root)["LTR-119-CDFI-WATERS"]["status"] == "EXACT"


@pytest.mark.parametrize("status", ["OFF_TOPIC", "NOT_EXACT:unaccounted", "DUPLICATE_OF:LTR-119-CDFI-WATERS", "STAGED"])
def test_only_exact_letters_are_considered(make_root, roster, status):
    root = make_root()
    stage(root, record(roster, status=status))
    assert go(root)["rows_added"] == 0 and go(root)["held"] == []


def test_c1_needs_a_category_acu_backing_and_a_one_directional_subject(make_root, roster):
    root = make_root()
    stage(root, record(roster, subject_categories=[]))
    assert go(root)["held"][0]["reason"] == "no_gate_c_authority"
    for cats in (["CFPB"], ["CDFI Fund", "CFPB"]):           # two-sided subjects are not C1
        stage(root, record(roster, subject_categories=cats))
        assert go(root, dry_run=True)["promotable"] == 0
    stage(root, record(roster, subject_categories=["CU Tax Status"]))
    assert go(root, dry_run=True)["promotable"] == 0         # ACU wrote nothing on tax status in this snapshot



# ---- C1 promotion ----------------------------------------------------------------------------------

def test_c1_promotion_appends_roster_rows_only_and_keeps_every_existing_byte(make_root, roster):
    root = make_root()
    stage(root, record(roster))
    before = (root / "manual_bill_evidence.csv").read_bytes()
    receipt = go(root)
    after = (root / "manual_bill_evidence.csv").read_bytes()
    assert after.startswith(before) and receipt["rows_added"] == 89 and receipt["status"] == "PASS"
    appended = list(csv.DictReader((after[len(before):]).decode("utf-8").splitlines(), fieldnames=C.CSV_COLUMNS))
    assert len(appended) == 89 and after.count(b"\r\n") == before.count(b"\r\n") + 89 and after.replace(b"\r\n", b"").count(b"\n") == 0
    waters = [r for r in appended if r["Member"] == "Maxine Waters"][0]
    assert waters["Role"] == "sponsor" and waters["Bill"] == "LTR-119-CDFI-WATERS" and waters["Category"] == "CDFI Fund"
    assert waters["Direction"] == "+1" and waters["DecayWeight"] == "1.0" and waters["Congress"] == "119"
    assert waters["LastAction"].startswith("Letter sent 2025-04-21 to The Honorable Scott Bessent") and waters["DetailLink"] == CDFI_URL
    assert "auto-letter LTR-119-CDFI-WATERS sha256=" in waters["Note"] and "L2:acu-letter" in waters["Note"]
    assert {r["Role"] for r in appended if r["Member"] != "Maxine Waters"} == {"original-cosponsor"}
    assert all(r["Member"] != "Sheila Cherfilus-McCormick" for r in appended)        # off-roster: attested, not written
    (backup,) = root.glob("manual_bill_evidence.PRE-LETTERS-*.csv")
    assert backup.read_bytes() == before


def test_c1_promotion_writes_a_tag_the_chain_can_score_and_the_receipt_accounts_for_it(make_root, roster):
    root = make_root()
    stage(root, record(roster))
    go(root)
    tags = LT.load(str(root))
    tag = tags["LTR-119-CDFI-WATERS|119"]
    assert tag["class"] == "cu_primary" and tag["areas"] == ["CDFI Fund"] and tag["authority"] == "L2:acu-letter"
    assert tag["member_links"] == 89 and tag["roster_role_weight"] == 1.0 + 88 * 0.5 and tag["source_url"] == CDFI_URL
    rec = staged(root)["LTR-119-CDFI-WATERS"]
    assert rec["status"] == "PROMOTED" and rec["classification"]["authority"] == "L2:acu-letter" and rec["classification"]["direction"] == 1
    r = json.loads((root / "letters" / "promotion_receipt.json").read_text(encoding="utf-8"))
    assert r["auto_letter_accounting"] == {"rows": 89, "sponsor": 1, "original": 88, "letters": 1}
    assert r["csv_sha256_before"] != r["csv_sha256_after"] and r["letters"][0]["letter_id"] == "LTR-119-CDFI-WATERS"


def test_a_rerun_is_a_byte_identical_noop_and_keeps_the_cumulative_accounting(make_root, roster):
    root = make_root()
    stage(root, record(roster))
    go(root)
    before = snapshot(root)
    receipt = go(root)
    assert receipt["rows_added"] == 0 and snapshot(root) == before
    assert len(list(root.glob("manual_bill_evidence.PRE-LETTERS-*"))) == 1


def test_rows_already_in_the_csv_are_never_added_twice(make_root, roster):
    root = make_root()
    stage(root, record(roster))
    go(root)
    rows = list(csv.DictReader(open(root / "manual_bill_evidence.csv", encoding="utf-8", newline="")))
    keep = [r for r in rows if r["Bill"] != "LTR-119-CDFI-WATERS" or r["Member"] != "Maxine Waters"]
    write_csv(root / "manual_bill_evidence.csv", keep)           # one row lost: only that row comes back
    staging = staged(root)
    staging["LTR-119-CDFI-WATERS"]["status"] = "EXACT"
    (root / "letters" / "letter_staging.jsonl").write_text("".join(json.dumps(v) + "\n" for v in staging.values()), encoding="utf-8")
    assert go(root)["rows_added"] == 1


def test_a_second_letter_accumulates_in_the_receipt(make_root, roster):
    root = make_root()
    stage(root, record(roster))
    go(root)
    other = record(roster, letter_id="LTR-119-CDFI-FOSTER", sha256="e" * 64, letter_date="2025-07-01", source_url="https://o.house.gov/z",
                   source_urls=["https://o.house.gov/z"], signatories=record(roster)["signatories"][:10], leads=[])
    other["signatories"] = [dict(s, role="original-cosponsor") for s in other["signatories"]]
    staging = staged(root)
    staging[other["letter_id"]] = other
    (root / "letters" / "letter_staging.jsonl").write_text("".join(json.dumps(v) + "\n" for v in staging.values()), encoding="utf-8")
    receipt = go(root)
    assert receipt["rows_added"] == 10 and receipt["auto_letter_accounting"] == {"rows": 99, "sponsor": 1, "original": 98, "letters": 2}


# ---- C2 ---------------------------------------------------------------------------------------------

def c2(roster, sentence):
    return record(roster, letter_id="LTR-119-UNCAT-WATERS", subject_categories=[], body=sentence)


@pytest.mark.parametrize("sentence, direction, outcome", [
    ("We urge you to support H.R. 1234 and move it to the floor.", 1, "promoted"),
    ("We urge you to oppose H.R. 1234.", -1, "adverse_direction_held"),
    ("We urge you to support H.R. 1234 and oppose its companion.", 0, "c2_ambiguous"),
])
def test_c2_inherits_a_named_bills_classification_and_holds_adverse_letters(make_root, roster, sentence, direction, outcome):
    root = make_root()
    stage(root, c2(roster, sentence))
    receipt = go(root)
    if outcome == "promoted":
        assert receipt["rows_added"] == 89
        assert staged(root)["LTR-119-UNCAT-WATERS"]["classification"]["authority"] == "L2:letter-names-classified-bill"
        assert staged(root)["LTR-119-UNCAT-WATERS"]["classification"]["category"] == ["CFPB"]
    else:
        assert receipt["rows_added"] == 0 and receipt["held"][0]["reason"] == outcome


def test_c2_needs_the_bill_to_be_classified_in_the_same_congress(make_root, roster):
    root = make_root()
    stage(root, c2(roster, "We urge you to support H.R. 9999."))
    assert go(root)["rows_added"] == 0


# ---- fail-closed IO ------------------------------------------------------------------------------------

def test_a_malformed_csv_writes_nothing_and_still_exits_zero(make_root, roster):
    root = make_root()
    write_csv(root / "manual_bill_evidence.csv", [HAND], columns=C.CSV_COLUMNS[:-1])
    stage(root, record(roster))
    before = snapshot(root)
    receipt = go(root)
    assert receipt["status"] == "PARTIAL" and receipt["rows_added"] == 0 and snapshot(root) == before
    assert P.main(["--root", str(root), "--letters-dir", str(root / "letters")]) == 0


def test_dry_run_reports_and_writes_nothing(make_root, roster):
    root = make_root()
    stage(root, record(roster))
    before = snapshot(root)
    receipt = go(root, dry_run=True)
    assert receipt["dry_run"] is True and receipt["promotable"] == 1 and receipt["rows_added"] == 89 and snapshot(root) == before
    assert receipt["example_row"]["Bill"] == "LTR-119-CDFI-WATERS"


def test_a_crash_before_the_csv_rename_leaves_a_tag_nobody_serves_and_recovers(make_root, roster, monkeypatch):
    root = make_root()
    stage(root, record(roster))
    before = snapshot(root)
    real = os.replace

    def flaky(src, dst):
        if str(dst).endswith("manual_bill_evidence.csv"):
            raise OSError("disk full")
        return real(src, dst)

    monkeypatch.setattr(P.os, "replace", flaky)
    receipt = go(root)
    assert receipt["status"] == "PARTIAL" and (root / "manual_bill_evidence.csv").read_bytes() == before["manual_bill_evidence.csv"]
    assert LT.load(str(root)) == {} and staged(root)["LTR-119-CDFI-WATERS"]["status"] == "EXACT"
    monkeypatch.setattr(P.os, "replace", real)
    assert go(root)["rows_added"] == 89
    assert len(LT.read_rows(str(root))) == 1 and list(LT.load(str(root))) == ["LTR-119-CDFI-WATERS|119"]


def test_cli_dry_run_prints_counts(make_root, roster, capsys):
    root = make_root()
    stage(root, record(roster))
    assert P.main(["--root", str(root), "--letters-dir", str(root / "letters"), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "promotable 1" in out and "rows 89" in out


def test_a_crash_while_writing_the_sidecar_leaves_the_csv_untouched(make_root, roster, monkeypatch):
    """Order matters: rows must never reach the CSV before their tag exists (primacy raises KeyError on an untagged act)."""
    root = make_root()
    stage(root, record(roster))
    before = (root / "manual_bill_evidence.csv").read_bytes()
    real = os.replace

    def flaky(src, dst):
        if str(dst).endswith("letter_tags.ndjson"):
            raise OSError("disk full")
        return real(src, dst)

    monkeypatch.setattr(P.os, "replace", flaky)
    receipt = go(root)
    assert receipt["status"] == "PARTIAL" and (root / "manual_bill_evidence.csv").read_bytes() == before
    assert not list(root.glob("letters/*.tmp"))            # the temp file of the failed rename is cleaned up


def test_a_record_extracted_under_older_rules_is_held_not_promoted(make_root, roster):
    """The first live dry run staged mis-filed records under v1 rules; staging outlives code, so the rules version is checked."""
    root = make_root()
    stage(root, record(roster, extraction_method="pypdf-6.19.0:signature-block-v1"))
    receipt = go(root)
    assert receipt["rows_added"] == 0 and receipt["held"][0]["reason"] == "stale_extraction_rules"


def test_a_letter_the_bill_rules_exclude_is_held_so_the_desk_and_tags_stay_closed(make_root, roster):
    root = make_root()
    stage(root, record(roster, title="Letter on the George Floyd Justice in Policing Act and the CDFI Fund"))
    receipt = go(root)
    assert receipt["rows_added"] == 0 and receipt["held"][0]["reason"] == "excluded_by_bill_rules"


# ---- lead ruling 1: a C1 letter whose text carries an adverse cue is held, never promoted ----------------------------------------

ADVERSE = ["Congress should repeal the exemption.", "We would eliminate the exemption for large credit unions.",
           "It is time to end the tax exemption.", "Some propose to tax credit unions like banks.",
           "Lawmakers want to subject credit unions to corporate tax.", "We must level the playing field.",
           "Credit unions enjoy an unfair advantage over community banks."]


@pytest.mark.parametrize("sentence", ADVERSE)
def test_a_c1_letter_with_an_adverse_cue_is_held_as_possible_adverse_c1(make_root, roster, sentence):
    root = make_root()
    rec = record(roster)
    stage(root, dict(rec, body=rec["body"] + " " + sentence))
    receipt = go(root)
    assert receipt["rows_added"] == 0 and receipt["held"] == [{"letter_id": "LTR-119-CDFI-WATERS", "reason": "possible_adverse_c1"}]
    held = staged(root)["LTR-119-CDFI-WATERS"]
    assert held["status"] == "EXACT" and held["hold_reason"] == "possible_adverse_c1" and held["classification"] is None   # a hold is not a classification


def test_the_title_is_screened_too_and_the_cue_is_case_insensitive(make_root, roster):
    root = make_root()
    stage(root, record(roster, title="Letter: REPEAL the CDFI Fund?"))
    assert go(root)["held"][0]["reason"] == "possible_adverse_c1"


def test_unfair_advantage_alone_is_not_a_cue_without_credit_union(make_root, roster):
    root = make_root()
    stage(root, record(roster, body="We urge Treasury to protect the CDFI Fund. Rival lenders have an unfair advantage today."))
    assert go(root)["rows_added"] == 89
    root2 = make_root()
    stage(root2, record(roster, body="We urge Treasury to protect the CDFI Fund. Credit unions face an unfair advantage today."))
    assert go(root2, dry_run=True)["held"][0]["reason"] == "possible_adverse_c1"


def test_a_c1_letter_without_any_adverse_cue_is_still_promoted(make_root, roster):
    root = make_root()
    stage(root, record(roster))
    assert go(root)["rows_added"] == 89


def test_the_adverse_screen_is_c1_only_a_c2_letter_is_not_screened_by_it(make_root, roster):
    root = make_root()
    stage(root, c2(roster, "We urge you to support H.R. 1234. Do not repeal the protections it builds on."))
    assert go(root)["rows_added"] == 89


# ---- review ruling 3: C1 fails closed - a positive-advocacy cue is REQUIRED, the adverse list is a second screen -------------------

TAX_ACU = dict(ACU_SNAPSHOT, letters=ACU_SNAPSHOT["letters"] + [
    {"id": "2", "title": "America's Credit Unions Letter on Protecting the Credit Union Tax Exemption",
     "fieldAdvocacyIssueTypes": [{"label": "Tax, Budget & Bank Attacks"}]}])


def c1_letter(roster, body, categories=("CDFI Fund",), **kw):
    return record(roster, subject_categories=list(categories), body=body, **kw)


def with_tax_acu(root):
    (root / "source_data" / "acu_letters_snapshot_20260725.json").write_text(json.dumps(TAX_ACU), encoding="utf-8")


def test_reviewer_probe_one_eliminate_and_defund_is_held(make_root, roster):
    root = make_root()
    stage(root, c1_letter(roster, "We urge Treasury to eliminate the CDFI Fund and defund its grant programs."))
    receipt = go(root)
    assert receipt["rows_added"] == 0 and receipt["held"][0]["reason"] in ("possible_adverse_c1", "c1_direction_unconfirmed")
    assert staged(root)["LTR-119-CDFI-WATERS"]["classification"] is None


def test_reviewer_probe_two_asking_gao_whether_the_exemption_remains_justified_is_held(make_root, roster):
    root = make_root()
    with_tax_acu(root)
    # even with a generic 'support' in the text (a positive cue), the scrutiny phrases hold it
    stage(root, c1_letter(roster, "Credit unions say they support their members. We ask the GAO to examine whether the tax exemption "
                                  "for credit unions remains justified.", categories=("CU Tax Status",)))
    receipt = go(root)
    assert receipt["rows_added"] == 0 and receipt["held"][0]["reason"] == "possible_adverse_c1"
    # and with no positive cue at all, the fail-closed rule holds it
    stage(root, c1_letter(roster, "We write about the credit union tax exemption and ask the GAO to review its cost.", categories=("CU Tax Status",)))
    assert go(root, dry_run=True)["held"][0]["reason"] == "c1_direction_unconfirmed"


def test_a_c1_letter_with_no_positive_advocacy_cue_is_held_as_direction_unconfirmed(make_root, roster):
    root = make_root()
    stage(root, c1_letter(roster, "We write regarding the CDFI Fund and the Treasury budget process for next year."))
    receipt = go(root)
    assert receipt["rows_added"] == 0 and receipt["held"] == [{"letter_id": "LTR-119-CDFI-WATERS", "reason": "c1_direction_unconfirmed"}]
    held = staged(root)["LTR-119-CDFI-WATERS"]
    assert held["status"] == "EXACT" and held["classification"] is None and held["hold_reason"] == "c1_direction_unconfirmed"


@pytest.mark.parametrize("sentence", [
    "We urge you to protect the CDFI Fund.", "Please preserve the CDFI Fund.", "Congress should fully fund the CDFI Fund.",
    "We ask you to maintain the tax exemption for credit unions.", "We strongly support the CDFI Fund.",
    "We oppose any effort to eliminate funding for CDFIs.", "We want to strengthen the CDFI Fund.", "We will defend the CDFI Fund."])
def test_each_positive_advocacy_cue_confirms_the_direction(make_root, roster, sentence):
    root = make_root()
    stage(root, c1_letter(roster, sentence))
    assert go(root, dry_run=True)["promotable"] == 1


def test_the_real_cdfi_letter_still_promotes_because_it_urges_support(make_root, roster):
    root = make_root()
    stage(root, record(roster))
    assert go(root)["rows_added"] == 89


def test_the_positive_cue_is_a_c1_rule_only(make_root, roster):
    root = make_root()
    stage(root, c2(roster, "We urge you to support H.R. 1234."))
    assert go(root)["rows_added"] == 89


# ---- review ruling 4: C2 reads Paul's hand-entered CSV bill rows only ---------------------------------------------------------------

def test_the_sentinel_ledger_is_never_a_c2_authority(make_root, roster):
    """An LLM classification must not pose as L2: a letter urging a ledger-only bill is simply unclassified."""
    root = make_root()
    ledger = {"bills": {"119:hr:7777": {"display": "H.R.7777", "congress": 119}},
              "decisions": {"119:hr:7777": {"categories": [{"category": "CFPB", "direction": 1}]}}}
    (root / "data" / "legislation").mkdir(parents=True, exist_ok=True)
    (root / "data" / "legislation" / "sentinel_admissions.json").write_text(json.dumps(ledger), encoding="utf-8")
    stage(root, c2(roster, "We urge you to support H.R. 7777."))
    receipt = go(root)
    assert receipt["rows_added"] == 0 and receipt["held"][0]["reason"] == "no_gate_c_authority"


def bill_row(bill, **kw):
    return dict(BILL, Bill=bill, **kw)


def test_only_active_include_equivalent_csv_rows_index_a_bill_and_bad_rows_are_skipped_and_counted(make_root, roster):
    rows = [HAND, bill_row("H.R.1234"),
            bill_row("H.R.2001", Direction="0"),                                       # neutral: not include-equivalent
            bill_row("H.R.2002", Direction=""),                                        # blank
            bill_row("H.R.2003", Title="George Floyd Justice in Policing Act"),         # excluded by the bill rules
            bill_row("H.R.2004", Note="cosponsor withdrawn"),                          # withdrawn
            bill_row("H.R.2005", Congress="not-a-number"),                             # malformed: skipped one by one, counted
            bill_row("H.R.2006", Direction="maybe")]                                   # malformed
    root = make_root(rows=rows)
    for number in (2001, 2002, 2003, 2004, 2005, 2006):
        stage(root, c2(roster, "We urge you to support H.R. %d." % number))
        receipt = go(root, dry_run=True)
        assert receipt["promotable"] == 0, number
    stage(root, c2(roster, "We urge you to support H.R. 1234."))
    receipt = go(root, dry_run=True)
    assert receipt["promotable"] == 1 and receipt["c2_rows_skipped"] == 2


def test_hand_rows_that_disagree_on_a_bills_direction_make_c2_ambiguous(make_root, roster):
    root = make_root(rows=[HAND, bill_row("H.R.1234"), bill_row("H.R.1234", Member="Brad Sherman", Direction="-1")])
    stage(root, c2(roster, "We urge you to support H.R. 1234."))
    assert go(root, dry_run=True)["held"][0]["reason"] == "c2_ambiguous"


@pytest.mark.parametrize("sentence", [
    "We do not urge you to support H.R. 1234.",
    "We urge you not to oppose H.R. 1234.",
    "We urge no one to support H.R. 1234.",
    "Nobody should be asked to support H.R. 1234, and we never urge it.",
    "We cannot urge you to support H.R. 1234."])
def test_negation_near_the_verb_makes_c2_ambiguous(make_root, roster, sentence):
    root = make_root()
    stage(root, c2(roster, sentence))
    assert go(root, dry_run=True)["held"][0]["reason"] == "c2_ambiguous"


# ---- review ruling 5: a letter whose signers have all left the roster is held, and the run carries on -------------------------------

def test_a_letter_with_no_roster_rows_is_held_and_does_not_stop_the_other_letters(make_root, roster):
    root = make_root()
    gone = record(roster, letter_id="LTR-119-CDFI-GONE", sha256="a" * 64, source_url="https://o.house.gov/g", source_urls=["https://o.house.gov/g"],
                  signatories=[{"line": "Departed Member", "query": "Departed Member", "member": "Departed Member", "bioguide": "Z000001",
                                "status": "roster", "office": "Member of Congress", "role": "original-cosponsor"}], leads=[])
    stage(root, gone, record(roster))
    receipt = go(root)
    assert {"letter_id": "LTR-119-CDFI-GONE", "reason": "no_roster_rows"} in receipt["held"]
    assert receipt["status"] == "PASS" and receipt["rows_added"] == 89 and staged(root)["LTR-119-CDFI-WATERS"]["status"] == "PROMOTED"
    assert staged(root)["LTR-119-CDFI-GONE"]["status"] == "EXACT"


# ---- review nit: Gate E is re-checked at promotion (staging is a file anyone can edit or an older rule can have written) ---------

@pytest.mark.parametrize("change, reason", [
    ({"unaccounted_lines": ["Stray Name"]}, "unaccounted"),
    ({"blank_pages": [3]}, "page_without_text_layer"),
    ({"document_url": "https://evil.example.com/a.pdf"}, "host_not_official"),
    ({"stated_count": {"n": 50, "min": False}}, "stated_count_mismatch"),
    ({"letter_date": None}, "no_date")])
def test_gate_e_is_rechecked_at_promotion(make_root, roster, change, reason):
    root = make_root()
    rec = record(roster, **change)
    C.save_staging(str(root / "letters"), {rec["letter_id"]: rec})        # written straight to the file, as an edit or an older rule would
    receipt = go(root)
    assert receipt["rows_added"] == 0 and receipt["held"] == [{"letter_id": "LTR-119-CDFI-WATERS", "reason": "gate_e_failed:" + reason}]


# ---- review nit: no C3 dial and no PROMOTABLE status (C3 stays unbuilt, and is Paul's call) ------------------------------------------

def test_there_is_no_c3_dial_and_the_old_dial_changes_nothing(make_root, roster):
    root = make_root(acu=False)
    stage(root, record(roster))
    receipt = go(root, env={"LETTERS_SENTINEL_CLASSIFY": "1"})
    assert receipt["held"][0]["reason"] == "no_gate_c_authority"
    assert "LETTERS_SENTINEL_CLASSIFY" not in (FEC / "legislation" / "promote_staged_letters.py").read_text(encoding="utf-8")


def test_promotable_is_not_a_status_the_promoter_or_the_collector_knows(make_root, roster):
    root = make_root()
    stage(root, record(roster, status="PROMOTABLE"))
    assert go(root)["rows_added"] == 0 and staged(root)["LTR-119-CDFI-WATERS"]["status"] == "PROMOTABLE"
    for name in ("promote_staged_letters.py",):
        assert "PROMOTABLE" not in (FEC / "legislation" / name).read_text(encoding="utf-8")
    assert "PROMOTABLE" not in (FEC / "collect" / "collect_signon_letters.py").read_text(encoding="utf-8")


# ---- review ruling 6: the accounting is DERIVED from the CSV itself, not accumulated in a receipt ---------------------------------

def test_the_accounting_survives_a_lost_receipt_because_it_is_counted_from_the_csv(make_root, roster):
    root = make_root()
    stage(root, record(roster))
    go(root)
    (root / "letters" / "promotion_receipt.json").unlink()
    other = record(roster, letter_id="LTR-119-CDFI-FOSTER", sha256="e" * 64, letter_date="2025-07-01", source_url="https://o.house.gov/z",
                   source_urls=["https://o.house.gov/z"], signatories=record(roster)["signatories"][:10], leads=[])
    staging = staged(root)
    staging[other["letter_id"]] = other
    (root / "letters" / "letter_staging.jsonl").write_text("".join(json.dumps(v) + "\n" for v in staging.values()), encoding="utf-8")
    receipt = go(root)
    assert receipt["rows_added"] == 10 and receipt["auto_letter_accounting"] == {"rows": 99, "sponsor": 1, "original": 98, "letters": 2}
    on_disk = json.loads((root / "letters" / "promotion_receipt.json").read_text(encoding="utf-8"))
    assert on_disk["auto_letter_accounting"] == receipt["auto_letter_accounting"]


def test_a_dry_run_reports_the_accounting_the_csv_would_have(make_root, roster):
    root = make_root()
    stage(root, record(roster))
    receipt = go(root, dry_run=True)
    assert receipt["auto_letter_accounting"] == {"rows": 89, "sponsor": 1, "original": 88, "letters": 1}


def test_a_noop_run_still_reports_the_accounting_of_what_is_in_the_csv(make_root, roster):
    root = make_root()
    stage(root, record(roster))
    go(root)
    assert go(root)["auto_letter_accounting"] == {"rows": 89, "sponsor": 1, "original": 88, "letters": 1}


# ---- review ruling 8 (promoter side): the promoter ALWAYS writes a status file, PARTIAL included ---------------------------------

def status_file(root):
    return json.loads((root / "letters" / "promoter_status.json").read_text(encoding="utf-8"))


def test_a_pass_run_writes_its_status(make_root, roster):
    root = make_root()
    stage(root, record(roster))
    go(root)
    status = status_file(root)
    assert status["status"] == "PASS" and status["rows_added"] == 89 and status["dry_run"] is False
    assert status["run_at"] == "2026-10-20T19:00:00Z" and status["held"] == []


def test_a_partial_run_writes_its_status_with_the_reason_even_though_it_writes_nothing_else(make_root, roster):
    root = make_root()
    write_csv(root / "manual_bill_evidence.csv", [HAND], columns=C.CSV_COLUMNS[:-1])
    stage(root, record(roster))
    before = snapshot(root)
    go(root)
    assert snapshot(root) == before
    status = status_file(root)
    assert status["status"] == "PARTIAL" and "header" in status["error"] and status["rows_added"] == 0


def test_a_noop_and_a_dry_run_also_write_a_fresh_status(make_root, roster):
    root = make_root()
    stage(root, record(roster, subject_categories=[]))
    go(root)
    assert status_file(root)["held"] == [{"letter_id": "LTR-119-CDFI-WATERS", "reason": "no_gate_c_authority"}]
    go(root, dry_run=True)
    assert status_file(root)["dry_run"] is True


def test_the_status_lists_a_bounded_number_of_held_letters_but_counts_all(make_root, roster):
    root = make_root()
    recs = [record(roster, subject_categories=[], letter_id="LTR-119-CDFI-L%02d" % i, sha256="%064x" % i,
                   source_url="https://o.house.gov/%d" % i, source_urls=["https://o.house.gov/%d" % i]) for i in range(30)]
    C.save_staging(str(root / "letters"), {r["letter_id"]: r for r in recs})
    go(root)
    status = status_file(root)
    assert status["held_count"] == 30 and len(status["held"]) == 20


def test_an_unexpected_crash_still_leaves_a_partial_status_and_then_propagates(make_root, roster, monkeypatch):
    root = make_root()
    stage(root, record(roster))
    monkeypatch.setattr(P, "classify", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bug")))
    with pytest.raises(RuntimeError):
        go(root)
    status = status_file(root)
    assert status["status"] == "PARTIAL" and status["error"].startswith("crash:RuntimeError")


# ---- review ruling 12: a lost-update guard - never overwrite a CSV someone else wrote while we were working ---------------------

def test_a_csv_changed_during_the_backup_is_not_overwritten_and_nothing_is_written(make_root, roster, monkeypatch):
    root = make_root()
    stage(root, record(roster))
    real_copy = P.shutil.copyfile

    def copy_then_a_hand_edit(src, dst):
        real_copy(src, dst)
        with open(src, "ab") as handle:
            handle.write(b"Paul,original-cosponsor,H.R.9,t,s,119,CFPB,+1,1.0,x,,s,hand edit\r\n")

    monkeypatch.setattr(P.shutil, "copyfile", copy_then_a_hand_edit)
    receipt = go(root)
    assert receipt["status"] == "PARTIAL" and receipt["error"] == "csv_changed_during_promotion" and receipt["rows_added"] == 0
    assert (root / "manual_bill_evidence.csv").read_bytes().endswith(b"hand edit\r\n")
    assert not (root / "letters" / "letter_tags.ndjson").exists() and staged(root)["LTR-119-CDFI-WATERS"]["status"] == "EXACT"


def test_a_csv_changed_just_before_the_replace_is_not_overwritten(make_root, roster, monkeypatch):
    root = make_root()
    stage(root, record(roster))
    real_write = C._atomic_write

    def write_then_a_hand_edit(path, data):
        real_write(path, data)
        if str(path).endswith("letter_tags.ndjson"):
            with open(root / "manual_bill_evidence.csv", "ab") as handle:
                handle.write(b"Paul,original-cosponsor,H.R.9,t,s,119,CFPB,+1,1.0,x,,s,hand edit\r\n")

    monkeypatch.setattr(C, "_atomic_write", write_then_a_hand_edit)
    receipt = go(root)
    assert receipt["status"] == "PARTIAL" and receipt["error"] == "csv_changed_during_promotion"
    assert (root / "manual_bill_evidence.csv").read_bytes().endswith(b"hand edit\r\n")
    assert LT.load(str(root)) == {}                    # the tag written first is harmless: its letter has no rows
    assert staged(root)["LTR-119-CDFI-WATERS"]["status"] == "EXACT"
    monkeypatch.setattr(C, "_atomic_write", real_write)
    assert go(root)["rows_added"] == 89                # and the next run, on the new bytes, promotes


# ---- review ruling 10: the LETTERS_PROMOTE revert dial (1 = promote, 0 = dry-run only, anything else raises) --------------------------

@pytest.mark.parametrize("value, expected", [(None, True), ("", True), ("1", True), ("0", False)])
def test_the_promote_dial_defaults_on_and_zero_turns_promotion_off(value, expected):
    assert P.promote_dial({} if value is None else {"LETTERS_PROMOTE": value}) is expected


@pytest.mark.parametrize("bad", ["off", "2", "true", "no"])
def test_any_other_dial_value_raises(bad):
    with pytest.raises(ValueError, match="LETTERS_PROMOTE"):
        P.promote_dial({"LETTERS_PROMOTE": bad})


def test_with_the_dial_at_zero_the_promoter_only_dry_runs_even_when_called_for_real(make_root, roster, monkeypatch, capsys):
    root = make_root()
    stage(root, record(roster))
    before = snapshot(root)
    monkeypatch.setenv("LETTERS_PROMOTE", "0")
    assert P.main(["--root", str(root), "--letters-dir", str(root / "letters")]) == 0
    assert snapshot(root) == before and "DRY-RUN" in capsys.readouterr().out
    assert status_file(root)["dry_run"] is True and status_file(root)["rows_added"] == 89     # what it WOULD have added
    monkeypatch.setenv("LETTERS_PROMOTE", "1")
    assert P.main(["--root", str(root), "--letters-dir", str(root / "letters")]) == 0
    assert status_file(root)["dry_run"] is False and (root / "letters" / "promotion_receipt.json").exists()


def test_the_dial_is_catalogued_where_congress_rederive_is():
    repo = Path(__file__).resolve().parents[3]
    docs = (repo / "MATHEMATICAL_SPECIFICATION.md", repo / ".claude" / "skills" / "moneyball-config-and-flags" / "SKILL.md")
    missing = [str(doc.relative_to(repo)) for doc in docs if not doc.is_file()]
    if missing:   # the public source export ships neither doc; the private repo does and is checked there
        pytest.skip("dial catalogue docs absent from this checkout: " + ", ".join(missing))
    for doc in docs:
        assert "LETTERS_PROMOTE" in doc.read_text(encoding="utf-8"), doc.name
