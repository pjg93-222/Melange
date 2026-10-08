"""Synthetic-only regression tests for receipt-bound checkpoint repair."""

import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from audits.staffer_network import repair_politico_profile_checkpoint as repair
from audits.staffer_network import verify_politico_profile_crawl as verify

API_PERSON_PREFIX = "https://directory.politicopro.com/proxy/lava/api/v1/person/"


class RepairFixture(unittest.TestCase):
    """Shared synthetic checkpoint: one good, one partial and one 404 row."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.directory = self.root / "directory.ndjson"
        self.profiles = self.root / "profiles.ndjson"
        self.state = self.root / "state.json"
        self.verification = self.root / "verification.json"
        self.quarantine = self.root / "quarantine.ndjson"
        self.receipt = self.root / "repair.json"
        self.rows = [self.profile("good"), self.profile("partial"), self.profile("unavailable")]
        self.rows[1].update(verified_name="My Notes", identity_status="LIVE_NAME_CHANGED_SAME_UUID",
                            review_status="IDENTITY_EXCEPTION_REVIEW_REQUIRED", employment_history=[])
        self.rows[2].update(verified_name=None, identity_status="PROFILE_UNAVAILABLE_404",
                            review_status="IDENTITY_EXCEPTION_REVIEW_REQUIRED",
                            unavailable_evidence="HTTP_404", response_status=404,
                            observed_source_url=verify.PROFILE_URL_PREFIX + "unavailable")
        for field in repair.PROFILE_COLLECTIONS:
            self.rows[2][field] = []
        self.directory.write_text(repair.ndjson_text([
            {"profile_uuid": row["profile_uuid"], "name": row["expected_name"], "roles": []}
            for row in self.rows
        ]), encoding="utf-8")
        self.profiles.write_text(repair.ndjson_text(self.rows), encoding="utf-8")
        self.state.write_text(json.dumps({
            "schema_id": "politico-profile-crawl-state-v1", "scope": "ALL_CURRENT_PROFILES",
            "queue_total": 3, "total_succeeded": 3, "total_failed": 0,
            "remaining": 0, "halted": False, "max_requests_per_minute": 40,
        }), encoding="utf-8")

    @staticmethod
    def profile(profile_id):
        return {
            "profile_uuid": profile_id, "expected_name": "Test " + profile_id,
            "verified_name": "Test " + profile_id, "identity_status": "UUID_AND_NAME_MATCH",
            "partition": "staffer", "source_card_roles": [], "source_card_issue_areas": [],
            "current_header_positions": ["Assistant for Test Member"], "explicit_side_labels": [],
            "profile_issue_areas": [], "education": [],
            "employment_history": [{"employer": "Test Member", "title": "Assistant", "date_text": ""}],
            "observed_at": "2026-09-04T00:00:00Z",
            "source_url": verify.PROFILE_URL_PREFIX + profile_id,
            "review_status": "REVIEW_REQUIRED", "contact_fields_collected": False,
        }

    def run_verifier(self):
        args = ["verify", "--directory", str(self.directory), "--profiles", str(self.profiles),
                "--state", str(self.state), "--output", str(self.verification)]
        with patch.object(sys, "argv", args), patch.object(verify, "EXPECTED_CORPUS_TOTAL", len(self.rows)), contextlib.redirect_stdout(io.StringIO()):
            code = verify.main()
        return code, json.loads(self.verification.read_text(encoding="utf-8"))

    def rewrite_corpus(self):
        """Re-seal the directory, profile rows and state around ``self.rows``."""
        self.directory.write_text(repair.ndjson_text([
            {"profile_uuid": row["profile_uuid"], "name": row["expected_name"], "roles": []}
            for row in self.rows
        ]), encoding="utf-8")
        self.profiles.write_text(repair.ndjson_text(self.rows), encoding="utf-8")
        self.state.write_text(json.dumps({
            "schema_id": "politico-profile-crawl-state-v1", "scope": "ALL_CURRENT_PROFILES",
            "queue_total": len(self.rows), "total_succeeded": len(self.rows), "total_failed": 0,
            "remaining": 0, "halted": False, "max_requests_per_minute": 40,
        }), encoding="utf-8")

    def declared_source_incomplete(self, profile_id="declared"):
        """An API-extracted row whose bound source evidence omits both collections."""
        row = self.profile(profile_id)
        data = {"lexiconId": profile_id, "name": {"displayName": row["verified_name"]},
                "stafferPositions": [], "employmentItems": []}
        row.update(current_header_positions=[], employment_history=[],
                   extraction_method="AUTHENTICATED_PERSON_API_V1",
                   content_status=repair.SOURCE_INCOMPLETE_DECLARATION,
                   source_missing_collections=["current_header_positions", "employment_history"],
                   source_api_url=API_PERSON_PREFIX + profile_id,
                   projected_api_sha256=verify.evidence_digest(data))
        evidence = {"profile_uuid": profile_id, "status": 200,
                    "url": API_PERSON_PREFIX + profile_id, "data": data}
        return row, evidence

    def seed_source_incomplete(self, *extra_rows):
        """good + declared-missing + 404 (+ callers' extra rows), with API evidence."""
        declared, evidence = self.declared_source_incomplete()
        self.rows = [self.rows[0], declared, self.rows[2], *extra_rows]
        (self.root / "api_projected_evidence_20260905.ndjson").write_text(
            repair.ndjson_text([evidence]), encoding="utf-8")
        self.rewrite_corpus()
        return declared

    def patch_verification(self, **changes):
        result = json.loads(self.verification.read_text(encoding="utf-8"))
        result.update(changes)
        self.verification.write_text(json.dumps(result), encoding="utf-8")
        return result

    def run_repair(self, *extra):
        args = ["--profiles", str(self.profiles), "--verification", str(self.verification),
                "--state", str(self.state), "--quarantine", str(self.quarantine),
                "--receipt", str(self.receipt), *extra]
        with contextlib.redirect_stdout(io.StringIO()):
            return repair.main(args)

    def assert_no_mutation_on_error(self, expression, *extra):
        originals = {path: path.read_bytes() for path in (self.profiles, self.state)}
        with self.assertRaisesRegex(ValueError, expression):
            self.run_repair(*extra)
        for path, original in originals.items():
            self.assertEqual(path.read_bytes(), original)
        self.assertFalse(self.quarantine.exists())
        self.assertFalse(self.receipt.exists())


class CheckpointRepairTests(RepairFixture):
    def test_renamed_shell_fails_content_gate(self):
        code, result = self.run_verifier()
        self.assertEqual(code, 1)
        self.assertEqual(result["integrity_status"], "FAIL")
        self.assertEqual(result["verification_failures"]["incomplete_profile_content"][0]["profile_uuid"], "partial")
        self.assertEqual(result["input_sha256"]["profiles"], repair.sha256_path(self.profiles))

    def test_renamed_complete_profile_remains_supported(self):
        self.rows[1]["employment_history"] = copy.deepcopy(self.rows[0]["employment_history"])
        self.profiles.write_text(repair.ndjson_text(self.rows), encoding="utf-8")
        code, result = self.run_verifier()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["counts"]["content_bearing_profiles"], 2)

    def test_requeue_all_404_preserves_originals_and_exact_union(self):
        self.run_verifier()
        self.assertEqual(self.run_repair("--requeue-all-unavailable-404"), 0)
        self.assertEqual([row["profile_uuid"] for row in repair.read_ndjson(self.profiles)], ["good"])
        quarantine = repair.read_ndjson(self.quarantine)
        self.assertEqual([item["row"] for item in quarantine], self.rows[1:])
        result = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(result["counts"]["incomplete_rows_quarantined_for_requeue"], 1)
        self.assertEqual(result["counts"]["profile_unavailable_404_rows_quarantined_for_requeue"], 1)
        self.assertEqual(result["counts"]["profile_unavailable_404_rows_normalized"], 0)
        self.assertEqual(result["counts"]["state_remaining_after"], 2)
        self.assertTrue(result["invariants"]["removed_ids_exactly_equal_verifier_incomplete_union_selected_404_ids"])

    def test_default_normalizes_only_flagged_404_and_preserves_original(self):
        self.rows[2]["current_header_positions"] = ["Unrelated Footer"]
        self.profiles.write_text(repair.ndjson_text(self.rows), encoding="utf-8")
        self.run_verifier()
        self.run_repair()
        result = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(result["counts"]["profile_unavailable_404_rows_normalized"], 1)
        self.assertEqual(result["counts"]["profile_unavailable_404_rows_quarantined_for_requeue"], 0)
        self.assertEqual(repair.read_ndjson(self.quarantine)[1]["row"], self.rows[2])
        self.assertEqual(repair.read_ndjson(self.profiles)[1]["current_header_positions"], [])

    def test_opt_in_requeues_policy_violating_404_instead_of_normalizing(self):
        self.rows[2]["current_header_positions"] = ["Unrelated Footer"]
        self.profiles.write_text(repair.ndjson_text(self.rows), encoding="utf-8")
        self.run_verifier()
        self.run_repair("--requeue-all-unavailable-404")
        result = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertEqual(result["counts"]["profile_unavailable_404_rows_normalized"], 0)
        self.assertEqual(result["counts"]["profile_unavailable_404_rows_quarantined_for_requeue"], 1)
        self.assertEqual(repair.read_ndjson(self.quarantine)[1]["row"], self.rows[2])

    def test_stale_profiles_are_rejected_without_mutation(self):
        self.run_verifier()
        self.profiles.write_text(self.profiles.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.assert_no_mutation_on_error("stale or unbound verifier profiles")

    def test_stale_state_is_rejected_without_mutation(self):
        self.run_verifier()
        self.state.write_text(self.state.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.assert_no_mutation_on_error("stale or unbound verifier state")

    def test_wrong_path_is_rejected_even_for_identical_bytes(self):
        self.run_verifier()
        result = json.loads(self.verification.read_text(encoding="utf-8"))
        result["inputs"]["profiles"] = str(self.root / "another.ndjson")
        self.verification.write_text(json.dumps(result), encoding="utf-8")
        self.assert_no_mutation_on_error("different profiles path")

    def test_unsupported_failure_category_is_rejected(self):
        self.run_verifier()
        result = json.loads(self.verification.read_text(encoding="utf-8"))
        result["verification_failures"]["source_url_mismatches"] = [{"profile_uuid": "good"}]
        self.verification.write_text(json.dumps(result), encoding="utf-8")
        self.assert_no_mutation_on_error("unsupported verifier failures")

    def test_unsupported_target_id_is_rejected(self):
        self.run_verifier()
        result = json.loads(self.verification.read_text(encoding="utf-8"))
        result["verification_failures"]["incomplete_profile_content"][0]["profile_uuid"] = "not-present"
        self.verification.write_text(json.dumps(result), encoding="utf-8")
        self.assert_no_mutation_on_error("incomplete targets do not exactly match")

    def test_unbound_legacy_receipt_is_rejected(self):
        self.run_verifier()
        result = json.loads(self.verification.read_text(encoding="utf-8"))
        result.pop("input_sha256")
        self.verification.write_text(json.dumps(result), encoding="utf-8")
        self.assert_no_mutation_on_error("stale or unbound verifier profiles")

    def test_repair_requires_fail_even_with_404_opt_in(self):
        self.rows[1]["employment_history"] = copy.deepcopy(self.rows[0]["employment_history"])
        self.profiles.write_text(repair.ndjson_text(self.rows), encoding="utf-8")
        self.run_verifier()
        self.assert_no_mutation_on_error("requires a verifier FAIL", "--requeue-all-unavailable-404")

    def test_legacy_404_without_evidence_requires_recollection(self):
        for key in ("unavailable_evidence", "response_status", "observed_source_url"):
            self.rows[2].pop(key)
        self.profiles.write_text(repair.ndjson_text(self.rows), encoding="utf-8")
        _, result = self.run_verifier()
        failures = result["verification_failures"]["identity_exception_policy_violations"]
        self.assertEqual([item["profile_uuid"] for item in failures], ["unavailable"])
        self.assertFalse(failures[0]["unavailable_evidence_valid"])
        self.assert_no_mutation_on_error("evidence cannot be normalized")
        self.run_repair("--requeue-all-unavailable-404")
        self.assertEqual(repair.read_ndjson(self.quarantine)[1]["row"], self.rows[2])

    def test_404_evidence_must_match_http_status(self):
        self.rows[2]["response_status"] = 200
        self.profiles.write_text(repair.ndjson_text(self.rows), encoding="utf-8")
        _, result = self.run_verifier()
        self.assertEqual(len(result["verification_failures"]["identity_exception_policy_violations"]), 1)

    def test_soft404_evidence_with_api404_is_supported(self):
        self.rows[2].update(unavailable_evidence="STABLE_SCOPED_ERROR_HEADING", response_status=200,
                            profile_api_status=404)
        self.profiles.write_text(repair.ndjson_text(self.rows), encoding="utf-8")
        _, result = self.run_verifier()
        self.assertEqual(result["verification_failures"]["identity_exception_policy_violations"], [])

    def test_soft404_without_api404_proof_must_be_requeued(self):
        for api_status in (None, 200, 400, 401, 403, 429, 500):
            with self.subTest(profile_api_status=api_status):
                self.rows[2].update(unavailable_evidence="STABLE_SCOPED_ERROR_HEADING", response_status=200)
                if api_status is None:
                    self.rows[2].pop("profile_api_status", None)
                else:
                    self.rows[2]["profile_api_status"] = api_status
                self.profiles.write_text(repair.ndjson_text(self.rows), encoding="utf-8")
                _, result = self.run_verifier()
                failures = result["verification_failures"]["identity_exception_policy_violations"]
                self.assertEqual([item["profile_uuid"] for item in failures], ["unavailable"])
                self.assertFalse(failures[0]["unavailable_evidence_valid"])
                self.assert_no_mutation_on_error("evidence cannot be normalized")
        self.run_repair("--requeue-all-unavailable-404")
        self.assertEqual(repair.read_ndjson(self.quarantine)[1]["row"], self.rows[2])

    def test_observed_url_mismatch_is_checked_for_non404(self):
        self.rows[0]["observed_source_url"] = verify.PROFILE_URL_PREFIX + "wrong-uuid"
        self.profiles.write_text(repair.ndjson_text(self.rows), encoding="utf-8")
        _, result = self.run_verifier()
        failures = result["verification_failures"]["source_url_mismatches"]
        self.assertEqual(failures[0]["field"], "observed_source_url")
        self.assert_no_mutation_on_error("unsupported verifier failures")


class SourceIncompleteRequeueTests(RepairFixture):
    """Owner ruling 2026-09-05: requeue declared-missing rows through the browser."""

    def test_declared_missing_rows_verify_clean_and_are_requeued(self):
        declared = self.seed_source_incomplete()
        code, result = self.run_verifier()
        self.assertEqual(code, 0)
        self.assertEqual((result["status"], result["integrity_status"]), ("IN_PROGRESS", "PASS"))
        self.assertEqual(result["completion_status"], "INCOMPLETE")
        self.assertEqual(result["counts"]["source_incomplete_profiles"], 1)
        self.assertEqual(result["verification_failure_count"], 0)
        self.assertEqual([item["profile_uuid"] for item in result["source_incomplete_profiles"]], ["declared"])

        self.assertEqual(self.run_repair("--requeue-source-incomplete"), 0)
        self.assertEqual([row["profile_uuid"] for row in repair.read_ndjson(self.profiles)],
                         ["good", "unavailable"])
        quarantine = repair.read_ndjson(self.quarantine)
        self.assertEqual([item["reason"] for item in quarantine], ["SOURCE_INCOMPLETE_BROWSER_REQUEUE"])
        self.assertEqual([item["row"] for item in quarantine], [declared])
        state = json.loads(self.state.read_text(encoding="utf-8"))
        self.assertEqual((state["total_succeeded"], state["remaining"], state["total_failed"]), (2, 1, 0))
        self.assertEqual(state["attempted_this_session"], 0)
        self.assertEqual(state["max_requests_per_minute"], 40)
        self.assertEqual(state["queue_total"], 3)
        receipt = json.loads(self.receipt.read_text(encoding="utf-8"))
        self.assertIn("Re-crawl the 18 through the browser path first", receipt["ruling"])
        self.assertEqual(receipt["counts"]["source_incomplete_rows_quarantined_for_requeue"], 1)
        self.assertEqual(receipt["counts"]["state_remaining_after"], 1)
        self.assertEqual(receipt["counts"]["rows_after"], 2)
        self.assertEqual(receipt["policy"]["quarantine_reason"], "SOURCE_INCOMPLETE_BROWSER_REQUEUE")
        self.assertTrue(receipt["invariants"]["removed_ids_exactly_equal_verifier_source_incomplete_ids"])
        self.assertTrue(receipt["invariants"]["no_unavailable_404_row_touched"])

    def test_undeclared_missing_row_still_aborts(self):
        undeclared = self.profile("undeclared")
        undeclared["employment_history"] = []
        declared = self.seed_source_incomplete(undeclared)
        _, result = self.run_verifier()
        self.assertEqual([item["profile_uuid"] for item in
                          result["verification_failures"]["incomplete_profile_content"]], ["undeclared"])
        # Even handed a receipt that claims the checkpoint is clean, the tool must
        # refuse while a row lacks a collection without the source declaration.
        failures = dict(result["verification_failures"], incomplete_profile_content=[])
        self.patch_verification(status="IN_PROGRESS", integrity_status="PASS",
                                verification_failures=failures)
        self.assertEqual([item["profile_uuid"] for item in
                          json.loads(self.verification.read_text(encoding="utf-8"))["source_incomplete_profiles"]],
                         [declared["profile_uuid"]])
        self.assert_no_mutation_on_error("without a SOURCE_CONFIRMED_MISSING_FIELDS declaration",
                                         "--requeue-source-incomplete")

    def test_receipt_targets_must_equal_the_declared_rows(self):
        self.seed_source_incomplete()
        _, result = self.run_verifier()
        targets = copy.deepcopy(result["source_incomplete_profiles"])
        targets[0]["profile_uuid"] = "not-present"
        self.patch_verification(source_incomplete_profiles=targets)
        self.assert_no_mutation_on_error("source-incomplete targets do not exactly match",
                                         "--requeue-source-incomplete")

    def test_empty_receipt_target_list_is_rejected(self):
        self.seed_source_incomplete()
        self.run_verifier()
        self.patch_verification(source_incomplete_profiles=[])
        self.assert_no_mutation_on_error("no source-incomplete repair targets",
                                         "--requeue-source-incomplete")

    def test_integrity_fail_receipt_is_rejected_for_the_new_flag(self):
        # setUp's fixture: a row missing employment history with no declaration.
        _, result = self.run_verifier()
        self.assertEqual(result["integrity_status"], "FAIL")
        self.assert_no_mutation_on_error("requires an integrity PASS IN_PROGRESS checkpoint",
                                         "--requeue-source-incomplete")

    def test_any_verifier_failure_blocks_the_new_flag(self):
        self.seed_source_incomplete()
        _, result = self.run_verifier()
        failures = dict(result["verification_failures"],
                        source_url_mismatches=[{"profile_uuid": "good"}])
        self.patch_verification(verification_failures=failures)
        self.assert_no_mutation_on_error("requires zero verifier failures",
                                         "--requeue-source-incomplete")

    def test_stale_profiles_are_rejected_for_the_new_flag(self):
        self.seed_source_incomplete()
        self.run_verifier()
        self.profiles.write_text(self.profiles.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.assert_no_mutation_on_error("stale or unbound verifier profiles",
                                         "--requeue-source-incomplete")

    def test_new_flag_is_mutually_exclusive_with_the_404_requeue(self):
        self.seed_source_incomplete()
        self.run_verifier()
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.run_repair("--requeue-source-incomplete", "--requeue-all-unavailable-404")
        self.assertFalse(self.quarantine.exists())
        self.assertFalse(self.receipt.exists())


if __name__ == "__main__":
    unittest.main()
