"""Auditable committee cash-transfer graph and explicitly modelled allocations.

OTH 24G/24K outgoing records only: incoming mirror records and independent
expenditures are never counted again as transfers. Sources:
https://www.fec.gov/campaign-finance-data/transaction-type-code-descriptions/
https://www.fec.gov/campaign-finance-data/any-transaction-one-committee-another-file-description/
"""
import argparse
from collections import defaultdict,deque
from datetime import datetime,timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import re
import time
import sqlite3
import csv

VERSION=2
CASH_CODES={'24G','24K'}


def atomic_json(path,value):
    pending=path.with_suffix('.pending')
    pending.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    os.replace(pending,path)


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def publish_index(directory,index):
    path=directory/'transfer-edges.csv'
    temporary=path.with_suffix('.pending')
    with temporary.open('w',encoding='utf-8',newline='') as stream:
        fields=['cycle','source','destination','amount','record_count','first_date','last_date']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(index['edges'])
    os.replace(temporary,path)
    info={key:value for key,value in index.items() if key!='edges'}
    info['edges_sha256']=sha(path)
    atomic_json(directory/'transfer-info.json',info)
    atomic_json(directory/'transfer-current.json',index)


def transfer_index(path,cycle):
    signature=sha(path)
    cache=path.parent/f'transfer-index-v{VERSION}-{signature[:20]}.json'
    ledger=cache.with_suffix('.sqlite')
    if cache.exists() and ledger.exists():return json.loads(cache.read_text(encoding='utf-8'))
    started=time.monotonic();counts=defaultdict(int)
    pending=ledger.with_suffix(f'.pending-{os.getpid()}')
    connection=sqlite3.connect(pending)
    connection.execute('PRAGMA journal_mode=OFF')
    connection.execute('PRAGMA synchronous=OFF')
    connection.execute('CREATE TABLE records(version_key TEXT PRIMARY KEY, source TEXT,destination TEXT,date TEXT,cents INTEGER,type TEXT,transaction_id TEXT,file_num INTEGER,memo TEXT,report TEXT,sub_id TEXT,amend_priority INTEGER)')
    sql="""INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(version_key) DO UPDATE SET source=excluded.source,destination=excluded.destination,
    date=excluded.date,cents=excluded.cents,type=excluded.type,transaction_id=excluded.transaction_id,
    file_num=excluded.file_num,memo=excluded.memo,report=excluded.report,sub_id=excluded.sub_id,amend_priority=excluded.amend_priority
    WHERE (excluded.file_num,excluded.amend_priority,excluded.sub_id)>(records.file_num,records.amend_priority,records.sub_id)"""
    batch=[]
    try:
        with path.open(encoding='utf-8',errors='replace') as stream:
            for line in stream:
                counts['source_rows']+=1
                fields=line.rstrip('\n\r').split('|')
                if len(fields)!=21:
                    counts['malformed_rows']+=1;continue
                source,amend,report=fields[:3];kind=fields[5];destination=fields[15]
                if kind not in CASH_CODES or not re.fullmatch(r'C\d{8}',destination):continue
                counts['cash_transfer_rows']+=1
                sub=fields[20];raw_date=fields[13].zfill(8)
                try:date=datetime.strptime(raw_date,'%m%d%Y').date().isoformat()
                except ValueError:
                    counts['invalid_transfer_dates']+=1;continue
                try:cents=int((Decimal(fields[14])*100).to_integral_exact())
                except Exception:
                    counts['invalid_transfer_amounts']+=1;continue
                transaction=fields[16]
                key='|'.join((source,report,date[:4],transaction)) if transaction else 'SUB|'+(sub or str(counts['source_rows']))
                batch.append((key,source,destination,date,cents,kind,transaction,int(fields[17] or 0),fields[18],report,sub,{'N':0,'A':1,'T':2}.get(amend,0)))
                if len(batch)>=10000:
                    connection.executemany(sql,batch);connection.commit();batch.clear()
        if batch:connection.executemany(sql,batch)
        connection.execute("CREATE INDEX records_edge ON records(source,destination)")
        counts['latest_rows']=connection.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        counts['memo_rows']=connection.execute("SELECT COUNT(*) FROM records WHERE memo='X'").fetchone()[0]
        counts['superseded_or_duplicate_rows']=counts['cash_transfer_rows']-counts['latest_rows']-counts['invalid_transfer_dates']-counts['invalid_transfer_amounts']
        # Exact repeated sub-IDs are excluded independently of transaction IDs.
        connection.execute("DELETE FROM records WHERE sub_id<>'' AND rowid NOT IN (SELECT MIN(rowid) FROM records WHERE sub_id<>'' GROUP BY sub_id)")
        connection.commit()
        if connection.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Transfer ledger integrity failed')
        edges=[dict(zip(('source','destination','amount','record_count','first_date','last_date'),row),cycle=cycle)
            for row in connection.execute("SELECT source,destination,SUM(cents)/100.0,COUNT(*),MIN(date),MAX(date) FROM records WHERE memo<>'X' GROUP BY source,destination ORDER BY source,destination")]
    finally:connection.close()
    os.replace(pending,ledger)
    result={'version':VERSION,'source_sha256':signature,'cycle':cycle,'counts':dict(counts),
            'edges':edges,'ledger_path':str(ledger.resolve()),'built_seconds':round(time.monotonic()-started,3)}
    atomic_json(cache,result)
    return result


def reachable(roots,edges,max_depth=3,stop_nodes=()):
    adjacency=defaultdict(list)
    for edge in edges:
        if edge['amount']>0:adjacency[edge['source']].append(edge)
    output=[];visited=set();queue=deque((root,root,0,(root,)) for root in sorted(roots))
    while queue:
        root,node,depth,path=queue.popleft()
        if (root,node) in visited:continue
        visited.add((root,node))
        for edge in adjacency[node]:
            destination=edge['destination']
            status='candidate_committee' if destination in stop_nodes else 'cycle' if destination in path else 'depth_limit' if depth+1>=max_depth else 'followed'
            output.append({**edge,'root':root,'depth':depth+1,'path':' > '.join((*path,destination)),'status':status})
            if status=='followed':queue.append((root,destination,depth+1,(*path,destination)))
    return output


def allocate(funding,edges,activity,max_depth=3,stop_nodes=()):
    """Conserve each root's nonnegative funding over observed cash activity.

    This is a conditional pro-rata scenario, not traced dollars, causal benefit,
    or a lower bound. Opposition stays with the named target, never its rivals.
    """
    adjacency=defaultdict(list);terminal=defaultdict(list)
    for edge in edges:
        if edge['amount']>0 and edge['destination'] not in stop_nodes:
            adjacency[edge['source']].append((edge['destination'],edge['amount']))
    grouped=defaultdict(float)
    for row in activity:
        grouped[(row['source'],row['candidate'],row['direction'])]+=row['amount']
    for (source,candidate,direction),value in grouped.items():
        if value>0:terminal[source].append((candidate,direction,value))
    result=[];coverage=[]
    for root,input_amount in sorted(funding.items()):
        total=max(0,input_amount);allocated=defaultdict(float);unresolved=defaultdict(float)
        pending=[(root,total,0,(root,))] if total else []
        processed=0
        while pending:
            node,amount,depth,path=pending.pop()
            processed+=1
            if processed>100000:
                unresolved['traversal_limit']+=amount+sum(item[1] for item in pending)
                break
            outgoing=adjacency[node];destinations=terminal[node]
            denominator=sum(v for _,v in outgoing)+sum(v for _,_,v in destinations)
            if denominator<=0:unresolved['no_observed_outflow']+=amount;continue
            for candidate,direction,value in destinations:allocated[candidate,direction]+=amount*value/denominator
            for destination,value in outgoing:
                portion=amount*value/denominator
                if destination in path:unresolved['cycle']+=portion
                elif depth>=max_depth:unresolved['depth_limit']+=portion
                else:pending.append((destination,portion,depth+1,(*path,destination)))
        assigned=sum(allocated.values());unknown=sum(unresolved.values())
        if abs(total-assigned-unknown)>max(.005,total*1e-10):raise ValueError('Transfer allocation does not conserve root funding')
        for (candidate,direction),value in allocated.items():
            result.append({'root':root,'candidate_id':candidate,'direction':direction,'estimated_amount':value})
        coverage.append({'root':root,'input_net_funding':input_amount,'model_funding':total,
                         'estimated_candidate_activity':assigned,'unresolved':unknown,
                         'negative_net_funding_excluded':min(0,input_amount),'unresolved_reasons':dict(unresolved)})
    return result,coverage


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--cycles',type=int,nargs='+',default=[2022,2024,2026])
    args=parser.parse_args()
    for cycle in args.cycles:
        index=transfer_index(args.directory/f'oth{str(cycle)[-2:]}'/'itoth.txt',cycle)
        publish_index(args.directory/f'oth{str(cycle)[-2:]}',index)
        print(json.dumps({'cycle':cycle,'counts':index['counts'],'edges':len(index['edges']),'seconds':index['built_seconds']}),flush=True)


if __name__=='__main__':main()
