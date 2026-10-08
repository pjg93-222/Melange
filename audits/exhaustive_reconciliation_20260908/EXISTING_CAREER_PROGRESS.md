# Existing-evidence cleanup checkpoint

The Python batch reconciled existing holdings without new collection or live activation.

- 11,347 undated Politico directory rows have a single matching bounded role with the same person, office, title, and observation timestamp. Another 46 clauses reference one interval through previously accepted LDA/Politico bindings. These are sidecar decisions; the source ledger is retained.
- 144 repeated-role records and five compound clauses remain ambiguous. They were not collapsed into one career interval.
- 234 of the 1,704 bounded clauses in completed historical holdings have exact held office/title phrase mappings. These remain source claims, with no employment or identity promotion.
- Independent evaluation accounted for all 29,688 items across those three input sets.
- The partial 2018 archive contains 1,032 byte-identical twin pages: 25,800 filings and 120,269 lobbyist observations. Thirty-two single-twin pages remain held. This is an incomplete year, not a releaseable window.
- Those 120,269 observations compress to 14,425 exact person/text cases. Every original row is retained through reconstructable references. Of these, 3,100 match existing claims, 9,483 contain no covered-position text, and 1,842 have unseen text.
- Only the unseen text was parsed: 295 bounded clause candidates, 2,881 missing-date clauses, 57 excluded internship clauses, and 24 other review cases. A bounded clause alone does not establish a staffer or confirmed employment.

Receipts under `C:\Users\pgoff\AppData\Local\Melange\staffer_network\reconciliation`:

- `existing-career-completion-20260908-v2\receipt.json`
- `existing-career-completion-20260908-v2-evaluation.json`
- `partial-2018-compact-20260908-v1\receipt.json`
- `partial-2018-career-cases-20260908-v2\receipt.json`

Six focused tests passed. An additional reconstruction check verified all 120,269 source observations against their case references and all 3,257 parsed clauses against unseen parent cases.

## Adjudication, integration, and targeted backfill

Release `release-history-5.json` has been activated after candidate evaluation and focused checks. It adds 159 source-reported career observations to accepted people. Sixty historical clauses lacking accepted person/office mappings remain held; repeated source text was deduplicated without removing its filing references. The 11,347 duplicate directory records were not turned into extra employment episodes or score increments.

The exact source-person fetch for Kathleen Coulombe (`lda:lobbyist:68016`) verified matching independent copies of 42 filings spanning 2018–2026. Forty-one explicitly name her. One returned 2026 amendment does not name her and is held, demonstrating why API query membership alone is insufficient.

Five 2018 filings reconcile to four quarters after choosing the later Q4 amendment. Four same-activity historical groups are integrated as ecosystem evidence, without work-duration inference. Alane Dent's exact name, organization, and contemporaneous official reporting-line evidence link her filing record to her existing official node; three other source-native ecosystem identities are retained without cross-source merging. Offline evaluation covers 63 sampled/curated identities and finds 83 Kathleen neighbors, compared with 80 in the prior release. This is a database result, not her complete real-world network.

The new Python office-token index avoids scanning the entire office catalog for every clause. It adjudicated all 295 bounded candidates from the saved partial-2018 archive: 49 exact office/title phrase mappings and 246 held unmapped clauses. These 49 claims concern 25 source IDs and cite 67 filings; they remain outside production while the partial-window qualification and identity questions are unresolved.

Remaining: residual identity, role/date, and historical coverage gaps still require supporting evidence. Overall cleanup remains incomplete; missing facts and ambiguous records have not been silently accepted.

## Final integrated release

`release-backfilled-6.json` is active and live verification passed with revision `58587f69f6532c44fd33`, ready status, and no service errors. The person API verified the backfilled career observations and Kathleen's 83 ecosystem neighbors.

All 25 documented 2018 source-person targets passed independent acquisition comparison: 547 person/filing results representing 514 unique filings. Fourteen additional exact career statements survived latest-filing and identity checks, bringing this run's integrated career observations to 173. Of the other 35 clauses, 23 require accepted identity mapping; 12 lack exact latest-filing support or have an ambiguous office. The originals remain in the archive. No internship employment or inferred work duration was promoted.

The selected adjudication/integration/backfill release is complete. This does not certify every residual identity, career endpoint, or historical year as complete. See `live-backfilled-6.json` and `RUN_STATE.json` for the final verification and explicit remaining evidence gaps.

## Continued review: release 8

The earlier “final integrated release” label describes a checkpoint, not completion of the backlog. Release 8 processes all 1,999 bounded historical clause cases already assembled: 1,704 from completed windows and 295 from the partial-2018 adjudication.

The integration now distinguishes a standardized employment record from a verbatim source observation. An unmatched office/title catalog entry no longer prevents an authenticated dated filing statement from appearing in an established person's evidence panel. It does not become a confirmed job, staffer qualification, or work-duration edge.

- 856 additional source statements integrated; 508 clause cases supplied additional references for existing statements.
- 13 historical source IDs have unique exact-full-name and exact-bounded-career-statement matches to existing people. These qualify evidence attribution only; identity aliases and routing remain unchanged.
- 399 clause cases still require identity evidence, across 149 historical source IDs.
- 15 clause cases lack an exact statement in verified latest target filings.
- 221 clause cases require target-history verification, across 102 source IDs. These are not described as failed source checks because those targets have not been checked.

Of the previous 60 historical integration holds, two now have supported attribution; of the previous 35 targeted-backfill holds, four now have supported attribution. This accounting does not silently close the other holds.

An independent check verified all 1,999 case decisions, original clause text and date precision, retained preexisting evidence, and unchanged routing/identity configuration. Seventeen Python tests and three display tests passed. Offline route evaluation covered 63 identities and retained Kathleen's 83 ecosystem neighbors. Additional supporting references are now visible in the person evidence display.

Receipts: `exhaustive-20260908-v2/candidate-reviewed-8.review.json`, `tests-reviewed-8.json`, `evaluation-reviewed-8.json`, and `release-reviewed-8.json` under the reconciliation directory. The current residual cases are also exported to `residual-bounded-review-8.json` alongside this document. The broader undated-career and identity queues remain incomplete; no full-backlog completion is claimed.
