# Politico collection and next steps — September 5, 2026

All **18,618 records in the sealed congressional directory snapshot are accounted for**. Collection integrity passes with zero duplicate profile IDs and zero verification failures. This is not a claim that every profile is available, every field is populated, or every cross-source identity is resolved.

| Outcome | Profiles |
|---|---:|
| Current position and employment history present | 17,127 |
| Source-confirmed missing current-position or history collection | 18 |
| Unavailable, HTTP 404 | 1,473 |
| Total accounted for | 18,618 |
| Not yet accounted for | 0 |

The corpus contains **70,926 employment entries** and **25,245 education entries**. All **2,584 committee-priority profiles** are accounted for.

## What was fixed and double-checked

The previous crawler required every historical job to have both a title and an employer, which rejected usable profiles with a single blank field. Its contact filter also incorrectly removed job titles such as “Telephone Operator” and “Mobile Communications Specialist.” Both cases now retain the professional record and explicitly preserve missing values. Institutional offices and a legacy numeric source ID are supported.

An authenticated request to the site's observed person endpoint avoids the page-rendering timeout. The adapter retains only modeled fields and binds them to saved, hashed source evidence. All **426 API-derived profile records** pass a field-projection audit. The complete raw corpus has **410 more profiles with both current positions and histories** than the starting checkpoint.

Fresh API checks covered all 34 records left after recovery. Rendered-page checks included John Fossum and Ty Basilio, confirming that their histories exist and contain individual blank fields. The remaining 18 source gaps are: **15 profiles with histories but no current staffer position, one with current positions but no history, and two with neither collection**. Historical data is retained; current employment is not invented.

All previously recorded 1,458 unavailable profiles were rechecked. Two transient server errors were retried and both returned 404. The final 1,473 unavailable outcomes include 15 additional source-bound API 404 observations.

The subsequent [unavailable-profile audit](UNAVAILABLE_CHECK_20260905.md) individually searched all 1,473 names and freshly fetched 12 candidate profiles. It found two probable replacement links: Kaylin Henderson (a newly saved supplementary profile) and Henry Chiperfield (the live profile was already collected). Both match the old card's exact name, employer, and title. These are documented review candidates, not automatic identity merges; the sealed corpus count remains unchanged. Three rendered original-page samples all displayed 404.

## Duplicate reconciliation

- No repeated profile IDs in the 18,618-row corpus.
- The latest audited identity overlay contains 280 evidence-backed groups and 298 aliases, with no conflicting alias targets.
- 103 groups share normalized names and remain review candidates. No new merge was justified by the exact source-ID or complete distinctive-history checks. Shared names alone do not establish identity.
- 16 live-name changes on the same source ID remain explicitly marked for identity review.

## Dashboard and remaining work

The live staffer service has been restarted with the updated source data and clearer coverage categories. Its readiness check reported Ready with no errors. The standalone `staffer-network.html` has been regenerated from its existing verified graph generation. When combined-dashboard regeneration was attempted, another pipeline held the writer lease; this task did not overwrite that pipeline's files.

The strict full-content completion gate remains **INCOMPLETE** because of the 18 source gaps. The separate acquisition status is **ALL_DIRECTORY_RECORDS_ACCOUNTED**. The existing historical graph generation remains pinned; this report does not claim a new independently reproduced full graph generation.

Next steps are to review the source gaps, unavailable profiles, name changes, and ambiguous identities; then publish a newly verified graph generation when its source-completeness requirements can be met. Preserve payroll, LDA, Politico, committee, policy, current-employer, and historical-employer layers and existing modeling defaults.

This receipt covers the sealed congressional directory snapshot. It does not certify all payroll years, the full LDA corpus, or a separate executive-agency directory census.

## Evidence

- `politico_profile_crawl_20260903_raw/crawl_verification.json`
- `PROFILE_GAP_DOUBLECHECK_20260905.json`
- `PROFILE_RECOVERY_AND_DUPLICATE_AUDIT_20260905.json`
- `politico_profile_crawl_20260903_raw/api_projected_evidence_20260905.ndjson`
- `politico_profile_crawl_20260903_raw/api_recheck_observations_20260905.ndjson`

Validation: 10 API normalization/evidence tests and 39 live-server/service tests passed; dashboard JavaScript syntax passed. Pre-finalization and pre-reprojection profile backups are retained alongside the raw corpus.
