"""Frozen benchmark contract for the 29 documented development sign dyads.

STATUS: EXPLORATORY. Nothing here is a validated instrument, a forecast, or a
causal statement. Every number is a ranking summary of 29 reviewed dyads.

The canonical benchmark row is original-signature, strict-before work features
under the R0 specification with the four visibility features removed. All-history
timing, all-cosponsor signatures and the visibility features are named
diagnostics, reported beside the canonical row and never substituted for it.

This module adds a benchmark. It does not change, rerun or re-tune any existing
lane artifact, and by default it writes only under
outputs/member_personal_relationships/20260910_benchmark_contract. --output-dir
redirects writes elsewhere; --bills and --congress-range read a different, already-
reshaped bill panel and congress bound instead of the frozen 116-119 panel, and both
require --output-dir so the frozen run above is never overwritten.

Two quantities follow the panel a run actually loads rather than the frozen default: the
panel coverage start used by the S1 sensitivity and the coverage notes (derive_coverage_start)
and the contract's bill_universe block (run_bill_universe). A run whose panel block and S1
rule match the frozen ones is contract_version 1.1 and digests to CONTRACT_SHA256; any other
panel or range is contract_version 1.2, whose contract.json and run_receipt.json carry both
that run's digest and the frozen v1.1 digest.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import comb
from pathlib import Path
import argparse
import hashlib
import json
import sys
import time

import numpy as np

from .data import ROOT, read_json, digest
from .history_work import served_on
from .run_history import read_rows
from .regression import PENALTIES, SIM, LEVEL, VISIBILITY, matrices, save
from .regression_bias_controls import EXTRA
from .regression_diagnostics import leave_two_cases_out
from .chamber_work import WORK_FIELDS, temporal_features
from .personality_context import MODELS as PERSONALITY_MODELS

HERE = Path(__file__).resolve().parent
OUTPUTS = ROOT / 'outputs/member_personal_relationships'
HISTORY = OUTPUTS / '20260910_full_history'
REGRESSION = OUTPUTS / '20260910_regression'
PERSONALITY = OUTPUTS / '20260910_personality_context'
OUT = OUTPUTS / '20260910_benchmark_contract'

SEED = 20260910
BOOTSTRAP = 10000
MODE = 'members'
ALL_HISTORY_CUTOFF = '2026-09-11'
# Frozen v1.1 baseline only: the coverage start of the default 116-119 panel. Every run derives its own
# coverage_start from the panel it actually loaded (derive_coverage_start) and uses that value for the
# S1 dyad set, the contract bill_universe block, the coverage notes and the run receipt. This constant
# is the value that derivation must return under the default flags, and nothing else.
COVERAGE_START = '2019-01-03'
REFERENCE_TARGET = (164, 180)

# One template per run-dependent sentence, so the frozen v1.1 wording and the run-specific wording come
# out of the same code path and cannot drift apart.
S1_DROP_TEXT = 'dyads whose first documented event predates the bill panel coverage start {coverage_start}'
LOADER_TEXT = ('fec/research/member_personal_relationships/history_work.py read_history(), congresses {span}, '
               'read cutoff 2026-09-10; the "original" flag is first created there from the per-cosponsor '
               'isOriginalCosponsor field, exactly as original_work_context.py original_panel() consumes it.')
RE_READ_LOADER_TAIL = (
    ' This run did not call read_history(): it re-read the already-reshaped panel named in "serialized_panel" '
    'with run_history.read_rows() and applied the inclusive congress bound {start}-{end} from --congress-range, '
    'so rows outside that bound never reach the feature builders. That panel\'s own upstream provenance is '
    'recorded in the manifest.json and run_receipt.json written beside it, not here.')

# Non-work context. issue_similarity and co_service_* are deliberately absent:
# both are work-panel quantities and are supplied by the dated work builder.
CONTEXT_STATIC = ['same_party', 'same_state', 'same_chamber', 'dw1_distance',
                  'actor_leader', 'target_leader']
# Every work-derived column, produced by one builder for every benchmark row.
WORK_BENCH = ['direct_propensity', 'reverse_direct_propensity', 'weighted_shared_jaccard',
              'log_shared_bills', 'network_proximity', 'issue_similarity',
              'co_service_years', 'bipartisan_pair']
VOLUME = ['actor_log_original_signatures_given', 'target_log_original_signatures_given',
          'actor_log_original_signatures_received', 'target_log_original_signatures_received',
          'actor_log_bills_sponsored', 'target_log_bills_sponsored']
R0_NOVIS = CONTEXT_STATIC + WORK_BENCH + SIM + LEVEL + EXTRA
R0 = R0_NOVIS + VISIBILITY
# Nuisance floor: no dyadic work quantity of any kind, only who the two members
# are and how much each of them talks and files.
FLOOR = VISIBILITY + ['same_party', 'same_chamber', 'actor_republican', 'target_republican',
                      'actor_senator', 'target_senator'] + VOLUME
ROW_ORDER = ['C1', 'C2', 'C3', 'D1', 'D2', 'REF', 'F1', 'S1', 'S2', 'S2b', 'F1b']

CASES_FILE = 'outputs/member_personal_relationships/20260910_regression/cases.json'
FEATURES_FILE = 'outputs/member_personal_relationships/20260910_regression/features.json'
MEMBERS_FILE = 'outputs/member_personal_relationships/20260910_full_history/members.json'
PANEL_FILE = 'outputs/member_personal_relationships/20260910_full_history/bills.ndjson'
BILLS_FILE = 'outputs/cosponsor_challengers_20260905/bills.jsonl'
DEFAULT_CONGRESS_RANGE = (116, 119)
REFERENCE_FEATURES_FILE = 'outputs/member_personal_relationships/20260910_personality_context/features.json'
REFERENCE_AUC_FILE = 'outputs/member_personal_relationships/20260910_personality_context/same_fit_auc.json'

INPUT_PINS = {
    CASES_FILE: 'dc79cb78477262772edb9352b424e0b6340defeed165d39421dd61911b29a177',
    FEATURES_FILE: '04ca9829bf2a198f2447b2f2902ce6d12c62cda0072034e49eb3eef679b4ecc1',
    MEMBERS_FILE: 'cba35445627c239dc73bf2e810e274b61b5d04b7bb908b9785beaa87b856ebad',
    PANEL_FILE: 'aeb0f08a7df8aff3438aaf6c1bd9e74e1a41a672de9ab1bf742042a8d8448e10',
    BILLS_FILE: '44372d89553e1140f6e319055f8e06a8e00e69fef1f09236d73b9d4f55f63ed4',
    REFERENCE_FEATURES_FILE: '9645a657352032347e28defb562f885339f3fe174f1cc75e7c0a97a77619a952',
    REFERENCE_AUC_FILE: '482637167f73e41de61837f6940d22c9a9196e12d461d8435030b9fa49d6799d',
}

CONTRACT = {
    'contract_id': '20260910_benchmark_contract',
    'contract_version': '1.1',
    'status': 'EXPLORATORY',
    'owner_ruling': ('Original-signature, strict-before work features is the canonical benchmark row. '
                     'All-history timing and all-cosponsor signatures are named diagnostics. '
                     'Visibility features leave the estimate and are reported separately.'),
    'labels': {
        'file': CASES_FILE,
        'sha256': INPUT_PINS[CASES_FILE],
        'dyads': 29, 'positive': 20, 'negative': 9,
        'label_meaning': ('positive = documented personal friendship evidence; '
                          'negative = documented public antagonism evidence. Reviewed evidence only; '
                          'absence of cosponsorship never produces a label.'),
        'held_out_split_touched': False,
        'held_out_note': ('The sealed frozen-v5 held-out members and sampled pairs are not read, '
                          'not scored and not referenced by this benchmark.'),
    },
    'pair_universe': {
        'definition': 'Exactly the 29 development sign dyads in the pinned cases.json, in file order.',
        'row_expansion': ('One assessment per documented direction in case["directions"]; '
                          '33 direction rows over 29 dyads.'),
    },
    'bill_universe': {
        'source': BILLS_FILE,
        'source_sha256': INPUT_PINS[BILLS_FILE],
        'source_records': 61085,
        'loader': LOADER_TEXT.format(span='116-119'),
        'serialized_panel': PANEL_FILE,
        'serialized_panel_sha256': INPUT_PINS[PANEL_FILE],
        'panel_records': 61085,
        'congresses': [116, 117, 118, 119],
        'coverage_start': COVERAGE_START,
    },
    'signature_policies': {
        'original': ('bill["original"] is left exactly as the history loader produced it: the cosponsors whose '
                     'source record carries isOriginalCosponsor, restricted by the work builder to signers who '
                     'are not the sponsor and who served in that chamber on the introduction day.'),
        'all': ('bill["original"] is replaced by sorted(bill["joins"]), i.e. every valid signature on the bill, '
                'before the work builder runs. The builder is otherwise unchanged, so an "original" edge under '
                'this policy means "any valid cosponsor signature".'),
        'transform_invariant': 'set(bill["original"]) must remain a subset of bill["joins"] under either policy.',
    },
    'timing_policies': {
        'strict_before': ('Assessment date = case["first"], the earliest documented event date for that dyad. '
                          'A bill enters the panel only if its introduction date is strictly before that date.'),
        'all_history': ('Assessment date = ' + ALL_HISTORY_CUTOFF + ' for every dyad, so the whole 116-119 panel '
                        'enters for every dyad.'),
        'known_leak_under_all_history': ('Under all_history the work features are measured after the documented '
                                         'event, so they may encode the relationship they are being ranked '
                                         'against. This is why all_history is a diagnostic, not the benchmark.'),
        'known_leak_under_all_signatures': ('Under the "all" signature policy a signature may be joined long after '
                                            'the bill was introduced, so an "all"+strict_before combination would '
                                            'not be strictly before. That combination is therefore not built; '
                                            '"all" is only ever paired with all_history.'),
    },
    'features': {
        'work_builder': ('fec/research/member_personal_relationships/chamber_work.py temporal_features(). '
                         'Chamber-layered: House-House and Senate-Senate only; a dyad whose two members sit in '
                         'different chambers on the assessment date is structurally unavailable and receives '
                         'missing work features, never zero.'),
        'work_features': WORK_BENCH,
        'work_substitutions': {
            'co_service_congresses -> co_service_years': (
                'The stored R0 specification used co_service_congresses, a count over the whole 116-119 panel that '
                'is not bounded by the assessment date. The dated builder emits co_service_years, capped at the '
                'assessment date. One-for-one replacement; the feature count is unchanged.'),
            'bipartisan_pair': (
                'Recomputed from the dated builder as the mean of actor_bipartisan and target_bipartisan, each of '
                'which is that member\'s smoothed cross-party original-signature share with the focal partner '
                'excluded from both opportunity groups. Same construct and same smoothing as the stored '
                'bipartisan_pair, computed strictly before the assessment date instead of over all history.'),
            'co_service_years_on_cross_chamber_rows': (
                'chamber_work.co_service_years returns 0.0 when the layer is cross_chamber because no term matches '
                'that pseudo-chamber. This benchmark records it as missing, so a structurally unavailable dyad '
                'never contributes a fabricated zero.'),
        },
        'non_work_features': {
            'source': (FEATURES_FILE + ', "composite" source, produced by regression.py features(); '
                       'identical values in every benchmark row.'),
            'sha256': INPUT_PINS[FEATURES_FILE],
            'context_static': CONTEXT_STATIC,
            'similarity': SIM, 'levels': LEVEL, 'visibility': VISIBILITY,
            'extra_ideology_and_chamber': EXTRA,
            'extra_derivation': ('actor/target dw1, dw2, republican and senator are re-derived from '
                                 '20260910_full_history/members.json exactly as regression_bias_controls.py and '
                                 'personality_context.py derive them.'),
            'dw_nominate_note': ('DW-NOMINATE comes from HS119 only, as '
                                 'fec/research/member_personal_relationships/data.py already does.'),
        },
        'volume_features': {
            'names': VOLUME,
            'definition': ('Per member over the whole 116-119 panel: original signatures given (the member is an '
                           'original signer, is not the sponsor, and served in that chamber at introduction), '
                           'original signatures received on bills the member sponsored, and bills sponsored. '
                           'log1p of each count, for both endpoints.'),
            'policy': 'Counted under the "original" signature policy, matching the canonical row.',
            'timing': 'Not date-cut. A nuisance floor is deliberately given the more generous measurement.',
        },
        'specifications': {
            'R0': R0, 'R0_novis': R0_NOVIS, 'FLOOR': FLOOR,
            'R0_novis_rule': 'R0 minus the four visibility features, nothing else.',
            'FLOOR_rule': ('No dyadic work quantity of any kind; identity, chamber, party, visibility and '
                           'volume only.'),
        },
    },
    'validation': {
        'procedure': ('fec/research/member_personal_relationships/regression_diagnostics.py leave_two_cases_out(), '
                      'mode "members": one positive dyad and one negative dyad are held out together, the union of '
                      'their member and evidence-family exclusions is removed from training, the ridge penalty is '
                      'selected inside that reduced training set, and the two held-out dyads are then ranked '
                      'against each other in the same fit.'),
        'mode': MODE,
        'mode_evidence': ('The three stored receipts this benchmark reproduces all call leave_two_cases_out(..., '
                          '"members"): personality_context.py:200, regression_bias_controls.py:47, '
                          'original_work_context.py:185.'),
        'inner_penalty_grid': list(PENALTIES),
        'model': ('regression.py RidgeLogit; missing values are mean-imputed with an explicit missingness '
                  'indicator column per feature.'),
    },
    'metrics': {
        'same_fit_auc': ('Mean concordance over every (positive dyad, negative dyad) comparison that could be '
                         'scored. The denominator is reported with every figure; the full 29-dyad set gives '
                         '20 x 9 = 180.'),
        'dyad_bootstrap': {
            'replicates': BOOTSTRAP, 'seed': SEED,
            'procedure': ('Two-sample dyad bootstrap over the stored concordance rows: resample the positive dyads '
                          'with replacement and the negative dyads with replacement, then average the existing '
                          'concordance grid over the resampled index pairs. The fits are not repeated, so this '
                          'describes label-set sampling variability only, not refitting or selection variability.'),
            'interval': 'percentile 2.5 / 97.5',
        },
        'paired_difference': ('Row minus the canonical row on the same bootstrap draws, reported with its '
                             'percentile interval and the fraction of replicates above zero. Defined only for rows '
                             'built on the identical dyad set; reported as unavailable for the dyad-dropping '
                             'sensitivities.'),
        'nuisance_floor': ('The FLOOR specification run through the identical validation, as the reference level '
                           'for any other row.'),
        'permutation_null': {
            'unit': 'dyad labels', 'seed': SEED,
            'strata': ('The dated chamber layer of the canonical build: House, Senate, cross_chamber. Labels are '
                       'permuted within stratum so each stratum keeps its own positive count.'),
            'each_replicate': 'A complete same-fit run on the unchanged feature matrix with permuted labels.',
        },
    },
    'rows': {
        'C1': {'role': 'canonical', 'spec': 'R0_novis', 'signatures': 'original', 'timing': 'strict_before'},
        'C2': {'role': 'diagnostic', 'spec': 'R0_novis', 'signatures': 'original', 'timing': 'all_history'},
        'C3': {'role': 'diagnostic', 'spec': 'R0_novis', 'signatures': 'all', 'timing': 'all_history'},
        'D1': {'role': 'diagnostic', 'spec': 'R0', 'signatures': 'original', 'timing': 'strict_before'},
        'D2': {'role': 'diagnostic', 'spec': 'R0', 'signatures': 'all', 'timing': 'all_history'},
        'REF': {'role': 'wiring check', 'spec': 'personality_context R0_main_effects',
                'signatures': 'all (stored feature matrix)', 'timing': 'all_history (stored feature matrix)',
                'target': '164/180 from 20260910_personality_context/same_fit_auc.json'},
        'F1': {'role': 'nuisance floor', 'spec': 'FLOOR', 'signatures': 'original', 'timing': 'not date-cut'},
        'S1': {'role': 'sensitivity', 'spec': 'R0_novis', 'signatures': 'original', 'timing': 'strict_before',
               'drop': S1_DROP_TEXT.format(coverage_start=COVERAGE_START)},
        'S2': {'role': 'sensitivity', 'spec': 'R0_novis', 'signatures': 'original', 'timing': 'strict_before',
               'drop': ('dyads the work builder reports as cross-chamber structurally unavailable, identified from '
                        'their missing opportunity counts')},
        'S2b': {'role': 'sensitivity added by this build, not in the requested row list', 'spec': 'R0_novis',
                'signatures': 'original', 'timing': 'strict_before',
                'drop': 'every dyad with no eligible bill under the canonical build, whatever the reason'},
        'F1b': {'role': 'nuisance floor added by this build, not in the requested row list', 'spec': 'FLOOR',
                'signatures': 'original', 'timing': 'not date-cut',
                'why': ('F1 and C1 are not like for like: C1 has eight dyads with no eligible bill while F1 has '
                        'complete data on all 29. F1b runs the floor on the S2b dyad set so the floor and the work '
                        'specification are compared on identical dyads and an identical denominator.')},
        'N1': {'role': 'permutation null', 'spec': 'R0_novis', 'signatures': 'original', 'timing': 'strict_before'},
    },
    'subset_comparison': ('S2b minus F1b on shared bootstrap draws is the like-for-like contrast between the work '
                          'specification and the nuisance floor on the dyads the canonical build can actually '
                          'measure. It is a post-hoc subset chosen on a data property, so it is a sensitivity, '
                          'never the headline.'),
    'outputs': ['CONTRACT.md', 'contract.json', 'same_fit_rows.json', 'results.json',
                'null_distribution.json', 'REPORT.md', 'run_receipt.json'],
    'limitations': [
        'Twenty-nine reviewed dyads is a ranking exercise, not an accuracy estimate for any population.',
        'The dyads are not a probability sample of Congress and the negative class has nine members.',
        ('The bootstrap resamples labels only. It does not carry refitting, penalty-selection or '
         'specification-search variability.'),
        'Personality, ideology and visibility are fixed retrospective measurements even on the strict-before rows.',
        'No causal reading is available from any row: these are rankings of documented evidence, not effects.',
    ],
}

CONTRACT_SHA256 = 'be020c478d0562000c501036392d761308af7efc4828b92da121d78de38718d6'


def contract_digest(contract=None):
    payload = json.dumps(CONTRACT if contract is None else contract, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _emitter():
    try:
        from fec.surfaces.glassbox_emit import emit, new_run_id
        return emit, new_run_id
    except ImportError:
        import importlib.util
        spec = importlib.util.spec_from_file_location('glassbox_emit', ROOT / 'fec/surfaces/glassbox_emit.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.emit, module.new_run_id


EMIT, NEW_RUN_ID = _emitter()


def event(kind, status, summary, run_id, stage='', detail='', duration_ms=-1, metadata=None):
    EMIT(kind, status, summary, run_id=run_id, lane='claude',
         source='member-personal-relationships-benchmark', stage=stage, detail=detail,
         duration_ms=int(duration_ms), metadata=metadata)


# ---------------------------------------------------------------- feature build


def parse_congress_range(value):
    """argparse type= for --congress-range: 'START-END' -> inclusive (start, end) ints."""
    text = str(value).strip()
    parts = text.split('-')
    if len(parts) != 2 or not all(p.strip().isdigit() for p in parts):
        raise argparse.ArgumentTypeError(
            f'--congress-range must look like START-END with two whole numbers, got {value!r}')
    start, end = int(parts[0]), int(parts[1])
    if start > end:
        raise argparse.ArgumentTypeError(
            f'--congress-range start ({start}) must not be after end ({end}), got {value!r}')
    if start < 1 or end > 500:
        raise argparse.ArgumentTypeError(
            f'--congress-range values must be plausible congress numbers (1-500), got {value!r}')
    return (start, end)


def read_bills_in_range(path, congress_range):
    """Bill panel already reshaped by history_work.read_history(), restricted to a congress range.

    Rows at `path` carry the schema history_work.read_history() produces (key, congress, chamber,
    sponsor, introduced, end, title, area, joins, withdrawals, original, size, updated, url), so this
    performs no cosponsor re-parsing of its own: it re-reads the ndjson with run_history.read_rows()
    and applies the requested inclusive congress bound instead of history_work's fixed 116-119 filter.
    The filtered rows feed the same feature builders (history_work.full_work, chamber_work.
    temporal_features) unchanged.
    """
    start, end = congress_range
    all_rows = read_rows(path)
    bills = [b for b in all_rows if start <= b['congress'] <= end]
    audit = dict(source_path=str(path), source_records=len(all_rows), included_bills=len(bills),
                 excluded_outside_range=len(all_rows) - len(bills), congress_range=[start, end],
                 bills_by_congress=dict(Counter(b['congress'] for b in bills)),
                 earliest_introduced=min((b['introduced'] for b in bills), default=None))
    return bills, audit


def congress_start_date(congress):
    """First day of a congress: January 3 of year 1789 + 2*(congress - 1).

    The 20th Amendment fixed January 3 as the convening date from the 74th congress onward, so this is
    exact for every congress this lane can read (115 -> 2017-01-03, 116 -> 2019-01-03).
    """
    return f'{1789 + 2 * (int(congress) - 1)}-01-03'


def derive_coverage_start(bills_audit, congress_range):
    """Panel coverage start for this run, with the derivation recorded rather than assumed.

    Chosen rule: the first day of the earliest congress actually present in the loaded, range-filtered
    panel. It is used instead of min(introduced) because it is a property of the requested panel rather
    than of whichever bill happens to be filed first, and because a congress that opens with no bill on
    day one must not shrink the coverage window. min(introduced) is recorded beside it as an observed
    cross-check; for both panels this lane reads the two agree exactly.
    """
    congresses = sorted(bills_audit['bills_by_congress'])
    requested_start = congress_range[0]
    if congresses:
        earliest, basis = congresses[0], 'earliest congress present in the loaded panel'
    else:
        earliest, basis = requested_start, 'requested --congress-range start (the loaded panel is empty)'
    coverage_start = congress_start_date(earliest)
    return dict(
        coverage_start=coverage_start,
        rule='first day of the earliest congress in the loaded bill panel',
        basis=basis,
        earliest_congress=int(earliest),
        formula=f'January 3 of year 1789 + 2*({int(earliest)} - 1) = {coverage_start}',
        congresses_in_panel=[int(c) for c in congresses],
        requested_congress_range=[int(congress_range[0]), int(congress_range[1])],
        requested_range_start_date=congress_start_date(requested_start),
        earliest_introduced_in_panel=bills_audit.get('earliest_introduced'),
        agrees_with_earliest_introduced=bills_audit.get('earliest_introduced') == coverage_start,
        frozen_v1_1_coverage_start=COVERAGE_START)


def repo_relative(path):
    """Repo-relative POSIX name where the file sits under ROOT, so the frozen panel renders as the
    pinned PANEL_FILE string; otherwise the absolute path."""
    path = Path(path)
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def run_bill_universe(bills_path, bills_sha256, bills_audit, coverage):
    """The contract's bill_universe block, built from the panel this run actually loaded.

    Under the default flags every field reproduces the frozen v1.1 block exactly, which is what keeps
    CONTRACT_SHA256 valid for a default run. Under any other panel or range the block describes that
    panel, so contract.json can no longer contradict run_receipt.json.
    """
    panel = repo_relative(bills_path)
    frozen_panel = panel == PANEL_FILE and bills_sha256 == INPUT_PINS[PANEL_FILE]
    congresses = [int(c) for c in sorted(bills_audit['bills_by_congress'])]
    start, end = bills_audit['congress_range']
    span = f'{congresses[0]}-{congresses[-1]}' if congresses else f'{start}-{end}'
    loader = LOADER_TEXT.format(span=span)
    if not frozen_panel:
        loader += RE_READ_LOADER_TAIL.format(start=start, end=end)
    return {
        'source': BILLS_FILE if frozen_panel else panel,
        'source_sha256': INPUT_PINS[BILLS_FILE] if frozen_panel else bills_sha256,
        'source_records': int(bills_audit['source_records']),
        'loader': loader,
        'serialized_panel': panel,
        'serialized_panel_sha256': bills_sha256,
        'panel_records': int(bills_audit['included_bills']),
        'congresses': congresses,
        'coverage_start': coverage['coverage_start'],
    }


def build_run_contract(bill_universe, coverage_start):
    """CONTRACT with its panel block and its coverage-dependent S1 wording replaced by this run's.

    contract_version is decided by content, not by which flags were typed: a run whose panel block and
    S1 rule are identical to the frozen ones is v1.1 and digests to CONTRACT_SHA256 by construction;
    anything else is v1.2. Nothing here mutates CONTRACT.
    """
    rows = {k: dict(v) for k, v in CONTRACT['rows'].items()}
    rows['S1']['drop'] = S1_DROP_TEXT.format(coverage_start=coverage_start)
    candidate = dict(CONTRACT, bill_universe=bill_universe, rows=rows)
    version = '1.1' if candidate == CONTRACT else '1.2'
    return dict(candidate, contract_version=version)


def consumed_input_pins(observed, bills_path, bills_sha256):
    """The pin table for the files this run actually read.

    verify_pins() checks the seven frozen v1.1 pins for drift; that table names the 116-119 panel even
    when --bills points somewhere else, which made the 115-119 receipt read as though no hashed input
    reflected the stated range. Here the panel entry is replaced by the file the run opened. Under the
    default flags the key and the value are the frozen ones, so the table is unchanged.
    """
    panel = repo_relative(bills_path)
    consumed = {k: v for k, v in observed.items() if k != PANEL_FILE or k == panel}
    consumed[panel] = bills_sha256
    return consumed


def apply_signature_policy(bills, policy):
    """Return the bill panel the work builder should see under this signature policy."""
    if policy == 'original':
        return bills
    if policy != 'all':
        raise ValueError('Unknown signature policy: ' + str(policy))
    out = []
    for b in bills:
        joins = sorted(b['joins'])
        if not set(joins).issubset(set(b['joins'])):
            raise ValueError('Signature policy produced a signer without a valid signature')
        out.append(dict(b, original=joins))
    return out


def build_assessments(cases, timing):
    """One dated assessment per documented direction."""
    if timing == 'strict_before':
        def when(case):
            return case['first']
    elif timing == 'all_history':
        def when(case):
            return ALL_HISTORY_CUTOFF
    else:
        raise ValueError('Unknown timing policy: ' + str(timing))
    out = []
    for i, c in enumerate(cases):
        for k, (a, b) in enumerate(c['directions']):
            out.append(dict(id=f'{i}:{k}', case=i, direction=k, actor=a, target=b, date=when(c)))
    return out


def finish_work_row(feature_row):
    """Post-process one work row: a structurally unavailable layer must never read as zero."""
    row = dict(feature_row)
    if row.get('chamber') == 'cross_chamber':
        row['co_service_years'] = None
    a, b = row.get('actor_bipartisan'), row.get('target_bipartisan')
    row['bipartisan_pair'] = (a + b) / 2 if a is not None and b is not None else None
    return row


def build_work_rows(members, bills, cases, policy, timing, progress=print):
    """The one work-feature builder every benchmark row uses."""
    panel = apply_signature_policy(bills, policy)
    assessments = build_assessments(cases, timing)
    features, audit = temporal_features(members, panel, assessments, progress)
    rows = {}
    for r in assessments:
        key = (r['actor'], r['target'])
        if key in rows:
            raise ValueError(f'Two assessments share direction {key}; one feature row cannot serve both')
        rows[key] = finish_work_row(features[r['id']])
    audit = dict(audit, signature_policy=policy, timing_policy=timing, assessments=len(assessments),
                 cutoff=None if timing == 'strict_before' else ALL_HISTORY_CUTOFF)
    return rows, audit


def volume_counts(members, bills):
    """Per-member panel volume under the original signature policy."""
    given, received, sponsored = Counter(), Counter(), Counter()
    for b in bills:
        sponsored[b['sponsor']] += 1
        for a in b['original']:
            if a == b['sponsor']:
                continue
            if a in members and not served_on(members[a], b['introduced'], b['chamber']):
                continue
            given[a] += 1
            received[b['sponsor']] += 1
    return given, received, sponsored


def static_rows(cases, members, stored_composite, volumes):
    """Non-work features, identical in every benchmark row."""
    given, received, sponsored = volumes
    out = {}
    for c in cases:
        for a, b in c['directions']:
            source = stored_composite[(a, b)]
            row = {n: source.get(n) for n in CONTEXT_STATIC + SIM + LEVEL + VISIBILITY}
            for label, who in (('actor', a), ('target', b)):
                row[label + '_dw1'] = members[who].get('d1')
                row[label + '_dw2'] = members[who].get('d2')
                row[label + '_republican'] = float(members[who]['party'] == 'Republican')
                row[label + '_senator'] = float(members[who]['chamber'] == 'Senate')
                row[label + '_log_original_signatures_given'] = float(np.log1p(given[who]))
                row[label + '_log_original_signatures_received'] = float(np.log1p(received[who]))
                row[label + '_log_bills_sponsored'] = float(np.log1p(sponsored[who]))
            out[(a, b)] = row
    return out


def merge_rows(static, work):
    """Work columns always win; the static side deliberately carries no work column."""
    overlap = set(next(iter(static.values()))) & set(WORK_BENCH)
    if overlap:
        raise ValueError('Static features leaked a work column: ' + ', '.join(sorted(overlap)))
    return {k: dict(static[k], **work[k]) for k in static}


# ---------------------------------------------------------------- scoring


def concordance_grid(cases, result):
    positive = [i for i, c in enumerate(cases) if c['y']]
    negative = [i for i, c in enumerate(cases) if not c['y']]
    table = {(r['positive'], r['negative']): r['concordance'] for r in result['rows'] if 'concordance' in r}
    missing = [(p, n) for p in positive for n in negative if (p, n) not in table]
    if missing:
        raise ValueError(f'{len(missing)} comparisons were not scored; a partial grid cannot be resampled')
    grid = np.array([[table[(p, n)] for n in negative] for p in positive], dtype=float)
    return grid, positive, negative


def bootstrap_draws(n_positive, n_negative, replicates=BOOTSTRAP, seed=SEED):
    """Same construction as the session's auc_ci.py: one shared draw per (shape, seed)."""
    rng = np.random.default_rng(seed)
    return (rng.integers(0, n_positive, size=(replicates, n_positive)),
            rng.integers(0, n_negative, size=(replicates, n_negative)))


def bootstrap_auc(grid, draws):
    i, j = draws
    return grid[i[:, :, None], j[:, None, :]].mean(axis=(1, 2))


def interval(values):
    low, mid, high = np.percentile(values, [2.5, 50, 97.5])
    return dict(low=float(low), median=float(mid), high=float(high),
                mean=float(np.mean(values)),
                sd=float(np.std(values, ddof=1)) if len(values) > 1 else None)


def run_same_fit(name, cases, feature_rows, names, run_id, note=''):
    started = time.time()
    x = matrices(cases, names, feature_rows)
    result = leave_two_cases_out(cases, x, MODE)
    seconds = time.time() - started
    summary = (f"{name}: same-fit AUC {result['auc']:.4f} "
               f"({round(result['auc'] * result['comparisons'])}/{result['comparisons']})")
    print(f'  {summary}  [{seconds:.1f}s, {result["unique_fits"]} unique fits]', flush=True)
    event('benchmark_row', 'ok', summary, run_id, stage=name, detail=note, duration_ms=seconds * 1000,
          metadata=dict(row=name, features=len(names), dyads=len(cases), comparisons=result['comparisons'],
                        expected_comparisons=result['expected_comparisons'], auc=result['auc'],
                        unique_fits=result['unique_fits']))
    return result, seconds


def missing_report(cases, feature_rows, names):
    """How much of a row's design matrix is actually observed."""
    blocks = matrices(cases, names, feature_rows)
    stacked = np.vstack(blocks)
    per_feature = {n: int(np.sum(~np.isfinite(stacked[:, k]))) for k, n in enumerate(names)}
    work = [n for n in names if n in WORK_BENCH or n in WORK_FIELDS]
    empty = []
    if work:
        index = [names.index(n) for n in work]
        empty = [i for i, block in enumerate(blocks) if not np.isfinite(block[:, index]).any()]
    return dict(direction_rows=int(stacked.shape[0]),
                missing_cells_by_feature={k: v for k, v in per_feature.items() if v},
                dyads_with_no_observed_work_feature=empty)


# ---------------------------------------------------------------- permutation null


def chamber_strata(cases, work_rows):
    """Dated chamber layer of the canonical build, one label per dyad."""
    strata = defaultdict(list)
    for i, c in enumerate(cases):
        a, b = c['directions'][0]
        strata[work_rows[(a, b)].get('chamber') or 'unresolved'].append(i)
    return dict(strata)


def permuted_cases(cases, strata, rng):
    """Permute y inside each stratum; pairs, families and directions are untouched."""
    out = [dict(c) for c in cases]
    for indices in strata.values():
        labels = rng.permutation([cases[i]['y'] for i in indices])
        for i, y in zip(indices, labels):
            out[i]['y'] = int(y)
            out[i]['sign'] = 'positive' if int(y) else 'negative'
    return out


def stratum_shape(cases, strata):
    return {k: dict(dyads=len(v), positive=sum(cases[i]['y'] for i in v),
                    negative=sum(1 - cases[i]['y'] for i in v)) for k, v in sorted(strata.items())}


def distinct_permutations(cases, strata):
    total = 1
    for indices in strata.values():
        total *= comb(len(indices), sum(cases[i]['y'] for i in indices))
    return total


def summarise_null(values, observed, requested, started, partial):
    array = np.array(values, dtype=float)
    body = dict(permutations_requested=requested, permutations_completed=len(values), partial=partial,
                seconds=time.time() - started, seed=SEED, mode=MODE, observed_auc=observed,
                values=[float(v) for v in array])
    if len(array):
        body.update(mean=float(array.mean()),
                    sd=float(array.std(ddof=1)) if len(array) > 1 else None,
                    percentile_50=float(np.percentile(array, 50)),
                    percentile_95=float(np.percentile(array, 95)),
                    percentile_99=float(np.percentile(array, 99)),
                    observed_percentile_rank=float(np.mean(array < observed) + .5 * np.mean(array == observed)),
                    one_sided_p=float((1 + int(np.sum(array >= observed))) / (1 + len(array))))
    else:
        body.update(mean=None, sd=None, percentile_50=None, percentile_95=None, percentile_99=None,
                    observed_percentile_rank=None, one_sided_p=None)
    return body


def permutation_null(cases, feature_rows, names, strata, observed, requested, max_minutes, run_id):
    """Each replicate is a complete same-fit run; partial results are written as they accrue."""
    x = matrices(cases, names, feature_rows)
    rng = np.random.default_rng(SEED)
    values, started = [], time.time()
    deadline = started + max_minutes * 60
    stopped = None
    for k in range(requested):
        if time.time() > deadline:
            stopped = f'wall-clock guard of {max_minutes} minutes reached after {k} replicates'
            print('  ' + stopped, flush=True)
            break
        values.append(float(leave_two_cases_out(permuted_cases(cases, strata, rng), x, MODE)['auc']))
        if k == 0:
            each = time.time() - started
            print(f'  one permutation took {each:.1f}s; {requested} would take '
                  f'{each * requested / 60:.1f} minutes (guard {max_minutes} minutes)', flush=True)
            event('benchmark_null', 'running',
                  f'permutation projection {each * requested / 60:.1f} minutes for {requested} replicates',
                  run_id, stage='N1', duration_ms=each * 1000,
                  metadata=dict(seconds_per_permutation=each, requested=requested, max_minutes=max_minutes))
        if (k + 1) % 10 == 0:
            print(f'  permutations {k + 1}/{requested}, null mean {np.mean(values):.4f}', flush=True)
            save(OUT / 'null_distribution.json', summarise_null(values, observed, requested, started, True))
    body = summarise_null(values, observed, requested, started, False)
    if stopped:
        body['stopped_early'] = stopped
    return body


# ---------------------------------------------------------------- reporting


def fraction(auc, comparisons):
    return f'{auc:.4f} ({round(auc * comparisons)}/{comparisons})'


def report_text(results, null, contract_sha, cases, shape, available, notes, measurable):
    canonical = results['C1']
    floor = results['F1']
    lines = ['# Benchmark contract: 29 documented development sign dyads', '']
    lines.append('**STATUS: EXPLORATORY.** Nothing below is a validated instrument, a forecast, or a causal '
                 'statement. Every figure is a ranking summary over reviewed dyads and is printed with its own '
                 'denominator in the same sentence.')
    lines.append('')
    lines.append(f'Label set: {len(cases)} dyads ({sum(c["y"] for c in cases)} documented friendship, '
                 f'{sum(1 - c["y"] for c in cases)} documented antagonism) from `{CASES_FILE}` '
                 f'sha256 `{CONTRACT["labels"]["sha256"]}`. Contract sha256 `{contract_sha}`. '
                 'The sealed held-out split is not read by this benchmark.')
    lines.append('')
    lines.append('## Rows')
    lines.append('')
    lines.append('| row | spec | signatures | timing | comparisons | same-fit AUC | 95% CI | '
                 'diff vs C1 [95% CI] | notes |')
    lines.append('| --- | --- | --- | --- | --- | --- | --- | --- | --- |')
    for name in ROW_ORDER:
        r = results[name]
        ci = f"[{r['ci']['low']:.4f}, {r['ci']['high']:.4f}]" if r.get('ci') else 'n/a'
        if r.get('diff_vs_C1'):
            d = r['diff_vs_C1']
            diff = (f"{d['point']:+.4f} [{d['low']:+.4f}, {d['high']:+.4f}], "
                    f"frac>0 {d['fraction_above_zero']:.3f}")
        else:
            diff = r.get('diff_unavailable', 'n/a')
        lines.append(f"| {name} | {r['spec_label']} ({r['features']}) | {r['signatures']} | {r['timing']} | "
                     f"{r['comparisons']}/{r['expected_comparisons']} | {fraction(r['auc'], r['comparisons'])} | "
                     f"{ci} | {diff} | {r['note']} |")
    lines.append('')
    lines.append(f"The canonical row C1 scores {fraction(canonical['auc'], canonical['comparisons'])} comparisons "
                 f"over {canonical['dyads']} dyads ({canonical['positive']} positive, {canonical['negative']} "
                 f"negative), with a {CONTRACT['metrics']['dyad_bootstrap']['replicates']}-replicate dyad "
                 f"bootstrap interval of [{canonical['ci']['low']:.4f}, {canonical['ci']['high']:.4f}].")
    lines.append('')
    lines.append('## Nuisance floor')
    lines.append('')
    floor_line = (f"F1 carries no dyadic work quantity at all - visibility, party, chamber and per-member volume "
                  f"only, {len(FLOOR)} features - and reaches {fraction(floor['auc'], floor['comparisons'])} with a "
                  f"95% interval of [{floor['ci']['low']:.4f}, {floor['ci']['high']:.4f}]. C1 reaches "
                  f"{fraction(canonical['auc'], canonical['comparisons'])} over the same "
                  f"{canonical['comparisons']} comparisons.")
    if floor.get('diff_vs_C1'):
        d = floor['diff_vs_C1']
        floor_line += (f" C1 minus F1 on paired draws is {-d['point']:+.4f} "
                       f"[{-d['high']:+.4f}, {-d['low']:+.4f}] over {d['replicates']} replicates, with "
                       f"{1 - d['fraction_above_zero']:.3f} of replicates above zero.")
    lines.append(floor_line)
    lines.append('')
    lines.append('F1 and C1 are not measured on the same evidence. F1 has complete data on all '
                 f"{canonical['dyads']} dyads, while C1 has "
                 f"{len(results['C1']['coverage']['dyads_with_no_observed_work_feature'])} dyads with no work value "
                 f"at all and {canonical['dyads'] - results['S2b']['dyads']} with no bill-derived work value, so any ordering between them mixes a "
                 'specification difference with a coverage difference.')
    lines.append('')
    lines.append('## Like-for-like on the measurable dyads')
    lines.append('')
    subset, subset_floor = results['S2b'], results['F1b']
    lines.append(f"On the {measurable['dyads']} dyads the canonical build can actually measure, the work "
                 f"specification S2b reaches {fraction(subset['auc'], subset['comparisons'])} "
                 f"[{subset['ci']['low']:.4f}, {subset['ci']['high']:.4f}] and the same nuisance floor F1b reaches "
                 f"{fraction(subset_floor['auc'], subset_floor['comparisons'])} "
                 f"[{subset_floor['ci']['low']:.4f}, {subset_floor['ci']['high']:.4f}] over the identical "
                 f"{measurable['comparisons']} comparisons. S2b minus F1b on shared draws is "
                 f"{measurable['point']:+.4f} [{measurable['low']:+.4f}, {measurable['high']:+.4f}] with "
                 f"{measurable['fraction_above_zero']:.3f} of {measurable['replicates']} replicates above zero.")
    lines.append('')
    lines.append(measurable['caveat'])
    lines.append('')
    lines.append('## Permutation null for C1')
    lines.append('')
    if null.get('permutations_completed'):
        lines.append(f"{null['permutations_completed']} of {null['permutations_requested']} requested label "
                     f"permutations completed, each a complete same-fit run over the same "
                     f"{canonical['comparisons']} comparisons with labels permuted inside the dated chamber strata "
                     f"{json.dumps(shape)}. Null mean {null['mean']:.4f} over "
                     f"{null['permutations_completed']} replicates, 95th percentile {null['percentile_95']:.4f}, "
                     f"99th percentile {null['percentile_99']:.4f}. C1's observed "
                     f"{fraction(canonical['auc'], canonical['comparisons'])} sits at percentile rank "
                     f"{null['observed_percentile_rank']:.4f} of that null, one-sided p = "
                     f"{null['one_sided_p']:.4f} on {null['permutations_completed']} replicates.")
        lines.append('')
        lines.append(f'The stratified design admits {available:,} distinct label assignments in total. The '
                     'cross-chamber stratum holds no positive dyad, so those dyads stay negative in every '
                     'replicate, and the Senate stratum holds a single negative dyad. The null is therefore '
                     'narrower than an unrestricted label permutation would be.')
    else:
        lines.append(f"No permutation replicate was completed ({null.get('reason', 'see null_distribution.json')}). "
                     'No null figure is reported and no substitute is offered.')
    lines.append('')
    lines.append('## Reading notes')
    lines.append('')
    lines.extend('- ' + n for n in notes)
    lines.append('')
    lines.append('## Limitations carried by every row above')
    lines.append('')
    lines.extend('- ' + n for n in CONTRACT['limitations'])
    lines.append('')
    return '\n'.join(lines) + '\n'


def contract_markdown(contract_sha, bill_panel_used=None, contract=None, frozen_sha=None):
    contract = CONTRACT if contract is None else contract
    frozen_sha = CONTRACT_SHA256 if frozen_sha is None else frozen_sha
    lines = ['# Benchmark contract', '', '**STATUS: EXPLORATORY.**', '',
             f'Frozen contract sha256 `{frozen_sha}` over `json.dumps(CONTRACT, sort_keys=True)`.', '']
    if contract_sha != frozen_sha:
        lines.append(f'This run\'s contract is version {contract["contract_version"]}, sha256 `{contract_sha}`: '
                     'the `bill_universe` block and the S1 coverage rule below were built from the panel this run '
                     'actually loaded, so they describe this run and not the frozen 116-119 default. Every other '
                     f'section is the frozen v1.1 text carried unchanged from `{frozen_sha}`.')
        lines.append('')
    lines.append('The machine-readable form is `contract.json`. This file is the same content in prose so a '
                 'reviewer can check the benchmark definition without reading JSON.')
    lines.append('')

    def render(value, depth):
        pad = '  ' * depth
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, (dict, list)):
                    lines.append(f'{pad}- **{k}**')
                    render(v, depth + 1)
                else:
                    lines.append(f'{pad}- **{k}**: {v}')
        elif isinstance(value, list):
            for v in value:
                if isinstance(v, (dict, list)):
                    render(v, depth + 1)
                else:
                    lines.append(f'{pad}- {v}')

    render(contract, 0)
    lines.append('')
    if bill_panel_used:
        lines.append('## Bills input for this run (CONTRACT.md v1.2 addendum)')
        lines.append('')
        lines.append('The `bill_universe` section above is already this run\'s panel. This addendum adds the '
                     'per-congress record split the block does not carry:')
        lines.append('')
        lines.append(f"- **path**: {bill_panel_used['path']}")
        lines.append(f"- **sha256**: {bill_panel_used['sha256']}")
        lines.append(f"- **congress_range**: {bill_panel_used['congress_range']}")
        lines.append(f"- **records_in_file**: {bill_panel_used['records_in_file']}")
        lines.append(f"- **records_in_range**: {bill_panel_used['records_in_range']}")
        lines.append(f"- **bills_by_congress**: {bill_panel_used['bills_by_congress']}")
        lines.append('')
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- main


def observed_pins():
    return {name: (digest(ROOT / name) if (ROOT / name).exists() else None) for name in INPUT_PINS}


def verify_pins():
    observed = observed_pins()
    drift = {k: dict(pinned=v, observed=observed[k]) for k, v in INPUT_PINS.items()
             if observed[k] != v}
    if drift:
        raise RuntimeError('Pinned benchmark inputs changed: ' + json.dumps(drift, indent=1))
    return observed


def cached_work(members, bills, cases, policy, timing, rebuild, run_id):
    """Build once, then always read the JSON round trip so every run sees identical values."""
    path = OUT / f'work_rows_{policy}_{timing}.json'
    if rebuild or not path.exists():
        started = time.time()
        print(f'  building work features: signatures={policy} timing={timing}', flush=True)
        rows, audit = build_work_rows(members, bills, cases, policy, timing)
        save(path, dict(signature_policy=policy, timing_policy=timing, audit=audit,
                        rows=[dict(direction=list(k), features=v) for k, v in rows.items()]))
        event('benchmark_work_panel', 'ok', f'work panel {policy}/{timing} built', run_id,
              stage=f'{policy}/{timing}', duration_ms=(time.time() - started) * 1000,
              metadata=dict(signature_policy=policy, timing_policy=timing, direction_rows=len(rows),
                            bills_by_chamber=audit['bills_used_by_chamber']))
    stored = read_json(path)
    rows = {tuple(r['direction']): r['features'] for r in stored['rows']}
    print(f'  work panel {policy}/{timing}: {len(rows)} direction rows', flush=True)
    return rows, stored['audit']


def main():
    parser = argparse.ArgumentParser(description='Frozen benchmark contract for the 29 development sign dyads')
    parser.add_argument('--permutations', type=int, default=200)
    parser.add_argument('--max-minutes', type=float, default=90.)
    parser.add_argument('--bootstrap', type=int, default=BOOTSTRAP)
    parser.add_argument('--rebuild-work', action='store_true')
    parser.add_argument('--bills', default=PANEL_FILE,
                        help='Bill panel ndjson already reshaped by history_work.read_history() (relative '
                             f'to the repo root unless absolute). Defaults to the frozen panel: {PANEL_FILE}')
    parser.add_argument('--congress-range', type=parse_congress_range, default=DEFAULT_CONGRESS_RANGE,
                        help='Inclusive congress range to keep from --bills, e.g. 115-119. Defaults to '
                             f'{DEFAULT_CONGRESS_RANGE[0]}-{DEFAULT_CONGRESS_RANGE[1]}, the frozen contract range.')
    parser.add_argument('--output-dir', default=None,
                        help='Write outputs here instead of the frozen 20260910_benchmark_contract directory. '
                             'Required whenever --bills or --congress-range is non-default, so the frozen run '
                             'is never overwritten.')
    args = parser.parse_args()

    bills_path = Path(args.bills)
    if not bills_path.is_absolute():
        bills_path = ROOT / bills_path
    non_default_inputs = (args.bills != PANEL_FILE) or (args.congress_range != DEFAULT_CONGRESS_RANGE)
    if non_default_inputs and not args.output_dir:
        parser.error('--bills or --congress-range differs from the frozen default; pass --output-dir so the '
                     'frozen 20260910_benchmark_contract run is never overwritten.')

    global OUT
    if args.output_dir:
        OUT = Path(args.output_dir)
        if not OUT.is_absolute():
            OUT = ROOT / OUT

    run_id = NEW_RUN_ID('benchmark-contract')
    started = time.time()
    frozen_sha = contract_digest()
    print(f'Benchmark contract {frozen_sha}', flush=True)
    event('benchmark_contract', 'started', 'benchmark contract run started', run_id, stage='start',
          detail=f'permutations={args.permutations} max_minutes={args.max_minutes}',
          metadata=dict(contract_sha256=frozen_sha, seed=SEED, mode=MODE))
    if CONTRACT_SHA256 != frozen_sha:
        raise RuntimeError(f'Contract changed: frozen {CONTRACT_SHA256} vs computed {frozen_sha}')
    pins = verify_pins()

    OUT.mkdir(parents=True, exist_ok=True)

    cases = read_json(REGRESSION / 'cases.json')
    members = read_json(HISTORY / 'members.json')
    bills, bills_audit = read_bills_in_range(bills_path, args.congress_range)
    bills_sha256 = digest(bills_path)
    consumed_pins = consumed_input_pins(pins, bills_path, bills_sha256)
    print(f'Bills panel: {bills_path} congress {args.congress_range[0]}-{args.congress_range[1]}: '
          f'{bills_audit["included_bills"]:,} of {bills_audit["source_records"]:,} records in range', flush=True)
    event('benchmark_bills_panel', 'ok', f'bills panel loaded: {bills_audit["included_bills"]:,} records', run_id,
          stage='bills', metadata=dict(path=str(bills_path), sha256=bills_sha256,
          congress_range=list(args.congress_range), source_records=bills_audit['source_records'],
          included_bills=bills_audit['included_bills']))
    bill_panel_used = None
    if non_default_inputs:
        bill_panel_used = dict(path=str(bills_path), sha256=bills_sha256,
                               congress_range=list(args.congress_range),
                               records_in_file=bills_audit['source_records'],
                               records_in_range=bills_audit['included_bills'],
                               bills_by_congress=bills_audit['bills_by_congress'])

    # D1/D2: the panel start and the contract's panel block are derived from the panel just loaded, so
    # the S1 rule, the coverage notes and contract.json all describe this run rather than the default.
    coverage = derive_coverage_start(bills_audit, args.congress_range)
    coverage_start = coverage['coverage_start']
    run_contract = build_run_contract(run_bill_universe(bills_path, bills_sha256, bills_audit, coverage),
                                      coverage_start)
    contract_sha = contract_digest(run_contract)
    contract_version = run_contract['contract_version']
    if contract_version == '1.1' and contract_sha != CONTRACT_SHA256:
        raise RuntimeError(f'A v1.1 run contract must digest to the frozen {CONTRACT_SHA256}, got {contract_sha}')
    if contract_version != '1.1' and contract_sha == CONTRACT_SHA256:
        raise RuntimeError('A v1.2 run contract must not carry the frozen digest')
    print(f'Coverage start {coverage_start} ({coverage["basis"]}, {coverage["formula"]}); '
          f'earliest introduced in panel {coverage["earliest_introduced_in_panel"]}', flush=True)
    print(f'Contract version {contract_version}: run sha256 {contract_sha}, frozen v1.1 {CONTRACT_SHA256}',
          flush=True)
    event('benchmark_contract_panel', 'ok',
          f'contract v{contract_version} built for coverage_start {coverage_start}', run_id, stage='contract',
          metadata=dict(contract_version=contract_version, contract_sha256=contract_sha,
                        frozen_contract_sha256=CONTRACT_SHA256, coverage_start=coverage_start,
                        coverage_basis=coverage['basis'],
                        congresses=run_contract['bill_universe']['congresses']))
    written_contract = dict(run_contract, contract_sha256=contract_sha, input_sha256_observed=pins)
    if contract_sha != CONTRACT_SHA256:
        # A v1.2 contract also carries the pin table for the files this run opened, so no artifact in the
        # run directory names only the frozen 116-119 panel. On a v1.1 run the two tables are equal and
        # contract.json stays byte-identical to the frozen one.
        written_contract['frozen_contract_sha256'] = CONTRACT_SHA256
        written_contract['input_sha256_consumed'] = consumed_pins
    save(OUT / 'contract.json', written_contract)
    (OUT / 'CONTRACT.md').write_text(
        contract_markdown(contract_sha, bill_panel_used, run_contract, CONTRACT_SHA256), encoding='utf-8')
    stored_composite = {(r['actor'], r['target']): r for r in read_json(REGRESSION / 'features.json')['composite']}
    if len(cases) != 29 or sum(c['y'] for c in cases) != 20:
        raise ValueError('The pinned label file is not the 29-dyad development set')
    static = static_rows(cases, members, stored_composite, volume_counts(members, bills))

    results, same_fit, timings, notes = {}, {}, {}, []

    def record(name, result, seconds, spec_label, names, signatures, timing, used, note, feature_rows):
        same_fit[name] = result
        timings[name] = seconds
        results[name] = dict(spec_label=spec_label, features=len(names), feature_names=names,
                             signatures=signatures, timing=timing, dyads=len(used),
                             positive=sum(c['y'] for c in used), negative=sum(1 - c['y'] for c in used),
                             comparisons=result['comparisons'], expected_comparisons=result['expected_comparisons'],
                             auc=result['auc'], unique_fits=result['unique_fits'], wall_seconds=seconds,
                             note=note, coverage=missing_report(used, feature_rows, names))

    # REF first: it needs no new work panel and it proves the validation loop wiring.
    print('REF: reproducing the stored personality-context R0 row', flush=True)
    reference_rows = {(r['actor'], r['target']): r for r in read_json(PERSONALITY / 'features.json')}
    reference_names = PERSONALITY_MODELS['R0_main_effects']
    ref, ref_seconds = run_same_fit('REF', cases, reference_rows, reference_names, run_id,
                                    note='stored personality_context feature matrix')
    stored_ref = read_json(PERSONALITY / 'same_fit_auc.json')['R0_main_effects']
    stored_pair = (round(stored_ref['auc'] * stored_ref['comparisons']), stored_ref['comparisons'])
    recomputed = (round(ref['auc'] * ref['comparisons']), ref['comparisons'])
    reference_ok = recomputed == stored_pair == REFERENCE_TARGET
    print(f'  REF reproduction: recomputed {recomputed[0]}/{recomputed[1]}, '
          f'stored {stored_pair[0]}/{stored_pair[1]}, target {REFERENCE_TARGET[0]}/{REFERENCE_TARGET[1]}, '
          f'exact={reference_ok}', flush=True)
    if not reference_ok:
        event('benchmark_row', 'failed', 'REF did not reproduce the stored 164/180 row', run_id, stage='REF',
              metadata=dict(recomputed=list(recomputed), stored=list(stored_pair), target=list(REFERENCE_TARGET)))
        raise RuntimeError(f'Wiring check failed: recomputed {recomputed}, stored {stored_pair}, '
                           f'target {REFERENCE_TARGET}')
    record('REF', ref, ref_seconds, 'personality_context R0_main_effects', reference_names,
           'all (stored matrix)', 'all_history (stored matrix)', cases,
           f'wiring check: recomputed {recomputed[0]}/{recomputed[1]} = stored {stored_pair[0]}/{stored_pair[1]}',
           reference_rows)

    floor, floor_seconds = run_same_fit('F1', cases, static, FLOOR, run_id, note='nuisance floor')
    record('F1', floor, floor_seconds, 'FLOOR', FLOOR, 'original (volume only)', 'not date-cut', cases,
           'nuisance floor; contains no dyadic work quantity', static)

    panels = {}
    for policy, timing in (('original', 'strict_before'), ('original', 'all_history'), ('all', 'all_history')):
        rows, audit = cached_work(members, bills, cases, policy, timing, args.rebuild_work, run_id)
        panels[(policy, timing)] = (merge_rows(static, rows), rows, audit)
    canonical_rows, canonical_work, _ = panels[('original', 'strict_before')]
    history_rows = panels[('original', 'all_history')][0]
    signature_rows = panels[('all', 'all_history')][0]

    result, seconds = run_same_fit('C1', cases, canonical_rows, R0_NOVIS, run_id, note='canonical')
    record('C1', result, seconds, 'R0_novis', R0_NOVIS, 'original', 'strict_before', cases,
           'canonical benchmark row', canonical_rows)

    result, seconds = run_same_fit('C2', cases, history_rows, R0_NOVIS, run_id)
    record('C2', result, seconds, 'R0_novis', R0_NOVIS, 'original', 'all_history', cases,
           'diagnostic: work measured after the documented event', history_rows)

    result, seconds = run_same_fit('C3', cases, signature_rows, R0_NOVIS, run_id)
    record('C3', result, seconds, 'R0_novis', R0_NOVIS, 'all', 'all_history', cases,
           'diagnostic: any cosponsor signature, measured after the documented event', signature_rows)

    result, seconds = run_same_fit('D1', cases, canonical_rows, R0, run_id)
    record('D1', result, seconds, 'R0', R0, 'original', 'strict_before', cases,
           'diagnostic: canonical plus the four visibility features', canonical_rows)

    result, seconds = run_same_fit('D2', cases, signature_rows, R0, run_id)
    record('D2', result, seconds, 'R0', R0, 'all', 'all_history', cases,
           'diagnostic: nearest rebuild of the stored 164/180 row', signature_rows)

    early = [i for i, c in enumerate(cases) if c['first'] < coverage_start]
    s1_cases = [c for i, c in enumerate(cases) if i not in set(early)]
    result, seconds = run_same_fit('S1', s1_cases, canonical_rows, R0_NOVIS, run_id)
    record('S1', result, seconds, 'R0_novis', R0_NOVIS, 'original', 'strict_before', s1_cases,
           f'drops the {len(early)} dyads whose first documented event predates {coverage_start}', canonical_rows)

    def no_opportunity(case):
        return all(canonical_work[(a, b)].get('opportunities_a_to_b') is None
                   and canonical_work[(a, b)].get('opportunities_b_to_a') is None for a, b in case['directions'])

    structural = [i for i, c in enumerate(cases) if no_opportunity(c) and all(
        canonical_work[(a, b)].get('work_status') == 'cross_chamber_structurally_unavailable'
        for a, b in c['directions'])]
    s2_cases = [c for i, c in enumerate(cases) if i not in set(structural)]
    result, seconds = run_same_fit('S2', s2_cases, canonical_rows, R0_NOVIS, run_id)
    record('S2', result, seconds, 'R0_novis', R0_NOVIS, 'original', 'strict_before', s2_cases,
           f'drops the {len(structural)} dyads with no opportunity count in either direction because the work '
           'builder reports the layer structurally unavailable', canonical_rows)

    no_work = [i for i, c in enumerate(cases) if no_opportunity(c)]
    s2b_cases = [c for i, c in enumerate(cases) if i not in set(no_work)]
    result, seconds = run_same_fit('S2b', s2b_cases, canonical_rows, R0_NOVIS, run_id)
    record('S2b', result, seconds, 'R0_novis', R0_NOVIS, 'original', 'strict_before', s2b_cases,
           f'added row, not in the requested list: drops all {len(no_work)} dyads with no eligible bill under the '
           'canonical build', canonical_rows)

    result, seconds = run_same_fit('F1b', s2b_cases, static, FLOOR, run_id, note='floor on the measurable subset')
    record('F1b', result, seconds, 'FLOOR', FLOOR, 'original (volume only)', 'not date-cut', s2b_cases,
           'added row, not in the requested list: the nuisance floor on the S2b dyad set, the only like-for-like '
           'comparison with S2b', static)

    # Bootstrap intervals and paired differences against the canonical row.
    canonical_grid, positive, negative = concordance_grid(cases, same_fit['C1'])
    shared = bootstrap_draws(len(positive), len(negative), args.bootstrap)
    canonical_boot = bootstrap_auc(canonical_grid, shared)
    subsets = {'S1': s1_cases, 'S2': s2_cases, 'S2b': s2b_cases, 'F1b': s2b_cases}
    for name, row in results.items():
        if name in subsets:
            grid, p, n = concordance_grid(subsets[name], same_fit[name])
            row['ci'] = interval(bootstrap_auc(grid, bootstrap_draws(len(p), len(n), args.bootstrap)))
            row['diff_vs_C1'] = None
            row['diff_unavailable'] = 'different dyad set'
            continue
        grid, _, _ = concordance_grid(cases, same_fit[name])
        boot = bootstrap_auc(grid, shared)
        row['ci'] = interval(boot)
        if name == 'C1':
            row['diff_vs_C1'] = None
            row['diff_unavailable'] = 'canonical row'
            continue
        diff = boot - canonical_boot
        low, mid, high = np.percentile(diff, [2.5, 50, 97.5])
        row['diff_vs_C1'] = dict(point=row['auc'] - results['C1']['auc'], low=float(low), median=float(mid),
                                 high=float(high), fraction_above_zero=float(np.mean(diff > 0)),
                                 replicates=int(args.bootstrap))

    # The one like-for-like contrast: work specification against the floor on identical dyads.
    subset_grid, subset_positive, subset_negative = concordance_grid(s2b_cases, same_fit['S2b'])
    subset_draws = bootstrap_draws(len(subset_positive), len(subset_negative), args.bootstrap)
    subset_diff = (bootstrap_auc(subset_grid, subset_draws)
                   - bootstrap_auc(concordance_grid(s2b_cases, same_fit['F1b'])[0], subset_draws))
    low, mid, high = np.percentile(subset_diff, [2.5, 50, 97.5])
    measurable = dict(rows=['S2b', 'F1b'], dyads=len(s2b_cases),
                      comparisons=results['S2b']['comparisons'],
                      point=results['S2b']['auc'] - results['F1b']['auc'],
                      low=float(low), median=float(mid), high=float(high),
                      fraction_above_zero=float(np.mean(subset_diff > 0)), replicates=int(args.bootstrap),
                      caveat=CONTRACT['subset_comparison'])
    print(f"S2b minus F1b on the {len(s2b_cases)} measurable dyads: {measurable['point']:+.4f} "
          f"[{low:+.4f}, {high:+.4f}], frac>0 {measurable['fraction_above_zero']:.4f}", flush=True)

    strata = chamber_strata(cases, canonical_work)
    shape = stratum_shape(cases, strata)
    available = distinct_permutations(cases, strata)
    print(f'Permutation strata {json.dumps(shape)}; {available:,} distinct label assignments', flush=True)
    if args.permutations > 0:
        null = permutation_null(cases, canonical_rows, R0_NOVIS, strata, results['C1']['auc'],
                                args.permutations, args.max_minutes, run_id)
    else:
        null = summarise_null([], results['C1']['auc'], 0, time.time(), False)
        null['reason'] = 'not requested (--permutations 0)'
    null.update(strata=shape, distinct_label_assignments=available, max_minutes=args.max_minutes,
                strata_definition=CONTRACT['metrics']['permutation_null']['strata'])
    save(OUT / 'null_distribution.json', null)

    notes.append(f'C1 has {len(no_work)} of {len(cases)} dyads with no eligible bill in either direction, so every '
                 f'bill-derived work feature is missing for them: {len(structural)} because the two members sat in '
                 f'different chambers on the assessment date and {len(early)} because the documented event predates '
                 f'the {coverage_start} panel start (dyad indices {sorted(set(structural) | set(early))}). Those '
                 f'{len(early)} still carry a dated co_service_years; the {len(structural)} cross-chamber dyads '
                 'carry no work value at all.')
    notes.append('Dyads with no observed work value at all, by row: ' + ', '.join(
        f"{n} {len(results[n]['coverage']['dyads_with_no_observed_work_feature'])}/{results[n]['dyads']}"
        for n in ROW_ORDER) + '. A row measured on more dyads is not measured on the same evidence as C1, so a '
        'difference between rows carries a coverage difference as well as a specification difference.')
    notes.append(f'F1 and C1 share a denominator but not a coverage level: F1 has complete data on all '
                 f'{len(cases)} dyads while C1 has {len(no_work)} dyads with no bill-derived work value. F1b is the '
                 'like-for-like floor, run on the S2b dyad set.')
    notes.append(f'The requested S1 rule "first < {coverage_start}" selects {len(early)} dyads '
                 f'{[cases[i]["names"] for i in early]}, not the four named in the build request. The rule was '
                 'followed as written and the discrepancy is reported rather than resolved here.')
    if coverage_start != COVERAGE_START:
        # Only a run whose panel does not start where the frozen v1.1 panel starts needs this said out
        # loud; on the default flags the note list stays exactly as the frozen report has it.
        notes.append(f'The S1 threshold and the panel-start figures above are {coverage_start}, not the frozen '
                     f'v1.1 {COVERAGE_START}: this run\'s coverage start is derived as the {coverage["rule"]} '
                     f'({coverage["basis"]}; {coverage["formula"]}). The earliest introduction date actually '
                     f'present in the loaded panel is {coverage["earliest_introduced_in_panel"]}, which '
                     f'{"agrees with" if coverage["agrees_with_earliest_introduced"] else "differs from"} the '
                     'derived value. Contract version '
                     f'{contract_version}, contract sha256 {contract_sha}, frozen v1.1 {CONTRACT_SHA256}.')
    notes.append('D2 is the nearest rebuild of the stored 164/180 row and is not expected to equal it: the dated '
                 'chamber-layered builder leaves cross-chamber dyads structurally missing, uses introduction-day '
                 'eligibility, substitutes dated co_service_years for co_service_congresses and a dated '
                 f'bipartisan_pair for the all-history one, and cuts at {ALL_HISTORY_CUTOFF}.')
    notes.append('REF is the wiring check. It is computed from the stored personality-context feature matrix, not '
                 'from this benchmark\'s work builder, so it isolates the validation loop from the feature build.')
    notes.append('Rows S1, S2, S2b and F1b are computed on reduced dyad sets, so their comparison denominators '
                 'differ from C1 and no paired difference against C1 is defined for them. S2b and F1b share one '
                 'dyad set, so the difference between those two is defined and is reported separately.')

    save(OUT / 'same_fit_rows.json', same_fit)
    save(OUT / 'results.json', dict(
        rows=results, canonical='C1', mode=MODE, bootstrap_replicates=args.bootstrap, seed=SEED,
        contract_sha256=contract_sha, reference_reproduced=reference_ok,
        reference_recomputed=list(recomputed), reference_stored=list(stored_pair),
        early_coverage_dyads=[dict(index=i, names=cases[i]['names'], first=cases[i]['first']) for i in early],
        structurally_unavailable_dyads=[dict(index=i, names=cases[i]['names']) for i in structural],
        no_eligible_bill_dyads=[dict(index=i, names=cases[i]['names']) for i in no_work],
        permutation_strata=shape, measurable_subset_comparison=measurable, notes=notes))
    (OUT / 'REPORT.md').write_text(
        report_text(results, null, contract_sha, cases, shape, available, notes, measurable), encoding='utf-8')

    artifacts = {p.name: digest(p) for p in sorted(OUT.iterdir())
                 if p.is_file() and p.name != 'run_receipt.json'}
    consumed = consumed_pins
    save(OUT / 'run_receipt.json', dict(
        finished_utc=datetime.now(timezone.utc).isoformat(), run_id=run_id, wall_seconds=time.time() - started,
        contract_sha256=contract_sha, contract_version=contract_version, frozen_contract_sha256=CONTRACT_SHA256,
        code_sha256=digest(__file__), python=sys.version, numpy=np.__version__,
        mode=MODE, seed=SEED, bootstrap=args.bootstrap, permutations_requested=args.permutations,
        permutations_completed=null['permutations_completed'], max_minutes=args.max_minutes,
        input_sha256=consumed, row_wall_seconds=timings, reference_reproduced=reference_ok,
        input_sha256_note=('input_sha256 lists the files this run read: the bill panel entry is the panel named '
                           'by --bills, not the frozen 116-119 panel. frozen_input_pins_v1_1 is the pinned v1.1 '
                           'table verify_pins() checked for drift, kept for comparison.'),
        frozen_input_pins_v1_1=pins, input_pins_differ_from_frozen=consumed != pins,
        coverage_start=coverage_start, coverage_start_derivation=coverage,
        development_only=True, held_out_split_touched=False, artifacts=artifacts,
        bills_path=str(bills_path), bills_sha256=bills_sha256, congress_range=list(args.congress_range),
        bills_source_records=bills_audit['source_records'], bills_included_records=bills_audit['included_bills'],
        bills_by_congress=bills_audit['bills_by_congress']))
    event('benchmark_contract', 'ok',
          f'benchmark complete; C1 {fraction(results["C1"]["auc"], results["C1"]["comparisons"])}', run_id,
          stage='finish', duration_ms=(time.time() - started) * 1000,
          metadata=dict(rows=ROW_ORDER, reference_reproduced=reference_ok, canonical_auc=results['C1']['auc'],
                        permutations_completed=null['permutations_completed']))
    print(f'Wrote {OUT}', flush=True)


if __name__ == '__main__':
    main()
