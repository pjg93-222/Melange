import collections,json,sqlite3
from pathlib import Path
root=Path(r'C:\Users\pgoff\Mentat\mentat\state\contribution-analytics')
for path in sorted(root.glob('*.sqlite')):
    try:
        db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
        db.execute('PRAGMA query_only=ON')
        meta=json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
        print(json.dumps({'index':path.name,'mtime':path.stat().st_mtime,'manifest':meta}))
        if 'Banking' not in meta.get('provenance',{}).get('workbook',''):
            db.close();continue
        for title,sql in [
            ('status','SELECT decision_status,COUNT(*),SUM(receipt_cents),SUM(original_cents),SUM(supported_cents),SUM(raw_cents) FROM facts GROUP BY decision_status'),
            ('bucket','SELECT funding_source,COUNT(*),SUM(receipt_cents),SUM(original_cents),SUM(original_cents-receipt_cents) FROM facts GROUP BY funding_source'),
            ('role','SELECT receipt_role,COUNT(*),SUM(receipt_cents),SUM(original_cents),SUM(original_cents-receipt_cents) FROM facts GROUP BY receipt_role'),
            ('cycle','SELECT cycle,COUNT(*),SUM(receipt_cents),SUM(original_cents),SUM(original_cents-receipt_cents) FROM facts GROUP BY cycle'),
            ('receipt_absent','SELECT (receipt_cents=0),COUNT(*),SUM(receipt_cents),SUM(original_cents),SUM(original_cents-receipt_cents) FROM facts WHERE original_cents<>receipt_cents GROUP BY (receipt_cents=0)'),
            ('party','SELECT party,COUNT(*),SUM(receipt_cents),SUM(original_cents) FROM facts GROUP BY party'),
            ('big_delta','SELECT source_id,company,contributor,raw_cents,receipt_cents,original_cents,decision_status,receipt_role,reasons FROM facts WHERE original_cents<>receipt_cents ORDER BY ABS(original_cents-receipt_cents) DESC LIMIT 12'),
        ]:
            try: print(json.dumps({'index':path.name,'table':title,'rows':db.execute(sql).fetchall()}))
            except sqlite3.OperationalError as e:print(json.dumps({'error':str(e)}))
        reasons=collections.defaultdict(lambda:[0,0,0,0])
        for receipt,original,raw,reasons_json in db.execute('SELECT receipt_cents,original_cents,raw_cents,reasons FROM facts WHERE original_cents<>receipt_cents'):
            for reason in json.loads(reasons_json):
                x=reasons[reason];x[0]+=1;x[1]+=receipt;x[2]+=original;x[3]+=original-receipt
        print(json.dumps({'index':path.name,'table':'delta_reason_memberships_overlap','rows':sorted(reasons.items(),key=lambda x:abs(x[1][-1]),reverse=True)}))
        db.close()
    except Exception as e:print(json.dumps({'index':path.name,'error':str(e)}))
