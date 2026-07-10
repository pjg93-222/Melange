# Moneyball skill library

16 skills that let a zero-context engineer or Sonnet-class model maintain and advance this
project. Built 2026-07-09/10 (14-agent repo discovery → 16 parallel authors → factual/doctrine/
usability review → fix pass; every command and number verified against the repo at authoring time).
Each skill's frontmatter `description` says exactly when to load it; each ends with a
"Provenance and maintenance" section of one-line re-verification commands.

**Start here for any change:** `moneyball-change-control` (the constitution — gates, project law,
what is Paul's decision alone). Nothing in this library overrides it.

## The 16 skills

| Skill | One line |
|---|---|
| moneyball-change-control | Change classes, the 4-step verification protocol, gating vocabulary, all 18 project laws with incidents, user-domain boundaries |
| moneyball-architecture-contract | The 5-layer system shape, 9 load-bearing invariants (two cpf physics, '—' ontology, CRN determinism…), artifact ownership, known-weak points |
| moneyball-build-and-env | Recreate the environment from zero; code-vs-data git split; new-script house style; Windows/OneDrive traps |
| moneyball-run-and-operate | The 17-step chain, refresh order, collectors, workbook discipline (+ apply_* DANGER table), dashboards/preview/deploy |
| moneyball-config-and-flags | All ~88 env dials + workbook dials + kernel constants, verified per row; add-a-dial checklist |
| moneyball-debugging-playbook | Symptom→cause→discriminating-experiment→fix for the 12 live failure modes, each with its real incident |
| moneyball-diagnostics-and-tooling | The test/audit harnesses + 8-tool diagnostic fleet + 3 shipped read-only scripts (rank_delta, artifact_freshness, env_dials) |
| moneyball-validation-and-qa | The 6-rung evidence ladder, user-gold-label machinery, add-a-test / add-an-audit-check templates |
| moneyball-failure-archaeology | Every incident, dead end, retired route, and refuted finding — so no settled battle is re-fought |
| influence-modeling-reference | The persuasion/network/optimization theory as implemented here, from zero, with citation-honesty rules |
| psychometrics-reference | Measurement theory from zero: reliability, validity, halo, power, the validated-trait ledger semantics |
| moneyball-research-methodology | The prereg → simulate-battery → one-look discipline; the hunch-to-promotion/retirement lifecycle |
| moneyball-proof-and-analysis-toolkit | Ten prove-it-first recipes (power study, plant battery, byte-match purity…), each with a worked repo example |
| moneyball-docs-and-claims | Doc-plane vintages, house style, commit vocabulary, the validated-claims ledger + forbidden-claims receipts |
| moneyball-congress-rollover-campaign | The executable, decision-gated campaign for the 119th→120th Congress rollover (+ readiness gate script) |
| moneyball-research-frontier | Five open SOTA-advancing problems with first-steps-in-this-repo and falsifiable milestones |

## Locations and git status

This library lives at the live-tree root `.claude/skills/` (this copy) and was authored in
worktree `nifty-cray-f6d053`. `.gitignore` line 28 (`.claude/*`) means it is **untracked**.
To put it in git, add keep rules after the existing `!.claude/commands/*.md` block:

```
!.claude/skills/
!.claude/skills/**
```

then `git add .claude/skills` (from a tree where `.claude/skills` exists). That edit is outside
the library's own write scope — it is Paul's (or a normally-gated change-control) decision.
