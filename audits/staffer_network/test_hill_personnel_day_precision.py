from __future__ import annotations

from datetime import date

import build_hill_personnel_spine as spine


def test_bare_senate_committee_names_are_committees() -> None:
    for office in (
        "JUDICIARY",
        "HEALTH, EDUCATION, LABOR, AND PENSIONS",
        "HOMELAND SEC.& GOV AFF",
        "SELECT COM ON INTEL -",
    ):
        assert spine.container_kind_senate(office) == "committee"


def _observation(office: str, start: date, end: date) -> spine.Observation:
    return spine.Observation(
        lane=spine.LANE_HOUSE_LEDGER,
        chamber=spine.CHAMBER_HOUSE,
        period="2023Q1",
        office_raw=office,
        office_key=office,
        container_kind="member_office",
        payee_raw="HOLZBERG, GORDON E",
        payee_key=("HOLZBERG", "GORDON", "E"),
        title="LEGISLATIVE DIRECTOR",
        amount=1.0,
        row_id=f"{office}:{start.isoformat()}",
        shared_employee=False,
        ledger_office_key=office,
        ledger_container_kind="member_office",
        ledger_member_bioguide=None,
        service_start=start,
        service_end=end,
    )


def test_same_quarter_abutting_office_move_is_one_person() -> None:
    adams = spine.OfficeNode(
        chamber=spine.CHAMBER_HOUSE,
        office_key="HON:A000370",
        payee_key=("HOLZBERG", "GORDON", "E"),
        observations=[_observation("HON:A000370", date(2023, 1, 1), date(2023, 2, 9))],
    )
    sykes = spine.OfficeNode(
        chamber=spine.CHAMBER_HOUSE,
        office_key="HON:S001223",
        payee_key=("HOLZBERG", "GORDON", "E"),
        observations=[_observation("HON:S001223", date(2023, 2, 10), date(2023, 3, 31))],
    )

    clusters, shared, day_links, splits = spine.cluster_nodes([adams, sykes])
    assert len(clusters) == 1
    assert len(clusters[0]) == 2
    assert shared == 0
    assert day_links == 1
    assert splits == 0


def test_same_quarter_actual_overlap_remains_two_people() -> None:
    first = spine.OfficeNode(
        chamber=spine.CHAMBER_HOUSE,
        office_key="HON:ONE",
        payee_key=("SMITH", "ALEX", None),
        observations=[_observation("HON:ONE", date(2023, 1, 1), date(2023, 2, 10))],
    )
    second = spine.OfficeNode(
        chamber=spine.CHAMBER_HOUSE,
        office_key="HON:TWO",
        payee_key=("SMITH", "ALEX", None),
        observations=[_observation("HON:TWO", date(2023, 2, 10), date(2023, 3, 31))],
    )

    clusters, shared, day_links, splits = spine.cluster_nodes([first, second])
    assert len(clusters) == 2
    assert shared == 0
    assert day_links == 0
    assert splits == 1
