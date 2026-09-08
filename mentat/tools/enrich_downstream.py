"""Attach explicit transfer paths, conserved estimates and unresolved coverage."""
import argparse
from collections import defaultdict
import json
import csv
import hashlib
from pathlib import Path
from fec_transfer_graph import allocate,reachable,atomic_json


def enrich(payload,directory):
    paths=[];estimates=[];coverage=[];source_dates=[];review=[]
    masters={(r['cycle'],r['candidate_id']):r for r in payload.get('candidate_master',[])}
    links=defaultdict(set)
    for row in payload.get('candidate_committee_links',[]):
        if row['designation'] in ('P','A'):links[row['cycle'],row['committee_id']].add(row['candidate_id'])
    grouped=defaultdict(float)
    for row in payload['raw_rows']:
        if row['include_in_analysis']=='Yes':grouped[row['cycle'],row['committee_id']]+=row['amount']
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
                   'direction':row['support_oppose'],'amount':row['preliminary_included_amount']}
                  for row in payload['downstream_activity'] if row['cycle']==cycle]
        cycle_paths=reachable({key for key,value in funding.items() if value>0},edges,stop_nodes=direct_ids)
        paths.extend(cycle_paths)
        assigned,unresolved=allocate(funding,edges,activity,stop_nodes=direct_ids)
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
                   attribution_summary=sorted(summary,key=lambda r:(r['cycle'],-r['direct_plus_estimated_non_opposition'],r['candidate_id'])),
                   source_freshness=source_dates,classification_review=review)
    payload['metadata']['allocation_method']='Conditional pro-rata allocation of nonnegative net funding across observed candidate activity and 24G/24K cash transfers, maximum 3 transfers. Not traced dollars or a lower bound. Opposition is kept against its named target. Negative activity is excluded from allocation weights. Unobserved operating expenses and retained cash are not modelled.'
    payload['metadata']['allocation_conservation_verified']=True
    payload['quality_checks']=[*payload['metadata'].get('export_guards',[])]
    for source in payload['metadata'].get('transfer_coverage',[]):
        invalid=sum(source.get('counts',{}).get(key,0) for key in
            ('malformed_rows','invalid_transfer_dates','invalid_transfer_amounts'))
        payload['quality_checks'].append({'id':f"transfer_source_{source['cycle']}",
            'severity':'warn','passed':source['status']=='indexed' and invalid==0,'detail':json.dumps(source)})
    payload['quality_checks'].append({'id':'allocation_conservation','severity':'fail','passed':True,
        'detail':'Arithmetic conservation does not establish complete data or traced dollars.'})
    return payload


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('payload',type=Path);parser.add_argument('directory',type=Path)
    parser.add_argument('--audit-directory',type=Path)
    parser.add_argument('--audit-only',action='store_true')
    parser.add_argument('--workbook',type=Path)
    args=parser.parse_args()
    value=json.loads(args.payload.read_text(encoding='utf-8-sig'))
    if not args.audit_only:value=enrich(value,args.directory)
    if args.audit_directory:
        args.audit_directory.mkdir(parents=True,exist_ok=True)
        for name in ('transfer_paths','allocation_estimates','allocation_coverage','attribution_summary','source_freshness','classification_review','quality_checks'):
            rows=value[name]
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
    print('Transfer paths:',len(value['transfer_paths']),'Allocation records:',len(value['allocation_estimates']),flush=True)


if __name__=='__main__':main()
