"""Recompute context comparisons without rebuilding raw legislative counts."""
import numpy as np
from .data import read_json,write_json
from .prepare_history import OUT
from .history_work import matched_percentiles,network_proximity


def main():
    members=read_json(OUT/'members.json');ids=read_json(OUT/'matrix_index.json')['ids']
    with np.load(OUT/'work_matrices.npz') as z:work={k:z[k] for k in z.files}
    matched,counts,peers=matched_percentiles(ids,members,work)
    raw,mp=network_proximity(work,peers);matched['network_proximity']=mp
    work.update({'pct_'+k:v for k,v in matched.items()});work['peer_count']=counts;work['network_proximity']=raw
    np.savez_compressed(OUT/'work_matrices.npz',**work)
    manifest=read_json(OUT/'work_manifest.json')
    manifest['matched_shared_directions']=int(np.isfinite(matched['weighted_jaccard']).sum())
    manifest['matching']='Actor fixed; same-party, same-state, same-chamber; 0.2-wide DW1 distance and 0.25-wide issue-similarity bins. Service and activity in denominators. Status reported for review.'
    write_json(OUT/'work_manifest.json',manifest)
    print(manifest['matched_shared_directions'],flush=True)


if __name__=='__main__':main()
