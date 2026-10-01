# Quorum and Politico Pro: source reconciliation and design findings

Date: September 8, 2026  
Source comparison: complete for the retained snapshots below  
Identity adjudication: review required; no new merges or live model changes

## What changes in the design

**Source precedence confirmed after this comparison:** Politico Pro is the preferred source for staff role, title and office when it conflicts with Quorum. Quorum remains complementary evidence. Payroll can be consulted for the specific discrepancies and identity ambiguities identified here. This preference applies to verified, populated Politico content; it does not establish that ambiguous same-name records are one person, turn an undated Quorum role into a dated past job, or override missing Politico content. Preserve conflicting evidence and report unresolved contradictions.

Payroll is a targeted evidence source. An identical name appearing in different offices during apparently overlapping periods is a valid reason to consult it. Exact service dates, office, title, fuller names, and shared-employee records may distinguish a duplicate profile from different people. Concurrent payments alone do not prove different people, and broad report windows do not prove simultaneous service.

Intern-only roles do not count toward the operational population or route eligibility. Internship episodes contribute no work duration or connection strength. A person who later becomes substantive staff can qualify through that later role. Coordinating interns does not make the coordinator an intern.

The work measure has two dimensions: how closely people worked and how much time they actually worked together. The current math already includes proximity and duration. The principal changes are cleaner inputs, explicit exclusion of internship periods, and tying each proximity level to the period it describes. A short close-team stint must not upgrade years of a broader association. Duplicate Quorum and Politico descriptions add corroboration, not additional people, days, or ties.

Unknown identity or dates are evidence problems to resolve before scoring. They are not a third dimension of work closeness. How long ago people worked together is also a separate question; no new recency decay has been introduced. Proposed formulas and parameter choices remain shadow-evaluation candidates in the implementation framework.

## Compared source snapshots

The Quorum input is the retained `quorum-legacy-source-native-seed` in corpus generation `20260830T070500Z-d`: 5,773 unique source IDs, verified against its receipt. This is not a fresh Quorum account export. Every seed record has a name, member-office label and title, but no service dates. The generation timestamp cannot be used as an employment date.

The Politico Pro input is the hash-bound verified prefix of `politico_profile_crawl_20260903_raw/profiles.ndjson`: 18,618 unique profile UUIDs, verified by the September 5 crawl receipt. That receipt reports completion with source exceptions. Profiles that are unavailable remain accounted for separately and do not provide verified name or role content merely because their directory cards exist.

The comparison produces candidate crosswalks, not a globally deduplicated people count. It uses normalized names, conservative first/last and nickname retrieval, title comparison within the matching office, and current-versus-history distinctions. Suffix and middle-name conflicts remain separate review outcomes. A match to an old role cannot establish current office agreement.

## Quorum record dispositions

Each Quorum source ID appears exactly once in this table. “One candidate” refers to a usable retrieved profile lead, not an accepted same-person decision.

| Disposition | Quorum source IDs |
|---|---:|
| One candidate: normalized name, office and title agree | 2,658 |
| One candidate: name variant, office and title agree | 68 |
| One candidate: office agrees, title differs | 1,359 |
| One candidate: matching office appears in Politico history | 133 |
| One candidate: name lead, office not reconciled | 721 |
| Multiple candidate profiles requiring review | 56 |
| Only conflicting, unavailable or intern-only profile leads | 23 |
| No candidate retrieved under these rules | 755 |
| **Total Quorum source IDs** | **5,773** |

Title or office differences may represent promotions, moves, incomplete source content, distinct people, or stale records. The undated Quorum input cannot establish which source role came first. The 755 records without retrieved candidates are a follow-up queue, not 755 proven Quorum-exclusive people.

The detailed crosswalk contains 5,084 candidate pairs. Of the 18,618 Politico profiles, 5,064 have a retrieved lead from a non-intern Quorum record and 13,554 do not. These lead counts include blocked or unavailable candidates and must not be described as accepted overlaps or true source-only populations.

## Intern and source-content exclusions

| Politico profile state | Source profiles |
|---|---:|
| Current roles available for review, excluding intern-only profiles | 16,861 |
| Current roles are intern-only | 267 |
| Verified name available but current role unknown | 17 |
| Profile unavailable | 1,473 |
| **Total** | **18,618** |

No Quorum seed title was classified intern-only under this comparison. Politico histories contain 10,075 internship episode records flagged for exclusion from work-time scoring, plus six mixed internship/substantive-role episode records requiring role review. These are source episode counts, not unique internships or a count of additional people. No live weighting or membership changes were made by this audit.

## Targeted payroll ambiguity review

Within the multiple-candidate queue, 45 Quorum records have identical-name Politico candidates with different current-office labels. These questions involve 81 distinct Politico candidate UUIDs; some questions share candidates.

The follow-up consulted existing payroll proof attached to those candidate identities only. It checked the pinned payroll bundle hash and verified each returned observation against the bundle's exact person, office, title, interval, date-evidence class and source row IDs. It did not undertake a new population-wide payroll matching pass.

- Existing payroll support was retrieved for at least one candidate in 28 of the 45 questions.
- The other 17 questions had no matching cached payroll proof through this lookup.
- Thirty of the 81 candidate profiles had verified cached payroll support.
- Eight questions had support for every candidate profile; that still does not resolve which profile matches the undated Quorum role.
- Zero returned proof-row binding failures; zero new identity decisions.

Existing payroll bindings are prior evidence, not an independent adjudication of these same-name collisions. The next review must determine whether the observations distinguish the people, show legitimate shared employment, reflect duplicate profiles, or remain ambiguous. Absence of cached evidence is not absence from payroll. Payroll reporting windows must not be converted into exact shared-service duration.

## Next reconciliation decisions

1. Adjudicate the 2,658 strongest exact-agreement proposals first, applying the framework's identity checks and preserving both source IDs. Do not convert the whole batch to accepted aliases without evaluating the acceptance rule.
2. Inspect the 56 multiple-candidate groups using the prepared context and targeted payroll results. Preserve same-name people as separate where evidence distinguishes them; preserve uncertainty otherwise.
3. Review title differences and historical-office leads against available career dates, using targeted payroll evidence where needed. Once the identity is accepted, defer to populated, verified Politico Pro role/title/office values while retaining the Quorum discrepancy and its resolution status. Retrieve original Quorum observation metadata where available; do not invent service dates or treat an undated mismatch as proof of a current conflict.
4. Broaden retrieval for the 755 unmatched seed records using evidenced aliases, fuller office normalization, and missing-profile recovery; measure additional true matches and false candidates separately.
5. Apply the accepted crosswalk and role-level intern exclusions to a shadow operational population, then evaluate the two-dimensional work score on accepted non-intern intervals.

## Verification and artifacts

Input hashes, record counts, unique source IDs, and stable Politico prefix bindings were checked. Eight focused boundary tests passed: exact agreement stays a proposal; different offices stay unresolved; titles must agree within the matching office; historical matches stay historical; middle/suffix conflicts are retained; intern supervisors and mixed titles are distinguished; an old internship does not exclude a later staff role; and unavailable profiles supply only name leads.

Detailed person-level records remain machine-local. The repository report contains aggregate findings. The initial comparison receipt reports zero payroll lookups at that stage; the separate follow-up receipt records the subsequent targeted cached-evidence review.

- [Implementation and evaluation framework](</C:/Users/pgoff/OneDrive/Desktop/Melange Systems/STAFFER_NETWORK_IMPLEMENTATION_EVALUATION_FRAMEWORK_20260908.md>)
- [Source comparison receipt](/C:/Users/pgoff/AppData/Local/Melange/staffer_network/reconciliation/quorum-politico-20260908-design-v1/reconciliation_receipt.json)
- [Candidate crosswalk](/C:/Users/pgoff/AppData/Local/Melange/staffer_network/reconciliation/quorum-politico-20260908-design-v1/candidate_crosswalk.ndjson)
- [Quorum dispositions](/C:/Users/pgoff/AppData/Local/Melange/staffer_network/reconciliation/quorum-politico-20260908-design-v1/quorum_dispositions.ndjson)
- [Politico dispositions](/C:/Users/pgoff/AppData/Local/Melange/staffer_network/reconciliation/quorum-politico-20260908-design-v1/politico_dispositions.ndjson)
- [Targeted payroll review receipt](/C:/Users/pgoff/AppData/Local/Melange/staffer_network/reconciliation/quorum-politico-20260908-design-v1/payroll_ambiguity_cached_review_receipt.json)
- [Targeted payroll evidence](/C:/Users/pgoff/AppData/Local/Melange/staffer_network/reconciliation/quorum-politico-20260908-design-v1/payroll_ambiguity_cached_review.ndjson)
- [Reproducible source comparison script](</C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/staffer_network/reconcile_quorum_politico_design.py>)
- [Targeted cached-payroll review script](</C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/staffer_network/review_quorum_politico_payroll_ambiguities.py>)

This completes the source-comparison pass for these snapshots. Identity adjudication, production population changes, and mathematical evaluation remain separate implementation stages.
