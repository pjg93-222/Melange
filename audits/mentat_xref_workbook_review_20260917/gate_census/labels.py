import sqlite3, os, sys

BASE = 'C:/Users/pgoff/Mentat/mentat/.cache/receipt-metadata-repair-20260910'
dbs = [(d, BASE + '/' + d + '/mentat.db') for d in sorted(os.listdir(BASE))]
dbs.append(('banking@report-repairs',
            'C:/Users/pgoff/Mentat/mentat/.cache/report-repairs/banking-20260910/data/mentat.db'))

for slug, p in dbs:
    if not os.path.exists(p):
        print(slug.ljust(28), 'MISSING', p)
        continue
    con = sqlite3.connect('file:' + p + '?mode=ro', uri=True)
    parts = []
    for t in ('contributions', 'corporate_giving'):
        try:
            rows = con.execute(
                'SELECT industry, COUNT(*) FROM %s GROUP BY industry ORDER BY 2 DESC' % t
            ).fetchall()
            parts.append('%s=%s' % (t, rows))
        except Exception as e:
            parts.append('%s=ERR(%s)' % (t, e))
    print(slug.ljust(28), ' | '.join(parts))
    con.close()
