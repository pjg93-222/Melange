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
def load_network():
    """Newest congress_cosponsor_network_*.xlsx by mtime (AUG picked up automatically),
    mean-symmetrized (D2: 41 reverse-dup asymmetric pairs), name-keyed adjacency dict."""
    if 'adj' not in _c:
        import openpyxl
        net=max(glob.glob(p('congress_cosponsor_network_*.xlsx')),key=os.path.getmtime)
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
PERS={'Champion':0.10,'Defender':0.12,'Ally':0.40,'Highly Persuadable':0.55,'True Neutral':0.50,
      'Lean Skeptic':0.40,'Neutral':0.50,'Skeptic':0.25,'Opponent':0.08,'—':PERS_NONE}
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
SGATE={'Highly Persuadable':1.00,'True Neutral':0.90,'Neutral':0.90,'—':0.85,'Lean Skeptic':0.75,
       'Skeptic':0.55,'Opponent':0.35,'Ally':1.0,'Champion':1.0,'Defender':1.0}
def gate(n,cs): return max(0.15,rc(n,'seed_prob',1.0)*SGATE.get(cs.get(n,'—'),0.85))
