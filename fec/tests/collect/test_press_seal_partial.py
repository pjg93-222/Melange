# -*- coding: utf-8 -*-
"""PS: a press run that skipped any member site is sealed PARTIAL, never PASS (Paul 2026-10-26, D-294).

Offline: the R wrapper is not run (its receipt fields are pinned by source); the intake gate
(validate_body_completion / inspect_run), the same-day reuse test and the collection audit read real files.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

FEC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FEC))
from collect import refresh_press_stream as stream
from collect.build_press_engine_feed import ReceiptRejected, validate_body_completion
from test_press_audit_scored_partitions import PENDING, audit, dated, failed

SKIP = {"member_id": "O000174", "source": "official_wordpress_custom_post",
        "url": "https://www.ossoff.senate.gov/wp-json/wp/v2/types", "error_class": "http_403"}
NAMED = {k: SKIP[k] for k in ("member_id", "url", "error_class")}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seal_sites(root, receipt, failures=(SKIP,), status="PARTIAL", pending=0):
    """Write the walk's sealed press_site_failures.json and the receipt fields R writes beside it."""
    path = Path(root) / "press_site_failures.json"
    path.write_text(json.dumps({"schema": "press-site-failures-v1", "failures": list(failures)}), encoding="utf-8")
    receipt.update(status=status, site_failures=len(failures), site_failures_sha256=sha(path),
                   skipped_sites=[{k: f[k] for k in NAMED} for f in failures])
    if not pending:
        receipt["pending_body_urls"] = 0


def test_a_skipped_site_gives_a_partial_receipt_the_intake_accepts_and_names_the_site(tmp_path, monkeypatch):
    first = dated("a")
    audited = audit(tmp_path, monkeypatch, dated_rows=[first], scored_rows=[first],
                    mutate=lambda root, receipt: seal_sites(root, receipt))
    assert audited["errors"] == [], audited
    assert audited["live_network_retry_receipt_valid"] is True
    assert audited["press_receipt_status"] == "PARTIAL"
    assert audited["coverage_complete"] is False
    assert audited["site_failures_skipped"] == [NAMED]
    assert audited["pending_body_urls_carried"] == 0


def test_no_skip_stays_pass_and_unchanged(tmp_path, monkeypatch):
    first = dated("a")
    audited = audit(tmp_path, monkeypatch, dated_rows=[first], scored_rows=[first])
    assert audited["errors"] == [], audited
    assert audited["press_receipt_status"] == "PASS" and audited["coverage_complete"] is True
    assert audited["site_failures_skipped"] == []


def test_an_empty_failures_file_beside_a_pass_receipt_is_still_pass(tmp_path, monkeypatch):
    first = dated("a")
    audited = audit(tmp_path, monkeypatch, dated_rows=[first], scored_rows=[first],
                    mutate=lambda root, receipt: seal_sites(root, receipt, failures=(), status="PASS"))
    assert audited["errors"] == [], audited
    assert audited["press_receipt_status"] == "PASS" and audited["site_failures_skipped"] == []


def test_the_audit_never_says_pass_when_a_site_was_skipped(tmp_path, monkeypatch):
    first = dated("a")
    audited = audit(tmp_path, monkeypatch, dated_rows=[first], scored_rows=[first],
                    mutate=lambda root, receipt: seal_sites(root, receipt, status="PASS"))
    assert audited["live_network_retry_receipt_valid"] is False
    assert any("PASS_OVER_SKIPPED_SITES" in error for error in audited["errors"]), audited


def test_a_skip_plus_a_pending_backlog_is_accepted_and_both_are_reported(tmp_path, monkeypatch):
    first, held = dated("a"), failed("p", PENDING, bioguide="X000009")
    audited = audit(tmp_path, monkeypatch, dated_rows=[first], failed_rows=[held], scored_rows=[first],
                    mutate=lambda root, receipt: seal_sites(root, receipt, pending=1))
    assert audited["errors"] == [], audited
    assert audited["pending_body_urls_carried"] == 1 and audited["site_failures_skipped"] == [NAMED]


@pytest.mark.parametrize("tamper", ["count", "hash", "file_removed"])
def test_integrity_failures_stay_fatal(tmp_path, monkeypatch, tamper):
    def mutate(root, receipt):
        seal_sites(root, receipt)
        if tamper == "count":
            receipt["site_failures"] = 5
        elif tamper == "hash":
            receipt["site_failures_sha256"] = "0" * 64
        else:
            (Path(root) / "press_site_failures.json").unlink()
    first = dated("a")
    audited = audit(tmp_path, monkeypatch, dated_rows=[first], scored_rows=[first], mutate=mutate)
    assert audited["live_network_retry_receipt_valid"] is False
    assert audited["coverage_complete"] is False          # CodeRabbit PR #94: invalid proof is never complete
    assert any("SITE_FAILURES_PROOF_MISMATCH" in error for error in audited["errors"]), audited


def test_partial_with_no_backlog_and_no_skipped_site_is_still_refused(tmp_path):
    (tmp_path / "press_delta_pending.csv").write_text("bioguide,url,date,collection_status\n", encoding="utf-8")
    receipt = {"mode": "live_network_retry", "status": "PARTIAL", "pending_body_urls": 0,
               "pending_body_urls_sha256": sha(tmp_path / "press_delta_pending.csv")}
    with pytest.raises(ReceiptRejected) as refused:
        validate_body_completion(tmp_path, receipt)
    assert refused.value.reason == "PENDING_BODY_ATTEMPTS"


def test_a_sites_only_partial_cannot_hide_pending_rows(tmp_path):
    pending = tmp_path / "press_delta_pending.csv"
    pending.write_text('bioguide,url,date,collection_status\n"X1","https://e.gov/a",NA,"p"\n', encoding="utf-8")
    receipt = {"mode": "live_network_retry", "pending_body_urls_sha256": sha(pending)}
    seal_sites(tmp_path, receipt)
    with pytest.raises(ReceiptRejected) as refused:
        validate_body_completion(tmp_path, receipt)
    assert refused.value.reason == "PENDING_BODY_PROOF_MISMATCH"


def _reuse(monkeypatch, receipt):
    monkeypatch.setattr(stream, "valid_run", lambda root: (None, receipt))
    return stream.current_source_run(Path("x"), "S")


def test_a_same_day_sites_only_partial_is_reused_not_rewalked(monkeypatch):
    receipt = {"collector_sources_sha256": "S", "status": "PARTIAL", "pending_body_urls": 0, "site_failures": 1}
    assert _reuse(monkeypatch, receipt) is not None


def test_a_partial_with_nothing_to_carry_is_still_rewalked_and_a_pass_is_reused(monkeypatch):
    base = {"collector_sources_sha256": "S", "pending_body_urls": 0}
    assert _reuse(monkeypatch, {**base, "status": "PARTIAL", "site_failures": 0}) is None
    assert _reuse(monkeypatch, {**base, "status": "PASS", "site_failures": 0}) is not None


def test_the_r_receipt_is_partial_for_skipped_sites_and_binds_the_file():
    source = (FEC / "collect" / "refresh_press_delta.R").read_text(encoding="utf-8")
    assert 'status = if (nrow(pending) || length(site_rows)) "PARTIAL" else "PASS"' in source
    assert "site_failures_sha256 = if (file.exists(site_failures_path))" in source
    assert "skipped_sites = lapply(site_rows" in source
    # the skipped-site file is written before the receipt; a sites-only PARTIAL still exits 0 (the weekly continues)
    assert source.index('promote_with_backup(site_failures_temp') < source.rindex("completion <- write_retry_receipt")
    assert "if (completion$pending_body_urls) 3L else 0L" in source


def test_retry_from_copies_the_parents_skipped_sites_before_the_receipt_is_written():
    source = (FEC / "collect" / "refresh_press_delta.R").read_text(encoding="utf-8")
    copy = source.index("file.copy(parent_site_failures, target_site_failures, overwrite = TRUE)")
    # a failed copy stops the recovery, and a stale file is removed when the parent has none (CodeRabbit PR #94)
    assert "if (!isTRUE(file.copy(parent_site_failures, target_site_failures, overwrite = TRUE)))" in source
    assert "unlink(target_site_failures)" in source and 'stop("failed to remove a stale press_site_failures.json' in source
    # the parent's proof is validated against the parent receipt before it is copied (CodeRabbit PR #94)
    assert source.index("validate_site_failures_proof(source_root,") < copy
    assert source.index("import_official_coverage_from_run(source_root)") < copy
    assert copy < source.rindex("completion <- write_retry_receipt")
    assert copy < source.index("run_receipt_metrics$retry_source_run <- basename(source_root)")


def test_a_historical_recovery_receipt_over_inherited_skips_is_partial_and_never_pass(tmp_path):
    (tmp_path / "press_delta_pending.csv").write_text("bioguide,url,date,collection_status\n", encoding="utf-8")
    base = {"mode": "historical_body_recovery", "pending_body_urls": 0,
            "pending_body_urls_sha256": sha(tmp_path / "press_delta_pending.csv")}
    partial = dict(base)
    seal_sites(tmp_path, partial)                        # the parent's file, copied in
    assert validate_body_completion(tmp_path, partial, require_complete=True)["site_failures_skipped"] == [NAMED]
    passing = {**partial, "status": "PASS"}
    with pytest.raises(ReceiptRejected) as refused:
        validate_body_completion(tmp_path, passing, require_complete=True)
    assert refused.value.reason == "PASS_OVER_SKIPPED_SITES"


def test_feed_coverage_names_the_sites_from_the_validated_file_not_the_receipt_copy(tmp_path):
    # CodeRabbit PR #94: _coverage used the receipt's own skipped_sites; it now uses site_failure_proof.
    from collect import build_press_engine_feed as feed
    receipt = {"mode": "live_network_retry"}
    seal_sites(tmp_path, receipt)
    receipt["skipped_sites"] = [{"member_id": "X000001", "url": "https://elsewhere.example.com", "error_class": "timeout"}]
    coverage = feed._coverage(tmp_path, receipt)
    assert coverage["complete"] is False and coverage["site_failures_skipped"] == [NAMED]
    clean = {"mode": "live_network_retry"}
    seal_sites(tmp_path, clean, failures=(), status="PASS")
    assert feed._coverage(tmp_path, clean) == {"complete": True, "pending_body_urls_carried": 0,
                                               "pending_body_urls_sha256": None, "pending_members": {}}


def test_score_only_admits_a_sites_only_partial_only_with_its_proof_intact():
    # CodeRabbit PR #94: load_valid_retry_receipt checks press_site_failures.json against the receipt.
    source = (FEC / "collect" / "refresh_press_delta.R").read_text(encoding="utf-8")
    helper = source[source.index("validate_site_failures_proof <- function(root, receipt)"):]
    helper = helper[:helper.index("\n}\n")]
    assert "is.null(claimed)" in helper and "is missing" in helper and "sha256_file(path)" in helper
    gate = source[source.index("load_valid_retry_receipt <- function()"):]
    gate = gate[:gate.index("\n}\n")]
    assert "validate_site_failures_proof(run_root, receipt)" in gate
