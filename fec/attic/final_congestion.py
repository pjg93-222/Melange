import csv,sys,re,collections,json,openpyxl
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
BANK={'C00336768','C00104299','C00128512','C00379693','C00034595','C00300178','C00429852','C00004275',
'C00043489','C00364778','C00009639','C00386524','C00008474','C00039305','C00032698','C00035519','C00186064',
'C00018036','C00488882','C00432252','C00648345','C00501429','C00890707','C00438051','C00040535','C00365122',
'C00326595','C00038604','C00410274','C00879890','C00579540','C00589119','C00370015'}
# fec_id -> bio ; bio -> [cands] ; legislator bios
fec2bio={}; bio2cands=collections.defaultdict(list); legbio=set()
with open('legislators.csv',encoding='utf-8') as f:
    r=csv.reader(f); h=next(r); fi=h.index('fec_ids');bi=h.index('bioguide_id')
    for row in r:
        legbio.add(row[bi])
        for c in re.findall(r'[HSP]\d[A-Z0-9]{2}\d{5}',row[fi]): fec2bio[c]=row[bi]; bio2cands[row[bi]].append(c)
receipts={}
for line in open('weball24.txt',encoding='latin-1'):
    p=line.split('|')
    if len(p)>5:
        try: receipts[p[0]]=float(p[5])
        except: pass
bankbio=collections.defaultdict(float); nonmember=collections.defaultdict(float)
cn={l.split('|')[0]:l.split('|')[1] for l in open('cn.txt',encoding='latin-1') if l.count('|')>1}
for line in open('itpas2.txt',encoding='latin-1'):
    p=line.split('|')
    if len(p)<17 or p[0] not in BANK or p[5] not in ('24K','24Z'): continue
    if len(p)>19 and p[19]=='X': continue
    cand=p[16]
    try: amt=float(p[14])
    except: continue
    if cand in fec2bio: bankbio[fec2bio[cand]]+=amt
    elif cand: nonmember[cand]+=amt
recbio={b:sum(receipts.get(c,0) for c in cs) for b,cs in bio2cands.items()}
# model roster -> bioguide via Centrality
wb=openpyxl.load_workbook(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx',data_only=True)
cen=wb['Centrality']; name2bio={cen.cell(r,2).value:cen.cell(r,1).value for r in range(2,cen.max_row+1) if cen.cell(r,2).value}
model=[wb['Blended Model'].cell(r,1).value for r in range(3,536) if wb['Blended Model'].cell(r,1).value]
mbio={n:name2bio.get(n) for n in model}
nobio=[n for n in model if not mbio[n]]
notinleg=[n for n in model if mbio[n] and mbio[n] not in legbio]
print(f'model members: {len(model)} | no bioguide match: {len(nobio)} | bio not in legislators(true gap): {len(notinleg)} {notinleg[:6]}')
covered=[n for n in model if mbio[n] in bankbio]
print(f'model members receiving bank PAC $: {len(covered)} / {len(model)}')
print(f'\nunmapped non-member $: ${sum(nonmember.values()):,.0f} -- spot check top are NOT model members:')
for c,a in sorted(nonmember.items(),key=lambda x:-x[1])[:6]:
    nm=cn.get(c,'?'); inmodel=any(mbio[n]==fec2bio.get(c) for n in model)
    print(f"   {nm:28s} ${a:>8,.0f}  in-model={inmodel}")
# saturation per model member
out={}
for n in model:
    b=mbio[n]; bk=bankbio.get(b,0); rc=recbio.get(b,0)
    out[n]={'bioguide':b,'bank':round(bk),'receipts':round(rc),'sat':(bk/rc if rc>=100000 else None)}
json.dump(out,open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\congestion_final.json','w'))
valid=[(n,d) for n,d in out.items() if d['sat'] is not None]
print('\nTOP 12 model members by bank saturation:')
for n,d in sorted(valid,key=lambda x:-x[1]['sat'])[:12]:
    print(f"   {n:24s} bank ${d['bank']:>8,} / rec ${d['receipts']:>9,} = {100*d['sat']:>5.1f}%")
print('\nSANITY (HFSC leaders):', {n:f"${out[n]['bank']:,}" for n in ['Andy Barr','French Hill','Young Kim','Roger Williams','Bill Huizenga'] if n in out})
