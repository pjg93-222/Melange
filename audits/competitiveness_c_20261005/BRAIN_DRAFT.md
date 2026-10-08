# Brain update draft: competitiveness multiplier (for Paul to apply via brainctl)

## DECISIONS.md, new entry (provisional key D-PENDING-COMPET)

### D-PENDING-COMPET: Cook PVI election-competitiveness multiplier on the money curves
- Date: 2026-10-05
- Status: ACTIVE (code landed uncommitted, dial OFF; candidate promotion pending Paul)
- Decision (Paul's rulings, 2026-10-05):
  - Hypothesis: money given to members in competitive races buys more future reciprocity, so dollars to those members count more.
  - lean = Cook PVI signed points x (+1 if the incumbent is R, -1 if D); c = 1 + 1.0 * exp(-max(lean, 0) / 5), in (1, 2].
  - Engine integration as effective dollars on both sides: a uses c*cu and b uses c*ind inside the money curve. The same c applies in shift_lean, lt_priming, per_topic_flip, the dashboard JS and desk ROI. The per-member $10k cap and the pot stay in real dollars.
  - budget_frontier: c replaces the Ballotpedia lev factor when the dial is on.
  - House: Cook 2026 district PVI, joined by Cook's incumbent placement first and district number as fallback.
  - Senate: Paul-supplied state PVI, applied to all senators regardless of 2026 class.
  - Open seats and retirees: boosted, flagged.
  - c = 1 with a flag for: Kiley (unoriented independent), the PR delegate, and Calvert and Doggett (whose district-number row is held by another incumbent).
  - Dial COMPET_MULT, default off; COMPET_SRC names the artifact. Artifact: data/money/competitiveness_c.json(.candidate). Builder: fec/engine/build_competitiveness.py.
- Rationale: the effective-dollar form leaves the money ceiling WM*pm unchanged. It therefore leaves the locked receptivity clip [0.50, 1.60] and the calibrated money/peer split alone, and does not duplicate incent_mult. Applying c to both sides keeps equal money at 50/50.
- Interactions: c is the third competitiveness channel, after incent_mult and the prospect-theory loss test. It amplifies the imputed median industry money (D-071/D-051 R2). D-070 is unchanged, and the certificate holds on current data. D-072: eff_value and gap are unchanged; ROI includes c when the dial is on. RA_SCORE ranks do not move in either dial state.
- Caveat: 1.0 and 5 are Paul's judgment constants, uncalibrated against outcomes. Reciprocity is NOT validated, and no claim may say otherwise without a prereg.
- Reversal condition: Paul retires the dial, or an outcome test (a prereg on whether money given in close races predicts later alignment) fails.

## STATE.md, Current position bullet
- COMPETITIVENESS MULTIPLIER (2026-10-05/06): code in the live tree, UNCOMMITTED, dial COMPET_MULT off.
  - Dial-off engine outputs are byte-identical to baseline (6/6).
  - Kernel tests: 273 passed / 1 failed (pre-existing test_publication_crown_guard). Lane pytest: 76 passed.
  - Candidate (dial on, in data/system/compet_candidate/): ranks unchanged, pot $2.5M conserved, certificate valid, no conversions; 134 members' allocations move.
  - PENDING: dial-off full chain, rank_delta, audit_full and the bundle/desk compare. These were blocked because Excel was open (PID 10588).
  - Then: the candidate bundle/desk, promotion of the .candidate artifact (Paul), and the commit (Paul).

## Open questions (STATE)
- Whether to promote competitiveness_c.json.candidate and turn COMPET_MULT on in production (Paul).
- The prereg design to test the reciprocity hypothesis (Paul).
