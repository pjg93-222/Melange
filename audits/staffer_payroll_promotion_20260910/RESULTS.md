# Payroll promotion: observed change

## Coverage

| Work-route index | Directory only | Payroll and directory |
|---|---:|---:|
| Person records with indexed employment | 10,936 | 84,734 |
| Workplaces | 477 | 1,547 |

These are indexed source person records, including historical staff; they are not a count of current staff or a guarantee that every underlying human has only one identity.

## Gordon Holzberg → Mike Casca

Before: `insufficient_work_coverage`. Gordon could not enter the staffer model.

After: **GORDON HOLZBERG → Hailey M Barringer → Rene O Castellanos → Mike Casca**.

| Connection | Workplace | Overlap days | Observed concurrent headcount |
|---|---|---:|---:|
| GORDON HOLZBERG → Hailey M Barringer | 2014 HON. ALMA S. ADAMS | 395 | 15–21 |
| Hailey M Barringer → Rene O Castellanos | 2021 HON. KATHY E. MANNING | 331 | 13–21 |
| Rene O Castellanos → Mike Casca | 2019 HON. ALEXANDRIA OCASIO-CORTEZ | 285 | 21–29 |

The selected source titles are Senior Legislative Assistant / Press Secretary; Deputy Chief of Staff / Caseworker; and Field Representative / Chief of Staff. No shared-employee title appears in the selected evidence for this top route. The first two connections are enabled by payroll history; the final connection combines payroll and directory history.

This replaces the previous five-step ecosystem candidate through Greg Mesack with a three-step employment route. The old and new scores belong to different models and should not be compared numerically. The controlled directory-only comparison still cannot route Gordon.

The source records support longer workplace overlap than the previous candidate’s one-day 2012 endpoint connection. They do not establish present friendship or willingness. The existing uncertainty discount remains active; its value is an assumption-driven score adjustment, not an estimated success probability.

## Source scope

Payroll promotion is active in live staffer routing. The sealed historical graph and previously generated static member recommendation lists were not rebuilt. The source admission policy can be switched back to directory only for comparison. No name-based identity merge or friendship classifier was added.

## Validation

60 focused Python tests and 8 JavaScript tests passed. The guarded restart passed 121 integration checks. All six live comparisons passed and used the same routing revision. Full responses are retained in this audit directory.


## Alternatives and Darner exclusion

Explicitly excluding Darner did not change any of the three returned person sequences or their costs. The newly admitted work evidence, rather than the exclusion, displaced him.

1. GORDON HOLZBERG → Hailey M Barringer → Rene O Castellanos → Mike Casca
2. GORDON HOLZBERG → Michael P Cobb → Toni Dunbar → Jessica M Grandberry → Karla Santillan → Mike Casca
3. GORDON HOLZBERG → Sandra Brown → Caroline Drury → Bryce C Causey → Michelle Luna → Mike Casca

The stricter separate-workplace search returned two routes under its accumulated exclusions. The first was unchanged. Its second was GORDON HOLZBERG → Hunter Patterson → Isabel T Root → Whitley D O'Neal → Jacklyn E Rogers → Nicholas N Leingang → Mike Casca. This is a greedy conditional result, not proof that no other disjoint portfolio exists.

A comparison case, Merrilee Rogers → Liz Amster, retained its direct route. Its score changed from 0.423889 to 0.426213 as payroll filled additional coverage.

## Runtime cost

The complete three-route searches took 136.7 seconds with the expanded sources and 126.5 seconds with Darner excluded. The stricter workplace-separation search took 217.0 seconds. These include exhaustive alternative searches; the first route was found earlier. This is a material latency tradeoff of the expanded graph, not a reported improvement in model quality.

[Open the top payroll-enabled route](http://127.0.0.1:8841/staffer-live/?route_model=work_time&work_sources=payroll_and_directory&route_count=1&alternative_strategy=distinct&route_origin=person%3Ahill%3Aperson%3A3c5c98a62501db5461f553baeb6951498db922df1379dd88232d9987cf949579&route_target=person%3Ahill%3Aperson%3A15a178e5e7aa800aa071006d01e9541b9cb6ea622065ab6dd577b3f0a140e2e6&avoid_people=person%3Ahill%3Aperson%3Af4da00148a15c2e44e577a0ea2799ab3319bab13f352f29d9f8abfe09fe7a81c). The directory-only comparison remains available in the Employment history selector.
