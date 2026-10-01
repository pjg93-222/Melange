# -*- coding: utf-8 -*-
"""Synthetic plain-assert tests for the generalized LDA rebuild."""

import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__)))); from paths import ROOT as MB_ROOT

import csv
import hashlib
import http.client
import io
import json
import math
import os
import random
import sys
import tempfile
import urllib.error
import zipfile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import build_network_2021_rebuild as BN
import assemble_association_items as AAI
import classify_bill_positions as BP
import collect_lda_filings as CLF
import fec_lda_bridge3_look as B3
import fec_lda_round4b_look as R4B
import lobby_champions as LC
import attention_vs_stance as AVS
import lobby_forecast as LF
import cosponsor_forecast as CF
import sector_spend as SS
import make_lobby_network_html as MLN
import historical_member_names as HMN


def _keys(text):
    parsed, _unparsed = BN.extract_bill_mentions(text)
    return [(item["type"], item["number"]) for item in parsed]


def test_bill_regex_formal_variants():
    cases = {
        "H.R. 1234": ("HR", 1234),
        "H.R.1234": ("HR", 1234),
        "HR 1234": ("HR", 1234),
        "HR1319": ("HR", 1319),
        "H R 1234": ("HR", 1234),
        "hr. 1234": ("HR", 1234),
        "H.R.\n1234": ("HR", 1234),
        "S. 567": ("S", 567),
        "S.567": ("S", 567),
        "s. 567": ("S", 567),
        "H.J.Res. 33": ("HJRES", 33),
        "H.J.Res.33": ("HJRES", 33),
        "H J Res 33": ("HJRES", 33),
        "HJRES 33": ("HJRES", 33),
        "h.j.resolution. 33": ("HJRES", 33),
        "S.J.Res. 34": ("SJRES", 34),
        "S J Resolution 34": ("SJRES", 34),
        "SJRES 34": ("SJRES", 34),
        "H.Con.Res. 35": ("HCONRES", 35),
        "H Con Res 35": ("HCONRES", 35),
        "HCONRES 35": ("HCONRES", 35),
        "H.Con.Resolution.35": ("HCONRES", 35),
        "S.Con.Res. 36": ("SCONRES", 36),
        "S Con Resolution 36": ("SCONRES", 36),
        "SCONRES 36": ("SCONRES", 36),
        "H.Res. 37": ("HRES", 37),
        "H Res 37": ("HRES", 37),
        "HRES 37": ("HRES", 37),
        "H Resolution 37": ("HRES", 37),
        "S.Res. 38": ("SRES", 38),
        "S Res 38": ("SRES", 38),
        "SRES 38": ("SRES", 38),
        "S Resolution 38": ("SRES", 38),
    }
    for text, expected in cases.items():
        assert _keys(text) == [expected], (text, _keys(text), expected)


def test_bill_regex_boundaries_multi_and_unparsed():
    for text in (
        "the SBA's 7(a) loan program",
        "U.S. 2020 Census data products",
        "24-hr 7-day staffing",
        "HR 50,000",
        "PL 117-2",
        "$1,234",
        "XHR 50",
        "HR 50A",
        "hr1319",
        "Hr 1319",
        "S 2021",
        "S1260",
        "S1",
    ):
        assert _keys(text) == [], (text, _keys(text))

    for text in (
        "the SBA's 7(a) loan program",
        "U.S. 2020 Census data products",
        "24-hr 7-day staffing",
    ):
        parsed, unparsed = BN.extract_bill_mentions(text)
        assert parsed == [] and unparsed == [], (text, parsed, unparsed)

    text = "(H.R. 9); [S.10] / H.J.Res.11, plus h.con.resolution 12."
    assert _keys(text) == [
        ("HR", 9),
        ("S", 10),
        ("HJRES", 11),
        ("HCONRES", 12),
    ]

    assert _keys("H.R. 1319, 1320 and 1321") == [
        ("HR", 1319),
        ("HR", 1320),
        ("HR", 1321),
    ]
    assert _keys("S. 1260 and 2321") == [("S", 1260), ("S", 2321)]
    assert _keys("H.R. 748,1319") == [("HR", 748), ("HR", 1319)]
    assert _keys("H.R. 1; 2") == [("HR", 1), ("HR", 2)]

    parsed, unparsed = BN.extract_bill_mentions(
        "Malformed formal refs HR-22, H.R.-23, and H.R. No. 25; "
        "valid H.R. 24."
    )
    assert [(item["type"], item["number"]) for item in parsed] == [
        ("HR", 24)
    ]
    assert [item["verbatim"] for item in unparsed] == [
        "HR-22",
        "H.R.-23",
        "H.R. No. 25",
    ]

    diagnostic_cases = {
        "H.R. 1,234": ["H.R. 1,234"],
        "H.R.\u201323": ["H.R.\u201323"],
        "S 2021": ["S 2021"],
        "S1260": ["S1260"],
        "hr1319": ["hr1319"],
    }
    for text, expected in diagnostic_cases.items():
        parsed, unparsed = BN.extract_bill_mentions(text)
        assert parsed == [], (text, parsed)
        assert [item["verbatim"] for item in unparsed] == expected

    parsed, unparsed = BN.extract_bill_mentions("S1")
    assert parsed == [] and unparsed == []


def _bill_xml(
    bioguide=None, sponsor_item=True, cosponsors=None, titles=None
):
    if not sponsor_item:
        sponsors = "<sponsors />"
    elif bioguide is None:
        sponsors = "<sponsors><item><fullName>Missing ID</fullName></item></sponsors>"
    else:
        sponsors = (
            "<sponsors><item><bioguideId>"
            + bioguide
            + "</bioguideId></item></sponsors>"
        )
    cosponsor_xml = ""
    if cosponsors is not None:
        cosponsor_xml = "<cosponsors>" + "".join(
            (
                "<item><bioguideId>"
                + cosponsor
                + "</bioguideId></item>"
            )
            if cosponsor is not None
            else "<item><fullName>Missing ID</fullName></item>"
            for cosponsor in cosponsors
        ) + "</cosponsors>"
    title_xml = ""
    if titles:
        title_xml = "<titles>" + "".join(
            "<item><titleType>"
            + title_type
            + "</titleType><title>"
            + title
            + "</title></item>"
            for title_type, title in titles
        ) + "</titles>"
    return (
        "<?xml version='1.0'?><billStatus><bill>"
        + sponsors
        + cosponsor_xml
        + title_xml
        + "</bill></billStatus>"
    ).encode("utf-8")


def test_sponsor_map_synthetic_billstatus():
    with tempfile.TemporaryDirectory() as fixture:
        for archive_token, _type_token in BN.ZIP_TYPES:
            path = os.path.join(
                fixture, f"BILLSTATUS-117-{archive_token}.zip"
            )
            with zipfile.ZipFile(path, "w") as archive:
                if archive_token == "hr":
                    archive.writestr(
                        "BILLSTATUS-117hr1.xml",
                        _bill_xml(
                            "A000001",
                            cosponsors=["B000002", "C000003"],
                            titles=[
                                (
                                    "Official Title as Introduced",
                                    "The Safe Banking Act of 2021",
                                ),
                                (
                                    "Short Title(s) as Passed House",
                                    "Safe Banking Act of 2021",
                                ),
                                (
                                    "Popular Titles",
                                    "Secure Finance Protection Act",
                                ),
                                ("Display Title", "Ignored Display Title"),
                            ],
                        ),
                    )
                    archive.writestr(
                        "BILLSTATUS-117hr2.xml",
                        _bill_xml(sponsor_item=False, cosponsors=[]),
                    )
                    archive.writestr(
                        "BILLSTATUS-117hr3.xml",
                        _bill_xml("D000004", cosponsors=[]),
                    )

        (
            bill_people_map,
            billstatus_keys,
            sponsorless_keys,
            title_index,
            title_receipts,
            receipts,
        ) = BN.load_sponsor_map(fixture)
        assert bill_people_map == {
            ("HR", 1, 117): {"A000001", "B000002", "C000003"},
            ("HR", 2, 117): set(),
            ("HR", 3, 117): {"D000004"},
        }
        assert billstatus_keys == {
            ("HR", 1, 117),
            ("HR", 2, 117),
            ("HR", 3, 117),
        }
        assert sponsorless_keys == {("HR", 2, 117)}
        assert title_index == {
            "SAFE BANKING ACT OF 2021": {("HR", 1, 117)},
            "SAFE BANKING ACT": {("HR", 1, 117)},
            "SECURE FINANCE PROTECTION ACT": {("HR", 1, 117)},
        }
        assert title_index.typed_titles_by_bill[("HR", 1, 117)] == {
            "short_title": ("Safe Banking Act of 2021",),
            "official_title": ("The Safe Banking Act of 2021",),
        }
        assert title_receipts == {
            "congress": 117,
            "titles_in_dictionary": 3,
            "titles_excluded_by_guard": 0,
        }
        assert receipts["xml_members"] == 3
        assert receipts["bills_mapped"] == 2
        assert receipts["bills_lacking_sponsor"] == 1
        assert receipts["bills_lacking_sponsor_refs"] == [
            "HR 2 (Congress 117)"
        ]
        assert "parse_failures" not in receipts
        assert BN.matched_bill_people_rows(
            billstatus_keys, bill_people_map
        ) == [
            {
                "type": "HR",
                "number": 1,
                "congress": 117,
                "people_set_size": 3,
            },
            {
                "type": "HR",
                "number": 2,
                "congress": 117,
                "people_set_size": 0,
            },
            {
                "type": "HR",
                "number": 3,
                "congress": 117,
                "people_set_size": 1,
            },
        ]

    try:
        BN._sponsor_for_member(
            io.BytesIO(_bill_xml()), "synthetic.zip", "bad.xml"
        )
        raised = False
    except BN.IngestError as exc:
        raised = "bill/sponsors/item/bioguideId" in str(exc)
    assert raised

    try:
        BN._bill_metadata_for_member(
            io.BytesIO(_bill_xml("A000001", cosponsors=[None])),
            "synthetic.zip",
            "bad-cosponsor.xml",
        )
        raised = False
    except BN.IngestError as exc:
        raised = "bill/cosponsors/item/bioguideId" in str(exc)
    assert raised


def _write_billstatus_congress(
    fixture,
    congress,
    members_by_archive,
    zip_types=None,
):
    zip_types = BN.ZIP_TYPES if zip_types is None else zip_types
    for archive_token, _type_token in zip_types:
        path = os.path.join(
            fixture, f"BILLSTATUS-{congress}-{archive_token}.zip"
        )
        with zipfile.ZipFile(path, "w") as archive:
            for number, xml_payload in sorted(
                members_by_archive.get(archive_token, {}).items()
            ):
                archive.writestr(
                    f"BILLSTATUS-{congress}{archive_token}{number}.xml",
                    xml_payload,
                )


def test_multi_congress_same_number_resolution():
    assert BN.parse_years("2021,2023,2026") == (2021, 2023, 2026)
    assert BN.congress_for_year(2021) == 117
    assert BN.congress_for_year(2022) == 117
    assert BN.congress_for_year(2023) == 118
    assert BN.congress_for_year(2024) == 118
    assert BN.congress_for_year(2025) == 119
    assert BN.congress_for_year(2026) == 119
    assert BN.congress_first_year(2022) == 2021
    assert BN.congress_first_year(2024) == 2023
    assert BN.congress_for_calendar_year(2019) == 116
    assert BN.congress_for_calendar_year(2020) == 116
    assert BN.congress_for_calendar_year(2017) == 115
    paths = BN.default_paths("C:\\fixture")
    assert BN.network_output_path(paths, 2023).endswith(
        "our_network_2023_generous.csv"
    )
    assert BN.network_output_path(paths, 2023, strict=True).endswith(
        "our_network_2023_strict.csv"
    )

    with tempfile.TemporaryDirectory() as fixture:
        congress_117 = os.path.join(fixture, "billstatus117")
        congress_118 = os.path.join(fixture, "billstatus118")
        os.makedirs(congress_117)
        os.makedirs(congress_118)
        _write_billstatus_congress(
            congress_117,
            117,
            {"hr": {1: _bill_xml("A000117", cosponsors=[])}},
        )
        _write_billstatus_congress(
            congress_118,
            118,
            {"hr": {1: _bill_xml("A000118", cosponsors=[])}},
        )
        people_117 = BN.load_sponsor_map(congress_117, 117)[0]
        people_118 = BN.load_sponsor_map(congress_118, 118)[0]
        assert people_117[("HR", 1, 117)] == {"A000117"}
        assert people_118[("HR", 1, 118)] == {"A000118"}
        cited_117 = {"lob-a": {("HR", 1, 117)}}
        cited_118 = {"lob-a": {("HR", 1, 118)}}
        assert BN.build_dyads(cited_117, people_117) == {
            ("lob-a", "A000117"): 1
        }
        assert BN.build_dyads(cited_118, people_118) == {
            ("lob-a", "A000118"): 1
        }


def test_title_normalization_guard_ambiguity_boundary_and_longest():
    assert BN.normalize_title("The SAFE-Banking Act, of 2021.") == (
        "SAFE BANKING ACT OF 2021"
    )
    assert BN.title_index_forms("The SAFE-Banking Act, of 2021.") == (
        "SAFE BANKING ACT OF 2021",
        "SAFE BANKING ACT",
    )

    guarded_index, guarded_receipts = BN.build_title_index(
        {("HR", 1, 117): ["CARES ACT"]}
    )
    assert guarded_index == {}
    assert guarded_receipts == {
        "titles_in_dictionary": 0,
        "titles_excluded_by_guard": 1,
    }

    companion_index, companion_receipts = BN.build_title_index(
        {
            ("HR", 5, 117): ["SAFE Banking Act"],
            ("S", 5, 117): ["Safe Banking Act"],
        }
    )
    assert companion_receipts == {
        "titles_in_dictionary": 1,
        "titles_excluded_by_guard": 0,
    }
    ambiguous = BN.match_bill_titles(
        "Support the SAFE Banking Act.", companion_index
    )
    assert ambiguous["bill_keys"] == {
        ("HR", 5, 117),
        ("S", 5, 117),
    }
    assert ambiguous["unique_matches"] == []
    assert ambiguous["ambiguous_matches"] == [
        {
            "verbatim": "SAFE Banking Act",
            "bill_keys": [
                {"type": "HR", "number": 5, "congress": 117},
                {"type": "S", "number": 5, "congress": 117},
            ],
        }
    ]
    assert BN.match_bill_titles(
        "Review the UNSAFE BANKING ACTION.", companion_index
    )["bill_keys"] == set()

    overlap_index, _receipts = BN.build_title_index(
        {
            ("HR", 10, 117): ["American Rescue Plan Act of 2021"],
            ("S", 10, 117): ["American Rescue Plan"],
        }
    )
    longest = BN.match_bill_titles(
        "Implement the American Rescue Plan Act of 2021.", overlap_index
    )
    assert longest["bill_keys"] == {("HR", 10, 117)}
    assert longest["unique_matches"] == [
        {
            "verbatim": "American Rescue Plan Act of 2021",
            "bill_keys": [
                {"type": "HR", "number": 10, "congress": 117}
            ],
        }
    ]
    assert longest["ambiguous_matches"] == []


def test_stale_citation_original_congress_and_strict_generous():
    segment = "S. 1587 / H.R. 2923, Inclusive Prosperity Act of 2019"
    with tempfile.TemporaryDirectory() as fixture:
        congress_116 = os.path.join(fixture, "billstatus116")
        congress_117 = os.path.join(fixture, "billstatus117")
        os.makedirs(congress_116)
        os.makedirs(congress_117)
        _write_billstatus_congress(
            congress_116,
            116,
            {
                "hr": {
                    2923: _bill_xml(
                        "A000116",
                        cosponsors=["B000116", "C000116"],
                    )
                },
                "s": {1587: _bill_xml("S000116", cosponsors=[])},
            },
            zip_types=BN.HISTORICAL_ZIP_TYPES,
        )
        _write_billstatus_congress(
            congress_117,
            117,
            {
                "hr": {
                    2923: _bill_xml("X000117", cosponsors=[]),
                    4000: _bill_xml(
                        "R000117",
                        cosponsors=[],
                        titles=[
                            (
                                "Official Title as Introduced",
                                "Inclusive Prosperity Act of 2021",
                            )
                        ],
                    ),
                }
            },
        )
        people_116 = BN.load_sponsor_map(congress_116, 116)[0]
        loaded_117 = BN.load_sponsor_map(congress_117, 117)
        people_117 = loaded_117[0]
        title_index = loaded_117[3]
        people_maps = {116: people_116, 117: people_117}

        resolved = BN.resolve_activity_mentions(
            segment, title_index, 2021, people_maps
        )
        historical_keys = {
            ("S", 1587, 116),
            ("HR", 2923, 116),
        }
        assert resolved["formal_keys"] == historical_keys
        assert resolved["credited_formal_keys"] == historical_keys
        assert {item["congress"] for item in resolved["parsed"]} == {116}
        assert resolved["generous_bill_keys"] == historical_keys | {
            ("HR", 4000, 117)
        }
        assert resolved["strict_bill_keys"] == historical_keys
        assert ("HR", 2923, 117) not in resolved["generous_bill_keys"]
        assert ("HR", 2923, 117) not in resolved["strict_bill_keys"]
        assert resolved["stale_unresolvable"] == []
        assert [
            item["resolved_congress"]
            for item in resolved["stale_citations"]
        ] == [116, 116]
        sizes = {
            (item["cited_key"]["type"], item["cited_key"]["number"]):
            item["credited_people_set_size"]
            for item in resolved["stale_citations"]
        }
        assert sizes == {("HR", 2923): 3, ("S", 1587): 1}
        for item in resolved["stale_citations"]:
            assert item["cited_key"]["congress"] == 116
            assert item["resolved_bill_key"]["congress"] == 116
            assert {
                row["congress"]
                for row in item[
                    "credited_people_set_sizes_generous"
                ]
            } == {116, 117}
            assert {
                row["congress"]
                for row in item["credited_people_set_sizes_strict"]
            } == {116}

        attribution_people = dict(people_116)
        attribution_people.update(people_117)
        generous_edges = BN.build_dyads(
            {"lob-a": resolved["generous_bill_keys"]},
            attribution_people,
        )
        strict_edges = BN.build_dyads(
            {"lob-a": resolved["strict_bill_keys"]},
            attribution_people,
        )
        dyad_rows = BN.per_dyad_bill_rows(
            BN.build_dyad_bill_sets(
                {"lob-a": resolved["generous_bill_keys"]},
                attribution_people,
            )
        )
        original_row = next(
            row for row in dyad_rows if row["bioguide"] == "A000116"
        )
        assert original_row["bill_keys"] == [
            {"type": "HR", "number": 2923, "congress": 116}
        ]
        assert ("lob-a", "X000117") not in generous_edges
        assert ("lob-a", "X000117") not in strict_edges
        assert ("lob-a", "R000117") in generous_edges
        assert ("lob-a", "R000117") not in strict_edges
        for bioguide in ("A000116", "B000116", "C000116", "S000116"):
            assert generous_edges[("lob-a", bioguide)] == 1
            assert strict_edges[("lob-a", bioguide)] == 1

        report_uuid = "11600000-0000-0000-0000-000000000001"
        _write_filing(
            os.path.join(fixture, report_uuid + ".json"),
            report_uuid,
            [segment],
        )
        filing_result = BN.parse_filings(
            [
                {
                    "report_uuid": report_uuid,
                    "lob_id": "lob-a",
                    "filing_year": 2021,
                    "is_no_activity": False,
                    "is_amendment": False,
                    "filing_period_code": "Q1",
                }
            ],
            fixture,
            title_index=title_index,
            bill_people_maps=people_maps,
        )
        assert filing_result["bills_by_lob"]["lob-a"] == (
            resolved["generous_bill_keys"]
        )
        assert len(filing_result["stale_citations"]) == 2
        assert {
            row["congress"]
            for row in filing_result["per_filing_mentions"][report_uuid][
                "parsed_bill_keys"
            ]
        } == {116}

        unsupported = BN.resolve_activity_mentions(
            "H.J.Res. 5 of 2019",
            title_index,
            2021,
            people_maps,
        )
        assert unsupported["generous_bill_keys"] == set()
        assert unsupported["strict_bill_keys"] == set()
        assert unsupported["stale_unresolvable"] == [
            {
                "verbatim_segment": "H.J.Res. 5 of 2019",
                "source_years": [2019],
                "filing_congress": 117,
                "resolved_congress": 116,
                "cited_key": {
                    "type": "HJRES",
                    "number": 5,
                    "congress": 116,
                },
                "reason": "unsupported_bill_type",
            }
        ]
        absent = BN.resolve_activity_mentions(
            "H.R. 9999 of 2019", title_index, 2021, people_maps
        )
        assert absent["stale_unresolvable"][0]["reason"] == (
            "bill_not_found"
        )
        unsupported_congress = BN.resolve_activity_mentions(
            "H.R. 5 of 2017", title_index, 2021, people_maps
        )
        assert unsupported_congress["stale_unresolvable"][0][
            "resolved_congress"
        ] == 115
        assert unsupported_congress["stale_unresolvable"][0][
            "reason"
        ] == "unsupported_congress"

    ambiguous_index = {
        "SAFE BANKING ACT": {
            ("HR", 1, 117),
            ("S", 1, 117),
        }
    }
    ambiguous = BN.resolve_activity_mentions(
        "Support the SAFE Banking Act", ambiguous_index, 2021, {}
    )
    assert ambiguous["generous_bill_keys"] == {
        ("HR", 1, 117),
        ("S", 1, 117),
    }
    assert ambiguous["strict_bill_keys"] == set()

    disambiguated = BN.resolve_activity_mentions(
        "H.R. 1, the SAFE Banking Act", ambiguous_index, 2021, {}
    )
    assert disambiguated["generous_bill_keys"] == {
        ("HR", 1, 117),
        ("S", 1, 117),
    }
    assert disambiguated["strict_bill_keys"] == {("HR", 1, 117)}


def test_multi_suffix_stale_citations_forward_binding():
    failing_input = (
        "Rules on plan fiduciaries responsibilities with respect to brokerage "
        "windows in 401(k)s and under ERISA. H.R.5282/S.2526, Retirement "
        "Enhancement and Savings Act of 2018. H.R. 1994 and Setting Every "
        "Community Up for Retirement Enhancement Act of 2019 (SECURE Act)."
    )
    with tempfile.TemporaryDirectory() as fixture:
        congress_115 = os.path.join(fixture, "billstatus115")
        congress_116 = os.path.join(fixture, "billstatus116")
        os.makedirs(congress_115)
        os.makedirs(congress_116)
        _write_billstatus_congress(
            congress_115,
            115,
            {
                "hr": {5282: _bill_xml("A000115", cosponsors=[])},
                "s": {2526: _bill_xml("B000115", cosponsors=[])},
            },
            zip_types=BN.HISTORICAL_ZIP_TYPES,
        )
        _write_billstatus_congress(
            congress_116,
            116,
            {"hr": {1994: _bill_xml("C000116", cosponsors=[])}},
            zip_types=BN.HISTORICAL_ZIP_TYPES,
        )
        people_115 = BN.load_sponsor_map(congress_115, 115)[0]
        people_116 = BN.load_sponsor_map(congress_116, 116)[0]
        people_maps = {115: people_115, 116: people_116}

        resolved = BN.resolve_activity_mentions(
            failing_input, {}, 2022, people_maps
        )
        expected_keys = {
            ("HR", 5282, 115),
            ("S", 2526, 115),
            ("HR", 1994, 116),
        }
        assert resolved["formal_keys"] == expected_keys
        assert resolved["credited_formal_keys"] == expected_keys
        assert resolved["strict_bill_keys"] == expected_keys
        assert resolved["stale_unresolvable"] == []
        assert all(
            item["verbatim_segment"] == failing_input
            for item in resolved["stale_citations"]
        )
        assert {
            (item["cited_key"]["type"], item["cited_key"]["number"]): (
                item["source_years"],
                item["resolved_congress"],
                item["credited_people_set_size"],
            )
            for item in resolved["stale_citations"]
        } == {
            ("HR", 5282): ([2018], 115, 1),
            ("S", 2526): ([2018], 115, 1),
            ("HR", 1994): ([2019], 116, 1),
        }
        attribution_people = dict(people_115)
        attribution_people.update(people_116)
        assert BN.build_dyads(
            {"lob-a": resolved["strict_bill_keys"]}, attribution_people
        ) == {
            ("lob-a", "A000115"): 1,
            ("lob-a", "B000115"): 1,
            ("lob-a", "C000116"): 1,
        }

        trailing_input = "...Act of 2019. Also supported H.R. 555"
        trailing = BN.resolve_activity_mentions(
            trailing_input, {}, 2022, people_maps
        )
        assert trailing["formal_keys"] == {("HR", 555, 117)}
        assert trailing["credited_formal_keys"] == {("HR", 555, 117)}
        assert trailing["strict_bill_keys"] == {("HR", 555, 117)}
        assert trailing["stale_citations"] == []
        assert trailing["stale_unresolvable"] == []
        assert {item["congress"] for item in trailing["parsed"]} == {117}

        single_suffix = BN.resolve_activity_mentions(
            "H.R. 1994 of 2019", {}, 2022, people_maps
        )
        assert single_suffix["credited_formal_keys"] == {("HR", 1994, 116)}
        assert single_suffix["stale_unresolvable"] == []
        assert single_suffix["stale_citations"][0]["source_years"] == [2019]

        unsupported_115 = BN.resolve_activity_mentions(
            "H.J.Res. 5 of 2018", {}, 2022, people_maps
        )
        assert unsupported_115["stale_unresolvable"][0][
            "resolved_congress"
        ] == 115
        assert unsupported_115["stale_unresolvable"][0]["reason"] == (
            "unsupported_bill_type"
        )


def _write_filing(path, report_uuid, descriptions=None, registrant="TEST REG"):
    payload = {
        "filing_uuid": report_uuid,
        "registrant": {"name": registrant},
        "lobbying_activities": [
            {"description": description}
            for description in (descriptions or [])
        ],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)


def test_distinct_bill_dyad_counting():
    with tempfile.TemporaryDirectory() as fixture:
        worklist = []
        descriptions = [
            "H.R. 1",
            "H.R.1",
            "HR 1 and H.R. 2 and H.R. 3",
        ]
        for index, description in enumerate(descriptions, start=1):
            report_uuid = f"00000000-0000-0000-0000-{index:012d}"
            worklist.append(
                {
                    "report_uuid": report_uuid,
                    "lob_id": "lob-a",
                    "is_no_activity": False,
                    "is_amendment": index == 2,
                    "filing_period_code": "Q1" if index < 3 else "Q2",
                }
            )
            _write_filing(
                os.path.join(fixture, report_uuid + ".json"),
                report_uuid,
                [description],
            )
        no_activity_uuid = "00000000-0000-0000-0000-000000000004"
        worklist.append(
            {
                "report_uuid": no_activity_uuid,
                "lob_id": "lob-a",
                "is_no_activity": True,
                "is_amendment": False,
                "filing_period_code": "Q3",
            }
        )
        _write_filing(
            os.path.join(fixture, no_activity_uuid + ".json"),
            no_activity_uuid,
        )

        parsed = BN.parse_filings(worklist, fixture)
        assert parsed["filings_parsed"] == 4
        assert parsed["no_activity_filings"] == 1
        assert parsed["amendment_filings"] == 1
        assert "union-of-versions" in BN.__doc__
        assert "latest-version-text" in BN.AMENDMENT_POLICY_NOTE
        assert parsed["activities"] == 3
        assert parsed["raw_mentions"] == 5
        assert parsed["distinct_bills"] == {
            ("HR", 1, 117),
            ("HR", 2, 117),
            ("HR", 3, 117),
        }
        assert parsed["bills_by_lob"] == {
            "lob-a": {
                ("HR", 1, 117),
                ("HR", 2, 117),
                ("HR", 3, 117),
            }
        }
        assert parsed["original_and_amendment_groups"] == [
            {
                "lob_id": "lob-a",
                "registrant": "TEST REG",
                "period": "Q1",
                "original_report_uuids": [
                    "00000000-0000-0000-0000-000000000001"
                ],
                "amendment_report_uuids": [
                    "00000000-0000-0000-0000-000000000002"
                ],
            }
        ]
        first_receipt = parsed["per_filing_mentions"][
            "00000000-0000-0000-0000-000000000001"
        ]
        assert first_receipt == {
            "lob_id": "lob-a",
            "parsed_bill_keys": [
                {"type": "HR", "number": 1, "congress": 117}
            ],
            "matched_titles": [],
            "unparsed_items": [],
        }

        bill_people_map = {
            ("HR", 1, 117): {"A000001", "B000002", "C000003"},
            ("HR", 2, 117): {"B000002", "D000004"},
            ("HR", 3, 117): {"E000005"},
        }
        assert BN.build_dyads(
            {"lob-single": {("HR", 1, 117)}}, bill_people_map
        ) == {
            ("lob-single", "A000001"): 1,
            ("lob-single", "B000002"): 1,
            ("lob-single", "C000003"): 1,
        }
        assert BN.build_dyads(
            parsed["bills_by_lob"], bill_people_map
        ) == {
            ("lob-a", "A000001"): 1,
            ("lob-a", "B000002"): 2,
            ("lob-a", "C000003"): 1,
            ("lob-a", "D000004"): 1,
            ("lob-a", "E000005"): 1,
        }
        dyad_sets = BN.build_dyad_bill_sets(
            parsed["bills_by_lob"], bill_people_map
        )
        assert BN.per_dyad_bill_rows(dyad_sets) == [
            {
                "lob_id": "lob-a",
                "bioguide": "A000001",
                "bill_keys": [
                    {"type": "HR", "number": 1, "congress": 117},
                ],
            },
            {
                "lob_id": "lob-a",
                "bioguide": "B000002",
                "bill_keys": [
                    {"type": "HR", "number": 1, "congress": 117},
                    {"type": "HR", "number": 2, "congress": 117},
                ],
            },
            {
                "lob_id": "lob-a",
                "bioguide": "C000003",
                "bill_keys": [
                    {"type": "HR", "number": 1, "congress": 117},
                ],
            },
            {
                "lob_id": "lob-a",
                "bioguide": "D000004",
                "bill_keys": [
                    {"type": "HR", "number": 2, "congress": 117},
                ],
            },
            {
                "lob_id": "lob-a",
                "bioguide": "E000005",
                "bill_keys": [
                    {"type": "HR", "number": 3, "congress": 117},
                ],
            }
        ]
        assert BN.matched_bill_people_rows(
            parsed["distinct_bills"], bill_people_map
        ) == [
            {
                "type": "HR",
                "number": 1,
                "congress": 117,
                "people_set_size": 3,
            },
            {
                "type": "HR",
                "number": 2,
                "congress": 117,
                "people_set_size": 2,
            },
            {
                "type": "HR",
                "number": 3,
                "congress": 117,
                "people_set_size": 1,
            },
        ]


def test_title_union_with_formal_is_distinct():
    with tempfile.TemporaryDirectory() as fixture:
        report_uuid = "00000000-0000-0000-0000-000000000101"
        record = {
            "report_uuid": report_uuid,
            "lob_id": "lob-title",
            "is_no_activity": False,
            "is_amendment": False,
            "filing_period_code": "Q1",
        }
        _write_filing(
            os.path.join(fixture, report_uuid + ".json"),
            report_uuid,
            [
                "H.R. 1, the SAFE Banking Act, and the Community Lending "
                "Protection Act."
            ],
        )
        title_index, _title_receipts = BN.build_title_index(
            {
                ("HR", 1, 117): ["Safe Banking Act"],
                ("HR", 2, 117): ["Community Lending Protection Act"],
            }
        )
        parsed = BN.parse_filings(
            [record], fixture, title_index=title_index
        )
        assert parsed["raw_mentions"] == 1
        assert parsed["distinct_bills"] == {
            ("HR", 1, 117),
            ("HR", 2, 117),
        }
        assert parsed["bills_by_lob"] == {
            "lob-title": {("HR", 1, 117), ("HR", 2, 117)}
        }
        assert parsed["per_filing_mentions"][report_uuid] == {
            "lob_id": "lob-title",
            "parsed_bill_keys": [
                {"type": "HR", "number": 1, "congress": 117}
            ],
            "matched_titles": [
                {
                    "verbatim": "Community Lending Protection Act",
                    "bill_keys": [
                        {"type": "HR", "number": 2, "congress": 117}
                    ],
                },
                {
                    "verbatim": "SAFE Banking Act",
                    "bill_keys": [
                        {"type": "HR", "number": 1, "congress": 117}
                    ],
                }
            ],
            "unparsed_items": [],
        }
        assert parsed["title_channel"] == {
            "filings_with_title_matches": 1,
            "unique_title_matches": 2,
            "ambiguous_title_matches": 0,
            "bills_added_by_title_channel": 1,
            "unique_matches": [
                {
                    "report_uuid": report_uuid,
                    "verbatim": "Community Lending Protection Act",
                    "bill_keys": [
                        {"type": "HR", "number": 2, "congress": 117}
                    ],
                },
                {
                    "report_uuid": report_uuid,
                    "verbatim": "SAFE Banking Act",
                    "bill_keys": [
                        {"type": "HR", "number": 1, "congress": 117}
                    ],
                }
            ],
            "ambiguous_matches": [],
        }
        assert BN.build_dyads(
            parsed["bills_by_lob"],
            {
                ("HR", 1, 117): {"A000001", "B000002"},
                ("HR", 2, 117): {"A000001"},
            },
        ) == {
            ("lob-title", "A000001"): 2,
            ("lob-title", "B000002"): 1,
        }


def test_per_activity_scope_congress_and_contradiction():
    with tempfile.TemporaryDirectory() as fixture:
        report_uuid = "10000000-0000-0000-0000-000000000001"
        record = {
            "report_uuid": report_uuid,
            "lob_id": "lob-a",
            "is_no_activity": False,
            "is_amendment": False,
            "filing_period_code": "Q1",
        }
        _write_filing(
            os.path.join(fixture, report_uuid + ".json"),
            report_uuid,
            [
                "Monitoring policy developments in the U.S.",
                "2021 highway program; work of the 116th Congress.",
                "H.R.",
                "1319",
                "H.R.\u201323",
            ],
        )
        title_index = {
            "U S 2021 HIGHWAY PROGRAM": {("S", 99, 117)}
        }
        parsed = BN.parse_filings(
            [record], fixture, title_index=title_index
        )
        assert parsed["distinct_bills"] == set()
        assert parsed["congress_context_mentions"] == [
            {"report_uuid": report_uuid, "matched_text": "116th Congress"}
        ]
        assert parsed["per_filing_mentions"][report_uuid] == {
            "lob_id": "lob-a",
            "parsed_bill_keys": [],
            "matched_titles": [],
            "unparsed_items": ["H.R.\u201323"],
        }

        bad_uuid = "10000000-0000-0000-0000-000000000002"
        bad_record = dict(record)
        bad_record.update(
            {"report_uuid": bad_uuid, "is_no_activity": True}
        )
        _write_filing(
            os.path.join(fixture, bad_uuid + ".json"),
            bad_uuid,
            ["H.R. 1"],
        )
        try:
            BN.parse_filings([bad_record], fixture)
            raised = False
        except BN.IngestError as exc:
            raised = "is_no_activity=true" in str(exc)
        assert raised


def test_sponsorless_intersection_receipt():
    bills_by_lob = {
        "lob-a": {("HR", 1, 117), ("HR", 2, 117)},
        "lob-b": {("HR", 2, 117), ("S", 3, 117)},
    }
    assert BN.mentioned_sponsorless_rows(
        bills_by_lob, {("HR", 2, 117), ("S", 99, 117)}
    ) == [
        {
            "type": "HR",
            "number": 2,
            "congress": 117,
            "lob_ids": ["lob-a", "lob-b"],
        }
    ]


def test_cross_comparison_arithmetic():
    their_edges = {
        ("lob-a", "A000001"): 2,
        ("lob-a", "B000002"): 1,
        ("lob-b", "D000004"): 4,
    }
    our_edges = {
        ("lob-a", "A000001"): 2,
        ("lob-a", "B000002"): 3,
        ("lob-b", "C000003"): 1,
    }
    result = BN.compare_edges(
        their_edges,
        our_edges,
        lob_ids={"lob-a", "lob-b", "lob-empty"},
    )
    assert result["totals"] == {
        "edges_theirs": 3,
        "edges_ours": 3,
        "common": 2,
        "exact_n_bills_matches": 1,
        "theirs_only": 1,
        "ours_only": 1,
    }
    assert [item["bioguide"] for item in result["common"]] == [
        "A000001",
        "B000002",
    ]
    assert [item["exact_match"] for item in result["common"]] == [
        True,
        False,
    ]
    assert result["theirs_only"] == [
        {"lob_id": "lob-b", "bioguide": "D000004", "n_theirs": 4}
    ]
    assert result["ours_only"] == [
        {"lob_id": "lob-b", "bioguide": "C000003", "n_ours": 1}
    ]
    empty = next(
        item
        for item in result["per_org_summary"]
        if item["lob_id"] == "lob-empty"
    )
    assert empty == {
        "lob_id": "lob-empty",
        "edges_theirs": 0,
        "edges_ours": 0,
        "common": 0,
        "exact_n_bills_matches": 0,
        "theirs_only": 0,
        "ours_only": 0,
    }


def test_collector_manifest_idempotency():
    with tempfile.TemporaryDirectory() as fixture:
        path = os.path.join(fixture, "uuid-1.json")
        data = b'{"lobbying_activities": []}'
        with open(path, "wb") as handle:
            handle.write(data)
        digest = hashlib.md5(data).hexdigest()
        manifest = {"md5": {"uuid-1": digest}}
        assert CLF.can_skip_existing(path, "uuid-1", manifest)
        assert not CLF.can_skip_existing(path, "uuid-2", manifest)
        assert not CLF.can_skip_existing(
            path, "uuid-1", {"md5": {"uuid-1": "0" * 32}}
        )
        with open(path, "ab") as handle:
            handle.write(b"\n")
        assert not CLF.can_skip_existing(path, "uuid-1", manifest)


def _collector_record(report_uuid, is_no_activity=False):
    return {
        "report_uuid": report_uuid,
        "is_no_activity": is_no_activity,
    }


def _collector_payload(report_uuid, descriptions=None):
    return {
        "filing_uuid": report_uuid,
        "lobbying_activities": [
            {"description": description}
            for description in (descriptions or [])
        ],
    }


def test_collector_schema_identity_and_resume_validation():
    report_uuid = "20000000-0000-0000-0000-000000000001"
    record = _collector_record(report_uuid)
    CLF.validate_filing_payload(_collector_payload(report_uuid), record)

    bad_payloads = [
        {"lobbying_activities": []},
        {"filing_uuid": report_uuid},
        {"filing_uuid": report_uuid, "lobbying_activities": None},
        _collector_payload(
            "20000000-0000-0000-0000-000000000002"
        ),
    ]
    for payload in bad_payloads:
        try:
            CLF.validate_filing_payload(payload, record)
            raised = False
        except CLF.IngestError:
            raised = True
        assert raised, payload

    no_activity_record = _collector_record(report_uuid, is_no_activity=True)
    CLF.validate_filing_payload(
        _collector_payload(report_uuid), no_activity_record
    )
    try:
        CLF.validate_filing_payload(
            _collector_payload(report_uuid, ["H.R. 1"]),
            no_activity_record,
        )
        raised = False
    except CLF.IngestError as exc:
        raised = "is_no_activity=true" in str(exc)
    assert raised

    with tempfile.TemporaryDirectory() as fixture:
        path = os.path.join(fixture, report_uuid + ".json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(bad_payloads[-1], handle)
        try:
            CLF.validate_existing_filing(path, record)
            raised = False
        except CLF.IngestError as exc:
            raised = "identity mismatch" in str(exc)
        assert raised


class _FakePacer:
    def __init__(self):
        self.calls = 0

    def wait(self):
        self.calls += 1


class _FakeResponse:
    def __init__(self, url, data=None, read_error=None):
        self.url = url
        self.data = data
        self.read_error = read_error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def geturl(self):
        return self.url

    def read(self):
        if self.read_error is not None:
            raise self.read_error
        return self.data


class _SequenceOpener:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.timeouts = []
        self.urls = []

    def __call__(self, request, timeout):
        self.timeouts.append(timeout)
        self.urls.append(request.full_url)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def test_collector_timeout_redirect_and_transient_retries():
    report_uuid = "20000000-0000-0000-0000-000000000003"
    url = CLF.API_BASE + report_uuid + "/"
    sleeps = []
    pacer = _FakePacer()
    opener = _SequenceOpener(
        [
            urllib.error.URLError("temporary"),
            _FakeResponse(url, data=b"{}"),
        ]
    )
    assert CLF.fetch_filing(
        report_uuid,
        {},
        pacer,
        opener=opener,
        sleep_fn=sleeps.append,
    ) == b"{}"
    assert opener.timeouts == [60, 60]
    assert sleeps == [1]
    assert pacer.calls == 2

    read_retry = _SequenceOpener(
        [
            _FakeResponse(
                url,
                read_error=http.client.IncompleteRead(b"partial", 10),
            ),
            _FakeResponse(url, data=b"complete"),
        ]
    )
    sleeps = []
    assert CLF.fetch_filing(
        report_uuid,
        {},
        _FakePacer(),
        opener=read_retry,
        sleep_fn=sleeps.append,
    ) == b"complete"
    assert sleeps == [1]

    server_retry = _SequenceOpener(
        [
            urllib.error.HTTPError(url, 500, "server", {}, None),
            _FakeResponse(url, data=b"recovered"),
        ]
    )
    sleeps = []
    assert CLF.fetch_filing(
        report_uuid,
        {},
        _FakePacer(),
        opener=server_retry,
        sleep_fn=sleeps.append,
    ) == b"recovered"
    assert sleeps == [1]

    redirect = _SequenceOpener(
        [_FakeResponse("https://example.invalid/filing", data=b"{}")]
    )
    try:
        CLF.fetch_filing(
            report_uuid, {}, _FakePacer(), opener=redirect
        )
        raised = False
    except CLF.IngestError as exc:
        raised = "redirect refused" in str(exc)
    assert raised

    not_found = _SequenceOpener(
        [urllib.error.HTTPError(url, 404, "missing", {}, None)]
    )
    sleeps = []
    try:
        CLF.fetch_filing(
            report_uuid,
            {},
            _FakePacer(),
            opener=not_found,
            sleep_fn=sleeps.append,
        )
        raised = False
    except CLF.IngestError as exc:
        raised = report_uuid in str(exc) and "404" in str(exc)
    assert raised and len(not_found.urls) == 1 and sleeps == []


def test_incremental_manifest_writer():
    with tempfile.TemporaryDirectory() as fixture:
        path = os.path.join(fixture, "manifest.json")
        CLF._write_manifest(path, 1, 0, [], {"uuid-1": "a"}, "worklist")
        CLF._write_manifest(
            path,
            2,
            0,
            [],
            {"uuid-1": "a", "uuid-2": "b"},
            "worklist",
        )
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        assert payload["fetched"] == 2
        assert payload["md5"] == {"uuid-1": "a", "uuid-2": "b"}
        assert payload["failures"] == []


def test_year_partitioned_resume_paths():
    with tempfile.TemporaryDirectory() as fixture:
        paths = CLF.default_paths(fixture)
        uuid_2021 = "21000000-0000-0000-0000-000000000001"
        primary_2021, candidates_2021 = CLF.filing_paths_for_record(
            paths,
            {"report_uuid": uuid_2021, "filing_year": 2021},
        )
        assert primary_2021 == os.path.join(
            paths["partitioned_filings_dir"], "2021", uuid_2021 + ".json"
        )
        assert candidates_2021 == (
            primary_2021,
            os.path.join(paths["filings_dir"], uuid_2021 + ".json"),
        )

        legacy_primary, legacy_candidates = CLF.filing_paths_for_record(
            paths,
            {"report_uuid": uuid_2021, "filing_year": 2021},
            legacy_output=True,
        )
        assert legacy_primary == os.path.join(
            paths["filings_dir"], uuid_2021 + ".json"
        )
        assert legacy_candidates == (legacy_primary, primary_2021)

        uuid_2023 = "23000000-0000-0000-0000-000000000001"
        primary_2023, candidates_2023 = CLF.filing_paths_for_record(
            paths,
            {"report_uuid": uuid_2023, "filing_year": 2023},
        )
        assert primary_2023 == os.path.join(
            paths["partitioned_filings_dir"], "2023", uuid_2023 + ".json"
        )
        assert candidates_2023 == (primary_2023,)


def test_sweep_page_validation():
    assert CLF.sweep_page_url(2024, 3) == (
        "https://lda.gov/api/v1/filings/"
        "?filing_year=2024&page=3&page_size=25"
    )
    nonfinal = {
        "results": [{"filing_year": 2024}, {"filing_year": "2024"}],
        "next": "https://lda.gov/api/v1/filings/?page=2",
    }
    assert CLF.validate_sweep_page(nonfinal, 2024, 1) is True
    assert CLF.validate_sweep_page(
        {"results": [], "next": None}, 2024, 2
    ) is False

    bad_pages = (
        ({"results": [], "next": "next"}, "empty results"),
        (
            {"results": [{"filing_year": 2023}], "next": None},
            "expected 2024",
        ),
        ({"results": [{}], "next": None}, "missing key filing_year"),
    )
    for payload, expected in bad_pages:
        try:
            CLF.validate_sweep_page(payload, 2024, 7)
            raised = False
        except CLF.IngestError as exc:
            raised = expected in str(exc)
        assert raised, (payload, expected)


def _full_worklist_record(report_uuid, filing_year=None):
    record = {
        "report_uuid": report_uuid,
        "lob_id": "lob-a",
        "filing_period_code": "Q1",
        "is_amendment": False,
        "is_no_activity": False,
        "filing_url": "https://lda.gov/filing/example/",
    }
    if filing_year is not None:
        record["filing_year"] = filing_year
    return record


def test_worklist_filing_year_validation():
    for module in (CLF, BN):
        assert module.validate_filing_year(2021, "0") == 2021
        assert module.validate_filing_year("2024", "0") == 2024
        for value in (2020, 2027, "2024 ", True):
            try:
                module.validate_filing_year(value, "7")
                raised = False
            except module.IngestError as exc:
                raised = "filing_year" in str(exc) and "7" in str(exc)
            assert raised, (module.__name__, value)

    with tempfile.TemporaryDirectory() as fixture:
        path = os.path.join(fixture, "worklist.json")
        report_uuid = "24000000-0000-0000-0000-000000000001"
        with open(path, "w", encoding="utf-8") as handle:
            json.dump([_full_worklist_record(report_uuid, "2024")], handle)
        collector_records, _digest = CLF.load_worklist(path)
        builder_records, _digest = BN.load_worklist(path)
        assert collector_records[0]["filing_year"] == 2024
        assert builder_records[0]["filing_year"] == 2024

        missing_path = os.path.join(fixture, "legacy.json")
        with open(missing_path, "w", encoding="utf-8") as handle:
            json.dump([_full_worklist_record(report_uuid)], handle)
        try:
            CLF.load_worklist(missing_path)
            raised = False
        except CLF.IngestError as exc:
            raised = "missing key filing_year" in str(exc)
        assert raised
        legacy_records, _digest = CLF.load_worklist(
            missing_path, legacy_default_year=2021
        )
        assert legacy_records[0]["filing_year"] == 2021


def test_strict_uuid_and_pinned_lob_scope():
    for module in (CLF, BN):
        valid = "30000000-0000-0000-0000-000000000001"
        assert module.validate_report_uuid(valid, "0") == valid
        try:
            module.validate_report_uuid("not-a-uuid", "7")
            raised = False
        except module.IngestError as exc:
            raised = "report_uuid" in str(exc) and "7" in str(exc)
        assert raised

    records = [
        {"lob_id": lob_id} for lob_id in sorted(BN.EXPECTED_LOB_IDS_2021)
    ]
    assert BN.validate_lob_id_scope(records) == BN.EXPECTED_LOB_IDS_2021
    pinned_lobs = sorted(BN.EXPECTED_LOB_IDS_2021)
    comparison_records = [
        {"lob_id": pinned_lobs[index % len(pinned_lobs)], "filing_year": 2021}
        for index in range(BN.EXPECTED_WORKLIST_RECORDS)
    ]
    assert BN.validate_2021_comparison_scope(comparison_records) is True
    wrong_year = [dict(record) for record in comparison_records]
    wrong_year[0]["filing_year"] = 2022
    try:
        BN.validate_2021_comparison_scope(wrong_year)
        raised = False
    except BN.IngestError as exc:
        raised = "non-2021" in str(exc)
    assert raised
    try:
        BN.validate_lob_id_scope(records[:-1])
        raised = False
    except BN.IngestError as exc:
        raised = "pinned 14" in str(exc)
    assert raised

    with tempfile.TemporaryDirectory() as fixture:
        path = os.path.join(fixture, "network.csv")
        lob_id = sorted(BN.EXPECTED_LOB_IDS_2021)[0]
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(BN.NETWORK_FIELDS)
            writer.writerow(["  " + lob_id + "  ", "A000001", 2021, 3])
        assert BN.load_their_edges(
            path, BN.EXPECTED_LOB_IDS_2021
        ) == {(lob_id, "A000001"): 3}


def test_worklist_boolean_normalization():
    for module in (CLF, BN):
        normalize = module.normalize_worklist_boolean
        assert normalize(True, "is_amendment", "0 (uuid-1)") is True
        assert normalize(False, "is_no_activity", "0 (uuid-1)") is False
        assert normalize("true", "is_amendment", "0 (uuid-1)") is True
        assert normalize("false", "is_no_activity", "0 (uuid-1)") is False
        for field, value in (
            ("is_amendment", "True"),
            ("is_no_activity", "FALSE"),
            ("is_no_activity", "yes"),
            ("is_amendment", 1),
        ):
            try:
                normalize(value, field, "7 (uuid-bad)")
                raised = False
            except module.IngestError as exc:
                message = str(exc)
                raised = field in message and "7 (uuid-bad)" in message
            assert raised, (module.__name__, field, value)


def test_bridge3_member_blocked_two_cycle_joint_move():
    records = []
    for cycle, offset in (("2023-2024", 0.0), ("2025-2026", 100.0)):
        for index, member in enumerate(("A", "B", "C"), start=1):
            records.append(
                {
                    "industry": "fintech",
                    "cycle": cycle,
                    "member": member,
                    "y": offset + index * 10.0,
                }
            )
    permuted = B3._member_blocked_y_permutation(
        records, random.Random(19)
    )
    by_target = {}
    for record, value in zip(records, permuted):
        by_target[(record["member"], record["cycle"])] = value
    for member in ("A", "B", "C"):
        assert (
            by_target[(member, "2025-2026")]
            - by_target[(member, "2023-2024")]
            == 100.0
        )


def test_bridge3_fractional_ranks_and_singleton_party_cell():
    ranked = B3.fractional_ranks([10, 10, 30])
    assert ranked == [1.0 / 3.0, 1.0 / 3.0, 5.0 / 6.0]
    records = [
        {
            "industry": "crypto",
            "cycle": "2023-2024",
            "party_name": "Republican",
            "volume_raw": 4,
        },
        {
            "industry": "crypto",
            "cycle": "2023-2024",
            "party_name": "Democrat",
            "volume_raw": 2,
        },
        {
            "industry": "crypto",
            "cycle": "2023-2024",
            "party_name": "Democrat",
            "volume_raw": 2,
        },
    ]
    values = B3.volume_within_party_fractional(records)
    assert values[0] == 0.5
    assert values[1:] == [0.5, 0.5]


def test_bridge3_committee_snapshot_parser():
    text = """HSBA:
  - name: Alice Example
    party: majority
    bioguide: A000001
HSBA07:
  - bioguide: B000002
HSBA01: []
SSBK:
  - bioguide: C000003
HSAG:
  - bioguide: D000004
"""
    parsed = B3.parse_committee_snapshot_text(text)
    assert parsed["HSBA01"] == set()
    assert B3.finance_committee_members(parsed) == {
        "A000001",
        "B000002",
        "C000003",
    }
    try:
        B3.parse_committee_snapshot_text(
            "HSBA:\n  - member: A000001\n"
        )
        raised = False
    except B3.IngestError as exc:
        raised = "malformed line" in str(exc)
    assert raised


def _bridge3_sweep_filing(
    filing_uuid,
    year,
    client_id="1",
    name="Example",
    senate_client_id=None,
):
    if senate_client_id is None:
        senate_client_id = "global-" + str(client_id)
    return {
        "filing_uuid": filing_uuid,
        "filing_year": year,
        "client": {
            "id": senate_client_id,
            "client_id": client_id,
            "name": name,
        },
        "lobbying_activities": [{"description": "Support H.R. 1"}],
    }


def test_bridge3_sweep_ingestion_duplicate_and_wrong_year():
    filing_uuid = "24000000-0000-0000-0000-000000000001"
    other_uuid = "24000000-0000-0000-0000-000000000002"
    with tempfile.TemporaryDirectory() as fixture:
        first = _bridge3_sweep_filing(filing_uuid, 2024)
        with open(
            os.path.join(fixture, "page_00001.json"), "w", encoding="utf-8"
        ) as handle:
            json.dump({"results": [first]}, handle)
        with open(
            os.path.join(fixture, "page_00002.json"), "w", encoding="utf-8"
        ) as handle:
            json.dump(
                {
                    "results": [
                        dict(first),
                        _bridge3_sweep_filing(other_uuid, 2024),
                    ]
                },
                handle,
            )
        scan = BN.scan_sweep_pages(fixture, 2024)
        receipt = scan["receipt"]
        assert receipt["filings"] == 2
        assert receipt["raw_filing_occurrences"] == 3
        duplicates = receipt["sweep_duplicate_filing_uuids"]
        assert duplicates == {"count": 1, "filing_uuids": [filing_uuid]}
        mismatches = receipt["sweep_duplicate_uuid_body_mismatch"]
        assert mismatches == {"count": 0, "filing_uuids": []}
        yielded = list(BN.iter_sweep_filings(scan["page_paths"], 2024))
        assert [payload["filing_uuid"] for payload in yielded] == [
            filing_uuid,
            other_uuid,
        ]
        network = BN.aggregate_sweep_network(
            scan["page_paths"],
            2024,
            {filing_uuid: "lob", other_uuid: "lob"},
            {},
            {},
        )
        assert network["receipts"]["filings"] == 2
        totals_inputs = list(
            BN.full_universe_payloads(
                2024, [], {}, scan["page_paths"]
            )
        )
        assert [item[0] for item in totals_inputs] == [
            filing_uuid,
            other_uuid,
        ]

    with tempfile.TemporaryDirectory() as fixture:
        first = _bridge3_sweep_filing(filing_uuid, 2024)
        changed = _bridge3_sweep_filing(filing_uuid, 2024)
        changed["lobbying_activities"][0]["description"] = "Support H.R. 999"
        with open(
            os.path.join(fixture, "page_00001.json"), "w", encoding="utf-8"
        ) as handle:
            json.dump({"results": [first]}, handle)
        with open(
            os.path.join(fixture, "page_00002.json"), "w", encoding="utf-8"
        ) as handle:
            json.dump({"results": [changed]}, handle)
        scan = BN.scan_sweep_pages(fixture, 2024)
        mismatch = scan["receipt"]["sweep_duplicate_uuid_body_mismatch"]
        assert mismatch == {"count": 1, "filing_uuids": [filing_uuid]}
        yielded = list(BN.iter_sweep_filings(scan["page_paths"], 2024))
        assert len(yielded) == 1
        assert yielded[0]["lobbying_activities"] == first[
            "lobbying_activities"
        ]

    with tempfile.TemporaryDirectory() as fixture:
        with open(
            os.path.join(fixture, "page_00001.json"), "w", encoding="utf-8"
        ) as handle:
            json.dump(
                {
                    "results": [
                        _bridge3_sweep_filing(filing_uuid, 2024)
                    ]
                },
                handle,
            )
        with open(
            os.path.join(fixture, "page_00002.json"), "w", encoding="utf-8"
        ) as handle:
            json.dump(
                {
                    "results": [
                        _bridge3_sweep_filing(other_uuid, 2024)
                    ]
                },
                handle,
            )
        receipt = BN.scan_sweep_pages(fixture, 2024)["receipt"]
        assert receipt["filings"] == 2
        assert receipt["raw_filing_occurrences"] == 2
        assert receipt["sweep_duplicate_filing_uuids"]["count"] == 0
        assert receipt["sweep_duplicate_uuid_body_mismatch"]["count"] == 0

    with tempfile.TemporaryDirectory() as fixture:
        with open(
            os.path.join(fixture, "page_00001.json"), "w", encoding="utf-8"
        ) as handle:
            json.dump(
                {"results": [_bridge3_sweep_filing(filing_uuid, 2023)]},
                handle,
            )
        try:
            BN.scan_sweep_pages(fixture, 2024)
            raised = False
        except BN.IngestError as exc:
            raised = "expected 2024" in str(exc)
        assert raised


def test_bridge3_client_attribution_and_near_miss_receipt():
    crosswalk = {
        "alpha": {"ALPHA FINANCIAL GROUP": "lob-alpha"},
        "beta": {"BETA CREDIT UNION": "lob-beta"},
    }
    harvested = {"lob-alpha": {"101"}, "lob-beta": {"202"}}
    id_hit = BN.attribute_sweep_filing(
        {
            "filing_uuid": "id-hit",
            "client": {"id": "101", "client_id": "12", "name": "Other"},
        },
        harvested,
        crosswalk=crosswalk,
    )
    assert id_hit["lob_id"] == "lob-alpha" and id_hit["client_id_match"]
    name_hit = BN.attribute_sweep_filing(
        {
            "filing_uuid": "name-hit",
            "client": {
                "id": "999",
                "client_id": "12",
                "name": "Alpha Financial Group",
            },
        },
        harvested,
        crosswalk=crosswalk,
    )
    assert name_hit["lob_id"] == "lob-alpha" and name_hit["exact_name_match"]
    try:
        BN.attribute_sweep_filing(
            {
                "filing_uuid": "ambiguous",
                "client": {
                    "id": "101",
                    "client_id": "12",
                    "name": "Beta Credit Union",
                },
            },
            harvested,
            crosswalk=crosswalk,
        )
        raised = False
    except BN.IngestError as exc:
        raised = "ambiguous pinned-org attribution" in str(exc)
    assert raised

    with tempfile.TemporaryDirectory() as fixture:
        near_name = "Alpha Financial Group Holdings"
        payload = _bridge3_sweep_filing(
            "24000000-0000-0000-0000-000000000002",
            2024,
            client_id="999",
            name=near_name,
        )
        with open(
            os.path.join(fixture, "page_00001.json"), "w", encoding="utf-8"
        ) as handle:
            json.dump({"results": [payload]}, handle)
        scan = BN.scan_sweep_pages(
            fixture,
            2024,
            harvested_client_ids=harvested,
            crosswalk=crosswalk,
        )
        assert scan["receipt"]["attribution"]["unmatched_near_names"] == [
            BN.normalize_client_name(near_name)
        ]


def test_bridge3_stable_client_id_harvest_and_collision():
    crosswalk = {
        "alpha": {"ALPHA FINANCIAL GROUP": "lob-alpha"},
        "beta": {"BETA CREDIT UNION": "lob-beta"},
    }
    worklist = [
        {"report_uuid": "alpha-1", "lob_id": "lob-alpha", "filing_year": 2023},
        {"report_uuid": "alpha-2", "lob_id": "lob-alpha", "filing_year": 2023},
        {"report_uuid": "beta-1", "lob_id": "lob-beta", "filing_year": 2023},
    ]
    payloads = {
        "alpha-1": {
            "client": {
                "id": 100,
                "client_id": 12,
                "name": "Alpha Financial Group",
            }
        },
        "alpha-2": {
            "client": {
                "id": 101,
                "client_id": 12,
                "name": "Alpha Financial Group",
            }
        },
        "beta-1": {
            "client": {
                "id": 200,
                "client_id": 12,
                "name": "Beta Credit Union",
            }
        },
    }
    with tempfile.TemporaryDirectory() as fixture:
        filing_paths = {}
        for filing_uuid, payload in payloads.items():
            path = os.path.join(fixture, filing_uuid + ".json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
            filing_paths[filing_uuid] = path
        harvested, receipt = BN.harvest_client_ids(
            worklist, filing_paths, crosswalk=crosswalk
        )
        assert harvested == {
            "lob-alpha": {"100", "101"},
            "lob-beta": {"200"},
        }
        assert receipt["counts_by_lob_id"] == {
            "lob-alpha": 2,
            "lob-beta": 1,
        }
        assert receipt[
            "registrant_scoped_client_ids_non_identifying_by_lob_id"
        ] == {"lob-alpha": ["12"], "lob-beta": ["12"]}
        assert receipt["identifying_client_key_field"] == "client.id"

        alpha = BN.attribute_sweep_filing(
            {
                "filing_uuid": "sweep-alpha",
                "client": {
                    "id": 100,
                    "client_id": 12,
                    "name": "Alpha Financial Group",
                },
            },
            harvested,
            crosswalk=crosswalk,
        )
        beta = BN.attribute_sweep_filing(
            {
                "filing_uuid": "sweep-beta",
                "client": {
                    "id": 200,
                    "client_id": 12,
                    "name": "Beta Credit Union",
                },
            },
            harvested,
            crosswalk=crosswalk,
        )
        assert alpha["lob_id"] == "lob-alpha"
        assert beta["lob_id"] == "lob-beta"

        collision_path = os.path.join(fixture, "beta-collision.json")
        with open(collision_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "client": {
                        "id": 100,
                        "client_id": 999,
                        "name": "Beta Credit Union",
                    }
                },
                handle,
            )
        try:
            BN.harvest_client_ids(
                [worklist[0], {
                    "report_uuid": "beta-collision",
                    "lob_id": "lob-beta",
                    "filing_year": 2023,
                }],
                {
                    "alpha-1": filing_paths["alpha-1"],
                    "beta-collision": collision_path,
                },
                crosswalk=crosswalk,
            )
            raised = False
        except BN.IngestError as exc:
            raised = "harvested client.id maps to multiple pinned orgs" in str(exc)
        assert raised

    try:
        BN.attribute_sweep_filing(
            {
                "filing_uuid": "missing-id",
                "client": {"client_id": 12, "name": "Alpha Financial Group"},
            },
            {"lob-alpha": set(), "lob-beta": set()},
            crosswalk=crosswalk,
        )
        raised = False
    except BN.IngestError as exc:
        raised = "missing key client.id" in str(exc)
    assert raised


def test_bridge3_all_year_id_harvest_matches_unseen_sweep_name():
    crosswalk = {
        "fintech": {"ALPHA FINANCIAL GROUP": "lob-alpha"},
    }
    worklist = [
        {
            "report_uuid": "alpha-2025",
            "lob_id": "lob-alpha",
            "filing_year": 2025,
        }
    ]
    with tempfile.TemporaryDirectory() as fixture:
        seed_path = os.path.join(fixture, "alpha-2025.json")
        with open(seed_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "client": {
                        "id": 101,
                        "client_id": 12,
                        "name": "Alpha Financial Group",
                    }
                },
                handle,
            )
        harvested, receipt = BN.harvest_client_ids(
            worklist,
            {"alpha-2025": seed_path},
            crosswalk=crosswalk,
        )
    assert harvested == {"lob-alpha": {"101"}}
    assert receipt["harvest_filing_years"] == [2025]
    assert receipt["harvest_max_filing_year"] == 2025
    assert receipt["harvest_year_cap"] is None

    result = BN.attribute_sweep_filing(
        {
            "filing_uuid": "future-alpha",
            "client": {
                "id": 101,
                "client_id": 999,
                "name": "AlphaPay Future Services",
            },
        },
        harvested,
        crosswalk=crosswalk,
    )
    assert result["lob_id"] == "lob-alpha"
    assert result["client_id_match"] is True
    assert result["exact_name_match"] is False


def test_bridge3_id_harvest_plausibility_guard_rejects_cross_attribution():
    crosswalk = {
        "alpha": {"ALPHA FINANCIAL GROUP": "lob-alpha"},
        "beta": {"BETA CREDIT UNION": "lob-beta"},
    }
    worklist = [
        {
            "report_uuid": "wrong-owner",
            "lob_id": "lob-alpha",
            "filing_year": 2024,
        }
    ]
    with tempfile.TemporaryDirectory() as fixture:
        seed_path = os.path.join(fixture, "wrong-owner.json")
        with open(seed_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "client": {
                        "id": 202,
                        "client_id": 12,
                        "name": "Beta Credit Union",
                    }
                },
                handle,
            )
        harvested, receipt = BN.harvest_client_ids(
            worklist,
            {"wrong-owner": seed_path},
            crosswalk=crosswalk,
        )
    assert harvested == {"lob-alpha": set(), "lob-beta": set()}
    alpha_receipt = next(
        row for row in receipt["per_org"] if row["lob_id"] == "lob-alpha"
    )
    assert alpha_receipt["accepted_client_ids"] == []
    assert alpha_receipt["rejected_client_ids"][0]["client_id"] == "202"
    assert alpha_receipt["rejected_client_ids"][0]["failed_rule"] == (
        AAI.NAME_PLAUSIBILITY_FAILED_RULE
    )

    result = BN.attribute_sweep_filing(
        {
            "filing_uuid": "cross-attribution-trap",
            "client": {
                "id": 202,
                "client_id": 12,
                "name": "Unseen Organization Name",
            },
        },
        harvested,
        crosswalk=crosswalk,
    )
    assert result["lob_id"] is None
    assert result["client_id_match"] is False


def test_legacy_2021_build_does_not_consult_identity_harvest_loader():
    filing_uuid = "21000000-0000-0000-0000-000000000091"
    lob_id = "legacy-lob"
    with tempfile.TemporaryDirectory() as directory:
        raw_dir = os.path.join(directory, "Melange", "lda_rebuild", "raw")
        filing_dir = os.path.join(raw_dir, "filings", "2021")
        os.makedirs(filing_dir)
        worklist_path = os.path.join(
            raw_dir, "pinned_2021_filings_worklist.json"
        )
        with open(worklist_path, "w", encoding="utf-8") as handle:
            json.dump(
                [
                    {
                        "report_uuid": filing_uuid,
                        "lob_id": lob_id,
                        "filing_period_code": "Q1",
                        "is_amendment": False,
                        "is_no_activity": False,
                        "filing_url": "https://example.invalid/filing",
                    }
                ],
                handle,
            )
        filing_path = os.path.join(filing_dir, filing_uuid + ".json")
        with open(filing_path, "w", encoding="utf-8") as handle:
            json.dump({}, handle)
        with open(worklist_path, "rb") as handle:
            worklist_md5 = hashlib.md5(handle.read()).hexdigest()
        with open(filing_path, "rb") as handle:
            filing_md5 = hashlib.md5(handle.read()).hexdigest()
        with open(
            os.path.join(raw_dir, "fec_lda_filings_manifest.json"),
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                {
                    "worklist_md5": worklist_md5,
                    "failures": [],
                    "md5": {filing_uuid: filing_md5},
                },
                handle,
            )

        originals = {
            "load_pinned_identity_harvest": BN.load_pinned_identity_harvest,
            "load_client_industries": BN.load_client_industries,
            "load_sponsor_map": BN.load_sponsor_map,
            "parse_filings": BN.parse_filings,
        }

        def forbidden_harvest(*_args, **_kwargs):
            raise AssertionError("2021 consulted sweep identity harvest")

        def empty_sponsor_map(*_args, **_kwargs):
            return ({}, set(), set(), {}, {}, {})

        def empty_parse(*_args, **_kwargs):
            return {
                "bills_by_lob": {},
                "bills_by_lob_strict": {},
                "distinct_bills": set(),
                "distinct_bills_strict": set(),
                "filings_parsed": 1,
                "no_activity_filings": 0,
                "amendment_filings": 0,
                "original_and_amendment_groups": [],
                "activities": 0,
                "raw_mentions": 0,
                "unparsed_mentions": {},
                "congress_context_mentions": [],
                "stale_citations": [],
                "stale_unresolvable": [],
                "per_filing_mentions": [],
                "parsed_mentions": [],
                "title_channel": {},
            }

        BN.load_pinned_identity_harvest = forbidden_harvest
        BN.load_client_industries = lambda _path, lob_ids: {
            value: "legacy" for value in lob_ids
        }
        BN.load_sponsor_map = empty_sponsor_map
        BN.parse_filings = empty_parse
        try:
            assert BN._run(
                environ={"LOCALAPPDATA": directory},
                argv=("--years", "2021"),
            ) == 0
        finally:
            for name, value in originals.items():
                setattr(BN, name, value)


def test_bridge3_zero_match_org_has_per_year_coverage_gap_receipt():
    crosswalk = {
        "alpha": {"ALPHA FINANCIAL GROUP": "lob-alpha"},
        "beta": {"BETA CREDIT UNION": "lob-beta"},
    }
    harvested = {"lob-alpha": {"101"}, "lob-beta": set()}
    filing_uuid = "24000000-0000-0000-0000-000000000092"
    with tempfile.TemporaryDirectory() as fixture:
        with open(
            os.path.join(fixture, "page_00001.json"),
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump(
                {
                    "results": [
                        _bridge3_sweep_filing(
                            filing_uuid,
                            2024,
                            client_id="12",
                            senate_client_id="101",
                            name="Unseen Alpha DBA Name",
                        )
                    ]
                },
                handle,
            )
        receipt = BN.scan_sweep_pages(
            fixture,
            2024,
            harvested_client_ids=harvested,
            crosswalk=crosswalk,
        )["receipt"]["attribution"]

    by_lob = {row["lob_id"]: row for row in receipt["per_org_year"]}
    assert by_lob["lob-alpha"]["matched_filings"] == 1
    assert by_lob["lob-alpha"]["matched_by_id"] == 1
    assert by_lob["lob-alpha"]["matched_by_name"] == 0
    assert by_lob["lob-alpha"]["matched_by_both"] == 0
    assert by_lob["lob-alpha"]["client_names_matched_by_id"] == [
        "Unseen Alpha DBA Name"
    ]
    assert receipt["coverage_gaps"] == [
        {
            "lob_id": "lob-beta",
            "industry": "beta",
            "filing_year": 2024,
            "reason": "zero_id_and_exact_name_matches",
        }
    ]


def _naive_title_keys(text, title_index):
    normalized, _spans = BN._normalized_text_with_spans(text)
    padded = " " + normalized + " "
    candidates = []
    for title, bill_keys in title_index.items():
        needle = " " + title + " "
        start_from = 0
        while True:
            found = padded.find(needle, start_from)
            if found < 0:
                break
            candidates.append((found, found + len(title), title, set(bill_keys)))
            start_from = found + 1
    candidates.sort(key=lambda item: (-(item[1] - item[0]), item[0], item[2]))
    accepted = []
    for candidate in candidates:
        length = candidate[1] - candidate[0]
        if not any(
            candidate[0] < prior[1]
            and candidate[1] > prior[0]
            and prior[1] - prior[0] > length
            for prior in accepted
        ):
            accepted.append(candidate)
    return set().union(*(candidate[3] for candidate in accepted)) if accepted else set()


def test_bridge3_first_word_title_index_matches_naive():
    title_index, _receipt = BN.build_title_index(
        {
            ("HR", 1, 118): ["American Rescue Plan Act of 2023"],
            ("S", 2, 118): ["American Rescue Plan"],
            ("HR", 3, 118): ["Safe Banking Reform Act"],
        }
    )
    descriptions = (
        "Support the American Rescue Plan Act of 2023.",
        "Discuss the Safe Banking Reform Act and implementation.",
        "No indexed legislation appears here.",
    )
    for description in descriptions:
        indexed = BN.match_bill_titles(description, title_index)["bill_keys"]
        assert indexed == _naive_title_keys(description, title_index)


def test_bridge3_xhat_battery_construction_sanity():
    records = []
    for cycle in ("2023-2024", "2025-2026"):
        for index in range(6):
            records.append(
                {
                    "industry": "fintech",
                    "cycle": cycle,
                    "member": f"M{index}",
                    "x": float(index + 1),
                    "y": 0.0,
                    "party": float(index % 2),
                    "chamber": float(index >= 3),
                    "volume": (index + 0.5) / 6.0,
                    "committee": float(index in {1, 4}),
                }
            )
    components = B3._battery_components(records)
    assert len(components["x_fitted"]) == len(records)
    assert abs(sum(components["z_x_fitted"])) < 1e-9
    assert max(components["z_x_fitted"]) > min(components["z_x_fitted"])
    residual = [
        observed - fitted
        for observed, fitted in zip(
            components["x_fractional"], components["x_fitted"]
        )
    ]
    design = B3._design(components["records"], B3.CONTROL_NAMES)
    for column in range(len(design[0])):
        assert abs(
            sum(row[column] * error for row, error in zip(design, residual))
        ) < 1e-9


def test_round4b_y_distinct_directional_bill_construction():
    bill_one = ("HR", 10, 118)
    bill_nondirectional = ("S", 20, 118)
    rows = [
        {
            "stratum": "credit_union",
            "lob_id": "lob-a",
            "bill_key": bill_one,
            "our_position": "Support",
        },
        {
            "stratum": "credit_union",
            "lob_id": "lob-b",
            "bill_key": bill_one,
            "our_position": "Oppose",
        },
        {
            "stratum": "credit_union",
            "lob_id": "lob-a",
            "bill_key": bill_one,
            "our_position": "Support",
        },
        {
            "stratum": "credit_union",
            "lob_id": "lob-a",
            "bill_key": bill_nondirectional,
            "our_position": "Amend",
        },
    ]
    members = {"A000001", "B000002", "C000003"}
    result = R4B._construct_y(
        rows,
        {bill_one: {"A000001", "B000002"}},
        members,
    )
    assert result["bills_by_stratum"]["credit_union"] == {bill_one}
    assert result["all"]["credit_union"] == {
        "A000001": 1,
        "B000002": 1,
        "C000003": 0,
    }
    assert result["support"]["credit_union"]["A000001"] == 1
    assert result["oppose"]["credit_union"]["A000001"] == 1
    assert result["positioned_bill_counts"] == {
        ("credit_union", "lob-a"): 1,
        ("credit_union", "lob-b"): 1,
    }


def test_round4b_congestion_x_stratum_field_mapping():
    rows = [
        {
            "member": "Alpha Member",
            "bioguide": "A000001",
            "cu": 11,
            "banks": 29,
        },
        {
            "member": "Beta Member",
            "bioguide": "B000002",
            "cu": 7,
            "banks": 3,
        },
    ]
    mapped = R4B._x_by_stratum_from_congestion_rows(rows)
    assert mapped["credit_union"] == {"A000001": 11.0, "B000002": 7.0}
    assert mapped["bank"] == {"A000001": 29.0, "B000002": 3.0}
    malformed = [dict(rows[0])]
    del malformed[0]["banks"]
    try:
        R4B._x_by_stratum_from_congestion_rows(malformed)
    except R4B.IngestError as exc:
        assert "banks" in str(exc)
    else:
        raise AssertionError("missing congestion banks field was accepted")


def test_round4b_entry_and_void_exact_boundaries():
    x_ten = {
        stratum: {
            f"{stratum[0].upper()}{index:06d}": 1.0
            for index in range(10)
        }
        for stratum in R4B.STRATA
    }
    y_data = {
        "associations_by_stratum": {
            "credit_union": {"cu-a", "cu-b"},
            "bank": {"bank-a", "bank-b"},
        },
        "bills_by_stratum": {
            "credit_union": {("HR", 1, 118)},
            "bank": {("S", 2, 118)},
        },
    }
    exact_entry = R4B._entry_status(y_data, x_ten)
    assert exact_entry["credit_union"]["entered"]
    assert exact_entry["bank"]["entered"]

    x_nine = {key: dict(value) for key, value in x_ten.items()}
    x_nine["bank"].pop(next(iter(x_nine["bank"])))
    assert not R4B._entry_status(y_data, x_nine)["bank"]["entered"]
    one_association = {
        **y_data,
        "associations_by_stratum": {
            **y_data["associations_by_stratum"],
            "bank": {"bank-a"},
        },
    }
    assert not R4B._entry_status(one_association, x_ten)["bank"]["entered"]

    exact_floor = {
        "credit_union": {"entered": True, "x_positive_members": 40},
        "bank": {"entered": True, "x_positive_members": 40},
    }
    assert not R4B._coverage_status(exact_floor)["void"]
    below_floor = {
        "credit_union": {"entered": True, "x_positive_members": 39},
        "bank": {"entered": True, "x_positive_members": 40},
    }
    assert R4B._coverage_status(below_floor)["void"]
    one_stratum = {
        "credit_union": {"entered": True, "x_positive_members": 80},
        "bank": {"entered": False, "x_positive_members": 40},
    }
    assert R4B._coverage_status(one_stratum)["void"]


def test_round4b_battery_never_loads_real_y():
    margins = {
        "x": {stratum: {} for stratum in R4B.STRATA},
        "legislators": {},
        "committee": set(),
        "totals": {},
    }
    for stratum in R4B.STRATA:
        for index in range(40):
            member = f"{stratum[0].upper()}{index:06d}"
            margins["x"][stratum][member] = float((index % 17) + 1)
            margins["legislators"][member] = {
                "party_name": "Republican" if index % 2 else "Democrat",
                "party": float(index % 2),
                "chamber": float(index % 5 == 0),
            }
            margins["totals"][member] = (index % 11) + 1
            if index % 3 == 0:
                margins["committee"].add(member)

    original_loader = R4B._load_real_y
    original_margin_loader = R4B._load_margins
    original_emit = R4B._emit
    original_permutations = B3.PERMUTATIONS
    emitted = []

    def forbidden_loader(*_args, **_kwargs):
        raise AssertionError("battery invoked the real-Y loader")

    class BatteryArgs:
        battery = True
        out = None

    R4B._load_real_y = forbidden_loader
    R4B._load_margins = lambda _args: margins
    R4B._emit = lambda text, _path: emitted.append(text)
    B3.PERMUTATIONS = 7
    try:
        exit_code = R4B._run(BatteryArgs())
    finally:
        B3.PERMUTATIONS = original_permutations
        R4B._emit = original_emit
        R4B._load_margins = original_margin_loader
        R4B._load_real_y = original_loader
    assert exit_code in {0, 4}
    assert len(emitted) == 1
    assert emitted[0].startswith("## BATTERY-R4B\n")
    assert "real-Y isolation: PASS" in emitted[0]


def _position_work_item(
    lob_id="lob-a",
    bill_type="HR",
    bill_number=1,
    congress=117,
    report_uuid="00000000-0000-0000-0000-000000000001",
    filing_year=2021,
    paragraph="Support H.R. 1.",
):
    bill_key = (bill_type, bill_number, congress)
    return {
        "lob_id": lob_id,
        "client_name": "Synthetic Client",
        "bill_key": {
            "type": bill_type,
            "number": bill_number,
            "congress": congress,
        },
        "bill_no": BP.bill_display(bill_key),
        "short_title": "Synthetic Short Title",
        "official_title": "A bill used for synthetic testing.",
        "official_title_tier": "official_as_introduced",
        "paragraph": paragraph,
        "report_uuid": report_uuid,
        "filing_year": filing_year,
        "quarter": 1,
    }


def _position_payload(descriptions):
    if isinstance(descriptions, str):
        descriptions = [descriptions]
    return {
        "client": {
            "id": 101,
            "client_id": 202,
            "name": "Synthetic Client",
        },
        "lobbying_activities": [
            {"description": description} for description in descriptions
        ],
    }


def _write_position_dataset_fixture(path, rows):
    fieldnames = [
        "lob_id",
        "client_name",
        "bill_id",
        "label_3_class",
        "label_5_class",
        "annotation_source",
    ]
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _fewshot_dataset_row(lob_id, bill_number, label):
    return {
        "lob_id": lob_id,
        "client_name": f"Client {lob_id}",
        "bill_key": ("HR", bill_number, 117),
        "label_3_class": BP.collapse_their_five_to_three(label),
        "label_5_class": label,
        "annotation_source": "llm",
    }


def _fewshot_source_item(lob_id, bill_number):
    return _position_work_item(
        lob_id=lob_id,
        bill_number=bill_number,
        report_uuid=(
            "00000000-0000-0000-0000-" + f"{bill_number:012d}"
        ),
        paragraph=f"Position text for H.R. {bill_number}.",
    )


def test_quarterly_period_vocabulary_and_unknown():
    cases = {
        "Q1": 1,
        "Q2": 2,
        "Q3": 3,
        "Q4": 4,
        "H1": 2,
        "H2": 4,
        "first_quarter": 1,
        "second_quarter": 2,
        "third_quarter": 3,
        "fourth_quarter": 4,
        "mid_year": 2,
        "year_end": 4,
    }
    for period, quarter in cases.items():
        assert BN.filing_period_to_quarter(period) == quarter
    try:
        BN.filing_period_to_quarter("fifth_quarter")
    except BN.IngestError as exc:
        assert "fifth_quarter" in str(exc)
    else:
        raise AssertionError("unknown filing period did not fail")


def test_quarterly_aggregation_distinctness():
    bill = ("HR", 1, 117)
    dyad_sets = BN.build_quarterly_dyad_bill_sets(
        {
            ("lob-a", 1): [bill, bill],
            ("lob-a", 2): [bill],
        },
        {bill: {"A000001"}},
    )
    assert dyad_sets == {
        ("lob-a", "A000001", 1): {bill},
        ("lob-a", "A000001", 2): {bill},
    }
    assert BN._quarterly_network_rows(dyad_sets, 2021) == [
        {
            "lob_id": "lob-a",
            "bioguide_id": "A000001",
            "year": 2021,
            "quarter": 1,
            "n_bills": 1,
        },
        {
            "lob_id": "lob-a",
            "bioguide_id": "A000001",
            "year": 2021,
            "quarter": 2,
            "n_bills": 1,
        },
    ]


def test_position_calibration_join_and_three_class_collapse():
    work_items = [
        _position_work_item(lob_id="lob-a"),
        _position_work_item(
            lob_id="lob-b",
            report_uuid="00000000-0000-0000-0000-000000000002",
        ),
        _position_work_item(
            lob_id="lob-c",
            bill_number=9,
            congress=118,
            report_uuid="00000000-0000-0000-0000-000000000003",
            filing_year=2023,
        ),
    ]
    dataset_rows = [
        {
            "lob_id": "lob-a",
            "client_name": "A",
            "bill_key": ("HR", 1, 117),
            "label_3_class": "Support",
            "label_5_class": "Support",
            "annotation_source": "llm",
        },
        {
            "lob_id": "lob-b",
            "client_name": "B",
            "bill_key": ("HR", 1, 117),
            "label_3_class": "Engage",
            "label_5_class": "Monitor",
            "annotation_source": "gnn",
        },
        {
            "lob_id": "lob-z",
            "client_name": "Z",
            "bill_key": ("S", 2, 117),
            "label_3_class": "Oppose",
            "label_5_class": "Oppose",
            "annotation_source": "llm",
        },
    ]
    joined, report = BP.calibration_join(
        work_items, dataset_rows, {"lob-a"}
    )
    assert report["our_extractable_pairs_through_2022"] == 2
    assert report["overlapping_pairs_overall"] == 2
    assert report["overlapping_pairs_subset"] == 1
    assert report["joinable_work_items"] == 1
    assert len(joined) == 1
    assert joined[0]["their_label_5_class"] == "Support"
    assert BP.collapse_three_class("Support") == "Support"
    assert BP.collapse_three_class("Oppose") == "Oppose"
    for label in ("Amend", "Monitor", "Mention"):
        assert BP.collapse_three_class(label) == "Engage"


def test_position_dataset_accepts_their_five_label_vocabulary():
    their_labels = BP.THEIR_FIVE_CLASS_LABELS
    rows = []
    for index, label in enumerate(their_labels, start=1):
        rows.append(
            {
                "lob_id": f"lob-{index}",
                "client_name": f"Client {index}",
                "bill_id": f"hr{index}-117",
                "label_3_class": BP.collapse_their_five_to_three(label),
                "label_5_class": label,
                "annotation_source": "llm",
            }
        )
    with tempfile.TemporaryDirectory() as fixture:
        path = os.path.join(fixture, "positions.csv")
        _write_position_dataset_fixture(path, rows)
        parsed = BP.load_position_dataset(path)
    assert [row["label_5_class"] for row in parsed] == list(their_labels)
    assert [row["label_3_class"] for row in parsed] == [
        BP.collapse_their_five_to_three(label) for label in their_labels
    ]


def test_position_dataset_unknown_label_names_row():
    base = {
        "lob_id": "lob-a",
        "client_name": "Client A",
        "bill_id": "hr1-117",
        "label_3_class": "Support",
        "label_5_class": "Support",
        "annotation_source": "llm",
    }
    for field, unknown in (
        ("label_5_class", "Mention"),
        ("label_3_class", "Monitor"),
    ):
        row = dict(base)
        row[field] = unknown
        with tempfile.TemporaryDirectory() as fixture:
            path = os.path.join(fixture, "positions.csv")
            _write_position_dataset_fixture(path, [row])
            try:
                BP.load_position_dataset(path)
            except BN.IngestError as exc:
                assert "row 2" in str(exc)
                assert field in str(exc)
                assert unknown in str(exc)
            else:
                raise AssertionError(f"unknown {field} did not fail")


def test_position_three_class_collapse_both_directions():
    assert {
        label: BP.collapse_our_to_three(label) for label in BP.OUR_LABELS
    } == {
        "Support": "Support",
        "Oppose": "Oppose",
        "Amend": "Engage",
        "Monitor": "Engage",
        "Mention": "Engage",
    }
    assert {
        label: BP.collapse_their_five_to_three(label)
        for label in BP.THEIR_FIVE_CLASS_LABELS
    } == {
        "Support": "Support",
        "Oppose": "Oppose",
        "Amend": "Engage",
        "Monitor": "Engage",
        "Engage": "Engage",
    }


def test_position_agreement_primary_and_restricted_secondary_n():
    results = []
    their_labels = BP.THEIR_FIVE_CLASS_LABELS
    our_labels = ("Support", "Oppose", "Amend", "Monitor", "Mention")
    for index, (their_label, our_label) in enumerate(
        zip(their_labels, our_labels), start=1
    ):
        item = _position_work_item(
            report_uuid=(
                "00000000-0000-0000-0000-" + f"{index:012d}"
            )
        )
        item.update(
            {
                "their_label_5_class": their_label,
                "their_label_3_class": (
                    BP.collapse_their_five_to_three(their_label)
                ),
                "annotation_source": "llm" if index <= 3 else "gnn",
            }
        )
        results.append(
            (
                item,
                {
                    "status": "ok",
                    "position": our_label,
                },
            )
        )
    report = BP.agreement_report(results)
    assert report["primary_agreement"] == "three_class"
    overall = report["groups"]["overall"]
    assert overall["primary_three_class"]["n"] == 5
    assert overall["primary_three_class"]["accuracy"] == 1.0
    secondary = overall["restricted_secondary_five_class"]
    assert secondary["n"] == 4
    assert secondary["accuracy"] == 1.0
    assert "Engage rows excluded" in secondary["restriction"]
    assert report["groups"]["llm"]["primary_three_class"]["n"] == 3
    assert report["groups"]["gnn"]["primary_three_class"]["n"] == 2
    assert (
        report["groups"]["gnn"][
            "restricted_secondary_five_class"
        ]["n"]
        == 1
    )


def test_position_prompt_exactness():
    item = _position_work_item(
        bill_number=1996,
        paragraph="We support enactment.",
    )
    item["short_title"] = "SAFE Banking Act"
    item["official_title"] = "A bill to protect financial institutions."
    expected = (
        "Classify the given text that explicitly describes lobbying "
        "activities for bill H.R. 1996 into one of the five types: "
        "'Support', 'Oppose', 'Amend', 'Monitor', or 'Mention' without "
        "explanation.\n"
        "H.R. 1996 short title: SAFE Banking Act\n"
        "H.R. 1996 official title: A bill to protect financial "
        "institutions.\n"
        "Text:We support enactment.\n"
        "Answer:"
    )
    assert BP.build_prompt(
        item, prompt_variant="zeroshot"
    ).encode("utf-8") == expected.encode("utf-8")


def test_position_jsonl_and_flat_csv_round_trip():
    item = _position_work_item()
    item["client_name"] = "Synthetic Client, Inc."
    item.update(
        {
            "their_label_3_class": "Support",
            "their_label_5_class": "Support",
            "annotation_source": "llm",
        }
    )
    receipt = {
        "status": "ok",
        "position": "Support",
        "raw_reply": "Support",
        "model": BP.MODEL,
        "prompt_sha256": BP.prompt_sha256(item),
    }
    with tempfile.TemporaryDirectory() as fixture:
        output = os.path.join(fixture, "calibration.csv")
        _rows, sibling = BP.write_classification_outputs(
            output, [(item, receipt)]
        )
        assert sibling == os.path.join(fixture, "calibration.flat.csv")
        with open(output, "r", encoding="utf-8") as handle:
            primary_rows = [json.loads(line) for line in handle]
        with open(sibling, "r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            flat_rows = list(reader)
            assert reader.fieldnames == BP.FLAT_RESULT_FIELDS
    assert len(primary_rows) == 1
    assert primary_rows[0]["bill_key"] == item["bill_key"]
    assert primary_rows[0]["our_position"] == "Support"
    assert flat_rows == [
        {
            "lob_id": "lob-a",
            "client_name": "Synthetic Client, Inc.",
            "bill_type": "HR",
            "bill_number": "1",
            "congress": "117",
            "bill_no": "H.R. 1",
            "our_position": "Support",
            "their_label_3_class": "Support",
            "their_label_5_class": "Support",
            "annotation_source": "llm",
            "report_uuid": item["report_uuid"],
            "filing_year": "2021",
            "quarter": "1",
            "classification_status": "ok",
            "model": BP.MODEL,
            "prompt_sha256": receipt["prompt_sha256"],
        }
    ]


def test_position_fewshot_prompt_pinned_order_and_label_mapping():
    labels = ("Support", "Oppose", "Amend", "Engage")
    dataset = [
        _fewshot_dataset_row(f"lob-{index}", index, label)
        for index, label in enumerate(labels, start=1)
    ]
    sources = [
        _fewshot_source_item(f"lob-{index}", index)
        for index in range(1, len(labels) + 1)
    ]
    exemplars, _receipt = BP.select_fewshot_exemplars(
        dataset, sources, []
    )
    assert [item["their_label_5_class"] for item in exemplars] == list(labels)
    assert [item["mapped_label"] for item in exemplars] == [
        "Support",
        "Oppose",
        "Amend",
        "Mention",
    ]
    target = _position_work_item(
        bill_number=99,
        report_uuid="00000000-0000-0000-0000-000000000099",
    )
    prompt = BP.build_prompt(target, "fewshot", exemplars)
    cursor = 0
    for exemplar in exemplars:
        rendered = BP.render_exemplar(exemplar)
        position = prompt.find(rendered, cursor)
        assert position >= cursor
        cursor = position + len(rendered)
    assert prompt.endswith(BP.PROMPT_TARGET_TEMPLATE.format(
        bill_no=target["bill_no"],
        short_title=target["short_title"],
        official_title=target["official_title"],
        paragraph=target["paragraph"],
    ))


def test_position_fewshot_selection_excludes_calibration_pairs():
    leaked = _fewshot_source_item("lob-leaked", 1)
    allowed = _fewshot_source_item("lob-allowed", 2)
    dataset = [
        _fewshot_dataset_row("lob-leaked", 1, "Support"),
        _fewshot_dataset_row("lob-allowed", 2, "Support"),
    ]
    exemplars, receipt = BP.select_fewshot_exemplars(
        dataset, [leaked, allowed], [leaked]
    )
    source_pairs = [item["source_pair"] for item in exemplars]
    assert {"lob_id": "lob-leaked", "bill_id": "hr1-117"} not in source_pairs
    assert source_pairs == [
        {"lob_id": "lob-allowed", "bill_id": "hr2-117"}
    ]
    assert receipt["dataset_pairs_excluded_by_calibration_set"] == 1


def test_position_fewshot_shortfall_receipt_and_cache_reuse():
    dataset = [_fewshot_dataset_row("lob-support", 7, "Support")]
    source = _fewshot_source_item("lob-support", 7)
    with tempfile.TemporaryDirectory() as fixture:
        cache_path = os.path.join(fixture, "exemplars.json")
        first, first_audit = BP.prepare_prompt_variant(
            "fewshot",
            [],
            dataset_rows=dataset,
            source_work_items=[source],
            exemplar_cache=cache_path,
        )
        second, second_audit = BP.prepare_prompt_variant(
            "fewshot", [], exemplar_cache=cache_path
        )
    shortfalls = first_audit["selection_receipt"]["shortfall_by_group"]
    assert shortfalls == {
        "Support": 2,
        "Oppose": 3,
        "Monitor/Amend": 3,
        "Engage/Mention": 3,
    }
    assert first_audit["selected_exemplars"] == 1
    assert first_audit["exemplar_cache_used"] is False
    assert second_audit["exemplar_cache_used"] is True
    assert first == second
    assert first_audit["exemplar_cache_sha256"] == (
        second_audit["exemplar_cache_sha256"]
    )
    assert first_audit["rendered_prompt_prefix_sha256"] == (
        second_audit["rendered_prompt_prefix_sha256"]
    )


def test_position_reply_parsing_and_unparseable_receipt():
    for label in BP.LABELS:
        assert BP.parse_model_reply(label) == label
        assert BP.parse_model_reply(label.upper() + ".") == label
        assert BP.parse_model_reply("'" + label.lower() + "'") == label
    receipt = BP.reply_receipt("Support because the text says so")
    assert receipt == {
        "status": "unparseable",
        "position": None,
        "raw_reply": "Support because the text says so",
    }


def test_position_content_hash_resume_behavior():
    first = _position_work_item()
    duplicate = json.loads(json.dumps(first))
    changed = dict(first)
    changed["paragraph"] = "Monitor H.R. 1."
    first_hash = BP.work_item_content_hash(first)
    assert BP.work_item_content_hash(duplicate) == first_hash
    assert BP.work_item_content_hash(changed) != first_hash
    manifest = {
        "model": BP.MODEL,
        "completed": {
            first_hash: {
                "status": "ok",
                "position": "Support",
                "raw_reply": "Support",
                "model": BP.MODEL,
                "prompt_sha256": BP.prompt_sha256(first),
            }
        },
    }
    pending = BP.pending_work_items([first, duplicate, changed], manifest)
    assert pending == [changed]


def test_position_title_only_official_allows_empty_short():
    bill_key = ("HR", 2, 117)
    title_items = BP._title_items_for_member(
        io.BytesIO(
            _bill_xml(
                "A000001",
                titles=[
                    (
                        "Official Title as Introduced",
                        "Reserved for the Speaker.",
                    )
                ],
            )
        ),
        "synthetic.zip",
        "BILLSTATUS-117hr2.xml",
    )
    short_title, official_title, tier = BP.resolve_prompt_titles(
        title_items, bill_key
    )
    assert short_title == ""
    assert official_title == "Reserved for the Speaker."
    assert tier == "official_as_introduced"
    item = _position_work_item(bill_number=2)
    item.update(
        {
            "short_title": short_title,
            "official_title": official_title,
            "official_title_tier": tier,
        }
    )
    assert "H.R. 2 short title: \n" in BP.build_prompt(item)
    assert BP.title_availability_receipt([item]) == {
        "work_items_without_short_title": 1,
        "official_title_resolution_tiers": {
            "official_as_introduced": 1,
            "official_other": 0,
            "display_title": 0,
            "first_available": 0,
        },
    }


def test_position_title_display_fallback_receipted():
    bill_key = ("HR", 2, 117)
    title_items = BP._title_items_for_member(
        io.BytesIO(
            _bill_xml(
                "A000001",
                titles=[("Display Title", "A display-only bill title")],
            )
        ),
        "synthetic.zip",
        "BILLSTATUS-117hr2.xml",
    )
    short_title, official_title, tier = BP.resolve_prompt_titles(
        title_items, bill_key
    )
    assert short_title == ""
    assert official_title == "A display-only bill title"
    assert tier == "display_title"
    item = _position_work_item(bill_number=2)
    item.update(
        {
            "short_title": short_title,
            "official_title": official_title,
            "official_title_tier": tier,
        }
    )
    receipt = BP.title_availability_receipt([item])
    assert receipt["work_items_without_short_title"] == 1
    assert receipt["official_title_resolution_tiers"]["display_title"] == 1


def test_position_title_zero_items_raises():
    title_items = BP._title_items_for_member(
        io.BytesIO(_bill_xml("A000001")),
        "synthetic.zip",
        "BILLSTATUS-117hr2.xml",
    )
    try:
        BP.resolve_prompt_titles(title_items, ("HR", 2, 117))
    except BN.IngestError as exc:
        assert "H.R. 2" in str(exc)
        assert "Congress 117" in str(exc)
    else:
        raise AssertionError("bill with zero title items did not fail")


def test_position_title_both_preserves_short_and_prefers_introduced():
    bill_key = ("HR", 1, 117)
    title_items = BP._title_items_for_member(
        io.BytesIO(
            _bill_xml(
                "A000001",
                titles=[
                    ("Official Title as Passed House", "Passed official"),
                    ("Short Title as Introduced", "Named Act"),
                    (
                        "Official Title as Introduced",
                        "Introduced official",
                    ),
                    ("Display Title", "Display title"),
                ],
            )
        ),
        "synthetic.zip",
        "BILLSTATUS-117hr1.xml",
    )
    short_title, official_title, tier = BP.resolve_prompt_titles(
        title_items, bill_key
    )
    assert short_title == "Named Act"
    assert official_title == "Introduced official"
    assert tier == "official_as_introduced"
    item = _position_work_item()
    item.update(
        {
            "short_title": short_title,
            "official_title": official_title,
            "official_title_tier": tier,
        }
    )
    receipt = BP.title_availability_receipt([item])
    assert receipt["work_items_without_short_title"] == 0
    assert (
        receipt["official_title_resolution_tiers"][
            "official_as_introduced"
        ]
        == 1
    )


def test_position_absent_billstatus_key_skipped_with_samples():
    report_uuid = "00000000-0000-0000-0000-000000000144"
    long_description = (
        "A" * 150
        + " S.Con.Res. 144616, Synthetic Resolution of 2020 "
        + "B" * 150
    )
    short_description = (
        "Discussed S.Con.Res. 144616, Synthetic Resolution of 2020."
    )
    skipped = {}
    items = BP.work_items_from_payload(
        _position_payload([long_description, short_description]),
        report_uuid,
        "lob-a",
        2021,
        "Q1",
        {},
        {},
        {116: {}, 117: {}},
        skipped,
    )
    assert items == []
    receipt = BP.bill_not_in_billstatus_receipt(skipped)[
        "work_items_skipped_bill_not_in_billstatus"
    ]
    assert receipt["count"] == 2
    assert receipt["distinct_bill_keys"] == 1
    assert len(receipt["by_bill"]) == 1
    bill_receipt = receipt["by_bill"][0]
    assert bill_receipt["bill_no"] == "S.Con.Res. 144616"
    assert bill_receipt["congress"] == 116
    assert bill_receipt["count"] == 2
    assert len(bill_receipt["samples"]) == 2
    assert all(
        sample["report_uuid"] == report_uuid
        for sample in bill_receipt["samples"]
    )
    assert all(
        len(sample["verbatim_source_segment"]) <= 200
        for sample in bill_receipt["samples"]
    )
    assert all(
        "S.Con.Res. 144616" in sample["verbatim_source_segment"]
        for sample in bill_receipt["samples"]
    )
    assert bill_receipt["samples"][1][
        "verbatim_source_segment"
    ] == short_description


def test_position_present_billstatus_key_without_titles_still_raises():
    bill_key = ("SCONRES", 144616, 116)
    try:
        BP.work_items_from_payload(
            _position_payload(
                "Discussed S.Con.Res. 144616, Synthetic Resolution of 2020."
            ),
            "00000000-0000-0000-0000-000000000145",
            "lob-a",
            2021,
            "Q1",
            {},
            {bill_key: ()},
            {116: {bill_key: set()}, 117: {}},
            {},
        )
    except BN.IngestError as exc:
        assert "S.Con.Res. 144616" in str(exc)
        assert "Congress 116" in str(exc)
    else:
        raise AssertionError("present titleless bill did not fail")


def test_position_present_billstatus_key_with_titles_unchanged():
    bill_key = ("HR", 1, 117)
    skipped = {}
    items = BP.work_items_from_payload(
        _position_payload("Support H.R. 1."),
        "00000000-0000-0000-0000-000000000146",
        "lob-a",
        2021,
        "Q1",
        {},
        {
            bill_key: (
                {
                    "title_type": "Short Title as Introduced",
                    "title": "Named Act",
                },
                {
                    "title_type": "Official Title as Introduced",
                    "title": "A bill to establish a synthetic policy.",
                },
            )
        },
        {117: {bill_key: {"A000001"}}},
        skipped,
    )
    assert len(items) == 1
    assert items[0]["bill_key"] == {
        "type": "HR",
        "number": 1,
        "congress": 117,
    }
    assert items[0]["short_title"] == "Named Act"
    assert items[0]["official_title"] == (
        "A bill to establish a synthetic policy."
    )
    assert items[0]["official_title_tier"] == "official_as_introduced"
    assert BP.bill_not_in_billstatus_receipt(skipped) == {
        "work_items_skipped_bill_not_in_billstatus": {
            "count": 0,
            "distinct_bill_keys": 0,
            "by_bill": [],
        }
    }


def _assoc_write_csv(path, fieldnames, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _assoc_kim_rows(lob_id, count, directional):
    rows = []
    for index in range(count):
        if index < directional:
            label_5 = "Support" if index % 2 == 0 else "Oppose"
            label_3 = label_5
        else:
            label_5 = "Monitor"
            label_3 = "Engage"
        rows.append(
            {
                "lob_id": lob_id,
                "client_name": f"Kim {lob_id}",
                "bill_id": f"hr{index + 1}-117",
                "label_3_class": label_3,
                "label_5_class": label_5,
                "label": "1.0",
                "annotation_source": "synthetic",
            }
        )
    return rows


def _assoc_payload(
    filing_uuid,
    year,
    client_name,
    client_id,
    description,
    scoped_client_id=None,
):
    if scoped_client_id is None:
        scoped_client_id = client_id
    return {
        "filing_uuid": filing_uuid,
        "filing_year": year,
        "filing_period": "first_quarter",
        "client": {
            "id": client_id,
            "client_id": scoped_client_id,
            "name": client_name,
        },
        "lobbying_activities": [
            {
                "general_issue_code": "FIN",
                "description": description,
            }
        ],
    }


def _assoc_calibration_rows():
    rows = []
    for index in (1, 2):
        rows.append(
            {
                "annotation_source": "synthetic",
                "bill_key": {"congress": 118, "number": 7, "type": "HR"},
                "bill_no": "H.R. 7",
                "client_name": "EXACT ASSOCIATION",
                "filing_year": 2023,
                "lob_id": "lob-cu",
                "official_title": "A bill used for association testing.",
                "official_title_tier": "official_as_introduced",
                "paragraph": f"Support H.R. 7 fixture {index}.",
                "quarter": 1,
                "report_uuid": (
                    f"00000000-0000-0000-0000-{index:012d}"
                ),
                "short_title": "Synthetic Association Act",
                "their_client_name": "Exact Association",
                "their_label_3_class": "Support",
                "their_label_5_class": "Support",
            }
        )
    return rows


def _assoc_write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _assoc_id_entry(stratum, name, client_ids):
    accepted = sorted(client_ids)
    return {
        "stratum": stratum,
        "lobbyview_name": name,
        "client_ids": list(accepted),
        "accepted_client_ids": list(accepted),
        "rejected_client_ids": [],
        "filing_names_seen": [name],
        "uuids_present": 1,
        "uuids_missing": 0,
    }


def _assoc_write_sweep_window(directory, results_2023, results_2024=None):
    if results_2024 is None:
        results_2024 = []
    for year, results in ((2023, results_2023), (2024, results_2024)):
        year_dir = os.path.join(directory, str(year))
        os.makedirs(year_dir)
        with open(
            os.path.join(year_dir, "page_00001.json"),
            "w",
            encoding="utf-8",
        ) as handle:
            json.dump({"results": results}, handle)


def _assoc_extraction_context():
    bill_key = ("HR", 7, 118)
    title_index, _receipt = BN.build_title_index(
        {bill_key: ["Synthetic Association Act of 2023"]}
    )
    return {
        "bill_people_maps": {118: {bill_key: {"A000001"}}},
        "title_indexes": {118: title_index},
        "prompt_title_items": {
            bill_key: (
                {
                    "title_type": "Short Title as Introduced",
                    "title": "Synthetic Association Act",
                },
                {
                    "title_type": "Official Title as Introduced",
                    "title": "A bill used for association testing.",
                },
            )
        },
    }


def test_association_name_normalizer_fixed_cases():
    assert AAI.normalize_association_name("  Mixed\tCase\nAssociation  ") == (
        "MIXED CASE ASSOCIATION"
    )
    assert AAI.normalize_association_name("Example Association.,") == (
        "EXAMPLE ASSOCIATION"
    )
    assert AAI.normalize_association_name("lower case,   spaced.") == (
        "LOWER CASE, SPACED"
    )


def test_association_set_directional_threshold_rule():
    with tempfile.TemporaryDirectory() as directory:
        classified = os.path.join(directory, "classified.csv")
        kim = os.path.join(directory, "kim.csv")
        _assoc_write_csv(
            classified,
            (
                "lob_id",
                "client_name",
                "naics",
                "gvkey",
                "bvdid",
                "side",
                "match_rule",
                "confidence",
            ),
            [
                {
                    "lob_id": "cu-below",
                    "client_name": "CU Below",
                    "side": "credit_union",
                },
                {
                    "lob_id": "cu-exact",
                    "client_name": "CU Exact",
                    "side": "credit_union",
                },
                {
                    "lob_id": "bank-exact",
                    "client_name": "Bank Exact",
                    "side": "bank",
                },
                {
                    "lob_id": "not-relevant",
                    "client_name": "Other Client",
                    "side": "other",
                },
            ],
        )
        kim_rows = []
        kim_rows.extend(_assoc_kim_rows("cu-below", 7, 4))
        kim_rows.extend(_assoc_kim_rows("cu-exact", 8, 5))
        kim_rows.extend(_assoc_kim_rows("bank-exact", 5, 5))
        kim_rows.extend(_assoc_kim_rows("not-relevant", 6, 6))
        _assoc_write_csv(
            kim,
            (
                "lob_id",
                "client_name",
                "bill_id",
                "label_3_class",
                "label_5_class",
                "label",
                "annotation_source",
            ),
            kim_rows,
        )

        association_sets, receipt = AAI.load_association_sets(
            classified, kim, min_directional=5
        )
        assert [
            row["lob_id"] for row in association_sets["credit_union"]
        ] == ["cu-exact"]
        assert [row["lob_id"] for row in association_sets["bank"]] == [
            "bank-exact"
        ]
        assert association_sets["credit_union"][0]["directional_count"] == 5
        assert association_sets["credit_union"][0]["total_position_count"] == 8
        excluded = receipt["excluded_below_min_directional"]["credit_union"]
        assert [row["lob_id"] for row in excluded] == ["cu-below"]
        assert excluded[0]["directional_count"] == 4


def test_association_crosswalk_is_exact_only_and_receipts_near_name():
    association_sets = {
        "credit_union": [
            {
                "lob_id": "lob-cu",
                "client_names": ["Exact Association"],
                "directional_count": 5,
                "total_position_count": 5,
            }
        ],
        "bank": [],
    }
    exact_uuid = "00000000-0000-0000-0000-000000000201"
    near_uuid = "00000000-0000-0000-0000-000000000202"
    id_crosswalk = {
        "lob-cu": _assoc_id_entry(
            "credit_union", "Exact Association", []
        )
    }
    with tempfile.TemporaryDirectory() as directory:
        _assoc_write_sweep_window(
            directory,
            [
                _assoc_payload(
                    exact_uuid,
                    2023,
                    "  exact   association. ",
                    101,
                    "Support H.R. 7.",
                ),
                _assoc_payload(
                    near_uuid,
                    2023,
                    "Exact Association PAC",
                    102,
                    "Support H.R. 7.",
                ),
            ],
        )

        result = AAI.scan_sweeps(
            directory, association_sets, id_crosswalk
        )
        assert [
            row["filing_uuid"] for row in result["matched_filings"]
        ] == [exact_uuid]
        assert result["crosswalk"]["credit_union"][0][
            "lda_client_ids"
        ] == [101]
        assert result["crosswalk"]["credit_union"][0][
            "matched_by_name"
        ] == 1
        assert result["crosswalk"]["credit_union"][0][
            "matched_by_id"
        ] == 0
        unmatched = result["receipt"]["unmatched_exact_name"]
        assert unmatched["count"] == 1
        assert unmatched["samples"][0]["filing_uuid"] == near_uuid
        assert unmatched["samples"][0]["normalized_client_name"] == (
            "EXACT ASSOCIATION PAC"
        )


def test_association_global_id_matches_despite_name_mismatch():
    association_sets = {
        "credit_union": [
            {
                "lob_id": "lob-id",
                "client_names": ["Legacy Association Name"],
                "directional_count": 5,
                "total_position_count": 6,
            }
        ],
        "bank": [],
    }
    id_crosswalk = {
        "lob-id": _assoc_id_entry(
            "credit_union", "Legacy Association Name", [701]
        )
    }
    filing_uuid = "00000000-0000-0000-0000-000000000401"
    with tempfile.TemporaryDirectory() as directory:
        _assoc_write_sweep_window(
            directory,
            [
                _assoc_payload(
                    filing_uuid,
                    2023,
                    "Completely Renamed Organization",
                    701,
                    "Support H.R. 7.",
                    scoped_client_id=44,
                )
            ],
        )
        result = AAI.scan_sweeps(
            directory, association_sets, id_crosswalk
        )
        assert [row["filing_uuid"] for row in result["matched_filings"]] == [
            filing_uuid
        ]
        row = result["crosswalk"]["credit_union"][0]
        assert row["matched_by_id"] == 1
        assert row["matched_by_name"] == 0
        assert row["matched_by_both"] == 0
        assert row["client_names_matched_by_id_only"] == [
            "Completely Renamed Organization"
        ]


def test_association_id_and_name_channels_have_union_semantics():
    association_sets = {
        "credit_union": [],
        "bank": [
            {
                "lob_id": "lob-union",
                "client_names": ["Union Bank Association"],
                "directional_count": 5,
                "total_position_count": 7,
            }
        ],
    }
    id_crosswalk = {
        "lob-union": _assoc_id_entry(
            "bank", "Union Bank Association", [801]
        )
    }
    id_uuid = "00000000-0000-0000-0000-000000000411"
    name_uuid = "00000000-0000-0000-0000-000000000412"
    with tempfile.TemporaryDirectory() as directory:
        _assoc_write_sweep_window(
            directory,
            [
                _assoc_payload(
                    id_uuid,
                    2023,
                    "Renamed Bank Organization",
                    801,
                    "Support H.R. 7.",
                ),
                _assoc_payload(
                    name_uuid,
                    2023,
                    "Union Bank Association",
                    802,
                    "Oppose H.R. 7.",
                ),
            ],
        )
        result = AAI.scan_sweeps(
            directory, association_sets, id_crosswalk
        )
        assert [row["filing_uuid"] for row in result["matched_filings"]] == [
            id_uuid,
            name_uuid,
        ]
        row = result["crosswalk"]["bank"][0]
        assert row["matched_by_id"] == 1
        assert row["matched_by_name"] == 1
        assert row["matched_by_both"] == 0
        channels = {
            item["filing_uuid"]: (
                item["matched_by_id"],
                item["matched_by_name"],
            )
            for item in result["matched_filings"]
        }
        assert channels[id_uuid] == (True, False)
        assert channels[name_uuid] == (False, True)


def test_association_client_scoped_id_never_attributes_identity():
    association_sets = {
        "credit_union": [
            {
                "lob_id": "lob-a",
                "client_names": ["Legacy A"],
                "directional_count": 5,
                "total_position_count": 5,
            }
        ],
        "bank": [
            {
                "lob_id": "lob-b",
                "client_names": ["Legacy B"],
                "directional_count": 5,
                "total_position_count": 5,
            }
        ],
    }
    seed_a = "00000000-0000-0000-0000-000000000421"
    seed_b = "00000000-0000-0000-0000-000000000422"
    missing = "00000000-0000-0000-0000-000000000423"
    window_a = "00000000-0000-0000-0000-000000000424"
    window_b = "00000000-0000-0000-0000-000000000425"
    scoped_trap = "00000000-0000-0000-0000-000000000426"
    with tempfile.TemporaryDirectory() as directory:
        seed_path = os.path.join(directory, "seed.json")
        filings_root = os.path.join(directory, "filings")
        cache_2021 = os.path.join(filings_root, "2021")
        os.makedirs(cache_2021)
        with open(seed_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "lob-a": {
                        "stratum": "credit_union",
                        "name": "Legacy A",
                        "uuids": [seed_a, missing],
                        "total": 2,
                    },
                    "lob-b": {
                        "stratum": "bank",
                        "name": "Legacy B",
                        "uuids": [seed_b],
                        "total": 1,
                    },
                },
                handle,
            )
        for filing_uuid, global_id, name in (
            (seed_a, 901, "Legacy A Historical"),
            (seed_b, 902, "Legacy B Historical"),
        ):
            with open(
                os.path.join(cache_2021, filing_uuid + ".json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    _assoc_payload(
                        filing_uuid,
                        2021,
                        name,
                        global_id,
                        "Support H.R. 7.",
                        scoped_client_id=777,
                    ),
                    handle,
                )

        harvested = AAI.harvest_id_crosswalk(seed_path, filings_root)
        assert harvested["lob-a"]["client_ids"] == [901]
        assert harvested["lob-b"]["client_ids"] == [902]
        assert harvested["lob-a"]["uuids_present"] == 1
        assert harvested["lob-a"]["uuids_missing"] == 1

        sweeps = os.path.join(directory, "sweeps")
        _assoc_write_sweep_window(
            sweeps,
            [
                _assoc_payload(
                    window_a,
                    2023,
                    "Current A",
                    901,
                    "Support H.R. 7.",
                    scoped_client_id=777,
                ),
                _assoc_payload(
                    window_b,
                    2023,
                    "Current B",
                    902,
                    "Support H.R. 7.",
                    scoped_client_id=777,
                ),
                _assoc_payload(
                    scoped_trap,
                    2023,
                    "Unrelated Organization",
                    999,
                    "Support H.R. 7.",
                    scoped_client_id=901,
                ),
            ],
        )
        result = AAI.scan_sweeps(sweeps, association_sets, harvested)
        attributed = {
            row["filing_uuid"]: row["lob_id"]
            for row in result["matched_filings"]
        }
        assert attributed == {window_a: "lob-a", window_b: "lob-b"}
        unmatched = result["receipt"]["unmatched_exact_name"]
        assert unmatched["count"] == 1
        assert unmatched["samples"][0]["filing_uuid"] == scoped_trap


def test_association_main_fails_loud_without_id_crosswalk():
    with tempfile.TemporaryDirectory() as directory:
        missing = os.path.join(directory, "id_crosswalk.json")
        try:
            AAI.load_id_crosswalk(missing)
        except BN.IngestError as exc:
            assert "identity client.id crosswalk" in str(exc)
        else:
            raise AssertionError("missing identity crosswalk did not fail")
        assert AAI.main(
            ["--out-dir", directory, "--id-crosswalk", missing],
            environ={"LOCALAPPDATA": directory},
        ) == 2


def test_association_work_item_determinism_and_schema_mirror():
    filing_uuid = "00000000-0000-0000-0000-000000000301"
    matched = [
        {
            "stratum": "credit_union",
            "lob_id": "lob-cu",
            "association_name": "EXACT ASSOCIATION",
            "filing_uuid": filing_uuid,
            "filing_year": 2023,
            "payload": _assoc_payload(
                filing_uuid,
                2023,
                "EXACT ASSOCIATION",
                101,
                "Support H.R. 7 without changing this paragraph.",
            ),
        }
    ]
    calib_rows = _assoc_calibration_rows()
    with tempfile.TemporaryDirectory() as directory:
        calib = os.path.join(directory, "calib.jsonl")
        _assoc_write_jsonl(calib, calib_rows)
        schema = AAI.load_calibration_schema(calib)
        first_items, first_receipt = AAI.assemble_association_work_items(
            matched, schema, _assoc_extraction_context()
        )
        second_items, second_receipt = AAI.assemble_association_work_items(
            matched, schema, _assoc_extraction_context()
        )
        assert first_items == second_items
        assert first_receipt == second_receipt
        assert len(first_items) == 1
        item = first_items[0]
        assert item["paragraph"] == (
            "Support H.R. 7 without changing this paragraph."
        )
        assert set(item) - {"stratum"} == (
            set(calib_rows[0]) - AAI.GOLD_FIELDS
        )
        assert item["stratum"] == "credit_union"

        first_dir = os.path.join(directory, "first")
        second_dir = os.path.join(directory, "second")
        AAI.write_outputs(first_dir, {"fixture": True}, first_items)
        AAI.write_outputs(second_dir, {"fixture": True}, second_items)
        with open(
            os.path.join(first_dir, "assoc_work_items.jsonl"), "rb"
        ) as handle:
            first_bytes = handle.read()
        with open(
            os.path.join(second_dir, "assoc_work_items.jsonl"), "rb"
        ) as handle:
            second_bytes = handle.read()
        assert first_bytes == second_bytes


def _assoc_harvest_name_pairs(lobbyview_name, client_names_and_ids):
    with tempfile.TemporaryDirectory() as directory:
        seed_path = os.path.join(directory, "seed.json")
        filings_root = os.path.join(directory, "filings")
        cache_2021 = os.path.join(filings_root, "2021")
        os.makedirs(cache_2021)
        uuids = [
            f"00000000-0000-0000-0000-{index:012d}"
            for index in range(501, 501 + len(client_names_and_ids))
        ]
        with open(seed_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "lob-guard": {
                        "stratum": "bank",
                        "name": lobbyview_name,
                        "uuids": uuids,
                        "total": len(uuids),
                    }
                },
                handle,
            )
        for filing_uuid, (filing_name, client_id) in zip(
            uuids, client_names_and_ids
        ):
            with open(
                os.path.join(cache_2021, filing_uuid + ".json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(
                    _assoc_payload(
                        filing_uuid,
                        2021,
                        filing_name,
                        client_id,
                        "Support H.R. 7.",
                    ),
                    handle,
                )
        return AAI.harvest_id_crosswalk(seed_path, filings_root)["lob-guard"]


def test_association_id_guard_rejects_ufcw_for_sound_banking():
    row = _assoc_harvest_name_pairs(
        "SOUND BANKING COALITION",
        [
            (
                "UNITED FOOD & COMMERCIAL WORKERS INTERNATIONAL UNION",
                147122,
            )
        ],
    )
    assert row["accepted_client_ids"] == []
    assert row["client_ids"] == []
    assert {receipt["client_id"] for receipt in row["rejected_client_ids"]} == {
        147122
    }


def test_association_id_guard_accepts_nafcu_rename():
    row = _assoc_harvest_name_pairs(
        "NATIONAL ASSOCIATION OF FEDERAL CREDIT UNIONS",
        [
            (
                "NATIONAL ASSOCIATION OF FEDERALLY-INSURED CREDIT UNIONS",
                134228,
            )
        ],
    )
    assert row["accepted_client_ids"] == [134228]
    assert row["rejected_client_ids"] == []


def test_association_id_guard_accepts_nonempty_subset():
    row = _assoc_harvest_name_pairs(
        "CITIGROUP", [("CITIGROUP WASHINGTON INC", 168138)]
    )
    assert row["accepted_client_ids"] == [168138]
    assert row["rejected_client_ids"] == []


def test_association_id_guard_rejects_shared_stopwords_only():
    row = _assoc_harvest_name_pairs(
        "NATIONAL RESTAURANT ASSOCIATION",
        [("NATIONAL MINING ASSOCIATION", 300001)],
    )
    assert row["accepted_client_ids"] == []
    assert len(row["rejected_client_ids"]) == 1


def test_association_id_rejection_receipt_carries_both_token_sets():
    lobbyview_name = "SOUND BANKING COALITION"
    filing_name = "UNITED FOOD & COMMERCIAL WORKERS INTERNATIONAL UNION"
    row = _assoc_harvest_name_pairs(
        lobbyview_name, [(filing_name, 147122)]
    )
    receipt = row["rejected_client_ids"][0]
    assert receipt["lobbyview_name"] == lobbyview_name
    assert receipt["filing_client_name"] == filing_name
    assert receipt["lobbyview_tokens"] == ["BANKING", "SOUND"]
    assert receipt["filing_name_tokens"] == [
        "COMMERCIAL",
        "FOOD",
        "UNITED",
        "WORKERS",
    ]
    assert receipt["failed_rule"] == AAI.NAME_PLAUSIBILITY_FAILED_RULE


def _champion_fixture_row(
    bioguide,
    seniority,
    volume,
    raw,
    party="D",
    chamber="rep",
    committee=False,
):
    return {
        "bioguide_id": bioguide,
        "member_name": "Member " + bioguide,
        "party": party,
        "chamber": chamber,
        "seniority_years": seniority,
        "legislative_volume": volume,
        "finance_committee": committee,
        "raw_n_bills": raw,
        "years_present": 1 if raw else 0,
        "first_contact_year": 2023 if raw else None,
        "latest_year": 2023 if raw else None,
        "trend_sign": 0,
        "direction_of_travel": "flat",
        "yearly_n_bills": {"2023": raw},
    }


def _champion_full_rank_rows():
    rows = []
    index = 1
    for level in range(1, 11):
        for party_index, party in enumerate(("D", "R", "I")):
            for chamber_index, chamber in enumerate(("rep", "sen")):
                committee = bool(
                    (level + party_index + chamber_index) % 2
                )
                seniority = 2 * level + party_index
                volume = (
                    20 * level * level
                    + 3 * party_index
                    + chamber_index
                )
                structural = (
                    0.45 * math.log1p(seniority)
                    + 0.80 * math.log1p(volume)
                    + 0.15 * party_index
                    + 0.10 * chamber_index
                    + 0.08 * int(committee)
                )
                raw = max(1, int(round(math.exp(structural) - 1.0)))
                rows.append(
                    _champion_fixture_row(
                        f"X{index:06d}",
                        seniority,
                        volume,
                        raw,
                        party=party,
                        chamber=chamber,
                        committee=committee,
                    )
                )
                index += 1
    rows.extend(
        [
            _champion_fixture_row("L000001", 1, 1, 25),
            _champion_fixture_row("H000001", 40, 2000, 25),
        ]
    )
    return rows


def test_lobby_champions_structural_controls_bite():
    result = LC.score_member_rows(
        _champion_full_rank_rows(), include_committee=True, min_links=1
    )
    assert result["skipped_reason"] is None
    scored = {row["bioguide_id"]: row for row in result["rows"]}
    assert scored["L000001"]["raw_n_bills"] == 25
    assert scored["H000001"]["raw_n_bills"] == 25
    assert (
        scored["L000001"]["champion_score"]
        > scored["H000001"]["champion_score"]
    )


def test_lobby_champions_zero_fills_roster_member():
    roster = {
        "A000001": {
            "member_name": "Member A",
            "party": "D",
            "chamber": "rep",
        },
        "B000001": {
            "member_name": "Member B",
            "party": "R",
            "chamber": "sen",
        },
    }
    rows = LC.build_member_rows(
        {2021: {"A000001": 3}, 2022: {"A000001": 2}},
        [2021, 2022],
        roster,
        {"A000001": 12, "B000001": 8},
        {"A000001": 100, "B000001": 50},
        committee_members=None,
    )
    by_member = {row["bioguide_id"]: row for row in rows}
    assert len(rows) == 2
    assert by_member["B000001"]["raw_n_bills"] == 0
    assert by_member["B000001"]["yearly_n_bills"] == {
        "2021": 0,
        "2022": 0,
    }
    assert by_member["B000001"]["years_present"] == 0


def test_lobby_champions_under_min_links_receipted():
    rows = [
        _champion_fixture_row("A000001", 5, 10, 2),
        _champion_fixture_row("B000001", 8, 20, 0, party="R"),
        _champion_fixture_row("C000001", 9, 30, 0, party="I"),
    ]
    result = LC.score_member_rows(
        rows, include_committee=False, min_links=2
    )
    assert result["rows"] == []
    assert result["n_nonzero_member_links"] == 1
    assert "below min_links=2" in result["skipped_reason"]


def test_lobby_champions_rank_deficiency_receipted():
    rows = [
        _champion_fixture_row(
            f"D{index:06d}", 10, 100, index + 1
        )
        for index in range(30)
    ]
    result = LC.score_member_rows(
        rows, include_committee=False, min_links=1
    )
    assert result["rows"] == []
    assert result["design_rank"] < 6
    assert result["skipped_reason"].startswith("rank_deficient_design:")


def test_lobby_champions_csv_determinism():
    result = LC.score_member_rows(
        _champion_full_rank_rows(), include_committee=True, min_links=1
    )
    assert result["skipped_reason"] is None
    flat_rows = []
    for source in result["rows"]:
        row = dict(source)
        row.update(
            {
                "lob_id": "lob-fixture",
                "org_name": "Fixture Organization",
                "name_source": "unresolved",
                "org_side": "other",
                "covered_years": "[2023]",
                "controls_used": "[\"log1p_seniority\"]",
                "controls_omitted_reason": "fixture",
                "residual_standard_error": result[
                    "residual_standard_error"
                ],
                "r2": result["r2"],
                "n_members_modeled": result["n_members_modeled"],
                "yearly_n_bills": json.dumps(
                    source["yearly_n_bills"],
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            }
        )
        flat_rows.append(row)
    document = {
        "generated_utc": "2026-08-02T00:00:00Z",
        "provenance": {},
        "method_note": LC.METHOD_NOTE,
        "per_org": [],
    }
    with tempfile.TemporaryDirectory() as directory:
        first = os.path.join(directory, "first")
        second = os.path.join(directory, "second")
        LC.write_outputs(first, document, flat_rows)
        LC.write_outputs(second, document, flat_rows)
        with open(os.path.join(first, "champions.csv"), "rb") as handle:
            first_bytes = handle.read()
        with open(os.path.join(second, "champions.csv"), "rb") as handle:
            second_bytes = handle.read()
        assert first_bytes == second_bytes


def test_lobby_champions_sector_mean_is_genuine_leave_one_out():
    rows = [
        {
            "lob_id": "org-a",
            "org_side": "finance",
            "bioguide_id": "A000001",
            "member_name": "Member A",
            "champion_rank": 1,
            "champion_score": 10.0,
        },
        {
            "lob_id": "org-b",
            "org_side": "finance",
            "bioguide_id": "A000001",
            "member_name": "Member A",
            "champion_rank": 1,
            "champion_score": 2.0,
        },
        {
            "lob_id": "org-c",
            "org_side": "finance",
            "bioguide_id": "A000001",
            "member_name": "Member A",
            "champion_rank": 1,
            "champion_score": 4.0,
        },
    ]
    per_org = [
        {
            "lob_id": row["lob_id"],
            "champions": [
                {
                    "bioguide_id": row["bioguide_id"],
                    "champion_score": row["champion_score"],
                }
            ],
        }
        for row in rows
    ]
    LC.add_sector_relative(per_org, rows)
    by_org = {row["lob_id"]: row for row in rows}
    assert by_org["org-a"]["sector_mean_score"] == 3.0
    assert by_org["org-a"]["sector_relative_score"] == 7.0
    assert by_org["org-a"]["sector_n_orgs"] == 2
    assert by_org["org-b"]["sector_mean_score"] == 7.0
    assert per_org[0]["champions"][0]["sector_mean_score"] == 3.0


def test_lobby_champions_single_org_sector_fields_are_null_not_zero():
    rows = [
        {
            "lob_id": "only-org",
            "org_side": None,
            "bioguide_id": "A000001",
            "member_name": "Member A",
            "champion_rank": 1,
            "champion_score": 5.0,
        }
    ]
    per_org = [
        {
            "lob_id": "only-org",
            "champions": [
                {"bioguide_id": "A000001", "champion_score": 5.0}
            ],
        }
    ]
    LC.add_sector_relative(per_org, rows)
    assert rows[0]["sector_basis"] == "all_orgs"
    assert rows[0]["sector_n_orgs"] == 0
    assert rows[0]["sector_mean_score"] is None
    assert rows[0]["sector_relative_score"] is None
    assert rows[0]["sector_rank"] is None


def test_attention_vs_stance_bioguide_join_survives_display_name_difference():
    identities = {
        "K000383": {
            "bioguide_id": "K000383",
            "member_name": "Angus S. King, Jr.",
        },
        "B000001": {
            "bioguide_id": "B000001",
            "member_name": "Absent Crosswalk Member",
        },
    }
    congestion_by_bioguide = {
        "K000383": {"member": "Angus King", "bioguide": "K000383"},
        "Z000001": {"member": "Congestion Only", "bioguide": "Z000001"},
    }
    congestion_by_member = {
        "Angus King": {"member": "Angus King", "bioguide": "K000383"},
        "Congestion Only": {
            "member": "Congestion Only",
            "bioguide": "Z000001",
        },
    }
    say_do = {
        "Angus King": {
            "source_name": "Angus King",
            "say_z": 0.2,
            "do_z": 0.1,
            "gap": 0.1,
            "sponsored_cu": 2,
            "quadrant": "aligned",
        }
    }
    category = {
        "Angus King": {
            "source_name": "Angus King",
            "stance_mean": 0.4,
            "stance_defensive_mean": 0.3,
            "n_categories_with_data": 5,
            "n_defensive_categories_with_data": 2,
        }
    }
    receipt = AVS.make_bioguide_join_receipts(
        identities,
        congestion_by_bioguide,
        congestion_by_member,
        say_do,
        category,
    )
    assert receipt["matched_bioguides"] == 1
    assert receipt["champions_bioguide_absent_from_congestion"] == {
        "count": 1,
        "samples": ["B000001 | Absent Crosswalk Member"],
    }
    assert receipt["congestion_bioguide_absent_from_champions"] == {
        "count": 1,
        "samples": ["Z000001 | Congestion Only"],
    }
    assert receipt["congestion_display_name_absent_from_say_do_gap"][
        "samples"
    ] == ["Congestion Only"]
    assert receipt["congestion_display_name_absent_from_category_stance"][
        "samples"
    ] == ["Congestion Only"]
    attached = AVS.attach_member_records(
        [
            {
                "bioguide_id": "K000383",
                "member_name": "Angus S. King, Jr.",
            }
        ],
        congestion_by_bioguide,
        say_do,
        category,
    )
    assert attached[0]["congestion_member_name"] == "Angus King"
    assert attached[0]["stance_mean"] == 0.4
    assert attached[0]["quadrant"] == "aligned"


def _attention_stance_fixture_row(name, bioguide, rank, score, stance, quadrant):
    return {
        "lob_id": "fixture-org",
        "org_name": "Fixture Organization",
        "org_side": "credit_union",
        "bioguide_id": bioguide,
        "member_name": name,
        "congestion_member_name": name,
        "champion_rank": rank,
        "champion_score": score,
        "sector_rank": rank,
        "sector_relative_score": score / 10.0,
        "category_stance_name": name,
        "say_do_gap_name": name,
        "stance_mean": stance,
        "stance_defensive_mean": stance,
        "n_categories_with_data": 4,
        "n_defensive_categories_with_data": 2,
        "say_z": score / 10.0,
        "do_z": score / 20.0,
        "gap": score / 20.0,
        "sponsored_cu": rank,
        "quadrant": quadrant,
    }


def test_attention_vs_stance_known_member_enters_worked_adversaries_cell():
    rows = [
        _attention_stance_fixture_row(
            "Hostile High", "A000001", 1, 4.0, -0.5, "talker"
        ),
        _attention_stance_fixture_row(
            "Supportive High", "B000001", 2, 3.0, 0.5, "aligned"
        ),
        _attention_stance_fixture_row(
            "Supportive Low", "C000001", 3, 2.0, 0.2, "doer"
        ),
        _attention_stance_fixture_row(
            "Hostile Low", "D000001", 4, 1.0, -0.2, "aligned"
        ),
    ]
    entry, analyzed = AVS.analyze_organization_rows(rows, min_members=1)
    worked_adversaries = entry["primary_attention_by_stance"]["cells"][
        "high"
    ]["hostile"]
    assert worked_adversaries["label"] == "worked adversaries"
    assert worked_adversaries["n"] == 1
    assert worked_adversaries["names"] == ["Hostile High"]
    by_name = {row["member_name"]: row for row in analyzed}
    assert by_name["Hostile High"]["primary_cell_label"] == "worked adversaries"


def test_attention_vs_stance_json_and_csv_are_deterministic():
    rows = [
        _attention_stance_fixture_row(
            "Member A", "A000001", 1, 2.0, 0.4, "aligned"
        ),
        _attention_stance_fixture_row(
            "Member B", "B000001", 2, 1.0, -0.4, "doer"
        ),
    ]
    entry, _analyzed = AVS.analyze_organization_rows(rows, min_members=1)
    flat_rows = [AVS.flatten_org_entry(entry)]
    document = {
        "method_note": AVS.METHOD_NOTE,
        "provenance": {},
        "join_receipts": {},
        "per_org": [entry],
    }
    with tempfile.TemporaryDirectory() as directory:
        first = os.path.join(directory, "first")
        second = os.path.join(directory, "second")
        AVS.write_outputs(first, document, flat_rows)
        AVS.write_outputs(second, document, flat_rows)
        for filename in (
            "attention_vs_stance.json",
            "attention_vs_stance.csv",
        ):
            with open(os.path.join(first, filename), "rb") as handle:
                first_bytes = handle.read()
            with open(os.path.join(second, filename), "rb") as handle:
                second_bytes = handle.read()
            assert first_bytes == second_bytes


def _dotless_bare_s_people_maps():
    keys_117 = {
        ("S", 4356, 117),
        ("S", 4760, 117),
        ("S", 5300, 117),
    }
    keys_118 = {
        ("HR", 50, 118),
        ("HR", 835, 118),
        ("HR", 1165, 118),
        ("HR", 1234, 118),
        ("S", 7, 118),
        ("S", 1160, 118),
        ("S", 1234, 118),
        ("S", 2020, 118),
        ("S", 3684, 118),
        ("S", 3728, 118),
        ("S", 3862, 118),
        ("S", 3902, 118),
        ("S", 3930, 118),
        ("S", 3940, 118),
    }
    return {
        117: {key: set() for key in keys_117},
        118: {key: set() for key in keys_118},
    }


def test_dotless_bare_s_sba_lookbehind_wins_over_context():
    result = BN.resolve_activity_mentions(
        "the SBA's 7(a) program; H.R. 1234",
        {},
        2023,
        _dotless_bare_s_people_maps(),
    )
    assert result["strict_bill_keys"] == {("HR", 1234, 118)}
    assert ("S", 7, 118) not in result["formal_keys"]
    assert result["dotless_bare_s_rejected"][0][
        "failed_conditions"
    ] == ["negative_lookbehind"]


def test_dotless_bare_s_us_census_lookbehind_wins_over_context():
    result = BN.resolve_activity_mentions(
        "U.S. 2020 Census; H.R. 1234",
        {},
        2023,
        _dotless_bare_s_people_maps(),
    )
    assert result["strict_bill_keys"] == {("HR", 1234, 118)}
    assert ("S", 2020, 118) not in result["formal_keys"]


def test_dotless_bare_s_bank_of_america_5300_and_1160():
    description = (
        "General issues related to credit card late fees; HR 1165, Data "
        "Privacy Act of 2023, issues related to Gramm Leach Bliley Act "
        "modernization; S 5300, Financial Regulators Transparency Act, and "
        "S 1160, issues related to financial regulator transparency."
    )
    result = BN.resolve_activity_mentions(
        description, {}, 2023, _dotless_bare_s_people_maps()
    )
    assert result["strict_bill_keys"] == {
        ("HR", 1165, 118),
        ("S", 1160, 118),
    }
    rejected_5300 = next(
        item
        for item in result["dotless_bare_s_rejected"]
        if item["matched_text"] == "S 5300"
    )
    assert rejected_5300["candidate_bill_key"] == {
        "type": "S",
        "number": 5300,
        "congress": 118,
    }
    assert "billstatus_existence" in rejected_5300[
        "failed_conditions"
    ]


def test_dotless_and_dotted_s_in_same_activity_both_resolve():
    description = (
        "S 4760, Digital Commodities Consumer Protection Act of 2022, and "
        "S. 4356, Responsible Financial Innovation Act, issues related to "
        "digital assets; HR 835, Fair Investment Opportunities for "
        "Professional Experts Act."
    )
    result = BN.resolve_activity_mentions(
        description, {}, 2023, _dotless_bare_s_people_maps()
    )
    assert {("S", 4760), ("S", 4356)} <= {
        (type_token, number)
        for type_token, number, _congress in result["strict_bill_keys"]
    }


def test_dotless_bare_s_without_formal_context_is_rejected():
    result = BN.resolve_activity_mentions(
        "S 1234",
        {},
        2023,
        _dotless_bare_s_people_maps(),
    )
    assert result["strict_bill_keys"] == set()
    assert result["dotless_bare_s_rejected"][0][
        "failed_conditions"
    ] == ["citing_context_proof"]


def test_dotless_bare_s_over_range_and_absent_is_rejected():
    result = BN.resolve_activity_mentions(
        "H.R. 1234; S 99999",
        {},
        2023,
        _dotless_bare_s_people_maps(),
    )
    assert result["strict_bill_keys"] == {("HR", 1234, 118)}
    assert set(
        result["dotless_bare_s_rejected"][0]["failed_conditions"]
    ) == {"billstatus_existence", "range_sanity"}


def test_dotless_bare_s_recovery_and_rejection_receipts():
    filing_uuid = "47ba9366-7ec6-4df9-951b-2bba1d6440ea"
    descriptions = [
        "H.R. 1234; S 1160; S 5300; S 99999",
        "S 1234",
        "the SBA's 7(a) program; H.R. 1234",
    ]
    with tempfile.TemporaryDirectory() as fixture:
        _write_filing(
            os.path.join(fixture, filing_uuid + ".json"),
            filing_uuid,
            descriptions,
        )
        result = BN.parse_filings(
            [
                {
                    "report_uuid": filing_uuid,
                    "lob_id": "lob-a",
                    "filing_year": 2023,
                    "is_no_activity": False,
                    "is_amendment": False,
                    "filing_period_code": "Q1",
                }
            ],
            fixture,
            bill_people_maps=_dotless_bare_s_people_maps(),
        )

    assert result["dotless_bare_s_recovered"] == {
        "count": 1,
        "samples": [
            {
                "filing_uuid": filing_uuid,
                "matched_text": "S 1160",
                "context": descriptions[0],
                "resolved_bill_key": {
                    "type": "S",
                    "number": 1160,
                    "congress": 118,
                },
            }
        ],
    }
    rejected = result["dotless_bare_s_rejected"]
    assert rejected["count"] == 4
    buckets = rejected["by_failed_condition"]
    assert buckets["negative_lookbehind"]["count"] == 1
    assert buckets["billstatus_existence"]["count"] == 2
    assert buckets["citing_context_proof"]["count"] == 1
    assert buckets["range_sanity"]["count"] == 2
    assert all(
        sample["filing_uuid"] == filing_uuid
        for bucket in buckets.values()
        for sample in bucket["samples"]
    )


def test_bill_number_runs_into_title_six_verbatim_citations():
    cases = {
        "S.3728the Veterans Housing Stability Act of 2024": (
            3728,
            "S.3728",
        ),
        "S. 3930Downpayment Toward Equity Act": (3930, "S. 3930"),
        "S. 3862Homeownership Affordability Act": (3862, "S. 3862"),
        "S. 3684Housing Supply and Affordability Act": (3684, "S. 3684"),
        "S. 3940The First-Time Homebuyer Act": (3940, "S. 3940"),
        "S. 3902Appraisal Industry Improvement Act": (3902, "S. 3902"),
    }
    for description, (number, matched_text) in cases.items():
        assert _keys(description) == []
        result = BN.resolve_activity_mentions(
            description,
            {},
            2023,
            _dotless_bare_s_people_maps(),
        )
        assert result["strict_bill_keys"] == {("S", number, 118)}
        assert result["runs_into_title_recovered"] == [
            {
                "matched_text": matched_text,
                "context": description,
                "resolved_bill_key": {
                    "type": "S",
                    "number": number,
                    "congress": 118,
                },
            }
        ]


def test_run_into_title_keeps_thousands_separator_protection():
    for description in ("H.R. 1,234", "S. 1,000"):
        parsed, _unparsed = BN.extract_bill_mentions(description)
        assert parsed == []
        result = BN.resolve_activity_mentions(
            description,
            {},
            2023,
            _dotless_bare_s_people_maps(),
        )
        assert result["strict_bill_keys"] == set()


def test_run_into_title_keeps_six_digit_boundary_protection():
    for description in (
        "S. 144616Synthetic Bill Title",
        "S.Con.Res. 144616Synthetic Resolution Title",
    ):
        assert _keys(description) == []
        result = BN.resolve_activity_mentions(
            description,
            {},
            2023,
            _dotless_bare_s_people_maps(),
        )
        assert result["strict_bill_keys"] == set()
        assert result["runs_into_title_recovered"] == []
    suffix_result = BN.resolve_activity_mentions(
        "HR 50A", {}, 2023, _dotless_bare_s_people_maps()
    )
    assert suffix_result["strict_bill_keys"] == set()
    assert suffix_result["runs_into_title_recovered"] == []


def test_run_into_title_keeps_existing_hyphen_behavior():
    description = "S. 123-456"
    assert _keys(description) == [("S", 123)]
    result = BN.resolve_activity_mentions(
        description, {}, 2023, _dotless_bare_s_people_maps()
    )
    assert result["strict_bill_keys"] == {("S", 123, 118)}
    assert result["runs_into_title_recovered"] == []


def test_runs_into_title_recovery_receipt_bucket():
    filing_uuid = "47ba9366-7ec6-4df9-951b-2bba1d6440ea"
    descriptions = [
        "S.3728the Veterans Housing Stability Act of 2024",
        "S. 3930Downpayment Toward Equity Act",
        "S. 3862Homeownership Affordability Act",
        "S. 3684Housing Supply and Affordability Act",
        "S. 3940The First-Time Homebuyer Act",
        "S. 3902Appraisal Industry Improvement Act",
    ]
    with tempfile.TemporaryDirectory() as fixture:
        _write_filing(
            os.path.join(fixture, filing_uuid + ".json"),
            filing_uuid,
            descriptions,
        )
        result = BN.parse_filings(
            [
                {
                    "report_uuid": filing_uuid,
                    "lob_id": "lob-a",
                    "filing_year": 2023,
                    "is_no_activity": False,
                    "is_amendment": False,
                    "filing_period_code": "Q1",
                }
            ],
            fixture,
            bill_people_maps=_dotless_bare_s_people_maps(),
        )

    runs_receipt = result["runs_into_title_recovered"]
    assert runs_receipt["count"] == 6
    assert len(runs_receipt["samples"]) == 6
    assert {
        sample["resolved_bill_key"]["number"]
        for sample in runs_receipt["samples"]
    } == {3684, 3728, 3862, 3902, 3930, 3940}
    assert all(
        sample["filing_uuid"] == filing_uuid
        for sample in runs_receipt["samples"]
    )


def _forecast_fixture_row(year=2022, lob_id="org-a", bioguide="A000001"):
    row = {
        "lob_id": lob_id,
        "bioguide_id": bioguide,
        "year": year,
        "target_year": year + 1,
        "actual": 0,
        "baseline_persistence": 0,
        "baseline_popularity_probability": 0.0,
        "n_bills_y": 0.0,
        "n_bills_y_minus_1": 0.0,
        "prior_years_present": 0.0,
        "years_since_first_contact": 0.0,
        "years_since_last_contact": 0.0,
        "log1p_seniority": 1.0,
        "log1p_legislative_volume": 2.0,
        "org_total_dyads_y": 25.0,
        "org_median_n_bills_y": 1.0,
        "member_popularity_other_orgs_y": 2.0,
        "chamber": "rep",
        "party": "D",
        "finance_committee": "0",
        "org_side": "finance",
        "_feature_source_years": {
            feature: year for feature in LF.MODEL_FEATURES
        },
    }
    row["_feature_source_years"]["n_bills_y_minus_1"] = year - 1
    return row


def test_lobby_forecast_no_leakage_by_construction():
    row = _forecast_fixture_row()
    assert LF.assert_as_of_features(row)
    assert not (set(LF.MODEL_FEATURES) & set(LF.FEATURES_EXCLUDED_FOR_LEAKAGE))
    row["_feature_source_years"]["synthetic_future_feature"] = row["year"] + 1
    try:
        LF.assert_as_of_features(row)
    except LF.LeakageError as exc:
        assert "after feature year" in str(exc)
    else:
        raise AssertionError("Y+1 feature source was not rejected")


def test_lobby_forecast_persistence_reproduces_82_percent_carryover():
    rows = []
    for index in range(100):
        row = _forecast_fixture_row(
            lob_id="org-a", bioguide=f"A{index:06d}"
        )
        row["actual"] = 1
        row["baseline_persistence"] = int(index < 82)
        rows.append(row)
    assert math.isclose(LF.persistence_carryover(rows), 0.82)


def test_lobby_forecast_churn_subset_excludes_persistent_dyad():
    rows = []
    for index, (previous, actual) in enumerate(
        ((1, 1), (0, 0), (1, 0), (0, 1))
    ):
        row = _forecast_fixture_row(bioguide=f"B{index:06d}")
        row["baseline_persistence"] = previous
        row["actual"] = actual
        rows.append(row)
    churn = LF.churn_subset(rows)
    assert [row["bioguide_id"] for row in churn] == ["B000002", "B000003"]


def test_lobby_forecast_temporal_split_never_trains_on_t_plus_1():
    rows = [
        _forecast_fixture_row(year=year, bioguide=f"C{year:06d}")
        for year in (2021, 2022, 2023)
    ]
    train, test = LF.make_temporal_split(rows, 2021)
    assert {row["year"] for row in train} == {2021}
    assert {row["year"] for row in test} == {2022}
    try:
        LF.available_cutoffs(rows[:1], 2021)
    except LF.ForecastError as exc:
        assert str(exc) == "no temporal train/test split available"
    else:
        raise AssertionError("single usable year-pair was not refused")


def test_lobby_forecast_rank_deficiency_is_reported():
    matrix = []
    outcomes = []
    for index in range(20):
        value = float(index - 10)
        matrix.append([1.0, value, value])
        outcomes.append(index % 2)
    result = LF.irls_logistic(matrix, outcomes, ["intercept", "x", "x_copy"])
    assert result["rank_deficient"] is True
    assert result["design_rank"] == 2
    assert result["design_columns"] == 3
    assert "detected before solve" in result["rank_deficiency_handling"]


def test_lobby_forecast_determinism():
    matrix = []
    outcomes = []
    for index in range(30):
        x1 = (index - 15) / 5.0
        x2 = float((index % 4) - 2)
        matrix.append([1.0, x1, x2])
        outcomes.append(int(index % 3 == 0 or index > 22))
    first = LF.irls_logistic(matrix, outcomes, ["intercept", "x1", "x2"])
    second = LF.irls_logistic(matrix, outcomes, ["intercept", "x1", "x2"])
    assert first == second
    score = {
        "lob_id": "org-a",
        "bioguide_id": "A000001",
        "year": 2022,
        "target_year": 2023,
        "train_through": 2021,
        "predicted_probability": 0.25,
        "actual": 0,
        "baseline_persistence": 1,
        "baseline_popularity_probability": 0.125,
        "baseline_popularity_prediction": 0,
    }
    document = {
        "method_note": LF.METHOD_NOTE,
        "features_excluded_for_leakage": LF.FEATURES_EXCLUDED_FOR_LEAKAGE,
        "per_split": [],
    }
    with tempfile.TemporaryDirectory() as directory:
        first_dir = os.path.join(directory, "first")
        second_dir = os.path.join(directory, "second")
        LF.write_outputs(first_dir, document, [score])
        LF.write_outputs(second_dir, document, [score])
        for filename in ("forecast_report.json", "forecast_scores.csv"):
            with open(os.path.join(first_dir, filename), "rb") as handle:
                first_bytes = handle.read()
            with open(os.path.join(second_dir, filename), "rb") as handle:
                second_bytes = handle.read()
            assert first_bytes == second_bytes


def test_lobby_forecast_coverage_guard_rejects_mixed_basis():
    assert LF.assert_coverage_homogeneous(
        [2023, 2024, 2025], {2023: "sweep", 2024: "sweep", 2025: "sweep"}
    ) == "sweep"
    try:
        LF.assert_coverage_homogeneous(
            [2022, 2023], {2022: "uuid_worklist", 2023: "sweep"}
        )
    except LF.ForecastError as exc:
        assert "mixed network corpus basis refused" in str(exc)
    else:
        raise AssertionError("mixed worklist/sweep split was not refused")


def test_fullscope_org_set_is_four_source_union_without_duplicates():
    with tempfile.TemporaryDirectory() as directory:
        classification_path = os.path.join(directory, "classified.csv")
        association_path = os.path.join(directory, "association_sets.json")
        with open(
            classification_path, "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["lob_id", "client_name", "side"]
            )
            writer.writeheader()
            writer.writerows(
                [
                    {"lob_id": "a", "client_name": "Alpha", "side": "bank"},
                    {
                        "lob_id": "b",
                        "client_name": "Beta",
                        "side": "financial_other",
                    },
                    {"lob_id": "x", "client_name": "Excluded", "side": "other"},
                ]
            )
        with open(association_path, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "association_sets": {
                        "bank": [
                            {"lob_id": "b", "client_names": ["Beta"]},
                            {"lob_id": "c", "client_names": ["Gamma"]},
                        ]
                    }
                },
                handle,
            )
        scope = BN.load_fullscope_org_scope(
            {
                "client_classification": classification_path,
                "association_sets": association_path,
            },
            pinned_crosswalk={
                "pinned": {"Gamma": "c", "Delta": "d"}
            },
        )
        seed_state = BN._new_fullscope_seed_state()
        BN._record_fullscope_pattern_candidate(
            seed_state,
            "47ba9366-7ec6-4df9-951b-2bba1d6440ea",
            2021,
            "900000",
            "EPSILON COMMUNITY BANK",
        )
        BN._extend_fullscope_scope_with_pattern_clients(
            scope,
            seed_state,
            {lob_id: set() for lob_id in scope["lob_ids"]},
        )
    assert scope["lob_ids"] == frozenset({"a", "b", "c", "d", "900000"})
    assert scope["receipt"]["org_set_size"] == 5
    assert scope["receipt"]["net_new_by_union_order"]["name_pattern"] == 1
    assert scope["receipt"]["overlaps"] == {
        "classified_and_association": 1,
        "classified_and_pinned": 0,
        "association_and_pinned": 1,
    }


def test_fullscope_corpus_basis_is_shared_and_not_legacy():
    scope = {
        "lob_ids": frozenset({"a"}),
        "orgs": {
            "a": {
                "normalized_names": ("ALPHA",),
                "sources": ("classified_finance",),
            }
        },
    }
    basis = BN.fullscope_corpus_basis(scope)
    receipts = {
        "2021": {"network": {"CORPUS_BASIS": basis}},
        "2022": {"network": {"CORPUS_BASIS": basis}},
    }
    assert BN.assert_fullscope_corpus_basis(receipts, basis) == basis
    assert basis != BN.LEGACY_CORPUS_BASIS


def test_fullscope_mode_never_selects_legacy_output_paths():
    with tempfile.TemporaryDirectory() as directory:
        paths = BN.default_paths(directory)
        isolation = BN.assert_fullscope_output_isolation(
            paths, (2021, 2022, 2023, 2024, 2025, 2026)
        )
    assert set(isolation["fullscope"]).isdisjoint(
        isolation["legacy_never_written"]
    )
    assert any(
        os.path.basename(path) == "fullscope_receipts.json"
        for path in isolation["fullscope"]
    )


def test_fullscope_zero_match_is_a_per_year_coverage_gap():
    scope = {
        "lob_ids": frozenset({"a", "b"}),
        "orgs": {
            "a": {"names": ("Alpha",)},
            "b": {"names": ("Beta",)},
        },
    }
    resolution_2021, gaps_2021, _rows_2021 = (
        BN.fullscope_resolution_receipt(
            scope,
            2021,
            {"b": {"name": 1}},
            {"b": 1},
        )
    )
    resolution_2022, gaps_2022, _rows_2022 = (
        BN.fullscope_resolution_receipt(
            scope,
            2022,
            {"a": {"id": 2}, "b": {"name": 1}},
            {"a": 2, "b": 1},
        )
    )
    assert resolution_2021["not_at_all"] == 1
    assert [gap["lob_id"] for gap in gaps_2021] == ["a"]
    assert resolution_2022["not_at_all"] == 0
    assert gaps_2022 == []


def test_fullscope_quarterly_union_is_annual_with_repeat_excess():
    bill_a = ("HR", 1, 117)
    bill_b = ("S", 2, 117)
    annual = {("org", "A000001"): {bill_a, bill_b}}
    quarterly = {
        ("org", "A000001", 1): {bill_a},
        ("org", "A000001", 2): {bill_a, bill_b},
    }
    receipt = BN.assert_quarterly_annual_relationship(annual, quarterly)
    assert receipt["annual_equals_union_of_quarters"] is True
    assert receipt["annual_dyad_bill_incidence"] == 2
    assert receipt["summed_quarterly_dyad_bill_incidence"] == 3
    assert receipt["cross_quarter_repeat_excess"] == 1


def test_fullscope_name_pattern_adds_missing_state_league_to_roster():
    with tempfile.TemporaryDirectory() as directory:
        classification_path = os.path.join(directory, "classified.csv")
        association_path = os.path.join(directory, "association_sets.json")
        with open(
            classification_path, "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(
                handle, fieldnames=["lob_id", "client_name", "side"]
            )
            writer.writeheader()
            writer.writerow(
                {
                    "lob_id": "classified-base",
                    "client_name": "BASE FINANCIAL COMPANY",
                    "side": "financial_other",
                }
            )
        with open(association_path, "w", encoding="utf-8") as handle:
            json.dump({"association_sets": {}}, handle)
        scope = BN.load_fullscope_org_scope(
            {
                "client_classification": classification_path,
                "association_sets": association_path,
            },
            pinned_crosswalk={},
        )
        seed_state = BN._new_fullscope_seed_state()
        league_name = "VIRGINIA CREDIT UNION LEAGUE"
        matched = BN._record_fullscope_pattern_candidate(
            seed_state,
            "47ba9366-7ec6-4df9-951b-2bba1d6440ea",
            2021,
            "900001",
            league_name,
        )
        pattern_receipt = BN._extend_fullscope_scope_with_pattern_clients(
            scope,
            seed_state,
            {"classified-base": set()},
        )
        roster = BN.fullscope_org_roster_rows(scope)
    assert {"credit_union", "state_or_territory_league"} <= set(matched)
    assert "900001" not in scope["source_lob_ids"]["classified_finance"]
    league_row = next(
        row for row in roster if row["lob_id_or_client_id"] == "900001"
    )
    assert league_row["client_name"] == league_name
    assert "name_pattern:state_or_territory_league" in league_row[
        "source_flags"
    ]
    derived = pattern_receipt["per_client"][0]
    assert derived["matches"][0]["client_name"] == league_name
    assert derived["first_year_seen"] == 2021


def _voteview_transition_row(
    bioguide,
    congress,
    chamber,
    icpsr,
    state="CA",
    district="0",
    party="100",
):
    return {
        "bioguide_id": bioguide,
        "congress": str(congress),
        "chamber": chamber,
        "icpsr": str(icpsr),
        "state_abbrev": state,
        "district_code": str(district),
        "party_code": str(party),
    }


def test_lobby_forecast_schiff_transition_does_not_break_seniority():
    fields = [
        "bioguide_id",
        "congress",
        "chamber",
        "icpsr",
        "state_abbrev",
        "district_code",
        "party_code",
    ]
    rows = [
        _voteview_transition_row("S001150", 107, "House", 20104, district=29),
        _voteview_transition_row("S001150", 118, "House", 20104, district=30),
        _voteview_transition_row("S001150", 118, "Senate", 20104, district=0),
    ]
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "HSall_members.csv")
        with open(path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        seniority, receipt = LF.load_voteview_seniority(path)
    assert seniority["S001150"] == 2026 - (1789 + 2 * (107 - 1))
    assert "min_voteview_congress" in receipt["derivation"]
    assert receipt["bioguide_congress_pairs_with_additional_rows"] == 1


def test_lobby_forecast_mid_congress_move_prefers_senate_with_receipt():
    rows = [
        _voteview_transition_row("S001150", 118, "House", 20104, district=30),
        _voteview_transition_row("S001150", 118, "Senate", 20104, district=0),
    ]
    resolved, receipts = LF.resolve_voteview_congress_rows(rows)
    assert resolved[("S001150", 118)]["chamber"] == "Senate"
    assert len(receipts) == 1
    assert receipts[0]["rule"] == "mid_congress_chamber_move_prefer_senate"
    assert receipts[0]["selected_chamber"] == "Senate"
    assert receipts[0]["selected_icpsr"] == "20104"
    assert receipts[0]["discarded_rows"] == [
        {
            "chamber": "House",
            "state": "CA",
            "party_code": "100",
            "icpsr": "20104",
        }
    ]


def test_lobby_forecast_icpsr_difference_prefers_other_congress_match():
    rows = [
        _voteview_transition_row("A000367", 115, "House", 21143),
        _voteview_transition_row("A000367", 116, "House", 21143, party=328),
        _voteview_transition_row("A000367", 116, "House", 29999, party=328),
        _voteview_transition_row("A000367", 117, "House", 21143),
    ]
    resolved, receipts = LF.resolve_voteview_congress_rows(rows)
    assert resolved[("A000367", 116)]["icpsr"] == "21143"
    receipt = next(row for row in receipts if row["congress"] == 116)
    assert receipt["rule"] == "mid_congress_party_switch_carried_forward"
    assert receipt["selected_icpsr"] == "21143"
    assert receipt["discarded_rows"][0]["icpsr"] == "29999"


def test_lobby_forecast_same_chamber_conflicting_state_still_raises():
    rows = [
        _voteview_transition_row("X000001", 118, "House", 90001, state="CA"),
        _voteview_transition_row("X000001", 118, "House", 90001, state="NY"),
    ]
    try:
        LF.resolve_voteview_congress_rows(rows)
    except LF.ForecastError as exc:
        assert "contradictory same-bioguide/congress/chamber states" in str(exc)
    else:
        raise AssertionError("same-chamber conflicting states were not rejected")


def test_lobby_forecast_committee_congress_keys_normalize_to_int():
    normalized = LF.normalize_committee_by_congress(
        {118: {"A000001"}, "119": {"B000001"}}
    )
    assert sorted(normalized) == [118, 119]
    assert normalized[118] == {"A000001"}
    assert normalized[119] == {"B000001"}


def test_lobby_forecast_committee_error_names_only_genuine_missing():
    try:
        LF.require_committee_coverage(
            [117, 118, 119], {"118": set(), 119: set()}, allow_missing=False
        )
    except LF.ForecastError as exc:
        assert str(exc) == (
            "pinned finance-committee snapshot missing for Congress(es) 117"
        )
    else:
        raise AssertionError("missing Congress 117 did not fail loudly")


def _forecast_missing_committee_panel(allow_missing):
    member = {
        "member_name": "Fixture Member",
        "party": "D",
        "chamber": "rep",
        "seniority_years": 5,
    }
    return LF.build_panel(
        {
            "org-a": {
                2021: {"A000001": 2},
                2022: {"A000001": 1},
            }
        },
        [2021, 2022],
        {2021: {"A000001": member}, 2022: {"A000001": member}},
        {2021: {"A000001": 10}, 2022: {"A000001": 12}},
        {},
        {"org-a": {"side": "finance"}},
        min_org_dyads=1,
        allow_missing_committee=allow_missing,
    )


def test_lobby_forecast_allow_missing_committee_drops_split_feature():
    rows, panel_receipt = _forecast_missing_committee_panel(True)
    assert len(rows) == 1
    missing_row = rows[0]
    assert "finance_committee" not in missing_row
    assert "finance_committee" not in missing_row["_feature_source_years"]
    assert missing_row["_features_unavailable"] == ["finance_committee"]
    assert panel_receipt["features_excluded_for_missing_data"] == {
        "finance_committee": {
            "reason": LF.MISSING_COMMITTEE_REASON,
            "congresses": [117],
            "row_counts_by_congress": {"117": 1},
            "total_rows": 1,
        }
    }

    available_row = _forecast_fixture_row(year=2023, bioguide="B000001")
    available_row["_committee_congress"] = 118
    available_row["_features_unavailable"] = []
    excluded, split_receipt = LF.split_missing_feature_policy(
        [missing_row, available_row]
    )
    assert excluded == {"finance_committee"}
    preprocessor = LF.fit_preprocessor(
        [missing_row, available_row], excluded_features=excluded
    )
    matrix, unseen = LF.transform_rows(
        [missing_row, available_row], preprocessor
    )
    assert unseen == []
    assert len(matrix) == 2
    assert preprocessor["excluded_features"] == ["finance_committee"]
    assert all(
        not name.startswith("finance_committee=")
        for name in preprocessor["design_names"]
    )
    assert split_receipt["finance_committee"]["total_rows"] == 1


def test_lobby_forecast_missing_committee_without_flag_still_raises():
    try:
        _forecast_missing_committee_panel(False)
    except LF.ForecastError as exc:
        assert str(exc) == (
            "pinned finance-committee snapshot missing for Congress(es) 117"
        )
    else:
        raise AssertionError("missing committee snapshot was silently accepted")


def _forecast_churn_loss_metrics():
    rows = []
    for index, actual in enumerate((0, 1, 0, 1)):
        row = _forecast_fixture_row(bioguide=f"V{index:06d}")
        row["actual"] = actual
        row["baseline_persistence"] = 1 - actual
        row["predicted_probability"] = 0.9 if actual == 0 else 0.1
        row["baseline_popularity_probability"] = 0.1 if actual == 0 else 0.9
        rows.append(row)
    return LF.evaluate_split(rows)


def test_lobby_forecast_churn_headline_names_winning_popularity_baseline():
    metrics = _forecast_churn_loss_metrics()
    assert metrics["model"]["churn"]["accuracy"] == 0.0
    assert metrics["baselines"]["popularity"]["churn"]["accuracy"] == 1.0
    assert metrics["churn_verdict"]["outcome"] == "loss"
    assert metrics["churn_verdict"]["best_baseline"] == "popularity"
    assert metrics["headline"].startswith("MODEL LOSES ON CHURN:")
    assert "popularity 100.0% vs model 0.0%" in metrics["headline"]


def test_lobby_forecast_persistence_churn_is_annotated_structurally_zero():
    churn = _forecast_churn_loss_metrics()["baselines"]["persistence"]["churn"]
    assert churn["accuracy"] == 0.0
    assert churn["structurally_zero_by_construction"] is True
    assert "structurally 0%" in churn["annotation"]
    assert "predicts no change" in churn["annotation"]


def test_lobby_forecast_overall_verdict_counts_losses_and_leads_with_failure():
    outcomes = ("loss", "win", "loss")
    reports = []
    for index, outcome in enumerate(outcomes):
        reports.append(
            {
                "train_through": 2021 + index,
                "test_feature_year": 2022 + index,
                "metrics": {
                    "churn_verdict": {
                        "outcome": outcome,
                        "best_baseline": "popularity",
                        "best_baseline_churn_accuracy": 0.6,
                        "model_churn_accuracy": 0.4 if outcome == "loss" else 0.7,
                        "headline": outcome,
                    }
                },
            }
        )
    verdict = LF.overall_churn_verdict(reports)
    assert verdict["splits_evaluated"] == 3
    assert verdict["wins"] == 1
    assert verdict["losses"] == 2
    assert verdict["ties"] == 0
    assert verdict["headline"].startswith(
        "MODEL DOES NOT BEAT TRIVIAL BASELINES"
    )


def _cosponsor_voteview_member(bioguide, name, party=100, state="VA"):
    return {
        "bioguide_id": bioguide,
        "member_name": name,
        "congress": 117,
        "chamber": "House",
        "party_code": party,
        "state": state,
        "icpsr": bioguide[1:],
        "nominate_dim1": 0.0,
        "nominate_dim2": 0.0,
    }


def _cosponsor_synthetic_panel():
    sponsor = "S000001"
    candidate = "C000001"
    key = ("HR", 1, 117)
    metadata = {
        "sponsor_bioguide": sponsor,
        "cosponsors": (
            {"bioguide_id": candidate, "sponsorship_date": "2021-01-04"},
        ),
        "introduced_date": "2021-01-03",
        "origin_chamber": "House",
        "policy_area": "Banking",
        "committee_referrals": (),
    }
    universes = {
        117: {
            sponsor: _cosponsor_voteview_member(sponsor, "Sponsor"),
            candidate: _cosponsor_voteview_member(candidate, "Candidate"),
        }
    }
    rows, _receipt = CF.build_panel(
        [117],
        universes,
        {},
        {sponsor: 117, candidate: 117},
        {116: {"metadata": {}}, 117: {"metadata": {key: metadata}}},
        {117: {key}},
        {},
        min_cosponsors=0,
    )
    return rows


def test_cosponsor_forecast_no_leakage_and_sponsor_excluded():
    rows = _cosponsor_synthetic_panel()
    assert [row["bioguide_id"] for row in rows] == ["C000001"]
    assert rows[0]["sponsor_bioguide"] == "S000001"
    assert not (set(rows[0]) & CF.POST_INTRODUCTION_FIELDS)
    assert CF.assert_no_leakage(rows[0]) is True
    contaminated = dict(rows[0])
    contaminated["actions"] = ["Passed House"]
    try:
        CF.assert_no_leakage(contaminated)
    except CF.LeakageError as exc:
        assert "post-introduction" in str(exc)
    else:
        raise AssertionError("post-introduction field entered the design silently")


def test_cosponsor_forecast_prior_features_never_read_target_congress():
    row = dict(_cosponsor_synthetic_panel()[0])
    row["_feature_source_congresses"] = dict(row["_feature_source_congresses"])
    row["_feature_source_congresses"]["prior_member_cosponsorships"] = 117
    try:
        CF.assert_no_leakage(row)
    except CF.LeakageError as exc:
        assert "expected 116" in str(exc)
    else:
        raise AssertionError("target-Congress prior feature was accepted")


def _cosponsor_known_baseline_metrics():
    rows = []
    for index, actual in enumerate((1, 0, 1, 0)):
        rows.append(
            {
                "congress": 118,
                "bill": "HR 1",
                "bioguide_id": f"B{index:06d}",
                "actual": actual,
                "predicted_probability": 0.1 if actual else 0.9,
                "baseline_member_propensity": 4 - index,
                "baseline_member_propensity_probability": (4 - index) / 4.0,
                "baseline_sponsor_affinity": 3 if index == 2 else 0,
                "baseline_sponsor_affinity_probability": (
                    0.75 if index == 2 else 0.0
                ),
                "baseline_party_match": actual,
            }
        )
    return CF.evaluate_split(rows)


def test_cosponsor_forecast_three_baselines_known_structure():
    metrics = _cosponsor_known_baseline_metrics()
    assert math.isclose(
        metrics["baselines"]["B1_member_propensity"]["average_precision"],
        5.0 / 6.0,
    )
    assert math.isclose(
        metrics["baselines"]["B2_sponsor_affinity"]["average_precision"],
        0.75,
    )
    assert metrics["baselines"]["B3_party_match"]["average_precision"] == 1.0
    assert metrics["baselines"]["B3_party_match"]["brier"] == 0.0
    assert math.isclose(
        metrics["baselines"]["B1_member_propensity"]["brier"], 0.21875
    )
    assert math.isclose(
        metrics["baselines"]["B2_sponsor_affinity"]["brier"], 0.265625
    )


def test_cosponsor_forecast_headline_names_best_baseline_and_loss():
    metrics = _cosponsor_known_baseline_metrics()
    assert metrics["verdict"]["outcome"] == "loss"
    assert metrics["verdict"]["best_baseline"] == "B3_party_match"
    assert metrics["headline"].startswith("MODEL LOSES:")
    assert "B3_party_match" in metrics["headline"]


def test_cosponsor_forecast_rank_deficiency_detected_not_silent():
    result = CF.irls_logistic(
        [[1.0, 0.0, 0.0], [1.0, 1.0, 1.0], [1.0, 2.0, 2.0], [1.0, 3.0, 3.0]],
        [0, 0, 1, 1],
        ["intercept", "duplicated_a", "duplicated_b"],
    )
    assert result["rank_deficient"] is True
    assert result["design_rank"] < result["design_columns"]
    assert "detected before solve" in result["rank_deficiency_handling"]


def test_cosponsor_forecast_output_determinism():
    document = {
        "verdict": {"headline": "MODEL LOSES: fixture"},
        "per_split": [],
        "method_note": CF.METHOD_NOTE,
    }
    scores = [
        {
            "congress": 118,
            "bill": "HR 2",
            "bioguide_id": "B000002",
            "predicted_probability": 0.25,
            "actual": 0,
            "baseline_member_propensity": 2,
            "baseline_sponsor_affinity": 1,
            "baseline_party_match": 0,
        },
        {
            "congress": 118,
            "bill": "HR 1",
            "bioguide_id": "A000001",
            "predicted_probability": 0.75,
            "actual": 1,
            "baseline_member_propensity": 4,
            "baseline_sponsor_affinity": 3,
            "baseline_party_match": 1,
        },
    ]
    with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
        CF.write_outputs(first, document, scores)
        CF.write_outputs(second, document, list(reversed(scores)))
        for filename in ("cosponsor_forecast_report.json", "cosponsor_scores.csv"):
            with open(os.path.join(first, filename), "rb") as left:
                left_bytes = left.read()
            with open(os.path.join(second, filename), "rb") as right:
                assert left_bytes == right.read()


def test_cosponsor_forecast_voteview_universe_includes_cheney_fixture():
    rows = [
        {
            "congress": "117",
            "chamber": "House",
            "icpsr": "21504",
            "state_abbrev": "WY",
            "district_code": "1",
            "party_code": "200",
            "bioname": "CHENEY, Liz",
            "bioguide_id": "C001109",
            "nominate_dim1": "0.45",
            "nominate_dim2": "0.02",
        },
        {
            "congress": "117",
            "chamber": "House",
            "icpsr": "99999",
            "state_abbrev": "VA",
            "district_code": "1",
            "party_code": "100",
            "bioname": "FIXTURE, Member",
            "bioguide_id": "F000001",
            "nominate_dim1": "-0.2",
            "nominate_dim2": "0.0",
        },
    ]
    universes, _resolved, _earliest, receipt = CF.build_candidate_universes(
        rows, [117], enforce_expected=False
    )
    assert "C001109" in universes[117]
    assert receipt["current_roster_consulted"] is False


def test_cosponsor_forecast_streamed_normal_equations_match_direct_solve():
    matrix = [
        [1.0, -1.5, 0.0],
        [1.0, -1.0, 1.0],
        [1.0, -0.5, 0.0],
        [1.0, 0.0, 1.0],
        [1.0, 0.5, 0.0],
        [1.0, 1.0, 1.0],
        [1.0, 1.5, 0.0],
        [1.0, 2.0, 1.0],
    ]
    outcomes = [0, 0, 0, 1, 0, 1, 1, 1]
    names = ["intercept", "continuous", "binary"]
    direct = CF.irls_logistic(matrix, outcomes, names)
    design = CF.np.asarray(matrix, dtype=float)
    target = CF.np.asarray(outcomes, dtype=float)

    def chunks():
        for start in range(0, len(matrix), 3):
            stop = min(len(matrix), start + 3)
            yield design[start:stop], target[start:stop]

    streamed = CF.irls_logistic_streaming(len(matrix), names, chunks)
    for direct_value, streamed_value in zip(direct["beta"], streamed["beta"]):
        assert abs(direct_value - streamed_value) <= 1e-9
    assert streamed["normal_equations_streamed"] is True


def test_cosponsor_forecast_streamed_auc_matches_direct_fixture():
    scores = [0.9, 0.2, 0.7, 0.7, 0.1, 0.55, 0.4, 0.95]
    actual = [1, 0, 0, 1, 0, 1, 1, 0]
    direct = CF.auc_score(actual, scores)
    with tempfile.TemporaryDirectory() as work_dir:
        streamed = CF.streamed_auc_for_fixture(
            scores, actual, work_dir, chunk_rows=3
        )
    assert abs(direct - streamed) <= 1e-12


def test_cosponsor_forecast_gram_rank_deficiency_detected():
    design = CF.np.asarray(
        [[1.0, 0.0, 0.0], [1.0, 1.0, 2.0], [1.0, 2.0, 4.0], [1.0, 3.0, 6.0]],
        dtype=float,
    )
    receipt = CF._gram_rank_receipt(design.T @ design)
    assert receipt["rank_deficient"] is True
    assert receipt["design_rank"] < receipt["design_columns"]
    assert receipt["gram_pivoted_qr_rank"] < receipt["design_columns"]
    assert receipt["gram_svd_rank"] < receipt["design_columns"]
    assert receipt["condition_number_scale"].startswith("X'WX Gram scale")


def test_cosponsor_forecast_campbell_switch_carries_forward_identity():
    rows = [
        _voteview_transition_row("C000077", 103, "Senate", 15407, state="CO", party=100),
        {
            **_voteview_transition_row(
                "C000077", 104, "Senate", 15407, state="CO", party=100
            ),
            "nominate_dim1": "-0.141",
            "nominate_dim2": "0.07",
        },
        {
            **_voteview_transition_row(
                "C000077", 104, "Senate", 95407, state="CO", party=200
            ),
            "nominate_dim1": "0.23",
            "nominate_dim2": "0.132",
        },
        _voteview_transition_row("C000077", 105, "Senate", 95407, state="CO", party=200),
    ]
    resolved, receipts = LF.resolve_voteview_congress_rows(rows)
    assert resolved[("C000077", 104)]["icpsr"] == "95407"
    receipt = next(row for row in receipts if row["congress"] == 104)
    assert receipt["rule"] == "mid_congress_party_switch_carried_forward"
    assert receipt["selected_party_code"] == "200"
    assert receipt["discarded_rows"] == [
        {
            "chamber": "Senate",
            "state": "CO",
            "party_code": "100",
            "icpsr": "15407",
        }
    ]


def test_cosponsor_forecast_final_congress_switch_uses_higher_icpsr():
    rows = [
        _voteview_transition_row("F000099", 117, "House", 20002, state="OH", party=100),
        _voteview_transition_row("F000099", 118, "House", 20002, state="OH", party=100),
        _voteview_transition_row("F000099", 118, "House", 90002, state="OH", party=200),
    ]
    resolved, receipts = LF.resolve_voteview_congress_rows(rows)
    assert resolved[("F000099", 118)]["icpsr"] == "90002"
    receipt = next(row for row in receipts if row["congress"] == 118)
    assert receipt["rule"] == "mid_congress_party_switch_higher_icpsr_tiebreak"
    assert receipt["following_congress"] == 119
    assert receipt["discarded_rows"][0]["icpsr"] == "20002"


def test_cosponsor_forecast_out_of_scope_voteview_conflict_is_not_validated():
    rows = [
        _voteview_transition_row("A000001", 118, "House", 22001, state="VA"),
        _voteview_transition_row("A000001", 119, "House", 22001, state="VA"),
        _voteview_transition_row("X000050", 50, "House", 50001, state="CA"),
        _voteview_transition_row("X000050", 50, "House", 50001, state="NY"),
    ]
    universes, resolved, _earliest, receipt = CF.build_candidate_universes(
        rows, [118, 119], enforce_expected=False
    )
    assert sorted(universes) == [118, 119]
    assert ("X000050", 50) not in resolved
    assert receipt["identity_rows_loaded_congresses"] == [117, 118, 119]
    assert receipt["identity_rows_outside_scope_ignored"] == 2


def test_cosponsor_forecast_in_scope_state_conflict_still_raises():
    rows = [
        _voteview_transition_row("X000118", 118, "House", 90001, state="CA"),
        _voteview_transition_row("X000118", 118, "House", 90001, state="NY"),
    ]
    try:
        CF.build_candidate_universes(rows, [118], enforce_expected=False)
    except CF.ForecastError as exc:
        assert "contradictory same-bioguide/congress/chamber states" in str(exc)
    else:
        raise AssertionError("in-scope Voteview state conflict was not rejected")


def _cosponsor_same_chamber_fixture_panels():
    sponsor = "S000001"
    house_member = "H000001"
    senate_member = "N000001"
    key = ("HR", 7, 117)
    metadata = {
        "sponsor_bioguide": sponsor,
        "cosponsors": (
            {"bioguide_id": house_member, "sponsorship_date": "2021-01-04"},
        ),
        "introduced_date": "2021-01-03",
        "origin_chamber": "House",
        "policy_area": "Banking",
        "committee_referrals": (),
    }
    senate_row = _cosponsor_voteview_member(senate_member, "Senate Member")
    senate_row["chamber"] = "Senate"
    universes = {
        117: {
            sponsor: _cosponsor_voteview_member(sponsor, "Sponsor"),
            house_member: _cosponsor_voteview_member(house_member, "House Member"),
            senate_member: senate_row,
        }
    }
    arguments = (
        [117],
        universes,
        {},
        {sponsor: 117, house_member: 117, senate_member: 117},
        {116: {"metadata": {}}, 117: {"metadata": {key: metadata}}},
        {117: {key}},
        {},
    )
    unrestricted, unrestricted_receipt = CF.build_panel(
        *arguments, min_cosponsors=0, same_chamber_only=False
    )
    restricted, restricted_receipt = CF.build_panel(
        *arguments, min_cosponsors=0, same_chamber_only=True
    )
    return unrestricted, unrestricted_receipt, restricted, restricted_receipt


def test_cosponsor_forecast_same_chamber_only_excludes_and_drops_constant():
    _unrestricted, _receipt, restricted, restricted_receipt = (
        _cosponsor_same_chamber_fixture_panels()
    )
    assert [row["bioguide_id"] for row in restricted] == ["H000001"]
    assert restricted_receipt["per_congress"]["117"][
        "structurally_impossible_cross_chamber_rows_excluded"
    ] == 1
    excluded, _missing = CF.split_missing_feature_policy(restricted, [117])
    preprocessor = CF.fit_columnar_preprocessor(
        restricted, 117, excluded_features=excluded
    )
    assert "same_chamber" in preprocessor["dropped_zero_variance_features"]
    assert "same_chamber" not in preprocessor["design_names"]


def test_cosponsor_forecast_candidate_configurations_have_correct_base_rates():
    unrestricted, unrestricted_receipt, restricted, restricted_receipt = (
        _cosponsor_same_chamber_fixture_panels()
    )
    assert len(unrestricted) == 2
    assert len(restricted) == 1
    assert unrestricted_receipt["per_congress"]["117"]["base_rate"] == 0.5
    assert restricted_receipt["per_congress"]["117"]["base_rate"] == 1.0


def test_cosponsor_forecast_penalized_standard_errors_finite_positive():
    matrix = CF.np.asarray(
        [
            [1.0, -2.0, 0.0],
            [1.0, -1.0, 1.0],
            [1.0, -0.5, 0.0],
            [1.0, 0.0, 1.0],
            [1.0, 0.5, 0.0],
            [1.0, 1.0, 1.0],
            [1.0, 1.5, 0.0],
            [1.0, 2.0, 1.0],
        ],
        dtype=float,
    )
    outcomes = CF.np.asarray([0, 0, 0, 1, 0, 1, 1, 1], dtype=float)

    def chunks():
        for start in range(0, len(outcomes), 3):
            stop = min(len(outcomes), start + 3)
            yield matrix[start:stop], outcomes[start:stop]

    fit = CF.irls_logistic_streaming(
        len(outcomes), ["intercept", "continuous", "binary"], chunks
    )
    for row in fit["coefficients"]:
        assert math.isfinite(row["se"])
        assert row["se"] > 0.0
        assert row["se"] == row["standard_error"]


def test_cosponsor_forecast_policy_area_coefficients_carry_bill_counts():
    panel = _cosponsor_synthetic_panel()
    counts = CF.policy_area_bill_counts(panel, 117)
    table = [
        {"feature": "policy_area=Banking", "coefficient": 1.0},
        {"feature": "same_party", "coefficient": 0.5},
    ]
    CF.annotate_policy_area_coefficients(table, counts)
    assert table[0]["policy_area_training_bill_count"] == 1
    assert "policy_area_training_bill_count" not in table[1]


def _sector_filing(
    filing_uuid,
    client_id,
    client_name,
    income="100.00",
    expenses=None,
    filing_year=2025,
    filing_period="first_quarter",
    filing_type="Q1",
    filing_type_display="1st Quarter - Report",
    dt_posted="2025-04-15T12:00:00-04:00",
    registrant_id=9001,
):
    return {
        "filing_uuid": filing_uuid,
        "filing_year": filing_year,
        "filing_period": filing_period,
        "filing_type": filing_type,
        "filing_type_display": filing_type_display,
        "dt_posted": dt_posted,
        "income": income,
        "expenses": expenses,
        "client": {"id": client_id, "name": client_name},
        "registrant": {"id": registrant_id, "name": f"Registrant {registrant_id}"},
        "lobbying_activities": [
            {
                "general_issue_code": "FIN",
                "description": "Synthetic financial-services issue",
                "government_entities": [],
                "lobbyists": [
                    {
                        "lobbyist": {
                            "id": registrant_id + 10000,
                            "first_name": "Test",
                            "last_name": "Lobbyist",
                        },
                        "covered_position": None,
                    }
                ],
            }
        ],
    }


def _sector_year(document, sector, year):
    return next(
        row for row in document["sectors"][sector]["years"] if row["year"] == year
    )


def test_sector_spend_amendment_supersession_latest_dt_and_receipt():
    original = _sector_filing(
        "amend-original",
        101,
        "Coinbase, Inc.",
        income="100.00",
        dt_posted="2025-04-15T12:00:00-04:00",
    )
    amendment = _sector_filing(
        "amend-latest",
        101,
        "Coinbase, Inc.",
        income="250.00",
        filing_type="1A",
        filing_type_display="1st Quarter - Report Amendment",
        dt_posted="2025-05-01T09:00:00-04:00",
    )
    document, _roster = SS.measure_filings(
        [amendment, original], years=(2025,), sectors=("crypto",)
    )
    annual = _sector_year(document, "crypto", 2025)
    assert annual["filings"] == 1
    assert annual["income_total"] == 250
    receipt = document["receipts"]["amendment_supersession"]
    assert receipt["records_superseded"] == 1
    assert receipt["groups_retained"] == 1


def test_sector_spend_registration_types_excluded_and_receipted():
    filings = [
        _sector_filing(
            "registration",
            102,
            "Coinbase",
            income=None,
            filing_type="RR",
            filing_type_display="Registration",
        ),
        _sector_filing(
            "registration-amendment",
            102,
            "Coinbase",
            income=None,
            filing_type="RA",
            filing_type_display="Registration - Amendment",
        ),
        _sector_filing("financial-report", 102, "Coinbase", income="75.00"),
    ]
    document, _roster = SS.measure_filings(
        filings, years=(2025,), sectors=("crypto",)
    )
    receipt = document["receipts"]["filing_type_exclusions"]
    assert receipt["records_excluded"] == 2
    assert {row["filing_type"] for row in receipt["types"]} == {"RA", "RR"}
    assert _sector_year(document, "crypto", 2025)["filings"] == 1


def test_sector_spend_components_support_exact_total():
    filing = _sector_filing(
        "separate-series", 103, "Coinbase", income="100.00", expenses="40.00"
    )
    document, _roster = SS.measure_filings(
        [filing], years=(2025,), sectors=("crypto",)
    )
    assert set(document["financial_series"]) == {"income_total", "expenses_total"}
    annual = _sector_year(document, "crypto", 2025)
    assert annual["income_total"] == 100
    assert annual["expenses_total"] == 40
    assert annual["income_total"] + annual["expenses_total"] == 140


def test_sector_spend_cuna_nafcu_dba_variants_one_family():
    variants = [
        (56159, "CREDIT UNION NATIONAL ASSOC INC. DBA AMERICA'S CREDIT UNIONS (FORMERLY NAFCU)"),
        (110165, "CREDIT UNION NATIONAL ASSOCIATION, INC. DBA AMERICAS CREDIT UNIONS"),
        (115381, "CREDIT UNION NATIONAL ASSOCIATION, INC. DBA AMERICA'S CREDIT UNIONS"),
        (192149, "CREDIT UNION NATIONAL ASSOCIATION INC. D/B/A AMERICA'S CREDIT UNIONS"),
        (56184, "CREDIT UNION NATIONAL ASSOCIATION. INC. DBA AMERICA'S CREDIT UNIONS"),
    ]
    filings = [
        _sector_filing(
            f"cuna-{index}",
            client_id,
            name,
            registrant_id=9100 + index,
        )
        for index, (client_id, name) in enumerate(variants)
    ]
    document, roster = SS.measure_filings(
        filings, years=(2025,), sectors=("credit_union",)
    )
    annual = _sector_year(document, "credit_union", 2025)
    assert annual["distinct_organizations"] == 1
    assert [row["canonical_family"] for row in roster] == [
        "AMERICA'S CREDIT UNIONS"
    ]
    assert len(roster[0]["raw_name_variants"]) == 5
    assert set(roster[0]["client_ids"]) == {str(item[0]) for item in variants}


def test_sector_spend_individual_excluded_and_reported_separately():
    filings = [
        _sector_filing("coinbase", 104, "Coinbase", income="50.00"),
        _sector_filing(
            "roger-ver",
            64731,
            "Roger Ver",
            income="600000.00",
            registrant_id=9200,
        ),
    ]
    document, _roster = SS.measure_filings(
        filings, years=(2025,), sectors=("crypto",)
    )
    annual = _sector_year(document, "crypto", 2025)
    assert annual["filings"] == 1
    assert annual["income_total"] == 50
    excluded = document["excluded_individuals"]
    assert len(excluded) == 1
    assert excluded[0]["canonical_family"] == "ROGER VER"
    assert excluded[0]["client_ids"] == ["64731"]
    assert excluded[0]["income_total"] == 600000


def test_sector_spend_2026_is_partial_year():
    filing = _sector_filing(
        "partial-2026",
        105,
        "Coinbase",
        filing_year=2026,
        dt_posted="2026-04-15T12:00:00-04:00",
    )
    document, _roster = SS.measure_filings(
        [filing], years=(2026,), sectors=("crypto",)
    )
    annual = _sector_year(document, "crypto", 2026)
    assert annual["is_partial_year"] is True
    assert all(quarter["is_partial_year"] is True for quarter in annual["quarters"])


def test_sector_spend_output_determinism():
    first = _sector_filing("det-a", 106, "Coinbase", income="125.00")
    second = _sector_filing(
        "det-b",
        107,
        "Blockchain Association",
        income="75.00",
        filing_period="second_quarter",
        filing_type="Q2",
        filing_type_display="2nd Quarter - Report",
        dt_posted="2025-07-15T12:00:00-04:00",
        registrant_id=9300,
    )
    duplicate = dict(first)
    document_a, roster_a = SS.measure_filings(
        [first, second, duplicate], years=(2025,), sectors=("crypto",)
    )
    document_b, roster_b = SS.measure_filings(
        [duplicate, second, first], years=(2025,), sectors=("crypto",)
    )
    assert document_a == document_b
    assert roster_a == roster_b
    with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
        SS.write_outputs(left, document_a, roster_a)
        SS.write_outputs(right, document_b, roster_b)
        for filename in ("sector_spend.json", "sector_spend.csv", "sector_roster.csv"):
            with open(os.path.join(left, filename), "rb") as handle:
                left_bytes = handle.read()
            with open(os.path.join(right, filename), "rb") as handle:
                assert left_bytes == handle.read()


def _write_industry_csv(path, fieldnames, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


# The page spans 2021-2026, so the fixture deliberately carries three member
# shapes: one sitting member, one who has left office (McHenry, real bioguide),
# and one that no roster or Voteview row names at all.
FIXTURE_SITTING_MEMBER = "M000001"
FIXTURE_FORMER_MEMBER = "M001156"
FIXTURE_UNKNOWN_MEMBER = "Z999999"
FIXTURE_BLANK_NAME_MEMBER = "M000002"


def _identity_fixture(data_root):
    """Write the three member-name sources the page resolves names from."""
    with open(
        os.path.join(data_root, "congestion.json"), "w", encoding="utf-8"
    ) as handle:
        json.dump(
            [
                {"member": "Fixture Member", "bioguide": FIXTURE_SITTING_MEMBER},
                {"member": "Blank Roster Member", "bioguide": FIXTURE_BLANK_NAME_MEMBER},
            ],
            handle,
            sort_keys=True,
        )
    _write_industry_csv(
        os.path.join(data_root, "legislators.csv"),
        ["bioguide_id", "full_name", "party", "type"],
        [
            {
                "bioguide_id": FIXTURE_SITTING_MEMBER,
                "full_name": "Fixture Member",
                "party": "Independent",
                "type": "rep",
            },
            {
                # legislators.csv really does carry roster rows with no
                # full_name; congestion.json has to answer for them.
                "bioguide_id": FIXTURE_BLANK_NAME_MEMBER,
                "full_name": "",
                "party": "Democrat",
                "type": "rep",
            },
        ],
    )
    _write_industry_csv(
        os.path.join(data_root, "HSall_members.csv"),
        [
            "congress",
            "chamber",
            "icpsr",
            "state_abbrev",
            "party_code",
            "bioname",
            "bioguide_id",
        ],
        [
            {
                "congress": 118,
                "chamber": "House",
                "icpsr": 20301,
                "state_abbrev": "NC",
                "party_code": 200,
                "bioname": "McHENRY, Patrick T.",
                "bioguide_id": FIXTURE_FORMER_MEMBER,
            },
            {
                "congress": 119,
                "chamber": "House",
                "icpsr": 20302,
                "state_abbrev": "XX",
                "party_code": 328,
                "bioname": "FIXTURE, Sitting",
                "bioguide_id": FIXTURE_SITTING_MEMBER,
            },
        ],
    )


def _industry_html_fixture(data_root):
    organization = "org-1"
    organization_two = "org-2"
    member = "M000001"
    champion_dir = os.path.join(data_root, "champions_fullscope")
    spend_dir = os.path.join(data_root, "sector_spend")
    forecast_dir = os.path.join(data_root, "cosponsor_sc")
    os.makedirs(champion_dir, exist_ok=True)
    os.makedirs(spend_dir, exist_ok=True)
    os.makedirs(forecast_dir, exist_ok=True)

    _identity_fixture(data_root)
    for year in MLN.YEARS:
        _write_industry_csv(
            os.path.join(
                data_root, f"our_network_fullscope_{year}_strict.csv"
            ),
            ["lob_id", "bioguide_id", "year", "n_bills"],
            [
                {
                    "lob_id": organization,
                    "bioguide_id": member,
                    "year": year,
                    "n_bills": year - 2020,
                },
                {
                    "lob_id": organization,
                    "bioguide_id": FIXTURE_FORMER_MEMBER,
                    "year": year,
                    "n_bills": 2,
                },
                {
                    "lob_id": organization,
                    "bioguide_id": FIXTURE_UNKNOWN_MEMBER,
                    "year": year,
                    "n_bills": 1,
                },
            ],
        )
    _write_industry_csv(
        os.path.join(data_root, "fullscope_org_roster.csv"),
        [
            "lob_id_or_client_id",
            "client_name",
            "source_flags",
            "first_year_seen",
            "last_year_seen",
        ],
        [
            {
                "lob_id_or_client_id": organization,
                "client_name": "Fixture Credit Union",
                "source_flags": "fixture",
                "first_year_seen": 2021,
                "last_year_seen": 2026,
            },
            {
                "lob_id_or_client_id": organization_two,
                "client_name": "Second Fixture Bank",
                "source_flags": "fixture",
                "first_year_seen": 2021,
                "last_year_seen": 2026,
            }
        ],
    )
    _write_industry_csv(
        os.path.join(spend_dir, "sector_roster.csv"),
        [
            "sector",
            "canonical_family",
            "raw_name_variants",
            "normalized_name_variants",
            "matched_pattern",
            "client_ids",
            "collapse_rules",
            "first_year_seen",
            "last_year_seen",
        ],
        [
            {
                "sector": "credit_union",
                "canonical_family": "FIXTURE CREDIT UNION",
                "raw_name_variants": "Fixture Credit Union",
                "normalized_name_variants": "FIXTURE CREDIT UNION",
                "matched_pattern": "fixture",
                "client_ids": organization,
                "collapse_rules": "fixture",
                "first_year_seen": 2021,
                "last_year_seen": 2026,
            }
        ],
    )
    with open(
        os.path.join(spend_dir, "sector_spend.json"), "w", encoding="utf-8"
    ) as handle:
        json.dump(
            {
                "selected_sectors": ["credit_union"],
            },
            handle,
            sort_keys=True,
        )
    spend_rows = []
    for year in MLN.YEARS:
        spend_rows.append(
            {
                "sector": "credit_union",
                "year": year,
                "period": "annual",
                "is_partial_year": str(year == 2026).lower(),
                "distinct_organizations": 1,
                "filings": 2,
                "income_total": 111111,
                "expenses_total": 222222,
                "distinct_registrants": 1,
                "distinct_named_lobbyists": 3,
                "top_1_income_share": 1,
                "top_3_income_share": 1,
                "top_10_income_share": 1,
                "income_hhi": 1,
            }
        )
    _write_industry_csv(
        os.path.join(spend_dir, "sector_spend.csv"),
        [
            "sector",
            "year",
            "period",
            "is_partial_year",
            "distinct_organizations",
            "filings",
            "income_total",
            "expenses_total",
            "distinct_registrants",
            "distinct_named_lobbyists",
            "top_1_income_share",
            "top_3_income_share",
            "top_10_income_share",
            "income_hhi",
        ],
        spend_rows,
    )

    champion_metadata = {
        "lob_id": organization,
        "covered_years": list(MLN.YEARS),
        "controls_used": ["log1p_seniority", "chamber", "party"],
        "r2": 0.25,
        "n_members_modeled": 1,
        "skipped_reason": None,
        "champions": [],
    }
    with open(
        os.path.join(champion_dir, "champions.json"), "w", encoding="utf-8"
    ) as handle:
        json.dump({"per_org": [champion_metadata]}, handle, sort_keys=True)
    champion_fields = [
        "lob_id",
        "org_name",
        "org_side",
        "covered_years",
        "controls_used",
        "bioguide_id",
        "member_name",
        "party",
        "chamber",
        "champion_rank",
        "champion_score",
        "sector_relative_score",
        "sector_rank",
        "raw_n_bills",
        "years_present",
        "direction_of_travel",
        "r2",
        "n_members_modeled",
    ]
    _write_industry_csv(
        os.path.join(champion_dir, "champions.csv"),
        champion_fields,
        [
            {
                "lob_id": organization,
                "org_name": "Fixture Credit Union",
                "org_side": "credit_union",
                "covered_years": "[2021,2022,2023,2024,2025,2026]",
                "controls_used": '["log1p_seniority","chamber","party"]',
                "bioguide_id": member,
                "member_name": "Fixture Member",
                "party": "I",
                "chamber": "rep",
                "champion_rank": 1,
                "champion_score": 1.5,
                "sector_relative_score": "",
                "sector_rank": "",
                "raw_n_bills": 21,
                "years_present": 6,
                "direction_of_travel": "increasing",
                "r2": 0.25,
                "n_members_modeled": 1,
            }
        ],
    )

    metric_values = {
        "auc": 0.7,
        "average_precision": 0.3,
        "precision_at_10": 0.4,
        "precision_at_25": 0.35,
        "precision_at_50": 0.3,
    }
    baselines = {
        "B1_member_propensity": dict(metric_values, average_precision=0.1),
        "B2_sponsor_affinity": dict(metric_values, average_precision=0.2),
        "B3_party_match": dict(metric_values, average_precision=0.15),
    }
    forecast_report = {
        "headline_candidate_configuration": "same_chamber_only",
        "candidate_configurations": {
            "same_chamber_only": {
                "role": "defensible_headline",
                "same_chamber_only": True,
                "reader_should_quote": True,
                "per_split": [
                    {
                        "role": "primary",
                        "train_congress": 118,
                        "test_congress": 119,
                        "metrics": {
                            "base_rate": 0.05,
                            "model": metric_values,
                            "baselines": baselines,
                        },
                    }
                ],
                "verdict": {
                    "headline": "MODEL WINS: fixture model beats best baseline",
                    "comparison_rule": "best of all three baselines within the split",
                },
            }
        },
    }
    with open(
        os.path.join(forecast_dir, "cosponsor_forecast_report.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(forecast_report, handle, sort_keys=True)
    score_fields = [
        "candidate_configuration",
        "congress",
        "bill",
        "member",
        "predicted_probability",
        "actual",
        "baseline_member_propensity",
        "baseline_member_propensity_probability",
        "baseline_sponsor_affinity",
        "baseline_sponsor_affinity_probability",
        "baseline_party_match",
    ]
    _write_industry_csv(
        os.path.join(forecast_dir, "cosponsor_scores.csv"),
        score_fields,
        [
            {
                "candidate_configuration": "same_chamber_only",
                "congress": 119,
                "bill": "HR 1",
                "member": member,
                "predicted_probability": 0.75,
                "actual": 1,
                "baseline_member_propensity": 1,
                "baseline_member_propensity_probability": 0.1,
                "baseline_sponsor_affinity": 1,
                "baseline_sponsor_affinity_probability": 0.2,
                "baseline_party_match": 1,
            },
            {
                "candidate_configuration": "same_chamber_only",
                "congress": 119,
                "bill": "HR 1",
                "member": FIXTURE_FORMER_MEMBER,
                "predicted_probability": 0.6,
                "actual": 0,
                "baseline_member_propensity": 1,
                "baseline_member_propensity_probability": 0.1,
                "baseline_sponsor_affinity": 1,
                "baseline_sponsor_affinity_probability": 0.2,
                "baseline_party_match": 1,
            },
            {
                "candidate_configuration": "same_chamber_only",
                "congress": 119,
                "bill": "HR 1",
                "member": FIXTURE_UNKNOWN_MEMBER,
                "predicted_probability": 0.5,
                "actual": 0,
                "baseline_member_propensity": 1,
                "baseline_member_propensity_probability": 0.1,
                "baseline_sponsor_affinity": 1,
                "baseline_sponsor_affinity_probability": 0.2,
                "baseline_party_match": 1,
            },
        ],
    )

    bill_fields = [
        "congress",
        "bill_type",
        "bill_number",
        "bill_key",
        "lob_id",
        "client_name",
        "org_sector",
        "n_filings",
        "n_activities",
        "first_filing_period",
        "last_filing_period",
        "channel",
    ]
    for year in MLN.YEARS:
        _write_industry_csv(
            os.path.join(data_root, f"our_bill_lobby_index_{year}.csv"),
            bill_fields,
            [
                {
                    "congress": 117,
                    "bill_type": "hr",
                    "bill_number": 1215,
                    "bill_key": "117:hr:1215",
                    "lob_id": organization,
                    "client_name": "Fixture Credit Union",
                    "org_sector": "credit_union",
                    "n_filings": 1,
                    "n_activities": 2,
                    "first_filing_period": "first_quarter",
                    "last_filing_period": "first_quarter",
                    "channel": "formal_strict",
                },
                {
                    "congress": 117,
                    "bill_type": "hr",
                    "bill_number": 1215,
                    "bill_key": "117:hr:1215",
                    "lob_id": organization_two,
                    "client_name": "Second Fixture Bank",
                    "org_sector": "bank",
                    "n_filings": 2,
                    "n_activities": 3,
                    "first_filing_period": "second_quarter",
                    "last_filing_period": "second_quarter",
                    "channel": "title_strict",
                },
                {
                    "congress": 118,
                    "bill_type": "hr",
                    "bill_number": 1181,
                    "bill_key": "118:hr:1181",
                    "lob_id": organization,
                    "client_name": "Fixture Credit Union",
                    "org_sector": "credit_union",
                    "n_filings": 3,
                    "n_activities": 3,
                    "first_filing_period": "third_quarter",
                    "last_filing_period": "third_quarter",
                    "channel": "both_strict",
                },
                {
                    "congress": 119,
                    "bill_type": "s",
                    "bill_number": 9999,
                    "bill_key": "119:s:9999",
                    "lob_id": organization,
                    "client_name": "Fixture Credit Union",
                    "org_sector": "credit_union",
                    "n_filings": 1,
                    "n_activities": 1,
                    "first_filing_period": "fourth_quarter",
                    "last_filing_period": "fourth_quarter",
                    "channel": "title_generous_only",
                },
            ],
        )
    with open(
        os.path.join(data_root, "our_bill_lobby_index_manifest.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            {
                "CORPUS_BASIS": "fixture:fullscope",
                "corpus_basis_invariant": "fixture invariant",
                "repository_join": {"lobbied_distinct_bills": 3},
                "years": {
                    str(year): {
                        "CORPUS_BASIS": "fixture:fullscope",
                        "rows": 4,
                        "distinct_bills": 3,
                        "distinct_orgs": 2,
                    }
                    for year in MLN.YEARS
                },
            },
            handle,
            sort_keys=True,
        )
    _write_industry_csv(
        os.path.join(data_root, "our_bill_repository_join.csv"),
        ["bill_key", "canonical_key", "bill_type", "join_status"],
        [
            {
                "bill_key": "117:hr:1215",
                "canonical_key": "117:hr:1215",
                "bill_type": "hr",
                "join_status": "matched",
            },
            {
                "bill_key": "118:hr:1181",
                "canonical_key": "",
                "bill_type": "hr",
                "join_status": "lobbying_only",
            },
            {
                "bill_key": "119:s:9999",
                "canonical_key": "",
                "bill_type": "s",
                "join_status": "lobbying_only",
            },
            {
                "bill_key": "118:samdt:42",
                "canonical_key": "118:samdt:42",
                "bill_type": "samdt",
                "join_status": "repository_only",
            },
        ],
    )
    _write_industry_csv(
        os.path.join(data_root, "bill_directions.csv"),
        ["Bill", "Congress", "Category", "Direction", "Note"],
        [
            {
                "Bill": "H.R.1215",
                "Congress": 117,
                "Category": "CFPB:Neutral",
                "Direction": 0,
                "Note": "real neutral fixture",
            },
            {
                "Bill": "H.R. 1181",
                "Congress": 118,
                "Category": "Payments:Support",
                "Direction": 1,
                "Note": "display spelling intentionally differs",
            },
        ],
    )
    _write_industry_csv(
        os.path.join(data_root, "bills_audit.csv"),
        ["section", "bill", "title", "n_cosponsors", "congresses", "flagged"],
        [
            {
                "section": "CFPB Issues & Structural Reform",
                "bill": "H.R.1215",
                "title": "Fraud and Scam Reduction Act",
                "n_cosponsors": 25,
                "congresses": "117",
                "flagged": "",
            },
            {
                "section": "Payments",
                "bill": "H.R.1181",
                "title": "Fixture Payments Act",
                "n_cosponsors": 4,
                "congresses": "118",
                "flagged": "",
            },
            {
                "section": "Fixture",
                "bill": "S.9999",
                "title": "Unmarked Fixture Act",
                "n_cosponsors": 0,
                "congresses": "119",
                "flagged": "",
            },
        ],
    )


def _identity_paths(data_root):
    return {
        "congestion_path": os.path.join(data_root, "congestion.json"),
        "legislators_path": os.path.join(data_root, "legislators.csv"),
        "voteview_path": os.path.join(data_root, "HSall_members.csv"),
    }


def _build_industry_fixture(directory, filename="lobby-network.html"):
    data_root = os.path.join(directory, "derived")
    os.makedirs(data_root, exist_ok=True)
    _industry_html_fixture(data_root)
    output = os.path.join(directory, filename)
    document = MLN.build(
        data_root,
        output,
        bill_directions_path=os.path.join(data_root, "bill_directions.csv"),
        bills_audit_path=os.path.join(data_root, "bills_audit.csv"),
        **_identity_paths(data_root),
    )
    with open(output, "rb") as handle:
        output_bytes = handle.read()
    return document, output_bytes, data_root


def test_industry_html_total_is_exact_component_sum_with_precision_note():
    with tempfile.TemporaryDirectory() as directory:
        document, _output, data_root = _build_industry_fixture(directory)
        spend = MLN._load_spend(
            os.path.join(data_root, "sector_spend", "sector_spend.json"),
            os.path.join(data_root, "sector_spend", "sector_spend.csv"),
            ["credit_union"],
        )
    latest = spend["credit_union"][-1]
    assert latest["total"] == latest["hired_firms"] + latest["in_house"]
    assert latest["total"] == 333333
    assert "$111.1k" in document
    assert "$222.2k" in document
    assert "$333.3k" in document
    assert MLN._money(940000) == "$940k"
    assert MLN._money(1200000) == "$1.2M"
    assert "Total lobbying spend" in document
    assert "Hired firms" in document
    assert "In-house" in document
    assert document.count(MLN.SPEND_PRECISION_NOTE) == 1


def test_industry_html_null_sector_score_renders_em_dash():
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    assert '"s":null' in document
    assert 'const EM_DASH="—"' in document
    assert "row.s===null" in document
    assert "shown as “—”, never zero" in document


def test_industry_html_marks_2026_partial_year():
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    assert "2026 · PARTIAL YEAR through Q2" in document
    assert "2026 (partial year)" in document
    assert "2026 partial Δ" in document


def test_industry_html_is_self_contained():
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    assert "http://" not in document
    assert "https://" not in document
    assert "<script" in document
    assert "<style>" in document


def test_industry_html_is_not_a_one_way_trap():
    """BUG (product owner, 2026-08-02): the dashboard links OUT to this page and the page
    offered no way back.  Every surface reachable from the dashboard needs a route home, and
    the dashboard artifact is the one make_dashboard_html.py writes -- 'Moneyball.html' is the
    combined shell, a different file."""
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    header = document.split("<header class=product-header>", 1)[1].split("</header>", 1)[0]
    assert 'href="Moneyball Dashboard.html"' in header
    assert 'href="cu-member-desk.html"' in header
    assert "Main dashboard" in header
    assert "Member desk" in header
    # real anchors, and the page already carries a visible focus ring for them
    assert "a):focus-visible" in document or "a:focus-visible" in document


def test_industry_html_member_names_carry_the_member_desk_address():
    """A member is addressed by display name through ?m=; every member cell on this page mints
    that address, and a retained-universe row whose name is really a bioguide ID stays text."""
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    assert 'const DESK_FILE="cu-member-desk.html";' in document
    assert '${DESK_FILE}?m=${encodeURIComponent(name)}' in document
    # attention, champions board, organization drill-down and forecast ranking
    assert document.count("memberLink(row.") == 4
    assert 'class="member left">${esc(row.n)}' not in document
    assert 'class="member left">${esc(row.name)}' not in document
    assert "if(bioguide!=null&&String(name)===String(bioguide))return text;" in document


def test_industry_html_contains_required_honesty_language():
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    required = (
        "Coverage 2021–2026 from complete LDA sweeps (~540,000 filings)",
        "Attention means the organization lobbied a bill this member sponsored or "
        "cosponsored. It is NOT evidence of contact, agreement, or a relationship.",
        "Only ~23% of lobbying activities cite a bill number, so member-level "
        "attention rests on that 23% and it is not a random sample "
        "(better-resourced filers cite bills more).",
        "Champion scores are DESCRIPTIVE residuals, not a hypothesis test, with no p-value.",
        "Attention measures who an org WORKS, not who agrees with it — organizations "
        "lobby adversaries as hard as allies.",
        "Sector spend LEVELS depend on roster choice; the SHAPES are the defensible claim.",
        "In-house figures are self-reported and rounded to a $10k threshold, so the "
        "total mixes a contract price with a self-estimated budget and should be read "
        "as approximate.",
        "The forecast is descriptive, not causal, and its headline is judged against "
        "the BEST baseline.",
    )
    for statement in required:
        assert statement in document


def test_industry_html_is_byte_deterministic():
    with tempfile.TemporaryDirectory() as directory:
        first_document, first_bytes, data_root = _build_industry_fixture(
            directory, "first.html"
        )
        second_path = os.path.join(directory, "second.html")
        second_document = MLN.build(
            data_root,
            second_path,
            bill_directions_path=os.path.join(data_root, "bill_directions.csv"),
            bills_audit_path=os.path.join(data_root, "bills_audit.csv"),
            **_identity_paths(data_root),
        )
        with open(second_path, "rb") as handle:
            second_bytes = handle.read()
    assert first_document == second_document
    assert first_bytes == second_bytes


def _industry_page_data(document):
    opening = '<script id=page-data type=application/json>'
    payload = document.split(opening, 1)[1].split("</script>", 1)[0]
    return json.loads(payload)


def test_bill_view_unmarked_bill_renders_em_dash_not_zero_or_blank():
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    data = _industry_page_data(document)
    bill = next(item for item in data["bills"] if item["key"] == "119:s:9999")
    assert bill["marking"] is None
    assert 'class=unmarked aria-label="Unmarked">${EM_DASH}</span>' in document
    assert 'const EM_DASH="—"' in document
    assert "Neutral means adjudicated neutral; an em dash means no adjudication row." in document


def test_bill_view_multiple_organizations_are_all_in_expansion_payload():
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    data = _industry_page_data(document)
    bill = next(item for item in data["bills"] if item["key"] == "117:hr:1215")
    assert [item["name"] for item in bill["organizations"]] == [
        "Second Fixture Bank",
        "Fixture Credit Union",
    ]
    assert len(bill["organizations"]) == 2
    assert "Complete organization list" in document
    assert "bill.organizations.map" in document


def test_bill_view_marking_overlay_joins_on_canonical_parts_not_display_string():
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    data = _industry_page_data(document)
    bill = next(item for item in data["bills"] if item["key"] == "118:hr:1181")
    assert bill["bill"] == "H.R.1181"
    assert bill["marking"]["direction"] == 1
    assert bill["marking"]["state"] == "support"
    assert bill["marking"]["category"] == "Payments:Support"


def test_bill_view_has_zero_remote_asset_references():
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    assert "http://" not in document
    assert "https://" not in document
    assert "@import" not in document
    assert "<link" not in document


def test_bill_view_preserves_every_required_honesty_string():
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    required = (
        MLN.ATTENTION_NOTE,
        MLN.CITATION_NOTE,
        MLN.CHAMPION_NOTE,
        MLN.WORKS_NOTE,
        MLN.SPEND_NOTE,
        MLN.FORECAST_NOTE,
        "2026 is a PARTIAL YEAR through Q2.",
        "It is not evidence that the organization supported or opposed it.",
    )
    for statement in required:
        assert statement in document


def test_bill_view_manifest_count_and_complete_link_receipt_are_exact():
    with tempfile.TemporaryDirectory() as directory:
        document, _output, data_root = _build_industry_fixture(directory)
        with open(
            os.path.join(data_root, "our_bill_lobby_index_manifest.json"),
            "r",
            encoding="utf-8",
        ) as handle:
            manifest = json.load(handle)
    data = _industry_page_data(document)
    receipt = data["receipts"]["bills"]
    assert receipt["bills"] == manifest["repository_join"]["lobbied_distinct_bills"]
    assert receipt["links"] == sum(len(item["organizations"]) for item in data["bills"])
    assert receipt["truncated_links"] == 0
    assert f"all {receipt['links']:,} distinct bill–organization links" in document
    assert "0 links truncated" in document


def test_bill_view_is_byte_deterministic():
    with tempfile.TemporaryDirectory() as directory:
        first_document, first_bytes, data_root = _build_industry_fixture(
            directory, "bill-first.html"
        )
        second_path = os.path.join(directory, "bill-second.html")
        second_document = MLN.build(
            data_root,
            second_path,
            bill_directions_path=os.path.join(data_root, "bill_directions.csv"),
            bills_audit_path=os.path.join(data_root, "bills_audit.csv"),
            **_identity_paths(data_root),
        )
        with open(second_path, "rb") as handle:
            second_bytes = handle.read()
    assert first_document == second_document
    assert first_bytes == second_bytes


def test_bill_view_direction_zero_is_neutral_and_counted_as_marked():
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    data = _industry_page_data(document)
    bill = next(item for item in data["bills"] if item["key"] == "117:hr:1215")
    receipt = data["receipts"]["bills"]
    assert bill["bill"] == "H.R.1215"
    assert bill["marking"] == {
        "category": "CFPB:Neutral",
        "direction": 0,
        "state": "neutral",
    }
    assert receipt["marked"] == 2
    assert receipt["directional"] == 1
    assert receipt["neutral"] == 1
    assert "2 of 3 bills carry a CU marking (1 directional, 1 neutral)" in document
    assert 'neutral:["◆","Neutral"]' in document
    assert "Neutral · category" in document
    assert "CFPB:Neutral" in document


def _fixture_resolver(data_root):
    return HMN.MemberNameResolver.from_paths(
        congestion_path=os.path.join(data_root, "congestion.json"),
        legislators_path=os.path.join(data_root, "legislators.csv"),
        voteview_path=os.path.join(data_root, "HSall_members.csv"),
    )


def _identity_only_fixture(directory):
    data_root = os.path.join(directory, "derived")
    os.makedirs(data_root, exist_ok=True)
    _identity_fixture(data_root)
    return data_root


def test_member_name_bioname_is_rendered_forename_first():
    """Voteview writes LAST, First; a reader needs First Last, correctly cased."""
    cases = {
        "McHENRY, Patrick T.": "Patrick T. McHenry",
        "MCCARTHY, Kevin": "Kevin McCarthy",
        "CHERFILUS-MCCORMICK, Sheila": "Sheila Cherfilus-McCormick",
        "D'ESPOSITO, Anthony": "Anthony D'Esposito",
        "MANCHIN, Joe, III": "Joe Manchin III",
        "PASCRELL, William J., Jr.": "William J. Pascrell Jr.",
        "DeFAZIO, Peter Anthony": "Peter Anthony DeFazio",
        "LaMALFA, Doug": "Doug LaMalfa",
        "JACKSON LEE, Sheila": "Sheila Jackson Lee",
        "MACE, Nancy": "Nancy Mace",
    }
    for bioname, expected in cases.items():
        assert HMN.display_name_from_bioname(bioname) == expected, (
            bioname,
            HMN.display_name_from_bioname(bioname),
        )


def test_member_name_resolver_names_departed_member_and_marks_them_former():
    """M001156 is Patrick T. McHenry, off both current rosters since the 118th.

    He must arrive as a readable name AND be visibly marked as no longer
    serving, because a reader scanning a champions board cannot otherwise tell
    that a listed member has left office.
    """
    with tempfile.TemporaryDirectory() as directory:
        resolver = _fixture_resolver(_identity_only_fixture(directory))
        record = resolver.resolve(FIXTURE_FORMER_MEMBER)
    assert record["name"] == "Patrick T. McHenry", record
    assert record["source"] == HMN.SOURCE_VOTEVIEW
    assert record["status"] == HMN.STATUS_FORMER
    assert record["is_former"] is True
    assert record["resolved"] is True
    assert record["last_congress"] == 118
    assert HMN.FORMER_MARKER in record["display"]
    assert "Patrick T. McHenry" in record["display"]
    assert FIXTURE_FORMER_MEMBER not in record["display"]


def test_member_name_resolver_sitting_member_carries_no_former_flag():
    """A member still in office resolves from the current roster and is unmarked."""
    with tempfile.TemporaryDirectory() as directory:
        resolver = _fixture_resolver(_identity_only_fixture(directory))
        sitting = resolver.resolve(FIXTURE_SITTING_MEMBER)
        # legislators.csv really does carry roster rows with a blank full_name;
        # the ladder answers those from congestion.json, not with a bioguide.
        blank = resolver.resolve(FIXTURE_BLANK_NAME_MEMBER)
    assert sitting["name"] == "Fixture Member"
    assert sitting["display"] == "Fixture Member"
    assert sitting["source"] == HMN.SOURCE_CONGESTION
    assert sitting["status"] == HMN.STATUS_SERVING
    assert sitting["is_former"] is False
    assert HMN.FORMER_MARKER not in sitting["display"]
    assert HMN.UNRESOLVED_MARKER not in sitting["display"]
    assert blank["name"] == "Blank Roster Member"
    assert blank["is_former"] is False
    assert blank["display"] == "Blank Roster Member"


def test_member_name_resolver_unknown_bioguide_degrades_visibly():
    """No roster and no Voteview row: say so, never print a bare identifier."""
    with tempfile.TemporaryDirectory() as directory:
        resolver = _fixture_resolver(_identity_only_fixture(directory))
        record = resolver.resolve(FIXTURE_UNKNOWN_MEMBER)
        receipt = resolver.receipt()
    assert record["resolved"] is False
    assert record["status"] == HMN.STATUS_UNRESOLVED
    assert record["source"] == HMN.SOURCE_NONE
    assert record["is_former"] is False
    assert record["display"] != FIXTURE_UNKNOWN_MEMBER
    assert HMN.UNRESOLVED_MARKER in record["display"]
    assert FIXTURE_UNKNOWN_MEMBER in record["display"]
    assert receipt["unresolved"] == 1
    assert receipt["unresolved_bioguides"] == [FIXTURE_UNKNOWN_MEMBER]
    try:
        resolver.resolve("   ")
    except HMN.IdentityError:
        pass
    else:
        raise AssertionError("a blank bioguide was silently resolved")


def test_industry_html_departed_member_is_named_not_rendered_as_a_bioguide():
    """The regression itself: M001156 reached the page as its own display name."""
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    data = _industry_page_data(document)
    members = {
        row["id"]: row for item in data["industries"] for row in item["members"]
    }
    former = members[FIXTURE_FORMER_MEMBER]
    assert former["name"] == "Patrick T. McHenry"
    assert former["flag"] == "former"
    assert members[FIXTURE_SITTING_MEMBER]["name"] == "Fixture Member"
    assert members[FIXTURE_SITTING_MEMBER]["flag"] is None
    forecast = {
        row["member"]: row
        for bill in data["forecast"]["bills"]
        for row in bill["rows"]
    }
    assert forecast[FIXTURE_FORMER_MEMBER]["name"] == "Patrick T. McHenry"
    assert forecast[FIXTURE_FORMER_MEMBER]["flag"] == "former"
    # the exact leak shape: a member whose printed name IS the bioguide
    assert '"name":"' + FIXTURE_FORMER_MEMBER + '"' not in document
    assert "Patrick T. McHenry" in document
    receipt = data["receipts"]["member_names"]
    assert receipt["former_members"] == 1
    assert receipt["by_source"][HMN.SOURCE_VOTEVIEW] == 1
    assert MLN.FORMER_MEMBER_NOTE in document


def test_industry_html_unresolvable_bioguide_is_marked_never_silent():
    """A bioguide nothing can name is badged, and never mints a dead desk link."""
    with tempfile.TemporaryDirectory() as directory:
        document, _output, _root = _build_industry_fixture(directory)
    data = _industry_page_data(document)
    members = {
        row["id"]: row for item in data["industries"] for row in item["members"]
    }
    unknown = members[FIXTURE_UNKNOWN_MEMBER]
    assert unknown["name"] == FIXTURE_UNKNOWN_MEMBER
    assert unknown["flag"] == "unresolved"
    receipt = data["receipts"]["member_names"]
    assert receipt["unresolved"] == 1
    assert receipt["unresolved_bioguides"] == [FIXTURE_UNKNOWN_MEMBER]
    # the badge is rendered, and a flagged member never becomes a desk anchor
    assert 'MEMBER_FLAG_LABELS={former:"Former",unresolved:"Name unresolved"}' in document
    assert "if(flag)return text+memberFlag(flag);" in document


def test_lobby_champions_blank_roster_name_never_emits_a_bare_bioguide():
    """A blank legislators.csv full_name is the champions-board leak; fill it."""
    with tempfile.TemporaryDirectory() as directory:
        resolver = _fixture_resolver(_identity_only_fixture(directory))
        roster = {
            FIXTURE_SITTING_MEMBER: {
                "member_name": "Fixture Member",
                "party": "I",
                "chamber": "rep",
            },
            FIXTURE_BLANK_NAME_MEMBER: {
                "member_name": None,
                "party": "D",
                "chamber": "rep",
            },
            FIXTURE_UNKNOWN_MEMBER: {
                "member_name": None,
                "party": "R",
                "chamber": "sen",
            },
        }
        filled, receipt = LC.resolve_roster_names(roster, resolver)
    assert filled[FIXTURE_SITTING_MEMBER]["member_name"] == "Fixture Member"
    assert filled[FIXTURE_BLANK_NAME_MEMBER]["member_name"] == "Blank Roster Member"
    assert HMN.UNRESOLVED_MARKER in filled[FIXTURE_UNKNOWN_MEMBER]["member_name"]
    assert receipt["roster_rows_with_blank_full_name"] == 2
    for bioguide in roster:
        assert filled[bioguide]["member_name"] != bioguide


def test_attention_vs_stance_member_display_never_returns_a_bare_bioguide():
    """Every stance cell names a member or says plainly that it cannot."""
    named = {
        "bioguide_id": FIXTURE_SITTING_MEMBER,
        "congestion_member_name": "Fixture Member",
        "member_name": "Fixture Member",
    }
    assert AVS._member_display(named) == "Fixture Member"
    former = {
        "bioguide_id": FIXTURE_FORMER_MEMBER,
        "congestion_member_name": None,
        "member_name": "",
        "historical_member_display": "Patrick T. McHenry (" + HMN.FORMER_MARKER + ")",
    }
    assert AVS._member_display(former) == (
        "Patrick T. McHenry (" + HMN.FORMER_MARKER + ")"
    )
    unknown = {
        "bioguide_id": FIXTURE_UNKNOWN_MEMBER,
        "congestion_member_name": None,
        "member_name": None,
    }
    display = AVS._member_display(unknown)
    assert display != FIXTURE_UNKNOWN_MEMBER
    assert HMN.UNRESOLVED_MARKER in display
    attached = AVS.attach_member_records(
        [{"lob_id": "org-1", "bioguide_id": FIXTURE_FORMER_MEMBER}], {}, {}, {}
    )
    assert attached[0]["historical_member_display"] is None
    assert HMN.UNRESOLVED_MARKER in AVS._member_display(attached[0])


def _bill_index_test_scope():
    return {
        "orgs": {
            "org-a": {
                "canonical_name": "Alpha Bank",
                "sides": ("bank",),
            },
            "org-b": {
                "canonical_name": "Beta Credit Union",
                "sides": ("credit_union",),
            },
            "org-c": {
                "canonical_name": "Gamma Finance",
                "sides": ("financial_other",),
            },
            "org-d": {
                "canonical_name": "Delta Bank",
                "sides": ("bank",),
            },
        }
    }


def _bill_index_test_observation(sources, strict, period="q1"):
    return {
        "n_filings": 1,
        "n_activities": 1,
        "filing_periods": {period},
        "sources": set(sources),
        "strict": strict,
    }


def test_bill_index_keeps_one_row_per_bill_and_organization():
    bill = ("HR", 1181, 118)
    rows = BN.bill_index_rows(
        2023,
        {
            ("org-a", bill): _bill_index_test_observation(
                {"formal"}, True
            ),
            ("org-b", bill): _bill_index_test_observation(
                {"formal"}, True
            ),
        },
        _bill_index_test_scope(),
    )
    assert len(rows) == 2
    assert {row["lob_id"] for row in rows} == {"org-a", "org-b"}
    assert {row["bill_key"] for row in rows} == {"118:hr:1181"}


def test_bill_index_canonical_keys_match_repository_convention():
    expected = {
        ("HR", 1181, 118): "118:hr:1181",
        ("HJRES", 66, 118): "118:hjres:66",
        ("HAMDT", 247, 116): "116:hamdt:247",
        ("SAMDT", 1049, 116): "116:samdt:1049",
    }
    for bill, canonical in expected.items():
        assert BN.canonical_bill_key(bill) == canonical
        assert BN.bill_key_from_canonical(canonical) == bill
    assert BN.repository_display_bill_key("H.Amdt.247", "116") == (
        "116:hamdt:247"
    )
    assert BN.repository_display_bill_key("S.Amdt.1049", 116) == (
        "116:samdt:1049"
    )


def test_bill_index_preserves_strict_and_generous_channel_per_row():
    bills = {
        "org-a": (("HR", 1, 118), {"formal"}, True),
        "org-b": (("HR", 2, 118), {"title"}, True),
        "org-c": (("HR", 3, 118), {"title"}, False),
        "org-d": (("HR", 4, 118), {"formal", "title"}, True),
    }
    rows = BN.bill_index_rows(
        2023,
        {
            (lob_id, bill): _bill_index_test_observation(sources, strict)
            for lob_id, (bill, sources, strict) in bills.items()
        },
        _bill_index_test_scope(),
    )
    assert {row["lob_id"]: row["channel"] for row in rows} == {
        "org-a": "formal_strict",
        "org-b": "title_strict",
        "org-c": "title_generous_only",
        "org-d": "both_strict",
    }


def test_bill_repository_join_receipts_unjoinable_keys_on_both_sides():
    index_rows = [
        {
            "congress": 118,
            "bill_type": "hr",
            "bill_number": number,
            "bill_key": f"118:hr:{number}",
            "lob_id": "org-a",
            "n_filings": 1,
            "n_activities": 1,
            "channel": "formal_strict",
        }
        for number in (1, 2)
    ]
    membership_rows = [
        {
            "canonical_key": f"118:hr:{number}",
            "category_id": "category",
            "integration_state": "included_scoring_ready",
            "measure_weight": 1.0,
        }
        for number in (1, 3)
    ]
    rows, receipt = BN.build_bill_repository_join(
        {2023: index_rows}, membership_rows, [], []
    )
    assert receipt["repository_bills_with_lobbying"] == 1
    assert receipt["repository_bills_without_lobbying"] == 1
    assert receipt["lobbied_bills_absent_from_repository"] == 1
    assert receipt["unjoinable_keys"]["lobbying_not_in_repository"] == {
        "count": 1,
        "samples": ["118:hr:2"],
    }
    assert receipt["unjoinable_keys"]["repository_without_lobbying"] == {
        "count": 1,
        "samples": ["118:hr:3"],
    }
    by_status = {row["join_status"]: row for row in rows}
    assert by_status["lobbying_only"]["canonical_key"] == ""
    assert by_status["repository_only"]["bill_key"] == ""


def test_bill_index_and_repository_join_are_deterministic():
    args = BN._parse_args(
        ["--full-scope", "--emit-bill-index", "--years", "2023,2024"]
    )
    assert args.full_scope is True
    assert args.emit_bill_index is True
    assert BN.parse_years(args.years) == (2023, 2024)
    scope = _bill_index_test_scope()
    bill_a = ("HR", 10, 118)
    bill_b = ("S", 20, 118)
    observations = {
        ("org-b", bill_b): _bill_index_test_observation(
            {"title"}, False, "q4"
        ),
        ("org-a", bill_a): _bill_index_test_observation(
            {"formal"}, True, "q1"
        ),
    }
    first_index = BN.bill_index_rows(2023, observations, scope)
    second_index = BN.bill_index_rows(
        2023, dict(reversed(list(observations.items()))), scope
    )
    assert first_index == second_index
    membership = [
        {
            "canonical_key": "118:s:20",
            "category_id": "z",
            "integration_state": "included_scoring_ready",
            "measure_weight": 0.5,
        },
        {
            "canonical_key": "118:hr:10",
            "category_id": "a",
            "integration_state": "included_scoring_ready",
            "measure_weight": 1.0,
        },
    ]
    first_join = BN.build_bill_repository_join(
        {2023: first_index}, membership, [], []
    )
    second_join = BN.build_bill_repository_join(
        {2023: second_index}, list(reversed(membership)), [], []
    )
    assert first_join == second_join


TESTS = (
    test_bill_regex_formal_variants,
    test_bill_regex_boundaries_multi_and_unparsed,
    test_dotless_bare_s_sba_lookbehind_wins_over_context,
    test_dotless_bare_s_us_census_lookbehind_wins_over_context,
    test_dotless_bare_s_bank_of_america_5300_and_1160,
    test_dotless_and_dotted_s_in_same_activity_both_resolve,
    test_dotless_bare_s_without_formal_context_is_rejected,
    test_dotless_bare_s_over_range_and_absent_is_rejected,
    test_dotless_bare_s_recovery_and_rejection_receipts,
    test_bill_number_runs_into_title_six_verbatim_citations,
    test_run_into_title_keeps_thousands_separator_protection,
    test_run_into_title_keeps_six_digit_boundary_protection,
    test_run_into_title_keeps_existing_hyphen_behavior,
    test_runs_into_title_recovery_receipt_bucket,
    test_sponsor_map_synthetic_billstatus,
    test_multi_congress_same_number_resolution,
    test_title_normalization_guard_ambiguity_boundary_and_longest,
    test_stale_citation_original_congress_and_strict_generous,
    test_multi_suffix_stale_citations_forward_binding,
    test_distinct_bill_dyad_counting,
    test_title_union_with_formal_is_distinct,
    test_per_activity_scope_congress_and_contradiction,
    test_sponsorless_intersection_receipt,
    test_cross_comparison_arithmetic,
    test_collector_manifest_idempotency,
    test_collector_schema_identity_and_resume_validation,
    test_collector_timeout_redirect_and_transient_retries,
    test_incremental_manifest_writer,
    test_year_partitioned_resume_paths,
    test_sweep_page_validation,
    test_worklist_filing_year_validation,
    test_strict_uuid_and_pinned_lob_scope,
    test_worklist_boolean_normalization,
    test_bridge3_member_blocked_two_cycle_joint_move,
    test_bridge3_fractional_ranks_and_singleton_party_cell,
    test_bridge3_committee_snapshot_parser,
    test_bridge3_sweep_ingestion_duplicate_and_wrong_year,
    test_bridge3_client_attribution_and_near_miss_receipt,
    test_bridge3_stable_client_id_harvest_and_collision,
    test_bridge3_all_year_id_harvest_matches_unseen_sweep_name,
    test_bridge3_id_harvest_plausibility_guard_rejects_cross_attribution,
    test_legacy_2021_build_does_not_consult_identity_harvest_loader,
    test_bridge3_zero_match_org_has_per_year_coverage_gap_receipt,
    test_bridge3_first_word_title_index_matches_naive,
    test_bridge3_xhat_battery_construction_sanity,
    test_round4b_y_distinct_directional_bill_construction,
    test_round4b_congestion_x_stratum_field_mapping,
    test_round4b_entry_and_void_exact_boundaries,
    test_round4b_battery_never_loads_real_y,
    test_quarterly_period_vocabulary_and_unknown,
    test_quarterly_aggregation_distinctness,
    test_position_calibration_join_and_three_class_collapse,
    test_position_dataset_accepts_their_five_label_vocabulary,
    test_position_dataset_unknown_label_names_row,
    test_position_three_class_collapse_both_directions,
    test_position_agreement_primary_and_restricted_secondary_n,
    test_position_prompt_exactness,
    test_position_jsonl_and_flat_csv_round_trip,
    test_position_fewshot_prompt_pinned_order_and_label_mapping,
    test_position_fewshot_selection_excludes_calibration_pairs,
    test_position_fewshot_shortfall_receipt_and_cache_reuse,
    test_position_reply_parsing_and_unparseable_receipt,
    test_position_content_hash_resume_behavior,
    test_position_title_only_official_allows_empty_short,
    test_position_title_display_fallback_receipted,
    test_position_title_zero_items_raises,
    test_position_title_both_preserves_short_and_prefers_introduced,
    test_position_absent_billstatus_key_skipped_with_samples,
    test_position_present_billstatus_key_without_titles_still_raises,
    test_position_present_billstatus_key_with_titles_unchanged,
    test_association_name_normalizer_fixed_cases,
    test_association_set_directional_threshold_rule,
    test_association_crosswalk_is_exact_only_and_receipts_near_name,
    test_association_global_id_matches_despite_name_mismatch,
    test_association_id_and_name_channels_have_union_semantics,
    test_association_client_scoped_id_never_attributes_identity,
    test_association_main_fails_loud_without_id_crosswalk,
    test_association_work_item_determinism_and_schema_mirror,
    test_association_id_guard_rejects_ufcw_for_sound_banking,
    test_association_id_guard_accepts_nafcu_rename,
    test_association_id_guard_accepts_nonempty_subset,
    test_association_id_guard_rejects_shared_stopwords_only,
    test_association_id_rejection_receipt_carries_both_token_sets,
    test_lobby_champions_structural_controls_bite,
    test_lobby_champions_zero_fills_roster_member,
    test_lobby_champions_under_min_links_receipted,
    test_lobby_champions_rank_deficiency_receipted,
    test_lobby_champions_csv_determinism,
    test_lobby_champions_sector_mean_is_genuine_leave_one_out,
    test_lobby_champions_single_org_sector_fields_are_null_not_zero,
    test_attention_vs_stance_bioguide_join_survives_display_name_difference,
    test_attention_vs_stance_known_member_enters_worked_adversaries_cell,
    test_attention_vs_stance_json_and_csv_are_deterministic,
    test_lobby_forecast_no_leakage_by_construction,
    test_lobby_forecast_persistence_reproduces_82_percent_carryover,
    test_lobby_forecast_churn_subset_excludes_persistent_dyad,
    test_lobby_forecast_temporal_split_never_trains_on_t_plus_1,
    test_lobby_forecast_rank_deficiency_is_reported,
    test_lobby_forecast_determinism,
    test_lobby_forecast_coverage_guard_rejects_mixed_basis,
    test_lobby_forecast_schiff_transition_does_not_break_seniority,
    test_lobby_forecast_mid_congress_move_prefers_senate_with_receipt,
    test_lobby_forecast_icpsr_difference_prefers_other_congress_match,
    test_lobby_forecast_same_chamber_conflicting_state_still_raises,
    test_lobby_forecast_committee_congress_keys_normalize_to_int,
    test_lobby_forecast_committee_error_names_only_genuine_missing,
    test_lobby_forecast_allow_missing_committee_drops_split_feature,
    test_lobby_forecast_missing_committee_without_flag_still_raises,
    test_lobby_forecast_churn_headline_names_winning_popularity_baseline,
    test_lobby_forecast_persistence_churn_is_annotated_structurally_zero,
    test_lobby_forecast_overall_verdict_counts_losses_and_leads_with_failure,
    test_cosponsor_forecast_no_leakage_and_sponsor_excluded,
    test_cosponsor_forecast_prior_features_never_read_target_congress,
    test_cosponsor_forecast_three_baselines_known_structure,
    test_cosponsor_forecast_headline_names_best_baseline_and_loss,
    test_cosponsor_forecast_rank_deficiency_detected_not_silent,
    test_cosponsor_forecast_output_determinism,
    test_cosponsor_forecast_voteview_universe_includes_cheney_fixture,
    test_cosponsor_forecast_streamed_normal_equations_match_direct_solve,
    test_cosponsor_forecast_streamed_auc_matches_direct_fixture,
    test_cosponsor_forecast_gram_rank_deficiency_detected,
    test_cosponsor_forecast_campbell_switch_carries_forward_identity,
    test_cosponsor_forecast_final_congress_switch_uses_higher_icpsr,
    test_cosponsor_forecast_out_of_scope_voteview_conflict_is_not_validated,
    test_cosponsor_forecast_in_scope_state_conflict_still_raises,
    test_cosponsor_forecast_same_chamber_only_excludes_and_drops_constant,
    test_cosponsor_forecast_candidate_configurations_have_correct_base_rates,
    test_cosponsor_forecast_penalized_standard_errors_finite_positive,
    test_cosponsor_forecast_policy_area_coefficients_carry_bill_counts,
    test_sector_spend_amendment_supersession_latest_dt_and_receipt,
    test_sector_spend_registration_types_excluded_and_receipted,
    test_sector_spend_components_support_exact_total,
    test_sector_spend_cuna_nafcu_dba_variants_one_family,
    test_sector_spend_individual_excluded_and_reported_separately,
    test_sector_spend_2026_is_partial_year,
    test_sector_spend_output_determinism,
    test_industry_html_total_is_exact_component_sum_with_precision_note,
    test_industry_html_null_sector_score_renders_em_dash,
    test_industry_html_marks_2026_partial_year,
    test_industry_html_is_self_contained,
    test_industry_html_is_not_a_one_way_trap,
    test_industry_html_member_names_carry_the_member_desk_address,
    test_industry_html_contains_required_honesty_language,
    test_industry_html_is_byte_deterministic,
    test_bill_view_unmarked_bill_renders_em_dash_not_zero_or_blank,
    test_bill_view_multiple_organizations_are_all_in_expansion_payload,
    test_bill_view_marking_overlay_joins_on_canonical_parts_not_display_string,
    test_bill_view_has_zero_remote_asset_references,
    test_bill_view_preserves_every_required_honesty_string,
    test_bill_view_manifest_count_and_complete_link_receipt_are_exact,
    test_bill_view_is_byte_deterministic,
    test_bill_view_direction_zero_is_neutral_and_counted_as_marked,
    test_fullscope_org_set_is_four_source_union_without_duplicates,
    test_fullscope_corpus_basis_is_shared_and_not_legacy,
    test_fullscope_mode_never_selects_legacy_output_paths,
    test_fullscope_zero_match_is_a_per_year_coverage_gap,
    test_fullscope_quarterly_union_is_annual_with_repeat_excess,
    test_fullscope_name_pattern_adds_missing_state_league_to_roster,
    test_bill_index_keeps_one_row_per_bill_and_organization,
    test_bill_index_canonical_keys_match_repository_convention,
    test_bill_index_preserves_strict_and_generous_channel_per_row,
    test_bill_repository_join_receipts_unjoinable_keys_on_both_sides,
    test_bill_index_and_repository_join_are_deterministic,
    test_member_name_bioname_is_rendered_forename_first,
    test_member_name_resolver_names_departed_member_and_marks_them_former,
    test_member_name_resolver_sitting_member_carries_no_former_flag,
    test_member_name_resolver_unknown_bioguide_degrades_visibly,
    test_industry_html_departed_member_is_named_not_rendered_as_a_bioguide,
    test_industry_html_unresolvable_bioguide_is_marked_never_silent,
    test_lobby_champions_blank_roster_name_never_emits_a_bare_bioguide,
    test_attention_vs_stance_member_display_never_returns_a_bare_bioguide,
)


def main():
    for test in TESTS:
        test()
        print(f"  OK   {test.__name__}")
    print(f"lda rebuild tests: {len(TESTS)} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
