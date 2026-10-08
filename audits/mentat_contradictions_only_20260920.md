# Contradictions-only accounting and downstream measurement review

2026-09-20. Code and fixture verification; not a remeasurement of all published reports.

The governing rule is that magnitude, rarity, missing metadata, search confidence, or disagreement with expectations do not establish a contradiction. Retained uncertain amounts are provisional, not certified unique giving. Explicit source policies, identified non-giving events, and supported duplicate/amendment links remain effective. Raw databases, accepted baselines, archived runs, and published workbooks were not rewritten.

## Confirmed faults corrected

| Fault | Correction and counterexample |
|---|---|
| Every rejected search match was treated as an attribution contradiction. | Separate explicit adjudication from automated heuristics; evaluate reported identity evidence. A rejected blank employer or `CONSULTANT` retains its amount and a review flag. A reported `OTHER BANK` still contradicts an unrelated listed company. |
| Any non-placeholder word was assumed to name a different organization. | Shared R/Python vocabulary distinguishes generic professions and missing information from organization evidence. Unrecognized names remain unresolved. |
| A generic hockey occupation excluded a row. | Remove the automatic occupation-only exclusion. Explicit configured exclusion patterns and persistent adjudications remain intact. |
| Only accepted matches reached report summaries and raw exports. | Apply an evidence-based attribution disposition, retain all raw decisions, and carry uncertainty into payloads and Data workbooks. An individual found in a corporate query is not thereby treasury giving. |
| The final publication guard rejected missing form/line/role metadata and invented zero-dollar decisions for omitted nonmatches. | Missing receipt evidence remains counted and flagged. Every scoped source must have an explicit payload decision. Contradictory or established non-giving roles still block counted publication. |
| Equal committee, cycle and amount were treated as proof of a repeated disclosure memo. | Remove that shortcut. Same-filing, compatible, explicit back-reference evidence still resolves actual duplicates. |
| Ambiguous downstream versions were collapsed to the largest filing number. | Default to retaining distinct observations with unverified-version flags. Verified amendment-family headers still establish supersession. Policy/version changes invalidate old transfer caches. Legacy latest/withhold policies remain separately keyed sensitivity scenarios. |
| Missing monetary values became zero; string `false` was interpreted as a memo flag. | Required amounts fail as unavailable instead of manufacturing zero. Parse memo flags by their values consistently. |
| Candidate-level snapshot replacements could mix incompatible workbook and snapshot schedules. | Select whole saved schedule partitions and disclose differing candidate/direction measurements, including equal totals with different recipients. Show the selected snapshot's coverage and hash. Do not present either source as a correction proved against the other. |
| Concentration percentages used positive gross rows while numerators used net amounts. | Net $100 - $20 plus another candidate's $20 gives shares 80%/20%. Net reversals keep signed amounts but make percentage shares unavailable. |
| A balancing residual was presented as successful reconciliation. | Keep the residual visible and report the source disagreement; arithmetic balance is not evidence reconciliation. |
| The map could replace the user's selected root snapshot with another saved run. | Pin the selected root and retain imported CSV scope. Downstream snapshot windows and gaps remain disclosed. |
| UI language implied a traced flow from a donor/PAC into candidates. | Label saved downstream PAC activity, observed committee routes, separate direction totals, provisional filing relationships and source differences. `Contribution / Other` is no longer shortened to a stronger claim of contributions alone. Missing candidate identities do not count as one known candidate. |

## Verification

Targeted automated coverage includes the cross-reference engine/runner/storage/digest/API, source publication guard, shared R receipt and attribution rules, Python/R transfer indexing, downstream network diamonds/cycles/gaps, graph API, map reconciliation and source selection, Data-workbook generation, R report generation, and browser rendering. Positive controls still enforce explicit exclusions, genuine source identity checks, known non-giving roles, supported memo links, and verified amendment families.

The browser fixture was visually inspected. Amount/share columns now precede long routes, provenance hashes wrap, negative amounts remain visible, and percentages that cannot be interpreted are labeled unavailable.

Final regression run: 298 Python tests passed, the R transfer-evidence suite passed, 13 UI tests passed, and the isolated map browser completed all 22 steps without browser errors. Earlier targeted R receipt-role, tidy-stage and report-generation checks also passed. Expected failing controls verified that contradictory inputs still prevent publication.

## Remaining scope limits

These are code changes for subsequent runs, not a new accepted financial baseline. Existing saved reports retain the rules and coverage under which they were produced. No claim of complete filing coverage, unique dollars, donor-to-candidate tracing, or quantified real-world accuracy follows from the passing tests. Rebuilding reports must use the designated report folder and preserve the before/after source and dollar ledgers.
