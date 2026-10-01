import csv, sys, re, collections, json
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
BANK={'C00336768','C00104299','C00128512','C00379693','C00034595','C00300178','C00429852','C00004275',
'C00043489','C00364778','C00009639','C00386524','C00008474','C00039305','C00032698','C00035519','C00186064',
'C00018036','C00488882','C00432252','C00648345','C00501429','C00890707','C00438051','C00040535','C00365122',
'C00326595','C00038604','C00410274','C00879890','C00579540','C00589119'}
CU={'C00007880','C00040659','C00390633','C00402107','C00430066','C00326132','C70006317','C00409342','C00360610','C00235929','C00751214'}
grpof={**{c:'BANK' for c in BANK},**{c:'CU' for c in CU}}
fec2mem={}
with open('legislators.csv',encoding='utf-8') as f:
    r=csv.reader(f); h=next(r); fi=h.index('fec_ids');ni=h.index('full_name');ti=h.index('type');bi=h.index('bioguide_id')
    for row in r:
        for cid in re.findall(r'[HSP]\d[A-Z0-9]{2}\d{5}',row[fi]): fec2mem[cid]=(row[ni],row[ti],row[bi])
# total receipts per cand id (weball: CAND_ID f0, TTL_RECEIPTS f5)
receipts={}
with open('weball24.txt',encoding='latin-1') as f:
    for line in f:
        p=line.split('|')
        if len(p)>5:
            try: receipts[p[0]]=float(p[5])
            except: pass
# aggregate by bioguide
mem=collections.defaultdict(lambda:{'name':'','type':'','bank':0.0,'cu':0.0,'rec':0.0})
for line in open('itpas2.txt',encoding='latin-1'):
    p=line.split('|')
    if len(p)<17 or p[0] not in grpof or p[5] not in ('24K','24Z'): continue
    if len(p)>19 and p[19]=='X': continue
    cand=p[16]
    if cand not in fec2mem: continue
    try: amt=float(p[14])
    except: continue
    nm,tp,bio=fec2mem[cand]; m=mem[bio]; m['name']=nm; m['type']=tp
    m['bank' if grpof[p[0]]=='BANK' else 'cu']+=amt
# receipts by bioguide (sum over member's cand ids)
b2cands=collections.defaultdict(list)
for cand,(nm,tp,bio) in fec2mem.items(): b2cands[bio].append(cand)
for bio,m in mem.items():
    m['rec']=sum(receipts.get(c,0) for c in b2cands[bio])
# saturation
out={}
for bio,m in mem.items():
    sat=(m['bank']/m['rec']) if m['rec']>0 else None
    out[bio]={'name':m['name'],'type':m['type'],'bank':round(m['bank']),'cu':round(m['cu']),'receipts':round(m['rec']),'saturation':sat}
json.dump(out,open('data/engine/congestion.json','w'))
rows=[(b,d) for b,d in out.items() if d['bank']>0]
valid=[(b,d) for b,d in rows if d['receipts'] and d['receipts']>=100000]  # reliable denom
print(f"members w/ bank$: {len(rows)} | with receipts>=100k (reliable saturation): {len(valid)}")
print('\nTOP 15 by SATURATION (bank$ / total receipts), receipts>=$100k:')
print(f"  {'member':24s}{'type':>5}{'bank$':>9}{'receipts':>11}{'sat%':>7}")
for b,d in sorted(valid,key=lambda x:-x[1]['saturation'])[:15]:
    print(f"  {d['name']:24s}{d['type']:>5}{d['bank']:>9,}{d['receipts']:>11,}{100*d['saturation']:>6.1f}%")
print('\nLOW-receipt members w/ high bank$ (saturation UNRELIABLE - flag):')
for b,d in sorted([(b,d) for b,d in rows if not d['receipts'] or d['receipts']<100000],key=lambda x:-x[1]['bank'])[:5]:
    print(f"  {d['name']:24s} bank {d['bank']:>8,}  receipts {d['receipts']:>9,}")
print('\nwrote congestion.json (bioguide-keyed)')
