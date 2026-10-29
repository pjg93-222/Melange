"""Run the finite all-roster automated evidence pipeline, preserving every gap.

Transcription writers own their manifests. This reader freezes each completed
source before inference, then executes boundaries, identity, exact PCM cutting,
and the original whole-turn acoustic measurement. No human sign-off required.
No profile publication is permitted by this collection/measurement worker.
"""
from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import json
from pathlib import Path
import shutil
import subprocess
import sys

from fec.speech import source_media_recovery as SMR
from fec.speech import snapshot_member_longform_ready_sources as snapshot
from fec.speech import select_member_longform_profile_sources as selector
from fec.speech import classify_member_longform_full_turns as physical
from fec.speech import screen_member_longform_identity_cues as screen
from fec.speech import build_member_longform_review_queue as queue
from audits.longform_collection_20260904 import audit_primary_transcript_quality as quality

ROOT = Path(__file__).resolve().parents[2]
STEP_TIMEOUT = None  # seconds per child module; set from --step-timeout in main


def check_prepare(root):
    receipt = json.loads((root / 'prepare.receipt.json').read_text(encoding='utf-8'))
    if receipt.get('status') != 'PREPARED_NOT_VERIFIED':
        raise ValueError('batch preparation receipt not recognized')
    # transcripts.jsonl is intentionally owned by the active ASR writer.
    for name in ('acquisitions.jsonl', 'member_queue.jsonl'):
        if SMR.sha256_file(root / name) != receipt['artifacts'][name]['sha256']:
            raise ValueError('batch source scope changed: ' + name)
    source_snapshot = Path(receipt['source_snapshot'])
    if SMR.sha256_file(source_snapshot / 'snapshot.receipt.json') != receipt['source_snapshot_receipt_sha256']:
        raise ValueError('original source snapshot receipt changed')
    snapshot.verify_snapshot(source_snapshot)
    original = json.loads((source_snapshot / 'snapshot.receipt.json').read_text(encoding='utf-8'))
    return {key: Path(item['snapshot_path']) for key, item in original['inputs'].items()}


# Audio facts a restored recording may legitimately change; identity/source fields may not.
REBIND_KEYS = {'wav_sha256', 'old_sha256', 'new_sha256', 'rebind_reason', 'sha_match', 'rebound_at', 'restore_run',
               'measured_duration_seconds', 'old_measured_duration_seconds', 'frame_count', 'old_frame_count',
               'restore_duration_delta_sec'}


def effective_acquisitions(root, frozen):
    """The frozen acquisitions, with restored-audio re-bindings applied when the batch root carries them.

    acquisitions.rebound.jsonl may differ from the frozen file only in the audio hash/duration and its
    old/new/reason record, so a re-bind can never swap the source."""
    path = root / 'acquisitions.rebound.jsonl'
    if not path.exists():
        return frozen
    bound = {row['member']: row for row in SMR.read_jsonl(path, required=True)}
    if set(bound) != {row['member'] for row in frozen}:
        raise ValueError('rebound acquisitions cover a different member set')
    result = []
    for row in frozen:
        new = bound[row['member']]
        if new != row:
            changed = {key for key in set(row) | set(new) if row.get(key) != new.get(key)}
            if (new.get('old_sha256') != row.get('wav_sha256') or new.get('new_sha256') != new.get('wav_sha256')
                    or not new.get('rebind_reason') or not changed <= REBIND_KEYS):
                raise ValueError('rebound acquisition changes more than the audio binding: ' + row['member'])
        result.append(new)
    return result


def choose_transcript(member, acquired, repaired, primary):
    candidates = [row for row in (repaired.get(member), primary.get(member)) if row
                  and selector.ready(row) and row.get('source_id') == acquired.get('source_id')
                  and row.get('wav_sha256') == acquired.get('wav_sha256')
                  and row.get('status') != 'CAPTION_TRANSCRIPT_READY_IDENTITY_UNVERIFIED']
    diagnostics = []
    for row in candidates:
        report = quality.inspect(row, acquired)
        if not report['flags'] and report.get('binding') == 'CURRENT_SOURCE_AND_RECORDED_AUDIO_HASH_MATCH':
            return row, diagnostics
        diagnostics.append(report)
    return None, diagnostics


def freeze_source(acquired, transcript, role, job):
    path = job / 'transcript.words.jsonl'
    original = Path(transcript['transcript'])
    if SMR.sha256_file(original) != transcript['transcript_sha256']:
        raise ValueError('completed transcript changed before freezing')
    if not path.exists():
        job.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, path)
    if SMR.sha256_file(path) != transcript['transcript_sha256']:
        raise ValueError('frozen transcript hash mismatch')
    source = {**acquired, **transcript, 'transcript': str(path.resolve())}
    words, _ = physical.validate_source(source)
    cues = screen.find_name_cues(words, source['member'])
    if not cues:
        raise ValueError('NO_IN_BAND_NAME_CUE')
    acquisition_era, transcript_era = acquired.get('source_era'), transcript.get('source_era')
    if acquisition_era and transcript_era and acquisition_era != transcript_era:
        raise ValueError('source_transcript_era_mismatch')
    explicit_era = acquisition_era or transcript_era
    era = explicit_era or 'NOT_CURRENT_FORMAL_LEADERSHIP'
    if str(era).startswith('PRE_CONGRESS'):
        dt.date.fromisoformat(str(acquired.get('recorded_at') or acquired.get('published') or '')[:10])
        if role:
            raise ValueError('leader_source_era_not_admitted')
    if role:
        date = dt.date.fromisoformat(str(acquired.get('recorded_at') or acquired.get('published') or '')[:10])
        cutoff = dt.date.fromisoformat(role['current_role_assumed_on'][:10])
        if date >= cutoff:
            if explicit_era != 'CURRENT_ROLE_CONDITIONED':
                raise ValueError('leader_source_not_before_current_role')
            era = 'CURRENT_ROLE_CONDITIONED'
        else:
            if explicit_era not in (None, 'NOT_CURRENT_FORMAL_LEADERSHIP', 'PRE_CURRENT_LEADERSHIP_ROLE'):
                raise ValueError('leader_source_era_date_mismatch')
            era = 'PRE_CURRENT_LEADERSHIP_ROLE'
        if acquired.get('current_role_assumed_on') not in (None, role['current_role_assumed_on']):
            raise ValueError('source_current_role_cutoff_mismatch')
        source['current_role'] = role.get('current_role')
        source['current_role_assumed_on'] = role['current_role_assumed_on']
    elif era in {'CURRENT_ROLE_CONDITIONED', 'PRE_CURRENT_LEADERSHIP_ROLE'}:
        raise ValueError('source_era_requires_current_role')
    selected = selector.source_record({**source, 'cues': cues}, acquired,
                                       selection='isolated-automated-full-recording', source_era=era)
    for filename, row in (('selection.jsonl', selected), ('acquisition.jsonl', acquired),
                          ('transcript.jsonl', {**transcript, 'transcript': str(path.resolve())})):
        output = job / filename
        if output.exists() and SMR.read_jsonl(output, required=True) != [row]:
            # selected_at is metadata, not a reason to rewrite the original proof.
            old = SMR.read_jsonl(output, required=True)
            if filename != 'selection.jsonl' or len(old) != 1 or any(
                    old[0].get(k) != row.get(k) for k in row if k != 'selected_at'):
                raise ValueError('existing frozen job input changed: ' + filename)
        elif not output.exists():
            SMR.write_jsonl_atomic(output, [row])
    return selected


def invoke(module, arguments, log):
    with log.open('a', encoding='utf-8') as handle:
        handle.write('\n' + dt.datetime.now(dt.timezone.utc).isoformat() + ' ' + module + '\n')
        handle.flush()
        subprocess.run([sys.executable, '-u', '-m', module, *map(str, arguments)],
                       cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=True, timeout=STEP_TIMEOUT)


def continuity_calibration(root):
    """Optional batch-root override of the speaker-continuity calibration, read on every run.

    <batch-root>/continuity_calibration.json = {"calibration": path, "sha256": hex}; the hash binds the file."""
    path = root / 'continuity_calibration.json'
    if not path.exists():
        return ()
    config = json.loads(path.read_text(encoding='utf-8'))
    calibration = Path(config['calibration'])
    if SMR.sha256_file(calibration) != config['sha256']:
        raise ValueError('continuity calibration hash mismatch: ' + str(calibration))
    return ('--calibration', calibration)


def source_pipeline(selected, job, model, threads, backend='local', effort='low', calibration=()):
    def run(module, *arguments):
        invoke('fec.speech.' + module, arguments, job / 'processing.log')
    classifier = (('--backend', 'cli', '--cli-effort', effort, '--same-prompt-both-passes') if backend == 'cli'
                  else ('--converted-model', model, '--cpu-threads', threads))
    run('classify_member_longform_two_passes_local', '--input', job / 'selection.jsonl',
        '--out-root', job, *classifier)
    if not (job / 'candidates.receipt.json').exists():
        run('reconcile_member_longform_candidate_passes', '--input', job / 'selection.jsonl',
            '--member', selected['member'], '--source-id', selected['source_id'],
            '--pass-a', job / 'pass-a.json', '--pass-b', job / 'pass-b.json',
            '--output', job / 'candidates.jsonl', '--receipt', job / 'candidates.receipt.json')
    candidate = SMR.read_jsonl(job / 'candidates.jsonl', required=True)[0]
    if not candidate.get('turns'):
        return {'status': 'HELD_NO_AGREED_COMPLETE_RESPONSES', 'verified_turns': 0}
    run('verify_member_longform_speaker_continuity', '--input', job / 'candidates.jsonl',
        '--output', job / 'continuity.jsonl', '--receipt', job / 'continuity.receipt.json', *calibration)
    run('verify_member_longform_automated', '--selection', job / 'selection.jsonl',
        '--candidates', job / 'candidates.jsonl', '--candidate-receipt', job / 'candidates.receipt.json',
        '--continuity', job / 'continuity.jsonl', '--out', job / 'verifications.jsonl',
        '--receipt', job / 'verifications.receipt.json', '--diagnostics', job / 'verification-diagnostics.jsonl')
    verified = SMR.read_jsonl(job / 'verifications.jsonl', required=True)
    if not verified:
        return {'status': 'HELD_NO_SPEAKER_VERIFIED_RESPONSES', 'verified_turns': 0}
    run('materialize_member_longform_reviewed_turns', '--selection', job / 'selection.jsonl',
        '--candidates', job / 'candidates.jsonl', '--continuity', job / 'continuity.jsonl',
        '--reviews', job / 'verifications.jsonl', '--out', job / 'turns.jsonl',
        '--receipt', job / 'turns.receipt.json', '--audio-root', job / 'turn-audio')
    run('build_member_longform_turn_features', '--turn-pair', job / 'turns.jsonl', job / 'turns.receipt.json',
        '--source-manifest', job / 'acquisition.jsonl', '--transcript-manifest', job / 'transcript.jsonl',
        '--quality-holds', ROOT / 'audits/longform_collection_20260904/quality_holds.jsonl',
        '--out', job / 'features.json', '--receipt', job / 'features.receipt.json')
    measured = json.loads((job / 'features.json').read_text(encoding='utf-8'))
    return {'status': 'AUTOMATED_VERIFIED_AND_MEASURED',
            'verified_turns': measured['counts']['qualified_turns'],
            'verified_minutes': measured['counts']['minutes'], 'job': str(job.resolve()),
            'feature_receipt_sha256': SMR.sha256_file(job / 'features.receipt.json'),
            'recurring_pattern_established': False, 'profiles_published': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch-root', required=True, type=Path)
    parser.add_argument('--classifier-backend', choices=('local', 'cli'), default='local')
    parser.add_argument('--converted-model', type=Path)
    parser.add_argument('--cli-effort', choices=('low', 'medium', 'high'), default='low')
    parser.add_argument('--same-prompt-both-passes', action='store_true',
                        help='accepted for explicitness; the cli backend always sends the same prompt in both passes')
    parser.add_argument('--cpu-threads', default=2, type=int)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--member', action='append', default=[], help='only these queue members (repeatable); results/receipt then cover only them')
    parser.add_argument('--step-timeout', default=14400, type=float, help='seconds per child module; 0 = unlimited')
    args = parser.parse_args()
    if args.classifier_backend == 'local' and not args.converted_model:
        parser.error('--converted-model is required for --classifier-backend local')
    if args.same_prompt_both_passes and args.classifier_backend != 'cli':
        parser.error('--same-prompt-both-passes applies to --classifier-backend cli only')
    global STEP_TIMEOUT
    STEP_TIMEOUT = args.step_timeout or None
    root = args.batch_root.resolve()
    frozen = check_prepare(root)
    roles = json.loads(frozen['roles'].read_text(encoding='utf-8'))['members']
    acquired = snapshot.rows_by_member(effective_acquisitions(root, SMR.read_jsonl(root / 'acquisitions.jsonl', required=True)),
                                       'batch acquisitions')
    repaired = snapshot.rows_by_member(SMR.read_jsonl(root / 'transcripts.jsonl', required=True), 'repair transcripts')
    primary = snapshot.rows_by_member(SMR.read_jsonl(selector.DEFAULT_PRIMARY_TRANSCRIPTS, required=True), 'primary transcripts')
    queue_rows = SMR.read_jsonl(root / 'member_queue.jsonl', required=True)
    queue_names = [row['member'] for row in queue_rows]
    unknown = sorted(set(args.member) - set(queue_names))
    if unknown:
        parser.error('--member not in member_queue.jsonl: ' + ', '.join(unknown))
    members = [row for row in queue_rows if not args.member or row['member'] in args.member]
    name = 'processing-preparation.jsonl' if args.prepare_only else 'processing-results.jsonl'
    # A --member run replaces only its own members' rows; every other queue member keeps its earlier row.
    earlier = {row['member']: row for row in SMR.read_jsonl(root / name)} if args.member else {}
    output, merged = [], [earlier[member] for member in queue_names if member in earlier]
    for index, member_row in enumerate(members, 1):
        member = member_row['member']
        item = {'member': member, 'source_id': member_row.get('source_id'), 'verified_turns': 0}
        try:
            if member_row['status'] == 'SOURCE_HOLD':
                item.update(status='SOURCE_HOLD', reason=member_row['reason'])
            else:
                source = acquired[member]
                transcript, diagnostics = choose_transcript(member, source, repaired, primary)
                if transcript is None:
                    item.update(status='TRANSCRIPT_NOT_READY_OR_QUALITY_HOLD', diagnostics=diagnostics)
                else:
                    job = root / 'processing' / (queue.slug(member) + '__' + transcript['transcript_sha256'][:16])
                    selected = freeze_source(source, transcript, roles.get(member), job)
                    item.update(job=str(job.resolve()), status='FROZEN_READY_FOR_AUTOMATED_PROCESSING')
                    if not args.prepare_only:
                        item.update(source_pipeline(selected, job, args.converted_model, max(1, args.cpu_threads),
                                                       args.classifier_backend, args.cli_effort,
                                                       continuity_calibration(root)))
        except (ValueError, OSError, KeyError, subprocess.CalledProcessError, subprocess.TimeoutExpired, SystemExit) as exc:
            item.update(status='PROCESSING_HOLD', reason=f'{type(exc).__name__}: {str(exc)[:1000]}')
        output.append(item)
        # Persist after each source; an interrupted or failed member cannot erase prior progress.
        rows = {**earlier, **{row['member']: row for row in output}}
        merged = [rows[member] for member in queue_names if member in rows]
        SMR.write_jsonl_atomic(root / name, merged)
        print(f"automated-evidence {index}/{len(members)} {member}: {item['status']}", flush=True)
    covered = len(merged) == len(queue_names)
    all_verified = covered and all(row['verified_turns'] > 0 for row in merged)
    counts = dict(Counter(row['status'] for row in merged))
    receipt = {'schema': 'member-longform-automated-processing-receipt-v1',
               'status': 'PREPARED_ONLY' if args.prepare_only else 'FINISHED_WITH_EXPLICIT_COVERAGE' if all_verified
                         else 'FINISHED_WITH_EXPLICIT_HOLDS' if covered else 'FINISHED_PARTIAL_COVERAGE',
               'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(), 'active_members': len(members),
               'member_filter': sorted(args.member) or None, 'queue_members': len(queue_names), 'covered_members': len(merged),
               'counts': counts, 'verified_members': sum(row['verified_turns'] > 0 for row in merged),
               'verified_turns': sum(row['verified_turns'] for row in merged),
               'all_members_verified': all_verified,
               'human_reviews_required': False, 'profiles_regenerated_or_published': False,
               'output': {'path': str(root / name), 'sha256': SMR.sha256_file(root / name)}}
    SMR.write_json_atomic(root / name.replace('.jsonl', '.receipt.json'), receipt)
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
