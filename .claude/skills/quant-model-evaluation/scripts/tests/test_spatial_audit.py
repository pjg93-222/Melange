# -*- coding: utf-8 -*-
"""Tests for scripts/spatial_audit.py (build spec section 6.4).

Known answers: Moran's I on a 10x10 checkerboard with rook weights is exactly -1, a smooth gradient is
strongly positive, and white noise sits near E[I] = -1/(n-1); planted join defects (keys that lost leading
zeros, a duplicated right key, a point on a shared boundary, mismatched CRS) and crosswalk defects (a unit
whose weights sum to 0.9, a four-digit ZIP, uncovered units) are counted exactly. Negative controls: noise
on the lattice and a clean 1:1 key join. Usage errors exit 2. The run folder holds every output and the
input GeoPackage is unchanged. Fixtures are built in code with shapely box() and written to tmp_path.
The esda-path test is skipped when esda/libpysal are not installed.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

try:
    from conftest import SCRIPTS, latest_report, latest_run_dir, sha256
except ImportError:  # conftest.py (agent S1) absent: minimal fallback with the same API (spec 6.6)
    SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(SCRIPTS))

    def latest_run_dir(out_dir):
        reports = sorted(pathlib.Path(out_dir).glob("*/report.json"), key=lambda p: p.stat().st_mtime)
        assert reports, f"no */report.json under {out_dir}"
        return reports[-1].parent

    def latest_report(out_dir):
        return json.loads((latest_run_dir(out_dir) / "report.json").read_text(encoding="utf-8"))

    def sha256(path):
        return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

    @pytest.fixture
    def run_script(tmp_path):
        def _run(name, *args, tmp_path=tmp_path, timeout=120, env=None):
            cmd = [sys.executable, str(SCRIPTS / name), *map(str, args), "--no-glassbox", "--out", str(tmp_path)]
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return _run

gpd = pytest.importorskip("geopandas")
shapely = pytest.importorskip("shapely")
from pyproj import CRS  # noqa: E402  (geopandas dependency)
from shapely.geometry import Point, Polygon, box  # noqa: E402

import spatial_audit as sa  # noqa: E402  (scripts/ is on sys.path)

SCRIPT = "spatial_audit.py"


def checks(report: dict) -> dict:
    return {c["id"]: c for c in report["checks"]}


def run_inprocess(out: pathlib.Path, *argv) -> tuple[int, dict | None]:
    code = sa.run_main(sa.SCRIPT, sa.main, sa.build_parser(),
                       argv=[*map(str, argv), "--no-glassbox", "--quiet", "--out", str(out)])
    return code, (latest_report(out) if code != 2 else None)


def lattice(n: int = 10, crs: str = "EPSG:32618") -> "gpd.GeoDataFrame":
    cells = [(i, j) for i in range(n) for j in range(n)]
    return gpd.GeoDataFrame({"GEOID": [f"{k:05d}" for k in range(n * n)],
                             "checker": [float((i + j) % 2) for i, j in cells],
                             "gradient": [float(i + j) for i, j in cells],
                             "noise": np.random.default_rng(3).normal(size=n * n)},
                            geometry=[box(i, j, i + 1, j + 1) for i, j in cells], crs=crs)


def save(gdf, path: pathlib.Path) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GPKG")
    return path


def csv(df: pd.DataFrame, path: pathlib.Path) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def matrix(gdf, rule: str):
    return sa.row_standardize(sa.binary_matrix(*sa.contiguity_pairs(sa.geoms_of(gdf), rule, shapely), len(gdf)))


# ---- Moran's I known answers (numpy path, in-process) ----
def test_known_answer_moran_lattices():
    g = lattice()
    rng = np.random.default_rng(1)
    checker = sa.moran_numpy(g["checker"].to_numpy(), matrix(g, "rook"), 999, rng)
    assert checker["I"] == pytest.approx(-1.0, abs=1e-12)  # every rook neighbour has the opposite colour
    assert checker["EI"] == pytest.approx(-1 / 99) and checker["p_sim"] == pytest.approx(1 / 1000)
    gradient = sa.moran_numpy(g["gradient"].to_numpy(), matrix(g, "queen"), 999, rng)
    assert gradient["I"] > 0.9 and gradient["p_sim"] == pytest.approx(1 / 1000)
    noise = sa.moran_numpy(g["noise"].to_numpy(), matrix(g, "queen"), 999, rng)
    assert abs(noise["z_norm"]) < 2 and noise["p_sim"] > 0.05  # negative control


def test_known_answer_normality_variance_matches_spdep():
    """CR-16: Var(I) under normality depends only on W. Reference values from R spdep 1.4.2,
    moran.test(x, nb2listw(cell2nb(10, 10, type), style = "W"), randomisation = FALSE) with x = i + j:
    rook I 0.96, Var 0.0054864728897132372; queen I 0.93309090909090919, Var 0.0028594807460543825.
    The variance pins S0, S1 and S2 (dropping the 1/2 in S1 fails this test)."""
    g = lattice()
    for rule, i_ref, vi_ref in (("rook", 0.96, 0.0054864728897132372),
                                ("queen", 0.93309090909090919, 0.0028594807460543825)):
        res = sa.moran_numpy(g["gradient"].to_numpy(), matrix(g, rule), 99, np.random.default_rng(0))
        assert res["I"] == pytest.approx(i_ref, rel=1e-12)
        assert res["VI_norm"] == pytest.approx(vi_ref, rel=1e-12)
        assert res["EI"] == pytest.approx(-1 / 99, rel=1e-15)


def test_contiguity_and_knn_neighbour_counts():
    g = lattice(3)
    geoms = sa.geoms_of(g)
    rook = sa.binary_matrix(*sa.contiguity_pairs(geoms, "rook", shapely), 9).sum(axis=1).A.ravel()
    queen = sa.binary_matrix(*sa.contiguity_pairs(geoms, "queen", shapely), 9).sum(axis=1).A.ravel()
    assert (rook[4], queen[4], rook[0], queen[0]) == (4, 8, 2, 3)  # centre and corner cells
    knn = sa.binary_matrix(*sa.knn_pairs(geoms, 2, False, shapely), 9)
    assert (knn.sum(axis=1).A.ravel() == 2).all() and knn.diagonal().sum() == 0


def test_knn_uses_great_circle_order_for_geographic_crs():
    pts = np.array([Point(179.9, 0.0), Point(-179.9, 0.0), Point(170.0, 0.0)], dtype=object)
    i, j = sa.knn_pairs(pts, 1, True, shapely)
    assert dict(zip(i.tolist(), j.tolist()))[0] == 1  # 0.2 degrees apart across the antimeridian
    i, j = sa.knn_pairs(pts, 1, False, shapely)
    assert dict(zip(i.tolist(), j.tolist()))[0] == 2  # naive planar degrees would pick the far point


def test_crs_fitness_for_area_and_distance():
    assert sa.crs_measure(CRS("EPSG:4326"))[0] == "WOUNDED"   # degrees
    assert sa.crs_measure(CRS("EPSG:3857"))[0] == "WOUNDED"   # Web Mercator
    assert sa.crs_measure(CRS("EPSG:5070"))[0] == "SURVIVES"  # CONUS Albers equal-area
    assert sa.crs_measure(CRS("EPSG:32618"))[0] == "SURVIVES"  # UTM (transverse Mercator)
    assert sa.crs_measure(None)[0] == "UNVERIFIED-HERE"


# ---- through the CLI: known answer, negative control + run folder, usage error ----
def test_known_answer_checkerboard_cli(run_script, tmp_path):
    geo = save(lattice(), tmp_path / "in" / "lattice.gpkg")
    out = tmp_path / "out"
    proc = run_script(SCRIPT, "--mode", "autocorr", "--geo", geo, "--var", "checker", "--weights", "rook",
                      "--engine", "numpy", tmp_path=out)
    assert proc.returncode == 1, proc.stderr + proc.stdout
    c = checks(latest_report(out))
    assert c["AC-01"]["verdict"] == "WOUNDED" and c["AC-01"]["value"] == pytest.approx(-1.0, abs=1e-9)
    assert "negative" in c["AC-01"]["detail"] and c["AC-02"]["verdict"] == "SURVIVES"


def test_negative_control_and_run_folder_contract(run_script, tmp_path):
    geo = save(lattice(), tmp_path / "in" / "lattice.gpkg")
    before, listing = sha256(geo), sorted(f.name for f in geo.parent.iterdir())
    out = tmp_path / "out"
    proc = run_script(SCRIPT, "--mode", "autocorr", "--geo", geo, "--var", "noise", "--weights", "queen",
                      "--engine", "numpy", "--perm", "499", tmp_path=out)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    rep = latest_report(out)
    assert {c["verdict"] for c in rep["checks"]} == {"SURVIVES"}
    assert {c["id"] for c in rep["checks"]} == {"AC-01", "AC-02"}  # no AC-PATH when only numpy ran
    assert rep["data"]["moran"]["engine"] == "numpy" and rep["data"]["moran"]["n"] == 100
    run = latest_run_dir(out)
    assert list(out.iterdir()) == [run] and {f.name for f in run.iterdir()} == {"report.json", "report.md"}
    assert sha256(geo) == before and sorted(f.name for f in geo.parent.iterdir()) == listing


def test_usage_error_exits_2(run_script, tmp_path):
    geo = save(lattice(3), tmp_path / "in" / "small.gpkg")
    proc = run_script(SCRIPT, "--mode", "autocorr", "--geo", geo, "--var", "noise", "--weights", "hexagon",
                      tmp_path=tmp_path / "out")
    assert proc.returncode == 2
    assert "usage error" in proc.stderr and "Traceback" not in proc.stderr


def test_gdal_indirection_and_urls_are_refused(tmp_path, capsys):
    """CR-14: a local .vrt can make GDAL fetch a URL, so .vrt files, GDAL virtual paths and URLs are refused before
    anything is opened, and only self-contained formats are read."""
    vrt = tmp_path / "in" / "remote.vrt"
    vrt.parent.mkdir(parents=True)
    vrt.write_text('<OGRVRTDataSource><OGRVRTLayer name="x"><SrcDataSource>/vsicurl/http://127.0.0.1:9/x.geojson'
                   "</SrcDataSource></OGRVRTLayer></OGRVRTDataSource>", encoding="utf-8")
    table = csv(pd.DataFrame({"k": ["a"]}), tmp_path / "in" / "t.csv")
    cases = [("--mode", "autocorr", "--geo", vrt, "--var", "v"),
             ("--mode", "join", "--left", "/vsizip/C:/data/x.zip/a.shp", "--right", table, "--sjoin", "within"),
             ("--mode", "join", "--left", table, "--right", "https://example.org/r.csv", "--left-key", "k",
              "--right-key", "k"),
             ("--mode", "crosswalk", "--xwalk", save(lattice(3), tmp_path / "in" / "x.gpkg"), "--from", "GEOID",
              "--to", "GEOID")]  # crosswalks and unit lists are tables only
    for i, argv in enumerate(cases):
        assert run_inprocess(tmp_path / f"o{i}", *argv)[0] == 2
    err = capsys.readouterr().err
    assert "'.vrt' files are refused" in err and "'.gpkg' files are refused" in err
    assert err.count("GDAL virtual-filesystem and URL paths are refused") == 2
    assert sa.VSI_OR_URL.search("/vsicurl/http://h/x") and not sa.VSI_OR_URL.search(r"C:\data\devsite\x.gpkg")


@pytest.mark.parametrize("argv", [["--mode", "join", "--left", "L.csv"],                        # no --right
                                  ["--mode", "crosswalk", "--xwalk", "X.csv", "--from", "a"],     # no --to
                                  ["--mode", "autocorr", "--geo", "G.gpkg"]])                     # no --var
def test_incomplete_mode_arguments_exit_2(tmp_path, argv):
    assert run_inprocess(tmp_path / "out", *argv)[0] == 2


# ---- joins (in-process) ----
def test_known_answer_key_join_defects(tmp_path):
    """Right keys 0, 1, 2 lost their leading zeros and 00050 appears twice: 3 unmatched but recoverable
    left rows, a 1:m pattern that breaks the default m:1 lookup, and one extra row."""
    left = save(lattice(), tmp_path / "in" / "left.gpkg")
    fips = [str(k) if k < 3 else f"{k:05d}" for k in range(100)] + ["00050"]
    right = csv(pd.DataFrame({"fips": fips, "pop": np.arange(101)}), tmp_path / "in" / "right.csv")
    code, rep = run_inprocess(tmp_path / "out", "--mode", "join", "--left", left, "--right", right,
                              "--left-key", "GEOID", "--right-key", "fips")
    c = checks(rep)
    assert code == 1
    assert (c["JOIN-01"]["verdict"], c["JOIN-01"]["value"]) == ("WOUNDED", "1:m")
    assert rep["data"]["join"]["extra_rows"] == 1
    assert (c["JOIN-02"]["value"], c["JOIN-03"]["value"]) == (3, 3)
    assert c["JOIN-03"]["verdict"] == "WOUNDED"
    assert [c[k]["verdict"] for k in ("JOIN-04", "JOIN-05", "JOIN-06")] == ["SURVIVES"] * 3
    unmatched = pd.read_csv(latest_run_dir(tmp_path / "out") / "unmatched_left.csv", dtype={"key": str})
    assert unmatched["key"].tolist() == ["00000", "00001", "00002"] and unmatched["recoverable"].all()


def test_negative_control_clean_key_join(tmp_path):
    keys = [f"{k:05d}" for k in range(50)]
    left = csv(pd.DataFrame({"geoid": keys, "votes": range(50)}), tmp_path / "in" / "a.csv")
    right = csv(pd.DataFrame({"geoid": keys[::-1], "pop": range(50)}), tmp_path / "in" / "b.csv")
    code, rep = run_inprocess(tmp_path / "out", "--mode", "join", "--left", left, "--right", right,
                              "--left-key", "geoid", "--right-key", "geoid", "--expect", "1:1")
    assert code == 0 and {c["verdict"] for c in rep["checks"]} == {"SURVIVES"}


def test_spatial_join_boundary_point_and_crs_mismatch(tmp_path):
    polys = save(lattice(), tmp_path / "in" / "cells.gpkg")
    pts = gpd.GeoDataFrame({"pid": range(4)}, geometry=[Point(0.5, 0.5), Point(3.2, 7.7), Point(9.9, 0.1),
                                                        Point(5.0, 5.5)], crs="EPSG:32618")  # last one on an edge
    code, rep = run_inprocess(tmp_path / "o1", "--mode", "join", "--left", save(pts, tmp_path / "in" / "pts.gpkg"),
                              "--right", polys, "--sjoin", "within")
    c = checks(rep)
    assert (c["JOIN-01"]["verdict"], c["JOIN-02"]["value"]) == ("SURVIVES", 1)
    assert "1 unmatched left features touch a right boundary" in c["JOIN-02"]["detail"]
    code, rep = run_inprocess(tmp_path / "o2", "--mode", "join", "--right", polys, "--sjoin", "intersects",
                              "--left", save(pts.set_crs("EPSG:4326", allow_override=True), tmp_path / "in" / "p84.gpkg"))
    c = checks(rep)
    assert c["JOIN-04"]["verdict"] == "KILLED" and c["JOIN-05"]["verdict"] == "WOUNDED"


def test_invalid_geometry_is_flagged(tmp_path):
    g = lattice(3)
    g.loc[4, "geometry"] = Polygon([(0, 0), (1, 1), (1, 0), (0, 1)])  # a self-intersecting bow-tie
    left = save(g, tmp_path / "in" / "bow.gpkg")
    right = csv(pd.DataFrame({"GEOID": g["GEOID"]}), tmp_path / "in" / "ids.csv")
    code, rep = run_inprocess(tmp_path / "out", "--mode", "join", "--left", left, "--right", right,
                              "--left-key", "GEOID", "--right-key", "GEOID")
    c = checks(rep)
    assert c["JOIN-06"]["verdict"] == "WOUNDED" and c["JOIN-06"]["value"] == 1
    assert "Self-intersection" in c["JOIN-06"]["detail"]


# ---- crosswalks (in-process) ----
def test_known_answer_crosswalk_defects(tmp_path):
    xw = csv(pd.DataFrame({"zip": ["02139", "02139", "02140", "02141", "2142", "10001"],
                           "tract": ["A", "B", "A", "C", "C", "D"],
                           "res_ratio": [0.6, 0.4, 1.0, 0.9, 1.0, 1.0]}), tmp_path / "in" / "xw.csv")
    units = csv(pd.DataFrame({"zip": ["02139", "02140", "02142", "99999"]}), tmp_path / "in" / "units.csv")
    code, rep = run_inprocess(tmp_path / "out", "--mode", "crosswalk", "--xwalk", xw, "--from", "zip", "--to", "tract",
                              "--weight", "res_ratio", "--units", units, "--unit-col", "zip")
    c = checks(rep)
    assert code == 1
    assert (c["XW-01"]["verdict"], c["XW-01"]["value"]) == ("KILLED", 1)  # 02141 sums to 0.9: 1 of 5 units
    assert (c["XW-02"]["verdict"], c["XW-02"]["value"]) == ("SURVIVES", 0.2)
    assert (c["XW-03"]["verdict"], c["XW-03"]["value"]) == ("KILLED", 2)  # 02142 (recoverable) and 99999
    assert "1 would match after trimming" in c["XW-03"]["detail"]
    assert (c["XW-04"]["verdict"], c["XW-04"]["value"]) == ("WOUNDED", 1)  # '2142' lost its leading zero
    assert c["XW-05"]["verdict"] == "UNVERIFIED-HERE"


def test_unweighted_split_double_counts(tmp_path):
    xw = csv(pd.DataFrame({"precinct": ["P1", "P1", "P2"], "district": ["D1", "D2", "D2"]}), tmp_path / "in" / "x.csv")
    code, rep = run_inprocess(tmp_path / "out", "--mode", "crosswalk", "--xwalk", xw, "--from", "precinct",
                              "--to", "district")
    assert code == 1 and checks(rep)["XW-02"]["verdict"] == "WOUNDED"
    assert set(checks(rep)) == {"XW-02"}  # no weights, no unit list, no ZIP columns


def test_islands_are_flagged(tmp_path):
    g = lattice(4)
    island = gpd.GeoDataFrame({"GEOID": ["99999"], "checker": [0.0], "gradient": [0.0], "noise": [0.0]},
                              geometry=[box(50, 50, 51, 51)], crs=g.crs)
    geo = save(pd.concat([g, island], ignore_index=True), tmp_path / "in" / "island.gpkg")
    code, rep = run_inprocess(tmp_path / "out", "--mode", "autocorr", "--geo", geo, "--var", "gradient",
                              "--engine", "numpy", "--perm", "199")
    c = checks(rep)
    assert (c["AC-02"]["verdict"], c["AC-02"]["value"]) == ("WOUNDED", 1)
    assert rep["data"]["moran"]["components"] == 2


# ---- esda path (runs only when esda and libpysal are installed) ----
def test_esda_engine_matches_numpy(tmp_path, monkeypatch):
    """CR-15: when both engines run, AC-PATH judges their agreement: SURVIVES on the real engines, WOUNDED when
    numpy's I is nudged by 1e-6 (> --parity-tol 1e-9), UNVERIFIED-HERE when esda fails."""
    esda = pytest.importorskip("esda")
    pytest.importorskip("libpysal")
    geo = save(lattice(), tmp_path / "in" / "lattice.gpkg")
    argv = ("--mode", "autocorr", "--geo", geo, "--var", "checker", "--weights", "rook", "--engine", "esda",
            "--perm", "199")
    code, rep = run_inprocess(tmp_path / "o1", *argv)
    moran = rep["data"]["moran"]
    assert code == 1 and moran["engine"] == "esda"
    assert moran["I"] == pytest.approx(-1.0, abs=1e-12) and moran["parity_abs_diff"] < 1e-10
    assert checks(rep)["AC-PATH"]["verdict"] == "SURVIVES"
    original = sa.moran_numpy

    def nudged(*args, **kwargs):
        out = original(*args, **kwargs)
        return {**out, "I": out["I"] + 1e-6}
    monkeypatch.setattr(sa, "moran_numpy", nudged)
    c = checks(run_inprocess(tmp_path / "o2", *argv)[1])["AC-PATH"]
    assert c["verdict"] == "WOUNDED" and c["value"] == pytest.approx(1e-6, rel=1e-6)
    monkeypatch.setattr(sa, "moran_numpy", original)

    def broken(*args, **kwargs):
        raise RuntimeError("planted esda failure")
    monkeypatch.setattr(esda.moran, "Moran", broken)
    code, rep = run_inprocess(tmp_path / "o3", *argv)
    c = checks(rep)["AC-PATH"]
    assert c["verdict"] == "UNVERIFIED-HERE" and "planted esda failure" in c["detail"]
    assert rep["data"]["moran"]["engine"] == "numpy" and checks(rep)["AC-01"]["verdict"] == "WOUNDED"
