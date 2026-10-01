"""Join the historical shared-broadcast graph to frozen candidate rows."""
import numpy as np
import pandas as pd
import networkx as nx
from pathlib import Path

from universe_common import OLD, OUT, digest, log, read_json, stamp, write_json
from build_panel import get_bills

COUNTS=['rel_unique_turns','rel_words','rel_observed_episodes','rel_qualifying_episodes','rel_shared_episodes',
        'rel_degree','rel_raw_strength','rel_normalized_strength']
COVERAGE=['rel_observed_coverage','rel_qualifying_coverage','rel_shared_coverage']
STATIC=[name+'_log' for name in COUNTS]+COVERAGE+['rel_pagerank','rel_component_eigenvector']
DYNAMIC=['rel_sponsor_tie','rel_sponsor_observed','rel_prior_coalition_exposure','rel_prior_coalition_max_tie','rel_recent30_exposure']
FEATURES=STATIC+DYNAMIC


def exposure(adjacency,idx,coalition):
    total=adjacency.sum(axis=1)
    if not len(coalition):return np.zeros(len(idx),dtype=np.float32),np.zeros(len(idx),dtype=np.float32)
    edges=adjacency[np.ix_(idx,coalition)]
    return np.divide(edges.sum(axis=1),total[idx],out=np.zeros(len(idx),dtype=np.float32),where=total[idx]>0),edges.max(axis=1)


def build():
    if (OUT/'relational_panel_receipt.json').exists():raise RuntimeError('Relational panel already frozen')
    ids=read_json(OLD/'identifiers.json');bills={b['key']:b for b in get_bills() if b['congress']<=118};receipts={}
    source_receipt=read_json(OUT/'relational_receipt.json')
    source_hash=digest(OUT/'relational_receipt.json')
    expected={Path(item['path']).name:item['sha256'] for item in source_receipt['outputs']}
    for cg in [117,118]:
        for name in [f'relational_graph_{cg}.npz',f'relational_members_{cg}.csv']:
            assert digest(OUT/name)==expected[name],name
    for cg in [117,118]:
        graph=np.load(OUT/f'relational_graph_{cg}.npz');gids=graph['ids'].tolist();lookup={mid:i for i,mid in enumerate(gids)}
        assert int(graph['congress'])==cg
        assert str(graph['cutoff_exclusive'])==('2021-01-03' if cg==117 else '2023-01-03')
        assert str(graph['window_start'])==('2019-01-03' if cg==117 else '2021-01-03')
        adjacency=graph['adjacency'];assert np.allclose(adjacency,adjacency.T) and np.all(np.diag(adjacency)==0)
        assert np.isfinite(adjacency).all() and adjacency.min()>=0
        members=pd.read_csv(OUT/f'relational_members_{cg}.csv').set_index('bioguide').reindex(gids)
        # Historical graph nodes include observed former members; all nodes affect centrality.
        g=nx.from_numpy_array(adjacency)
        pr=nx.pagerank(g,alpha=.85,weight='weight')
        eig=np.zeros(len(gids))
        for component in nx.connected_components(g):
            ix=np.array(sorted(component),dtype=int)
            if len(ix)<2:continue
            _,v=np.linalg.eigh(adjacency[np.ix_(ix,ix)].astype(float));v=np.abs(v[:,-1]);eig[ix]=v/v.sum()
        static=np.column_stack([np.log1p(members[c].fillna(0).to_numpy()) for c in COUNTS]+
            [members[c].fillna(0).to_numpy() for c in COVERAGE]+[np.array([pr[i] for i in range(len(gids))]),eig]).astype(np.float32)
        m=pd.read_parquet(OLD/f'meta_{cg}.parquet');member_map=np.array([lookup.get(mid,-1) for mid in ids['members']],dtype=int)
        rows=member_map[m.member.to_numpy()];assert np.all(rows>=0),'Candidate member omitted from historical roster'
        path=OUT/f'relational_panel_{cg}.f32';a=np.memmap(path,mode='w+',dtype=np.float32,shape=(len(m),len(FEATURES)))
        a[:,:len(STATIC)]=static[rows];a[:,len(STATIC):]=0
        for _,ix in m.groupby('group',sort=False).indices.items():
            first=m.iloc[ix[0]];bill=bills[ids['bills'][int(first.bill)]];day=int(first.day);candidates=rows[ix]
            sponsor=lookup.get(bill['sponsor']);coalition=[lookup[mid] for mid,d in bill['joins'].items() if d<day and mid in lookup]
            recent=[lookup[mid] for mid,d in bill['joins'].items() if day-30<=d<day and mid in lookup]
            if sponsor is not None:
                a[ix,len(STATIC)]=adjacency[candidates,sponsor]
                a[ix,len(STATIC)+1]=static[sponsor,STATIC.index('rel_observed_coverage')]
            e,maxedge=exposure(adjacency,candidates,coalition);r,_=exposure(adjacency,candidates,recent)
            a[ix,len(STATIC)+2:]=np.column_stack([e,maxedge,r])
        a.flush();del a
        receipts[cg]=dict(rows=len(m),graph_members=len(gids),sha256=digest(path),
             graph_sha256=digest(OUT/f'relational_graph_{cg}.npz'),member_csv_sha256=digest(OUT/f'relational_members_{cg}.csv'))
        log(f'Historical media relationships joined to Congress {cg} forecasts')
    assert digest(OUT/'relational_receipt.json')==source_hash,'Extractor receipt changed during panel build'
    for cg in [117,118]:
        for name in [f'relational_graph_{cg}.npz',f'relational_members_{cg}.csv']:
            assert digest(OUT/name)==expected[name],name
    write_json(OUT/'relational_panel_receipt.json',dict(completed_utc=stamp(),features=FEATURES,splits=receipts,
      extractor_receipt_sha256=source_hash,code_sha256=digest(__file__),
      qualification='Shared broadcast, not verified interaction. Prior two-year graph. Coalition exposure includes earlier cosponsors only, with sponsor tie separate; current joins strictly before forecast. Eigenvector normalized L1 separately by connected component; PageRank on normalized undirected graph.'))


if __name__=='__main__':build()
