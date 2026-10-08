You are the Opus 5 adjudication lane inside an already-running Meta LOOP.

Objective
---------
Complete the amendment-culling adjudication using the original method recovered
from the attached/input work folder. This is an adjudication and culling
proposal run only. Do not integrate, promote, sync, score, recalculate ranks,
edit the discovery corpus, edit manual_bill_evidence.csv, edit the workbook, or
write the junk ledger.

Model and execution constraints
-------------------------------
- You are Opus 5 at max effort. Do not delegate semantic decisions to Fable,
  Sonnet, or a paid API.
- Work from local evidence only. Do not use web search or network collection.
- Treat all output as proposals requiring later human ratification.
- Preserve every input and write only under:
  audits/legfix5/opus_adjudication/amendment_culling_opus5_20260728a/
- You may write helper code only inside that same output directory.
- Never modify files in the recovered input folder.

Binding original-method inputs
------------------------------
Recovered input root:
C:/Users/pgoff/AppData/Local/Temp/claude/cxwt-acu-registry/

Read these first:
- fec/build_amendment_review_queue.py
- fec/adjudicate_amendment_queue.py
- fec/decide_amendment_domain.py
- audits_out/amendments/amendment_review_queue.ndjson
- audits_out/amendments/amendment_adjudicated.ndjson
- audits_out/amendments/amendment_content_v2.ndjson

Also use the frozen, hash-bound evidence already copied into the live workspace:
- audits/legfix5/opus_adjudication/original_method_evidence/manifest.json
- its referenced amendment text, floor-remark, press, letter, metadata, and
  manual-evidence artifacts
- audits/legfix5/short_act_collision_sidecar/

Method to preserve
------------------
1. Adjudicate the amendment's own ultimate policy effect. Parent bill subject,
   roles, or relevance never transfer domain or direction to the amendment.
2. A direct, operative amendment-text connection to one or more of the 19 ACU
   categories is the primary domain basis.
3. Floor remarks are sponsor intent/context only. They do not substitute for
   operative text and do not create sponsor/cosponsor roles.
4. Press can establish direction only when the evidence directly identifies
   the exact amendment and clearly states ACU's position. Press absence is
   neutral.
5. Letters remain a separate corroborative/role surface. Letter lead/signatory
   is never bill or amendment sponsorship.
6. For the final direction, the only substantive question is whether the
   amendment is ultimately positive or negative for the category. Record +1 or
   -1. The fixed amendment scoring weight is separately 0.5.
7. Missing amendment text cannot support an absence-based exclusion. If direct
   amendment-specific official/press evidence cannot resolve it, flag it.
8. Never turn uncertainty into exclusion.

Required scope
--------------
- Deeply adjudicate all 419 rows in amendment_review_queue.ndjson.
- Reconcile those decisions against all 3,703 amendments in
  amendment_content_v2.ndjson so every amendment has exactly one accounting
  state: include, exclude_false_positive, or flagged.
- Validate or overturn the prior 160-in / 3,543-out original-method partition
  based on the above rules. Do not merely copy it.
- Preserve the 679 unavailable-text cases as a distinct audited subset.

Required immutable outputs
--------------------------
Create:
1. proposal_adjudications_419.ndjson — exactly one row per review-queue key.
2. amendment_partition_3703.ndjson — exactly one row per amendment key.
3. flagged_amendments.ndjson.
4. receipt.json.
5. summary.md.

Each proposal row must include:
- canonical_key
- disposition: include | exclude_false_positive | flagged
- category_ids (zero or more of the 19 canonical category IDs)
- ultimate_direction: 1 | -1 | null
- amendment_weight: 0.5
- evidence_ids and evidence hashes/paths
- a concise reason and confidence
- text_available boolean
- floor_evidence_used boolean
- press_evidence_used boolean
- parent_context_used boolean
- parent_relevance_transferred: false
- automated_final_decision: false
- human_ratification_required: true

The receipt must bind every input and output by SHA-256, prove exact key
coverage/no duplicates, give all count identities, list blockers, and state:
- integration_performed: false
- production_write_performed: false
- scoring_performed: false
- rank_recompute_performed: false

Fail closed if exact 419 and 3,703 coverage cannot be proven. End with a compact
terminal report naming output paths, counts, unresolved blockers, and whether
the original 160/3,543 partition survived review.
