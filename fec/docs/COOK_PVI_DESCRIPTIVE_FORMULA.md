# Cook PVI: descriptive formula and data contract

This document describes the historical district context implemented by
`fec/district/cook_pvi.py`. It encodes the published, rounded **2026 PVI label**
and associates it with a district code. The result is descriptive context.

## Version 1: signed rounded points

Let `L` be the published 2026 label and `k` its positive integer number of points.
The encoding is:

```text
                 -k    when L = "D+k"
points(L) =       +k    when L = "R+k"
                  0    when L = "EVEN"
```

For a member record `m`, the displayed value is:

```text
value(m) = points(L[district_id(m)])    when cook_pvi.status = "available"
           null                       for every other status
```

`null` here means **no numeric observation**. In the actual JSON contract,
`signed_points` and `pvi_label` are omitted for non-available records; consumers
must treat those absent fields as null. An unavailable value never becomes zero.
The published `EVEN` category encodes as zero but does not establish that the
underlying, unrounded estimate is exactly zero.

The source packet contains 435 complete rows. Missing or malformed labels in
that packet cause validation to fail; the loader does not convert corrupt input
into null or `EVEN`. The encoding uses rounded labels only. It does not reconstruct
the underlying Cook estimates or recalculate PVI from election returns.

Examples from the preserved source snapshot:

| Historical district code | Published label | `signed_points` | Reading of the encoding |
| --- | --- | ---: | --- |
| `AK-00` (source label `AK-AL`) | `R+6` | `6` | Republican lean, six rounded points |
| `AL-07` | `D+10` | `-10` | Democratic lean, ten rounded points |
| `AZ-06` | `EVEN` | `0` | Published EVEN category |
| Unmatched district | No observation | null | No label or numeric value supplied |

These are examples of source-vintage geography and encoding, not statements
that the corresponding present-day district boundaries have been verified.

## Version 2: direction and magnitude

An equivalent descriptive representation separates direction from magnitude:

```text
direction(p) = "D"       when p < 0
               "R"       when p > 0
               "EVEN"    when p = 0
               null      when p is absent

magnitude(p) = abs(p)     when p is present
               null      when p is absent
```

For example, `-10` becomes `(D, 10)` and `6` becomes `(R, 6)`. The sign indicates
direction; the absolute value preserves the number of rounded points. This
representation conveys the same information as Version 1. `direction` and
`magnitude` are explanatory derived values, not additional fields emitted by the
current implementation. The original `pvi_label` remains available for display.

## District lookup and status

The canonical key is the two-letter state code followed by a two-digit district
number, such as `AL-07`. At-large seats use `00`, such as `AK-00`, while the original
publisher label `AK-AL` is preserved separately.

Member matching requires House chamber identity. When a bioguide-linked roster
record is supplied, its representative type, state and district provide the key.
Explicit member state or district conflicts prevent a match. Without that roster
record, the implementation parses the member's state and district text. It never
uses the publisher's incumbent name to establish identity.

The implementation evaluates scope and identity before attempting the historical
row lookup:

| `cook_pvi.status` | Meaning | Numeric value |
| --- | --- | --- |
| `available` | A validated source row matches the resolved House district code. | Published label encoded by Version 1. |
| `outside_scope` | Senate seat, or House district in DC, AS, GU, MP, PR or VI. | Absent. |
| `unmatched` | House identity is missing or conflicting, or no source row matches the resolved key. | Absent. |
| `unavailable` | The optional source snapshot is absent after the preceding identity and scope checks. | Absent. |

For a missing snapshot, the implementation returns `unavailable` before testing
whether the final district key exists in a source table. A partially present or
corrupt source packet raises a validation error; it is not silently treated as
an unavailable optional source.

## Actual contract fields

The validated reference artifact uses schema
`cook-pvi-district-reference-v1`, with `metadata` and a `districts` mapping. Source
rows preserve both 2025 and 2026 labels; the member display uses the 2026 fields.

An available member record adds this `members[].cook_pvi` object:

```json
{
  "status": "available",
  "district_id": "AK-00",
  "district_label": "AK-AL",
  "pvi_label": "R+6",
  "signed_points": 6,
  "boundary_currency_status": "UNVERIFIED-HERE",
  "match_basis": "district_code_only",
  "identity_source": "legislators_bioguide"
}
```

`identity_source` is `legislators_bioguide` for a supplied roster match or
`member_district_text` for a parsed member record. Non-available objects contain
`status` and an explanatory `reason`, without a district PVI value.

The bundle's `cook_pvi_meta` carries provenance, `display_only: true`, the edition,
CSV and manifest hashes, interpretation and geography notes, and `coverage`
counts by status. When the source is absent, it contains the display-only flag
and coverage counts. The attachment preserves the bundle's existing fields and
adds descriptive PVI context after its existing calculations.

## Snapshot provenance and boundary limits

The source is the preserved public table associated with
[Cook's 2026 district map and list](https://www.cookpolitical.com/cook-pvi/2026-partisan-voting-index/district-map-and-list),
using [Datawrapper table `fejB0`, version 1](https://datawrapper.dwcdn.net/fejB0/1/).
Dates below are recorded provenance from the supplied packet, not a fresh
verification of the publisher's current page.

| Provenance field | Preserved value |
| --- | --- |
| Edition | 2026 |
| Article publication date | 2026-07-29 |
| Embed `lastModifiedAt` | 2026-07-22T15:17:03.000Z |
| Retrieval date | 2026-10-05 |
| Coverage | 435 House districts across 50 states, including six at-large seats |
| Boundary currency | `UNVERIFIED-HERE` for every row |
| Normalized CSV SHA-256 | `3bf2786d391323b48f4d87e9b5c5e82802bbf7749a1c83e7c6da600fa353cb71` |

The packet is stored under `source_data/cook_pvi/2026/`, with its manifest and
original raw files. Validation checks hashes, complete district coverage, label
and sign agreement, and agreement between CSV, JSON and raw source rows.
Successful validation establishes consistency with that preserved snapshot.
An available district-code match does not verify present-day boundaries or
incumbency. A district number can remain unchanged while its geography changes.
