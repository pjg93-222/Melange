#!/usr/bin/env python3
"""Geospatial joins, crosswalks and spatial autocorrelation. Read-only: reads vector files (GeoPackage,
GeoJSON, Shapefile, GeoParquet) and CSV tables; writes only its run folder.

Modes: join (keys via --left-key/--right-key, or --sjoin intersects|within) checks cardinality vs --expect,
unmatched rows, key hygiene, CRS presence/identity/fitness and geometry validity; crosswalk checks weight sums,
split share, unit coverage and ZIP/ZCTA hygiene; autocorr runs global Moran's I (Moran 1950) with a permutation
test (esda/libpysal when installed, numpy as the second path) and LISA counts (Anselin 1995) with --lisa (slow).
Inputs: .gpkg .geojson .json .shp .parquet .geoparquet (vector) and .csv .tsv (tables) only. A .vrt file or a
GDAL virtual or URL path (/vsi..., http:, https:, ftp:) is refused, because GDAL could fetch it over the network.

Usage:
  python scripts/spatial_audit.py --mode join --left L.gpkg --right R.csv --left-key GEOID --right-key fips
  python scripts/spatial_audit.py --mode join --left points.gpkg --right polygons.gpkg --sjoin within
  python scripts/spatial_audit.py --mode crosswalk --xwalk zip_tract.csv --from zip --to tract --weight ratio
  python scripts/spatial_audit.py --mode autocorr --geo counties.gpkg --var resid --weights queen --perm 999

Verdicts ("share rule": 0 affected -> SURVIVES; share <= --kill-share -> WOUNDED; above -> KILLED):
  JOIN-01 cardinality compatible with --expect (default m:1, a lookup keeping one row per left row) ->
          SURVIVES; else WOUNDED, KILLED if the join adds more than --kill-share extra rows vs the left.
  JOIN-02 unmatched share of left rows <= --max-unmatched -> SURVIVES; else WOUNDED.
  JOIN-03 keys matching only after trimming/zero-stripping, null keys on both sides (pandas merges NaN with
          NaN) or number-vs-text keys -> WOUNDED.   JOIN-06 missing, empty or invalid geometries -> WOUNDED.
  JOIN-04 CRS missing -> WOUNDED; different in a spatial join -> KILLED; different in a key join -> WOUNDED.
  JOIN-05 CRS in degrees or Mercator -> WOUNDED; other projected -> SURVIVES; none -> UNVERIFIED-HERE.
  XW-01 weights in [0, 1] summing to 1 per source unit within --tol, no repeated pair; share rule.
  XW-02 source units split across targets without --weight -> WOUNDED (double counting).
  XW-03 --units absent from the --from column; share rule.   XW-04 ZIP-like values not 5 digits -> WOUNDED.
  XW-05 ZIP used as an area (ZIP != ZCTA; crosswalk vintage vs data period): UNVERIFIED-HERE whenever a ZIP
        column is present, because the file cannot show it (Grubesic & Matisziw 2006).
  AC-01 two-sided permutation p <= --alpha -> WOUNDED for any model assuming independent errors; else
        SURVIVES; fewer than --min-n units -> UNVERIFIED-HERE.   AC-02 islands -> WOUNDED.
  AC-PATH (esda ran) |I(esda) - I(numpy)| > --parity-tol -> WOUNDED; esda failed -> UNVERIFIED-HERE.

Exit codes: 0 all SURVIVES · 1 any WOUNDED/KILLED · 2 usage/input error · 3 UNVERIFIED-HERE present.
"""
from __future__ import annotations

import inspect
import math
import pathlib
import re
import sys
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (Check, Report, UsageError, base_parser, run_main, require_file, write_once, emit,
                     optional_import, SURVIVES, WOUNDED, KILLED, UNVERIFIED)

import numpy as np
import pandas as pd
from scipy import sparse, stats
from scipy.sparse import csgraph

SCRIPT = "spatial_audit"
SOURCE = f"quant-model-evaluation/{SCRIPT}"
TABLE_EXT = {".csv", ".tsv"}
VECTOR_EXT = {".gpkg", ".geojson", ".json", ".shp", ".parquet", ".geoparquet"}  # self-contained formats only
VSI_OR_URL = re.compile(r"(^|[\\/])vsi|https?:|ftp:", re.I)  # GDAL virtual filesystems (/vsicurl/, /vsizip/...)
SEVERITY = {SURVIVES: 0, UNVERIFIED: 1, WOUNDED: 2, KILLED: 3}
ZIP_NAME = re.compile(r"zip|postal|zcta", re.I)


def build_parser():
    p = base_parser(__doc__)
    p.add_argument("--mode", required=True, choices=("join", "crosswalk", "autocorr"))
    p.add_argument("--left", help="join: left table (vector file or CSV)")
    p.add_argument("--right", help="join: right table (vector file or CSV)")
    p.add_argument("--left-key", help="join: key column in --left")
    p.add_argument("--right-key", help="join: key column in --right")
    p.add_argument("--sjoin", choices=("intersects", "within"), help="join: spatial predicate instead of keys")
    p.add_argument("--expect", choices=("1:1", "1:m", "m:1", "m:m"), default="m:1", help="join: intended cardinality")
    p.add_argument("--max-unmatched", type=float, default=0.01, help="join: tolerated unmatched share of left rows")
    p.add_argument("--xwalk", help="crosswalk: CSV")
    p.add_argument("--from", dest="from_col", help="crosswalk: source-unit column")
    p.add_argument("--to", dest="to_col", help="crosswalk: target-unit column")
    p.add_argument("--weight", help="crosswalk: share of the source unit allocated to the target")
    p.add_argument("--tol", type=float, default=0.001, help="crosswalk: tolerance on weight sums (default 0.001)")
    p.add_argument("--units", help="crosswalk: CSV listing the source units your data uses")
    p.add_argument("--unit-col", help="crosswalk: unit column in --units")
    p.add_argument("--geo", help="autocorr: vector file holding the variable")
    p.add_argument("--var", help="autocorr: numeric column (use model residuals to test independence)")
    p.add_argument("--weights", default="queen", help="autocorr: queen, rook or knn:K (default queen)")
    p.add_argument("--perm", type=int, default=999, help="autocorr: permutations (default 999)")
    p.add_argument("--min-n", type=int, default=10, help="autocorr: fewest units for a verdict (default 10)")
    p.add_argument("--engine", choices=("auto", "esda", "numpy"), default="auto", help="autocorr: Moran engine")
    p.add_argument("--lisa", action="store_true", help="autocorr: LISA cluster counts (needs esda; slow)")
    p.add_argument("--parity-tol", type=float, default=1e-9, help="autocorr: largest tolerated |I(esda) - I(numpy)|")
    p.add_argument("--alpha", type=float, default=0.05, help="test level (default 0.05)")
    p.add_argument("--kill-share", type=float, default=0.05, help="share above which a count check is KILLED")
    return p


# ---- reading and small helpers ----
def read_any(path: pathlib.Path, flag: str, key_cols=(), gpd=None):
    ext = path.suffix.lower()
    if ext in TABLE_EXT:
        sep = "\t" if ext == ".tsv" else ","
        try:
            header = pd.read_csv(path, sep=sep, nrows=0)
            dtype = {c: str for c in key_cols if c and c in header.columns}  # keep leading zeros
            df = pd.read_csv(path, sep=sep, low_memory=False, dtype=dtype or None)
        except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
            raise UsageError(f"cannot read {flag} {path.name}: {exc}") from None
    else:
        gpd = gpd or optional_import("geopandas")  # imported only when a vector file is read
        if gpd is None:
            raise UsageError(f"{flag} {path.name} is not a CSV/TSV table, and vector files need geopandas")
        try:
            df = gpd.read_parquet(path) if ext in (".parquet", ".geoparquet") else gpd.read_file(path)
        except Exception as exc:
            raise UsageError(f"cannot read {flag} {path.name}: {type(exc).__name__}: {exc}") from None
    if len(df) == 0:
        raise UsageError(f"{flag} {path.name} has no rows")
    return df


def is_geo(df, gpd) -> bool:
    try:
        return gpd is not None and isinstance(df, gpd.GeoDataFrame) and df.geometry is not None
    except AttributeError:  # a GeoDataFrame without an active geometry column
        return False


def geoms_of(gdf) -> np.ndarray:  # shapely geometries as an object array
    return np.asarray(gdf.geometry.values, dtype=object)


def key_text(s: pd.Series) -> pd.Series:
    """Keys as a merge sees them once read as text; integral floats lose '.0'."""
    if pd.api.types.is_numeric_dtype(s) and not pd.api.types.is_bool_dtype(s):
        v = pd.to_numeric(s, errors="coerce").to_numpy(dtype=float, na_value=np.nan)
        out = [None if math.isnan(x) else (str(int(x)) if float(x).is_integer() else repr(float(x))) for x in v]
        return pd.Series(out, index=s.index, dtype="string")
    return s.astype("string")


def norm_key(s: pd.Series) -> pd.Series:
    """Trimmed, upper-cased, no trailing '.0', no leading zeros: '01001', ' 1001' and 1001.0 agree."""
    t = s.astype("string").str.strip().str.upper()
    t = t.str.replace(r"^(\d+)\.0+$", r"\1", regex=True).str.replace(r"^0+(?=\d)", "", regex=True)
    return t.mask(t == "")


def share_verdict(count: int, share: float, kill: float) -> str:
    return SURVIVES if count == 0 else (KILLED if share > kill else WOUNDED)


def need_cols(df, cols, flag):
    missing = [c for c in cols if c and c not in df.columns]
    if missing:
        raise UsageError(f"{flag} has no column(s) {missing}; columns are {[str(c) for c in df.columns][:30]}")


def safe_input(text, flag: str, allowed: set) -> pathlib.Path:
    """Self-contained local formats only: a .vrt or a GDAL virtual path (/vsicurl/, /vsizip/, ...) can make GDAL
    fetch data over the network, and only cite_check may use the network (build spec section 5)."""
    if VSI_OR_URL.search(str(text)):
        raise UsageError(f"{flag}: GDAL virtual-filesystem and URL paths are refused: {text}")
    path = require_file(text, flag)
    if path.suffix.lower() not in allowed:
        raise UsageError(f"{flag}: '{path.suffix}' files are refused (.vrt and other GDAL indirections can reach the "
                         f"network); accepted: {' '.join(sorted(allowed))}")
    return path


# ---- CRS and geometry checks ----
def crs_desc(crs) -> str:
    if crs is None:
        return "no CRS"
    epsg, unit = crs.to_epsg(), (crs.axis_info[0].unit_name if crs.axis_info else "unknown unit")
    return f"{'EPSG:' + str(epsg) if epsg else crs.name} ({'geographic' if crs.is_geographic else 'projected'}, {unit})"


def crs_measure(crs) -> tuple[str, str]:
    if crs is None:
        return UNVERIFIED, "no CRS declared, so coordinate units are unknown"
    if crs.is_geographic:
        return WOUNDED, (f"{crs_desc(crs)}: degrees, so areas and distances computed in it are wrong; reproject "
                         "to an equal-area CRS for areas or a local projected CRS for distances")
    method = getattr(crs.coordinate_operation, "method_name", "") or ""
    if "mercator" in method.lower() and not re.search("transverse|oblique", method, re.I):
        return WOUNDED, f"{crs_desc(crs)} uses {method}: scale grows with latitude, so areas inflate"
    return SURVIVES, f"{crs_desc(crs)}, projection {method or 'n/a'}"


def crs_checks(report, sides: dict, spatial_join: bool) -> None:
    """JOIN-04 and JOIN-05 over the spatial sides {'left': crs, 'right': crs}."""
    missing = [k for k, c in sides.items() if c is None]
    if missing:
        v4, d4 = WOUNDED, f"no CRS on {' and '.join(missing)}; whether the layers share coordinates cannot be verified"
    elif len(sides) == 2 and not sides["left"].equals(sides["right"], ignore_axis_order=True):
        v4 = KILLED if spatial_join else WOUNDED
        d4 = (f"left {crs_desc(sides['left'])} vs right {crs_desc(sides['right'])}; " + ("a naive spatial join compares "
              "incompatible coordinates (right side reprojected here before counting)" if spatial_join else "reproject first"))
    else:
        v4, d4 = SURVIVES, "; ".join(f"{k}: {crs_desc(c)}" for k, c in sides.items())
    report.add(Check("JOIN-04", "CRS declared and identical on the spatial layers", v4,
                     criterion="every spatial layer declares a CRS; both sides share it", detail=d4))
    res = [(k, *crs_measure(c)) for k, c in sides.items()]
    report.add(Check("JOIN-05", "CRS fit for area and distance", max((r[1] for r in res), key=SEVERITY.get),
                     criterion="projected, non-Mercator CRS (degrees and Mercator scale distort area/distance)",
                     detail="; ".join(f"{k}: {d}" for k, _, d in res)))


def geometry_check(report, layers: dict, shapely) -> None:
    parts, bad = [], 0
    for k, gdf in layers.items():
        g = geoms_of(gdf)
        missing = shapely.is_missing(g)
        empty = shapely.is_empty(g) & ~missing
        invalid = ~shapely.is_valid(g) & ~missing & ~empty
        bad += int(missing.sum() + empty.sum() + invalid.sum())
        why = ", ".join(sorted(set(shapely.is_valid_reason(g[invalid][:3])))) if invalid.any() else ""
        parts.append(f"{k}: {int(missing.sum())} missing, {int(empty.sum())} empty, {int(invalid.sum())} invalid"
                     + (f" ({why})" if why else ""))
    report.add(Check("JOIN-06", "Geometries present, non-empty and valid", WOUNDED if bad else SURVIVES,
                     criterion="0 missing, empty or invalid geometries", value=bad, detail="; ".join(parts)))


# ---- mode: join ----
def cardinality(report, lm: bool, rm: bool, both: bool, extra: int, n_left: int, args, detail: str) -> None:
    """lm: a right row meets several left rows ('m' on the left); rm: a left row meets several right rows."""
    label = "m:m" if both else ("m:1 and 1:m on different keys" if lm and rm else
                                {(False, False): "1:1", (True, False): "m:1", (False, True): "1:m"}[(lm, rm)])
    ok = {"1:1": not lm and not rm, "1:m": not lm, "m:1": not rm, "m:m": True}[args.expect]
    v = SURVIVES if ok else (KILLED if extra / n_left > args.kill_share else WOUNDED)
    report.add(Check("JOIN-01", f"Join cardinality matches the expected {args.expect}", v,
                     criterion=f"observed pattern compatible with {args.expect}; KILLED if extra rows > "
                               f"{args.kill_share:g} of left rows", value=label,
                     detail=f"observed {label}; the join adds {extra} row(s) to {n_left} left rows "
                            f"(x{(n_left + extra) / n_left:.3f}); {detail}"))


def unmatched(report, un_l: int, n_left: int, un_r: int, n_right: int, args, extra: str) -> None:
    share = un_l / n_left
    report.add(Check("JOIN-02", "Left rows find a match", SURVIVES if share <= args.max_unmatched else WOUNDED,
                     criterion=f"unmatched share of left rows <= {args.max_unmatched:g}", value=un_l,
                     detail=f"{un_l} of {n_left} left rows ({share:.1%}) unmatched; {un_r} of {n_right} right rows "
                            f"unused{extra}"))


def join_keys(args, report, run_dir, left, right) -> dict:
    need_cols(left, [args.left_key], "--left")
    need_cols(right, [args.right_key], "--right")
    lk, rk = key_text(left[args.left_key]), key_text(right[args.right_key])
    cl, cr = lk.value_counts(dropna=True), rk.value_counts(dropna=True)
    matched = cl.index.intersection(cr.index)
    clm, crm = cl.reindex(matched), cr.reindex(matched)
    rm, extra = bool((crm > 1).any()), int((clm * (crm - 1)).sum())
    cardinality(report, bool((clm > 1).any()), rm, bool(((clm > 1) & (crm > 1)).any()), extra, len(left), args,
                f"{int((cl > 1).sum())} left and {int((cr > 1).sum())} right key values repeat"
                + (f" (e.g. right {', '.join(map(str, crm[crm > 1].index[:3]))})" if rm else ""))
    hit = np.asarray(lk.isin(matched), dtype=bool)
    rec = ~hit & np.asarray(lk.notna() & norm_key(lk).isin(set(norm_key(rk).dropna())), dtype=bool)
    un_l, un_r, n_rec = int((~hit).sum()), int((~np.asarray(rk.isin(matched), dtype=bool)).sum()), int(rec.sum())
    unmatched(report, un_l, len(left), un_r, len(right), args,
              f"; {n_rec} unmatched left rows would match after trimming/zero-stripping" if n_rec else "")
    if un_l:
        um = pd.DataFrame({"key": lk[~hit].fillna("<null>").to_numpy(dtype=object), "recoverable": rec[~hit]})
        write_once(run_dir / "unmatched_left.csv", um.groupby("key", as_index=False).agg(
            rows=("recoverable", "size"), recoverable=("recoverable", "max")).to_csv(index=False, lineterminator="\n"))
    null_l, null_r = int(lk.isna().sum()), int(rk.isna().sum())
    types = ["number" if pd.api.types.is_numeric_dtype(df[c]) else "text"
             for df, c in ((left, args.left_key), (right, args.right_key))]
    issues = [msg for hit_, msg in (
        (n_rec, f"{n_rec} left rows match only after trimming, case-folding or stripping leading zeros"),
        (null_l and null_r, f"null keys on both sides ({null_l} left, {null_r} right): pandas merge pairs NaN with NaN"),
        (types[0] != types[1], f"left key is {types[0]}, right key is {types[1]} (numbers lose leading zeros)")) if hit_]
    report.add(Check("JOIN-03", "Join keys well-formed and consistent", WOUNDED if issues else SURVIVES,
                     criterion="no match recoverable only by normalizing keys; no null keys on both sides; same key type",
                     value=n_rec, detail="; ".join(issues) or f"{null_l} left and {null_r} right null keys; key types "
                                                              f"{types[0]}/{types[1]}"))
    return {"type": "key", "extra_rows": extra, "unmatched_left": un_l, "unmatched_right": un_r, "recoverable": n_rec}


def join_spatial(args, report, left, right, shapely) -> dict:
    if left.crs is not None and right.crs is not None and not left.crs.equals(right.crs, ignore_axis_order=True):
        right = right.to_crs(left.crs)
    lg, rg = geoms_of(left), geoms_of(right)
    tree = shapely.STRtree(rg)
    li, ri = tree.query(lg, predicate=args.sjoin)
    c_l, c_r = np.bincount(li, minlength=len(lg)), np.bincount(ri, minlength=len(rg))
    lm, rm, extra = bool((c_r > 1).any()), bool((c_l > 1).any()), int(np.maximum(c_l - 1, 0).sum())
    note = f"{int((c_l > 1).sum())} left features match several right features"
    if args.sjoin == "intersects" and rm:
        ti, _ = tree.query(lg, predicate="touches")
        note += (f"; {len(set(ti) & set(np.nonzero(c_l > 1)[0]))} of them touch a neighbour's boundary ('intersects' "
                 "counts shared edges; consider 'within', representative points or area weights)")
    cardinality(report, lm, rm, lm and rm, extra, len(lg), args, note)
    un_l, un_r = int((c_l == 0).sum()), int((c_r == 0).sum())
    edge = len(set(tree.query(lg[c_l == 0], predicate="intersects")[0])) if args.sjoin == "within" and un_l else 0
    unmatched(report, un_l, len(lg), un_r, len(rg), args,
              f"; {edge} unmatched left features touch a right boundary (on-boundary is not 'within')" if edge else "")
    return {"type": f"sjoin-{args.sjoin}", "extra_rows": extra, "unmatched_left": un_l, "unmatched_right": un_r}


def mode_join(args, report, run_dir, gpd, shapely) -> None:
    keyed = bool(args.left_key or args.right_key)
    if not (args.left and args.right) or keyed == bool(args.sjoin) or (keyed and not (args.left_key and args.right_key)):
        raise UsageError("--mode join needs --left, --right and either --left-key with --right-key, or --sjoin")
    lp, rp = (safe_input(v, f, TABLE_EXT | VECTOR_EXT) for v, f in ((args.left, "--left"), (args.right, "--right")))
    for path in (lp, rp):
        report.add_input(path)
    left, right = read_any(lp, "--left", [args.left_key], gpd), read_any(rp, "--right", [args.right_key], gpd)
    spatial = {k: df for k, df in (("left", left), ("right", right)) if is_geo(df, gpd)}
    if not keyed and len(spatial) < 2:
        raise UsageError("--sjoin needs two vector files with geometry")
    if spatial:
        crs_checks(report, {k: df.crs for k, df in spatial.items()}, spatial_join=not keyed)
        geometry_check(report, spatial, shapely)
    info = join_keys(args, report, run_dir, left, right) if keyed else join_spatial(args, report, left, right, shapely)
    report.checks.sort(key=lambda c: c.id)
    report.section("Trend", f"{len(left)} left rows, {len(right)} right rows ({info['type']} join): "
                            f"{info['unmatched_left']} left rows unmatched, {info['extra_rows']} extra rows created.")
    report.data["join"] = {"left_rows": len(left), "right_rows": len(right), **info}


# ---- mode: crosswalk ----
def zip_profile(s: pd.Series) -> dict:
    t = s.dropna().astype("string").str.strip()
    return {"values": int(len(t)), "four_digit": int(t.str.fullmatch(r"\d{4}").sum()),
            "zip_plus4": int(t.str.fullmatch(r"\d{5}-?\d{4}").sum()),
            "other": int((~t.str.fullmatch(r"\d{4,5}|\d{5}-?\d{4}")).sum())}


def mode_crosswalk(args, report, run_dir) -> None:
    if not (args.xwalk and args.from_col and args.to_col) or bool(args.units) != bool(args.unit_col):
        raise UsageError("--mode crosswalk needs --xwalk, --from and --to; --units needs --unit-col")
    xp = safe_input(args.xwalk, "--xwalk", TABLE_EXT)
    report.add_input(xp)
    xw = read_any(xp, "--xwalk", [args.from_col, args.to_col])
    need_cols(xw, [args.from_col, args.to_col, args.weight], "--xwalk")
    f, t = xw[args.from_col].astype("string").str.strip(), xw[args.to_col].astype("string").str.strip()
    ok = np.asarray(f.notna() & t.notna(), dtype=bool)
    n_null, n_units, f, t = int((~ok).sum()), int(f[ok].nunique()), f[ok], t[ok]
    w, pos = None, np.ones(len(f), dtype=bool)
    if args.weight:
        w = pd.to_numeric(xw[args.weight], errors="coerce")[ok]
        bad_w = np.asarray(w.isna() | (w < 0) | (w > 1 + args.tol), dtype=bool)
        sums = w.fillna(0).groupby(f.to_numpy()).sum()
        off = (sums - 1).abs() > args.tol
        dup = pd.DataFrame({"f": f.to_numpy(), "t": t.to_numpy()}).duplicated().to_numpy()
        units_bad = set(sums.index[off]) | set(f[bad_w]) | set(f[dup])
        report.add(Check("XW-01", "Allocation weights sum to 1 per source unit",
                         share_verdict(len(units_bad), len(units_bad) / n_units, args.kill_share),
                         criterion=f"|sum - 1| <= {args.tol:g}, weights in [0, 1], no repeated (from, to) pair; "
                                   f"KILLED above {args.kill_share:g} of source units", value=len(units_bad),
                         detail=f"{int(off.sum())} of {n_units} source units off ({int((sums < 1 - args.tol).sum())} lose mass, "
                                f"{int((sums > 1 + args.tol).sum())} create it; sums {sums.min():.4f} to {sums.max():.4f}); "
                                f"{int(bad_w.sum())} missing or out-of-range weights; {int(dup.sum())} repeated pairs"))
        if off.any():
            write_once(run_dir / "weight_sums_off.csv", pd.DataFrame(
                {"unit": sums.index[off], "weight_sum": sums[off].to_numpy()}).to_csv(index=False, lineterminator="\n"))
        pos = np.asarray(w.fillna(0) > 0, dtype=bool)
    ntgt = t[pos].groupby(f[pos].to_numpy()).nunique()
    split = ntgt > 1
    split_share = float(split.mean()) if len(ntgt) else 0.0
    det = f"{int(split.sum())} of {len(ntgt)} source units ({split_share:.1%}) map to more than one target"
    if w is not None and split.any():
        wmax = w[pos].groupby(f[pos].to_numpy()).max()
        det += f"; {int((wmax[split.index[split]] < 0.5).sum())} split units have no majority target"
    v2 = WOUNDED if (w is None and split.any()) else SURVIVES
    det += "; without weights each target would receive the whole source value (double counting)" * (v2 == WOUNDED)
    report.add(Check("XW-02", "Split source units carry explicit allocation weights", v2,
                     criterion="every source unit mapped to several targets has a weight per target",
                     value=round(split_share, 6), detail=det + (f"; {n_null} rows lack from/to" if n_null else "")))
    zsrc = [(f"xwalk {args.from_col}", args.from_col, xw[args.from_col]),
            (f"xwalk {args.to_col}", args.to_col, xw[args.to_col])]
    if args.units:
        up = safe_input(args.units, "--units", TABLE_EXT)
        report.add_input(up)
        ut = read_any(up, "--units", [args.unit_col])
        need_cols(ut, [args.unit_col], "--units")
        zsrc.append((f"units {args.unit_col}", args.unit_col, ut[args.unit_col]))
        units = set(ut[args.unit_col].dropna().astype("string").str.strip())
        missing = sorted(units - set(f))
        pool = set(norm_key(pd.Series(sorted(set(f)), dtype="string")).dropna())
        rec = [u for u, v in zip(missing, norm_key(pd.Series(missing, dtype="string"))) if v in pool]
        share = len(missing) / max(len(units), 1)
        report.add(Check("XW-03", f"Crosswalk covers every unit in {up.name}",
                         share_verdict(len(missing), share, args.kill_share),
                         criterion=f"every listed unit appears in --from; KILLED above {args.kill_share:g} missing",
                         value=len(missing),
                         detail=f"{len(missing)} of {len(units)} units ({share:.1%}) absent from the crosswalk"
                                + (f"; {len(rec)} would match after trimming/zero-stripping (e.g. {', '.join(rec[:3])})"
                                   if rec else "") + (f"; e.g. {', '.join(missing[:3])}" if missing else "")))
        if missing:
            write_once(run_dir / "missing_units.csv", pd.DataFrame(
                {"unit": missing, "recoverable": [u in set(rec) for u in missing]}).to_csv(index=False, lineterminator="\n"))
    zcols = [(label, name, s) for label, name, s in zsrc if ZIP_NAME.search(str(name))]
    if zcols:
        prof = {label: zip_profile(s) for label, _, s in zcols}
        bad = sum(p["four_digit"] + p["zip_plus4"] + p["other"] for p in prof.values())
        report.add(Check("XW-04", "ZIP-like columns hold 5-digit codes", WOUNDED if bad else SURVIVES,
                         criterion="every value in a ZIP/ZCTA-named column is exactly 5 digits", value=bad,
                         detail="; ".join(f"{k}: {p['four_digit']} four-digit (lost leading zero), {p['zip_plus4']} "
                                          f"ZIP+4, {p['other']} other, of {p['values']}" for k, p in prof.items())))
        if any(re.search(r"zip|postal", str(name), re.I) for _, name, _ in zcols):
            report.add(Check("XW-05", "ZIP Codes used as areas match the crosswalk geography and vintage", UNVERIFIED,
                             criterion="cannot be tested from the file; needs the crosswalk source and date",
                             detail="ZIP Codes are USPS delivery routes, not areas; ZCTAs are census approximations that "
                                    "omit PO-box and unique ZIPs; ZIP-to-tract/county allocations change each quarter. State "
                                    "the crosswalk source and quarter; match it to the data period (Grubesic & Matisziw 2006)."))
    report.section("Trend", f"{len(xw)} crosswalk rows, {n_units} source units, {int(t.nunique())} target units; "
                            f"{split_share:.1%} of source units split across targets.")
    report.data["crosswalk"] = {"rows": int(len(xw)), "source_units": n_units, "split_share": split_share,
                                "rows_without_from_or_to": n_null}


# ---- mode: autocorr ----
def parse_weights(text: str) -> tuple[str, int]:
    m = re.fullmatch(r"\s*(queen|rook|knn:(\d+))\s*", (text or "").lower())
    if not m or (m.group(2) is not None and int(m.group(2)) < 1):
        raise UsageError(f"--weights {text!r}: use queen, rook or knn:K with K >= 1")
    return ("knn", int(m.group(2))) if m.group(2) else (m.group(1), 0)


def contiguity_pairs(geoms: np.ndarray, rule: str, shapely) -> tuple[np.ndarray, np.ndarray]:
    """Queen: polygons share any point (shapely intersects). Rook: boundaries share a segment of positive
    length. Geometric, so T-junctions count (libpysal's vertex matching can miss them)."""
    i, j = shapely.STRtree(geoms).query(geoms, predicate="intersects")
    keep = i != j
    i, j = i[keep], j[keep]
    if rule == "rook" and len(i):
        bnd = shapely.boundary(geoms)
        keep = shapely.length(shapely.intersection(bnd[i], bnd[j])) > 0
        i, j = i[keep], j[keep]
    return i, j


def knn_pairs(geoms: np.ndarray, k: int, geographic: bool, shapely) -> tuple[np.ndarray, np.ndarray]:
    """k nearest centroids; a geographic CRS is mapped to the unit sphere so chord order = great-circle order."""
    xy = shapely.get_coordinates(shapely.centroid(geoms))
    if geographic:
        lon, lat = np.radians(xy[:, 0]), np.radians(xy[:, 1])
        xy = np.column_stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)])
    n = len(xy)
    if k >= n:
        raise UsageError(f"knn:{k} needs more than {k} units; there are {n}")
    from scipy.spatial import cKDTree
    _, idx = cKDTree(xy).query(xy, k=k + 1)
    rows = np.broadcast_to(np.arange(n)[:, None], idx.shape)
    drop = idx == rows
    drop[~drop.any(axis=1), -1] = True  # self not returned (duplicate points): drop the farthest instead
    return rows[~drop], idx[~drop]


def binary_matrix(i, j, n) -> sparse.csr_matrix:
    a = sparse.csr_matrix((np.ones(len(i)), (i, j)), shape=(n, n))
    a.data[:] = 1.0
    return a


def row_standardize(a: sparse.csr_matrix) -> sparse.csr_matrix:
    deg = np.asarray(a.sum(axis=1)).ravel()
    return sparse.csr_matrix(sparse.diags(np.divide(1.0, deg, out=np.zeros_like(deg), where=deg > 0)) @ a)


def moran_numpy(y: np.ndarray, w: sparse.csr_matrix, perm: int, rng) -> dict:
    """Global Moran's I = (n/S0) z'Wz / z'z with normality moments (Cliff & Ord 1981) and a permutation
    test whose pseudo p-value follows esda: (min(#sims >= I, #sims < I) + 1) / (perm + 1)."""
    n, z = len(y), y - y.mean()
    zz, s0 = float(z @ z), float(w.sum())
    i_obs, ei = n / s0 * float(z @ (w @ z)) / zz, -1.0 / (n - 1)
    s1 = 0.5 * float((w + w.T).multiply(w + w.T).sum())  # S1 = 1/2 sum_ij (w_ij + w_ji)^2
    s2 = float(((np.asarray(w.sum(axis=1)).ravel() + np.asarray(w.sum(axis=0)).ravel()) ** 2).sum())
    vi = (n * n * s1 - n * s2 + 3 * s0 * s0) / ((n * n - 1) * s0 * s0) - ei * ei
    z_norm = (i_obs - ei) / math.sqrt(vi) if vi > 0 else math.nan
    out = {"I": i_obs, "EI": ei, "VI_norm": vi, "z_norm": z_norm, "p_norm": float(2 * stats.norm.sf(abs(z_norm)))}
    sims, done, batch = np.empty(perm), 0, max(1, min(perm, 2_000_000 // n))
    while done < perm:
        m = min(batch, perm - done)
        zp = rng.permuted(np.repeat(z[:, None], m, axis=1), axis=0)  # an independent shuffle per column
        sims[done:done + m] = n / s0 * np.einsum("ij,ij->j", zp, w @ zp) / zz
        done += m
    larger, sd = int((sims >= i_obs).sum()), float(sims.std())
    out.update(p_sim=(min(larger, perm - larger) + 1) / (perm + 1), EI_sim=float(sims.mean()),
               z_sim=(i_obs - float(sims.mean())) / sd if sd > 0 else math.nan)
    return out


def esda_moran(lps, esda, y, a, res, args, run_dir, run_id) -> tuple[str, float | None, dict | None, str]:
    """esda on the same binary matrix: global Moran (primary when --engine allows) and LISA on request."""
    path, parity, counts = "numpy", None, None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            w_lib = lps.weights.WSP(a).to_W(silence_warnings=True)
            w_lib.transform = "r"
            if args.engine != "numpy":
                np.random.seed(args.seed % 2 ** 32)  # esda permutes with numpy's global generator
                mi = esda.moran.Moran(y, w_lib, transformation="r", permutations=args.perm)
                parity = abs(float(mi.I) - res["I"])
                res.update(I=float(mi.I), EI=float(mi.EI), p_sim=float(mi.p_sim), z_sim=float(mi.z_sim),
                           EI_sim=float(mi.EI_sim), p_norm=float(mi.p_norm), z_norm=float(mi.z_norm))
                path = "esda"
            if args.lisa:
                emit("stage", "running", "LISA (esda; numba compiles on first call)", run_id=run_id, source=SOURCE)
                kw = {"seed": args.seed % 2 ** 32} if "seed" in inspect.signature(esda.moran.Moran_Local).parameters else {}
                lisa = esda.moran.Moran_Local(y, w_lib, transformation="r", permutations=args.perm, **kw)
                q, p = np.asarray(lisa.q), np.asarray(lisa.p_sim)
                write_once(run_dir / "lisa.csv", pd.DataFrame({"row": np.arange(len(y)), "Ii": np.asarray(lisa.Is), "q": q,
                                                              "p_sim": p}).to_csv(index=False, lineterminator="\n"))
                counts = {nm: int(((q == c) & (p <= args.alpha)).sum()) for c, nm in ((1, "HH"), (2, "LH"), (3, "LL"), (4, "HL"))}
        except Exception as exc:  # esda present but failed: keep the numpy result and say so
            return path, parity, counts, f"; esda step failed ({type(exc).__name__}: {str(exc)[:120]})"
    return path, parity, counts, ""


def mode_autocorr(args, report, run_dir, run_id, gpd, shapely) -> None:
    if not (args.geo and args.var):
        raise UsageError("--mode autocorr needs --geo and --var")
    rule, k = parse_weights(args.weights)
    if args.perm < 99 or args.min_n < 3:
        raise UsageError("--perm must be >= 99 and --min-n >= 3")
    gp = safe_input(args.geo, "--geo", VECTOR_EXT)
    report.add_input(gp)
    gdf = read_any(gp, "--geo", (), gpd)
    if not is_geo(gdf, gpd):
        raise UsageError("--geo must be a vector file with geometry")
    need_cols(gdf, [args.var], "--geo")
    y_all, g_all = pd.to_numeric(gdf[args.var], errors="coerce").to_numpy(dtype=float, na_value=np.nan), geoms_of(gdf)
    keep = np.isfinite(y_all) & ~shapely.is_missing(g_all) & ~shapely.is_empty(g_all)
    y, geoms, dropped, n = y_all[keep], g_all[keep], int((~keep).sum()), int(keep.sum())
    if n < 3 or float(np.std(y)) == 0:
        raise UsageError(f"--var needs at least 3 usable units with some variation (have {n})")
    if rule != "knn" and not set(shapely.get_type_id(geoms).tolist()) <= {3, 6}:
        raise UsageError(f"{rule} contiguity needs polygons; use --weights knn:K for points or lines")
    lps, esda = (optional_import("libpysal"), optional_import("esda")) if args.engine != "numpy" or args.lisa else (None, None)
    if args.engine == "esda" and (lps is None or esda is None):
        raise UsageError("--engine esda needs libpysal and esda installed")
    geographic = bool(gdf.crs is not None and gdf.crs.is_geographic)
    pairs = knn_pairs(geoms, k, geographic, shapely) if rule == "knn" else contiguity_pairs(geoms, rule, shapely)
    a = binary_matrix(*pairs, n)
    deg = np.asarray(a.sum(axis=1)).ravel()
    islands = int((deg == 0).sum())
    if islands == n:
        raise UsageError("no unit has a neighbour under these weights")
    ncomp = int(csgraph.connected_components(a + a.T, directed=False)[0])
    emit("stage", "running", f"Moran's I with {args.perm} permutations", run_id=run_id, source=SOURCE)
    res = moran_numpy(y, row_standardize(a), args.perm, np.random.default_rng(args.seed))
    i_np, path, parity, lisa_counts, note = res["I"], "numpy", None, None, ""
    if lps is not None and esda is not None:
        path, parity, lisa_counts, note = esda_moran(lps, esda, y, a, res, args, run_dir, run_id)
    elif args.lisa:
        note = "; LISA skipped: needs libpysal and esda"
    p_two = min(1.0, 2 * res["p_sim"])
    v1 = UNVERIFIED if n < args.min_n else (WOUNDED if p_two <= args.alpha else SURVIVES)
    sign = ("positive: neighbours resemble each other (clustering)" if res["I"] > res["EI"] else
            "negative: neighbours differ (checkerboard-like dispersion)")
    report.add(Check("AC-01", f"No spatial autocorrelation in {args.var}", v1,
                     criterion=f"two-sided permutation p > {args.alpha:g} ({args.perm} permutations, {args.weights} "
                               f"weights, row-standardized); n >= {args.min_n}", value=round(res["I"], 6),
                     detail=f"I = {res['I']:.4f} vs E[I] = {res['EI']:.4f} ({sign}); z_sim {res['z_sim']:.2f}, "
                            f"p_sim {res['p_sim']:.4f} (one-tailed, esda convention), two-sided p {p_two:.4f}; "
                            f"n = {n}" + (f", {dropped} unit(s) dropped for missing values or geometry" if dropped else "")
                            + "; independence-based SEs are too small: use spatial HAC/Conley SEs or a spatial model, and "
                              "test residuals, not the raw outcome" * (v1 == WOUNDED)))
    report.add(Check("AC-02", "Every unit has at least one neighbour", WOUNDED if islands else SURVIVES,
                     criterion="0 islands under the chosen weights", value=islands,
                     detail=f"{islands} island(s); {ncomp} connected component(s); mean neighbours {deg.mean():.2f}"
                            + ("; islands add to z'z but not to z'Wz, pulling I toward 0: drop them explicitly or "
                               "use knn weights" if islands else "")))
    if parity is not None or (lps is not None and esda is not None and args.engine != "numpy"):  # two engines ran
        report.add(Check("AC-PATH", "esda and numpy agree on Moran's I", UNVERIFIED if parity is None else
                         (WOUNDED if parity > args.parity_tol else SURVIVES), value=parity,
                         criterion=f"|I(esda) - I(numpy)| <= {args.parity_tol:g} on the same weights",
                         detail=note.lstrip("; ") if parity is None else f"esda {res['I']:.15g} vs numpy {i_np:.15g}"))
    report.section("Trend", f"Moran's I {res['I']:.4f} (E[I] {res['EI']:.4f}) for {args.var} over {n} units, "
                            f"{args.weights} weights; two-sided permutation p {p_two:.4f}. Engine: {path}"
                            + (f"; numpy parity |dI| = {parity:.2e}" if parity is not None else
                               "; no second computation path (esda/libpysal not used)") + note + "."
                            + ("" if lisa_counts is None else f" LISA clusters at p <= {args.alpha:g} (not adjusted for "
                               "multiple testing): " + ", ".join(f"{k} {v}" for k, v in lisa_counts.items()) + "."))
    report.data["moran"] = {**res, "p_two_sided": p_two, "n": n, "dropped": dropped, "weights": args.weights,
                            "islands": islands, "components": ncomp, "engine": path, "parity_abs_diff": parity,
                            "lisa_counts": lisa_counts, "crs": crs_desc(gdf.crs)}


def main(args, report: Report, run_dir: pathlib.Path, run_id: str) -> None:
    if any((not 0 < args.alpha < 1, not 0 <= args.kill_share < 1, not 0 <= args.max_unmatched < 1, args.tol <= 0,
            args.parity_tol < 0)):
        raise UsageError("--alpha in (0, 1); --kill-share, --max-unmatched in [0, 1); --tol > 0; --parity-tol >= 0")
    report.note_packages(["numpy", "pandas", "scipy", "geopandas", "shapely", "pyproj", "pyogrio", "libpysal", "esda"])
    if args.mode == "crosswalk":
        return mode_crosswalk(args, report, run_dir)
    vector = args.mode == "autocorr" or any(f and pathlib.Path(f).suffix.lower() not in TABLE_EXT for f in (args.left, args.right))
    gpd, shapely = (optional_import("geopandas"), optional_import("shapely")) if vector else (None, None)
    if vector and (gpd is None or shapely is None):
        report.add(Check("GEO-00", f"{args.mode} mode on vector files", UNVERIFIED, criterion="needs geopandas and shapely",
                         detail="install geopandas (with shapely) to read vector files; nothing was tested"))
    elif args.mode == "join":
        mode_join(args, report, run_dir, gpd, shapely)
    else:
        mode_autocorr(args, report, run_dir, run_id, gpd, shapely)


if __name__ == "__main__":
    sys.exit(run_main(SCRIPT, main, build_parser()))
