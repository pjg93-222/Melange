# GovInfo BILLSTATUS staged-enrichment audit

Status: **viable with a strict eight-type boundary; not a discovery
replacement and not complete for standalone amendments.**

## Official-source findings

- GovInfo's Developer Hub identifies Congressional Bill Status XML as a
  key-free bulk dataset available from the 108th Congress forward. The
  official BILLSTATUS sitemap index currently exposes exactly 32 target
  sitemaps: Congresses 116, 117, 118, and 119 crossed with `hr`, `hres`,
  `hjres`, `hconres`, `s`, `sres`, `sjres`, and `sconres`.
- The official GPO user guide lists those same eight top-level types.
  `hamdt` and `samdt` occur only as amendment objects nested inside a parent
  bill/resolution record. They are not independent BILLSTATUS packages and
  cannot provide lossless enrichment for standalone amendment candidates.
- Current files use format version `3.0.0`. Direct official samples from all
  four target Congresses were checked. Required stable provenance is the
  source URL, source SHA-256, sitemap `lastmod`, root format `version`,
  `bill/updateDate`, and optional `bill/updateDateIncludingText`.
- Current v3 records can contain titles (including official-title type and
  bill-text version), CRS summaries describing significant provisions,
  sponsors, cosponsors, `isOriginalCosponsor`, and
  `sponsorshipWithdrawnDate`. H.Res.353 (119th Congress) was directly checked:
  it contains original-current, later-current, and both original-withdrawn
  and later-withdrawn cosponsors as distinct facts.
- Actions are under `bill/actions/item`; recorded-vote metadata is nested
  under the corresponding action at `recordedVotes/recordedVote`. H.R.1
  (119th Congress) was directly checked and has 59 actions and 26 actions
  carrying recorded-vote metadata.
- `textVersions` is not an exhaustive provisions-link service. GPO has
  explicitly documented that BILLSTATUS supplies format information only
  when XML is available, and does not supply PDF or HTML links there.
  Therefore a missing text-version URL is not evidence that official text is
  absent. CRS summary text may support relevance triage, but operative-
  provision adjudication must continue using an official bill-text source.

Primary official sources:

- https://www.govinfo.gov/developers
- https://www.govinfo.gov/bulkdata/BILLSTATUS/resources/readme.html
- https://github.com/usgpo/bill-status
- https://github.com/usgpo/bill-status/blob/main/BILLSTATUS-XML_User_User-Guide.md
- https://github.com/usgpo/bill-status/issues/200
- https://github.com/usgpo/bill-status/issues/232
- https://www.govinfo.gov/sitemap/bulkdata/BILLSTATUS/sitemapindex.xml

## Current-corpus impact

The frozen Advanced Search record corpus contains 18,557 distinct candidates:
14,854 are in the eight directly enrichable types and 3,703 are standalone
amendments (1,279 `hamdt`; 2,424 `samdt`). All 3,703 amendments must remain in
the discovery/review corpus with an explicit
`unsupported_nested_amendment` enrichment status. Their absence from
BILLSTATUS can never be an exclusion signal.

## Staged contract

`fec/stage_billstatus_bulk_enrichment.py` is deliberately non-networking. It
builds a deterministic fetch plan from a hash-frozen Advanced Search corpus
and exclusion ledger, enumerates the exact 32 official type sitemaps, creates
record tasks only for already-discovered top-level keys, and keeps every
amendment as a retained unsupported candidate.

A later isolated fetch/validation run must:

1. Freeze the Advanced Search corpus, collection exclusion ledger, and all
   reviewed false-positive exclusion-ledger SHA-256 values.
2. Retrieve and hash the official sitemap index and all 32 type sitemaps.
3. Resolve only the already-discovered 14,854 top-level keys in those
   sitemaps; never union sitemap-only records into discovery.
4. Download to a new staging root, recording URL, sitemap `lastmod`,
   retrieval time, byte count, and SHA-256 for every file.
5. Validate exact XML identity, official HTTPS host/path, size and XML-safety
   bounds, allowlisted format version, parseable update dates, and duplicate
   key count zero.
6. Produce a separate enrichment ledger with exactly 18,557 rows: enriched,
   missing-source failure, or retained nested-only amendment. Preserve
   conflicting official facts side by side; do not overwrite Congress.gov
   page evidence and do not make exclusions.
7. Fail promotion if any input hash changes, any key is side-loaded or lost,
   any of the 32 sitemaps is absent, any eligible key is unresolved, any XML
   hash/identity/schema check fails, or Quorum provenance appears.

The module is not wired into the collector, pipeline, pre-sync, readiness, or
production data. It does not authorize a fetch, sync, promotion, rank, or
mainframe write.
