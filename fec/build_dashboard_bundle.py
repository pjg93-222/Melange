import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
from moneyball_core import dump_atomic   # S2-03: crash-safe artifact write
import json, sys, glob, os, csv, openpyxl, networkx as nx, math, random, re, unicodedata, zlib
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
C=json.load(open(MB_ROOT+r'\congestion.json'))
cong={m['member']:m for m in C}
CS=json.load(open(MB_ROOT+r'\category_stance.json'))['matrix']
FL=json.load(open(MB_ROOT+r'\per_topic_alloc.json'))
CO=json.load(open(MB_ROOT+r'\per_topic_coalition.json'))
issues=list(FL.keys())            # 18 labels, blocks order
# label -> matrix category (CFPB Restrain/Reach share combined CFPB stance)
LBLCAT={'Examination & Supervision':'Examination & Supervision','Credit Union Capital Requirements':'CU Capital Requirements',
'NCUA Budget & Share Insurance Fund':'NCUA Budget & Insurance','Interchange':'Interchange','Payments':'Payments',
'Technology & Emerging Issues':'Technology & Emerging','Fraud Prevention':'Fraud Prevention',
'Data Privacy & Cybersecurity':'Data Privacy & Cyber','Charter Modernization & Governance':'Charter Modernization',
'Defense Credit Union Issues':'Defense CU Issues','Field of Membership':'Field of Membership','CDFI Fund':'CDFI Fund',
'CFPB Restrain':'CFPB','CFPB Reach (-)':'CFPB','Telephone Consumer Protection Act Issues':'TCPA',
'Credit Card & Consumer-Fee Mandates':'Credit Card Mandates','Member Business Lending':'Member Business Lending',
'Mortgage Lending & Housing':'Mortgage & Housing'}
issue_cat=[LBLCAT.get(lb,lb) for lb in issues]
wb=openpyxl.load_workbook(MB_ROOT+r'\Moneyball Main Version - Blended.xlsx',data_only=True)
ra=wb['Rank & Allocation']
# authoritative rank = Blended Model col20 (was erroneously reading Rank & Allocation col2 = District/State)
bm=wb['Blended Model']
from moneyball_core import ranks as _pyranks
rank=_pyranks()   # PHASE-2: Python rank authority
# committee memberships (base committee per member, subcommittees folded into parent) from the Committee Data
# sheet -> drives the committee-cluster layout (Porter et al. bipartite member-committee structure).
def _nfc(s): return unicodedata.normalize('NFC',str(s)) if s else s
cd=wb['Committee Data']; MEM_COMM={}
for r in range(2,cd.max_row+1):
    nm=cd.cell(r,1).value; seats=str(cd.cell(r,5).value or '')
    if not nm or not seats.strip(): continue
    bases=set()
    for part in seats.split('|'):
        mm=re.match(r'^(.*?)\s*\[',part.strip())
        if mm:
            base=re.split(r' - | \(full\)',mm.group(1).strip())[0].strip()
            if base: bases.add(base)
    if bases: MEM_COMM[_nfc(nm)]=bases
# Overall stance = IMPORTANCE-WEIGHTED aggregate of the per-category tiers (category_stance matrix). The
# per-category classifier is self-calibrated; we weight each area by its CU stakes (Credit Card Mandates x3,
# Interchange x2, CFPB x1, rest 0.2-0.75) so a member who is anti-CU on the defensive flagship issues (e.g.
# Marshall on the Credit Card Competition Act) reads Opponent, not diluted to mild-skeptic. Bucketed into a
# symmetric 10-tier ladder: Champion > Ally > Highly/Persuadable/Lean Persuadable > True Neutral >
# Lean Skeptic/Skeptic/Highly Skeptical > Opponent. (Replaces the coarse press/leg formula; ranks unaffected.)
_TORD={'Champion':4,'Defender':4,'Ally':2,'Highly Persuadable':1,'True Neutral':0,'Neutral':0,
       'Lean Skeptic':-1,'Skeptic':-2,'Opponent':-4}
from moneyball_core import IMP as _IMP
def _agg_stance(n):
    cm=CS.get(n,{}); sw=si=0.0
    for c,t in cm.items():
        if t in _TORD: w=_IMP.get(c,0.5); sw+=_TORD[t]*w; si+=w
    if si==0: return 'Neutral'
    x=sw/si
    # Defender = holds the line on a flagship defensive fight (Champion/Defender on Interchange or Credit Card
    # Mandates) without being a broad across-the-board Champion -> carved from the Ally band, ranks just below
    # Champion (matches the per-category Defender tier, which only appears on the two defensive flagships).
    defends=any(cm.get(c) in ('Champion','Defender') for c in ('Interchange','Credit Card Mandates'))
    if x>=2.5: return 'Champion'
    if x>=1.75: return 'Defender' if defends else 'Ally'
    return ('Highly Persuadable' if x>=1.25 else
            'Persuadable' if x>=0.75 else 'Lean Persuadable' if x>=0.25 else 'True Neutral' if x>=-0.25 else
            'Lean Skeptic' if x>=-0.75 else 'Skeptic' if x>=-1.25 else 'Highly Skeptical' if x>=-1.9 else 'Opponent')
gen={ra.cell(r,1).value:_agg_stance(ra.cell(r,1).value) for r in range(3,536) if ra.cell(r,1).value}
members=[m['member'] for m in C]; idx={n:i for i,n in enumerate(members)}
# party from voteview members (party_code 100=D,200=R,else I); prefer most recent congress
party={}
for congN in (119,118,117):
    p=MB_ROOT+r'\votes\HS%d_members.csv'%congN
    if os.path.exists(p):
        with open(p,encoding='utf-8') as fh:
            for row in csv.DictReader(fh):
                b=row.get('bioguide_id'); pc=str(row.get('party_code'))
                if b and b not in party: party[b]={'100':'D','200':'R'}.get(pc,'I')
bio2name={cong[n]['bioguide']:n for n in members if cong[n].get('bioguide')}
# network
net=max(glob.glob(MB_ROOT+r'\congress_cosponsor_network_*.xlsx'),key=os.path.getmtime)
ne=openpyxl.load_workbook(net,data_only=True)['Edges']
G=nx.Graph(); G.add_nodes_from(members); ew={}
for r in range(2,ne.max_row+1):
    a,b,w=ne.cell(r,1).value,ne.cell(r,2).value,ne.cell(r,3).value
    a=bio2name.get(a); b=bio2name.get(b)
    if a in idx and b in idx and a!=b and isinstance(w,(int,float)):
        G.add_edge(a,b,weight=w); ew[(a,b)]=ew.get((a,b),0)+w
print('graph: %d nodes %d edges; laying out...'%(G.number_of_nodes(),G.number_of_edges()))
pos=nx.spring_layout(G,weight='weight',k=0.45,iterations=60,seed=7)
xs=[p[0] for p in pos.values()]; ys=[p[1] for p in pos.values()]
x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys)
def sx(v):return round(40+920*(v-x0)/(x1-x0))
def sy(v):return round(40+920*(v-y0)/(y1-y0))
TC={'Champion':'C','Defender':'F','Ally':'A','Highly Persuadable':'H','Persuadable':'P','Lean Persuadable':'G','True Neutral':'T','Lean Skeptic':'L','Neutral':'N','Skeptic':'S','Highly Skeptical':'K','Opponent':'O','—':'-'}
# bipartisanship = weighted fraction of COSPONSORSHIP ties crossing party, shrunk toward the global
# rate (low-degree members aren't 0/100).
# S2-01 fix (audit 2026-07-02): the display graph G above deliberately uses the AUG network (the live
# cascade reality incl. social/press layers), but BP is DEFINED on cosponsorship — cross-party reposts
# are not cosponsorship, and letting them in both redefined bipartisanship unratified AND fed back into
# cpf_diffusion/tgt/coalition boosts via bipartisan.json. BP therefore uses the newest NON-AUG file.
# BP_SRC=aug restores the augmented definition if the user ever ratifies it.
if os.environ.get('BP_SRC','cosponsor')=='cosponsor':
    _n0=max([q for q in glob.glob(MB_ROOT+r'\congress_cosponsor_network_*.xlsx') if 'AUG' not in os.path.basename(q)],key=os.path.getmtime)
    _e0=openpyxl.load_workbook(_n0,data_only=True)['Edges']
    G0=nx.Graph(); G0.add_nodes_from(members)
    for r in range(2,_e0.max_row+1):
        a,b,w=_e0.cell(r,1).value,_e0.cell(r,2).value,_e0.cell(r,3).value
        a=bio2name.get(a); b=bio2name.get(b)
        if a in idx and b in idx and a!=b and isinstance(w,(int,float)):
            w=(G0[a][b]['weight']+w)/2 if G0.has_edge(a,b) else w   # D2 mean-symmetrize
            G0.add_edge(a,b,weight=w)
else: G0=G
raw={}; gs=gc=0.0
for n in members:
    pn=party.get(cong[n].get('bioguide',''),'?'); same=cross=0.0
    for nb in G0.neighbors(n):
        pnb=party.get(cong[nb].get('bioguide',''),'?')
        if pn in ('D','R') and pnb in ('D','R'):
            w=G0[n][nb].get('weight',1.0)
            if pnb==pn: same+=w
            else: cross+=w
    raw[n]=(same,cross); gs+=same; gc+=cross
prior=gc/(gs+gc) if (gs+gc)>0 else 0.12; ALPHA=6.0
bp={n:(raw[n][1]+ALPHA*prior)/(raw[n][0]+raw[n][1]+ALPHA) for n in members}
cfp=MB_ROOT+r'\confidence.json'; CONF=json.load(open(cfp)) if os.path.exists(cfp) else {}
# receptivity color layer (2026-07-04): pressure_mult per member (behavioral basis) for colorBy=recept
_rcp=MB_ROOT+r'\member_receptivity.json'
_RC=(json.load(open(_rcp)).get('members',{}) if os.path.exists(_rcp) else {})
name=[];X=[];Y=[];PARTY=[];GEN=[];RANK=[];NL=[];STANCE=[];BP=[];CF=[]   # columnar to drop repeated JSON keys
for n in members:
    sm=''.join(TC.get(CS.get(n,{}).get(issue_cat[i],'—'),'-') for i in range(len(issues)))
    c=cong[n]
    name.append(n);X.append(sx(pos[n][0]));Y.append(sy(pos[n][1]))
    PARTY.append(party.get(c.get('bioguide',''),'?'));GEN.append(TC.get(gen.get(n,'Neutral'),'N'))
    RANK.append(rank.get(n,0) or 0);NL.append(round((c.get('net_lean') or 0)*10));STANCE.append(sm);BP.append(round(bp[n]*100));CF.append(CONF.get(n,50))
# ---------- COMMITTEE-CLUSTER LAYOUT (Porter et al. 2005): a second set of node positions where members
# cluster by committee. Committees are positioned by NORMALIZED INTERLOCK (shared members / expected-by-chance)
# via a spring layout, then each member sits at the centroid of their committees' anchors (+ deterministic
# jitter); members with no CU-tracked committee ring the periphery. Toggled against the cosponsorship layout.
def mc(n): return MEM_COMM.get(_nfc(n))
comms=sorted({c for s in MEM_COMM.values() for c in s})
NC=len(MEM_COMM); csize={c:sum(1 for s in MEM_COMM.values() if c in s) for c in comms}
CG=nx.Graph(); CG.add_nodes_from(comms)
for ia,a in enumerate(comms):
    for b in comms[ia+1:]:
        shared=sum(1 for s in MEM_COMM.values() if a in s and b in s); exp=csize[a]*csize[b]/NC if NC else 0
        if shared>0 and exp>0: CG.add_edge(a,b,weight=shared/exp)        # normalized interlock
canc=nx.spring_layout(CG,weight='weight',k=0.9,iterations=200,seed=7)
craw={}; ncirc=[n for n in members if not mc(n)]
for k,n in enumerate(ncirc):
    ang=2*math.pi*k/max(1,len(ncirc)); craw[n]=(1.85*math.cos(ang),1.85*math.sin(ang))
for n in members:
    s=mc(n)
    if not s: continue
    ax=sum(canc[c][0] for c in s)/len(s); ay=sum(canc[c][1] for c in s)/len(s)
    rg=random.Random(zlib.crc32(n.encode('utf-8'))); j=0.07   # STABLE per-name seed (Python's hash() is salted per-process -> non-reproducible layout)
    craw[n]=(ax+rg.uniform(-j,j), ay+rg.uniform(-j,j))
cxs=[p[0] for p in craw.values()]; cys=[p[1] for p in craw.values()]
cx0,cx1,cy0,cy1=min(cxs),max(cxs),min(cys),max(cys)
def csx(v):return round(40+920*(v-cx0)/(cx1-cx0))
def csy(v):return round(40+920*(v-cy0)/(cy1-cy0))
CX=[csx(craw[n][0]) for n in members]; CY=[csy(craw[n][1]) for n in members]
COMMS=[[c,csx(canc[c][0]),csy(canc[c][1]),csize[c]] for c in comms]   # committee anchors + sizes for labels
CMI=[ (comms.index(sorted(mc(n))[0]) if mc(n) else -1) for n in members]  # primary committee index per member (tint)
edges=sorted(ew.items(),key=lambda kv:-kv[1])[:420]
E=[[idx[a],idx[b]] for (a,b),w in edges]
# --- layer toggles (user-ratified 2026-07-04): per-drawn-edge provenance code + signed reference layer ---
# Provenance sheet (AUG builder) maps bioguide pairs -> layer; drawn edges get 1 char each:
# c=cosponsor s=social h=hcoi e=engagement m=mixed (missing -> c, the dominant layer).
_prov={}
try:
    _pv=openpyxl.load_workbook(net,data_only=True)['Provenance']
    for r in range(2,_pv.max_row+1):
        a,b,ly=bio2name.get(_pv.cell(r,1).value),bio2name.get(_pv.cell(r,2).value),str(_pv.cell(r,4).value or '')
        if a and b and ly: _prov[frozenset((a,b))]=('m' if '+' in ly else {'cosponsor':'c','social':'s','hcoi':'h','engagement':'e'}.get(ly,'c'))
except KeyError: pass   # non-AUG file without a Provenance sheet -> all edges default to 'c'
ELAY=''.join(_prov.get(frozenset(ab),'c') for ab,w in edges)
# signed cross-media reference layer (member_references.json: CREC/interview/X mentions, Fable-valenced,
# dyad-capped at build time). n_scored>=2 keeps one-off mentions out of the drawing.
REFE=[]
_rfp=MB_ROOT+r'\member_references.json'
if os.path.exists(_rfp):
    for _e in json.load(open(_rfp,encoding='utf-8'))['edges']:
        if _e['a'] in idx and _e['b'] in idx and _e.get('n_scored',0)>=2:
            REFE.append([idx[_e['a']],idx[_e['b']],round(_e.get('net',0),2),_e['n_scored']])
print('layer provenance: %s | reference layer: %d dyads (n_scored>=2)'%(
    {c:ELAY.count(c) for c in 'cshem' if ELAY.count(c)},len(REFE)))
flip=[{str(idx[n]):round(v/1000) for n,v in FL[lb].items() if v>=10000} for lb in issues]
coal=[{str(idx[n]):round(v/1000) for n,v in CO[lb].items() if v>0} for lb in issues]
stats=[]
for i,lb in enumerate(issues):
    col=[STANCE[k][i] for k in range(len(name))]
    stats.append({'champ':col.count('C')+col.count('F'),'ally':col.count('A'),'opp':col.count('O'),'skep':col.count('S'),
                  'flip':sum(FL[lb].values()),'coal':sum(CO[lb].values()),'coalN':len(coal[i])})
B=MB_ROOT
# --- electoral contest/defend plays (per member) ---
EP=json.load(open(B+r'\electoral_plays.json')) if os.path.exists(B+r'\electoral_plays.json') else {}
def _playcode(n):   # c = contest via PRIMARY (same-party), g = contest via GENERAL (cross-party flip), d = defend, n = none
    e=EP.get(n) or {}; pl=e.get('play','none')
    if pl=='contest': return 'g' if e.get('route')=='general' else 'c'
    return {'defend':'d'}.get(pl,'n')
PLAY=''.join(_playcode(n) for n in members)
EPVAL=[round((EP.get(n) or {}).get('value',0)) for n in members]
# --- nested budget frontier per issue (slider does a live lookup of the precomputed path) ---
if not os.path.exists(B+r'\budget_frontier.json'): print('  !! budget_frontier.json MISSING — frontier sliders will be EMPTY (run budget_frontier.py)')   # S3-05: silent-empty sections now announce themselves
BF=json.load(open(B+r'\budget_frontier.json')) if os.path.exists(B+r'\budget_frontier.json') else {'topics':{}}
def frontier_for(lb):
    t=BF['topics'].get(lb)
    if not t: return None
    pts=[[p['b'],p['spread'],(idx.get(p['seed']) if p.get('seed') else -1),(p.get('type','') or '')[:1]] for p in t['path']]
    return {'base':t['base'],'knee':t.get('knee',0),'core':t.get('core_seeds',0),'path':pts}
frontier=[frontier_for(lb) for lb in issues]
# --- adaptive optimizer (cross-topic CU allocation) ---
if not os.path.exists(B+r'\optimize_result.json'): print('  !! optimize_result.json MISSING — optimizer panel will be EMPTY (run optimize.py)')   # S3-05
OPT=json.load(open(B+r'\optimize_result.json')) if os.path.exists(B+r'\optimize_result.json') else None
opt=None
if OPT:
    opt={'budget':OPT['budget'],'base':round(OPT['base'],1),'final':round(OPT['final'],1),
         'alloc':sorted([[idx[n],round(v/1000)] for n,v in OPT['alloc'].items() if n in idx],key=lambda x:-x[1]),
         'conv':[idx[c[0]] for c in OPT['conversions'] if c[0] in idx]}
# ====== LIVE SCENARIO ENGINE DATA (faithful in-browser port of flip_model + competitive cascade + lt_priming) ======
import importlib.util
_es=importlib.util.spec_from_file_location('fmE',MB_ROOT+r'\fec\flip_model.py');fmE=importlib.util.module_from_spec(_es);_es.loader.exec_module(fmE)
ADJ=[[idx[a],idx[b],round(w,3)] for (a,b),w in ew.items() if a in idx and b in idx]   # FULL network (engine cascade uses all edges, not just the top-420 drawn)
ENG=[[round(fmE.eng[fmE.cat2sc[issue_cat[i]]][n],3) for n in members] for i in range(len(issues))]   # legislative engagement per issue x member
engine={'adj':ADJ,
 'cu':[round(fmE.cu0[n]) for n in members],'ind':[round(fmE.ind0[n]) for n in members],
 'rcp':[round(fmE.R[n]) for n in members],'sco':[round(fmE.score.get(n,0),3) for n in members],
 'nlraw':[round(cong[n].get('net_lean') or 0,1) for n in members],'bpf':[round(bp[n],4) for n in members],
 'eng':ENG,
 'const':{'WM':fmE.WM,'WP':fmE.WP,'HALFF':fmE.HALFF,'BASE':fmE.BASE,'smax':round(fmE.smax,4),
          'MAXSHIFT':18,'HALF':0.10,'DTHRESH':11.25,'BSCALE':400000,'SRCPRO':1.7,'SRCANTI':0.5,'DCROSS':0.4,'CEDGE':10000,'RFLOOR':200000,'MC':40,'SEED':7},
 'pers':fmE.PERS,'theta':{'Highly Persuadable':0.6,'True Neutral':1.0,'Neutral':1.0,'Lean Skeptic':1.5,'Skeptic':2.0,'Opponent':3.0,'Ally':0.0},
 'refflip':[round(fmE.flip_value(issue_cat[i],fmE.CS0,fmE.cu0,fmE.ind0),3) for i in range(len(issues))]}   # Python baseline per issue -> in-browser self-check
# ---- Noble & Turner (2024) going-public parameters per issue -> System-shocks exec cue ----
# z = sincere polarization (D-R stance gap on the issue); psi = share w/o an established posture;
# P(rally)=(1-b)(1-z/3), P(retreat)=(1-b)(z/3), b = 0.05+0.10*psi backfire.  Estimation identical to
# fec/salience_shock.py (KEEP IN SYNC).  Feeds the party-asymmetric exec-cue multipliers in the JS.
_TS={'C':3,'F':2.5,'A':2,'H':1,'T':0,'L':-1,'S':-2,'O':-3}
_DEF=set(json.load(open(MB_ROOT+r'\category_stance.json'))['defensive'])
engine['sal']=[]
for i in range(len(issues)):
    sd=[_TS[STANCE[k][i]] for k in range(len(name)) if PARTY[k]=='D' and STANCE[k][i] in _TS]
    sr=[_TS[STANCE[k][i]] for k in range(len(name)) if PARTY[k]=='R' and STANCE[k][i] in _TS]
    _z=abs((sum(sd)/max(1,len(sd)))-(sum(sr)/max(1,len(sr)))); _zn=min(1.0,_z/3.0)
    _psi=1.0-sum(1 for k in range(len(name)) if STANCE[k][i] in _TS)/max(1,len(name))
    _b=min(0.35,0.05+0.10*_psi)
    engine['sal'].append({'z':round(_z,2),'p':round((1-_b)*(1-_zn),3),'q':round((1-_b)*_zn,3),'b':round(_b,3),
                          'def':1 if issue_cat[i] in _DEF else 0})
engine['const']['EXECP']='R'   # executive party for the going-public cue (119th Congress)
# go-public advisory verdicts (salience_shock.py --advise), surfaced in the System-shocks panel
_advmap={}
try:
    _advl=json.load(open(MB_ROOT+r'\salience_advisory.json'))['advisory']
    _cut=sorted((a['value'] for a in _advl),reverse=True)[max(0,len(_advl)//4-1)]
    for a in _advl:
        v='GO PUBLIC' if (a['value']>=_cut and a['value']>0) else 'quiet work'
        if a.get('defections_prevented'): v+=' · holds %d'%len(a['defections_prevented'])
        _advmap[a['issue']]=v
except FileNotFoundError: print('  !! salience_advisory.json MISSING — advisory column will be EMPTY (run salience_shock.py --advise)')   # S3-05: was `except Exception: pass`, which also buried schema drift forever
engine['adv']=[_advmap.get(issue_cat[i],'') for i in range(len(issues))]
# ===== Overall CU stance as a selectable ISSUE layer (general stance, toggleable like Interchange) =====
_ovf={str(k):round(sum(FL[lb].get(name[k],0) for lb in FL)/1000) for k in range(len(name)) if sum(FL[lb].get(name[k],0) for lb in FL)>=10000}
_ovc={str(k):round(sum(CO[lb].get(name[k],0) for lb in CO)/1000) for k in range(len(name)) if sum(CO[lb].get(name[k],0) for lb in CO)>0}
issues.append('Overall CU stance')
for k in range(len(name)): STANCE[k]=STANCE[k]+GEN[k]                                   # this issue's stance = overall (R&A col 7) tier
flip.append(_ovf); coal.append(_ovc); frontier.append(None)                              # no single-topic frontier for the aggregate layer
engine['eng'].append([round(sum(engine['eng'][i][k] for i in range(len(engine['eng'])))/max(1,len(engine['eng'])),3) for k in range(len(name))])  # overall engagement = mean per-issue eng
engine['refflip'].append(0)                                                              # synthetic layer -> engchk self-check skips it
engine['sal'].append({'z':0,'p':0.6,'q':0.3,'b':0.1,'def':0})                            # neutral going-public params for the aggregate layer
stats.append({'champ':GEN.count('C')+GEN.count('F'),'ally':GEN.count('A'),'opp':GEN.count('O'),'skep':GEN.count('S'),'flip':sum(_ovf.values())*1000,'coal':sum(_ovc.values())*1000,'coalN':len(_ovc)})
bundle={'issues':issues,'name':name,'x':X,'y':Y,'party':''.join(PARTY),'gen':''.join(GEN),
        'rank':RANK,'nl':NL,'bp':BP,'cf':CF,'stance':STANCE,'edges':E,'flip':flip,'coal':coal,'stats':stats,
        'play':PLAY,'epval':EPVAL,'frontier':frontier,'opt':opt,'engine':engine,
        'cx':CX,'cy':CY,'comms':COMMS,'cmi':CMI,   # committee-cluster layout (Porter): positions + anchors + per-member primary committee
        'elay':ELAY,'refs':REFE,   # layer toggles: per-drawn-edge provenance code + signed reference dyads
        'recept':[round((_RC.get(n) or {}).get('pressure_mult',1.0),2) for n in members]}   # behavioral receptivity (colorBy=recept)
dump_atomic({name[i]:BP[i] for i in range(len(name))},MB_ROOT+r'\bipartisan.json')
out=MB_ROOT+r'\dashboard_data.json'
dump_atomic(bundle,out,separators=(',',':'))
print('wrote %s  (%.1f KB)  nodes=%d edges=%d issues=%d'%(out,os.path.getsize(out)/1024,len(name),len(E),len(issues)))
