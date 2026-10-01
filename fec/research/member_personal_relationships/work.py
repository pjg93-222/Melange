"""Descriptive, matched cooperation residuals with the focal sponsor removed.

This is not a prospective cosponsorship model. All inputs are a frozen as-of
snapshot. Geography, ideology, and status are conditioning variables, never
bonuses. No-comparator observations stay unavailable.
"""
from collections import defaultdict
from datetime import timedelta
from math import sqrt
from .core import parse_date
from .data import context_key, term_at


def leave_pair_out_rate(cell, focal, broad, broad_focal, min_peers=20, smoothing=20):
    for n,y in (cell,focal,broad,broad_focal):
        if n<0 or y<0 or y>n:
            raise ValueError("Invalid successes/exposures")
    n,y=cell[0]-focal[0],cell[1]-focal[1]
    bn,by=broad[0]-broad_focal[0],broad[1]-broad_focal[1]
    if n<0 or y<0 or y>n or bn<0 or by<0 or by>bn:
        raise ValueError("Focal counts must be a subset of baseline counts")
    if bn<min_peers:
        return None
    return (y+smoothing*by/bn)/(n+smoothing)


def eligible_members(members,bills):
    cache={}
    for b in bills:
        key=(b["date"],b["chamber"])
        if key not in cache:
            end=(parse_date(b["date"])+timedelta(days=30)).isoformat()
            eligible=[]
            for bio,p in members.items():
                t=term_at(p,b["date"],b["chamber"])
                if t and t["end"]>end:
                    eligible.append(bio)
            cache[key]=eligible
    return cache


def raw_pairs(members,bills,eligibility):
    counts=defaultdict(lambda:[0,0])
    for b in bills:
        for actor in eligibility[(b["date"],b["chamber"])]:
            if actor==b["sponsor"]:
                continue
            pair=(actor,b["sponsor"])
            counts[pair][0]+=1
            counts[pair][1]+=int(actor in b["joins"])
    return dict(counts)


def build_residuals(members,bills,pairs,eligibility):
    pair_set=set(pairs)
    actors={a for a,b in pairs}
    cell=defaultdict(lambda:[0,0,0])
    broad=defaultdict(lambda:[0,0,0])
    focal=defaultdict(lambda:defaultdict(lambda:[0,0,0]))
    cached_context={(a,b):context_key(members[a],members[b]) for a in actors for b in members if a!=b}
    def add(bucket,y,y7):
        bucket[0]+=1; bucket[1]+=y; bucket[2]+=y7
    opportunities=[]
    for b in bills:
        target=b["sponsor"]
        for actor in eligibility[(b["date"],b["chamber"])]:
            if actor not in actors or actor==target:
                continue
            k=cached_context[(actor,target)]
            y=int(actor in b["joins"])
            y7=int(y and (parse_date(b["joins"][actor])-parse_date(b["date"])).days<=7)
            add(cell[(actor,k,b["area"])],y,y7)
            add(broad[(actor,k)],y,y7)
            if (actor,target) in pair_set:
                add(focal[(actor,target)][b["area"]],y,y7)
                opportunities.append(dict(actor=actor,target=target,bill=b["key"],introduced=b["date"],
                    area=b["area"],joined_30=y,joined_7=y7,source_updated=b.get("source_updated")))
    features={}
    for a,b in pairs:
        groups=focal[(a,b)]
        k=cached_context[(a,b)]
        own=[sum(v[j] for v in groups.values()) for j in range(3)]
        available=0; mu=0.; obs=0; mu7=0.; obs7=0; var=0.
        details=[]
        for area,v in sorted(groups.items()):
            p=leave_pair_out_rate(cell[(a,k,area)][:2],v[:2],broad[(a,k)][:2],own[:2])
            p7=leave_pair_out_rate((cell[(a,k,area)][0],cell[(a,k,area)][2]),(v[0],v[2]),
                                   (broad[(a,k)][0],broad[(a,k)][2]),(own[0],own[2]))
            details.append(dict(area=area,opportunities=v[0],observed=v[1],expected_rate=p,
                                matched_peer_opportunities=cell[(a,k,area)][0]-v[0]))
            if p is not None:
                available+=v[0]; mu+=v[0]*p; obs+=v[1]; var+=v[0]*p*(1-p)
                mu7+=v[0]*p7; obs7+=v[2]
        features[(a,b)]=dict(work_total_opportunities=own[0],work_total_observed=own[1],
            work_opportunities=available,work_observed=obs,work_expected=round(mu,6),
            work_residual_rate=(obs-mu)/available if available else None,
            work_residual_rate_7=(obs7-mu7)/available if available else None,
            work_residual_standardized=(obs-mu)/sqrt(var) if var else None,
            work_baseline_status="matched_descriptive" if available else "unavailable_no_comparators",
            work_baseline_context=dict(member_fixed=a,same_party=k[0],same_state=k[1],
                                       nominate_distance_bin=k[2],target_leader=k[3]),
            work_areas=details,
            work_uncertainty="standardized residual is descriptive, not a p-value; bill dependence remains")
    return features,opportunities
