"""Compare a systematic six-item repeat with the primary Gemini ratings."""

from __future__ import annotations

import json
import statistics
from pathlib import Path


HERE = Path(__file__).resolve().parent
PRIMARY = HERE / "results"
REPEAT = HERE / "results_repeat"
OUT = HERE / "reliability_report.json"
FIELDS = (
    "pace",
    "pause_frequency",
    "disfluency_frequency",
    "prosodic_variability",
    "turn_competition",
    "response_directness",
)
IDS = ("P001", "P006", "P011", "P016", "P021", "P026")


def load(directory: Path, pilot_id: str) -> dict:
    return json.loads((directory / f"{pilot_id}.json").read_text(encoding="utf-8"))


def identity_value(row: dict) -> str:
    return "ABSTAIN" if row.get("abstained") else str(row.get("candidate_choice"))


def main() -> int:
    rows = []
    categorical_total = 0
    categorical_agree = 0
    identity_agree = 0
    speaker_exact = 0
    speaker_within_one = 0
    confidence_deltas = []

    for pilot_id in IDS:
        first = load(PRIMARY, pilot_id)
        second = load(REPEAT, pilot_id)
        field_agreement = {
            field: first["observable_delivery"][field]
            == second["observable_delivery"][field]
            for field in FIELDS
        }
        categorical_total += len(FIELDS)
        categorical_agree += sum(field_agreement.values())
        same_identity = identity_value(first) == identity_value(second)
        identity_agree += same_identity
        speaker_delta = abs(
            int(first["estimated_speaker_count"])
            - int(second["estimated_speaker_count"])
        )
        speaker_exact += speaker_delta == 0
        speaker_within_one += speaker_delta <= 1
        confidence_deltas.append(
            abs(
                float(first.get("identity_confidence") or 0)
                - float(second.get("identity_confidence") or 0)
            )
        )
        rows.append(
            {
                "pilot_id": pilot_id,
                "primary_identity": identity_value(first),
                "repeat_identity": identity_value(second),
                "identity_agreement": same_identity,
                "primary_speaker_count": first["estimated_speaker_count"],
                "repeat_speaker_count": second["estimated_speaker_count"],
                "delivery_field_agreement": field_agreement,
            }
        )

    report = {
        "schema": "gemini-congressional-av-pilot-reliability-v1",
        "status": "RESEARCH_CANDIDATE_NOT_CONSUMED",
        "selection": {
            "ids": list(IDS),
            "method": "systematic every-fifth item beginning at P001",
            "caveat": (
                "Repeat subset was formalized after the primary run and is "
                "therefore an exploratory, not preregistered, reliability check."
            ),
        },
        "repeat_n": len(IDS),
        "identity_choice_agreement_n": identity_agree,
        "identity_choice_agreement": round(identity_agree / len(IDS), 6),
        "delivery_categorical_agreement_n": categorical_agree,
        "delivery_categorical_total_n": categorical_total,
        "delivery_categorical_agreement": round(
            categorical_agree / categorical_total, 6
        ),
        "speaker_count_exact_agreement_n": speaker_exact,
        "speaker_count_within_one_n": speaker_within_one,
        "identity_confidence_mean_absolute_delta": round(
            statistics.mean(confidence_deltas), 6
        ),
        "production_consumers": 0,
        "items": rows,
    }
    OUT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "repeat_n": report["repeat_n"],
                "identity_choice_agreement": report["identity_choice_agreement"],
                "delivery_categorical_agreement": report[
                    "delivery_categorical_agreement"
                ],
                "speaker_count_exact_agreement_n": report[
                    "speaker_count_exact_agreement_n"
                ],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

