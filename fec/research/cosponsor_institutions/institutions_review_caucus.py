"""Root review of caucus source counts, dates and independent graph formulas."""
import datetime as dt
import json
from collections import defaultdict, Counter
import fitz
import numpy as np
import pandas as pd
from institutions_common import OLD, OUT, digest, read_json, write_json, stamp


def run():
    receipt = read_json(OUT / 'caucus_receipt.json')
    audit = read_json(OUT / 'caucus_extraction_audit.json')
    evidence = [json.loads(s) for s in (OUT / 'caucus_evidence.jsonl').read_text(encoding='utf-8').splitlines()]
    accepted = [r for r in evidence if r['status'] == 'accepted']
    assert len({(r['target_congress'],r['kind'],r['group_id'],r['bioguide']) for r in accepted}) == len(accepted)
    counts = Counter(r['source_id'] for r in accepted)
    assert counts == {'cmo_116':1108,'cmo_117':957,'psc_117':54,'psc_118':63}
    checks = []
    for source in receipt['sourcehashes']:
        assert digest(source['path']) == source['sha256']
    for cg in [116,117]:
        document = fitz.open(OUT / f'caucus_sources/cmo_{cg}.pdf')
        for row in [r for r in accepted if r['source_id'] == f'cmo_{cg}'][::19]:
            text = document[row['page']-1].get_text()
            normalized = ' '.join(text.replace('\u2019',"'").split())
            assert row['raw_name'].replace('\u2019',"'") in normalized, row
            checks.append({'source':row['source_id'],'page':row['page'],'raw_name':row['raw_name']})
    identifiers = read_json(OLD / 'identifiers.json')
    selected_bills = {}
    with (OLD / 'bills.jsonl').open(encoding='utf-8') as handle:
        for line in handle:
            b=json.loads(line)
            if b['congress'] in [117,118]:
                selected_bills[b['key']]=b
    checks_by_congress = {}
    for cg in [117,118]:
        meta=pd.read_parquet(OLD/f'meta_{cg}.parquet',columns=['member','bill','day'])
        matrix=np.memmap(OUT/f'caucus_{cg}.f32',dtype='float32',mode='r',shape=(len(meta),15))
        groups={}
        for kind in ['leadership','membership']:
            by_member=defaultdict(set)
            for r in accepted:
                if r['target_congress']==cg and r['kind']==kind:by_member[r['bioguide']].add(r['group_id'])
            groups[kind]=by_member
        membership_day=dt.date.fromisoformat(receipt['splits'][str(cg)]['membership_date']).toordinal()
        assert np.all(matrix[meta.day.to_numpy()<=membership_day,10]==0)
        assert np.all(matrix[meta.day.to_numpy()>membership_day,10]==1)
        maximum_error=0.
        for ix in np.random.default_rng(7100+cg).choice(len(meta),300,replace=False):
            row=meta.iloc[ix];mid=identifiers['members'][int(row.member)]
            b=selected_bills[identifiers['bills'][int(row.bill)]]
            # Independently normalize the frozen bill's dated joins.
            joins={}
            for c in b['cosponsors']:
                day=dt.date.fromisoformat(c['date']).toordinal()
                joins[c['member']]=min(day,joins.get(c['member'],day))
            for kind, indices in [('leadership',(5,6)),('membership',(13,14))]:
                if kind=='membership' and row.day<=membership_day:continue
                own=groups[kind][mid]
                weights={peer:len(own&g) for peer,g in groups[kind].items() if peer!=mid}
                denominator=sum(weights.values())
                values=[]
                for lower in [-10**8,int(row.day)-30]:
                    numerator=sum(weights.get(peer,0) for peer,day in joins.items() if lower<=day<int(row.day))
                    values.append(numerator/denominator if denominator else 0.)
                err=float(np.max(np.abs(matrix[ix,list(indices)]-values)))
                maximum_error=max(maximum_error,err)
                assert err<1e-6,(cg,int(ix),kind,err)
        checks_by_congress[str(cg)]={'sample_rows':300,'membership_date_gates_all_rows':True,'maximum_exposure_error':maximum_error}
    write_json(OUT/'source_review_caucus.json',dict(status='PASS',completed_utc=stamp(),receipt_sha256=digest(OUT/'caucus_receipt.json'),
        code_sha256=digest(__file__),counts=dict(counts),raw_pdf_name_checks=checks,panels=checks_by_congress,
        code_review=['No labels read by builder','Prior-Congress officer roles distinct from membership','Same-day joins and announcements excluded',
        'Source total mismatch retained rather than inventing identities','Unlisted people unknown; no continuous-membership claim','Graph co-affiliation is observational, not causal influence'],
        qualification='Official historical documents retrieved in 2026; date of byte-level public availability not independently proven. Partial single-caucus membership test.'))
    print('Root caucus review PASS')


if __name__=='__main__':run()
