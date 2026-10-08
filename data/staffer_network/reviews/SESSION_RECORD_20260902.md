# Employment-Tenure Lane — Session Record, 2026-09-02

Author: Fable. Every generation below is immutable, twin-verified, and independently
verified by a second implementation. Nothing is canonical: every row is
`REVIEW_REQUIRED`, `canonical_employment_promoted: false`, and both promotion counters are
pinned at 0. No git was used.

## 1. What exists now

| Generation | Contents | Verified |
|---|---|---|
| `house_personnel_ledger_..._v3` | 67 quarters 2009Q3–2026Q1, 975,058 personnel observations, 161,102 tenure spans, 49,637 member-quarters (incl. 14,182 PDF-era), 77,666 staffers, 1,023 member offices | PASS 40/40 |
| `hill_personnel_spine_..._v3` | 141,241 people, 188k person-office spans, both chambers, ledger-bound | PASS 22/22 |
| `tiered_corroboration_sidecar_..._v2` | 18,206 person-office records, nickname + term-window resolution | PASS 32 assertions |
| `exploratory_temporal_tier_..._v1` | 73,268 edges, 14,415 node scores, 3 layers | PASS, failures [] |
| `house_person_identity_..._v2` | 82,166 office-scoped identities, 2,182 names split | PASS 13/13 |
| `current_staffer_links_..._v2` | 5,773 staffers tiered | PASS, 5,773/5,773 re-derived |
| `payroll_name_resolution_..._v1` | 118,471 candidates over the full 31,113-name roster | PASS |

## 2. Coverage — the honest numbers

**Current staffers (5,773).** Two independent passes, and they disagree:

| Pass | Resolved | Rate |
|---|---:|---:|
| Baseline (start of session) | 1,985 | 34.4% |
| `current_staffer_links_v2` | 4,727 | 81.9% |
| `payroll_name_resolution_v1` | 4,228 | 73.2% |

The gap is not an error. The name-resolution pass is stricter: its R1/R2 tiers require a
*qualifying corroboration signal* (the payee paid from the staffer's own member office, or
from a committee/leadership office in a period that member was serving) AND no
contradicting middle initial or generational suffix. The link pass's T1 accepts an exact
own-member match without those extra constraints. **4,228 is the defensible floor; 4,727
is the ceiling of the same evidence under a looser rule.**

**Lobbyists (25,340 sealed LDA identities).**
- 6,011 linked to the spine via the payroll match lanes (98.5% of the 6,101 in those lanes)
- Name resolution independently reaches 3,108 at R1/R2, of which **833 are outside the old
  match lanes entirely** — genuinely new links the payroll lanes never found
- 10,652 not found at any tier

**The ceiling.** Reachable population decomposes exactly into 25,340:

| Bucket | n | share |
|---|---:|---:|
| Never declared a covered position | 17,504 | 69.1% |
| Executive branch only | 651 | 2.6% |
| Hill, but entirely pre-window | 318 | 1.3% |
| **Hill in-window — reachable** | **6,867** | **27.1%** |

Consolidated ceiling from two independent methods: **31.2–37.7%** of 25,340. We hold
46.9% of the reachable set. Paul's estimate of "at most 50%" is too optimistic by 12–19
points; his instinct that 24% used the wrong denominator was right.

## 3. What limits it (not fixable by better matching)

- **~1,400–1,500 of the 6,101 lobbyist links are expected to be pure name collisions**
  (8.63% false-positive floor, 95% CI 6.80–10.89%, measured on four independent negative
  controls). 6,101 must never be published as a count of people.
- **81.4% of resolved current staffers (3,848 of 4,727) rest on office corroboration, not
  name uniqueness.** Only 879 have a name reaching exactly one payroll identity. The
  coverage is therefore only as sound as the office attribution — which is why the spine's
  zero bioguide disagreements matter directly.
- **Name collisions in the roster itself:** 4,076 of 33,410 key triples (12.2%) are shared
  by 2+ identities; 20.4% on the looser surname + first-initial key (`SMITH J` = 29
  identities). 94.3% of these are the same person registered repeatedly in LDA, not
  distinct people.
- **PFDs cannot reach pre-2009** (corrected in session): online archives start ~2012 and a
  PFD's position schedule covers only the reporting period plus the prior year. The
  pre-2009 route is the LDA's own 20-year covered-position lookback (the A6 prose lane,
  2,525 near-candidates with resolvable office and explicit years), LegiStorm if licensed,
  or the CAPTCHA-walled pre-2009 SOD volumes (1 of 52 quarters recovered).

## 4. Defects found and fixed

- **False member attribution.** The spine keyed House member offices by bare surname, so
  `HON:JOHNSON` merged 8 members and `HON:SMITH` five; 100,763 spans (21%) carried a
  bioguide contradicting the ledger — Mike Thompson's staff attributed to Bennie Thompson.
  Fixed: keys resolve to bioguide. Both acceptance targets now measure **0**.
- **Circular shared-employee flag.** `shared_employee_flag` is set by multi-office
  co-occurrence, not only by the printed title (88,395 flagged rows vs 32,032 with the
  title). Using it to classify collisions was self-fulfilling. Non-circular re-measurement
  moved TRUE_COLLISION from 23 to 2,182.
- **Verifier blind to the PDF era.** It recounted CSV-only and compared against a full-era
  receipt, so it failed on any correct PDF build. Taught to ingest the PDF rows; now
  reports `pdf_era_coverage: NOT_SUPPLIED` rather than silently passing a partial check.
- **Member-quarters blind to 2009–2015** (0 rows for 26 quarters). Fixed: 14,182 PDF-era
  rows across 659 member offices, explicitly marked.
- **O(offices × blocks) build phase**: ~928s extrapolated → **4.7s measured, ~198×**, with
  byte-identical output.
- **Anti-promotion tripwire false positive**: flagged the builder's own
  `canonical_promotions_zero: True`. Narrowed by name; the row invariant untouched.

## 5. Corrections I made to my own claims

1. Called the Part A summary tier a defect; it was correct (union-of-lanes semantics
   pinned by INV-5). The bug was Part B's assumption. My misdiagnosis.
2. Reported 7,605 shared employees and 23 collisions from the circular flag. True
   non-circular figures: 562 and 2,182.
3. Said 515 staffers matched on surname only; the true subset is 345.
4. Claimed PFDs could reach pre-2009 service. They cannot (Paul's correction).
5. My covered-position classification (5,516 member / 1,065 agency) is not reproducible;
   the later pass gives 5,644 / 1,923 and identifies a likely cause — a regex compiled
   without case-insensitivity suppressing "Department of", "ambassador". Treat the later
   figures as better.

## 6. Open for Paul

- **T-2** I-4 identity gold set owner (the only external anchor on rule correctness).
- **T-3** LegiStorm licence — the sole route to pre-2009 Hill tenure and a
  completeness-bindable corpus.
- **T-1** v5 promotion prototype disposition (recommend: keep immutable, never armed).
- **Dial freeze** — every tier strength is `UNTESTED_DEFAULTS_PENDING_FREEZE`.
- **Network layering** — Paul's own design task, to be raised once collection settles:
  562 title-declared shared employees (up to 133 offices each) are the "between members"
  layer; single-office staffers nest beneath one member.
- **House payee parse** — 498 rows / 52 people written `LAST MIDDLE FIRST` in both
  directions; unresolvable without a source ruling. One known regression rides on it.
- **3,229 unlinked reachable lobbyists name a member or committee in their own filing
  text** — the concrete remaining work inside the current ceiling.
