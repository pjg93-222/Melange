"""Matched institutional evidence comparisons; earlier artifacts are read-only."""
import gc
import shutil
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from institutions_common import CODE, OUT, OLD, UNIVERSE, digest, read_json, write_json, log, stamp
import universe_models as previous
from universe_models import EARLY_END, SEED, COV, NETWORK, ACTIVITY
from run_models import metrics, platt_fit, calibrate

REFERENCES = ['boosted_activity', 'boosted_network', 'boosted_context', 'boosted_universe']
BACKBONE = 'institution_backbone'
ALL = 'institution_all'


def unique(items):
    return list(dict.fromkeys(items))


def feature_groups():
    receipts = {k: read_json(OUT / f'{k}_receipt.json') for k in ['caucus', 'committees', 'votes']}
    groups = {k: list(r['features']) for k, r in receipts.items()}
    cg = receipts['committees'].get('feature_groups', {})
    sensitivity = list(cg.get('hearing_event_reconstruction_sensitivity_only', []))
    assert list(cg['primary']) == [f for f in groups['committees'] if f not in sensitivity]
    groups['committee_sensitivity'] = sensitivity
    groups['committees'] = [f for f in groups['committees'] if f not in sensitivity]
    groups['caucus_leadership'] = list(receipts['caucus'].get('feature_groups', {}).get('leadership', groups['caucus']))
    groups['caucus_membership'] = list(receipts['caucus'].get('feature_groups', {}).get('membership', []))
    return receipts, groups


def menu():
    _, g = feature_groups()
    base = unique(COV + NETWORK + ACTIVITY)
    blocks = {
        BACKBONE: [],
        'institution_votes': g['votes'],
        'institution_committees': g['committees'],
        'institution_caucus': g['caucus'],
        'institution_votes_committees': g['votes'] + g['committees'],
        'institution_votes_caucus': g['votes'] + g['caucus'],
        'institution_committees_caucus': g['committees'] + g['caucus'],
        ALL: g['votes'] + g['committees'] + g['caucus'],
    }
    specs = {n: dict(kind='boosted', features=unique(base + f), role='new', eligible=True,
                     source_qualification='conditional_institutional_reconstruction') for n, f in blocks.items()}
    for n, source in [('institution_logistic_backbone', BACKBONE), ('institution_logistic_all', ALL)]:
        specs[n] = {**specs[source], 'kind': 'logistic'}
    oldplan = read_json(UNIVERSE / 'universe_plan.json')
    specs['institution_universe_all'] = dict(kind='boosted',
        features=unique(oldplan['models']['boosted_universe']['features'] + blocks[ALL]), role='new', eligible=True,
        source_qualification='conditional_institutional_and_prior_universe')
    if g['caucus_membership']:
        specs['institution_caucus_leadership'] = dict(kind='boosted', features=unique(base + g['caucus_leadership']),
            role='new', eligible=True, source_qualification='prior_caucus_officer_evidence_only')
    if g['committee_sensitivity']:
        specs['institution_hearing_sensitivity'] = dict(kind='boosted',
            features=unique(specs[ALL]['features'] + g['committee_sensitivity']), role='new', eligible=False,
            source_qualification='hearing_event_reconstruction_operational_availability_unverified')
    for n in REFERENCES:
        specs[n] = dict(kind='boosted', features=oldplan['models'][n]['features'], role='frozen_reference', eligible=True,
                        source_qualification='same_cohort_frozen_reference')
    assert all(len(s['features']) == len(set(s['features'])) for s in specs.values())
    return specs


def comparison_pairs(specs):
    pairs = [(n, b) for n, s in specs.items() if s['role'] == 'new' for b in REFERENCES]
    pairs += [(n, BACKBONE) for n, s in specs.items() if s['role'] == 'new' and n != BACKBONE]
    pairs += [(ALL, n) for n in ['institution_votes_committees', 'institution_votes_caucus', 'institution_committees_caucus']]
    pairs += [(ALL, 'institution_logistic_all'), (BACKBONE, 'institution_logistic_backbone')]
    if 'institution_caucus_leadership' in specs:
        pairs += [('institution_caucus', 'institution_caucus_leadership')]
    if 'institution_hearing_sensitivity' in specs:
        pairs += [('institution_hearing_sensitivity', ALL)]
    result, seen = [], set()
    for pair in pairs:
        key = frozenset(pair)
        assert len(key) == 2
        if key not in seen:
            result.append(pair)
            seen.add(key)
    return result


class Panel(previous.Panel):
    def __init__(self, congress):
        super().__init__(congress)
        receipts, _ = feature_groups()
        for key, receipt in receipts.items():
            names = receipt['features']
            path = OUT / f'{key}_{congress}.f32'
            assert path.stat().st_size == len(self.meta) * len(names) * 4, path
            array = np.memmap(path, dtype='float32', mode='r', shape=(len(self.meta), len(names)))
            for j, name in enumerate(names):
                assert name not in self.columns and name not in self.static, name
                self.columns[name] = (array, j)


def sample_indices(panel):
    y = panel.meta.y.to_numpy()
    eligible = panel.meta.mature.to_numpy().astype(bool) & panel.gold
    selected = eligible & ((y > 0) | (np.random.default_rng(SEED + 117).random(len(y)) < .1))
    indices = np.flatnonzero(selected)
    return indices, y[indices], np.where(y[indices] > 0, 1., 10.)


def make_plan(specs):
    inputs = [OUT / f'{k}_receipt.json' for k in ['caucus', 'committees', 'votes']]
    inputs += [OUT / f'{k}_{cg}.f32' for k in ['caucus', 'committees', 'votes'] for cg in [117, 118]]
    # Bind every retained raw/normalized source sidecar available before fitting.
    inputs += [p for p in OUT.rglob('*') if p.is_file() and p not in inputs and
               (any(part.endswith('_sources') for part in p.parts) or
                p.name.startswith(('caucus_', 'committees_', 'votes_'))) and '__pycache__' not in p.parts]
    inputs += [OLD / 'analogue_links.json', OLD / 'bills.jsonl']
    declared = {}
    def bind_declared(value):
        if isinstance(value, dict):
            if isinstance(value.get('path'), str) and isinstance(value.get('sha256'), str):
                path = Path(value['path']).resolve()
                assert digest(path) == value['sha256'], path
                assert str(path) not in declared or declared[str(path)] == value['sha256'], path
                declared[str(path)] = value['sha256']
                inputs.append(path)
            for item in value.values():
                bind_declared(item)
        elif isinstance(value, list):
            for item in value:
                bind_declared(item)
    for key in ['caucus', 'committees', 'votes']:
        bind_declared(read_json(OUT / f'{key}_receipt.json'))
    import universe_statistics
    import paired_extensions
    deps = [previous, previous.build_panel, previous.run_models, previous.fit_extensions, universe_statistics, paired_extensions]
    oldplan = read_json(UNIVERSE / 'universe_plan.json')
    for f, expected in oldplan['supporting_code_sha256'].items():
        assert digest(CODE.parent / 'cosponsor_universe' / f) == expected, f
    assert digest(previous.__file__) == oldplan['code_sha256']
    frozen_inputs = {}
    reviewed = read_json(UNIVERSE / 'gold_model_review.json')['source_receipt_verification']['observed']
    for item in reviewed:
        path = Path(item['path'])
        if any(path.is_relative_to(folder) for folder in [OLD, UNIVERSE, previous.PREVIOUS]):
            assert digest(path) == item['expected_sha256'], path
            frozen_inputs[str(path)] = item['expected_sha256']
    plan = dict(created_utc=stamp(), models=specs, pairs=comparison_pairs(specs),
        training=117, selection=2023, assessment=2024, cohort_members=377,
        status='retrospective_continuing_member_development',
        boosted_config=dict(max_leaf_nodes=15, max_iter=200, learning_rate=.06, l2_regularization=10, min_samples_leaf=50),
        logistic_config=dict(C=1., max_iter=150, solver='newton-cholesky', tol=1e-7),
        protocol_sha256=digest(CODE / 'PROTOCOL.md'), model_code_sha256=digest(__file__),
        supporting_code_sha256={f: digest(CODE / f) for f in ['institutions_common.py', 'institutions_caucus.py',
            'institutions_committees.py', 'institutions_votes.py', 'institutions_statistics.py']},
        dependency_code_sha256={m.__file__: digest(m.__file__) for m in deps},
        frozen_feature_inputs_sha256=frozen_inputs,
        receipt_declared_source_sha256=declared,
        input_sha256={str(p.resolve()): digest(p) for p in sorted(set(inputs))},
        prior_bindings={str(UNIVERSE / f): digest(UNIVERSE / f) for f in
            ['experiment_manifest.json', 'universe_plan.json', 'universe_selection.json', 'universe_results.json', 'gold_cohort.json', 'gold_cohort.receipt.json']},
        references={n: dict(prediction_sha256=digest(UNIVERSE / f'predictions/{n}.npy'),
                            model_sha256=digest(UNIVERSE / f'models/{n}.joblib')) for n in REFERENCES})
    return plan


def run():
    if (OUT / 'institutions_results.json').exists():
        raise RuntimeError('Institutional evaluation already frozen')
    specs = menu()
    plan = make_plan(specs)
    plan_path = OUT / 'institutions_plan.json'
    if plan_path.exists():
        saved = read_json(plan_path)
        for key in set(plan) - {'created_utc'}:
            assert saved[key] == plan[key], key
        plan = saved
    else:
        write_json(plan_path, plan)
    for sub in ['models', 'predictions']:
        (OUT / sub).mkdir(exist_ok=True)
    train, val = Panel(117), Panel(118)
    indices, target, weight = sample_indices(train)
    assert len(indices) == 214132 and int(target.sum()) == 6529
    vi = np.flatnonzero(val.meta.mature.to_numpy().astype(bool) & val.gold)
    meta = val.meta.iloc[vi].reset_index(drop=True)
    assert len(meta) == 2907161
    early = meta.day.to_numpy() < EARLY_END
    me = meta[early].reset_index(drop=True)
    selection_path = OUT / 'institutions_selection.json'
    selection = read_json(selection_path) if selection_path.exists() else dict(started_utc=stamp(),
        plan_sha256=digest(plan_path), training_rows=len(indices), training_events=int(target.sum()),
        training_original_indices_sha256=__import__('hashlib').sha256(indices.tobytes()).hexdigest(),
        evaluation_original_indices_sha256=__import__('hashlib').sha256(vi.tobytes()).hexdigest(), models={})
    assert selection['plan_sha256'] == digest(plan_path)
    for name, spec in specs.items():
        pred_path, model_path = OUT / f'predictions/{name}.npy', OUT / f'models/{name}.joblib'
        if name in selection['models']:
            rec = selection['models'][name]
            assert digest(pred_path) == rec['prediction_sha256'] and digest(model_path) == rec['model_sha256']
            continue
        if spec['role'] == 'frozen_reference':
            for source, dest in [(UNIVERSE / f'predictions/{name}.npy', pred_path), (UNIVERSE / f'models/{name}.joblib', model_path)]:
                if dest.exists():
                    assert digest(dest) == digest(source), dest
                else:
                    shutil.copy2(source, dest)
            assert digest(pred_path) == plan['references'][name]['prediction_sha256']
            assert digest(model_path) == plan['references'][name]['model_sha256']
            probs = np.load(pred_path)
            assert len(probs) == len(meta)
            measured = metrics(me, probs[early])
        else:
            log(f'Fitting {name}: {len(indices):,} weighted rows, {len(spec["features"])} features')
            x = train.design(indices, spec['features'])
            scaler = None
            if spec['kind'] == 'boosted':
                model = HistGradientBoostingClassifier(**plan['boosted_config'], early_stopping=False, random_state=SEED)
                model.fit(x, target, sample_weight=weight)
            else:
                scaler = StandardScaler().fit(x, sample_weight=weight)
                xx = scaler.transform(x).astype(np.float64)
                model = LogisticRegression(**plan['logistic_config'], random_state=SEED)
                model.fit(xx, target, sample_weight=weight)
                del xx
            del x
            artifact = {**spec, 'model': model, 'scaler': scaler, 'placebo': False}
            raw = previous.predict(artifact, val, vi)
            cal = platt_fit(meta.y.to_numpy()[early], raw[early])
            probs = calibrate(raw, cal)
            artifact['calibration_2023'] = cal
            np.save(pred_path, probs)
            joblib.dump(artifact, model_path)
            measured = metrics(me, probs[early])
            del model, artifact, raw
        selection['models'][name] = dict(selection_2023=measured, role=spec['role'],
            prediction_sha256=digest(pred_path), model_sha256=digest(model_path))
        write_json(selection_path, selection)
        log(f'2023 selection {name}: P@8={measured["precision_at_8"]:.6f}; AP={measured["average_precision"]:.6f}')
        del probs
        gc.collect()
    if 'frozen_utc' not in selection:
        winner = max((n for n, s in specs.items() if s['eligible']),
                     key=lambda n: selection['models'][n]['selection_2023']['precision_at_8'])
        selection.update(chosen=winner, frozen_utc=stamp())
        write_json(selection_path, selection)
    result = dict(assessment_started_utc=stamp(), selection_sha256=digest(selection_path),
                  chosen_on_2023=selection['chosen'], status='development_only_not_independent_confirmation', models={})
    for name, spec in specs.items():
        probs = np.load(OUT / f'predictions/{name}.npy')
        result['models'][name] = dict(role=spec['role'], eligible=spec['eligible'], source_qualification=spec['source_qualification'],
            year_2023=metrics(me, probs[early]), year_2024=metrics(meta[~early].reset_index(drop=True), probs[~early]))
        log(f'2024 development {name}: P@8={result["models"][name]["year_2024"]["precision_at_8"]:.6f}')
    result['completed_utc'] = stamp()
    write_json(OUT / 'institutions_results.json', result)


if __name__ == '__main__':
    with threadpool_limits(limits=4):
        run()
