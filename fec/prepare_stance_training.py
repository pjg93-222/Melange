# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT,DRAFT as MB_DRAFT  # centralized root (arch review 2026-07-02)
"""PREPARE STANCE TRAINING DATA — fuses the user's cu_stance_label_set_AUGMENTED.xlsx (two-hop labels,
train/test splits, targets, stance spans, speaker attribution) with the full text_snippets from
cu_stance_label_set.csv into one training-ready jsonl, following the dataset-construction discipline of
Khan et al. (IECE TACS 2025): balanced classes documented, explicit labeling guidelines (the workbook's
Codebook sheet), fixed train/test split (user's own: 456/87/9-excluded), and augmentation of the rare
class (Sheet 3 'Oppose candidates' — included as split=candidate_oppose until the user labels them).
Two supervised tasks come out of the same rows:
  task=composed : human_label      (member's stance toward CREDIT UNIONS — the production signal)
  task=hop1     : hop1_stance      (member's stance toward the TARGET — Burnham/Stanceformer layer;
                                    only rows where the user filled/verified hop1)
Writes stance_training.jsonl + class/split stats."""
import csv,json,io,sys,collections
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
import openpyxl
B=MB_ROOT
DS=MB_DRAFT
XLSX=r'C:\Users\pgoff\Downloads\cu_stance_label_set_AUGMENTED.xlsx'
snip={}
for r in csv.DictReader(open(DS+r'\cu_stance_label_set.csv',encoding='utf-8-sig')):
    if (r.get('row') or '').strip(): snip[r['row'].strip()]={'text':(r.get('text_snippet') or ''),'url':r.get('url') or ''}
wb=openpyxl.load_workbook(XLSX,read_only=True,data_only=True)
out=[]
for sn in ('Labels (augmented)','Oppose candidates'):
    ws=wb[sn]; rows=list(ws.iter_rows(values_only=True))
    ix={str(h):i for i,h in enumerate(rows[0])}
    g=lambda r,k:(str(r[ix[k]]).strip() if k in ix and r[ix[k]] is not None else '')
    for r in rows[1:]:
        if not g(r,'member'): continue
        rid=g(r,'row'); s=snip.get(rid,{})
        rec={'row':rid,'sheet':sn,'split':g(r,'split'),'review_flag':g(r,'review_flag'),
             'member':g(r,'member'),'date':g(r,'date'),'title':g(r,'title'),
             'label_composed':g(r,'human_label').lower(),'hop1_stance':g(r,'hop1_stance').lower(),
             'hop1_proposed':g(r,'hop1_stance_proposed'),'target':g(r,'target'),
             'hop2_acu_position':g(r,'hop2_acu_position'),'speaker_source':g(r,'speaker_source'),
             'stance_span':g(r,'stance_span'),'intensity_r':g(r,'intensity_r'),
             'text':(s.get('text') or g(r,'stance_span') or g(r,'title'))[:4000],'url':s.get('url','')}
        out.append(rec)
with io.open(B+r'\stance_training.jsonl','w',encoding='utf-8') as f:
    for r in out: f.write(json.dumps(r,ensure_ascii=True)+'\n')
sp=collections.Counter(r['split'] for r in out)
lb=collections.Counter((r['split'],r['label_composed']) for r in out if r['label_composed'])
h1=sum(1 for r in out if r['hop1_stance'])
tx=sum(1 for r in out if len(r['text'])>len(r['title'])+10)
print('stance_training.jsonl: %d rows | splits %s'%(len(out),dict(sp)))
print('composed labels: train %s | test %s'%({k[1]:v for k,v in lb.items() if k[0]=='train'},{k[1]:v for k,v in lb.items() if k[0]=='test'}))
print('hop1 filled (user-verified): %d | rows with full text joined: %d/%d'%(h1,tx,len(out)))
print('candidate_oppose rows awaiting the user\'s label: %d'%sp.get('candidate_oppose',0))
