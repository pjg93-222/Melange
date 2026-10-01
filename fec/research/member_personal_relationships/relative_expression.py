"""Reviewed, source-separated expression as a personality interaction.

Raw lexical cues are deliberately ineligible. This module estimates descriptive
contrasts, not sincerity, private affection, or an automatically signed edge.
"""
from collections import defaultdict
from math import log


def _logit(p):
    return log(p / (1 - p))


def relative_contrast(n, positive, other_n, other_positive, strength=5.):
    if strength <= 0:
        raise ValueError('Shrinkage strength must be positive')
    if any(not isinstance(x, int) or x < 0 for x in (n, positive, other_n, other_positive)):
        raise ValueError('Counts must be nonnegative integers')
    if positive > n or other_positive > other_n:
        raise ValueError('Positive episodes exceed opportunities')
    if not n or not other_n:
        return dict(contrast=None, baseline_rate=None, target_rate=None,
                    target_n=n, other_n=other_n, data_fraction=n/(n+strength))
    baseline = (other_positive + .5) / (other_n + 1)
    target = (positive + strength * baseline) / (n + strength)
    return dict(contrast=_logit(target)-_logit(baseline), baseline_rate=baseline,
                target_rate=target, target_n=n, other_n=other_n,
                data_fraction=n/(n+strength))


def reviewed_expression(rows, traits, excluded_episodes=(), excluded_families=(), before=None):
    """Exclude outcomes globally, then count reviewed authored target episodes.

    before is exclusive. Missing or ambiguous attribution cannot create either
    a positive or a zero in the baseline. Repetitions within an episode collapse.
    """
    excluded_episodes, excluded_families = set(excluded_episodes), set(excluded_families)
    units = {}
    for row in rows:
        if row.get('review_status') != 'context_reviewed':
            continue
        required = ('actor', 'target', 'venue', 'episode_id', 'source_family', 'date')
        if any(not row.get(k) for k in required):
            raise ValueError('Reviewed interactions require identity/date/source provenance')
        if row['episode_id'] in excluded_episodes or row['source_family'] in excluded_families:
            continue
        if before is not None and row['date'] >= before:
            continue
        if (row['actor'] == row['target'] or not row.get('speaker_verified') or
                not row.get('target_verified') or row.get('quoted_only') or
                row.get('content_status') != 'resolved'):
            continue
        if any(type(row.get(k)) is not bool for k in ('substantive_warmth', 'personal_hostility')):
            raise ValueError('Resolved review needs explicit warmth and hostility decisions')
        key = (row['actor'], row['target'], row['venue'], row['episode_id'])
        current = units.setdefault(key, dict(warmth=False, hostility=False))
        current['warmth'] |= row['substantive_warmth']
        current['hostility'] |= row['personal_hostility']
    counts = defaultdict(lambda: dict(n=0, warmth=0, hostility=0))
    totals = defaultdict(lambda: dict(n=0, warmth=0, hostility=0))
    for (a, b, venue, episode), values in units.items():
        for target in (counts[(a,b,venue)], totals[(a,venue)]):
            target['n'] += 1
            for k in ('warmth','hostility'):
                target[k] += int(values[k])
    output = {}
    for (a,b,v), count in sorted(counts.items()):
        total = totals[(a,v)]
        row = dict(actor=a, target=b, venue=v, counts=dict(count),
                   other_counts={k:total[k]-count[k] for k in count},
                   probability_of_sincerity=None)
        for kind in ('warmth','hostility'):
            row[kind] = relative_contrast(count['n'],count[kind],
                                         total['n']-count['n'],total[kind]-count[kind])
            contrast = row[kind]['contrast']
            for trait in ('E','A'):
                value = traits.get(a,{}).get(trait)
                row[kind+'_x_'+trait] = contrast*value if contrast is not None and value is not None else None
        output[(a,b,v)] = row
    for (a,b,v), row in output.items():
        reverse = output.get((b,a,v),{}).get('warmth',{}).get('contrast')
        forward = row['warmth']['contrast']
        row['reciprocal_warmth'] = (min(max(forward,0.),max(reverse,0.))
                                   if forward is not None and reverse is not None else None)
    return list(output.values())


def expression_features(rows):
    """Equal-venue summaries, with explicit missingness and contribution counts."""
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r['actor'],r['target'])].append(r)
    output = {}
    for pair,venues in grouped.items():
        values = {}
        for key in ('relative_warmth','relative_hostility','warmth_x_E','warmth_x_A',
                    'hostility_x_A','reciprocal_warmth'):
            raw = ([r[key.replace('relative_','')]['contrast'] for r in venues]
                   if key.startswith('relative_') else [r[key] for r in venues])
            available = [x for x in raw if x is not None]
            values[key] = sum(available)/len(available) if available else None
            values[key+'_venue_n'] = len(available)
        output[pair] = values
    return output


def leadership_tension(same_party, actor_support, target_challenge):
    """Dated independently coded inputs; unknown support/challenge stays unknown."""
    if not same_party:
        return 0.
    if actor_support is None or target_challenge is None:
        return None
    if actor_support not in (0,1) or target_challenge not in (0,1):
        raise ValueError('Leadership support/challenge must be reviewed binary facts')
    return float(actor_support * target_challenge)
