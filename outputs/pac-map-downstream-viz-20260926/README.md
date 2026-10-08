# Commit plan for the uncommitted Mentat work (PAC map downstream + viz lanes, 2026-09-26)

This folder holds everything needed to commit the work the 09-20..09-26 sessions left uncommitted in
`C:\Users\pgoff\Mentat` (branch `codex/mentat-crypto`, currently at `3cec98524`): 633 files in six commits.
Lanes Z and T built the six commits in throwaway copies, tested every one of them on a clean export, and
rehearsed both ways of applying them. Nothing has been committed in your checkout. The commits are yours to make.

## The six commits

| # | Subject | Files |
| --- | --- | --- |
| Z1 | Record the 09-20..09-25 Chart Studio, query and palette work left uncommitted | 35 |
| Z2 | Give Chart Studio Tableau-style marks cards (Marks v3, boards #50-#52) | 19 |
| Z3 | Build geo v2 map layers from the Census files with GeoPandas | 464 |
| Z4 | Stage the previous cycle's FEC files only for the cycles a run selects | 2 |
| Z5 | Trace PAC money downstream, draw it as Sankey flows and layered maps | 118 |
| Z6 | Launch Mentat's venv Python as one process (bpo-35797) | 15 |

Make all six. Z5 and Z6 belong together: the venv change is split across them, and between the two the
launcher still starts the venv's Python as two processes.

## How to apply (PowerShell)

1. **Check first. This changes nothing.**

   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\pgoff\Mentat\outputs\pac-map-downstream-viz-20260926\apply_plan.ps1
   ```

   Every line should start with `OK`, and the last line should say `Checks passed`. A `FAIL` line means
   something moved since the plan was tested (it names what). The usual cause is a session editing one of the
   633 files after 09-26. Stop there: the plan has to be regenerated, because the commits would no longer
   hold what is on disk.

2. **Make the commits.** Run the same command with `-Execute` at the end:

   ```
   powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\pgoff\Mentat\outputs\pac-map-downstream-viz-20260926\apply_plan.ps1 -Execute
   ```

   It makes the six commits under your name with the messages in `messages\`, moves the branch to the last
   one, and changes one file on disk: `mentat/app/geo/.gitignore` gets three ignore rules (with a short
   comment) for the geo v2 bulk tiers. No other file on disk is touched. The check refuses if that file has
   been edited, so nothing in it can be overwritten. This route skips your git hooks, so push the mirror yourself:

   ```
   git -C C:\Users\pgoff\Mentat push mirror codex/mentat-crypto
   ```

3. **Confirm.** `git -C C:\Users\pgoff\Mentat log --oneline -7` lists the six commits above `3cec98524`.
   The script's last `OK` line says that nothing under `mentat/` or `audits/mentat_failings_20260915/contracts`
   is left uncommitted. Untracked folders that belong to other work (other `outputs/` folders, other `audits/`
   packets, `sector_growth_study/`, this folder) are not part of the plan, so they stay untracked.

**The other route.** `apply_plan_porcelain.ps1` makes the same six commits with an ordinary `git add` and
`git commit` for each one, so your post-commit hook pushes the mirror after every commit. You use it the same
way: check first, then `-Execute`. It checks every commit's tree against the tested tree and stops if one
differs. Use only one of the two scripts.

**To undo** after committing and before pushing, run these two commands. They move the branch back and put
the geo ignore file back the way it was, and leave every other file on disk as it is:

```
git -C C:\Users\pgoff\Mentat reset --mixed 3cec985249b098478868b8729e33b5b4ab31752e
git -C C:\Users\pgoff\Mentat checkout -- mentat/app/geo/.gitignore
```

## What you are asked to rule on

The commits record several decisions that are still yours. `COMMIT_PLAN.md` section 5.4 lists the test
expectations that changed (re-pins), and section 5.5 lists what is recorded but not yet ratified.

## What is in this folder

- `apply_plan.ps1`, `apply_plan_porcelain.ps1`: the two routes. Both only check unless you add `-Execute`.
  They read everything from this folder, so they work from wherever the folder is.
- `zPlan.bundle`: the six tested commits. The scripts take the tested trees and file contents from it.
- `messages\Z1.txt` .. `Z6.txt`: the commit messages.
- `commit_set.json`: the 633 files, each with the sha256 it had when tested. The check compares them.
- `plan_trees.txt`, `plan_paths_*.nul`, `plan_add_*.nul`, `plan_cacheinfo_*.txt`, `paths.nul`: the file lists
  for each commit, and for the single-commit fallback described in `COMMIT_PLAN.md` section 5.2.
- `plan_states.zip`: the exact bytes each commit stages, for review. The scripts do not use it.
- `COMMIT_PLAN.md`: the full plan, the test results and the open items.
- `lanes\`: every lane's receipt and progress notes (`RECEIPT.json` and `PROGRESS.md`, or what that lane kept).

A note on git: the root `.gitignore` hides `*.json`, `*.txt` and `*.jsonl` here, and the scripts need some of
those files. If you ever commit this folder as a lane packet, add it with `git add -f`.
