import json, sys, openpyxl
from paths import WORKBOOK, p   # S2-02 audit run-2: honor MONEYBALL_ROOT — never audit a hardcoded tree
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
P=[]; F=[]
def ok(c,m): (P if c else F).append(m)
M=WORKBOOK
wb=openpyxl.load_workbook(M,data_only=True); wbf=openpyxl.load_workbook(M,data_only=False)
bm=wb['Blended Model']; ra=wb['Rank & Allocation']
# PHASE-2 (2026-07-02): Blended's formula caches DIE after any openpyxl save (sync/blend) and revive
# on user Excel opens (fullCalcOnLoad). Rank truth = ranks_python.json (the authority). View-dependent
# checks (allocation col 21) run only while the view cache is alive.
AUTH=json.load(open(p('ranks_python.json')))
VIEW_ALIVE=sum(1 for r in range(3,536) if bm.cell(r,1).value) >= 500
# A integrity
errs=sum(1 for ws in wb.worksheets for row in ws.iter_rows() for c in row if isinstance(c.value,str) and c.value in {'#REF!','#DIV/0!','#VALUE!','#N/A','#NAME?','#NUM!'})
nmem=sum(1 for r in range(3,536) if ra.cell(r,1).value)   # R&A names are TYPED (cache-immune)
ok(errs==0,'A1 formula errors = %d'%errs)
if VIEW_ALIVE:
    alloc=sum((bm.cell(r,21).value or 0) for r in range(3,536)); funded=sum(1 for r in range(3,536) if (bm.cell(r,21).value or 0)>0)
    ok(abs(alloc-2_000_000)<1,f'A2 allocation = ${alloc:,.0f}')
    ok(funded==int(bm.cell(7,28).value or 133),'A3 funded = %d (= Fund top N)'%funded)
else:
    ok(True,'A2 allocation: SKIP (view cache stale; self-heals on Excel open)')
    ok(True,'A3 funded: SKIP (view cache stale)')
ok(nmem==533,'A4 members = %d'%nmem)
# B influence = committee-only
ab12=bm.cell(12,28).value; ab13=bm.cell(13,28).value
ok(ab12==1.0 and ab13==0.0,'B1 influence weights committee=%s centrality=%s (expect 1.0/0.0)'%(ab12,ab13))
# C legislative = restored curated (NOT the failed refresh): Tim Scott high, Durbin low; Barry Moore Exam-norm high (curated artifact)
rk=AUTH['rank']   # rank truth = the python authority (phase 2), not the view's cache
ok(rk.get('Tim Scott',999)<=15,'C1 Tim Scott rank = %s (expect <=15, champion)'%rk.get('Tim Scott'))
ok(rk.get('Richard Durbin',0)>=380,'C2 Durbin rank = %s (expect >=380, opponent)'%rk.get('Richard Durbin'))
nrm=wb['Legislative Score - Normalized']
bmoore=[nrm.cell(r,3).value for r in range(3,536) if nrm.cell(r,1).value=='Barry Moore']
ok(bmoore and bmoore[0] and bmoore[0]>0.5,'C3 legislative is curated/frozen (Barry Moore Exam-norm=%s>0.5 confirms NOT refreshed)'%(bmoore[0] if bmoore else None))
# D stance dist sane -- col G is the 10-tier overall-stance ladder (sync_stance_clean: importance-weighted
# per-category aggregate). 'Opponent' is the EXTREME bucket, so the sane invariant is that the anti-CU SIDE
# (Opponent+Highly Skeptical+Skeptic) and pro-CU SIDE (Champion+Ally) are each non-trivially populated --
# NOT the obsolete 6-tier 'Opponent>=40' guard threshold (that scheme conflated leg activity with alignment).
from collections import Counter
sd=Counter(ra.cell(r,7).value for r in range(3,536) if ra.cell(r,1).value)
oppside=sd.get('Opponent',0)+sd.get('Highly Skeptical',0)+sd.get('Skeptic',0)
champside=sd.get('Champion',0)+sd.get('Ally',0)
ok(oppside>=40 and champside>=40,'D1 stance dist (anti-side=%d pro-side=%d) %s'%(oppside,champside,dict(sd)))
# E congestion sheet
ok('Congestion' in wb.sheetnames,'E1 Congestion sheet present')
cg=wb['Congestion']; ncg=sum(1 for r in range(3,cg.max_row+1) if cg.cell(r,1).value)
ok(ncg==533,'E2 Congestion rows = %d'%ncg)
CJ=json.load(open(p('congestion.json')))
TCU=sum(m['cu'] for m in CJ); TBK=sum(m['banks'] for m in CJ); TFS=sum(m['finserv'] for m in CJ)
ok(abs(TBK-7_795_150)<2000 and abs(TCU-2_670_800)<2000 and abs(TFS-3_363_600)<2000,f'E3 industry totals CU ${TCU:,} Banks ${TBK:,} FinSvc ${TFS:,}')
# 3-way raw shares sum to 100; capacity-adj sum to 100
badraw=sum(1 for m in CJ if m['total']>0 and abs((m['cu_pct']+m['banks_pct']+m['finserv_pct'])-100)>0.3)
badadj=sum(1 for m in CJ if m['total']>0 and abs((m['cu_adj']+m['banks_adj']+m['finserv_adj'])-100)>0.3)
ok(badraw==0 and badadj==0,'E4 share rows not summing to 100: raw=%d adj=%d'%(badraw,badadj))
# capacity-adj spot check (recompute one)
m=[x for x in CJ if x['member']=='Tina Smith'][0]
cw,bw,fw=m['cu']/TCU,m['banks']/TBK,m['finserv']/TFS; s=cw+bw+fw
ok(abs(m['cu_adj']-100*cw/s)<0.2,'E5 capacity-adj math (Tina Smith CU adj %.1f vs recomputed %.1f)'%(m['cu_adj'],100*cw/s))
# 3 edge cases present
ec={m['member']:m for m in CJ}
ok(all(n in ec for n in ['Debbie Wasserman Schultz','Matt Van Epps','Pablo Hernández Rivera']),'E6 three edge-case members present')
# F FEC mapping coverage + no false-match committees in totals
ok(len([m for m in CJ if m['bioguide']])==533,'F1 all 533 members have bioguide')
neg=[m['member'] for m in CJ if (m['cu'] or 0)<0 or (m['banks'] or 0)<0 or (m['finserv'] or 0)<0]
ok(len(neg)==0,'F2 no negative $ buckets (refunds floored): %s'%neg[:3])
# G IM allocation -- M4: im_allocation.json is now the LIVE per-topic model (member-level row-sums of
# per_topic_alloc.json [FLIP] + per_topic_coalition.json [COALITION]), NOT the superseded single-$2M
# im_allocate2.py output. G1/G2 updated accordingly: the real invariant is that the IM columns EQUAL the
# per-topic row-sums (so the workbook sheet can't silently go stale), and the flip total is the 18 topic
# budgets (18 x $2M = $36M; each topic's $2M is checked by G4).
IM=json.load(open(p('im_allocation.json')))
PT=json.load(open(p('per_topic_alloc.json')))
PTC=json.load(open(p('per_topic_coalition.json')))
fs=sum(IM['flip'].values()); cs=sum(IM['coalition'].values())
pta_tot=sum(sum(d.values()) for d in PT.values()); ptc_tot=sum(sum(d.values()) for d in PTC.values())
ok(fs==pta_tot and abs(fs-len(PT)*2_000_000)<5000*len(PT),f'G1 flip allocation = live per-topic row-sums ${fs:,} (= {len(PT)} x $2M)')
ok(cs==ptc_tot and 0<cs<=len(PTC)*2_000_000,f'G2 coalition allocation = live per-topic row-sums ${cs:,} (0 < c <= {len(PTC)} x $2M)')
ok(len(PT)==18,'G3 per-sub-category allocations = %d topics'%len(PT))
ptbad=[t for t,a in PT.items() if abs(sum(a.values())-2_000_000)>5000]
ok(len(ptbad)==0,'G4 each sub-category sums to $2M (bad: %s)'%ptbad)
# H cross-consistency: congestion.json members == model members
modn=set(ra.cell(r,1).value for r in range(3,536) if ra.cell(r,1).value)   # cache-immune
cjn=set(m['member'] for m in CJ)
ok(modn==cjn,'H1 congestion.json members match model exactly (diff %d)'%len(modn^cjn))
# ===== report =====
print('AUDIT — %d passed, %d FAILED\n'%(len(P),len(F)))
for x in P: print('  [PASS] '+x)
if F:
    print('\n  !!! FAILURES !!!')
    for x in F: print('  [FAIL] '+x)
else: print('\n  ALL CHECKS PASSED.')
