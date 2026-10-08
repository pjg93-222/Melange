# Fable C5 bounded-concurrency code review

`VERDICT: PROCEED`

Fable reviewed the repair implementation, its collector dependency, the tests, the receipt schema, and publication semantics read-only with no network access. No blockers were found. The reported full-suite result (`92 passed, 45 subtests passed`) was treated as supplied evidence rather than independently rerun in the read-only lane.

## Findings

1. **Medium, non-blocking hardening:** two offline legacy sites compare raw ISO timestamp strings. Mixed UTC offsets could cause a loud false ordering failure or an imprecise gap-window start around a DST edge. Online validation parses aware datetimes, and final per-year source-count conservation fails closed, so this is not a silent data-integrity risk.
2. **Low, fail-closed:** an exact-second cohort larger than 25 deliberately stops the run. The measured sealed maximum is four.
3. **Low, availability only:** already-running futures drain their retry envelopes after the first worker failure. No manifest can be written and the original exception re-raises.
4. **Trivial:** Ctrl-C is not caught by the run's `Exception` handler, so a deliberately interrupted generation needs a separate supersession/interruption receipt.

## Binding launch condition

The sealed legacy page-shape audit must pass before the first live batched run. Codex completed that independent rerun after the review prompt was submitted: 21,599 pages, 539,870 objects, zero page-shape violations, all 88 duplicate occurrences identical and at the same exact timestamp; overall `pass=true` and `page_shape_pass=true`.

## Evidence reconciliation

| Plan condition | Result |
|---|---|
| Page 1 alone; exact `max(1, ceil(count/25))`; zero/divisible controls | PASS |
| Worker threads perform transport only; caller validates/writes ascending | PASS |
| One shared lock-protected 120-RPM start pacer; sleep outside lock; retries paced | PASS |
| Fresh opener per production request | PASS |
| First worker failure cancels/drains/re-raises; no manifest | PASS |
| Bounded in-flight, spacing, drift, failure, ordering, and sequential/batched equivalence controls | PASS |
| Offline sealed-sweep page-shape audit | PASS (independently completed after prompt submission) |

The receipt does not overclaim: its page-size, concurrency, and transport constants match the production defaults; PASS receipt construction occurs only after all validation and conservation checks.
