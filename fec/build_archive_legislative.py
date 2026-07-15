import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
from moneyball_core import dump_atomic   # S2-03: crash-safe artifact write
import pandas as pd,glob,json,sys,collections,csv,re
import bill_rules as BR
from member_identity import Resolver
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
def parse_direction(value):
    """Parse spreadsheet/CSV direction cells without pandas dtype surprises.

    ``read_csv`` may coerce a column containing blanks to floats, so valid 1/-1 values arrive as
    1.0/-1.0.  Missing stays ``None``; explicit zero stays 0 (neutral/excluded).
    """
    if value is None or pd.isna(value): return None
    text=str(value).strip()
    if not text: return None
    try: number=float(text)
    except (TypeError,ValueError): return 0
    return int(number) if number in (-1.0,0.0,1.0) else 0
A=pd.read_excel(sorted(glob.glob(MB_ROOT+r'\congress_bills_archive_*.xlsx'))[-1],sheet_name='All Bills')
_manual_path=MB_ROOT+r'\manual_bill_evidence.csv'
_manual_n=0
if _o.path.exists(_manual_path):
    _manual=pd.read_csv(_manual_path)
    _manual=_manual.rename(columns={'Category':'Section','Bill':'Name','Summary':'bill_summary','Direction':'ManualDirection'})
    if 'ManualDirection' not in A.columns: A['ManualDirection']=''
    for _col in A.columns:
        if _col not in _manual.columns: _manual[_col]=''
    _manual_n=len(_manual)
    A=pd.concat([A,_manual[A.columns]],ignore_index=True)
model=[m['member'] for m in json.load(open(MB_ROOT+r'\congestion.json'))]
mset=set(model)
def seccat(s):
    return BR.canonical_category(s)
NEG={'Interchange','Credit Card Mandates'}
def billkey(name):
    return BR.bill_key(name)
# D3 (2026-07-01): per-bill direction registry for ALL categories (generalizes the old CFPB-only csv).
# Direction: 1 = pro-CU, -1 = anti-CU, 0 = neutral (excluded). Registry beats every section default,
# so a pro-CU Interchange bill can finally score positive. User-editable; seeded from cfpb_bill_directions.csv.
bdir={}
for row in csv.DictReader(open(MB_ROOT+r'\bill_directions.csv',encoding='utf-8-sig')):
    bk=billkey(row['Bill'])
    if bk: bdir[bk]=row['Direction'].strip()
def rolewt(role):
    return BR.role_weight(role)
_resolver=Resolver(model)
def matchmember(mem): return _resolver.resolve(mem)
overrides=BR.load_overrides(MB_ROOT+r'\bill_overrides.csv')
leg=collections.defaultdict(lambda:collections.defaultdict(float)); unmatched=collections.Counter()
excluded=collections.Counter(); overridden=collections.Counter()
for _,r in A.iterrows():
    cat=seccat(r['Section'])
    if not cat: continue
    phrase=BR.excluded_bill(r.get('Name'),r.get('Congress'),r.get('Title'),r.get('bill_summary'))
    if phrase: excluded[phrase]+=1; continue
    mm=matchmember(r['Member'])
    if not mm: unmatched[str(r['Member'])]+=1; continue
    dw=r['DecayWeight'] if pd.notna(r['DecayWeight']) else 1.0; w=rolewt(r['Role'])
    bk=billkey(r['Name'])
    ov=BR.override_for(overrides,r['Name'],r.get('Congress'))
    sign=None
    if ov:
        overridden['rows']+=1
        if not BR.override_included(ov): overridden['excluded']+=1; continue
        if ov.get('Category'):
            ocat=BR.canonical_category(ov['Category'])
            if not ocat: raise ValueError('Unknown override category for %s: %s'%(r['Name'],ov['Category']))
            cat=ocat
        odir=parse_direction(ov.get('Direction',''))
        if odir is not None:
            sign=odir
            if sign==0: overridden['neutral']+=1; continue
    if sign is None and parse_direction(r.get('ManualDirection')) is not None:
        sign=parse_direction(r.get('ManualDirection'))
        if sign==0: continue
    if sign is not None:
        pass                              # explicit per-bill/per-Congress override wins
    elif bk in bdir:                      # registry beats the section default (any category)
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
print('manual sponsored/original evidence rows loaded: %d'%_manual_n)
um=sum(unmatched.values()); print('unmatched archive rows: %d ; top unmatched names:'%um,[n for n,_ in unmatched.most_common(6)])
print('shared false-positive exclusions: %d rows; override rows: %d (excluded %d, neutral %d)'%(
      sum(excluded.values()),overridden['rows'],overridden['excluded'],overridden['neutral']))
dump_atomic({m:dict(leg[m]) for m in leg},MB_ROOT+r'\archive_leg.json')
print('\nVALIDATION — Durbin per-category (signed role-weighted):')
for c,v in sorted(leg['Richard Durbin'].items(),key=lambda x:-abs(x[1])): print('   %-26s %+.1f'%(c,v))
