# Wiring the Mentat money pipeline and industry spending into Melange

Prepared 2026-10-06. This document is a design plan. It changes no code. It
describes how to take Mentat's FEC money and the industry spending it measures
and feed them into the Melange engine (the flip model, the optimizer, the member
desk, and the competitiveness multiplier).

Two standing rules govern every step below.

1. **Mentat's money collection is frozen.** Melange reads Mentat's outputs. It
   never changes `R/collect.R`, `R/schema.R`, `inputs/fec_receipt_rules.json`,
   `tools/pac_evidence.py`, `tools/cross_reference_engine.py`, the money logic
   in `app/flow_data.py`, or the rules in `METHODOLOGY.md`. Any change to those
   needs Paul's approval for that specific change.
2. **A new money source enters behind a dial that defaults to off.** It
   follows the same pattern as `COMPET_MULT`. With the dial off, the run must
   be byte-identical to today's. Paul approves before the dial goes on.

## 1. What Melange measures today

| Item | Where | What it is |
|---|---|---|
| Collector | `fec/collect/refresh_fec_money.py` | OpenFEC Schedule B, disbursement types 24K/24Z, for the current two-year cycle. It fully replaces the previous data rather than adding to it. |
| Committee scope | `fec/attic/full_congestion.py` (the `CU`, `BANKS`, `FINSERV` lists) | A fixed list of credit union, bank and financial-services PACs. Each committee belongs to exactly one group. |
| Candidate map | `fec/legislators.csv` (`fec_ids`, `bioguide_id`) | Maps FEC candidate IDs to bioguide IDs. |
| Out of scope today | the collector's docstring | Individual (employee) contributions, PAC-to-PAC transfers and independent expenditures. |
| Gate | `fec/engine/apply_fec_money_refresh.py` | Requires `fec_refresh_current.json` to have status PASS, be at most 8 days old, and match every hash. The roster must be identical. |
| Fields written | `data/engine/congestion.json` | `cu`, `banks`, `finserv`, `receipts`, `total`, the `_pct` and `_adj` ratios, `industry_adj`, `net_lean`, `money_source_status`. |
| Engine use | `fec/engine/flip_model.py:37-46` | `cu0 = cu`, `ind0 = banks + finserv`, `R = max(receipts, 200000)` (median imputed when missing). Unobserved industry money gets the median (`IMPUTE_IND0`, D-071). |
| Money curve | `flip_model.pflip` | `WM·pm·(c·cu+1)/((c·cu+1)+HALFF·R)` against the same expression for `c·ind`. WM = 0.35 is the money weight and WP = 0.65 the peer weight. |

In short, Melange sees only one channel, PAC checks written directly to
candidates, and only from a hand-kept list of committees.

## 2. What Mentat measures

Mentat (`C:\Users\pgoff\Mentat\mentat`, an R pipeline plus Python tools) collects
FEC money by employer and committee for each industry book: Credit Union,
Community Banks, Credit Arms, Crypto, Fintech, P&C Insurance and Banking. It
classifies both donors and recipients.

| Mentat output | Key columns | What Melange gains |
|---|---|---|
| Store table `contributions` (`R/schema.R:13`) | `sub_id`, `committee_id`, `contribution_receipt_amount`, `industry`, `company`, `two_year_transaction_period`, the leg flags (`is_conduit_leg`, `is_memo_leg`, `is_passthrough_leg`, `superseded_by_amendment`, `duplicate_*`, `is_refund`), `company_match_status` | Employee and executive giving, attributed to companies. |
| Tidy sheet **Recipient Facts** | `cycle_label`, `company`, `committee_id`, `employee_tier` | Money by recipient committee, including candidate committees. |
| Tidy sheet **Committee Sponsors** | `committee_id`, `candidate_id`, `link_source` | Maps a committee to its candidate. This is the bridge to bioguide. |
| Tidy sheet **Downstream Activity** | `source_committee_id`, `candidate_id`, `activity_type`, `support_oppose`, `net_included_amount` | What industry PACs, leadership PACs and super PACs did for or against each candidate, including independent expenditures. |
| Tidy sheet **Network Candidate Activity** | `company`, `candidate_id`, `support_amount`, `oppose_amount`, `associated_funding` | Company-attributed reach into each candidate. |
| Tidy sheet **Allocation Estimates** | `funded_committee`, `candidate_id`, `direction` | Mentat's estimate of how pooled money reaches candidates. |
| Tidy sheet **Source Freshness** | `cycle_label`, `fec_dataset` | Freshness gates. |
| About sheet | `Source DB SHA-256: <hex>` | Provenance hash for the import receipt. |

The tidy workbook (`<Industry> Industry Spending Data.xlsx`, built by
`tools/build_tidy_workbook.py`) is the stable published contract. The SQLite store
is richer but is Mentat's own working file. **Recommendation: read the tidy
workbook.** Verify its About-sheet hash against the store, and never open the
store for writing.

## 3. Target design

### 3.1 New producer: `fec/collect/import_mentat_money.py`

- **Inputs, read-only:** each industry's tidy workbook, plus `fec/legislators.csv`
  and `data/engine/congestion.json` for the roster.
- **Output:** `data/money/mentat_money_projection.json`. It contains:
  - **Header:** schema, workbook paths and sha256s, the store hash from each About sheet, the cycles covered, the industry-to-side map, the channel weights, and the roster hash.
  - **Per member, keyed by bioguide:** for each industry, channel and cycle, the `net_included_amount`, the source row counts, and the join status.
- **Join:** `candidate_id → bioguide` through `fec_ids` in `fec/legislators.csv`, the
  same map `refresh_fec_money.candidate_map` uses. A candidate committee reaches
  its candidate through Committee Sponsors. Unmatched candidate IDs are counted
  and listed, never dropped silently.
- **Amounts:** use Mentat's included or net amounts as given. Never re-derive them
  from raw rows. Conduit, memo, pass-through, amendment, duplicate and refund
  legs are already resolved by Mentat's frozen rules, and re-deriving them would
  be a second, competing money rule.
- **Deterministic:** no timestamps in the body, so a re-run with the same inputs
  writes identical bytes.
- **Chain slot:** right after `apply_fec_money_refresh.py`, before
  `build_competitiveness.py`.

### 3.2 Industry-to-side map (Paul rules)

The engine has two sides. `cu` is the side we fund. `ind` is the opposing money
on the same member.

| Mentat book | Proposed side | Note |
|---|---|---|
| Credit Union | `cu` | Our side |
| Community Banks | `ind` | Today's `banks` group |
| Banking (large banks) | `ind` | |
| Credit Arms | `ind` | Today's `finserv` overlaps here |
| Fintech | `ind` or context only | Ruling needed |
| Crypto | context only | Not in the CU-versus-banks contest. Could feed the per-topic engine for crypto topics. |
| P&C Insurance | context only | Same as Crypto |

### 3.3 Channel weights (Paul rules)

| Channel | Mentat source | Proposed weight |
|---|---|---|
| Direct PAC to candidate | Recipient Facts (company PAC to candidate committee) | 1.0 (today's scope) |
| Employee and executive giving to candidate | Recipient Facts by `employee_tier` | 1.0 for Chief tier; lower for Employees (ruling) |
| Leadership PAC to candidate | Downstream Activity | Ruling |
| Independent expenditure, support | Downstream Activity (`support_oppose = S`) | Ruling. It is not a check to the campaign, so arguably less than 1. |
| Independent expenditure, oppose | Downstream Activity (`support_oppose = O`) | Counts against the member, so it is not added to either side. Ruling. |
| Pooled or pass-through estimate | Allocation Estimates | Context only at first. Mentat labels it an estimate. |

Each channel stays a separate field in the projection, so Paul can change a
weight without re-running the import.

### 3.4 How the engine reads it

- **New dial `MONEY_SOURCE`:**
  - `fec` (the default) is exactly today's behaviour and reads no new file.
  - `mentat` builds `cu` and `ind` from the projection, using the map and weights above.
  - `blend` uses the FEC direct-PAC fields where they exist and Mentat for the other channels.
- **Single entry point:** one kernel accessor, `moneyball_core.money(n)`, returns
  `(cu, ind, status)`. `flip_model.py:39`, `per_topic_flip.py`, `optimize.py`,
  `budget_frontier.py`, `lt_priming.py`, `salience_shock.py`, the dashboard bundle
  and `desk_roi` all read it. Today each one reads `congestion.json` directly.
  This is the same single-entry pattern as `cmult`, so no consumer can drift.
- **Unchanged:** receipts `R` stays the FEC total receipts in `congestion.json`,
  so the saturation scale `HALFF·R` does not change. `congestion.json` itself is
  not rewritten.
- **D-071 median imputation for unobserved industry money still applies.**
  "Unobserved" becomes "no Mentat row and no FEC row", and with Mentat, far
  fewer members fall into it.
- **The competitiveness multiplier applies unchanged:** `c·cu` and `c·ind`.
  Because Mentat's `ind` is larger, c then amplifies more opposing money.

### 3.5 Industry spending beyond candidate money

Mentat's industry totals (company-level spending, share by recipient category)
and Melange's lobbying data (LobbyView/LD-2) are different measures. Recommended
uses:

- **Member desk:** a new "industry money on this member" panel showing CU versus
  opposing industry dollars by channel and cycle. It is display only, with no
  rank effect.
- **Efficiency section:** an "industry share" column, CU dollars ÷ (CU + opposing
  dollars) for each member, next to ROI.
- **Per-topic engine:** crypto and P&C money feeds only the topics they belong to.

Do not use the LD-2 lobbying link as a member-level money input. LD-2 never
names the member, and the link is circular (see the memory note on lobbied
links).

## 4. Gates before the dial goes on

1. **Reconciliation fixture.** For each member, Mentat's direct-PAC channel,
   restricted to the committees on today's `CU`, `BANKS` and `FINSERV` lists,
   must reproduce Melange's current `cu`, `banks` and `finserv` within a stated
   tolerance (proposed: $1 per member, 99% of members exact). Every difference is
   explained before going further. This is the graduation gate, as the Crypto
   fixture was for Mentat.
2. **Dial off.** All engine outputs must be byte-identical to today's, as was
   proven for COMPET_MULT.
3. **Candidate run, `MONEY_SOURCE=mentat`.** Outputs are redirected to
   `data/system/mentat_money_candidate/`. Check that ranks are unchanged
   (`compute_pillars` reads no flip output), the pot is conserved, and the
   certificate stays valid. Then write an allocation-delta report for Paul.
4. **Freshness.** The import refuses a workbook whose Source Freshness is older
   than the rule Paul sets (proposed: the same 8 days as the FEC refresh). It
   refuses a workbook whose About hash does not match the store.
5. **Kernel tests and the audit.** There is no new red. The new artifact is
   added to `dashboard_integrity` fingerprints and the system-manifest inventory.

## 5. Build order

1. The import producer, its tests (join, channel split, refusal cases), and the
   reconciliation script (gate 1). Melange only; nothing in Mentat changes.
2. Paul's rulings on the side map (3.2), the channel weights (3.3), the cycle
   window, and the freshness rule.
3. The kernel accessor `money(n)` and the `MONEY_SOURCE` dial (default `fec`).
   Then repoint the eight consumers and prove dial-off is byte-identical (gate 2).
4. Candidate run and allocation-delta report (gate 3). Paul decides whether to
   turn it on.
5. The desk and efficiency display panels (3.5).
6. Docs: `MATHEMATICAL_SPECIFICATION.md` standing dials, the config-and-flags
   catalog, and a brain decision entry.

## 6. Open rulings for Paul

1. The side map, especially Fintech, Credit Arms and Banking (3.2).
2. Channel weights, especially employees by tier, independent expenditures
   and leadership PACs (3.3).
3. The cycle window. The options are the current cycle only (today's rule), or
   a rolling three cycles to match the six-year lookback directive.
4. The freshness rule for Mentat workbooks.
5. Whether `blend` is wanted, or a clean switch from `fec` to `mentat`.
6. The tolerance for the reconciliation fixture.

## 7. Risks

- **Double counting across channels.** A company's PAC check and its
  executives' personal checks to the same candidate are separate money. Mentat
  already marks pass-through and conduit legs, so if Melange keeps its own
  amounts, the same dollar should not count twice. The reconciliation must
  confirm this.
- **Coverage gaps carried over.** Mentat's trade-association register coverage
  is uneven (P&C about 10%, Credit Arms about 56%). Opposing money is
  understated where coverage is thin, so the projection should carry a
  coverage figure for each book.
- **Size of the money arm.** Adding channels raises `cu` and `ind` for many
  members, and members saturate sooner against `HALFF·R`. The money curve's
  ceiling (WM = 0.35) does not move, but allocations will shift noticeably.
  That is what the candidate run measures.
- **Stale workbooks.** The industry books are refreshed on different
  schedules. The freshness gate decides, for each book, whether a stale one is
  dropped or holds the run.
