"""Preserve member-scoped exclusions for the before-reconciliation primaries."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fec.speech.acquire_member_longform_audio import acquisition_matches_queue, candidate_source_key


def read(path):
    return {row["member"]: row for row in map(json.loads, path.read_text(encoding="utf-8").splitlines())}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = Path(__file__).resolve().parent
    before_path = folder / "before_reconciliation/member_longform_acquisition_v1.jsonl"
    queue_path = ROOT / "data/speech/member_longform_acquisition_queue_v1.jsonl"
    before, queue = read(before_path), read(queue_path)
    if set(before) != set(queue):
        raise SystemExit("before/current member rosters differ")
    output = []
    for member, original in sorted(before.items()):
        current = queue[member]
        if acquisition_matches_queue(original, current):
            continue
        primary = current["primary"]
        if not primary.get("reviewed_replacement"):
            raise SystemExit(f"replacement not reviewed: {member}")
        output.append({
            "schema": "member-longform-superseded-primary-source-v1",
            "status": "SUPERSEDED_PRIMARY_PENDING_REVIEW",
            "member": member,
            **{key: original.get(key) for key in ("source_id", "extractor_id", "url", "audio_url", "title", "channel", "wav", "wav_sha256") if original.get(key) is not None},
            "superseded_as": "PRIMARY_SOURCE",
            "replacement_source_id": candidate_source_key(primary),
            "replacement_url": primary.get("url"),
            "review_reason": primary.get("review_reason"),
            "exclusion_scope": "Do not reselect this member's superseded primary through a retry until separately reviewed. Supersession does not by itself establish a wrong speaker; reasons also include format and context.",
            "media_preserved": True,
            "identity_authority": False,
            "semantic_authority": False,
        })
    out_path = folder / "superseded_primary_sources.jsonl"
    out_path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in output), encoding="utf-8")
    receipt = {
        "generated_at": datetime.now(timezone.utc).isoformat(), "count": len(output),
        "inputs": {"before_acquisition_sha256": digest(before_path), "current_queue_sha256": digest(queue_path)},
        "output_sha256": digest(out_path), "profile_or_review_effect": "NONE",
    }
    (folder / "superseded_primary_sources.receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
