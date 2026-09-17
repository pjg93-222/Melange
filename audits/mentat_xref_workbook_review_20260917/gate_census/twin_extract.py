"""Extract every DISTINCT classifier-input tuple across all 8 databases, so the
R gate's fec_receipt_role() and the Python twin's receipt_role() can be compared
over the complete classification space rather than a sample. Read-only."""
import sqlite3, os, csv

OUT = os.path.dirname(os.path.abspath(__file__))
BASE = 'C:/Users/pgoff/Mentat/mentat/.cache/receipt-metadata-repair-20260910'
TARGETS = [
    ('banking', 'Banking',
     'C:/Users/pgoff/Mentat/mentat/.cache/report-repairs/banking-20260910/data/mentat.db'),
    ('community_banks', 'Community Banks', BASE + '/community_banks/mentat.db'),
    ('credit_arms', 'Credit Arms', BASE + '/credit_arms/mentat.db'),
    ('credit_union', 'Credit Union', BASE + '/credit_union/mentat.db'),
    ('crypto', 'Crypto', BASE + '/crypto/mentat.db'),
    ('fintech', 'Fintech', BASE + '/fintech/mentat.db'),
    ('property_casualty_insurance', 'Property & Casualty Insurance',
     BASE + '/property_casualty_insurance/mentat.db'),
    ('telecom', 'Telecom', BASE + '/telecom/mentat.db'),
]

FIELDS = ['filing_form', 'line_number', 'receipt_type_full', 'memo_text',
          'memo_code', 'memoed_subtotal', 'is_memo_leg']

seen = set()
for slug, label, path in TARGETS:
    con = sqlite3.connect('file:' + path + '?mode=ro', uri=True)
    for table in ('contributions', 'corporate_giving'):
        have = {r[1] for r in con.execute('PRAGMA table_info(%s)' % table)}
        sel = ', '.join(f if f in have else "NULL AS " + f for f in FIELDS)
        q = 'SELECT DISTINCT %s FROM %s WHERE industry = ?' % (sel, table)
        for row in con.execute(q, (label,)):
            seen.add(tuple('' if v is None else str(v) for v in row))
    con.close()
    print('%-30s cumulative distinct tuples=%d' % (slug, len(seen)))

rows = sorted(seen)
with open(os.path.join(OUT, 'twin_inputs.csv'), 'w', newline='',
          encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(FIELDS)
    w.writerows(rows)
print('wrote twin_inputs.csv with', len(rows), 'rows')
