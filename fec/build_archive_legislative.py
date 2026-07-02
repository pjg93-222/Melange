import pandas as pd,glob,json,sys,collections,csv,re
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
A=pd.read_excel(sorted(glob.glob(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\congress_bills_archive_*.xlsx'))[-1],sheet_name='All Bills')
model=[m['member'] for m in json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\congestion.json'))]
mset=set(model)
SECKW=[('Examination & Supervision','examination'),('CU Capital Requirements','capital'),('NCUA Budget & Insurance','ncua'),
('Interchange','interchange'),('Payments','payments'),('Technology & Emerging','technology'),('Fraud Prevention','fraud'),
('Data Privacy & Cyber','data privacy'),('Charter Modernization','charter'),('Defense CU Issues','defense'),
('Field of Membership','field of membership'),('CDFI Fund','cdfi'),('CFPB','cfpb'),('Credit Card Mandates','credit card'),
('TCPA','telephone'),('Member Business Lending','member business'),('Mortgage & Housing','mortgage')]
def seccat(s):
    s=str(s).lower()
    for cat,kw in SECKW:
        if kw in s: return cat
    return None
NEG={'Interchange','Credit Card Mandates'}
def billkey(name):
    m=re.match(r'\s*([HS])\.?\s*([RJ]?\.?\s*(?:Res\.?)?)\s*(\d+)',str(name),re.I)
    return ('H' if m.group(1).upper()=='H' else 'S',int(m.group(3))) if m else None
# D3 (2026-07-01): per-bill direction registry for ALL categories (generalizes the old CFPB-only csv).
# Direction: 1 = pro-CU, -1 = anti-CU, 0 = neutral (excluded). Registry beats every section default,
# so a pro-CU Interchange bill can finally score positive. User-editable; seeded from cfpb_bill_directions.csv.
bdir={}
for row in csv.DictReader(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\bill_directions.csv',encoding='utf-8-sig')):
    bk=billkey(row['Bill'])
    if bk: bdir[bk]=row['Direction'].strip()
def rolewt(role):
    r=str(role).lower()
    if 'original' in r: return 2.0
    if 'cosponsor' in r or 'co-spons' in r: return 1.0
    if 'sponsor' in r: return 3.0
    return 1.0
bylast=collections.defaultdict(list)
for n in model: bylast[n.split()[-1].lower()].append(n)
def matchmember(mem):
    if mem in mset: return mem
    toks=str(mem).replace(',',' ').replace('.',' ').split()
    if not toks: return None
    for t in [toks[-1].lower(),toks[0].lower()]:
        c=bylast.get(t)
        if c and len(c)==1: return c[0]
        if c:
            fi=toks[0][0].lower()
            for cand in c:
                if cand.split()[0][0].lower()==fi: return cand
            return c[0]
    return None
leg=collections.defaultdict(lambda:collections.defaultdict(float)); unmatched=collections.Counter()
for _,r in A.iterrows():
    cat=seccat(r['Section'])
    if not cat: continue
    mm=matchmember(r['Member'])
    if not mm: unmatched[str(r['Member'])]+=1; continue
    dw=r['DecayWeight'] if pd.notna(r['DecayWeight']) else 1.0; w=rolewt(r['Role'])
    bk=billkey(r['Name'])
    if bk in bdir:                        # registry beats the section default (any category)
        sign={'1':1,'-1':-1}.get(bdir[bk],0)
        if sign==0: continue              # '0' = neutral bill, excluded (the old code mis-signed these -1)
    elif cat=='CFPB':
        sign=1                            # CFPB default = restrain-side (all 43 archive bills ARE in the registry today; this default covers future pulls)
    elif cat=='Credit Card Mandates':
        sign=1 if 'disapproval' in str(r['Title']).lower() else -1   # CRA disapproval overturns the fee rule = pro-CU; rate/fee caps = anti-CU
    else:
        sign=-1 if cat in NEG else 1
    leg[mm][cat]+=sign*w*dw
print('matched model members with >=1 archive bill: %d / %d'%(len(leg),len(model)))
um=sum(unmatched.values()); print('unmatched archive rows: %d ; top unmatched names:'%um,[n for n,_ in unmatched.most_common(6)])
json.dump({m:dict(leg[m]) for m in leg},open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\archive_leg.json','w'))
print('\nVALIDATION — Durbin per-category (signed role-weighted):')
for c,v in sorted(leg['Richard Durbin'].items(),key=lambda x:-abs(x[1])): print('   %-26s %+.1f'%(c,v))
