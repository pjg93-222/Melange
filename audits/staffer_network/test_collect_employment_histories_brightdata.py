from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

import pytest

import collect_employment_histories_brightdata as collector


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def write_ndjson_gz(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")


def lda_queue_row(lda_id: str, display_name: str) -> dict[str, Any]:
    return {
        "lda_source_person_id": lda_id,
        "display_name": display_name,
        "name_variants": [display_name],
        "covered_position_values": ["Some Covered Position, 2010-2014."],
        "filing_years": [2024, 2025],
    }


def episode_row(lda_id: str, employer_name: str) -> dict[str, Any]:
    return {
        "lda_source_person_id": lda_id,
        "employer_name": employer_name,
        "display_name": "unused",
    }


def staff_directory_payload() -> dict[str, Any]:
    return {
        "Terri Sewell": [
            {"id": "61082", "n": "Hillary Beard", "t": "Chief of Staff", "star": 0},
            {"id": "61117", "n": "Robert Nuttall", "t": "Legislative Director", "star": 0},
        ]
    }


def write_keys_json(path: Path, *, api_key: str = "test-key-123", unlocker_zone: str = "test-zone") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"brightdata": {"api_key": api_key, "unlocker_zone": unlocker_zone}}),
        encoding="utf-8",
    )


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise collector.requests.HTTPError(f"status {self.status_code}")

    def json(self) -> Any:
        return self._payload


def forbid_http(monkeypatch: pytest.MonkeyPatch) -> dict[str, list]:
    """Install requests.post/get stand-ins that fail the test if called at all.

    The returned dict stays empty for the lifetime of the test; asserting it
    is still ``{"post": [], "get": []}`` at the end documents intent, but the
    stand-ins below already fail loudly (via AssertionError) the instant
    either function is invoked, so a silent no-op call can never slip through.
    """
    calls: dict[str, list] = {"post": [], "get": []}

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(f"unexpected HTTP call: args={args} kwargs={kwargs}")

    monkeypatch.setattr(collector.requests, "post", fail)
    monkeypatch.setattr(collector.requests, "get", fail)
    return calls


def install_http_mocks(
    monkeypatch: pytest.MonkeyPatch,
    *,
    trigger_snapshot_ids: list[str],
    snapshots: dict[str, list[dict[str, Any]]],
    progress_status: str = "ready",
) -> dict[str, list]:
    calls: dict[str, list] = {"post": [], "get": []}
    remaining_ids = list(trigger_snapshot_ids)

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        calls["post"].append((url, kwargs))
        assert url == collector.TRIGGER_URL
        snapshot_id = remaining_ids.pop(0)
        return FakeResponse({"snapshot_id": snapshot_id})

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls["get"].append((url, kwargs))
        if "/datasets/v3/progress/" in url:
            return FakeResponse({"status": progress_status})
        if "/datasets/v3/snapshot/" in url:
            snapshot_id = url.rsplit("/", 1)[-1]
            return FakeResponse(snapshots.get(snapshot_id, []))
        raise AssertionError(f"unexpected GET {url}")

    monkeypatch.setattr(collector.requests, "post", fake_post)
    monkeypatch.setattr(collector.requests, "get", fake_get)
    return calls


def make_args(argv: list[str]) -> Any:
    return collector.resolve_paths(collector.build_arg_parser().parse_args(argv))


def base_argv(tmp_path: Path, *, mode: str, extra: list[str] | None = None) -> list[str]:
    argv = [
        "--live-root", str(tmp_path / "unused_live"),
        "--appdata-root", str(tmp_path / "unused_appdata"),
        "--output-root", str(tmp_path / "output"),
        "--glassbox-events-dir", str(tmp_path / "glassbox"),
        "--keys-json", str(tmp_path / "keys.json"),
        "--mode", mode,
        "--dataset-id-profile", "gd_test_profile",
        "--dataset-id-search", "gd_test_search",
        "--assumed-price-per-record", "0.0",
    ]
    if extra:
        argv.extend(extra)
    return argv


def find_all_values(value: Any) -> list[Any]:
    """Flatten a JSON-like structure into a list of every leaf/key encountered."""
    out: list[Any] = []
    if isinstance(value, dict):
        for k, v in value.items():
            out.append(k)
            out.extend(find_all_values(v))
    elif isinstance(value, list):
        for item in value:
            out.extend(find_all_values(item))
    else:
        out.append(value)
    return out


# ---------------------------------------------------------------------------
# Queue building
# ---------------------------------------------------------------------------


def test_build_lda_queue_joins_registrant_employer_hints(tmp_path: Path) -> None:
    queue_path = tmp_path / "employment_lookup_queue.ndjson.gz"
    episodes_path = tmp_path / "episodes.ndjson.gz"
    write_ndjson_gz(
        queue_path,
        [
            lda_queue_row("lda:lobbyist:1", "JANE ACME"),
            lda_queue_row("lda:lobbyist:2", "NO HINT PERSON"),
        ],
    )
    write_ndjson_gz(
        episodes_path,
        [
            episode_row("lda:lobbyist:1", "ACME WIDGETS, LLC"),
            episode_row("lda:lobbyist:1", "Beltway Strategies Group"),
        ],
    )

    registrant_map = collector.load_registrant_employer_map(episodes_path)
    people = collector.build_lda_queue(queue_path, registrant_map)

    assert len(people) == 2
    jane = next(p for p in people if p.lda_source_person_id == "lda:lobbyist:1")
    nohint = next(p for p in people if p.lda_source_person_id == "lda:lobbyist:2")

    # "LLC" and "Group" are stopwords and must be filtered out of the hints.
    assert set(jane.discovery_hints) == {"acme", "widgets", "beltway", "strategies"}
    assert jane.subject_kind == "lda_lobbyist"
    assert jane.quorum_staff_id is None
    assert nohint.discovery_hints == ()


def test_build_staffer_queue_uses_member_surname_hint(tmp_path: Path) -> None:
    staff_path = tmp_path / "staff_directory.json"
    staff_path.write_text(json.dumps(staff_directory_payload()), encoding="utf-8")

    people = collector.build_staffer_queue(staff_path)

    assert len(people) == 2
    beard = next(p for p in people if p.quorum_staff_id == "61082")
    assert beard.subject_kind == "current_staffer"
    assert beard.lda_source_person_id is None
    assert beard.discovery_hints == ("sewell",)
    assert beard.member_office == "Terri Sewell"
    assert beard.title == "Chief of Staff"


def test_build_queue_both_combines_lda_and_staffdir(tmp_path: Path) -> None:
    queue_path = tmp_path / "appdata" / "employment-lookup" / "generation-20260831T050000Z" / "employment_lookup_queue.ndjson.gz"
    episodes_path = tmp_path / "live" / "audits" / "staffer_network" / "lda_registrant_employment_20260831" / "lda_registrant_employment_episodes.ndjson.gz"
    staff_path = tmp_path / "live" / "data" / "members" / "staff_directory.json"
    write_ndjson_gz(queue_path, [lda_queue_row("lda:lobbyist:1", "JANE ACME")])
    write_ndjson_gz(episodes_path, [episode_row("lda:lobbyist:1", "ACME WIDGETS")])
    staff_path.parent.mkdir(parents=True, exist_ok=True)
    staff_path.write_text(json.dumps(staff_directory_payload()), encoding="utf-8")

    args = make_args(
        [
            "--queue", "both",
            "--live-root", str(tmp_path / "live"),
            "--appdata-root", str(tmp_path / "appdata"),
            "--output-root", str(tmp_path / "output"),
        ]
    )
    people = collector.build_queue(args)
    kinds = sorted(p.subject_kind for p in people)
    assert kinds == ["current_staffer", "current_staffer", "lda_lobbyist"]


# ---------------------------------------------------------------------------
# Identity discipline
# ---------------------------------------------------------------------------


def make_person(hints: tuple[str, ...] = ("acme",)) -> collector.QueuePerson:
    return collector.QueuePerson(
        subject_kind="lda_lobbyist",
        lda_source_person_id="lda:lobbyist:1",
        quorum_staff_id=None,
        display_name="Jane Acme",
        discovery_hints=hints,
    )


def test_evaluate_candidates_accepts_unique_name_and_token_match() -> None:
    person = make_person()
    records = [
        {
            "name": "Jane Acme",
            "url": "https://www.linkedin.com/in/jane-acme/",
            "experience": [{"company": "Acme Widgets", "title": "Director"}],
        },
        {
            "name": "John Someone",
            "url": "https://www.linkedin.com/in/john-someone/",
            "experience": [{"company": "Acme Widgets", "title": "Engineer"}],
        },
    ]
    result = collector.evaluate_candidates(person, records)
    assert result.status == "ACCEPTED"
    assert result.record["url"] == "https://www.linkedin.com/in/jane-acme/"
    assert result.matched_tokens == ["acme"]


def test_evaluate_candidates_collision_blocks_fetch() -> None:
    person = make_person()
    records = [
        {
            "name": "Jane Acme",
            "url": "https://www.linkedin.com/in/jane-acme-one/",
            "experience": [{"company": "Acme Widgets", "title": "Director"}],
        },
        {
            "name": "Jane Acme",
            "url": "https://www.linkedin.com/in/jane-acme-two/",
            "experience": [{"company": "Acme Consulting", "title": "Partner"}],
        },
    ]
    result = collector.evaluate_candidates(person, records)
    assert result.status == "NAME_COLLISION"
    assert result.record is None
    assert result.matched_tokens == []


def test_evaluate_candidates_no_unique_candidate_without_token_support() -> None:
    person = make_person()
    records = [
        {
            "name": "Jane Acme",
            "url": "https://www.linkedin.com/in/jane-acme/",
            "experience": [{"company": "Unrelated Corp", "title": "Manager"}],
        }
    ]
    result = collector.evaluate_candidates(person, records)
    assert result.status == "NO_UNIQUE_CANDIDATE"
    assert result.reason == "NO_TOKEN_SUPPORT"
    assert result.record is None


def test_evaluate_candidates_not_found_when_no_name_match() -> None:
    person = make_person()
    records = [
        {
            "name": "Someone Else",
            "url": "https://www.linkedin.com/in/someone-else/",
            "experience": [{"company": "Acme Widgets", "title": "Director"}],
        }
    ]
    result = collector.evaluate_candidates(person, records)
    assert result.status == "NO_UNIQUE_CANDIDATE"
    assert result.reason == "NOT_FOUND"


def test_evaluate_candidates_never_accepts_without_discovery_hints() -> None:
    person = make_person(hints=())
    records = [{"name": "Jane Acme", "url": "https://www.linkedin.com/in/jane-acme/"}]
    result = collector.evaluate_candidates(person, records)
    assert result.status == "NO_UNIQUE_CANDIDATE"


# ---------------------------------------------------------------------------
# Mapping / precision / stripping
# ---------------------------------------------------------------------------


def test_build_evidence_row_maps_fields_and_strips_contact_info() -> None:
    person = make_person()
    profile = {
        "url": "https://www.linkedin.com/in/jane-acme/",
        "name": "Jane Acme",
        "email": "jane@example.com",
        "phone": "555-1234",
        "connections": 500,
        "followers": 900,
        "profile_pic": "https://example.com/pic.jpg",
        "posts": [{"text": "hello world"}],
        "about": "A long personal summary that should never be stored.",
        "experience": [
            {
                "company": "Acme Widgets",
                "title": "Director",
                "location": "Washington, DC",
                "start_date": "Jan 2020",
                "end_date": "Present",
                "description": "Led the government affairs team.",
            }
        ],
        "education": [
            {
                "institution": "State University",
                "degree": "B.A.",
                "field_of_study": "Political Science",
                "start_year": 2005,
                "end_year": 2009,
            }
        ],
    }
    row = collector.build_evidence_row(
        person, profile, "gd_profile", "snap-1", "2026-09-02", ["acme"]
    )

    assert row["schema_id"] == collector.SCHEMA_ROW
    assert row["subject_kind"] == "lda_lobbyist"
    assert row["profile_url"] == "https://www.linkedin.com/in/jane-acme/"
    assert row["dataset_id"] == "gd_profile"
    assert row["snapshot_id"] == "snap-1"
    assert row["identity_status"] == "REVIEW_REQUIRED"
    assert row["identity_support"] == ["acme"]
    assert row["canonical_identity_decision"] == "NOT_ADJUDICATED"
    assert row["canonical_employment_promoted"] is False
    assert row["canonical_eligible"] is False
    assert row["privacy_class"] == "restricted-machine-local"

    assert len(row["employment"]) == 1
    exp = row["employment"][0]
    assert exp["employer_raw"] == "Acme Widgets"
    assert exp["title_raw"] == "Director"
    assert exp["location_raw"] == "Washington, DC"
    assert exp["current"] is True
    assert exp["end"] is None
    assert exp["start"] == {"year": 2020, "month": 1}
    assert exp["precision"] == "month"
    assert exp["description_present"] is True

    assert len(row["education"]) == 1
    edu = row["education"][0]
    assert edu["institution_raw"] == "State University"
    assert edu["degree_raw"] == "B.A."
    assert edu["field_raw"] == "Political Science"
    assert edu["start_year"] == 2005
    assert edu["end_year"] == 2009

    # NEVER store description text, contact fields, photos, posts, or summaries.
    flat = find_all_values(row)
    assert "Led the government affairs team." not in flat
    assert "jane@example.com" not in flat
    assert "555-1234" not in flat
    assert "https://example.com/pic.jpg" not in flat
    assert "A long personal summary that should never be stored." not in flat
    for forbidden_key in (
        "email", "phone", "connections", "followers", "profile_pic", "posts",
        "about", "description",
    ):
        assert forbidden_key not in flat


def test_precision_assignment_month_year_none_and_current() -> None:
    month_level = collector.map_experience_entry(
        {"company": "Acme", "title": "Analyst", "start_date": "Jan 2020", "end_date": "Present"}
    )
    assert month_level["precision"] == "month"
    assert month_level["current"] is True
    assert month_level["end"] is None
    assert month_level["start"] == {"year": 2020, "month": 1}

    year_level = collector.map_experience_entry(
        {"company": "Acme", "title": "Director", "start_date": "2015", "end_date": "2018"}
    )
    assert year_level["precision"] == "year"
    assert year_level["current"] is False
    assert year_level["end"] == {"year": 2018, "month": None}

    none_level = collector.map_experience_entry(
        {"company": "Acme", "title": "VP", "start_date": "unparseable", "end_date": "also unparseable"}
    )
    assert none_level["precision"] == "none"
    assert none_level["current"] is False
    assert none_level["start"] is None
    assert none_level["end"] is None

    explicit_current = collector.map_experience_entry(
        {"company": "Acme", "title": "SVP", "start_date": "2019", "end_date": "2021", "current": True}
    )
    assert explicit_current["current"] is True
    assert explicit_current["end"] is None


# ---------------------------------------------------------------------------
# Anti-promotion tripwire
# ---------------------------------------------------------------------------


def test_assert_unpromoted_tripwire() -> None:
    good_row = {
        "canonical_employment_promoted": False,
        "canonical_identity_promoted": False,
        "canonical_identity_decision": "NOT_ADJUDICATED",
        "complete_lifetime_employment_asserted": False,
    }
    collector.assert_unpromoted(good_row, "good")  # must not raise

    for bad_field, bad_value in (
        ("canonical_employment_promoted", True),
        ("canonical_identity_promoted", True),
        ("complete_lifetime_employment_asserted", True),
        ("canonical_identity_decision", "ADJUDICATED"),
    ):
        tampered = dict(good_row)
        tampered[bad_field] = bad_value
        with pytest.raises(collector.GateFailure):
            collector.assert_unpromoted(tampered, "tampered")


def test_build_evidence_row_always_passes_its_own_tripwire() -> None:
    person = make_person()
    profile = {"url": "https://www.linkedin.com/in/jane-acme/", "name": "Jane Acme"}
    row = collector.build_evidence_row(person, profile, "gd_profile", "snap-1", "2026-09-02", [])
    collector.assert_unpromoted(row, "row")  # already asserted inside; re-check is harmless


# ---------------------------------------------------------------------------
# Cost cap
# ---------------------------------------------------------------------------


def test_check_cost_cap_raises_when_estimate_exceeds_max() -> None:
    with pytest.raises(collector.CostCapExceeded):
        collector.check_cost_cap(
            num_people=1, price_search=100.0, price_profile=100.0, max_cost_usd=25.0
        )


def test_check_cost_cap_allows_estimate_under_max() -> None:
    estimate = collector.check_cost_cap(
        num_people=1, price_search=0.001, price_profile=0.001, max_cost_usd=25.0
    )
    assert estimate["estimated_cost_usd"] == pytest.approx(0.002)
    assert estimate["estimated_records"] == 2


def test_run_aborts_before_any_http_call_when_cost_cap_exceeded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue_path = tmp_path / "queue.ndjson.gz"
    write_ndjson_gz(queue_path, [lda_queue_row("lda:lobbyist:1", "JANE ACME")])
    write_keys_json(tmp_path / "keys.json")
    calls = forbid_http(monkeypatch)

    # base_argv() ends with ["--assumed-price-per-record", "0.0"]; drop the "0.0"
    # and substitute a price high enough that even 1 person exceeds the default
    # --max-cost-usd of 25.0.
    args = make_args(
        base_argv(tmp_path, mode="sample")[:-1]
        + ["1000.0"]
        + ["--employment-lookup-queue-path", str(queue_path)]
        + ["--staff-directory-path", str(tmp_path / "missing_staff.json")]
        + ["--sample-size", "1"]
    )
    run_id = "run-test-cost-cap"

    with pytest.raises(collector.CostCapExceeded):
        collector.run(args, run_id)

    assert calls["post"] == []
    assert calls["get"] == []


# ---------------------------------------------------------------------------
# Dry-run: zero HTTP calls
# ---------------------------------------------------------------------------


def test_dry_run_performs_zero_http_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue_path = tmp_path / "queue.ndjson.gz"
    episodes_path = tmp_path / "episodes.ndjson.gz"
    staff_path = tmp_path / "staff_directory.json"
    write_ndjson_gz(queue_path, [lda_queue_row("lda:lobbyist:1", "JANE ACME")])
    write_ndjson_gz(episodes_path, [episode_row("lda:lobbyist:1", "ACME WIDGETS")])
    staff_path.write_text(json.dumps(staff_directory_payload()), encoding="utf-8")
    calls = forbid_http(monkeypatch)

    args = make_args(
        base_argv(tmp_path, mode="dry-run")
        + [
            "--queue", "both",
            "--employment-lookup-queue-path", str(queue_path),
            "--lda-registrant-episodes-path", str(episodes_path),
            "--staff-directory-path", str(staff_path),
        ]
    )
    run_id = "run-test-dry-run"
    result = collector.run(args, run_id)

    assert calls["post"] == []
    assert calls["get"] == []
    assert result["mode"] == "dry-run"
    assert result["queue_counts"]["total"] == 3
    assert result["queue_counts"]["lda_lobbyist"] == 1
    assert result["queue_counts"]["current_staffer"] == 2
    assert result["discovery_hint_coverage"]["lda_lobbyist_with_hint"] == 1
    assert result["discovery_hint_coverage"]["current_staffer_with_hint"] == 2
    plan_path = Path(result["plan_path"])
    assert plan_path.is_file()
    assert json.loads(plan_path.read_text(encoding="utf-8"))["schema_id"] == collector.SCHEMA_PLAN


def test_main_dry_run_zero_http_calls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    queue_path = tmp_path / "queue.ndjson.gz"
    write_ndjson_gz(queue_path, [lda_queue_row("lda:lobbyist:1", "JANE ACME")])
    calls = forbid_http(monkeypatch)

    argv = base_argv(tmp_path, mode="dry-run") + [
        "--queue", "lda",
        "--employment-lookup-queue-path", str(queue_path),
    ]
    exit_code = collector.main(argv)

    assert exit_code == 0
    assert calls["post"] == []
    assert calls["get"] == []
    events = list((tmp_path / "glassbox").glob("evt-*.json"))
    assert len(events) == 2  # run.start + run.finish
    kinds = {json.loads(p.read_text(encoding="utf-8"))["kind"] for p in events}
    assert kinds == {"run.start", "run.finish"}


# ---------------------------------------------------------------------------
# Resume skips completed batches
# ---------------------------------------------------------------------------


def test_resume_skips_completed_batches_with_zero_http_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue_path = tmp_path / "queue.ndjson.gz"
    write_ndjson_gz(queue_path, [lda_queue_row("lda:lobbyist:1", "JANE ACME")])
    write_keys_json(tmp_path / "keys.json")

    person = collector.QueuePerson(
        subject_kind="lda_lobbyist",
        lda_source_person_id="lda:lobbyist:1",
        quorum_staff_id=None,
        display_name="JANE ACME",
        discovery_hints=("acme",),
    )
    key = collector.person_key(person)
    profile = {
        "url": "https://www.linkedin.com/in/jane-acme/",
        "name": "JANE ACME",
        "experience": [{"company": "Acme Widgets", "title": "Director", "start_date": "2020", "end_date": "2022"}],
        "education": [],
    }
    evidence_row = collector.build_evidence_row(
        person, profile, "gd_test_profile", "snap-cached-profile", "2026-01-01", ["acme"]
    )

    manifest = {
        "schema_id": collector.SCHEMA_MANIFEST,
        "batches": {
            collector.batch_id_for("discovery", [key]): {
                "cost_usd": None,
                "dataset_id": "gd_test_search",
                "person_keys": [key],
                "record_count": 1,
                "snapshot_id": "snap-cached-search",
                "stage": "discovery",
                "status": "FETCHED",
            },
            collector.batch_id_for("profile", [key]): {
                "cost_usd": None,
                "dataset_id": "gd_test_profile",
                "person_keys": [key],
                "record_count": 1,
                "snapshot_id": "snap-cached-profile",
                "stage": "profile",
                "status": "FETCHED",
            },
        },
        "people": {
            key: {
                "subject_kind": "lda_lobbyist",
                "lda_source_person_id": "lda:lobbyist:1",
                "quorum_staff_id": None,
                "display_name": "JANE ACME",
                "discovery_status": "ACCEPTED",
                "discovery_reason": None,
                "candidate_count": 1,
                "matched_tokens": ["acme"],
                "profile_url": "https://www.linkedin.com/in/jane-acme/",
                "profile_status": "FETCHED",
                "evidence_row": evidence_row,
            }
        },
    }
    output_root = tmp_path / "output"
    output_root.mkdir(parents=True, exist_ok=True)
    collector.save_manifest(output_root / "manifest.json", manifest)

    calls = forbid_http(monkeypatch)
    args = make_args(
        base_argv(tmp_path, mode="sample")
        + [
            "--employment-lookup-queue-path", str(queue_path),
            "--staff-directory-path", str(tmp_path / "missing_staff.json"),
            "--resume",
        ]
    )
    result = collector.run(args, "run-test-resume")

    assert calls["post"] == []
    assert calls["get"] == []
    assert result["profiles_fetched"] == 1
    assert result["discovery_outcomes"]["accepted"] == 1
    output_path = Path(result["output_path"])
    rows = list(collector.read_ndjson_gz(output_path))
    assert len(rows) == 1
    assert rows[0]["profile_url"] == "https://www.linkedin.com/in/jane-acme/"


# ---------------------------------------------------------------------------
# End-to-end sample mode with fully mocked HTTP
# ---------------------------------------------------------------------------


def test_sample_mode_end_to_end_writes_expected_row(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    queue_path = tmp_path / "queue.ndjson.gz"
    episodes_path = tmp_path / "episodes.ndjson.gz"
    write_ndjson_gz(queue_path, [lda_queue_row("lda:lobbyist:1", "Jane Acme")])
    write_ndjson_gz(episodes_path, [episode_row("lda:lobbyist:1", "Acme Widgets")])
    write_keys_json(tmp_path / "keys.json")

    search_record = {
        "name": "Jane Acme",
        "url": "https://www.linkedin.com/in/jane-acme/",
        "experience": [{"company": "Acme Widgets", "title": "Director"}],
    }
    profile_record = {
        "url": "https://www.linkedin.com/in/jane-acme/",
        "name": "Jane Acme",
        "email": "jane@example.com",
        "connections": 500,
        "experience": [
            {
                "company": "Acme Widgets",
                "title": "Director",
                "start_date": "Jan 2020",
                "end_date": "Present",
                "description": "secret sauce",
            }
        ],
        "education": [
            {"institution": "State University", "degree": "BA", "field_of_study": "Political Science",
             "start_year": 2005, "end_year": 2009}
        ],
    }
    calls = install_http_mocks(
        monkeypatch,
        trigger_snapshot_ids=["snap-search-1", "snap-profile-1"],
        snapshots={"snap-search-1": [search_record], "snap-profile-1": [profile_record]},
    )

    args = make_args(
        base_argv(tmp_path, mode="sample")
        + [
            "--employment-lookup-queue-path", str(queue_path),
            "--lda-registrant-episodes-path", str(episodes_path),
            "--staff-directory-path", str(tmp_path / "missing_staff.json"),
            "--sample-size", "5",
        ]
    )
    result = collector.run(args, "run-test-sample")

    assert len(calls["post"]) == 2
    assert len(calls["get"]) == 4  # 2x progress + 2x snapshot

    assert result["discovery_outcomes"] == {
        "accepted": 1, "no_unique_candidate": 0, "name_collision": 0, "not_found": 0,
    }
    assert result["profiles_fetched"] == 1
    assert result["employment_rows"] == 1
    assert result["education_rows"] == 1
    assert result["precision_distribution"] == {"month": 1}

    output_path = Path(result["output_path"])
    rows = list(collector.read_ndjson_gz(output_path))
    assert len(rows) == 1
    row = rows[0]
    assert row["profile_url"] == "https://www.linkedin.com/in/jane-acme/"
    assert row["employment"][0]["current"] is True
    assert row["employment"][0]["end"] is None
    flat = find_all_values(row)
    assert "jane@example.com" not in flat
    assert "secret sauce" not in flat

    receipt_path = Path(result["receipt_path"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["notice"] == collector.NOTICE_SENTENCE
    assert receipt["canonical_employment_promotions"] == 0
    assert receipt["canonical_identity_promotions"] == 0


# ---------------------------------------------------------------------------
# Dataset id / key gating
# ---------------------------------------------------------------------------


def test_resolve_dataset_ids_refuses_to_guess(tmp_path: Path) -> None:
    args = make_args(
        [
            "--live-root", str(tmp_path / "live"),
            "--appdata-root", str(tmp_path / "appdata"),
            "--output-root", str(tmp_path / "output"),
            "--mode", "sample",
        ]
    )
    with pytest.raises(collector.GateFailure, match="UNKNOWN_DATASET_ID"):
        collector.resolve_dataset_ids(args)


def test_run_requires_api_key_for_sample_mode(tmp_path: Path) -> None:
    queue_path = tmp_path / "queue.ndjson.gz"
    write_ndjson_gz(queue_path, [lda_queue_row("lda:lobbyist:1", "JANE ACME")])
    args = make_args(
        base_argv(tmp_path, mode="sample")
        + [
            "--employment-lookup-queue-path", str(queue_path),
            "--staff-directory-path", str(tmp_path / "missing_staff.json"),
            "--keys-json", str(tmp_path / "does_not_exist.json"),
        ]
    )
    with pytest.raises(collector.GateFailure, match="no Bright Data API key"):
        collector.run(args, "run-test-no-key")
