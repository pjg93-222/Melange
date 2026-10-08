# Live comparison and remaining evidence gaps

Routing revision: `97527f770f56a8d885b1`. Live runtime PID: `24612`.

The route-diversity implementation passed its checks. Personal introduction quality has not been validated. These are distinct findings.

## Comparison

| Search | Result |
|---|---|
| after_ranked | GORDON HOLZBERG → Michael P Darner → Mike Casca<br>GORDON HOLZBERG → Cora A Thompson → Michael P Darner → Mike Casca<br>GORDON HOLZBERG → Michael P Darner → Diana Rudd → Mike Casca |
| after_distinct | GORDON HOLZBERG → Michael P Darner → Mike Casca<br>GORDON HOLZBERG → Cora A Thompson → Maria L Laverdiere → Mike Casca<br>GORDON HOLZBERG → Bryashia Buggs → Tommy C Wolfe → Mike Casca |
| after_independent | GORDON HOLZBERG → Michael P Darner → Mike Casca<br>GORDON HOLZBERG → Hailey Barringer → Tommy C Wolfe → Mike Casca<br>GORDON HOLZBERG → JOHN GREEN → Ellis A Brachman → Mike Casca |
| after_avoid_darner_distinct | GORDON HOLZBERG → Cora A Thompson → Maria L Laverdiere → Mike Casca<br>GORDON HOLZBERG → Bryashia Buggs → Tommy C Wolfe → Mike Casca<br>GORDON HOLZBERG → Gabrielle K Gould → Christopher Rackens → Mike Casca |
| after_avoid_darner_independent | GORDON HOLZBERG → Cora A Thompson → Maria L Laverdiere → Mike Casca<br>GORDON HOLZBERG → Hailey Barringer → Tommy C Wolfe → Mike Casca<br>GORDON HOLZBERG → JOHN GREEN → Ellis A Brachman → Mike Casca |
| after_gordon_work | insufficient_work_coverage |
| after_work_distinct | Merrilee Rogers → Liz Amster<br>Merrilee Rogers → Joe Valente → Liz Amster<br>Merrilee Rogers → Catarina Pereira → Liz Amster |
| after_work_independent | Merrilee Rogers → Liz Amster |
| after_work_office | Merrilee Rogers<br>Merrilee Rogers → Joe Valente<br>Merrilee Rogers → Stephanie Gray |

## Shared-role stress test

The first Darner-excluded portfolio still contained shared-employee or administrative-office flags in every route. Cora Thompson, Maria Laverdiere and Tommy Wolfe have shared-employee stint-summary flags on the selected evidence. The John Green–Ellis Brachman step relies on broad administrative-office overlap. Distinct names and workplaces alone did not fix these evidence-quality problems.

A further query conservatively excluded the six contacts identified in the receipt (Darner plus the flagged contacts), then repeated the separate-workplace search. Its third result was:

**GORDON HOLZBERG → GREGORY MESACK → Sarah Jacobs → Tevye F Johnson → Diana Rudd → Mike Casca**

[Open this test in the live interface](http://127.0.0.1:8841/staffer-live/?route_model=evidence_cost&route_count=3&alternative_strategy=independent&avoid_people=person%3Ahill%3Aperson%3A0516ded6d6b623850300877be9778aae820293a6307deeb0dbead395dc018cbf%2Cperson%3Ahill%3Aperson%3A27789dfa726f24f041a3e107b6f18bd125715e65bff7e027818ae3ef1c6e5a9e%2Cperson%3Ahill%3Aperson%3A61a351e7eccfd4b4d8138b5fd3fe0a9814104b263dfcc4a940c0ab066e5935b8%2Cperson%3Ahill%3Aperson%3Aea95f936343e552508f0273fe4c1f2b05f52a6e005e84ccf0d970425ee7a8fcc%2Cperson%3Ahill%3Aperson%3Af253a521f705138d79d9ce6b8aac89efd76530b6cafb2e9d7bb955da75aae049%2Cperson%3Ahill%3Aperson%3Af4da00148a15c2e44e577a0ea2799ab3319bab13f352f29d9f8abfe09fe7a81c&route_origin=person%3Ahill%3Aperson%3A3c5c98a62501db5461f553baeb6951498db922df1379dd88232d9987cf949579&route_target=person%3Ahill%3Aperson%3A15a178e5e7aa800aa071006d01e9541b9cb6ea622065ab6dd577b3f0a140e2e6) — choose Route 3. Exclusions can be removed in the interface.

| Connection | Recorded basis | Limitation |
|---|---|
| Gordon → Greg Mesack | Existing user statement of current coworking | Coworking is not a promise to introduce |
| Greg Mesack → Sarah Jacobs | One shared issue/reporting period, Q4 2021, NAFCU | Reported activity does not establish direct interaction |
| Sarah Jacobs → Tevye Johnson | Madeleine Dean office overlap, 2022-04-19 through 2025-06-24 | Present willingness unknown |
| Tevye Johnson → Diana Rudd | Speaker’s office overlap, 2022-01-12 through 2022-04-08 | Present willingness unknown |
| Diana Rudd → Mike Casca | Democratic Caucus overlap, one supplied day in 2012 | Very old, thin evidence; a critical weak link |

No shared-employee/admin flag appears in this candidate’s selected provenance. That is not proof that every role was substantive, every identity is correct, or that the introduction is usable. The test removes whole contacts using summary flags rather than classifying each role on the exact overlap day. It is a sensitivity experiment, not a global blacklist or proof of exhaustive high-quality reachability.

## Practical conclusion

The next model change must address which evidence can support personal closeness in the ecosystem layer. Administrative/shared-role associations need their own evidence class and contextual treatment before comparing them with sustained direct teamwork. Role summaries alone should trigger visible uncertainty, not be treated as exact daily assignments. Where authenticated coverage is missing, report the gap rather than silently substituting an association score for a staffer closeness score.

The current release makes diversity and exclusions explicit and exposes shared/admin evidence notes. It deliberately does not claim that more paths, higher centrality, or a generic uncertainty coefficient recovers unobserved willingness.

## Checks

- 55 focused Python regression tests passed.
- 8 JavaScript tests passed.
- 121 guarded restart integration tests passed.
- Nine live route/office cases passed behavioral assertions, including uncertainty score identities.
- The additional role stress test retained full route provenance.
- Browser verification covered restored endpoints/exclusions, both alternative modes, displayed routes and map rendering.
- Served HTML and JavaScript matched workspace bytes.

These checks establish implementation behavior, not introduction-success calibration.
