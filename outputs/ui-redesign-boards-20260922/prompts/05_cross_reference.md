# Build prompt 05 · Cross-reference (B16)

**Builder:** one Opus architect or Codex agent, alone in the tree, after 01. **Read first:** `prompts\00_README.md`.

## Visual spec (binding)

- `boards\B16_cross_reference.webp`.

**Don't copy:** the same record id repeated on seven rows; every name and amount.

## What exists today (verified 2026-09-22)

- Template `mentat/app/templates/view_cross_reference.html` (6 lines): the intro paragraph, `.xref-toolbar` with `#xref-refresh` ("Refresh saved evidence") and `#xref-refresh-status` ("Read-only · Refreshes every 5 seconds while this tab is visible."), and `#xref-results`.
- `mentat/app/cross-reference.js`: `html()` at lines 59-103 renders the run status (line 63), Clear refunds (76-82, `refunds.linked`), contradictions (90-93, `outliers.non_giving`) and large receipts (95-100, `outliers.large`); line 14 `LEDE` ("... this view publishes no totals.").
- `/api/cross-reference` (`server.py` 2559; `cross_reference_data.py` `_report()` at 180): `run_id, status, generated_at, scope, digest_available, digest, digest_message, limitations`. Row fields: contradictions `{record_id, company, cycle, amount, role, description, source_url}`; large receipts `{record_id, company, cycle, amount, entity, role, source_url}`; linked refunds `{refund_record_id, original_record_id, company, cycle, refund_amount, original_amount, refund_source_url, original_source_url}`; unlinked `{record_id, company, cycle, amount, description, source_url}`.
- D-040 is enforced in comments and in `mentat/tests/test_cross_reference_data.py`.

## Build this

1. **Header:** title "Cross-reference", subtitle "Inspect saved contradictions, matched refunds and unusually large receipts. Read-only." At the right, secondary "Refresh saved evidence" (`#xref-refresh`); `#xref-refresh-status` becomes its tooltip, plus a small `--muted` "Refreshing..." beside it only while a refresh runs.
2. **Run strip** (one-line card): a lilac pill with the run status ("Cross-referencing complete"), then "<sector> · cycles <list> · <n> companies · run <date time>", and at the right "Companies in scope ›" (the existing disclosure).
3. **Tabs with counts, never money:** "Contradictions <n>" (`outliers.non_giving`), "Large receipts <n>" (`outliers.large`), "Refunds <n>" (linked plus unlinked). The active tab has a 3px `--acu-gold` underline.
4. **Filter row:** Company, Cycle and Description selects (Entity instead of Description on Large receipts) and a search box "Search description or record ID". Filters apply to the active tab's rows.
5. **One full-width table card** (remove today's width cap of about 1,260px) with a sticky header:
   - Contradictions: Company | Cycle | Description | Role | Amount removed | FEC record.
   - Large receipts: Company | Cycle | Entity | Role | Amount | FEC record.
   - Refunds: Company | Cycle | Refund | Original | Refund record | Original record for linked rows; unlinked rows follow under the small heading "Negative adjustments without a matched original" with Company | Cycle | Description | Amount | FEC record.
   - Amounts right-aligned and tabular. Record ids in mono 13px, shortened in the middle with the full id in the tooltip, then an external-link icon that opens `source_url`.
   - Pager: 25 rows, "Rows 1-25 of 177", previous and next.
6. **"How this list is built ⌄"** disclosure at the bottom right holds today's explanatory text verbatim (the LEDE; the rule that a receipt is large when it is in the top 0.1% of its class and at least 20x that class's median; "Magnitude alone is not a contradiction and never excludes a receipt").
7. **Empty tab:** "No refund in this run is matched to the gift it reverses." (and the equivalent per tab), `--muted`, inside the card.
8. **D-040:** no money totals anywhere: no sums, no "total removed", no footer totals. Row counts are allowed.

## Acceptance
States at 1440x900 and 1920x1080 beside B16: the Contradictions tab; Large receipts; Refunds with zero rows; a company filter applied; a search; page 2. Check in code that no element in the view shows a money figure other than one row's amount. Suites: `test_cross_reference_data.py` (from `mentat/tests`), any browser suite that opens Cross-reference, `render_console.py --check`.
