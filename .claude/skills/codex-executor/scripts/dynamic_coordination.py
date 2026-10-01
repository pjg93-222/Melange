"""Deterministic dynamic-coordination types, evaluation, and replay."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
import hashlib
import json
import re
from typing import Mapping, Sequence

from coordination_contract import LaneState


class DynamicCoordinationError(ValueError):
    """A dynamic-coordination input fails a closed validation rule."""


class ReconciliationResult(str, Enum):
    MATCH = "MATCH"
    BOUNDED_DRIFT = "BOUNDED_DRIFT"
    DIVERGENCE = "DIVERGENCE"
    UNKNOWN = "UNKNOWN"
    REBASE_REQUIRED = "REBASE_REQUIRED"


class Comparison(str, Enum):
    EQUALS = "equals"
    CONTAINS = "contains"
    EXISTS = "exists"
    ABSENT = "absent"
    RANGE = "range"
    CHANGED = "changed"
    UNCHANGED = "unchanged"


class EvidenceClass(str, Enum):
    INDEPENDENT = "independent"
    SELF_GENERATED = "self_generated"


class GeneralizationScope(str, Enum):
    EXACT_CONTEXT = "EXACT_CONTEXT"
    RELATED_CONTEXT = "RELATED_CONTEXT"
    UNSEEN_CONTEXT = "UNSEEN_CONTEXT"


class CorrectionDisposition(str, Enum):
    RESUME_PRIOR = "RESUME_PRIOR"
    PAUSE_FOR_DECISION = "PAUSE_FOR_DECISION"
    ESCALATE_TO_USER = "ESCALATE_TO_USER"


class ReasonCode(str, Enum):
    MATCH = "RC_MATCH"
    DRIFT_BAND = "RC_DRIFT_BAND"
    DIVERGE_VALUE = "RC_DIVERGE_VALUE"
    DIVERGE_ABSENT_VIOLATED = "RC_DIVERGE_ABSENT_VIOLATED"
    DIVERGE_EXISTS_MISSED = "RC_DIVERGE_EXISTS_MISSED"
    DIVERGE_EXISTS_FILTERED = "RC_DIVERGE_EXISTS_FILTERED"
    DIVERGE_BASELINE_EQUAL = "RC_DIVERGE_BASELINE_EQUAL"
    DIVERGE_BASELINE_DIFFERS = "RC_DIVERGE_BASELINE_DIFFERS"
    UNKNOWN_NO_ELIGIBLE = "RC_UNKNOWN_NO_ELIGIBLE"
    UNKNOWN_CUTOFF = "RC_UNKNOWN_CUTOFF"
    UNKNOWN_STALE = "RC_UNKNOWN_STALE"
    UNKNOWN_LOW_CONFIDENCE = "RC_UNKNOWN_LOW_CONFIDENCE"
    UNKNOWN_SELF_GENERATED = "RC_UNKNOWN_SELF_GENERATED"
    UNKNOWN_MALFORMED = "RC_UNKNOWN_MALFORMED"
    UNKNOWN_BASELINE = "RC_UNKNOWN_BASELINE"
    UNKNOWN_BASELINE_UNAVAILABLE = "RC_UNKNOWN_BASELINE_UNAVAILABLE"
    UNKNOWN_CAUSAL = "RC_UNKNOWN_CAUSAL"
    PRE_DEADLINE_INDETERMINATE = "RC_PRE_DEADLINE_INDETERMINATE"
    REBASE_STREAK = "RC_REBASE_STREAK"


_OBSERVATION_KEYS = {
    "observation_id",
    "run_id",
    "sequence",
    "observed_at",
    "source",
    "kind",
    "subject",
    "value",
    "confidence",
    "evidence_class",
    "caused_by_action_id",
    "retry_attempt_id",
    "content_sha256",
}
_PREDICTION_KEYS = {
    "prediction_id",
    "step_id",
    "subject",
    "expected",
    "comparison",
    "tolerance",
    "deadline_sequence",
    "allow_self_generated",
    "minimum_evidence_confidence",
    "max_observation_age_seconds",
    "allow_bounded_drift_continue",
}
_OBSERVATION_SOURCES = {"tool", "file", "process", "service", "reviewer"}
_OBSERVATION_KINDS = {
    "exit_code",
    "file_state",
    "process_state",
    "response",
    "drift",
    "metric",
}
_CAUSED_BY_ACTION_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_MAX_COMPARISON_DEPTH = 32
_MISSING_OBSERVATION_VALUE = object()


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise DynamicCoordinationError(f"{label} must be an object")
    return value


def _closed(value: Mapping[str, object], allowed: set[str], label: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise DynamicCoordinationError(
            f"{label} contains unknown keys: {', '.join(unknown)}"
        )


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DynamicCoordinationError(f"{label} must be a non-empty string")
    return value.strip()


def _action_id(value: object) -> str:
    text = _text(value, "caused_by_action_id")
    if text != value or (
        text != "none" and _CAUSED_BY_ACTION_ID.fullmatch(text) is None
    ):
        raise DynamicCoordinationError(
            "caused_by_action_id must be 'none' or match "
            "^[A-Za-z0-9_.:-]{1,64}$"
        )
    return text


def _valid_action_id(value: object) -> bool:
    return isinstance(value, str) and (
        value == "none" or _CAUSED_BY_ACTION_ID.fullmatch(value) is not None
    )


def _integer(value: object, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise DynamicCoordinationError(
            f"{label} must be an integer >= {minimum}"
        )
    return value


def _decimal(value: object, label: str) -> Decimal:
    if isinstance(value, bool):
        raise DynamicCoordinationError(f"{label} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise DynamicCoordinationError(f"{label} must be numeric") from exc
    if not result.is_finite():
        raise DynamicCoordinationError(f"{label} must be finite")
    return result


def _probability(value: object, label: str) -> Decimal:
    result = _decimal(value, label)
    if result < 0 or result > 1:
        raise DynamicCoordinationError(f"{label} must be between 0 and 1")
    return result


def _is_scalar(value: object) -> bool:
    return isinstance(value, (str, int, float, bool))


def _is_non_bool_number(value: object) -> bool:
    return isinstance(value, (int, float, Decimal)) and not isinstance(value, bool)


def _guarded_equal(
    left: object,
    right: object,
    *,
    _depth: int = 0,
) -> bool:
    if _depth > _MAX_COMPARISON_DEPTH:
        return False
    if (isinstance(left, bool) and _is_non_bool_number(right)) or (
        isinstance(right, bool) and _is_non_bool_number(left)
    ):
        return False
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _guarded_equal(left_item, right_item, _depth=_depth + 1)
            for left_item, right_item in zip(left, right)
        )
    if isinstance(left, dict) and isinstance(right, dict):
        left_canonical = {
            (isinstance(key, bool), key): value
            for key, value in left.items()
        }
        right_canonical = {
            (isinstance(key, bool), key): value
            for key, value in right.items()
        }
        return (
            len(left_canonical) == len(right_canonical)
            and left_canonical.keys() == right_canonical.keys()
            and all(
                _guarded_equal(
                    left_value,
                    right_canonical[key],
                    _depth=_depth + 1,
                )
                for key, left_value in left_canonical.items()
            )
        )
    return left == right


def _timestamp(value: object, label: str) -> datetime:
    text = _text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DynamicCoordinationError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise DynamicCoordinationError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def parse_timestamp(value: object, label: str = "timestamp") -> datetime:
    """Parse one explicit, timezone-aware timestamp for a pinned evaluation."""

    return _timestamp(value, label)


def canonical_hash(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class Observation:
    observation_id: str
    run_id: str
    sequence: int
    observed_at: datetime
    source: str
    kind: str
    subject: str
    value: object
    confidence: Decimal
    evidence_class: EvidenceClass
    caused_by_action_id: str
    retry_attempt_id: str | None = None
    content_sha256: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "Observation":
        value = _mapping(value, "observation")
        _closed(value, _OBSERVATION_KEYS, "observation")
        caused_by = _action_id(value.get("caused_by_action_id"))
        retry = value.get("retry_attempt_id")
        digest = value.get("content_sha256")
        if retry is not None:
            retry = _text(retry, "retry_attempt_id")
        if digest is not None:
            digest = _text(digest, "content_sha256")
            if len(digest) != 64:
                raise DynamicCoordinationError(
                    "content_sha256 must contain 64 hexadecimal characters"
                )
            try:
                int(digest, 16)
            except ValueError as exc:
                raise DynamicCoordinationError(
                    "content_sha256 must be hexadecimal"
                ) from exc
        try:
            evidence_class = EvidenceClass(value.get("evidence_class"))
        except (TypeError, ValueError) as exc:
            raise DynamicCoordinationError(
                "evidence_class is not recognized"
            ) from exc
        source = _text(value.get("source"), "source")
        kind = _text(value.get("kind"), "kind")
        if source not in _OBSERVATION_SOURCES:
            raise DynamicCoordinationError("source is not recognized")
        if kind not in _OBSERVATION_KINDS:
            raise DynamicCoordinationError("kind is not recognized")
        return cls(
            observation_id=_text(value.get("observation_id"), "observation_id"),
            run_id=_text(value.get("run_id"), "run_id"),
            sequence=_integer(value.get("sequence"), "sequence", minimum=1),
            observed_at=_timestamp(value.get("observed_at"), "observed_at"),
            source=source,
            kind=kind,
            subject=_text(value.get("subject"), "subject"),
            value=(
                value["value"]
                if "value" in value
                else _MISSING_OBSERVATION_VALUE
            ),
            confidence=_probability(value.get("confidence"), "confidence"),
            evidence_class=evidence_class,
            caused_by_action_id=caused_by,
            retry_attempt_id=retry,
            content_sha256=digest,
        )


@dataclass(frozen=True)
class Prediction:
    prediction_id: str
    step_id: str
    subject: str
    expected: object
    comparison: Comparison
    tolerance: Mapping[str, object]
    deadline_sequence: int
    allow_self_generated: bool
    minimum_evidence_confidence: Decimal
    max_observation_age_seconds: int | None
    allow_bounded_drift_continue: bool

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "Prediction":
        value = _mapping(value, "prediction")
        _closed(value, _PREDICTION_KEYS, "prediction")
        tolerance = value.get("tolerance")
        if not isinstance(tolerance, Mapping):
            raise DynamicCoordinationError("tolerance must be an object")
        try:
            comparison = Comparison(value.get("comparison"))
        except (TypeError, ValueError) as exc:
            raise DynamicCoordinationError("comparison is not recognized") from exc
        _validate_tolerance(comparison, tolerance)
        expected = value.get("expected")
        if comparison in {
            Comparison.EQUALS,
            Comparison.CONTAINS,
            Comparison.RANGE,
        } and ("expected" not in value or expected is None):
            raise DynamicCoordinationError(
                f"{comparison.value} requires a non-null expected value"
            )
        if comparison is Comparison.CONTAINS:
            mode = tolerance["mode"]
            if mode == "substring":
                if not isinstance(expected, str) or not expected.strip():
                    raise DynamicCoordinationError(
                        "contains substring expected must be a non-empty string"
                    )
            elif not _is_scalar(expected):
                raise DynamicCoordinationError(
                    "contains element expected must be a non-null scalar"
                )
        allow_self = value.get("allow_self_generated", False)
        allow_drift = value.get("allow_bounded_drift_continue", False)
        if not isinstance(allow_self, bool) or not isinstance(allow_drift, bool):
            raise DynamicCoordinationError("allow fields must be boolean")
        max_age = value.get("max_observation_age_seconds")
        if max_age is not None:
            max_age = _integer(
                max_age,
                "max_observation_age_seconds",
                minimum=0,
            )
        return cls(
            prediction_id=_text(value.get("prediction_id"), "prediction_id"),
            step_id=_text(value.get("step_id"), "step_id"),
            subject=_text(value.get("subject"), "subject"),
            expected=expected,
            comparison=comparison,
            tolerance=dict(tolerance),
            deadline_sequence=_integer(
                value.get("deadline_sequence"),
                "deadline_sequence",
                minimum=1,
            ),
            allow_self_generated=allow_self,
            minimum_evidence_confidence=_probability(
                value.get("minimum_evidence_confidence", 0),
                "minimum_evidence_confidence",
            ),
            max_observation_age_seconds=max_age,
            allow_bounded_drift_continue=allow_drift,
        )


def _validate_tolerance(
    comparison: Comparison,
    tolerance: Mapping[str, object],
) -> None:
    allowed: set[str]
    if comparison in {
        Comparison.EQUALS,
        Comparison.EXISTS,
        Comparison.ABSENT,
    }:
        allowed = set()
    elif comparison is Comparison.CONTAINS:
        allowed = {"mode"}
        if tolerance.get("mode") not in {"substring", "element"}:
            raise DynamicCoordinationError(
                "contains tolerance.mode must be substring or element"
            )
    elif comparison is Comparison.RANGE:
        allowed = {"match_min", "match_max", "drift_min", "drift_max"}
        if "match_min" not in tolerance or "match_max" not in tolerance:
            raise DynamicCoordinationError("range needs match_min and match_max")
        match_min = _decimal(tolerance["match_min"], "match_min")
        match_max = _decimal(tolerance["match_max"], "match_max")
        if match_min > match_max:
            raise DynamicCoordinationError("match_min must be <= match_max")
        if tolerance.get("drift_min") is not None and _decimal(
            tolerance["drift_min"], "drift_min"
        ) > match_min:
            raise DynamicCoordinationError("drift_min must be <= match_min")
        if tolerance.get("drift_max") is not None and _decimal(
            tolerance["drift_max"], "drift_max"
        ) < match_max:
            raise DynamicCoordinationError("drift_max must be >= match_max")
    else:
        allowed = {"baseline_observation_id"}
        _text(
            tolerance.get("baseline_observation_id"),
            "baseline_observation_id",
        )
    _closed(tolerance, allowed, f"{comparison.value} tolerance")


@dataclass(frozen=True)
class PredictionResult:
    prediction_id: str
    observation_id: str | None
    result: ReconciliationResult
    reason_code: ReasonCode
    terminal: bool = True
    continuation_permitted: bool = False


@dataclass(frozen=True)
class Reconciliation:
    prediction_results: tuple[PredictionResult, ...]
    aggregate_result: ReconciliationResult
    evaluated_at_sequence: int
    reconciliation_sha256: str


def _latest_eligible(
    prediction: Prediction,
    observations: Sequence[Observation],
    *,
    run_id: str,
    cutoff_sequence: int,
    evaluated_at: datetime | None,
) -> tuple[
    list[Observation],
    list[tuple[Observation, ReasonCode]],
    int,
]:
    subject = [
        item
        for item in observations
        if item.run_id == run_id
        and item.subject == prediction.subject
    ]
    eligible: list[Observation] = []
    excluded: list[tuple[Observation, ReasonCode]] = []
    latest_sequence = min(cutoff_sequence, prediction.deadline_sequence)
    for item in sorted(subject, key=lambda entry: entry.sequence):
        if item.sequence > latest_sequence:
            excluded.append((item, ReasonCode.UNKNOWN_CUTOFF))
            continue
        if prediction.max_observation_age_seconds is not None:
            if evaluated_at is None or (
                evaluated_at - item.observed_at
            ).total_seconds() > prediction.max_observation_age_seconds:
                excluded.append((item, ReasonCode.UNKNOWN_STALE))
                continue
        if item.confidence < prediction.minimum_evidence_confidence:
            excluded.append((item, ReasonCode.UNKNOWN_LOW_CONFIDENCE))
            continue
        if (
            item.evidence_class is EvidenceClass.SELF_GENERATED
            and not prediction.allow_self_generated
        ):
            excluded.append((item, ReasonCode.UNKNOWN_SELF_GENERATED))
            continue
        if not _valid_action_id(item.caused_by_action_id):
            excluded.append((item, ReasonCode.UNKNOWN_CAUSAL))
            continue
        eligible.append(item)
    return eligible, excluded, len(subject)


def _latest_exclusion_reason(
    excluded: Sequence[tuple[Observation, ReasonCode]],
) -> ReasonCode:
    if not excluded:
        return ReasonCode.UNKNOWN_NO_ELIGIBLE
    return max(excluded, key=lambda entry: entry[0].sequence)[1]


def _compare(
    prediction: Prediction,
    eligible: Sequence[Observation],
    excluded: Sequence[tuple[Observation, ReasonCode]],
    subject_count: int,
    *,
    cutoff_sequence: int,
) -> PredictionResult:
    if prediction.comparison in {Comparison.EXISTS, Comparison.ABSENT}:
        if cutoff_sequence < prediction.deadline_sequence:
            return PredictionResult(
                prediction.prediction_id,
                None,
                ReconciliationResult.UNKNOWN,
                ReasonCode.PRE_DEADLINE_INDETERMINATE,
                terminal=False,
            )
        if prediction.comparison is Comparison.EXISTS:
            if eligible:
                return PredictionResult(
                    prediction.prediction_id,
                    eligible[-1].observation_id,
                    ReconciliationResult.MATCH,
                    ReasonCode.MATCH,
                )
            return PredictionResult(
                prediction.prediction_id,
                None,
                ReconciliationResult.DIVERGENCE,
                (
                    ReasonCode.DIVERGE_EXISTS_FILTERED
                    if subject_count
                    else ReasonCode.DIVERGE_EXISTS_MISSED
                ),
            )
        if eligible:
            return PredictionResult(
                prediction.prediction_id,
                eligible[-1].observation_id,
                ReconciliationResult.DIVERGENCE,
                ReasonCode.DIVERGE_ABSENT_VIOLATED,
            )
        if subject_count:
            return PredictionResult(
                prediction.prediction_id,
                None,
                ReconciliationResult.UNKNOWN,
                _latest_exclusion_reason(excluded),
            )
        return PredictionResult(
            prediction.prediction_id,
            None,
            ReconciliationResult.MATCH,
            ReasonCode.MATCH,
        )
    if not eligible:
        return PredictionResult(
            prediction.prediction_id,
            None,
            ReconciliationResult.UNKNOWN,
            ReasonCode.UNKNOWN_NO_ELIGIBLE,
        )
    observation = max(eligible, key=lambda item: item.sequence)
    comparison = prediction.comparison
    if comparison in {
        Comparison.EQUALS,
        Comparison.CONTAINS,
        Comparison.RANGE,
    } and observation.value is _MISSING_OBSERVATION_VALUE:
        return PredictionResult(
            prediction.prediction_id,
            observation.observation_id,
            ReconciliationResult.UNKNOWN,
            ReasonCode.UNKNOWN_MALFORMED,
        )
    try:
        if comparison is Comparison.EQUALS:
            matched = _guarded_equal(observation.value, prediction.expected)
        elif comparison is Comparison.CONTAINS:
            mode = prediction.tolerance["mode"]
            if mode == "substring":
                if not isinstance(observation.value, str) or not isinstance(
                    prediction.expected, str
                ):
                    raise TypeError
                matched = prediction.expected in observation.value
            else:
                if not isinstance(observation.value, list) or any(
                    isinstance(item, (list, dict)) for item in observation.value
                ) or not _is_scalar(prediction.expected):
                    raise TypeError
                matched = any(
                    _guarded_equal(prediction.expected, item)
                    for item in observation.value
                )
        elif comparison is Comparison.RANGE:
            actual = _decimal(observation.value, "observation value")
            match_min = _decimal(prediction.tolerance["match_min"], "match_min")
            match_max = _decimal(prediction.tolerance["match_max"], "match_max")
            if match_min <= actual <= match_max:
                return PredictionResult(
                    prediction.prediction_id,
                    observation.observation_id,
                    ReconciliationResult.MATCH,
                    ReasonCode.MATCH,
                )
            drift_min = prediction.tolerance.get("drift_min")
            drift_max = prediction.tolerance.get("drift_max")
            lower = match_min if drift_min is None else _decimal(
                drift_min, "drift_min"
            )
            upper = match_max if drift_max is None else _decimal(
                drift_max, "drift_max"
            )
            if lower <= actual <= upper:
                return PredictionResult(
                    prediction.prediction_id,
                    observation.observation_id,
                    ReconciliationResult.BOUNDED_DRIFT,
                    ReasonCode.DRIFT_BAND,
                )
            matched = False
        else:
            baseline_id = str(
                prediction.tolerance["baseline_observation_id"]
            )
            if baseline_id == observation.observation_id:
                return PredictionResult(
                    prediction.prediction_id,
                    observation.observation_id,
                    ReconciliationResult.UNKNOWN,
                    ReasonCode.UNKNOWN_BASELINE,
                )
            baseline = next(
                (
                    item
                    for item in eligible
                    if item.observation_id == baseline_id
                ),
                None,
            )
            if baseline is None:
                return PredictionResult(
                    prediction.prediction_id,
                    observation.observation_id,
                    ReconciliationResult.UNKNOWN,
                    ReasonCode.UNKNOWN_BASELINE,
                )
            changed = canonical_hash(observation.value) != canonical_hash(
                baseline.value
            )
            matched = (
                changed
                if comparison is Comparison.CHANGED
                else not changed
            )
            reason = (
                ReasonCode.DIVERGE_BASELINE_EQUAL
                if comparison is Comparison.CHANGED
                else ReasonCode.DIVERGE_BASELINE_DIFFERS
            )
            return PredictionResult(
                prediction.prediction_id,
                observation.observation_id,
                (
                    ReconciliationResult.MATCH
                    if matched
                    else ReconciliationResult.DIVERGENCE
                ),
                ReasonCode.MATCH if matched else reason,
            )
    except (DynamicCoordinationError, TypeError, ValueError):
        return PredictionResult(
            prediction.prediction_id,
            observation.observation_id,
            ReconciliationResult.UNKNOWN,
            ReasonCode.UNKNOWN_MALFORMED,
        )
    return PredictionResult(
        prediction.prediction_id,
        observation.observation_id,
        ReconciliationResult.MATCH if matched else ReconciliationResult.DIVERGENCE,
        ReasonCode.MATCH if matched else ReasonCode.DIVERGE_VALUE,
    )


def reconcile(
    predictions: Sequence[Prediction],
    observations: Sequence[Observation],
    *,
    run_id: str,
    cutoff_sequence: int,
    consecutive_divergences: int = 0,
    rebase_after: int = 3,
    evaluated_at: datetime | None = None,
) -> Reconciliation:
    if not predictions:
        raise DynamicCoordinationError("predictions must not be empty")
    _integer(cutoff_sequence, "cutoff_sequence", minimum=1)
    _integer(
        consecutive_divergences,
        "consecutive_divergences",
        minimum=0,
    )
    _integer(rebase_after, "rebase_after", minimum=1)
    results = []
    for prediction in predictions:
        eligible, excluded, subject_count = _latest_eligible(
            prediction,
            observations,
            run_id=run_id,
            cutoff_sequence=cutoff_sequence,
            evaluated_at=evaluated_at,
        )
        result = _compare(
            prediction,
            eligible,
            excluded,
            subject_count,
            cutoff_sequence=cutoff_sequence,
        )
        if result.result is ReconciliationResult.UNKNOWN and not eligible:
            result = PredictionResult(
                result.prediction_id,
                result.observation_id,
                result.result,
                (
                    result.reason_code
                    if result.reason_code is ReasonCode.PRE_DEADLINE_INDETERMINATE
                    else _latest_exclusion_reason(excluded)
                ),
                result.terminal,
            )
        result = PredictionResult(
            result.prediction_id,
            result.observation_id,
            result.result,
            result.reason_code,
            result.terminal,
            prediction.allow_bounded_drift_continue,
        )
        results.append(result)
    values = {item.result for item in results}
    if ReconciliationResult.DIVERGENCE in values:
        aggregate = (
            ReconciliationResult.REBASE_REQUIRED
            if consecutive_divergences + 1 >= rebase_after
            else ReconciliationResult.DIVERGENCE
        )
    elif ReconciliationResult.UNKNOWN in values:
        aggregate = ReconciliationResult.UNKNOWN
    elif ReconciliationResult.BOUNDED_DRIFT in values:
        aggregate = ReconciliationResult.BOUNDED_DRIFT
    else:
        aggregate = ReconciliationResult.MATCH
    payload = {
        "prediction_results": [
            {
                "prediction_id": item.prediction_id,
                "observation_id": item.observation_id,
                "result": item.result.value,
                "reason_code": item.reason_code.value,
                "terminal": item.terminal,
                "continuation_permitted": item.continuation_permitted,
            }
            for item in results
        ],
        "aggregate_result": aggregate.value,
        "evaluated_at_sequence": cutoff_sequence,
    }
    return Reconciliation(
        prediction_results=tuple(results),
        aggregate_result=aggregate,
        evaluated_at_sequence=cutoff_sequence,
        reconciliation_sha256=canonical_hash(payload),
    )


def next_state(
    current: LaneState,
    reconciliation: Reconciliation,
) -> LaneState:
    if current is not LaneState.RECONCILING:
        raise DynamicCoordinationError(
            "reconciliation results apply only from RECONCILING"
        )
    result = reconciliation.aggregate_result
    if result is ReconciliationResult.MATCH:
        return LaneState.EXECUTING
    if result is ReconciliationResult.BOUNDED_DRIFT:
        permitted = all(
            item.result is not ReconciliationResult.BOUNDED_DRIFT
            or item.continuation_permitted
            for item in reconciliation.prediction_results
        )
        return LaneState.EXECUTING if permitted else LaneState.AWAITING_DECISION
    if result is ReconciliationResult.REBASE_REQUIRED:
        return LaneState.AWAITING_REBASE
    return LaneState.AWAITING_DECISION


def replay_report(
    predictions: Sequence[Mapping[str, object]],
    observations: Sequence[Mapping[str, object]],
    *,
    run_id: str,
    cutoff_sequence: int,
    consecutive_divergences: int = 0,
    rebase_after: int = 3,
    evaluated_at: str | None = None,
    recorded_reconciliation_sha256: str | None = None,
) -> dict[str, object]:
    reconciliation = reconcile(
        [Prediction.from_mapping(value) for value in predictions],
        [Observation.from_mapping(value) for value in observations],
        run_id=run_id,
        cutoff_sequence=cutoff_sequence,
        consecutive_divergences=consecutive_divergences,
        rebase_after=rebase_after,
        evaluated_at=(
            None if evaluated_at is None else _timestamp(evaluated_at, "evaluated_at")
        ),
    )
    if recorded_reconciliation_sha256 is None:
        replay_result = "REPLAY_REPORT"
    elif recorded_reconciliation_sha256 == reconciliation.reconciliation_sha256:
        replay_result = "REPLAY_MATCH"
    else:
        replay_result = "REPLAY_DIVERGENCE"
    return {
        "result": replay_result,
        "aggregate_result": reconciliation.aggregate_result.value,
        "evaluated_at_sequence": reconciliation.evaluated_at_sequence,
        "reconciliation_sha256": reconciliation.reconciliation_sha256,
        "prediction_results": [
            {
                "prediction_id": item.prediction_id,
                "observation_id": item.observation_id,
                "result": item.result.value,
                "reason_code": item.reason_code.value,
                "terminal": item.terminal,
                "continuation_permitted": item.continuation_permitted,
            }
            for item in reconciliation.prediction_results
        ],
    }
