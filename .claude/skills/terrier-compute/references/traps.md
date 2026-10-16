# Terrier compute pitfalls

Prepared 2026-10-16 from the 2026-10-14 findings. Old machine paths, branches,
ports and incident explanations are not current facts.

| Pitfall | Required handling |
|---|---|
| Junction/placeholder path used for Docker input | Resolve an explicit local checkout and validate required files/mounts; do not assume a personal path |
| Historical source/image branch confused with current main | Canonical app source is `pjg93-222/Geo/main`; independently pin selected source and image |
| Stale image notes | Use existing authenticated release/trusted digest configuration, not a documented old tag/digest |
| Shared project-wide timeout cleanup | Never overlap a legacy runner with other users of that label; verify ownership-scoped cleanup before relying on it |
| Missing tmpfs mask mount points | Inspect compose and create only scoped scratch mount points when authorized; do not mount live `.local` writable |
| Untracked local runners | Review exact local bytes and preserve backups; Git cannot restore files it never tracked |
| Missing demo key/walk salt | Fail closed; a replacement re-keys voters and is not an acceptable build repair |
| Voter-derived stage or comparison data | Keep private/local; no upload to pods, hosted CI or third parties; dispose only within current retention scope |
| Server/account-store changes bundled into compute work | Keep separate scope, verified backup, rollback and existing-owner control |
| Host-specific libraries in a step | Keep the supported runtime boundary; don't infer container compatibility |
| Different base/Python/library versions | Record exact image and acceptance evidence; do not borrow another build's proof |
| Old data migration ancestry | Verify current lineage and receipts; never move main backward to satisfy an obsolete handoff |

Existing private operational notes may clarify a historical incident, but are not
publication inputs or instructions to resume a held migration.
