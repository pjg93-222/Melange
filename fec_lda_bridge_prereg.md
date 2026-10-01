# Pre-registration: FEC relational exposure × LDA lobbying attention (the fec-bridge corroboration look)

STATUS: LOCKED

Lock date 2026-07-31 (late session, committed before any instrument×criterion pairing was
computed). Authorized by Paul's directive, verbatim: "I want you to see if there is a
correlation between how much they donated on FEC and how much they lobbied them. If so, we
can use the current FEC donation record of them as a predictor of their current and
projected relationship with them." Adversarially self-reviewed pre-lock (leniency hunts that
tightened the design: the asymmetric X-zero/Y-zero rule, the ≥3-matched-org entry rule,
the within-industry permutation scheme, and the closure-coverage clause barring crosswalk
re-weighting variants); the look script `fec/fec_lda_bridge_look.py` rides this
same commit, so the constructor is pinned by same-commit code. Codex (the executor lane)
is BARRED from consuming the look; only a Claude session may run `--look`.

## What this look is — and is not

This is a **CORROBORATION look, not a validation look.** It asks whether two independent
money/attention instruments point the same direction at the only overlap window that
exists (2021–2022). Power honesty: at the expected pooled N≈70–82 pairs, the p<.05
detection threshold is Spearman ρ≈.18–.20; power against a true ρ=.30 is ≈75–80%; against
ρ=.20 it is ≈50%. A MISS is therefore recorded as **"UNCORROBORATED," never "disproven"**
— wording fixed here. Nothing in this look measures stance, votes, or persuasion; the
standing caveat "target-side money prior, never a stance or vote predictor" is untouched
by every outcome.

## Compliance with recorded closures

Touches no big5_* prereg, no trait claim, no engine, no rank. Does not reopen: raw-FEC-bulk
(CLOSED by Paul 2026-07-31, "We do not need the raw fec bulk pull"); congestion.json
comparability (the 57% sign-agreement finding stands — different instruments); the IE
removal from headline metrics (this look uses the ratified RELATIONAL basis only). No
outcome changes the ratified interpretation of relational exposure (one-hop upstream
funding channel) or the w_b wiring; on UNCORROBORATED the FEC lane keeps its money-prior
role unchanged.

## Hypothesis and honest prior

H: Within an industry, members who receive more of the industry's one-hop relational
committee-path money (FEC, 2021-2022 cycle) also receive more of that industry's lobbying
attention (LobbyView network `n_bills`, 2021+2022), org-exactly matched.

Honest prior: MODERATE for fintech/crypto (direct-lobbying industries; government-affairs
and PAC/employee money plausibly co-target the same bill sponsors), LOW-MODERATE for
credit_union (only 3/10 sample orgs lobby directly; trade associations carry the rest —
the register holds only ~28% of trade money, mentat-trade-association-gap).

Adverse priors disclosed: (1) congestion.json vs this prior agree on lean sign only 57%
(157/276) — money instruments in this domain routinely disagree; (2) 79.1% of raw
associated exposure was IE/communication money removed from the relational basis — the
tested basis is deliberately the minority channel; (3) single-cycle cross-section, no
temporal replication possible in-window; (4) X is truncated (beneficiary top-100/cycle/view:
X=0 means "not in top-100", not zero) — handled by the exclusion rule below; (5) the
volume confound that has killed multiple routes in this repo: important members attract
ALL money and ALL lobbying — bar-2 exists because of it.

## Roster, stratum, pinned crosswalk

X source: `fec_opposition_prior.json` per-member `associated_by_industry[i]["2021-2022"]
["assoc_relational_used"]` (the ratified floored relational basis, shipped @a120b9d).
In-roster members with X>0: credit_union 30, fintech 30, crypto 22, community_banks 28,
credit_arms 34 (counts computed X-side-only pre-lock, 2026-07-31).

Y source: `network.csv` rows with `year ∈ {2021, 2022}` and `lob_id` in the industry's
pinned org-exact crosswalk below; Y(m) = Σ n_bills. **Absent dyad = 0 by codebook**
("this number will never be zero; missing = no connection") — Y=0 members STAY in the
pairing. X=0 members are EXCLUDED (truncation artifact, not a measured zero). This
asymmetric rule is pinned; an X=0-inclusive read is a firewalled secondary.

Industry entry rule: an industry enters the primary pool iff ≥3 of its pinned lob_ids
have ≥1 network row in 2021–2022 AND ≥1 in-roster member carries X>0 for it (both
computed by the script before any pairing; the RESULT block reports every candidate
industry's entry status, and industries failing entry are reported as coverage-limited
with no pairing computed for them).
community_banks (1 matched org) and credit_arms (1) cannot enter by construction;
credit_union / fintech / crypto are expected to enter.

Pinned crosswalk (FEC workbook roster org → LobbyView lob_id; name-matched pre-lock
against clients.csv vintage 2024-10-25; parents of captive arms deliberately REJECTED;
unmatched = org does not lobby under its own registration in this vintage):

- credit_union (3/10 matched): Boeing Employees Credit Union → d039e7e5-f821…;
  Navy Federal Credit Union → 69c5a9e9-7d79…; Pentagon Federal Credit Union → c27f7c24-43ec….
  Unmatched: Alliant, America First, Golden 1, Mountain America, SchoolsFirst,
  State Employees', Suncoast.
- fintech (9/10 matched): Cash App → {BLOCK, INC. 0f549ea5-9fdb…, SQUARE, INC.
  f2f8dae7-b696…} (same entity, renamed 2021 — both pinned); Chime → 9a33b530-6a10…;
  Dave → 5f438304-3b42…; Kalshi → 18cf487e-9e89…; Klarna → c3dc5b6d-38b1…;
  Plaid → 3f7a52db-9be0…; Robinhood → 4f43f95f-f6f0…; SoFi → 03b1f6cd-0546…;
  Stripe → {b849b9da-67fa…, cb4ac22a-dd82…} (both registrations pinned).
  Unmatched: Polymarket.
- crypto (6/10 matched): Bakkt → dbdd9f97-b360…; Binance → {1c3314d2-e20e… (BAM/Binance.US),
  75d2c2aa-fb94… (Binance Holdings)}; Coinbase → {67e35f81-afa7…, 7ddb0913-d306…};
  Crypto.com → 6904853b-ba69… (Foris DAX); Gemini → 4317e970-8485… (Gemini Trust only —
  the six non-exchange "Gemini" clients rejected); Kraken → 8b517298-a4d4… (Payward).
  Unmatched: Bitnomial, CoinList, MIAXdx, tZero (JETZERO is an aircraft company, rejected).

The look script carries the full-length lob_ids; the truncated forms above are for human
reading. Construct disclosure: X uses ALL TEN sample companies' committee-path money per
industry; Y uses the matched subset's lobbying only — near-complete for fintech (9/10)
and crypto (6/10 incl. every major), thin for credit_union (3/10, disclosed).

## Input fingerprints (look aborts WITHOUT consuming on any mismatch)

- `%LOCALAPPDATA%\Melange\lobbyview\raw\network.csv`
  SHA-256 628F82DFA8EFD1010BEA378CF0C91DDF65AA6BC8EBCBF68A21498ADDEAFE7776,
  data rows 10,937,756, header `lob_id,bioguide_id,year,n_bills`.
- `%LOCALAPPDATA%\Melange\fec_spending\derived\fec_opposition_prior.json`
  SHA-256 CE3136A896CFA2E86CF80B68227825F863EAD1C605C6A1C1B189DDAFAA9EDED4,
  members 363.

## Instrument / machinery

All in `fec/fec_lda_bridge_look.py`, same commit. No LLM calls anywhere (arithmetic only).
New numerics, complete list (nothing else): within-industry average ranks (ties = average
rank); pooled Spearman ρ computed as Pearson on pooled within-industry ranks; exact
permutation p by within-industry shuffles, K=5000, seed 87001, with the exceedance
decision (permuted ≥ observed) computed EXACTLY in integer arithmetic — the permutation
preserves each stratum's rank multiset, so exceedance reduces to comparing integer dot
products of 2×-scaled rank vectors, immune to float tie-classification noise; volume
control = within-industry rank of member total attention Σ n_bills over ALL clients
2021+2022; partial Spearman via rank-residual regression. Re-derivation: every reported
statistic is recomputed by an independent second implementation (separate functions, no
shared helpers) in the same run; ρ/partial/secondaries agree within |Δ| ≤ 1e-9 and p
agrees exactly (both implementations use the integer exceedance rule independently); any
violation = DEFECT HALT, nothing recorded, look not consumed. The script also emits the
pre-declared consequence sentence for the achieved tier verbatim in its RESULT block, and
re-hashes both inputs after parsing and before statistics (abort without consuming on
drift).

## Bars (all-must-hold for CORROBORATED; set once, before any pairing exists)

1. Pooled Spearman ρ ≥ +0.20 AND exact permutation p < .05.
2. Volume-gated partial (controlling total-attention rank) ≥ +0.10.

STRONG tier additionally: ρ ≥ +0.40 AND p < .01 AND partial ≥ +0.20.
VOID-FOR-COVERAGE (look NOT consumed): pooled pairs < 40 OR entering industries < 2 —
computed before any correlation, Vote-Smart ordering.

## Simulate battery (in-process before the look; refusal = RETIRED WITHOUT A LOOK)

Synthetic Y only; real pairing never computed in simulate. Constructed on the real X
margins of the entering industries:
All constructions operate in within-industry rank-z space (ranks standardized to mean 0,
sd 1 within industry); ε denotes i.i.d. standard Gaussian draws from the stated seed,
drawn once per check:
(a) PLANTED, seed 424242: Y_syn = z(X-rank) + λ·ε with λ calibrated by deterministic
    bisection (domain λ ∈ [0.5, 8], 60 iterations, ε fixed) so pooled Spearman(X, Y_syn)
    lands in [.32, .38] — must clear bar-1.
(b) NULL, seed 535353: within-industry permutation of (a)'s final Y_syn — must NOT
    clear bar-1.
(c) CONFOUND-ONLY, seed 646464: Y_syn = z(total-attention rank) + 0.15·ε — bar-2 MUST
    refuse (partial < +0.10). Disclosed leak: this check pairs X with a function of the
    real total-attention vector, revealing the confound-path magnitude only, never
    pinned-org Y.
(d) TRUE+CONFOUND, seed 757575: Y_syn = z_planted + 0.75·z(total-attention rank) +
    0.15·ε, where z_planted is a fresh draw (seed 757575) of the (a)-calibrated signal
    construction (same λ) — bars 1 AND 2 must admit (partial ≥ +0.10). If the real
    X↔total-attention dependence is so strong that true signal cannot survive the
    partial, this check fails and the round retires WITHOUT a look — that is the
    designed honest outcome, not a defect.
Battery output recorded verbatim in an addendum, pass or fail.

## Pre-declared consequences (wording fixed now)

- STRONG: "FEC relational exposure is STRONGLY CORROBORATED (2021–22, org-exact) as a
  cross-sectional proxy for LDA lobbying attention." Consequence: a bridge generator may
  be built emitting `fec_lda_bridge.json.candidate` (current-cycle annualized relational
  exposure → projected lobbying-attention rank, confidence-tagged `fec-bridge`),
  **consumed by NOTHING until Paul promotes it**. Projection language permitted only as
  "projected lobbying-attention rank, corroborated at 2021–22."
- CORROBORATED (bars met, not STRONG): same candidate permitted; every display label must
  read "directionally corroborated (weak)"; the unqualified word "predictor" is barred.
- UNCORROBORATED (any bar failed): "FEC exposure remains a target-side money prior ONLY
  and must NOT be presented as a lobbying-relationship predictor or projection." Route
  CLOSED for this window; closure covers ANY re-weighting or subsetting of the pinned
  crosswalk, rank-vs-dollar transform swaps, and X=0-inclusive variants. Successor prereg
  permitted only on a NEW LobbyView vintage extending network coverage past 2022, with
  fresh fingerprints.
- FRAGILE = MISS: re-derivation mismatch already DEFECT-HALTs pre-record; if bars pass
  but any verbatim-rerun of the script (same inputs) fails to reproduce every reported
  STATISTIC exactly (the date line is excluded from the comparison, being the only
  intentionally volatile field), the result is FRAGILE = MISS for all consequences
  including closure.
- VOID-FOR-COVERAGE: not consumed; a successor prereg may relax ONLY the entry rule or
  floor, with fresh fingerprints and its own single look.

## No-status-change clause

No outcome promotes, demotes, or annotates any existing validated claim, any big5 status,
the w_b ratification, or the relational-exposure interpretation. This look grounds exactly
one new claim (the corroboration tier) and nothing else.

## Secondaries (firewalled: reported in the same look, ground NOTHING)

Per-industry ρ and p; top-25 Jaccard overlap between X-rank and Y-rank lists; X=0-inclusive
sensitivity ρ; ours-vs-opposition asymmetry note; 2021-vs-2022 split consistency.

## Stopping rule

One look. On UNCORROBORATED: stop; do not re-specify past this within the 2024-10-25
vintage. On battery refusal: retire, pin the successor condition, stop. No bar, seed,
roster, crosswalk, or wording change after the lock commit.

## Look gate (complete refusal conditions, enforced by the script)

Refuses without consuming when: this file is absent; `STATUS: LOCKED` line absent; a
newline-anchored `## RESULT-BRIDGE` heading already present (one look only); either input
SHA-256 or the network row count or the member count mismatches the pins; the battery
fails in-process; the invoker passes anything other than `--look` for a real run
(`--simulate` = battery only; no-arg = status print). The look runs only under
`if __name__ == "__main__"`. Codex is barred from `--look` by the executor lane's
standing ALWAYS-BARRED list.

## ADDENDUM 1 — VOID-FOR-COVERAGE (2026-08-01, recorded verbatim; look NOT consumed)

Post-lock (@9a1e3a1) `--simulate` printed:

    VOID-FOR-COVERAGE: pooled pairs=0, entering industries=0; look NOT consumed

Side-separate diagnostic (pre-look-legal; no pairing computed): network rows by year
2018–2022 = 598,124 / 865,642 / 1,214,559 / 658,873 / 2,101 — member-level bill linkage
collapses after 2021, the same cliff family as the issue codes. Pinned orgs with ANY
network rows ever: 8 of 22 (BECU 493, Square 616, Block 469, SoFi 197, Stripe 104,
Robinhood 80, PenFed 49, Coinbase Inc. 36). Active in the locked 2021–2022 window:
credit_union 1 (BECU), fintech 2 (Block, Robinhood), crypto 1 (Coinbase Inc.) — every
industry below the ≥3 entry rule. Root cause is structural, not mechanical: the FEC lane
begins (2021–2022 cycle) exactly where LDA member linkage ends; the overlap window is
empty. This independently confirms the lda_bridge lead-months thesis — FEC is the only
member-level money/attention signal for the current period.

Disposition: look NOT consumed; route neither validated nor closed. The org-exact
2021–2022 window is exhausted at ANY entry rule or floor — relaxation cannot manufacture
coverage, so no relaxed re-lock will be attempted on this vintage. Successor prereg
permitted only on a NEW LobbyView vintage whose network coverage extends past 2022
(fresh fingerprints, its own single look). Consequence for display language, binding
until a successor look says otherwise: FEC exposure is presented as a target-side money
prior; the words "lobbying predictor" and any projection framing remain barred.
