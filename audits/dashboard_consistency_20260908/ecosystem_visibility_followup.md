# Ecosystem visibility and Kathleen coverage follow-up

Verified September 8, 2026.

The route-model selector was inside the scrolling person panel. Selecting a person scrolls that panel to their details; hiding the panel also hid the selector. The live People toolbar now has explicit Work & background and Ecosystem routes buttons outside that panel. They synchronize with the form selector and saved route model, reopen the pathfinder, and scroll its panel to the top. The map population and both backend routing models are unchanged.

An unreachable work/background route now explicitly says this does not establish that either person has no connections and offers Search Ecosystem routes. Shared-report collaborator route buttons now select the displayed person as origin, the collaborator as destination, and Ecosystem as the route model.

Verification: nine Node route/navigation tests passed; JavaScript syntax check passed. Browser verification after reload confirmed the toolbar button was visible above the map and remained visible with the person panel hidden. Clicking it reopened the pathfinder. Kathleen to Gordon under Work & background produced the revised no-route explanation; the explicit Ecosystem retry returned a one-step route. Chrome automation could not inspect the user's existing tab reliably, so visual verification used the existing in-app dashboard tab against the same local server. An already-open tab needs a browser reload to obtain these changes; the in-page Refresh action only refreshes records.

## Data coverage finding

A fresh live person response reports zero indexed dated coworkers and fourteen reported lobbying collaborators for Kathleen Coulombe. See `kathleen_visibility_person.json`. This is not a complete professional-network count and is not a finding that she lacks connections.

The employer's official leadership biography identifies her as Chief Advocacy Officer, America’s Credit Unions, formerly Senior Vice President, Federal Relations at ACLI, with earlier roles at SHRM, the Department of Defense, and the Nevada Governor's Office. These substantive biography details are missing from the live person's work/background features. Her April 20, 2026 appointment announcement supplies a concrete start date for the current role. The public biography is supporting evidence for a coverage gap, not sufficient evidence for arbitrary person-to-person links or overlap dates for her earlier roles.

Sources checked:
- https://www.americascreditunions.org/about-us/leadership
- https://www.americascreditunions.org/news-media/news/kathleen-coulombe-starts-americas-credit-unions-chief-advocacy-officer
- https://www.americascreditunions.org/news-media/podcast/episode-17-get-know-our-chief-advocate

No biography assertions were automatically promoted to route edges, no source identities were merged, and no production spine activation occurred in this repair. Follow-up reconciliation should attach sourced roles and dates to the existing confirmed identity, then establish specific overlapping colleagues from evidence. LDA remains ecosystem evidence rather than staffer-population qualification.
