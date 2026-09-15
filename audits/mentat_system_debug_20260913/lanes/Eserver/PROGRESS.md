# Lane E-server progress

2026-09-14 — lane opened. Prior attempt left: backups (.bak-20260914-E) for server.py,
README.md, .gitignore (all byte-identical to the live files, i.e. pristine); vendor bundle and
LICENSE copied byte-exact into mentat/app/vendor (sha256 4fb9eac5... matches the pin); five
pocket tools copied byte-exact into mentat/tools/pocket; step1-template.js drafted but not run.
Running consoles found and LEFT ALONE: pid 66760 mentat server.py --port 8806; pid 17756
staffer_live_server 8841. My own instances will use 8820/8821 only.

CONTRACT ITEM 1 (saved views) — server.py Console.list_views/get_view/save_view/delete_view,
GET /api/studio/views[?id=], POST /api/studio/views + /views/delete, read-only 403, 512 KB body
ceiling. step2-views.js applied; server.py 88038 -> 93208 bytes; py_compile OK. Endpoint
exercise still pending (after the pocket lane, on ports 8820/8821).

CONTRACT ITEM 2 (briefing) — server.py Conflict exception + briefing/briefing_item/
add_to_briefing/remove_from_briefing/order_briefing, GET /api/studio/briefing[/item], POST
add/remove/order, read-only 403, 409 on the 41st item. step3-briefing.js applied; 93208 ->
99287 bytes; py_compile OK.

CONTRACT ITEM 3 (vendor route) — step4-assets.js applied: /chart-briefing.js, /chart-briefing.css,
/vendor/pptxgen.bundle.js in STATIC_ASSETS plus a 404 guard for an allow-listed file that is not
on disk yet (the two chart-briefing files belong to the parallel client lane). 99287 -> 99650
bytes; py_compile OK. Vendor bytes were already in place and hash-verified (4fb9eac5...).

CONTRACT ITEM 4 (pocket publish) — step5-tools.js (--out-dir), build_page.py installed whole
(--data/--out), step6-pocket.js (Console.port, publish_pocket, publication, routes, main port
wiring), step8-pocket-hardening.js and step10-publication-read.js (two races closed). Real
publish with --datasets Crypto against 8821 reached DONE in 22.1s: 57,956-byte full-document
page + pocket-data.json + pocket-integrity.json in the throwaway report folder; repo template
unchanged; build_page byte-identical across 3 builds.

.gitignore appended (2 exceptions, verified with git check-ignore). README.md appended
(4 paragraphs, mixed endings preserved: 544 lines kept their own, 41 new CRLF).

TESTS: 8 + 7 + 9 + 22 + 4 = 50 per round, 3 rounds, zero failures.
Both lane consoles (pids 50944 read-only 8820, 1396 writable 8821) stopped by PID; Paul's
processes untouched. pyc deleted. RECEIPT.md written. LANE COMPLETE.

ADDENDUM (coordinator ruling on items 8-9) — icon-180.png + manifest.webmanifest copied
byte-exact into mentat/tools/pocket (no .gitignore change needed: both verified NOT IGNORED).
selfcheck.py gained --dir/--data (step12) and two inherited assertions were corrected (step14:
wrapper checks inverted for the now-full document, hardcoded 8-industry count replaced).
server.py publish now copies both assets, records output_files, and runs selfcheck as an
ADVISORY post-check (step13). Re-published Crypto on 8821: done + selfcheck PASS, 5 files.
Negative control: a one-cent tamper still produces 3 FAILs. 53 tests/round x 3, zero failures.
Consoles 67256/73388 stopped. Item 7 (atomic_json retry) untouched per ruling. ADDENDUM DONE.
