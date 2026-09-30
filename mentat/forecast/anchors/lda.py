"""Melange LDA lobbying levels by sector (read-only).

Source: the Melange repo's `fec/lobbying/sector_spend.py` output `sector_spend.csv` (default
%LOCALAPPDATA%\\Melange\\lda_rebuild\\derived\\sector_spend\\sector_spend.csv). Two series are measured and NEVER added:
`income_total` (fees paid to outside registrants) and `expenses_total` (the client's own in-house expense). Both are nominal dollars.
The level depends on the roster the Melange code chose (banks: 86-100 organisations, credit unions: 19-26), so the console applies a
relative change to it and never treats it as the Mentat roster's own spending. The bank sector is the TOTAL, not a bank tier.
"""
import csv
from datetime import date
import calendar

SERIES = {'income_total': 'Outside-firm fees (LDA income_total)', 'expenses_total': 'In-house expenses (LDA expenses_total)'}
NOTE = ('Melange LDA sector level, nominal dollars. income_total = fees paid to outside firms; expenses_total = the client\'s own in-house '
        'spending. The two series are different flows and are never added. The sector roster is wider than Mentat\'s ten companies.')


def read_sector_rows(path):
    with open(path, encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def sector_levels(rows, sector):
    """Annual + partial-year levels of one sector, both series. None when the sector has no rows."""
    mine = [r for r in rows if r['sector'] == sector]
    if not mine:
        return None
    series, through = {}, None
    partial_years = sorted({int(r['year']) for r in mine if r['is_partial_year'].lower() == 'true'})
    for sid, label in SERIES.items():
        annual = {}
        for r in mine:
            if r['period'] == 'annual' and r['is_partial_year'].lower() != 'true':
                annual[r['year']] = float(r[sid])
        partial = None
        if partial_years:
            year = partial_years[-1]
            quarters = {r['period']: float(r[sid]) for r in mine
                        if int(r['year']) == year and r['period'] in ('Q1', 'Q2', 'Q3', 'Q4') and int(r['filings'] or 0) > 0}
            if quarters:
                last = max(int(q[1]) for q in quarters)
                partial = {'year': year, 'through_quarter': 'Q' + str(last), 'quarters': dict(sorted(quarters.items())),
                           'total': round(sum(quarters.values()), 2)}
                through = date(year, last * 3, calendar.monthrange(year, last * 3)[1]).isoformat()
        series[sid] = {'label': label, 'annual': dict(sorted(annual.items())), 'partial': partial}
    if through is None:
        last_year = max(int(y) for y in series['income_total']['annual'])
        through = date(last_year, 12, 31).isoformat()
    return {'series': series, 'through': through}
