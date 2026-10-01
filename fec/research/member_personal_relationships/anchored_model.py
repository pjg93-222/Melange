"""Small fitted models and leakage barriers, with no ML-service dependency.

Binary sign prediction is conditional on a documented tie. PU models discriminate
reviewed anchors from matched *unlabeled* examples; they do not estimate a
population friendship probability. Defaults are fixed before looking at results.
"""
from collections import defaultdict
import numpy as np
from .core import accepted_events


def anchor_cases(events, cutoff):
    groups=defaultdict(list)
    for e in accepted_events(events,cutoff):
        groups[tuple(sorted((e['actor'],e['target'])))].append(e)
    out=[]
    for pair,rows in sorted(groups.items()):
        signs={r['sign'] for r in rows}
        if len(signs)!=1: continue
        out.append(dict(pair=list(pair), sign=next(iter(signs)),
                        directions=[list(p) for p in sorted({(r['actor'],r['target']) for r in rows})],
                        families=sorted({r['source_family'] for r in rows}),
                        first=min(r['event_date'] for r in rows),last=max(r['event_date'] for r in rows)))
    return out


def fold_mask(events,cases,held):
    """Remove the connected component of cases sharing any underlying source.

    Excluding a case also excludes *all* its source families, transitively. Every
    direction of each excluded pair is removed before computing graph features.
    """
    pairs={tuple(held['pair'])};families=set(held['families'])
    changed=True
    while changed:
        changed=False
        for c in cases:
            pair=tuple(c['pair'])
            if pair in pairs or families.intersection(c['families']):
                old=(len(pairs),len(families))
                pairs.add(pair);families.update(c['families'])
                changed |= old!=(len(pairs),len(families))
    graph=[e for e in events if tuple(sorted((e['actor'],e['target']))) not in pairs
           and e['source_family'] not in families]
    train=[c for c in cases if tuple(c['pair']) not in pairs]
    return graph,train


def matrix(x):
    return np.asarray(x,dtype=float)


def fit_scale(x):
    x=matrix(x)
    count=np.isfinite(x).sum(axis=0)
    mean=np.divide(np.where(np.isfinite(x),x,0).sum(axis=0),count,
                   out=np.zeros(x.shape[1]),where=count>0)
    clean=np.where(np.isfinite(x),x,mean)
    scale=clean.std(axis=0);scale=np.where(scale>1e-8,scale,1.)
    return mean,scale


class Logistic:
    def __init__(self,penalty=1.0): self.penalty=penalty
    def fit(self,x,y,weights=None):
        x=matrix(x);y=matrix(y)
        if len(x)!=len(y) or not np.isin(y,[0,1]).all() or len(set(y))<2:
            raise ValueError('Training requires two explicit binary classes; unknown is not negative')
        self.mean_,self.scale_=fit_scale(x)
        z=self.transform(x);z=np.column_stack([np.ones(len(z)),z])
        w=np.ones(len(y)) if weights is None else matrix(weights)
        if not np.isfinite(w).all() or (w<=0).any(): raise ValueError('Invalid weights')
        w=w/w.sum()
        beta=np.zeros(z.shape[1]);reg=np.diag([0.]+[self.penalty]*(len(beta)-1))
        for _ in range(80):
            p=1/(1+np.exp(-np.clip(z@beta,-35,35)))
            grad=z.T@(w*(p-y))+reg@beta
            hess=z.T@((w*p*(1-p))[:,None]*z)+reg+np.eye(len(beta))*1e-9
            step=np.linalg.solve(hess,grad);beta-=step
            if np.max(np.abs(step))<1e-8: break
        self.intercept_=float(beta[0]);self.coefficients_=beta[1:]
        return self
    def transform(self,x):
        x=matrix(x)
        return np.clip((np.where(np.isfinite(x),x,self.mean_)-self.mean_)/self.scale_,-8,8)
    def predict(self,x):
        return 1/(1+np.exp(-np.clip(self.intercept_+self.transform(x)@self.coefficients_,-35,35)))
    def serializable(self):
        return dict(intercept=self.intercept_,coefficients=self.coefficients_.tolist(),
                    mean=self.mean_.tolist(),scale=self.scale_.tolist(),penalty=self.penalty)


class ResidualRanker:
    """Fit context expectations first, then learn from deviations from expectation.

    score is the logit contribution relative to a context-typical pair. It omits
    the selection intercept and includes no direct party or geography bonus.
    """
    def fit(self,context,features,y,weights=None):
        context=matrix(context);features=matrix(features)
        self.context_mean_,self.context_scale_=fit_scale(context)
        self.feature_mean_,_=fit_scale(features)
        c=self.context_matrix(context)
        x=np.where(np.isfinite(features),features,self.feature_mean_)
        self.anchor_supported_=(np.abs(x[np.asarray(y)==1])>1e-10).any(axis=0)
        w=np.ones(len(x)) if weights is None else matrix(weights)
        w=w/w.sum()
        ridge=np.eye(c.shape[1])*.01;ridge[0,0]=1e-10
        self.expectation_=np.linalg.solve(c.T@(w[:,None]*c)+ridge,c.T@(w[:,None]*x))
        residual=x-c@self.expectation_
        self.model_=Logistic().fit(residual,y,weights)
        return self
    def context_matrix(self,c):
        c=matrix(c)
        z=np.clip((np.where(np.isfinite(c),c,self.context_mean_)-self.context_mean_)/self.context_scale_,-8,8)
        return np.column_stack([np.ones(len(z)),z])
    def score(self,c,x):
        x=matrix(x);x=np.where(np.isfinite(x),x,self.feature_mean_)
        r=x-self.context_matrix(c)@self.expectation_
        zero=np.zeros_like(r)
        return (self.model_.transform(r)-self.model_.transform(zero))@self.model_.coefficients_
    def serializable(self):
        return dict(context_mean=self.context_mean_.tolist(),context_scale=self.context_scale_.tolist(),
                    feature_mean=self.feature_mean_.tolist(),expectation=self.expectation_.tolist(),
                    anchor_supported=self.anchor_supported_.tolist(),classifier=self.model_.serializable())

    def contribution(self,c,x,indices):
        """Change in fitted score when these observed channels are set to zero."""
        x=matrix(x);zero=x.copy();zero[:,list(indices)]=0
        return self.score(c,x)-self.score(c,zero)


def rank_fraction(score,other):
    other=np.asarray(other,dtype=float)
    # Expected rank under random tie-breaking; .5 percentile for all tied.
    rank=1+float((other>score+1e-12).sum())+.5*float(np.isclose(other,score,atol=1e-12,rtol=0).sum())
    pct=(float((other<score-1e-12).sum())+.5*float(np.isclose(other,score,atol=1e-12,rtol=0).sum()))/len(other)
    return rank,pct


def sign_metrics(rows,key):
    y=np.array([r['sign']=='positive' for r in rows]);p=np.array([r[key] for r in rows])
    pred=p>=.5
    auc=float(np.mean([(a>b)+.5*(a==b) for a in p[y] for b in p[~y]]))
    return dict(n=len(y),positive=int(y.sum()),negative=int((~y).sum()),
                accuracy=float((pred==y).mean()),balanced_accuracy=float(((pred[y]).mean()+(~pred[~y]).mean())/2),
                auc=auc,log_loss=float(-(y*np.log(p)+(~y)*np.log(1-p)).mean()))
