# Forecast audit completion — 2026-09-30

## Result

The owner-approved v2 refit and P&C pilot were completed and published in the RunPod.
The original 2026-09-29 report remains historical evidence. This addendum records the
current build, explicit G6 waivers, publication repairs, and validation.

Final run: `pod-publish-final-20260930`.
Model: `refit-20260930-377f7324-c3f221343515`.
Bundle SHA256: `7bc7bcf175f7a3c291cc67300f981d610ef7b52059eefb7cb21e2dc4e020e0bb`.
Published: `2026-09-30T21:53:03Z`.
Producer SHA256: `9adbd797afe4aa8c1b80b64bb3b2d1ca188dec21d889e10e7479fd3eb6e01f00`.
The Git landing transaction has a separate receipt to avoid embedding a commit's own identity.
Windows activation remains dormant under the owner's instruction to run all workloads in the pod.

## Scope and source

Execution host: `d3e3e3ac8c64`, isolated root `/workspace/forecast-audit-5603f2`.
Build baseline: `e93a324326e04720821741df2071a318b82366a2`.
Live landing base: `7287dbb50f4c910d5dce620ada903f0bbe20c9a1`.
Phase3: `56519c6285964dd5d07eee893efa4c193672cd1b`.
Sector Growth Study: `04e2391e56ce7422255a062b297773e7aaa8fd7c`.
Model inputs: 121 pinned files, all verified by SHA256 in the pod.
The aggregate anchor snapshot and receipt match the measured current hashes of all four
industry workbooks. No donor-index SQLite databases were transferred. Approved SGS loaded
workbooks retain their exact bytes and stay in the private repository/pod; no public push occurred.

Model fitting, data parsing, installs, tests, browser rendering, and Git assembly for this
completion run took place in the pod. Earlier SGS run receipts were reviewed as prior evidence. Final workstation operations are bounded metadata reads and byte transport. Separate
co-resident pod work under `/dev/shm/melange` was left untouched.

## Behavior and owner decisions

The P&C pilot uses F09 all-insurance with the disclosed scope mismatch; the 2024 revenue
point is the current-year estimate from the same 2024-11 IBISWorld vintage. A newer complete
history supersedes the estimate. Share-anchor and nonpooled slope selection require at least
a 5% accuracy win in both leave-one-election-out and chronological validation.

The first completed refit, `pod-final-20260930`, correctly held publication. House-share MAE
increased: banks 1.053 to 1.550; credit unions 1.522 to 1.836; auto 1.338 to 1.766.
The owner explicitly answered: **"Waive these three cells and publish"**. The registry records
exactly those three visible warnings plus the existing quiet banks-lobbying waiver. All other
cells retain the no-degradation gate. The original HOLD and subsequent waived publication
receipts are retained. Waivers do not establish improved model accuracy.

Publication now selects immutable content-addressed bundles through an authoritative,
validated pointer. Both R and Python check the pointer's contained path, hash and identity.
A failed switch retains the previous active model; rollback to v1 is tested. Same-day version
identities include run/time/code provenance. The final review additionally found that in-process
parity tests leaked their temporary runtime into the publisher. Caller-environment restoration
and an actual-helper regression were added, and the publication was repeated against the
persistent runtime with the old immutable pair recovered into the rollback archive.

The simple Insights forecast card is off by default and enabled through the existing setting.
Chart Studio calls the transform "Same-phase baseline". The mobile Giving Forecast outcome
heading now uses the available width. Existing peer edits in Chart Studio, generated index,
evidence template and server are preserved outside the forecast commit.

## Verification

- Full R suite against the final frozen producer: 2,507 passed, 1 skip,
  zero failures/errors/warnings. The skip requires an unavailable real-report directory.
- Python: 212 passed, 2 optional donor-rebuild skips, and 805 passed subtests.
- Ingest: 1,132 passed, 7 optional/licensed-input skips, zero failures/warnings.
- SGS synthetic suite: 1,945 expectations passed, zero skips/failures/warnings.
- JavaScript renderer: 24 passed. Phase3 Insights-setting and Studio-label browser suites passed.
- Real aggregate consumer/browser: 3 offered industries × 2 horizons; all ready outputs finite;
  unavailable channels show explicit reasons; missing/stale anchors refuse projection.
  All three scenario exports passed; no browser JavaScript errors or 390px horizontal overflow.
- Installed runtime: 66 R namespaces verified and Python dependency consistency passed.

Final targeted regressions: publication/environment tests 85 passed; agent/environment tests
106 passed plus the same unavailable-report skip. Independent final publication review passed
25 checks. All 5,052 numeric leaves exactly match the originally authorized publication;
only build, lineage, and gate metadata changed. The persistent archive and its previous pointer
were verified, and the publication lock was released. Normal final G6 comparison used the
then-active v2; it did not silently rewrite the earlier waived comparison against v1.

Prior SGS real-input evidence was also recovered and reviewed: the 2026-09-30 run completed
373 studies (140 estimable, 233 not estimable, zero unbuilt); 840 backtest rows and 496 metrics
exactly match its parity rebuild; 516 unaffected forecast rows and 170 unaffected metrics stayed
unchanged. LobbyView backtesting ran. Contribution backtesting intentionally remains unrun
because its missing-2020 data collection was cancelled by the owner; it was not revived here.
 P&C
roster-PAC and lobbying remain unavailable with explicit evidence reasons; banks and credit
unions have ready primary channels. Community banks has an anchor snapshot but is not an
offered model. Auto lobbying remains withheld (G4); log-lobbying MAE 4.050 versus naive 3.936
remains a G9 warning. Licensed raw PDF/bulk-source checks were not represented as passed.

## Evidence and activation

Pod directories: `logs/`, `out/runs/`, `verification/`, `landing/metadata/`, and `completion/`.
The landing packet preserves the clean committed source separately from the working-copy
peer overlay and includes exact file hashes, object-pack hashes, index/ref preconditions,
and rollback backups. `landing/activation/WINDOWS_ACTIVATION.md` records dormant activation
steps. No local console restart or Windows task registration is part of this pod-only run.
