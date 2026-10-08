# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
"""MULTILAYER NETWORK BUILDER — integrates the press-derived layers into the live cascade network.

Writes `congress_cosponsor_network_AUG<date>.xlsx` in the exact Edges format the NINE existing loaders
glob by mtime (`congress_cosponsor_network_*.xlsx`) — so the augmented graph goes live pipeline-wide with
ZERO loader changes, and REVERT = delete the AUG file (the original xlsx is never touched).

Layer policy (conservative, provenance-tracked in a second sheet):
  1. COSPONSOR edges: copied verbatim — the augmentation never modifies an existing tie.
  2. ENGAGEMENT edges (press_engagement.json, Fink-normalized empirical influence): added for pairs not
     already tied.  The cascade kernel is p = w/(w+6), so an engagement probability p maps to weight
     w = 6p/(1-p), capped at 2.0 (a strong cosponsor tie).  These are EMPIRICAL probabilities (Fink et
     al. 2023) — the one layer whose weights arrive already in probability units.
  3. HCoI edges (press_hcoi.json, who-talks-about-the-same-issues): added ONLY when incident to a
     cosponsor-ISOLATED member (the D4 fix: leadership doesn't cosponsor by norm; Hoyer/Clyburn/Scalise/
     Jordan/Jason Smith were unreachable by every cascade/route).  Weight = 0.6*r*HCOI_W (default cap
     0.12, i.e. p~0.02 per step — a weak interest-affinity tie, NOT a collaboration claim).  Adding all
     1,239 HCoI edges would triple graph density on a similarity signal; surgical is the honest choice.
Env dials: ENG_CAP (2.0), HCOI_W (0.2 -> max weight 0.12), AUG_OUT (filename override).
After building, run audit_full.py — the whole 40-check suite then validates the augmented graph."""
import json,sys,os,glob,collections,datetime
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
import openpyxl
B=MB_ROOT
ENG_CAP=float(os.environ.get('ENG_CAP','2.0')); HCOI_W=float(os.environ.get('HCOI_W','0.2'))
C={m['member']:m for m in json.load(open(B+r'\congestion.json'))}
name2bio={m:C[m]['bioguide'] for m in C if C[m].get('bioguide')}
bio2name={v:k for k,v in name2bio.items()}
# 1) original cosponsor edges (pick the newest NON-augmented file so re-runs don't compound)
srcs=[p for p in glob.glob(B+r'\congress_cosponsor_network_*.xlsx') if 'AUG' not in os.path.basename(p)]
src=max(srcs,key=os.path.getmtime)
ws=openpyxl.load_workbook(src,data_only=True)['Edges']
edges={}; deg=collections.Counter()
for r in range(2,ws.max_row+1):
    a,b,w=ws.cell(r,1).value,ws.cell(r,2).value,ws.cell(r,3).value
    if a and b and isinstance(w,(int,float)):
        k=(min(a,b),max(a,b))
        # deep-audit fix 2026-07-02: the source xlsx carries 41 reverse-dup pairs with asymmetric weights
        # (the old D2 wart). Loaders mean-symmetrize anyway; symmetrize HERE too so the AUG artifact is
        # clean at rest (one row per pair, mean weight) instead of reproducing the wart.
        if k in edges: edges[k]=('cosponsor',(edges[k][1]+w)/2)
        else: edges[k]=('cosponsor',w)
        if a in bio2name: deg[bio2name[a]]+=1
        if b in bio2name: deg[bio2name[b]]+=1
have=set()
for a,b in edges: have.add((min(a,b),max(a,b)))
isolated={m for m in C if deg[m]==0}
print('base: %s (%d edge rows) | cosponsor-isolated members: %d'%(os.path.basename(src),len(edges),len(isolated)))
# 2) engagement layer (empirical influence probabilities -> kernel-inverse weights)
neweng=0
try:
    pe=json.load(open(B+r'\press_engagement.json',encoding='utf-8'))
    for e in pe['symmetric']:
        a,b=name2bio.get(e['a']),name2bio.get(e['b'])
        if not a or not b: continue
        k=(min(a,b),max(a,b))
        if k in have: continue
        w=min(ENG_CAP,6*e['w']/max(1e-6,1-e['w']))
        if w<0.01: continue
        edges[k]=('engagement',round(w,4)); have.add(k); neweng+=1   # N-2 (audit 2026-07-08): key by sorted k (not raw a,b) so the social branch's `k in edges` reinforcement lookup matches instead of double-writing the pair
except FileNotFoundError: print('  (press_engagement.json missing — run press_engagement_layer.py)')
# 3) HCoI layer — ONLY edges touching a cosponsor-isolated member (the D4 surgical fix)
newhc=0; reconnected=set()
try:
    hc=json.load(open(B+r'\press_hcoi.json',encoding='utf-8'))
    for e in hc['edges']:
        if e['a'] not in isolated and e['b'] not in isolated: continue
        a,b=name2bio.get(e['a']),name2bio.get(e['b'])
        if not a or not b: continue
        k=(min(a,b),max(a,b))
        if k in have: continue
        edges[k]=('hcoi',round(0.6*e['r']*HCOI_W,4)); have.add(k); newhc+=1   # N-2 (audit 2026-07-08): key by sorted k (see engagement branch)
        for m in (e['a'],e['b']):
            if m in isolated: reconnected.add(m)
except FileNotFoundError: print('  (press_hcoi.json missing — run press_hcoi.py)')
# 4) SOCIAL INTERACTION layer (social_interaction_layer.py: member reposts + mentions, Fink-normalized)
#    — user 2026-07-02: posts/reposts enter as BOTH network linkages AND edge weights:
#    (a) NEW EDGE for untied pairs: same kernel-inverse mapping as engagement, w=6p/(1-p), cap SOC_CAP;
#    (b) REINFORCEMENT for already-tied pairs: w *= 1 + SOC_REINF*min(1, p/0.10) — a pair at or above
#        10% interaction probability gets the full boost (default +30%, SOC_REINF=0 disables). A repost
#        channel on top of cosponsorship means the tie is live in public, not just on paper.
SOC_CAP=float(os.environ.get('SOC_CAP','2.0')); SOC_REINF=float(os.environ.get('SOC_REINF','0.3'))
newsoc=0; reinf=0
try:
    si=json.load(open(B+r'\social_interactions.json',encoding='utf-8'))
    for e in si['symmetric']:
        a,b=name2bio.get(e['a']),name2bio.get(e['b'])
        if not a or not b: continue
        k=(min(a,b),max(a,b))
        if k in edges:
            lay,w0=edges[k]
            edges[k]=(lay+'+social',round(w0*(1.0+SOC_REINF*min(1.0,e['w']/0.10)),4)); reinf+=1
        else:
            w=min(SOC_CAP,6*e['w']/max(1e-6,1-e['w']))
            if w<0.01: continue
            edges[k]=('social',round(w,4)); have.add(k); newsoc+=1
except FileNotFoundError: print('  (social_interactions.json missing — run social_interaction_layer.py)')
# 5) write the augmented workbook (Edges sheet = loader contract; Provenance sheet = audit trail)
out=os.environ.get('AUG_OUT',B+r'\congress_cosponsor_network_AUG%s.xlsx'%datetime.date.today().strftime('%Y%m%d'))
wb=openpyxl.Workbook(); e1=wb.active; e1.title='Edges'
e1.append(['source_bioguide','target_bioguide','weight'])
pr=wb.create_sheet('Provenance'); pr.append(['source_bioguide','target_bioguide','weight','layer'])
for (a,b),(lay,w) in sorted(edges.items()):
    e1.append([a,b,w]); pr.append([a,b,w,lay])
pr.append([]); pr.append(['built',datetime.datetime.now().isoformat(),'base',os.path.basename(src)])
pr.append(['policy','cosponsor verbatim; engagement w=6p/(1-p) cap %.1f; hcoi only isolated-incident, w=0.6*r*%.2f; social new-edge cap %.1f + reinforcement x(1+%.2f*min(1,p/.10)) on tied pairs'%(ENG_CAP,HCOI_W,SOC_CAP,SOC_REINF)])
pr.append(['revert','delete this file — loaders fall back to the newest plain cosponsor xlsx'])
wb.save(out)
print('AUGMENTED NETWORK: +%d engagement edges, +%d HCoI edges (isolated-incident only), +%d SOCIAL edges, %d existing ties socially reinforced'%(neweng,newhc,newsoc,reinf))
print('  D4: %d/%d formerly-isolated members are now cascade-reachable: %s%s'%(
    len(reconnected),len(isolated),', '.join(sorted(reconnected)[:8]),'...' if len(reconnected)>8 else ''))
print('wrote %s  -> ALL loaders pick it up by mtime; regenerate pipeline + audit_full to validate'%os.path.basename(out))
