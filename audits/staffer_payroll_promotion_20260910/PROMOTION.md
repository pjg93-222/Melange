# Payroll promotion: employment evidence before friendship inference

User-authorized scope: promote payroll history, measure the change, and return for consultation before proceeding into friendship inference.

## What was promoted

The live staffer route model now admits verified payroll trajectories and source-linked individual payroll entries alongside directory employment histories. Payroll-only people with eligible work evidence can serve as endpoints and intermediaries even when they are absent from the earlier directory-oriented operational admission set. This fills the specific coverage gap that prevented Gordon Holzberg from entering the staffer model.

Payroll retains its original source identity and provenance. It is not rewritten as a directory profile, merged with a namesake, or assigned a friendship label. The promotion is into the live employment-exposure index; the sealed historical graph and previously generated static member recommendation artifact are not rebuilt in this phase.

## How the data is handled

- Directory history and detailed payroll entries retain their source intervals and titles.
- Aggregate payroll trajectories fill intervals not already covered by detailed employment evidence for that person and workplace. This prevents a broad trajectory summary from overriding a detailed dated role.
- Duplicate and overlapping source intervals do not multiply exposure; the existing interval-union and concurrent-headcount logic still applies.
- Payroll titles and chamber/workplace kinds now reach that logic, including the existing shared-role dilution and exclusion of administrative containers from staffer exposure.
- A trajectory's last title remains explicitly labeled as a stint summary, not an exact daily assignment.
- Report-period and uncertain payment windows supply **modeled exposure**. Responses mark them as modeled, do not claim observed temporal overlap, and separate modeled interval days from documented overlap days.
- Filing-only associations and user coworker assertions are not silently converted into payroll employment. They remain available in their existing evidence layers.

The earlier directory-only source policy remains selectable with `work_sources=directory`. The new default is `work_sources=payroll_and_directory`. The UI preserves that choice in route URLs and shows employment sources and uncertainty notes.

## What stayed fixed for this comparison

The exposure formula, concurrent staff-size divisor, divided-work allocation, shared-role factors, hop penalty and uncertainty coefficients were retained. The bounded member context used for office destinations was not retuned. Person-to-person paths such as Gordon → Casca do not use that member centrality bonus.

This lets the comparison test the admission and use of payroll evidence before changing the relationship prediction target. Neither source mode estimates a calibrated probability of friendship or introduction success.

## Verification

The focused suite checks payroll-only endpoint admission, retained provenance, source-mode isolation, shared-role dilution, administrative exclusions, duplicate invariance, detailed-role precedence, uncovered interval filling, modeled-date disclosure and filter validation. Existing path and uncertainty oracles also run. Live results and population changes are recorded in `live_receipt.json` and summarized in `RESULTS.md` after the expanded graph finishes loading.
