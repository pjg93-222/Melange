# -*- coding: utf-8 -*-
"""Build and validate the source-primary multimethod Big Five instrument.

The protocol is locked in ``big5_multimethod_prereg.md``.  This script owns three reproducible
artifacts:

* ``b5_lsa256_package_halves.npz`` / ``.meta.json`` -- one common LSA basis with full, package-half
  1, and package-half 2 member-by-venue vectors;
* ``big5_multimethod_reliability.json`` -- package overlap and five Spearman-Brown coefficients;
* ``big5_blue_validated.json`` -- promoted production scores, written only when every locked gate
  clears.

Usage:
  python b5_multimethod_validate.py --rebuild-package-cache --reliability
  python b5_multimethod_validate.py --validate
  python b5_multimethod_validate.py --promote
"""
import argparse
import collections
import csv
import hashlib
import json
import math
import os
import re
import sqlite3
import sys

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.model_selection import GridSearchCV, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import Normalizer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from paths import ROOT as B
import moneyball_core as MC
from moneyball_core import dump_atomic
import affective_n_validate as AN

GENRES = ('CREC', 'INTERVIEW', 'social')
TRAITS = ('O', 'C', 'E', 'A', 'N')
TARGET = {'O': 'breadth_z', 'C': 'diligence_z', 'E': 'visibility_z'}
ALPHAS = [1, 3, 10, 30, 100, 300, 1000]
SEED = 20260712
PERMUTATIONS = 4999
CACHE = os.path.join(B, 'b5_lsa256_package_halves.npz')
META = os.path.join(B, 'b5_lsa256_package_halves.meta.json')
REL_OUT = os.path.join(B, 'big5_multimethod_reliability.json')
OUT = os.path.join(B, 'big5_blue_validated.json')

RITUAL = re.compile(
    r'\b(i yield (back|to|the floor|myself)[^.]*|mr\.? (president|speaker)|madam (president|speaker)|'
    r'i ask unanimous consent[^.]*|the (gentleman|gentlewoman|gentlelady) from [a-z ]+|'
    r'i (rise|reserve the balance of my time)|pursuant to [^.]*|the clerk will [^.]*|'
    r'i suggest the absence of a quorum|the balance of my time)\b', re.I)


def corr(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    good = np.isfinite(a) & np.isfinite(b)
    if good.sum() < 5 or np.std(a[good]) == 0 or np.std(b[good]) == 0:
        return float('nan')
    return float(np.corrcoef(a[good], b[good])[0, 1])


def z(v):
    v = np.asarray(v, float); sd = v.std(ddof=1) or 1.0
    return (v - v.mean()) / sd


def package_half(kind, package):
    key = ('%s|%s' % (kind, package or '')).encode('utf-8', 'replace')
    return 1 + (int(hashlib.sha256(key).hexdigest(), 16) & 1)


def build_package_cache():
    """Build full/h1/h2 LSA-256 vectors with indivisible source packages."""
    b2n = MC.bio2name()
    # Keep only the two final half streams in memory.  The earlier draft retained every turn in a
    # nested package dictionary and then duplicated it into full/h1/h2 strings (>4 GB peak).
    # SQLite groups turns by package; each grouped package is appended to exactly one half.
    parts = collections.defaultdict(lambda: {'h1': [], 'h2': []})
    package_counts = {'full': 0, 'h1': 0, 'h2': 0, 'overlap': 0}
    con = sqlite3.connect(os.path.join(B, 'social_media.db'), timeout=60)
    con.execute('PRAGMA query_only=1')
    for member, source, package, text in con.execute(
            "SELECT member,source,package,group_concat(text,' ') FROM speeches "
            "WHERE source IN ('CREC','INTERVIEW') AND text IS NOT NULL "
            "GROUP BY member,source,package ORDER BY member,source,package"):
        if member and text:
            pkg = str(package)
            cleaned = RITUAL.sub(' ', text) if source == 'CREC' else text
            half = package_half(source, pkg)
            parts[(member, source)]['h%d' % half].append(cleaned)
            package_counts['full'] += 1; package_counts['h%d' % half] += 1
    for bg, post_id, text in con.execute(
            "SELECT bioguide,post_id,text FROM posts WHERE repost_of IS NULL AND text IS NOT NULL"):
        member = b2n.get(bg)
        if member and text:
            pkg = post_id or hashlib.sha256(text.encode('utf-8', 'replace')).hexdigest()
            half = package_half('social', pkg)
            parts[(member, 'social')]['h%d' % half].append(text)
            package_counts['full'] += 1; package_counts['h%d' % half] += 1
    con.close()

    docs = {}
    toks = {}
    for pair, half_parts in parts.items():
        h1 = ' '.join(half_parts['h1']); h2 = ' '.join(half_parts['h2'])
        docs[pair] = {'h1': h1, 'h2': h2}
        t1, t2 = len(h1.split()), len(h2.split())
        toks[pair] = {'full': t1 + t2, 'h1': t1, 'h2': t2}
    del parts

    pairs = sorted(pair for pair in docs if toks[pair]['full'] >= 50)
    corpus = [docs[p]['h1'] + ' ' + docs[p]['h2'] for p in pairs]
    print('package cache corpus ready: %d member-venue docs; fitting common LSA-256 basis' % len(pairs), flush=True)
    pipe = make_pipeline(
        TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=40000, sublinear_tf=True),
        TruncatedSVD(n_components=256, random_state=7),
        Normalizer(copy=False))
    full = pipe.fit_transform(corpus)
    print('  full corpus transformed; transforming package half 1', flush=True)
    arrays = {}
    for i, pair in enumerate(pairs):
        arrays['full|%s|%s' % pair] = full[i]
    for rep in ('h1', 'h2'):
        transformed = pipe.transform([docs[p][rep] for p in pairs])
        print('  %s transformed' % rep, flush=True)
        for i, pair in enumerate(pairs):
            arrays['%s|%s|%s' % (rep, pair[0], pair[1])] = transformed[i]
    np.savez_compressed(CACHE, **arrays)
    meta = {
        'basis': 'LSA-256 TF-IDF word 1-2gram, one full-corpus unsupervised basis',
        'genres': list(GENRES), 'pairs': ['%s|%s' % p for p in pairs],
        'tokens': {'%s|%s|%s' % (rep, p[0], p[1]): toks[p][rep]
                   for p in pairs for rep in ('full', 'h1', 'h2')},
        'package_assignment': 'SHA256(source|package) parity; package indivisible',
        'package_counts': package_counts, 'shared_packages': 0,
        'social_unit': 'post_id', 'speech_unit': 'source package', 'seed': 7,
    }
    dump_atomic(meta, META, indent=1)
    print('package cache: %d member-venue documents | %d source packages | overlap 0' %
          (len(pairs), package_counts['full']))


def load_matrix(rep):
    if not os.path.exists(CACHE) or not os.path.exists(META):
        raise RuntimeError('package cache missing; run --rebuild-package-cache')
    meta = json.load(open(META, encoding='utf-8'))
    npz = np.load(CACHE)
    pairs = [tuple(s.split('|', 1)) for s in meta['pairs']]
    tokens = meta['tokens']
    by_genre = {}
    for genre in GENRES:
        gp = [p for p in pairs if p[1] == genre and tokens.get('%s|%s|%s' % (rep, p[0], genre), 0) >= 50]
        if len(gp) < 20:
            continue
        X = np.array([npz['%s|%s|%s' % (rep, m, genre)] for m, _ in gp])
        mu = X.mean(0); sd = X.std(0, ddof=1); sd[sd == 0] = 1
        by_genre[genre] = ({m: i for i, (m, _g) in enumerate(gp)}, (X - mu) / sd)
    members = sorted({m for idx, _x in by_genre.values() for m in idx})
    rows, keep = [], []
    for member in members:
        num = None; den = 0.0
        for genre, (idx, X) in by_genre.items():
            if member not in idx:
                continue
            wt = tokens.get('%s|%s|%s' % (rep, member, genre), 0)
            num = X[idx[member]] * wt if num is None else num + X[idx[member]] * wt
            den += wt
        if den:
            rows.append(num / den); keep.append(member)
    return np.asarray(rows), keep


def nested_oof(X, members, criterion):
    bd = json.load(open(os.path.join(B, 'behavioral_dispositions.json'), encoding='utf-8'))['members']
    idx = {m: i for i, m in enumerate(members)}
    ms = [m for m in members if bd.get(m, {}).get(criterion) is not None]
    Xa = X[[idx[m] for m in ms]]; y = np.array([bd[m][criterion] for m in ms], float)
    pred = np.empty(len(ms), float); chosen = []
    outer = KFold(5, shuffle=True, random_state=7)
    for train, test in outer.split(Xa):
        grid = GridSearchCV(Ridge(), {'alpha': ALPHAS}, cv=5, scoring='neg_mean_squared_error')
        grid.fit(Xa[train], y[train]); pred[test] = grid.predict(Xa[test]); chosen.append(grid.best_params_['alpha'])
    return dict(zip(ms, pred)), dict(zip(ms, y)), chosen


def fit_full_models(X, members):
    bd = json.load(open(os.path.join(B, 'behavioral_dispositions.json'), encoding='utf-8'))['members']
    idx = {m: i for i, m in enumerate(members)}; models = {}; scores = {}
    for trait, criterion in TARGET.items():
        ms = [m for m in members if bd.get(m, {}).get(criterion) is not None]
        Xa = X[[idx[m] for m in ms]]; y = np.array([bd[m][criterion] for m in ms], float)
        grid = GridSearchCV(Ridge(), {'alpha': ALPHAS}, cv=5, scoring='neg_mean_squared_error')
        grid.fit(Xa, y); model = grid.best_estimator_; models[trait] = model
        scores[trait] = dict(zip(members, z(model.predict(X))))
    return models, scores


def raw_a_halves():
    raw = json.load(open(os.path.join(B, 'interview_antagonism_halves.json.candidate'),
                         encoding='utf-8'))['members']
    members = sorted(raw)
    h1 = {m: -float(raw[m]['halves']['A']['antagonism']) for m in members}
    h2 = {m: -float(raw[m]['halves']['B']['antagonism']) for m in members}
    mean = {m: (h1[m] + h2[m]) / 2 for m in members}
    zm = z([mean[m] for m in members])
    return h1, h2, dict(zip(members, zm))


def n_channels(e_row):
    path = os.path.join(AN.SC, 'interview_n_affective.json')
    if not os.path.exists(path):
        raise RuntimeError('independent LLM affect channel missing: ' + path)
    llm_raw = json.load(open(path, encoding='utf-8'))
    liwc = AN.liwc_n(AN.liwc_counts())
    party = MC.party()
    members = sorted(set(llm_raw) & set(liwc) & set(e_row))
    y = np.array([sum(float(llm_raw[m][k]) for k in
                      ('pessimism', 'anxiety', 'depression', 'volatility')) for m in members])
    controls = np.column_stack([np.ones(len(members)),
                                [1.0 if party.get(m) == 'R' else 0.0 for m in members],
                                [e_row[m] for m in members]])
    residual = y - controls @ np.linalg.lstsq(controls, y, rcond=None)[0]
    return dict(zip(members, residual)), {m: liwc[m] for m in members}, path


def permutation_p(row, col, rng):
    members = sorted(set(row) & set(col)); x = np.array([row[m] for m in members]); y = np.array([col[m] for m in members])
    observed = corr(x, y); exceed = 0
    for _ in range(PERMUTATIONS):
        if corr(x, rng.permutation(y)) >= observed:
            exceed += 1
    return observed, (exceed + 1) / (PERMUTATIONS + 1), len(members)


def validation_result():
    X, members = load_matrix('full')
    rows = {}; cols = {}; alphas = {}
    for trait, criterion in TARGET.items():
        rows[trait], cols[trait], alphas[trait] = nested_oof(X, members, criterion)
    rows['A'], cols['A'], prod_a = raw_a_halves()
    rows['N'], cols['N'], n_source = n_channels(rows['E'])

    matrix = {}; ns = {}
    for row_trait in TRAITS:
        matrix[row_trait] = {}; ns[row_trait] = {}
        for col_trait in TRAITS:
            common = sorted(set(rows[row_trait]) & set(cols[col_trait]))
            matrix[row_trait][col_trait] = corr([rows[row_trait][m] for m in common],
                                                [cols[col_trait][m] for m in common])
            ns[row_trait][col_trait] = len(common)
    rng = np.random.default_rng(SEED)
    pvals = {}; diag = {}
    for i, trait in enumerate(TRAITS):
        obs, p, n = permutation_p(rows[trait], cols[trait], rng)
        row_other = [abs(matrix[trait][t]) for t in TRAITS if t != trait]
        col_other = [abs(matrix[t][trait]) for t in TRAITS if t != trait]
        row_dom = abs(obs) > max(row_other); col_dom = abs(obs) > max(col_other)
        pvals[trait] = p
        diag[trait] = {'r': obs, 'n': n, 'perm_p': p, 'row_dominant': row_dom,
                       'column_dominant': col_dom,
                       'pass': obs > 0 and p < .05 and row_dom and col_dom}

    models, prod_oce = fit_full_models(X, members)
    affective = json.load(open(os.path.join(B, 'affective_n.json'), encoding='utf-8'))['members']
    v2 = json.load(open(os.path.join(B, 'big5_v2.json'), encoding='utf-8'))['traits']
    traits = {}
    for member in sorted(set(members) & set(affective)):
        n = float(affective[member]); a = prod_a.get(member)
        traits[member] = {'O': round(float(prod_oce['O'][member]), 3),
                          'C': round(float(prod_oce['C'][member]), 3),
                          'E': round(float(prod_oce['E'][member]), 3),
                          'A': None if a is None else round(float(a), 3),
                          'N': round(n, 3), 'ES': round(-n, 3),
                          'tokens': int(v2.get(member, {}).get('tokens', 0)),
                          'lowconf': bool(v2.get(member, {}).get('lowconf', False)),
                          'a_source': None if a is None else 'inverse_interview_antagonism',
                          'n_source': 'affective_n'}

    party = MC.party(); expected = {'O': -1, 'C': 1, 'E': -1, 'A': -1, 'N': -1}
    known = {}
    for trait in TRAITS:
        rs = [d[trait] for m, d in traits.items() if d.get(trait) is not None and party.get(m) == 'R']
        ds = [d[trait] for m, d in traits.items() if d.get(trait) is not None and party.get(m) == 'D']
        diff = float(np.mean(rs) - np.mean(ds))
        known[trait] = {'r_minus_d': diff, 'n_r': len(rs), 'n_d': len(ds),
                        'expected_sign': expected[trait], 'pass': diff * expected[trait] > 0}

    coverage = {trait: sum(d.get(trait) is not None for d in traits.values()) for trait in TRAITS}
    return {'matrix': matrix, 'cell_n': ns, 'diagonal': diag,
            'diagonal_pass_n': sum(d['pass'] for d in diag.values()),
            'known_groups': known, 'known_groups_pass_n': sum(d['pass'] for d in known.values()),
            'coverage': coverage, 'nested_alpha_by_fold': alphas,
            'criterion_channels': {'O': 'breadth_z', 'C': 'diligence_z', 'E': 'visibility_z',
                                   'A': 'opposite package half', 'N': 'LIWC affect'},
            'n_llm_source': n_source, 'traits': traits}


def package_liwc_reliability():
    con = sqlite3.connect(os.path.join(B, 'social_media.db'), timeout=60); con.execute('PRAGMA query_only=1')
    packs = collections.defaultdict(lambda: collections.defaultdict(list))
    for member, package, text in con.execute(
            "SELECT member,package,text FROM speeches WHERE source='INTERVIEW' AND text IS NOT NULL"):
        pkg = package or hashlib.sha256(text.encode('utf-8', 'replace')).hexdigest()
        packs[member][str(pkg)].append(text)
    con.close()
    scores = []
    for half in (1, 2):
        ag = {}
        for member, pp in packs.items():
            counts = [0, 0, 0, 0]
            for pkg, turns in pp.items():
                if package_half('INTERVIEW', pkg) != half:
                    continue
                text = ' '.join(turns); words = len(AN.WORD.findall(text))
                counts[0] += len(AN.FPS.findall(text)); counts[1] += len(AN.NEG.findall(text))
                counts[2] += len(AN.POS.findall(text)); counts[3] += words
            if counts[3] >= 400:
                ag[member] = counts
        scores.append(AN.liwc_n(ag, floor=400))
    common = sorted(set(scores[0]) & set(scores[1]))
    return corr([scores[0][m] for m in common], [scores[1][m] for m in common]), len(common)


def reliability_result():
    meta = json.load(open(META, encoding='utf-8'))
    Xf, mf = load_matrix('full'); X1, m1 = load_matrix('h1'); X2, m2 = load_matrix('h2')
    models, _scores = fit_full_models(Xf, mf)
    i1 = {m: i for i, m in enumerate(m1)}; i2 = {m: i for i, m in enumerate(m2)}
    result = {}
    for trait in ('O', 'C', 'E'):
        common = sorted(set(m1) & set(m2))
        p1 = models[trait].predict(X1[[i1[m] for m in common]])
        p2 = models[trait].predict(X2[[i2[m] for m in common]])
        r = corr(p1, p2); result[trait] = {'half_r': r, 'spearman_brown': 2*r/(1+r), 'n': len(common)}
    a1, a2, _mean = raw_a_halves(); common = sorted(set(a1) & set(a2)); r = corr([a1[m] for m in common], [a2[m] for m in common])
    result['A'] = {'half_r': r, 'spearman_brown': 2*r/(1+r), 'n': len(common)}
    r, n = package_liwc_reliability(); result['N'] = {'half_r': r, 'spearman_brown': 2*r/(1+r), 'n': n}
    for trait in TRAITS:
        result[trait]['pass'] = result[trait]['spearman_brown'] >= .50
    out = {'traits': result, 'pass_n': sum(d['pass'] for d in result.values()),
           'package_overlap': int(meta.get('shared_packages', -1)),
           'package_counts': meta.get('package_counts'),
           'method': 'SHA256 package-disjoint halves; common full-corpus LSA basis; fixed full models',
           'preregistration': 'big5_multimethod_prereg.md'}
    dump_atomic(out, REL_OUT, indent=1)
    return out


def print_validation(v):
    print('five-trait independent-criterion matrix (row instrument -> column criterion)')
    print('        ' + ' '.join('%8s' % t for t in TRAITS))
    for trait in TRAITS:
        print('%3s  %s' % (trait, ' '.join('%+8.3f' % v['matrix'][trait][t] for t in TRAITS)))
    for trait in TRAITS:
        d = v['diagonal'][trait]
        print('  %s diag=%+.3f n=%d p=%.4f row=%s col=%s -> %s' %
              (trait, d['r'], d['n'], d['perm_p'], d['row_dominant'], d['column_dominant'],
               'PASS' if d['pass'] else 'MISS'))
    print('diagonal dominance: %d/5' % v['diagonal_pass_n'])
    for trait in TRAITS:
        d = v['known_groups'][trait]
        print('  known %s R-D=%+.3f n=%d -> %s' %
              (trait, d['r_minus_d'], d['n_r'] + d['n_d'], 'PASS' if d['pass'] else 'MISS'))
    print('known-groups: %d/5 | coverage %s' % (v['known_groups_pass_n'], v['coverage']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rebuild-package-cache', action='store_true')
    ap.add_argument('--reliability', action='store_true')
    ap.add_argument('--validate', action='store_true')
    ap.add_argument('--promote', action='store_true')
    args = ap.parse_args()
    if args.rebuild_package_cache:
        build_package_cache()
    if args.reliability:
        rel = reliability_result()
        for trait in TRAITS:
            d = rel['traits'][trait]
            print('  reliability %s half-r=%+.3f SB=%.3f n=%d -> %s' %
                  (trait, d['half_r'], d['spearman_brown'], d['n'], 'PASS' if d['pass'] else 'MISS'))
        print('reliability: %d/5 | package overlap %d' % (rel['pass_n'], rel['package_overlap']))
    if args.validate or args.promote or not any((args.rebuild_package_cache, args.reliability)):
        val = validation_result(); print_validation(val)
        if args.promote:
            if not os.path.exists(REL_OUT):
                raise SystemExit('promotion refused: reliability artifact missing')
            rel = json.load(open(REL_OUT, encoding='utf-8'))
            ok = (rel.get('pass_n') == 5 and rel.get('package_overlap') == 0 and
                  val['diagonal_pass_n'] == 5 and val['known_groups_pass_n'] == 5)
            if not ok:
                raise SystemExit('promotion refused: one or more locked gates missed')
            dump_atomic({'traits': val.pop('traits'), 'validation': val, 'reliability': rel,
                         'method': 'source-primary multimethod Big Five: O/C/E venue-specific LSA behavior calibration; '
                                   'A inverse package-split interview antagonism; N promoted affective-content; ES=-N',
                         'preregistration': 'big5_multimethod_prereg.md'}, OUT, indent=1)
            print('PROMOTED: big5_blue_validated.json')


if __name__ == '__main__':
    main()
