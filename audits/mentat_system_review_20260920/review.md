**Mentat interface, retrieval and compilation review — September 20, 2026**

Mentat passed the exercised accounting, source-preservation, query, workbook and export checks. One functional UI defect was reproduced and fixed: Cross-reference could display the previous industry's evidence after the selected industry changed during a request. Three failing test files also contained two obsolete assumptions; those were corrected without changing accounting behavior. These results establish behavior on the tested fixtures, not complete real-world FEC coverage or independently certified totals.

The work preserved the pre-existing uncommitted changes. No production collection was started, report regenerated, accepted evidence changed, or live server restarted. Tests used temporary databases, report folders and synthetic responses. The live server was inspected only through health and static-asset GET requests.

The Higgsfield connection was inspected as requested. It lists one undeployed `melange-influence` app, not this local Mentat console. Its website workflow explicitly leaves existing local-codebase fixes in the repository; no hosted app or generated visual asset was needed for these defects. No data was uploaded or remote site changed.

**System and workflow examined**

The applicable `mentat/AGENTS.md` pins final report viewing and publication to `C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files`. `mentat/README.md`, `app/README.md`, `METHODOLOGY.md` and `app/CONTRIBUTION_STUDIO.md` describe the following workflow; entry points and representative paths were checked in implementation.

| Stage | Implementation and meaning | Evidence boundary |
| --- | --- | --- |
| Input | `app/Start-MentatApp.ps1` launches `app/server.py`; `app/app.js` accepts a sector, canonical companies, aliases and cycles, reviews the roster, and launches an isolated runtime. | Reviewing a roster is distinct from starting collection. Blank names and cross-company alias collisions block readiness. |
| Retrieval | `mentat.R` loads `R/ingest.R`, `collect.R` and `fec_api.R`. Literal employer/contributor queries, FEC pages, checkpoints, archived evidence and company matching populate SQLite. | This is structured record retrieval, not semantic document search. A paraphrase is not an approved employer alias. Incomplete or changed query contracts cannot certify complete coverage. |
| Content compilation | `tools/run_cross_reference.py` and `cross_reference_engine.py` reconcile identities, receipt roles, explicit memo links and filing evidence. Source guards and the workbook builder carry the accepted records into report outputs. | Source verification, company attribution and complete/unique-dollar coverage are separate claims. Ambiguous evidence cannot silently become zero or certified giving. |
| Display | Graph reads report data; Chart Studio uses a provenance-bound analytical index; PAC evidence shows saved observations; Cross-reference shows scope and the contradiction/refund/large-receipt digest. | The published workbook remains the accounting of record. Cross-reference deliberately publishes no money totals. Direct giving, PAC activity and conditional estimates remain separate. |
| Export/revision | Workbook output, filtered CSV, PNG/SVG, saved views and URL scope preserve their declared population and source context. | CSV population and image-visible page are different export contracts. Source changes during a data export must stop it. |

No model prompt, LLM context window, or generated-answer stage was found in the reviewed entry points and collection/compilation path. A revised prompt is therefore not applicable. Relevant hostile-content checks concern source text escaping, safe source URLs and export data, rather than a prompt allowing retrieved text to become instructions.

Software build verification is separate: this pass executed Python, JavaScript, R and browser tests and template-parity checks. It did not rebuild the existing Rust scanner or package/deploy a new application.

**Findings, ranked by impact**

1. **P2 — Cross-reference could render evidence for the wrong selected industry. Fixed.**

   Reproduction: load Cross-reference with industry Alpha and delay its response; change the URL scope to Beta while Alpha is pending; complete Alpha's response. Before the fix, the browser displayed `Run fixture-Alpha` and Alpha's scope, and the request log contained only `/api/cross-reference?industry=Alpha`. Beta had to wait for a later poll. A previously rendered scope also remained visible while replacement data loaded or failed.

   Confirmed cause: the global `fetching` flag made the scope-change refresh return early, while the pending response had no request-identity or current-industry check. This was an interface state defect, not evidence of an incorrect server query or wrong stored dollars.

   Correction: `mentat/app/cross-reference.js:127` now replaces an obsolete request, checks request identity and current scope after reading the body, clears the previous scope immediately, shows loading/retry state, and cancels pending work when leaving the tab. A failed refresh of the *same* scope may keep its result with an explicit older-snapshot warning.

   Verification: the new `mentat/tests/test_cross_reference_scope_browser.cjs` first failed against the original code and now passes. It deliberately ignores abort signals to prove that stale replies cannot paint even when cancellation does not stop them. It covers old success arriving both before and after the new success, stale failure after a newer success, empty scope, current failure, retry and tab reactivation. See [before](cross-reference-scope-before.log) and [final](cross-reference-scope-final.log). The exact pre-edit module is preserved in [cross-reference.before.js](cross-reference.before.js).

2. **P2 — Map regression harness sampled queued work and imposed an obsolete rendering expectation. Corrected.**

   Reproduction: `node mentat/tests/test_evidence_map_render.cjs`. The original test issued 30 zoom operations synchronously and read the duration list before the animation-frame callbacks ran. Its output had no median and a JSON `null` maximum. It then failed because 73 visible circles did not exceed 2,500, although viewport culling and clustering intentionally reduce the SVG population.

   Confirmed cause: the harness still assumed synchronous transforms and a full unculled DOM population. This failed test was not proof of slow zoom or missing source data.

   Correction: await each scheduled frame, test 3,000 source ZIPs independently from the visible circle count, and require 30 real, finite transform samples plus visible-point retention and culling. The existing polygon-identity, layer, legend and performance assertions remain. This does not claim a benchmark with 3,000 simultaneous SVG circles.

   Verification: the corrected run passed with 3,000 source ZIPs, 73 visible circles and 30 measured transforms. Recorded median/max JS transform times were about 0.20/0.30 ms; those are fixture transform-update timings, not end-to-end frame-paint or production latency guarantees. See [JavaScript log](javascript-tests-after.log).

3. **P3 — Two browser suites stopped at obsolete copy assertions. Corrected.**

   Reproduction: the console and navigation-scope browser suites required `it publishes no totals`; the current UI correctly says `this view publishes no totals`. Both stopped before later workflow assertions despite the accounting-of-record rule being intact.

   Correction: update the two phrase checks to the actual wording. No production copy or accounting rule was changed to satisfy them.

   Verification: the full console workflow and all 13 navigation-scope steps passed afterward. See [console before](console-browser.log), [console after](console-browser-after.log), [navigation before](test_navigation_scope_browser.log) and [navigation after](navigation-scope-after.log).

A separate usability observation remains advisory: the [captured Cross-reference screen](cross-reference.png) retains the global `Run restored.` message after leaving Collection. The evidence-specific status is correct, but identifying that message as collection context would make its meaning clearer. This was observed visually; no incorrect underlying run state was established, and it was not counted as another functional failure.

**Representative scenario results**

The scenarios adapt the brief to structured FEC records. They were exercised across layer tests and browser fixtures, not as a new production collection from the public API through final publication.

| Scenario and concrete input | Expected result | Observed evidence |
| --- | --- | --- |
| Normal collection/report workflow | Reviewed roster and declared cycles carry through query contracts, source records, classification and report output. | Python console/runtime tests and all nine selected R suites passed. The console browser showed the fixture's $1,585 total and a $300 Chief-filtered scope. Workbook tests verified the six-sheet contract and 6,035 Stats formulas. |
| Incomplete/ambiguous input | Blank canonical names and shared aliases cannot launch; unknown attribution remains explicit. | `test_collection_console.py` readiness tests and `test_names.R` passed. Cross-reference engine/runner tests retained unexplained heuristic rejections provisionally while excluding evidence-backed non-giving events. |
| No relevant source | Empty query results differ from incomplete collection; a missing scoped run does not fall back to a different industry. | `test_query_coverage.py` passed: adding missing literal alias `Alpha.Pay` produced six uncovered units; normalized `Alpha Pay` did not satisfy the literal contract. Query pagination/empty-population tests, navigation step 13 and the new scope browser test passed. |
| Duplicate sources | Preserve observations but count the same source ID once; require a compatible retained counterpart for memo removal. | The runner counted a shared $100 source once while preserving two observations. A $1.25 gift and explicitly linked $1.25 memo produced $1.25, a -$1.25 change and identical replay ledgers. Equal independent gifts remained separate. |
| Conflicting sources | Do not silently choose one conflicting financial value or certify ambiguous accounting. | The runner rejected the same source ID at $100 versus $101 without publishing a report. Conflicting line/role evidence retained $100 as unresolved with zero supported-unique amount. |
| Dependency/processing failure | Preserve failure receipts, reject stale inputs, provide an honest recoverable UI state. | Preparation/source-guard/API retry tests passed. Delayed and rejected Cross-reference fetches reproduced the UI defect before the fix and passed after it. No real FEC outage was induced. |
| Revision/repeated run | Edited scope survives navigation/reload; old saved state cannot undo an edit; unchanged compilation repeats deterministically. | Navigation steps 8/12, Studio state tests and the runner's repeated-ledger test passed. The new browser test rejects obsolete responses after an industry revision. |
| Display/export agreement and provenance | Preserve amount units, filters, page contracts and source identity; reject changes during export. | Query/filter tests, Graph–Studio cent reconciliation, complete CSV state tests and PNG/SVG pixel/viewport checks passed. Source text escaped in PAC evidence, source URLs were constrained, and source/query fingerprints were checked. |

**Execution record and limits**

| Check run in this review | Result | Log |
| --- | --- | --- |
| `python -m unittest discover -s mentat/tests -p 'test_*.py'` | 1,078 executed tests, OK; these are the discovery count, not a claim of 1,078 independent scenarios. | [python-tests.log](python-tests.log) |
| Node app unit tests plus non-`browser` CJS tests, including the map rendering test | Initially 371/372; after the harness correction, 372/372. | [initial](javascript-tests.log), [final](javascript-tests-after.log) |
| R names, attribution recheck, FEC API, API reconciliation, request windows, collection contract, receipt roles, reconciliation and report suites | All 9 exited 0; the API reconciliation suite reports 16/16. | `test_*.log` in this directory, including [report](test_report.log) and [API reconciliation](test_fec_api_reconcile.log) |
| Console, navigation scope, Studio reconciliation, contribution export, Studio state, worksheet guards, PAC evidence panes, Graph explorer, downstream measurement and the new scope-race browser suite | All 10 suites passed their functional assertions. PAC evidence: 33 steps; navigation: 13 steps; explorer: 10,000 searchable relationships. | Corresponding browser logs in this directory |
| Template parity | 9/9 passed. | [template-parity.log](template-parity.log) |
| Live localhost health and static JavaScript | Port 8806 reachable; configured report folder correct; backend code matches disk; corrected Cross-reference bytes served exactly. | [live-health.json](live-health.json) |

Reproduce the primary fix with `node mentat/tests/test_cross_reference_scope_browser.cjs` from the repository root. Reproduce the complete console path with `node mentat/tests/test_console_browser.cjs`. Browser tests use the installed Chrome and the existing Playwright runtime; the existing `MENTAT_NODE_MODULES`, `MENTAT_PYTHON` and browser-channel overrides apply where supported.

The full Python run emitted an unclosed-socket ResourceWarning after `OK`. The navigation browser's final cleanup reported a `browser.close()` timeout after all assertions passed and exited 0. Several R suites emitted Windows locale warnings. These are recorded harness/environment limitations, not silently presented as warning-free runs.

The in-app browser failed to attach twice, so the actual user's open UI session was not interacted with. Browser interaction and the inspected screenshot used isolated Chrome fixtures. Production report contents were not independently reconciled against public filings, and no live key/budget/network collection or paid dependency was exercised. Full filing/route completeness, current upstream FEC correctness and historical report uniqueness therefore remain unverified by this pass. Successful local tests do not fill those data gaps.

The only production-code edit in this pass is the Cross-reference request/state correction. Backend collection and accounting were not altered. Reloading Mentat loads the corrected UI; the live static-asset match was verified without restarting the server.
