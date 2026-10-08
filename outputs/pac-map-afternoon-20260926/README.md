# Commit kit for the 09-26 afternoon Mentat work (lanes J2, J3, S2, L2, L3)

This folder holds everything needed to commit the work the 09-26 afternoon lanes left uncommitted in
`C:\Users\pgoff\Mentat` (branch `codex/mentat-crypto`, at `fadd2c751`, the morning's Z6): 75 files in three
commits. Lane V2 built the three commits in a throwaway clone from the bytes on disk, tested the result on a
clean export, and rehearsed the apply on a copy set up like your checkout. Nothing has been committed in your
checkout. The commits are yours to make.

## The three commits

| # | Subject | Lanes | Files |
| --- | --- | --- | --- |
| C7 | Count money unless it is proven counted twice | J2, J3 (+ L2's METHODOLOGY header line) | 19 |
| C8 | Name split workbook sheets by election year | S2 | 7 |
| C9 | Fix the Alaska and Hawaii map insets, the busy canvas and test temp folders | L2, L3, J3's two browser-suite cleanups | 49 |

C7 holds both lanes' edits to `inputs/fec_receipt_rules.json`, so "v7" names one file in history. The
full messages are in `messages\`.

## How to apply (PowerShell)

1. **Check first. This changes nothing.**

   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\pgoff\Mentat\outputs\pac-map-afternoon-20260926\apply_plan.ps1
   ```

   Every line should start with `OK`, and the last line should say `Checks passed`. A `FAIL` line means
   something moved since the plan was tested, and it names what. The usual cause is a session editing one
   of the 75 files after lane V2 tested them. Stop there: the plan has to be rebuilt, because the commits
   would no longer hold what is on disk. A `NOTE` line lists changed files under `mentat/` that are not in
   this plan; they are left alone and stay uncommitted.

2. **Make the commits.** Run the same command with `-Execute` at the end:

   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\pgoff\Mentat\outputs\pac-map-afternoon-20260926\apply_plan.ps1 -Execute
   ```

   It makes the three commits under your name with the messages in `messages\`, moves the branch to the
   last one and sets the index to it. It uses git's plumbing commands (`commit-tree`, `update-ref`,
   `read-tree`), so it writes no file in your working tree and runs none of your git hooks. Push the
   mirror yourself afterwards:

   ```
   git -C C:\Users\pgoff\Mentat push mirror codex/mentat-crypto
   ```

3. **Confirm.** `git -C C:\Users\pgoff\Mentat log --oneline -4` lists the three commits above `fadd2c751`.
   The script's last `OK` line says that nothing under `mentat/` or `audits/mentat_failings_20260915/contracts`
   is left uncommitted.

## To undo

After committing and before pushing, this one command moves the branch back to `fadd2c751` and resets the
index. It leaves every file on disk as it is, so the 75 files show as uncommitted again:

```
git -C C:\Users\pgoff\Mentat reset --mixed fadd2c751e1936c8924cab8c060d28f54837909b
```

Nothing else needs restoring: the apply wrote no file in the working tree. If you have already pushed the
mirror, the mirror's branch still names the three commits after this reset; moving it back needs a force
push, which is your call.

## What you are asked to rule on

- C7 re-pins (test expectations that changed), listed in its message: receipt rules 6 -> 7; the
  back-reference proof pair at the same amount; MEMO_DRIFT's removal flag 1 -> 0; NON-CONTRIBUTION from
  other_receipt to unverified_other_receipt; the memo harnesses' negative controls; memo fixture version
  1 -> 3; flow contract 4 -> 5.
- C8 re-pin: the split-sheet names `Contributions 2022` / `Contributions 2024`.
- C9 re-pins: the NWHI test in `test_state_legislative_geo.py` (clipped, not off-canvas rings); the
  reference projections in `test_district_geo.py` and `test_zip_centroids.py` wrap longitude.
- Open decisions carried in the messages: the Hawaii clip extent `(247, 497, 371, 610)` instead of the
  layout box (lane L3); whether METHODOLOGY becomes Version 6 (lane L2 kept Version 5).
- Measured, not changed (lane V2): the caption "NON-CONTRIBUTION AMOUNT", which lane J3 left excluded, is
  on no receipt description in the eight industry databases, but it is the memo text of 241 Banking rows
  ($4,420.00; FEC type 10, Form 3X line 17, all to Progressive Turnout Project), which the committed rules
  exclude. Details in `lanes\laneV2\PROGRESS.md`, section 5.

## What is in this folder

- `apply_plan.ps1`: check mode by default; `-Execute` makes the three commits. It reads everything from
  this folder, so it works from wherever the folder is.
- `cPlan.bundle`: the three tested commits (requires `fadd2c751`). The script takes the tested trees from it.
- `messages\C7.txt` .. `C9.txt`: the commit messages.
- `commit_set.json`: the 75 files, each with the sha256 it had when tested, its commit, and its blob; the
  base, the tested commits and their trees. The check compares every file against it.
- `plan_trees.txt`, `paths_C7.nul`, `paths_C8.nul`, `paths_C9.nul`: each commit's tree and file list.
- `lanes\`: the receipts and progress notes of lanes J2, J3, S2, L2, L3 and V2 (`RECEIPT.json`,
  `PROGRESS.md`). Lane V2's test results are in its PROGRESS.md.
- `MANIFEST.sha256`: the sha256 of every other file here.

A note on git: the root `.gitignore` hides `*.json` and `*.txt` here, and the script needs some of those
files. If you ever commit this folder as a lane packet, add it with `git add -f`.
