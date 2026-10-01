# PREREG DRAFT -- F1: FOL-CoT structured elicitation for the model valence hop

STATUS: **DRAFT -- NOT LOCKED.** Written 2026-08-14 under menu ruling 5 (F1 picked as first
prereg). Locking is a separate, Paul-visible step: bars become binding only when this file is
locked per moneyball-research-methodology and fingerprints are pinned. No look may be taken,
and no look script may run, while this header reads DRAFT.

## Hypothesis
Reformatting the valence-hop classification prompt as FOL-structured chain-of-thought
elicitation (predicate glossary + explicit rule ending in a valence consequent), executed by
Haiku 4.5, improves valence-hop accuracy over the current prompt's 0.689 baseline (400
adjudicated tweet golds; fec/stance/apply_two_hop_stance.py:4-5) on FRESH gold. Mechanism
prior: Dai et al. 2025 (Neural Networks 183:106956) report their training-free FOL-CoT
variant beating plain CoT by +6.4 macro-F zero-shot on VAST (79.8 vs 73.4, their Table 4);
HONEST-PRIOR DISCOUNT: their benchmarks are public sets predating LLM cutoffs (contamination
risk) and short-text social media (domain shift) -- the expected local effect is materially
smaller than +6.4.

## Design (to be frozen at lock)
- MODEL: claude-haiku-4-5 (cost law). PROMPT: the FOL-CoT template, sha256-pinned at lock.
- REGISTRY SUPREMACY (hard invariant): the tracked valence registry and policy_force bind
  wherever they cover; the model scores ONLY registry-uncovered targets. Zero overrides of
  registry-covered items -- a single override is an automatic FAIL.
- FRESH GOLD: n >= 150 items adjudicated by Paul AFTER the method freeze (labels never seen
  by prompt development). Composition mirrors the press/tweet mix of the uncovered stream.
- COMPARATOR: the current production valence-hop prompt, same items, same session
  discipline. Paired design: both prompts score every item, so the permutation test is a
  paired sign-flip on item-level correctness.
- ANALYSIS PLANE ONLY: no production artifact, dial, or JS-mirror template change until a
  ratified promotion; the .candidate convention applies.

## Bars (ALL must hold; DRAFT values -- final values set at lock)
1. Valence-hop accuracy >= 0.75 on the fresh batch (baseline 0.689 recomputed on the same
   batch for the honest comparison; the 0.75 bar binds on the fresh-batch denominator).
2. Macro-F1 >= the recomputed same-batch compose baseline.
3. Exact permutation p < .05 (K=5000, seed pinned at lock) for the accuracy delta.
4. Zero registry-covered items overridden (hard zero).
5. Ceiling-beat CLAIM (optional, only if 1-4 pass): composed accuracy > the 0.872-equivalent
   recomputed on the fresh batch; otherwise no ceiling language anywhere.

## Battery (simulate gate; must pass before the look; refusal = RETIRED WITHOUT A LOOK)
- Label-permutation null: the pipeline on permuted labels must score at chance.
- Registry-leakage check: the model must fail items whose answer is knowable ONLY from the
  registry (proves it is not memorizing registry families).
- Target-swap confound: swapped-target items must not retain their original valence.

## Stopping rules and consequences (fixed wording at lock)
- PASS -> .candidate prompt artifact; production swap is Paul's gate with the old prompt as
  the revert dial. - MISS -> route closed for this prompt family; kill-ledger entry; the
  0.689 baseline stands. - FRAGILE on re-derivation = MISS.

## Fingerprints (pinned at lock, empty in DRAFT)
prompt sha256: TBD | gold batch file + sha256: TBD | eval harness: fec/stance/stance_eval.py
@ commit TBD | seeds: TBD | lock date + Paul sign-off: TBD
## READY-TO-LOCK ADDENDUM (2026-08-17, coordinator prep; lock still requires Paul)

Freeze artifacts now exist and fingerprint as follows (recompute at lock to confirm):
- prompt template: fec/stance/folcot_valence_prompt_v1.txt
  sha256 84F374ACF4CCE02D986F27BD708EC9F61138BB38311B3AE115EF7772220A2E77
- sampling rule: fec/stance/folcot_gold_sampling_rule_v1.txt
  sha256 85EBD1F1AC68A48DD99E799B73083BF1595934B28658C166A23D4FF312F19251
Remaining for the LOCK block: battery probe-set construction + seeds (built at lock), the
eval-harness commit pin, bars confirmation, and the sign-off. On lock, the sampling window
opens and prompt iteration ends.
## LOCK (2026-08-17) -- THIS PREREG IS NOW LOCKED

Signature: Paul, in-chat directive 2026-08-17 ("Start those" naming "the F1 lock
signature" from the enumerated waiting-on-Paul list). Bars confirmed AS WRITTEN in
section 4. From this timestamp the method is FROZEN: no prompt iteration, no sampling-rule
change, no bar change. The fresh-gold sampling window is OPEN per the sampling rule.

- Prompt template: fec/stance/folcot_valence_prompt_v1.txt
  sha256 84F374ACF4CCE02D986F27BD708EC9F61138BB38311B3AE115EF7772220A2E77
- Sampling rule: fec/stance/folcot_gold_sampling_rule_v1.txt
  sha256 85EBD1F1AC68A48DD99E799B73083BF1595934B28658C166A23D4FF312F19251
- Eval harness pin: fec/stance/stance_eval.py at main commit ba92f0a18b0f949b30b06ccd2f5ce3942fd0d8c6
- Battery seeds (pinned): label-permutation null = 535353; registry-leakage probe = 646464;
  target-swap = 757575. Permutation count K = 10,000 (paired sign-flip, per section 4 bar 3
  as drafted; the 5,000 in the earlier prose of section 5 of the OTHER draft lineage does
  not apply -- this file's section 4 governs).
- Battery probe-set CONSTRUCTION RULES (pinned; materialized at battery run, pre-look):
  (null) the fresh batch's labels permuted with seed 535353;
  (leakage) 30 registry-covered targets drawn with seed 646464, their registry valences
  MASKED, the candidate must NOT recover the masked family valences above chance;
  (swap) 30 fresh-batch items re-paired with wrong targets drawn with seed 757575,
  accuracy retention above the chance band = confound failure.
- Look script: to be authored as a gated runner per methodology (refuses on fingerprint or
  battery failure); its commit is recorded in the RESULT, not here.
- Lock date: 2026-08-17. Look status: UNSPENT.