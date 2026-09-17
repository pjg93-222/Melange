import sqlite3, csv, os

OUT = os.path.dirname(os.path.abspath(__file__))
DB = ('C:/Users/pgoff/Mentat/mentat/.cache/receipt-metadata-repair-20260910/'
      'crypto/mentat.db')

with open(os.path.join(OUT, 'crypto_refused.csv'), newline='',
          encoding='utf-8-sig') as f:
    ids = [r['sub_id'] for r in csv.DictReader(f)
           if not r['line_number'].strip() and not r['normalized_description'].strip()]

F = ['sub_id', 'contribution_receipt_date', 'contribution_receipt_amount',
     'entity_type', 'contributor_name', 'committee_id', 'committee_name',
     'receipt_type_full', 'memo_text', 'memo_code', 'filing_form',
     'line_number', 'transaction_id', 'back_reference_transaction_id',
     'back_reference_schedule_name', 'is_memo_leg', 'memoed_subtotal',
     'company', 'pdf_url']

con = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
rows = []
for t in ('contributions', 'corporate_giving'):
    have = {r[1] for r in con.execute('PRAGMA table_info(%s)' % t)}
    sel = ', '.join(c if c in have else "'' AS " + c for c in F)
    q = 'SELECT %s FROM %s WHERE sub_id IN (%s)' % (
        sel, t, ','.join('?' * len(ids)))
    for r in con.execute(q, ids):
        rows.append(dict(zip(F, ['' if v is None else str(v) for v in r])))
con.close()

rows.sort(key=lambda r: -float(r['contribution_receipt_amount'] or 0))
total = sum(float(r['contribution_receipt_amount'] or 0) for r in rows)
print('rows: %d   total: $%s\n' % (len(rows), '{:,.2f}'.format(total)))
for i, r in enumerate(rows, 1):
    ind = r['entity_type'].strip().upper() == 'IND'
    print('--- row %d%s ---' % (i, '  [INDIVIDUAL - redacted]' if ind else ''))
    if ind:
        for k in ('contribution_receipt_amount', 'contribution_receipt_date',
                  'committee_id', 'committee_name', 'receipt_type_full',
                  'memo_text', 'memo_code'):
            print('  %-30s %s' % (k, r[k]))
        continue
    for k in F:
        print('  %-30s %s' % (k, r[k] if r[k] != '' else '(empty)'))

with open(os.path.join(OUT, 'crypto_blankline_four.csv'), 'w', newline='',
          encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=F)
    w.writeheader()
    w.writerows(rows)
print('\nwrote crypto_blankline_four.csv')
