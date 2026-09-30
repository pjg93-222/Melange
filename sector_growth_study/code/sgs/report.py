"""Write the run outputs: results_<run>.xlsx (study format), report_<run>.md, estimability_<run>.md.

Workbook format: header in row 1, one table per sheet, values only (no formulas, styles, merged cells); missing is an
empty cell, never 0; unbounded interval ends are blank numbers with the interval spelled out in `ci_text`.
Every figure in the markdown names its window (or cycles) and its denominator (house rule).
"""
from __future__ import annotations

import collections
import math
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

from . import config
from .panel import PANEL_DICTIONARY
from .sample import years_text

H5_UNIT = "board x champion x cycle"


def label_text(label: str) -> str:
    """The label as printed: PREVIEW outputs always read 'PREVIEW - below the 6-year minimum'."""
    return config.PREVIEW_FLAG if label == "PREVIEW" else label


def _clean(v):
    if v is None:
        return None
    if isinstance(v, (float, np.floating)):
        return None if (math.isnan(v) or math.isinf(v)) else float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, (list, tuple)):
        return "; ".join(str(x) for x in v)
    if v is pd.NA or v is pd.NaT:
        return None
    if isinstance(v, str) and v.startswith("="):
        raise ValueError(f"refusing to write a cell starting with '=': {v[:40]!r}")
    return v


def fmt(x, digits=4):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    if isinstance(x, float) and math.isinf(x):
        return "-inf" if x < 0 else "+inf"
    return f"{x:.{digits}g}" if abs(x) < 1e-3 and x != 0 else f"{x:,.{digits}f}"


def ci_text(lo, hi):
    return f"[{fmt(lo)}, {fmt(hi)}]"


def write_sheet(wb, title, frame: pd.DataFrame):
    ws = wb.create_sheet(title)
    ws.append([str(c) for c in frame.columns])
    for row in frame.itertuples(index=False, name=None):
        ws.append([_clean(v) for v in row])


RESULT_DICTIONARY = [
    ("estimability", "test_id", "text", None, "Registry id (registry.py)."),
    ("estimability", "family", "text", None, "C, L, L-LV, H1, H4, H5, E1, T, core_reduced, robustness, DS."),
    ("estimability", "label", "text", None, "CORE / EXTENSION / ROBUSTNESS / EXPLORATORY / DESCRIPTIVE (no inference) / PREVIEW (fixed window 2021-2025, below the 6-year minimum; printed 'PREVIEW - below the 6-year minimum')."),
    ("estimability", "status", "text", None, "ESTIMABLE (window used) / NOT ESTIMABLE (reason) / NOT BUILT."),
    ("estimability", "window_used", "text", "years", "Window of the estimated sample (sector-year tests) or its cycles (H5); blank unless ESTIMABLE."),
    ("estimability", "window_kind", "text", None, "default (2020-2025, >= 6 years); fallback (most recent 10 consecutive complete-case years of the most recent run of >= 10 within 2008-2025, only when the default fails); preview (fixed 2021-2025, >= 5 years, PREVIEW tests only); member-cycle gate (H5)."),
    ("estimability", "fallback_search", "text", None, "The fallback search: complete-case years in 2008-2025, the runs of consecutive years, the run and the window used."),
    ("estimability", "n", "integer", "rows", "Complete-case rows of the estimated sample, or of the last attempted window (H5: board x champion x cycle rows)."),
    ("estimability", "n_window", "text", "years", "Window in which n, n_sectors, n_years and years were counted (H5: cycles)."),
    ("estimability", "n_sectors", "integer", "sectors", "Distinct sectors in that sample (blank for H5)."),
    ("estimability", "sectors", "text", None, "Sectors in that sample."),
    ("estimability", "n_years", "integer", "years", "Distinct years in that sample (H5: distinct cycles)."),
    ("estimability", "years", "text", None, "Years in that sample (H5: cycles)."),
    ("estimability", "resid_df", "integer", "df", "n minus design rank."),
    ("estimability", "reason_short", "text", None, "Compact reason per attempted window: years found vs required, terms not identified, residual df, inputs no sector has (with years), sectors never complete; H5: cycles, member-cycles, variance, availability by cycle."),
    ("estimability", "reason", "text", None, "Why NOT ESTIMABLE / NOT BUILT: each attempted window with its failed checks and blocking inputs."),
    ("estimability", "default_attempt", "text", None, "Outcome of the default-window attempt."),
    ("estimability", "fallback_attempt", "text", None, "Outcome of the fallback attempt (blank when not needed)."),
    ("estimability", "exclusions", "text", None, "Rows excluded, by reason (counts)."),
    ("estimability", "dv / dv_column / dv_label", "text", None, "Registry DV (H5: the DV role) / the workbook column used / its label (H5 fallback DV: 'employee channel only')."),
    ("estimability", "focal / controls / fixed_effects / variant / base_test / year_filter / tiers / note", "text", None, "The registry entry."),
    ("estimability", "unit", "text", None, "Unit of analysis: sector x year, sector x year x tier, or board x champion x cycle (H5)."),
    ("estimability", "n_champions / n_member_cycles / boards", "mixed", None, "H5: champions (bioguide), distinct champion x cycle pairs, boards in the sample."),
    ("estimability", "cluster_by / n_clusters", "mixed", None, "Inference clusters (study sector; H5: champion) and their number in the sample."),
    ("estimability", "gate_rule", "text", None, "The estimability rule applied to the test."),
    ("estimability", "inference", "text", None, "Wild cluster restricted bootstrap (by sector or champion), or none (DESCRIPTIVE)."),
    ("estimability", "flag", "text", None, "Flags printed with every coefficient (e.g. employee channel only; outcome-contaminated; PREVIEW - below the 6-year minimum)."),
    ("estimability", "input_flags", "text", None, "Expected-control inputs of the sample that are not IEM annual means: variable, year, method (forecaster_final_call_binary, market_snapshot, market_daily_mean) and timing flag (e.g. measured Nov 2024, after the year)."),
    ("coefficients", "test_id", "text", None, "Test the row belongs to (derived H1/H4 rows name their source test in source_test)."),
    ("coefficients", "coefficient", "text", None, "Regressor name; X:Chief / X:Middle Management are slope differences from Employee."),
    ("coefficients", "focal", "boolean", None, "True for the test's focal coefficient(s)."),
    ("coefficients", "estimate", "decimal", "see unit", "OLS point estimate."),
    ("coefficients", "unit", "text", None, "Unit of the estimate (DV in $M 2025 for sector-year tests, USD 2025 for H5, unless transformed)."),
    ("coefficients", "hc1_se", "decimal", "see unit", "HC1 heteroskedasticity-robust standard error (reference only)."),
    ("coefficients", "cr1_se", "decimal", "see unit", "CR1 cluster-robust standard error (by sector; H5 by champion) used in the bootstrap t; blank for DESCRIPTIVE tests."),
    ("coefficients", "t_cr1", "decimal", None, "t statistic estimate / cr1_se."),
    ("coefficients", "boot_p", "decimal", "probability", "Wild cluster restricted bootstrap p-value for coefficient = 0 (two-sided, symmetric); blank for DESCRIPTIVE tests."),
    ("coefficients", "ci_low / ci_high", "decimal", "see unit", "95% interval by bootstrap test inversion; blank where unbounded or not computed (see ci_text)."),
    ("coefficients", "ci_text", "text", None, "The interval as text, including infinite ends, or 'n/a (inference not available)'."),
    ("coefficients", "boot_draws", "integer", "draws", "Bootstrap draws (6**G when enumerated); 0 when no bootstrap was run."),
    ("coefficients", "boot_enumerated", "boolean", None, "True when all 6**G Webb weight vectors were enumerated."),
    ("coefficients", "boot_note", "text", None, "Bootstrap caveat, or the DESCRIPTIVE note ('2 sectors: wild cluster bootstrap cannot reach p < 0.056; inference not available')."),
    ("coefficients", "inference / flag", "text", None, "Inference used; flags (employee channel only; outcome-contaminated: money affects margins)."),
    ("coefficients", "stratification", "text", None, "STRATIFIED (k of G sectors or boards have a stratum-only estimate; see strata) or UNSTRATIFIED (reason)."),
    ("coefficients", "left_out / subfit_status / subfit_reason / subfit_flag", "text", None, "Leave-one-out sub-fits: the sector or year left out and the sub-fit outcome."),
    ("coefficients", "window_used / n / n_sectors / n_years / years / unit_of_analysis / n_champions / n_member_cycles / cycles / dv_column", "mixed", None, "Window (or cycles) and denominator of the estimate."),
    ("coefficients", "resid_df / sectors / boards / controls / fixed_effects", "mixed", None, "Residual df of the fitted design (n minus rank), the sectors (or H5 boards) in the sample, and the specification's controls and fixed effects."),
    ("strata", "test_id / coefficient / study_sector / board", "text", None, "Stratum-only regression of the same specification: one sector (sector baseline = intercept), or one board (H5, board fixed effects dropped)."),
    ("strata", "status", "text", None, "estimated, or insufficient (residual df < 2, rank deficient, or focal not identified)."),
    ("strata", "estimate / hc1_se / cr1_se", "decimal", "see coefficients.unit", "Stratum OLS estimate, HC1 error, CR1 error by champion (H5)."),
    ("strata", "n / resid_df / years / cycles / n_champions / reason", "mixed", None, "Denominator of the stratum estimate, or why it is insufficient."),
    ("samples", "test_id / window_used / study_sector / year / tier / y / board / bioguide / cycle", "mixed", None, "Rows of every estimated sample (y = the DV as entered: $M 2025, ln, first difference; H5: USD 2025, log1p or 0/1)."),
    ("sector_year", "(columns)", "mixed", None, "Analysis table study_sector x year; columns defined in the rows below."),
    ("sector_year_tier", "(columns)", "mixed", None, "Analysis table study_sector x year x tier; same column definitions."),
    ("industry_year", "(columns)", "mixed", None, "H1-PV table: every Mentat industry of 04 sector_year (seven study sectors plus community_banks, not a study sector; column study_sector holds the 04 unit) x year: contributions and pres_year / midterm_year."),
    ("champions", "(columns)", "mixed", None, "05 data columns H5 reads, every row of 05 as read at run time (empty when 05 is NOT BUILT); definitions in 05's dictionary."),
    ("sources", "file / workbook / absolute_path / sha256 / size_bytes / mtime_utc / read_at_utc / sheets_read / rows_read / note",
     "mixed", None, "Every input workbook read by the run (read-only), with its SHA-256; note = how 05 was read, or why it is NOT BUILT."),
]

EST_COLS = ["test_id", "family", "label", "status", "window_used", "window_kind", "fallback_search", "n", "n_window",
            "n_sectors", "sectors", "n_years", "years", "resid_df", "reason_short", "reason", "default_attempt",
            "fallback_attempt", "exclusions", "dv", "dv_column", "dv_label", "focal", "controls", "fixed_effects", "variant",
            "base_test", "year_filter", "tiers", "note", "unit", "n_champions", "n_member_cycles", "boards",
            "cluster_by", "n_clusters", "gate_rule", "inference", "flag", "input_flags"]


def _estimability_frame(rows):
    return pd.DataFrame(rows, columns=EST_COLS)


COEF_COLS = ["test_id", "label", "source_test", "window_used", "n", "n_sectors", "n_years", "years", "unit_of_analysis",
             "n_champions", "n_member_cycles", "cycles", "dv_column", "resid_df", "sectors", "boards", "controls",
             "fixed_effects", "coefficient", "focal", "estimate", "unit",
             "hc1_se", "cr1_se", "t_cr1", "boot_p", "ci_low", "ci_high", "ci_text", "boot_draws", "boot_enumerated",
             "boot_note", "inference", "flag", "stratification", "left_out", "subfit_status", "subfit_reason",
             "subfit_flag"]
STRATA_COLS = ["test_id", "coefficient", "study_sector", "board", "status", "estimate", "hc1_se", "cr1_se", "n",
               "resid_df", "years", "cycles", "n_champions", "reason"]
SAMPLE_COLS = ["test_id", "window_used", "study_sector", "year", "tier", "y", "board", "bioguide", "cycle"]
SOURCE_COLS = ["file", "workbook", "absolute_path", "sha256", "size_bytes", "mtime_utc", "read_at_utc", "sheets_read",
               "rows_read", "note"]


def write_workbook(path: Path, est_rows, coef_rows, strata_rows, sample_rows, tables, sources):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    write_sheet(wb, "estimability", _estimability_frame(est_rows))
    write_sheet(wb, "coefficients", pd.DataFrame(coef_rows, columns=COEF_COLS))
    write_sheet(wb, "strata", pd.DataFrame(strata_rows, columns=STRATA_COLS))
    write_sheet(wb, "samples", pd.DataFrame(sample_rows, columns=SAMPLE_COLS))
    write_sheet(wb, "sector_year", tables["sector_year"])
    write_sheet(wb, "sector_year_tier", tables["sector_year_tier"])
    if "industry_year" in tables:
        write_sheet(wb, "industry_year", tables["industry_year"])
    if "champions" in tables:
        write_sheet(wb, "champions", tables["champions"])
    dic = [dict(sheet=s, column=c, type=t, unit=u, definition=d) for s, c, t, u, d in RESULT_DICTIONARY]
    for col, (t, u, d) in PANEL_DICTIONARY.items():
        dic.append(dict(sheet="sector_year / sector_year_tier", column=col, type=t, unit=u, definition=d))
    write_sheet(wb, "dictionary", pd.DataFrame(dic, columns=["sheet", "column", "type", "unit", "definition"]))
    write_sheet(wb, "sources", pd.DataFrame(sources, columns=SOURCE_COLS))
    tmp = path.with_suffix(".tmp.xlsx")
    wb.save(tmp)
    tmp.replace(path)


def _md_escape(s: str) -> str:
    return str(s).replace("|", "/").replace("\n", " ")


def blocking_summary(est_rows, attempts_by_test) -> list:
    """Most frequent blocking inputs / checks across NOT ESTIMABLE sector-year tests, per window kind."""
    out = []
    for kind in ("default", "fallback", "preview"):
        cnt = collections.Counter()
        for tid, atts in attempts_by_test.items():
            for a in atts:
                if a.kind != kind or a.ok:
                    continue
                items = set()
                for r in a.reasons:
                    if r.startswith("blocking inputs: "):
                        for part in r[len("blocking inputs: "):].split("; "):
                            items.add(part)
                    elif r.startswith("no run of"):
                        items.add(r.split(" (")[0])
                    elif "distinct years" in r and "<" in r:
                        items.add("fewer distinct years than required")
                    elif r.startswith("year-level design not identified"):
                        items.add("year-level design not identified: " + r.split("; not identified: ")[-1])
                    else:
                        items.add(r.split(";")[0])
                cnt.update(items)
        out.append((kind, cnt.most_common(12)))
    return out


def _denominator(r) -> str:
    if r.get("unit") == H5_UNIT:
        if r.get("n") is None:
            return "n/a"
        return (f"{r['n']} rows ({r.get('n_champions')} champions, {r.get('n_member_cycles')} member-cycles) in cycles "
                f"{r.get('years') or 'none'}")
    if r.get("n") is None:
        return "n/a"
    return f"{r['n']} ({r['n_sectors']} x {r['n_years']}) in {r.get('n_window', '')}"


def write_estimability_md(path: Path, run_id, est_rows, attempts_by_test, windows):
    counts = collections.Counter(r["status"] for r in est_rows)
    fb = windows[1]
    fb_text = (f"only if the default fails, the most recent run of >= {config.MIN_YEARS_FALLBACK} consecutive calendar "
               f"years within {fb[0]}-{fb[1]} in which the test's complete-case sample exists, using "
               + ("the whole run" if config.FALLBACK_WHOLE_RUN else f"its most recent {config.MIN_YEARS_FALLBACK} years")
               if fb and fb[0] is not None else "no fallback")
    L = [f"# Estimability, run {run_id}", "",
         f"Sector-year tests (Paul's R8 and the fallback ruling of 2026-09-25): default {windows[0][0]}-{windows[0][1]} "
         f"needs >= {config.MIN_YEARS_DEFAULT} distinct years; fallback: {fb_text}; >= {config.MIN_SECTORS} sectors (every "
         f"sector with complete data enters); full-rank design with the year-level regressors checked against the distinct "
         f"years; residual df >= {config.MIN_RESID_DF}. 2026 is partial and excluded.", "",
         f"H5 (champions, unit {H5_UNIT}): member-cycle gate, not the 6-year sector-year gate: >= {config.H5_MIN_CYCLES} "
         f"cycles, >= {config.H5_MIN_MEMBER_CYCLES} member-cycles, non-zero variance of the focal regressor (within champion "
         f"for H5-within), focal identified, residual df >= {config.MIN_RESID_DF}.", "",
         f"PREVIEW tests ({config.PREVIEW_FLAG}): fixed window {config.PREVIEW_WINDOW[0]}-{config.PREVIEW_WINDOW[1]} "
         f"(5 full years), >= {config.PREVIEW_MIN_YEARS} distinct years, >= {config.MIN_SECTORS} sectors, full rank, "
         f"residual df >= {config.MIN_RESID_DF}, no fallback; the full core specification is NOT IDENTIFIED when its "
         "year-level parameters are as many as the distinct years (not forced).", "",
         f"Tests: {len(est_rows)}. ESTIMABLE {counts.get('ESTIMABLE', 0)}; NOT ESTIMABLE {counts.get('NOT ESTIMABLE', 0)}; "
         f"NOT BUILT {counts.get('NOT BUILT', 0)}.", "",
         "## Most frequent blockers of the sector-year tests (tests blocked; derived H1/H4 read-outs count with their "
         "source test)", ""]
    for kind, items in blocking_summary(est_rows, attempts_by_test):
        L.append(f"{kind} window:")
        L.append("")
        for text, k in items:
            L.append(f"- {k} tests: {_md_escape(text)}")
        L.append("")
    h5 = [r for r in est_rows if r.get("unit") == H5_UNIT and r["status"] != "ESTIMABLE"]
    if h5:
        L += ["H5 (member-cycle gate):", ""]
        for r in h5:
            L.append(f"- {r['test_id']}: {r['status']}: {_md_escape(r.get('reason_short') or r.get('reason') or '')}")
        L.append("")
    L += ["## Every test", "",
          "n = complete-case rows (sectors x distinct years) of the estimated sample, or of the last window attempted, "
          "counted in the window named after it; H5: board x champion x cycle rows, champions and member-cycles. The full "
          "reason, with every sector-level gap, is in the `reason` column of the results workbook.", "",
          "| test | label | status | window used | n in window | reason |", "|---|---|---|---|---|---|"]
    for r in est_rows:
        wtxt = r["window_used"] or ""
        if r.get("window_kind") == "fallback" and r.get("fallback_search"):
            wtxt += " (fallback)"
        L.append(f"| {r['test_id']} | {label_text(r['label'])} | {r['status']} | {wtxt} | {_denominator(r)} | "
                 f"{_md_escape(r.get('reason_short') or r.get('reason') or '')} |")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def _coef_line(c, r) -> str:
    where = (f"cycles {r['years']}, n = {r['n']} ({r.get('n_champions')} champions, {r.get('n_member_cycles')} "
             f"member-cycles), residual df {r.get('resid_df')}" if r.get("unit") == H5_UNIT else
             f"window {r['window_used']}, n = {r['n']} ({r.get('n_sectors')} sectors x {r.get('n_years')} years: "
             f"{r.get('years')}), residual df {r.get('resid_df')}")
    flag = f" Flag: {c['flag']}." if c.get("flag") else ""
    if (c.get("inference") or "").startswith("none"):
        return (f"- {c['coefficient']}: b = {fmt(c['estimate'])} ({c['unit']}); HC1 se {fmt(c.get('hc1_se'))} (reference "
                f"only); {where}. {c.get('boot_note')}. {c['stratification']}.{flag}")
    return (f"- {c['coefficient']}: b = {fmt(c['estimate'])} ({c['unit']}); bootstrap 95% CI {c['ci_text']}, "
            f"p = {fmt(c.get('boot_p'))} ({c.get('boot_draws')} draws{', enumerated' if c.get('boot_enumerated') else ''}); "
            f"CR1 se {fmt(c.get('cr1_se'))}; HC1 se {fmt(c.get('hc1_se'))}; {where}. {c['stratification']}.{flag}"
            + (f" {c['boot_note']}" if c.get("boot_note") else ""))


def write_report_md(path: Path, run_id, est_rows, coef_rows, strata_rows, specs, sources, windows, params, notes):
    counts = collections.Counter(r["status"] for r in est_rows)
    fb = windows[1]
    L = [f"# Sector growth and political spending: analysis run {run_id}", "",
         "Exploratory observational study (plan of 2026-09-25). Associations only; no causal reading. Numbers only below.", "",
         "## Run", "",
         f"- Sector-year windows: default {windows[0][0]}-{windows[0][1]} (>= {config.MIN_YEARS_DEFAULT} years); fallback "
         + (f"(only if the default fails) the most recent {config.MIN_YEARS_FALLBACK} consecutive years of the most recent "
            f"run of >= {config.MIN_YEARS_FALLBACK} consecutive complete-case years within {fb[0]}-{fb[1]}"
            if fb and fb[0] is not None else "none")
         + f"; >= {config.MIN_SECTORS} sectors; residual df >= {config.MIN_RESID_DF}.",
         f"- H5 gate (member-cycle based): >= {config.H5_MIN_CYCLES} cycles, >= {config.H5_MIN_MEMBER_CYCLES} member-cycles, "
         "non-zero focal variance.",
         f"- Inference: wild cluster restricted bootstrap (by sector; H5 by champion), Webb six-point weights, B = "
         f"{params['B']:,} (all 6^G draws enumerated when 6^G <= B), seed {params['seed']}, 95% interval by test inversion; "
         "HC1 errors for reference only. DESCRIPTIVE tests: estimate and HC1 only.",
         f"- PREVIEW tests: fixed window {config.PREVIEW_WINDOW[0]}-{config.PREVIEW_WINDOW[1]} (5 full years); every PREVIEW "
         f"output reads '{config.PREVIEW_FLAG}'.",
         f"- Tests: {len(est_rows)}; ESTIMABLE {counts.get('ESTIMABLE', 0)}, NOT ESTIMABLE {counts.get('NOT ESTIMABLE', 0)}, "
         f"NOT BUILT {counts.get('NOT BUILT', 0)}.",
         "- Inputs (SHA-256, first 16 hex):"]
    for s in sources:
        L.append(f"  - {s['file']}: {(s.get('sha256') or 'n/a')[:16]}" + (f" ({s['note']})" if s.get("note") else ""))
    if notes:
        L += ["", "## Build notes", ""] + [f"- {n}" for n in notes]
    by_test = collections.defaultdict(list)
    for c in coef_rows:
        by_test[c["test_id"]].append(c)
    st_by = collections.defaultdict(list)
    for s in strata_rows:
        st_by[(s["test_id"], s["coefficient"])].append(s)
    L += ["", "## Tests", ""]
    for r in est_rows:
        spec = specs[r["test_id"]]
        h5 = r.get("unit") == H5_UNIT
        L.append(f"### {r['test_id']} ({label_text(r['label'])}): {r['status']}")
        L.append("")
        dv = f"{r.get('dv_column') or spec.dv}" + (f" ({r['dv_label']})" if r.get("dv_label") else "")
        L.append(f"- DV: {dv}; focal: {', '.join(spec.focal) or 'n/a'}; controls: {', '.join(spec.controls) or 'none'}; "
                 f"fixed effects: {', '.join(spec.fe) or 'none'}; variant: {r.get('variant') or spec.variant}; unit: "
                 f"{r.get('unit') or spec.unit}" + (f"; source test: {spec.base}" if spec.base else ""))
        if r.get("note") or spec.note:
            L.append(f"- Note: {r.get('note') or spec.note}")
        if r["status"] != "ESTIMABLE":
            L.append(f"- Reason: {r['reason']}")
            L.append("")
            continue
        if h5:
            L.append(f"- Gate: {r['gate_rule']}.")
            L.append(f"- Sample: cycles {r['years']}; n = {r['n']} rows ({r['n_champions']} champions = clusters, "
                     f"{r['n_member_cycles']} member-cycles, boards {r['boards']}); residual df {r['resid_df']}.")
        else:
            L.append(f"- Window: {r['window_used']} ({r['window_kind']}"
                     + (f"; {r['fallback_search']}" if r.get("fallback_search") else "")
                     + f"); denominator: n = {r['n']} rows, {r['n_sectors']} sectors ({r['sectors']}), {r['n_years']} "
                       f"years ({r['years']}); residual df {r['resid_df']}.")
        if r["exclusions"]:
            L.append(f"- Exclusions: {r['exclusions']}")
        if r.get("input_flags"):
            L.append(f"- Input flags (expected control not from the IEM annual mean): {r['input_flags']}")
        for c in by_test.get(r["test_id"], []):
            if c.get("left_out"):
                continue
            L.append(_coef_line(c, r))
            for s in st_by.get((c.get("source_test") or r["test_id"], c["coefficient"]), []):
                name = f"board {s['board']}" if s.get("board") else s.get("study_sector")
                if s["status"] == "estimated":
                    extra = (f", CR1 se {fmt(s.get('cr1_se'))}; n = {s['n']}, {s.get('n_champions')} champions, cycles "
                             f"{s.get('cycles')}" if s.get("board") else f"; n = {s['n']}, years {s['years']}")
                    L.append(f"  - stratum {name}: b = {fmt(s['estimate'])} (HC1 se {fmt(s['hc1_se'])}{extra}, "
                             f"residual df {s['resid_df']})")
                else:
                    L.append(f"  - stratum {name}: insufficient ({s['reason']})")
        subs = [c for c in by_test.get(r["test_id"], []) if c.get("left_out")]
        for c in subs:
            if c.get("subfit_status") == "estimated":
                L.append(f"- without {c['left_out']}: {c['coefficient']} b = {fmt(c['estimate'])} ({c['unit']}), CI {c['ci_text']}, "
                         f"p = {fmt(c.get('boot_p'))}; n = {c['n']} ({c['n_sectors']} sectors, {c['n_years']} years: {c['years']}). "
                         f"{c.get('subfit_flag') or ''}")
            else:
                L.append(f"- without {c['left_out']}: {c['coefficient']} not estimable ({c.get('subfit_reason')}). "
                         f"{c.get('subfit_flag') or ''}")
        L.append("")
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
