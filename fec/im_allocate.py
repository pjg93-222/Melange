import json,sys,heapq,math,openpyxl
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
# ---- dials ----
BUDGET=2_000_000; INC=1000; CAP=50_000; MODE='FLIP'
PERS={'Neutral':1.0,'Skeptic':0.85,'Unengaged':0.55,'Ally':0.45,'Champion':0.20,'Opponent':0.10}
# ---- inputs ----
C={m['member']:m for m in json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\congestion.json'))}
wb=openpyxl.load_workbook(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx',data_only=True)
bm=wb['Blended Model']; ra=wb['Rank & Allocation']
stance={ra.cell(r,1).value:ra.cell(r,7).value for r in range(3,536) if ra.cell(r,1).value}
M={}
for r in range(3,536):
    n=bm.cell(r,1).value
    if not n or n not in C: continue
    s=bm.cell(r,19).value or 0           # blended score = strategic value
    st=stance.get(n,'Neutral'); c=C[n]
    ind=(c['banks'] or 0)+(c['finserv'] or 0)   # B-side: industry money (absolute)
    cu=c['cu'] or 0                              # A-side baseline
    M[n]=dict(score=s,stance=st,pers=PERS.get(st,0.5),ind=ind,cu=cu,
              target=s*PERS.get(st,0.5))         # FLIP target = strategic value x persuadability
# money -> access weight (Kalla-Broockman: concave, diminishing returns => submodular)
def w(d): return math.sqrt(d+1.0)
def pflip(cu,alloc,ind): a=w(cu+alloc); return a/(a+w(ind))
# greedy allocation under selected mode
alloc={n:0 for n in M}
def marg(n):
    m=M[n]
    if alloc[n]>=CAP: return 0.0
    return m['target']*(pflip(m['cu'],alloc[n]+INC,m['ind'])-pflip(m['cu'],alloc[n],m['ind']))
heap=[(-marg(n),n) for n in M]; heapq.heapify(heap)
spent=0; flips0=sum(M[n]['target']*pflip(M[n]['cu'],0,M[n]['ind']) for n in M)
while spent<BUDGET and heap:
    g,n=heapq.heappop(heap)
    if -g<=0: break
    alloc[n]+=INC; spent+=INC
    heapq.heappush(heap,(-marg(n),n))
fund=[(n,alloc[n]) for n in M if alloc[n]>0]; fund.sort(key=lambda x:-x[1])
flips1=sum(M[n]['target']*pflip(M[n]['cu'],alloc[n],M[n]['ind']) for n in M)
print('MODE=%s  spent $%s  funded %d members  cap $%s'%(MODE,f'{spent:,}',len(fund),f'{CAP:,}'))
print('expected influence-weighted flip score: %.1f -> %.1f  (+%.1f)'%(flips0,flips1,flips1-flips0))
print('\nTOP 20 ALLOCATIONS (flip mode = influential, persuadable, contestable):')
print('   %-22s %8s  stance      P_flip 0->fund   ind$/cu$'%('member','alloc'))
for n,a in fund[:20]:
    m=M[n]
    print('   %-22s $%7s  %-10s  %.2f->%.2f   $%s/$%s'%(n,f'{a:,}',m['stance'],pflip(m['cu'],0,m['ind']),pflip(m['cu'],a,m['ind']),f"{m['ind']:,}",f"{m['cu']:,}"))
out={n:alloc[n] for n in M if alloc[n]>0}
json.dump(out,open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\im_allocation.json','w'))
# contrast: how different from naive top-by-score?
naive=set(sorted(M,key=lambda n:-M[n]['score'])[:len(fund)])
chosen=set(dict(fund)); print('\nfunded but NOT in naive top-%d-by-score (the flip engine targets these): %d'%(len(fund),len(chosen-naive)))
print('  e.g.:',[n for n in list(chosen-naive)[:8]])
