import csv,sys,re,collections,json,openpyxl
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
BANK={'C00336768','C00104299','C00128512','C00379693','C00034595','C00300178','C00429852','C00004275',
'C00043489','C00364778','C00009639','C00386524','C00008474','C00039305','C00032698','C00035519','C00186064',
'C00018036','C00488882','C00432252','C00648345','C00501429','C00890707','C00438051','C00040535','C00365122',
'C00326595','C00038604','C00410274','C00879890','C00579540','C00589119','C00370015'}
ST={'ALABAMA':'AL','ALASKA':'AK','ARIZONA':'AZ','ARKANSAS':'AR','CALIFORNIA':'CA','COLORADO':'CO','CONNECTICUT':'CT','DELAWARE':'DE','FLORIDA':'FL','GEORGIA':'GA','HAWAII':'HI','IDAHO':'ID','ILLINOIS':'IL','INDIANA':'IN','IOWA':'IA','KANSAS':'KS','KENTUCKY':'KY','LOUISIANA':'LA','MAINE':'ME','MARYLAND':'MD','MASSACHUSETTS':'MA','MICHIGAN':'MI','MINNESOTA':'MN','MISSISSIPPI':'MS','MISSOURI':'MO','MONTANA':'MT','NEBRASKA':'NE','NEVADA':'NV','NEW HAMPSHIRE':'NH','NEW JERSEY':'NJ','NEW MEXICO':'NM','NEW YORK':'NY','NORTH CAROLINA':'NC','NORTH DAKOTA':'ND','OHIO':'OH','OKLAHOMA':'OK','OREGON':'OR','PENNSYLVANIA':'PA','RHODE ISLAND':'RI','SOUTH CAROLINA':'SC','SOUTH DAKOTA':'SD','TENNESSEE':'TN','TEXAS':'TX','UTAH':'UT','VERMONT':'VT','VIRGINIA':'VA','WASHINGTON':'WA','WEST VIRGINIA':'WV','WISCONSIN':'WI','WYOMING':'WY'}
bm=openpyxl.load_workbook(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx',data_only=True)['Blended Model']
# model roster: name + state2
idx=collections.defaultdict(list)  # lastupper -> [(name, firstupper, state2)]
roster=[]
for r in range(3,536):
    nm=bm.cell(r,1).value; ds=str(bm.cell(r,2).value or '')
    if not nm: continue
    m=re.search(r'\b([A-Z]{2})\b',ds.upper()); st=m.group(1) if m else ST.get(ds.upper().strip(),'')
    parts=nm.split(); last=parts[-1].upper(); first=parts[0].upper()
    idx[last].append((nm,first,st)); roster.append(nm)
print(f'model roster: {len(roster)} | David Scott in model: {"David Scott" in roster}')
cn={}
for line in open('cn.txt',encoding='latin-1'):
    p=line.split('|')
    if len(p)>13: cn[p[0]]=(p[1],p[13])
def match(cand):
    if cand not in cn: return None
    nm,st=cn[cand]; last=nm.split(',')[0].strip().upper()
    first=nm.split(',')[1].strip().split()[0].upper() if ',' in nm and nm.split(',')[1].strip() else ''
    cs=[x for x in idx.get(last,[]) if x[2]==st]
    if len(cs)==1: return cs[0][0]
    if len(cs)>1:
        for n,f,s in cs:
            if f[:1]==first[:1]: return n
    al=idx.get(last,[])
    if len(al)==1: return al[0][0]
    return None
bankm=collections.defaultdict(float); nonmodel=collections.defaultdict(float)
for line in open('itpas2.txt',encoding='latin-1'):
    p=line.split('|')
    if len(p)<17 or p[0] not in BANK or p[5] not in ('24K','24Z'): continue
    if len(p)>19 and p[19]=='X': continue
    cand=p[16]
    try: amt=float(p[14])
    except: continue
    mm=match(cand)
    if mm: bankm[mm]+=amt
    elif cand: nonmodel[cand]+=amt
print(f'bank$ -> MODEL members: ${sum(bankm.values()):,.0f} | members receiving: {len(bankm)}')
print(f'bank$ -> non-model (lost/retired/challengers): ${sum(nonmodel.values()):,.0f} / {len(nonmodel)}')
print('David Scott bank$:', f"${bankm.get('David Scott',0):,.0f}")
print('\ntop remaining non-model (verify none are sitting model members):')
for c,a in sorted(nonmodel.items(),key=lambda x:-x[1])[:8]:
    print(f"   {cn.get(c,('?',''))[0]:30s} ${a:>8,.0f}")
json.dump({n:round(v) for n,v in bankm.items()}, open('bank_by_model.json','w'))
print('\nwrote bank_by_model.json')
