# RESEARCH INTEGRATION -- EFFECTIVENESS REFERENCE SHEET 2026-08-14

STATUS: LIVING MEASUREMENT REFERENCE (companion to RESEARCH_INTEGRATION_UNIFIED_2026-08-14.md).
This sheet is the single place to answer: "is each adopted addition succeeding, and is the
system it landed in still healthy?" It holds baselines, success bars, the measuring
instrument, cadence, and a measurement log per item.

## 0. How to use this sheet (binding rules)

1. BASELINES are dated facts with window + denominator; never overwrite one -- a re-measured
   value is a NEW row in the item's log.
2. BARS here are REFERENCE DRAFTS. For research-look items (class MODEL-CHANGE) the LOCKED
   prereg supersedes this sheet's numbers the moment it locks; this sheet then mirrors the
   locked bar verbatim. Changing any bar is Paul's, via prereg lock or explicit ruling.
3. ONE-LOOK items are measured ONCE. Their row records the single RESULT (PASS / MISS /
   FRAGILE=MISS / RETIRED WITHOUT A LOOK) and is never re-scored. Repeatable counters
   (coverage, join rates, usage) may be re-measured on cadence.
4. SUCCESS has two components, always both: the item's own bars AND the guardrails (section
   1) holding. An addition that hits its bar while a guardrail regresses is a FAILURE.
5. A retirement or MISS recorded with evidence is a DISCIPLINE SUCCESS for the program even
   though the item died -- log it as such (section 2's program metrics count both).
6. Measurement log rows are append-only: date | value (window/denominator) | evidence pointer
   (commit, artifact, glassbox run id) | measured-by.

## 1. Guardrail invariants (measured at EVERY implementation gate, all items)

| ID | Guardrail | Baseline (2026-08-14) | Bar | Instrument |
|---|---|---|---|---|
| G1 | Kernel tests | 154 passed / 0 failed at 846d90ae3 (live-tree lineage; 153/0 recorded 2026-08-13 pre-merge) | count never decreases; 0 FAIL | python fec/tests/run_tests.py (live tree) |
| G2 | Full audit | 202 passed / 1 FAILED, the 1 being the Paul-gated legfix5 culling item | no NEW fails; the legfix5 item stays Paul's | python fec/audit/audit_full.py |
| G3 | Rank stability | ranks_python.json hash at gate time | byte-identical across any non-rank change; rank-class changes use the full 2026-08-12 verification protocol instead | Get-FileHash + rank_delta.py |
| G4 | Glassbox visibility | emitter live | every job of every item emits (run/task/agent pairs) | events dir + viewer |
| G5 | Mirror durability | mirror remote live | branch pushed at every commit gate; main pushed at every merge gate | git push mirror |
| G6 | JS-mirror parity | dashboard mirrors engine constants | any ratified engine change lands with its matching template edit or is not ratified | template diff at review |
| G7 | Data-plane hygiene | -- | new artifacts land consumed-by-NOTHING (.candidate / new dirs) until promoted | review + grep of consumers |

## 2. Program-level effectiveness (the additions in aggregate)

| ID | Measure | Baseline (2026-08-14) | Target direction | Cadence |
|---|---|---|---|---|
| PR1 | Valence-hop accuracy (the named bottleneck) | 0.689 on the 400 adjudicated tweet golds (fec/stance/apply_two_hop_stance.py:4-5, re-verified 2026-08-14) | up, toward/past the 0.872 compose ceiling on FRESH gold | at F1 look; then per gold refresh |
| PR2 | Weekly override burden | capture at F2 start from press_stance_overrides.json history (baseline row to be added) | down over >= 4 weekly refreshes | weekly |
| PR3 | Corpus coverage beyond finance | CHRG hearings finance-only (2026-07-10 record); committee-report texts: none | non-finance hearing + report channels exist with measured floors | at B3 gates |
| PR4 | Freshman-readiness (120th) | pre-office text for incoming freshmen: none | >= 85% of seated 120th freshmen carry pre-office text at seating 2027-01-03 | monthly from lane start |
| PR5 | Lobbying-edge recall | LobbyView-derived links only (single source) | dual-source with adjudicated disagreement ledger | at B0/B1 gates |
| PR6 | Discipline ledger | looks consumed to date: per big5_methods; no look consumed on a battery-refusable design in this program | every look in this slate preceded by a passed battery; retirements recorded with pinned successor gates | per look |
| PR7 | Psychometrics gate motion | raw reactivity_z coverage 270/533 (live tree, 2026-08-14); MEM_N (intersection with the 456-member eligible roster) UNCOUNTED; gate = 250 | MEM_N counted (menu item 7); if >= 250, the N-route successor prereg becomes lockable | at menu ruling; then per interview-collection cycle |
| PR8 | Prospective outcome harness | outcome_snapshot_2026-07-04.json frozen; scoreable ~2026-09-02 if >= 150 movers; bars rho >= +.20 PASS / +.10 DIRECTIONAL / <= -.10 INDICTED (in-file, re-verified 2026-08-14) | scored at horizon exactly as frozen; verdict recorded whatever it says | once at horizon; new freezes as ruled |
## 3. Per-item scorecards

Format per item: BASELINE (dated, with denominator) / SUCCESS BARS (draft unless marked
LOCKED) / INSTRUMENT / CADENCE / LOG (append-only). Class in brackets.

### C1-2026 -- campaign-site collection for the 120th freshman corpus [DATA]
- BASELINE: 0 pages held for the 2026 cycle; CampaignView coverage context: winners' web
  presence ran 88.3% (platform) / 99.0% (biography) among general-election winners in
  2018-2022 (paper p.7, denominators = general-election winners per cycle).
- BARS: >= 85% of the general-election universe (~870 House + Senate class, both parties)
  collected with bio + issues subpages before the November 2026 election; 100% of collected
  pages carry per-page provenance (URL, timestamp); post-election: pre-office text held for
  >= 85% of members actually seated 2027-01-03.
- INSTRUMENT: collection manifest counts (script-emitted, glassbox-logged), spot audit n=25.
- CADENCE: weekly September-October 2026; final measure at seating.
- LOG: (empty -- lane not authorized)

### B0 -- BICAM acquisition + arrival audit [DATA; prerequisite of B1/B2/B3/B4]
- BASELINE: no BICAM holdings; internal-consistency caution recorded (408,000 vs 421,764
  bill-count discrepancy in the paper itself).
- BARS (pre-declared, from SOURCE 2 P1): roster join 533/533 bioguides (every miss named);
  act-universe join >= 640/644 bill_ids with every miss adjudicated; text-presence agreement
  >= 95% vs the 18,557-bill legfix5 store with a classified disagreement sample n >= 50;
  cosponsor-count agreement within +/-2% on a pinned 100-act sample; snapshot sha256-pinned
  with row counts recorded per component.
- INSTRUMENT: arrival-audit script (read-only over the snapshot + repo artifacts), report
  with denominators.
- CADENCE: once at arrival; repeated per BICAM refresh adopted.
- LOG: (empty -- acquisition not authorized)

### M1 -- embedding record linkage for the mentat trade-association resolver [TOOLING]
- BASELINE: exact-name resolver produced $0 rows for known-active trade associations
  (fault class recorded 2026-07-27).
- BARS: precision >= 0.95 on a hand-checked stratified sample of n=200 resolver decisions;
  every sub-threshold match human-reviewed (the CampaignView operating point); recall gain
  over exact-name reported with denominators (no bar -- recall is the point, precision the
  guard); zero silent $0 rows for the Paul-listed roster after deployment.
- INSTRUMENT: resolver eval script + review queue; mentat workbook diff on affected rows.
- CADENCE: once at build; re-run per mentat refresh.
- LOG: (empty)

### F2/F4 -- FOL rationale tooling in adjudication queues + onboarding proposer [TOOLING]
- BASELINE: queues carry no machine rationale column; PR2 override baseline captured at start.
- BARS: F4 retrospective $0 check -- proposer agreement with ALREADY-SETTLED registry
  entries reported with denominators (reference expectation >= 0.80 agreement to be useful;
  grounds no claim about future targets, stated as such); F2 -- Paul's qualitative verdict
  after one queue batch + PR2 trending down over >= 4 weekly refreshes.
- INSTRUMENT: agreement script vs cu_valence_registry.json; press_stance_overrides.json
  counter; Paul's word.
- CADENCE: retrospective check once; PR2 weekly.
- LOG: (empty)

### E3 + S3 -- $0 structure probes into the coalition-builder lane [DIAGNOSTIC]
- BASELINE: existing community layers (HCoI/press) only.
- BARS: none (probes). DELIVERABLE = adjusted-Rand comparison + discrimination counts with
  denominators, filed as notes to the gated coalition-builder lane. A near-identical or
  non-discriminating result is a recorded negative, logged here, and the items die free.
- CADENCE: once each.
- LOG: (empty)

### F1 -- FOL-CoT valence-hop candidate [RESEARCH LOOK -- ONE MEASUREMENT]
- BASELINE: valence-hop 0.689; stance-hop 0.915; compose ceiling 0.872 (400 adjudicated
  tweet golds; code line re-verified 2026-08-14).
- DRAFT BARS (lock at prereg): on a FRESH Paul-adjudicated gold batch (n >= 150, labels
  collected AFTER method freeze): valence-hop accuracy >= 0.75; macro-F1 >= recomputed
  same-batch compose baseline; exact permutation p < .05; zero registry-covered items
  overridden (hard zero); ceiling-beat claims require composed accuracy above the
  0.872-equivalent on the fresh batch. Honest-prior note: the paper's +6.4 zero-shot gain
  carries contamination risk -- prereg discounts it. Battery: label-permutation null at
  chance; registry-leakage check; target-swap confound check. PASS requires adversarial
  re-derivation; FRAGILE = MISS.
- INSTRUMENT: fec/stance/stance_eval.py against the fresh gold; locked look script.
- CADENCE: ONCE. Post-adoption drift (if promoted) rides PR1 per gold refresh.
- LOG: (empty -- prereg not drafted)

### C2 -- cross-context trait-stability corroboration [RESEARCH LOOK -- ONE MEASUREMENT]
- BASELINE: no cross-context agreement number exists for any trait; overlap roster and
  per-trait coverage UNCOUNTED (the Stage-2 $0 count is the first act).
- DRAFT BARS: power arithmetic FIRST -- if honest power < ~80% against a plausible
  stability effect at the counted overlap n, the look is labeled CORROBORATION with tiered
  wording or a data gate is pinned instead of locking; gender and party partials are GATING
  bars; battery precedes any look and its refusal retires the round (logged as RETIRED
  WITHOUT A LOOK with pinned successor gate -- a valid outcome).
- INSTRUMENT: existing validated instruments applied unchanged to both corpora; per
  psychometrics-reference machinery.
- CADENCE: ONCE per locked round.
- LOG: (empty)

### S1 -- signed trust/distrust edge completion [RESEARCH LOOK -- BATTERY-FIRST]
- BASELINE: multiplex carries observed edges only; no propagated edges anywhere.
- DRAFT BARS: planted-edge battery -- recovery of removed KNOWN edges and refusal of
  planted nulls at rates pre-declared in the prereg (reference: recovery >= 0.80,
  false-accept <= 0.10 on the pinned synthetic design); only a passed battery unlocks the
  look: external criterion (post-freeze cosponsorship adoption or observed money flows,
  pinned in advance) with the unsigned/absent-edge ablation as comparator under CRN.
- INSTRUMENT: new battery script (kb_benchmark pattern, redirected outputs).
- CADENCE: battery once; look ONCE if unlocked.
- LOG: (empty)

### E1 -- stance-cell imputation [RESEARCH LOOK -- CONDITIONAL on menu item 6]
- BASELINE: '-' cells = 59.8% of the 533x18 matrix at the 2026-07-09 vintage (re-count at
  prereg if admitted); PERS_NONE=0.45 Ally-parity pricing is user-ratified design.
- DRAFT BARS (only if Paul rules the desert-fill precedent extends): on masked KNOWN cells,
  beat global-mean AND party-mean AND row/col-marginal baselines (party-mean = homophily
  gate) AND the existing pflip network-proximity prediction (redundancy gate); every
  derived metric reported real-cells-only beside augmented; IMPUTED flag everywhere; true
  '-' never silently overwritten.
- CADENCE: ONCE at look; if promoted (display-first), mask-recovery re-checked per stance
  refresh.
- LOG: (empty -- awaiting ontology ruling)

### B2 -- BICAM rollover backbone [DATA; rollover-campaign-gated]
- BASELINE: roster/committee crosswalks hand-stitched from voteview/legislators.csv.
- BARS: 119th-Congress reconciliation EXACT -- BICAM members reproduces the 533 roster
  (with delegate/commissioner filtering proven); committee-code crosswalk coverage 100% of
  live committees or misses adjudicated; adoption itself only through the rollover
  campaign's own validation bars (533 invariant, pinned totals, workbook row drift).
- CADENCE: reconciliation once now; adoption measures at rollover rehearsal and at seating.
- LOG: (empty)

### B3 -- hearings/reports/witness expansion [DATA -> candidate LAYER]
- BASELINE: CHRG hearing collection finance-only (2026-07-10 record); committee-report
  texts absent; no witness-appearance table.
- BARS: PRE-INGEST -- transcript presence >= 70% measured on the 533's committees'
  hearings, 117th-119th window (below floor -> partial-channel with per-figure caveats);
  POST-INGEST -- per-member attribution rate reported with denominators; witness table
  coverage stated per-Congress (114th+ only, named on every figure); any witness EDGE
  faces the S1-class planted-edge battery before kernel contact.
- CADENCE: presence audit once; attribution per collection cycle.
- LOG: (empty)

### E2 -- three-way triage + minimum-cost dual diagnostic [DIAGNOSTIC]
- BASELINE: no explicit defer-region artifact; allocator answers max-value-under-budget only.
- BARS: stability -- partition agreement >= 90% of members unchanged across SEED in
  {7,1,13} and MC=20 vs MC=100 under CRN (else shelved as unstable, logged); consistency --
  minimum-cost answers within one $500 INC grid step of the frontier's inverse read on
  >= 90% of a pinned topic x threshold grid, disagreements enumerated; UAC construct
  sensitivity-swept (receptivity_sensitivity pattern) and flagged design-choice until
  frontier P2 delivers outcome grounding; zero-rank-delta proof on every run.
- CADENCE: at build; re-run after any engine-constant ratification.
- LOG: (empty)

### C3 / C4 / S4 -- display line, gold QA resample, annobib [TOOLING/DOCS]
- C3: ships only per-surface with Paul's mockup approval; measure = provenance-labeled
  render with the Economics-and-Commerce bucket named honestly; no other bar.
- C4: measure = agreement + correctly-computed kappa on Paul's ~20% resample (import the
  DESIGN, not the paper's arithmetic -- their printed kappa exceeds their agreement, which
  standard Cohen's kappa cannot do); his current ruling stays final on disagreement.
- S4: measure = annobib entries present with honest-analogical wording; docs-duty checklist.
- LOG: (empty)

## 4. Measurement log conventions + open questions

Append rows as: `| YYYY-MM-DD | item | value (window/denominator) | evidence | by |` under
the item's LOG line. Never edit prior rows; corrections are new rows naming the old one.
OPEN at creation: PR2 override baseline uncaptured; MEM_N intersection uncounted (menu 7);
kernel-count wording pinned to the 846d90ae3 lineage (re-capture G1 at first gate).

-- end of sheet (living; bars lock only in preregs; appends only) --
## 5. MEASUREMENT LOG (append-only; format per section 4; newest last)

| date | item | value (window/denominator) | evidence | by |
|---|---|---|---|---|
| 2026-08-14 | rulings | menu items 1-7 APPROVED by Paul | RESEARCH_INTEGRATION_UNIFIED_2026-08-14.md section 7; brain D-009/D-010 | claude |
| 2026-08-14 | PR7 / MEM_N | MEM=472 (sect-17-eligible via load_corpus), MEM_N=260 >= gate 250 MET (was 201 at round-4 lock); raw reactivity_z 270/533 | metaloop run-20260814T1552374698259Z-b00ea83fd1, N2 command in transcript | claude |
| 2026-08-14 | M1/F2/B0 builds | 6 files landed @6d5303774, 45/45 tests green (12 M1 + 14 F2 + 19 B0), flag-gated OFF, consumed by nothing | metaloop run-20260814T1552374698259Z-b00ea83fd1; codex lane; coordinator-run suite | claude+codex |
| 2026-08-14 | review debt | Codex adversarial second-review round DEFERRED to the pre-merge gate (context budget); recorded, not skipped | this log row + PDF change report sect. 3 | claude |
| 2026-08-17 | PR7 MEM_N gate (independent recount) | MEM=472; MEM_N=260; raw 270/533; GATE MET -- convergent with the 08-14 metaloop row via a separate load_corpus run | live-tree read-only run, glassbox run-now-tier-20260817 (count_mem_n.py) | Fable 062ce9 lane |
| 2026-08-17 | (note) | PR7's "MEM_N uncounted" open item in section 4 is closed; N-route successor prereg LOCKABLE -- locking and the look remain Paul-gated | -- | Fable |
| 2026-08-17 | E3+S3 probes | S3: NOT DISCRIMINATING as instrumented (overlap 153/533 = coverage artifact; covered>=2 stratum 153/153 one status; structural signal = 13 multi-echo members). E3: DEGENERATE (theta 0.0657 admitted all 533 as centroids; 334 clusters, 251 singletons; ARI -0.001/0.000/0.004 vs hcoi/k2/party) -- Zhan-Cai distance presumes dense trust matrix, fails on sparse observed-edge network. BOTH DIE FREE. | audits/STRUCTURE_PROBES_DESIGN_2026-08-17.md RESULT blocks; glassbox run-now-tier-20260817 | Fable |
| 2026-08-17 | B0 pre-arrival caveats | MIT asserted in paper/Dataverse/package but NOT restated on bicam.net at point of download; three mutually inconsistent size tables (trust datasets.py -- it carries sha256s); package congress_range says bills 93-118 vs site "6th-present" -- 253 of our 644 acts are 119th, so per-congress strata adjudicate currency; Dataverse copies STRIPPED of raw_text (bicam.net only for texts); data last updated 1/25/2025 | recon workflow wf_6cdf7d59-505 (2 read-only agents) | Fable |
| 2026-08-17 | dedup (post-merge) | Parallel-lane duplicates resolved on one branch: canonical = fec/tools/b0_bicam_arrival_audit.py (tested, 19 B0 tests), CAMPAIGN_SITE_COLLECTION_2026_RUNBOOK.md, stance_valence_folcot_prereg.md; deleted the three 062ce9-lane duplicates after folding deltas (housegov incumbent substitution, n=10 smoke gate, sha256 revision-diff; paired-design + analysis-plane-only + extra adverse priors in the prereg). Residual: per-congress strata REPORTING + explicit non-bill exclusion labeling in the B0 tool -> assigned to the deferred Codex second-review round. | this commit | Fable |
| 2026-08-17 | B0 arrival audit RUN | Tool verdict FAIL, decomposed: roster 485/533 (48 misses = the 119th freshman class -- REAL BICAM currency finding, members end at 118th); act-join 38/644 + text-overlap 0/18,557 = TOOL key-normalization defects 6-7 (not data verdicts); cosponsor agreement PERFECT where aligned (420/420, ratio 0.0000, n=37 < 100 floor). Zips sha256 6/6 MATCH. 3 damaged legfix5 receipts found (119:hr:2393/2397/2401, 1330B binary each) -> legfix5 lane. html_file patch landed, 19/19 tests. Full record: audits/bicam_arrival_20260817/ | this commit; glassbox run-bicam-acquisition-20260817 | Fable |
| 2026-08-17 | B0 arrival audit RUN 2 (post-fix) | Normalization fixes landed (float-congress parse + canonical key conversion; 22/22 tests): pre-119th bills join 319/319 (100%); pre-119th text agreement 98.65% (n=11,474) ABOVE bar on the honest stratum; cosponsors PASS 1,288/1,288 ratio 0.0000 (n=304 acts); remaining FAILs are real: 48 freshmen absent (members = early-118th vintage -- CORRECTED wording), 141 119th bills beyond the 1/25/2025 sliver, 173 amendments out of component scope. Bar recalibration (per-stratum) -> review round. | audits/bicam_arrival_20260817/*_run2.json; this commit | Fable |
| 2026-08-17 | Forecast collinearity audit | Engine-stack target (Paul-scoped): susc/edge/susc_mult identity rho=1.000; security double-entry in pressure_mult (rho -0.671); bpf x coop_v2 +0.888 party-robust double-count; stance-coverage x breadth -0.851 coupling; VIF severe only on the duplicate stance scales; confounder register = party->susc chain (-0.29/-0.31, partials 0 by construction), gender via communion (+0.38/+0.30), volume->visibility (+0.70 party-robust); retired-route adjacency recorded (forecast trait-features RETIRED, successor DeltaAP >= +0.010 plant). Controls only -- nothing applied. | audits/FORECAST_COLLINEARITY_2026-08-17.md | Fable |
| 2026-08-17 | Five model observations RULED | (a) susc triple-identity FIXED behavior-neutral (SUSC_GAINS single dial; bit-exact over 212,007 points; merge-gate byte-match checklist pinned); (b) security double-entry KEPT AS DESIGNED + documented; (c) bpf/coop double-count RECORDED + documented, no change; (d) pm-cancellation spec documented in docstring; (e) stale bridge/sqrt prose corrected in flip_model + per_topic_flip, code untouched. Zero behavior change; rank-moving candidates stay closed. | audits/MODEL_OBSERVATIONS_RULINGS_2026-08-17.md @this commit | Fable |
| 2026-08-17 | MERGE GATE + main merge + dashboard regen | Branch merged to main @c6e1c679b, mirror-pushed. Receipts: kernel pre 154/0 (first run 153/1 = transient staleness guard, healed by A-regen); member_receptivity A(old)==ORIGINAL==B(new) BYTE-IDENTICAL (refactor neutral on production data); ranks_python.json byte-identical; tools suites 48 passed; dashboard regenerated (bundle+html+combined) with dashboard_data.json AND bipartisan.json byte-identical (pure re-embed); audit_full 201/2 -- both FAILs pre-existing/time-driven (legfix5 gated item + pillar-snapshot >14d staleness tripwire; cure = full chain run, Paul-gated cadence). Codex second-review debt carried past the gate on Paul's merge order -- still open. | main @c6e1c679b | Fable |
| 2026-08-17 | FULL CHAIN refresh (Paul-ordered) | All steps OK end-to-end (compute_pillars --write, sync_stance_g SAVED, media blend 2016 cells, surfaces + desk + combined rebuilt); rank delta LAWFUL: 5 movers of 533, max |delta| 2 (Mast 412->410; three adjacent swaps); bipartisan.json byte-identical = converged, no second run; kernel unchanged. STALENESS TRIPWIRE NOT CLEARED -- BY DESIGN: O/E/F are formula-backed workbook cells whose caches die on every openpyxl save and revive only via human open+save in Excel (522-rank-incident guard); snapshot still stamped 2026-07-29. CURE = Paul opens+saves+closes Blended.xlsx, then compute_pillars --write re-stamps. Culling FAIL unchanged (Paul-gated). Artifact plane is gitignored by design -- this row IS the refresh commit. | chain run bov9f8ljv; glassbox run-fullchain-20260817 | Fable |
| 2026-08-17 | Tripwire CLEARED | Workbook saved via Excel COM (full rebuild calculated; backup backups/Blended_pre-comsave_20260817_121316.xlsx); compute_pillars --write re-read LIVE O/E/F cells and re-stamped the snapshot 2026-08-17T12:14:04; ranks BYTE-IDENTICAL after live-cell recompute (the snapshot fallback had preserved the basis faithfully -- the guard worked as designed); audit_full now 202 passed / 1 FAILED, the 1 being the Paul-gated legfix5 culling item. Canonical audit posture restored. | glassbox run-fullchain-20260817 | Fable |
| 2026-08-17 | C1-2026 lane AUTHORIZED | Paul: "Authorize the C1-2026 collection lane." GO recorded; runbook governs (CAMPAIGN_SITE_COLLECTION_2026_RUNBOOK.md): collector build via Codex lane, n=10 smoke gates Sweep 1 (results presented before full run), Sweep 1 late September post-certification, weekly passes with sha256 revision-diff, election-day hard stop. | this row; brain STATE | Fable |
| 2026-08-17 | C1-2026 SMOKE CLEAN 6/6 + SWEEP APPROVED (delegated) + collector MERGED | Smoke n=10 (run 20260817T180410Z): 8/10 collected (Miller 403 + Sykes 429 both site-side, recorded honestly); provenance 46/46 entries complete; extraction 7/8 (Castro splash-only); min inter-fetch gap 2.13s >= 2.0 floor; zero robots violations; zero off-roster hosts; gzip 45/45; zero login pages. Roster: 10/10 verified, 7/7 incumbent bioguides MATCH congestion.json; NC-11 anomaly excluded per drop-never-guess. SWEEP_APPROVED created under Paul-delegated authority (Sweep 1 still late-Sept per runbook, full roster first). Merges: 13df44998 (collector) + 8e72cff3f (FIX-16 import-hygiene, caught by audit_stale_imports post-merge -- gate-sequencing miss owned: full run_tests was not run with new files pre-merge). Final gates: stale imports 1/0, KERNEL 154/0, ranks byte-identical, mirror pushed. Intermittent runner flake (pre+post merge, suites pass solo) -> chip task_3870310a. | glassbox c1-2026-collection; ledger run c1-2026-collector-20260817 | Fable |
| 2026-08-17 | Review debt DISCHARGED + queue drafts | Deferred M1/F2/B0 adversarial round run (16 findings: D1/D2/D3/D5/D8 confirmed w/ refinements, D3 merge-blocking on default paths; fresh MAJORs incl. F2 live-without-write cost leak, fixture-overwrite, circular proofs; M1 rank-reason mislabel; B0 count-only cosponsor bar). Tools remain flag-gated OFF, consumed by nothing; fix contract = next dispatch. Queue drafts landed: F1 freeze artifacts (prompt v1 + sampling rule v1, sha256-pinned in a ready-to-lock addendum), E1 prereg DRAFT (D-010 basis, four-baseline bars incl. pflip-redundancy gate), BICAM follow-ups (per-stratum bar recalibration PROPOSAL, maintainer email DRAFT unsent, residual gaps enumerated: 162/162 = 118th late-session tail hr10004+). Roster tranche-1 workflow running. | ledger m1f2b0-second-review-20260817; this commit | Fable |
| 2026-08-17 | Sweep-1 roster TRANCHE 1 assembled | TX/NC/IL/OH via 5-agent workflow: 168 rows = 84 districts x 2 parties exactly (TX 76, IL 34, OH 30, NC 28), 84D/84R, zero dup keys, ZERO exclusions, 65/65 incumbent bioguides MATCH congestion.json, 162/168 with campaign urls (6 honest no-site blanks). Roster committed source_data/campaign_sites_2026/roster_tranche1_20260817.csv + coverage notes. Remaining tranches: other completed-primary states next sessions; late-primary states (FL/AK/WY/MA/NH/RI/DE) September per runbook; certification re-verification at sweep time. | workflow wf_7026ba56-a00 | Fable |
| 2026-08-17 | M1/F2/B0 FIX ROUND MERGED | 15 adjudicated fixes + 4 diff-review amendments (2 spec-origin fail-open bars restored fail-closed, fence collision neutralized, hard-link aliasing via samefile) @0fc190cd1. Two independent review rounds; executor STOP REPORT correctly caught a coordinator mis-rooted verification (19 phantom failures; correct-root 64/64 then 66/66 with amendments; source-hash-beside-logs practice ADOPTED); three missing-RECEIPT reworks across the day flagged to the amendment channel. Gates: stale-imports 1/0, tools 66/66 from main, kernel 154/0, ranks byte-identical, mirror pushed. Tools remain flag-gated OFF. D3 default-path fix means the next BICAM re-audit can run on defaults. | ledger m1f2b0-second-review-20260817 | Fable |
| 2026-08-17 | BICAM audit RUN 3 (fixed defaults) | D3 defaults resolved correctly, no hand-pinning; native strata {117:153/173, 118:169/197, 119:1/253}; pre-119th bills 322/322 (100%) -- run-2 sidecar split corrected (319+4 -> 322+1, same 323 total); NON_BILL 180 native, MALFORMED 0; AMEND-2 veto fired on the 3 damaged receipts (fail-closed proven live); cosponsors IDENTITY-perfect (symdiff 0, ratio 0.0000, 304 acts / 1,288 entries). | audits/bicam_arrival_20260817/*_run3.json | Fable |
| 2026-08-17 | D-011 bars IMPLEMENTED + RUN 4 | Ratified per-stratum bars merged @a42674d56 (37 B0 tests, tools 72/72 from main, kernel 154/0; review round caught two empty-stratum fail-opens -> closed fail-closed; boundary tests at exact 0.987/0.95). RUN 4 verdicts: act PASS (first of the arc, pre-119th 100%), roster FAIL (intended currency signal), text FAIL solely on the retained 3-receipt veto (pre-119th 0.9865 clears 0.95 -- passes when legfix5 repairs the receipts), cosponsors identity-perfect. bars_schema d011-stratum-v1. | audits/bicam_arrival_20260817/*_run4.json; ledger b0-stratum-bars-20260817 | Fable |
| 2026-08-17 | FIVE ITEMS STARTED (Paul: "Start those, new session") | F1 PREREG LOCKED @5534eedd2 (in-chat signature; fingerprints + seeds 535353/646464/757575 + probe-construction rules pinned; sampling window OPEN, look UNSPENT). E1 = new-session build item (harness + 4 baselines + battery per its draft prereg, then lock). Maintainer email: NO send capability on this box -- draft ready in FOLLOWUPS sect.2, Paul pastes. Amendments component: download IN FLIGHT (6.5GB, sha256 pin 2b2660... chained). Receipt repair: DIAGNOSIS COMPLETE -- bodies AND receipts corrupt for all three keys, direct fetch 403-blocked, ONLY route = legfix5 httr cookie-replay R machinery (new-session item with the lane contract). | this commit; glassbox run-five-items-20260817 | Fable |
| 2026-08-17 | legfix5 3-receipt REPAIR (queue exec) | 3/3 re-fetched via httr cookie-replay (HTTP 200; bodies 365-388K chars title-matched; damaged pair quarantined w/ sha256 damage record; store presence 18,552 -> 18,555 of the receipt view; healthy receipt size is ALSO 1330 bytes -- size never distinguishes damage) | harvest manifest invocation 5062c3e9...; quarantine DAMAGE_RECORD.json; run-5 legfix5_errors=0 | session 055f12e9 |
| 2026-08-17 | B0 amendments stratum ARMED (D-011 arming condition met) | manifest bicam-fetch-map-v2; build 49/49 tests (37+12); v1 byte-identity proven vs TRUE pre-change golden sha256 255fdd43 (deterministic-gzip basis, instance-independent); review round 3 findings -> 2 accepted+fixed, 1 rejected recorded; merged 56f1f84c7 (kernel 154/0, stale-imports 1/0) | ledger run b0-amdt-arming-20260817; audits/bicam_arrival_20260817 run-5 section | session 055f12e9 |
| 2026-08-17 | BICAM RUN 5 (armed amendments + repaired receipts) | act: pre-119th 322/322 PASS-stratum, armed amendments 57/173=32.9% FAIL (119th 0/108 -- component has NO 119th; pre-119th 57/65=87.7%); text: AMEND-2 veto CLEARED, pre-119th 0.9859/11,474 PASS-stratum, armed amendments 2,643/3,703=71.4% FAIL (119th 0/874; pre-119th pooled 93.4%); cosponsors identity-perfect; roster 485/533 intended signal; ZERO join defects (spot-audited vs staged csv) | bicam_arrival_audit_run5.json; ARRIVAL_FINDINGS run-5 decomposition | session 055f12e9 |
| 2026-08-17 | E1 harness BUILT (prereg still DRAFT; lock = Paul) | 41/41 tests; flag-gated consumed-by-nothing; look DOUBLE-gated (LOCKED-substring lock file AND --allow-real-data); battery DISCRIMINABLE: BATTERY_PASS world exists (decoupled iid observation p=0.35) and two adverse worlds recorded (dense + edge-correlated observation both defeat the null probe via the sim channel) -- lock-relevant adverse prior; review 7 findings -> 6 fixed, 1 converted to stricter gate; merged (stale-imports 1/0, 408 modules) | ledger run e1-imputation-harness-20260817; codex/e1-imputation-harness a4cb54151 | session 055f12e9 || 2026-08-17 | E1 READY-TO-LOCK ADDENDUM (Paul: finish + push) | 7/7 input pins sha256 at main @ba4f19853 (stance matrix, members, operative AUG20260802 cosponsor network, pflip source, candidate co-appearance layer, harness + tests); mechanical derivation rules; proposed seeds 424242/565656/787878 + battery 313131 (disjoint from F1); ONE open choice routed to Paul = edge-layer roster (1-layer / 2-layer / hold for donor-overlap export); LOCK checkboxes stay unchecked until signature | stance_e1_imputation_prereg.md READY-TO-LOCK ADDENDUM section | session 055f12e9 |
| 2026-08-17 | E1 BATTERY RUN (official pre-look gate) | BATTERY_PASS at proposed seed 313131 (PLANTED/NULL/CONFOUND all pass; synthetic only, nothing spent); evidence sha256-pinned in the addendum | audits/e1_lock_20260817/battery_313131.json | session 055f12e9 |
| 2026-08-17 | POST-MERGE FULL GATE BATTERY (Paul: "Run all") | kernel 154/0; tools pytest 125+39 subtests; stale-imports 1/0 (408 modules); audit_full 202/1 (sole FAIL = pre-existing Paul-gated legfix5 culling item); test_primacy_tier 83+7 subtests; RUNTESTS_DUMP_DIR armed, zero flake captures; ranks untouched by today's merges (never appeared in porcelain) | this commit; runtests dump dir empty | session 055f12e9 |
| 2026-08-17 | FULL CHAIN run 2 (Paul: "run it all") | all 36 steps OK; audit tail 202/1 (known gated item); ranks_python/dashboard_data/bipartisan all BYTE-IDENTICAL to pre-run baseline (SEED=7/MC=20 determinism re-proven at rest; zero movers; zero tracked-surface drift) | chain log tail; baseline vs post-run sha256 triple match | session 055f12e9 |
