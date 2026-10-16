# Evidence and parity

Prepared 2026-10-16 from the 2026-10-14 compute procedures. The standards below
preserve their safety gates; historical D-177/D-196/D-198/D-201/D-202 labels are
optional local context, not fresh authority. Validate the selected tool version
and current accepted contract before running a procedure.

## Current facts and proof

Record UTC observation time, exact checkout, full commit, dirty-state disposition,
image digest, input manifest and evidence SHA256. Do not copy a current HEAD, image,
free-space figure, engine state or task state from a handoff. State scripts provide
bounded local metadata only; absence of a lock file does not prove no writer exists,
and presence of an evidence file does not prove its contents or provenance valid.

Local ancestry, remote source receipt, packaged source provenance and installed
bytes are different claims. A passing test in a dirty tree does not certify HEAD.
A wrapper exit code or another agent's completion notice is not a substitute for
the actual result, scope and changed-byte evidence. Report failures and unverified
phases rather than attributing them to the baseline without a comparison.

## Equivalence gates retained from the source procedures

| Output | Required comparison |
|---|---|
| `ranks_python.json`, `dashboard_data.json`, `bipartisan.json`, Terrier bundle ZIP | Byte identity |
| Ranks, percentiles, thresholds, flags and labels | Exact in the same run |
| Workbooks and SQLite stores | Every compared cell value and table row; only the explicitly accepted numeric/variance rules below |
| Workbook continuous numeric cells | At most 1024 ULP only when all ranks, percentiles and thresholds in that same run match exactly; otherwise refuse the tolerance |
| Other continuous floats | At most the accepted general 4-ULP bound; never apply this to money, ranks, flags or labels |
| FTS5 shadow tables | Equivalent rebuilt form using one library plus 400 MATCH-query rowid comparisons; contentless tables remain exact |
| Text outputs | Byte identity with the required writer line endings; no blanket EOL normalization |
| Mentat money | Equal row counts, exact Decimal sums and multiset digests across A1/A2/B and R0 against A1; never mask money values |

Do not widen numeric tolerances, masks or accepted populations to make a failing
run pass. The 1024-ULP and FTS5 rules were implementation choices recorded in the
older procedure; confirm their applicability in the selected harness. Record the
compared population, and do not substitute a smaller subset for the expected
533-member office rank check without a separately reviewed contract change.

The historical lighter procedure used one Windows reference and one container run
from identical frozen inputs. Some chain/replay harnesses require A1 and A2.
Do not omit A2, pass A twice, invent a noise mask or mark a missing run complete.
Resolve the harness/accepted-procedure mismatch before execution.

## Evidence consumed by gates

| Lane | Expected evidence |
|---|---|
| Melange chain | `chain_parity.json`: PASS, exit code 0, no failed gates |
| Melange collect | `collectors_replay.json`: PASS for the actual replay scope |
| Office | `office_equivalence.json`: equivalent with cells compared > 0; `office_rank_check.json`: PASS, 533 members, 533 exact ranks |
| Mentat money | Per-snapshot `reports/judge.json`, complete B run and both job streaks 3 of 3 on the same accepted identity |
| Terrier | `parity_report.json`, precise steps/districts, expected negative controls detected |

Melange's default evidence directory is `audits/compute_parity`; check any explicit
`MELANGE_PARITY_DIR` override. Mentat replay roots and Terrier scratch directories
are private runtime locations, not source publication inputs. Check existing
evidence against the exact selected source, images and inputs before relying on it.

A downstream semantic difference invalidates a claimed pass. Stop the cutover and
report it; use a preauthorized safe fallback only within current scope. Preserve
negative-control failures as evidence. Do not delete recovery evidence on a generic
instruction to clean up parity copies.

Keep existing bounded application audit events where implemented. These skills do
not require installing or re-enabling global observer hooks, or starting an extra
logging process for every command. Receipts must not contain credentials or private
data rows; record paths and hashes only where their disclosure is permitted.
