# Money record/replay procedure

Prepared 2026-10-16 from the 2026-10-14 design. The private
`audits/deploy_20261011/MENTAT_MONEY_RUNBOOK.md` is optional historical context;
it is not required to publish this page. Verify CLI details against selected
Mentat `COMPUTE.md` and `tools/replay_parity.py`. No collector is started by this skill.

## Budget and identity

The old design estimated 25-60 requests per small collect-fanout snapshot and
200-300 for a whole proof; one historical pac-evidence example measured 38. These
are planning examples, not current API limits or guaranteed costs. Use the current
provider/key budget and explicit execution scope. Count actual R0 interactions.

Keep the conservative design stops: at most 600 candidate records for a tiny fanout
input and stop after F1 if R0 exceeds 150 requests; do not enlarge them to complete
a run. Any current lower limit also applies. Retired snapshots, missing image
identities or dirty/moved HEADs cannot be accepted as current proof.

## Sequence for each authorized snapshot

1. Verify source SHA/clean selected inputs, exclusive job/key ownership, Docker,
   authenticated image digest, clock and projected disk headroom. Keep paused
   collection batches and unrelated report jobs unchanged.
2. Preserve an immutable copy of the selected Melange `ops/compute/http_replay.py`
   in the private replay root; record its SHA256. Set `MELANGE_HTTP_REPLAY` only in
   owned child processes. Do not let another lane's proxy edit alter the snapshot.
3. Read the selected `mentat/compute.images.lock`; validate its digest/source under
   the existing trust policy. Pulling or running that image requires current scope.
   A stale digest from this document is not a substitute.
4. Review plan-only wrapper output for `pac-evidence` and `collect-fanout` before
   execution; do not print key values or cassette contents.
5. Create uniquely named snapshots. For each: `snapshot`, `record --plan`, R0
   `record` (LIVE, spends quota), `replay --side A1`, `replay --side A2`,
   `replay --side B`, then `judge`. Verify the actual CLI in selected source.
6. Complete three accepted pac-evidence snapshots, then the three small fanout
   snapshots under the F1 budget gate. Use accepted input criteria; old committee,
   employer and cycle examples are not an instruction to collect them now.
7. Read `reports/R0.replay.json` for actual interactions and secret-leak status, and
   `reports/judge.json` for all gates. Snapshot names identify distinct immutable
   attempts; do not overwrite failed evidence to manufacture a streak.

## Passing and stopping

Both job status reports must show streak 3 with `cut_over_needs` 3; every judged
snapshot must be `ok` and `complete` with an actual B run. Require no secret leak,
no replay misses and no refused TLS hosts. Exact row counts, Decimal sums and
multiset digests must agree across A1/A2/B and R0 versus A1. Never mask money values.

A changed source identity, competing collector, exceeded budget, dirty/failed
record or failed judge stops progression and cutover. Use the job's existing
bounded timeout and supported owned cancellation policy; the old 30-minute
observation is not a universal kill threshold. Never issue a broad Python kill.
Retain private evidence and applicable secret-leak cleanup/refusal behavior;
do not move a leaked cassette into a public report or silently retry it.

## Launch transition

Mentat money historically launches through `app/server.py` and its report/PAC
entry points. Verify the current call graph. Melange's `cutover.py set collect
container` does not switch Mentat money. A launcher change needs current scoped
authorization and exact acceptance of unchanged counting semantics plus rollback.

Historical wrapper exits: 0 verified; 1 failed/unverified receipt; 2 refused;
3 Docker/clock failure; 75 lock held; 124 timeout. Check the selected implementation
and report nonzero exits honestly rather than relaxing receipt or trust gates.
