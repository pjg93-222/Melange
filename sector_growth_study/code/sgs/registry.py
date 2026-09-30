"""Frozen, explicit registry of every test of the study (plan sections 2, 3, 5; staged plan approved 2026-09-25).

Each TestSpec names its DV, focal regressors, controls, fixed effects, sample-window rule and label.
Labels: CORE (the six core tests, nine DV runs), EXTENSION (planned secondary tests), ROBUSTNESS, EXPLORATORY,
DESCRIPTIVE (coefficients and HC1 reference errors only, no inference: the LobbyView tests L1-LV..L3-LV, Paul's
option (a)). Label assignments not fixed by the brief (H1/H4 read-outs, H1-phase-only, E1, T, DS, H5-pooled, H5-within
= EXTENSION; H5 robustness = ROBUSTNESS; H5 secondary regressors = EXPLORATORY) are this build's choice and are listed
in the report so they can be overruled.
Sector-year tests use the window rule of gates.py: primary 2020-2025 first; only on failure the most recent run of
>= 10 consecutive complete-case years within 2008-2025 (its most recent 10 years). H5 (unit board x champion x cycle,
05) uses the member-cycle gate of champions.py instead.
PREVIEW (Paul, 2026-09-25, "yes, run the preview too"): C1-PV..C3-PV (reduced, year-FE and full core specifications)
and H1-PV on the fixed window 2021-2025, 5 full years below the 6-year minimum; every PREVIEW output carries the flag
"PREVIEW - below the 6-year minimum" (config.PREVIEW_FLAG).
"""
from __future__ import annotations

from dataclasses import dataclass

from . import config

WINDOW_RULE = ("primary 2020-2025 (>= 6 distinct years); only if it fails, fallback = the most recent run of >= 10 "
               "consecutive calendar years within 2008-2025 with a complete-case sample (its most recent 10 years)")
H5_GATE_RULE = ("H5 gate (member-cycle based, not the 6-year sector-year gate): >= 3 cycles, >= 30 member-cycles "
                "(distinct bioguide x cycle), non-zero variance of the focal regressor (within champion for H5-within), "
                "focal identified, residual df >= 3, >= 2 champion clusters")
LV_NOTE = "2 sectors: wild cluster bootstrap cannot reach p < 0.056; inference not available"

GROWTH = {"1": "growth_previous_year_pct", "2": "growth_same_year_pct", "3": "predicted_growth_pct"}
GROWTH_VARS = tuple(GROWTH.values())
C_CONTROLS = ("pres_year", "midterm_year", "exp_dem_house", "exp_dem_senate")
L_CONTROLS = C_CONTROLS + ("cur_dem_house", "cur_dem_senate")
DVS = (
    ("contributions", "contributions_real_m"),
    ("lobby_income", "lobby_income_real_m"),
    ("lobby_expenses", "lobby_expenses_real_m"),
)


@dataclass(frozen=True)
class TestSpec:
    id: str
    family: str
    label: str
    dv: str
    focal: tuple = ()
    controls: tuple = ()
    fe: tuple = ("sector",)  # "sector", "year", "sector_x_tier"; () for first differences
    variant: str = "level"  # level | log | year_fe | loso | loyo | fd | tier | derived | not_built
    table: str = "sector_year"
    base: str | None = None
    year_filter: str | None = None  # None | "election_years"
    tiers: tuple | None = None
    interactions: tuple = ()  # ((var, tier), ...) for the tier model
    note: str = ""
    window_rule: str = WINDOW_RULE
    inference: str = "wcr"  # "wcr" (wild cluster restricted bootstrap) | "none" (DESCRIPTIVE: estimate + HC1 only)
    dv_transform: str = "level"  # H5: level | log1p | any (extensive margin, linear probability model)
    drop_cycles: tuple = ()  # H5 robustness: cycles excluded
    keep_lost_primary: bool = False  # H5: lost-renomination rows enter only the primary models
    flag: str = ""  # printed with every coefficient of the test (e.g. outcome-contaminated)
    unit: str = "sector x year"  # unit of analysis
    gate: str = "r8"  # r8 (primary window, then the fallback search) | preview (fixed PREVIEW window, no fallback) | h5
    saturation_check: bool = False  # PREVIEW full core spec: NOT IDENTIFIED when year-level parameters >= distinct years

    @property
    def raw_regressors(self) -> tuple:
        """Panel variables the design needs (before interactions / transformations)."""
        if self.variant == "tier":
            return tuple(dict.fromkeys([v for v, _ in self.interactions] + list(self.controls)))
        return tuple(dict.fromkeys(list(self.focal) + list(self.controls)))

    @property
    def required_vars(self) -> tuple:
        return (self.dv,) + self.raw_regressors


def _core():
    out = []
    for k in "123":
        out.append(TestSpec(id=f"C{k}", family="C", label="CORE", dv="contributions_real_m",
                            focal=(GROWTH[k],), controls=C_CONTROLS))
    for k in "123":
        for dvkey, dv in DVS[1:]:
            out.append(TestSpec(id=f"L{k}-{dvkey.split('_')[1]}", family="L", label="CORE", dv=dv,
                                focal=(GROWTH[k],), controls=L_CONTROLS))
    return out


def _replace_exp(controls, new):
    out = []
    for c in controls:
        if c == "exp_dem_house":
            out.append(new[0])
        elif c == "exp_dem_senate":
            out.append(new[1])
        else:
            out.append(c)
    return tuple(out)


def _build() -> tuple:
    core = _core()
    reg = list(core)
    for c in core:
        reg.append(TestSpec(id=f"H1-{c.id}", family="H1", label="EXTENSION", dv=c.dv, focal=("pres_year", "midterm_year"),
                            controls=c.focal + tuple(x for x in c.controls if x not in ("pres_year", "midterm_year")),
                            variant="derived", base=c.id,
                            note=f"Timing: pres_year and midterm_year coefficients read from {c.id}."))
    for dvkey, dv in DVS:
        reg.append(TestSpec(id=f"H1-phase-{dvkey}", family="H1", label="EXTENSION", dv=dv,
                            focal=("pres_year", "midterm_year"), controls=(),
                            note="DV ~ sector FE + pres_year + midterm_year: the largest complete-case sample of the DV."))
    for c in core:
        reg.append(TestSpec(id=f"H4-{c.id}", family="H4", label="EXTENSION", dv=c.dv,
                            focal=("exp_dem_house", "exp_dem_senate"),
                            controls=c.focal + tuple(x for x in c.controls if not x.startswith("exp_dem")),
                            variant="derived", base=c.id,
                            note=f"Partisan: exp_dem coefficients read from {c.id}."))
    for c in core:
        ctl = _replace_exp(c.controls, ("exp_shift_house", "exp_shift_senate"))
        note = "exp_shift = exp_dem - cur_dem replaces exp_dem."
        if "cur_dem_house" in ctl:
            note += (" cur_dem is retained in this lobbying model, so the shift terms reparametrise the core model: "
                     "their coefficients equal the core model's exp_dem coefficients.")
        reg.append(TestSpec(id=f"H4shift-{c.id}", family="H4", label="EXPLORATORY", dv=c.dv,
                            focal=("exp_shift_house", "exp_shift_senate"),
                            controls=c.focal + tuple(x for x in ctl if not x.startswith("exp_shift")), note=note))
    for c in core:
        ctl = tuple(x for x in c.controls if not x.startswith("exp_dem") and x != "midterm_year")
        reg.append(TestSpec(id=f"H4seat-{c.id}", family="H4", label="EXPLORATORY", dv=c.dv,
                            focal=("pred_dem_seat_change_house", "pred_dem_seat_change_senate"),
                            controls=c.focal + ctl, year_filter="election_years",
                            note=("Final pre-election seat calls replace exp_dem; election years only, so midterm_year "
                                  "(= 1 - pres_year on those years) is omitted.")))
    for dvkey, dv in DVS:
        ctl = C_CONTROLS if dv == "contributions_real_m" else L_CONTROLS
        reg.append(TestSpec(id=f"E1-{dvkey}", family="E1", label="EXTENSION", dv=dv,
                            focal=("growth_previous_year_pct", "predicted_growth_pct"), controls=ctl,
                            note="Prior actual and predicted growth together (plan section 5, extension 1)."))
    for k in "123":
        x = GROWTH[k]
        reg.append(TestSpec(
            id=f"T{k}", family="T", label="EXTENSION", dv="contributions_real_m", table="sector_year_tier",
            focal=(x, f"{x}:Chief", f"{x}:Middle Management"), controls=C_CONTROLS, fe=("sector_x_tier",),
            variant="tier", tiers=config.TIER_MODEL_TIERS, interactions=((x, "Chief"), (x, "Middle Management")),
            note=("Tier model: sector x tier baselines; the slope on X is the Employee slope (reference tier); "
                  "X:Chief and X:Middle Management are slope differences from Employee.")))
    for k in "123":
        x = GROWTH[k]
        reg.append(TestSpec(id=f"T{k}-corporate", family="T", label="EXTENSION", dv="contributions_real_m",
                            table="sector_year_tier", focal=(x,), controls=C_CONTROLS, tiers=(config.CORPORATE_TIER,),
                            note="Corporate (organisational) giving, fitted separately from the person tiers."))
    for c in core:
        reg.append(TestSpec(id=f"CR-{c.id}", family="core_reduced", label="EXPLORATORY", dv=c.dv, focal=c.focal,
                            controls=tuple(x for x in c.controls if not x.startswith("exp_dem")), base=c.id,
                            note="Core test without the exp_dem controls (expected control is blank for 2023-2025)."))
    for c in core:
        reg.append(TestSpec(id=f"R-yearFE-{c.id}", family="robustness", label="ROBUSTNESS", dv=c.dv, focal=c.focal,
                            controls=(), fe=("sector", "year"), variant="year_fe", base=c.id,
                            note="Year fixed effects replace the national controls."))
        reg.append(TestSpec(id=f"R-log-{c.id}", family="robustness", label="ROBUSTNESS", dv=c.dv, focal=c.focal,
                            controls=c.controls, variant="log", base=c.id,
                            note="ln(DV) on positive DV values only; rows with DV <= 0 are counted, never altered."))
        reg.append(TestSpec(id=f"R-LOSO-{c.id}", family="robustness", label="ROBUSTNESS", dv=c.dv, focal=c.focal,
                            controls=c.controls, variant="loso", base=c.id,
                            note="Leave one sector out: refits on the gated sample without each sector in turn."))
        reg.append(TestSpec(id=f"R-LOYO-{c.id}", family="robustness", label="ROBUSTNESS", dv=c.dv, focal=c.focal,
                            controls=c.controls, variant="loyo", base=c.id,
                            note=("Leave one year out: refits on the gated sample without each year in turn; sub-fits "
                                  "necessarily have one year fewer than the minimum they were gated at (diagnostic).")))
        reg.append(TestSpec(id=f"R-FD-{c.id}", family="robustness", label="ROBUSTNESS", dv=c.dv, focal=c.focal,
                            controls=c.controls, fe=(), variant="fd", base=c.id,
                            note=("First differences within sector (consecutive calendar years; the year before the "
                                  "window may supply the lag level); no intercept, so sector baselines drop out.")))
    for ch in ("House", "Senate"):
        reg.append(TestSpec(id=f"DS-{ch}", family="DS", label="EXTENSION", dv=f"dem_share_{ch.lower()}",
                            table="dem_share", variant="not_built",
                            note="Democratic share of chamber-mapped contributions (plan section 5)."))
    reg.extend(_lobbyview())
    reg.extend(_champions())
    reg.extend(_preview())
    ids = [t.id for t in reg]
    if len(ids) != len(set(ids)):
        raise RuntimeError("registry: duplicate test ids")
    return tuple(reg)


def _lobbyview() -> list:
    """Paul's option (a): the L tests on the LobbyView measure. Kept apart from the LDA L tests (never summed with LDA);
    no derived read-outs or robustness variants are generated from them."""
    out = []
    for k in "123":
        out.append(TestSpec(
            id=f"L{k}-LV", family="L-LV", label="DESCRIPTIVE", dv="lobby_amount_undiff_real_m", focal=(GROWTH[k],),
            controls=L_CONTROLS, inference="none",
            note=("LobbyView undifferentiated amount, high-confidence classification (commercial_banks and credit_unions "
                  "only); L-test controls and sector baselines; gated through the fallback window. DESCRIPTIVE: "
                  "coefficients and HC1 errors (reference only); " + LV_NOTE + ". Never added to LDA amounts.")))
    return out


def _champions() -> list:
    """H5: champions' race toughness and industry money (05 data sheet; unit board x champion x cycle)."""
    ctl = ("chamber", "party", "seniority_years")
    tough = ("toughness_general",)
    pooled = dict(family="H5", dv="industry_money_primary", focal=tough, controls=ctl, fe=("board", "cycle"),
                  variant="h5", table="champions", window_rule=H5_GATE_RULE, inference="wcr",
                  unit="board x champion x cycle")
    within = dict(pooled, fe=("champion", "board", "cycle"))
    base_note = ("toughness_general = mean competitiveness of Cook, Inside Elections and Sabato (0 safe ... 3 toss-up); "
                 "sample up_for_election = 1 (retiring rows excluded by that flag), lost-renomination rows excluded; "
                 "controls chamber, party, seniority_years; cycle and board fixed effects; CR1 and wild cluster bootstrap "
                 "by champion (bioguide).")
    within_note = (" Champion fixed effects: identified from cycles in which the same member's toughness varies; "
                   "controls without within-champion variation are dropped and named.")
    out = [
        TestSpec(id="H5-pooled", label="EXTENSION", note=base_note, **pooled),
        TestSpec(id="H5-within", label="EXTENSION", note=base_note + within_note, **within),
    ]
    for tag, kw, txt in (
            ("log1p", dict(dv_transform="log1p"), "log1p(DV); rows with DV < 0 are counted and excluded, never altered."),
            ("any", dict(dv_transform="any"), "Extensive margin: 1 if the DV > 0, linear probability model."),
            ("no2026", dict(drop_cycles=(2026,)),
             "Excludes 2026 (partial cycle: current, not final, ratings; money to mid-2026).")):
        out.append(TestSpec(id=f"H5-pooled-{tag}", label="ROBUSTNESS", base="H5-pooled", note=txt, **{**pooled, **kw}))
        out.append(TestSpec(id=f"H5-within-{tag}", label="ROBUSTNESS", base="H5-within", note=txt,
                            **{**within, **kw}))
    trade = ("Sensitivity DV industry_money_with_trade_real_2025_usd (NOT BUILT when 05 has no such column); "
             "otherwise as the base test.")
    out.append(TestSpec(id="H5-pooled-trade", label="ROBUSTNESS", base="H5-pooled", note=trade,
                        **{**pooled, "dv": "industry_money_with_trade"}))
    out.append(TestSpec(id="H5-within-trade", label="ROBUSTNESS", base="H5-within", note=trade,
                        **{**within, "dv": "industry_money_with_trade"}))
    sec = ("Secondary regressor in its own model (pooled specification). Sample: up_for_election = 1 "
           "including lost-renomination rows (primary models only).")
    out.append(TestSpec(id="H5-primary_contested", label="EXPLORATORY", note=sec, keep_lost_primary=True,
                        **{**pooled, "focal": ("primary_contested",)}))
    out.append(TestSpec(id="H5-primary_margin", label="EXPLORATORY", note=sec, keep_lost_primary=True,
                        **{**pooled, "focal": ("primary_margin",)}))
    out.append(TestSpec(id="H5-general_margin", label="EXPLORATORY",
                        note=("Secondary regressor in its own model (pooled specification); lost-renomination rows "
                              "excluded (no general election). Flag: " + config.H5_GENERAL_MARGIN_FLAG + "."),
                        flag=config.H5_GENERAL_MARGIN_FLAG, **{**pooled, "focal": ("general_margin",)}))
    return out


def _preview() -> list:
    """PREVIEW tests (Paul, 2026-09-25): contributions on the fixed window 2021-2025 (5 full years, below the 6-year
    minimum), every sector with contributions and the focal growth measure; H1-PV over every Mentat industry of 04.
    Each C test has a reduced and a year-FE specification plus the full core specification, which is reported NOT
    IDENTIFIED (not forced) when its national terms saturate the distinct years."""
    common = dict(label="PREVIEW", dv="contributions_real_m", gate="preview", flag=config.PREVIEW_FLAG,
                  window_rule=PREVIEW_RULE)
    out = []
    for k in "123":
        x = GROWTH[k]
        out.append(TestSpec(id=f"C{k}-PV-reduced", family="C-PV", focal=(x,), controls=("pres_year", "midterm_year"),
                            base=f"C{k}", note=("PREVIEW (i) reduced: sector FE + pres_year + midterm_year + " + x + "."),
                            **common))
        out.append(TestSpec(id=f"C{k}-PV-yearFE", family="C-PV", focal=(x,), controls=(), fe=("sector", "year"),
                            variant="year_fe", base=f"C{k}",
                            note=("PREVIEW (ii) year FE: sector FE + year FE + " + x + "."), **common))
        out.append(TestSpec(id=f"C{k}-PV-core", family="C-PV", focal=(x,), controls=C_CONTROLS, base=f"C{k}",
                            saturation_check=True,
                            note=("PREVIEW full core specification (sector FE + pres_year + midterm_year + exp_dem_house + "
                                  "exp_dem_senate + " + x + "), exp_dem 2023-2026 filled from 02 "
                                  "expected_control_2023_2026; NOT IDENTIFIED when the national terms saturate the "
                                  "distinct years (not forced)."), **common))
    out.append(TestSpec(id="H1-PV", family="H1-PV", focal=("pres_year", "midterm_year"), controls=(),
                        table="industry_year", unit="Mentat industry x year",
                        note=("PREVIEW: contributions ~ sector FE + pres_year + midterm_year over every Mentat industry of 04 "
                              "(the seven study sectors with a Mentat workbook plus community_banks, which is not a study "
                              "sector), 2021-2025."), **common))
    return out


PREVIEW_RULE = (f"PREVIEW gate: fixed window {config.PREVIEW_WINDOW[0]}-{config.PREVIEW_WINDOW[1]} "
                f"(5 full years, below Paul's 6-year minimum), >= {config.PREVIEW_MIN_YEARS} distinct years, "
                f">= {config.MIN_SECTORS} sectors, full-rank design, residual df >= {config.MIN_RESID_DF}; no fallback; "
                "full core specification NOT IDENTIFIED when year-level parameters >= distinct years")

REGISTRY = _build()
BY_ID = {t.id: t for t in REGISTRY}


def select(only=None) -> tuple:
    """Tests to run. `only` entries match an id exactly or as a prefix followed by '-' (e.g. 'L1', 'H1', 'R-log')."""
    if not only:
        return REGISTRY
    chosen = []
    for t in REGISTRY:
        for o in only:
            if t.id == o or t.id.startswith(o + "-"):
                chosen.append(t)
                break
    unknown = [o for o in only if not any(t.id == o or t.id.startswith(o + "-") for t in REGISTRY)]
    if unknown:
        raise KeyError(f"unknown test ids: {unknown}")
    return tuple(chosen)
