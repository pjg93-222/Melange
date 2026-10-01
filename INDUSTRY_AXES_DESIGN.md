# Industry Axes — design spec (tensor generalization)

STATUS: SPEC — phase 1 (CU axis) SHIPPED 2026-08-10 (@c54ed56); later phases
are USER-GATED, nothing below builds without Paul's go per phase.
Author: Fable, 2026-08-10, from Paul's directives "should we have the share
primacy be along an axis?" / "3 dimensional axis … multiple industries at the
same time" / "Ship the CU axis now, spec the tensor after".

## 1. Problem

`bill_beneficiary_tags.ndjson` gives each act ONE exclusive `class`. The
per-industry boards reweight classes through per-industry maps, so the scalar
class is secretly a flattened product of two independent judgments:

    weight[act, industry] = relevance[act, industry] x valence[act, industry]

Flattening loses information, and every defect found in the 2026-08-10 board
work traces to that loss:

- Warren topped the crypto board (valence missing on own-industry acts) —
  fixed by the valence ledger (one un-flattened slice).
- STABLE/GENIUS promotion to crypto_primary silently stripped their CU credit
  although ACU declared SUPPORT — an act cannot be "crypto AND CU-relevant"
  under an exclusive class. Evicted two user-ratified desk seats. Fixed by
  the CU relevance axis (a second slice).
- Cross-board ripples (Gillibrand crypto 7->9, Donalds bank 1->5) are the
  0.15 cross-industry default acting as an unadjudicated relevance guess.

## 2. Target shape

A sparse tensor over (act, industry) with two adjudicated dimensions and one
metadata dimension per cell:

    industry_axes[act_key][industry] = {
        relevance:  0.0..1.0     # how much the act is about X's space
        valence:   -1.0..+1.0    # direction of operative effect on X
        confidence: 0.0..1.0     # evidence grade (metadata, not physics yet)
        basis:      str          # operative-text | declared-position |
                                 # revealed-lobbying | class-default
        rationale:  str
        adjudicated_by / adjudicated / status
    }

Member score on industry X keeps today's physics exactly (CORRECTED
2026-08-10 at phase-4 build: the shipped physics — including the entire
ratified CU lineage — has always used the UNWEIGHTED role-credit
denominator; the earlier draft showed a relevance-weighted denominator no
system ever ran):

    factor_raw = sum(role_w * relevance * valence) / sum(role_w)

A relevance-weighted denominator would be a DIFFERENT physics (it moves
every board) and is recorded here as a rejected-for-now variant requiring
Paul's ratification, never a silent upgrade.

`class` remains the TOPIC HOME for display and for the producers; cells
override its effective weight per (act, industry). MECHANISM (as built):
each adjudicated cell relabels the act in that industry's in-memory view to
a synthetic scoped class weighted round(relevance x valence, 6) — the same
proven machinery the valence ledger uses; the ledger's rows are the
diagonal cells and the tensor file owns everything else, with a one-owner
conflict guard between them.

### Default fill (day-one byte-compatibility)

Unspecified cells derive from `class` via the current maps: own-primary
(1.0, +1), shared (0.5, +1), cross-industry (0.15, +1), offtopic (0, 0),
oppose (1.0, -1 on the CU axis). A tensor with zero adjudicated cells
reproduces today's boards bit-for-bit — that is the acceptance gate for the
loader.

### Overlay order (later layers win only where they have data)

    class-default  <  declared-position  <  operative-text adjudication

## 3. The three dimensions — ruling recorded

Dimensions 1-2 (relevance, valence) are the tensor. For Paul's "3rd
dimension" question, the candidates and the recorded recommendation:

- MAGNITUDE / stage (enacted vs one-pager): REJECTED for primacy — the
  primacy factor is deliberately stage- and volume-blind (recorded intent).
  If wanted, it becomes a SEPARATE impact board, never a primacy input.
- CONFIDENCE as shrink weight: measurement-honest, semantics-preserving.
  Candidate for dimension 3 AFTER the 2-D tensor is live and observed.
- TIME: mostly carried by per-congress act keys already; revisit only if
  cross-congress drift becomes visible in adjudications.

Decision deferred until the 2-D tensor has run long enough to show whether
the residual hunger is "impact" or "certainty".

## 4. Phases

- PHASE 1 — CU axis (SHIPPED @c54ed56): `acu_position` floors the CU-map
  weight (SUPPORT >= 0.5, OPPOSE = -1.0) inside the engine; non-CU scoped
  boards do not inherit (`ACU_RELEVANCE_ACTIVE` swap). This is the
  declared-position overlay for the CU column only, keyed off data that
  already exists on every tag row. Constants pinned in
  `_constants.acu_position_relevance` + cross-validated by industry_tiers.
- PHASE 2 — own-industry valence (SHIPPED earlier 2026-08-10): the 115-row
  `data/lobbying/industry_valence_adjudication.ndjson` is the operative-text
  overlay for the diagonal cells (act's own industry). Its loader contract
  (strict own-primary scope) RELAXES in phase 4 to any (act, industry) cell.
- PHASE 3 — declared positions for bank/crypto/fintech (PILOTED 2026-08-10;
  SOURCE CORRECTED): there is NO LobbyView positions dataset (its network
  file carries no bill identifiers). The real lane is the LDA-filings Haiku
  classifier (bill_positions_kim.jsonl, 22,617 org-bill pairs; reconnected
  to the interaction ledger 2026-08-10 via lobby_position_join.py
  --variant kim_llm4 — note the ledger regen lane wipes positions, so the
  join must rerun after any lda_rebuild). BANK-COLUMN PILOT VERDICT (Paul
  "pilot the bank column"): with explicit-bill-mention filtering and
  paragraph adjudication, the lane CORROBORATES but cannot autonomously
  sign — Support labels are plausible, Oppose labels dissolve on primary
  text ~70% of the time (Farm-Credit "Opposition" bled onto ACRE; the
  disapproval-resolution double-negative confuses the model; laundry
  lists). STANDING RULE, empirically grounded: inferred positions enter
  the tensor as RETRIEVAL + adjudication evidence only, never as automatic
  weights (one pilot product: ABA's explicit S.381 opposition upgraded
  that row's confidence 0.8->0.9). Still open before any wider phase-3
  use: the org-position->industry-position aggregation rule (Paul), and
  the sector_spend.ROSTERS vs collect_lobbyview classify_client scope
  divergence (Discover/Synchrony/Amex/Western Alliance).
- PHASE 4 — the sidecar tensor proper (MACHINERY SHIPPED 2026-08-10,
  empty-tensor byte-identity gated; first cells pending adjudication): new
  `data/lobbying/industry_axes.ndjson`, one row per adjudicated cell;
  loader merges cells onto class defaults via the synthetic scoped-class
  mechanism (see MECHANISM note in section 2 — the in-memory relabel IS the
  tensor's application layer; the engine's scalar map is untouched).
  Acceptance: empty-tensor run byte-identical boards (the four rows arrays;
  receipts gain declared additive keys only); ranks_python 0/533.
- PHASE 5 (optional, separate surface) — impact board using magnitude/stage;
  never mutates primacy.

## 5. Revealed-relevance (phase 3b, additive evidence only)

`bill_lobbying_sidecar.json` organizations-per-bill = revealed relevance
(who actually lobbied the act). Usable as EVIDENCE feeding adjudication
rationales, never as an automatic weight (only ~23% of lobbying cites bills;
absence is not irrelevance — the sidecar's own caveat).

## 6. Invariants that survive every phase

- CU desk method untouched unless Paul re-ratifies (exact-533 parity gate).
- ranks_python.json 0/533 for every phase (primacy is display-plane).
- Ratified-seat guards (audit_full.py:1622) adjudicate conflicts to Paul —
  never weakened to make a phase pass (H-3 law).
- Every adjudicated cell is row-level overridable (status=inactive) and the
  all-inactive state must reproduce the class-default boards.
- Fable signs adjudications; Paul overrules row-by-row; nothing is claimed
  user-ratified without his explicit word.

## 7. Known residual at spec time

Young Kim's ratified CU seat (tier 2 <= 14) sits at rank 19: her PACE Act
sponsorship carries no ACU position, so the axis restores nothing there.
Resolution is Paul's: re-ratify at the corrected rank, or top up her
`primacy_adjudication_ledger` credit. Huizenga restored (14 <= 16) by
phase 1.
