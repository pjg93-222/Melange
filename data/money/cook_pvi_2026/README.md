# Cook PVI 2026 — neutral reference extract

Acquired 2026-10-05 from the public table embedded in [Cook's 2026 district map and list](https://www.cookpolitical.com/cook-pvi/2026-partisan-voting-index/district-map-and-list). Article dated July 29, 2026. The ordinary browser exposed [Datawrapper table fejB0, version 1](https://datawrapper.dwcdn.net/fejB0/1/); its public configuration declared [dataset.csv](https://datawrapper.dwcdn.net/fejB0/1/dataset.csv), fetched using ordinary HTTP. No login, challenge bypass or private endpoint was used.

`cook_pvi_2026_districts.csv` and `.json` hold 435 district records, ordered by district ID. Preserve `source_manifest.json` beside the CSV when sharing or moving it: CSV cells alone do not carry the publication, retrieval, geography or interpretation context. JSON already embeds that metadata. Keep the original `raw/` files for reproducibility.

The `.csv` source asset is tab-delimited. `raw/dataset.csv` preserves its original bytes and all six columns. Datawrapper stores some cells as `displayed label@@integer sort key`; the normalized table separates the suffix only after checking that it is an integer. The embed displays the raw `Rank` header as `2026 Rank` and reorders the columns. It reports `lastModifiedAt=2026-07-22T15:17:03.000Z`, `publicVersion=1`, and no `publishedAt` value.

## Data dictionary

| Field | Meaning |
|---|---|
| `district_source_cell` | Original Dist cell, including its `@@` suffix. |
| `district_label` | Browser display label, such as AL-01 or AK-AL. |
| `district_id` | Separate normalized key; at-large districts use SS-00. |
| `state` | Two-letter state code from the source district. |
| `district_number` | Numeric district number; zero means at-large. |
| `district_source_sort_key` | Preserved Datawrapper district sort suffix. |
| `incumbent_source_text` | Exact publisher text, including OPEN/VACANT qualifiers. Not independently established as current. |
| `incumbent_party_source` | Exact source party label; independent labels remain independent. |
| `pvi_2025_label` | Original 2025 PVI label. |
| `pvi_2025_signed_points` | Parsed code for the displayed 2025 label: D negative, R positive, EVEN zero. |
| `pvi_2026_source_cell` | Original 2026 PVI cell, including its `@@` suffix. |
| `pvi_2026_label` | Browser display PVI label with validated sort suffix removed. |
| `pvi_2026_signed_points` | Parsed code for the displayed 2026 label: D negative, R positive, EVEN zero. |
| `pvi_2026_source_sort_key` | Preserved Datawrapper PVI sort suffix. |
| `source_rank_2026` | Publisher's Rank cell, preserved verbatim; not a research priority or donation rank. |
| `boundary_currency_status` | UNVERIFIED-HERE for every row; no district-by-district legal-current geography validation performed. |

Signed fields encode already-rounded display labels. They are not raw underlying Cook estimates, winning margins, win probabilities, causal effects or donation multipliers. EVEN preserves Cook's rounded category; zero in the code does not assert an exact unrounded zero.

No current-member or candidate join was performed. A district number can survive a change in its geographic boundaries. The source's incumbent text is a vintage-specific description, not a stable member identifier. Senators are outside this district-table extract.

## Validation and limits

The original `source_parse_plan.md` was locked before extraction at 2026-10-05T19:44:36Z with SHA-256 `c6b50d497d88801cd7b00d170c12eca4965edb987a61a8f4835a731ec7dc8de7`. An explicit pre-normalization addendum then documented the declared TSV asset and display-sort encoding. The final plan SHA-256 is `c9ddaf4e321ab3c99876c2ded44dd9cbb7b851302cef7cd8d6bbcb1306bb93f9`. Neither record should be described as the other's hash. See the independent validation receipt for full-census parsing, field agreement and planted-defect checks; successful parsing does not establish substantive validity.

Cook defines PVI as historical presidential partisanship relative to the nation and distinguishes it from election race ratings. The July table is preserved as published. The [NCSL tracker](https://www.ncsl.org/redistricting-and-census/changing-the-maps-tracking-mid-decade-redistricting?maptype=tile), read October 5 and displaying a September 11 update, reports later Missouri boundary developments. Current geography and current incumbency therefore need separate verification before any descriptive reuse. No current-election certification is claimed.

This folder contains a standalone research extract. It changes no Member Desk formula, donation allocation, ranking or production dataset. No relationship between donations, electoral outcomes and later congressional behavior was estimated.
