# Staffer spine identity adjudication — 2026-09-08

Status: COMPLETE — v8 primary/twin verified, release and source-link maps emitted.

Authority: Paul's request to examine `STAFFER_SPINE_IDENTITY_DECISION_2026-09-08.md`
and `STAFFER_SPINE_IDENTITY_AUDIT_2026-09-08.md`, adjudicate the recommendations,
implement the most accurate corpus/spine approach, and commit. Those two documents
are retained as submitted; this document supersedes their recommendation.

## Decision

Adopt **bounded name repairs plus a fail-closed merge guard**. Use the proposed
Senate title rule to generate source-linked review candidates, not automatic
identity mergers. Do not extend it across chambers. Preserve the existing House
cross-office rule and uncertain-date semantics; a candidate identity link must
never manufacture day-level service dates or a co-tenure edge.

This is a qualified alternative to A+B. A's automatic merging is not established
as the most accurate option by this audit. The named examples are useful leads,
but no independently labelled identity set or precision measurement validates the
general rule. D-020 requires evidence for cross-office identity. D-019 separately
governs employment overlap; identity resolution does not relax that requirement.

## Findings adjudicated

| Claim or proposal | Ruling |
|---|---|
| 26.05% of the v7 spine is incorrectly split | Rejected as an error-rate estimate. The measured quantity is 37,684 of 144,690 records sharing a name key, across 16,151 keys. Some are different people. The audit itself counts correctly separated collisions. |
| No people are incorrectly merged | Not established. The House overlap check tests one detectable failure class. It cannot establish global identity precision, particularly in undated Senate records or suffix conflicts. |
| Missing dates authorize same-office variant merging | Rejected. Distinct payee records in the same office and report period stay separate when usable service dates are missing. The block applies to either chamber. Day-disjoint House merges remain allowed. |
| Identical annotated Senate titles justify merging | Candidate evidence only. `spans.titles` pools titles over the office history and cannot establish that a title occurred in a particular period. The new queue instead reads original payroll rows and groups exact title strings within their own report period. |
| A reaches all 17,127 Senate-only records, plus cross-chamber groups | These are candidate populations, not measured qualifying merges. No cross-chamber title rule is adopted. |
| Strip all suspicious leading fragments | Adopt two bounded, observed header prefixes: `SENATE STEERING COMMITTEE` and `OF THE SENATE`, before a surviving surname and comma-separated given name. Do not infer a general job-title stripping grammar from a few examples. Other suspect raw names remain review issues. |
| Add DE LOS / DE LAS particles | Adopt as explicit two-token sequences with the existing given-name guard. Preserve names such as `LE CATHERINE L.` and `VAN BRITTANY M`. |
| Split every conflicting suffix | Do not automate. The submitted audit distinguishes column-shift artifacts from genuine suffix disagreements. Emit every multiple-suffix record for review; neither absence nor disagreement alone resolves identity. |
| Join consumers on name_key | Rejected. Use generation-scoped person IDs and exact source-row associations. Even an office/period/name tuple can be ambiguous after the undated-record guard fires. |

The raw Wallner rows also limit the decision document's shorthand: in report
`GPO-CDOC-112sdoc10`, period starting 2012-04-01, page 400 carries
`EXECUTIVE DIRECTOR FROM SEP. 20`, page 411 carries
`EXECUTIVE DIRECTOR FROM SEP. 1`, and page 713 carries
`EXECUTIVE DIRECTOR FROM SEP. 7`. Earlier periods include `LEGISLATIVE DIRECTOR`.
All are from the bound `senate_payroll_candidates_1` input, not independent
identity confirmations. These observations support prioritizing review; they do
not turn all matching names into a validated identity class.

## Implementation and release contract

- Name standard 1.2 repairs the two header forms and the two particle sequences.
  Original raw strings are preserved. The legacy `payee_key` remains explicitly
  legacy; consumers must not substitute its middle initial for `name_key`.
- The builder and independent verifier both block
  `same_period_variant_no_day_dates`. The receipt lists the actual blocking basis
  and collision ordinals distinguish records without dropping observations.
- `rebuild_spine_identity.py` reuses the exact audited payroll and linkage inputs,
  verifies their hashes, computes a fresh name-change census, builds primary and
  twin v8 generations, and runs the independent source reconstruction verifier.
- Rebuilding from the original payroll/v6 identity partition recovers the two
  records inside each previously undated v7 merge. The v7-to-v8 migration relation
  explicitly permits multiple targets; such a source ID requires a source-row
  lookup and must never be assigned to an arbitrary target or fanned out as fact.
- `senate_title_identity_review.ndjson.gz` carries exact title, period, person IDs,
  office keys, source row IDs, source PDF hashes/URLs, pages, and raw quotes. It
  authorizes no identity merger. `suffix_identity_review.ndjson.gz` preserves
  unresolved suffix conflicts. `name_parse_review.ndjson.gz` additionally
  nominates remaining role/title fragments in parsed surnames without treating
  those patterns as grounds for deleting or renaming a record.
- Generated directories remain local and are not committed (D-022). Code, tests,
  this adjudication, and a compact completion record are committed. Existing
  graph/surface generations keep their own pinned provenance until rebuilt; a
  pointer swap cannot migrate a graph through a one-to-many person-ID split.

Reproduction, from the repository root:

```powershell
python audits/staffer_network/rebuild_spine_identity.py delta
python audits/staffer_network/rebuild_spine_identity.py primary
python audits/staffer_network/rebuild_spine_identity.py twin
python audits/staffer_network/rebuild_spine_identity.py verify
python audits/staffer_network/rebuild_spine_identity.py review
```

The builder's `spine_id_map_v6_to_v7.ndjson.gz` filename and `key_v7` field are
retained as the existing wire format; inside v8 they refer to the current target
generation. Consumers migrating from the released v7 must use the separately
named **spine_id_map_v7_to_v8.ndjson.gz**, whose generation fields are explicit.

## Verification

Targeted suite: 213 tests passed, including 48,308 parser subtests. Positive merge
fixtures now supply day-disjoint service dates; an explicit negative control
proves missing Senate dates block merging even when the titles match. Additional
controls reject cross-period title matches, different date annotations,
unannotated titles, unknown source row IDs, and same-office candidate groups.
Migration tests require both split targets and reject lost or duplicated source
identities. Replica tests require the same batch metadata in separate output
directories. The language check exempts quoted source office keys, consistently
with the builder, while still rejecting authored access claims. The existing parser gold remains unchanged.

Full generation counts and independent verification results are recorded below.

Findings review (D-007): this ruling distinguishes name-key counts from identity
errors; treats repeated reads of payroll as one evidence substrate; separates
House and Senate rules; uses capable negative controls; and binds claims to
dated generations. It supersedes, rather than retroactively edits, the submitted
audit and decision documents (DE-004).

## Ranking/source-link handoff

The concurrent ranking task owns its math changes and the ensuing graph rebuild.
Its controlled comparison uses the v7 spine and must not be reported as a v8
result. No live graph or surface selector is changed by this identity release.

The actual Politico bridge consumed by `staffer_social_network_20260907_v6_primary`
is bound to **v6**, whose spine hash is
`a6ffb3f5e683fd8741b51ddc971e39648271636f4ea46c9f856fd7d66bb3fad7`.
A hash-checked scan of all graph-bound Politico payloads finds **7,712 distinct
native person IDs**; every one has one target in the direct v6-to-v8 map. No name
join or selection between the two children of a v7 split is involved.

Use `spine_identity_adjudication_20260908/spine_id_map_v6_to_v8.ndjson.gz`
(144,693 source rows) for these native bridge inputs. Its proof is
`source_link_remap_receipt.json`. Keep the original bridge receipts and bind both
the new map and the verified v8 spine in the new graph receipt. Any different
consumer carrying already-merged v7 IDs must instead use the split-aware v7 map
and recover original source-row identity where necessary. Recompute all graph
weights and ranks; never copy or sum the old scores through either map.

## Completion receipt

Basis: `audits/staffer_network/spine_identity_adjudication_20260908/identity_release_receipt.json`,
using the exact payroll vintage and hash-bound inputs of the submitted v7 audit.
The final independent receipt is
`audits/staffer_network/hill_personnel_spine_20260908_v8_verification/hill_personnel_spine_verification_receipt.json`.

| Measure | Result |
|---|---:|
| Independent verification assertions | **50 / 50 PASS**, zero failures |
| Byte-identical primary/twin files | 7 (six payloads plus the build receipt) |
| v8 spine records | 144,692 |
| Office spans | 204,699 |
| Admitted source observations, all conserved | 1,351,415 |
| Unchanged v7 IDs | 144,647 |
| Rekeyed v7 IDs (name repairs) | 41 |
| v7 IDs split into two targets each | 2 |
| v8 shared name keys / records on those keys | 16,154 / 37,700 |
| Senate exact annotated-title review groups / involved IDs | 3,605 / 5,513 |
| Suffix-conflict review records | 57 |
| Additional suspect name-parse review records | 87 |
| Native Politico IDs checked / missing | 7,712 / 0 |
| Automatic title-based identity merges / canonical promotions | 0 / 0 |

The 41 name-key repairs do not assert 41 new cross-office identity mergers.
The rise in records and shared-key counts is expected when unsupported merges
are reversed and contaminated spellings normalize; neither statistic is an
identity error-rate estimate. Residual title-only identities, suffix conflicts,
and suspect source parses remain explicitly unresolved.

The source-link handoff was delivered to the concurrent ranking task with the
verified generation paths and direct native map. Graph scores and live selectors
remain that task's rebuild responsibility. The old graph's counts are not v8
results. The graph's actual map reader accepted all 144,693 native-map rows.

Final primary spine SHA256:
`c8d26b0423e6f5a713127c4d53a72c2c2cfc9769190682b4a3ac2e5b740da302`.
Native v6-to-v8 map SHA256:
`fbbf2bb0ef41ab97a1744e46de53cd378b687897058821d88b77d277505c0e84`.
The verification attestation records the complete file hashes and the release
stage rechecks them before emitting its receipt. Preflight attempts are retained
separately; they are not release generations.
