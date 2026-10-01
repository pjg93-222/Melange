import csv,sys,re,collections,json,openpyxl
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
BANK={'C00336768','C00104299','C00128512','C00379693','C00034595','C00300178','C00429852','C00004275','C00043489','C00364778','C00009639','C00386524','C00008474','C00039305','C00032698','C00035519','C00186064','C00018036','C00488882','C00432252','C00648345','C00501429','C00890707','C00438051','C00040535','C00365122','C00326595','C00038604','C00410274','C00879890','C00579540','C00589119','C00370015'}
ST={'ALABAMA':'AL','ALASKA':'AK','ARIZONA':'AZ','ARKANSAS':'AR','CALIFORNIA':'CA','COLORADO':'CO','CONNECTICUT':'CT','DELAWARE':'DE','FLORIDA':'FL','GEORGIA':'GA','HAWAII':'HI','IDAHO':'ID','ILLINOIS':'IL','INDIANA':'IN','IOWA':'IA','KANSAS':'KS','KENTUCKY':'KY','LOUISIANA':'LA','MAINE':'ME','MARYLAND':'MD','MASSACHUSETTS':'MA','MICHIGAN':'MI','MINNESOTA':'MN','MISSISSIPPI':'MS','MISSOURI':'MO','MONTANA':'MT','NEBRASKA':'NE','NEVADA':'NV','NEW HAMPSHIRE':'NH','NEW JERSEY':'NJ','NEW MEXICO':'NM','NEW YORK':'NY','NORTH CAROLINA':'NC','NORTH DAKOTA':'ND','OHIO':'OH','OKLAHOMA':'OK','OREGON':'OR','PENNSYLVANIA':'PA','RHODE ISLAND':'RI','SOUTH CAROLINA':'SC','SOUTH DAKOTA':'SD','TENNESSEE':'TN','TEXAS':'TX','UTAH':'UT','VERMONT':'VT','VIRGINIA':'VA','WASHINGTON':'WA','WEST VIRGINIA':'WV','WISCONSIN':'WI','WYOMING':'WY'}
fec2bio={}; bio2cands=collections.defaultdict(list)
h=open('legislators.csv',encoding='utf-8').readline().strip().split(',')
li,fir,bi,sti,nick,full=h.index('last_name'),h.index('first_name'),h.index('bioguide_id'),h.index('state'),h.index('nickname'),h.index('full_name')
L=collections.defaultdict(list)
with open('legislators.csv',encoding='utf-8') as f:
    r=csv.reader(f); next(r)
    for row in r:
        for c in re.findall(r'[HSP]\d[A-Z0-9]{2}\d{5}',row[h.index('fec_ids')]): fec2bio[c]=row[bi]; bio2cands[row[bi]].append(c)
        L[(row[li].upper(),row[sti])].append((row[bi],row[fir].upper(),row[nick].upper()))
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
wb=openpyxl.load_workbook(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx',data_only=True)
bm=wb['Blended Model']; cen=wb['Centrality']
name2bio={cen.cell(r,2).value:cen.cell(r,1).value for r in range(2,cen.max_row+1) if cen.cell(r,2).value}
def st2(ds):
    t=ds.split(',')[-1].strip().upper()
    return ST.get(t) or (re.search(r'\b([A-Z]{2})\b',ds.upper()).group(1) if re.search(r'\b([A-Z]{2})\b',ds.upper()) else '')
out={}; unres=[]
for r in range(3,536):
    nm=bm.cell(r,1).value
    if not nm: continue
    ds=str(bm.cell(r,2).value or ''); bio=name2bio.get(nm)
    if not bio:
        last=nm.split()[-1].upper(); fr=nm.split()[0].upper(); st=st2(ds); cands=L.get((last,st),[])
        if len(cands)==1: bio=cands[0][0]
        else:
            for b,f,nk in cands:
                if f[:3]==fr[:3] or nk[:3]==fr[:3]: bio=b; break
    if not bio: unres.append(nm); continue
    bk=bankbio.get(bio,0); rc=recbio.get(bio,0)
    out[nm]={'bioguide':bio,'bank':round(bk),'receipts':round(rc),'saturation':(bk/rc if rc>=100000 else None)}
json.dump(out,open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\data\engine\congestion.json','w'))
print(f'model members resolved: {len(out)}/533 | unresolved: {len(unres)} {unres}')
print(f'receiving bank PAC $: {sum(1 for d in out.values() if d["bank"]>0)} | $0: {sum(1 for d in out.values() if d["bank"]==0)}')
valid=[(n,d) for n,d in out.items() if d['saturation'] is not None]
print('\nTOP 12 by SATURATION:')
for n,d in sorted(valid,key=lambda x:-x[1]['saturation'])[:12]:
    print(f"   {n:24s} ${d['bank']:>7,}/{d['receipts']:>10,} = {100*d['saturation']:.1f}%")
print('\nSANITY now-resolved formerly-unmatched:', {n:f"${out[n]['bank']:,}" for n in ['Jim Jordan','Jason Smith','James Clyburn','David Schweikert','Doris Matsui'] if n in out})
