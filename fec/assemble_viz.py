import json,sys,math,collections,glob,os,openpyxl
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
WM,WP=0.6,0.4; CAP=50000
PERS={'Neutral':1.0,'Skeptic':0.85,'Unengaged':0.55,'Ally':0.45,'Champion':0.20,'Opponent':0.10}
PRO={'Champion','Ally'}; ANTI={'Opponent','Skeptic'}
C={m['member']:m for m in json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\congestion.json'))}
bio2name={m['bioguide']:m['member'] for m in C.values() if m['bioguide']}
AL=json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\im_allocation.json'))
flip=AL['flip']; coal=AL['coalition']
wb=openpyxl.load_workbook(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx',data_only=True)
ra=wb['Rank & Allocation']
stance={ra.cell(r,1).value:ra.cell(r,7).value for r in range(3,536) if ra.cell(r,1).value}
members=[m['member'] for m in C.values()]
ind={n:(C[n]['banks'] or 0)+(C[n]['finserv'] or 0) for n in members}
cu={n:(C[n]['cu'] or 0) for n in members}
st={n:stance.get(n,'Neutral') for n in members}
camp={n:('pro' if st[n] in PRO else 'anti' if st[n] in ANTI else 'neu') for n in members}
net=max(glob.glob(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\congress_cosponsor_network_*.xlsx'),key=os.path.getmtime)
ne=openpyxl.load_workbook(net,data_only=True)['Edges']
adj=collections.defaultdict(dict); mem=set(members)
for r in range(2,ne.max_row+1):
    a,b,w=ne.cell(r,1).value,ne.cell(r,2).value,ne.cell(r,3).value
    a=bio2name.get(a); b=bio2name.get(b)
    if a in mem and b in mem and a!=b and isinstance(w,(int,float)):
        w=(adj[a][b]+w)/2 if b in adj[a] else w   # D2 2026-07-01: 41 reverse-dup pairs carry ASYMMETRIC directed weights (up to 3x) -- mean-symmetrize (was silent last-write-wins)
        adj[a][b]=w; adj[b][a]=w
nbrA={n:sum(w for u,w in adj[n].items() if camp[u]=='pro') for n in members}
nbrB={n:sum(w for u,w in adj[n].items() if camp[u]=='anti') for n in members}
mA=max(nbrA.values()) or 1; mB=max(nbrB.values()) or 1
moneyM=max(math.sqrt(cu[n]+CAP) for n in members) or 1; moneyB=max(math.sqrt(ind[n]+1) for n in members) or 1
def pf(n,al):
    a=WM*math.sqrt(cu[n]+al+1)/moneyM+WP*nbrA[n]/mA; b=WM*math.sqrt(ind[n]+1)/moneyB+WP*nbrB[n]/mB
    return a/(a+b) if a+b>0 else 0
rows=[]
for n in members:
    fa=flip.get(n,0); ca=coal.get(n,0)
    if fa<=0 and ca<=0: continue
    rows.append([n,st[n][:4],fa,ca,round(pf(n,0),2),round(pf(n,fa),2),C[n]['net_lean']])
json.dump({'rows':rows,'flipTot':sum(flip.values()),'coalTot':sum(coal.values()),'flipN':len(flip),'coalN':len(coal)},
          open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\imviz.json','w'),separators=(',',':'),ensure_ascii=False)
print('rows',len(rows),'| flip $%s / %d  coal $%s / %d'%(f"{sum(flip.values()):,}",len(flip),f"{sum(coal.values()):,}",len(coal)),'| bytes',os.path.getsize(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\imviz.json'))
