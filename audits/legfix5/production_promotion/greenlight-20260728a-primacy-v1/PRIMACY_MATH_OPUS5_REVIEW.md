# Primacy math review — Opus-5 method, local Codex execution

Date: 2026-07-29

## Decision

The prior slots 10–13 were display pins. They are removed.

The replacement is a score input, not a placement rule: each active row in
`primacy_adjudication_ledger.ndjson` enters the existing beneficiary numerator
and denominator exactly like one classified role. The five current rows use
one uniform rule:

```text
role_weight = 1.0
beneficiary_class = cu_primary
act_weight = 1.0
```

The rest of the ratified formula is unchanged:

```text
factor_raw =
    sum(role_weight × act_weight) / sum(role_weight)

lambda =
    min(1, agenda_credit / 15)

factor_shrunk =
    roster_baseline + lambda × (factor_raw - roster_baseline)

tier_score =
    Leg% × factor_shrunk
```

No member has a fixed tier or position. The conduct ladder still applies
after score order and can only move a constrained member down.

## Computed result

| Member | Control rank | New rank | New score |
|---|---:|---:|---:|
| Tim Scott | 10 | 6 | 0.570391 |
| Bill Huizenga | 13 | 7 | 0.566220 |
| Young Kim | 14 | 11 | 0.561581 |
| Brad Sherman | 18 | 12 | 0.560269 |
| Catherine Cortez Masto | 16 | 13 | 0.558310 |

The control ranks above have all display placements disabled and include the
conduct ladder.

## Scope and stability

- Official rank and score delta: **0**
- Display-rank changes: **41 of 533**
- Members unchanged: **492 of 533**
- Median absolute display-rank delta, all members: **0**
- Maximum absolute display-rank delta: **6**
- Paid API/provider calls: **none**

## CFPB contract

The CFPB direction ledger remains unchanged:

- reducing or restraining CFPB authority is industry-aligned and positive;
- expanding CFPB authority is negative;
- neutral CFPB measures remain neutral.

The local Opus-5-method replay used complete supplied evidence, treated
absence as neutral, and preserved mixed evidence rather than forcing it into a
one-sided finding. Codex executed the replay locally; no Anthropic/OpenAI paid
API was called.

Machine-readable receipt:
`primacy_math_opus5_review.json`.
