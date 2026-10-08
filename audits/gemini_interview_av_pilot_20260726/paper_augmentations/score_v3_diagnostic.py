#!/usr/bin/env python3
"""Validate v3 Flash receipts and compare executable metrics with v2."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import re
from collections import Counter
from pathlib import Path


AUDIT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "v3_manifest.json"
RESULTS = HERE / "v3_results"
V2_RESULTS = AUDIT / "results_web_v2"
TURNS = AUDIT.parents[1] / "cspan_out" / "turns.csv"
OUTPUT_JSON = HERE / "v3_score.json"
OUTPUT_MD = HERE / "V3_RESULTS.md"

TOP_KEYS = {
    "schema",
    "case_id",
    "condition",
    "media_processed",
    "abstained",
    "quality_flags",
    "atomic",
    "composite",
    "evidence",
    "prohibited_inference_detected",
    "error",
}
AUDIO_KEYS = {
    "speech",
    "speaker_count",
    "target_active_intervals",
    "events",
    "excerpt",
    "pace",
    "pause_frequency",
    "disfluency_frequency",
    "prosodic_variability",
}
VISUAL_KEYS = {
    "person_visible",
    "face_visible",
    "upper_body_visible",
    "displayed_text",
    "events",
}
COMPOSITE_KEYS = {
    "av_consistency",
    "synchronization",
    "lag_ms",
    "absent_modality",
    "confidence",
}
LEVELS = {"low", "medium", "high", "not_observable"}
SPEECH_VALUES = {"present", "absent", "uncertain", "not_observable"}
VISIBILITY_VALUES = {"yes", "no", "uncertain", "not_observable"}
EVENT_TYPES = {
    "gesture",
    "head_move",
    "posture_shift",
    "shot_change",
    "turn_coordination",
    "other",
}
ORDER_RELATIONS = {"before", "after", "overlaps", "uncertain"}
AV_CONSISTENCY_VALUES = {
    "matched",
    "mismatched",
    "uncertain",
    "not_applicable",
}
SYNCHRONIZATION_VALUES = {
    "synchronized",
    "audio_leads",
    "video_leads",
    "not_observable",
}
ABSENT_MODALITY_VALUES = {"none", "audio", "video", "not_applicable"}
PROHIBITED = re.compile(
    r"\b(big\s*five|personality|honest|dishonest|intelligen|"
    r"mental state|diagnos|depress|anxious|attractive|character trait)\b",
    flags=re.IGNORECASE,
)


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", (value or "").lower())


def bag_coverage(needle: list[str], haystack: list[str]) -> float:
    if not needle:
        return 0.0
    available = Counter(haystack)
    matched = 0
    for token in needle:
        if available[token]:
            matched += 1
            available[token] -= 1
    return matched / len(needle)


def longest_contiguous(needle: list[str], haystack: list[str]) -> int:
    previous = [0] * (len(haystack) + 1)
    best = 0
    for left in needle:
        current = [0]
        for index, right in enumerate(haystack, start=1):
            value = previous[index - 1] + 1 if left == right else 0
            current.append(value)
            best = max(best, value)
        previous = current
    return best


def grounding(excerpt: str, target: str) -> dict:
    excerpt_tokens = tokens(excerpt)
    target_tokens = tokens(target)
    coverage = bag_coverage(excerpt_tokens, target_tokens)
    contiguous = longest_contiguous(excerpt_tokens, target_tokens)
    grounded = (
        len(excerpt_tokens) >= 4
        and (contiguous >= 4 or (len(excerpt_tokens) >= 6 and coverage >= 0.80))
    )
    return {
        "excerpt": excerpt,
        "token_count": len(excerpt_tokens),
        "bag_coverage": round(coverage, 6),
        "longest_contiguous": contiguous,
        "grounded": grounded,
    }


def bootstrap_rate(values: list[bool], samples: int = 10_000) -> dict:
    if not values:
        return {"estimate": None, "ci95": [None, None]}
    rng = random.Random(20260726)
    n = len(values)
    estimates = []
    numeric = [int(value) for value in values]
    for _ in range(samples):
        estimates.append(sum(rng.choice(numeric) for _ in range(n)) / n)
    estimates.sort()
    return {
        "estimate": round(sum(numeric) / n, 6),
        "ci95": [
            round(estimates[int(0.025 * samples)], 6),
            round(estimates[int(0.975 * samples) - 1], 6),
        ],
    }


def full_turns() -> dict[tuple[str, int], str]:
    rows = {}
    with TURNS.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            try:
                key = (str(row["id"]), int(row["seq"]))
            except (KeyError, TypeError, ValueError):
                continue
            rows[key] = row.get("text", "")
    return rows


def expected_tasks(manifest: dict) -> list[dict]:
    tasks = []
    for case in manifest["cases"]:
        for condition, derivative in case["derivatives"].items():
            tasks.append(
                {
                    "case_id": case["case_id"],
                    "task_id": f"{case['case_id']}-{condition}",
                    "condition": condition,
                    "duration_sec": float(derivative["duration_sec"]),
                    "media_sha256": derivative["sha256"],
                    "role": case["role"],
                    "program_id": case["source"]["program_id"],
                    "target_turn_seq": int(case["source"]["target_turn_seq"]),
                    "hidden_label": "matched" if condition == "audiovisual" else None,
                }
            )
    for mismatch in manifest["mismatches"]:
        derivative = mismatch["derivative"]
        tasks.append(
            {
                "case_id": mismatch["case_id"],
                "task_id": f"{mismatch['case_id']}-audiovisual",
                "condition": "audiovisual",
                "duration_sec": float(derivative["duration_sec"]),
                "media_sha256": derivative["sha256"],
                "role": "hidden_mismatch",
                "program_id": None,
                "target_turn_seq": None,
                "hidden_label": "mismatched",
            }
        )
    return tasks


def add_time_issue(
    issues: list[str],
    label: str,
    value: object,
    duration: float,
) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        issues.append(f"{label}: timestamp_not_numeric")
    elif not math.isfinite(float(value)) or not 0 <= float(value) <= duration:
        issues.append(f"{label}: timestamp_out_of_bounds:{value}")


def enum_issue(
    issues: list[str],
    label: str,
    value: object,
    allowed: set[str],
) -> None:
    if value not in allowed:
        issues.append(f"{label}:invalid_enum:{value}")


def numeric_issue(
    issues: list[str],
    label: str,
    value: object,
    minimum: float | None = None,
    maximum: float | None = None,
) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        issues.append(f"{label}:not_numeric")
        return
    number = float(value)
    if not math.isfinite(number):
        issues.append(f"{label}:not_finite")
    elif minimum is not None and number < minimum:
        issues.append(f"{label}:below_minimum")
    elif maximum is not None and number > maximum:
        issues.append(f"{label}:above_maximum")


def validate_result(task: dict, wrapper: dict) -> dict:
    issues = []
    result = wrapper.get("result")
    if not isinstance(result, dict):
        return {"issues": ["missing_result_object"], "result": None}
    if set(result) != TOP_KEYS:
        issues.append(
            "top_keys:"
            f"missing={sorted(TOP_KEYS - set(result))},"
            f"extra={sorted(set(result) - TOP_KEYS)}"
        )
    if result.get("schema") != "interview-av-v3.0":
        issues.append("schema")
    if result.get("case_id") != task["task_id"]:
        issues.append("case_id")
    if result.get("condition") != task["condition"]:
        issues.append("condition")
    if result.get("media_processed") is not True:
        issues.append("media_not_processed")
    if result.get("prohibited_inference_detected") is not False:
        issues.append("prohibited_inference_flag")
    if PROHIBITED.search(json.dumps(result, ensure_ascii=False)):
        issues.append("prohibited_inference_text")
    receipt = wrapper.get("_receipt", {})
    if receipt.get("model_family") != "Gemini Flash":
        issues.append("model_family")
    if receipt.get("media_sha256") != task["media_sha256"]:
        issues.append("media_hash")
    if not receipt.get("conversation_url"):
        issues.append("conversation_url")
    if not receipt.get("completed_at"):
        issues.append("completed_at")

    atomic = result.get("atomic")
    if not isinstance(atomic, dict) or set(atomic) != {
        "audio",
        "visual",
        "temporal",
    }:
        issues.append("atomic_keys")
        return {"issues": issues, "result": result}
    audio = atomic.get("audio", {})
    visual = atomic.get("visual", {})
    temporal = atomic.get("temporal", {})
    composite = result.get("composite", {})
    if set(audio) != AUDIO_KEYS:
        issues.append("audio_keys")
    if set(visual) != VISUAL_KEYS:
        issues.append("visual_keys")
    if set(temporal) != {"order_pairs"}:
        issues.append("temporal_keys")
    if set(composite) != COMPOSITE_KEYS:
        issues.append("composite_keys")

    for key in (
        "pace",
        "pause_frequency",
        "disfluency_frequency",
        "prosodic_variability",
    ):
        if audio.get(key) not in LEVELS:
            issues.append(f"audio_enum:{key}")
    enum_issue(issues, "audio.speech", audio.get("speech"), SPEECH_VALUES)
    speaker_count = audio.get("speaker_count")
    if (
        not isinstance(speaker_count, int)
        or isinstance(speaker_count, bool)
        or speaker_count < 0
    ):
        issues.append("audio.speaker_count")
    excerpt = audio.get("excerpt")
    if not isinstance(excerpt, str):
        issues.append("audio.excerpt_type")
    elif len(tokens(excerpt)) > 20:
        issues.append("audio.excerpt_over_20_words")
    for key in ("person_visible", "face_visible", "upper_body_visible"):
        enum_issue(
            issues,
            f"visual.{key}",
            visual.get(key),
            VISIBILITY_VALUES,
        )
    if not isinstance(visual.get("displayed_text"), list) or not all(
        isinstance(value, str) for value in visual.get("displayed_text", [])
    ):
        issues.append("visual.displayed_text_type")
    enum_issue(
        issues,
        "composite.av_consistency",
        composite.get("av_consistency"),
        AV_CONSISTENCY_VALUES,
    )
    enum_issue(
        issues,
        "composite.synchronization",
        composite.get("synchronization"),
        SYNCHRONIZATION_VALUES,
    )
    enum_issue(
        issues,
        "composite.absent_modality",
        composite.get("absent_modality"),
        ABSENT_MODALITY_VALUES,
    )
    numeric_issue(
        issues,
        "composite.confidence",
        composite.get("confidence"),
        0.0,
        1.0,
    )
    lag = composite.get("lag_ms")
    if lag is not None:
        numeric_issue(issues, "composite.lag_ms", lag)
    duration = task["duration_sec"]
    for index, interval in enumerate(audio.get("target_active_intervals", [])):
        add_time_issue(
            issues, f"audio_interval[{index}].start", interval.get("start_sec"), duration
        )
        add_time_issue(
            issues, f"audio_interval[{index}].end", interval.get("end_sec"), duration
        )
        if (
            isinstance(interval.get("start_sec"), (int, float))
            and isinstance(interval.get("end_sec"), (int, float))
            and interval["end_sec"] < interval["start_sec"]
        ):
            issues.append(f"audio_interval[{index}]:reversed")
    for side in ("audio", "visual"):
        for index, event in enumerate(atomic.get(side, {}).get("events", [])):
            add_time_issue(
                issues, f"{side}_event[{index}].start", event.get("start_sec"), duration
            )
            add_time_issue(
                issues, f"{side}_event[{index}].end", event.get("end_sec"), duration
            )
            if not isinstance(event.get("event_id"), str) or not event.get(
                "event_id"
            ):
                issues.append(f"{side}_event[{index}]:event_id")
            if side == "visual":
                enum_issue(
                    issues,
                    f"visual_event[{index}].type",
                    event.get("type"),
                    EVENT_TYPES,
                )
            if not isinstance(event.get("description"), str):
                issues.append(f"{side}_event[{index}]:description")
    event_ids = {
        event.get("event_id")
        for side in ("audio", "visual")
        for event in atomic.get(side, {}).get("events", [])
        if isinstance(event, dict)
    }
    order_pairs = temporal.get("order_pairs", [])
    if not isinstance(order_pairs, list):
        issues.append("temporal.order_pairs_type")
        order_pairs = []
    for index, pair in enumerate(order_pairs):
        enum_issue(
            issues,
            f"order_pair[{index}].relation",
            pair.get("relation"),
            ORDER_RELATIONS,
        )
        for key in ("first_event_id", "second_event_id"):
            if pair.get(key) not in event_ids:
                issues.append(f"order_pair[{index}].{key}:unknown_event")
    evidence = result.get("evidence", [])
    if not isinstance(evidence, list):
        issues.append("evidence_type")
        evidence = []
    for index, item in enumerate(evidence):
        add_time_issue(
            issues, f"evidence[{index}]", item.get("timestamp_sec"), duration
        )
        if item.get("modality") not in {"audio", "visual", "audiovisual"}:
            issues.append(f"evidence[{index}]:modality")

    condition = task["condition"]
    if condition == "audio_only":
        if any(
            visual.get(key) != "not_observable"
            for key in ("person_visible", "face_visible", "upper_body_visible")
        ):
            issues.append("audio_only_visual_nonabstention")
        if visual.get("displayed_text") or visual.get("events"):
            issues.append("audio_only_visual_content")
        if any(item.get("modality") != "audio" for item in evidence):
            issues.append("audio_only_evidence_leak")
        if composite.get("av_consistency") != "not_applicable":
            issues.append("audio_only_composite")
        if composite.get("synchronization") != "not_observable":
            issues.append("audio_only_synchronization")
        if composite.get("absent_modality") not in {"video", "not_applicable"}:
            issues.append("audio_only_absent_modality")
    elif condition == "visual16_only":
        if audio.get("speech") != "not_observable":
            issues.append("visual_only_audio_nonabstention")
        if (
            audio.get("target_active_intervals")
            or audio.get("events")
            or audio.get("excerpt")
        ):
            issues.append("visual_only_audio_content")
        if any(audio.get(key) != "not_observable" for key in LEVEL_FIELD_NAMES):
            issues.append("visual_only_audio_labels")
        if any(item.get("modality") != "visual" for item in evidence):
            issues.append("visual_only_evidence_leak")
        if composite.get("av_consistency") != "not_applicable":
            issues.append("visual_only_composite")
        if composite.get("synchronization") != "not_observable":
            issues.append("visual_only_synchronization")
        if composite.get("absent_modality") not in {"audio", "not_applicable"}:
            issues.append("visual_only_absent_modality")
    else:
        evidence_modalities = {item.get("modality") for item in evidence}
        if not evidence_modalities.intersection({"audio", "audiovisual"}):
            issues.append("av_missing_audio_evidence")
        if not evidence_modalities.intersection({"visual", "audiovisual"}):
            issues.append("av_missing_visual_evidence")

    return {"issues": issues, "result": result}


LEVEL_FIELD_NAMES = (
    "pace",
    "pause_frequency",
    "disfluency_frequency",
    "prosodic_variability",
)


def load_wrapper(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    tasks = expected_tasks(manifest)
    turn_map = full_turns()
    rows = []
    missing = []
    for task in tasks:
        path = args.results / f"{task['task_id']}.json"
        if not path.exists():
            missing.append(task["task_id"])
            continue
        try:
            wrapper = load_wrapper(path)
            checked = validate_result(task, wrapper)
        except Exception as exc:
            checked = {
                "issues": [f"parse_error:{type(exc).__name__}:{exc}"],
                "result": None,
            }
        row = {**task, "path": str(path), **checked}
        if checked["result"] and task["program_id"] is not None:
            target = turn_map.get(
                (task["program_id"], task["target_turn_seq"]), ""
            )
            row["grounding"] = grounding(
                checked["result"]["atomic"]["audio"].get("excerpt", ""),
                target,
            )
        rows.append(row)

    v2_grounding = {}
    v2_timestamp_clean = {}
    for case in manifest["cases"]:
        case_id = case["case_id"]
        path = V2_RESULTS / f"{case_id}.json"
        if not path.exists():
            continue
        wrapper = json.loads(path.read_text(encoding="utf-8"))
        result = wrapper.get("result", {})
        target = turn_map.get(
            (
                case["source"]["program_id"],
                case["source"]["target_turn_seq"],
            ),
            "",
        )
        v2_grounding[case_id] = grounding(
            result.get("transcript_excerpt", ""), target
        )
        v2_timestamp_clean[case_id] = not wrapper.get("validation_issues", [])

    clean = [not row["issues"] for row in rows]
    primary = [row for row in rows if row["role"] != "hidden_mismatch"]
    av_rows = [
        row
        for row in rows
        if row["condition"] == "audiovisual"
        and row["role"] != "hidden_mismatch"
    ]
    failure_repairs = []
    sentinel_status = []
    for case_id in manifest["known_v2_failures"]:
        per_case = {
            row["condition"]: row
            for row in primary
            if row["case_id"] == case_id
        }
        audio_ok = per_case.get("audio_only", {}).get("grounding", {}).get(
            "grounded", False
        )
        av_ok = per_case.get("audiovisual", {}).get("grounding", {}).get(
            "grounded", False
        )
        failure_repairs.append(
            {
                "case_id": case_id,
                "v2_grounded": v2_grounding.get(case_id, {}).get(
                    "grounded", False
                ),
                "v3_audio_grounded": audio_ok,
                "v3_av_grounded": av_ok,
                "repaired": audio_ok and av_ok,
            }
        )
    for case_id in manifest["aligned_sentinels"]:
        row = next(
            (
                candidate
                for candidate in av_rows
                if candidate["case_id"] == case_id
            ),
            None,
        )
        sentinel_status.append(
            {
                "case_id": case_id,
                "v2_grounded": v2_grounding.get(case_id, {}).get(
                    "grounded", False
                ),
                "v3_av_grounded": (
                    row.get("grounding", {}).get("grounded", False)
                    if row
                    else False
                ),
            }
        )

    mismatch_rows = [row for row in rows if row["role"] == "hidden_mismatch"]
    mismatch_correct = [
        row["result"]["composite"].get("av_consistency") == "mismatched"
        for row in mismatch_rows
        if row["result"]
    ]
    matched_false_positives = [
        row["result"]["composite"].get("av_consistency") == "mismatched"
        for row in av_rows
        if row["result"]
    ]
    report = {
        "status": (
            "PARTIAL" if missing else "COMPLETE"
        ),
        "expected_tasks": len(tasks),
        "received_tasks": len(rows),
        "missing_tasks": missing,
        "schema_timestamp_clean": bootstrap_rate(clean),
        "primary_schema_timestamp_clean_count": sum(
            not row["issues"] for row in primary
        ),
        "primary_expected_count": 30,
        "issues": {
            row["task_id"]: row["issues"] for row in rows if row["issues"]
        },
        "v2_grounding": v2_grounding,
        "comparison": {
            "v2_selected_grounded_count": sum(
                row["grounded"] for row in v2_grounding.values()
            ),
            "v2_selected_case_count": len(v2_grounding),
            "v2_selected_timestamp_clean_count": sum(
                v2_timestamp_clean.values()
            ),
            "v3_audio_only_grounded_count": sum(
                row.get("grounding", {}).get("grounded", False)
                for row in primary
                if row["condition"] == "audio_only"
            ),
            "v3_av_grounded_count": sum(
                row.get("grounding", {}).get("grounded", False)
                for row in av_rows
            ),
            "v3_audio_only_condition_clean_count": sum(
                not row["issues"]
                for row in primary
                if row["condition"] == "audio_only"
            ),
            "v3_visual16_condition_clean_count": sum(
                not row["issues"]
                for row in primary
                if row["condition"] == "visual16_only"
            ),
            "v3_av_condition_clean_count": sum(
                not row["issues"] for row in av_rows
            ),
            "v3_true_pair_consistency_counts": dict(
                Counter(
                    row["result"]["composite"].get("av_consistency")
                    for row in av_rows
                    if row["result"]
                )
            ),
        },
        "failure_repairs": failure_repairs,
        "repaired_failure_count": sum(
            row["repaired"] for row in failure_repairs
        ),
        "sentinels": sentinel_status,
        "hidden_mismatch_detection": bootstrap_rate(mismatch_correct),
        "matched_false_mismatch": bootstrap_rate(matched_false_positives),
        "prohibited_inference_count": sum(
            any("prohibited_inference" in issue for issue in row["issues"])
            for row in rows
        ),
        "production_consumers": 0,
        "rows": rows,
    }
    hard_gates = {
        "all_30_primary_clean": (
            len(primary) == 30
            and all(not row["issues"] for row in primary)
        ),
        "seven_of_eight_failures_repaired": (
            report["repaired_failure_count"] >= 7
        ),
        "both_sentinels_grounded": (
            len(sentinel_status) == 2
            and all(row["v3_av_grounded"] for row in sentinel_status)
        ),
        "both_hidden_mismatches_detected": (
            len(mismatch_correct) == 2 and all(mismatch_correct)
        ),
        "at_most_one_false_mismatch": (
            len(matched_false_positives) == 10
            and sum(matched_false_positives) <= 1
        ),
        "zero_prohibited_inference": (
            report["prohibited_inference_count"] == 0
        ),
    }
    report["hard_gates"] = hard_gates
    report["decision"] = (
        "CONDITIONAL_GO_PERCEPTION_ONLY"
        if all(hard_gates.values())
        else "NO_GO_OR_INCOMPLETE"
    )
    atomic_json(OUTPUT_JSON, report)
    lines = [
        "# V3 diagnostic results",
        "",
        f"- Status: **{report['status']}**",
        f"- Receipts: **{len(rows)}/{len(tasks)}**",
        (
            "- Clean primary receipts: "
            f"**{report['primary_schema_timestamp_clean_count']}/30**"
        ),
        (
            "- Repaired known v2 semantic failures: "
            f"**{report['repaired_failure_count']}/8**"
        ),
        (
            "- Hidden mismatches detected: "
            f"**{sum(mismatch_correct)}/{len(mismatch_correct)}**"
        ),
        f"- Decision: **{report['decision']}**",
        "- Production consumers: **0**",
        (
            "- Stored-turn grounding, selected cases: "
            f"**{report['comparison']['v2_selected_grounded_count']}/"
            f"{report['comparison']['v2_selected_case_count']} in v2 -> "
            f"{report['comparison']['v3_av_grounded_count']}/10 in v3 A/V**"
        ),
        (
            "- Unavailable-modality discipline: "
            f"**{report['comparison']['v3_audio_only_condition_clean_count']}/10 "
            "audio-only; "
            f"{report['comparison']['v3_visual16_condition_clean_count']}/10 "
            "visual-only**"
        ),
        "",
        "## Hard gates",
        "",
    ]
    lines.extend(
        f"- {'PASS' if value else 'FAIL'} - `{name}`"
        for name, value in hard_gates.items()
    )
    lines.extend(["", "## Receipt issues", ""])
    if report["issues"]:
        for task_id, issues in report["issues"].items():
            lines.append(f"- `{task_id}`: {', '.join(issues)}")
    else:
        lines.append("- None.")
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "received": len(rows),
                "missing": len(missing),
                "clean_primary": report[
                    "primary_schema_timestamp_clean_count"
                ],
                "repaired_failures": report["repaired_failure_count"],
                "decision": report["decision"],
            },
            indent=2,
        )
    )
    if missing and not args.allow_partial:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
