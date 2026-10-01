# RESEARCH INTEGRATION 2026-08-14 — five papers, mapped to Melange, with a validation framework

STATUS: DRAFT FOR PAUL. Nothing in this document is adopted, scheduled, or authorized.
Every implementation step below is gated per `moneyball-change-control`; every APPLY is
Paul's. This document is the deliverable of the research-integration lane (worktree
`melange-research-integration-a31e20`, branch `claude/melange-research-integration-a31e20`).

## 0. What this document is

Paul supplied five papers (PDFs in `C:\Users\pgoff\Downloads\`) and asked for: (1) a
grounding in the current state and ethos of Melange, (2) a read of the papers, (3) a
mapping of where they could be implemented, and (4) a guiding document and validation
framework for those implementations. This is that document.

Method note (provenance): each paper was read cover-to-cover by a dedicated reader agent
returning a structured digest with page-anchored verbatim quotes; the mapping, framework,
and priority slate were built against the project brain (STATE/CONSTRAINTS/DECISIONS/
DEADENDS as of 2026-08-14), the skills library (research-frontier, research-methodology,
docs-and-claims, failure-archaeology), and read-only checks against the live tree run
2026-08-14. Reader integrity notes are recorded per paper (figure-render limits,
page-count discrepancies). Paper page numbers cite the PDF as read by the reader agent.
Per the frozen-vintage constraint, this file is a dated record: facts about repo state
are as-of 2026-08-14 and re-verify per the provenance table in §9.3.

## 1. The system as it stands (state and ethos)

### 1.1 What Melange is

Melange (repo name Moneyball) is a congressional influence-analytics platform for
credit-union-sector lobbying: 533 members of Congress, a multi-modal corpus (floor
speeches, hearings, press, tweets, interviews, 18,557 full-text bills, letters, 395
verified voiceprints), a stance/sentiment stack scoring member alignment toward the CU
sector and named targets (CFPB, banks, crypto), a behavioral-psychometrics program
(Big Five instruments validated against behavioral criteria), FEC/LDA/press/cosponsorship
networks fused into a signed multiplex graph, IC/LT influence-propagation engines with
per-member receptivity, submodular budget/seed optimizers, and lobbyist-facing surfaces
(rankings, tiers, coalition builder, desk). Rank authority is `ranks_python.json`;
surfaces show rankings and data only (Paul, 2026-08-11 — no advisory copy).

### 1.2 The ethos (what makes this repo unusual)

Any integration of outside research must fit these, not fight them:

1. **The code is the law; docs point at it.** The long-form spec was retired for
   drifting (`MATHEMATICAL_SPECIFICATION.md:2-3`). This document therefore names files
   and owners, and does not restate math.
2. **Claims are earned, never narrated.** Every validity claim runs prereg → simulate
   battery → ONE look, with numeric bars fixed before data is seen; a consumed look is
   never re-taken; a MISS is a first-class recorded result (`moneyball-research-methodology`).
3. **Paul's domains are hard boundaries.** Stance/press labels, registry valence, dial
   values, engine promotions, deletions, roster membership, and anything rank-moving are
   user-gated. Analysis lanes present findings and WAIT.
4. **Honest gaps stay honest.** A coverage hole is reported as a hole (the 8-state QCEW
   precedent), never papered over by relabeling or estimation without a gate.
5. **Everything runs in the glass box.** Processes emit to the shared event stream;
   invisible work is unacceptable (Paul, 2026-07-27; lane law 4).
6. **Determinism and provenance.** SEED=7/MC=20 CRN determinism, SHA-256 input pinning,
   atomic writes, append-only history, `.candidate` staging for anything unpromoted.
7. **Cost discipline.** Fable/Opus only for the 533 narratives; every other LLM step is
   Haiku 4.5 (standing rule; applies to anything these papers inspire).
8. **Figures carry window + denominator in-sentence** (D-007 / CONSTRAINTS Claims), and
   pooled coefficients over a named fault line are quoted with strata visible or labeled
   UNSTRATIFIED.

### 1.3 Working state relevant to these papers (verified 2026-08-14, read-only)

- Board and gates: kernel tests green post-merge on main; `audit_full` 202/1 with the
  single FAIL being the Paul-gated legfix5 culling item (brain STATE, verified
  2026-08-14; the worktree base for this document is main @846d90ae3).
- Stance ladder (unchanged): stance-hop 0.915, valence-hop 0.689, compose ceiling 0.872
  on the 400 adjudicated tweet golds (`fec/stance/apply_two_hop_stance.py:4-5`).
- Psych program: instrument look 3/5 (O/C/E diagonal-dominant); A criterion-valid, not
  discriminant; ES has no clean validation (gender-confound caveat mandatory); A− grade
  FINAL; O successor route spent 2026-08-14 (DUAL_PANEL_SUCCESSOR_MISS @9425ac5fd).
- Frontier gate movement observed 2026-08-14: raw `reactivity_z` coverage in the live
  tree's `behavioral_dispositions.json` is **270 of 533** (coverage block, read
  2026-08-14). The round-4 N-route gate is **MEM_N ≥ 250 where MEM_N = MEM ∩
  reactivity_z non-null on the eligible roster MEM=456** (`big5_n_matrix_prereg.md:63`,
  pinned at 201 at lock). Raw 270 is an upper bound on MEM_N, not the gate value — but
  it is the first observation putting the gate plausibly within reach. Checking the
  true intersection is synthetic-side and risks no look.
- Prospective-outcome harness: `outcome_snapshot_2026-07-04.json` now lives at
  `data\engine\outcome_snapshot_2026-07-04.json` (relocated by the reorg; the
  research-frontier skill's root-path pointer is stale). Scoreable from ~2026-09-02 if
  the ≥150-mover floor is met.
- Open Paul-gated items that these proposals must not collide with: the 94-row CFPB
  queue, the legfix5 19-category culling review, stranded codex worktrees, and the
  electoral_plays chain (TODO.md §1).

## 2. The integration validation framework

This is the law for turning ANY paper-derived idea into a shipped Melange change. It
composes the repo's existing machinery — nothing here is new discipline, only the
existing discipline arranged as a gauntlet with the paper-specific traps named. Owning
skills are cited per stage; where this document and an owning skill disagree, the skill
wins.

### Stage 0 — Kill-ledger and decision screen (before anything is proposed)

Check every idea against: `moneyball-failure-archaeology` (the kill-ledger, refuted
lists, canceled work), the brain's DEADENDS.md and DECISIONS.md, and the standing
prohibitions. An idea that paraphrases a dead end is dead unless its pinned
`Would reconsider if:` condition is shown met. Traps adjacent to THESE five papers:

- **DE-001 (mention density).** Any paper method that scores relevance/salience by term
  frequency is barred from relevance pricing; term counts are a NEGATIVE screen only.
- **Human raters / expert panels.** Canceled by Paul; A− FINAL. Any paper whose
  validation requires fresh human annotation panels cannot import that validation step
  for psychometrics. (Stance gold adjudication by PAUL is different and standing.)
- **RL envelope.** Paul's roadmap; papers proposing RL-based consensus/targeting loops
  are citation material only — do not build uninvited.
- **CT-CM / latent-factor halo modeling.** Four misses, stopped by rule. Papers offering
  latent trait fusion do not reopen it.
- **Auto-valence registries.** Five automated registries lost to curation (@827f211);
  papers offering automated stance-knowledge construction feed the CURATION QUEUE, never
  replace the registry.
- **FEC×LDA R3 ruling.** Structure explains all of the FEC→LDA lead; predictor-language
  is BARRED for claims built on those links.
- **Bluesky/self-selected platform samples** measure platform membership, not traits
  (kill-ledger); social-platform methods from papers inherit that caveat.

### Stage 1 — Change-class and ownership triage

Classify the proposal per `moneyball-change-control` BEFORE any work: new data source /
new instrument / new engine physics / display-only / doc-only. Then name the gate owner.
Non-negotiable ownership boundaries that recur below: stance and press labels (Paul);
registry valence (Paul); anything moving `ranks_python.json` (verification protocol +
Paul); engine promotion even after a PASS (Paul, `.candidate` convention); deletions
(Paul); dial values (Paul). A proposal card without a named gate owner is incomplete.

### Stage 2 — $0 probes (never risking a look)

Permitted before any prereg: criterion-side diagnostics, coverage counts, synthetic
simulations, external-data reconciliation counts, code plumbing checks. FORBIDDEN: any
pairing of a candidate instrument with its criterion — that IS the look. For data-source
papers (BICAM class), the $0 probe is reconciliation: row counts, key-join rates, and
coverage vs the repo's existing artifacts, written up as counts with denominators.

### Stage 3 — Prereg with numeric bars

Per `moneyball-research-methodology` §2: locked file, numeric all-must-hold bars, pinned
roster/stratum, SHA-256 input fingerprints, adverse priors disclosed, consequences for
every outcome with fixed wording, stopping rules, and the corroboration-vs-validation
label chosen by power arithmetic (if honest power < ~80% against the best published
effect size, label it corroboration with tiered wording, or pin a data gate instead).
Any new-source integration that will touch rank-feeding artifacts also pre-declares its
reconciliation bars (join-rate floors, disagreement ceilings) the same way.

### Stage 4 — Simulate battery / planted-signal gate

Machinery must prove it can find planted signal, refuse null, refuse pure confound, and
admit true+confound (four checks, pinned seeds, plants orthogonalized). Battery refusal
= RETIRED WITHOUT A LOOK with a pinned successor gate — neither validated nor closed.
For network/edge proposals the analogue is a planted-edge battery: plant known signed
edges, verify recovery; plant nulls, verify refusal — before any real edge enters a
kernel.

### Stage 5 — The one look

Taken by a gated script, never by hand; refuses on lock/fingerprint/battery failure;
RESULT recorded verbatim (MISSes included) and committed same session. A PASS is
adversarially re-derived (fresh seeds / independent recomputation) before any
consequence fires; FRAGILE = MISS.

### Stage 6 — User-gated promotion and doc duties

On PASS: build the artifact as `.candidate` (consumed by nothing), present to Paul, and
only on his ratification wire it behind a revert dial (`RECEPT_COOP=v2` pattern). For
anything touching ranks: baseline hashes + full board captured first, independent
adversarial review of the DRAFT, revert dial proven byte-identical, mirror reproduces
the live board, every mover enumerated (CONSTRAINTS Tooling, 2026-08-12). Docs duties
per `moneyball-docs-and-claims` §6 (spec table row, README module map, claims ledger,
commit vocabulary). Citation honesty per §4.1 there: papers are cited for settings,
principles, and directions; magnitudes are local calibration — citing a paper never
transfers its evidence to our constants.

### Cross-cutting rules (all stages)

- LLM steps: Haiku 4.5 only (Fable reserved for the 533 narratives).
- import == execution; worktrees do not isolate the data plane for fec scripts — run
  data-dependent checks in the live tree, after checking for Paul's live jobs.
- Every long-running process emits to the glassbox stream.
- Figures in any write-up carry window + denominator in-sentence; strata visible for
  pooled quantities over party/chamber/sector fault lines.
- External claims: only prereg'd RESULT numbers leave the repo, with mandatory caveats
  attached verbatim.

### The proposal card (template used in §§3-7)

Every proposal below is stated as: **what / where it plugs in / expected benefit /
effort (S,M,L) / fit (1-5) / change class + gate owner / validation plan (stages above,
with draft bars where applicable) / dead-end adjacency (what Stage 0 checked)**. Draft
bars are DRAFTS — locking any of them is a separate, Paul-visible prereg step.

## 3. Paper 1 — FOLAR: LLM-enhanced Logic Tensor Networks for stance detection (Neural Networks 2025)

Dai, Liao, Zhao et al., "Large Language Model Enhanced Logic Tensor Network for Stance
Detection," Neural Networks 183:106956 (2025), DOI 10.1016/j.neunet.2024.106956.
New method. Reader note: the PDF is 10 pages (not the briefed 18); all 10 read; Figures
1-5 are raster (ablation bar values unreadable); quotes dehyphenated.

**What it does.** A chain-of-thought prompt has an LLM emit, per input, a predicate
glossary and a first-order-logic rule ending in a stance consequent ("Knowledge
Elicitation"); the rule is compiled into a differentiable Logic Tensor Network over
shared BERT embeddings (product logic, Reichenbach implication) and trained on labels;
three LLM-specific LTNs are fused by an attention dynamic-routing head (MDF). Also
ships FOLAR's training-free ablation, **FOL-CoT**: the LLM classifies directly from
FOL-formatted reasoning chains, no training. Verbatim: "To the best of our knowledge,
this is the first attempt to integrate an interpretable logic tensor network into a
stance detection framework." (p.2).

**Key numbers** (reader-extracted; benchmarks are short English social-media text):
zero-shot VAST all-topics macro-F 81.0 vs best baseline 76.8 (Table 4, p.7); at 10%
training data 80.2 vs 74.0; training-free FOL-CoT 79.8 vs plain CoT 73.4 (same table)
— in the paper's own ablation, the FOL formatting itself, not the trained network,
carries most of the zero-shot gain. In-target results have real exceptions (TPDG beats it on LA in-target, KEprompt
on FM, its own no-MDF ablation on HC — Table 3, p.6). Admitted failure modes: sarcasm
and implicit stance (p.9). Reader-observed risks: benchmark-contamination (targets are
saturated public figures predating LLM cutoffs), retired API versions, no released
code yet, no variance reported.

**Where it plugs in.** Frontier problem 4 — the valence-hop bottleneck (model
valence-hop 0.689 on the 400 adjudicated tweet golds; compose ceiling 0.872,
`fec/stance/apply_two_hop_stance.py:4-5`). The compose architecture is the unusual
asset here and is NOT up for replacement: the model handles language, Paul's registry
handles domain valence, `policy_force` binds. FOLAR-derived ideas upgrade the MODEL
legs and the CURATION tooling only.

### Proposal F1 — FOL-CoT prompting for the model valence hop
- **What:** reformat the valence-hop classification prompt to elicit a predicate
  glossary + FOL rule rationale (one-shot CoT), Haiku 4.5 as the model (cost rule; NOT
  the paper's three-LLM ensemble), keeping the registry authoritative and the model as
  registry-fallback exactly as today.
- **Where:** `fec/stance/` valence-hop leg; scored by `fec/stance/stance_eval.py`
  against adjudicated gold only.
- **Expected benefit:** the paper's cleanest isolated effect is FOL-formatting
  (+6.4 macro-F zero-shot over plain CoT on VAST, Table 4 p.7). If even a fraction
  transfers to long-form press valence, the 0.689 hop moves.
- **Effort:** S. **Fit:** 4/5.
- **Change class + gate:** research instrument change to a model leg; no production
  label changes without Paul; prereg + one look per `moneyball-research-methodology`.
- **Validation plan:** Stage 2 — none that pairs instrument with criterion (forbidden);
  permitted $0 work is prompt-format engineering on SYNTHETIC/plant items only.
  Stage 3 — prereg with draft bars of the established shape: valence-hop accuracy on a
  FRESH held-out user-adjudicated gold batch (labels collected after the method is
  frozen) ≥ baseline 0.689 + pre-declared margin, macro-F1 primary, permutation p
  < .05; composed accuracy reported secondary (ceiling 0.872 unless the stance hop also
  moves — state this so the bar is honest). Stage 5 — one look, adversarial
  re-derivation on PASS. Stage 6 — production prompt swap is user-gated with the old
  prompt as the revert.
- **Dead-end adjacency (Stage 0):** does not touch the registry (auto-valence
  registries are a killed route — five lost to curation @827f211); does not relabel
  anything (stance labels are Paul's); no human raters; LLM step is Haiku-only. Clean.
- **Main risks:** short-text→long-form domain shift; sarcasm/implicit stance (admitted
  failure mode, common in congressional press); contamination-inflated paper baselines
  mean the +6.4 is an optimistic prior — the prereg's honest-prior section must lower
  it.

### Proposal F2 — FOL rationales as curation/adjudication tooling
- **What:** attach the elicited predicate glossary + rule trace to items in Paul's
  adjudication queues (the 94-row CFPB queue pattern) and to `--uncovered` registry
  candidates, as a human-auditable WHY column. Never auto-applies a label.
- **Where:** queue builders (`fec/stance/build_gold_queue.py` family) + the
  `apply_two_hop_stance.py --uncovered` curation list.
- **Expected benefit:** faster, better-grounded adjudication of exactly the world-
  knowledge judgments that bottleneck the valence hop; rationales emit to glassbox as
  auditable artifacts.
- **Effort:** S. **Fit:** 4/5.
- **Change class + gate:** curation tooling (the explicitly sanctioned direction:
  "you build curation tooling and override mechanisms; you NEVER relabel by model
  judgment"). Display/tooling class; Paul sees it in his queue workflow; no prereg
  needed because no validity claim is made — but any accuracy statement about the
  rationales themselves would need one.
- **Validation plan:** Stage 2 only — a $0 usefulness check is Paul's own experience
  with one queue batch; the honest metric is overrides-per-week trending down
  (`press_stance_overrides.json` is the natural counter, per frontier P4).
- **Dead-end adjacency:** exactly the sanctioned lane; no conflicts found.
- **Main risks:** rationale plausibility ≠ correctness (LLM over-inference is the
  paper's second admitted failure mode) — the queue UI must present rationales as
  machine argument, not evidence.

### Proposal F3 — multi-model stance fusion (MDF) — CONFLICTS WITH STANDING LAW, not recommended now
The paper's MDF head fuses three frontier LLMs. Melange's standing cost rule is
Haiku 4.5 for every LLM step except the 533 narratives; a multi-frontier-model stance
ensemble violates it. A prompt-ensemble variant (multiple FOL framings, one Haiku
model, disagreement flags routed to Paul's queue) preserves the idea inside the law.
Recorded here as: PARKED pending Paul explicitly re-ruling the cost law for stance
ensembles (his call to open, not ours to propose around). Effort if unparked: M.
Fit as parked variant: 3/5.

### Proposal F4 — zero-shot valence PROPOSALS for newly onboarded targets
- **What:** when the act/target universe expands (the 633→644 precedent), run FOL-CoT
  zero-shot over the new targets to generate PROPOSED registry entries with rationales,
  queued for Paul. Nothing enters production unruled; provisional bands never render.
- **Where:** target onboarding path + registry curation queue.
- **Effort:** S-M. **Fit:** 3/5.
- **Change class + gate:** curation tooling feeding Paul's registry domain; the
  registry itself remains `derive_valence_registry.py --write` under his sign-off.
- **Validation plan:** retrospective $0 check IS permitted here because it pairs the
  tool with ALREADY-ADJUDICATED registry entries (no look risked on new claims): run
  the proposer over the existing registry's targets, report agreement with Paul's
  settled valences with denominators. High agreement = useful proposer; this grounds no
  validity claim about future targets, stated as such.
- **Dead-end adjacency:** the auto-registry kill is the near miss — five automated
  registries lost to curation. This proposal differs by construction: it produces QUEUE
  ENTRIES, not registry values. The write path stays Paul-only.
- **Main risks:** anchor bias (a plausible wrong proposal is stickier than a blank);
  mitigate by showing the rationale, not a naked label, and randomizing proposal order
  in the queue.

**Not imported from this paper:** the trained LTN layer (M-L effort; the 400-tweet gold
set is far too small to train BERT groundings without overfitting; product-logic
vanishing gradients; heavy dependency) — literature note only. The three-LLM MDF as
published (cost law). The paper's benchmark magnitudes as expectations (honest-
analogical: settings and directions, never magnitudes).

## 4. Paper 2 — Zhan & Cai: two-stage three-way dynamic consensus for SN-LSGDM (Expert Systems with Applications 2025)

Zhan, Cai (Hunan University), "A cost-minimized two-stage three-way dynamic consensus
mechanism for social network-large scale group decision-making: Utilizing K-nearest
neighbors for incomplete fuzzy preference relations," ESWA 263:125705 (2025), DOI
10.1016/j.eswa.2024.125705. New method (fuzzy decision science; no ML, no NLP, no real-
world data). Reader note: PDF is 20 pages (not the briefed 26); all read; Figures 1-9
raster; Table 1 symbol glossary partially unrecoverable.

**What it does.** For large groups submitting incomplete pairwise preference matrices
over a trust network: (1) impute missing cells by K-nearest-neighbors over the TRUST
network, weighting neighbors by trust × preference similarity, imputing
highest-reliability cells first and emitting a per-cell reliability score (Eqs. 11-17);
(2) cluster members by a blended distance of mutual influence and unit adjustment cost
(UAC), with adaptive k (Algorithms 1-2); (3) reach consensus by a two-stage three-way
decision: per subgroup, partition members into consent (Pos) / adjust-now (Neg) /
defer (Bnd) via a Comprehensive Adjustment Priority — CAP = β·(1−UAC) +
(1−β)/2·trust-toward-Pos + (1−β)/2·(1−consensus-degree) (Eq. 32) — then buy minimal
opinion movement from the Neg set by linear programming (Eq. 34, scipy linprog), with
a monotone trust update per round. Verbatim: "a two-stage minimum adjustment cost
consensus reaching mechanism based on three-way decision (TWD) is proposed, using
comprehensive adjustment priority as the criterion for division" (p.1).

**Honesty flags (reader-observed):** no real-world data anywhere (one 20-member case
borrowed from Gong et al. 2024; UACs randomly generated; simulations synthetic);
single figure-level baseline, no statistical tests; the trust update t* = t^(1−t) can
only INCREASE trust — no distrust, no decay, no signed edges; endogeneity — imputing
from trusted neighbors mechanically raises measured consensus, so part of the reported
"consensus improvement" is imputation-induced homophily; imputation MSE 0.09-0.13 on
[0,1] cells (≈RMSE 0.30-0.36) is coarse; thresholds chosen by fiat.

**Where it plugs in.** The mechanism's literal problem (a moderator herding a panel to
internal consensus) is ANALOGICAL to Melange's (an outside actor influencing
legislators) — every citation carries the honest-analogical flag. Three components
transfer as machinery; one is rejected.

### Proposal E1 — trust-KNN imputation with per-cell reliability, for sparse-coverage cells
- **What:** evaluate network-KNN imputation (edges: cosponsorship/committee/donor
  overlap; similarity: stance-profile agreement on co-known cells) for MISSING
  member×category stance cells, emitting the paper's per-cell reliability score, cells
  flagged IMPUTED everywhere they render.
- **Where:** stance-matrix data prep as a `.candidate` estimate layer — the repo
  already has the pattern (the desert-fill estimate layer, amendment-gated locks, per
  the desert-fill record): imputed values are display-flagged and never silently enter
  validated surfaces.
- **Expected benefit:** principled coverage expansion over the sparse stance corpus
  with an honesty score per cell — compatible with the honest-gap ethos precisely
  because cells stay flagged.
- **Effort:** M. **Fit:** 4/5.
- **Change class + gate:** estimate-layer change; anything reaching surfaces or ranks
  is Paul-gated; the '-' no-position ontology is load-bearing — an imputed cell must
  never overwrite a true '-' silently.
- **Validation plan:** Stage 4 IS the paper's own protocol, localized: mask-and-recover
  on KNOWN cells. Draft bars (to be prereg'd): imputation must beat, on masked known
  cells, (i) the global-mean baseline, (ii) the PARTY-mean baseline, and (iii) row/col
  marginal baselines — bar (ii) is the homophily-circularity gate: an imputer that only
  matches party means is party homophily wearing a network costume. Report MSE with
  denominators per stratum. Stage 5/6 — one look on the pre-declared mask; promotion
  display-first.
- **Dead-end adjacency:** honest-gap rulings (8-state QCEW: never relabel a gap) are
  satisfied by the IMPUTED flag; the desert-fill precedent shows the sanctioned shape.
  DE-001 untouched (no mention-density anywhere).
- **Main risks:** endogeneity (the paper's own flaw) — any downstream metric computed
  over imputed+real cells must also be reported real-only; network edges are not
  "trust" and the analogy could fail — the party-mean bar is the tripwire.

### Proposal E2 — CAP triage + minimum-cost LP as a candidate optimizer objective
- **What:** a three-way targeting artifact — act (Neg) / defer (Bnd) / already-aligned
  (Pos) — with an LP that minimizes total movement cost subject to proximity to the
  allied bloc, as a DIAGNOSTIC sibling of the existing allocator/frontier engines
  (JSON artifact, chain consumes nothing).
- **Where:** `fec/engine/` diagnostic, modeled on the `kb_benchmark` read-only pattern.
- **Expected benefit:** an explicit cost-of-movement objective and a formalized
  deferral class (watchlist) complementing cascade-reach maximization; comparable
  against the live allocator's picks under the ablation pattern.
- **Effort:** M-L. **Fit:** 3/5.
- **Change class + gate:** read-only diagnostic (lane work) UNTIL any surface or
  allocation consumes it — and note the AUDIENCE LAW: an act/defer/skip page is
  advisory copy, which surfaces must not carry (Paul, 2026-08-11). As shipped UI this
  is barred; as an engine-side artifact it is lawful. Stated so nobody ships it by
  enthusiasm.
- **Validation plan:** the UAC construct (per-member cost of movement) has NO empirical
  grounding — it inherits frontier problem 2's status (design choice, sensitivity-
  bounded at best). Honest sequencing: define UAC candidates from existing receptivity/
  susceptibility quantities, sensitivity-sweep them (the `receptivity_sensitivity`
  pattern), and pin any external test to the Problem-2 outcome-snapshot stream.
- **Dead-end adjacency:** the RL envelope stays untouched (this is one-shot LP, not a
  learned policy); no dial changes.
- **Main risks:** decision-support veneer over ungrounded constants — mitigated by the
  diagnostic-only class and the sensitivity sweep; LP feasibility at 533 is trivial
  compute-wise but the ε-proximity constraint needs a Melange-native meaning (stance
  bands, not fuzzy preference cells).

### Proposal E3 — cost-aware clustering with adaptive k, for coalition segmentation
- **What:** the paper's clustering (distance = blend of mutual influence and cost
  difference; adaptive centroid seeding by influence + mutual distance; Dunn/DBI
  validity checks) as a $0 structure probe over the 533 — do cost-aware segments
  differ materially from the existing communities (HCoI/press communities)?
- **Where:** a note INTO the coalition-builder redesign lane, which is already awaiting
  Paul's APPLY gate — no second lane opened.
- **Effort:** S-M (probe). **Fit:** 3/5.
- **Validation plan:** Stage 2 probe (structure-side only, no criterion pairing);
  adjusted-Rand comparison against existing community layers with counts; if segments
  are ~identical, record the negative for free.
- **Main risks:** none beyond wasted effort; kept strictly off ratified tier surfaces.

### Proposal E4 — monotone trust update — REJECTED; cite only
t* = t^(1−t) can only raise trust — behaviorally false for politics, produces no
signed/negative edges, and answers nothing in frontier 3. Literature note.

**Transferable caution (free import):** the paper's endogeneity flaw — metrics
computed over imputed data flatter the machinery that imputed it — becomes a standing
check wherever E1-class estimation ships: every coverage/consensus/accuracy figure is
reported real-cells-only alongside the augmented figure.

## 5. Paper 3 — BICAM: Bulk Ingestion of Congressional Actions and Materials (Scientific Data 2025)

Delano, Rudkin, Kim (MIT), "Bulk Ingestion of Congressional Actions and Materials
Dataset," Scientific Data 12:1567 (2025), DOI 10.1038/s41597-025-05737-8. Dataset
paper, MIT-licensed data+code. Reader note: PDF is 9 pages (not the briefed 20); all
read; Figures 1-2 raster.

**What it is.** An eleven-component relational database consolidating Congress.gov and
GovInfo APIs — Bills (421,764, 6th-119th Congress), Amendments (123,061), Members
(2,597 with bioguide+ICPSR), Committees (226 + 587 subcommittees with name history),
Reports (106,818), Prints, Meetings (12,238, 114th+ with witness lists), Hearings
(74,918 with transcripts sub-component), Treaties, Nominations, Congresses — with
standardized identifiers, a Bills↔Voteview crosswalk, and a **Bills↔LDA Section-16
linkage** built by fuzzy-matching bill references out of LD-2 lobbying-report text with
per-match confidence (pp.3-4). Incremental "catch-up" collection is supported. Verbatim:
"BICAM includes virtually all of the data which the U.S. Congress makes available."
(p.4). Data: https://bicam.net + Harvard Dataverse doi:10.7910/DVN/TALQZL; code:
github.com/bicam-data.

**Honesty flags (reader-observed):** the headline linkage claim ("significantly more
cases of bill lobbying than existing sources") is supported only in the Supplementary
Information, which is not in the PDF — unverified here; main-text validation is
qualitative data-integrity engineering, no precision/recall anywhere; internal count
inconsistency (408,000 vs 421,764 bills, pp.3/5); "1789 to the present" overstates
per-component coverage.

**Where it plugs in.** Three lanes: the LDA/network repository (frontier 3's data
substrate), the 120th-Congress rollover campaign, and the corpus layer's known soft
spot (CHRG finance-only).

### Proposal B1 — Bills↔LDA linkage as an additional lobbying-edge source
- **What:** adopt BICAM's bills-lobbied sub-component as a SECOND source of bill-level
  lobbying links beside the LobbyView-derived ones, including its ex-post (post-passage)
  lobbying links which current layers lack.
- **Where:** the network repository / contested_bills machinery / FEC-precognition
  lane's LDA side.
- **Expected benefit:** higher recall of industry-pressure-on-bill structure; a second
  independent linkage source enables a disagreement audit of the existing one.
- **Effort:** M. **Fit:** 5/5 (data lane), with the claims constraint below.
- **Change class + gate:** new data source. Reconciliation and shadow artifacts are
  lane work; ANY edge entering rank-feeding networks is a rank-moving change → full
  verification protocol + Paul.
- **Validation plan:** Stage 2 $0 reconciliation FIRST and as the decision evidence:
  join BICAM bills-lobbied against the existing LobbyView-derived link set on the
  CU-relevant bill universe (644 acts + the 18,557-bill corpus keys); report
  agree/only-BICAM/only-LobbyView counts with denominators and confidence-score
  distributions. The paper's recall claim is treated as UNVERIFIED until this local
  reconciliation reproduces it. Stage 3 — if edges are to feed engines: prereg with
  join-rate floors and disagreement ceilings pre-declared; planted-edge battery
  (Stage 4) before any kernel consumes them; external-criterion ablation per frontier
  3's `kb_benchmark` pattern.
- **Dead-end adjacency:** **FEC×LDA R3 is binding** — structure explains the FEC→LDA
  lead; predictor-language is BARRED for anything built on these links. New edges are
  STRUCTURE. Any write-up inherits that wording constraint verbatim.
- **Main risks:** fuzzy-match confidence thresholds are the paper's own soft spot
  (SI-only validation); appropriations bills are called out by the authors as a special
  error class; key normalization (BICAM bill_id ↔ repo bill keys) must be proven on
  counts before anything else.

### Proposal B2 — rollover backbone: members/committees crosswalks + catch-up collection
- **What:** use BICAM members.csv (bioguide+ICPSR, party-switch and term handling) and
  Committees-with-history as the roster/committee-code crosswalk source for the
  119th→120th rollover, with the catch-up collector as the freshness mechanism.
- **Where:** `moneyball-congress-rollover-campaign` (roster swap, HS120, committee
  re-map).
- **Expected benefit:** replaces hand-stitched voteview/legislators.csv joins at the
  single riskiest scheduled event in the system's life; committee codes are already the
  THOMAS scheme used repo-side.
- **Effort:** S-M. **Fit:** 4/5.
- **Change class + gate:** rollover campaign work — owned by that campaign's own
  decision gates and validation bars (533-roster invariant, pinned totals, workbook row
  drift checks). Nothing moves before the campaign says so.
- **Validation plan:** Stage 2 reconciliation: BICAM members vs legislators.csv +
  voteview for the 119th (exact-match counts, delegate/commissioner filtering proven to
  reproduce 533), committee-code crosswalk coverage counts. Adopt only where
  reconciliation is exact or the disagreement is adjudicated.
- **Dead-end adjacency:** roster membership is Paul's domain (mentat roster rule: only
  companies/rosters Paul lists — the congressional analogue: the 533 roster is
  invariant until the rollover campaign moves it).
- **Main risks:** BICAM's 120th-update timing is a promise, not an SLA — the campaign
  cannot depend on it; keep the existing pipeline as primary until BICAM proves fresher.

### Proposal B3 — hearings/witness corpus expansion
- **What:** use BICAM Hearings (74,918, transcripts sub-component) to close the "CHRG
  finance-only" corpus soft spot, and Meetings witness lists (114th+) as a candidate
  witness-appearance layer (industry witness ↔ member) for the multiplex.
- **Where:** corpus collectors + `fec/network/build_multilayer_network.py` (candidate
  layer, `.candidate` until ratified).
- **Expected benefit:** broader antagonism/stance text base (hearing antagonism is the
  A/ES lever per the psych ledger, with the chair/majority confound noted there); a
  novel edge type for frontier 3.
- **Effort:** M-L. **Fit:** 3/5.
- **Change class + gate:** corpus collection (lane work, but scheduled around Paul's
  live jobs); any new network LAYER is an engine-input change → Paul.
- **Validation plan:** collection inherits the 5a/5b lessons as REQUIREMENTS: dates on
  every row (the two dateless-collector-legs incident), smoke tests through the
  production enumeration path, freshness audit checks paired with any cache. Witness-
  edge signing gets a planted-edge battery before any kernel touch.
- **Dead-end adjacency:** none killed; note the desk 27MB footprint constraint —
  corpus growth must not bloat shipped surfaces.
- **Main risks:** witness documents are PDF-only upstream (extraction deferred by the
  authors); transcript completeness varies by era; hearing text ≠ live-interview text
  (it does NOT feed the MEM_N reactivity gate, which is interview-specific — stated so
  nobody double-books that benefit).

### Proposal B4 — bills backbone swap — REJECTED FOR NOW; use BICAM as a reconciliation oracle instead
The full-text corpus is complete (18,557/18,557 per the legfix5 collection record,
2026-07-27) and the legfix5 culling review is a live Paul-gated lane; swapping
backbones under it would churn a gated review. Instead:
S-effort $0 probe using BICAM as a SECOND OPINION — reconcile bill metadata for the
644-act universe (status, versions, sponsor/cosponsor counts) and surface disagreements
as evidence rows. This also bears on the STATE open question about the two ACRE-pair
acts classified from BILLSTATUS metadata only: BICAM offers an independent metadata
path to corroborate or contradict those rows. Fit: 4/5 as an oracle. Gate: evidence
goes to Paul; no reclassification by model judgment.

## 6. Paper 4 — CampaignView: policy platforms and biographies for congressional candidates (Scientific Data 2025)

Porter, Case, Treul, "CampaignView, a database of policy platforms and biographical
narratives for congressional candidates," Scientific Data 12:1237 (2025), DOI
10.1038/s41597-025-05491-x. Dataset paper, CC0 on Harvard Dataverse
(doi:10.7910/DVN/JIEAPT) + campaignview.org. Reader note: PDF is 12 pages (not the
briefed 24); complete; the reader's first extraction transiently picked up fragments of
an unrelated ESWA consensus-models paper — excluded after re-extraction; Figures 1-3
raster.

**What it is.** Real-time-collected campaign-website text for 5,228 of 6,016
major-party ballot-eligible U.S. House candidates 2018-2022 (86.9%, p.1): 43,465
platform points hand-labeled with 14 Major Policy Topics (crosswalked to Policy Agendas
and CRS coding), 5,114 biographical narratives, FEC + BioGuide identifiers, candidate
covariates, primary/general outcomes. Verbatim: "Our corpus covers 5,228 candidates,
representing 86.9% of major-party, ballot-eligible contenders who ran for the U.S.
House of Representatives between 2018 and 2022." (p.1).

**Honesty flags (reader-observed):** missingness is systematically correlated with
campaign seriousness (incumbency coefficient −2.967 on website-missingness, Table 5
p.8) — the corpus over-represents viable campaigns; the reported Cohen's kappa (0.84)
EXCEEDS raw percent agreement (0.80), which is arithmetically impossible for standard
kappa — treat 80% agreement as the reliability figure and the kappa as suspect; topic
labels only (no stance/valence); no financial-services-specific topic (banking/credit
folds into "Economics and Commerce"); coverage stops at 2022.

**Where it plugs in.** The 120th-Congress rollover (freshman cold-start), frontier
problem 1 (a second same-person text context), and gold-label QA.

### Proposal C1 — freshman cold-start corpus for the rollover
- **What:** merge CampaignView bios+platforms by BioGuideID/FECCandID for members first
  elected 2018-2022, and — the real prize — replicate the collection protocol for 2026
  candidates so incoming 120th freshmen arrive with pre-office text on day one.
- **Where:** corpus layer + `moneyball-congress-rollover-campaign` (the freshman-impact
  problem: zero floor/press/interview history at seating).
- **Expected benefit:** day-one priors for stance banding, salience, and display-layer
  psychometrics where today there is NOTHING; the paper's cited literature (Sulkin)
  supports campaign-priorities → legislative-priorities transfer as the design prior.
- **Effort:** M (merge); L (2026 replication — a real collection project with the
  paper's protocol as the runbook). **Fit:** 5/5 for the rollover.
- **Change class + gate:** new corpus source (lane work) → but ANY model consumption
  (priors feeding receptivity/stance/ranks) is an engine change, Paul-gated, prereg'd.
  Display-first is the house pattern (the instrument firewall).
- **Validation plan:** Stage 2 — identity-join reconciliation with counts (BioGuide for
  incumbents, FECCandID else; the paper's own linkage audit found 16 wrong links, p.8 —
  spot-audit ours the same way). Stage 3 — any claim that campaign text predicts
  in-office behavior is a prereg'd look against the members already in both corpora
  (the 2018-2022 entrants), with the transfer correlation bars set by power arithmetic
  BEFORE the 2026 collection is relied on.
- **Dead-end adjacency:** none killed; the YouTube-captions lesson (drop-never-guess on
  identity) applies to candidate-site attribution — collection must keep provenance per
  page.
- **Main risks:** ghostwriting (staff-crafted persona, not member disposition) — the
  same reason RKH text-derived agreement is only shared-method evidence; staleness
  (2022 data cover only returning members; the 2026 replication is the part that pays);
  House-only (no Senate freshmen).

### Proposal C2 — cross-context trait-stability corroboration (frontier 1 adjacent)
- **What:** for members present in both corpora, compute the EXISTING validated
  instruments on campaign text vs congressional text and measure per-trait cross-
  context agreement — a measurement-invariance corroboration, not a new instrument.
- **Where:** psychometrics lane; read-only over both corpora.
- **Expected benefit:** cross-situational consistency evidence for O/C/E at n≈150-300
  (exact overlap to be counted in Stage 2) — a context-robustness line the program
  currently cannot write.
- **Effort:** M. **Fit:** 3/5.
- **Change class + gate:** research look; prereg + one look; no engine consequence
  pre-declarable except annotation.
- **Validation plan:** Stage 2 — count the overlap roster and its per-trait coverage
  ($0, criterion-side); run the power arithmetic; if honest power < ~80% against a
  plausible stability effect, LABEL IT CORROBORATION with tiered wording per
  methodology §10, or pin a data gate. Stage 3 — prereg with the gender/party partials
  as gating bars (the recurring confound), genre-composition disclosed as an adverse
  prior (campaign text is a distinct genre — the E genre caveat generalizes). Stage 4
  — plant battery on the overlap stratum before the look (the round-4/5 lesson:
  n≈200-300 strata refuse looks below E-class signals; expect and honor a refusal).
- **Dead-end adjacency:** instrument-side lexical refits are killed (three bases); this
  is NOT a new basis — it applies the EXISTING instrument to a second context. The
  blue-on-pink calibration prohibition is untouched (same instrument, two contexts).
  CT-CM latent modeling stays closed — report the agreement matrix; fit no latent
  factors.
- **Main risks:** the battery refuses at the achievable n (honest outcome: RETIRED
  WITHOUT A LOOK with a pinned gate — record it and stop); ghostwriting produces
  context DIVERGENCE that is real but uninterpretable as instrument failure — the
  prereg's consequences section must pre-word that reading.

### Proposal C3 — campaign-revealed issue-attention priors (display-only)
- **What:** candidate-year 14-topic emphasis vectors, crosswalked (their Table 6, p.10)
  to CRS policy areas already on the bills corpus, surfaced as a display-only
  "pre-office attention" line on member pages for 2018-2022 entrants.
- **Where:** desk/member surfaces (display plane).
- **Effort:** S. **Fit:** 3/5.
- **Change class + gate:** display change → per-surface rules (rankings-and-data-only
  law; full-fidelity mockup for Paul before deploy).
- **Validation plan:** none needed beyond provenance (descriptive data, labeled with
  window and denominator per the claims constraint).
- **Dead-end adjacency:** **DE-001 guard stated explicitly:** topic-share vectors are
  member-attention description and are NEVER an input to act/industry relevance pricing
  (mention-density relevance is a dead end; the tensor is priced by operative text and
  Paul's centering test only).
- **Main risks:** the missing financial-services topic dilutes exactly our sector —
  the display line must name the "Economics and Commerce" bucket honestly rather than
  implying CU-specific salience.

### Proposal C4 — annotation-QA resample protocol for the gold sets
- **What:** adopt their reliability design — random ~20% relabel sample, never-your-own
  -prior-work, agreement + kappa + disagreement audit — as a periodic QA pass over the
  stance/valence gold sets (the 400 tweet golds + press golds).
- **Where:** gold-label machinery (`moneyball-validation-and-qa` owns acceptance
  thresholds).
- **Expected benefit:** a label-stability number for the very sets every stance claim
  is scored against; currently the program has adjudication but no periodic drift
  check.
- **Effort:** S (tooling); the labeling time is Paul's — this is a proposal for HIS
  time and stands or falls on his appetite. **Fit:** 3/5.
- **Change class + gate:** QA protocol addition; gold labels remain Paul's domain — the
  resample measures stability of HIS rulings, his current ruling stays final on any
  disagreement.
- **Validation plan:** import the DESIGN, not their arithmetic — their kappa exceeds
  their raw agreement, which standard Cohen's kappa cannot do (reader-verified, p.8);
  compute agreement and kappa from our own counts with the formula in the QA skill.
- **Dead-end adjacency:** this is NOT the expert panel (external human raters for
  psychometrics, canceled, never re-propose) — it is Paul re-checking Paul's own
  labels; stated to keep the boundary bright.
- **Main risks:** none technical; purely a time ask.

## 7. Paper 5 — SNGDM survey: social network group decision making from an AI/LLM perspective (Information Fusion 2025)

Cao, Gai, Wu et al. (incl. Chiclana, Dong, Herrera-Viedma, Herrera), "Social network
group decision making: Characterization, taxonomy, challenges and future directions
from an AI and LLMs perspective," Information Fusion 120:103107 (2025), DOI
10.1016/j.inffus.2025.103107. Survey (917-paper bibliometric corpus; no method, no
data, no code). Reader note: PDF is 18 pages (not the briefed 45); all read via text
extraction; Figures 1-8 raster, bibliometric chart values not extractable.

**What it covers.** The fuzzy-consensus school's decade of "SNGDM": trust modeling
(representation, propagation — including SIGNED trust/distrust operators; evolution),
internal structure (consensus measurement, power weighting, community structure —
including overlapping-community bridge effects), and consensus mechanisms (feedback,
opinion dynamics — DeGroot/Hegselmann-Krause; behavior management — manipulation
detection). Reader-flagged limits: purely narrative, zero quantitative method
comparison; surveyed models validated on toy expert panels — verbatim: the field
"mainly constructs social networks through questionnaires or directly pre-sets social
networks" (p.13); the author group is itself the central cluster in its own
collaboration map.

**Where it plugs in.** Mostly as a CITATION MAP and design-prior source for frontier
problem 3 (signed-multiplex influence maximization) — and as independent confirmation
that psychologically heterogeneous, signed, real-data influence modeling is rare in
this adjacent literature too (the frontier framing holds up against a second field).

### Proposal S1 — signed trust/distrust propagation as candidate edge completion
- **What:** evaluate one coupled trust-distrust propagation operator family (Guha et
  al. WWW 2004 matrix propagation; the uninorm and dual-Einstein operators the survey
  catalogs, p.7) for COMPLETING missing signed member-member edges in the multiplex,
  with path decay.
- **Where:** `fec/network/` as a `.candidate` edge layer; never a kernel input without
  the full gauntlet.
- **Expected benefit:** denser signed structure for frontier 3; a principled
  alternative to leaving unknown edges absent.
- **Effort:** M. **Fit:** 3/5.
- **Change class + gate:** engine-input change (rank-moving if consumed) → Paul, after
  the full verification protocol.
- **Validation plan:** Stage 4 FIRST is the heart: a planted-edge battery — remove
  known edges, verify recovery; plant nulls, verify refusal; only an operator that
  passes proceeds to Stage 3 prereg with an external criterion pinned in advance
  (post-freeze cosponsorship adoption via the Problem-2 snapshot, or observed money
  flows per the `kb_benchmark` pattern) and the unsigned/absent-edge ablation as the
  comparator.
- **Dead-end adjacency:** none killed; nearest law is the two-cpf-physics invariant —
  this proposal completes EDGES, it does not add a physics.
- **Main risks:** trust-transitivity axioms are unvalidated for congressional
  relationships — the operators could fabricate confident edges out of ideology
  homophily; that is exactly what the planted-edge battery exists to catch, and a
  refusal retires the idea without a look.

### Proposal S2 — bounded-confidence opinion dynamics as a third physics — DO NOT BUILD; cite only
A third propagation physics (graded stance drift vs binary activation) collides with
the load-bearing two-named-cpf-physics invariant, costs L, and inherits frontier 2's
unsolved outcome validation. Recorded as literature (DeGroot/HK + the mixed TSMC 2022
model) for the day Paul opens an engine-physics question; not proposed.

### Proposal S3 — overlapping-community bridge candidates for the coalition builder
- **What:** a $0 discrimination probe: does overlapping-community membership
  (committee/caucus/donor communities) even DISCRIMINATE among 533 members, or is
  overlap near-universal? If it discriminates, hand the measure to the coalition-
  builder lane as a candidate feature.
- **Where:** the coalition-builder redesign — which is ALREADY awaiting Paul's APPLY
  gate; this folds INTO that gated lane as a note, it does not open a second lane.
- **Effort:** S (probe). **Fit:** 3/5.
- **Validation plan:** the probe is Stage 2 by construction (structure-side only). The
  survey's own evidence (Gai et al. 2024: overlapping members raise compromise
  willingness) is toy-panel evidence — design prior only, honest-analogical.
- **Main risks:** non-discrimination (likely) — in which case the probe's negative is
  recorded and the idea dies for free.

### Proposal S4 — citation/annobib enrichment
S-effort: add the survey's signed-propagation operator family, the manipulation-
detection line (Xiong et al. 2024 — adversarial-robustness framing for engine inputs),
and its LLM-psychometrics pointers (Rao 2023; Yan 2024) to the annotated bibliography
as frontier-1/-3 literature anchors, under the citation-honesty standard (settings and
directions, never magnitudes). Fit: 3/5. No gate beyond docs duties.

## 8. Cross-paper synthesis and priority slate

### 8.1 The map — papers × frontier problems

| Frontier problem | Served by | How |
|---|---|---|
| P1 behavioral-criterion LLM psychometrics | CampaignView (C2); survey refs (S4) | a second same-person text context for corroboration; two LLM-psychometrics citations |
| P2 prospective outcome validation | ESWA (E2, negatively) | E2's cost construct is UNGROUNDED until P2 delivers — a new consumer waiting on the already-armed snapshot (scoreable ~2026-09-02) |
| P3 signed-multiplex influence max | Survey (S1), BICAM (B1, B3) | signed propagation operators for edge completion; denser LDA edges; a candidate witness layer |
| P4 stance→valence bottleneck | FOLAR (F1, F2, F4), CampaignView (C4) | FOL-formatted prompting for the model hop; rationale tooling for Paul's curation; gold-set QA |
| P5 cross-modal personality | **none** | honest zero — no paper touches audio; P5 stays where it was (MFCC route untried) |
| Rollover campaign (not a frontier problem, but the calendar) | CampaignView (C1), BICAM (B2) | freshman cold-start text; roster/committee crosswalk + catch-up collection |

Meta-observation (one line, honest-analogical, and from ONE school — the survey admits
its own group's centrality in the field, p.4): the two SNGDM papers indicate that the
adjacent consensus-modeling field runs on questionnaire/preset networks and toy panels
("mainly constructs social networks through questionnaires or directly pre-sets social
networks," survey p.13) — Melange's frontier-3 combination (signed + multiplex +
psychologically heterogeneous receivers + real behavioral data) is absent there too.
This supports the frontier FRAMING; it is zero evidence our methods work.

### 8.2 The one time-boxed item — flagged before any tiering

**The 2026 campaign-site collection window closes at the November election.**
CampaignView's released data stop at 2022; the freshman-prior value for the 120th
Congress requires collecting the 2026 candidates' sites while they are live. Campaign
sites decay within weeks of losing (and often of winning). Collecting the
general-election universe (~870 House candidates + the Senate class, both parties) in
September-October 2026, per the paper's protocol (bio + issues subpages, one page per
candidate, provenance kept), yields pre-office text for nearly every incoming freshman
at seating 2027-01-03 (winner web-presence ran 88-99% in the paper's cycles: 88.3% had
a platform, 99.0% a biography among general-election winners, digest p.7). This is the
only proposal in this document that expires. Effort: L as a collection lane, but well
under the paper's sweep — the general-election universe is roughly 2 candidates per
seat vs the ~2,000-candidates-per-cycle primary universe the paper covered. Gate: Paul
authorizes the lane; collection discipline per the 5a/5b lessons (dates,
production-path smoke tests, glassbox emission).

### 8.3 Priority slate

**Tier NOW — cheap, inside standing law, start on Paul's word:**
1. **C1-2026 collection** (see 8.2; the clock is the reason it leads).
2. **B1 probe** — BICAM×LobbyView reconciliation counts on the CU bill universe ($0
   decision evidence for the biggest data-lane win).
3. **B4** — BICAM as metadata second-opinion on the ACRE pair and the L4-rung acts
   (feeds two OPEN questions already in the brain's STATE).
4. **F2** — FOL rationales attached to Paul's adjudication queues (the sanctioned
   curation-tooling lane; smallest build with a visible quality-of-life win).
5. **E3 + S3** — the two $0 structure probes, folded as notes into the already-gated
   coalition-builder lane.

**Tier PREREG — research looks; each needs a locked prereg, battery, and Paul's
awareness that a look gets consumed:**
6. **F1** — FOL-CoT valence-hop candidate (the one proposal aimed square at the 0.689
   number; S build, honest-prior section must discount the paper's benchmarks).
7. **E1** — trust-KNN imputation with the party-mean homophily bar (display-first
   estimate layer).
8. **C2** — cross-context trait corroboration (battery may refuse at the overlap n —
   an honest RETIRED WITHOUT A LOOK is a fine outcome and costs nothing).
9. **S1** — signed edge completion, planted-edge battery first.

**Tier STRATEGIC — bigger builds, sequenced with existing campaigns:**
10. **B2** — BICAM rollover backbone (reconcile now; adopt only through the rollover
    campaign's own gates).
11. **B3** — hearings/witness corpus expansion + candidate witness layer.
12. **E2** — CAP/LP three-way targeting diagnostic (engine-side only; surface barred
    by the audience law; cost construct waits on P2).

**PARKED / REJECTED (recorded so they are not re-proposed casually):**
- F3 multi-frontier-LLM stance fusion — conflicts with the Haiku-only cost law;
  Paul-only to open.
- S2 bounded-confidence third physics — collides with the two-cpf-physics invariant;
  cite only.
- E4 monotone trust update — behaviorally false; cite only.
- FOLAR trained-LTN layer — gold set too small; heavy dependency.
- BICAM bills-backbone swap — churns the live legfix5 Paul-gated lane; oracle use
  instead (B4).

### 8.4 Decision menu for Paul

Each line is one decision; nothing proceeds without it.
1. Authorize the 2026 campaign-site collection lane (8.2) — the expiring one.
2. Authorize the two $0 reconciliation probes (B1, B4) — read-only evidence, no writes
   beyond scratch artifacts.
3. Approve F2 (rationales in your queues) — changes your adjudication view, nobody
   else's.
4. Pick which (if any) Tier-PREREG item gets a prereg drafted FIRST (F1 is the
   recommendation — it attacks the named bottleneck at S effort).
5. Rule whether the MEM_N gate check should be run now. Raw reactivity coverage (270)
   now exceeds the gate VALUE (250), but the gate itself binds on MEM_N — the
   intersection with the §17-eligible roster — which has not been counted; counting it
   is synthetic-side and risks no look. Not paper-derived, but observed while grounding
   this document (§1.3).
6. (Standing) The outcome snapshot at `data\engine\outcome_snapshot_2026-07-04.json`
   becomes scoreable ~2026-09-02 — calendar item, one command, refusal rules built in.

## 9. Compliance annex

### 9.1 Dead-end / decision adjacency table

Every proposal was screened (Stage 0) against the kill-ledger, the brain's DEADENDS
and DECISIONS, and standing prohibitions. Items with a real adjacency:

| Proposal | Adjacent settled item | Resolution |
|---|---|---|
| F1/F2/F4 | Auto-valence registries killed (@827f211); stance labels = Paul (non-negotiable #1) | model leg + queue tooling only; registry write path untouched |
| F3 | Haiku-only LLM cost rule (session-ratified 2026-07) | PARKED; conflict stated, not worked around |
| B1 | FEC×LDA R3: predictor-language BARRED | edges are structure; wording constraint inherited verbatim |
| B2 | 533-roster invariance; rollover campaign owns sequencing | reconciliation only until the campaign's gates open |
| B4 | Never reclassify by model judgment (D-005 spirit: no per-act repricing by proximity) | evidence rows to Paul; no reclassification |
| C1 | drop-never-guess identity rule (YouTube captions kill) | per-page provenance required in collection |
| C2 | three lexical-basis refits killed; CT-CM closed; blue-on-pink prohibition | same instrument, two contexts; no latent factors; no cross-instrument calibration |
| C3 | DE-001 mention-density relevance | attention display only; never prices act relevance |
| C4 | Expert panel canceled (never re-propose raters) | Paul re-checks Paul's labels; no external raters |
| E1 | Honest-gap rulings (QCEW); '-' ontology; desert-fill precedent | IMPUTED flag everywhere; '-' never silently overwritten |
| E2 | RL envelope (Paul's roadmap); audience law (no advisory surfaces) | one-shot LP diagnostic; no surface |
| S1 | two-cpf-physics invariant | edge completion, not a physics |
| S2 | two-cpf-physics invariant | rejected outright |

### 9.2 Citation-honesty notes for these five papers

House standard: honest-analogical — settings, principles, directions; magnitudes are
local calibration; citing a paper never transfers its evidence to our constants.
Paper-specific cautions for any future write-up:
- **FOLAR:** quote zero-shot VAST 81.0 vs 76.8 and FOL-CoT 79.8 vs plain-CoT 73.4
  (Table 4, p.7) only with the contamination caveat (public-figure targets predate LLM
  cutoffs) and the short-text domain note; in-target superiority has named exceptions
  (Table 3, p.6).
- **BICAM:** the linkage-recall claim ("significantly more cases of bill lobbying") is
  Supplementary-Information-only and was NOT verified here — cite as the authors'
  claim, rely only after local reconciliation (B1 probe).
- **CampaignView:** coverage 86.9% of 6,016 (p.1) is quotable; the kappa 0.84 is
  arithmetically inconsistent with the 80% raw agreement it accompanies (p.8) — lean
  on the 80% figure; missingness is seriousness-correlated (Table 5, p.8) — the corpus
  over-represents viable campaigns.
- **Zhan & Cai (ESWA):** no real-world data in the paper; all magnitudes are worked-
  example or synthetic; the consensus problem is analogical to lobbying, not identical
  — flag every citation honest-analogical.
- **SNGDM survey:** narrative, no benchmarks; useful as a citation map (917-paper
  corpus, cutoff 2024-09-25, WoS-only, single-school centrality admitted p.4).

### 9.3 Provenance and re-verification (volatile facts cited in this document)

| Fact | As of | Re-verify |
|---|---|---|
| Stance ladder 0.915 / 0.689 / 0.872 | 2026-08-14 | `Select-String -Path fec\stance\apply_two_hop_stance.py -Pattern "0.915"` |
| Raw reactivity_z coverage 270 | 2026-08-14 (live tree) | the coverage one-liner in §1.3 (reads `behavioral_dispositions.json` only) |
| N-route gate MEM_N ≥ 250; MEM_N = MEM ∩ reactivity_z non-null (201 at lock) | prereg vintage | `Select-String -Path big5_n_matrix_prereg.md -Pattern "MEM_N"` |
| Outcome snapshot at `data\engine\outcome_snapshot_2026-07-04.json`; scoreable ~2026-09-02 | 2026-08-14 | `Get-ChildItem "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\data\engine\outcome_snapshot_*.json"` |
| Worktree base = main @846d90ae3 | 2026-08-14 | `git log --oneline -1` in the worktree |
| audit_full 202 passed / 1 FAILED (Paul-gated legfix5 item) | brain STATE 2026-08-14 | re-run per `moneyball-diagnostics-and-tooling` |
| TODO open items referenced (94-row CFPB queue, stranded codex worktrees, electoral_plays gate) | 2026-08-14 | `TODO.md` §1 |

### 9.4 Reader integrity record (how the papers were read)

Five parallel reader agents, one per PDF, each returning the §0 digest schema with
page-anchored verbatim quotes. Material notes:
- **Page counts:** every PDF's harness-reported page count exceeded the count the
  readers observed after extraction (26→20, 24→12, 45→18, 18→10, 20→9). Each reader
  verified article completeness by content (abstract through references/license) and
  matched the file to its DOI/PII identity. The digests describe the articles as
  extracted.
- **Cross-contamination incident (operational lesson):** two readers transiently
  observed fragments of a SIBLING paper mid-extraction (the CampaignView reader saw
  ESWA consensus-models pages; the ESWA reader saw CampaignView/FOLAR fragments). Both
  attributed it to concurrent agents sharing a scratch path, re-extracted cleanly, and
  self-verified against the correct PII/DOI. Lesson for future fan-outs: give parallel
  readers DISJOINT scratch filenames. No contaminated content is believed to survive
  in the digests (each was identity-checked), but any load-bearing quote should be
  spot-checked against the PDF before external use.
- **Raster figures:** none of the readers could inspect figure interiors (bibliometric
  charts, ablation bars); figure claims come from captions and body text only.

### 9.5 Standing status of this document

Dated record (frozen-vintage class once merged). It proposes; it does not authorize.
Implementation of any item requires: Paul's decision from §8.4, the owning skill loaded
(`moneyball-change-control` first), and for research items a locked prereg per
`moneyball-research-methodology`. If any §9.3 fact fails re-verification, fix THIS
document's copy against the source of record, never the reverse.
