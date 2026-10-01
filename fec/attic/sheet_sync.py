"""Live Moneyball-sheet connection (roadmap step 3, D* Lite incremental).
Fingerprints each topic's inputs; on a sync, only topics whose fingerprint CHANGED are flagged for
recompute (reuse the rest = D* Lite's 'recompute only affected nodes'). Writes the live model outputs
to a 'Melange - Live' tab in the workbook via COM."""
import json,sys,os,hashlib,win32com.client as win32
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
B=r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
M=r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx'
CS=json.load(open(B+r'\category_stance.json')); MAT=CS['matrix']; cats=CS['cats']
cong={m['member']:m for m in json.load(open(B+r'\data\engine\congestion.json'))}; members=list(cong)
CO=json.load(open(B+r'\data\money\budget_frontier.json'))['topics']
EL=json.load(open(B+r'\data\money\budget_frontier_electoral.json'))['topics']
def catof(lab):
    for c in cats:
        if c.split(' &')[0][:10].lower() in lab.lower() or lab.split(' &')[0][:10].lower() in c.lower(): return c
    return None
def fp(cat):   # fingerprint = stances on this topic + money leans (the inputs that move this topic's plan)
    s=''.join(str(MAT.get(m,{}).get(cat,'-'))[0] for m in members)+'|'+''.join(str(int((cong[m].get('net_lean') or 0)/5)) for m in members)
    return hashlib.md5(s.encode()).hexdigest()[:10]
snapf=B+r'\data\engine\sheet_sync_snapshot.json'
prev=json.load(open(snapf)) if os.path.exists(snapf) else {}
cur={c:fp(c) for c in cats}
changed=[c for c in cats if cur[c]!=prev.get(c)]
print('topics changed since last sync (incremental recompute set): %d -> %s'%(len(changed),[c.split(' &')[0] for c in changed][:6]))
# assemble live rows from cached frontiers (reuse) + changed flag
rows=[['Topic','Base reach','Knee $','Coalition seeds','Contest seeds','Defend seeds','Electoral reach','Changed?']]
for lab in CO:
    c=catof(lab); co=CO[lab]; el=EL.get(lab,{})
    rows.append([lab,co['base'],co['knee'],len(co['path'])-1-co.get('contest_seeds',0)-co.get('defend_seeds',0),
                 el.get('contest_seeds',0),el.get('defend_seeds',0),el.get('path',[{}])[-1].get('spread',co['base']),
                 'YES' if c in changed else ''])
# priming highlights if present
prime=json.load(open(B+r'\data\network\lt_priming.json')) if os.path.exists(B+r'\data\network\lt_priming.json') else []
def rgb(r,g,b): return b*65536+g*256+r
xl=win32.DispatchEx('Excel.Application'); xl.Visible=False; xl.DisplayAlerts=False
try:
    wb=xl.Workbooks.Open(M)
    for nm in ('Melange - Live',):
        try: wb.Worksheets(nm).Delete()
        except: pass
    ws=wb.Worksheets.Add(After=wb.Worksheets(wb.Worksheets.Count)); ws.Name='Melange - Live'
    ws.Range(ws.Cells(1,1),ws.Cells(len(rows),8)).Value=rows
    h=ws.Range(ws.Cells(1,1),ws.Cells(1,8)); h.Font.Bold=True; h.Interior.Color=rgb(0x25,0x3A,0x5A); h.Font.Color=rgb(255,255,255)
    ws.Columns(1).ColumnWidth=30
    for c in range(2,9): ws.Columns(c).ColumnWidth=13
    # mark changed rows
    for i,r in enumerate(rows[1:],start=2):
        if r[7]=='YES': ws.Range(ws.Cells(i,1),ws.Cells(i,8)).Interior.Color=rgb(0xFF,0xF2,0xCC)
    base=len(rows)+2
    ws.Cells(base,1).Value='CHEAPEST LT-PRIMING FLIPS (current topic: %s)'%(prime[0].get('v','') and os.environ.get('TOPIC','Mortgage') or '')
    ws.Cells(base,1).Font.Bold=True
    pr=[['Member','Tier','Gap','Total $','Money $','Recruit']]
    for p in prime[:12]:
        pr.append([p['v'],p['tier'],p['gap'],p['cost'],p['money'],', '.join(u.split()[-1] for u,a in p['recruits'][:3])])
    ws.Range(ws.Cells(base+1,1),ws.Cells(base+len(pr),6)).Value=pr
    ws.Range(ws.Cells(base+1,1),ws.Cells(base+1,6)).Font.Bold=True
    wb.Save(); print('wrote "Melange - Live" tab (%d topics, %d changed, %d priming rows)'%(len(CO),len(changed),len(prime[:12])))
finally:
    wb.Close(SaveChanges=True); xl.Quit()
json.dump(cur,open(snapf,'w'))
print('snapshot updated -> next sync recomputes only newly-changed topics')
