# Source parse plan — fixed before extraction

Locked 2026-10-05T19:44:36Z after public embed retrieval and before reading embedded district rows. This is a neutral descriptive reference extract, not a model evaluation or production join.

Input: `raw/datawrapper_fejB0_v1.html`, fetched from https://datawrapper.dwcdn.net/fejB0/1/ (public iframe observed on the requested Cook page in the ordinary browser). SHA-256: `1e1af6e4b1f7bc0feb6a62473de3c08993a0d6d655803d2ec3316178301a8d60`.

Checks and pass rules:

1. Parse only embedded public JSON data, never execute downloaded JavaScript. Preserve decoded source table unchanged. Reject absence or ambiguity of data string.
2. Exactly 435 records, exactly 50 distinct states, exactly one unique district identifier per record. No synthesized observations, no imputation.
3. Preserve all six original fields and their text. Require unique field names and exactly six fields per row. Source table's current rank is preserved only as publisher metadata; no new priority/rank is computed.
4. Districts match uppercase two-letter state plus `-01` through `-52` or `-AL`. Use `SS-00` as a separate canonical at-large key while retaining the source key. Require the expected 2020-apportionment district counts by state; the six at-large states are AK, DE, ND, SD, VT, WY. Verify the expected roster separately, not by deriving it from the input.
5. Each PVI label is exactly EVEN or D+/R+ followed by a positive whole number. Store sign convention D negative / R positive; EVEN encodes 0 but retains original text. This does not imply underlying unrounded PVI is exactly zero. Preserve vintage fields independently.
6. Each 2026 source rank is an integer and the collection covers 1 through 435 exactly once. Rank metadata is not an assessment of donation impact or priority.
7. Independent full-census comparison of all six source values against browser DOM extraction if available. If unavailable, independent parser can establish extraction parity, but browser fidelity remains explicitly UNVERIFIED-HERE.
8. Copy-based synthetic defects must be detected: remove one row, duplicate a district, inject an invalid PVI, and corrupt a rank. No production code imported or executed.
9. Report source checksum, output checksums, retrieval timestamp, article publication date, embed identity, source row count and any limitations. A successful structural parse does not establish boundary currency, causal usefulness or applicability to senators.

Independent counts and row comparison are review work. No predeclared threshold may be relaxed after extraction; any changes must be recorded as deviations.

## Acquisition/encoding addendum, before normalization

The public embed contains no row data in the JSON itself; it declares the public relative asset `dataset.csv` in `assets`. Fetching https://datawrapper.dwcdn.net/fejB0/1/dataset.csv yielded a tab-delimited file, SHA-256 `ac08becbc973ed001bb7c2da1f9af8c0addb14c6406e4bbe45f9cb499e9e841a`. Raw headers are `Dist`, `Incumbent`, `Incumbent Party`, `2026 PVI`, `Rank`, `2025 PVI`. The embed applies a header change from Rank to 2026 Rank and a column order matching the browser. Dist and 2026 PVI contain `@@` display-sort suffixes; the browser spot-check establishes that AL-01@@1 renders AL-01 and R+17@@394 renders R+17. Preserve raw cells and suffixes as separate fields; validate label syntax on displayed text, not presentation markup. This is a declared encoding amendment, not a change in expected observation count or a weaker data criterion. Rank is publisher metadata only.
