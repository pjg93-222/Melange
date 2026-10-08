# HALLUCINATION AND ERROR IDENTIFICATION FRAMEWORK - findings analyses

Status: ADOPTED 2026-08-13 by Paul's ruling ("Adopt"), revision 2 as
examined. This framework is in force for findings-analysis documents from
that date; what "in force" does and does not mechanically guarantee is
inventoried honestly in section 7, and the adoption record is section 8.
Originally produced as a draft under Meta LOOP run
run-20260814T0055554676370Z-853ef0994b with draft-only invariants pinned in
the coordination ledger. Revision 2 follows one adversarial critique round
(Grok lane, this run): 6 KILLED and ~20 WOUNDED points adjudicated - 24
repairs accepted and implemented below, 2 points rejected on
cite-correctness (the critic lacked commit access; both disputed quotes are
verbatim commit text), disposition table in the run record. Review receipts
are dated reads (E15): the critique binds nothing and proves nothing beyond
its date.

Scope: findings-analysis documents - the family of analyses written over
the forecast lane and its kin (BARR_CU_COURTSHIP_BATTERY_2026-08-11,
CROSS_INDUSTRY_BACKFIRE_ANALYSIS_2026-08-11, D9_PARTY_STRATIFIED_REFIT_
2026-08-13, and successors). This framework identifies defects in claims.
It does not replace change-control (what may be edited), prereg discipline
(research claims), or the brain's conflict precedence (CONSTRAINTS >
DECISIONS > STATE). Challenges to settled brain entries route through each
entry's recorded Reversal/Would-reconsider condition, never around it.

GROUNDING RULE: every error class here is anchored to at least one instance
that actually occurred in this repository or its brain record, quoted
verbatim with its pointer (section 2). Where the findings family itself has
not yet exhibited a class, the section-2 entry says so explicitly (C5 is
the one case). A framework assembled from hypothetical failure modes would
itself be the kind of unsourced claim it polices.

## 0. Definitions

A claim in a findings document has three legs: the VALUE (the number or
fact asserted), the BASIS (the run, window, denominator, and derivation
that support it), and the WORDING (what the sentence says the value shows -
including its caveats). A defect is a mismatch on any leg.

- HALLUCINATION: the asserted support does not exist as stated -
  unrecoverable derivations, phantom independence, provenance misreads,
  verification-tool artifacts reported as facts.
- ERROR: support exists but is wrong or no longer true - stale figures,
  masked aggregates, caveats that have rotted false, checks that prove
  less than they claim.
- INFIDELITY IS TWO-SIDED: overclaim and overcaveat are both defects, and
  the passes below police both directions. This corpus contains both
  (E1-E6 overclaim; E14 overcaveat).

## 1. The six-pass examination (operating core)

Run all six passes over any findings document, at authoring and again at
review. Each pass names its target classes (section 3) and observed hits
(section 2). Passes 1a and 2 are runnable cold from the document alone;
1b, 3, 4, 5, 6 need the named receipts within reach.

PASS 1 - NUMBERS.
  1a BASIS LINT (cold-runnable): every figure carries its window,
  denominator, and source in the same sentence or an adjacent named
  receipt - a receipt is a file, commit, ledger event, or registry the
  reader can open. A bare percentage on a shipped surface is a defect
  regardless of whether it is true.
  1b RE-DERIVATION (needs receipts): the figure recomputes from the
  source of record - and provenance is read from the source of record,
  never from descriptive fields ("authority and rationale ... describe
  how the CLASS was decided, never where the POSITION came from",
  brain DE-003).
  Disposition rule: receipts REACHABLE and the figure fails to re-derive,
  or receipts recoverably ABSENT - treat the figure as wrong until
  re-measured. Receipts out of THIS session's reach - mark
  UNVERIFIED-HERE and queue; a figure is not demolished because the
  present session cannot reach its receipts. The E7 lesson with its own
  basis: the shipped bill-citation figure was "STALE, NOT IMPRECISE.
  23.29% is exactly the 2023-only rate", against a measured 28.18% =
  9,584/34,011 pooled across 2021-2026 [commit 23affda4b]. [C3, C5;
  hits E7, DE-003]

PASS 2 - WORDS, BOTH DIRECTIONS.
  OVERCLAIM families - each occurrence names its supporting check in its
  sentence or supporting block, or is reworded. Families are matched as
  word families (morphology included); quoted specimens of defects are
  exempt; the lists below are the observed cores, extensible by evidence:
    ABSOLUTES ("ALL", "ANY", "TOTAL", "NO ... ON ANY TEST") - licensed
    only over a closed, enumerated, fully observed set cited in place
    ("All 12 archived models reproduce" [D9:41] is licensed; an absolute
    over an open capability space is not - E1);
    CAUSAL VERBS ("backfire", "causes", "drives") - require
    identification, not association (E4);
    ROBUSTNESS WORDS ("robust", "confirmed", "validated") - require the
    named robustness checks to have actually run (E6);
    INTENT WORDS ("ignore", "refuse", "chose") - require evidence of
    intent; absence of an action is not intent (E3);
    PRESCRIPTIVE PROMOTIONS (an exploratory fit worded as a "rule",
    "screen", or "procedure") - require the prereg class first (E5).
  OVERCAVEAT direction (the E14 counter-class): estimator caveats
  attached to descriptive censuses; a blanket banner importing caveats
  onto enumerations; every caveat must match the object's evidence
  class. Underclaim is also infidelity.
  BANNER COHERENCE: a claim that contradicts the document's own banner is
  catchable from the document alone, no external data needed - a causal
  YES sat 80 lines below the document's own no-causal-claims banner (E4).
  [C1 and the E14 side of C7; hits E1, E3, E4, E5, E6, E14]

PASS 3 - INDEPENDENCE, BY LAYER. For any "N confirmations" or "N lenses
  agree" claim, enumerate three layers: the DATA SUBSTRATE, the
  ESTIMATOR/ROUTE, and the AUTHOR. N reads of one substrate are ONE
  instrument looked at N ways, whatever the estimator count (E2: four
  lenses on the same sponsorship-visible substrate with the same
  seat-mechanical common cause). A distinct-estimator, same-substrate
  replication (D9 S0: 0.000e+00 transcription route, 1.5e-13 independent
  SVD/QR route) is a real COMPUTATION check - it confirms the arithmetic,
  not the measurement. Independence claims about measurement need
  distinct substrates; about computation, distinct routes; about
  judgment, distinct authors (the two-chair form). [C2; hit E2]

PASS 4 - STRATA.
  4a QUOTE HYGIENE: a pooled quantity over a named fault line - party,
  chamber, sector; additions to this list ride evidence, not reviewer
  preference - is quoted with its strata visible, or labeled
  UNSTRATIFIED explicitly. Disposition follows the D9 pattern, not a
  blanket rule: opposite-signed strata whose interaction survives the
  correction DEPRECATE the pooled number ("No member of either stratum
  is described by the pooled number" - E8); same-signed or non-surviving
  strata may stand WITH the split visible.
  4b DESIGN FLOOR for any stratification check: it must be
  interaction-capable - "a main-effect dummy shifts the intercept and
  the align_A slope but cannot absorb a product term or reveal that the
  product term differs by party" [commit 0996be7de] (E9) - and its
  reference cell must be the intended stratum (E16). [C4; hit E8.
  Design floor from C6's E9, E16]

PASS 5 - CAPABILITY OF CHECKS AND NULLS. The decision rule for every
  gate, guard, and null result: WHAT WOULD THIS SAY IF THE CLAIM WERE
  FALSE? If the answer is "the same thing", it is not a gate (E11:
  byte-identical reproduction "proves transcription fidelity, not
  correctness - a bug in that function would have been reproduced
  perfectly and invisibly"). A null names the capability axis it
  exercised - identification, statistical power, or instrument
  visibility: "no test here that was capable of showing one did", never
  "no signal on any test" (E1). "Not significant within a stratum" is
  not "zero within that stratum" (the D9 record: five Republican pairs
  nominally p<.05 all die under Holm at m=12). Extraction fidelity is
  capability too: the checking tool must read the artifact at the
  artifact's own level - line-oriented search over joined string
  literals reported an intact claim destroyed (E13), and a mutation
  harness trusts a FAIL only after verifying the mutation landed.
  [C1, C6; hits E1, E9, E11, E13]

PASS 6 - TIME, WITH NAMED TRIGGERS. Figures re-derive at every
  corpus-growth event that touches their denominator (E7's 2023-only
  rate rode a corpus that grew to 2021-2026). Caveats re-verify whenever
  a check they cite as absent is run, or a fact they describe changes -
  a caveat line "HAD BECOME FALSE" after three of its five named
  absences were filled (E10; current state per CROSS:57-58 - party
  control, Holm, and split-sample run; outlier diagnostics and
  alternative specifications still absent). Hash pins and review
  receipts are dated reads, never live invariants (E15). STATE-class
  claims follow the brain's 7-day verification window. CORRECTION
  PROPAGATION: a correction sweeps every restatement of the corrected
  claim, not just the headline - the prose analogue of the guard test's
  partial-update catch ("three of four are corrected and one is
  forgotten") - see E17 for three live residuals found this run.
  [C3; hits E7, E10, E15, E17]

## 2. The observed error corpus (grounding, verbatim)

Wording corrections, merge 2ababfb48 (Paul-gated, two-chair examination
pilot run-20260812T0109334914983Z-323f3b7afd; no number changed):

- E1 "NO BACKFIRE SIGNAL ON ANY TEST" - twelve single-member descriptive
  tests with no power analysis, no null distribution, and party
  uncontrolled cannot license an absolute over ALL tests. Corrected to
  "NO TEST HERE THAT WAS CAPABLE OF SHOWING A BACKFIRE SIGNAL DID".
  [audits/BARR_CU_COURTSHIP_BATTERY_2026-08-11.md, correction 1]
- E2 "the divergence ... is now TOTAL" - four lenses reading the same
  sponsorship-visible substrate with the same seat-mechanical common
  cause, counted as four independent confirmations. [same doc,
  correction 2]
- E3 "The cleanest single ignore datum" - intent attributed to a
  non-signature; symmetric to the standing rule that attention is not
  evidence of contact, agreement, or a relationship. [same doc,
  correction 3]
- E4 "YES, it can backfire, in two measurable ways" - a causal verb 80
  lines below the document's own no-causal-claims banner (the 80 is the
  correction block's own count, inherited not re-counted). Corrected to
  "TWO PATTERNS ARE MEASURABLE; NEITHER IDENTIFIES BACKFIRE". Both
  examining chairs independently named this the largest overclaim, from
  opposite directions. [audits/CROSS_INDUSTRY_BACKFIRE_ANALYSIS_
  2026-08-11.md, correction 1]
- E5 "The screening rule the data supports" - an exploratory fit with
  party uncontrolled and no multiplicity handling converted into an
  operational decision procedure. [same doc, correction 2]
- E6 "robustly NEGATIVE interactions" - robustness language with no
  robustness check run. As of the 2026-08-12 correction the absent
  checks were named in place (no alternative specification, no party
  control, no outlier diagnostic, no multiplicity correction, no
  split-sample); by 2026-08-13 three of the five had been run and the
  caveat updated again - see E10. [same doc, correction 3; current
  state CROSS:57-58]

Value and aggregation defects:

- E7 The shipped "~23%" bill-citation figure was "STALE, NOT IMPRECISE.
  23.29% is exactly the 2023-only rate" carried forward as the corpus
  grew to 2021-2026; measured pooled rate 28.18% = 9,584/34,011; the
  original derivation was not recovered [commit 23affda4b]. It "sat on
  four user-facing surfaces for months until a coverage diagnostic
  caught it" [commit 2b04eb7fa].
- E8 Three pooled coefficients average OPPOSITE-SIGNED party strata
  (CU->crypto pooled +0.0921 vs D +0.2624 / R -0.0624; bank->crypto
  +0.0849 vs +0.2047 / -0.0549; fintech->crypto +0.0615 vs +0.2538 /
  -0.0562): "No member of either stratum is described by the pooled
  number." [commits 0996be7de, 286f2c8e9; audits/D9_PARTY_STRATIFIED_
  REFIT_2026-08-13.md]
- E9 "a prior refit added party as a MAIN EFFECT and reported the
  interactions survived. That design cannot answer the question ...
  An independent replication found that, not the author." [verbatim
  from commit 0996be7de] The design flaw was found by reasoning about
  the design in an independent replication round - the replication's
  different solver and join route (D9 S0) verified computation, and is
  not what surfaced the design hole.

Verification and record defects:

- E10 "The finding-2 caveat line was updated because it HAD BECOME
  FALSE" [commit message wording, 286f2c8e9] - the caveat said no party
  control, no multiplicity correction and no split-sample had been run,
  after all three had. Caveats rot like values do.
- E11 The D9 reproduction gate "was described as establishing that
  'downstream is trustworthy.' Byte-identical transcription of the
  archived ols() proves transcription fidelity, not correctness - a bug
  in that function would have been reproduced perfectly and invisibly."
  [audits/D9_PARTY_STRATIFIED_REFIT_2026-08-13.md:132-135]
- E12 "A coherence gap in the decision rule, flagged by the analyst and
  followed anyway." [same doc:123]
- E13 "A grep for the shipped selection claim reported it destroyed when
  it was intact" - the notes are implicit multi-line string
  concatenations, so line-oriented search gives false answers; the
  mutation harness itself hit the same trap (mutations silently not
  applying) and now asserts at the JOINED level that a mutation landed
  before trusting a pass. [commit 2b04eb7fa]
- E14 OVERCAVEAT (the counter-class): "Findings 1 and 4 are NOT
  exploratory associations and the blanket status banner above
  over-caveats them" - descriptive censuses over a fully observed
  population were wearing estimator caveats; E2's enumeration needs
  "the completeness and denominator caveats and nothing else".
  [both correction blocks, merge 2ababfb48]
- E15 "That pin was ALREADY stale before this correction ... it records
  what the critic read on 2026-08-11 and is not a live invariant."
  [BARR correction block, re audits/barr_courtship_2026-08-11/
  grok_critique_D1.md:22]
- E16 REFERENCE CELL: the D9 S2 coding used "only a Republican dummy, so
  its reference cell is Democrats UNION Independents (n=262), not
  Democrats (n=259); the three-way term tests R vs (D+I), not R vs D."
  Immaterial there (a D+R-only refit agrees on all 12 Holm decisions)
  and recorded rather than absorbed. [audits/D9_PARTY_STRATIFIED_REFIT_
  2026-08-13.md:118-119]
- E17 CORRECTION PROPAGATION (found this run, adversarial critique
  round; disposition of the residuals is Paul's): after the 2026-08-12
  corrections, restatements of the corrected claims survive in the
  interiors - CROSS:90 "### 2. The backfire signature exists and is
  DIRECTIONAL (crypto fault line)"; CROSS:93 "The interaction term is
  the backfire test."; BARR:72 "~zero). NO BACKFIRE." A correction that
  fixes the headline and misses the restatements is the partial update
  the coverage guard was built to catch, in prose.

Brain anchors (settled entries; challenge only via their recorded
reversal conditions):

- DE-001 mention-density relevance: a breadth artifact produced 0.75
  where the evidence supports 0.30 (both values from the entry) - "a
  bill that defines 'insured depository institution' by enumerating
  every charter type names credit unions dozens of times without being
  about them." Term counts survive only as a NEGATIVE screen.
- DE-002 the class-bias hypothesis, measured and refuted with a
  pre-registered concentration measure: 11 anchors held by 109 of 533
  members, only 11.1 percent of role-credit landing inside the Tier 1/2
  band (figures from the entry) - the counterexample to fixing by
  anecdote.
- DE-003 provenance misread: reading a tag row's authority/rationale
  fields as position provenance produced a false finding that four of
  five ACU SUPPORT flags were model-signed (per the entry). Those
  fields describe how the CLASS was decided, never where the POSITION
  came from.
- D-005 proximity repricing: fixing acts one at a time in response to
  whichever member was last investigated "selects fixes by proximity
  and turns the board into a record of what was examined."

## 3. Taxonomy

- C1 CLAIM-EVIDENCE GAP - the wording asserts more than the run
  performed. Instances E1, E3, E4, E5, E6. Detected by PASS 2
  (including the promotions family for E5) and PASS 5. Tooth:
  procedural now, lint candidate (section 7).
- C2 PHANTOM INDEPENDENCE - correlated reads counted as replications.
  Instance E2. Detected by PASS 3's three-layer enumeration. Tooth:
  procedural.
- C3 STALENESS AND ROT - a value, caveat, pin, state, or corrected
  claim's restatement that was true once and silently stopped being
  true. Instances E7, E10, E15, E17. Detected by PASS 1a and PASS 6;
  guard tests where built. Tooth: MECHANICAL for the guarded value
  class only (E7's guard exists; E10/E15/E17 have none yet).
- C4 AGGREGATION MASKING - a pooled number or proxy that describes no
  underlying case. Instance E8; sibling DE-001 (an invalid proxy is
  masking by construction). Detected by PASS 4a. Tooth: procedural
  standard (the D9 disposition pattern).
- C5 PROVENANCE FAILURE - support unrecoverable or read from the wrong
  field. Instances: E7's unrecovered derivation and brain DE-003 -
  both from the wider repo/brain record; the three findings documents
  themselves have not yet exhibited this class, stated here per the
  grounding rule. Detected by PASS 1b. Tooth: MECHANICAL for ledger
  facts (orphan facts rejected at insert - exercised five times in
  this framework's own production run); procedural for documents.
- C6 FALSE ASSURANCE - a verification that proves less than it claims.
  Instances E9, E11, E13, E16; also the unregistered-suite trap ("a
  suite no runner invokes is indistinguishable from a deleted one",
  commit 2b04eb7fa). The PASS 5 question is the detector. Tooth:
  MECHANICAL for E13-class suite hygiene (mutation testing, runner
  registration); procedural for design-level assurance (E9, E11, E16).
- C7 SELECTION AND PRESENTATION - defects in how findings are produced,
  corrected, or shown: proximity fixes (D-005), flagged-and-followed
  (E12), overcaveat (E14), and unstable small-denominator presentation -
  the rule is the recorded presentation limit (a ZERO numerator can be
  presentable where the 0/15 RATE is not, until denominators carry
  eligible/active/unscored flags), and the corpus's own positive
  exemplar is BARR:155 "(3/32). Payments (+1668%, 1/7) is a
  SINGLE-SIGNATURE cell - unstable," where the label travels with the
  rate. Tooth: procedural, Paul-gated.

## 4. Detection battery beyond the six passes

- TWO-CHAIR EXAMINATION - two reviewers from different disciplines
  examine the same document independently. In the one pilot run to date
  (run-20260812T0109334914983Z-323f3b7afd), convergence from opposite
  directions marked the largest defect (E4); treat convergence as a
  priority signal, not a proven law. Single-chair adversarial review
  (Grok lane) with per-point exact locations is the lighter form;
  cite-correctness of the critique is itself adjudicated before any
  point is accepted (two of ~26 points in this document's own round
  failed cite-correctness on commit provenance).
- INDEPENDENT REPLICATION - for any quantity feeding a decision:
  independent of the AUTHOR above all (E9's design hole was found by a
  replication round, not the author); a different solver and join route
  (D9 S0: 0.000e+00 and 1.5e-13) additionally verifies the computation
  layer.
- GUARD TESTS, MUTATION-TESTED - assert internal consistency plus
  not-the-known-stale-value; never hardcode the live value: "pinning 28
  would require editing this test every time the corpus grows - which
  would recreate the staleness it exists to catch" [commit 2b04eb7fa].
  A guard is trusted only after it FAILED on each planted defect, with
  the harness verifying each mutation actually landed (E13). Register
  the suite in the runner. The one built exemplar,
  fec/tests/lobbying/test_coverage_claim_text.py, guards E7's
  regression (the not-23% assertion and cross-surface consistency)
  through E13's lesson (AST joined-literal extraction).
- PRE-REGISTERED CLASS RULES - before repricing or refitting instances,
  fix the decision rule and its deciding measure in advance (DE-002's
  concentration measure refuted the bias hypothesis before the
  counterfactual could argue for it; D-005 is the anti-pattern).
- CORRECTION OF RECORD pattern - dated, Paul-gated block at the top of
  the corrected document: quotes the prior wording verbatim, states NO
  NUMBER CHANGED when true, names what was examined and NOT corrected,
  preserves the record append-only (supersession, never deletion - the
  brain's own rule), and - per E17 - closes with a PROPAGATION SWEEP
  enumerating every restatement of the corrected claim. The corrector's
  own defects are recorded in the corrector's own document (D9
  precedent), never absorbed.

## 5. Severity and disposition

- S1 wrong VALUE on a user-facing surface (E7): correct first, then add
  a regression guard on the exact defect.
- S2 masked quantity (E8): quote only with strata visible; DEPRECATE the
  pooled statement where strata are opposite-signed and the interaction
  survives correction (the E8 three); same-signed or non-surviving
  pools stand with the split - the D9 disposition (3 deprecated, 9
  stand, 3 coherence-gap pools stand with split visible).
- S3 wording exceeding evidence (E1-E6): CORRECTION OF RECORD, with the
  E17 propagation sweep.
- S4 caveat defects, both directions (E10 rot, E14 overcaveat): the
  caveat is re-derived like a number.
- S5 receipt and pin hygiene (E15): annotate as dated reads; never
  retro-edit or delete.
All dispositions are Paul-gated. A wording fix never alters a number
silently; a number fix never rewrites wording beyond its basis clause.

## 6. Anti-patterns (the framework misused)

- Overcaveating descriptive censuses as safety theater (E14) -
  underclaim is also infidelity, and PASS 2 runs in both directions.
- Demolishing sound numbers a session merely cannot reach receipts for -
  PASS 1's disposition rule exists exactly to prevent this.
- Hardcoding live values into guards - builds the next staleness.
- Reading "not significant within a stratum" as "zero within it".
- Trusting a guard that has never failed, or a mutation never verified
  to have landed (E13).
- Weakening a test, floor, or count to make a change pass (standing
  Never-do; change-control law).
- Fixing instances by proximity to the last thing examined (D-005).
- Treating review receipts or sha256 pins as live invariants (E15) -
  including this document's own critique round.
- Demanding endless strata: fault-line additions ride evidence
  (PASS 4a), not reviewer preference.
- Citing adoption instead of examining - only the two mechanical teeth in
  section 7 catch anything without a person running the pass. A document
  is not examined because this framework exists.
- Hiding the corrector's own defects - record them where they happened
  (D9 precedent; E16 is the worked example).

## 7. Teeth: an honest inventory

MECHANICAL TEETH - these catch a defect with no examiner present:
- fec/tests/lobbying/test_coverage_claim_text.py - registered in
  fec/tests/run_tests.py, mutation-tested, guarding E7's regression via
  E13's extraction lesson [commit 2b04eb7fa].
- Coordination-ledger fact gating - a fact event without claim +
  provenance is rejected at insert (exercised five times producing this
  document's census).
- fec/tests/docs/test_findings_causal_claims.py - causal-claims lint over
  banner-gated findings documents: five detector patterns over JOINED
  blocks with structural exemptions, a 22-fixture answer key carrying the
  corpus's actual historical defects in both directions (every exemption
  test bears a live trigger, so a deleted exemption fails its own test),
  registered in the kernel runner; adversarially reviewed and
  negative-controlled at build (2026-08-13).

DATED RECORDS - support audits, never gates: sha256 pins and review
receipts date what was read (E15).

IN FORCE BY ADOPTION (2026-08-13) - procedural, and therefore only as
live as the examiner who runs them: the six passes, the grounding rule,
the severity ladder, the CORRECTION OF RECORD pattern with its
propagation sweep, and pre-registered class rules (D-005/DE-002). The
section-4 battery is invoked by its own triggers, not on every document:
independent replication for any quantity feeding a decision; two-chair
examination for high-stakes documents, one pilot to date and resource-
gated by Paul.

CANDIDATES - Paul selected all three on 2026-08-13; all landed the same
day:
  (a) BUILT NARROW as the causal-claims lint above. The ABSOLUTES,
      ROBUSTNESS, INTENT and PROMOTIONS families stay manual per the
      feasibility census: ~88% naive false positives on 34 adjudicated
      samples, and licensed vs defective absolutes share one surface form
      no lexical tool can separate.
  (b) BUILT: brain skill skills/examine-a-findings-document.md - the six
      passes and the correction procedure as a cold-runnable checklist.
  (c) BUILT: brain CONSTRAINTS "Claims" group - the basis-clause rule and
      the pooled-with-split rule, each with its source.
A rule with no tooth is a hope; this section is the inventory of which
is which.

## 8. Adoption record

ADOPTED 2026-08-13 by Paul, on the draft as examined (one adversarial
round, 24 repairs accepted, 2 points rejected on cite-correctness).
Settled at adoption:
  - This document is in force for findings-analysis documents, under the
    honest teeth inventory of section 7.
  - The E17 residuals were swept and repaired the same day under the
    framework's own S3 disposition, Paul ruling "do what is most
    optimal"; each repair is recorded in a dated amendment block in the
    document it corrects, with no number changed.
  - The brain carries the adoption as a DECISIONS entry and the
    headline-only-correction failure as a DEADENDS entry.
STILL OPEN, deliberately:
  - Merge to main. This document was committed on its own branch; the
    live tree carries another lane's uncommitted work, and entering it
    mid-lane is a recorded hazard.