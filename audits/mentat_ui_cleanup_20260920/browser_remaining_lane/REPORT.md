# Remaining browser harnesses - 2026-09-20

Functional assertions: **16/16 passed**. Process exit 0: **16/16**; consult the table for cleanup status.

All harnesses used isolated fixture roots or browser route fixtures. No collectors, production data, or production code were changed. Initial and retry logs remain separate.

| Harness | Final status | Exit | Steps / node tests |
| --- | --- | --- | --- |
| test_app_lazy_startup_browser.cjs | passed | 0 | 3 tests |
| test_contribution_map_browser.cjs | passed | 0 | 1 test |
| test_cross_reference_scope_browser.cjs | passed | 0 | See log |
| test_evidence_panes_browser.cjs | passed | 0 | 33 steps |
| test_original_studio_contributions_browser.cjs | passed | 0 | 1 test |
| test_studio_board_browser.cjs | passed | 0 | 19 steps |
| test_studio_briefing_tray_browser.cjs | passed | 0 | 2 tests |
| test_studio_canvas_only_browser.cjs | passed | 0 | 1 test |
| test_studio_click_to_add_browser.cjs | passed | 0 | 1 test |
| test_studio_copy_print_browser.cjs | passed | 0 | 4 tests |
| test_studio_data_source_browser.cjs | passed | 0 | 1 test |
| test_studio_industry_browser.cjs | passed | 0 | 10 steps |
| test_studio_ride1_browser.cjs | passed | 0 | 2 tests |
| test_studio_strip_removed_browser.cjs | passed | 0 | 6 steps |
| test_studio_worksheet_guard_browser.cjs | passed | 0 | 3 tests |
| test_ui_cleanup_browser.cjs | passed | 0 | 12 steps |

Three initial runs were cancelled or hit a watchdog during an observed multi-hour timing interruption. Each passed in a fresh process. The strip-retirement test initially stopped at a stale v4 contract-version assertion; the current documented contract is v5 with Graph drawer keys, while studioPane remains retired. Only that version assertion and its comment were corrected; the rerun passed all six UI checks.

The industry harness logged a 10-second browser.close timeout after all 10 steps passed, then exited0. The strip-retirement rerun passed all 6 steps and exited 0 in 64.09 seconds; no forced process cleanup was needed.

Detailed initial and final statuses: [final_ledger.json](final_ledger.json).
