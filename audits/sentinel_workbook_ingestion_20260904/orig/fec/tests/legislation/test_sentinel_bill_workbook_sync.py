from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "fec" / "legislation" / "sync_sentinel_bill_ledger.py"


def load_module():
    spec = importlib.util.spec_from_file_location("sentinel_sync", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_plan_tracks_canonical_ids_and_only_verified_rows_score(tmp_path, monkeypatch):
    module = load_module()
    repository_path = tmp_path / "repository.json"
    repository_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(module, "REPOSITORY", repository_path)
    repository = {"bills": {"119:hr:7": {
        "key": "119:hr:7", "display": "H.R.7", "congress": 119,
        "type": "hr", "number": 7, "title": "Test Act",
        "sponsor": {"name": "Rep. Sponsor"}, "cosponsor_count": 3,
        "introduced_date": "2025-01-03", "update_date": "2026-09-01",
        "latest_action": {"date": "2026-08-31", "text": "Introduced"},
        "policy_area": "Finance", "source": "GovInfo",
        "url": "https://www.congress.gov/bill/119th-congress/house-bill/7",
        "summary": "Summary", "updated_at": "2026-09-02T00:00:00Z",
    }}}
    updates = [{
        "repository_key": "119:hr:7", "member": "Member One",
        "bioguide": "M000001", "role": "original", "join_date": "2025-01-03",
        "areas": ["Payments"], "source": "GovInfo", "verified_at": "2026-09-02T00:00:00Z",
    }]
    pending = [{
        "repository_key": "119:hr:7", "member": "Member Two",
        "role": "cosponsor", "reason": "needs review", "verified_at": "2026-09-02T00:00:00Z",
    }]
    plan = module.build_plan(repository, updates, pending,
                             discovery=[{"canonical_key":"119:s:9","display_number":"S.9","congress":119,"type":"s","number":9,"candidate_status":"included_unreviewed_candidate"}],
                             adjudications=[],
                             input_path=tmp_path / "in.xlsx", output_path=tmp_path / "out.xlsx")
    assert plan["counts"] == {
        "repository_bills": 1, "verified_memberships": 1,
        "verified_interaction_rows": 1, "pending_memberships": 1,
        "ledger_rows_excluding_header": 4,
        "discovery_candidates": 1, "discovery_only_ids": 1,
        "discovery_pending_review": 1,
    }
    header = plan["ledger_rows"][0]
    rows = [dict(zip(header, row)) for row in plan["ledger_rows"][1:]]
    assert {row["Canonical Bill ID"] for row in rows} == {"119:hr:7", "119:s:9"}
    assert sum(bool(row["Scoring Eligible"]) for row in rows) == 1
    assert plan["accepted_interactions"][0]["sheet"] == "Original Co-Sponsor Interaction"
    assert plan["accepted_interactions"][0]["values"][1] == "original-cosponsor"


def test_pipeline_orders_workbook_sync_before_legislative_consumers():
    source = (ROOT / "fec" / "run_pipeline.py").read_text(encoding="utf-8")
    verify = source.index("('verify_collector_roster_updates.py',[])")
    sync = source.index("('sync_sentinel_bill_ledger.py',[])")
    archive = source.index("('build_archive_legislative.py',[])")
    stance = source.index("('per_category_stance.py',[])")
    pillars = source.index("('compute_pillars.py',['--write'])")
    assert verify < sync < archive < stance < pillars

    weekly = (ROOT / "fec" / "weekly_refresh.py").read_text(encoding="utf-8")
    discovery = weekly.index("'legislation/refresh_legislation_discovery.py'")
    repository = weekly.index("'legislation/update_bill_repository.py'", discovery)
    full_pipeline = weekly.index("'run_pipeline.py'", repository)
    assert discovery < repository < full_pipeline


def test_archive_builder_reads_only_scoring_eligible_workbook_rows():
    source = (ROOT / "fec" / "legislation" / "build_archive_legislative.py").read_text(encoding="utf-8")
    assert "sheet_name='Sentinel Bill Ledger'" in source
    assert "'Scoring Eligible'" in source
    assert "_sentinel[_eligible]" in source


def test_workbook_writer_is_artifact_tool_only():
    source = (ROOT / "fec" / "sync_sentinel_bill_ledger_artifact.cjs").read_text(encoding="utf-8")
    assert '@oai/artifact-tool' in source
    assert "Workbook.create" in source
    assert "SpreadsheetFile.exportXlsx" in source
    assert "openpyxl" not in source
