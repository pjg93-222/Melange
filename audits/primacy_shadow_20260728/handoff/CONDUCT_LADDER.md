# The conduct ladder — logic, evidence, and integration

**2026-07-29 · Melange Systems · `audits/primacy_shadow_20260728/ship/`**
Companion to `PRIMACY_IMPLEMENTATION_SPEC_2026-07-28.md` (§2.4) and `INTEGRATION.md`.
This file is the standalone account: why the mechanism exists, what it computes, what the
evidence is, and exactly what a coder has to do.

---

## 1. The question that produced it

*"Why the fuck is French Hill in Tier 3?"*

**Because until this change, the ledger wasn't what put him there — his own score was.** Hill's
score order is 73 of 533. Tier 3 is slots 37–84. With an empty ledger, no gate, no ladder, no
grievance layer at all, French Hill lands at slot 73. The conduct rule was capping him at a
ceiling he was already sitting under. It was doing nothing.

And the reason his score is that high is worth stating plainly, because it is the real finding:

| | |
|---|---|
| **Leg% 0.9342** | He is in the **93rd percentile** on legislative volume — 35 acts, 10 of them sponsorships. The Leg pillar loves him. |
| **Primacy factor 0.4732** | Against a 0.5024 baseline. Of 20.50 agenda credit: **1.0 CU-primary**, 16.5 shared, 1.0 bank-primary, 1.5 crypto-primary, 0.5 fintech. |
| **Product 0.442** | 93rd percentile × a below-baseline factor still clears slot 73 of 533. |

Primacy already cut him from roughly 7th to 73rd. That is the axis working. It just could not
finish the job, because a member can be *this* prolific and still not fall out of 533 on a
multiplier bounded below by zero.

His two authored bills of the 119th say the rest out loud:

```
1.00 sponsor  H.R.6955|119  bank_primary    Main Street Act
1.00 sponsor  H.R.3633|119  crypto_primary  Digital Asset Market Clarity Act
```

---

## 2. What was wrong with the old rule

The 2026-07-28 draft read one field and emitted one verdict:

```python
if int(ev.get('severity', 0)) >= 3 and ev.get('status') == 'open':   # ineligible for Tier 1
```

But **the ledger schema already carried `leverage_mult` on every event** — collected, and thrown
away. Three consequences:

1. **Barr and Hill drew the identical penalty** though their leverage differs by design (Hill 2.0
   as full-committee chair *and* vehicle sponsor; Barr 1.75 as subcommittee chair of jurisdiction
   and original cosponsor). The ledger recorded the difference; the code erased it.
2. **Severity-2 events cost exactly nothing**, so they could accumulate without bound. Barr's
   credit-appropriation release was worth zero.
3. **There was no consequence above "not a Champion."** The worst actor in the file and a
   marginal one landed in the same place.

---

## 3. The mechanism

```
effective_severity(member) = Σ  severity × leverage_mult      over OPEN, unexpired events

    eff ≥ 3   →   tier ceiling 2      (cannot be a Champion)
    eff ≥ 6   →   tier ceiling 3
    eff ≥ 9   →   untiered
```

**A ceiling is a floor on slot index, not a fixed demotion.** The member is barred from every slot
above their ceiling's first slot, then re-enters at their own score position among the remainder.
Placement is greedy and stable: walk the slots in order, take the best-scoring unplaced member
permitted in that slot.

Three properties follow, and all three are asserted in the test suite:

- **It is a permutation.** Nobody is dropped; `sorted(final) == sorted(order)`.
- **It never promotes a capped member.** `final.index(m) >= order.index(m)` for every capped `m`.
- **It never demotes an uncapped one.** A capped member's seat is released, never taken.

This is why Hill at 6.00 did not move: capped at Tier 3, already at 73, nothing to do. It is a
consequence of the design, not a bug — and it is exactly what exposed that his ledger was
incomplete rather than his conduct mild.

---

## 4. The ledger of record

### MS-2026-001 · French Hill · refusal on a vehicle he controlled — 3 × 2.00 = **6.00**

Full committee chair **and** sponsor of H.R.6955. All four ACU asks (H.R.4167 loan maturities,
H.R.7647 FHLB community-FI definition, H.R.507 veterans MBL exemption, H.R.1791 MBL threshold)
excluded. Passed 270-155-1 on 2026-07-22 without any of them.
> *"several provisions only address concerns for banks while not tackling top issues for credit unions"*
> — [America's Credit Unions](https://www.americascreditunions.org/news-media/news/house-clears-main-street-capital-access-act)

**Cure:** any of the four attached to or reported through an FSC vehicle under his control.

### MS-2026-004 · French Hill · credit appropriation — 2 × 2.00 = **4.00** *(new, 2026-07-29)*

The Financial Services Committee's own release on the bill, issued under his gavel:
> *"House Republicans are modernizing outdated regulations that have placed costly and unnecessary
> burdens on community banks **and credit unions**"*
> — [House Financial Services Committee, 2026-07-21](https://financialservices.house.gov/news/documentsingle.aspx?DocumentID=411204)

The committee of jurisdiction claimed credit-union benefit on the same vehicle from which all four
credit-union asks had been stripped. **No credit union organization is quoted or listed as
endorsing** — the only voices are Hill, Barr, Johnson, Scalise, Emmer, McClain, Huizenga, Meuser
and Loudermilk. ACU's account of the identical bill, one day later, is the direct contradiction
quoted above.

**Corroboration, recorded but NOT scored as a separate event:** [Hill's personal
release](https://hill.house.gov/news/documentsingle.aspx?DocumentID=10266) on the same bill
mentions credit unions **zero times** — *"it's our local banks that step up,"* opening *"As a former
community banker."* That is not misconduct; he claimed nothing he failed to deliver. It is logged
because it confirms the `bank_primary` classification of H.R.6955 **from the sponsor's own mouth**.

**Hill total: 10.00 → untiered → slot 73 becomes slot 85, off the board.**

### MS-2026-002 · Andy Barr · refusal on a vehicle he controlled — 3 × 1.75 = **5.25**

Subcommittee chair of jurisdiction (Financial Institutions), original cosponsor of the vehicle.
Same four exclusions. **Cure:** H.R.4167 reported out of his subcommittee.

### MS-2026-003 · Andy Barr · credit appropriation — 2 × 1.00 = **2.00**

His [own release](https://barr.house.gov/2026/7/barr-leads-house-passage-of-main-street-capital-access-act-to-strengthen-community-banks-and-expand-opportunity)
claims the bill helps *"community banks and credit unions … better compete"* while quoting the
Kentucky Bankers Association and Commerce Lexington and **no credit union organization**.

**Barr total: 7.25 → Tier 3 → slot 12 becomes slot 37.**

---

## 5. The one judgment call in the above

**MS-2026-004 is priced at `leverage_mult = 2.0`; Barr's structurally identical MS-2026-003 is
priced at 1.0.** The distinction is real and it is the reason `leverage_mult` exists: Barr's is a
personal press release, one member's spin. Hill's is **the Financial Services Committee's official
institutional account of the bill**, issued under his own gavel, in the committee's voice. He is
answerable for it in a way Barr is not for his own.

**But state the fork honestly:**

| MS-2026-004 multiplier | Hill effective severity | Ceiling | Slot |
|---|---|---|---|
| **2.0 (shipped)** | **10.00** | **untiered** | **85 — off the board** |
| 1.0 (parity with Barr) | 8.00 | Tier 3 | 73 |

If you think a chair's committee release is just a press release, set it to 1.0 and Hill is back at
73. One field in one NDJSON line. It is recorded in the event as `_multiplier_note` so nobody has
to reconstruct this reasoning later.

---

## 6. A documented limitation — read this before adding events

**Effective severity is a sum over *logged* events, so the ladder measures the ledger, not the
world.** Before MS-2026-004 was found, Barr (7.25) out-scored Hill (6.00) — the arithmetic said
Barr was the worse actor, when Hill was the chair *and* the author of the vehicle. That inversion
was purely an artifact of Barr having two events written down and Hill one.

**The mitigation is procedural, not code.** For every vehicle logged in the ledger, sweep *every*
member with leverage over it — chair, ranking member, subcommittee chair, sponsor, original
cosponsors — and record what each of them said and did. A partial sweep produces a ranking of
whoever happened to get researched hardest.

The property is asserted in `test_ladder_counts_events_so_completeness_matters` so it stays
explicit rather than becoming a surprise.

---

## 7. Code — what a developer actually does

### 7.1 New functions in `fec/tier_util.py`

From `tier_util_primacy.patch.py`, drop in verbatim:

| Function | Contract |
|---|---|
| `load_primacy_factors(root)` | `{member: factor_shrunk}`. Missing → `{}` (**fail open**, tier degrades to pure Leg%). Malformed → **raise**. |
| `load_open_breaches(root)` | `{member: {'effective_severity': float, 'events': [(id, sev, mult)]}}`. Missing → `{}`. Missing `leverage_mult` → **1.0**, never 0. `status != 'open'` → excluded. |
| `tier_ceiling(eff)` | Best tier permitted. `1` unconstrained, `0` untiered. Monotone. |
| `apply_conduct_ladder(order, breaches)` | `(final_order, detail)`. Greedy, stable, permutation-preserving. |
| `primacy_scores(pcts, factors)` | `Leg% × factor`. Member absent from `factors` → neutral `1.0`, never zeroed. |

Module constants: `CONDUCT_LADDER = ((9.0, 0), (6.0, 3), (3.0, 2))`, `BUCKETS = (12, 36, 84)`.

### 7.2 Replacement body for `legislative_press_tiers()`

```python
root = root or _ROOT
with open(os.path.join(root, 'ranks_python.json'), encoding='utf-8') as handle:
    rp = json.load(handle)
pcts = rp.get('pcts', {})

factors  = load_primacy_factors(root)          # {} -> fail open to pure Leg%
breaches = load_open_breaches(root)
all_scores = primacy_scores(pcts, factors)

rankable    = [m for m in members if m in all_scores]
score_order = sorted(rankable, key=lambda m: (-all_scores[m], m))    # deterministic tie-break
order       = apply_tier_overrides(score_order, load_tier_overrides(),
                                   positions=load_tier_positions())

final, detail = apply_conduct_ladder(order, breaches)

b1, b2, b3 = BUCKETS
tier, tierrank = {}, {}
for i, m in enumerate(final):
    tierrank[m] = i + 1
    tier[m] = 1 if i < b1 else 2 if i < b2 else 3 if i < b3 else 0
return tier, tierrank, detail       # third value is NEW — keep a 2-tuple shim for one release
```

Nothing else changes. `moneyball_core.overall_display_tier()` already reads
`if legislative_press_tier == 1: return 'Champion'`, so gating the tier gates the crown for free.
**`ranks_python.json` is read-only. Zero rank delta is the acceptance test.**

### 7.3 Order of operations

1. Land `tier_overrides.proposed.json` (`placements: []`). Safe alone — `load_tier_overrides()`
   returns `{}` on empty placements and ignores the unknown `demotions` key.
2. Add `fec/primacy_factors.py`; run it; diff against the committed `primacy_factors.json` —
   expect **0 mismatches across 533**, baseline `0.502380`.
3. Fold the patch into `fec/tier_util.py`.
4. Add `test_primacy_tier.py` (**27 tests**) to `fec/tests/run_tests.py`, plus a fixture test
   against `FIXTURE_expected_board.csv` (all 533 rows, 9 dp).
5. Surface the reason in the desk and dashboard. **This sentence is the product:**
   > *"French Hill — untiered. Open conduct events MS-2026-001, MS-2026-004; effective severity
   > 10.00. Cure: any of H.R.4167 / H.R.7647 / H.R.507 / H.R.1791 attached to or reported through
   > an FSC vehicle under his control."*

   Print the **number**, not just the flag. The number is what makes the ask negotiable: Barr
   clearing MS-2026-002 drops him to 2.00 and off the ladder entirely; clearing only MS-2026-003
   leaves him at 5.25, still capped at Tier 2. **That asymmetry is the ask, priced.**
6. Chain wiring: `primacy_factors.py` runs **after** `make_member_desk` (it consumes the bundle)
   and **before** the dashboard/desk build.

**Verification gate:** kernel tests → `run_pipeline.py` → **rank delta exactly zero** →
`audit_full.py` clean. If any rank moves, it was wired into the wrong layer.

### 7.4 Failure semantics (deliberate — mirrors `moneyball_core`'s bill-corroboration sentinel)

| Condition | Behaviour |
|---|---|
| `primacy_factors.json` missing | **Fail open** — every member factor 1.0, tier degrades to pure Leg%. Never a silent zero. |
| `primacy_factors.json` malformed | **Raise.** Corrupt evidence is never treated as absent. |
| `grievance_ledger.ndjson` missing | No gating; `apply_conduct_ladder` is the identity. |
| Ledger event without `leverage_mult` | Defaults to **1.0** — counts at face severity rather than vanishing. |
| Ledger event `status != 'open'` | Excluded from the sum. |
| Act in the bundle, absent from the tag file | **Raise.** Universe and classification must stay in sync. |
| Member absent from `factors` | Neutral **1.0**, never zeroed. |
| Unknown beneficiary class | **Raise.** |

---

## 8. Verification actually run — 17 invariants, all pass

Executed on the live `member_desk_bundle.json` and `ranks_python.json`, on Paul's own machine.

| | |
|---|---|
| Universe closure (bundle acts == tag acts) | 614 / 614 |
| Zero naked defaults (L9) | 0 acts |
| L8 `areas` asserting `cu_primary` | 0 — the circularity fix holds |
| Shrink containment | 0 / 533 violations |
| λ = min(1, credit / 15) | 0 / 533 violations |
| `shared` 0.500 vs baseline 0.502380 | gap 0.0024 — neutral **by construction** |
| pcts ↔ bundle parity | 533 ranked, no silent drops |
| Ladder is a permutation | pass |
| Ladder never promotes a capped member | pass |
| Ladder never demotes an uncapped member | pass |
| Ceiling monotone in effective severity | pass |
| Producer determinism | pass |
| OPPOSE acts weight −1.0 | pass |
| No Tier-1 member carries an OPPOSE act | 0 members |
| Board matches shipped fixture, all 533 | pass |
| Bucket sizes | 12 / 24 / 48 |
| **Rank delta vs `ranks_python.json`** | **0** — read-only, sha256 `79c087aa31091e75…` |

Primacy share of log-score variance: **0.6%** across all 532 scorable members, **61.5%** in the top
100, **86.6%** in the top 40, **84.2%** in the top 20. Leg% is a percentile and saturates at the
ceiling; primacy does not. Leg% decides who is in contention, primacy decides who wins among
contenders. Global Spearman (0.9928) is the wrong statistic for a top-k problem — it is dominated
by the ~400 members nobody is selecting.

---

## 9. Result

**Tier 1 (Champions), 1–12:** Padilla · Gonzalez★ · Fitzpatrick★ · Cramer★ · Timmons · Sullivan ·
Fitzgerald · Vargas · Tim Scott★ · Young Kim★ · Sherman★ · Huizenga
**13–18:** Hagerty · Meuser · Sessions · Crapo · **Cortez Masto★ (17)** · Bonamici
★ = named on the ground-truth list. **6 of 7 at 12 seats, 7 of 7 at 18.**

| Member | Score order | Final | Outcome |
|---|---|---|---|
| **Andy Barr** | 12 | **37** | Tier 3. Clean on score; the ledger is his only disqualifier. |
| **French Hill** | 73 | **85** | **Untiered.** Fails on his own record *and* carries 10.00. |

Eleven members between slots 74 and 84 move up one as Hill vacates. Tier 1 and Tier 2 are
untouched by MS-2026-004.

**Two things worth saying to your boss.** Hill fails the primacy axis without the ledger being
consulted at all — 1.0 of 20.50 agenda credit is CU-primary, and his two authored bills of this
Congress are a bank bill and a crypto bill. **Barr does not.** Barr is a Tier-1 member on the
numbers and only the grievance record removes him. That is the standing argument for keeping the
ledger maintained rather than decorative, and the reason every demotion row cites an event ID with
a URL and a cure.
