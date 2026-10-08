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

You should see **23 checks, 0 failed**. If you don't, stop and report — do not start editing.
Run it again after you integrate. It is the same gate both times.

---

## 1. What this is, in one paragraph

Melange Systems ranks all 533 members of Congress on credit-union influence for an advocacy shop.
Separately from that rank, it shows a **Legislative+Press display tier** (1/2/3), and
`moneyball_core.overall_display_tier()` reads `Tier 1 ⇒ Champion`. The problem: Champion was
something you could only earn, never lose, and it was blind to *whom* a member legislates for — so
members who fight for banks or crypto, and members who quietly killed the credit-union asks, showed
up as Champions. This change adds two things to the **display layer only**: a **primacy factor**
(champion *for whom*) and a **net conduct ladder** — a graduated, evidence-cited consequence that
nets a grievance ledger against a delivery ledger, so the system can register both a chair who
refused your asks and a chair who carried your bill across the floor. It touches no pillar, no
weight, and no engine.

**The acceptance test is that ranks do not move.** `ranks_python.json` is read-only. If any rank
changes, the work was wired into the wrong layer.

---

## 2. Read in this order

| # | File | Why |
|---|---|---|
| 1 | **`CONDUCT_LADDER.md`** | The ladder: logic, all four grievance events and the delivery ledger with URLs and quotes, the arithmetic, the drop-in code, and a recorded reversal (§5) worth reading before you touch a multiplier. **Start here after this file.** |
| 2 | **`INTEGRATION.md`** | Compact drop-in guide — files, destinations, build order, failure semantics. |
| 3 | `PRIMACY_IMPLEMENTATION_SPEC_2026-07-28.md` | Full spec. §0 the classifier's 9-level authority ladder and why the multiplicative form is right; §2 what is used; **§3 what was tried and rejected — read this before proposing anything**; §4 the board + math verification; §6.2 the Waters / Cortez Masto / Barr investigations; §7 what is Paul's call, not yours. |
| 4 | **`FLAGS.md`** | Everything known to be weak, unproven, or deferred — 16 numbered items, ordered by what they cost you. **F1 and F2 are blockers.** Read before you tell anyone this is finished. |
| 5 | `primacy_board.html` | The rendered board. Open it in a browser — fastest way to see what the change does. |

---

## 3. Files and where they go

| File | Destination | Notes |
|---|---|---|
| `primacy_factors.py` | `fec/primacy_factors.py` | Producer. Pure, no network, chain-independent. |
| `tier_util_primacy.patch.py` | **fold into** `fec/tier_util.py` | 6 functions + a commented replacement body at the bottom. **Not a drop-in file** — read §4 below. |
| `test_primacy_tier.py` | `fec/tests/` | **34 tests.** Add `'test_primacy_tier'` to the registered-suite tuple at the bottom of `fec/tests/run_tests.py` — the file already prints the `N passed, M failed` line that runner greps for, so no change to `run_tests.py` beyond the name. Self-resolves the consumer, so it runs before *and* after integration. |
| `bill_beneficiary_tags.ndjson` | repo root | 614 acts, each with beneficiary class + authority level + rationale. |
| `grievance_ledger.ndjson` | repo root | 4 grievance events. Ladder input (the negative side). |
| `primacy_factors.json` | repo root (generated) | Committed as the expected producer output — diff against it. |
| `tier_overrides.proposed.json` | replaces `tier_overrides.json` | `placements: []`. **Read its `_README` before editing.** |
| `FIXTURE_expected_board.csv` | `fec/tests/fixtures/` | All 533 rows to 9 dp. Regression target. |
| `beneficiary_review_queue.csv` | working doc | Human adjudication queue, weight-sorted. Not code. |
| `delivery_ledger.ndjson` | repo root | 14 delivery events. Ladder input (the positive side). |
| `verify.py` | stays here | Package self-check. Not part of the repo. |

**Two inputs are NOT in this package** because they are large and live in the repo already:
`member_desk_bundle.json` (~31 MB) and `ranks_python.json` (~230 KB), both in the Melange Systems
root. `verify.py` finds them for you.

---

## 4. Five things that will bite you

These are real hazards found by reading the live `fec/tier_util.py` and its callers. Each one is a
silent breakage, not an error you'd notice. ⑤ is also `FLAGS.md` **F1** — the one that decides
whether this change should land at all.

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
Ceilings now come from the ledgers. If you find a `demotions` array anywhere, it is stale — two
sources of truth already disagreed once about Barr and Hill.

**⑤ Steps 1–4 without step 5 is worse than not shipping.** The code change alone moves Andy Barr
from slot 12 to 37 and shows **no reason anywhere**. A board that silently demotes the subcommittee
chair of jurisdiction, with no cited event and no cure printed, will be dismissed the first time
someone asks why — and they will be right to dismiss it. **The rendered reason is the deliverable;
the re-ranking is just the mechanism.** If you cannot do step 5 in the same change, do not ship
steps 1–4.

---

## 5. Build order

1. Land `tier_overrides.proposed.json`. Safe alone: `load_tier_overrides()` returns `{}` on empty
   placements.
2. Add `fec/primacy_factors.py`; run it; diff its output against the committed
   `primacy_factors.json` — expect **0 mismatches across 533**, baseline `0.502380`.
3. Fold the patch into `fec/tier_util.py`, honoring §4 above.
4. Add `'test_primacy_tier'` to the registered-suite tuple at the bottom of
   `fec/tests/run_tests.py`, plus a fixture test against `FIXTURE_expected_board.csv`.
5. Surface the reason in the desk and dashboard. **This is the actual product:**
   > *"French Hill — Tier 3. Conduct 8.00 (MS-2026-001, MS-2026-004) less delivery 3.00 (moved
   > H.R.975, H.R.4437, H.R.4544) = net 5.00, ceiling Tier 2. Cure: any of H.R.4167 / H.R.7647 /
   > H.R.507 / H.R.1791 attached to or reported through an FSC vehicle under his control."*

   Print the **numbers and both sides**, not just a flag. The number is what makes the ask
   negotiable to a member's staff — Barr clearing MS-2026-002 drops him to 2.00 and off the ladder
   entirely; clearing only MS-2026-003 leaves him at 5.25, still capped at Tier 2. And a staffer
   shown only the grievance half will dispute it, correctly.
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
| **Andy Barr** | 12 | **37** (Tier 3) | Clean on score — a Tier-1 member on the numbers. Net conduct 7.25 (grievance 7.25, delivery **0.00**) is his only disqualifier. |
| **French Hill** | 73 | **73** (Tier 3) | Net 5.00 (grievance 8.00 less delivery 3.00) caps him at Tier 2, but a ceiling never promotes and his own record already put him at 73. |

Roster baseline **0.502380**. Primacy carries **84.2%** of log-score variance in the top 20 and
0.6% across all 532 scorable members — that asymmetry is the design, not a defect: `Leg%` is a
percentile and saturates at the ceiling, so it selects contenders; the primacy factor does not
saturate, so it picks the winner among them.

---

## 7. Configuration — ratified 2026-07-29, do not re-open

Paul ruled on all three open questions. **Each confirms the shipped configuration, so the board is
byte-identical to the one in `FIXTURE_expected_board.csv`.** They are decisions, not defaults —
implement them, do not re-litigate them, and do not tune a constant to move a member.

| Decision | Ruling | Where it lives |
|---|---|---|
| **Tier 1 size** | **12** | `tier_util.BUCKETS = (12, 24, 48)` — already correct |
| **Letter signatory role weight** | **0.50** (`original`) | signatories coded `original` in the bundle; `ROLE_W['original']` |
| **Dan Sullivan (slot 6)** | **Keep** | no override, no ledger event — he holds the seat on his record |

Notes on each, so the reasoning survives:

- **Tier 1 at 12** seats 6 of the 7 named ground-truth members plus Huizenga. 18 would have reached
  7 of 7 by catching Cortez Masto at 17, but 18 is not a neutral widening — it also admits Hagerty,
  Meuser, Sessions, Crapo and Bonamici. Twelve was chosen with that trade-off explicit.
- **Signatory at 0.50** was tested against 0.25. At 0.25 Cortez Masto rises 17 → 16 but Huizenga
  drops 12 → 13, out of Tier 1. **No setting seats Masto at 12 and keeps Huizenga**, so this is a
  preference, not an optimum. 0.50 holds because Huizenga was explicitly reviewed and accepted.
- **Sullivan stays.** He was flagged for removal early and primacy has no grip on him — he is
  genuinely **48.7% CU-primary**, purer than most of Tier 1. Removing him would have required a
  standing rule (committee-of-jurisdiction requirement) or a fabricated ledger event. The system was
  telling the truth and the list was wrong; the list moved.

**What is still not yours:** any change to `leverage_mult` on a ledger event, any change to a
beneficiary classification above the review-queue threshold, and `OPPOSE_W`. Those are Paul's.

**Spec §3 lists everything already built and empirically rejected** — family de-dup, significance
weights, delivery weighting of the score, primacy floors, jurisdiction multipliers, IMP-weighted
`shared`, any leniency toward `shared`, the press pillar, all 8 standing pins. Each has a recorded
failure mode. Read it before proposing a change; the evidence exists so nobody re-litigates.

## 8. Known limitations

**Moved to `FLAGS.md`** — 16 numbered items, ordered by what they cost you, so they can be cited
individually in review. The two that gate this change:

- **F1 — steps 1–4 without step 5 is worse than not shipping.** The code alone moves Andy Barr from
  slot 12 to 37 and shows **no reason anywhere**. The rendered reason is the deliverable; the
  re-ranking is just the mechanism.
- **F2 — "rank delta zero" is a design claim, not yet verified.** `verify.py` confirms
  `ranks_python.json` was never written, which is true and trivial. The real test is patching
  `tier_util` and running `run_pipeline.py`. Do it first, not last.

The rest, in one line each: **F3** ~38% of role weight is title regexes · **F4** the Quorum full
export unblocks three problems at once and is the highest-value input by a wide margin · **F5** the
delivery ledger is a general mechanism built on a sample of one, and understates every chair ·
**F6** both ledgers measure the ledger, not the world · **F7** 559 acts carry no authoritative ACU
position · **F8** the role vocabulary has no `floor_manager` · **F9** five registry anchor bills
were lost at collection · **F10–F16** deferred items: no expiry pass, inherited shrink anchor,
`OPPOSE_W` as a values judgment, decay asymmetry, untested ladder rungs, Maxine Waters being
unreachable by any primacy change, and one row-level classification call.
