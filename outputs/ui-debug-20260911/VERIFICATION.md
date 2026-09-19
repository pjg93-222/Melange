# Mentat app debug and UI cleanup

Completed September 10, 2026 (America/New_York).

Updated local app: http://127.0.0.1:8804/#graph

## UI

Higgsfield generated a MENTAT UI concept using gpt_image_2 (job bba9ec68-9033-4ed4-bcc9-b1f0891b7827). The implementation retains Mentat's plum, ivory and teal theme, and uses grouped navigation, simpler controls and expandable explanations.

- Desktop sidebar; horizontal navigation at narrower widths, with working arrow/Home/End keys and a skip link.
- Compact Graph filters and row controls; report-folder selection in a disclosure.
- Comparison occupies its own focused view, with Back to graph.
- Collection progress appears before detailed coverage tables. Coverage and reconciliation warnings remain visible.
- Evidence estimation explanations expand on demand. Mobile charts scroll within their cards so financial labels remain readable.

## Bugs fixed

- Windows LocalAppData aliases broke saved worker-path containment and prevented the collection monitor from loading. Both paths now resolve before containment checks. Outside-run worker files remain rejected before reading.
- A stopped run could retain a collecting badge and present stale worker counts as active. Terminal state now takes precedence; saved worker counts and industry stages are labeled as the last checkpoint.
- Report refreshes during Graph/comparison reads could mix versions. Results now reject changed sources; concurrent reads of the same workbook share one in-progress load.
- Accounting percentages were mis-scaled, and malformed accounting numbers were accepted.
- Stopped/failed checkpoint timers could be labeled Finished or keep advancing.
- Chart suggestions could lose Row count; swapping funding chart axes retained unrelated blank series.
- Comparison charts exposed invalid worksheet/rescan controls. Old failed requests could overwrite newer chart state.
- Repeated comparison openings duplicated requests; folder changes retained stale industry choices; missing current-period giving produced a false negative change.

## Verification

| Check | Result |
|---|---|
| Python: Graph 15, comparisons 5, collection 28, cross-reference 16, report directory 8 | 72 passed |
| Focused offline JavaScript tests | 28 passed |
| Isolated chart/comparison browser regression | Passed; no page errors |
| Full fixture browser suite | Passed, exit 0; fixture cleaned up |
| Responsive widths | 390, 768, 1099, 1100 and 1440 px checked |
| Browser workflows | All five views; disclosures; stopped-run state; charts; exports; keyboard navigation; mobile readability |
| Browser requests | Local requests only; no page errors |
| Syntax and diff checks | Passed |

Real app verification used the authoritative Mentat Complete Files folder. All eight report datasets were available, with Banking and Community Banks separate. Banking and Credit Union graphs loaded; the Chief filter returned promptly. The previously failing Banking collection loaded all eight saved worker lanes. Final app showed Local connection without the path exception, and a stopped badge with last-checkpoint worker counts.

Final running server SHA-256: d186be5db75e52607389fef4e78371ae06f007503c89036743235fbc7bad79d6.

A large workbook's cold read can still take tens of seconds: the Credit Union report took 24.83 seconds under profiling. Cached local Graph computation was effectively immediate; a final Banking API request returned in 2.29 seconds. These are individual observations, not a performance guarantee.

No live FEC collection was started by these tests, and report documents were not modified. Existing work and collection processes were preserved. The earlier server started during this session was retained after a cleanup check found child processes; the final launcher receipt points to port 8804.

## Review images

The screenshots use explicitly fictional fixtures, not the user's real financial totals.

- [Graph](clean-graph.png)
- [Loading](clean-loading.png)
- [Collection](clean-collection.png)
- [Stopped collection](clean-stopped.png)
- [Cross-reference](clean-cross-reference.png)
- [PAC evidence](clean-evidence.png)
- [Mobile](clean-mobile.png)
- [Chart builder](clean-builder.png)
- [Sources](clean-sources.png)

[Higgsfield design concept](https://d8j0ntlcm91z4.cloudfront.net/user_3J1aVESwhbXLraSW8PtRFWWgpV2/hf_20260911_025248_bba9ec68-9033-4ed4-bcc9-b1f0891b7827.png)
