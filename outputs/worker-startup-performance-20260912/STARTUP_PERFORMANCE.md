# Mentat startup performance — September 12, 2026

The desktop launcher and worker handoff now avoid measured idle work. The original desktop entry point and appearance remain intact. No collections, FEC requests, production database changes or report generation were used to benchmark these changes.

| Local measurement | Before | After | Scope |
|---|---:|---:|---|
| Cold desktop launch, median of 3 | 4.413 s | 2.103 s | Same synthetic localhost server, including its openpyxl import; about 52% faster |
| Existing server reuse, median of 3 | 1.308 s | 1.427 s | Similar; no warm-launch improvement claimed |
| Probe of an unused port | 2.389 s HTTP | 0.018 s bind | Launcher now checks whether a port is free before attempting HTTP |
| Disposable Python preflight, median of 5 | 0.277 s full import | 0.033 s package discovery | Real server still imports openpyxl; Python version and package availability remain checked |
| Managed synthetic process completion, median of 3 | 2.007 s | 1.060 s | Two-second status cadence now wakes immediately when the child exits |
| Ordinal delay on shared-pool lane 32 | 7.750 s per invocation | 0 s | Existing ledger setup/verification, request budgets and lane isolation retained |

These are component and fixture timings, not an estimate of complete collection time. Source snapshot copying, genuine R startup, report validation and remote FEC response times still require their normal work.

`Start-MentatApp.ps1` now probes free ports directly, checks TCP readiness before HTTP, and avoids importing openpyxl twice. It still validates application identity, project, data root, authoritative report directory, loaded server hash and writable mode before reusing a server. Its named startup mutex, stable port receipt and hidden server process remain in place. `desktop/Launcher.cs` needed no change: its PowerShell handoff continues to perform these checks.

`Start-MentatResilientIndustryReports.ps1` uses `Process.WaitForExit(2000)` instead of sleeping between status polls. Existing exit-code handling, including the PowerShell 5.1 cached process-handle guard and null-exit sentinel, remains intact.

`collect_api_lane.R` skips the ordinal stagger only for the managed loopback request-pool mode, whose Python owner initializes the budget ledger before dispatch. Direct worker mode retains its existing stagger. SQLite busy timeouts, WAL checks, durability, per-key budget reservations and private database ownership remain unchanged. Worker receipts now record `startup_jitter_seconds` for auditability.

Validation passed: 17 focused Python tests across cold-start/reuse, TCP probing, actual desktop conflicts and concurrent launches, rejection of old/read-only servers, managed exit handling, request-pool budgets/authentication, and company borrowing/resume/stop semantics. The R fanout test passed its durable budget, resume-marker and startup-delay cases. A mock collector ran complete lane fixtures without making HTTP requests; the ledger's existing counter remained unchanged. The R transport test requires an explicit usable `R_LIBS_USER` in this restricted test environment and passed with the bundled audit library. Actual launcher tests terminated only identity-verified servers in their temporary data roots.

Raw measurements and reproducible local probes: [desktop-before-after.json](desktop-before-after.json), [before.json](before.json), [after.json](after.json), [before-lane.json](before-lane.json), [after-lane.json](after-lane.json), [benchmark_desktop.py](benchmark_desktop.py), [benchmark_startup.py](benchmark_startup.py), [benchmark_lane.R](benchmark_lane.R). The desktop comparison reconstructs the immediately preceding launcher algorithm by reversing only this task's exact edits inside a temporary fixture.
