# Melange Containment v2 -- measured
Date: 2026-08-27
Status: SUPERSEDES audits/CONTAINERIZATION_PROPOSAL_2026-08-25.md. That document stands as written
(frozen vintage); this one carries the corrections. Still a PROPOSAL for phases 1-4; Phase 0 executed.

## 0. Why a v2

The 2026-08-25 proposal (v1) was written from the project brain and three read-only scout sweeps --
footprint, secrets/runtime touchpoints, and the build-and-env + architecture-contract skills. That is
a reasonable basis for a first pass, but it is secondhand: brain entries and targeted sweeps report
what was written down or what a narrow search happened to touch, not what is actually on disk.

A five-agent read-only census run on 2026-08-26, with an adversarial cross-check, measured the system
directly -- file counts, byte sizes, `git remote -v`, disk/partition identity, junction-vs-directory
checks -- and CONTRADICTED three load-bearing claims from v1 §1. Those are not rounding errors; each
one changes which store sits in which risk tier, and tier placement is what the whole vault design in
v1 §3 hangs off. This document exists to carry the corrections into the plan rather than leave v1
silently wrong underneath it.

## 1. The three corrections (each measured, each verified more than once)

**THE MIRROR IS ON-BOX.** v1 §1 recorded the git repo as "mirrored (see §8 gaps)" and the project
memory index carries a standing note that the repo mirror is an "off-box bare copy." Both are wrong.
C:\Users\pgoff\GitMirrors sits on the SAME physical disk and partition as the live tree -- one NVMe,
Disk 0, drive C:. It is a plain directory, not a junction or a separate volume. And it sits OUTSIDE
OneDrive, while the live tree sits INSIDE OneDrive's sync scope -- so the mirror is actually the LESS
protected of the two copies, not the disaster-recovery layer the v1 language implied. Four independent
measurements agree on this and the standing memory note is contradicted by all four. Consequence: the
mirror still protects against repo corruption, bad history rewrites, and accidental branch deletion --
those are real and worth keeping. It does not protect against losing the drive, because there is no
drive it does not share.

**MENTAT IS NOT AN EXTERNAL REPO.** v1 §1 lists "External repos: C:\Users\pgoff\Mentat (R), Desktop\
Draft Systems (R scraper + adjudicated CU universe) -- not sized -- IRREPLACEABLE (universe)," treating
both the same way. That conflation was wrong for Mentat specifically. C:\Users\pgoff\Mentat\.git is a
78-byte pointer file, not a repository head -- Mentat is worktree #34 of the Melange repo itself. Its
512 tracked R files are therefore in-repo and already covered by whatever mirrors the Melange repo. The
v1 claim -- external repo, not sized, irreplaceable -- was wrong on all three counts for Mentat. Draft
Systems is unaffected by this correction and keeps its v1 treatment as a genuinely external, genuinely
irreplaceable store (the adjudicated CU universe). What IS actually at risk under Mentat's worktree: 24
modified tracked files sitting uncommitted, and roughly 37 GB of untracked corpus that the repo has
never seen and that no mirror push would carry.

**lda_rebuild IS 320x LARGER THAN RECORDED.** v1 §1 recorded lda_rebuild\raw at "74 files / 10.5 MB as
measured," flagged in v1 §8 as needing verification against a 55,195-measure census figure it could not
reconcile, with a guess in v1 §8 that the mismatch was "likely zipped" strata. The census resolves the
flag: the true figure is 30,050 files across 3.28 GiB. The v1 number came from a non-recursive listing
that counted subdirectories as if they were files and never descended into them. The "likely zipped"
guess was also wrong -- the strata are loose JSON on disk, not archives, so there is no compression step
hiding the size the way the guess assumed.

**Also corrected, lower stakes but load-bearing for vault sizing:** C:\melange-data is approximately 96
GB total, not the ~65 GB v1 §1 implied -- that smaller figure was bicam_snapshot alone, not the whole
store. The BICAM zips live under bicam_snapshot\zips\, not directly under bicam_snapshot\, which matters
for anyone scripting a restore off the v1 path assumption. There are 35 worktrees total (34 linked plus
main), not the 25 a v1-era count implied. There are FOUR credential files, not the two v1 §1 lists (fec\
anthropic_key.txt, fec\govinfo_key.txt) -- two more live under %LOCALAPPDATA%\Melange\lda_rebuild\ and
were missed by the secrets sweep that fed v1 §4. And the glassbox runtime, which v1 §1 and §3 both flag
as "UNTRACKED, single-disk" and recommend giving "its OWN repo... Paul's call," is no longer untracked:
it is already its own clean git repository. Its events/state subtree stays gitignored by design, and its
only remote is the on-box mirror -- so v1's open question about where glassbox should live is answered
for the "has a repo" half, but the single-disk exposure v1 flagged is unchanged.

## 2. The finding that outranks the plan

Independent of all three corrections above, the census surfaced something v1 did not have: there is NO
off-box, non-syncing backup of anything in this system. One physical disk carries all of it. No external
drive is attached, no network share is configured, Windows File History is stopped, and there are zero
restore points. OneDrive covers whatever lives inside its sync scope, but sync is not backup -- a
deletion or a corruption on disk propagates through sync just as faithfully as a good write does.
Roughly 141 GB across this system has no copy anywhere outside Disk 0.

Tiering that 141 GB by what recovery would actually cost, rather than by where it happens to sit, gives
four bands:

- **~6 MB that nothing regenerates:** the glassbox orchestration ledger, the sentinel scripts, hand-
  adjudicated LLM exemplars, the scheduled-task definitions, and roughly 322 KB of acquisition recipes.
  Small, but there is no process anywhere that reproduces it if it is gone.
- **~58 GB unrecoverable in practice:** the Mentat corpus -- whose own collection layer emits silent
  plausible zeros, so even a successful re-collection would not be trustworthy without independent
  verification -- the LobbyView 2024-10-25 vintage, broadcast audio that is actively expiring at its
  source, and a paid LLM classification pass that cost real money to produce once.
- **~77 GB recoverable with time -- but only because of the 322 KB of acquisition recipes, and those
  recipes live in the 6 MB tier above.** This is the sharpest structural fact the census turned up: the
  tier that looks recoverable is recoverable purely as a downstream dependency of the tier that is least
  protected. Lose the recipes and the "recoverable with time" band stops being recoverable.
- **~54 GB pure compute:** the BICAM extraction, which regenerates cleanly from its own zips and carries
  no independent risk.

## 3. What was actually done on 2026-08-26 (Phase 0 + an unplanned rescue)

Phase 0 -- the census itself -- executed read-only. It produced a manifest schema
(melange-system-manifest-v1) and an anti-vacuity audit design; the manifest schema carries a
`confidence` field specifically so that inferences the census could not fully verify stay marked as
inferences rather than hardening into asserted facts over time, the way the v1 §1 numbers did.

Alongside the census, an unplanned three-phase rescue ran the same day, entirely read/copy operations,
every phase hash-verified, nothing moved and nothing deleted from its source location:

- **Phase A** -- 74 of 74 files, 5.74 MB, the tier-0 irreplaceables. This phase produced the first-ever
  file copies of both scheduled-task definitions to exist anywhere outside Task Scheduler's own store.
- **Phase B** -- four corpora compressed from 4.3 GB down to 551 MB (the LobbyView vintage compressed to
  14.4% of its original size, the LDA sweeps to 12.6%).
- **Phase C** -- 2,270 of 2,270 files, 39.0 GiB of audio and BICAM zips, with bicam_amendments.zip
  copied first because it is the one zip in the set with no known acquisition URL to fall back on if it
  were lost.

All three phases landed under backups\offbox_rescue_20260826\ inside the OneDrive-synced live tree,
with three manifests recording what moved and its hashes.

**Still unconfirmed, and load-bearing for whether the rescue accomplished anything:** whether OneDrive
has actually uploaded any of it yet. Quota is not readable from this box, and the 39 GiB the rescue
added landed on top of 255.6 GB already synced. Until upload is confirmed, the rescue phases are three
sets of copies sitting on the same physical disk as their originals -- consistent with §2's finding, not
an exception to it.

## 4. What changes in the plan

- **Layer 3's first job is no longer "build a vault" -- it is get one copy off this machine.** v1 §3
  designed tiered, deterministic, encrypted archives assuming an off-box target already existed (per the
  now-corrected mirror assumption in section 1 above). With that assumption gone, an external drive or a
  non-syncing cloud target is the precondition for Layer 3 to mean anything; the tiering and encryption
  design in v1 §3 is still the right shape for what gets built once a real off-box target exists, but
  sequencing changes: get a copy off-box first, then apply that structure to it.
- **The vault builder should reuse the email lane's deterministic-zip + FFD + manifest machinery**
  (fec/surfaces/make_email_package.py, on the unmerged branch claude/melange-email-compartmentalized-
  8809c0), generalized from the 9 deployed surfaces it currently handles to arbitrary trees -- this is
  the same reuse-proven-primitives principle v1 §2 already commits to, just naming the specific piece to
  extend. Two gaps need closing before it is fit for vault duty: it does not round-trip verify its own
  output today, and its manifest carries no self-hash, so a corrupted manifest would not be caught by
  the manifest itself.
- **`cryptography` is imported by lock_dashboard.py but declared in NO requirements.txt on any branch.**
  This is an undeclared dependency that v1's Layer 2 engine image (§3, "requirements.txt installed and
  freeze-pinned at build") would silently omit, breaking on first use of the lock/unlock path inside a
  container. Fix before Layer 2 proceeds.
- **The cheapest asymmetric win is unchanged from the census and still stands:** commit roughly 322 KB
  of ops scripts, roughly 165 KB of moat material, and roughly 3.1 MB of gold queues into the repo. That
  moves the most irreplaceable material identified in section 2's tiering into something already
  replicated by the existing (on-box, but real) mirror, at negligible cost.

## 5. Open rulings for Paul

(a) Does OneDrive sync count as a second copy for the `single_disk` flag -- this reclassifies roughly 30
rows in the manifest either way; recommendation is to keep `single_disk` strictly physical (disk/
partition identity only) and add a separate `durable_backup:false` flag system-wide, so sync coverage
and off-box coverage stay distinguishable rather than collapsed into one flag. (b) hearings_wit.db (500
MB, no producer found on main, zero known consumers) -- promote to a tracked/vaulted store or retire it.
(c) The 209 MB chrome_debug_profile -- archive-exclude it going forward? (d) Commit the three cheap
durability wins named in section 4? (e) Vault destination, once an actual off-box target exists to point
it at.

## 6. What v1 got right and stands

The five-layer shape, the byte-identity acceptance test, the boundary drawn between containerizable
compute and host-bound coupling (Excel COM, cookie-replay, OneDrive, glassbox), the reuse of the repo's
already-proven primitives, the import-equals-execution discipline for the image build, and the restore
drill with its corrupt-one-byte negative control all hold without modification. None of the three
corrections in section 1 touch the design principles in v1 §2 or the phase structure in v1 §5 -- they
change input numbers and tier placement, not the shape of the plan.

## 7. Provenance

Census run 2026-08-26 by five read-only agents plus an adversarial cross-check; rescue phases A-C
executed the same day. Every figure in this document is measured unless marked otherwise.
