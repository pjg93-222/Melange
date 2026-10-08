"""Read-only transcript quality diagnostics; flags do not adjudicate speakers or meaning."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import wave


ROOT = Path(__file__).resolve().parents[2]
ACQUISITION = ROOT / "data/speech/member_longform_acquisition_v1.jsonl"
TRANSCRIPTS = Path("C:/melange-data/member_longform_transcripts_v1.jsonl")
OUTPUT = Path(__file__).with_name("transcript_quality_snapshot.json")
SUCCESS = {"ACQUIRED_IDENTITY_VERIFIED", "ACQUIRED_IDENTITY_UNVERIFIED"}
# Match the complete-turn classifier's existing physical-input tolerance.
# A duration-scaled allowance can hide seconds of words beyond the recording.
TIMESTAMP_END_TOLERANCE_SECONDS = 0.1


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def jsonl(payload):
    return [json.loads(line) for line in payload.decode("utf-8-sig").splitlines() if line.strip()]


def timestamp(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def inspect(row, acquisition):
    result = {"member": row["member"], "source_id": row.get("source_id"),
              "manifest_status": row.get("status"), "flags": []}
    flags = result["flags"]
    def flag(code, detail):
        flags.append({"code": code, "detail": detail})
    if not acquisition or acquisition.get("status") not in SUCCESS:
        result["binding"] = "NO_SUCCESSFUL_CURRENT_ACQUISITION"
        return result
    if (row.get("source_id") != acquisition.get("source_id")
            or row.get("wav_sha256") != acquisition.get("wav_sha256")):
        result.update(binding="STALE_SOURCE_BINDING", current_source_id=acquisition.get("source_id"))
        return result
    result["binding"] = "CURRENT_SOURCE_AND_RECORDED_AUDIO_HASH_MATCH"
    duration = None
    try:
        with wave.open(str(acquisition["wav"]), "rb") as wav:
            duration = wav.getnframes() / wav.getframerate()
            result["audio_seconds"] = round(duration, 3)
            if (wav.getnchannels(), wav.getframerate(), wav.getsampwidth()) != (1, 16000, 2):
                flag("AUDIO_FORMAT", "WAV header does not match mono 16kHz PCM16")
    except (OSError, EOFError, wave.Error, KeyError, ZeroDivisionError) as exc:
        flag("AUDIO_PATH_OR_HEADER", str(exc))
    if not row.get("transcript"):
        flag("NO_TRANSCRIPT", "No transcript path in the current manifest row")
        return result
    path = Path(row["transcript"])
    result["transcript"] = str(path)
    try:
        payload = path.read_bytes()
        result["actual_transcript_sha256"] = digest(payload)
        if digest(payload) != row.get("transcript_sha256"):
            flag("TRANSCRIPT_HASH_MISMATCH", "File differs from the manifest's recorded transcript hash")
        words = jsonl(payload)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        flag("TRANSCRIPT_UNREADABLE", str(exc))
        return result
    result["word_rows"] = len(words)
    result["claimed_word_count"] = row.get("word_count")
    if row.get("word_count") != len(words):
        flag("WORD_COUNT_MISMATCH", {"claimed": row.get("word_count"), "actual_rows": len(words)})
    if not words:
        flag("EMPTY_TRANSCRIPT", "The transcript contains no word rows")
        return result
    valid, bad_times, negative, reversed_span, start_backsteps, end_backsteps = [], 0, 0, 0, 0, 0
    text_parts = []
    estimated_rows = 0
    previous_start = previous_end = None
    for word in words:
        if not isinstance(word, dict):
            bad_times += 1
            continue
        text_parts.append(str(word.get("word") or ""))
        estimated_rows += word.get("timing_is_estimated") is True
        start, end = timestamp(word.get("start_sec")), timestamp(word.get("end_sec"))
        if start is None or end is None:
            bad_times += 1
            continue
        valid.append((start, end))
        negative += min(start, end) < 0
        reversed_span += end < start
        start_backsteps += previous_start is not None and start < previous_start - .05
        end_backsteps += previous_end is not None and end < previous_end - .05
        previous_start, previous_end = start, end
    result["timing"] = {"valid_rows": len(valid), "invalid_rows": bad_times,
                        "negative_rows": negative, "reversed_span_rows": reversed_span,
                        "start_backsteps_gt_50ms": start_backsteps, "end_backsteps_gt_50ms": end_backsteps,
                        "explicitly_estimated_rows": estimated_rows,
                        "caption_derived": row.get("status") == "CAPTION_TRANSCRIPT_READY_IDENTITY_UNVERIFIED"}
    for code, count in (("INVALID_TIMESTAMPS", bad_times), ("NEGATIVE_TIMESTAMPS", negative),
                        ("REVERSED_WORD_SPANS", reversed_span), ("START_TIME_BACKSTEPS", start_backsteps),
                        ("END_TIME_BACKSTEPS", end_backsteps)):
        if count:
            flag(code, count)
    if valid:
        first, last = min(x[0] for x in valid), max(x[1] for x in valid)
        result["timing"].update(first_start_sec=round(first, 3), last_end_sec=round(last, 3))
        if duration:
            result["timing"].update(last_end_audio_ratio=round(last / duration, 4),
                                    tail_without_timed_words_sec=round(duration - last, 3))
            if last > duration + TIMESTAMP_END_TOLERANCE_SECONDS:
                flag("TIMESTAMPS_BEYOND_AUDIO", {"last_end": last, "audio_seconds": duration})
            if last < duration * .60 and duration - last > 120:
                flag("LARGE_UNCOVERED_TAIL", "Timed words end before 60% of the recording, with over two minutes remaining")
            if first > 120:
                flag("LATE_TRANSCRIPT_START", "First timed word begins more than two minutes into the recording")
    tokens = re.findall(r"\w+", " ".join(text_parts).casefold())
    result["normalized_tokens"] = len(tokens)
    if duration:
        wpm = len(tokens) / (duration / 60)
        result["tokens_per_audio_minute"] = round(wpm, 2)
        if duration >= 600 and wpm < 10:
            flag("VERY_SPARSE_TEXT", "Fewer than 10 tokens per audio minute in a recording of at least 10 minutes")
        if wpm > 350 and len(tokens) > 100:
            flag("IMPLAUSIBLY_DENSE_TEXT", "More than 350 tokens per full audio minute; check duplication or duration")
    if len(tokens) < 50:
        flag("VERY_SHORT_TRANSCRIPT", len(tokens))
    longest_run = run = 0
    previous = None
    for token in tokens:
        run = run + 1 if token == previous else 1
        longest_run = max(longest_run, run)
        previous = token
    result["longest_repeated_token_run"] = longest_run
    if longest_run >= 8:
        flag("REPEATED_TOKEN_RUN", longest_run)
    repeated = Counter(tuple(tokens[i:i + 8]) for i in range(max(0, len(tokens) - 7)))
    top = repeated.most_common(3)
    result["most_repeated_eight_token_phrase_count"] = top[0][1] if top else 0
    if top and top[0][1] >= 10:
        flag("REPEATED_PHRASE", [{"phrase": " ".join(phrase), "occurrences": count}
                                  for phrase, count in top if count >= 10])
    return result


def main():
    acquired_bytes, transcript_bytes = ACQUISITION.read_bytes(), TRANSCRIPTS.read_bytes()
    acquisitions, transcripts = jsonl(acquired_bytes), jsonl(transcript_bytes)
    by_member = {row["member"]: row for row in acquisitions}
    rows = [inspect(row, by_member.get(row["member"])) for row in transcripts]
    flags = Counter(flag["code"] for row in rows for flag in row["flags"])
    bindings = Counter(row["binding"] for row in rows)
    report = {
        "schema": "member-longform-transcript-quality-snapshot-v1",
        "status": "DIAGNOSTIC_SNAPSHOT_NOT_REVIEW_APPROVAL",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "Current primary transcript manifest only; stale source bindings are counted but not inspected as current evidence.",
        "limitations": ["Risk flags require inspection; they are not automatic semantic failures.",
                       "Caption timestamps are estimated localization, not precise acoustic measurements.",
                       "WAV headers were read; full audio files were not rehashed in this audit.",
                       "No speaker identity, complete-turn boundaries, or behavioral interpretation was approved."],
        "inputs": {
            "acquisition": {"path": str(ACQUISITION), "sha256": digest(acquired_bytes),
                            "unchanged_during_audit": digest(ACQUISITION.read_bytes()) == digest(acquired_bytes)},
            "transcripts": {"path": str(TRANSCRIPTS), "sha256": digest(transcript_bytes),
                            "unchanged_during_audit": digest(TRANSCRIPTS.read_bytes()) == digest(transcript_bytes)},
            "audit_script_sha256": digest(Path(__file__).read_bytes()),
        },
        "counts": {"acquisition_rows": len(acquisitions), "transcript_rows": len(transcripts),
                   "duplicate_acquisition_members": len(acquisitions) - len(by_member),
                   "duplicate_transcript_members": len(transcripts) - len({row['member'] for row in transcripts}),
                   "bindings": dict(bindings), "members_with_risk_flags": sum(bool(row['flags']) for row in rows),
                   "flag_counts": dict(flags)},
        "missing_transcript_member_rows": sorted(set(by_member) - {row['member'] for row in transcripts}),
        "members": rows,
    }
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "counts": report["counts"], "inputs": report["inputs"]}, indent=2))


if __name__ == "__main__":
    main()
