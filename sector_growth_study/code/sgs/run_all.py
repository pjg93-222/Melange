"""Run the whole study: load -> panel -> registry -> gates -> estimate -> report, with Glass Box start/finish events.

Usage (from the code folder):
  python -m sgs.run_all [--window 2020-2025] [--fallback 2008-2025|none] [--seed N] [--only C1 L1 H1 ...]
                        [--B 9999] [--data-dir DIR] [--results-dir DIR] [--no-glassbox] [--include-partial]
--fallback is the span searched for the fallback window (the most recent run of >= 10 consecutive complete-case years,
its most recent 10 years), tried only when the primary window fails; `none` disables the fallback.
05 (champions, H5) is read at run time only; see champions.py for when H5 is NOT BUILT.
PREVIEW tests (C1-PV..C3-PV, H1-PV) always use the fixed window config.PREVIEW_WINDOW (2021-2025): --window and
--fallback do not apply to them.
"""
from __future__ import annotations

import argparse
import collections
import datetime as _dt
import sys
import time
from pathlib import Path

from . import champions, config, estimate, gates, glassbox, load, panel, registry, report
from .sample import years_text

BUILD_NOTES = [
    "Labels not fixed by the brief are this build's assignment: H1/H4 read-outs, H1-phase-only, E1, T, DS, H5-pooled and "
    "H5-within = EXTENSION; C1-C3 and L1-L3 (nine DV runs) = CORE; H4-shift, H4-seatcalls, core_reduced and the H5 "
    "secondary regressors = EXPLORATORY; R-* and the H5 variants = ROBUSTNESS; L1-LV..L3-LV = DESCRIPTIVE (Paul's option (a)).",
    "Fallback window (ruling of 2026-09-25): only when the primary 2020-2025 window fails, the most recent run of >= 10 "
    "consecutive calendar years within 2008-2025 in which the test's complete-case sample exists; the window used is that "
    "run's most recent 10 years (config.FALLBACK_WHOLE_RUN = False, matching the ruling's LobbyView example 2013-2022). "
    "The fixed 2016-2025 fallback is retired. Each test records its search (fallback_search).",
    "L1-LV..L3-LV use lobby_amount_undiff_real_m (LobbyView, high confidence: commercial_banks and credit_unions, "
    "2006-2023): L-test controls, sector baselines, DESCRIPTIVE (estimate and HC1 error only; 2 sectors, so the wild "
    "cluster bootstrap cannot reach p < 0.056). They are never added to LDA amounts; the LDA L tests are unchanged.",
    "L tests carry 6 national regressors, i.e. 7 year-level parameters with the sector baselines; 6 distinct years cannot "
    "identify them, so L tests can only pass in a fallback window.",
    "H4-seatcalls uses election years only, so its sample never holds consecutive calendar years: it cannot pass the "
    "fallback, and holds at most 3 distinct years in 2020-2025.",
    "H4-shift in lobbying models keeps cur_dem, so exp_shift reparametrises exp_dem and returns the same coefficients.",
    "Leave-one-year-out sub-fits have one year fewer than the window minimum by construction; they are flagged diagnostic. "
    "Leave-one-out tests are gated on their parent sample.",
    "First differences pair year t with t-1 inside each sector; the lag level may come from the year before the window.",
    "Telecom sector growth is withheld (components kept separate per the plan); wireless and cable component growth are "
    "carried as separate sector_year columns and enter no test.",
    "04 names its study-sector column `study_sector` (renamed from `sector`, 2026-09-25); the loader now requires "
    "`study_sector` in every sheet that carries study sectors.",
    "Expected control 2023-2026 (Paul's ruling of 2026-09-25): exp_dem_* = the IEM annual mean (02 data) where present, "
    "else 02 expected_control_2023_2026: 2023-2024 = 1 if the Crystal Ball final call for the 2024 election (4 Nov 2024) "
    "projects >= 218 Democratic House / >= 51 Democratic Senate seats, else 0 (method forecaster_final_call_binary; 2023 "
    "flagged 'measured Nov 2024, after the year'); 2025-2026 = 1 - p_rep_control, the normalized mean of Kalshi and "
    "Polymarket read 24-25 Sep 2026 (method market_snapshot; 2025 flagged 'measured Sep 2026, after the year'). A future "
    "02 sheet expected_control_markets (daily history) takes precedence for 2023-2026 when present. Method and flag are "
    "carried into the panel (exp_dem_*_method, exp_dem_*_flag) and listed per test (input_flags).",
    "PREVIEW (Paul: 'yes, run the preview too'): C1-PV..C3-PV on contributions_real_m and H1-PV, fixed window 2021-2025 "
    "(5 full years, BELOW the 6-year minimum; no fallback). Specifications: (i) reduced = sector FE + pres_year + "
    "midterm_year + focal growth; (ii) year FE = sector FE + year FE + focal growth; the full core specification (with "
    "exp_dem) is NOT IDENTIFIED when its year-level parameters are as many as the distinct years (not forced). H1-PV: "
    "every Mentat industry of 04 (seven study sectors plus community_banks). Every PREVIEW output carries 'PREVIEW - "
    "below the 6-year minimum'.",
    "H5 (05 data sheet, unit board x champion x cycle) has its own gate: >= 3 cycles, >= 30 member-cycles, non-zero focal "
    "variance (member-cycle based, not the 6-year sector-year gate). Sample up_for_election = 1; lost-renomination rows "
    "only in the primary models; 'no_authorized_committee' zeros (0 by construction) and 2020 (no money collected) do not "
    "enter. Clusters: champions (bioguide); CR1 plus wild cluster restricted bootstrap. 05 is read at run time only and is "
    "NOT BUILT when missing, when its receipt or file is younger than 10 minutes, when its bytes differ from its receipt, "
    "or when expected columns are missing.",
]


def parse_window(text):
    if text is None or str(text).lower() in ("none", "off", ""):
        return None
    a, b = str(text).split("-")
    return int(a), int(b)


def _attempt_fields(att):
    if att is None:
        return dict(n=None, n_window="", n_sectors=None, sectors="", n_years=None, years="", resid_df=None)
    return dict(n=att.n, n_window=f"{att.window[0]}-{att.window[1]}", n_sectors=len(att.sectors),
                sectors=", ".join(att.sectors), n_years=len(att.years), years=years_text(att.years),
                resid_df=att.resid_df)


def _excl_text(att):
    if att is None or att.sample is None:
        return ""
    parts = [f"{k}: {v}" for k, v in att.sample.exclusions.items()]
    parts += att.sample.notes
    return "; ".join(parts)


FLAG_COLUMNS = {
    "exp_dem_house": ("exp_dem_house_method", "exp_dem_house_flag"),
    "exp_dem_senate": ("exp_dem_senate_method", "exp_dem_senate_flag"),
    "exp_shift_house": ("exp_dem_house_method", "exp_dem_house_flag"),
    "exp_shift_senate": ("exp_dem_senate_method", "exp_dem_senate_flag"),
}


def input_flags(spec, att) -> str:
    """Expected-control inputs of the estimated (or last attempted) sample that do not come from the IEM annual mean:
    variable, year, method and timing flag (e.g. 2023 forecaster_final_call_binary, measured Nov 2024, after the year)."""
    if att is None or att.sample is None or not len(att.sample.df):
        return ""
    df = att.sample.df
    parts = []
    for v in spec.required_vars:
        if v not in FLAG_COLUMNS:
            continue
        mcol, fcol = FLAG_COLUMNS[v]
        if mcol not in df.columns:
            continue
        seen = []
        for y, m, f in sorted({(int(r[0]), r[1], r[2]) for r in df[["year", mcol, fcol]].astype(object).where(
                df[["year", mcol, fcol]].notna(), None).itertuples(index=False, name=None)}, key=lambda t: t[0]):
            if m in (None, "iem_annual_mean"):
                continue
            seen.append(f"{y} {m}" + (f" ({f})" if f else ""))
        if seen:
            parts.append(f"{v}: " + "; ".join(seen))
    return " | ".join(parts)


def run(window=config.DEFAULT_WINDOW, fallback=config.FALLBACK_SEARCH, seed=config.SEED, only=None, B=config.BOOT_B,
        data_dir=None, results_dir=None, include_partial=False, run_id=None, log=print, now=None) -> dict:
    run_id = run_id or "analysis-" + _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    results_dir = Path(results_dir or config.RESULTS_DIR)
    results_dir.mkdir(parents=True, exist_ok=True)
    wbs = load.load_all(data_dir)
    sy = panel.build_sector_year(wbs)
    syt = panel.build_sector_year_tier(wbs, sy)
    iy = panel.build_industry_year(wbs)
    tables = {"sector_year": sy, "sector_year_tier": syt, "industry_year": iy}

    chosen = {t.id for t in registry.select(only)}
    for t in list(registry.REGISTRY):
        if t.id in chosen and t.variant == "derived":
            chosen.add(t.base)
    order = [t for t in registry.REGISTRY if t.id in chosen]
    extra = collections.defaultdict(dict)  # ordered set of coefficients derived read-outs need from their base
    for t in order:
        if t.variant == "derived":
            for c in t.focal:
                extra[t.base][c] = True
    champ = None
    if any(t.table == "champions" for t in order):
        champ = champions.load_champions(data_dir, now=now)  # read at run time only
        log(f"  05 champions: {'loaded' if champ.ok else 'NOT BUILT: ' + champ.reason}")

    decisions, results = {}, {}
    for t in order:
        if t.variant == "derived":
            continue
        if t.table == "champions":
            d = champions.decide_h5(t, champ)
            decisions[t.id] = d
            if d.status == gates.ESTIMABLE:
                results[t.id] = champions.estimate_h5(t, d, B=B, seed=seed)
            log(f"  {t.id}: {d.status}" + (f" (cycles {champions.cycles_text(d.sample.cycles)})"
                                           if d.status == gates.ESTIMABLE else ""))
            continue
        d = gates.decide(t, tables, window, fallback, include_partial=include_partial)
        decisions[t.id] = d
        if d.status == gates.ESTIMABLE:
            results[t.id] = estimate.estimate(t, d.chosen, B=B, seed=seed, extra_coefs=list(extra.get(t.id, {})))
        log(f"  {t.id}: {d.status}" + (f" ({d.window[0]}-{d.window[1]})" if d.window else ""))

    est_rows, coef_rows, strata_rows, sample_rows, attempts_by_test = [], [], [], [], {}
    for t in order:
        if t.table == "champions":
            d = decisions[t.id]
            attempts_by_test[t.id] = []
            est_rows.append(champions.est_row(t, d))
            if d.status == gates.ESTIMABLE:
                r = results[t.id]
                coef_rows.extend(champions.coef_rows(t, d, r))
                strata_rows.extend({**s, "test_id": t.id} for s in r.strata)
                sample_rows.extend(champions.sample_rows(t, d))
            continue
        src = t.base if t.variant == "derived" else t.id
        d = decisions[src]
        att = d.chosen or (d.attempts[-1] if d.attempts else None)
        attempts_by_test[t.id] = d.attempts
        reason = d.reason if d.status != gates.ESTIMABLE else ""
        iflags = input_flags(t, att)
        short = ""
        if d.status == gates.NOT_ESTIMABLE:
            short = " || ".join(a.compact() for a in d.attempts)
        elif d.status == gates.NOT_BUILT:
            short = d.reason
        if t.variant == "derived" and reason:
            reason = f"from {src}: {reason}"
            short = f"from {src}: {short}"
        est_rows.append(dict(
            test_id=t.id, family=t.family, label=t.label, status=d.status,
            window_used=f"{d.window[0]}-{d.window[1]}" if d.window else "", window_kind=d.window_kind or "",
            **_attempt_fields(att), reason=reason, reason_short=short,
            default_attempt=d.attempts[0].text() if d.attempts else "",
            fallback_attempt=d.attempts[1].text() if len(d.attempts) > 1 else "",
            fallback_search=d.fallback_search, exclusions=_excl_text(att), dv=t.dv, dv_column=t.dv,
            dv_label=config.DV_LABELS.get(t.dv, ""), focal=", ".join(t.focal), controls=", ".join(t.controls),
            fixed_effects=", ".join(t.fe), variant=t.variant, base_test=t.base or "", year_filter=t.year_filter or "",
            tiers=", ".join(t.tiers) if t.tiers else "", note=t.note, unit=t.unit if t.table != "sector_year_tier"
            else "sector x year x tier", n_champions=None, n_member_cycles=None, boards="",
            cluster_by=("Mentat industry" if t.table == "industry_year" else "study sector") if t.table != "dem_share"
            else "", n_clusters=att.sectors.__len__() if att else None,
            gate_rule=t.window_rule, inference=("none (DESCRIPTIVE)" if t.inference == "none"
                                                else "wild cluster restricted bootstrap by sector"), flag=t.flag,
            input_flags=iflags))
        if d.status != gates.ESTIMABLE:
            continue
        r = results[src]
        wtxt = f"{d.window[0]}-{d.window[1]}"
        common = dict(label=t.label, window_used=wtxt, unit_of_analysis=est_rows[-1]["unit"], dv_column=t.dv,
                      resid_df=att.resid_df, sectors=", ".join(att.sectors), controls=", ".join(t.controls),
                      fixed_effects=", ".join(t.fe),
                      **{k: v for k, v in _attempt_fields(att).items() if k in ("n", "n_sectors", "n_years", "years")})
        cflag = "; ".join(x for x in (t.flag, ("input flags: " + iflags) if iflags else "") if x)
        coefs = r.coefs
        if t.variant == "derived":
            coefs = sorted([c for c in r.coefs if c["coefficient"] in t.focal], key=lambda c: t.focal.index(c["coefficient"]))
        for c in coefs:
            if t.variant != "derived" and not c.get("focal"):
                continue
            coef_rows.append({**common, **c, "test_id": t.id, "source_test": src if src != t.id else "",
                              "flag": cflag,
                              "ci_text": ("n/a (inference not available)" if t.inference == "none"
                                          else report.ci_text(c.get("ci_low"), c.get("ci_high")))})
        for c in r.subfits:
            coef_rows.append({**common, **c, "test_id": t.id, "source_test": "", "n": c.get("n"),
                              "n_sectors": c.get("n_sectors"), "n_years": c.get("n_years"), "years": c.get("years"),
                              "subfit_status": c.get("status"), "subfit_reason": c.get("reason"),
                              "subfit_flag": c.get("flag"), "ci_text": report.ci_text(c.get("ci_low"), c.get("ci_high"))})
        if t.variant != "derived":
            for s in r.strata:
                strata_rows.append({**s, "test_id": t.id})
            for rec in att.sample.df.to_dict("records"):
                sample_rows.append(dict(test_id=t.id, window_used=wtxt, study_sector=rec["study_sector"],
                                        year=rec["year"], tier=rec.get("tier"), y=rec["y"]))

    sources = [dict(file=w.path.name, workbook=w.name, absolute_path=str(w.path), sha256=w.sha256,
                    size_bytes=w.size_bytes, mtime_utc=w.mtime_utc, read_at_utc=w.read_at_utc,
                    sheets_read=", ".join(w.frames), rows_read=", ".join(f"{k}={len(v)}" for k, v in w.frames.items()),
                    note="")
               for w in wbs.values()]
    if champ is not None and champ.source:
        sources.append(champ.source)
    tables_out = dict(tables)
    if champ is not None:
        tables_out["champions"] = champions.panel_table(champ)
    windows = (window, fallback or (None, None))
    xlsx = results_dir / f"results_{run_id}.xlsx"
    md = results_dir / f"report_{run_id}.md"
    emd = results_dir / f"estimability_{run_id}.md"
    report.write_workbook(xlsx, est_rows, coef_rows, strata_rows, sample_rows, tables_out, sources)
    specs = {t.id: t for t in order}
    report.write_report_md(md, run_id, est_rows, coef_rows, strata_rows, specs, sources, windows,
                           {"B": B, "seed": seed}, BUILD_NOTES)
    report.write_estimability_md(emd, run_id, est_rows, attempts_by_test, windows)
    counts = collections.Counter(r["status"] for r in est_rows)
    return dict(run_id=run_id, counts=dict(counts), xlsx=str(xlsx), report=str(md), estimability=str(emd),
                est_rows=est_rows, coef_rows=coef_rows, strata_rows=strata_rows, tables=tables_out,
                decisions=decisions, results=results, attempts_by_test=attempts_by_test, champions=champ,
                sources=sources)


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m sgs.run_all", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--window", default=f"{config.DEFAULT_WINDOW[0]}-{config.DEFAULT_WINDOW[1]}")
    p.add_argument("--fallback", default=f"{config.FALLBACK_SEARCH[0]}-{config.FALLBACK_SEARCH[1]}",
                   help="span searched for the fallback window, or none")
    p.add_argument("--seed", type=int, default=config.SEED)
    p.add_argument("--only", nargs="+", default=None, help="test ids or id prefixes (comma or space separated)")
    p.add_argument("--B", type=int, default=config.BOOT_B)
    p.add_argument("--data-dir", default=None)
    p.add_argument("--results-dir", default=None)
    p.add_argument("--no-glassbox", action="store_true")
    p.add_argument("--include-partial", action="store_true")
    a = p.parse_args(argv)
    only = [x for o in (a.only or []) for x in o.split(",") if x] or None
    run_id = "analysis-" + _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    gb = not a.no_glassbox
    start_id = None
    if gb:
        start_id = glassbox.emit("run.start", "running", "start",
                                 f"sector growth analysis: start (window {a.window}, fallback search {a.fallback}, "
                                 f"seed {a.seed}, B {a.B}, only {only or 'all'})", run_id)
    t0 = time.time()
    try:
        out = run(parse_window(a.window), parse_window(a.fallback), a.seed, only, a.B, a.data_dir, a.results_dir,
                  a.include_partial, run_id=run_id)
    except Exception as exc:
        if gb:
            glassbox.emit("run.finish", "failed", "finish", f"sector growth analysis: FAILED ({type(exc).__name__})",
                          run_id, correlation_id=start_id or "", parent_id=start_id or "", detail=str(exc)[:2000],
                          duration_ms=int((time.time() - t0) * 1000))
        raise
    c = out["counts"]
    ch = out.get("champions")
    summary = (f"sector growth analysis: {len(out['est_rows'])} tests; ESTIMABLE {c.get('ESTIMABLE', 0)}, "
               f"NOT ESTIMABLE {c.get('NOT ESTIMABLE', 0)}, NOT BUILT {c.get('NOT BUILT', 0)}"
               + ("" if ch is None else f"; 05 {'read' if ch.ok else 'NOT BUILT'}"))
    if gb:
        glassbox.emit("run.finish", "succeeded", "finish", summary, run_id, correlation_id=start_id or "",
                      parent_id=start_id or "", detail=f"{out['xlsx']}; {out['report']}; {out['estimability']}"
                      + ("" if ch is None or ch.ok else f"; 05 NOT BUILT: {ch.reason}"),
                      duration_ms=int((time.time() - t0) * 1000))
    print(summary)
    print(out["xlsx"])
    print(out["report"])
    print(out["estimability"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
