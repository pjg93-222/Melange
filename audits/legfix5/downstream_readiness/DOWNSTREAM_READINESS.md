# Legislation downstream readiness

- Generated: `2026-07-26T16:59:43.052850+00:00`
- Sync allowed: **NO**
- Strict queries completed: **22/62**
- Strict discovery status: **failed**
- Final merged generation: **not complete**
- Frozen production baseline: **DRIFT/ABSENT**
- Review unresolved: **unknown**
- Relationship enrichment: **not complete**
- Reconciliation acceptance: **FAIL/ABSENT**
- Decay propagation audit: **FAIL/STALE/ABSENT**
- Post-weekly-refresh downstream drift evidence: **CURRENT_INFORMATIONAL** (informational only; no gate authority)
- Behavior/stance semantic drift evidence: **CURRENT_INFORMATIONAL** (informational only; no gate authority)
- Planning/dashboard semantic drift evidence: **CURRENT_INFORMATIONAL** (informational only; causality/domain-correctness gaps retained)
- Workbook OOXML semantic drift evidence: **CURRENT_INFORMATIONAL** (informational only; formula/runtime/applicability blockers retained)
- Isolated formula-cache recomputation evidence: **CURRENT_INFORMATIONAL** (informational only; live-cache, promotion, applicability, runtime, and causality blockers retained)
- Official roll-call action source: **FAIL/STALE/ABSENT** (BILLSTATUS no-key for bills/resolutions; amendments fail closed)
- Official roll-call member identity: **FAIL/STALE/ABSENT**
- Isolated consumer steps: **16/16**
- Role-weight policy: **unresolved**
- Approved spreadsheet import: **PASS**
- Current workbook live computation: **BLOCKED**
- Accepted workbook recomputation: **FAIL/ABSENT**
- Centrality/rank treatment: **preserved** (base/AUG centrality effective rank weight remains 0; committee score remains the influence pillar)

## Gates

- [ ] `strict_discovery_complete`
- [ ] `final_merged_generation_complete`
- [ ] `acu_title_corroboration_query_plan_current_and_resolved`
- [x] `billstatus_bulk_enrichment_snapshot_current`
- [x] `query_specificity_current_and_passed`
- [ ] `production_baseline_still_frozen`
- [ ] `membership_review_current_and_resolved`
- [ ] `relationship_enrichment_complete`
- [ ] `coverage_reconciliation_acceptance_passed`
- [ ] `aggressive_decay_staged_for_presync`
- [ ] `decay_propagation_audit_current_and_passed`
- [x] `accepted_corpus_and_downstream_producers_exist`
- [ ] `role_weight_policy_explicitly_approved`
- [x] `approved_spreadsheet_engine_import_passed`
- [ ] `accepted_workbook_legislative_recompute_complete`
- [ ] `accepted_workbook_live_computation_verified`
- [ ] `legislative_efficiency_definition_consistent`
- [x] `centrality_rank_method_preserved`
- [x] `shadow_consumer_plan_structural_only`
- [ ] `shadow_consumer_isolation_executed_and_passed`
- [ ] `shadow_current_policy_layout_numeric_bound`
- [ ] `official_rollcall_event_ledger_exists`
- [ ] `rollcall_measure_match_audit_exists`
- [ ] `official_rollcall_member_identity_complete`
- [ ] `official_rollcall_action_source_complete`
- [ ] `staged_recompute_acceptance_passed`

## Hard rule

No production archive, workbook, network, roll-call aggregate, rank authority, dashboard, or mainframe publication may be replaced until every gate above is true.
