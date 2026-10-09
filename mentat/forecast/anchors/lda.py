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
import math

SERIES = {'income_total': 'Outside-firm fees (LDA income_total)', 'expenses_total': 'In-house expenses (LDA expenses_total)'}
NOTE = ('Melange LDA sector level, nominal dollars. income_total = fees paid to outside firms; expenses_total = the client\'s own in-house '
        'spending. The two series are different flows and are never added. The sector roster is wider than Mentat\'s ten companies.')


def read_sector_rows(path):
    with open(path, encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

# --- in-year nowcast (owner rulings 2026-10-08) -------------------------------------------------------------------------------
# pred_year = O + (1 - s) * B   (the PAC panel's R8_REMAINING form; not the pace O / s)
#   O  filed so far this year through the latest complete quarter cut k, B  the prior full-year total,
#   s  geometric mean of the share filed by the same cut k in up to the 3 prior years (each year's final quarterly figures; at least 1 year).
# Blind-test pool: the sectors whose quarterly series are complete and stable enough to be tested (crypto is left out: its 2021-2022 years are too thin).
NOWCAST_POOL = ('bank', 'credit_union', 'telecom', 'fintech')
NOWCAST_WINDOW = 3
NOWCAST_CUTS = (1, 2, 3)


def quarter_table(rows, sector, series):
    """{year: {1..4: amount}} of the quarters with filings (a quarter without a filing is not a figure)."""
    out = {}
    for r in rows:
        if r['sector'] == sector and r['period'] in ('Q1', 'Q2', 'Q3', 'Q4') and int(r['filings'] or 0) > 0:
            out.setdefault(int(r['year']), {})[int(r['period'][1])] = float(r[series])
    return out


def nowcast(quarters, year, cut, window=NOWCAST_WINDOW):
    """The remaining-share nowcast of `year` at quarter cut `cut` from {year: {quarter: amount}}, or None when the prior year or every prior share is missing."""
    mine = quarters.get(year, {})
    complete = lambda y: all(i in quarters.get(y, {}) for i in (1, 2, 3, 4))
    if not complete(year - 1) or not all(i in mine for i in range(1, cut + 1)):
        return None
    shares = []
    for y in range(year - window, year):
        if complete(y):
            total, got = sum(quarters[y].values()), sum(quarters[y][i] for i in range(1, cut + 1))
            if total > 0 and got > 0:
                shares.append((y, got / total))
    if not shares:
        return None
    s = math.exp(sum(math.log(v) for _y, v in shares) / len(shares))
    observed, prior_total = sum(mine[i] for i in range(1, cut + 1)), sum(quarters[year - 1].values())
    return {'year': year, 'through_quarter': 'Q' + str(cut), 'observed': observed, 'prior_total': prior_total, 'share': s,
            'share_years': [y for y, _v in shares], 'shares': [v for _y, v in shares], 'point': observed + (1. - s) * prior_total}


def conformal_quantile(values, q):
    """Split-conformal quantile of |values|: the ceil((n + 1) q)-th smallest; None when n is too small for it."""
    a = sorted(abs(v) for v in values)
    k = math.ceil((len(a) + 1) * q)
    return a[k - 1] if 0 < k <= len(a) else None


def nowcast_errors(rows, pool=NOWCAST_POOL):
    """Pooled blind errors of the nowcast, log(pred / actual), by quarter cut: every complete year with a complete prior year, both series, every pool sector.
    -> {'pool', 'series', 'targets', 'by_cut': {'1'|'2'|'3': {'n', 'q80', 'max'}}} (q80 = split-conformal 80th percentile of |error|, max = the largest blind miss), or None."""
    errors, targets = {c: [] for c in NOWCAST_CUTS}, set()
    for sector in pool:
        for sid in SERIES:
            q = quarter_table(rows, sector, sid)
            for year in sorted(y for y in q if len(q[y]) == 4):
                for cut in NOWCAST_CUTS:
                    n = nowcast(q, year, cut)
                    if n:
                        errors[cut].append(math.log(n['point'] / sum(q[year].values())))
                        targets.add(year)
    by_cut = {str(c): {'n': len(e), 'q80': conformal_quantile(e, .8), 'max': max((abs(v) for v in e), default=None)} for c, e in errors.items()}
    if any(row['q80'] is None for row in by_cut.values()):          # too few blind tests for an 80th percentile: no bands rather than made-up ones
        return None
    return {'pool': list(pool), 'series': list(SERIES), 'targets': sorted(targets), 'by_cut': by_cut}


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
                if last in NOWCAST_CUTS:
                    partial['nowcast'] = nowcast(quarter_table(mine, sector, sid), year, last)
                through = date(year, last * 3, calendar.monthrange(year, last * 3)[1]).isoformat()
        series[sid] = {'label': label, 'annual': dict(sorted(annual.items())), 'partial': partial}
    if through is None:
        last_year = max(int(y) for y in series['income_total']['annual'])
        through = date(last_year, 12, 31).isoformat()
    # The roster counts Melange prints under each sector card (its `annual` rows, the partial year's included): distinct organizations and named lobbyists.
    counts = {r['year']: {'organizations': int(r['distinct_organizations']), 'lobbyists': int(r['distinct_named_lobbyists'])}
              for r in mine if r['period'] == 'annual' and (r.get('distinct_organizations') or '').strip() and (r.get('distinct_named_lobbyists') or '').strip()}
    return {'series': series, 'through': through, 'counts': dict(sorted(counts.items()))}
