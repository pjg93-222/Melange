# RESEARCH INTEGRATION 2026-08-14 -- five-paper review against the Melange system

STATUS: PROPOSAL. This is a dated examination record (frozen vintage on adoption). Nothing in it is
ratified, nothing here changes an engine, artifact, dial, surface, or test. Every APPLY step named
below is Paul's gate. Prepared under the D-007 findings-examination standard: every figure quoted
from a paper carries its window and denominator; figure-only numbers (plots we could not extract)
are excluded rather than approximated.

## 0. Provenance

Task: Paul's directive this session -- read five uploaded articles, derive how they apply to
melange, produce a guiding document and validation framework.

Sources (SHA-256 of the PDFs as received in Downloads, uppercase as printed by Get-FileHash):

| Key | File | SHA-256 | Identity |
|---|---|---|---|
| A | 1-s2.0-S0957417424025727-main.pdf | DC506A7C4F270E3ECC6924DD6C247DC2CD8E94A24D57C16AF955588ACCD56DAE | Zhan and Cai, ESWA 263 (2025) 125705 |
| B | s41597-025-05491-x.pdf | 82C914FDFDE26593E0ABB918A224F3F67792F3D3A554E1CD22204EFF94E6286F | Porter, Case and Treul, Scientific Data 12:1237 (2025) |
| C | 1-s2.0-S1566253525001800-main.pdf | 8A79464F6782F71522CDB74C778E761C4297AAC69764305FC7DEA346435E2894 | Cao et al., Information Fusion 120 (2025) 103107 |
| D | 1-s2.0-S0893608024008852-main.pdf | ED50ECC3FFE499A32895AC3C5E491F459C44090ABEC984130497C78E011DBB55 | Dai et al., Neural Networks 183 (2025) 106956 |
| E | s41597-025-05737-8.pdf | 59D11D0FFA4360AC39DD13F7EC14B14B6B3D4D5BE0342CDBA9387FED3751164F | Delano, Rudkin and Kim, Scientific Data 12:1567 (2025) |

Copies of the five PDFs are added under research/ with descriptive names (this commit).

Ingestion route and its honest limits: the Read tool's PDF renderer is unavailable on this box
(pdftoppm/poppler absent; flagged to Paul as a separate task). Text was extracted with PyMuPDF
into per-page-marked text files; five parallel read-only digest agents produced structured
digests (glassbox run-research-integration-20260814 carries the emitted agent pairs, including
the first blocked round); the coordinator then re-verified every number quoted in this document
against the extracted text directly before inclusion. Figures/plots were NOT ingested -- any
result that exists only in a figure is marked "figure-only" and not quoted as a number. A few
formulas were garbled by extraction; low-confidence reconstructions are flagged where they matter.

## 1. The receiving system: state, ethos, constraints

Melange (Moneyball) models how a credit-union advocacy shop moves Congress: 533 members x 18 CU
issue categories; stance matrix + media blend + multiplex network + receptivity psychometrics
feeding IC/LT influence engines, greedy submodular budget allocation, and lobbyist-facing
surfaces. Rank authority is ranks_python.json; the primacy/industry boards sit beside it. As of
2026-08-14: main at 6e27bcb2c, kernel gate 153/0 on the live tree 2026-08-13 (154 after the
846d90ae3 merge this worktree tips at), audit_full 202/1 (the 1 = Paul-gated legfix5 culling),
ratified board Tier 1 ending 11 Sherman / 12 Vargas / 13 Rounds.

The ethos that decides what these papers may touch:

1. EMPIRICAL GROUNDING. Every network edge is observed behavior (cosponsorship counts, press
   cross-engagement, social reposts -- Fink-normalized empirical probabilities), never assumed,
   never imputed. Every validity claim is earned through prereg -> battery -> ONE look.
2. HONEST GAPS. A '-' stance cell means "no recorded position" (59.8% of cells at the 2026-07-09
   vintage) and is PRICED as designed (PERS_NONE=0.45 Ally parity, user-ratified), not filled.
   Missing data is displayed as missing (the 8-state QCEW precedent: relabeling a gap is a defect).
3. USER DOMAINS. Stance/press classification, valence registry curation, gold labels, promotions,
   and anything rank-moving are Paul's. Sessions build mechanisms and candidates (.candidate
   convention), never fait accompli.
4. AUDIENCE LAW. Surfaces show rankings and data only -- no advisory copy (Paul, 2026-08-11).
5. COST RULE. Fable/Opus only for the 533 narratives; every other LLM step is Haiku 4.5.
6. CLAIM HYGIENE. Window + denominator in the same sentence; stratified or labeled UNSTRATIFIED;
   citations are honest-analogical ("we borrowed this mechanism"), never "this paper validated us."

Constraint checklist a proposal must clear before it is even a candidate (with the recorded law):
no mention-density relevance (DE-001); no per-item repricing outside a pre-registered class rule
(D-005); no reading tag authority/rationale as position provenance (DE-003); no re-running consumed
looks or retired routes (one-look law; round-6 anti-basis-shopping clause for any new instrument
basis); no RL envelope building uninvited (Paul's roadmap); no weakening tests/floors/counts to
pass (change-control law 7); Python-JS engine mirror stays in lockstep or the change waits;
worktrees do not isolate the data plane (verify in the live tree); everything emits to glassbox.

Frontier anchor points these papers land on (moneyball-research-frontier, all CANDIDATE/OPEN):
P-1 behavioral-criterion LLM psychometrics (N-route DATA-GATED MEM_N >= 250, was 201/456 at
2026-07-09; A-route bound by the round-6 anti-basis-shopping clause), P-2 prospective outcome
validation (outcome_snapshot_2026-07-04.json armed; scoreable ~2026-09-02 if >= 150 movers;
bars in fec/engine/outcome_snapshot.py:14-17 re-verified today), P-3 signed-multiplex IM
ablation benchmark (unbuilt), P-4 stance->valence bottleneck (stance-hop 0.915 / valence-hop
0.689 on the 400 tweet golds, compose ceiling 0.872 -- re-verified today at
fec/stance/apply_two_hop_stance.py:4-5), P-5 cross-modal personality (MFCC voice-C route untried).

## 2. The five papers -- what they are and what they establish

### A. Zhan and Cai 2025 (ESWA 263:125705) -- cost-minimized two-stage three-way dynamic consensus for SN-LSGDM
Mechanism paper from the social-network group-decision-making (SNGDM) field. Pipeline: KNN
trust-based imputation of missing fuzzy preference entries; k-means-style clustering whose
distance blends mutual trust, preference similarity, AND per-member unit adjustment cost (UAC);
three-way partitioning each round into Pos (consensus met), Neg (adjust now), Bnd (defer) via a
Comprehensive Adjustment Priority CAP = beta*(1-UAC) + w*(trust toward Pos) + w*(distance from
consensus), with a lambda dial trading speed against completeness; a linear program minimizing
sum(UAC x |opinion change|) subject to reaching threshold; and a trust update t* = t^(1-t) that
only ever increases trust. Validation is entirely numerical: the 20-DM case study's preferences
and trust matrix are copied from a prior paper's example, UACs are randomly generated, scaling
runs are synthetic (50-5000 DMs), and the imputation robustness claim is "estimation error
remains within a small range of 0.09 to 0.13" (average MSE, synthetic grids, 10 repeats/cell).
No human participants or observed behavior anywhere. Code link printed:
github.com/JustinaZhan/Datasets-and-code; "Data will be made available on request."

### B. Porter, Case and Treul 2025 (Scientific Data 12:1237) -- CampaignView
Data descriptor. Campaign-website text for U.S. House major-party primary candidates, three
cycles (2018/2020/2022): 5,228 of 6,016 ballot-eligible candidates covered (86.9%); 43,465
platform points (policy statements parsed at the sub-heading level) + 5,114 biographical
narratives; each platform point hand-labeled with one of fourteen Major Policy Topic codes
(13 named + Unknown/Other). Auxiliary fields: incumbency, prior office, party, primary/general
outcomes, FEC candidate ID (manual linkage), BioGuideID for incumbents. Validation: missingness
quantified against the 6,016 denominator (no website 11.9%, no platform 25.08%, no bio 14.99%)
with logistic models showing missingness concentrates in non-serious campaigns (incumbent
coefficient -2.967*, logged fundraising -0.222*, N=6,016); topic labels double-coded on a random
20% (8,584 of 43,465): 80% agreement, Cohen's kappa 0.84, weighted kappa 0.74; cross-cycle
candidate linkage via embedding-based probabilistic record linkage (Ornstein 2025) with hand
review of sub-50% matches (16 bad links removed across three cycle-pairs). CC0 1.0 on Harvard
Dataverse (doi 10.7910/DVN/JIEAPT) + campaignview.org. Limits that bind us: House only, no
Senate; topic labels carry NO stance direction; snapshot one week before each primary; ends 2022.

### C. Cao et al. 2025 (Information Fusion 120:103107) -- SNGDM survey and taxonomy
Survey of the field paper A lives in: 917 deduplicated references (Web of Science through
2024-09-25), field founded by Wu and Chiclana 2014. Taxonomy: trust modeling (representation /
propagation operators incl. chain-length decay / evolution), internal structure (consensus
measurement, power structure, community detection incl. overlapping communities and the
"pseudoconsensus" warning -- high within-subgroup consensus masking cross-subgroup failure),
consensus mechanisms (feedback incl. minimum-cost designs, opinion dynamics on DeGroot /
Hegselmann-Krause lines, behavior management incl. manipulation and a non-cooperative taxonomy
naming "bribery behavior, passive participation behavior, and potential conflict behavior").
The survey's own verdict on the field's evidence base is the load-bearing fact: "Existing SNGDM
research mainly constructs social networks through questionnaires or directly pre-sets social
networks," and its future-work call is empirical studies "with real data." It catalogues no
datasets, no software, no benchmarks ("No data was used for the research described in the
article."). Also flags RL-based feedback and LLM/multimodal integration as open directions, and
notes no unified evaluation standards exist for those integrations.

### D. Dai et al. 2025 (Neural Networks 183:106956) -- FOLAR: LLM-elicited first-order logic + logic tensor network for stance detection
Method paper. Three components: (1) Knowledge Elicitation -- chain-of-thought prompting that has
an LLM emit first-order-logic rules as the prediction rationale for each (text, target) pair;
(2) a Logic Tensor Network grounding those FOL rules in differentiable soft-logic (product real
logic: AND = product, OR = inclusion-exclusion, NOT = 1-u) over shared BERT embeddings, trained
on labeled data; (3) Multi-Decision Fusion -- one LTN per elicitation LLM (GPT-3.5, Llama-2-70b,
Claude-2), attention-routed fusion to cancel single-model elicitation bias. Political-target
benchmarks throughout: SemEval-2016 (Hillary Clinton, Donald Trump, Feminist Movement,
Legalization of Abortion), ISD (Trump/Biden tweets), VAST (zero-shot topics). Headline numbers
(F_avg = mean of favor/against F1, 3-run mean; * = p<0.05, test unspecified): in-target HC 84.5*
(vs Ts-CoT 83.2); zero-shot VAST-all 81.0* at 100% train and 80.2* at 10% train (best competitor
74.4 / 74.0). The training-free variant FOL-CoT (one-shot FOL-formatted reasoning, no
backprop) alone beats plain CoT on most zero-shot cells. As-printed anomalies we verified and
therefore treat as reliability caveats: the ablation "w/o MDF" 85.5 exceeds full FOLAR 84.5 on
in-target HC; one baseline row (TPDG LA 74.7) exceeds FOLAR's 72.7; FOL-CoT's VAST 100% and 10%
triples print identically. No code URL ("will be made publicly available"); benchmarks are old
public sets with uncontrolled LLM-pretraining contamination risk; per-instance inference needs
three commercial LLM calls in the full architecture.

### E. Delano, Rudkin and Kim 2025 (Scientific Data 12:1567) -- BICAM
Data descriptor (MIT group; Kim is the LobbyView PI). Bulk, cleaned, linked CSVs of congressional
actions and materials from dual ground-truth APIs (Congress.gov + GovInfo): 421,764 bills
(6th-119th Congress; the Methods section separately says "all 408,000 bills" -- an unreconciled
internal inconsistency we treat as a caveat), 123,061 amendments (97th-119th), 74,918 hearings
WITH a transcripts sub-component (79th-119th), 106,818 committee reports with texts (16th-119th),
12,238 committee meetings incl. witnesses and witness documents (114th-119th, witness docs
PDF-only), 43,858 nominations, 2,597 members with bioguide_id AND ICPSR crosswalk, committees
keyed by THOMAS codes. External linkages: bills -> Voteview, and bills -> LDA lobbying reports
via Section 16 extraction with distance-measure confidence (claimed to detect "significantly more
cases of bill lobbying than existing sources" -- quantification lives in the supplement, not the
main text). Validation is procedural (download completeness, type enforcement, identifier
uniqueness, referential integrity, dual-source synthesis with documented error rules); NO
quantitative completeness percentages in the main text. Excludes: Congressional Record floor
speeches, press releases, FEC data, roll-call votes (Voteview linkage instead). MIT license, no
restrictions: bicam.net + Harvard Dataverse doi 10.7910/DVN/TALQZL; code at github.com/bicam-data.

## 3. Mapping -- where each paper earns a place here

| Paper | Strongest hooks into melange | Frontier tie | Risk class |
|---|---|---|---|
| E BICAM | corpus expansion (hearings/reports), independent coverage cross-check vs legfix5 + the 644-act universe, witness/appearance layer, bill-LDA vs LobbyView comparison, rollover support | P-1 (corpus growth), P-2 (outcome stream), rollover campaign | LOW (additive data; license clean) |
| B CampaignView | Ornstein embedding record-linkage METHOD for the mentat resolver; incumbent platform/bio text as analysis asset; challenger-context for electoral-incentive validation | P-1 (future basis, gated), receptivity validation | LOW-MED (House-only, ends 2022, no stance labels) |
| D FOLAR | valence-hop fallback candidate (FOL-structured Haiku prompting); soft-logic consistency for any future trained valence model; fresh-gold evaluation pattern | P-4 directly | MED (model change; strict gates) |
| A three-way consensus | three-way triage formalization (commit/actionable/defer + urgency dial); minimum-cost-to-threshold DUAL objective as diagnostic | P-3 adjacent (diagnostics) | LOW as diagnostics; HIGH if allowed near engines |
| C SNGDM survey | vocabulary + external confirmation that melange's empirical grounding is the differentiator; pseudoconsensus (coalition-quality) framing; manipulation/non-cooperative taxonomies as future analytic labels | P-3 framing | LOW (no mechanism adopted as-is) |

The through-line: melange already holds the asset this literature says it lacks. The SNGDM field
(A, C) optimizes consensus on questionnaire or pre-set networks with no behavioral criterion;
melange runs observed-behavior networks with prereg discipline and a live campaign to score
against. So we import FORMALISMS and DATA from these papers, never validation-free mechanisms:
A/C contribute vocabulary and two diagnostic shapes; B/E contribute real, licensed datasets and
one linkage method; D contributes a concrete attack on our measured bottleneck. Nothing in the
five papers justifies touching the IC/LT kernel, the two partisan physics, the receptivity
multipliers, or any ratified constant.
## 4. Proposals -- gated candidates, in recommended order

Every proposal: additive, behind its own artifact/dial, promoted only by Paul. None is started
without his go-ahead. "Gate" names the class from moneyball-change-control vocabulary.

### P1. BICAM arrival audit + reconciliation (recommended first move)
WHAT: acquire the BICAM CSV components we care about (Bills, Bills-Texts, Bills-Sponsored,
Hearings, Committee Reports, Committees, Members), sha256-pin the download snapshot, then run a
PRE-REGISTERED reconciliation against what we already hold: (a) member roster -- 533 bioguides
must join Members; (b) the 644-act universe (bill_beneficiary_tags.ndjson) joined on bill_id;
(c) the legfix5 full-text store (18,557/18,557 at the 2026-07-27 record) vs Bills-Texts version
counts for the same bills; (d) cosponsor counts on a sampled act set vs our network source.
Declare expected join rates BEFORE running (draft bars in section 5.2). WHY: independent
cross-validation of our own collection is cheap assurance we cannot get internally -- and
BICAM's own 408,000-vs-421,764 inconsistency shows arrival data gets audited, not trusted.
VALUE: high (assurance + the foundation every other E-proposal stands on). COST: ~GBs of CSV,
one collector-style script, zero engine surface. GATE: acquisition+audit is a data-lane ADD
(Paul approves the download); no rank surface touched. REVERT: delete the snapshot dir.
KILL: join rates far below bars with causes traced to BICAM quality -> record and stop.

### P2. Hearing-transcript + committee-report corpus expansion (from BICAM)
WHAT: backfill non-finance hearing transcripts (our CHRG collection is finance-only by the
2026-07-10 corpus record) and committee-report texts for the current roster's committees, as a
NEW corpus channel with per-member attribution where the source supports it. WHY: grows the
behavioral text base feeding stance channels and the psychometrics program (corpus growth is
one of the two things that opens frontier P-1's gates; hearing text specifically feeds the
hearing-antagonism A/ES lever recorded 2026-07-10). CAVEATS: transcript coverage within the
74,918 is unquantified in the paper -- P1's audit measures it first; speaker attribution inside
transcripts is our work, not BICAM's. VALUE: high, compounding. COST: storage + an ingest script
+ attribution pass. GATE: collector ADD (user-gated); no engine change. REVERT: channel dir.
KILL: transcript coverage or attribution quality below pre-declared floors.

### P3. Valence-hop candidate from FOLAR's elicitation idea (the science jewel)
WHAT: attack the measured bottleneck -- valence-hop 0.689 vs compose ceiling 0.872 -- with a
Haiku-only, FOL-CoT-style STRUCTURED elicitation classifier used strictly as registry-FALLBACK
(the tracked cu_valence_registry.json and Paul's policy_force entries always bind; the model
only scores targets the registry does not cover). Adaptation, honestly stated: FOLAR's full
architecture (three commercial LLMs + BERT LTN + fusion) is out of scope under the cost rule;
what we adopt is (i) FOL-formatted reasoning elicitation, which in the paper's own ablation
lifts LLM-only prediction WITHOUT training (their FOL-CoT variant), and (ii) if a trained
fallback is ever ratified, soft-logic encoding of registry rules as consistency constraints.
PROTOCOL: frontier P-4 discipline verbatim -- Paul curates families first (the free --uncovered
probe), fresh gold batch he adjudicates AFTER the method is frozen, prereg locked with numeric
bars (draft in 5.2), stance_eval macro-F1 harness, .candidate artifact consumed by nothing.
VALUE: the only proposal that can move a measured ceiling. COST: prompt engineering + one
prereg + Paul's gold labels. GATE: prereg + one look; promotion user-gated. REVERT: candidate
file deleted; registry untouched by construction. KILL: MISS at the locked bars -> route
closed with evidence, kill-ledger entry.

### P4. Ornstein-style embedding record linkage for the mentat resolver (method transfer)
WHAT: replace/augment the exact-name trade-association resolver in the mentat R pipeline (the
recorded $0-rows fault class of 2026-07-27) with the embedding-based probabilistic record
linkage CampaignView validated operationally (pre-trained embeddings + blocking + hand review
of sub-threshold matches; their observed error: 16 bad links across three cycle-pairs, each
traced to an FEC-ID district change). WHY: a measured fault class in OUR pipeline with a
published, operationally-proven fix shape. VALUE: medium-high (kills silent zeros). COST: small
(R or Python side-script + review queue for Paul). GATE: mentat change (user-gated; touches
money workbooks only after review). REVERT: keep exact-name path behind a flag.
KILL: precision on a hand-checked sample below bar.

### P5. Witness/appearance layer from BICAM committee meetings
WHAT: structured witness lists (114th-119th) -> an interest-group appearance table (who
testified, which committee, which bills) keyed to our association anchors (ABA/ICBA/Blockchain
Assn/AFC etc.) and committees. WHY: extends the association-anchor campaign with an observed-
behavior channel; potential future edge layer (industry presence x committee) for the network
plane -- data first, any edge use is its own later proposal. VALUE: medium. COST: one ingest +
entity-resolution pass (P4's linker reused). GATE: data ADD. KILL: witness field coverage too
thin (114th+ only -- narrow window is a known cap, state it on every figure).

### P6. Three-way targeting triage diagnostic (from A)
WHAT: a read-only diagnostic (kb_benchmark pattern: guarded __main__, one tagged JSON, chain
consumes nothing) that partitions, per category, the 533 into committed / actionable / defer
using EXISTING signals only (tier, pflip, money-response headroom, network proximity), with A's
lambda dial as an explicit speed-vs-completeness parameter. NO new physics, no UAC invention,
no trust updates. WHY: formalizes the triage the engines already imply; gives Paul a one-page
actionability cut that is pure data (audience-law compatible if it ever ships, which is his
call). VALUE: medium (analytic clarity). COST: small. GATE: diagnostic ADD; any surface use
user-gated. KILL: if the partition is unstable under MC seeds (stability check pre-declared).

### P7. Minimum-cost-to-consensus dual diagnostic (from A)
WHAT: the dual question to optimize.py -- instead of "given $2.5M, maximize weighted flips,"
compute "minimum spend (and recruit set) to reach pre-set coalition/consensus thresholds on
category X," reusing money_response + flip physics unchanged, outputs redirected (FRONTIER_OUT
idiom), never touching production artifacts. WHY: lobbyist-natural framing ("what does winning
Interchange cost?") and a consistency probe on the allocator from a second direction. Guarantee
honesty: competitive-LT caveat inherits -- no (1-1/e) claim on the flip side, marginals checked
empirically like audit_frontier does. VALUE: medium. COST: small-medium. GATE: diagnostic ADD.
KILL: dual answers inconsistent with frontier curves beyond tolerance -> investigate as a
finding, not a feature.

### P8. CampaignView acquisition as an analysis asset
WHAT: pull the CC0 datasets (platforms + biographies), link incumbent rows to our roster via
BioGuideID, hold as source_data with provenance. Two SCOPED uses now: (a) challenger-context
history for validating the competitiveness inputs behind incent_mult (retrospective only -- the
data END at 2022; useless for live 2026 races, state so); (b) incumbent self-presentation text
as a FUTURE instrument-basis candidate -- explicitly NOT exercised without a round-6-compliant
prereg (anti-basis-shopping clause binds: own diagnostic, fresh-seed confirmation, screening
ledger, adversarial prereg). VALUE: medium now, option value later. COST: trivial (CSV).
GATE: data ADD now; ANY instrument use is prereg-gated later. KILL: n/a for acquisition.

### P9. BICAM bill-LDA linkage vs LobbyView comparison (descriptive)
WHAT: compare BICAM's bill->LDA-report linkage against our LobbyView holdings on the finance
bill universe: coverage counts, agreement, disagreement samples adjudicated. HARD BOUNDARY: the
FECxLDA R3 ruling stands -- structure explains the correlation, predictor-language BARRED; this
comparison is repository hygiene and coverage, never a predictive feature. VALUE: low-medium
(better lobbying repository). COST: small. GATE: data-lane analysis. KILL: if supplement-level
linkage quality (unquantified in main text) proves weak on our slice.

NOT RANKED AS PROPOSALS: C's survey vocabulary (adopted free in this doc's framing); C's
RL-feedback direction (BARRED -- Paul's roadmap); A's KNN preference imputation and monotone
trust updates (REFUSED, section 6).

## 5. Validation framework

### 5.1 Class contracts (which machinery applies to which proposal)

| Class | Proposals | Required machinery, in order |
|---|---|---|
| DATA-INTEGRATION | P1, P2, P5, P8, P9 | license verified -> snapshot sha256-pinned + row counts recorded -> PRE-DECLARED reconciliation/coverage bars -> arrival audit vs bars -> honest-gap ledger for every miss (window + denominator) -> artifacts land in source_data/new channel dirs consumed by NOTHING -> any engine/surface consumption is a separate user-gated proposal with its own dial |
| MODEL-CHANGE | P3, P4 | free probes (criterion-side only) -> Paul's domain inputs first (registry families, gold queues) -> prereg locked per moneyball-research-methodology (hypothesis, numeric bars, fingerprints, battery, consequences, stopping rules) -> simulate battery must pass or RETIRED WITHOUT A LOOK -> ONE look on fresh gold -> verbatim RESULT committed same session -> PASS still ships only as .candidate; promotion is Paul's, behind a revert dial |
| DIAGNOSTIC | P6, P7 | read-only script, guarded __main__, redirected outputs -> zero-rank-delta proof (ranks_python.json byte-identical before/after) -> pre-declared interpretation rules -> results into a dated audits/ record -> surface exposure only by Paul |

Cross-cutting, all classes: glassbox emission around every job (law 4); JS mirror untouched
until a ratified engine change requires a matching template edit; nothing runs in a worktree
against live data assumptions (verify in the live tree); every claim written down carries
window + denominator (D-007); citations honest-analogical.

### 5.2 Draft numeric bars (DRAFT ONLY -- these lock inside per-proposal preregs, not here)

- P1 reconciliation: roster join 533/533 bioguides expected (any miss enumerated by name);
  644-act bill_id join >= 640/644 expected with every miss adjudicated; legfix5-vs-Bills-Texts
  presence agreement >= 95% on the 18,557 store with disagreements sampled n>=50 and classified
  (their gap / our gap / id mismatch); cosponsor-count agreement within +/-2% on a pinned
  100-act sample. Deviations below bars are FINDINGS to trace, never auto-corrections.
- P2 coverage floors: transcript presence measured on the hearings of the 533's committees for
  the 117th-119th BEFORE ingestion is approved; floor proposed at >= 70% presence for the ingest
  to proceed as a channel (below that it is a partial-channel with per-figure caveats).
- P3 stance bars (to lock at prereg time): on a FRESH Paul-adjudicated gold batch (n >= 150,
  collected after method freeze): valence-hop accuracy >= 0.75 (vs 0.689 baseline, same-batch
  denominator) AND composed CU-alignment macro-F1 >= the recomputed compose baseline on that
  batch AND no registry-covered item overridden (hard zero). Claiming a ceiling-beat requires
  composed accuracy > 0.872-equivalent on the fresh batch. Battery: label-permutation null must
  score at chance; a registry-leakage check (model must not merely memorize registry families);
  a target-swap confound check. FRAGILE = MISS on re-derivation, per standing law.
- P4 linkage bars: on a hand-checked stratified sample (n=200 resolver decisions): precision
  >= 0.95 for auto-accepted links; every sub-threshold link human-reviewed (CampaignView's own
  operating point); recall improvement over exact-name reported with denominators, no bar
  (recall is the point; precision is the guard).
- P6 stability: partition agreement >= 90% of members unchanged across SEED in {7,1,13} at
  MC=20 vs MC=100 (CRN held), else the diagnostic is reported as unstable and shelved.
- P7 consistency: dual-vs-frontier agreement -- the minimum-cost answer at threshold T must be
  within one INC ($500) grid step of the frontier's inverse read at T on >= 90% of a pinned
  topic x threshold grid; disagreements enumerated.

### 5.3 Standing refusals and kill-switches (bind all of the above)

Never: impute '-' stance cells (the gap IS the datum); adopt monotone trust updates or any
trust-evolution rule without behavioral evidence; move stance/press labels by model judgment;
mention-density relevance anywhere (DE-001); RL feedback loops (Paul's envelope); weaken any
existing test/floor/pin to admit new data (change-control law 7); let any new artifact be
consumed by engines without its own ratified promotion. Every proposal above dies quietly and
completely via its KILL line -- a killed candidate leaves a dated record and no residue in the
data plane.

## 6. Considered and refused (so the next session does not re-derive them)

1. A's KNN imputation of missing preferences -> REFUSED for stance cells. Our '-' is a designed
   ontology (no recorded position, priced Ally-parity, user-ratified), not missingness to fill.
   Peer-inference of movability already exists honestly as pflip's network term. Would reopen
   only if Paul redefines the '-' ontology (no current reason to).
2. A's trust-update t^(1-t) (monotone increase) -> REFUSED. No behavioral basis; would bake
   convergence into the network by construction. Would reopen with measured longitudinal edge
   data showing that dynamic.
3. C's RL-based feedback mechanisms -> BARRED (standing rule: the RL envelope is Paul's roadmap).
4. D's full FOLAR architecture (3 commercial LLMs + BERT LTN + fusion per item) -> REFUSED on
   the cost rule and dependency surface; only the elicitation pattern and (conditionally) the
   soft-logic consistency idea transfer (P3).
5. Densifying the multiplex network with trust-propagation operators (C's operator families) ->
   REFUSED for now. Our edges are observed; propagated edges are model-imputed influence. The
   D4-era decision deliberately restricted similarity edges to cosponsor-isolated members.
   Would reopen only as a frontier P-3 ablation benchmark question (does a propagation-densified
   kernel predict real adoption better?) under its own prereg.
6. CampaignView as an immediate psychometric instrument basis -> DEFERRED by the round-6
   anti-basis-shopping clause; acquisition (P8) deliberately separates data from any look.

## 7. Relation to the research frontier (so the pages stay consistent)

P3 executes frontier problem 4's step 3 (focused valence model as registry-fallback). P1/P2 feed
problem 1's corpus growth passively (they do NOT move MEM_N, which is live-interview coverage).
P6/P7 are problem-3-adjacent diagnostics, not the ablation benchmark itself (that remains open).
BICAM's actions data is a candidate ENRICHMENT for problem 2's outcome stream -- but the armed
snapshot (outcome_snapshot_2026-07-04.json) is scored EXACTLY as frozen; any action-based
outcome criterion is a NEW freeze with its own prereg, never an edit to the armed one.

## 8. Draft brain updates (to commit under D-006)

STATE.md, Active workstream, ADD:
"- Research-integration lane (2026-08-14): five uploaded papers (SNGDM consensus x2, CampaignView,
  FOLAR stance, BICAM) examined; guiding doc + validation framework at
  audits/RESEARCH_INTEGRATION_2026-08-14.md on branch claude/melange-research-integration-062ce9
  (committed, unmerged). Nine gated proposals P1-P9 await Paul's ruling; recommended first moves
  P1 (BICAM arrival audit), P4 (embedding record-linkage for the mentat resolver), P3 (valence-hop
  prereg). Nothing applied; no engine, artifact, or surface touched."

DECISIONS.md: no entry -- no decision has been made. A skeleton is left for Paul in section 4;
if he ratifies any subset, that ruling (not this document) becomes the D-entry.

-- end of record --