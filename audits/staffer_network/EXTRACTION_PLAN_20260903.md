# Staffer network — collect, parse, construct

Plan of record, 2026-09-03. Three phases: **collect** every missing source, **parse** it
correctly, **construct** the network. Written so a future session executes without
re-deriving anything.

Nothing here promotes anything to canonical. Every artifact carries
`review_status: "REVIEW_REQUIRED"` and `canonical_employment_promoted: false`, promotion
counters pinned at 0. **No git**, ever, by anyone — including read-only inspection.

Companions: `STAFFER_NETWORK_EXPANSION_DESIGN_20260829.md` (§ refs are to it) and
`STAFFER_NETWORK_METRICS_20260829.md` (C-bars, I-bars).

---

## 0. Architecture — the ant colony

Paul's rulings, 2026-09-03:

- **Members are stations.** The congress member layer (cosponsorship + press/media) stays
  **independent and untouched**. KEPT. Cosponsor and media references are central to the model.
- **The staffer network is its own social network, a layer BELOW members.** Not a
  member-member projection. Members are attachment points for staffer nodes, not nodes here.
  No member↔member edges are computed in this layer.
- **Lobbyists are outsiders entering the colony** via revolving-door edges.
- Layers combine at **analysis** time in the multiplex — never inside each other's weights.
  Do **not** multiply the cosponsorship adjacency `Â` into staffer weights (§6.4's `w_x`):
  cosponsorship is already its own layer, so importing it double-counts and contaminates the
  D-Q7 comparability bar by making the graphs correlate by construction. Same failure class as
  the LD-2 circularity.
- **Education is out** ("nice cherry on top"). Keep `w_edu` in code at α=0 rather than
  deleting, so it slots back if Politico profiles are ever crawled. With education and `w_x`
  both out, §6.9 collapses to **`W = ŵ_work`** — purely staffer-derived, and therefore
  legitimately *comparable* to the bill graph instead of contaminated by it.

### THE EDGE RULE — OVERLAP

A person-to-person edge requires **actual temporal overlap in the same container**. Two people
in an office at the same time knew each other; that is the edge, weighted by overlap duration
× container κ. If A left in 2015 and B arrived in 2018 they never met — **no edge**. Not a
weak tie; not a tie.

**Sequence is a property of a person's trajectory, not a person-person edge.** Person p served
office A then office B: real data, kept, emitted as ordered stints plus derived directed
office→office moves. It is the institutional tunnel between stations, never a claim that two
strangers know each other.

Measured 2026-09-03: **29,237,612** same-container candidate pairs exist with multiplicity;
**11,817,537** survive with guaranteed overlap on the spine, plus 3,330,352 possible-only
carrying zero weight. House ledger alone: **3,553,487** guaranteed pairs over 77,635 people,
median degree 35. Every build must emit a negative control stating how many edges a build that
skipped the overlap test *would* have emitted — if that number equals the real count, the test
is not firing.

---

# PHASE 1 — COLLECT

## 1.1 Already on disk but never parsed — the largest miss

Paul, 2026-09-03: *"The filings we obtained have committee payrolls, 2009, the committee on
agriculture is page 2791, and goes down, you missed a lot of shit."*

A prior lane concluded "committee membership does not exist on disk." That was wrong — it
scanned for committee *roster files* and missed that the payroll data sits inside House SOD
volumes **already ingested**. This is a parse miss, not a missing source.

### Document anatomy (from the volume's own table of contents)

The volume runs: leadership (pp. 3–41) → officers and employees (pp. 47–221) → member offices
(the bulk) → other administration (2772) → committees (2774–2912) → revolving funds and
allowances (2915+) → **index (3345)**.

**Working hypothesis to confirm or refute:** the parser locks onto the member-office range and
walks past the front matter *and* the back matter. That would explain both the committee miss
and Paul's earlier observation that people appear "after the initial round" with positions
beside them.

**Family 1 — House Leadership Offices, pp. 3–41 (17 offices):**
The Speaker 3 · Majority Floor Leader 10 · Minority Floor Leader 16 · Majority Whip 22 ·
Minority Whip 25 · Chief Deputy Minority Whip 29 · Republican Conference 33 · Republican Policy
Committee 37 · Republican Steering Committee 39 · Democratic Caucus 30 · Democratic Steering
and Policy Committee 29 · DS-Training & Program Development 40 · RC-Training & Program
Development 40 · Cloakroom Personnel Majority 40 · Cloakroom Personnel Minority 41 ·
Legislative Floor Activities 39 · Minority employees 39

**These carry SIDE IN THE OFFICE NAME** — Cloakroom Majority vs Minority, Majority vs Minority
Whip, "Minority employees". First real `maj`/`min` source in a corpus where side measured 0%.

**Family 2 — Salaries, Officers and Employees, pp. 47–221 (14 offices):**
Chief Administrative Officer 47 · Clerk 140 · General Counsel 184 · Sergeant at Arms 186 ·
Chaplain 194 · Parliamentarian 194 · Compilation of Precedents 195 · Technical Assistants 196 ·
Inspector General 198 · Historian 201 · Law Revision Counsel 205 · Legislative Counsel 208 ·
Interparliamentary Affairs 212 · OEPPO 221

**Family 3 — Committee Employees and Special and Select Committees, pp. 2774–2912 (23):**
Appropriations 2774 · Budget 2788 · **Agriculture 2791** · Armed Services 2796 · Financial
Services 2801 · Education and Labor 2807 · Energy and Commerce 2814 · Oversight and Government
Reform 2823 · House Administration 2837 · Natural Resources 2843 · Foreign Affairs 2849 ·
Judiciary 2855 · Transportation and Infrastructure 2867 · Rules 2873 · Science and Technology
2877 · Small Business 2882 · Standards of Official Conduct 2886 · Veterans' Affairs 2888 · Ways
and Means 2892 · Select Committee on Intelligence (Permanent) 2898 · Homeland Security 2904 ·
Energy Independence and Global Warming 2912 · **Joint Committee on Taxation 3063**

Joint Taxation sits *outside* the 2774–2912 block — do not assume one contiguous range.

**Total: 54 non-member offices.**

**Also check for person rows before dismissing:** Other Administration – Official Expenses of
Members 2772 · Members' Representational Allowance 3329 · revolving funds (House Recording
Studio 3052, House Services 3051, Page 3069, Stationery 2915). Some revolving funds employ
people.

### The completeness oracle — page 3345

**"Index of House Officers and Employees."** A name index with page references. Extract it and
use it as an independent completeness check: every indexed name should resolve to an extracted
person. This gives a real external denominator for the volume — exactly what the metrics doc
demands ("N of D listed by <source> on <date>") and what this lane has never had.

### Robustness requirement

**Do not hardcode page numbers.** They differ across quarters and years. **Parse the table of
contents itself, per document**, to locate sections. Report whether the TOC is machine-parseable
in every document or only some.

## 1.2 Politico Pro directory (authenticated, attended)

**Access law (§3.1, non-negotiable):** Paul logs in himself; the session drives the
already-authenticated tab. No credential transits the session. Never unattended, never
credentialed-by-Claude, never rate-abusive. Honor delay floors; never bypass a challenge.

| Route | URL | Yields |
|---|---|---|
| Committee roster | `https://directory.politicopro.com/committees` | The list of all committees |
| Committee-employed staff | `…/congress/search?Type=staffer&Committee=<C>&StaffersType=COMMITTEE_EMPLOYER&profileName=Staff+for+<C>` | Staff employed **by the committee** |
| Member + committee universe | `…/congress/search?Type=staffer&StaffersType=MEMBER_COMMITTEES` | The 18,618-result universe (2026-08-29) |
| Federal agency people | `https://directory.politicopro.com/agency?Type=federal-agency-person` | Executive-branch people — never on Hill payroll |
| Individual profile | `…/congress/staffer/{uuid}` | **Employment History**: org + `(Mon YYYY – Mon YYYY \| Present)` + title, multi-stint, **including stints under other members**; education; bio; issue areas |

Grammar, from Paul:

```
https://directory.politicopro.com/congress/search
  ?Type=staffer
  &Committee=Commission+on+Security+and+Cooperation+in+Europe
  &StaffersType=COMMITTEE_EMPLOYER
  &profileName=Staff+for+Commission+on+Security+and+Cooperation+in+Europe
  &CaucusType=MEMBER_CAUCUSES
```

`COMMITTEE_EMPLOYER` ≠ `MEMBER_COMMITTEES` — different populations; crawl and label separately.
Conflating them corrupts the container-kind assignment κ depends on.

**Held vs needed.** On disk is the directory **listing** only:
`…\AppData\Local\Melange\staffer_network\raw\politico\crawl-20260829T221300-0400\directory_rows.ndjson`
— fields `name`, `roles`, `partition`, `partition_ordinal`, `issue_areas`, `profile_uuid`. That
is the card: one current role each, entirely undated. The **profiles** behind those UUIDs are
un-fetched, and they are the only source reaching departed staffers' stints and service
**before 2009**, which payroll cannot.

Ask the account rep about an export or API first (D-Q1) — an export replaces the whole crawl.

## 1.3 House SOD — the dated backbone

- Archive: `https://www.house.gov/the-house-explained/open-government/statement-of-disbursements/archive`
  (earliest **2009Q3**; HTML index 403s bots, CSVs serve with a browser UA).
- Historic mirror with a free member join:
  `https://wgetsnaps.github.io/propublica-congress-expenditures/` — per-quarter CSVs
  **2009Q3–2020Q1**, header carries **`BIOGUIDE_ID`**. Pipeline CC0 at
  `https://github.com/propublica/disbursements`.
- Row fields (byte-verified): `ORGANIZATION`, `VENDOR NAME`, `DESCRIPTION` (title),
  `PERFORM START DT` / `PERFORM END DT`, `AMOUNT`.
- Ingested: `house_personnel_ledger_20260902_v3_primary` — 975,058 observations, 161,102 spans,
  67 quarters 2009Q3–2026Q1, 77,666 people, 1,023 member offices.
- `compensation_class` distribution: BASE 906,612 · OTHER COMPENSATION 58,724 · OVERTIME 9,722.
  Only **31** of 77,666 people lack a BASE row — compensation class is not a hiding place.

**Missing quarters:** 2009Q1, 2009Q2 (see 1.5), 2026Q2 (likely unpublished — verify).

## 1.4 Senate Report of the Secretary

- Semiannual GPO PDFs on govinfo, web index April 2011 → March 2026.
- **Volume I** = personal offices. **Volume II = "Expenses of Inquiries and Investigations" =
  committee payrolls** — the Senate analogue of the House committee miss. Ingested as
  `senate_committee_payroll_20260903_v2_primary`: 34,865 rows, 43 offices, 7,187 payees, 30
  periods. A `v3_primary`/`v3_twin` exist without a verification directory.
- **Inline service-date qualifiers** sit inside the title field:
  `SCHAPITL, ASHLEY OVERSIGHT-DEPUTY POLICY DIRECTOR-SPOKESPERSON TO MAY 29 AND $39,666.65`
  (`GPO-CDOC-117sdoc8` p.21). `TO MAY 29` is a **day-level** boundary in an otherwise
  period-level corpus. Survey the real variant family before writing any rule.
- **Missing periods:** 2009-04, 2009-10, 2010-04, 2010-10.

## 1.5 The 2009 backfill

Targets identified: **House Doc 26** (111th, Jan–Mar 2009, pts 1–3) · **House Doc 56** (111th,
Apr–Jun 2009, pts 1–3) · **Senate Doc 2** (111th, Oct 2008–Mar 2009) · **Senate Doc 8** (111th,
Apr–Sep 2009).

**Confirmed dead ends — do not re-probe:**
- house.gov — archive earliest period is 2009Q3; `mentions_2009q1` and `mentions_2009q2` both false.
- Direct govinfo CDOC PDF paths — `GPO-CDOC-111sdoc2` and `CDOC-111sdoc2` both return HTTP 200
  with `content_type: text/html` at 44,165 B. A page, not a PDF.

**Route under test:** govinfo **SERIALSET** collection sitemaps.
**Verification rule: HEAD probes on govinfo lie.** Confirm with a ranged GET — `content_type`
must be `application/pdf` AND the body must begin with `%PDF`.

## 1.6 LDA — the lobbying spine

- **Domain moved:** `lda.senate.gov/api` → 301 → **`https://lda.gov/api`**. Old host is stale.
- Endpoints: `/api/v1/filings/`, `/registrants/`, `/clients/`, `/lobbyists/`, `/contributions/`.
  Anonymous 15 req/min; **free key 120 req/min**.
- Sealed corpus, figures reproduce exactly: **25,340** lobbyists · 748,589 covered-position
  assertions · 1,037,547 activities · 7,077 registrants · 46,996 clients · 4,816,559
  source-native industry edges. Queue partition P0 6,527 / P1 2,957 / P2 15,856.
- **LDA is NOT a dated employment source.** Only 2,166 covered-position texts carry a
  four-digit year token, 597 a month token. **`dt_posted` is never an employment date** — an
  armed gate asserts zero such uses.

## 1.7 Supplementary

- **LittleSis** — `relationships.json.gz` on disk (1,880,491 records: Position 368,995,
  Education 44,673). Fetch companion `entities.json.gz` for canonical ID↔name. 61.4% of
  Position records undated; raw start years span `0199`–`3013` → I-2 sanity mandatory.
- **`legislators-historical`** (unitedstates project) or voteview — the historic bioguide
  roster. Required for alumni stints; `data/engine/congestion.json` is current members only.
  Most load-bearing new upstream (D-Q9).
- **Legislative-branch agencies** — CRS, CBO, GAO, LOC, Capitol Police, AOC. Hill service that
  never touches Hill payroll. Route: Pro `agency?Type=federal-agency-person`.

---

# PHASE 2 — PARSE

## 2.1 Known parser defects

| Defect | Detail | Fix |
|---|---|---|
| **Section blindness** | Parser appears to read only the member-office range, missing leadership (front), officers (front), committees (back) | Parse the TOC per document; iterate every section |
| **Spine discards day precision** | House SOD carries `start_precision = end_precision = "day"` on 161,102/161,102 spans with `core == envelope`, but the spine re-derives bounds from `period_bounds()` of first/last reporting period (`build_hill_personnel_spine.py:2874-2888`) and throws printed dates away. Day precision **or** cross-chamber identity — not both | Walk each spine span's `source_row_ids` back to the House observations' printed dates: House lane DAY, Senate lane REPORT_PERIOD |
| **Fiscal-year office keys fragment containers** | `FISCAL YEAR 2025 CHIEF ADMIN OFCR OF THE HOUSE` splits one office into per-year containers, **suppressing real co-tenure across year boundaries** | Normalize the FY prefix out of the container key — **Paul's ruling**, office identity is not a network decision |
| **Substring side matching** | `committee_side()` used substring match, so `COMMITTEE ON MINING` → `MIN`, fabricating a minority attribution. Blast radius measured: 0 of 73 containers disagreed | Word-boundary regex. Fixed |
| **Surname-only office keys** | `HON:JOHNSON` merged 8 distinct members; 100,763 spans (21%) carried a contradicting bioguide | Keys resolve to bioguide. Fixed; both targets measure 0 |
| **`—Con.` stripper ate surnames** | `HON. DON BACON` → `HON:BA` across 1,408 rows | Fixed |
| **Payee name order** | 498 rows / 52 people written `LAST MIDDLE FIRST` in both directions | Unresolved — needs a source ruling |

## 2.2 Side is four-valued

Paul, 2026-09-03: committee staffers are bipartisan — *"Well not actually only some are."* The
population is **mixed**: side genuinely applies to some committee staff and genuinely does not
apply to others, and our data cannot currently distinguish them.

Measured: House ledger **0 of 18,865** committee episodes carry a side; spine **1,053 of 14,817
(7.1%)**. Payroll does not record it because the payroll is the committee's, not a party's.

**Make side four-valued: `maj` / `min` / `bipartisan` / `unknown`.** `bipartisan` is a real
value — a nonpartisan professional staffer has no side. `unknown` is missing data. §6.2
conflates them at the κ=0.60 fallback, which hides which is which and makes C-8c unreadable.

**Correction to an earlier claim:** the κ=0.40 "opposite side" row **is** reachable. A committee
employs both majority and minority staff on one payroll, so same-container does **not** imply
same-side. It is unpopulated for want of data, not structurally dead.

**Sources for side:** leadership office names (§1.1 Family 1) carry it explicitly; Politico Pro
committee pages resolve it per staffer.

## 2.3 Interval algebra

`core(e) = [start_latest, end_earliest)` · `envelope(e) = [start_earliest, end_latest)`

**Union before intersection**, and union again across containers. Not cosmetic: **1,000,581**
pairs share 2+ offices concurrently, and naive pairwise summation invents **13,720,047**
co-tenure days (1.0%) that unioning removes.

Possible-only overlap carries **zero** primary weight. Zero undated episodes enter temporal
weight — but undated co-affiliation edges still **exist**, at weight 0, and are counted in C-9.

---

# PHASE 3 — CONSTRUCT

## 3.1 The math

```
duration_weight = 1 - exp(-guaranteed_days / τ)      τ = 365.2425
w_work(i,j)     = Σ_c κ(c) · O(a,b)^γ · δ(Δ)          γ = 1.0
δ(Δ)            = exp(-ln2 · Δ / H)                   H = 12y
W               = ŵ_work                              (education and w_x both out)
```

Container proximity κ (§6.2), pending the four-valued rework and D-Q3 freeze: same member
personal office 1.00 · committee same side 0.75 · committee side unknown 0.60 · committee
opposite side 0.40 · leadership 0.75 · admin/officer 0.50.

**Cross-container κ**: when an edge spans two shared offices a single κ must govern it.
**Decision in force: maximum κ over contributing containers** — closest shared office governs —
with `kappa_min` emitted alongside so the alternative is recomputable without a rebuild.
Declared, not silent; overrulable.

**Substantive note for D-Q3:** personal offices are partisan silos, so **committees are where
cross-party ties form**. Committee κ is load-bearing for whole-graph connectivity, not a minor
cell. If the graph holds together, check specifically whether committee containers are what
hold it together.

## 3.2 Centrality

Eigenvector centrality is ill-defined on a disconnected or reducible graph — the existing
artifact's `PARTIAL_NULL` at tiers L3/L4 (while L2 converged) is a **fragmentation symptom**,
not an iteration limit. **Compute per connected component**, re-solve any null component
directly with `eigsh`, record which components were repaired, assert zero nulls remain, and
report the component-size distribution and largest-component fraction. That last number also
answers "how many separate colonies are there".

## 3.3 What exists and what it is

- `exploratory_temporal_tier_20260902_v1_primary` — 73,268 edges (co_tenure 54,610, membership
  12,482, revolving 6,176), 14,415 nodes, 3 layers, verification PASS, twin byte-identical.
  **Its co-tenure layer is 100% lobbyist-to-lobbyist** — all 109,220 endpoints are
  `person:lda:lobbyist:`, covering 3,794 people. It is not a staffer network. Right
  architecture, wrong population: fed from the LDA-corroborated sidecar (18,206 person-office
  records) rather than payroll.
- `staffer_social_network_20260903_v1_*` — **in progress**, same math over 188,168 payroll
  episodes / 141,241 people.
- Revolving layer: **99.0% single-person bridges** (4,942 of 4,991 dyads rest on one person);
  860 member-side orphans (13.9%) on unresolved strings like `HON:BECARRA` → **5,316 usable**;
  only 344 of 908 members are on the current roster.

## 3.4 Naming law and the dial

The `staffer_network_*` family must **fail every existing selection glob** — 9+ live
mtime-selectors match `congress_cosponsor_network_*`, and no existing loader may ingest the
staffer family by accident. Prove it mechanically (I-10a).

`STAFF_NET ∈ {off, analysis, engine}`, default **off**. `analysis` and each `engine` consumer
arm as their own individually Paul-gated changes under the standing rank-moving verification
order. Never armed wholesale.

---

## 4. Non-circularity register

### 4.1 Banned files — verified against producing code and vendor codebooks

| File | Rows | Why circular |
|---|---:|---|
| LobbyView `network.csv` | 10,937,756 | Codebook defines `bioguide_id` as **sponsor of the bill** |
| `lobbyview_network_member.csv` | 63,991 | Same defect, member-keyed |
| `our_network_*.csv` | 595,864 | **Worse** — builder credits every sponsor *and* cosponsor |
| `bill_lobbying_sidecar.json` | — | Same join |

### 4.2 The LD-2 rule
An LD-2 filing **never names a member**. Any "lobbied member" edge is a join on the bill's
cosponsor roster, so `P(joined | lobbied) = 1` by construction. **Language law I-15:** zero
influence or predictor phrasing on revolving-door or LDA-derived edges in any artifact,
manifest, or doc. Adding one is a prereg event, not a wording choice.

### 4.3 The self-fulfilling flag
`shared_employee_flag` is set by multi-office co-occurrence, **not** the printed title (88,395
flagged rows vs 32,032 with the title). Count from observed co-occurrence and from the printed
title **separately**; report both.

### 4.4 Inference never merges with observation
Predicted destinations and inferred ties live in a **separate exploratory tier**, never in
`employment_episodes` or the observed edge set. A promoted prediction becomes evidence for the
next one and the graph starts confirming itself.

**Destination inference has a real validation set**, unlike identity resolution: ~6,011
lobbyists have observed destinations. Hold a stratified slice out, predict from the co-tenure
graph alone, measure precision and recall, and report against the permuted-network null
(I-5/I-6).

### 4.5 Verified NOT circular
The revolving layer joins on `lda_source_person_id`; grep for `bill|cosponsor|sponsor` across
its builder returns zero hits.

---

## 5. Gap register

| # | Gap | Route | Status |
|---|---|---|---|
| G-1 | **54 non-member offices unparsed** in documents already held — 17 leadership, 14 officers, 23 committees | Parse the TOC per document; iterate all sections (§1.1) | **In progress** |
| G-2 | Committee side unknown; population mixed (some bipartisan, some not) | Leadership office names; Pro committee pages | Open |
| G-3 | Staffer social network did not exist — built layer is lobbyist-to-lobbyist | Rebuild over full payroll | **In progress** |
| G-4 | Pre-2009 House / pre-2011 Senate — no free census | Pro profiles per-person; Serial Set; LegiStorm (D-Q2) | Open |
| G-5 | 2009Q1/Q2 House; 2009-04, 2009-10, 2010-04, 2010-10 Senate | Serial Set (§1.5) | Open |
| G-6 | Everything except payroll is undated — Pro cards, Quorum rows, LittleSis 59.8%, bills 0/55,195 | Pro **profiles** carry month bounds | Profiles un-fetched |
| G-7 | Revolving layer 99.0% single-person bridges | More people per dyad via G-1 and G-3 | Structural |
| G-8 | 860 member-side orphans on unresolved office strings | Adjudication queue; never fuzzy-match | Open |
| G-9 | **I-4 gold set unmeasurable** — samples exist (200 identity, 100 parser) but carry `proposed_decision`, not human labels; all five gates OPEN | Human adjudication (D-Q5) | **Blocks all arming** |
| G-10 | Legislative-branch agencies and detailees | Pro `agency?Type=federal-agency-person` | Route identified |
| G-11 | 1,325 with no name match anywhere — the 80.03% cap, **STALE** (predates the Senate committee corpus) | Recount with committee corpus + paired control | Open |
| G-12 | House payee parse — 498 rows / 52 people `LAST MIDDLE FIRST` both ways | Source ruling | Open |
| G-13 | Fiscal-year office keys fragment containers | Normalize FY prefix — Paul's ruling | Measured, not changed |

**Cross-layer joins, measured:** LDA↔payroll 6,011 of 25,340 (23.7%) reach a payroll person,
only 1,561–1,582 (6.2%) at L4+L5, and 19,239 (75.9%) have no Hill payroll observation at all.
Quorum↔member is strongest — 5,635 of 5,773 (97.6%) carry a bioguide across 519 members — but
undated; only the 2,481 payroll matches (43.0%) gain quarters. **Corpus→bill→member has no
lawful path**: the canonical vocabulary (11 predicates, 6,050,221 facts) has no bill entity.

---

## 6. Identity discipline

- **STRICT-BIOGUIDE.** Members resolve by bioguide against the roster and nothing else.
  Unresolvable → logged and skipped, never fuzzy-matched.
- **`person_xref`** carries per-person source keys: Politico `profile_uuid`, Quorum id, LDA
  lobbyist id, LittleSis entity id, SOD name-office key, bioguide.
- **Declaration-directed matching** collapses the candidate pool ~451×. A Pro-stated current
  office beats a self-declared LDA covered position, which is only a lower bound.
- **Every widening runs a paired control arm** — same search in offices the person is *not*
  stated to work in. That rate is the false-positive floor, reported **per tier**. A positive
  control (rule Z) proves the arm fires. A tier whose control rate approaches its treatment
  rate does not work.
- **Office corroboration is load-bearing** — 81.4% of resolved staffers rest on it rather than
  name uniqueness. Its error rate is measured, never assumed zero.
- **Nickname table**: `data\staffer_network\reference\first_name_nicknames_v1.json` (188).
  Name changes queued, never inferred.
- **The mentat lesson**: exact-name resolvers fail silently. Ship coverage alarms with
  match-rate floors; a sub-floor run aborts fail-closed rather than shipping a plausible zero.
- **Gold check that must keep passing:** Gordon Holzberg resolves to exactly two spans and one
  directed Adams→Sykes move, gap 0 days, ABUTTING.

---

## 7. Order of operations

1. **G-1 — parse the 54 missed offices** from documents already held. Largest miss, zero
   collection cost, and it feeds κ, the side field, and the committee population at once.
2. **Index oracle (p. 3345)** — validate extraction completeness against a real denominator.
3. **G-3 — rebuild the staffer network** on the corrected population. If the G-1 miss is large,
   redo rather than patch.
4. **G-2 — committee crawl** for side and committee rosters.
5. **G-10 — agencies.** Explains part of G-11.
6. **G-11 — cap recount** with the committee corpus admitted and a paired control.
7. **G-6 — Pro profiles**, attended (~5–6 s/profile, chunked, uuid-checkpointed, resumable).
   Ask the rep first (D-Q1). Largest effort, largest payoff: dates, pre-2009 reach, departures.
8. **G-4/G-5 — 2009 backfill** via Serial Set.
9. **G-9 — gold set.** Nothing arms until this closes.

---

## 8. Acceptance bars

**A bare percentage is a defect even when true** — every figure names its window and denominator
in the same sentence.

- **C-1** Pro profiles harvested ÷ directory results on crawl date (18,618 on 2026-08-29) ≥ 99%, misses enumerated by uuid.
- **C-3** House SOD quarters ingested ÷ published 2009Q3→date = **100%** (a missing quarter is a FAIL). **C-3b** rows parsed ÷ present ≥ 99.9%, residue dumped with reasons.
- **C-3c** *(new)* — non-member offices extracted ÷ offices listed in the document's own table of contents = 100%; and names resolved ÷ names in the p.3345 index, misses enumerated.
- **C-4** Senate reports parsed ÷ published = 100% ingest, ≥ 99% of payroll lines per report.
- **C-8c** committee episodes with side known, reported with `bipartisan` and `unknown` **separately**.
- **C-9** edge date precision mix (day / month / year / undated). **Binding: an undated-only edge carries weight 0 in every duration-weighted computation**, checked mechanically.
- **C-10** members with ≥1 resolved staffer; members reachable by ≥1 alumni or shared-staffer edge.
- **I-2** interval sanity: 0 episodes with `t1 < t0`, 0 dates beyond as-of.
- **I-4** ER precision ≥ 0.98, recall ≥ 0.90 on ≥ 200 hand-adjudicated pairs. **Unmeasurable today — G-9.**
- **I-5 / I-6** negative controls: permuted (name, context) pairs match < 1%; permuted-date null reported beside the real distribution.
- **I-9** STRICT-BIOGUIDE: 0 fuzzy member joins.
- **I-10a** isolation with `STAFF_NET=off`: full chain byte-identical `ranks_python.json`, untouched dashboard hashes, measured **in the live tree** (worktree figures are void), plus a mechanical glob census.
- **I-11** determinism: two consecutive builds from identical inputs byte-identical; all writes atomic; glassbox per run.
- **I-13** robots/ToS: 0 challenge bypasses; attended-only for authenticated surfaces; a violation is a run FAIL regardless of data quality.
- **I-15** language law: 0 influence/predictor phrasings on LDA-derived edges.

Every κ, γ, half-life and α is an **UNTESTED DEFAULT** pending D-Q3.

---

## 9. Open for Paul

| ID | Question |
|---|---|
| D-Q1 | Politico: ask the account rep for an export/API, or go attended-crawl? |
| D-Q2 | LegiStorm licence — the only route to pre-2009 and a completeness-bindable corpus |
| D-Q3 | Freeze the dial defaults (κ table incl. the four-valued side rework, H=12y, γ=1.0) |
| D-Q5 | Owner for the I-4 gold-set adjudication — G-9 blocks all arming until it closes |
| D-Q9 | Adopt `legislators-historical` as the alumni roster upstream |
| G-13 | Fiscal-year office keys: normalize the FY prefix out, or keep offices split per year? |
| G-12 | House payee parse — which name order governs the 498 ambiguous rows? |
| κ-max | Cross-container κ = max over contributing containers (in force) — or min? |
| — | Time slices: one decayed snapshot (§6.7's δ) or a first-class time series? Default in force: full date bounds retained on every edge so slices can be cut later without a rebuild |
