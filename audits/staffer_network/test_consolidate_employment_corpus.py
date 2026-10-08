import json
from pathlib import Path
import sys

import pytest

from audits.staffer_network.consolidate_employment_corpus import (
    canonical_bytes,
    classify_person_id,
    consolidate,
    consolidate_with_accounting,
    consolidation_status,
    main,
    read_rows,
    residual_row,
    validate_receipt,
    write_gzip,
)
from fec.staffer_network.employment_history import employment_episode_digest


def _episode(employer: str, start: str, end: str) -> dict:
    return {
        "employer": employer,
        "title": "Director",
        "start_date": start,
        "end_date": end,
        "source_url": "https://example.org/bio",
    }


def _attestation(episodes: list[dict]) -> dict:
    return {
        "reviewer_kind": "independent-human",
        "reviewer_id": "reviewer:fixture",
        "rationale": "Fixture establishes exhaustive employment coverage.",
        "attested_at": "2026-08-31T12:00:00Z",
        "employment_exhaustive": True,
        "unresolved_employment_gaps": [],
        "adjudication_status": "PASS",
        "attested_episode_digest": employment_episode_digest(episodes),
    }


def test_collected_history_gap_invalidates_base_attestation() -> None:
    episodes = [_episode("Example Org", "2020", "2021")]
    rows = [
        (
            Path("complete.ndjson"),
            {
                "lda_source_person_id": "lda:lobbyist:1",
                "history_completeness": "complete_history",
                "employment_episodes": episodes,
                "history_completeness_attestation": _attestation(episodes),
            },
        ),
        (
            Path("gap.ndjson"),
            {
                "lda_source_person_id": "lda:lobbyist:1",
                "unresolved_history_gaps": ["1999-2004 unaccounted"],
            },
        ),
    ]

    [profile] = consolidate(rows)

    assert profile["employment_completeness"] == "INCOMPLETE"
    assert "UNRESOLVED_EMPLOYMENT_GAPS_REMAIN" in profile["completeness_audit"]["failure_codes"]


def test_attestation_does_not_certify_episodes_merged_from_another_row() -> None:
    certified = [_episode("Example Org", "2020", "2021")]
    additional = [_episode("Other Org", "2022", "2023")]
    rows = [
        (
            Path("complete.ndjson"),
            {
                "lda_source_person_id": "lda:lobbyist:1",
                "history_completeness": "complete_history",
                "employment_episodes": certified,
                "history_completeness_attestation": _attestation(certified),
            },
        ),
        (
            Path("new.ndjson"),
            {
                "lda_source_person_id": "lda:lobbyist:1",
                "employment_episodes": additional,
            },
        ),
    ]

    [profile] = consolidate(rows)

    assert len(profile["employment_episodes"]) == 2
    assert profile["employment_completeness"] == "INCOMPLETE"
    assert "EXHAUSTIVENESS_ATTESTATION_UNBOUND" in profile["completeness_audit"]["failure_codes"]


def test_typed_gap_from_nonbase_row_invalidates_base_attestation() -> None:
    episodes = [_episode("Example Org", "2020", "2021")]
    incomplete_attestation = _attestation(episodes)
    incomplete_attestation["unresolved_employment_gaps"] = [
        "1999-2004 unaccounted"
    ]
    rows = [
        (
            Path("complete.ndjson"),
            {
                "lda_source_person_id": "lda:lobbyist:1",
                "history_completeness": "complete_history",
                "employment_episodes": episodes,
                "history_completeness_attestation": _attestation(episodes),
            },
        ),
        (
            Path("typed-gap.ndjson"),
            {
                "lda_source_person_id": "lda:lobbyist:1",
                "employment_episodes": episodes,
                "history_completeness_attestation": incomplete_attestation,
            },
        ),
    ]

    [profile] = consolidate(rows)

    assert profile["employment_completeness"] == "INCOMPLETE"
    assert "UNRESOLVED_EMPLOYMENT_GAPS_REMAIN" in profile["completeness_audit"]["failure_codes"]


def test_malformed_typed_gap_from_nonbase_row_fails_closed() -> None:
    episodes = [_episode("Example Org", "2020", "2021")]
    malformed_attestation = _attestation(episodes)
    malformed_attestation["unresolved_employment_gaps"] = "unknown"
    rows = [
        (
            Path("complete.ndjson"),
            {
                "lda_source_person_id": "lda:lobbyist:1",
                "history_completeness": "complete_history",
                "employment_episodes": episodes,
                "history_completeness_attestation": _attestation(episodes),
            },
        ),
        (
            Path("malformed-gap.ndjson"),
            {
                "lda_source_person_id": "lda:lobbyist:1",
                "employment_episodes": episodes,
                "history_completeness_attestation": malformed_attestation,
            },
        ),
    ]

    [profile] = consolidate(rows)

    assert profile["employment_completeness"] == "INCOMPLETE"
    assert "UNRESOLVED_EMPLOYMENT_GAPS_INVALID" in profile["completeness_audit"]["failure_codes"]


def test_missing_or_null_typed_gap_field_cannot_be_laundered_to_empty() -> None:
    employment = [_episode("Example Org", "2020", "2021")]
    for replacement in (None, "MISSING"):
        attestation = _attestation(employment)
        if replacement == "MISSING":
            del attestation["unresolved_employment_gaps"]
        else:
            attestation["unresolved_employment_gaps"] = None
        [profile] = consolidate([
            (
                Path("unsafe-attestation.ndjson"),
                {
                    "lda_source_person_id": "lda:lobbyist:1",
                    "employment_episodes": employment,
                    "history_completeness_attestation": attestation,
                },
            ),
        ])
        assert profile["employment_completeness"] == "INCOMPLETE"
        assert "UNRESOLVED_EMPLOYMENT_GAPS_INVALID" in (
            profile["completeness_audit"]["failure_codes"]
        )


def test_blank_gap_and_null_primary_history_fallback_are_preserved() -> None:
    employment = [_episode("Example Org", "2020", "2021")]
    attestation = _attestation(employment)
    attestation["unresolved_employment_gaps"] = ["   "]
    [profile] = consolidate([
        (
            Path("legacy-history.ndjson"),
            {
                "lda_source_person_id": "lda:lobbyist:1",
                "employment_episodes": None,
                "employment_history": employment,
                "history_completeness_attestation": attestation,
            },
        ),
    ])
    assert profile["employment_episodes"] == employment
    assert profile["employment_completeness"] == "INCOMPLETE"
    assert "UNRESOLVED_EMPLOYMENT_GAPS_REMAIN" in (
        profile["completeness_audit"]["failure_codes"]
    )


def test_malformed_legacy_gap_field_cannot_be_laundered_to_empty() -> None:
    employment = [_episode("Example Org", "2020", "2021")]
    [profile] = consolidate([
        (
            Path("malformed-legacy-gap.ndjson"),
            {
                "lda_source_person_id": "lda:lobbyist:1",
                "employment_episodes": employment,
                "history_gaps": "1999-2004 unaccounted",
                "history_completeness_attestation": _attestation(employment),
            },
        ),
    ])
    assert profile["employment_completeness"] == "INCOMPLETE"
    assert "UNRESOLVED_EMPLOYMENT_GAPS_INVALID" in (
        profile["completeness_audit"]["failure_codes"]
    )


def test_unresolved_seen_profile_stays_at_front_of_residual_queue() -> None:
    row = residual_row(
        {
            "lda_source_person_id": "lda:lobbyist:1",
            "display_name": "Example Person",
        },
        1,
        {
            "history_completeness": "unresolved",
            "completeness_audit": {"failure_codes": ["EMPLOYMENT_HISTORY_EMPTY"]},
            "employment_episodes": [],
            "education": [],
        },
    )

    assert row["acquisition_priority"] == 0


def test_all_unresolved_employment_corpus_is_incomplete() -> None:
    profiles, rejected, accounting = consolidate_with_accounting([
        (Path("one.ndjson"), {"lda_source_person_id": "lda:lobbyist:1"}),
        (Path("two.ndjson"), {"lda_source_person_id": "lda:lobbyist:2"}),
    ])

    status, reasons = consolidation_status(profiles, accounting)

    assert rejected == []
    assert len(profiles) == 2
    assert status == "INCOMPLETE"
    assert reasons == ["IDENTIFIED_EMPLOYMENT_NOT_COMPLETE"]


def test_missing_ids_are_preserved_in_unidentified_ledger() -> None:
    profiles, rejected, accounting = consolidate_with_accounting([
        (Path("missing.ndjson"), {"display_name": "No Identifier"}),
        (
            Path("blank.ndjson"),
            {"person_identity": {"lda_source_person_id": "   "}},
        ),
    ])

    assert profiles == []
    assert len(rejected) == 2
    assert {row["rejection_reason"] for row in rejected} == {
        "MISSING_OR_BLANK_PERSON_ID"
    }
    assert accounting["unidentified_input_rows"] == 2
    assert accounting["dropped_input_rows"] == 2


def test_literal_and_whitespace_unresolved_ids_never_merge() -> None:
    rows = [
        (Path("sentinels.ndjson"), {"lda_source_person_id": "UNRESOLVED"}),
        (Path("sentinels.ndjson"), {"lda_source_person_id": " unresolved "}),
    ]

    profiles, rejected, accounting = consolidate_with_accounting(rows)

    assert profiles == []
    assert len(rejected) == 2
    assert all(
        row["rejection_reason"] == "RESERVED_UNRESOLVED_PERSON_ID"
        for row in rejected
    )
    assert [row["source_row_ordinal"] for row in rejected] == [1, 2]
    assert accounting["duplicate_identified_input_rows"] == 0


def test_whitespace_normalized_duplicate_ids_are_counted() -> None:
    profiles, rejected, accounting = consolidate_with_accounting([
        (Path("one.ndjson"), {"lda_source_person_id": " lda:lobbyist:1 "}),
        (
            Path("two.ndjson"),
            {"person_identity": {"lda_source_person_id": "lda:lobbyist:1"}},
        ),
    ])

    assert rejected == []
    assert [profile["lda_source_person_id"] for profile in profiles] == [
        "lda:lobbyist:1"
    ]
    assert profiles[0]["source_row_count"] == 2
    assert accounting["duplicate_identified_input_rows"] == 1
    assert accounting["duplicate_identified_person_ids"] == 1
    assert consolidation_status(profiles, accounting)[0] == "INCOMPLETE"


def test_row_conservation_accounts_for_consumed_and_dropped_rows() -> None:
    rows = [
        (Path("mixed.ndjson"), {"lda_source_person_id": "lda:lobbyist:1"}),
        (Path("mixed.ndjson"), {"display_name": "Missing"}),
        (Path("mixed.ndjson"), {"lda_source_person_id": " UNRESOLVED "}),
        (
            Path("mixed.ndjson"),
            {
                "lda_source_person_id": "lda:lobbyist:2",
                "person_identity": {"lda_source_person_id": "lda:lobbyist:3"},
            },
        ),
    ]

    profiles, rejected, accounting = consolidate_with_accounting(rows)

    assert len(profiles) == 1
    assert len(rejected) == 3
    assert accounting["identified_input_rows"] == 1
    assert accounting["consumed_identified_input_rows"] == 1
    assert accounting["accounted_input_rows"] == 4
    assert accounting["classification_row_conservation_ok"] is True
    assert accounting["identified_row_conservation_ok"] is True
    assert accounting["input_row_conservation_ok"] is True
    assert classify_person_id(rows[-1][1]) == (None, "CONFLICTING_PERSON_IDS")


def test_main_validates_receipt_and_is_byte_deterministic(
    tmp_path: Path, monkeypatch
) -> None:
    fanout_root = tmp_path / "fanout"
    fanout_root.mkdir()
    acquisition_path = (
        fanout_root
        / "legistorm_lda_profile_fanout_fixture_slice_000001_000002.ndjson"
    )
    acquisition_rows = [
        {"lda_source_person_id": "lda:lobbyist:1", "display_name": "One"},
        {"lda_source_person_id": " UNRESOLVED ", "display_name": "Unknown"},
    ]
    acquisition_path.write_bytes(b"".join(map(canonical_bytes, acquisition_rows)))
    queue_path = tmp_path / "queue.ndjson.gz"
    write_gzip(
        queue_path,
        [
            {
                "lda_source_person_id": "lda:lobbyist:1",
                "display_name": "One",
            }
        ],
        key=lambda row: row["lda_source_person_id"],
    )

    output_roots = [tmp_path / "primary", tmp_path / "twin"]
    for output_root in output_roots:
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "consolidate_employment_corpus.py",
                "--fanout-root",
                str(fanout_root),
                "--queue",
                str(queue_path),
                "--output-root",
                str(output_root),
                "--workers",
                "2",
            ],
        )
        assert main() == 0
        receipt = json.loads(
            (output_root / "working_history_corpus_receipt.json").read_text(
                encoding="utf-8"
            )
        )
        validate_receipt(receipt)
        assert receipt["status"] == "INCOMPLETE"
        assert receipt["incomplete_reasons"] == [
            "IDENTIFIED_EMPLOYMENT_NOT_COMPLETE",
            "UNIDENTIFIED_INPUT_ROWS",
        ]
        false_pass = dict(receipt)
        false_pass["status"] = "PASS"
        false_pass["incomplete_reasons"] = []
        with pytest.raises(ValueError, match="receipt evidence"):
            validate_receipt(false_pass)

        row_loss = json.loads(json.dumps(receipt))
        row_loss["row_accounting"]["input_rows"] = 100
        row_loss["input_row_count"] = 100
        row_loss["row_accounting"]["identified_input_rows"] = 100
        row_loss["row_accounting"]["accounted_input_rows"] = 40
        row_loss["row_accounting"]["consumed_identified_input_rows"] = 40
        row_loss["row_accounting"]["classification_row_conservation_ok"] = True
        row_loss["row_accounting"]["identified_row_conservation_ok"] = True
        row_loss["row_accounting"]["input_row_conservation_ok"] = True
        with pytest.raises(ValueError, match="all input rows are accounted"):
            validate_receipt(row_loss)

        false_reasons = json.loads(json.dumps(receipt))
        false_reasons["row_accounting"]["unidentified_reason_counts"] = {
            "CONFLICTING_PERSON_IDS": 500
        }
        with pytest.raises(ValueError, match="unidentified reasons conserve"):
            validate_receipt(false_reasons)

        false_duplicates = json.loads(json.dumps(receipt))
        false_duplicates["row_accounting"]["output_duplicate_person_ids"] = 12
        false_duplicates["row_accounting"]["output_person_ids_unique"] = True
        with pytest.raises(ValueError, match="output duplicate count"):
            validate_receipt(false_duplicates)

        inflated_people = json.loads(json.dumps(receipt))
        inflated_people["processed_people"] = 500
        inflated_people["unresolved_people"] = 500
        inflated_people["identity_verification_queue_rows"] = 500
        inflated_people["queue_rows"] = 500
        inflated_people["residual_incomplete_rows"] = 500
        with pytest.raises(ValueError, match="duplicate rows bridge"):
            validate_receipt(inflated_people)

        false_residual = json.loads(json.dumps(receipt))
        false_residual["residual_incomplete_rows"] = 400
        with pytest.raises(ValueError, match="residual rows equal"):
            validate_receipt(false_residual)
        assert len(read_rows(output_root / "unidentified_input_rows.ndjson.gz")) == 1

    primary_files = {
        path.name: path.read_bytes() for path in output_roots[0].iterdir()
    }
    twin_files = {path.name: path.read_bytes() for path in output_roots[1].iterdir()}
    assert primary_files == twin_files
