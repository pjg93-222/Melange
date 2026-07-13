# Source-primary multimethod Big Five promotion gate

**STATUS: LOCKED 2026-07-12 before the package-disjoint reliability build and before the exact
permutation / production known-groups look.** The component evidence and one deterministic
five-by-five design diagnostic were already inspected before this lock; those point estimates are
therefore a re-derivation target, not a newly confirmatory result. The fresh promotion decisions are
the package-disjoint reliability battery, exact permutation tests, and generated production artifact.

## Fixed instrument

- O, C, E: LSA-256 open-vocabulary member features, computed separately within CREC, interview,
  and social venues, standardized within venue, token-weighted across available venues, then one
  Ridge model per trait against breadth, diligence, and visibility. Validation scores are nested
  five-fold out-of-fold predictions; production scores refit the same fixed model on all eligible rows.
- A: inverse of the already-qualified raw interview-antagonism criterion. Reporter hostility,
  personal contempt, and gratuitous cruelty are included; policy conflict and principled dissent
  are excluded. Production uses the mean of the two package-disjoint halves. The opposite half is
  the independent validation criterion.
- N: the promoted affective-content N artifact. Validation pairs the LLM affective facet channel
  (pessimism, anxiety, depression, volatility; residualized on party and E) with the independently
  computed LIWC affect channel. ES is exactly `-N` for compatibility.
- Missing A is left missing. O/C/E/N retain their wider coverage; no A imputation or source-primary
  text-A fallback is permitted in this instrument.

## Fresh package-disjoint reliability build

Every CREC/interview speech package and every social post is assigned wholly to half 1 or half 2 by
SHA-256 parity. No package may occur in both halves. One full-corpus TF-IDF/LSA basis is fixed, both
halves are transformed through that same basis, and the full-corpus trait models score each half.
A uses its existing package halves. N uses the identical package split on interview LIWC affect.

All five traits must have Spearman-Brown reliability `>= .50`; any shared package or any trait below
the bar refuses promotion.

## Five-trait validity and contamination gate

Rows are independent instrument channels; columns are independent criteria:

| Row | Criterion column |
|---|---|
| O LSA out-of-fold | behavioral breadth |
| C LSA out-of-fold | behavioral diligence |
| E LSA out-of-fold | behavioral visibility |
| A inverse-antagonism half A | inverse-antagonism half B |
| N LLM affect | LIWC affect |

For every trait, the diagonal must be positive, exact one-sided permutation `p < .05`, larger in
absolute value than every other cell in its row, and larger in absolute value than every other cell
in its column. Required verdict: 5/5.

Known-groups is evaluated trait-by-trait on available production scores. Required signs of R-D are
O negative, C positive, E negative, A negative, N negative (equivalent to ES positive). Trait-specific
coverage is fixed because A is never imputed. Required verdict: 5/5.

## Promotion consequence

Only if reliability is 5/5, validity/diagonal dominance is 5/5, exact permutation is 5/5, the
known-groups signs are 5/5, and package overlap is zero may `big5_blue_validated.json` replace the
pooled lexical Blue on the member desk. Otherwise `big5_blue_emb.json` remains the last promoted
artifact and this candidate is retained as a failed result.
