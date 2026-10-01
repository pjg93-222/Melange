"""Universe-wide pair scoring with explicit states and no imputation across a missing channel.

STATUS: EXPLORATORY. Nothing here feeds any engine, rank, dashboard or production
surface. Every figure produced by this module is a ranking or grading summary over
reviewed research evidence, printed with its own denominator.

What this module does, and only this. It takes the lane's existing fitted
development model -- the cumulative-logit ``ordinal_degrees.OrdinalDegrees`` family
that ``run_chamber_degrees.py`` fits on the 73 dated v6 degree records -- and applies
it to every unordered pair of members in the lane's member panel at one stated
reference date. It emits three separate blocks per pair, exactly as P1-6 asks:

    estimate              expected grade and grade probabilities per axis and direction
    evidence_availability the denominators behind that estimate, never folded into it
    confidence            bootstrap standard error of the estimate over source-resampled
                          refits of the development model; never the model probability

Two axes, affinity and friction, are reported side by side and are never combined
into one signed number (ruling P1-8: the sign benchmark is a diagnostic only).

Rulings this module implements, all ratified 2026-09-10.

  Ruling: canonical work features are original-signature, strict-before, exactly the
  canonical row C1 of ``20260910_benchmark_contract/CONTRACT.md``. The work columns
  come from ``chamber_work.temporal_features`` with the unmodified serialized bill
  panel, evaluated strictly before the reference date.

  Ruling 7: visibility features -- mention volume, fame proxies, activity counts --
  leave the estimate and move into the evidence-availability block. The estimate
  feature list is therefore ``run_chamber_degrees.CONTEXT + WORK`` with the two
  ``*_log_interview_words`` columns removed, and nothing else changed. The removed
  columns reappear under ``evidence_availability.visibility``.

  P1-11: missing work is evidence availability, never a mean-imputed feature. When
  the work channel is absent for a pair the estimate is not produced at all: the
  prediction state becomes ``not_scored:<reason>`` naming the missing channel. The
  model's own train-fitted missingness-indicator encoding still handles individual
  missing context cells inside a present channel, because that encoding is part of
  the fitted model and removing it would be a different model family. That carve-out
  is stated in REPORT.md rather than hidden here.

  P1-10: no new personality terms. The primary specification carries none. The sign
  diagnostic reuses the benchmark contract's own stored R0_novis feature list
  unchanged, personality columns included, because that list is the existing
  canonical row and is reproduced, not designed here.

Held-out discipline. The 120 ``split == 'heldout'`` pairs of the frozen probability
sample are scored like every other pair in ``pair_scores.ndjson`` and carry a
``heldout`` flag. They are refused, by assertion and not by silent filtering, from
every validation table, every diagnostic and every figure in REPORT.md, and both
REPORT.md and validation_predictions.ndjson are scanned for their pair ids before
the run is allowed to succeed. No held-out label is read: ``sampled_pairs.ndjson``
carries ``affinity: null`` for every row and ``labels_v1.ndjson`` contains
development rows only, which this module asserts.

Known panel gap. ``data.py``'s roster join drops Lindsey Graham (G000359), so no
pair involving him exists in this universe. That is recorded, never imputed.

This module writes only under the directory given by --out. It changes no existing
file and reruns no existing artefact.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import itertools
import json
import math
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .data import ROOT, digest, read_json, write_json
from .chamber_work import WORK_FIELDS, temporal_features, term_on
from .history_work import congress_end
from .ordinal_degrees import OrdinalDegrees, training_indices
from .run_chamber_degrees import CONTEXT as V6_CONTEXT, WORK as V6_WORK
from .work_baseline import SHRINKAGE, load_nominate

OUTPUTS = ROOT / 'outputs/member_personal_relationships'
HISTORY = OUTPUTS / '20260910_full_history'
HISTORY_115 = OUTPUTS / '20260911_full_history_115_119'
FROZEN = OUTPUTS / '20260910_frozen_v5'
V6 = OUTPUTS / '20260910_chamber_degrees_v6'
REGRADE = OUTPUTS / '20260911_v6_regrade'
CONTRASTS = OUTPUTS / '20260910_expression_contrasts'
CENSUS = OUTPUTS / '20260910_systematic_encounters'
SAMPLE_LABELS = OUTPUTS / '20260910_probability_sample_labels'
REGRESSION = OUTPUTS / '20260910_regression'
BENCH = OUTPUTS / '20260910_benchmark_contract'
OUT = OUTPUTS / '20260911_pair_scores'
NOMINATE_FILE = ROOT / 'votes/HSall_members.csv'

STATUS = 'EXPLORATORY'
# The serialized bill panel was read with cutoff 2026-09-10, so "strictly before
# 2026-09-11" admits the whole panel and nothing beyond it.
REFERENCE_DATE = '2026-09-11'
DEFAULT_CONGRESS_RANGE = (116, 119)
SEED = 20260911
BOOTSTRAP = 200
SIGN_SEED = 20260910
SIGN_BOOTSTRAP = 10000
PENALTY = 1.0
AXES = ('affinity', 'friction')
GRADES = np.arange(5)
VENUES = ('CHRG', 'CREC', 'INTERVIEW')
POOLED = 'pooled'
CHUNK = 40000
MIN_AUC_CLASS = 5
ARTEFACTS = ['pair_scores.ndjson', 'validation_predictions.ndjson', 'validation_tables.json',
             'sign_diagnostic.json', 'label_states_summary.json']
PANEL_GAPS = {'G000359': 'Lindsey Graham is absent from the lane member panel built by data.py; '
                         'every pair involving him is absent from this universe, not scored as '
                         'missing'}

# ------------------------------------------------------------------ states

WORK_AVAILABLE = 'prior_original_work_available'
WORK_NO_HISTORY = 'no_history_before_date'
WORK_CROSS_CHAMBER = 'cross_chamber_not_measured'
WORK_NO_MEMBERSHIP = 'no_dated_membership_on_reference_date'
WORK_NO_RESIDUAL = 'work_residuals_absent'
# Directed residuals can leave one direction of a pair covered and the other not, which
# the undirected substitution above can never produce (it applies one value to both
# directions or neither). This state names that one missing direction, not the pair.
WORK_NO_BASELINE_ROW = 'no_baseline_row'
WORK_STATES = (WORK_AVAILABLE, WORK_NO_HISTORY, WORK_CROSS_CHAMBER, WORK_NO_MEMBERSHIP,
               WORK_NO_RESIDUAL, WORK_NO_BASELINE_ROW)

SPEECH_AVAILABLE = 'available'
SPEECH_NO_MENTIONS = 'no_mentions'
SPEECH_INSUFFICIENT = 'insufficient_systematic_exposure'
SPEECH_STATES = (SPEECH_AVAILABLE, SPEECH_NO_MENTIONS, SPEECH_INSUFFICIENT)

SCORED = 'scored'
LABEL_NOT_ASSESSED = 'not_assessed'
LABEL_SIGN = 'sign_dyad'
LABEL_DEGREE = 'degree_record'
LABEL_SAMPLE_GRADED = 'probability_sample_graded'
LABEL_SAMPLE_NO_EVIDENCE = 'probability_sample_no_evidence'
LABEL_STATES = (LABEL_SIGN, LABEL_DEGREE, LABEL_SAMPLE_GRADED, LABEL_SAMPLE_NO_EVIDENCE,
                LABEL_NOT_ASSESSED)

# The chamber_work builder's own vocabulary, mapped one-for-one onto the explicit
# states P1-5 asks for. Nothing is collapsed and nothing becomes a zero.
WORK_STATUS_MAP = {'prior_original_work_available': WORK_AVAILABLE,
                   'no_prior_covered_work': WORK_NO_HISTORY,
                   'cross_chamber_structurally_unavailable': WORK_CROSS_CHAMBER}

NOMINATE_RANKS = {2: 'per_congress', 1: 'static_members_json_hs119', 0: 'absent_not_imputed'}

# P1-5 asks for the window and the denominator "in the cell or its adjacent receipt".
# Each pair row carries the window and every denominator as a value; the prose that
# defines each one is written once, here and into run_receipt.json, instead of being
# repeated 141,246 times inside the ndjson.
DEFINITIONS = {
    'window.timing': 'a bill enters the work panel only if it was introduced strictly before the '
                     'reference date; the cutoff selects history, not a signature-joining window',
    'window.signatures': 'original signatures only, exactly as history_work.read_history created '
                         'the flag from the per-cosponsor isOriginalCosponsor field',
    'work.eligible_target_sponsored_bills': 'chamber_work.py:124 denominator: bills sponsored by '
                                            'the target on which the actor was an eligible '
                                            'non-sponsor in the same chamber, introduced strictly '
                                            'before the reference date',
    'work.shared_eligible_bills': 'bills of the pair chamber, introduced strictly before the '
                                  'reference date, for which a single dated term of each member '
                                  'covered the introduction day and neither member is the sponsor',
    'work.shared_original_bills': 'bills both members signed as original cosponsors inside that '
                                  'same window',
    'work.co_service_years': 'years both members held a dated term in the same chamber up to the '
                             'reference date; a cross-chamber pair has none by construction and '
                             'is stated as cross_chamber_not_measured rather than zero',
    'speech.mention_turns_by_venue': 'mention_turns published by the systematic encounter census '
                                     'for that directed pair and venue; a venue with no row is a '
                                     'measured zero of turns, not a missing measurement',
    'speech.pooled_mention_turns': 'the n of the pooled expression-contrast row, the number of '
                                   'speaker turns the warm and hostile contrasts are computed on',
    'confidence.bootstrap_standard_error': 'the standard deviation of the expected grade over '
                                           'source-resampled refits of the development model, '
                                           'resampling whole evidence-family components of the '
                                           'labelled rows; never the model probability',
    'estimate.probability_by_grade': 'the fitted cumulative-logit probability of each of the five '
                                     'ordinal grades; it describes observed reviewed assessments, '
                                     'not private feelings',
    'visibility': 'the interview-volume columns that left the estimate under ruling 7; they are '
                  'evidence availability here and are not features of any estimate above',
}

# ------------------------------------------------------------------ features

VISIBILITY_OUT_OF_ESTIMATE = ['actor_log_interview_words', 'target_log_interview_words']
ESTIMATE_CONTEXT = [n for n in V6_CONTEXT if n not in VISIBILITY_OUT_OF_ESTIMATE]
ESTIMATE_WORK = list(V6_WORK)
# Bill-rate work columns. co_service_years is a dated service count, not a bill-rate
# feature, so the residual substitution below leaves it alone.
RAW_WORK_COLUMNS = ESTIMATE_WORK + ['issue_similarity']
WORK_CHANNEL = ESTIMATE_WORK + ['issue_similarity', 'co_service_years']
SPEECH_FEATURES = ['speech_warm_contrast', 'speech_hostile_contrast']
RESIDUAL_FEATURES = ['work_rate_ratio_shrunk', 'work_residual']
# The pooled work-baseline row is undirected and carries these column names.
RESIDUAL_COLUMN_SOURCE = ('shrunken_rate_ratio', 'residual')
RESIDUAL_COUNT_COLUMNS = ('original_cosponsorships', 'eligible_opportunities', 'expected',
                          'residual', 'shrunken_rate_ratio', 'state')
# The producer's directed, per-congress row (pair_work_residuals.ndjson). residual and
# shrunken_rate_ratio are read here only to be discarded: this module pools n, N and
# expected itself across congresses per (signer, sponsor) direction and recomputes both,
# so a caller can never substitute a per-congress figure where a pooled one belongs.
DIRECTED_RESIDUAL_INPUT_COLUMNS = ('signer', 'sponsor', 'original_cosponsorships',
                                   'eligible_opportunities', 'expected', 'state')
NOMINATE_COLUMNS = ('actor_dw1', 'target_dw1', 'actor_dw2', 'target_dw2', 'dw1_distance')
# Everything chamber_work.temporal_features emits. The training rows take these from a
# rebuild on the run's own bill panel so the fit and the universe never sit on two
# different panels; on the frozen default that rebuild must reproduce v6 exactly.
BUILDER_COLUMNS = tuple(WORK_FIELDS) + ('chamber', 'work_status', 'shared_original_bills',
                                        'original_a_to_b', 'original_b_to_a',
                                        'opportunities_a_to_b', 'opportunities_b_to_a',
                                        'co_service_years')
FROZEN_DEFAULT_RANGE = (116, 119)
# chamber_work accumulates through float32 matrix products. BLAS may reorder that
# reduction between runs, so two builds of one panel can differ by about float32 eps.
FLOAT32_TOLERANCE = 1e-5

SPECS = {
    'joint': dict(features=ESTIMATE_CONTEXT + ESTIMATE_WORK, chamber_slopes=True, channel='work',
                  partial=False,
                  basis='run_chamber_degrees.py MODELS["G2_chamber_context_work"] with the two '
                        'visibility columns removed under ruling 7; no other change'),
    'work_only': dict(features=WORK_CHANNEL, chamber_slopes=False, channel='work', partial=True,
                      basis='the same OrdinalDegrees family restricted to the work channel; a '
                            'partial view, not one of the five fitted G-models'),
    'speech_only': dict(features=SPEECH_FEATURES, chamber_slopes=False, channel='speech',
                        partial=True,
                        basis='the same OrdinalDegrees family restricted to the mechanical '
                              'within-speaker expression contrasts; a partial view, not one of '
                              'the five fitted G-models'),
}
SPEC_ORDER = ('joint', 'work_only', 'speech_only')


def substitute_work(names):
    """Replace the raw bill-rate work columns by the baseline residual columns, in place."""
    out, inserted = [], False
    for name in names:
        if name in RAW_WORK_COLUMNS:
            if not inserted:
                out.extend(RESIDUAL_FEATURES)
                inserted = True
            continue
        out.append(name)
    return out


def spec_features(spec_name, residuals_active):
    names = list(SPECS[spec_name]['features'])
    if residuals_active and SPECS[spec_name]['channel'] == 'work':
        names = substitute_work(names)
    return names


# ------------------------------------------------------------------ small io


def read_rows(path):
    with Path(path).open(encoding='utf-8') as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def write_rows(path, rows):
    written = 0
    with Path(path).open('w', encoding='utf-8', newline='\n') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False,
                                    separators=(',', ':')) + '\n')
            written += 1
    return written


def num(value, places=6):
    """The one place a value becomes JSON: None and non-finite both become null."""
    if value is None:
        return None
    value = float(value)
    if not math.isfinite(value):
        return None
    return round(value, places)


def clean(value):
    """numpy-safe JSON coercion, same contract as regression.clean_json."""
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [clean(v) for v in value]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return num(value)
    return value


def finite_or_none(value):
    """A non-finite float means "no measurement"; so does null. Both become None."""
    if isinstance(value, (float, np.floating)) and not math.isfinite(float(value)):
        return None
    return value


def pair_id_of(a, b):
    return '__'.join(sorted((a, b)))


def relative(path):
    path = Path(path)
    try:
        return str(path.relative_to(ROOT)).replace('\\', '/')
    except ValueError:
        return str(path)


def noop(*args, **kwargs):
    return None


def parse_congress_range(text):
    """'116-119' or '118' or '115,116' -> an inclusive (low, high) pair of congresses."""
    if not isinstance(text, str):
        values = sorted(int(c) for c in text)
        return (values[0], values[-1])
    cleaned = str(text).strip()
    if '-' in cleaned:
        low, high = (part.strip() for part in cleaned.split('-', 1))
        low, high = int(low), int(high)
    else:
        values = sorted(int(part) for part in cleaned.split(',') if part.strip())
        low, high = values[0], values[-1]
    if high < low:
        raise argparse.ArgumentTypeError('--congress-range runs backwards: %s' % text)
    if low < 1 or high > 500:
        raise argparse.ArgumentTypeError('--congress-range is not a plausible congress: %s' % text)
    return (low, high)


def congress_of(day, congress_range):
    """Which congress of the requested range covers this day; None outside the range."""
    low, high = congress_range
    for congress in range(low, high + 1):
        if congress_end(congress - 1) <= day < congress_end(congress):
            return congress
    return None


# ------------------------------------------------------------- held-out seal


def assert_no_heldout(pair_ids, denied, label):
    """Refuse any held-out dyad. Raises with the offending ids; never filters silently."""
    pair_ids = list(pair_ids)
    hits = sorted({p for p in pair_ids if p in denied})
    if hits:
        raise ValueError('Held-out dyads refused in %s: %s' % (label, ', '.join(hits[:5])))
    return len(pair_ids)


def assert_text_free_of_heldout(text, denied, label):
    """No held-out pair id may be printed anywhere in a reported artefact."""
    hits = sorted(p for p in denied if p in text)
    if hits:
        raise ValueError('Held-out pair ids appear in %s: %s' % (label, ', '.join(hits[:5])))
    return len(denied)


def load_sample(path):
    """Held-out rows contribute a pair_id deny-list and nothing else; no label is read."""
    development, denied, leaked = [], set(), []
    for row in read_rows(path):
        if row.get('split') == 'development':
            development.append(row)
            continue
        denied.add(str(row['pair_id']))
        for field in ('affinity', 'antagonism'):
            if row.get(field) is not None:
                leaked.append((row['pair_id'], field))
    if leaked:
        raise ValueError('Held-out rows carry a label this module must not read: %r' % leaked[:5])
    return development, frozenset(denied)


# ------------------------------------------------------------------- inputs


def read_bills_in_range(path, congress_range):
    """Read an already-reshaped bill panel with our own congress bound.

    ``history_work.read_history`` hard-filters 116 <= congress <= 119 while it builds
    a panel from the raw source, so reading a wider serialized panel back through it
    would silently lose the 115th. This reader applies the requested bound instead,
    exactly as ``benchmark_contract.read_bills_in_range`` does.
    """
    low, high = congress_range
    every = list(read_rows(path))
    if not every:
        raise ValueError('Bill panel is empty: %s' % path)
    bills = [b for b in every if low <= int(b['congress']) <= high]
    audit = dict(source_path=relative(path), source_records=len(every), included_bills=len(bills),
                 excluded_outside_range=len(every) - len(bills), congress_range=[low, high],
                 bills_by_congress=dict(sorted(Counter(int(b['congress']) for b in bills).items())))
    return bills, audit


def pooled_expression(path):
    """One pooled row per directed pair; the per-venue counts come from the census itself."""
    pooled = {}
    for row in read_rows(path):
        if row['source'] != POOLED:
            continue
        key = (row['actor'], row['target'])
        if key in pooled:
            raise ValueError('Two pooled expression rows for one directed pair: %r' % (key,))
        pooled[key] = dict(status=row['status'], n=row['n'],
                           warm=row['warm_contrast']['contrast'],
                           hostile=row['hostile_contrast']['contrast'],
                           speaker_total_turns=row.get('speaker_total_turns'),
                           speaker_distinct_targets=row.get('speaker_distinct_targets'),
                           speaker_target_mention_turns=row.get('speaker_target_mention_turns'))
    if not pooled:
        raise ValueError('No pooled expression rows found in %s' % path)
    return pooled


def encounter_volume(path):
    """mention_turns by venue, per directed pair: the census's own published counts."""
    volume = defaultdict(dict)
    for row in read_rows(path):
        volume[(row['actor'], row['target'])][row['venue']] = int(row['mention_turns'])
    return dict(volume)


def load_residuals(path):
    """Baseline work residuals, keyed by the undirected pair id the pooled file uses.

    ``20260911_work_baseline/pair_work_pooled.ndjson`` is one row per unordered pair,
    pooled over chambers and congresses. It carries no direction, so both directions
    of a pair receive the same substituted columns and the receipt says so.
    """
    rows, seen, states = {}, 0, Counter()
    for row in read_rows(path):
        seen += 1
        key = str(row['pair_id'])
        for field in RESIDUAL_COUNT_COLUMNS:
            if field not in row:
                raise ValueError('Work-residual row is missing %r: %r' % (field, sorted(row)))
        if key in rows:
            raise ValueError('Two work-residual rows for one pair: %s' % key)
        states[row['state']] += 1
        entry = {target: row[source]
                 for source, target in zip(RESIDUAL_COLUMN_SOURCE, RESIDUAL_FEATURES)}
        entry['counts'] = {field: row[field] for field in RESIDUAL_COUNT_COLUMNS}
        rows[key] = entry
    if not rows:
        raise ValueError('Work-residual file is empty: %s' % path)
    return rows, dict(rows_read=seen, pairs=len(rows), directed=False,
                      states=dict(sorted(states.items())),
                      source_columns=list(RESIDUAL_COLUMN_SOURCE),
                      substituted_columns=list(RESIDUAL_FEATURES))


def load_residuals_directed(path):
    """Baseline work residuals, pooled per directed (signer, sponsor) pair across congresses.

    ``pair_work_residuals.ndjson`` is the producer's one-row-per-(signer, sponsor,
    congress) fit, never pooled across direction: two directed rows for one unordered
    pair (i -> j and j -> i) are only ever pooled together by ``pair_id``, which is how
    ``pair_work_pooled.ndjson`` -- and this module's undirected ``--work-residuals`` --
    lose the direction. This function pools only across congress, for one exact
    (signer, sponsor) direction at a time, so the two directions of a pair can end up
    with different substituted values, or with one present and the other absent, exactly
    as the producer's own per-direction fits allow.

    Pooling reproduces ``work_baseline.py``'s own convention (SHRINKAGE = 0.5): sum n, N
    and expected across congresses, then residual = n - expected and shrunken_rate_ratio
    = (n + SHRINKAGE) / (expected + SHRINKAGE). The per-congress residual and
    shrunken_rate_ratio columns already on each row are read only for the schema check
    below and are never reused, so a caller can never average an already-shrunk ratio.
    """
    totals = {}
    seen = 0
    for row in read_rows(path):
        seen += 1
        for field in DIRECTED_RESIDUAL_INPUT_COLUMNS:
            if field not in row:
                raise ValueError('Directed work-residual row is missing %r: %r'
                                 % (field, sorted(row)))
        if row['state'] != 'measured':
            raise ValueError('Directed work-residual row is not state "measured": %r' % row)
        key = (str(row['signer']), str(row['sponsor']))
        cell = totals.setdefault(key, dict(n=0.0, N=0.0, expected=0.0, congresses=0))
        cell['n'] += float(row['original_cosponsorships'])
        cell['N'] += float(row['eligible_opportunities'])
        cell['expected'] += float(row['expected'])
        cell['congresses'] += 1
    if not totals:
        raise ValueError('Directed work-residual file is empty: %s' % path)
    pooled = {}
    for key, cell in totals.items():
        n, big_n, expected = cell['n'], cell['N'], cell['expected']
        residual = n - expected
        ratio = (n + SHRINKAGE) / (expected + SHRINKAGE)
        counts = dict(original_cosponsorships=int(round(n)), eligible_opportunities=int(round(big_n)),
                     expected=expected, residual=residual, shrunken_rate_ratio=ratio,
                     state='measured', rows_pooled=cell['congresses'])
        pooled[key] = dict(work_rate_ratio_shrunk=ratio, work_residual=residual, counts=counts)
    return pooled, dict(rows_read=seen, directions=len(pooled), directed=True,
                        source_columns=list(DIRECTED_RESIDUAL_INPUT_COLUMNS),
                        substituted_columns=list(RESIDUAL_FEATURES),
                        pooling='summed original_cosponsorships, eligible_opportunities and '
                                'expected across congresses for one (signer, sponsor) direction; '
                                'residual = n - expected; shrunken_rate_ratio = '
                                '(n + %s) / (expected + %s), work_baseline.SHRINKAGE'
                                % (SHRINKAGE, SHRINKAGE))


def residual_for_direction(inputs, actor, target):
    """The one active residual entry for exactly one direction, whichever mode is active.

    Undirected: the pooled entry never carries a direction, so both directions of a pair
    read the same entry under the pair's undirected id, exactly as before this option
    existed. Directed: the exact (actor, target) tuple is the lookup key, so the two
    directions of one pair can read different entries, or one can be absent while the
    other is present.
    """
    directed = inputs.get('residuals_directed')
    if directed is not None:
        return directed.get((actor, target)), WORK_NO_BASELINE_ROW
    return inputs['residuals'].get(pair_id_of(actor, target)), WORK_NO_RESIDUAL


# ------------------------------------------------- eligibility, own accounting


def single_term_intervals(member):
    """Maximal day ranges where exactly one dated term covers the day.

    ``chamber_work.term_on`` returns a term only when exactly one covers the day, so
    an overlapping pair of terms is not an opportunity. Segmenting on the sorted term
    boundaries reproduces that rule exactly: the covering set is constant inside a
    segment, so deciding once per segment is deciding once per day.
    """
    terms = member['terms']
    edges = sorted({t[k] for t in terms for k in ('start', 'end')})
    out = []
    for low, high in zip(edges, edges[1:]):
        covering = [t for t in terms if t['start'] <= low and high <= t['end']]
        if len(covering) == 1:
            out.append((low, high, covering[0]['chamber']))
    return out


def eligibility_matrix(members, bills, reference_date, chamber):
    """The chamber's eligible-opportunity indicator, members x bills, strictly before a date.

    Reproduces ``chamber_work.temporal_features``'s rule without its per-bill python
    loop: a member is eligible for a bill when a single dated term of that member
    covers the introduction day in the bill's chamber and the member is not the
    sponsor. ``coeligible_counts`` cross-checks the result against the builder's own
    published opportunity counts, so this is a second accounting of one rule rather
    than a second rule.
    """
    ids = sorted(members)
    index = {a: i for i, a in enumerate(ids)}
    panel = sorted((b for b in bills if b['chamber'] == chamber
                    and b['introduced'] < reference_date),
                   key=lambda b: (b['introduced'], b['key']))
    days = [b['introduced'] for b in panel]
    eligible = np.zeros((len(ids), len(panel)), dtype=np.float32)
    for a in ids:
        for low, high, term_chamber in single_term_intervals(members[a]):
            if term_chamber != chamber:
                continue
            start = bisect.bisect_left(days, low)
            stop = bisect.bisect_left(days, high)
            if stop > start:
                eligible[index[a], start:stop] = 1.0
    sponsor = np.zeros_like(eligible)
    for column, b in enumerate(panel):
        seat = index.get(b['sponsor'])
        if seat is not None:
            sponsor[seat, column] = 1.0
            eligible[seat, column] = 0.0
    return ids, panel, eligible, sponsor


def coeligible_counts(members, bills, reference_date, work_rows, progress=print):
    """Shared eligible bills per unordered pair, with a check against the work builder.

    ``chamber_work`` keeps its co-eligible matrix internal and publishes only the
    directed opportunity counts, so the shared-eligible denominator P1-6 asks for is
    recomputed here. The check is exact and total, not a sample: the opportunity
    counts implied by this eligibility matrix are compared to every opportunity count
    the builder published, and any disagreement raises.
    """
    shared, audit = {}, dict(checked_counts=0, mismatches=0, by_chamber={})
    for chamber in ('House', 'Senate'):
        ids, panel, eligible, sponsor = eligibility_matrix(members, bills, reference_date, chamber)
        if not panel:
            audit['by_chamber'][chamber] = dict(bills=0, pairs=0)
            continue
        co = (eligible @ eligible.T).astype(np.int64)
        opportunities = (eligible @ sponsor.T).astype(np.int64)
        count = 0
        for i, a in enumerate(ids):
            for j in range(i + 1, len(ids)):
                key = '%s__%s' % (a, ids[j])
                row = work_rows.get(key)
                if row is None or row.get('chamber') != chamber:
                    continue
                shared[key] = int(co[i, j])
                count += 1
                for field, value in (('opportunities_a_to_b', opportunities[i, j]),
                                     ('opportunities_b_to_a', opportunities[j, i])):
                    published = row.get(field)
                    if published is None:
                        continue
                    audit['checked_counts'] += 1
                    if int(published) != int(value):
                        audit['mismatches'] += 1
                        raise ValueError(
                            'Shared-eligible accounting disagrees with chamber_work for %s %s: '
                            'builder %s, recomputed %s' % (key, field, published, int(value)))
        audit['by_chamber'][chamber] = dict(bills=len(panel), pairs=count)
        progress('  shared-eligible %s: %s bills, %s pairs'
                 % (chamber, f'{len(panel):,}', f'{count:,}'), flush=True)
        del eligible, sponsor, co, opportunities
    audit['rule'] = ('bills of this chamber introduced strictly before the reference date for '
                     'which a single dated term of each member covered the introduction day and '
                     'neither member is the sponsor')
    audit['cross_check'] = ('every published chamber_work opportunity count was reproduced from '
                            'this eligibility matrix; a disagreement raises')
    return shared, audit


# ------------------------------------------------------------------- nominate


def load_nominate_dim2(path, congresses):
    """The second dimension, read with exactly load_nominate's row-resolution rule."""
    wanted = {int(c) for c in congresses}
    best = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            try:
                congress = int(row['congress'])
            except (TypeError, ValueError):
                continue
            if congress not in wanted or row['chamber'] not in ('House', 'Senate'):
                continue
            bioguide = (row.get('bioguide_id') or '').strip()
            score = (row.get('nominate_dim2') or '').strip()
            if not bioguide or not score:
                continue
            try:
                votes = float(row.get('nominate_number_of_votes') or 0)
            except ValueError:
                votes = 0.0
            key = (congress, row['chamber'], bioguide)
            if key in best and votes <= best[key][1]:
                continue
            best[key] = (float(score), votes)
    return {k: v[0] for k, v in best.items()}, dict(members_scored=len(best))


def nominate_resolver(path, congress_range, members):
    """Per-congress NOMINATE dimensions with an explicit, never-imputed fallback.

    Returns a callable (bioguide, day) -> dict(dw1, dw2, rank). Rank 2 is a row for
    that member's own congress and chamber, rank 1 the static HS119 value already
    carried in members.json, rank 0 nothing at all. Rank 0 leaves the column missing;
    it is never imputed, because P1-11 makes a missing measurement evidence
    availability rather than a feature value.
    """
    low, high = congress_range
    congresses = tuple(range(low, high + 1))
    scores, audit = load_nominate(path, congresses)
    second, second_audit = load_nominate_dim2(path, congresses)
    counts = Counter()

    def resolve(bioguide, day):
        congress = congress_of(day, congress_range)
        term = term_on(members[bioguide], day)
        chamber = term['chamber'] if term else members[bioguide].get('chamber')
        key = (congress, chamber, bioguide) if congress is not None else None
        value = scores.get(key) if key else None
        if value is not None:
            counts[2] += 1
            return dict(dw1=float(value), dw2=second.get(key), rank=2)
        static = members[bioguide].get('d1')
        if static is not None:
            counts[1] += 1
            return dict(dw1=float(static), dw2=members[bioguide].get('d2'), rank=1)
        counts[0] += 1
        return dict(dw1=None, dw2=None, rank=0)

    resolve.audit = dict(dim1=audit, dim2=second_audit,
                         congress_range=[low, high], source=relative(path))
    resolve.counts = counts
    return resolve


# --------------------------------------------------------------- feature rows


def work_state_of(row):
    if row is None or row.get('chamber') is None:
        return WORK_NO_MEMBERSHIP
    status = row.get('work_status')
    if status not in WORK_STATUS_MAP:
        raise ValueError('Unknown work status from the builder: %r' % status)
    return WORK_STATUS_MAP[status]


def speech_state_of(entry):
    if entry is None:
        return SPEECH_NO_MENTIONS
    return SPEECH_AVAILABLE if entry['status'] == 'available' else SPEECH_INSUFFICIENT


REVERSIBLE = {'direct_propensity': 'reverse_direct_propensity',
              'actor_bipartisan': 'target_bipartisan',
              'original_a_to_b': 'original_b_to_a',
              'opportunities_a_to_b': 'opportunities_b_to_a'}


def reverse_work_row(row):
    """The builder emits one row per unordered pair; the other direction swaps the
    asymmetric columns and leaves the symmetric ones alone."""
    out = dict(row)
    for left, right in REVERSIBLE.items():
        out[left], out[right] = row.get(right), row.get(left)
    return out


def directed_work(work_rows, a, b):
    forward = work_rows.get('%s__%s' % (a, b))
    if forward is not None:
        return forward, reverse_work_row(forward)
    backward = work_rows.get('%s__%s' % (b, a))
    if backward is None:
        return None, None
    return reverse_work_row(backward), backward


SWAPPED_CONTEXT = {'actor_dw1': 'target_dw1', 'target_dw1': 'actor_dw1',
                   'actor_dw2': 'target_dw2', 'target_dw2': 'actor_dw2'}
CONTEXT_CELLS = ('same_party', 'same_state', 'dw1_distance', 'actor_dw1', 'target_dw1',
                 'actor_dw2', 'target_dw2')


def member_context(members, a, b, day, nominate=None):
    """The non-work context columns, derived exactly as run_chamber_degrees derives them."""
    ta, tb = term_on(members[a], day), term_on(members[b], day)
    out = {}
    if ta is not None and tb is not None:
        out['same_party'] = float(ta['party'] == tb['party'])
        out['same_state'] = float(ta['state'] == tb['state'])
    else:
        out['same_party'] = None
        out['same_state'] = None
    if nominate is None:
        ranks = (None, None)
        values = {'actor_dw1': members[a].get('d1'), 'target_dw1': members[b].get('d1'),
                  'actor_dw2': members[a].get('d2'), 'target_dw2': members[b].get('d2')}
    else:
        left, right = nominate(a, day), nominate(b, day)
        ranks = (left['rank'], right['rank'])
        values = {'actor_dw1': left['dw1'], 'target_dw1': right['dw1'],
                  'actor_dw2': left['dw2'], 'target_dw2': right['dw2']}
    out.update(values)
    d1a, d1b = values['actor_dw1'], values['target_dw1']
    out['dw1_distance'] = abs(d1a - d1b) if d1a is not None and d1b is not None else None
    out['nominate_ranks'] = ranks
    return out


def visibility_block(assignment, a, b):
    out = {}
    for role, who in (('a', a), ('b', b)):
        words = assignment.get(who, {}).get('interview_words')
        out[role + '_interview_words'] = words
        out[role + '_log_interview_words'] = (num(float(np.log1p(words)))
                                              if words is not None else None)
    return out


def parse_grade(value):
    """A blind pass writes its grade as a string; 'unassessable' is not a grade."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if 0 <= value <= 4 else None
    text = str(value).strip()
    if not text.isdigit():
        return None
    grade = int(text)
    return grade if 0 <= grade <= 4 else None


def blind_agreement_labels(pass_a, pass_b):
    """Degree-record grades where both blind re-grading passes produced the same number."""
    left = {row['id']: row for row in pass_a}
    right = {row['id']: row for row in pass_b}
    labels, audit = {}, dict(records=len(left), both_assessed={}, agreed={})
    for axis in AXES:
        both, agree = 0, 0
        for record_id, a_row in sorted(left.items()):
            b_row = right.get(record_id)
            if b_row is None:
                continue
            a_grade, b_grade = parse_grade(a_row.get(axis)), parse_grade(b_row.get(axis))
            if a_grade is None or b_grade is None:
                continue
            both += 1
            if a_grade == b_grade:
                agree += 1
                labels.setdefault(record_id, {})[axis] = a_grade
        audit['both_assessed'][axis] = both
        audit['agreed'][axis] = agree
    audit['rule'] = ('both blind passes produced the same whole grade for that axis; a pass that '
                     'wrote "unassessable" contributes nothing')
    return labels, audit


def training_work_panel(members, bills, annotations, v6_features, frozen_default,
                        progress=print):
    """Rebuild the degree records' work columns on the run's own bill panel.

    ``run_chamber_degrees.prepare`` froze the v6 work columns against congresses
    116-119. Applying a model fitted on those columns to a universe whose work columns
    were built on a wider panel would standardise the universe by a training
    distribution taken from a different panel, so the columns are rebuilt here with the
    same builder, the same records and the same dates as the frozen prepare used.

    On the frozen default panel the rebuild must reproduce ``features.json``, and that
    is asserted rather than assumed -- but it is asserted to a float32 tolerance, not
    bit for bit. ``chamber_work`` accumulates its matrices through float32 matrix
    products, whose reduction order BLAS is free to change between runs, so a cell can
    move by around 1e-8 with no change of input at all. A real panel change moves
    ``log_shared_bills`` and the opportunity counts by whole units, orders of magnitude
    above that floor, so the check still catches what it is for. Every count, whether
    exact, inside the tolerance or beyond it, is in the receipt.
    """
    assessments = [dict(id=r['id'], actor=r['actor'], target=r['target'], date=r['date'])
                   for r in annotations]
    rows, _ = temporal_features(members, bills, assessments, progress)
    # The builder writes a non-finite float where a quantity is undefined; regression.save
    # wrote the same cell out as null. Both mean "no measurement", so both become None
    # before any comparison and neither is ever read as a number.
    rows = {key: {k: finite_or_none(v) for k, v in row.items()} for key, row in rows.items()}
    compared = exact = within = beyond = 0
    largest, columns = 0.0, Counter()
    for record in annotations:
        rebuilt, stored = rows[record['id']], v6_features[record['id']]
        for column in BUILDER_COLUMNS:
            left, right = rebuilt.get(column), finite_or_none(stored.get(column))
            compared += 1
            if isinstance(left, str) or isinstance(right, str) or left is None or right is None:
                if left == right:
                    exact += 1
                else:
                    beyond += 1
                    columns[column] += 1
                continue
            gap = abs(float(left) - float(right))
            largest = max(largest, gap)
            if gap == 0.0:
                exact += 1
            elif gap <= max(FLOAT32_TOLERANCE, FLOAT32_TOLERANCE * abs(float(right))):
                within += 1
            else:
                beyond += 1
                columns[column] += 1
    audit = dict(records=len(annotations), columns=list(BUILDER_COLUMNS), cells_compared=compared,
                 cells_exactly_equal=exact, cells_within_float32_tolerance=within,
                 cells_beyond_tolerance=beyond, beyond_tolerance_columns=dict(sorted(
                     columns.items())),
                 # As a string: the gap that justifies the tolerance is around 1e-8, and the
                 # receipt's own six-place float rounding would print it as a bare zero.
                 max_absolute_difference='%.4e' % largest,
                 max_absolute_difference_exceeds_tolerance=bool(largest > FLOAT32_TOLERANCE),
                 tolerance=FLOAT32_TOLERANCE,
                 frozen_default_panel=bool(frozen_default),
                 rule='the degree records carry work columns built on the same bill panel and '
                      'congress range as the universe rows they are applied to',
                 tolerance_note='chamber_work accumulates through float32 matrix products, whose '
                                'reduction order is not fixed between runs, so a cell can move by '
                                'about 1e-8 with identical inputs; a real panel change moves the '
                                'same cells by whole units')
    if frozen_default and beyond:
        raise ValueError(
            'Rebuilding the v6 work columns on the frozen 116-119 panel did not reproduce '
            'features.json: %d cells differ beyond the float32 tolerance, largest gap %g, '
            'columns %r' % (beyond, largest, dict(columns)))
    audit['reproduces_frozen_v6_features'] = bool(frozen_default and not beyond)
    return rows, audit


def load_inputs(reference_date=REFERENCE_DATE, bills_path=None, congress_range=None,
                work_residuals=None, work_residuals_directed=None, nominate_path=None,
                progress=print, stage=noop):
    """Read every lane input this module consumes and build the universe work panel."""
    if work_residuals and work_residuals_directed:
        raise ValueError('--work-residuals and --work-residuals-directed are two substitutions '
                         'of the same feature pair; pass exactly one')
    congress_range = tuple(congress_range or DEFAULT_CONGRESS_RANGE)
    bills_path = Path(bills_path or (HISTORY / 'bills.ndjson'))
    members = read_json(HISTORY / 'members.json')
    bills, bill_audit = read_bills_in_range(bills_path, congress_range)
    assignment = read_json(FROZEN / 'member_assignment.json')
    annotations = list(read_rows(V6 / 'annotations.ndjson'))
    v6_features = read_json(V6 / 'features.json')
    cases = read_json(REGRESSION / 'cases.json')
    development, denied = load_sample(FROZEN / 'sampled_pairs.ndjson')
    labels = list(read_rows(SAMPLE_LABELS / 'labels_v1.ndjson'))
    regrade_a = list(read_rows(REGRADE / 'pass_A.ndjson'))
    regrade_b = list(read_rows(REGRADE / 'pass_B.ndjson'))
    pooled = pooled_expression(CONTRASTS / 'expression_contrasts.ndjson')
    volume = encounter_volume(CENSUS / 'encounter_counts.ndjson')
    stage('read_inputs', 'lane inputs read: %s bills, %s members' % (len(bills), len(members)))

    residuals, residual_audit = None, None
    if work_residuals:
        residuals, residual_audit = load_residuals(work_residuals)
    residuals_directed, residual_directed_audit = None, None
    if work_residuals_directed:
        residuals_directed, residual_directed_audit = load_residuals_directed(
            work_residuals_directed)
    nominate = None
    if nominate_path:
        nominate = nominate_resolver(nominate_path, congress_range, members)

    ids = sorted(members)
    universe = list(itertools.combinations(ids, 2))
    progress('Universe: %s members, %s unordered pairs, reference date %s'
             % (f'{len(ids):,}', f'{len(universe):,}', reference_date), flush=True)
    assessments = [dict(id='%s__%s' % (a, b), actor=a, target=b, date=reference_date)
                   for a, b in universe]
    work_rows, work_audit = temporal_features(members, bills, assessments, progress)
    stage('work_panel', 'canonical work panel built for %s pairs' % len(work_rows))
    frozen_default = (bills_path.resolve() == (HISTORY / 'bills.ndjson').resolve()
                      and tuple(congress_range) == FROZEN_DEFAULT_RANGE)
    training_work, training_audit = training_work_panel(members, bills, annotations, v6_features,
                                                        frozen_default, progress)
    stage('training_work_panel',
          "degree-record work columns rebuilt on this run's panel (%d of %d cells differ from v6 "
          'beyond the float32 tolerance)'
          % (training_audit['cells_beyond_tolerance'], training_audit['cells_compared']))
    shared_eligible, eligible_audit = coeligible_counts(members, bills, reference_date, work_rows,
                                                        progress)
    stage('shared_eligible', 'shared-eligible denominators recomputed and cross-checked')

    sources = {
        'members.json': HISTORY / 'members.json',
        'bills.ndjson': bills_path,
        'member_assignment.json': FROZEN / 'member_assignment.json',
        'sampled_pairs.ndjson': FROZEN / 'sampled_pairs.ndjson',
        'v6_annotations.ndjson': V6 / 'annotations.ndjson',
        'v6_features.json': V6 / 'features.json',
        'v6_regrade_pass_A.ndjson': REGRADE / 'pass_A.ndjson',
        'v6_regrade_pass_B.ndjson': REGRADE / 'pass_B.ndjson',
        'cases.json': REGRESSION / 'cases.json',
        'labels_v1.ndjson': SAMPLE_LABELS / 'labels_v1.ndjson',
        'expression_contrasts.ndjson': CONTRASTS / 'expression_contrasts.ndjson',
        'encounter_counts.ndjson': CENSUS / 'encounter_counts.ndjson',
    }
    if work_residuals:
        sources['work_residuals'] = Path(work_residuals)
    if work_residuals_directed:
        sources['work_residuals_directed'] = Path(work_residuals_directed)
    if nominate_path:
        sources['nominate'] = Path(nominate_path)
    digests = {}
    for name, path in sorted(sources.items()):
        path = Path(path)
        digests[name] = dict(path=relative(path), sha256=digest(path), bytes=path.stat().st_size)
    return dict(members=members, assignment=assignment, annotations=annotations,
                v6_features=v6_features, cases=cases, development=development, denied=denied,
                labels=labels, regrade_a=regrade_a, regrade_b=regrade_b,
                pooled=pooled, volume=volume, residuals=residuals, residual_audit=residual_audit,
                residual_path=work_residuals, residuals_directed=residuals_directed,
                residual_directed_audit=residual_directed_audit,
                residual_directed_path=work_residuals_directed,
                nominate=nominate, nominate_path=nominate_path,
                universe=universe, work_rows=work_rows, work_audit=work_audit,
                training_work=training_work, training_work_audit=training_audit,
                shared_eligible=shared_eligible, eligible_audit=eligible_audit,
                bills=bills, bill_audit=bill_audit, congress_range=list(congress_range),
                panel_start=congress_end(congress_range[0] - 1),
                reference_date=reference_date, digests=digests, sign=None)


def load_sign_inputs(members, bills, cases):
    """The benchmark contract's own canonical row C1, rebuilt from its cached work panel."""
    from .benchmark_contract import R0_NOVIS, merge_rows, static_rows, volume_counts
    path = BENCH / 'work_rows_original_strict_before.json'
    if not path.exists():
        return None
    stored = read_json(path)
    work = {tuple(r['direction']): r['features'] for r in stored['rows']}
    composite = {(r['actor'], r['target']): r
                 for r in read_json(REGRESSION / 'features.json')['composite']}
    static = static_rows(cases, members, composite, volume_counts(members, bills))
    return dict(names=list(R0_NOVIS), feature_rows=merge_rows(static, work),
                work_path=relative(path), work_sha256=digest(path),
                timing=stored['timing_policy'], signatures=stored['signature_policy'])


# ------------------------------------------------------------- training rows


def training_rows(inputs, residuals_active, grades=None, label_source='original'):
    """The 73 dated v6 degree records, carrying the exact features the v6 fit used."""
    rows = []
    nominate = inputs.get('nominate')
    panel = inputs.get('training_work') or {}
    for record in inputs['annotations']:
        features = dict(inputs['v6_features'][record['id']])
        rebuilt = panel.get(record['id'])
        if rebuilt is not None:
            features.update({k: v for k, v in rebuilt.items() if k in BUILDER_COLUMNS})
        key = (record['actor'], record['target'])
        entry = inputs['pooled'].get(key)
        features['speech_warm_contrast'] = entry['warm'] if entry else None
        features['speech_hostile_contrast'] = entry['hostile'] if entry else None
        speech = speech_state_of(entry)
        work = WORK_STATUS_MAP.get(features.get('work_status'), WORK_NO_MEMBERSHIP)
        ranks = (None, None)
        if nominate is not None:
            left, right = (nominate(record['actor'], record['date']),
                           nominate(record['target'], record['date']))
            ranks = (left['rank'], right['rank'])
            features['actor_dw1'], features['target_dw1'] = left['dw1'], right['dw1']
            features['actor_dw2'], features['target_dw2'] = left['dw2'], right['dw2']
            features['dw1_distance'] = (abs(left['dw1'] - right['dw1'])
                                        if left['dw1'] is not None and right['dw1'] is not None
                                        else None)
        if residuals_active:
            residual, missing_state = residual_for_direction(inputs, record['actor'],
                                                              record['target'])
            if residual is None:
                work = missing_state
            else:
                for name in RESIDUAL_FEATURES:
                    features[name] = residual[name]
        if grades is None:
            affinity, friction = record['affinity'], record['friction']
        else:
            cell = grades.get(record['id'], {})
            affinity, friction = cell.get('affinity'), cell.get('friction')
        rows.append(dict(id=record['id'], pair=list(record['pair']), actor=record['actor'],
                         target=record['target'], pair_id=pair_id_of(*record['pair']),
                         names=record['names'], date=record['date'], chamber=record['chamber'],
                         families=list(record['families']), affinity=affinity, friction=friction,
                         features=features, work_state=work, speech_state=speech,
                         nominate_ranks=list(ranks), label_source=label_source))
    return rows


# ------------------------------------------------------------------- fitting


def dyad_weights(rows, index):
    """Each unordered dyad carries total weight one, exactly as run_chamber_degrees does."""
    counts = Counter(rows[i]['pair_id'] for i in index)
    return np.array([1.0 / counts[rows[i]['pair_id']] for i in index], dtype=float)


def fittable(rows, axis, spec_name, residuals_active=False):
    """Rows this axis and specification can be fit on: a graded outcome and a present
    channel. A missing channel never becomes a mean-imputed training row."""
    channel = SPECS[spec_name]['channel']
    keep = []
    for i, row in enumerate(rows):
        if row[axis] is None:
            continue
        if channel == 'work' and row['work_state'] != WORK_AVAILABLE:
            continue
        if channel == 'speech' and row['speech_state'] != SPEECH_AVAILABLE:
            continue
        keep.append(i)
    return keep


def design_matrix(rows, index, names):
    return np.array([[rows[i]['features'].get(n) for n in names] for i in index], dtype=float)


def fit_spec(rows, index, names, axis, chamber_slopes, penalty=PENALTY):
    x = design_matrix(rows, index, names)
    y = [rows[i][axis] for i in index]
    chambers = [rows[i]['chamber'] for i in index]
    return OrdinalDegrees(penalty, chamber_slopes).fit(x, y, chambers, dyad_weights(rows, index))


def family_components(rows, index):
    """Connected components over shared evidence families: the lane's own exclusion unit."""
    first_seen = {}
    parent = {i: i for i in index}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)

    for i in index:
        for family in rows[i]['families']:
            if family in first_seen:
                union(i, first_seen[family])
            else:
                first_seen[family] = i
    groups = defaultdict(list)
    for i in index:
        groups[find(i)].append(i)
    return [sorted(v) for _, v in sorted(groups.items())]


def bootstrap_fits(rows, index, names, axis, chamber_slopes, replicates, seed, penalty=PENALTY):
    """Source-resampled refits: resample whole evidence-family components with replacement.

    This carries refitting variability over the labelled units the model is fit on. It
    carries no specification-search variability and is not a coverage claim.
    """
    groups = family_components(rows, index)
    rng = np.random.default_rng(seed)
    models, failures = [], Counter()
    for _ in range(replicates):
        picks = rng.integers(0, len(groups), size=len(groups)) if groups else []
        draw = [i for k in picks for i in groups[k]]
        if not draw:
            failures['empty_resample'] += 1
            continue
        try:
            models.append(fit_spec(rows, draw, names, axis, chamber_slopes, penalty))
        except (ValueError, ArithmeticError, np.linalg.LinAlgError) as error:
            failures[type(error).__name__] += 1
    return models, dict(requested=replicates, fitted=len(models),
                        failed=dict(sorted(failures.items())),
                        resample_unit='evidence_family_component', components=len(groups),
                        labelled_rows=len(index),
                        labelled_dyads=len({rows[i]['pair_id'] for i in index}), seed=seed,
                        note='standard deviation of the expected grade over refits; never the '
                             'model probability')


def bootstrap_standard_error(models, x, chambers, chunk=CHUNK):
    """Welford over refits, chunked so a 200-refit sweep never materialises 200 arrays."""
    n = len(x)
    se = np.full(n, np.nan)
    if len(models) < 2 or n == 0:
        return se
    for start in range(0, n, chunk):
        stop = min(start + chunk, n)
        xs, cs = x[start:stop], chambers[start:stop]
        count = 0
        mean = np.zeros(stop - start)
        m2 = np.zeros(stop - start)
        for model in models:
            value = model.predict_proba(xs, cs) @ GRADES
            count += 1
            delta = value - mean
            mean += delta / count
            m2 += delta * (value - mean)
        se[start:stop] = np.sqrt(m2 / (count - 1))
    return se


# ------------------------------------------------------------------ universe


def universe_frame(inputs, residuals_active, progress=print):
    """Every directed row of the universe: its states, its columns and its denominators."""
    members, assignment = inputs['members'], inputs['assignment']
    day = inputs['reference_date']
    universe = inputs['universe']
    pooled, volume, work_rows = inputs['pooled'], inputs['volume'], inputs['work_rows']
    shared_eligible = inputs['shared_eligible']
    residuals_directed = inputs.get('residuals_directed')
    directed_coverage = Counter() if residuals_directed is not None else None
    nominate = inputs.get('nominate')

    columns = sorted(set(ESTIMATE_CONTEXT) | set(ESTIMATE_WORK) | set(WORK_CHANNEL)
                     | set(SPEECH_FEATURES) | set(RESIDUAL_FEATURES))
    n = 2 * len(universe)
    values = {name: np.full(n, np.nan) for name in columns}
    chambers = np.empty(n, dtype=object)
    work_states = np.empty(n, dtype=object)
    speech_states = np.empty(n, dtype=object)
    nominate_ranks = Counter()
    pair_rows = []
    work_columns = set(ESTIMATE_WORK) | {'issue_similarity'}

    for k, (a, b) in enumerate(universe):
        if k and k % 25000 == 0:
            progress('  universe frame: %s of %s pairs' % (f'{k:,}', f'{len(universe):,}'),
                     flush=True)
        forward, backward = directed_work(work_rows, a, b)
        base_state = work_state_of(forward)
        context = member_context(members, a, b, day, nominate)
        if nominate is not None:
            for rank in context['nominate_ranks']:
                nominate_ranks[rank] += 1
        entry_ab, entry_ba = pooled.get((a, b)), pooled.get((b, a))
        chamber = forward.get('chamber') if forward else None
        pair_key = pair_id_of(a, b)
        directed_entries = {}
        for direction, (actor, target, work, entry) in enumerate(
                ((a, b, forward, entry_ab), (b, a, backward, entry_ba))):
            row = 2 * k + direction
            state = base_state
            if residuals_active and state == WORK_AVAILABLE:
                residual_entry, missing_state = residual_for_direction(inputs, actor, target)
                if residual_entry is None:
                    state = missing_state
                    if residuals_directed is not None:
                        directed_coverage['no_baseline_row'] += 1
                else:
                    if residuals_directed is not None:
                        directed_entries['a_to_b' if direction == 0 else 'b_to_a'] = residual_entry
                        directed_coverage['covered'] += 1
                    for name in RESIDUAL_FEATURES:
                        value = residual_entry[name]
                        if value is not None:
                            values[name][row] = float(value)
            elif residuals_directed is not None:
                directed_coverage['not_work_available'] += 1
            if work is not None:
                if state == WORK_AVAILABLE:
                    for name in work_columns:
                        value = work.get(name)
                        if value is not None:
                            values[name][row] = float(value)
                if state != WORK_CROSS_CHAMBER:
                    value = work.get('co_service_years')
                    if value is not None:
                        values['co_service_years'][row] = float(value)
            for name in CONTEXT_CELLS:
                value = context[name if direction == 0 else SWAPPED_CONTEXT.get(name, name)]
                if value is not None:
                    values[name][row] = float(value)
            if entry is not None:
                for name, field in (('speech_warm_contrast', 'warm'),
                                    ('speech_hostile_contrast', 'hostile')):
                    if entry[field] is not None:
                        values[name][row] = float(entry[field])
            chambers[row] = chamber
            work_states[row] = state
            speech_states[row] = speech_state_of(entry)
        work = forward or {}
        pair_residual_entry = (residual_for_direction(inputs, a, b)[0]
                               if residuals_active and residuals_directed is None else None)
        pair_rows.append(dict(
            pair=[a, b], pair_id=pair_key, names=[members[a]['name'], members[b]['name']],
            chamber_layer=chamber,
            opportunities=(work.get('opportunities_a_to_b'), work.get('opportunities_b_to_a')),
            originals=(work.get('original_a_to_b'), work.get('original_b_to_a')),
            shared_original_bills=work.get('shared_original_bills'),
            shared_eligible_bills=shared_eligible.get(pair_key),
            co_service_years=(None if chamber == 'cross_chamber'
                              else work.get('co_service_years')),
            nominate_ranks=list(context['nominate_ranks']),
            residual=(pair_residual_entry or {}).get('counts'),
            residual_by_direction=(dict(a_to_b=(directed_entries.get('a_to_b') or {}).get('counts'),
                                        b_to_a=(directed_entries.get('b_to_a') or {}).get('counts'))
                                   if residuals_directed is not None else None),
            speech=dict(a_to_b=entry_ab, b_to_a=entry_ba),
            mention_turns=dict(a_to_b=volume.get((a, b), {}), b_to_a=volume.get((b, a), {})),
            coverage_tier=[assignment.get(a, {}).get('coverage_tier'),
                           assignment.get(b, {}).get('coverage_tier')],
            visibility=visibility_block(assignment, a, b)))
    observed = {name: int(np.isfinite(values[name]).sum()) for name in sorted(values)}
    # A member with no single dated term on the reference date leaves the pair's chamber
    # layer unresolved. OrdinalDegrees.design refuses such a row rather than letting it
    # become House, so the row is held out of every specification with that state named,
    # instead of reaching the model and raising there.
    resolved = np.array([c is not None for c in chambers])
    return dict(pairs=pair_rows, values=values, chambers=chambers, work_states=work_states,
                speech_states=speech_states, resolved=resolved, rows=n,
                observed_columns=observed, unresolved_chamber_rows=int((~resolved).sum()),
                nominate_ranks=dict(sorted(nominate_ranks.items())),
                directed_coverage=(dict(sorted(directed_coverage.items()))
                                   if directed_coverage is not None else None))


def not_scored_reason(spec_name, frame, row, block):
    """Why this directed row has no estimate, named rather than left blank."""
    if not block['fitted']:
        return 'not_scored:%s' % block['reason']
    if not frame['resolved'][row]:
        return 'not_scored:%s' % WORK_NO_MEMBERSHIP
    channel = SPECS[spec_name]['channel']
    return 'not_scored:%s' % (frame['work_states'][row] if channel == 'work'
                              else frame['speech_states'][row])


def score_universe(frame, rows, residuals_active, bootstrap, seed, progress=print, stage=noop):
    """Fit each specification on the labelled rows, then apply it to every eligible row."""
    out, fits = {}, {}
    for spec_name in SPEC_ORDER:
        spec = SPECS[spec_name]
        names = spec_features(spec_name, residuals_active)
        channel = spec['channel']
        eligible = ((frame['work_states'] == WORK_AVAILABLE if channel == 'work'
                     else frame['speech_states'] == SPEECH_AVAILABLE) & frame['resolved'])
        index = np.flatnonzero(eligible)
        x = (np.column_stack([frame['values'][n] for n in names])[index] if len(index)
             else np.zeros((0, len(names))))
        chambers = frame['chambers'][index]
        out[spec_name] = {}
        fits[spec_name] = dict(features=names, chamber_slopes=spec['chamber_slopes'],
                               partial=spec['partial'], basis=spec['basis'], channel=channel,
                               eligible_directed_rows=int(len(index)),
                               unresolved_chamber_rows=frame['unresolved_chamber_rows'],
                               directed_rows=int(frame['rows']), axes={})
        for axis in AXES:
            training = fittable(rows, axis, spec_name, residuals_active)
            block = dict(expected=np.full(frame['rows'], np.nan),
                         probability=np.full((frame['rows'], 5), np.nan),
                         se=np.full(frame['rows'], np.nan), fitted=False, reason=None)
            record = dict(labelled_rows=len(training),
                          labelled_dyads=len({rows[i]['pair_id'] for i in training}),
                          observed_grades=sorted({rows[i][axis] for i in training}),
                          fitted=False, reason=None, bootstrap=None)
            if len(training) < 3 or len({rows[i][axis] for i in training}) < 2:
                record['reason'] = 'insufficient_graded_rows'
                block['reason'] = 'model_not_fitted:%s:%s' % (spec_name, axis)
                out[spec_name][axis] = block
                fits[spec_name]['axes'][axis] = record
                progress('  %s/%s: not fitted (%d graded rows)'
                         % (spec_name, axis, len(training)), flush=True)
                continue
            model = fit_spec(rows, training, names, axis, spec['chamber_slopes'])
            record.update(fitted=True, gradient_norm=model.gradient_norm_,
                          iterations=model.iterations_, penalty=PENALTY,
                          chamber_slopes=spec['chamber_slopes'],
                          model_observed_grades=model.observed_grades_)
            block['fitted'] = True
            if len(index):
                probability = model.predict_proba(x, chambers)
                block['probability'][index] = probability
                block['expected'][index] = probability @ GRADES
            models, audit = bootstrap_fits(rows, training, names, axis, spec['chamber_slopes'],
                                           bootstrap, seed)
            record['bootstrap'] = audit
            if len(index) and len(models) >= 2:
                block['se'][index] = bootstrap_standard_error(models, x, chambers)
            out[spec_name][axis] = block
            fits[spec_name]['axes'][axis] = record
            progress('  %s/%s: fitted on %d graded rows over %d dyads, %d/%d refits'
                     % (spec_name, axis, len(training), record['labelled_dyads'],
                        audit['fitted'], audit['requested']), flush=True)
        stage('score_%s' % spec_name, '%s scored on %s of %s directed rows'
              % (spec_name, f'{len(index):,}', f"{frame['rows']:,}"))
    return out, fits


# ------------------------------------------------------------------- labels


def label_index(inputs):
    """Which lane label, if any, touches each unordered pair. No held-out label is read."""
    index = defaultdict(lambda: dict(states=set(), detail={}))
    for case in inputs['cases']:
        key = pair_id_of(*case['pair'])
        index[key]['states'].add(LABEL_SIGN)
        index[key]['detail']['sign'] = dict(sign=case['sign'], y=case['y'], first=case['first'])
    for record in inputs['annotations']:
        key = pair_id_of(*record['pair'])
        index[key]['states'].add(LABEL_DEGREE)
        index[key]['detail'].setdefault('degree_records', []).append(
            dict(id=record['id'], date=record['date'], affinity=record['affinity'],
                 friction=record['friction']))
    for row in inputs['labels']:
        key = str(row['pair_id'])
        state = (LABEL_SAMPLE_GRADED if row['label_status'] == 'two_blind_model_passes_merged'
                 else LABEL_SAMPLE_NO_EVIDENCE)
        index[key]['states'].add(state)
        index[key]['detail']['probability_sample'] = dict(label_status=row['label_status'],
                                                          graded_via=row['graded_via'])
    return dict(index)


def label_state_of(entry):
    if not entry or not entry['states']:
        return LABEL_NOT_ASSESSED, []
    order = [s for s in LABEL_STATES if s in entry['states']]
    return order[0], order


def exact_label_cells(inputs, denied):
    """Cells where both blind passes agreed exactly. Adjudication-pending cells are out.

    The census returned beside them closes the denominator chain: how many cells carry a
    whole grade at all, how many of those are still awaiting adjudication, how many were
    merged by min_of_adjacent, and how many are left for the reported table.
    """
    cells, sensitivity = [], []
    census = Counter()
    for row in inputs['labels']:
        pair_id = str(row['pair_id'])
        if pair_id in denied:
            raise ValueError('labels_v1.ndjson carries a held-out pair: %s' % pair_id)
        a, b = row['pair']
        for direction, (actor, target) in (('a_to_b', (a, b)), ('b_to_a', (b, a))):
            for axis in AXES:
                cell = row['directions'][direction][axis]
                value = cell.get('value')
                graded = not isinstance(value, bool) and isinstance(value, int)
                if graded:
                    census[(axis, 'graded_cells')] += 1
                if cell.get('adjudication_needed'):
                    census[(axis, 'adjudication_pending_cells')] += int(graded)
                    continue
                if not graded:
                    continue
                item = dict(pair_id=pair_id, pair=[a, b], names=row['names'], actor=actor,
                            target=target, direction=direction, axis=axis, value=int(value),
                            merge_rule=cell.get('merge_rule'), label_status=row['label_status'])
                (cells if cell.get('merge_rule') == 'exact' else sensitivity).append(item)
    return cells, sensitivity, {axis: dict(graded_cells=census[(axis, 'graded_cells')],
                                           adjudication_pending_cells=census[
                                               (axis, 'adjudication_pending_cells')])
                                for axis in AXES}


# ------------------------------------------------------------- sign diagnostic


def sign_diagnostic(inputs, sign, denied, progress=print):
    """The 29 documented sign dyads. A diagnostic only, never an axis of the estimate."""
    from .benchmark_contract import bootstrap_auc, bootstrap_draws, concordance_grid, interval
    from .regression import matrices
    from .regression_diagnostics import leave_two_cases_out
    cases = inputs['cases']
    assert_no_heldout([pair_id_of(*c['pair']) for c in cases], denied, 'sign_diagnostic')
    started = time.time()
    full = leave_two_cases_out(cases, matrices(cases, sign['names'], sign['feature_rows']),
                               'members')
    grid, positive, negative = concordance_grid(cases, full)
    drop = []
    for i, case in enumerate(cases):
        row = sign['feature_rows'][tuple(case['directions'][0])]
        if row.get('chamber') == 'cross_chamber' and row.get('opportunities_a_to_b') is None \
                and row.get('opportunities_b_to_a') is None:
            drop.append(i)
    keep = [i for i in range(len(cases)) if i not in drop]
    reduced_cases = [cases[i] for i in keep]
    reduced = leave_two_cases_out(
        reduced_cases, matrices(reduced_cases, sign['names'], sign['feature_rows']), 'members')
    reduced_grid, reduced_positive, reduced_negative = concordance_grid(reduced_cases, reduced)

    def row(name, note, result, grid_, n_positive, n_negative, dyads):
        values = bootstrap_auc(grid_, bootstrap_draws(n_positive, n_negative,
                                                      SIGN_BOOTSTRAP, SIGN_SEED))
        comparisons = int(grid_.size)
        return dict(row=name, note=note, dyads=dyads, positive=n_positive, negative=n_negative,
                    comparisons=comparisons, expected_comparisons=result['expected_comparisons'],
                    concordant=round(result['auc'] * result['comparisons'], 4),
                    same_fit_auc=num(result['auc']), bootstrap=clean(interval(values)),
                    bootstrap_replicates=SIGN_BOOTSTRAP, bootstrap_seed=SIGN_SEED,
                    unique_fits=result['unique_fits'])

    keep_positive = [k for k, i in enumerate(positive) if i in keep]
    keep_negative = [k for k, i in enumerate(negative) if i in keep]
    subset = grid[np.ix_(keep_positive, keep_negative)]
    out = dict(
        status=STATUS,
        label_file=relative(REGRESSION / 'cases.json'),
        specification=dict(names=sign['names'], count=len(sign['names']),
                           signatures=sign['signatures'], timing=sign['timing'],
                           work_panel=sign['work_path'], work_panel_sha256=sign['work_sha256'],
                           note='the benchmark contract canonical row R0_novis, reproduced '
                                'unchanged; its personality columns are the existing row, not '
                                'terms added here'),
        dropped_dyads=[dict(index=i, names=cases[i]['names']) for i in drop],
        drop_rule='dyads whose canonical work layer is cross_chamber and whose eligible '
                  'target-sponsored bill count is missing in both directions',
        rows=[row('all_dyads', 'every documented sign dyad', full, grid, len(positive),
                  len(negative), len(cases)),
              row('without_zero_work_cross_chamber',
                  'refit after dropping the zero-work cross-chamber dyads; the training sets '
                  'shrink with the dyad set', reduced, reduced_grid, len(reduced_positive),
                  len(reduced_negative), len(reduced_cases))],
        held_fits_variant=dict(
            note='the same drop applied to the all-dyad concordance grid: comparisons are '
                 'removed but the fits are the all-dyad fits, so this is a different quantity '
                 'from the refit row, not an alternative estimate of it',
            same_fit_auc=num(float(subset.mean())), comparisons=int(subset.size),
            concordant=round(float(subset.sum()), 4)),
        wall_seconds=round(time.time() - started, 1),
        reading='two axes are reported side by side in pair_scores.ndjson; this signed benchmark '
                'is a diagnostic and never collapses them into one number')
    progress('  sign diagnostic: %.4f (%g/%d) all dyads, %.4f (%g/%d) without the zero-work '
             'cross-chamber dyads'
             % (out['rows'][0]['same_fit_auc'], out['rows'][0]['concordant'],
                out['rows'][0]['comparisons'], out['rows'][1]['same_fit_auc'],
                out['rows'][1]['concordant'], out['rows'][1]['comparisons']), flush=True)
    return out


# --------------------------------------------------------------- leave-one-out


def leave_one_record_out(rows, axis, spec_name, residuals_active):
    """The lane's own outer validation: hold a record out with its transitive evidence-family
    and endpoint exclusions, as ordinal_degrees.training_indices defines them."""
    names = spec_features(spec_name, residuals_active)
    spec = SPECS[spec_name]
    available = fittable(rows, axis, spec_name, residuals_active)
    allowed = set(available)
    predictions, cache = [], {}
    for held in available:
        train = tuple(i for i in training_indices(rows, held) if i in allowed)
        base = dict(id=rows[held]['id'], pair_id=rows[held]['pair_id'], pair=rows[held]['pair'],
                    names=rows[held]['names'], date=rows[held]['date'],
                    chamber=rows[held]['chamber'], axis=axis,
                    label_source=rows[held]['label_source'],
                    observed_grade=rows[held][axis], train_rows=len(train))
        if len(train) < 3 or len({rows[i][axis] for i in train}) < 2:
            predictions.append(
                dict(base, prediction_state='not_scored:insufficient_independent_training'))
            continue
        if train not in cache:
            try:
                cache[train] = fit_spec(rows, list(train), names, axis, spec['chamber_slopes'])
            except (ValueError, ArithmeticError, np.linalg.LinAlgError) as error:
                cache[train] = error
        model = cache[train]
        if isinstance(model, Exception):
            predictions.append(dict(base, prediction_state='not_scored:fit_failed:%s'
                                                            % type(model).__name__))
            continue
        probability = model.predict_proba(design_matrix(rows, [held], names),
                                          [rows[held]['chamber']])[0]
        predictions.append(dict(base, prediction_state=SCORED,
                                expected_grade=num(float(probability @ GRADES)),
                                probability_by_grade=[num(p, 5) for p in probability],
                                train_dyads=len({rows[i]['pair_id'] for i in train})))
    scored = [p for p in predictions if p['prediction_state'] == SCORED]
    summary = dict(label_source=rows[0]['label_source'] if rows else None,
                   specification=spec_name, axis=axis, records=len(available),
                   scored=len(scored), not_scored=len(predictions) - len(scored),
                   dyads=len({rows[i]['pair_id'] for i in available}))
    if scored:
        error = [abs(p['expected_grade'] - p['observed_grade']) for p in scored]
        summary['mean_absolute_grade_error'] = num(sum(error) / len(error))
        summary['denominator'] = len(scored)
    return predictions, summary


# ------------------------------------------------------------------ 47 pairs


def presence_auc(values, presence):
    """Rank the estimate against a presence indicator. Both denominators are returned."""
    positive = [v for v, p in zip(values, presence) if p]
    negative = [v for v, p in zip(values, presence) if not p]
    if len(positive) < MIN_AUC_CLASS or len(negative) < MIN_AUC_CLASS:
        return dict(auc=None, positive=len(positive), negative=len(negative),
                    comparisons=len(positive) * len(negative), state='n_too_small',
                    minimum_per_class=MIN_AUC_CLASS)
    total = 0.0
    for p in positive:
        for n in negative:
            total += 1.0 if p > n else 0.5 if p == n else 0.0
    comparisons = len(positive) * len(negative)
    return dict(auc=num(total / comparisons), positive=len(positive), negative=len(negative),
                comparisons=comparisons, concordant=num(total), state='reported',
                minimum_per_class=MIN_AUC_CLASS)


def graded_sample_table(inputs, frame, scores, denied):
    """The graded development pairs of the probability sample, cell by cell."""
    cells, sensitivity, census = exact_label_cells(inputs, denied)
    position = {pair['pair_id']: k for k, pair in enumerate(frame['pairs'])}
    rows = []
    for cell in cells:
        k = position.get(cell['pair_id'])
        if k is None:
            rows.append(dict(cell, prediction_state='not_scored:pair_absent_from_universe'))
            continue
        a, b = frame['pairs'][k]['pair']
        row = 2 * k + (0 if (cell['actor'], cell['target']) == (a, b) else 1)
        item = dict(cell, chamber_layer=frame['pairs'][k]['chamber_layer'],
                    work_state=frame['work_states'][row],
                    speech_state=frame['speech_states'][row])
        for spec_name in SPEC_ORDER:
            block = scores[spec_name][cell['axis']]
            expected = block['expected'][row]
            item[spec_name] = dict(
                expected_grade=num(expected),
                bootstrap_standard_error=num(block['se'][row]),
                prediction_state=SCORED if np.isfinite(expected)
                else not_scored_reason(spec_name, frame, row, block))
        item['prediction_state'] = item['joint']['prediction_state']
        rows.append(item)
    summary = {}
    for axis in AXES:
        axis_cells = [r for r in rows if r['axis'] == axis]
        block = dict(agreed_cells=len(axis_cells),
                     pairs=len({r['pair_id'] for r in axis_cells}),
                     grade_histogram=dict(sorted(Counter(str(r['value'])
                                                         for r in axis_cells).items())),
                     sensitivity_cells_min_of_adjacent=sum(1 for s in sensitivity
                                                           if s['axis'] == axis),
                     graded_cells=census[axis]['graded_cells'],
                     adjudication_pending_cells=census[axis]['adjudication_pending_cells'],
                     agreement_rule='merge_rule == "exact": both blind passes produced the same '
                                    'degree; adjudication-pending cells excluded')
        for spec_name in SPEC_ORDER:
            scored = [r for r in axis_cells if r[spec_name]['prediction_state'] == SCORED]
            entry = dict(scored_cells=len(scored), denominator=len(axis_cells))
            if scored:
                error = [abs(r[spec_name]['expected_grade'] - r['value']) for r in scored]
                entry['mean_absolute_grade_error'] = num(sum(error) / len(error))
                entry['presence_vs_ordinary_auc'] = presence_auc(
                    [r[spec_name]['expected_grade'] for r in scored],
                    [r['value'] >= 1 for r in scored])
            else:
                entry['presence_vs_ordinary_auc'] = dict(auc=None, state='no_scored_cells',
                                                         positive=0, negative=0, comparisons=0)
            block[spec_name] = entry
        summary[axis] = block
    return rows, summary, sensitivity


# ------------------------------------------------------------------- writing


def speech_evidence(pair, direction, state):
    entry = pair['speech'][direction] or {}
    return dict(state=state,
                mention_turns_by_venue={v: pair['mention_turns'][direction].get(v, 0)
                                        for v in VENUES},
                pooled_mention_turns=entry.get('n'),
                speaker_total_turns=entry.get('speaker_total_turns'),
                speaker_distinct_targets=entry.get('speaker_distinct_targets'),
                warm_contrast=num(entry.get('warm')),
                hostile_contrast=num(entry.get('hostile')))


def residual_counts_block(counts):
    """The six reported fields of one residual entry's ``counts``, undirected or one
    direction of a directed one; the same shape either way."""
    counts = counts or {}
    return dict(original_cosponsorships=counts.get('original_cosponsorships'),
               eligible_opportunities=counts.get('eligible_opportunities'),
               expected=num(counts.get('expected')), residual=num(counts.get('residual')),
               rate_ratio_shrunk=num(counts.get('shrunken_rate_ratio')),
               baseline_state=counts.get('state'))


def pair_score_rows(inputs, frame, scores, denied, residuals_active, labels):
    """One ndjson row per unordered pair: estimate, evidence availability, confidence."""
    window = dict(reference_date=inputs['reference_date'],
                  congress_range=inputs['congress_range'],
                  panel_start=inputs['panel_start'],
                  timing='strict_before_reference_date',
                  signatures='original',
                  definitions='run_receipt.json:definitions')
    nominate_on = inputs.get('nominate') is not None
    for k, pair in enumerate(frame['pairs']):
        rows = (2 * k, 2 * k + 1)
        work_state = frame['work_states'][rows[0]]
        entry = labels.get(pair['pair_id'])
        state, all_states = label_state_of(entry)
        estimate, confidence = {}, {}
        for spec_name in SPEC_ORDER:
            estimate[spec_name] = {}
            confidence[spec_name] = {}
            for axis in AXES:
                block = scores[spec_name][axis]
                estimate[spec_name][axis] = {}
                confidence[spec_name][axis] = {}
                for label, row in (('a_to_b', rows[0]), ('b_to_a', rows[1])):
                    expected = block['expected'][row]
                    scored = bool(np.isfinite(expected))
                    cell = dict(expected_grade=num(expected),
                                prediction_state=SCORED if scored
                                else not_scored_reason(spec_name, frame, row, block))
                    if spec_name == 'joint' and scored:
                        cell['probability_by_grade'] = [num(p, 5)
                                                        for p in block['probability'][row]]
                    if SPECS[spec_name]['partial']:
                        cell['partial'] = True
                        cell['partial_channel'] = SPECS[spec_name]['channel']
                    estimate[spec_name][axis][label] = cell
                    confidence[spec_name][axis][label] = dict(
                        bootstrap_standard_error=num(block['se'][row]))
        evidence = dict(
            window=window,
            work=dict(state=work_state, chamber_layer=pair['chamber_layer'],
                      eligible_target_sponsored_bills=dict(
                          a_to_b=pair['opportunities'][0], b_to_a=pair['opportunities'][1],
                          definition='chamber_work.py:124'),
                      original_signatures=dict(a_to_b=pair['originals'][0],
                                               b_to_a=pair['originals'][1]),
                      shared_original_bills=pair['shared_original_bills'],
                      shared_eligible_bills=pair['shared_eligible_bills'],
                      co_service_years=num(pair['co_service_years']),
                      co_service_years_state=(WORK_CROSS_CHAMBER
                                              if pair['chamber_layer'] == 'cross_chamber'
                                              else 'same_chamber_measured')),
            speech=dict(a_to_b=speech_evidence(pair, 'a_to_b', frame['speech_states'][rows[0]]),
                        b_to_a=speech_evidence(pair, 'b_to_a', frame['speech_states'][rows[1]])),
            coverage_tier=dict(a=pair['coverage_tier'][0], b=pair['coverage_tier'][1]),
            visibility=pair['visibility'])
        if nominate_on:
            evidence['nominate'] = dict(
                a=NOMINATE_RANKS.get(pair['nominate_ranks'][0]),
                b=NOMINATE_RANKS.get(pair['nominate_ranks'][1]),
                note='per-congress NOMINATE where a row exists for that member, congress and '
                     'chamber; the static members.json value otherwise; never imputed')
        if residuals_active:
            if inputs.get('residuals_directed') is not None:
                by_direction = pair.get('residual_by_direction') or {}
                evidence['work']['residual_substitution'] = dict(
                    active=True, undirected=False, directed=True,
                    a_to_b=residual_counts_block(by_direction.get('a_to_b')),
                    b_to_a=residual_counts_block(by_direction.get('b_to_a')))
            else:
                evidence['work']['residual_substitution'] = dict(
                    active=True, undirected=True, **residual_counts_block(pair['residual']))
        yield dict(pair=pair['pair'], pair_id=pair['pair_id'], names=pair['names'],
                   chamber_layer=pair['chamber_layer'], heldout=pair['pair_id'] in denied,
                   label=dict(state=state, states=all_states,
                              detail=(entry or {}).get('detail', {})),
                   work_state=work_state,
                   speech_state=dict(a_to_b=frame['speech_states'][rows[0]],
                                     b_to_a=frame['speech_states'][rows[1]]),
                   estimate=estimate, evidence_availability=evidence, confidence=confidence)


def state_summary(frame, scores, denied, inputs, labels):
    """Counts of every state over the whole universe, each with its denominator."""
    n_pairs = len(frame['pairs'])
    work = Counter(frame['work_states'][2 * k] for k in range(n_pairs))
    for state in WORK_STATES:
        work.setdefault(state, 0)
    speech = Counter(frame['speech_states'])
    for state in SPEECH_STATES:
        speech.setdefault(state, 0)
    label_counts = Counter()
    for state in LABEL_STATES:
        label_counts.setdefault(state, 0)
    for pair in frame['pairs']:
        label_counts[label_state_of(labels.get(pair['pair_id']))[0]] += 1
    prediction = {}
    for spec_name in SPEC_ORDER:
        prediction[spec_name] = {}
        for axis in AXES:
            block = scores[spec_name][axis]
            counts = Counter()
            for row in range(frame['rows']):
                if np.isfinite(block['expected'][row]):
                    counts[SCORED] += 1
                else:
                    counts[not_scored_reason(spec_name, frame, row, block)] += 1
            prediction[spec_name][axis] = dict(counts=dict(sorted(counts.items())),
                                               denominator=frame['rows'])
    both_axes = {}
    for spec_name in SPEC_ORDER:
        finite = (np.isfinite(scores[spec_name]['affinity']['expected'])
                  & np.isfinite(scores[spec_name]['friction']['expected']))
        by_pair = finite.reshape(n_pairs, 2)
        both_axes[spec_name] = dict(
            directed_rows_scored_on_both_axes=int(finite.sum()),
            pairs_scored_on_both_axes_in_both_directions=int(by_pair.all(axis=1).sum()),
            pairs_scored_on_both_axes_in_at_least_one_direction=int(by_pair.any(axis=1).sum()),
            denominator_directed_rows=int(frame['rows']), denominator_pairs=n_pairs)
    return dict(status=STATUS, reference_date=inputs['reference_date'],
                congress_range=inputs['congress_range'],
                universe=dict(members=len(inputs['members']), pairs=n_pairs,
                              directed_rows=frame['rows'], known_panel_gaps=PANEL_GAPS),
                heldout_pairs_in_universe=sum(1 for p in frame['pairs']
                                              if p['pair_id'] in denied),
                heldout_note='scored like every other pair and excluded, by assertion, from '
                             'every validation table, diagnostic and reported figure',
                work_state_counts=dict(sorted(work.items())), work_state_denominator=n_pairs,
                speech_state_counts=dict(sorted(speech.items())),
                speech_state_denominator=frame['rows'],
                label_state_counts=dict(sorted(label_counts.items())),
                label_state_denominator=n_pairs,
                observed_feature_cells=frame['observed_columns'],
                observed_feature_denominator=frame['rows'],
                nominate_rank_counts={NOMINATE_RANKS[k]: v
                                      for k, v in frame['nominate_ranks'].items()
                                      if k in NOMINATE_RANKS},
                prediction_state_counts=prediction, scored_on_both_axes=both_axes)


# -------------------------------------------------------------------- report


DESIGN_CHOICES = [
    dict(choice='Which fitted G-model is the estimate.',
         note='`G2_chamber_context_work` minus the two visibility columns was used, because it is '
              'the richest specification carrying no personality term and P1-10 forbids adding '
              'any. `G1_pooled_context_work` minus visibility is the pooled-slope alternative. '
              'Neither was selected on an outer score, as CHAMBER_DEGREES_V6.md requires.'),
    dict(choice='The two partial estimates are not fitted G-models.',
         note='`work_only` and `speech_only` are the same OrdinalDegrees family restricted to one '
              'channel. The lane has never fitted either, so they are labelled partial in every '
              'row and are not a second model family.'),
    dict(choice='Speech features are not date-cut.',
         note='`expression_contrasts.ndjson` pools the whole systematic-encounter census, so the '
              'speech channel on the dated degree records is measured after the documented event. '
              'This is the same leak the benchmark contract names under '
              '`known_leak_under_all_history`, and it makes `speech_only` a diagnostic, not a '
              'strict-before row.'),
    dict(choice='Mean imputation inside a present channel.',
         note='P1-11 is enforced at the channel gate: a pair with no work never receives a work '
              'estimate. Inside a present channel, individual missing context cells still use the '
              "model's own train-fitted missingness-indicator encoding, because that encoding is "
              'part of the fitted family and removing it would be a different model.'),
    dict(choice='The training rows sit on the same bill panel as the universe rows.',
         note='`OrdinalDegrees` standardises the universe by the training distribution, so a '
              'model fitted on frozen 116-119 work columns and applied to a 115-119 universe '
              'would move every estimate for a reason that has nothing to do with the '
              'relationship. The degree records therefore carry work columns rebuilt with the '
              'same builder on whatever panel `--bills` and `--congress-range` select. On the '
              'frozen default panel that rebuild is asserted to reproduce '
              '`20260910_chamber_degrees_v6/features.json` cell for cell, and a disagreement '
              'raises -- to a float32 tolerance of %g, because chamber_work accumulates through '
              'float32 matrix products whose reduction order BLAS may change between runs. On '
              'the frozen panel the rebuild agreed with v6 on every cell inside that tolerance, '
              'with a largest gap of about 1e-8 and none beyond it. Whether the wider panel '
              'should instead be treated as a different experiment is Paul\'s call.'
              % FLOAT32_TOLERANCE),
    dict(choice='The shared-eligible denominator is recomputed, not taken from the builder.',
         note='`chamber_work.temporal_features` keeps its co-eligible matrix internal, so '
              '`shared_eligible_bills` is rebuilt here from the same eligibility rule and then '
              'cross-checked: every opportunity count the builder published is reproduced from '
              'the recomputed eligibility matrix, and a disagreement raises rather than warns.'),
    dict(choice='The work-residual substitution is undirected by default.',
         note='`--work-residuals` reads `pair_work_pooled.ndjson`, one row per unordered pair '
              'pooled over chambers and congresses, so both directions of a pair receive the '
              'same residual and rate-ratio columns. `--work-residuals-directed` reads the '
              'producer\'s per-(signer, sponsor, congress) cell file instead and pools it here '
              'per direction, so the two directions of a pair can differ or one can be absent; '
              'it is an EXPLORATORY fourth variant, not a replacement, pending Paul\'s choice '
              'between the two.'),
    dict(choice='"Both passes agreed" was read strictly.',
         note='Only `merge_rule == "exact"` cells enter the graded-sample table. The '
              '`min_of_adjacent` cells, where the two passes differed by one grade, are counted '
              'separately and never pooled into the reported figure.'),
    dict(choice='Bootstrap resampling unit.',
         note='Whole evidence-family components of the labelled rows are resampled, which is '
              'stricter than the dyad resampling CONTRACT.md uses for the sign benchmark, because '
              'the degree records share source families across dyads.'),
    dict(choice='Minimum class size before a presence-vs-ordinary AUC is printed.',
         note='Set at %d units per class. Below that the cell prints `n too small` with both '
              'class counts instead of a number.' % MIN_AUC_CLASS),
    dict(choice='The 133 no-evidence probability-sample rows are a count, not a class.',
         note='They are reported as the ordinary reference count. They were not used as the '
              'negative class of an AUC, because ranking a graded pair against a no-evidence pair '
              'ranks evidence availability rather than degree, and P1-6 separates those two.'),
    dict(choice='The blind re-grade is a second label set, not a replacement.',
         note='The universe estimate is fitted on the original v6 grades. The records where both '
              'blind passes agree are reported as a separate leave-one-record-out row with its '
              'own denominator, never merged into the original row.'),
    dict(choice="The sign diagnostic keeps the benchmark contract's personality columns.",
         note='It reproduces the stored canonical row R0_novis unchanged. Those columns are the '
              'existing row, not personality terms added here, so P1-10 is not engaged.'),
    dict(choice='Per-congress NOMINATE is a flag, not the default.',
         note='`--nominate-file` replaces `actor_dw1`, `target_dw1`, `actor_dw2`, `target_dw2` '
              'and `dw1_distance` with the VoteView row for that member, congress and chamber, in '
              'the training rows and the universe rows alike. Without the flag the static '
              'members.json values are used, which is exactly what the v6 fit used. A member with '
              'no row anywhere leaves the column missing; it is never imputed.'),
]

LIMITATIONS = [
    'The estimate is fitted on a few dozen graded research annotations per axis. That is a '
    'grading exercise over reviewed evidence, not an accuracy estimate for any population.',
    'The degree records are single-assistant annotations. The blind re-grade measures how far a '
    'second and third pass agree with the first, not accuracy against a population.',
    'The bootstrap carries refitting variability over the labelled units only. It carries no '
    'specification-search variability, no annotation variability and no coverage guarantee.',
    'Personality, ideology and visibility are fixed retrospective measurements even on the '
    'strict-before work rows.',
    'Cross-chamber pairs have no same-bill work by construction, so their estimate is absent, '
    'not low.',
    'No causal reading is available from any figure here: these are gradings and rankings of '
    'documented evidence, not effects.',
]


def _auc_text(auc):
    if auc.get('auc') is None:
        return ('n too small: %d presence, %d ordinary, minimum %d per class'
                % (auc.get('positive', 0), auc.get('negative', 0), MIN_AUC_CLASS))
    return '%.4f (%g/%d)' % (auc['auc'], auc['concordant'], auc['comparisons'])


def report_text(receipt):
    summary = receipt['label_states']
    fits = receipt['fits']
    universe = summary['universe']
    lines = ['# Universe pair scores: estimate, evidence availability, confidence', '',
             '**STATUS: EXPLORATORY.** Nothing below is a validated instrument, a forecast or a '
             'causal statement. Every figure is a grading or ranking summary over reviewed '
             'research evidence and carries its own denominator in the same sentence.', '',
             '## Universe and reference date', '',
             'The universe is every unordered pair of the %s members in the lane member panel: '
             '%s pairs, %s directed rows, scored at reference date %s. Work features use bills '
             'introduced strictly before that date, original signatures only, congresses %s-%s '
             'from panel start %s (%s bills read, %s outside the range).'
             % (f"{universe['members']:,}", f"{universe['pairs']:,}",
                f"{universe['directed_rows']:,}", receipt['reference_date'],
                receipt['congress_range'][0], receipt['congress_range'][1],
                receipt['panel_start'], f"{receipt['bill_panel']['included_bills']:,}",
                f"{receipt['bill_panel']['excluded_outside_range']:,}"), '']
    for bioguide, note in sorted(PANEL_GAPS.items()):
        lines += ['Known panel gap: %s (%s).' % (note, bioguide), '']
    lines += ['%s of the %s pairs are sealed held-out pairs. They are scored like every other pair '
              'in `pair_scores.ndjson` and are refused, by assertion, from every table below; '
              'this file and `validation_predictions.ndjson` are scanned for their pair ids '
              'before the run is allowed to succeed.'
              % (summary['heldout_pairs_in_universe'], f"{universe['pairs']:,}"), '',
              '## Counts per state', '',
              'Work state, over %s pairs:' % f"{summary['work_state_denominator']:,}", '',
              '| work state | pairs | share of %s |' % f"{summary['work_state_denominator']:,}",
              '| --- | ---: | ---: |']
    for state, count in summary['work_state_counts'].items():
        lines.append('| `%s` | %s | %.1f%% |'
                     % (state, f'{count:,}', 100 * count / summary['work_state_denominator']))
    lines += ['', 'Speech state, over %s directed rows:'
              % f"{summary['speech_state_denominator']:,}", '',
              '| speech state | directed rows | share of %s |'
              % f"{summary['speech_state_denominator']:,}", '| --- | ---: | ---: |']
    for state, count in summary['speech_state_counts'].items():
        lines.append('| `%s` | %s | %.1f%% |'
                     % (state, f'{count:,}', 100 * count / summary['speech_state_denominator']))
    lines += ['', 'Label state, over %s pairs:' % f"{summary['label_state_denominator']:,}", '',
              '| label state | pairs |', '| --- | ---: |']
    for state, count in summary['label_state_counts'].items():
        lines.append('| `%s` | %s |' % (state, f'{count:,}'))
    lines += ['', 'Every pair carrying no lane label is `not_assessed`; the word `unknown` appears '
              'nowhere in the output schema. A pair can hold more than one kind of label, so the '
              'state counted above is the first of the fixed precedence order %s and every label '
              'the pair holds is listed in its own `label.states`.'
              % ' > '.join('`%s`' % s for s in LABEL_STATES), '',
              '### Prediction state, by specification and axis', '',
              '| specification | axis | scored | not scored, by reason | denominator |',
              '| --- | --- | ---: | --- | ---: |']
    for spec_name in SPEC_ORDER:
        for axis in AXES:
            block = summary['prediction_state_counts'][spec_name][axis]
            scored = block['counts'].get(SCORED, 0)
            other = '; '.join('`%s` %s' % (k, f'{v:,}') for k, v in block['counts'].items()
                              if k != SCORED) or 'none'
            lines.append('| %s | %s | %s | %s | %s |'
                         % (spec_name, axis, f'{scored:,}', other, f"{block['denominator']:,}"))
    lines += ['', '### Scored on both axes', '',
              '| specification | directed rows on both axes | pairs, both directions | pairs, at '
              'least one direction | denominators |', '| --- | ---: | ---: | ---: | --- |']
    for spec_name in SPEC_ORDER:
        block = summary['scored_on_both_axes'][spec_name]
        lines.append('| %s | %s | %s | %s | %s directed rows, %s pairs |'
                     % (spec_name, f"{block['directed_rows_scored_on_both_axes']:,}",
                        f"{block['pairs_scored_on_both_axes_in_both_directions']:,}",
                        f"{block['pairs_scored_on_both_axes_in_at_least_one_direction']:,}",
                        f"{block['denominator_directed_rows']:,}",
                        f"{block['denominator_pairs']:,}"))
    lines += ['', '### Evidence-availability denominators', '',
              'Shared eligible bills were recomputed from the same eligibility rule the work '
              'builder uses and cross-checked against it: %s published opportunity counts were '
              'reproduced exactly, %s disagreed.'
              % (f"{receipt['shared_eligible']['checked_counts']:,}",
                 receipt['shared_eligible']['mismatches']), '',
              'Every pair row in `pair_scores.ndjson` carries its own window block and every '
              'denominator as a value. The prose defining each of them is written once, into '
              '`run_receipt.json` under `definitions`, rather than repeated in %s rows:'
              % f"{universe['pairs']:,}", '',
              '| field | definition |', '| --- | --- |']
    for field, note in sorted(receipt['definitions'].items()):
        lines.append('| `%s` | %s |' % (field, note))
    lines += ['', 'Observed feature cells over %s directed rows, so a present channel with an '
              'individual missing cell is visible rather than hidden:'
              % f"{summary['observed_feature_denominator']:,}", '',
              '| column | observed cells | share |', '| --- | ---: | ---: |']
    for column, count in summary['observed_feature_cells'].items():
        lines.append('| `%s` | %s | %.1f%% |'
                     % (column, f'{count:,}',
                        100 * count / summary['observed_feature_denominator']))
    if summary['nominate_rank_counts']:
        lines += ['', 'Per-congress NOMINATE resolution, over member slots in the universe: '
                  + '; '.join('`%s` %s' % (k, f'{v:,}')
                              for k, v in sorted(summary['nominate_rank_counts'].items())) + '.']
    lines += ['', '## The fitted development model', '',
              "The estimate is the lane's existing cumulative-logit `OrdinalDegrees` family, fit "
              'on the dated v6 degree records. Three specifications are reported side by side; the '
              'two partial ones exist so a pair with one channel still shows what that channel '
              'says.', '',
              '| specification | features | chamber slopes | partial | axis | graded rows | graded '
              'dyads | refits fitted / requested |',
              '| --- | ---: | --- | --- | --- | ---: | ---: | --- |']
    for spec_name in SPEC_ORDER:
        block = fits[spec_name]
        for axis in AXES:
            record = block['axes'][axis]
            boot = record.get('bootstrap') or {}
            lines.append('| %s | %d | %s | %s | %s | %d | %d | %s |'
                         % (spec_name, len(block['features']), block['chamber_slopes'],
                            block['partial'], axis, record['labelled_rows'],
                            record['labelled_dyads'],
                            '%d / %d' % (boot.get('fitted', 0), boot.get('requested', 0))
                            if boot else 'not fitted'))
    lines += ['', 'Estimate feature list (%d columns): `%s`.'
              % (len(fits['joint']['features']), '`, `'.join(fits['joint']['features'])), '',
              'Basis: %s.' % fits['joint']['basis'], '',
              'The two visibility columns `%s` left the estimate under ruling 7 and appear only '
              'under `evidence_availability.visibility`.'
              % '`, `'.join(VISIBILITY_OUT_OF_ESTIMATE), '',
              'Confidence is the standard deviation of the expected grade over %d source-resampled '
              'refits, resampling whole evidence-family components of the labelled rows with '
              'replacement. It is never the model probability.' % receipt['bootstrap_replicates'],
              '']
    panel = receipt.get('training_work_panel') or {}
    if panel:
        lines += ['The %d degree records carry work columns rebuilt on this run\'s own bill panel, '
                  'so the fit and the universe stand on one panel. Of %s rebuilt cells compared '
                  'against the frozen v6 `features.json`, %s are equal exactly, %s agree inside '
                  'the float32 tolerance %g, and %s differ beyond it (largest absolute gap %s). '
                  'On the frozen default panel a single cell beyond the tolerance stops the run. '
                  '%s'
                  % (panel['records'], f"{panel['cells_compared']:,}",
                     f"{panel['cells_exactly_equal']:,}",
                     f"{panel['cells_within_float32_tolerance']:,}", panel['tolerance'],
                     f"{panel['cells_beyond_tolerance']:,}", panel['max_absolute_difference'],
                     panel['tolerance_note'] + '.'), '']
    lines += ['## Sign benchmark (diagnostic only)', '']
    sign = receipt['sign_diagnostic']
    if not sign:
        lines += ['The benchmark contract work panel is not present, so the sign diagnostic was '
                  'not computed on this run.', '']
    else:
        lines += ['Two axes are reported side by side in `pair_scores.ndjson`. The signed benchmark '
                  'below is a diagnostic under ruling P1-8 and never collapses them.', '',
                  '| row | dyads | positive | negative | comparisons | same-fit AUC | 95% dyad '
                  'bootstrap CI |', '| --- | ---: | ---: | ---: | ---: | ---: | --- |']
        for row in sign['rows']:
            lines.append('| %s | %d | %d | %d | %d/%d | %.4f (%g/%d) | [%.4f, %.4f] |'
                         % (row['row'], row['dyads'], row['positive'], row['negative'],
                            row['comparisons'], row['expected_comparisons'], row['same_fit_auc'],
                            row['concordant'], row['comparisons'], row['bootstrap']['low'],
                            row['bootstrap']['high']))
        dropped = ', '.join('%s (index %d)' % (' / '.join(d['names']), d['index'])
                            for d in sign['dropped_dyads'])
        lines += ['', 'Dropped dyads: %s. Drop rule: %s.'
                  % (dropped or 'none', sign['drop_rule']), '',
                  "Both intervals are %d-replicate dyad bootstraps at seed %d, the benchmark "
                  "contract's own procedure; they resample labels only and carry no refitting or "
                  'selection variability.' % (SIGN_BOOTSTRAP, SIGN_SEED), '',
                  'Holding the all-dyad fits fixed and removing only the affected comparisons '
                  'gives %.4f (%g/%d) instead. That is a different quantity from the refit row '
                  'above, not an alternative estimate of it.'
                  % (sign['held_fits_variant']['same_fit_auc'],
                     sign['held_fits_variant']['concordant'],
                     sign['held_fits_variant']['comparisons']), '',
                  'This diagnostic reads the benchmark contract\'s own cached work panel `%s`, '
                  'which is fixed at congresses 116-119, so it does not move with `--bills`, '
                  '`--congress-range` or `--work-residuals`. It is reproduced here unchanged and '
                  'is identical in every run of the comparison table below; a difference there '
                  'would mean the cached panel had changed, not that this run scored better.'
                  % sign['specification']['work_panel'], '']
    blind = receipt['degree_records']['blind_agreement']
    lines += ['## The v6 degree records', '',
              'Leave-one-record-out, holding out the record with its transitive evidence-family '
              'and endpoint exclusions, exactly as `ordinal_degrees.training_indices` defines '
              'them. Two label sets are reported side by side and never merged: the original v6 '
              'grades, and the records where both blind re-grading passes produced the same grade '
              '(%s).'
              % '; '.join('%s %d agreed of %d assessed by both'
                          % (axis, blind['agreed'][axis], blind['both_assessed'][axis])
                          for axis in AXES), '',
              '| label set | specification | axis | records | scored | not scored | dyads | mean '
              'absolute grade error | denominator |',
              '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for entry in receipt['degree_records']['summaries']:
        lines.append('| %s | %s | %s | %d | %d | %d | %d | %s | %s |'
                     % (entry['label_source'], entry['specification'], entry['axis'],
                        entry['records'], entry['scored'], entry['not_scored'], entry['dyads'],
                        entry.get('mean_absolute_grade_error', 'n/a'),
                        entry.get('denominator', 'n/a')))
    lines += ['', 'The record file holds %d dated records over %d graded affinity rows and %d '
              'graded friction rows under the original grades.'
              % (receipt['degree_records']['records'],
                 fits['joint']['axes']['affinity']['labelled_rows'],
                 fits['joint']['axes']['friction']['labelled_rows']), '',
              '**Caveat.** These records are ungraded under the current contract: they are '
              'single-assistant research annotations. The blind re-grade measures how far a second '
              'and a third pass agree with the first, so agreement between a model expected grade '
              'and either label set is agreement with reviewers, not accuracy against a '
              'population.', '']
    table = receipt['graded_sample']
    lines += ['## The graded development pairs of the probability sample', '',
              '%d of the %d development rows were graded by two blind passes; the remaining %d are '
              'no-evidence rows and are reported here as the ordinary reference count only.'
              % (table['graded_pairs'], table['development_rows'], table['no_evidence_rows']), '',
              '| axis | cells where both passes agreed | pairs | grade histogram | scored by the '
              'joint estimate | mean absolute grade error | presence-vs-ordinary AUC |',
              '| --- | ---: | ---: | --- | ---: | ---: | --- |']
    for axis in AXES:
        block = table['summary'][axis]
        joint = block['joint']
        lines.append('| %s | %d | %d | %s | %d/%d | %s | %s |'
                     % (axis, block['agreed_cells'], block['pairs'],
                        ', '.join('grade %s: %s' % kv
                                  for kv in sorted(block['grade_histogram'].items())),
                        joint['scored_cells'], joint['denominator'],
                        joint.get('mean_absolute_grade_error', 'n/a'),
                        _auc_text(joint['presence_vs_ordinary_auc'])))
    lines += ['', 'Agreement rule: %s.' % table['summary']['affinity']['agreement_rule'], '',
              'The denominator chain from every graded cell to the table above:', '',
              '| axis | cells carrying a whole grade | still awaiting adjudication | merged by '
              '`min_of_adjacent` | left in the table |',
              '| --- | ---: | ---: | ---: | ---: |']
    for axis in AXES:
        block = table['summary'][axis]
        lines.append('| %s | %d | %d | %d | %d |'
                     % (axis, block['graded_cells'], block['adjudication_pending_cells'],
                        block['sensitivity_cells_min_of_adjacent'], block['agreed_cells']))
    lines += ['', 'The `min_of_adjacent` cells, where the two passes differed by one grade, are '
              'kept out of the reported figure and listed in '
              '`validation_tables.json` under `graded_development_sensitivity_cells`.', '']
    comparison = receipt.get('comparison')
    lines += ['## Comparison across runs', '']
    if not comparison or not comparison.get('runs'):
        lines += ['No sibling run was supplied with `--compare` on this run, so no comparison '
                  'table is printed. The flag takes the output directory of another run of this '
                  'module.', '']
    else:
        lines += ['| run | congress range | work columns | pairs | work available | joint affinity '
                  'scored | joint friction scored | sign AUC, all dyads | sign AUC, without the '
                  'zero-work cross-chamber dyads |',
                  '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
        for item in comparison['runs']:
            lines.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s |'
                         % (item['run'], item['congress_range'], item['work_columns'],
                            f"{item['pairs']:,}", f"{item['work_available']:,}",
                            f"{item['joint_affinity_scored']:,}",
                            f"{item['joint_friction_scored']:,}",
                            item['sign_all'] if item['sign_all'] is not None else 'n/a',
                            item['sign_without'] if item['sign_without'] is not None else 'n/a'))
        lines += ['', 'Each compared run is a separate output directory with its own receipt; the '
                  'sha256 of each receipt is in the receipt table below. The rows are not paired '
                  'tests and no difference between them is a hypothesis test. The two sign-AUC '
                  'columns are expected to be identical across every row, because that diagnostic '
                  "reads the benchmark contract's cached 116-119 work panel rather than this "
                  "run's; they are printed so that a change in them is visible, not as a "
                  'comparison between the runs.', '',
                  '| run | joint affinity graded rows | joint affinity graded dyads | joint '
                  'friction graded rows | cells beyond the v6 float32 tolerance |',
                  '| --- | ---: | ---: | ---: | ---: |']
        for item in comparison['runs']:
            lines.append('| %s | %s | %s | %s | %s |'
                         % (item['run'], item['affinity_rows'], item['affinity_dyads'],
                            item['friction_rows'], item['training_cells_beyond_tolerance']))
        lines += ['', 'A wider bill panel changes how many degree records have a present work '
                  'channel at their own date, so the number of rows the fit stands on moves with '
                  'the panel. That is the count the row above reports, with its own denominator '
                  'of %d dated records.' % receipt['degree_records']['records'], '']
    lines += ['## Design choices pending Paul', '']
    for item in receipt['design_choices']:
        lines.append('- **%s** %s' % (item['choice'], item['note']))
    lines += ['', '## Limitations carried by every figure above', '']
    for item in receipt['limitations']:
        lines.append('- %s' % item)
    lines += ['', '## Receipt', '', '| artefact | bytes | sha256 |', '| --- | ---: | --- |']
    for item in receipt['artefacts']:
        lines.append('| `%s` | %s | `%s` |' % (item['name'], f"{item['bytes']:,}", item['sha256']))
    lines += ['', '| input | sha256 |', '| --- | --- |']
    for _, item in sorted(receipt['inputs'].items()):
        lines.append('| `%s` | `%s` |' % (item['path'], item['sha256']))
    if comparison and comparison.get('runs'):
        lines += ['', '| compared run | receipt sha256 |', '| --- | --- |']
        for item in comparison['runs']:
            lines.append('| `%s` | `%s` |' % (item['path'], item['receipt_sha256']))
    lines += ['', 'Wall clock %.1f s. Glassbox run id `%s`. Reference date %s. Bootstrap %d '
              'replicates at seed %d. Work residual substitution: %s. Per-congress NOMINATE: %s.'
              % (receipt['runtime_seconds'], receipt['glassbox_run_id'], receipt['reference_date'],
                 receipt['bootstrap_replicates'], receipt['seed'],
                 'active' if receipt['work_residuals']['active'] else 'not supplied',
                 receipt['nominate']['path'] or 'not supplied'), '']
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- comparison


def comparison_table(paths):
    """Read sibling run receipts and line their headline counts up in one table."""
    runs = []
    for path in paths or ():
        receipt_path = Path(path)
        if receipt_path.is_dir():
            receipt_path = receipt_path / 'run_receipt.json'
        if not receipt_path.is_file():
            raise FileNotFoundError('Compared run has no receipt: %s' % receipt_path)
        other = read_json(receipt_path)
        states = other['label_states']
        sign = other.get('sign_diagnostic') or {}
        by_row = {r['row']: r['same_fit_auc'] for r in sign.get('rows', [])}
        counts = states['prediction_state_counts']['joint']
        axes = other['fits']['joint']['axes']
        panel = other.get('training_work_panel') or {}
        runs.append(dict(
            run=receipt_path.parent.name, path=relative(receipt_path),
            receipt_sha256=digest(receipt_path),
            congress_range='%s-%s' % tuple(other['congress_range']),
            work_columns=('residual_directed' if other['work_residuals'].get('directed')
                          else 'residual' if other['work_residuals']['active'] else 'raw'),
            pairs=states['universe']['pairs'],
            work_available=states['work_state_counts'].get(WORK_AVAILABLE, 0),
            joint_affinity_scored=counts['affinity']['counts'].get(SCORED, 0),
            joint_friction_scored=counts['friction']['counts'].get(SCORED, 0),
            affinity_rows=axes['affinity']['labelled_rows'],
            affinity_dyads=axes['affinity']['labelled_dyads'],
            friction_rows=axes['friction']['labelled_rows'],
            training_cells_beyond_tolerance=panel.get('cells_beyond_tolerance'),
            sign_all=by_row.get('all_dyads'),
            sign_without=by_row.get('without_zero_work_cross_chamber')))
    return runs


# ---------------------------------------------------------------------- build


def build(out_dir, inputs, bootstrap=BOOTSTRAP, seed=SEED, compare=(), progress=print, stage=noop):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    denied = inputs['denied']
    residuals_active = inputs['residuals'] is not None or inputs.get('residuals_directed') is not None
    rows = training_rows(inputs, residuals_active)
    assert_no_heldout([r['pair_id'] for r in rows], denied, 'degree_records')
    assert_no_heldout([pair_id_of(*c['pair']) for c in inputs['cases']], denied, 'sign_dyads')
    blind, blind_audit = blind_agreement_labels(inputs['regrade_a'], inputs['regrade_b'])
    blind_rows = training_rows(inputs, residuals_active, grades=blind,
                               label_source='blind_passes_agree')
    stage('training', '%d dated degree records loaded' % len(rows))

    frame = universe_frame(inputs, residuals_active, progress)
    stage('universe', '%d pairs, %d directed rows' % (len(frame['pairs']), frame['rows']))

    scores, fits = score_universe(frame, rows, residuals_active, bootstrap, seed, progress, stage)
    labels = label_index(inputs)

    written = write_rows(out_dir / 'pair_scores.ndjson',
                         pair_score_rows(inputs, frame, scores, denied, residuals_active, labels))
    stage('pair_scores', '%d pair rows written' % written)

    summary = state_summary(frame, scores, denied, inputs, labels)
    write_json(out_dir / 'label_states_summary.json', clean(summary))

    validation, degree_summaries = [], []
    for source, source_rows in (('original', rows), ('blind_passes_agree', blind_rows)):
        for spec_name in SPEC_ORDER:
            for axis in AXES:
                predictions, block = leave_one_record_out(source_rows, axis, spec_name,
                                                          residuals_active)
                degree_summaries.append(dict(block, label_source=source))
                for item in predictions:
                    validation.append(dict(item, table='degree_records',
                                           specification=spec_name))
    graded_rows, graded_summary, sensitivity = graded_sample_table(inputs, frame, scores, denied)
    for item in graded_rows:
        validation.append(dict(item, table='graded_development_pairs'))

    sign = None
    if inputs.get('sign'):
        sign = sign_diagnostic(inputs, inputs['sign'], denied, progress)
        for case in inputs['cases']:
            validation.append(dict(table='sign_dyads', pair=list(case['pair']),
                                   pair_id=pair_id_of(*case['pair']), names=case['names'],
                                   sign=case['sign'], y=case['y'], first=case['first'],
                                   note='the signed benchmark is a diagnostic; the same-fit rows '
                                        'live in sign_diagnostic.json'))
    write_json(out_dir / 'sign_diagnostic.json',
               clean(sign) if sign else dict(status=STATUS, state='not_computed',
                                             reason='benchmark contract work panel absent'))
    assert_no_heldout([r['pair_id'] for r in validation if r.get('pair_id')], denied,
                      'validation_predictions')
    write_rows(out_dir / 'validation_predictions.ndjson', [clean(r) for r in validation])
    assert_text_free_of_heldout(
        (out_dir / 'validation_predictions.ndjson').read_text(encoding='utf-8'), denied,
        'validation_predictions.ndjson')
    stage('validation', '%d validation rows written' % len(validation))

    no_evidence = sum(1 for r in inputs['labels']
                      if r['label_status'] != 'two_blind_model_passes_merged')
    tables = dict(status=STATUS, reference_date=inputs['reference_date'],
                  sign_dyads=clean(sign) if sign else None,
                  degree_records=clean(degree_summaries),
                  blind_agreement=clean(blind_audit),
                  graded_development_pairs=clean(graded_summary),
                  graded_development_sensitivity_cells=clean(sensitivity),
                  heldout_refused=['degree_records', 'graded_development_pairs', 'sign_dyads'])
    write_json(out_dir / 'validation_tables.json', tables)

    return dict(
        status=STATUS, reference_date=inputs['reference_date'], seed=seed,
        bootstrap_replicates=bootstrap, penalty=PENALTY,
        congress_range=inputs['congress_range'], panel_start=inputs['panel_start'],
        bill_panel=clean(inputs['bill_audit']),
        universe=summary['universe'], label_states=summary,
        fits={k: clean(v) for k, v in fits.items()},
        sign_diagnostic=clean(sign) if sign else None,
        degree_records=dict(records=len(rows), summaries=clean(degree_summaries),
                            blind_agreement=clean(blind_audit),
                            caveat='single-assistant annotations; the blind re-grade measures '
                                   'agreement between passes, not accuracy'),
        graded_sample=dict(development_rows=len(inputs['labels']),
                           graded_pairs=len(inputs['labels']) - no_evidence,
                           no_evidence_rows=no_evidence,
                           no_evidence_note='reported as the ordinary reference count only',
                           summary=clean(graded_summary), sensitivity_cells=clean(sensitivity)),
        work_residuals=dict(active=residuals_active,
                            directed=inputs.get('residuals_directed') is not None,
                            path=(relative(inputs['residual_path'])
                                  if inputs['residual_path'] else None),
                            audit=clean(inputs['residual_audit']),
                            replaced_columns=RAW_WORK_COLUMNS if residuals_active else [],
                            substituted_columns=RESIDUAL_FEATURES if residuals_active else [],
                            note=('the raw bill-rate work columns were replaced by the baseline '
                                  'residual and rate-ratio columns; co_service_years is a dated '
                                  'service count and was left in place') if residuals_active
                            else 'not supplied; raw work columns used',
                            directed_source=(dict(
                                path=relative(inputs['residual_directed_path']),
                                sha256=inputs['digests']['work_residuals_directed']['sha256'],
                                rows_pooled=inputs['residual_directed_audit']['rows_read'],
                                directions_produced=inputs['residual_directed_audit']['directions'],
                                directions_covered=frame['directed_coverage'].get('covered', 0),
                                directions_missing=frame['directed_coverage'].get(
                                    'no_baseline_row', 0),
                                directions_not_work_available=frame['directed_coverage'].get(
                                    'not_work_available', 0),
                                note='covered + missing + not_work_available sums to twice the '
                                     'pair count, one row per directed universe row')
                                if inputs.get('residuals_directed') is not None else None)),
        nominate=dict(path=relative(inputs['nominate_path']) if inputs['nominate_path'] else None,
                      replaced_columns=list(NOMINATE_COLUMNS) if inputs['nominate_path'] else [],
                      audit=clean(getattr(inputs.get('nominate'), 'audit', None)),
                      rank_counts=summary['nominate_rank_counts'],
                      note='per-congress rows where they exist, the static members.json value as '
                           'the fallback, and nothing imputed'),
        shared_eligible=clean(inputs['eligible_audit']),
        training_work_panel=clean(inputs.get('training_work_audit')),
        definitions=DEFINITIONS,
        work_audit=clean({k: v for k, v in inputs['work_audit'].items() if k != 'snapshots'}),
        heldout=dict(denied_pairs=len(denied),
                     in_universe=summary['heldout_pairs_in_universe'],
                     refused_from=['validation_predictions', 'validation_tables',
                                   'sign_diagnostic', 'graded_development_pairs',
                                   'degree_records', 'REPORT.md']),
        comparison=dict(runs=comparison_table(compare),
                        requested=[str(p) for p in (compare or ())]),
        design_choices=DESIGN_CHOICES, limitations=LIMITATIONS,
        inputs=inputs['digests'], pair_rows=written)


# ---------------------------------------------------------------------- entry


def emitter():
    try:
        from fec.surfaces.glassbox_emit import emit, new_run_id
        return emit, new_run_id
    except ImportError:  # pragma: no cover - path-based fallback to the same file
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            'glassbox_emit', ROOT / 'fec/surfaces/glassbox_emit.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.emit, module.new_run_id


def main(argv=None):
    emit, new_run_id = emitter()

    parser = argparse.ArgumentParser(
        description='Universe pair scoring: estimate, evidence availability, confidence '
                    '(EXPLORATORY)')
    parser.add_argument('--out', default=str(OUT))
    parser.add_argument('--reference-date', default=REFERENCE_DATE)
    parser.add_argument('--bills', default=str(HISTORY / 'bills.ndjson'),
                        help="dated bill panel ndjson, read with this module's own reader so no "
                             'fixed congress filter is applied on the way in')
    parser.add_argument('--congress-range', default='116-119', type=parse_congress_range,
                        help='inclusive range such as 116-119 or 115-119')
    parser.add_argument('--bootstrap', type=int, default=BOOTSTRAP)
    parser.add_argument('--seed', type=int, default=SEED)
    parser.add_argument('--work-residuals', default=None,
                        help='pooled work-baseline ndjson; substitutes the raw bill-rate work '
                             'columns with the residual and rate-ratio columns, the same value '
                             'in both directions of a pair')
    parser.add_argument('--work-residuals-directed', default=None,
                        help='the producer\'s directed pair_work_residuals.ndjson; pools it per '
                             '(signer, sponsor) direction across congresses and substitutes the '
                             'residual and rate-ratio columns per direction, so the two directions '
                             'of a pair can differ or one can be absent. Mutually exclusive with '
                             '--work-residuals')
    parser.add_argument('--nominate-file', default=None,
                        help='votes/HSall_members.csv; substitutes per-congress NOMINATE for the '
                             'static members.json dimensions in training and universe rows alike')
    parser.add_argument('--compare', action='append', default=[],
                        help='another run directory or receipt to line up in REPORT.md; repeatable')
    parser.add_argument('--no-sign-diagnostic', action='store_true')
    args = parser.parse_args(argv)

    run_id = new_run_id('mpr-pair-scoring')
    started = time.time()

    def stage(name, summary, **metadata):
        emit('stage', 'running', summary, run_id=run_id, stage=name,
             source='member_personal_relationships',
             duration_ms=int((time.time() - started) * 1000), metadata=metadata or None)

    emit('task', 'started', 'Universe pair scoring opening', run_id=run_id, stage='start',
         source='member_personal_relationships',
         metadata=dict(out=args.out, reference_date=args.reference_date, bills=args.bills,
                       congress_range=list(args.congress_range), bootstrap=args.bootstrap,
                       work_residuals=args.work_residuals,
                       work_residuals_directed=args.work_residuals_directed,
                       nominate_file=args.nominate_file))
    try:
        inputs = load_inputs(args.reference_date, bills_path=args.bills,
                             congress_range=args.congress_range,
                             work_residuals=args.work_residuals,
                             work_residuals_directed=args.work_residuals_directed,
                             nominate_path=args.nominate_file, stage=stage)
        stage('inputs', 'lane inputs read and universe work panel built')
        if not args.no_sign_diagnostic:
            inputs['sign'] = load_sign_inputs(inputs['members'], inputs['bills'], inputs['cases'])
        receipt = build(args.out, inputs, bootstrap=args.bootstrap, seed=args.seed,
                        compare=args.compare, stage=stage)
        out_dir = Path(args.out)
        receipt['command_line'] = dict(out=args.out, reference_date=args.reference_date,
                                       bills=args.bills,
                                       congress_range=list(args.congress_range),
                                       bootstrap=args.bootstrap, seed=args.seed,
                                       work_residuals=args.work_residuals,
                                       work_residuals_directed=args.work_residuals_directed,
                                       nominate_file=args.nominate_file, compare=args.compare)
        receipt['artefacts'] = [dict(name=n, bytes=(out_dir / n).stat().st_size,
                                     sha256=digest(out_dir / n)) for n in ARTEFACTS]
        receipt['glassbox_run_id'] = run_id
        receipt['runtime_seconds'] = round(time.time() - started, 1)
        text = report_text(receipt)
        assert_text_free_of_heldout(text, inputs['denied'], 'REPORT.md')
        (out_dir / 'REPORT.md').write_text(text, encoding='utf-8')
        receipt['artefacts'].append(dict(name='REPORT.md',
                                         bytes=(out_dir / 'REPORT.md').stat().st_size,
                                         sha256=digest(out_dir / 'REPORT.md')))
        receipt['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write_json(out_dir / 'run_receipt.json', clean(receipt))
        emit('task', 'completed', 'Pair scores written', run_id=run_id, stage='done',
             source='member_personal_relationships',
             duration_ms=int((time.time() - started) * 1000),
             metadata=dict(pairs=receipt['pair_rows'],
                           directed_rows=receipt['universe']['directed_rows']))
        print('Wrote %s pair rows to %s in %.1f s'
              % (f"{receipt['pair_rows']:,}", out_dir, receipt['runtime_seconds']))
        return 0
    except Exception as error:
        emit('task', 'failed', 'Pair scoring failed: %s' % error, run_id=run_id, stage='error',
             source='member_personal_relationships',
             duration_ms=int((time.time() - started) * 1000),
             metadata=dict(error=type(error).__name__))
        raise


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())
