# Opus 5 max restored-evidence canary receipt

Packet generation:
`97a4cea6f3306576fb1bedfe91571b0371560058368bfb943229ad26e72c3036`

Packet SHA-256:
`736119a69c0c643eaadddafad73978b7f0540d5468cd8773a8353accbb145b56`

## Initial restored canary

Run: `opus5-max-restored-canary25-20260728b`

Status: `STOPPED_DO_NOT_RESUME_OR_MERGE`

The initial per-call limit was the estimated visible-token reservation. Opus
max exhausted that ceiling before returning a valid structured proposal on
the first call. The exact process tree was stopped to prevent repeated
systematic failures.

- Provider call starts: 4
- Terminal provider-failure receipts: 3
- Call start without a terminal receipt: 1
- Accepted structured responses: 0
- Conservatively accounted cost: USD 1.611945
- Affected candidates:
  `119:hr:3230`, `119:hr:4538`, `119:hr:6202`, `119:hr:7775`

All four candidates are permanently excluded from automatic replay. Their
receipts or call-start records remain immutable audit evidence but are not
admissible adjudication proposals.

## Replacement canary

Run: `opus5-max-restored-canary10r2-20260728c`

Status: `COMPLETE_PROPOSALS_ONLY_PENDING_HUMAN_RATIFICATION`

The replacement run automatically excluded every candidate with a call start
in the initial restored canary. It reserved a minimum of USD 2.00 from the
aggregate cap for each dispatch, used one worker, permitted at most five
provider calls, and retained the USD 10.00 aggregate ceiling.

- Selected candidates: 10
- Provider calls: 5
- Accepted structured responses: 5
- No-call ceiling receipts: 5
- Category proposals: 190
- Membership proposals: 18
- Effective membership proposals:
  - include: 1
  - exclude false positive: 6
  - flagged: 11
- Recorded provider cost: USD 1.644085
- Proposal generation SHA-256:
  `67c327ed8746340e03e4a8e377995616e8072ce284c6fcd7fa80e48c6202a820`

The five no-call ceiling receipts are safe to continue in a new run through
the explicit no-call retry mechanism. The five accepted responses may advance
only to human ratification. Neither canary performed culling, ranking,
integration, synchronization, promotion, or main-corpus writes.
