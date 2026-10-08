# W2 Tier-1 direction wiring report

Date: 2026-07-25

Archive basis: `congress_bills_archive_20260624_115822.xlsx`, SHA-256
`4ca1c81af641a2e255ab54cd78dc4c8eb43aa7d2c156893c753cdbe4faa05a73`.
The machine-readable decision ledger is `audits/legfix3/wiring_report.json`.

## Outcome

The upgraded registry contains 126 rows: 62 Congress-resolved existing rows, 47 accepted
ACU rows, and 17 accepted queue rows. Directions are 107 support, 12 oppose, and 7 neutral.
Fourteen Congress-blank rows are archive-absent and inert today; 112 rows currently resolve
to archive instances. Of those, 50 are newly wired rows.

The original 60-row registry expands to 62 rows because H.J.Res.50 resolves to Congresses
118 and 119 and H.R.166 resolves to Congresses 117 and 118. Its restored source category
semantics are 49 `CFPB:Reduce`, 5 `CFPB:Expand`, and 6 `CFPB:Neutral`; after the two
cross-Congress expansions they are 50, 6, and 6 respectively. The builder continues to
ignore Category in the direction registry.

Source resolution produced 180 provisional instances: 62 existing, 61 ACU, and 57 queue.
Quarantine ran first and removed seven title mismatches. Keep-earlier precedence then made
47 decisions, leaving 126 rows. Every precedence overlap had the same direction, so the
precedence phase creates no sign flip.

## Precedence decisions

Precedence is existing registry, then `cu_bill_directions.json`, then
`bill_direction_queue_FILLED.csv`. The 47 kept/dropped decisions are:

- Existing kept over ACU (11): H.J.Res.59/119, H.R.1652/119, H.R.2331/119,
  H.R.3445/119, H.R.4735/119, H.R.654/119, H.R.940/119, H.R.976/119,
  S.2419/119, S.557/119, and S.J.Res.18/119.
- Existing kept over queue (9): H.R.1806/118, H.R.4735/119, H.R.654/119,
  H.R.6732/117, H.R.7000/118, H.R.941/119, S.2419/119, S.J.Res.18/119,
  and S.J.Res.32/118.
- ACU kept over queue (27): H.R.1791/119, H.R.1799/119, H.R.1919/119,
  H.R.2094/119, H.R.2543/117, H.R.2702/119, H.R.2808/119, H.R.3170/118,
  H.R.3380/blank, H.R.3633/119, H.R.3709/blank, H.R.4167/119,
  H.R.4437/119, H.R.4544/119, H.R.4568/119, H.R.507/119, H.R.6644/119,
  H.R.7056/119, H.R.975/119, S.110/119, S.1467/119, S.1582/119,
  S.1978/blank, S.2019/119, S.2486/119, S.3017/119, and S.522/119.

The JSON ledger records kept source, dropped source, and both directions for every decision.

## Title-mismatch quarantines

The pinned matcher applies NFKC, casefolding, whitespace collapse, and punctuation stripping.
It accepts equality, substring in either direction, token-set Jaccard at least 0.6 after the
pinned stopword removal, or a matching all-caps acronym expansion. Failure quarantines the
instance before precedence.

- ACU H.R.2392/119: `GENIUS Act` does not match archive `STABLE Act of 2025` /
  `Stablecoin Transparency and Accountability for a Better Ledger Economy Act of 2025 or
  the STABLE Act of 2025`.
- ACU S.2704/117: `CDFI Fund Transparency Act` does not match archive
  `Small Business Surcharge Relief Act`.
- ACU S.919/117: `GENIUS Act` does not match archive `21` / `Data Care Act of 2021`.
  Its matching 119th-Congress GENIUS instance is wired.
- Queue H.R.4479/119: `SUPPLY Act – Supporting Upgraded Property Projects and Lending for
  Yards [title-matched HR4568]` does not match the archive accessory-dwelling-unit
  second-lien title.
- Queue H.R.4763/118: `Anti-CBDC Surveillance State Act [title-matched S1124]` does not
  match archive `Financial Innovation and Technology for the 21st Century Act`.
- Queue H.R.6955/119: `Protecting Access to Credit for Small Businesses Act
  [title-matched S2486]` does not match archive `Main Street Act`.
- Queue S.394/119: `Anti-CBDC Surveillance State Act [title-matched S1124]` does not match
  archive `GENIUS Act of 2025`.

## Inert archive-absent rows

The 14 Congress-blank rows are H.R.1 (neutral), H.R.1640, H.R.3380, H.R.3709, H.R.4460,
H.R.4478, S.52, S.427, S.1071, S.1880, S.1978 (oppose), S.3052, S.3443, and S.3940.
They preserve adjudication and match any future archive instance of the same type-aware bill
key, but they affect no current archive cell.

## Skips

- ACU H.R.1 is `MONITOR`, so it is not a position and is skipped. The queue's separately
  adjudicated H.R.1 direction 0 is retained as an inert neutral row.
- ACU H.R.8398 and H.R.8413 have blank positions and are skipped.
- The remaining 159 queue rows have blank `direction_+1_0_-1` values. Exact `1`, `-1`, or
  `0` is required, so all 159 are skipped. Their complete bill list is in the JSON ledger.

## Predicted effects and verification boundary

The registry adds 50 archive-active direction rows and 14 inert rows. Existing precedence
decisions do not flip signs. Six active registry rows remain adjudicated-neutral exclusions;
the seventh neutral is archive-absent H.R.1. The three category-only overrides reroute
S.J.Res.18/119 and H.J.Res.59/119 to CFPB and H.R.6955/119 to CU Capital Requirements.

No runtime cell-delta count is claimed here because this lane has no Python. Claude must run
the scratch-only commands in `RUNBOOK_W2.md`; any write beneath the live data root is an
abort condition.
