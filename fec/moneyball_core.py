# -*- coding: utf-8 -*-
"""MONEYBALL SHARED KERNEL (architecture review 2026-07-02) — the single source for every block that
was previously copy-pasted across the engines and drifted (measured pre-refactor: network loader x17,
party loader x11, cpf x8 under TWO different physics, IMP x6, PERS x5, splitmix x4, receptivity x9;
three of the week's five code bugs were duplication drift: the CFPB block-merge missed in the
frontier, the BETA export break, the PERS_NONE comment/code contradiction).

Physics note — there are deliberately TWO partisan edge factors, now under distinct names:
  cpf_diffusion : cascade/contagion physics — cross-party edges dampened unless both ends are
                  bridge-builders (0.4+0.6*sqrt(bpf_a*bpf_b)); same-party 1.0.
  cpf_pressure  : direct-persuasion physics (Furnas/Bakker source-alignment) — co-partisan pressure
                  x1.7, out-partisan x0.5.
Loaders are lazy + cached; importing this module does NO workbook IO."""
import os,sys,json,csv,glob,collections,math
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from paths import ROOT,DRAFT,WORKBOOK,p
import bill_rules as BR
import media_rules as MR
_c={}
def congestion():
    if 'C' not in _c: _c['C']={m['member']:m for m in json.load(open(p('congestion.json')))}
    return _c['C']
def members(): return list(congestion())
def name2bio():
    if 'n2b' not in _c: _c['n2b']={m:v['bioguide'] for m,v in congestion().items() if v.get('bioguide')}
    return _c['n2b']
def bio2name():
    if 'b2n' not in _c: _c['b2n']={v:k for k,v in name2bio().items()}
    return _c['b2n']
def party():
    """member name -> 'D'/'R'/'I'/'?' from the HS119..117 rosters (first-seen wins)."""
    if 'prt' not in _c:
        pb={}
        for cn in (119,118,117):
            f=p('votes','HS%d_members.csv'%cn)
            if os.path.exists(f):
                for row in csv.DictReader(open(f,encoding='utf-8')):
                    b=row.get('bioguide_id'); pc=str(row.get('party_code'))
                    if b and b not in pb: pb[b]={'100':'D','200':'R'}.get(pc,'I')
        _c['prt']={m:pb.get(v.get('bioguide',''),'?') for m,v in congestion().items()}
    return _c['prt']
def bpf():
    if 'bpf' not in _c:
        BP=json.load(open(p('bipartisan.json')))
        _c['bpf']={m:BP.get(m,24)/100.0 for m in congestion()}
    return _c['bpf']
def receptivity():
    if 'rec' not in _c:
        try:
            _c['rec']=json.load(open(p('member_receptivity.json')))['members'] if os.environ.get('RECEPT_LAYER','1')!='0' else {}
        except FileNotFoundError: _c['rec']={}
    return _c['rec']
def rc(m,k,d=1.0): return receptivity().get(m,{}).get(k,d)
def press_matrix():
    """PHASE-2 (system-of-record inversion, user sign-off 2026-07-02): Python-owned press
    normalization. Reads 'Press Release - Raw' VALUES (always fresh — the blend writes literals)
    and the row-535 tiered weights (user-edited literals on the Normalized sheet), applies signed
    positive/negative-extrema normalization within each domain. The upstream p80 transform only
    makes press and social components commensurable; this distinct step makes domains comparable.
    No dependency on the sheet's cached formula results,
    hence no COM recalc needed anywhere in the pipeline.
    Returns (norm {col:{member:val}}, w535 {col:weight}, headers {col:name})."""
    if 'pressM' not in _c:
        import openpyxl
        wb=openpyxl.load_workbook(WORKBOOK,data_only=True)   # NOT read_only: streamed sheets make random .cell() O(sheet) per call (640s pathology) and misread openpyxl-saved files
        rw=wb['Press Release - Raw']; pn=wb['Press Release - Normalized']
        rrow={rw.cell(r,1).value:r for r in range(2,535) if rw.cell(r,1).value}
        COLS=list(range(5,24))
        ALL_COLS=COLS+[24]   # X = General Credit Union; audited below, never invented into a domain
        headers={c:rw.cell(1,c).value for c in ALL_COLS}
        raw_all={c:{m:(rw.cell(rrow[m],c).value or 0.0) for m in rrow} for c in ALL_COLS}
        norm={c:MR.normalize_signed_extrema(raw_all[c]) for c in COLS}
        _c['press_general_exclusions']=MR.general_exclusion_ledger(raw_all[24])
        _c['pressM']=(norm,{c:(pn.cell(535,c).value or 0.0) for c in COLS},
                      {c:rw.cell(1,c).value for c in COLS})
        wb.close()
    return _c['pressM']
def press_general_exclusions():
    """Per-member ledger of General-CU media retained for audit but excluded from policy scoring."""
    press_matrix()
    return _c.get('press_general_exclusions',{})
def pillar_scores():
    """The Python rank authority (ranks_python.json, written by compute_pillars --write in the
    pipeline). Loud failure if missing — engines must not run on a stale/absent authority."""
    if 'pillars' not in _c:
        f=p('ranks_python.json')
        if not os.path.exists(f):
            raise FileNotFoundError('ranks_python.json missing — run `python fec/compute_pillars.py --write` '
                                    '(or the full pipeline); the workbook is a VIEW, not the score source.')
        _c['pillars']=json.load(open(f))
    return _c['pillars']
def scores(): return pillar_scores()['score']
def ranks():  return pillar_scores()['rank']
def dump_atomic(obj,path,**kw):
    """S2-03 (audit 2026-07-02): write JSON to a temp sibling then os.replace() — atomic on NTFS, so a
    crash/kill mid-write (Excel force-kill, OneDrive contention) can never leave a truncated artifact.
    Drop-in for json.dump(obj, open(path,'w'), **kw)."""
    import json as _j,tempfile as _t
    d=os.path.dirname(path) or '.'
    fd,tmp=_t.mkstemp(dir=d,suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as fh: _j.dump(obj,fh,**kw)
        os.replace(tmp,path)
    except BaseException:
        try: os.remove(tmp)
        except OSError: pass
        raise
def write_text_atomic(text,path,encoding='utf-8'):
    """Atomically replace a generated text/HTML artifact."""
    import tempfile as _t
    d=os.path.dirname(path) or '.'
    fd,tmp=_t.mkstemp(dir=d,suffix='.tmp')
    try:
        with os.fdopen(fd,'w',encoding=encoding,newline='') as fh: fh.write(text)
        os.replace(tmp,path)
    except BaseException:
        try: os.remove(tmp)
        except OSError: pass
        raise
def json_for_script(obj,**kw):
    """Serialize JSON for an inline ``<script>`` without permitting an HTML end tag.

    JSON's Unicode escapes decode to the original values in JavaScript/JSON.parse, while escaping
    ``<`` prevents user/source text such as ``</script>`` from terminating the data element early.
    U+2028/U+2029 are escaped for older JavaScript parsers as well.
    """
    raw=json.dumps(obj,**kw)
    return (raw.replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
               .replace('\u2028','\\u2028').replace('\u2029','\\u2029'))
def save_workbook_atomic(workbook,path):
    """Save an openpyxl workbook to a verified sibling ZIP, then replace."""
    import tempfile as _t,zipfile as _z
    d=os.path.dirname(path) or '.'
    fd,tmp=_t.mkstemp(dir=d,suffix='.xlsx.tmp'); os.close(fd)
    try:
        workbook.save(tmp)
        with _z.ZipFile(tmp,'r') as archive:
            bad=archive.testzip()
            if bad: raise IOError('workbook ZIP verification failed at '+bad)
        os.replace(tmp,path)
    except BaseException:
        try: os.remove(tmp)
        except OSError: pass
        raise
def select_network_file(files):
    """Select the newest augmented network, falling back to a base network only if needed."""
    files=[str(f) for f in files]
    if not files: raise FileNotFoundError('no congress_cosponsor_network_*.xlsx files found')
    augmented=[f for f in files if 'AUG' in os.path.basename(f).upper()]
    return max(augmented or files,key=os.path.getmtime)
def load_network():
    """Newest augmented congress_cosponsor network (base only when no AUG exists),
    mean-symmetrized (D2: 41 reverse-dup asymmetric pairs), name-keyed adjacency dict."""
    if 'adj' not in _c:
        import openpyxl
        net=select_network_file(glob.glob(p('congress_cosponsor_network_*.xlsx')))
        ne=openpyxl.load_workbook(net,data_only=True)['Edges']
        b2n=bio2name(); mem=set(congestion()); adj=collections.defaultdict(dict)
        for r in range(2,ne.max_row+1):
            a,b,w=ne.cell(r,1).value,ne.cell(r,2).value,ne.cell(r,3).value
            a=b2n.get(a); b=b2n.get(b)
            if a in mem and b in mem and a!=b and isinstance(w,(int,float)):
                w=(adj[a][b]+w)/2 if b in adj[a] else w
                adj[a][b]=w; adj[b][a]=w
        for m in mem: adj.setdefault(m,{})   # contract: EVERY member has an entry (isolated -> {});
                                             # the old per-file defaultdicts behaved this way implicitly
        _c['adj']=dict(adj); _c['netfile']=os.path.basename(net)
    return _c['adj']
def cpf_diffusion(n,u):
    prt=party(); bf=bpf()
    return 0.4+0.6*math.sqrt(bf.get(n,0.24)*bf.get(u,0.24)) if (prt.get(n)!=prt.get(u) and prt.get(n) in 'DR' and prt.get(u) in 'DR') else 1.0
def cpf_pressure(n,u):
    prt=party()
    return 0.5 if (prt.get(n)!=prt.get(u) and prt.get(n) in 'DR' and prt.get(u) in 'DR') else (1.7 if (prt.get(n)==prt.get(u) and prt.get(n) in 'DR') else 1.0)
def sm64(x):
    """splitmix64 -> [0,1): deterministic per-key draw, independent of evaluation order (TRUE CRN)."""
    x=(x+0x9E3779B97F4A7C15)&0xFFFFFFFFFFFFFFFF
    x=((x^(x>>30))*0xBF58476D1CE4E5B9)&0xFFFFFFFFFFFFFFFF
    x=((x^(x>>27))*0x94D049BB133111EB)&0xFFFFFFFFFFFFFFFF
    return ((x^(x>>31))&0xFFFFFFFFFFFFFFFF)/0x10000000000000000
def build_P(adj=None,physics=cpf_diffusion,edge_mult=True):
    """Cascade kernel p = w*cpf*sigma_v / (w*cpf*sigma_v + 6); sigma_v = receiver susceptibility."""
    adj=adj if adj is not None else load_network()
    em=(lambda v: rc(v,'edge_mult')) if edge_mult else (lambda v:1.0)
    return {u:{v:(w*physics(u,v)*em(v))/(w*physics(u,v)*em(v)+6.0) for v,w in nb.items()} for u,nb in adj.items()}
# ---- calibrated constant tables (single copies; env dials preserved) ----
PERS_NONE=float(os.environ.get('PERS_NONE','0.45'))   # USER-RATIFIED 2026-07-02: Ally parity — silence never outranks a declared Ally
PERS={'Champion':0.10,'Defender':0.12,'Ally':0.40,'Highly Persuadable':0.65,
      'Persuadable':0.60,'Lean Persuadable':0.55,'True Neutral':0.50,
      'Lean Skeptic':0.40,'Neutral':0.50,'Skeptic':0.25,'Highly Skeptical':0.15,
      'Opponent':0.08,'—':PERS_NONE}
IMP={'Examination & Supervision':0.75,'CU Capital Requirements':0.25,'NCUA Budget & Insurance':1.0,'Interchange':2.0,
 'Payments':0.75,'Technology & Emerging':0.75,'Fraud Prevention':0.75,'Data Privacy & Cyber':1.0,'Charter Modernization':1.0,
 'Defense CU Issues':0.2,'Field of Membership':1.0,'CDFI Fund':0.1,'CFPB':1.0,'Credit Card Mandates':3.0,'TCPA':0.2,
 'Member Business Lending':0.3,'Mortgage & Housing':0.4,'CU Tax Status':3.0}   # ABB26 handout anchoring — 18 categories
blocks=[3,11,19,27,35,43,51,59,67,75,83,91,99,145,115,107,123,131]
BLOCKCAT={3:'Examination & Supervision',11:'CU Capital Requirements',19:'NCUA Budget & Insurance',27:'Interchange',
 35:'Payments',43:'Technology & Emerging',51:'Fraud Prevention',59:'Data Privacy & Cyber',67:'Charter Modernization',
 75:'Defense CU Issues',83:'Field of Membership',91:'CDFI Fund',99:'CFPB',145:'CFPB',115:'TCPA',
 107:'Credit Card Mandates',123:'Member Business Lending',131:'Mortgage & Housing'}
CATBLOCKS={sc:[b for b in blocks if BLOCKCAT[b]==BLOCKCAT[sc]] for sc in blocks}   # M3/H2: CFPB 99+145 fold
SGATE={'Highly Persuadable':1.00,'Persuadable':0.96,'Lean Persuadable':0.93,
       'True Neutral':0.90,'Neutral':0.90,'—':0.85,'Lean Skeptic':0.75,
       'Skeptic':0.55,'Highly Skeptical':0.45,'Opponent':0.35,
       'Ally':1.0,'Champion':1.0,'Defender':1.0}
def gate(n,cs): return max(0.15,rc(n,'seed_prob',1.0)*SGATE.get(cs.get(n,'—'),0.85))
TORD={'Champion':4,'Defender':4,'Ally':3,'Highly Persuadable':2,'Persuadable':1,
      'Lean Persuadable':0.5,'True Neutral':0,'Neutral':0,'Lean Skeptic':-0.5,
      'Skeptic':-1,'Highly Skeptical':-2,'Opponent':-4}
# User-directed 2026-07-15: populate the overall Opponent rung modestly. The prior -2.50
# cutoff sat below the observed roster minimum and produced zero Opponents; -1.60 creates
# the first committed Opponent while retaining a distinct Highly Skeptical band. Higher
# values create more Opponents. Revert: OVERALL_OPPONENT_CUTOFF=-2.50.
OVERALL_OPPONENT_CUTOFF=float(os.environ.get('OVERALL_OPPONENT_CUTOFF','-1.20'))   # Paul 2026-07-15: raised -1.60 -> -1.20 (the CFPB re-correction shifted scores up and emptied the rung at -1.60)
OVERALL_BANDS=((2.85,'Champion'),(2.25,'Ally'),(1.50,'Highly Persuadable'),
               (0.75,'Persuadable'),(0.25,'Lean Persuadable'),(-0.25,'True Neutral'),
               (-0.75,'Lean Skeptic'),(-1.50,'Skeptic'),(OVERALL_OPPONENT_CUTOFF,'Highly Skeptical'))
def overall_thresholds():
    return {'scale':'fixed-ten-tier-overall-v2','bands':[{'minimum':cut,'tier':tier} for cut,tier in OVERALL_BANDS],
            'below_last':'Opponent','missing':'—','normalization':'fixed-not-roster-percentile'}
def overall_rounding(cm):
    """Bounded +/-0.05 nudge from exceptional cross-domain performance."""
    earned=[t for t in cm.values() if t in TORD]
    if not earned: return 0.0
    balance=sum(t in ('Champion','Defender') for t in earned)-sum(t=='Opponent' for t in earned)
    return max(-0.05,min(0.05,0.10*balance/len(earned)))
def overall_tier(cm,member=None,overall_capped=None):
    """IMP-weighted mean of TORD tier scores -> the 10-rung overall ladder ('—' excluded: silence
    doesn't dilute earned tiers). SINGLE COPY (S2-04 fix, audit run-2): sync_stance_g writes col G
    with this law, and per_category_stance's in-run gen iteration derives the SAME law — so col G
    is a pure OUTPUT/view, never a cross-run input."""
    sw=si=0.0
    for c,t in cm.items():
        if t in TORD: w=IMP.get(c,0.5); sw+=TORD[t]*w; si+=w
    if si==0: return '—'
    x=sw/si+overall_rounding(cm)
    tier=next((label for cut,label in OVERALL_BANDS if x>=cut),'Opponent')
    # The producer records its evidence-denominator decision in category_stance.json. Consumers pass
    # that block explicitly, so no hidden read of a stale artifact can influence this shared function.
    if tier=='Champion' and member and member in (overall_capped or {}):
        return (overall_capped[member] or {}).get('final','Ally')
    return tier

# ---- SAY-DO gate + delivery discount (user-ratified 2026-07-07, boss review: "Hill says a lot,
# doesn't follow through") — SINGLE COPY, applied where category_stance.json is WRITTEN so every
# consumer (engines, desk, dashboard, col G, audit) inherits it identically. Cheap-talk vs costly
# signals: the top stance rungs (Champion/Defender) must be backed by a COSTLY, RECORDED action.
# A cell keeps its top tier if either recorded-action path holds; else it displays Ally (raw preserved
# in the gate block). Committee office is deliberately NOT a say-do action: it is already represented
# in the Influence pillar and cannot substitute for authored legislation or a recorded vote.
#   A  Authored     — sponsored/original-cosponsored an in-category bill (offense: you write reform).
#   V  Voted line   — a recorded final-passage CU-aligned vote in the category (vote_category_lean).
# Rule C (badge, never a cap): 'proven' = an AUTHORED bill in the category that advanced past
# introduction. A second aggregate guard requires A/V evidence in at least two-thirds of the raw
# top-tier cells supporting an overall Champion label. A fixed high-volume follow-through check also
# caps prolific direct sponsors (10+ CU bills) when no more than 20% advanced, except where exceptional
# direct authorship (20+ tracked bills) corroborates every top-tier domain. This preserves the say-do
# safeguard without penalizing an unusually substantial sponsored-but-incomplete record. The thresholds
# are roster-independent; ranks are unaffected (stances never feed the pillars).
_ADV_ACTIONS={'Passed House','Passed Senate','Agreed to in Senate','Resolving Differences','Became Law',
              'Failed to pass over veto'}
# label->canonical map + curated non-CU drop list: kept in lockstep with make_member_desk's copies
# (the desk parses the same role sheets for display; consolidate to this import at next touch).
_LBL2CAT=dict(BR.LABEL_TO_CANONICAL)
_DROP_BILLS=BR.EXCLUDED_TITLE_PHRASES
_CORR=None
def bill_corroboration():
    """{member: {'sponsored': set(canonical cats), 'advanced': set(...)}} from the workbook role
    sheets ('Sponsor Interactions' + 'Original Co-Sponsor Interaction'; plain cosponsorship does NOT
    corroborate under Rule A). Lazy + cached; NFC-casefold name match against the roster."""
    global _CORR
    if _CORR is not None: return _CORR
    import openpyxl,unicodedata
    nrm=lambda s:unicodedata.normalize('NFC',str(s or '')).strip().lower()
    roster={nrm(m):m for m in congestion()}
    out=collections.defaultdict(lambda:{'sponsored':set(),'advanced':set(),
                                        'direct_sponsored_bills':set(),'advanced_direct_bills':set()})
    try:
        wb=openpyxl.load_workbook(WORKBOOK,read_only=True,data_only=True)
        missing=[s for s in ('Sponsor Interactions','Original Co-Sponsor Interaction') if s not in wb.sheetnames]
        if missing: raise KeyError('missing required bill sheets: %s'%missing)
        overrides=BR.load_overrides(p('bill_overrides.csv'))
        for sheet in ('Sponsor Interactions','Original Co-Sponsor Interaction'):
            for r in wb[sheet].iter_rows(min_row=2,values_only=True):
                m=roster.get(nrm(r[2]))
                if not m: continue
                if BR.excluded_bill(r[3],r[9],r[4],r[12]): continue
                cat=_LBL2CAT.get(r[0],r[0]) if r[0] else ''
                ov=BR.override_for(overrides,r[3],r[9])
                if ov and not BR.override_included(ov): continue
                if ov and ov.get('Category'): cat=BR.canonical_category(ov['Category']) or cat
                if not cat: continue
                out[m]['sponsored'].add(cat)
                if str(r[8] or '') in _ADV_ACTIONS: out[m]['advanced'].add(cat)
                if sheet=='Sponsor Interactions':
                    key=(str(r[3] or ''),str(r[9] or ''))
                    out[m]['direct_sponsored_bills'].add(key)
                    if str(r[8] or '') in _ADV_ACTIONS: out[m]['advanced_direct_bills'].add(key)
        wb.close()
        manual=p('manual_bill_evidence.csv')
        if os.path.exists(manual):
            for r in csv.DictReader(open(manual,encoding='utf-8-sig')):
                role=str(r.get('Role') or '').lower()
                if 'sponsor' not in role: continue
                m=roster.get(nrm(r.get('Member')))
                if not m or BR.excluded_bill(r.get('Bill'),r.get('Congress'),r.get('Title'),r.get('Summary')): continue
                cat=BR.canonical_category(r.get('Category'))
                if not cat: continue
                out[m]['sponsored'].add(cat)
                if str(r.get('LastAction') or '') in _ADV_ACTIONS: out[m]['advanced'].add(cat)
                if role.strip()=='sponsor':
                    key=(str(r.get('Bill') or ''),str(r.get('Congress') or ''))
                    out[m]['direct_sponsored_bills'].add(key)
                    if str(r.get('LastAction') or '') in _ADV_ACTIONS: out[m]['advanced_direct_bills'].add(key)
    except (OSError,KeyError,ValueError,IndexError) as e:
        raise RuntimeError('required bill corroboration source is invalid; refusing to disable the say-do gate') from e
    _CORR=dict(out); return _CORR
_VOTECORR=None
def vote_corroboration():
    """{name: set(cats with a recorded net-CU-aligned final-passage vote, lean>=0.5, n>=1)} from
    vote_category_lean.json (Path V — a floor vote is on the record, more than talk). Lazy+cached;
    missing file -> {} (Path V simply contributes nothing; never fail-caps)."""
    global _VOTECORR
    if _VOTECORR is not None: return _VOTECORR
    try:
        with open(p('vote_category_lean.json'),encoding='utf-8') as handle:
            VL=json.load(handle)
        nof=VL['name_of']
        out=collections.defaultdict(set)
        for bio,cats in VL['votes'].items():
            nm=nof.get(bio)
            if not nm: continue
            for c,d in cats.items():
                if (d.get('lean',0) or 0)>=0.5 and (d.get('n',0) or 0)>=1: out[nm].add(c)
        _VOTECORR=dict(out)
    except FileNotFoundError:
        _VOTECORR={}
    except Exception as exc:
        raise RuntimeError(
            'vote_category_lean.json is present but invalid; refusing to treat malformed vote evidence as absent'
        ) from exc
    return _VOTECORR
def cap_uncorroborated(member,cm):
    """Say-do gate on one member's category map (paths A/V — see header). Returns (gated_cm,
    capped{cat:raw_tier}, proven[cats], corrob{cat:'A'|'V'}). Only ever LOWERS Champion/Defender
    to Ally; all other tiers pass through untouched."""
    corr=bill_corroboration()
    cm2=dict(cm); capped={}; proven=[]; corrob={}
    if not corr: return cm2,capped,proven,corrob   # authorship source missing -> fail-open (no caps)
    spon=corr.get(member,{}).get('sponsored',set()); adv=corr.get(member,{}).get('advanced',set())
    vcats=vote_corroboration().get(member,set())
    for c,t in cm.items():
        if t in ('Champion','Defender'):
            if c in spon:
                corrob[c]='A'
                if c in adv: proven.append(c)
            elif c in vcats: corrob[c]='V'
            else: capped[c]=t; cm2[c]='Ally'
    return cm2,capped,sorted(proven),corrob

SAY_DO_OVERALL_RATIO=2.0/3.0
SAY_DO_MIN_TOP_CELLS=6
SAY_DO_DIRECT_VOLUME_MIN=10
SAY_DO_MAX_ADVANCEMENT_RATE=0.20
SAY_DO_EXCEPTIONAL_AUTHORSHIP_MIN=20
def overall_say_do_gate(member,gated_cm,raw_cm,corroborated):
    """Return (final overall tier, audit detail) for the aggregate say-do rule.

    The denominator is the member's raw Champion/Defender cells, before the cell-level A/V caps.
    The numerator is the subset with authored/original-cosponsored legislation or an aligned recorded
    vote. A separate fixed-volume check catches a large introduced-only direct-sponsorship trail. The
    bill source is the availability sentinel: if it cannot be loaded, the rule fails open instead of
    penalizing an entire roster for a missing input.
    """
    raw=overall_tier(gated_cm)
    top=sorted(c for c,t in raw_cm.items() if t in ('Champion','Defender'))
    corr=bill_corroboration(); member_corr=corr.get(member,{}) or {}
    delivered=sorted(c for c in top if corroborated.get(c) in ('A','V'))
    available=bool(corr)
    ratio=(len(delivered)/len(top)) if top else 1.0
    direct=len(member_corr.get('direct_sponsored_bills',set()))
    advanced_direct=len(member_corr.get('advanced_direct_bills',set()))
    advancement_rate=(advanced_direct/direct) if direct else None
    exceptional_authorship=bool(direct>=SAY_DO_EXCEPTIONAL_AUTHORSHIP_MIN and top and
                                len(delivered)==len(top))
    thin_high_volume=bool(direct>=SAY_DO_DIRECT_VOLUME_MIN and advancement_rate is not None and
                          advancement_rate<=SAY_DO_MAX_ADVANCEMENT_RATE+1e-12 and
                          not exceptional_authorship)
    low_coverage=bool(top and ratio+1e-12<SAY_DO_OVERALL_RATIO)
    insufficient_breadth=len(top)<SAY_DO_MIN_TOP_CELLS
    capped=bool(available and raw=='Champion' and (insufficient_breadth or low_coverage or thin_high_volume))
    final='Ally' if capped else raw
    return final,{'raw':raw,'final':final,'top_cells':top,'delivered_cells':delivered,
                  'delivery_ratio':round(ratio,6),'threshold':round(SAY_DO_OVERALL_RATIO,6),
                  'direct_sponsored_bills':direct,'advanced_direct_bills':advanced_direct,
                  'direct_advancement_rate':(round(advancement_rate,6) if advancement_rate is not None else None),
                  'minimum_top_tier_cells':SAY_DO_MIN_TOP_CELLS,
                  'high_volume_minimum':SAY_DO_DIRECT_VOLUME_MIN,
                  'high_volume_max_advancement_rate':SAY_DO_MAX_ADVANCEMENT_RATE,
                  'exceptional_authorship_minimum':SAY_DO_EXCEPTIONAL_AUTHORSHIP_MIN,
                  'exceptional_authorship_override':exceptional_authorship,
                  'cap_reasons':([r for r,flag in (('insufficient_top_tier_breadth',insufficient_breadth),
                                                   ('top_tier_action_coverage',low_coverage),
                                                   ('high_volume_low_followthrough',thin_high_volume)) if flag]),
                  'evidence_available':available}
_DELIV=None
def delivery_mult(m):
    """Say-do talker discount on engine TARGET VALUE (never on rank): clip(1-0.15*max(0,gap-1),
    0.70,1.00). gap from say_do_gap.json (weekly diagnostic); missing artifact or member -> neutral
    1.0 (the receptivity layer's fallback pattern)."""
    global _DELIV
    if _DELIV is None:
        try:
            with open(p('say_do_gap.json'),encoding='utf-8') as handle:
                g=json.load(handle)['members']
            _DELIV={n:(v.get('gap') or 0.0) for n,v in g.items()}   # raw gaps; clip computed per call (testable)
        except FileNotFoundError:
            _DELIV={}
        except Exception as exc:
            raise RuntimeError(
                'say_do_gap.json is present but invalid; refusing to treat malformed delivery evidence as neutral'
            ) from exc
    return max(0.70,min(1.00,1-0.15*max(0.0,_DELIV.get(m,0.0)-1.0)))

# Nickname equivalence classes (QA3 2026-07-04, Bernie/Bernard-class resolver misses) — SINGLE COPY.
# fetch_interviews.py carries the original inline; consolidate it to this import at next touch.
NICK_SETS=[{'bernard','bernie'},{'charles','chuck','charlie'},{'christopher','chris'},{'richard','dick','rich','rick'},
 {'michael','mike'},{'james','jim','jimmy'},{'robert','bob','rob','bobby'},{'thomas','tom','tommy'},{'daniel','dan','danny'},
 {'joseph','joe','joey'},{'timothy','tim'},{'patrick','pat'},{'william','bill','will','billy'},{'edward','ed','ted','eddie'},
 {'theodore','ted'},{'elizabeth','liz','beth','betty'},{'katherine','kathryn','katie','kate','kathy'},{'margaret','maggie','meg'},
 {'benjamin','ben'},{'alexander','alex'},{'anthony','tony'},{'andrew','andy','drew'},{'matthew','matt'},{'jonathan','jon'},
 {'nicholas','nick'},{'gregory','greg'},{'lawrence','larry'},{'gerald','jerry'},{'ronald','ron','ronny'},{'donald','don'},
 {'kenneth','ken'},{'stephen','steven','steve'},{'david','dave'},{'samuel','sam'},{'frederick','fred'},{'susan','sue','suzy'},
 {'deborah','debbie','deb'},{'cynthia','cindy'},{'jacquelyn','jacqueline','jackie'},{'raphael','rafael','raffi'},
 {'joshua','josh'},{'zachary','zach','zack'},{'abigail','abby'},{'rebecca','becca','becky'},{'jefferson','jeff'},
 {'jeffrey','jeff'},{'mitchell','mitch'},{'randall','randy'},{'terrence','terri','terry'},{'vincent','vince'}]
_NICK={}
for _ns in NICK_SETS:
    for _a in _ns: _NICK.setdefault(_a,set()).update(_ns)
def name_variants(first):
    """All nickname-equivalent first names for `first` (incl. itself)."""
    return _NICK.get(first,set())|{first}
