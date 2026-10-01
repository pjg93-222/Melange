#!/usr/bin/env python3
"""Train/test contamination and target-leakage audit for a tabular split. Read-only: reads the train and
test tables; writes only its run folder.

Checks whether a held-out score can be trusted: exact duplicate rows across splits (hash of normalized
rows), entity and group overlap, temporal ordering with an optional embargo gap, a single-feature
target-leakage screen (AUC for a binary target, R^2 for a numeric one), feature availability after the
prediction time, and missingness-pattern shift between splits. A clean result is not proof of
independence, and a flag is a lead for a second reader, not proof of leakage (Kapoor & Narayanan 2023,
Patterns 4:100804; purging/embargo: Lopez de Prado 2018, Advances in Financial Machine Learning).

Usage:
  python scripts/leakage_audit.py --train train.csv --test test.csv [--id COL] [--group COL] [--time COL]
      [--embargo 90D] [--target COL] [--features c1,c2|all] [--available-at COL[,COL]] [--ignore c1,c2]

Verdict rules (the flags fix every threshold before the run). "Share rule": no affected test rows ->
SURVIVES; affected share <= --kill-share -> WOUNDED; above it -> KILLED.
  LEAK-01 duplicate rows: test rows identical to a train row on every shared column except --id and
          --ignore (numbers compared as float64, text trimmed); share rule.
  LEAK-02 entity overlap (--id) and LEAK-03 group overlap (--group): test rows whose key also occurs in
          train, keys compared after trimming case, a trailing '.0' and leading zeros; share rule.
  LEAK-04 temporal order (--time): test rows at or before the last training time; share rule.
  LEAK-05 embargo (--embargo, needs --time): test rows before last training time + embargo; share rule.
          Units Y, Q, M (months), W, D, H, min, S (20D, 90D, 6M, 1Y); a plain number for numeric --time.
  LEAK-06 target leakage (--target): a feature whose single-feature AUC (binary target, folded so direction
          does not matter) or R^2 (numeric target; max of Pearson and Spearman) reaches --leak-threshold in
          train or test, or whose missingness alone does -> WOUNDED (confirm it exists at prediction time);
          no feature scorable (all missing or constant) -> UNVERIFIED-HERE; else SURVIVES. Categorical
          features use out-of-fold target encoding; test uses train's fit.
  LEAK-07 availability (--available-at, needs --time): rows whose availability time is after the
          prediction time in either split; share rule over checked rows.
  LEAK-08 missingness shift: a shared column whose missing rate changes by >= --max-missing-shift
          (absolute) with a two-proportion z-test p < --alpha -> WOUNDED; else SURVIVES.

Exit codes: 0 all SURVIVES · 1 any WOUNDED/KILLED · 2 usage/input error · 3 UNVERIFIED-HERE present.
"""
from __future__ import annotations

import math
import pathlib
import re
import sys
import warnings

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (Check, Report, UsageError, base_parser, run_main, require_file, write_once, emit,
                     SURVIVES, WOUNDED, KILLED, UNVERIFIED)

import numpy as np
import pandas as pd
from scipy import stats

# The check list was informed by K-Dense-AI scientific-agent-skills
# exploratory-data-analysis/scripts/missingness_leakage_audit.py (MIT, (c) 2025 K-Dense Inc.).
# Ideas only; no code was copied.

SCRIPT = "leakage_audit"
SOURCE = f"quant-model-evaluation/{SCRIPT}"
NA_TOKEN = "\x00NA"
MIX = np.uint64(1099511628211)  # FNV-1 64-bit prime; mixes per-column hashes into one row hash
_DUR = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([A-Za-z]*)\s*$")
_UNITS = {"y": "years", "yr": "years", "year": "years", "years": "years", "q": "quarters",
          "m": "months", "mo": "months", "month": "months", "months": "months",
          "w": "weeks", "week": "weeks", "weeks": "weeks", "d": "days", "day": "days", "days": "days",
          "h": "hours", "hr": "hours", "hour": "hours", "hours": "hours",
          "min": "minutes", "minute": "minutes", "minutes": "minutes",
          "s": "seconds", "sec": "seconds", "second": "seconds", "seconds": "seconds"}


def build_parser():
    p = base_parser(__doc__)
    p.add_argument("--train", required=True, help="training split (CSV or .tsv)")
    p.add_argument("--test", required=True, help="test / holdout split (CSV or .tsv)")
    p.add_argument("--id", help="entity identifier column; an id present in both splits is an overlap")
    p.add_argument("--group", help="grouping unit that must not straddle splits (household, district, firm)")
    p.add_argument("--time", help="prediction-time column (dates or numbers); checks that test follows train")
    p.add_argument("--embargo", help="required gap after the last training time: 20D, 90D, 6M, 1Y, 12H, "
                                     "30min (M = months, min = minutes); a plain number for numeric --time")
    p.add_argument("--target", help="target column; runs the single-feature leakage screen")
    p.add_argument("--features", default="all", help="comma list of feature columns, or 'all' (default)")
    p.add_argument("--available-at", help="comma list of columns holding when each row's features became "
                                          "available; compared with --time, the prediction time")
    p.add_argument("--ignore", default="", help="comma list of columns left out of row hashing and the screen "
                                                "(row numbers, load stamps)")
    p.add_argument("--leak-threshold", type=float, default=0.98, help="single-feature AUC or R^2 that flags a feature")
    p.add_argument("--max-missing-shift", type=float, default=0.10, help="missing-rate change that flags a column")
    p.add_argument("--kill-share", type=float, default=0.05, help="affected test-row share above which -> KILLED")
    p.add_argument("--alpha", type=float, default=0.05, help="level of the missingness test (default 0.05)")
    p.add_argument("--folds", type=int, default=5, help="folds for out-of-fold target encoding (default 5)")
    return p


# ---- input helpers ----
def csv_list(text: str | None) -> list[str]:
    return [c.strip() for c in (text or "").split(",") if c.strip()]


def read_table(path: pathlib.Path, text_cols: list[str]) -> pd.DataFrame:
    sep = "\t" if path.suffix.lower() in (".tsv", ".tab") else ","
    try:
        header = pd.read_csv(path, sep=sep, nrows=0)
        dtype = {c: str for c in text_cols if c in header.columns}  # keep leading zeros in keys
        df = pd.read_csv(path, sep=sep, low_memory=False, dtype=dtype or None)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise UsageError(f"cannot read {path.name} as a table: {exc}") from None
    if df.empty:
        raise UsageError(f"{path.name} has no data rows")
    return df


def parse_embargo(text: str, numeric_time: bool):
    """Return (offset, label). Calendar units become DateOffset, clock units Timedelta."""
    m = _DUR.match(text or "")
    if not m:
        raise UsageError(f"--embargo {text!r} is not a duration like 20D, 90D, 6M, 1Y or a plain number")
    qty, unit = float(m.group(1)), m.group(2).lower()
    if not unit:
        if not numeric_time:
            raise UsageError("--embargo needs a unit (e.g. 20D) because --time holds dates")
        return qty, f"{qty:g} time units"
    if numeric_time:
        raise UsageError("--time is numeric; give --embargo as a plain number in the same units")
    kind = _UNITS.get(unit)
    if kind is None:
        raise UsageError(f"unknown --embargo unit {m.group(2)!r}; use Y, Q, M (months), W, D, H, min or S")
    if kind in ("years", "quarters", "months"):
        if not qty.is_integer():
            raise UsageError("calendar units (Y, Q, M) need a whole number")
        months = int(qty) * {"years": 12, "quarters": 3, "months": 1}[kind]
        return pd.DateOffset(months=months), f"{int(qty)} {kind}"
    return pd.Timedelta(**{kind: qty}), f"{qty:g} {kind}"


def parse_time(s: pd.Series, flag: str) -> tuple[pd.Series, bool]:
    """(values, is_numeric): numbers stay numbers, text is parsed as dates in UTC."""
    if pd.api.types.is_bool_dtype(s):
        raise UsageError(f"{flag} is boolean, not a time")
    if pd.api.types.is_numeric_dtype(s):
        return s.astype(float), True
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        t = pd.to_datetime(s, errors="coerce", utc=True)
        if (t.isna() & s.notna()).any():
            t2 = pd.to_datetime(s, errors="coerce", utc=True, format="mixed")
            if t2.notna().sum() > t.notna().sum():
                t = t2
    bad = t.isna() & s.notna()
    if bad.any():
        raise UsageError(f"{flag}: {int(bad.sum())} value(s) are not dates, e.g. {str(s[bad].iloc[0])!r}")
    return t, False


def fmt_t(v) -> str:
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d %H:%M:%S").replace(" 00:00:00", "")
    if isinstance(v, pd.Timedelta):
        return f"{v / pd.Timedelta(days=1):.6g} days"
    return f"{v:g}" if isinstance(v, (int, float)) else str(v)


# ---- canonical values and hashing ----
def _is_num(s: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s)


def canon_num(s: pd.Series) -> np.ndarray:
    v = pd.to_numeric(s, errors="coerce").to_numpy(dtype=float, na_value=np.nan) + 0.0  # folds -0.0 into 0.0
    v[np.isnan(v)] = np.nan  # one NaN bit pattern
    return v


def canon_text(s: pd.Series) -> np.ndarray:
    """Trimmed text; values that parse as numbers are written in float form so '1', '1.0' and 1 agree."""
    txt = s.astype("string").str.strip()
    num = pd.to_numeric(txt, errors="coerce")
    isnum = np.asarray(num.notna(), dtype=bool)
    out = np.array(txt.fillna(NA_TOKEN), dtype=object, copy=True)  # writable: pandas CoW can hand back a read-only view
    if isnum.any():
        out[isnum] = [repr(float(v)) for v in num.to_numpy(dtype=float, na_value=np.nan)[isnum] + 0.0]
    return out


def row_hashes(a: pd.DataFrame, b: pd.DataFrame, cols) -> tuple[np.ndarray, np.ndarray]:
    """64-bit content hash per row over `cols` (sorted, so column order does not matter)."""
    ha, hb = np.zeros(len(a), dtype=np.uint64), np.zeros(len(b), dtype=np.uint64)
    for c in sorted(cols, key=str):
        if _is_num(a[c]) and _is_num(b[c]):
            ca, cb = canon_num(a[c]), canon_num(b[c])
        else:
            ca, cb = canon_text(a[c]), canon_text(b[c])
        ha = (ha * MIX) ^ pd.util.hash_array(ca)
        hb = (hb * MIX) ^ pd.util.hash_array(cb)
    return ha, hb


def norm_keys(s: pd.Series) -> pd.Series:
    """Keys after trimming, upper-casing, dropping a trailing '.0' and leading zeros ('007' = '7' = '7.0')."""
    t = s.astype("string").str.strip().str.upper()
    t = t.str.replace(r"^(\d+)\.0+$", r"\1", regex=True).str.replace(r"^0+(?=\d)", "", regex=True)
    return t.mask(t == "")


def share_verdict(count: int, share: float, kill: float) -> str:
    if count == 0:
        return SURVIVES
    return KILLED if share > kill else WOUNDED


def safe_name(col: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(col))[:60]


# ---- single-feature leakage screen ----
def auc_rank(y: np.ndarray, s: np.ndarray) -> float:
    """Mann-Whitney AUC with midranks for ties; y in {0, 1}."""
    m = int(y.sum())
    n0 = len(y) - m
    if m == 0 or n0 == 0:
        return math.nan
    r = stats.rankdata(s)
    return float((r[y == 1].sum() - m * (m + 1) / 2) / (m * n0))


def fold(a: float) -> float:
    return max(a, 1 - a) if math.isfinite(a) else a


def f3(v: float) -> str:
    return f"{v:.3f}" if math.isfinite(v) else "n/a"


def r2_pair(x: np.ndarray, y: np.ndarray) -> float:
    """max(Pearson r^2, Spearman rho^2): linear or monotone single-feature fit."""
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return math.nan
    r = float(np.corrcoef(x, y)[0, 1])
    rho = float(stats.spearmanr(x, y)[0])
    return max(r * r, rho * rho)


def r2_fit(pred: np.ndarray, y: np.ndarray) -> float:
    sst = float(np.sum((y - y.mean()) ** 2))
    return math.nan if sst == 0 else 1.0 - float(np.sum((y - pred) ** 2)) / sst


def oof_encode(cats: np.ndarray, y: np.ndarray, folds: int, rng) -> np.ndarray:
    """Out-of-fold category means: each row is encoded by the other folds. Unseen levels get one constant (the
    overall mean): a per-fold fill would vary with each fold's own label mix and fake a (negative) signal."""
    fold_id = rng.permutation(len(y)) % folds
    out = np.empty(len(y))
    ys, cs, fill = pd.Series(y), pd.Series(cats), float(np.mean(y))
    for k in range(folds):
        fit = fold_id != k
        means = ys[fit].groupby(cs[fit].to_numpy()).mean()
        out[~fit] = cs[~fit].map(means).fillna(fill).to_numpy(dtype=float)
    return out


def target_vectors(tr_s: pd.Series, te_s: pd.Series | None):
    """(kind, y_train, y_test, positive label). kind: binary | numeric | multiclass | constant."""
    ctr = canon_text(tr_s)
    present = ctr != NA_TOKEN
    labels = sorted(set(ctr[present]))
    if len(labels) < 2:
        return "constant", None, None, None
    if len(labels) == 2:
        pos = labels[1]
        ytr = np.where(present, (ctr == pos).astype(float), np.nan)
        yte = None
        if te_s is not None:
            cte = canon_text(te_s)
            yte = np.where(np.isin(cte, labels), (cte == pos).astype(float), np.nan)
        return "binary", ytr, yte, pos
    if _is_num(tr_s):
        return "numeric", canon_num(tr_s), (canon_num(te_s) if te_s is not None else None), None
    return "multiclass", None, None, None


def screen_features(tr, te, feats, kind, ytr, yte, args, rng) -> list[dict]:
    okt = ~np.isnan(ytr)
    yk = ytr[okt]
    rows = []
    for f in feats:
        ftr = tr[f]
        fte = te[f] if (yte is not None and f in te.columns) else None
        numeric = _is_num(ftr) and (fte is None or _is_num(fte))
        row = {"feature": str(f), "type": "numeric" if numeric else "categorical",
               "train": math.nan, "train_missing": math.nan, "test": math.nan}
        miss = ftr.isna().to_numpy()[okt]
        levels = ftr[okt].nunique(dropna=True)
        if levels < 2 and not 0 < miss.sum() < len(miss):  # nothing varies, so there is nothing to score
            rows.append({**row, "max": math.nan, "flagged": False,
                         "unscorable": "all missing" if levels == 0 else "constant"})
            continue
        raw = math.nan
        if numeric:
            x = canon_num(ftr)[okt]
            sel = ~np.isnan(x)
            raw = auc_rank(yk[sel], x[sel]) if kind == "binary" else math.nan
            row["train"] = fold(raw) if kind == "binary" else r2_pair(x[sel], yk[sel])
        else:
            cats = canon_text(ftr)[okt]
            enc = oof_encode(cats, yk, args.folds, rng)
            row["train"] = auc_rank(yk, enc) if kind == "binary" else r2_fit(enc, yk)
        if 0 < miss.sum() < len(miss):  # missingness alone as the signal
            ind = miss.astype(float)
            row["train_missing"] = fold(auc_rank(yk, ind)) if kind == "binary" else r2_pair(ind, yk)
        if fte is not None:
            okv = ~np.isnan(yte)
            yv = yte[okv]
            if numeric:
                xv = canon_num(fte)[okv]
                sel = ~np.isnan(xv)
                a = auc_rank(yv[sel], xv[sel]) if kind == "binary" else r2_pair(xv[sel], yv[sel])
                row["test"] = 1 - a if kind == "binary" and math.isfinite(raw) and raw < 0.5 else a  # train's direction
            else:
                means = pd.Series(yk).groupby(cats).mean()  # encoding fitted on train only
                ev = pd.Series(canon_text(fte)[okv]).map(means).fillna(float(yk.mean())).to_numpy(dtype=float)
                row["test"] = auc_rank(yv, ev) if kind == "binary" else r2_fit(ev, yv)
        scores = [v for v in (row["train"], row["train_missing"], row["test"]) if math.isfinite(v)]
        row["max"] = max(scores) if scores else math.nan
        row["flagged"] = bool(scores) and max(scores) >= args.leak_threshold
        if not scores:
            row["unscorable"] = "no finite score (too few usable rows)"
        rows.append(row)
    return rows


def two_prop_p(k1: int, n1: int, k2: int, n2: int) -> float:
    pooled = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0 if k1 / n1 == k2 / n2 else 0.0
    return float(2 * stats.norm.sf(abs(k2 / n2 - k1 / n1) / se))


def pattern_freq(df: pd.DataFrame) -> dict:
    packed = np.packbits(df.isna().to_numpy(), axis=1)
    keys = packed.view(np.dtype((np.void, packed.shape[1]))).ravel()
    uniq, counts = np.unique(keys, return_counts=True)
    return {u.tobytes(): c / len(df) for u, c in zip(uniq, counts)}


# ---- main ----
def validate(args) -> None:
    if not 0.5 < args.leak_threshold <= 1:
        raise UsageError("--leak-threshold must be in (0.5, 1]")
    if not 0 < args.max_missing_shift <= 1 or not 0 <= args.kill_share < 1:
        raise UsageError("--max-missing-shift must be in (0, 1] and --kill-share in [0, 1)")
    if not 0 < args.alpha < 1 or args.folds < 2:
        raise UsageError("--alpha must be in (0, 1) and --folds >= 2")
    if (args.embargo or args.available_at) and not args.time:
        raise UsageError("--embargo and --available-at need --time (the prediction time)")


def main(args, report: Report, run_dir: pathlib.Path, run_id: str) -> None:
    validate(args)
    tr_path, te_path = require_file(args.train, "--train"), require_file(args.test, "--test")
    report.add_input(tr_path)
    report.add_input(te_path)
    report.note_packages(["numpy", "pandas", "scipy"])
    keys = [c for c in (args.id, args.group) if c]
    tr, te = read_table(tr_path, keys), read_table(te_path, keys)
    n_tr, n_te = len(tr), len(te)
    for flag, col in (("--id", args.id), ("--group", args.group), ("--time", args.time)):
        if col and (col not in tr.columns or col not in te.columns):
            raise UsageError(f"{flag} column {col!r} must exist in both --train and --test")
    if args.target and args.target not in tr.columns:
        raise UsageError(f"--target column {args.target!r} not in --train")
    avail = csv_list(args.available_at)
    for c in avail:
        if c not in tr.columns and c not in te.columns:
            raise UsageError(f"--available-at column {c!r} is in neither split")
    ignore = set(csv_list(args.ignore)) | {c for c in tr.columns.union(te.columns) if str(c).startswith("Unnamed:")}
    common = [c for c in tr.columns if c in te.columns]
    rng = np.random.default_rng(args.seed)
    ks = args.kill_share
    tail = f"WOUNDED while at most {ks:g} of test rows are affected, KILLED above"
    c01 = f"no test row duplicating a train row; {tail}"
    only_tr = [str(c) for c in tr.columns if c not in te.columns]
    only_te = [str(c) for c in te.columns if c not in tr.columns]
    mixed = [str(c) for c in common if _is_num(tr[c]) != _is_num(te[c])]

    # LEAK-01 exact duplicate rows across splits
    hcols = [c for c in common if c != args.id and c not in ignore]
    if hcols:
        h_tr, h_te = row_hashes(tr, te, hcols)
        dup = np.isin(h_te, h_tr)
        n_dup, share = int(dup.sum()), float(dup.mean())
        self_dup = 1 - len(np.unique(h_tr)) / n_tr
        det = (f"{n_dup} of {n_te} test rows ({share:.1%}) repeat a train row on {len(hcols)} shared columns; "
               f"train repeats itself at {self_dup:.1%}")
        if args.target and args.target in hcols and len(hcols) > 1:
            fcols = [c for c in hcols if c != args.target]
            f_tr, f_te = row_hashes(tr, te, fcols)
            fdup = np.isin(f_te, f_tr)
            det += (f"; {int(fdup.sum())} test rows share every non-target value with a train row, "
                    f"{int((fdup & ~dup).sum())} of them differ in the target")
        if n_dup:
            first = pd.Series(np.arange(n_tr)).groupby(h_tr).first()
            pos = np.nonzero(dup)[0]
            write_once(run_dir / "duplicate_rows.csv", pd.DataFrame(
                {"test_row_index": pos, "train_row_index": first.loc[h_te[pos]].to_numpy()}
            ).to_csv(index=False, lineterminator="\n"))
            det += "; row pairs in duplicate_rows.csv (0-based data rows)"
        report.add(Check("LEAK-01", "No test row duplicates a train row", share_verdict(n_dup, share, ks),
                         criterion=c01, value=n_dup, detail=det))
        report.data["duplicates"] = {"columns": [str(c) for c in hcols], "test_rows": n_dup, "share": share,
                                     "train_self_duplicate_share": self_dup}
    else:
        report.add(Check("LEAK-01", "No test row duplicates a train row", UNVERIFIED, criterion=c01,
                         detail="the splits share no comparable columns"))

    # LEAK-02 / LEAK-03 entity and group overlap
    for cid, what, col in (("LEAK-02", "entity", args.id), ("LEAK-03", "group", args.group)):
        if not col:
            continue
        a, b = norm_keys(tr[col]), norm_keys(te[col])
        raw_shared = set(tr[col].astype("string").str.strip().dropna()) & set(te[col].astype("string").str.strip().dropna())
        shared = sorted(set(a.dropna()) & set(b.dropna()))
        hit = np.asarray(b.isin(shared), dtype=bool)
        rows, share = int(hit.sum()), float(hit.mean())
        det = (f"{len(shared)} of {b.nunique()} test {what} keys also occur in train; {rows} test rows "
               f"({share:.1%}) affected")
        if len(shared) > len(raw_shared):
            det += f"; {len(shared) - len(raw_shared)} match only after trimming case, '.0' or leading zeros"
        nulls = int(tr[col].isna().sum() + te[col].isna().sum())
        if nulls:
            det += f"; {nulls} row(s) have no {what} key"
        if shared:
            examples = pd.unique(te[col][hit].astype("string").str.strip())[:3]
            det += f"; e.g. {', '.join(map(str, examples))}"
            va, vb = a.value_counts(), b.value_counts()
            write_once(run_dir / f"overlap_{safe_name(col)}.csv", pd.DataFrame(
                {"key": shared, "rows_train": va.reindex(shared).to_numpy(), "rows_test": vb.reindex(shared).to_numpy()}
            ).to_csv(index=False, lineterminator="\n"))
        report.add(Check(cid, f"No {what} ({col}) appears in both splits", share_verdict(len(shared), share, ks),
                         criterion=f"no test {what} key found in train; {tail}", value=len(shared), detail=det))
        report.data[f"{what}_overlap"] = {"column": col, "shared_keys": len(shared), "test_rows": rows, "share": share}

    # LEAK-04 / LEAK-05 temporal order and embargo
    t_tr = t_te = None
    if args.time:
        t_tr, num_tr = parse_time(tr[args.time], f"--time {args.time!r} in --train")
        t_te, num_te = parse_time(te[args.time], f"--time {args.time!r} in --test")
        if num_tr != num_te:
            raise UsageError("--time is numeric in one split and dates in the other")
        if t_tr.notna().sum() == 0 or t_te.notna().sum() == 0:
            raise UsageError("--time has no values in one of the splits")
        tr_max, te_min = t_tr.max(), t_te.min()
        valid = t_te.notna()
        early = (t_te <= tr_max) & valid
        n_early, share = int(early.sum()), float(early.sum() / valid.sum())
        report.add(Check("LEAK-04", "Test period follows the training period", share_verdict(n_early, share, ks),
                         criterion=f"no test row at or before the last training time; {tail}", value=n_early,
                         detail=f"train {fmt_t(t_tr.min())} to {fmt_t(tr_max)}; test {fmt_t(te_min)} to "
                                f"{fmt_t(t_te.max())}; gap {fmt_t(te_min - tr_max)}; {n_early} test rows ({share:.1%}) at "
                                f"or before the last training time"
                                + (f"; {int((~valid).sum())} test rows lack a time" if (~valid).any() else "")))
        report.data["time"] = {"train_min": fmt_t(t_tr.min()), "train_max": fmt_t(tr_max), "test_min": fmt_t(te_min),
                               "test_max": fmt_t(t_te.max()), "test_rows_not_after_train": n_early}
        if args.embargo:
            emb, label = parse_embargo(args.embargo, num_tr)
            boundary = tr_max + emb
            inside = (t_te < boundary) & valid
            n_in, share_in = int(inside.sum()), float(inside.sum() / valid.sum())
            report.add(Check("LEAK-05", f"Embargo gap of {label} after training", share_verdict(n_in, share_in, ks),
                             criterion=f"no test row before the last training time + embargo; {tail}", value=n_in,
                             detail=f"first allowed test time {fmt_t(boundary)}; first test time {fmt_t(te_min)}; "
                                    f"{n_in} test rows ({share_in:.1%}) fall inside the embargo"))
            report.data["embargo"] = {"embargo": label, "boundary": fmt_t(boundary), "test_rows_inside": n_in}

    # LEAK-06 single-feature target-leakage screen
    screened = None
    if args.target:
        te_target = te[args.target] if args.target in te.columns else None
        kind, ytr, yte, pos = target_vectors(tr[args.target], te_target)
        excluded = {args.target, args.id, args.group, args.time, *avail} | ignore
        if args.features.strip().lower() == "all":
            feats = [c for c in tr.columns if c not in excluded]
        else:
            feats = csv_list(args.features)
            absent = [c for c in feats if c not in tr.columns]
            if absent:
                raise UsageError(f"--features not in --train: {absent}")
        metric = "AUC" if kind == "binary" else "R^2"
        crit = (f"every feature's single-feature {metric} (train, test, and missingness alone) < "
                f"{args.leak_threshold:g}; no scorable feature -> UNVERIFIED-HERE")
        if kind in ("constant", "multiclass"):
            report.add(Check("LEAK-06", "No single feature nearly determines the target", UNVERIFIED, criterion=crit,
                             detail=("the target has a single value in train" if kind == "constant" else
                                     "multiclass text target: the screen handles binary and numeric targets")))
        elif not feats:
            report.add(Check("LEAK-06", "No single feature nearly determines the target", UNVERIFIED, criterion=crit,
                             detail="no feature columns left after exclusions"))
        else:
            emit("stage", "running", f"single-feature screen over {len(feats)} features", run_id=run_id, source=SOURCE)
            screened = screen_features(tr, te, feats, kind, ytr, yte, args, rng)
            flagged = sorted((r for r in screened if r["flagged"]), key=lambda r: -r["max"])
            unscorable = [f"{r['feature']} ({r['unscorable']})" for r in screened if r.get("unscorable")]
            best = max((r["max"] for r in screened if math.isfinite(r["max"])), default=math.nan)
            top = sorted((r for r in screened if math.isfinite(r["max"])), key=lambda r: -r["max"])[:5]
            v6 = WOUNDED if flagged else (UNVERIFIED if len(unscorable) == len(screened) else SURVIVES)
            det = (("no feature could be scored, so nothing was tested; " if v6 == UNVERIFIED else "")
                   + f"{len(flagged)} of {len(screened) - len(unscorable)} scored features flagged ({kind} target"
                   + (f", positive = {pos}" if kind == "binary" else "") + "); top: "
                   + (", ".join(f"{r['feature']} {r['max']:.3f}" for r in top) or "none"))
            if unscorable:
                det += f"; unscorable ({len(unscorable)}): {', '.join(unscorable[:8])}{' ...' if len(unscorable) > 8 else ''}"
            if te_target is None:
                det += "; test split has no target column, so only train was screened"
            if flagged:
                det += "; confirm each flagged feature exists at prediction time and is not built from the target"
            report.add(Check("LEAK-06", "No single feature nearly determines the target", v6, criterion=crit,
                             value=round(best, 6) if math.isfinite(best) else None, detail=det))
            write_once(run_dir / "feature_screen.csv",
                       pd.DataFrame(screened).to_csv(index=False, lineterminator="\n"))
            report.data["feature_screen"] = {"target_kind": kind, "metric": metric, "rows": screened}

    # LEAK-07 availability after prediction time
    if avail:
        per, viol_all, checked_all = [], 0, 0
        for c in avail:
            for split, df, tp in (("train", tr, t_tr), ("test", te, t_te)):
                if c not in df.columns:
                    per.append(f"{c}/{split}: absent")
                    continue
                at, num_a = parse_time(df[c], f"--available-at {c!r} in {split}")
                if num_a != pd.api.types.is_numeric_dtype(tp):
                    raise UsageError(f"--available-at {c!r} and --time must both be dates or both numbers")
                both = at.notna() & tp.notna()
                late = int(((at > tp) & both).sum())
                viol_all, checked_all = viol_all + late, checked_all + int(both.sum())
                per.append(f"{c}/{split}: {late} late of {int(both.sum())}"
                           + (f", {int(at.isna().sum())} unknown" if at.isna().any() else ""))
        crit = f"no row whose availability time is after its prediction time ({args.time}); share of checked rows: {tail}"
        if checked_all == 0:
            report.add(Check("LEAK-07", "Features available at prediction time", UNVERIFIED, criterion=crit,
                             detail="no row has both an availability time and a prediction time; " + "; ".join(per)))
        else:
            sh = viol_all / checked_all
            report.add(Check("LEAK-07", "Features available at prediction time", share_verdict(viol_all, sh, ks),
                             criterion=crit, value=viol_all, detail=f"{viol_all} of {checked_all} rows ({sh:.1%}) "
                                                                    "late; " + "; ".join(per)))
        report.data["availability"] = {"columns": avail, "late_rows": viol_all, "checked_rows": checked_all}

    # LEAK-08 missingness-pattern shift
    mcols = [c for c in common if c != args.target and c not in ignore]
    mrows = []
    for c in mcols:
        k1, k2 = int(tr[c].isna().sum()), int(te[c].isna().sum())
        r1, r2 = k1 / n_tr, k2 / n_te
        pv = two_prop_p(k1, n_tr, k2, n_te)
        mrows.append({"column": str(c), "missing_train": r1, "missing_test": r2, "diff": r2 - r1, "p": pv,
                      "flagged": abs(r2 - r1) >= args.max_missing_shift and pv < args.alpha})
    shifted = [r for r in mrows if r["flagged"]]
    patt = [c for c in mcols if tr[c].isna().any() or te[c].isna().any()]
    tvd = 0.0
    if patt:
        fa, fb = pattern_freq(tr[patt]), pattern_freq(te[patt])
        tvd = 0.5 * sum(abs(fa.get(k, 0.0) - fb.get(k, 0.0)) for k in set(fa) | set(fb))
    report.add(Check("LEAK-08", "Missingness pattern stable across splits", WOUNDED if shifted else SURVIVES,
                     criterion=f"no column with |missing-rate change| >= {args.max_missing_shift:g} and two-proportion p < {args.alpha:g}",
                     value=len(shifted),
                     detail=(", ".join(f"{r['column']} {r['missing_train']:.1%} -> {r['missing_test']:.1%}" for r in shifted[:8])
                             or "no column shifted") + f"; {len(patt)} columns have missing values; pattern "
                                                        f"total-variation distance {tvd:.3f}"))
    if mrows:
        write_once(run_dir / "missingness.csv", pd.DataFrame(mrows).to_csv(index=False, lineterminator="\n"))
    report.data["missingness"] = {"flagged": shifted, "pattern_tvd": tvd}

    # Sections
    ran = {c.id for c in report.checks}
    skipped = [f"{cid} needs {flag}" for cid, flag in (("LEAK-02", "--id"), ("LEAK-03", "--group"),
                                                       ("LEAK-04", "--time"), ("LEAK-05", "--embargo"),
                                                       ("LEAK-06", "--target"), ("LEAK-07", "--available-at"))
               if cid not in ran]
    report.section("Trend", f"{n_tr} train rows, {n_te} test rows, {len(common)} shared columns. Contamination "
                            f"checks run: {', '.join(sorted(ran))}." + (" Not run: " + "; ".join(skipped) + "."
                                                                       if skipped else ""))
    report.section("Schema", "\n".join([
        f"- only in train: {', '.join(only_tr[:20]) or 'none'}", f"- only in test: {', '.join(only_te[:20]) or 'none'}",
        f"- numeric in one split, text in the other: {', '.join(mixed[:20]) or 'none'}",
        f"- ignored: {', '.join(sorted(map(str, ignore))) or 'none'}"]))
    if screened:
        top = sorted((r for r in screened if math.isfinite(r["max"])), key=lambda r: -r["max"])[:15]
        lines = ["| feature | type | train | missingness | test | flagged |", "|---|---|---|---|---|---|"]
        lines += [f"| {r['feature']} | {r['type']} | {f3(r['train'])} | {f3(r['train_missing'])} | {f3(r['test'])} | "
                  f"{'yes' if r['flagged'] else ''} |" for r in top]
        report.section("Single-feature screen (top 15)", "\n".join(lines))
    report.section("Notes", "- Row hashes are 64-bit (collisions negligible below ~10^8 rows).\n- A flagged feature is a "
                   "lead, not proof: confirm timing and construction.\n- Only the two files are seen: preprocessing fitted "
                   "on all rows (scaling, imputation, selection, target encoding) must be checked in the pipeline code.")
    report.data.update({"n_train": n_tr, "n_test": n_te, "shared_columns": len(common),
                        "only_train": only_tr, "only_test": only_te, "ignored": sorted(map(str, ignore))})


if __name__ == "__main__":
    sys.exit(run_main(SCRIPT, main, build_parser()))
