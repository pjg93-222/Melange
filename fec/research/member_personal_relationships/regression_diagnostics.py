"""Post-fit ranking-bias check and uncertainty diagnostics; preserves original fits."""
from collections import Counter
import numpy as np
from .regression import (ROOT, OUT, INPUT, MODELS, PENALTIES, read_json, save,
    matrices, Fitter, training_indices, components, metrics, digest)


def leave_two_cases_out(cases,x,mode):
    """Hold a positive dyad and negative dyad out together for each comparison.

    The union of their source/member exclusions is excluded, not only the two
    focal rows. All inner tuning stays inside this smaller training set.
    """
    fitter=Fitter(cases,x);rows=[]
    positive=[i for i,c in enumerate(cases) if c['y']]
    negative=[i for i,c in enumerate(cases) if not c['y']]
    for i in positive:
        for j in negative:
            train=sorted(set(training_indices(cases,i,mode))&set(training_indices(cases,j,mode)))
            if len({cases[k]['y'] for k in train})<2:
                rows.append(dict(positive=i,negative=j,skipped='single_class_training'));continue
            penalty,loss,count=fitter.select(train,mode,PENALTIES)
            model=fitter.fit(train,penalty)
            a,b=float(model.predict(x[i]).mean()),float(model.predict(x[j]).mean())
            rows.append(dict(positive=i,negative=j,p_positive=a,p_negative=b,concordance=float(a>b)+.5*float(a==b),
                train_cases=train,penalty=penalty,inner_scored_pairs=count))
    valid=[r for r in rows if 'concordance' in r]
    return dict(auc=float(np.mean([r['concordance'] for r in valid])),comparisons=len(valid),
        expected_comparisons=len(positive)*len(negative),rows=rows,unique_fits=len(fitter.cache))


def resample_oof(cases,models,n=2000):
    """Paired descriptive stability of existing OOF predictions, not refit CIs.

    Source-component resampling preserves source clusters. Vertex resampling
    weights a dyad by the product of its two sampled member multiplicities.
    Neither handles selection bias or certifies coverage of a confidence level.
    """
    rng=np.random.default_rng(3108);groups=components(cases)
    members=sorted({a for c in cases for a in c['pair']});samples={}
    for scheme in ['source_components','member_vertices']:
        draws=[]
        for _ in range(n):
            if scheme=='source_components':
                ix=[i for k in rng.integers(0,len(groups),len(groups)) for i in groups[k]]
            else:
                count=Counter(members[k] for k in rng.integers(0,len(members),len(members)))
                ix=[i for i,c in enumerate(cases) for _ in range(count[c['pair'][0]]*count[c['pair'][1]])]
            if len({cases[i]['y'] for i in ix})!=2:continue
            y=[cases[i]['y'] for i in ix];values={}
            for name,result in models.items():
                values[name]=metrics(y,[result['predictions'][i]['p'] for i in ix])
            draws.append(dict(combined_auc=values['combined']['auc'],
                combined_accuracy=values['combined']['accuracy'],
                personality_auc_gain=values['combined']['auc']-values['context_work']['auc'],
                personality_log_loss_gain=values['context_work']['log_loss']-values['combined']['log_loss']))
        samples[scheme]=dict(valid_resamples=len(draws),
            intervals={k:np.quantile([r[k] for r in draws],[.025,.5,.975]) for k in draws[0]})
    return samples


def main():
    cases=read_json(OUT/'cases.json');feature_sets=read_json(OUT/'features.json')
    feature_sets={s:{(r['actor'],r['target']):r for r in rows} for s,rows in feature_sets.items()}
    # This check was added after seeing anomalous pooled baseline AUC. It does
    # not replace, select, or retune the declared feature families.
    save(OUT/'ranking_check_spec.json',dict(reason='Training-prevalence baseline has near-zero pooled leave-one-out AUC; compare positive and negative in the same fitted model.',
        models=list(MODELS),source='composite',mode='members',
        reference='https://proceedings.mlr.press/v8/airola10a.html',
        post_fit_diagnostic=True))
    result={}
    for name,names in MODELS.items():
        print('Same-fit ranking check:',name,flush=True)
        x=matrices(cases,names,feature_sets['composite'])
        result[name]=leave_two_cases_out(cases,x,'members')
        print(name,'AUC',result[name]['auc'],'comparisons',result[name]['comparisons'],flush=True)
        save(OUT/'same_fit_auc.json',result)
    models=read_json(OUT/'model_results.json')
    save(OUT/'oof_stability.json',resample_oof(cases,{n:models[n]['members'] for n in ['context_work','combined']}))
    save(OUT/'ranking_check_receipt.json',dict(code_sha256=digest(__file__),models=len(result),
        all_comparisons_scored=all(v['comparisons']==v['expected_comparisons'] for v in result.values())))


if __name__=='__main__':main()
