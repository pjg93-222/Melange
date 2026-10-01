#!/usr/bin/env python3
"""Mutation check: can a data check actually fail? (vacuous-check detector). Read-only toward --input: the
command only ever sees copies. Writes only its run folder: report.md, report.json, mutants.csv, and under
mutants/ the mutated copies plus each run's stdout.txt and stderr.txt.

*** WARNING: THIS SCRIPT EXECUTES THE COMMAND YOU GIVE IT, once per mutant plus two control runs, with your
*** user rights, in the current directory. Point it only at check commands you have read and approved. In
*** repositories where importing a module runs it (import == execution), an unreviewed command can change
*** real data or state. The command gets the path of a copy (always named input.csv or input.json inside
*** the run folder), never your original file. It is started with shell=False, but on Windows .bat and .cmd
*** files always run through cmd.exe, which re-parses the arguments: such commands (and .ps1, cmd,
*** powershell, pwsh) are refused unless you pass --allow-shell-script.

How it works
  1. Baseline: --input is copied byte for byte into the run folder and the command runs on the copy. It must
     pass (exit code in --pass-codes), or nothing can be concluded (UNVERIFIED-HERE).
  2. Identity control: the input is parsed and re-serialized without changes. It must pass too; otherwise the
     check reacts to formatting alone and kills would mean nothing (UNVERIFIED-HERE).
  3. Mutants: each mutation is written as a new file and the command runs on it. KILLED = the command failed
     (exit code not in --pass-codes); SURVIVED = it passed. A mutant whose parsed values equal the control's
     (for example flip_sign turning "0" into "-0") is EQUIVALENT: listed, not run, not counted. Mutants named
     in --expect-survive that pass are EXPECTED-SURVIVOR: listed, not counted. TIMEOUTs are listed, not counted.
  Each run gets --timeout seconds; on timeout the whole process tree is killed (Windows: taskkill /T /F on a
  new process group; elsewhere: the process group of a new session), so a check cannot outlive its budget.

Auto mutations (--auto, the default)
  CSV, per numeric column (or per --columns): shuffle_col, sort_col, flip_sign, constant (the median), nan
  (10% of rows set to NaN); once: drop_rows (10%), dup_rows (10%); swap of each adjacent pair of columns.
  JSON, per numeric array found anywhere: reverse, swap_adjacent (a monotone series becomes non-monotone),
  scale (x10), zero; plus delete_key for the key holding the array.
Custom mutations (--mutations spec.json), a JSON list, for example
  [{"op": "flip_sign", "column": "amount"}, {"op": "swap", "columns": ["a", "b"]}, {"op": "drop_rows", "frac": 0.2},
   {"op": "swap_adjacent", "path": "/series/values", "index": 3}, {"op": "scale", "path": "/w", "factor": 10},
   {"op": "delete_key", "path": "/meta/limit"}]      (JSON paths are JSON pointers, RFC 6901)
--expect-survive NAME[,NAME]: mutants the check cannot catch by design (for example drop_rows,dup_rows for a
  row-wise identity check). NAME is an op ("drop_rows"), op:target ("flip_sign:id", "swap:a<->b",
  "reverse:/values") or a mutant id ("017_drop_rows"); every NAME must match a mutant.

Verdict (unexpected survivors only): no counted mutant killed -> KILLED ("vacuous check"); some survive ->
WOUNDED, listing the blind spots; all killed -> SURVIVES.

Usage (--cmd goes last, or end the command with a lone --):
  python scripts/mutation_check.py --input data.csv --cmd python checks/validate.py --file '{input}'
  python scripts/mutation_check.py --input s.json --mutations spec.json --timeout 60 --cmd Rscript check.R '{input}' --
  Quote the placeholder as '{input}': PowerShell parses a bare {input} as a script block (bash accepts both).

Exit codes: 0 all SURVIVES · 1 any WOUNDED/KILLED · 2 usage/input error · 3 UNVERIFIED-HERE present.
"""
from __future__ import annotations

import argparse
import copy
import csv
import io
import json
import math
import os
import pathlib
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (Check, Report, UsageError, base_parser, run_main, require_file, write_once,  # noqa: E402
                     emit, sha256_file, SURVIVES, WOUNDED, KILLED, UNVERIFIED)

import numpy as np  # noqa: E402

SCRIPT = "mutation_check"
SRC = f"quant-model-evaluation/{SCRIPT}"
CSV_OPS = ("shuffle_col", "sort_col", "flip_sign", "constant", "nan", "drop_rows", "dup_rows", "swap")
JSON_OPS = ("reverse", "swap_adjacent", "scale", "zero", "delete_key")
SHELL_SUFFIXES = (".bat", ".cmd", ".ps1")
SHELL_PROGRAMS = {"cmd", "cmd.exe", "powershell", "powershell.exe", "pwsh", "pwsh.exe"}
CMD_META = set('&|^<>()%!"')
BOM = "\ufeff"


def build_parser():
    p = base_parser(__doc__)
    p.add_argument("--input", required=True, help=".csv or .json file the check reads (never modified)")
    p.add_argument("--cmd", nargs=argparse.REMAINDER, metavar="TOKENS",
                   help="WARNING: EXECUTED once per mutant. The check command; must contain {input}; put it last "
                        "or end it with a lone --")
    how = p.add_mutually_exclusive_group()
    how.add_argument("--auto", action="store_true", help="built-in mutations (the default)")
    how.add_argument("--mutations", help="JSON list of custom mutations")
    p.add_argument("--columns", help="CSV: only mutate these columns (default: every numeric column)")
    p.add_argument("--delimiter", default=",", help="CSV delimiter (default ,)")
    p.add_argument("--pass-codes", default="0", help="exit codes that mean the check passed (default 0)")
    p.add_argument("--timeout", type=float, default=120.0,
                   help="seconds per command run; the whole process tree is killed after it (default 120)")
    p.add_argument("--max-mutants", type=int, default=200, help="run at most this many mutants (default 200)")
    p.add_argument("--expect-survive", action="append", default=[], metavar="NAME[,NAME]",
                   help="mutants the check cannot catch by design: op, op:target or mutant id (repeatable)")
    p.add_argument("--allow-shell-script", action="store_true",
                   help="DANGEROUS: allow a .bat/.cmd/.ps1 (or cmd/powershell/pwsh) command, which re-parses its "
                        "arguments through a shell")
    return p


def split_cmd(argv):
    """Take '--cmd TOKENS... [--]' out of argv: argparse cannot hold a free-form command mid-line."""
    if "--cmd" not in argv:
        return list(argv), None
    i = argv.index("--cmd")
    rest = argv[i + 1:]
    if "--" in rest:
        j = rest.index("--")
        return argv[:i] + rest[j + 1:], rest[:j]
    return argv[:i], rest


# --------------------------------------------------------------------------- #
# Documents: parse, serialize, mutate, compare by value
# --------------------------------------------------------------------------- #
def _num(s):
    try:
        v = float(s)
    except (TypeError, ValueError):
        return None
    return v


def _cell_value(s):
    """A cell as the value a check would read: numbers compare by value ("0" == "-0", "NaN" == "-NaN")."""
    v = _num(s.strip())
    if v is None:
        return ("s", s.strip())
    return ("n", "nan") if math.isnan(v) else ("n", v + 0.0)


class CsvDoc:
    def __init__(self, text, delim):
        self.delim, self.eol = delim, "\r\n" if "\r\n" in text else "\n"
        self.bom = text.startswith(BOM)  # utf-8-sig: parse without the BOM, write it back unchanged
        rows = self._rows(text)
        if len(rows) < 2:
            raise UsageError("CSV --input needs a header and at least one data row")
        self.header, self.body = rows[0], rows[1:]
        if any(len(r) != len(self.header) for r in self.body):
            raise UsageError("CSV --input has rows with a different number of fields than the header")
        self.numeric = [c for j, c in enumerate(self.header)
                        if all(_num(r[j]) is not None for r in self.body if r[j] != "")
                        and any(r[j] != "" for r in self.body)]

    def _rows(self, text):
        text = text[1:] if text.startswith(BOM) else text
        return [r for r in csv.reader(io.StringIO(text, newline=""), delimiter=self.delim) if r]

    def canon(self, text):
        return [[_cell_value(c) for c in r] for r in self._rows(text)]

    def dump(self, body=None):
        buf = io.StringIO(newline="")
        w = csv.writer(buf, delimiter=self.delim, lineterminator=self.eol)
        w.writerow(self.header)
        w.writerows(self.body if body is None else body)
        return (BOM if self.bom else "") + buf.getvalue()

    def auto(self, only):
        cols = only or self.numeric
        muts = [{"op": op, "column": c} for c in cols for op in ("shuffle_col", "sort_col", "flip_sign", "constant", "nan")]
        muts += [{"op": "drop_rows"}, {"op": "dup_rows"}]
        return muts + [{"op": "swap", "columns": [a, b]} for a, b in zip(cols, cols[1:])]

    def apply(self, m, rng):
        op, body, n = m["op"], [list(r) for r in self.body], len(self.body)
        if op not in CSV_OPS:
            raise UsageError(f"unknown CSV mutation op {op!r}; use one of {CSV_OPS}")
        try:
            k = max(1, int(round(float(m.get("frac", 0.1)) * n)))
        except (TypeError, ValueError):
            raise UsageError(f"mutation {op!r}: frac must be a number") from None
        if op in ("drop_rows", "dup_rows"):
            pick = set(rng.choice(n, size=min(k, n - 1 if op == "drop_rows" else n), replace=False).tolist())
            if op == "drop_rows":
                return self.dump([r for i, r in enumerate(body) if i not in pick])
            return self.dump([x for i, r in enumerate(body) for x in ([r, list(r)] if i in pick else [r])])
        if op == "swap":
            pair = m.get("columns")
            if not (isinstance(pair, list) and len(pair) == 2 and pair[0] != pair[1]):
                raise UsageError("swap needs \"columns\": [two different column names]")
            a, b = self._col(pair[0]), self._col(pair[1])
            for r in body:
                r[a], r[b] = r[b], r[a]
            return self.dump(body)
        j = self._col(m.get("column"))
        vals = [r[j] for r in body]
        if op == "shuffle_col":
            for _ in range(20):  # make sure the order really changes when it can
                perm = rng.permutation(n)
                if [vals[i] for i in perm] != vals:
                    break
            new = [vals[i] for i in perm]
        elif op == "sort_col":
            new = sorted(vals, key=lambda s: (_num(s) is None, _num(s) if _num(s) is not None else 0.0))
        elif op == "flip_sign":
            new = [s if _num(s) is None else (s[1:] if s.startswith("-") else "-" + s.lstrip("+")) for s in vals]
        elif op == "constant":
            good = sorted((s for s in vals if _num(s) is not None), key=_num)
            new = [str(m["value"]) if "value" in m else (good[len(good) // 2] if good else "0")] * n
        else:  # nan
            pick = set(rng.choice(n, size=min(k, n), replace=False).tolist())
            new = ["NaN" if i in pick else s for i, s in enumerate(vals)]
        for r, s in zip(body, new):
            r[j] = s
        return self.dump(body)

    def _col(self, name):
        if name not in self.header:
            raise UsageError(f"mutation names column {name!r}, not in the CSV header {self.header}")
        return self.header.index(name)


class JsonDoc:
    def __init__(self, text):
        self.bom = text.startswith(BOM)
        try:
            self.obj = json.loads(text[1:] if self.bom else text)
        except ValueError as exc:
            raise UsageError(f"JSON --input does not parse: {exc}") from None

    def canon(self, text):
        return json.loads(text[1:] if text.startswith(BOM) else text)  # Python equality: 0 == -0 == 0.0

    def dump(self, obj=None):
        return (BOM if self.bom else "") + json.dumps(self.obj if obj is None else obj, indent=2,
                                                      ensure_ascii=False) + "\n"

    @staticmethod
    def _is_num(x):
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def arrays(self, node=None, path=()):
        node = self.obj if node is None else node
        if isinstance(node, list) and len(node) >= 2 and all(self._is_num(x) for x in node):
            yield path
        elif isinstance(node, dict):
            for key, val in node.items():
                yield from self.arrays(val, path + (key,))
        elif isinstance(node, list):
            for i, val in enumerate(node):
                yield from self.arrays(val, path + (i,))

    def auto(self, only):
        muts = []
        for path in self.arrays():
            ptr = "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in path)
            muts += [{"op": op, "path": ptr} for op in ("reverse", "swap_adjacent", "scale", "zero")]
            if path:
                muts.append({"op": "delete_key", "path": ptr})
        return muts

    def _resolve(self, obj, ptr):
        if not isinstance(ptr, str) or not ptr.startswith("/"):
            raise UsageError(f"JSON mutation path must be a JSON pointer like /a/b/0, got {ptr!r}")
        parent, key = None, None
        node = obj
        for tok in ptr[1:].split("/"):
            tok = tok.replace("~1", "/").replace("~0", "~")
            parent = node
            try:
                key = int(tok) if isinstance(node, list) else tok
                node = node[key]
            except (KeyError, IndexError, ValueError, TypeError):
                raise UsageError(f"JSON path {ptr!r} does not exist in --input") from None
        return parent, key, node

    def apply(self, m, rng):
        obj = copy.deepcopy(self.obj)
        op = m["op"]
        if op not in JSON_OPS:
            raise UsageError(f"unknown JSON mutation op {op!r}; use one of {JSON_OPS}")
        parent, key, node = self._resolve(obj, m.get("path"))
        if op == "delete_key":
            del parent[key]
            return self.dump(obj)
        if not (isinstance(node, list) and node and all(self._is_num(x) for x in node)):
            raise UsageError(f"JSON op {op!r} needs a numeric array at {m.get('path')!r}")
        if op == "reverse":
            node.reverse()
        elif op == "swap_adjacent":
            i = m.get("index")
            if i is None:  # first adjacent pair whose swap changes the series
                i = next((t for t in range(len(node) - 1) if node[t] != node[t + 1]), 0)
            if not 0 <= int(i) < len(node) - 1:
                raise UsageError(f"swap_adjacent index {i} out of range")
            node[i], node[i + 1] = node[i + 1], node[i]
        elif op == "scale":
            f = m.get("factor", 10)
            node[:] = [x * f for x in node]
        else:  # zero
            node[:] = [0.0 if isinstance(x, float) else 0 for x in node]
        return self.dump(obj)


def _label(m):
    cols = m.get("columns")
    if isinstance(cols, list):
        return "<->".join(str(c) for c in cols)
    return m.get("column") or m.get("path") or "(rows)"


def _names(tag, m):
    """The names --expect-survive may use for a mutant: op, op:target, or its id."""
    return {m["op"], f"{m['op']}:{_label(m)}", tag}


def _row_names(row):
    return {row["op"], f"{row['op']}:{row['target']}", row["id"]}


# --------------------------------------------------------------------------- #
# Running the check
# --------------------------------------------------------------------------- #
def _shell_like(argv0):
    name = pathlib.PureWindowsPath(argv0).name.lower()  # handles / and \ separators
    return name.endswith(SHELL_SUFFIXES) or name in SHELL_PROGRAMS


def _kill_tree(proc):
    """Timeout: kill the command and every process it started, not only the direct child (CR-03)."""
    if os.name == "nt":
        exe = pathlib.Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"
        try:
            subprocess.run([str(exe) if exe.is_file() else "taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           shell=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)  # the child leads its own session, so pgid == pid
        except OSError:
            pass
    try:
        proc.kill()
        proc.wait(timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _tail(path):
    with open(path, "rb") as fh:
        fh.seek(max(0, path.stat().st_size - 2000))
        text = fh.read().decode("utf-8", errors="replace").strip()
    return text[-300:].replace("\r", "").replace("\n", " | ")


def run_cmd(tokens, path, timeout, folder):
    """Run the check on one copy. Output goes to files in the mutant folder, never to pipes: a grandchild
    holding a pipe open could otherwise stall the run past its timeout."""
    argv = [t.replace("{input}", str(path)) for t in tokens]
    group = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    t0 = time.perf_counter()
    with open(folder / "stdout.txt", "xb") as out, open(folder / "stderr.txt", "xb") as err:
        try:
            proc = subprocess.Popen(argv, shell=False, stdin=subprocess.DEVNULL, stdout=out, stderr=err, **group)
        except OSError as exc:  # not found / not executable / a batch path over MAX_PATH (WinError 206)
            raise UsageError(f"cannot start the command {argv[0]!r}: {exc}") from None
        try:
            code, timed_out = proc.wait(timeout=timeout), False
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            code, timed_out = None, True
    tail = _tail(folder / "stderr.txt") or _tail(folder / "stdout.txt")
    return {"code": code, "seconds": time.perf_counter() - t0, "timeout": timed_out, "tail": tail}


def main(args, report: Report, run_dir: pathlib.Path, run_id: str) -> None:
    cmd = getattr(args, "cmd_tokens", None) or args.cmd
    if not cmd:
        raise UsageError("--cmd is required: the check command, containing {input}")
    if not any("{input}" in t for t in cmd):
        raise UsageError("the command must contain {input} where the path of the (mutated) copy goes")
    shell_warning = None
    if _shell_like(cmd[0]):
        if not args.allow_shell_script:
            raise UsageError(f"{cmd[0]!r} runs through a command shell (cmd.exe or PowerShell), which re-parses its "
                             "arguments; run the underlying program directly (e.g. python check.py '{input}'), or pass "
                             "--allow-shell-script after reviewing the script")
        if CMD_META & set(str(run_dir)):
            raise UsageError(f"the run folder path {run_dir} contains shell metacharacters; choose another --out")
        shell_warning = (f"WARNING: --allow-shell-script: {cmd[0]!r} runs through a command shell that re-parses its "
                         "arguments. The copies are named input<ext> and the run folder path has no shell "
                         "metacharacters, but everything the script itself does is on you: review it.")
        print("*" * 78 + "\n" + shell_warning + "\n" + "*" * 78, file=sys.stderr)
    src = require_file(args.input, "--input")
    kind = src.suffix.lower()
    if kind not in (".csv", ".json"):
        raise UsageError("--input must be a .csv or .json file")
    try:
        pass_codes = {int(c) for c in args.pass_codes.split(",") if c.strip()}
    except ValueError:
        raise UsageError("--pass-codes must be comma-separated integers") from None
    if not pass_codes or not args.timeout > 0 or args.max_mutants < 1:
        raise UsageError("need --pass-codes, --timeout > 0 and --max-mutants >= 1")
    report.add_input(src)
    report.note_packages(["numpy"])
    try:
        with open(src, encoding="utf-8", newline="") as fh:
            text = fh.read()
    except UnicodeDecodeError:
        raise UsageError("--input must be UTF-8 text") from None
    doc = CsvDoc(text, args.delimiter) if kind == ".csv" else JsonDoc(text)
    only = None
    if args.columns:
        if kind != ".csv":
            raise UsageError("--columns applies to CSV input only")
        only = [c.strip() for c in args.columns.split(",") if c.strip()]
        for c in only:
            doc._col(c)  # raises UsageError on unknown names
    if args.mutations:
        spec = require_file(args.mutations, "--mutations")
        try:
            muts = json.loads(spec.read_text(encoding="utf-8-sig"))
        except ValueError as exc:
            raise UsageError(f"--mutations is not valid JSON: {exc}") from None
        if not isinstance(muts, list) or not all(isinstance(m, dict) and "op" in m for m in muts) or not muts:
            raise UsageError("--mutations must be a non-empty JSON list of objects with an 'op'")
        report.add_input(spec)  # the spec decides the verdict, so it is pinned in the provenance (CR-19)
    else:
        muts = doc.auto(only)
    seen = {src.resolve()}
    for tok in cmd:  # pin the check's own files too (the script it runs, a config it reads)
        p = pathlib.Path(tok)
        if "{input}" not in tok and p.is_file() and p.resolve() not in seen:
            seen.add(p.resolve())
            report.add_input(p)
    skipped = max(0, len(muts) - args.max_mutants)
    muts = muts[:args.max_mutants]
    rng = np.random.default_rng(args.seed)
    texts = [doc.apply(m, rng) for m in muts]  # build all mutants first: spec errors stop before any run
    tags = [f"{i + 1:03d}_{m['op']}" for i, m in enumerate(muts, start=1)]
    expect = {n.strip() for chunk in args.expect_survive for n in chunk.split(",") if n.strip()}
    unknown = sorted(n for n in expect if not any(n in _names(t, m) for t, m in zip(tags, muts)))
    if unknown:
        known = sorted({m["op"] + ":" + _label(m) for m in muts})[:20]
        raise UsageError(f"--expect-survive names match no mutant: {unknown}; mutants are {known}")

    mdir = run_dir / "mutants"
    mdir.mkdir()
    name, rows = f"input{kind}", []  # never the user's file name: no metacharacters reach argv (CR-04)

    def attempt(tag, body, m, expected=False):
        folder = mdir / tag
        folder.mkdir()
        path = write_once(folder / name, body)
        res = run_cmd(cmd, path, args.timeout, folder)
        status = ("TIMEOUT" if res["timeout"] else "KILLED" if res["code"] not in pass_codes
                  else "EXPECTED-SURVIVOR" if expected else "SURVIVED")
        rows.append({"id": tag, "op": m["op"], "target": _label(m), "status": status, "exit_code": res["code"],
                     "seconds": round(res["seconds"], 3), "file": str(path.relative_to(run_dir)), "tail": res["tail"]})
        return status, path

    report.section("Command (executed once per run below)",
                   "`" + " ".join(cmd) + "`\n\nThis script executed the command above; review it before trusting any "
                   "verdict. `{input}` was replaced by the path of a copy inside the run folder.")
    if shell_warning:
        report.section("Shell-script warning", shell_warning)
    status, copy_path = attempt("000_baseline", text, {"op": "baseline"})
    exact = sha256_file(copy_path) == sha256_file(src)
    ok = status == "SURVIVED"
    report.add(Check(id="MUT-BASE", title="Check passes on an unmodified copy of the input",
                     verdict=SURVIVES if ok else UNVERIFIED, criterion=f"exit code in {sorted(pass_codes)}",
                     value=rows[-1]["exit_code"],
                     detail=("byte-identical copy" if exact else "copy differs in bytes from the input") +
                            ("" if ok else f"; the check fails on the real input ({status}): nothing can be concluded "
                                           f"about mutants. Output tail: {rows[-1]['tail'][:200]}")))
    equivalent, expected_rows = [], []
    if ok:
        status, _ = attempt("001_identity", doc.dump(), {"op": "identity"})
        ok = status == "SURVIVED"
        report.add(Check(id="MUT-IDENT", title="Check passes on the re-serialized (unchanged) input",
                         verdict=SURVIVES if ok else UNVERIFIED, criterion=f"exit code in {sorted(pass_codes)}",
                         value=rows[-1]["exit_code"],
                         detail="" if ok else "the check reacts to formatting alone, so mutant kills would mean nothing"))
    if ok:
        ident = doc.canon(doc.dump())
        for i, (tag, m, body) in enumerate(zip(tags, muts, texts), start=1):
            if doc.canon(body) == ident:  # same values as the control: the check cannot tell them apart (CR-21)
                equivalent.append(f"{m['op']}:{_label(m)}")
                rows.append({"id": tag, "op": m["op"], "target": _label(m), "status": "EQUIVALENT", "exit_code": None,
                             "seconds": 0.0, "file": "", "tail": "same parsed values as the input; not run"})
                continue
            emit("stage", "running", f"mutant {i}/{len(muts)}: {m['op']} {_label(m)}", run_id=run_id, source=SRC,
                 current=i, total=len(muts))
            attempt(tag, body, m, expected=bool(expect & _names(tag, m)))
        muts_rows = rows[2:]
        killed = [r for r in muts_rows if r["status"] == "KILLED"]
        survived = [r for r in muts_rows if r["status"] == "SURVIVED"]
        expected_rows = [r for r in muts_rows if r["status"] == "EXPECTED-SURVIVOR"]
        timeouts = [r for r in muts_rows if r["status"] == "TIMEOUT"]
        caught_anyway = [f"{r['op']}:{r['target']}" for r in killed if expect & _row_names(r)]
        counted = len(killed) + len(survived)
        blind = [f"{r['op']} {r['target']}" for r in survived]
        if counted == 0:
            verdict, why = UNVERIFIED, ("no mutant could be counted (none applicable, all equivalent or expected to "
                                        "survive, or all timed out)")
        elif not killed:
            verdict, why = KILLED, f"vacuous check: none of {counted} counted mutants made it fail"
        elif survived:
            verdict, why = WOUNDED, f"blind spots ({len(survived)} unexpected survivors): {'; '.join(blind[:15])}"
        else:
            verdict, why = SURVIVES, f"all {counted} counted mutants made the check fail"
        extra = (f"; {len(expected_rows)} expected survivor(s) not counted: "
                 f"{[r['op'] + ':' + r['target'] for r in expected_rows][:10]}" if expected_rows else "") + \
                (f"; expected to survive but caught: {caught_anyway[:10]}" if caught_anyway else "") + \
                (f"; {len(equivalent)} equivalent mutant(s) not run: {equivalent[:10]}" if equivalent else "") + \
                (f"; {len(timeouts)} timed out (not counted)" if timeouts else "") + \
                (f"; {skipped} mutants beyond --max-mutants not run" if skipped else "")
        report.add(Check(id="MUT-KILL", title="Check fails when the data is corrupted (mutant kill rate)",
                         verdict=verdict, value=f"{len(killed)}/{counted}",
                         criterion=("unexpected survivors only: 0 kills -> KILLED (vacuous); some survivors -> "
                                    "WOUNDED; all killed -> SURVIVES"),
                         detail=why + extra))
        report.data["kill_rate"] = len(killed) / counted if counted else None
        report.data["blind_spots"] = blind
    lines = ["| id | op | target | status | exit | seconds |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['id']} | {r['op']} | {r['target']} | {r['status']} | {r['exit_code']} | {r['seconds']} |"
              for r in rows]
    report.section("Runs", "\n".join(lines))
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    write_once(run_dir / "mutants.csv", buf.getvalue())
    report.data.update({"command": cmd, "pass_codes": sorted(pass_codes), "runs": rows,
                        "baseline_copy_byte_identical": exact, "equivalent": equivalent,
                        "expected_survivors": [f"{r['op']}:{r['target']}" for r in expected_rows],
                        "shell_script_allowed": shell_warning is not None})


if __name__ == "__main__":
    rest, tokens = split_cmd(sys.argv[1:])
    parser = build_parser()
    parser.set_defaults(cmd_tokens=tokens)
    sys.exit(run_main(SCRIPT, main, parser, rest))
