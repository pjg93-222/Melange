# Disk cleanup — September 5, 2026

Recovered **117.20 GB** of net free space (109.15 GiB). C: now has **119.06 GB free** (110.88 GiB).

Removed six inactive worktree copies and four fully merged local branch names. All six commit tips remain reachable from `main`. Small uncommitted and ignored files were archived and their SHA-256 hashes verified before removal. Active worktrees and the live checkout remain intact.

| Removed copy | Recovery archive |
|---|---|
| moneyball-dashboard-simplify-2efa95 | [moneyball-dashboard-simplify-2efa95.zip](<C:/Users/pgoff/AppData/Local/Melange/cleanup/20260905/moneyball-dashboard-simplify-2efa95.zip>) |
| charming-lumiere-27e0e5 | [charming-lumiere-27e0e5.zip](<C:/Users/pgoff/AppData/Local/Melange/cleanup/20260905/charming-lumiere-27e0e5.zip>) |
| melange-containerization-55a7d3 | [melange-containerization-55a7d3.zip](<C:/Users/pgoff/AppData/Local/Melange/cleanup/20260905/melange-containerization-55a7d3.zip>) |
| mystifying-wright-346030 | [mystifying-wright-346030.zip](<C:/Users/pgoff/AppData/Local/Melange/cleanup/20260905/mystifying-wright-346030.zip>) |
| speech-lane-progress-review-db2e9d | [speech-lane-progress-review-db2e9d.zip](<C:/Users/pgoff/AppData/Local/Melange/cleanup/20260905/speech-lane-progress-review-db2e9d.zip>) |
| loving-hugle-6ebcb4 | [loving-hugle-6ebcb4.zip](<C:/Users/pgoff/AppData/Local/Melange/cleanup/20260905/loving-hugle-6ebcb4.zip>) |

The live staffer endpoint is ready with no errors. The protected server, user assertions, pinned graph receipt, and source-exception evidence have unchanged hashes. No system settings or Windows files were changed.

## Recovery

Each ZIP contains `manifest.json`, the saved commit and branch, `staged.patch`, `unstaged.patch`, the original porcelain status, and a `files/` directory containing every retained local file. Recreate a worktree at the saved commit, restore staged and unstaged patches in that order, then copy `files/` into that worktree. The shared Git repository holds all committed files.

Detailed paths, hashes, free-space measurements and preservation checks are in `CLEANUP_RESULT.json`. The discovery and removal logs remain under `tmp/disk_cleanup_20260905/`.
