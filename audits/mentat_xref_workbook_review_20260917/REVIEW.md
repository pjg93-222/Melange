# Mentat cross-reference and workbook generation review (four-voice council)

Date: 2026-09-17. Session model: Claude Fable 5.1 (Architect voice and synthesis); Skeptic, Pragmatist and Critic were fresh Fable subagents given only the question and the measured context below, no conversation history. Read-only: nothing in `C:\Users\pgoff\Mentat` or `Mentat Complete Files` was edited; every number below was recomputed in this session from the published workbooks and the cross-reference run reports.

Paul's question: "I see the cross reference as redundant, however check this and for blind spots, it seems to minimize the amounts too much. Additionally, check the workbook generation, it should be fit for the way in which the chart-studio reads the graphs."

## 1. What "cross-reference" is

Two things carry the name. The R collector's `company_cross_reference_people()` (`mentat/R/collect.R:871`) only builds trusted name keys from the executives table and verified aliases; it adds acceptances (`identity_cross_reference:` reasons at `collect.R:2641, 2778`) and never reduces an amount. The engine Paul is reading is the console's Cross-reference tab: `mentat/tools/run_cross_reference.py` reads every row of `mentat.db` for the industry (`contributions` and `corporate_giving`, industry filter only, `run_cross_reference.py:54-59`), `mentat/tools/cross_reference_engine.py` re-decides each row under its own rulebook and zeroes what it excludes (`exclude()` at `:120-128`), and `report.json` feeds `mentat/app/cross-reference.js`. Only two runs exist on disk: Banking `20260913T074303-bca0ac2b9cd3` (the one `latest.json` points to) and Fintech `20260911T010907-d7fdb039c080`. The other six industries have no run.

## 2. Measured numbers (Banking, three cycles 2022/2024/2026)

| Quantity | Value | Source |
|---|---:|---|
| Published workbook Total Giving, 2021-2022 | $16,652,458.77 | `Banking Industry Spending Overview.xlsx`, Company List / Master Overview "Industry Total" |
| Published workbook Total Giving, 2023-2024 | $26,107,204.16 | same |
| Published workbook Total Giving, 2025-2026 | $12,003,181.12 | same |
| Published workbook Total Giving, all three cycles | $54,762,844.05 | sum; equals Chart Studio's verified-contributions Scope A to the cent |
| Workbook tiers, three cycles | Employee $38,604,371.32; Middle Management $12,689,031.02; Chief $2,104,179.29; Corporate $1,365,262.42 | Company List |
| Cross-reference "Previous receipt total" (baseline) | $133,516,227.27 | `report.json summary.baseline_amount` = face value of DB rows with company_match_status accepted, no excluded_reason, no duplicate_memo |
| Cross-reference "Observed original giving" | $72,103,655.70 | `summary.observed_original_giving` |
| of which employee-attributed | $70,446,487.57 | `summary.employee_giving` |
| of which funding attribution unverified | $1,657,168.13 | `summary.unverified_funding` |
| of which corporate treasury | $0.00 | `summary.corporate_giving` (structurally unreachable, see 3.3) |
| "PAC outgoing activity" (separate, not added) | $22,774,438.00 | `summary.pac_outgoing` |
| "Change from previous total" | -$61,412,571.57 | `summary.amount_change` |
| Records needing review | 76,197 rows, $49,929,377.44 gross | `summary.unresolved_records / unresolved_amount` |
| top review row: company attribution unresolved | 36,241 rows, $37,940,955.71 | `unresolved_reasons[0]`; every row zeroed and outside every total |
| Rows verified against preserved FEC responses | 13,853 of 849,399 (1.6%) | `summary.source_verified_records` |
| Rows classified from stored evidence (the same DB) | 759,349 | `summary.classified_from_stored_records` |

Fintech (older DB, run 2026-09-11): workbook Total Giving $1,891,559.66 + $3,859,524.56 + $4,052,807.09 = $9,803,891.31, which equals the cross-reference baseline exactly; observed original giving $9,089,743.52 (-7.3%); unresolved exposure $17,899,062.06; PAC outgoing $0.00; corporate $0.00.

## 3. Findings on the cross-reference

### 3.1 The premise is inverted: it does not minimize against the workbook

Against the published workbook the cross-reference counts more original giving, not less: $72.1M versus $54.8M, +$17.3M (+32%). The "-$61.4M change" Paul sees is measured against the $133.5M baseline, which no engine publishes as giving. Of that cut, $22.8M is company-PAC money moved to the separate PAC view by design (`cross_reference_engine.py:295-303`) and about $19.0M is interest, dividends and other non-giving receipt roles (`:257-263`), money the workbook also keeps out of Total Giving through its F3X line-17 handling. The remaining cut is attribution and role exclusions. The $37.9M "company attribution unresolved" row is the face value of rows whose donor never matched a listed bank; it is not spending and it is in no total, but the label renders as bare snake_case under "Associated amount" because the key is missing from the `reasons` map in `cross-reference.js`.

### 3.2 Where the +$17.3M excess comes from (engine code verified this session)

- Memo legs whose same-filing parent is not proven are kept at full value: 19,529 rows / $8,522,419.98 (`cross_reference_engine.py:424-451`, `memo_parent_not_established` is review-only).
- Transfer receipts (F3X line 12) are kept pending the original source: 18,696 rows / $5,789,063.20 (`:283-289`, review-only).
- Earmark conduit and destination legs are both kept unless reciprocal "EARMARKED FOR" text pairs them one-to-one: 15,915 + 2,168 rows, about $0.7M (`:456-500`).

The R report dedups memo and conduit legs by its own keys (R8 ruling: conduit legs count once, recipient as shown). The two rulebooks therefore disagree on exactly the rows where a leg's parent is outside the industry corpus. That is the one place a systematic under-count could hide in the workbook, and the cross-reference's retained memo legs are the probe for it (see section 6, the one measurement).

### 3.3 Real blind spots (under-count mechanisms)

1. Corporate treasury giving is structurally $0. `mentat/inputs/verified_company_affiliations.json` holds 12 records, all `connected_pac` for the ten banks, and zero `treasury_entity` records; both paths that produce `corporate_original` require `treasury_entity` (`:216`, `:311-318`). The workbook's Corporate tier is $1,365,262.42 for Banking and $1,307,620.23 for Fintech.
2. PAC outgoing is $0.00 for every industry except Banking because the register lists only bank PACs; company-PAC rows elsewhere fall to "attribution unresolved" and are zeroed.
3. Company matching against the register is exact string equality on subsidiary names such as "Bank of America NA" (`:146`); a parent-name roster silently misses.
4. Cycle is computed from the receipt date (`year + year % 2`, `run_cross_reference.py:64-68`) while the workbook keys on the FEC `two_year_transaction_period`; rows straddling a cycle boundary land in different cycles. Small, unmeasured.
5. Only 13,853 rows (1.6%) were checked against preserved FEC responses; 98.4% of the run re-classifies the DB the workbook was built from. The exact alias and PAC registers it introduced are now consumed by `collect.R`, so that value has already migrated into the main pipeline.

### 3.4 What the console shows

Three engines, three totals, no bridge: Graph (workbook, `include_in_analysis == Yes`, latest cycle by default), Chart Studio verified contributions (observation grain from the export payload joined to the workbook's include flags; it also exposes R's per-row decisions as `reported_*` fields), and the Cross-reference tab. The reconciliation strip compares Chart Studio with Graph only. The workbook's own Downstream Activity sheet carries company-PAC outgoing money per candidate from Schedule B (24K/24E/24A rows), richer than the cross-reference's Schedule-A-observed PAC view.

## 4. Findings on workbook generation versus Chart Studio

Chart Studio has two source kinds. The verified-contributions source (`contribution_data.py`, `contribution_semantics.py`) reads an analytics index built from the export payload's raw observation rows; the xlsx shape does not affect it, and it agrees with the workbook to the cent. Worksheet mode reads any sheet of the xlsx through a header-sniffing reader (`report_insights.worksheet_data`, 50,000-row cap, 60-group fold, identifier columns hidden, "; "-joined cells, cached formula values only). Worksheet mode is where the generator is not fit:

- Cycle sheets carry a Fact Type column mixing Recipient, Employee and Master rows. Summing Amount on the Banking 2025-2026 sheet gives $33,413,266.53 against the true $12,003,181.12 (2.8x). `graph_data.py:195-207` filters Fact Type; worksheet mode does not.
- Recipient List repeats Industry and Company views: its Total Giving sums to $109,525,688.10, twice the true $54.76M.
- Downstream Activity "Net Included Amount" sums to $2.08B / $3.78B / $0.48B per cycle: recipient committees' activity, not industry money.
- Three different cycle-sheet schemas are in production. Raw rows with dates, employer, ZIP and R's decision flags (35 columns): Community Banks, Credit Union, Crypto, Fintech. Fact rows with IDs and recipient names (18 columns): Credit Arms, Property & Casualty. Compact fact rows with no Cycle column, no Committee ID, no recipient name and no dates (12 columns): Banking, Telecom (payload above the 120 MB threshold sets `MENTAT_COMPACT_RAW=1` and `MENTAT_FORMULA_FACTS=1` in `build_industry_report.ps1:857-858`, consumed by `crypto_workbook_builder.mjs:119-120`).
- Seven of eight published books date from 2026-07-28..31; only Banking (2026-09-10) carries the September sheets (Transfer Paths, Funding Cohorts, Allocation Estimates/Coverage, Source Freshness, Classification Review, Data Quality). No published book has the committed Recipient Detail / Contributor Detail / Accounting Basis sheets, and no `<Industry> Industry Spending Data.xlsx` companion exists in `Mentat Complete Files` for any industry, although `contribution_data.py:209` already looks for it and the tidy writer passed the console's own reader in the dry run.
- Why nothing newer is published: the uncommitted receipt-evidence gate (`fec_assert_receipt_evidence`, `collect.R`, ruleset `inputs/fec_receipt_rules.json`) refuses any unresolved row, so every rebuild stops: Banking 2,070 rows / $20.7M of interest, dividend and transfer descriptions, Crypto 80, Credit Union 4. The tidy lane's P2 exporter hook and P5 orchestrator step are applied in the working tree but uncommitted, so even a rebuild that passed the gate would not write the companion.
- Scale caveat for the companion: the tidy design splits sheets per cycle above 50,000 rows, but Banking's Contributions grain is about 602,000 accepted rows (about 200,000 per cycle) and Transfer Paths is 68k / 124k / 63k, so the row-grain sheets exceed the console's worksheet cap at Banking scale regardless of the split. The Facts sheets (Giving, Recipient, Contributor, Location) fit; row grain belongs to the verified path. The 90/90 and 5/5 proofs were a Credit Union dry run.

## 5. Council positions

**Architect (session model, written before reading the others):** retire the cross-reference as a totals engine and keep it only as an evidence and review ledger; the workbook generator is fit for the verified path and unfit for worksheet mode on the Overview, and the fix already built (companion book plus detail sheets) is blocked on Paul's receipt rulings and the uncommitted P2/P5. Risk: losing the only per-row evidence ledger and the only list that flags roster gaps.

**Skeptic:** remove the tab, totals and queue outright; it is not a cross-reference (98.4% re-classifies the same DB, registers already migrated, PAC view poorer than Downstream Activity); Corporate $0 and Fintech PAC $0 are empty-register artifacts. Surprise: the gate blocking rebuilds refuses interest and dividend rows no engine counts; route them to Data Quality as advisory rather than refusing the workbook. Risk of removal: nothing else re-reads rejected rows; take one read-only diff of the Banking ledger against R's decision columns first.

**Pragmatist:** reframe cheaply; leave the engine offline, strip every total from the tab, show only a disagreement queue (rows R accepted that the engine could not attribute, beside R's status). Ship the companion that already exists once Paul extends the description ruleset; badge Overview cycle, Recipient List and Downstream sheets "not summable" today. Risk: the companion was proven at Credit Union scale only; check Banking against the 50,000-row cap before it becomes the default. Surprise: both halves of the question bottleneck on the same thing, Paul's classification rulings.

**Critic:** keep only the 13,853 FEC-verified rows as a ledger; delete the re-run and the "-$61.4M" line. Worksheet mode is a footgun no Overview layout fixes. Risk: the $37.9M bucket is the only signal flagging roster gaps unless R emits an unmatched-employer-by-dollars list; "quarantine, not refuse" brushes classification, Paul's domain. Surprise: the tall companion walks into the 50,000-row cap and the 60-group fold at Banking scale; and the gate is uncommitted, so a HEAD rebuild skips it while a live-tree rebuild hits it.

## 6. Verdict

- Consensus (4/4): "minimizes too much" is inverted for Banking (+$17.3M against the workbook; the -$61.4M is against an unpublished baseline and $41.8M of it is money the workbook also excludes). The engine is not an independent check. The generator is fit for the verified path and unfit for worksheet mode on the Overview; the built fix is unpublished and gated on Paul's rulings.
- Strongest dissent: how much to keep. Skeptic removes everything; Critic keeps only the FEC-verified slice; Pragmatist keeps a disagreement queue; Architect keeps the ledger. The Critic's roster-gap point stands: the unresolved-employer list has no substitute today.
- Premise check: the Skeptic rejected the framing "does it minimize" and replaced it with "is it a check at all"; the answer is no, except for the 1.6% FEC-verified slice.
- The one measurement before any retirement (read-only, no console, no engine run): from the Banking run's `review.csv` and `ledger.sqlite`, take the 19,529 `memo_parent_not_established` rows and the 18,696 transfer rows and join them to the workbook's decision flags (`is_memo_leg`, `is_conduit_leg`, `duplicate_memo`, `include_in_analysis`) in the export payload. Rows the workbook dropped whose parent leg is absent from the industry corpus are the only candidates for a real workbook under-count. If that set is near zero, the +$17.3M is the engine's over-count and the cross-reference has nothing left to say about totals.
- Recommendation (all apply/commit steps are Paul's):
  1. Cross-reference tab: stop publishing totals (baseline, Observed original giving, Change, PAC outgoing). Keep a disagreement queue and an unmatched-employer-by-dollars list; keep the FEC-verified slice as evidence. Name the reasons that render as snake_case. Do the section-6 measurement first.
  2. Workbook: Paul rules on the receipt-rule descriptions (Banking 2,070 / Crypto 80 / Credit Union 4), or rules that unresolved rows are quarantined into Data Quality (kept out of totals, visible) instead of refusing the build; then commit P2/P5 (and P6c/P7b); rebuild Crypto first (smallest, 80 rows) with the companion and detail sheets and run the console's reader on it; then Banking with the cap check.
  3. Console worksheet mode: default the picker to the companion Data book and mark the Overview cycle sheets, Recipient List and Downstream Activity non-summable until every book is rebuilt; the schema drift across the eight books is a rebuild problem, not a reader problem.

## 7. Brain update draft (for Paul to apply)

STATE.md, Current position, new first bullet:

`- MENTAT CROSS-REFERENCE + WORKBOOK REVIEW (2026-09-17, worktree mentat-xref-spreadsheet-review-3f1ff0, read-only, four-voice council): Banking cross-reference run 20260913T074303 counts $72,103,655.70 original giving against the published workbook's $54,762,844.05 (+$17.3M: retained memo legs $8.5M, transfers $5.8M, earmark legs ~$0.7M); its "-$61.4M change" is against a $133.5M baseline no engine publishes, and $41.8M of that cut (PAC view $22.8M, non-giving $19.0M) is money the workbook also excludes - Paul's "minimizes too much" is inverted for Banking. Only 1.6% of rows are FEC-verified; registers already migrated into collect.R; Downstream Activity is richer than the PAC view. Real blind spots: corporate treasury structurally $0 (no treasury_entity records), PAC outgoing $0 outside Banking, exact-string register matching, calendar-vs-transaction-period cycle drift. Workbook: three cycle-sheet schemas across the 8 published books (raw 35-col: CB/CU/Crypto/Fintech; fact 18-col: Credit Arms/P&C; compact 12-col with no dates or cycle: Banking/Telecom); worksheet mode sums 2.8x on cycle sheets and 2x on Recipient List; no companion Data book or Detail sheets published anywhere; rebuilds blocked by the uncommitted receipt-evidence gate (Banking 2,070 / Crypto 80 / CU 4 rows) and the uncommitted P2/P5. Verdict: retire cross-reference totals, keep a disagreement queue + unmatched-employer list + FEC-verified slice; one read-only ledger-vs-workbook memo/transfer measurement before retirement; rulings + P2/P5 commit + Crypto-first rebuild for the workbook. Packet: audits/mentat_xref_workbook_review_20260917/REVIEW.md in the Mentat tree. All decisions Paul's; nothing applied.`

No DECISIONS.md or DEADENDS.md entry is proposed until Paul rules.

## 8. Evidence pointers

- Scratchpad scripts (read-only, openpyxl): `workbook_totals.py`, `workbook_facts.py`, `sheet_summary.py`, `workbook_census.py`; outputs `banking_workbook_totals.txt`, `workbook_census.txt`.
- Cross-reference reports: `mentat/state/cross-reference/20260913T074303-bca0ac2b9cd3/report.json`, `20260911T010907-d7fdb039c080/report.json`.
- Prior audit: `audits/mentat_system_debug_20260913/XREF_LOGIC_AUDIT.md` (2026-09-13, confirmed consistent with today's code).
- Codex's own record: `Mentat Complete Files/Cross Reference Further Review Complete - 2026-09-13.md`.
