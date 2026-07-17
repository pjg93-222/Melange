# -*- coding: utf-8 -*-
"""Regression tests for the independent 2026-07-14 bug report.

These tests intentionally exercise contracts that the historical kernel/full-audit suites did
not cover.  They are kept dependency-light so rebuildability can be checked with a clean Python
runtime as well as the workstation environment.
"""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


FEC = Path(__file__).resolve().parents[1]
ROOT = FEC.parent
DATA_ROOT = Path(os.environ.get("MONEYBALL_ROOT", ROOT))
sys.path.insert(0, str(FEC))


def source(name: str) -> str:
    return (FEC / name).read_text(encoding="utf-8-sig")


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, FEC / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_function(filename: str, function_name: str, namespace=None):
    tree = ast.parse(source(filename), filename=filename)
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function_name)
    ns = dict(namespace or {})
    exec(compile(ast.Module(body=[fn], type_ignores=[]), filename, "exec"), ns)
    return ns[function_name]


class PipelineContracts(unittest.TestCase):
    def test_unknown_resume_target_is_a_hard_failure(self):
        run = subprocess.run(
            [sys.executable, str(FEC / "run_pipeline.py"), "--from", "definitely_not_a_step"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=20,
        )
        self.assertNotEqual(0, run.returncode, run.stdout + run.stderr)
        self.assertIn("unknown --from target", (run.stdout + run.stderr).lower())

    def test_pipeline_has_an_exclusive_run_lock(self):
        text = source("run_pipeline.py")
        self.assertIn("pipeline_run_lock", text)
        self.assertIn("finally", text)

    def test_weekly_refresh_never_publishes_from_a_skipped_rank_rebuild(self):
        text = source("weekly_refresh.py")
        self.assertNotIn("DASHBOARD FALLBACK", text)
        self.assertNotIn("--from','per_topic_flip", text)
        self.assertIn("hard=True", text)

    def test_weekly_timeout_terminates_the_whole_process_tree(self):
        text = source("weekly_refresh.py")
        self.assertIn("taskkill", text)
        self.assertIn("CREATE_NEW_PROCESS_GROUP", text)

    def test_canonical_runtime_dependencies_are_declared_and_preflighted(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        for package in ("networkx", "numpy", "openpyxl", "pandas", "scikit-learn", "scipy"):
            self.assertIn(package, requirements)
        runner = source("run_pipeline.py")
        self.assertIn("preflight_dependencies", runner)
        self.assertIn("pip install -r requirements.txt", runner)


class MathAndSelectionContracts(unittest.TestCase):
    def test_unratified_formal_office_context_cannot_move_rank_authority(self):
        producer = source("compute_pillars.py")
        self.assertIn("E=dict(Ebase)", producer.replace(" ", ""))
        self.assertNotIn("Ebase[m])+ROLE_BONUS[m]", producer.replace(" ", ""))
        self.assertIn("formal_role_display_weight", producer)
        self.assertIn("formal_role_influence_bonus", producer)
        self.assertIn("display-only", producer.lower())

    def test_media_domain_normalization_preserves_signed_relative_magnitude(self):
        import media_rules

        normalized = media_rules.normalize_signed_extrema(
            {"high_pro": 8.0, "low_pro": 2.0, "high_anti": -10.0, "low_anti": -2.5, "zero": 0.0}
        )
        self.assertEqual(
            {"high_pro": 1.0, "low_pro": 0.25, "high_anti": -1.0, "low_anti": -0.25, "zero": 0.0},
            normalized,
        )

    def test_general_media_is_audited_without_inventing_policy_specificity(self):
        import media_rules

        ledger = media_rules.general_exclusion_ledger({"A": 0.8, "B": 0.0, "C": -0.4})
        self.assertEqual({"A", "C"}, set(ledger))
        self.assertTrue(all(row["applied_to_policy_domains"] is False for row in ledger.values()))
        core = source("moneyball_core.py")
        self.assertIn("normalize_signed_extrema", core)
        self.assertIn("general_exclusion_ledger", core)
        self.assertNotIn("disperse_general", core)

    def test_priming_charges_recruit_rate_times_recruited_influence(self):
        tree = ast.parse(source("lt_priming.py"), filename="lt_priming.py")
        prime = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "prime")
        body = ast.unparse(prime).replace(" ", "")
        self.assertIn("cost+=c*add", body)
        self.assertNotIn("cost+=c;", body)

    def test_network_selector_prefers_augmented_network_over_newer_base(self):
        import moneyball_core as core

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "congress_cosponsor_network_119_20260714.xlsx"
            aug = Path(tmp) / "congress_cosponsor_network_AUG_20260713.xlsx"
            base.write_bytes(b"base")
            aug.write_bytes(b"aug")
            os.utime(base, (200, 200))
            os.utime(aug, (100, 100))
            self.assertEqual(aug, Path(core.select_network_file([str(base), str(aug)])))


class ValidationContracts(unittest.TestCase):
    def test_audio_duration_floor_matches_two_minimum_clips(self):
        import audio_rules

        self.assertEqual(30.0, audio_rules.MIN_CLIP_TARGET_SEC)
        self.assertEqual(2, audio_rules.MIN_INDEPENDENT_PROGRAMS)
        self.assertEqual(
            audio_rules.MIN_CLIP_TARGET_SEC * audio_rules.MIN_INDEPENDENT_PROGRAMS,
            audio_rules.MIN_MEMBER_TARGET_SEC,
        )
        self.assertEqual(60.0, audio_rules.MIN_MEMBER_TARGET_SEC)
        self.assertEqual(5, audio_rules.MIN_MEMBER_SPEECH_UNITS)
        self.assertEqual(2, audio_rules.MIN_MEMBER_DISTINCT_TOPICS)
        for filename in (
            "b5_audio_descriptors_candidate.py",
            "b5_audio_build.py",
            "b5_audio_fetch.py",
            "b5_audio_verify.py",
        ):
            self.assertIn("audio_rules", source(filename), filename)

    def test_active_audio_contract_uses_the_same_duration_floor(self):
        import audio_rules

        artifact = json.loads((DATA_ROOT / "b5_audio_descriptors_v2.json").read_text(encoding="utf-8"))
        reviews = json.loads((DATA_ROOT / "b5_audio_reviews_v2.json").read_text(encoding="utf-8"))
        self.assertEqual(
            audio_rules.MIN_MEMBER_TARGET_SEC,
            artifact["measurement_contract"]["minimum_target_seconds_per_member"],
        )
        self.assertEqual(
            audio_rules.MIN_MEMBER_TARGET_SEC,
            reviews["contract"]["minimum_confirmed_target_seconds_per_member"],
        )
        self.assertEqual(
            audio_rules.MIN_MEMBER_SPEECH_UNITS,
            artifact["measurement_contract"]["minimum_speech_units_per_member"],
        )
        self.assertEqual(
            audio_rules.MIN_MEMBER_DISTINCT_TOPICS,
            reviews["contract"]["minimum_distinct_topics_per_member"],
        )
        self.assertIn("pitch_deviation_from_speaker_baseline_z", artifact["measurement_contract"])
        self.assertEqual(
            hashlib.sha256((DATA_ROOT / "b5_audio_reviews_v2.json").read_bytes()).hexdigest(),
            artifact["review_sha256"],
        )
        self.assertIn("--active", source("b5_audio_descriptors_candidate.py"))

    def test_external_gold_e_is_equal_weight_and_discriminant(self):
        artifact = json.loads((DATA_ROOT / "big5_e_gold_anchored.json").read_text(encoding="utf-8"))
        validation = json.loads((DATA_ROOT / "big5_external_gold_validation.json").read_text(encoding="utf-8"))
        self.assertEqual("ACTIVE_EXTERNAL_GOLD_ANCHORED", artifact["status"])
        self.assertGreaterEqual(len(artifact["members"]), 450)
        for row in validation["panel_results"].values():
            self.assertGreaterEqual(row["e_r"], .30)
            self.assertTrue(row["diagonal_dominant"])
            self.assertLess(row["e_permutation_p_one_sided"], .05)
        sample = next(iter(artifact["members"].values()))
        self.assertEqual({"blue_visibility": .5, "pink_observer": .5}, sample["channel_weights"])

    def test_staff_directory_rejects_missing_titles(self):
        validate_staff_rows = load_function("build_staff_directory.py", "validate_staff_rows")
        with self.assertRaisesRegex(ValueError, "no staff rows"):
            validate_staff_rows({})
        with self.assertRaisesRegex(ValueError, "missing title"):
            validate_staff_rows({"Q-1": {"n": "A Staffer", "t": "", "m": "Example Member"}})
        validate_staff_rows({"Q-1": {"n": "A Staffer", "t": "Legislative Director", "m": "Example Member"}})
        directory = json.loads((DATA_ROOT / "staff_directory.json").read_text(encoding="utf-8"))
        self.assertFalse(
            [(member, row.get("n")) for member, rows in directory.items()
             for row in rows if not str(row.get("t") or "").strip()]
        )

    def test_communication_style_requires_every_facet(self):
        module = load_module("validate_communication_style_test", "validate_communication_style.py")
        artifact = {
            "schema": "communication-style-v1",
            "status": "ACTIVE_DISPLAY_ONLY",
            "members": {
                "Example Member": {
                    "scope": {}, "raw_text": {}, "facets": {"warmth": {"percentile": 0.5}},
                    "public_exposure": None, "extraversion_status": "unknown",
                }
            },
        }
        errors = module.validate(artifact, ["Example Member"], {"members": {}}, verify_hashes=False)
        self.assertTrue(any("missing required facets" in error for error in errors), errors)

    def test_recorded_input_hashes_are_enforced(self):
        module = load_module("validate_communication_style_hash_test", "validate_communication_style.py")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "input.json"
            p.write_text("current", encoding="utf-8")
            artifact = {"inputs_sha256": {"input.json": hashlib.sha256(b"stale").hexdigest()}}
            errors = module.validate_input_hashes(artifact, Path(tmp))
            self.assertTrue(any("input hash mismatch" in error for error in errors), errors)

    def test_guarded_profile_validator_enforces_recorded_hashes(self):
        text = source("validate_guarded_profile_artifacts.py")
        self.assertIn("validate_input_hashes", text)
        self.assertIn("review_sha256", text)

    def test_ratified_receptivity_slots_do_not_silently_revert(self):
        text = source("receptivity_layer.py")
        self.assertNotIn("reverting RECEPT_N", text)
        self.assertNotIn("reverting to RECEPT_COOP", text)
        self.assertIn("required ratified", text)

    def test_affective_n_builder_has_rebuildable_input_path_and_atomic_output(self):
        text = source("emit_affective_n.py")
        self.assertIn("AFFECTIVE_N_INPUT", text)
        self.assertNotIn("claude-worktrees", text)
        self.assertIn("dump_atomic", text)

    def test_malformed_vote_evidence_cannot_be_treated_as_no_evidence(self):
        import moneyball_core as core

        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "vote_category_lean.json"
            bad.write_text('{"name_of": {}}', encoding="utf-8")
            core._VOTECORR = None
            with mock.patch.object(core, "p", return_value=str(bad)):
                with self.assertRaises(RuntimeError):
                    core.vote_corroboration()

    def test_malformed_delivery_evidence_cannot_be_treated_as_neutral(self):
        import moneyball_core as core

        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "say_do_gap.json"
            bad.write_text('{"wrong_key": {}}', encoding="utf-8")
            core._DELIV = None
            with mock.patch.object(core, "p", return_value=str(bad)):
                with self.assertRaises(RuntimeError):
                    core.delivery_mult("Example Member")


class IngestionContracts(unittest.TestCase):
    def test_float_coerced_manual_directions_remain_valid(self):
        import math
        pd=types.SimpleNamespace(isna=lambda value:isinstance(value,float) and math.isnan(value))
        parse_direction = load_function("build_archive_legislative.py", "parse_direction", {"pd":pd})
        self.assertEqual(1, parse_direction(1.0))
        self.assertEqual(-1, parse_direction(-1.0))
        self.assertIsNone(parse_direction(float("nan")))

    def test_congress_changes_on_january_third_not_january_first(self):
        text = source("fetch_congressional_record.py")
        tree = ast.parse(text, filename="fetch_congressional_record.py")
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "congress_for_date")
        import datetime
        ns = {"datetime":datetime}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "fetch_congressional_record.py", "exec"), ns)
        self.assertEqual(116, ns["congress_for_date"]("2021-01-01"))
        self.assertEqual(116, ns["congress_for_date"]("2021-01-02"))
        self.assertEqual(117, ns["congress_for_date"]("2021-01-03"))

    def test_collector_never_decodes_scoring_text_with_replacement(self):
        text = source("fetch_congressional_record.py")
        self.assertNotIn("decode('utf-8','replace')", text.replace('"', "'"))

    def test_govinfo_key_is_sent_in_a_header_not_the_url(self):
        # EVERY govinfo collector must send the key in the X-Api-Key HEADER, never the URL query string
        # (secret-hygiene: URL query leaks into logs/proxies). 2026-07-15: extended to the hearings collectors.
        for fn in ("fetch_congressional_record.py", "fetch_hearings_antag.py", "fetch_hearings_seq.py"):
            text = source(fn)
            self.assertIn("X-Api-Key", text, fn)
            self.assertNotIn("api_key=%s", text, fn)
            self.assertNotIn("&api_key=", text, fn)

    def test_empty_social_cells_never_become_literal_nan_tokens(self):
        import math
        clean_social_text = load_function("big5_traits.py", "clean_social_text", {"math":math})
        self.assertIsNone(clean_social_text(float("nan")))
        self.assertIsNone(clean_social_text("nan"))
        self.assertEqual("real text", clean_social_text(" real text "))

    def test_electoral_history_uses_atomic_json_write(self):
        text = source("build_electoral_history.py")
        self.assertIn("dump_atomic", text)
        self.assertNotIn("json.dump(out", text)


class DisplayContracts(unittest.TestCase):
    def test_embedded_json_cannot_close_its_script_element(self):
        import moneyball_core as core

        payload = core.json_for_script({"title": "x</script><script>alert(1)</script>"})
        self.assertNotIn("</script", payload.lower())
        self.assertEqual(
            {"title": "x</script><script>alert(1)</script>"},
            json.loads(payload),
        )

    def test_dashboard_uses_ratified_monte_carlo_and_cascade_cap(self):
        bundle = source("build_dashboard_bundle.py")
        template = source("templates/make_dashboard_html_00.tpl")
        self.assertIn("'MC':20", bundle.replace(" ", ""))
        self.assertNotIn("Math.min(0.95", template)
        self.assertIn("Math.min(0.9", template)

    def test_cfpb_display_has_one_layer_without_double_weighting_the_aggregate(self):
        contract = load_function(
            "build_dashboard_bundle.py",
            "dashboard_issue_contract",
            {
                "LBLCAT": {"CFPB Restrain": "CFPB", "CFPB Reach (-)": "CFPB"},
                "DISPLAY_LABEL": {
                    "CFPB Restrain": "CFPB Restrain (pro-CU; limits agency reach)"
                },
                "DROPPED_DISPLAY_CLONES": {"CFPB Reach (-)"},
            },
        )
        source_issues, labels, categories = contract(
            ["Interchange", "CFPB Restrain", "CFPB Reach (-)"]
        )
        self.assertEqual(["Interchange", "CFPB Restrain"], source_issues)
        self.assertEqual(1, sum("CFPB" in label for label in labels))
        self.assertEqual(["Interchange", "CFPB"], categories)
        producer = source("build_dashboard_bundle.py")
        self.assertIn("for lb in source_issues", producer)

    def test_big_five_missing_axes_are_not_drawn_as_median_measurements(self):
        template = source("templates/make_member_desk_00.tpl")
        self.assertNotIn("P.big5_pct.map(_ns)", template)
        self.assertIn("Big Five axes unavailable", template)

    def test_dashboard_semantic_hash_ignores_only_volatile_freshness(self):
        producer = source("dashboard_integrity.py")
        self.assertIn("k not in ('integrity','freshness')", producer)
        self.assertIn("big5_gold_anchored.json", producer)

    def test_biography_links_protect_opener(self):
        template = source("templates/make_member_desk_00.tpl")
        for line in template.splitlines():
            if "target=_blank" in line:
                self.assertIn("rel=noopener", line, line)

    def test_inputs_have_accessible_names(self):
        for template in (source("templates/make_member_desk_00.tpl"), source("templates/make_dashboard_html_00.tpl")):
            for line in template.splitlines():
                if "<input" in line and "type=hidden" not in line and " hidden" not in line:
                    self.assertTrue("aria-label=" in line or "aria-labelledby=" in line, line)

    def test_media_headlines_are_bounded_in_the_ui(self):
        template = source("templates/make_member_desk_00.tpl")
        self.assertIn("clipTitle(", template)

    def test_product_surfaces_exclusion_accounting_and_freshness(self):
        template = source("templates/make_member_desk_00.tpl")
        self.assertIn("Exclusion accounting", template)
        self.assertIn("Data freshness", template)

    def test_cu_frame_is_explicit_where_stances_are_shown(self):
        template = source("templates/make_member_desk_00.tpl")
        self.assertIn("CU advocacy frame", template)
        self.assertIn("restrain CFPB reach", template)

    def test_model_dials_and_display_only_tiers_are_labeled_at_the_result(self):
        dashboard = source("templates/make_dashboard_html_00.tpl")
        desk = source("templates/make_member_desk_00.tpl")
        self.assertIn("Modeled chain holds", dashboard)
        self.assertIn("not an empirical probability", dashboard)
        self.assertIn("overall rank may differ", desk)

    def test_rank_audit_compares_the_shipped_adjusted_authority(self):
        text = source("compute_pillars.py")
        self.assertIn("SHIPPED AUTHORITY PARITY", text)
        self.assertIn("effective_weight_diagnostics", text)

    def test_offtopic_exclusions_have_per_member_counts(self):
        producer = source("make_member_desk.py")
        template = source("templates/make_member_desk_00.tpl")
        self.assertIn("social_exclusions_by_member", producer)
        self.assertIn("filtered social items", template)

    def test_big_five_axis_uses_canonical_extraversion_spelling_everywhere(self):
        self.assertNotIn("Extroversion", source("templates/make_member_desk_00.tpl"))
        self.assertNotIn("Extroversion", source("audit_full.py"))


class PersonalTextureContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module("personal_texture_contract_test", "personal_texture_layer.py")

    def test_attributed_third_party_first_person_quote_is_rejected(self):
        row = {
            "member": "Kevin Kiley",
            "evidence": 'Constituent Jodie told the committee, "We traveled to 10 countries and love visiting Paris."',
            "hints": ["places_travel"],
        }
        result = self.module.local_explicit(row)
        self.assertFalse(result["keep"], result)

    def test_memorial_companion_story_is_not_member_biography(self):
        row = {
            "member": "Michael Baumgartner",
            "evidence": ("Mike and I spoke often. Together, we traveled the world, visiting over 10 countries. "
                         "Unfortunately, he was taken from us too soon when he passed."),
            "hints": ["places_travel"],
        }
        self.assertFalse(self.module.local_explicit(row)["keep"])

    def test_somebody_elses_favorite_quote_is_not_member_biography(self):
        row = {
            "member": "Mark DeSaulnier",
            "evidence": "Our Speaker has a favorite quote where she says public opinion means everything.",
            "hints": ["favorite", "quotes_values"],
        }
        self.assertFalse(self.module.local_explicit(row)["keep"])

    def test_near_duplicate_claims_share_a_fingerprint(self):
        a = "My family and I traveled to ten countries during those years."
        b = "During those years, my family and I travelled to 10 countries!"
        self.assertEqual(self.module.claim_fingerprint(a), self.module.claim_fingerprint(b))

    def test_local_fallback_details_cannot_enter_narrative_prompts(self):
        text = source("b5_narratives.py")
        self.assertIn("narrative_eligible", text)


class DocumentationContracts(unittest.TestCase):
    def test_current_runbook_names_the_real_harnesses_and_runtime(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8-sig")
        self.assertIn("64 kernel", readme)
        self.assertIn("97 full-audit", readme)
        self.assertIn("pip install -r requirements.txt", readme)
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8-sig")
        self.assertIn("!requirements*.txt", gitignore)

    def test_paid_narrative_header_names_the_configured_primary_model(self):
        text = source("b5_narratives.py")
        self.assertNotIn("FABLE write", text)
        self.assertIn("claude-sonnet-5", text)

    def test_historical_architecture_review_is_not_presented_as_current_state(self):
        review = (ROOT / "ARCHITECTURE_REVIEW_2026-07-02.md").read_text(encoding="utf-8-sig")
        self.assertIn("Historical snapshot", review[:500])

    def test_audio_runbook_distinguishes_legacy_corpus_from_strict_gate(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8-sig")
        for fact in ("2,192", "1,761", "435", "strict profile gate accepts 0"):
            self.assertIn(fact, readme)


if __name__ == "__main__":
    unittest.main(verbosity=2)
