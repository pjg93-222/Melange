# Compute operations skills

This index covers only the three compute skills and their shared references below.
It does not imply that any other private or locally installed skill is published.

| Skill | Scope |
|---|---|
| [Melange chain compute](melange-chain-compute/SKILL.md) | Chain, collector replay, office parity and controlled engine changes |
| [Mentat compute and money](mentat-compute-and-money/SKILL.md) | Compute-job parity and bounded money record/replay evidence |
| [Terrier compute](terrier-compute/SKILL.md) | Isolated district builds, bundle identity and controlled data installation |
| [Shared operating scope](ops-shared/chain-of-command.md) | Authorization, ownership and canonical source destinations |

Prepared 2026-10-16 from the compute documentation in source commit
`6df9422a6366f89143489b2eea2902b97a632142` (2026-10-14). Historical rulings,
run results and machine settings are context, not new permission or current state.
This publication does not establish completion of any unfinished compute cutover.

Current application source destinations, verified for the 2026-10-16 release work:

| Application | Canonical GitHub source | Integration rule |
|---|---|---|
| Melange | `pjg93-222/Melange`, `main` | Existing filtered publication route; do not push raw shared history |
| Mentat | `pjg93-222/Mentat`, `main` | Existing filtered publication route; preserve unfinished local work |
| Terrier | `pjg93-222/Geo`, `main` | Verify the owning checkout and selected committed inputs |

Recheck destination and full source SHA before later publication. Local compute
branches, image build refs, release tags and app-source main are different inputs.
These skills do not select or trigger an Electron release, installer rebuild,
collector, scheduled task or container migration. Native desktop runtimes do not
acquire a Docker requirement merely because these compute procedures exist.

The seven separately reviewed published skill exceptions are outside this
index. Preserve their existing provenance and redactions. The exporter does
not automatically carry `.claude/skills` forward; additions need an explicit
reviewed path inventory, not a blanket `.claude/` export.

Start with the shared [accuracy](ops-shared/accuracy.md),
[capacity](ops-shared/efficiency.md), [host](ops-shared/host.md) and
[records](ops-shared/records.md) references. The state scripts require an explicit
absolute `-Repo` path and inspect metadata only. They are not readiness certificates.
Dirty/staged/untracked state is explicitly unverified: no `git status` or content
filter runs. Only directly local roots with a direct `.git` directory are supported;
linked-worktree/gitfile routes, unsafe ancestors and config includes/extensions are
refused rather than followed. Validation limits are recorded in the
repository's `SOURCE_PROVENANCE.json`.
