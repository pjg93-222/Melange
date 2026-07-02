import csv,sys,re,collections,json,unicodedata,openpyxl
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def norm(s): return ''.join(c for c in unicodedata.normalize('NFKD',str(s)) if not unicodedata.combining(c)).lower().strip()
BANK={'C00336768','C00104299','C00128512','C00379693','C00034595','C00300178','C00429852','C00004275','C00043489','C00364778','C00009639','C00386524','C00008474','C00039305','C00032698','C00035519','C00186064','C00018036','C00488882','C00432252','C00648345','C00501429','C00890707','C00438051','C00040535','C00365122','C00326595','C00038604','C00410274','C00879890','C00579540','C00589119','C00370015'}
# legislators
rows=list(csv.reader(open('legislators.csv',encoding='utf-8'))); H=rows[0]
li,fri,bi,sti,nk,fl,ty=H.index('last_name'),H.index('first_name'),H.index('bioguide_id'),H.index('state'),H.index('nickname'),H.index('full_name'),H.index('type')
fec2bio={}; bio2cands=collections.defaultdict(list); bylast=collections.defaultdict(list); bio2type={}
for r in rows[1:]:
    bio2type[r[bi]]=r[ty]
    for c in re.findall(r'[HSP]\d[A-Z0-9]{2}\d{5}',r[H.index('fec_ids')]): fec2bio[c]=r[bi]; bio2cands[r[bi]].append(c)
    bylast[norm(r[li])].append((r[bi],norm(r[fri]),norm(r[nk])))
receipts={}
for line in open('weball24.txt',encoding='latin-1'):
    p=line.split('|')
    if len(p)>5:
        try: receipts[p[0]]=float(p[5])
        except: pass
bankbio=collections.defaultdict(float)
for line in open('itpas2.txt',encoding='latin-1'):
    p=line.split('|')
    if len(p)<17 or p[0] not in BANK or p[5] not in ('24K','24Z') or (len(p)>19 and p[19]=='X'): continue
    if p[16] in fec2bio:
        try: bankbio[fec2bio[p[16]]]+=float(p[14])
        except: pass
recbio={b:sum(receipts.get(c,0) for c in cs) for b,cs in bio2cands.items()}
# model roster
wb=openpyxl.load_workbook(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx',data_only=True)
bm=wb['Blended Model']; cen=wb['Centrality']
name2bio={cen.cell(r,2).value:cen.cell(r,1).value for r in range(2,cen.max_row+1) if cen.cell(r,2).value}
def resolve(nm):
    if nm in name2bio: return name2bio[nm]
    nn=norm(nm); toks=nn.split()
    for k in (3,2,1):  # compound last name: last k tokens
        if len(toks)>k:
            last=' '.join(toks[-k:]); first=toks[0]
            cands=bylast.get(last,[])
            if len(cands)==1: return cands[0][0]
            for b,f,nck in cands:
                if f[:3]==first[:3] or nck[:3]==first[:3]: return b
    return None
recs=[]; unres=[]
for r in range(3,536):
    nm=bm.cell(r,1).value
    if not nm: continue
    b=resolve(nm)
    if not b: unres.append(nm); continue
    bk=bankbio.get(b,0); rc=recbio.get(b,0); ch='House' if bio2type.get(b)=='rep' else 'Senate'
    recs.append({'member':nm,'bioguide':b,'chamber':ch,'bank':round(bk),'receipts':round(rc),'saturation':(bk/rc if rc>=100000 else None)})
# within-chamber percentile of saturation
for ch in ('House','Senate'):
    grp=[x for x in recs if x['chamber']==ch and x['saturation'] is not None]
    vals=sorted(x['saturation'] for x in grp)
    for x in grp:
        x['cong_pctile']=round(100*sum(1 for v in vals if v<x['saturation'])/(len(vals)-1),1) if len(vals)>1 else 0
for x in recs:
    x.setdefault('cong_pctile',None)
print(f'resolved {len(recs)}/533 | unresolved: {unres}')
# pinned edge cases
for n in ['Debbie Wasserman Schultz','Matt Van Epps','Pablo Hernández Rivera']:
    m=[x for x in recs if x['member']==n]
    print(f"  PINNED {n}: {m[0] if m else 'STILL UNRESOLVED'}")
print(f"\nchamber counts: House {sum(1 for x in recs if x['chamber']=='House')}, Senate {sum(1 for x in recs if x['chamber']=='Senate')}")
recs.sort(key=lambda x:-(x['cong_pctile'] or -1))
print('\nTOP 12 congestion percentile (within chamber):')
for x in recs[:12]: print(f"   {x['member']:22s} {x['chamber']:6s} bank ${x['bank']:>7,} sat {100*(x['saturation'] or 0):4.1f}% pctile {x['cong_pctile']}")
# write CSV
with open('congestion_table.csv','w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['member','bioguide','chamber','bank','receipts','saturation','cong_pctile']); w.writeheader()
    for x in sorted(recs,key=lambda x:x['member']): w.writerow(x)
json.dump(recs,open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\congestion.json','w'))
print('\nwrote congestion_table.csv + congestion.json (533 members)')
