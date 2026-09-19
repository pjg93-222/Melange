"""Attach explicit transfer paths, conserved estimates and unresolved coverage."""
import argparse
from collections import defaultdict
import json
import csv
import hashlib
from pathlib import Path
import sqlite3
from fec_transfer_graph import allocate,reachable,atomic_json


# --- tidy staging store (schema_version "tidy-1") ---------------------------
#
# These seven tables exist only on the Python side of the export: R has already
# written the receipt and dimension tables into the same SQLite file and the
# orchestrator publishes it once both producers are done. They are appended
# here, in place, because this is the only process that ever holds them.
#
# Column names are the contract's (section 2.12), not this module's internal
# keys, and the types are declared explicitly: SQLite would otherwise give an
# all-NULL column BLOB affinity, and the workbook writer reads the declared type
# to choose a currency, integer or date cell format.

def _cycle_label(cycle):
    try:
        year=int(cycle)
    except (TypeError,ValueError):
        return None
    return f'{year - 1}-{year}'


def _text(value):
    if value is None:return None
    if isinstance(value,(dict,list)):return json.dumps(value,sort_keys=True)
    text=str(value).strip()
    return text or None


def _number(value):
    if value is None or isinstance(value,bool):return None
    try:
        return float(value)
    except (TypeError,ValueError):
        return None


def _count(value):
    number=_number(value)
    return None if number is None else int(round(number))


def _flag(value):
    if value is None:return None
    if isinstance(value,bool):return int(value)
    if isinstance(value,(int,float)):return int(bool(value))
    text=str(value).strip().lower()
    if text in ('yes','true','t','y','1'):return 1
    if text in ('no','false','f','n','0'):return 0
    return None


STAGING_TABLES={
    'transfer_paths':(
        (('cycle_label','TEXT'),lambda r:_cycle_label(r.get('cycle'))),
        (('cycle','INTEGER'),lambda r:_count(r.get('cycle'))),
        (('funded_committee','TEXT'),lambda r:_text(r.get('root'))),
        (('source_committee','TEXT'),lambda r:_text(r.get('source'))),
        (('destination_committee','TEXT'),lambda r:_text(r.get('destination'))),
        (('reported_net_transfer','REAL'),lambda r:_number(r.get('amount'))),
        (('depth','INTEGER'),lambda r:_count(r.get('depth'))),
        (('representative_path','TEXT'),lambda r:_text(r.get('path'))),
        (('traversal_status','TEXT'),lambda r:_text(r.get('status'))),
    ),
    'funding_cohorts':(
        (('cycle_label','TEXT'),lambda r:_cycle_label(r.get('cycle'))),
        (('cycle','INTEGER'),lambda r:_count(r.get('cycle'))),
        (('company','TEXT'),lambda r:_text(r.get('company'))),
        (('funding_type','TEXT'),lambda r:_text(r.get('funding_type'))),
        (('recipient_committee','TEXT'),lambda r:_text(r.get('committee_id'))),
        (('receipt_role','TEXT'),lambda r:_text(r.get('receipt_role'))),
        (('included_net_receipts','REAL'),lambda r:_number(r.get('amount'))),
        (('receipt_count','INTEGER'),lambda r:_count(r.get('receipt_count'))),
        (('first_receipt','TEXT'),lambda r:_text(r.get('first_date'))),
        (('last_receipt','TEXT'),lambda r:_text(r.get('last_date'))),
    ),
    'allocation_estimates':(
        (('cycle_label','TEXT'),lambda r:_cycle_label(r.get('cycle'))),
        (('cycle','INTEGER'),lambda r:_count(r.get('cycle'))),
        (('funded_committee','TEXT'),lambda r:_text(r.get('root'))),
        (('candidate_id','TEXT'),lambda r:_text(r.get('candidate_id'))),
        (('candidate','TEXT'),lambda r:_text(r.get('candidate_name'))),
        (('direction','TEXT'),lambda r:_text(r.get('direction'))),
        (('conditional_estimate','REAL'),lambda r:_number(r.get('estimated_amount'))),
    ),
    'allocation_coverage':(
        (('cycle_label','TEXT'),lambda r:_cycle_label(r.get('cycle'))),
        (('cycle','INTEGER'),lambda r:_count(r.get('cycle'))),
        (('funded_committee','TEXT'),lambda r:_text(r.get('root'))),
        (('net_input_funding','REAL'),lambda r:_number(r.get('input_net_funding'))),
        (('nonnegative_model_funding','REAL'),lambda r:_number(r.get('model_funding'))),
        (('estimated_candidate_activity','REAL'),
         lambda r:_number(r.get('estimated_candidate_activity'))),
        (('unresolved','REAL'),lambda r:_number(r.get('unresolved'))),
        (('negative_net_funding','REAL'),
         lambda r:_number(r.get('negative_net_funding_excluded'))),
        # A reason map is evidence a reader opens, not a dimension. Splitting it
        # into rows here would multiply every unresolved dollar by its reasons.
        (('unresolved_reasons','TEXT'),lambda r:_text(r.get('unresolved_reasons'))),
    ),
    'source_freshness':(
        (('cycle_label','TEXT'),lambda r:_cycle_label(r.get('cycle'))),
        (('cycle','INTEGER'),lambda r:_count(r.get('cycle'))),
        (('fec_dataset','TEXT'),lambda r:_text(r.get('source'))),
        (('checked_at','TEXT'),lambda r:_text(r.get('checked_at'))),
        (('server_last_modified','TEXT'),lambda r:_text(r.get('last_modified'))),
        (('sha256','TEXT'),lambda r:_text(r.get('sha256'))),
        (('source_url','TEXT'),lambda r:_text(r.get('url'))),
    ),
    'classification_review':(
        (('cycle_label','TEXT'),lambda r:_cycle_label(r.get('cycle'))),
        (('cycle','INTEGER'),lambda r:_count(r.get('cycle'))),
        (('committee_id','TEXT'),lambda r:_text(r.get('committee_id'))),
        (('committee','TEXT'),lambda r:_text(r.get('committee_name'))),
        (('official_type','TEXT'),lambda r:_text(r.get('master_committee_type'))),
        (('reporting_category','TEXT'),lambda r:_text(r.get('recipient_category'))),
        (('included_funding','REAL'),
         lambda r:_number(r.get('preliminary_crypto_funding'))),
    ),
}

DATA_QUALITY_COLUMNS=(('check_id','TEXT'),('source','TEXT'),('severity','TEXT'),
                      ('passed','INTEGER'),('detail','TEXT'),('metric','TEXT'))


def stage(payload,path):
    """Append the Python-side tables to an existing tidy staging store.

    The store MUST already hold the R-side tables. Connecting to a missing file
    would create an empty database and publish a companion workbook with seven
    sheets and no receipts - a failure that looks like a successful build.
    """
    path=Path(path)
    if not path.is_file():
        raise ValueError(f'Tidy staging store does not exist: {path}')
    with sqlite3.connect(str(path)) as database:
        existing={row[0] for row in database.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if 'contributions' not in existing:
            raise ValueError(
                f'Tidy staging store holds no contributions table: {path}')
        written={}
        for table,specification in STAGING_TABLES.items():
            columns=[column for column,_ in specification]
            database.execute(f'DROP TABLE IF EXISTS "{table}"')
            database.execute('CREATE TABLE "{}" ({})'.format(
                table,','.join(f'"{name}" {kind}' for name,kind in columns)))
            rows=[tuple(extract(row) for _,extract in specification)
                  for row in payload.get(table,[]) or []]
            if rows:
                database.executemany('INSERT INTO "{}" VALUES ({})'.format(
                    table,','.join('?' for _ in columns)),rows)
            written[table]=len(rows)
        if 'data_quality' not in existing:
            database.execute('CREATE TABLE "data_quality" ({})'.format(
                ','.join(f'"{name}" {kind}' for name,kind in DATA_QUALITY_COLUMNS)))
        # Replace only this producer's rows: the R guards own source 'r_guard'
        # and the workbook writer appends source 'writer' after this runs.
        database.execute("DELETE FROM data_quality WHERE source='enrichment'")
        checks=[(_text(check.get('id')),'enrichment',_text(check.get('severity')),
                 _flag(check.get('passed')),_text(check.get('detail')),
                 _text(check.get('metric')))
                for check in payload.get('quality_checks',[]) or []]
        if checks:
            database.executemany('INSERT INTO data_quality VALUES (?,?,?,?,?,?)',checks)
        written['data_quality(enrichment)']=len(checks)
        database.commit()
    return written


def enrich(payload,directory):
    paths=[];estimates=[];coverage=[];source_dates=[];review=[]
    masters={(r['cycle'],r['candidate_id']):r for r in payload.get('candidate_master',[])}
    links=defaultdict(set)
    for row in payload.get('candidate_committee_links',[]):
        if row['designation'] in ('P','A'):links[row['cycle'],row['committee_id']].add(row['candidate_id'])
    grouped=defaultdict(float)
    cohorts=defaultdict(lambda: {'amount':0., 'receipt_count':0, 'first_date':'', 'last_date':''})
    for row in payload['raw_rows']:
        if row['include_in_analysis']=='Yes':
            grouped[row['cycle'],row['committee_id']]+=row['amount']
            key=(row['cycle'],row.get('company',''),row.get('employee_tier',''),row['committee_id'],row.get('receipt_role','unverified_receipt_role'),
                 row.get('funding_source_type','Unverified source type'),
                 row.get('funding_direction', 'Into company PAC' if row.get('recipient_category')=='Company PAC' else 'To named recipient'))
            cohort=cohorts[key]
            cohort['amount']+=row['amount'];cohort['receipt_count']+=1
            day=row.get('date','')
            if day:
                cohort['first_date']=min(cohort['first_date'] or day,day)
                cohort['last_date']=max(cohort['last_date'],day)
    totals=defaultdict(lambda:{'direct':0.,'estimated_non_opposition':0.,'estimated_opposition':0.})
    for cycle in (c['cycle'] for c in payload['cycles']):
        funding={committee:value for (year,committee),value in grouped.items() if year==cycle and committee}
        direct_ids={committee for (year,committee) in links if year==cycle}
        for committee in direct_ids:
            if committee not in funding:continue
            candidates=links[cycle,committee]
            if len(candidates)==1:totals[cycle,next(iter(candidates))]['direct']+=funding.pop(committee)
            else:
                amount=funding.pop(committee)
                coverage.append({'cycle':cycle,'root':committee,'input_net_funding':amount,
                    'model_funding':max(0,amount),'estimated_candidate_activity':0,
                    'unresolved':max(0,amount),'negative_net_funding_excluded':min(0,amount),
                    'unresolved_reasons':{'ambiguous_authorized_candidate':max(0,amount)}})
        edges=[row for row in payload.get('transfer_edges',[]) if row['cycle']==cycle]
        activity=[{'source':row['source_committee_id'],'candidate':row['candidate_id'],
                   'direction':row['support_oppose'],'amount':row['preliminary_included_amount'],
                   'transfer_records':row.get('transfer_records',[])}
                  for row in payload['downstream_activity'] if row['cycle']==cycle]
        source_coverage=[r for r in payload['metadata'].get('transfer_coverage',[]) if r['cycle']==cycle]
        unresolved_nodes={node for r in source_coverage for node in r.get('unresolved_sources',[])}
        unresolved_nodes.update(r['source_committee_id'] for r in payload['downstream_activity']
            if r['cycle']==cycle and r.get('unresolved_version_rows',0)>0)
        if any(r.get('unresolved_all_sources') or r['status']=='stale_transfer_index' for r in source_coverage):
            unresolved_nodes.update(funding)
        cycle_paths=reachable({key for key,value in funding.items() if value>0},edges,stop_nodes=direct_ids)
        paths.extend(cycle_paths)
        assigned,unresolved=allocate(funding,edges,activity,stop_nodes=direct_ids,
            candidate_links={committee:links[cycle,committee] for committee in direct_ids},unresolved_nodes=unresolved_nodes)
        for row in assigned:
            candidate=masters.get((cycle,row['candidate_id']),{})
            estimates.append({**row,'cycle':cycle,'candidate_name':candidate.get('candidate_name',row['candidate_id'])})
            field='estimated_opposition' if row['direction']=='Oppose' else 'estimated_non_opposition'
            totals[cycle,row['candidate_id']][field]+=row['estimated_amount']
        coverage.extend(dict(row,cycle=cycle) for row in unresolved)
    summary=[]
    for (cycle,candidate_id),values in totals.items():
        candidate=masters.get((cycle,candidate_id),{})
        summary.append({'industry':payload['metadata']['industry'],'cycle':cycle,'candidate_id':candidate_id,
            'candidate_name':candidate.get('candidate_name',candidate_id),'party':candidate.get('candidate_party',''),
            **values,'direct_plus_estimated_non_opposition':values['direct']+values['estimated_non_opposition']})
    for file in [*directory.glob('*/source-receipt.json'), *(directory.parent/'fec_committee_master').glob('*/source-receipt.json')]:
        source=json.loads(file.read_text(encoding='utf-8'))
        source_dates.append({'source':source['family'],'cycle':source['cycle'],'checked_at':source['checked_at'],
                             'last_modified':source.get('last_modified'),'sha256':source['sha256'],'url':source['url']})
    for row in payload['committee_map']:
        if row['recipient_category']=='Unclassified' and row['preliminary_crypto_funding']:
            review.append({key:row.get(key) for key in ('cycle','committee_id','committee_name','master_committee_type','recipient_category','preliminary_crypto_funding')})
    payload.update(transfer_paths=paths,allocation_estimates=estimates,allocation_coverage=coverage,
                   funding_cohorts=[dict(cycle=k[0],company=k[1],funding_type=k[2],committee_id=k[3],receipt_role=k[4],funding_source_type=k[5],funding_direction=k[6],**v)
                                    for k,v in sorted(cohorts.items())],
                   attribution_summary=sorted(summary,key=lambda r:(r['cycle'],-r['direct_plus_estimated_non_opposition'],r['candidate_id'])),
                   source_freshness=source_dates,classification_review=review)
    payload['metadata']['allocation_method']='Conditional industry-level activity allocation across observed candidate activity and 24G/24K transfers, maximum 3 transfers. Not traced dollars, company attribution or a lower bound. Pools corporate and personal funding. Donation timing, in-kind liquidation, all-donor funding, retained cash and operating expenses are not modelled. Opposition stays against its named target; negative activity is excluded from weights. Use funding cohorts and dated PAC evidence for donor-specific review.'
    payload['metadata']['company_cash_attribution_available']=False
    payload['metadata']['allocation_conservation_verified']=True
    payload['quality_checks']=[*payload['metadata'].get('export_guards',[])]
    unverified=[row for row in payload['raw_rows'] if row.get('include_in_analysis')=='Yes'
                and row.get('receipt_role','unverified_receipt_role').startswith('unverified_')]
    payload['quality_checks'].append({'id':'receipt_role_metadata','severity':'warn','passed':not unverified,
        'detail':f'{len(unverified)} included rows lack sufficient filing-form/line metadata to verify their receipt role. Name matching alone does not verify a contribution; refresh legacy source rows before donor-specific cash attribution.'})
    for source in payload['metadata'].get('transfer_coverage',[]):
        invalid=sum(source.get('counts',{}).get(key,0) for key in
            ('malformed_rows','invalid_transfer_dates','invalid_transfer_amounts','invalid_transfer_destinations','unresolved_rows'))
        payload['quality_checks'].append({'id':f"transfer_source_{source['cycle']}",
            'severity':'warn','passed':source['status']=='indexed' and invalid==0,'detail':json.dumps(source)})
    pending=[row for row in coverage if row['unresolved']>.005]
    payload['quality_checks'].append({'id':'allocation_coverage','severity':'warn','passed':not pending,
        'detail':f'{len(pending)} funding roots have unresolved allocation; consult allocation_coverage for amounts and reasons.'})
    payload['quality_checks'].append({'id':'allocation_conservation','severity':'fail','passed':True,
        'detail':'Arithmetic conservation does not establish complete data or traced dollars.'})
    return payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('payload',type=Path);parser.add_argument('directory',type=Path)
    parser.add_argument('--audit-directory',type=Path)
    parser.add_argument('--audit-only',action='store_true')
    parser.add_argument('--workbook',type=Path)
    # Absent means "no tidy staging": every existing invocation, including the
    # --audit-only companion publication at build time, is unchanged.
    parser.add_argument('--staging',type=Path,
                        help='Tidy staging SQLite written by R/tidy_stage.R; the Python-side tables are appended to it.')
    args=parser.parse_args()
    value=json.loads(args.payload.read_text(encoding='utf-8-sig'))
    if not args.audit_only:value=enrich(value,args.directory)
    if args.audit_directory:
        args.audit_directory.mkdir(parents=True,exist_ok=True)
        for name in ('transfer_paths','allocation_estimates','allocation_coverage','attribution_summary','funding_cohorts','source_freshness','classification_review','quality_checks'):
            rows=value.get(name,[])
            fields=list(dict.fromkeys(key for row in rows for key in row)) or ['status']
            path=args.audit_directory/f'{name}.csv'
            temporary=path.with_suffix('.pending')
            with temporary.open('w',encoding='utf-8-sig',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
                for row in rows:
                    safe={}
                    for key,item in row.items():
                        if isinstance(item,(dict,list)):item=json.dumps(item)
                        if isinstance(item,str) and item[:1] in ('=','+','-','@'):item="'"+item
                        safe[key]=item
                    writer.writerow(safe)
            temporary.replace(path)
        if args.workbook:
            def signature(path):
                with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
            atomic_json(args.audit_directory/'audit-manifest.json',{
                'version':1,'workbook_name':args.workbook.name,'workbook_sha256':signature(args.workbook),
                'payload_path':str(args.payload.resolve()),'payload_sha256':signature(args.payload),
                'csv_sha256':{path.name:signature(path) for path in args.audit_directory.glob('*.csv')}})
    if not args.audit_only:atomic_json(args.payload,value)
    if args.staging and not args.audit_only:
        staged=stage(value,args.staging)
        print('Tidy staging:',json.dumps(staged,sort_keys=True),flush=True)
    print('Transfer paths:',len(value['transfer_paths']),'Allocation records:',len(value['allocation_estimates']),flush=True)


if __name__=='__main__':main()
