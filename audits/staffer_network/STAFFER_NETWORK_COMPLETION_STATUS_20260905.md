# Staffer Network Completion Status

**Checkpoint:** 2026-09-05 05:57 UTC  
**Status:** Live collection continues; the full verified Politico network is loaded in the dashboard.

## Current collection

- Crawler checkpoint: **17,416 succeeded**, **1,202 remaining**, not halted.
- Service snapshot: **17,397 collected**, **17,388 verified**, **9 pending** of **18,618 expected**.
- Unresolved records: **1,230**; recorded exceptions: **1,404**; failed profiles: **0**.
- Adaptive pacing remains enabled. The crawler backs off when a batch is slow or retryable and resumes cleanly; it is not being forced through an unhealthy batch.

## Entire network graph

- Full graph endpoint: `http://127.0.0.1:8841/api/staffer-network-full?summary=1`
- **15,984 receipt-verified Politico profile nodes** are eligible for the full graph.
- **689,471 exact shared-employer edges** are available across current and historical employer layers.
- **10,298** employer/affiliation groups were observed; **2 groups larger than 250** were not pair-expanded to prevent a quadratic edge explosion. Those people remain in the node set and the skipped-group count is reported.
- Policy IDs remain node metadata and are not converted into unsupported person-to-person ties.
- The graph keeps current shared-employer and historical shared-employer layers separate and marks them review-only.

## Dashboard

Open [Melange Live Staffer Network](http://127.0.0.1:8841/staffer-live/) and use **Load entire network**. The button changes to **Use bounded view** when active. The live page has been refreshed and verified in full mode; it shows the complete profile-network payload rather than the default fast bounded view.

The bounded view remains the default for responsiveness. Full mode is intentionally heavier because it renders the complete verified profile node set and shared-employer edge set.

## Verification completed

- Live-service regression suite: **16 tests passed**.
- Crawler pacing suite: **7 tests passed**.
- Crawler self-test passed with the configured ceiling of **250 requests/minute**.
- JavaScript syntax and Python compilation checks passed.
- The sidecar API is ready and the dashboard control is present and functional.

## Next steps

1. Let the active crawler finish the remaining profiles; the sidecar will refresh the graph as new verified receipts arrive.
2. Reconcile the remaining pending/unresolved/exception records, preserving unresolved identities as separate records until evidence supports a match.
3. Review the two large employer groups separately if a future run needs their pairwise edges; do not silently infer those ties.
4. Keep payroll, LDA, Politico, committee, policy, current-employer, and historical-employer layers distinct in downstream routing and A*/D*-Lite path scoring.
