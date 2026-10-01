# Moneyball skill library

20 skills that let a zero-context engineer or Sonnet-class model maintain and advance this
project. Built 2026-07-09/10 (14-agent repo discovery → 16 parallel authors → factual/doctrine/
usability review → fix pass; every command and number verified against the repo at authoring time).
Each skill's frontmatter `description` says exactly when to load it; each ends with a
"Provenance and maintenance" section of one-line re-verification commands.

**Start here for any change:** `moneyball-change-control` (the constitution — gates, project law,
what is Paul's decision alone). Nothing in this library overrides it.

## The 20 skills

| Skill | One line |
|---|---|
| codex-executor | Claude-reviewed Codex lane with runtime contracts, a duplicate-aware ledger, bounded correction, and live Fable→Sol retry routing |
| gemini-perception | The media perception lane (Antigravity CLI, Gemini 3.6 Flash): images/screenshots/OCR in, four-list observation reports out; zero authority |
| grok-companion | Adversarial counsel (xAI Grok Build CLI, SuperGrok subscription): attacks plans, claims, and syntheses before they ship; zero execution authority, zero veto; also the no-API-key X search lane and the Monday catalog collector |
| moneyball-change-control | Change classes, the 4-step verification protocol, gating vocabulary, all 18 project laws with incidents, user-domain boundaries |
| moneyball-architecture-contract | The 5-layer system shape, 9 load-bearing invariants (two cpf physics, '—' ontology, CRN determinism…), artifact ownership, known-weak points |
| moneyball-build-and-env | Recreate the environment from zero; code-vs-data git split; new-script house style; Windows/OneDrive traps |
| moneyball-run-and-operate | The chain (`CHAIN` in `fec/run_pipeline.py:45-292`: 80 entries; a default run executes 79 because `DESK_RESPONSIVENESS=0` drops `responsiveness_layers.py` at `:300-302`; as of 2026-09-30), refresh order, collectors, workbook discipline (+ apply_* DANGER table), dashboards/preview/deploy |
| moneyball-config-and-flags | All env dials + workbook dials + kernel constants, verified per row; add-a-dial checklist |
| moneyball-debugging-playbook | Symptom→cause→discriminating-experiment→fix for the 12 live failure modes, each with its real incident |
| moneyball-diagnostics-and-tooling | The test/audit harnesses + 8-tool diagnostic fleet + 3 shipped read-only scripts (rank_delta, artifact_freshness, env_dials) |
| moneyball-validation-and-qa | The 6-rung evidence ladder, user-gold-label machinery, add-a-test / add-an-audit-check templates |
| moneyball-failure-archaeology | Every incident, dead end, retired route, and refuted finding — so no settled battle is re-fought |
| influence-modeling-reference | The persuasion/network/optimization theory as implemented here, from zero, with citation-honesty rules |
| psychometrics-reference | Measurement theory from zero: reliability, validity, halo, power, the validated-trait ledger semantics |
| quant-model-evaluation | General evaluation and assumption-testing skill for quantitative systems (finance and computational social science depth): 7-phase protocol, 11 domain modules, 11 read-only scripts, and a Melange binding (`references/bindings/melange.md`) |
| moneyball-research-methodology | The prereg → simulate-battery → one-look discipline; the hunch-to-promotion/retirement lifecycle |
| moneyball-proof-and-analysis-toolkit | Ten prove-it-first recipes (power study, plant battery, byte-match purity…), each with a worked repo example |
| moneyball-docs-and-claims | Doc-plane vintages, house style, commit vocabulary, the validated-claims ledger + forbidden-claims receipts |
| moneyball-congress-rollover-campaign | The executable, decision-gated campaign for the 119th→120th Congress rollover (+ readiness gate script) |
| moneyball-research-frontier | Five open SOTA-advancing problems with first-steps-in-this-repo and falsifiable milestones |

## Locations and git status

This library lives at the live-tree root `.claude/skills/`. The original 16-skill
library was authored in worktree `nifty-cray-f6d053` (b994d9332, 2026-07-10);
`codex-executor` was added later as the versioned Claude–Codex coordination lane
(fe8d6d142, 2026-07-18), then `gemini-perception` (9d8217db8) and `grok-companion`
(67569857d), both on 2026-07-24, and `quant-model-evaluation` (c13f3a5d4, 2026-09-30)
(history corrected 2026-09-30 from `git log`).
The library is tracked through the `.gitignore` keep rules:

```
!.claude/skills/
!.claude/skills/**
```
