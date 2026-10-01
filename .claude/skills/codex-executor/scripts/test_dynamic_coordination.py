"""Focused tests for the research-derived coordination extension."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from coordination_contract import CoordinationStateMachine, LaneState
from coordination_ledger import CoordinationLedger
from dynamic_coordination import (
    DynamicCoordinationError,
    Observation,
    Prediction,
    ReasonCode,
    ReconciliationResult,
    next_state,
    reconcile,
    replay_report,
)


def observation(
    *,
    identifier: str = "obs-1",
    sequence: int = 1,
    subject: str = "service.status",
    value: object = "ready",
    confidence: float = 1.0,
    evidence_class: str = "independent",
) -> dict[str, object]:
    return {
        "observation_id": identifier,
        "run_id": "run-1",
        "sequence": sequence,
        "observed_at": "2026-07-24T12:00:00Z",
        "source": "service",
        "kind": "response",
        "subject": subject,
        "value": value,
        "confidence": confidence,
        "evidence_class": evidence_class,
        "caused_by_action_id": "none",
        "retry_attempt_id": None,
        "content_sha256": None,
    }


def prediction(
    *,
    identifier: str = "pred-1",
    comparison: str = "equals",
    expected: object = "ready",
    tolerance: dict[str, object] | None = None,
    deadline: int = 2,
    allow_self_generated: bool = False,
    allow_bounded_drift_continue: bool = False,
) -> dict[str, object]:
    return {
        "prediction_id": identifier,
        "step_id": "step-1",
        "subject": "service.status",
        "expected": expected,
        "comparison": comparison,
        "tolerance": {} if tolerance is None else tolerance,
        "deadline_sequence": deadline,
        "allow_self_generated": allow_self_generated,
        "minimum_evidence_confidence": 0.5,
        "max_observation_age_seconds": None,
        "allow_bounded_drift_continue": allow_bounded_drift_continue,
    }


class ValidationTests(unittest.TestCase):
    def test_unknown_observation_key_fails_closed(self) -> None:
        value = observation()
        value["extra"] = True
        with self.assertRaises(DynamicCoordinationError):
            Observation.from_mapping(value)

    def test_null_causal_link_fails_closed(self) -> None:
        value = observation()
        value["caused_by_action_id"] = None
        with self.assertRaises(DynamicCoordinationError):
            Observation.from_mapping(value)

    def test_confidence_range_is_closed(self) -> None:
        value = observation(confidence=1.1)
        with self.assertRaises(DynamicCoordinationError):
            Observation.from_mapping(value)

    def test_unknown_tolerance_key_fails_closed(self) -> None:
        value = prediction(tolerance={"unexpected": 1})
        with self.assertRaises(DynamicCoordinationError):
            Prediction.from_mapping(value)

    def test_invalid_range_shape_fails_closed(self) -> None:
        value = prediction(
            comparison="range",
            tolerance={"match_min": 10, "match_max": 1},
        )
        with self.assertRaises(DynamicCoordinationError):
            Prediction.from_mapping(value)

    def test_dc01_expected_and_observation_value_presence_fail_closed(self) -> None:
        cases = (
            ("equals", {}),
            ("contains", {"mode": "substring"}),
            ("range", {"match_min": 1, "match_max": 2}),
        )
        for comparison, tolerance in cases:
            with self.subTest(comparison=comparison, expected="missing"):
                value = prediction(comparison=comparison, tolerance=tolerance)
                value.pop("expected")
                with self.assertRaises(DynamicCoordinationError):
                    Prediction.from_mapping(value)
            with self.subTest(comparison=comparison, expected=None):
                value = prediction(
                    comparison=comparison,
                    expected=None,
                    tolerance=tolerance,
                )
                with self.assertRaises(DynamicCoordinationError):
                    Prediction.from_mapping(value)

        for comparison, tolerance in cases:
            with self.subTest(comparison=comparison, observation_value="missing"):
                missing_value = observation()
                missing_value.pop("value")
                result = reconcile(
                    [
                        Prediction.from_mapping(
                            prediction(
                                comparison=comparison,
                                tolerance=tolerance,
                            )
                        )
                    ],
                    [Observation.from_mapping(missing_value)],
                    run_id="run-1",
                    cutoff_sequence=2,
                )
                self.assertEqual(
                    result.aggregate_result,
                    ReconciliationResult.UNKNOWN,
                )
                self.assertEqual(
                    result.prediction_results[0].reason_code,
                    ReasonCode.UNKNOWN_MALFORMED,
                )

    def test_dc03_contains_expected_shape_is_validated(self) -> None:
        for expected in ("", "   "):
            with self.subTest(mode="substring", expected=expected):
                with self.assertRaises(DynamicCoordinationError):
                    Prediction.from_mapping(
                        prediction(
                            comparison="contains",
                            expected=expected,
                            tolerance={"mode": "substring"},
                        )
                    )
        for expected in (None, [], {}):
            with self.subTest(mode="element", expected=expected):
                with self.assertRaises(DynamicCoordinationError):
                    Prediction.from_mapping(
                        prediction(
                            comparison="contains",
                            expected=expected,
                            tolerance={"mode": "element"},
                        )
                    )

    def test_dc10_causal_ids_are_validated_at_parse_and_reconcile(self) -> None:
        for caused_by in ("", " ", "bad id", "x" * 65):
            with self.subTest(caused_by=caused_by):
                value = observation()
                value["caused_by_action_id"] = caused_by
                with self.assertRaises(DynamicCoordinationError):
                    Observation.from_mapping(value)

        parsed = Observation.from_mapping(observation())
        invalid_direct = replace(parsed, caused_by_action_id="bad id")
        result = reconcile(
            [Prediction.from_mapping(prediction())],
            [invalid_direct],
            run_id="run-1",
            cutoff_sequence=2,
        )
        self.assertEqual(result.aggregate_result, ReconciliationResult.UNKNOWN)
        self.assertEqual(
            result.prediction_results[0].reason_code,
            ReasonCode.UNKNOWN_CAUSAL,
        )


class EvaluatorTests(unittest.TestCase):
    def evaluate(
        self,
        pred: dict[str, object],
        observations: list[dict[str, object]],
        **options: int,
    ):
        return reconcile(
            [Prediction.from_mapping(pred)],
            [Observation.from_mapping(item) for item in observations],
            run_id="run-1",
            cutoff_sequence=options.get("cutoff_sequence", 2),
            consecutive_divergences=options.get("consecutive_divergences", 0),
            rebase_after=options.get("rebase_after", 3),
        )

    def test_equals_match_and_divergence(self) -> None:
        match = self.evaluate(prediction(), [observation()])
        self.assertEqual(match.aggregate_result, ReconciliationResult.MATCH)
        divergence = self.evaluate(
            prediction(),
            [observation(value="not-ready")],
        )
        self.assertEqual(
            divergence.aggregate_result, ReconciliationResult.DIVERGENCE
        )

    def test_self_generated_evidence_is_unknown_by_default(self) -> None:
        result = self.evaluate(
            prediction(),
            [observation(evidence_class="self_generated")],
        )
        self.assertEqual(result.aggregate_result, ReconciliationResult.UNKNOWN)
        self.assertEqual(
            result.prediction_results[0].reason_code,
            ReasonCode.UNKNOWN_SELF_GENERATED,
        )

    def test_stale_evidence_is_unknown(self) -> None:
        pred = prediction()
        pred["max_observation_age_seconds"] = 60
        result = reconcile(
            [Prediction.from_mapping(pred)],
            [Observation.from_mapping(observation())],
            run_id="run-1",
            cutoff_sequence=2,
            evaluated_at=Observation.from_mapping(
                observation() | {"observed_at": "2026-07-24T12:02:00Z"}
            ).observed_at,
        )
        self.assertEqual(result.aggregate_result, ReconciliationResult.UNKNOWN)
        self.assertEqual(
            result.prediction_results[0].reason_code,
            ReasonCode.UNKNOWN_STALE,
        )

    def test_range_has_match_drift_and_divergence(self) -> None:
        pred = prediction(
            comparison="range",
            expected=15,
            tolerance={
                "match_min": 10,
                "match_max": 20,
                "drift_min": 8,
                "drift_max": 22,
            },
        )
        self.assertEqual(
            self.evaluate(pred, [observation(value=15)]).aggregate_result,
            ReconciliationResult.MATCH,
        )
        self.assertEqual(
            self.evaluate(pred, [observation(value=21)]).aggregate_result,
            ReconciliationResult.BOUNDED_DRIFT,
        )
        self.assertEqual(
            self.evaluate(pred, [observation(value=30)]).aggregate_result,
            ReconciliationResult.DIVERGENCE,
        )
        drift = self.evaluate(pred, [observation(value=21)])
        self.assertEqual(
            next_state(LaneState.RECONCILING, drift),
            LaneState.AWAITING_DECISION,
        )
        permitted = prediction(
            comparison="range",
            expected=15,
            tolerance=pred["tolerance"],
            allow_bounded_drift_continue=True,
        )
        self.assertEqual(
            next_state(
                LaneState.RECONCILING,
                self.evaluate(permitted, [observation(value=21)]),
            ),
            LaneState.EXECUTING,
        )

    def test_contains_modes(self) -> None:
        substring = prediction(
            comparison="contains",
            expected="ready",
            tolerance={"mode": "substring"},
        )
        self.assertEqual(
            self.evaluate(
                substring, [observation(value="service ready")]
            ).aggregate_result,
            ReconciliationResult.MATCH,
        )
        element = prediction(
            comparison="contains",
            expected="ready",
            tolerance={"mode": "element"},
        )
        self.assertEqual(
            self.evaluate(
                element, [observation(value=["ready", "stable"])]
            ).aggregate_result,
            ReconciliationResult.MATCH,
        )

    def test_exists_absent_are_nonterminal_before_deadline(self) -> None:
        exists = prediction(comparison="exists", expected=None, deadline=3)
        result = self.evaluate(
            exists, [observation()], cutoff_sequence=2
        )
        self.assertEqual(result.aggregate_result, ReconciliationResult.UNKNOWN)
        self.assertFalse(result.prediction_results[0].terminal)
        absent = prediction(comparison="absent", expected=None, deadline=3)
        result = self.evaluate(absent, [], cutoff_sequence=3)
        self.assertEqual(result.aggregate_result, ReconciliationResult.MATCH)

    def test_changed_and_unchanged_use_baseline(self) -> None:
        baseline = observation(identifier="obs-0", sequence=1, value="old")
        current = observation(identifier="obs-1", sequence=2, value="new")
        changed = prediction(
            comparison="changed",
            expected=None,
            tolerance={"baseline_observation_id": "obs-0"},
            deadline=2,
        )
        result = self.evaluate(changed, [baseline, current])
        self.assertEqual(result.aggregate_result, ReconciliationResult.MATCH)
        unchanged = prediction(
            comparison="unchanged",
            expected=None,
            tolerance={"baseline_observation_id": "obs-0"},
            deadline=2,
        )
        current_same_value = observation(
            identifier="obs-1",
            sequence=2,
            value="old",
        )
        result = self.evaluate(unchanged, [baseline, current_same_value])
        self.assertEqual(result.aggregate_result, ReconciliationResult.MATCH)

    def test_dc02_absent_requires_zero_subject_observations(self) -> None:
        absent = prediction(comparison="absent", expected=None, deadline=2)
        empty = self.evaluate(absent, [])
        self.assertEqual(empty.aggregate_result, ReconciliationResult.MATCH)

        eligible = self.evaluate(absent, [observation()])
        self.assertEqual(
            eligible.aggregate_result,
            ReconciliationResult.DIVERGENCE,
        )
        self.assertEqual(
            eligible.prediction_results[0].reason_code,
            ReasonCode.DIVERGE_ABSENT_VIOLATED,
        )

        excluded_cases = (
            (
                observation(evidence_class="self_generated"),
                ReasonCode.UNKNOWN_SELF_GENERATED,
            ),
            (
                observation(confidence=0.1),
                ReasonCode.UNKNOWN_LOW_CONFIDENCE,
            ),
            (
                observation(sequence=3),
                ReasonCode.UNKNOWN_CUTOFF,
            ),
        )
        for excluded, reason in excluded_cases:
            with self.subTest(reason=reason):
                result = self.evaluate(absent, [excluded])
                self.assertEqual(
                    result.aggregate_result,
                    ReconciliationResult.UNKNOWN,
                )
                self.assertEqual(result.prediction_results[0].reason_code, reason)

        cross_run = self.evaluate(
            absent,
            [observation() | {"run_id": "run-other"}],
        )
        self.assertEqual(
            cross_run.aggregate_result,
            ReconciliationResult.MATCH,
        )

        latest_excluded = self.evaluate(
            absent,
            [
                observation(sequence=1, confidence=0.1),
                observation(
                    identifier="obs-2",
                    sequence=2,
                    evidence_class="self_generated",
                ),
            ],
        )
        self.assertEqual(
            latest_excluded.prediction_results[0].reason_code,
            ReasonCode.UNKNOWN_SELF_GENERATED,
        )

        proven_violation = self.evaluate(
            absent,
            [
                observation(sequence=1),
                observation(
                    identifier="obs-2",
                    sequence=2,
                    evidence_class="self_generated",
                ),
            ],
        )
        self.assertEqual(
            proven_violation.aggregate_result,
            ReconciliationResult.DIVERGENCE,
        )

    def test_dc04_bool_number_equality_is_divergence(self) -> None:
        cases = (
            (prediction(expected=True), observation(value=1)),
            (prediction(expected=1), observation(value=True)),
            (
                prediction(
                    comparison="contains",
                    expected=True,
                    tolerance={"mode": "element"},
                ),
                observation(value=[1]),
            ),
            (
                prediction(
                    comparison="contains",
                    expected=1,
                    tolerance={"mode": "element"},
                ),
                observation(value=[True]),
            ),
            (
                prediction(expected=[True]),
                observation(value=[1]),
            ),
            (
                prediction(expected={"nested": {"flag": True}}),
                observation(value={"nested": {"flag": 1}}),
            ),
            (
                prediction(expected={True: "x"}),
                observation(value={1: "x"}),
            ),
        )
        for pred, observed in cases:
            with self.subTest(pred=pred, observed=observed):
                result = self.evaluate(pred, [observed])
                self.assertEqual(
                    result.aggregate_result,
                    ReconciliationResult.DIVERGENCE,
                )
                self.assertEqual(
                    result.prediction_results[0].reason_code,
                    ReasonCode.DIVERGE_VALUE,
                )

    def test_dc05_baseline_uses_primary_eligibility(self) -> None:
        changed = prediction(
            comparison="changed",
            expected=None,
            tolerance={"baseline_observation_id": "obs-0"},
            deadline=2,
        )
        ineligible_baseline = self.evaluate(
            changed,
            [
                observation(
                    identifier="obs-0",
                    sequence=1,
                    value="old",
                    confidence=0.1,
                ),
                observation(identifier="obs-1", sequence=2, value="new"),
            ],
        )
        self.assertEqual(
            ineligible_baseline.aggregate_result,
            ReconciliationResult.UNKNOWN,
        )
        self.assertEqual(
            ineligible_baseline.prediction_results[0].reason_code,
            ReasonCode.UNKNOWN_BASELINE,
        )

        self_baseline = prediction(
            comparison="changed",
            expected=None,
            tolerance={"baseline_observation_id": "obs-1"},
            deadline=2,
        )
        self_reference = self.evaluate(
            self_baseline,
            [observation(identifier="obs-1", sequence=2, value="new")],
        )
        self.assertEqual(
            self_reference.aggregate_result,
            ReconciliationResult.UNKNOWN,
        )
        self.assertEqual(
            self_reference.prediction_results[0].reason_code,
            ReasonCode.UNKNOWN_BASELINE,
        )

    def test_dc06_negative_consecutive_divergences_is_rejected(self) -> None:
        with self.assertRaises(DynamicCoordinationError):
            self.evaluate(
                prediction(),
                [observation()],
                consecutive_divergences=-1,
            )

    def test_dc13_exists_filtered_has_distinct_reason(self) -> None:
        exists = prediction(comparison="exists", expected=None, deadline=2)
        filtered = self.evaluate(exists, [observation(confidence=0.1)])
        self.assertEqual(
            filtered.aggregate_result,
            ReconciliationResult.DIVERGENCE,
        )
        self.assertEqual(
            filtered.prediction_results[0].reason_code,
            ReasonCode.DIVERGE_EXISTS_FILTERED,
        )

        missed = self.evaluate(exists, [])
        self.assertEqual(
            missed.prediction_results[0].reason_code,
            ReasonCode.DIVERGE_EXISTS_MISSED,
        )

        cross_run = self.evaluate(
            exists,
            [observation() | {"run_id": "run-other"}],
        )
        self.assertEqual(
            cross_run.prediction_results[0].reason_code,
            ReasonCode.DIVERGE_EXISTS_MISSED,
        )

    def test_dc14_replay_report_compares_recorded_hash(self) -> None:
        report = replay_report(
            [prediction()],
            [observation()],
            run_id="run-1",
            cutoff_sequence=2,
        )
        self.assertEqual(report["result"], "REPLAY_REPORT")

        matching = replay_report(
            [prediction()],
            [observation()],
            run_id="run-1",
            cutoff_sequence=2,
            recorded_reconciliation_sha256=report["reconciliation_sha256"],
        )
        self.assertEqual(matching["result"], "REPLAY_MATCH")

        divergence = replay_report(
            [prediction()],
            [observation()],
            run_id="run-1",
            cutoff_sequence=2,
            recorded_reconciliation_sha256="not-a-sha256",
        )
        self.assertEqual(divergence["result"], "REPLAY_DIVERGENCE")

    def test_rebase_threshold_is_evaluator_only(self) -> None:
        result = self.evaluate(
            prediction(),
            [observation(value="wrong")],
            consecutive_divergences=2,
            rebase_after=3,
        )
        self.assertEqual(
            result.aggregate_result, ReconciliationResult.REBASE_REQUIRED
        )
        self.assertEqual(
            next_state(LaneState.RECONCILING, result),
            LaneState.AWAITING_REBASE,
        )

    def test_replay_is_byte_deterministic(self) -> None:
        first = replay_report(
            [prediction()],
            [observation()],
            run_id="run-1",
            cutoff_sequence=2,
        )
        second = replay_report(
            [prediction()],
            [observation()],
            run_id="run-1",
            cutoff_sequence=2,
        )
        self.assertEqual(
            json.dumps(first, sort_keys=True),
            json.dumps(second, sort_keys=True),
        )


class StateAndLedgerTests(unittest.TestCase):
    def test_new_state_path_preserves_legacy_path(self) -> None:
        machine = CoordinationStateMachine()
        machine.transition(LaneState.OBSERVING)
        machine.transition(LaneState.READY)
        machine.transition(LaneState.EXECUTING)
        machine.transition(LaneState.RECONCILING)
        self.assertEqual(machine.state, LaneState.RECONCILING)

    def test_episode_order_duplicate_and_candidate_view(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "ledger.sqlite3")
            first = ledger.record_episode_event(
                run_id="run-1",
                event_kind="TRIGGER_OCCURRENCE",
                subject="runtime",
                trigger_key="retry:flag",
                payload={"value": "private-a"},
            )
            duplicate = ledger.record_episode_event(
                run_id="run-1",
                event_kind="TRIGGER_OCCURRENCE",
                subject="runtime",
                trigger_key="retry:flag",
                payload={"value": "private-a"},
            )
            second = ledger.record_episode_event(
                run_id="run-1",
                event_kind="TRIGGER_OCCURRENCE",
                subject="runtime",
                trigger_key="retry:flag",
                payload={"value": "private-b"},
            )
            self.assertEqual((first, duplicate, second), (1, 1, 2))
            events = ledger.episode(run_id="run-1")
            self.assertEqual([item["sequence"] for item in events], [1, 2])
            self.assertNotIn("private-a", json.dumps(events))
            candidates = ledger.amendment_candidates()
            self.assertEqual(candidates[0]["status"], "CANDIDATE")
            self.assertEqual(candidates[0]["occurrence_count"], 2)


if __name__ == "__main__":
    unittest.main()
