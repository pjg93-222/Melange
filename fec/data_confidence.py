import json,openpyxl,sys,collections
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
B=r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
wb=openpyxl.load_workbook(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx',data_only=True)
pr=wb['Press Release - Normalized']; ra=wb['Rank & Allocation']
members=[ra.cell(r,1).value for r in range(3,536) if ra.cell(r,1).value]
prow={pr.cell(r,1).value:r for r in range(2,535) if pr.cell(r,1).value}
LEG=json.load(open(B+r'\archive_leg.json'))
VC=json.load(open(B+r'\vote_category_lean.json')); n2b={v:k for k,v in VC['name_of'].items()}; votes=VC['votes']
cats=[('Examination & Supervision',5),('CU Capital Requirements',6),('NCUA Budget & Insurance',7),('Interchange',8),
('Payments',9),('Technology & Emerging',10),('Fraud Prevention',11),('Data Privacy & Cyber',12),('Charter Modernization',13),
('Defense CU Issues',14),('Field of Membership',15),('CDFI Fund',17),('CFPB',19),('Credit Card Mandates',20),
('TCPA',21),('Member Business Lending',22),('Mortgage & Housing',23)]
# per-member coverage across the three pillars
conf={}
for m in members:
    legc=sum(1 for lab,_ in cats if abs(LEG.get(m,{}).get(lab,0))>1e-9)
    prc =sum(1 for lab,pc in cats if m in prow and abs(pr.cell(prow[m],pc).value or 0)>0.02)
    voc =sum(1 for lab,_ in cats if (votes.get(n2b.get(m,''),{}).get(lab,{}) or {}).get('n',0)>=5)
    # 0-100 coverage: legislation breadth (50) + press presence (30) + vote presence (20)
    score=round(min(1,legc/4)*50 + min(1,prc/2)*30 + min(1,voc/1)*20)
    conf[m]={'score':score,'legcats':legc,'presscats':prc,'votecats':voc}
json.dump({m:conf[m]['score'] for m in members},open(B+r'\confidence.json','w'))
low=sorted([(m,c['score']) for m,c in conf.items() if c['score']<30],key=lambda x:x[1])
print('per-member data-coverage confidence written (confidence.json)')
print('LOW-confidence members (<30): %d  e.g.'%len(low),[m.split()[-1] for m,_ in low[:8]])
nobill=[m for m in members if conf[m]['legcats']==0]
print('members with ZERO archive bills (press/votes only): %d'%len(nobill))
# per-category pillar coverage (flag single-pillar categories)
print('\nPER-CATEGORY pillar coverage (members with leg / press / votes):')
for lab,pc in cats:
    lc=sum(1 for m in members if abs(LEG.get(m,{}).get(lab,0))>1e-9)
    pcc=sum(1 for m in members if m in prow and abs(pr.cell(prow[m],pc).value or 0)>0.02)
    vc=sum(1 for m in members if (votes.get(n2b.get(m,''),{}).get(lab,{}) or {}).get('n',0)>=5)
    flag=' <-- single-pillar' if sum(x>5 for x in (lc,pcc,vc))<=1 else ''
    print('   %-26s leg %3d  press %3d  votes %3d%s'%(lab,lc,pcc,vc,flag))
# cap saturation per topic
print('\nCAP SATURATION (members at the $50k coalition cap, and flip funded count):')
co=json.load(open(B+r'\per_topic_coalition.json')); fl=json.load(open(B+r'\per_topic_alloc.json'))
for t in list(co.keys()):
    sat=sum(1 for v in co[t].values() if v>=50000); seeds=len(co[t])
    print('   %-30s %d/%d seeds capped'%(t[:30],sat,seeds))
