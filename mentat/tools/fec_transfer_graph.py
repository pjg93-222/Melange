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

VERSION=3
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
        fields=['cycle','source','destination','amount','record_count','first_date','last_date','records']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(index['edges'])
    os.replace(temporary,path)
    info={key:value for key,value in index.items() if key!='edges'}
    info['edges_sha256']=sha(path)
    atomic_json(directory/'transfer-info.json',info)
    atomic_json(directory/'transfer-current.json',index)


def verified_headers(evidence):
    """Accept only preserved, hash-checked filing headers, never inferred dates."""
    from fec_filing_headers import parse_header
    headers={}
    for item in evidence:
        header=item['header']; number=header['file_num']
        prefix=bytes.fromhex(item['prefix_hex'])
        if (hashlib.sha256(prefix).hexdigest()!=item['prefix_sha256']
                or parse_header(prefix,number)!=header
                or item['url']!=f'https://docquery.fec.gov/dcdev/posted/{number}.fec'):
            raise ValueError('Transfer filing header evidence failed verification')
        if number in headers and headers[number]!=header:
            raise ValueError('Conflicting transfer filing headers')
        headers[number]=header
    return headers


def transfer_key(fields,row_number):
    return '|'.join((fields[0],fields[2],fields[16])) if fields[16] else 'SUB|'+fields[0]+'|'+(fields[20] or str(row_number))


def transfer_index(path,cycle,filing_headers=()):
    filing_headers=list(filing_headers)
    headers=verified_headers(filing_headers)
    signature=sha(path)
    header_signature=hashlib.sha256(json.dumps(filing_headers,sort_keys=True).encode()).hexdigest()
    cache=path.parent/f'transfer-index-v{VERSION}-{cycle}-{signature[:20]}-{header_signature[:12]}.json'
    ledger=cache.with_suffix('.sqlite')
    if cache.exists() and ledger.exists():
        cached=json.loads(cache.read_text(encoding='utf-8'))
        if cached.get('ledger_sha256')!=sha(ledger):raise ValueError('Transfer ledger checksum failed')
        return cached
    started=time.monotonic();counts=defaultdict(int)
    pending=ledger.with_suffix(f'.pending-{os.getpid()}-{time.monotonic_ns()}')
    connection=sqlite3.connect(pending)
    connection.execute('PRAGMA journal_mode=OFF')
    connection.execute('PRAGMA synchronous=OFF')
    connection.execute('CREATE TABLE records(version_key TEXT, source TEXT,destination TEXT,date TEXT,cents INTEGER,type TEXT,transaction_id TEXT,file_num INTEGER,memo TEXT,report TEXT,sub_id TEXT,amendment TEXT,raw_line TEXT,status TEXT)')
    connection.execute('CREATE TABLE filing_headers(evidence_json TEXT)')
    connection.executemany('INSERT INTO filing_headers VALUES (?)',[(json.dumps(h,sort_keys=True),) for h in filing_headers])
    sql='INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
    unresolved=set(); unresolved_all=False
    batch=[]
    try:
        # OTH files contain millions of unrelated receipts and expenditures.
        # First identify cash-related keys on disk, then retain EVERY observed
        # representation of those keys, including later noncash amendments.
        connection.execute('CREATE TABLE relevant_keys(version_key TEXT PRIMARY KEY) WITHOUT ROWID')
        with path.open(encoding='utf-8',errors='replace') as stream:
            for number,line in enumerate(stream,1):
                fields=line.rstrip('\n\r').split('|')
                if len(fields)==21 and fields[5] in CASH_CODES:
                    batch.append((transfer_key(fields,number),))
                if len(batch)>=10000:
                    connection.executemany('INSERT OR IGNORE INTO relevant_keys VALUES (?)',batch)
                    connection.commit();batch.clear()
        if batch:
            connection.executemany('INSERT OR IGNORE INTO relevant_keys VALUES (?)',batch);batch.clear()
        with path.open(encoding='utf-8',errors='replace') as stream:
            for line in stream:
                counts['source_rows']+=1
                fields=line.rstrip('\n\r').split('|')
                if len(fields)!=21:
                    counts['malformed_rows']+=1
                    if re.fullmatch(r'C\d{8}',fields[0]):unresolved.add(fields[0])
                    else:unresolved_all=True
                    continue
                source,amend,report=fields[:3];kind=fields[5];destination=fields[15]
                # Keep all transaction types and destinations until versions are
                # resolved. An amendment can change either, or mark a memo.
                if kind in CASH_CODES:counts['cash_transfer_rows']+=1
                key=transfer_key(fields,counts['source_rows'])
                if not connection.execute('SELECT 1 FROM relevant_keys WHERE version_key=?',(key,)).fetchone():continue
                sub=fields[20];raw_date=fields[13].zfill(8)
                try:date=datetime.strptime(raw_date,'%m%d%Y').date().isoformat()
                except ValueError:date=''
                try:
                    value=Decimal(fields[14])*100
                    if not value.is_finite() or value!=value.to_integral_value():raise ValueError('Invalid cents')
                    cents=int(value)
                    if abs(cents)>9223372036854775807:raise ValueError('Amount too large')
                except (ValueError,ArithmeticError):cents=None
                transaction=fields[16]
                try:file_num=int(fields[17] or 0)
                except ValueError:file_num=0
                batch.append((key,source,destination,date,cents,kind,transaction,file_num,fields[18],report,sub,amend,line.rstrip('\n\r'),'observed'))
                if len(batch)>=10000:
                    connection.executemany(sql,batch);connection.commit();batch.clear()
        if batch:connection.executemany(sql,batch)
        connection.execute('CREATE INDEX records_version ON records(version_key)')
        connection.execute('CREATE INDEX records_edge ON records(source,destination)')
        connection.row_factory=sqlite3.Row
        from itertools import groupby
        for _,items in groupby(connection.execute('SELECT rowid,* FROM records ORDER BY version_key'),lambda r:r['version_key']):
            observed=list(items)
            # Noncash records still participate in a group containing cash.
            if not any(r['type'] in CASH_CODES for r in observed):continue
            unique={}
            for row in observed:
                if row['raw_line'] in unique:
                    connection.execute("UPDATE records SET status='duplicate' WHERE rowid=?",(row['rowid'],))
                else:unique[row['raw_line']]=row
            rows=list(unique.values()); families=defaultdict(list); ambiguous=False
            files={r['file_num'] for r in rows}
            for row in rows:
                family=row['file_num']
                if len(files)>1:
                    h=headers.get(row['file_num'],{})
                    if (h.get('committee_id')!=row['source'] or h.get('report_type')!=row['report']
                            or h.get('amendment_indicator')!=row['amendment']
                            or h.get('relationship_evidence') is False):
                        ambiguous=True;break
                    original=h.get('original_file_num')
                    if h.get('amendment_indicator')=='N' and not original:family=h['file_num']
                    elif h.get('amendment_indicator') in ('A','T') and original and original!=h['file_num']:family=original
                    else:ambiguous=True;break
                families[family].append(row)
            selected=[]
            for family in families.values():
                if len(family)==1:selected.append((family,family[0]));continue
                versions={}
                for row in family:
                    h=headers.get(row['file_num'],{})
                    number='0' if h.get('amendment_indicator')=='N' else str(h.get('amendment_number',''))
                    if not number.isdigit() or int(number) in versions:
                        ambiguous=True;break
                    versions[int(number)]=row
                if not ambiguous:selected.append((family,versions[max(versions)]))
            if ambiguous:
                counts['unresolved_version_groups']+=1
                unresolved.update(r['source'] for r in rows)
                connection.executemany("UPDATE records SET status='unresolved_version' WHERE rowid=?",[(r['rowid'],) for r in rows])
                continue
            for family,latest in selected:
                for row in family:
                    status='superseded' if row['rowid']!=latest['rowid'] else 'current'
                    if status=='current' and row['type'] in CASH_CODES:
                        invalid=False
                        for field,count in [('date','invalid_transfer_dates'),('cents','invalid_transfer_amounts')]:
                            if row[field] is None or row[field]=='':counts[count]+=1;invalid=True
                        if not re.fullmatch(r'C\d{8}',row['destination']):
                            counts['invalid_transfer_destinations']+=1;invalid=True
                        if invalid:status='unresolved_record';unresolved.add(row['source'])
                    connection.execute('UPDATE records SET status=? WHERE rowid=?',(status,row['rowid']))
        counts['latest_rows']=connection.execute("SELECT COUNT(*) FROM records WHERE status='current'").fetchone()[0]
        counts['memo_rows']=connection.execute("SELECT COUNT(*) FROM records WHERE status='current' AND memo='X'").fetchone()[0]
        counts['superseded_or_duplicate_rows']=connection.execute("SELECT COUNT(*) FROM records WHERE status IN ('superseded','duplicate')").fetchone()[0]
        counts['unresolved_rows']=connection.execute("SELECT COUNT(*) FROM records WHERE status LIKE 'unresolved_%'").fetchone()[0]
        connection.commit()
        if connection.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Transfer ledger integrity failed')
        edges=[]
        active=connection.execute("SELECT * FROM records WHERE status='current' AND type IN ('24G','24K') AND memo<>'X' ORDER BY source,destination")
        for (source,destination),items in groupby(active,lambda r:(r['source'],r['destination'])):
            rows=list(items)
            evidence=[{k:r[k] for k in ('file_num','transaction_id','sub_id','date','cents','type')} for r in rows]
            edges.append(dict(cycle=cycle,source=source,destination=destination,amount=sum(r['cents'] for r in rows)/100,
                record_count=len(rows),first_date=min(r['date'] for r in rows),last_date=max(r['date'] for r in rows),
                records=json.dumps(evidence,separators=(',',':'))))
    finally:connection.close()
    if sha(path)!=signature:raise ValueError('Transfer source changed during indexing; output withheld')
    os.replace(pending,ledger)
    result={'version':VERSION,'source_sha256':signature,'cycle':cycle,'counts':dict(counts),
            'edges':edges,'ledger_path':str(ledger.resolve()),'ledger_sha256':sha(ledger),
            'filing_headers_sha256':header_signature,'unresolved_sources':sorted(unresolved),
            'unresolved_all_sources':unresolved_all,'built_seconds':round(time.monotonic()-started,3)}
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
            output.append({**{k:v for k,v in edge.items() if k!='records'},'root':root,'depth':depth+1,'path':' > '.join((*path,destination)),'status':status})
            if status=='followed':queue.append((root,destination,depth+1,(*path,destination)))
    return output


def record_list(value):
    return json.loads(value) if isinstance(value,str) and value else value or []


def cash_identity(row):
    """A transaction ID is meaningful only inside its specific filing."""
    if not row.get('transaction_id') or not row.get('file_num'):return None
    return (str(int(row['file_num'])),row['transaction_id'],row.get('date'),row.get('cents'),row.get('type'))


def allocate(funding,edges,activity,max_depth=3,stop_nodes=(),candidate_links=None,unresolved_nodes=()):
    """Conserve each root's nonnegative funding over observed cash activity.

    This is a conditional pro-rata scenario, not traced dollars, causal benefit,
    or a lower bound. Opposition stays with the named target, never its rivals.
    """
    adjacency=defaultdict(list);terminal=defaultdict(list)
    candidate_links=candidate_links or {}
    uncertain={node:'unresolved_transfer_records' for node in unresolved_nodes}
    grouped=defaultdict(float)
    for row in activity:
        grouped[(row['source'],row['candidate'],row['direction'])]+=row['amount']
    for (source,candidate,direction),value in grouped.items():
        if value>0:terminal[source].append((candidate,direction,value))
    used=set()
    for edge in edges:
        if edge['amount']<=0:continue
        remaining=edge['amount'];source=edge['source'];destination=edge['destination']
        if destination in stop_nodes:
            candidates=candidate_links.get(destination,set())
            compatible=[r for r in activity if r['source']==source and r['direction']=='Contribution / Other'
                        and r['amount']>0 and (not candidates or r['candidate'] in candidates)]
            counterparts={}
            for row in compatible:
                if len(candidates)!=1:continue
                records=record_list(row.get('transfer_records'))
                # Records must be part of the retained aggregate, not merely
                # present somewhere in the original filings.
                if abs(sum(r['cents'] for r in records)/100-row['amount'])>.005:continue
                for r in records:
                    identity=cash_identity(r)
                    if identity and r.get('destination')==destination:
                        counterparts[identity]=r['cents']/100
            records=record_list(edge.get('records'))
            matched=0
            if records and abs(sum(r['cents'] for r in records)/100-edge['amount'])<=.005:
                for r in records:
                    identity=cash_identity(r);key=(source,destination,identity)
                    if identity in counterparts and key not in used:
                        matched+=counterparts[identity];used.add(key)
            remaining=max(0,remaining-matched)
            if (compatible and remaining>.005) or matched<-.005 or matched>edge['amount']+.005:
                # Without a record-level match we cannot tell whether these
                # are two outflows or two representations of the same one.
                uncertain[source]='unverified_candidate_transfer_overlap'
        if remaining>0:adjacency[source].append((destination,remaining))
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
            if node in uncertain:unresolved[uncertain[node]]+=amount;continue
            outgoing=adjacency[node];destinations=terminal[node]
            denominator=sum(v for _,v in outgoing)+sum(v for _,_,v in destinations)
            if denominator<=0:unresolved['no_observed_outflow']+=amount;continue
            for candidate,direction,value in destinations:allocated[candidate,direction]+=amount*value/denominator
            for destination,value in outgoing:
                portion=amount*value/denominator
                if destination in stop_nodes:unresolved['unmatched_candidate_transfer']+=portion
                elif destination in path:unresolved['cycle']+=portion
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
    parser.add_argument('--filing-header-directory',type=Path,
                        help='Optional preserved FEC header evidence; read locally, without fetching.')
    args=parser.parse_args()
    headers=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(args.filing_header_directory.glob('*.json'))
             if not p.name.endswith('.review.json')] if args.filing_header_directory else []
    for cycle in args.cycles:
        index=transfer_index(args.directory/f'oth{str(cycle)[-2:]}'/'itoth.txt',cycle,headers)
        publish_index(args.directory/f'oth{str(cycle)[-2:]}',index)
        print(json.dumps({'cycle':cycle,'counts':index['counts'],'edges':len(index['edges']),'seconds':index['built_seconds']}),flush=True)


if __name__=='__main__':main()
