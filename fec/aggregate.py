import csv, sys, re, collections
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
# curated, verified committee -> group (false matches excluded)
BANK={'C00336768','C00104299','C00128512','C00379693','C00034595','C00300178','C00429852','C00004275',
'C00043489','C00364778','C00009639','C00386524','C00008474','C00039305','C00032698','C00035519','C00186064',
'C00018036','C00488882','C00432252','C00648345','C00501429','C00890707','C00438051','C00040535','C00365122',
'C00326595','C00038604','C00410274','C00879890','C00579540','C00589119'}
CU={'C00007880','C00040659','C00390633','C00402107','C00430066','C00326132','C70006317','C00409342',
'C00360610','C00235929','C00751214'}
grpof={**{c:'BANK' for c in BANK},**{c:'CU' for c in CU}}

# fec cand id -> member name/type/bioguide
fec2mem={}
with open('legislators.csv', encoding='utf-8') as f:
    r=csv.reader(f); hdr=next(r)
    fi=hdr.index('fec_ids'); ni=hdr.index('full_name'); ti=hdr.index('type'); bi=hdr.index('bioguide_id')
    for row in r:
        for cid in re.findall(r'[HSP]\d[A-Z0-9]{2}\d{5}', row[fi]):
            fec2mem[cid]=(row[ni],row[ti],row[bi])
print(f'fec cand ids mapped: {len(fec2mem)} | committees: BANK {len(BANK)}, CU {len(CU)}')

agg=collections.defaultdict(lambda: collections.defaultdict(float))  # group -> cand -> $
with open('itpas2.txt', encoding='latin-1') as f:
    for line in f:
        p=line.split('|')
        if len(p)<17: continue
        cmte=p[0]
        if cmte not in grpof: continue
        if p[5] not in ('24K','24Z'): continue   # direct contributions to candidate (not IEs)
        if len(p)>19 and p[19]=='X': continue     # skip memo double-counts
        cand=p[16]
        try: amt=float(p[14])
        except: continue
        agg[grpof[cmte]][cand]+=amt

# per-member
mem=collections.defaultdict(lambda:{'BANK':0.0,'CU':0.0})
unmapped={'BANK':0.0,'CU':0.0}
for grp in ('BANK','CU'):
    for cand,amt in agg[grp].items():
        if cand in fec2mem: mem[fec2mem[cand][0]][grp]+=amt
        else: unmapped[grp]+=amt
print(f"total BANK PAC->cands ${sum(agg['BANK'].values()):,.0f} | CU ${sum(agg['CU'].values()):,.0f}")
print(f"  (to NON-current-members/lost candidates: BANK ${unmapped['BANK']:,.0f}, CU ${unmapped['CU']:,.0f})")
rows=[(n,v['BANK'],v['CU']) for n,v in mem.items()]
rows.sort(key=lambda x:-x[1])
print(f"\ncurrent members receiving bank PAC $: {sum(1 for _,b,_ in rows if b>0)}")
print('\nTOP 18 most BANK-congested members (2024 cycle, PAC contributions):')
print(f"  {'member':26s} {'BANK$':>10} {'CU$':>9} {'bank/(bank+cu)':>14}")
for n,b,c in rows[:18]:
    ratio=b/(b+c) if (b+c)>0 else 0
    print(f"  {n:26s} {b:>10,.0f} {c:>9,.0f} {ratio:>13.2f}")
print('\nTop 8 CU-funded members:')
for n,b,c in sorted(rows,key=lambda x:-x[2])[:8]:
    print(f"  {n:26s} bank {b:>9,.0f}  cu {c:>8,.0f}")
import json; json.dump({n:{'bank':v['BANK'],'cu':v['CU']} for n,v in mem.items()}, open('congestion_raw.json','w'))
print('\nwrote congestion_raw.json')
