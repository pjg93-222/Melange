"""Mechanical, venue-matched expression contrasts over the systematic encounter census.

STATUS: EXPLORATORY. Nothing here feeds any engine, rank, or production surface.

What this module computes, and only this: for every directed (actor, target) pair
the census found, how much more often the actor's turns naming that target carried
a warm (or hostile) lexical cue than the same actor's turns naming everybody else,
in the same source. That is a within-speaker, venue-matched contrast of a regex
retrieval statistic. It is not affection, not sincerity, not a reviewed encounter,
and not a signed relationship edge.

Provenance gate. Every row is stamped ``sampling_basis == 'systematic_encounter_mechanical'``.
``chamber_expression.matched_expression`` admits only ``sampling_basis ==
'systematic_encounter_review'`` with ``review_status == 'context_reviewed'``, so
nothing written here can be mistaken for, or promoted into, reviewed evidence. The
status vocabulary deliberately mirrors that module's shape while using a distinct
value, ``insufficient_systematic_exposure``, for the same reason.

Denominator contract. The four arguments of ``relative_contrast`` come from the
census manifest's own ``denominator_contract`` block:

    n              = encounter_counts[(actor, target, source)].mention_turns
    positive       = encounter_counts[(actor, target, source)].<channel>_turns
    other_n        = speaker_baseline[(actor, source)].target_mention_turn_sum - n
    other_positive = speaker_baseline[(actor, source)].target_<channel>_turn_sum - positive

This is the leave-one-target-out form: both sides count *target-mention turns*, so
``other_positive <= other_n`` holds by construction. The alternative reading --
``other_n = colleague_mention_turns - n`` with the speaker's turn-level
``warm_turns`` as the positives -- mixes two different units (distinct turns naming
anybody, versus cue-bearing turns whether or not they name anybody) and is not a
valid argument pair: on this census it violates ``other_positive <= other_n`` on
685 of 20,766 warm rows and 29 hostile rows, which ``relative_contrast`` rejects.
That reading is still computed, per row, under ``turn_level_variant``, carrying its
own status so the difference stays auditable instead of asserted.

Held-out discipline. ``split == 'heldout'`` rows of the frozen probability sample
are read for their ``pair_id`` only, into a deny-list, and are refused in both
derived views and in the diagnostic leaderboards. No held-out label, review,
weight, or stratum is read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections import defaultdict
from pathlib import Path

from .data import ROOT, digest, read_json, term_at, write_json
from .relative_expression import relative_contrast

OUTPUTS = ROOT / 'outputs/member_personal_relationships'
CENSUS = OUTPUTS / '20260910_systematic_encounters'
FROZEN = OUTPUTS / '20260910_frozen_v5'
REGRESSION = OUTPUTS / '20260910_regression'
PILOT = OUTPUTS / '20260910_pilot'
OUT = OUTPUTS / '20260910_expression_contrasts'

SOURCES = ('CHRG', 'CREC', 'INTERVIEW')
POOLED = 'pooled'
CHANNELS = ('warm', 'hostile')

SAMPLING_BASIS = 'systematic_encounter_mechanical'
CLASSIFIER = 'history_speech cue regexes (uncalibrated until calibration receipt attached)'
AVAILABLE = 'available'
INSUFFICIENT = 'insufficient_systematic_exposure'
VARIANT_UNDEFINED = 'undefined_positive_exceeds_opportunities'
LEADERBOARD_MIN_N = 3


# ------------------------------------------------------------------ small io

def read_rows(path):
    with Path(path).open(encoding='utf-8') as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_rows(path, rows):
    """Streaming twin of data.write_ndjson; the census-wide file is large."""
    written = 0
    with Path(path).open('w', encoding='utf-8', newline='\n') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
            written += 1
    return written


def sha256_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


# ------------------------------------------------------------- pure helpers

def percentile(values, q):
    """Linear interpolation between order statistics; no numpy, no silent nan."""
    ordered = sorted(values)
    if not ordered:
        return None
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * q
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return float(ordered[low])
    return float(ordered[low] + (ordered[high] - ordered[low]) * (position - low))


def median_iqr(values):
    values = [v for v in values if v is not None]
    return dict(n=len(values), median=percentile(values, .5),
                q1=percentile(values, .25), q3=percentile(values, .75),
                iqr=None if not values else percentile(values, .75) - percentile(values, .25),
                minimum=min(values) if values else None, maximum=max(values) if values else None)


def mann_whitney_auc(positive, negative):
    """Rank-based separation with half credit for ties.

    This is the probability that a randomly drawn documented-positive dyad scores
    above a randomly drawn documented-negative dyad. It measures SIGN AMONG
    DOCUMENTED TIES only: both groups were selected because a tie of a known sign
    already exists. It says nothing about detecting ties, and nothing about pairs
    with no documented tie.
    """
    pos = [x for x in positive if x is not None]
    neg = [x for x in negative if x is not None]
    if not pos or not neg:
        return dict(auc=None, n_pos=len(pos), n_neg=len(neg), comparisons=0, wins=0, ties=0)
    wins = ties = 0
    for a in pos:
        for b in neg:
            if a > b:
                wins += 1
            elif a == b:
                ties += 1
    comparisons = len(pos) * len(neg)
    return dict(auc=(wins + .5 * ties) / comparisons, n_pos=len(pos), n_neg=len(neg),
                comparisons=comparisons, wins=wins, ties=ties)


# ------------------------------------------------------- denominator mapping

def contrast_arguments(count, baseline, channel):
    """Census manifest denominator contract -> (n, positive, other_n, other_positive)."""
    if channel not in CHANNELS:
        raise ValueError('Channel must be warm or hostile')
    n = int(count.get('mention_turns', 0))
    positive = int(count.get(channel + '_turns', 0))
    other_n = int(baseline.get('target_mention_turn_sum', 0)) - n
    other_positive = int(baseline.get('target_%s_turn_sum' % channel, 0)) - positive
    return n, positive, other_n, other_positive


def turn_level_arguments(count, baseline, channel):
    """The speaker-turn-level reading, kept for audit. Units do not match; see module docstring."""
    n = int(count.get('mention_turns', 0))
    positive = int(count.get(channel + '_turns', 0))
    other_n = int(baseline.get('colleague_mention_turns', 0)) - n
    other_positive = int(baseline.get(channel + '_turns', 0)) - positive
    return n, positive, other_n, other_positive


def exposure_status(n, other_n):
    return AVAILABLE if n >= 1 and other_n >= 1 else INSUFFICIENT


def turn_level_block(count, baseline):
    """Both channels of the audit variant, with an explicit undefined status."""
    block = {}
    statuses = []
    for channel in CHANNELS:
        n, positive, other_n, other_positive = turn_level_arguments(count, baseline, channel)
        block['other_n'] = other_n
        block['other_' + channel] = other_positive
        # relative_contrast checks positive-vs-opportunity BEFORE its zero-denominator
        # early return, so other_n == 0 with any positive left over is undefined too.
        if other_positive < 0 or positive > n or other_positive > other_n:
            block[channel + '_contrast'] = None
            block[channel + '_status'] = VARIANT_UNDEFINED
            statuses.append(VARIANT_UNDEFINED)
            continue
        status = exposure_status(n, other_n)
        block[channel + '_status'] = status
        statuses.append(status)
        value = relative_contrast(n, positive, max(0, other_n), max(0, other_positive))
        block[channel + '_contrast'] = value['contrast']
    if VARIANT_UNDEFINED in statuses:
        block['status'] = VARIANT_UNDEFINED
    elif AVAILABLE in statuses:
        block['status'] = AVAILABLE
    else:
        block['status'] = INSUFFICIENT
    return block


# --------------------------------------------------------------- row builder

EMPTY_COUNT = dict(mention_turns=0, warm_turns=0, hostile_turns=0, personal_turns=0,
                   first_date=None, last_date=None)
EMPTY_BASELINE = dict(total_turns=0, colleague_mention_turns=0, distinct_targets=0,
                      target_mention_turn_sum=0, target_warm_turn_sum=0,
                      target_hostile_turn_sum=0, target_personal_turn_sum=0,
                      warm_turns=0, hostile_turns=0, personal_turns=0)


def pooled_counts(rows):
    """Sum a directed pair's per-source counts. Dates take the outer envelope."""
    out = dict(EMPTY_COUNT)
    dated = [r for r in rows if r.get('first_date')]
    for row in rows:
        for key in ('mention_turns', 'warm_turns', 'hostile_turns', 'personal_turns'):
            out[key] += int(row.get(key, 0))
    if dated:
        out['first_date'] = min(r['first_date'] for r in dated)
        out['last_date'] = max(r['last_date'] for r in dated)
    return out


def pooled_baseline(rows):
    """Sum a speaker's per-source baselines across every source they speak in."""
    out = dict(EMPTY_BASELINE)
    for row in rows:
        for key in EMPTY_BASELINE:
            out[key] += int(row.get(key, 0))
    return out


def build_row(actor, target, source, count, baseline, *, actor_name, target_name,
              chamber, chamber_basis, manifest_sha, calibration=None):
    """One directed (actor, target, source) contrast row. Pure; no file or clock access."""
    n = int(count.get('mention_turns', 0))
    row = dict(
        actor=actor, target=target, actor_name=actor_name, target_name=target_name,
        source=source, row_kind=POOLED if source == POOLED else 'venue_matched',
        speaker_chamber=chamber, speaker_chamber_basis=chamber_basis,
        n=n, warm=int(count.get('warm_turns', 0)), hostile=int(count.get('hostile_turns', 0)),
        personal=int(count.get('personal_turns', 0)),
        speaker_target_mention_turns=int(baseline.get('target_mention_turn_sum', 0)),
        speaker_total_turns=int(baseline.get('total_turns', 0)),
        speaker_distinct_targets=int(baseline.get('distinct_targets', 0)),
        first_date=count.get('first_date'), last_date=count.get('last_date'))
    other_n = 0
    for channel in CHANNELS:
        args = contrast_arguments(count, baseline, channel)
        other_n = args[2]
        row['other_' + channel] = args[3]
        row[channel + '_contrast'] = relative_contrast(*args)
    row['other_n'] = other_n
    row['status'] = exposure_status(n, other_n)
    row['turn_level_variant'] = turn_level_block(count, baseline)
    row['sampling_basis'] = SAMPLING_BASIS
    row['classifier'] = CLASSIFIER
    row['census_manifest_sha256'] = manifest_sha
    row['calibration'] = calibration
    return row


# ------------------------------------------------------------- calibration

def load_calibration(path):
    """Return (stratum table, sha256). Stratum objects are copied verbatim into rows."""
    raw = Path(path).read_bytes()
    payload = json.loads(raw.decode('utf-8'))
    table = (payload.get('strata') if isinstance(payload, dict)
             and isinstance(payload.get('strata'), dict) else payload)
    if not isinstance(table, dict):
        raise ValueError('Calibration receipt must be an object of strata')
    cleaned = {}
    for key, block in table.items():
        if isinstance(block, dict) and '|' in str(key):
            cleaned[str(key)] = block
    if not cleaned:
        raise ValueError('Calibration receipt has no "<chamber>|<source>" strata')
    return cleaned, hashlib.sha256(raw).hexdigest()


def calibration_for(table, chamber, source, contributing=()):
    """Match a stratum by speaker chamber x source; pooled rows carry every contributing stratum."""
    if not table or not chamber:
        return None
    if source != POOLED:
        return table.get('%s|%s' % (chamber, source))
    matched = {}
    for item in sorted(contributing):
        key = '%s|%s' % (chamber, item)
        if key in table:
            matched[key] = table[key]
    return matched or None


# ------------------------------------------------------------ held-out seal

def load_sample(path):
    """Development rows as data; held-out rows contribute a pair_id deny-list and nothing else."""
    development, denied = [], set()
    for row in read_rows(path):
        if row.get('split') == 'development':
            development.append(row)
        else:
            denied.add(str(row.get('pair_id')))
    return development, frozenset(denied)


def pair_id_of(actor, target):
    return '__'.join(sorted((actor, target)))


def assert_no_heldout(rows, denied, label):
    """Refuse any row whose dyad is in the sealed split. Raises; never filters silently."""
    hits = sorted({pair_id_of(r['actor'], r['target']) for r in rows
                   if pair_id_of(r['actor'], r['target']) in denied})
    if hits:
        raise ValueError('Held-out dyads refused in %s: %s' % (label, ', '.join(hits[:5])))
    return len(rows)


# ------------------------------------------------------------------- chamber

def chamber_resolver(members):
    """Speaker chamber on the pair's last observed day, matching the census's own rule.

    The census keyed its calibration strata on roster.chamber_on(actor, day). Rows
    here are aggregates over many days, so the last observed day stands in, and the
    roster's own chamber field is the fallback when no term covers it.
    """
    cache = {}

    def resolve(actor, day):
        key = (actor, day)
        if key not in cache:
            person = members.get(actor)
            if person is None:
                cache[key] = (None, 'member_not_in_roster')
            else:
                term = term_at(person, day) if day else None
                if term:
                    cache[key] = (term['chamber'], 'term_at_last_date')
                elif person.get('chamber'):
                    cache[key] = (person['chamber'], 'roster_chamber_field')
                else:
                    cache[key] = (None, 'unavailable')
        return cache[key]

    return resolve


# ------------------------------------------------------------------- builder

def build(out_dir, *, census_dir=CENSUS, sample_path=None, cases_path=None,
          members_path=None, calibration_path=None, stage=None, progress=print):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    census_dir = Path(census_dir)
    sample_path = Path(sample_path or FROZEN / 'sampled_pairs.ndjson')
    cases_path = Path(cases_path or REGRESSION / 'cases.json')
    members_path = Path(members_path or PILOT / 'members.json')
    stage = stage or (lambda *a, **k: None)

    manifest_path = census_dir / 'manifest.json'
    census_manifest = read_json(manifest_path)
    manifest_sha = digest(manifest_path)

    counts_path = census_dir / 'encounter_counts.ndjson'
    baseline_path = census_dir / 'speaker_baseline.ndjson'
    pinned = {a['name']: a['sha256'] for a in census_manifest.get('artefacts', [])}
    inputs = {}
    for name, path in (('encounter_counts.ndjson', counts_path),
                       ('speaker_baseline.ndjson', baseline_path)):
        actual = digest(path)
        inputs[name] = dict(path=str(path), sha256=actual, manifest_sha256=pinned.get(name),
                            matches_census_manifest=pinned.get(name) == actual)
    inputs['manifest.json'] = dict(path=str(manifest_path), sha256=manifest_sha)
    for name, path in (('sampled_pairs.ndjson', sample_path), ('cases.json', cases_path),
                       ('members.json', members_path)):
        inputs[name] = dict(path=str(path), sha256=digest(path))

    members = read_json(members_path)
    counts = list(read_rows(counts_path))
    baselines = list(read_rows(baseline_path))
    development, denied = load_sample(sample_path)
    cases = read_json(cases_path)
    stage('inputs', '%d encounter rows, %d speaker baselines, %d development pairs, %d benchmark dyads'
          % (len(counts), len(baselines), len(development), len(cases)))

    calibration_table, calibration_sha = None, None
    if calibration_path:
        calibration_table, calibration_sha = load_calibration(calibration_path)
        stage('calibration', '%d strata attached' % len(calibration_table))

    count_index, name_of, pair_sources = {}, {}, defaultdict(set)
    for row in counts:
        count_index[(row['actor'], row['target'], row['source'])] = row
        name_of[row['actor']] = row.get('actor_name')
        name_of[row['target']] = row.get('target_name')
        pair_sources[(row['actor'], row['target'])].add(row['source'])
    baseline_index = {(row['actor'], row['source']): row for row in baselines}
    actor_baselines = defaultdict(list)
    for row in baselines:
        actor_baselines[row['actor']].append(row)
        name_of.setdefault(row['actor'], row.get('actor_name'))
    for bio, person in members.items():
        name_of.setdefault(bio, person.get('name'))

    resolve_chamber = chamber_resolver(members)
    pairs = sorted(pair_sources)
    chamber_basis_counts = defaultdict(int)

    def rows_for_pair(actor, target):
        """Three venue-matched rows plus the pooled row, in a fixed order."""
        per_source = {s: count_index.get((actor, target, s)) for s in SOURCES}
        last = [r['last_date'] for r in per_source.values() if r and r.get('last_date')]
        day = max(last) if last else None
        chamber, basis = resolve_chamber(actor, day)
        chamber_basis_counts[basis] += 1
        contributing = sorted(s for s in SOURCES if per_source.get(s))
        out = []
        for source in SOURCES:
            count = per_source[source] or EMPTY_COUNT
            baseline = baseline_index.get((actor, source)) or EMPTY_BASELINE
            out.append(build_row(actor, target, source, count, baseline,
                                 actor_name=name_of.get(actor), target_name=name_of.get(target),
                                 chamber=chamber, chamber_basis=basis, manifest_sha=manifest_sha,
                                 calibration=calibration_for(calibration_table, chamber, source)))
        out.append(build_row(actor, target, POOLED,
                             pooled_counts([r for r in per_source.values() if r]),
                             pooled_baseline(actor_baselines.get(actor, [])),
                             actor_name=name_of.get(actor), target_name=name_of.get(target),
                             chamber=chamber, chamber_basis=basis, manifest_sha=manifest_sha,
                             calibration=calibration_for(calibration_table, chamber, POOLED,
                                                         contributing)))
        return out

    pooled_index, source_status, leaderboard = {}, {}, []
    variant_status, status_counts = defaultdict(int), defaultdict(int)
    # Per-source rows with n >= 1 are exactly the census's encounter_counts rows, so
    # this reproduces the variant's failure rate on the census's own denominator
    # instead of quoting a figure that could go stale under a recount.
    census_row_variant = defaultdict(int)

    def stream():
        for index, (actor, target) in enumerate(pairs, 1):
            if index % 5000 == 0:
                progress('Expression contrasts: %s of %s directed pairs'
                         % (f'{index:,}', f'{len(pairs):,}'), flush=True)
            for row in rows_for_pair(actor, target):
                status_counts[(row['source'], row['status'])] += 1
                variant_status[(row['source'], row['turn_level_variant']['status'])] += 1
                if row['source'] != POOLED and row['n'] >= 1:
                    census_row_variant['census_rows'] += 1
                    for channel in CHANNELS:
                        if row['turn_level_variant'][channel + '_status'] == VARIANT_UNDEFINED:
                            census_row_variant[channel] += 1
                if row['source'] == POOLED:
                    pooled_index[(actor, target)] = dict(
                        status=row['status'], n=row['n'],
                        warm=row['warm_contrast']['contrast'],
                        hostile=row['hostile_contrast']['contrast'])
                    if row['status'] == AVAILABLE and row['n'] >= LEADERBOARD_MIN_N:
                        leaderboard.append(dict(
                            actor=actor, target=target, actor_name=row['actor_name'],
                            target_name=row['target_name'], n=row['n'],
                            warm=row['warm'], hostile=row['hostile'],
                            warm_contrast=row['warm_contrast']['contrast'],
                            hostile_contrast=row['hostile_contrast']['contrast'],
                            warm_target_rate=row['warm_contrast']['target_rate'],
                            warm_baseline_rate=row['warm_contrast']['baseline_rate'],
                            hostile_target_rate=row['hostile_contrast']['target_rate'],
                            hostile_baseline_rate=row['hostile_contrast']['baseline_rate'],
                            heldout=pair_id_of(actor, target) in denied))
                else:
                    source_status[(actor, target, row['source'])] = row['status']
                yield row

    main_rows = write_rows(out_dir / 'expression_contrasts.ndjson', stream())
    stage('contrasts', '%d rows over %d directed pairs' % (main_rows, len(pairs)))

    def view_rows(dyads, extra):
        out = []
        for key in dyads:
            for row in rows_for_pair(*key):
                out.append(dict(row, **extra[key]))
        return out

    case_dyads, case_extra = [], {}
    for case in cases:
        a, b = case['pair']
        block = dict(dyad_pair_id=pair_id_of(a, b), sign=case['sign'], y=case['y'],
                     dyad_names=case['names'], documented_first=case['first'],
                     documented_directions=[list(d) for d in case['directions']])
        for key in ((a, b), (b, a)):
            case_dyads.append(key)
            case_extra[key] = block
    case_rows = view_rows(case_dyads, case_extra)
    assert_no_heldout(case_rows, denied, 'sign_benchmark_contrasts')
    write_rows(out_dir / 'sign_benchmark_contrasts.ndjson', case_rows)

    dev_dyads, dev_extra = [], {}
    for entry in development:
        a, b = entry['pair']
        block = dict(dyad_pair_id=entry['pair_id'], dyad_names=entry['names'],
                     design_weight=entry['design_weight'], stratum=entry['stratum'],
                     split='development')
        for key in ((a, b), (b, a)):
            dev_dyads.append(key)
            dev_extra[key] = block
    dev_rows = view_rows(dev_dyads, dev_extra)
    assert_no_heldout(dev_rows, denied, 'development_pair_contrasts')
    write_rows(out_dir / 'development_pair_contrasts.ndjson', dev_rows)
    stage('views', '%d benchmark rows, %d development rows' % (len(case_rows), len(dev_rows)))

    diagnostics = diagnose(cases=cases, development=development, pooled_index=pooled_index,
                           source_status=source_status, baselines=baselines, members=members,
                           leaderboard=leaderboard, denied=denied)
    diagnostics['status_counts'] = {'%s|%s' % k: v for k, v in sorted(status_counts.items())}
    diagnostics['turn_level_variant_status'] = {'%s|%s' % k: v for k, v in sorted(variant_status.items())}
    diagnostics['turn_level_variant_undefined_on_census_rows'] = dict(
        census_rows=census_row_variant['census_rows'],
        warm=census_row_variant['warm'], hostile=census_row_variant['hostile'],
        denominator='per-source rows with n >= 1, which are exactly the '
                    'encounter_counts.ndjson rows the census published')
    diagnostics['speaker_chamber_basis'] = dict(sorted(chamber_basis_counts.items()))
    diagnostics['directed_pairs'] = len(pairs)
    diagnostics['rows'] = main_rows
    write_json(out_dir / 'diagnostics.json', diagnostics)

    return dict(inputs=inputs, rows=main_rows, directed_pairs=len(pairs),
                benchmark_rows=len(case_rows), development_rows=len(dev_rows),
                calibration=dict(path=str(calibration_path) if calibration_path else None,
                                 sha256=calibration_sha,
                                 strata=sorted(calibration_table) if calibration_table else None),
                heldout_dyads_denied=len(denied), diagnostics=diagnostics)


# --------------------------------------------------------------- diagnostics

def dyad_value(pooled_index, a, b, key):
    """Direction-average an available pooled contrast over the two orderings."""
    values = []
    for pair in ((a, b), (b, a)):
        block = pooled_index.get(pair)
        if block and block['status'] == AVAILABLE and block[key] is not None:
            values.append(block[key])
    return sum(values) / len(values) if values else None


def dyad_volume(pooled_index, a, b):
    return sum((pooled_index.get(p) or {}).get('n', 0) for p in ((a, b), (b, a)))


def coverage(dyads, pooled_index, source_status):
    """Per source and pooled: dyads with an available contrast in at least one direction."""
    out = {}
    for source in SOURCES:
        hit = 0
        for a, b in dyads:
            if any(source_status.get((x, y, source)) == AVAILABLE for x, y in ((a, b), (b, a))):
                hit += 1
        out[source] = dict(available_in_at_least_one_direction=hit, dyads=len(dyads))
    hit_pooled = both = 0
    for a, b in dyads:
        flags = [(pooled_index.get(p) or {}).get('status') == AVAILABLE for p in ((a, b), (b, a))]
        hit_pooled += any(flags)
        both += all(flags)
    out[POOLED] = dict(available_in_at_least_one_direction=hit_pooled,
                       available_in_both_directions=both, dyads=len(dyads))
    return out


def diagnose(*, cases, development, pooled_index, source_status, baselines, members,
             leaderboard, denied):
    case_dyads = [tuple(c['pair']) for c in cases]
    dev_dyads = [tuple(r['pair']) for r in development]
    out = dict(status='EXPLORATORY',
               coverage=dict(sign_benchmark=coverage(case_dyads, pooled_index, source_status),
                             development_sample=coverage(dev_dyads, pooled_index, source_status)))

    graded = []
    for case in cases:
        a, b = case['pair']
        graded.append(dict(pair_id=pair_id_of(a, b), names=case['names'], sign=case['sign'],
                           warm=dyad_value(pooled_index, a, b, 'warm'),
                           hostile=dyad_value(pooled_index, a, b, 'hostile'),
                           mention_turns=dyad_volume(pooled_index, a, b)))
    scored = [g for g in graded if g['warm'] is not None]
    positives = [g for g in scored if g['sign'] == 'positive']
    negatives = [g for g in scored if g['sign'] == 'negative']
    separation = dict(
        interpretation='sign-among-documented-ties, not detection',
        restricted_to='dyads with an available pooled warm contrast in at least one direction',
        dyads_scored=len(scored), dyads_total=len(graded),
        dropped_no_available_contrast=len(graded) - len(scored),
        warm_contrast=mann_whitney_auc([g['warm'] for g in positives],
                                       [g['warm'] for g in negatives]),
        hostile_contrast=mann_whitney_auc([g['hostile'] for g in positives],
                                          [g['hostile'] for g in negatives]),
        mention_turns_volume=mann_whitney_auc([g['mention_turns'] for g in positives],
                                              [g['mention_turns'] for g in negatives]))
    # A one-sided drop moves the AUC on its own, so record which side lost dyads.
    separation['group_sizes'] = {
        sign: dict(documented=sum(1 for g in graded if g['sign'] == sign),
                   scored=sum(1 for g in scored if g['sign'] == sign),
                   dropped=sorted(g['pair_id'] for g in graded
                                  if g['sign'] == sign and g['warm'] is None))
        for sign in ('positive', 'negative')}
    wide_pos = [g for g in graded if g['sign'] == 'positive' and g['mention_turns'] >= 1]
    wide_neg = [g for g in graded if g['sign'] == 'negative' and g['mention_turns'] >= 1]
    separation['mention_turns_volume_unrestricted'] = mann_whitney_auc(
        [g['mention_turns'] for g in wide_pos], [g['mention_turns'] for g in wide_neg])
    separation['mention_turns_volume_unrestricted']['dyads_scored'] = len(wide_pos) + len(wide_neg)
    separation['per_dyad'] = sorted(graded, key=lambda g: g['pair_id'])
    out['sign_separation'] = separation

    by_stratum = defaultdict(list)
    for row in baselines:
        denominator = int(row.get('target_mention_turn_sum', 0))
        if denominator < 1:
            continue
        chamber = (members.get(row['actor']) or {}).get('chamber')
        rate = (int(row.get('target_warm_turn_sum', 0)) + .5) / (denominator + 1)
        by_stratum[(chamber, row['source'])].append(rate)
        by_stratum[(chamber, POOLED)].append(rate)
    out['baseline_warm_rate'] = dict(
        definition='(target_warm_turn_sum + 0.5) / (target_mention_turn_sum + 1), one value per '
                   'speaker per source; the same smoothing relative_contrast applies to its baseline',
        denominator='speakers with at least one target-mention turn in that source',
        note='the pooled row stacks a speaker once per source they speak in, so it is not a speaker count',
        strata={'%s|%s' % (c or 'unknown', s): median_iqr(v) for (c, s), v in sorted(
            by_stratum.items(), key=lambda kv: (str(kv[0][0]), kv[0][1]))})

    open_rows = [r for r in leaderboard if not r['heldout']]
    out['leaderboards'] = dict(
        minimum_n=LEADERBOARD_MIN_N,
        eligible_directed_pairs=len(leaderboard),
        heldout_directed_pairs_excluded=len(leaderboard) - len(open_rows),
        top_warm=sorted(open_rows, key=lambda r: (-r['warm_contrast'], r['actor'], r['target']))[:15],
        top_hostile=sorted(open_rows,
                           key=lambda r: (-r['hostile_contrast'], r['actor'], r['target']))[:15])
    out['heldout_dyads_in_census_rows'] = sum(1 for r in leaderboard if r['heldout'])
    return out


# -------------------------------------------------------------------- report

def _fmt(value, digits=3):
    return '--' if value is None else f'{value:.{digits}f}'


def report_text(receipt):
    d = receipt['diagnostics']
    calibration = receipt['calibration']
    board = d['leaderboards']
    undef = d['turn_level_variant_undefined_on_census_rows']
    lines = ['# Expression contrasts over the systematic encounter census', '',
             '**STATUS: EXPLORATORY.** Nothing here feeds any engine, rank, dial or published surface. '
             'Every number below is a contrast of *lexical cue* counts, computed mechanically from the '
             'systematic encounter census. A cue is a regex hit, not a reviewed encounter and not a '
             'relationship. No claim on this page is causal.', '',
             '## What was computed', '',
             f'For each of {d["directed_pairs"]:,} directed (actor, target) pairs the census found, one '
             f'row per source in {", ".join("`%s`" % s for s in SOURCES)} plus one pooled row: '
             f'{d["rows"]:,} rows. Each row calls `relative_expression.relative_contrast` twice, once '
             'for warm and once for hostile, with the arguments the census manifest\'s '
             '`denominator_contract` specifies: `n` is the pair\'s `mention_turns` in that source, '
             '`positive` is the matching `<channel>_turns`, `other_n` is the speaker\'s '
             '`target_mention_turn_sum` in that source minus `n`, and `other_positive` is '
             '`target_<channel>_turn_sum` minus `positive`. The contrast is the logit of the shrunk '
             'target rate minus the logit of the speaker\'s own baseline rate: within-speaker, '
             'within-source, leave-this-target-out.', '',
             'Status is `available` when `n >= 1` and `other_n >= 1`, and '
             f'`{INSUFFICIENT}` otherwise. That value is deliberately distinct from '
             '`chamber_expression`\'s `insufficient_systematic_reviewed_exposure`, and every row carries '
             f'`sampling_basis == "{SAMPLING_BASIS}"`, so no mechanical row can be mistaken for, or pass '
             'the gate of, a reviewed one.', '',
             '### The denominator that was not used', '',
             'A second reading of the same two files sets `other_n = colleague_mention_turns - n` and '
             'takes the speaker\'s turn-level `warm_turns` as the other positives. Those are different '
             'units: `colleague_mention_turns` counts distinct turns naming anybody, while `warm_turns` '
             'counts turns carrying a cue whether or not they name anybody. On this census that reading '
             f'puts more positives than opportunities in the baseline on {undef["warm"]:,} of '
             f'{undef["census_rows"]:,} warm rows and {undef["hostile"]:,} hostile rows ({undef["denominator"]}), '
             'which `relative_contrast` rejects outright. It is computed anyway, per row, under '
             f'`turn_level_variant`, with status `{VARIANT_UNDEFINED}` on exactly those rows, so the '
             'difference can be audited rather than taken on trust.', '',
             '| Row family | Status | Rows |', '|---|---|---:|']
    for key, value in sorted(d['status_counts'].items()):
        source, status = key.split('|', 1)
        lines.append(f'| `{source}` | {status} | {value:,} |')
    lines += ['', '| Row family | `turn_level_variant` status | Rows |', '|---|---|---:|']
    for key, value in sorted(d['turn_level_variant_status'].items()):
        source, status = key.split('|', 1)
        lines.append(f'| `{source}` | {status} | {value:,} |')

    lines += ['', '## (a) Coverage', '',
              'Every figure is a count over a stated denominator. A dyad with no available contrast is '
              'a retrieval nonresponse: the speaker never named the other member in that source, or '
              'named nobody else, so there is no within-speaker comparison to make.', '',
              '| Set | Source | Dyads with an available contrast in >=1 direction | Dyads |',
              '|---|---|---:|---:|']
    for label, key in (('29 sign-benchmark dyads', 'sign_benchmark'),
                       ('180 development dyads', 'development_sample')):
        block = d['coverage'][key]
        for source in list(SOURCES) + [POOLED]:
            item = block[source]
            lines.append(f'| {label} | `{source}` | '
                         f'{item["available_in_at_least_one_direction"]} | {item["dyads"]} |')
    for label, key in (('29 sign-benchmark dyads', 'sign_benchmark'),
                       ('180 development dyads', 'development_sample')):
        block = d['coverage'][key][POOLED]
        lines.append(f'| {label} | `pooled`, BOTH directions | '
                     f'{block["available_in_both_directions"]} | {block["dyads"]} |')

    sep = d['sign_separation']
    lines += ['', '## (b) Sign among documented ties', '',
              'This is **not** a detection result. Both groups were selected because a tie of a known '
              'sign is already documented; the only question asked is whether the mechanical contrast '
              'orders the documented-positive dyads above the documented-negative ones. The estimate '
              'is a Mann-Whitney AUC with half credit for ties, computed only over dyads carrying an '
              f'available pooled warm contrast: {sep["dyads_scored"]} of {sep["dyads_total"]} dyads, '
              f'{sep["dropped_no_available_contrast"]} dropped for no available contrast. The n_pos and '
              'n_neg columns below are the surviving group sizes, not the group sizes the benchmark '
              'started with; read the AUC against those.', '',
              '**The drop is one-sided.** '
              + '; '.join('%s: %d of %d documented dyads scored%s'
                          % (sign, sep['group_sizes'][sign]['scored'],
                             sep['group_sizes'][sign]['documented'],
                             (', dropped ' + ', '.join('`%s`' % p for p in
                                                       sep['group_sizes'][sign]['dropped']))
                             if sep['group_sizes'][sign]['dropped'] else '')
                          for sign in ('positive', 'negative'))
              + '. Losing dyads from one side alone changes the AUC by itself, independently of how '
                'well the contrast orders anything, so this comparison is not between the groups the '
                'benchmark was built to compare.', '',
              '| Ranking quantity | AUC | n_pos | n_neg | Comparisons | Tied comparisons |',
              '|---|---:|---:|---:|---:|---:|']
    for label, key in (('Pooled warm contrast (direction-averaged)', 'warm_contrast'),
                       ('Pooled hostile contrast (direction-averaged)', 'hostile_contrast'),
                       ('Raw pooled mention turns (volume), same dyads', 'mention_turns_volume'),
                       ('Raw pooled mention turns, every dyad with >=1 mention',
                        'mention_turns_volume_unrestricted')):
        block = sep[key]
        lines.append(f'| {label} | {_fmt(block["auc"])} | {block["n_pos"]} | {block["n_neg"]} | '
                     f'{block["comparisons"]} | {block["ties"]} |')
    lines += ['',
              'The volume rows are the control the reader needs: if mention volume alone orders the '
              'dyads as well as the contrast does, the contrast has added nothing here. With n_pos and '
              'n_neg this small, none of these AUCs separates from chance on its own.']

    lines += ['', '## (c) Ordinary chamber warmth', '',
              'Speaker baseline warm rate is ' + d['baseline_warm_rate']['definition'] + '. '
              'Denominator: ' + d['baseline_warm_rate']['denominator'] + '. Note that ' +
              d['baseline_warm_rate']['note'] + '.', '',
              '| Speaker chamber | Source | Speakers | Median | Q1 | Q3 | IQR |',
              '|---|---|---:|---:|---:|---:|---:|']
    for key, block in d['baseline_warm_rate']['strata'].items():
        chamber, source = key.split('|', 1)
        lines.append(f'| {chamber} | `{source}` | {block["n"]:,} | {_fmt(block["median"], 4)} | '
                     f'{_fmt(block["q1"], 4)} | {_fmt(block["q3"], 4)} | {_fmt(block["iqr"], 4)} |')

    lines += ['', '## (d) Highest mechanical contrasts', '',
              f'Directed pairs with pooled `n >= {board["minimum_n"]}` and an available contrast: '
              f'{board["eligible_directed_pairs"]:,}. '
              f'{board["heldout_directed_pairs_excluded"]:,} directed pairs belonging to the sealed '
              'held-out split are excluded from both tables. A high contrast means the cue regex fired '
              'more often near this target than near this speaker\'s other targets; with uncalibrated '
              'cues it is a retrieval statistic, not a finding.', '',
              '### Top 15 directed pairs by pooled warm contrast', '',
              '| Actor | Target | n | Warm turns | Target rate | Baseline rate | Contrast |',
              '|---|---|---:|---:|---:|---:|---:|']
    for row in board['top_warm']:
        lines.append(f'| {row["actor_name"]} | {row["target_name"]} | {row["n"]} | {row["warm"]} | '
                     f'{_fmt(row["warm_target_rate"], 4)} | {_fmt(row["warm_baseline_rate"], 4)} | '
                     f'{_fmt(row["warm_contrast"])} |')
    lines += ['', '### Top 15 directed pairs by pooled hostile contrast', '',
              '| Actor | Target | n | Hostile turns | Target rate | Baseline rate | Contrast |',
              '|---|---|---:|---:|---:|---:|---:|']
    for row in board['top_hostile']:
        lines.append(f'| {row["actor_name"]} | {row["target_name"]} | {row["n"]} | {row["hostile"]} | '
                     f'{_fmt(row["hostile_target_rate"], 4)} | '
                     f'{_fmt(row["hostile_baseline_rate"], 4)} | {_fmt(row["hostile_contrast"])} |')

    lines += ['', '## Calibration', '']
    if calibration['sha256']:
        lines += ['Per-stratum cue precision and recall copied verbatim into every row\'s '
                  '`calibration` field, matched by speaker chamber x source. Receipt sha256 '
                  f'`{calibration["sha256"]}`, strata: '
                  f'{", ".join("`%s`" % s for s in calibration["strata"])}.']
    else:
        lines += ['No calibration receipt was attached, so every row carries `calibration: null`. '
                  'Until `cue_precision_recall.json` exists, the cue regexes have unknown precision '
                  'and recall, and a contrast between two uncalibrated rates has an unknown '
                  'relationship to the quantity it is named for.']

    lines += ['', '## Held-out discipline', '',
              f'{receipt["heldout_dyads_denied"]} held-out dyads are loaded as a `pair_id` deny-list '
              'only. No held-out label, weight, stratum or review is read. Both derived views refuse a '
              'held-out dyad by raising, and the leaderboards exclude them. The census-wide file '
              'mirrors the census and therefore still contains mechanical rows for held-out dyads '
              f'({d["heldout_dyads_in_census_rows"]:,} directed pairs at n >= {board["minimum_n"]}); '
              'those rows are cue-blind counts the census already published, but a reader should not '
              'browse them before the held-out review.', '',
              '## What this does not establish', '',
              'Cue counts are lexical retrieval. A warm contrast can be high because a speaker uses '
              'one stock phrase about one colleague, because a floor ritual repeats, or because the '
              'regex misfires; it can be low where warmth was expressed in words the regex does not '
              'hold. Mention volume tracks floor time, committee role and media appearance rates, '
              'which this census does not separate. Nothing here is evidence about private relations, '
              'and no row here can enter `chamber_expression.matched_expression`.', '',
              '| Artefact | Bytes | sha256 |', '|---|---:|---|']
    for item in receipt['artefacts']:
        lines.append(f'| `{item["name"]}` | {item["bytes"]:,} | `{item["sha256"]}` |')
    lines += ['', f'Wall clock {receipt["runtime_seconds"]:,.1f} s. Glassbox run id '
              f'`{receipt["glassbox_run_id"]}`. Census manifest sha256 '
              f'`{receipt["inputs"]["manifest.json"]["sha256"]}`.']
    return '\n'.join(lines) + '\n'


# --------------------------------------------------------------------- entry

def main(argv=None):
    try:
        from fec.surfaces.glassbox_emit import emit, new_run_id
    except ImportError:  # pragma: no cover - path-based fallback to the same file
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'glassbox_emit', ROOT / 'fec/surfaces/glassbox_emit.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        emit, new_run_id = module.emit, module.new_run_id

    parser = argparse.ArgumentParser(
        description='Mechanical within-speaker, venue-matched expression contrasts (EXPLORATORY)')
    parser.add_argument('--out', default=str(OUT))
    parser.add_argument('--census', default=str(CENSUS))
    parser.add_argument('--attach-calibration', dest='calibration', default=None,
                        help='path to cue_precision_recall.json')
    args = parser.parse_args(argv)

    run_id = new_run_id('mpr-expression-contrasts')
    started = time.time()

    def stage(name, summary, **metadata):
        emit('stage', 'running', summary, run_id=run_id, stage=name,
             source='member_personal_relationships',
             duration_ms=int((time.time() - started) * 1000), metadata=metadata or None)

    emit('task', 'started', 'Expression contrast consumer opening', run_id=run_id, stage='start',
         source='member_personal_relationships',
         metadata=dict(out=args.out, calibration=args.calibration))
    try:
        receipt = build(args.out, census_dir=args.census, calibration_path=args.calibration,
                        stage=stage)
        out_dir = Path(args.out)
        names = ['expression_contrasts.ndjson', 'sign_benchmark_contrasts.ndjson',
                 'development_pair_contrasts.ndjson', 'diagnostics.json']
        receipt['artefacts'] = [dict(name=n, bytes=(out_dir / n).stat().st_size,
                                     sha256=digest(out_dir / n)) for n in names]
        receipt['status'] = 'EXPLORATORY'
        receipt['glassbox_run_id'] = run_id
        receipt['runtime_seconds'] = round(time.time() - started, 1)
        receipt['sampling_basis'] = SAMPLING_BASIS
        receipt['classifier'] = CLASSIFIER
        (out_dir / 'REPORT.md').write_text(report_text(receipt), encoding='utf-8')
        receipt['artefacts'].append(dict(name='REPORT.md',
                                         bytes=(out_dir / 'REPORT.md').stat().st_size,
                                         sha256=digest(out_dir / 'REPORT.md')))
        write_json(out_dir / 'run_receipt.json', receipt)
        emit('task', 'completed', 'Expression contrasts written', run_id=run_id, stage='done',
             source='member_personal_relationships',
             duration_ms=int((time.time() - started) * 1000),
             metadata=dict(rows=receipt['rows'], directed_pairs=receipt['directed_pairs']))
        print('Wrote %s rows for %s directed pairs to %s in %.1f s'
              % (f'{receipt["rows"]:,}', f'{receipt["directed_pairs"]:,}', out_dir,
                 receipt['runtime_seconds']))
        return 0
    except Exception as error:
        emit('task', 'failed', 'Expression contrasts failed: %s' % error, run_id=run_id,
             stage='error', source='member_personal_relationships',
             duration_ms=int((time.time() - started) * 1000))
        raise


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
