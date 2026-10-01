"""Marginal structural coalition coverage, not an estimated causal diffusion process."""
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from common import OLD, OUT, digest, log, read_json, stamp, write_json
from member_network import prior_graph
from build_panel import get_bills

NAME='network_marginal_coalition_coverage'


def marginal_coverage(a,active):
    maximum=a.max(axis=0)
    q=np.divide(a,maximum[None,:],out=np.zeros_like(a),where=maximum[None,:]>0)
    covered=q[np.asarray(active,dtype=bool)].max(axis=0) if np.any(active) else np.zeros(len(a))
    return np.maximum(q-covered[None,:],0).sum(axis=1)/max(1,len(a))


def from_dates(a,ids,joined,day):
    return marginal_coverage(a,np.array([joined.get(mid,10**9)<day for mid in ids]))


def build():
    receipt=OUT/'marginal_coverage_receipt.json'
    if receipt.exists():raise RuntimeError('Marginal coverage already frozen')
    bills=[b for b in get_bills() if b['congress']<=118];bykey={b['key']:b for b in bills};ids=read_json(OLD/'identifiers.json')
    result={}
    for cg in [117,118]:
        graphs={ch:prior_graph(bills,cg,ch) for ch in ['House','Senate']}
        m=pd.read_parquet(OLD/f'meta_{cg}.parquet');path=OUT/f'marginal_coverage_{cg}.f32'
        out=np.memmap(path,mode='w+',dtype=np.float32,shape=(len(m),1))
        for _,idx in m.groupby('group',sort=False).indices.items():
            first=m.iloc[idx[0]];b=bykey[ids['bills'][int(first.bill)]];g=graphs[b['chamber']];day=int(first.day)
            joined=dict(b['joins'])
            if b['intro']<day:joined[b['sponsor']]=b['intro']
            gain=from_dates(g['adjacency'],g['ids'],joined,day)
            out[idx,0]=[gain[g['index'][ids['members'][int(mid)]]] if ids['members'][int(mid)] in g['index'] else 0 for mid in m.member.iloc[idx]]
        out.flush();del out
        result[cg]=dict(rows=len(m),sha256=digest(path));log(f'Marginal structural coverage complete: Congress {cg}')
    write_json(receipt,dict(completed_utc=stamp(),features=[NAME],splits=result,source_sha256=digest(OLD/'bills.jsonl'),
        note='One-step submodular coverage gain beyond strictly earlier coalition; relationship weights are not causal transmission probabilities.'))


if __name__=='__main__':
    with threadpool_limits(limits=1):build()
