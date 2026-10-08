# Visible downstream spending correction — September 21, 2026

Following the user's request to keep the interpretation simple, the UI calls this **PAC-backed candidate spending**, with one short statement that backing is assumed from recorded transfers. Detailed measurement caveats remain under source/measurement disclosures. Numerical aggregation, non-additivity of transfers, hashes and missing-source handling are unchanged.

The earlier measurement fix reached Graph's live API, but PAC Evidence still filtered its candidate table to the selected committee's own spending. A Fairshake pane therefore omitted Andy Barr even though the saved source included spending by Defend American Jobs. This was a presentation/data integration defect, not missing source dollars.

## Changes

- `/api/evidence-network` uses the shared cycle-safe downstream measurement. The selected snapshot supplies the starting PAC; saved recipient PAC snapshots supply onward activity. Multiple routes and cycles cannot duplicate a spending PAC's observations. Source hashes, windows and missing destinations accompany the response.
- PAC Evidence now has a clearly named **PAC routes & candidates** control and a searchable network spending table showing the named route, actual spending PAC, cycle, direction and exact amount. The root PAC's original as-filed detail remains separately expandable. Receipt and own-PAC financial summary figures retain their original meanings.
- Graph search now matches separate name words, so **Andy Barr** finds **BARR, GARLAND ANDY**. Focusing an upstream PAC includes its descendants by default; users can still explicitly select own-PAC-only activity.
- The idle live console on port 8806 was restarted through its normal restart endpoint. Its loaded code hash now matches disk; the live endpoint returns the corrected network.

## Dollar ledger

| Source selection | Cycle | Previously visible Barr activity in Fairshake's own-only table | Now visible through Defend American Jobs |
|---|---|---:|---:|
| fairshake-20260908 | 2024 | $0.00 | $106,708.00 |
| fairshake-20260908 | 2026 | $0.00 | $7,170,138.40 |
| September 16 root-only snapshot | 2026 | $0.00 | $7,170,138.40 |

The previous zero here means omitted from that table, not a factual zero-spending assertion. Each selection is an alternative view, not an additive amount. Upstream transfers are not added to candidate spending. These are recipient PAC observations, not proof that particular Fairshake or Coinbase dollars funded Barr.

The current count-all policy retains distinct source observations. This fix does not independently reconcile their filing/amendment relationships or certify unique economic spending.

## Verification and scope

30 Python tests and 3 JavaScript unit tests passed. The existing 10,000-relationship browser regression passed. A real-browser replay used the actual preserved source through a read-only scratch HTTP server and then passed against the restarted live console: both Fairshake cycles and the newer root-only snapshot each displayed Barr exactly once, with the expected cents and named route. It checked natural-order name search, upstream Graph focus retaining descendants, and mobile page containment. Tables retain horizontal scrolling for exact values at narrow widths. The scratch server was stopped after verification.

`before-after-ledger.json` preserves the measurements and selected source hashes. `verification.json` verifies the source files are unchanged and records the running app's build. `browser-results.json` records the rendered observations. The Fairshake source SHA-256 remains `ffee8b261b28fe15cd93f1b5c30b74d493a0b6a955baa22bc0e4a9cfb2af43fa`.

No FEC recollection or production workbook rewrite occurred. Saved coverage dates still apply. Two 2024 reachable destinations, C00476978 and C00774463, lack snapshots and are explicitly disclosed. The selected 2026 network has no missing reachable snapshot in the currently saved inventory; this is not a claim of complete FEC filing coverage. Different root/recipient snapshot dates remain visible in source coverage.
