import pandas as pd,csv,sys,re,glob,collections,json
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
ARCH=sorted(glob.glob(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\congress_bills_archive_*.xlsx'))[-1]
a=pd.read_excel(ARCH,sheet_name='All Bills')
def billkey(name,cong):
    if not isinstance(name,str) or pd.isna(cong): return None
    m=re.match(r'\s*([HS])\.?\s*([RJ]?\.?\s*(?:Res\.?)?)\s*(\d+)',name.replace('  ',' '),re.I)
    if not m: return None
    return (int(cong),'H' if m.group(1).upper()=='H' else 'S',int(m.group(3)))
# Section is the category NAME -> index 1..17 (keyword match)
SECKW=[(1,'examination'),(2,'capital'),(3,'ncua'),(4,'interchange'),(5,'payments'),(6,'technology'),(7,'fraud'),
(8,'data privacy'),(9,'charter'),(10,'defense'),(11,'field of membership'),(12,'cdfi'),(13,'cfpb'),
(14,'credit card'),(15,'telephone'),(16,'member business'),(17,'mortgage')]
def secnum(s):
    s=str(s).lower()
    for i,kw in SECKW:
        if kw in s: return i
    return None
bill2cat={}
for _,r in a.iterrows():
    bk=billkey(r['Name'],r['Congress']); sn=secnum(r['Section'])
    if bk and sn: bill2cat[bk]=sn
print('bills mapped to a Section:',len(bill2cat))
# CFPB (section 13) per-bill direction: Direction 1=Reduce/Restrain(pro), else Reach/Expand(anti)
cfpb={}
with open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\cfpb_bill_directions.csv',encoding='utf-8-sig') as fh:
    for row in csv.DictReader(fh):
        b=row['Bill']; m=re.match(r'\s*([HS])\.?\s*([RJ]?\.?\s*(?:Res\.?)?)\s*(\d+)',b,re.I)
        if m: cfpb[('H' if m.group(1).upper()=='H' else 'S',int(m.group(3)))]=row['Direction'].strip()
ANTI={4,14}   # Interchange, Credit Card = anti-CU categories (Yea = anti)
CATLAB={1:'Examination & Supervision',2:'CU Capital Requirements',3:'NCUA Budget & Insurance',4:'Interchange',5:'Payments',
6:'Technology & Emerging',7:'Fraud Prevention',8:'Data Privacy & Cyber',9:'Charter Modernization',10:'Defense CU Issues',
11:'Field of Membership',12:'CDFI Fund',13:'CFPB',14:'Credit Card Mandates',15:'TCPA',16:'Member Business Lending',17:'Mortgage & Housing'}
def rc_bill(s):
    if not isinstance(s,str): return None
    m=re.match(r'\s*([HS])\s*([RJ]?)\s*(\d+)',s.replace('.',' '),re.I)
    return ('H' if m.group(1).upper()=='H' else 'S',int(m.group(3))) if m else None
# accumulate signed CU-aligned vote per (bioguide,cat)
agg=collections.defaultdict(lambda:[0.0,0]); name_of={}; covered=collections.Counter(); skip=0
v=pd.read_csv(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\votes\cu_rollcall_votes_clean.csv')
def passage(s): return isinstance(s,str) and re.search(r'passage|suspend the rules and pass|concur',s,re.I) and not re.search(r'recommit|amendment',s,re.I)
for _,r in v.iterrows():
    if not passage(r['vote_question']): skip+=1; continue   # final-passage only (drop amendment/procedural noise)
    bk=rc_bill(r['bill_number'])
    if not bk: skip+=1; continue
    key=(int(r['congress']),bk[0],bk[1]); cat=bill2cat.get(key)
    if not cat: skip+=1; continue
    vote=str(r['vote']).strip().lower()
    if vote in ('yea','yes','aye'): yv=1
    elif vote in ('nay','no'): yv=-1
    else: continue
    # CU-aligned sign
    if cat==13:
        d=cfpb.get(bk); sign=+1 if d=='1' else -1 if d is not None else +1
    else:
        sign=-1 if cat in ANTI else +1
    aligned=yv*sign
    bio=r['bioguide']; name_of[bio]=r['member']; covered[CATLAB[cat]]+=1
    s=agg[(bio,cat)]; s[0]+=aligned; s[1]+=1
print('votes skipped (no bill/category match):',skip,'of',len(v))
print('\nvote coverage by category (roll-call votes landing in each):')
for c in range(1,18):
    print('   %-26s %5d votes'%(CATLAB[c],covered[CATLAB[c]]))
# per-member per-category mean signed lean [-1,1]
out=collections.defaultdict(dict)
for (bio,cat),(ssum,cnt) in agg.items():
    out[bio][CATLAB[cat]]={'lean':ssum/cnt,'n':cnt}
json.dump({'name_of':name_of,'votes':out},open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\vote_category_lean.json','w'))
nm=len(out); print('\nmembers with >=1 categorized vote:',nm)
# sanity: Durbin (interchange author) and a known CFPB opponent
b2n={v:k for k,v in name_of.items()}
for who in ['Richard Durbin','Andy Barr','Maxine Waters']:
    bio=b2n.get(who)
    if bio and bio in out:
        items=sorted(out[bio].items(),key=lambda x:x[1]['lean'])
        print('   %s: most-anti %s | most-pro %s'%(who,
            ', '.join('%s %.2f(n%d)'%(k,d['lean'],d['n']) for k,d in items[:2]),
            ', '.join('%s %.2f(n%d)'%(k,d['lean'],d['n']) for k,d in items[-2:])))
print('\nwrote vote_category_lean.json')
