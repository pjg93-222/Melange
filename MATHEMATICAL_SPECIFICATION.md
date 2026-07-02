# Melange Systems — Mathematical Specification

**A complete, self-contained formal specification of the credit-union ("Moneyball") legislative-influence model.**

This document is written to be rigorous enough that a quant can reimplement the system from it alone. Every formula, constant, data source, and rationale is given. Where the documented intent and the actual code disagree, that disagreement is called out inline as **⚠ AUDIT NOTE** (those notes are cross-referenced in the accompanying findings report).

Scope: the canonical folder is `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`. Python engine in `fec\`, derived data as root `*.json`, master workbook `Moneyball Main Version - Blended.xlsx`. The system scores 533 members of Congress on 17 issues and allocates a credit-union (CU) budget to maximize CU legislative influence.

---

## 0. Notation, member set, and global conventions

| Symbol | Meaning |
|---|---|
| `n`, `m`, `u`, `v` | a member of Congress (one of 533) |
| `M` | the member set, \|M\| = 533 |
| `c` | one of the 17 issue categories (also "topic"/"cat") |
| `sc` | a legislative block start-column in the workbook (one of 18 blocks) |
| `cu(n)` | CU PAC money received by `n` (USD) |
| `ind(n)` | competing-industry money = `banks(n) + finserv(n)` (USD) |
| `R(n)` | fundraising receipts of `n` (USD), floored |
| `adj[n][u]` | co-sponsor network edge weight between `n` and `u` |
| `prt(n)` | party ∈ {D, R, I, ?} |
| `bpf(n)` | bipartisanship fraction ∈ [0,1] |

The member set M is defined by `congestion.json` (533 records). It is **exactly** consistent with the `category_stance.json` matrix and with rows 3–535 of the workbook sheets `Blended Model`, `Legislative Score - Normalized`, and `Rank & Allocation` (verified: 533 unique names, no duplicates, no header bleed; §Data Integrity).

All workbook member rows are read with `range(3,536)` → rows 3…535 inclusive = 533 rows. Row 2 is a header/weight row; row 536 is empty. This is correct (verified).

---

## 1. Data inputs

### 1.1 `congestion.json` — money state
Per member: `cu`, `banks`, `finserv`, `receipts`, `total` (FEC-derived USD), plus `bioguide`, `net_lean`.
- Source: FEC bulk files in `fec\` (itpas2, cm, cn, weball24, etc.) processed by the `*congestion*.py` / `final*.py` builders.
- Coverage (verified): `cu` zero/null 128/533 (24.0%), `banks` 121 (22.7%), `finserv` 269 (50.5%), `receipts` 18 (3.4%), `total` 63 (11.8%). No field is ever `null` (always a number, possibly 0).

### 1.2 `category_stance.json` — the 533×18 stance matrix
Keys: `cats` (18 labels — the original 17 plus **`CU Tax Status`, added 2026-07-01** per the ABB26 handout's flagship Protect priority; all-`—`/0.0 scaffolding until data collection tags tax bills & press), `defensive` = {`Interchange`, `Credit Card Mandates`}, `matrix` (533 members × 18 tiers), `scores` (533×18 signed continuous score). The flip-engine topics remain the 18 legislative blocks (17 categories) — CU Tax Status has no legislative block yet. Tier vocabulary:
`Champion, Defender, Ally, Highly Persuadable, True Neutral, Lean Skeptic, Neutral(internal), Skeptic, Opponent, —`.
`—` means *no recorded position on this issue* (≈59.8% of cells). Produced by `per_category_stance.py` (§2).

### 1.3 Co-sponsor network — `congress_cosponsor_network_*.xlsx` (latest by mtime)
Sheet `Edges`: columns (bioguide_a, bioguide_b, weight). Loaded undirected: `adj[a][b]=adj[b][a]=w`. Endpoints are mapped bioguide→name via `bio2name`. Rows where an endpoint is not in M are dropped.

### 1.4 Party — `votes\HS{119,118,117}_members.csv`
`party_code` 100→D, 200→R, else→I. First occurrence (119th preferred) wins.

### 1.5 `bipartisan.json` — `bpf(n) = BP[n]/100`, default 24 (→0.24). Range observed [0.03, 0.62].

### 1.6 `electoral.json`, `electoral_plays.json` — §6.

### 1.7 Workbook engagement — `Legislative Score - Normalized`
18 legislative blocks at start-columns `sc ∈ {3,11,19,27,35,43,51,59,67,75,83,91,99,145,115,107,123,131}`. Each block spans 8 columns; the **weighted** sub-columns are at offsets {0, 2, 4} with row-2 weights ≈ {0.2857, 0.1429, 0.0714} (Sponsor / Original-Cosponsor / Co-sponsorship). Offsets {1,3,5} are Average/Success columns with weight 0 (deliberately excluded). Verified against the live header.

---

## 2. Per-category stance (`per_category_stance.py` → `category_stance.json`)

For each issue `c` and member `m`, a combined signed score `comb(c,m)` is built from three pillars, then thresholded into a tier.

### 2.1 Pillar weights
```
weights(c) = (0.55, 0.70, 0.20)   if c ∈ DEFENSIVE = {Interchange, Credit Card Mandates}
           = (0.55, 0.35, 0.10)   otherwise
```
(WL, WP, WV) = (legislative, press, vote) weights.

### 2.2 Raw pillar normalization
- Legislative raw `legraw(c,m)` from `archive_leg.json`. Sqrt-compressed to tame the heavy tail:
  `legc = sign(legraw)·√|legraw|`.
- Press raw `prraw(c,m)` from `Press Release - Normalized`.
- Each normalized by an 80th-percentile scale `p80(·)` of the |values|, then clipped to [−1,1]:
  `ln = clip(legc/sl)`, `pn = clip(prraw/sp)`, with `sl = p80(legc)`, `sp = p80(prraw)`.
- Vote lean `vn = clip(vinfo.lean)` used only when the member has ≥5 recorded votes on `c` (`hv`).

### 2.3 Combined score
```
Defensive c:      comb = clip( WL·ln + WP·pn + WV·vn )
Non-defensive c:  comb = ( WL·ln + WP·pn + WV·vn ) / ( WL + WP + (WV if hv else 0) )
```
The non-defensive form **renormalizes by the active weight mass** so members without a vote pillar aren't penalized. Defensive issues are press-led and intentionally *not* renormalized.

**Anti-prior correction:** if `comb>0` but the member is press-silent (`prraw ≤ 0.02`) and has a positive overall-anti signal `anti(m)>0`, shrink:
`comb ·= (1 − PRIOR·anti(m))`, `PRIOR = 0.70`. (`anti(m)` is the negative of the press-weighted overall lean, percentile-scaled, floored by the R&A overall-stance label via `ANTI_STANCE={Opponent:1.0, Skeptic:0.5}`.)

### 2.4 Self-calibrating thresholds (median + k·IQR, rate-bounded)
For a sorted value list `s`:
```
shaped_cut(s, hi, rfloor, rcap, k=1.25):
    q1,med,q3 = quartiles(s);  iqr = max(q3−q1, 1e−9)
    if hi:  c = med + k·iqr;  rate = clamp( |{x≥c}|/n , rfloor, rcap );  return quantile(s, 1−rate)
    else:   c = med − k·iqr;  rate = clamp( |{x≤c}|/n , rfloor, rcap );  return quantile(s, rate)
    (returns None if n < MINN = 8)
```
This sets a cut at a data-driven quantile whose *rate* is bounded to a sane band — so a category can't make 40% of members Champions or 0%.

**Non-defensive classification** (per category, on signed `comb`):
- Champion cut `cc` = `shaped_cut(P, hi, 0.03, 0.12)` (≤12% elite band)
- Ally boundary `ac` = `shaped_cut(P, hi, 0.30, 0.60)`
- Opponent cut `oc` = `shaped_cut(Ng, lo, 0.05, 0.25)`; Skeptic boundary `sc` = `shaped_cut(Ng, lo, 0.30, 0.60)`
- where P = positive-`comb` members with signal, Ng = negative-`comb`. Pooled empirical fallbacks (`pooled_champ` etc.) when a thin category returns None.
```
c≥cc → Champion;  cc>c≥ac → Ally;  0<c<ac → Neutral
c≤oc → Opponent;  oc<c≤sc → Skeptic;  sc<c<0 → Neutral
no signal → —
```

**Defensive classification** (Interchange, Credit Card Mandates — press/legislative led, signed):
```
leg ≤ oppc            → Opponent
leg < 0               → Skeptic
leg ≥ defl OR prs≥defp→ Defender
leg > 0 OR prs≥0.4·defp→ Ally
prs ≤ −0.4·defp       → Skeptic
else                  → Neutral
no signal             → —
```
with `oppc, defl, defp` from `shaped_cut` on the defensive legislative/press distributions.

> **⚠ AUDIT NOTE 2.A (cosmetic/fragile, not a bug):** the `defl` fallback is written
> `defl = defl if defl is not None else qtile(POOLlegneg,0.0) and 2.0`, then `defl = defl or 2.0`.
> The `<negative> and 2.0` Python idiom evaluates to `2.0` (any nonzero is truthy), and line 70 catches the rest, so the fallback is effectively `2.0`. It happens to be correct. **Interchange has 0 positive-leg members** (verified), so `shaped_cut` for `defl` always returns None and the `2.0` fallback fires — meaning on Interchange a Defender can only arise via the press path `prs≥defp`, never the legislative path. This is consistent with Interchange being press-led, but the idiom is brittle; prefer an explicit constant.

### 2.5 Neutral split into persuadability tiers
Each category's `Neutral` band is split by its **own** tertiles of `scores`:
```
c ≥ t67 → Highly Persuadable
t33 ≤ c < t67 → True Neutral
c < t33 → Lean Skeptic
```
(`t33,t67` = 34th/67th percentiles of the category's Neutral scores; degenerate fallback ±0.0001 if <6 members.)

---

## 3. The persuadability and target-value layer (shared by flip + optimizer)

### 3.1 Persuadability weights `PERS`
Maps a per-category tier to a persuadability multiplier (how movable the member is on that issue). **CALIBRATED — compressed from a ~10:1 to a ~3:1 spread** (real persuasion is small & bounded — Coppock "parallel publics"; Kalla-Broockman minimal effects; Bakker asymmetry):
```
Champion 0.10, Defender 0.12, Ally 0.40, Highly Persuadable 0.55, True Neutral 0.50,
Lean Skeptic 0.40, Neutral 0.50, Skeptic 0.25, Opponent 0.08, '—' 0.50 (env PERS_NONE)
```
`'—' = 0.50` sets a silent member at **parity with True Neutral** (a blank = uncommitted/unconstrained, most movable ~ neutral; Bergan; Butler-Nickerson) — env-tunable via `PERS_NONE`. **Identical in `flip_model.py` and `per_topic_flip.py`** (verified).

### 3.2 Camp assignment
```
PRO  = {Champion, Defender, Ally}
ANTI = {Opponent, Skeptic}
camp(t) = pro if t∈PRO; anti if t∈ANTI; neu otherwise
```

### 3.3 Source-alignment factor `cpf`
**CALIBRATED — this replaced the old bipartisan "bridge amplifier".** Pressure from a *co-partisan* colleague carries more weight than from an out-partisan one (the largest documented elite-influence effect — Furnas; Bakker):
```
cpf(n,u) = 1.7   if prt(n)=prt(u) and both ∈ {D,R}   (co-partisan pressure amplified)
         = 0.5   if prt(n)≠prt(u) and both ∈ {D,R}   (out-partisan pressure damped)
         = 1.0   otherwise (Independents / unknown)
```
`cpf` is symmetric (party-equality symmetric, edge weight set both directions).

> **⚠ CORRECTED 2026-07-01 — there are TWO deliberate kernels, not one.** An earlier revision of this spec
> wrongly claimed the 1.7/0.5 source-alignment kernel was "L4-unified across all 7 modules." The live code
> (and the AUDIT_ROADMAP Phase-7 design rationale) intentionally split them:
> - **FLIP family** (`flip_model`, `per_topic_flip`): the source-alignment kernel above (1.7 / 0.5 / 1.0) —
>   co-partisan pressure amplified in the nA/nB proximity sums (Furnas; Bakker).
> - **DIFFUSION/ROUTE family** (`scenario`, `budget_frontier`, `per_topic_coalition`, `cosponsor_route`,
>   `lt_priming`): bipartisan **damping** on cross-party edges,
>   `cpf(n,u) = 0.4 + 0.6·√(bpf(n)·bpf(u))` if prt(n)≠prt(u) (both ∈{D,R}), else `1.0` —
>   cascades spread more weakly across the aisle (homophily — Harmon; Andris), damped least between two
>   bridge-builders. Each family is internally consistent (verified).
>
> *(The bipartisanship signal `bpf` also enters as the always-on passage bonus in `tgt`, §3.6, and the
> coalition seed boost, §5.3.)*

### 3.4 Network proximity to a topic's champions/opponents
For topic `c` with per-member camps:
```
nA(n) = Σ_{u∈adj[n], camp(u)=pro}  adj[n][u]·cpf(n,u)   (bridge-amplified pull toward pro)
nB(n) = Σ_{u∈adj[n], camp(u)=anti} adj[n][u]·cpf(n,u)   (... toward anti)
mAt = max_n nA(n) (or 1);   mBt = max_n nB(n) (or 1)    (per-topic normalizers)
```

### 3.5 Engagement signal `eng`
```
eng[sc][n] = Σ_{o∈{0,2,4}}  weight(2, sc+o) · normalized_value(row_n, sc+o)
```
Read from `Legislative Score - Normalized`. For **CFPB**, two legislative blocks (99 = CFPB-Restrain, 145 = CFPB-Reach) map to the single combined CFPB stance; the engagement signal **sums both blocks** (`cat2blocks[99]=[99,145]`). Verified load-bearing: Al Green, Warren, McGarvey, Whitehouse carry block-145 engagement that would otherwise be dropped (the M3 fix). All `eng` values observed ≥ 0.

### 3.6 Target value `tgt` (strategic value × persuadability)
```
tgt(n) = ( eng[sc][n] + BASE·score(n)/smax ) · PERS[ stance(n,c) ] · (1 + 0.3·bpf(n))
BASE = 0.15
```
`score(n)` = Blended-Model composite (workbook col 19); `smax = max score`. The `(1 + 0.3·bpf)` factor is the
**always-on PASSAGE bonus** (bipartisan members advance bills more — Volden-Wiseman +8–14% → higher strategic
value; identical in flip_model and per_topic_flip). With `--bridge`, the 0.3 bonus is **replaced** by
`(1 + GAMMA·bpf(n))`, `GAMMA = 1.2` (a stronger bridge-targeting mode). *(Corrected 2026-07-01: an earlier
revision omitted the always-on 0.3 bonus.)*
All 9061 (member,topic) `tgt` values observed ≥ 0 (verified) — so the `tgt>0` candidate filter and the `Σ tgt·pflip` objective are sign-consistent, no negative drag.

---

## 4. Flip / winnability model (`flip_model.py`, `per_topic_flip.py`)

### 4.1 The flip probability `pflip`
A capacity-aware competing **Linear-Threshold** winnability. With allocation `al` of new CU money on `n`:
```
a = WM·(cu(n)+al+1) / ((cu(n)+al+1) + HALFF·R(n))  +  WP·nA(n)/mAt        (pro pull)
b = WM·(ind(n)+1)   / ((ind(n)+1)   + HALFF·R(n))  +  WP·nB(n)/mBt        (anti pull)
pflip = a/(a+b)   (0 if a+b=0)
```
Constants: `WM = 0.35` (money channel — the minority partner), `WP = 0.65` (network channel), `HALFF = 0.10` (env `HALFF`). CALIBRATED from 0.6/0.4: money buys access/effort, not votes (Ansolabehere; Hall-Wayman; Kalla-Broockman).

**Money term (Michaelis-Menten):** `(cu+al+1)/((cu+al+1)+HALFF·R)` saturates toward 1; half-saturation at total CU money = `HALFF·R = 0.10·receipts`. The `+1` is Laplace smoothing (prevents 0/0 and a false `pflip≈1` for zero-money members).

**Properties (independently verified, 2×10⁵–10⁵ random trials each):**
- `pflip ∈ [0,1]` always (0 out-of-range).
- **Monotone non-decreasing in CU** (0 violations) — more CU money never lowers winnability.
- **Concave in CU** (0 convexity violations) — genuine diminishing returns.
- `flip_model.pflip` and `per_topic_flip` arithmetic are **numerically identical** (max abs diff = 0.0 over 10⁵ random inputs). `flip_model.pflip(cu_state,…)` takes the post-allocation CU directly; `per_topic_flip.pflip(n,al,…)` adds `al` internally — same result.

> **⚠ AUDIT NOTE 4.A (modeling choice):** the money term saturates on **total** CU `(cu+al+1)`, not the *added* amount `al`. A member who already holds large CU money is near saturation, so additional CU barely moves their `pflip`. This is internally consistent (capacity is about total dollars vs receipts) but means the optimizer prefers low-existing-CU members; this is a defensible choice, not an error.

### 4.2 Expected weighted flips on a topic
```
flip_value(c) = Σ_n  tgt(n)·pflip(cu(n), ind(n), R(n), nA(n), nB(n), mAt, mBt)
```
Total winnability = Σ over the 17 categories. Baseline observed: **171.76**.

### 4.3 Receipts floor and imputation
```
R(n) = MEDIAN{R(m):receipts>0} if receipts(n)=0 (no record), else max(receipts(n), 200000)   (HIGH-2: impute, don't floor — §7.A)
ind(n) imputed: if receipts(n)=0 → ind(n) = median{ ind(m) : ind(m)>0 }   (H3, FEC-verified trigger)
```
H3 prevents a member with **no FEC fundraising record at all** (receipts=0 → truly blind: 18 new/special-election
winners and unresolved joins) from reading as `b≈0 → pflip≈1` ("missing" misread as "no opposition"). Verified:
all blind members imputed; **0** rank in the top-50 winnability.

> **✅ RESOLVED — AUDIT NOTE 4.B (was Findings HIGH-3):** an earlier version imputed for `ind=0` regardless of
> record, which **over-corrected**. An FEC re-verification (`itpas2.txt`, 24K/24Z transactions, joined via
> `cm.txt`) confirmed that the **91 members who raised money but show `ind=0` are VERIFIED-REAL zeros**: they
> received \$0 from the 33 tracked major bank/finserv PACs (ABA, Citi, Wells, JPMorgan, BofA, Visa, MC, Amex,
> Discover, Capital One, Ally…). They are 39 D / 4 R among the prominent, many no-corporate-PAC members
> (Tlaib, Casar, Jayapal); their only "other-industry" money is **insurance** PACs or false-positives (END
> CITIZENS UNITED matched on "citi"), not banks. So `ind=0` here is **real signal** ("not captured by the
> banking industry"), not missing data — imputing it would *fabricate* opposition. The trigger is therefore
> `receipts=0` (no record), and verified-real zeros are trusted. `IMPUTE_IND0=0` disables imputation entirely.

### 4.4 Per-topic flip allocation (`per_topic_flip.py`)
Greedy marginal allocation per topic, `INC = 1000`, `BUDGET = 2,000,000`, per-member `CAP = 50,000`:
```
marg(n) = 0 if al(n)≥CAP else tgt(n)·[ pflip(n, al(n)+INC) − pflip(n, al(n)) ]
```
A max-heap allocates `INC` to the current best marginal until budget exhausted or no positive marginal. Writes `per_topic_alloc.json` (or `_bridge` with `--bridge`).

---

## 5. Competitive coalition cascade (`scenario.py`, `budget_frontier.py`, `per_topic_coalition.py`)

A competitive **Independent Cascade** (Bharathi-Kempe-Salek competing diffusion): pro seeds (A) and anti seeds (B) race to color the network; the count of A-colored nodes is CU coalition spread.

### 5.1 Edge activation probability
```
P[u][v] = (w·cpf(u,v)) / (w·cpf(u,v) + 6.0)        w = adj[u][v]
```
The `+6.0` (CALIBRATED 4.0→6.0) is the half-saturation weight (an edge of raw weight 6 fires w.p. 0.5 before amplification). **Identical kernel in all three cascade modules + the two route modules** (verified).

### 5.2 Cascade with common random numbers (CRN)
**`scenario.py`** uses a splitmix64 edge-keyed CRN — the draw for edge (u→v) at iteration `it` is a pure function of `(it·NM² + idx[u]·NM + idx[v])`, independent of activation order:
```
_sm(x): splitmix64(x) → [0,1)
edge (u,v) fires iff _sm(it·NM² + idx[u]·NM + idx[v]) < P[u][v]
```
**Independently verified exact:** a B-seed perturbation in one network component leaves disconnected nodes' coloring **bit-identical** across 10⁵ iterations (0 changes). So baseline-vs-scenario at the same seed isolates the real effect with **zero RNG noise**. This is the correct, gold-standard CRN.

> **✅ RESOLVED — AUDIT NOTE 5.A (was HIGH):** the cascade **edge activation** in `budget_frontier.py` and
> `per_topic_coalition.py` now uses the splitmix edge-keyed CRN (`_sm(it·NM²+idx[u]·NM+idx[v])`, identical to
> `scenario.py`) — order-independent, exact. The residual desync was in the **bystander roll**: `per_topic_coalition.py`
> gated its `random.random()` draw behind `n not in s`, so adding a seed changed how many draws fired → stream desync.
> **Fixed (2026-06-29):** the draw now fires for *every* member first, then filters (matching `budget_frontier.py`'s
> roll-for-all order). So `spread({n})−base` shares draws and isolates the true effect with **no MC desync noise**,
> across all three cascade modules. (`scenario.py` was already exact.)

### 5.3 Bystander activation
Neutral members spontaneously join the cascade as bystanders:
```
P(bystander n) = min(0.9, ind(n)/BSCALE)     BSCALE = 400000   (CALIBRATED 350k→400k)
```
Bounded in [0, 0.9]; observed max 0.51 (no member hits the 0.9 cap). Modeled as industry-money-driven baseline activity. Rolled for **every** member each iteration (CRN-stable) then filtered to neutrals not already seeded.

**Coalition seed boost (`per_topic_coalition.py` only):** a bridge member's marginal is boosted `v·(1 + BETA_C·bpf(n))`, `BETA_C = 0.8` — a *different* mechanism from `cpf` (it weights the *seeding budget*, not edge probability).

### 5.4 Nested CELF frontier (`budget_frontier.py`)
Seeds the pro core (Champions/Defenders/Allies free), then greedily adds Neutrals (`coalition`), and in `--electoral` mode also `contest` (flip an anti) and `defend` (insure a competitive ally). Per-seed cost `CAP = 50,000`, up to `MAXSEEDS = 60`.
```
marg(c,S,D,cur) = max(0, spread(...with c added...) − cur) · fac(c)
fac(c) = REPFAC·lev(c)  if contest      (REPFAC = 0.6, primary-feasibility discount)
       = 1.0            if defend
       = lev(c)         if coalition     (electoral leverage, §6)
```
Display spread is clamped non-decreasing (`prev=max(prev,cur)`) to hide MC dips; the **true** `cur` drives marginals. Knee = last seed whose marginal ≥ 25% of peak marginal.

---

## 6. Electoral layer (`build_electoral.py`, `build_electoral_plays.py`)

### 6.1 Leverage (`electoral.json`)
From Ballotpedia `Election_Average` (margin proxy), matched by last-name+initial:
```
security(m) = percentile-rank of elavg(m)   ∈ [0,1]  (higher = safer)
leverage(m) = 1 + LELEV·(1 − security(m))    LELEV = 0.8 (CALIBRATED 0.6→0.8)  → leverage ∈ [1.0, 1.8]
unmatched → security 0.5, leverage 1.4
```
Verified: leverage ∈ [1.001, 1.600], security ∈ [0, 0.998]; 503/533 matched.

### 6.2 Plays (`electoral_plays.json`)
Non-partisan gating on the **overall** R&A stance, using per-category score gaps vs party means:
```
gap_opp(c)  = SCO(m,c) − mean_{opp party}(c)     (vs general challenger)
gap_same(c) = SCO(m,c) − mean_{same party}(c)    (vs primary challenger)
comp(m) = 1 − security(m)

if overall ∈ PRO:        play=defend,  value = comp · mean_c max(0, gap_opp(c))
elif overall=Opponent:   play=contest, primary = mean_c max(0,−gap_same(c))
                                        general = comp · mean_c max(0,−gap_opp(c))
                                        value = max(primary, general), route = whichever larger
else:                    play=none
```
Verified: contest gated to Opponents only (53), defend to PRO only (309), contest party balance not skewed >70% one party. Defend value range [0, 0.328] (some 0-value defends are emitted but the frontier gates on `comp≥0.4`).

---

## 7. Money → lean / defection (`money_response.py`)

### 7.1 Money-response curve (Michaelis-Menten, shared with flip)
```
r = amount / receipts(m)          receipts(m) = MEDIAN if receipts=0 (no record), else max(receipts, RFLOOR=200000)
shift = MAXSHIFT · r/(r + HALF)    (signed: + for cu, − for comp)
MAXSHIFT = 18   (CALIBRATED 40→18: money moves positions little)   HALF = 0.10
```
Saturates toward ±18. **Reconciles with the flip money term:** both are Michaelis-Menten with half-saturation at money = `0.10·receipts` (`HALFF = HALF = 0.10`, verified equal). Verified inverse pair with lt_priming's `dollars_for_units` (error 1e-16). `receipts=0` is imputed to the median (§7.A), not floored.

### 7.2 Defection rule
```
ORDER = [Champion, Ally, Highly Persuadable, Persuadable, Lean Persuadable, True Neutral,
         Lean Skeptic, Skeptic, Highly Skeptical, Opponent]    (the FULL 10-rung overall ladder, pro→anti)
COMMITTED = {Champion, Opponent}                        (only the TERMINAL rungs are money-immune)
DTHRESH = 11.25   (net-lean shift needed to risk a defection; env DTHRESH — see rescale note below)
PROJ (aliases only): Defender→Champion; bare Neutral / legacy Unengaged → True Neutral.

defection(m, dlean):
   st = PROJ.get(overall, overall)
   if st ∈ COMMITTED or |dlean| < DTHRESH: return None
   steps = ⌊|dlean| / DTHRESH⌋
   i = ORDER.index(st)
   j = clamp(i + (steps if dlean<0 else −steps), 0, 9)   # comp(−)→toward Opponent; cu(+)→toward Champion
   return ORDER[j] if changed else None
```
One DTHRESH crossing = ONE fine ladder rung — consistent with the optimizer's per-category
`CONV_MAXSTEP = 1` fine-tier move (the earlier coarse 5-rung ORDER made one crossing ≈ 2 fine tiers, the
"unjustified cross-taxonomy magnitude" of note M2). **Highly Skeptical is deep but movable** (user
calibration 2026-07-01): 8 rungs from Champion, one from Opponent — e.g. Durbin (overall = Highly
Skeptical) defects to Opponent under a ≥ DTHRESH competitor shock, and is absorbed below it.
Verified directions correct (comp→Opponent, cu→Champion), terminal rungs immune.

> **✅ RESOLVED — AUDIT NOTE 7.B (was CRITICAL, found+fixed 2026-07-01):** two compounding defects had
> silently killed this mechanic. **(1) Impossible threshold:** DTHRESH=25 was calibrated while MAXSHIFT was
> still 40 (conversion boundary: donation ≥ ~1/6 of receipts). When MAXSHIFT was cut 40→18, the curve's
> *ceiling* (18) fell below the threshold (25) — `|dlean| < DTHRESH` was ALWAYS true, so no donation of any
> size could ever trigger a defection (optimizer conversions, scenario money-defections, and the dashboard
> warning were all dead code). **Fixed by rescaling DTHRESH to 11.25 = 18·(1/6)/((1/6)+0.10)** — this
> preserves the ORIGINAL calibrated boundary exactly (a chunk ≥ ~16.7% of receipts risks one tier; still
> rare/earned: a $10k FEC-capped PAC donation on median receipts shifts <1 point). **(2) Vocabulary hole:**
> `defection()` returned None for any overall label outside the 5-tier ORDER, but R&A col G now carries the
> 11-label ladder — so 419/533 members (79%, the movable middle) were categorically immune. Fixed with the
> PROJ ladder→ORDER projection above.

> **✅ RESOLVED — AUDIT NOTE 7.A (was HIGH):** the receipts **floor** (200000) had made `receipts=0` (no FEC
> record) members the *cheapest* to convert — a chunk read as a large fraction of the artificial $200k floor, so a
> blind member instant-converted. **Fixed (2026-06-29):** `money_response.receipts()`, `flip_model.R`, and
> `per_topic_flip.Rcap` now **impute the MEDIAN receipts** for no-record members (the floor still applies only to
> *real* small fundraisers). A blind member now reads as *typically* movable, not artificially cheap. With MAXSHIFT 18
> and the calibrated caps (optimizer PMAX $10k, live what-if slider $20k), `dlean` for these members stays well below
> DTHRESH — no instant conversion. (The DTHRESH default was also reconciled 15→25, removing the code-vs-comment contradiction.)

---

## 8. Co-sponsor route finder (`cosponsor_route.py`) — RELINK + MOPBD*

Edge-activation IM: champions seed; each recruiter whips ≤ `K = 5` colleagues (out-degree budget). Returns the Pareto front over (money, co-sponsors gained, risk).
```
P[u][v] = (w·cpf(u,v))/(w·cpf(u,v)+6.0)          (diffusion-family damping kernel + the +6 half-saturation, same as §5.1; spec corrected 2026-07-01 — an earlier revision wrote +4)
edge_cost(p) = CEDGE / max(0.1, p)                CEDGE = 10000   (unlikely asks cost more)
greedy value of recruiting v from u: val = (reach(u)·p − λ·(1−p)) / edge_cost(p)
```
λ ∈ {0, 0.5, 1, 2, 4} sweeps risk-aversion. With `MCMODE=1`, reach is recomputed by an exact MC IC cascade (`MC=40`, CRN `random.seed(1009·it)`) capturing reinforcement; otherwise tree-reach.

**Pareto front** (want spread↑, cost↓, risk↓):
```
a dominated iff ∃b: b.spread≥a.spread ∧ b.cost≤a.cost ∧ b.risk≤a.risk ∧ (strict in ≥1)
```
**Verified genuinely non-dominated:** front size 37, 0 internal dominance violations, 0 external dominators. (Cosmetic: duplicate points across λ survive `set()` because λ is a 4th coordinate; the print loop dedupes by `(cost//25000, round(spread))`.)

---

## 9. LT-priming (`lt_priming.py`)

For each persuadable target, the cheapest balance of network pressure + money to clear its Linear-Threshold:
```
THETA = {Highly Persuadable:0.6, True Neutral:1.0, Neutral:1.0, Lean Skeptic:1.5, Skeptic:2.0, Opponent:3.0, Ally:0.0}
        (CALIBRATED — widened at the committed end: Bakker asymmetry; corrected in spec 2026-07-01)
theta(v)    = THETA[tier] + max(0, −net_lean(v)/120)     (money-captured members resist more — sign verified)
pressure(v) = Σ_{u∈pro neighbors} P[v][u]
gap = theta − pressure
money_units(v,$) = r/(r+HALF),  r=$/receipts            (= shift/MAXSHIFT, in influence units)
dollars_for_units(v,u) = HALF·receipts·u/(1−u), u capped 0.98   (exact inverse, verified 1e-16)
```
Recruit not-yet-pro neighbors cheaper per unit than money's average rate (each adds `P[v][u]`), then close the residual with money. If residual > 0.97 units → not primeable on money alone.
**Verified: all 148 Mortgage targets' recipes close their gap (0 failures).** Kernel unified (L4).

---

## 10. Adaptive optimizer (`optimize.py`) — Golovin-Krause adaptive submodularity

Greedily allocates a CU budget to maximize total winnability (§4.2). `BUDGET = 2,000,000`, `INC = 500` (CALIBRATED 100k→500: a realistic contribution step → fine-grained spread across many candidates), per-member cap `PMAX = 10,000` (CALIBRATED 300k→10k: the FEC PAC→candidate per-cycle legal limit — no candidate can legally take more).

### 10.1 Marginal and lazy (CELF) greedy
```
marg(m) = 0 if m∈won or cu(m)≥cu0(m)+PMAX
        else Σ_c tgt(m)·[ pflip(cu(m)+INC) − pflip(cu(m)) ]   over topics where tgt(m)>0
```
A lazy priority queue with a staleness counter (`le==step`) implements CELF.
**Verified: CELF lazy greedy == exhaustive greedy** on the submodular core (Interchange, $400k) — identical picks (Wicker, Bennet, Hudson, Burchett) and identical marginals. This confirms the (1−1/e) lazy-evaluation correctness.

### 10.2 Adaptive conversion (the "observe → re-optimize" loop)
When cumulative CU on `m` crosses the money-response defection threshold, `m` **converts** (joins the pro coalition), is realized into `secured`, and leaves the flippable pool:
```
contrib = Σ_c tgt(m)             # bank m's flip at certainty (pflip→1)
secured += contrib;  won.add(m);  shift_pro(m, capped at CONV_MAXSTEP=1 fine tier)
cur = secured + unwon_winnability();  rebuild queue
```
**Verified monotone:** the realized objective path has **0 monotonicity violations** (the H1 fix — conversion is a *gain*, banking `tgt` at certainty exceeds the pre-conversion partial `tgt·pflip`). Full $2M run (2026-07-01, INC $500 / PMAX $10k, current workbook): **120.17 → 145.44 (+25.27)**, 200 members funded at the $10k cap, knee at $12,000, **0 conversions** — at the FEC cap the money-response shift (<1 point on typical receipts) cannot cross DTHRESH; conversions are reachable only for scenario-scale shocks (§7.B), which is the economically honest behavior. Output path is env-overridable (`OPT_OUT`) so audit test-runs no longer clobber the production `optimize_result.json`; the per-chunk cap check now requires room for a FULL chunk (`cu+INC ≤ cu0+PMAX`), so the FEC limit can never be overshot when INC∤PMAX.

> **⚠ AUDIT NOTE 10.A (MEDIUM):** `contrib = Σ tgt(m)` banks the member at **certainty using their pre-conversion stance weights** `PERS[old tier]`, not the champion weight (PERS 0.20) they should hold after converting. The net jump (contrib − partial ≈ +0.063 for Hoeven) is small and **positive**, so monotonicity holds, but the banked magnitude uses stale weights.

> **⚠ AUDIT NOTE 10.B (MEDIUM):** the diminishing-returns **knee detector is effectively non-functional** at production settings. Because `INC=100k` is spread across ~20 distinct fresh members (each member's first chunk has a similar marginal ≈ 0.75–0.9), no chunk's marginal falls below 20% of peak, so the knee = full budget every time (verified: reported knee $2,000,000). Also the per-step marginals are **not monotone** (spike at the conversion step: 0.918→1.237), which is correct economically (a conversion is a discrete gain) but breaks the "peak marginal" assumption the knee math relies on.

---

## 11. Constants table

| Constant | Value | Set in | Env-tunable | Meaning |
|---|---|---|---|---|
| WM | **0.35** | flip_model, per_topic_flip | no | money channel weight in pflip (CALIBRATED 0.6→0.35: money is the minority partner — buys access, not votes) |
| WP | **0.65** | flip_model, per_topic_flip | no | network channel weight in pflip (CALIBRATED 0.4→0.65) |
| HALFF | 0.10 | flip_model, per_topic_flip | `HALFF` | pflip money half-saturation (×receipts) |
| BASE | 0.15 | flip_model, per_topic_flip (`0.15` literal in coalition mods) | no | strategic-score weight in tgt |
| PERS['—'] | **0.50** | flip_model, per_topic_flip | `PERS_NONE` | persuadability of a silent member (≈ True Neutral) |
| SRCPRO / SRCANTI | **1.7 / 0.5** | **FLIP family only** (flip_model, per_topic_flip) | no | SOURCE-ALIGNMENT in nA/nB: co-partisan pressure ×1.7, out-partisan ×0.5, else ×1.0 (corrected 2026-07-01 — NOT unified across all 7) |
| DCROSS damping | 0.4+0.6·√(bpf·bpf) | DIFFUSION family (scenario, budget_frontier, per_topic_coalition, cosponsor_route, lt_priming) | no | cross-party edge damping in the cascade/route kernels (homophily); same-party ×1.0 |
| passage bonus | **0.3** | flip_model, per_topic_flip (`tgt`) | no | always-on ×(1+0.3·bpf) strategic-value boost (Volden-Wiseman); `--bridge` replaces it with GAMMA |
| BETA_C | 0.8 | per_topic_coalition | no | bridge seed-budget boost (coalition only) |
| edge `+` const | **6.0** | all cascade/route modules | no | edge-prob half-saturation weight (CALIBRATED 4.0→6.0) |
| BSCALE | **400000** | scenario, budget_frontier, per_topic_coalition | no | bystander activation scale (CALIBRATED 350k→400k) |
| CAP | 50000 | flip_model, per_topic_flip, frontier, coalition | no | per-member/per-seed cost cap (flip/coalition layers) |
| BUDGET | **2,500,000 (optimize)** / 2,000,000 (per-topic) | optimize / per_topic_flip, coalition | `BUDGET` | **THE joint allocation = optimize.py at $2.5M total (user 2026-07-01)**; per-topic $2M runs are per-issue diagnostics, not additive budgets |
| INC | **1000 (flip) / 500 (optimize)** | per_topic_flip / optimize | `INC` | allocation chunk (optimize CALIBRATED 100k→500 = realistic contribution step) |
| PMAX | **10000** | optimize | `PMAX` | optimizer per-member cap (CALIBRATED 300k→10k = FEC PAC→candidate per-cycle legal limit) |
| DTHRESH | **11.25** | money_response (+ dashboard engine const) | `DTHRESH` | net-lean shift to risk defection. RESCALED 25→11.25 (2026-07-01): 25 was calibrated under MAXSHIFT=40; at MAXSHIFT=18 the curve's ceiling fell below it, making defection impossible. 11.25 = 18·(1/6)/((1/6)+0.1) preserves the original boundary (donation ≥ ~1/6 receipts) |
| MAXSHIFT | **18** | money_response, lt_priming | `MAXSHIFT` | max net-lean points per donation (CALIBRATED 40→18) |
| HALF | 0.10 | money_response, lt_priming | `HALF` | money-curve half-saturation (×receipts) |
| RFLOOR | 200000 | money_response, lt_priming, flip_model, per_topic_flip | no | receipts floor for *real small* fundraisers; **receipts=0 (no FEC record) is imputed to the MEDIAN**, not floored (HIGH-2 fix — see §7.1; ported to lt_priming 2026-07-01, which had been missed) |
| REPFAC | 0.6 | budget_frontier | `REPFAC` | contest-play primary-feasibility discount |
| LELEV | **0.8** | build_electoral | `LELEV` | electoral leverage strength (CALIBRATED 0.6→0.8) |
| GAMMA | 1.2 | per_topic_flip | no | `--bridge` target boost |
| K | 5 | cosponsor_route | `K` | recruiter out-degree budget |
| CEDGE | 10000 | cosponsor_route, lt_priming | `CEDGE` | base $/recruitment ask |
| CONV_MAXSTEP | 1 | scenario, optimize | `CONV_MAXSTEP` | max fine-tier move per conversion |
| MC | 40 (scenario/route) / 20 (frontier/coalition) | various | `MC` | cascade iterations |
| SEED | 7 | all stochastic modules | `SEED` | RNG seed |
| MAXSEEDS | 60 | budget_frontier | `MAXSEEDS` | max frontier seeds |
| _imed (H3) | 12000 | flip_model, money_response, per_topic_flip | no (data-derived) | imputed industry median |
| score col | 19 | all (Blended Model) | no | composite strategic score |
| member rows | 3…535 | all workbook reads | no | the 533 members |

---

## 12. Worked example — `pflip` for a real member

**John Hoeven (R-ND), topic = Interchange.** From `congestion.json`: `cu=0, banks=1000, finserv=1000` → `ind=2000` (real, not imputed; `total=2000>0`). `receipts=530750 → R=530750`. From the topic setup on the live stance matrix: `nA=0.000` (no pro neighbors on Interchange), `nB=0.318`, `mAt=6.350`, `mBt=4.867`. Constants `WM=0.6, WP=0.4, HALFF=0.10`.

```
a = 0.6·(0+1)/((0+1)+0.10·530750)            + 0.4·0/6.350
  = 0.6·1/53076                              + 0
  = 0.0000113                                + 0           = 0.0000113

b = 0.6·(2000+1)/((2000+1)+0.10·530750)      + 0.4·0.318/4.867
  = 0.6·2001/55076                           + 0.4·0.0653
  = 0.021799                                 + 0.026137     = 0.047936

pflip = a/(a+b) = 0.0000113 / 0.047947 = 0.000236
```
Hoeven is (correctly) near-zero winnable on Interchange: no CU money, real industry money, zero pro-neighbors. The `+1` smoothing keeps `a>0` (no division-by-zero, no false `pflip≈1`).

**Now add $100k CU** (`al=100000`):
```
a' = 0.6·(0+100000+1)/((100001)+53075) + 0 = 0.6·100001/153076 = 0.39196
pflip' = 0.39196/(0.39196+0.047936) = 0.8911
```
A $100k CU chunk moves Hoeven sharply up on Interchange winnability — and because $100k = ~18.8% of his receipts, the money-response shift is `dlean = 18·(0.188)/(0.188+0.10) = 11.76 > DTHRESH 11.25`, so a scenario-scale $100k shock **converts** him one tier. (At the optimizer's $10k FEC cap, `dlean ≈ 1.5` — far below threshold; conversions live in the scenario layer, not the capped allocator.)

---

## 13. Data integrity summary

| Check | Result |
|---|---|
| Member-set size | 533 across congestion.json, category_stance, all 3 workbook sheets — **exact** |
| Duplicate names | 0 |
| Workbook row alignment | rows 3–535, no header bleed, no row-536 spill — **correct** |
| category_stance dimensions | 533 × 18 (17 + CU Tax Status scaffold), all members exactly 18 categories |
| congestion ↔ category_stance | identical member sets (0 in-one-not-other) |
| money-field nulls | none null; zero-or-null: cu 24%, banks 23%, finserv 50%, receipts 3.4%, total 12% |
| H3 imputation | trigger = receipts=0 (no FEC record, 18 blind members); imputed to median industry; **0 in top-50** — **correct** |
| ind=0 with a record | **91 members** raised money but $0 from the 33 tracked major bank/finserv PACs — **FEC-verified-real** (not a gap); trusted, not imputed (was Finding HIGH-3) |
| receipts floored | 18 members (<200k or null) → 200000 |
| bipartisan coverage | 533/533 explicit |
| network coverage | **only 492/533 members in network; 41 isolated (0 edges)**; 340/2214 edge rows reference non-members (dropped) |
| electoral match | 503/533 (30 default-neutral) |
| BLOCKCAT map | byte-identical across 4 modules, 18 blocks, CFPB 99+145 both present |

---

## 14. Research basis

- **Noble & Turner 2024 — Presidential Leadership and Legislative Polarization.** Going-public salience shock: party-base pressure regimes (rally/retreat/backfire), gridlock widening (Prop 1), defensive appeals (Prop 2), polarization/uncertainty/electoral-strength statics → §15.1.
- **Malaterre & Lareau 2024 (Data & Policy) — Hidden communities of interest.** Topic-profile correlation networks + Louvain + Hellinger genealogies → §15.2.
- **Fink et al. 2023 (Data in Brief) — Congressional Twitter influence network.** Empirical pairwise influence probabilities for the Independent Cascade; normalization + minimum-activity floor → §15.3.
- **Zhou & Elejalde 2026 (IP&M) — TWLGCN.** Temporal stance dynamics: snapshot persistence, seven-dynamics taxonomy, flip curves, silent-actor inference w/ masking validation → §15.4.
- **Joo & Steinert-Threlkeld 2022 (CCR) — Image as Data.** Duplication-rate frame alignment + χ² label-party association, text analog → §15.5.
- **Steinert-Threlkeld — Twitter as Data (Cambridge).** Mining-scope survey grounding the press-as-elite-communication framing of §15.2–15.5.
- **Bharathi, Kempe & Salek — Competitive Influence Maximization.** The pro(A)/anti(B) first-to-reach coloring in §5 is their competing-diffusion model. CU spread = expected A-coloring.
- **Golovin & Krause — Adaptive Submodularity.** §10's "allocate → observe conversion → re-optimize" is an adaptive policy; the lazy/CELF greedy carries the (1−1/e) guarantee into the adaptive setting. (CELF==exhaustive verified.)
- **RELINK — Closed-Network Influence Maximization (CIKM'25)** (`research/4_Closed_Network_IM_CIKM25_temp.pdf`). Edge-activation IM under a per-member out-degree budget → the §8 co-sponsor route finder (the `K` whip budget).
- **Multi-Objective Path-Based D\* Lite** (`research/Multi-Objective_Path-Based_D_Lite.pdf`). Incremental multi-objective path planning → the Pareto routes (§8) and the incremental sheet-sync (recompute only changed slices).

---

*Specification **corrected 2026-07-01** after the deep-dive audit. Changes in this revision: (1) the false
"L4 cpf unification" claim replaced with the true two-kernel design (§3.3); (2) the always-on ×(1+0.3·bpf)
passage bonus restored to §3.6; (3) §7.2 defection rule — DTHRESH rescaled 25→11.25 (the 25 threshold had made
money defection mathematically impossible at MAXSHIFT 18) and the PROJ ladder→ORDER projection added (79% of
members had been vocabulary-immune); (4) §8 route kernel +4→+6; (5) §9 THETA updated to the widened live values
and lt_priming's median-imputation port noted; (6) §10 refreshed with the current $2M run (120.17→145.44),
OPT_OUT, and the strict full-chunk FEC-cap check. The earlier 2026-06-29 refresh had itself introduced errors
(1), (2), (4), (5) — **the live code in `fec/*.py` remains the source of truth; verify constants there before
citing this document.***

> **⚠ One spot still cites pre-calibration numbers:** the **§12 worked example** uses WM 0.6 in its `pflip`
> arithmetic — recompute with WM 0.35 / WP 0.65 for exact current values (the qualitative conclusion — Hoeven
> near-zero-winnable on Interchange — is unchanged; the defection line WAS recomputed for MAXSHIFT 18 /
> DTHRESH 11.25). Documentation-only.*

*All "verified" claims were reproduced by independent Python during the audits of 2026-06-29 and 2026-07-01.*


## 15. Salience shock + press SNA layers (2026-07-01 build)

### 15.1 Going-public salience shock (`salience_shock.py`, dashboard exec cue) — Noble & Turner 2024
Replaces the flat exec-cue dial (oppose ×1.6 / support ×0.6 on opposition-bystander mobilization) with the
Noble–Turner structure. Per issue *c*, estimated from the stance matrix (never hand-set):
- **z_c** (sincere polarization) = |mean D tier-score − mean R tier-score|, tier scores C3/F2.5/A2/H1/T0/L−1/S−2/O−3;
- **ψ_c** (policy uncertainty) = share of members with no established posture (+0.3·TN share);
- regime probabilities: **b** = min(0.35, 0.05+0.10ψ) backfire, **P(rally)** = (1−b)(1−z/3), **P(retreat)** = (1−b)(z/3).
A campaign by actor party *A* applies party-asymmetric fine-ladder nudges (β_co > β_out always; terminal
rungs immune; electoral-play members ×1.35 "gambling for reelection", their A.4): rally = co +1 toward,
cross-pressured out (bpf ≥ 0.30) +1; retreat = co +1 toward, out −1 away; backfire = both away, co with a live
race hold (δ dominates the base). Reported: expected Δspread (cascade), Δ remaining-pool winnability,
persuadable-band occupancy (their Prop 1 gridlock-widening), and the **defensive-appeal channel** (their Prop 2 /
Eq. 1): while a co-partisan appeal is live, co-partisan defection needs dlean ≥ DTHRESH·(1+δ/2), δ=0.5 →
"fair-weather allies held" vs a $250k competitor probe. `--advise` ranks all issues (opportunity-cost verdict is
RELATIVE — top quartile GO PUBLIC): flagship result: **Credit Card Mandates** loses −2.4 expected cascade
cosponsors from going loud but **holds 8 fair-weather allies** — the Manchin-abortion defensive appeal mapped to
the CU tax/interchange fights. Dashboard: `engine.sal[issue]` + `EXECP`; exec cue multipliers
oppose: co 1+0.8(p+q), out 1+0.8(p−q−b); support: co 1−0.7(p+q), out 1−0.7(p−q−b) — on polarized issues an exec
SUPPORT cue counter-mobilizes out-party bystanders (Lee 2009 retreat). Old flat dial = special case p=1,q=b=0.
Outputs: `salience_advisory.json`.

### 15.2 Hidden communities of interest (`press_hcoi.py`) — Malaterre & Lareau 2024
Member topic profile = recency-weighted distribution of his/her press across the 19 categories (multi-label
split evenly); members ≥3 weighted items; Pearson r ≥ 0.6 edges; Louvain (seed 7) → 8 interpretable
communities (e.g. a CU-Bank-Dynamics + Credit-Card-Mandates defensive-fight community) with community topic
profiles; diachronic genealogy across the median-date split via Hellinger distance (persist < 0.25 < drift <
0.45 < novel — an Interchange community EMERGES in period 2). Partially repairs D4: 4/41 cosponsor-isolated
members (incl. Scalise, Jason Smith) get community placement. Output `press_hcoi.json` (candidate 2nd cascade
layer — adoption is a user decision).

### 15.3 Press engagement layer (`press_engagement_layer.py`) — Fink et al. 2023 + Danowski & Cepela 2010
Empirical influence probabilities from press-title co-actor mentions, Fink-normalized:
P(i→j) = (# of j's items naming i) / (# items by i), source floor ≥5 items (their ≥100-tweets analog).
Precision-first extraction: full-name match OR honorific chain (Sen./Rep./Chair… + surname list); never
self/ambiguous/short surnames (kills the headline-case 'Banks'/'Flood'/'Young' false positives). 78 directed
edges; 26% coincide with cosponsor edges (independent confirmation). Output `press_engagement.json`.

### 15.4 Stance dynamics (`stance_dynamics.py`) — Zhou & Elejalde 2026 (TWLGCN design, sans GNN)
Quarterly (91d) member stance trajectories p_m,t ∈ [−1,1] (conf-weighted stance_sign) with persistence
carry-forward (their silent-user embedding persistence). Seven-dynamics taxonomy per transition (their Sec 5.2;
static band = median+MAD over observed→observed transitions, floor 0.05): static / O→MO / O→LO / O→S / S→O /
S→LS / S→MS. Flip curves per window (their mirror-curve external-event detector; peak flip window 2025-07).
Neighbor co-movement: **null on both layers** (cosponsor 52%, HCoI 49% — the Twitter homophily does not
replicate at quarterly press resolution; honest null). Silent-member proposals: network-neighbor collaborative
filtering (≥5 informative neighbors, |est| ≥ 0.75) → `stance_imputation_proposals.csv` with provenance —
**matrix untouched, user adjudicates**; masking validation 77% sign agreement on known cells.

### 15.5 Frame alignment (`frame_alignment.py`) — Joo & Steinert-Threlkeld 2022
Their image-duplication frame-alignment metric, text analog: share of items near-duplicated by ANOTHER member
(3-word-shingle Jaccard ≥ 0.5) per issue/party. CU Tax Status = 65% duplication (the Venezuela-state-violence
analog: one coordinated script), General CU 60%, vs Defense CU 12%. Bottom-up party framing (their Tables 1–2
χ²): D frames via CU-Bank Competitive Dynamics (χ²=128), Mortgage/Housing, Credit-Card Mandates; R via General
CU, Technology & Emerging. Output `frame_alignment.json`.

All five modules audited (audit_full [NEW] block, 8 checks; total 40).

### 15.6 Multilayer integration (`build_multilayer_network.py`) — LIVE 2026-07-01
The press layers feed the production cascade via `congress_cosponsor_network_AUG<date>.xlsx`, written in
the exact Edges format all nine loaders glob by mtime — zero loader changes, **revert = delete the AUG
file**. Policy: cosponsor edges verbatim (never modified); engagement edges added at kernel-inverse weight
w = 6p/(1−p) (cap 2.0 — the one layer whose weights are already empirical probabilities, Fink et al.);
HCoI edges added ONLY when incident to a cosponsor-isolated member (weight 0.6·r·0.2 ≤ 0.12, a weak
interest-affinity tie) — the surgical D4 fix, not a density explosion. Result: +55 engagement, +59 HCoI
edges; 4/41 formerly-unreachable members (incl. Scalise, Jason Smith) now cascade-reachable; full pipeline
regenerated and the 40-check audit passes on the augmented graph. Provenance sheet inside the xlsx.
Dashboard also surfaces the go-public advisory verdict per issue (engine.adv) in the System-shocks panel,
and `salience_shock.py --intensity auto` scales campaign strength by the measured frame alignment (§15.5).

### 15.7 Stance-template cross-validation + social-media collector (2026-07-01)
`stance_template_xval.py` → `stance_templates_review.md`: collates the four template artifacts
(T1 cu_stance_label_set.csv, T2 api_prelabel SYSTEM factorization+priors, T3 bill_directions.csv,
T4 gold_label_queue.csv). Findings: T1 pre-vs-human κ=0.529 / 70.1% (below the 0.81–0.94 clean-template
bar; dominant error = implicit support read as neutral, n=78); T2×T3 valence priors CONSISTENT (CFPB
49 pro-restraint/5 anti; Interchange+CCM defensive ✓); T1×T4 overlap comparison is flagged CIRCULAR
(all 95 overlap rows have stance_src=human_label) — the clean benchmark is user-adjudicated gold_* via
stance_eval.py. Also emits `stance_template_variants.csv` (45 Burnham synonymous-hypothesis paraphrases
for the S3 NLI layer — user-editable).
`tweet_collector.py` + `social_media.db` (SQLite, WAL, idempotent upserts, per-handle checkpoints):
members/posts/interactions/fetch_log tables; X API v2 adapter (needs paid X_BEARER_TOKEN — the Fink-era
free academic track is gone), keyless Bluesky adapter (public AppView), `discover-bluesky` handle probe
(domain-verified senate.gov/house.gov handles auto-accepted; pattern hits flagged UNVERIFIED),
`build-influence` = Fink-normalized influence network → `tweet_influence.json` (feedable to the
multilayer builder). Seeded 515/533 members, 502 X handles, from unitedstates/congress-legislators.

### 15.8 Domain stance classifier + collection structure (2026-07-01, Khan et al. TACS 2025)
Khan et al. (IECE TACS 2025, VERIFIED from the PDF this time: Roman Urdu political tweets, 8,374 items,
agree/disagree/unrelated, classical TF-IDF models RF 95% > SVM 94% > LogReg 93% > DT 92% > NB 89%,
fine-tuned RoBERTa 97% with paired [CLS] context [SEP] text [SEP] input, augmentation + class balancing,
3 annotators + agreement) — pipeline transplanted to the CU domain:
- **Training data** = the user's `cu_stance_label_set_AUGMENTED.xlsx` (two-hop redesign: hop1 member→target,
  hop2 ACU→target from the bills table, composed = human_label; train 456 / test 87 / exclude 9; Sheet 3 =
  21 oppose candidates to grow the rare class) fused with full text_snippets → `stance_training.jsonl`
  (`prepare_stance_training.py`).
- **`train_stance_domain.py`**: TF-IDF (1–2gram) + LogReg/LinearSVM/RF/NB/DT with class_weight=balanced,
  target+speaker-conditioned input ("target: CFPB. speaker: member. …" — Stanceformer/Burnham conditioning);
  `--transformer` fine-tunes distilroberta (default; `--model roberta-base` = paper-exact) with
  inverse-frequency loss weights. `--save` → `stance_clf_composed.pkl` / `stance_ft_composed/`.
- **BENCHMARKS (user-adjudicated gold, first clean numbers)**: on the 312-item balanced queue —
  DEBATE macro-F1 **0.430** (acc 57%, no unrelated class, ACU channel 0.26) vs API factorization pass
  **0.750** (title-only; own-domain 0.82). On the user's own 87-row test split (full text):
  LinearSVM **0.792** macro-F1 best classical. The API pre-seed survived adjudication on 235/312 rows
  (75% — user corrected 77).
- **Collection structure** (Khan two-channel + platform reality): `tweet_collector.py` now covers
  account timelines (X paid / Bluesky keyless / **Truth Social** via Mastodon-fork API, TRUTH_TOKEN env,
  R-skewed coverage mirroring Bluesky's D skew — use both) + domain keyword search (`search` cmd, X
  recent-search with CU_TERMS query). `classify` cmd scores collected posts with the saved classifier +
  CU_TERMS relevance filter (344/573 labeled articles flagged, sanity-checked) →
  `social_stance_signals.json` — a NEW provenance-tagged evidence channel; adoption = user decision.
