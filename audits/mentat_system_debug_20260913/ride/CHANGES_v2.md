# Ride 1 checklist — wording changes for republish

Base packet: `C:\Users\pgoff\Mentat\audits\mentat_system_debug_20260913\ride\RIDE_CHECKLIST.md` /
`RIDE_CHECKLIST.html`. Updated against `WORDING_PASS.md` (`lanes\wording_20260914\`, 96 changed
rows of 491) and the live shipped code at commit `f64316daa` (branch `codex/mentat-crypto`).

Of the 32 ride steps, only three quote literal product strings that changed in the wording pass.
The rest either don't quote a literal string (they describe the result in general terms) or quote
a string that the wording pass left alone.

| Step ID | Old expected | New expected | Reason |
|---|---|---|---|
| 04 | Ends with "build \<sha7\> · :\<port\> · started HH:MM · pid n" matching /api/health | Ends with "build \<sha7\> · port \<port\> · up since HH:MM" matching /api/health | WORDING_PASS row 1 (`app.js:562`): build stamp dropped `started`/`pid`, reworded to `build <sha7> · port <n> · up since <time>`. Confirmed live in `mentat/app/app.js:562` (`buildStampText`). |
| 06 | Gold banner "This console is running an older build…" with Restart; launcher replaces an idle stale server on the same port | Gold banner "This console runs an older build…" with Restart; launcher replaces an idle stale server on the same port | WORDING_PASS row 4 (`app.js:606`): "is running" → "runs"; Restart clause moved first. Confirmed live in `mentat/app/app.js:606`. |
| 16 | Chip "Carried from Graph · Banking · All cycles"; strip "Graph shows $X … Studio total $X. Agree." to the cent | Chip "Carried from Graph · Banking · All cycles"; strip "Graph shows $X for …. Studio shows $X. Agree." to the cent | WORDING_PASS row 142 (`chart-studio.js:2316`): dropped "Basis: …" lead-in and "(workbook receipts)"; "Studio total" → "Studio shows". Confirmed live in `mentat/app/chart-studio.js:2316-2317`. The "Agree."/"They differ by … because …" verdict text (row 144) is unchanged in substance — "Differ by" gained a leading "They" (`chart-studio.js:2320-2321`) but step 16 only exercises the agree path, so its quoted text ("Agree.") did not need to change. |

## Checked but not changed

Every other quoted or paraphrased string across the 32 steps was checked against WORDING_PASS's
96-row change table and the live source; none of the following needed edits because either the
step doesn't quote the literal string, or the string wasn't touched by the wording pass:

- Step 08's field-pill tooltip ("Click to add · drag to place · Enter for actions") — not in the
  WORDING_PASS change table (F2 tooltip text is untouched).
- Step 13's progress row ("Preparing verified data · … · m:ss elapsed") — not in the change table.
- Step 19's "counted at $0" — rows 387/388/407 retitle the reason text but keep "counted at $0"
  verbatim.
- Step 21's Filters pill ("\<field\>: any value") — different string from the "not carried" chips
  (rows 148-151); not touched.
- Step 27's "Add to briefing" click path already paraphrases row 430's new button label ("Add this
  chart to the briefing"); no literal quote to fix.

## Wording-pass items with no matching Ride 1 step

Two strings the task called out from WORDING_PASS do not appear, quoted or otherwise, in any of
the 32 step definitions, because no step exercises that path on Paul's own console:

- Row 12 (`app.js:644`), "Console already current — nothing to restart." → "Already up to date."
  — this is what Restart shows when the console is already on the shipped build. No ride step
  clicks Restart on a current console (step 06 only covers the *stale* case). Folded into the new
  preamble line instead ("Restart the console before step 01 — Restart reads 'Already up to
  date.' when you are already on this build."), matching the plan's instruction to add a preamble
  line before step 01.
- Rows 118/489 (`chart-studio.js:1802`, `server.py:1825`), "Saved views are read-only in this
  preview console; save from the original console." → "Read-only preview. Save views from the
  main console." — this refusal only fires on the coordinator's read-only mirror instance, which
  is pre-flight/coordinator setup in the plan's Test protocol, not one of the 32 numbered steps
  Paul walks on his own console. Not added to any step; noted here for the record.

## Group-limit wording (row 99/434, groups-per-page tooltip and default 60)

Not quoted in any of the 32 steps either — the tooltip text ("40 per page (verified) · fold after
40 (worksheet); Graph and classic fold at 60…" → "Groups shown per page. Totals and CSV exports
include every group.") and the verified-mode default change (40 → 60) live in the Chart Studio UI
itself, not in the checklist page. Step 15-19 (F4, Scope A/B) exercise totals that would surface a
wrong count if the 60-cap regressed, but the checklist's expected text never quoted the old label,
so nothing there needed editing.

## Other content changes (not wording-pass driven)

- Added a preamble line under the progress line: "Verifies f64316daa (on 9b14e1d53 · 215faa9db ·
  ed6474351). Restart the console before step 01 — Restart reads 'Already up to date.' when you
  are already on this build." Reuses the existing `.progress-line` style; no new CSS, no new
  capability, no new interactive element.
- P1/P2 markers were checked against the plan (`the-mentat-chart-system-breezy-wilkinson.md`,
  "Sequence and gates" step 4 and the per-fix descriptions) and against the hard-coded "P1 passed
  0/22" placeholder in the original page's progress line, which only holds if exactly 22 of the 32
  steps are P1. Recount on the STEPS array: 22 P1 steps (01,02,03,04,06,07,08,09,10,11,12,13,15,
  16,17,18,22,23,24,27,29,32). Unchanged — no drift from the plan.
- Title unchanged: `<title>Mentat Ride 1</title>`, same as the original page.
