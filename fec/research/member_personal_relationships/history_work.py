"""Full-history descriptive cosponsorship. Import-safe; never writes production.

Uses the project's selectivity definition (signatures / eligible opportunities).
Distinct bill IDs survive. A service overlap, not a 30-day window, is required.
"""
import json
from collections import Counter
from datetime import date
import numpy as np


def congress_end(congress):
    return f'{1789 + 2 * congress:04d}-01-03'


def service_overlap(person, introduced, end, chamber):
    return any(t['chamber'] == chamber and max(t['start'], introduced) < min(t['end'], end)
               for t in person['terms'])


def served_on(person, day, chamber):
    return any(t['chamber'] == chamber and t['start'] <= day < t['end'] for t in person['terms'])


def read_history(path, members, cutoff):
    """Latest record per canonical bill ID; no title-based collapsing."""
    seen = {}; audit = Counter()
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            b = json.loads(line); audit['source_records'] += 1
            if not 116 <= b['congress'] <= 119 or b['introduced'] > cutoff:
                audit['outside_congress_or_cutoff'] += 1; continue
            key = b['key']
            if key in seen:
                audit['duplicate_bill_records'] += 1
                if (seen[key].get('updated') or '') > (b.get('updated') or ''): continue
            seen[key] = b
    bills = []
    for key, b in sorted(seen.items()):
        # Exclusive service end, inclusive data cutoff.
        end = min(congress_end(b['congress']), date.fromordinal(date.fromisoformat(cutoff).toordinal()+1).isoformat())
        valid = {}; withdrawal = {}; original = set()
        for c in b['cosponsors']:
            who, joined = c['member'], c.get('date')
            if not joined or not b['introduced'] <= joined < end:
                audit['invalid_or_post_cutoff_join'] += 1; continue
            if who == b['sponsor']:
                audit['self_signature'] += 1; continue
            if who in members and not served_on(members[who], joined, b['chamber']):
                audit['join_outside_dated_service'] += 1; continue
            valid[who] = min(joined, valid.get(who, joined))
            if c.get('original'): original.add(who)
            withdrawn = c.get('withdrawn')
            if withdrawn and joined <= withdrawn < end: withdrawal[who] = withdrawn
        title = next((t['text'] for t in b['titles'] if t['kind'].startswith('Short Title')), None)
        title = title or next((t['text'] for t in b['titles'] if t['kind'] == 'Official Title as Introduced'), '')
        bills.append(dict(key=key, congress=b['congress'], chamber=b['chamber'],
            sponsor=b['sponsor'], introduced=b['introduced'], end=end, title=title,
            area=b.get('policy_area') or 'Unknown', joins=valid, withdrawals=withdrawal,
            original=sorted(original), size=len(valid), updated=b.get('updated'),
            url=f"https://www.congress.gov/bill/{b['congress']}th-congress/{'house' if b['type']=='hr' else 'senate'}-bill/{b['number']}"))
        audit['joins_after_day_30'] += sum((date.fromisoformat(d)-date.fromisoformat(b['introduced'])).days > 30 for d in valid.values())
        audit['withdrawal_records'] += len(withdrawal)
    audit['included_bills'] = len(bills)
    audit['distinct_title_reintroductions_retained'] = len(bills) - len({(b['sponsor'], b['title'].casefold()) for b in bills})
    audit['bills_by_congress'] = dict(Counter(b['congress'] for b in bills))
    return bills, dict(audit)


def safe_ratio(num, den):
    return np.divide(num, den, out=np.full_like(np.asarray(num, dtype=float), np.nan), where=np.asarray(den)>0)


def full_work(members, bills, progress=print):
    ids = sorted(members); index = {a:i for i,a in enumerate(ids)}; n = len(ids)
    keys = ['direct', 'direct_opportunities', 'withdrawn_direct', 'shared', 'shared_active',
            'original_shared', 'weighted_shared', 'shared_opportunities', 'union', 'weighted_union',
            'shared_congresses', 'shared_areas', 'co_service_congresses']
    out = {k:np.zeros((n,n), dtype=float) for k in keys}; by_congress = {}
    areas = sorted({b['area'] for b in bills}); ai = {a:i for i,a in enumerate(areas)}
    area_sig = np.zeros((n,len(areas))); area_opp = np.zeros_like(area_sig)
    area_shared = {a:np.zeros((n,n), dtype=bool) for a in areas}
    for congress in sorted({b['congress'] for b in bills}):
        bs = [b for b in bills if b['congress'] == congress]; m = len(bs)
        # float32 is exact for these integer counts and reduces memory. Weighted
        # totals are descriptive; final outputs use float64 matrices.
        c = np.zeros((n,m), dtype=np.float32); eligible = np.zeros_like(c)
        sponsor = np.zeros_like(c); active = np.zeros_like(c); original = np.zeros_like(c)
        weights = np.array([1/max(1,b['size']-1) for b in bs],dtype=np.float32)
        for col,b in enumerate(bs):
            s = index.get(b['sponsor'])
            if s is not None: sponsor[s,col] = 1
            for i,a in enumerate(ids):
                if a != b['sponsor'] and service_overlap(members[a],b['introduced'],b['end'],b['chamber']):
                    eligible[i,col] = 1
            for a in b['joins']:
                i = index.get(a)
                if i is not None:
                    c[i,col] = 1; active[i,col] = int(a not in b['withdrawals'])
                    original[i,col] = int(a in b['original'])
            if np.any(c[:,col] > eligible[:,col]): raise ValueError('Signature outside eligible opportunity')
            jj = np.flatnonzero(c[:,col]); area_shared[b['area']][np.ix_(jj,jj)] = True
            area_sig[:,ai[b['area']]] += c[:,col]; area_opp[:,ai[b['area']]] += eligible[:,col]
        direct = c @ sponsor.T; opp = eligible @ sponsor.T
        shared = c @ c.T; weighted = (c*weights) @ c.T
        # Eligible excludes one's own bills, so these conditional denominators
        # also exclude bills sponsored by either member of the focal pair.
        conditional = eligible @ c.T
        weighted_conditional = (eligible*weights) @ c.T
        union = conditional + conditional.T - shared
        weighted_union = weighted_conditional + weighted_conditional.T - weighted
        out['direct'] += direct; out['direct_opportunities'] += opp
        out['withdrawn_direct'] += (c-active) @ sponsor.T
        out['shared'] += shared; out['shared_active'] += active @ active.T
        out['original_shared'] += original @ original.T
        out['weighted_shared'] += weighted; out['shared_opportunities'] += conditional
        out['union'] += union; out['weighted_union'] += weighted_union
        out['shared_congresses'] += shared > 0
        # There must actually be bills both could have joined.
        co_service = (eligible @ eligible.T)>0
        out['co_service_congresses'] += co_service
        by_congress[str(congress)] = dict(direct=direct, opportunities=opp, shared=shared,
            shared_opportunities=conditional, shared_active=active@active.T)
        progress(f'Congress {congress}: {m:,} bills, {int(c.sum()):,} signatures by target roster', flush=True)
    for a,v in area_shared.items(): out['shared_areas'] += v
    out['direct_rate'] = safe_ratio(out['direct'],out['direct_opportunities'])
    out['shared_propensity'] = safe_ratio(out['shared'],out['shared_opportunities'])
    out['shared_jaccard'] = safe_ratio(out['shared'],out['union'])
    out['weighted_jaccard'] = safe_ratio(out['weighted_shared'],out['weighted_union'])
    # Similarity between members' issue-area selectivity profiles is a context
    # control. It is not a personal edge and receives no hostility interpretation.
    selectivity = np.nan_to_num(safe_ratio(area_sig,area_opp))
    norm = np.linalg.norm(selectivity,axis=1)
    out['issue_similarity'] = safe_ratio(selectivity@selectivity.T, norm[:,None]*norm[None,:])
    for v in out.values(): np.fill_diagonal(v,np.nan)
    return ids,out,by_congress,dict(areas=areas, signatures=area_sig, opportunities=area_opp)


def percentile(value, peers):
    p = np.asarray(peers,dtype=float); p = p[np.isfinite(p)]
    if not np.isfinite(value) or len(p)<5: return None
    return float((np.sum(p < value-1e-10)+0.5*np.sum(np.abs(p-value)<=1e-10))/len(p))


def matched_percentiles(ids,members,work):
    """Fix actor, party/state/chamber relationship, ideological-distance bin and
    policy-profile overlap bin. Opportunity denominators handle service/activity.
    """
    n=len(ids); keys=['direct_rate','shared_propensity','weighted_jaccard']
    result={k:np.full((n,n),np.nan) for k in keys}; counts=np.zeros((n,n),int)
    peer_sets={}
    def group(i,j):
        a,b=members[ids[i]],members[ids[j]]
        distance=abs(a['d1']-b['d1']) if a.get('d1') is not None and b.get('d1') is not None else None
        issue=work['issue_similarity'][i,j]
        # Exact fixed strata, disclosed in the methodology. No fallback silently
        # drops geography or ideology when a group is sparse.
        return (a['party']==b['party'],a['state']==b['state'],a['chamber']==b['chamber'],
            None if distance is None else int(distance/.2),
            None if not np.isfinite(issue) else min(3,int(issue*4)))
    for i in range(n):
        groups={}
        for j in range(n):
            if i!=j: groups.setdefault(group(i,j),[]).append(j)
        for js in groups.values():
            for j in js:
                peers=[k for k in js if k!=j]; peer_sets[(i,j)] = peers; counts[i,j]=len(peers)
                for key in keys:
                    p=percentile(work[key][i,j],work[key][i,peers])
                    if p is not None: result[key][i,j]=p
    return result,counts,peer_sets


def network_proximity(work,peer_sets):
    """Weighted common neighbors in the complete observed co-work network.
    Cosine on weighted-Jaccard profiles; focal endpoints omitted in each dyad.
    """
    a=np.nan_to_num(work['weighted_jaccard']); np.fill_diagonal(a,0)
    dot=a@a.T; squares=(a*a).sum(axis=1)
    denominator=np.sqrt(np.maximum(0,(squares[:,None]-a*a)*(squares[None,:]-a.T*a.T)))
    raw=safe_ratio(dot,denominator); np.fill_diagonal(raw,np.nan)
    matched=np.full_like(raw,np.nan)
    for (i,j),peers in peer_sets.items():
        value=percentile(raw[i,j],raw[i,peers])
        if value is not None: matched[i,j]=value
    return raw,matched
