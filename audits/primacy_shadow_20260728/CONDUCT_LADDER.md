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

1. **Barr and Hill drew the identical penalty** though their leverage differs by design (Hill 2.00
   as full-committee chair *and* vehicle sponsor; Barr 1.75 as subcommittee chair of jurisdiction
   and original cosponsor). The ledger recorded the difference; the code erased it.
2. **Severity-2 events cost exactly nothing**, so they could accumulate without bound. Barr's
   credit-appropriation release was worth zero.
3. **There was no consequence above "not a Champion."** The worst actor in the file and a
   marginal one landed in the same place.

---

## 3. The mechanism

The ledger began as a way to record *failures*, because the original complaint was that the system
measured actions and not inactions. It then overcorrected: it could only ever punish. A chair who
refuses to move your asks earns an event; a chair who carries your bill across the floor earns
nothing. **The `cure` field on every grievance already implies the missing half** — a cure *is* a
delivery event, adjudicated by hand. So delivery is now its own ledger, and the ladder reads the
net:

```
net_severity = effective_severity  −  delivered_credit

effective_severity(member) = Σ  severity × leverage_mult      over OPEN, unexpired events
delivered_credit(member)   = Σ  act_weight × instrument_mult  over OPEN delivery events

    net ≥ 3   →   tier ceiling 2      (cannot be a Champion)
    net ≥ 6   →   tier ceiling 3
    net ≥ 9   →   untiered

instrument_mult:  reported out of committee under your gavel   1.00
                  floor-managed to passage                     0.75
                  markup scheduled, not reported               0.25
```

`act_weight` is the **same `ACT_W` table the primacy factor uses**, so delivery is priced by *who
the bill you moved was for*: moving a `cu_primary` bill earns 1.00, a `shared` bill 0.50, a
`crypto_primary` bill 0.15, an out-of-universe bill nothing. That single join is what stops this
from becoming the jurisdiction-leverage multiplier §3 of the spec already rejected — a chair does
not get paid for holding a gavel, only for what they spend it on.

**Delivery offsets conduct. It does not enter the primacy factor and it does not change any
score.** Primacy answers *champion for whom*; delivery answers *did you spend your position*.
Putting a `floor_manager` role into `ROLE_W` would mix the two questions into one number and
corrupt the beneficiary ratio. Consequences, all asserted in tests: delivery can only ever restore
a member **toward** their own score position, never above it; a member with delivery and no
grievance is completely unaffected; and more delivery is never worse than less.

**A ceiling is a floor on slot index, not a fixed demotion.** The member is barred from every slot
above their ceiling's first slot, then re-enters at their own score position among the remainder.
Placement is greedy and stable: walk the slots in order, take the best-scoring unplaced member
permitted in that slot.

Three properties follow, and all three are asserted in the test suite:

- **It is a permutation.** Nobody is dropped; `sorted(final) == sorted(order)`.
- **It never promotes a capped member.** `final.index(m) >= order.index(m)` for every capped `m`.
- **It never demotes an uncapped one.** A capped member's seat is released, never taken.

This is why Hill does not move: his net caps him at Tier 2, but his own score already put him at
73, and **a ceiling never promotes**. It is a consequence of the design, not a bug — and it was
exactly what exposed that his ledger was incomplete in *both* directions: a missing grievance
(MS-2026-004) and, more consequentially, a missing delivery record worth 3.00.

---

## 4. The ledger of record

### MS-2026-001 · French Hill · refusal on a vehicle he controlled — 3 × 2.00 = **6.00**

Full committee chair **and** sponsor of H.R.6955. All four ACU asks (H.R.4167 loan maturities,
H.R.7647 FHLB community-FI definition, H.R.507 veterans MBL exemption, H.R.1791 MBL threshold)
excluded. Passed 270-155-1 on 2026-07-22 without any of them.
> *"several provisions only address concerns for banks while not tackling top issues for credit unions"*
> — [America's Credit Unions](https://www.americascreditunions.org/news-media/news/house-clears-main-street-capital-access-act)

**Cure:** any of the four attached to or reported through an FSC vehicle under his control.

### MS-2026-004 · French Hill · credit appropriation — 2 × 1.00 = **2.00** *(new, 2026-07-29)*

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

**Hill gross: 8.00.** See §5 for why the multiplier is 1.00 and not 2.00, and §4a for the delivery
credit that nets it down to 5.00.

### MS-2026-002 · Andy Barr · refusal on a vehicle he controlled — 3 × 1.75 = **5.25**

Subcommittee chair of jurisdiction (Financial Institutions), original cosponsor of the vehicle.
Same four exclusions. **Cure:** H.R.4167 reported out of his subcommittee.

### MS-2026-003 · Andy Barr · credit appropriation — 2 × 1.00 = **2.00**

His [own release](https://barr.house.gov/2026/7/barr-leads-house-passage-of-main-street-capital-access-act-to-strengthen-community-banks-and-expand-opportunity)
claims the bill helps *"community banks and credit unions … better compete"* while quoting the
Kentucky Bankers Association and Commerce Lexington and **no credit union organization**.

**Barr gross: 7.25. Barr delivered: 0.00.** Net 7.25 → Tier 3 → slot 12 becomes slot 37.

---

## 4a. The delivery ledger — `delivery_ledger.ndjson`

Extracted from the Congressional Record already in `speeches_cu.csv`, on the motion phrasing, which
is boilerplate and parses cleanly:

> *"Mr. Speaker, I move to suspend the rules and pass the bill (H.R. 975)…"*

14 distinct member-bill motions across 7 members in the CU corpus. Each is joined to
`bill_beneficiary_tags.ndjson` and priced by class. Only 3 members end with credit:

| Member | Bill | Class | Credit |
|---|---|---|---|
| **French Hill** | H.R.975 Credit Union Board Modernization | **cu_primary** | 0.75 |
| **French Hill** | H.R.4437 SMART Act | **cu_primary** | 0.75 |
| **French Hill** | H.R.4544 American Access to Banking | **cu_primary** | 0.75 |
| **French Hill** | H.R.3390 Discount Window | shared | 0.38 |
| **French Hill** | H.R.6644 21st Century ROAD to Housing | shared | 0.38 |
| John Rose | H.R.2808 (FCRA) | shared | 0.38 |
| Mike Bost | H.R.1663 (VA fraud) | shared | 0.38 |
| *Hill ×4, Cline, Westerman, Tiffany, Jason Smith* | out of universe | — | 0.00 |

**French Hill 3.00 · John Rose 0.38 · Mike Bost 0.38 · everyone else 0.00. Andy Barr has no
delivery record at all.**

This closes a real hole. Hill personally carried **three `cu_primary` bills** to passage and the
system credited him for none of them, because floor management is not `sponsor`, `original` or
`cosponsor` — the only three roles the vocabulary has. His recorded CU-primary credit is 1.00 of
20.50 agenda credit, 4.9%, for a member who moved the Credit Union Board Modernization Act across
the House floor and said on the record *"this will be a great service to those credit unions."*

**Known coverage limit, and it understates delivery.** The highest-agency instrument — *reporting a
bill out of committee under your own gavel*, weight 1.00 — is **not yet extractable**; nothing in
the corpus records markup outcomes by member. Only `floor_managed` events exist today. And the
speech corpus is CU-scoped (307 rows), so this measures floor management *within credit-union floor
debate*, which is the right scope for this purpose but is not a census of legislative throughput.
Do not compare members on totals.

*Aside: Maxine Waters shows 5 "I yield myself such time as I may consume" — she is managing the
minority's time as ranking member. That is not moving a bill; she cannot schedule anything. It is
deliberately not credited, consistent with the existing rule that ranking members are not held to
the chair test.*

---

## 5. The judgment call, and why it was revised

**MS-2026-004 shipped for one draft at `leverage_mult = 2.0`, against Barr's structurally identical
MS-2026-003 at 1.0.** The argument was that Barr's is a personal press release while Hill's is the
committee's institutional voice under his own gavel. That distinction is real — but it does not
survive the rest of the record, and the record was checked only after the fact:

- *"community banks and credit unions"* is **Hill's consistent register**, not a one-off
  appropriation. He used the same phrasing in his floor statement on the same bill the same day.
- He has a **genuine delivery record** — the three `cu_primary` bills in §4a — which a
  credit-appropriation charge at double weight implicitly denies.

Pricing an identical instrument higher for him than for Barr was reverse-engineering toward a
destination. **1.00 is the defensible value, and it is what ships.** What actually distinguishes
the two members is now carried by the delivery ledger, where it belongs: **Barr delivers 0.00,
Hill delivers 3.00.**

What sustains MS-2026-004 at severity 2 even after the cut is the substance, which was verified
independently: the committee's own section-by-section for H.R.6955 runs to 8 titles and 30-odd
sections, **all bank-directed. Credit unions appear exactly twice, both as "NCUA" inside a list of
regulators. There is no credit-union provision in the bill.** The claim of credit-union benefit is
hollow on the merits. That is the event.

### The arithmetic, all of it

| | gross | delivered | **net** | ceiling | score order | **final slot** |
|---|---|---|---|---|---|---|
| **French Hill** | 8.00 | 3.00 | **5.00** | Tier 2 | 73 | **73** |
| **Andy Barr** | 7.25 | 0.00 | **7.25** | Tier 3 | 12 | **37** |

Hill's ceiling is Tier 2, but **a ceiling never promotes** — his own score already put him at 73,
which is Tier 3. So he lands at 73: exactly where his record put him before either ledger was
opened. Barr, by contrast, is a Tier-1 member on score alone and is held at 37 entirely by conduct.
**That contrast is the whole point of the mechanism**, and it survives every configuration tested.

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
| `load_delivery_credit(root)` | `{member: {'delivered': float, 'events': [(id, bill, class, credit)]}}`. Missing → `{}` (no offsets). Zero-credit rows never create a record. `status != 'open'` → excluded. |
| `tier_ceiling(eff)` | Best tier permitted. `1` unconstrained, `0` untiered. Monotone. |
| `apply_conduct_ladder(order, breaches, delivered)` | `(final_order, detail)`. Greedy, stable, permutation-preserving. Reads `net = gross − delivered`. `detail` covers every member with a grievance **or** a delivery record, so the desk can show both sides. |
| `primacy_scores(pcts, factors)` | `Leg% × factor`. Member absent from `factors` → neutral `1.0`, never zeroed. |

Module constants: `CONDUCT_LADDER = ((9.0, 0), (6.0, 3), (3.0, 2))`, `BUCKETS = (12, 36, 84)`.

### 7.2 Replacement body for `legislative_press_tiers()`

```python
root = root or _ROOT
with open(os.path.join(root, 'ranks_python.json'), encoding='utf-8') as handle:
    rp = json.load(handle)
pcts = rp.get('pcts', {})

factors   = load_primacy_factors(root)         # {} -> fail open to pure Leg%
breaches  = load_open_breaches(root)
delivered = load_delivery_credit(root)
all_scores = primacy_scores(pcts, factors)

rankable    = [m for m in members if m in all_scores]
score_order = sorted(rankable, key=lambda m: (-all_scores[m], m))    # deterministic tie-break
order       = apply_tier_overrides(score_order, load_tier_overrides(),
                                   positions=load_tier_positions())

final, detail = apply_conduct_ladder(order, breaches, delivered)

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
4. Add `test_primacy_tier.py` (**34 tests**) to `fec/tests/run_tests.py`, plus a fixture test
   against `FIXTURE_expected_board.csv` (all 533 rows, 9 dp).
5. Surface the reason in the desk and dashboard. **This sentence is the product:**
   > *"French Hill — Tier 3. Conduct 8.00 (MS-2026-001, MS-2026-004) less delivery 3.00 (moved
   > H.R.975, H.R.4437, H.R.4544) = net 5.00, ceiling Tier 2. Cure: any of H.R.4167 / H.R.7647 /
   > H.R.507 / H.R.1791 attached to or reported through an FSC vehicle under his control."*

   Show **both sides**. A member's staff reading only the grievance half will dispute it, and they
   will be right to.

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
| `delivery_ledger.ndjson` missing | No offsets; the ladder reads gross severity, exactly as before. |
| Delivery row with 0.00 credit (out-of-universe bill) | Skipped — never creates a member record. |
| Ledger event `status != 'open'` | Excluded from the sum. |
| Act in the bundle, absent from the tag file | **Raise.** Universe and classification must stay in sync. |
| Member absent from `factors` | Neutral **1.0**, never zeroed. |
| Unknown beneficiary class | **Raise.** |

---

## 8. Verification actually run — 23 checks, all pass, 34 kernel tests

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
| Delivery alone never caps a member | 2 delivery-only members, all unconstrained |
| Delivery is monotone — more is never worse | pass |
| Board matches the shipped 533-row fixture | pass |
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

| Member | gross | delivered | net | ceiling | score order | Final |
|---|---|---|---|---|---|---|
| **Andy Barr** | 7.25 | 0.00 | 7.25 | Tier 3 | 12 | **37** |
| **French Hill** | 8.00 | 3.00 | 5.00 | Tier 2 | 73 | **73** |

Twenty-four members between slots 13 and 36 move up one as Barr vacates. Tier 1 is untouched.

**Three things worth saying to your boss.**

**Barr is the real case.** He is a Tier-1 member on the numbers — clean primacy, clean delivery
would have kept him there — and *only* the grievance record removes him. That is the standing
argument for maintaining the ledger rather than treating it as decorative.

**Hill needs no ledger at all.** He fails the primacy axis on his own record: 1.00 of 20.50 agenda
credit is CU-primary, and his two authored bills of this Congress are a bank bill and a crypto
bill. He lands at 73 whether or not anyone opens the ledger.

**And Hill is not nothing.** He floor-managed three credit-union bills to passage, including the
Credit Union Board Modernization Act, and said on the record it *"will be a great service to those
credit unions."* The delivery ledger exists because the first version of this analysis missed that
entirely and would have taken him off the board on an incomplete record. **A conduct system that
can only subtract will eventually be wrong about someone, and it will be wrong in the direction
that is hardest to walk back.**
