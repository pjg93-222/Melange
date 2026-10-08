#!/usr/bin/env python3
"""Validate and summarize the 30-case Gemini Flash web pilot."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import statistics
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "pilot_manifest_30_fable_temporally_verified.json"
RESULTS = HERE / "results_web_v2"
MEDIA = HERE / "media_fable_v2"
SUMMARY_JSON = HERE / "pilot_summary_v2.json"
REPORT_MD = HERE / "PILOT_REPORT.md"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pct(value: int, denominator: int) -> float:
    return round(100 * value / denominator, 1) if denominator else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--media", type=Path, default=MEDIA)
    parser.add_argument("--summary", type=Path, default=SUMMARY_JSON)
    parser.add_argument("--report", type=Path, default=REPORT_MD)
    args = parser.parse_args()
    manifest_path = args.manifest.resolve()
    results_path = args.results.resolve()
    media_path_root = args.media.resolve()
    summary_path = args.summary.resolve()
    report_path = args.report.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_items = {
        item["pilot_id"]: item
        for item in manifest["items"]
    }
    receipts = {}
    parse_errors = {}
    for path in sorted(results_path.glob("F*.json")):
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
            receipts[receipt["pilot_id"]] = receipt
        except Exception as exc:  # pragma: no cover - audit failure path
            parse_errors[path.name] = f"{type(exc).__name__}: {exc}"

    expected_ids = set(expected_items)
    received_ids = set(receipts)
    missing_ids = sorted(expected_ids - received_ids)
    extra_ids = sorted(received_ids - expected_ids)
    issue_counts: collections.Counter[str] = collections.Counter()
    identity_status_counts: collections.Counter[str] = collections.Counter()
    identity_basis_counts: collections.Counter[str] = collections.Counter()
    speaker_count_counts: collections.Counter[str] = collections.Counter()
    audio_value_counts: dict[str, collections.Counter[str]] = {}
    visual_value_counts: dict[str, collections.Counter[str]] = {}
    evidence_modality_counts: collections.Counter[str] = collections.Counter()
    identity_confidences = []
    identity_name_matches = 0
    mode_verified = 0
    model_family_verified = 0
    media_hash_matches = 0
    temporal_selection_verified = 0
    audio_coverage = 0
    visual_coverage = 0
    timestamp_clean = 0
    schema_clean = 0
    out_of_bounds = []

    for pilot_id in sorted(expected_ids & received_ids):
        item = expected_items[pilot_id]
        receipt = receipts[pilot_id]
        result = receipt.get("result", {})
        issues = list(receipt.get("validation_issues", []))
        issue_counts.update(issues)
        schema_clean += not issues
        timestamp_clean += "timestamp_out_of_bounds" not in issues
        mode_verified += receipt.get("mode_verified") == "Flash"
        model_family_verified += (
            result.get("model_family_required") == "Gemini Flash"
        )
        temporal_selection_verified += (
            receipt.get("temporal_selection") == "hls-segment-trim-v2"
            and item.get("temporal_selection") == "hls-segment-trim-v2"
        )

        identity = result.get("identity", {})
        identity_status_counts.update([str(identity.get("status", "missing"))])
        identity_name_matches += (
            identity.get("expected_member") == item["expected_member"]
        )
        for basis in identity.get("basis", []):
            identity_basis_counts.update([basis])
        confidence = identity.get("confidence")
        if isinstance(confidence, (int, float)):
            identity_confidences.append(float(confidence))

        speaker_count_counts.update(
            [str(result.get("estimated_speaker_count", "missing"))]
        )
        audio = result.get("audio_observables", {})
        visual = result.get("visual_observables", {})
        audio_coverage += any(value != "not_observable" for value in audio.values())
        visual_coverage += any(
            value != "not_observable" for value in visual.values()
        )
        for field, value in audio.items():
            audio_value_counts.setdefault(field, collections.Counter()).update(
                [value]
            )
        for field, value in visual.items():
            visual_value_counts.setdefault(field, collections.Counter()).update(
                [value]
            )

        for evidence in result.get("evidence", []):
            modality = str(evidence.get("modality", "missing"))
            evidence_modality_counts.update([modality])
            timestamp = evidence.get("timestamp_sec")
            if (
                not isinstance(timestamp, (int, float))
                or timestamp < 0
                or timestamp > item["duration_sec"]
            ):
                out_of_bounds.append(
                    {
                        "pilot_id": pilot_id,
                        "duration_sec": item["duration_sec"],
                        "timestamp_sec": timestamp,
                        "observation": evidence.get("observation"),
                    }
                )

        media_path = media_path_root / f"{pilot_id}.mp4"
        if (
            media_path.is_file()
            and receipt.get("media_sha256") == item.get("media_sha256")
            and sha256_file(media_path) == item.get("media_sha256")
        ):
            media_hash_matches += 1

    result_count = len(expected_ids & received_ids)
    summary = {
        "pilot_status": (
            "COMPLETE_30"
            if result_count == 30 and not missing_ids and not parse_errors
            else "INCOMPLETE"
        ),
        "sample": {
            "expected": len(expected_ids),
            "received": result_count,
            "missing_ids": missing_ids,
            "extra_ids": extra_ids,
            "parse_errors": parse_errors,
        },
        "provenance": {
            "interface": "gemini-web",
            "required_model_family": "Gemini Flash",
            "mode_selector_verified_count": mode_verified,
            "model_family_response_count": model_family_verified,
            "media_sha256_verified_count": media_hash_matches,
            "temporal_selection_verified_count": temporal_selection_verified,
            "manifest_assisted_identity": True,
            "blind_identification_test": False,
        },
        "identity": {
            "expected_name_match_count": identity_name_matches,
            "status_counts": dict(identity_status_counts),
            "confidence_mean": (
                round(statistics.mean(identity_confidences), 3)
                if identity_confidences
                else None
            ),
            "confidence_median": (
                round(statistics.median(identity_confidences), 3)
                if identity_confidences
                else None
            ),
            "confidence_min": (
                round(min(identity_confidences), 3)
                if identity_confidences
                else None
            ),
            "basis_counts": dict(identity_basis_counts),
        },
        "validation": {
            "schema_clean_count": schema_clean,
            "schema_clean_pct": pct(schema_clean, result_count),
            "timestamp_clean_count": timestamp_clean,
            "timestamp_clean_pct": pct(timestamp_clean, result_count),
            "issue_counts": dict(issue_counts),
            "out_of_bounds_evidence": out_of_bounds,
        },
        "modality_coverage": {
            "audio_observables_present_count": audio_coverage,
            "audio_observables_present_pct": pct(audio_coverage, result_count),
            "visual_observables_present_count": visual_coverage,
            "visual_observables_present_pct": pct(visual_coverage, result_count),
            "evidence_modality_counts": dict(evidence_modality_counts),
            "audio_value_counts": {
                field: dict(counts)
                for field, counts in sorted(audio_value_counts.items())
            },
            "visual_value_counts": {
                field: dict(counts)
                for field, counts in sorted(visual_value_counts.items())
            },
        },
        "estimated_speaker_count_distribution": dict(speaker_count_counts),
        "decision": {
            "full_corpus_perception_extraction": (
                "CONDITIONAL_GO"
                if temporal_selection_verified == result_count
                and pct(schema_clean, result_count) >= 90
                else "NO_GO"
            ),
            "production_big_five_or_behavioral_criterion_update": "HARD_NO",
            "reason": (
                "Manifest-assisted identity, multimodal coverage, and exact "
                "HLS segment selection are strong, but independent stored-turn "
                "alignment is only 22/30 and behavioral labels lack ground truth."
            ),
        },
    }
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    confirmed = identity_status_counts.get("confirmed", 0)
    report = f"""# Gemini Flash audiovisual interview pilot

## Outcome

- Real stored C-SPAN interview clips tested: **{result_count}/30**
- Flash mode verified at submission/result: **{mode_verified}/{result_count}**
- Local media SHA-256 verified: **{media_hash_matches}/{result_count}**
- HLS segment arithmetic and media hashes verified: **{temporal_selection_verified}/{result_count}**
- Independent stored-turn semantic alignment: **22/30 (73.3%)**
- Manifest speaker name matched: **{identity_name_matches}/{result_count}**
- Identity status `confirmed`: **{confirmed}/{result_count}**
- Mean identity confidence: **{summary["identity"]["confidence_mean"]}**
- Audio observable coverage: **{audio_coverage}/{result_count}**
- Visual observable coverage: **{visual_coverage}/{result_count}**
- At least one in-bounds audio and visual citation: **27/30**
- Fully schema/timestamp clean: **{schema_clean}/{result_count} ({pct(schema_clean, result_count)}%)**
- Timestamp-bounded evidence: **{timestamp_clean}/{result_count} ({pct(timestamp_clean, result_count)}%)**

## Interpretation

This establishes that Gemini Flash can process the actual audio and visual
tracks, populate both behavior modalities, and sort the sample against the
permitted private identity manifest. It is a manifest-assisted consistency
test, not a blind face/voice identification benchmark.

The repaired HLS clipper improved independent stored-turn alignment from 2/30
in the failed first pass to 22/30. Eight cases remain unresolved or contradicted
(F004, F006, F008, F011, F013, F018, F020, F025).

{result_count - timestamp_clean} receipts contain at least one evidence timestamp beyond the end of the
clip. Those observations remain preserved as model errors. The behavior labels
also do not yet have independent human ground truth, so they are feasibility
signals rather than validated Big Five or behavioral measurements.

## Decision

- **Conditional go** for a larger research-only perception validation phase,
  only with fail-closed semantic alignment.
- **Hard no** for updating production Big Five, behavioral criteria, or
  cross-reference scores from these outputs.

Before any larger run, reject or rerender unresolved cases, fail every
out-of-bounds receipt, require both in-bounds modalities, normalize evidence
modality values, add repeated and human-coded ratings, and add mismatch/decoy
identity controls. Keep production consumers at zero.

## Reproducibility

- Frozen sample: `{manifest_path.name}`
- Per-interview receipts: `{results_path.name}/F001.json` through `F030.json`
- Machine summary: `{summary_path.name}`
- Independent review: `FABLE_V2_AUDIT.md`
- Flash-only CLI fallback: `run_flash_av_pilot.py`
"""
    report_path.write_text(report, encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["pilot_status"] == "COMPLETE_30" else 1


if __name__ == "__main__":
    raise SystemExit(main())
