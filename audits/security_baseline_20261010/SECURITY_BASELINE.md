# Melange Security Baseline — 2026-10-10

**Scope:** the Melange Systems repo (`C:\Users\pgoff\OneDrive\Desktop\Melange Systems`) and the Mentat worktree (`C:\Users\pgoff\Mentat`, a linked worktree of the same git repo).
**Requirements reference:** OWASP ASVS 4.0.3. The target is Level 2 for the components that exist; most authentication and session chapters do not apply. The requirement IDs were cited from memory and should be checked against the official text.
**Brain record:** D-140, "Security baseline adopted 2026-10-10".

This document records what was verified. It is not a compliance claim, and the system is not "fully secure."

---

## 1. Executive summary

- **Framework:** there is no Django, Flask, FastAPI, Shiny or plumber anywhere. Every server is Python's standard-library `http.server`, so all Django and DRF checks (including `check --deploy`) are **not applicable**.
- **System shape:** single user, on a Windows laptop. Work leaves the machine in three ways: a password-locked dashboard uploaded to Netlify by hand, an emailed zip package, and a private GitHub remote.
- **Fixes:** the read-only audit produced 14 findings and operational items. Paul approved fixes P1–P9, which were built in isolated worktrees, reviewed by Opus and landed. An adversarial test campaign of about 7,300 hostile cases then found **no bypass** of the landed controls. Its low-severity gaps were also fixed and landed.
- **Dashboard password:** replaced with a random temporary password, stored outside OneDrive and the repo. The dashboard was re-locked, and the password field now hides input.
- **Open items (Paul):** the elevated sentinel scheduled task, the ACL on the password file, the Netlify upload, a history rewrite to purge the old zip, a desk rebuild, sidecar stamping, a backup target, and a pull request for the GitHub security branch.

---

## 2. Architecture and trust boundaries

| Component | Bind | Authentication | Notes |
|---|---|---|---|
| Mentat console `mentat/app/server.py` (8802/8806) | 127.0.0.1 | Per-process token, compared in constant time; Host and Origin checks | Already well built: read-only mode, CSP `frame-ancestors 'none'`, 5 MB upload cap, path guards, DPAPI key store |
| Staffer server `fec/surfaces/staffer_live_server.py` (8841) | 127.0.0.1 | Origin and Sec-Fetch-Site on POST; **Host allowlist added** | Restarted 2026-10-10 (PID 38776) |
| Glass Box `fec/surfaces/glassbox_app_server.py` (8823) | 127.0.0.1 only | Shutdown token; **Host allowlist plus generic 500 added** | Not running at restart time |
| Press monitor `fec/collect/press_recovery_monitor.py` (8876) | 127.0.0.1 | **Host allowlist added** (file is untracked) | Not running at restart time |
| Preview `.claude/launch.json` (8802) | **now 127.0.0.1** (was all interfaces) | none | Fixed in P1 |

**Data classes:**
- Public-source: FEC, LDA, congress.gov, govinfo, hearings.
- Proprietary analysis: rankings, forecasts.
- Personal data: staffer names, employment and co-tenure; social media; audio of public figures.
- Confidential client data: Mentat workbooks. Eighteen workbook paths remain in git history.

**Untrusted inputs:** scraped news, press and social text and URLs; C-SPAN media URLs; FEC donor free-text fields (employer, occupation); bill text sent to LLM prompts; imported JSON in the member desk.

**AI components:** several `claude -p` callers. Their output is JSON checked against a schema and is never executed. All callers are now locked down (P5).

---

## 3. Review coverage and limitations

**Inspected:**
- All server entry points, request handlers and launchers.
- Git hooks, remotes and tracked files.
- Repo-wide searches for command execution, eval and deserialization, SQL building, URL fetching, XSS sinks, archives, spreadsheet writers, TLS settings and LLM callers.
- A secret-pattern scan of all 43,558 tracked files, which was clean.
- All path names in git history, which were clean.
- Dependency manifests, scheduled tasks (read-only), and Glass Box and refresh logs, which were clean.

**Not assessed:**
- Whether the GitHub repo is private. A memory note says it is; this was not verified live.
- Windows Firewall rules, and disk encryption (needs elevation).
- A content scan of git history. It was killed after 540 seconds and is inconclusive.
- The Claude transcripts (11.6 GB). The scan was inconclusive.
- `pip-audit` or OSV advisory scans, which were **not run** because they need network access.
- Live C-SPAN HLS downloads with the new ffmpeg whitelist.
- In-browser execution of the XSS vectors. Headless Chrome hung; the render fragments were covered with bun instead.

**Accepted risk (Paul's standing ruling):** the free api.data.gov FEC and govinfo keys are not treated as findings.

---

## 4. Findings and status

| ID | Severity | Finding | Status |
|---|---|---|---|
| H-1 | High if public, Medium if private | Unlocked `data/money/Moneyball_email.zip` (90 MB plaintext dashboard) was tracked and pushed | **IMPLEMENTED:** untracked in `abec38cd4` and ignored via `.gitignore`. Old blobs remain in history and on GitHub's default branch until the history rewrite or merge. **Paul decides.** |
| H-2 | Medium-High | `ClaudeSystemSentinel` runs at HighestAvailable using a script the user account can edit (UAC bypass) | **BLOCKED for Claude** (system security setting). Paul must change it; see section 8. |
| M-1 | Medium-High | Stored XSS in the member desk: `esc` did not escape quotes; raw `href` values; imported stance and notes files | **VERIFIED** in the template. Not yet in the shipped desk; **a desk rebuild is needed.** |
| M-2 | Medium | Dashboard password in plaintext in `deploy/DEPLOY.md` next to the ciphertext; password literal in brain `STATE.md` | **VERIFIED:** password rotated, `DEPLOY.md` scrubbed, brain lines redacted. Older brain commits and the mirror still hold the old literal. |
| M-3 | Medium | Preview `http.server` bound to all interfaces, serving the whole repo | **VERIFIED:** `--bind 127.0.0.1` |
| M-4 | Medium | Spreadsheet formula injection in the Mentat tidy workbook (FEC employer and occupation) | **VERIFIED:** formula-leading strings forced to text |
| M-5 | Low now, Medium when enabled | SMTP STARTTLS did not verify the certificate | **VERIFIED:** `ssl.create_default_context()` |
| L-1 | Low-Medium | Claude CLI caller with no tool lockdown, fed untrusted bill text | **VERIFIED:** lockdown flags plus a temp working directory |
| L-2 | Low-Medium | No Host check, leaving a DNS-rebinding read path on 8841, 8823 and 8876 | **VERIFIED:** Host allowlist; 8841 confirmed live (foreign Host gives 403, normal request gives 200) |
| L-3 | Low | Pickle and joblib loads before any integrity check | **VERIFIED:** sha256 sidecar checked before unpickling. An absent sidecar warns and loads (design limit). `fec/research/universe_verify.py:208` is skipped because sealed hashes pin it. |
| L-4 | Low | Press-text fetcher accepted any scheme or host (`file://`, internal addresses) | **VERIFIED:** public addresses only, every redirect re-checked, NAT64 and 6to4 decoded |
| L-5 | Low | `javascript:` links in the longform review app; ffmpeg would follow any protocol; FEC export URL unchecked; output-directory check matched by prefix only | **VERIFIED** (the FEC export check is https-only with no host pin, because openFEC returns presigned S3 URLs) |
| L-6 | Low | Anthropic key stored in plaintext in an OneDrive folder (gitignored) | **OPEN:** Paul's call |
| OPS-1 | High availability impact | No durable backup of 46.9 GiB of data; no restore procedure | **OPEN:** Paul's call |
| OPS-2 | Low | No `renv.lock`; no dependency hashes; no CI; Python 3.12.10 behind on patches | **OPEN** |
| — | Info | Plain-text password field on the lock page | **VERIFIED:** now `type=password` |
| — | Info | AppContainer SID has full control of `%LOCALAPPDATA%\Melange` | **OPEN:** Paul's call; see section 8 |

---

## 5. Security baseline matrix

| Control | Applies? | Required state | Enforced at | Verification | Status |
|---|---|---|---|---|---|
| Output encoding (V5.3.3) | Yes | Quote-safe escaping; http(s)-only links | Desk template | 6,007-case fuzz plus bun render tests | VERIFIED (template) |
| Untrusted deserialization (V5.5.3) | Yes | Hash checked before load | `lane_file_io` helper | Tripwire tests (40 cases) | VERIFIED |
| Outbound request allowlist / SSRF (V12.6.1) | Yes | Scheme plus public-host allowlist | `fetch_press_text`, R guards | 145 SSRF cases, 188 R cases | VERIFIED |
| Outbound TLS (V9.2.1) | Yes | Verified context | `refresh_email` | Mocked SMTP | VERIFIED |
| Secrets not in source (V2.10.4) | Yes | No plaintext password near the artifact | `deploy/`, brain | Leak scan | VERIFIED (current files) |
| Formula injection (V5 output encoding) | Yes | Neutralise leading `= + - @ \t \r` | Mentat writer | 67-case round trip | VERIFIED |
| Local service exposure (V14) | Yes | Loopback bind plus Host allowlist | Launchers, servers | 741 Host cases plus a live check | VERIFIED |
| LLM tool privilege | Yes | Tool-free, isolated working directory | CLI argv | argv tests | VERIFIED |
| Data protection (V8) | Yes | Unlocked artifacts never in git | `.gitignore`, git index | `git ls-files` | IMPLEMENTED (history still holds old blobs) |
| Dependency inventory and patching (V14.2) | Yes | Locked and audited dependencies | Manifests | `pip-audit` | NOT ASSESSED |
| Backup and restore | Yes | Off-disk backup | Infrastructure | Restore drill | NOT ASSESSED |
| Django settings, `check --deploy`, DRF | No | — | — | — | NOT APPLICABLE |
| Server authentication, sessions, MFA, tenants (V2, V3, V4) | Mostly no | — | — | — | NOT APPLICABLE |

---

## 6. What landed

**Melange (`main`, local; never pushed as `main`):**

| Commit | Content |
|---|---|
| `6de7ed180` | P1 loopback preview bind; P9 `.gitignore`; P2 desk XSS; P4 SMTP TLS; P5 CLI lockdown; P6 Host allowlist and generic 500; P7 sha256 sidecar; P8 SSRF and link guards; manifest cite update |
| `16b214d38` | SSRF gap fix: `_is_public`, which rejects multicast, reserved and site-local addresses and decodes NAT64 and 6to4 |
| `23ed9b836` | Sidecar guards on 6 `fec/research` unpickles |
| `963cf59ef` | Lock page `type=password` |
| `abec38cd4` | Untrack `data/money/Moneyball_email.zip` |

**Mentat (`codex/mentat-crypto`, pushed to origin):**
- `0ea51d6d6`: formula guard
- `726e6fdba` and `23d33bfe8`: C-SPAN URL guard and ffmpeg protocol whitelist
- `c752f7bf6` then `a5e88ff08`: FEC export URL, https-only
- `95646bcbf`: rejection of non-ASCII URLs

**GitHub:**
- Branch `security/baseline-2026-10-10` holds the five Melange commits, cherry-picked onto origin's default branch. 185 tests pass on it. No pull request has been opened.
- `codex/mentat-crypto` is fast-forwarded to `95646bcbf`.
- A secret scan before the push found only two benign test constants, and no hit for the password file.

**Dashboard lock:**
- **Password:** 24 random characters (about 141 bits), stored at `%LOCALAPPDATA%\Melange\dashboard_password.txt`.
- **`deploy/index.html`:** re-locked (148,146,438 bytes, sha256 `0ec50c58…832434`). It decrypts to bytes identical to `Moneyball.html`. Wrong and tampered inputs fail. PBKDF2-SHA256 with 250,000 iterations, a 16-byte salt and a 12-byte GCM IV.
- **Netlify:** **not yet uploaded**. The live site keeps the old password until Paul uploads the new file.

---

## 7. Test evidence

| Suite | Result |
|---|---|
| Targeted pytest after landing (Melange) | 135 passed, 31 subtests; plus 50 SSRF tests; plus 48 sidecar and lock tests |
| Node desk tests (`test_desk_cook_pvi`, `test_member_desk_honors`, `test_desk_overlays_r5`) | 26 passed, 0 failed |
| Mentat: `test_tidy_workbook.py`, `test_fec_page.R`, `test_cspan_media_url.R` | 25 passed plus 100 subtests; PASS; PASS |
| Kernel runner `fec/tests/run_tests.py` | 276 passed, 1 failed. The failure is `test_per_area_board`, caused by stale `sentinel_admissions.json` and unrelated to these changes. |
| Adversarial campaign (`scratchpad\sectest\`) | About 7,300 cases, 0 bypasses. The low gaps it found were fixed: SSRF 121/122 (the one remaining admit is a non-exploitable URL-parser quirk); R guards 188/188 |
| Lock crypto verification | 24/25; the one failure, the text field, has since been fixed |
| Not run | `test_staffer_live_server_concurrency.py` (burst load, prohibited); `pip-audit`; live C-SPAN; in-browser XSS execution |

Passing tests and scanners are supporting evidence, not proof of security.

---

## 8. Actions for Paul

1. **Sentinel task (H-2).** Run in an **elevated** PowerShell:
   ```powershell
   $t = Get-ScheduledTask -TaskName ClaudeSystemSentinel; $t.Principal.RunLevel = 'Limited'; Set-ScheduledTask -InputObject $t
   ```
2. **Password file ACL.** Run in an **elevated** PowerShell:
   ```powershell
   icacls "$env:LOCALAPPDATA\Melange\dashboard_password.txt" /inheritance:r /grant:r "${env:USERNAME}:F" "SYSTEM:F"
   ```
3. **Netlify.** Upload the new `deploy\index.html` (148 MB; check the size limit).
4. **GitHub.** Open and merge a pull request for `security/baseline-2026-10-10`. Until then, the default branch still contains the unlocked zip. Then decide whether to rewrite history to purge it.
5. **Desk rebuild.** Needed so the XSS fixes reach the shipped dashboard. Re-lock afterwards.
6. **Restarts.** Start Glass Box (8823) and the press monitor (8876) whenever needed; they load the guards on start.
7. **Sidecars.** Stamp sha256 sidecars for the current models, or accept warn-and-load. Note that restoring the tracked joblib from git without its sidecar would trigger a retrain.
8. **Backups.** Choose an off-disk target for the databases, workbooks and audio, and run a restore drill.
9. **Dependencies.** Add an `renv.lock`, and approve a `pip-audit`/OSV run (it sends package names and versions to PyPA/OSV).
10. **Brain history.** Older brain commits and the mirror still contain the old probe-lock password literal.

## 9. Release gates

Do not share a new dashboard build until all of the following hold:
- H-1 is resolved, or the repo is confirmed private and Paul accepts the risk.
- The desk has been rebuilt with the XSS fixes and re-locked.
- The new password is in use on Netlify.

Only Paul can accept residual risk.

## 10. Rollback

| Change | Command |
|---|---|
| Melange P1–P9 | `git revert --no-edit 6de7ed180`, then remove the press-monitor guard and its untracked test by hand |
| SSRF gaps | `git revert --no-edit 16b214d38` |
| Research guards | `git revert 23ed9b836` |
| Lock page | `git revert 963cf59ef`, then restore `index.html` from `scratchpad\relock_backup_20261010b\` |
| Zip untrack | `git add -f data/money/Moneyball_email.zip` and commit |
| Mentat | `git -C C:\Users\pgoff\Mentat reset --keep dedad2a5f` (all security commits) |
| Password and first re-lock | Restore `deploy\` from `scratchpad\relock_backup_20261010\` and delete the password file |

Worktrees left in place: `C:\Users\pgoff\worktrees\` (melange-sec-a, melange-sec-b, mentat-sec, melange-ssrf, mentat-unicode, melange-followups, melange-push).
