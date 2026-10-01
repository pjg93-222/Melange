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

## CRITERIA FREEZE ADDENDUM (2026-07-16)

RED boundary: `2f36484` (`LOCK O coverage recovery in RED`). Panel-blind implementation commit:
`a7740d3` (`BUILD primary-250 O coverage criterion`). The focused contract was observed RED on the
missing implementation, then passed 10/10 after construction.

criteria_sha256: `879f21fafc064eeacdb778c5d021897ce6227c29734edb2c686ad056b751c5bd`

All locked inputs matched: `social_media.db`
`a5c0b191f94fa721f752bf9d89d63af56f79aab7a70629347a69719e8681c93b`;
`congestion.json` `ddc9d746600dbdfc60b76c54537662e19c758cbfb9d7a478a71b7bf90cd727a6`;
`fec/legislators.csv` `c5a6cbdbaae0bb19faa89852c29922809ececc70b97c149b4709588087e5e391`;
the 18-domain lexicon `6966ab49de88da5fc4e2405b1f20bcca48a7f378d08777cd249558b677aebd70`;
and stopped criterion `eb16cde3c160f7fc14280a3c6b0ae4754a913606fcd2e78fa7a4fd1c8dea8e12`.

The criterion cleared **PRIMARY_250** without invoking the guarded lower floor: total 279 (House
193, Senate 86); full INTERVIEW-vs-CREC r=.1520279096; Spearman-Brown=.2639309487; added-member
n=81 with cross-source r=.0998588003; stopped-core overlap n=198 with recovered-vs-stopped
r=.9934574724. Every primary readiness bar passes. The artifact records zero production consumers
and has not opened, imported, or named either panel. Exactly one frozen O look is now licensed.

## RESULT-O-RECOVERY (2026-07-16 -- ONE LOOK CONSUMED)

Result artifact: `big5_o_coverage_result.json.candidate`, SHA-256
`fd0b244fc9639f3d76f5cfc791632331a815544b4e889de1ccc7676c45d2c77f`. Exact 9,999-permutation
look; production consumers 0. The route records `DUAL_PANEL_SUCCESSOR_MISS` and is permanently
closed on these inputs.

- Academic experts (n=49): candidate O r=.4020680445, p=.0021, partial=.1337394103. The r, p,
  partial, and n bars pass, but strict dominance fails because candidate correlation with academic
  C is .4746686977. Panel result: MISS. Same-roster preserved original O was stronger and passed
  this panel (r=.5033871803, p=.0002, partial=.2515260818, dominant).
- Senate insiders (n=44): candidate O r=.1839780589, p=.1131, partial=.0227006037. It fails r, p,
  partial, and dominance (max absolute heterotrait=.2540925077 with E). Panel result: MISS.
  Same-roster preserved original O had r=.2246642561 and p=.0698 with dominance, but still failed
  its partial bar at .0695958563.

The experiment solved the coverage problem at 279 members without lowering the floor, but the
added cross-context criterion did not create a stable dual-panel O construct. Per the locked
consequences, O keeps its original one-panel association-supported status; no score, profile,
status, C finding, engine input, or production artifact changes.
