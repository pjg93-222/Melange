# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT,DRAFT as MB_DRAFT  # centralized root (arch review 2026-07-02)
"""Per-member electoral history for the member desk: FEC primary + general vote share (2016-2022,
member-level, from the FEC 'Federal Elections' books in ~/Downloads) + 2024 general from MEDSL.
Matched with build_electoral's exact name formula, state+chamber scoped. Writes electoral_history.json.
Run: python fec/build_electoral_history.py"""
import json, openpyxl, collections, glob, os, csv, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
B = MB_ROOT
DL = r"C:\Users\pgoff\Downloads"; DS = MB_DRAFT

members = [m['member'] for m in json.load(open(B+r"\congestion.json"))]
mset = set(members); bylast = collections.defaultdict(list)
for n in members: bylast[n.split()[-1].lower()].append(n)
def match(nm):
    if nm in mset: return nm
    t = str(nm).replace(',',' ').replace('.',' ').split()
    if not t: return None
    c = bylast.get(t[-1].lower())
    if not c: return None
    if len(c)==1: return c[0]
    fi = t[0][0].lower()
    for cand in c:
        if cand.split()[0][0].lower()==fi: return cand
    return c[0]
def isnum(x): return isinstance(x,(int,float)) and not isinstance(x,bool)

bp = sorted(glob.glob(B+r"\archive\Ballotpedia_119th_CU_Influence_*.xlsx"), key=os.path.basename)[-1]
ws = openpyxl.load_workbook(bp, data_only=True, read_only=True)['Members']
hd = {ws.cell(1,c).value:c for c in range(1,ws.max_column+1)}
mstate={}; mcham={}
for r in range(2, ws.max_row+1):
    mm = match(ws.cell(r,hd['Member']).value)
    if not mm: continue
    if ws.cell(r,hd['State']).value: mstate[mm]=str(ws.cell(r,hd['State']).value).strip().upper()
    if ws.cell(r,hd['Chamber']).value: mcham[mm]=str(ws.cell(r,hd['Chamber']).value).strip()
EL = json.load(open(B+r"\electoral.json"))

hist = {m:{'chamber':mcham.get(m),'state':mstate.get(m),
           'forecast':{'avg':(EL.get(m,{}) or {}).get('elavg'),'security':(EL.get(m,{}) or {}).get('security')},
           'primary':{}, 'general':{}} for m in members}
SHEETS = {2016:("2016 US House Results by State","2016 US Senate Results by State"),
          2018:("2018 US House Results by State","2018 US Senate Results by State"),
          2020:("13. US House Results by State","12. US Senate Results by State"),
          2022:("8. US House Results by State","7. US Senate Results by State")}
def pct(x): return round(x*100,1) if isnum(x) else None
for yr,(hs,ss) in SHEETS.items():
    wb = openpyxl.load_workbook(DL+r"\federalelections%d.xlsx"%yr, data_only=True, read_only=True)
    for sheet,cham in ((hs,'House'),(ss,'Senate')):
        for row in wb[sheet].iter_rows(min_row=2, values_only=True):
            stab=row[1]; first=row[6]; last=row[7]
            if not stab or not last or len(str(stab))!=2: continue
            m = match(("%s %s"%(str(first or ''),str(last or ''))).strip())
            if not m or mstate.get(m)!=str(stab).strip().upper() or mcham.get(m)!=cham: continue
            pv=row[11]; pp=row[12]; gv=row[15] if len(row)>15 else None; gp=row[16] if len(row)>16 else None
            unopp = (isinstance(pv,str) and 'unoppos' in pv.lower()) or (isinstance(pp,str) and 'unoppos' in pp.lower())
            if yr not in hist[m]['general'] or (isnum(gv) and (hist[m]['general'][yr].get('votes') or 0)<gv):
                hist[m]['general'][yr]={'pct':pct(gp),'votes':gv if isnum(gv) else None,'src':'FEC'}
                hist[m]['primary'][yr]={'pct':pct(pp),'votes':pv if isnum(pv) else None,'unopposed':unopp}
    wb.close()
def add_medsl(path, cham):
    for r in csv.DictReader(open(path,encoding='utf-8-sig',newline='')):
        if r.get('year')!='2024' or str(r.get('stage','')).upper() not in ('GEN','GEN RUNOFF'): continue
        m=match(str(r.get('candidate','')).strip()); st=str(r.get('state_po','')).strip().upper()
        if not m or mstate.get(m)!=st or mcham.get(m)!=cham: continue
        try: cv=float(r.get('candidatevotes')); tv=float(r.get('totalvotes'))
        except (TypeError,ValueError): continue   # S3-02: narrowed from bare except
        cur=hist[m]['general'].get(2024)
        if cur is None or (cur.get('votes') or 0)<cv:
            hist[m]['general'][2024]={'pct':round(100*cv/tv,1) if tv else None,'votes':int(cv),'src':'MEDSL'}
add_medsl(DS+r"\medsl_house.csv",'House'); add_medsl(DS+r"\medsl_senate.csv",'Senate')

out={}
for m,d in hist.items():
    if not d['primary'] and not d['general']: continue
    out[m]={'chamber':d['chamber'],'state':d['state'],'forecast':d['forecast'],
            'primary':[dict(year=y,**d['primary'][y]) for y in sorted(d['primary'])],
            'general':[dict(year=y,**d['general'][y]) for y in sorted(d['general'])]}
json.dump(out, open(B+r"\electoral_history.json","w"), separators=(',',':'))
print("wrote electoral_history.json — %d members with history"%len(out))
