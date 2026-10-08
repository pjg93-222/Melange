# Opus adjudication canary supersession

Status: `SUPERSEDED_DO_NOT_MERGE`

The proposal run `opus5-max-canary25-20260728a` is permanently excluded
from ratification, culling, integration, and promotion.

## Superseded binding

- Packet generation:
  `4a4aac994b410f7e0392e71eeaf4046bf9e0ff57f61985cd0f8077865b05d44a`
- Packet SHA-256:
  `b76a71f45d40b4b1a41b01bfe5a398c396220735698dbd0224be02616a2ac767`
- Complete provider receipts: 6
- Provider-call starts: 7
- Call start without a terminal receipt: 1
- Accounted cost recorded by the six terminal receipts: USD 5.634520

The seventh call start is indeterminate and must never be replayed as if no
provider call occurred. The six terminal receipts remain immutable audit
evidence but are not admissible adjudication proposals.

## Reason

That run was bound to packets built before the accepted GovInfo version
objects were restored locally. The restored object set changed the evidence
available for all-version review and therefore changed the packet generation
and canary selection. Reusing the old responses would violate the
evidence-bound proposal contract.

## Replacement binding

- Packet generation:
  `97a4cea6f3306576fb1bedfe91571b0371560058368bfb943229ad26e72c3036`
- Packet SHA-256:
  `736119a69c0c643eaadddafad73978b7f0540d5468cd8773a8353accbb145b56`
- Restored evidence run:
  `restore-full-18440-20260728a`
- Replacement canary:
  `opus5-max-restored-canary10r2-20260728c`

Only proposals whose receipts bind to the replacement packet SHA-256 may
advance to human ratification. Automated proposals cannot self-ratify, and
integration remains separately gated by the user's explicit Greenlight.

The intervening run `opus5-max-restored-canary25-20260728b` failed its initial
per-call budget validation and is also excluded from merge or automatic
replay. Its four call-start keys were omitted from the successful replacement
run. See `CANARY_EXECUTION_2026-07-28.md` for the complete execution receipt.
