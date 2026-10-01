# Geospatial — quant-model-evaluation reference

> **Load when:** a result depends on where things are: district, county, ZIP or media-market aggregates; ZIP-to-district crosswalks for donor or customer money; spatial joins and areal interpolation; census or ACS covariates for small areas; spatial dependence in model residuals; designs built on a geographic boundary; anything tied to district lines that were redrawn. **Not for:** bank-deposit, credit-union and CRA geography (`finance.md`); causal identification in general (`social-science.md`); map design and honest encoding (`data-visualization.md`); data-use law (`regulatory.md`); split design for spatial prediction models (`machine-learning.md` §2.2).
> Facts marked (as of DATE) are time-sensitive; re-verify before relying on them. Every Python snippet below was run on synthetic data with a known answer (geopandas 1.1.4, shapely 2.1.2, pyproj 3.8.0, pandas 3.0.3, scipy 1.18.0; as of 2026-09-30).
> A KILLED printed by a script is a candidate until a second independent reader confirms it (SKILL.md hard rule 5).

Geography enters most political-finance systems twice: as a unit of analysis (money by district, deposits by county) and as a join key (a donor's ZIP mapped to a district). Each brings its own assumptions. Start every audit by writing down which unit the claim is about and which unit the data were measured in.

## 1. Assumption map

| Assumption (class) | Where it usually hides | What breaks if it is false | Tests |
|---|---|---|---|
| Results do not depend on the zoning or scale of aggregation (`FUNCTIONAL-FORM`) | Money by ZIP vs county vs district vs media market | Sign or size flips between levels | 2.1; GEO-01, GEO-02 |
| Aggregate relations describe individuals (`MEASUREMENT`, `CAUSAL`) | "Donors in district X prefer ..." drawn from district totals | Ecological fallacy | 2.1; GEO-01 |
| Units are spatially independent (`STATISTICAL`) | Residuals of county or district regressions | Standard errors too small; "significant" effects from spatial noise | 2.2; GEO-03 to GEO-06 |
| The spatial model's weights matrix and form are right (`FUNCTIONAL-FORM`) | Spatial lag and error models; rho near 1 | Conclusions that move with W; lag coefficients misread as marginal effects | 2.3; GEO-07 |
| Treatment is as-if random near a boundary (`CAUSAL`) | State-line, district-line or media-market designs | Sorting or bundled treatments read as one effect | 2.4; GEO-08 |
| A ZIP is an area, and ZIP = ZCTA (`DATA`) | Donor and customer geocoding | Misallocated money; PO-box and unique ZIPs silently dropped | 2.5; GEO-09, GEO-12 |
| Crosswalk weights are valid shares of the quantity allocated (`MEASUREMENT`) | Modal assignment; address ratios used as dollar or population shares | In-district shares wrong by the whole split ZIP | 2.5; GEO-10, GEO-11, GEO-13 |
| A district code names the same place over time (`DATA`) | Panels across redistricting; mid-decade maps; different primary and general maps | Covariates from one plan attached to members elected under another | 2.6; GEO-14 to GEO-17 |
| Small-area census counts and ACS estimates are exact (`MEASUREMENT`) | Block counts; tract and block-group ACS tables | Noise read as signal; biased covariates | 2.7; GEO-18, GEO-19 |
| Areal interpolation weights follow the attribute (`FUNCTIONAL-FORM`) | Area weighting across uneven population; summed rates | Counts moved onto empty land; meaningless sums | 2.8; GEO-20 |
| The CRS is known and fit for the operation; joins have the declared cardinality (`COMPUTATIONAL`, `DATA`) | Areas in degrees or Web Mercator; `set_crs` used to "fix" a mismatch; inner joins | Wrong areas and distances; rows silently duplicated or dropped | 2.9; GEO-21 to GEO-23 |
| Geocoding is complete and non-selective (`DATA`) | Rural routes, PO boxes, malformed addresses | Coverage that differs by place or donor type biases every aggregate | 2.10; GEO-24 |
| A booked location is the economic location (`DATA`) | Deposits by branch; credit-union headquarters | Money attributed to the wrong district | 2.11; GEO-25 |

## 2. Tests

`scripts/spatial_audit.py` reads vector files (.gpkg, .geojson, .json, .shp, .parquet, .geoparquet) and tables (.csv, .tsv) only; it refuses URLs, GDAL `/vsi` paths and .vrt files, which GDAL could fetch over the network (as of 2026-09-30). Convert other formats to a local GeoPackage first.

### 2.1 MAUP and the ecological fallacy
- **Tests:** whether a result survives a change of zoning or scale (the modifiable areal unit problem: multivariate results change with both; Fotheringham & Wong 1991), and whether an aggregate relation is being read as an individual one (Robinson 1950). Openshaw's 1984 monograph is the usual origin citation but is not indexed in CrossRef or OpenAlex (UNVERIFIED).
- **Assumptions of the test itself:** the alternative levels are meaningful for the claim; each aggregate uses the sums or rates the claim is about.
- **Run it:** re-estimate at every available level:
```python
import numpy as np

def slope(frame):
    return np.polyfit(frame["x"], frame["y"], 1)[0]

for level in ["zip", "county", "district"]:
    agg = df.groupby(level)[["x", "y"]].mean()     # use the sums or rates the claim is about
    print(level, len(agg), round(slope(agg), 3))
```
  On synthetic data built with a within-district slope of −1 and a between-district slope of +2, every aggregate level returned about +2: aggregation alone cannot reveal the individual relation. Individual-level claims from aggregates need an explicit ecological-inference model with bounds (King 1997; `social-science.md`).
- **Pass criterion (fix before running):** the same sign at every level examined, and size within a ratio fixed in advance (for example a factor of 2); otherwise WOUNDED, with the claim restricted to the level estimated.
- **Failure signature:** the sign flips between ZIP- and district-level aggregation; individual-level wording from district data; results shown at one scale only.
- **Source:** Fotheringham & Wong (1991); Robinson (1950); King (1997).

### 2.2 Spatial autocorrelation: global Moran's I, LISA and residuals
- **Tests:** whether values, and above all model residuals, are spatially dependent. Global Moran's I measures similarity among neighbours (Moran 1950). LISA splits it into local clusters and outliers, which need permutation inference and multiplicity control (Anselin 1995). Spatially autocorrelated noise can yield large t-statistics in persistence-style regressions, so compare with spatial-HAC (Conley) standard errors and with regressions on simulated spatial noise (Conley 1999; Conley & Kelly 2025). Spatial prediction models need spatially blocked CV folds (Roberts et al. 2017).
- **Assumptions of the test itself:** the weights matrix W (queen or rook contiguity, k nearest neighbours) reflects plausible interaction and is fixed before testing; islands (units without neighbours) are handled explicitly; permuting OLS residuals is approximate, and `spdep::lm.morantest()` accounts for their estimation.
- **Run it:** `python scripts/spatial_audit.py --mode autocorr --geo districts_resid.gpkg --var resid --weights queen --perm 999`
  (`--engine auto|esda|numpy` picks the Moran engine; when esda runs, the numpy path is computed as well and AC-PATH checks that the two statistics agree within `--parity-tol`; LISA cluster counts are opt-in with `--lisa` (needs esda; slow); the p-value is two-sided and islands are flagged). Numpy version with k-nearest-neighbour weights on projected centroids (dense W: keep n to a few thousand; duplicate points break the self-neighbour step):
```python
import numpy as np
from scipy.spatial import KDTree

def moran_knn(xy, z, k=6, perm=999, seed=20260930):
    """Global Moran's I, row-standardized k-nearest-neighbour weights, one-sided permutation p."""
    n = len(z); _, nb = KDTree(xy).query(xy, k=k + 1)
    W = np.zeros((n, n)); W[np.repeat(np.arange(n), k), nb[:, 1:].ravel()] = 1.0 / k
    zc = np.asarray(z, float) - np.mean(z)
    stat = lambda v: (v @ W @ v) / (v @ v)          # row-standardized, so S0 = n
    obs = stat(zc); rng = np.random.default_rng(seed)
    sims = np.array([stat(rng.permutation(zc)) for _ in range(perm)])
    return obs, (1 + np.sum(sims >= obs)) / (perm + 1)
```
  Known answers on a 20 × 20 lattice with k = 4: smooth gradient I = 0.99 (p = 0.001); checkerboard I = −0.90; white noise I = −0.03 (p = 0.78). In R (needs spdep; run on synthetic data with spdep 1.4.2: residual I = 0.90 with a planted spatial trend, −0.10 with p = 0.94 on independent noise):
```r
library(sf); library(spdep)
g   <- st_read("districts.gpkg"); fit <- lm(y ~ x, data = g)
lw  <- nb2listw(poly2nb(g, queen = TRUE), style = "W", zero.policy = TRUE)
lm.morantest(fit, lw, zero.policy = TRUE)      # residual Moran's I
lm.RStests(fit, lw, test = "all")              # lag vs error diagnostics (successor to lm.LMtests)
```
- **Pass criterion (fix before running):** for any model that assumes independent errors, residual Moran's I not significant at the level fixed in advance → SURVIVES; significant → WOUNDED (the script's rule) until inference is redone with spatial-HAC standard errors and a placebo on simulated spatial noise fails to reproduce the effect's t-statistic; the verdict holds under a second W.
- **Failure signature:** significant residual Moran's I; the effect vanishes under Conley standard errors; placebo noise gives similar t-statistics; LISA "hot spots" reported without multiplicity correction.
- **Source:** Moran (1950); Anselin (1995); Conley (1999); Conley & Kelly (2025); Roberts et al. (2017).

### 2.3 Spatial lag and error models
- **Tests:** whether a spatial regression is specified and read correctly. A spatial lag (SAR) model lets each outcome depend on neighbouring outcomes; a spatial error model lets the errors do so (Anselin 1988; Franzese & Hays 2007; Darmofal 2015). Lagrange-multiplier diagnostics help choose between them (Anselin et al. 1996). In a lag model a coefficient is not a marginal effect: report direct, indirect and total impacts (LeSage & Pace 2009). Identification often rests on the chosen W and functional form rather than on a design, so prefer quasi-experimental variation for causal claims (Gibbons & Overman 2012).
- **Assumptions of the test itself:** W is chosen in advance, not searched over; rho is estimated away from its bounds.
- **Run it:** R `spatialreg::lagsarlm()`, `errorsarlm()` and `impacts()` (needs spatialreg); Python `spreg` (needs spreg). Fit under two W (for example queen contiguity and k = 6) and compare the impacts.
- **Pass criterion (fix before running):** impacts keep their sign and stay within a tolerance fixed in advance across both W; rho clearly inside (−1, 1); causal wording only with a design (`social-science.md`).
- **Failure signature:** conclusions that change with W; rho near 1; lag-model coefficients quoted as marginal effects without `impacts()`.
- **Source:** Anselin (1988); Anselin et al. (1996); Franzese & Hays (2007); LeSage & Pace (2009); Gibbons & Overman (2012); Darmofal (2015).

### 2.4 Geographic-boundary regression discontinuity
- **Tests:** effects of treatments that switch at a line on the map (a state border, a district line, a media-market edge). Keele & Titiunik (2015) show that the running variable is two-dimensional (distance to the border and position along it), that the effect can vary along the border, that one border often bundles several treatments, and that people and firms may sort across it.
- **Assumptions of the test itself:** the border segment used is where treatment actually changes; distances come from a projected CRS; covariates are measured before treatment.
- **Run it:** signed distance to the shared border, positive on the treated side:
```python
import numpy as np

border = treated.union_all().boundary.intersection(control.union_all().boundary)
dist = pts.geometry.distance(border)               # CRS units: use a projected CRS
signed = np.where(pts.geometry.within(treated.union_all()), dist, -dist)
```
  Estimation: R `rdmulti`, `SpatialRDD::spatialrd()` and `border_segment()`; Python `rdrobust` on the signed distance (needs rdrobust). RD diagnostics (density, covariate continuity, bandwidth choice) are in `social-science.md`.
- **Pass criterion (fix before running):** no sorting or covariate jump at the border at the level fixed in advance; the same sign of effect across border segments; the treatments that change at the border are named, not assumed to be one.
- **Failure signature:** the effect comes from one segment only; covariates jump at the border; a state line that also changes taxes, media markets and law is credited to one policy.
- **Source:** Keele & Titiunik (2015).

### 2.5 ZIPs, ZCTAs and crosswalk allocation
- **Tests:** whether money or people located by ZIP code are assigned to districts correctly.
  - A ZIP is a USPS delivery attribute, not an area. ZCTAs are Census approximations of ZIPs; PO-box-only and single-organization ZIPs have no ZCTA, and ZIPs change while ZCTAs are fixed per census (Grubesic & Matisziw 2006; Krieger et al. 2002).
  - Many ZIPs straddle district lines. The HUD-USPS ZIP-to-congressional-district crosswalk is quarterly, and its residential, business, other and total ratios are shares of addresses, not of people or dollars (Wilson & Din 2018; huduser.gov/portal/datasets/usps_crosswalk.html, as of 2026-09-30).
  - Allocate a split ZIP by ratio and carry the allocation uncertainty; assigning the whole ZIP to its modal district discards it. Use ZIP+4 where present.
  - A contributor ZIP is a mailing address, and much money comes from outside the recipient's district; on the concentrated geography of contributions see Gimpel et al. (2006).
- **Assumptions of the test itself:** the crosswalk quarter matches the transaction dates and the district plan (2.6); the ratio chosen (residential for individual donors, business for firms) is stated and justified.
- **Run it:** `python scripts/spatial_audit.py --mode crosswalk --xwalk zip_cd.csv --from zip --to cd --weight res_ratio --units donor_zips.csv --unit-col zip`
  (weights in [0, 1] summing to 1 per ZIP within `--tol` 0.001; share of split ZIPs; coverage of your ZIP list; lost leading zeros and ZIP+4 values; the ZIP-is-not-an-area assumption is always reported UNVERIFIED-HERE because a file cannot show it). Allocation and bounds by hand:
```python
import pandas as pd

xw = pd.read_csv("zip_cd.csv", dtype={"zip": str, "cd": str})        # keep leading zeros
gifts = pd.read_csv("gifts.csv", dtype={"zip": str})
gifts["zip5"] = gifts["zip"].str[:5]                                 # ZIP+4 -> ZIP5
wsum = xw.groupby("zip")["res_ratio"].sum()
n_cd = xw.groupby("zip")["cd"].nunique()
print("ZIPs whose weights do not sum to 1:", int(((wsum - 1).abs() > 1e-3).sum()))
print("share of ZIPs split across districts:", float((n_cd > 1).mean()))
print("unmatched dollars:", gifts.loc[~gifts["zip5"].isin(xw["zip"]), "amount"].sum())
alloc = gifts.merge(xw, left_on="zip5", right_on="zip")              # one row per gift x district
ratio_by_cd = (alloc["amount"] * alloc["res_ratio"]).groupby(alloc["cd"]).sum()
D = "XX-07"                                                          # district being audited
touch = set(xw.loc[xw["cd"] == D, "zip"])
whole = set(n_cd.index[n_cd == 1]) & touch
lower = gifts.loc[gifts["zip5"].isin(whole), "amount"].sum()         # ZIPs wholly inside D
upper = gifts.loc[gifts["zip5"].isin(touch), "amount"].sum()         # every ZIP touching D
```
  In the synthetic check, ratio allocation gave the audited district $900, inside the bounds [$500, $1,500]; modal assignment gave it $500 by moving a split ZIP's $1,000 to its neighbour. R: `zctaCrosswalk::get_zctas_by_state()`, `zippeR::zi_crosswalk()`, `tigris::zctas()`.
- **Pass criterion (fix before running):** weights sum to 1 (±0.001) for every ZIP; unmatched ZIPs reported in rows and dollars and below a share fixed in advance; the conclusion (for example "most money is in-district") holds at both bounds, otherwise WOUNDED with the bounds shown.
- **Failure signature:** ZIPs read as integers (leading zeros lost, as in New England, New Jersey and Puerto Rico); modal assignment; address ratios presented as dollar shares; a crosswalk from the wrong quarter or plan; PO-box ZIPs dropped silently.
- **Source:** Grubesic & Matisziw (2006); Krieger et al. (2002); Wilson & Din (2018); Gimpel et al. (2006); Fotheringham & Wong (1991).

### 2.6 Redistricting: pin every record to the plan in force
- **Tests:** whether district-level data are attached to the map in force on each election date. A code such as "XX-07" is not the same place across plans, and a primary and a general election can use different maps. Member-constituency covariates (industry employment, deposit shares, in-district money) must be recomputed for each plan.
- **Status (as of 2026-09-29; secondary sources, UNVERIFIED against enacted plans or court orders; re-verify before relying).** Maps drawn after the 2020 census took effect for 2022; these states were reported with new or contested maps for 2026:

| State | New map for 2026 | Date (reported) | How | Note |
|---|---|---|---|---|
| TX | Yes | 2025-08-29 | Legislature | |
| NC | Yes | 2025-10-22 | Legislature | |
| OH | Yes | 2025-10-31 | Commission | |
| CA | Yes | 2025-11-04 | Ballot measure (Prop 50) | |
| UT | Yes | 2025-11-10 | Court-ordered | |
| FL | Yes | 2026-05-04 | Legislature | |
| TN | Yes | 2026-05-07 | Legislature | |
| LA | Yes | 2026-05-29 | Legislature | After *Callais* |
| AL | Yes | 2026-06-02 | Legislature | After *Callais* |
| MO | Contested | 2025-09-28 | Legislature | August 2026 primary on the 2025 map; on 2026-09-03 the state supreme court ordered the 2022 map for November, pending a referendum; later U.S. Supreme Court orders reported |
| VA | No | 2026-04-21 | Referendum | Reportedly struck down by the state supreme court |

  A second tracker (dated 2026-05-11) lists a partly different set; the sources disagree by date. *Louisiana v. Callais*, No. 24-109, was decided 2026-04-29 (date and docket from the Supreme Court's slip-opinion listing). Research summaries describe it as holding Louisiana's second majority-Black district an unconstitutional racial gerrymander and narrowing Section 2 obligations; that description was not checked against the opinion (UNVERIFIED). Legal consequences are for counsel; `regulatory.md` owns law.
- **Assumptions of the test itself:** the plan table (state, election type, plan ID, valid from, valid to) is built from enacted plans and court orders, not from news summaries.
- **Run it:** every row must match exactly one plan:
```python
m = rows.merge(plans, on=["state", "election_type"], how="left")   # plans: one row per validity window
m = m[(m["election_date"] >= m["valid_from"]) & (m["election_date"] < m["valid_to"])]
n_plans = m.groupby("row_id").size().reindex(rows["row_id"], fill_value=0)
print("rows with no plan:", int((n_plans == 0).sum()), "rows with >1 plan:", int((n_plans > 1).sum()))
```
  Boundaries: R `tigris::congressional_districts()`; plan ensembles for counterfactual maps: `redist::redist_smc()` (McCartan & Imai 2023); tract histories: Logan et al. (2014); colliding boundaries: Amos et al. (2017).
- **Pass criterion (fix before running):** every district-level row pinned to exactly one plan; covariates recomputed per plan; panels that cross a plan change either re-aggregated to stable units or split at the change.
- **Failure signature:** 2022-plan covariates attached to members elected under a 2026 plan; district identifiers used as stable panel IDs; one map assumed for a state whose primary and general used different ones.
- **Source:** Cho & Gimpel (2012); Amos et al. (2017); McCartan & Imai (2023); Logan et al. (2014).

### 2.7 Small-area census noise: differential privacy and ACS margins of error
- **Tests:** whether small-area counts and survey estimates used as covariates are precise enough for the claim.
  - 2020 Census data were released through a differential-privacy system. It systematically undercounts mixed-race and mixed-partisan precincts, with unpredictable racial and partisan biases (Kenny et al. 2021); its errors are relatively large for small-population geographies, and the noisy measurement file needs measurement-error modelling (Kenny et al. 2024).
  - ACS estimates carry margins of error that are often large for tracts and block groups, and data quality varies across places (Spielman et al. 2014; Folch et al. 2016). Published ACS margins of error are 90% intervals, so SE = MOE / 1.645.
- **Assumptions of the test itself:** the MOE of a derived quantity is approximated (the standard formulas for sums, ratios and proportions ignore covariance); 1-year and 5-year ACS are not mixed, and overlapping 5-year periods, which share survey years, are not treated as independent.
- **Run it:**
```python
import numpy as np

se = moe / 1.645                              # ACS margins of error are 90% intervals
moe_sum = np.sqrt(np.sum(moe_parts ** 2))     # approximate MOE of a sum (ignores covariance)
cv = se / est                                 # flag units above a CV fixed in advance
```
  Then re-run the analysis with high-CV units dropped or aggregated and compare signs.
- **Pass criterion (fix before running):** no block-level 2020 counts used as covariates; each ACS covariate carries its SE into the analysis or is aggregated until its CV is below a threshold fixed in advance; conclusions unchanged when high-CV units are excluded.
- **Failure signature:** block counts used directly; tract or block-group shares used as exact covariates; results that change sign when the noisiest units are dropped.
- **Source:** Kenny et al. (2021); Kenny et al. (2024); Spielman et al. (2014); Folch et al. (2016).

### 2.8 Areal interpolation: area versus population weights
- **Tests:** whether values moved from one set of units to another (tracts to districts, an old plan to a new one) follow where the attribute actually is. Area weighting assumes the attribute is spread evenly over land. Population (dasymetric) weighting distributes it with a finer population layer and is preferred where population is uneven (Eicher & Brewer 2001; Logan et al. 2014).
- **Assumptions of the test itself:** areas come from an equal-area CRS; the target layer covers the source layer, so weights sum to 1; only extensive variables (counts, dollars) are split by weight, while intensive ones (rates, medians, shares) are rebuilt from interpolated numerators and denominators.
- **Run it:** area weights with a coverage check:
```python
import geopandas as gpd

src = src.to_crs("EPSG:5070"); tgt = tgt.to_crs("EPSG:5070")   # equal-area CRS (CONUS)
src["a_src"] = src.area
pieces = gpd.overlay(src[["sid", "count", "a_src", "geometry"]], tgt[["tid", "geometry"]],
                     how="intersection")
pieces["w"] = pieces.area / pieces["a_src"]
print("max |weights - 1| per source:", (pieces.groupby("sid")["w"].sum() - 1).abs().max())
est = (pieces["count"] * pieces["w"]).groupby(pieces["tid"]).sum()   # counts only, never rates
```
  For population weights, replace each piece's area with the population of the finer units (for example census blocks) that fall inside it. R: `areal::aw_interpolate()`.
- **Pass criterion (fix before running):** weights sum to 1 per source unit within a tolerance fixed in advance, or the uncovered share is reported; totals are preserved; area- and population-weighted results agree in sign and within a tolerance, or the population-weighted one is used.
- **Failure signature:** plain area weighting across sparsely populated tracts; rates or medians summed; weights that miss 1 because layers do not align (slivers, different vintages); areas computed in degrees.
- **Source:** Eicher & Brewer (2001); Logan et al. (2014); Amos et al. (2017).

### 2.9 CRS discipline and join cardinality
- **Tests:** whether coordinates are interpreted correctly and whether joins create, drop or duplicate rows.
  - A CRS is part of the data: require it on every layer and never infer it from coordinate ranges. `set_crs()` only relabels; `to_crs()` transforms.
  - Planar operations (area, distance, buffers, nearest joins) need a projected CRS: equal-area for areas, a local conformal or equidistant one for distances. Web Mercator (EPSG:3857) is for display only.
  - Before every `merge`, `sjoin` or `sjoin_nearest`, declare the expected cardinality (1:1, 1:m, m:1, m:m); afterwards count unmatched and multiplied rows on both sides. Predicates are directional and differ at boundaries: a point on a shared line is `within` neither polygon but `intersects` both.
- **Assumptions of the test itself:** the declared cardinality comes from the data model, not from the observed result; both sides carry stable feature IDs.
- **Run it:** `python scripts/spatial_audit.py --mode join --left donors.gpkg --right districts_2026.gpkg --sjoin within` or, for keys, `python scripts/spatial_audit.py --mode join --left tracts.gpkg --right acs.csv --left-key GEOID --right-key GEOID --expect 1:1 --max-unmatched 0.01`
  (cardinality against `--expect`, unmatched rows, key hygiene, CRS presence and equality, CRS fit for area and distance, geometry validity). By hand:
```python
import geopandas as gpd

for name, g in {"points": pts, "districts": cds}.items():
    assert g.crs is not None, f"{name}: CRS missing; recover it from the source, never guess"
pts = pts.to_crs(cds.crs)                          # to_crs transforms; set_crs only relabels
j = gpd.sjoin(pts, cds[["cd", "geometry"]], how="left", predicate="within")
print("multi-matched points:", int(j.index.duplicated().sum()),
      "unmatched points:", int(j["cd"].isna().sum()))
m = cov.merge(outcomes, on="geoid", how="outer", validate="one_to_one", indicator=True)
print(m["_merge"].value_counts().to_dict())       # left_only / right_only = unmatched keys
area_km2 = cds.to_crs("EPSG:5070").area / 1e6      # CONUS equal-area; never EPSG:4326 or 3857
```
  Known answers: a 1° × 1° cell at 40° N measures 9,413 km² in EPSG:5070, matching its geodesic area; Web Mercator gives 16,297 km² (73% too large) and EPSG:4326 an "area" of 1.0 square degree. Alaska and Hawaii need their own equal-area projections.
- **Pass criterion (fix before running):** CRS present and identical on joined layers; a projected CRS for every measurement; observed cardinality equal to the declared one; unmatched share at or below `--max-unmatched` (default 0.01).
- **Failure signature:** areas or distances in degrees or Web Mercator; `set_crs()` used to "fix" a mismatch; an inner join that silently drops unmatched rows; boundary points lost with `within` or double-counted with `intersects`.
- **Source:** the correctness gates of the K-Dense `geopandas` skill (adapted; see §5).

### 2.10 Geocoding coverage and selective non-match
- **Tests:** whether records that fail to geocode differ from those that succeed. Failure is rarely random: PO boxes, rural routes, new developments and malformed addresses cluster in particular places and among particular filers.
- **Assumptions of the test itself:** the match level is recorded (rooftop, street segment, ZIP centroid); coverage is measured in the quantity of interest (dollars, people), not only in rows.
- **Run it:** tabulate match rate and match level by state, urban or rural status, amount band and source; compare amount distributions of matched and unmatched records (for example `scipy.stats.mannwhitneyu`); report unmatched dollars next to unmatched rows. `spatial_audit.py --mode join` reports unmatched rows for the point-in-polygon step.
- **Pass criterion (fix before running):** match rate at or above a level fixed in advance, overall and in every reported subgroup; matched and unmatched records similar on the audited dimensions; ZIP-centroid matches never used for sub-ZIP geography.
- **Failure signature:** coverage that differs by state or urbanicity; unmatched records concentrated among large or small amounts; ZIP centroids treated as addresses.
- **Source:** Krieger et al. (2002); Grubesic & Matisziw (2006).

### 2.11 Finance geography (pointer)
- **Tests:** whether a "deposits by district" or "institution presence" measure says which location it uses. Deposits in the FDIC Summary of Deposits are booked at offices by each bank's internal rules, not at depositors' homes; credit unions are not in it, and published NCUA call-report files give no branch-level shares. Data details: `finance.md`. Community Reinvestment Act scope and status, including coverage of credit unions: the CRA row in `regulatory.md`.
- **Assumptions of the test itself:** the measure's code or documentation shows its location field.
- **Run it:** read the location field (booked office, headquarters, member address) and the plan vintage (2.6); join institutions to districts with `--mode join --sjoin within` (2.9).
- **Pass criterion (fix before running):** the label names the location basis and the plan vintage; no depositor-residence wording for booked deposits.
- **Failure signature:** "deposits of district residents" computed from booked office locations; credit-union presence taken from headquarters alone without saying so.
- **Source:** `finance.md` (FDIC Summary of Deposits instructions; NCUA call-report files) and `regulatory.md` (CRA row).

## 3. Checklist

- **GEO-01** State the unit of analysis and the unit of inference; allow no individual-level wording from aggregates without an explicit model. `MEASUREMENT` · 2.1
- **GEO-02** Re-estimate key results at two or more aggregation levels and report sign and size at each. `FUNCTIONAL-FORM` · 2.1
- **GEO-03** Test residual spatial autocorrelation for every model that assumes independent errors (`scripts/spatial_audit.py --mode autocorr --var resid`). `STATISTICAL` · 2.2
- **GEO-04** Where residual Moran's I is significant, redo inference with spatial-HAC (Conley) standard errors and a simulated spatial-noise placebo. `STATISTICAL` · 2.2
- **GEO-05** Fix the weights matrix before testing, report it, and repeat under a second W. `FUNCTIONAL-FORM` · 2.2, 2.3
- **GEO-06** Treat LISA clusters as exploratory and control multiplicity. `STATISTICAL` · 2.2
- **GEO-07** For spatial lag or error models, report direct and indirect impacts, rho and W-sensitivity; make causal claims only with a design. `CAUSAL` · 2.3
- **GEO-08** For boundary designs, check sorting, covariate balance near the border, bundled treatments and variation along the border. `CAUSAL` · 2.4
- **GEO-09** Keep ZIPs as five-character strings; never treat a ZIP as an area or as equal to a ZCTA. `DATA` · 2.5
- **GEO-10** Allocate ZIP-to-district money with ratio weights, not modal assignment, and state which ratio and why. `MEASUREMENT` · 2.5
- **GEO-11** Verify that crosswalk weights sum to 1 per source unit and cover every unit in use (`--mode crosswalk --units`). `DATA` · 2.5
- **GEO-12** Report unmatched, PO-box and unique ZIPs in rows and in dollars. `DATA` · 2.5, 2.10
- **GEO-13** Show lower and upper bounds for any in-district share and say whether the conclusion survives both. `MEASUREMENT` · 2.5
- **GEO-14** Match vintages: crosswalk quarter, district plan and transaction or election date. `DATA` · 2.5, 2.6
- **GEO-15** Pin every district-level record to exactly one plan valid on its election date and election type. `DATA` · 2.6
- **GEO-16** Recompute member-constituency covariates for each plan; never use a district code as a stable ID across plans. `DATA` · 2.6
- **GEO-17** Date-stamp every redistricting fact and verify it against enacted plans or court orders before relying on it. `DATA`, `LEGAL` · 2.6
- **GEO-18** Use no block-level 2020 Census counts as covariates; aggregate or model the privacy noise. `MEASUREMENT` · 2.7
- **GEO-19** Carry ACS margins of error (SE = MOE / 1.645) into derived estimates and flag high-CV units. `MEASUREMENT` · 2.7
- **GEO-20** Interpolate counts with population weights where population is uneven; never sum intensive variables. `FUNCTIONAL-FORM` · 2.8
- **GEO-21** Require CRS metadata on every layer; measure areas in an equal-area CRS and distances in a suitable projected CRS. `COMPUTATIONAL` · 2.9
- **GEO-22** Declare join cardinality before every merge or spatial join and audit unmatched and multiplied rows after it (`--mode join --expect`). `DATA` · 2.9
- **GEO-23** Choose spatial predicates deliberately (`within`, `intersects`, `covers`) and count boundary cases. `COMPUTATIONAL` · 2.9
- **GEO-24** Report geocoding match rate and match level by subgroup and in dollars; test for selective non-match. `DATA` · 2.10
- **GEO-25** Label deposit and institution geography as booked or headquarters locations; follow `finance.md` for data limits and the `regulatory.md` CRA row for CRA scope. `DATA` · 2.11
- **GEO-26** Use spatially blocked folds when validating a spatial prediction model (`machine-learning.md` §2.2). `STATISTICAL` · 2.2
- **GEO-27** On maps of rates for small-population units, show uncertainty or shrinkage and never rank units by raw rates (Gelman & Price 1999; `data-visualization.md`). `PRESENTATION`

## 4. Pitfalls and anti-patterns

- Reading ZIPs as integers (leading zeros lost), truncating ZIP+4 into the wrong ZIP, or joining ZIP-coded data to ZCTA polygons as if they were the same thing.
- Assigning a split ZIP wholly to its modal district, or using HUD address ratios as dollar shares without saying so.
- A crosswalk from a different quarter, or a pre-redistricting plan, joined to current money.
- District codes used as panel IDs across plans; one map assumed for both primary and general.
- Area weighting across uneven population; summing rates, medians or shares.
- Computing areas or distances in EPSG:4326 or Web Mercator; using `set_crs()` where `to_crs()` was needed.
- `sjoin` with `within` losing boundary points, or `intersects` double-counting them; inner joins that drop unmatched rows silently.
- Moran's I computed on the raw outcome when the question is whether the model's errors are independent.
- LISA hot spots reported without multiplicity control; spatial lag coefficients read as marginal effects.
- Individual-level language ("donors here prefer...") from district aggregates.
- Block-level 2020 counts, or tract ACS estimates with large margins, treated as exact; 1-year and 5-year ACS mixed.
- Maps that rank small counties by raw rates, where the extremes are mostly noise (Gelman & Price 1999).
- Geocoding failures dropped instead of counted and characterized.
- Deposits "by district" presented as where depositors live.

## 5. References

Verified in the research files (CrossRef or OpenAlex), except items marked [this build], which were checked against CrossRef (CR) on 2026-09-30 while writing this module.

- Amos, B., McDonald, M. P., & Watkins, R. (2017). When boundaries collide. *Public Opinion Quarterly* 81(S1), 385-400. doi:10.1093/poq/nfx001
- Anselin, L. (1988). *Spatial Econometrics: Methods and Models*. Springer. doi:10.1007/978-94-015-7799-1
- Anselin, L. (1995). Local indicators of spatial association—LISA. *Geographical Analysis* 27(2), 93-115. doi:10.1111/j.1538-4632.1995.tb00338.x
- Anselin, L., Bera, A. K., Florax, R., & Yoon, M. J. (1996). Simple diagnostic tests for spatial dependence. *Regional Science and Urban Economics* 26(1), 77-104. doi:10.1016/0166-0462(95)02111-6 [this build, CR]
- Cho, W. K. T., & Gimpel, J. G. (2012). Geographic information systems and the spatial dimensions of American politics. *Annual Review of Political Science* 15, 443-460. doi:10.1146/annurev-polisci-031710-112215
- Conley, T. G. (1999). GMM estimation with cross sectional dependence. *Journal of Econometrics* 92(1), 1-45. doi:10.1016/S0304-4076(98)00084-0
- Conley, T. G., & Kelly, M. (2025). The standard errors of persistence. *Journal of International Economics* 153, 104027. doi:10.1016/j.jinteco.2024.104027
- Darmofal, D. (2015). *Spatial Analysis for the Social Sciences*. Cambridge University Press. doi:10.1017/CBO9781139051293
- Eicher, C. L., & Brewer, C. A. (2001). Dasymetric mapping and areal interpolation: implementation and evaluation. *Cartography and Geographic Information Science* 28(2), 125-138. doi:10.1559/152304001782173727
- Folch, D. C., Arribas-Bel, D., Koschinsky, J., & Spielman, S. E. (2016). Spatial variation in the quality of American Community Survey estimates. *Demography* 53(5), 1535-1554. doi:10.1007/s13524-016-0499-1 [this build, CR]
- Fotheringham, A. S., & Wong, D. W. S. (1991). The modifiable areal unit problem in multivariate statistical analysis. *Environment and Planning A* 23(7), 1025-1044. doi:10.1068/a231025
- Franzese, R. J., & Hays, J. C. (2007). Spatial econometric models of cross-sectional interdependence in political science panel and time-series-cross-section data. *Political Analysis* 15(2), 140-164. doi:10.1093/pan/mpm005
- Gelman, A., & Price, P. N. (1999). All maps of parameter estimates are misleading. *Statistics in Medicine* 18(23), 3221-3234. doi:10.1002/(SICI)1097-0258(19991215)18:23<3221::AID-SIM312>3.0.CO;2-M
- Gibbons, S., & Overman, H. G. (2012). Mostly pointless spatial econometrics? *Journal of Regional Science* 52(2), 172-191. doi:10.1111/j.1467-9787.2012.00760.x
- Gimpel, J. G., Lee, F. E., & Kaminski, J. (2006). The political geography of campaign contributions in American politics. *Journal of Politics* 68(3), 626-639. doi:10.1111/j.1468-2508.2006.00450.x
- Grubesic, T. H., & Matisziw, T. C. (2006). On the use of ZIP codes and ZIP code tabulation areas (ZCTAs) for the spatial analysis of epidemiological data. *International Journal of Health Geographics* 5, 58. doi:10.1186/1476-072X-5-58
- Keele, L. J., & Titiunik, R. (2015). Geographic boundaries as regression discontinuities. *Political Analysis* 23(1), 127-155. doi:10.1093/pan/mpu014
- Kenny, C. T., Kuriwaki, S., McCartan, C., Rosenman, E. T. R., Simko, T., & Imai, K. (2021). The use of differential privacy for census data and its impact on redistricting: the case of the 2020 U.S. Census. *Science Advances* 7(41), eabk3283. doi:10.1126/sciadv.abk3283
- Kenny, C. T., McCartan, C., Kuriwaki, S., Simko, T., & Imai, K. (2024). Evaluating bias and noise induced by the U.S. Census Bureau's privacy protection methods. *Science Advances* 10(18), eadl2524. doi:10.1126/sciadv.adl2524
- King, G. (1997). *A Solution to the Ecological Inference Problem: Reconstructing Individual Behavior from Aggregate Data*. Princeton University Press. doi:10.1515/9781400849208 (De Gruyter digital edition)
- Krieger, N., Waterman, P., Chen, J. T., Soobader, M.-J., Subramanian, S. V., & Carson, R. (2002). Zip code caveat: bias due to spatiotemporal mismatches between zip codes and US census-defined geographic areas — the Public Health Disparities Geocoding Project. *American Journal of Public Health* 92(7), 1100-1102. doi:10.2105/AJPH.92.7.1100
- LeSage, J., & Pace, R. K. (2009). *Introduction to Spatial Econometrics*. Chapman and Hall/CRC. doi:10.1201/9781420064254 [this build, CR]
- Logan, J. R., Xu, Z., & Stults, B. J. (2014). Interpolating U.S. decennial census tract data from as early as 1970 to 2010: a longitudinal tract database. *Professional Geographer* 66(3), 412-420. doi:10.1080/00330124.2014.905156
- McCartan, C., & Imai, K. (2023). Sequential Monte Carlo for sampling balanced and compact redistricting plans. *Annals of Applied Statistics* 17(4). doi:10.1214/23-AOAS1763
- Moran, P. A. P. (1950). Notes on continuous stochastic phenomena. *Biometrika* 37(1/2), 17. doi:10.2307/2332142
- Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J., Guillera-Arroita, G., et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. *Ecography* 40(8), 913-929. doi:10.1111/ecog.02881
- Robinson, W. S. (1950). Ecological correlations and the behavior of individuals. *American Sociological Review* 15(3), 351. doi:10.2307/2087176
- Spielman, S. E., Folch, D., & Nagle, N. (2014). Patterns and causes of uncertainty in the American Community Survey. *Applied Geography* 46, 147-157. doi:10.1016/j.apgeog.2013.11.002 [this build, CR]
- Wilson, R., & Din, A. (2018). Understanding and enhancing the U.S. Department of Housing and Urban Development's ZIP code crosswalk files. *Cityscape* 20(2), 277-. Repository copy doi:10.13016/m2vt1gt2k (OpenAlex; no journal DOI found)
- UNVERIFIED: Openshaw, S. (1984). *The Modifiable Areal Unit Problem*. CATMOG 38, Geo Books. Not indexed in CrossRef or OpenAlex.
- [REG] *Louisiana v. Callais*, No. 24-109 (U.S., decided 2026-04-29). Date and docket from the Supreme Court slip-opinion listing; holding summary from CRS LSB11431 and news (not read here; UNVERIFIED). Status as of 2026-09-30.
- Data source: HUD USPS ZIP crosswalk files, huduser.gov/portal/datasets/usps_crosswalk.html (quarterly; as of 2026-09-30).

**Adapted from** (ideas paraphrased; no text or code copied): K-Dense-AI scientific-agent-skills (MIT) — `geopandas/SKILL.md` (correctness gates), `geopandas/references/crs-management.md`, `geopandas/references/spatial-analysis.md`, `geopandas/scripts/spatial_join_audit.py` (cardinality-audit design); `geomaster/SKILL.md` and `geomaster/references/coordinate-systems.md` (CRS guidance).
