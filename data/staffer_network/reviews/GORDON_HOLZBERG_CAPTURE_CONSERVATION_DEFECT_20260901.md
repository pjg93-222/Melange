# Gordon Holzberg profile-capture conservation defect — 2026-09-01

## Ruling

`lda:lobbyist:147664` is not a person with no employment evidence. The current corpus
holds an exact numeric identity anchor, an exact LegiStorm crosswalk, a substantive LDA
covered-position claim with five Hill role/office mentions, and an LDA registrant
affiliation. However, the profile-employment capture referenced during acquisition did
not survive into the current working-history, rapid structured-profile, authenticated-
profile, or canonical episode ledgers.

Current classification:

- broader collected-assertion status: `FIELD_COMPLETE_ON_COLLECTED_ASSERTIONS`;
- structured source-profile status: `NO_STRUCTURED_SOURCE_PROFILE_EMPLOYMENT`;
- canonical episode count: `0`;
- defect: `KNOWN_PROFILE_CAPTURE_NOT_CONSERVED`;
- repair priority: `HIGH`.

## Conserved anchors

- LDA person: `lda:lobbyist:147664`, display name `GORDON HOLZBERG`;
- LegiStorm person: `267918`;
- direct profile URL: `https://www.legistorm.com/person/bio/267918/Gordon_E_Holzberg.html`;
- LDA covered-position roles: Legislative Director for Rep. Emilia Sykes; Senior
  Legislative Assistant, Legislative Assistant, Legislative Correspondent, and Staff
  Assistant for Rep. Alma Adams;
- industry biography anchor: America's Credit Unions beginning August 2024.

The exact crosswalk and golden fixture are documented in
`data/staffer_network/reviews/CLAUDE_OPUS5_FULL_LOBBYIST_EMPLOYMENT_HANDOFF_20260831.md`.
Numeric-key verification is documented in
`audits/staffer_network/A5A_LDA_COVERED_POSITION_VERIFICATION_20260831.md`.

## Repair acceptance

Re-materialize every captured profile employment episode as a structured, source-bound
record; preserve the profile URL and capture timestamp; bind the exact LDA person ID;
retain role and employer even when dates are unavailable; compare the reconstructed
episode count and payload digest against any surviving acquisition receipt; and rerun the
source-profile inventory primary/twin. Do not infer missing dates or claim lifetime
exhaustiveness.
