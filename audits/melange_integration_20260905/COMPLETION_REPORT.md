# Melange local dashboard integration — September 5, 2026

The full local dashboard is available at http://127.0.0.1:8841/.

## Completed

- Shared navigation joins Influence, Members, Industry and the live People application. Bills, reported interactions, champions, forecasts and organization screening are served and reachable through More.
- Member profiles offer **Find a connection to this office**. It opens People with the member's office name and Office mode selected. The live office chooser retains distinct committee offices rather than guessing a match.
- The full People inventory, route search, contact fields, source dates and identity review use the existing live service. Person selections and return-to-inventory state synchronize with the parent URL.
- Build receipts and input hashes are retained inside **Methods → Build checks and source files**, closed by default. Raw member-response calculation rows move into Methods while the readable member summary remains visible.
- The fixed navigation no longer covers member profile actions. Shared navigation wraps for narrow layouts; the embedded People application retains its existing responsive layout.
- Failed snapshot requests clear stale cache tokens and retry after three seconds. A 304 response cannot leave an initial load empty; it requests a full response. Successful refreshes clear stale errors.
- The local HTML loads an identical member-profile script separately, reducing the combined document from 80,408,220 to 18,987,304 bytes. All 61,421,107 bytes of member profiles remain available. Published/offline artifacts are unchanged.

## Verification

- 31 Python tests passed, covering the live HTTP handler, route-page aliases, gzip responses, caching, allowed paths and source preservation.
- The snapshot-recovery regression passed: a failed initial request, an unusable 304, then a successful complete response recovers without leaving an empty cached view.
- Six dashboard pages returned HTTP 200 and supported ETag 304 caching. The separate member-profile payload matched its original SHA-256.
- All 11 previously published pages/assets matched their original hashes.
- The live inventory reports 686,297 records, including 493,535 person records and 181,390 people indexed for routes. The snapshot and full inventory share source revision `4e16439288d003caa95e`.
- Browser checks confirmed all four main views, 533 member profiles, Alex Padilla's profile-to-office shortcut, Methods receipt containment, and the live People inventory.
- Within the integrated dashboard, the fewest-step office search compared 63 Padilla staff and returned Gordon Holzberg → Nina E Doorley → Silvia Ruelas-Chulak, two steps.
- Searching Grace J Ryan returned the consolidated Grace Ryan profile, current role as reported, office phone `(202) 225-8273` and email `grace.ryan@mail.house.gov`, with the contact export date July 3, 2026.
- Service PID 63692 was ready without service errors. The `MelangeStafferLiveSidecar` watchdog was restored to Ready.

## Scope and retained limitations

This integrates the existing audited dashboard and current live network. It does not claim every person record is a unique individual or routable: unresolved source identities remain separately browsable. Source dates and missing contact fields remain explicit. Earlier data/model receipts remain unchanged. No new employment, identity or relationship evidence was invented, and no messages were sent to contacts.

The browser showed the completed desktop layout. A requested viewport override did not change the inspected tab's width, so this receipt does not claim a new narrow-screen browser acceptance test; the override was reset.

Evidence: `tests.log`, `recovery_tests.log`, `live_acceptance.json`, `published_inputs.json`, `watchdog.json` and the sealed completion receipt in this directory.
