import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
import json,glob,os,sys,openpyxl
import networkx as nx
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
M={m['bioguide']:m for m in json.load(open(MB_ROOT+r'\congestion.json')) if m['bioguide']}
wb=openpyxl.load_workbook(MB_ROOT+r'\Moneyball Main Version - Blended.xlsx',data_only=True)
cen=wb['Centrality']
infl={cen.cell(r,1).value:(cen.cell(r,3).value or 0) for r in range(2,cen.max_row+1) if cen.cell(r,1).value}
net=max(glob.glob(MB_ROOT+r'\congress_cosponsor_network_*.xlsx'),key=os.path.getmtime)
ne=openpyxl.load_workbook(net,data_only=True)['Edges']
keep=set(M)
G=nx.Graph(); G.add_nodes_from(keep)
for r in range(2,ne.max_row+1):
    a,b,wt=ne.cell(r,1).value,ne.cell(r,2).value,ne.cell(r,3).value
    if a in keep and b in keep and a!=b and isinstance(wt,(int,float)):
        if G.has_edge(a,b): G[a][b]['weight']+=wt
        else: G.add_edge(a,b,weight=wt)
print('nodes',G.number_of_nodes(),'edges',G.number_of_edges())
pos=nx.spring_layout(G,k=1.1/(len(keep)**0.5),iterations=80,seed=7,weight='weight')
xs=[p[0] for p in pos.values()]; ys=[p[1] for p in pos.values()]
mnx,mxx,mny,mxy=min(xs),max(xs),min(ys),max(ys)
W,Hh=940,640; pad=24
def sx(x): return round(pad+(x-mnx)/(mxx-mnx)*(W-2*pad),1)
def sy(y): return round(pad+(y-mny)/(mxy-mny)*(Hh-2*pad),1)
idx={b:i for i,b in enumerate(G.nodes())}
nodes=[]
for b in G.nodes():
    m=M[b]; iv=infl.get(b,0)
    r=round(2+ (iv/100)*9,1)
    nodes.append([m['member'],int(round(sx(pos[b][0]))),int(round(sy(pos[b][1]))),r,m['net_lean'],m['total']])
ew=sorted(G.edges(data=True),key=lambda e:-e[2].get('weight',0))[:650]
edges=[[idx[a],idx[b]] for a,b,_ in ew]
json.dump({'n':nodes,'e':edges,'W':W,'H':Hh},open(MB_ROOT+r'\sna_compact.json','w'),separators=(',',':'),ensure_ascii=False)
import os
print('wrote sna_compact.json:',len(nodes),'nodes',len(edges),'edges,',os.path.getsize(MB_ROOT+r'\sna_compact.json'),'bytes')
# quick stats
lean=[n[4] for n in nodes if n[4] is not None]
print('net_lean: CU-leaning(>0) %d | captured(<0) %d | neutral/none %d'%(sum(1 for l in lean if l>0),sum(1 for l in lean if l<0),len(nodes)-len(lean)))
