# AUDIT FINDINGS — 2026-07-02 RUN 2 (Fable extensive audit + TRUE RUN-THROUGH)

Auditor: Claude Fable 5, `/fable-audit` runbook. Worktree `wizardly-jemison-171391` @ 9adc4c1 (== main HEAD, clean → audited code is exactly main).
Named `_RUN2` because `AUDIT_FINDINGS_2026-07-02.md` is the earlier constrained read-only audit (pre-phase-2 era: 28 tests / 50 audit checks) and is referenced as a canonical doc — not clobbered.
Data plane = live tree (`paths.py` ROOT default); worktree does not isolate data. Run-through executes worktree code (== main) against live data, per runbook.

## Baselines (Phase 1)
- kernel tests `fec/tests/run_tests.py`: **30 passed, 0 FAILED** ✅
- py_compile sweep fec/*.py (excl. attic): **70/70 ALL CLEAN** ✅
- `fec/audit_full.py`: **52 passed, 0 FAILED — ALL MODULES CLEAN** ✅

## Run-through gates (Phase 2) — ALL PASS
- (a) chain steps all OK, exit 0: ✅ 16/16 steps OK, `PIPELINE COMPLETE in 6.9 min` (view-cache-dead path; compute_pillars used the snapshot fallback — known-benign)
- (b) audit tail ALL MODULES CLEAN: ✅ (audit_full as final chain step, 139.6s)
- (c) rank delta vs pre-state: ✅ **0 rank deltas, 0 score deltas / 533 members**
- (d) engine artifact hashes vs pre-state: ✅ EXPLAINED — 7/8 changed (sizes ±1..63 bytes), 1/8 identical (per_topic_alloc_bridge.json, not chain-produced). Explanation is the known-benign TWO-RUN CONVERGENCE with hard evidence: weekly_refresh.log shows a refresh at 20:00:16-20:09:11 (CREC+CHRG+big5+social+**new congress_cosponsor_network_AUG20260702.xlsx at 20:00:44**+media blend 1666 cells) whose pipeline produced the pre-state artifacts; its late-chain col-G sync + bipartisan.json (~20:09) landed AFTER its engines ran, so THIS run's engines legitimately consumed the settled inputs. Zero rank delta (c) is consistent: press raw last changed 20:01, before both rank computations.
  **[CORRECTED by the post-fix verification, same night: "convergence" was the wrong model — the drift does NOT settle; it is a period-2 LIMIT CYCLE through the col-G→anti-prior recurrence (see S2-04, mechanism proven by sandbox probe). Input-driven and rank-immune as stated, but expect engine hashes to ALTERNATE between two byte-states on consecutive runs until S2-04 is resolved.]**
- determinism: ✅ budget_frontier ×2 (TOPIC=Interchange, FRONTIER_OUT→scratchpad) — **byte-identical MD5 9D7C06D27DE7B1F1300380A9BD78F9E9**, confirming (d)'s drift is input-driven, not stochastic.

## P5 UI smoke (preview browser, live tree via :8802; NO localStorage state left behind)
- cu-member-desk.html: ranked table renders (533 member rows; #1 = Tim Scott, Defender, 0.85); member detail opens with rank/ROI/radar incl. CU Tax Status; Staff accordion → **18 staff cards** with gold/★ toggles, note fields, "Mark contacted / Set up meeting / + Media" actions; In-contact panel renders (empty-state + export/import staff state). **Zero console errors/warnings.**
- Moneyball Dashboard.html: renders (19-issue selector incl. CFPB pair + Overall; Coalition/Flip modes; budget-frontier slider — knee $1150k, 45 seeds, spread 36→80; adaptive optimizer 107.5→129.6 = +22.1 flips; canvas network + targets list). In-page parity badge: **"engine ✓ flip 3.26 = py 3.25"**. **Zero console errors/warnings.**
- (preview_screenshot timed out on the 5MB canvas page — evidence above is DOM/a11y-snapshot + console, which is stronger anyway.)

## Fix lane (branch `audit/fixes-2026-07-02-run2`) — USER-RATIFIED implementation ("Implement fixes")
Inert lane (pre-ratification): b5eee3f unused `_m` import removed (run-1 S3-08); 6a0f57a port-8802 launch config.
Ratified lane (one commit per fix, py_compile per file, kernel tests 30/30):
- f830850 **S2-01** — press_stance_overrides.json via dump_atomic (kwargs pass through; user data never truncated in place).
- 84cc916 **S3-07** — post-override NEXT hint → `run_pipeline.py` (docstring + runtime print).
- 5ec5d27 **S2-02** — audit.py on `paths.py` (WORKBOOK, p); standalone rerun after: ALL CHECKS PASSED.
- a4fa2f8 **S2-03** — salience electoral-vuln guard: FileNotFoundError-only + loud `!!` print (receptivity pattern); corruption now crashes.
- 42a7955 **S3-01** — five chain writers → dump_atomic (byte-identical output); README atomicity claim scoped honestly.
- c90a530 **S3-03** — audit_full asserts sub-audit passed-count (>=22 / >=11, `>=` so growth is free); audit_frontier prints SKIP instead of silent pass (verified: audit.py prints exactly 22, frontier 11 in-chain).
- ba50a28 **S3-05** — bundle/desk announce missing engine inputs (`!!` prints); advisory guard narrowed Exception→FileNotFoundError.
- b3ff99c **S3-04** — doc pass: counts 28→30 / 50→52 (spec ×2, INDEX ×2), COM claim scoped to the pipeline, HALF vs HALFF disambiguated in dials, salience b-clamp documented. Docs→code direction only; no value changed.
- 1b0713b **S3-02** — assemble_viz legacy PERS table DELETED: re-examination showed it was dead code (defined L6, referenced nowhere), so the remap concern was moot and removal is provably inert. Post-fix smoke run clean (487 rows, imviz.json 24,589 B). PRO/ANTI camp sets left untouched — but note they predate the Defender tier (a col-G Defender is camped 'neu' in this diagnostics-only viz; user may want Defender ∈ PRO).
NOT implemented (needs a user decision): **S3-06** (weekly_refresh lock-abort behavior — design question, not a defect).
Verification (output-affecting protocol): kernel 30/30 ✅ · full pipeline + zero-delta + audit-clean: **see §Post-fix verification addendum**.

## Post-fix verification addendum (run 21:42–21:49, post-fix worktree code)
The previous session's verification run (20:52–20:59) completed through make_combined but died UNRECORDED with the session — its outputs were byte-identical (MD5) to the 20:03–20:06 pre-audit state, the first evidence of the A/B orbit below. This recorded rerun supplies the protocol proof:
- (a) chain: **16/16 steps OK, exit 0, PIPELINE COMPLETE in 5.8 min** ✅
- (b) audit tail: **audit_full.py OK — ALL MODULES CLEAN (112.9s)** ✅ (includes the S3-03-hardened sub-audit count gates)
- (c) rank delta vs pre-state (20:55 ranks_python.json): **0 rank deltas, 0 score deltas, 0 missing/extra of 533** ✅
- (d) engine artifact hashes: 7/8 changed ±1..63 bytes, bridge identical — **NOT caused by the fixes**: the four-run hash record (weekly refresh ≈A → run-through ≈B → orphan verify =A byte-exact → this run ≈B) spans pre-fix AND post-fix code with the same orbit; mechanism isolated and proven as **S2-04** (sandbox probe: 39 tier cells / 55 score floats flip per half-cycle; ranks immune both transitions).
- kernel tests after the final fix (S3-02): **30 passed, 0 FAILED** ✅ · S3-01's converted writers exercised end-to-end by this run (all consumers parsed them; audit clean); engine determinism stands on the audit-phase frontier double-run (byte-identical MD5).

## Findings
(S1 corrupts/crashes/unexplained delta · S2 silent wrong-number · S3 hygiene)
**Counts: S1 = 0 · S2 = 4 · S3 = 7** (S2-04 added during post-fix verification; S3-06 is a design question, not a defect)

### [S2-01] fec/apply_press_overrides.py:43 — non-atomic in-place rewrite of the USER-OWNED overrides registry
Evidence: `json.dump(doc, io.open(OVR, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)` — `OVR` = press_stance_overrides.json, the canonical merge target for the user's dashboard stance corrections (L30-43 merges then rewrites in place).
Impact: unlike every other json.dump target in the repo, this file is NOT regenerable pipeline output — it is the user's accumulated press-stance corrections (user's domain). `open(...,'w')` truncates first; a crash/kill/disk-full between truncate and flush destroys the registry. No backup copy is taken first (workbook writers do backup-first; this doesn't).
Remedy: use `moneyball_core.dump_atomic(doc, OVR, ensure_ascii=False, indent=2)` (drop-in), optionally with a timestamped copy into `backups/` before the merge.

### [S3-01] Five canonical-chain writers still non-atomic; README claims "all writes are atomic via MC.dump_atomic"
Evidence: raw `json.dump(..., open(...,'w'))` in per_category_stance.py:116-117 (category_stance.json), receptivity_layer.py:74-76 (member_receptivity.json), budget_frontier.py:120 (budget_frontier*.json), salience_shock.py:249 (salience_advisory.json), make_member_desk.py:502-504 (member_desk_bundle.json, io.open direct). README.md L15: "all writes are atomic via `MC.dump_atomic`" — false for these five. (Data-refresh-layer writers — big5_traits, social_interaction_layer, press_engagement_layer, press_hcoi, build_electoral_history, build_social_master, sna_layout, tweet_collector L265, frame_alignment — are also raw, but run manually/rarely.)
Impact: kill/crash mid-write leaves a truncated artifact; the next consumer fails LOUDLY (JSONDecodeError), so this is availability not silent-wrong-number — but it is exactly the failure class dump_atomic was built for (S2-03, audit run 1), and the doc overstates coverage. OneDrive can also sync a half-written file.
Remedy: convert the five chain writers to `dump_atomic` (mechanical, kwargs pass through); or amend README L15 to name the atomic subset.

### [S3-02] fec/assemble_viz.py:6 — residual legacy PERS table shadows the kernel's ratified persuadability
Evidence: `PERS={'Neutral':1.0,'Skeptic':0.85,'Unengaged':0.55,'Ally':0.45,'Champion':0.20,'Opponent':0.10}` — pre-refactor tier scheme (no Defender/Highly Persuadable/True Neutral/Lean Skeptic/'—'; Ally=0.45 vs kernel 0.40, and inverted magnitudes: legacy treats Neutral as MOST persuadable=1.0 while kernel PERS['Neutral']=0.50). File imports the kernel as MBC on L2 yet keeps its own copy — exactly the drift class the refactor removed elsewhere (runbook expectation: no copies outside core except sync_stance_clean.py).
Impact: imviz.json only (README-confirmed diagnostics-only, no live consumer) — a human reading the viz sees persuadability colored by the retired scheme. No rank/engine effect.
Remedy: `PERS=MBC.PERS` (or delete the local table and read from MBC) — but note the tier vocabularies differ; if the viz predates the new taxonomy it may need remapping, so flagged rather than fixed.

### [S2-02] fec/audit.py:5,11,48,71,72,73 — six hardcoded absolute live-tree paths bypass paths.py; under MONEYBALL_ROOT relocation the integrity sub-audit silently validates the WRONG tree
Evidence: `M=r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx'` (L5); same literal root in L11 (ranks_python.json), L48 (congestion.json), L71-73 (im_allocation / per_topic_alloc / per_topic_coalition). Every other live script resolves through `paths.py` (whose docstring names `MONEYBALL_ROOT` as the supported relocation mechanism).
Impact: inert in today's default config. But if the project is ever run under `MONEYBALL_ROOT` (the documented escape from OneDrive), the pipeline reads/writes the new root while audit.py — the "integrity (22)" leg of audit_full — keeps auditing the OLD tree and reports clean against stale artifacts. Silent wrong-audit, which is worse than a crash.
Remedy: `from paths import ROOT,WORKBOOK` + join, mechanical 6-line diff.

### [S2-03] fec/salience_shock.py:57-60 — whole-file-missing/corrupt electoral_plays.json silently neutralizes electoral vulnerability (no warning print), unlike the ratified loud-guard pattern
Evidence: `try: _ep=json.load(open(B+r'\electoral_plays.json',...)); vuln={...1.35 if play in ('defend','contest')...} / except Exception: vuln={}` → `VULN=lambda m: vuln.get(m,1.0)`.
Impact: salience_advisory.json (and the bundle's GO PUBLIC/quiet-work calls + "holds N" defensive appeals) computed without the ×1.35 electoral-gamble amplifier for every defend/contest member, with zero failure signal. receptivity_layer.py got exactly this remedy in run 1 (`!! ... MISSING/EMPTY` prints at L44/L48); this sibling site was missed. `except Exception` (not FileNotFoundError) additionally swallows a corrupt/truncated file.
Remedy: mirror the receptivity guard — catch FileNotFoundError only, and print `!! electoral_plays.json MISSING — VULN neutral (run build_electoral_plays.py)` when vuln=={}.

### [S2-04] fec/per_category_stance.py:9,32,57 (+ sync_stance_g.py step-order) — col-G feedback puts the stance matrix on a period-2 limit cycle: ~39 persuadable-middle tier cells flip on EVERY consecutive pipeline run with zero input change
Evidence — mechanism: L9 `gen={ra.cell(r,1).value:ra.cell(r,7).value ...}` reads workbook col G, which the PREVIOUS run's sync_stance_g wrote (sync is chain step 4, stance is step 2 — so stance always consumes last run's overall tiers); L32 `anti={m:max(clip(-opl[m]/ascale), ANTI_STANCE.get(gen.get(m),0.0))}` floors the anti-prior for members whose previous OVERALL tier was Opponent(1.0)/Skeptic(0.5); L57 `c*=(1-0.70*anti[m])` damps press-silent positive scores. Hence stance_N+1 = F(stance_N), population-coupled through the ascale/p80 pools and the shaped_cut quantile+rate clamps — boundary members flip in unison.
Evidence — observed orbit (four runs, identical data): engine-artifact MD5 state **A** (weekly refresh outputs, ~20:03-20:06) → **B** (audit run-through, "7/8 changed ±1..63 B") → **A byte-exact** (orphaned verify run, 20:55-20:58 — all seven MD5s equal the 20:03 set) → **B** (recorded verify run, 21:43-21:47). Determinism is NOT in question: the audit-phase frontier double-run was byte-identical on fixed inputs.
Evidence — sandbox probe (MONEYBALL_ROOT → scratch copy of the CURRENT workbook + archive_leg + vote_category_lean; zero live-tree writes): fresh stance output vs live category_stance.json = **39 tier diffs / 55 score-float diffs**, all in the persuadable middle — e.g. James McGovern ×6 categories (True Neutral↔Highly Persuadable↔Ally), Chellie Pingree ×4, Frederica Wilson Data Privacy True Neutral→Ally, Adam Smith MBL Highly Persuadable→True Neutral. No Champion/Defender/Opponent anchor moves.
Impact: tier labels for ~0.4% of the 533×18 matrix — and every consumer of `['matrix']`: per-topic flip/coalition $ allocations, frontier seeds/gates, salience advisory, dashboard/desk colors — depend on run PARITY rather than data. Ranks are provably immune (compute_pillars reads press only; 0/533 across both A→B transitions tonight). Byte-stability audits (gate d) can never settle while the orbit persists. Run-1's "two-run convergence" known-benign note described a fixed point that existed THEN; tonight's media-blend refresh (1666 press cells changed) perturbed the system onto a cycle — latent design property, not a regression (pre-fix and post-fix code orbit identically).
Remedy (user decision required — stance semantics are ratified): (a) cheapest: snapshot `gen` once per DATA refresh (weekly_refresh dumps overall_tier_snapshot.json; per_category_stance reads the snapshot, not live col G) → pipeline idempotent between data changes; (b) ε-hysteresis at shaped_cut boundaries (tier changes only when clearing a cut by ε) → kills flapping in general; (c) within-run stance↔sync fixed-point iteration with damping (heaviest). **Questions for the user:** which phase (A or B) should be canonical this week, and should the oscillating ~39-cell set be pinned via overrides until (a)/(b) lands?

### [S3-03] fec/audit_frontier.py:57-63 + fec/audit_full.py:16-18 — an audit check can silently vanish; the harness only asserts "0 FAILED", not check COUNT
Evidence: audit_frontier wraps the contest-gates-party-blind check in `try/except FileNotFoundError: pass` (L63); audit_full's sub-audit gate is `m.group(2)=='0'` on the tail line — the "(11)"/"(22)" in the label is display text, never enforced.
Impact: if member_receptivity.json is absent the frontier sub-audit passes 10/10 and audit_full still prints "frontier (11) sub-audit clean". Any future regression that deletes/skips checks passes unnoticed. Audit-of-the-audit hygiene.
Remedy: audit_frontier prints an explicit `SKIP` line instead of pass; audit_full asserts the parsed passed-count matches the expected number embedded in the label.

### [S3-04] Documentation rot cluster (spec/INDEX/tool-hints vs live code) — report-only, both directions, per runbook P4
1. MATHEMATICAL_SPECIFICATION.md L24 "(28 checks)" and L76 "(28)" — kernel suite is 30 (run 1 added 2). INDEX.md L7 "28 kernel checks", L21-22 "audit 50/50 clean" — now 30 / 52.
2. Spec L54 "There is NO COM anywhere" — true for the run_pipeline CHAIN (verified: no chain script imports win32com), but ELEVEN live manual tools still drive Excel COM (apply_committee_fix, apply_leg_stance, apply_alloc_cap, apply_committee_reweight, apply_raw_max_norm, apply_press_overrides, apply_weights, apply_press_dedup, apply_stance_guard, sync_stance_clean, write_im_sheet — all graceful `xl.Quit()` in finally, no force-kill). The COM+OneDrive failure class phase 2 retired remains reachable through these manual lanes.
3. Spec §Standing dials lists `HALFF=0.10` (flip family) but omits the DISTINCT near-namesake `HALF=0.10` env of money_response.py:14 — the name collision is a live foot-gun (setting the wrong one no-ops silently).
4. Spec salience row says "b=0.05+0.10ψ"; code is `b=min(0.35, BACKFIRE0+BACKF_PSI·ψ)` (salience_shock.py:101) — clamp undocumented.
5. Run-1 report L144 says "S2-03 dump_atomic at all 14 sites" and README L15 says all root-JSON writes atomic — five chain writers remain raw (see S3-01); the "14 sites" set was narrower than "all writers".
6. README L38 says audit_full = "52 checks" ✓ (accurate); INDEX verification section still describes the pre-phase-2 recalc flow wording but is materially right.

### [S3-05] Dashboard/desk builders render silently-empty sections when engine inputs are missing or corrupt
Evidence: build_dashboard_bundle.py:179 `BF=json.load(...) if os.path.exists(...) else {'topics':{}}`; L187 `OPT=... else None`; L225-232 advisory `except Exception: pass` → engine['adv']=['','',...]; make_member_desk.py:45 `OPT = L('optimize_result.json') or {}`.
Impact: canonical chain order makes these unreachable in-pipeline (producers run first); a manual/out-of-order run quietly ships dashboards with empty frontier/optimizer/advisory sections — user sees "no data" where there should be numbers, no error anywhere. The L225 `except Exception` also masks schema drift (KeyError) forever.
Remedy: narrow to FileNotFoundError + one loud print per skipped section (pattern already ratified in build_multilayer_network).

### [S3-06] fec/weekly_refresh.py — Sunday 06:00 unattended run aborts ALL dashboard regeneration if the workbook is locked at the sync step (only the media-blend lock is gracefully tolerated)
Evidence: docstring L14-15 covers Excel-lock tolerance for build_media_blend only; `step('FULL PIPELINE + dashboards',['run_pipeline.py'],...,hard=True)` — sync_stance_g.py inside the chain PermissionErrors on a locked workbook → run_pipeline exits 1 → hard abort, logged, no dashboards that week.
Impact: Excel left open over a weekend = stale dashboards + a log line nobody may read. Not a defect (fail-loud is defensible); flagged as a DESIGN QUESTION: should weekly_refresh fall back to regenerating dashboards from the previous consistent state (resume `--from per_topic_flip`) when only the workbook write is blocked?

### [S3-07] fec/apply_press_overrides.py:109 — post-run "NEXT:" hint predates phase 2 and skips the rank-authority recompute
Evidence: `print('\nNEXT: python fec/make_member_desk.py   then   python fec/make_combined.py ...')` after COM-updating Press Raw + CalculateFull + Save.
Impact: press overrides change the press pillar → ranks. Following the hint regenerates the member desk from the UNCHANGED ranks_python.json (phase-2 authority), i.e. pre-override ranks presented as fresh. The correct next step is `python fec/run_pipeline.py` (stance → compute_pillars --write → engines → dashboards).
Remedy: update the hint string.

## Notes / observations (non-findings)
- Kernel `blocks`/`BLOCKCAT`: 18 block columns over 17 categories (99+145 both CFPB); `CU Tax Status` has IMP weight 3.0 but no stance block — matches "18th cat, data pending" state.
- README says kernel tests "currently 30"; spec §Regeneration still says "(28)" — folded into S3-04.
- Worktree @ 9adc4c1 == main, clean → audited code is exactly main.
- Run-1 S2-01 (bipartisan from AUG graph) remediation VERIFIED in place: build_dashboard_bundle.py:95-101 computes BP from the newest non-AUG cosponsor file, `BP_SRC=aug` dial documented, bipartisan.json written via dump_atomic (L248). Not re-flagged.
- MC-alias discipline holds: cascade engines import the kernel as `MBC`; flip/pillar family use `MC` and none has an `MC` Monte-Carlo env read (verified per_topic_flip/flip_model — closed-form). No shadowing.
- Kernel-drift sweep: `sm64`/`cpf_*` definitions ONLY in moneyball_core ✓; PERS/IMP/BLOCKCAT/SGATE copies only in attic + hard-guarded sync_stance_clean.py (known exception) + assemble_viz.py legacy PERS (S3-02).
- Bare `except:` — attic-only ✓. Live broad `except Exception` sites triaged; load-bearing ones are S2-03/S3-05; the rest are per-row collector tolerance (build_media_blend:69, tweet_collector) or deliberate iteration (compute_pillars:78 backup-candidate loop).
- `per_topic_alloc_bridge.json` (root, 2026-06-26) is a write-only variant produced ONLY under `--bridge`/`BRIDGE=1` (per_topic_flip.py:82); zero live consumers — stale copy inert. Not in README's diagnostics-only list; could be added.
- Whole-file-missing guards confirmed still loud: build_multilayer_network L62/76/98, receptivity_layer L44/48, compute_pillars snapshot/bootstrap prints, moneyball_core.pillar_scores raises with instructions.
- `python -m http.server 8801` (PID 31056, since 19:35) = dashboard server, not a writer; no interference with the run-through.
- Pre-run artifact mtimes show a full pipeline completed ~20:03-20:06 tonight → gate (c)/(d) expectation is byte-identical regeneration (no input changed since; two-run convergence already settled).
