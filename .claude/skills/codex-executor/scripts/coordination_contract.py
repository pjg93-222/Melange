"""Runtime validation for the Claude-to-Codex execution contract."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping, Sequence


class ContractError(ValueError):
    """A coordination payload violates the runtime contract."""


def _text(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{label} must be a non-empty string")
    return value.strip()


def _items(
    values: object,
    label: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, Mapping)) or not isinstance(
        values, Sequence
    ):
        raise ContractError(f"{label} must be an array")
    if not values and not allow_empty:
        raise ContractError(f"{label} must contain at least one item")
    return tuple(_text(value, f"{label} item") for value in values)


def _optional_items(values: object, label: str) -> tuple[str, ...]:
    return _items(values, label, allow_empty=True)


def _mapping_items(
    value: Mapping[str, object],
    key: str,
) -> tuple[str, ...]:
    items = value.get(key)
    return _optional_items(items, key)


def _mapping_text(value: Mapping[str, object], key: str) -> str:
    return _text(value.get(key, ""), key)  # type: ignore[arg-type]


class Readiness(str, Enum):
    READY = "READY"
    READY_WITH_LIMITS = "READY_WITH_LIMITS"
    BLOCKED = "BLOCKED"


class ReportKind(str, Enum):
    CORRECTION = "CORRECTION_REPORT"
    DECISION = "DECISION_REQUEST"
    STOP = "STOP_REPORT"
    CLOSEOUT = "CLOSEOUT"


class CorrectionVerdict(str, Enum):
    CONFIRM = "CONFIRM"
    MODIFY = "MODIFY"
    ROLLBACK = "ROLLBACK"
    ESCALATE = "ESCALATE"


class DecisionVerdict(str, Enum):
    CONTINUE = "CONTINUE"
    REVISE = "REVISE"
    REVERSE = "REVERSE"
    REDUCE_SCOPE = "REDUCE_SCOPE"
    REQUEST_USER_AUTHORIZATION = "REQUEST_USER_AUTHORIZATION"
    STOP = "STOP"


class LaneState(str, Enum):
    SPECIFIED = "SPECIFIED"
    OBSERVING = "OBSERVING"
    READY = "READY"
    EXECUTING = "EXECUTING"
    RECONCILING = "RECONCILING"
    AWAITING_CORRECTION_VERDICT = "AWAITING_CORRECTION_VERDICT"
    AWAITING_DECISION = "AWAITING_DECISION"
    AWAITING_REBASE = "AWAITING_REBASE"
    AWAITING_SPEC_FIX = "AWAITING_SPEC_FIX"
    REVIEW = "REVIEW"
    COMPLETE = "COMPLETE"
    STOPPED = "STOPPED"


@dataclass(frozen=True)
class ExecutionContract:
    objective: str
    constraints: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    impact_files: tuple[str, ...]
    impact_processes: tuple[str, ...]
    confirmation_conditions: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "objective", _text(self.objective, "objective"))
        object.__setattr__(
            self, "constraints", _items(self.constraints, "constraints")
        )
        object.__setattr__(
            self,
            "acceptance_criteria",
            _items(self.acceptance_criteria, "acceptance_criteria"),
        )
        impact_files = _optional_items(self.impact_files, "impact_files")
        impact_processes = _optional_items(
            self.impact_processes,
            "impact_processes",
        )
        if not impact_files and not impact_processes:
            raise ContractError(
                "impact envelope needs at least one file or permitted process"
            )
        object.__setattr__(self, "impact_files", impact_files)
        object.__setattr__(self, "impact_processes", impact_processes)
        object.__setattr__(
            self,
            "confirmation_conditions",
            _items(self.confirmation_conditions, "confirmation_conditions"),
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "ExecutionContract":
        envelope = value.get("impact_envelope")
        if not isinstance(envelope, Mapping):
            raise ContractError("impact_envelope must be an object")
        return cls(
            objective=value.get("objective", ""),  # type: ignore[arg-type]
            constraints=_mapping_items(value, "constraints"),
            acceptance_criteria=_mapping_items(value, "acceptance_criteria"),
            impact_files=_mapping_items(envelope, "files"),
            impact_processes=_mapping_items(envelope, "processes"),
            confirmation_conditions=_mapping_items(
                value, "confirmation_conditions"
            ),
        )


@dataclass(frozen=True)
class CapabilityHandshake:
    readiness: Readiness
    tools_verified: tuple[str, ...]
    permissions_verified: tuple[str, ...]
    files_verified: tuple[str, ...]
    reversal_options: tuple[str, ...]
    limits: tuple[str, ...] = ()
    blocker: str | None = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "readiness", Readiness(self.readiness))
        except (TypeError, ValueError) as exc:
            raise ContractError("readiness is not a recognized state") from exc
        for label in (
            "tools_verified",
            "permissions_verified",
            "files_verified",
            "reversal_options",
        ):
            object.__setattr__(self, label, _items(getattr(self, label), label))
        object.__setattr__(
            self,
            "limits",
            _optional_items(self.limits, "limits"),
        )
        if self.readiness is Readiness.READY and (self.limits or self.blocker):
            raise ContractError("READY cannot include limits or a blocker")
        if self.readiness is Readiness.READY_WITH_LIMITS and not self.limits:
            raise ContractError("READY_WITH_LIMITS must name at least one limit")
        if self.readiness is Readiness.READY_WITH_LIMITS and self.blocker:
            raise ContractError("READY_WITH_LIMITS cannot include a blocker")
        if self.readiness is Readiness.BLOCKED:
            if not self.blocker:
                raise ContractError("BLOCKED must name the blocker")
            _text(self.blocker, "blocker")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "CapabilityHandshake":
        try:
            readiness = Readiness(value.get("readiness"))
        except (TypeError, ValueError) as exc:
            raise ContractError("readiness is not a recognized state") from exc
        blocker = value.get("blocker")
        if blocker is not None and not isinstance(blocker, str):
            raise ContractError("blocker must be a string or null")
        return cls(
            readiness=readiness,
            tools_verified=_mapping_items(value, "tools_verified"),
            permissions_verified=_mapping_items(value, "permissions_verified"),
            files_verified=_mapping_items(value, "files_verified"),
            reversal_options=_mapping_items(value, "reversal_options"),
            limits=(
                ()
                if "limits" not in value
                else _mapping_items(value, "limits")
            ),
            blocker=blocker,
        )


@dataclass(frozen=True)
class CorrectionReport:
    trigger: str
    evidence_observed: str
    immediate_risk: str
    action_taken: str
    affected_state: tuple[str, ...]
    proportionality: str
    reversal: str
    current_safe_state: str
    recommended_next_step: str
    confirmation_requested: str

    def __post_init__(self) -> None:
        for label in (
            "trigger",
            "evidence_observed",
            "immediate_risk",
            "action_taken",
            "proportionality",
            "reversal",
            "current_safe_state",
            "recommended_next_step",
            "confirmation_requested",
        ):
            object.__setattr__(self, label, _text(getattr(self, label), label))
        if self.action_taken.casefold() == "none":
            raise ContractError("a correction report must name the action taken")
        object.__setattr__(
            self, "affected_state", _items(self.affected_state, "affected_state")
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "CorrectionReport":
        return cls(
            trigger=_mapping_text(value, "trigger"),
            evidence_observed=_mapping_text(value, "evidence_observed"),
            immediate_risk=_mapping_text(value, "immediate_risk"),
            action_taken=_mapping_text(value, "action_taken"),
            affected_state=_mapping_items(value, "affected_state"),
            proportionality=_mapping_text(value, "proportionality"),
            reversal=_mapping_text(value, "reversal"),
            current_safe_state=_mapping_text(value, "current_safe_state"),
            recommended_next_step=_mapping_text(value, "recommended_next_step"),
            confirmation_requested=_mapping_text(value, "confirmation_requested"),
        )


@dataclass(frozen=True)
class DecisionRequest:
    intended_result: str
    actual_result: str
    evidence: str
    current_state: str
    options: tuple[str, ...]
    risks: tuple[str, ...]
    recommended_option: str
    reversal_procedure: str
    decision_required: str

    def __post_init__(self) -> None:
        for label in (
            "intended_result",
            "actual_result",
            "evidence",
            "current_state",
            "recommended_option",
            "reversal_procedure",
            "decision_required",
        ):
            object.__setattr__(self, label, _text(getattr(self, label), label))
        object.__setattr__(self, "options", _items(self.options, "options"))
        object.__setattr__(self, "risks", _items(self.risks, "risks"))
        if len(self.options) != len(self.risks):
            raise ContractError("each option must have one corresponding risk")
        if self.recommended_option not in self.options:
            raise ContractError("recommended_option must be one of options")

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "DecisionRequest":
        return cls(
            intended_result=_mapping_text(value, "intended_result"),
            actual_result=_mapping_text(value, "actual_result"),
            evidence=_mapping_text(value, "evidence"),
            current_state=_mapping_text(value, "current_state"),
            options=_mapping_items(value, "options"),
            risks=_mapping_items(value, "risks"),
            recommended_option=_mapping_text(value, "recommended_option"),
            reversal_procedure=_mapping_text(value, "reversal_procedure"),
            decision_required=_mapping_text(value, "decision_required"),
        )


@dataclass
class CoordinationStateMachine:
    state: LaneState = LaneState.SPECIFIED
    history: list[LaneState] = field(default_factory=lambda: [LaneState.SPECIFIED])

    _ALLOWED = {
        LaneState.SPECIFIED: {
            LaneState.OBSERVING,
            LaneState.READY,
            LaneState.AWAITING_SPEC_FIX,
        },
        LaneState.OBSERVING: {
            LaneState.READY,
            LaneState.AWAITING_CORRECTION_VERDICT,
            LaneState.STOPPED,
        },
        LaneState.READY: {LaneState.EXECUTING, LaneState.AWAITING_DECISION, LaneState.STOPPED},
        LaneState.EXECUTING: {
            LaneState.RECONCILING,
            LaneState.AWAITING_CORRECTION_VERDICT,
            LaneState.AWAITING_DECISION,
            LaneState.AWAITING_SPEC_FIX,
            LaneState.REVIEW,
            LaneState.STOPPED,
        },
        LaneState.RECONCILING: {
            LaneState.EXECUTING,
            LaneState.AWAITING_CORRECTION_VERDICT,
            LaneState.AWAITING_DECISION,
            LaneState.AWAITING_REBASE,
            LaneState.REVIEW,
            LaneState.STOPPED,
        },
        LaneState.AWAITING_CORRECTION_VERDICT: {
            LaneState.EXECUTING,
            LaneState.STOPPED,
        },
        LaneState.AWAITING_DECISION: {LaneState.EXECUTING, LaneState.STOPPED},
        LaneState.AWAITING_REBASE: {LaneState.OBSERVING, LaneState.STOPPED},
        LaneState.AWAITING_SPEC_FIX: {LaneState.SPECIFIED, LaneState.STOPPED},
        LaneState.REVIEW: {LaneState.EXECUTING, LaneState.COMPLETE, LaneState.STOPPED},
        LaneState.COMPLETE: set(),
        LaneState.STOPPED: set(),
    }

    def transition(self, target: LaneState) -> None:
        if target not in self._ALLOWED[self.state]:
            raise ContractError(f"invalid transition: {self.state} -> {target}")
        self.state = target
        self.history.append(target)


def validate_verdict(report_kind: ReportKind, verdict: str) -> str:
    if report_kind is ReportKind.CORRECTION:
        return CorrectionVerdict(verdict).value
    if report_kind is ReportKind.DECISION:
        return DecisionVerdict(verdict).value
    raise ContractError(f"{report_kind.value} does not accept a verdict")
