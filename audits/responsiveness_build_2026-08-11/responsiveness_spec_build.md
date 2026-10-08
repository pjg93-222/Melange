# Responsiveness surface — build spec (Paul-ratified 2026-08-11)

RATIFIED DECISIONS: CU-only pilot; desk panel + tier-board chips; capacity
residual dual-spec with LINEAR headline; DISPLAY-ONLY indefinitely (ACU
internal rankings not shareable — no criterion-validity claims, no scoring
use, prereg gates any future promotion).

PROVENANCE: audits/BARR_CU_COURTSHIP_BATTERY_2026-08-11.md (E1+E2),
audits/barr_courtship_2026-08-11/e2_flagship_takeup.json. The E2
computations are the acceptance oracle for producer numbers.

## Artifact 1 — ask registry
Path: data/lobbying/industry_ask_registry.ndjson
Content: EXACTLY the 27 rows in responsiveness_spec_registry.ndjson
(this directory) — materialize verbatim, byte-for-byte, LF endings.
Governance mirrors industry_valence_adjudication.ndjson: fable-signed,
row-level Paul override via status, loader guards.

## Artifact 2 — producer
Path: fec/engine/responsiveness_layers.py (house style: encoding
boilerplate, atomic write, logging contract, paths.py resolution).
Inputs (read-only): member_desk_bundle.json (root; members[].bills =
authoritative memberships, members[].party/chamber), bill_beneficiary_tags.ndjson
(root; vehicle keys must exist here — guard), data/lobbying/industry_ask_registry.ndjson,
data/engine/primacy_factors.json (members.*.mix.cu_primary + agenda_credit),
data/members/member_desk_src.json (committee.on/mem/lead for finance flags),
data/network/cosponsor_selectivity.json (service map — see below).
Output: data/engine/responsiveness_layers.json.

Registry loader guards (hard errors): vehicle+congress not in tags
universe; industry not in {credit_union} for this pilot; duplicate
(vehicle, congress, industry); status not in {active, unscored,
inactive}; scope keys outside {chamber, party, committee}; chamber not
in {House, Senate}; party not in {Republican, Democrat}.

Eligibility semantics (per member m, vehicle v):
- status != active  -> NOT counted anywhere except unscored_count
  (status=inactive rows are Paul-struck: fully ignored, not unscored).
- chamber scoped and m.chamber != scope.chamber -> ineligible.
- party scoped and m.party != scope.party -> ineligible.
- committee scoped -> ALWAYS unscored in this pilot (no rosters outside
  finance in corpus) — belt on top of the CISCOMANI row's status.
- service: m must have served congress(v). Source of truth: the service
  data inside data/network/cosponsor_selectivity.json (its definition
  states opportunities are scoped to "a Congress the member served";
  inspect its schema — 'congresses'/'service_source' keys — and reuse).
  If no per-member service map is extractable, ESCALATE (STOP REPORT)
  rather than inventing a proxy.
- answered(v) = vehicle key present in m.bills with ANY role (sponsor/
  original/cosponsor/signer; initiator's own vehicle counts answered).

Per-member output row:
  { member, chamber, party,
    take_up: { answered, eligible, rate (null if eligible==0),
               unscored, vehicles: [ {vehicle, congress, ask_type,
               scope, eligible: bool, answered: bool, role|null} ] },
    in_group: { definition: "same chamber + same party + finance-committee",
                n, mean_rate },
    capacity: { actual_cu_primary, pred_linear, resid_linear,
                pctile_linear, pred_log, resid_log, pctile_log } }
Capacity model (both specs, betas receipted): OLS of
mix.cu_primary ~ [1, fin_member, fin_lead_grade, fin_mem_grade,
agenda_term, senate] over all 533; agenda_term = agenda_credit (linear
spec) or log1p(agenda_credit) (log spec); fin_* from member_desk_src
committee.on containing 'Financial Services' or 'Banking'. Closed-form
normal equations w/ partial pivoting (reference implementation:
audits/backfire_analysis_2026-08-11/n2_models.py ols()). HEADLINE =
linear spec; log spec present in artifact for transparency.
Acceptance oracle: Barr actual 4.0, pred_linear 3.76 +/- 0.02,
pred_log 2.21 +/- 0.02, take_up answered includes LTR-117-CDFI-BARR +
H.R.6889|117, Barr post-117 active-eligible answered = 0.

Receipts block: registry_sha256, registry_rows=27, active_rows,
unscored_rows, betas both specs, service_source, in_group_definition,
display_only: true. NO wall-clock timestamp (determinism: rerun must be
byte-identical).

## Surface 1 — desk panel
make_member_desk.py: optional-ingest (missing artifact = no panel, no
error). Member card panel "Responsiveness (CU) — display-only":
headline "Asks answered X/Y · in-group mean Z" + "Capacity-adjusted CU
delivery: Pth pctile (linear; log in receipt)" + per-vehicle table
(vehicle, congress, scope tag, answered/na) + disclosure line "This
layer is display-only: no desk score, board tier, or rank uses it."

## Surface 2 — MLN chips
make_lobby_network_html.py: optional-ingest responsiveness for the CU
board ONLY (mirror the RHETORIC pattern: loader + attach + note
disclosure). Chip per seated row: "asks X/Y". Note line addition:
"Responsiveness chips are display-only: boards price acts held, not
asks answered — evidence on the member desk." Fixture updated; the
required_receipt whitelist gains the new key (the scope/rhetoric
whitelist-omission lesson, third time pays for all).

## Chain wiring
run_pipeline CHAIN: responsiveness_layers.py inserted AFTER whatever
produces/refreshes member_desk_bundle.json + primacy_factors.json,
BEFORE make_member_desk.py. Codex verifies the actual producer of
member_desk_bundle.json before choosing the slot; if ambiguous,
ESCALATE, do not guess.

## Tests (fec/tests/)
1. Registry loader: each guard fires (unknown vehicle, dup, bad scope,
   bad status, bad party/chamber).
2. Eligibility negative controls: unscored excluded from denominators;
   inactive fully ignored; wrong-chamber ineligible; party-scoped
   excludes the other party; non-served congress ineligible.
3. Determinism: two runs byte-identical.
4. Capacity oracle: Barr numbers within tolerance (above).
5. MLN fixture: chips render, receipt key present, absent-file = no
   chips and unchanged note.
6. Zero-rank-delta: ranks_python 0/533 after full chain; four boards
   byte-identical except declared chip/note keys.

## Invariants (pinned in ledger, run responsiveness-surface)
Display-only; 0/533; registry governance; unscored-never-in-denominator;
no manufactured scope (composition-circularity disclosed on KIMCRAPO/
WATERS/SCOTT rows); prereg gates scoring; CU pilot only.

## RULINGS APPENDED DURING BUILD (run ccd0abf0e4)

1. SERVICE-MAP RULING (supersedes the cosponsor_selectivity.json wording
   above): that artifact persists no per-member service map — the lane
   escalated exactly as instructed, and Fable ruled the producer reads
   votes/HSall_members.csv DIRECTLY, mirroring cosponsor_selectivity.py's
   own bioguide/congress/chamber derivation. receipts.service_source
   records this. Any future reviewer reading only this spec: the CSV
   route is the ruled design, not a deviation.
2. Adversarial round 1 (producer): congress-time chamber eligibility
   (switcher fix, proven on Blunt Rochester), service_unmatched
   disclosure (41 members, Voteview freshman lag), capacity_n +
   percentile_definition receipts, in_group n = measurable-rate
   denominator, non-saturated OLS + midrank + switcher tests.
3. Adversarial round 2 (surfaces): desk fail-loud nested validation,
   escaped counts, zero-eligible consistency guard, chain-order test
   extended to MLN precedence. Static-JS byte finding adjudicated
   no-action (rhetoric-branch precedent; byte-identity binds data
   artifacts + board rows, measured at the chain gate).
4. Executor receipt-omission on revision rounds recurred 3x (each caught
   at gate, receipts then produced faithfully) - logged as an upstream
   skill-amendment candidate: revision-round RECEIPT as its own first
   exchange.

## N6 GROK ADJUDICATION (registry semantics critique, run ccd0abf0e4)

Grok (grok-4.5, single-file embed) returned 6 KILLED / 8 WOUNDED / 5
SURVIVES / 0 BLOCKED against the shipped 27-row registry + eligibility
semantics. Verbatim dispatch preserved in critique_n6_dispatch.txt (this
directory); the full critique text is in the session transcript and its
operative content is captured by the adjudication below.

ACCEPTED (applied @c828aa107):
- K1 circularity: disclosure is not cure. The three party-scoped letters
  (SCOTT/KIMCRAPO/WATERS) restated to EX-ANTE document-type scoping
  (minority-caucus letter / R-led circulation / majority-D opposition
  letter); observed composition demoted to corroboration; basis ->
  document-type-ex-ante.
- K4 Blunt Rochester: the "Senate signer anomaly" is a chamber-migration
  display artifact (a 117 House signer now serving in the Senate) that
  the congress-time chamber semantics already resolve; evidence now says
  exactly that. House scope is the 117 truth.
- K3 non-comparability: chip note + desk disclosure now carry "Denominators
  are member-specific (chamber, party, and service scoped); rates are not
  comparable across members."
- CUTAX unscored honesty, chamber-only bill scopes, unscored-exclusion
  failure mode, letter-initiator credit: SURVIVED per Grok.

REJECTED with reasons:
- K5 (drop H.R.4867 as non-informative): removing zero-take-up asks
  selects on the outcome — survivorship circularity worse than the
  disease; the in-group context (0/30 renders absence normal) is the
  designed cure.
- K6 (bill initiators uncreditable): the reviewer lacked producer
  visibility (its own BLOCKED note) — bill sponsors are credited through
  the membership ledger role='sponsor'; the letter initiator field is
  belt, not the only path.

PAUL-GATED V2 QUEUE (raised by Grok, real design questions, no silent
changes): (1) FAMILY-COLLAPSE of reintroduction clones (Board
Modernization x6, VetMBL x5, CLF x6 as ask FAMILIES instead of per-
congress vehicles); (2) dual S.2545/S.3575 CLF vehicles merge-or-prove;
(3) chip label wording ("asks" vs "catalogued asks"); (4) registry
completeness statement (catalogued flagship + letters, not the ask
universe); (5) multi-lane adjudication of future registry rows.

Registry sha re-pin after amendments:
4f25098ecd96131602ad205a192c598db14b0e63f8bf522ba380ee47b98aa64c
