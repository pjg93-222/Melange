import csv,sys,re,collections,json,openpyxl
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
wb=openpyxl.load_workbook(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx',data_only=True)
bm=wb['Blended Model']; cen=wb['Centrality']
name2bio={cen.cell(r,2).value:cen.cell(r,1).value for r in range(2,cen.max_row+1) if cen.cell(r,2).value}
model=[(bm.cell(r,1).value,str(bm.cell(r,2).value or '')) for r in range(3,536) if bm.cell(r,1).value]
print('model col B samples:', [model[i][1] for i in (0,1,200,400)])
# legislators indices
h=open('legislators.csv',encoding='utf-8').readline().strip().split(',')
print('leg cols 3-8:', h[3:8])
L=collections.defaultdict(list)  # (LAST,STATE)->[(bio,FIRST,NICK,FULL)]
Lname={}
with open('legislators.csv',encoding='utf-8') as f:
    r=csv.reader(f); next(r)
    li,fir,bi,sti=h.index('last_name'),h.index('first_name'),h.index('bioguide_id'),h.index('state')
    nick = h.index('nickname') if 'nickname' in h else None
    for row in r:
        L[(row[li].upper(),row[sti])].append((row[bi],row[fir].upper(),(row[nick].upper() if nick else ''),row[h.index('full_name')]))
        Lname[row[bi]]=row[h.index('full_name')]
def st2(ds):
    m=re.search(r'\b([A-Z]{2})\b',ds.upper()); return m.group(1) if m else ''
# resolve model name -> bio: Centrality first, else legislators last+state(+first/nick)
unres=[]; mbio={}
for nm,ds in model:
    if nm in name2bio: mbio[nm]=name2bio[nm]; continue
    last=nm.split()[-1].upper(); first=nm.split()[0].upper(); st=st2(ds)
    cands=L.get((last,st),[])
    pick=None
    if len(cands)==1: pick=cands[0][0]
    else:
        for b,f,nk,full in cands:
            if f[:3]==first[:3] or nk[:3]==first[:3] or first[:3]==f[:3]: pick=b; break
    if pick: mbio[nm]=pick
    else: unres.append((nm,ds,st,len(cands)))
print(f'\nmodel members resolved to bioguide: {len(mbio)}/{len(model)} | still unresolved: {len(unres)}')
for nm,ds,st,nc in unres[:15]: print(f'   UNRESOLVED: {nm:26s} [{ds}] st={st} legcands={nc}')
json.dump(mbio, open('model_bio.json','w'))
