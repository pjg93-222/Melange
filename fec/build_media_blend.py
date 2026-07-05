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
import sys, os, json, re, shutil, datetime, collections
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
# ---- STANCE STACK OVERRIDE (user-ratified 2026-07-04 "lets first wire this in"): per-tweet stance
# from tweet_stance_stack.py (0.855 acc / 0.819 F1 honest OOF vs the user's golds; old transfer
# model measured 0.481). Join by member+normalized-text (100% match on probe). Intensity becomes
# tier-weighted confidence (unanimous/majority/review); 'unrelated' maps to sign 0 (excluded) —
# ~900 noise posts stop polluting the blend. Unmatched rows keep their existing label. Absent file
# -> legacy behavior (neutral fallback discipline).
STACK={}
_sf=M+r'\tweet_stance_final.csv'
if os.path.exists(_sf):
    import csv as _csv,io as _io
    def _nrm(t):
        t=re.sub(r'https?://\S+','',str(t or '').lower())
        return re.sub(r'[^a-z0-9]','',t)[:80]
    for _r in _csv.DictReader(_io.open(_sf,encoding='utf-8-sig',newline='')):
        STACK[(_r['member'],_nrm(_r['text']))]= _r
    _TIERW={'unanimous':1.0,'majority':0.7,'review':0.35}
    print('stance-stack override ACTIVE: %d labeled tweets loaded'%len(STACK))
else:
    print('!! tweet_stance_final.csv missing — legacy per-tweet stances in force')
soc=collections.defaultdict(lambda:collections.defaultdict(float)); nassigned=0
nover=0
for _,r in corp.iterrows():
    _st=r['stance']; _inten_override=None
    if STACK:
        _s=STACK.get((r['member'],_nrm(r['text'])))
        if _s:
            _st=_s['stack_stance']; _inten_override=_TIERW.get(_s['tier'],0.5); nover+=1
    sg=SIGN.get(_st,0.0)
    if sg==0.0: continue
    try: age=(TODAY-datetime.date.fromisoformat(str(r['date'])[:10])).days/365.25
    except Exception: continue
    if _inten_override is not None:
        inten=_inten_override
    else:
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
os.makedirs(M+r'\backups',exist_ok=True)
bak=M+r'\backups\Moneyball Main Version - Blended.BACKUP-%s.xlsx'%datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
shutil.copy2(WBP,bak); print('backup:','backups/'+os.path.basename(bak))
wb=openpyxl.load_workbook(WBP)             # formulas preserved
rw=wb['Press Release - Raw']
hdr={rw.cell(1,c).value:c for c in range(1,30) if rw.cell(1,c).value}
members=[rw.cell(r,1).value for r in range(2,536) if rw.cell(r,1).value]
mrow={rw.cell(r,1).value:r for r in range(2,536) if rw.cell(r,1).value}
# IDEMPOTENCE: press components never come from the live sheet (it holds the blend after run 1).
# 2026-07-04 INTEGRITY FIX (user-ratified "fix it"): the frozen 07-02 archive meant NO press article
# collected after 2026-07-02 could ever reach the workbook (197 members, frozen forever). The press
# component is now DYNAMIC — aggregated from the CURRENT cu_press_stance_tone.csv with the same
# shape as the social side: sign x intensity(press_value) x decay(0.5^(age/2.0yr press half-life)),
# category-split. R's exact archive units were not reproducible (best r=0.38; hidden steps), and
# don't need to be: the blend p80-normalizes press and social, so relative structure is what matters.
# PRESS_DYNAMIC=0 reverts to the frozen archive.
ORIG=json.load(open(M+r'\press_raw_original.json',encoding='utf-8'))
if os.environ.get('PRESS_DYNAMIC','1')!='0':
    import csv as _csv,io as _io
    _tone=os.path.join(DRAFT,'cu_press_stance_tone.csv') if 'DRAFT' in dir() else os.path.join(os.path.dirname(M),'Draft Systems','cu_press_stance_tone.csv')
    _dyn=collections.defaultdict(lambda:collections.defaultdict(float))
    _n=0; _nm=set(); _pvs=[]
    # STACK OVERRIDE (user-ratified 2026-07-04 "wire in the most accurate stack"): press_stance_final.csv
    # (press_stance_stack.py, 760-gold meta: 0.837 all-gold frame / 0.765 adversarial frame; DEBATE alone
    # 0.796/0.571). Stack label replaces DEBATE sign; UNRELATED -> 0 (kills ACU trade-digest mention
    # noise, the Warren #103 driver); tier-weighted trust (measured: unan .955 / maj .776 / rev .638).
    # Missing sidecar or unmatched url -> DEBATE fallback (legacy behavior, never silently empty).
    _stk={}
    _sfp=M+r'\press_stance_final.csv'
    if os.path.exists(_sfp):
        for _r in _csv.DictReader(_io.open(_sfp,encoding='utf-8-sig',newline='')):
            _stk[(_r.get('url') or '').strip().rstrip('/')]=((_r.get('stack_label') or '').strip().lower(),(_r.get('tier') or '').strip().lower())
    _TW={'unanimous':1.0,'majority':0.7,'review':0.35}
    # ATTRIBUTION-STRENGTH channel weight (user 2026-07-04 "that is such a regression" — Warren
    # pulled to #83 by trade-press tagging): a member's OWN .gov press release is member-authored
    # evidence (attribution-clean, like tweets); trade/third-party coverage that merely tags the
    # member is weaker. His golds label trade coverage support (41/65 third-party = support) — the
    # LABELS stand; this dial reduces the CREDIT such articles contribute to the 40%-weight pillar.
    # PRESS_THIRD_W env reverts (1.0 = old behavior).
    _W3=float(os.environ.get('PRESS_THIRD_W','0.5'))
    _n_stack=0; _n_fallback=0; _n_unrel=0; _n_own=0; _n_third=0
    def _pdate(s):
        for _f in ('%m/%d/%Y','%Y-%m-%d','%m/%d/%y'):
            try: return datetime.datetime.strptime((s or '').strip(),_f).date()
            except ValueError: pass
        return None
    for _r in _csv.DictReader(_io.open(_tone,encoding='utf-8-sig',newline='')):
        _m=_r.get('member')
        _hit=_stk.get((_r.get('url') or '').strip().rstrip('/'))
        if _hit is not None:
            _lab,_tier=_hit
            if _lab=='unrelated': _n_unrel+=1; continue   # mention noise -> zero contribution
            _sg=SIGN.get(_lab,0.0)*_TW.get(_tier,0.7)
            if _sg!=0.0: _n_stack+=1
        else:
            _sg=SIGN.get((_r.get('stance') or '').lower(),0.0)
            if _sg!=0.0: _n_fallback+=1
        if not _m or _sg==0.0: continue
        # intensity = |press_value| (column embeds sign; stance supplies sign here). NO floor:
        # the csv's units are tiny (~0.03 scale) and a 0.25 floor saturated 100% of articles,
        # erasing intensity into a pure count measure. Top clip 3.0 = outlier guard only.
        try: _pv=min(3.0,abs(float(_r.get('press_value'))))
        except (TypeError,ValueError): _pv=0.0
        if _pv==0.0: continue   # no intensity evidence -> no contribution
        _d=_pdate(_r.get('date'))
        if _d is not None: _dec=0.5**(max(0.0,(TODAY-_d).days/365.25)/2.0)
        else:
            try: _dec=max(0.0,min(1.0,float(_r.get('recency_weight') or 0.5)))
            except (TypeError,ValueError): _dec=0.5
        _cats=[c.strip() for c in (_r.get('categories') or '').split(';') if c.strip() and c.strip() in ORIG]
        if not _cats: continue
        _ul=(_r.get('url') or '').lower()
        if '.house.gov' in _ul or '.senate.gov' in _ul: _cw=1.0; _n_own+=1
        else: _cw=_W3; _n_third+=1
        _n+=1; _nm.add(_m); _pvs.append(_pv)
        for _c in _cats: _dyn[_c][_m]+=_sg*_pv*_dec*_cw/len(_cats)
    ORIG={c:dict(_dyn.get(c,{})) for c in ORIG}   # same shape/keys as the archive
    from moneyball_core import dump_atomic as _da
    _pvs.sort()
    _da({'built_from_csv_mtime':os.path.getmtime(_tone),'articles_used':_n,'members_nonzero':len(_nm),
         'pv_stats':{'min':_pvs[0] if _pvs else 0.0,'median':_pvs[len(_pvs)//2] if _pvs else 0.0,
                     'max':_pvs[-1] if _pvs else 0.0,'n_distinct':len(set(_pvs))},
         'stack':{'sidecar':os.path.exists(_sfp),'stack_signed':_n_stack,'debate_fallback':_n_fallback,
                  'unrelated_zeroed':_n_unrel},
         'channel_weight':{'third_w':_W3,'own_domain':_n_own,'third_party':_n_third},
         'note':'dynamic press component (PRESS_DYNAMIC); archive fallback with PRESS_DYNAMIC=0'},
        M+r'\press_component_meta.json')
    print('DYNAMIC press component: %d signed articles -> %d members (stack-signed %d, DEBATE fallback %d, unrelated zeroed %d; own-domain %d @1.0, third-party %d @%.2f)'%(_n,len(_nm),_n_stack,_n_fallback,_n_unrel,_n_own,_n_third,_W3))
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
wb.calculation.fullCalcOnLoad=True   # PHASE-2: the workbook is a VIEW — Excel recalcs it on open; no COM recalc anywhere
wb.save(WBP)
print('wrote media blend into Press Release - Raw: %d cells changed (formulas untouched)'%changed)
