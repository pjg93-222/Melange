# Pre-registration: FEC relational exposure × rebuilt LDA attention, round 3 — multivariate controls, 2023–2026 window

STATUS: LOCKED

Lock date 2026-08-01, committed BEFORE any Y-side data for this window is assembled
into networks and before any pairing exists. Adversarially panel-reviewed pre-lock
(2 lenses, 17 findings — 5 blocking, 9 should-fix, 3 notes — ALL incorporated below;
review recorded in the session workflow wf_b53cbe73-cb6). Authorized by Paul,
verbatim: "Ok, lets re-run the experiment with the appropriate control variables" —
routed to a NEW window per the one-look rule; RESULT-BRIDGE2 and its closed 2021–2022
window are untouched by every outcome here. The look script
`fec/fec_lda_bridge3_look.py` does not yet exist at lock: it lands by a SEPARATE
commit that must precede any COLLECTION RECORD entry, and that commit's hash plus the
script's SHA-256 are recorded in the COLLECTION RECORD — a disclosed deviation from
the same-commit convention, forced by locking pre-collection while sweeps run.
Codex is BARRED from `--look`; only a Claude session runs it.

## What this look is — and is not

CORROBORATION look, round-2 epistemics. POWER, restated honestly against the
COMPOSITE bar after the review: pairs are member×industry×cycle, but the same member
recurs across cycles, so the permutation is member-blocked (below) and effective
independent units ≈ unique member×industry combinations (~150–200 expected, not the
~340 raw pairs). Against true ρ=.25, the joint probability of clearing BOTH the
point-estimate bar (ρ̂ ≥ .20) AND p<.05 AND the partial bar is roughly 65–80% at
that effective N — good, not near-certain. A MISS is recorded as "UNCORROBORATED,"
never "disproven." No outcome measures stance, votes, persuasion, or causation.

## Adverse priors and honesty disclosures

- Round 2: UNCORROBORATED at ρ=+0.259, partial=+0.170, p=.098, N=52 (2021–2022).
- DIRECTIONAL-EXPECTATION HONESTY (review note incorporated): the disclosed
  diagnostics (crypto X~party ρ=+0.87 on 2021–22-cycle X; total-attention~party
  ρ=−0.76 and crypto Y~senate ρ=+0.46, both computed on the ROUND-2-WINDOW
  2021–2022 Y, never this window's) form a classic suppression pattern, so this
  control set is directionally EXPECTED to favor the hypothesis relative to
  round 2. That is legitimate on a fresh window and is stated plainly rather than
  dressed as neutral.
- OVERCONTROL / MEDIATION (review should-fix): committee assignment is plausibly on
  the causal path (industries target committee members; members seek seats because
  of industry ties). Partialling it can remove real mechanism, not just confound.
  Pre-declared interpretation: if bar 1 passes and bar 2 fails ONLY under the
  four-control partial while the firewalled three-control partial (party, chamber,
  volume-within-party; committee excluded) clears +0.10, the RESULT records the
  fixed sentence "association present but not separable from committee structure
  with this design" inside the UNCORROBORATED outcome — the tier does NOT improve,
  the closure still binds; the sentence exists so the record cannot be spun either
  way later.
- 2026 JOINT truncation (review should-fix): BOTH sides of the 2025–2026 stratum are
  mid-cycle series truncated at a common date (X = FEC through the artifact's
  data_max_date; Y = filings through the sweep date). Joint truncation is NOT
  attenuation-only: co-accumulation can bias that stratum toward passing. The
  2025–2026 stratum's contribution is therefore reported separately in secondaries,
  and the pooled result is the only bar-bearing number.
- Sweep-year attribution (hardened per review): 2024–2026 filings match pinned orgs
  via Senate client_ids harvested from the orgs' UUID-pinned ≤2023 filings.
  Harvest completeness is conditioned on ≤2023 footprint, and a new post-2023
  client_id would be silently missed — a differential-coverage channel whose bias
  direction is NOT guaranteed against passing; disclosed here, and the COLLECTION
  RECORD carries per-org harvested-client_id counts so the exposure is bounded.
  Zero-harvest orgs are coverage-limited (count against the stratum entry rule,
  reported in the RESULT). Name matching, where used, applies the pinned
  normalization: uppercase, punctuation→spaces, whitespace collapsed; EXACT match
  on the normalized string only; anything non-exact lands in a receipts list,
  and ALL match adjudication completes before any Y aggregate is computed or
  viewed.
- X truncation (top-100 beneficiary rows) unchanged from prior rounds.

## Input fingerprints (pinned at lock; gate refuses without consuming on drift)

- `%LOCALAPPDATA%\Melange\fec_spending\derived\fec_opposition_prior.json`
  SHA-256 CE3136A896CFA2E86CF80B68227825F863EAD1C605C6A1C1B189DDAFAA9EDED4,
  members 363 (verified at lock: unchanged since round 1; both cycle keys present;
  all six pinned X counts below reproduce exactly). This file is ALSO the roster
  (in_roster) source.
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\legislators.csv`
  SHA-256 C5A6CBDBAAE0BB19FAA89852C29922809ECECC70B97C149B4709588087E5E391
  (party + chamber source).
- Y-side artifacts, the committee-roster artifact, sweep manifests, and the look
  script itself are pinned in the COLLECTION RECORD (they do not exist at lock).

## Design

Strata: industry × cycle. Cycles "2023-2024" (Y years 2023+2024) and "2025-2026"
(Y years 2025+2026, both sides mid-cycle as disclosed). Industries: the pinned
22-lob_id org-exact crosswalk incorporated by reference from rounds 1–2
(credit_union, fintech, crypto; community_banks and credit_arms excluded by
construction). X, X>0 inclusion, Y=0 retention, in-roster scope: unchanged.
X counts pinned (2026-08-01): 2023-2024 fintech 48 / crypto 44 / credit_union 48;
2025-2026 fintech 55 / crypto 66 / credit_union 80.

Y: strict rebuilt network CSVs. 2023 filings enter via LobbyView-UUID worklists;
2024–2026 via full-year sweeps with the attribution rules above.

RANK NORMALIZATION (review blocking-3a): all pooled analyses use FRACTIONAL ranks
(rank − 0.5)/n computed within stratum (and within party×stratum cells for the
volume control), so strata of different sizes pool coherently.

Entry rule per stratum: ≥3 pinned lob_ids with ≥1 network row in the stratum's
years AND ≥1 in-roster member with X>0. VOID-FOR-COVERAGE (not consumed): pooled
pairs < 60 OR fewer than 2 DISTINCT INDUSTRIES among entering strata (review
should-fix: same-industry-twice does not satisfy the floor).

## Controls (all four pre-declared; construction rules fixed at lock)

1. PARTY: Republican indicator from the pinned legislators.csv `party`.
2. CHAMBER: Senate indicator from the pinned legislators.csv `type`.
3. VOLUME-WITHIN-PARTY: fractional rank of member total attention (Σ n_bills over
   ALL clients in the FULL-UNIVERSE sweep-derived network for the stratum's years —
   the same uniform population for all four years, 2023 included) computed within
   party × stratum cell; ties = average rank before the fractional transform;
   a singleton cell takes the constant 0.5; an empty-party cell cannot occur
   (members have party by construction).
4. FINANCE-COMMITTEE: indicator for full-committee membership of House Financial
   Services (thomas_id HSBA) or Senate Banking (SSBK), from
   unitedstates/congress-legislators `committee-membership-current.yaml` at TWO
   PINNED UPSTREAM GIT COMMITS chosen by rule (review blocking-4: no historical
   membership file exists): for the 118th stratum, the last commit to that file
   dated BEFORE 2025-01-03 (the 119th seating); for the 119th stratum, the last
   commit dated before this lock date. Membership = listed in that snapshot
   (full committee; subcommittee-only listings count via their parent committee
   id prefix). The two commit SHAs, the derived artifact, and its SHA-256 are
   recorded in the COLLECTION RECORD. If either snapshot cannot be retrieved and
   verified, the look REFUSES (not consumed); successor condition: same design
   re-locks when a verifiable roster source exists.

Partial statistic: residual Pearson after regression of pooled fractional
X-ranks and Y-ranks on ALL FOUR control vectors simultaneously. Both independent
implementations compute the residuals as the unique column-space projection —
implementation 1 via pivoted-QR, implementation 2 via SVD pseudo-inverse (review
note: collinearity-safe by construction; the design matrix's condition number is
logged in the RESULT); agreement |Δ| ≤ 1e-9 on every reported statistic, exact
equality on p. A DEFECT HALT (implementation disagreement) does NOT consume the
look — stated explicitly per review.

PERMUTATION (review blocking-1): member-blocked. For each permutation draw
(K=5000, seed 87001), one permutation of MEMBERS is drawn per industry over the
union of that industry's members across both cycle strata; each member's Y values
carry jointly to the permuted member's position in EVERY stratum where both are
present; strata positions with no counterpart under the block alignment are
permuted within the leftover set of that stratum. Exceedance decided in exact
integer arithmetic on 2×-scaled ranks. This preserves cross-cycle dependence under
the null; the raw-pair count never enters a variance formula.

## Bars (all-must-hold for CORROBORATED)

1. Pooled within-stratum Spearman ρ (fractional ranks) ≥ +0.20 AND member-blocked
   exact permutation p < .05.
2. Four-control multivariate partial ≥ +0.10.
STRONG: ρ ≥ +0.40 AND p < .01 AND partial ≥ +0.20.

## Simulate battery (any check's failure = RETIRED WITHOUT A LOOK, not consumed;
successor condition pinned at retirement — applies to (a) through (d) equally)

Rank-z constructions, seeds 424242/535353/646464/757575, on the real X margins and
REAL control vectors (exercising the disclosed collinearity regime — review note):
(a) PLANTED: Y = z(X-frac-rank) + λ·ε, λ bisected (domain [0.5, 8], 60 iters) to
    pooled ρ ∈ [.32, .38] — must clear bar 1 under the member-blocked permutation.
(b) NULL: member-blocked permutation of (a)'s Y — must NOT clear bar 1.
(c) CONFOUND-ONLY (redesigned per review): Y = z(X̂) + 0.15·ε where X̂ = fitted
    values of X-frac-ranks regressed on the four real controls — confound-driven Y
    through the control span with real collinearity. Bar 2 MUST refuse
    (partial < +0.10). Exercise clause: if this Y's raw pooled ρ vs X is < +0.20,
    the check is recorded VACUOUS-PASS with both numbers (the controls grip X too
    weakly for the check to bite) — recorded, not hidden.
(d) TRUE+CONFOUND: Y = z(X-frac-rank) + λ·ε + 0.75·z(X̂) + 0.15·ε (single ε per
    the standing clause) — bars 1 AND 2 must admit.
Battery output recorded verbatim, pass or fail.

## Consequences (wording fixed now)

- STRONG: "FEC relational exposure is STRONGLY CORROBORATED (2023–26, org-exact,
  our instrument, four-control) as a cross-sectional proxy for LDA lobbying
  attention." Candidate generator permitted, consumed by nothing, Paul's gate.
- CORROBORATED: candidate permitted; labels "directionally corroborated";
  unqualified "predictor" barred.
- UNCORROBORATED: "FEC exposure remains a target-side money prior ONLY and must
  NOT be presented as a lobbying-relationship predictor or projection." Route
  CLOSED for the 2023–2026 window on this instrument — and explicitly: A DIFFERENT
  CONTROL SET ON THIS WINDOW IS NOT A SUCCESSOR (review should-fix; the
  control-set qualifier is struck from closure scope). Successor requires a later
  window or a materially different instrument, fresh fingerprints, its own look.
  The overcontrol interpretation sentence applies as pre-declared above.
- FRAGILE = MISS: statistics (date excluded) must reproduce exactly on verbatim
  rerun.
- VOID-FOR-COVERAGE: not consumed; successor may relax only entry rule or floor.
- On CORROBORATED-or-better: RESULT-BRIDGE2 gains a dated ANNOTATION (original
  text untouched) noting the controlled successor outcome.

## COLLECTION RECORD

Appended 2026-08-01 on Y-side assembly completion (the pre-declared post-lock edit).
Sweeps: 14,226/14,226 pages across 2023–2026, per-year manifests clean; sweep-through
dates carried in rebuild_receipts.json. Machinery commits preceding this record:
look script @80d3f16 (fec/fec_lda_bridge3_look.py SHA-256
CF45E5DD774A512A0472EF5DCF194F2228109362CB1623A0C487314CBBB263B6), builder
attribution/dedupe fixes @9cb600e (client.id proven the stable Senate key —
client_id=12 resolved to five different pinned orgs; sweep pagination-drift dedupe,
1 duplicate receipted). X and legislators fingerprints re-verified equal to the
locked pins. Zero-harvest coverage-limited org: c27f7c24 (PenFed, last direct
lobbying 2010).

our_network_2023_strict.csv SHA-256 22DB9A8087BA7CC322F89202554D0D58787D3B1E60CE118DECAF885C2084CC5A rows 116
our_network_2023_generous.csv SHA-256 CB237B5F966E248230E10758B492BEB571E4354404797FCFD7EF9AEAEDFD6511 rows 117
our_network_2024_strict.csv SHA-256 D7517DDB4B7D118247A14A92BC1E50B57286CC9674B34F872A4B8BCEAE9CCC59 rows 139
our_network_2024_generous.csv SHA-256 D7517DDB4B7D118247A14A92BC1E50B57286CC9674B34F872A4B8BCEAE9CCC59 rows 139
our_network_2025_strict.csv SHA-256 1634EE7D0A88CA29C2C248B0D13465D6792103DE8751E337727E2C503502EE3A rows 364
our_network_2025_generous.csv SHA-256 40CA19C90BF1442B1810EF3F5DD9DC68FA39FC5B871B155692B5123DF0250D94 rows 412
our_network_2026_strict.csv SHA-256 2C91207F39B0F47AC8BFA27E2A1B5276AD24F39D6FCCBBAFA55E72AC287FC056 rows 211
our_network_2026_generous.csv SHA-256 D4A999CFE70D72AC123A5CB04C1C0E95FF67BEE5CC1BF46F941E15C8D587E65F rows 341
totals_2023.csv SHA-256 BC34C92CA4FEBD75194ACC0FFC8310E27D2C56F93B077759E02126B060C545AD rows 814
totals_2024.csv SHA-256 4566BF9A87F61FC3046988904D5988B20BE3A8ECE6583C442F902B7555705CB9 rows 811
totals_2025.csv SHA-256 0C5D40DC9E6C9C4B44478B121783344012780BB581C59FF6681D0CEED1E9F768 rows 897
totals_2026.csv SHA-256 A0C7C762519C8301D05993E4A80B4DB8F27DBBDE477DAC0769A79D199940D2B0 rows 877
committee-membership-118-c3843a3e83e5b00e33f4140a977af546514396e2.yaml SHA-256 D70F765B3A13E262D21B0C3C45DCD00687A8B13537EA92FF20929CA16116C99F
committee-membership-119-f9e4eda519ccf1a57e3e502555f9b7bd473601d4.yaml SHA-256 F35C02AC3C6E5E9BA12C43AA9E17B4A4124FA23A29264542F669D64DB41F24CC
harvested-client-ids 03b1f6cd-0546-59d2-97d3-9a31da3063b0 count 2
harvested-client-ids 0f549ea5-9fdb-5cb9-9a9f-82682d4ef353 count 4
harvested-client-ids 18cf487e-9e89-52ec-93dc-d91de45c0b84 count 2
harvested-client-ids 1c3314d2-e20e-5484-8084-97e58c4eca81 count 4
harvested-client-ids 3f7a52db-9be0-5222-84bd-693a1ccc38ae count 2
harvested-client-ids 4317e970-8485-55be-af60-d59762a1c8d7 count 1
harvested-client-ids 4f43f95f-f6f0-5b47-9f74-08d6b885ac55 count 7
harvested-client-ids 5f438304-3b42-5241-9821-874137fdc0ce count 1
harvested-client-ids 67e35f81-afa7-5258-998e-7f08a3512e20 count 10
harvested-client-ids 6904853b-ba69-5493-85b0-6699c0f7e33b count 7
harvested-client-ids 69c5a9e9-7d79-557e-8ff5-f07df772534d count 2
harvested-client-ids 75d2c2aa-fb94-5005-acff-1479c56d41b5 count 3
harvested-client-ids 7ddb0913-d306-57d7-b42d-febd24a314cf count 1
harvested-client-ids 8b517298-a4d4-5e93-bf5a-86af84076c66 count 2
harvested-client-ids 9a33b530-6a10-52df-9d55-a2f4e0168316 count 1
harvested-client-ids b849b9da-67fa-5eae-914b-92ac41c7ad31 count 1
harvested-client-ids c27f7c24-43ec-52f7-80d6-ebb74cc526b1 count 0
harvested-client-ids c3dc5b6d-38b1-5331-bec4-6cf081fa6cf1 count 4
harvested-client-ids cb4ac22a-dd82-5a42-a289-83fd13ba07d0 count 3
harvested-client-ids d039e7e5-f821-55d5-9e38-f93c0b71aecb count 1
harvested-client-ids dbdd9f97-b360-53f0-adc8-9a7e5e4c967c count 1
harvested-client-ids f2f8dae7-b696-5e01-8067-31b357170ec2 count 2

Original scope declaration (retained): must contain: SHA-256 + row counts of the four strict network
CSVs (2023–2026) AND the full-universe totals files backing control 3; the
committee-roster artifact SHA-256 + both upstream commit SHAs; sweep manifests
(pages, md5 maps, sweep-through dates); per-org harvested-client_id counts and the
name-match receipts; the look-script commit hash + file SHA-256; the X and
legislators fingerprints re-verified. Everything the look script trusts is either
pinned above or listed here — nothing else may be read by the look path.

## Discipline

One look; battery-gated; no bar/seed/roster/crosswalk/wording/rule changes
post-lock; no-status-change on every prior result and ratified constant.
Secondaries (all firewalled, grounding NOTHING): per-stratum ρ/p; per-control
single partials; the three-control partial named in the overcontrol clause; the
2025–2026-stratum-only ρ; generous-mode pooled ρ; a round-2-window descriptive
replay under these controls — a labeled curiosity that is NOT a look, may never be
quoted as evidence, and appears only inside the RESULT block. Gate refusals:
prereg absent; STATUS: LOCKED absent; newline-anchored `## RESULT-BRIDGE3`
present; any pinned fingerprint drifts; COLLECTION RECORD absent/malformed/
incomplete per the scope above; committee-roster retrieval failure; battery
failure; non-`--look` real-path invocation. `--simulate` = battery only;
no-arg = status print. The look runs only under `if __name__ == "__main__"`.

## BATTERY-BRIDGE3
- battery PASS
- planted lambda: 2.209005014457
- PLANTED seed 424242: check=PASS; impl1 rho=+0.349869778160, p=0.000199960008, partial=+0.330629357485; impl2 rho=+0.349869778160, p=0.000199960008, partial=+0.330629357485
- MEMBER-BLOCKED NULL seed 535353: check=PASS; impl1 rho=-0.020639301038, p=0.624475104979, partial=-0.027725864528; impl2 rho=-0.020639301038, p=0.624475104979, partial=-0.027725864528
- CONFOUND-ONLY seed 646464: check=PASS; impl1 rho=+0.465485419058, p=0.000199960008, partial=+0.079451802726; impl2 rho=+0.465485419058, p=0.000199960008, partial=+0.079451802726
- TRUE+CONFOUND seed 757575: check=PASS; impl1 rho=+0.514083525555, p=0.000199960008, partial=+0.390368842006; impl2 rho=+0.514083525555, p=0.000199960008, partial=+0.390368842006
- look eligibility: battery admitted

## RESULT-BRIDGE3
- date: 2026-08-01
- pooled N: 213
- stratum entry status:
  - credit_union x 2023-2024: coverage-limited; active_nonzero_harvest_orgs<3; active_orgs=1
  - credit_union x 2025-2026: coverage-limited; active_nonzero_harvest_orgs<3; active_orgs=2
  - fintech x 2023-2024: entered; pairs=48; active_orgs=3
  - fintech x 2025-2026: entered; pairs=55; active_orgs=5
  - crypto x 2023-2024: entered; pairs=44; active_orgs=4
  - crypto x 2025-2026: entered; pairs=66; active_orgs=3
zero-harvest coverage-limited orgs: c27f7c24-43ec-52f7-80d6-ebb74cc526b1
- pooled fractional-rank Spearman rho: +0.152525809416
- exact member-blocked permutation p: 0.014597080584 (K=5000, seed=87001)
- four-control partial: -0.000204468398
- design-matrix condition number: 5.48804931642
- tier: UNCORROBORATED
- consequence (fixed wording): FEC exposure remains a target-side money prior ONLY and must NOT be presented as a lobbying-relationship predictor or projection. Route CLOSED for the 2023–2026 window on this instrument; A DIFFERENT CONTROL SET ON THIS WINDOW IS NOT A SUCCESSOR.
- implementation 1: rho=+0.152525809416, p=0.014597080584, partial=-0.000204468398
- implementation 2: rho=+0.152525809416, p=0.014597080584, partial=-0.000204468398
- battery summary: PASS; lambda=2.209005014457
- secondaries (firewalled; ground nothing):
  - credit_union x 2023-2024: NOT ENTERING
  - credit_union x 2025-2026: NOT ENTERING
  - fintech x 2023-2024: impl1 rho=+0.028000264448, p=0.444111177764; impl2 rho=+0.028000264448, p=0.444111177764
  - fintech x 2025-2026: impl1 rho=+0.180366159196, p=0.094181163767; impl2 rho=+0.180366159196, p=0.094181163767
  - crypto x 2023-2024: impl1 rho=-0.146203461607, p=0.817036592681; impl2 rho=-0.146203461607, p=0.817036592681
  - crypto x 2025-2026: impl1 rho=+0.292778320851, p=0.010197960408; impl2 rho=+0.292778320851, p=0.010197960408
  - party-only partial: impl1=+0.120776916855; impl2=+0.120776916855
  - chamber-only partial: impl1=+0.148148608971; impl2=+0.148148608971
  - volume-only partial: impl1=+0.112829847065; impl2=+0.112829847065
  - committee-only partial: impl1=+0.053035589513; impl2=+0.053035589513
  - three-control partial (party, chamber, volume; committee excluded): impl1=+0.072670065762; impl2=+0.072670065762
  - 2025-2026-only rho: impl1=+0.240444177163; impl2=+0.240444177163
  - generous-mode pooled rho: impl1=+0.173117539084; impl2=+0.173117539084
  - round-2-window descriptive replay: OMITTED — its committee-control input has no pinned pre-lock snapshot rule; emitting it would require post-lock discretion, so it is not computed.
