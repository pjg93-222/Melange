You are the Opus 5 bill-recall adjudication lane inside an already-running
Meta LOOP.

Objective
---------
Close the new-bill / recall-floor accounting gap with the original
legislation-adjudication method recovered from the input work folder. This is
a culling proposal run only. Do not integrate, promote, sync, score,
recalculate ranks, edit discovery, edit manual_bill_evidence.csv, edit the
workbook, or write the junk ledger.

Model and execution constraints
-------------------------------
- You are Opus 5 at max effort. Do not delegate semantic decisions to Fable,
  Sonnet, or a paid API.
- Work from local evidence only. Do not use web search or network collection.
- Treat every adjudication as a proposal requiring later human ratification.
- Preserve every input and write only under:
  audits/legfix5/opus_adjudication/bill_recall_culling_opus5_20260728a/
- You may write helper code only inside that output directory.
- Never modify the recovered input folder or the 18,557-row discovery corpus.

Binding inputs
--------------
Recovered input root:
C:/Users/pgoff/AppData/Local/Temp/claude/cxwt-acu-registry/

Read and bind:
- audits/legfix5/opus_adjudication/recall_floor_evidence/receipt.json
- audits/legfix5/opus_adjudication/recall_floor_evidence/legacy_collection_floor_465.json
- audits/legfix5/opus_adjudication/recall_floor_evidence/quorum_recall_floor_44.xlsx
- audits/legfix5/opus_adjudication/original_method_evidence/manifest.json
- audits/legfix5/opus_adjudication/original_method_evidence/category_method_registry.json
- audits/legfix5/congress_advanced_pages_20260725/congress_advanced_records.ndjson
- audits/legfix5/congress_advanced_pages_20260725/congress_advanced_memberships.ndjson
- relevant local bill/title/summary/text/manual-evidence artifacts under the
  recovered input root and the frozen evidence manifest

Method to preserve
------------------
1. The Moneyball ACU outline defines the 19 category boundaries.
2. Review order is official title, official summary/status, then operative
   bill text. A legacy collection row or Quorum row is recall evidence, not
   disposition evidence.
3. Absence from discovery is neutral. It can never establish irrelevance.
4. A bill may be proposed for inclusion only on affirmative, bill-specific
   official evidence of a material credit-union policy nexus.
5. A false-positive exclusion requires affirmative official evidence showing
   the measure falls outside the 19 categories. Uncertainty remains flagged.
6. Category assignment must follow the bill's operative policy effect; do not
   retain a legacy category merely because the recall file used it.
7. Do not assign sponsorship, cosponsorship, direction, or scoring roles from
   letters, press, or recall files.

Required scope
--------------
- Verify the receipt identities: all 44 Quorum rows are present in discovery;
  442 of 465 legacy rows are present; exactly 23 legacy rows are absent.
- Deeply adjudicate each of those exact 23 absent measures. Search all relevant
  local evidence surfaces before flagging, but never invent missing official
  evidence.
- Reconcile all 465 legacy rows into exactly one accounting state:
  covered_in_discovery, include_candidate, exclude_false_positive, or flagged.
- Reconcile all 44 Quorum rows as covered_in_discovery or fail closed.
- Identify category corrections/cross-listing for the 23 where evidence
  supports them.
- Do not add any proposed include to discovery. Integration remains forbidden.

Required immutable outputs
--------------------------
Create:
1. proposal_adjudications_23.ndjson -- exactly one row per absent legacy key.
2. legacy_recall_partition_465.ndjson -- exactly one row per legacy row.
3. quorum_recall_partition_44.ndjson -- exactly one row per Quorum row.
4. receipt.json.
5. summary.md.

Each 23-row proposal must include:
- canonical_key
- legacy_category
- disposition: include_candidate | exclude_false_positive | flagged
- category_ids (zero or more canonical 19-category IDs)
- evidence_ids and evidence hashes/paths
- title_reviewed boolean
- official_summary_status
- operative_text_reviewed boolean
- concise reason and confidence
- automated_final_decision: false
- human_ratification_required: true

The receipt must bind every input and output by SHA-256, prove exact
23/465/44 coverage with no duplicates, provide count identities, list
blockers, and state:
- integration_performed: false
- production_write_performed: false
- scoring_performed: false
- rank_recompute_performed: false

Fail closed if any exact coverage identity cannot be proven. End with a compact
terminal report naming outputs, counts, unresolved blockers, and whether every
relevant new-bill recall gap is accounted for.
