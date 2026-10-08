# -*- coding: utf-8 -*-
"""pytest for build_hill_personnel_spine.py / verify_hill_personnel_spine.py.

Every fixture is synthetic and written under ``tmp_path``; no test reads a live
generation, a live ledger or any file in the repository other than the two
scripts under test and the six committed schemas the verifier validates
against.  The cases are the ones the Part C build spec names --

  * shared employee: one person, two memberships, no double count
  * cross-office S2 over non-overlapping sequential spans, against the
    same-period collision that must stay two people
  * a current-staffer link whose name collides inside one member office
    (NAME_COLLISION, never LINKED), against a clean LINKED control
  * the PDF-era / CSV-era boundary at 2015Q4 -> 2016Q1 for one person
  * conservation: every admitted input row lands in exactly one span
  * the anti-promotion tripwire negative control: a row carrying
    ``canonical_employment_promoted: true`` must make the verifier FAIL

-- plus regressions for the two defects found while finishing the lane: payee
keys whose middle initial is ``None`` in one lane and a letter in another are
not orderable as raw triples, and the committed nickname table's on-disk shape
was not one the loader recognised.
"""
from __future__ import annotations

import gzip
import json
import shutil
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_hill_personnel_spine as bs  # noqa: E402
import verify_hill_personnel_spine as vs  # noqa: E402


GENERATED_AT = "2026-09-02T00:00:00Z"
RUN_ID = "run-test-hill-personnel-spine"
EM_DASH = "—"


# ---------------------------------------------------------------------------
# Fixture plumbing
# ---------------------------------------------------------------------------
def write_gz(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")


def read_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def read_generation(root: Path) -> dict:
    payload = {name: read_gz(root / name) for name in bs.PAYLOAD_FILES}
    payload["receipt"] = json.loads(
        (root / bs.RECEIPT_FILE).read_text(encoding="utf-8")
    )
    return payload


def write_roster(directory: Path, people) -> None:
    """``people`` is a sequence of (bioguide, first, last, start_year, end_year)."""

    directory.mkdir(parents=True, exist_ok=True)
    current = [
        {
            "id": {"bioguide": bioguide},
            "name": {"first": first, "last": last, "official_full": f"{first} {last}"},
            "terms": [
                {
                    "type": "rep",
                    "start": f"{start}-01-03",
                    "end": f"{end}-01-03",
                    "state": "XX",
                }
            ],
        }
        for bioguide, first, last, start, end in people
    ]
    (directory / "legislators-current.yaml").write_text(
        yaml.safe_dump(current, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    (directory / "legislators-historical.yaml").write_text(
        yaml.safe_dump([], sort_keys=False), encoding="utf-8"
    )


class World:
    """A synthetic Part C input world under one tmp_path."""

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.ledger: list[dict] = []
        # row id -> the PDF-era candidate id the ledger carries through for that
        # row, which is what the H1 LDA match lane keys on.
        self.candidate_ids: dict[str, str] = {}
        self.senate: list[dict] = []
        self.roster: list[tuple] = []
        self.staff: dict[str, list[dict]] = {}
        self.congestion: dict[str, dict] = {}
        self.h1: list[dict] = []
        self.h2: list[dict] = []
        self.senate_matches: list[dict] = []
        self.part_a: list[dict] = []
        self.registrant: list[dict] = []
        self.nickname: dict | None = None
        # ``--name-standard`` is off by default here for the same reason it is
        # off in the builder: every existing test must keep exercising the
        # unmodified path.
        self.name_standard = False
        self.name_standard_baseline: Path | None = None
        # Ruling B: --name-standard requires a read-only re-key delta report to
        # assert the key-change histogram against, and its absence is a
        # declared failure.  A test that turns the flag on must therefore say
        # what histogram it expects, which is the point: the expected numbers
        # are written in the test, not read back out of the build.
        self.name_standard_delta_report: Path | None = None
        self._ordinal = 0
        self._argv: list[str] | None = None

    # -- rows ---------------------------------------------------------------
    def add_ledger(
        self,
        quarter: str,
        office: str,
        payee: str,
        title: str | None = None,
        amount: str | None = "1000.00",
        **extra,
    ) -> str:
        self._ordinal += 1
        source_file = f"{quarter.lower()}_sod_detail.csv"
        row = {
            "amount": amount,
            "office_raw": office,
            "payee_raw": payee,
            "quarter": quarter,
            "report_period_start": None,
            "source_file": source_file,
            "source_form": "detail_csv",
            "source_row_index": self._ordinal,
            "title_raw": title,
        }
        row.update(extra)
        self.ledger.append(row)
        return f"house-ledger:{source_file}#{self._ordinal}"

    def add_pdf(
        self,
        period: str,
        office: str,
        payee: str,
        title: str | None = None,
        amount: str | None = "1,000.00",
        **extra,
    ) -> str:
        """A 2009Q3-2015Q4 row, INSIDE the ledger.

        From House ledger v3 the PDF era is not a separate lane: the ledger
        carries those rows itself, normalized to the same field names as the CSV
        era and tagged ``source_form: house_gov_single_volume_pdf``, with the
        original candidate file's id carried through in
        ``source_locator.candidate_id``.  This helper builds that shape, so a
        test that adds a PDF-era row is exercising the one lane the builder now
        has rather than a second one it no longer accepts.
        """

        self._ordinal += 1
        candidate_id = f"house-sod-pdf-payroll:{self._ordinal:08d}"
        source_file = "house_sod_payroll_pdf_candidates.ndjson.gz"
        row = {
            "amount": amount,
            "office_raw": office,
            "payee_raw": payee,
            "quarter": period,
            "report_period_start": None,
            "source_file": source_file,
            "source_form": "house_gov_single_volume_pdf",
            "source_locator": {"candidate_id": candidate_id},
            "source_row_index": self._ordinal,
            "title_raw": title,
        }
        row.update(extra)
        self.ledger.append(row)
        row_id = f"house-ledger:{source_file}#{self._ordinal}"
        self.candidate_ids[row_id] = candidate_id
        return row_id

    def add_senate(
        self,
        period_start: str,
        office: str,
        payee: str,
        title: str | None = None,
        amount: str | None = "$1,000.00",
    ) -> str:
        self._ordinal += 1
        candidate_id = f"senate:payroll-candidate:{self._ordinal:08d}"
        self.senate.append(
            {
                "amount_paid_raw": amount,
                "candidate_id": candidate_id,
                "office_raw": office,
                "payee_name_raw": payee,
                "report_period_start": period_start,
                "title_raw": title,
            }
        )
        return candidate_id

    # -- materialisation ----------------------------------------------------
    def argv(self) -> list[str]:
        if self._argv is not None:
            return list(self._argv)
        inputs = self.root / "inputs"
        argv: list[str] = []
        if self.ledger:
            ledger_root = inputs / "house_ledger"
            write_gz(
                ledger_root / "house_personnel_observations.ndjson.gz", self.ledger
            )
            write_gz(ledger_root / "house_person_office_spans.ndjson.gz", [])
            write_gz(ledger_root / "house_member_quarters.ndjson.gz", [])
            (ledger_root / "house_personnel_ledger_receipt.json").write_text(
                json.dumps({"status": "PASS"}, sort_keys=True), encoding="utf-8"
            )
            argv += ["--house-ledger-root", str(ledger_root)]
        if self.senate:
            path = inputs / "senate_payroll_employment_candidates.ndjson.gz"
            write_gz(path, self.senate)
            argv += ["--senate-candidates", str(path)]
        if self.roster:
            roster_dir = inputs / "roster"
            write_roster(roster_dir, self.roster)
            argv += ["--roster-dir", str(roster_dir)]
        if self.nickname is not None:
            path = inputs / "first_name_nicknames.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.nickname, sort_keys=True), encoding="utf-8")
            argv += ["--nickname-table", str(path)]
        if self.staff:
            path = inputs / "staff_directory.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.staff, sort_keys=True), encoding="utf-8")
            argv += ["--staff-directory", str(path)]
        if self.congestion:
            path = inputs / "congestion.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.congestion, sort_keys=True), encoding="utf-8")
            argv += ["--congestion", str(path)]
        for rows, flag, name in (
            (self.h1, "--h1-matches", "h1_matches.ndjson.gz"),
            (self.h2, "--h2-matches", "h2_matches.ndjson.gz"),
            (self.senate_matches, "--senate-matches", "senate_matches.ndjson.gz"),
        ):
            if rows:
                path = inputs / name
                write_gz(path, rows)
                argv += [flag, str(path)]
        if self.part_a:
            sidecar = inputs / "sidecar"
            write_gz(sidecar / "tiered_person_summary_25340.ndjson.gz", self.part_a)
            write_gz(sidecar / "tiered_person_office_records.ndjson.gz", [])
            write_gz(sidecar / "registrant_side_records.ndjson.gz", [])
            (sidecar / "tiered_corroboration_receipt.json").write_text(
                json.dumps({"status": "PASS"}, sort_keys=True), encoding="utf-8"
            )
            argv += ["--sidecar-root", str(sidecar)]
        if self.registrant:
            path = inputs / "registrant_episodes.ndjson.gz"
            write_gz(path, self.registrant)
            argv += ["--registrant-episodes", str(path)]
        self._argv = argv
        return list(argv)

    # -- running ------------------------------------------------------------
    def build(self, name: str = "primary") -> tuple[int, Path]:
        output_root = self.root / name
        extra: list[str] = []
        if self.name_standard:
            extra.append("--name-standard")
            if self.name_standard_baseline is not None:
                extra += [
                    "--name-standard-baseline",
                    str(self.name_standard_baseline),
                ]
            if self.name_standard_delta_report is not None:
                extra += [
                    "--name-standard-delta-report",
                    str(self.name_standard_delta_report),
                ]
        code = bs.main(
            self.argv()
            + [
                "--output-root",
                str(output_root),
                "--generated-at",
                GENERATED_AT,
                "--run-id",
                RUN_ID,
                "--no-glassbox",
            ]
            + extra
        )
        return code, output_root

    def build_ok(self, name: str = "primary") -> dict:
        code, output_root = self.build(name)
        payload = read_generation(output_root)
        assert code == 0, payload["receipt"]["failures"]
        assert payload["receipt"]["status"] == "PASS", payload["receipt"]["failures"]
        payload["output_root"] = output_root
        return payload

    def build_pair_and_verify(self, tag: str = "v") -> dict:
        primary = self.build_ok(f"{tag}_primary")["output_root"]
        twin = self.build_ok(f"{tag}_twin")["output_root"]
        report = self.root / f"{tag}_verification"
        code = vs.main(
            [
                "--primary-root",
                str(primary),
                "--twin-root",
                str(twin),
                "--report-root",
                str(report),
            ]
        )
        result = json.loads(
            (report / vs.VERIFICATION_FILE).read_text(encoding="utf-8")
        )
        return {"code": code, "primary": primary, "twin": twin, "result": result}


def two_member_roster() -> list[tuple]:
    return [
        ("A000001", "Alpha", "Beta", 2009, 2027),
        ("G000002", "Gamma", "Delta", 2009, 2027),
    ]


# ---------------------------------------------------------------------------
# 1. Shared employee: one person, two memberships, no double count
# ---------------------------------------------------------------------------
def test_shared_employee_is_one_person_with_two_memberships(tmp_path):
    world = World(tmp_path)
    world.roster = two_member_roster()
    world.add_ledger("2020Q1", "2020 HON. ALPHA BETA", "SMITH JANE", "SHARED EMPLOYEE")
    world.add_ledger("2020Q1", "2020 HON. GAMMA DELTA", "SMITH JANE", "SHARED EMPLOYEE")
    world.add_ledger("2020Q2", "2020 HON. ALPHA BETA", "SMITH JANE", "SHARED EMPLOYEE")
    world.add_ledger("2020Q2", "2020 HON. GAMMA DELTA", "SMITH JANE", "SHARED EMPLOYEE")

    out = world.build_ok()
    spine = out[bs.SPINE_FILE]
    spans = out[bs.SPAN_FILE]
    receipt = out["receipt"]

    assert len(spine) == 1, "a shared employee is one person, not two"
    person = spine[0]
    assert person["identity_tier"] == "S2"
    assert person["span_count"] == 2
    assert person["office_count"] == 2
    assert "SPINE_CROSS_OFFICE_S2" in person["link_methods"]
    assert "SPINE_CROSS_OFFICE_SHARED_EMPLOYEE" in person["link_methods"]
    assert person["member_bioguides"] == ["A000001", "G000002"]

    assert len(spans) == 2
    assert {span["office_key"] for span in spans} == {"HON:ALPHA|BETA", "HON:GAMMA|DELTA"}
    assert all(span["shared_employee"] is True for span in spans)
    assert all(span["periods_observed"] == 2 for span in spans)

    # No double count: four input rows, two spans of two observations each.
    assert sum(span["observation_count"] for span in spans) == 4
    assert receipt["conservation"]["observations_admitted"] == 4
    assert receipt["conservation"]["span_observation_count_sum"] == 4
    assert receipt["conservation"]["observation_conservation_holds"] is True
    assert receipt["counts"]["shared_employee_office_links"] >= 1
    assert receipt["counts"]["same_period_office_splits"] == 0
    assert receipt["counts"]["identity_tier_people"] == {"S2": 1}


# ---------------------------------------------------------------------------
# 2. Cross-office S2 over sequential spans vs the same-period collision
# ---------------------------------------------------------------------------
def test_cross_office_s2_links_sequential_non_overlapping_spans(tmp_path):
    world = World(tmp_path)
    world.roster = two_member_roster()
    world.add_ledger("2020Q1", "2020 HON. ALPHA BETA", "SMITH JANE", "STAFF ASSISTANT")
    world.add_ledger("2020Q2", "2020 HON. ALPHA BETA", "SMITH JANE", "STAFF ASSISTANT")
    world.add_ledger("2020Q3", "2020 HON. GAMMA DELTA", "SMITH JANE", "LEGISLATIVE DIRECTOR")
    world.add_ledger("2020Q4", "2020 HON. GAMMA DELTA", "SMITH JANE", "LEGISLATIVE DIRECTOR")

    out = world.build_ok()
    spine = out[bs.SPINE_FILE]
    spans = sorted(out[bs.SPAN_FILE], key=lambda row: row["first_period"])

    assert len(spine) == 1
    assert spine[0]["identity_tier"] == "S2"
    assert spine[0]["first_period"] == "2020Q1"
    assert spine[0]["last_period"] == "2020Q4"
    assert "SPINE_CROSS_OFFICE_SHARED_EMPLOYEE" not in spine[0]["link_methods"]

    assert [span["office_key"] for span in spans] == ["HON:ALPHA|BETA", "HON:GAMMA|DELTA"]
    assert [span["first_period"] for span in spans] == ["2020Q1", "2020Q3"]
    assert [span["last_period"] for span in spans] == ["2020Q2", "2020Q4"]
    assert all(span["contiguous"] is True for span in spans)
    assert all(span["shared_employee"] is False for span in spans)
    assert spans[0]["title_last"] == "STAFF ASSISTANT"
    assert spans[1]["title_first"] == "LEGISLATIVE DIRECTOR"
    assert out["receipt"]["counts"]["same_period_office_splits"] == 0


def test_same_period_two_offices_without_shared_employee_stay_two_people(tmp_path):
    world = World(tmp_path)
    world.roster = two_member_roster()
    world.add_ledger("2021Q1", "2021 HON. ALPHA BETA", "SMITH JANE", "STAFF ASSISTANT")
    world.add_ledger("2021Q1", "2021 HON. GAMMA DELTA", "SMITH JANE", "STAFF ASSISTANT")

    out = world.build_ok()
    spine = out[bs.SPINE_FILE]
    spans = out[bs.SPAN_FILE]
    receipt = out["receipt"]

    assert len(spine) == 2, "one payee key in two offices in one period is two people"
    assert {person["identity_tier"] for person in spine} == {"S1"}
    assert all(person["span_count"] == 1 for person in spine)
    assert len({person["spine_person_id"] for person in spine}) == 2
    assert len(spans) == 2
    assert {span["spine_person_id"] for span in spans} == {
        person["spine_person_id"] for person in spine
    }
    assert receipt["counts"]["same_period_office_splits"] >= 1
    assert receipt["counts"]["shared_employee_office_links"] == 0
    assert receipt["counts"]["identity_tier_people"] == {"S1": 2}
    assert receipt["conservation"]["duplicate_spine_person_ids"] == 0


def test_one_shared_employee_row_on_either_side_is_enough_to_link(tmp_path):
    """The exemption is per shared period and needs the flag on ONE side only."""

    world = World(tmp_path)
    world.roster = two_member_roster()
    world.add_ledger("2022Q1", "2022 HON. ALPHA BETA", "SMITH JANE", "SHARED EMPLOYEE")
    world.add_ledger("2022Q1", "2022 HON. GAMMA DELTA", "SMITH JANE", "CASEWORKER")

    out = world.build_ok()
    assert len(out[bs.SPINE_FILE]) == 1
    assert out[bs.SPINE_FILE][0]["identity_tier"] == "S2"
    spans = {span["office_key"]: span for span in out[bs.SPAN_FILE]}
    assert spans["HON:ALPHA|BETA"]["shared_employee"] is True
    assert spans["HON:GAMMA|DELTA"]["shared_employee"] is False


# ---------------------------------------------------------------------------
# 3. Current-staffer link, with a name collision inside one member office
# ---------------------------------------------------------------------------
def staffer_world(tmp_path) -> World:
    world = World(tmp_path)
    world.roster = [
        ("A000001", "Alpha", "Beta", 2009, 2027),
        ("G000002", "Gamma", "Delta", 2009, 2027),
        ("Z000003", "Zeta", "Omega", 2009, 2027),
        ("S000004", "Sigma", "Tau", 2009, 2027),
    ]
    latest = "2026Q1"
    # Two payroll people who share a first and last name inside one member office.
    world.add_ledger(latest, "2026 HON. ALPHA BETA", "DOE JOHN A", "LEGISLATIVE ASSISTANT")
    world.add_ledger(latest, "2026 HON. ALPHA BETA", "DOE JOHN B", "LEGISLATIVE ASSISTANT")
    # One unambiguous payroll person in another member office.
    world.add_ledger(latest, "2026 HON. GAMMA DELTA", "ROE MARY", "CHIEF OF STAFF")
    # A member office reachable only through the roster fallback.
    world.add_ledger(latest, "2026 HON. SIGMA TAU", "LEE SAM", "SCHEDULER")
    world.staff = {
        "Alpha Beta": [{"id": "1", "n": "John Doe", "t": "Legislative Assistant", "star": 0}],
        "Gamma Delta": [{"id": "2", "n": "Mary Roe", "t": "Chief of Staff", "star": 0}],
        "Zeta Omega": [{"id": "3", "n": "Nobody Here", "t": "Intern", "star": 0}],
        "Sigma Tau": [{"id": "4", "n": "Sam Lee", "t": "Scheduler", "star": 0}],
        "Notin Roster": [{"id": "5", "n": "Someone Else", "t": "Intern", "star": 0}],
    }
    world.congestion = {
        "A000001": {"name": "Alpha Beta", "type": "rep"},
        "G000002": {"name": "Gamma Delta", "type": "rep"},
        "Z000003": {"name": "Zeta Omega", "type": "rep"},
    }
    return world


def test_current_staffer_name_collision_is_not_linked(tmp_path):
    out = staffer_world(tmp_path).build_ok()
    rows = {row["quorum_staff_id"]: row for row in out[bs.STAFFER_FILE]}
    receipt = out["receipt"]

    assert len(rows) == 5
    assert receipt["conservation"]["current_staffer_rows"] == 5
    assert receipt["conservation"]["current_staffer_rows_equal_directory"] is True

    collided = rows["1"]
    assert collided["link_status"] == "NAME_COLLISION"
    assert collided["spine_person_id"] is None
    assert collided["candidate_count"] == 2
    assert collided["member_bioguide"] == "A000001"
    assert collided["member_resolution_source"] == "MEMBER_DISPLAY_NAME_INDEX"
    assert collided["hill_history"] == []

    linked = rows["2"]
    assert linked["link_status"] == "LINKED"
    assert linked["spine_person_id"] is not None
    assert linked["candidate_count"] == 1
    assert linked["hill_history"][0]["office_key"] == "HON:GAMMA|DELTA"
    assert linked["hill_history"][0]["status"] == "current"
    assert linked["hill_history"][0]["member_bioguide"] == "G000002"

    fallback = rows["4"]
    assert fallback["link_status"] == "LINKED"
    assert fallback["member_bioguide"] == "S000004"
    assert fallback["member_resolution_source"] == "ROSTER_STRICT_FALLBACK"

    not_on_payroll = rows["3"]
    assert not_on_payroll["link_status"] == "NOT_ON_PAYROLL"
    assert not_on_payroll["member_bioguide"] == "Z000003"
    assert not_on_payroll["candidate_count"] == 0

    unresolved = rows["5"]
    assert unresolved["link_status"] == "MEMBER_UNRESOLVED"
    assert unresolved["member_bioguide"] is None
    assert unresolved["member_resolution_source"] == "UNRESOLVED"

    assert receipt["counts"]["current_staffer_link_status"] == {
        "LINKED": 2,
        "MEMBER_UNRESOLVED": 1,
        "NAME_COLLISION": 1,
        "NOT_ON_PAYROLL": 1,
    }
    assert receipt["link_rates"]["current_staffers_linked"] == 2
    assert receipt["link_rates"]["current_staffers_total"] == 5

    # A collided staffer must not be stamped onto either spine person.
    spine = {row["spine_person_id"]: row for row in out[bs.SPINE_FILE]}
    assert [row for row in spine.values() if row["quorum_staff_id"] == "1"] == []
    assert sorted(
        row["quorum_staff_id"] for row in spine.values() if row["quorum_staff_id"]
    ) == ["2", "4"]


def test_current_staffer_link_requires_the_latest_house_period(tmp_path):
    """A person who left before the latest quarter is NOT_ON_PAYROLL, not LINKED."""

    world = World(tmp_path)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    world.add_ledger("2024Q1", "2024 HON. ALPHA BETA", "ROE MARY", "CHIEF OF STAFF")
    world.add_ledger("2026Q1", "2026 HON. ALPHA BETA", "LEE SAM", "SCHEDULER")
    world.staff = {
        "Alpha Beta": [
            {"id": "1", "n": "Mary Roe", "t": "Chief of Staff", "star": 0},
            {"id": "2", "n": "Sam Lee", "t": "Scheduler", "star": 0},
        ]
    }
    world.congestion = {"A000001": {"name": "Alpha Beta", "type": "rep"}}

    out = world.build_ok()
    rows = {row["quorum_staff_id"]: row for row in out[bs.STAFFER_FILE]}
    assert rows["1"]["link_status"] == "NOT_ON_PAYROLL"
    assert rows["2"]["link_status"] == "LINKED"
    spans = {span["office_key"]: span for span in out[bs.SPAN_FILE]}
    assert out["receipt"]["latest_period_by_chamber"]["house"] == "2026Q1"
    departed = [
        span for span in out[bs.SPAN_FILE] if span["last_period"] == "2024Q1"
    ]
    assert departed and departed[0]["status"] == "departed"
    assert spans["HON:ALPHA|BETA"] is not None


# ---------------------------------------------------------------------------
# 4. The PDF-era / CSV-era boundary at 2015Q4 -> 2016Q1 for one person
# ---------------------------------------------------------------------------
def test_pdf_era_and_csv_era_join_into_one_span_across_2015q4_2016q1(tmp_path):
    """One lane, both eras, one span.

    Before the ledger v3 rebind the two eras reached this module through two
    different files under two different parses, and a span crossing the boundary
    was a stitch between them.  They now arrive in one ledger, so the crossing
    span is a property of the span rule alone.  The rows still look different --
    the PDF era is the comma form with a trailing service-date hint and the
    em-dash continuation artifact, the CSV era the no-comma vendor form -- and
    the payee key still has to carry them to the same person.
    """

    world = World(tmp_path)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    world.add_pdf(
        "2015Q4",
        f"2015 HON. ALPHA BETA{EM_DASH}Con.",
        "SMITH, JANE 10/01/15",
        "COMMUNICATIONS DIRECTOR",
        "43125.00",
    )
    world.add_ledger(
        "2016Q1", "2016 HON. ALPHA BETA", "SMITH JANE", "COMMUNICATIONS DIRECTOR", "43125.00"
    )
    world.add_ledger(
        "2016Q2", "2016 HON. ALPHA BETA", "SMITH JANE", "COMMUNICATIONS DIRECTOR", "43125.00"
    )

    out = world.build_ok()
    spine = out[bs.SPINE_FILE]
    spans = out[bs.SPAN_FILE]
    receipt = out["receipt"]

    assert len(spine) == 1, "the same person either side of the boundary is one person"
    assert spine[0]["identity_tier"] == "S1"
    assert spine[0]["first_period"] == "2015Q4"
    assert spine[0]["last_period"] == "2016Q2"
    assert spine[0]["payee_key"] == {"first": "jane", "last": "smith", "middle_initial": None}

    assert len(spans) == 1, "one office, one span across the era boundary"
    span = spans[0]
    assert span["office_key"] == "HON:ALPHA|BETA"
    assert span["member_bioguide"] == "A000001"
    assert span["periods_observed"] == 3
    assert span["observation_count"] == 3
    assert span["contiguous"] is True
    assert span["first_period"] == "2015Q4"
    assert span["last_period"] == "2016Q2"
    assert span["core"] == {"start_latest": "2015-10-01", "end_earliest": "2016-06-30"}
    assert span["envelope"] == {"start_earliest": "2015-07-01", "end_latest": "2016-09-30"}
    # One lane.  The era is not a lane any more; it is a source_form INSIDE it.
    assert span["source_lane"] == ["house_ledger"]
    assert len(span["source_row_ids"]) == 3

    assert receipt["sources"]["source_rows_read"] == {"house_ledger": 3}
    assert receipt["sources"]["source_rows_admitted"] == {"house_ledger": 3}
    assert receipt["sources"]["source_rows_suppressed"] == {}
    assert receipt["sources"]["source_rows_suppressed_by_reason"] == {}
    assert receipt["sources"]["separate_pdf_lane_bound"] is False
    assert receipt["sources"]["house_ledger_quarters"] == 3
    assert receipt["sources"]["house_ledger_rows_read_by_source_form"] == {
        "detail_csv": 2,
        "house_gov_single_volume_pdf": 1,
    }
    assert receipt["sources"]["house_ledger_quarters_by_source_form"] == {
        "detail_csv": 2,
        "house_gov_single_volume_pdf": 1,
    }
    assert "house_pdf_present" not in receipt["sources"]
    assert "house_pdf_quarters_admitted" not in receipt["sources"]
    # The span's own era provenance, and the boundary crossing counted once.
    assert receipt["counts"]["spans_by_house_source_form"] == {
        "detail_csv+house_gov_single_volume_pdf": 1
    }
    assert receipt["counts"]["spans_crossing_csv_pdf_era_boundary"] == 1
    assert receipt["conservation"]["observations_admitted"] == 3
    assert receipt["conservation"]["span_observation_count_sum"] == 3


def test_the_separate_pdf_lane_cannot_be_bound(tmp_path):
    """The trap, closed at the command line.

    Ledger v3 carries the PDF era.  Passing the old candidate file as well would
    admit every 2009Q3-2015Q4 row twice, and conservation would still balance
    because the duplicates carry different row ids.  The option does not exist,
    so the mistake cannot be made.
    """

    import pytest

    with pytest.raises(SystemExit):
        bs.parse_args(
            ["--house-pdf-candidates", "anything", "--output-root", str(tmp_path)]
        )
    assert not hasattr(bs, "LANE_HOUSE_PDF")
    assert bs.RETIRED_LANE_HOUSE_PDF == "house_sod_pdf_2009q3_2015q4"


# ---------------------------------------------------------------------------
# 5. Conservation: every admitted row lands in exactly one span
# ---------------------------------------------------------------------------
def conservation_world(tmp_path) -> tuple[World, list[str]]:
    world = World(tmp_path)
    world.roster = [
        ("A000001", "Alpha", "Beta", 2009, 2027),
        ("G000002", "Gamma", "Delta", 2009, 2027),
        ("K000005", "Kappa", "Iota", 2009, 2027),
    ]
    expected: list[str] = []
    expected.append(
        world.add_pdf("2013Q1", "2013 HON. ALPHA BETA", "SMITH, JANE", "COUNSEL")
    )
    expected.append(
        world.add_pdf("2013Q2", "2013 COMMITTEE ON RULES", "SMITH, JANE", "COUNSEL")
    )
    expected.append(
        world.add_pdf("2013Q2", "2013 HON. GAMMA DELTA", "OTHER, PERSON", "SCHEDULER")
    )
    for quarter in ("2016Q1", "2016Q2", "2016Q3"):
        expected.append(
            world.add_ledger(
                quarter, f"{quarter[:4]} HON. ALPHA BETA", "SMITH JANE", "COUNSEL"
            )
        )
    expected.append(
        world.add_ledger("2016Q1", "2016 CLERK OF THE HOUSE", "THIRD PARTY", None, None)
    )
    expected.append(
        world.add_senate("2019-04-01", "SENATOR KAPPA IOTA", "NORTH, ROBIN", "COUNSEL")
    )
    expected.append(
        world.add_senate("2019-10-01", "SENATOR KAPPA IOTA", "NORTH, ROBIN", "COUNSEL")
    )
    expected.append(
        world.add_senate("2020-04-01", "APPROPRIATIONS", "NORTH, ROBIN", "COUNSEL")
    )
    return world, expected


def test_conservation_every_admitted_row_lands_in_exactly_one_span(tmp_path):
    world, expected_ids = conservation_world(tmp_path)
    out = world.build_ok()
    spans = out[bs.SPAN_FILE]
    receipt = out["receipt"]

    seen: dict[str, int] = {}
    for span in spans:
        for row_id in span["source_row_ids"]:
            seen[row_id] = seen.get(row_id, 0) + 1

    assert sorted(seen) == sorted(expected_ids)
    assert all(count == 1 for count in seen.values()), "a row landed in two spans"
    assert sum(span["observation_count"] for span in spans) == len(expected_ids)

    assert receipt["conservation"]["observations_admitted"] == len(expected_ids)
    assert receipt["conservation"]["span_observation_count_sum"] == len(expected_ids)
    assert receipt["conservation"]["distinct_source_row_ids"] == len(expected_ids)
    assert receipt["conservation"]["span_source_row_id_union"] == len(expected_ids)
    assert receipt["conservation"]["observation_conservation_holds"] is True
    assert receipt["conservation"]["spine_ids_equal"] is True
    assert receipt["conservation"]["duplicate_spine_person_ids"] == 0
    assert receipt["failures"] == []

    # The office index is the same population seen office-first.
    index_rows = out[bs.OFFICE_INDEX_FILE]
    assert sum(row["observation_count"] for row in index_rows) == len(expected_ids)
    assert {(row["chamber"], row["office_key"]) for row in index_rows} == {
        (span["chamber"], span["office_key"]) for span in spans
    }
    assert receipt["period_kind_by_chamber"] == {"house": "quarter", "senate": "half_year"}
    assert receipt["latest_period_by_chamber"] == {
        "house": "2016Q3",
        "senate": "2020-04-01",
    }


def test_conservation_holds_under_independent_verification(tmp_path):
    world, expected_ids = conservation_world(tmp_path)
    run = world.build_pair_and_verify()
    result = run["result"]

    assert run["code"] == 0, result["failures"]
    assert result["status"] == "PASS", result["failures"]
    assert result["assertions"]["rederived_rows_equal_emitted_rows"] is True
    assert result["assertions"]["primary_and_twin_byte_identical"] is True
    assert result["assertions"]["twin_receipt_equals_primary_receipt"] is True
    assert result["assertions"]["every_row_validates_against_its_schema"] is True
    assert result["assertions"]["anti_promotion_tripwire_clean"] is True
    assert result["assertions"]["language_law_clean"] is True
    assert result["assertions"]["observation_conservation"] is True
    assert result["assertions"]["input_hashes_rebind"] is True
    assert result["detail"]["conservation"]["observations_rederived"] == len(expected_ids)
    for name in bs.PAYLOAD_FILES:
        detail = result["detail"]["rederivation"][name]
        assert detail["emitted_rows"] == detail["rederived_rows"] == detail["matched_rows"]


# ---------------------------------------------------------------------------
# 6. Anti-promotion tripwire negative control
# ---------------------------------------------------------------------------
def promote_one_span_row(source: Path, destination: Path) -> None:
    """Copy a generation and flip one span row to ``promoted``.

    The receipt's file block is re-stamped so the copy stays self-consistent on
    bytes, rows and sha256 and primary and twin stay byte-identical: the only
    thing wrong with the copy is the promoted row, so a verifier FAIL cannot be
    attributed to a stale hash.
    """

    shutil.copytree(source, destination)
    path = destination / bs.SPAN_FILE
    rows = read_gz(path)
    assert rows, "fixture must emit at least one span row"
    rows[0]["canonical_employment_promoted"] = True
    bs.write_ndjson_gz(path, rows)
    receipt_path = destination / bs.RECEIPT_FILE
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["files"][bs.SPAN_FILE] = {
        "bytes": path.stat().st_size,
        "rows": len(rows),
        "sha256": bs.sha(path),
    }
    bs.write_json_atomic(receipt_path, receipt)


def test_promoted_row_makes_the_verifier_fail(tmp_path):
    world = World(tmp_path)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    world.add_ledger("2025Q1", "2025 HON. ALPHA BETA", "SMITH JANE", "COUNSEL")
    world.add_ledger("2025Q2", "2025 HON. ALPHA BETA", "SMITH JANE", "COUNSEL")

    clean = world.build_pair_and_verify()
    assert clean["code"] == 0, clean["result"]["failures"]
    assert clean["result"]["assertions"]["anti_promotion_tripwire_clean"] is True

    tampered_primary = tmp_path / "tampered_primary"
    tampered_twin = tmp_path / "tampered_twin"
    promote_one_span_row(clean["primary"], tampered_primary)
    promote_one_span_row(clean["twin"], tampered_twin)

    report = tmp_path / "tampered_verification"
    code = vs.main(
        [
            "--primary-root",
            str(tampered_primary),
            "--twin-root",
            str(tampered_twin),
            "--report-root",
            str(report),
        ]
    )
    result = json.loads((report / vs.VERIFICATION_FILE).read_text(encoding="utf-8"))

    assert code == 1
    assert result["status"] == "FAIL"
    assert "INV1_PROMOTION_TRIPWIRE" in result["failures"]
    assert result["assertions"]["anti_promotion_tripwire_clean"] is False
    # The tamper is the finding, not a bookkeeping artefact.
    assert result["assertions"]["receipt_file_block_matches_disk"] is True
    assert result["assertions"]["primary_and_twin_byte_identical"] is True
    # A const:false pin also catches it independently of the tripwire.
    assert result["assertions"]["every_row_validates_against_its_schema"] is False


def readmit_the_pdf_lane(source: Path, destination: Path) -> None:
    """Copy a generation and put ONE span back on the retired PDF lane.

    Everything else is re-stamped so the copy stays self-consistent on bytes,
    rows and sha256: the only thing wrong with it is that a span claims the
    separate 2009Q3-2015Q4 lane, which after the ledger v3 rebind can only mean
    that era was read twice.
    """

    shutil.copytree(source, destination)
    path = destination / bs.SPAN_FILE
    rows = read_gz(path)
    assert rows, "fixture must emit at least one span row"
    rows[0]["source_lane"] = sorted(
        set(rows[0]["source_lane"]) | {bs.RETIRED_LANE_HOUSE_PDF}
    )
    bs.write_ndjson_gz(path, rows)
    receipt_path = destination / bs.RECEIPT_FILE
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["files"][bs.SPAN_FILE] = {
        "bytes": path.stat().st_size,
        "rows": len(rows),
        "sha256": bs.sha(path),
    }
    bs.write_json_atomic(receipt_path, receipt)


def test_a_span_on_the_retired_pdf_lane_makes_the_verifier_fail(tmp_path):
    """Negative control for the double-count trap.

    The builder cannot produce this -- the option to bind the second lane is
    gone -- so the control has to manufacture it.  The point is that if a
    generation ever did carry it, the verifier says so instead of passing a
    quietly doubled observation set.
    """

    world = World(tmp_path)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    world.add_pdf("2015Q4", "2015 HON. ALPHA BETA", "SMITH, JANE", "COUNSEL")
    world.add_ledger("2016Q1", "2016 HON. ALPHA BETA", "SMITH JANE", "COUNSEL")

    clean = world.build_pair_and_verify()
    assert clean["code"] == 0, clean["result"]["failures"]
    assert clean["result"]["assertions"]["no_span_carries_the_retired_pdf_lane"] is True
    assert clean["result"]["assertions"]["no_separate_pdf_lane_input_bound"] is True
    assert clean["result"]["assertions"]["receipt_pins_separate_pdf_lane_false"] is True
    assert (
        clean["result"]["detail"]["era_provenance"]["house_ledger_carries_both_eras"]
        is True
    )

    tampered_primary = tmp_path / "relaned_primary"
    tampered_twin = tmp_path / "relaned_twin"
    readmit_the_pdf_lane(clean["primary"], tampered_primary)
    readmit_the_pdf_lane(clean["twin"], tampered_twin)

    report = tmp_path / "relaned_verification"
    code = vs.main(
        [
            "--primary-root",
            str(tampered_primary),
            "--twin-root",
            str(tampered_twin),
            "--report-root",
            str(report),
        ]
    )
    result = json.loads((report / vs.VERIFICATION_FILE).read_text(encoding="utf-8"))

    assert code == 1
    assert result["status"] == "FAIL"
    assert "SPAN_CARRIES_RETIRED_PDF_LANE" in result["failures"]
    assert result["assertions"]["no_span_carries_the_retired_pdf_lane"] is False
    # The tamper is the finding, not a bookkeeping artefact.
    assert result["assertions"]["receipt_file_block_matches_disk"] is True
    assert result["assertions"]["primary_and_twin_byte_identical"] is True


def test_a_borrowed_bioguide_and_a_derived_one_count_apart(tmp_path):
    """The carry-over ruling on ``member_resolution_method``.

    Two member offices in one build: one the ledger resolved, whose bioguide is
    borrowed from the ledger's own map, and one the ledger never resolved, whose
    bioguide this module derives from the roster.  Before this generation both
    recorded STRICT_ROSTER_SURNAME_AND_FIRST_NAME and the receipt summed them
    under one label, so a reader could not tell borrowed from derived.
    """

    world = World(tmp_path)
    world.roster = [
        ("A000001", "Alpha", "Beta", 2009, 2027),
        ("G000002", "Gamma", "Delta", 2009, 2027),
    ]
    world.add_ledger(
        "2016Q1",
        "2016 HON. ALPHA BETA",
        "SMITH JANE",
        "COUNSEL",
        office_key="HON:A000001",
        member_bioguide="A000001",
        container_kind="member_office",
    )
    # Never resolved by the ledger: no office_key, no member_bioguide.
    world.add_ledger("2016Q1", "2016 HON. GAMMA DELTA", "ROE MARY", "SCHEDULER")

    out = world.build_ok()
    by_key = {span["office_key"]: span for span in out[bs.SPAN_FILE]}

    assert by_key["HON:A000001"]["member_bioguide"] == "A000001"
    assert (
        by_key["HON:A000001"]["member_resolution_method"]
        == "LEDGER_SUPPLIED_STRICT_RESOLUTION"
    )
    assert by_key["HON:GAMMA|DELTA"]["member_bioguide"] == "G000002"
    assert (
        by_key["HON:GAMMA|DELTA"]["member_resolution_method"]
        == "STRICT_ROSTER_SURNAME_AND_FIRST_NAME"
    )
    assert out["receipt"]["counts"]["member_resolution_methods"] == {
        "LEDGER_SUPPLIED_STRICT_RESOLUTION": 1,
        "STRICT_ROSTER_SURNAME_AND_FIRST_NAME": 1,
    }
    # The office index records the same two methods as the spans do.
    index = {row["office_key"]: row for row in out[bs.OFFICE_INDEX_FILE]}
    assert (
        index["HON:A000001"]["member_resolution_method"]
        == "LEDGER_SUPPLIED_STRICT_RESOLUTION"
    )


def test_r1_rejects_every_pair_the_ledger_cannot_split(tmp_path):
    """The R-1 comment's two rejection tests, both exercised.

    Six era-scoped roster pairs are ambiguous.  A pair is rejected either
    because the ledger itself resolved it to two different bioguides, or
    because two roster members holding it served in the covered era.  Both
    counts are re-measured on every build and their SUM is how many ambiguous
    pairs the bound ledger can see -- which is why quoting one of them alone as
    "the number rejected" contradicted the list of six names.
    """

    world = World(tmp_path)
    world.roster = [
        ("P000149", "Donald", "Payne", 1989, 2012),
        ("P000604", "Donald", "Payne", 2012, 2027),
        ("H000981", "Duncan", "Hunter", 1981, 2009),
        ("H001048", "Duncan", "Hunter", 2009, 2021),
    ]
    # The ledger resolved this pair to TWO bioguides, one per era.
    world.add_pdf(
        "2011Q1",
        "2011 HON. DONALD PAYNE",
        "SMITH, JANE",
        "COUNSEL",
        office_key="HON:P000149",
        member_bioguide="P000149",
        container_kind="member_office",
    )
    world.add_ledger(
        "2016Q1",
        "2016 HON. DONALD PAYNE",
        "ROE MARY",
        "SCHEDULER",
        office_key="HON:P000604",
        member_bioguide="P000604",
        container_kind="member_office",
    )
    # The ledger resolved this pair to ONE bioguide, but two era roster members
    # hold it, so the name pair still cannot be reused for an unseen string.
    world.add_ledger(
        "2016Q2",
        "2016 HON. DUNCAN HUNTER",
        "NORTH ROBIN",
        "COUNSEL",
        office_key="HON:H001048",
        member_bioguide="H001048",
        container_kind="member_office",
    )

    stats = world.build_ok()["receipt"]["counts"]["ledger_field_disagreements"]
    assert stats["member_name_pairs_seen_in_ledger"] == 2
    assert stats["member_name_pairs_rejected_two_ledger_bioguides"] == 1
    assert stats["member_name_pairs_rejected_two_era_roster_members"] == 1
    assert stats["member_name_pairs_accepted"] == 0
    assert (
        stats["member_name_pairs_rejected_two_ledger_bioguides"]
        + stats["member_name_pairs_rejected_two_era_roster_members"]
        == stats["member_name_pairs_seen_in_ledger"]
    )


def test_tripwire_catches_every_promotion_shaped_field():
    assert bs.assert_unpromoted([]) == []
    clean = {
        "review_status": "REVIEW_REQUIRED",
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
    }
    assert bs.assert_unpromoted([clean]) == []
    assert vs.assert_unpromoted([clean]) == []
    for mutation in (
        {"review_status": "PROMOTED"},
        {"canonical_eligible": True},
        {"canonical_employment_promoted": True},
        {"canonical_identity_promoted": True},
    ):
        row = dict(clean)
        row.update(mutation)
        assert bs.assert_unpromoted([row]), mutation
        assert vs.assert_unpromoted([row]), mutation


# ---------------------------------------------------------------------------
# 7. Regression: payee keys are not orderable as raw triples
# ---------------------------------------------------------------------------
def test_raw_payee_triples_are_not_orderable_but_the_sort_key_is():
    with pytest.raises(TypeError):
        sorted([("daly", "brendan", None), ("daly", "brendan", "m")])
    assert bs.payee_sort_key(("daly", "brendan", None)) < bs.payee_sort_key(
        ("daly", "brendan", "m")
    )
    assert bs.payee_sort_key(("daly", "brendan", None)) == vs.payee_sort_key(
        ("daly", "brendan", None)
    )
    # The substitution stays injective: _triple never emits an empty middle.
    assert bs._triple("Daly", "Brendan", "") == ("daly", "brendan", None)
    assert bs._triple("Daly", "Brendan", "M.") == ("daly", "brendan", "m")


def test_same_name_with_and_without_a_middle_initial_builds(tmp_path):
    """The two payee forms co-occur in one chamber across the era boundary."""

    world = World(tmp_path)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    world.add_pdf("2015Q1", "2015 HON. ALPHA BETA", "DALY, BRENDAN", "PRESS SECRETARY")
    world.add_ledger("2016Q1", "2016 HON. ALPHA BETA", "DALY BRENDAN M", "PRESS SECRETARY")
    world.add_ledger("2016Q1", "2016 HON. ALPHA BETA", "ANDREWS THOMAS S", "COUNSEL")
    world.add_pdf("2015Q1", "2015 HON. ALPHA BETA", "ANDREWS, THOMAS", "COUNSEL")

    out = world.build_ok()
    spine = out[bs.SPINE_FILE]
    # Four distinct payee keys -> four people; the point is that the build ran.
    assert len(spine) == 4
    assert {person["identity_tier"] for person in spine} == {"S1"}
    middles = sorted(
        (
            (person["payee_key"]["last"], person["payee_key"]["middle_initial"])
            for person in spine
        ),
        key=lambda pair: (pair[0], pair[1] or ""),
    )
    assert middles == [
        ("andrews", None),
        ("andrews", "s"),
        ("daly", None),
        ("daly", "m"),
    ]
    run = world.build_pair_and_verify()
    assert run["code"] == 0, run["result"]["failures"]


# ---------------------------------------------------------------------------
# 8. Regression: the committed nickname table's shape
# ---------------------------------------------------------------------------
COMMITTED_NICKNAME_PAYLOAD = {
    "schema_id": "staffer-network-first-name-nickname-table-v1",
    "provenance": "short form to one or more formal forms",
    "entries": {
        "abe": ["abraham"],
        "al": ["alan", "albert"],
        "bill": ["william"],
    },
}


def test_committed_nickname_table_is_loaded_and_ambiguous_entries_are_dropped(tmp_path):
    path = tmp_path / "first_name_nicknames_v1.json"
    path.write_text(json.dumps(COMMITTED_NICKNAME_PAYLOAD, sort_keys=True), encoding="utf-8")

    table, loaded = bs.load_nickname_table(path)
    assert loaded is True
    assert table["abe"] == "abraham"
    assert table["bill"] == "william"
    # Ambiguous short forms are dropped, never collapsed onto one token.
    assert "al" not in table
    # The wrapper's own metadata is never injected as a nickname.
    assert "schema_id" not in table
    assert "provenance" not in table
    # The verifier's independent restatement agrees.
    assert bs._flatten_nickname_payload(COMMITTED_NICKNAME_PAYLOAD) == (
        vs.flatten_nickname_payload(COMMITTED_NICKNAME_PAYLOAD)
    )
    assert vs.load_nickname_table(path)["abe"] == "abraham"


def test_load_nickname_table_reports_a_useless_file_as_not_loaded(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text(
        json.dumps({"schema_id": bs.NICKNAME_TABLE_SCHEMA_ID, "entries": {}}),
        encoding="utf-8",
    )
    table, loaded = bs.load_nickname_table(path)
    assert loaded is False
    assert table == dict(bs.NICKNAME_MAP)
    # The two legacy shapes the loader documents still work.
    flat = tmp_path / "flat.json"
    flat.write_text(json.dumps({"abe": "abraham"}), encoding="utf-8")
    assert bs.load_nickname_table(flat) == ({**bs.NICKNAME_MAP, "abe": "abraham"}, True)
    inverted = tmp_path / "inverted.json"
    inverted.write_text(json.dumps({"map": {"abraham": ["abe"]}}), encoding="utf-8")
    assert bs.load_nickname_table(inverted) == (
        {**bs.NICKNAME_MAP, "abe": "abraham"},
        True,
    )


def test_nickname_table_changes_strict_bioguide_resolution(tmp_path):
    def build(with_table: bool, name: str):
        world = World(tmp_path / name)
        world.roster = [("A000009", "Abraham", "Beta", 2009, 2027)]
        world.add_ledger("2020Q1", "2020 HON. ABE BETA", "SMITH JANE", "COUNSEL")
        if with_table:
            world.nickname = COMMITTED_NICKNAME_PAYLOAD
        return world.build_ok()

    without = build(False, "without")
    assert without[bs.SPAN_FILE][0]["member_bioguide"] is None
    assert (
        without[bs.SPAN_FILE][0]["member_resolution_method"]
        == "UNRESOLVED_FIRST_NAME_NOT_IN_ROSTER"
    )
    assert without["receipt"]["notes"]["nickname_table"].startswith("declared file absent")

    with_table = build(True, "with")
    assert with_table[bs.SPAN_FILE][0]["member_bioguide"] == "A000009"
    assert (
        with_table[bs.SPAN_FILE][0]["member_resolution_method"]
        == "STRICT_ROSTER_SURNAME_AND_FIRST_NAME"
    )
    assert with_table["receipt"]["notes"]["nickname_table"] == "loaded from the declared file"


# ---------------------------------------------------------------------------
# 9. Cross-chamber S3
# ---------------------------------------------------------------------------
def test_cross_chamber_s3_merges_only_when_the_periods_are_disjoint(tmp_path):
    world = World(tmp_path / "disjoint")
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    world.add_ledger("2016Q1", "2016 HON. ALPHA BETA", "SMITH JANE", "COUNSEL")
    world.add_senate("2018-04-01", "APPROPRIATIONS", "SMITH, JANE", "COUNSEL")
    out = world.build_ok()
    assert len(out[bs.SPINE_FILE]) == 1
    person = out[bs.SPINE_FILE][0]
    assert person["identity_tier"] == "S3"
    assert person["chambers"] == ["house", "senate"]
    assert "SPINE_CROSS_CHAMBER_S3" in person["link_methods"]
    assert person["first_period"] == "2016Q1"
    assert person["last_period"] == "2018-04-01"
    assert out["receipt"]["counts"]["cross_chamber_merges"] == 1

    overlap = World(tmp_path / "overlap")
    overlap.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    overlap.add_ledger("2018Q2", "2018 HON. ALPHA BETA", "SMITH JANE", "COUNSEL")
    overlap.add_senate("2018-04-01", "APPROPRIATIONS", "SMITH, JANE", "COUNSEL")
    out2 = overlap.build_ok()
    assert len(out2[bs.SPINE_FILE]) == 2
    assert {person["identity_tier"] for person in out2[bs.SPINE_FILE]} == {"S1"}
    assert out2["receipt"]["counts"]["cross_chamber_merges"] == 0
    assert out2["receipt"]["counts"]["cross_chamber_not_merged_period_overlap"] == 1


# ---------------------------------------------------------------------------
# 10. LDA payroll-key links
# ---------------------------------------------------------------------------
def test_lda_links_resolve_by_candidate_id_and_by_name_and_office(tmp_path):
    world = World(tmp_path)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    # H1 keys on the PDF-era candidate id.  It now arrives through the ledger in
    # source_locator.candidate_id rather than as the row id of a second lane,
    # and the join has to survive that.
    pdf_row_id = world.add_pdf(
        "2014Q1", "2014 HON. ALPHA BETA", "SMITH, JANE", "COUNSEL"
    )
    candidate_id = world.candidate_ids[pdf_row_id]
    assert candidate_id != pdf_row_id
    world.add_ledger(
        "2017Q1", "2017 TRANSPORTATION-INFRASTRUCTURE", "BROWN CHRISTOPHER C", "STAFF DIRECTOR"
    )
    world.h1 = [
        {
            "lda_source_person_id": "lda:lobbyist:11",
            "payroll_candidate_id": candidate_id,
            "lda_display_name": "JANE SMITH",
            "employing_office_raw": "2014 HON. ALPHA BETA",
            "payroll_payee_raw": "SMITH, JANE",
        }
    ]
    world.h2 = [
        {
            "lda_source_person_id": "lda:lobbyist:22",
            "payroll_support_digest": "b" * 64,
            "display_name": "CHRISTOPHER C BROWN",
            "employing_office_candidate": "TRANSPORTATION-INFRASTRUCTURE",
        }
    ]
    world.senate_matches = [
        {
            "lda_source_person_id": "lda:lobbyist:33",
            "payroll_support_digest": "c" * 64,
            "display_name": "ROBIN NORTH",
            "employing_office_candidate": "SENATOR NOBODY ATALL",
        }
    ]
    world.part_a = [
        {"lda_source_person_id": "lda:lobbyist:11", "max_tier": "L4"},
        {"lda_source_person_id": "lda:lobbyist:22", "max_tier": "L2"},
        {"lda_source_person_id": "lda:lobbyist:33", "max_tier": "L1"},
    ]

    out = world.build_ok()
    links = {row["lda_source_person_id"]: row for row in out[bs.LDA_LINK_FILE]}
    receipt = out["receipt"]

    assert links["lda:lobbyist:11"]["link_status"] == "LINKED_BY_PAYROLL_KEY"
    assert links["lda:lobbyist:11"]["key_resolution"] == "MATCHED_UNIQUE"
    assert links["lda:lobbyist:11"]["lane"] == "h1_house_sod_pdf"
    assert links["lda:lobbyist:11"]["payroll_key_field"] == "payroll_candidate_id"
    assert links["lda:lobbyist:11"]["part_a_tier"] == "L4"

    assert links["lda:lobbyist:22"]["link_status"] == "LINKED_BY_PAYROLL_KEY"
    assert links["lda:lobbyist:22"]["lane"] == "h2_house_payroll"
    assert links["lda:lobbyist:22"]["part_a_tier"] == "L2"

    assert links["lda:lobbyist:33"]["link_status"] == "KEY_NOT_FOUND"
    assert links["lda:lobbyist:33"]["key_resolution"] == "KEY_ABSENT"
    assert links["lda:lobbyist:33"]["spine_person_id"] is None

    assert receipt["link_rates"]["lda_people_in_match_lanes"] == 3
    assert receipt["link_rates"]["lda_people_linked"] == 2
    assert receipt["counts"]["lda_link_status"] == {
        "KEY_NOT_FOUND": 1,
        "LINKED_BY_PAYROLL_KEY": 2,
    }

    spine = {row["spine_person_id"]: row for row in out[bs.SPINE_FILE]}
    carried = {
        row["lda_source_person_id"]: row["lda_tier"]
        for row in spine.values()
        if row["lda_source_person_id"]
    }
    assert carried == {"lda:lobbyist:11": "L4", "lda:lobbyist:22": "L2"}
    assert "LDA_PAYROLL_KEY_H1" in spine[links["lda:lobbyist:11"]["spine_person_id"]][
        "link_methods"
    ]
    assert "LDA_PAYROLL_KEY_H2" in spine[links["lda:lobbyist:22"]["spine_person_id"]][
        "link_methods"
    ]

    run = world.build_pair_and_verify()
    assert run["code"] == 0, run["result"]["failures"]


# ---------------------------------------------------------------------------
# 11. Immutability and determinism gates
# ---------------------------------------------------------------------------
def test_refuses_to_write_into_a_non_empty_output_root(tmp_path):
    world = World(tmp_path)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    world.add_ledger("2020Q1", "2020 HON. ALPHA BETA", "SMITH JANE", "COUNSEL")
    world.build_ok("primary")
    with pytest.raises(bs.GateFailure, match="INV-2"):
        world.build("primary")


def test_no_personnel_source_present_is_a_declared_failure(tmp_path):
    world = World(tmp_path)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    code, output_root = world.build("empty")
    receipt = json.loads((output_root / bs.RECEIPT_FILE).read_text(encoding="utf-8"))
    assert code == 1
    assert receipt["status"] == "FAIL"
    assert "NO_PERSONNEL_SOURCE_PRESENT" in receipt["failures"]
    assert receipt["canonical_employment_promotions"] == 0
    assert receipt["canonical_identity_promotions"] == 0


def test_generated_at_must_carry_a_timezone(tmp_path):
    world = World(tmp_path)
    world.add_ledger("2020Q1", "2020 HON. ALPHA BETA", "SMITH JANE", "COUNSEL")
    with pytest.raises(bs.GateFailure, match="ISO-8601"):
        bs.main(
            world.argv()
            + [
                "--output-root",
                str(tmp_path / "bad"),
                "--generated-at",
                "2026-09-02T00:00:00",
                "--no-glassbox",
            ]
        )


# ---------------------------------------------------------------------------
# R-1.  A member office key names a MEMBER, never a bare surname
# ---------------------------------------------------------------------------
def two_thompsons() -> list[tuple]:
    return [
        ("B000193", "Bennie", "Thompson", 2009, 2027),
        ("T000460", "Mike", "Thompson", 2009, 2027),
    ]


def test_two_same_surname_members_never_share_an_office_key(tmp_path):
    """The v1 defect, pinned.

    ``HON:<SURNAME>`` put every Thompson in one office, stamped the
    alphabetically-first member's bioguide on all of their staff, and -- because
    the two members were then one office -- suppressed the same-period collision
    rule between them entirely.  Two members must never share a key, whether or
    not the House ledger resolved either of them.
    """

    # The key is a pure function of the office string, so assert it directly
    # first, with no ledger to lean on.
    # The nickname table folds the first name, so MIKE and MICHAEL are one
    # member and BENNIE is another.
    bare = bs.HouseOfficeKey({}, {}, bs.NICKNAME_MAP)
    assert bare("2013 HON. MIKE THOMPSON") != bare("2013 HON. BENNIE THOMPSON")
    assert bare("2013 HON. MIKE THOMPSON") == "HON:MICHAEL|THOMPSON"
    assert bare("2013 HON. MICHAEL THOMPSON") == "HON:MICHAEL|THOMPSON"
    assert bare("2013 HON. BENNIE THOMPSON") == "HON:BENNIE|THOMPSON"

    world = World(tmp_path)
    world.roster = two_thompsons()
    # One payee name, both offices, the SAME quarter, no shared-employee title.
    world.add_ledger("2020Q1", "2020 HON. MIKE THOMPSON", "SMITH JANE", "COUNSEL")
    world.add_ledger("2020Q1", "2020 HON. BENNIE THOMPSON", "SMITH JANE", "COUNSEL")

    out = world.build_ok()
    spans = out[bs.SPAN_FILE]
    receipt = out["receipt"]
    keys = {span["office_key"] for span in spans}
    assert len(keys) == 2, "two members, two office keys"

    by_key = {span["office_key"]: span for span in spans}
    bioguides = {key: span["member_bioguide"] for key, span in by_key.items()}
    assert sorted(bioguides.values()) == ["B000193", "T000460"]
    assert len(set(bioguides.values())) == 2, "each office resolves its own member"

    # The same-period collision rule can now fire between them: one payee key in
    # two offices in one quarter with no shared-employee row is two people.
    assert len(out[bs.SPINE_FILE]) == 2
    assert receipt["counts"]["same_period_office_splits"] >= 1
    assert receipt["counts"]["identity_tier_people"] == {"S1": 2}

    # And the census the ruling set as the acceptance bar reads zero.
    census = receipt["counts"]["ledger_field_disagreements"]
    assert census["member_office_keys"] == 2
    assert census["member_office_keys_merging_more_than_one_office_name"] == 0
    assert census["member_office_keys_merging_more_than_one_ledger_bioguide"] == 0


def test_member_office_key_and_bioguide_come_from_the_house_ledger(tmp_path):
    """Level 1 and level 2 of the member office key.

    A ledger office row hands over its own ``HON:<bioguide>``, and the emitted
    ``member_bioguide`` is that bioguide rather than one re-derived under a
    different rule -- which is what makes the ledger disagreement count zero.
    A PDF-era office string the ledger never saw reaches the same key through
    the member's name, and the OTHER same-surname member's PDF-era string does
    not.
    """

    world = World(tmp_path)
    world.roster = two_thompsons()
    world.add_ledger(
        "2016Q1",
        "2016 HON. MIKE THOMPSON",
        "SMITH JANE",
        "COUNSEL",
        office_key="HON:T000460",
        member_bioguide="T000460",
        container_kind="member_office",
    )
    world.add_pdf("2013Q1", "2013 HON. MIKE THOMPSON", "SMITH, JANE", "COUNSEL")
    world.add_pdf("2013Q1", "2013 HON. BENNIE THOMPSON", "ROE, MARY", "SCHEDULER")

    out = world.build_ok()
    spans = out[bs.SPAN_FILE]
    receipt = out["receipt"]
    by_key = {span["office_key"]: span for span in spans}

    assert "HON:T000460" in by_key, "the ledger's own office key is reused"
    assert by_key["HON:T000460"]["member_bioguide"] == "T000460"
    assert (
        by_key["HON:T000460"]["member_resolution_method"]
        == "LEDGER_SUPPLIED_STRICT_RESOLUTION"
    ), "the bioguide was borrowed from the ledger, not re-derived here"
    # The 2013 string carries no office_key of its own -- the ledger resolved
    # only the 2016 one -- and still lands on the same office, so the PDF era
    # joins the CSV era for that member through the member's name.
    assert by_key["HON:T000460"]["source_lane"] == [bs.LANE_HOUSE_LEDGER]
    assert receipt["counts"]["spans_by_house_source_form"][
        "detail_csv+house_gov_single_volume_pdf"
    ] == 1
    # The other Thompson does not.
    assert "HON:BENNIE|THOMPSON" in by_key
    assert by_key["HON:BENNIE|THOMPSON"]["member_bioguide"] == "B000193"

    disagreements = receipt["counts"]["ledger_field_disagreements"]
    assert disagreements["member_bioguide_present"] == 1
    assert disagreements["member_bioguide_disagreement"] == 0
    assert disagreements["office_key_disagreement"] == 0
    assert disagreements["ledger_office_string_key_conflicts"] == 0


def test_a_name_the_ledger_cannot_split_carries_no_bioguide(tmp_path):
    """The declared residue.

    Two members with the SAME first name and surname cannot be separated by the
    office string.  They share the fallback key -- but that key resolves to no
    member, so nothing is attributed to either of them.  A merged key that
    attributed one of them would be the v1 defect again.
    """

    world = World(tmp_path)
    world.roster = [
        ("R000572", "Mike", "Rogers", 2001, 2015),
        ("R000575", "Mike", "Rogers", 2003, 2027),
    ]
    world.add_pdf("2013Q1", "2013 HON. MIKE ROGERS", "SMITH, JANE", "COUNSEL")

    out = world.build_ok()
    span = out[bs.SPAN_FILE][0]
    assert span["office_key"] == "HON:MICHAEL|ROGERS"
    assert span["member_bioguide"] is None
    assert span["member_resolution_method"] == "UNRESOLVED_FIRST_NAME_DOES_NOT_DISAMBIGUATE"


# ---------------------------------------------------------------------------
# R-2.  The continuation stripper must not eat a surname
# ---------------------------------------------------------------------------
def test_don_bacon_keys_on_the_whole_surname(tmp_path):
    """``[—']?\\s*Con\\.?$`` made the dash optional, so it ate the CON out of
    BACON and MELANCON: 1,251 and 154 House rows keyed ``HON:BA`` and
    ``HON:MELAN``, and neither truncated surname could resolve against the
    roster."""

    assert bs.normalize_office("2017 HON. DON BACON") == "HON. DON BACON"
    assert bs.normalize_office("2010 HON. CHARLIE MELANCON") == "HON. CHARLIE MELANCON"
    # A genuine continuation still goes.
    assert (
        bs.normalize_office(f"2017 HON. DON BACON{EM_DASH}Con.") == "HON. DON BACON"
    )
    assert bs.normalize_office("2017 HON. DON BACON’Con.") == "HON. DON BACON"

    bare = bs.HouseOfficeKey({}, {}, bs.NICKNAME_MAP)
    assert bare("2017 HON. DON BACON") == "HON:DON|BACON"
    assert bare("2010 HON. CHARLIE MELANCON") == "HON:CHARLES|MELANCON"

    world = World(tmp_path)
    world.roster = [
        ("B001298", "Don", "Bacon", 2017, 2027),
        ("M000998", "Charlie", "Melancon", 2005, 2011),
    ]
    world.add_ledger("2017Q1", "2017 HON. DON BACON", "SMITH JANE", "COUNSEL")
    world.add_ledger(
        "2017Q2", f"2017 HON. DON BACON{EM_DASH}Con.", "SMITH JANE", "COUNSEL"
    )
    world.add_pdf("2010Q1", "2010 HON. CHARLIE MELANCON", "ROE, MARY", "SCHEDULER")

    out = world.build_ok()
    by_key = {span["office_key"]: span for span in out[bs.SPAN_FILE]}
    assert set(by_key) == {"HON:DON|BACON", "HON:CHARLES|MELANCON"}
    # The continuation row folded into the same office, not a second one.
    assert by_key["HON:DON|BACON"]["periods_observed"] == 2
    # And with the whole surname the roster resolves both, which HON:BA and
    # HON:MELAN could never do.
    assert by_key["HON:DON|BACON"]["member_bioguide"] == "B001298"
    assert by_key["HON:CHARLES|MELANCON"]["member_bioguide"] == "M000998"


# ---------------------------------------------------------------------------
# --name-standard.  The re-key: OFF by default, and when on, an id map that is
# exact against the build it re-keys.
# ---------------------------------------------------------------------------
NAME_STANDARD_FIXTURE_TABLE = {
    "schema_id": "staffer-network-first-name-nickname-class-table-v2",
    "entries": {
        "james": "jamie",
        "jamie": "jamie",
        "jim": "jamie",
        "robert": "robert",
        "bob": "robert",
        "jane": "jane",
        "mary": "mary",
    },
}


@pytest.fixture
def name_standard_table(tmp_path, monkeypatch):
    """Point the standard at a small, stable class table for the duration.

    The shipped table is another lane's artifact and is free to grow; a test
    that pins a fold must pin the table too, or it is testing that file rather
    than this builder.
    """

    standard = bs.load_name_standard()
    path = tmp_path / "first_name_nicknames_v2.json"
    path.write_text(json.dumps(NAME_STANDARD_FIXTURE_TABLE, sort_keys=True), encoding="utf-8")
    monkeypatch.setenv("STAFFER_NAME_CLASS_TABLE", str(path))
    standard.reset_class_table_cache()
    yield path
    standard.reset_class_table_cache()


#: The five-person world's key-change histogram, WRITTEN OUT rather than read
#: back off the build.  SMITH JAMES folds onto the jamie class; SMITH JAMIE and
#: ROE MARY do not move; O'BRIEN PAT moves on the punctuation fold alone;
#: DALY-JR BOB moves on all three -- the fold drops the hyphen, the suffix lift
#: takes JR out of the surname, and BOB folds onto robert.
FIVE_PERSON_CAUSE_HISTOGRAM = {"ascii_punct": 2, "nickname_class": 2, "suffix": 1}


def write_delta_report(path: Path, cause_histogram: dict, keys_changed: int) -> Path:
    """A read-only re-key delta report in the shape ruling B asserts against.

    Only the two fields the builder reads are written; the real report carries
    a great deal more, and binding a fuller one would make these tests depend
    on that script's output format rather than on this contract.
    """

    path.write_text(
        json.dumps(
            {
                "name_standard_version": "test-fixture",
                "read_only": True,
                "key_change": {
                    "cause_histogram": dict(cause_histogram),
                    "changed_v1_1_raw_route": keys_changed,
                },
            },
            indent=1,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def five_person_world(root: Path) -> World:
    """Five payroll people in one member office and one reporting period.

    SMITH JAMES and SMITH JAMIE fold onto one name key and are the merge.
    O'BRIEN PAT moves on the ascii/punctuation fold alone.  ROE MARY does not
    move at all.  DALY-JR BOB moves on the suffix lift.
    """

    world = World(root)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    office = "2016 HON. ALPHA BETA"
    world.add_ledger("2016Q1", office, "SMITH JAMES", "COUNSEL",
                     service_start="2016-01-01", service_end="2016-02-14")
    world.add_ledger("2016Q1", office, "SMITH JAMIE", "COUNSEL",
                     service_start="2016-02-15", service_end="2016-03-31")
    world.add_ledger("2016Q1", office, "O'BRIEN PAT", "SCHEDULER")
    world.add_ledger("2016Q1", office, "ROE MARY", "SCHEDULER")
    world.add_ledger("2016Q1", office, "DALY-JR, BOB", "SCHEDULER")
    return world


def five_person_rekey_world(root: Path) -> World:
    """:func:`five_person_world` with the re-key on and its delta report bound."""

    world = five_person_world(root)
    world.name_standard = True
    world.name_standard_delta_report = write_delta_report(
        root / "delta_report.json", FIVE_PERSON_CAUSE_HISTOGRAM, 3
    )
    return world


def test_name_standard_is_off_by_default(tmp_path):
    """No flag, no re-key: no new spine field, no id map, no receipt block."""

    out = five_person_world(tmp_path).build_ok()
    assert "name_standard" not in out["receipt"]
    assert not (out["output_root"] / bs.NAME_STANDARD_ID_MAP_FILE).exists()
    assert bs.NAME_STANDARD_ID_MAP_FILE not in out["receipt"]["files"]
    for row in out[bs.SPINE_FILE]:
        assert set(row["payee_key"]) == {"last", "first", "middle_initial"}
        for field in (
            "name_key",
            "display_name",
            "legacy_person_id",
            "legacy_person_ids",
            "name_standard_parts",
            "payee_raw",
        ):
            assert field not in row
    # Five distinct payee keys, five people: nothing merged.
    assert len(out[bs.SPINE_FILE]) == 5


def test_name_standard_id_map_is_exact_against_the_default_build(
    tmp_path, name_standard_table
):
    """The map is total on the previous ids, and every legacy id reproduces."""

    # ONE world, built twice: the default build and the re-key must read the
    # very same input files, or the baseline sha invariant is comparing two
    # fixtures rather than two builds.
    world = five_person_rekey_world(tmp_path)
    world.name_standard = False
    default = world.build_ok("default")
    world.name_standard = True
    world.name_standard_baseline = default["output_root"]
    out = world.build_ok("rekeyed")

    id_map = read_gz(out["output_root"] / bs.NAME_STANDARD_ID_MAP_FILE)
    legacy_before = {row["spine_person_id"] for row in default[bs.SPINE_FILE]}

    # One row per previous person, and the legacy ids ARE the previous ids.
    assert len(id_map) == 5
    assert {row["legacy_person_id"] for row in id_map} == legacy_before
    assert len({row["legacy_person_id"] for row in id_map}) == 5

    # One merge: JAMES and JAMIE fold together, so five people become four.
    assert len({row["person_id"] for row in id_map}) == 4
    assert len(out[bs.SPINE_FILE]) == 4
    merged = [row for row in id_map if row["reason"] == "merged"]
    assert len(merged) == 2
    assert merged[0]["person_id"] == merged[1]["person_id"]
    assert merged[0]["merged_with"] == [merged[1]["legacy_person_id"]]
    assert merged[1]["merged_with"] == [merged[0]["legacy_person_id"]]

    # Every spine row carries its previous ids, and their union is the whole
    # previous population exactly once.
    carried: list[str] = []
    for row in out[bs.SPINE_FILE]:
        assert row["legacy_person_id"] == sorted(row["legacy_person_ids"])[0]
        carried.extend(row["legacy_person_ids"])
    assert sorted(carried) == sorted(legacy_before)

    # The map's targets are exactly the spine's ids.
    assert {row["person_id"] for row in id_map} == {
        row["spine_person_id"] for row in out[bs.SPINE_FILE]
    }

    # The reasons name the causes the delta vocabulary defines.
    by_key = {row["key_v6"]: row for row in id_map}
    assert by_key["smith|james|"]["reason"] == "merged"
    assert by_key["smith|jamie|"]["reason"] == "merged"
    assert by_key["o'brien|pat|"]["reason"] == "ascii_punct"
    assert by_key["o'brien|pat|"]["key_v7"] == "obrien|pat|"
    assert by_key["roe|mary|"]["reason"] == "unchanged"
    assert by_key["roe|mary|"]["causes"] == []
    assert by_key["daly-jr|bob|"]["reason"] == "suffix"
    assert "suffix" in by_key["daly-jr|bob|"]["causes"]
    assert by_key["daly-jr|bob|"]["key_v7"] == "daly|robert|"

    # Conservation: the office index and the observations are the ones the
    # identity rules produced, not a re-grouped set.  Ruling A: regrouping is
    # false and the receipt says so.
    assert out["receipt"]["name_standard"]["regrouping"] is False
    assert len(out[bs.OFFICE_INDEX_FILE]) == len(default[bs.OFFICE_INDEX_FILE])
    assert (
        out["receipt"]["conservation"]["observations_admitted"]
        == default["receipt"]["conservation"]["observations_admitted"]
    )
    # Ruling C: spans are conserved MINUS the union.  JAMES and JAMIE held the
    # same office in the same quarter, so their two spans became one, and no
    # observation was lost doing it.
    unioned = out["receipt"]["counts"]["spans_unioned_after_merge"]
    assert unioned == 1
    assert len(out[bs.SPAN_FILE]) == len(default[bs.SPAN_FILE]) - unioned
    assert out["receipt"]["counts"]["person_office_spans_with_touching_windows"] == 0
    assert (
        sum(row["observation_count"] for row in out[bs.SPAN_FILE])
        == sum(row["observation_count"] for row in default[bs.SPAN_FILE])
    )
    # The unioned row is one row over BOTH observations, and it carries both
    # source row ids.
    merged_id = merged[0]["person_id"]
    merged_spans = [
        row for row in out[bs.SPAN_FILE] if row["spine_person_id"] == merged_id
    ]
    assert len(merged_spans) == 1
    assert merged_spans[0]["observation_count"] == 2
    assert len(merged_spans[0]["source_row_ids"]) == 2


def test_name_standard_id_is_the_declared_tuple(tmp_path, name_standard_table):
    """The id digests (chamber, ordinal, first_office_key, first_period, key).

    Ruling C put ``collision_ordinal`` inside the tuple for EVERY row, so the
    reconstruction below needs nothing but the spine row and its anchor span.
    """

    world = five_person_rekey_world(tmp_path)
    out = world.build_ok()
    anchors: dict[str, tuple] = {}
    for span in out[bs.SPAN_FILE]:
        ordering = (
            bs.period_bounds(span["chamber"], span["first_period"])[0].toordinal(),
            span["chamber"],
            span["office_key"],
        )
        found = anchors.get(span["spine_person_id"])
        if found is None or ordering < found[0]:
            anchors[span["spine_person_id"]] = (
                ordering,
                span["chamber"],
                span["office_key"],
                span["first_period"],
            )
    for row in out[bs.SPINE_FILE]:
        _ordering, chamber, office_key, first_period = anchors[row["spine_person_id"]]
        assert row["collision_ordinal"] == 1
        assert row["spine_person_id"] == "hill:person:" + bs.digest_of(
            {
                "chamber": chamber,
                "collision_ordinal": row["collision_ordinal"],
                "first_office_key": office_key,
                "first_period": first_period,
                "name_key": row["name_key"],
            }
        )
    # Ruling A: the row is named from the raw it was KEYED from.
    for row in out[bs.SPINE_FILE]:
        parsed = bs.load_name_standard().parse_name(
            row["payee_raw"],
            bs.name_standard_source(row["chambers"][0], row["payee_raw"]),
        )
        table, _ = bs.load_name_standard().load_class_table()
        assert bs.load_name_standard().name_key(parsed, table=table) == row["name_key"]


def test_name_standard_receipt_invariants_and_suffix_recovery(
    tmp_path, name_standard_table
):
    world = five_person_rekey_world(tmp_path)
    world.name_standard = False
    default = world.build_ok("default")
    world.name_standard = True
    world.name_standard_baseline = default["output_root"]
    out = world.build_ok("rekeyed")
    block = out["receipt"]["name_standard"]

    # Ruling A: the two key routes agree on every one of these five, so the
    # histogram is EMPTY -- not absent, and not a zero.
    assert block["key_source_disagreements"] == {}
    assert block["key_source_disagreement_people"] == 0
    assert block["canonical_promotions"] == 0
    assert block["regrouping"] is False
    assert block["spine_persons_before"] == 5
    assert block["id_map_rows"] == 5
    assert block["merge_groups_count"] == 1
    assert block["merge_people_in_groups"] == 2
    assert block["merge_ids_removed"] == 1
    assert block["keys_changed"] + block["keys_unchanged"] == 5
    assert block["reason_counts"] == {
        "ascii_punct": 1,
        "merged": 2,
        "suffix": 1,
        "unchanged": 1,
    }
    # Ruling B: the histogram is the one the bound report states, and no
    # person's own raws resolve differently from their triple's population.
    assert block["cause_counts"] == FIVE_PERSON_CAUSE_HISTOGRAM
    assert block["delta_reconstruction_cause_counts"] == FIVE_PERSON_CAUSE_HISTOGRAM
    assert block["delta_residuals_count"] == 0
    assert block["delta_agreement"]["bound"] is True
    assert (
        block["delta_agreement"]["causes_differing_by_more_than_the_residual_count"]
        == []
    )
    # Ruling E: no person's first_class is empty.
    assert block["empty_first_class_count"] == 0

    baseline = block["baseline"]
    assert baseline["bound"] is True
    assert baseline["input_sha256_identical"] is True
    assert baseline["every_baseline_id_in_the_map_exactly_once"] is True
    assert baseline["spine_persons_equals_baseline_minus_merges"] is True
    # Ruling C: the two merged people shared an office and a period, so their
    # two spans became one and the baseline count is short by exactly that.
    assert baseline["person_office_spans"] == 5
    assert baseline["person_office_spans_unioned"] == 1
    assert baseline["person_office_spans_equal_baseline_minus_unioned"] is True
    assert baseline["member_office_index_rows_conserved"] is True
    assert baseline["observations_conserved"] is True

    # The suffix the payee key triple threw away is back on the row, and the
    # two suffix populations are counted apart.
    by_name = {row["name_key"]: row for row in out[bs.SPINE_FILE]}
    daly = by_name["daly|robert|"]
    assert daly["payee_key"]["suffix"] == "JR"
    assert daly["suffix_observed"] == ["JR"]
    assert daly["name_standard_parts"]["suffix"] == "JR"
    assert daly["display_name"] == "Bob Daly Jr."
    assert daly["payee_raw"] == "DALY-JR, BOB"
    assert block["rows_with_a_suffix_from_payee_key_lift"] == 1
    assert block["rows_with_a_suffix_from_raw_parse"] == 1


def test_name_standard_generation_verifies(tmp_path, name_standard_table):
    """The verifier re-derives the re-key independently and passes."""

    world = five_person_rekey_world(tmp_path)
    outcome = world.build_pair_and_verify("ns")
    assert outcome["code"] == 0, outcome["result"]["failures"]
    result = outcome["result"]
    assert result["status"] == "PASS", result["failures"]
    for key in (
        "id_map_has_one_row_per_previous_person",
        "id_map_targets_are_exactly_the_spine_ids",
        "every_spine_row_carries_its_previous_ids",
        "spine_name_key_matches_the_id_map",
        "every_id_reconstructs_from_its_anchor_span_and_name_key",
        "receipt_name_standard_arithmetic_holds",
        "rederived_rows_equal_emitted_rows",
        "primary_and_twin_byte_identical",
    ):
        assert result["assertions"][key] is True, key


def test_name_standard_merged_person_still_links_under_both_spellings(
    tmp_path, name_standard_table
):
    """A merge must not cost the LDA join one of the two names it folded."""

    world = five_person_rekey_world(tmp_path)
    world.h2 = [
        {
            "lda_source_person_id": "lda:lobbyist:1",
            "payroll_support_digest": "a" * 64,
            "display_name": "JAMES SMITH",
            "payroll_payee_raw": "SMITH JAMES",
            "employing_office_candidate": "HON. ALPHA BETA",
        },
        {
            "lda_source_person_id": "lda:lobbyist:2",
            "payroll_support_digest": "b" * 64,
            "display_name": "JAMIE SMITH",
            "payroll_payee_raw": "SMITH JAMIE",
            "employing_office_candidate": "HON. ALPHA BETA",
        },
    ]
    out = world.build_ok()
    links = {row["lda_source_person_id"]: row for row in out[bs.LDA_LINK_FILE]}
    assert links["lda:lobbyist:1"]["link_status"] == "LINKED_BY_PAYROLL_KEY"
    assert links["lda:lobbyist:2"]["link_status"] == "LINKED_BY_PAYROLL_KEY"
    # Both spellings resolve, and they resolve to the SAME merged person.
    assert (
        links["lda:lobbyist:1"]["spine_person_id"]
        == links["lda:lobbyist:2"]["spine_person_id"]
    )


# ---------------------------------------------------------------------------
# Lane-owner rulings A, B, C and E (2026-09-07).
# ---------------------------------------------------------------------------
def test_ruling_a_the_key_comes_from_the_raw_not_from_the_payee_key_lift(
    tmp_path, name_standard_table
):
    """A bare V the builder's own tokeniser deleted reaches the key.

    ``payroll_payee_key`` still treats a trailing "V" as a Roman numeral and
    drops it, so the stored triple is ("TOMMASINI", "JOHN", None) and no
    function of that triple can put the V back.  Under ruling A the key is the
    RAW parse, which reads it as a middle initial -- and the distance between
    the two routes is now a receipt histogram rather than a build failure.
    """

    world = World(tmp_path)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    office = "2016 HON. ALPHA BETA"
    world.add_ledger("2016Q1", office, "TOMMASINI, JOHN V", "COUNSEL")
    world.add_ledger("2016Q1", office, "ROE MARY", "SCHEDULER")
    world.name_standard = True
    world.name_standard_delta_report = write_delta_report(
        tmp_path / "delta.json", {"v_initial": 1}, 1
    )
    out = world.build_ok()

    assert bs.payroll_payee_key("TOMMASINI, JOHN V") == ("tommasini", "john", None)
    by_key = {row["name_key"]: row for row in out[bs.SPINE_FILE]}
    assert "tommasini|john|v" in by_key, sorted(by_key)
    assert by_key["tommasini|john|v"]["payee_raw"] == "TOMMASINI, JOHN V"

    block = out["receipt"]["name_standard"]
    # The gate became a histogram, and the histogram names the cause.
    assert block["key_source_disagreements"] == {"v_initial": 1}
    assert block["key_source_disagreement_people"] == 1
    assert block["cause_counts"] == {"v_initial": 1}
    assert out["receipt"]["status"] == "PASS"
    assert out["receipt"]["failures"] == []
    example = block["key_source_disagreement_examples"][0]
    assert example["key_from_raw_parse"] == "tommasini|john|v"
    assert example["key_from_payee_key_lift"] == "tommasini|john|"
    assert example["causes"] == ["v_initial"]

    id_map = read_gz(out["output_root"] / bs.NAME_STANDARD_ID_MAP_FILE)
    moved = [row for row in id_map if row["key_v6"] == "tommasini|john|"]
    assert len(moved) == 1
    assert moved[0]["reason"] == "v_initial"
    assert moved[0]["causes"] == ["v_initial"]


def test_ruling_b_lists_every_delta_residual_and_stays_inside_the_allowance(
    tmp_path, name_standard_table
):
    """Where a person's own raws disagree with the triple's, both are reported.

    The read-only delta resolves ONE key per payee-key TRIPLE over the whole
    corpus; ruling A resolves per PERSON.  Two people share the triple here and
    are written differently, so the two answers differ for exactly one of them.
    That person is the residual, and the receipt names them.
    """

    world = World(tmp_path)
    world.roster = [
        ("A000001", "Alpha", "Beta", 2009, 2027),
        ("A000002", "Gamma", "Delta", 2009, 2027),
    ]
    left = "2016 HON. ALPHA BETA"
    right = "2016 HON. GAMMA DELTA"
    # Three recordings without the initial in one office, one WITH it in
    # another, in the SAME quarter -- so the two are two people, not one.
    world.add_ledger("2016Q1", left, "PEREZ, ROSA", "COUNSEL")
    world.add_ledger("2016Q2", left, "PEREZ, ROSA", "COUNSEL")
    world.add_ledger("2016Q3", left, "PEREZ, ROSA", "COUNSEL")
    world.add_ledger("2016Q1", right, "PEREZ, ROSA V", "COUNSEL")
    world.name_standard = True
    # The report is the TRIPLE-level answer: the initial is evidence, so both
    # people carry it there, and v_initial fires twice.
    world.name_standard_delta_report = write_delta_report(
        tmp_path / "delta.json", {"v_initial": 2}, 2
    )
    out = world.build_ok()
    block = out["receipt"]["name_standard"]

    assert len(out[bs.SPINE_FILE]) == 2
    assert block["cause_counts"] == {"v_initial": 1}
    assert block["delta_reconstruction_cause_counts"] == {"v_initial": 2}
    assert block["delta_residuals_count"] == 1
    assert block["people_on_an_ambiguous_triple"] == 2
    residual = block["delta_residuals"][0]
    assert residual["key_from_this_build"] == "perez|rosa|"
    assert residual["key_from_the_delta_reconstruction"] == "perez|rosa|v"
    assert residual["payee_raw_examples"] == ["PEREZ, ROSA"]
    assert residual["spine_person_id_legacy"].startswith("hill:person:")

    agreement = block["delta_agreement"]
    assert agreement["bound"] is True
    # v_initial differs by 1, which is exactly the residual count, so it is
    # inside the allowance; the RECONSTRUCTION matches the report exactly.
    assert agreement["by_cause"]["v_initial"] == {
        "this_build": 1,
        "the_delta_report": 2,
        "the_delta_reconstruction": 2,
    }
    assert agreement["causes_differing_by_more_than_the_residual_count"] == []
    assert agreement["causes_where_the_reconstruction_differs_from_the_report"] == []


def test_ruling_b_fails_when_the_report_disagrees_by_more_than_the_residuals(
    tmp_path, name_standard_table
):
    """A negative control: a wrong report is a FAILURE, not a warning."""

    world = five_person_rekey_world(tmp_path)
    world.name_standard_delta_report = write_delta_report(
        tmp_path / "wrong.json", {"ascii_punct": 99, "nickname_class": 2, "suffix": 1}, 3
    )
    code, output_root = world.build("wrong")
    payload = read_generation(output_root)
    assert code != 0
    assert "NAME_STANDARD_DELTA_CAUSE_HISTOGRAM_DISAGREES" in payload["receipt"][
        "failures"
    ]


def test_ruling_b_fails_when_no_delta_report_is_bound(tmp_path, name_standard_table):
    """The assertion cannot be skipped by leaving the report off."""

    world = five_person_rekey_world(tmp_path)
    world.name_standard_delta_report = None
    code, output_root = world.build("unbound")
    payload = read_generation(output_root)
    assert code != 0
    assert "NAME_STANDARD_DELTA_REPORT_NOT_BOUND" in payload["receipt"]["failures"]


def day_dated_world(root: Path, james: tuple[str, str], jamie: tuple[str, str]) -> World:
    """Five-person world with printed service dates on the two SMITH rows."""

    world = World(root)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    office = "2016 HON. ALPHA BETA"
    world.add_ledger(
        "2016Q1", office, "SMITH JAMES", "COUNSEL",
        service_start=james[0], service_end=james[1],
    )
    world.add_ledger(
        "2016Q1", office, "SMITH JAMIE", "COUNSEL",
        service_start=jamie[0], service_end=jamie[1],
    )
    world.add_ledger("2016Q1", office, "ROE MARY", "SCHEDULER")
    world.name_standard = True
    world.name_standard_delta_report = write_delta_report(
        root / "delta.json", {"nickname_class": 1}, 1
    )
    return world


def test_ruling_c_day_level_overlap_blocks_the_merge_and_the_ordinal_separates(
    tmp_path, name_standard_table
):
    """Two people in one office on the SAME DAYS are two people."""

    world = day_dated_world(
        tmp_path, ("2016-01-01", "2016-03-31"), ("2016-02-01", "2016-03-31")
    )
    out = world.build_ok()
    block = out["receipt"]["name_standard"]

    # Nothing merged: three payroll people stay three spine rows.
    assert len(out[bs.SPINE_FILE]) == 3
    assert block["merge_groups_count"] == 0
    assert block["merge_ids_removed"] == 0
    assert block["merges_blocked_pairs"] == 1
    blocked = block["merges_blocked"][0]
    assert blocked["basis"] == "day_level_service_overlap"
    assert blocked["name_key"] == "smith|jamie|"
    assert blocked["first_period"] == "2016Q1"
    assert len(blocked["pair"]) == 2

    # The two share a tuple, so the ORDINAL is what keeps their ids apart.
    smiths = [row for row in out[bs.SPINE_FILE] if row["name_key"] == "smith|jamie|"]
    assert len(smiths) == 2
    assert sorted(row["collision_ordinal"] for row in smiths) == [1, 2]
    assert len({row["spine_person_id"] for row in smiths}) == 2
    assert block["collision_ordinals_above_one"] == 1

    # The ordinal is inside the hash, and the id reconstructs with it.
    for row in smiths:
        span = [
            item
            for item in out[bs.SPAN_FILE]
            if item["spine_person_id"] == row["spine_person_id"]
        ][0]
        assert row["spine_person_id"] == "hill:person:" + bs.digest_of(
            {
                "chamber": span["chamber"],
                "collision_ordinal": row["collision_ordinal"],
                "first_office_key": span["office_key"],
                "first_period": span["first_period"],
                "name_key": row["name_key"],
            }
        )
    # Nothing was unioned, because nothing merged.
    assert out["receipt"]["counts"]["spans_unioned_after_merge"] == 0
    assert len(out[bs.SPAN_FILE]) == 3


def test_ruling_c_day_level_disjoint_service_lets_the_merge_through(
    tmp_path, name_standard_table
):
    """A within-quarter move is one person, and the merge says so."""

    world = day_dated_world(
        tmp_path, ("2016-01-01", "2016-02-15"), ("2016-02-16", "2016-03-31")
    )
    out = world.build_ok()
    block = out["receipt"]["name_standard"]

    assert len(out[bs.SPINE_FILE]) == 2
    assert block["merges_blocked_pairs"] == 0
    assert block["merge_groups_count"] == 1
    assert block["merge_groups"][0]["merge_basis"] == "same_period_day_level_disjoint"
    assert block["merge_basis_counts"] == {"same_period_day_level_disjoint": 1}
    assert block["collision_ordinals_above_one"] == 0
    # One office, one continuous stretch: one span over both observations.
    assert out["receipt"]["counts"]["spans_unioned_after_merge"] == 1
    merged_row = [
        row for row in out[bs.SPINE_FILE] if row["name_key"] == "smith|jamie|"
    ][0]
    spans = [
        row
        for row in out[bs.SPAN_FILE]
        if row["spine_person_id"] == merged_row["spine_person_id"]
    ]
    assert len(spans) == 1
    assert spans[0]["observation_count"] == 2
    assert spans[0]["date_precision"] == "DAY"
    assert spans[0]["core"]["start_latest"] == "2016-01-01"
    assert spans[0]["core"]["end_earliest"] == "2016-03-31"


def test_missing_day_dates_block_senate_same_period_variant(
    tmp_path, name_standard_table
):
    """Missing day dates cannot authorize merging distinct payee lines."""

    world = World(tmp_path)
    world.roster = [("S000001", "Kappa", "Iota", 2009, 2027)]
    office = "SENATOR KAPPA IOTA"
    world.add_senate("2021-04-01", office, "SMITH, JAMES", "COUNSEL")
    world.add_senate("2021-04-01", office, "SMITH, JAMIE", "COUNSEL")
    world.name_standard = True
    world.name_standard_delta_report = write_delta_report(
        tmp_path / "delta.json", {"nickname_class": 1}, 1
    )
    out = world.build_ok()
    block = out["receipt"]["name_standard"]

    assert len(out[bs.SPINE_FILE]) == 2
    assert block["merges_blocked_pairs"] == 1
    assert block["merge_groups_count"] == 0
    assert block["merges_blocked"][0]["basis"] == "same_period_variant_no_day_dates"
    assert sorted(row["collision_ordinal"] for row in out[bs.SPINE_FILE]) == [1, 2]
    assert len(out[bs.SPAN_FILE]) == 2
    assert sum(row["observation_count"] for row in out[bs.SPAN_FILE]) == 2
    assert out["receipt"]["counts"]["spans_unioned_after_merge"] == 0
    verified = world.build_pair_and_verify()
    assert verified["code"] == 0, verified["result"]["failures"]



def test_ruling_c_spans_union_only_when_the_windows_touch(
    tmp_path, name_standard_table
):
    """Overlapping or abutting windows become one span; a real gap stays two."""

    world = World(tmp_path)
    world.roster = [
        ("A000001", "Alpha", "Beta", 2009, 2027),
        ("A000002", "Gamma", "Delta", 2009, 2027),
    ]
    anchor_office = "2016 HON. ALPHA BETA"
    other_office = "2016 HON. GAMMA DELTA"
    # Both spellings start in the anchor office in the same quarter, so they
    # share the id tuple and merge.  In the OTHER office their windows are two
    # quarters apart, which is a real gap, not a continuation.
    world.add_ledger("2016Q1", anchor_office, "SMITH JAMES", "COUNSEL",
                     service_start="2016-01-01", service_end="2016-02-14")
    world.add_ledger("2016Q2", other_office, "SMITH JAMES", "COUNSEL")
    world.add_ledger("2016Q1", anchor_office, "SMITH JIM", "COUNSEL",
                     service_start="2016-02-15", service_end="2016-03-31")
    world.add_ledger("2017Q1", other_office, "SMITH JIM", "COUNSEL")
    world.name_standard = True
    world.name_standard_delta_report = write_delta_report(
        tmp_path / "delta.json", {"nickname_class": 2}, 2
    )
    out = world.build_ok()

    assert len(out[bs.SPINE_FILE]) == 1
    row = out[bs.SPINE_FILE][0]
    assert row["name_key"] == "smith|jamie|"
    # Four office nodes became three spans: the two anchor-office nodes are one
    # stretch, the two other-office nodes are two.
    assert out["receipt"]["counts"]["spans_unioned_after_merge"] == 1
    assert row["span_count"] == 3
    assert len(out[bs.SPAN_FILE]) == 3
    assert row["office_count"] == 2
    by_office: dict[str, list[dict]] = {}
    for span in out[bs.SPAN_FILE]:
        by_office.setdefault(span["office_key"], []).append(span)
    sizes = sorted(len(items) for items in by_office.values())
    assert sizes == [1, 2]
    # Conservation: no observation was lost or double-counted by the union.
    assert sum(span["observation_count"] for span in out[bs.SPAN_FILE]) == 4
    assert out["receipt"]["counts"]["person_office_spans_with_touching_windows"] == 0
    # Both spellings still reach the joins.
    assert sorted(
        variant["first"] for variant in row["payee_key_legacy_variants"]
    ) == ["james", "jim"]


def test_ruling_c_the_verifier_rederives_a_blocked_merge_and_its_ordinals(
    tmp_path, name_standard_table
):
    """The twin re-derives the guard, the ordinals and the histograms."""

    world = day_dated_world(
        tmp_path, ("2016-01-01", "2016-03-31"), ("2016-02-01", "2016-03-31")
    )
    outcome = world.build_pair_and_verify("blocked")
    result = outcome["result"]
    assert outcome["code"] == 0, result["failures"]
    assert result["status"] == "PASS", result["failures"]
    for key in (
        "every_id_reconstructs_from_its_anchor_span_and_name_key",
        "receipt_name_standard_key_source_histogram_rederives",
        "receipt_name_standard_cause_histograms_rederive",
        "receipt_name_standard_delta_residuals_within_allowance",
        "receipt_name_standard_delta_report_agrees",
        "receipt_name_standard_merge_guard_rederives",
        "receipt_spans_unioned_rederives",
        "no_person_office_holds_two_touching_span_windows",
        "receipt_name_standard_no_empty_first_class",
        "rederived_rows_equal_emitted_rows",
        "primary_and_twin_byte_identical",
    ):
        assert result["assertions"][key] is True, key
    detail = result["detail"]["name_standard"]
    assert detail["merges_blocked_pairs_rederived"] == 1
    assert detail["collision_ordinals_above_one"] == 1
    assert detail["spans_unioned_rederived"] == 0


def test_ruling_c_the_verifier_rederives_a_union_and_a_gap(
    tmp_path, name_standard_table
):
    """The twin re-derives the span union, including where it must NOT fire."""

    world = World(tmp_path)
    world.roster = [
        ("A000001", "Alpha", "Beta", 2009, 2027),
        ("A000002", "Gamma", "Delta", 2009, 2027),
    ]
    anchor_office = "2016 HON. ALPHA BETA"
    other_office = "2016 HON. GAMMA DELTA"
    world.add_ledger("2016Q1", anchor_office, "SMITH JAMES", "COUNSEL",
                     service_start="2016-01-01", service_end="2016-02-14")
    world.add_ledger("2016Q2", other_office, "SMITH JAMES", "COUNSEL")
    world.add_ledger("2016Q1", anchor_office, "SMITH JIM", "COUNSEL",
                     service_start="2016-02-15", service_end="2016-03-31")
    world.add_ledger("2017Q1", other_office, "SMITH JIM", "COUNSEL")
    world.name_standard = True
    world.name_standard_delta_report = write_delta_report(
        tmp_path / "delta.json", {"nickname_class": 2}, 2
    )
    outcome = world.build_pair_and_verify("union")
    result = outcome["result"]
    assert outcome["code"] == 0, result["failures"]
    assert result["status"] == "PASS", result["failures"]
    assert result["assertions"]["receipt_spans_unioned_rederives"] is True
    assert result["assertions"]["rederived_rows_equal_emitted_rows"] is True
    assert result["detail"]["name_standard"]["spans_unioned_rederived"] == 1


def test_ruling_e_an_empty_first_class_is_attributed_and_fatal(
    tmp_path, name_standard_table, monkeypatch
):
    """Negative control: the gate fires, names the person, and fails the build.

    ``payroll_payee_key`` needs two tokens, so no payroll row can actually
    produce an empty given name; the gate exists so that a future change to the
    class table or to the fold cannot make one disappear in silence.  Forcing
    ``canonical_first`` to return nothing is the only way to reach it.
    """

    standard = bs.load_name_standard()
    monkeypatch.setattr(standard, "canonical_first", lambda first, table=None: "")
    world = five_person_rekey_world(tmp_path)
    world.name_standard_delta_report = write_delta_report(
        tmp_path / "empty.json", {"ascii_punct": 2, "suffix": 1}, 3
    )
    code, output_root = world.build("empty_first_class")
    payload = read_generation(output_root)
    assert code != 0
    assert "NAME_STANDARD_EMPTY_FIRST_CLASS" in payload["receipt"]["failures"]
    block = payload["receipt"]["name_standard"]
    assert block["empty_first_class_count"] > 0
    attributed = block["empty_first_class"][0]
    assert attributed["spine_person_id"].startswith("hill:person:")
    assert attributed["payee_raw"]


def test_ruling_e_the_verifier_has_its_own_raw_example_cap(tmp_path):
    """The payee-raw cap is not the office-raw cap wearing a different hat."""

    assert vs.NAME_STANDARD_MAX_RAW_EXAMPLES == bs.NAME_STANDARD_MAX_RAW_EXAMPLES
    assert "NAME_STANDARD_MAX_RAW_EXAMPLES" in vars(vs)
    assert "MAX_OFFICE_RAW_EXAMPLES" in vars(vs)


def test_ruling_e_legacy_payee_keys_is_not_a_silent_defaultdict(tmp_path):
    """An unknown person id is a KeyError on both sides, not an empty list."""

    deriver = object.__new__(vs.Deriver)
    deriver.legacy_payee_keys = {}
    with pytest.raises(KeyError):
        deriver.legacy_payee_keys["hill:person:" + "0" * 64]


def test_name_standard_shipped_class_table_loads(tmp_path):
    """The table the re-key actually keys on is present and non-empty."""

    standard = bs.load_name_standard()
    standard.reset_class_table_cache()
    table, loaded = standard.load_class_table()
    standard.reset_class_table_cache()
    assert loaded is True
    assert len(table) > 100
    assert standard.class_table_path().is_file()


# ---------------------------------------------------------------------------
# observed_periods / observed_period_count / contiguous_runs (2026-09-07)
#
# A span's first_period and last_period are a min and a max, so a person seen
# in four scattered quarters reads as one unbroken stretch.  These three
# additive fields carry the observations themselves.  The tests below fix the
# values on the builder side and, for each statement the verifier makes about
# them, use a tamper that violates that statement and nothing else.
# ---------------------------------------------------------------------------
def gapped_house_world(root: Path) -> World:
    """One person, one office, seen 2016Q1-Q2 and 2017Q1-Q2 -- two runs."""

    world = World(root)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    for quarter in ("2016Q1", "2016Q2", "2017Q1", "2017Q2"):
        world.add_ledger(quarter, "2016 HON. ALPHA BETA", "SMITH JANE", "COUNSEL")
    return world


def tamper_span_rows(source: Path, destination: Path, mutate) -> None:
    """Copy a generation, mutate its span rows, restamp the file block.

    Same discipline as :func:`promote_one_span_row`: bytes, rows and sha256 stay
    self-consistent and primary and twin stay byte-identical, so a verifier FAIL
    can only be the mutation.
    """

    shutil.copytree(source, destination)
    path = destination / bs.SPAN_FILE
    rows = read_gz(path)
    assert rows, "fixture must emit at least one span row"
    mutate(rows)
    bs.write_ndjson_gz(path, rows)
    receipt_path = destination / bs.RECEIPT_FILE
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["files"][bs.SPAN_FILE] = {
        "bytes": path.stat().st_size,
        "rows": len(rows),
        "sha256": bs.sha(path),
    }
    bs.write_json_atomic(receipt_path, receipt)


def verify_tampered(tmp_path: Path, clean: dict, tag: str, mutate) -> dict:
    """Apply ``mutate`` to both halves of a clean pair and re-verify."""

    primary = tmp_path / f"{tag}_primary"
    twin = tmp_path / f"{tag}_twin"
    tamper_span_rows(clean["primary"], primary, mutate)
    tamper_span_rows(clean["twin"], twin, mutate)
    report = tmp_path / f"{tag}_verification"
    code = vs.main(
        [
            "--primary-root",
            str(primary),
            "--twin-root",
            str(twin),
            "--report-root",
            str(report),
        ]
    )
    result = json.loads((report / vs.VERIFICATION_FILE).read_text(encoding="utf-8"))
    assert code == 1
    assert result["status"] == "FAIL"
    # The tamper is the finding, not a bookkeeping artefact.
    assert result["assertions"]["receipt_file_block_matches_disk"] is True
    assert result["assertions"]["primary_and_twin_byte_identical"] is True
    return result


def test_observed_periods_are_the_periods_not_the_min_to_max_window(tmp_path):
    """The window is six quarters wide.  The person was seen in four."""

    out = gapped_house_world(tmp_path).build_ok()
    assert len(out[bs.SPAN_FILE]) == 1
    span = out[bs.SPAN_FILE][0]
    # first_period and last_period are untouched: downstream reads them.
    assert span["first_period"] == "2016Q1"
    assert span["last_period"] == "2017Q2"
    assert span["periods_observed"] == 4
    assert span["observed_period_count"] == 4
    assert span["observed_periods"] == ["2016Q1", "2016Q2", "2017Q1", "2017Q2"]
    assert span["contiguous_runs"] == [["2016Q1", "2016Q2"], ["2017Q1", "2017Q2"]]
    assert span["contiguous"] is False
    # The longest RUN is two quarters; the min-to-max window is six.
    window = (
        bs.period_ordinal("house", "2017Q2")
        - bs.period_ordinal("house", "2016Q1")
        + 1
    )
    assert window == 6


def test_a_contiguous_span_is_exactly_one_run(tmp_path):
    """``contiguous`` and ``len(contiguous_runs) == 1`` are one statement."""

    world = World(tmp_path)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    for quarter in ("2016Q1", "2016Q2", "2016Q3"):
        world.add_ledger(quarter, "2016 HON. ALPHA BETA", "SMITH JANE", "COUNSEL")
    span = world.build_ok()[bs.SPAN_FILE][0]
    assert span["contiguous"] is True
    assert span["contiguous_runs"] == [["2016Q1", "2016Q3"]]
    assert span["observed_periods"] == ["2016Q1", "2016Q2", "2016Q3"]
    assert span["observed_period_count"] == span["periods_observed"] == 3


def test_senate_runs_step_by_half_year_not_by_quarter(tmp_path):
    """The run calendar is the CHAMBER's, and the two chambers differ.

    Two Senate periods six months apart are CONSECUTIVE; a skipped half-year is
    a gap.  Under a quarter calendar the first pair would read as a gap, which
    is the mistake this test exists to catch.
    """

    world = World(tmp_path)
    world.roster = [("S000001", "Kappa", "Iota", 2009, 2027)]
    for start in ("2016-04-01", "2016-10-01", "2017-10-01"):
        world.add_senate(start, "SENATOR KAPPA IOTA", "SMITH, JANE", "COUNSEL")
    span = world.build_ok()[bs.SPAN_FILE][0]
    assert span["period_kind"] == "half_year"
    assert span["observed_periods"] == ["2016-04-01", "2016-10-01", "2017-10-01"]
    assert span["contiguous_runs"] == [
        ["2016-04-01", "2016-10-01"],
        ["2017-10-01", "2017-10-01"],
    ]
    assert span["contiguous"] is False
    assert span["observed_period_count"] == 3


def test_the_verifier_rederives_the_runs_and_passes_a_clean_generation(tmp_path):
    outcome = gapped_house_world(tmp_path).build_pair_and_verify("runs")
    result = outcome["result"]
    assert outcome["code"] == 0, result["failures"]
    assert result["status"] == "PASS", result["failures"]
    for key in (
        "every_span_carries_the_observed_period_fields",
        "span_observed_period_count_agrees_with_periods_observed",
        "span_contiguous_runs_cover_exactly_the_observed_periods",
        "span_contiguous_runs_are_maximal_and_non_empty",
        "span_contiguous_runs_lie_within_the_first_last_period_window",
        "span_contiguous_flag_agrees_with_the_run_count",
        "rederived_rows_equal_emitted_rows",
    ):
        assert result["assertions"][key] is True, key
    census = result["detail"]["observed_periods"]
    assert census["spans_with_more_than_one_run"] == 1
    assert census["longest_contiguous_run_periods"] == 2
    assert census["longest_first_to_last_window_periods"] == 6
    assert census["spans_by_run_count"] == {"spans_with_2_runs": 1}


def test_a_run_that_drops_a_period_makes_the_verifier_fail(tmp_path):
    clean = gapped_house_world(tmp_path).build_pair_and_verify("cover")
    assert clean["code"] == 0, clean["result"]["failures"]

    def drop_a_period(rows):
        rows[0]["contiguous_runs"] = [["2016Q1", "2016Q1"], ["2017Q1", "2017Q2"]]

    result = verify_tampered(tmp_path, clean, "cover_bad", drop_a_period)
    assert (
        "SPAN_CONTIGUOUS_RUNS_DO_NOT_COVER_THE_OBSERVED_PERIODS" in result["failures"]
    )
    assert (
        result["assertions"]["span_contiguous_runs_cover_exactly_the_observed_periods"]
        is False
    )
    # The schema cannot see this: the shape is still two pairs of strings.
    assert result["assertions"]["every_row_validates_against_its_schema"] is True


def test_a_run_reaching_past_last_period_makes_the_verifier_fail(tmp_path):
    clean = gapped_house_world(tmp_path).build_pair_and_verify("window")
    assert clean["code"] == 0, clean["result"]["failures"]

    def reach_past_the_end(rows):
        rows[0]["contiguous_runs"] = [["2016Q1", "2016Q2"], ["2017Q1", "2018Q4"]]

    result = verify_tampered(tmp_path, clean, "window_bad", reach_past_the_end)
    assert "SPAN_CONTIGUOUS_RUNS_OUTSIDE_THE_SPAN_WINDOW" in result["failures"]
    assert (
        result["assertions"][
            "span_contiguous_runs_lie_within_the_first_last_period_window"
        ]
        is False
    )


def test_splitting_one_run_in_two_makes_the_verifier_fail(tmp_path):
    """Coverage alone is not enough: the runs must also be MAXIMAL.

    The split below covers exactly the same three quarters, in order, with
    nothing repeated -- so only the maximality check and the ``contiguous``
    cross-check can see it.
    """

    world = World(tmp_path)
    world.roster = [("A000001", "Alpha", "Beta", 2009, 2027)]
    for quarter in ("2016Q1", "2016Q2", "2016Q3"):
        world.add_ledger(quarter, "2016 HON. ALPHA BETA", "SMITH JANE", "COUNSEL")
    clean = world.build_pair_and_verify("maximal")
    assert clean["code"] == 0, clean["result"]["failures"]

    def split_the_run(rows):
        rows[0]["contiguous_runs"] = [["2016Q1", "2016Q2"], ["2016Q3", "2016Q3"]]

    result = verify_tampered(tmp_path, clean, "maximal_bad", split_the_run)
    assert "SPAN_CONTIGUOUS_RUNS_NOT_MAXIMAL_OR_EMPTY" in result["failures"]
    assert "SPAN_CONTIGUOUS_FLAG_DISAGREES_WITH_THE_RUN_COUNT" in result["failures"]
    assert (
        result["assertions"]["span_contiguous_runs_are_maximal_and_non_empty"] is False
    )
    assert (
        result["assertions"]["span_contiguous_flag_agrees_with_the_run_count"] is False
    )
    # The coverage check is silent, which is what makes this a separate check.
    assert (
        result["assertions"]["span_contiguous_runs_cover_exactly_the_observed_periods"]
        is True
    )


def test_a_count_that_disagrees_with_periods_observed_makes_the_verifier_fail(tmp_path):
    clean = gapped_house_world(tmp_path).build_pair_and_verify("count")
    assert clean["code"] == 0, clean["result"]["failures"]

    def bend_the_count(rows):
        rows[0]["observed_period_count"] = 3

    result = verify_tampered(tmp_path, clean, "count_bad", bend_the_count)
    assert "SPAN_OBSERVED_PERIOD_COUNT_MISMATCH" in result["failures"]
    assert (
        result["assertions"]["span_observed_period_count_agrees_with_periods_observed"]
        is False
    )


def test_a_span_that_drops_the_new_fields_makes_the_verifier_fail(tmp_path):
    """Optional in the SCHEMA, required by the VERIFIER.

    The fields are optional so that a generation built before they existed
    still validates; this generation is not one of those, and the verifier is
    the thing that says so.
    """

    clean = gapped_house_world(tmp_path).build_pair_and_verify("missing")
    assert clean["code"] == 0, clean["result"]["failures"]

    def strip_the_fields(rows):
        for field in ("observed_periods", "observed_period_count", "contiguous_runs"):
            rows[0].pop(field, None)

    result = verify_tampered(tmp_path, clean, "missing_bad", strip_the_fields)
    assert "SPAN_OBSERVED_PERIOD_FIELDS_MISSING" in result["failures"]
    assert result["assertions"]["every_span_carries_the_observed_period_fields"] is False
    # Optional means optional: the schema is content.
    assert result["assertions"]["every_row_validates_against_its_schema"] is True


def test_the_span_schema_keeps_the_three_fields_optional_but_typed(tmp_path):
    schema = json.loads(
        (vs.SCHEMA_DIR / "hill_person_office_span.schema.json").read_text(
            encoding="utf-8"
        )
    )
    for field in ("observed_periods", "observed_period_count", "contiguous_runs"):
        assert field in schema["properties"], field
        assert field not in schema["required"], field
    span = gapped_house_world(tmp_path).build_ok()[bs.SPAN_FILE][0]
    vs.validate_instance(span, schema)
    without = {
        key: value
        for key, value in span.items()
        if key not in ("observed_periods", "observed_period_count", "contiguous_runs")
    }
    vs.validate_instance(without, schema)
    for broken in (
        {"contiguous_runs": [["2016Q1"]]},
        {"contiguous_runs": [["2016Q1", "2016Q2", "2016Q3"]]},
        {"contiguous_runs": []},
        {"observed_periods": []},
        {"observed_period_count": 0},
    ):
        with pytest.raises(vs.SchemaValidationError):
            vs.validate_instance({**span, **broken}, schema)


if __name__ == "__main__":  # pragma: no cover - the runner, not a test
    # This file is a pytest module.  ``python test_hill_personnel_spine.py``
    # used to define every fixture and every test, run NOTHING, print NOTHING
    # and exit 0 -- which reads exactly like a clean pass, and is why a run of
    # it was reported as silent.  Hand the file to pytest instead and let its
    # own summary through, with pytest's exit code as this process's.
    raise SystemExit(
        pytest.main([str(Path(__file__).resolve()), "-q", "-p", "no:cacheprovider"])
    )
