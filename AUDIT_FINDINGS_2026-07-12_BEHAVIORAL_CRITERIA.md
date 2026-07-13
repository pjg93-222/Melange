# Behavioral criteria and Big Five overlay audit — 2026-07-12

**Scope.** Behavioral dispositions, the Blue behavior-calibrated text model, the Pink LLM item-read, criterion validity, and cross-contamination. Audited on `main` at `c9effff` with the pre-existing dirty worktree preserved. This report records an engineering/measurement audit; it does not reopen a locked research look or promote a new psychometric claim.

## Bottom line

- **Leg 1 reliability: 5/5 pass. Leg 2 known-groups: 5/5 pass. Leg 3 discriminant/diagonal dominance: 3/5 pass (O/C/E).** The earlier shorthand “3/5” referred only to Leg 3; using it without the leg label was misleading and has been corrected in the desk.
- Blue A is related to cooperation but is not discriminant. A new N look passed all five bars twice on the interview-covered stratum (n=263), but failed its no-interview ship gate; it is conditional evidence, not a full-corpus promotion.
- Pink remains **0/5 diagonal-dominant** against the behavioral criteria. It is an independent, display-only item-read, not a calibration target.
- The large Blue/Pink gaps are genuine method disagreement plus some mixed-corpus-vintage drift. They must not be removed by averaging or calibrating one method to the other.
- Criterion contamination is modest for party/gender in several slots, but substantial **exposure/volume contamination** remains in Visibility and Breadth. Affective-N remains the ratified engine slot after review; its E/party residualization is correctly treated as a confound control, not independent validity evidence.

## Blue/Pink discrepancy audit

The current Blue snapshot covers 532 members; the frozen cost-gated Pink snapshot covers 509; 509 members pair. Pink is 4.4 days older (2026-07-07 versus Blue 2026-07-12).

| Trait | Pearson r | Spearman rho | Median absolute percentile gap | Mean gap | Gap > 0.60 |
|---|---:|---:|---:|---:|---:|
| O | -0.044 | -0.080 | 0.311 | 0.350 | 97 |
| C | 0.160 | 0.100 | 0.289 | 0.320 | 69 |
| E | 0.027 | 0.020 | 0.295 | 0.331 | 74 |
| A | 0.234 | 0.220 | 0.226 | 0.283 | 52 |
| N | 0.055 | 0.063 | 0.281 | 0.317 | 68 |

The discrepancy is not explained by text chunks/tokens (gap correlations were near zero), and changing percentile tie handling changes average gaps by about 0.001. Those routes are not plausible fixes.

### Display defects fixed

1. The draft desk had copied one affective-N percentile into both Blue and Pink, manufacturing fifth-axis agreement. Blue N and Pink N are now independently ranked from each family's own `N = -ES` score. In the regenerated bundle, only 1 of 509 paired members has a coincidental fifth-axis percentile tie.
2. The desk now discloses the mixed Blue/Pink vintages and coverage counts.
3. Missing axes no longer count as agreement, overlap is labeled descriptive rather than a validity verdict, and the UI explicitly warns against averaging/calibrating the methods together.
4. The gender-confounded voice-ES read remains retired from the display.
5. Rendered inspection found a separate leakage path: legacy generated narratives repeated direct text-A/ES claims even though those axes were not qualified. Those sentences are now removed at bundle generation, every narrative carries a provenance warning, and the ambiguous text-model `grade A-` badge is replaced by the actual `3/5 distinct (O/C/E)` result.

## Criterion and cross-contamination audit

| Criterion | n | Party r | Gender r | Raw volume r | Volume-controlled r | Principal concern |
|---|---:|---:|---:|---:|---:|---|
| Cooperation v2 (A role) | 315 | -0.154 | -0.021 | -0.131 | -0.180 | Source mix: tweets -0.196; cosponsors -0.159 |
| Diligence (C role) | 529 | 0.182 | -0.057 | 0.058 | 0.097 | Votes cast +0.187; availability correlation only +0.024 |
| Dominance (E resistance role) | 533 | 0.000 | 0.003 | 0.211 | 0.234 | Tweets +0.257; 222 members share the modal value and 261 lack observed interaction coverage |
| Visibility (seed role) | 493 | -0.165 | -0.049 | 0.423 | 0.487 | Interview count +0.887 |
| Breadth (seed role) | 511 | -0.192 | 0.030 | 0.463 | 0.558 | Cosponsor count +0.848; only 24 unique values |
| Reactivity (pressure role) | 272 | 0.031 | -0.040 | 0.085 | 0.059 | Role measure, not a validated Big Five N criterion |

Criterion-to-criterion correlations are mostly small. The larger pairs are Cooperation–Dominance `r=-0.166`, Dominance–Breadth `r=+0.171`, and Reactivity–Dominance `r=+0.147`. This is not a general halo collapse, but the exposure-heavy Visibility/Breadth criteria and coarse Dominance coverage require caution.

### Affective-N interpretation corrected

`affective_n.json` is an LLM affective-facet score residualized on another text-family E score and party. Therefore its E-clean and party-clean results are confound controls and cannot be counted as independent criterion-validity evidence. It is also not a behavioral criterion. Its producer currently depends on an ephemeral scratchpad label file outside the repository, a genuine reproducibility weakness. Before residualization, the pre-specified facet recipes were party-loaded (`r=-0.20` to `-0.30`).

Those caveats do **not** overturn the committed Round-7/7b promotion. The measure passed its pre-registered 5/5 engine gate: E distinctness, party control, independent LIWC convergence (`r≈+0.24`), a fresh reliability test, and lower E contamination than the incumbent reactivity measure. The current artifact also passes its prespecified face-validity check: **Clay Higgins is #1** (`z=4.568`). Affective-N therefore remains the default engine pressure slot, while the report and UI distinguish its controlled construct evidence from external criterion validation.

An audited rollback would have been decision-relevant—offline sensitivity showed susceptibility-multiplier `r=0.855`, mean absolute change 0.0288, 95th-percentile change 0.0828, and top-20 overlap 11/20—so it was rejected once the binding 5/5 promotion record was rechecked. Rank authority is upstream and its SHA-256 remained unchanged: `797A6490CA0C0F63496F76AC9F030C0A8B538D5F46DBC18E39092BBBC74B00C6`.

## Gated Agreeableness follow-up

The shipped Round-5 Empath successor diagnostic was run in synthetic/no-look mode. Its five seeds passed 2/5 bars (seed results `+.081`, `+.206`, `+.060`, `+.209`, `+.137`; median `+.137`). The gate correctly refused a real look. No recalibration or status change is authorized from this result.

## Verification

- Kernel tests after all changes: **37/37 passed**.
- Full-body audit including the new overlay guards: **ALL MODULES CLEAN** after the restored affective-N downstream rebuild.
- The documented Excel-open fallback was used: rebuild from `per_topic_flip` through both dashboards and the member desk, avoiding workbook writes.
- Regenerated bundle: 469 affective-N-covered members, Clay Higgins #1 on that axis (`z=4.568`, 100th percentile), 509 paired Blue/Pink profiles, and only 1 coincidental text-N percentile tie.
- Downstream-only pipeline from `per_topic_flip`: every step passed; `audit_full.py` returned **ALL MODULES CLEAN** in a 10.3-minute run. Rank SHA-256 remained unchanged.
- Final independent rerun after the article-guided sampling-frame and display/cross-contamination guards: **79 passed, 0 failed — ALL MODULES CLEAN**; kernel tests **37/37**.

## Post-audit validation campaign

- **N Round 8:** current corpus unlocked MEM_N=263 with criterion SB=.596. The locked five-seed diagnostic cleared 3/5. Primary N passed all five bars (`r=.188`, perm-p=.0014, partial `.152`, p=.0078); fresh-seed re-derivation passed (`r=.179`, p=.0030, partial `.146`, p=.0098). The no-interview ship gate missed (`r=.098`, p=.0562), so the result is interview-stratum only and no production trait was promoted.
- **A Round 9 criterion:** fresh blinded interview-antagonism labels qualified 5/5 (n=322, SB=.699, low raw party/gender/volume contamination, hearing convergence `.160`, cooperation direction `-.072`).
- **A Round 9 trait:** the locked `st_mean` text-A look missed (`r=.084`, p=.0782, row/column dominance false, partial `.087`, p=.0652). This route is closed. The new antagonism criterion remains useful as a secondary measure, but it does not validate Blue A.
- **A facet deployment:** after the user clarified that A itself—not specifically Blue text-A—must be validated, the qualified Round-9 criterion was promoted as a separate display-only inverse-antagonism A facet. It is valid at the facet level under the locked 5/5 criterion gate; it neither replaces cooperation_v2 nor changes ranks, and it is not imputed into Blue or Pink.

## Open, bounded follow-ups

1. Preserve the LLM affective-facet labels as a reproducible, versioned input; the current ephemeral scratchpad dependency is not acceptable long-term provenance.
2. Treat Visibility and Breadth as role variables, not pure personality criteria, until a preregistered residualized/exposure-matched robustness test succeeds.
3. Improve observed-interaction coverage for Dominance before interpreting fine member-level differences in its modal block.
4. Do not rerun or force the A look: its successor battery failed its diagnostic gate.
5. Do not refresh Pink merely to make the chart agree. A refresh is justified only as a separately authorized, cost-gated new snapshot.

## User-supplied literature and the resulting correction

- Azucar, Marengo, and Settanni (2018, DOI `10.1016/j.paid.2017.12.018`) meta-analyze 16
  independent studies per trait: O .39, C .35, E .40, A .29, N .33. A is the weakest target;
  multiple footprints generally help other traits but not A, while demographics increase apparent
  A/N prediction. In this project demographics therefore remain confound controls, never A features.
- Celli et al. (2026, DOI `10.1145/3806009`) distinguish stable traits, situated states,
  ecological validity, and observer/model representation validity. They also document that LLMs
  can exhibit a high-A/high-O/low-N response profile. Pink is therefore a model-perception channel,
  not a gold standard; cross-source evidence is triangulated without being averaged together.
- Hargittai (2015, DOI `10.1177/0002716215570866`) demonstrates that trace-data size cannot cure
  a non-random sampling frame and recommends explicit scope plus data triangulation.

The resulting locked coverage audit found the A facet's 322 members are selected: Senate coverage
90.0% versus House 53.6%; Democrats 68.0% versus Republicans 52.9%; visibility SMD +1.877 and
log-Blue-token SMD +1.195; gender coverage is balanced (60.7%/60.8%). The claim is now explicitly
**validated inverse-antagonism A facet on the interview/media-covered stratum**. Percentiles are
relative only to covered members; no score was changed and no uncovered member is imputed.

## Citation-chain and independent gap audit (2026-07-12, second pass)

The useful descendant literature does **not** show that simply adding hearings, interviews, and
social posts makes five passive-text traits valid. It shows that the successful designs share two
properties missing here: a real questionnaire target for every person and repeated independent
judgments that can be averaged.

- Hinds and Joinson (2024, DOI `10.1037/bul0000430`) supersede the Azucar evidence base with a
  two-study systematic review/meta-analysis. Computer prediction remains modest and heterogeneous
  across data types and platforms; platform/source is a moderator, not interchangeable extra volume.
- Peters and Matz (2024, DOI `10.1093/pnasnexus/pgae231`) scored 1,000 people with 200 Facebook
  statuses each against their own 100-item IPIP self-reports. Three repeated LLM ratings improved
  reliability, but the LLMs systematically underestimated A/C, overestimated N, and showed
  demographic error differences.
- Marengo, Montag, and Settanni (2025, DOI `10.1111/jopy.70019`) are a direct successor to Azucar:
  two LLMs x two years of Facebook posts for 1,214 people. Averaging models and time points improved
  stability and self-report convergence, but observed same-trait correlations remained modest
  (combined E .23, A .14, C .17, N .13; attenuation-corrected values are larger).
- Härtel et al. (2025, DOI `10.1007/s10869-025-10087-8`) provide the closest public-persona analogue:
  406 LinkedIn profiles and BFI-2 gold. Only O and E were above chance among the Big Five; A=.09,
  C=.07, N=-.03, and the MTMM matrix failed because broad favorable-profile cues loaded on many
  inferred traits. More/enriched public-profile input did not repair the construct problem.
- Wright et al. (2026, DOI `10.1038/s41562-025-02389-x`) identify the strongest current protocol:
  seven different LLMs, the exact 60/120 inventory answered item-by-item, and model averaging over
  unconstrained first-person narratives, evaluated against the participants' own inventory scores.
  Recalculation from the authors' public Sample-1 files reproduces all-five convergence at n=60:
  N .472, E .434, O .397, A .546, C .531. The critical design differences are private spontaneous
  thought plus questionnaire gold—not merely a larger passive public corpus.

### Local findings that invalidate the former three-leg shorthand

1. **The three reported legs were attached to different instruments.** The .92/.81/.77/.80/.92
   reliability vector is documented for a legacy genre composite. The displayed Blue O/C/E/A
   scores are behavior-calibrated v2 scores, while v2 ES mixes that old composite for 259 members
   with the current pooled lexical fallback for 273. It was therefore incorrect to say that all
   five displayed Blue axes passed that split-half test.
2. **The old reliability split is package-contaminated.** Reconstructing `BIG5_HALF` exactly found
   30,427 of 142,813 speech packages (21.3%) represented in both halves: CREC 33.4%, interviews
   12.6%, and hearings 95.0%. Alternating adjacent turns is not an independent split. Current-Blue
   reliability is now marked **re-audit required**, not 5/5.
3. **Known-groups remains a five-sign pass but A has no effect.** On the cleaned current v2 artifact,
   R-D is O -.3716, C +.6002, E -.2698, A -.0009, ES +.4116. A's 95% CI is [-.1709,+.1690],
   p=.9914; 204/530 leave-one-member-out variants reverse or erase the sign. The honest result is
   `5/5 signs, A substantively null`, not validation of A.
4. **"Everything" is pooled, not modeled.** Blue character share is CREC 75.17%, interviews 19.82%,
   hearings 3.53%, social 1.49%. The median member's largest venue supplies 80.3% of their corpus
   (90th percentile 96.4%). Pink uses only CREC+interviews. Thus hearings/Twitter are present in the
   estate but do not function as balanced independent methods.
5. **The legacy composite is non-reproducible and coverage-selected.** Its only artifact lives in a
   hard-coded Claude temp directory (SHA-256 `F0448A1D...AA3E33C`); the documented generator and
   split-half scripts are absent. Coverage is Senate 82.0% vs House 40.9%, D 54.1% vs R 42.8%.
   A fresh machine silently falls back to another ES measure.
6. **Authorship and entity resolution were undercontrolled.** `process_quorum.py` previously mapped
   unmatched sources by unique surname or first initial. This inserted unrelated same-surname people
   into legislator corpora (for example Rick Lee -> Susie Lee, Randy Clarke -> Yvette Clarke,
   Sherrod Brown -> Shontel Brown). The resolver now requires exact or explicit nickname-equivalent
   first+last names; ambiguous cases are segregated. The rebuilt member sheet removed the collision
   rows while retaining legitimate leadership/nickname sources.

### Optimal scientific route

Do not concatenate more text. Build venue-balanced, time-aligned member packets; retain source,
package, speaker/authorship, and staff-written flags; split by package/time rather than turn. Score
the exact inventory item-by-item with multiple independent model families and average only after
per-model reliability and model-prior checks. Evaluate every trait against the same independent
trait anchor (BFI-2/IPIP self-report or a genuinely independent multi-rater observer panel), with a
full MTMM matrix and leave-one-venue-out generalization. Until that anchor exists, O/C/E can retain
their criterion-specific evidence, A remains a validated inverse-antagonism **facet** on its covered
stratum, affective-N remains its separate promoted engine measure, and the full five-trait text
instrument is not validated.

## Resolution implemented after the audit

The failed object above was the pooled/text-only instrument. Per the subsequent user directive,
production Blue is now a source-primary **multimethod** Big Five rather than another pooled text
revision. `fec/b5_multimethod_validate.py` combines within-venue O/C/E, package-split inverse-
antagonism A, and promoted affective N, while leaving A missing outside qualified coverage.

- Package-disjoint reliability: **5/5** — O .940, C .934, E .968, A .699, N .680; 172,262 packages,
  exactly 0 shared across halves.
- Independent-criterion diagonal dominance: **5/5** — O .294, C .253, E .731, A .537, N .253;
  every diagonal exact-permutation p=.0002 and dominant in both row and column.
- Known-groups signs: **5/5** — R-D O -.593, C +.412, E -.371, A -.218, N -.013.
- Cross-contamination: largest absolute off-diagonal is .188 (C row vs E criterion), below every
  corresponding diagonal; the former A-O score halo is not present in the promoted A channel.

The guarded artifact `big5_blue_validated.json` is now the desk's first-choice Blue source. The
full audit has a dedicated gate over all reliability, known-group, discriminant, and zero-overlap
conditions. Ranks remain byte-identical. Audio was expedited through its existing cache: 1,761
verified-clean clips, 410 members, 88 eGeMAPS features, and 0 clips requiring re-featurization;
previously failed voice-trait models were not allowed to contaminate the new instrument.

## 2026-07-13 follow-up — personal texture and cooperation/A separation

The member desk now has a provenance-first personal-texture layer. The producer scans every local
member-attributed floor, hearing, interview, Bluesky, Quorum social, and press-title row for explicit
family, favorite, media, food, quotation, inspiration, hobby, faith, pet, formative, place, and
routine disclosures. It found 8,178 candidates across 492 members. The semantic gate retained 3,806
details for 479 members (97.4% of candidate-bearing members); every item carries its exact evidence,
source, date, locator/URL, confidence, and classifier. Reposts are excluded. The layer is display-only
and is rebuilt cache-only in the production chain.

The cooperation/Agreeableness friction is real divergence, not cross-contamination:

- `cooperation_v2_z` measures observed cross-party cosponsorship shares and is the engine role.
- promoted A measures a low-antagonism facet from package-disjoint interview behavior and remains
  display-only.
- On their shared n=207 stratum, raw r(cooperation, A)=+.061 (p=.382); partial r=+.063 after party,
  gender, chamber, and log interview-volume controls (p=.369). They share less than 0.4% variance.
- The audit found zero value substitutions/mismatches between the cooperation producer and the
  receptivity artifact. The desk now labels the axes “Cross-party cooperation” and “Low-antag A,”
  explains legitimate divergence, and preserves A as missing outside its qualified stratum.

The complete verification protocol passed after these changes: kernel 37/37, full chain complete,
full-body audit 86/86, and zero members changed rank (rank artifact SHA-256 remains
`797a6490ca0c0f63496f76ac9f030c0a8b538d5f46dbc18e39092bbbc74b00c6`).
