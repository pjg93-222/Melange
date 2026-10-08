# Payroll route map and visible exclusions

The live Gordon Holzberg → Hailey M Barringer → Rene O Castellanos → Mike Casca search returned four nodes and three edges, but the inventory worker could locate only Casca in its directory browse population. The screenshot showed one highlighted person and no route lines despite the completed route card.

## Changes

- The position lookup now accepts supplied person records from route and neighborhood results. For people outside the inventory, it uses the same deterministic placement function. This adds display positions, not inferred relationships or inventory membership.
- The caption reports positioned route people and additional historical records. The renderer exposes the number of drawn route edges for verification.
- Show route on map now refits the route before scrolling to it.
- The toolbar always reports active person exclusions, including when the details panel is closed. The search form lists names and individual removal controls, plus Clear all person exclusions. Unresolved names from saved links retain a visible record ID.
- Clear and Reset view clear person exclusions and their URL state. Route results state whether people were excluded. Different-contact alternatives name contacts skipped from earlier choices; workplace separation is also explained when selected.
- Updated stale Sources text describing the old directory-only routing and scoring.

No backend scoring, identity decisions, or person-specific default exclusions were changed. The router defaults to an empty avoid_people list. Intern, evidence and identity eligibility rules remain separate from user-selected person exclusions.

## Validation

11 focused JavaScript tests passed, covering payroll-only positions, stable coordinates across filtering, unchanged inventory counts, route map integration, alternative disclosures, and exclusion removal. JavaScript syntax checks and git diff whitespace checks passed.

Live browser verification on port 8841:

- Gordon → Casca, Staffer, payroll and directory, one route, no person exclusions: all four labels and three gold connecting lines visibly rendered.
- Caption: 4/4 route people on map; 3 additional historical records. Canvas data-route-edges-drawn: 3.
- Saved Darner exclusion: toolbar showed 1 person excluded with the side panel closed; review reopened the named exclusion.
- Clear all person exclusions: toolbar returned to No people excluded and avoid_people disappeared from the URL.
- Rerun returned the same Gordon → Hailey → Rene → Casca route.
- Fit map followed by Show route on map refocused the route. Final page retained the unexcluded result.

The map overview still represents the directory browse population; the expanded payroll route is drawn over that overview. The updated caption makes this distinction explicit.
