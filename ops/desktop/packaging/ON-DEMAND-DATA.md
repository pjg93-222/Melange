# Melange public pages

The optional `melange.public-data.pages.v1` launch contract consumes the
`melange.official-payroll-pages.v1` module. Its signed module contains only
`index` (at most 2 MiB) and `receipt` (at most 1 MiB). The receipt retains the
whole original projection hash, provenance and record counts. The index binds
immutable, content-addressed NDJSON pages to that receipt, release and catalogue
generation. The publisher must finish and verify every page before advertising
the signed index.

`payroll_pages_publish.py` builds a new sealed staging directory from the
completed observations and receipt. It checks every row, ordering, counts and
whole-stream hash before writing `publication.json`. A failed build leaves no
complete seal. `demand_publish.py` uploads only the seal's exact asset inventory
and downloads every uploaded asset again to verify it before publishing the
prerelease. It refuses clobbering or adopting another release.

Build Melange with `DESKTOP_PUBLIC_DATA_MODE=paged-v1` only when a matching signed
catalogue is prepared at the distinct fixed GitHub pointer
`docs/desktop-data/on-demand-current.json`. The ordinary build retains
`melange.public-data.v1` and `docs/desktop-data/current.json`; neither pointer is
changed by these build flags. Updating the installed program inventory and
signing the matching catalogue are required release steps. Run
`python refresh_module_inventory.py --app melange --write` after reviewed source
changes, and run it without `--write` to check drift. In a split repository,
preserve the other app's declaration with `--app`.

The existing `/api/public-data/catalogue`, `/provenance`, and `/observations`
responses are preserved. Catalogue/provenance and native startup probes perform
no page downloads. Observations select only pages overlapping the requested
source, offset and limit (maximum 200 rows). Every fetched page is SHA-256 checked
and every row is validated before the response is returned. Cached pages work
offline. Uncached offline requests fail rather than returning invented or
partial rows.

Page bodies live in the native module cache's dedicated `pages` directory, with
a default 1 GiB cap. Temporary downloads count against the same cap; LRU eviction
affects only this owned cache. A cross-process lease protects reads from eviction.
Small signed metadata and existing legacy module storage are separate. This
implementation never deletes existing user data or previously installed module
generations. Legacy whole-snapshot data can be retired only after the new client
and matching signed release have been deployed and verified.

This module covers official payroll source observations. It does not claim to
provide all Melange compiled graph/dashboard inputs. A full application export
must separately inventory and wire those inputs; their absence cannot be treated
as a successful whole-app migration.
