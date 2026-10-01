# CAMPAIGN SITE COLLECTION 2026 -- RUNBOOK (C1-2026, AUTHORIZED 2026-08-14)

TIME-BOX: collection executes September-October 2026 and MUST complete before the November
2026 election; campaign sites decay within weeks of losing (and often of winning). This is
the only research-integration item that expires.

## Objective
Pre-office text (biography + issue platform) for every incoming 120th-Congress freshman at
seating 2027-01-03, collected while candidate sites are live. Protocol adapted from
CampaignView (Porter, Case, Treul 2025, Sci Data 12:1237; research/2025_SciData_Porter_CampaignView.pdf).

## Universe
General-election candidates, both major parties: ~870 House (2/seat x 435) + the 2026 Senate
class (33-35 races, ~70 candidates). NOT the primary universe (~2000+/cycle) -- general
election only, per the unified plan's scoping.

## Protocol (per candidate)
1. Roster: state general-election certified candidate lists as primaries conclude; FEC
   candidate file for FECCandID linkage (mandatory where the candidate filed).
2. URL discovery: repositories (politics1.com), candidate social profiles, targeted search.
3. Capture: biography page + issues/platform subpages, one snapshot per candidate; platform
   parsed to one document per issue heading (CampaignView unit). Rare video-only platforms
   noted, not transcribed at capture time. Incumbents with no campaign site (or a
   donation-only site): capture the official House.gov/Senate.gov bio + issues pages
   instead, flagged housegov_bio / housegov_issue per the CampaignView mechanism.
4. Provenance per page (NON-NEGOTIABLE, the 5a/5b lessons): source URL, retrieval timestamp
   UTC, sha256 of raw HTML, capture date on EVERY row. Drop-never-guess on identity.
5. Storage: source_data/campaign_sites_2026/<state>/<candidate_slug>/ with a manifest.json
   per candidate; raw HTML kept; extracted text derived, never replaces raw.
6. Glassbox: the collector emits progress to the shared event stream (lane claude, source
   campaign-sites-2026); silent runs are unacceptable.

## Success bars (effectiveness sheet, C1-2026 card)
>= 85% of the general-election universe captured with bio + issues before the election;
100% provenance; post-seating: pre-office text held for >= 85% of actually-seated freshmen.
Context ceiling from the paper: winners' web presence ran 88.3% (platform) / 99.0% (bio).

## Build plan
Collector script: Codex lane, late August (spec via codex-executor protocol; new files only,
politeness delays, no login walls, robots-respecting). A smoke test on n=10 candidates
gates Sweep 1 (results presented before the full run). Weekly collection passes September-
October (re-fetches diffed by raw-HTML sha256 so platform revisions are detected and
re-captured); final sweep the week before the election; post-election Wayback fallback pass for
any missed winner (within one month of election day, per the paper's archive-timing rule).

## Not in scope
Primary-stage candidates; third parties (record as honest gap); stance labeling of platform
text (topic parsing only at capture; any labeling is Paul's later call).