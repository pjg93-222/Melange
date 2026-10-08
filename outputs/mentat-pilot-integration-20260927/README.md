# Mentat pilot integration and GPT-6 Sol verification

Date: 2026-09-27. Implementation workspace: `C:\Users\pgoff\Mentat` on `codex/mentat-crypto`, based on commit `533b4033e8e28d6f70fe1a4a2b20e14ed7731fb8`. The supplied handoff describes an older worktree; this work uses the current implementation and the preserved successful pilot. Changes are uncommitted.

## Pilot integration completed

The published `Rust FEC Verified Industry Spending Overview 2023-2024.xlsx` is now an available, cycle-specific snapshot named **Rust FEC Verified 2023-2024**. Chart Studio, Graph, and PAC Flow resolve the same lineage. The authoritative report remains in `C:\Users\pgoff\OneDrive\Desktop\Mentat Complete Files`.

| Verified item | Result |
| --- | --- |
| Pilot run | `20260927T180216-55892`, Ripple Labs, cycle 2024 |
| Source observations | 102: 95 employee contributions and 7 corporate receipts |
| Published included receipt total | $51,152,975.30 |
| Reported donor identities | 28; not a certified distinct-person count |
| Snapshot build stamp | `246e6b07329c432670498b7002211dda0a17234772e531cb76ab94e3ce2a8280` |
| Workbook SHA-256 | `57f2961ecdfd788445a906d95ae9721753655a933e2992881845db0798cc1518` |
| Source database SHA-256 | `0ed03d40b71c14529ac59c0e0761da289c6827074fb7412ad649c2a8783dd26f` |
| Cycle payload SHA-256 | `53e7cc1e142c9c134168ea77fb1d4e5d6cc607d2979abcae5789be8419254d6a` |

The publication helper checks workbook totals, source database identity, payload cycle, payload hash, and workbook hash. It refuses conflicting existing lineage and uses separate temporary files with exclusive publication. Cycle-specific records cannot fall back to an all-cycle manifest. Report discovery, memo invalidation, contribution indexing, and Graph grouping preserve the selected cycle.

Evidence: [lineage publication](lineage-publication.json), [snapshot registry](snapshots.json), [HTTP checks](http-verification.json), [contribution query](contribution-query-pilot.json), [Graph](graph-pilot.json), [PAC Flow](flow-pilot.json).

## Dated FEC evidence

The exact employer and corporate query contracts saved by the pilot were requested again with dates 2023-01-01 through 2024-12-31. Both responses reported exact counts: 95 employee records and 7 corporate records. Full financial record identities matched the preserved database. Two shared request workers completed the two requests without changing the source database.

Raw responses, response hashes, observation timestamps, HTTP dates, and query contracts are preserved under [dated-fec](dated-fec). The reassessed coverage receipt passed all checks and reports `current`, with verified coverage through **2024-12-31** for these configured searches. The updated receipt was published back to the original pilot run; its previous receipt is retained in [coverage-receipt.before-dated-verification.json](coverage-receipt.before-dated-verification.json). [Publication](coverage-publication.json) and [console readback](coverage-console-readback.json) confirm the change.

This establishes the dated configured-search scope as observed on 2026-09-27. Later filings and unlisted aliases can add records. It does not establish all Ripple Labs giving nationwide, economic uniqueness of every receipt, or complete downstream committee filings.

## Fresh console and UI verification

A fresh read-only preview is running at [the verified Chart Studio snapshot](http://127.0.0.1:8816/?industry=Rust%20FEC%20Verified%202023-2024#chart-studio). It uses the current code and authoritative report directory. The original consoles and unrelated active Telecom collection were left running.

- Chart Studio reports Ready, 102 observations, 28 reported identities, and $51,152,975.30. Its receipt view reconciles to the published workbook.
- The contributor map renders all six location groups. Selected and located amounts both equal $51,152,975.30; unmapped amount is $0.00, with no top-N cutoff. State and congressional boundaries are visual overlays and do not allocate the money.
- Graph reads the registered cycle snapshot and carries its build stamp. Giving equals $51,152,975.30.
- Follow the money/PAC Flow renders the company, committee, onward committee, and reported activity stages. Its build stamp matches Chart Studio. Onward committee activity is explicitly presented as the committee's reported spending, not as traced Ripple Labs dollars.

The preserved payload has destination schema 0. Contributor geography is verified; recipient-state and candidate-state maps still require a payload generated with that destination evidence. Graph's separate report-bound source-freshness panel remains unknown because the pilot lacks those broader freshness receipts; the dated collection receipt does not substitute for them.

UI observation: the map chart heading is partially clipped at the tested browser viewport, in both builder and expanded views. Totals, coverage readouts, and the map render and remain readable. No frontend layout code was changed in this task.

## GPT-6 Sol concurrency and recovery verification

The user requested GPT-6 Sol, and the delegated verification ran with that model. The [Sol verification report](../mentat-sol-concurrency-20260927/README.md) contains commands, process-level tests, logs, and hashes. Tests use disposable databases and loopback HTTP fixtures, plus the separately recorded live dated FEC queries above.

The supported sharing model is multiple concurrent HTTP fetch workers serving one lane, with one R database writer owning that lane at a time. Progress and page checkpoints remain durable. Duplicate supervisors, surviving R writers, delayed stale children, reused attempt filenames, and surviving merge children are specifically covered by the ownership work and its regression tests.

The fixes add a supervisor lease, a per-lane writer lease, a merge-child lease, supervisor identity checks in children, and unique resume artifact filenames. Resume refuses while a surviving writer or merger still owns its database. Database and budget connections close before the lane lease is released. A batched merge rechecks the source fingerprint before replacing it; superseded children cannot commit a newer supervisor's work.

Sol's final run passed **136 Python tests and three R test scripts**, including 69 concurrency, checkpoint, supervisor, lane, and merge tests. Across Sol and the root app checks, **213 distinct Python tests passed** in 17 suites (the 27 contribution tests were run by both agents and counted once). [final-verification.json](final-verification.json) records the suite counts and unchanged pilot hashes. These are local-process results, not a certification for remote/network filesystems.

Remaining recovery bounds: a crash after a successful source merge but before the final supervisor receipt requires operator review because the original source fingerprint has changed. The system refuses automatic resume in that condition. Unrelated external writers that ignore the merge sidecar lock are outside the cooperating-worker guarantee and could race in the final Windows file-replacement interval. Existing live collections retain their already-loaded code; the fixes apply to runs launched from this updated workspace.

## App regression evidence

The final local app runs passed 104 tests: report-directory console 10, contribution data 27, Graph 25, workbook guard 4, contribution HTTP 24, and source guard 14. Each file's stdout/stderr is preserved in the corresponding `test_*.log`. Sol also ran the cycle-lineage, snapshot-registry, source-memo, and dated-coverage tests; see its report for their final counts.

The first Graph run identified a legacy grouping regression, which was corrected before the final run. An unchanged source-guard test initially rejected a changed fixture through its financial-fact check rather than the expected fingerprint error; both isolated and suite reruns passed without changing that guard or test. The initial logs are retained. This is not evidence of an accepted corrupted source.

The prior handoff's Cargo/native parity results were not rerun because this work did not modify Rust. The final hashes and whitespace check are recorded alongside this report.
