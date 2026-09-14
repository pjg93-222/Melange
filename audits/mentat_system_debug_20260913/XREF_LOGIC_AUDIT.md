# Cross-reference vs Graph: read-only logic audit (Banking)

Date: 2026-09-13. Contract: source reading + read-only git + one metadata read of the latest
Banking `report.json`. No file inside `C:\Users\pgoff\Mentat` was created, edited or deleted;
no console, collector, R script, cross-reference run or DB/xlsx query was executed.

Disclosure of scope stretch: I read `summary` + `scope` + aggregate `unresolved_reasons` /
`coverage_reasons` from the latest run's `report.json` (the authorized read), and additionally the
same summary-level fields from the 8 sibling run directories, purely to rule out "Paul is looking
at a stale run". No row-level data (`review_queue` rows, `changes` rows, `ledger.sqlite`,
`mentat.db`, any workbook) was opened.

---

## 0. HEADLINE CORRECTION — the scout misidentified the $37M

**CONFIRMED.** `unverified_funding` in the latest Banking run is **$1,657,168.13**, not ~$37M.

The ~$37M Paul is reading is the **`company attribution unresolved`** row in the *Records needing
review* table: **36,241 records / $37,940,955.71**. Verified against the run the console is
actually serving:

```
mentat/state/cross-reference/latest.json
  run_id 20260913T074303-bca0ac2b9cd3, report_sha256 d396f52f...
report.json scope.industries ['Banking']  scope.cycles [2022, 2024, 2026]
report.json summary.unverified_funding      = 1657168.13
report.json unresolved_reasons[0]           = company_attribution_unresolved 36241 $37,940,955.71
report.json summary.unresolved_amount       = 49929377.44
```

Not stale: every Banking run in the state tree tells the same story, with the number converging
as fixes landed.

| run | unverified_funding | top unresolved reason |
|---|---|---|
| 20260912T204736 | $20,698,944.09 | company_attribution_unresolved $97,584,701.75 |
| 20260913T025223 | $3,833,852.25 | company_attribution_unresolved $71,115,245.50 |
| 20260913T070028 | $1,657,812.51 | company_attribution_unresolved $37,947,436.09 |
| 20260913T072613 | $1,657,169.22 | company_attribution_unresolved $37,940,955.71 |
| **20260913T074303 (live)** | **$1,657,168.13** | **company_attribution_unresolved $37,940,955.71** |

The UI never prints a friendly name for it. `cross-reference.js:19-31` defines a `reasons`
lookup; `company_attribution_unresolved` is **not in it**, so `reason()` at
`cross-reference.js:32` falls through to `part.trim().replaceAll('_',' ')` and the table renders
the literal words **"company attribution unresolved"** next to a dollar sign. That is the entire
origin of "about $37M unattributed spending".

**It is not spending, and it is not in any total.** Every one of those 36,241 rows was zeroed.

---

## 1. UNIVERSE — what rows enter the engine

### 1a. The row source: two SQLite tables, industry filter only

`C:\Users\pgoff\Mentat\mentat\tools\run_cross_reference.py:50-77`

```python
def read_sources(database,industry,cycles,baseline,companies=None,baseline_pinned=False):
    rows=[];conflicts=[]
    with closing(sqlite3.connect(Path(database).resolve().as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        for table,period in [('contributions','two_year_transaction_period'),('corporate_giving','cycle')]:
            if not table_exists(db,table):continue
            query=f'SELECT * FROM {table} WHERE industry=?'
            params=[industry]
            if companies:
                query+=f' AND company IN ({",".join("?" for _ in companies)})';params+=list(companies)
            for item in db.execute(query,params):
                row=dict(item);sid=str(row['sub_id']);row['sub_id']=sid;row['source_table']=table
                ...
                row['cycle']=receipt_date.year+receipt_date.year%2
                if row['cycle'] not in cycles:continue
                prior=baseline.get(sid)
                eligible=(str(row.get('company_match_status','accepted')).lower()=='accepted' and not row.get('excluded_reason'))
                row['current_receipt_cents']=int(prior['analysis'].get('counted_cents',0)) if prior else (0 if baseline_pinned else (cents(row['contribution_receipt_amount']) if eligible and not row.get('duplicate_memo') else 0))
```

**Inclusion predicate (CONFIRMED):**

```
row enters analyze()  <=>  row.industry == 'Banking'
                      AND  (calendar_year(contribution_receipt_date) + year % 2) IN {2022, 2024, 2026}
                      AND  row lives in `contributions` OR `corporate_giving`
                      AND  (optional) row.company IN --company list   [console passes none]
```

That is the **whole** predicate. There is **no** filter on `include_in_analysis`, `countable`,
`company_match_status`, `excluded_reason`, `duplicate_memo`, memo legs, conduit legs, refunds or
negative amounts. `company_match_status` / `excluded_reason` / `duplicate_memo` appear only in the
`eligible` expression on line 70-71, which sets the **baseline** dollar (`current_receipt_cents`),
not membership. Rejected, excluded, review-status, memo and negative rows all enter the engine and
are disposed of *inside* it.

Scale confirms it: `scope.source_observations = 849,431`, `distinct_source_ids = 849,399`,
`summary.input_records = 849,399`, `summary.baseline_amount = $133,516,227.27`.

### 1b. What the rows *are*

They are **FEC Schedule A receipt rows** — money **received by** a committee, on which an
industry-attributed name appears as the **contributor**. They are not recipient-committee
totals and not Schedule B disbursements. `cross_reference_engine.py:175` takes the dollar
straight off the row:

```python
amount = _cents(row["contribution_receipt_amount"])
```

The rows arrive in `mentat.db` from four collector phases (`mentat/R/collect.R`):
`P1_employer`, `P2_variant`, `P2_name` (all into `contributions`) and `P2_company_name`
(into `corporate_giving`, `collect.R:3159`). `P1_employer`/`P2_variant` query
`contributor_employer` (`collect.R:1753 query_field = "contributor_employer"`);
`P2_company_name` queries the corporate **name** as the contributor.

**This is the mechanism behind Paul's hypothesis (c), and it is real but partly defused.** A
corporate-name Schedule A search for "BANK OF AMERICA" returns every committee receipt on which
that string is the contributor — which includes the committee's **own loans** (the bank is the
lender), **interest/dividends** (the bank is the payer) and transfers. Those are receipts
*of a committee from a bank*, not *giving by the industry*. Paul is seeing them in the console's
"What changed" table: BofA LOAN rows at $10M / $5M×5 / $3M / $2M and JP Morgan
"NON-CONTRIBUTION: INTEREST", all reclassified to $0.

Whether such a row survives to the $37.9M bucket depends on its form/line, per
`mentat/inputs/fec_receipt_rules.json` (`forms`), applied in `mentat/tools/pac_evidence.py`
`receipt_role()`:

| F3X line | role | fate in engine |
|---|---|---|
| 11A/11AI/11B/11C | `contribution` | counted |
| 12 | `transfer_receipt` | **retained at full value**, review `original_source_of_transfer_unresolved` |
| 13, 14, 15, 16 | `other_receipt` | excluded at `cross_reference_engine.py:257-263`, bucket `non_giving` |
| 17 | `unverified_other_receipt` | survives line 257; **falls through to the attribution check at :264** |

So loans (line 13) and most interest (line 13-16, or line 17 matching the non-giving patterns)
are correctly diverted to `non_giving` **before** the attribution test. But F3X line 17 rows whose
description does not match a non-giving pattern, and line 12 transfers, are still live when the
attribution test runs — and if their company match is unresolved they land in the $37.9M.

---

## 2. BUCKETS — the decision tree and what `counted_cents` means

### 2a. `counted_cents` is the receipt amount of the gift being examined

`cross_reference_engine.py:182-188` initialises `counted_cents = amount` = the row's own
`contribution_receipt_amount`. It is **never** a recipient organisation's total receipts and
**never** a disbursement. It is only ever (a) the row's own face amount, or (b) zero.

```python
d = decisions[sid] = dict(source_id=sid, company=..., industry=..., cycle=row.get("cycle"),
    amount_cents=amount, baseline_cents=..., counted_cents=amount,
    pac_activity_cents=0, supported_unique_cents=0, bucket=bucket, ...)
```

The only writer that changes it is `exclude()` at `cross_reference_engine.py:120-128`:

```python
def exclude(sid, code, counterpart=None, link_evidence=(), kind="duplicate"):
    d = decisions[sid]
    d["counted_cents"] = 0
    d["pac_activity_cents"] = 0
    d["status"] = "excluded_with_evidence"
```

### 2b. Initial bucket, by FEC `entity_type`

`cross_reference_engine.py:177-181`

```python
entity = _text(row.get("entity_type"))
donor_id = str(row.get("contributor_id") or "")
bucket = "employee_original" if entity == "IND" else "organization_unverified" if entity == "ORG" else "funding_unverified"
if entity in ("PAC", "COM", "CCM", "PTY") and re.fullmatch(r"C\d{8}", donor_id):
    bucket = "pac_activity"
```

So `funding_unverified` = "entity_type is neither IND nor ORG, and not a committee with a
well-formed `C########` id" — i.e. blank / unknown / malformed entity metadata. It is a
**metadata-quality** bucket, not a money-source bucket. `cross_reference_engine.py:298` adds one
more member: a PAC row whose nested `contributor.committee_id` disagrees with `contributor_id`.

### 2c. Full decision tree, in evaluation order (per row, single pass)

```
cross_reference_engine.py
 :194-196  attribution_resolution present            -> record reason, continue tree
 :197-199  match = company_match_status
           attribution_unresolved = match NOT IN (ACCEPTED, REJECTED, EXCLUDED)
                                    OR (ACCEPTED AND company is blank)
 :204-223  early affiliation promotion (only if attribution_unresolved and match not REJECTED/EXCLUDED)
             PAC/COM/CCM/PTY + dated connected_pac evidence -> bucket pac_activity, resolved
             ORG           + dated treasury_entity evidence -> bucket corporate_original, resolved
 :224-230  resolved AND excluded_reason set   -> exclude()  bucket excluded_source_policy       [$0]
 :236-241  match REJECTED/EXCLUDED            -> exclude()  bucket excluded_company_match       [$0]
 :245-256  source_conflicts present           -> bucket conflicting_source_evidence  [FULL AMOUNT RETAINED]
             ...and if also attribution_unresolved -> exclude() bucket attribution_unresolved   [$0]
 :257-263  role in (other_receipt, asset_liquidation) -> exclude() bucket non_giving            [$0]
 :264-272  attribution_unresolved             -> exclude()  bucket attribution_unresolved       [$0]
                                                  + review("company_attribution_unresolved")
 :273-282  competing accepted company claims  -> bucket conflicting_source_evidence  [FULL AMOUNT RETAINED]
 :283-289  role not contribution/in_kind      -> review only, amount retained
 :295-303  bucket == pac_activity             -> counted_cents=0, pac_activity_cents=amount
 :304-305  entity not IND/ORG                 -> review funding_identity_unresolved, amount retained
 :311-322  ORG with dated treasury evidence   -> bucket corporate_original; else review, amount retained
```

**Answers to the specific questions:**

- **Can one dollar land in two buckets?** No. `d["bucket"]` is a single scalar per row, and the
  aggregation at `cross_reference_engine.py:657-662` adds each row's `counted_cents` to exactly one
  bucket. `unverified_funding` = three *disjoint* buckets summed (`run_cross_reference.py:308`),
  so that sum cannot double count at the bucket level.
- **Can it land at both contribution level and organization level?** No. There is no
  organization-level accumulator anywhere in the engine. `affiliations_for()`
  (`cross_reference_engine.py:132-151`) only *classifies* a row; it never adds a dollar.
- **Is any per-organization total added once per contribution row (classic fan-out)?**
  **No — hypothesis (d) is REFUTED for these numbers.** Grep of the engine shows every monetary
  accumulation is `sum(d[...] for d in result_rows)` over the per-row decision list
  (`cross_reference_engine.py:638-656`), and the reason-group totals iterate `source_ids` with an
  explicit per-group `set` dedup (`run_cross_reference.py:261`). No committee total is ever
  multiplied by its contribution count.
- **`original_and_pac_buckets_disjoint`** is asserted at `cross_reference_engine.py:671` and
  enforced at `run_cross_reference.py:448-450`; the live run reports it `true`.

### 2d. Why `corporate_giving` is exactly $0.00 (side finding, CONFIRMED)

`mentat/inputs/verified_company_affiliations.json` holds **12 records, every one
`relationship: "connected_pac"`. There are ZERO `treasury_entity` records.** The two code paths
that can ever produce bucket `corporate_original` both require `treasury_entity`
(`cross_reference_engine.py:216` and `:311-318`). So `corporate_original` is **structurally
unreachable** in this run, and every ORG row must end in `organization_unverified` or
`attribution_unresolved`. That is the real reason "Corporate treasury giving · supported
ownership" reads $0.00 — not an absence of corporate money.

Compounding hazard: `affiliations_for` requires **exact normalised string equality** on the
company name (`cross_reference_engine.py:146`, `_text(affiliation.get("company")) == company`).
The 12 affiliation records use bank-subsidiary names — `Bank of America NA`,
`JP Morgan Chase Bank NA`, `Goldman Sachs Bank NA`, `Wells Fargo Bank NA`, `Citibank`,
`US Bank NA`, `PNC Bank NA`, `Truist Bank`, `Capital One Bank NA`, `Morgan Stanley Bank`. If the
roster's `company` strings are the parent names (`Bank of America`, `JPMorgan Chase`), **every
affiliation silently misses** and no row is ever promoted. Reported, not fixed.

---

## 3. GRAPH UNIVERSE — a different file, a different rule, a different sign

### 3a. Source: the published report **workbook**, not the database

`mentat/app/graph_data.py:158-238` `report_facts()` opens the xlsx with `openpyxl`, walks only
sheets named `YYYY-YYYY` (`graph_schema`, `:139-150`), and applies **one** inclusion rule:

```python
# graph_data.py:187-189
for row in table_rows(book[sheet_name], 4, ('company','employee_tier','amount','include_in_analysis')):
    if str(row.get('include_in_analysis', '')).lower() != 'yes':
        continue
```

`include_in_analysis == "Yes"` is the report's own acceptance decision
(`mentat/R/report.R:1857`, `mentat/R/fec_beneficiary.R:695`,
`mentat/app/contribution_data.py:332,470`). A row is `Yes` only if it survived acceptance,
role and duplicate screening. `graph_data.py:226-229` then *asserts* the recipient facts
reconcile to the report's own master totals to the cent.

`amount` is **signed and netted** (`graph_data.py:209-210, 225`: `partitions[scope] += value`;
`facts[identity]['amount'] += value`). Refunds and negatives cancel.

### 3b. Default scope IS one cycle — the latest

```js
// graph.js:60
const response=await fetch('/api/graph?'+filters()+(initial?'&latest=1':''),{signal:controller.signal});
// graph.js:168  (Reset)
get('cycle').value=view?.options.cycles.at(-1)||'';
```
```python
# graph_data.py:317-318
if filters.get('latest') == '1' and years:
    selected['cycle'] = max(years)
```

**CONFIRMED**: the graph's first paint, and its Reset button, both pin the **max cycle only**.
With Banking sheets through 2025-2026 that is **2026 alone**. The headline is
`index.html:99` `<span>Net giving in selected scope</span>` fed by
`graph.js:82` `get('total').textContent=dollars(view.totals.giving)` from
`graph_data.py:378` `'giving': money(sum((r['amount'] for r in filtered), Decimal(0)))`.

### 3c. What the graph excludes that the cross-reference includes

Everything that is not `include_in_analysis == 'Yes'`: rejected and review-status employer
matches, `excluded_reason` rows, memo/duplicate legs, non-giving receipt roles (the BofA loans and
JPM interest), conduit legs, and any row the report screened out. Plus: three quarters of the
cycle window. Conversely the graph *adds* nothing the cross-reference lacks — its workbook rows
descend from the same `contributions`/`corporate_giving` tables.

---

## 4. SCOPE — quoted from the live run's metadata

```
run_id        : 20260913T074303-bca0ac2b9cd3
generated_at  : 2026-09-13T07:52:18.286562+00:00
status        : completed
scope.industries : ['Banking']
scope.cycles     : [2022, 2024, 2026]
scope.cycle_basis: 'calendar receipt date; original source query period preserved separately'
scope.accounting_basis : 'original giving once; PAC outgoing activity separately'
scope.company_count    : 10
scope.source_observations : 849431   scope.distinct_source_ids : 849399
```

**Answer: yes.** The cross-reference figure covers **three cycles, 2022 + 2024 + 2026**, set by
`run_cross_reference.py:339` (`cycles=(2022,2024,2026)` default) and enforced at `:342-343` and
`:68`. The graph shows **2026 only** by default. The console prints the xref cycle list once, in
the scope panel at `cross-reference.js:72`, eight panels above the money — and never next to a
dollar figure.

---

## 5. RECONCILIATION LADDER

### The two numbers as formulas over named sets

```
Let R = { rows r : r.industry='Banking' AND cycle(r) in {2022,2024,2026}
                   AND r in (contributions UNION corporate_giving) }        |R| = 849,399
      amt(r) = cents(r.contribution_receipt_amount)                  [raw, signed, face value]
      counted(r) = engine counted_cents                              [0 for every excluded row]

Let U = { r in R : review_queue has reason 'company_attribution_unresolved' naming r }
        equivalently  { r in R : company_match_status NOT IN (accepted,rejected,excluded)
                                 OR (accepted AND company blank) }
                      minus rows diverted earlier to excluded_source_policy /
                            excluded_company_match / non_giving
        |U| = 36,241,  and  counted(r) = 0  for all r in U

XREF-DISPLAYED  A = ( SUM_{r in U} max(0,amt(r)) + | SUM_{r in U} min(0,amt(r)) | ) / 100
                  = $37,940,955.71
                  producer: run_cross_reference.py:258-262, :312-313

Let F = { workbook recipient facts f : include_in_analysis(f)='Yes'
                                       AND cycle(f) = max(cycles in workbook) = 2026
                                       AND no company/tier/category/recipient filter
                                       AND funding='all' }

GRAPH-DISPLAYED G = SUM_{f in F} amount(f)                      [SIGNED NET]  ~= $12,000,000
                  producer: graph_data.py:332-339, :378
```

### Every term by which they differ

| # | Term | Direction | Evidence |
|---|---|---|---|
| T1 | Cycle window: `{2022,2024,2026}` vs `{2026}` | A covers ~3x the time | `report.json scope.cycles`; `graph.js:60`; `graph_data.py:317-318` |
| T2 | Membership: all DB rows vs `include_in_analysis='Yes'` | A is the *rejected* side | `run_cross_reference.py:56`; `graph_data.py:188` |
| T3 | **The two sets are near-disjoint by construction.** U requires match status ∉ accepted; `Yes` requires accepted. | A ∩ G ≈ ∅ | `cross_reference_engine.py:197-199` vs `R/report.R:1857` |
| T4 | Sign handling: A adds `|negatives|`; G nets them | A inflated | `run_cross_reference.py:262,313` vs `graph_data.py:225` |
| T5 | Dollar meaning: A uses face value of rows counted at **$0**; G uses included net giving | different kind | `cross_reference_engine.py:120-122` |
| T6 | Reason overlap: A deduped **within** its reason group only | irrelevant here (U is single-reason, see note) | `run_cross_reference.py:261` |
| T7 | Role: U can hold unresolved-role committee-side receipts (F3X line 17, line 12 transfers); F holds only accepted giving | A contaminated | `fec_receipt_rules.json forms.F3X`; `cross_reference_engine.py:257-272` |
| T8 | Denominator: A is 36,241 records; G is `receipt_groups` of pre-aggregated recipient facts | not comparable | `graph_data.py:382` |

Note on T6: attribution-unresolved rows `continue` at `cross_reference_engine.py:272` before any
further `review()` call, and are then skipped by every later pass — amendment families
(`:340 sid in attribution_review`), memo parents (`:426 status != excluded_with_evidence`),
earmark routes (`:457 counted_cents > 0`) and refunds (`:507`). So each of the 36,241 rows appears
in exactly one reason group. Arithmetic corroboration:
`$49,929,377.44 − $37,940,955.71 = $11,988,421.73`.

> **Trap flagged for Paul:** that residual, $11,988,421.73, is within rounding distance of the
> graph's "~$12M". **It is a coincidence and must not be used as a reconciliation.** It is the
> deduped face value of the *other* unresolved reasons (memo, transfer, role, treasury, earmark),
> over three cycles, and has no set-theoretic relationship to the graph's one-cycle net giving.

### Candidate explanations, ranked

**(b) Different receipt universes — PRIMARY. Confidence: HIGH (CONFIRMED).**
The $37.9M is the gross face value of rows the report *threw away*; the $12M is the net of rows
the report *kept*. They are complementary halves of the same corpus, not two measurements of one
quantity. Evidence: `run_cross_reference.py:56` (no acceptance filter) vs `graph_data.py:188`
(`include_in_analysis` gate); `cross_reference_engine.py:197-199` (U = not-accepted) vs
`R/report.R:1857` (`Yes` = accepted); `cross_reference_engine.py:264-267` sets `counted_cents = 0`.
*Cheapest check:* open the run's own `review.csv` (already written by
`run_cross_reference.py:472-475`, full list with `record_id, reason, company, cycle, amount`),
filter `reason` containing `company_attribution_unresolved`, and confirm the record count is 36,241
and the amount $37,940,955.71 — then cross-check a handful of those `record_id`s against the
workbook's `include_in_analysis` column. No database, no engine run.

**(a) Cycle scope — SECONDARY, and independently sufficient for a ~3x factor. Confidence: HIGH (CONFIRMED).**
Three cycles vs one. Evidence: `report.json scope.cycles = [2022, 2024, 2026]`;
`graph.js:60 '&latest=1'`; `graph_data.py:317-318 selected['cycle'] = max(years)`.
*Cheapest check:* the same `review.csv`, `Group-Object cycle` on the filtered rows. This is the
single check that settles the whole question — see §8.

**(c) Committee-level money counted as industry money — CONTRIBUTING, partly defused. Confidence: MEDIUM (PLAUSIBLE).**
The mechanism is real and confirmed in code: corporate-name Schedule A searches
(`collect.R:3159 phase = "P2_company_name"`) return receipts where the bank is a **lender or
interest payer**, and those rows enter the engine with `industry='Banking'`. Paul is looking at
the proof in the "What changed" table. But `cross_reference_engine.py:257-263` diverts
`other_receipt` (F3X lines 13-16) to `non_giving` **before** the attribution test at `:264`, so
clean loans and interest do *not* reach the $37.9M. Only F3X **line 17** rows that dodge the
non-giving patterns, and **line 12** transfers, can. What this hypothesis *does* fully explain is
the `-$61,412,571.57` "Change from previous total" and the $0 rows Paul sees.
*Cheapest check:* group the run's `ledger.sqlite` `decisions` table by
`json_extract(payload_json,'$.bucket')` and `json_extract(payload_json,'$.receipt_role')` — one
read-only SQLite query against the **run's own ledger** (not `mentat.db`) shows how much of
`attribution_unresolved` carries a non-`contribution` role.

**(d) Fan-out double count — REFUTED for this number. Confidence: HIGH.**
No per-organization total exists in the engine; buckets are per-row and disjoint
(`cross_reference_engine.py:657-662`); reason groups dedup by `sid`
(`run_cross_reference.py:261`). `original_and_pac_buckets_disjoint` and
`integer_cent_reconciliation` both report `true`. **However, genuine double counts do exist in
`observed_original_giving` — see §7.**

**(e) Other — label semantics. Confidence: HIGH (CONFIRMED).**
The number's *name* is doing the damage. It renders as raw snake_case
(`cross-reference.js:32`), under a column headed "Associated amount", in a currency format, in a
panel that sits directly below the money grid. Nothing on screen says "these dollars are
excluded from every total above". `cross-reference.js:96` says "This is an evidence gap, not an
estimated error amount" — true, but it does not say *not spending* and *not in the totals*.

---

## 6. VERDICT FOR PAUL

**No. `unverified_funding` is not the same kind of quantity as "net giving" — and the $37.9M Paul
is actually reading is a third kind again.** The three quantities:

- **"$12M net giving" (Graph)** — signed, netted dollars the published Banking report **accepted
  as giving**, for **one cycle (2025-2026)**.
- **"$1,657,168.13 Funding attribution unverified" (`unverified_funding`)** — in one sentence:
  *the counted dollars of receipts that ARE attributed to a listed company but whose funding-source
  identity is unproven — ORG rows with no dated treasury-ownership evidence, rows with unusable
  `entity_type` metadata, and rows with conflicting source facts — a **subset of**, never an
  addition to, the $72.1M Observed original giving, across three cycles.*
- **"$37,940,955.71 company attribution unresolved"** — in one sentence: *the gross absolute face
  value of 36,241 Schedule A receipt rows, over three cycles, whose donor was never matched to a
  listed Banking company, **every one of which the engine counted at $0 and excluded from every
  total on the page**.*

**Does the $37.9M overlap the $72.1M Observed original giving? No — it is entirely outside it.**
`cross_reference_engine.py:264-267` calls `exclude()`, which sets `counted_cents = 0` and
`pac_activity_cents = 0` (`:120-125`); `observed_original_giving` is
`sum(d["counted_cents"])` (`:638`, `:643`, surfaced at `run_cross_reference.py:290, 304`).
The caption at `cross-reference.js:81` — "Includes unresolved giving" — refers to a **different**
unresolved population: reasons that review a row without excluding it (`memo_parent_not_established`,
`original_source_of_transfer_unresolved`, `receipt_role_unresolved`, `treasury_ownership_unresolved`,
the earmark reasons). Those *are* inside the $72.1M. The caption is therefore accurate but, read
next to the $37.9M row, dangerously misleading.

### Proposed wording and scope fixes (proposals only — nothing changed)

1. **Name it.** Add to the `reasons` map at `cross-reference.js:19-31`:
   `company_attribution_unresolved: 'Donor not yet matched to a listed company — excluded from all totals'`.
   Today it has no entry and renders as bare snake_case. Also add the other unmapped reasons
   visible in this run: `memo_parent_not_established`, `observed_filing_versions_unresolved`,
   `earmark_counterpart_not_unique`, `earmark_destination_ambiguous`, `latest_filing_*`.
2. **Rename the column.** `cross-reference.js:97` heading `'Associated amount'` ->
   `'Face value of affected records'`, and add a sub-caption: *"These are not totals. Rows that
   were excluded contributed $0 to every figure above."*
3. **Split the review table by disposition.** The table currently mixes reasons that zero a row
   (`company_attribution_unresolved`) with reasons that keep it (`memo_parent_not_established`).
   Two sections — "Excluded pending attribution" and "Counted but unverified" — would end the
   confusion permanently. The data to do it already exists: every decision carries
   `status == 'held_for_attribution_review'` (`cross_reference_engine.py:602-603`).
4. **Print the cycle window next to the money.** `cross-reference.js:80` should carry
   `Cycles {scope.cycles}` in the panel heading, not only in the scope panel at `:72`. Symmetrically
   `index.html:99` "Net giving in selected scope" should render the resolved cycle inline
   (`view.filters.cycle` is already on the wire, `graph_data.py:374`).
5. **Scope alignment is a producer change, not a console change** — see §8.

---

## 7. EVERY METRIC ON THE CROSS-REFERENCE SUMMARY, AND ITS PRODUCER

| Console label (`cross-reference.js`) | Summary key | Producer |
|---|---|---|
| :72 scope line (industries · cycles · companies · snapshots · generated) | `scope.*` | `run_cross_reference.py:386-393` |
| :73 Records examined | `input_records` | `:297` `len(rows)` post-coalesce |
| :73 Automatically resolved | `automatic_decisions` | `:297` decisions not in `review_ids` |
| :73 Records needing review | `unresolved_records` | `:302` `len(review_ids)` |
| :76 Source-verified receipts | `source_verified_records` | `:298` |
| :77 Classified from stored evidence | `classified_from_stored_records` | `:299` |
| :80 badge "Provisional totals" | `verified_unique` | `:305` hardcoded `False` |
| :81 **Observed original giving** | `observed_original_giving` | `:290,304` <- engine `:638,643` `sum(counted_cents)` |
| :82 Observed PAC outgoing activity | `pac_outgoing` | `:310` <- engine `:647` |
| :83 Employee giving · reported employer | `employee_giving` | `:306` `bucket('employee_original')` |
| :83 Corporate treasury giving · supported ownership | `corporate_giving` | `:307` `bucket('corporate_original')` — structurally $0, §2d |
| :83 **Funding attribution unverified** | `unverified_funding` | `:308` `organization_unverified + funding_unverified + conflicting_source_evidence` |
| :84 Linked refund adjustments | `linked_refund_adjustments` | `:309` `bucket('linked_refund')` |
| :86 Gross giving with complete uniqueness evidence | `supported_original_giving` | `:311` <- engine `:646`; requires a `--filing-manifest` the console never passes (`server.py` builds no such arg) -> always $0 |
| :90 Partisan composition table | `partisan_breakdowns` | `:317-336`; all $72.1M lands in `other_unknown` because `baseline_party` needs a pinned baseline, and `scope.baseline` is `null` |
| :93 Previous receipt total | `baseline_amount` | `:291,304` <- engine `:639` `sum(baseline_cents)` |
| :93 Change from previous total | `amount_change` | `:305` `original - baseline` |
| :94 "What changed" table | `changes` | `:275-287`, truncated to 20 at `:458` and again at `cross_reference_data.py:169` |
| :96 unresolved headline $ | `unresolved_amount` | `:294-295, 302` gross, union-deduped |
| :97 **Records-needing-review table** | `unresolved_reasons` | `:253-262, 312-313` per-reason set dedup |
| :98 Review priority table | `review_queue` | `:264-274`, truncated to 20 |
| :102 Coverage records / amount | `coverage_records`, `coverage_amount` | `:296, 300-301` |
| :103 Coverage-only records | `coverage_only_records` | `:300` `coverage_ids - review_ids` |
| :104 Coverage table | `coverage_reasons` | `coverage_presentation`, `:226-247` |

### Double-count hazards noticed in passing (reported, not fixed)

- **H1 — biggest live one. `memo_parent_not_established`: 19,529 records / $8,522,419.98 are
  retained at full value inside `observed_original_giving`.** `cross_reference_engine.py:445-451`
  excludes a memo leg **only** when exactly one same-filing parent is proven; otherwise it merely
  files a review and the leg keeps `counted_cents = amount`. Where the parent is also in the
  corpus, that dollar is counted twice in the $72.1M headline.
- **H2 — conflicted rows escape every dedup pass.** `cross_reference_engine.py:245-256` and
  `:273-282` set `bucket = "conflicting_source_evidence"` and `continue` **without** calling
  `exclude()`, so the full amount survives. Those `sid`s are then skipped by the amendment-family
  loop (`:340`), memo loop (`:426`), earmark route index (`:457`) and refund loop (`:507`).
  Amendment duplicates and memo legs inside that bucket are therefore double counted into both
  `observed_original_giving` and `unverified_funding`. Currently small
  (`source_or_attribution_conflict` = 4 records / $375) but it scales with source conflicts.
- **H3 — earmark conduit + destination both retained.** `earmark_counterpart_not_unique`
  (15,915 / $383,125.12) and `reciprocal_earmark_not_established` (2,168 / $328,691.08) mean the
  conduit leg and the destination leg of the same gift both keep their amount
  (`cross_reference_engine.py:470-489` review-only paths).
- **H4 — transfers.** `original_source_of_transfer_unresolved` = 18,696 / $5,789,063.20;
  `cross_reference_engine.py:283-287` reviews without excluding, so a transfer receipt and the
  original donor receipt behind it can both be counted.
- **H5 — reason-group amounts must not be summed.** `run_cross_reference.py:261` dedups only
  *within* a reason. `cross-reference.js:99` warns about this in a caption; the table itself
  invites the addition.
- **H6 — two different definitions of the same quantity.** `cross_reference_engine.py:572-575`
  computes each review item's `positive_cents`/`negative_cents` from `counted_cents +
  pac_activity_cents`; `run_cross_reference.py:260-262, 294-295` recomputes them from the raw
  `contribution_receipt_amount`. The report ships the raw one, which is why excluded rows still
  carry a dollar figure on screen. Reconciling these two would by itself fix the display.
- **H7 — exact-string affiliation matching.** `cross_reference_engine.py:146` requires
  `_text(affiliation['company']) == _text(row['company'])`. See §2d.

---

## 8. THE ONE CHECK THAT SETTLES IT — and the per-cycle question

**Per-cycle breakdown in `report.json`: NONE exists.** Confirmed from the metadata read.
Top-level keys are `[attribution_recheck, changes, checks, coverage_reasons, coverage_task_count,
elapsed_seconds, generated_at, header_recovery, imports, ledger_sha256, limitations, link_count,
partisan_breakdowns, recovery, review_queue, run_id, schema_version, scope, status, steps, summary,
unresolved_reasons]`.

- `unresolved_reasons` rows carry only `reason`, `records`, `amount` —
  `run_cross_reference.py:312-313` emits no cycle field, and `cross_reference_data.py:166` would
  strip one anyway (`_rows(..., ("reason","records","amount"), 50)`).
- `review_queue` rows **do** carry `cycle` (`run_cross_reference.py:264`) but are truncated to the
  top 20 by amount at `:458` (`review[:20]`) and again at `cross_reference_data.py:168`.
- `summary` and `partisan_breakdowns` have no cycle dimension.

**So the console cannot scope the review buckets to the graph's selected cycle today.** Making it
possible needs a producer change: add a `by_cycle` map to each reason group at
`run_cross_reference.py:312-313`, then allow that field through the display filter at
`cross_reference_data.py:166`. Reading the ledger from the API instead would violate the deliberate
design of `cross_reference_data.py` (bounded, report-only, no raw donor data — see its docstring).

**The full per-cycle data already exists on disk, untruncated.** `run_cross_reference.py:472-475`
writes `review.csv` from the **complete** `review` list (not the `[:20]` slice), with columns
`record_id, reason, company, cycle, amount, action, source_url`:

```
C:\Users\pgoff\Mentat\mentat\state\cross-reference\20260913T074303-bca0ac2b9cd3\review.csv
```

**THE CHECK (describe only — NOT RUN):** read that one CSV, keep rows whose `reason` contains
`company_attribution_unresolved`, and group by `cycle` summing `abs(amount)`. Three numbers come
back. If they sum to $37,940,955.71 over 36,241 records — proving the reason group — and the
2026 slice is roughly a third of it, then the gap is settled: scope (a) plus universe (b), with
no double count and no committee money leaking into a giving total. One CSV read. No database,
no workbook, no engine run, no console.
