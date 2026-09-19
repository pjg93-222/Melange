import collections,json,sqlite3
from pathlib import Path
p=Path(r'C:\Users\pgoff\Mentat\mentat\state\cross-reference\20260912T204736-ed3b2a351279')
r=json.loads((p/'report.json').read_text(encoding='utf-8-sig'))
print(json.dumps({'keys':list(r)}),flush=True)
for key in r:
    if key in ('changes','reviews','review_queue','decisions','links','companies'):continue
    text=json.dumps(r[key]);print(json.dumps({'key':key,'value':r[key] if len(text)<18000 else text[:18000]}),flush=True)
db=sqlite3.connect((p/'ledger.sqlite').as_uri()+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON')
for table in ['decisions','source_records']:
    print(json.dumps({'schema':table,'columns':db.execute('PRAGMA table_info('+table+')').fetchall()}),flush=True)
counts=collections.Counter();roles=collections.defaultdict(lambda:[0,0,0,0]);buckets=collections.defaultdict(lambda:[0,0,0,0]);reasons=collections.defaultdict(lambda:[0,0,0,0]);diffs=[]
for raw, in db.execute('SELECT payload_json FROM decisions'):
    d=json.loads(raw);receipt=d['baseline_cents'];original=d['counted_cents'];delta=original-receipt
    counts[d['status']]+=1
    for key,target in [(d['receipt_role'],roles),(d['bucket'],buckets)]:
        x=target[key];x[0]+=1;x[1]+=receipt;x[2]+=original;x[3]+=delta
    if delta:
        for reason in d['reasons']:
            x=reasons[reason];x[0]+=1;x[1]+=receipt;x[2]+=original;x[3]+=delta
        if delta>1000000:diffs.append({k:d.get(k) for k in ['source_id','company','baseline_cents','counted_cents','bucket','receipt_role','status','reasons']})
print(json.dumps({'statuses':counts,'roles':roles,'buckets':buckets,'delta_reason_memberships_overlap':reasons,'positive_deltas_over_10000':sorted(diffs,key=lambda d:d['counted_cents']-d['baseline_cents'],reverse=True)[:25]}),flush=True)
