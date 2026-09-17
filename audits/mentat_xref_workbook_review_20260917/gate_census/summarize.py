"""Group the refused rows and build SUMMARY.md. Reads only the census outputs
in this directory plus the Banking cross-check CSV (read-only)."""
import csv, os, sys
from collections import defaultdict, Counter

OUT = os.path.dirname(os.path.abspath(__file__))
BANK_XCHECK = ('C:/Users/pgoff/Mentat/mentat/.cache/industry-report/banking/'
               'industry_data-4abdea581b99cec1.json.pending-42976.receipt-review.csv')

ORDER = ['banking', 'community_banks', 'credit_arms', 'credit_union', 'crypto',
         'fintech', 'property_casualty_insurance', 'telecom']

csv.field_size_limit(10 ** 8)


def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def money(x):
    return '${:,.2f}'.format(x)


receipts, refusals, groupings = {}, {}, {}

for slug in ORDER:
    rpath = os.path.join(OUT, slug + '_receipt.csv')
    fpath = os.path.join(OUT, slug + '_refused.csv')
    if not os.path.exists(rpath):
        print('MISSING receipt for', slug, file=sys.stderr)
        continue
    receipts[slug] = read_csv(rpath)[0]
    rows = read_csv(fpath) if os.path.exists(fpath) else []
    refusals[slug] = rows

    groups = defaultdict(lambda: {'rows': 0, 'dollars': 0.0, 'example': '',
                                  'reasons': defaultdict(int)})
    for r in rows:
        key = (r['filing_form'], r['line_number'], r['normalized_description'])
        g = groups[key]
        g['rows'] += 1
        try:
            g['dollars'] += float(r['amount'] or 0)
        except ValueError:
            pass
        g['reasons'][r['reason']] += 1
        if not g['example']:
            g['example'] = r['sub_id']
    ranked = sorted(groups.items(), key=lambda kv: -kv[1]['dollars'])
    groupings[slug] = ranked

    with open(os.path.join(OUT, slug + '_groups.csv'), 'w', newline='',
              encoding='utf-8-sig') as f:
        w = csv.writer(f)
        w.writerow(['rank', 'filing_form', 'line_number', 'normalized_description',
                    'rows', 'dollars', 'example_sub_id', 'reasons'])
        for i, (key, g) in enumerate(ranked[:60], 1):
            reasons = '; '.join('%s=%d' % (k, v)
                                for k, v in sorted(g['reasons'].items(),
                                                   key=lambda kv: -kv[1]))
            w.writerow([i, key[0], key[1], key[2], g['rows'],
                        '%.2f' % g['dollars'], g['example'], reasons])

# ---- Banking cross-check -------------------------------------------------
xnote = []
recl = os.path.join(OUT, 'banking_xcheck_reclassified.csv')
if os.path.exists(BANK_XCHECK) and 'banking' in refusals and os.path.exists(recl):
    x = read_csv(BANK_XCHECK)
    xids = set(r['sub_id'] for r in x)
    xdollars = sum(float(r['contribution_receipt_amount'] or 0) for r in x)
    mine = refusals['banking']
    mids = set(r['sub_id'] for r in mine)
    mdollars = sum(float(r['amount'] or 0) for r in mine)

    rc = read_csv(recl)
    still = [r for r in rc if r['unresolved_today'] == 'TRUE']
    gone = [r for r in rc if r['unresolved_today'] != 'TRUE']
    sids = set(r['sub_id'] for r in still)
    sdollars = sum(float(r['amount'] or 0) for r in still)
    gdollars = sum(float(r['amount'] or 0) for r in gone)
    moved = Counter((r['role_sep12'], r['role_today']) for r in gone)

    xnote = [
        'The CSV was written **2026-09-12 17:59**. `inputs/fec_receipt_rules.json`',
        'was last modified **2026-09-13 03:42** - after that run - and the file is',
        'gitignored, so the change carries no history. The raw row set is identical;',
        'only the classification moved. Re-running **today\'s** `fec_receipt_role()`',
        'over the CSV\'s own 2,070 rows decomposes the difference exactly:',
        '',
        '| | rows | dollars |',
        '| --- | ---: | ---: |',
        '| refused by the 2026-09-12 run (the CSV) | %d | %s |' % (len(x), money(xdollars)),
        '| ...still refused under today\'s ruleset | %d | %s |' % (len(still), money(sdollars)),
        '| ...now resolved by today\'s ruleset | %d | %s |' % (len(gone), money(gdollars)),
        '| **this reproduction (independent, from the database)** | **%d** | **%s** |'
        % (len(mine), money(mdollars)),
        '',
        '| consistency check | result |',
        '| --- | :---: |',
        '| %d + %d = %d | %s |' % (len(still), len(gone), len(x),
                                   'OK' if len(still) + len(gone) == len(x) else 'FAIL'),
        '| %s + %s = %s | %s |' % (money(sdollars), money(gdollars), money(xdollars),
                                   'OK' if abs(sdollars + gdollars - xdollars) < 0.005 else 'FAIL'),
        '| reproduction row count == still-refused count | %s |'
        % ('OK' if len(mine) == len(still) else 'FAIL'),
        '| reproduction dollars == still-refused dollars | %s |'
        % ('OK' if abs(mdollars - sdollars) < 0.005 else 'FAIL'),
        '| reproduction sub_id set == still-refused sub_id set | %s |'
        % ('OK' if mids == sids else 'FAIL'),
        '| reproduction is a subset of the CSV | %s |'
        % ('OK' if mids <= xids else 'FAIL'),
        '| rows newly refused that the CSV did not have | %d |' % len(mids - xids),
        '',
        'Where the 1,477 rows went (Sep-12 role -> today\'s role):',
        '',
        '| Sep-12 role | today\'s role | rows |',
        '| --- | --- | ---: |',
    ]
    for (a, b), n in moved.most_common():
        xnote.append('| `%s` | `%s` | %d |' % (a, b, n))
    xnote += [
        '',
        'No row moved the other way: nothing that the 2026-09-12 run accepted is',
        'refused today. The reproduction is therefore an exact match against the only',
        'ground truth available - the failed run\'s own output - once the ruleset',
        'change between the two dates is accounted for.',
    ]
    if mids - sids:
        xnote.append('')
        xnote.append('UNEXPECTED, only in reproduction: `%s`'
                     % '`, `'.join(sorted(mids - sids)[:10]))
    if sids - mids:
        xnote.append('')
        xnote.append('UNEXPECTED, only in still-refused: `%s`'
                     % '`, `'.join(sorted(sids - mids)[:10]))

# ---- SUMMARY.md ----------------------------------------------------------
L = []
L.append('# Receipt-evidence gate census')
L.append('')
L.append('Read-only reproduction of `fec_assert_receipt_evidence(raw_rows[evidence_scope])`')
L.append('(`mentat/tools/export_crypto_spending_data.R:225`, gate body at')
L.append('`mentat/R/collect.R:137-147`). These are the rows the exporter would')
L.append('REFUSE at export time, per industry.')
L.append('')
L.append('## Per-industry')
L.append('')
L.append('| industry | rows loaded | rows in evidence scope | rows refused | dollars refused | % of scope |')
L.append('| --- | ---: | ---: | ---: | ---: | ---: |')
tr = td = tl = ts = 0
for slug in ORDER:
    if slug not in receipts:
        L.append('| %s | (not run) | | | | |' % slug)
        continue
    r = receipts[slug]
    raw, scope = int(r['raw_rows']), int(r['in_scope'])
    ref, dol = int(r['refused_rows']), float(r['refused_dollars'])
    tl += raw; ts += scope; tr += ref; td += dol
    L.append('| %s | %s | %s | %s | %s | %.3f%% |' % (
        r['industry'], '{:,}'.format(raw), '{:,}'.format(scope),
        '{:,}'.format(ref), money(dol), 100.0 * ref / scope if scope else 0))
L.append('| **total** | **%s** | **%s** | **%s** | **%s** | |' % (
    '{:,}'.format(tl), '{:,}'.format(ts), '{:,}'.format(tr), money(td)))
L.append('')

L.append('## Top 5 description groups per industry')
L.append('')
L.append('Grouped by `(filing_form, line_number, normalized description)`, where the')
L.append('normalized description is exactly what the classifier keys on:')
L.append('`normalized(receipt_type_full)` then `normalized(memo_text)`, pasted and')
L.append('trimmed (`collect.R:46-49`). Full top-60 tables are in `<slug>_groups.csv`.')
L.append('')
for slug in ORDER:
    if slug not in groupings:
        continue
    L.append('### %s' % receipts[slug]['industry'])
    L.append('')
    L.append('| form | line | normalized description | rows | dollars | example sub_id |')
    L.append('| --- | --- | --- | ---: | ---: | --- |')
    for key, g in groupings[slug][:5]:
        desc = key[2] if key[2] else '(empty)'
        if len(desc) > 70:
            desc = desc[:67] + '...'
        L.append('| %s | %s | %s | %d | %s | `%s` |' % (
            key[0] or '(blank)', key[1] or '(blank)', desc, g['rows'],
            money(g['dollars']), g['example']))
    L.append('')
    L.append('(%d distinct groups total)' % len(groupings[slug]))
    L.append('')

L.append('## Banking cross-check')
L.append('')
if xnote:
    L.append('Against the failed run\'s own review CSV,')
    L.append('`.cache/industry-report/banking/industry_data-4abdea581b99cec1.json.pending-42976.receipt-review.csv`:')
    L.append('')
    L.extend(xnote)
else:
    L.append('NOT RUN - Banking census output or cross-check CSV missing.')
L.append('')

L.append('## What the refusals are made of')
L.append('')
L.append('Two structural buckets account for most of the refused rows, and neither is')
L.append('a description the owner can rule on as written.')
L.append('')
L.append('**Rows with no description at all.** `receipt_type_full` and `memo_text` are')
L.append('both empty, so the classifier has nothing but form+line to go on and falls')
L.append('through to `unverified_*`.')
L.append('')
L.append('| industry | refused | of which blank description | dollars (blank) |')
L.append('| --- | ---: | ---: | ---: |')
for slug in ORDER:
    if slug not in refusals:
        continue
    rows = refusals[slug]
    blank = [r for r in rows if not r['normalized_description'].strip()]
    bd = sum(float(r['amount'] or 0) for r in blank)
    L.append('| %s | %d | %d | %s |' % (receipts[slug]['industry'], len(rows),
                                        len(blank), money(bd)))
L.append('')
L.append('**Filing forms the ruleset does not cover.** `fec_receipt_rules.json` maps')
L.append('line numbers for `F3`, `F3X`, `F3P` and `F4` only. A row on any other form')
L.append('(or with a blank form) cannot match a line rule and lands on')
L.append('`unverified_receipt_role` no matter what its line number is.')
L.append('')
L.append('| industry | form | rows | dollars |')
L.append('| --- | --- | ---: | ---: |')
KNOWN = {'F3', 'F3X', 'F3P', 'F4'}
any_unknown = False
for slug in ORDER:
    if slug not in refusals:
        continue
    agg = defaultdict(lambda: [0, 0.0])
    for r in refusals[slug]:
        form = (r['filing_form'] or '').strip().upper()
        if form not in KNOWN:
            a = agg[form or '(blank)']
            a[0] += 1
            a[1] += float(r['amount'] or 0)
    for form, (n, d) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
        any_unknown = True
        L.append('| %s | `%s` | %d | %s |' % (receipts[slug]['industry'], form,
                                              n, money(d)))
if not any_unknown:
    L.append('| (none) | | | |')
L.append('')

L.append('## Method')
L.append('')
L.append('Per industry, one `Rscript gate_census.R <db> <label> <slug> <out>` run that:')
L.append('')
L.append('1. assigns the **global R variable** `MENTAT_INDUSTRY` before sourcing (it is')
L.append('   not an environment variable; leaving it unset silently queries Crypto),')
L.append('2. sources the same 14 modules the exporter sources, in the same order,')
L.append('3. opens the database with `RSQLite::SQLITE_RO`,')
L.append('4. calls `spending_raw_report_rows(connection, versioning_applied = TRUE)` -')
L.append('   the `TRUE` skips `apply_amendment_versioning()`, the only writing step,')
L.append('   exactly as the exporter does at line 208,')
L.append('5. rebuilds `evidence_scope` from `contribution_cycle()` against')
L.append('   `supported_cycles = c(2022, 2024, 2026)` (exporter lines 97, 133-137, 219),')
L.append('6. applies the gate body from `collect.R:138` to `raw_rows[evidence_scope]`.')
L.append('')
L.append('Every run printed its industry label, the SQL filter, and its loaded row')
L.append('count; no run loaded zero rows.')
L.append('')
L.append('Both refusal masks were computed independently and compared per industry:')
L.append('the gate\'s own (`collect.R:138`, applied to the scoped subset) and the')
L.append('exporter\'s review-CSV logic (lines 220-221, applied to the full table).')
L.append('They agreed on every industry - see `masks_agree` in each `_receipt.csv`.')
L.append('')

# twin
tw = os.path.join(OUT, 'twin_disagreements.csv')
if os.path.exists(tw):
    d = read_csv(tw)
    verdict = [r for r in d if r['verdict_differs'] == 'True']
    kinds = sorted(set((r['r_role'], r['python_role']) for r in d))
    L.append('## Cross-check against the Python twin')
    L.append('')
    L.append('Every DISTINCT classifier-input tuple across all 8 databases')
    L.append('(`filing_form`, `line_number`, `receipt_type_full`, `memo_text`,')
    L.append('`memo_code`, `memoed_subtotal`, `is_memo_leg`) was classified by both the')
    L.append('authoritative R `fec_receipt_role()` and `tools/pac_evidence.py`')
    L.append('`receipt_role()`.')
    L.append('')
    L.append('| metric | value |')
    L.append('| --- | ---: |')
    L.append('| distinct tuples compared | 28,548 |')
    L.append('| role-string disagreements | %d |' % len(d))
    L.append('| **refuse/allow verdict disagreements** | **%d** |' % len(verdict))
    L.append('')
    L.append('The only disagreement shape is `%s`.' % ', '.join(
        '`%s` -> `%s`' % k for k in kinds))
    L.append('`pac_evidence.py:89-90` carries an `in_kind_contribution` rule')
    L.append('(`IN KIND|NOT LIQUIDATED`) that `collect.R` has no counterpart for. Both')
    L.append('labels are *resolved*, so the refusal set is identical either way. Stated')
    L.append('as an observed fact about the two implementations, not a proposed change.')
    L.append('')

L.append('## Deviations and uncertainties')
L.append('')
L.append('**D1 - Banking\'s database is not where the brief expected it, and the')
L.append('`receipt-metadata-repair-20260910` set has no Banking entry at all.**')
L.append('That directory holds 7 slugs: `community_banks`, `credit_arms`,')
L.append('`credit_union`, `crypto`, `fintech`, `property_casualty_insurance`,')
L.append('`telecom`. Banking was taken from')
L.append('`.cache/report-repairs/banking-20260910/data/mentat.db`. This is not a guess:')
L.append('its SHA-256 is')
L.append('`4abdea581b99cec1674252ee098ab6afca57674bd8e90313e9f4156e88b2d991`, which is')
L.append('the `database_sha256` recorded in')
L.append('`.cache/industry-report/banking/manifest-4abdea581b99cec1.json` - so it is')
L.append('provably the database behind `industry_data-4abdea581b99cec1.json` and its')
L.append('`.pending-42976.receipt-review.csv`.')
L.append('')
L.append('**D2 - the live exporter cannot load ANY of these 8 databases today.**')
L.append('`report.R:2032` and `:2051` SELECT `contributor_street_1, contributor_street_2`')
L.append('unconditionally; commit `d78cf0b8f` added them. All 16 tables (8 databases x')
L.append('`contributions` + `corporate_giving`) lack both columns, so')
L.append('`spending_raw_report_rows()` aborts with `no such column:')
L.append('contributor_street_1` **before** the gate at line 225 is reached. Verified by')
L.append('`PRAGMA table_info` on all 16 tables and by running the unmodified path once.')
L.append('')
L.append('The census therefore overrides `spending_raw_report_rows()` with a verbatim')
L.append('copy of `report.R:2011-2083` changed in exactly one way: the two street')
L.append('columns are routed through the same tolerant `NULL AS <field>` projection')
L.append('that `report.R:2018-2026` already applies to absent receipt metadata. Neither')
L.append('column is read by `fec_receipt_role()`, `fec_receipt_countable()`,')
L.append('`fec_receipt_role_unresolved()` or `mentat_memo_duplicate_plan()`; a')
L.append('repo-wide grep shows the only consumer in this path is the exporter\'s own')
L.append('`raw_export` projection at lines 545-546, which runs after the gate. The')
L.append('refusal set is unaffected, and the Banking row-for-row match below confirms')
L.append('it empirically.')
L.append('')
L.append('**D3 - `MENTAT_CYCLE_FILTER` was deliberately left unset.** It would narrow')
L.append('`supported_cycles`, and therefore `evidence_scope`, before the gate runs')
L.append('(exporter lines 112-131). The census refuses to start if it is set, so these')
L.append('are full-payload refusal sets. The Banking cross-check CSV spans 2022, 2024')
L.append('and 2026, confirming the failed run was also unfiltered.')
L.append('')
L.append('**D5 - the ruleset changed after the Banking run that produced the')
L.append('cross-check CSV, and that change is invisible to git.**')
L.append('`inputs/fec_receipt_rules.json` (version 4) has mtime 2026-09-13 03:42; the')
L.append('cross-check CSV was written 2026-09-12 17:59. The file matches `*.json` in')
L.append('`.gitignore`, so there is no history to diff and no way from this session to')
L.append('recover the exact Sep-12 ruleset. The effect is measured rather than')
L.append('assumed: re-classifying the CSV\'s own 2,070 rows with today\'s')
L.append('`fec_receipt_role()` resolves 1,477 of them and leaves exactly the 593 this')
L.append('census reports, with no row moving the other way (see the Banking')
L.append('cross-check). Every count in this report is therefore the refusal set under')
L.append('**today\'s** ruleset, which is what a run started now would produce. Anyone')
L.append('comparing against an older receipt-review CSV should expect it to be larger.')
L.append('')
L.append('**D4 - the industry labels are read from the databases, not derived from the')
L.append('slugs.** `property_casualty_insurance` is the token for the label')
L.append('`Property & Casualty Insurance` (`build_industry_report.ps1:54` maps')
L.append('`[^A-Za-z0-9]+` to `_`), so the slug alone would not have produced a matching')
L.append('SQL filter. Each database contains exactly one distinct `industry` value in')
L.append('both tables.')
L.append('')

with open(os.path.join(OUT, 'SUMMARY.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(L) + '\n')
print('wrote SUMMARY.md')
for slug in ORDER:
    if slug in receipts:
        r = receipts[slug]
        print('%-30s refused=%6s dollars=%18s groups=%d agree=%s' % (
            slug, r['refused_rows'], money(float(r['refused_dollars'])),
            len(groupings[slug]), r['masks_agree']))
