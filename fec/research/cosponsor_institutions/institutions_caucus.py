"""Dated caucus observations for the separate institutional research experiment.

CMO officer lists measure prior-Congress leadership history. Problem Solvers
announcements measure a bounded set of positive membership observations.
Neither establishes complete membership, continuing membership, or persuasion.
No model fitting and no earlier research/production output writes.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import unicodedata

os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
import fitz
import numpy as np
import pandas as pd
import yaml

from institutions_common import ROOT, OUT, OLD, digest, read_json, write_json, stamp

SOURCE = OUT / 'caucus_sources'
LEADERSHIP = ['caucus_leadership_lag_groups_log', 'caucus_leadership_lag_unknown',
    'caucus_leadership_lag_finance_groups_log', 'caucus_leadership_lag_sponsor_shared_log',
    'caucus_leadership_lag_sponsor_unknown', 'caucus_leadership_lag_peer_exposure',
    'caucus_leadership_lag_recent30_peer_exposure', 'caucus_leadership_lag_peer_max_shared_log']
MEMBERSHIP = ['caucus_membership_observed_groups_log', 'caucus_membership_unknown',
    'caucus_membership_source_available', 'caucus_membership_sponsor_shared_log',
    'caucus_membership_sponsor_unknown', 'caucus_membership_peer_exposure',
    'caucus_membership_recent30_peer_exposure']
FEATURES = LEADERSHIP + MEMBERSHIP
CMO_DATES = {116: '2020-02-29', 117: '2022-04-30'}
PSC_DATES = {117: '2021-01-22', 118: '2023-03-08'}
FINANCE_PATTERN = (r'\b(?:bank\w*|financ\w*|credit\w*|insurance|insur\w*|housing|'
    r'homeown\w*|mortgage\w*|tax\w*|small business|entrepreneur\w*|capital market\w*|'
    r'invest\w*|saving\w*|payment\w*|retire\w*|pension\w*|blockchain|digital asset\w*|'
    r'cryptocurrenc\w*)\b')
# Reviewed full-name aliases, linked to the historical identity record below.
# Typos/ambiguous combinations in the CMO PDF are deliberately not fuzzy-matched.
REVIEWED_ALIASES = {
    'Alex X. Mooney':'M001195', 'Ann McLane Kuster':'K000382', 'Bill Keating':'K000375',
    'Cindy Axne':'A000378', 'Dan Kildee':'K000380', 'Dan Lipinski':'L000563', 'Dan Meuser':'M001204',
    'Dave Joyce':'J000295', 'Dave Loebsack':'L000565', 'Deb Haaland':'H001080', 'Don Beyer':'B001292',
    'Don Davis':'D000230', 'Gerry Connolly':'C001078', 'Glenn GT Thompson':'T000467',
    'Jeffrey A. Merkley':'M001176', 'Jim Baird':'B001307', 'Jim Sensenbrenner':'S000244',
    'Lacy Clay':'C001049', 'Lou Correa':'C001110', 'Marc Molinaro':'M001221', 'Michael Bost':'B001295',
    'Michael Gallagher':'G000579', 'Mike Conaway':'C001062', 'Mike Doyle':'D000482', 'Mike Enzi':'E000285',
    'Mike Lawler':'L000599', 'Pete Visclosky':'V000108', 'Rob Wittman':'W000804', 'Steven Stivers':'S001187',
}


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s).strip()


def compact_name(s):
    return ' '.join(t for t in norm(s).split() if len(t)>1 and t not in {'jr','sr','ii','iii','iv'})


def clean(s):
    return re.sub(r'\s+', ' ', s).strip()


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]
    def handle_data(self, data):
        if data.strip(): self.parts.append(data.strip())


def identities():
    directories = sorted(p for p in (ROOT/'data/staffer_network/reference/congress-legislators').iterdir() if p.is_dir())
    assert len(directories)==1
    people={}; aliases=collections.defaultdict(set); receipts=[]
    for filename in ['legislators-current.yaml','legislators-historical.yaml']:
        path=directories[0]/filename; receipts.append(dict(path=str(path),sha256=digest(path)))
        for row in yaml.load(path.read_bytes(),Loader=yaml.CSafeLoader):
            mid=row['id'].get('bioguide')
            terms=[dict(start=str(t['start']),end=str(t['end']),chamber=t['type'],state=t['state'],
                district=t.get('district'),party=t.get('party')) for t in row.get('terms',[]) if t['type'] in ['rep','sen']]
            if not mid or not terms: continue
            name=row['name']; people[mid]=dict(name=name,terms=terms)
            names=[name.get('official_full',''),name.get('first','')+' '+name.get('last',''),
                name.get('nickname','')+' '+name.get('last','')]
            for value in names:
                if len(norm(value).split())<2: continue
                aliases[norm(value)].add(mid); aliases[compact_name(value)].add(mid)
    path=ROOT/'fec/legislators.csv'; receipts.append(dict(path=str(path),sha256=digest(path)))
    with path.open(encoding='utf-8-sig',newline='') as handle:
        for row in csv.DictReader(handle):
            mid=row['bioguide_id']
            if mid in people:
                aliases[norm(row['full_name'])].add(mid); aliases[compact_name(row['full_name'])].add(mid)
    return people,aliases,receipts


def resolve(raw, day, chamber, people, aliases, state=None, district=None):
    candidates=aliases.get(norm(raw),set()) | aliases.get(compact_name(raw),set())
    reviewed={norm(n):mid for n,mid in REVIEWED_ALIASES.items()}
    review_used=norm(raw) in reviewed
    if review_used: candidates=candidates | {reviewed[norm(raw)]}
    # This misspelling is corrected elsewhere in the same PSC 117 statement;
    # its GA-07 identity is additionally required to match historical service.
    source_typo=norm(raw)=='carolyn bordeaux' and day=='2021-01-22' and state=='GA' and district==7
    if source_typo: candidates=candidates | {'B001312'}
    matches=[]
    for mid in sorted(candidates):
        terms=[t for t in people[mid]['terms'] if t['start']<=day<t['end'] and t['chamber']==chamber]
        if state: terms=[t for t in terms if t['state']==state and (district is None or t['district']==district)]
        if terms: matches.append(mid)
    if len(matches)==1:
        return matches[0],('same_source_spelling_correction_and_exact_district' if source_typo else
            'reviewed_full_name_alias_and_service' if review_used else 'exact_name_or_initial_suffix_normalization')
    return None,'not_serving_or_unresolved' if not matches else 'ambiguous_name'


def cmo_rows(cg):
    """PDF font/column geometry identifies group headings, avoiding staff contacts."""
    doc=fitz.open(SOURCE/f'cmo_{cg}.pdf'); current=None; rows=[]; headings=[]; raw_members=0
    for pn in range(1,len(doc)):
        page=doc[pn]; page_heads=[]; page_members=[]
        for block in page.get_text('dict')['blocks']:
            spans=[s for line in block.get('lines',[]) for s in line['spans']]
            title=[s for s in spans if (17.5<s['size']<18.5 if cg==116 else 13.5<s['size']<14.5) and s['bbox'][0]<280]
            if title:
                name=clean(' '.join(s['text'] for s in title))
                page_heads.append((min(s['bbox'][1] for s in title),name));headings.append(dict(page=pn+1,group=name))
            for s in spans:
                txt=clean(s['text'])
                if re.match(r'^(?:Rep\.?|Sen\.?|Senator|Resident Commissioner)\s',txt):
                    if cg==117 and s['bbox'][0]<280: continue
                    page_members.append((s['bbox'][1],txt));raw_members+=1
        events=sorted([(y,0,name) for y,name in page_heads]+[(y,1,txt) for y,txt in page_members])
        for y,kind,value in events:
            if kind==0: current=value
            else:
                assert current, (cg,pn,value)
                match=re.match(r'^(Rep\.?|Sen\.?|Senator|Resident Commissioner)\s+(.+)$',value)
                assert match,value
                prefix,raw=match.groups()
                rows.append(dict(target_congress=cg+1,source_congress=cg,source_id=f'cmo_{cg}',
                    evidence_date=CMO_DATES[cg],group_id=norm(current),group_label=current,
                    raw_name=raw.strip(),role='chair_cochair' if cg==116 else 'chair_or_sponsor',
                    kind='leadership',chamber='sen' if prefix in ['Sen','Sen.','Senator'] else 'rep',page=pn+1,
                    pdf_y=round(y,3),state=None,district=None))
    return rows,dict(pages=len(doc),headings=len(headings),unique_groups=len(set(h['group'] for h in headings)),
        raw_officer_rows=raw_members,groups=headings)


def psc_rows(cg):
    raw=(SOURCE/f'psc_{cg}.html').read_bytes().decode('utf-8')
    parser=TextParser();parser.feed(raw);txt='\n'.join(parser.parts)
    (SOURCE/f'psc_{cg}_extracted.txt').write_text(txt,encoding='utf-8')
    date_phrase='Jan 22, 2021' if cg==117 else 'March 8, 2023'
    assert date_phrase in txt
    marker=('Members of the Problem Solvers Caucus for the 117th Congress include:' if cg==117
        else 'Membership of the Problem Solvers Caucus for the 118th Congress includes:')
    start=txt.index(marker);tail=txt[start+len(marker):]
    tail=tail[tail.index('italicized.')+len('italicized.'):]
    # The roster ends at the first quoted statement, not later quoted speakers.
    end=tail.index('\u201c') if cg==117 else tail.index('"Last Congress')
    roster=tail[:end]
    pattern=r'([^\[\]\(\)]+?)\s*[\[\(]([A-Z]{2})\s*-\s*(\d+|AL)[\]\)]'
    entries=[(clean(n),s,0 if d=='AL' else int(d),'member') for n,s,d in re.findall(pattern,roster)]
    if cg==117:
        # Co-chairs are explicit members but omitted from the article's roster list.
        for role in ['Democratic Co-Chair','Republican Co-Chair']:
            match=re.search(role+r':\s*([^\[]+)\[([A-Z]{2})-(\d+)\]',txt)
            assert match,role
            n,s,d=match.groups();entries.append((clean(n),s,int(d),'cochair'))
    rows=[]
    for name,state,district,role in entries:
        rows.append(dict(target_congress=cg,source_congress=cg,source_id=f'psc_{cg}',
            evidence_date=PSC_DATES[cg],group_id='problem solvers caucus',group_label='Problem Solvers Caucus',
            raw_name=name,role=role,kind='membership',chamber='rep',page=None,pdf_y=None,state=state,district=district))
    return rows,dict(explicit_roster_names=len(entries)-(2 if cg==117 else 0),explicit_cochairs_added=2 if cg==117 else 0,
        stated_total=56 if cg==117 else None,
        limitation='117 names omit two co-chairs from the roster body; we add them from the explicit leadership section. No unnamed members inferred. The explicit names include a Puerto Rico delegate and do not reconcile with the stated 28 Democrats plus 28 Republicans.' if cg==117 else
        '63 explicit roster entries include Puerto Rico and Guam delegates; membership may change after this announcement.')


def extract():
    people,aliases,identity_receipts=identities(); raw=[]; summaries={}; source_receipts=[]
    for cg in [116,117]:
        rows,summary=cmo_rows(cg);raw.extend(rows);summaries[f'cmo_{cg}']=summary
    for cg in [117,118]:
        rows,summary=psc_rows(cg);raw.extend(rows);summaries[f'psc_{cg}']=summary
    for row in raw:
        mid,reason=resolve(row['raw_name'],row['evidence_date'],row['chamber'],people,aliases,row['state'],row['district'])
        row['bioguide']=mid;row['identity_resolution']=reason;row['status']='accepted' if mid else 'quarantined'
        row['finance_name_match']=bool(re.search(FINANCE_PATTERN,row['group_label'],re.I))
    # Dedup exact member-group observations; a repeated official listing is not extra strength.
    seen=set()
    for row in raw:
        if row['status']!='accepted': continue
        key=(row['target_congress'],row['kind'],row['group_id'],row['bioguide'],row['evidence_date'])
        if key in seen: row['status']='duplicate_observation'
        seen.add(key)
    for sid in summaries:
        part=[r for r in raw if r['source_id']==sid];accepted=[r for r in part if r['status']=='accepted']
        summaries[sid].update(status_counts=dict(collections.Counter(r['status'] for r in part)),
            accepted_members=len(set(r['bioguide'] for r in accepted)),accepted_groups=len(set(r['group_id'] for r in accepted)),
            unresolved_names=sorted(set(r['raw_name'] for r in part if r['status']=='quarantined')))
        receipt=read_json(SOURCE/f'{sid}_download.json');path=SOURCE/(sid+('.pdf' if sid.startswith('cmo') else '.html'))
        assert digest(path)==receipt['sha256']; receipt['path']=str(path);receipt['evidence_date']=CMO_DATES.get(int(sid[4:])) if sid.startswith('cmo') else PSC_DATES[int(sid[4:])]
        source_receipts.append(receipt)
    path=OUT/'caucus_evidence.jsonl'
    path.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in raw),encoding='utf-8')
    write_json(OUT/'caucus_extraction_audit.json',dict(created_utc=stamp(),sources=source_receipts,identities=identity_receipts,
        source_summaries=summaries,finance_pattern=FINANCE_PATTERN,reviewed_aliases=REVIEWED_ALIASES,ledger_sha256=digest(path),
        dating='CMO month-end bounds from document cover, corroborated by PDF creation metadata. Actual downloads occurred in 2026; no claim that these exact bytes were captured contemporaneously. PSC historical event publication date is distinct from 2026 retrieval. Same day excluded.',
        scope='Historical leadership observations and one caucus membership subset. No current role assertions, no full caucus census.'))
    print(json.dumps({s:{k:v for k,v in x.items() if k!='groups'} for s,x in summaries.items()},indent=2),flush=True)
    return raw


def load_bills():
    audit=read_json(OLD/'data_audit.json');path=OLD/'bills.jsonl'
    assert digest(path)==audit['extracted_bills_sha256']
    bills={}
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            b=json.loads(line)
            if b['congress'] not in [117,118]: continue
            joins={}
            for c in b['cosponsors']:
                day=dt.date.fromisoformat(c['date']).toordinal()
                joins[c['member']]=min(day,joins.get(c['member'],day))
            bills[b['key']]=dict(sponsor=b['sponsor'],joins=joins,congress=b['congress'])
    return bills


def graph(rows,ids):
    groups=sorted(set(r['group_id'] for r in rows)); index={g:i for i,g in enumerate(groups)}
    nodes=sorted(set(ids)|set(r['bioguide'] for r in rows)); lookup={m:i for i,m in enumerate(nodes)}
    membership=np.zeros((len(nodes),len(groups)),np.float32);finance=np.zeros(len(groups),bool)
    for r in rows:
        membership[lookup[r['bioguide']],index[r['group_id']]]=1
        finance[index[r['group_id']]] |= r['finance_name_match']
    adjacency=membership@membership.T;np.fill_diagonal(adjacency,0)
    return nodes,lookup,membership,adjacency,finance


def exposures(adjacency,candidate,peers):
    total=adjacency.sum(axis=1)[candidate]
    if not len(peers): return np.zeros(len(candidate),np.float32),np.zeros(len(candidate),np.float32)
    edges=adjacency[np.ix_(candidate,peers)]
    share=np.divide(edges.sum(axis=1),total,out=np.zeros(len(candidate),np.float32),where=total>0)
    return share,np.log1p(edges.max(axis=1))


def build():
    if (OUT/'caucus_receipt.json').exists(): raise RuntimeError('Caucus features already frozen')
    raw=[json.loads(line) for line in (OUT/'caucus_evidence.jsonl').read_text(encoding='utf-8').splitlines()]
    audit=read_json(OUT/'caucus_extraction_audit.json');assert digest(OUT/'caucus_evidence.jsonl')==audit['ledger_sha256']
    ids=read_json(OLD/'identifiers.json');bills=load_bills();splits={}
    for cg in [117,118]:
        lead=[r for r in raw if r['status']=='accepted' and r['target_congress']==cg and r['kind']=='leadership']
        member=[r for r in raw if r['status']=='accepted' and r['target_congress']==cg and r['kind']=='membership']
        nodes,lookup,lmat,ladj,finance=graph(lead,ids['members'])
        mnodes,mlookup,mmat,madj,_=graph(member,ids['members'])
        lday=dt.date.fromisoformat(CMO_DATES[cg-1]).toordinal();mday=dt.date.fromisoformat(PSC_DATES[cg]).toordinal()
        metadata_path=OLD/f'meta_{cg}.parquet';meta_hash=digest(metadata_path)
        m=pd.read_parquet(metadata_path,columns=['group','bill','day','member'])
        assert lday<int(m.day.min())
        lmapping=np.array([lookup[mid] for mid in ids['members']],np.int32)
        mmapping=np.array([mlookup[mid] for mid in ids['members']],np.int32)
        lgroups=lmat.sum(axis=1);mgroups=mmat.sum(axis=1);lfinance=lmat[:,finance].sum(axis=1)
        path=OUT/f'caucus_{cg}.f32';a=np.memmap(path,mode='w+',dtype=np.float32,shape=(len(m),len(FEATURES)))
        a[:]=0
        ri=lmapping[m.member.to_numpy()]
        a[:,0]=np.log1p(lgroups[ri]);a[:,1]=(lgroups[ri]==0);a[:,2]=np.log1p(lfinance[ri])
        a[:,4]=1;a[:,9]=1;a[:,12]=1
        for _,ix in m.groupby('group',sort=False).indices.items():
            first=m.iloc[ix[0]];day=int(first.day);bill=bills[ids['bills'][int(first.bill)]]
            assert bill['congress']==cg
            assert np.all(m.day.to_numpy()[ix]==day) and np.all(m.bill.to_numpy()[ix]==int(first.bill))
            candidate=lmapping[m.member.to_numpy()[ix]];sponsor=lookup.get(bill['sponsor'])
            peers=[lookup[mid] for mid,d in bill['joins'].items() if d<day and mid in lookup]
            recent=[lookup[mid] for mid,d in bill['joins'].items() if day-30<=d<day and mid in lookup]
            if sponsor is not None:
                a[ix,3]=np.log1p(ladj[candidate,sponsor]);a[ix,4]=lgroups[sponsor]==0
            a[ix,5],a[ix,7]=exposures(ladj,candidate,peers);a[ix,6],_=exposures(ladj,candidate,recent)
            if mday<day:
                candidate=mmapping[m.member.to_numpy()[ix]];sponsor=mlookup.get(bill['sponsor'])
                a[ix,8]=np.log1p(mgroups[candidate]);a[ix,9]=mgroups[candidate]==0;a[ix,10]=1
                if sponsor is not None:
                    a[ix,11]=np.log1p(madj[candidate,sponsor]);a[ix,12]=mgroups[sponsor]==0
                peers=[mlookup[mid] for mid,d in bill['joins'].items() if d<day and mid in mlookup]
                recent=[mlookup[mid] for mid,d in bill['joins'].items() if day-30<=d<day and mid in mlookup]
                a[ix,13],_=exposures(madj,candidate,peers);a[ix,14],_=exposures(madj,candidate,recent)
        a.flush()
        coverage={name:dict(nonzero_rows=int(np.count_nonzero(a[:,i])),min=float(a[:,i].min()),max=float(a[:,i].max())) for i,name in enumerate(FEATURES)}
        assert np.isfinite(a).all();assert np.all(a[m.day.to_numpy()<=mday,8]==0)
        assert np.all(a[m.day.to_numpy()<=mday,10]==0)
        split=dict(path=str(path),rows=len(m),shape=[len(m),len(FEATURES)],dtype='float32',order='C',sha256=digest(path),
            metadata_path=str(metadata_path),metadata_sha256=meta_hash,leadership_date=CMO_DATES[cg-1],membership_date=PSC_DATES[cg],
            coverage=coverage,leadership_members=int((lgroups>0).sum()),membership_members=int((mgroups>0).sum()),
            membership_before_or_same_day_rows=int((m.day.to_numpy()<=mday).sum()),forecast_min=str(dt.date.fromordinal(int(m.day.min()))),
            forecast_max=str(dt.date.fromordinal(int(m.day.max()))))
        assert digest(metadata_path)==meta_hash;splits[str(cg)]=split;del a,m
        print('Caucus feature panel completed:',cg,flush=True)
    source_paths=[Path(s['path']) for s in audit['sources']]+[Path(s['path']) for s in audit['identities']]
    source_paths += [OLD/'identifiers.json',OLD/'bills.jsonl',OUT/'caucus_evidence.jsonl',OUT/'caucus_extraction_audit.json']
    write_json(OUT/'caucus_receipt.json',dict(completed_utc=stamp(),features=FEATURES,feature_groups=dict(leadership=LEADERSHIP,membership=MEMBERSHIP),
        splits=splits,sourcehashes=[dict(path=str(p),sha256=digest(p)) for p in source_paths],code_sha256=digest(__file__),
        source_vintages={sid:s['evidence_date'] for sid,s in zip(['cmo_116','cmo_117','psc_117','psc_118'],audit['sources'])},
        fullmembership_readiness='A dated single-caucus subset is ready for testing. No comprehensive caucus census. 117 source total and explicit names do not reconcile; only named positives retained. Nonlisted membership remains unknown.',
        timing_rules='CMO leadership is a previous-Congress observation, never backfilled as current role. PSC membership observed only after its same-Congress announcement. Every evidence date must be strictly less than forecast; all joins d < forecast and recent forecast-30 <= d < forecast. Sponsor handled separately, never automatically included among earlier cosponsors.',
        formulas='Binary member-group incidence; undirected co-group adjacency is count of shared observed groups, diagonal zero. Sponsor and maximum peer ties log1p. Peer exposure equals sum of ties to distinct earlier cosponsors divided by candidate total tie strength across all source graph nodes, zero when no ties. Counts log1p. Finance count uses prespecified name regex, not bill outcomes. Missing positive evidence is zero plus unknown=1; source_available flags membership release timing.',
        alignment='Every OLD metadata row, original order, integer Bioguide/bill codes decoded using frozen identifiers.json. No gold cohort filtering, labels, fitting, or Congress 119 feature use.',
        source_qualification=audit['dating']))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--extract',action='store_true');parser.add_argument('--build',action='store_true')
    args=parser.parse_args()
    if args.extract: extract()
    if args.build: build()
    if not args.extract and not args.build: parser.error('Choose --extract and/or --build')
