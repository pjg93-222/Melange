import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
from moneyball_core import dump_atomic   # S2-03: crash-safe artifact write
import pandas as pd,glob,json,sys,collections,csv,re
import bill_rules as BR
from members.member_identity import Resolver
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
# The verified sentinel is persisted to the canonical workbook before this
# producer runs.  Consume that worksheet, not the transient collector JSONL,
# so the Excel bill ledger and every downstream label share one source of
# truth.  Pending rows are visible for review but are never admitted here.
_sentinel_path=MB_ROOT+r'\Sentinel Bill Ledger.xlsx'
_sentinel_n=0
_sentinel_verified=0
if _o.path.exists(_sentinel_path):
    try:
        _sentinel=pd.read_excel(_sentinel_path,sheet_name='Sentinel Bill Ledger')
    except ValueError:
        _sentinel=None
    if _sentinel is not None:
        _sentinel_n=len(_sentinel)
        _eligible=_sentinel.get('Scoring Eligible',False)
        if not hasattr(_eligible,'fillna'):
            _eligible=pd.Series([False]*len(_sentinel),index=_sentinel.index)
        _eligible=_eligible.fillna(False).astype(str).str.strip().str.lower().isin(
            {'true','1','yes'}
        )
        _verified=_sentinel[_eligible].copy()
        _sentinel_verified=len(_verified)
        if _sentinel_verified:
            _verified=_verified.rename(columns={
                'Bill':'Name','Cosponsor Count':'CosponsorCount',
                'Latest Action':'LastAction','Detail Link':'DetailLink',
                'Summary':'bill_summary',
            })
            _verified['Role']=_verified['Role'].replace(
                {'original':'original-cosponsor'}
            )
            for _col in A.columns:
                if _col not in _verified.columns: _verified[_col]=''
            A=pd.concat([A,_verified[A.columns]],ignore_index=True)
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
model=[m['member'] for m in json.load(open(MB_ROOT+r'\data\engine\congestion.json'))]
mset=set(model)
def seccat(s):
    return BR.canonical_category(s)
NEG={'Interchange','Credit Card Mandates'}
def billkey(name):
    return BR.bill_key(name)
def load_direction_registry(path,legacy=False):
    """Load the legacy bill-number registry or the Congress-aware typed registry."""
    if legacy:
        registry={}
        for row in csv.DictReader(open(path,encoding='utf-8-sig')):
            key=billkey(row['Bill'])
            if key: registry[key]=row['Direction'].strip()
        return registry
    registry={'exact':{},'blank':{}}
    for row in csv.DictReader(open(path,encoding='utf-8-sig')):
        key=BR.bill_type_key(row.get('Bill'))
        if not key: continue
        direction=(row.get('Direction') or '').strip()
        congress=BR._congress(row.get('Congress'))
        if congress: registry['exact'][(key,congress)]=direction
        else: registry['blank'][key]=direction
    return registry
def direction_for(registry,bill,congress,legacy=False):
    """Return (direction, mechanism), preferring typed exact Congress over blank fallback."""
    if legacy:
        value=registry.get(billkey(bill))
        return (value,'legacy-registry') if value is not None else (None,None)
    key=BR.bill_type_key(bill)
    if not key: return None,None
    exact=(key,BR._congress(congress))
    if exact in registry['exact']: return registry['exact'][exact],'registry-exact'
    if key in registry['blank']: return registry['blank'][key],'registry-blank'
    return None,None
def direction_registry_path(root,legacy=False):
    """Return the pinned registry path for the requested compatibility mode."""
    return (_o.path.join(root,'backups','bill_directions.PRE-LEGFIX3.csv')
            if legacy else _o.path.join(root,'data', 'legislation', 'bill_directions.csv'))
def legacy_direction_enabled(environ=None):
    """Keep the compatibility dial strict: only LEGDIR_V1=1 selects legacy behavior."""
    environment=_o.environ if environ is None else environ
    return environment.get('LEGDIR_V1')=='1'
# D3 (2026-07-01): per-bill direction registry for ALL categories (generalizes the old CFPB-only csv).
# Direction: 1 = pro-CU, -1 = anti-CU, 0 = neutral (excluded). Registry beats every section default,
# so a pro-CU Interchange bill can finally score positive. User-editable; seeded from cfpb_bill_directions.csv.
_legacy_directions=legacy_direction_enabled()
_direction_path=direction_registry_path(MB_ROOT,_legacy_directions)
bdir=load_direction_registry(_direction_path,_legacy_directions)
def rolewt(role):
    return BR.role_weight(role)
_resolver=Resolver(model)
def matchmember(mem): return _resolver.resolve(mem)
overrides=BR.load_overrides(MB_ROOT+r'\data\legislation\bill_overrides.csv')
leg=collections.defaultdict(lambda:collections.defaultdict(float)); unmatched=collections.Counter()
excluded=collections.Counter(); overridden=collections.Counter()
events={}; routing_rows=[]; duplicate_rows=collections.Counter()
def _clean(value):
    if value is None or pd.isna(value): return None
    if isinstance(value,(int,float,str,bool)): return value
    return str(value)
for _idx,r in A.iterrows():
    audit={'source_row':int(_idx)+2,'member_source':_clean(r.get('Member')),
           'bill':_clean(r.get('Name')),'congress':_clean(r.get('Congress')),
           'title':_clean(r.get('Title')),'source_section':_clean(r.get('Section')),
           'source_role':_clean(r.get('Role'))}
    cat=seccat(r['Section'])
    if not cat:
        audit['disposition']='unknown-section'; routing_rows.append(audit); continue
    audit['category_mechanism']='source-section'
    phrase=BR.excluded_bill(r.get('Name'),r.get('Congress'),r.get('Title'),r.get('bill_summary'))
    if phrase:
        excluded[phrase]+=1; audit.update({'disposition':'excluded-title','reason':phrase})
        routing_rows.append(audit); continue
    mm=matchmember(r['Member'])
    if not mm:
        unmatched[str(r['Member'])]+=1; audit['disposition']='unmatched-member'
        routing_rows.append(audit); continue
    dw=BR.evidence_decay(r.get('Name'),r.get('Congress'),
                         r.get('DecayWeight') if pd.notna(r.get('DecayWeight')) else 1.0)
    role=BR.canonical_role(r['Role']); w=rolewt(role)
    registry_direction,registry_mechanism=direction_for(
        bdir,r['Name'],r.get('Congress'),_legacy_directions)
    ov=BR.override_for(overrides,r['Name'],r.get('Congress'))
    sign=None
    if ov:
        overridden['rows']+=1
        audit['override_reason']=(ov.get('Reason') or ov.get('Notes')
                                  or ov.get('Note') or 'bill override')
        if not BR.override_included(ov):
            overridden['excluded']+=1; audit['disposition']='excluded-override'
            routing_rows.append(audit); continue
        if ov.get('Category'):
            ocat=BR.canonical_category(ov['Category'])
            if not ocat: raise ValueError('Unknown override category for %s: %s'%(r['Name'],ov['Category']))
            cat=ocat
            audit['category_mechanism']='bill-override'
        odir=parse_direction(ov.get('Direction',''))
        if odir is not None:
            sign=odir
            audit['direction_mechanism']='override-direction'
            if sign==0:
                audit.update({'member':mm,'effective_category':cat,'sign':0,
                              'contribution':0.0})
                overridden['neutral']+=1; audit['disposition']='neutral-override'
                routing_rows.append(audit); continue
    if sign is None and parse_direction(r.get('ManualDirection')) is not None:
        sign=parse_direction(r.get('ManualDirection'))
        audit['direction_mechanism']='manual-direction'
        if sign==0:
            audit.update({'member':mm,'effective_category':cat,'sign':0,
                          'contribution':0.0})
            audit['disposition']='neutral-manual'; routing_rows.append(audit); continue
    if sign is not None:
        pass                              # explicit per-bill/per-Congress override wins
    elif registry_direction is not None:  # registry beats the section default (any category)
        sign={'1':1,'-1':-1}.get(registry_direction,0)
        audit['direction_mechanism']=registry_mechanism
        if sign==0:
            audit.update({'member':mm,'effective_category':cat,'sign':0,
                          'contribution':0.0})
            audit['disposition']='neutral-registry'; routing_rows.append(audit); continue
    elif cat=='CFPB':
        sign=1                            # CFPB default = restrain-side (all 43 archive bills ARE in the registry today; this default covers future pulls)
        audit['direction_mechanism']='cfpb-default'
    elif cat=='Credit Card Mandates':
        sign=1 if BR.is_disapproval(r['Title']) else -1   # CRA disapproval overturns the fee rule = pro-CU; rate/fee caps = anti-CU; matches both 'disapproval' and 'disapproving'
        audit['direction_mechanism']='credit-card-default'
    else:
        sign=-1 if cat in NEG else 1
        audit['direction_mechanism']='section-default'
    contribution=float(sign*w*dw)
    # The archive repeats many original cosponsors once as "original-cosponsor" and again as
    # "cosponsor". Score one member/bill/Congress/effective-domain event, preserving the strongest role.
    event_key=(mm,str(r.get('Name') or '').strip().lower(),BR._congress(r.get('Congress')),cat)
    audit.update({'member':mm,'effective_category':cat,'effective_role':role,'sign':int(sign),
                  'decay_weight':dw,'contribution':contribution,'disposition':'selected'})
    routing_rows.append(audit); ai=len(routing_rows)-1
    prior=events.get(event_key)
    if prior is None:
        events[event_key]={'role':role,'contribution':contribution,'audit_index':ai}
    else:
        preferred=BR.preferred_role((prior['role'],role))
        if preferred==role and role!=prior['role']:
            routing_rows[prior['audit_index']]['disposition']='duplicate-lower-role'
            routing_rows[prior['audit_index']]['selected_role']=role
            duplicate_rows['lower-role-replaced']+=1
            events[event_key]={'role':role,'contribution':contribution,'audit_index':ai}
        else:
            audit['disposition']='duplicate-lower-role' if role!=prior['role'] else 'duplicate-same-role'
            audit['selected_role']=prior['role']
            duplicate_rows[audit['disposition']]+=1
for (mm,_bill,_congress,cat),event in events.items():
    leg[mm][cat]+=event['contribution']
print('matched model members with >=1 archive bill: %d / %d'%(len(leg),len(model)))
print('manual sponsored/original evidence rows loaded: %d'%_manual_n)
print('sentinel bill ledger: %d tracked rows; %d verified scoring rows loaded'%(
      _sentinel_n,_sentinel_verified))
# Fail closed on the sign-on letters. They are the ONLY evidence for CU Tax
# Status and CU-Bank Competitive Dynamics, they live in exactly one file, and
# a run that silently loaded none of them used to print 0 and continue to
# PIPELINE COMPLETE. Bad reads must stop the chain, not quietly zero a
# category.
_ltr = _manual[_manual['Name'].astype(str).str.upper().str.startswith('LTR-')] if _manual_n else None
_ltr_rows = 0 if _ltr is None else len(_ltr)
_ltr_ids = 0 if _ltr is None else _ltr['Name'].nunique()
_ltr_members = 0 if _ltr is None else _ltr['Member'].nunique()
print('letter evidence: %d rows / %d letters / %d members'%(_ltr_rows,_ltr_ids,_ltr_members))
_LTR_MIN_ROWS, _LTR_MIN_IDS, _LTR_MIN_MEMBERS = 296, 7, 251
if _ltr_rows < _LTR_MIN_ROWS or _ltr_ids < _LTR_MIN_IDS or _ltr_members < _LTR_MIN_MEMBERS:
    raise SystemExit(
        'FATAL: sign-on letter evidence incomplete -- got %d rows / %d letters / %d members, '
        'expected at least %d / %d / %d. Refusing to rebuild archive_leg.json; '
        'restore manual_bill_evidence.csv before rerunning.'
        %(_ltr_rows,_ltr_ids,_ltr_members,_LTR_MIN_ROWS,_LTR_MIN_IDS,_LTR_MIN_MEMBERS))
um=sum(unmatched.values()); print('unmatched archive rows: %d ; top unmatched names:'%um,[n for n,_ in unmatched.most_common(6)])
print('shared false-positive exclusions: %d rows; override rows: %d (excluded %d, neutral %d); deduplicated %d rows'%(
      sum(excluded.values()),overridden['rows'],overridden['excluded'],overridden['neutral'],
      sum(duplicate_rows.values())))
dump_atomic({m:dict(leg[m]) for m in leg},MB_ROOT+r'\archive_leg.json')
dump_atomic({'schema':'legislation-routing-audit-v1',
             'source':_o.path.basename(sorted(glob.glob(MB_ROOT+r'\congress_bills_archive_*.xlsx'))[-1])+
                      ' + Sentinel Bill Ledger',
             'source_rows':len(A),'selected_events':len(events),
             'sentinel_ledger_rows':_sentinel_n,
             'sentinel_verified_rows':_sentinel_verified,
             'summary':{'dispositions':dict(collections.Counter(row['disposition'] for row in routing_rows)),
                        'effective_categories':dict(collections.Counter(
                            row.get('effective_category') for row in routing_rows if row.get('effective_category'))),
                        'duplicates':dict(duplicate_rows),'excluded':dict(excluded),
                        'unmatched_members':dict(unmatched.most_common())},
             'rows':routing_rows},MB_ROOT+r'\legislation_routing_audit.json')
print('\nVALIDATION — Durbin per-category (signed role-weighted):')
for c,v in sorted(leg['Richard Durbin'].items(),key=lambda x:-abs(x[1])): print('   %-26s %+.1f'%(c,v))
