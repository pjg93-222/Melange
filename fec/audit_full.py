import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
"""FULL-BODY AUDIT — every module in one report.
Consolidates the integrity (22) + frontier (11) audits and adds correctness checks for the
new modules: money-response, electoral plays, co-sponsor routes, LT-priming, stance, determinism."""
import json,sys,os,subprocess,re,collections,importlib.util
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
B=MB_ROOT; FE=B+r'\fec'
P,F=[],[]
def ck(name,cond,detail=''):
    (P if cond else F).append(name); print(('  OK   ' if cond else 'FAIL  ')+name+((' :: '+detail) if (detail and not cond) else ''))
def run(script):
    return subprocess.run([sys.executable,FE+'\\'+script],capture_output=True,text=True,encoding='utf-8',errors='replace').stdout


print('========== FULL-BODY AUDIT ==========\n[1] Existing audits')
for s,nm,exp in [('audit.py','integrity (22)',22),('audit_frontier.py','frontier (11)',11)]:   # S3-03 audit run-2: assert COUNT too — a silently-skipped check must fail here, not vanish
    out=run(s); m=re.search(r'(\d+) passed, (\d+) FAILED',out)
    ck('%s sub-audit clean'%nm, bool(m) and m.group(2)=='0' and int(m.group(1))>=exp, out.strip().splitlines()[-1] if out else 'no output')
print('\n[2] Money-response (diminishing returns + capacity)')
spec=importlib.util.spec_from_file_location('mr',FE+r'\money_response.py'); mr=importlib.util.module_from_spec(spec); spec.loader.exec_module(mr)
g='Jared Golden'
s1,s2,s4=mr.shift_lean(g,'cu',100000),mr.shift_lean(g,'cu',200000),mr.shift_lean(g,'cu',400000)
ck('money curve concave (doubling $ < doubling effect)', s2<2*s1 and s4<2*s2, '%.1f %.1f %.1f'%(s1,s2,s4))
big=mr.shift_lean('Jared Golden','cu',100000); small=mr.shift_lean('Steve Daines','cu',100000)
ck('capacity-aware (bigger-receipts member moves less)', abs(big)<abs(small))
# 2026-07-02: PT loss-frame asymmetry (Linde-Vis / K&T) is BY DESIGN: comp = -LOSSFRAME x cu, not the plain mirror.
ck('competitor money = -LOSSFRAME x cu (loss-frame asymmetry, PT)', abs(mr.shift_lean(g,'comp',100000)+mr.LOSSFRAME*s1)<1e-9)
_valid_ov=set(mr.ORDER); _deft={mr.defection(m,-30) for m in mr.C}-{None}
ck('defection yields ONLY valid overall tiers (no taxonomy leak)', _deft<=_valid_ov, 'invalid: %s'%(_deft-_valid_ov))
_opps=[m for m in mr.C if mr.PROJ.get(mr.OV.get(m),mr.OV.get(m))=='Opponent']   # committed terminal rung
ck('committed Opponents immune to money defection', bool(_opps) and all(mr.defection(m,-99) is None for m in _opps), '%d opponents'%len(_opps))
# 2026-07-02: test the RUNG, not a named member — Durbin (the old exemplar) legitimately graduated to
# full Opponent once the tiered media weights priced his interchange opposition.
_hsk=[m for m in mr.C if mr.PROJ.get(mr.OV.get(m),mr.OV.get(m))=='Highly Skeptical']
ck('Highly Skeptical deep-but-movable (sub-threshold absorbed, big shock -> Opponent)',
   bool(_hsk) and all(mr.defection(m,-5) is None and mr.defection(m,-12)=='Opponent' for m in _hsk),
   '%d members at rung'%len(_hsk))
print('\n[3] Electoral plays (non-partisan, gated)')
EP=json.load(open(B+r'\electoral_plays.json'))
contest=[m for m,d in EP.items() if d.get('play')=='contest']; defend=[m for m,d in EP.items() if d.get('play')=='defend']
ck('contest plays gated to Opponents only', all(EP[m]['overall']=='Opponent' for m in contest))
ck('defend plays gated to allies only', all(EP[m]['overall'] in ('Champion','Defender','Ally') for m in defend))
pb=collections.Counter(EP[m]['party'] for m in contest)
ck('contest plays not partisan-skewed (<70%% one party)', max(pb['D'],pb['R'])<=0.70*max(1,sum(pb.values())),'D%d R%d'%(pb['D'],pb['R']))
print('\n[4] Stance matrix sanity')
CS=json.load(open(B+r'\category_stance.json')); MAT=CS['matrix']
ck('Durbin is Interchange Opponent', MAT['Richard Durbin']['Interchange']=='Opponent')
ck('Durbin anti on Credit Card (Opponent/Skeptic)', MAT['Richard Durbin']['Credit Card Mandates'] in ('Opponent','Skeptic'))
cnt=collections.Counter(MAT[m][c] for m in MAT for c in CS['cats'])
ck('champion rate disciplined (<2000 of ~9000 cells)', cnt['Champion']<2000, str(cnt['Champion']))
print('\n[5] Co-sponsor route (Pareto + MC reinforcement + determinism)')
def front(env):
    e=dict(os.environ,TOPIC='Mortgage',**env)
    out=subprocess.run([sys.executable,FE+r'\cosponsor_route.py'],capture_output=True,text=True,encoding='utf-8',errors='replace',env=e).stdout
    d={}
    for ln in out.splitlines():
        m=re.search(r'([0-9,]+) +-> +\+([0-9.]+) +co-sponsors +risk +([0-9.]+)',ln)
        if m: d[int(m.group(1).replace(',',''))]=float(m.group(2))
    return d
tr=front({}); mc=front({'MCMODE':'1','MC':'30'}); mc2=front({'MCMODE':'1','MC':'30'})
shared=sorted(set(tr)&set(mc))
ck('route front non-empty', len(tr)>3, '%d pts'%len(tr))
ck('MC-exact >= tree-reach at shared costs (reinforcement)', all(mc[c]>=tr[c]-0.05 for c in shared) if shared else False)
ck('MC route deterministic (same seed -> identical)', mc==mc2)
print('\n[6] LT-priming validity')
pr=json.load(open(B+r'\lt_priming.json'))
ck('priming sorted cheapest-first', all(pr[i]['cost']<=pr[i+1]['cost'] for i in range(len(pr)-1)))
ck('every recipe closes the gap (pressure+money)', all(p['cost']>0 and p['gap']>0 for p in pr))
ck('no committed Opponents/Champions in primeable set', all(p['tier'] not in ('Champion','Defender','Opponent') for p in pr))
print('\n[7] Scenario runner (end-to-end)')
def scen():
    return subprocess.run([sys.executable,FE+r'\scenario.py','--money','Jared Golden:comp:500000'],capture_output=True,text=True,encoding='utf-8',errors='replace').stdout
o1=scen(); o2=scen()
net=re.search(r'([+-][0-9.]+) co-sponsors\)',o1)   # the coalition/mobilization NET line
ck('scenario runs end-to-end (reports a net influence change)', bool(net), o1.strip().splitlines()[-1] if o1 else 'no output')
ck('scenario deterministic (same scenario -> identical)', o1==o2)
ck('competitor shock reduces CU influence (sign sane)', bool(net) and float(net.group(1))<=0, net.group(1) if net else '?')
# H2/H3 regression: competitor shock must reduce the FLIP channel too (caught the imputed-vs-raw ind footing bug)
flnet=re.search(r'winnability [0-9.]+ -> [0-9.]+  \(([+-][0-9.]+) expected flips\)',o1)
ck('competitor shock reduces winnability too (flip channel, consistent footing)', bool(flnet) and float(flnet.group(1))<=0, flnet.group(1) if flnet else '?')
# scenario CU spend now registers via flip channel (regression on the bug we just fixed)
cu_o=subprocess.run([sys.executable,FE+r'\scenario.py','--money','Tim Scott:cu:300000'],capture_output=True,text=True,encoding='utf-8',errors='replace').stdout
fl=re.search(r'([+-][0-9.]+) expected flips',cu_o)
ck('CU spend registers gradual flip-value gain (not absorbed)', bool(fl) and float(fl.group(1))>0, fl.group(1) if fl else '?')
print('\n[8] Adaptive optimizer (Golovin-Krause)')
def opt(env): return subprocess.run([sys.executable,FE+r'\optimize.py'],capture_output=True,text=True,encoding='utf-8',errors='replace',env=dict(os.environ,**env)).stdout
# OPT_OUT -> temp json so the test run doesn't clobber the production optimize_result.json (mirrors FRONTIER_OUT below).
# INC=5000 (divides PMAX=10000): optimize.py's cap check requires room for a FULL chunk, so INC>PMAX allocates nothing.
_OE={'BUDGET':'300000','INC':'5000','OPT_OUT':B+r'\_audit_tmp_optimize.json'}
oo1=opt(_OE); oo2=opt(_OE)
gn=re.search(r'\(([+-][0-9.]+) expected flips\)',oo1)
ck('optimizer runs + reports a winnability frontier', bool(gn), oo1.strip().splitlines()[1] if oo1 else 'no output')
ck('optimizer improves winnability (monotone, sign sane)', bool(gn) and float(gn.group(1))>0, gn.group(1) if gn else '?')
ck('optimizer deterministic (same budget -> identical)', oo1==oo2)
# H1 regression: winning a member (conversion) must be a GAIN -> the spend->winnability path is monotone non-decreasing
_opt=json.load(open(B+r'\_audit_tmp_optimize.json')); _pp=[v for _,v in _opt['path']]
_drops=sum(1 for i in range(1,len(_pp)) if _pp[i]<_pp[i-1]-1e-9)
ck('optimizer path monotone (conversion is a gain, not the old persuadability-loss)', _drops==0, '%d drops; base %.2f final %.2f'%(_drops,_pp[0],_pp[-1]))
# H3 regression: members with NO FEC data must NOT rank as top flip targets (ind=0 -> pflip~1 was misreading "missing" as "no opposition")
_s=importlib.util.spec_from_file_location('fmA',FE+r'\flip_model.py'); _fm=importlib.util.module_from_spec(_s); _s.loader.exec_module(_fm)
_wn=collections.Counter()
for c in _fm.cats:
    cs,ct,nA,nB,mAt,mBt,tgt=_fm.topic_setup(c,_fm.CS0)
    for n in _fm.members: _wn[n]+=tgt[n]*_fm.pflip(_fm.cu0[n],_fm.ind0[n],_fm.R[n],nA[n],nB[n],mAt,mBt)
_nd=sum(1 for n,_ in _wn.most_common(20) if n in _fm.nodata)
ck('no zero-FEC-data member ranks top-20 winnability (missing != no-opposition)', _nd==0, '%d of top-20 are data-less'%_nd)
# HIGH-3 (corrected): impute ONLY no-FEC-record (receipts=0) blind members; trust FEC-verified-real ind=0 zeros
_blind_ok=all(_fm.ind0[n]>0 for n in _fm.ind_imputed)
_realzero=[n for n in _fm.members if (_fm.C[n].get('receipts') or 0)>0 and ((_fm.C[n]['banks'] or 0)+(_fm.C[n]['finserv'] or 0))==0]
_real_kept=all(_fm.ind0[n]==0 for n in _realzero)
ck('imputation limited to no-FEC-record members; verified-real ind=0 zeros trusted', _blind_ok and _real_kept, 'blind %d imputed, %d real-zeros trusted'%(len(_fm.ind_imputed),len(_realzero)))
# HIGH-1 regression: frontier cascade now uses edge-keyed CRN -> a single-topic run is deterministic across repeats
def bf(): return subprocess.run([sys.executable,FE+r'\budget_frontier.py'],capture_output=True,text=True,encoding='utf-8',errors='replace',env=dict(os.environ,TOPIC='Interchange',FRONTIER_OUT=B+r'\_audit_tmp_frontier.json')).stdout   # temp out -> don't clobber the all-topics production json
bf1=bf(); bf2=bf()
ck('budget_frontier deterministic w/ edge-keyed CRN (single topic)', bf1==bf2 and 'Interchange' in bf1)

print('\n[NEW] Salience shock + press SNA layers (Noble-Turner / HCoI / Fink / Zhou-Elejalde / Joo)')
import json as _j
if os.path.exists(B+r'\salience_advisory.json'):
    _adv=_j.load(open(B+r'\salience_advisory.json'))['advisory']
    ck('salience advisory covers all issues', len(_adv)>=18, str(len(_adv)))
    _pr=[a['params'] for a in _adv]
    ck('salience regime probs valid (p+q+b~1, all in [0,1])',
       all(0<=x['p']<=1 and 0<=x['q']<=1 and 0<=x['b']<=1 and 0.94<=x['p']+x['q']+x['b']<=1.01 for x in _pr))
else: ck('salience advisory present (run salience_shock.py --advise)', False)
if os.path.exists(B+r'\dashboard_data.json'):
    _dd=_j.load(open(B+r'\dashboard_data.json',encoding='utf-8'))
    _sal=_dd.get('engine',{}).get('sal')
    ck('bundle exports Noble sal params (one per issue layer)', bool(_sal) and len(_sal)==len(_dd['issues']),
       '%s vs %s'%(len(_sal or []),len(_dd['issues'])))
if os.path.exists(B+r'\press_hcoi.json'):
    _hc=_j.load(open(B+r'\press_hcoi.json',encoding='utf-8'))
    _allm=[m2 for c in _hc['communities'] for m2 in c['members']]
    ck('HCoI communities non-trivial and disjoint (Louvain partition)',
       len(_hc['communities'])>=3 and len(_allm)==len(set(_allm)), '%d comms'%len(_hc['communities']))
if os.path.exists(B+r'\press_engagement.json'):
    _pe=_j.load(open(B+r'\press_engagement.json',encoding='utf-8'))
    ck('engagement layer: valid probabilities, no self-edges',
       all(0<e['p']<=1 and e['src']!=e['dst'] for e in _pe['directed']), '%d edges'%len(_pe['directed']))
if os.path.exists(B+r'\stance_dynamics.json'):
    _sd=_j.load(open(B+r'\stance_dynamics.json',encoding='utf-8'))
    ck('stance-dynamics imputation beats coin flip on masked cells (sign agreement > 0.55)',
       _sd['masking_validation']['sign_agreement']>0.55, str(_sd['masking_validation']))
    ck('imputation proposals carry provenance (user adjudicates; matrix untouched)',
       os.path.exists(B+r'\stance_imputation_proposals.csv') and
       'provenance' in open(B+r'\stance_imputation_proposals.csv',encoding='utf-8-sig').readline())
if os.path.exists(B+r'\frame_alignment.json'):
    _fa=_j.load(open(B+r'\frame_alignment.json',encoding='utf-8'))
    ck('frame-alignment rates in [0,1] across issues', all(0<=x['alignment']<=1 for x in _fa['alignment']))


print('\n[GOLD] Golden labels + domain classifier + collector DB')
if os.path.exists(B+'\\cu_golden_labels.csv'):
    import csv as _csv
    _gl=list(_csv.DictReader(open(B+'\\cu_golden_labels.csv',encoding='utf-8-sig')))
    _cls={'support','oppose','neutral','unrelated'}
    ck('golden label set parses, all labels in vocabulary', len(_gl)>=700 and all(r['label'] in _cls for r in _gl), '%d rows'%len(_gl))
    _sp=collections.Counter(r['split'] for r in _gl)
    ck("golden set preserves the user's train/test split and firewalls goldeval",
       _sp.get('train')==456 and _sp.get('test')==87 and _sp.get('goldeval',0)>0, str(dict(_sp)))
    _du=collections.Counter(r['url'] for r in _gl if r['url'])
    ck('golden set has no duplicate URLs', max(_du.values())==1 if _du else False)
    _cf=[r for r in _gl if r['conflict']]
    # two provenance formats are compliant: the arrow ('aug=X->queue=Y', unresolved flag) and the
    # user-adjudicated form 'user-resolved: <label> (was aug=X queue=Y)' (2026-07-03 overnight pass, 36 rows)
    ck('label conflicts are flagged, not silently resolved',
       all(('->' in r['conflict']) or r['conflict'].startswith('user-resolved:') for r in _cf), '%d flagged (user-resolved carries its trail inline)'%len(_cf))
else: ck('golden label set present (run build_golden_labels.py)', False)
if os.path.exists(B+'\\stance_clf_composed.pkl'):
    try:
        import pickle as _pk
        _clf=_pk.load(open(B+'\\stance_clf_composed.pkl','rb'))
        _pr=_clf.predict(['target: Credit Card Mandates. speaker: member. Senator introduces the Credit Card Competition Act to cap interchange.',
                          'target: Credit Unions (direct). speaker: member. Senator celebrates credit union community investment.'])
        ck('domain classifier loads and predicts sane labels', _pr[0]=='oppose' and _pr[1]=='support', str(list(_pr)))
    except Exception as e: ck('domain classifier loads', False, str(e)[:80])
if os.path.exists(B+'\\social_media.db'):
    import sqlite3 as _sq
    _c=_sq.connect(B+'\\social_media.db')
    _ok=_c.execute('PRAGMA integrity_check').fetchone()[0]
    _orph=_c.execute("SELECT COUNT(*) FROM posts WHERE platform IS NULL OR post_id IS NULL").fetchone()[0]
    ck('social_media.db integrity + no orphan posts', _ok=='ok' and _orph==0, '%s / %d orphans'%(_ok,_orph))

print('\n========================================')

# RECEPTIVITY LAYER (2026-07-02): coverage + documented caps.
if os.path.exists(B+r'\member_receptivity.json'):
    _rj=json.load(open(B+r'\member_receptivity.json'))['members']
    ck('receptivity layer covers all members', len(_rj)==533, str(len(_rj)))
    ck('receptivity multipliers within documented caps',
       all(0.30<=v['seed_prob']<=0.90 and 0.50<=v['pressure_mult']<=1.60 and 0.80<=v['edge_mult']<=1.20 for v in _rj.values()))

# W1 guard 2026-07-02: the press-pillar SUMPRODUCT weight row once held stray LET-formula remnants that
# evaluated to 0 on the three TOP-tier categories — every weight must be a positive literal number.
import openpyxl as _px
_wb=_px.load_workbook(B+r'\Moneyball Main Version - Blended.xlsx',data_only=True)
_w535=[_wb['Press Release - Normalized'].cell(535,c).value for c in range(5,24)]
ck('press-pillar weight row 535: 19 numeric positive weights (no formula remnants)',
   all(isinstance(v,(int,float)) and v>0 for v in _w535),str(_w535))
# 2026-07-04 integrity fix guard: the press component must be DYNAMIC (built from the current tone
# csv), never the frozen 07-02 archive (which silently excluded every post-archive article: 197
# members frozen forever). Checks the blend's meta artifact is fresh vs the csv and coverage grew.
_pm_p=B+r'\press_component_meta.json'
if os.path.exists(_pm_p):
    _pm=json.load(open(_pm_p))
    _tone_p=os.path.join(os.path.dirname(B),'Draft Systems','cu_press_stance_tone.csv')
    _fresh=(os.path.getmtime(_tone_p)-_pm.get('built_from_csv_mtime',0))<8*86400 if os.path.exists(_tone_p) else True   # csv may be up to one weekly cycle newer; beyond that the blend stopped ingesting
    ck('media-blend press component is DYNAMIC and fresh (not the frozen archive)',
       _fresh and _pm.get('members_nonzero',0)>=197,
       'members=%s fresh=%s'%(_pm.get('members_nonzero'),_fresh))
    # 2026-07-04: intensity must be NON-DEGENERATE. The first dynamic build clipped |press_value|
    # to a 0.25 floor that 100% of articles saturated -> the component silently became a pure
    # article-count measure (flipped Warren +310 ranks). Guard: recorded pv stats must show real
    # spread (many distinct values, median strictly inside (0, max)).
    _pvs=_pm.get('pv_stats') or {}
    ck('press component intensity non-degenerate (no clip saturation / constant weights)',
       _pvs.get('n_distinct',0)>=20 and 0<_pvs.get('median',0)<_pvs.get('max',0),
       'pv_stats=%s'%_pvs)
    # 2026-07-04 stack wiring guard: when the press_stance_final.csv sidecar exists, the stack must
    # actually drive the signs (>=90% stack vs DEBATE-fallback) and the unrelated->0 mention-noise
    # kill must be active. A silent fall-back to DEBATE (0.571 adversarial-frame) is a regression.
    _sk=_pm.get('stack') or {}
    if _sk.get('sidecar'):
        _tot=_sk.get('stack_signed',0)+_sk.get('debate_fallback',0)
        ck('press stack drives the dynamic component (not silently on DEBATE fallback)',
           _tot>0 and _sk.get('stack_signed',0)/_tot>=0.9 and _sk.get('unrelated_zeroed',0)>0,
           'stack=%s'%_sk)
# 2026-07-04 nomological fix guard: receptivity must run on the BEHAVIORAL basis (the lexical Big5
# was INDICTED by the pre-registered label-free validation — big5_nomological_prereg.md). A silent
# fall-back to lexical (missing dispositions artifact) is a regression to an indicted instrument.
_rc_p=B+r'\member_receptivity.json'
if os.path.exists(_rc_p):
    _rc=json.load(open(_rc_p))
    _bd_p=B+r'\behavioral_dispositions.json'
    _bd_ok=os.path.exists(_bd_p) and len((json.load(open(_bd_p)) or {}).get('members',{}))>=450
    ck('receptivity runs on the behavioral basis (lexical Big5 indicted 2026-07-04)',
       _rc.get('basis')=='behavioral' and _bd_ok,
       'basis=%s dispositions_ok=%s'%(_rc.get('basis'),_bd_ok))
    # ROUND-3 N-slot guard (2026-07-09): the susceptibility N-slot must be the behavioral reactivity
    # read (n_slot='behavioral'); a silent RECEPT_N=text revert or a reactivity-coverage collapse
    # would sail through the basis gate above. Coverage floor 150 (currently 207/533).
    _nsl=_rc.get('n_slot'); _nsrc=sum(1 for v in _rc.get('members',{}).values() if v.get('n_source')=='reactivity')
    ck('receptivity N-slot = behavioral reactivity (round-3; no silent text revert)',
       _nsl=='behavioral' and _nsrc>=150,'n_slot=%s reactivity_members=%d'%(_nsl,_nsrc))
    # COOP-SLOT guard (audit 2026-07-10, mirrors the N-slot guard): the A-slot must be the promoted
    # share-based cooperation_v2 (@94f09cf); a silent RECEPT_COOP=v1 revert or a coverage collapse
    # (coop_v2_candidate staleness / c2-floor starvation) would sail through the basis gate above.
    _csl=_rc.get('coop_slot'); _csrc=sum(1 for v in _rc.get('members',{}).values() if v.get('coop_source')=='coop_v2')
    _cv=[v.get('cooperation_v2_z') for v in _rc.get('members',{}).values() if v.get('cooperation_v2_z') is not None]
    ck('receptivity A-slot = cooperation_v2 (promotion @94f09cf; coverage>=250, |z|<=5, no silent v1 revert)',
       _csl=='v2' and _csrc>=250 and len(_cv)>=250 and all(abs(x)<=5.0 for x in _cv),
       'coop_slot=%s coop_v2_members=%d'%(_csl,_csrc))
    if _bd_ok:
        _rv=[d['reactivity_z'] for d in json.load(open(_bd_p))['members'].values() if d.get('reactivity_z') is not None]
        ck('reactivity_z disposition sane (coverage >=150, |z|<=5)',
           len(_rv)>=150 and all(abs(v)<=5.0 for v in _rv),'%d covered'%len(_rv))
else:
    # (2026-07-09 fix: this branch previously fired a MISLABELED press-component check name)
    ck('receptivity artifact present (member_receptivity.json)',False,'missing — chain step 1 (receptivity_layer.py) did not run')
# S2-04 guard (audit 2026-07-02): every workbook reader hardcodes range(3,536) for the 533-member roster.
# If a member row is ever added/removed, those readers silently truncate or NUL the tail. Assert on
# R&A col A — TYPED names, immune to the phase-2 openpyxl-save cache death (Blended col A is
# formula-backed and legitimately reads empty between Excel opens).
_roster=len(json.load(open(B+r'\congestion.json')))
_ra=_wb['Rank & Allocation']; _wbrows=sum(1 for r in range(3,536) if _ra.cell(r,1).value)
ck('workbook member rows == roster size (no silent row drift)', _wbrows==_roster, 'workbook %d vs roster %d'%(_wbrows,_roster))
# Roadmap-#9 phase 1 (2026-07-02): the whole raw->normalized->pillar->score->rank chain is reproduced
# in Python (compute_pillars.py) and must match the sheet EXACTLY — catches any silent formula edit.
_pp=run('compute_pillars.py')
ck('python pillar shadow-compute parity (rank math reproducible, 533/533)','PARITY: CLEAN' in _pp,
   _pp.strip().splitlines()[-1] if _pp else 'no output')

if os.path.exists(B+r'\stance_training.jsonl'):
    import hashlib as _hl, json as _js
    _tr=set(); _te=set()
    for _l in open(B+r'\stance_training.jsonl',encoding='utf-8'):
        _r=_js.loads(_l)
        _vs=[_r.get('text',''),_r.get('title',''),_r.get('stance_span','')]
        _hs={_hl.md5(v.strip().lower()[:400].encode()).hexdigest() for v in _vs if v and v.strip()}
        if _r['split']=='train': _tr|=_hs
        elif _r['split']=='test': _te|=_hs
    _ov=len(_tr&_te)
    ck('train/test split-leak (text-hash, incl. augment views) within known bound', _ov<=4,
       '%d collisions (4 known: same-ACU-article rows 75/214; fix = same-text same-split on next label refresh)'%_ov)

# run-5b guards (audit 2026-07-06): the psychology/media-layer artifacts had ZERO audit coverage —
# a truncated big5_llm_opus.json or malformed reference/co-appearance edges would sail through.
# Schema + sanity floors only (freshness is meaningless mid-collector-crawl); each skips if absent.
if os.path.exists(B+r'\big5_llm_opus.json'):
    _b5=json.load(open(B+r'\big5_llm_opus.json',encoding='utf-8')).get('traits',{})
    _bad=sum(1 for d in _b5.values() if not all(k in d for k in ('O','C','E','A','ES')) or not d.get('n_chunks'))
    ck('big5_llm artifact schema (5 traits + n_chunks per member, coverage >=400)',
       len(_b5)>=400 and _bad==0, '%d members, %d malformed'%(len(_b5),_bad))
if os.path.exists(B+r'\member_references.json'):
    _re_=json.load(open(B+r'\member_references.json',encoding='utf-8')).get('edges',[])
    _bad=sum(1 for e in _re_ if not all(k in e for k in ('a','b','n_raw','n_scored','pos','neg','net')) or e['n_scored']<(e['pos']+e['neg']))
    ck('reference-layer edge schema (keys present, scored>=pos+neg, >=1000 edges)',
       len(_re_)>=1000 and _bad==0, '%d edges, %d malformed'%(len(_re_),_bad))
# run-5h guard (user 2026-07-06 'make sure the displays are entirely accurate'): the member-desk
# pillar bars + weights MUST match the rank authority (ranks_python.json) — they silently drifted
# (Crapo influence 1.000 in the authority displayed as 0.222 from a stale workbook column; weights
# 0.40/0.20/0.35/0.05 vs the live 0.25/0.30/0.40/0.05), making the #1 rank look unjustified on the
# desk. This asserts the DISPLAYED decomposition reconstructs the DISPLAYED score for every member.
if os.path.exists(B+r'\member_desk_bundle.json') and os.path.exists(B+r'\ranks_python.json'):
    _bun=json.load(open(B+r'\member_desk_bundle.json',encoding='utf-8')); _ra=json.load(open(B+r'\ranks_python.json',encoding='utf-8'))
    _W=_bun.get('weights',{}); _pcts=_ra.get('pcts',{})
    _bad=[]; _nomatch=0
    for _m in _bun.get('members',[]):
        _nm=_m.get('name'); _p=_pcts.get(_nm)
        if not _p: continue
        # displayed pillars == authority pcts
        if any(abs((_m.get(_dk) or 0)-_p[_ak])>1e-4 for _dk,_ak in (('press_n','press'),('leg_n','leg'),('comm_n','inf'),('demo_n','dem'))):
            _nomatch+=1
        # displayed weights*displayed pillars reconstruct displayed score
        _rc=_W.get('leg',0)*(_m.get('leg_n') or 0)+_W.get('press',0)*(_m.get('press_n') or 0)+_W.get('comm',0)*(_m.get('comm_n') or 0)+_W.get('demo',0)*(_m.get('demo_n') or 0)
        if abs(_rc-(_m.get('score') or 0))>0.003: _bad.append(_nm)
    ck('desk pillar bars match rank authority (no stale-workbook drift)', _nomatch==0, '%d members mismatch authority pcts'%_nomatch)
    ck('desk displayed pillars*weights reconstruct displayed score', len(_bad)==0, '%d members fail reconstruction: %s'%(len(_bad),_bad[:3]))
# run-5j guard (2026-07-06): exact-duplicate speech rows (same member+package+text) inflate word
# counts + big5 chunk sampling. The CREC backfill introduced 922 (no pre-insert dedup); collector
# legs now carry stored-package guards. Assert the corpus stays exact-dup-clean (threshold covers
# the small user-gated legacy ABC/CNN set, currently 0 post-dedup).
if os.path.exists(B+r'\social_media.db'):
    import sqlite3 as _sq
    _c=_sq.connect(B+r'\social_media.db',timeout=60); _c.execute('PRAGMA query_only=1')
    _ex=_c.execute("SELECT COALESCE(SUM(c-1),0) FROM (SELECT COUNT(*) c FROM speeches GROUP BY member,package,text HAVING c>1)").fetchone()[0]
    _c.close()
    ck('speech corpus exact-duplicate free (member+package+text)', _ex<=50, '%d exact-dup surplus rows'%_ex)
if os.path.exists(B+r'\co_appearance.json'):
    _co=json.load(open(B+r'\co_appearance.json',encoding='utf-8')).get('edges',[])
    _bad=sum(1 for e in _co if not all(k in e for k in ('a','b','n','last','bipartisan')) or e['n']<1)
    ck('co-appearance edge schema (keys present, n>=1, non-empty)', len(_co)>=100 and _bad==0,
       '%d pairs, %d malformed'%(len(_co),_bad))
# 2026-07-09 guards: clean-audio/narrative layer (same rationale as run-5b — display artifacts with
# zero coverage would silently truncate/malform). Skip-if-absent; all display-only.
if os.path.exists(B+r'\member_narratives.json'):
    _na=json.load(open(B+r'\member_narratives.json',encoding='utf-8'))
    _nbad=sum(1 for v in _na.values() if v.get('ok') and not (v.get('p1') and v.get('p2') and v.get('p3')))
    _nok=sum(1 for v in _na.values() if v.get('ok'))
    ck('narrative artifact schema (ok => 3 non-empty paragraphs; coverage >=500)', _nok>=500 and _nbad==0,
       '%d ok, %d malformed'%(_nok,_nbad))
if os.path.exists(B+r'\b5_audio_cache.json') and os.path.exists(B+r'\b5_audio_verify.json'):
    _au=json.load(open(B+r'\b5_audio_cache.json',encoding='utf-8'))
    _vf=json.load(open(B+r'\b5_audio_verify.json',encoding='utf-8'))
    _keep={k.split('/')[0] for k,v in _vf.items() if isinstance(v,dict) and v.get('keep')}
    _stray=[m for m in _au.get('members',[]) if m not in _keep]   # voiceprint with zero kept clips = gate breach
    ck('clean-audio voiceprints verification-gated (every cached member has a keep-clip; 88 eGeMAPS)',
       _au.get('n_features')==88 and len(_au.get('members',[]))>=300 and not _stray,
       '%d members, %d stray'%(len(_au.get('members',[])),len(_stray)))
if os.path.exists(B+r'\b5_es_voice.json'):
    _ev=json.load(open(B+r'\b5_es_voice.json',encoding='utf-8'))
    _evm=_ev.get('members',{}); _ebad=sum(1 for v in _evm.values() if v.get('voice_es_z') is None or v.get('gap') is None)
    ck('voice-ES display artifact schema (z+gap per member; matches the recorded look r=+0.208)',
       len(_evm)>=300 and _ebad==0 and abs((_ev.get('heldout_r') or 0)-0.208)<1e-9,
       '%d members, %d malformed, r=%s'%(len(_evm),_ebad,_ev.get('heldout_r')))
# say-do corroboration gate coherence (2026-07-07): every capped cell must DISPLAY Ally with its raw
# tier preserved as Champion/Defender; every proven cell must BE Champion/Defender in the matrix.
_g=(CS.get('gate') or {})
if _g:
    _cap=_g.get('capped') or {}; _prov=_g.get('proven') or {}
    _b1=sum(1 for m,cc in _cap.items() for c,raw in cc.items()
            if MAT.get(m,{}).get(c)!='Ally' or raw not in ('Champion','Defender'))
    _b2=sum(1 for m,cs_ in _prov.items() for c in cs_ if MAT.get(m,{}).get(c) not in ('Champion','Defender'))
    ck('say-do gate coherent (capped->Ally w/ raw C/D preserved; proven are C/D cells)', _b1==0 and _b2==0,
       '%d capped cells / %d proven cells; %d+%d incoherent'%(sum(len(v) for v in _cap.values()),
       sum(len(v) for v in _prov.values()),_b1,_b2))
    # corroboration paths A/V/J (2026-07-08): every corroborated cell must BE Champion/Defender in the
    # matrix (it survived the cap) and must NOT also be listed capped for the same member; every J path
    # must belong to a gatekeep category.
    _cor=_g.get('corrob') or {}; _gk=set(_g.get('gatekeep') or [])
    _b3=sum(1 for m,cc in _cor.items() for c,pth in cc.items()
            if MAT.get(m,{}).get(c) not in ('Champion','Defender') or c in (_cap.get(m) or {})
            or pth not in ('A','V','J') or (pth=='J' and c not in _gk))
    _cbp=collections.Counter(pth for cc in _cor.values() for pth in cc.values())
    ck('say-do corroboration paths coherent (A/V/J cells are C/D, un-capped; J in gatekeep set)', _b3==0,
       'corroborated A%d V%d J%d; %d incoherent'%(_cbp['A'],_cbp['V'],_cbp['J'],_b3))
else:
    ck('say-do gate block present in category_stance.json', False, 'gate key missing — producer predates 2026-07-07 landing')

print('FULL-BODY AUDIT — %d passed, %d FAILED'%(len(P),len(F)))
if F: print('  FAILURES:',F)
else: print('  ALL MODULES CLEAN.')
