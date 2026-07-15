# In-use production files

This folder is the index for the live Moneyball system. Canonical files remain at their existing
paths because pipeline scripts use those paths directly; duplicating them here would create two
competing sources of truth. `active_manifest.json` identifies the current entrypoints, rule sources,
primary inputs, and generated dashboard artifacts.

Historical snapshots, canceled runs, and obsolete scratch artifacts are physically stored under
`../orphan/` with their original names recorded in that folder's manifest.
