"""Regularized cumulative-logit degrees; independent outcomes, no implicit zeros."""
import numpy as np


def sigmoid(x):
    return np.exp(-np.logaddexp(0, -np.asarray(x, dtype=float)))


def cutpoints(raw):
    return np.r_[raw[0], raw[0] + np.cumsum(np.logaddexp(0, raw[1:]))]


def ordinal_objective(params, z, y, weights, regularization, cut_penalty=.01):
    """Stable exact five-category likelihood and its analytic gradient."""
    p = z.shape[1]
    beta, raw = params[:p], params[p:]
    theta = cutpoints(raw)
    eta = z @ beta
    w = weights / weights.sum()
    ll = np.zeros(len(y)); geta = np.zeros(len(y)); gt = np.zeros(4)
    for k in range(5):
        take = y == k
        if not np.any(take):
            continue
        e, wk = eta[take], w[take]
        if k == 0:
            upper = theta[0] - e
            a = sigmoid(upper)
            ll[take] = -np.logaddexp(0, -upper)
            geta[take] = 1 - a
            gt[0] -= wk @ (1 - a)
        elif k == 4:
            lower = theta[3] - e
            b = sigmoid(lower)
            ll[take] = -np.logaddexp(0, lower)
            geta[take] = -b
            gt[3] += wk @ b
        else:
            upper, lower = theta[k] - e, theta[k-1] - e
            a, b = sigmoid(upper), sigmoid(lower)
            gap = theta[k] - theta[k-1]
            lp = (-np.logaddexp(0, -upper) - np.logaddexp(0, lower)
                  + np.log(-np.expm1(-gap)))
            ll[take] = lp
            geta[take] = 1 - a - b
            log_fu = -np.logaddexp(0, -upper) - np.logaddexp(0, upper)
            log_fl = -np.logaddexp(0, -lower) - np.logaddexp(0, lower)
            gt[k] -= wk @ np.exp(log_fu - lp)
            gt[k-1] += wk @ np.exp(log_fl - lp)
    reference = np.log(np.arange(1, 5) / np.arange(4, 0, -1))
    delta = theta - reference
    objective = (-w @ ll + .5 * np.sum(regularization * beta**2)
                 + .5 * cut_penalty * (delta @ delta))
    gb = z.T @ (w * geta) + regularization * beta
    gt += cut_penalty * delta
    gr = np.r_[gt.sum(), [sigmoid(raw[j]) * gt[j:].sum() for j in range(1, 4)]]
    return float(objective), np.r_[gb, gr]


class OrdinalDegrees:
    """Train-only scaling plus regularized chamber intercepts/slope deviations.

    The probabilities describe observed ordinal assessments. The predictive
    grade interval is not an epistemic confidence interval on private feelings.
    """
    def __init__(self, penalty=1., chamber_slopes=False):
        if penalty <= 0:
            raise ValueError('Positive regularization required')
        self.penalty = float(penalty)
        self.chamber_slopes = chamber_slopes

    def base_transform(self, x):
        valid = np.isfinite(x)
        raw = np.c_[np.where(valid, x, self.mean_), ~valid].astype(float)
        return (raw - self.center_) / self.scale_

    def design(self, x, chambers):
        if any(c not in ('House', 'Senate', 'cross_chamber') for c in chambers):
            raise ValueError('Unresolved chamber cannot silently become House')
        base = self.base_transform(np.asarray(x, dtype=float))
        c = np.asarray(chambers)
        parts = [np.c_[c == 'Senate', c == 'cross_chamber'].astype(float), base]
        if self.chamber_slopes:
            parts.extend(base * (c == group)[:, None] for group in ('House', 'Senate', 'cross_chamber'))
        return np.concatenate(parts, axis=1)

    def fit(self, x, y, chambers, weights=None):
        x = np.asarray(x, dtype=float); y = np.asarray(y)
        if x.ndim != 2 or len(x) != len(y) or len(chambers) != len(y) or not len(y):
            raise ValueError('Nonempty aligned rows required')
        if not np.isin(y, np.arange(5)).all():
            raise ValueError('Only explicit grades 0..4; unknown must be omitted')
        y = y.astype(int)
        w = np.ones(len(y)) if weights is None else np.asarray(weights, dtype=float)
        if w.shape != y.shape or not np.isfinite(w).all() or np.any(w <= 0):
            raise ValueError('Invalid weights')
        w = w / w.sum(); valid = np.isfinite(x)
        denominator = (valid * w[:, None]).sum(0)
        self.mean_ = np.divide((np.where(valid, x, 0) * w[:, None]).sum(0), denominator,
                               out=np.zeros(x.shape[1]), where=denominator > 0)
        raw = np.c_[np.where(valid, x, self.mean_), ~valid].astype(float)
        self.center_ = w @ raw
        scale = np.sqrt(w @ (raw - self.center_)**2)
        self.scale_ = np.where(scale > 1e-8, scale, 1.)
        z = self.design(x, chambers); n = z.shape[1]
        reg = np.full(n, self.penalty)
        if self.chamber_slopes:
            reg[2 + raw.shape[1]:] *= 4
        reference = np.log(np.arange(1, 5) / np.arange(4, 0, -1))
        params = np.r_[np.zeros(n), reference[0], np.log(np.expm1(np.diff(reference))) ]
        fun = lambda b: ordinal_objective(b, z, y, w, reg)
        f, g = fun(params); h = np.eye(len(params))
        for iteration in range(700):
            if np.max(np.abs(g)) < 1e-7:
                break
            direction = -(h @ g)
            if direction @ g >= -1e-14:
                h = np.eye(len(params)); direction = -g
            step = 1.
            for _ in range(50):
                candidate = params + step * direction
                nf, ng = fun(candidate)
                if np.isfinite(nf) and nf <= f + 1e-4 * step * (g @ direction):
                    break
                step *= .5
            else:
                raise ArithmeticError('Ordinal line search failed')
            s = candidate - params; dy = ng - g; sy = s @ dy
            if sy > 1e-12:
                hy = h @ dy
                h += ((sy + dy @ hy) / sy**2) * np.outer(s, s) - (np.outer(hy, s) + np.outer(s, hy)) / sy
            params, f, g = candidate, nf, ng
        self.gradient_norm_ = float(np.max(np.abs(g)))
        if self.gradient_norm_ > 2e-6:
            raise ArithmeticError(f'Ordinal model did not converge: {self.gradient_norm_}')
        self.beta_ = params[:n]; self.theta_ = cutpoints(params[n:])
        self.iterations_ = iteration + 1; self.objective_ = f
        self.observed_grades_ = sorted(set(y.tolist()))
        return self

    def predict_proba(self, x, chambers):
        eta = self.design(x, chambers) @ self.beta_
        cdf = sigmoid(self.theta_[None, :] - eta[:, None])
        probabilities = np.diff(np.c_[np.zeros(len(eta)), cdf, np.ones(len(eta))], axis=1)
        if not np.isfinite(probabilities).all() or (probabilities < -1e-12).any():
            raise ArithmeticError('Invalid ordinal probabilities')
        return np.maximum(probabilities, 0)

    def serializable(self):
        return dict(penalty=self.penalty, chamber_slopes=self.chamber_slopes,
                    beta=self.beta_, cutpoints=self.theta_, mean=self.mean_,
                    center=self.center_, scale=self.scale_, observed_grades=self.observed_grades_,
                    gradient_norm=self.gradient_norm_, iterations=self.iterations_, objective=self.objective_)


def weighted_metrics(y, probability, weights):
    y = np.asarray(y, dtype=int); p = np.asarray(probability, dtype=float)
    w = np.asarray(weights, dtype=float); w /= w.sum()
    expected = p @ np.arange(5)
    targets = y[:, None] <= np.arange(4)[None, :]
    return dict(n=len(y), ordinal_log_loss=float(-w @ np.log(np.maximum(p[np.arange(len(y)), y], 1e-15))),
                ranked_probability_score=float(w @ np.mean((p.cumsum(1)[:, :4] - targets)**2, axis=1)),
                mean_absolute_grade_error=float(w @ np.abs(expected - y)),
                observed_grades=sorted(set(y.tolist())))


def training_indices(rows, held):
    endpoints = set(rows[held]['pair'])
    excluded = {i for i, r in enumerate(rows) if endpoints.intersection(r['pair'])}
    families = {f for i in excluded for f in rows[i]['families']}
    while True:
        newer = {i for i, r in enumerate(rows) if families.intersection(r['families'])} | excluded
        nf = {f for i in newer for f in rows[i]['families']}
        if newer == excluded and nf == families:
            return [i for i in range(len(rows)) if i not in excluded]
        excluded, families = newer, nf


def reviewed_display(affinity, friction, neutral_evidence=False):
    """Descriptions are ancillary to degrees; model scores cannot establish neutral."""
    if affinity is not None and affinity >= 2 and friction is not None and friction >= 2:
        return 'mixed'
    if affinity == 0 and friction == 0 and neutral_evidence:
        return 'supported_neutral'
    if affinity is None and friction is None:
        return 'unknown'
    return 'partially_assessed' if affinity is None or friction is None else 'graded_relationship'
