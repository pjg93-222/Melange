"""Build the reproducible 160-pair pilot from the frozen preparation outputs."""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict,deque
import hashlib
import itertools
import json
from pathlib import Path
import random

from .core import accepted_events,collapse_episodes,graph_features,personality_features,relationship_summary
from .data import ROOT,context,context_key,digest,read_json,write_json,write_ndjson
from .work import eligible_members,raw_pairs,build_residuals

SEED=20260910


def read_lines(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def personality_comparisons(members,traits):
    values={}; sums=defaultdict(lambda:[0.,0])
    for a in sorted(members):
        for b in sorted(members):
            if a==b:
                continue
            f=personality_features(traits[a],traits[b]); value=f["personality_similarity_eao"]
            # Match within sender, political distance, geography, chamber, status,
            # AND the exact observed trait set, so missing A is not an advantage.
            mask="".join(t for t in "EAO" if f["similarity_"+t] is not None)
            key=(a,context_key(members[a],members[b]),members[b]["chamber"],mask)
            values[(a,b)]=(value,key)
            if value is not None:
                sums[key][0]+=value; sums[key][1]+=1
    result={}
    for pair,(value,key) in values.items():
        total,n=sums[key]
        peer=(total-value)/(n-1) if value is not None and n>=6 else None
        result[pair]=dict(personality_similarity_eao=value,personality_matched_mean=peer,
                          personality_peer_count=n-1 if value is not None else 0,
                          personality_similarity_excess=value-peer if peer is not None else None)
    return result


def legacy_graph(members):
    names={v["name"]:k for k,v in members.items()}
    raw=read_json(ROOT/"member_references.json")["edges"]
    edges=[]; positive=defaultdict(set); negative=defaultdict(set)
    for r in raw:
        a,b=names.get(r["a"]),names.get(r["b"])
        if not a or not b or a==b:
            continue
        e=dict(r,actor=a,target=b); edges.append(e)
        if r["pos"]: positive[a].add(b)
        if r["neg"]: negative[a].add(b)
    return edges,positive,negative


def select_pilot(members,candidates,events,comparisons,raw_work,legacy,negative):
    used=set(); selected=[]
    def take(label,ranked):
        n=0
        for a,b in ranked:
            key=tuple(sorted((a,b)))
            if key in used or a==b:
                continue
            used.add(key); selected.append(dict(a=a,b=b,stratum=label)); n+=1
            if n==20: break
        return n
    counts={}
    counts["personal_story_candidates"]=take("personal_story_candidates",
        [(e["actor"],e["target"]) for e in events]+[(r["actor"],r["target"]) for r in candidates])
    counts["same_party_negative_references"]=take("same_party_negative_references",[
        (e["actor"],e["target"]) for e in sorted(legacy,key=lambda e:(-e["neg"],e["actor"],e["target"]))
        if e["neg"] and members[e["actor"]]["party"]==members[e["target"]]["party"]])
    counts["leadership_praise"]=take("leadership_praise",[
        (e["actor"],e["target"]) for e in sorted(legacy,key=lambda e:(-e["pos"],e["actor"],e["target"]))
        if e["pos"] and members[e["target"]]["leader"]])
    counts["distant_collaborators"]=take("distant_collaborators",[
        pair for pair,v in sorted(raw_work.items(),key=lambda x:(-x[1][1],x[0]))
        if v[1]>0 and not context(members[pair[0]],members[pair[1]])["same_state"]
        and (context(members[pair[0]],members[pair[1]])["nominate_distance"] or 0)>=0.5])
    all_pairs=list(itertools.combinations(sorted(members),2))
    rng=random.Random(SEED); rng.shuffle(all_pairs)
    counts["political_geographic_peers"]=take("political_geographic_peers",[(a,b) for a,b in all_pairs
        if members[a]["state"]==members[b]["state"] and members[a]["party"]==members[b]["party"]])
    counts["personality_candidates"]=take("personality_candidates",[
        pair for pair,f in sorted(comparisons.items(),key=lambda x:(-(x[1]["personality_similarity_excess"] or -10),x[0]))
        if f["personality_similarity_excess"] is not None])
    # Discovery-only use of signed public-reference graph. It never supplies
    # personal edges and its shared-enemy pattern has no assumed affinity sign.
    signed=sorted(all_pairs,key=lambda p:(-len(negative[p[0]] & negative[p[1]]),p))
    counts["signed_reference_proximity"]=take("signed_reference_proximity",signed)
    counts["random_pairs"]=take("random_pairs",all_pairs)
    return selected,counts


def apply_reviews(candidates,out):
    review=read_json(Path(__file__).with_name("review_decisions.json"))
    index={r["evidence_id"]:r for r in candidates}
    reviewed=[]
    official={r["evidence_id"]:r for r in read_json(Path(__file__).with_name("official_verification.json"))["records"]}
    for decision in review["decisions"]:
        if decision["evidence_id"] not in index:
            raise ValueError("Review evidence missing from extraction")
        row=dict(index[decision["evidence_id"]])
        row.update(decision); row["review_status"]="assistant_reviewed"
        if row["evidence_id"] in official:
            row["official_verification"]=official[row["evidence_id"]]
        reviewed.append(row)
    write_ndjson(out/"events.ndjson",reviewed)
    return reviewed


def path_diagnostic(adjacency,nodes):
    dist=Counter()
    for a in nodes:
        seen={a}; queue=deque([(a,0)])
        while queue:
            u,d=queue.popleft()
            for v in adjacency[u]-seen:
                seen.add(v); dist[d+1]+=1; queue.append((v,d+1))
        dist["unreachable"]+=len(nodes)-len(seen)
    return {str(k):v for k,v in sorted(dist.items(),key=lambda x:str(x[0]))}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="outputs/member_personal_relationships/20260910_pilot")
    args=parser.parse_args(); out=ROOT/args.out
    source=read_json(out/"source_manifest.json")
    for path,sha in source["source_sha256"].items():
        if digest(ROOT/path)!=sha: raise ValueError("Source changed since preparation: "+path)
    for path,sha in source.get("frozen_artifact_sha256",{}).items():
        if digest(out/path)!=sha: raise ValueError("Frozen extraction changed: "+path)
    members=read_json(out/"members.json"); traits=read_json(out/"traits.json")
    candidates=read_lines(out/"candidates.ndjson"); bills=read_lines(out/"bills.ndjson")
    reviewed=apply_reviews(candidates,out)
    events=accepted_events(reviewed,source["as_of"],source["start"])
    print("Building political comparisons for personality",flush=True)
    comparisons=personality_comparisons(members,traits)
    print("Constructing dated legislative opportunity sets",flush=True)
    eligibility=eligible_members(members,bills)
    work=raw_pairs(members,bills,eligibility)
    legacy,positive,negative=legacy_graph(members)
    pilot,strata=select_pilot(members,candidates,events,comparisons,work,legacy,negative)
    pairs=[pair for r in pilot for pair in ((r["a"],r["b"]),(r["b"],r["a"]))]
    print(f"Computing matched cooperation residuals for {len(pairs)} directions",flush=True)
    residuals,opportunities=build_residuals(members,bills,pairs,eligibility)
    write_ndjson(out/"opportunities.ndjson",opportunities)
    write_ndjson(out/"pilot_pairs.ndjson",pilot)
    features=[]; relations=[]; ablations=[]
    for a,b in pairs:
        f=dict(actor=a,target=b,actor_name=members[a]["name"],target_name=members[b]["name"],
               **context(members[a],members[b]),**personality_features(traits[a],traits[b]))
        f.update(comparisons[(a,b)]); f.update(residuals[(a,b)])
        families={e["source_family"] for e in events if {e["actor"],e["target"]}=={a,b}}
        f.update(graph_features(events,a,b,as_of=source["as_of"],excluded_families=families))
        f["public_reference_shared_negative_targets"]=len(negative[a]&negative[b])
        f["personal_graph_mask"]="focal pair both directions plus focal source families; no predicted edges"
        r=relationship_summary(a,b,events,f)
        r.update(actor_name=members[a]["name"],target_name=members[b]["name"],as_of=source["as_of"])
        features.append(f); relations.append(r)
        abl=dict(actor=a,target=b,full_score=r["affinity_candidate_score"])
        for name,changes in {"without_personality":{"personality_similarity_excess":None},
                             "without_network":{"positive_resource_allocation":0},
                             "without_work":{"work_residual_rate":None},
                             "work_7_days":{"work_residual_rate":f["work_residual_rate_7"]}}.items():
            abl[name]=relationship_summary(a,b,events,dict(f,**changes))["affinity_candidate_score"]
        abl["context_only"]=relationship_summary(a,b,[],context(members[a],members[b]))["affinity_candidate_score"]
        ablations.append(abl)
    # Mutual *declared affinity* is descriptive; do not equate it with mutual friendship.
    write_ndjson(out/"pair_features.ndjson",features)
    write_ndjson(out/"relationships.ndjson",relations)
    write_ndjson(out/"ablations.ndjson",ablations)
    reviewed_ids={r["evidence_id"] for r in reviewed}
    write_ndjson(out/"review_queue.ndjson",[r for r in candidates if r["evidence_id"] not in reviewed_ids])
    stats=dict(pilot_pairs=len(pilot),directed_assessments=len(pairs),strata=strata,
        human_gold_labels=0,predictive_accuracy=None,calibration=None,
        ablation_interpretation="engineering sensitivity only, not held-out predictive performance",
        reviewed_source_rows=len(reviewed),review_categories=dict(Counter(e["category"] for e in reviewed)),
        personal_seed_events=len(events),personal_seed_pairs=len({(e["actor"],e["target"]) for e in events}),
        personal_seed_independent_episodes=len(collapse_episodes(events)),
        affinity_status=dict(Counter(r["affinity"] for r in relations)),
        antagonism_status=dict(Counter(r["antagonism"] for r in relations)),
        work_baseline_available=sum(f["work_opportunities"]>0 for f in features),
        work_baseline_unavailable=sum(f["work_opportunities"]==0 for f in features),
        matched_work_observations=sum(f["work_opportunities"] for f in features),
        all_work_observations=sum(v[0] for v in work.values()),
        all_work_pairs=len(work),all_work_pairs_with_support=sum(v[1]>0 for v in work.values()),
        graph_pairs_with_indirect_positive_path=sum(f["positive_shortest_path"] is not None for f in features),
        legacy_edges=len(legacy),legacy_positive_path_distribution=path_diagnostic(positive,sorted(members)),
        personality_pair_coverage=sum(f["personality_similarity_eao"] is not None for f in features),
        personality_matched_coverage=sum(f["personality_similarity_excess"] is not None for f in features),
        context_only_nonzero=sum(a["context_only"]!=0 for a in ablations),
        personality_score_changes=sum(abs(a["full_score"]-a["without_personality"])>1e-9 for a in ablations),
        work_score_changes=sum(abs(a["full_score"]-a["without_work"])>1e-9 for a in ablations),
        network_score_changes=sum(abs(a["full_score"]-a["without_network"])>1e-9 for a in ablations))
    write_json(out/"results.json",stats)
    manifest=dict(source,results=stats,run_seed=SEED,
        source_hashes_verified=True,
        production_unchanged=all(digest(ROOT/p)==h for p,h in source["production_sha256"].items()),
        code_sha256={p.name:digest(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
        review_sha256=digest(Path(__file__).with_name("review_decisions.json")),
        official_verification_sha256=digest(Path(__file__).with_name("official_verification.json")),
        limitations=["No independently labeled friendship/antagonism test set; no accuracy or probability claim.",
          "Public personality estimates lack relationship-source holdouts; exploratory only.",
          "Work baseline controls actor, party, state, ideological bins, target leadership, chamber, and topic; committee roles, district mileage, donor networks, and bill-specific incentives remain.",
          "Current Voteview/role snapshot makes work residuals retrospective descriptions, not historical predictions.",
          "Original bill records were retrieved by another local pipeline; exact-title dedup is not semantic bill-family adjudication.",
          "Source dates and corpus speaker labels are not independently verified; selected source turns were reviewed by the assistant.",
          "Full-name retrieval misses surname-only, pronoun, and unmentioned personal ties; unknown is not neutral.",
          "Four sparse provisional personal seeds cannot validate a network-proximity or antagonism model."])
    artifacts=["relationships.ndjson","pair_features.ndjson","opportunities.ndjson","pilot_pairs.ndjson",
               "events.ndjson","coverage.ndjson","review_queue.ndjson","ablations.ndjson","results.json"]
    manifest["artifact_sha256"]={p:digest(out/p) for p in artifacts}
    write_json(out/"manifest.json",manifest)
    print(json.dumps(stats,indent=2),flush=True)


if __name__=="__main__":
    main()
