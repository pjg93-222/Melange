"""Expected-rate baseline for original cosponsorship (member-relationships P1 item 7).

STATUS: EXPLORATORY. Nothing here is a validated instrument, a forecast, or a
causal statement. Every number is a descriptive count, a ratio of counts, or a
ranking summary, and every one of them is reported with its denominator.

What this module computes, and only this. For every directed pair of panel
members (signer i, sponsor j) who served in the same chamber in the same
congress, it counts how many of j's eligible bills i signed as an original
cosponsor (n_ij) out of how many of j's bills i was eligible to sign (N_ij),
fits one binomial logistic regression per chamber x congress on ordinary
compatibility and volume terms, and reports the difference between the observed
count and the count the fitted rate puts on that cell (the residual). The
residual is the work signal this lane asked for: ordinary behaviour is the
neutral reference, as it already is for speech in the expression lane.

Reuse, not reinvention. The bill universe, the "original cosponsorship"
definition and the eligibility rule are the ones already used by this lane:

    history_work.read_history()   -> the dated bill panel (congresses 116-119,
                                     read cutoff 2026-09-10), serialized at
                                     20260910_full_history/bills.ndjson, which
                                     benchmark_contract.py pins by sha256.
    chamber_work.term_on()        -> a member holds an eligible opportunity only
                                     while a single dated term covers the
                                     introduction day in the bill's chamber.
    chamber_work.temporal_features() -> the accumulation repeated here per
                                     congress: opportunities = eligible @
                                     sponsor.T, direct = original @ sponsor.T, a
                                     sponsor is never eligible for its own bill,
                                     and an original signature outside an
                                     opportunity raises rather than drops.
    data.load_members()           -> the member panel, through the frozen
                                     20260910_full_history/members.json copy.

Known gap, carried and not fixed: data.py drops Lindsey Graham (G000359) at the
cutoff because no dated term covers it, so the panel is 532 members, and one
further member has no NOMINATE first dimension in votes/HS119_members.csv. Both
are recorded in the receipt and in REPORT.md; neither is repaired here.

Held-out discipline. The 120 ``split == 'heldout'`` rows of the frozen
probability sample are read for their ``pair_id`` only, into a deny-list. Those
pairs are scored in the pair tables like every other pair of serving members --
the baseline never sees a label of any kind -- and they are refused, loudly, in
every validation table and are never named in REPORT.md.

This module writes only under
outputs/member_personal_relationships/20260911_work_baseline. It changes no
existing file, reruns no existing artefact, and feeds no engine, rank or surface.
"""
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
import argparse
import csv
import json
import sys
import time

import numpy as np

from .data import ROOT, read_json, digest
from .history_work import service_overlap
from .chamber_work import term_on
from .run_history import read_rows
from .regression import clean_json, save

STATUS = 'EXPLORATORY'
SEED = 20260911
BOOTSTRAP_COEFFICIENTS = 200
BOOTSTRAP_AUC = 1000
SHRINKAGE = 0.5
CONGRESSES = (116, 117, 118, 119)
CUTOFF = '2026-09-10'
ETA_CLIP = 30.0
RIDGE = 1e-6
MAX_ITER = 100
STEP_TOL = 1e-9
GRADIENT_TOL = 1e-6

OUTPUTS = ROOT / 'outputs/member_personal_relationships'
HISTORY = OUTPUTS / '20260910_full_history'
REGRESSION = OUTPUTS / '20260910_regression'
FROZEN = OUTPUTS / '20260910_frozen_v5'
LABELS = OUTPUTS / '20260910_probability_sample_labels'
OUT = OUTPUTS / '20260911_work_baseline'

MEMBERS_FILE = HISTORY / 'members.json'
BILLS_FILE = HISTORY / 'bills.ndjson'
CASES_FILE = REGRESSION / 'cases.json'
SAMPLE_FILE = FROZEN / 'sampled_pairs.ndjson'
LABELS_FILE = LABELS / 'labels_v1.ndjson'
NOMINATE_FILE = ROOT / 'votes/HSall_members.csv'

NOMINATE_SOURCES = {2: 'per_congress', 1: 'static_hs119_fallback', 0: 'missing_imputed_at_cell_mean'}

ARTEFACTS = ['baseline_fits.json', 'pair_work_residuals.ndjson', 'pair_work_pooled.ndjson',
             'validation.json']

# Covariate order is the report order. shared_committee is absent: COMMITTEE_SEARCH
# below records the paths searched and why the term is omitted.
COVARIATES = ['same_party', 'nominate_distance', 'nominate_distance_imputed', 'same_state',
              'log_sponsor_volume', 'signer_propensity_logit']

COMMITTEE_SEARCH = {
    'term': 'shared_committee',
    'status': 'omitted',
    'reason': ('no per-congress committee-membership table covering 116-119 was found. The rosters that do '
               'exist cover only part of the window: a current-congress-only roster, a finance-committee-only '
               'pair of 118/119 snapshots outside the repository, and a 117/118 institutional build that '
               'needs pyarrow, which this lane does not import.'),
    'paths_searched': [
        'data/staffer_network/reference/congress-legislators/750c0608efb6ef1fc3257ba72c99af3771d35088/'
        'committee-membership-current.yaml (current congress only; no 116/117/118 roster)',
        'data/staffer_network/reference/congress-legislators/750c0608efb6ef1fc3257ba72c99af3771d35088/'
        'committees-current.yaml and committees-historical.yaml (committee definitions, no member rosters)',
        '%LOCALAPPDATA%/Melange/lda_rebuild/raw/committee_snapshots/committee-membership-{118,119}-*.yaml '
        '(congresses 118 and 119 only, and fec/lobbying/member_congress_panel.py reads only the four finance '
        'committees HSBA/SSBK/HSAG/SSAF out of them)',
        'outputs/cosponsor_institutions_20260905/committees_roster_ledger.parquet and '
        'committees_{117,118}.f32 (congresses 117 and 118 only; parquet needs pyarrow, which this lane does '
        'not import)',
        'C:/melange-data/bicam_snapshot/extracted/bicam_committees/*.csv (committees, referrals, reports and '
        'subcommittees; no committee-member roster) and bicam_members/*.csv (terms, party history and '
        'leadership roles; no committee assignments)',
        'repository-wide search of fec/ and data/ for files named *committee* and for committee_membership / '
        'committee_members / committee_assignments loaders',
    ],
}

DESIGN_NOTES = {
    'outcome': ('n_ij = the number of bills sponsored by j in this chamber and congress that i signed as an '
                'original cosponsor, over the lane bill panel built by history_work.read_history() and the '
                'original-cosponsor rule chamber_work.temporal_features() applies.'),
    'exposure': ('N_ij = the number of bills sponsored by j in this chamber and congress for which i held an '
                 'eligible opportunity, i.e. a single dated term of i covered the introduction day in that '
                 'chamber and i is not the sponsor. This is the lane quantity eligible @ sponsor.T. It is '
                 'pair-specific rather than a bare count of j bills, because a member who joined the chamber '
                 'mid-congress never held the opportunity to sign the earlier ones.'),
    'likelihood': ('binomial logistic with N_ij trials, not Poisson with a log-exposure offset. The count is '
                   'bounded above by the number of eligible opportunities by construction -- chamber_work '
                   'raises on a signature outside an opportunity -- so the binomial respects a ceiling that '
                   'Poisson does not, and the fitted expectation can never exceed the exposure.'),
    'volume_term': ('log_sponsor_volume = log(1 + the number of bills j sponsored in this chamber and '
                    'congress). It is a sponsor attribute and is separate from the exposure N_ij, which is '
                    'the pair-specific opportunity count used as the binomial trials.'),
    'propensity_term': ('signer_propensity_logit = log((s + 0.5) / (o - s + 0.5)) where s and o are the '
                        'original signatures and eligible opportunities of i in this chamber and congress '
                        'over every sponsor except j, so the focal pair is left out of its own reference '
                        'rate. o counts bills by every sponsor in the chamber and congress, including '
                        'sponsors outside the 532-member panel.'),
    'ideology_and_geography': ('nominate_distance and same_state stay in the outcome model as compatibility '
                               'terms, as the P1-7 specification requires; they are not partialled out '
                               'beforehand and they are given no interpretation here.'),
    'nominate_source': ('nominate_distance = |dim1_i - dim1_j| taken from votes/HSall_members.csv at the '
                        'member\'s own congress and chamber. Where a member has no row for that congress '
                        'and chamber the static votes/HS119_members.csv value carried in members.json is '
                        'used instead, and where neither exists the distance is imputed at the within-cell '
                        'mean of the observed off-diagonal distances. Each pair row carries which of the '
                        'three applied, and the counts are in the cell record and the receipt. Where a '
                        'member holds two HSall rows in one congress and chamber -- a party switch inside '
                        'the congress -- the row with the larger nominate_number_of_votes is taken and the '
                        'resolution is counted.'),
    'shrinkage': 'shrunken_rate_ratio = (n + 0.5) / (E + 0.5); the 0.5 is fixed, not tuned.',
    'residual': ('residual = n - E, and pearson_residual = (n - E) / sqrt(E(1 - E/N)), the binomial variance '
                 'at the fitted rate. Neither is a probability, an effect, or a relationship.'),
}

STATE_VOCABULARY = {
    'measured': 'both members served in this chamber and congress and N_ij > 0.',
    'no_eligible_bills': ('both members served in this chamber and congress but N_ij = 0, so no rate is '
                          'defined; the pair is counted and left out of the fit, never scored as a zero.'),
    'cross_chamber_not_measured': ('for the consumer: the two members never served in the same chamber inside '
                                   'the coverage window, so the pair is absent from these tables by '
                                   'construction. Absence is not a low score.'),
}

PENDING_DECISIONS = [
    ('Per-congress NOMINATE, with a static fallback. The ideological distance uses nominate_dim1 from '
     'votes/HSall_members.csv at each member\'s own congress and chamber. Members with no row for that '
     'congress and chamber fall back to the static votes/HS119_members.csv value carried in members.json, '
     'and members with neither are imputed at the within-cell mean and flagged. The three counts are in '
     'every cell record, in the receipt and in the report; the earlier static-only build is superseded.'),
    ('shared_committee omitted. No per-congress committee-membership table covering 116-119 was found; the '
     'paths searched are listed in baseline_fits.json under shared_committee.paths_searched. The '
     'compatibility side of the model is therefore party, ideology and geography only.'),
    ('Known panel gap carried, not fixed. data.py drops Lindsey Graham (G000359) at the cutoff because no '
     'dated term covers it, so the panel is 532 members and every Graham pair is absent from these tables.'),
    ('The member panel is the roster of today projected backwards. Only members serving at the read cutoff '
     'are in it, so congress 116 holds 246 of the current House members against 444 distinct House sponsors '
     'in that congress. The earlier congresses are a subset of the members of today, not the chamber of the '
     'day.'),
    ('Exposure is pair-specific. N_ij counts j bills for which i held an eligible opportunity, not a bare '
     'count of j bills, so a member who arrived mid-congress is not charged for bills filed before arrival. '
     'The volume of the sponsor enters separately as log_sponsor_volume.'),
    ('Bootstrap unit. Coefficient standard errors resample undirected pairs, so the two directions of a pair '
     'move together, but they do not carry clustering by member. They are the optimistic end of the range.'),
    ('Shrinkage a = 0.5 is fixed, not tuned, and the ridge 1e-6 on standardised columns exists for '
     'conditioning only.'),
    ('The residual is offered as the work signal the review asked for. Whether it is used that way, and '
     'whether the compatibility terms belong inside the outcome model rather than beside it, is Paul\'s '
     'call.'),
]


# ----------------------------------------------------------------- small helpers

def number(value, digits=6):
    """JSON-safe float. write_json forbids NaN, so a non-finite value becomes null."""
    if value is None:
        return None
    value = float(value)
    return round(value, digits) if np.isfinite(value) else None


def pair_id_of(a, b):
    return '__'.join(sorted((a, b)))


def congress_window(congress, cutoff=CUTOFF):
    """[start, end) for a congress, with the end clamped at the day after the read cutoff.

    history_work.read_history() clamps the window of each bill the same way, so the
    member panel and the bill panel stop on the same day.
    """
    start = '%04d-01-03' % (1787 + 2 * congress)
    end = '%04d-01-03' % (1789 + 2 * congress)
    exclusive = date.fromordinal(date.fromisoformat(cutoff).toordinal() + 1).isoformat()
    return start, min(end, exclusive)


def window_label(start, end):
    return '%s..%s' % (start, end)


def term_in_window(person, chamber, start, end):
    """The term of this member in this chamber that overlaps the window the longest."""
    best, best_days = None, 0
    for term in person['terms']:
        if term['chamber'] != chamber:
            continue
        low, high = max(term['start'], start), min(term['end'], end)
        if low >= high:
            continue
        days = date.fromisoformat(high).toordinal() - date.fromisoformat(low).toordinal()
        if days > best_days:
            best, best_days = term, days
    return best


def read_bills(path):
    """Read the dated bill panel with no congress filter of any kind.

    history_work.read_history() hard-filters 116 <= congress <= 119 while it builds a
    panel from the raw source, so a wider serialized panel read back through it would
    lose the 115th silently. This reader is deliberately plain: every line of the
    ndjson becomes a row, and the census of what was read is returned with it.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError('Bill panel not found: %s' % path)
    rows = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if not rows:
        raise ValueError('Bill panel is empty: %s' % path)
    census = defaultdict(int)
    for row in rows:
        census[int(row['congress'])] += 1
    return rows, dict(sorted(census.items()))


def parse_congress_range(text):
    """"116-119" or "118" or "116,117" -> a sorted tuple of congress numbers."""
    if not isinstance(text, str):
        return tuple(sorted(int(c) for c in text))
    cleaned = text.strip()
    if '-' in cleaned:
        low, high = (part.strip() for part in cleaned.split('-', 1))
        low, high = int(low), int(high)
        if high < low:
            raise ValueError('Congress range runs backwards: %s' % text)
        return tuple(range(low, high + 1))
    return tuple(sorted(int(part) for part in cleaned.split(',') if part.strip()))


def load_deny_list(path):
    """Held-out rows give up their pair_id and nothing else; no label, weight or stratum is read."""
    denied, development = set(), 0
    for row in read_rows(Path(path)):
        if row.get('split') == 'development':
            development += 1
        else:
            denied.add(str(row.get('pair_id')))
    return frozenset(denied), development


def load_nominate(path, congresses):
    """Per-congress NOMINATE first dimension, keyed (congress, chamber, bioguide).

    A member with two rows in one congress and chamber -- a party switch inside the
    congress gives VoteView two spells -- keeps the row with the larger recorded vote
    count, ties going to the earlier row in the file. The resolutions are counted.
    """
    wanted = {int(c) for c in congresses}
    best, audit = {}, dict(source_rows=0, rows_in_window=0, usable_rows=0,
                           duplicate_member_congress_rows=0, blank_scores=0, blank_bioguide=0)
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            audit['source_rows'] += 1
            try:
                congress = int(row['congress'])
            except (TypeError, ValueError):
                continue
            if congress not in wanted or row['chamber'] not in ('House', 'Senate'):
                continue
            audit['rows_in_window'] += 1
            bioguide = (row.get('bioguide_id') or '').strip()
            if not bioguide:
                audit['blank_bioguide'] += 1
                continue
            score = (row.get('nominate_dim1') or '').strip()
            if not score:
                audit['blank_scores'] += 1
                continue
            try:
                votes = float(row.get('nominate_number_of_votes') or 0)
            except ValueError:
                votes = 0.0
            key = (congress, row['chamber'], bioguide)
            audit['usable_rows'] += 1
            if key in best:
                audit['duplicate_member_congress_rows'] += 1
                if votes <= best[key][1]:
                    continue
            best[key] = (float(score), votes)
    audit['members_scored'] = len(best)
    audit['congresses'] = sorted({k[0] for k in best})
    return {k: v[0] for k, v in best.items()}, audit


def cell_nominate(member_ids, members, scores, congress, chamber):
    """Per-member ideology for one cell: per-congress row, static fallback, or nothing."""
    resolved = {}
    for bioguide in member_ids:
        value = scores.get((int(congress), chamber, bioguide)) if scores else None
        if value is not None:
            resolved[bioguide] = dict(value=float(value), rank=2)
            continue
        static = members[bioguide].get('d1')
        resolved[bioguide] = (dict(value=float(static), rank=1) if static is not None
                              else dict(value=None, rank=0))
    return resolved


def assert_no_heldout(pair_ids, denied, label):
    """Refuse any sealed dyad in a validation table. Raises; never filters silently."""
    hits = sorted(p for p in set(pair_ids) if p in denied)
    if hits:
        raise ValueError('Held-out dyads refused in %s: %d dyad(s)' % (label, len(hits)))
    return len(set(pair_ids))


# --------------------------------------------------------------------- the fit

def sigmoid(eta):
    out = np.empty_like(np.asarray(eta, dtype=float))
    eta = np.asarray(eta, dtype=float)
    positive = eta >= 0
    out[positive] = 1.0 / (1.0 + np.exp(-eta[positive]))
    exponent = np.exp(eta[~positive])
    out[~positive] = exponent / (1.0 + exponent)
    return out


def binomial_deviance(y, trials, mu):
    """Twice the saturated log-likelihood difference, with 0 log 0 read as 0."""
    with np.errstate(divide='ignore', invalid='ignore'):
        first = np.where(y > 0, y * np.log(np.where(y > 0, y / np.maximum(mu, 1e-300), 1.0)), 0.0)
        rest = trials - y
        second = np.where(rest > 0,
                          rest * np.log(np.where(rest > 0, rest / np.maximum(trials - mu, 1e-300), 1.0)),
                          0.0)
    return float(2.0 * np.sum(first + second))


def irls_binomial(X, y, trials, ridge=RIDGE, max_iter=MAX_ITER):
    """Newton / IRLS for a binomial logit with per-row trials. The intercept is unpenalised.

    The ridge is for conditioning only: 1e-6 on standardised columns, orders of
    magnitude below the curvature any real cell carries. It is reported in the fit
    record so it is never an invisible choice.
    """
    columns = X.shape[1]
    beta = np.zeros(columns)
    rate = (float(np.sum(y)) + 0.5) / (float(np.sum(trials)) + 1.0)
    beta[0] = np.log(rate / (1.0 - rate))
    penalty = np.full(columns, float(ridge))
    penalty[0] = 0.0
    deviance = binomial_deviance(y, trials, trials * sigmoid(np.clip(X @ beta, -ETA_CLIP, ETA_CLIP)))
    converged, iterations = False, 0
    max_step, max_gradient, status = float('nan'), float('nan'), 'ok'
    for iterations in range(1, max_iter + 1):
        eta = np.clip(X @ beta, -ETA_CLIP, ETA_CLIP)
        probability = sigmoid(eta)
        mu = trials * probability
        weights = trials * probability * (1.0 - probability)
        gradient = X.T @ (y - mu) - penalty * beta
        hessian = (X * weights[:, None]).T @ X + np.diag(penalty)
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            status = 'singular_hessian'
            break
        scale, candidate, candidate_deviance = 1.0, beta, deviance
        for _ in range(7):
            candidate = beta + scale * step
            candidate_deviance = binomial_deviance(
                y, trials, trials * sigmoid(np.clip(X @ candidate, -ETA_CLIP, ETA_CLIP)))
            if np.isfinite(candidate_deviance) and candidate_deviance <= deviance + 1e-8:
                break
            scale /= 2.0
        beta, deviance = candidate, candidate_deviance
        max_step = float(np.max(np.abs(scale * step)))
        max_gradient = float(np.max(np.abs(gradient)))
        if max_step < STEP_TOL and max_gradient < GRADIENT_TOL:
            converged = True
            break
    return dict(beta=beta, converged=bool(converged), iterations=int(iterations), max_step=max_step,
                max_gradient=max_gradient, deviance=float(deviance), status=status)


def standardise(X):
    """Centre and scale the non-intercept columns; drop any column with no variation.

    A constant column inside a cell -- every pair in a different state, say -- would
    make the Hessian singular. Dropping it is recorded, never silent.
    """
    keep, means, scales = [], [], []
    for index in range(X.shape[1]):
        column = X[:, index]
        scale = float(np.std(column))
        if scale <= 1e-12:
            continue
        keep.append(index)
        means.append(float(np.mean(column)))
        scales.append(scale)
    if not keep:
        return np.ones((X.shape[0], 1)), [], np.array([]), np.array([])
    means, scales = np.array(means), np.array(scales)
    design = np.column_stack([np.ones(X.shape[0]), (X[:, keep] - means) / scales])
    return design, keep, means, scales


def back_transform(beta, means, scales, kept, total_columns):
    """Standardised coefficients to the natural scale; dropped columns stay None."""
    natural = [None] * total_columns
    intercept = float(beta[0])
    for position, index in enumerate(kept):
        coefficient = float(beta[position + 1]) / scales[position]
        natural[index] = coefficient
        intercept -= coefficient * means[position]
    return intercept, natural


def fitted_counts(X, trials, intercept, coefficients):
    """E = N * sigmoid(eta). Bounded above by N by construction."""
    eta = np.full(X.shape[0], float(intercept))
    for index, coefficient in enumerate(coefficients):
        if coefficient is not None:
            eta = eta + coefficient * X[:, index]
    return trials * sigmoid(np.clip(eta, -ETA_CLIP, ETA_CLIP))


def fit_binomial(X, y, trials, ridge=RIDGE, max_iter=MAX_ITER):
    """Fit on standardised columns, report on the natural scale."""
    design, kept, means, scales = standardise(X)
    result = irls_binomial(design, y, trials, ridge=ridge, max_iter=max_iter)
    intercept, natural = back_transform(result['beta'], means, scales, kept, X.shape[1])
    result['intercept'] = intercept
    result['coefficients'] = natural
    result['kept_columns'] = list(kept)
    result['fitted'] = fitted_counts(X, trials, intercept, natural)
    return result


def pair_groups(signer_index, sponsor_index):
    """Row indices grouped by undirected pair, at most two rows each (i->j and j->i)."""
    signer_index = np.asarray(signer_index, dtype=np.int64)
    sponsor_index = np.asarray(sponsor_index, dtype=np.int64)
    if len(signer_index) == 0:
        return np.zeros((0, 2), dtype=np.int64)
    low = np.minimum(signer_index, sponsor_index)
    high = np.maximum(signer_index, sponsor_index)
    key = low * (int(high.max()) + 2) + high
    order = np.argsort(key, kind='stable')
    ordered = key[order]
    starts = np.flatnonzero(np.concatenate(([True], ordered[1:] != ordered[:-1])))
    counts = np.diff(np.concatenate((starts, [len(ordered)])))
    if counts.max() > 2:
        raise ValueError('An undirected pair carried more than two directed rows')
    table = np.full((len(starts), 2), -1, dtype=np.int64)
    table[:, 0] = order[starts]
    two = counts == 2
    table[two, 1] = order[starts[two] + 1]
    return table


def bootstrap_coefficients(X, y, trials, groups, draws, seed, ridge=RIDGE):
    """Resample undirected pairs with replacement and refit; the SE is the spread of the refits.

    The resampling unit is the undirected pair, so the two directions of a pair move
    together. It does not carry clustering by member, so these standard errors are the
    optimistic end of the range.
    """
    empty = dict(se=None, p2_5=None, p97_5=None, draws=0)
    if draws <= 0 or len(groups) == 0:
        return [dict(empty) for _ in range(X.shape[1])], dict(empty), 0, 0
    generator = np.random.default_rng(seed)
    total = len(groups)
    intercepts, rows, failures = [], [], 0
    for _ in range(int(draws)):
        chosen = groups[generator.integers(0, total, total)].ravel()
        chosen = chosen[chosen >= 0]
        try:
            result = fit_binomial(X[chosen], y[chosen], trials[chosen], ridge=ridge)
        except (np.linalg.LinAlgError, ValueError):
            failures += 1
            continue
        if not result['converged']:
            failures += 1
        intercepts.append(result['intercept'])
        rows.append([np.nan if c is None else c for c in result['coefficients']])
    if not rows:
        return [dict(empty) for _ in range(X.shape[1])], dict(empty), 0, int(failures)
    matrix = np.array(rows, dtype=float)

    def spread(values):
        values = values[np.isfinite(values)]
        if len(values) <= 2:
            return dict(se=None, p2_5=None, p97_5=None, draws=int(len(values)))
        # The percentiles are reported beside the standard deviation because a
        # near-separated resample -- one same-state Senate dyad dropping out, say --
        # can throw a single refit to a huge value and the standard deviation with it.
        return dict(se=float(np.std(values, ddof=1)), p2_5=float(np.percentile(values, 2.5)),
                    p97_5=float(np.percentile(values, 97.5)), draws=int(len(values)))

    errors = [spread(matrix[:, index]) for index in range(matrix.shape[1])]
    intercept_error = spread(np.array(intercepts, dtype=float))
    return errors, intercept_error, len(rows), int(failures)


# ------------------------------------------------------------- counting a cell

def serving_vectors(member_ids, members, chamber):
    """Cache of "is this member serving in this chamber on this day", one vector per day.

    term_on() is the rule of chamber_work: exactly one dated term must cover the day.
    Bills share introduction days in the hundreds, so the cache turns a
    members x bills scan into a members x days one.
    """
    cache = {}

    def vector(day):
        found = cache.get(day)
        if found is None:
            found = np.array([1.0 if (term_on(members[a], day) or {}).get('chamber') == chamber else 0.0
                              for a in member_ids])
            cache[day] = found
        return found
    return vector, cache


def cell_counts(member_ids, members, bills, chamber):
    """Directed counts for one chamber x congress cell.

    direct[i, j]        original signatures by i on bills sponsored by j
    opportunities[i, j] eligible opportunities of i on bills sponsored by j
    signatures[i]       original signatures by i over every sponsor in the cell
    exposures[i]        eligible opportunities of i over every sponsor in the cell
    sponsor_bills[j]    bills sponsored by j in the cell

    signatures and exposures count bills by sponsors outside the panel as well, so the
    leave-pair-out propensity of a signer is taken over every other sponsor, not only
    the ones inside the panel.
    """
    index = {a: i for i, a in enumerate(member_ids)}
    size = len(member_ids)
    direct = np.zeros((size, size))
    opportunities = np.zeros((size, size))
    signatures = np.zeros(size)
    exposures = np.zeros(size)
    sponsor_bills = np.zeros(size)
    vector, cache = serving_vectors(member_ids, members, chamber)
    for bill in bills:
        serving = vector(bill['introduced'])
        sponsor = index.get(bill['sponsor'])
        if not set(bill['original']).issubset(set(bill['joins'])):
            raise ValueError('Original signature missing valid provenance')
        eligible = serving
        if sponsor is not None:
            eligible = serving.copy()
            eligible[sponsor] = 0.0
            sponsor_bills[sponsor] += 1
            opportunities[:, sponsor] += eligible
        exposures += eligible
        for signer in bill['original']:
            position = index.get(signer)
            if position is None or signer == bill['sponsor'] or not serving[position]:
                continue
            signatures[position] += 1
            if sponsor is not None:
                direct[position, sponsor] += 1
    if np.any(direct > opportunities):
        raise ValueError('Original cosponsor outside opportunity')
    if np.any(signatures > exposures):
        raise ValueError('Signer signatures exceed signer opportunities')
    return dict(direct=direct, opportunities=opportunities, signatures=signatures,
                exposures=exposures, sponsor_bills=sponsor_bills, days_cached=len(cache))


def cell_design(member_ids, members, counts, chamber, start, end, nominate=None):
    """Covariate matrices over the directed pairs of one cell.

    ``nominate`` is the per-member mapping cell_nominate() returns. Without it the
    static members.json score stands in, which is the pre-HSall behaviour.
    """
    size = len(member_ids)
    terms = [term_in_window(members[a], chamber, start, end) for a in member_ids]
    party = np.array([(t or {}).get('party', 'Unknown') for t in terms], dtype=object)
    state = np.array([(t or {}).get('state', 'Unknown') for t in terms], dtype=object)
    if nominate is None:
        nominate = {a: (dict(value=float(members[a]['d1']), rank=1)
                        if members[a].get('d1') is not None else dict(value=None, rank=0))
                    for a in member_ids}
    scores = np.array([np.nan if nominate[a]['value'] is None else nominate[a]['value']
                       for a in member_ids], dtype=float)
    ranks = np.array([nominate[a]['rank'] for a in member_ids], dtype=int)
    off_diagonal = ~np.eye(size, dtype=bool)

    same_party = (party[:, None] == party[None, :]).astype(float)
    same_state = (state[:, None] == state[None, :]).astype(float)
    distance = np.abs(scores[:, None] - scores[None, :])
    missing = ~np.isfinite(distance)
    observed = distance[(~missing) & off_diagonal]
    fill = float(observed.mean()) if observed.size else 0.0
    distance = np.where(missing, fill, distance)
    pair_rank = np.minimum(ranks[:, None], ranks[None, :])

    volume = np.log1p(counts['sponsor_bills'])[None, :] * np.ones((size, 1))
    other_signatures = counts['signatures'][:, None] - counts['direct']
    other_exposures = counts['exposures'][:, None] - counts['opportunities']
    propensity_logit = np.log((other_signatures + 0.5)
                              / (np.maximum(other_exposures - other_signatures, 0.0) + 0.5))
    with np.errstate(divide='ignore', invalid='ignore'):
        propensity_rate = np.where(other_exposures > 0,
                                   other_signatures / np.maximum(other_exposures, 1e-12), np.nan)

    columns = dict(same_party=same_party, nominate_distance=distance,
                   nominate_distance_imputed=missing.astype(float), same_state=same_state,
                   log_sponsor_volume=volume, signer_propensity_logit=propensity_logit)
    return dict(columns=columns, off_diagonal=off_diagonal, propensity_rate=propensity_rate,
                nominate_fill=fill, imputed_pairs=int(np.sum(missing & off_diagonal)),
                nominate_pair_rank=pair_rank,
                nominate_members={name: int(np.sum(ranks == rank))
                                  for rank, name in NOMINATE_SOURCES.items()},
                nominate_pairs={name: int(np.sum((pair_rank == rank) & off_diagonal))
                                for rank, name in NOMINATE_SOURCES.items()})


# ------------------------------------------------------------------ validation

def auc_from_scores(positive, negative):
    """Wins over all positive x negative comparisons; a tie counts a half."""
    positive = np.asarray(positive, dtype=float)
    negative = np.asarray(negative, dtype=float)
    comparisons = int(len(positive) * len(negative))
    if comparisons == 0:
        return None, 0, 0.0
    difference = positive[:, None] - negative[None, :]
    wins = float(np.sum(difference > 0) + 0.5 * np.sum(difference == 0))
    return wins / comparisons, comparisons, wins


def auc_bootstrap_interval(positive, negative, draws, seed):
    """Percentile interval over dyad resamples, drawn inside each class so neither empties."""
    positive = np.asarray(positive, dtype=float)
    negative = np.asarray(negative, dtype=float)
    if len(positive) == 0 or len(negative) == 0 or draws <= 0:
        return None, None, 0
    generator = np.random.default_rng(seed)
    values = []
    for _ in range(int(draws)):
        drawn_positive = positive[generator.integers(0, len(positive), len(positive))]
        drawn_negative = negative[generator.integers(0, len(negative), len(negative))]
        value, _, _ = auc_from_scores(drawn_positive, drawn_negative)
        values.append(value)
    values = np.array(values, dtype=float)
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5)), len(values)


def average_ranks(values):
    values = np.asarray(values, dtype=float)
    order = np.argsort(values, kind='stable')
    ranks = np.empty(len(values), dtype=float)
    position = 0
    while position < len(values):
        end = position + 1
        while end < len(values) and values[order[end]] == values[order[position]]:
            end += 1
        ranks[order[position:end]] = 0.5 * (position + end - 1) + 1.0
        position = end
    return ranks


def spearman(x, y):
    """Rank correlation with average ranks for ties. Descriptive only."""
    if len(x) < 3:
        return None
    rx, ry = average_ranks(x), average_ranks(y)
    sx, sy = float(np.std(rx)), float(np.std(ry))
    if sx <= 1e-12 or sy <= 1e-12:
        return None
    return float(np.mean((rx - np.mean(rx)) * (ry - np.mean(ry))) / (sx * sy))


def co_served_same_chamber(a, b, congresses, cutoff):
    """Did the two members ever share a chamber inside the coverage window?"""
    for congress in congresses:
        start, end = congress_window(congress, cutoff)
        for chamber in ('House', 'Senate'):
            if service_overlap(a, start, end, chamber) and service_overlap(b, start, end, chamber):
                return True
    return False


def validate(pooled, cases, labels, members, denied, congresses, cutoff, auc_draws):
    """Two diagnostics, both descriptive, neither a training target.

    Nothing in the fit ever saw a label, so these are read-outs of a fixed score on
    reviewed dyads, not a tuned result.
    """
    def dyad_state(a, b):
        if a not in members or b not in members:
            return 'member_outside_panel'
        if not co_served_same_chamber(members[a], members[b], congresses, cutoff):
            return 'cross_chamber_not_measured'
        return 'no_eligible_bills'

    rows = []
    for case in cases:
        a, b = case['pair']
        entry = pooled.get(pair_id_of(a, b))
        rows.append(dict(
            pair_id=pair_id_of(a, b), y=int(case['y']), sign=case['sign'],
            state='measured' if entry else dyad_state(a, b),
            original_cosponsorships=int(entry['n']) if entry else None,
            eligible_opportunities=int(entry['N']) if entry else None,
            expected=number(entry['expected']) if entry else None,
            congresses=sorted(int(c) for c in entry['by_congress']) if entry else [],
            shrunken_rate_ratio=number((entry['n'] + SHRINKAGE) / (entry['expected'] + SHRINKAGE))
            if entry else None,
            raw_rate=number(entry['n'] / entry['N'], 8) if entry and entry['N'] else None))
    assert_no_heldout([r['pair_id'] for r in rows], denied, 'sign_benchmark_validation')

    measurable = [r for r in rows if r['state'] == 'measured']
    unmeasurable = [r for r in rows if r['state'] != 'measured']
    benchmark = dict(dyads=len(rows), positive=sum(r['y'] for r in rows),
                     negative=sum(1 - r['y'] for r in rows),
                     measurable=len(measurable), unmeasurable=len(unmeasurable),
                     unmeasurable_states={state: sum(1 for r in unmeasurable if r['state'] == state)
                                          for state in sorted({r['state'] for r in unmeasurable})},
                     scores={}, rows=rows)
    for score_name in ('shrunken_rate_ratio', 'raw_rate'):
        values = [r[score_name] for r in measurable]
        mean = float(np.mean(values)) if values else 0.0
        block = {}
        variants = (
            ('mean_imputed', [dict(y=r['y'], score=r[score_name]) for r in measurable]
             + [dict(y=r['y'], score=mean) for r in unmeasurable]),
            ('dropped', [dict(y=r['y'], score=r[score_name]) for r in measurable]),
        )
        for variant, subset in variants:
            positive = [r['score'] for r in subset if r['y'] == 1]
            negative = [r['score'] for r in subset if r['y'] == 0]
            value, comparisons, wins = auc_from_scores(positive, negative)
            low, high, draws_used = auc_bootstrap_interval(
                positive, negative, auc_draws, SEED + (0 if variant == 'mean_imputed' else 1))
            block[variant] = dict(
                auc=number(value, 6), wins=number(wins, 1), comparisons=comparisons, dyads=len(subset),
                positive=len(positive), negative=len(negative), bootstrap_draws=int(draws_used),
                ci_low=number(low, 6), ci_high=number(high, 6),
                unmeasurable_handling=('unmeasurable dyads take the mean score of the measurable dyads, %s'
                                       % number(mean, 6)) if variant == 'mean_imputed'
                else 'unmeasurable dyads dropped')
        benchmark['scores'][score_name] = block

    graded_rows = []
    for row in labels:
        if row.get('label_status') != 'two_blind_model_passes_merged' or row.get('split') != 'development':
            continue
        degrees = []
        for direction in ('a_to_b', 'b_to_a'):
            affinity = row['directions'][direction]['affinity']
            value = affinity.get('value')
            if isinstance(value, bool) or not isinstance(value, int):
                continue
            if affinity.get('merge_rule') != 'exact':
                continue
            degrees.append(int(value))
        entry = pooled.get(row['pair_id'])
        graded_rows.append(dict(
            pair_id=row['pair_id'], degree=max(degrees) if degrees else None,
            agreed_assessable=bool(degrees), state='measured' if entry else 'not_in_pair_table',
            residual=number(entry['n'] - entry['expected']) if entry else None,
            original_cosponsorships=int(entry['n']) if entry else None,
            eligible_opportunities=int(entry['N']) if entry else None))
    assert_no_heldout([r['pair_id'] for r in graded_rows], denied, 'development_graded_validation')

    with_degree = [r for r in graded_rows if r['agreed_assessable'] and r['state'] == 'measured']
    present = [r for r in graded_rows if r['state'] == 'measured']
    graded = dict(
        two_pass_merged_rows=len(graded_rows),
        with_agreed_assessable_affinity=sum(1 for r in graded_rows if r['agreed_assessable']),
        measured_in_pair_table=len(present),
        degree_distribution={str(d): sum(1 for r in with_degree if r['degree'] == d)
                             for d in sorted({r['degree'] for r in with_degree})},
        primary=dict(
            definition=('Spearman of the pooled residual against the agreed affinity degree, over the '
                        'two-pass merged development rows whose affinity degree is assessable in either '
                        'direction and identical in both passes.'),
            n=len(with_degree),
            spearman=number(spearman([r['residual'] for r in with_degree],
                                     [r['degree'] for r in with_degree]), 6)),
        secondary=dict(
            definition=('Spearman of the pooled residual against an indicator that the row carried any '
                        'agreed assessable affinity degree, over every two-pass merged development row '
                        'present in the pair table. Reported because the degree scale above is almost '
                        'constant.'),
            n=len(present), positive=sum(1 for r in present if r['agreed_assessable']),
            spearman=number(spearman([r['residual'] for r in present],
                                     [1.0 if r['agreed_assessable'] else 0.0 for r in present]), 6)),
        rows=graded_rows)
    return dict(status=STATUS,
                note=('Diagnostic only. The baseline fit is estimated without any label, so neither table is '
                      'a training target and neither is an accuracy estimate for any population.'),
                sign_benchmark=benchmark, development_graded=graded)


# ----------------------------------------------------------------------- build

def build(out_dir, *, members_path=None, bills_path=None, cases_path=None, sample_path=None,
          labels_path=None, nominate_path=None, bootstrap=BOOTSTRAP_COEFFICIENTS,
          auc_draws=BOOTSTRAP_AUC, congresses=CONGRESSES, cutoff=CUTOFF, stage=None, progress=print):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stage = stage or (lambda *a, **k: None)
    started = time.time()

    members_path = Path(members_path or MEMBERS_FILE)
    bills_path = Path(bills_path or BILLS_FILE)
    cases_path = Path(cases_path or CASES_FILE)
    sample_path = Path(sample_path or SAMPLE_FILE)
    labels_path = Path(labels_path or LABELS_FILE)
    nominate_path = Path(nominate_path or NOMINATE_FILE)
    inputs = {name: dict(path=str(path), sha256=digest(path))
              for name, path in (('members.json', members_path), ('bills.ndjson', bills_path),
                                 ('cases.json', cases_path), ('sampled_pairs.ndjson', sample_path),
                                 ('labels_v1.ndjson', labels_path),
                                 ('HSall_members.csv', nominate_path))}

    congresses = parse_congress_range(congresses)
    members = read_json(members_path)
    nominate_scores, nominate_audit = load_nominate(nominate_path, congresses)
    bills, bill_census = read_bills(bills_path)
    cases = read_json(cases_path)
    denied, development_rows = load_deny_list(sample_path)
    labels = read_rows(labels_path)
    covered = [b for b in bills if b['congress'] in set(congresses)]
    # A requested congress with no bill in the panel would otherwise pass as an empty
    # cell. It is a loading fault -- the 115th read back through a 116-119 filter, for
    # instance -- and it stops the run.
    empty = [c for c in congresses if not bill_census.get(int(c))]
    if empty:
        raise ValueError('Requested congresses carry no bills in %s: %s (panel census %s)'
                         % (bills_path, ', '.join(str(c) for c in empty), bill_census))
    coverage = dict(bill_records=len(bills), bills_in_covered_congresses=len(covered),
                    congress_range='%d-%d' % (min(congresses), max(congresses)),
                    requested_congresses=list(congresses),
                    congresses=sorted({b['congress'] for b in covered}),
                    bills_by_congress_in_source=bill_census,
                    bill_source=str(bills_path), bill_source_sha256=inputs['bills.ndjson']['sha256'],
                    first_introduced=min((b['introduced'] for b in covered), default=None),
                    last_introduced=max((b['introduced'] for b in covered), default=None),
                    read_cutoff=cutoff, members_in_panel=len(members))
    stage('inputs', '%d bills, %d panel members, %d benchmark dyads, %d held-out dyads denied, '
                    '%d per-congress NOMINATE rows'
          % (len(covered), len(members), len(cases), len(denied), nominate_audit['members_scored']))

    by_cell = defaultdict(list)
    for bill in covered:
        by_cell[(bill['congress'], bill['chamber'])].append(bill)
    for rows in by_cell.values():
        rows.sort(key=lambda b: (b['introduced'], b['key']))

    cell_records, pooled, cell_seconds = [], {}, {}
    totals = dict(directed_pairs=0, measured=0, no_eligible_bills=0,
                  original_cosponsorships=0, eligible_opportunities=0)
    fitted_cells = 0
    residual_path = out_dir / 'pair_work_residuals.ndjson'
    with residual_path.open('w', encoding='utf-8', newline='\n') as stream:
        for congress in sorted(congresses):
            start, end = congress_window(congress, cutoff)
            window = window_label(start, end)
            for chamber_position, chamber in enumerate(('House', 'Senate')):
                member_ids = sorted(a for a, person in members.items()
                                    if service_overlap(person, start, end, chamber))
                cell_bills = by_cell.get((congress, chamber), [])
                if len(member_ids) < 2 or not cell_bills:
                    cell_records.append(dict(congress=congress, chamber=chamber, window=window,
                                             serving_members=len(member_ids), bills=len(cell_bills),
                                             fit_status='not_fitted_empty_cell'))
                    continue
                counts = cell_counts(member_ids, members, cell_bills, chamber)
                design = cell_design(member_ids, members, counts, chamber, start, end,
                                     nominate=cell_nominate(member_ids, members, nominate_scores,
                                                            congress, chamber))
                mask = design['off_diagonal'] & (counts['opportunities'] > 0)
                pairs_in_cell = int(np.sum(design['off_diagonal']))
                measured = int(np.sum(mask))
                signer_index, sponsor_index = np.nonzero(mask)
                trials = counts['opportunities'][mask]
                observed = counts['direct'][mask]
                X = np.column_stack([design['columns'][name][mask] for name in COVARIATES])

                record = dict(congress=congress, chamber=chamber, window=window,
                              serving_members=len(member_ids), bills=len(cell_bills),
                              panel_sponsors=int(np.sum(counts['sponsor_bills'] > 0)),
                              directed_pairs_in_cell=pairs_in_cell, fitted_pairs=measured,
                              no_eligible_bills_pairs=pairs_in_cell - measured,
                              original_cosponsorships=int(observed.sum()),
                              eligible_opportunities=int(trials.sum()),
                              base_rate=number(observed.sum() / trials.sum(), 8) if trials.sum() else None,
                              nominate_imputed_pairs=design['imputed_pairs'],
                              nominate_fill_value=number(design['nominate_fill']),
                              nominate_members=design['nominate_members'],
                              nominate_pairs=design['nominate_pairs'],
                              days_cached=counts['days_cached'])
                totals['directed_pairs'] += pairs_in_cell
                totals['no_eligible_bills'] += pairs_in_cell - measured
                if measured < 3:
                    record['fit_status'] = 'not_fitted_too_few_pairs'
                    cell_records.append(record)
                    continue

                fit_started = time.time()
                result = fit_binomial(X, observed, trials)
                groups = pair_groups(signer_index, sponsor_index)
                seed = SEED + congress * 10 + chamber_position
                errors, intercept_error, draws_used, failures = bootstrap_coefficients(
                    X, observed, trials, groups, bootstrap, seed)
                expected = result['fitted']
                if np.any(expected > trials + 1e-9):
                    raise ValueError('A fitted expectation exceeded its exposure')
                variance = expected * (1.0 - expected / np.maximum(trials, 1e-12))
                residual = observed - expected
                with np.errstate(divide='ignore', invalid='ignore'):
                    pearson = np.where(variance > 0, residual / np.sqrt(np.maximum(variance, 1e-300)), np.nan)
                ratio = (observed + SHRINKAGE) / (expected + SHRINKAGE)

                record.update(
                    fit_status='fitted', converged=result['converged'], iterations=result['iterations'],
                    max_newton_step=number(result['max_step'], 12),
                    max_gradient=number(result['max_gradient'], 12), solver_status=result['status'],
                    deviance=number(result['deviance'], 4), ridge=RIDGE,
                    undirected_pairs_resampled=int(len(groups)),
                    bootstrap=dict(draws_requested=int(bootstrap), draws_used=int(draws_used),
                                   non_converged_or_failed=int(failures), seed=int(seed),
                                   unit='undirected pair (both directions move together)'),
                    columns=[dict(name='intercept', coefficient=number(result['intercept'], 8),
                                  bootstrap_se=number(intercept_error['se'], 8),
                                  bootstrap_p2_5=number(intercept_error['p2_5'], 8),
                                  bootstrap_p97_5=number(intercept_error['p97_5'], 8),
                                  bootstrap_draws=intercept_error['draws'], dropped=False)]
                    + [dict(name=name, coefficient=number(result['coefficients'][position], 8),
                            bootstrap_se=number(errors[position]['se'], 8),
                            bootstrap_p2_5=number(errors[position]['p2_5'], 8),
                            bootstrap_p97_5=number(errors[position]['p97_5'], 8),
                            bootstrap_draws=errors[position]['draws'],
                            dropped=result['coefficients'][position] is None,
                            mean=number(float(np.mean(X[:, position])), 6),
                            sd=number(float(np.std(X[:, position])), 6))
                       for position, name in enumerate(COVARIATES)])
                # Wall time stays out of the data artefact so two runs stay byte-identical;
                # it is carried in the receipt instead.
                cell_seconds['%d|%s' % (congress, chamber)] = round(time.time() - fit_started, 2)
                cell_records.append(record)
                fitted_cells += 1

                same_party_at = COVARIATES.index('same_party')
                distance_at = COVARIATES.index('nominate_distance')
                imputed_at = COVARIATES.index('nominate_distance_imputed')
                same_state_at = COVARIATES.index('same_state')
                for position in range(measured):
                    signer = member_ids[signer_index[position]]
                    sponsor = member_ids[sponsor_index[position]]
                    key = pair_id_of(signer, sponsor)
                    row = dict(
                        congress=congress, chamber=chamber, window=window, pair_id=key,
                        signer=signer, sponsor=sponsor,
                        original_cosponsorships=int(observed[position]),
                        eligible_opportunities=int(trials[position]),
                        expected=number(expected[position]), residual=number(residual[position]),
                        variance=number(variance[position]), pearson_residual=number(pearson[position]),
                        shrunken_rate_ratio=number(ratio[position]),
                        same_party=bool(X[position, same_party_at]),
                        nominate_distance=number(X[position, distance_at], 4),
                        nominate_distance_imputed=bool(X[position, imputed_at]),
                        nominate_source=NOMINATE_SOURCES[int(
                            design['nominate_pair_rank'][signer_index[position], sponsor_index[position]])],
                        same_state=bool(X[position, same_state_at]),
                        sponsor_bills_in_window=int(counts['sponsor_bills'][sponsor_index[position]]),
                        signer_propensity_excluding_sponsor=number(
                            design['propensity_rate'][signer_index[position], sponsor_index[position]], 8),
                        shrinkage=SHRINKAGE, state='measured')
                    stream.write(json.dumps(clean_json(row), ensure_ascii=False, allow_nan=False) + '\n')

                    entry = pooled.get(key)
                    if entry is None:
                        entry = pooled[key] = dict(members=sorted((signer, sponsor)), by_congress={},
                                                   n=0.0, N=0.0, expected=0.0, variance=0.0, directions=0)
                    entry['n'] += float(observed[position])
                    entry['N'] += float(trials[position])
                    entry['expected'] += float(expected[position])
                    entry['variance'] += float(variance[position])
                    entry['directions'] += 1
                    slot = entry['by_congress'].setdefault(
                        str(congress), dict(chambers=[], window=window, n=0.0, N=0.0, expected=0.0,
                                            variance=0.0, directions=0))
                    if chamber not in slot['chambers']:
                        slot['chambers'].append(chamber)
                    slot['n'] += float(observed[position])
                    slot['N'] += float(trials[position])
                    slot['expected'] += float(expected[position])
                    slot['variance'] += float(variance[position])
                    slot['directions'] += 1

                totals['measured'] += measured
                totals['original_cosponsorships'] += int(observed.sum())
                totals['eligible_opportunities'] += int(trials.sum())
                stage('cell', '%d %s: %d of %d directed pairs measured, %d original signatures over %d '
                              'opportunities' % (congress, chamber, measured, pairs_in_cell,
                                                 int(observed.sum()), int(trials.sum())),
                      congress=congress, chamber=chamber, converged=result['converged'])
                progress('%s %d: %s of %s directed pairs measured, %s original signatures over %s '
                         'opportunities, converged=%s in %d iterations'
                         % (chamber, congress, f'{measured:,}', f'{pairs_in_cell:,}',
                            f'{int(observed.sum()):,}', f'{int(trials.sum()):,}',
                            result['converged'], result['iterations']), flush=True)

    pooled_path = out_dir / 'pair_work_pooled.ndjson'
    with pooled_path.open('w', encoding='utf-8', newline='\n') as stream:
        for key in sorted(pooled):
            entry = pooled[key]
            row = dict(
                pair_id=key, members=entry['members'],
                congresses=sorted(int(c) for c in entry['by_congress']),
                chambers=sorted({c for slot in entry['by_congress'].values() for c in slot['chambers']}),
                directed_rows=entry['directions'],
                original_cosponsorships=int(entry['n']), eligible_opportunities=int(entry['N']),
                expected=number(entry['expected']), residual=number(entry['n'] - entry['expected']),
                variance=number(entry['variance']),
                pearson_residual=number((entry['n'] - entry['expected']) / np.sqrt(entry['variance']))
                if entry['variance'] > 0 else None,
                shrunken_rate_ratio=number((entry['n'] + SHRINKAGE) / (entry['expected'] + SHRINKAGE)),
                observed_rate=number(entry['n'] / entry['N'], 8) if entry['N'] else None,
                expected_rate=number(entry['expected'] / entry['N'], 8) if entry['N'] else None,
                shrinkage=SHRINKAGE, state='measured',
                by_congress={congress: dict(
                    chambers=slot['chambers'], window=slot['window'], directed_rows=slot['directions'],
                    original_cosponsorships=int(slot['n']), eligible_opportunities=int(slot['N']),
                    expected=number(slot['expected']), residual=number(slot['n'] - slot['expected']),
                    shrunken_rate_ratio=number((slot['n'] + SHRINKAGE) / (slot['expected'] + SHRINKAGE)))
                    for congress, slot in sorted(entry['by_congress'].items())})
            stream.write(json.dumps(clean_json(row), ensure_ascii=False, allow_nan=False) + '\n')

    stage('pairs', '%d measured directed rows, %d undirected pooled pairs'
          % (totals['measured'], len(pooled)))

    for record in cell_records:
        for source, count in (record.get('nominate_pairs') or {}).items():
            totals['nominate_' + source] = totals.get('nominate_' + source, 0) + count

    save(out_dir / 'baseline_fits.json', dict(
        status=STATUS, seed=SEED, shrinkage=SHRINKAGE, covariates=COVARIATES, design=DESIGN_NOTES,
        shared_committee=COMMITTEE_SEARCH, state_vocabulary=STATE_VOCABULARY, coverage=coverage,
        nominate=dict(source=str(nominate_path), **nominate_audit), totals=totals, cells=cell_records))

    validation = validate(pooled, cases, labels, members, denied, congresses, cutoff, auc_draws)
    save(out_dir / 'validation.json', validation)
    stage('validation', 'sign benchmark on %d dyads, %d measurable'
          % (validation['sign_benchmark']['dyads'], validation['sign_benchmark']['measurable']))

    return dict(
        status=STATUS, seed=SEED, inputs=inputs, coverage=coverage, totals=totals,
        cells_fitted=fitted_cells, cell_wall_seconds=cell_seconds, undirected_pairs=len(pooled),
        bootstrap_coefficient_draws=int(bootstrap), bootstrap_auc_draws=int(auc_draws),
        held_out_dyads_denied=len(denied), development_sample_rows=development_rows,
        held_out_split_touched=False,
        held_out_note=('held-out rows of the frozen probability sample are read for their pair_id only, into '
                       'a deny-list; they are scored in the pair tables like every other pair of serving '
                       'members and are refused in every validation table'),
        validation=validation, shared_committee=COMMITTEE_SEARCH, nominate=dict(
            source=str(nominate_path), **nominate_audit),
        pending_decisions=list(PENDING_DECISIONS),
        python=sys.version, numpy=np.__version__, code_sha256=digest(__file__),
        build_seconds=round(time.time() - started, 1))


# ---------------------------------------------------------------------- report

def report_text(receipt):
    validation = receipt['validation']
    benchmark = validation['sign_benchmark']
    graded = validation['development_graded']
    coverage = receipt['coverage']
    totals = receipt['totals']
    fits = [c for c in receipt['cells'] if c.get('fit_status') == 'fitted']
    lines = ['# Expected-rate baseline for original cosponsorship (P1 item 7)', '',
             'STATUS: EXPLORATORY. No number here is validated, forecast, or causal. Every quantity is a '
             'count, a ratio of counts, or a ranking summary, and each one carries its denominator.', '']
    lines += ['## What was fit', '',
              'One binomial logistic regression per chamber x congress. The unit is the directed pair '
              '(signer i, sponsor j) of panel members serving in the same chamber in the same congress. The '
              'outcome is n_ij, the number of bills sponsored by j in that chamber and congress that i '
              'signed as an original cosponsor; the binomial trials are N_ij, the number of those bills for '
              'which i held an eligible opportunity under the rule this lane already uses (a single dated '
              'term of i covers the introduction day in that chamber, and i is not the sponsor).', '',
              'Binomial rather than Poisson with a log-exposure offset: n_ij is bounded above by N_ij by '
              'construction, so the fitted expectation can never exceed the exposure.', '',
              '- Coverage: %s bills over congresses %s, introduced %s to %s, read cutoff %s. The requested '
              'range was %s, and the source panel `%s` holds %s.'
              % (f"{coverage['bills_in_covered_congresses']:,}",
                 ', '.join(str(c) for c in coverage['congresses']), coverage['first_introduced'],
                 coverage['last_introduced'], coverage['read_cutoff'], coverage['congress_range'],
                 Path(coverage['bill_source']).parent.name + '/' + Path(coverage['bill_source']).name,
                 ', '.join('%s: %s' % (c, f'{n:,}')
                           for c, n in sorted(coverage['bills_by_congress_in_source'].items()))),
              '- Member panel: %d members (the lane roster with dated service at the cutoff).'
              % coverage['members_in_panel'],
              '- Directed pairs in the cells: %s, of which %s are measured (N_ij > 0) and %s are '
              'no_eligible_bills (N_ij = 0, counted and left out of the fit, never scored as a zero).'
              % (f"{totals['directed_pairs']:,}", f"{totals['measured']:,}",
                 f"{totals['no_eligible_bills']:,}"),
              '- Signatures counted: %s original cosponsorships over %s eligible opportunities, an overall '
              'rate of %s.'
              % (f"{totals['original_cosponsorships']:,}", f"{totals['eligible_opportunities']:,}",
                 number(totals['original_cosponsorships'] / totals['eligible_opportunities'], 6)
                 if totals['eligible_opportunities'] else 'n/a'),
              '- Undirected pooled pairs written: %s.' % f"{receipt['undirected_pairs']:,}",
              '- Ideology: of the %s directed pairs in the cells (the %s measured and the %s with no '
              'eligible bills alike), %s carry a per-congress NOMINATE first dimension for both members '
              'from `%s`, %s fall back to the static HS119 score for at least one member, and %s have '
              'neither and take the within-cell mean. %s member-congress scores were kept out of %s usable '
              'rows in the requested congresses, and %s within-congress duplicate rows (party switches) '
              'were resolved to the row with more recorded votes.'
              % (f"{totals['directed_pairs']:,}", f"{totals['measured']:,}",
                 f"{totals['no_eligible_bills']:,}", f"{totals.get('nominate_per_congress', 0):,}",
                 Path(receipt['nominate']['source']).name,
                 f"{totals.get('nominate_static_hs119_fallback', 0):,}",
                 f"{totals.get('nominate_missing_imputed_at_cell_mean', 0):,}",
                 f"{receipt['nominate']['members_scored']:,}",
                 f"{receipt['nominate']['usable_rows']:,}",
                 f"{receipt['nominate']['duplicate_member_congress_rows']:,}"), '']
    lines += ['## Cells', '',
              '| congress | chamber | members | bills | measured pairs / pairs in cell | signatures / '
              'opportunities | base rate | per-congress NOMINATE pairs | converged | iterations |',
              '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    for cell in fits:
        lines.append('| %d | %s | %d | %s | %s / %s | %s / %s | %s | %s / %s | %s | %d |'
                     % (cell['congress'], cell['chamber'], cell['serving_members'], f"{cell['bills']:,}",
                        f"{cell['fitted_pairs']:,}", f"{cell['directed_pairs_in_cell']:,}",
                        f"{cell['original_cosponsorships']:,}", f"{cell['eligible_opportunities']:,}",
                        cell['base_rate'], f"{cell['nominate_pairs']['per_congress']:,}",
                        f"{cell['directed_pairs_in_cell']:,}", cell['converged'], cell['iterations']))
    lines += ['']
    lines += ['## Coefficients', '',
              'Log-odds on the natural scale of each covariate. The standard error and the 2.5th to 97.5th '
              'percentile band are the spread of %d refits on undirected-pair resamples of the same cell; '
              'they do not carry clustering by member, so they are the optimistic end of the range. The '
              'percentile band is printed beside the standard deviation because a near-separated resample '
              '-- one same-state Senate dyad dropping out, say -- can throw a single refit to a very large '
              'value and the standard deviation with it. Every coefficient is a within-cell association in '
              'a descriptive model; none of them is an effect.'
              % receipt['bootstrap_coefficient_draws'], '']
    for cell in fits:
        lines += ['### %s %d (%s measured directed pairs of %s; %s signatures over %s opportunities)'
                  % (cell['chamber'], cell['congress'], f"{cell['fitted_pairs']:,}",
                     f"{cell['directed_pairs_in_cell']:,}", f"{cell['original_cosponsorships']:,}",
                     f"{cell['eligible_opportunities']:,}"), '',
                  '| term | coefficient | bootstrap SE | bootstrap 2.5-97.5% | note |',
                  '| --- | --- | --- | --- | --- |']
        for column in cell['columns']:
            note = 'dropped: no variation in this cell' if column.get('dropped') else ''
            band = ('n/a' if column['bootstrap_p2_5'] is None
                    else '%s to %s' % (column['bootstrap_p2_5'], column['bootstrap_p97_5']))
            lines.append('| %s | %s | %s | %s | %s |'
                         % (column['name'],
                            'n/a' if column['coefficient'] is None else column['coefficient'],
                            'n/a' if column['bootstrap_se'] is None else column['bootstrap_se'],
                            band, note))
        lines += ['', 'Convergence: converged=%s after %d Newton iterations, max step %s, max gradient %s, '
                      'solver %s, ridge %s on standardised columns. Bootstrap: %d of %d draws used, %d '
                      'non-converged or failed.'
                  % (cell['converged'], cell['iterations'], cell['max_newton_step'], cell['max_gradient'],
                     cell['solver_status'], cell['ridge'], cell['bootstrap']['draws_used'],
                     cell['bootstrap']['draws_requested'], cell['bootstrap']['non_converged_or_failed']), '']
    lines += ['## Sign diagnostic (29 reviewed development dyads)', '',
              'Diagnostic only, never a training target: the baseline is fit without any label. The score is '
              'the pooled shrunken rate ratio (n + %s) / (E + %s) over every congress in which the two '
              'members shared a chamber, set beside the raw pooled rate n / N.' % (SHRINKAGE, SHRINKAGE), '',
              '- Dyads: %d (%d documented-positive, %d documented-negative).'
              % (benchmark['dyads'], benchmark['positive'], benchmark['negative']),
              '- Unmeasurable: %d of %d (%s).'
              % (benchmark['unmeasurable'], benchmark['dyads'],
                 ', '.join('%s %d' % (k, v) for k, v in benchmark['unmeasurable_states'].items()) or 'none'),
              '']
    lines += ['| score | unmeasurable handling | AUC | wins / comparisons | dyads | 95% dyad-bootstrap |',
              '| --- | --- | --- | --- | --- | --- |']
    for score_name, block in benchmark['scores'].items():
        for variant, values in block.items():
            lines.append('| %s | %s | %s | %s / %d | %d (%d positive, %d negative) | %s to %s |'
                         % (score_name, variant, values['auc'], values['wins'], values['comparisons'],
                            values['dyads'], values['positive'], values['negative'], values['ci_low'],
                            values['ci_high']))
    lines += ['', 'The interval is the 2.5th to 97.5th percentile over %d dyad resamples drawn inside each '
                  'class, so neither class can empty.' % receipt['bootstrap_auc_draws'], '']
    lines += ['## Descriptive correlation with the graded development pairs', '',
              '- Two-pass merged development rows available: %d.' % graded['two_pass_merged_rows'],
              '- Rows with an affinity degree that is assessable in either direction and identical in both '
              'passes: %d.' % graded['with_agreed_assessable_affinity'],
              '- Primary: Spearman %s of the pooled residual against the agreed degree, n = %d, degree '
              'distribution %s.' % (graded['primary']['spearman'], graded['primary']['n'],
                                    json.dumps(graded['degree_distribution'], sort_keys=True)),
              '- Secondary: Spearman %s of the pooled residual against an indicator of any agreed assessable '
              'affinity, n = %d, of which %d positive. Reported because the degree scale above is almost '
              'constant, so the primary number turns on very few rows.'
              % (graded['secondary']['spearman'], graded['secondary']['n'], graded['secondary']['positive']),
              '', 'Both are descriptive. Neither is an accuracy estimate and neither was used to choose '
                  'anything in the model.', '']
    lines += ['## Held-out discipline', '',
              '%d held-out dyads of the frozen probability sample are loaded as a pair_id deny-list and '
              'nothing else: no label, weight or stratum is read. Those pairs are scored in the pair tables '
              'like every other pair of serving members, and both validation tables above are checked '
              'against the deny-list and raise rather than filter. No held-out dyad is named in this report.'
              % receipt['held_out_dyads_denied'], '']
    lines += ['## Design choices pending Paul', '']
    for note in receipt['pending_decisions']:
        lines.append('- %s' % note)
    lines += ['', '## Receipt', '',
              '- Run id `%s`; runtime %s s; %d cells fitted.'
              % (receipt['glassbox_run_id'], receipt['runtime_seconds'], receipt['cells_fitted']),
              '- Flags: `--congress-range %s`, `--bills %s`, `--bootstrap %d`, `--auc-bootstrap %d`.'
              % (coverage['congress_range'], coverage['bill_source'],
                 receipt['bootstrap_coefficient_draws'], receipt['bootstrap_auc_draws']),
              '- Inputs:']
    for name, value in sorted(receipt['inputs'].items()):
        lines.append('  - `%s` sha256 `%s`' % (name, value['sha256']))
    lines += ['- Artefacts:']
    for artefact in receipt['artefacts']:
        lines.append('  - `%s` %s bytes, sha256 `%s`'
                     % (artefact['name'], f"{artefact['bytes']:,}", artefact['sha256']))
    lines += ['- Code `work_baseline.py` sha256 `%s`; python %s; numpy %s.'
              % (receipt['code_sha256'], receipt['python'].split()[0], receipt['numpy']), '']
    return '\n'.join(lines) + '\n'


# ----------------------------------------------------------------------- entry

def main(argv=None):
    try:
        from fec.surfaces.glassbox_emit import emit, new_run_id
    except ImportError:  # pragma: no cover - path-based fallback to the same file
        import importlib.util
        spec = importlib.util.spec_from_file_location('glassbox_emit', ROOT / 'fec/surfaces/glassbox_emit.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        emit, new_run_id = module.emit, module.new_run_id

    parser = argparse.ArgumentParser(
        description='Expected-rate baseline for original cosponsorship, per chamber and congress (EXPLORATORY)')
    parser.add_argument('--out', default=str(OUT))
    parser.add_argument('--bills', default=str(BILLS_FILE),
                        help='dated bill panel ndjson; read with this module\'s own reader, so no '
                             'congress filter is applied on the way in')
    parser.add_argument('--congress-range', default='116-119',
                        help='inclusive range such as 116-119 or 115-119, or a comma list')
    parser.add_argument('--nominate', default=str(NOMINATE_FILE))
    parser.add_argument('--bootstrap', type=int, default=BOOTSTRAP_COEFFICIENTS)
    parser.add_argument('--auc-bootstrap', type=int, default=BOOTSTRAP_AUC)
    args = parser.parse_args(argv)

    run_id = new_run_id('mpr-work-baseline')
    started = time.time()

    def stage(name, summary, **metadata):
        emit('stage', 'running', summary, run_id=run_id, stage=name,
             source='member_personal_relationships',
             duration_ms=int((time.time() - started) * 1000), metadata=metadata or None)

    emit('task', 'started', 'Original-cosponsorship expected-rate baseline opening', run_id=run_id,
         stage='start', source='member_personal_relationships',
         metadata=dict(out=args.out, bills=args.bills, congress_range=args.congress_range,
                       bootstrap=args.bootstrap, auc_bootstrap=args.auc_bootstrap))
    try:
        receipt = build(args.out, bills_path=args.bills, nominate_path=args.nominate,
                        congresses=args.congress_range, bootstrap=args.bootstrap,
                        auc_draws=args.auc_bootstrap, stage=stage)
        receipt['command_line'] = dict(out=args.out, bills=args.bills,
                                       congress_range=args.congress_range, nominate=args.nominate,
                                       bootstrap=args.bootstrap, auc_bootstrap=args.auc_bootstrap)
        out_dir = Path(args.out)
        receipt['glassbox_run_id'] = run_id
        receipt['runtime_seconds'] = round(time.time() - started, 1)
        receipt['cells'] = read_json(out_dir / 'baseline_fits.json')['cells']
        receipt['artefacts'] = [dict(name=name, bytes=(out_dir / name).stat().st_size,
                                     sha256=digest(out_dir / name)) for name in ARTEFACTS]
        (out_dir / 'REPORT.md').write_text(report_text(receipt), encoding='utf-8')
        receipt['artefacts'].append(dict(name='REPORT.md', bytes=(out_dir / 'REPORT.md').stat().st_size,
                                         sha256=digest(out_dir / 'REPORT.md')))
        receipt.pop('cells', None)
        receipt['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save(out_dir / 'run_receipt.json', receipt)
        emit('task', 'completed', 'Work baseline written', run_id=run_id, stage='done',
             source='member_personal_relationships', duration_ms=int((time.time() - started) * 1000),
             metadata=dict(measured_directed_pairs=receipt['totals']['measured'],
                           undirected_pairs=receipt['undirected_pairs'],
                           cells_fitted=receipt['cells_fitted']))
        print('Wrote %s measured directed pairs and %s undirected pairs to %s in %.1f s'
              % (f"{receipt['totals']['measured']:,}", f"{receipt['undirected_pairs']:,}", out_dir,
                 receipt['runtime_seconds']))
        return 0
    except Exception as error:
        emit('task', 'failed', 'Work baseline failed: %s' % error, run_id=run_id, stage='error',
             source='member_personal_relationships', duration_ms=int((time.time() - started) * 1000),
             metadata=dict(error=type(error).__name__))
        raise


if __name__ == '__main__':
    raise SystemExit(main())
