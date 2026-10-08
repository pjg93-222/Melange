# OpenSecrets standardized collection - point-in-time receipt
Historical generated receipt: 2026-10-01T22:47:01+00:00 (UTC). Its original tables, transport statistics and test counts remain historical. The authoritative terminal section is dated 2026-10-02T06:19:59Z below and includes known PAC aggregate conflicts; passing formal validation does not certify those conflicts. Code: `standardized/osc`, README.md. No model publication/refit; Mentat production untouched.

## Requests / elapsed (computed from request_log.jsonl and the cache manifest)
- transport calls (one curl / requests invocation each; ALL runs incl. aborted duplicates): **777** (by status {200: 476, 429: 296, None: 5}; transport {'curl': 777}); redirect HTTP hops counted separately: 0; URLs cached: **491**; bytes downloaded 166,807,608
- first/last transport call: 2026-10-01T21:20:15+00:00 / 2026-10-01T22:46:53+00:00; ACTUAL wall time first-to-last call (includes rate-limit deferral waits and restarts, nothing removed): 5198.0 s
- retries logged 214; HTTP 429 responses 296; non-request events {'request': 25, 'cache_only_miss': 18042, 'deferred_family_retry_after': 66047, 'deferred_resume_after_not_reached': 91, 'family_deferred': 5}
- latest persisted run status: {'run_id': '20261001T224245Z-13124', 'phase': 'running', 'elapsed_s': 199.0, 'queue_states': {'done': 463, 'deferred': 362, 'pending': 3234}, 'deferred': {'urls': 362, 'earliest_resume_epoch': 1790894926.0, 'earliest_resume_utc': '2026-10-01T22:48:46+00:00', 'by_stage': {'seeds_lobby': 81, 'org_search': 281}, 'active_deferrals': {'global': None, 'families': {'federal-lobbying': 1790894926.8685713, 'search': 1790895018.3249655}}}, 'min_interval_s': 0.5, 'concurrency': 4, 'transport': 'curl'}
- latest persisted request stats: {'transport_calls': 6, 'redirect_hops': 0, 'url_fetches': 12, 'retries': 4, 'http_429': 6, 'bytes_downloaded': 36033, 'cache_hits': 469, 'duplicate_requests_avoided': 184, 'skipped_circuit_open': 0, 'skipped_deferred': 640, 'skipped_budget': 0, 'cache_only_misses': 0, 'challenge_200_rejected': 0, 'deferred_urls': 643, 'transport_by_name': {'curl': 6}, 'status_counts': {'429': 6}, 'http_requests_total': 6}

### Benchmarks per run (aborted/duplicate launches are labelled and NOT counted as the successful-run benchmark)
| run | aborted/duplicate | transport calls | redirect hops | HTTP 200 | HTTP 429 | bytes | first | last | wall s |
|---|---|---|---|---|---|---|---|---|---|
| archived_aborted_duplicate_runs_pre_run_id | True | 351 | 0 | 94 | 252 | 33,766,812 | 2026-10-01T21:20:15+00:00 | 2026-10-01T21:39:24+00:00 | 1149.0 |
| archived_run_35396_pre_run_id | False | 303 | 0 | 296 | 7 | 104,844,393 | 2026-10-01T21:40:05+00:00 | 2026-10-01T21:52:55+00:00 | 770.0 |
| 20261001T220111Z-2456 | False | 51 | 0 | 36 | 15 | 12,287,253 | 2026-10-01T22:01:12+00:00 | 2026-10-01T22:10:49+00:00 | 577.0 |
| 20261001T221323Z-71984 | False | 2 | 0 | 1 | 1 | 298,671 | 2026-10-01T22:13:24+00:00 | 2026-10-01T22:20:03+00:00 | 399.0 |
| 20261001T222014Z-69460 | False | 26 | 0 | 20 | 6 | 6,652,217 | 2026-10-01T22:20:14+00:00 | 2026-10-01T22:22:03+00:00 | 109.0 |
| 20261001T222610Z-46528 | False | 3 | 0 | 0 | 3 | 17,328 | 2026-10-01T22:26:13+00:00 | 2026-10-01T22:26:44+00:00 | 31.0 |
| 20261001T223042Z-65744 | False | 30 | 0 | 24 | 6 | 7,445,185 | 2026-10-01T22:31:49+00:00 | 2026-10-01T22:40:53+00:00 | 544.0 |
| 20261001T224245Z-13124 | False | 11 | 0 | 5 | 6 | 1,498,559 | 2026-10-01T22:42:47+00:00 | 2026-10-01T22:46:53+00:00 | 246.0 |

## Snapshot status (collection is continuing)
- **snapshot_with_gaps; collection remains active**: planned URLs by stage and state: {'seeds_national': {'done': 12}, 'seeds_pac': {'done': 82}, 'seeds_legacy': {'done': 224}, 'seeds_lobby': {'done': 77, 'deferred': 81}, 'org_search': {'deferred': 281, 'done': 1}, 'org_totals': {'done': 1}, 'pac_recipients': {'done': 66, 'pending': 3234}}
- deferred (server rate limit / managed challenge; not observed, not failed, never zero): 362; earliest resume 2026-10-01T22:48:46+00:00; active deferrals {'global': None, 'families': {'federal-lobbying': 1790894926.8685713, 'search': 1790895018.3249655}}
- resume (same cache, same state; PowerShell, from the `standardized` folder): `python -m osc collect --tiers all --data-dir "C:\melange-data\forecast-redesign-20261001-review\standardized-collector\data" --state-dir "C:\melange-data\forecast-redesign-20261001-review\standardized-collector\state" --out-dir "C:\Users\pgoff\Mentat\outputs\opensecrets-2008-2026-20261001\standardized\csv"` then `python -m osc build`
- Aggregates built on uncollected PAC/client/organisation pages are `partial`/`unavailable` with `partial_sum_usd` or blanks; nothing is completed from a partial census.

## Parser coverage by page type (cache manifest)
| page type | cached ok | failed |
|---|---|---|
| PAC candidate recipients | 77 | 0  |
| PAC industry breakdown | 10 | 0  |
| PAC industry detail (roster) | 72 | 0  |
| cost of election | 1 | 0  |
| legacy combined candidate list | 144 | 0  |
| legacy industry totals | 8 | 0  |
| legacy lobbying | 10 | 0  |
| legacy top contributors | 72 | 0  |
| lobbying about-data note | 1 | 0  |
| lobbying annual chart | 4 | 0  |
| lobbying category page | 5 | 2 {'failed:429': 1, 'failed:404': 1} |
| lobbying client in-house/outside | 1 | 0  |
| lobbying client table | 57 | 3 {'failed:429': 3} |
| national overview | 10 | 0  |
| org search | 1 | 4 {'failed:429': 4} |
| org totals history | 1 | 0  |
| other | 7 | 0  |
| taxonomy list | 1 | 0  |

## Tables (rows; extraction_status; completeness_status)
| table | rows | extraction_status | completeness_status |
|---|---|---|---|
| national_candidate_by_office | 70 | {'parsed': 69, 'served_cycle_mismatch': 1} | {'complete': 69, 'unavailable': 1} |
| national_candidate_giving | 90 | {'parsed': 84, 'served_cycle_mismatch': 6} | {'complete': 84, 'unavailable': 6} |
| national_election_cost | 10 | {'parsed': 9, 'not_published': 1} | {'complete': 9, 'unavailable': 1} |
| pac_industry_breakdown | 1335 | {'parsed': 1334, 'served_cycle_mismatch': 1} | {'complete': 1334, 'unavailable': 1} |
| pac_industry_candidate_totals | 130 | {'parsed': 72, 'not_published': 8, 'not_requested': 50} | {'complete': 70, 'unavailable': 58, 'partial': 2} |
| pac_roster | 3338 | {'parsed': 3338} | {'complete': 3338} |
| pac_membership_crosswalk | 3300 | {'parsed': 3300} | {'complete': 3300} |
| pac_pages | 3300 | {'parsed': 74, 'fetch_failed': 3226} | {'complete': 74, 'unavailable': 3226} |
| pac_chamber_party | 331 | {'parsed': 311, 'chamber_table_absent': 20} | {'complete': 311, 'partial': 20} |
| pac_recipients | 7718 | {'parsed': 7718} | {'complete': 7718} |
| pac_candidate_giving_industry | 538 | {'parsed': 62, 'pac_pages_unavailable': 244, 'not_published': 32, 'not_requested': 200} | {'partial': 62, 'unavailable': 476} |
| individual_candidate_giving_industry | 520 | {'source_not_found': 520} | {'unavailable': 520} |
| legacy_candidate_combined | 63470 | {'parsed': 63470} | {'partial': 63470} |
| legacy_candidate_combined_by_chamber_party | 477 | {'parsed': 419, 'not_published': 8, 'not_requested': 50} | {'partial': 419, 'unavailable': 58} |
| industry_totals | 130 | {'parsed': 72, 'not_published': 8, 'not_requested': 50} | {'complete': 72, 'unavailable': 58} |
| top_contributors | 1476 | {'parsed': 1418, 'not_published': 8, 'not_requested': 50} | {'partial': 1418, 'unavailable': 58} |
| org_contribution_sources | 698 | {'not_attempted': 668, 'parsed': 9, 'fetch_failed': 21} | {'unavailable': 689, 'complete': 9} |
| org_totals_history | 18 | {'incomplete_inputs': 1, 'parsed': 17} | {'partial': 1, 'complete': 17} |
| org_roster_crosswalk | 80 | {'not_attempted': 80} | {'unavailable': 80} |
| lobbying_annual | 247 | {'parsed': 95, 'fetch_failed': 38, 'offline_export': 19, 'not_requested': 95} | {'complete': 57, 'partial': 57, 'unavailable': 133} |
| lobbying_annual_offline_export | 114 | {'offline_export_ingested': 114} | {'complete': 95, 'partial': 19} |
| lobbying_clients | 5349 | {'parsed': 5263, 'fetch_failed': 76, 'not_published': 10} | {'complete': 5263, 'unavailable': 86} |
| lobbying_client_splits | 1 | {'parsed': 1} | {'partial': 1} |

## Schemas
- `national_candidate_by_office`: requested_cycle, served_cycle, office, party, n_candidates, total_raised_usd, total_spent_usd, cash_on_hand_usd, from_pacs_usd, from_individuals_usd, candidate_universe, display_type, control_type_value, control_display_value, controls_basis, table_caption, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `national_candidate_giving`: requested_cycle, served_cycle, donor_type, party, party_universe, office_scope, amount_usd, offices_included, offices_expected, all_party_amount_usd, other_party_residual_signed_usd, candidate_universe, display_type, controls_basis, coverage_note, money_universe, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `national_election_cost`: requested_cycle, served_cycle, total_usd, presidential_usd, congressional_usd, sum_check_delta_usd, asterisk_flag, dollar_basis, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `pac_industry_breakdown`: requested_cycle, served_cycle, industry_code, industry_name, classification, hierarchy_note, total_usd, to_democrats_usd, to_republicans_usd, other_party_residual_signed_usd, row_detail_href, row_href_cycle, row_href_cycle_stale, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `pac_industry_candidate_totals`: scope_id, scope_name, opensecrets_code, scope_classification, mentat_key, scope_relation, requested_cycle, served_cycle, total_usd, to_democrats_usd, to_republicans_usd, other_party_residual_signed_usd, n_pacs_headline, n_pac_rows, roster_sum_total_usd, roster_sum_democrat_usd, roster_sum_republican_usd, roster_minus_headline_democrat_usd, roster_minus_headline_republican_usd, breakdown_total_usd, breakdown_matches_detail, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `pac_roster`: scope_id, scope_name, opensecrets_code, scope_classification, mentat_key, scope_relation, requested_cycle, served_cycle, pac_id, pac_name, pac_slug, affiliate, lean, total_usd, to_democrats_usd, to_republicans_usd, other_party_residual_signed_usd, summary_url, summary_href_cycle, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `pac_membership_crosswalk`: requested_cycle, pac_id, pac_name, scope_ids, scope_codes, n_scopes, overlap_note, source_urls, source_retrieved_utc, source_sha256s, source_capture_pairs, extraction_status, completeness_status, reason_code
- `pac_pages`: pac_id, pac_name, pac_slug, requested_cycle, served_cycle, page_url, headline_total_usd, headline_democrat_usd, headline_republican_usd, house_recipient_rows, senate_recipient_rows, tables_seen, chamber_dr_sum_democrat_usd, chamber_dr_sum_republican_usd, headline_minus_chamber_democrat_usd, headline_minus_chamber_republican_usd, presidential_recipient_rows, missing_amount_cells, all_party_sum_usd, all_party_reconciles_to_headline_total, negative_amount_rows, reconciles_to_headline, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `pac_chamber_party`: pac_id, requested_cycle, served_cycle, chamber, party_group, summary_table_amount_usd, recipient_rows_sum_usd, n_recipients, amount_usd, amount_basis, summary_minus_rows_usd, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `pac_recipients`: pac_id, requested_cycle, served_cycle, chamber, candidate, sort_name, party_code, party_group, state, amount_usd, candidate_url, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `pac_candidate_giving_industry`: scope_id, scope_name, opensecrets_code, scope_classification, mentat_key, scope_relation, requested_cycle, served_cycle, chamber, party_group, amount_usd, partial_sum_usd, amount_status, pacs_expected_headline, pacs_in_roster, pacs_unique_ids, pacs_duplicate_roster_rows, pacs_retrieved, pacs_missing, pacs_with_missing_money, pacs_unreconciled, presidential_party_usd, industry_headline_party_usd, headline_minus_chambers_incl_presidential_usd, chamber_sum_minus_headline_usd, money_universe, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `individual_candidate_giving_industry`: scope_id, scope_name, opensecrets_code, scope_classification, mentat_key, scope_relation, requested_cycle, served_cycle, chamber, party_group, amount_usd, industry_individual_total_all_recipients_usd, money_universe, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `legacy_candidate_combined`: scope_id, scope_name, opensecrets_code, scope_classification, mentat_key, scope_relation, requested_cycle, served_cycle, list_chamber, recipient, party_code, party_group, state_label, state_code, combined_pac_individual_usd, chamber_basis, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `legacy_candidate_combined_by_chamber_party`: scope_id, scope_name, opensecrets_code, scope_classification, mentat_key, scope_relation, requested_cycle, served_cycle, list_chamber, party_group, combined_pac_individual_usd, n_rows, n_negative_rows, money_universe, chamber_basis, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `industry_totals`: scope_id, scope_name, opensecrets_code, scope_classification, mentat_key, scope_relation, requested_cycle, served_cycle, total_usd, individual_usd, pac_usd, soft_outside_usd, democrat_usd, republican_usd, democrat_pct, republican_pct, party_pct_basis, donor_sum_minus_total_usd, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `top_contributors`: scope_id, scope_name, opensecrets_code, scope_classification, mentat_key, scope_relation, requested_cycle, served_cycle, rank, organisation, organisation_normalized, total_usd, candidates_parties_usd, democrat_usd, republican_usd, outside_groups_usd, liberal_groups_usd, conservative_groups_usd, lean, total_minus_cp_plus_outside_usd, additivity_flag, pac_individual_split_status, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `org_contribution_sources`: scope_id, scope_name, opensecrets_code, scope_classification, mentat_key, scope_relation, requested_cycle, served_cycle, rank, organisation, industry_page_total_usd, industry_source_url, industry_source_retrieved_utc, industry_source_sha256, org_search_status, org_id, org_slug, profile_total_usd, profile_individual_usd, profile_pac_usd, profile_soft_individual_usd, profile_soft_organization_usd, profile_democrat_usd, profile_republican_usd, profile_minus_industry_page_usd, scope_mismatch_flag, scope_qualification, match_qualification, n_affiliates_listed, affiliates_selected_cycle, profile_url, search_url, search_retrieved_utc, search_sha256, source_universe, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `org_totals_history`: org_id, org_slug, org_name, cycle, total_usd, democrat_usd, republican_usd, individual_usd, pac_usd, soft_individual_usd, soft_organization_usd, by_party_row_present, by_source_row_present, matched_via, scope_ids, search_url, search_retrieved_utc, search_sha256, profile_url, note_527, match_qualification, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `org_roster_crosswalk`: roster_source_workbook, roster_worksheet, roster_row_number, roster_scope_id, roster_mentat_industry, original_company_name, normalized_company_name, roster_capture_utc, roster_workbook_sha256, roster_snapshot_status, search_url, match_status, n_org_candidates, org_candidates, org_id, org_slug, profile_url, history_first_cycle, history_last_cycle, n_history_cycles, profile_retrieved_utc, profile_sha256, scope_qualification, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `lobbying_annual`: scope_id, scope_name, opensecrets_code, scope_classification, mentat_key, scope_relation, requested_year, served_year, spend_usd, source_category_id, source_category_title, clients_active, client_rows_parsed, main_chunk_industry_spend_usd, chart_minus_main_usd, in_house_usd, outside_firm_usd, in_house_outside_status, in_house_outside_reason, in_house_partial_sum_usd, outside_partial_sum_usd, clients_with_split, clients_split_reconciled, data_as_of_date, spending_period_start, spending_period_end, period_note, capture_date, capture_timestamp_status, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `lobbying_annual_offline_export`: scope_id, scope_name, opensecrets_code, scope_classification, mentat_key, scope_relation, requested_year, source_category_id, spend_usd, lobbyists_count, lobbyists_note, http_annual_spend_usd, comparison, source_file, source_file_sha256, source_method, source_page_url, capture_date, capture_timestamp_status, source_as_of_note, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `lobbying_clients`: scope_id, scope_name, opensecrets_code, scope_classification, mentat_key, scope_relation, requested_year, served_year, row_order, client, client_id, client_slug, spend_usd, client_url, listing_note, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes
- `lobbying_client_splits`: scope_id, scope_name, opensecrets_code, scope_classification, mentat_key, scope_relation, requested_year, served_year, client, client_id, industry_table_spend_usd, client_year_total_usd, in_house_usd, outside_firms_usd, components_explicit, split_sum_usd, split_sum_minus_page_total_usd, page_total_minus_industry_table_usd, reconciliation_flag, source_url, final_url, http_status, retrieved_utc, source_sha256, cache_key, source_generation, source_vintage, source_release_date, source_cutoff_date, source_cutoff_basis, extraction_status, completeness_status, reason_code, notes

## Cross-checks
summary: {'pass': 57, 'info': 10}
| status | check | expected | actual |
|---|---|---|---|
| pass | unique_keys:national_candidate_by_office | 0 | 0 |
| pass | unique_keys:national_candidate_giving | 0 | 0 |
| pass | unique_keys:national_election_cost | 0 | 0 |
| pass | unique_keys:pac_industry_breakdown | 0 | 0 |
| pass | unique_keys:pac_industry_candidate_totals | 0 | 0 |
| pass | unique_keys:pac_roster | 0 | 0 |
| pass | unique_keys:pac_membership_crosswalk | 0 | 0 |
| pass | unique_keys:pac_pages | 0 | 0 |
| pass | unique_keys:pac_chamber_party | 0 | 0 |
| pass | unique_keys:pac_candidate_giving_industry | 0 | 0 |
| pass | unique_keys:individual_candidate_giving_industry | 0 | 0 |
| pass | unique_keys:legacy_candidate_combined_by_chamber_party | 0 | 0 |
| pass | unique_keys:industry_totals | 0 | 0 |
| pass | unique_keys:lobbying_annual | 0 | 0 |
| pass | provenance_on_parsed_rows | 0 | 0 |
| pass | blanks_never_zero | 0 | 0 |
| info | negative_amounts_preserved | >0 expected | 47 |
| pass | cache_sha256_byte_exact | 0 | 0 |
| pass | national_vs_browser_json | 138 cells, 0 mismatch | 138 cells, 0 mismatch, 0 missing |
| pass | national_2024_vector | (1187730, 422640137, 87386285, 1802512049, 1247529449, 11836 | (1187730, 422640137, 87386285, 1802512049, 1247529449, 1183616110) |
| pass | national_2012_pres_all_below_R_preserved | 1681812<1706312 | 1681812 vs 1706312 |
| info | national_2026_not_relabelled | mismatch/failed rows or true 2026 | served_cycle_mismatch:2024 |
| pass | national_controls_derived | 0 rows with other universe/display | 0 of 69 |
| pass | national_2026_gap_aggregate_rows | >0 rows, all unavailable/blank/reason-coded | 6 rows |
| pass | national_offices_included_explicit | 0 | 0 |
| pass | national_aggregate_cycles | 9 cycles | [2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022, 2024] |
| pass | aba_2024_vector | {('House', 'D'): 780500, ('House', 'R'): 1464999, ('Senate', | {('House', 'D'): 780500, ('House', 'R'): 1464999, ('Senate', 'D'): 57500, ('Senate', 'R'): |
| pass | aba_2024_senate_independents | [15000] | [15000] |
| pass | pac_roster_equals_headline | 72 rows, 0 unexplained | 70 complete, 2 partial-with-reason, 0 unexplained |
| info | breakdown_equals_detail | 0 | 1 |
| pass | crosswalk_url_capture_pairs | 0 | 0 |
| pass | f03_2024_detail_vector | (11633976, 4554978, 7033998, 78) | (11633976, 4554978, 7033998, 78) |
| pass | f03_2018_vector_stale_href_trap | (13828165, 4213679, 9558486) | (13828165, 4213679, 9558486) |
| info | pac_industry_chamber_completeness |  | {'partial': 44} |
| pass | pac_complete_cells_reconcile_headline | 0 | 0 |
| pass | pac_exact_amount_only_when_complete | 0 | 0 |
| info | pac_pages_status |  | {'parsed': 74, 'fetch_failed': 3226} |
| info | pac_pages_reconcile |  | {'True': 74} |
| pass | industry_totals_vs_old_collector | 63 rows equal | 63 compared, 0 differ |
| pass | legacy_candidate_rows_vs_old_collector | 126 | 126 |
| info | top_contributor_rows_vs_old | 1238 | old=0 new=1418 |
| pass | election_cost_vs_old | 0 | 0 |
| pass | lobby_annual_vs_browser_csv:insurance | 0 | 0 |
| pass | lobby_annual_vs_browser_csv:commercial_banks | 0 | 0 |
| pass | lobby_annual_vs_browser_csv:credit_unions | 0 | 0 |
| pass | lobby_annual_vs_browser_csv:automotive_industry | 0 | 0 |
| pass | lobby_annual_vs_browser_csv:telecom_services | 0 | 0 |
| pass | lobby_T2100_vs_browser_capture | 0 | 0 |
| pass | lobby_vector:insurance:2026 | (88178939, 179) | (88178939, 179) |
| pass | lobby_vector:commercial_banks:2026 | (44990209, 96) | (44990209, 96) |
| pass | lobby_vector:credit_unions:2026 | (4153000, 16) | (4153000, 16) |
| pass | lobby_vector:automotive_industry:2026 | 64603605 | 64603605 |
| pass | lobby_vector:telecom_services:2026 | 59292390 | 59292390 |
| pass | lobby_vector:auto_manufacturers:2026 | (22925589, None) | (22925589, None) |
| pass | lobby_vector:auto_manufacturers:2024 | (48570667, 34) | (48570667, 34) |
| pass | lobby_client_sum_vs_annual | 0 | 0 |
| pass | lobby_F09_label |  |  |
| pass | lobby_asof_2026 | 2026-07-23/2026-06-30 | 2026-07-23/2026-06-30 |
| info | lobby_in_house_outside_status |  | {'not_collected': 75, 'partial_unreconciled': 1, 'unavailable': 76, '': 95} |
| pass | lobby_complete_exact_is_exact | 0 | 0 |
| pass | lobby_exact_blank_unless_complete | 0 | 0 |
| pass | org_complete_requires_all_components | 0 | 0 |
| pass | org_joined_rows_carry_both_origins | 0 | 0 |
| info | org_roster_crosswalk_census | 80 | 80 |
| pass | boa_2024_vector | (4231320, 2000278, 1973367, 3308282, 710000, 212554, 484) | (4231320, 2000278, 1973367, 3308282, 710000, 212554, 484) |
| pass | boa_2008_vector | (3669164, 1657143, 1996071, 5945, 10005) | (3669164, 1657143, 1996071, 5945, 10005) |
| info | org_match_status |  | {'org_search_not_collected': 668, 'matched_exact': 9, 'deferred_family_429_cooldown': 14,  |

## Gaps by reason (gap_summary.csv)
| table | reason | rows |
|---|---|---|
| legacy_candidate_combined | combined_pac_individual_not_a_donor_split | 63470 |
| pac_pages | not_collected | 3226 |
| top_contributors | top_list_only_no_pac_individual_split | 1418 |
| org_contribution_sources | org_search_not_collected | 668 |
| individual_candidate_giving_industry | no_direct_industry_individual_by_chamber_source | 520 |
| legacy_candidate_combined_by_chamber_party | combined_pac_individual_not_a_donor_split | 419 |
| pac_candidate_giving_industry | pac_pages_missing | 288 |
| pac_candidate_giving_industry | no_published_industry_code | 200 |
| lobbying_annual | no_published_industry_code | 95 |
| lobbying_annual_offline_export | offline_export_ingested | 95 |
| org_roster_crosswalk | org_search_not_collected | 80 |
| lobbying_clients | deferred_family_retry_after | 73 |
| industry_totals | no_published_industry_code | 50 |
| legacy_candidate_combined_by_chamber_party | no_published_industry_code | 50 |
| pac_industry_candidate_totals | no_published_industry_code | 50 |
| top_contributors | no_published_industry_code | 50 |
| lobbying_annual | deferred_family_retry_after | 38 |
| pac_candidate_giving_industry | cycle_not_in_source_menu | 32 |
| pac_chamber_party | chamber_table_absent_on_page | 20 |
| lobbying_annual | http_annual_chart_unavailable_offline_native_export_used | 19 |
| lobbying_annual | legacy_source_no_in_house_outside_no_cutoff | 19 |
| lobbying_annual | main_chunk_missing_or_differs | 19 |
| lobbying_annual_offline_export | http_capture_unavailable_offline_export_used | 19 |
| org_contribution_sources | deferred_family_429_cooldown | 14 |
| lobbying_clients | legacy_clients_only_for_even_cycles_on_source_menu | 10 |
| pac_candidate_giving_industry | pac_pages_missing;pac_page_not_reconciled_to_own_headline_or_roster | 10 |
| industry_totals | cycle_not_published | 8 |
| legacy_candidate_combined_by_chamber_party | cycle_not_in_source_menu | 8 |
| pac_candidate_giving_industry | pac_pages_missing;roster_not_reconciled_to_industry_headline | 8 |
| pac_industry_candidate_totals | cycle_not_in_source_menu | 8 |
| top_contributors | cycle_not_in_source_menu | 8 |
| org_contribution_sources | deferred_family_retry_after | 7 |
| national_candidate_giving | served_cycle_mismatch | 6 |
| lobbying_clients | deferred_family_429_cooldown | 3 |
| pac_industry_candidate_totals | roster_dr_sums_differ_from_headline | 2 |
| lobbying_client_splits | split_sum_differs_from_client_total | 1 |
| national_candidate_by_office | served_cycle_mismatch | 1 |
| national_election_cost | cycle_not_published | 1 |
| org_totals_history | org_component_missing | 1 |
| pac_industry_breakdown | served_cycle_mismatch | 1 |

## Tests
```
...................................................                      [100%]
51 passed in 15.72s
```


Coordinator qualification: this receipt describes a partial snapshot, not a completed collection. The collector continues as PID68360. Per-run aborted/duplicate flags produced by the generator are incomplete: several earlier single-process runs were interrupted as documented in COORDINATOR_STATE.txt. False is not proof that a run completed. The first-to-last transport interval is not total process lifetime. Use the dated independent validation for dataset acceptance and the status/log for current process progress. The deadline option is a soft bound in this version.

## Historical snapshot refresh — 2026-10-02T01:10:18Z (October 1, 9:10 p.m. Eastern)

Earlier generated tables, test counts and transport intervals above are historical. This historical full offline build completed in 206.640 seconds: 58 passing data checks, 10 informational checks, no failures, including a hash check of 3,109 present HTTP-200 cached bodies. All 60 software tests passed in 15.62 seconds at that earlier checkpoint; they were not rerun for the current refresh.

Current client split rows: 2,563, including 2,181 reconciled and 382 partial (326 split-total mismatches and 56 industry-scope mismatches). There are 55 partial industry-year rows and zero exact industry in-house/outside totals. Source coverage remains partial. Other core observed counts are unchanged: 9,861 PAC recipient rows across 139 of 3,300 planned PAC-cycle pages; 7,569 client listing rows plus 67 blank placeholders; 72 industry totals; 1,418 top contributors; 114 annual lobbying observations; 69 national office-party rows with 138 donor values; 84 derived national aggregates; nine election-cost cycles. PAC industry/chamber totals have 62 partial cells and zero exact cells; employee/chamber data remain unavailable.

The user-directed speed change removes duplicate client body reads and the validator's second sidecar read, preserving SHA checks, challenge rejection, served-year checks and exact-census predicates. In a frozen F03/2008-2010 sample of 239 captured pages (234 client splits), cache loads fell from 473 to 239. Three alternating post-warmup runs per version measured median component extraction at 4.114143 versus 2.994704 seconds, 27.2% less time. All three component CSVs were byte-identical in all eight recorded runs, with zero transport. This excludes CSV writing, validation and full-build timing; it is not a network speedup or a guaranteed general speedup. The full-build duration above is a separate measurement. Evidence: C:/melange-data/forecast-redesign-20261001-review/standardized-collector/speed-review/benchmark_result.json.

Bounded independent diff and snapshot checks found no blocking semantic error, client arithmetic/flag/year/key/group-count error or missing populated provenance fields; CSV hashes were stable. Client source hashes number 2,543, which is not a unique-client census or an independently inspected 2,543-body audit. Client CSV SHA256: dfa17c2f7464b9f36fc68e34c99f128b71e8200fab535d4441a89b685310adc3. validation.json SHA256: b99a7ef08d5a99d1b3d23912b996e6dfd8866625f2534011e96bcff36712365e. Reports: speed-review/INDEPENDENT_DIFF_REVIEW.txt, SNAPSHOT_VERIFICATION.txt and SNAPSHOT_COUNTS.json under the review data root. The historical 310 HTTP-body/six-native-file independent audit covers only the 22:46:28Z snapshot. Client as-of/release fields stay blank where unstated.

The prior offline ACU validator string-versus-integer error was repaired without changing source amounts or the real partial -264,000-dollar mismatch. Its failed receipt and before-fix regression remain preserved; valid mismatch now passes while altered money/falsely exact status fails.

Collection remains active under sole PID 68360. No transport, queue, pacing or retry-state edit or collector restart was made. Full requested coverage, including 2026 contribution/national values, employee chamber splits, complete PAC detail and exact custom Mentat aggregate mappings, remains incomplete. A validated partial export is not a completed collection.
## Terminal snapshot — 2026-10-02T06:19:59Z

PARTIAL SOURCE DATA — KNOWN PAC AGGREGATE CONFLICTS
The bounded collector RUN finished; final export validated at 06:19:59Z, owner released at 06:20:00Z, and process68360 was confirmed absent at 06:20:41Z. Collection retains 3,029 deferred PAC/cycle URLs. No automatic restart, extra terminal build, or full requested-coverage claim. Formal validation reports 58 PASS /10 INFO /0 FAIL and rehashed 8,442 cached bodies; these checks miss the PAC certification issue below.

PAC QUARANTINE: independent review found 62 source-summary/detail discrepancies across 56 PAC/cycles, and 55 page all-party sums differing from recipient detail. Selected summary amounts plus recipient Other/Unclassified may double count a source-label disagreement; a separate Presidential summary discrepancy was also confirmed. Four T2100/2008 industry cells are flagged exact by the existing code but are NOT CERTIFIED: House R summary440,750 versus recipient detail438,750 differs2,000; the other three cells match arithmetically but do not prove a consistent industry-year universe. The final delivery relocates pac_pages.csv, pac_chamber_party.csv and pac_candidate_giving_industry.csv, unchanged, into unverified_pac_tables/. Original filename references in gaps/crosschecks remain unchanged. pac_recipients.csv stays in csv/ as faithfully captured detail, not proof that contradictory source party labels are correct. No source values or parties were silently corrected. Collector code is not repaired: future exact eligibility must require source-summary/detail agreement and all-party reconciliation.

Final observed counts: 271 PAC pages of3,300;13,918 recipient rows (89 signed negative),1,212 chamber/party rows. Industry table540rows contains4quarantined exact flags,60partial sums,244unavailable and232blank statuses; industry individual/candidate amounts remain entirely unavailable. Company profile history has1,877numeric rows from132profiles:1,088requested-window2008–2024 rows with PAC and individual values,789pre2008,zero2026. Linked profiles:489numeric/209blank across118profiles;415totals differ from industry-page totals,74equal with universe equivalence unproven. Current Mentat roster:22exact matches with history,38no organization rows,20no exact match. Profile history and current rosters are not historical industry censuses.
Client/lobbying counts remain7,338split rows (6,272reconciled,1,066partial:873sum/193scope),5,004primary+2,334comparison;7,271referenced hashes,102partialannual scope-years,zero exact industry in-house/outside totals. Annual spend152numeric/95blank (76primary/76comparison);client listings11,892numeric/10blank (5,277primary/6,615comparison). Industry totals72,topcontributors1,418,national69office/partyrows containing138donorvalues,84derived aggregates and9costcycles remain unchanged. Campaign/national2026 remains unobserved. Source/capture/as-of, nominal-dollar, signed-net and F09/M02/custom-scope qualifications above remain essential.

Evidence: standardized-collector/FINAL_SNAPSHOT_VERIFICATION.txt, FINAL_SNAPSHOT_COUNTS.json, FINAL_PAC_PAGE_DISCREPANCIES.csv and FINAL_PAC_CHAMBER_DISCREPANCIES.csv. Independent stable CSV read completed06:21:37Z, with supplemental matching-hash checks and two targeted raw examples. This is not a comprehensive raw-page audit. Validation SHA2561baf96d2e5f5eabd14399974dc5b091b0c266d8fc935074c3a600312b0b7534e;org history SHA25600aebf5a92fc4208db84231c35c41fd05c19214fada9b2dabc10a74c5833ebf4;linked-org SHA256028804ed1b02e6700f56a6738151bdb8327b993e6b8682bd3d1efd10cb95c93c;client SHA2561c54e68eee3310936d7c022f7c4eb344cd533b0ec16f1f0b3108eb84fa2242dc. Prior60software tests remain historical, not certification of this newly found gap.

All three older delivery folders/ZIPs (013154,040315,051937) remain unchanged historical partial snapshots and exclude later data. Final packaging preserves all CSV bytes and includes the discrepancy reports and prominent quarantine. Forecast review remains C:/melange-data/forecast-redesign-20261001-review/REVIEW_AND_COMPLETION_2026-10-01.txt; reviewed scratch package instructions are C:/melange-data/forecast-redesign-20261001-review/forecast-completion/package/README.md and apply_forecast_completion.py. The integration proof does not authorize live apply, publication or a console restart. Candidate HOLD, production and owner choices remain unchanged. Parent pauses follow-up after terminal delivery/report; no automatic collection restart.
