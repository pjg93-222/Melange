# FORECAST COLLINEARITY + CONFOUNDER AUDIT -- 2026-08-17

Frozen dated record. Paul's directive: examine "the expected co-sponsorship forecast from
lobbying pressure" for multicollinearity and confounding. READ-ONLY analysis over live-tree
artifacts; no engine, dial, artifact, or surface changed. Companions in this directory:
collinearity_results.json (flagged-pair table), collinearity_analysis.py (the exact script).

## 0. Scope ruling and method

TARGET (per Paul's wording "from lobbying pressure"): the ENGINE stack -- flip_model.py's
pflip/tgt winnability and the cascade cosponsor-route -- whose formula map (coordinator-
dispatched read-only extraction, 2026-08-17) identified ~22 exogenous per-member leaves.
The separate descriptive logistic model behind lobby-forecast.html (P(member cosponsors
bill) from priors/ideology; zero lobbying variables) is out of primary scope; section 6
carries its note. Thresholds were PINNED IN CHAT BEFORE COMPUTATION: |rho| >= 0.7 flags a
pair; VIF >= 5 caution / >= 10 severe; party-partial attenuation > 50% flags party
confounding; explicit volume/gender/chamber/retiring checks. n = 533 roster; per-pair n
stated; VIF listwise n = 289 (dominated by cooperation_v2_z coverage 314/533). Spearman
primary (money skew), Pearson beside it.

## 1. Structural collinearity -- predicted by the formula map, now MEASURED

- C2 CONFIRMED AT CEILING: susc_z x edge_mult x susc_mult all rho = +1.000 (n=533). The
  three are one scalar wearing three names (affine transforms of the same susc; the clip
  boundaries never bind in practice). Anywhere a pipeline uses pflip's money channel AND a
  cascade kernel, "receptivity" enters twice as the identical signal.
- C3 CONFIRMED: security drives BOTH factors of pressure_mult's tail -- incent_mult x
  security rho = -0.773, pt_mult x security rho = -0.686, net pressure_mult x security
  rho = -0.671 (all n=533). A hidden security-squared term sits inside the pressure scalar.
  retiring x pressure_mult rho = -0.57 is the designed hard-set (incent=0.60), a stratum to
  keep visible, not a defect.
- C1 CONFIRMED, WORST LEG: bpf x cooperation_v2_z rho = +0.888 (party-partial +0.889,
  n=314). The cross-party tie share and the v2 cooperation construct are near-duplicates of
  one underlying signal, and they enter the SAME product through two doors: tgt's
  (1 + 0.3*bpf) factor and pressure_mult via susc (coop weight .40). Party does not explain
  it -- it is genuinely one construct counted twice. seed_prob inherits the cluster
  (x coop rho = +0.757).
- C8 (SPECIFICATION, from the map's algebra): pressure_mult multiplies both money terms of
  pflip's Bradley-Terry ratio and CANCELS in the money-only limit -- it has no first-order
  effect on pflip level, only reweights money-vs-peer channels. Any analysis treating it as
  an additive predictor of pflip mis-specifies it.
- Clean bill of health where it matters: the money block is NOT collinear (log_cu, log_ind,
  log_receipts, nodata VIF <= 2.7); net_strength x bpf rho = -0.14 (raw connectivity and
  cross-party share are independent); chamber shows no |rho| >= 0.2 against any trait input.

## 2. Novel findings (not predicted)

- STANCE-COVERAGE x BREADTH COUPLING: stance_none_share x breadth_z rho = -0.851;
  stance_score_mean x breadth_z rho = +0.743 (party-partial +0.782, n=511). Members with
  high behavioral breadth have far fewer '-' cells and higher mean stance scores -- stance
  COVERAGE is entangled with the O-criterion behavioral input. Since stance tier/score
  enters tgt (PERS, priority) and breadth enters seed_prob, coverage couples the stance and
  seeding blocks through a channel nobody chose.
- DUPLICATE STANCE SCALES: stance_score_mean x stance_pers_mean rho = +0.977 -- two views
  of one matrix; VIF 19.4 / 17.4 (the only SEVERE VIFs). Never enter both in any regression.

## 3. VIF summary (leaf set, z-scored, listwise n=289 of 533)

SEVERE: stance_score_mean 19.38, stance_pers_mean 17.38 (mutual duplicates -- drop either).
CAUTION: cooperation_v2_z 6.38, bpf 6.15 (the C1 cluster). ALL OTHERS < 5, money block
<= 2.66, every missingness indicator ~1.0. The leaf set minus one stance scale and with
{bpf, coop_v2, seed_prob} treated as one cluster is well-conditioned.

## 4. Confounder register (measured; controls named)

| Confounder | Loading (rho, n) | Party-partial | Reading / control |
|---|---|---|---|
| PARTY (headline) | communion -0.50 (523); M_susc_z -0.29 (530); M_seed_prob -0.31 (530); diligence +0.22; breadth -0.21 | all ~0.00 (by construction) | The susceptibility/seeding chain partly ENCODES party -- Democrats measure more susceptible/seedable on average. CONTROL: any forecast-vs-outcome validation runs WITHIN PARTY as a mandatory secondary read; pooled numbers carry the UNSTRATIFIED label per D-007. |
| GENDER | communion +0.38 (526, partial +0.30); M_susc_z +0.20 (partial +0.11) | persists | Gender leaks into susceptibility via the persona channel (persona_susc = .60*z(communion) - .40*z(agency)). CONTROL: gender partial on any susceptibility-ranked claim; echoes the recorded ES-gender lesson. |
| VOLUME | log_nposts x visibility_z +0.70 (496, partial +0.72); x dominance +0.46 (partial +0.15); x M_seed_prob +0.36 (partial +0.33) | visibility persists | visibility_z IS a volume measure by design (E criterion); dominance-volume is mostly party-mediated. CONTROL: volume covariate on any visibility/seed_prob-derived claim; never read seed_prob differences as disposition without it. |
| RETIRING | M_pressure_mult -0.57 (533) | persists | Designed hard-set (incent=0.60). Keep the retiring stratum visible in any pressure-ranked table. |
| CHAMBER | none >= 0.2 | -- | No control needed at this granularity. |
| MISSINGNESS | coopv2_missing 219/533; affn_missing 61/533; persona_missing 7/533; nodata money 18/533 | -- | Neutral-fill imputation makes coverage flags correlate with values. CONTROL: explicit missingness indicators (as used here) in any regression; the 18 no-FEC members form a perfectly-collinear money stratum -- fixed-effect or exclude. |

## 5. What this means for the 2026-09-02 outcome scoring and any model work

- The FROZEN outcome-snapshot scorer runs exactly as locked (bars rho >= +.20 / +.10 /
  <= -.10; >= 60 days AND >= 150 movers). Nothing here edits it.
- The controls above define the SECONDARY diagnostics that should accompany its
  interpretation, as new pre-declared analyses: within-party rho, volume-partialed rho,
  and the retiring/nodata strata reported beside the pooled number.
- Candidate MODEL-side items (ALL Paul-gated, none acted on): (a) the susc triple-identity
  -- edge_mult/susc_mult are one dial; (b) the security double-entry inside pressure_mult
  (intentional prospect-theory design or accidental squaring -- his call); (c) the
  bpf+coop_v2 double-count in tgt x pressure_mult; (d) the pflip pm-cancellation
  specification note; (e) the flip_model docstring claims bridge-amplified proximity while
  the code uses party-only cpf_pressure -- possibly a ratified divergence, needs his ruling,
  code untouched.

## 6. Secondary note -- the lobby-forecast.html logistic model (out of primary scope)

By construction its feature set contains exact functional dependencies (nominate abs-
distances are |differences| of included components; ideology_distance_missing is an OR of
included flags; same_party nearly determined by nominate_dim1 sign). Its own harness
already QR/SVD-guards the Gram matrix and reports a condition number -- read that receipt
before computing VIFs there. Its realized configuration lives outside the repo
(%LOCALAPPDATA%\Melange\lda_rebuild\derived) and was not read; if Paul wants this model
audited to the same standard, that is a follow-on task against those artifacts.

## 7. Provenance

Inputs and coverage as printed by the script (533 roster; per-column non-null counts in the
run log); formula map from the read-only code extraction (flip_model.py:75-130,
receptivity_layer.py:147-198, moneyball_core.py consumers); thresholds pinned in chat
before computation; script + flagged-pair JSON committed beside this record. The mapper's
full inventory (three forecast objects, leaf table, nine built-in channels C1-C9) is
reproduced in the transcript and summarized here; its two escalations (docstring
divergence, audit-target choice) are recorded in sections 0 and 5.

## 8. Retired-route adjacency (kill-ledger check, added before commit)

A read-only sweep surfaced `big5_forecast_features_prereg.md` on branch
`claude/metaloop-forecasting-data-fixes-9043da` (retirement commit 413185090, Paul,
2026-08-14): "primacy factor + behavioral traits O/C/E" as ADDED FEATURES to the
v2-surgical cosponsor_forecast model (Object C) is **RETIRED WITHOUT A LOOK** -- the
PLANTED sigma=0 battery check refused (measured DeltaAP -0.0108, negative), look unspent.
Pinned successor condition, quoted verbatim per that prereg's own rule: "A successor may
proceed only when its pinned member-space sigma=0 plant recovers measured DeltaAP >= +0.010
on its pinned panel."

BINDING CONSEQUENCE FOR THIS AUDIT: nothing in sections 1-5 may be read as license to add
or reweight trait features in any cosponsorship forecast -- that route is retired until the
successor predicate is discharged. This audit's outputs are CONTROLS for interpretation and
redundancy/specification questions for Paul, not feature proposals. Corroboration noted:
that prereg's own adverse prior ("cooperation_z ... constructed from cosponsorship records;
feeding them to a cosponsorship forecast is circular") is the same construct-circularity
this audit measured empirically as C1 (bpf x cooperation_v2_z rho = +0.888).