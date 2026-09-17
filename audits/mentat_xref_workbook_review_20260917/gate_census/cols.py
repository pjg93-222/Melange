import sqlite3, os

BASE = 'C:/Users/pgoff/Mentat/mentat/.cache/receipt-metadata-repair-20260910'
dbs = [(d, BASE + '/' + d + '/mentat.db') for d in sorted(os.listdir(BASE))]
dbs.append(('banking',
            'C:/Users/pgoff/Mentat/mentat/.cache/report-repairs/banking-20260910/data/mentat.db'))

WANT = ['contributor_street_1', 'contributor_street_2', 'receipt_type_full',
        'filing_form', 'line_number', 'line_number_label', 'memo_text',
        'memo_code', 'memoed_subtotal', 'back_reference_transaction_id',
        'back_reference_schedule_name', 'receipt_type', 'file_num',
        'report_year', 'report_type']

for slug, p in dbs:
    con = sqlite3.connect('file:' + p + '?mode=ro', uri=True)
    for t in ('contributions', 'corporate_giving'):
        have = {r[1] for r in con.execute('PRAGMA table_info(%s)' % t)}
        missing = [c for c in WANT if c not in have]
        print('%-30s %-18s missing=%s' % (slug, t, missing if missing else 'none'))
    con.close()
