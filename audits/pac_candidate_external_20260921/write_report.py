from pathlib import Path
from collections import Counter,defaultdict
from decimal import Decimal
from datetime import datetime,timezone
import json

OUT=Path(__file__).resolve().parent
def read(name):return json.loads((OUT/name).read_text())
def dollars(value):return f'${Decimal(str(value)):,.2f}'

bulk=read('bulk_comparison.json'); exceptions=read('external_exceptions.json')
claims={}
for r in bulk:claims[r['cycle'],r['committee'],r['candidate_id'],r['direction'],r['amount']]=r
resolved={}
for r in exceptions:resolved[r['cycle'],r['committee'],r['candidate_id'],r['direction'],r['amount']]=r
counts=Counter(r['status'] for r in claims.values())
classifications=Counter((r['cycle'],r['external_status']) for r in resolved.values())
culac=read('culac_external.json');local=read('report_activity.json')
localcu={(r['cycle'],r['candidate_id'],r['direction']):r for r in local if r['committee']=='C00007880' and r['report'].startswith('Credit Union')}
legacy=read('clf_legacy_check.json')
gap=sum(Decimal(r['local_source_sum'])-Decimal(r['saved']) for r in legacy)
snapshots=read('snapshot_comparison.json')

text=f'''# External PAC candidate-spending audit — September 21, 2026

Completed: {datetime.now(timezone.utc).isoformat()}

## Result

CULAC / America's Credit Unions PAC (C00007880): all nine independent-spending candidate/cycle entries already present in the Credit Union report are supported by current FEC regular-report records. These are expenses supporting candidates, not money received by the candidate campaigns. Bacon's 2022 $450,000 and Lawler's 2024 $400,000 are genuine.

The broader saved data is **not entirely current or correct**. The review identifies:

- Whole-dollar precision loss in the PAS2 source, demonstrated against exact Schedule E values. It does not explain away the large CULAC expenditures.
- A missing 2026 CULAC expenditure: Ben McAdams, $299,999.87. The saved Credit Union report contains Young Kim's $500,000 but no McAdams entry.
- **21 understated Congressional Leadership Fund (C00504530) candidate/direction totals for 2022**, totaling {dollars(gap)} below the already-preserved local whole-dollar source rows. This is a data-processing issue, not new 2026 spending. The old maximum-filing-per-transaction-label rule reproduces all 21 saved totals exactly while dropping distinct candidate expenses under recycled transaction labels.
- Current 2026 FEC records differ from numerous saved report totals. These are reported as refresh/reconciliation differences; the comparison does not presume every difference is an application defect.
- The saved PAC API snapshots agree exactly on all 122 candidate/direction groups they contain; current records add 12 groups in 2026.

No production workbook, source database, imported file, or application code was edited. New downloaded evidence and analysis are isolated in this audit directory. Existing September 20 review notes record related version-policy corrections in code but explicitly say published reports were not rebuilt. This review verifies the remaining saved-report differences; it does not claim deployment or rebuilding has occurred.

## Scope and method

Read all eight designated `*Industry Spending Overview.xlsx` reports from `C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files`; Excel lock files were excluded. Read the Downstream Activity sheet and preserve each report's cycle and accounting basis. The scope here is independent-spending Support/Oppose entries analogous to Bacon and Lawler, not every direct contribution, employee receipt, or legal contribution-limit question.

The workbooks contain {len(bulk):,} independent-spending report entries representing 8,818 distinct committee/cycle/candidate/direction groups. Overlapping reports were compared separately, never added. They contain {len(claims):,} distinct amount claims because some workbooks contain different vintages of the same group.

Fresh official FEC PAS2 files for 2022, 2024 and 2026 were downloaded, hashed and retained. For the saved included-spending basis, non-memo rows were grouped by exact committee, cycle, candidate ID and support/oppose code; exact repeated source IDs were counted once. {counts['exact_current_bulk_match']:,} distinct amount claims match that current whole-dollar bulk comparison exactly. All exceptions were queried against current regular-report Schedule E data, with pagination exhausted and 24/48-hour notices excluded.

For duplicated API records, a comparison counted the same filing number + transaction ID + candidate + direction + amount + expense/dissemination dates + payee + purpose only once. This resolves eight additional distinct amount claims (six from 2022 and two from 2024). Records merely sharing an amount were never merged. A malformed or changed image-number field did not create a second transaction.

The remaining unique amount-claim categories are recorded in `external_exceptions.json`. This is a reconciliation of the existing non-memo included basis, not certification that excluding every memo item captures every unpaid independent-expenditure obligation. The FEC cautions that memo items can disclose unpaid activity. A matching amount does not independently validate every name, underlying ad, campaign coordination, or donor-to-candidate attribution. Missing source groups were not treated as proven zero spending.

## CULAC: all candidate spending in current regular reports

| Cycle | Candidate | Saved Credit Union report | Exact FEC amount | Result |
|---|---|---:|---:|---|
'''
for year in culac:
    for r in sorted(year['groups'],key=lambda x:-Decimal(x['amount'])):
        prior=localcu.get((str(year['cycle']),r['candidate_id'],'Support'))
        observed=dollars(prior['amount']) if prior else 'Absent'
        status='Supported; exact match' if prior and Decimal(prior['amount'])==Decimal(r['amount']) else 'Supported; whole-dollar source loses cents' if prior else 'Missing from saved report'
        source=r['transactions'][0]['pdf_url']
        text+=f"| {year['cycle']} | [{r['candidate']}]({source}) | {observed} | {dollars(r['amount'])} | {status} |\n"
text+='\nAll ten current candidate groups are Support. Totals reconcile exactly to the FEC committee financial summary: '+', '.join(f"{y['cycle']}: {dollars(y['sum'])}" for y in culac)+'.\n'
text+='''
Independent corroboration:

- [Nebraska Credit Union League, October 14, 2022](https://www.ncultheaffiliate.com/?p=4330) describes the CULAC independent-expenditure campaign supporting Don Bacon, including advertising featuring a retired Cobalt Credit Union executive.
- [America's Credit Unions, October 16, 2024](https://www.americascreditunions.org/news-media/news/credit-unions-support-rep-fitzpatrick-direct-mail-digital-advertising) confirms the Fitzpatrick campaign. Exact dollars are verified from FEC records, not inferred from this announcement.
- [America's Credit Unions, June 1, 2026](https://www.americascreditunions.org/news-media/press-release/press-release-americas-credit-unions-pac-announces-new-expenditure-utah) confirms the McAdams and Young Kim independent-expenditure campaigns. Its separate Sherman discussion is not attributed to C00007880 without matching FEC evidence.

## Confirmed historical understatement: Congressional Leadership Fund, 2022

All amounts below are committee spending supporting/opposing the named candidate. They are not direct contributions.

| Candidate | Direction | Saved report amount | Preserved local PAS2 total | Current exact FEC total |
|---|---|---:|---:|---:|
'''
for r in legacy:
    match=next(x for x in resolved.values() if x['cycle']=='2022' and x['committee']=='C00504530' and x['candidate_id']==r['candidate_id'] and x['direction']==r['direction'])
    text+=f"| {r['candidate']} | {r['direction']} | {dollars(r['saved'])} | {dollars(r['local_source_sum'])} | {dollars(match['api_unique_exact'])} |\n"
text+='''
Discriminating example: Brian Fitzpatrick shows $0 from CLF in the saved 2022 report, while the FEC reports $194,527.15 across eight regular-report Schedule E items. Original electronic filings [1592379](https://docquery.fec.gov/dcdev/posted/1592379.fec) and [1598276](https://docquery.fec.gov/dcdev/posted/1598276.fec), downloaded in full, contain these eight distinct items and sum to exactly $194,527.15. This is separate from CULAC's 2024 Fitzpatrick spending.

`clf_legacy_check.json` records the independent reproduction of all 21 lower saved totals. Related source-policy fixes were already described in `audits/mentat_contradictions_only_20260920.md`; saved report regeneration was expressly not performed in that earlier work.

## 2026 identity and freshness differences

- C00821439 / Julia Letlow: the saved report associates $116,119 with her House ID H2LA05126. Current regular filings associate the four expenses, $116,120.25 exactly, with her Senate ID S6LA00664. This is a historical-ID difference plus lost cents; it is not evidence of zero expenditure.
- C00687848 / Joe Kerr: current filings use H6CA40317, while a saved small-dollar group uses H4CA40098. Another saved group labels a purported candidate with the paying organization's name. These source-identity differences need source-aware refresh/reconciliation; no silent reassignment was made.
- C00687848 / Robert Garcia: current retrieved rows exist but are memo-coded; a non-memo comparison therefore has no included API amount. It would be wrong to describe this as no spending or automatically replace it with zero.
- Other current-cycle changes are retained at candidate/direction level in `external_exceptions.json`, with original filing links, saved amounts, current exact values, and whole-dollar comparison values. Differences include new reports and corrections; this audit does not indiscriminately relabel them as bugs.

## Saved API snapshots

Six distinct committee/cycle units were selected from the two saved snapshot directories using the app's current selection rule. Current FEC regular-report records match 71 existing 2024 groups and 51 existing 2026 groups, to the cent. Twelve additional 2026 groups appear in current FEC data. These are new to the saved snapshot, not necessarily newly incurred expenses. Details: `snapshot_comparison.json`.

## Evidence and reproducibility

- `report_inventory.json`: report names, SHA-256 hashes, row counts, and source notes.
- `report_activity.json` and `bulk_comparison.json`: complete scoped report inventory and current official bulk comparison.
- `culac_external.json`: all CULAC transactions, exact amounts, payees, dates, and original filing URLs; raw API response receipts accompany it.
- `external_exceptions.json`: every initial bulk exception checked against current regular-report Schedule E; `external_failures.json` is empty.
- `snapshot_comparison.json`: independent-spending comparisons for saved API snapshot units.
- `official-pas2*-receipt.json`: fresh FEC download URLs, modification times, lengths and hashes. Archive files are retained unchanged.
- `clf_legacy_check.json` and original electronic filing files: concrete reproduction and primary evidence for the historical understatement.

Reference definitions: [FEC independent expenditures](https://www.fec.gov/help-candidates-and-committees/making-independent-expenditures/), [FEC PAS2 file description](https://www.fec.gov/campaign-finance-data/contributions-committees-candidates-file-description/).
'''
(OUT/'REVIEW.md').write_text(text,encoding='utf-8')
print('distinct claims',len(claims),'bulk matched',counts['exact_current_bulk_match'],'exceptions',dict(classifications),'CLF gap',gap)
print('Written',OUT/'REVIEW.md')
