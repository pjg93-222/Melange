# Legislation culling and corpus-integration architecture

Version: §acu-legislation-culling-integration-v1§

## Objective

Audit all 18,557 discovered candidates and 64,004 candidate/query memberships
without deleting discovery evidence, overcorrecting category relevance, or
allowing an incomplete review into scoring. Congress.gov Advanced Search is
the primary collection instrument. Quorum is a recall floor only and never an
authority for collection, adjudication, or scoring.

## Control flow

§§§mermaid
flowchart TD
    A[Preserved 55-file ranking baseline] --> B[62-query Congress.gov discovery]
    B --> C[Immutable candidate and membership corpus]
    C --> D[Official evidence join]
    D --> E[Membership-level adjudication]
    E --> F{Candidate partition}
    F -->|Any included membership| G[Keep]
    F -->|Every membership excluded with complete high-confidence evidence| H[Reversible junk pile]
    F -->|Anything unresolved or incomplete| I[Flagged review workbook]
    G --> J[Hash-bound accepted generation]
    H --> J
    I --> K[Integration blocked]
    J --> L[Shadow recomputation]
    L --> M[Rank-drift review]
    M --> N[Pre-sync and current full regression]
    N --> O[Explicit promotion decision]
§§§

The discovery corpus is immutable throughout. Keep, junk, and flagged are
views over the corpus, not destructive moves.

## Evidence envelope

Each candidate receives one §acu-legislation-candidate-evidence-v1§ envelope
bound to its original discovery line. The envelope contains:

- canonical Congress/type/number identity and all query memberships;
- discovery path, file hash, and exact record hash;
- official title and its text hash;
- latest nonempty official CRS summary and its text hash;
- accepted official full-text HTML receipt, body hash, exact final URL, typed
  main-surface marker, and challenge checks;
- versioned identifier/keyword results for title, summary, and full text,
  including positive spans and an explicit rule that absence is neutral;
- actions and derived bill stage, bound to an actions hash;
- sponsor, original cosponsor, later cosponsor, and withdrawn relationship
  edges with Bioguide identity and role provenance;
- source gaps, including an explicitly unavailable CRS summary.

A missing summary or full text does not become negative evidence. It keeps the
membership in the flagged queue.

## Two levels of culling

Category relevance is adjudicated at the natural key
§(canonical_key, query_id)§. A measure can be a false positive for one query
while remaining relevant to another.

Candidate-wide junk status is stricter. It requires all of the following:

1. Every discovered membership has a final §exclude_false_positive§ decision.
2. Every decision cites the official title, CRS summary, and full text.
3. Full-text keyword/identifier rule-out is complete for that membership.
4. Reviewer confidence is high and the decision is human-ratified or an
   officially reverified preexisting decision.
5. No article or press absence is used as exclusion evidence.
6. The exclusion is appended to the hash-chained junk ledger and remains
   separately restorable.

Any included membership prevents global junk status. Any unresolved or
incompletely evidenced membership is exported to the flagged workbook.

## Artifact boundaries

| Layer | Authoritative artifact | Mutation policy |
|---|---|---|
| Baseline | §audits/legfix5/PRE_LEGISLATION_RANK_CONTROL_2026-07-25.json§ | Read only |
| Discovery | §congress_advanced_records.ndjson§ and §congress_advanced_memberships.ndjson§ | Immutable |
| Official metadata | GovInfo BILLSTATUS parsed records and receipts | Immutable enrichment |
| Official full text | R harvester accepted HTML and receipt trees | Immutable, resumable |
| Candidate evidence | §candidate_evidence.ndjson§ | New hash-addressed generation |
| Membership review | §membership_review_ledger.ndjson§ | New hash-addressed generation |
| Global junk | Append-only exclusion/restoration ledgers | Reversible only |
| Human review | §flagged_memberships.xlsx§ plus NDJSON source | Review surface only |
| Accepted data | §accepted_legislation_relationships.ndjson§ | Staged generation only |
| Corpus integration | Approved generation, shadow outputs, and receipts | No production write before terminal gates |

Excel is a review surface, never the sole authority. Every workbook row maps
back to an NDJSON natural key and immutable evidence hashes.

## Main-corpus integration

Integration reuses the existing fail-closed sequence:

1. §build_accepted_legislation_generation.py§ validates discovery,
   reconciliation, membership decisions, and relationship roles.
2. §assemble_approved_legislation_generation.py§ packages only hash-verified
   authoritative inputs in an audit directory.
3. Direction, numeric-plan, and role-method approvals are attached.
4. §run_legislation_shadow_recompute.py§ recomputes outside production.
5. Rank deltas are compared with the preserved 55-file baseline. Large or
   unexplained movement blocks promotion; no assumption is made that ranks
   must remain unchanged.
6. Pre-sync, downstream-readiness, formula-cache, role-attribution, and
   current full-regression gates must all pass against the same hashes.
7. Promotion remains a separate explicit action. Passing the architecture
   gate never writes the main corpus automatically.

## Terminal acceptance gates

The executable gate list is defined in
§fec/legislation_culling_integration_contract.py§. It includes:

- complete registry/discovery/reconciliation and Quorum-floor recall audit;
- completed identifier-probe revalidation;
- accepted full text for every candidate with no unresolved failures;
- an exact 18,557-candidate and 64,004-membership evidence partition;
- zero unresolved membership adjudications;
- an audited reversible junk ledger;
- complete stage/action and sponsor/original-cosponsor/cosponsor provenance;
- hash-bound accepted generation and shadow recomputation;
- reviewed rank drift against the preserved baseline;
- current pre-sync and full-regression receipts.

Until all gates pass, the contract reports §BLOCKED§ and explicitly records
that scoring, synchronization, promotion, and main-corpus writes did not occur.

## Parallel execution plan

While full-text collection continues, offline workers may safely perform:

- BillStatus title, summary, actions, stage, and relationship normalization;
- evidence-envelope construction for already accepted full-text records;
- membership proposals that remain §unresolved§ until ratified;
- incremental flagged-workbook generation;
- junk-ledger integrity audits and baseline drift preparation.

Only the R collector writes full-text artifacts. Only a single coordinator
writes each generation manifest. Workers write disjoint hash-addressed files,
then the coordinator reconciles counts and hashes. This prevents checkpoint
collisions and the corruption seen in the prior oversized/browser workflow.