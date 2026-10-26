# Press site failure triage (for a Claude session)

Source ruling, Paul, brain D-294: "The press 403 rule, should never fail the whole thing, and if
there are any failures you should log them and send them over to claude for adjustment. We need
this fully sustainable."

## What happens in the run

- One member site being unavailable (HTTP 403/404/5xx, timeout, SSL, non-JSON reply) is recorded and
  that member is skipped for the run. Everything else is still collected. Code:
  `press_site_unavailable` and friends in `collect/press_official_coverage.R`; the loops in
  `collect/press_wordpress_custom_posts.R` (`press_wp_collect`) and
  `collect/press_official_dated_listings.R` (`press_official_collect`).
- Still fatal: output cannot be written, a seal or hash is broken, a roster/origin/pagination/date
  integrity violation, the delta safety cap, or EVERY member failing (`press_site_all_failed`,
  `refresh_press_delta.R`, exit 2).
- `outputs/press_refresh_YYYYMMDD/press_site_failures.json` is written beside the receipt (the receipt is
  unchanged). After a sealed walk `collect/refresh_press_stream.py` calls `press_failure_queue.record_run`,
  which upserts the queue and writes `press_site_failure_receipt.json` into the run folder.
- `weekly_refresh.py` records `press_status` (PARTIAL when a site was skipped, never PASS),
  `press_failures_open` and `press_failure_queue` in `data/engine/weekly_refresh_status.json`, and copies
  the receipt into `audits/weekly_refresh/<run>/`.

## The queue

`data/press/press_failure_queue.ndjson` (git-ignored runtime data). One row per
`(member_id, url, error_class)`: `first_seen`, `last_seen`, `consecutive_runs`, `last_error`,
`http_status`, `run_id`, `source`, `status` (`open`, `recovered`, `adjusted`), optional `note`.
Rows are never deleted. Recorded again in the same run does not double count. A key that fails again
re-opens.

## Process it

1. Read the open rows: `status == "open"`. Highest `consecutive_runs` first. Do not run any collector,
   walk or network job to diagnose; reason from `url`, `error_class`, `http_status`, `last_error`, and
   at most one manual look at the site.
2. Diagnose each row. Typical causes:
   - site moved or endpoint changed (404, redirect, new press path): the member needs a new route;
   - bot block (403 on `wp-json`, `error_class` `http_403`, same status on several members): the
     adapter or request headers, not the member, needs the change;
   - member left office or site retired: roster change (Paul's decision);
   - transient (`timeout`, `http_5xx`, `network_error`) that did not recur: leave open one more run.
3. Propose the adjustment in the EXISTING mechanism, as a reviewed change on a branch, never applied
   blind: `PRESS_MEMBER_OVERRIDES` in `collect/press_member_overrides.R` (member press route),
   `PRESS_WORDPRESS_CUSTOM_MEMBERS` in `collect/press_wordpress_custom_posts.R`, or
   `PRESS_OFFICIAL_DATED_MEMBERS` in `collect/press_official_dated_listings.R`. Add or update a test.
   Never run `apply_press_overrides.py`. Roster membership and classification stay Paul's.
4. When the change is accepted, edit that row in the queue: `status: "adjusted"` and a `note` saying what
   changed and where (branch or sha). If the fix was only "wait", set `note` and leave it `open`.
5. Do not delete rows.

## Follow-up option for Paul (not built)

An unattended Claude/LLM call that drafts these overrides automatically. Not added: every adjustment
here is a reviewed change, and nothing in the refresh invokes a model.
