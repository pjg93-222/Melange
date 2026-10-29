from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "fec"))

from legislation import govinfo_discovery_fallback as FALLBACK
from legislation import refresh_legislation_discovery as REFRESH
from legislation import stage_billstatus_bulk_enrichment as BILLSTATUS


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_ndjson(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def fixture_status(
    number: int, *, text_url: str | None = None, amendments: str = ""
) -> bytes:
    versions = (
        f"<textVersions><item><date>2026-08-30</date><type>Introduced in House</type>"
        f"<formats><item><url>{text_url}</url></item></formats></item></textVersions>"
        if text_url
        else ""
    )
    return f"""<?xml version="1.0" encoding="utf-8"?>
<billStatus>
  <version>3.0.0</version>
  <bill>
    <congress>119</congress><type>HR</type><number>{number}</number>
    <updateDate>2026-08-30T12:00:00Z</updateDate>
    <titles><item><title>Safe Local Finance Act</title><titleType>Official Title as Introduced</titleType></item></titles>
    <sponsors><item><bioguideId>T000001</bioguideId><fullName>Test, Terry [Rep.-I-TS-1]</fullName></item></sponsors>
    <cosponsors><item><bioguideId>C000001</bioguideId><fullName>Cosponsor, Casey</fullName><isOriginalCosponsor>true</isOriginalCosponsor></item></cosponsors>
    <actions><item><actionDate>2026-08-30</actionDate><text>Introduced in House</text></item></actions>
    {versions}
    {amendments}
  </bill>
</billStatus>
""".encode()


def setup_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path, dict[str, bytes]]:
    registry_path = tmp_path / "registry.json"
    registry = {
        "collection_contract": {
            "congresses": [119],
            "legislation_types": ["hr", "hamdt"],
            "required_window_start": "2020-07-25",
            "required_window_end": "2026-09-04",
        },
        "categories": [
            {
                "id": "community_finance",
                "label": "Community Finance",
                "scoring_category": True,
                "query_terms": [
                    {
                        "kind": "outline_identifier",
                        "query": "community development finance",
                    }
                ],
            }
        ],
        "coverage_probes": [
            {
                "id": "credit_union_recall",
                "label": "Credit Union Recall",
                "scoring_category": False,
                "record_kind": "coverage_probe",
                "query_terms": [
                    {"kind": "coverage_probe", "query": '"credit union"'}
                ],
            }
        ],
    }
    write_json(registry_path, registry)
    registry_sha = FALLBACK.sha256_bytes(registry_path.read_bytes())

    baseline = tmp_path / "baseline"
    baseline_record = {
        "record_kind": "bill",
        "congress": 119,
        "type": "hr",
        "number": 1,
        "canonical_key": "119:hr:1",
        "title": "Never mutate this baseline row",
        "matched_scoring_categories": [],
        "matched_monitor_categories": [],
        "matched_coverage_probes": [],
    }
    baseline_membership = {
        "query_id": "old_query",
        "canonical_key": "119:hr:1",
        "result_url": "https://www.congress.gov/bill/119th-congress/house-bill/1",
    }
    write_ndjson(baseline / "congress_advanced_records.ndjson", [baseline_record])
    write_ndjson(
        baseline / "congress_advanced_memberships.ndjson", [baseline_membership]
    )
    write_ndjson(baseline / "coverage_gap_ledger.ndjson", [])
    write_ndjson(baseline / "exclusion_ledger.ndjson", [])
    write_json(baseline / "scope_and_exclusion_contract.json", {"baseline": True})
    write_json(
        baseline / "manifest.json",
        {
            "status": "complete",
            "completed_at": "2026-07-26T19:04:16Z",
            "registry_sha256": registry_sha,
            "union": {
                "records_file": "congress_advanced_records.ndjson",
                "unique_record_count": 1,
                "records_sha256": FALLBACK.stable_hash([baseline_record]),
                "memberships_file": "congress_advanced_memberships.ndjson",
                "membership_count": 1,
                "memberships_sha256": FALLBACK.stable_hash([baseline_membership]),
            },
        },
    )

    out = tmp_path / "out"
    browser_failure = tmp_path / "browser_failure.json"
    write_json(
        browser_failure,
        {
            "status": "failed",
            "automatic_verification_timeout": {
                "collection_stopped_without_result_acceptance": True
            },
            "error": {"code": "CONGRESS_AUTOMATIC_VERIFICATION_TIMEOUT"},
        },
    )
    sitemap_url = BILLSTATUS.expected_sitemap_url(119, "hr")
    old_url = BILLSTATUS.expected_record_url(119, "hr", 1)
    new_url = BILLSTATUS.expected_record_url(119, "hr", 99)
    text_url = (
        "https://www.govinfo.gov/content/pkg/BILLS-119hr99ih/"
        "uslm/BILLS-119hr99ih.xml"
    )
    sitemap = f"""<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>{old_url}</loc><lastmod>2026-08-30</lastmod></url>
  <url><loc>{new_url}</loc><lastmod>2026-08-30</lastmod></url>
</urlset>
""".encode()
    bill_text = b"""<?xml version="1.0"?>
<!DOCTYPE bill PUBLIC "-//US Congress//DTDs/bill.dtd//EN" "bill.dtd">
<bill><legis-body>This community development finance proposal serves every credit union.</legis-body></bill>
"""
    amendments = """
    <amendments>
      <amendment>
        <number>700</number><congress>119</congress><type>HAMDT</type>
        <purpose>To expand community development finance options.</purpose>
        <updateDate>2026-08-31T12:00:00Z</updateDate>
        <sponsors><item><bioguideId>A000001</bioguideId><fullName>Amender, Alex</fullName></item></sponsors>
        <proposedDate>2026-08-31T04:00:00Z</proposedDate>
        <amendedBill><congress>119</congress><type>HR</type><number>99</number></amendedBill>
      </amendment>
      <amendment>
        <number>701</number><congress>119</congress><type>HAMDT</type>
        <purpose>To rename a post office.</purpose>
        <updateDate>2026-08-31T12:00:00Z</updateDate>
        <amendedBill><congress>119</congress><type>HR</type><number>99</number></amendedBill>
      </amendment>
    </amendments>
    """
    return (
        registry_path,
        baseline,
        out,
        browser_failure,
        {
            sitemap_url: sitemap,
            old_url: fixture_status(1),
            new_url: fixture_status(99, text_url=text_url, amendments=amendments),
            text_url: bill_text,
        },
    )


def test_official_fallback_is_cumulative_pending_and_idempotent(tmp_path: Path) -> None:
    registry, baseline, out, failure, responses = setup_fixture(tmp_path)

    def fetch(url: str, limit: int) -> bytes:
        assert len(responses[url]) <= limit
        return responses[url]

    first = FALLBACK.run_fallback(
        registry_path=registry,
        baseline_dir=baseline,
        out_dir=out,
        browser_failure_path=failure,
        workers=2,
        fetch=fetch,
    )
    records = FALLBACK._read_ndjson(out / "congress_advanced_records.ndjson")
    memberships = FALLBACK._read_ndjson(
        out / "congress_advanced_memberships.ndjson"
    )
    assert len(records) == 3
    assert records[0]["title"] == "Never mutate this baseline row"
    bill = next(row for row in records if row["canonical_key"] == "119:hr:99")
    amendment = next(row for row in records if row["canonical_key"] == "119:hamdt:700")
    assert bill["candidate_status"] == "included_unreviewed_candidate"
    assert bill["fallback_discovery"]["scoring_eligible"] is False
    assert bill["matched_scoring_categories"] == ["community_finance"]
    assert bill["matched_coverage_probes"] == ["credit_union_recall"]
    assert amendment["matched_scoring_categories"] == ["community_finance"]
    assert "parent_bill_title" in amendment["fallback_discovery"]["matching_evidence_scope"]
    assert not any(row["canonical_key"] == "119:hamdt:701" for row in records)
    assert len(memberships) == 4
    assert all(
        row.get("scoring_eligible") is False
        for row in memberships
        if row["canonical_key"] == "119:hr:99"
    )
    assert first["immutable_baseline"]["preexisting_records_preserved_losslessly"]
    receipt = json.loads(
        (out / "govinfo_fallback_receipt.json").read_text()
    )
    assert "hamdt" in receipt["types_without_top_level_sitemaps"]
    assert receipt["scan"]["new_matching_pending_amendment_candidates"] == 1
    # A fallback is never PASS (memory rule 2026-10-27): DEGRADED, naming GovInfo.
    assert receipt["status"] == "DEGRADED" and receipt["degraded_source"].startswith("GovInfo")
    assert first["discovery_status"] == "DEGRADED"
    assert first["primary_instrument"] != REFRESH.CONGRESS_SOURCE

    records_before = (out / "congress_advanced_records.ndjson").read_bytes()
    memberships_before = (out / "congress_advanced_memberships.ndjson").read_bytes()
    second = FALLBACK.run_fallback(
        registry_path=registry,
        baseline_dir=baseline,
        out_dir=out,
        browser_failure_path=failure,
        workers=2,
        fetch=fetch,
    )
    assert second["union"]["unique_record_count"] == 3
    assert (out / "congress_advanced_records.ndjson").read_bytes() == records_before
    assert (
        out / "congress_advanced_memberships.ndjson"
    ).read_bytes() == memberships_before


def test_fallback_after_a_member_pages_walk_keeps_every_walk_record(tmp_path: Path) -> None:
    """D-346 interim default: the member-pages checkpoint is the cumulative base, so a later GovInfo
    fallback never drops what the Congress.gov walk found; a union that does not verify fails closed."""
    registry, baseline, out, failure, responses = setup_fixture(tmp_path)
    base_rows = FALLBACK._read_ndjson(baseline / "congress_advanced_records.ndjson")
    base_members = FALLBACK._read_ndjson(baseline / "congress_advanced_memberships.ndjson")
    walk_row = {"record_kind": "bill", "congress": 118, "type": "s", "number": 5, "canonical_key": "118:s:5",
                "title": "Found by the member-pages walk", "matched_scoring_categories": ["community_finance"],
                "matched_monitor_categories": [], "matched_coverage_probes": [],
                "discovery_sources": ["congress_gov_member_pages"]}
    walk_member = {"query_id": "community_finance", "canonical_key": "118:s:5", "section_key": "cdfi_fund"}
    records, memberships = [*base_rows, walk_row], [*base_members, walk_member]
    write_ndjson(out / "congress_advanced_records.ndjson", records)
    write_ndjson(out / "congress_advanced_memberships.ndjson", memberships)
    manifest = {"schema": FALLBACK.MEMBER_PAGES_MANIFEST_SCHEMA, "status": "complete", "slice": False,
                "primary_instrument": REFRESH.CONGRESS_SOURCE,
                "union": {"records_file": "congress_advanced_records.ndjson", "unique_record_count": 2,
                          "records_sha256": FALLBACK.stable_hash(records),
                          "memberships_file": "congress_advanced_memberships.ndjson", "membership_count": 2,
                          "memberships_sha256": FALLBACK.stable_hash(memberships)}}
    write_json(out / "manifest.json", manifest)

    def fetch(url: str, limit: int) -> bytes:
        return responses[url]

    result = FALLBACK.run_fallback(registry_path=registry, baseline_dir=baseline, out_dir=out,
                                   browser_failure_path=failure, workers=1, fetch=fetch)
    kept = {row["canonical_key"]: row for row in FALLBACK._read_ndjson(out / "congress_advanced_records.ndjson")}
    assert kept["118:s:5"] == walk_row and kept["119:hr:1"] == base_rows[0]
    assert {"119:hr:99", "119:hamdt:700"} <= set(kept) and len(kept) == 4
    assert result["discovery_status"] == "DEGRADED"

    first = json.loads((out / "manifest.json").read_text())
    assert first["cumulative_base"] == FALLBACK.LINEAGE_MEMBER_PAGES
    assert not (out / FALLBACK.PENDING_MANIFEST).exists()

    # Drift between a member-pages manifest and its files: refuse, replace nothing.
    write_json(out / "manifest.json", {**manifest, "union": {**manifest["union"], "unique_record_count": 3}})
    write_ndjson(out / "congress_advanced_records.ndjson", records)
    write_ndjson(out / "congress_advanced_memberships.ndjson", memberships)
    before = (out / "congress_advanced_records.ndjson").read_bytes()
    with pytest.raises(FALLBACK.FallbackError, match="current union receipt drift"):
        FALLBACK.run_fallback(registry_path=registry, baseline_dir=baseline, out_dir=out,
                              browser_failure_path=failure, workers=1, fetch=fetch)
    assert (out / "congress_advanced_records.ndjson").read_bytes() == before


def test_two_fallbacks_in_a_row_after_a_walk_that_refreshed_and_tagged_baseline_rows(tmp_path: Path) -> None:
    """Review blocker 2026-10-27: M -> F1 -> F2. The walk (mergeWithPrior) re-tags and refreshes the
    baseline rows it carries, so F2 must not demand byte-equality with the immutable baseline."""
    registry, baseline, out, failure, responses = setup_fixture(tmp_path)
    base_row = FALLBACK._read_ndjson(baseline / "congress_advanced_records.ndjson")[0]
    base_members = FALLBACK._read_ndjson(baseline / "congress_advanced_memberships.ndjson")
    walked = {**base_row, "title": "Refreshed by the walk",
              "discovery_sources": ["congress_gov_category_search", "congress_gov_member_pages"]}
    write_ndjson(out / "congress_advanced_records.ndjson", [walked])
    write_ndjson(out / "congress_advanced_memberships.ndjson", base_members)
    write_json(out / "manifest.json", {
        "schema": FALLBACK.MEMBER_PAGES_MANIFEST_SCHEMA, "status": "complete", "slice": False,
        "union": {"records_file": "congress_advanced_records.ndjson", "unique_record_count": 1,
                  "records_sha256": FALLBACK.stable_hash([walked]),
                  "memberships_file": "congress_advanced_memberships.ndjson", "membership_count": 1,
                  "memberships_sha256": FALLBACK.stable_hash(base_members)}})

    def fetch(url: str, limit: int) -> bytes:
        return responses[url]

    for _ in range(2):   # F1 then F2: neither may fail on the walked row
        FALLBACK.run_fallback(registry_path=registry, baseline_dir=baseline, out_dir=out,
                              browser_failure_path=failure, workers=1, fetch=fetch)
        kept = {row["canonical_key"]: row for row in FALLBACK._read_ndjson(out / "congress_advanced_records.ndjson")}
        assert kept["119:hr:1"] == walked and len(kept) == 3
        assert json.loads((out / "manifest.json").read_text())["cumulative_base"] == FALLBACK.LINEAGE_MEMBER_PAGES

    # The immutable lineage keeps its byte-equality guard.
    clean = tmp_path / "clean"
    FALLBACK.run_fallback(registry_path=registry, baseline_dir=baseline, out_dir=clean / "o",
                          browser_failure_path=failure, workers=1, fetch=fetch)
    rows = FALLBACK._read_ndjson(clean / "o" / "congress_advanced_records.ndjson")
    rows[0] = {**rows[0], "title": "mutated"}
    write_ndjson(clean / "o" / "congress_advanced_records.ndjson", rows)
    manifest = json.loads((clean / "o" / "manifest.json").read_text())
    manifest["union"]["records_sha256"] = FALLBACK.stable_hash(rows)
    write_json(clean / "o" / "manifest.json", manifest)
    assert manifest["cumulative_base"] == FALLBACK.LINEAGE_IMMUTABLE
    with pytest.raises(FALLBACK.FallbackError, match="prior fallback mutated a baseline record"):
        FALLBACK.run_fallback(registry_path=registry, baseline_dir=baseline, out_dir=clean / "o",
                              browser_failure_path=failure, workers=1, fetch=fetch)


def test_a_fallback_that_died_after_replacing_the_files_recovers_from_the_pending_manifest(tmp_path: Path, monkeypatch) -> None:
    registry, baseline, out, failure, responses = setup_fixture(tmp_path)

    def fetch(url: str, limit: int) -> bytes:
        return responses[url]

    real_write_json = FALLBACK._write_json

    def dying_write_json(path, value):
        # Die on the final manifest.json write (after the pending manifest and the union files).
        if Path(path).name == "manifest.json" and value.get("status") == "complete" and not value.get("pending"):
            raise OSError("simulated crash before manifest.json")
        return real_write_json(path, value)

    monkeypatch.setattr(FALLBACK, "_write_json", dying_write_json)
    with pytest.raises(OSError):
        FALLBACK.run_fallback(registry_path=registry, baseline_dir=baseline, out_dir=out,
                              browser_failure_path=failure, workers=1, fetch=fetch)
    assert (out / FALLBACK.PENDING_MANIFEST).exists()
    assert json.loads((out / "manifest.json").read_text())["status"] == "in_progress"
    monkeypatch.setattr(FALLBACK, "_write_json", real_write_json)
    result = FALLBACK.run_fallback(registry_path=registry, baseline_dir=baseline, out_dir=out,
                                   browser_failure_path=failure, workers=1, fetch=fetch)
    assert result["union"]["unique_record_count"] == 3
    assert not (out / FALLBACK.PENDING_MANIFEST).exists()


def test_malformed_official_source_fails_before_union_replacement(tmp_path: Path) -> None:
    registry, baseline, out, failure, responses = setup_fixture(tmp_path)

    def fetch(url: str, limit: int) -> bytes:
        return responses[url]

    FALLBACK.run_fallback(
        registry_path=registry,
        baseline_dir=baseline,
        out_dir=out,
        browser_failure_path=failure,
        workers=1,
        fetch=fetch,
    )
    before = (out / "congress_advanced_records.ndjson").read_bytes()
    sitemap_url = BILLSTATUS.expected_sitemap_url(119, "hr")
    responses[sitemap_url] = b"<urlset><url>"
    with pytest.raises(FALLBACK.FallbackError, match="malformed sitemap"):
        FALLBACK.run_fallback(
            registry_path=registry,
            baseline_dir=baseline,
            out_dir=out,
            browser_failure_path=failure,
            workers=1,
            fetch=fetch,
        )
    assert (out / "congress_advanced_records.ndjson").read_bytes() == before


def test_wrapper_only_accepts_fresh_fail_closed_verification_receipt(tmp_path: Path) -> None:
    stale = tmp_path / "manifest.partial.1.json"
    fresh = tmp_path / "manifest.partial.2.json"
    body = {
        "status": "failed",
        "automatic_verification_timeout": {
            "collection_stopped_without_result_acceptance": True
        },
        "error": {"code": "CONGRESS_AUTOMATIC_VERIFICATION_TIMEOUT"},
    }
    write_json(stale, body)
    old = time.time() - 100
    stale.touch()
    import os

    os.utime(stale, (old, old))
    started = time.time()
    write_json(fresh, body)
    assert (
        REFRESH.latest_automatic_verification_failure(
            tmp_path, started_after=started
        )
        == fresh
    )
    body["error"]["code"] = "SOME_OTHER_FAILURE"
    write_json(fresh, body)
    assert (
        REFRESH.latest_automatic_verification_failure(
            tmp_path, started_after=started
        )
        is None
    )


def test_read_json_retries_transient_einval(tmp_path, monkeypatch):
    # OneDrive placeholder hydration raises [Errno 22] transiently (M11, 2026-10-24).
    target = tmp_path / "manifest.json"
    write_json(target, {"status": "complete"})
    real = Path.read_text
    calls = {"n": 0}

    def flaky(self, *args, **kwargs):
        if self == target and calls["n"] < 2:
            calls["n"] += 1
            raise OSError(22, "Invalid argument")
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", flaky)
    monkeypatch.setattr(FALLBACK.time, "sleep", lambda _s: None)
    assert FALLBACK._read_json(target) == {"status": "complete"}
    assert calls["n"] == 2


def test_read_json_persistent_einval_still_fails_clearly(tmp_path, monkeypatch):
    target = tmp_path / "manifest.json"
    write_json(target, {})

    def broken(self, *args, **kwargs):
        raise OSError(22, "Invalid argument")

    monkeypatch.setattr(Path, "read_text", broken)
    monkeypatch.setattr(FALLBACK.time, "sleep", lambda _s: None)
    with pytest.raises(FALLBACK.FallbackError, match="invalid JSON artifact"):
        FALLBACK._read_json(target)


def test_collector_command_headed_by_default_headless_opt_in():
    headed = REFRESH.collector_command("node", "out", 1500, None, False)
    assert "--headless" not in headed and "--headed" in headed
    assert "--headless" in REFRESH.collector_command("node", "out", 1500, "a,b", True)
    assert REFRESH.collector_command("node", "out", 1, "a,b", False)[-2:] == ["--categories", "a,b"]


def test_a_fallback_that_died_between_its_two_renames_is_completed_by_the_next_run(tmp_path: Path, monkeypatch) -> None:
    """Re-review 2026-10-27 finding 1: new records + old memberships must not wedge discovery."""
    registry, baseline, out, failure, responses = setup_fixture(tmp_path)

    def fetch(url: str, limit: int) -> bytes:
        return responses[url]

    real_promote = FALLBACK._promote

    def dying_promote(staged, final):
        if final.name == "congress_advanced_memberships.ndjson":
            raise PermissionError("simulated OneDrive sharing lock")
        return real_promote(staged, final)

    monkeypatch.setattr(FALLBACK, "_promote", dying_promote)
    with pytest.raises(PermissionError):
        FALLBACK.run_fallback(registry_path=registry, baseline_dir=baseline, out_dir=out,
                              browser_failure_path=failure, workers=1, fetch=fetch)
    assert (out / "congress_advanced_memberships.ndjson.next").exists()
    monkeypatch.setattr(FALLBACK, "_promote", real_promote)
    result = FALLBACK.run_fallback(registry_path=registry, baseline_dir=baseline, out_dir=out,
                                   browser_failure_path=failure, workers=1, fetch=fetch)
    assert result["union"]["unique_record_count"] == 3 and result["union"]["membership_count"] == 4
    assert not (out / "congress_advanced_memberships.ndjson.next").exists()


def test_a_verified_union_from_another_registry_is_refused_not_replaced_by_the_baseline(tmp_path: Path) -> None:
    """Re-review finding 7: never silently restart from the baseline over a union this run cannot extend."""
    registry, baseline, out, failure, responses = setup_fixture(tmp_path)

    def fetch(url: str, limit: int) -> bytes:
        return responses[url]

    FALLBACK.run_fallback(registry_path=registry, baseline_dir=baseline, out_dir=out,
                          browser_failure_path=failure, workers=1, fetch=fetch)
    manifest = json.loads((out / "manifest.json").read_text())
    manifest["registry"]["sha256"] = "0" * 64
    write_json(out / "manifest.json", manifest)
    before = (out / "congress_advanced_records.ndjson").read_bytes()
    with pytest.raises(FALLBACK.FallbackError, match="does not descend from this registry and baseline"):
        FALLBACK.run_fallback(registry_path=registry, baseline_dir=baseline, out_dir=out,
                              browser_failure_path=failure, workers=1, fetch=fetch)
    assert (out / "congress_advanced_records.ndjson").read_bytes() == before


def test_a_fresh_directory_whose_first_fallback_died_early_is_not_wedged(tmp_path: Path) -> None:
    """Re-review finding 6: a demoted manifest that names no union files is not drift."""
    registry, baseline, out, failure, responses = setup_fixture(tmp_path)
    write_json(out / "manifest.json", {"schema": FALLBACK.MANIFEST_SCHEMA, "status": "in_progress"})

    def fetch(url: str, limit: int) -> bytes:
        return responses[url]

    result = FALLBACK.run_fallback(registry_path=registry, baseline_dir=baseline, out_dir=out,
                                   browser_failure_path=failure, workers=1, fetch=fetch)
    assert result["union"]["unique_record_count"] == 3