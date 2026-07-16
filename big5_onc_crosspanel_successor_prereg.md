# O/N/C Cross-Panel Successor — New Behavioral Criteria

**STATUS: LOCKED 2026-07-16.** User-authorized successor: "E and A are fine ... try again with
the new criteria, Test-Drive Design ... keep a copy of what was originally held." The original
score artifact and the original gold are copied byte-for-byte under
`originals/big5_onc_20260716/`; neither may be overwritten. This study may write only `.candidate`
artifacts and may not alter E, A, any engine input, or any shipped member profile.

This is a genuinely new-criterion successor, not a reopening of the closed channel-weight spaces
in the O reliability and N variant-parity rounds. No old channel weight is optimized. The three
new behavioral criteria are constructed without importing, opening, naming, or otherwise reading
the Senate gold. After the criterion artifact clears its pre-look reliability bars, its SHA-256 is
recorded in a freeze addendum and one dual-panel look is allowed.

## Frozen originals and inputs

- Original `big5_gold_anchored.json` and copied original:
  `2b351af4c8fd077cc7fd10b05001a2843f850a3a83f956d5ac75b644a4317c13`
- Original `big5_senate_expert_gold.json` and copied original:
  `ff5a948361f478cf7d7da2ce84e333594b242cb65574760dd285a8dbd57afe7a`
- `social_media.db`: `a5c0b191f94fa721f752bf9d89d63af56f79aab7a70629347a69719e8681c93b`
- `behavior_panel.json`: `93d695cde6470f500f3aaac7db61d988b9c3c2ddee66360d568f965c97072ceb`
- `lep_criterion.json`: `10bf14924cfcc2f13ad08dd90fa3539561e1b47b39722345f319766a277c61fc`
- `congestion.json`: `ddc9d746600dbdfc60b76c54537662e19c758cbfb9d7a478a71b7bf90cd727a6`
- `fec/legislators.csv`: `c5a6cbdbaae0bb19faa89852c29922809ececc70b97c149b4709588087e5e391`
- Policy-domain lexicon: `b5_onc_policy_domains.json`, committed with this lock. It must contain
  exactly 18 sorted domains; no term may be added, removed, or reweighted after this lock.

Any fingerprint mismatch stops before a criterion build or gold look. The SQLite databases open
in URI read-only mode. Input row order is never a degree of freedom.

## New criteria — fixed before construction

### O: cross-context information breadth

Use only `social_media.db.speeches` rows whose source is `INTERVIEW` or `CREC`. Group rows by
member/source/package. Within each group retain the first 250 regex tokens. For each member/source,
select at most 200 packages by ascending SHA-256 of `member + NUL + source + NUL + package`; this
prevents volume and date from selecting the corpus. A source is eligible at >=10 packages, >=2,000
retained tokens, >=50 lexicon hits, and >=4 hit domains.

For each eligible source compute normalized Shannon entropy over the 18 domain-hit counts and
MATTR lexical diversity (window 100 tokens). Within chamber, z-score entropy and MATTR separately;
the source score is `.70 * entropy_z + .30 * mattr_z`. O's new criterion is the mean of the
INTERVIEW and CREC source scores and requires both. It is then residualized, without gold, on
intercept + female + Republican + chamber + log selected-token count + log selected-package count,
and z-scored. The two source scores are preserved for reliability.

Pre-look bars: final coverage >=250; at least 30 Senate and 150 House members; cross-source Pearson
r >= .10 and Spearman-Brown reliability >= .18. Failure retires O's new criterion without a gold
look.

### N: unscripted affective lability

Use only `INTERVIEW` rows. Each database row is a member turn; group by member/package and retain
turns with >=10 regex tokens. Eligible packages have >=2 retained turns. A member needs >=4
eligible packages and >=30 retained turns. Turn activation is
`(negative_hits - positive_hits) / sqrt(turn_tokens)`, using the fixed positive and negative
word sets committed as literals in the lock implementation tests. For each package compute the
mean absolute successive activation difference and the 90th-minus-50th percentile activation
spike. Member lability is `.70 * median(package differences) + .30 * median(package spikes)`.

Packages are also assigned to deterministic halves by the low bit of SHA-256(member + NUL +
package); each half must contain >=2 packages. The final raw score and both half scores use the
same formula. The final score is residualized, without gold, on intercept + female + Republican +
chamber + mean activation + mean turn length + log turn count + log package count, then z-scored.

Pre-look bars: final coverage >=150; at least 30 Senate and 100 House members; half-score Pearson
r >= .10 and Spearman-Brown reliability >= .18. Failure retires N's new criterion without a gold
look.

### C: two-mode execution consistency

Use raw `behavior_panel.json` `votes_cast` and `lep_criterion.json` `followthrough`; do not read the
existing `diligence_z`. Require both components. Within chamber, transform votes as `log1p`, then
z-score votes and followthrough separately. The fixed execution-consistency score is
`mean(vote_z, followthrough_z) - .5 * abs(vote_z - followthrough_z)`, algebraically the lower of
the two component z-scores: strong performance in only one mode cannot conceal weak performance in
the other. Residualize, without gold, on intercept + female + Republican + chamber, then z-score.

Pre-look bars: coverage >=350; at least 30 Senate and 250 House members; raw component Pearson
r must be nonnegative. Failure retires C's new criterion without a gold look.

## Candidate construction — no fitted weights

For members present in both the frozen original score and the eligible new criterion, z-score both
over their full-roster intersection and apply these fixed weights:

- O: 70% frozen original + 30% new cross-context information breadth.
- N: 70% frozen original + 30% new unscripted affective lability.
- C: 30% frozen original + 70% new two-mode execution consistency.

The unequal C weight is disclosed a priori: the original C failed the academic panel outright, so
a nominal 30% adjustment cannot be a meaningful test of a new criterion. No alternative weights,
sign flips, subsets, nonlinearities, panel weights, or post-look residualizations are permitted.
Missing new criteria remain missing and never become zero.

## One-look dual-panel gates

Evaluate unweighted, name-resolved members separately in `senate_insiders` and
`academic_experts`. N is the reverse of gold ES. For each trait and panel, all must hold:

1. n >= 30.
2. Pearson r(candidate, own gold) >= +.20.
3. One-sided permutation p < .10, K=9,999; seeds 20260716 + 100*trait index + panel index,
   with traits ordered C,N,O and panels ordered academic_experts,senate_insiders.
4. Strict diagonal dominance: own r > maximum absolute correlation with every other gold trait.
5. Partial r controlling female, Republican, and chamber >= +.10. Covariates are residualized from
   both candidate and gold by ordinary least squares; any rank deficiency or fewer than five 0/1
   observations for a binary covariate aborts before consumption.

A trait validates across both panels only if all ten panel-specific checks pass. No family-level
trade is allowed: O cannot rescue N or C. The artifact must also report the frozen original under
the same roster and tests, but those comparisons are historical context and cannot change the
original statuses.

## TDD and one-look gate

Tests are written and observed failing before implementation. They enforce original hashes,
criteria/gold separation, deterministic sampling, formula monotonicity, residualization,
fixed weights, score missingness, evaluator dominance, candidate-only output names, and refusal
after a newline-anchored `## RESULT-ONC` heading.

Before the look, append only `## CRITERIA FREEZE ADDENDUM` containing the criterion artifact hash,
coverage, reliability statistics, input hash verification, and the implementation commit. The look
script refuses without that addendum, on any mismatch, or if `## RESULT-ONC` already exists.

## Consequences and stopping rule

- PASS for a trait: record `DUAL_PANEL_SUCCESSOR_CANDIDATE_PASS`; nothing ships automatically.
  Promotion still requires a clean full audit and explicit user ratification.
- MISS for a trait: retain its original one-panel status and record the new criterion route closed.
- Criterion pre-look failure: retire that trait's criterion without exposing it to the gold.
- No result may overwrite `big5_gold_anchored.json`, the copied originals, E/A, or any profile.
- One look only. After `## RESULT-ONC`, no tuning or successor variant on these inputs is allowed.
