# START HERE

**Moneyball / Melange Systems — primacy tier + conduct ladder · handoff package · 2026-07-29**

You are being handed a **finished, verified change** to land in an existing Python repo. Nothing
here is exploratory. The board has been computed, every constant has a recorded reason, and the
whole package reproduces itself byte-for-byte from the repo's own inputs.

**Do this first:**

```bash
python3 verify.py                       # auto-locates the repo
python3 verify.py "/path/to/Melange Systems"     # or point it explicitly
```

You should see **20 checks, 0 failed**. If you don't, stop and report — do not start editing.
Run it again after you integrate. It is the same gate both times.

---

## 1. What this is, in one paragraph

Melange Systems ranks all 533 members of Congress on credit-union influence for an advocacy shop.
Separately from that rank, it shows a **Legislative+Press display tier** (1/2/3), and
`moneyball_core.overall_display_tier()` reads `Tier 1 ⇒ Champion`. The problem: Champion was
something you could only earn, never lose, and it was blind to *whom* a member legislates for — so
members who fight for banks or crypto, and members who quietly killed the credit-union asks, showed
up as Champions. This change adds two things to the **display layer only**: a **primacy factor**
(champion *for whom*) and a **conduct ladder** (a graduated, evidence-cited consequence). It touches
no pillar, no weight, and no engine.

**The acceptance test is that ranks do not move.** `ranks_python.json` is read-only. If any rank
changes, the work was wired into the wrong layer.

---

## 2. Read in this order

| # | File | Why |
|---|---|---|
| 1 | **`CONDUCT_LADDER.md`** | The ladder: logic, the four ledger events with URLs and quotes, the arithmetic, the drop-in code, and the one open judgment call. **Start here after this file.** |
| 2 | **`INTEGRATION.md`** | Compact drop-in guide — files, destinations, build order, failure semantics. |
| 3 | `PRIMACY_IMPLEMENTATION_SPEC_2026-07-28.md` | Full spec. §0 the classifier's 9-level authority ladder and why the multiplicative form is right; §2 what is used; **§3 what was tried and rejected — read this before proposing anything**; §4 the board + math verification; §6.2 the Waters / Cortez Masto / Barr investigations; §7 what is Paul's call, not yours. |
| 4 | `primacy_board.html` | The rendered board. Open it in a browser — fastest way to see what the change does. |

---

## 3. Files and where they go

| File | Destination | Notes |
|---|---|---|
| `primacy_factors.py` | `fec/primacy_factors.py` | Producer. Pure, no network, chain-independent. |
| `tier_util_primacy.patch.py` | **fold into** `fec/tier_util.py` | 6 functions + a commented replacement body at the bottom. **Not a drop-in file** — read §4 below. |
| `test_primacy_tier.py` | `fec/tests/` | 28 tests. Register in `fec/tests/run_tests.py`. Self-resolves the consumer, so it runs before *and* after integration. |
| `bill_beneficiary_tags.ndjson` | repo root | 614 acts, each with beneficiary class + authority level + rationale. |
| `grievance_ledger.ndjson` | repo root | 4 conduct events. Ladder input. |
| `primacy_factors.json` | repo root (generated) | Committed as the expected producer output — diff against it. |
| `tier_overrides.proposed.json` | replaces `tier_overrides.json` | `placements: []`. **Read its `_README` before editing.** |
| `FIXTURE_expected_board.csv` | `fec/tests/fixtures/` | All 533 rows to 9 dp. Regression target. |
| `beneficiary_review_queue.csv` | working doc | Human adjudication queue, weight-sorted. Not code. |
| `verify.py` | stays here | Package self-check. Not part of the repo. |

**Two inputs are NOT in this package** because they are large and live in the repo already:
`member_desk_bundle.json` (~31 MB) and `ranks_python.json` (~230 KB), both in the Melange Systems
root. `verify.py` finds them for you.

---

## 4. Four things that will bite you

These are real hazards found by reading the live `fec/tier_util.py` and its callers. Each one is a
silent breakage, not an error you'd notice.

**① `BUCKETS` is a name collision.** `tier_util.py:18` already defines `BUCKETS = (12, 24, 48)` as
tier **sizes**, and `apply_tier_overrides(order, overrides, buckets=BUCKETS)` consumes it that way.
The patch file defines the same name with the same value *only so it runs standalone* — **delete
that line when you fold it in.** Never redefine it as `(12, 36, 84)` (the cumulative form) or
`apply_tier_overrides` will silently start Tier 2 at slot 37.

**② `legislative_press_tiers()` must keep returning a 2-tuple.** Seven call sites unpack two
values: `audit_full.py:57`, `make_member_desk.py:1542`, `money_response.py:15`,
`outcome_snapshot.py:33`, `sync_stance_g.py:20`, `tests/test_audit_completion_20260716.py:120`, and
`build_dashboard_bundle.py:67` (import). The replacement body therefore returns the conduct detail
**only** when a caller passes `with_detail=True`. Returning a bare 3-tuple breaks all seven.

**③ Do not set the tier weights to 1.00 / 0.00.** The policy *is* legislation-only, but that lives
in code — the patched function computes `Leg% × factor` and never calls `load_tier_weights()`.
`load_tier_weights()` **raises** on any non-positive weight, and
`tests/test_audit_completion_20260716.py:96` asserts against the stored values. Leave 0.84 / 0.16
alone.

**④ The 2026-07-28 draft's `demotions[]` block is gone from the overrides file, on purpose.**
Ceilings now come from the ledger. If you find a `demotions` array anywhere, it is stale — two
sources of truth already disagreed once about Barr and Hill.

---

## 5. Build order

1. Land `tier_overrides.proposed.json`. Safe alone: `load_tier_overrides()` returns `{}` on empty
   placements.
2. Add `fec/primacy_factors.py`; run it; diff its output against the committed
   `primacy_factors.json` — expect **0 mismatches across 533**, baseline `0.502380`.
3. Fold the patch into `fec/tier_util.py`, honoring §4 above.
4. Add the tests to `fec/tests/run_tests.py` plus a fixture test against
   `FIXTURE_expected_board.csv`.
5. Surface the reason in the desk and dashboard. **This is the actual product:**
   > *"French Hill — untiered. Open conduct events MS-2026-001, MS-2026-004; effective severity
   > 10.00. Cure: any of H.R.4167 / H.R.7647 / H.R.507 / H.R.1791 attached to or reported through an
   > FSC vehicle under his control."*

   Print the **number**, not just the flag — it is what makes the ask negotiable to a member's
   staff. Barr clearing MS-2026-002 drops him to 2.00 and off the ladder entirely; clearing only
   MS-2026-003 leaves him at 5.25, still capped at Tier 2.
6. Chain wiring: `primacy_factors.py` runs **after** `make_member_desk` (it consumes the bundle) and
   **before** the dashboard/desk build.

**Gate:** `python3 verify.py` → kernel tests → `run_pipeline.py` → **rank delta exactly zero** →
`audit_full.py` clean.

---

## 6. The result you should reproduce

**Tier 1 (Champions):** Padilla · Gonzalez · Fitzpatrick · Cramer · Timmons · Sullivan ·
Fitzgerald · Vargas · Tim Scott · Young Kim · Sherman · Huizenga
**13–18:** Hagerty · Meuser · Sessions · Crapo · Cortez Masto · Bonamici

| Member | Score order | Final slot | Why |
|---|---|---|---|
| **Andy Barr** | 12 | **37** (Tier 3) | Clean on score — a Tier-1 member on the numbers. Effective severity 7.25 is his only disqualifier. |
| **French Hill** | 73 | **85** (untiered) | Fails the primacy axis on his own record *and* carries 10.00. |

Roster baseline **0.502380**. Primacy carries **84.2%** of log-score variance in the top 20 and
0.6% across all 532 scorable members — that asymmetry is the design, not a defect: `Leg%` is a
percentile and saturates at the ceiling, so it selects contenders; the primacy factor does not
saturate, so it picks the winner among them.

---

## 7. What is NOT yours to decide

Two open items belong to Paul (the owner). Implement whatever he has ruled; do not pick for him,
and do not tune constants to move a member.

1. **Letter signatory role weight** — shipped at `original` = 0.50; `cosponsor` = 0.25 is arguably
   more principled. At 0.25, Cortez Masto moves 17→16 but Huizenga drops 12→13 out of Tier 1. No
   setting achieves both.
2. **Tier 1 size, 12 or 18** — 12 hits 6 of 7 named members plus Huizenga; 18 hits 7 of 7 but also
   admits Hagerty, Meuser, Sessions, Crapo and Bonamici.

Also his: `leverage_mult` on MS-2026-004 (2.0 as shipped → Hill untiered; 1.0 → Hill at slot 73;
see `CONDUCT_LADDER.md` §5), and whether Dan Sullivan at slot 6 stays — primacy has no grip on him,
he is genuinely 48.7% CU-primary, so removing him needs a standing rule or a ledger event.

**Spec §3 lists everything already built and empirically rejected** — family de-dup, significance
weights, delivery weighting, primacy floors, jurisdiction multipliers, IMP-weighted `shared`, any
leniency toward `shared`, the press pillar, all 8 standing pins. Each has a recorded failure mode.
Read it before proposing a change; the evidence exists so nobody re-litigates.

---

## 8. Known limitations — do not present these as solved

- **The ladder sums *logged* events, so it measures the ledger, not the world.** Before the fourth
  event was found, Barr (7.25) out-scored Hill (6.00) — the arithmetic called Barr the worse actor
  when Hill was the chair *and* the author of the vehicle. That was pure coverage. The mitigation is
  procedural: for every vehicle in the ledger, sweep every member with leverage over it. Asserted in
  `test_ladder_counts_events_so_completeness_matters` so it stays explicit.
- **~38% of role weight rests on L7 title-rule classification.** The right instrument is Quorum's
  full export with its AI summaries. That single export also unblocks Cortez Masto's two FHLB bills
  (their bundle summaries are 51 and 47 characters — title only) and the 559 acts carrying no
  authoritative ACU position.
- **Five registry anchor bills are missing from the bundle** (S.427 / H.R.3380 TAILOR, S.3940
  AFFORD, S.1880 CDFI Bond Guarantee, H.R.1). They are in neither the bundle nor any workbook role
  sheet, so the loss is at **collection**, not scoring. `INTEGRATION.md` proposes a
  registry-vs-collected reconciliation audit so it never again takes a lucky document upload to
  notice.
- **Nothing expires yet.** `decay_years` is on every ledger event and read by nothing. MS-2026-003
  and MS-2026-004 are 2-year clocks from July 2026.
- **Maxine Waters cannot be seated by any primacy change.** Her factor is +0.5922, *above* baseline
  — she passes the axis. Her constraint is `Leg% = 0.641` (22 sponsor, 2 original, 7 cosponsor),
  which is upstream and would move rank. If the answer is that leading the CDFI letter should count
  like authorship, the lever is `LETTER_W` or the Leg pillar's role weights, not primacy.
