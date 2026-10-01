# Pre-registration: FEC relational exposure × REBUILT LDA attention (bridge, round 2)

STATUS: LOCKED

Lock date 2026-08-01 (pre-collection ordering: locked while the 2022 filing fetch is
still in flight and before any instrument×criterion pairing exists anywhere).
Authorized by Paul's directive, verbatim: "While that is going can we run to see if
there is statistical significance between FEC donations and lobbying?" — routed through
the prereg discipline per the house constitution. Successor to
`fec_lda_bridge_prereg.md` (VOID-FOR-COVERAGE, look never consumed): the Y-instrument
is MATERIALLY NEW — our own primary-source network rebuild (construction ratified by
Paul 2026-08-01, "if you can confidently improve it, fuck them lets go"), whose
2021 cross-validation against LobbyView proved the construction (BECU 181/181;
308/329 common; every delta receipted). The look script `fec/fec_lda_bridge2_look.py`
rides this same commit. Codex is BARRED from `--look`; only a Claude session runs it.

## What this look is — and is not

CORROBORATION look, identical epistemics to round 1: does industry committee-path
money co-rank with industry lobbying attention, org-exactly, 2021–2022? Power honesty
unchanged (pooled N≈70–82 expected; p<.05 detection threshold ρ≈.18–.20; ~75–80% power
against true ρ=.30). A MISS is recorded as "UNCORROBORATED," never "disproven."
No outcome measures stance, votes, or persuasion; the standing target-side-money-prior
caveat survives every outcome.

## Compliance with recorded closures

Round 1's closure clause barred re-locks "on this vintage" of the LOBBYVIEW network
table and any re-weighting of its crosswalk against that table. This round changes the
Y-INSTRUMENT, not the weighting: Y is our rebuilt network from Senate LDA primary
source + GovInfo BILLSTATUS, a different measurement instrument with its own validated
construction. The round-1 prereg, its VOID record, and its display-language rule
(no "predictor" framing absent a passing look) remain untouched unless this look's
pre-declared consequences fire. No big5 claim, engine, rank, or ratified constant is
touched by any outcome.

## Hypothesis and honest prior

H: unchanged from round 1 — within an industry, members receiving more of the
industry's one-hop relational money (FEC, 2021-2022 cycle) receive more of that
industry's lobbying attention (our network n_bills, 2021+2022), org-exactly.

Honest prior MODERATE for fintech/crypto, LOW-MODERATE for credit_union (3/10 direct
lobbyists). Adverse priors carried forward verbatim from round 1 (57% congestion sign
agreement; relational = minority channel after IE removal; single-cycle cross-section;
X truncation at top-100; the volume confound). New adverse prior: our Y is
formal-citation + title-matched attention only — a client lobbying a bill our channels
cannot see (26/117 pinned filings carried formal identifiers in 2021; titles cover
part of the rest) yields Y=0, attenuating any true association toward zero. This
biases AGAINST passing, never toward it.

## Roster, stratum, crosswalk, Y-instrument

X: `fec_opposition_prior.json` per-member
`associated_by_industry[i]["2021-2022"]["assoc_relational_used"]` — the ratified
floored relational basis. In-roster X>0 counts (computed X-side-only, 2026-07-31,
artifact unchanged since): credit_union 30, fintech 30, crypto 22.

Y: `our_network_2021.csv` and `our_network_2022.csv`, **STRICT mode** (primary),
produced by `fec/build_network_2021_rebuild.py` @37d83ee semantics: formal citations
+ unambiguous titles, stale citations resolved to original congress, sponsor-or-
cosponsor people-sets, distinct-bill counting. Y(m, i) = Σ n_bills over the pinned
lob_ids of industry i across years 2021+2022; absent dyad = 0; Y=0 members STAY;
X=0 members EXCLUDED (truncation artifact). The GENEROUS-mode Y is a firewalled
secondary only.

Crosswalk: the identical 22 lob_ids pinned in round 1 (verbatim list incorporated by
reference from `fec_lda_bridge_prereg.md`; same truncated-prefix table; the rebuild
keys clients by the same UUIDs since its worklists derive from the entity-resolved
reports table).

Industry entry rule: unchanged — ≥3 pinned lob_ids with ≥1 network row (our table)
in 2021–2022 AND ≥1 in-roster member with X>0; every candidate industry's entry
status reported; coverage-limited industries get no pairing.

VOID-FOR-COVERAGE (look NOT consumed): pooled pairs < 40 OR entering industries < 2,
computed before any correlation.

## Input fingerprints

Pinned NOW: `fec_opposition_prior.json` SHA-256
CE3136A896CFA2E86CF80B68227825F863EAD1C605C6A1C1B189DDAFAA9EDED4, members 363
(unchanged since round 1 — re-verified at lock).

Pinned at COLLECTION RECORD (the only permitted post-lock edit before the RESULT,
Vote-Smart pattern, because the 2022 filings are still downloading at lock time):
SHA-256 + row counts of `our_network_2021.csv` and `our_network_2022.csv` (strict),
plus the rebuild receipts' filings-parsed counts for both years. The look aborts
without consuming on any mismatch, absence, or a COLLECTION RECORD that has not been
appended.

## Instrument / machinery

`fec/fec_lda_bridge2_look.py`, same commit — the round-1 machinery (adversarially
reviewed then; two independent statistic implementations with no shared helpers;
integer-exact permutation exceedance; post-parse re-hash; allow_abbrev off) with only
these deltas, complete list: Y-source = the two strict CSVs (same header schema as
network.csv); fingerprint pins per this prereg (prior pinned in code, network CSVs
read from the COLLECTION RECORD section of this file at runtime); RESULT heading
RESULT-BRIDGE2; gates target this prereg file. Statistics unchanged: within-industry
average ranks; pooled Spearman ρ; exact within-industry permutation p (K=5000, seed
87001); volume control = within-industry rank of member total attention across ALL
clients in OUR full network output for 2021+2022; partial via rank-residuals;
1e-9 / exact-p dual-implementation agreement; DEFECT HALT on disagreement.

## Bars (identical to round 1, set before any pairing exists)

1. Pooled Spearman ρ ≥ +0.20 AND exact permutation p < .05.
2. Volume-gated partial ≥ +0.10.
STRONG tier: ρ ≥ +0.40 AND p < .01 AND partial ≥ +0.20.

## Simulate battery

Identical construction to round 1 (rank-z space; seeds 424242/535353/646464/757575;
planted λ-bisection to pooled ρ∈[.32,.38]; null permutation; confound-only refused by
bar-2; true+confound admitted; single ε draw per check; (d) failure = honest
retirement). Output recorded verbatim in an addendum, pass or fail.

## Pre-declared consequences (wording fixed now)

- STRONG: "FEC relational exposure is STRONGLY CORROBORATED (2021–22, org-exact, our
  instrument) as a cross-sectional proxy for LDA lobbying attention." Consequence: the
  bridge candidate generator may be built (`fec_lda_bridge.json.candidate`,
  current-cycle exposure → projected attention rank, tagged fec-bridge), consumed by
  NOTHING until Paul promotes; projection language only as "projected
  lobbying-attention rank, corroborated at 2021–22."
- CORROBORATED: candidate permitted; labels must read "directionally corroborated
  (weak)"; unqualified "predictor" barred.
- UNCORROBORATED: "FEC exposure remains a target-side money prior ONLY and must NOT
  be presented as a lobbying-relationship predictor or projection." Route CLOSED for
  the 2021–2022 window on THIS instrument; closure covers crosswalk re-weighting,
  rank-vs-dollar transform swaps, X=0-inclusive variants, and generous-mode
  re-scoring. Successor only on a window extending past 2022 with fresh fingerprints.
- FRAGILE = MISS: statistics (date line excluded) must reproduce exactly on verbatim
  rerun; else MISS for all consequences including closure.
- VOID-FOR-COVERAGE: not consumed; successor may relax only entry rule or floor.

## COLLECTION RECORD

Appended 2026-08-01 per the pre-declared exception; amended once, same session,
BEFORE any battery or look consumed anything: the first record was collected
against the finance-classified worklist, which name-rule-excludes most pinned
fintech/crypto orgs (they classify as nonfinancial "other") — a collection-scope
defect on my side, corrected by the union worklist (finance ∪ pinned-22,
2021–2022; 7,970 records, 0 unresolved failures, manifest
fec_lda_filings_manifest_union_bridge2_worklist.json). Rebuild @ forward-binding
stale rule, tests 21/21. Final pins:

our_network_2021_strict.csv SHA-256 3015BBA40DB71E1B78AA814427D0DD2B496EE98D91131DBDDC2EBD55B16F7796 rows 19191
our_network_2022_strict.csv SHA-256 F70CDB1225C6B7A53AF9BCBEC0ADC038C6CFB728CB695A3EAA8D73A621118740 rows 20156

## No-status-change clause; secondaries; stopping rule; look gate

All identical to round 1, incorporated by reference with these substitutions:
RESULT-BRIDGE2 heading; secondaries add the generous-mode pooled ρ (firewalled,
grounds nothing). One look. No bar, seed, roster, crosswalk, or wording change after
the lock commit; battery refusal retires with a pinned successor condition; the gate
refuses on: file absent, LOCKED absent, newline-anchored `## RESULT-BRIDGE2` present,
fingerprint drift, COLLECTION RECORD absent/malformed, battery failure, non-`--look`
invocation of the real path. `--simulate` = battery only; no-arg = status.

## BATTERY-BRIDGE2
- battery PASS
- planted lambda: 2.242822582521
- PLANTED seed 424242: check=PASS; impl1 rho=+0.349956030292, p=0.016996600680, partial=+0.334987413400; impl2 rho=+0.349956030292, p=0.016996600680, partial=+0.334987413400
- NULL seed 535353: check=PASS; impl1 rho=+0.182976877638, p=0.194561087782, partial=+0.224621703728; impl2 rho=+0.182976877638, p=0.194561087782, partial=+0.224621703728
- CONFOUND-ONLY seed 646464: check=PASS; impl1 rho=+0.240226091893, p=0.097780443911, partial=+0.039228926059; impl2 rho=+0.240226091893, p=0.097780443911, partial=+0.039228926059
- TRUE+CONFOUND seed 757575: check=PASS; impl1 rho=+0.317531043005, p=0.029994001200, partial=+0.258058478342; impl2 rho=+0.317531043005, p=0.029994001200, partial=+0.258058478342
- look eligibility: battery admitted

## RESULT-BRIDGE2
- date: 2026-08-01
- pooled N: 52
- entering industries:
  - credit_union: coverage-limited: active_orgs<3
  - fintech: entered; pairs=30, active_orgs=3
  - crypto: entered; pairs=22, active_orgs=4
- pooled Spearman rho: +0.258665430665
- exact within-industry permutation p: 0.098380323935 (K=5000, seed=87001)
- volume-controlled partial Spearman: +0.169843257534
- tier: UNCORROBORATED
- consequence (fixed wording): FEC exposure remains a target-side money prior ONLY and must NOT be presented as a lobbying-relationship predictor or projection.
- implementation 1: rho=+0.258665430665, p=0.098380323935, partial=+0.169843257534
- implementation 2: rho=+0.258665430665, p=0.098380323935, partial=+0.169843257534
- battery summary: PASS; lambda=2.242822582521; all four locked checks PASS
- secondaries (firewalled; ground nothing):
  - fintech: impl1 rho=+0.284222812706, p=0.067586482703; impl2 rho=+0.284222812706, p=0.067586482703
  - crypto: impl1 rho=+0.000737670969, p=0.490501899620; impl2 rho=+0.000737670969, p=0.490501899620
  - top-25 Jaccard X-rank vs Y-rank: impl1=0.250000000000; impl2=0.250000000000
  - X=0-inclusive sensitivity rho: impl1=-0.019890788969; impl2=-0.019890788969
  - generous-mode pooled rho (firewalled; grounds nothing): impl1=+0.248215039639; impl2=+0.248215039639
  - ours-vs-opposition asymmetry note: credit_union is the ours stratum; fintech and crypto are opposition strata; their firewalled industry statistics ground no claim
  - 2021 split rho: impl1=+0.273750672972; impl2=+0.273750672972
  - 2022 split rho: impl1=+0.258740614028; impl2=+0.258740614028
