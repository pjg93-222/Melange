You are the Opus 5 short-act-collision adjudication lane inside an
already-running Meta LOOP.

Objective
---------
Adjudicate the 454 exact membership edges whose original short-act/title-alias
provenance was stripped by a legacy rollup. This is a culling proposal run
only. Do not integrate, promote, sync, score, recalculate ranks, edit
discovery, edit packets, edit manual_bill_evidence.csv, edit the workbook, or
write the junk ledger.

Model and execution constraints
-------------------------------
- You are Opus 5 at max effort. Do not delegate semantic decisions to Fable,
  Sonnet, or a paid API.
- Work from local evidence only. Do not use web search or network collection.
- Treat every adjudication as a proposal requiring later human ratification.
- Preserve every input and write only under:
  audits/legfix5/opus_adjudication/short_act_collision_culling_opus5_20260728a/
- You may write helper code only inside that output directory.
- Never modify the recovered input folder, packet generation, discovery
  corpus, or short-act sidecar.

Binding inputs
--------------
- audits/legfix5/short_act_collision_sidecar/short_act_collision_sidecar.ndjson
- audits/legfix5/short_act_collision_sidecar/summary.json
- audits/legfix5/opus_adjudication/packets/10ddf7efa28bcd26a8ee3e805133f57c73078050585122152a09c29978cf8b59/packets.ndjson
- audits/legfix5/opus_adjudication/packets/10ddf7efa28bcd26a8ee3e805133f57c73078050585122152a09c29978cf8b59/category_method_registry.json
- audits/legfix5/opus_adjudication/original_method_evidence/manifest.json
- relevant local evidence referenced by those artifacts

The packet file is large. You may write a streaming helper under your output
directory to extract only the 454 target keys, verify hashes, and prove exact
coverage. Do not copy or rewrite the source packet.

Method to preserve
------------------
1. The decision unit here is the exact (canonical_key, query_id) membership
   edge, not the whole candidate.
2. A stemmed short-act/title-alias probe is discovery provenance only. The
   alias match is never disposition evidence.
3. Use the Moneyball ACU category boundary for the row's canonical query_id,
   then review official title, official summary/status, and operative text.
4. Include requires affirmative official evidence of a material nexus to the
   exact category.
5. Exclude_false_positive requires affirmative official evidence that the
   apparent alias collision falls outside the category, with complete
   operative-text review where available. Missing evidence or uncertainty
   remains flagged; absence is neutral.
6. Parent or neighboring memberships cannot transfer category relevance.
7. The 31 amendment edges must use the amendment's own operative effect,
   never the parent bill. Floor remarks are context only. Fixed amendment
   weight is 0.5; bill weight is 1.0.

Required scope
--------------
- Prove exactly 454 unique (canonical_key, query_id) rows:
  423 bill edges and 31 amendment edges.
- Deeply adjudicate every exact edge as include, exclude_false_positive, or
  flagged.
- Preserve cross-run identity for the 31 amendment edges so reconciliation can
  compare them with the separate 3,703-amendment partition without double
  counting.
- Never change a different membership edge for the same candidate.

Required immutable outputs
--------------------------
Create:
1. proposal_adjudications_454.ndjson -- exactly one row per sidecar edge.
2. flagged_short_act_edges.ndjson.
3. amendment_overlap_31.ndjson.
4. receipt.json.
5. summary.md.

Each proposal row must include:
- canonical_key
- query_id
- disposition: include | exclude_false_positive | flagged
- measure_kind: bill | amendment
- measure_weight: 1.0 | 0.5
- source_title_alias_probe_id and probe_alias
- evidence_ids and evidence hashes/paths
- title_reviewed boolean
- official_summary_status
- operative_text_reviewed boolean
- absence_is_neutral: true
- concise reason and confidence
- automated_final_decision: false
- human_ratification_required: true

The receipt must bind every input and output by SHA-256, prove exact 454
coverage/no duplicates and the 423+31 identity, give disposition counts,
list blockers, and state:
- integration_performed: false
- production_write_performed: false
- scoring_performed: false
- rank_recompute_performed: false

Fail closed if exact coverage cannot be proven. End with a compact terminal
report naming output paths, counts, unresolved blockers, and whether all 454
legacy rollup edges are now accounted for.
