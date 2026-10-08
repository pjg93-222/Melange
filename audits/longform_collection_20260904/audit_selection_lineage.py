"""Snapshot current source/transcript/cue linkage without updating the pipeline."""
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DATA = ROOT / "data/speech"
MEDIA = Path("C:/melange-data")


def rows(path):
    return {r["member"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if r.get("member")} if path.is_file() else {}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mismatch(left, right, keys):
    if not left or not right:
        return ["missing_row"]
    return [key for key in keys if left.get(key) != right.get(key)]


def main():
    names = {
        "primary": "member_longform",
        "retry1": "member_longform_no_cue_retry",
        "retry2": "member_longform_no_cue_retry2",
        "leadership": "member_leadership_prerole",
    }
    streams = {}
    for label, stem in names.items():
        paths = {"acquisition": DATA / f"{stem}_acquisition_v1.jsonl",
                 "transcripts": MEDIA / f"{stem}_transcripts_v1.jsonl",
                 "cues": MEDIA / f"{stem}_identity_cues_v1.jsonl"}
        stream = {kind: rows(path) for kind, path in paths.items()}
        stream["paths"] = paths
        streams[label] = stream
    roles = json.loads((DATA / "member_leadership_role_cutoffs_v1.json").read_text(encoding="utf-8"))["members"]
    selection = rows(DATA / "member_longform_profile_source_selection_v1.jsonl")
    checks = {}
    for label, stream in streams.items():
        acq, trans, cues = (stream[k] for k in ("acquisition", "transcripts", "cues"))
        linkages = []
        for member in sorted(set(acq) | set(trans) | set(cues)):
            a, t, c = acq.get(member), trans.get(member), cues.get(member)
            linkages.append({
                "member": member,
                "acquisition_source_id": (a or {}).get("source_id"),
                "transcript_source_id": (t or {}).get("source_id"),
                "cue_source_id": (c or {}).get("source_id"),
                "transcript_status": (t or {}).get("status"),
                "cue_status": (c or {}).get("status"),
                "transcript_vs_acquisition": mismatch(t, a, ("source_id", "wav_sha256")),
                "cue_vs_acquisition": mismatch(c, a, ("source_id", "wav_sha256")),
                "cue_vs_transcript": mismatch(c, t, ("source_id", "wav_sha256", "transcript", "transcript_sha256")),
            })
        receipt_checks = {}
        for kind, input_kind, input_key in (("transcripts", "acquisition", "acquisition_sha256"), ("cues", "transcripts", "transcripts_sha256")):
            path = stream["paths"][kind]
            receipt_path = path.with_suffix(".receipt.json")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else {}
            receipt_checks[kind] = {
                "receipt_status": receipt.get("status"),
                "input_hash_current": (receipt.get("inputs") or {}).get(input_key) == sha(stream["paths"][input_kind]),
                "output_hash_current": (receipt.get("output") or {}).get("sha256") == sha(path),
            }
        checks[label] = {
            "paths": {key: str(value) for key, value in stream["paths"].items()},
            "rows": {key: len(stream[key]) for key in ("acquisition", "transcripts", "cues")},
            "transcript_statuses": dict(Counter(r.get("status") for r in trans.values())),
            "cue_statuses": dict(Counter(r.get("status") for r in cues.values())),
            "transcript_acquisition_mismatch_count": sum(bool(r["transcript_vs_acquisition"]) for r in linkages),
            "cue_acquisition_mismatch_count": sum(bool(r["cue_vs_acquisition"]) for r in linkages),
            "cue_transcript_mismatch_count": sum(bool(r["cue_vs_transcript"]) for r in linkages),
            "receipts": receipt_checks,
            "mismatches": [r for r in linkages if r["transcript_vs_acquisition"] or r["cue_vs_acquisition"] or r["cue_vs_transcript"]],
        }
    dangerous = []
    for member in sorted(selection):
        labels = ["leadership"] if member in roles else ["primary", "retry1", "retry2"]
        for label in labels:
            stream = streams[label]
            cue = stream["cues"].get(member)
            if not cue or cue.get("status") != "HARD_IN_BAND_NAME_CUE_CANDIDATE" or not cue.get("cues"):
                continue
            acq, trans = stream["acquisition"].get(member), stream["transcripts"].get(member)
            mismatch_keys = mismatch(cue, acq, ("source_id", "wav_sha256"))
            if mismatch_keys:
                dangerous.append({"member": member, "would_select_stream": label, "cue_source_id": cue.get("source_id"), "acquisition_source_id": (acq or {}).get("source_id"), "mismatches": mismatch_keys})
            break
    result = {
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Read-only manifest lineage check. Does not perform transcription, screening, selection, review, or promotion.",
        "existing_selected_statuses": dict(Counter(r.get("status") for r in selection.values())),
        "streams": checks,
        "unsafe_selector_choices_if_run_without_refresh_count": len(dangerous),
        "unsafe_selector_choices_if_run_without_refresh": dangerous,
    }
    (OUT / "selection_lineage_inventory.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"snapshot_at": result["snapshot_at"], "streams": {key: {k: v for k, v in value.items() if k not in ("mismatches", "paths")} for key, value in checks.items()}, "unsafe_selector_choices": len(dangerous)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
