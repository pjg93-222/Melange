# Shared collection API

The optional broker serves `POST /v1/scrape/query` on the existing recipient
HTTPS listener. It uses the existing native bearer approval and Host/origin
checks. It supports Melange and Mentat approvals; revoked approvals and browser
calls are rejected. The local approval dashboard is unchanged.

The default is disabled. Enable only on the service host, under the publisher
account, after testing the existing HTTPS listener and its enrollment trust.
Set `MELANGE_SCRAPE_BROKER_ENABLED=1` and provide `FEC_API_KEY` and/or
`CONGRESS_API_KEY` in that server process environment. Keys never belong in an
installer, renderer, public repository, data release, request body or client
configuration. No keys are created or exported by this implementation.

The publisher's existing private state directory gains `scrape-broker.sqlite3`.
It stores usage timestamps, principal IDs, leases and provider cooldowns; it
contains no API keys, bearer tokens, request query values or scraped records.
Include this database in the publisher's existing protected backups. Do not
delete it to reset budgets.

Default limits are 120 upstream attempts per principal per rolling hour, 900
attempts globally across both providers per rolling hour, one in-flight request
per principal, and four globally. Override with positive integer server settings
`MELANGE_SCRAPE_PER_PRINCIPAL_HOUR`, `MELANGE_SCRAPE_GLOBAL_HOUR`,
`MELANGE_SCRAPE_PER_PRINCIPAL_CONCURRENT`, and `MELANGE_SCRAPE_GLOBAL_CONCURRENT`.
The global concurrency ceiling is eight to retain access/update worker capacity.
Select budgets within the actual upstream account allowance. Failed attempts
consume budget. Reservations and cooldowns survive service restarts. Abandoned
concurrency leases expire after 120 seconds; upstream reads have a shorter
deadline. `429` responses include the applicable `Retry-After`; clients should
pause, retain completed work, and retry after that interval.

Example request, using the already approved native access token:

```json
{"schemaVersion":1,"provider":"fec","path":"schedules/schedule_a","query":{"committee_id":["C00000001"],"per_page":100}}
```

The response has `schemaVersion`, `provider` and `raw`. The raw envelope has
`status`, allowlisted `headers`, `bodyBase64`, `sha256`, `bytes` and
`originalResponseBytes: true`. It preserves original JSON bytes and decimal
lexemes. The source body is capped at 16 MiB and its wire envelope at 24 MiB.
Congress example: provider `congress`, path `bill/119/hr/1/actions`, query
`{"limit":250}`. Relative endpoint paths and bounded query parameters are the
only caller choices. The server compiles the HTTPS origin, uses GET, inserts the
key into `X-Api-Key`, refuses redirects, and rejects responses reflecting a
shared key (including JSON/URL escapes). It never edits bytes labelled as
original evidence. Errors contain fixed codes. Endpoint inventories come
from the existing FEC money refresh and Congress bill collectors. Additional
paid/credentialed providers require explicit adapters and quota policies.

API-key header behavior is documented by [api.data.gov](https://api.data.gov/docs/developer-manual/);
the Congress endpoint catalogue is [Congress.gov's API](https://api.congress.gov/).
These upstream APIs can change. This source change does not restart or enable
the live service or replace enrollment trust.

Build recipient Melange/Mentat clients with `DESKTOP_SHARED_SCRAPE=1` to package
`desktopScrapeBroker: true`. The normal default stays disabled. The native main
process uses its existing protected access token and pinned HTTPS transport;
neither that token nor API keys cross renderer IPC. Main supplies its backend
an ephemeral `MELANGE_SCRAPE_BROKER_URL` (`http://127.0.0.1:<port>/query`) and
`MELANGE_SCRAPE_BROKER_TOKEN`. This separate local capability expires with the
backend and rejects browser requests. It must never be saved in configuration.

`fec/scrape_client.py` validates this local capability, accepts only the two
official upstream URLs, and verifies returned bytes/hashes. `fetch_raw_url`
returns `(body_bytes, source_status, source_headers)`; `fetch_json_url` parses
those bytes when exact decimal lexemes are unnecessary. Configured shared-mode
errors never fall back to direct keys. Service quota failures raise
`ScrapeBrokerError(status=429, retry_after=...)`.

Melange's `fec/collect/refresh_fec_money.py` and Congress requests from
`fec/legislation/collect_official_rollcall_events.py` use this transport when
the native capability exists. Their original response bytes and existing
normalization remain intact. Ordinary explicitly launched local collectors
retain their existing local-key behavior when no shared capability is present.
Other official no-key XML/CSV sources retain their existing routes. Additional
credentialed providers need separate reviewed adapters; the broker never accepts
arbitrary URLs, headers or keys from callers.
