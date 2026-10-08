# Project Brain update draft — refresh completion, 2026-09-20

Prepared for Paul to apply and commit under the repository's CLAUDE.md boot contract.
These proposed IDs were unused when checked; recheck numbering before applying.

## STATE.md — add to Current position

- REFRESH TICK CODE LANDED (2026-09-20, Codex completion of the vibrant-sammet handoff): the tick runner, sealed-run press tombstones/review, missing-promoted-run handling, and process-identity lease fix are on main at `1d6b3793a1f496ff07f4b460010c882969dd63eb`. Sandbox fixes cover shared-file zero floors, clock-free publication generations, stale inherited leases, manifest read retries, step budget sharing, producer-import isolation, bounded review history, and explicit owner zero acceptance. Additional independent probes found and fixed publication of externally damaged evidence, zero verdicts cleared by successful no-ops, and locked manifests losing their baseline when a collector was due; unrepaired damage now survives failures and console interruption. A further crash-after-failure race is closed by a durable pending-failure flag cleared at normal tick completion, with normal-failure cooldown preserved. Validation: final runner 64 passed, 4 focused LIVE tests passed, affected suites 158 passed; broad LIVE kernel: 250 passed / 2 failed (the two pre-existing baseline failures) at a7a11b5df1c123568a0672138bb1318d858be9a0 before the final two-file restart-race follow-up. The fold default and R retry opt-ins remain HELD by revert commit `3a1f2586b`; MoneyballWeeklyRefresh still launches weekly_refresh.py. No real collection, rank recomputation, paid AI invocation, scheduler cutover, or scratchpad deletion was performed. Operational publication remains subject to the existing press coverage, intake, audit, and reference-layer blockers listed in the original handoff; their live resolution was outside this code landing. Receipt: audits/refresh_tick_20260919/COMPLETION_20260920.md.

## DECISIONS.md — proposed entry

## D-063 — Refresh completion is per source and publication requires verified evidence
Date: 2026-09-20
Status: IMPLEMENTED; scheduling and the two press opt-ins remain held
Decision: Implement the accepted tick-runner contract: bounded independent collection, filed failure retries, per-step manifests and generations, crash reconciliation, and publication only from evidence that is present, intact, coverage-accepted, and inside the freshness window. Publication compares source generations rather than wall-clock ordering. A temporarily unreadable manifest preserves durable step history but defers that step and publication until the baseline is readable. A failure or a no-op cannot repair known damaged output; a rewrite or restoration of the committed bytes can. An owner may explicitly accept a zero-floor verdict with --accept-zero NAME, recorded for review.
Context: The 2026-09-19 accepted design contract in audits/refresh_tick_20260919/CONTRACT.md; Paul's 2026-09-20 request to finish PROGRESS_AND_NEXT_STEPS.md. Code landing `1d6b3793a1f496ff07f4b460010c882969dd63eb` includes the documented hold commit for fold default ON and gated R revisits.
Rationale: Crash recovery alone did not prevent plausible empty outputs, shared-file ownership from hiding a collapse, clock reversals from hiding new evidence, or a locked manifest from discarding the baseline needed to judge the next run.
Reversal condition: Measured production evidence shows the verification or recovery contract rejects legitimate source output; change the contract and its adversarial tests together, retaining fail-closed publication and explicit owner treatment of coverage exceptions.

## DEADENDS.md — proposed entry

## DE-046 — A fresh timestamp or successful exit does not prove evidence is intact
Date: 2026-09-20
Approach: Decide new evidence by last_ok_utc > last_publish_utc, retain a zero-floor baseline only while the source owns its file, and treat a later successful no-op as recovery from a damaged-output or coverage failure.
Failure mode: Sandbox clock reversal left new evidence unpublished indefinitely; shared-file handover hid a 60-row-to-empty collapse. Independent completion probes published a header-only file changed between ticks, cleared a shared-file zero verdict after a no-op, and accepted empty output when a locked manifest hid the previous baseline.
Root cause: Wall-clock order is not a commit identity; output ownership is not producer history; a zero exit code is not proof that previously damaged bytes were repaired. Ignoring an unreadable manifest can discard the very evidence required to evaluate the next run.
Would reconsider if: Never as the sole evidence of integrity. Use publication input generations, per-producer produced-row history, retained coverage and damage verdicts, readable manifests, and output verification. Timestamp-only touches with identical content are harmless and must not force collection. Reproductions and positive controls: audits/refresh_tick_20260919/completion_evidence/.
