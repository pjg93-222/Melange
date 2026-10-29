"""Freeze a conservative, current-source cohort without writing live manifests.

This can run while the atomic ASR manifest writer is active. Each input is read
once, parsed from those exact bytes, and retained with a content hash. Word
files are copied; WAVs remain original hash-bound files and are checked again
by acoustic continuity. No diagnostic pass establishes speaker identity,
complete turn boundaries, semantic review, or profile authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
from pathlib import Path

from audits.longform_collection_20260904 import audit_primary_transcript_quality as quality
from fec.speech import select_member_longform_profile_sources as selection
from fec.speech import source_media_recovery as SMR
from fec.speech.acquire_member_longform_audio import acquisition_matches_candidate, acquisition_matches_queue
from fec.speech.screen_member_longform_identity_cues import find_name_cues


ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / "audits/longform_collection_20260904"
INPUTS = {
    "roster": selection.DEFAULT_ROSTER,
    "roles": selection.DEFAULT_ROLES,
    "leader_sources": selection.DEFAULT_LEADER_SOURCES,
    "primary_queue": selection.DEFAULT_PRIMARY_QUEUE,
    "primary_acquisition": selection.DEFAULT_PRIMARY_ACQUISITION,
    "primary_transcripts": selection.DEFAULT_PRIMARY_TRANSCRIPTS,
    "leader_acquisition": selection.DEFAULT_LEADER_ACQUISITION,
    "leader_transcripts": selection.DEFAULT_LEADER_TRANSCRIPTS,
    "rejected_sources": AUDIT / "superseded_primary_sources.jsonl",
    "quality_holds": AUDIT / "quality_holds.jsonl",
}
BINDING_KEYS = ("member", "source_id", "wav_sha256", "transcript_sha256")
CURRENT_ROLE_AUTH_SCHEMA = "member-longform-current-role-source-authorization-v1"


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def rows_by_member(rows: list[dict], label: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        member = str(row["member"])
        if member in result:
            raise ValueError(f"duplicate member in {label}: {member}")
        result[member] = row
    return result


def validate_current_role_authorization(row: dict, role: dict | None) -> None:
    """An explicit source-bound P-7 exception never supplies a pre-role baseline."""
    if (row.get("schema") != CURRENT_ROLE_AUTH_SCHEMA
            or row.get("status") != "APPROVED_CURRENT_ROLE_CONDITIONED_SOURCE"
            or row.get("source_era") != "CURRENT_ROLE_CONDITIONED"
            or row.get("no_pre_role_baseline") is not True
            or row.get("decision_id") != "L-8/P-7"):
        raise ValueError("invalid current-role source authorization")
    for key in ("member", "source_id", "url", "wav_sha256", "recorded_at",
                "current_role_assumed_on", "decision_path", "decision_sha256"):
        if not isinstance(row.get(key), str) or not row[key].strip():
            raise ValueError("current-role authorization lacks " + key)
    for key in ("wav_sha256", "decision_sha256"):
        if len(row[key]) != 64 or any(char not in "0123456789abcdef" for char in row[key]):
            raise ValueError("invalid current-role authorization hash: " + key)
    if not role or row["current_role_assumed_on"] != role.get("current_role_assumed_on"):
        raise ValueError("current-role authorization cutoff differs from canonical role")
    if dt.date.fromisoformat(row["recorded_at"][:10]) < dt.date.fromisoformat(row["current_role_assumed_on"][:10]):
        raise ValueError("current-role authorization predates the current role")


def frozen_current_role_authorizations(run_root: Path, receipt: dict) -> dict[str, dict]:
    """Load only the hashed authorization input and copied decision bytes."""
    item = receipt["inputs"].get("current_role_authorizations")
    decisions = receipt.get("current_role_decisions") or {}
    if item is None:
        if decisions or receipt.get("contract", {}).get("current_role_conditioned_members"):
            raise ValueError("current-role scope has no frozen authorization input")
        return {}
    path = Path(item["snapshot_path"]).resolve()
    if not path.is_relative_to(run_root.resolve() / "inputs") or SMR.sha256_file(path) != item["sha256"]:
        raise ValueError("current-role authorization input hash/path mismatch")
    rows = rows_by_member(SMR.read_jsonl(path, required=True), "current-role authorizations")
    roles = json.loads(Path(receipt["inputs"]["roles"]["snapshot_path"]).read_text(encoding="utf-8-sig"))["members"]
    if set(decisions) != set(rows):
        raise ValueError("current-role decisions do not cover the frozen authorizations")
    if sorted(rows) != receipt.get("contract", {}).get("current_role_conditioned_members"):
        raise ValueError("current-role receipt scope differs from the frozen authorizations")
    result = {}
    for member, row in rows.items():
        validate_current_role_authorization(row, roles.get(member))
        bound = decisions[member]
        decision = Path(bound["snapshot_path"]).resolve()
        if (not decision.is_relative_to(run_root.resolve() / "decisions")
                or bound.get("sha256") != row["decision_sha256"]
                or SMR.sha256_file(decision) != row["decision_sha256"]):
            raise ValueError("current-role decision hash/path mismatch")
        result[member] = {**row, "decision_path": str(decision)}
    return result


def current_role_source_problem(member, acquisition, transcript, role, leader, authorization, *, acquisition_only):
    try:
        validate_current_role_authorization(authorization, role)
        if SMR.sha256_file(Path(authorization["decision_path"])) != authorization["decision_sha256"]:
            return "CURRENT_ROLE_DECISION_HASH_MISMATCH"
    except (ValueError, OSError):
        return "CURRENT_ROLE_AUTHORIZATION_INVALID"
    if authorization["member"] != member:
        return "CURRENT_ROLE_AUTHORIZATION_MEMBER_MISMATCH"
    if not leader or leader.get("status") == "HISTORICAL_LONGFORM_SOURCE_GAP":
        return "CURRENT_ROLE_REVIEWED_SOURCE_GAP"
    rows = (leader, acquisition) if acquisition_only else (leader, acquisition, transcript)
    for row in rows:
        if any(row.get(key) != authorization[key] for key in ("member", "source_id", "url", "source_era")):
            return "CURRENT_ROLE_AUTHORIZATION_SOURCE_MISMATCH"
        observed = str(row.get("recorded_at") or row.get("published") or "")[:10]
        if observed != authorization["recorded_at"][:10]:
            return "CURRENT_ROLE_RECORDING_DATE_BINDING_MISMATCH"
        if row.get("current_role_assumed_on") not in (None, role["current_role_assumed_on"]):
            return "CURRENT_ROLE_CUTOFF_BINDING_MISMATCH"
    for row in ((acquisition,) if acquisition_only else (acquisition, transcript)):
        if row.get("wav_sha256") != authorization["wav_sha256"]:
            return "CURRENT_ROLE_AUDIO_BINDING_MISMATCH"
    return None


def source_problem(member: str, acquisition: dict | None, transcript: dict | None,
                   queue: dict | None, role: dict | None, leader: dict | None,
                   rejected: list[dict], holds: list[dict], *, acquisition_only: bool = False,
                   current_role_authorization: dict | None = None) -> str | None:
    if not acquisition or acquisition.get("status") not in quality.SUCCESS:
        return "ACQUISITION_PENDING"
    if not acquisition_only and (not transcript or not selection.ready(transcript)):
        return "TRANSCRIPT_PENDING"
    if not acquisition_only and any(not transcript.get(key) or transcript.get(key) != acquisition.get(key)
           for key in ("member", "source_id", "wav_sha256")):
        return "STALE_TRANSCRIPT_SOURCE_BINDING"
    if current_role_authorization is not None:
        problem = current_role_source_problem(member, acquisition, transcript, role, leader,
                                              current_role_authorization, acquisition_only=acquisition_only)
        if problem:
            return problem
    elif role:
        if not leader or leader.get("status") == "HISTORICAL_LONGFORM_SOURCE_GAP":
            return "LEADERSHIP_PREROLE_SOURCE_GAP"
        if not acquisition_matches_candidate(acquisition, leader):
            return "LEADERSHIP_REVIEWED_SOURCE_MISMATCH"
        cutoff = str(role.get("current_role_assumed_on") or "")[:10]
        recorded = str(leader.get("recorded_at") or leader.get("published") or "")[:10]
        try:
            if dt.date.fromisoformat(recorded) >= dt.date.fromisoformat(cutoff):
                return "LEADERSHIP_PREROLE_CUTOFF_VIOLATION"
        except ValueError:
            return "LEADERSHIP_PREROLE_DATE_MISSING_OR_INVALID"
        for row in ((acquisition,) if acquisition_only else (acquisition, transcript)):
            row_date = str(row.get("recorded_at") or row.get("published") or "")[:10]
            if row_date != recorded:
                return "LEADERSHIP_RECORDING_DATE_BINDING_MISMATCH"
    elif not queue or not acquisition_matches_queue(acquisition, queue):
        return "CURRENT_PRIMARY_QUEUE_MISMATCH"
    member_rejected = [row for row in rejected if row.get("member") == member]
    if queue:
        for holder in (queue, queue.get("primary") or {}):
            member_rejected.extend({"source_id": value} for value in holder.get("rejected_source_ids") or [])
            member_rejected.extend({"url": value} for value in holder.get("rejected_urls") or [])
    if selection.rejected_source(acquisition, member_rejected):
        return "SUPERSEDED_OR_REJECTED_SOURCE"
    # Deliberately stricter than the exact-artifact selector: changing a held
    # transcript hash alone is not approval of the same underlying recording.
    if not acquisition_only and any(all(transcript.get(key) == hold.get(key) for key in ("member", "source_id", "wav_sha256"))
           for hold in holds):
        return "QUALITY_HOLD_REQUIRES_SEPARATE_REPAIR_REVIEW"
    return None


def build_snapshot(run_root: Path, paths: dict[str, Path], members: list[str] | None, *,
                   current_role_authorizations: Path | None = None) -> dict:
    run_root = run_root.resolve()
    # Never reuse a previous cohort, candidate cache, canonical directory, or receipt.
    if run_root.exists():
        raise ValueError(f"snapshot directory already exists: {run_root}")
    paths = dict(paths)
    if current_role_authorizations is not None:
        paths["current_role_authorizations"] = current_role_authorizations
    payloads = {key: path.read_bytes() for key, path in paths.items()}
    docs = {key: (json.loads(payload.decode("utf-8-sig")) if key in {"roster", "roles"}
                  else quality.jsonl(payload)) for key, payload in payloads.items()}
    roster = set(docs["roster"].get("members") or {})
    roles = docs["roles"].get("members") or {}
    if not roster or not set(roles) <= roster:
        raise ValueError("invalid roster or leadership registry")
    indexes = {key: rows_by_member(docs[key], key) for key in (
        "leader_sources", "primary_queue", "primary_acquisition", "primary_transcripts",
        "leader_acquisition", "leader_transcripts")}
    if set(indexes["primary_queue"]) != roster or set(indexes["leader_sources"]) != set(roles):
        raise ValueError("queue or leadership source roster mismatch")
    wanted = set(members) if members is not None else roster
    if not wanted or not wanted <= roster:
        raise ValueError("requested members absent from active roster")
    authorizations = rows_by_member(docs.get("current_role_authorizations") or [], "current-role authorizations")
    if not set(authorizations) <= wanted:
        raise ValueError("current-role authorization is outside the requested member scope")
    for member, authorization in authorizations.items():
        validate_current_role_authorization(authorization, roles.get(member))
    if any(any(not row.get(key) for key in BINDING_KEYS) for row in docs["quality_holds"]):
        raise ValueError("quality hold lacks exact artifact binding")
    run_root.mkdir(parents=True, exist_ok=False)
    (run_root / "inputs").mkdir()
    (run_root / "words").mkdir()
    input_receipts = {}
    for key, payload in payloads.items():
        target = run_root / "inputs" / (key + (".json" if key in {"roster", "roles"} else ".jsonl"))
        target.write_bytes(payload)
        input_receipts[key] = {"live_path": str(paths[key].resolve()), "snapshot_path": str(target),
                               "sha256": digest(payload)}
    decisions = {}
    for member, authorization in authorizations.items():
        source = Path(authorization["decision_path"])
        decision_bytes = source.read_bytes()
        if digest(decision_bytes) != authorization["decision_sha256"]:
            raise ValueError("current-role decision hash mismatch")
        target = run_root / "decisions" / (authorization["decision_sha256"] + ".decision")
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(decision_bytes)
        decisions[member] = {"source_path": str(source.resolve()), "snapshot_path": str(target),
                             "sha256": authorization["decision_sha256"]}
        authorizations[member] = {**authorization, "decision_path": str(target)}
    selected, diagnostics = [], []
    hash_cache: dict = {}
    for member in sorted(wanted):
        stream = "leader" if member in roles else "primary"
        acquired = indexes[stream + "_acquisition"].get(member)
        transcript = indexes[stream + "_transcripts"].get(member)
        problem = source_problem(member, acquired, transcript, indexes["primary_queue"].get(member),
                                 roles.get(member), indexes["leader_sources"].get(member),
                                 docs["rejected_sources"], docs["quality_holds"],
                                 current_role_authorization=authorizations.get(member))
        report = {"member": member, "stream": stream, "source_id": (acquired or {}).get("source_id")}
        if problem:
            diagnostics.append({**report, "status": "EXCLUDED", "reason": problem})
            continue
        try:
            acquired_era, transcript_era = acquired.get("source_era"), transcript.get("source_era")
            if acquired_era and transcript_era and acquired_era != transcript_era:
                raise ValueError("acquisition and transcript source eras disagree")
            selection.require_lineage(transcript, transcript, acquired, context=member, file_hashes=hash_cache)
            word_payload = Path(transcript["transcript"]).read_bytes()
            if digest(word_payload) != transcript["transcript_sha256"]:
                raise ValueError("word file changed while snapshotting")
            target = run_root / "words" / (digest(member.encode())[:16] + ".words.jsonl")
            target.write_bytes(word_payload)
            frozen = {**transcript, "transcript": str(target), "original_transcript": transcript["transcript"]}
            report["quality"] = quality.inspect(frozen, acquired)
            if report["quality"]["flags"]:
                diagnostics.append({**report, "status": "EXCLUDED", "reason": "DIAGNOSTIC_RISK_REQUIRES_REVIEW"})
                continue
            words = quality.jsonl(word_payload)
            cues = find_name_cues(words, member)
            if not cues:
                diagnostics.append({**report, "status": "EXCLUDED", "reason": "NO_IN_BAND_NAME_CUE"})
                continue
            record = selection.source_record(
                {**frozen, "cues": cues}, acquired,
                selection="immutable_ready_cohort_" + stream,
                source_era=("CURRENT_ROLE_CONDITIONED" if member in authorizations else
                            "PRE_CURRENT_LEADERSHIP_ROLE" if stream == "leader" else
                            acquired_era or transcript_era or "NOT_CURRENT_FORMAL_LEADERSHIP"),
            )
            record.update(snapshot_only=True, quality_scope="technical diagnostic screen; no semantic approval",
                          human_semantic_review=False, final_profile_authority=False)
            selected.append(record)
            diagnostics.append({**report, "status": "READY_CANDIDATE_ONLY"})
        except (Exception, SystemExit) as exc:
            diagnostics.append({**report, "status": "EXCLUDED", "reason": "PHYSICAL_OR_LINEAGE_VALIDATION_FAILED",
                                "error": str(exc)[:1000]})
    output = run_root / "ready_sources.jsonl"
    SMR.write_jsonl_atomic(output, selected)
    SMR.write_jsonl_atomic(run_root / "source_diagnostics.jsonl", diagnostics)
    for key, item in input_receipts.items():
        # An atomic live-manifest replacement is expected, not an error: this
        # receipt describes captured bytes, never claims the current global state.
        item["live_unchanged_at_finish"] = digest(paths[key].read_bytes()) == item["sha256"]
        if key not in {"primary_transcripts", "leader_transcripts"} and not item["live_unchanged_at_finish"]:
            raise ValueError(f"authoritative input changed during snapshot: {key}")
    receipt = {
        "schema": "member-longform-ready-source-snapshot-receipt-v1",
        "status": "PASS_IMMUTABLE_CANDIDATE_SNAPSHOT" if selected else "NO_READY_SOURCES",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "counts": {"requested": len(wanted), "ready": len(selected), "excluded": len(wanted) - len(selected),
                   "exclusion_reasons": dict(Counter(row["reason"] for row in diagnostics if "reason" in row))},
        "contract": {"canonical_manifests_modified": False, "profile_effect": "NONE",
                     "human_semantic_review": False, "speaker_identity_authority": False,
                     "word_files_copied": True, "audio_files_copied": False,
                     "audio_content_hashes_verified": True, "leader_pre_current_role_only": not bool(authorizations),
                     "current_role_conditioned_members": sorted(authorizations),
                     "current_role_sources_are_baseline": False,
                     "quality_pass_is_technical_not_semantic": True,
                     "held_recording_not_cleared_by_new_transcript_hash": True,
                     "retry_sources_not_in_snapshot_scope": True},
        "inputs": input_receipts,
        "current_role_decisions": decisions,
        "code": {"snapshot_sha256": SMR.sha256_file(Path(__file__)),
                 "quality_audit_sha256": SMR.sha256_file(Path(quality.__file__)),
                 "source_selector_sha256": SMR.sha256_file(Path(selection.__file__))},
        "output": {"path": str(output), "sha256": SMR.sha256_file(output)},
        "diagnostics": {"path": str(run_root / "source_diagnostics.jsonl"),
                        "sha256": SMR.sha256_file(run_root / "source_diagnostics.jsonl")},
    }
    SMR.write_json_atomic(run_root / "snapshot.receipt.json", receipt)
    return receipt


def verify_snapshot(run_root: Path) -> dict:
    """Verify only frozen inputs; live ASR progress cannot invalidate this cohort."""
    run_root = run_root.resolve()
    receipt = json.loads((run_root / "snapshot.receipt.json").read_text(encoding="utf-8"))
    if (receipt.get("schema") != "member-longform-ready-source-snapshot-receipt-v1"
            or receipt.get("status") != "PASS_IMMUTABLE_CANDIDATE_SNAPSHOT"):
        raise ValueError("snapshot receipt does not authorize candidate-only processing")
    paths = [(run_root / "ready_sources.jsonl", receipt.get("output") or {}),
             (run_root / "source_diagnostics.jsonl", receipt.get("diagnostics") or {})]
    for path, item in paths:
        if Path(str(item.get("path") or "")).resolve() != path or SMR.sha256_file(path) != item.get("sha256"):
            raise ValueError(f"snapshot artifact hash/path mismatch: {path}")
    for item in receipt["inputs"].values():
        path = Path(item["snapshot_path"]).resolve()
        if not path.is_relative_to(run_root / "inputs") or SMR.sha256_file(path) != item["sha256"]:
            raise ValueError("frozen input hash/path mismatch")
    frozen_current_role_authorizations(run_root, receipt)
    rows = SMR.read_jsonl(run_root / "ready_sources.jsonl", required=True)
    if len(rows) != receipt["counts"]["ready"] or len(rows_by_member(rows, "snapshot")) != len(rows):
        raise ValueError("snapshot cohort count mismatch")
    for row in rows:
        path = Path(row["transcript"]).resolve()
        if not path.is_relative_to(run_root / "words") or SMR.sha256_file(path) != row["transcript_sha256"]:
            raise ValueError("snapshot word file hash/path mismatch")
        if row.get("status") != "SELECTED_HARD_NAME_CUE_CANDIDATE" or not row.get("snapshot_only"):
            raise ValueError("invalid snapshot candidate status")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--run-root", type=Path)
    target.add_argument("--verify-run-root", type=Path)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--member", action="append")
    scope.add_argument("--all-ready", action="store_true")
    parser.add_argument("--current-role-authorizations", type=Path,
                        help="source-bound L-8/P-7 authorization JSONL; the pre-role default stays strict")
    args = parser.parse_args()
    if args.verify_run_root:
        if args.member or args.all_ready or args.current_role_authorizations:
            parser.error("verification does not accept a new member scope")
        receipt = verify_snapshot(args.verify_run_root)
        print(json.dumps({"status": "PASS_FROZEN_INPUT_BINDINGS_ONLY", "counts": receipt["counts"]}))
        return 0
    if not args.member and not args.all_ready:
        parser.error("snapshot creation requires explicit --member or --all-ready")
    receipt = build_snapshot(args.run_root, INPUTS, args.member,
                             current_role_authorizations=args.current_role_authorizations)
    print(json.dumps({"status": receipt["status"], "counts": receipt["counts"], "output": receipt["output"]}))
    return 0 if receipt["counts"]["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
