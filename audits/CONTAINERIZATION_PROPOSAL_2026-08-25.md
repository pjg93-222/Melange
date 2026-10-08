# Melange Containment — containerization + guarded-archive proposal
Date: 2026-08-25
Lane: claude/melange-containerization-55a7d3
Status: PROPOSAL ONLY — nothing applied. Every phase below is individually Paul-gated.
Basis: brain boot 2026-08-25 (STATE @2026-08-19 header, entries through 2026-08-24); three read-only
scout sweeps this session (footprint, secrets/runtime touchpoints, build-and-env + architecture-contract
skills). Scouted numbers below are labeled measured-this-session; the flagged unknowns in §8 were NOT
re-verified and are execution items, not facts.

## 0. The ask and the reading

Paul: "Propose a method by which the melange system, all its data, workflows, updates, functions, and
current capabilities, are containerized and secure in an accessible yet guarded format."

Reading: this generalizes the 2026-08-23 email-package lane (Paul: "a compartmentalized version of the
melange system that can be sent over emails") from the 9 surfaces to the WHOLE system — code, data
planes, workflows, automation, secrets, and the ability to bring it all back. The design reuses the
primitives that lane and the wider repo already proved: deterministic zips (FIXED_ZIP_TIME / FFD),
sha256 manifests, PBKDF2(250k)+AES-256-GCM envelopes (lock_dashboard.py), and byte-identity as the
acceptance currency.

## 1. What the system physically is (measured this session)

| Store | Where | Size | Class |
|---|---|---|---|
| Git repo (code + docs) | live tree on OneDrive | pack 3.39 GiB, 198 local branches | mirrored (see §8 gaps) |
| In-tree data plane (gitignored) | data\ + root artifacts | data\ ~180 MB; workbook; root JSONs | mixed source/derived |
| Deployed surfaces | repo root | ~168 MB (index 61.4, Moneyball 46.1, profiles.js 37.6, desk 3.0, lobby family) | derived (regenerable) |
| backups\ | live tree | ~2.9 GiB | mixed; triage list for Paul |
| tmp\ + orphan\ | live tree | ~1.4 GiB | triage list for Paul |
| C:\melange-data | off-repo | BICAM extracted ~44.7 GiB (zips pinned); audio ~20 GiB (npr 6.9 + sunday 12.5 + pilot 0.7) | snapshot / collected |
| %LOCALAPPDATA%\Melange | off-repo | lda_rebuild\raw 74 files / 10.5 MB as measured (§8 verify vs the 55,195-measure census) | source cache |
| External repos | C:\Users\pgoff\Mentat (R), Desktop\Draft Systems (R scraper + adjudicated CU universe) | not sized | IRREPLACEABLE (universe) |
| Glassbox runtime | ~\.claude\glassbox | 12 .ps1, 194 KB, UNTRACKED, single-disk | ops (open brain question) |
| Automation | ClaudeSystemSentinel + MoneyballWeeklyRefresh scheduled tasks; launch.json 8801/8802 | — | ops |
| Secrets | fec\anthropic_key.txt (109 B), fec\govinfo_key.txt (40 B); DEPLOY.md password | — | SECRET |

Runtime: Python 3.12.10, requirements.txt canonical (openpyxl/pandas/numpy/networkx/scipy/sklearn +
anthropic + cryptography + optional torch stack + pywin32 for Excel COM). No R inside the repo — R is
entirely external (Mentat, Draft Systems). No ports were listening at scan time; both preview servers
are localhost-only definitions.

## 2. Design principles (derived from standing law, not invented)

1. **Byte-identity is the acceptance test.** A containerized chain is accepted only when it reproduces
   ranks_python.json / dashboard_data.json / bipartisan.json byte-identical to the host chain at the
   same SHA and inputs (SEED=7/MC=20 determinism makes this a fair bar). "It runs" proves nothing.
2. **The container boundary follows the real coupling boundary.** Excel COM (formula-cache revival,
   522-rank guard), Chrome cookie-replay (congress.gov 403 wall), OneDrive sync, Defender, and the
   glassbox PowerShell runtime are host-side by nature and stay host-side, enumerated — not wished away.
3. **Data classes get different treatments.** build-and-env already defines irreplaceable vs
   regenerable; the vault follows that classification instead of inventing one.
4. **Reuse proven primitives.** lock_dashboard crypto, email-package deterministic zips, ENV-4 sha256
   baselines, artifact_freshness.py.
5. **Import == execution.** The image build must never import producer modules (three unintended
   production writes in one lane prove why). Build = pip install + file copy only.
6. **Observability cannot assume hooks** (DE-005: the settings.json hook mirror is dead). Glassbox
   emission stays transcript-/process-derived and host-side.

## 3. The method — five layers

### Layer 1 — System Manifest (foundation; read-only)
A machine-readable inventory covering every store in §1: path, class (SOURCE / SNAPSHOT / DERIVED /
SECRET / OPS), sha256 or content-hash recipe, producer, consumers, restore route, and cadence. Emitted
as JSON + a human doc; a new audit_full section asserts manifest-vs-disk agreement (registration is a
code change → gate). This is "all its data, workflows, functions" made explicit and checkable.

### Layer 2 — Engine container (compute)
- OCI image `melange-engine`: FROM python:3.12-slim pinned to 3.12.10, requirements.txt installed and
  freeze-pinned at build, repo checked out at a tagged SHA with core.autocrlf=false (byte fidelity).
- The data plane is NEVER baked into the image. It mounts at run time; `MONEYBALL_ROOT` points at the
  mount — paths.py already supports exactly this, so the system is accidentally container-ready.
- Secrets injected at run (env), never in the image or its layers.
- Runs containerized: run_pipeline.py chain, kernel gate, audit_full, surface producers, most
  collectors (outbound-only egress with an allowlist: congress.gov, govinfo, api.anthropic.com, X API —
  an egress control that is cheap in-container and effectively unavailable on the host today).
- Stays host-side (enumerated): Excel COM workbook rebuild + formula-cache revival; httr/Chrome
  cookie-replay fetches; real-browser verification; OneDrive; glassbox; scheduled tasks (they can
  invoke `docker run` instead of host python once accepted).
- Acceptance: the §2.1 byte-gate. Known honest blocker to disclose up front: the six xlsx producers
  without canonicalizers (build_holistic_base etc., STATE 2026-08-18) are non-reproducible even
  host-to-host; for those the bar is COR-7-style canonical-content-hash, and the recorded option (c)
  hoist (shared canonicalizer) is the enabler if Paul wants full byte coverage.

### Layer 3 — Data vault (all its data, guarded)
Deterministic, sha256-manifested, AES-256-GCM-enveloped archives, tiered:
- **Tier A — SOURCE (irreplaceable):** Draft Systems adjudicated CU universe (17 search templates +
  36-row drop list — the finding says this IS the moat), Quorum vendor exports, votes CSV,
  social_media.db, the workbook, gold labels + preregs, ACU outline docx + registry, MEMBER identity
  fixtures. Cadence: on every ratified merge or weekly, whichever first. Two copies, at least one
  off-box.
- **Tier B — SNAPSHOT (external, already pinned):** BICAM zips (~9 GB; the 44.7 GiB extraction is
  disposable and regenerable from them), audio WAVs (20 GiB, static — archive once, cold), FEC bulk
  zips (already git-tracked).
- **Tier C — DERIVED:** not archived; the restore route is the chain. Exception: the current deployed
  surfaces ride as the email-package zips already built.
- **Tier D — OPS:** the glassbox runtime finally version-controlled (194 KB; recommend its OWN repo
  mirrored beside melange, since the brain notes it is user-scope and the Melange repo may be the wrong
  home — Paul's call), exported scheduled-task XML, requirements freeze, the brain repo.
- backups\ (2.9 GiB) + tmp\ (578 MB) + orphan\ (853 MB): presented as a triage list; nothing deleted
  by this lane.

### Layer 4 — Secrets and guarded access
Findings (reporting-only, per the standing API-key ruling — Paul's box, Paul's call):
- fec\anthropic_key.txt and fec\govinfo_key.txt sit inside the OneDrive-synced tree; five scripts
  open anthropic_key.txt directly, bypassing the env-first helper.
- deploy\DEPLOY.md records the lock password in plaintext at lines 8 and 22, is git-tracked, and the
  repo is mirrored — the password propagates to every clone.
- lock_dashboard.py prints the password to stdout (fine on Paul's console; it also lands in
  transcripts and glassbox-adjacent logs).
Proposal (each gated): move both key files to a non-synced, non-repo path (e.g.
%USERPROFILE%\.melange\secrets), keep env-first resolution, route the five direct readers through the
shared helper (behavior-neutral edit), rotate both keys after migration; strip the password from
DEPLOY.md and re-lock with a fresh password (rotation is the real fix — git history and the mirror
retain the old one forever).
Access model stays as-is, because it is already right: AES-GCM locked doors + sha256-manifested email
packages for recipients; localhost-only previews; zero inbound exposure. The container adds the
egress allowlist and a no-inbound-ports rule for chain runs.

### Layer 5 — Update flow and the restore drill (proof)
- Update flow: Paul merges → image rebuilt tagged by SHA → containerized gates (kernel, audit_full,
  byte-gate) → vault delta archive. Collectors/weekly refresh keep their cadence, each step labeled
  container-side or host-side.
- **Restore drill** (verify-don't-infer made policy): quarterly, on a scratch environment (fresh WSL
  distro or second machine): clone from mirror @SHA + pull vault archives + run the image → gates
  green + ranks byte-identical ⇒ containment is real. Negative control required: corrupt one archive
  byte and the restore must FAIL on the manifest (fail-closed, or the drill proves nothing).

## 4. What this deliberately does NOT do
- Does not move the live tree off OneDrive (a change to Paul's daily workflow; available as an option
  with tradeoffs if wanted, not proposed).
- Does not containerize Excel, Mentat, or the Draft Systems R scraper — they are vaulted and
  manifested, not imaged. (An r-base image for Mentat is a later option if portability is wanted.)
- Does not touch ranks, press classification, or any data content. Zero behavior change anywhere.

## 5. Phasing and gates
- **Phase 0** — Manifest + resolve §8 unknowns. Read-only except the audit registration.
- **Phase 1** — Tier A vault + glassbox version-control ruling. (Highest value density: 194 KB of
  untracked ps1 plus a few GB of irreplaceables carry most of the extinction risk.)
- **Phase 2** — Engine image + byte-gate acceptance run.
- **Phase 3** — Secrets migration + rotation + DEPLOY.md/relock.
- **Phase 4** — Restore drill + standing cadence.

## 6. Decision points for Paul
1. Full OCI route (Docker Desktop/WSL2 on this box) vs. lockfile-only "logical container" (vault +
   manifest + pinned env, no Docker). Recommendation: OCI — the byte-gate makes it falsifiable, and
   the egress allowlist is a real security gain; the lockfile route is the fallback if Docker/OneDrive
   friction proves ugly.
2. Vault destination(s): what physically backs GitMirrors today, and where the off-box copy lives.
3. Secrets migration + key rotation authorization (Layer 4).
4. Glassbox home: own repo vs. Melange repo.
5. Whether the xlsx canonicalizer hoist (option c) rides along to make Layer 2's byte coverage total.
6. backups\/tmp\/orphan\ triage.

## 7. Governance
Ask-before-apply holds: this document is the presentation; the APPLY step is Paul's gate, per phase.
Brain updated per D-006 with a pointer to this proposal. Relevant dead end honored: DE-005 (no
reliance on settings.json hooks for containerized observability).

## 8. Flagged unknowns (verify in Phase 0 — not asserted as facts)
- social_media.db / hearings_seq.db exact paths (the sweep searched data\, audits\, outputs\ and
  off-repo stores; root/fec were not db-swept — the skills treat social_media.db as real and
  irreplaceable-in-practice).
- Mentat's git remote was read by a scout as pointing at GitMirrors\melange-systems.git — suspicious
  (Mentat sharing the Melange bare repo); verify before relying on Mentat's mirror status.
- lda_rebuild\raw measured 74 files / 10.5 MB vs. the Gate-1 census of 55,195 measures — likely
  zipped strata; verify before vault sizing.
- GitMirrors physical backing (memory says off-box; the path is C:\Users\pgoff\GitMirrors).
- Branch drift: 198 local branches now vs. 174 at the 2026-08-18 full mirror push — re-push policy
  needed.
- X collector: state files last written 2026-08-25, but no scheduled-task trigger found and one scout
  read the directory as empty — reconcile trigger + contents.
