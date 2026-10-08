# Opus 5 employment date/identity micro-review

- Stage: `R0a2a4a1-opus5-employment-date-identity`
- Model/effort: Claude Opus 5 / maximum
- Mode: read-only
- Verdict: `BLOCKED`

## Blocker

Top-level `lda_source_person_id` and nested
`person_identity.lda_source_person_id` were not compared. When both were
nonblank and disagreed, the top-level ID silently won and an otherwise valid
record could be marked `COMPLETE`
(`fec/staffer_network/employment_history.py:454-465`, pre-fix).

The coordinator accepted the blocker, added an explicit whitespace-normalized
conflict check and negative fixture, reran 47 focused tests and the full Python
suite (221 tests plus 73 subtests, zero failures), and required a post-fix Opus
review.

## Checks that passed

- Malformed, prose, impossible, and far-future dates fail closed.
- Current markers require as-of evidence and as-of-before-start is rejected
  under the supported precision bounds.
- Employment episodes require HTTP(S) source evidence and start/end bounds.
- Blank, whitespace, missing, and `UNRESOLVED` identity values fail closed.
- Validation failures are append-only and cannot be cleared before status
  derivation.

## Nonblocking findings

The episode digest does not include identity; the future-date guard permits the
next calendar year; coarse same-year as-of uncertainty may not prove an exact
before-start relation; non-boolean current markers are not treated as current;
and naive ISO datetimes fail closed with a coarse missing-date reason.

This preserved BLOCKED verdict is not overwritten by the local repair; only the
fresh post-fix review can resolve it.
