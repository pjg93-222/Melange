# Employment-tenure lane — state record, 2026-09-03

Nothing here is canonical. Every generation referenced is `REVIEW_REQUIRED`,
`canonical_employment_promoted: false`, promotion counters pinned at 0. No git was used.

This record exists because five background agents and one workflow were killed by Claude Code
process exits during this session. It captures what is established, what landed on disk, and
where to resume — so none of it has to be re-derived.

## 1. Settled this session

### H2 (compensation class) — CLOSED, NEGATIVE

Hypothesis: `person_quarter_offices` was populated from BASE rows only, so people appearing
only in non-BASE rows might be missing from the person universe entirely.

Measured against `house_personnel_ledger_20260902_v3_primary/house_personnel_observations.ndjson.gz`:

| compensation_class | rows |
|---|---:|
| BASE | 906,612 |
| OTHER COMPENSATION | 58,724 |
| OVERTIME | 9,722 |
| **total** | **975,058** |

Distinct `person_key`: 77,666. **People with no BASE row: 31.**

The ledger admits all three classes. The hypothesis accounts for at most 31 people. The 1,325
unmatched are not hiding here. Lead closed.

### The 80.03% cap is STALE

The cap (1,325 of 6,634 reachable people with no name match anywhere) was measured when the
person universe held Senate Volume I personal offices plus House SOD only. Senate Volume II —
committee payrolls, 7,187 distinct payees across 43 offices — did not exist at the time.

**No coverage or ceiling number predating the committee corpus should be quoted until the
recount runs.** Same defect class as earlier stale-input errors: a number carried forward
across a change to its own inputs.

## 2. On disk, verified present

| Generation | State |
|---|---|
| `senate_committee_payroll_20260903_v2_{primary,twin,verification}` | Receipt PASS: 34,865 rows, 43 offices, 7,187 payees, 30 periods. `verification_report.json` status **FAIL** on check V2. |
| `senate_committee_payroll_20260903_v3_{primary,twin}` | Both built, 5 files each. **No `_v3_verification` directory** — the agent died mid-verify. |
| `corpus_backfill_2009_raw` | 21 files (was 6 earlier in session). Discovery complete; ingestion not. |

### The V2 failure is an opportunity, not just a bug

Failing evidence row, `GPO-CDOC-117sdoc8` page 21:

```
SCHAPITL, ASHLEY OVERSIGHT-DEPUTY POLICY DIRECTOR-SPOKESPERSON TO MAY 29 AND $39,666.65
```

`TO MAY 29` is a **day-level departure date printed inline**, being absorbed into the title
field by the parser. The Senate corpus is otherwise period-level (semiannual) — the coarsest
resolution in the lane. Recovering these converts a six-month smear into an exact date for
every person who has one.

Before writing any rule: survey the corpus for the real variant family (`TO <MONTH> <DAY>`,
`FROM <MONTH> <DAY>`, `FROM ... TO ...`, others) and quote real examples of each. Then measure
corpus-wide how many rows carry a qualifier and how many distinct people gain a boundary they
did not previously have.

## 3. The 2009 backfill — documents identified, route not yet found

Targets, from `backfill_2009_discovery.json`:

- Senate Document No. 2 (111th) — Report of the Secretary, Oct 1 2008 – Mar 31 2009
- Senate Document No. 8 (111th) — Report of the Secretary, Apr 1 – Sep 30 2009
- House Document No. 26 (111th) — Statement of Disbursements, Jan 1 – Mar 31 2009 (parts 1–3)
- House Document No. 56 (111th) — Statement of Disbursements, Apr 1 – Jun 30 2009 (parts 1–3)

Two routes are **confirmed dead** — do not re-probe:

- **house.gov**: SOD archive earliest detected period is 2009Q3; `mentions_2009q1` and
  `mentions_2009q2` both false (`absence_confirmation.json`).
- **Direct govinfo CDOC PDF paths**: both `GPO-CDOC-111sdoc2` and `CDOC-111sdoc2` forms return
  HTTP 200 with `content_type: text/html` at 44,165 bytes — a page, not a PDF
  (`govinfo_endpoint_probe.json`).

Remaining route under test: the govinfo **SERIALSET** collection sitemaps
(`serialset_route.json`, `cdoc_sitemap_discovery.json`, `sitemap_local_parse.json`).

Verification rule for any candidate URL: **HEAD probes on govinfo lie.** Confirm with a ranged
GET — `content_type` must be `application/pdf` AND the body must begin with `%PDF`.

## 4. Date coverage — the gap table

| Chamber | Held | Missing |
|---|---|---|
| House | 2009Q3 – 2026Q1, 67 quarters | 2009Q1, 2009Q2, 2026Q2 (2026Q2 likely just unpublished — verify) |
| Senate | 30 periods | 2009-04, 2009-10, 2010-04, 2010-10 |

## 5. Gordon Holzberg — confirmed covered

43 payroll rows. Alma Adams 2017-05-18 → 2023-02-09 (24 quarters); Emilia Sykes 2023-02-10 →
2024-01-02 (5 quarters). The stints abut to the day. All five declared roles appear as payroll
titles.

The worked example of the standing finding: **employment is a sequence of stints, and the
pipeline counts people.** Holzberg is one person and two stints in two offices.

## 6. Open lanes, not started

Three lanes were briefed and died before producing anything:

1. **Reachable-cap recount** with the committee corpus admitted. Highest priority — every
   downstream coverage number depends on it. Requires a paired negative control: the same match
   run against names not expected on committee payroll. If the control rate approaches the
   treatment rate, the matches are collisions, not discoveries.
2. **Source line consumption audit.** Per source document, measure what fraction of text lines
   the parser turned into an observation, and classify the dropped lines. Critical bucket is
   "looks like a person row but did not match" — dump at least 40 verbatim examples. This tests
   Paul's structural lead: if a second block of people is printed after the initial roster with
   positions beside them, and the row predicate matches only the first block's shape, no amount
   of better name matching will ever reach them.
3. **Filing-text office mining** for the 3,229 unlinked reachable lobbyists who name a member or
   committee in their own filing text. Reuse the declaration-directed matcher and widened-given
   rules A/B/C/D; run the paired control arm per tier; resolve member names by strict bioguide,
   never surname alone.

## 7. Resume instructions

A workflow covering all five lanes (assess → finish → adversarially refute → synthesize) was
authored and stopped before any agent returned, to preserve budget. Resume:

```
Workflow({
  scriptPath: "<session dir>\\workflows\\scripts\\employment-tenure-finish-wf_1bdedbe4-b99.js",
  resumeFromRunId: "wf_1bdedbe4-b99"
})
```

Journal held 5 `started` entries and 0 returns at stop time, so the resume re-runs everything —
nothing was lost, and nothing is cached either.

## 8. Standing constraints for any continuation

- **No git.** Not from the operator, not from any agent, not even read-only inspection.
- **Immutable generations.** Never modify or delete an existing `*_v1_*` / `*_v2_*` / `*_v3_*`
  directory. `SUPERSEDED` directories are retained for the record; read them only to learn what
  defect superseded them, never as input.
- **Nothing canonical.** Promotion counters stay at 0.
- **Measure, do not assert.** Write `NOT MEASURED` rather than estimating.
- **Never loosen a failing check to make it pass.**
- **Reuse reviewed math** rather than reinventing matching rules.

## 9. Owed to Paul

A requested reminder, not yet due: **design the network layering once collection settles.**
Staffers nest underneath and in-between members; the 562 title-declared shared employees (up to
133 offices each) are the "between" layer, single-office staffers nest beneath one member.
Collection has not settled — committee corpus, 2009 backfill, and cap recount are all open — so
this stays pending.
