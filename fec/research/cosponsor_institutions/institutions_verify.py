"""Independent post-freeze verification; no fitting and one artifact at a time.

Run only after institutional results AND statistics are frozen.  Writes only
verification_receipt.json, and refuses to overwrite that receipt.
"""
from __future__ import annotations

import datetime as dt
import gc
import hashlib
import json
import os
import sys
from pathlib import Path

for _key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_key] = '2'
import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

import institutions_models as models
from institutions_common import OUT, OLD, UNIVERSE, REFINEMENT, CODE
import universe_verify as independent_helpers
from universe_verify import CHECKS, check, close, sha, read, manual_metrics, summary, compare_summary
sys.path.append(str(CODE.parents[1]))  # fec/, for lane_file_io
from lane_file_io import safe_to_unpickle  # noqa: E402

RECEIPT = OUT / 'verification_receipt.json'


def declared_sources(value):
    """Collect concrete file/hash pairs without executing any source producer."""
    result = {}
    if isinstance(value, dict):
        for key, path in value.items():
            if key.endswith('path') and isinstance(path, str):
                hash_key = key[:-4] + 'sha256'
                if hash_key in value and isinstance(value[hash_key], str):
                    if Path(path).is_file():
                        result[str(Path(path).resolve())] = value[hash_key]
                    else:
                        check('receipt_declared_path_exists:' + path, False)
        for item in value.values():
            result.update(declared_sources(item))
    elif isinstance(value, list):
        for item in value:
            result.update(declared_sources(item))
    return result


def verify_bindings(plan, selection, result, stat_plan, stat):
    check('selection_frozen', bool(selection.get('frozen_utc')))
    check('selection_plan_binding', selection['plan_sha256'] == sha(OUT / 'institutions_plan.json'))
    check('results_selection_binding', result['selection_sha256'] == sha(OUT / 'institutions_selection.json'))
    check('statistics_selection_binding', stat_plan['selection_sha256'] == sha(OUT / 'institutions_selection.json'))
    check('statistics_model_plan_binding', stat_plan['model_plan_sha256'] == sha(OUT / 'institutions_plan.json'))
    check('protocol_binding', plan['protocol_sha256'] == sha(CODE / 'PROTOCOL.md'))
    check('model_code_binding', plan['model_code_sha256'] == sha(models.__file__))
    check('statistics_code_binding', stat_plan['code_sha256'] == sha(CODE / 'institutions_statistics.py'))
    timeline = [plan['created_utc'], selection['frozen_utc'], result['assessment_started_utc'],
                result['completed_utc'], stat_plan['created_utc'], stat['completed_utc']]
    check('freeze_before_2024_assessment', timeline == sorted(timeline), timeline)
    for name, expected in plan['supporting_code_sha256'].items():
        check('supporting_code:' + name, sha(CODE / name) == expected)
    for key in ('dependency_code_sha256', 'frozen_feature_inputs_sha256', 'input_sha256',
                'receipt_declared_source_sha256', 'prior_bindings'):
        for path, expected in plan[key].items():
            check(key + ':' + path, sha(path) == expected)
    prior_verification = read(UNIVERSE / 'verification_receipt.json')
    check('prior_verifier_helper_code', sha(independent_helpers.__file__) == prior_verification['verifier_code_sha256'])
    check('prior_verification_passed', prior_verification['status'] == 'PASS')
    check('live_menu_matches_plan', models.menu() == plan['models'])
    check('all_models_frozen', set(plan['models']) == set(selection['models']) == set(result['models']))
    pairs = plan['pairs']
    check('pairs_match_statistics', pairs == stat_plan['pairs'])
    check('pairs_match_live_prespecification', pairs == [list(p) for p in models.comparison_pairs(plan['models'])])
    check('comparison_counts', len(pairs) == stat_plan['comparisons'] == stat['comparisons'])
    check('unordered_comparisons_unique', len({frozenset(p) for p in pairs}) == len(pairs))
    check('no_self_comparisons', all(len(set(p)) == 2 for p in pairs))
    winner = max((n for n, spec in plan['models'].items() if spec['eligible']),
                 key=lambda n: selection['models'][n]['selection_2023']['precision_at_8'])
    check('2023_only_winner', winner == selection['chosen'] == result['chosen_on_2023'] == stat['chosen_on_2023'])
    receipts, groups = models.feature_groups()
    sensitivity = set(groups['committee_sensitivity'])
    for name, spec in plan['models'].items():
        if spec['eligible']:
            check('sensitivity_excluded_from_eligible:' + name, not sensitivity.intersection(spec['features']))
    if sensitivity:
        check('sensitivity_model_ineligible', not plan['models']['institution_hearing_sensitivity']['eligible'])
    all_declared = {}
    for family, receipt in receipts.items():
        check('feature_names_unique:' + family, len(receipt['features']) == len(set(receipt['features'])))
        for path, expected in declared_sources(receipt).items():
            check('source_receipt:' + path, sha(path) == expected)
            all_declared[path] = expected
        for cg in (117, 118):
            shape = (len(pd.read_parquet(OLD / f'meta_{cg}.parquet', columns=['member'])), len(receipt['features']))
            path = OUT / f'{family}_{cg}.f32'
            check(f'{family}_{cg}:full_panel_bytes', path.stat().st_size == int(np.prod(shape))*4)
    for name in models.REFERENCES:
        ref = plan['references'][name]
        for folder, suffix, key in [('predictions', 'npy', 'prediction_sha256'), ('models', 'joblib', 'model_sha256')]:
            check('reference_original:' + folder + ':' + name, sha(UNIVERSE / f'{folder}/{name}.{suffix}') == ref[key])
            check('reference_copy:' + folder + ':' + name, sha(OUT / f'{folder}/{name}.{suffix}') == ref[key])
    return winner, all_declared


def extra_metrics(frame, probabilities, reported, name):
    """AP/AUC from grouped ties and calibration-bin arithmetic, not metric helpers."""
    values = np.asarray(probabilities)
    scores = np.clip(values.astype(np.float64), 1e-8, 1-1e-8)
    grouped = pd.DataFrame({'p': scores, 'y': frame.y.to_numpy()}).groupby('p', sort=True).y.agg(['sum', 'size'])
    pos = grouped['sum'].to_numpy(dtype=np.float64)
    neg = grouped['size'].to_numpy(dtype=np.float64) - pos
    auc = np.sum(pos * (np.cumsum(neg)-neg + .5*neg)) / (pos.sum()*neg.sum())
    pdesc, ndesc = pos[::-1], grouped['size'].to_numpy(dtype=np.float64)[::-1]
    ap = np.sum(pdesc * np.cumsum(pdesc)/np.cumsum(ndesc))/pdesc.sum()
    close(float(ap), reported['average_precision'], name + ':average_precision')
    close(float(auc), reported['roc_auc'], name + ':roc_auc')
    # digitize uses float64 bin edges; compare at that precision instead of
    # rounding a Python boundary to float32 (e.g. float32(.01) is below .01).
    unrounded = values.astype(np.float64)
    for i, entry in enumerate(reported.get('calibration', [])):
        mask = (unrounded >= entry['low']) & (unrounded < entry['high'])
        close(int(mask.sum()), entry['rows'], name + f':calibration_{i}_rows')
        close(float(values[mask].mean()), entry['predicted'], name + f':calibration_{i}_predicted', atol=1e-7)
        close(float(frame.y.to_numpy()[mask].mean()), entry['observed'], name + f':calibration_{i}_observed')
    return {'average_precision': float(ap), 'roc_auc': float(auc)}


def run():
    if RECEIPT.exists():
        raise RuntimeError('Verification receipt already frozen; do not overwrite')
    files = ['institutions_plan.json', 'institutions_selection.json', 'institutions_results.json',
             'institutions_statistics_plan.json', 'institutions_statistics.json']
    if not all((OUT / name).is_file() for name in files):
        raise RuntimeError('Wait until results, selection and statistics are frozen')
    began = dt.datetime.now(dt.timezone.utc).isoformat()
    plan, selection, result, stat_plan, stat = [read(OUT / name) for name in files]
    protected = [OUT / name for name in files]
    protected += [UNIVERSE / name for name in ['universe_plan.json', 'universe_selection.json',
                 'universe_results.json', 'universe_statistics.json', 'verification_receipt.json', 'experiment_manifest.json']]
    protected += [p for p in (REFINEMENT / 'prospective_20260905').iterdir() if p.is_file()]
    before = {str(p): sha(p) for p in protected}
    chosen, declared = verify_bindings(plan, selection, result, stat_plan, stat)
    prospective = independent_helpers.prospective_bindings()
    ids = read(OLD / 'identifiers.json')['members']
    gold = set(read(UNIVERSE / 'gold_cohort.json')['member_ids'])
    check('gold377', len(gold) == 377)
    tm = pd.read_parquet(OLD / 'meta_117.parquet', columns=['member', 'mature', 'y'])
    member_gold = np.array([mid in gold for mid in ids])
    train_gold = member_gold[tm.member.to_numpy()]
    eligible = tm.mature.to_numpy().astype(bool) & train_gold
    y = tm.y.to_numpy()
    selected = eligible & ((y > 0) | (np.random.default_rng(models.SEED+117).random(len(tm)) < .1))
    ti = np.flatnonzero(selected)
    train = {'rows': len(ti), 'events': int(y[ti].sum()),
             'indices_sha256': hashlib.sha256(ti.astype('<i8').tobytes()).hexdigest()}
    check('training_exact_sample', train['rows'] == selection['training_rows'] == 214132 and
          train['events'] == selection['training_events'] == 6529)
    check('training_index_binding', train['indices_sha256'] == selection['training_original_indices_sha256'])
    previous_sample = read(UNIVERSE / 'gold_model_review.json')['behavioral_test_run']['panels']['117']['sample_indices_sha256']
    check('training_same_as_references', train['indices_sha256'] == previous_sample)
    check('only_mature_gold_training', bool(eligible[ti].all()))
    check('all_eligible_training_positives_retained', bool(selected[eligible & (y > 0)].all()))
    del tm, train_gold, eligible, y, selected, ti
    panel = models.Panel(118)
    direct_gold = member_gold[panel.meta.member.to_numpy()]
    check('panel_cohort_mask', np.array_equal(panel.gold, direct_gold))
    original = np.flatnonzero(panel.meta.mature.to_numpy().astype(bool) & direct_gold)
    check('evaluation_original_index_binding', hashlib.sha256(original.astype('<i8').tobytes()).hexdigest() == selection['evaluation_original_indices_sha256'])
    meta = panel.meta.iloc[original][['bill', 'member', 'group', 'day', 'y', 'senate', 'democrat']].reset_index(drop=True)
    check('all_scored_members_gold', {ids[int(code)] for code in meta.member.unique()} == gold)
    early = meta.day.to_numpy() < models.EARLY_END
    me, ml = meta[early].reset_index(drop=True), meta[~early].reset_index(drop=True)
    check('exact_evaluation_rows', (len(meta), len(me), len(ml)) == (2907161, 1858229, 1048932))
    positions = np.sort(np.random.default_rng(905634).choice(len(meta), 2000, replace=False))
    source_indices = original[positions]
    check('reprediction_only_gold_original_rows', bool(panel.gold[source_indices].all()))
    for family, receipt in models.feature_groups()[0].items():
        raw = np.memmap(OUT / f'{family}_118.f32', dtype='float32', mode='r', shape=(len(panel.meta), len(receipt['features'])))
        check('full_index_design:' + family, np.array_equal(panel.design(source_indices, receipt['features']), raw[source_indices]))
        del raw
    per_model = {}
    for name, spec in plan['models'].items():
        pp, mp = OUT / f'predictions/{name}.npy', OUT / f'models/{name}.joblib'
        frozen = selection['models'][name]
        check(name + ':prediction_hash', sha(pp) == frozen['prediction_sha256'])
        check(name + ':model_hash', sha(mp) == frozen['model_sha256'])
        probabilities = np.load(pp, mmap_mode='r')
        check(name + ':prediction_length', probabilities.ndim == 1 and len(probabilities) == len(meta))
        check(name + ':probability_range', bool(np.isfinite(probabilities).all() and ((probabilities >= 0) & (probabilities <= 1)).all()))
        if not safe_to_unpickle(mp):
            raise SystemExit(f'refusing to unpickle {mp}: it fails its integrity sidecar')
        artifact = joblib.load(mp)
        for key in ('kind', 'features'):
            check(name + ':artifact_' + key, artifact[key] == spec[key])
        check(name + ':no_placebo', artifact.get('placebo', False) is False)
        cal = artifact['calibration_2023']
        check(name + ':monotone_calibration', np.isfinite([cal['slope'], cal['intercept']]).all() and cal['slope'] >= 0)
        raw = models.previous.predict(artifact, panel, source_indices)
        # Apply calibration separately from the production calibrate helper.
        bounded = np.clip(raw, 1e-7, 1-1e-7)
        linear = cal['intercept'] + cal['slope']*(np.log(bounded)-np.log1p(-bounded))
        reproduced = (1/(1+np.exp(-linear))).astype(np.float32)
        error = float(np.max(np.abs(reproduced.astype(float)-probabilities[positions].astype(float))))
        check(name + ':sample_reprediction', error <= 2e-6, error)
        a23, top23 = manual_metrics(me, probabilities[early], result['models'][name]['year_2023'], name + ':2023')
        a24, top24 = manual_metrics(ml, probabilities[~early], result['models'][name]['year_2024'], name + ':2024')
        a23.update(extra_metrics(me, probabilities[early], result['models'][name]['year_2023'], name + ':2023'))
        a24.update(extra_metrics(ml, probabilities[~early], result['models'][name]['year_2024'], name + ':2024'))
        close(a23['precision_at_8'], frozen['selection_2023']['precision_at_8'], name + ':selection_precision')
        ranked = top24.sort_values(['probability', 'group', 'member'], ascending=[False, True, True], kind='mergesort')
        total = int(ml.y.sum())
        for count in (250, 500, 1000, 2000, 5000):
            compare_summary(summary(ranked.head(count), total), stat['matched_retained_counts'][str(count)][name], name + f':matched_{count}')
        for row in stat['selective'][name]:
            fraction = row['target_fraction_2023']
            cutoff = float(np.quantile(top23.probability.to_numpy(), 1-fraction))
            close(cutoff, row['cutoff_2023'], name + f':cutoff_{fraction}', atol=1e-7)
            compare_summary(summary(top24[top24.probability >= row['cutoff_2023']], total), row, name + f':selective_{fraction}')
        masks = {'House': ml.senate.eq(0), 'Senate': ml.senate.eq(1), 'Democratic': ml.democrat.eq(1), 'non_Democratic': ml.democrat.eq(0)}
        for label, mask in masks.items():
            picked = top24.loc[top24.index.intersection(ml.index[mask])]
            expected = stat['strata'][name][label]
            compare_summary(summary(picked, int(ml.loc[mask, 'y'].sum())), expected, name + ':stratum_' + label)
            close(int(mask.sum()), expected['candidate_rows'], name + ':stratum_rows_' + label)
            close(int(ml.loc[mask, 'y'].sum()), expected['candidate_events'], name + ':stratum_events_' + label)
        per_model[name] = {'reprediction_rows': len(positions), 'reprediction_max_absolute_error': error,
                           'year_2023': a23, 'year_2024': a24,
                           'prediction_sha256': frozen['prediction_sha256'], 'model_sha256': frozen['model_sha256']}
        print(f'Verified {name}: sampled predictions and independent full-period metrics/counts match', flush=True)
        del artifact, probabilities, raw, reproduced, top23, top24, ranked
        gc.collect()
    for challenger, baseline in stat_plan['pairs']:
        left, right = per_model[challenger]['year_2024'], per_model[baseline]['year_2024']
        expected = stat['paired'][challenger + ' vs ' + baseline]
        label = challenger + ':' + baseline
        check('paired_budget:' + label, left['slots_at_8'] == right['slots_at_8'])
        close(left['hits_at_8']-right['hits_at_8'], expected['extra_hits'], 'paired_hits:' + label)
        close((left['hits_at_8']-right['hits_at_8'])/right['slots_at_8'], expected['delta_precision'], 'paired_precision:' + label)
        close(left['brier']-right['brier'], expected['delta_brier'], 'paired_brier:' + label)
        for ordinary, adjusted in [('ci95', 'adjusted_interval'), ('brier_ci95', 'brier_adjusted_interval')]:
            lo, hi = expected[ordinary]
            alo, ahi = expected[adjusted]
            check('interval_order:' + ordinary + ':' + label, np.isfinite([lo, hi, alo, ahi]).all() and alo <= lo <= hi <= ahi)
    close(len(ml), stat['rows_2024'], 'statistics_rows')
    close(int(ml.y.sum()), stat['events_2024'], 'statistics_events')
    close(int(ml.groupby('group').y.sum().clip(upper=8).sum()), stat['forced_top8_oracle']['hits'], 'oracle_hits')
    after = {str(p): sha(p) for p in protected}
    check('sealed_artifacts_and_prospective_snapshots_unchanged', before == after)
    for path, expected in declared.items():
        check('source_unchanged_after_verification:' + path, sha(path) == expected)
    output = {'schema': 'institutions-independent-verification-v1', 'status': 'PASS',
              'started_utc': began, 'completed_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'verifier_code_sha256': sha(__file__), 'pure_helper_code_sha256': sha(independent_helpers.__file__),
              'chosen_on_2023': chosen, 'cohort_members': len(gold), 'training_sample': train,
              'validation_rows': len(meta), 'selection_rows_2023': len(me), 'assessment_rows_2024': len(ml),
              'reprediction_original_indices_sha256': hashlib.sha256(source_indices.astype('<i8').tobytes()).hexdigest(),
              'models': per_model, 'checks': CHECKS, 'check_count': len(CHECKS),
              'protected_before': before, 'protected_after': after, 'prospective_manifest_bindings': prospective,
              'limitations': ['No model refitted; existing model predictions reproduced on 2,000 original gold row indices each.',
                  'Independent pandas ranking/counts, grouped-tie AP/AUC, calibration bins, Brier/log loss and paired point differences checked; bootstrap intervals not independently rerun.',
                  'Both assessment years remain continuing-member development; intervals do not repair prior search, source availability or survivor selection.',
                  'Congress119 prospective files checked by hashes only; no Congress119 outcomes loaded.']}
    RECEIPT.write_text(json.dumps(output, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'checks': len(CHECKS), 'models': len(per_model), 'receipt': str(RECEIPT)}), flush=True)


if __name__ == '__main__':
    with threadpool_limits(limits=2):
        run()
