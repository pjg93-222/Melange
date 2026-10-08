"""Validate and score completed Gemini pilot JSON files."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.json"
RESULTS = HERE / "results"
REPORT = HERE / "pilot_report.json"
ALLOWED = {"low", "medium", "high", "not_observable"}
DELIVERY_FIELDS = {
    "pace",
    "pause_frequency",
    "disfluency_frequency",
    "prosodic_variability",
    "turn_competition",
    "response_directness",
}


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total <= 0:
        return None
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = (
        z
        * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total)
        / denominator
    )
    return [round(max(0.0, center - half), 6), round(min(1.0, center + half), 6)]


def validate(
    result: dict, expected_id: str, candidates: list[str], duration_sec: float
) -> list[str]:
    errors: list[str] = []
    if result.get("pilot_id") != expected_id:
        errors.append("pilot_id")
    if not isinstance(result.get("media_processed"), bool):
        errors.append("media_processed")
    if not isinstance(result.get("estimated_speaker_count"), int):
        errors.append("estimated_speaker_count")
    fraction = result.get("dominant_speaker_fraction")
    if not isinstance(fraction, (int, float)) or not 0 <= fraction <= 1:
        errors.append("dominant_speaker_fraction")
    if not isinstance(result.get("abstained"), bool):
        errors.append("abstained")
    choice = result.get("candidate_choice")
    if result.get("abstained") is False and choice not in candidates:
        errors.append("candidate_choice")
    delivery = result.get("observable_delivery")
    if not isinstance(delivery, dict):
        errors.append("observable_delivery")
    else:
        if set(delivery) != DELIVERY_FIELDS:
            errors.append("observable_delivery_fields")
        if any(value not in ALLOWED for value in delivery.values()):
            errors.append("observable_delivery_values")
    evidence = result.get("evidence")
    if not isinstance(evidence, list):
        errors.append("evidence")
    else:
        for row in evidence:
            if not isinstance(row, dict) or not isinstance(
                row.get("timestamp_sec"), (int, float)
            ) or not isinstance(row.get("observation"), str):
                errors.append("evidence_row")
                break
            if not 0 <= row["timestamp_sec"] <= duration_sec:
                errors.append("evidence_timestamp_out_of_range")
                break
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--out", type=Path, default=REPORT)
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = []
    for item in manifest["items"]:
        path = args.results / f"{item['pilot_id']}.json"
        if not path.exists():
            rows.append({**item, "result": None, "validation_errors": ["missing"]})
            continue
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
            errors = validate(
                result,
                item["pilot_id"],
                item["candidate_set"],
                item["duration_sec"],
            )
        except Exception as exc:
            result = None
            errors = [f"parse:{type(exc).__name__}"]
        rows.append({**item, "result": result, "validation_errors": errors})

    valid = [row for row in rows if not row["validation_errors"]]
    processed = [
        row for row in valid if row["result"] and row["result"]["media_processed"]
    ]
    attempted_identity = [
        row
        for row in processed
        if not row["result"]["abstained"] and row["result"].get("candidate_choice")
    ]
    matches = [
        row
        for row in attempted_identity
        if row["result"]["candidate_choice"] == row["expected_member"]
    ]
    grounded = [
        row
        for row in processed
        if row["result"].get("evidence")
        and all(
            0 <= evidence["timestamp_sec"] <= row["duration_sec"]
            for evidence in row["result"]["evidence"]
        )
    ]

    report = {
        "schema": "gemini-congressional-av-pilot-report-v1",
        "status": "RESEARCH_CANDIDATE_NOT_CONSUMED",
        "sample_n": len(rows),
        "valid_schema_n": len(valid),
        "media_processed_n": len(processed),
        "timestamp_grounded_n": len(grounded),
        "identity_attempted_n": len(attempted_identity),
        "identity_recorded_label_match_n": len(matches),
        "identity_recorded_label_agreement": (
            round(len(matches) / len(attempted_identity), 6)
            if attempted_identity
            else None
        ),
        "identity_recorded_label_agreement_wilson95": wilson(
            len(matches), len(attempted_identity)
        ),
        "identity_recorded_label_match_full_cohort_rate": round(
            len(matches) / len(rows), 6
        ),
        "identity_recorded_label_match_full_cohort_wilson95": wilson(
            len(matches), len(rows)
        ),
        "abstention_n": sum(
            1 for row in processed if row["result"].get("abstained")
        ),
        "out_of_range_timestamp_item_n": sum(
            1
            for row in rows
            if "evidence_timestamp_out_of_range" in row["validation_errors"]
        ),
        "gates": {
            "media_processing_27_of_30": len(processed) >= 27,
            "schema_27_of_30": len(valid) >= 27,
            "timestamp_grounding_24_of_30": len(grounded) >= 24,
            "recorded_label_match_24_of_30": len(matches) >= 24,
        },
        "production_consumers": 0,
        "limitations": [
            "Expected identity labels are weak machine-caption/folder labels, not human gold.",
            "A Gemini disagreement cannot relabel a recording.",
            "Observable delivery ratings are not personality or Big Five measurements.",
            "Audio-only results do not establish audiovisual validity.",
            "The five-name candidate set always contains the recorded label.",
            "Speech content and contextual clues were not masked, so this is not a voice-only test.",
        ],
        "items": [
            {
                "pilot_id": row["pilot_id"],
                "expected_member": row["expected_member"],
                "validation_errors": row["validation_errors"],
                "result": row["result"],
            }
            for row in rows
        ],
    }
    args.out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: report[key] for key in report if key.endswith("_n")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
