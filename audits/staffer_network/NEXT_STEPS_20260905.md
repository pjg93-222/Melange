# Staffer network and dashboard: next steps

Written September 5, 2026, 1:15 p.m. Eastern, at Paul's request ("create markdown of next steps then stop"). Everything below was stopped cleanly; nothing is running from this lane. All paths are under the live tree `C:\Users\pgoff\OneDrive\Desktop\Melange Systems` unless stated. No git anywhere (Paul's standing rule); every edited file has a backup under `backups\staffer_section_20260904\`.

## Where things stand

- **Crawl:** complete. `politico_profile_crawl_20260903_raw\state.json` shows 18,618 of 18,618, zero failures, not halted. `profiles.ndjson` has 18,618 rows (last written 12:27 p.m.). No crawler, watchdog, or crawler Chrome is running.
- **Verification:** integrity PASS, zero failures, completion INCOMPLETE. 17,127 rows carry content, 1,473 are verified unavailable, and 18 are declared `SOURCE_CONFIRMED_MISSING_FIELDS` (16 lack current positions only, 2 lack both positions and employment history). The verifier's completion partition counts only the first two classes, so it reads 18,600 of 18,618. Fresh hash-bound receipt taken read-only at 1:13 p.m.: `C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-melange-audio-integration-9c7c56\15a0c71e-4691-4822-bd93-6270b821ccda\scratchpad\cv_requeue.json` (the 18 uuids are in its `source_incomplete_profiles` list and in `source_incomplete_uuids.txt` beside it).
- **Paul's ruling (12:40 p.m.):** re-crawl the 18 through the browser path first; leave the verifier contract alone.
- **Finishing chain runner:** not running. It halted at 12:26 p.m. at step 5a (`FINISH_CHAIN_HALT_20260905T162602Z.json`) on the single-row failure that the crawl lane has since repaired. It resumes with `--from verify_partial --execute`; it will pass step 5a now and stop at step 5b (`--require-complete`) until the receipt says COMPLETE.
- **Repair tool:** `repair_politico_profile_checkpoint.py` gained an additive flag `--requeue-source-incomplete` (written 1:07 p.m.; tests extended 1:09 p.m.; backups `repair_politico_profile_checkpoint.PRE-REQUEUE.py` and `test_politico_checkpoint_repair.PRE-REQUEUE.py`). The agent that wrote it was stopped before I saw its test output, so treat the tests as unverified until step 1 below.
- **Dashboard:** `Moneyball.html` (77.2 MB) and `Moneyball_Email.html` (73.1 MB) were both rebuilt at 3:12 a.m. by the legislative-workbook lane's full chain, which means the four-surface page, the three-surface email variant, and the new chain steps all ran end to end there. Paul ruled the email package stays three-surface.
- **Files not to touch from this lane:** `verify_politico_profile_crawl.py`, `politico_profile_crawl_api.py`, `politico_profile_crawl_playwright.py` (the Codex crawl lane edited the first two at 12:21 and 12:27 p.m. and owns them), and the 8841 sidecar plus `repin_staffer_live.py` (graph-consolidation session).

## Steps, in order

Run everything from the live tree root. `PY` below means `C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe`; `VENV` means `.venv-politico\Scripts\python.exe`.

### 1. Confirm the repair-tool extension before using it

```bash
"C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe" "audits\staffer_network\test_politico_checkpoint_repair.py"
```

Expect every case to pass, including the legacy FAIL-receipt cases unchanged. If anything fails, restore both `.PRE-REQUEUE` backups and stop; the flag is not safe to use.

### 2. Take a fresh hash-bound receipt (read-only, scratch output)

The repair tool refuses a receipt whose recorded hashes do not match the current `profiles.ndjson` and `state.json`, so take it immediately before step 3.

```bash
"C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe" "audits\staffer_network\finish_staffer_social_network_chain.py" --from verify_partial --once --execute --verification-output "audits\staffer_network\finish_chain_scratch\cv_requeue_fresh.json"
```

Expect integrity PASS, zero failures, 18 `source_incomplete_profiles`. If the counts differ, the crawl lane changed the corpus; re-read before continuing.

### 3. Check nothing else is writing the crawl files

```bash
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'politico_profile_crawl|politico-playwright-profile' -and $_.CommandLine -notmatch 'Get-CimInstance' } | Select-Object ProcessId,ParentProcessId,Name,CreationDate | Format-Table -AutoSize"
```

Expect no rows. If a crawler is running, the crawl lane is doing this itself; do not proceed. If an orphaned Chrome whose command line contains `politico-playwright-profile` exists with a dead parent, it will block the browser launch; stop only that Chrome.

### 4. Back up, then quarantine exactly the 18 declared rows

```bash
powershell -NoProfile -Command "Copy-Item 'audits\staffer_network\politico_profile_crawl_20260903_raw\profiles.ndjson' 'backups\staffer_section_20260904\profiles.PRE-REQUEUE.ndjson'; Copy-Item 'audits\staffer_network\politico_profile_crawl_20260903_raw\state.json' 'backups\staffer_section_20260904\state.PRE-REQUEUE.json'"
```

```bash
"C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe" "audits\staffer_network\repair_politico_profile_checkpoint.py" --requeue-source-incomplete --profiles "audits\staffer_network\politico_profile_crawl_20260903_raw\profiles.ndjson" --verification "audits\staffer_network\finish_chain_scratch\cv_requeue_fresh.json" --state "audits\staffer_network\politico_profile_crawl_20260903_raw\state.json" --quarantine "audits\staffer_network\politico_profile_crawl_20260903_raw\quarantine_source_incomplete_20260905.ndjson" --receipt "audits\staffer_network\politico_profile_crawl_20260903_raw\repair_receipt_source_incomplete_20260905.json"
```

Expect: `profiles.ndjson` drops to 18,600 rows, `state.json` shows remaining 18 and total_succeeded 18,600, the quarantine file holds the 18 original rows, the receipt names the ruling. The tool aborts (and writes nothing) if any declared row lacks its declaration or if the receipt's list does not equal the rows on disk.

### 5. Re-fetch the 18 through the browser path

Headed, one worker, the operator's 20-second slow-response threshold, no `--reset-rate`. If the dedicated Chrome window asks for a Politico login, sign in yourself; nothing automated may do that.

```bash
powershell -NoProfile -Command "Start-Process '.venv-politico\Scripts\python.exe' -ArgumentList '-u audits\staffer_network\politico_profile_crawl_playwright.py --workers 1 --wait-for-login --headed --slow-response-ms 20000' -WorkingDirectory (Get-Location).Path -WindowStyle Normal -RedirectStandardOutput 'audits\staffer_network\politico_profile_crawl_20260903_raw\python_requeue_20260905.log' -RedirectStandardError 'audits\staffer_network\politico_profile_crawl_20260903_raw\python_requeue_20260905.err.log'"
```

Watch `state.json` until remaining returns to 0 (18 fetches, minutes). If it halts, read the `.err.log`; an empty `CRAWL_ABORTED:` message is a transient timeout and a relaunch is safe once no crawler process exists.

### 6. Re-verify and read the outcome

```bash
"C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe" "audits\staffer_network\finish_staffer_social_network_chain.py" --from verify_partial --once --execute --verification-output "audits\staffer_network\finish_chain_scratch\cv_after_requeue.json"
```

Two possible outcomes:

- **The browser path recovered content** for all 18: completion becomes COMPLETE. Go to step 7.
- **The browser path found the same emptiness:** the browser crawler writes empty collections without the API crawler's declaration, so the verifier will list them under `incomplete_profile_content` and integrity turns FAIL. That is the evidence Paul asked for. The choice is then his: count declared source-incomplete rows as accounted (one anchored line in the verifier's `content_or_allowed_404_partition`, adding `len(source_incomplete_profiles)`; the crawl lane owns that file), or accept an INCOMPLETE receipt and run the finishing chain without `--require-complete` (which also means the v5 network build cannot use `--require-complete-politico-profile-crawl`, so the five profile-history review layers would stay off).

### 7. Resume the finishing chain

Only when the receipt reads COMPLETE. The runner writes its own halt file on any failed gate and never overwrites an existing generation directory.

```bash
powershell -NoProfile -Command "Start-Process 'C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe' -ArgumentList '\"audits\staffer_network\finish_staffer_social_network_chain.py\" --from verify_partial --execute' -WorkingDirectory (Get-Location).Path -WindowStyle Minimized -RedirectStandardOutput 'audits\staffer_network\finish_chain_runner_resume.stdout.log' -RedirectStandardError 'audits\staffer_network\finish_chain_runner_resume.stderr.log'"
```

It runs, in order: terminal verification, completion report, identity-exception review list, bridge primary and twin plus verifier, network v5 primary and twin plus verifier (review layers on, as approved), the reconciliation document, `build_staffer_network_section.py --generation staffer_social_network_20260904_v5_primary`, then `run_pipeline.py --from make_combined.py` when no other pipeline holds the lock. Expect hours and roughly 3 GB of new disk per network generation.

### 8. After v5 lands

- The graph-consolidation session owns the 8841 sidecar repin: `fec\surfaces\repin_staffer_live.py --wait --execute`, launched by Paul.
- Read `STAFFER_SOCIAL_NETWORK_FINAL_RECONCILIATION_20260904.md` and rule on the v5 disposition.
- Re-measure kernel tests and `audit_full.py` in the live tree. The kernel baseline moved by three suites this lane (`test_staffer_network_section`, `test_combined_email_variant`, `test_email_package_variant`).

## Parked, by decision

- `politico_crawl_watchdog.ps1` is rewritten as a 10-minute-staleness backstop (self-test 11 of 11) and deliberately not running. Relaunch only if a long crawl needs unattended supervision.
- Long-form profile regeneration waits for the full 533-member long-form pass and then goes through the holistic evidence merge.
- The email package stays three-surface; do not re-propose raising the 14 MiB budget.

## Records

- Running log of this lane: `audits\staffer_network\STAFFER_SOCIAL_NETWORK_USAGE_HANDOFF_20260904.md` (append-only; other lanes write to it too).
- Canonical dashboard report: `audits\MONEYBALL_HTML_CANONICALIZATION_2026-09-04.md`.
- Brain `STATE.md` (Project Brain repo) carries this lane under Active workstream and Next action; it is updated on disk and uncommitted under the no-git rule.
