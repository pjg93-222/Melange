# FEC bulk rows land as 'unsupported' — a channel mapping for Paul to rule on

Date: 2026-09-16 · Lane S3b (PAC evidence: any file type, any path) · Architect A
Status: PROPOSAL ONLY. Nothing here is implemented. `normalize()` is unchanged.

## What happens today

S3b reads FEC bulk files (a bulk `.zip`, or a pipe-delimited `.txt` under a known
bulk name) and everything about them resolves except the channel: `CMTE_ID`,
`NAME`, `TRANSACTION_DT` (MMDDYYYY) and `TRANSACTION_AMT` all map onto existing
columns, so committees, counterparties, dates and amounts are read correctly and
the import reaches `ready`. But every row is recorded `unsupported`, because
`normalize()` decides a row's type from `record_type / activity_type / schedule /
schedule_type / type / transaction_type`, and a bulk row carries its type in
`TRANSACTION_TP` (key `transaction_tp`), which is not one of those names. The
consequence is visible: a 5-row bulk import shows 5 rows, 5 unsupported, no
totals. This is a data rule, not a bug in the reader, so it goes to Paul rather
than into this lane's code.

## The proposal, in one paragraph

Add `transaction_tp` to the tuple of type columns `normalize()` reads, and give
`TYPES` the FEC transaction-type codes, so that a bulk row is classified by the
code the commission assigned it: map the individual/committee **receipt** codes
(`15` contribution, `15E` earmarked contribution, `15J` memo split among
affiliated committees, `15C` contribution from the candidate, `15Z` in-kind from
the candidate, `11` tribal contribution, `10` Levin/non-federal receipt, `19`
electioneering-communication donation, `30`/`31`/`32` convention and headquarters
account receipts) to `receipt`; map the **disbursement** codes (`20`-series
refunds and rebates, `22Y` contribution refund to an individual, `24K`
contribution to a non-affiliated committee, `24Z` in-kind made to a candidate,
`24G` transfer out to an affiliated committee, `24R` recount disbursement, `24C`
coordinated party expenditure) to `disbursement`; and map only the two
independent-expenditure codes to `independent_spending`, with the direction taken
from the code itself rather than from a `support_oppose` column that bulk files do
not have — `24E` (independent expenditure **advocating** a candidate's election)
to Support and `24A` (independent expenditure **opposing** a candidate's election)
to Oppose, with `24F` (communication cost **for** a candidate, Form 7) and `24N`
(communication cost **against**) following the same pairing if Paul wants Form 7
rows counted as spending at all. Every code not on the ruled list stays
`unsupported` and remains visible in the row table, exactly as an unrecognised
type does today; that is the conservative default and it is what keeps a wrong
guess out of a total.

## What this would touch (for scale, not for approval)

- `mentat/app/evidence_csv.py`: the type-column tuple inside `normalize()`
  (one name added), the `TYPES` table (the codes above), and a direction source
  for `24A`/`24E`/`24F`/`24N` that does not depend on a `support_oppose` column.
- Nothing else: the readers, the store, the HTTP surface and the totals path are
  already correct once the row carries a `kind`.

## The honesty caveat on the code list

The codes above are the ones I am confident of from the FEC's published
transaction-type table, but that table is authoritative and versioned, and I did
not read it from a file on this machine (no `*_header_file.csv` or code table is
present under `mentat/inputs`). Before any of this is implemented, the list
should be checked against the commission's own current "Transaction type code"
table — several `15`- and `24`-series suffixes are memo-only entries whose
inclusion would double-count against the parent transaction, and memo rows
(`MEMO_CD = 'X'`) are a separate question from the type code: they are already in
the file and would need their own ruling about whether they enter a total at all.

## The question for Paul

1. Are the three mappings above the ones you want (receipt / disbursement /
   independent spending, with `24E`→Support and `24A`→Oppose)?
2. Do Form 7 communication costs (`24F`/`24N`) count as independent spending here,
   or stay unsupported?
3. Do memo rows (`MEMO_CD = 'X'`) enter totals, or stay visible-but-unsupported?
