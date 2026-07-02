# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
"""MEDIA BLEND (user-directed 2026-07-02): the press pillar becomes MEDIA = 50% press releases +
50% social media, at the pillar's existing weight.  Insertion point = 'Press Release - Raw' (Table10):
its LET-normalized sheet and the Rank & Allocation SUMPRODUCT consume whatever sits there, so writing
media_raw = 0.5*press_component + 0.5*social_component updates the ENTIRE workbook chain (normalized
sheet -> pillar -> Blended Model rank) with zero formula edits.  Components are each scaled by their
own per-category p80 before mixing, so 50/50 means 50/50 regardless of raw units; the workbook's
pos/neg-max normalization then reapplies downstream exactly as before.

SOCIAL DECAY (user spec: "similar to press, more aggressive in frequency, not decline"): the press
recency curve fits a continuous exponential with HALF-LIFE ~2 YEARS (measured: w(1yr)=0.70,
w(2yr)=0.50, w(3yr)=0.35).  Social uses the SAME exponential shape on a 4x faster clock ->
HALF-LIFE 0.5 YEARS (env SOCIAL_HL_YEARS to re-dial).

Safety: timestamped backup copy of the workbook is written FIRST; only raw VALUE cells are touched
(all formulas preserved); revert = restore the backup."""
import sys,os,json,re,csv,math,shutil,datetime,collections
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
import pandas as pd, openpyxl
M=MB_ROOT
WBP=M+r'\Moneyball Main Version - Blended.xlsx'
HL=float(os.environ.get('SOCIAL_HL_YEARS','0.5')); PRESS_W=0.5; SOCIAL_W=0.5
# DEEP-AUDIT DIALS — USER-RATIFIED 2026-07-02 (both now ON by default; env-overridable):
#  SOCIAL_SHRINK=1 (default) -> in categories where <15 members carry social signal, the social share
#                      scales by nz/15 and press absorbs the remainder. Kills the
#                      one-tweet-=-eight-press-releases artifact in the 6 thin categories (finding A2).
#  RT_W (default 0.5) -> retweets count at half the stance weight of an original post (finding B2:
#                      an RT is amplification, not authorship; hostile-quote-RT damage halved).
SHRINK=os.environ.get('SOCIAL_SHRINK','1')=='1'; RT_W=float(os.environ.get('RT_W','0.5'))
TODAY=datetime.date(2026,7,2)
# category keyword map -> the raw sheet's own headers (built from quorum_query.txt vocabulary groups)
CATKW={
 'Examination & Supervision':r'\bncua\b|examination|supervis|regulatory burden|call report',
 'Credit Union Capital Requirements':r'capital requirement|risk.?based capital|net worth ratio',
 'NCUA Budget & Share Insurance Fund':r'share insurance|ncusif|ncua budget|central liquidity',
 'Interchange':r'interchange|swipe fee|routing mandate|durbin',
 'Payments':r'fednow|real.?time payments|faster payments|payments system|stablecoin|digital dollar|\bcbdc\b|earned wage',
 'Technology & Emerging Issues':r'fintech|artificial intelligence|\bai\b|crypto|digital asset|innovation',
 'Fraud Prevention':r'fraud|scam|elder financial|regulation e\b|zelle|p2p payment',
 'Data Privacy & Cybersecurity':r'data breach|data privacy|data security|cyber|gramm.?leach',
 'Charter Modernization & Governance':r'charter|de novo|governance',
 'Defense Credit Union Issues':r'military lending|defense credit union|military banking|military installation|servicemember',
 'Field of Membership':r'field of membership|common bond|underserved area',
 'CDFI Fund':r'\bcdfi\b|community development financial',
 'CFPB Issues & Structural Reform':r'\bcfpb\b|consumer financial protection|section 1071|section 1033|small business lending rule|open banking|junk fee|late fee|overdraft',
 'Credit Card & Consumer-Fee Mandates':r'credit card competition|\bccca\b|credit card fee|credit card mandate|card late fee',
 'Telephone Consumer Protection Act':r'\btcpa\b|telephone consumer protection|robocall',
 'Member Business Lending':r'member business lending|mbl cap|small.?dollar loan|business loan',
 'Mortgage Lending & Housing':r'mortgage|housing|trigger lead|\bhmda\b|federal home loan bank|gse',
 'Credit Union Tax Status':r'tax.?exempt|tax exemption|tax status|credit union tax|don.?t tax my credit union',
 'CU-Bank Competitive Dynamics':r'big bank|megabank|wall street bank|community bank|bank consolidation|industrial loan|de novo charter|bank lobby',
 'General Credit Union':r'credit union',   # fallback only: assigned when NO specific category hits (see below)
}
CATRX={k:re.compile(v,re.I) for k,v in CATKW.items()}
# keyword-cats == the RAW sheet's own header names (all 20 category columns E..X)
HDRMAP={k:k for k in CATKW}
SIGN={'support':1.0,'oppose':-1.0,'neutral':0.0}
def p80(vals):
    a=sorted(abs(x) for x in vals if abs(x)>1e-9); return a[int(0.8*len(a))] if a else 1.0
# ---- social aggregates: sign * intensity(margin) * decay(0.5^(age/HL)), multi-cat split evenly ----
corp=pd.read_excel(M+r'\Social Master.xlsx',sheet_name='Corpus',dtype=str)
corp=corp[(corp['stance'].fillna('')!='')&(corp['verified_handle'].astype(str)=='1')]
soc=collections.defaultdict(lambda:collections.defaultdict(float)); nassigned=0
for _,r in corp.iterrows():
    sg=SIGN.get(r['stance'],0.0)
    if sg==0.0: continue
    try: age=(TODAY-datetime.date.fromisoformat(str(r['date'])[:10])).days/365.25
    except Exception: continue
    try: inten=max(0.25,min(1.5,float(r['stance_margin'])))
    except (TypeError,ValueError): inten=0.5
    if str(r.get('is_rt','')).strip().lower() in ('1','true','yes'): inten*=RT_W
    decay=0.5**(max(0.0,age)/HL)
    hits=[c for c,rx in CATRX.items() if c!='General Credit Union' and rx.search(r['text'] or '')]
    if not hits and CATRX['General Credit Union'].search(r['text'] or ''): hits=['General Credit Union']
    if not hits: continue
    nassigned+=1
    for c in hits: soc[r['member']][c]+=sg*inten*decay/len(hits)
print('social: %d scored posts -> %d category-assigned | %d members | half-life %.2f yr (press: 2.0 yr)'%(len(corp),nassigned,len(soc),HL))
# ---- workbook surgery ----
bak=M+r'\Moneyball Main Version - Blended.BACKUP-%s.xlsx'%datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
shutil.copy2(WBP,bak); print('backup:',os.path.basename(bak))
wb=openpyxl.load_workbook(WBP)             # formulas preserved
rw=wb['Press Release - Raw']
hdr={rw.cell(1,c).value:c for c in range(1,30) if rw.cell(1,c).value}
members=[rw.cell(r,1).value for r in range(2,536) if rw.cell(r,1).value]
mrow={rw.cell(r,1).value:r for r in range(2,536) if rw.cell(r,1).value}
# IDEMPOTENCE: press components ALWAYS come from the cached originals (never from the live sheet,
# which holds the blend after the first run).  Cache is created from the pre-surgery backup.
ORIG=json.load(open(M+r'\press_raw_original.json',encoding='utf-8'))
changed=0
for kwcat,hname in HDRMAP.items():
    col=hdr.get(hname)
    if not col: print('  !! header not found:',hname); continue
    pressvals={m:ORIG.get(hname,{}).get(m,0.0) for m in members}
    socvals={m:soc.get(m,{}).get(kwcat,0.0) for m in members}
    sp=p80(pressvals.values()); ss=p80(socvals.values())
    nz=sum(1 for v in socvals.values() if abs(v)>1e-12)
    f=min(1.0,nz/15.0) if SHRINK else 1.0   # SOCIAL_SHRINK: thin-category social share scales with signal breadth
    for m in members:
        pv=pressvals[m]/sp if sp else 0.0; sv=socvals[m]/ss if ss else 0.0
        nv=(1.0-SOCIAL_W*f)*pv+SOCIAL_W*f*sv
        old=rw.cell(mrow[m],col).value or 0.0
        rw.cell(mrow[m],col).value=round(nv,6)
        if abs(nv-old)>1e-9: changed+=1
rw['Z1']='MEDIA BLEND %s: cells = press(p80-scaled)+social(p80-scaled, half-life %.2fy) at 50/50 (thin-cat shrink %s, RT weight %.2f). Backup: %s'%(TODAY,HL,'ON' if SHRINK else 'off',RT_W,os.path.basename(bak))
wb.save(WBP)
print('wrote media blend into Press Release - Raw: %d cells changed (formulas untouched)'%changed)
