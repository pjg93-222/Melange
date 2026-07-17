# -*- coding: utf-8 -*-
"""Regression contracts for the completed 2026-07-16 Moneyball audit.

These tests are intentionally cheap: they exercise pure kernel behavior and source-level
integration contracts without importing the run-on-import production engines.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


FEC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FEC))


def source(name: str) -> str:
    return (FEC / name).read_text(encoding="utf-8-sig")


def data_root() -> Path:
    """Resolve the live data root the same way in and outside a linked worktree."""
    root = Path(os.environ.get("MONEYBALL_ROOT", FEC.parent))
    if not (root / "category_stance.json").exists():
        root = FEC.parents[3]
    return root


class OverallCrownContracts(unittest.TestCase):
    def test_tier_one_is_sufficient_for_champion(self):
        import moneyball_core as core

        matrix = {"x%d" % i: "Persuadable" for i in range(8)}
        cap = {"Someone": {"raw": "Champion", "final": "Ally"}}
        base = core.overall_tier(matrix)
        self.assertNotEqual("Champion", base)
        self.assertEqual("Champion", core.overall_display_tier(matrix, 1, "Someone", cap))
        self.assertEqual(base, core.overall_display_tier(matrix, 2, "Someone", cap))
        self.assertEqual(base, core.overall_display_tier(matrix, 0, "Someone", cap))

    def test_ally_floor_includes_katie_britt_and_uses_prototype_hp_floor(self):
        import moneyball_core as core

        bands = dict((tier, cut) for cut, tier in core.OVERALL_BANDS)
        self.assertEqual(2.50, bands["Ally"])
        self.assertEqual(1.50, bands["Highly Persuadable"])
        self.assertNotIn("Champion", bands)
        self.assertEqual("Ally", core.overall_tier({"a": "Ally", "b": "Ally"}))

        root = data_root()
        matrix = json.loads((root / "category_stance.json").read_text(encoding="utf-8"))["matrix"]
        self.assertEqual("Ally", core.overall_tier(matrix["Katie Britt"]))

    def test_invalid_opponent_cutoff_is_rejected(self):
        import moneyball_core as core

        with self.assertRaises(ValueError):
            core.validate_overall_bands(((0.0, "Skeptic"), (-0.5, "Highly Skeptical")), -0.1)

    def test_overall_bands_are_nearest_rung_boundaries_below_ally(self):
        import moneyball_core as core

        bands = dict((tier, cut) for cut, tier in core.OVERALL_BANDS)
        self.assertEqual(
            {
                "Ally": 2.50,
                "Highly Persuadable": 1.50,
                "Persuadable": 0.75,
                "Lean Persuadable": 0.25,
                "True Neutral": -0.25,
                "Lean Skeptic": -0.75,
                "Skeptic": -1.50,
                "Highly Skeptical": -3.00,
            },
            bands,
        )
        self.assertEqual("True Neutral", core.overall_tier_from_value(0.0))
        self.assertNotIn(
            core.overall_tier_from_value(0.01),
            {"Lean Skeptic", "Skeptic", "Highly Skeptical", "Opponent"},
        )
        self.assertNotIn(
            core.overall_tier_from_value(-0.01),
            {"Highly Persuadable", "Persuadable", "Lean Persuadable", "Ally"},
        )


class TierMathContracts(unittest.TestCase):
    def test_user_ratified_tier_weights_are_80_legislation_20_press(self):
        import tier_util

        legislative, press = tier_util.load_tier_weights()
        self.assertAlmostEqual(0.80, legislative)
        self.assertAlmostEqual(0.20, press)
        self.assertAlmostEqual(1.0, legislative + press)

    def test_tier_score_uses_existing_pillar_scale_without_second_percentile_rank(self):
        import tier_util

        pcts = {
            "French Hill": {"leg": 0.90, "press": 0.80},
            "Daniel Meuser": {"leg": 0.998, "press": 0.414},
            "Young Kim": {"leg": 0.80, "press": 0.90},
        }
        scores = tier_util.legislative_press_scores(pcts, 0.30, 0.25)
        self.assertAlmostEqual(0.47, scores["French Hill"])
        self.assertAlmostEqual(0.4029, scores["Daniel Meuser"])
        self.assertAlmostEqual(0.465, scores["Young Kim"])
        self.assertGreater(scores["French Hill"], scores["Daniel Meuser"])

    def test_user_ratified_tier_placements_preserve_fixed_bucket_sizes(self):
        import tier_util

        root = data_root()
        roster = json.loads((root / "category_stance.json").read_text(encoding="utf-8"))["matrix"]
        tiers, _ = tier_util.legislative_press_tiers(list(roster), root=str(root))

        tier_one = {"Brian Fitzpatrick", "Roger Williams", "Bill Hagerty"}
        tier_two = {"Maxine Waters", "Juan Vargas", "Nydia Velázquez"}
        self.assertTrue(all(tiers.get(member) == 1 for member in tier_one))
        self.assertTrue(all(tiers.get(member) == 2 for member in tier_two))
        self.assertEqual(12, sum(value == 1 for value in tiers.values()))
        self.assertEqual(24, sum(value == 2 for value in tiers.values()))
        self.assertEqual(48, sum(value == 3 for value in tiers.values()))


class LegislativeRoutingContracts(unittest.TestCase):
    def test_known_cdfi_and_privacy_bills_have_one_effective_domain(self):
        import bill_rules as rules

        self.assertEqual(
            "CDFI Fund",
            rules.override_for({}, "H.R.7733", 117)["Category"],
        )
        self.assertEqual(
            "CDFI Fund",
            rules.override_for({}, "S.869", 118)["Category"],
        )
        for bill, congress in (("H.R.7036", 118), ("H.R.7022", 117), ("S.4698", 117)):
            self.assertEqual(
                "Data Privacy & Cyber",
                rules.override_for({}, bill, congress)["Category"],
            )

    def test_user_bill_override_wins_over_builtin_and_role_dedup_prefers_highest_role(self):
        import bill_rules as rules

        user = {
            (rules.bill_key("H.R.7733"), "117"): {
                "Bill": "H.R.7733",
                "Congress": "117",
                "Category": "Payments",
                "Include": "1",
            }
        }
        self.assertEqual(
            "Payments",
            rules.override_for(user, "H.R.7733", 117)["Category"],
        )
        self.assertEqual("original-cosponsor", rules.preferred_role(("cosponsor", "original-cosponsor")))
        self.assertEqual("sponsor", rules.preferred_role(("cosponsor", "sponsor", "original-cosponsor")))
        self.assertEqual(2.0, rules.role_weight(rules.preferred_role(("cosponsor", "original-cosponsor"))))


class MediaRoutingContracts(unittest.TestCase):
    def test_press_target_beats_bad_declared_tags(self):
        import media_rules as rules

        decision = rules.press_routing_decision(
            target="Bean Social Security simplification bill",
            title="Bean Bill to Simplify Social Security Moves Forward",
            declared=("Technology & Emerging Issues",),
            body="This release concerns Social Security retirement ages.",
        )
        self.assertEqual([], decision["categories"])
        self.assertEqual("no-policy-domain", decision["basis"])

    def test_press_routes_specific_target_and_keeps_residual_general_explicit(self):
        import media_rules as rules

        late_fee = rules.press_routing_decision(
            target="Barr CRA to nullify the CFPB credit card late fee rule",
            title="House, Senate resolutions would void CFPB credit card late fees rule",
            declared=("General Credit Union",),
        )
        self.assertEqual(
            ["CFPB Issues & Structural Reform", "Credit Card & Consumer-Fee Mandates"],
            late_fee["categories"],
        )
        general = rules.press_routing_decision(
            target="League contribution to NAF for credit union priorities",
            title="League advances credit union priorities",
            declared=("General Credit Union",),
        )
        self.assertEqual(["General Credit Union"], general["categories"])
        self.assertEqual("target", general["basis"])

    def test_social_context_guards_block_road_and_non_cu_tax_false_positives(self):
        import media_rules as rules

        self.assertNotIn(
            "Interchange",
            rules.route_raw_categories("Ribbon cutting opens a new highway interchange and exit ramp"),
        )
        self.assertNotIn(
            "Credit Union Tax Status",
            rules.route_raw_categories("The PGA Foundation is a tax-exempt nonprofit organization"),
        )
        self.assertNotIn(
            "CU-Bank Competitive Dynamics",
            rules.route_raw_categories("Visited a local community bank to discuss agriculture"),
        )

    def test_full_audit_persists_own_source_channel_integrity_guards(self):
        src = (FEC / "audit_full.py").read_text(encoding="utf-8-sig")
        for token in ("own_source_channels", "own-source channel sidecars preserve source row identity",
                      "validated own-source press channels are enabled and loaded",
                      "hearing channel remains gold-only", "Bluesky remains single-counted"):
            self.assertIn(token, src)


class BarrOverrideContracts(unittest.TestCase):
    def test_barr_late_fee_efforts_are_explicit_support_gold(self):
        tweet_overrides = json.loads(
            (FEC.parent / "tweet_stance_overrides.json").read_text(encoding="utf-8")
        )["corrections"]
        tweet_gold = {
            row["quorum_id"]: row["stance"]
            for row in tweet_overrides
        }
        for quorum_id in ("511658226", "511657485", "498264314", "458365083"):
            self.assertEqual("support", tweet_gold.get(quorum_id))

        press_overrides = json.loads(
            (FEC.parent / "press_stance_overrides.json").read_text(encoding="utf-8")
        )["corrections"]
        match = next(
            row
            for row in press_overrides
            if "House, Senate resolutions would void CFPB credit card late fees rule"
            in row.get("title_contains", "")
        )
        self.assertEqual("support", match["stance"])

    def test_worktree_gold_overlays_live_data_without_dropping_live_only_rows(self):
        import config_overlay

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            live = base / "live"
            code = base / "code"
            live.mkdir()
            code.mkdir()
            (live / "gold.json").write_text(
                json.dumps({"corrections": [
                    {"quorum_id": "1", "stance": "neutral"},
                    {"quorum_id": "2", "stance": "support"},
                ]}),
                encoding="utf-8",
            )
            (code / "gold.json").write_text(
                json.dumps({"corrections": [
                    {"quorum_id": "1", "stance": "support"},
                ]}),
                encoding="utf-8",
            )
            rows = config_overlay.merged_rows(
                "gold.json",
                "corrections",
                ("quorum_id",),
                data_root=str(live),
                code_root=str(code),
            )
        self.assertEqual(
            {"1": "support", "2": "support"},
            {row["quorum_id"]: row["stance"] for row in rows},
        )


class FollowupSocialGoldContracts(unittest.TestCase):
    def test_britt_and_lummis_user_ratified_posts_are_support(self):
        rows = json.loads(
            (FEC.parent / "tweet_stance_overrides.json").read_text(encoding="utf-8")
        )["corrections"]
        gold = {str(row.get("quorum_id")): row.get("stance") for row in rows}
        support_ids = {
            "559107834", "559097784",  # Britt: anti-debanking, Facebook/X cross-post
            "552715581", "552700010",  # Britt: opposition to CFPB credit-reporting overreach
            "545211528",               # Britt: CFPB accountability column
            "433093684",               # Britt: LSCU visit and opposition to harmful IRS action
            "591392565", "591305285",  # Lummis: open banking / anti-big-bank obstruction
            "539036369",               # Lummis: CBDC violates Fourth Amendment
            "536549427", "536545303",  # Lummis: anti-CBDC / pro-digital-assets cross-posts
            "445704177",               # Lummis: explicit opposition to U.S. CBDC
        }
        self.assertEqual(
            support_ids,
            {quorum_id for quorum_id in support_ids if gold.get(quorum_id) == "support"},
        )


class ValenceRegistryContracts(unittest.TestCase):
    def test_cbdc_target_is_anti_cu_so_opposition_composes_to_support(self):
        registry = json.loads(
            (FEC.parent / "cu_valence_registry.json").read_text(encoding="utf-8")
        )["entries"]
        cbdc = next(row for row in registry if row.get("key") == "cbdc")
        self.assertEqual(-1, cbdc["valence"])
        tweet_stack = source("tweet_stance_stack.py")
        self.assertIn(
            "CO.merged_rows('cu_valence_registry.json','entries',('key',),data_root=B)",
            tweet_stack.replace("\n", ""),
        )

    def test_three_reader_unanimity_beats_meta_but_not_manual_gold(self):
        import stance_rules

        self.assertEqual(
            "support",
            stance_rules.enforce_reader_unanimity(
                "oppose", ("support", "support", "support")
            ),
        )
        self.assertEqual(
            "oppose",
            stance_rules.enforce_reader_unanimity(
                "oppose", ("support", "support", "neutral")
            ),
        )
        stack = source("tweet_stance_stack.py")
        self.assertLess(
            stack.index("enforce_reader_unanimity"),
            stack.index("_ov = tweet_override("),
        )


class TweetImageContracts(unittest.TestCase):
    def test_image_evidence_only_resolves_weak_text_and_conflicts_go_to_review(self):
        import tweet_image_evidence as image_evidence

        strong_text = image_evidence.fuse_stance(
            text_stance="support",
            text_tier="unanimous",
            image_stance="oppose",
            image_confidence=0.99,
        )
        self.assertEqual("support", strong_text["stance"])
        self.assertEqual("conflict-review", strong_text["image_disposition"])

        resolved = image_evidence.fuse_stance(
            text_stance="neutral",
            text_tier="review",
            image_stance="support",
            image_confidence=0.90,
        )
        self.assertEqual("support", resolved["stance"])
        self.assertEqual("image-resolved", resolved["image_disposition"])

        weak = image_evidence.fuse_stance(
            text_stance="unrelated",
            text_tier="review",
            image_stance="support",
            image_confidence=0.60,
        )
        self.assertEqual("unrelated", weak["stance"])
        self.assertEqual("low-confidence-review", weak["image_disposition"])

    def test_x_collector_requests_and_persists_attachment_metadata(self):
        collector = source("tweet_collector.py")
        self.assertIn("attachments", collector)
        self.assertIn("attachments.media_keys", collector)
        self.assertIn("media.fields", collector)
        self.assertIn("media_json", collector)

    def test_canonical_pipeline_refreshes_tweet_labels_before_media_blend(self):
        pipeline = source("run_pipeline.py")
        self.assertLess(
            pipeline.index("('tweet_stance_stack.py',['--score'])"),
            pipeline.index("('build_media_blend.py',[])"),
        )


class AllocationContracts(unittest.TestCase):
    def test_coalition_candidates_exclude_unconditional_ally_seeds(self):
        text = source("per_topic_coalition.py").replace(" ", "")
        self.assertIn("ifcampT[n]=='neu'", text)
        self.assertNotIn("orcs[n]=='Ally'", text)
        self.assertIn("joint=spread(funded)", text)

    def test_topic_flip_blocks_system_level_skeptics_and_never_overspends(self):
        text = source("per_topic_flip.py").replace(" ", "")
        self.assertIn("BLOCK_OVERALL", text)
        self.assertIn("OVT", text)
        self.assertIn("spent+INC<=BUDGET", text)

    def test_frontier_only_removes_contest_opponent_after_activation(self):
        text = source("budget_frontier.py").replace(" ", "")
        self.assertIn("activated=", text)
        self.assertIn("aa=anti-activated", text)
        self.assertIn("if-negeff<=1e-12:break", text)

    def test_scoped_frontier_and_optimizer_runs_cannot_clobber_production(self):
        frontier = source("budget_frontier.py")
        optimizer = source("optimize.py")
        self.assertIn("scoped_output_path", frontier)
        self.assertIn("scoped_output_path", optimizer)
        self.assertIn("'topic':ONLY", frontier.replace(" ", ""))
        self.assertIn("'topic':ONLY", optimizer.replace(" ", ""))
        self.assertIn("'knee_found':knee_found", frontier.replace(" ", ""))

    def test_optimizer_budget_and_certificate_are_honest(self):
        text = source("optimize.py").replace(" ", "")
        self.assertIn("spent+INC<=BUDGET", text)
        self.assertIn("selected_marginals", text)
        self.assertIn("conversion_reachable", text)
        self.assertIn("certificate_valid", text)
        self.assertIn("'mode':optimizer_mode", text)
        self.assertIn("'guarantee':guarantee", text)
        self.assertIn("'observations':observations", text)
        self.assertIn("defconcavity_violations()", text)
        self.assertIn("'kind':'exact_discrete_separable_concave'", text)
        self.assertIn("certified_gain_ratio=1.0ifcertificate_validelseNone", text)
        self.assertIn("opt_bound=curifcertificate_validelseNone", text)
        self.assertNotIn("ADAPTIVEOPTIMIZER", text)


class DashboardContracts(unittest.TestCase):
    def test_canvas_blank_click_and_touch_clear_selection_and_refit(self):
        template = source("templates/make_dashboard_html_00.tpl").replace(" ", "")
        self.assertIn("elsebackToTargets()", template)
        self.assertIn("functionbackToTargets(){", template)
        self.assertIn("fit();draw();", template)

    def test_head_to_head_uses_pressure_multiplier_in_math_and_inverse(self):
        template = source("templates/make_dashboard_html_00.tpl").replace(" ", "")
        self.assertIn("pm=PM?PM[sel]:1", template)
        self.assertIn("K.WM*pm*", template)
        self.assertIn("/(K.WM*pm)", template)

    def test_max_cascade_is_closed_network_edge_activation_not_a_flip_star(self):
        template = source("templates/make_dashboard_html_00.tpl")
        compact = template.replace(" ", "")
        self.assertIn("function pageRankScores(", template)
        self.assertIn("function closedCascadeRoute(", template)
        self.assertIn("closedCascadeRoute(sel,6,2)", compact)
        self.assertIn("outdeg", template)
        self.assertIn("pathProb", template)
        max_route = template.split("function maxCascadeRoute()", 1)[1].split("function flipRoute()", 1)[0]
        self.assertNotIn("directOnly:true", max_route)
        self.assertIn("plan.edges", max_route)
        self.assertIn("u,v", max_route)
        self.assertIn("BLOCKOV", template)


class CrossEngineContracts(unittest.TestCase):
    def test_full_audit_separates_worktree_code_root_from_live_data_root(self):
        audit = source("audit_full.py")
        self.assertIn("FE=os.path.dirname(os.path.abspath(__file__))", audit.replace(" ", ""))
        self.assertIn("DATA_FE=B+r'\\fec'", audit.replace(" ", ""))
        self.assertIn("open(DATA_FE+r'\\legislators.csv'", audit)
        self.assertNotIn("B=MB_ROOT; FE=B+r'\\fec'", audit)

    def test_full_audit_refuses_a_foreign_live_pipeline_writer(self):
        audit = source("audit_full.py")
        self.assertIn("def assert_no_foreign_pipeline_writer", audit)
        self.assertIn("refusing audit while a foreign Moneyball pipeline owns the artifact set", audit)
        self.assertIn("owner not in (os.getpid(),parent_pid)", audit)

    def test_full_audit_checks_dashboard_and_workbook_crown_parity(self):
        audit = source("audit_full.py")
        self.assertIn("dashboard overall labels exactly match shared crown law", audit)
        self.assertIn("workbook stance column exactly matches shared crown law", audit)
        self.assertIn("_ra_ws=_wb['Rank & Allocation']", audit)
        self.assertIn("_wb_display={_ra_ws.cell", audit)

    def test_salience_parameters_have_one_shared_implementation(self):
        core = source("moneyball_core.py")
        shock = source("salience_shock.py")
        bundle = source("build_dashboard_bundle.py")
        self.assertIn("def salience_issue_params", core)
        self.assertIn("MBC.salience_issue_params", shock)
        self.assertIn("salience_issue_params", bundle)

    def test_dashboard_and_compact_layout_use_kernel_network_authority(self):
        bundle = source("build_dashboard_bundle.py")
        layout = source("sna_layout.py")
        self.assertIn("select_network_file", bundle)
        self.assertIn("load_network", layout)
        self.assertIn("dump_atomic", layout)
        self.assertIn("sorted(", layout)


if __name__ == "__main__":
    unittest.main()
