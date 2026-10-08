#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthetic-fixture tests for the House person-identity generation.

Every fixture is hand-written, so the expected classification is known before
the builder runs.  The suite covers one case per link_class, the split that
TRUE_COLLISION must produce, the circularity negative control (a row carrying
the ledger's ``shared_employee_flag`` but no printed SHARED EMPLOYEE title must
NOT classify as shared), the promotion tripwire negative control, immutable
generation refusal, twin byte identity, and the input receipt gate.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_house_person_identity as B  # noqa: E402

ATOMS = B.ATOMS_NAME
LINKS = B.LINKS_NAME
RECEIPT = B.RECEIPT_NAME


# ---------------------------------------------------------------------------
# fixture construction
# ---------------------------------------------------------------------------


def observation(
    person_key: str,
    office_key: str,
    quarter: str,
    start: str | None,
    end: str | None,
    *,
    title: str = "STAFF ASSISTANT",
    shared_flag: bool | None = None,
    container_kind: str = "member_office",
    member_bioguide: str | None = None,
) -> dict:
    """One SOD-shaped personnel observation row."""

    return {
        "schema_id": "staffer-network-sod-personnel-observation-v1",
        "person_key": person_key,
        "person_key_family": "SODFAM:" + person_key.split(":", 1)[1].rsplit("|", 1)[0],
        "office_key": office_key,
        "office_raw": office_key.split(":", 1)[-1],
        "quarter": quarter,
        "container_kind": container_kind,
        "member_bioguide": member_bioguide,
        "member_resolution_method": (
            "STRICT_ROSTER_SURNAME_AND_FIRST_NAME"
            if member_bioguide
            else "NOT_A_MEMBER_OFFICE"
        ),
        "title_base": title,
        "title_raw": title,
        "shared_employee_flag": (
            shared_flag if shared_flag is not None else ("SHARED EMPLOYEE" in title)
        ),
        "service_start": start,
        "service_end": end,
        "compensation_class": "BASE",
    }


def write_ledger(root: Path, rows: list[dict], *, status: str = "PASS",
                 break_hash: bool = False) -> Path:
    """Write a minimal but hash-bound ledger generation directory."""

    root.mkdir(parents=True, exist_ok=True)
    path = root / B.LEDGER_OBSERVATIONS_NAME
    raw = path.open("wb")
    stream = gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0)
    for row in rows:
        stream.write(B.canonical_bytes(row))
    stream.close()
    raw.close()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = {
        "schema_id": "staffer-network-house-personnel-ledger-receipt-v1",
        "status": status,
        "rule_version": "fixture",
        "run_id": "fixture",
        "outputs": [
            {
                "path": B.LEDGER_OBSERVATIONS_NAME,
                "role": "personnel_observations",
                "rows": len(rows),
                "bytes": path.stat().st_size,
                "sha256": ("0" * 64) if break_hash else digest,
            }
        ],
    }
    (root / B.LEDGER_RECEIPT_NAME).write_text(
        json.dumps(receipt, sort_keys=True, indent=1), encoding="utf-8"
    )
    return root


def build_receipt(ledger_root: Path, output_root: Path) -> dict:
    code = B.main(
        [
            "--ledger-root", str(ledger_root),
            "--output-root", str(output_root),
            "--run-id", "test",
            "--no-glassbox",
        ]
    )
    assert code == 0, f"builder exited {code}"
    return json.loads((output_root / RECEIPT).read_text(encoding="utf-8"))


def read_ndjson(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


# ---------------------------------------------------------------------------
# the corpus: one name per link_class
# ---------------------------------------------------------------------------

SHARED = "SOD:KAAI|KRYSTAL|C"
MOVER = "SOD:MOYER|ALEXANDRA|M"
COLLIDER = "SOD:BENJAMIN|WILLIAM|C"
SEQUENTIAL = "SOD:PIRSOS|JOHN|"
FLAGGED = "SOD:HARTL|KELLIE|J"
CROSS = "SOD:HOLSTE|ROBERT|L"


def corpus() -> list[dict]:
    rows: list[dict] = []

    # 1. SHARED_EMPLOYEE across three member offices in one quarter, every
    #    multi-office quarter printing the title.  Dates deliberately overlap:
    #    the printed title is what decides, not the calendar.
    for office, bioguide in (
        ("HON:A000001", "A000001"),
        ("HON:B000002", "B000002"),
        ("HON:C000003", "C000003"),
    ):
        rows.append(
            observation(
                SHARED, office, "2020Q4", "2020-10-01", "2020-12-31",
                title="SHARED EMPLOYEE", member_bioguide=bioguide,
            )
        )

    # 2. MID_QUARTER_MOVE: one quarter, two offices, disjoint day ranges.
    rows.append(
        observation(MOVER, "ADMIN:CHIEF ADMIN OFCR OF THE HOUSE", "2021Q2",
                    "2021-04-01", "2021-05-14", container_kind="admin")
    )
    rows.append(
        observation(MOVER, "HON:D000004", "2021Q2", "2021-05-15", "2021-06-30",
                    member_bioguide="D000004")
    )

    # 3. TRUE_COLLISION: one quarter, two committee offices, identical ranges,
    #    no printed shared title.
    rows.append(
        observation(COLLIDER, "COMMITTEE:COMMITTEE ON ENERGY AND COMMERCE", "2021Q2",
                    "2021-04-01", "2021-06-30", container_kind="committee")
    )
    rows.append(
        observation(COLLIDER, "COMMITTEE:COMM ON OVERSIGHT AND REFORM", "2021Q2",
                    "2021-04-01", "2021-06-30", container_kind="committee")
    )

    # 4. SEQUENTIAL_ONLY: two offices, never in the same quarter.
    rows.append(
        observation(SEQUENTIAL, "HON:E000005", "2019Q1", "2019-01-03", "2019-03-31",
                    member_bioguide="E000005")
    )
    rows.append(
        observation(SEQUENTIAL, "HON:F000006", "2019Q3", "2019-07-01", "2019-09-30",
                    member_bioguide="F000006")
    )

    # 5. CIRCULARITY NEGATIVE CONTROL: two offices in one quarter with the
    #    ledger's shared_employee_flag set on every row but NO printed title,
    #    and overlapping days.  The circular field would call this SHARED;
    #    the printed-title rule must call it TRUE_COLLISION.
    rows.append(
        observation(FLAGGED, "HON:G000007", "2022Q1", "2022-01-03", "2022-03-31",
                    shared_flag=True, member_bioguide="G000007")
    )
    rows.append(
        observation(FLAGGED, "HON:H000008", "2022Q1", "2022-01-03", "2022-03-31",
                    shared_flag=True, member_bioguide="H000008")
    )

    # 6. COMMITTEE_AND_MEMBER collision across TWO quarters with different
    #    overlap sizes, so deciding_quarter (largest overlap) and
    #    first_overlap_quarter (earliest) must differ.
    rows.append(
        observation(CROSS, "COMMITTEE:COMMITTEE ON WAYS AND MEANS", "2023Q1",
                    "2023-01-03", "2023-01-12", container_kind="committee")
    )
    rows.append(
        observation(CROSS, "HON:J000010", "2023Q1", "2023-01-03", "2023-03-31",
                    member_bioguide="J000010")
    )
    rows.append(
        observation(CROSS, "COMMITTEE:COMMITTEE ON WAYS AND MEANS", "2023Q3",
                    "2023-07-01", "2023-09-30", container_kind="committee")
    )
    rows.append(
        observation(CROSS, "HON:J000010", "2023Q3", "2023-07-01", "2023-09-30",
                    member_bioguide="J000010")
    )
    return rows


@pytest.fixture(scope="module")
def generation(tmp_path_factory) -> dict:
    base = tmp_path_factory.mktemp("hpi")
    ledger = write_ledger(base / "ledger", corpus())
    output = base / "primary"
    receipt = build_receipt(ledger, output)
    return {
        "base": base,
        "ledger": ledger,
        "output": output,
        "receipt": receipt,
        "atoms": {row["office_person_id"]: row for row in read_ndjson(output / ATOMS)},
        "atoms_by_name": _by_name(read_ndjson(output / ATOMS)),
        "links": read_ndjson(output / LINKS),
    }


def _by_name(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for row in rows:
        out.setdefault(row["person_key"], []).append(row)
    return out


def links_for(generation: dict, person_key: str) -> list[dict]:
    return [row for row in generation["links"] if row["person_key"] == person_key]


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


def test_receipt_passes_and_declares_the_atom(generation):
    receipt = generation["receipt"]
    assert receipt["status"] == "PASS", receipt["failures"]
    assert receipt["promotion_policy"] == "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS"
    assert "office_person_id" in receipt["atom_definition"]
    assert receipt["invariant_checks"]["name_class_equals_pair_aggregate"] is True


def test_atom_is_one_per_office_and_person(generation):
    atoms = generation["atoms"]
    assert len(atoms) == 13
    assert generation["receipt"]["atoms"]["emitted"] == 13
    keys = {(row["person_key"], row["office_key"]) for row in atoms.values()}
    assert len(keys) == 13
    ids = {row["office_person_id"] for row in atoms.values()}
    assert len(ids) == 13


def test_shared_employee_stays_one_person_across_three_offices(generation):
    rows = generation["atoms_by_name"][SHARED]
    assert len(rows) == 3
    assert {row["name_link_class"] for row in rows} == {"SHARED_EMPLOYEE"}
    assert {row["split"] for row in rows} == {False}
    assert rows[0]["name_member_bioguides"] == ["A000001", "B000002", "C000003"]
    assert rows[0]["name_member_bioguide_count"] == 3

    links = links_for(generation, SHARED)
    assert len(links) == 3
    assert {row["link_class"] for row in links} == {"SHARED_EMPLOYEE"}
    assert {row["cross_office_identity"] for row in links} == {"ONE_PERSON_MANY_OFFICES"}
    assert {row["split"] for row in links} == {False}
    assert links[0]["evidence"]["co_quarters"] == ["2020Q4"]
    assert links[0]["evidence"]["co_quarters_with_shared_title"] == ["2020Q4"]
    assert links[0]["evidence"]["shared_title_examples"] == ["SHARED EMPLOYEE"]


def test_mid_quarter_move_is_one_person_with_disjoint_days(generation):
    rows = generation["atoms_by_name"][MOVER]
    assert {row["name_link_class"] for row in rows} == {"MID_QUARTER_MOVE"}
    assert {row["split"] for row in rows} == {False}

    links = links_for(generation, MOVER)
    assert len(links) == 1
    link = links[0]
    assert link["link_class"] == "MID_QUARTER_MOVE"
    assert link["cross_office_identity"] == "ONE_PERSON_SEQUENTIAL_WITHIN_QUARTER"
    assert link["split"] is False
    assert link["split_basis"] is None
    assert link["evidence"]["co_quarters"] == ["2021Q2"]
    assert link["evidence"]["co_quarters_with_shared_title"] == []
    assert link["evidence"]["overlap_days"] == 0
    # 2021-05-14 then 2021-05-15: adjacent, so a zero-day gap and no overlap.
    assert link["evidence"]["min_gap_days"] == 0
    assert link["evidence"]["deciding_quarter"] == "2021Q2"


def test_true_collision_splits_and_is_never_merged(generation):
    rows = generation["atoms_by_name"][COLLIDER]
    assert len(rows) == 2
    assert {row["name_link_class"] for row in rows} == {"TRUE_COLLISION"}
    assert {row["split"] for row in rows} == {True}
    assert {row["split_basis"] for row in rows} == {"DAY_LEVEL_OVERLAP_NO_SHARED_TITLE"}
    # The split is the point: two office-scoped identities, never one.
    assert rows[0]["office_person_id"] != rows[1]["office_person_id"]
    assert {row["split_group_size"] for row in rows} == {2}
    assert {row["canonical_person_id"] for row in rows} == {None}

    links = links_for(generation, COLLIDER)
    assert len(links) == 1
    link = links[0]
    assert link["link_class"] == "TRUE_COLLISION"
    assert link["cross_office_identity"] == "SPLIT_NOT_LINKED"
    assert link["split"] is True
    assert link["split_basis"] == "DAY_LEVEL_OVERLAP_NO_SHARED_TITLE"
    assert link["link_subclass"] == "BOTH_COMMITTEE"
    assert link["evidence"]["overlap_days"] == 91
    assert link["evidence"]["co_quarters_without_shared_title"] == ["2021Q2"]
    assert link["evidence"]["first_overlap_quarter"] == "2021Q2"
    # It must not read as "two different people".
    assert "NOT an assertion" in link["split_note"]
    assert generation["receipt"]["split_policy"]["merges_performed"] == 0


def test_committee_and_member_subclass(generation):
    """The most common collision shape gets its own name, not the residual."""

    links = links_for(generation, CROSS)
    assert len(links) == 1
    link = links[0]
    assert link["link_class"] == "TRUE_COLLISION"
    assert link["link_subclass"] == "COMMITTEE_AND_MEMBER"
    assert link["container_kind_pair"] == "committee|member_office"
    assert link["split"] is True
    # A committee/member pair must never fall through to OTHER.
    assert link["link_subclass"] != "OTHER"


def test_first_overlap_quarter_is_emitted_alongside_the_strongest(generation):
    """Earliest evidence must not be buried behind the max-overlap choice."""

    link = links_for(generation, CROSS)[0]
    evidence = link["evidence"]
    assert evidence["co_quarters"] == ["2023Q1", "2023Q3"]
    assert evidence["co_quarters_without_shared_title"] == ["2023Q1", "2023Q3"]
    # 2023Q1 overlaps 10 days, 2023Q3 overlaps 92: they must differ.
    assert evidence["first_overlap_quarter"] == "2023Q1"
    assert evidence["deciding_quarter"] == "2023Q3"
    assert evidence["overlap_days"] == 92
    assert evidence["max_overlap_days"] == 92
    assert evidence["first_overlap_quarter"] != evidence["deciding_quarter"]


def test_first_overlap_quarter_is_null_off_collision(generation):
    for person in (SHARED, MOVER, SEQUENTIAL):
        for link in links_for(generation, person):
            assert link["link_class"] != "TRUE_COLLISION"
            assert link["evidence"]["first_overlap_quarter"] is None


def test_verification_scope_is_stated_in_the_receipt(generation):
    scope = generation["receipt"]["verification_scope"]
    assert "NOT rule errors" in scope
    assert "acceptance targets" in scope


def test_sequential_move_is_a_candidate_only(generation):
    rows = generation["atoms_by_name"][SEQUENTIAL]
    assert {row["name_link_class"] for row in rows} == {"SEQUENTIAL_ONLY"}
    assert {row["split"] for row in rows} == {False}

    links = links_for(generation, SEQUENTIAL)
    assert len(links) == 1
    link = links[0]
    assert link["link_class"] == "SEQUENTIAL_CANDIDATE"
    assert link["cross_office_identity"] == "CANDIDATE_REVIEW_REQUIRED"
    assert link["review_status"] == "REVIEW_REQUIRED"
    assert link["evidence"]["co_quarters"] == []
    assert link["evidence"]["deciding_quarter"] is None


def test_circular_ledger_flag_is_not_evidence(generation):
    """The negative control: flag set on every row, no printed title."""

    rows = generation["atoms_by_name"][FLAGGED]
    assert {row["ledger_shared_flag_any"] for row in rows} == {True}
    assert {row["ledger_shared_flag_all"] for row in rows} == {True}
    assert {row["shared_title_observed"] for row in rows} == {False}
    # Had the flag been read, this would be SHARED_EMPLOYEE.
    assert {row["name_link_class"] for row in rows} == {"TRUE_COLLISION"}
    assert {row["ledger_shared_flag_circular"] for row in rows} == {True}

    control = generation["receipt"]["circularity_finding"][
        "negative_control_if_flag_were_used"
    ]
    assert control["SHARED_EMPLOYEE"] > generation["receipt"][
        "name_link_class_counts"
    ]["SHARED_EMPLOYEE"]
    assert generation["receipt"]["invariant_checks"][
        "circularity_negative_control_differs"
    ] is True


def test_every_row_is_unpromoted(generation):
    atoms = list(generation["atoms"].values())
    assert B.assert_unpromoted(atoms, "atom") == []
    assert B.assert_unpromoted(generation["links"], "link") == []
    for row in atoms + generation["links"]:
        assert row["identity_status"] == "NAME_SCOPED_TO_OFFICE"
        assert row["review_status"] == "REVIEW_REQUIRED"
        assert row["canonical_eligible"] is False
        assert row["canonical_identity_promoted"] is False
        assert row["canonical_employment_promoted"] is False
        assert row["canonical_person_id"] is None
        assert row["canonical_identity_decision"] == "NOT_ADJUDICATED"


def test_promotion_tripwire_negative_control(generation):
    """A promoted row must be caught; the exemption must stay fail-closed."""

    clean = dict(next(iter(generation["atoms"].values())))
    assert B.unpromoted_failures(clean, "clean") == []

    promoted = dict(clean, canonical_identity_promoted=True)
    assert B.unpromoted_failures(promoted, "x"), "promotion was not caught"

    named = dict(clean, canonical_person_id="person:1")
    assert B.unpromoted_failures(named, "x"), "canonical id was not caught"

    eligible = dict(clean, canonical_eligible=True)
    assert B.unpromoted_failures(eligible, "x"), "eligibility was not caught"

    adjudicated = dict(clean, canonical_identity_decision="SAME_PERSON")
    assert B.unpromoted_failures(adjudicated, "x"), "decision was not caught"

    reviewed = dict(clean, review_status="RESOLVED")
    assert B.unpromoted_failures(reviewed, "x"), "review status was not caught"


def test_promoted_build_fails_status(tmp_path, monkeypatch):
    """End-to-end: if the INV block were ever promoted the receipt goes FAIL."""

    ledger = write_ledger(tmp_path / "ledger", corpus())
    monkeypatch.setattr(
        B, "INV_ATOM", dict(B.INV_ATOM, canonical_identity_promoted=True)
    )
    with pytest.raises(Exception):
        # The committed schema pins canonical_identity_promoted to false, so a
        # promoted row cannot even be written.
        B.IdentityBuild(
            B.parse_args(
                [
                    "--ledger-root", str(ledger),
                    "--output-root", str(tmp_path / "promoted"),
                    "--no-glassbox",
                ]
            )
        ).run()
    assert not (tmp_path / "promoted").exists(), "staging leaked on failure"


def test_twin_build_is_byte_identical(tmp_path):
    ledger = write_ledger(tmp_path / "ledger", corpus())
    first = tmp_path / "primary"
    second = tmp_path / "twin"
    build_receipt(ledger, first)
    build_receipt(ledger, second)
    for name in (ATOMS, LINKS, RECEIPT):
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


def test_immutable_generation_is_refused(tmp_path):
    ledger = write_ledger(tmp_path / "ledger", corpus())
    output = tmp_path / "primary"
    build_receipt(ledger, output)
    code = B.main(
        [
            "--ledger-root", str(ledger),
            "--output-root", str(output),
            "--no-glassbox",
        ]
    )
    assert code == 2


def test_input_receipt_gate(tmp_path):
    failing = write_ledger(tmp_path / "fail", corpus(), status="FAIL")
    assert B.main(
        ["--ledger-root", str(failing), "--output-root", str(tmp_path / "o1"),
         "--no-glassbox"]
    ) == 2
    unbound = write_ledger(tmp_path / "unbound", corpus(), break_hash=True)
    assert B.main(
        ["--ledger-root", str(unbound), "--output-root", str(tmp_path / "o2"),
         "--no-glassbox"]
    ) == 2


def test_acceptance_targets_not_claimed_on_a_fixture(generation):
    targets = generation["receipt"]["acceptance_targets"]
    assert targets["applicable"] is False
    assert targets["deviations"] == []
    assert "do not hash to the pinned v1 ledger" in targets["basis"]


def test_verifier_passes_on_the_fixture_generation(generation, tmp_path):
    twin = generation["base"] / "twin"
    if not twin.exists():
        build_receipt(generation["ledger"], twin)
    verification = tmp_path / "verification"
    result = subprocess.run(
        [
            sys.executable,
            str(HERE / "verify_house_person_identity.py"),
            "--ledger-root", str(generation["ledger"]),
            "--primary-root", str(generation["output"]),
            "--twin-root", str(twin),
            "--output-root", str(verification),
            "--no-glassbox",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(
        (verification / "house_person_identity_verification_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["status"] == "PASS", payload["failures"]
    assert payload["checks"]["twin_byte_identical"] is True
    assert payload["checks"]["independent_classification_agrees"] is True
    assert "NOT rule errors" in payload["verification_scope"]
    assert payload["measured"]["true_collision_subclasses"].get(
        "COMMITTEE_AND_MEMBER"
    ) == 1
