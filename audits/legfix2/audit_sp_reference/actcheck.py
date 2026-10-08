# -*- coding: utf-8 -*-
import sys,os,json,math,unicodedata,collections
FEC=r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\legislative-data-audit-1ad63e\fec'
sys.path.insert(0,FEC)
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
import openpyxl
B=r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
from moneyball_core import IMP
LEGPRE = {'Examination & Supervision':'examination & supervision','CU Capital Requirements':'credit union capital requirements','NCUA Budget & Insurance':'ncua budget','Interchange':'interchange','Payments':'payments','Technology & Emerging':'technology','Fraud Prevention':'fraud prevention','Data Privacy & Cyber':'data privacy','Charter Modernization':'charter modernization','Defense CU Issues':'defense credit union','Field of Membership':'field of membership','CDFI Fund':'cdfi fund','CFPB':'cfpb','Credit Card Mandates':'credit card & consumer-fee','TCPA':'telephone consumer','Member Business Lending':'member business lending','Mortgage & Housing':'mortgage lending','CU Tax Status':'credit union tax status'}
def norm(s): return str(s).lower().replace(' and ',' & ').strip()
def nfc(s): return unicodedata.normalize('NFC',str(s)) if s is not None else s
wb=openpyxl.load_workbook(B+r'\Moneyball Main Version - Blended.xlsx',data_only=True)
ls=wb['Legislative Score - Raw']; lh=[ls.cell(1,c).value for c in range(1,ls.max_column+1)]
topcols={t:[] for t in IMP}
for ci,h in enumerate(lh):
    if not h: continue
    hn=norm(h)
    if 'average' in hn or 'success' in hn or 'sponsor' not in hn: continue
    for t,pre in LEGPRE.items():
        if hn.startswith(norm(pre)): topcols[t].append(ci); break
ACT={}
for row in ls.iter_rows(min_row=2,values_only=True):
    nm=row[0]
    if not nm: continue
    ACT[nfc(nm)]={t:sum((row[ci] or 0) for ci in topcols[t] if isinstance(row[ci],(int,float))) for t in IMP}
cg=json.load(open(B+r'\congestion.json',encoding='utf-8'))
roster=[m['member'] for m in cg]
VC=json.load(open(B+r'\vote_category_lean.json',encoding='utf-8'))
LEG=json.load(open(B+r'\archive_leg.json',encoding='utf-8'))
n2b={v:k for k,v in VC['name_of'].items()}; votes=VC['votes']
vo=0; vo_act0=0; vo_actpos=0; ex=[]
vo5=0; vo5_act0=0; vo5_actpos=0
for m in roster:
    a=ACT.get(nfc(m),{})
    for c,d in votes.get(n2b.get(m,''),{}).items():
        n=d.get('n',0) or 0
        if n<1: continue
        if abs(LEG.get(m,{}).get(c,0.0))>1e-9: continue
        vo+=1
        act=a.get(c,0)
        if act: vo_actpos+=1; ex.append((m,c,n,act))
        else: vo_act0+=1
        if n>=5:
            vo5+=1
            if act: vo5_actpos+=1
            else: vo5_act0+=1
print('vote-only cells (n>=1, no archive_leg): %d | workbook activity==0: %d | activity>0: %d'%(vo,vo_act0,vo_actpos))
print('vote-only cells n>=5 (channel fires): %d | activity==0: %d | activity>0: %d'%(vo5,vo5_act0,vo5_actpos))
print('examples of vote-only-but-workbook-activity>0:',ex[:8])
# how many members have ANY category with activity>0 (i.e. leg raw nonzero base)
print('members with zero total workbook activity:',sum(1 for m in roster if sum(ACT.get(nfc(m),{}).values())==0))
