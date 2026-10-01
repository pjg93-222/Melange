"""Prespecified family-clustered assessment of frozen institutional forecasts."""
import gc
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from institutions_common import OLD, OUT, UNIVERSE, digest, log, read_json, stamp, write_json
from institutions_models import EARLY_END
from paired_extensions import families
from run_models import topk_vectors, basic_metrics
from universe_statistics import intervals, selected_summary

REPS = 100000
BUDGETS = [250, 500, 1000, 2000, 5000]
FRACTIONS = [1., .5, .25, .1, .05, .01]


def evaluation_meta():
    meta = pd.read_parquet(OLD / 'meta_118.parquet')
    member_ids = read_json(OLD / 'identifiers.json')['members']
    gold = set(read_json(UNIVERSE / 'gold_cohort.json')['member_ids'])
    included = np.array([mid in gold for mid in member_ids])[meta.member.to_numpy()]
    return meta[meta.mature.astype(bool) & included].reset_index(drop=True)


def run():
    if (OUT / 'institutions_statistics.json').exists():
        raise RuntimeError('Statistics already frozen')
    result = read_json(OUT / 'institutions_results.json')
    plan = read_json(OUT / 'institutions_plan.json')
    selection = read_json(OUT / 'institutions_selection.json')
    assert result['selection_sha256'] == digest(OUT / 'institutions_selection.json')
    assert selection['plan_sha256'] == digest(OUT / 'institutions_plan.json')
    assert digest(__file__) == plan['supporting_code_sha256']['institutions_statistics.py']
    pairs = plan['pairs']
    assert len({frozenset(p) for p in pairs}) == len(pairs)
    meta = evaluation_meta()
    early = meta.day.to_numpy() < EARLY_END
    me, ml = meta[early].reset_index(drop=True), meta[~early].reset_index(drop=True)
    codes, n = families(ml)
    y, ye = ml.y.to_numpy(), me.y.to_numpy()
    assert len(ml) == 1048932 and int(y.sum()) == 2100
    weights = np.random.default_rng(2090508).multinomial(n, np.full(n, 1/n), size=REPS).astype(np.uint16)
    write_json(OUT / 'institutions_statistics_plan.json', dict(created_utc=stamp(), pairs=pairs,
        comparisons=len(pairs), replicates=REPS, seed=2090508, code_sha256=digest(__file__),
        model_plan_sha256=digest(OUT / 'institutions_plan.json'), selection_sha256=digest(OUT / 'institutions_selection.json'),
        uncertainty='Whole legislative families; all member rows and dates retained. Bonferroni percentile intervals across the prespecified pairs separately for primary precision and secondary Brier. Development only.'))
    hist, slots, brier, selective, strata, ordering = {}, {}, {}, {}, {}, {}
    rowcounts = np.bincount(codes, minlength=n)
    for name in result['models']:
        path = OUT / f'predictions/{name}.npy'
        assert digest(path) == selection['models'][name]['prediction_sha256']
        p = np.load(path)
        assert len(p) == len(meta) and np.isfinite(p).all()
        pe, pl = p[early], p[~early]
        te, tl = topk_vectors(me, ye, pe, 8), topk_vectors(ml, y, pl, 8)
        hist[name] = np.bincount(codes[tl], weights=y[tl], minlength=n)
        slots[name] = np.bincount(codes[tl], minlength=n)
        brier[name] = np.bincount(codes, weights=(pl-y)**2, minlength=n)
        ordering[name] = tl[np.lexsort((ml.member.to_numpy()[tl], ml.group.to_numpy()[tl], -pl[tl]))]
        selective[name] = []
        for fraction in FRACTIONS:
            cutoff = float(np.quantile(pe[te], 1-fraction))
            idx = tl[pl[tl] >= cutoff]
            rec = selected_summary(ml, y, idx)
            h = np.bincount(codes[idx], weights=y[idx], minlength=n)
            d = np.bincount(codes[idx], minlength=n)
            rec.update(target_fraction_2023=fraction, cutoff_2023=cutoff, ci95=intervals(weights, h, d))
            selective[name].append(rec)
        strata[name] = {}
        masks = {'House': ml.senate.to_numpy() == 0, 'Senate': ml.senate.to_numpy() == 1,
                 'Democratic': ml.democrat.to_numpy() == 1, 'non_Democratic': ml.democrat.to_numpy() == 0}
        for label, mask in masks.items():
            idx = tl[mask[tl]]
            rec = selected_summary(ml, y, idx)
            rec.update(recall=int(y[idx].sum()) / max(1, int(y[mask].sum())), candidate_rows=int(mask.sum()),
                       candidate_events=int(y[mask].sum()), candidate_metrics=basic_metrics(y[mask], pl[mask]))
            strata[name][label] = rec
        log(f'Cluster and coverage statistics accumulated for {name}')
        del p, pe, pl
        gc.collect()
    paired = {}
    for challenger, baseline in pairs:
        assert np.array_equal(slots[challenger], slots[baseline]), 'Unequal per-family slot budgets'
        delta, bd = hist[challenger]-hist[baseline], brier[challenger]-brier[baseline]
        paired[challenger+' vs '+baseline] = dict(extra_hits=int(delta.sum()),
            delta_precision=float(delta.sum()/slots[baseline].sum()),
            ci95=intervals(weights, delta, slots[baseline]),
            adjusted_interval=intervals(weights, delta, slots[baseline], alpha=.05/len(pairs)),
            delta_brier=float(bd.sum()/rowcounts.sum()), brier_ci95=intervals(weights, bd, rowcounts),
            brier_adjusted_interval=intervals(weights, bd, rowcounts, alpha=.05/len(pairs)))
    matched = {count: {name: selected_summary(ml, y, idx[:count]) for name, idx in ordering.items()} for count in BUDGETS}
    all_counts = ml.groupby('group').y.sum().to_numpy()
    chosen = result['chosen_on_2023']
    output = dict(completed_utc=stamp(), status='retrospective_continuing_member_development', cohort_members=377,
        gold_cohort_sha256=digest(UNIVERSE / 'gold_cohort.json'), families=n, replicates=REPS, comparisons=len(pairs),
        chosen_on_2023=chosen, rows_2024=len(ml), events_2024=int(y.sum()), slots_2024=int(slots[chosen].sum()),
        bills_2024=int(ml.bill.nunique()), bill_dates_2024=int(ml.group.nunique()),
        forced_top8_oracle=dict(hits=int(np.minimum(all_counts, 8).sum()),
            precision=float(np.minimum(all_counts, 8).sum()/slots[chosen].sum()), zero_event_bill_dates=int((all_counts==0).sum())),
        paired=paired, selective=selective, matched_retained_counts=matched, strata=strata,
        note='Earlier development data were already examined. Family clustering does not remove remaining member dependence or historical selection optimism. Matched budgets are descriptive, not frozen probability policies.')
    write_json(OUT / 'institutions_statistics.json', output)
    log('Institutional family-clustered comparisons complete')


if __name__ == '__main__':
    with threadpool_limits(limits=2):
        run()
