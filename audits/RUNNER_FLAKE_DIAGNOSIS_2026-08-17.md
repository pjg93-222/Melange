# Aggregate-runner flake diagnosis — 2026-08-17

**Status: TWO mechanisms confirmed by capture, ONE fix applied at Paul's direction, ONE fix proposed
and awaiting his gate, ONE suite still uncaptured.** There is no single root cause: the flake family
is at least two unrelated defects that happen to share an intermittent surface.

| Suite | Verdict shape | Mechanism | State |
|---|---|---|---|
| `test_build_legislation_identifier_probe_shards` | `errors=1` | scanner denial on an unprotected staging-**directory rename** | CONFIRMED (natural capture) → **FIX APPLIED + verified** |
| `test_legislation_base_network` | assertion | `.xlsx` not byte-reproducible: openpyxl overwrites `properties.modified` with the **save-time clock** | CONFIRMED (natural capture + deterministic repro) → **fix PROPOSED, not applied** |
| `test_run_legislation_review_batches` | `failures=1` | a proven-sufficient assertion mechanism, but zero corroboration across every regime tried | UNCAPTURED — no fix proposed; capture path armed |

**What Paul needs from this document, in one paragraph.** The probe_shards fix is applied and
verified; merging `claude/amazing-cray-1e3a27` makes it permanent (it currently also lives as
uncommitted bytes in the live tree). The bigger remaining gate-flicker is base_network at a measured
**4.5% of runs (~1 in 22)** — so a lone `153/1` should not be read as a regression until its ~2-line
fix (item 3a below) is gated in. review_batches is unexplained and no change is proposed for it; the
armed `RUNTESTS_DUMP_DIR` recipe (item 4) is what will identify it, and that recipe has already
proven itself by catching base_network on its first routine use.

## Symptom (as observed by Paul, 2026-08-17 morning, live tree)

Three consecutive `fec/tests/run_tests.py` aggregate runs: 154/0, 153/1, 151/3. Named intermittent
failures: `test_build_legislation_identifier_probe_shards` (errors=1) and
`test_run_legislation_review_batches` (failures=1). Both pass 4/4 and 6/6 solo under pytest and
pass when aggregated under a single pytest process. A similar single-failure flicker occurred the
same morning before any related merge (pre-dates the C1-2026 collector). A prior instance of the
same class is recorded in the runner itself: `test_legislation_base_network` failed 2/3 kernel runs
on 2026-08-05 while passing every standalone run (comment at `fec/tests/run_tests.py:451-454`,
where the `RUNTESTS_DUMP_DIR` trap was added).

## Verdict on the three named suspects

| Suspect | Verdict | Evidence |
|---|---|---|
| Subprocess concurrency racing on a shared scratch/port/artifact | **ELIMINATED** (within one runner) | The runner launches every suite **sequentially** via blocking `subprocess.run` (`fec/tests/run_tests.py:448-461`). No two suites ever run concurrently in one aggregate run. |
| Environment-variable bleed (PYTHONPATH etc.) | **ELIMINATED** | The two flaky suites run with `env=None` (inherited, unmodified); the `_pkg_env` PYTHONPATH override applies only to other lanes. The probe_shards failure reproduced **solo** with no environment change. Same shell produced 154/0 and 153/1 back-to-back. |
| Freshness-sensitive check with a time window | **ELIMINATED** | `run_legislation_review_batches.py` contains zero time/mtime logic (grep: no `time.time`, `mtime`, `datetime`, `now(`). `build_legislation_identifier_probe_shards.py` uses `utc_now()` only for metadata stamps (`created_at`/`completed_at`), never in a validity comparison. |

A fourth mechanism explains probe_shards: **transient Windows file-lock denials from a concurrent
scanner (Defender real-time scanning is ON on this box; OneDrive's sync engine is a second
handle-holder during live-tree activity), racing the suites' rename/replace operations in `%TEMP%`.**

A **fifth**, entirely unrelated to file locks, explains base_network and is documented below: a
wall-clock timestamp leaking into an artifact that a byte-idempotence test compares across two runs.
The row-3 elimination above ("freshness-sensitive check") was correct as written — it addressed
freshness *validity comparisons* — but it did not consider timestamps embedded in **output bytes**,
which is a different failure surface. That gap is closed below.

## CONFIRMED #2: base_network — openpyxl's save-time clock (NATURALLY CAPTURED 2026-08-17 ~22:25)

Captured live by the `RUNTESTS_DUMP_DIR` trap during a full kernel gate (the gate returned
**153 passed / 1 FAILED**, that one failure being this suite). The dump:

```
PASS test_amendments_are_half_weighted_and_forged_weights_fail_closed
staged base network: 2 contributions -> 2 edges -> 5 nodes
...
  File "fec\tests\legislation\test_legislation_base_network.py", line 372, in
       test_end_to_end_outputs_hashes_and_byte_idempotence
    assert first_hashes == second_hashes
AssertionError
```

**Mechanism, proven deterministically.** The test runs the producer twice and asserts the output
hashes match. `build_legislation_base_network.py:893-896` carefully pins the workbook's document
properties:

```python
workbook.properties.created  = dt.datetime(1980, 1, 1)
workbook.properties.modified = dt.datetime(1980, 1, 1)
```

`created` is honored. **`modified` is not** — openpyxl's `save_workbook()` overwrites it
unconditionally at line 292 of `openpyxl/writer/excel.py`:

```python
workbook.properties.modified = datetime.datetime.now(tz=datetime.timezone.utc).replace(tzinfo=None)
```

So `docProps/core.xml` inside the `.xlsx` carries the save-time clock at **one-second granularity**.
Two saves in the same wall-clock second are byte-identical; two saves that straddle a boundary are
not. Measured directly (`which_member.py`): of the 9 zip members, **only `docProps/core.xml`
differs**, every ZIP entry header stamp is unchanged, and the two files' timestamps read
`1980-01-01T00:00:00Z` (created, pinned, stable) versus `...T02:29:09Z` → `...T02:29:10Z`
(modified, one second apart).

Driving the **shipped test** both ways (`zip_clock_proof.py`, no repo file modified):

| Condition | Result |
|---|---|
| both producer runs inside one wall-clock second | **PASS** |
| second run forced past a second boundary | **FAIL**, identical traceback to the natural capture |

**Why this is intermittent, quantitatively.** Failure probability ≈ (elapsed time between the two
saves) ÷ 1 second. A ~50 ms gap on an idle box predicts ~5% of runs — consistent with exactly one
base_network failure across ~21 aggregate runs today. A loaded box widens the gap and the rate rises
accordingly, which is consistent with the recorded 2026-08-05 observation of 2 failures in 3 kernel
runs. **This also makes it a strong candidate for the unnamed third failure in Paul's `151/3` run.**

Nothing about this mechanism involves Defender, OneDrive, aggregation, or the runner. It is a
genuine reproducibility defect in the producer: the artifact is *logically* deterministic (every
other zip member is byte-identical) but not *byte* reproducible.

**Measured impact on the gate: ~1 run in 22.** Running the shipped test function unmodified 200
times gave **9 failures = 4.5%**, at a mean per-test wall time of 161 ms. Three independent numbers
agree: the mechanism *predicts* (gap between the two saves) ÷ 1 s; the controlled measurement is
4.5%; and the observed field rate today was 1 failure across ~21 aggregate runs (4.8%). So until
this is fixed, a kernel gate on this box reads **153/1 instead of 154/0 roughly 4-5% of the time**,
rising on a loaded box as the gap widens — which is the same direction as the recorded 2-of-3 on
2026-08-05. Combined with the (now fixed) probe_shards rate of ~3% solo, the pre-fix expectation was
a flicker in roughly 1 gate run in 13, with morning conditions materially worse. That is the
quantitative explanation for Paul's 154/0 → 153/1 → 151/3 sequence.

## CONFIRMED: probe_shards (errors=1)

Captured on iteration 3 of a 30× solo loop on an otherwise idle box (2026-08-17 14:46, full
traceback in the session log):

```
ERROR: test_consolidation_requires_and_publishes_exact_210
  File "fec\legislation\build_legislation_identifier_probe_shards.py", line 846, in consolidate
    stage.rename(output)
PermissionError: [WinError 5] Access is denied:
'C:\...\Temp\tmpslj3lriq\.consolidated.staging-axglvwuh' -> 'C:\...\Temp\tmpslj3lriq\consolidated'
```

`consolidate()` writes ~70 files (some with fresh-timestamp content, so never verdict-cached) into
a staging directory, then renames the **directory** in one unprotected call. A directory rename is
denied if any file inside it still has an open scanner handle. The **sibling** module's
`atomic_write` (`run_legislation_review_batches.py:109-129`, 8 attempts, exponential backoff)
already treats transient `PermissionError` on `os.replace` as expected Windows behavior, and that
is the ratified shape this fix mirrors. An `errors=1` unittest verdict is exactly what a
`PermissionError` escaping a test body produces.

> **CORRECTION (adversarial review, same day).** An earlier revision of this paragraph claimed that
> *this* module's `atomic_write_json` already carried that protection and that the directory rename
> was "the one move without it." That was **false about pre-fix code**: at HEAD the module had a
> bare `os.replace` with no retry, so it had **two** unprotected moves, not one. Fix item 2 below
> was the correct half of the contradiction and the applied change is right; only this prose was
> wrong. Line citations in this document are **pre-fix** numbers (`stage.rename` at 846,
> `atomic_write_json`'s replace at 95); **post-fix they are 860 and 100** respectively.

## OS-primitive measurements (this box, 2026-08-17 afternoon)

Standalone probe (`pd_probe.py`, scratchpad; 20,000 trials, each = 4 rapid write+fsync+replace
cycles on one target then unlink then immediate `exists()`):

- `os.replace` denials: **235 / ~80,000 cycles (0.29% overall)** — every denial on a **re-replace of
  a recently-replaced target** (cycles 1-3); **zero** denials on a first replace after plain
  creation (cycle 0). Restricted to the only cycles that ever denied, the rate is 235/~60,000 =
  **~0.4%**; both figures appear in this document and refer to the same 235 events under different
  denominators. 233/235 cleared on attempt 2 (50 ms); worst case attempt 3.
- exists-after-unlink (pending-delete visibility): **0 / 20,000**.
- unlink denials: **0 / 20,000**.

Implications: (a) the 8-attempt retry in `atomic_write` is correctly shaped and empirically
sufficient; (b) pending-delete windows and unlink denials are non-mechanisms on this box;
(c) only rapid same-file re-replace and multi-file directory renames are exposed shapes.

## Why solo-vs-aggregate, and why the morning flickered

Defender caches scan verdicts by content. Suites whose outputs are byte-identical across runs
(review_batches is *proven* byte-deterministic by its own test) go quiet after a few executions;
suites embedding fresh timestamps (probe_shards receipts) are re-scanned every run. The aggregate
runner writes thousands of files across ~70 suites, keeping the scanner engaged so denial windows
overlap suite operations; a solo run on a quiet box usually fits between scans. Morning runs are
the worst case: Defender signature updates (typically overnight/morning) flush the verdict cache,
and the 2026-08-17 morning additionally had the full-chain run, workbook Excel COM rebuild, and
OneDrive sync traffic as concurrent handle-holders. Empirical support: probe_shards flaked 1/30 on
the quiet box but 0/150 under heavy synthetic churn (busy scanners react too slowly to collide),
and three same-protocol afternoon aggregate runs were 154/0 while the morning's three runs were
154/0, 153/1, 151/3.

## review_batches (failures=1) — capture status

**Not yet captured** (campaign continuing at the time of this draft). Cumulative clean evidence:
430 full-suite subprocess runs (quiet + churned regimes) + 2,000 in-process runs of the most
exposed test method + 6 full aggregate runs (3 quiet, 1 OneDrive-churned, 2 dual-concurrent),
zero failures. Site analysis under the measured
primitives: every write in the suite's run path goes through the retried `atomic_write`; the
completion `state_path.unlink()` (line 457) and pending-delete `exists()` windows measured at
0/20,000. The one denial-COUNTABLE site is the retry test's third attempt (`assertEqual(3,
attempts)` at test line 60): its real `os.replace` displaces an existing just-written target —
the exact shape the probe measured at ~0.4% — but the test rewrites the SAME bytes every run
(`old\n`/`new\n`), so Defender's content-keyed verdict cache stops scanning them after the first
execution, and 2,000 targeted exposures produced zero denials. This is the structural wall for
on-demand reproduction: the suite is byte-deterministic end to end, all of its files go
verdict-cache-warm, and the cache flushes only on signature updates (timestamped today at 01:50
and 08:25; the morning flicker sits in the post-08:25, chain-active, OneDrive-busy window).
probe_shards escapes the wall only because its receipts embed fresh timestamps — unique bytes
every run — which is why it is both the suite captured here and a repeat offender in the morning
runs. Honest state: the mechanism FAMILY is established and the retry test is the leading
candidate site by elimination; the exact failing assertion remains unconfirmed because a cold
verdict cache cannot be manufactured without touching Defender (prohibited). The standing
`RUNTESTS_DUMP_DIR` recommendation below guarantees the next natural occurrence self-captures.

## The failures-vs-errors discriminator, and a proven-sufficient mechanism (appended, evening)

A forensic point that was under-used earlier and narrows the search sharply: Paul's two verdicts
were **`errors=1`** (probe_shards) and **`failures=1`** (review_batches). In Python unittest an
exception escaping a test body is an **ERROR**; a **FAILURE** means an assertion evaluated false.
So probe_shards is an escaping `PermissionError` (confirmed, §CONFIRMED above) while review_batches
broke an **assertion** — a different failure class requiring a different explanation.

The one assertion in that suite whose truth depends on a real OS call is
`self.assertEqual(3, attempts)` at `test_run_legislation_review_batches.py:60`. Its test mocks
`os.replace` with a counter that raises for attempts 1-2 and calls the **real** `os.replace` on
attempt 3 (and mocks `time.sleep` to a no-op). If that real call draws a genuine scanner denial,
`atomic_write`'s own retry loop catches it and retries, the counter reaches 4, and the exact-count
assertion fails. (An earlier revision called this "the exact shape the probe measured" at ~0.4%.
That was wrong and is retracted: the site replaces onto a file created by a plain write — the
cycle-0 stratum the probe measured at **zero**. The corrected statement is the one below.)

**Mechanism proof (deterministic, no repo file modified).** A scratch harness replicated the test
body verbatim and injected exactly one denial at that point:

```
CONTROL  (no injection):    failures=0 errors=0  -> PASS
INJECTED (one denial):      failures=1 errors=0
    self.assertEqual(3, attempts)
AssertionError: 3 != 4
```

That reproduces the observed verdict shape exactly (`failures=1, errors=0`), which no other
candidate examined so far does.

**But the same site measured ZERO natural exposure.** The shipped test writes fixed bytes
(`b"old\n"` / `b"new\n"`) every run, so Defender's content-keyed cache goes warm and stops scanning
it — which is why 2,000 verbatim runs produced nothing. A harness that removes that mask (unique
bytes per iteration, same structure) measured:

| Regime | Iterations | Natural hits | Rate |
|---|---|---|---|
| Idle box | 4,000 | 0 | 0.000% |
| 3 concurrent churn workers | 4,000 | 0 | 0.000% |

Combined 0/8,000 (attempts histogram `{3: 8000}`). So the exposed primitive shape is narrower than
first stated: the ~0.3% denials measured by `pd_probe.py` occurred on **rapid repeated replace onto
one hot path**, NOT on the "replace onto an existing file" shape this site actually has.

**Ruled out for review_batches: the base_network timestamp mechanism.** Once the openpyxl clock
defect was found, the obvious question was whether review_batches' own
`test_complete_generations_are_byte_deterministic` fails the same way. It does not: the suite writes
no workbook (no openpyxl import anywhere in `run_legislation_review_batches.py`), and the triage
module it delegates to derives its timestamps from the **source manifests'** `completed_at` rather
than the wall clock (`build_legislation_membership_triage.py:291-305`) and explicitly emits
`"generated_at": None` (line 988). That suite's outputs are genuinely clock-free, which is why 430+
runs of it passed unbroken.

**Exhaustive enumeration + adversarial panel (23 agents, independent of the above).** Four
independent lenses enumerated **every** `assert*` in the suite — 150 assertions — and classified
which a transient OS denial could make evaluate FALSE (a unittest FAILURE) rather than raise (an
ERROR). Ten were flagged, deduplicating to **six candidate sites**: line 60 (`assertEqual(3,
attempts)`), 145/146 (rebuilt/reused shard counts), 153 (`assertFalse(state.partial.json.exists())`),
and 163/171 (the two `assertRaisesRegex` fail-closed blocks). Each was then attacked by a
three-lens refutation panel (mechanism-skeptic / unittest-semantics / os-primitive-realism).

**Zero of six survived** — and the *grounds* matter more than the count. The panel repeatedly
refuted at the **precondition, never at the code path**: "the claim's code-level half is accurate
and I confirmed it line by line; what fails is the causal precondition," and for line 60 the
unittest-semantics lens explicitly could **not** kill it: "I tried to kill this on
FAILURE-vs-ERROR grounds and could not; every step of the classification chain checks out."
Independently of my harness, the panel also located the same stratum error I had made — the site
sits in the cycle-0 stratum the probe measured at zero, not the ~0.4% re-replace stratum.

Two methods therefore converge on one answer: **the code path is real and would produce exactly
`failures=1`, but the OS precondition it requires has never been observed on this box.** Line 145's
sibling at 146 was additionally shown to be algebraically shadowed (it cannot fail independently),
and 153's precondition is the pending-delete window measured 0/20,000.

**Directional consequence.** With every scanner-transient candidate refuted at the precondition,
the balance of evidence says review_batches' real cause probably lies **outside** the file-lock
family altogether — exactly as base_network's did (a wall-clock reproducibility defect, not a lock
issue). The next capture should not assume a scanner.

**Final reproduction tally for review_batches (campaign closed 2026-08-18 00:40).** Every regime
this box can produce, exhausted:

| Method | Volume | Hits |
|---|---|---|
| Full suite, subprocess (quiet + churned) | 430 runs | 0 |
| Retry test alone, in-process | 2,000 runs | 0 |
| Retry test's real-replace site, unique bytes (idle + churned) | 8,000 iterations | 0 |
| **All 6 tests, in-process, under 3 churn workers** | **400 suite runs = 2,400 test executions** | **0** |
| Full aggregate kernel gate | ~25 runs | 0 |
| Static: assertions enumerated by 4 independent lenses | 150 | 6 candidates, 0 survived a 3-lens panel |

The suite does not reproduce. Contrast this with base_network, which reproduced naturally within a
single evening's routine gate and then deterministically on demand — the difference in tractability
is itself evidence that review_batches' cause is not in the family searched here.

**Honest status of the review_batches site.** The mechanism above is *sufficient* (proven to
produce the exact verdict) but is **not corroborated as the actual trigger** (natural rate below
~0.03% in both regimes, too rare to explain a same-morning occurrence). It stands as the leading
candidate on verdict-shape grounds alone. An exhaustive independent enumeration of every assertion
in the suite, with an adversarial panel, is recorded separately; until a natural capture or that
enumeration promotes a better candidate, **no code change to review_batches is proposed** — this
section deliberately stops short of a fix it has not earned.

## A correction to the original framing

The symptom was reported as "fails in aggregate, passes in isolation." That is a **sampling
artifact, not a property of the failure**: this session's one natural capture (probe_shards) came
from a **solo** 30x loop on an idle box, not from an aggregate run. Isolation confers no immunity.
The aggregate runner correlates with failures because it is what gets run during loaded periods and
because it writes far more files, keeping the scanner engaged — not because aggregation itself
races anything (the runner is strictly sequential).

## Cold-cache burst result (2026-08-17 20:46-20:57, appended)

A signature-change watcher caught the day's next Defender update live (1.457.206.0 →
1.457.214.0 at ~20:46) and fired three aggregate runs into the freshly flushed cache within
minutes. All three were CLEAN 154/0 (first run 4.1 min vs the 3.1-3.4 min warm baseline —
re-scanning was genuinely happening). Three samples is weak power, but it demotes "cold cache
alone" as a sufficient trigger: the surviving theory is cold cache AND ambient load together
(the morning had the full chain writing artifacts, OneDrive syncing them, and the Excel COM
rebuild concurrently). Day's aggregate tally: 23 runs, 0 failures, vs the morning's 2-in-3.
The watcher chain continues with churn added to the burst; the standing guaranteed path remains
item 3 below — the first gate run of any naturally loaded morning, with dumps armed, IS the
reproduction attempt that matters.

## Latent hazard noted in passing (separate, low priority)

`run_tests.py`'s core atomic-dump checks use a fixed shared path
(`%TEMP%\mb_atomic_test.json`, lines 32-49). Two aggregate runs executing concurrently (a real
multi-lane pattern in this repo) can race on it — including an unhandled `FileNotFoundError`
crash of one runner if the other's cleanup lands mid-check. Not the observed flake (Paul's runs
were serial); recorded so a future multi-lane gate collision is recognized on sight.

## Fix status

No test is weakened; no verdict handling changes; every path still fails closed by raising after
bounded retries. Mirrors the repo's own ratified pattern (`atomic_write`, 8 attempts, exponential
backoff, `PermissionError` only).

**Items 1 and 2 were APPLIED 2026-08-17 evening on Paul's explicit instruction ("apply the
probe_shards fix").** Items 3-5 remain proposals awaiting his gate.

1. **APPLIED — `fec/legislation/build_legislation_identifier_probe_shards.py:846`** — wrap the staging
   directory rename in the standard retry (add `import time`):

   ```python
   for attempt in range(8):
       try:
           stage.rename(output)
           break
       except PermissionError:
           if attempt == 7:
               raise
           time.sleep(min(0.05 * (2 ** attempt), 0.75))
   ```

2. **APPLIED — same module, `atomic_write_json` (line 95)** — the identical retry loop (same
   constants), closing the module's remaining unprotected replace.

3. **APPLIED 2026-08-18 on Paul's instruction ("apply the base_network fix") — option (a).** The
   producer's `modified` pin is silently defeated by openpyxl (§CONFIRMED #2).

   **A canonicalizer already exists and is smaller than first described.** `_canonicalize_xlsx`
   (`build_legislation_base_network.py:861-877`, called at line 900 immediately after
   `workbook.save(path)`) already rebuilds the archive: it sorts members (869) and pins **every**
   ZIP entry stamp to `FIXED_ZIP_TIME` (871). That existing helper is precisely why the measurement
   in §CONFIRMED #2 found all entry headers unchanged and only one member differing — the earlier
   revision of this document reported that as a bare empirical result without naming the code that
   guarantees it. What the helper does **not** do is normalize member *content*: it copies each
   member's bytes verbatim (870/874), so the save-time clock inside `docProps/core.xml` passes
   straight through.
   (a) **preferred, ~2 lines** — inside the existing `_canonicalize_xlsx` loop, when
   `name == "docProps/core.xml"`, substitute the `<dcterms:modified>` value with the pinned
   constant before `writestr`. No new helper, no second save, no new file.
   (b) re-assert `workbook.properties.modified` *after* `save_workbook()` mutates it and save once
   more — simpler-looking but writes twice and is fragile to openpyxl internals.
   (c) hoist content-normalization into `moneyball_core.save_workbook_atomic` so **every** workbook
   writer in the repo becomes byte-reproducible — the most valuable option and the largest blast
   radius, since it touches the shared kernel and the workbook is a rank-adjacent surface.
   I recommend (a) scoped to this producer now, with (c) considered separately on its own gate.

   **Adjacent, same class, noted not fixed:** `_canonicalize_xlsx` line 864 (pre-fix numbering) does
   `path.replace(source)` on a file openpyxl wrote one line earlier — an unprotected rename of a
   just-written file, the same exposure class this session hardened in probe_shards, sitting in this
   same producer. Left alone: it is outside what was gated, and the stratum measured zero.

   **What was actually applied.** Three module constants beside the existing `FIXED_ZIP_TIME`
   (deriving the pinned document timestamp *from* it, so there is no third hardcoded 1980 literal to
   drift), and a four-line normalization inside the existing `_canonicalize_xlsx` loop:

   ```python
   if name == CORE_PROPERTIES_MEMBER:
       data = _CORE_MODIFIED.sub(
           lambda match: match.group(1) + FIXED_DOC_TIME + match.group(2), data
       )
   ```

   `re` and `datetime` were already imported. The substitution is a no-op if the element is absent,
   so it degrades safely if openpyxl changes its output. `write_workbook`'s existing pin at 895-896
   was deliberately **not** touched: it is already honored for `created`, and re-pointing it would
   have widened the diff past what was gated.

   **Verification of the applied fix:**

   | Check | Before | After |
   |---|---|---|
   | Shipped test with the two runs forced across a second boundary | deterministic **FAIL** | **PASS** |
   | Shipped test, 200 runs (the flake-rate harness) | 9 failures = **4.5%** | **0 failures = 0.0%** |
   | base_network suite solo | — | all PASS |
   | `py_compile` | — | clean |
   | Full kernel gate | 153 passed / 1 FAILED | **156 passed / 0 FAILED** |

   **The gate count moved 154 → 156 for a reason unrelated to this work, and it was checked rather
   than waved through.** Another lane merged `claude/holistic-network-config-60c11c` into main at
   22:50 (merge `08d536b3a`); its commit `4f0722ba0` ("MEA-8 registration", authored 21:51) appends
   exactly two suites to `_LANE_MODULES` — `test_holistic_base` and `test_holistic_config`. 154 + 2
   = 156. The 153/1 gate ran at ~22:2x, *before* that merge; the 156/0 gate ran after it. Both
   totals are therefore correct for the tree they ran against, and neither delta is attributable to
   the two fixes in this document. (Recorded because a gate count that moves without explanation is
   exactly the failure the run-2 audit's count assertions exist to catch.)

   The forced-straddle case is the decisive control: it was a *deterministic* failure before and
   cannot be made to fail now. Workbook validity is covered by the suite's own
   `openpyxl.load_workbook` assertions, which pass.

   **Scope check on other workbook producers.** `build_legislation_base_network` is the only xlsx
   producer in the repo carrying a canonicalizer *and* the only one whose test asserts byte
   idempotence. Others (`build_holistic_base.py:240`, `build_multilayer_network.py:153`,
   `build_audit_workbook.py:270`, `add_judiciary_seats.py:105`, `build_social_master.py:84`,
   `process_quorum.py:165`) save without canonicalizing, so their artifacts are equally
   non-byte-reproducible — but no test asserts it, so none of them flickers the gate. That is a
   latent reproducibility gap, not a live one, and it is precisely what option (c) would close.
   **Explicitly NOT proposed: relaxing the test.** The byte-idempotence assertion is correct and is
   exactly the property the 2026-07-02 idempotency milestone (@f17dc2c) established; weakening it to
   silence the flake is barred by change-control law 7.

4. **PROPOSED — gate recipe** — run kernel gates with `RUNTESTS_DUMP_DIR` armed (e.g. a dated dir
   under `%TEMP%`). Zero cost on clean runs; any future intermittent failure self-captures its full
   suite output. **This recommendation has now paid for itself: the base_network mechanism above was
   found because the trap was armed on a routine post-fix gate run.**

5. **review_batches** — still no code change proposed; its traceback remains uncaptured and fixes
   follow evidence, not plausibility. Item 4 is the capture path.

## Verification performed on the APPLIED fix (items 1-2), 2026-08-17 evening

| Check | Result |
|---|---|
| `git diff` confined to the import + the two named functions | yes — 23 lines, one file |
| Injected 3 transient denials → `atomic_write_json` still writes correct content | PASS (4 calls, content intact) |
| **Fail-closed control**: persistent denial → still raises, no partial file | PASS |
| Injected 3 dir-rename denials → the **shipped** consolidation test | PASS (was the natural failure) |
| **Fail-closed control**: persistent dir-rename denial → still surfaces as a failure | PASS (errors=1) |
| probe_shards suite solo | 4/4 OK |
| probe_shards 60× solo loop (pre-fix baseline: 1 failure in 30) | 0 failures / 60 |
| import-hygiene gate (`audit_stale_imports`, the FIX-16 class) | 1 passed / 0 failed |
| `py_compile` | clean |
| Full kernel gate | **153 passed / 1 FAILED** — the one failure is `test_legislation_base_network`, the separate openpyxl defect of §CONFIRMED #2. `build_legislation_base_network.py` and its test do not import the changed module (verified by grep), so the applied fix is not implicated. |

No test, assertion, floor, or count was modified. No artifact or rank surface is touched: the
changed module is collection-lane tooling and the flake lives in `%TEMP%` staging paths.

**Independent review of the applied change** (adversarial, read-only) confirmed: never swallows
(catches `PermissionError` only; exits solely via `break` on success or bare `raise` at attempt 7,
preserving the original traceback); bounded at **3.00 s** maximum added latency before raising —
roughly an order of magnitude of headroom over the measured worst case of attempt 3; retries cannot
alter bytes (the temp file is written, flushed, fsynced and closed *before* the loop); and an
exhausted retry leaves no partial publication, since the staging directory is inside a
`TemporaryDirectory` context that cleans up on the raising path.

It also surfaced a safety property I had not articulated: the fix deliberately keeps `Path.rename`
rather than switching to `os.replace`. On Windows `rename` refuses an existing target with
`FileExistsError` (WinError 183), which is a **sibling** of `PermissionError` under `OSError`, not a
subclass — so it is not caught by the retry and still escapes immediately. The retry therefore
**cannot** convert the module's never-overwrite guarantee (refused at 506-509, asserted as
`"no_source_overwrite": True`) into a silent overwrite.

Two completeness notes, neither a defect under the measured primitives, neither acted on:
the `finally` at 107-108 uses `if temporary.exists(): temporary.unlink()` where the sibling uses
`try/except FileNotFoundError`, so a raise there would *replace* the in-flight exception and
mislabel a persistent-denial failure (still fail-closed, just wrong exception class); and five
adjacent unprotected mutation sites exist in the module (the sidecar `write_text` at 366-368,
`write_ndjson` at 436-440, `shutil.copy2` at 449 — the highest-count site at ~70+ calls per
consolidation — and the `manifest.json.sha256` write at 821-824). All are first-writes/creates
rather than re-replaces, the stratum measured at zero.

## Session evidence trail

Solo baseline 30×2 (1 capture); churned loops 150×2 (0); quiet loop 250× (0); in-process retry
method 2,000× (0); OS probe 20,000 trials; aggregate runs 1-3 clean 154/0 (5.6/4.6/3.9 min, dumps
armed, none written); dual-concurrent round 4 (4A+4B) both clean 154/0 at 14.8 min each under
partial OneDrive churn (the round's first churn writer died to a shared-directory cleanup race —
its own small lesson in unique scratch paths — and was replaced mid-round); quiet marathon
(runs 5-10, stop-on-capture) launched 15:35. Afternoon aggregate tally at draft close: 0 failures
in 6 samples vs the morning's 2-in-3 — the strongest single piece of evidence that the trigger is
regime-dependent (cold verdict cache + ambient chain/OneDrive/Excel load), not code-path-dependent.
Churn artifacts were confined to the session worktree (`_flake_churn*/`, self-deleting) and
`%TEMP%`; the live tree received only read-only-safe `run_tests.py` executions per project law.
