# Filing versions: what changes, what is proposed as the default, how to flip it

> **Update 2026-09-19: APPLIED as `12a880dc9`**, on Paul's instruction to finish this lane's open items, with
> the proposed default (`count_latest`). The VERSION 4 index was rebuilt and published the same night
> (`out/v4_index_build.log`). To take it back: `git revert` that commit and rebuild the index; the VERSION 3
> published files are kept in the session scratchpad under `v3_index_backup/`. The status block below is
> the proposal as it was written, before it was applied.

> **Status: PROPOSED, NOT APPLIED.** Nothing in `C:\Users\pgoff\Mentat` has been
> changed. What is live there is the **VERSION 3** transfer index, built and
> published on 2026-09-19 with the 25 preserved filing headers, and PAS2 parser
> **"4"**. Everything below describes what the attached patch would do if you
> apply it, measured in a scratch copy.

## What is wrong today

The counting rule treats every set of rows sharing `committee | report type |
transaction id` as competing versions of ONE transaction, and withholds all of
them unless a verified filing header settles the family. That key is not an
identity. Filers reuse a schedule line label as the transaction id, so rows with
nothing to do with each other collide and are all dropped.

**Example 1 - three real independent expenditures, all dropped.** Committee
C00864926 labels every Schedule E row `SE.5`. Three of its 2024 rows share
report type `12P`, so they land in one "version group":

    04/08/2024  INVICTUS ADVERTISING    $29,685   candidate H0IN03198  filing 1779689
    02/12/2024  DEL CIELO MEDIA LLC     $997,600  candidate H4TX26149  filing 1759197
    05/09/2024  WHISTLESTOP STRATEGIES  $10,454   candidate H4TX12065  filing 1788908

Different vendors, dates, amounts and candidates. Today all three are excluded.
Filing headers cannot fix this: they would pick one and silently drop the other
two real expenditures.

**Example 2 - one transfer counted as five.** Committee C00010603 filed the same
$1,480,000 transfer to the Democratic Party of Virginia five times inside filing
1573863, identical in every field except the FEC sub-ID. Today the rule withholds
all five; counting all five would book $7.4M. Only one of them is real.

On top of that, one ambiguous row today blacklists the whole source committee, so
its clean transfers stop allocating as well.

## The rule

1. Inside a version group, a row's identity is its counterparty, amount, date and
   transaction type.
2. The same identity in a later filing is that transaction re-reported: keep one,
   mark the rest superseded (by verified header order where headers establish the
   family, otherwise by the FEC's highest-filing-number convention).
3. The same identity repeated inside one filing is one itemization loaded twice:
   count it once. Two genuine equal gifts carry two transaction ids, so they are
   in different groups and both still count.
4. An identity nothing competes with is a separate transaction that merely reuses
   the label: count it, flagged so the reuse stays visible.
5. Competing representations in different filings that no counterparty tells
   apart keep their dollars: the highest filing number is counted and flagged
   `unverified_version`. Withheld rows never blacklist a committee - they enter
   its outflow denominator as an explicit unresolved share.

## The measured effect (committee-to-committee cash, all three cycles)

| committee-to-committee cash | VERSION 3 (today) | VERSION 4 |
|---|---:|---:|
| counted transfer dollars | $9,761,520,102 | **$9,839,756,394** |
| dollars lost to a blacklisted committee | $152,497,610 | **$0** |
| dollars held back as unresolved | $52,615,213 | **$325,734** |
| committees whose clean transfers stop allocating | 119 | **0** |

## The one judgement call, and what is proposed

Point 5 is the only place where the evidence runs out: same recipient, different
amount or date, different filings, no filing header. It is either an amended
figure or two transactions and nobody can tell.

**Proposed default: count the latest filed version, flagged `unverified_version`.**
Three reasons. Your standing ruling for this system is that a row loses its
amount only where evidence CONTRADICTS it, and that missing or ambiguous
information keeps its dollars under an unverified flag - neither of these rows
contradicts the other. The latest filed version is the FEC's own convention, and
it is what index v2 and parser "3" already did. And counting the latest is never
further from the truth than withholding both: if the pair is an amendment it is
exactly right; if it is two transactions it undercounts by one row, where
withholding undercounts by two.

Setting the constant to `withhold` instead would move **$65,000** of that counted total back out, raising the reported unresolved share from $325,734 to $390,734 and the number of committees carrying one from 6 to 9.

On committee-to-candidate activity the same switch is worth **$117,349**: the default counts $117,349 that `withhold` would leave out.

To take the other reading instead, set `AMBIGUOUS_VERSION_POLICY = 'withhold'` in
`mentat/tools/fec_transfer_graph.py` and `FEC_PAS2_AMBIGUOUS_VERSION_POLICY <-
"withhold"` in `mentat/R/fec_beneficiary.R`. Both constants are part of their
cache keys, so nothing stale is ever served back.

## What applying it takes

1. `git -C C:\Users\pgoff\Mentat apply <path>\filing_version_identity.patch`
2. Rebuild the transfer index at VERSION 4. **Not optional.** The R side refuses
   a v3 index as stale, and a stale index makes every transfer-derived number
   zero while raising only a `warn` - the report would ship silently gutted, the
   way it did while the v2 index was the newest one on disk.
   `python mentat\tools\fec_transfer_graph.py --directory <fec_beneficiary dir>
   --cycles 2022 2024 2026 --filing-header-directory
   mentat\state\cross-reference\filing-headers`
3. The PAS2 cache invalidates itself: the parser version in its signature moves
   from `p4` to `p5c`, so the next run reparses.
4. Then rebuild the workbooks yourself, as usual.
