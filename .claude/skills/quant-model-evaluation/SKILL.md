---
name: quant-model-evaluation
description: Evaluate a mathematical, statistical, machine-learning or simulation system and test the assumptions in its empirical foundations. General data-science skill with depth in finance and computational social science (political money, lobbying, banking and credit, legislative behaviour, text-as-data, networks, geography). Load when asked to audit, evaluate, validate or stress-test a model or pipeline; to check whether a number, trend or causal claim holds; to review a regression, forecast/backtest, allocator or optimizer, efficiency frontier, ROI or cost-per-outcome metric, Monte-Carlo engine, classifier, LLM-labelled measure, network model, geospatial join or dashboard; or to check the citations and regulatory status behind a method. Ships read-only scripts (citation integrity, R summary-format regression report, backtests, confounding sensitivity, DEA frontiers, Monte-Carlo error, global sensitivity, vacuous-check mutation testing, calibration, leakage, spatial audits). Evaluation only - it never edits, regenerates or commits the system under audit. Does NOT replace a project's own change-control or research-methodology skills (load those first where they exist; a project binding names them), does not build new production models, and is not legal advice.
---

# Quantitative model evaluation

This skill turns "the model says X" into a tested statement about what holds, what is fragile, what is wrong and what could not be checked. It works on any quantitative system: an econometric study, a forecasting pipeline, a budget allocator, a scoring dashboard, a Monte-Carlo engine, a classifier whose outputs feed other models. Its examples and deepest modules come from finance and computational social science, because that is where it is used most: political money, lobbying, legislative behaviour, banking and credit, text and network measures.

It is a synthesis. The statistical core, simulation and validation methods adapt material from K-Dense-AI's `scientific-agent-skills` (MIT; see `NOTICE.md`). The finance, social-science, regulatory and citation modules come from research done for this skill in September 2026, with every scholarly citation checked against CrossRef or OpenAlex (the few that could not be confirmed are marked UNVERIFIED in `references/sources.md`). The protocol borrows its structure from model-risk practice (conceptual soundness, outcomes analysis, ongoing monitoring, effective challenge) and from engineering credibility standards (verification, validation, uncertainty quantification).

## When NOT to use this skill

- You are **changing** a system, not evaluating it. Use the project's change-control skill; this skill only produces findings and questions.
- You need the rules for **preregistered confirmatory looks** (when a look is allowed, how it is locked, outcome vocabulary). Use the project's research-methodology skill where one exists; this skill supplies the tests inside those rules.
- You want to **build** a new production model. This skill evaluates models; it does not design them.
- You need **legal advice**. `references/regulatory.md` maps rules to checks and flags items for counsel; it does not replace counsel.

## Hard rules

1. **Evaluate, do not change.** Never edit, regenerate, re-run with writes, or commit the system under audit. The scripts read their inputs and write only inside a fresh run folder; the one exception is Glass Box progress events (rule 12), which `--no-glassbox` switches off.
2. **The owner applies.** Findings go to the owner as questions or options, each with its measured blast radius. Present, then wait. A project binding may add stricter gates.
3. **Fix criteria before looking.** Write the pass rule for every test before running it. Never move a threshold after seeing a result, never weaken a test so something passes, and never tune toward a preferred named outcome.
4. **Census before sample.** If a property can be enumerated from stored data, enumerate it. If you must sample, say how and why.
5. **Independence.** Re-derive every number you report by a second path. Never validate an artifact with the code that produced it. A KILLED verdict, and any citation graded fabricated, contradicted or identifier-conflict, needs a second independent reader.
6. **Controls.** Every detector gets a negative control or a planted signal. A check that cannot fail is vacuous; prove it can fail (`scripts/mutation_check.py`).
7. **Honest uncertainty.** UNVERIFIED-HERE is never a pass. Say what you could not test and what would unblock it.
8. **Trend first, never "confirmed".** Report sign, size and consistency first, uncertainty second, power third. Causal wording must follow the identification.
9. **Execution safety.** Running the system under audit, spawning its engines, or spending the owner's time or money is owner-gated. In repositories where importing a module executes it, read files instead of importing them.
10. **Citations and law.** Grade every load-bearing citation (`references/citation.md`). A paper cited for a mechanism never validates a local constant. Every regulatory statement carries a status date and is re-verified on the day it is relied on (`references/regulatory.md`).
11. **Security and privacy.** No package installs without the owner's OK. Never pipe a remote script into a shell, never scan for credentials or `.env` files, and never send user identifiers (emails, names) to an external service unless the owner supplies them for that purpose. Respect data-use law and platform terms, for example the FEC restriction on using contributor data.
12. **Observability.** The scripts emit Glass Box events when the shared stream exists. Long analyses you write yourself should emit too.
13. **Project bindings win.** If `references/bindings/<project>.md` exists for the project you are in, load it right after this file. Its rules override these defaults.

## Quick start

1. Load the project binding, if any, and the project's change-control skill.
2. Fill the **scope** and **model card** (phases 1-2 below) from the code and data, reading file bodies rather than names.
3. Build the **assumption register** (phase 3), pulling candidate assumptions from the module that matches each part of the system (router below).
4. Write the **test plan** with criteria fixed in advance (phase 4), run the tests read-only (phase 5), assign **verdicts** (phase 6).
5. Write the **report**, rank findings, and stop (phase 7).

## The protocol

### Phase 1: Scope

Record: system name and version (commit), owner, the decision or claim it feeds, who consumes its outputs, the audit question, what is out of scope, and a materiality tier.

- **T1**: drives money, public claims or irreversible decisions.
- **T2**: internal analysis that feeds T1.
- **T3**: exploratory.

### Phase 2: Model card

| Field | What to record |
|---|---|
| Purpose and decision | What the system computes and which decision uses it |
| Inputs | Source, pull date or vintage, provenance, known data-generating traps (see the domain module) |
| Transformations | Joins, filters, imputations, aggregations, each with file:line |
| Constants and dials | Value, location, and status: **ratified** by the owner, **literature-shaped** (borrowed from a paper, not fitted), **fitted** to data, or **arbitrary** (JSON tokens for `scripts/global_sensitivity.py`: `ratified`, `literature`, `fitted`, `arbitrary`) |
| Implementations | How many independent copies of the same maths exist (backend, front end, report port) and what proves they agree |
| Outputs and consumers | Artifacts, surfaces, downstream models |
| Existing tests | Structural or invariant tests, determinism tests, outcome or calibration evidence. A system with only the first two has never been validated |
| Open rulings | Decisions pending with the owner that the audit must not pre-empt |

### Phase 3: Assumption register

One row per assumption. Enumerate by class, asking each class's question of every component:

| Class | Question to ask |
|---|---|
| `DATA` | What would make this input wrong, incomplete, stale or double-counted? |
| `MEASUREMENT` | Does the variable measure what its name says, reliably, for every subgroup? |
| `FUNCTIONAL-FORM` | Why this curve, cap, saturation or link function, and what if it is wrong? |
| `CAUSAL` | What design identifies this effect? What rival explanation fits the same data? |
| `STATISTICAL` | What independence, distribution, stationarity or clustering is assumed? |
| `COMPUTATIONAL` | Is the result converged, deterministic, and identical across implementations? |
| `DECISION` | Are the objective's units, the constraints, caps and gates coherent, and consistent across engines? |
| `LEGAL` | May this data be used this way, and is the rule cited still in force? |
| `PRESENTATION` | Do labels, units, rounding and ranks say what the number actually is? |

Register format:

| ID | Class | Assumption | Where encoded (file:line or doc) | What breaks if false | Tests (checklist IDs, scripts) |
|---|---|---|---|---|---|

### Phase 4: Test plan

For each register row, write: the test; the **criterion fixed before running** (metric, threshold, direction); the negative control or planted signal; the data it reads; the cost class (`READ-ONLY`, `NETWORK`, or `RUNS-SYSTEM`, which is owner-gated); and the second computation path for any number that will be reported. If a claim is confirmatory and the project has a preregistration discipline, hand it to that discipline instead of running an ad hoc look.

Two checks before locking the plan:
- **Can the criterion be met at all?** A bar tighter than the data's own precision (rounded exports, display quantization, Monte-Carlo noise) can never pass. Check the achievable precision on a known case first, and set the bar above it.
- **Can you prove the plan came first?** Save the plan as a file, record its sha256 and UTC time in the report, and only then run the tests. Changes after that point are listed as deviations, never folded in silently.

### Phase 5: Execute read-only

Run the scripts (catalog below) or short analyses of your own that read, never write, the system's artifacts. Every result in the report carries a provenance line:

`commit <sha> · system SEED/MC <s>/<n> · script seed <s2> · inputs sha256:<first 12> · N <independent units> (<stratum>) · <UTC date>`

The scripts record their own part (script, version, seed, input hashes, package versions, time) in `report.json` and print a short form. You add what only you know: the system's commit, the system's own SEED and Monte-Carlo count, and the number of independent units behind the result.

### Phase 6: Verdicts

| Verdict | Meaning |
|---|---|
| `SURVIVES` | Tested; holds within the criterion fixed before the test |
| `WOUNDED` | Holds only in part: fragile, holds in some strata only, scope-limited, or repairable by rewording |
| `KILLED` | Tested and violated, and the violation is material. Record only after a second independent reader agrees; until then write `KILLED (pending second reader)` |
| `UNVERIFIED-HERE` | Could not be tested with the access, data or tools at hand. Never a pass or a fail |

These four verdicts judge **assumptions and claims about the system**. When you re-check a **finding someone else reported** (an earlier audit, a census, a colleague's number), say whether it `REPRODUCED`, `PARTLY REPRODUCED` or `NOT REPRODUCED`, then judge the assumption it bears on separately. A finding such as "the allocator has no stance gate" can reproduce while the assumption "every allocator shares one gate" is KILLED; report both, in that order.

A script's printed KILLED is a candidate. It enters a report as KILLED only after the second reading.

Tag every verdict with its evidence: `[CODE]` file body read · `[DATA]` artifact parsed · `[RUN]` computed in this audit · `[GIT]` history · `[LIT]` literature, graded per `citation.md` · `[REG]` law or standard, status-dated · `[OWNER]` owner or decision-record statement, not re-derived.

Then fill the system-level **credibility table**, marking each factor ESTABLISHED, PARTIAL or ABSENT with one line of evidence:

| Factor | Question |
|---|---|
| Verification | Does the code compute what the documentation says, checked against known cases? |
| Validation | Have outputs been compared with realized outcomes, out of sample? |
| Input pedigree | Are inputs traceable, current, reconciled to source totals? |
| Uncertainty | Is uncertainty quantified (sampling, Monte-Carlo, parameter, model)? |
| Robustness | Do decisions survive plausible changes in uncalibrated constants and specifications? |
| Use history and monitoring | Is there a record of performance in use, and drift triggers? |

### Phase 7: Report and stop

```
# Evaluation: <system> (<commit>, <UTC date>)
Scope, tier, audit question
Headline (at most five lines; trend first; no "confirmed")
Credibility table
Findings, ranked by materiality x fragility
  ID · verdict · class · evidence tags · location (file:line)
  numbers with units, window, denominator, vintage
  blast radius: what changes downstream if this is fixed (measured, not guessed)
  question or options for the owner
Assumption register (full)
Tests run: commands and provenance lines
Could not verify: each UNVERIFIED-HERE item and what would unblock it
Citations graded; regulatory items with applicability labels
```

Rank by **materiality** (tier; money or decisions affected) times **fragility** (how easily the conclusion flips under sensitivity, Monte-Carlo noise or a second data source). Then stop. Do not apply fixes.

## Presentation contract

- **Trend first.** Sign, size, and consistency across windows, strata and specifications come first. The interval or p-value follows on one line, then power or the minimum detectable effect.
- **Words follow design.** "Associated with" unless an identified design supports "causes". Never "confirmed", "proven" or "validated" for a single analysis.
- **Every number** names its units, window, denominator and data vintage.
- **Pooled estimates** across party, chamber, sector or period show their strata, or carry the label UNSTRATIFIED.
- **Regressions** are shown as the real R `summary(lm())` print followed by a labelled robust-inference block. `scripts/regression_report.R` produces exactly this.
- **Forecasts** are compared out of sample against naive and seasonal-naive benchmarks, with the backtest's power stated. A short backtest that fails is weak evidence of no effect; a short one that passes is weak evidence of an effect.
- **Surfaces**: a dashboard that describes data is different from one that recommends action. Flag advisory wording on a descriptive surface.

## Module router

| If the question is about | Load |
|---|---|
| Regression diagnostics, clustering, time series, multiplicity, power, bootstrap, missing data, the presentation contract | `references/core-statistics.md` |
| Charts, dashboards, labels, units, rounding, ties and ranks, clamped curves | `references/data-visualization.md` |
| Money data (FEC, LDA), spend-response curves, allocators and optimizers, efficiency frontiers, backtests, finance geography | `references/finance.md` |
| Causal claims, measurement validity, LLM and text labels, networks, legislative data | `references/social-science.md` |
| Classifiers, leakage, calibration, drift, ML predictions used as measures, LLM components | `references/machine-learning.md` |
| Maps, districts, crosswalks, spatial dependence, census geography | `references/geospatial.md` |
| Simulations, Monte-Carlo error, sensitivity analysis, optimizer verification, V&V standards | `references/engineering-simulation.md` |
| Pipelines, determinism, freshness, parity across implementations, audit harnesses, provenance | `references/automation.md` |
| Many simultaneous tests, shrinkage rankings, cross-cycle harmonization, budget shares as compositions | `references/multi-omics-transfer.md` |
| Model-risk guidance, AI governance, data-use law, platform terms, research ethics, reporting guidelines | `references/regulatory.md` |
| Citation integrity, retractions, superseded instruments, citation styles, provenance of claims | `references/citation.md` |
| Full bibliography and attributions | `references/sources.md`, `NOTICE.md` |

## Spending-efficiency quick map

Systems that turn money or effort into predicted outcomes (allocators, ROI metrics, frontiers, cost-per-outcome scores) fail in recurring ways. Start here, then go to the modules.

| Component | First tests |
|---|---|
| **Allocator or optimizer** (budget spread over targets) | Gates and constraints identical across every engine that allocates (`DECISION`); every allocated dollar maps to a legal instrument and cap, per election vs per cycle (`finance.md`); equal marginal returns at the optimum and an exact solve on a small instance (`finance.md`, `engineering-simulation.md`); allocation sensitivity to uncalibrated constants (`scripts/global_sensitivity.py`); any outcome validation at all |
| **Response curve** (money to probability of an outcome) | The identifying design, or the label "associational" (`social-science.md`, `scripts/confounding_sensitivity.py`); whether the saturation constant is identified by data or just a prior (profile check); implied effect sizes against credible designs (`finance.md`); calibration against realized outcomes (`scripts/calibration_report.py`) |
| **Efficiency score or frontier** | Units per input and output, dimensionality, outliers and bootstrap intervals (`scripts/dea_frontier.py`); no naive second-stage regression on scores; Monte-Carlo error of frontier points (`scripts/mc_error.py`); monotonicity checks that read clamped data are vacuous (`scripts/mutation_check.py`) |
| **ROI or cost-per-outcome metric on a surface** | The label's unit matches the computed unit; ties and percentile ranks; rounding that zeroes small values; sums of non-additive quantities; circularity when the metric is built from the optimizer it judges (`data-visualization.md`) |
| **Money inputs** | Data-generating traps (memo rows, conduit double counts, transfers, amendments, unitemized money), reconciliation to source totals, point-in-time pulls, and a census of imputed rows with results reported with and without them (`finance.md`) |
| **Forecasts of money or growth** | Out-of-sample backtest against naive and seasonal naive (`scripts/backtest_eval.py`), breaks and stationarity, correction for the number of specifications tried, and the backtest's power (`finance.md`, `core-statistics.md`) |

## Scripts

Run from the skill folder or give full paths. All scripts are read-only on their inputs, write a new run folder under `--out` (default `./qme_out`), print a markdown report, and write `report.md` and `report.json` with a provenance block (paths under the home directory are written as `~`). Shared flags: `--out DIR`, `--seed N` (default 20260930), `--no-glassbox`, and for the Python scripts `--quiet`. Every script documents its own thresholds and verdict rules under `--help`; read it before fixing a criterion.

| Script | Question it answers | Example |
|---|---|---|
| `scripts/cite_check.py` | Do the cited works exist, match their metadata, and remain unretracted? | `python scripts/cite_check.py --bib refs.bib` |
| `scripts/regression_report.R` | The R `summary(lm())` print plus a labelled cluster-robust block, wild bootstrap and diagnostics | `Rscript scripts/regression_report.R --data d.csv --formula "y ~ x + z" --cluster state` |
| `scripts/backtest_eval.py` | Does a forecast beat naive and seasonal-naive benchmarks out of sample, stably? | `python scripts/backtest_eval.py --data f.csv --actual y --forecast yhat --time cycle --benchmark seasonal:2` |
| `scripts/confounding_sensitivity.py` | How strong would an unobserved confounder have to be to erase the estimate? | `python scripts/confounding_sensitivity.py --mode evalue --rr 1.8 --lo 1.2 --hi 2.6` |
| `scripts/dea_frontier.py` | Efficiency scores with outlier, dimensionality and bootstrap checks | `python scripts/dea_frontier.py --data u.csv --inputs spend --outputs wins --rts vrs --bootstrap 1999` |
| `scripts/mc_error.py` | Is the Monte-Carlo run count enough for the decision gaps it drives? | `python scripts/mc_error.py --data reps.csv --rep rep --compare planA,planB --target-rel 0.01` |
| `scripts/global_sensitivity.py` | Which uncalibrated parameters drive the output? (design, then analysis; never runs the model) | `python scripts/global_sensitivity.py --problem p.json --method sobol --design-only --N 1024` |
| `scripts/mutation_check.py` | Can this check actually fail? | `python scripts/mutation_check.py --input data.json --auto --cmd python my_check.py '{input}'` (quote `{input}`: PowerShell reads a bare one as a script block) |
| `scripts/calibration_report.py` | Are predicted probabilities calibrated, and better than the base rate? | `python scripts/calibration_report.py --data p.csv --y flipped --p p_flip --group party` |
| `scripts/leakage_audit.py` | Did test information leak into training? | `python scripts/leakage_audit.py --train tr.csv --test te.csv --group member --time date --embargo 90D` |
| `scripts/spatial_audit.py` | Are joins and crosswalks sound, and is there spatial dependence? | `python scripts/spatial_audit.py --mode crosswalk --xwalk zip_cd.csv --from zip --to cd --weight res_ratio` |

Exit codes: `0` every check SURVIVES; `1` at least one WOUNDED or KILLED; `2` usage or input error; `3` UNVERIFIED-HERE present and no negative verdicts, or nothing was evaluated. A KILLED printed by a script is a candidate until a second independent reader confirms it (hard rule 5).

`mutation_check.py` executes the command you give it. In a repository where importing code executes it, point it only at checks the owner has approved.

**Environment.** Python 3.10 or later with numpy, pandas, scipy and statsmodels; geopandas for `spatial_audit.py`. Optional and used when present: SALib, libpysal and esda, arch, linearmodels; each script says which path ran. R 4.x for `regression_report.R`, with jsonlite; sandwich and lmtest are used when installed, otherwise hand-built HC1/CR1 and a wild cluster bootstrap run in base R. If `Rscript` is not on PATH, set `QME_RSCRIPT` or look under `C:\Program Files\R\R-*\bin\` on Windows. Tests: `python -m pytest scripts/tests -q`.

**Glass Box.** When `~/.claude/glassbox/events` exists or `GLASSBOX_EVENTS_DIR` is set, each script writes started, stage, completed and failed events there. `QME_GLASSBOX=0` or `--no-glassbox` switches this off.

## Working with subagents

- Fan out read-only work by module or by component, and brief each agent fully: paths, rules, what done looks like, the evidence tags to use.
- Require file:line for every code claim and a census where the data allows one. Agents that summarize from file names produce confident fiction.
- Review agent output against the real artifacts yourself, reproducing anything surprising. Verifier agents over-claim in both directions, including false "fabricated" verdicts.
- Write new analysis code with the strongest model available; use lightweight models only to locate facts.
- No subagent applies a fix.

## Project bindings

Project-specific rules, system maps and audit targets live in `references/bindings/<project>.md`. Load the binding right after this file when you work inside that project.

| Binding | Covers |
|---|---|
| `references/bindings/melange.md` | Melange Systems: the Moneyball engine, the Mentat R pipeline and the CU-geography lane; house rules, ratified constants, the spending-efficiency system map and the audit-first list |

## Provenance and maintenance

- Version 1.0.0, built 2026-09-30. Sources: K-Dense-AI/scientific-agent-skills at tree `65d6e786832e2c52832713117bbbf5096b56f77f` (MIT), plus the finance, computational-social-science, regulatory and citation research of 2026-09-29/30 (bibliography in `references/sources.md`).
- Run the test suite after any change: `python -m pytest scripts/tests -q -p no:cacheprovider` (the flag keeps pytest from leaving a cache folder in the skill).
- Time-sensitive facts carry "(as of DATE)" in the modules: regulatory status, API limits and prices, package versions, redistricting. Re-verify them before relying on them, and refresh the status register in `references/regulatory.md` at least quarterly.
- Re-check the bibliography with `python scripts/cite_check.py --text references/sources.md` (network; public pool; add `--mailto` only with an address the owner supplies for that purpose).
- Changes to this skill follow the host project's documentation change rules.
