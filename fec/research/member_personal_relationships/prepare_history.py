"""Build a frozen, complete pair panel without running production builders."""
import json
from pathlib import Path
import numpy as np
from .data import ROOT,read_json,write_json,write_ndjson,digest
from .history_work import read_history,full_work,matched_percentiles,network_proximity

OUT=ROOT/'outputs/member_personal_relationships/20260910_full_history'
INPUTS=['outputs/member_personal_relationships/20260910_pilot/members.json',
        'outputs/member_personal_relationships/20260910_pilot/traits.json',
        'outputs/member_personal_relationships/20260910_anchored/anchor_events.ndjson',
        'outputs/cosponsor_challengers_20260905/bills.jsonl']


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    before={p:digest(ROOT/p) for p in INPUTS}
    members=read_json(ROOT/INPUTS[0]);bills,audit=read_history(ROOT/INPUTS[3],members,'2026-09-10')
    ids,work,by_congress,area=full_work(members,bills)
    matched,counts,peers=matched_percentiles(ids,members,work)
    raw,mp=network_proximity(work,peers)
    work['network_proximity']=raw;matched['network_proximity']=mp
    np.savez_compressed(OUT/'work_matrices.npz',**work,**{'pct_'+k:v for k,v in matched.items()},peer_count=counts,
        **{f'c{c}_{k}':v for c,vs in by_congress.items() for k,v in vs.items()},
        area_signatures=area['signatures'],area_opportunities=area['opportunities'])
    write_json(OUT/'matrix_index.json',dict(ids=ids,areas=area['areas']))
    write_json(OUT/'members.json',members);write_json(OUT/'traits.json',read_json(ROOT/INPUTS[1]))
    write_ndjson(OUT/'bills.ndjson',bills)
    after={p:digest(ROOT/p) for p in INPUTS}
    if before!=after:raise RuntimeError('Source changed during build')
    write_json(OUT/'work_manifest.json',dict(cutoff='2026-09-10',source_sha256=before,unchanged=True,
        audit=audit,members=len(ids),ordered_pairs=len(ids)*(len(ids)-1),
        matching='Actor fixed; same-party, same-state, same-chamber; 0.2-wide DW1 distance and 0.25-wide issue-similarity bins. Service and activity in denominators. Status reported for review.',
        work_available_directions=int(np.isfinite(work['shared_propensity']).sum()),
        matched_shared_directions=int(np.isfinite(matched['weighted_jaccard']).sum())))
    print(json.dumps(audit));print('Wrote full-history matrix panel',flush=True)


if __name__=='__main__':main()
