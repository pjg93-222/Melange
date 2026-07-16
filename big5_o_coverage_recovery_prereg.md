# O Coverage-Recovery Successor

**STATUS: LOCKED 2026-07-16.** User-authorized O-only recovery: "Keep C ... let's get O
in, see what you can do to get the 250, or lower the floor." C remains exactly as recorded in
`big5_onc_crosspanel_successor.json.candidate`: strong insider-visible execution evidence, no
academic-panel promotion, and no score rewrite. E, A, N, every original score, both gold panels,
and every production consumer are outside this experiment.

The first O cross-context criterion stopped at 198 members before either gold panel was opened for
O. Its artifact and result are immutable controls:

- `big5_onc_new_criteria.json.candidate`:
  `eb16cde3c160f7fc14280a3c6b0ae4754a913606fcd2e78fa7a4fd1c8dea8e12`
- `big5_onc_crosspanel_successor.json.candidate`:
  `fc3bdbfa59671f61891c34d38e13839f57092c2110d760a12e221e7fc43ba5e9`
- preserved original score:
  `2b351af4c8fd077cc7fd10b05001a2843f850a3a83f956d5ac75b644a4317c13`
- preserved gold:
  `ff5a948361f478cf7d7da2ce84e333594b242cb65574760dd285a8dbd57afe7a`

This recovery may create only `big5_o_coverage_recovery.json.candidate` and, if licensed,
`big5_o_coverage_result.json.candidate`. It may not edit the immutable controls above.

## Criterion construction -- fixed before recovery build

Use the same frozen 18-domain lexicon, `INTERVIEW` and `CREC` sources, regex tokenizer,
order-independent SHA-256 package selection, 200-package cap, 250-token-per-package cap, Shannon
domain entropy, MATTR-100, `.70 * entropy_z + .30 * mattr_z` source formula, both-source
requirement, nuisance residualization, and final z-score as the stopped criterion.

Only source eligibility changes. A member/source is recovery-eligible at >=5 selected packages,
>=1,000 selected tokens, >=25 domain hits, and >=4 active domains. For each eligible source, apply
the following evidence factor to the within-chamber source score before combining sources:

`sqrt(min(1, packages/10) * min(1, tokens/2000) * min(1, domain_hits/50))`

Thus a record meeting the old package/token/hit floors receives factor 1, while a newly admitted
thin record is continuously shrunk toward the chamber mean. Active-domain breadth remains a hard
floor and is never shrunk into eligibility. Require both sources after these rules. Residualize the
two-source mean on intercept + female + Republican + chamber + log selected-token total + log
selected-package total, then z-score. No panel, gold-derived variable, original O outcome, trait
label, alternative threshold, sign, or weight may enter construction.

Preserve per-source raw metrics, evidence factors, and source scores. On the 198-member stopped
criterion overlap, report Pearson correlation between stopped and recovered final O. Also report
INTERVIEW-vs-CREC correlation for the full recovered set and separately for added members absent
from the stopped criterion.

## Pre-look readiness ladder

The first satisfied path licenses exactly the same single O look. These are fixed alternatives,
not post-result choices.

**Primary 250 path:** total >=250, House >=150, Senate >=30, full-set source r >=.10,
Spearman-Brown >=.18, added-member n >=22 and source r >=.05, stopped-core overlap >=190 and
stopped-vs-recovered r >=.90.

**Guarded 220--249 path:** total >=220, House >=135, Senate >=30, full-set source r >=.15,
Spearman-Brown >=.25, added-member n >=22 and source r >=.10, stopped-core overlap >=190 and
stopped-vs-recovered r >=.95.

Primary is evaluated first. The guarded path is allowed only when total is 220--249 and every
stronger reliability/core bar passes. Below 220, or failure of both paths, records
`CRITERION_STOP_BAR_MISS` and stops without opening either O panel. No floor may be lowered again.

## Fixed O candidate and one-look bars

For members present in both the preserved original O and recovered criterion, z-score each over
their intersection and combine `70% preserved original O + 30% recovered O`; z-score the result.
Missing recovered values remain missing. No fitted weight, sign flip, subset, nonlinear transform,
or alternative candidate is permitted.

If the criterion is licensed, append `## CRITERIA FREEZE ADDENDUM` with its SHA-256, readiness
path, coverage, reliability, core preservation, input verification, RED boundary, and build
commit. Then evaluate the O candidate once, separately, in `academic_experts` and
`senate_insiders`. Each panel must pass all of:

1. n >=30;
2. Pearson r with own O >=.20;
3. one-sided permutation p <.10, K=9,999, seeds 20260916 academic and 20260917 insiders;
4. own r strictly greater than the maximum absolute correlation with C, E, A, and reverse-ES N;
5. partial r controlling female and Republican >=.10 (chamber is constant Senate context).

The result also reports preserved-original O over the same recovered roster as historical context.
Both candidate panels passing records `DUAL_PANEL_SUCCESSOR_CANDIDATE_PASS`; any miss leaves O's
one-panel status unchanged. Nothing ships automatically. The look refuses without an exact freeze
hash or after a newline-anchored `## RESULT-O-RECOVERY` heading.

## TDD, audit, and stopping rule

Tests must be observed failing before implementation and must enforce immutable hashes, exact
eligibility/factor rules, both-source missingness, deterministic readiness paths, core preservation,
criterion/gold separation, fixed candidate weight, candidate-only outputs, C-result immutability,
freeze matching, and second-look refusal. A clean focused suite and full kernel are required. The
full audit is reported honestly; unrelated pre-existing failures cannot be relabeled as a pass.

After `## RESULT-O-RECOVERY`, no threshold, factor, weight, subset, seed, or same-input O successor
may be tried. Merge or production promotion requires an actual dual-panel pass, a clean relevant
gate, and explicit user ratification.
