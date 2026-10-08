# Eight-window scrape status

## Recovery update — 18:38 Eastern

The initial eight-window run aborted when replacement-worker directory navigation timed out after repeated profile timeouts. The captured error was a 30-second page-load timeout, not evidence of an authentication block. Its stopped checkpoint independently passed integrity verification at 5,713 accounted, leaving 12,905 pending.

Patched the coordinator to preserve eight fixed UUID shards while starting at one simultaneous profile load, adding one slot after three clean waves and halving concurrency on slow responses or failures. Transient directory-recovery timeouts now defer queued work instead of aborting the entire run; authentication and throttle exceptions still halt. All 71 tests passed, including capped concurrency with eight-shard conservation.

Restarted launcher PID 54844 at 18:37:52 Eastern; log `politico_profile_crawl_20260903_raw/python_adaptive_windows_20260904T183752.log`. All eight authenticated startup canaries and distinct-window shard initialization passed. No claim of improved saved throughput yet; live validation remains pending. The existing monitor now follows this process and adaptive-concurrency implementation.

Checkpoint: September 4, 2026, 18:29 Eastern. This is an interim report, not a completion certificate.

- Eight authenticated top-level Chrome windows launched under one Python/Playwright coordinator (launcher PID 67828).
- Deterministic UUID shards are disjoint: 1,601 / 1,609 / 1,663 / 1,583 / 1,601 / 1,615 / 1,604 / 1,668 pending profiles at launch. Assignment manifest: `politico_profile_crawl_20260903_raw/window_shard_manifest.json`.
- One checkpoint writer and aggregate navigation pacer; unchanged identity, full-history, API-response and stable-snapshot verification gates.
- Startup individual content canaries, concurrent two-window canary, and eight distinct window IDs passed. Unit suite: 70 tests passed before launch.
- Latest verified checkpoint: 5,706 of 18,618 UUIDs accounted (30.6478%); 5,510 content-bearing profiles and 196 authoritative unavailable-404 exceptions. Five same-UUID name-change exceptions remain explicit. Remaining: 12,912. Hard failures: zero. Integrity PASS; completion INCOMPLETE.
- The first two waves added 32 accounted profiles. Actual measured throughput was only 17.1 accounted/minute, below the earlier single-page run around 41/minute. Each wave had one retryable snapshot timeout and multiple slow responses. Eight windows are operational, but a speed improvement has NOT been demonstrated.
- Automatic backoff is at 60 aggregate navigation admissions/minute; configured ceiling remains 120 across all windows, not per window. Pending and interrupted work stays queued.

## Next steps

Keep checking actual saved throughput, API visibility and timeout behavior through the existing monitor. Diagnose persistent concurrency regression before claiming or increasing throughput. Preserve all checkpoints and verification gates. At terminal crawl completion, independently verify the full denominator, then build and verify the strict reconciliation bridges and separate-layer network outputs, coordinate dashboard repinning, and issue the final coverage/next-steps report. None of those final completion gates has passed yet.

Live log: `politico_profile_crawl_20260903_raw/python_eight_windows_20260904T182645.log`. Verification receipt: `politico_profile_crawl_20260903_raw/crawl_verification.json` (verified at 22:29:29 UTC). Existing recurring monitor updated with this measured regression; usage remaining was 7% at this checkpoint.
