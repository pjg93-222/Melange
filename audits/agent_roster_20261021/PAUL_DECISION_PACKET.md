# Paul decision packet, 2026-10-21

Status: DRAFT. Nothing ruled. Defaults are proposals.

Source: the P3 backlog in the approved plan `<local plan file, not published>`. Rows are drawn from the "Held for Paul" sections of the 16 sweep reports in `audits/fec_sweep_20261013/` (`fec_collect.md`, `fec_engine.md`, `fec_district.md`, `fec_network.md`, `fec_members.md`, `fec_lobbying.md`, `fec_stance.md`, `fec_legislation.md`, `fec_staffer_network.md`, `fec_surfaces.md`, `fec_speech.md`, `fec_root.md`, `fec_audit.md`, `fec_research.md`, `fec_tools.md`, `fec_desktop.md`), plus the wave-1 decisions in `audits/wave1_20261019/PAUL_DECISIONS.md` and the governance matrix in `audits/deploy_20261011/GOVERNANCE_MATRIX.md`.

How to read it. "Proposed default" is a draft for the manager and overseer to confirm in the first decision lane; "proposed: TBD" means the default is not obvious from the theme. Where a report carries its own proposed fix it is quoted in short form. "If Paul says no" is "item stays as-is; report notes risk" unless the report states a consequence. Each row appears in the single theme that fits best; some rows could sit in two themes.

## 1. Non-atomic writes of receipts, ledgers and sealed keys (members, research, audit, stance).

| Report | File:line | Issue | Proposed default | If Paul says no |
|---|---|---|---|---|
| engine | forecast_ledger.py:395 | freeze check-then-replace is not exclusive; ledger line plain write | proposed: exclusive create (open mode x or os.link) for the freeze; one-call write plus fsync for ledger lines | item stays as-is; report notes risk |
| lobbying | build_network_2021_rebuild.py:6429 | outputs not written as a set; failed run leaves stale receipts | proposed: stage everything and write receipts last, or invalidate old receipts first | item stays as-is; report notes risk |
| audit | audit_postrefresh_behavior_stance_semantics.py:170 | pointer current.json written non-atomically | proposed: port temp-file plus os.replace from downstream_drift, with the same re-mint | item stays as-is; report notes risk |
| stance | api_prelabel.py:130 | paid API results written straight over gold_label_queue.csv | proposed: write to a sidecar, then merge with tmp plus os.replace; catch PermissionError | an Excel lock loses every API result of a run; a crash can truncate the adjudicated gold file |
| research | cosponsor_universe/universe_common.py:31 | non-atomic receipt write can block run-once scripts (sealed) | proposed: tmp plus os.replace and re-seal, or leave sealed | item stays as-is; report notes risk |
| research | mpr/rematch_history.py:14 | rewrites frozen work_matrices.npz in place, non-atomic | proposed: write .tmp then os.replace; add rematched_utc and code sha to the manifest atomically | item stays as-is; report notes risk |
| members | b5_panel_build.py:114 | SEALED pid-to-member key written non-atomically and overwritable | proposed: refuse to overwrite an existing panel_key.json without a flag; use dump_atomic | a rebuild silently picks a new sample and replaces the sealed key |

## 2. Fail-open PASS: stale PASS receipts surviving a failure or exception (audit, desktop, members).

| Report | File:line | Issue | Proposed default | If Paul says no |
|---|---|---|---|---|
| district | fetch_hmda_district.py:1380 | up to 5 failed states publish as zero metrics that look real | proposed: TBD | failed-state districts keep publishing as zeros that look like real data |
| desktop | launch_moneyball_edge.py:100 | startup_receipt.json keeps old PASS after a failed launch | proposed: write a FAIL receipt in the except block, or unlink the receipt at the start of main(); write via temp file and os.replace | installed receipt stays a PASS dated 2026-10-14T21:24:33Z after a failure |
| audit | audit_quorum_recall_floor.py:336 | failing rerun leaves old PASS reconciliation_receipt.json | proposed: a failed run deletes or marks the PASS receipt (write a FAIL receipt); or have the consumer re-verify input hashes | item stays as-is; report notes risk |
| audit | verify_greenlit_primacy_integration.py:179 | any exception before final write leaves the July PASS receipt | proposed: a failed run deletes or marks the PASS receipt (write a FAIL receipt); or retire the script | July PASS receipt stays on disk after exceptions (13 untagged acts raise KeyError now) |
| research | cosponsor_institutions/institutions_votes.py:424 | PASS receipt rests on bare asserts; stripped under python -O | proposed: raise if not __debug__ at the top of main(), then re-seal | item stays as-is; report notes risk |
| research | cosponsor_universe/universe_amendment_features.py:206 | boundary_checks_passed rests on asserts; stripped under python -O | proposed: add the universe_boundary_checks.py:14 guard and record sum(checks) | item stays as-is; report notes risk |
| research | cosponsor_refinement build_extra_features.build() | no failures check on demographics_audit_v2.json | proposed: raise RuntimeError when demographics_audit_v2.json reports failures | item stays as-is; report notes risk |
| members | b5_audio_ctcm.py:L62 | fit exception printed; VERDICT PASS possible for unfitted model | proposed: set fit_ok=False in the except and require it, or refuse to run (DEPRECATED exit) | item stays as-is; report notes risk |
| members | b5_interaction_ctcm.py:82 | conv hard-coded True; fit exception only printed (look consumed) | proposed: conv from the solver's success flag, False on exception | item stays as-is; report notes risk |
| members | build_member_meeting_playbooks.py:418 | receipt rewritten PASS without checking prior validity | proposed: assert status PASS and both hashes match, SystemExit on failure | item stays as-is; report notes risk |
| members | sanitize_member_narratives_v2.py:139 | deterministic repairs stamped semantic_review pass True and PASS | proposed: set pass to null or not_reviewed (status PASS_DETERMINISTIC_PENDING_REVIEW) | rows repaired by deletion keep pass True with no semantic review |

## 3. Paid-API retry policy: retrying non-retryable errors, ignoring Retry-After, caching failures as None (members, lobbying, speech, tools).

| Report | File:line | Issue | Proposed default | If Paul says no |
|---|---|---|---|---|
| lobbying | classify_bill_positions.py:1383 | executor runs every queued item after first failure | proposed: cancel_futures on first failure, keep completed receipts | after a failure the executor keeps running every queued item (20 of 20 reproduced) |
| lobbying | classify_bill_positions.py:1263 | all exceptions retried 6 times; Retry-After ignored | proposed: honor Retry-After and never retry 4xx except 429 | item stays as-is; report notes risk |
| lobbying | lobby_position_classify.py:143 | circuit breaker does not stop queued API calls | proposed: explicit futures with cancel_futures on abort | item stays as-is; report notes risk |
| lobbying | lobby_position_benchmark.py:208 | failed results cached as None and never retried | proposed: do not cache failed results; retry them on the next run | INVALID arms stay invalid (kim_zeroshot scored 321 of 335) |
| lobbying | lobby_position_prompt_ab.py:163 | reuse_count never wired; cache_control applied regardless of fan-out | proposed: TBD | item stays as-is; report notes risk |
| tools | f2_stance_rationale_sidecars.py:451 | live_provider all-or-nothing, no retry; paid rationales discarded on one failure | proposed: retry only retryable statuses with backoff; include exception type and status in the error | one transient 429/529/timeout aborts the run after N paid calls and discards earlier paid rationales |
| speech | classify_local_youtube_turns.py:330; classify_youtube_anchor_candidates.py:177 | SDK default retries: one request can be billed up to three times | proposed: explicit timeout plus max_retries=0 and record api_requests_attempted | item stays as-is; report notes risk |
| members | b5_audio_verify.py:38 | failed yt-dlp fetch cached as empty, permanent NO_CAPTIONS | proposed: do not cache a failed fetch; cache empty only when yt-dlp succeeded; catch TimeoutExpired | 147 NO_CAPTIONS verdicts stay permanent |
| members | condense_member_narratives_v2.py:219 | canary gates nothing; all targets submitted regardless | proposed: TBD | paid spend continues after a failed canary |
| members | extend_affective_n_coverage.py:107 | retry catches every Exception; dropped chunks silent; exit 0 | proposed: retry only RateLimitError, APIConnectionError, APITimeoutError, InternalServerError; refuse to write when a chunk was dropped | dropped chunks stay silent and the script exits 0 |
| members | interview_antagonism_score.py:94; interview_e_persona_score.py:153 | catch-all retry re-buys paid Haiku calls on auth, 400 and parse failures | proposed: retry only RateLimitError, APIConnectionError, InternalServerError and 5xx; skip the final sleep | item stays as-is; report notes risk |
| members | revise_member_narratives_v2.py:344 | catch-all retries non-retryable failures up to 8 times | proposed: retry only transport errors (URLError, TimeoutError, ConnectionError, IncompleteRead) | item stays as-is; report notes risk |
| members | personal_texture_layer.py:386 | retry predicate is substring 'rate'; matches generate, separate | proposed: branch on exception type or status_code in 429, 500, 502, 503, 529 | item stays as-is; report notes risk |

## 4. Resume semantics: positional ids, stale reviews, unvalidated progress logs (members, stance, lobbying).

| Report | File:line | Issue | Proposed default | If Paul says no |
|---|---|---|---|---|
| lobbying | classify_bill_positions.py:1370 | resume ignores stored prompt_sha256 | proposed: reuse a prior record only when it matches a hash or key of the current input | a prompt edit silently mixes two prompts in one output |
| speech | classify_youtube_anchor_candidates.py:154 | CLASSIFIER_ERROR rows never re-classified; receipt still PASS_SCREENING_ONLY | proposed: opt-in --retry-errors flag; set PARTIAL_VISIBLE when classifier_errors > 0 | item stays as-is; report notes risk |
| stance | api_prelabel_tweets.py:118 | resume folds prior results by positional id alone | proposed: reuse a sidecar row only when its text or url matches the queue row | after a corpus change old labels attach to different tweets with no error |
| stance | api_stance_layer.py:198 | press run overwrites press_review_queue.csv decisions; reads frozen tone file only | proposed: carry over a non-empty your_decision keyed by url; build items from press_stream.load_tone_rows() | entered decisions would be destroyed (0 of 1,481 filled today); 291 refresh articles never get api_target |
| research | cosponsor_institutions/institutions_models.py:183 | crash-resume never succeeds (tuple vs list compare); sealed | proposed: TBD | item stays as-is; report notes risk |
| staffer_network | lda_composite_repair.py:2394 | KeyboardInterrupt leaves status RUNNING; resume refuses | proposed: catch BaseException, write FAILED with an INTERRUPTED error, then re-raise | only way back is hand-editing generation_status.json |
| members | b5_narratives.py:414 | error record overwrites a previously good narrative | proposed: keep the old entry when the prior was ok (store last_err) | a failed regeneration loses the previous good narrative |
| members | gen_demo_briefs.py:1384 | progress-log ok records not re-validated under current gates | proposed: reuse a prior record only when it matches a hash or key of the current input (triggers paid regeneration) | item stays as-is; report notes risk |
| members | revise_member_narratives_v2.py:422 | audit --resume reuses prior review with no hash of reviewed draft | proposed: store sha256 of the headed text and evidence basis; reuse only when both match (triggers paid re-review) | item stays as-is; report notes risk |

## 5. Sealed-input hash drift: challengers files (066a12c20), 3 receipts to re-mint, 3 held audit files, `cook_house_csv`, validate_communication_style.

| Report | File:line | Issue | Proposed default | If Paul says no |
|---|---|---|---|---|
| engine | outcome_contract.py:78 | git() has no timeout; editing it changes pinned tool_sha256 | proposed: TBD | item stays as-is; report notes risk |
| lobbying | build_network_2021_rebuild.py:1341 | should CORPUS_BASIS hash the client.id map and sweep manifests | proposed: TBD | item stays as-is; report notes risk |
| audit | audit_billstatus_enrichment_completeness.py:13 | broken entry point; fix changes producer sha256 so existing audits go STALE | proposed: TBD | script entry point stays broken (ModuleNotFoundError: legislation) |
| audit | audit_postrefresh_downstream_drift.py:537 | changed .py files get COMPLETE_BYTE_IDENTITY evidence; fix needs re-attest and re-mint | proposed: TBD | item stays as-is; report notes risk |
| audit | audit_postrefresh_behavior_stance_semantics.py:1314 | validate_evidence discards recomputed member closure; needs coordinated re-mint | proposed: TBD | item stays as-is; report notes risk |
| stance | build_field_action_evidence.py:402 | vote_cast_codes never checked against vote refresh receipt | proposed: add build_vote_category.py to needed once a forced vote refresh is accepted | no impact today (cast-code lines unchanged); hash stays unchecked |
| research | cosponsor_challengers/run_models.py:256 | develop() has no post-freeze guard; rerun breaks freeze selection hash | proposed: TBD | item stays as-is; report notes risk |
| research | cosponsor_challengers/write_report.py:53 | README pipeline cannot reproduce recorded artifacts (missing producers) | proposed: TBD | item stays as-is; report notes risk |
| research | cosponsor_institutions/institutions_verify.py:65 | sealed generation cannot be re-verified from live tree (post-seal edits) | proposed: TBD | item stays as-is; report notes risk |
| research | cosponsor_universe/universe_models.py:209 | edited after sealed hash recorded; downstream verifies fail closed | proposed: restore sealed bytes, or keep the edit with a re-seal or addendum naming the new hash | item stays as-is; report notes risk |
| research | mpr/history_speech.py:101 | excerpt offsets drift (normal vs raw text); hashed input of FROZEN_TEST_V5 | proposed: TBD | 5 of 496 review-queue rows keep excerpts that omit their target |
| members | validate_communication_style.py:36 | both validators FATAL on behavioral_dispositions.json and behavior_panel.json hash drift | proposed: rebuild and re-lock against current inputs, or restore the inputs | both validators and validate_guarded_profile_artifacts.py stay FATAL |

## 6. Roster and identity: Johnson/Scalise provenance, "Johnson, James", honorific regex. (The Aisha Wahab fault is closed: a roster-535 circular contract in build_primacy_surfaces, fixed in e347e0bb6 and e47a232fe on main.)

| Report | File:line | Issue | Proposed default | If Paul says no |
|---|---|---|---|---|
| network | press_engagement_layer.py:52 | honorific regex matches Title Case words as surnames | proposed: TBD | Title Case press titles keep matching false surnames (for example Young, Banks) |
| lobbying | entity_identity.py:1001 | bank_tier tests only the resolved display name | proposed: test the raw normalized name first, then the resolved name | item stays as-is; report notes risk |
| lobbying | entity_identity.py:1460 | union-find folds merger parts backward across all years (zero current effect) | proposed: TBD | item stays as-is; report notes risk |
| speech | materialize_leadership_prerole_reviewed_turns.py:134 | Johnson/Scalise review rows lack reviewer and timestamp but stamp VERIFIED | proposed: TBD | item stays as-is; report notes risk |
| members | b5_audio_verify.py:75 | classify() ignores NONE/empty hard-signal rule; 5 MATCH rows with no signal | proposed: parse the three fields positionally; downgrade to NEUTRAL when field 3 is empty or NONE | 5 MATCH rows stay hard matches in the frozen cohorts |
| members | member_identity.py:142 | 'Johnson, James' resolves to 'John James' | proposed: when a comma is present, try only the reordered variant | 'Johnson, James' keeps resolving to 'John James' in name joins feeding the model |

## 7. Measurement direction and definition: holistic_norm symmetry, flip-money definitions, defensive_appeal_value, SAY counting unscored.

| Report | File:line | Issue | Proposed default | If Paul says no |
|---|---|---|---|---|
| collect | refresh_fec_money.py:141 | pool exclusion and redefined receipt totals need per-change OK | proposed: TBD | item stays as-is; report notes risk |
| engine | salience_shock.py:162 | defensive_appeal_value counted for offense issues, changes GO PUBLIC order | proposed: TBD | item stays as-is; report notes risk |
| district | demographic_potential.py:1482 | growth_room gate misses zero_base_sectors (latent, 0 live cases) | proposed: TBD | item stays as-is; report notes risk |
| network | build_multilayer_network.py:102 | holistic_norm edges symmetrized into one direction only | proposed: TBD | holistic_norm cascade keeps edges only from the alphabetically smaller bioguide to the larger |
| lobbying | coalition_pricing.py:223 | intro_rate denominator counts every congress served | proposed: served = max(1, len(terms[b] & {115,116,117,118})) | 196 of 454 members keep a wrong intro_rate denominator |
| lobbying | financial_other_discovery.py:138 | amendment supersession differs from sector_spend | proposed: TBD | 4 proven groups keep losing income |
| audit | reconcile_mentat_money.py:74 | classify() returns timing when totals differ (MW-6 Gate 1 money gate) | proposed: return aggregation_residual for that case | item stays as-is; report notes risk |
| stance | build_media_blend.py:324 | _api_target keyed on raw URL, lookups use canonical URL | proposed: key by _canonical_press_url(url, keep_fragment=True) and measure the rank delta first | about 74% of articles keep missing their API target (627 of 2,388 hit) |
| stance | say_do_gap.py:45 | SAY counts 105,948 unscored items | proposed: count only scored, non-excluded items with pol >= 0 | SAY keeps counting unscored items (median say_n 45 vs 4 when scored only) |
| legislation | collect_official_rollcall_events.py:1094, 1598 | classify_final_passage and duplicate merge change which roll calls count | proposed: TBD | stays as an uncommitted sweep edit in the working tree |
| legislation | compute_legislation_policy_scenarios.py:311, 396 | scoring_eligible False rows get zero weight; changes scenario scores | proposed: TBD | stays as an uncommitted sweep edit in the working tree |
| surfaces | build_dashboard_bundle.py:698 | Overall flip sums members >= $10k; per-issue flip sums all | proposed: one definition, either Overall = sum over issues of sum(FL[lb].values()) or apply the >= $10k filter per issue | Overall CU stance card keeps understating per-issue totals by $458k |
| research | mpr/work_baseline.py:528 | non-converged bootstrap refits still feed SE and percentiles | proposed: TBD | published SE keep including non-converged refits (1 per Senate 116/117/118) |
| members | antagonism_validate.py:80 | G4 reads c1_bip_z (533) not cooperation_v2_z (300); locked gate | proposed: TBD | item stays as-is; report notes risk |
| members | antagonism_validate.py:64 | G1 split-half certifies a different composite than the gated measure | proposed: TBD | item stays as-is; report notes risk |
| members | b5_audio_embed.py:275 | chunk-mean pooling weights a short tail chunk equal to a full chunk | proposed: TBD | embeddings and prereg-pinned thresholds stay unchanged |
| members | b5_behavioral_instrument.py:191 | okmask unused; members with no lability get criterion 0 (look consumed) | proposed: TBD | item stays as-is; report notes risk |
| members | speech_n_genre_study.py:75 | sampling loop breaks; 11 members score on empty text (look consumed) | proposed: TBD | empty-text scores may have fed the consumed verdict (rho 0.0496, FAIL) |

## 8. Forecast and vintage: withdrawn cosponsors, Y-1 imputed zero, partial-year scoring, resolution horizon.

| Report | File:line | Issue | Proposed default | If Paul says no |
|---|---|---|---|---|
| engine | forecast_ledger.py:524 | cosponsor score counts joins dated before the freeze | proposed: TBD | next forecast_ledger run consumes the once-only score; 9 of 119 hits predate the freeze |
| engine | forecast_ledger.py:505 | cosponsor scoring fires with no minimum resolution horizon | proposed: TBD | next weekly_refresh or refresh_table DIAG run permanently scores the 119th Congress on about 2 months of joins |
| lobbying | champions_v2.py:675 | Tier-1 crown uses previous cycle's bundle (DECISIONS F-20) | proposed: TBD | item stays as-is; report notes risk |
| lobbying | cosponsor_forecast.py:1199 | withdrawn cosponsors labelled positives | proposed: TBD | item stays as-is; report notes risk |
| lobbying | lobby_forecast.py:750 | n_bills_y_minus_1 zero-imputed for first selected year | proposed: TBD | item stays as-is; report notes risk |
| lobbying | lobby_forecast.py:794 | partial 2026 target year scored as a full year (T=2024 split) | proposed: TBD | item stays as-is; report notes risk |
| lobbying | lobby_forecast.py:771 | current-vintage roster stamped with source year Y; as-of check blind to leak | proposed: TBD | item stays as-is; report notes risk |
| legislation | build_bank_anchor_backfill.py (whole file) | drops withdrawn cosponsors from credit; changes primacy inputs | proposed: TBD | stays as an uncommitted sweep edit in the working tree |
| legislation | build_registry_anchor_backfill.py:255 | raises on any withdrawn cosponsor; fails registry anchor build | proposed: TBD | stays as an uncommitted sweep edit in the working tree |

## 9. Gate semantics: `--look` and `--no-verify` writing live artifacts; `--promote` trusting stale reliability.

| Report | File:line | Issue | Proposed default | If Paul says no |
|---|---|---|---|---|
| engine | compet_reciprocity_look.py:126 | --look silently wins over --simulate; early-date message misleading (prereg file) | proposed: TBD | item stays as-is; report notes risk |
| lobbying | lobby_interactions.py:575 | --no-verify writes the live ledger with agrees=None | proposed: TBD | item stays as-is; report notes risk |
| lobbying | lobby_position_from_cache.py:49 | default output is the production positions file | proposed: TBD | a default run would shrink the production file from 45,464 rows to the benchmark subset |
| lobbying | fec_lda_round4b_look.py:719 | --look has no one-look gate or input SHA pins; Path B retired | proposed: TBD | item stays as-is; report notes risk |
| tools | e1_stance_imputation_harness.py:1234 | --look gated by a substring check only; no input hashes, no second-look block | proposed: TBD | item stays as-is; report notes risk |
| speech | speaker_anchor_recovery.py:1232 | retention_ready looks up clip_id but finals are per 8-second window | proposed: TBD | cleanup stays dead (0 of 934 sources READY); fails closed |
| audit | audit_tier_boundary_delta.py:12; audit_registry_anchor_primacy_delta.py:14-16 | no sys.path bootstrap; one run would overwrite sealed primacy receipts | proposed: retire to attic or repair with an --output flag | both scripts stay unimportable by path |
| audit | audit_tier_boundary_delta.py:207 | rank-authority-unchanged gate and deltas are constants, treated as evidence downstream | proposed: TBD | item stays as-is; report notes risk |
| stance | own_source_stance_model.py:786 | CU_GOLD_ORPHAN_OK=1 escape hatch does not work | proposed: drop the env var and correct the N13 note | N13 note keeps telling Paul the override unblocks the interview channel, which it does not |
| members | b5_multimethod_validate.py:490 | --promote trusts whatever reliability json is on disk | proposed: require rel package_counts to match META and check selected_content_sha256 | item stays as-is; report notes risk |
| members | b5_narratives_local.py:44 | default --out replaces live member_narratives_v2.json with templates | proposed: make --out required or refuse to overwrite a non-local schema; make --only merge | one default run replaces the live 533-member narratives; --only shrinks the file |
| members | b5_n_matrix.py:372 | RETIRED WITHOUT A LOOK prereg not enforced by look gate | proposed: also refuse when the prereg text contains RETIRED WITHOUT A LOOK | item stays as-is; report notes risk |
| members | merge_member_narratives_v2.py:200 | run without --activate writes live receipt path with no active hash | proposed: write to a .candidate path unless --activate | item stays as-is; report notes risk |
| members | merge_member_narratives_v2.py:205 | --activate backs up only when backup does not exist | proposed: always copy to a timestamped pre_activate backup; keep the 20260901 file read-only | later activations replace the live narratives with no backup |
| members | restamp_basis.py:47 | one-shot override has no guard tying it to the 2026-09-02 authorization | proposed: refuse unless old and new equal the 09-02 basis pair, or retire the script | a future basis mismatch could be stamped with a hardcoded REASON, defeating the fail-closed guard |
| members | refresh_member_profiles_20260903.py:269 | dated one-shot has no idempotence guard | proposed: refuse when provenance carries legacy_profile_refresh_20260908 or later, or move to attic | a re-run writes 09-03 prose back over Johnson, Scalise, Waters and Padilla |
| members | votesmart_npat_fetch.py:76 | re-running the retired collector would overwrite the Amendment-1 artifact | proposed: retire it, or refuse when OUTF exists without its own method and counts block | only a missing API key file stops a re-run today |

## 10. Ops: Task Scheduler logon type, behavioral one-run lag, Netlify site id and the 66 governance rows, WJ capture rule.

| Report | File:line | Issue | Proposed default | If Paul says no |
|---|---|---|---|---|
| collect | test_daily_media_refresh.py (press Step timeout) | press Step timeout 129600 vs test pinned at 72000 | proposed: TBD | report states no consequence; item stays as-is |
| root | weekly_refresh.py:502-511 | press and collection intake audit argv paths: anchor in build_press_engine_feed.py or re-pin weekly table | proposed: TBD | sweep change stays reverted; live path unverified (08-28 weekly log shows feed step OK) |
| speech | quarantine_logical_duplicates.py:66 | tie keeps shorter capture; contradicts keep-longer WJ rule (2026-08-25) | proposed: TBD | script stays retired as a one-shot (0 CSPAN duplicates today) |
| stance | build_golden_labels.py:33; prepare_stance_training.py:19 | default STANCE_LABEL_SET workbook path does not exist | proposed: restore the workbook to source_data/ or update the default path in both scripts | cu_golden_labels.csv (last built Jul 4) cannot be rebuilt |
| surfaces | build_approved_preview.py:36 | replaced builder still documented; would raise or overwrite live alias | proposed: retire it and update approved/README.md, or guard on the clean-workspace-v2 marker | builder raises ValueError on every run; on a tree without the alias it would overwrite the receipt-bound live alias |
| surfaces | make_lobby_network_html.py:4489 | stale responsiveness_layers.json (2026-09-12) still feeds 85 chips | proposed: load the artifact only when DESK_RESPONSIVENESS=1 | lobby-champions.html keeps 85 'asks N/M' chips from a stale artifact |
| wave1 PAUL_DECISIONS #1 | audits/wave1_20261019/PAUL_DECISIONS.md | Task Scheduler logon type for the refresh tasks (Interactive vs run whether logged on or not) | proposed: TBD (needs Paul's password at Task Scheduler, so Paul sets it) | tasks stay Interactive; a sign-out stops them (10-19 daily runs killed at 16:37 and 22:47) |
| wave1 PAUL_DECISIONS #2 | audits/wave1_20261019/PAUL_DECISIONS.md | accept or reject the one-run behavioral lag from the media-first reorder | proposed: TBD | if Paul says nothing the lag stays; rejecting means reverting the reorder and its stranded-binding protection |
| wave1 PAUL_DECISIONS #3 | audits/wave1_20261019/PAUL_DECISIONS.md | Netlify desk is stale (predates 10-10; 10-12 invited build never uploaded) | proposed: TBD | nothing deploys until Paul rules |
| governance | audits/deploy_20261011/GOVERNANCE_MATRIX.md; ops/release_config.json:29 | 66 governance rows, zero ticked; netlify.site_id is null | proposed: TBD (Paul rules every row; the matrix gives per-row recommendations) | deploy_desk.py keeps refusing with GOVERNANCE_PENDING; no invitee goes live (D-164) |

## 11. Unsorted

Held items that fit none of the ten themes.

| Report | File:line | Issue | Proposed default | If Paul says no |
|---|---|---|---|---|
| lobbying | lobby_position_join.py:144 | 35 conflicting keys ship an arbitrary first-in-file label | proposed: TBD | 35 conflicting keys keep an arbitrary first-in-file label |
| lobbying | classify_bill_positions.py:1018 | Monitor/Amend exemplar group picks 3 Amend, 0 Monitor (prompt design) | proposed: TBD | item stays as-is; report notes risk |
| lobbying | lobby_position_classify.py:235 | kim_fewshot_dir and kim_llm4_fewshot run zero-shot under a few-shot label | proposed: TBD | two arms keep running zero-shot under a few-shot label |
| stance | train_stance_domain.py:105 | --save writes to ROOT, production loads data/stance | proposed: TBD | retrain output stays unread; production keeps the July 4 model |
| legislation | run_greenlit_legislation_rank_shadow.py:134, 140 | adds two shadow-root inputs; changes shadow rank result | proposed: TBD | stays as an uncommitted sweep edit in the working tree |
| legislation | run_legislation_second_pass_dependents.py:668, 692 | timeout on run_child breaks a test fake (needs **kwargs) | proposed: TBD | stays as an uncommitted sweep edit in the working tree |
| legislation | run_legislation_dashboard_member_desk.py (freshness pin) | DESK_FRESHNESS_PIN not read by make_member_desk.py; placeholders left in shadow desk | proposed: teach make_member_desk.py to honour the pin, then land both hunks together | stays as an uncommitted sweep edit in the working tree |
| surfaces | build_audit_workbook.py:304 | scratch-keyed rollback copies and stale bindings accumulate | proposed: re-key in a finally; drop bindings[scratch_key] on failure; stable backup name | a ~619 KB scratch-keyed rollback copy accumulates per build (6 on disk) |
| research | test files modified in working tree (test_challengers.py, mpr/tests/*, others) | fixer-added tests and 3 modules modified but not committed | proposed: TBD | files stay modified and uncommitted in the working tree |
| members | big5_traits.py:123 | only first .dic loaded; licensed LIWC2015 may be ignored (precedence) | proposed: TBD | a licensed dictionary can be silently ignored |
| members | votesmart_npat_fetch.py:59 | cycles regex captures 19/20 instead of years | proposed: make the century group non-capturing so cycles records full years, with Paul's sign-off on the pinned collector | nothing consumes the field today; value stays wrong |

## Counts

Total sweep held items sorted: 119 (bulleted items in the 16 "Held for Paul" sections; the plan's estimate was about 130). Per theme, sweep items only: 1: 7; 2: 11; 3: 13; 4: 9; 5: 12; 6: 6; 7: 18; 8: 9; 9: 17; 10: 6; Unsorted: 11.

Theme 10 additionally carries 4 non-sweep rows (3 wave-1 decisions and the governance matrix), so theme 10 has 10 rows in total.
