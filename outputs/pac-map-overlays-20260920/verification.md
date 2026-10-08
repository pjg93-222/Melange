# PAC evidence map overlays — local verification

Implemented in the existing working tree on 2026-09-20. Existing unrelated edits were retained.

- ZIP points and state legislative districts are selectable alongside congressional districts, states and regions.
- Legislative controls choose a state and upper/unicameral or lower chamber. Only the selected state/chamber is fetched; the detailed geography cache retains at most six bundles. Offscreen legislative paths are culled after navigation settles.
- Legislative receipt amounts are estimates from the supplied ZIP internal-point crosswalk. Census 2024 vintage, source links, approximation, unavailable chambers, missing assignments and source ZIP truncation remain explicit. Spent shows reference boundaries without inferring legislative spending.
- ZIP markers use viewport culling and adaptive clustering with an 800-marker ceiling. Cluster tooltips identify the representative ZIP and aggregate amounts/counts.
- Enlarge gives the map the full content width, moves rankings below it, and preserves the SVG and zoom. Panning uses the actual SVG screen scale. The heat index sits below the map and wraps within narrower cards.

Validation:

- `node --test mentat/app/tests/evidence-map.test.js`: 15 passed.
- `python -m unittest discover -s mentat/tests -p test_evidence_geo.py`: 46 passed.
- `node mentat/tests/test_evidence_map_render.cjs`: passed against shipped geometry; 33,780 ZIPs rendered as 520 national clusters (ceiling 800); Texas lower chamber culled from 150 to 6 paths at a district zoom; selection retained nodes. Median transform JavaScript update 0.20 ms, maximum 1.5 ms in this run. These timings are not total browser paint/frame times.
- `node mentat/tests/test_evidence_map_interaction_browser.cjs`: all 20 steps passed, including real local static routes, chambers, absent Nebraska lower chamber, provenance links, delayed-response races, narrower legend layout, enlarge/collapse, search, ranking pagination and reduced motion. Zero page or console errors. First open 1,389 ms including localhost fetches; 667 clusters for the 3,200-ZIP receipt fixture. Width grew from 753 to 1,290 px and restored with zoom intact. Browser shutdown exceeded the harness's 10-second cleanup bound; the test server stopped and the browser subsequently exited.
- JavaScript syntax checks and focused tracked-file whitespace check passed.

`pac-map-overlays.png` is an inspected local browser screenshot of the Texas lower chamber in enlarged mode. Geography is the supplied real Census data; amounts and contributor records are synthetic test fixtures, not verified PAC financial results.
