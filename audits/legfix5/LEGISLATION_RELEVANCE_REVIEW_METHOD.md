# Legislation Relevance and False-Positive Review Method

**Status:** binding draft for the Congress.gov six-year coverage run  
**Primary discovery instrument:** Congress.gov Legislation Advanced Search  
**Core rule:** discovery is intentionally broad; promotion and exclusion are
evidence-gated.

## 1. Preserve the recall corpus

Every Congress-qualified measure returned by an in-scope Advanced Search query
remains in the discovery corpus. A candidate may be included in a category,
excluded from that category as a reviewed false positive, or left unresolved.
No candidate is deleted. Every exclusion remains visible in the exclusion
ledger alongside its reason, source, reviewer, and timestamp.

Search-query membership, a generic occurrence of `Act`, a short acronym title,
or the absence of a trusted press article is never enough to include or
exclude a measure.

## 2. Evidence order for an unclear bill

Review the official Congress.gov record in this order:

1. Confirm the Congress-qualified bill identity and official title.
2. Read the official summary when the title is not dispositive.
3. Read the operative provisions when the summary is broad, ambiguous, or
   missing. Prefer the provision that creates, changes, repeals, exempts,
   prohibits, requires, authorizes, directs, or funds the relevant policy.
4. Use the frozen pre-2026-07-25 press corpus as corroboration and as a pointer
   to an action. Article absence is not negative evidence, and article evidence
   never assigns Sponsor, Original Cosponsor, Cosponsor, or Withdrawn status.

The official title can establish relevance when it is specific and
unambiguous. A named statute in bill text is only a reference until a localized
operative action shows what the bill does to that statute or to the
credit-union industry.

## 3. Named-Act specificity

- `Act` alone is always non-evidence.
- A short alias such as `SMART Act`, `CLARITY Act`, or `GENIUS Act` is a
  non-scoring recall probe. It requires Congress-qualified identity plus the
  complete official title or operative provisions.
- A base-statute name such as `Federal Credit Union Act` must appear as the
  complete, ordered, token-bounded name.
- Mere mention of a named statute is unresolved. Category evidence additionally
  requires a legislative action in the same official-text segment.
- Query operators such as quotes and `~5` are search syntax, not evidence
  tokens.

## 4. Inclusion test

Include a category membership only when at least one official source
affirmatively shows a material industry connection:

- the official title is specifically about the relevant credit-union or
  financial-services policy;
- the official summary describes a material effect on credit unions, NCUA,
  credit-union members, covered financial institutions that include credit
  unions, or the category's regulated activity; or
- an operative provision creates or changes a duty, authority, exemption,
  cost, benefit, eligibility rule, market structure, funding stream, or
  enforcement exposure material to the industry.

Multi-topic bills may belong to more than one category. Relevance to a
credit-union category must not be discarded merely because the bill's primary
policy area is broader.

## 5. False-positive exclusion test

Exclude a category membership only after official evidence affirmatively shows
that the apparent hit is unrelated, for example:

- a different bill sharing the same short title or acronym;
- a Congress/bill-number collision;
- a lexical collision such as transportation `interchange`;
- a named statute appears only in a definition, citation, conforming reference,
  or unrelated provision; or
- the operative provisions regulate a different industry or activity and do
  not materially reach credit unions or the category.

Uncertainty is not an exclusion. Missing summary/text, weak evidence, or no
article leaves the membership unresolved.

## 6. Required decision record

Every manual `include` or `exclude_false_positive` decision must contain:

- `canonical_key` and `query_id`;
- `disposition`;
- `reason`;
- `evidence_basis`, one of `congress_qualified_identity_mismatch`,
  `explicit_named_outline_bill`, `official_title`, `official_summary`,
  `operative_provisions`, or `official_title_and_provisions`;
- `evidence`, containing a Congress.gov URL plus a concise quoted or
  paraphrased official passage;
- `reviewer`; and
- `reviewed_at`.

The automated system may prioritize cases and present exact contexts, but it
does not make semantic exclusions. Only explicitly named, Congress-qualified
outline bills bypass manual membership review.
