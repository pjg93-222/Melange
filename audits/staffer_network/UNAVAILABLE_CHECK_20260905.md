# Unavailable-profile check — September 5, 2026

The **1,473 original profile IDs still return API 404**, but that does not establish that all 1,473 people have disappeared from Politico. A deeper check found **two probable replacement profiles** with matching names, current employers, and job titles.

## Results

| Check | Result |
|---|---:|
| Original unavailable IDs with recorded direct API 404 rechecks | 1,473 / 1,473 |
| Individual live-directory name searches completed | 1,473 / 1,473 |
| Names returning no directory search results | 1,462 |
| Names returning one or more search results | 11 |
| Distinct candidate profiles freshly fetched successfully | 12 |
| Probable replacements: exact name + current employer + title | 2 |
| Original pages checked in the rendered website | 3 / 3 displayed 404 |
| Automatic identity merges | 0 |

A positive search canary succeeded. The three rendered samples were Matt Alexis, Katherine M. White, and Nicholas V. Sokolov. Their page shells returned HTTP 200, but the website displayed a 404 and no profile name or employment history. The original person API requests returned 404; these are not merely timeout classifications.

## Replacement and duplicate findings

| Person | Finding | Treatment |
|---|---|---|
| Kaylin Henderson | New ID `fea69aef-3b7a-4f17-a8bd-e9a7c6d924fb`; same Legislative Correspondent role for Rep. Christian Menefee. Five employment entries recovered. | Saved as a supplementary profile with source evidence. Probable replacement; not silently substituted for the old ID. |
| Henry Chiperfield | Live ID `4875afed-c41d-4d63-a93b-696ce0582861`; same Legislative Correspondent role for Sen. Katie Britt. | The live profile was already collected. Flagged the old unavailable ID as a probable duplicate/replacement candidate; no additional person inserted into the canonical corpus. |
| Grace Martin, Joel Miller, Jorge Lopez | Exact-name results exist, but their employers and histories do not corroborate the old source-card roles. Jorge Lopez has two different live profiles. | Kept separate pending stronger identity evidence. |
| Six other searched names | Returned differently named people without corroborating employment. | Search results are not accepted as identity matches. |

All 12 candidate profiles were saved in a separate, deduplicated evidence set; 11 were already represented in the original corpus. These supplementary records are **not yet integrated into the dashboard**. The sealed 18,618-record corpus and its verification receipt were not changed by this check. The canonical unavailable count therefore remains 1,473, with two probable replacement links now documented.

## Limits and next steps

The current staffer search reported 16,936 listings, but broad pagination stopped at 10,000. That truncated result was **not** used as a complete census: every unavailable name was individually searched instead. No original unavailable ID appeared in those results. Names that changed completely, unindexed profiles, and entries outside the congressional-staffer search scope may still require other evidence. A search miss is not proof of permanent deletion or absence from government.

Next: validate and integrate the two replacement mappings through the review-aware identity layer, without changing the sealed source IDs or double-counting Henry. Resolve the remaining ambiguous names only with corroborating identity evidence. The wider cross-source duplicate reconciliation and full-network publication remain separate unfinished work.

## Evidence

- `UNAVAILABLE_PROFILE_AUDIT_20260905.json`: exhaustive targeted-search coverage and rendered samples.
- `UNAVAILABLE_DIRECTORY_NAME_SEARCH_20260905.ndjson`: all 1,473 saved name queries and projected professional results.
- `UNAVAILABLE_REPLACEMENT_REVIEW_20260905.json`: candidate classifications and hashed evidence references.
- `UNAVAILABLE_REPLACEMENT_API_EVIDENCE_20260905.ndjson`: 12 projected HTTP-200 source responses.
- `UNAVAILABLE_REPLACEMENT_PROFILES_20260905.ndjson`: 12 unique supplementary normalized records, not canonical insertions.
- `politico_profile_crawl_20260903_raw/api_recheck_observations_20260905.ndjson`: original-ID rechecks, including successful retries of two transient server errors.

Six replacement-classification tests passed, including rejection of name-only, wrong-ID, prefix-employer, and mismatched-profile-role matches.
