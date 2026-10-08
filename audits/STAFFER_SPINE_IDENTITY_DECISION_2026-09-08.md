# Staffer spine — identity findings and the ruling you need to make

**Date:** 2026-09-08
**Artifact audited:** `audits/staffer_network/hill_personnel_spine_20260907_v7_primary` (144,690 people, 204,697 office spans, verifier 46/46 PASS, twin byte-identical)
**Full evidence:** `audits/STAFFER_SPINE_IDENTITY_AUDIT_2026-09-08.md`
**Status:** nothing changed. This document asks for one decision.

---

## The one-line finding

The spine does not fuse people who are different. It splits people who are the same — **26% of it** — and the reason is a single inconsistency in how missing Senate dates are read.

---

## What is working

| Test | Result |
|---|---|
| Over-merges of the D-020 kind (two people fused into one) | **0** |
| Flag-rule TRUE_COLLISION names held as 2+ ids (correctly kept apart) | **34 of 34** |
| House same-quarter two-office overlap without a shared-employee title | **0** |
| Senate people holding two offices in one report period | **0** |

The House rule — a name is an identity only within an office, and day-level service dates are the discriminator — is doing its job exactly as ruled.

---

## What is broken

**37,684 spine ids (26.05%) sit on a name key shared with at least one other id.** 37,001 of them are in the same shape: overlapping service, different offices, no link.

| Person | Held as | Evidence they are one person |
|---|---|---|
| Jamie Wallner | **30 ids** | 34 spans, every one titled `EXECUTIVE DIRECTOR FROM SEP. 1` / `TO JUL. 15`, across 30+ senator offices |
| Wendy Baig | **32 ids** (two keys) | An office header is glued into the surname: `SENATE STEERING COMMITTEEBAIG, WENDY F` vs `BAIG, WENDY F` |
| Clinton Brown | **30 ids** | same glued-header pattern |
| Rachel Bovard | **21 ids** | all spans `POLICY ADVISOR FROM MAR. 24` |

Seventeen of the twenty worst cases are the same Senate shape: one staffer paid by many member offices at once, which the Senate never labels as shared.

---

## Why — the asymmetry

Senate reports print no day-level dates. **72,237 of 72,237** Senate spans carry `date_precision = REPORT_PERIOD`.

That single absence is currently read **two opposite ways**:

| Where | How "no day dates" is read | Cases affected |
|---|---|---|
| Merge guard | **Permission to merge** — 2 of the 3 applied merges have basis `same_period_variant_no_day_dates`: same office, same period, distinct payee lines, no evidence | **3** |
| Cross-office link rule | **Bar to linking** — no day dates means no proof of concurrency, so no link | **17,127 ids** |

Permissive where it merges three people on no evidence; restrictive where it splits seventeen thousand.

---

## The ruling I am asking for

### Option A — the recommended fix (re-keys the spine; this is a v8)

Give the Senate a date-free evidence route, and apply it **in both directions**:

1. **Link** two office nodes on one name key when, in the same report period, they print the **identical title string including its date annotation** (`EXECUTIVE DIRECTOR FROM SEP. 1`). That string is verbatim source text already carried in `spans.titles`. It is the Senate's functional equivalent of the House's printed `SHARED EMPLOYEE` title.
2. **Stop merging** on the absence of day dates — the 2 unevidenced merges return to blocked.

Reaches 7,643 Senate-only groups (17,127 ids) and 4,960 cross-chamber groups (13,107 ids). Does not touch the House rule.

**Cost:** new generation v8 — primary, twin, verifier ≈ 55 min, ~3 GB, plus an id map and repointing the surfaces that consume the spine.

### Option B — cheap and bounded (still re-keys, but small)

Only the two mechanical repairs, no rule change:

- Strip **leading** office headers from surnames, exactly as the rule already strips trailing annotations — 32 keys / 58 ids. Baig 32 → 17, Wallner 31 → 30, Brown 30 → 17.
- Add `DE LOS` / `DE LAS` to the particle table — 5 rows, 2 already colliding (`DE LOS REYES VANESSA M.` has its surname truncated to `DE LOS` with the given name pushed into the middle slot).

### Option C — do nothing yet

The spine stays as it is. Every consumer keeps the rule that already holds: **`name_key` is not a person identifier and must never be joined on alone.** The only person-grade key is `spine_person_id`; the only safe name join is `(name_key, chamber, office_key)` inside a period window.

---

## Corrections to numbers I had been repeating

| I said | Actually |
|---|---|
| Class census SHARED_EMPLOYEE 7,605 / SEQUENTIAL_ONLY 3,934 / MID_QUARTER_MOVE 161 / TRUE_COLLISION 23 | Those are a **negative control** (`negative_control_if_flag_were_used`), not measured classes |
| Those numbers describe the spine's input | They were computed on **ledger v1** (60,143 keys, 2016Q1–); the spine consumes **v5** (81,826 keys, 2009Q3–) |
| Measured classes on v5, printed-title rule | SINGLE_OFFICE 64,204 · SEQUENTIAL_ONLY 6,593 · SHARED_EMPLOYEE 782 · MID_QUARTER_MOVE 7,028 · TRUE_COLLISION 3,219 |
| Name-only join degradation, v7 | **16,151 keys / 37,684 people** (v6: 15,828 / 36,863) — measured two independent ways; the 16,077 / 37,474 figure was wrong |

Any document quoting the v1 census against a v7 artifact is comparing two different populations.

---

## Smaller items found, not fixed

- **`collision_ordinal` carries no information** on this generation — all 144,690 rows are `1`, because 0 merges were blocked. A consequence of the guard narrowing above, not an absence of candidates.
- **57 rows carry two distinct observed suffixes**, of which **51 are a column-shift artefact** (`ALLEN R III` printed as `ALLEN RI II`). Only 6 are genuinely two suffixes on one id (JR+SR, III+JR, III+IV). Suffix is not part of `name_key`, so it never separates anyone — those 6 are the real generational-collapse candidates.
- **Two field names mean different things.** `payee_key.middle_initial` is the legacy tokenizer and shows **182** people with middle initial V; the `name_key` middle slot is the new standard and shows **1,311**. A consumer reading the wrong one is off by 7×. A random 10-of-1,311 spot-check of the V reading was **10/10 correct**.
- **17 of the 25 delta residuals are a phantom V** from raw-selection ambiguity — the build is right and the reconstruction was wrong. 2 are real defects (the `DE LOS` truncation above).

---

## Recommendation

**Option A, with B folded into it.** The asymmetry is the only genuinely unsound thing in the spine, it is fixable with source text already on disk, and leaving it means shipping a network in which one Senate staffer appears as thirty separate people. B alone repairs the cosmetic half and leaves the structural half in place.

If the answer is A, one further ruling is needed before building: should a title-string match link across **chambers** as well (4,960 groups / 13,107 ids), or Senate-only for now?
