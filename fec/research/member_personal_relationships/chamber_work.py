"""Dated original-cosponsorship features, computed in separate chamber layers."""
from datetime import date
import numpy as np
from .history_work import safe_ratio, network_proximity


def term_on(member, day):
    found = [t for t in member['terms'] if t['start'] <= day < t['end']]
    return found[0] if len(found) == 1 else None


def chamber_at(members, actor, target, day):
    a, b = term_on(members[actor], day), term_on(members[target], day)
    if not a or not b:
        return None
    return a['chamber'] if a['chamber'] == b['chamber'] else 'cross_chamber'


def co_service_years(a, b, day, chamber):
    days = 0
    for x in a['terms']:
        for y in b['terms']:
            if x['chamber'] != chamber or y['chamber'] != chamber:
                continue
            start, end = max(x['start'], y['start']), min(x['end'], y['end'], day)
            if start < end:
                days += (date.fromisoformat(end) - date.fromisoformat(start)).days
    return days / 365.25


WORK_FIELDS = ['direct_propensity', 'reverse_direct_propensity', 'weighted_shared_jaccard',
               'log_shared_bills', 'network_proximity', 'issue_similarity', 'actor_bipartisan',
               'target_bipartisan']


def temporal_features(members, bills, assessments, progress=print):
    """Incremental matrices: each bill enters once in its chamber, before the date.

    Work edges include original signatures only. Opportunity eligibility is at
    introduction; a date cutoff selects history, not a signature-joining window.
    Cross-chamber same-bill metrics remain structurally missing.
    """
    ids = sorted(members); ix = {a: i for i, a in enumerate(ids)}; n = len(ids)
    areas = sorted({b['area'] for b in bills}); ai = {a: i for i, a in enumerate(areas)}
    result = {}; audit = dict(bills_used_by_chamber={}, snapshots=[], coverage_start='2019-01-03',
                             snapshot_policy='bill introduction strictly before assessment date',
                             original_only=True, no_title_collapse=True,
                             later_withdrawals_count_as_original_participation=True)
    for r in assessments:
        layer = chamber_at(members, r['actor'], r['target'], r['date'])
        result[r['id']] = dict(chamber=layer, **{k: None for k in WORK_FIELDS},
                              shared_original_bills=None, original_a_to_b=None, original_b_to_a=None,
                              opportunities_a_to_b=None, opportunities_b_to_a=None,
                              work_status='cross_chamber_structurally_unavailable' if layer == 'cross_chamber' else 'no_prior_covered_work',
                              co_service_years=co_service_years(members[r['actor']], members[r['target']], r['date'], layer))
    for chamber in ('House', 'Senate'):
        rows = [r for r in assessments if result[r['id']]['chamber'] == chamber]
        bs = sorted([b for b in bills if b['chamber'] == chamber], key=lambda b: (b['introduced'], b['key']))
        matrices = {k: np.zeros((n, n)) for k in ('direct', 'opportunities', 'shared', 'weighted', 'conditional', 'coeligible', 'cross_direct', 'cross_opportunities', 'same_direct', 'same_opportunities')}
        sig = np.zeros((n, len(areas))); opp_area = np.zeros_like(sig)
        cursor = 0
        for day in sorted({r['date'] for r in rows}):
            end = cursor
            while end < len(bs) and bs[end]['introduced'] < day:
                end += 1
            for offset in range(cursor, end, 2500):
                batch = bs[offset:min(offset+2500, end)]; m = len(batch)
                c = np.zeros((n, m), np.float32); eligible = np.zeros_like(c); sponsor = np.zeros_like(c)
                cross = np.zeros_like(c); same = np.zeros_like(c)
                weights = np.zeros(m, np.float32)
                for j, b in enumerate(batch):
                    terms = [term_on(members[a], b['introduced']) for a in ids]
                    s = ix.get(b['sponsor'])
                    if s is not None:
                        sponsor[s, j] = 1
                    originals = set(b['original'])
                    if not originals.issubset(b['joins']):
                        raise ValueError('Original signature missing valid provenance')
                    kept = {a for a in originals if a != b['sponsor'] and (a not in ix or
                            (terms[ix[a]] and terms[ix[a]]['chamber'] == chamber))}
                    weights[j] = 1 / max(1, len(kept)-1)
                    for i, a in enumerate(ids):
                        t = terms[i]
                        if t and t['chamber'] == chamber and i != s:
                            eligible[i, j] = 1
                            c[i, j] = a in kept
                            if s is not None and terms[s] and t['party'] in ('Democrat', 'Republican') and terms[s]['party'] in ('Democrat', 'Republican'):
                                cross[i, j] = t['party'] != terms[s]['party']
                                same[i, j] = t['party'] == terms[s]['party']
                    if np.any(c[:, j] > eligible[:, j]):
                        raise ValueError('Original cosponsor outside opportunity')
                    sig[:, ai[b['area']]] += c[:, j]
                    opp_area[:, ai[b['area']]] += eligible[:, j]
                matrices['direct'] += c @ sponsor.T
                matrices['opportunities'] += eligible @ sponsor.T
                matrices['shared'] += c @ c.T
                matrices['weighted'] += (c * weights) @ c.T
                matrices['conditional'] += (eligible * weights) @ c.T
                matrices['coeligible'] += eligible @ eligible.T
                for kind, indicator in (('cross', cross), ('same', same)):
                    matrices[kind+'_direct'] += (c * indicator) @ sponsor.T
                    matrices[kind+'_opportunities'] += (eligible * indicator) @ sponsor.T
            cursor = end
            union = matrices['conditional'] + matrices['conditional'].T - matrices['weighted']
            overlap = safe_ratio(matrices['weighted'], union); np.fill_diagonal(overlap, np.nan)
            proximity = network_proximity({'weighted_jaccard': overlap}, {})[0]
            selectivity = np.nan_to_num(safe_ratio(sig, opp_area))
            norm = np.linalg.norm(selectivity, axis=1)
            issues = safe_ratio(selectivity @ selectivity.T, norm[:, None] * norm[None, :])
            def bipartisan(i, j):
                rates = []
                for kind in ('cross', 'same'):
                    num = matrices[kind+'_direct'][i].sum() - matrices[kind+'_direct'][i, j]
                    den = matrices[kind+'_opportunities'][i].sum() - matrices[kind+'_opportunities'][i, j]
                    if den <= 0:
                        return None
                    rates.append((num + .5) / (den + 1))
                return rates[0] / sum(rates)
            for r in (r for r in rows if r['date'] == day):
                i, j = ix[r['actor']], ix[r['target']]; f = result[r['id']]
                if matrices['coeligible'][i, j] <= 0:
                    continue
                d, o = matrices['direct'], matrices['opportunities']
                f.update(direct_propensity=d[i,j]/o[i,j] if o[i,j] else None,
                         reverse_direct_propensity=d[j,i]/o[j,i] if o[j,i] else None,
                         weighted_shared_jaccard=overlap[i,j], network_proximity=proximity[i,j],
                         log_shared_bills=np.log1p(matrices['shared'][i,j]),
                         shared_original_bills=int(matrices['shared'][i,j]),
                         original_a_to_b=int(d[i,j]), original_b_to_a=int(d[j,i]),
                         opportunities_a_to_b=int(o[i,j]), opportunities_b_to_a=int(o[j,i]),
                         issue_similarity=issues[i,j], actor_bipartisan=bipartisan(i,j),
                         target_bipartisan=bipartisan(j,i), work_status='prior_original_work_available')
            audit['snapshots'].append(dict(chamber=chamber, before=day, bill_count=end))
            progress(f'{chamber} before {day}: {end:,} original-opportunity bills', flush=True)
        audit['bills_used_by_chamber'][chamber] = cursor
    return result, audit
