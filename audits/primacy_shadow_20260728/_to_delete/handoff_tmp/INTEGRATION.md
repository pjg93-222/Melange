# Primacy tier — integration guide
**2026-07-29 · drop-in package · `audits/primacy_shadow_20260728/ship/`**

Verified: the shipped `primacy_factors.py` reproduces the session board **exactly** — baseline
0.502380, **0 member mismatches across 533**, Tier 1 identical, and `apply_conduct_ladder` reproduces
the final ordering for all 533 rows. **34 kernel tests pass; `verify.py` runs 23 checks.**

---

## What this changes, and what it must not

| | |
|---|---|
| **Changes** | the Legislative+Press **display tier**, and therefore the Champion crown (`overall_display_tier` already reads `Tier 1 ⇒ Champion`) |
| **Does NOT change** | `ranks_python.json`, any pillar, any engine, any ratified weight, `moneyball_core` |
| **Acceptance test** | **rank delta exactly zero.** If any rank moves, it was wired into the wrong layer. |

`tier_util` is already documented as *"Pure: reads ranks_python.json, returns dicts; writes nothing,
touches no engine."* This work stays inside that contract.

---

## Files

| File | Destination | Notes |
|---|---|---|
| `primacy_factors.py` | `fec/primacy_factors.py` | producer; pure, no network, chain-independent |
| `tier_util_primacy.patch.py` | fold into `fec/tier_util.py` | 6 functions + a replacement body (commented at the bottom) |
| `test_primacy_tier.py` | `fec/tests/` | **34 tests**; add to `run_tests.py` |
| `CONDUCT_LADDER.md` | docs | standalone logic + evidence + code for the ladder — **read this first** |
| `bill_beneficiary_tags.ndjson` | repo root | 614 acts, each with class + authority + rationale |
| `grievance_ledger.ndjson` | repo root | conduct ladder input — MS-2026-001/002/003/004 |
| `delivery_ledger.ndjson` | repo root | the positive mirror — institutional effort spent, priced by beneficiary class |
| `tier_overrides.proposed.json` | replaces `tier_overrides.json` | `placements: []` — all 8 pins retired |
| `primacy_factors.json` | generated | committed as the current expected output |
| `FIXTURE_expected_board.csv` | `fec/tests/fixtures/` | all 533 rows to 9 dp — regression target |
| `beneficiary_review_queue.csv` | working doc | Paul's adjudication queue, weight-sorted |

---

## Constants (all ratified in the spec)

```python
ROLE_W = {'sponsor': 1.0, 'original': 0.5, 'cosponsor': 0.25}   # unknown -> 0.25
ACT_W  = {'cu_primary': 1.00, 'shared': 0.50,
          'bank_primary': 0.15, 'crypto_primary': 0.15, 'fintech': 0.15,
          'offtopic': 0.00, 'oppose': -1.00}
LETTER_W      = 0.60     # env PRIMACY_LETTER_W  — ACU advocacy letters, calibrated
SHRINK_ANCHOR = 15.0     # env PRIMACY_SHRINK
ROSTER_BASELINE = 0.502380   # recomputed every run; this is the current value
TIER_WEIGHTS  = {'legislation': 1.00, 'press': 0.00}
BUCKETS       = (12, 36, 84)
CONDUCT_LADDER = ((9.0, 0), (6.0, 3), (3.0, 2))   # (effective_severity, tier ceiling); 0 == untiered
```

```
factor_raw    = Σ role_w · act_w  /  Σ role_w            (no acts -> 1.0)
baseline      = Σ(factor_raw · credit) / Σ credit         (credit-weighted roster mean)
λ             = min(1, agenda_credit / 15)
factor_shrunk = baseline + λ · (factor_raw − baseline)
score         = Leg% · factor_shrunk                      (press weight 0.00)
```

```
effective_severity = Σ severity × leverage_mult   over OPEN ledger events
tier_ceiling       = 2 at eff>=3 · 3 at eff>=6 · untiered at eff>=9 · else unconstrained
```

Sort desc, member name asc as tie-break. **The ceiling is a floor on slot index, not a fixed
demotion** — a capped member re-enters at their own score position among the remainder, so the
ladder can only push a capped member down and only pull an uncapped member up. It is a permutation;
nobody is dropped. The ladder reads a **net**: `net = effective_severity − delivered_credit`, where
delivery is `Σ act_weight × instrument_mult` over `delivery_ledger.ndjson` (reported_out 1.00 ·
floor_managed 0.75 · markup 0.25), priced by the moved bill's beneficiary class so a gavel earns
nothing by itself. Current: **Barr net 7.25 → Tier 3 (slot 12 → 37)**, **Hill net 5.00 → Tier 2
ceiling, slot 73 (unmoved — a ceiling never promotes)**. Full evidence in `CONDUCT_LADDER.md`.

---

## Build order

1. **Land `tier_overrides.proposed.json`** first — safe on its own. `load_tier_overrides()` returns `{}` on empty placements and ignores the unknown `demotions` key.
2. **Add `primacy_factors.py`**; run it; diff the output against the committed `primacy_factors.json` — expect byte-identical.
3. **Patch `tier_util.py`** per the commented block. Note the third return value (`detail`) is NEW; keep a 2-tuple shim for one release so `build_dashboard_bundle` / `make_member_desk` don't break.
4. **Add the tests**, plus a fixture test asserting the top-12 against `FIXTURE_expected_board.csv`.
5. **Surface the reason** in the desk/dashboard — *"French Hill — Tier 3. Conduct 8.00 (MS-2026-001, MS-2026-004) less delivery 3.00 (moved H.R.975, H.R.4437, H.R.4544) = net 5.00. Cure: any of H.R.4167 / H.R.7647 / H.R.507 / H.R.1791 attached to or reported through an FSC vehicle under his control."* — show BOTH sides; a member's staff reading only the grievance half will dispute it, and be right to. That sentence is the product. Print the effective severity, not just the flag — it is what makes the cure legible to a member's staff.
6. **Chain wiring**: `primacy_factors.py` runs after `make_member_desk` (it consumes the bundle) and before the dashboard/desk build.

**Verification:** kernel tests → `run_pipeline.py` → **rank delta exactly zero** → `audit_full.py` clean.

---

## Failure semantics (deliberate, mirrors `moneyball_core`'s bill-corroboration sentinel)

- `primacy_factors.json` **missing** → fail open: every member gets factor 1.0, tier degrades to pure Leg%. Never a silent zero.
- `primacy_factors.json` **present but malformed** → **raise.** Corrupt evidence is never treated as absent.
- `grievance_ledger.ndjson` missing → no gating; `apply_conduct_ladder` returns the identity.
- `delivery_ledger.ndjson` missing → no offsets; the ladder reads gross severity, as before.
- Delivery row with 0.00 credit (out-of-universe bill) → skipped, never creates a member record.
- Ledger event with no `leverage_mult` → defaults to **1.0** (neutral), so it still counts at face severity rather than vanishing.
- Ledger event with `status != 'open'` → excluded from the sum.
- Act in the bundle but **not** in the tag file → **raise.** Universe and classification must stay in sync.
- Member absent from `factors` → neutral 1.0, never zeroed.
- Unknown beneficiary class → **raise.**

---

## Two audits to add to `audit_full.py`

1. **Registry-vs-collected reconciliation.** `acu_legislation_search_registry.json` is a *declared expectation*: every anchor bill absent from `member_desk_bundle.json` is a defect. Five are currently missing (S.427 / H.R.3380 TAILOR, S.3940 AFFORD, S.1880 CDFI Bond Guarantee, H.R.1 — the last tagged **Credit Union Tax Status**). Present in neither the bundle nor any workbook role sheet, so the loss is at **collection**, not scoring. This audit means it never again takes a lucky document upload to notice.
2. **Tag-universe closure.** Assert `set(bundle acts) == set(tag file acts)`.

---

## Open items for Paul (none block the build)

1. **Review queue** — everything below confidence 0.85, weight-sorted. The L7 title-rule mass (~38% of role weight) is the largest remaining soft spot; the right instrument is Quorum's full export with its AI summaries.
2. **H.R.7056 Community Bank Regulatory Tailoring Act** sits at `cu_primary` — the outline files it under Exam & Supervision (CU-scoped) and ACU supports it, but the title argues `shared`. One row, Paul's call.
3. **The five collection-dropped bills** (item 1 above).
4. **Whether `fetch_acu_letters.py`'s full snapshot holds more than the 7 letters** the bundle carries.
5. **Tier 1 size.** 12 gives 6/7 of the named members + Huizenga; 18 gives 7/7 (Cortez Masto at 17). `BUCKETS` is one constant.
6. **`OPPOSE_W = −1.0`** is symmetric with `cu_primary = +1.0` — defensible, but a values judgment rather than a derived constant.
7. **Role vocabulary has no `floor_manager`.** `sponsor`/`original`/`cosponsor` is the whole set, so Hill appears nowhere among H.R.975's 23 credited members despite carrying it across the floor. Delivery is deliberately outside the primacy factor, but the desk should show it beside the factor.
8. **Letter signatory role weight**: shipped at `original` 0.50; `cosponsor` 0.25 is arguably more principled. Tested — 0.25 moves Masto 17→16 but drops Huizenga 12→13. One line, Paul's call.
9. **Nothing expires yet.** `decay_years` is recorded on every ledger event and read by nothing. Add an expiry pass before the first event's clock matters (MS-2026-003 is a 2-year clock from 2026-07-22).
