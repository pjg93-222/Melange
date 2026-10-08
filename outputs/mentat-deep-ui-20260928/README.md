# Additional recovery review and UI walkthrough — 2026-09-28

## Completed fixes

- The supervisor closes its shared HTTP request pool and control watcher after an exception, before releasing supervisor ownership. Interrupted active-run telemetry clears correctly.
- A worker that exits nonzero cannot certify successful tasks. Resume also checks recorded process exits and the R postflight result before trusting a saved success receipt.
- A rejected restart preserves the previous run's terminal telemetry. Cleanup only writes interruption state for an invocation that actually began publishing worker state.
- The read-only Collection monitor disables Pause and worker-count controls and explains where collection can be managed. Writable active collections retain these controls.

The backend fixes and process-level evidence are described in [recovery/README.md](recovery/README.md). The UI-control defect was reproduced against the actual shipped renderer before the change (`collection-readonly-before.log`) and passes afterward (`collection-readonly.log`).

## Completed verification

| Check | Result | Evidence |
|---|---:|---|
| GPT-6 Sol recovery regression suites | 89 Python tests + 9 subcases passed | `recovery/python-tests.log` |
| Collection console, upload isolation, telemetry and HTTP boundaries | 39 Python tests passed | `collection-console.log` |
| Application chart, scope, map, evidence and export logic | 660 JavaScript tests passed | `app-unit-tests.log` |
| Additional UI analysis rules | 16 JavaScript tests passed | `ui-analysis-unit.log` |
| Read-only collection controls | 3 JavaScript tests passed | `collection-readonly.log` |
| R fanout, date-window checkpoints, lane locking | 3 scripts passed | `recovery/r-tests.log` |

The scoped diff check passed. R emitted Windows locale startup warnings but all three scripts completed with PASS. Tests used disposable fixtures; active collectors and production databases were not modified.

## Live UI walkthrough — completed

The walkthrough was completed in Codex's built-in browser against the dedicated read-only preview on port 8816. Only that preview process was restarted. Existing live collectors were left running. This is a bounded workflow review across all seven workspaces, not an assertion that every possible chart, field combination, source or live collection action was exercised.

| Workspace | Interactions and observed result |
|---|---|
| Loading | Empty Review names submission rejected the required Sector field; saved coverage explanations and scope-preserving navigation rendered. |
| Collection | History displayed completed recovered runs. Workers, Activity log, Run events, Coverage and Report freshness expanded. The recovered Banking run showed 30/30 tasks, zero checkpoint workers and zero failures; absent historical evidence stayed unknown. In progress and Archived folders displayed their respective empty states. A different historical run could be selected. Worker controls were disabled in this preview. |
| Graph | Personal giving reconciled to $152,975.30; the Chief filter to $115,700. Corporate giving showed $51,000,000 with no direct candidate contributions. Reset cleared company, tier and giving restrictions. Candidates tab and scoped Open in Chart Studio handoffs worked. |
| Chart Studio | Bar and Text views, source-record opening/closing, Undo, Duplicate, company overview, contributor map, zoom/reset and in-tab briefing capture worked. Records paged 1–100, 101–102, then back to 1–100 of 102. FEC links used official docquery URLs, including report links for conduit filings. CSV, SVG and PNG actions reached visible download-request confirmations. |
| Insights | Core and All analysis selection loaded available results, including timing, recipient identities and legislative context. The single-cycle pilot withheld historical forecasts with the explicit four-complete-cycles requirement. The separate Forecast giving form loaded its labeled historical example, calculated both horizons and explained missing remainder inputs. Its whole-industry scope was disclosed. |
| Cross-reference | The pilot has no saved cross-reference run. The page stated this and remained read-only; viewing did not start collection or fabricate evidence. |
| PAC evidence | Loaded the saved Senate Leadership Fund snapshot, selected its PAC, searched a deliberate no-match string and cleared it. Summary, Flow, Rows and Map opened. Flow disclosed committees reached but not collected; map disclosed unlocated amounts and a source gap. Cycle selection, zoom and reset worked. |

Desktop (1440×900), phone (390×844) and the default panel were inspected. Graph, Chart Studio, Insights and PAC evidence remained within the page width at phone size; wide analytical tables use their own scrolling areas. The map heading remained visible. Workspace Home, ArrowRight and End keys selected the expected tabs. Escape from inside the data-source picker closed it and restored focus to its trigger. The temporary viewport override was reset.

The final browser console contained no captured warnings or errors. Final Chart Studio totals were **$51,152,975.30, 102 source observations and 28 reported donor identities**, with only the 2023–2024 cycle filter. Its reconciliation strip was correctly hidden because Graph agreed.

### Additional fixes found during the walkthrough

- Graph-to-Studio handoffs now replace all carried company, cycle and funding filters, including clearing old restrictions when Graph says All. Independent analytical filters remain intact.
- Verified maps now refresh reconciliation after rendering and clear stale reconciliation while a new view loads. Previously a map could retain an old Chief/all-cycles explanation.
- Reconciliation now explains the difference between Graph's published giving categories and Studio's evidence-based funding classifications. In this pilot, $51 million of published corporate receipts has an unverified organization classification; the UI must not silently reclassify it as verified corporate funding.
- Verified CSV, SVG and PNG exports now display progress and a download-request confirmation in the visible status line. Export before data is ready produces guidance. Previously these messages were hidden behind the generic Ready indicator.

`walkthrough-js-tests.log` records **665 passing application JavaScript tests**, including five new behavior regressions in `mentat/app/tests/studio-handoff-walkthrough.test.js`. The scoped diff check passed. Earlier Python, R and collection-control results above remain the evidence for recovery and concurrency behavior; they were not rerun for these JavaScript-only fixes.

`walkthrough-source-hashes.json` confirms that all four pilot artifacts—the authoritative workbook, source database, report payload and lineage manifest—retain their previous SHA-256 hashes. New forecast-related files already present in the workspace were preserved.

### Boundaries

Live collection start/stop/worker changes, imports, new FEC snapshots and production writes were not part of this read-only UI pass. Their recovery/concurrency behavior was exercised with the earlier Sol process fixtures. Cross-reference's populated-results case was unavailable for the pilot. Browser export generation and download requests were confirmed, but the built-in browser did not expose a reliable download event or saved-file path; final filesystem delivery is not claimed. This review does not certify nationwide completeness or exhaustively audit accessibility.

The scoped Impeccable scan (`ui-detector.json`) produced styling advisories: three border accents, one width transition, and palette/type/radius values outside the saved design metadata. These are not counted as demonstrated user-facing defects or a WCAG certification. The requested review preserves the existing design rather than restyling it based on detector output alone.
