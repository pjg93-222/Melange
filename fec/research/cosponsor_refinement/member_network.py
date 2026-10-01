"""Dated member-network structure and exposure to earlier cosponsors."""
import collections
import datetime as dt
import json

import numpy as np
import pandas as pd
from scipy.sparse import csgraph
from threadpoolctl import threadpool_limits

from common import OLD, OUT, digest, log, read_json, stamp, write_json
from build_panel import get_bills

NAMES=['network_degree','network_log_strength','network_pagerank','network_eigenvector_component',
       'network_component_size','network_isolate','network_sponsor_pagerank','network_sponsor_eigenvector',
       'network_sponsor_tie','network_active_weight_share','network_active_count','network_active_7d_share',
       'network_active_30d_share','network_active_centrality_share','network_two_hop_exposure',
       'network_residual_reach','network_crossparty_active_share']


def centrality(a):
    n=len(a);strength=a.sum(axis=1);degree=(a>0).sum(axis=1)
    transition=np.divide(a,strength[:,None],out=np.zeros_like(a),where=strength[:,None]>0)
    p=np.full(n,1/n)
    for _ in range(1000):
        q=.15/n+.85*(transition.T@p+p[strength==0].sum()/n)
        if np.abs(q-p).sum()<1e-11:break
        p=q
    else:raise RuntimeError('PageRank did not converge')
    ncomp,labels=csgraph.connected_components(a,directed=False)
    e=np.zeros(n);sizes=np.zeros(n)
    for component in range(ncomp):
        idx=np.flatnonzero(labels==component);sizes[idx]=len(idx)
        if len(idx)<2:continue
        vals,vecs=np.linalg.eigh(a[np.ix_(idx,idx)])
        v=np.abs(vecs[:,-1]);v/=v.sum()
        residual=np.linalg.norm(a[np.ix_(idx,idx)]@v-vals[-1]*v)
        if residual>1e-7:raise RuntimeError('Eigenvector residual exceeds tolerance')
        e[idx]=v
    # An isolate's teleport mass is not presented as structural connectedness.
    p[strength==0]=0
    return dict(degree=degree,strength=strength,transition=transition,pagerank=p,eigenvector=e,
                component_size=sizes,isolate=(strength==0).astype(float))


def prior_graph(bills,cg,chamber):
    prior=[b for b in bills if b['congress']==cg-1 and b['chamber']==chamber]
    ids=sorted({mid for b in prior for mid in [b['sponsor'],*b['joins']] if mid})
    index={mid:i for i,mid in enumerate(ids)}
    a=np.zeros((len(ids),len(ids)),dtype=np.float64)
    end=dt.date(1789+2*(cg-1),1,3).toordinal()
    for b in prior:
        joiners=[mid for mid,day in b['joins'].items() if mid!=b['sponsor'] and day<end]
        if not b['sponsor'] or not joiners:continue
        s=index[b['sponsor']];jj=[index[mid] for mid in joiners]
        a[s,jj]+=1/len(jj);a[jj,s]+=1/len(jj)
    return dict(ids=ids,index=index,adjacency=a,**centrality(a))


def exposure(graph,joined,day,sponsor,parties):
    joined={mid:d for mid,d in joined.items() if d<day}
    ids=graph['ids'];index=graph['index'];a=graph['adjacency'];n=len(ids)
    active=np.array([mid in joined for mid in ids],dtype=float)
    recent7=np.array([day-7<=joined.get(mid,-1)<day for mid in ids],dtype=float)
    recent30=np.array([day-30<=joined.get(mid,-1)<day for mid in ids],dtype=float)
    p=graph['transition'];e=graph['eigenvector'];strength=graph['strength']
    active_share=p@active
    weighted=a*e[None,:]
    central_share=np.divide(weighted@active,weighted.sum(axis=1),out=np.zeros(n),where=weighted.sum(axis=1)>0)
    # One- and two-hop weighted exposure are structural, not calibrated diffusion probabilities.
    two=p@active_share
    residual=p@(1-active_share)
    cross=np.zeros(n)
    for party in set(parties.values()):
        opposite=np.array([active[i] and mid in parties and parties[mid]!=party for i,mid in enumerate(ids)],dtype=float)
        rows=np.array([parties.get(mid)==party for mid in ids])
        cross[rows]=(p@opposite)[rows]
    s=index.get(sponsor)
    features=np.column_stack([np.log1p(graph['degree']),np.log1p(strength),graph['pagerank'],e,
         graph['component_size']/max(1,n),graph['isolate'],
         np.full(n,graph['pagerank'][s] if s is not None else 0),np.full(n,e[s] if s is not None else 0),
         p[:,s] if s is not None else np.zeros(n),active_share,np.log1p((a>0)@active),p@recent7,p@recent30,
         central_share,two,residual,cross]).astype(np.float32)
    return features


def build():
    if (OUT/'member_network_receipt_v2.json').exists():raise RuntimeError('Member network sidecar exists')
    # Only 116-118 outcomes enter this development extension.
    bills=[b for b in get_bills() if b['congress']<=118]
    bykey={b['key']:b for b in bills};ident=read_json(OLD/'identifiers.json')
    member_ids=ident['members'];keys=ident['bills']
    from build_panel import get_members,term_at
    members,_=get_members()
    receipts={}
    for cg in [117,118]:
        graphs={ch:prior_graph(bills,cg,ch) for ch in ['House','Senate']}
        for ch,g in graphs.items():
            np.savez_compressed(OUT/f'member_graph_{cg}_{ch.lower()}.npz',ids=g['ids'],adjacency=g['adjacency'],
                                pagerank=g['pagerank'],eigenvector_component=g['eigenvector'],component_size=g['component_size'])
        m=pd.read_parquet(OLD/f'meta_{cg}.parquet')
        path=OUT/f'member_network_v2_{cg}.f32'
        result=np.memmap(path,mode='w+',dtype=np.float32,shape=(len(m),len(NAMES)))
        missing=0
        for i,(group,idx) in enumerate(m.groupby('group',sort=False).indices.items()):
            rows=m.iloc[idx];bill=bykey[keys[int(rows.bill.iloc[0])]];day=int(rows.day.iloc[0]);ch=bill['chamber'];g=graphs[ch]
            joined={mid:d for mid,d in bill['joins'].items() if d<day}
            # Include the initiating sponsor as active from introduction, before forecast day only.
            if bill['intro']<day:joined[bill['sponsor']]=bill['intro']
            parties={}
            for mid in g['ids']:
                term=term_at(members[mid],day,ch) if mid in members else None
                if term:parties[mid]=term['party']
            table=exposure(g,joined,day,bill['sponsor'],parties)
            codes=np.array([g['index'].get(member_ids[int(mid)],-1) for mid in rows.member])
            block=np.zeros((len(idx),len(NAMES)),dtype=np.float32);valid=codes>=0
            block[valid]=table[codes[valid]];block[~valid,NAMES.index('network_isolate')]=1
            missing+=int((~valid).sum());result[idx]=block
            if (i+1)%4000==0:log(f'Member network {cg}: {i+1} bill-date groups')
        result.flush();del result
        receipts[cg]=dict(rows=len(m),missing_prior_member_rows=missing,sha256=digest(path),
                         graph_nodes={ch:len(g['ids']) for ch,g in graphs.items()})
        log(f'Member network complete {cg}: {receipts[cg]}')
    write_json(OUT/'member_network_receipt_v2.json',dict(completed_utc=stamp(),features=NAMES,splits=receipts,
               source_sha256=digest(OLD/'bills.jsonl'),note='Preceding-Congress member edges; current-bill signatures strictly earlier than forecast. No staff data or sign-derived lobbying contact flags.'))


if __name__=='__main__':
    with threadpool_limits(limits=1):build()
