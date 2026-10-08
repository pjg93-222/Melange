# Hill personnel spine v7 — identity-quality audit

**Generation audited:** `audits\staffer_network\hill_personnel_spine_20260907_v7_primary`
(spine 144,690 rows · spans 204,697 · member office index 2,032 · id map 144,693)
**Cross-referenced:** `audits\staffer_network\house_personnel_ledger_20260903_v5_primary`
(observations 1,083,510) and `audits\staffer_network\house_person_identity_20260902_v2_primary`
**Date:** 2026-09-08 · **Mode:** read-only. No spine code, generation or artifact was changed.
**Method:** every number below was recomputed by streaming the released `.ndjson.gz`
files; none is quoted from a receipt unless the row says so. Scripts:
`…\scratchpad\p1_spine.py`, `p1b_vcheck.py`, `p2_spans.py`, `p3_project.py`,
`p4a_overlap.py`, `p4b_classes.py`, `p5_undermerge.py`, `p6_refine.py`,
`p7_shared_shape.py`, `p8_residuals.py`, `p9_final.py`.

**Verification that the join is sound:** the projection of the v5 ledger onto the v7
spine reproduces the spine builder's own two counters exactly —
`ledger_rows_with_shared_employee_flag` 135,887 and
`ledger_rows_with_shared_employee_title` 52,647 — and joins 1,083,416 of 1,083,510
observation rows to a spine person, matching the receipt's `office_key_present`.

---

## Three corrections to the task's premises

| # | Premise as given | What the artifacts say |
|---|---|---|
| P1 | "the ledger's measured classes (SHARED_EMPLOYEE 7,605 / SEQUENTIAL_ONLY 3,934 / MID_QUARTER_MOVE 161 / TRUE_COLLISION 23 over 60,136 people)" | Those five numbers are **not** the measured classes. They are `circularity_finding.negative_control_if_flag_were_used` in `house_person_identity_20260902_v2_primary\house_person_identity_receipt.json` — the collapse that occurs **if** the circular flag is used. The measured classes on the same receipt are SINGLE_OFFICE 48,420 / SEQUENTIAL_ONLY 3,934 / MID_QUARTER_MOVE 5,045 / SHARED_EMPLOYEE 562 / **TRUE_COLLISION 2,182** over 60,143 person keys. |
| P2 | "per the House ledger's `shared_employee_flag`" | Both downstream builders refuse that field on record. `build_house_person_identity.py:18-38` proves it circular (`build_house_personnel_ledger.py:1135-1140` sets it true for *any* name in ≥2 offices in a quarter). `build_hill_personnel_spine.py:57` and `:4381-4391` say the same; the spine's own `shared_employee` is `is_shared_employee(title)` (`:1469-1472, :1557, :1641`) — the **printed title only**. This audit reports both tests side by side. |
| P3 | the identity census is over the same ledger as the spine | It is not. The census generation ran over `house_personnel_ledger_20260902_v1_primary` (681,177 rows, 2016Q1–2026Q1, 60,143 keys). The spine consumes **v5** (1,083,510 rows, 2009Q3–2026Q2, 81,826 keys). Section 1 therefore recomputes both rules over v5. |

---

## 1. Over-merging risk

### 1a — persons carrying spans in two or more offices

Computed by streaming `hill_person_office_spans.ndjson.gz` and counting distinct
`(chamber, office_key)` per `spine_person_id`.

| Measure | Count | Share of 144,690 |
|---|---:|---:|
| Persons with spans in **2+ distinct offices** | **28,131** | 19.44% |
| … by `office_key` alone (chamber ignored) | 28,130 | 19.44% |
| Persons in exactly one office | 116,559 | 80.56% |
| Persons whose offices span both chambers | 2,230 | 1.54% |
| Largest office count on one person | 133 | — |
| House-side subset (persons with 2+ *spine* offices among House rows) | 18,317 of 85,917 | 21.32% |

### 1b — day-level overlapping service in two offices in the same period

Test: for each spine person, group the joined ledger observations by quarter; inside
a quarter, group by **spine** `office_key`; two offices overlap when any printed
service window of one intersects any window of the other on ≥1 day. This is exactly
`guaranteed_overlap_days(as_interval(a), as_interval(b)) > 0`
(`fec\staffer_network\intervals.py:79-86`, end bound = end_inclusive + 1 day).

| Measure | Count |
|---|---:|
| Candidates (2+ spine offices, House rows) | 18,317 |
| Persons with a day-level same-quarter two-office overlap | **1,298** |
| Overlapping person-quarters | 12,029 |
| …of those, **no printed SHARED EMPLOYEE title** in the overlapping quarter | **0** |
| …of those, **no ledger `shared_employee_flag`** in the overlapping quarter | **0** |
| Senate persons holding two Senate offices in one report period | **0** |

**Reading.** On the House side the spine has zero over-merges of the kind D-020
forbids. Every one of the 1,298 day-level overlaps it tolerates is carried by a
printed SHARED EMPLOYEE title in the same quarter, and the corresponding negative
population — overlap without a title — is empty under either shared-employee test.
The rule is implemented as written.

### 1c — the 23 TRUE_COLLISION cases, and what v7 did with them

Both rules recomputed over the **v5** ledger the spine actually consumes:

| Class | Printed-title rule (the lane's rule) | Ledger-flag rule (the circular control) |
|---|---:|---:|
| SINGLE_OFFICE | 64,204 | 64,204 |
| SEQUENTIAL_ONLY | 6,593 | 6,593 |
| SHARED_EMPLOYEE | 782 | 10,766 |
| MID_QUARTER_MOVE | 7,028 | 229 |
| **TRUE_COLLISION** | **3,219** | **34** |
| person keys / multi-office names | 81,826 / 17,622 | 81,826 / 17,622 |

Cross-reference of every TRUE_COLLISION name against the spine ids its rows land on:

| Rule | TRUE_COLLISION names | held as **2+ spine ids** (correct, fail-closed) | held as **ONE spine id** |
|---|---:|---:|---:|
| Ledger-flag rule (the "23" analogue: 34 names on v5) | 34 | **34 (100%)** | **0** |
| Printed-title rule | 3,219 | 3,215 (99.88%) | **4** |

The 34 flag-rule names — every one of them two or more spine ids — are:
AHN|MICHAEL|M, AMAR|JONATHAN|Z, ARCE|JULIA|L, ARRIGHI|THOMAS|W, BARBER|CRAIG|,
BROMAN|JOCELYN|, BURNS|EMILY|M, DALY|HUGH|E, EASBYSMITH|ANNE|S, FLYNN|CAROLINE|M,
GAST|JONATHAN|P, GLEESON|JAMES|M, HOAR|RICHARD|, HYSOM|TIMOTHY|D (3 ids),
KENNEDY|JOHN|D, KOURI|JOSEPH|E, MAGALLANES|NICOLAS|, MURRY|LUKE|A, OMS|VICTORIA|R,
ORR|IAN|F, REAVES|TAYLOR|D, RICCI|ANDREW|, RODRIGUEZARGOTE|ESTEFANIA|L,
ROXBURGH|JESSICA|A, SCHWOEFFERMANN|IRENE|B, SHACKLEFORD|CLAIRE|D, SMITH|DANIEL|A,
THORMAN|SADIE|D, VIGIL|MARY|A, WALKER|RYAN|L, WHITE|CLAY|L, WHITE|JOSEPH|E,
WONG|STEPHANIE|P, YOUNG|SARAH|G.

The **4 exceptions are not over-merges**. All four are the same 2013Q1 pair of ledger
office keys, `HONRAW:HON. TIMOTHY J. RYAN` vs `HON:R000577`, which are the same
office under two ledger spellings; the spine's office normalization folds them into
one node (`office_count = 1`, `office_raw_examples` = "2009 HON. TIMOTHY J. RYAN",
"2010 HON. TIM RYAN"). The ledger key is the artifact and the spine is right:

| person_key | v7 spine id | spine offices | span |
|---|---|---:|---|
| SOD:ISENBERG\|ERIN\|L | `…63cc1fe1` | 1 (`HON:R000577`) | 2009Q3–2023Q1, 80 obs |
| SOD:KEATING\|RYAN\|P | `…dc0411df` | 1 (`HON:R000577`) | 2009Q3–2023Q1, 78 obs |
| SOD:LEONARD\|RICHARD\|W | `…26fba5aa` | 1 (`HON:R000577`) | 2009Q3–2023Q1, 79 obs |
| SOD:ZETTS\|MICHAEL\|P | `…bbfde937` | 1 (`HON:R000577`) | 2011Q3–2021Q4, 74 obs |

### 1d — where the over-merge risk actually sits: the Senate has no discriminator

D-020 names day-level service dates as the discriminator. Measured coverage:

| Chamber | Spans | `date_precision = DAY` | Day-level discriminator available |
|---|---:|---:|---|
| House | 132,460 | 132,433 (99.98%) | yes |
| Senate | 72,237 | 0 | **no — 35.3% of the corpus** |

The consequence is visible in the three merges v7 applied. The delta report's own
guard preview (`rekey_delta_report_v1_1_1.json`, `merges.cooccurrence_guard_preview`)
states that under the ruled guard "every merge group on this generation is blocked,
so the guard makes the merge feature inert". The shipped guard blocked **0**, because
it was narrowed to require day-level overlap:

| Merge group | Basis | Evidence actually used |
|---|---|---|
| `beresik\|michael\|t` (michael/micheal) | `same_period_day_level_disjoint` | House day dates disjoint — evidenced |
| `cooper\|elizabeth\|m` (beth/elizabeth) | `same_period_variant_no_day_dates` | **none — Senate prints no day dates** |
| `wood\|katherine\|r` (catherine/katherine) | `same_period_variant_no_day_dates` | **none — Senate prints no day dates** |

Two of three merges (67%) rest on absence of evidence in the same office and the same
report period. The guard is structurally incapable of firing on any Senate pair. The
exposure it sits on: 816 Senate spans carry more observations than observed periods
(955 extra payee lines inside a single report period), and 6,465 of 58,773
Senate-only persons are recorded under two or more raw spellings.

---

## 2. Under-merging

`name_key` = `last|first_class|middle_initial`. A key held by two or more distinct
`spine_person_id`s is a person the spine deliberately keeps apart.

| Measure | Count |
|---|---:|
| name_keys held by 2+ distinct spine ids | **16,151** |
| Distinct spine ids on those keys | **37,684** (26.05% of 144,690) |
| …in groups whose ids are in **wholly different offices** | 15,929 groups / **37,106 ids** |
| …in groups where two ids share an office | 222 groups / 578 ids |
| Largest number of spine ids on one name_key | 30 |

### 2a — shape of the within-key pairs (31,556 pairs)

Windows are per person: core = `min(core.start_latest) … max(core.end_earliest)`
(guaranteed service), envelope = `min(envelope.start_earliest) … max(envelope.end_latest)`.

| Pair shape | Pairs | Share |
|---|---:|---:|
| **Overlapping** (core windows intersect — shared-employee shape) | 27,827 | 88.2% |
| **Sequential** (envelopes disjoint, gap < 10 y — career move) | 2,909 | 9.2% |
| **Disjoint by decades** (envelopes disjoint, gap ≥ 10 y) | 77 | 0.2% |
| Ambiguous (envelopes touch, cores do not) | 743 | 2.4% |

At group level: 15,896 groups contain at least one overlapping pair; 187 are entirely
sequential under 10 y; 12 are entirely separated by a decade or more; 1 is mixed;
55 contain only ambiguous pairs.

### 2b — size of the class if cross-office identity were evidenced by day-level contiguity

Nothing was changed; these are counterfactual sizes only.

| Merge rule applied to same-name-key ids | Ids removed | Spine persons after |
|---|---:|---:|
| Only groups with **no** overlapping pair and every pair envelope-disjoint (the clean career-move class) | **197** | 144,493 (−0.14%) |
| Any envelope-disjoint pair, transitive closure, gap ≤ 5 y | 2,400 | 142,290 (−1.66%) |
| Any envelope-disjoint pair, transitive closure, any gap | 2,861 | 141,829 (−1.98%) |

The 197-figure is the defensible one; the two transitive-closure figures are upper
bounds, because A-disjoint-B and B-disjoint-C can chain even when A overlaps C.
Minimum gap in the 197 clean groups: 0–1 y 113, 1–5 y 44, 5–10 y 28, ≥10 y 12.

### 2c — the class the spine loses most people to

The 88.2% overlapping pairs are not two people wrongly split *in general* — a common
name held by two contemporaries is the expected case. But the subset with **many**
ids, disjoint offices and identical printed titles is one person split apart:

| Group population (overlapping + office-disjoint) | Groups | Spine ids |
|---|---:|---:|
| Senate only | 7,643 | 17,127 |
| House only | 3,237 | 6,767 |
| Both chambers | 4,960 | 13,107 |
| **Total** | **15,840** | **37,001** |
| …of which groups holding 5+ ids | 165 | 1,219 |

Worked evidence, `wallner|jamie|i` — 34 spans, **30 spine ids**, 2010-10-01…2020-09-30,
every span titled `EXECUTIVE DIRECTOR` with the same printed date annotations
(`FROM SEP. 1`, `TO JUL. 15`), `shared_employee = False` on all of them because the
Senate report never prints the phrase:

| Period | Office | Title | shared |
|---|---|---|---|
| 2012-04-01…2016-04-01 | SENATOR A. MITCHELL MCCONNELL, JR. | EXECUTIVE DIRECTOR FROM SEP. 1 | False |
| 2012-04-01…2016-04-01 | SENATOR BOB CORKER | EXECUTIVE DIRECTOR FROM SEP. 1 | False |
| 2012-04-01…2016-04-01 | SENATOR JOHN CORNYN | EXECUTIVE DIRECTOR TO JUL. 15 | False |
| 2012-04-01…2012-10-01 | SENATOR JIM DEMINT | EXECUTIVE DIRECTOR TO JAN. 1 | False |
| … 26 more senator offices | | | |

`bovard|rachel|a` is the same shape: 21 spans, **21 spine ids**, 2011-10-01…2015-04-01,
every one `POLICY ADVISOR FROM MAR. 24` / `POLICY DIRECTOR`, all `shared = False`.

### 2d — top 20 name_keys by distinct spine ids

| name_key | ids | offices | window | office shape |
|---|---:|---:|---|---|
| wallner\|jamie\|i | 30 | 34 | 2010-10-01…2020-09-30 | senate member offices |
| chartan\|steven\|a | 26 | 44 | 2010-10-01…2024-03-31 | house HON offices |
| guernsey\|andrew\|i | 24 | 30 | 2015-04-01…2025-03-31 | house leadership + senate |
| mooney\|arnold\|g | 24 | 25 | 2010-10-01…2014-09-30 | senate member offices |
| gaffin\|michael\|a | 23 | 23 | 2010-10-01…2017-03-31 | senate member offices |
| galvin\|grace\|s | 22 | 46 | 2018-10-01…2026-09-30 | house HON offices |
| bovard\|rachel\|a | 21 | 21 | 2011-04-01…2016-03-31 | senate member offices |
| mcmullan\|matthew\|p | 21 | 24 | 2013-04-01…2025-09-30 | house + senate |
| corrigan\|edward\|t | 18 | 19 | 2010-10-01…2019-03-31 | senate member offices |
| davis\|charlotte\|m | 18 | 18 | 2010-10-01…2013-09-30 | senate member offices |
| baig\|gwendolyn\|f | 17 | 33 | 2010-10-01…2026-09-30 | senate cttee + member |
| brown\|clinton\| | 17 | 22 | 2013-10-01…2023-09-30 | senate member offices |
| stanley\|rachel\|b | 17 | 17 | 2022-04-01…2024-09-30 | senate member offices |
| foltz\|jonathan\|r | 16 | 20 | 2012-10-01…2026-09-30 | senate cttee + member |
| oconnor\|mary\|m | 16 | 24 | 2009-04-01…2026-06-30 | house HON offices |
| hess\|jordan\|h | 15 | 15 | 2012-04-01…2017-09-30 | senate member offices |
| senatesteeringcommitteebaig\|gwendolyn\|f | 15 | 16 | 2016-10-01…2019-09-30 | senate member offices |
| ide\|matthew\|d | 14 | 19 | 2018-10-01…2026-09-30 | house + senate |
| knese\|chris\|m | 14 | 15 | 2013-04-01…2017-09-30 | senate member offices |
| drummy\|erin\|s | 13 | 14 | 2022-04-11…2026-09-30 | house + senate |

Seventeen of the twenty are the Senate many-member-office shape. Row 17,
`senatesteeringcommitteebaig|gwendolyn|f`, is row 11 (`baig|gwendolyn|f`) with the
section header glued onto the surname — see 2e.

### 2e — surname contamination splits one person across two name_keys

The Senate report's section header can be glued to the payee surname with no
separator, and the annotation strip only removes *trailing* annotations, so the header
survives into `name_standard_parts.last` and therefore into `name_key`.

| Measure | Count |
|---|---:|
| Distinct name_keys whose parsed surname contains an office/section phrase | **32** |
| Spine ids sitting on those keys | **58** |
| Parsed surnames ≥ 18 characters (the wider suspect pool) | 683 |

The proof is byte-level: `payee_raw` is `SENATE STEERING COMMITTEEBAIG, WENDY F`
against the clean `BAIG, WENDY F`, and `SENATE STEERING COMMITTEEWALLNER, JAMES I`
against the clean `WALLNER, JAMES I`. Wendy F. Baig is therefore held as 17 ids under
`baig|gwendolyn|f` plus 15 under `senatesteeringcommitteebaig|gwendolyn|f` = **32 ids
for one person**; Clinton Brown as 17 + 13 = 30; James I. Wallner as 30 + 1 = 31.
The same mechanism produces `ofthesenateerickson|nancy|` (Nancy Erickson, Secretary
of the Senate), `ofthesenateadams|julie|` (Julie Adams), `sergeantatarmscioarmstrong`,
`analystdemocraticackerman`, and 26 others.

---

## 3. The 25 delta residuals

Each residual is a legacy id where the v1.1.1 delta reconstruction's key differs from
the key this build produced. All 25 legacy ids were resolved to their v7 spine row and
the built key inspected against the person's own raws.

| # | reconstruction key | built key (= actual) | payee_raw(s) | verdict |
|---|---|---|---|---|
| 1 | akers\|lyndsey\|v | akers\|lyndsey\| | AKERS, LYNDSEY | reconstruction artefact — no V in the raw |
| 2 | anand\|tarunika\|v | anand\|tarunika\| | ANAND TARUNIKA | reconstruction artefact |
| 3 | camacho\|cara\|v | camacho\|cara\| | CAMACHO,CARA | reconstruction artefact |
| 4 | facchiano\|gregory\|v | facchiano\|gregory\| | FACCHIANO GREGORY / FACCHIANO, GREGORY | reconstruction artefact |
| 5 | jackson\|jamie\|v | jackson\|jamie\| | JACKSON,JAMES | reconstruction artefact |
| 6 | kane\|sanjay\|v | kane\|sanjay\| | KANE,SANJAY | reconstruction artefact |
| 7 | khanna\|raman\|v | khanna\|raman\| | KHANNA, RAMAN | reconstruction artefact |
| 8 | mcbride\|emily\|v | mcbride\|emily\| | MCBRIDE, EMILY | reconstruction artefact |
| 9 | mcbride\|emily\|v | mcbride\|emily\| | MCBRIDE, EMILY | reconstruction artefact (2nd legacy id) |
| 10 | mcbride\|emily\|v | mcbride\|emily\| | MCBRIDE, EMILY | reconstruction artefact (3rd legacy id) |
| 11 | perez\|rosa\|v | perez\|rosa\| | PEREZ, ROSA | reconstruction artefact |
| 12 | roberson\|andrew\|v | roberson\|andrew\| | ROBERSON DREW | reconstruction artefact |
| 13 | smith\|matthew\|v | smith\|matthew\| | SMITH MATTHEW / SMITH,MATTHEW | reconstruction artefact |
| 14 | tran\|richard\|v | tran\|richard\| | TRAN, RICHARD | reconstruction artefact |
| 15 | trubetskoy\|vadim\|v | trubetskoy\|vadim\| | TRUBETSKOY, VADIM | reconstruction artefact |
| 16 | waters\|monique\|v | waters\|monique\| | WATERS,MONIQUE | reconstruction artefact |
| 17 | woronoff\|arielle\|v | woronoff\|arielle\| | WORONOFF, ARIELLE | reconstruction artefact |
| 18 | gural\|harry\|d | gural\|harry\| | GURAL, HARRY DEMOCRATIC | reconstruction artefact — "DEMOCRATIC" read as an initial; build strips it |
| 19 | gural\|harry\|d | gural\|harry\| | GURAL, HARRY DEMOCRATIC | same, 2nd legacy id |
| 20 | english\|amy\|v | english\|amy\|a | ENGLISH, AMY A / ENGLISH, AMY AS TAFF | real 2-raw ambiguity, build resolved it correctly ("AS TAFF" = "A" + "STAFF") |
| 21 | delapena\|sebastian\|g | delapena\|diego\| | DE LA PENA DIEGO | real particle ambiguity, **build correct** (last = DE LA PENA) |
| 22 | vanderheide\|escobar\|j | vanderheide\|jennifer\| | VAN DER HEIDE JENNIFER | real particle ambiguity, **build correct** |
| 23 | vandewater\|logan\|e | vandewater\|parker\| | VAN DE WATER PARKER | real particle ambiguity, **build correct** |
| 24 | delos\|reyes\|e | delos\|reyes\|v | DE LOS REYES VANESSA M. | **real defect in the built key** — surname truncated to "DE LOS", given name pushed into `middle` |
| 25 | delos\|santos\|k | delos\|santos\|f | DE LOS SANTOS FLORES BABUR I | **real defect in the built key** — same truncation |

**Tally: 20 reconstruction artefacts, 3 real ambiguities the build resolved correctly,
2 real defects in the built key.**

The 17 phantom-V residuals are exactly the `v_initial` gap between the report (1,150)
and the build (1,133) — the mechanism is the ambiguous-triple raw selection
(`ambiguity.ambiguous_triples = 64`, `spine_people_on_an_ambiguous_triple = 102`,
`residual_allowance = 102`): the reconstruction keys a v6 *triple* and may pick a raw
belonging to another person on that triple, while the build keys only the raws that
person was recorded under. The build is right in all 20.

The 2 real defects generalize: the particle handler covers `DE LA`, `VAN DER`,
`VAN DE` but not `DE LOS`. **5 spine rows** carry the truncated surname `DE LOS`
with the true given name in `middle`, and two of them collide on one key
(`delos|santos|k` is held by two distinct spine ids, both raw `DE LOS SANTOS KAREN`).
Because the surname fragment occupies the `first_class` slot, any two `DE LOS X`
people whose given names share an initial receive the same name_key.

---

## 4. Collision ordinals

| Measure | Count | Expected |
|---|---:|---|
| Spine rows total | 144,690 | 144,690 |
| Rows with `collision_ordinal = 1` | **144,690** | all |
| Rows with `collision_ordinal` null | **0** | 0 |
| Rows with `collision_ordinal > 1` | **0** | 0 |
| Merges blocked (`merges_blocked_pairs`) | 0 | 0 |

Consistent, and the receipt's `collision_ordinals_above_one = 0` is confirmed against
the data. The ordinal field is therefore carrying no information on this generation:
it is in the hashed id tuple for reconstructability, and every row takes the same
value. **The finding is not the zero; it is why the zero happened** — see 1d. The
guard the delta report described would have blocked all three merges and left the
count at 144,693; the guard that shipped blocked none.

---

## 5. Suffix and V-initial aftermath

| Measure | Measured | Expected in the task | Status |
|---|---:|---|---|
| Rows with non-null `payee_key.suffix` | **2,231** | ~3,382 minus the V reclassification | expectation not reproducible from any field in the release; the receipt's own `rows_with_a_suffix_from_raw_parse` is 2,231 |
| Rows with non-empty `name_standard_parts.suffix` | 2,231 | — | the two fields agree exactly |
| Rows with `suffix_observed` holding 2+ distinct values | **57** | 61 | receipt also says 57 |
| Rows with `payee_key.middle_initial == 'v'` | **182** | ~1,133–1,166 | this is the wrong field |
| Rows whose **name_key** middle component is `v` | **1,311** | ~1,133–1,166 | this is the identity-bearing field |
| Rows with `name_standard_parts.middle` exactly `V` | 1,100 | — | of these, 1,093 have `payee_key.middle_initial = null` |
| `v_initial` keys **changed** by the rule | 1,133 (build) / 1,150 (report) | 1,133–1,166 | the 1,133 in the task is the *change* count, not the *population* |

Note the field split: `payee_key.middle_initial` is the legacy tokenizer's output,
which deletes a bare V; `name_key`'s third component comes from the new standard,
which recovers it. Any consumer keying on `payee_key` sees 182 V-people; any consumer
keying on `name_key` sees 1,311.

### Suffix under-capture

55 rows carry a `JR|SR|II|III|IV` token in `payee_raw` while `payee_key.suffix` is
null — e.g. `EASTON, ALLEN R III`, `FISCHER JR ROBERT V.`, `DAVIS IV,JOHN B`
(suffix after the middle initial, or in surname position). Since suffix is **not** a
component of `name_key`, a suffix never separates two people; it only annotates them.

Of the 57 rows carrying two distinct observed suffixes, **51 are a column-shift
artefact**, not two people: the SOD's fixed-width split turns `ALLEN R III` into
`ALLEN RI II`, so `II` and `III` are the same printed suffix. Only **6 are genuinely
different suffixes on one spine id** — the concrete generational-collapse candidates:

| name_key | suffixes seen | raws | spine id |
|---|---|---|---|
| neale\|kevin\|a | JR, SR | NEALE, KEVIN A / … A JR / … A SR | `…ead239940dc8af` |
| fischer\|robert\|v | III, JR | FISCHER III,ROBERT V / FISCHER JR ROBERT V. | `…0bd5e007916058` |
| miller\|louis\| | III, JR | MILLER III LOUIS / MILLER JR LOUIS | `…8fa2571cd245cc` |
| lewis\|charles\|e | III, JR | LEWIS III,CHARLES E / LEWIS JR,CHARLES E | `…a113398539419c` |
| davis\|john\|b | III, IV | DAVIS IV,JOHN B / DAVIS, JOHN BYRON III | `…45da56ccc4601e` |
| schuyler\|charles\|r | III, IV | SCHUYLER III,CHARLES R / SCHUYLER IV CHARLES R. | `…ba9bd26a9837f7` |

### V spot-check — 10 rows drawn at random (seed 20260908) from the 1,311

| name_key | payee_raw | `nsp.middle` | reading of the initial |
|---|---|---|---|
| oestringer\|chanelle\|v | OESTRINGER, CHANELLE V | V | correct |
| meadows\|carrie\|v | MEADOWS, CARRIE V. | V | correct |
| eppes\|lesya\|v | EPPES, LESYA V | V | correct |
| stone\|trenton\|v | STONE, TRENTON V | V | correct |
| rainbolt\|john\|v | RAINBOLT III, JOHN V. | V | correct (suffix III in surname position; not captured — see above) |
| sudakov\|briana\|v | SUDAKOV BRIANA V | V | correct |
| valusek\|pat\|v | VALUSEK, PATRICIA V. | V | correct (PATRICIA → `pat` by nickname class) |
| petrone\|katrina\|v | PETRONE, KATRINA VL EGISLATIVE | VL EGISLATIVE | correct — "V" + bled title "LEGISLATIVE…" |
| vanorden\|tammy\|v | VAN ORDEN, TAMMY V | V | correct (particle surname handled) |
| schechter\|henry\|v | SCHECHTER HENRY V. | V | correct |

**10 of 10 correct.** The V rule repairs a real defect: the legacy tokenizer was
deleting a genuine middle initial. Its direction is *splitting* — 1,133 keys became
more specific.

---

## 6. Name-only join degradation

Measured two independent ways that agree exactly: directly over
`hill_person_spine.ndjson.gz` (grouping `spine_person_id` by `name_key`) and over
`spine_id_map_v6_to_v7.ndjson.gz` (grouping `legacy_person_id` by `key_v6` and
`person_id` by `key_v7`).

| | Distinct keys | Keys held by 2+ people | People on those keys |
|---|---:|---:|---:|
| **v6** (measured) | 123,658 | **15,828** | **36,863** |
| **v7** (measured, both routes) | 123,157 | **16,151** | **37,684** |
| v7 as projected by the delta report | 123,137 | 16,162 | 37,718 |
| v7 as stated in the task | — | 16,077 | 37,474 |
| Change v6 → v7 (measured) | −501 | **+323 (+2.04%)** | **+821 (+2.23%)** |

The v6 half of the claim reconfirms exactly. The v7 half does not: the built spine is
16,151 / 37,684, the delta report projected 16,162 / 37,718, and the task's
16,077 / 37,474 matches neither. The *direction and rough size* of the claim stand —
a name-only join collides on more people after v1.1 — but the figures to quote are
**16,151 keys / 37,684 people**, +2.0% keys and +2.2% people over v6.

The degradation is the intended price of nickname folding: 12,630 keys changed by
`nickname_class` alone (james→jamie 1,311, christopher→chris 1,178,
catherine/kathryn→katherine 841 combined), which merges spelling variants of one
person and, as a side effect, merges distinct people who differ only by nickname.

**Practical rule this implies for any consumer.** `name_key` is not a person
identifier and must never be joined on alone: 26.05% of spine persons (37,684 of
144,690) sit on a key shared with at least one other person, and one key carries 30.
The only person-grade key is `spine_person_id`; the only safe name-based join is
`(name_key, chamber, office_key)` restricted to a period window, which is the tuple
the spine itself hashes. A consumer that joins on `name_key` alone will attach one
person's record to a median of 2 and a maximum of 30 spine persons, and the error is
2.2% worse than it was on v6.

---

## Verdict

**The spine is biased toward splitting, decisively and by design.** The evidence, in
the order it weighs:

- The one over-merge test D-020 actually names — day-level overlapping service in two
  offices in one period without a shared-employee title — returns **0** on the House
  side under either shared-employee test, and **34 of 34** flag-rule TRUE_COLLISION
  names are held as two or more spine ids. The 4 apparent exceptions are a ledger
  office-key artefact the spine correctly normalized away. The splitting rule is
  implemented as written and is not leaking.
- Against that, **37,684 spine ids (26.05%) sit on a shared name_key**, 37,106 of them
  in groups whose offices are wholly disjoint, and 15,840 of those groups have
  overlapping service windows — the shared-employee shape. One Senate Steering
  Committee staffer is held as 30 people (`wallner|jamie|i`), another as 21
  (`bovard|rachel|a`), and one person is held under two different name_keys and
  32 ids (`baig|gwendolyn|f` / `senatesteeringcommitteebaig|gwendolyn|f`).
- The v7 changes all pushed the same way. The V rule split 1,133 keys apart
  (correctly — 10 of 10 spot-checked). Nickname folding merged 12,630, which is the
  only merging force in the release and it operates on *spelling*, not on service.
  Three merges were applied against 25,075 same-period office splits.
- The single asymmetry that is genuinely unsound cuts **both** ways from the same
  missing evidence. Senate reports print no day dates. In the *merge* guard, absence
  of day dates is read as permission to merge (2 of 3 merges, basis
  `same_period_variant_no_day_dates`); in the *cross-office link* rule, the same
  absence is read as a bar to linking (0 Senate persons hold two offices in one
  report period). One missing field, two opposite defaults, and the permissive one is
  applied to the 3 cases while the restrictive one is applied to 17,127 ids.

**Highest-value single change to the identity rule:** give the Senate a
day-date-free evidence route, and make it the *same* route in both directions.
Concretely — link two office nodes carrying one `name_key` when, in the same report
period, they print the **same title string including its date annotation**
(`EXECUTIVE DIRECTOR FROM SEP. 1`, `POLICY ADVISOR TO SEP. 11`). That string is the
Senate's functional equivalent of the House's printed SHARED EMPLOYEE title: it is
verbatim source text, it is already carried on the span row in `titles`, and it is
what makes the Wallner and Bovard cases obvious to a reader in one glance. It
addresses the largest measured defect class — 7,643 senate-only groups holding
17,127 spine ids, plus the 4,960 cross-chamber groups holding 13,107 — without
touching the House rule that is currently working. It should be paired with the
mirror-image tightening: when day dates are absent, absence must stop authorizing a
merge as well, which would return the 2 unevidenced Senate merges to the blocked
state the delta report's guard preview described.

Two cheaper repairs, both bounded and both splitting-side:

1. Strip *leading* office/section headers from the surname as the annotation rule
   already strips trailing ones — 32 keys, 58 spine ids, and it alone recovers
   Baig (32 → 17), Brown (30 → 17) and Wallner (31 → 30).
2. Extend the particle table with `DE LOS` / `DE LAS`. Five rows carry a truncated
   surname today and two of them already share one key.

**Open risk for the orchestrator to rule on.** All of section 1's cross-reference is
computed over the v5 ledger because that is what the spine consumes; the 2,182 /
3,934 / 5,045 / 562 census in circulation is over the v1 ledger and is a different
population (60,143 vs 81,826 person keys, 2016Q1– vs 2009Q3–). Any downstream document
quoting the v1 numbers against a v7 artifact is comparing two generations. Whether the
identity census should be re-run on v5 is a scope call, not a finding.
