import json
from pathlib import Path

root = Path(__file__).resolve().parent
c = json.loads((root / 'comparison.json').read_text(encoding='utf-8'))
v = json.loads((root / 'verification.json').read_text(encoding='utf-8'))
qa = json.loads((root / 'preview-qa.json').read_text(encoding='utf-8'))
assert c['status'] == 'verified' and v['workbook_unchanged'] and not qa['javascript_errors']
old, new = c['before']['summary'], c['after']['summary']
money = lambda n: f'${n:,.2f}'
cmoney = lambda n: ('−' if n < 0 else '+') + money(abs(n) / 100)
labels = {
    'explicit_interest_or_investment_income': 'Explicit interest and investment income',
    'other_explicit_non_giving_receipt': 'Other explicit non-giving receipts',
    'exact_employer_alias_recheck': 'Exact employer alias rechecks',
    'other_accounting_change': 'Existing rejected-company exclusions',
    'explicit_non_giving_receipt_resolved': 'Explicit non-giving receipt resolved',
    'filing_coverage_separated_from_receipt_review': 'Filing coverage separated from receipt review',
    'other_automatic_resolution': 'Existing rejected-company exclusions',
}
reduction = old['unresolved_records'] - new['unresolved_records']
lines = [
    '# Mentat cross-reference review — September 12, 2026', '',
    f'The review was too restrictive in identifiable, repeatable ways. On a rerun of all {new["input_records"]:,} Banking records, the receipt-review queue fell from **{old["unresolved_records"]:,} to {new["unresolved_records"]:,}**: {reduction:,} fewer records ({100*reduction/old["unresolved_records"]:.1f}%). There are now **{new["automatic_decisions"]:,} automatic decisions**. This is a workflow measure, not an accuracy percentage.', '',
    'Scope: the latest Banking cross-reference, ten named major banks, election cycles 2022, 2024 and 2026. Its company scope matches the Banking workbook in the designated Mentat Complete Files folder. Community Banks and the other industry workbooks are separate scopes. The shared corrections apply across industries.', '',
    '## What was unnecessarily strict', '',
    '1. **Whole-filing completeness was being demanded for ordinary receipt decisions.** The old queue contained 561,167 records whose only questions concerned filing coverage. Clear contribution classification does not require manually reviewing every transaction in a missing filing census. Coverage now has its own grouped follow-up queue; observed conflicting versions and unresolved links remain receipt questions.',
    f'2. **Prefix checks could block stronger exact employer matches.** The scalar and batch matchers now check full approved aliases first and normalize equivalent bank legal suffixes, spacing and punctuation. The saved-data recheck accepted {v["attribution_recheck"]["resolved_records"]:,} historical individual-employer holds. BANK OF AMERICA, N.A.; CITI BANK; CITIBANK N.A.; JP MORGAN CHASE; and WELLS FARGO BANK pass. CITIZENS BANK is still not accepted as Citibank. An accepted employer match can still leave a separate memo or transaction question.',
    '3. **Irrelevant attribution questions preceded obvious receipt meaning.** The old queue held 40,332 already classifiable non-giving observations. Two Truist broker-sale descriptions alone accounted for $2,040,066 of review exposure. Such observations now resolve as non-giving without pretending their corporate identity is verified.',
    '4. **Explicit interest wording was missed.** NON-CONTRIBUTION: INTEREST, HEADQUARTERS INTEREST INCOME, RECOUNT INTEREST INCOME and exact INVESTMENT INCOME now have shared recognition rules. An account designation no longer overrides an explicit interest event. Generic form captions, contradictory gift descriptions and missing roles remain unresolved.', '',
    '## Measured result', '',
    '| Measure | Previous cross-reference | Revised cross-reference |',
    '|---|---:|---:|',
    f'| Records examined | {old["input_records"]:,} | {new["input_records"]:,} |',
    f'| Automatic decisions | {old["automatic_decisions"]:,} | {new["automatic_decisions"]:,} |',
    f'| Records requiring receipt review | {old["unresolved_records"]:,} | {new["unresolved_records"]:,} |',
    f'| Provisional original giving | {money(old["observed_original_giving"])} | {money(new["observed_original_giving"])} |',
    f'| Employee-attributed receipts | {money(old["employee_giving"])} | {money(new["employee_giving"])} |',
    f'| Unverified funding in provisional giving | {money(old["unverified_funding"])} | {money(new["unverified_funding"])} |', '',
    f'Of the automatic decisions, {new["source_verified_records"]:,} were checked against preserved exact FEC responses and {new["classified_from_stored_records"]:,} were classified from stored evidence. Filing coverage still affects {new["coverage_records"]:,} records, grouped into {v["coverage_task_count"]:,} tasks. Of those records, {new["coverage_only_records"]:,} have no outstanding receipt question. Coverage figures overlap the receipt populations and must not be added to them.', '',
    '### Accounting changes from the previous cross-reference', '',
    '| Mechanism | Changed records | Signed net change |',
    '|---|---:|---:|',
]
for g in c['giving_deltas_by_mechanism']:
    lines.append(f'| {labels.get(g["category"],g["category"])} | {g["records"]:,} | {cmoney(g["net_delta_cents"])} |')
lines += [f'| **Total** | **{c["cent_totals"]["changed_counted_records"]:,}** | **{cmoney(c["cent_totals"]["net_delta_cents"])}** |', '',
    f'Positive changes total {cmoney(c["cent_totals"]["positive_delta_cents"])}; negative changes total {cmoney(c["cent_totals"]["negative_delta_cents"])}. They reconcile exactly in cents. These changes compare two cross-reference computations. The page also shows its separate original receipt baseline of {money(new["baseline_amount"])}; that is a different comparison.', '',
    '### How old review items were resolved', '',
    'This partition is disjoint. Employer corrections that still have another receipt question are not counted as fully resolved here.', '',
    '| Resolution | Records now automatic |', '|---|---:|']
for g in c['resolved_review_partition']:
    lines.append(f'| {labels.get(g["category"],g["category"])} | {g["records"]:,} |')
lines += ['', '### Examples of changed giving decisions', '', '| Company / cycle | Evidence | Change |', '|---|---|---:|']
for item in (c['top_explicit_income_changes'][:4] + c['top_employer_recheck_changes'][:4]):
    description = (item.get('receipt_type_full') or item.get('memo_text') or item.get('contributor_employer') or item['category'])
    if item['category'] == 'exact_employer_alias_recheck':
        description = item.get('contributor_employer') or description
    description = description.replace('|', '/').replace('\n', ' ')[:150]
    lines.append(f'| {item["company"]} / {item["cycle"]} | {description} · [FEC {item["source_id"]}]({item["source_url"]}) | {cmoney(item["delta_cents"])} |')
lines += ['', '## Lessons implemented systemically', '',
    '- **Shared rules:** `mentat/inputs/fec_receipt_rules.json`, the Python receipt classifier, and the R receipt classifier now agree on explicit income treatment.',
    '- **One employer matcher:** collection, retagging and historical cross-reference rechecks use the same R matching code. The bridge opens the source database read-only. Historical rechecks release only exact approved matches, retain rejections/exclusions, and defer conflicting FEC employer inputs.',
    '- **Separate verification dimensions:** the engine and ledger distinguish automatic receipt decisions, exact-source verification, actual receipt ambiguity and collection coverage. Complete unique-dollar evidence remains a separate claim.',
    '- **Durable evidence:** each run saves source observations, old and new attribution reasons, matching inputs/results with SHA-256 fingerprints, rule snapshots, grouped coverage tasks and every signed accounting change.',
    '- **Product and operating guidance:** the cross-reference page exposes the new distinctions. The methodology, README and repository agent instructions require these practices on future work.',
    '- **Regression coverage:** positive examples and plausible counterexamples cover exact aliases, unrelated banks, persistent exclusions, conflicting employer evidence, generic versus explicit income, genuine special-account gifts, ambiguous memos, observed amendments and incomplete filings.', '',
    '## Verification and remaining work', '',
    f'All {len(c["checks"])} comparison checks passed, including unchanged source IDs, receipt amounts and baselines, identical preserved raw observations, and exact reconciliation of all signed changes. The source database fingerprint is unchanged. The published Banking workbook has the same SHA-256 before and after this review; the revised figures are in the cross-reference view.',
    'Validation passed: 118 Python tests, five R suites (including report generation and 6,035 workbook formula checks), JavaScript view checks, and desktop/mobile browser checks. The complete 849,399-record offline rerun finished successfully.', '',
    'The remaining queue is visible by reason below. Coverage follow-up is separate; resolving a receipt does not assert a complete filing census, ownership history or money route.', '',
    '| Remaining receipt question | Records | Associated gross amount |', '|---|---:|---:|']
for g in c['after']['unresolved_reasons'][:8]:
    lines.append(f'| {g["reason"].replace("_", " ")} | {g["records"]:,} | {money(g["amount"])} |')
lines += ['', 'Reason groups may overlap. Associated amounts are review exposure, not estimated errors or unique giving.', '',
    '## Evidence and references', '',
    '- [FEC receipt data reference](https://www.fec.gov/campaign-finance-data/about-campaign-finance-data/about-receipts-data/) and [investment income reporting guidance](https://www.fec.gov/help-candidates-and-committees/filing-reports/investment-income-and-loss/) support the receipt-role distinctions.',
    '- [JPMorgan Chase official terms](https://www.jpmorganchase.com/legal/terms-and-conditions) establish the JPMorgan Chase brand relationship used for the employer alias; this is not treasury or subsidiary-ownership proof.',
    '- [FEC conduit reporting guidance](https://www.fec.gov/help-candidates-and-committees/filing-reports/contributions-received-through-conduits/) supports keeping original gifts and memo/intermediary representations distinct.',
    f'- Revised immutable run: `{c["after"]["run_id"]}`. Previous run: `{c["before"]["run_id"]}`.',
    '- [Full machine-readable comparison](comparison.json), [initial review evidence](before-analysis.json), and [verification record](verification.json).',
    f'- [Refreshed read-only cross-reference]({qa["url"]}).', '',
]
(root / 'review.md').write_text('\n'.join(lines), encoding='utf-8')
print(root / 'review.md')
