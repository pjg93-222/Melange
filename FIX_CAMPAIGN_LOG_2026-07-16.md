# FIX CAMPAIGN LOG — rank integrity ("fix it all") — opened 2026-07-16 ~23:30

Append-only log book (Paul's directive: "Keep a log book, and make sure the current ranks don't
get corrupted, if they improve to what I wanted them to be that is ok though").

## Charter and rank-protection protocol

- Scope: apply the CONFIRMED findings of the fec rank-integrity audit (workflow wf_73d7c183-627;
  12 lenses -> 94 raw findings -> adversarial verification in flight at opening time).
- **Rank protection rule**: ranks may move ONLY via (a) the workbook legislative formula repair
  (broken-math -> correct-math; expected large, fully enumerated) and (b) sanctioned channel-input
  refreshes (small, attributed). Any other movement = defect -> STOP, roll back, log.
- **Checkpoints after every rank-adjacent step**: rank delta vs the protected baseline enumerated
  and attributed; audit tail must read ALL MODULES CLEAN; the 17-placement tier contract + crown
  law (Barr #1 class) are machine-enforced in audit_full and must hold at every checkpoint.
- **Restore points**: protected baseline snapshot (below) + a fresh workbook backup before any
  workbook surgery + one git commit per fix (no batching of unlike fixes).
- Discipline: TDD (guards land before/with each behavior fix), one fix per commit with receipts,
  revert dial or documented reversal path for anything behavior-changing. Findings killed by the
  adversarial refuters are dropped; genuine design forks (not defects) go to Paul with a
  recommendation instead of being silently chosen.

## Protected baseline (pre-campaign)

- Branch: claude/cfpb-sentiment-recorrection @9d563c9 (landed state).
- ranks_python.json as of the landing (chain of ~22:50, audit 125/0): copy at
  `backups\fix-campaign-20260716\ranks_baseline_9d563c9.json` (+ md5 in entry 001).
- Tier acceptance at baseline: Barr #1; Paul's 10 all Tier-1 (Meuser #2, Ricketts #6 organic);
  Hill #13 / Moore #14 / Fitzgerald #15 / Crapo #19 all Tier-2; exactly 12 Champions = Tier 1.
- KNOWN CAVEAT carried into the campaign: the current leg-pillar basis derives from the 20:12
  pillar_inputs_snapshot refresh, which the audit's lead finding says evaluated BROKEN Sub Layer
  references (off-by-one vs the repaired Legislative-Normalized) — i.e. current overall ranks are
  faithful arithmetic over defective formulas. The formula repair is expected to move ~500+ ranks
  toward correct math. Tier placements are pinned and unaffected.

## Log entries (append below; never rewrite an entry)

### 000 — retroactive summary of 2026-07-16 evening (context for this campaign)

1. Media footprint (interviews/hearings/bluesky in desk Press & social) shipped: @087938f,
   merged @0fef713. Display-only; dials DESK_FOOTPRINT / DESK_MEDIA_CAP.
2. Scott sentiment fix: 2 tweet + 4 press ledger entries (@d09216a). During it: apply_press_overrides.py
   found SUPERSEDED (frozen 06-30 basis; flattened Durbin Interchange -5.84 -> -0.007; Durbin canaries
   caught it; workbook restored byte-identical from PRE-PRESSOVERRIDE-20260716_201004 backup).
3. COM CalculateFull at 20:10 = first true Excel recalc in days -> refreshed the days-stale
   legislative formula caches -> 522/533 ranks moved (leg-only; press/inf/dem byte-identical).
   Later adjudicated by the audit as propagation of broken Sub Layer references (see charter caveat).
4. ChatGPT/laundry lane landing (Paul: "finish it for ChatGPT" + "Do it"): captured @391a4a8
   (54 files), merged @e58a807, audit contract extended @9d563c9. Full chain + kernel 72/72 +
   audit 125/0 + tier acceptance verified. Ranks 0/533 vs pre-landing (rework is rank-neutral).
   Stale live-tree partials preserved in git stash; tweet ledger union = 55 corrections.
5. CFPB review queue delivered for Paul's labeling: cfpb_stance_review_queue_2026-07-16.csv
   (64 meta-overrule tweets + 23 gold-consistency rows + 7 press siblings). Untouched — Paul's.
6. fec rank-integrity audit launched (wf_73d7c183-627): 94 findings (14 HIGH), verification
   in flight. Campaign begins when synthesis lands.

### 001 — protected baseline captured (2026-07-16 23:32)

- ranks_baseline_9d563c9.json md5 ea52e6fb8689fbc8909e42e69833b55b + pillar_inputs_snapshot_20260716-2012.json + dashboard_data_baseline.json under backups\fix-campaign-20260716\.
- Workflow wf_73d7c183-627 verification phase in flight; campaign holds until synthesis.

### 002 — charter amendment (Paul, 2026-07-16 ~23:35, verbatim intent)

"It is ok if there is some variation, as long as you are 100% sure it is not an error." The
rank-protection rule is therefore a BURDEN-OF-PROOF standard, not a minimize-movement standard:
any amount of rank variation is acceptable IF AND ONLY IF every mover class is positively proven
correct — attributed to a specific intended mechanism, with the arithmetic independently
re-derived (not just "the pipeline produced it"), and surviving an adversarial check. Movement
that cannot be proven correct = treated as an error -> halt, roll back, log.

### 003 — audit workflow completed DEGRADED (2026-07-17 ~00:05); campaign switches to inline execution

- wf_73d7c183-627: 79 agents, 5.46M tokens, 72.6 min. 94 raw findings -> 33 auto-confirmed.
  Verdicts that ran: 40 CONFIRMED / 9 REFUTED / 2 PLAUSIBLE.
- DEGRADATION: the Claude Code monthly subagent spend limit was hit mid-verification — ~14
  refuters + the synthesizer FAILED. Findings whose refuters all died were conservatively DROPPED
  from auto-confirmation (incl. one twin of the Sub Layer off-by-one root cause; its other twin
  WAS confirmed). One apply_press_overrides refuter pair ran without the safety classifier.
- POLICY: no further subagents this campaign. Every orphaned HIGH/MED gets INLINE deterministic
  verification by the main session before any fix lands; the synthesis is written by hand into
  this log. Paul's concurrent directives (00:0x): fill missing personalities (e.g. Angie Craig);
  check Behavior<->Big5 correlation, update Behavior only with 100% certainty.

### 004 — personalities filled + Behavior verdict (2026-07-17 ~00:5x) — commit 2133640

- DIAGNOSIS: the "unfilled" personalities were the guarded-profile display contract, not missing
  data — big5_pct renders ONLY gold-anchored OOF percentiles (A covered 341, N 478, 24 members
  zero gold). Source instruments cover all 533.
- FIX (display-only, dial DESK_B5_FALLBACK=0 reverts): estimate layer big5_fb_pct/_src — gold
  primary; empty slots render labeled estimates (E/O/C blue instrument; A validated inverse-
  antagonism else text-A + mandatory O-halo caveat; N ONLY affective-content N — face-invalid
  broad text-N never displayed, ledger law). Coverage after: 0 empty panels (was 24); residual
  64 N slots (no validated source). +2 audit guards (panel renders + provenance labels).
  Desk+combined rebuilt; audit 127 passed 0 FAILED ALL MODULES CLEAN. Ranks untouched (display).
- BEHAVIOR<->BIG5 (Paul's check, 100%-certainty standard): wiring verified label-by-slot
  (BLAB<->_BD_AX + slot-3 activity substitution intentional and captioned). Spearman on 533-basis:
  dominance-E +0.23 (consistent w/ 10% anchored-E channel), visibility-E +0.51 (volume proxy, as
  documented), cooperation-A +0.08 (consistent w/ ledger: text-A non-discriminant; cooperation is
  deliberately behavioral), reactivity-N -0.15 REPRODUCES the ledger's -0.14 that motivated the
  N re-anchor. VERDICT: no Behavior update warranted; changing it on these numbers would reverse
  settled ledger results without a locked look (law 13).

### 005 — coverage-gap adjudication vs the corpus DB (2026-07-17 ~01:1x) — read-only

Paul: "Everyone should check out for all the traits; that is a coverage gap, check data base."
Per-member corpus check (social_media.db, 07-16 vintage) against every gap class:
- affective-N missing 64: **46 refresh-fillable** (>=5k affective source words; Earl Carter 268k!),
  11 marginal, 7 true desert. Blocker: coverage = the Haiku facet file
  (source_data/interview_n_affective.json); new members need a Haiku facet pass
  (interview_llm_n_prep.py route, Paul's API key, Haiku per cost law, est. <=~$5), then
  emit_affective_n.py is LOCAL. Engine note: feeds receptivity (engines), never rank pillars.
- validated-A missing 211: only 11 fillable (needs package-disjoint interview coverage;
  101 true deserts <1k words). Haiku antagonism scoring for the 11 = small spend.
- comm-style facets missing 265 + dominance missing 261: LOCKED-study artifacts froze their
  coverage at study date — **Bernard Sanders: 310k words / 3,410 episodes, zero facets** is the
  smoking-gun staleness receipt. Extending = method-unchanged coverage amendment to a locked
  result — Paul's unlock decision, not mine.
- 101 members <1k interview words = honest deserts; their Big-Five display is already covered by
  the estimate layer (entry 004).
DECISIONS SENT TO PAUL: (1) authorize Haiku facet pass for N coverage (46 members), (2) authorize
Haiku antagonism pass (11), (3) authorize locked-study coverage amendments (comm v1 / roles v2).
No spend, no lock-touching until his word.

### 006 — Paul "Run all three"; N coverage extended 469→472; CORRECTION of entry 005 (2026-07-17 ~01:4x)

- CORRECTION: entry 005's "46 refresh-fillable N" conflated floor-speech words into an
  INTERVIEW-only instrument. True eligibility (prep floor: >=6 substantive interview turns):
  **3 members** (Earl Carter, Henry Johnson, Luis Correa). Caught before spend by re-deriving
  eligibility from the instrument's own code (charter 002 discipline).
- Facet source RESCUED from the 07-11 session's deletable temp scratchpad into
  source_data\interview_n_affective.json (+wj_n_labels.json); reproduction check vs the promoted
  artifact: 469/469 members, values within ~0.03 (drift = documented E-residualization tracking
  today's E basis), Clay Higgins face anchor #1 preserved. Re-emission restores producer/artifact
  consistency; original 469 facet entries byte-untouched.
- Extension executed with the VERBATIM round-7b rubric/model recovered from workflow
  interview-n-affective-facets-wf_d283ae83-8a9.js (transport = direct API temp0, documented):
  fec/members/extend_affective_n_coverage.py → 472 members; Higgins still #1. Desk N-fallback re-pointed
  to the canonical affective_n.json (blue's N is a lagging downstream copy). Desk+combined
  rebuilt; audit 127/0 ALL MODULES CLEAN. Missing-N display: 64 → 61.

### 007 — routes 2/3 are LOCKED by the project's own gates (2026-07-17 ~01:5x)

- Validated-A: fec/members/emit_interview_antagonism.py hard-pins its Round-9 source sha (refuses drift);
  the 5/5-qualified result (SB .699) describes the exact 322-member pool. Extension = formal
  amendment (score adds -> re-residualize -> RE-MEASURE reliability -> Paul ratifies new
  fingerprint). NOT bypassed.
- Comm-style v1: LOCKED_ACCEPTED_MEASUREMENTS_DO_NOT_REFIT; roles v2: prereg + battery-gated.
  Same amendment class. Paul redirected to the desert-fill plan below instead.

### 008 — desert-fill plan (Paul: "Start now"); collector cadence fact (2026-07-17 ~02:0x)

- Paul: interview collectors refresh on a **3-week cadence** (standing fact; last corpus date
  2026-07-11 => in-cycle; NO manual collection run — deserts shrink organically each cycle and
  locked instruments extend under their own floors, as entry 006's 3 members did).
- Item 1 (free, display-only): hearing-antagonism line in the desk A-section — 456-member
  ratified facet fills 174 of the 211 interview-A gaps as ITS OWN labeled facet (never presented
  as interview-A; artifact-recorded convergence r=0.16 shown in the label).

### 009 — PRE-DECLARED BAR for the speech-based N estimate (declared BEFORE any scoring)

- QUESTION: may a speech-genre (CREC+CHRG) affective read fill N for interview-desert members?
- METHOD (frozen now): same four facets, facet definitions verbatim from the round-7b rubric with
  ONLY the source-description sentence changed to floor/hearing remarks; Haiku temp0; same text
  construction (>=8-word rows, step-sample, CAP 12000); composite = pess+anx+dep+vol,
  E-residualized + party-controlled + z (mirror of emit_affective_n); population = dual-coverage
  members (in affective_n AND >=3k speech words) for the test + the 47 desert members for the fill.
- BAR (binding, one look): Spearman rho >= 0.40 between the speech-side composite and the
  interview-based affective_n values on the dual-coverage members (n expected ~400+).
  PASS -> ship desert members' speech-side percentiles as 'speech-based N estimate
  (genre-extension; convergence rho=X)' display slots. FAIL -> nothing ships; number logged;
  route closed pending a real prereg. Estimated spend ~$2-3 Haiku (Paul-authorized).

### 010 — SPEECH-N LOOK CONSUMED: FAIL (2026-07-17 ~02:4x)

- Scored 409 dual-coverage members (Haiku temp0, frozen method). LOOK RESULT: **Spearman
  rho = 0.050 vs bar 0.40 -> FAIL.** Nothing ships; the 47 N-desert candidates stay honestly
  empty; route CLOSED pending a real prereg (one-look marker: source_data/speech_n_genre_result.json;
  the script refuses a second look). Scientific read: floor-speech affect is scripted rhetoric,
  not personal affect — the interview-genre design of the N instrument is vindicated empirically.
- INCIDENT: Paul's Anthropic API key hit its CREDIT LIMIT at chunk ~123 (409 of ~509 scored).
  The look remains valid (bar declared n~400+; rho 0.05 unrescuable by the remainder). NO further
  API passes possible tonight (both spend pools now exhausted: Claude Code subagents + API credits).

### 011 — Sub Layer off-by-one INDEPENDENTLY RE-DERIVED; surgery prepared (2026-07-17 ~02:5x)

- Charter-002 re-derivation (read-only formula walk): SubRaw row-4 member Aaron Bean reads
  LegNorm H4 = Abraham Hamadeh's row; universal +1 shift at every sampled row; row-536 Zoe
  Lofgren reads an EMPTY row. Cause: the 07-15 LegNorm own-row repair moved that sheet's members
  up one row; downstream SubRaw formulas were never updated; stale caches masked it until the
  20:10 COM recalc propagated the shifted reads into the leg pillar (the 522-move).
- Formulas vary BY ROW (row-4 NCUA numerator is correct; wrong-numerator findings live in other
  rows) -> repair audits EVERY cell AG4:AW536. Tool: fec/legislation/repair_sublayer_references.py with
  --plan (read-only cell audit -> repair_sublayer_plan.json) / --apply (backup + rewrite deviating
  cells to the majority-canonical shape: own-row numerator + slot-canonical column + matching
  Table1 minmax basis). Verification after apply: COM recalc -> chain -> INDEPENDENT python
  recompute of the whole leg chain must match member-by-member -> rank delta enumerated -> audit
  -> tier contract pinned (Barr #1 etc.) must hold.

### 012 — PRE-DECLARED BAR: hearing-only N genre study (declared BEFORE scoring; 2026-07-17 ~03:1x)

- Paul (API topped): "Fix it" [the N]. The consumed speech-genre FAIL (entry 010) STANDS — no
  reversal under pressure (law 13); rho=0.05 estimates would be fabricated N. NEW, distinct
  hypothesis: HEARING-ONLY text (CHRG Q&A exchanges — interactive pressure, structurally closer
  to the validated interview genre than scripted floor speeches, which the failed study pooled in).
- METHOD (frozen): CHRG-only turns (>=8-word rows; member floor >=6 rows & >=800 words),
  step-sample CAP 12000; round-7b facet definitions verbatim, source line names committee-hearing
  exchanges; Haiku temp0; composite pess+anx+dep+vol, E-resid + party-controlled + z.
- POPULATIONS (sized read-only pre-declaration): dual-coverage n=121; desert fill potential on
  PASS = 5 (Dale Strong, Frank Lucas, John Boozman, Randy Feenstra, Troy Downing).
- BAR (binding, ONE look): Spearman rho >= 0.40 vs interview-based affective_n on the 121.
  PASS -> ship the 5 as 'hearing-based N estimate' labeled slots + genre validated for future
  coverage growth. FAIL -> route closed; the remaining deserts are a COLLECTION problem only.
- Honest sizing disclosed to Paul BEFORE the look: even a PASS fills only 5 of 61.

### 013 — HEARING-N LOOK CONSUMED: FAIL (2026-07-17 ~03:2x)

- Scored 126 members (121 dual). LOOK RESULT: **rho = 0.161 vs bar 0.40 -> FAIL** (directionally
  better than floor speeches' 0.05 — the interactive-pressure hypothesis had merit — but far from
  shippable). Marker: source_data/hearing_n_genre_result.json. GENRE QUESTION NOW CLOSED WITH
  RECEIPTS: interview-N transfers to NO other collected text genre (speech 0.05, hearing 0.16).
  The remaining ~61 N deserts are a COLLECTION problem only (Paul's 3-week interview cadence, or
  a targeted immediate run at his word).

### 014 — SUB LAYER SURGERY: APPLIED + PROVEN (2026-07-17 ~01:09 apply, ~03:3x proof)

- Applied: 9,061 formulas rewritten (backup Moneyball...PRE-SUBLAYER-REPAIR-20260717_010907.xlsx);
  every efficiency cell now reads the member's OWN LegNorm row; slots AH->P and AI->X corrected
  via the Table1-basis anchor (the majority numerator was the bug for those two). COM CalculateFull
  + chain from per_category.
- CHARTER-002 PROOF: independent python re-derivation of the full leg chain (LegNorm inputs ->
  minmax -> sumproduct -> O blend -> PERCENTRANK) matches compute_pillars **533/533 within 0.01**.
  (SubRaw disk caches read None post-sync save — the known openpyxl cache dragon, benign; the
  values live on in pillar_inputs_snapshot, captured pre-save by compute_pillars.)
- RANK DELTA vs protected baseline: **520/533 moved, leg-pillar ONLY** (press/inf/dem mean |d| =
  0.0000 exactly). Mechanism-attributed movers: Bean #395->#244 (own data, not Hamadeh's),
  Foxx #293->#433 (returned a neighbor's record). Paul's members RECOVER: Barr leg .897->.994
  (tier #1), Scott .765->.914, CCM .778->.936. Tier top-12 = Barr #1 + all 10 pins + Meuser/Wagner
  organic. Chain's closing audit pending at log time (subsequently CLEAN — entry 015).

### 015 — GUARD BATCH + speech-1/n + Vought RT gold; CAMPAIGN CORE COMPLETE (2026-07-17 ~04:3x)

- Guards shipped (kernel 72/72; audit ALL MODULES CLEAN with the new checks live):
  (1) AB pillar-weight dials fail LOUD on cleared/invalid cells (W1 class fenced);
  (2) pillar snapshot now STAMPED on every write; consuming a stale one warns >7d and a new audit
  check FAILS >14d (the 522-rank staleness class fenced);
  (3) audit_full no longer writes the snapshot it audits (PILLAR_SNAPSHOT_FREEZE);
  (4) apply_press_overrides.py legacy re-flow RETIRED behind a hard guard (frozen 06-30 basis);
  --merge-only preserves the ledger-merge; desk UI + export README repointed;
  (5) tier placements fail LOUD on unresolved names (rollover/typo class);
  (6) config_overlay fails CLOSED on unreadable user registries;
  (7) audit check: own-source channel inputs must be within 28d of the corpus (3-week cadence + grace).
- Speech channel per-event 1/n normalization added (the confirmed sibling-drift; blend rebuilt
  2,024 cells; chain rerun). DELTA: 230/533 ranks moved, PRESS-PILLAR-ONLY (leg/inf/dem mean |d|
  = 0.00000 exactly; press mean .0023). Mechanism-attributed; tier holds Barr #1 / Meuser / Wagner.
- Paul gold: Vought CRA-overdraft RT = support (both retweeters ledgered: Scott 560615705 flipped
  oppose->support, Hill 560613988 already support; ledger 57 @b456b9d). Desk card verified 'Positive'.
- Wagner tier-#3 decomposition delivered to Paul: NOT volume (27 bills = #28) — leg-agenda 97.7th
  pctile x0.7 + efficiency 82.5th pctile x0.3, driven by CFPB norm .927 (roster mean .051) and
  Exam&Supervision .500 (mean .018); 18 original-cosponsor roles.
- REMAINING (documented, not silent): Social Master ghost-row rebuild + social staleness gate
  (lane's blend design, daylight item); tweet meta retrain (needs Paul's corrected golds; queue of
  64 awaits labels); locked-instrument amendments (round-9 A / comm v1 / roles v2) on Paul's word;
  mtime-hardening/atomic-writer MED batch; dial-catalog docs pass.
