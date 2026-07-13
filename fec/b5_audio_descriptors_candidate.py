# -*- coding: utf-8 -*-
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from paths import ROOT as MB_ROOT
"""Build fail-closed, direct audio delivery measurements (candidate; consumed by NOTHING).

This replaces the narrative layer's unsupported proxy translations.  ``loudnessPeaksPerSec`` is not
treated as speaking speed; cross-source mean loudness, HNR character language, and jitter-as-tension
are omitted.  A clip is usable only after TWO distinct reviews confirm target identity, target-only
segments, and the segment word counts.  Pace is target transcript words / selected elapsed minutes.
Pitch variation and volume dynamics are measured only inside those target-only segments.

Real builds require explicit --review and --out paths.  The expected review artifact is documented by
validate_clip_review(); no live artifact is ever overwritten implicitly.  The resulting .candidate is
not read by production code until a separate user-ratified promotion.
"""
import argparse, hashlib, json, math, os, re, sys
from collections import defaultdict
import numpy as np
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from moneyball_core import dump_atomic

ADIR = os.path.join(MB_ROOT, 'audio_pilot')
PITCH_VAR = 'F0semitoneFrom27.5Hz_sma3nz_stddevNorm'
VOLUME_DYN = 'loudness_sma3_stddevNorm'
MIN_SEGMENT_SEC = 5.0
MIN_CLIP_TARGET_SEC = 30.0
MIN_MEMBER_TARGET_SEC = 180.0
MIN_INDEPENDENT_SOURCES = 2
MIN_COHORT_FOR_PERCENTILES = 80
SHA_RE = re.compile(r'^[0-9a-f]{64}$')


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def validate_clip_review(rel, row):
    """Validate the complete double-review contract; return normalized segments."""
    errors = []
    if not isinstance(row, dict):
        return None, ['row is not an object']
    source_id = str(row.get('source_id') or '').strip()
    source_url = str(row.get('source_url') or '').strip()
    venue = str(row.get('venue') or '').strip().lower()
    if not source_id: errors.append('source_id missing')
    if not source_url.startswith(('https://', 'http://')): errors.append('source_url missing/invalid')
    if not venue: errors.append('venue missing')
    reviews = row.get('reviews') or []
    if len(reviews) != 2:
        errors.append('exactly two reviews required')
    reviewer_ids = []
    for i, review in enumerate(reviews):
        if not isinstance(review, dict):
            errors.append('review %d is not an object' % (i + 1)); continue
        rid = str(review.get('reviewer') or '').strip()
        reviewer_ids.append(rid)
        if not rid: errors.append('review %d reviewer missing' % (i + 1))
        if review.get('identity') != 'TARGET': errors.append('review %d identity not TARGET' % (i + 1))
        if review.get('speaker') != 'TARGET_ONLY': errors.append('review %d speaker not TARGET_ONLY' % (i + 1))
        if review.get('segments_confirmed') is not True: errors.append('review %d segments unconfirmed' % (i + 1))
        if review.get('word_counts_confirmed') is not True: errors.append('review %d word counts unconfirmed' % (i + 1))
        if not str(review.get('identity_evidence') or '').strip(): errors.append('review %d identity evidence missing' % (i + 1))
    if len(reviewer_ids) == 2 and (not all(reviewer_ids) or reviewer_ids[0] == reviewer_ids[1]):
        errors.append('reviewers must be distinct')
    segments = row.get('segments') or []
    norm = []
    for i, seg in enumerate(segments):
        try:
            start = float(seg['start_sec']); end = float(seg['end_sec']); words = int(seg['word_count'])
        except (KeyError, TypeError, ValueError):
            errors.append('segment %d malformed' % (i + 1)); continue
        tsha = str(seg.get('transcript_sha256') or '').lower()
        if start < 0 or end - start < MIN_SEGMENT_SEC: errors.append('segment %d too short/invalid' % (i + 1))
        if words < 0: errors.append('segment %d negative word count' % (i + 1))
        if not SHA_RE.match(tsha): errors.append('segment %d transcript_sha256 invalid' % (i + 1))
        norm.append({'start_sec': start, 'end_sec': end, 'word_count': words,
                     'transcript_sha256': tsha})
    if not norm: errors.append('no valid target segments')
    if sum(s['end_sec'] - s['start_sec'] for s in norm) < MIN_CLIP_TARGET_SEC:
        errors.append('clip has < %ds confirmed target audio' % int(MIN_CLIP_TARGET_SEC))
    if errors:
        return None, errors
    return {'source_id': source_id, 'source_url': source_url, 'venue': venue,
            'segments': norm, 'reviewers': reviewer_ids}, []


def _smile():
    import opensmile
    return opensmile.Smile(feature_set=opensmile.FeatureSet.eGeMAPSv02,
                           feature_level=opensmile.FeatureLevel.Functionals)


def measure_clip(path, review, smile=None):
    """Measure only reviewer-confirmed target segments; no recording-level personality inference."""
    import soundfile as sf
    sig, sr = sf.read(path, always_2d=False)
    if getattr(sig, 'ndim', 1) > 1:
        sig = np.asarray(sig, float).mean(axis=1)
    else:
        sig = np.asarray(sig, float)
    smile = smile or _smile()
    rows = []
    total_sec = 0.0; total_words = 0
    for seg in review['segments']:
        a = max(0, int(round(seg['start_sec'] * sr)))
        b = min(len(sig), int(round(seg['end_sec'] * sr)))
        if b <= a: raise ValueError('segment outside audio bounds')
        part = sig[a:b]
        sec = len(part) / float(sr)
        frame = smile.process_signal(part, sr).iloc[0]
        vals = {PITCH_VAR: float(frame[PITCH_VAR]), VOLUME_DYN: float(frame[VOLUME_DYN])}
        if not all(math.isfinite(v) for v in vals.values()): raise ValueError('non-finite acoustic value')
        rows.append((vals, sec)); total_sec += sec; total_words += seg['word_count']
    weighted = {k: sum(v[k] * sec for v, sec in rows) / total_sec for k in (PITCH_VAR, VOLUME_DYN)}
    return {
        'target_elapsed_sec': round(total_sec, 3),
        'target_words': total_words,
        'delivery_rate_wpm': round(60.0 * total_words / total_sec, 3),
        'pitch_variability_raw': round(weighted[PITCH_VAR], 8),
        'volume_dynamics_raw': round(weighted[VOLUME_DYN], 8),
    }


def _percentile(value, population):
    vals = np.sort(np.asarray(population, float))
    if len(vals) <= 1: return None
    return round(100.0 * float(np.searchsorted(vals, value, side='left')) / (len(vals) - 1), 2)


def _stable_band(percentiles):
    """Only label a cross-source extreme when every source agrees on the same outer quartile."""
    if not percentiles or any(p is None for p in percentiles): return None
    if min(percentiles) >= 75.0: return 'high_across_sources'
    if max(percentiles) <= 25.0: return 'low_across_sources'
    return None


def build(review_path, only=None):
    with open(review_path, encoding='utf-8') as f:
        review_doc = json.load(f)
    if review_doc.get('schema') != 'b5-audio-review-v2-candidate':
        raise ValueError('review schema must be b5-audio-review-v2-candidate')
    clip_rows = review_doc.get('clips') or {}
    wanted = {x.strip() for x in (only or '').split(',') if x.strip()}
    accepted = {}; rejected = {}; smile = None
    for rel, raw in sorted(clip_rows.items()):
        member = rel.replace('\\', '/').split('/')[0]
        if wanted and member not in wanted: continue
        review, errors = validate_clip_review(rel, raw)
        path = os.path.join(ADIR, *rel.replace('\\', '/').split('/'))
        if not os.path.exists(path): errors.append('audio file missing')
        if errors:
            rejected[rel] = errors; continue
        try:
            smile = smile or _smile()
            measured = measure_clip(path, review, smile)
            accepted[rel] = {**review, **measured, 'audio_sha256': _sha256(path)}
        except Exception as e:
            rejected[rel] = ['measurement failed: ' + str(e)[:160]]
    by_member = defaultdict(list)
    for rel, row in accepted.items(): by_member[rel.replace('\\', '/').split('/')[0]].append(row)
    eligible = {m: rows for m, rows in by_member.items()
                if sum(r['target_elapsed_sec'] for r in rows) >= MIN_MEMBER_TARGET_SEC
                and len({r['source_id'] for r in rows}) >= MIN_INDEPENDENT_SOURCES}
    cohort_ok = len(eligible) >= MIN_COHORT_FOR_PERCENTILES
    populations = {}
    if cohort_ok:
        for key in ('delivery_rate_wpm', 'pitch_variability_raw', 'volume_dynamics_raw'):
            populations[key] = [float(np.median([r[key] for r in rows])) for rows in eligible.values()]
    members = {}
    for member, rows in sorted(eligible.items()):
        sources = sorted({r['source_id'] for r in rows}); venues = sorted({r['venue'] for r in rows})
        metrics = {}
        for key in ('delivery_rate_wpm', 'pitch_variability_raw', 'volume_dynamics_raw'):
            vals = [r[key] for r in rows]
            pcts = [_percentile(v, populations[key]) for v in vals] if cohort_ok else [None] * len(vals)
            metrics[key] = {
                'median': round(float(np.median(vals)), 4),
                'min': round(float(min(vals)), 4),
                'max': round(float(max(vals)), 4),
                'source_percentiles': pcts,
                'stable_outer_quartile': _stable_band(pcts),
            }
        members[member] = {
            'target_elapsed_sec': round(sum(r['target_elapsed_sec'] for r in rows), 3),
            'source_n': len(sources), 'sources': sources,
            'venue_n': len(venues), 'venues': venues,
            'cross_venue': len(venues) >= 2,
            'metrics': metrics,
            'clips': rows,
            'narrative_contract': {
                'generalize_across_venues_only_if_cross_venue': True,
                'use_high_low_label_only_if_stable_outer_quartile_present': True,
                'never_infer_personality_mood_health_or_sincerity': True,
            },
        }
    return {
        'schema': 'b5-audio-descriptors-v2-candidate',
        'status': 'CANDIDATE_CONSUMED_BY_NOTHING_AWAITING_USER_RATIFICATION',
        'measurement_contract': {
            'delivery_rate_wpm': 'confirmed target transcript words / confirmed target elapsed minutes; includes pauses',
            'pitch_variability_raw': PITCH_VAR + ' on confirmed target-only segments',
            'volume_dynamics_raw': VOLUME_DYN + ' on confirmed target-only segments',
            'explicitly_excluded': ['loudnessPeaksPerSec as pace', 'cross-source mean loudness',
                                    'HNR character inference', 'jitter as tension or emotional tell'],
            'two_distinct_reviews_per_clip': True,
            'minimum_independent_sources_per_member': MIN_INDEPENDENT_SOURCES,
            'minimum_target_seconds_per_member': MIN_MEMBER_TARGET_SEC,
            'cohort_minimum_for_percentile_labels': MIN_COHORT_FOR_PERCENTILES,
        },
        'review_sha256': _sha256(review_path),
        'cohort_percentiles_available': cohort_ok,
        'accepted_clip_n': len(accepted), 'rejected_clip_n': len(rejected),
        'rejected': rejected, 'members': members,
    }


def self_test():
    good = {
        'source_id': 'source-a', 'source_url': 'https://example.test/a', 'venue': 'floor',
        'segments': [{'start_sec': 0, 'end_sec': 60, 'word_count': 120,
                      'transcript_sha256': 'a' * 64}],
        'reviews': [
            {'reviewer': 'reviewer-1', 'identity': 'TARGET', 'speaker': 'TARGET_ONLY',
             'segments_confirmed': True, 'word_counts_confirmed': True, 'identity_evidence': 'direct introduction'},
            {'reviewer': 'reviewer-2', 'identity': 'TARGET', 'speaker': 'TARGET_ONLY',
             'segments_confirmed': True, 'word_counts_confirmed': True, 'identity_evidence': 'official source'},
        ],
    }
    norm, errors = validate_clip_review('Example/clip_a.wav', good)
    assert not errors and norm['segments'][0]['word_count'] == 120
    same = json.loads(json.dumps(good)); same['reviews'][1]['reviewer'] = 'reviewer-1'
    assert 'reviewers must be distinct' in validate_clip_review('x', same)[1]
    multi = json.loads(json.dumps(good)); multi['reviews'][0]['speaker'] = 'MULTI_SPEAKER'
    assert any('speaker not TARGET_ONLY' in x for x in validate_clip_review('x', multi)[1])
    bad_sha = json.loads(json.dumps(good)); bad_sha['segments'][0]['transcript_sha256'] = 'nope'
    assert any('transcript_sha256' in x for x in validate_clip_review('x', bad_sha)[1])
    short = json.loads(json.dumps(good)); short['segments'][0]['end_sec'] = 20
    assert any('confirmed target audio' in x for x in validate_clip_review('x', short)[1])
    assert _stable_band([76, 88]) == 'high_across_sources'
    assert _stable_band([12, 24]) == 'low_across_sources'
    assert _stable_band([20, 80]) is None
    print('b5_audio_descriptors_candidate self-test: 8 passed, 0 FAILED')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true')
    ap.add_argument('--review', help='double-reviewed candidate JSON')
    ap.add_argument('--out', help='candidate output JSON; required for a real build')
    ap.add_argument('--only', help='comma-separated member names')
    args = ap.parse_args()
    if args.self_test:
        self_test(); return
    if not args.review or not args.out:
        ap.error('--review and --out are required; candidate builds never write implicitly')
    review_path = args.review if os.path.isabs(args.review) else os.path.join(MB_ROOT, args.review)
    out_path = args.out if os.path.isabs(args.out) else os.path.join(MB_ROOT, args.out)
    doc = build(review_path, args.only)
    dump_atomic(doc, out_path, indent=1)
    print('%s: %d verified members, %d accepted clips, %d rejected; consumed by nothing' %
          (os.path.basename(out_path), len(doc['members']), doc['accepted_clip_n'], doc['rejected_clip_n']))


if __name__ == '__main__':
    main()
