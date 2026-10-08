# Staffer Social Network — Usage Threshold Handoff

## Latest operational override — September 4, 19:04 Eastern

User requested the most effective method with remaining usage. Replaced the eight-window process with one Python/Playwright worker; stopped checkpoint independently verified integrity PASS at 6,106 accounted (12,512 remaining). Current launcher PID 30960; log `politico_profile_crawl_20260903_raw/python_efficient_single_20260904T190422.log`. One worker retains the automatic aggregate request ramp up to 120/minute, error backoff and all verification gates. No concurrent-window experiments. AI monitoring remains PAUSED to conserve usage; Python runs independently. Inspect this current process before restarting. Older eight-window instructions and counts below are historical, not current operational settings.

Generated: `2026-09-04T22:45:20.181886+00:00`  
Codex usage remaining at handoff: **1%**  
Crawl phase: `ALL_CURRENT_PROFILES`

## Current checkpoint

Operational handoff: the recurring Codex monitor is PAUSED at the requested 1% threshold; the Python crawler was left running (launcher PID 54844, child 53044). Inspect its current status before resuming anything; never launch a duplicate writer. Log: `politico_profile_crawl_20260903_raw/python_adaptive_windows_20260904T183752.log`. Eight fixed UUID-sharded windows use adaptive simultaneous-load capacity starting at one, increasing after three clean waves and backing off on slow/failed responses. Transient recovery timeouts defer work; authentication failures still halt. Tests: 71 passed. The 120/minute setting is a navigation ceiling, not measured completed throughput. Existing bridge/graph PASS results below describe prior builds, not completion of the new full-profile reconciliation. Accounted UUIDs include unavailable-404 exceptions and are not all completed histories.

- Politico directory roster: **18,618 / 18,618 unique staffers known**.
- Profile histories accounted for: **5,863 / 18,618 (31.4910%)**.
- Profiles remaining: **12,755**.
- Committee-priority coverage: **2,577 / 2,584 (99.7291%)**.
- Employment-history rows collected: **27,954**.
- Education rows collected: **9,734**.
- Content-bearing profiles / allowed live-404 exceptions: **5,636 / 227**.
- Crawl hard failures: **0**.
- Crawl checkpoint status: **IN_PROGRESS**; integrity **PASS**; terminal gate **INCOMPLETE**.
- Verification failures / unmet terminal requirements: **0 / 7**.
- Rate control: **AUTHORIZED_GENTLE_RAMP** at the live checkpoint rate; authorized hard ceiling **250**.
- Identity statuses: `{"LEGACY_EXACT_MATCH": 1712, "LIVE_NAME_CHANGED_SAME_UUID": 6, "PROFILE_UNAVAILABLE_404": 227, "UUID_AND_NAME_MATCH": 3918}`.

## Existing reconciliation and graph

- Strict Politico/payroll bridge: **PASS**; 8,769 linked profiles, 8,768 unique payroll people, and 11,525 policy memberships.
- Independent bridge verifier: **PASS**.
- Social graph: **PASS**; 148,334 nodes and 15,343,553 edge rows.
- Independent graph verifier: **PASS**.
- Gordon Holzberg regression: **PASS**.
- Stephanie Belk regression: **PASS**.
- Canonical identity and employment promotions remain **zero**; current modeling defaults are preserved.

## Integrity receipts

- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\politico_profile_crawl_20260903_raw\crawl_verification.json` — SHA-256 `6ef584ad7453a04f688f15c84dd9558b971902604cf70a632cbe2f0249c93a01`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\politico_payroll_direct_links_20260903_v3_primary\politico_payroll_direct_link_receipt.json` — SHA-256 `5642ef01b4a37fe969882286a4dc69a116477cbd602e995aa760ff072a14a33b`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\politico_payroll_direct_links_20260903_v3_verification\verification_report.json` — SHA-256 `334880630dff396b9a44e4874ff55ff05b83ca997b824d5501b7bb712333f17e`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\staffer_social_network_20260903_v4_primary\staffer_social_network_receipt.json` — SHA-256 `36b08a581f98229d35c50620a8d212ea7834abde96f817dcdaab724e8403fb73`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\staffer_social_network_20260903_v4_verification\staffer_social_network_verification_receipt.json` — SHA-256 `3a0d953135898443b75e234cbbcae147384a94c2bddef34e78692b835a60c3cb`

## Resume and completion steps

1. Resume `ALL_CURRENT_PROFILES` from `politico_profile_crawl_20260903_raw/state.json`; completed UUIDs are skipped automatically.
2. Use authenticated crawler tabs. The legacy fixed rate of 40 requests/minute remains valid. The authorized gentle ramp is 60 → 80 → 100 → 120 → 150 → 200 → 250 when `state.rate_control.mode` is `AUTHORIZED_GENTLE_RAMP`; each step requires sustained clean evidence and adaptive backoff remains active. Never exceed 250.
3. At every authorized ramp rate, require `state.rate_control.current_requests_per_minute` to equal `state.max_requests_per_minute` and persist nonnegative `state.rate_control.last_batch.attempted`, `succeeded`, `retryable_failures`, and `hard_failures` counters. Continued ramping requires zero hard failures.
4. Immediately back off on any 401, 429, authentication or challenge surface, render degradation, or navigation degradation. Halt and report on authentication/challenge loss or any hard failure. Do not extract credentials, multiply sessions, or bypass challenges.
5. After each sustained segment, run `verify_politico_profile_crawl.py`; require `integrity_status=PASS`. An incomplete clean checkpoint is deliberately labeled `IN_PROGRESS`.
6. At 18,618 accounted UUIDs, rerun the verifier with `--require-complete`; only `status=PASS`, `completion_status=COMPLETE`, zero verification failures, and zero unmet gate requirements close the crawl.
7. Generate the crawl receipt with `write_politico_profile_completion_report.py` and independently review every `LIVE_NAME_CHANGED_SAME_UUID` and `PROFILE_UNAVAILABLE_404` exception it lists.
8. Rebuild the strict bridge with `build_politico_payroll_direct_links.py`, reproduce its twin, and run `verify_politico_payroll_direct_links.py`.
9. Rebuild the separated-layer network with `build_staffer_social_network.py`, reproduce its twin, and run `verify_staffer_social_network.py`.
10. Update `STAFFER_SOCIAL_NETWORK_COMPLETION_20260903_V4.md` and write `STAFFER_SOCIAL_NETWORK_FINAL_RECONCILIATION_20260904.md` with final coverage, hashes, limitations, and next steps.

## Known limitations

- The authenticated Politico API returns 401 outside the signed-in browser session.
- The tested history-only bulk PDF export consumed quota but did not complete.
- Live 404s and same-UUID name changes are accounted exceptions, not inferred identity merges.
- Politico directory cards are current-snapshot evidence; undated policy memberships remain a separate analysis layer.

## Watchdog and rename-retry — September 4, 9:02 PM Eastern

The Python/Playwright crawler that was already running at the start of this session (launcher PID 42940 → `.venv-politico` PID 42684 → the actual Python 3.12 interpreter PID 42692, all with command line `--workers 1 --wait-for-login --reset-rate --require-stale-seconds 0`, cwd the live tree) was left running untouched throughout. It was re-verified several times over the course of this work: `state.json` climbed from 6,926 succeeded / 11,692 remaining at the first check to 7,992 succeeded / 10,626 remaining roughly 40 minutes later, `halted` stayed `false` the whole time, and the advisory lock file `.politico-python-crawl.lock` stayed held by it. At no point was a second crawler instance actually launched — a stray-looking process that briefly appeared in one process listing turned out to be a false positive from this session's own diagnostic PowerShell command (the tool harness embeds the literal search text in its own process command line, so a search for "politico_profile_crawl_playwright" can transiently match itself); the crawler's process tree never duplicated.

**atomic_json rename-retry patch.** `politico_profile_crawl_playwright.py` had a single unguarded `os.replace(temporary, path)` call inside `atomic_json()` that could abort the whole crawl on a transient OneDrive/antivirus file lock (`WinError 5` / `Access is denied`), which is what killed an earlier run today. Before touching anything, the file was copied to `backups\politico_profile_crawl_playwright.PRE-ATOMIC-RETRY-20260905T002516Z.py` and verified byte-identical by SHA-256. The patch replaces that single `os.replace` call with a bounded retry: up to 12 attempts, starting at a 0.25s delay and doubling to a 4s cap, but only for `PermissionError`/`OSError` carrying Windows error code 5 or 32 — anything else still raises immediately, so real failures are not masked. No other `os.replace` or `.tmp` rename call exists anywhere else in the file, so no shared helper was needed. `python -m py_compile` passed, and `--self-test` (a pure in-memory unit test with synthetic fixture data — no network, no browser, no state file access) printed `{"passed": true, "fixtures": 3, "maximum_rpm": 120}`. Because the running crawler already has the old module loaded in memory, editing the file on disk did not touch or restart it; the fix only takes effect the next time the crawler process itself is started fresh (including by the watchdog below).

**Watchdog script.** `audits\staffer_network\politico_crawl_watchdog.ps1` (PowerShell 5.1) polls once a minute. If it ever sees a process whose command line matches `politico_profile_crawl_playwright`, it does nothing but log an `observed_running` heartbeat — it will never start a second crawler while one is already running. Only when no matching process exists does it look at `state.json`: if the crawl is done (`halted=false`, `remaining=0`) it writes a `WATCHDOG_DONE_<timestamp>.json` file and stops. If the crawler is gone and `state.json` was either explicitly halted with `CRAWLER_STARTUP_OR_SESSION_FAILURE` or has gone stale (no update for 3+ minutes while work remains), it reads the tail of the newest error log(s) and relaunches automatically — but only for the same transient signatures the crawl already tolerates (WinError 5/32, timeouts, connection resets, or a terminal-launched run with no error log at all). A relaunch never passes `--reset-rate`, so the proven 120/min ramp state carries over, and it always launches with `--headed` so a login prompt is visible on screen. If the log tail instead shows anything that smells like a login wall, a CAPTCHA, or an auth/rate-limit response (401/403/429, "login", "challenge", "captcha", "unauthorized", "Sign in"), or if `state.json` records any other halt reason, the watchdog writes a `WATCHDOG_HALT_<timestamp>.json` file explaining why and stops — it never attempts to click through or bypass a login or challenge. It also stops and halts once it hits the 40-relaunch cap (`-MaxRelaunches`, default 40). Every poll appends one line to `watchdog_heartbeat.ndjson` in the raw-crawl folder (timestamp, event, the PID it saw, and the current succeeded/remaining/halted/relaunch counts), and it emits Glassbox events (Lane `claude`, Source `politico-crawl-watchdog`) on startup, on every relaunch, on completion, and on any halt — wrapped so a broken Glassbox emit can never take the watchdog down.

One implementation snag worth recording: the first two attempts to launch the watchdog via `Start-Process powershell -ArgumentList @(...) -WindowStyle Minimized` died silently within seconds with no trace anywhere (no heartbeat line, no Glassbox event). Redirecting stdout/stderr to files exposed the cause — Windows PowerShell 5.1's `Start-Process -ArgumentList`, when given an array, does not quote array elements that contain spaces, so the `...\Melange Systems\...\politico_crawl_watchdog.ps1` path was split at the space and PowerShell tried to run a file called `Melange` with no `.ps1` extension. The fix was to build the argument list as a single pre-quoted string (`-File "<path>"`) instead of an array. The watchdog script's own internal relaunch call is unaffected, since none of its individual arguments contain spaces. Anyone restarting this watchdog by hand should use the same single-string form, not an array, whenever a path with spaces is involved.

The watchdog now running is PID 55236 (started 2026-09-05T00:57:51Z / 8:57:51 PM Eastern), launched detached from the live tree working directory. Its own console output is captured at `politico_profile_crawl_20260903_raw\watchdog_console_20260905T005751Z.log` / `.err.log` (both empty so far, as expected — the script only writes to the heartbeat file and Glassbox in normal operation). A one-line start marker is at `politico_profile_crawl_20260903_raw\WATCHDOG_STARTED_20260905T005751Z.txt`. It was verified alive and correctly tracking the live crawler 75 seconds after startup: three `observed_running` heartbeat lines had landed, each showing `pid_seen` 42940 (the crawler's own top-level launcher PID) and a climbing `total_succeeded`, while `state.json` itself climbed from 7,935 to 7,992 succeeded over that same window. Two earlier, failed launch attempts (PID 15948 and PID 9224, both killed by the quoting bug above before doing anything) left their own now-harmless `WATCHDOG_STARTED_*.txt` marker files behind in the raw-crawl folder; only the PID 55236 marker corresponds to a live watchdog.

**Live validation, unplanned.** At 9:04–9:05 PM Eastern, while this handoff was being written, the original crawler (PID 42940/42684/42692) exited on its own — nothing in this session stopped it; `state.json` was still climbing seconds beforehand, and the process was simply gone on the next check, with the advisory lock released. This was not caused by the source patch above (the running process had the old, unpatched code in memory) and most likely another instance of the same transient rename race, or an unrelated interruption. The watchdog handled it exactly as designed: it logged two `waiting_transient` heartbeats while `state.json`'s `last_updated` was still under 180 seconds old, then at 9:07:15 PM classified it as a crash (stale state, no matching process, empty newest error log) and relaunched with `--workers 1 --wait-for-login --headed` and no `--reset-rate`. The new process (PID 56468 → 40860) found the existing Chrome login still valid (`LOGIN_VERIFIED`, no attended sign-in needed), resumed at the full proven 120/min rate with `CLEAN_BATCH_AT_120_RPM` from the first batch, and `state.json` continued climbing normally. `watchdog_heartbeat.ndjson` shows the full sequence (`observed_running` → `waiting_transient` ×2 → `crash_detected_transient` → `relaunched`, relaunch count 1/40), and matching Glassbox events (`watchdog.started`, then `watchdog.relaunched`, run id `run-20260905T005755Z-crawlwd`) are recorded under `C:\Users\pgoff\.claude\glassbox\events`. This is a real, unplanned crash-and-recover cycle, not a synthetic test, and it went the way the design intended.

## Finishing chain runner — September 4, 2026, 9:08 PM Eastern

Everything after the crawl now has a single driver: `audits\staffer_network\finish_staffer_social_network_chain.py`. It runs steps 5 through 10 of the completion sequence above, in order, and then the two new dashboard steps, and it stops the instant any gate is unmet. It is a driver, not a decision maker — it promotes nothing, adjudicates nothing, and every generation it creates stays `REVIEW_REQUIRED`.

**How to invoke it.** From the live tree, `python audits\staffer_network\finish_staffer_social_network_chain.py` prints a dry run and exits without doing anything; that is the default, so there is no way to run the chain by accident. The dry run resolves every command to fully absolute paths, checks that every input it will read exists right now, checks that no output generation directory already exists, reports the interpreter it will invoke, and reports the current crawl state and any concurrent crawler or pipeline process it can see. When you are ready to let it finish the job unattended, use `python audits\staffer_network\finish_staffer_social_network_chain.py --wait --execute`. With `--wait` it polls `politico_profile_crawl_20260903_raw\state.json` once a minute and does nothing until the crawl reports `halted: false` with `remaining: 0`, or until the watchdog drops a `WATCHDOG_DONE_*.json` file; if a `WATCHDOG_HALT_*.json` appears instead, it halts rather than proceeding. `--from <step>` resumes at a named step after a halt has been dealt with (`--list-steps` prints the names), `--once` runs just one step, and `--date YYYYMMDD` overrides the vintage, which otherwise comes from the actual completion date in local time.

**What it actually runs.** Nothing in the chain is hand-typed. The crawl verifier's four input paths are read out of the existing `crawl_verification.json` so the terminal rerun is argument-identical to the checkpoint reruns that came before it. The five bridge inputs are read out of the v3 bridge receipt and mapped to their flags by file name. The spine root, House-ledger root, Senate-committee root and exploratory-revolving-edges path are read out of the v4 network receipt's input roles — which matters, because the network builder's own built-in defaults still point at the older `hill_personnel_spine_..._v5_primary` and `house_personnel_ledger_..._v4_primary` directories, so a build that relied on those defaults would silently use the wrong inputs. If any receipt is missing a value the runner needs, it leaves that flag out of the command and prints the gap as an owner decision rather than guessing at a path.

**Its gates.** Step 5a runs the verifier without `--require-complete` and requires `integrity_status = PASS`. Step 5b runs it again with `--require-complete` and requires all five things at once: exit code 0, `status = PASS`, `completion_status = COMPLETE`, `verification_failure_count = 0`, and an empty unmet-requirements list, with 18,618 profiles accounted. Each build step is immediately followed by its twin, then by a SHA-256 comparison of every file in the two directories, then by the independent verifier. The bridge pair must be byte-identical in all four files; the network pair must be byte-identical in all six, except that the manifest may differ in `generation_id` and nothing else, which is the convention the v3 and v4 pairs already follow. Any failed gate stops the chain, writes `FINISH_CHAIN_HALT_<timestamp>.json` next to this document with the reason and the failing detail, and emits a `blocked` Glassbox event. Every step logs its command, start and end time in UTC, exit code, and the first forty lines of output on failure, to `finish_chain_<timestamp>.log` in this directory, and emits Glassbox events under lane `claude`, source `staffer-finish-chain`.

**What it refuses to do.** It will not run any git command. It will not kill, signal, or restart any process — its liveness checks open a read-only handle and nothing more, which is deliberate, because on Windows the usual `os.kill(pid, 0)` idiom actually terminates the process it is asked about. It will not launch a crawler, and it refuses to start the chain at all while a `politico_profile_crawl_playwright` process is still alive, so it never reads `profiles.ndjson` out from under a live writer; the one exception is the read-only mid-crawl integrity probe described below, which writes to a scratch file. It will not delete or overwrite an existing generation directory — if one is already there it halts rather than clobbering it. It will not replace an existing Markdown report unless you pass `--allow-overwrite-reports`. It will not remove or steal the pipeline writer lease: the combined-dashboard rebuild runs only when no other `run_pipeline.py` process exists and `.pipeline_run.lock` is not live, and otherwise it waits, retrying every five minutes for up to two hours before writing a waiting note and stopping. It promotes nothing to canonical, and it adjudicates no identity exception: step 7 writes every `LIVE_NAME_CHANGED_SAME_UUID` and `PROFILE_UNAVAILABLE_404` row to `POLITICO_PROFILE_CRAWL_IDENTITY_EXCEPTIONS_<date>.md` as a plain listing for review, with the verifier's own policy text quoted beside each group.

**The reconciliation it writes.** Step 10 generates `STAFFER_SOCIAL_NETWORK_FINAL_RECONCILIATION_<date>.md` entirely from receipts — coverage against 18,618, bridge link counts, network node and edge counts by layer, the zero-overlap rejection count, the SHA-256 of every primary artifact and verification receipt, limitations copied verbatim from the receipt `statement` and rule fields, and the remaining owner-gated next steps. Where a receipt does not carry a figure, the document says so instead of supplying one. It then appends a dated "Final reconciliation" section to `STAFFER_SOCIAL_NETWORK_COMPLETION_20260903_V4.md` pointing at that new file.

**Two things that need a decision before the chain is run for real.** First, the dashboard section producer `fec\surfaces\build_staffer_network_section.py` does not exist yet; the runner references it with the right `--generation` argument and skips with a clear message if it is still missing, rather than failing. Second, and more substantively: the v4 network receipt records no Politico review-layer inputs at all, so the v4 graph was built without the current-committee, employment, education, policy-delta and explicit-committee-side assertions. Because the builder treats those five as all-or-none and requires all five whenever `--require-complete-politico-profile-crawl` is set, the v5 build turns those layers on for the first time. That is a scope change on top of the completed crawl, not a like-for-like reproduction of v4, and it should be an explicit choice rather than a side effect of finishing the crawl.

**Current-state check, 9:04 PM Eastern.** The runner's read-only probe (`--from verify_partial --once --execute`, writing to `finish_chain_scratch\` and never touching `crawl_verification.json`) reported `status = IN_PROGRESS`, `integrity_status = PASS`, `completion_status = INCOMPLETE`, 8,138 of 18,618 profiles accounted, 10,480 unresolved. The crawl is healthy and roughly 44 percent done; the terminal gate is correctly closed. Unit tests for the runner live in `test_finish_staffer_social_network_chain.py`: 27 tests covering command resolution from fixture receipts (including the two verifier output-path shapes), both gates, twin byte-identity including the `generation_id` exemption, and halt-file writing. All pass.

## Dashboard section producer — September 4, 21:30 Eastern

A new producer builds the Melange dashboard's Staffer Network section from this generation:
`fec\surfaces\build_staffer_network_section.py`. It is read-only against the generation, writes one
JSON file, and touches nothing else. Its tests are `fec\tests\surfaces\test_staffer_network_section.py`,
registered in `fec\tests\run_tests.py` in the staffer block of `_LANE_MODULES` (that runner selects
suites by explicit lane, so an unregistered suite would never be invoked; this raises the kernel
suite count by one).

**Inputs and hash binding.** The producer refuses to write unless every byte it reads is bound twice.
It requires the verification receipt at `staffer_social_network_20260903_v4_verification` to be
`status: PASS` with an empty `failures` list, and it recomputes the sha256 of everything it opens.
The generation receipt and manifest are bound through the verification receipt's `twin_byte_identity`
primary hashes; the three consumed artifacts — `staffer_social_node_scores.ndjson.gz`,
`staffer_trajectories.ndjson.gz` and `staffer_office_moves.ndjson.gz` — are bound through the
generation receipt's own `files` list and, independently, through the verification receipt's
`primary_file_integrity` record of both the receipt hash and the recomputed hash. The receipt's
promotion tripwire (`canonical_employment_promotions`, `canonical_identity_promotions`) must be zero
and `review_status` must be `REVIEW_REQUIRED`. This mirrors the rule in
`fec\surfaces\staffer_graph_snapshot.py`, which could not be imported for this job because its
binding is only reachable through a loader that also parses the 1.5 GB edge file; the rule is
reproduced explicitly and tightened with the second cross-check. The 1.5 GB
`staffer_social_edges.ndjson.gz` is never read, and the output says so in plain words rather than
implying it was verified: its entry carries the receipt's declared hash, an empty `bound_against`
list, and a `not_recomputed` note. `--hash-edges` binds it too for anyone who wants that.

The 533-member roster comes from the shared kernel, `moneyball_core.congestion()` over
`data\engine\congestion.json`, which is the same roster this generation's own receipt records having
used; party comes from the same kernel's Voteview map and state from `fec\legislators.csv` joined on
bioguide, exactly as the member desk enriches. No roster is hand-rolled anywhere in the producer.

**Output.** `data\engine\staffer_network_section.json`, written atomically through a temp file and
`os.replace` with a bounded retry because the tree sits under OneDrive. Keys are sorted, separators
are compact, every list has an explicit total tie-break, and the ordering keys are the rounded values
the file actually publishes, so a consumer that re-sorts on the printed fields reproduces the printed
order. Two runs are byte-identical apart from the `built_at` stamp, which `SOURCE_DATE_EPOCH` pins.
The file carries a per-member block (staff counts, shared staff, top staff, titles, office moves,
components), a `global` block, and a `meta` block. Start, completion and refusal all emit Glassbox
events on the `claude` lane under source `staffer-network-section`.

**Language rules the producer enforces.** The staffer network is its own layer below members, so the
file contains no member-to-member tie, edge or weight of any kind. Where two members appear together
it is only as shared staff — a count of people attached to both offices — and `meta.language_note`
states in the file itself that this is not a tie between the two members and carries no weight. The
producer refuses to write if the serialized output contains `member_tie`, `member_edge`,
`member_to_member`, `persuasion` or `persuade`, and it refuses if the word `influence` appears
anywhere except inside `meta.statement`, which is a verbatim copy of this generation's own
disclaimer and is never edited. The zero-overlap rule is propagated, not recomputed: the receipt's
16,001,459 rejected pairs and its stated rule appear in both `global` and `meta`. Everything is
marked `exploratory: true`, `review_status: REVIEW_REQUIRED`, `canonical_eligible: false`. No person
names are emitted at all: the three artifacts read here carry none, the producer joins none in, and
people are identified only by verified `node_id` and by the payroll title printed on their own stint.
Names remain behind the receipt-gated inventory.

**Tests.** 102 assertions, all passing. They mint a synthetic generation in a temp tree — three roster
members, six people, one person shared across two members, one person attached to a member who is not
on the roster, mixed current and departed stints, office moves both ways — with receipt, manifest and
verification files minted the way the shipped adapter expects. Besides the happy-path counts they
prove each refusal actually fires: verification not PASS, a recorded failure, a canonical promotion,
a tampered artifact, a receipt hash that does not match the verification receipt, a missing node-score
field, a trajectory that does not join the node scores, and the size cap. They also check shared-staff
symmetry, ordering reproducibility, byte-level determinism, and the language rules.

**Two things need a ruling.** First, the size cap: with the specified content the section serializes to
4,123,040 bytes, so the 3,000,000-byte default refuses and writes nothing. The run that produced the
file above passed `--max-bytes 5000000`. Raising the default, trimming `top_staff` below fifteen, or
dropping a field are all one-line changes; none was made unilaterally. Second,
`revolving_degree_sum` is zero for all 533 members, and that is not a bug in the aggregation: in this
generation `revolving_degree` is zero on every one of the 144,693 person nodes and is carried only by
container nodes (max 25, 1,007 non-zero) and organization nodes (max 93, 1,613 non-zero), because the
revolving layer is office-to-organization, never person-to-organization. Summed over a member's people
it is structurally zero. A container-scoped sum would carry signal; that is a change of population and
was left alone.

## Watchdog note — September 4, 22:25 Eastern

At 22:12 Eastern the crawler aborted with an empty-detail error: `RAW\watchdog_20260905T010715Z.err.log`
held only the 17-byte string `CRAWL_ABORTED: `, nothing else. The stdout tail's last batch before the
abort showed `BACKOFF_100_TO_80_RPM` with one retryable failure and a `SNAPSHOT_TimeoutError` at
10,828ms. `state.json` recorded `halted=true`, `halt_reason=CRAWLER_STARTUP_OR_SESSION_FAILURE`, 9,589
succeeded / 9,029 remaining. The watchdog (PID 55236) classified the bare `CRAWL_ABORTED: ` text as
`unrecognized_crash_signature` — it matches neither `$TransientPattern` nor `$AuthPattern` in
`politico_crawl_watchdog.ps1` — wrote `WATCHDOG_HALT_20260905T021449Z.json`, logged a `halt_other`
heartbeat, and exited (`exit 2`) at 02:14:50Z. No process ever duplicated: the `observed_running`
heartbeat at 02:13:41Z with `pid_seen=14900` was this session's own diagnostic `Get-CimInstance`
query self-matching its literal search string, not a second crawler. Direct reading of
`Get-CrawlerProcesses` (lines 76-84) confirms the underlying defect is real: the filter checks only
`CommandLine -like '*politico_profile_crawl_playwright*'` and does not exclude `$PID` or command
lines containing `Get-CimInstance`/`Where-Object`/`watchdog`, nor does it require the image name to
be `python.exe`. That defect exists in the script on disk, but it was not the cause of tonight's halt.

No classifier fix was applied to the watchdog script tonight, PID 55236 was never touched, and no file
was deleted. A fresh crawler (parent PID 55368 under `.venv-politico`, child PID 30616 running the
Python 3.12 interpreter, both spawned 22:19:35-36 Eastern with
`--workers 1 --wait-for-login --reset-rate --slow-response-ms 20000`, no `--headed`) was already
running and making progress by the time a 6-minute read-only observation window completed one pass —
launched by someone/something outside this session, not via the watchdog's own `Start-Relaunch` (no
new `watchdog_<stamp>.log` pair exists) and not by this session (no write, `Start-Process`, or
`Stop-Process` call was issued here). By 22:24:40 Eastern `state.json` showed `halted=false`, 9,710
succeeded / 8,908 remaining, climbing steadily with a recent `last_updated`, clearly past any login
gate. The watchdog is **not currently running** — PID 55236 exited cleanly on its own halt path and no
other `politico_crawl_watchdog` process exists — so nothing is currently supervising these two
processes if they fail again. Both the `Get-CrawlerProcesses` self-match defect and the
bare-`CRAWL_ABORTED:`-halts-instead-of-relaunches classifier gap remain unfixed in
`politico_crawl_watchdog.ps1`; a fix was drafted but not applied, since the crawl had already
recovered before it was needed. Restarting the watchdog and/or applying the classifier fix is an
owner decision, not made unilaterally here.

## Watchdog classifier fix — September 4, 11:04 PM Eastern

Backed up `politico_crawl_watchdog.ps1` to
`backups\staffer_section_20260904\politico_crawl_watchdog.PRE-CLASSIFIER-FIX.ps1` (sha256
`bb019dd9404fd8e3958c691e0239b59cd3314da20780bf86d4b536ec07145da0`, verified identical to the source
before editing) and applied both fixes identified in the 22:25 Eastern note. Defect A
(`Get-CrawlerProcesses`, was: `CommandLine -like '*politico_profile_crawl_playwright*'` alone) now
also requires `Name -eq 'python.exe'`, excludes `ProcessId -eq $PID`, and excludes command lines
matching `Get-CimInstance|Where-Object|politico_crawl_watchdog|finish_staffer_social_network_chain|Select-Object`.
Defect B (bare `CRAWL_ABORTED: ` falling through to `unrecognized_crash_signature` and halting on
first sight) is fixed by a new `Classify-ErrLog($Text,$HaltReason)` function returning
`'auth'|'transient'|'unknown'`: auth/challenge is tested first and always wins (so
`CAPTCHA ... Timeout` still halts, never relaunches); trimmed-empty or exactly `CRAWL_ABORTED:` or a
match on the (now also asyncio/Playwright-aware) `$TransientPattern` is `'transient'`; everything else
is `'unknown'`. `'unknown'` no longer halts on first sight — it waits 120s, relaunches once, and only
halts if the identical signature repeats on the very next crash-check with no `observed_running` poll
in between. Relaunch args now add `--slow-response-ms 20000` (keeping `--headed`, no `--reset-rate`,
per the operator's manual launch tonight). Heartbeat entries for halt/relaunch/wait-retry events carry
a new `detail` field with the classification decision. The `-SelfTest` switch's 8 cases (empty,
`CRAWL_ABORTED: `, `CRAWL_ABORTED: [WinError 5] Access is denied`, `TimeoutError`, `HTTP 401`,
`login challenge`, `CAPTCHA ... Timeout`, `Some brand new error`) all PASS. Parse-check
(`[scriptblock]::Create` on the file) is clean. 334 lines / 422 lines before/after. The existing
`WATCHDOG_HALT_20260905T021449Z.json` was left untouched — the script does not read halt files at
startup, so there was nothing to rename per the instruction to leave it alone if so.

The fixed watchdog was relaunched detached (PID 28884, `WATCHDOG_STARTED_20260905T024531Z.txt`) and
correctly stopped self-matching: heartbeats immediately showed genuine `observed_running` polls
against real crawler PIDs with `total_succeeded` climbing. But two things surfaced live that were not
anticipated by tonight's defect list, and both matter for whoever runs this next.

First: the crawler's own `state.json` briefly reported `halted=true` /
`halt_reason=CRAWLER_STARTUP_OR_SESSION_FAILURE` around 22:54 Eastern — a real self-reported failure,
the same class as the 02:14:49Z halt. `Get-ErrorLogTail()` (unchanged by tonight's fix — it was not
one of the two defects) picks the single most-recently-modified `*.err.log` **anywhere in the RAW
directory**, not scoped to the crawler's own run. At that moment the newest file happened to be
`python_fastresume_20260904T225409.log.err.log` (168 bytes, `can't open file
'...\Desktop\Melange': [Errno 2] No such file or directory` — an unrelated, unquoted-path launch
failure from something else writing into the same directory), which classified as `'unknown'` and
correctly took the new wait-120s-then-relaunch-once path rather than halting immediately.

Second: that relaunch (`watchdog_20260905T025648Z`, pid_seen 888) exited within seconds, its stderr
reading `CRAWL_ABORTED: checkpoint changed 12.4s ago; pause the existing CUA/JS runner and wait until
it is at least 90s old before Python takes over` — the crawler script's own collision guard, proving a
**separate, already-running restart mechanism** (not this watchdog, not manually launched by this
session) is independently keeping a crawler alive: the original 22:19 PIDs (55368/30616) are gone, and
a fresh `pwsh.exe`(30888)+`python.exe`(36116)+`python.exe`(26544) triplet was observed, most recently
spawned 23:00:42-43 Eastern, with `state.json` climbing normally throughout (9,907 to 10,473+ succeeded
across this session, never actually halted more than momentarily). The crawler's guard prevented any
actual duplicate run, but each of this watchdog's two relaunch attempts still briefly started a
throwaway `politico_profile_crawl_playwright.py` process and consumed one of the 40-relaunch budget.
Because the guard message embeds a changing elapsed-seconds value, the exact-match repeat-twice halt
safety net would not reliably catch this pattern, so left running unattended the watchdog would likely
keep repeating this wasted cycle every few minutes.

Given that, this watchdog process (PID 28884 only — no crawler process was stopped, started, or
touched) was stopped at 23:02 Eastern rather than left running unattended in a state not fully
understood. At the moment of stopping, `state.json` showed 10,473 succeeded / 8,145 remaining,
`halted=false`, climbing under whatever is already restarting it. Two things need a ruling before this
watchdog runs again: whether `Get-ErrorLogTail()` should be scoped to only the crawler's own
`python_*`/checkpoint log family instead of every `*.err.log` in RAW, and whether the classifier should
recognize `checkpoint changed .*CUA/JS runner` as an explicit no-relaunch wait state rather than
`'unknown'`. Neither change was made unilaterally.

## Finishing chain relaunched — September 5, 02:32 Eastern

The `finish_staffer_social_network_chain.py --wait --execute` runner started at 21:37 Eastern
(PID 22692, approval on file in `FINISH_CHAIN_RUNNER_STARTED_20260905T013753Z.txt`) halted itself at
02:15:01Z because `RAW/WATCHDOG_HALT_20260905T021449Z.json` existed. That halt file recorded a
transient `CRAWLER_STARTUP_OR_SESSION_FAILURE` at 02:14:49Z; the crawler recovered from it on its own
about 40 minutes later (`watchdog_heartbeat.ndjson` shows a clean `relaunched` event at 02:56:49Z) and
kept climbing for hours afterward — `state.json` reached 17,796/18,618 succeeded (822 remaining) by
06:24Z, long after the halt. The finishing chain's gate at the time treated any `WATCHDOG_HALT_*.json`
file as a permanent block, with no notion of a halt going stale once the crawler itself moved on.

Fix: `wait_for_crawl()`'s halt check was pulled into a new `current_halt_files()` method that compares
each halt file's mtime against `RAW/state.json`'s mtime. A halt file older than `state.json` means the
crawler wrote fresh state after the halt was recorded — i.e. it recovered on its own — so it is now
ignored (logged, not silently dropped). A halt file newer than `state.json` still blocks exactly as
before. The original script was backed up to
`C:\Users\pgoff\OneDrive\Desktop\Melange Systems\backups\staffer_section_20260904\finish_staffer_social_network_chain.PRE-STALE-HALT.py`
(sha256-verified identical to the pre-patch source) before editing. `python -m py_compile` passed, and
the test suite grew from 27 to 31 tests (four new `StaleHaltFileTests` covering: a halt older than
state.json is ignored; a halt newer than state.json still blocks; `wait_for_crawl()` returns quietly
past a stale halt when the crawl is otherwise terminal; `wait_for_crawl()` still raises `ChainHalt` on
a current one) — all 31 pass. A `--dry-run` from the live tree afterward showed 15 steps planned, 0
missing inputs, 0 blocked outputs, crawl terminal NO, exactly as expected mid-crawl.

`RAW/WATCHDOG_HALT_20260905T021449Z.json` was renamed to
`WATCHDOG_HALT_20260905T021449Z.superseded.json` to retire it (never deleted). Worth flagging: this
rename does *not* actually remove the file from the runner's `WATCHDOG_HALT_*.json` glob — the `*`
wildcard matches the `.superseded` text too, dot included, so the file is still enumerated. It is
harmless only because the new mtime-based check independently recognizes it as stale every time; the
post-relaunch log confirms this (`ignoring stale watchdog halt file(s) (older than state.json, crawler
recovered): WATCHDOG_HALT_20260905T021449Z.superseded.json`, repeated every poll). If a halt file ever
needs to be excluded from the glob itself rather than just judged stale, renaming it to drop the
`WATCHDOG_HALT_` prefix (or moving it out of `RAW`) would be required instead.
`FINISH_CHAIN_HALT_20260905T021501Z.json` was left in place: the runner only ever writes
`FINISH_CHAIN_HALT_*.json` files, it never reads them back at startup, so there was nothing there to
retire.

Relaunched detached: PID 58536, `finish_chain_runner_20260905T063227Z.{stdout,stderr}.log`, approval
recorded in `FINISH_CHAIN_RUNNER_STARTED_20260905T063227Z.txt` (same approval on file as the original
21:37 launch — "run the finishing chain yourself, I approve the review layers" — this is a relaunch of
that same approved run after the gate bug fix, not a new request). Verified 90 seconds after launch:
PID 58536 alive, stdout/log show the expected `waiting for terminal crawl state (poll 60 s)` lines with
`remaining=`/`succeeded=`/`halted=False` on each 60s poll, no `politico_payroll_direct_links_20260904_v4_*`
or `staffer_social_network_20260904_v5_*` generation directories exist yet, and `state.json` at that
point read 17,886 succeeded / 732 remaining / `halted: false` — still climbing, still short of the
`remaining == 0` terminal gate the chain is waiting on.

## Email package budget — September 5, 02:47 Eastern

### The regression

The staffer network landed as the fourth surface of the combined dashboard on September 4, and
that broke the emailed all-in-one attachment. `fec/surfaces/make_email_package.py` zips the
combined dashboard at compression level 9 and refuses any package over `BUDGET_BYTES`, which is
14 MiB, or 14,680,064 bytes. Before the staffer surface the package was 14,167,350 bytes (the
19:54 build on September 4). With the fourth surface merged, `Moneyball.html` grew to 80,071,855
bytes and its level-9 zip measured 14,808,817 bytes — 128,753 over. `build_zip` raised
"email package exceeds 14 MiB", `make_email_package.py` exited nonzero, and because that step sits
immediately before `audit_full.py` in the chain, the whole run halted before the audit ever ran.

The staffer panel is a roughly 4.15 MB page carrying a 4.12 MB inline JSON payload. It compresses
to about 640 KB, which was very nearly the entire headroom the package had. So this was not a near
miss that a little trimming would fix: the surface costs more than the budget had left.

### The decision

Two options were rejected. Raising `BUDGET_BYTES` is not this code's call — it is an email
attachment limit, sized for base64 transfer overhead on the receiving side, and only the owner
knows what the real ceiling is. Trimming the staffer section down to fit would have left roughly a
1% margin, which the next data refresh would eat.

What was done instead is to split the two deliverables, which had silently been the same file:

  * `Moneyball.html` stays the four-surface document — network, member desk, industry, staffer.
    It remains the file-open and live deliverable and is what the audit checks for an
    `id=app-staffer` panel.
  * `Moneyball_Email.html` is a new three-surface variant — network, member desk, industry —
    which is exactly what `Moneyball.html` was before September 4. This is what gets zipped into
    the all-in-one attachment, and it is stored inside the zip under the arcname `Moneyball.html`,
    so nothing changes for a recipient: they open the same filename they always have.

Both documents come out of one extraction. `make_combined.py` now has a pure function
`assemble(pieces, include_staffer)` and calls it twice over the same extracted pieces, so there is
no second parse, no second staleness contract, and no way for the two documents to disagree about
a surface. With `include_staffer` false it omits exactly three things: the staffer stylesheet
layer, the `#app-staffer` panel, and the staffer IIFE. Everything else — head, layer declaration,
shell CSS, the other three panels and their scripts, and the whole controller — is identical.

One behavioural change came with it. The controller defines `gotoStaffer` in every build,
including builds that have no staffer panel, and it did not check whether the panel was there. In
the email variant (and in any tree with no verified staffer generation, which was already possible
before tonight) a call to `gotoStaffer` would have pushed `?v=staffer` and then hidden every panel
that does exist, leaving a blank page. It now looks the panel up first and falls back to
`gotoNetwork` when it is absent, forwarding `nopush` so a Back/Forward-driven call still does not
push a duplicate history entry. That guard is the only difference between today's `Moneyball.html`
and the one the next chain run will write: 545 bytes, measured, and nothing else.

The network header's "Staffer network" link is deliberately unchanged and still points at
`staffer-network.html`. In the four-surface document the controller intercepts it and switches
panels in-page. In the email variant the intercept declines, because it requires the panel to
exist, and the click becomes a real navigation. **Worth knowing: the all-in-one zip contains only
`Moneyball.html`, and the family zip does not carry `staffer-network.html` either, so for an email
recipient that link dead-ends.** It was left that way on instruction rather than stripped; if that
is not acceptable the two options are to remove the link from the emailed variant, or to let the
intercept fire unconditionally so the click quietly stays on the network instead.

### Files changed

Every file was backed up to `backups\staffer_section_20260904\` before editing, with the copy's
sha256 compared against the original's.

  * `fec\surfaces\make_combined.py` → `make_combined.PRE-EMAIL-FIX.py` (30,073 bytes,
    sha256 F3F4A4C5A7DC3C2C…). Header block rewritten to describe both outputs and why; the
    concatenation moved verbatim into `assemble(pieces, include_staffer)`; a `PIECES` dict built
    from the existing extraction; `gotoStaffer` guarded; `Moneyball_Email.html` written with
    `write_text_atomic`; both sizes printed. The four-surface document is released from memory
    before the variant is assembled, because these pages hold an astral code point and CPython
    therefore stores them 4 bytes per character — the 79.7 M-character `Moneyball.html` is a
    304 MB string, and the builder's peak was already around 600 MB.
  * `fec\surfaces\make_email_package.py` → `make_email_package.PRE-EMAIL-FIX.py` (4,863 bytes,
    sha256 2E2D9B652CCC2533…). `MONOLITH_FILES` became a `(source, arcname)` pair table with a new
    `entries()` normalizer; the input receipt now records the source name and its sha256 plus the
    arcname; the 14 MiB check is untouched; a missing `Moneyball_Email.html` raises the same
    "email package input is missing" error, naming it.
  * `fec\tests\infra\test_collection_stream_wiring.py` →
    `test_collection_stream_wiring.PRE-EMAIL-FIX.py` (90,022 bytes, sha256 A2101872FC8FE2B5…).
    Its existing email-package test consumed `MONOLITH_FILES` as plain names and would have
    crashed on the pair table; it now reads sources through `entries()` and additionally asserts
    that every hash-bound input resolves to a real file and that the monolith records source
    `Moneyball_Email.html` delivered as `Moneyball.html`.
  * `fec\tests\run_tests.py` → `run_tests.PRE-EMAIL-FIX.py` (38,486 bytes,
    sha256 B06DF24692FE87E4…). Registered the two new suites. This runner uses an explicit
    registration list rather than discovery, and its own standing comment is that a suite no
    runner invokes is indistinguishable from a deleted one — so leaving them unregistered would
    have made them decoration. Two added lines, trivially reversible if that is not wanted.
  * `fec\audit\audit_full.py` — **not changed, deliberately.** Its email-package check reads
    `_item.get('name')` for each entry of `inputs` and `monolith_inputs`, joins it to the repo
    root and re-hashes it. Because the receipt keeps `name` as the source path, that check now
    hash-binds `Moneyball_Email.html` automatically and correctly. Its other conditions —
    schema `email-package-v2`, status `CURRENT_HASH_BOUND`, eight family inputs, one monolith
    input, every package under 14 MiB — all still hold. Nothing there needed an edit, so nothing
    there was edited.

New files, no backup needed: `fec\tests\surfaces\test_combined_email_variant.py` and
`fec\tests\surfaces\test_email_package_variant.py`.

### Test output

`test_combined_staffer_section.py`, the 46-check source contract suite for the staffer panel, was
re-run unchanged and still passes in full — the refactor deliberately kept every source string it
pins, which is why the merge expressions inside `assemble` are the pre-refactor ones verbatim.

    python fec/tests/surfaces/test_combined_staffer_section.py   ->  46 passed, 0 failed
    python fec/tests/surfaces/test_combined_email_variant.py     ->  39 passed, 0 failed
    python fec/tests/surfaces/test_email_package_variant.py      ->  33 passed, 0 failed
    python -m pytest fec/tests/infra/test_collection_stream_wiring.py -q  ->  74 passed in 2.70s

`test_combined_email_variant.py` is worth describing, because of how it gets its proof.
`make_combined.py` does all of its work at module scope, so importing it would rebuild a 76 MB
artifact; the suite instead parses the file, lifts the `assemble` function out of the AST, and
execs that function alone in an empty namespace. That is what proves the function pure — if it
reached back to any module global it would raise `NameError` and the suite would go red. It then
compares `assemble(pieces, True)` against a hand transcription of the pre-refactor concatenation
held in the test, and pins the variant negatively as that same document minus exactly three named
chunks and nothing else. It also cross-checks, through the AST, that every key `assemble` reads is
a key the module actually supplies, so a typo in the piece table fails a test instead of failing a
chain run.

`test_email_package_variant.py` seeds a temp tree containing the eight family surfaces, a
synthetic `Moneyball_Email.html`, and a decoy `Moneyball.html` with different content, then proves
the zip carries the email variant's bytes and not the decoy's; that the single zip member is named
`Moneyball.html` and the source name appears nowhere inside; that the receipt hash-binds the
source; that a missing `Moneyball_Email.html` refuses by name rather than silently substituting the
four-surface file sitting next to it; and that the budget check still fires under a patched tiny
budget — with a negative control proving the same call succeeds under the real budget, because
"it raised" on its own proves nothing about the budget.

### The size proof

Nothing was run against the live tree: another lane's full chain has held `.pipeline_run.lock`
since 02:17, so `make_combined.py`, `make_email_package.py` and `run_pipeline.py` were all left
alone. The sizes below were derived from files already on disk, in a scratch directory.

First, the email variant was reconstructed by cutting the three staffer chunks out of today's
`Moneyball.html` at the same boundaries `assemble` uses. That removed 4,154,139 characters and
produced a 75,917,644-byte document which zips at level 9 to **14,167,504 bytes**, against the
14,680,064 budget — 512,560 bytes under. The same script zipped today's unmodified four-surface
`Moneyball.html` as a control and got 14,808,817 bytes, reproducing the measured overage exactly,
which is what makes the method trustworthy.

Then the same claim was proved a second way, from the other direction. Today's live
`Moneyball.html` was factored back into the seventeen pieces `assemble` takes, and the real
`assemble` — lifted out of the edited builder — was run over them:

    assemble(pieces, True)  == today's live Moneyball.html      : True (79,714,081 chars each)
    assemble(pieces, False) == the cut-out reconstruction above : True (75,559,942 chars each)

The first line is the byte-for-byte guarantee on the four-surface deliverable, established against
the real 80 MB document rather than a fixture. The second is two independent methods — cutting
content out of the assembled page, and never adding it during assembly — agreeing to the byte.

Finally, allowing for the 545-byte controller guard that the next build will include, the numbers
the chain will actually produce are:

    Moneyball.html        80,072,400 bytes   (today's file + 545)
    Moneyball_Email.html  75,918,189 bytes
    all-in-one zip        14,167,719 bytes   budget 14,680,064   margin +512,345 (3.49%)

For reference, the four-surface document at that same point would zip to 14,809,021 bytes, still
128,957 over — so the split is doing real work, not shaving a rounding error.

### What is still the owner's call

The staffer surface is not in the emailed package at all. If it should be, the fix is not on this
side: raise `BUDGET_BYTES` in `fec\surfaces\make_email_package.py` to whatever the real attachment
ceiling is, and point `MONOLITH_FILES` back at `Moneyball.html`. As of tonight the four-surface
package needs at least 14,809,021 bytes, so a 15 MiB budget (15,728,640) would carry it with about
920 KB of room. That is a deliverability question about the receiving mail system, not a code
question, which is why it was not decided here.

Two smaller things also await a ruling. The dead "Staffer network" link in the emailed variant,
described above. And the disk cost: `make_combined.py` now writes a second ~76 MB document into
the live tree on every chain run, so the tree grows by that much and the builder does one more
large atomic write.

## Lane close-out (coordinator) — September 5, September 5, 2:53 AM Eastern

This section is the coordinator's summary of the staffer dashboard lane so a later session can read one place. Everything below was done in the live tree without git, with a backup of every edited file under backups/staffer_section_20260904/.

What was delivered. The staffer social network is the fourth top-level surface of Moneyball.html (id app-staffer, route ?v=staffer&s=<Member Name>, header link "Staffer network" on the influence map). Its data comes from fec/surfaces/build_staffer_network_section.py, which is receipt-gated on the v4 verification PASS, binds every input hash, and is deterministic (102 tests, registered in run_tests.py, so the kernel baseline moved by one suite). The page is built by fec/surfaces/make_staffer_network_html.py from templates/make_staffer_network_html_00.tpl (35 tests) and merged by make_combined.py (46 tests). The two producer steps sit in run_pipeline.py before make_member_desk.py, and audit_full.py has a [STAFF] block whose three checks were OK on the current tree. The other lane's inject_navigation hook, which loaded a script from 127.0.0.1:8841 into the combined page, is a no-op now; the live sidecar is only feature-detected from the staffer page with a no-cors fetch.

Independent verification. A six-verifier workflow re-derived the section counts for Crapo, Padilla and Scalise from the generation files and found them equal to the JSON; the zero-overlap rejected pair count 16,001,459 is carried through and shown; the four-surface page carries exactly one app-staffer block, no launch.js reference, and ranks_python.json was untouched. A sandbox render of all four routes (staffer station, member desk, industry, influence map, plus the header link into the staffer surface) passed with an empty console. A read-only audit_full at 22:55 Eastern on September 4 reported 574 passed and 8 failed; none of the eight came from this lane.

Regression found and fixed. The fourth surface pushed the emailed all-in-one zip to 14,808,817 bytes against the 14 MiB budget, so the chain halted at make_email_package.py before audit_full.py. make_combined.py now also writes a three-surface Moneyball_Email.html, and make_email_package.py zips that file under the arcname Moneyball.html (projected 14,167,719 bytes, about 3.5 percent under budget). The four-surface Moneyball.html assembly is byte-identical apart from a 545-byte guard that makes gotoStaffer fall back to the network when no staffer panel exists. The header's staffer link is stripped from the email variant so recipients do not hit a dead navigation.

Crawl and finishing chain. The Politico crawl survived the night through the rename-retry patch, the operator's own restart mechanism, and one watchdog relaunch; the redesigned watchdog (10-minute staleness backstop, other-supervisor detection, checkpoint-guard wait, digit-normalized repeat detection, self-test 11 of 11) is parked and was not relaunched because the crawl was above 95 percent under a healthy runner. The finishing chain runner was relaunched at 02:32 Eastern after its gate was fixed to ignore watchdog halt files older than the crawler's last state write; it will run the 15 steps when remaining reaches zero, with the five Politico profile-history review layers on, as Paul approved.

Paul's calls. Whether the emailed package should stay three surfaces (default) or the 14 MiB budget should rise so the staffer surface is emailed too. The v5 disposition once STAFFER_SOCIAL_NETWORK_FINAL_RECONCILIATION_20260904.md lands (the sidecar repin to v5 belongs to the graph-consolidation session). Whether the parked watchdog should be relaunched if the operator's runner stops. A fresh kernel and audit_full measurement in the live tree after the other lane's full chain completes.

## Email variant: staffer link removed — September 5, 3:01 AM Eastern

`assemble()` in `fec/surfaces/make_combined.py` now strips the network header's
`<a id=stflink ...>` anchor out of `snabody` before concatenation whenever `include_staffer`
is False, so `Moneyball_Email.html` no longer ships a dead link to a staffer-network.html that
is not in the package, while the True path never touches `snabody` and stays byte-identical.
`fec/tests/surfaces/test_combined_email_variant.py` gained two checks for this (the anchor is
present exactly once in the four-surface document and absent from the email variant) and its
size-delta check now accounts for the anchor's length; both surface test suites pass in full
(41/41 and 46/46).

## Owner ruling: email package — September 5, September 5, 11:50 AM Eastern

Paul ruled: keep the three-surface email package (Moneyball_Email.html zipped as Moneyball.html); the 14 MiB budget stays. He asked to be notified when the v5 network lands; a watch is armed in the coordinating session on the v5 verification receipt.


## Crawl completion and the first finishing gate — September 5, September 5, 12:43 PM Eastern

The crawl reached 18,618 of 18,618 at 12:24 Eastern with zero failures. The finishing chain halted two minutes later at step 5a because the verifier reported integrity FAIL on one row written by the API crawler; the crawl lane repaired that row at 12:27 and a read-only re-verification at 12:35 shows integrity PASS with zero failures. The remaining gap is contractual: 18 profiles are declared SOURCE_CONFIRMED_MISSING_FIELDS (valid API binding, no positions or employment history at the source), and the verifier's completion partition counts only content-bearing and verified-unavailable rows, so completion stays INCOMPLETE at 18,600 of 18,618. Paul ruled at 12:40: re-crawl the 18 through the browser path first, leave the verifier contract alone. The finishing chain stays idle until the receipt reaches COMPLETE; it resumes with --from verify_partial --execute.

