# Member personal relationships — full-history revision

The current implementation is the full-history revision requested after the two
earlier pilots. Start with
`outputs/member_personal_relationships/20260910_full_history/REPORT.md` and
`research/MEMBER_PERSONAL_RELATIONSHIPS_V3_MATH.md`. The earlier implementations
below are retained as historical artifacts, not the current methodology.

The revision includes all 61,085 stored H.R./S. bills in Congresses 116–119,
full-service opportunity propensities, shared third-party cosponsorship,
withdrawal and original-signature history, the complete weighted cooperation
network, positive personality compatibility, and speaker-relative rhetoric.
It computes all 282,492 directed pairs for the frozen 532-member roster.
Reviewed statements support documented and inferred relationships; work-only
screens remain candidates. Ideology and state overlap define comparison
groups and never receive negative friendship weights.

Rebuild in this order (standard library plus NumPy):

```powershell
python -m fec.research.member_personal_relationships.prepare_history
python -m fec.research.member_personal_relationships.history_speech
python -m fec.research.member_personal_relationships.run_history
python -m fec.research.member_personal_relationships.report_history
python -m fec.research.member_personal_relationships.verify_history
```

Inspect any pair, including pairs outside the shortlist:

```powershell
python -m fec.research.member_personal_relationships.query_history "Chrissy Houlahan" "Don Bacon" --bills
```

`history_reviews.json` adds source-context reviews to the original frozen anchor
ledger. The results report links to 37 pair dossiers containing all shared bills
and directional support lists. Tests include independent bill recounts, full
matrix reconciliation, identity traps, late joins, distinct reintroductions,
withdrawals, personality direction, and source integrity. Rebuilding decision
outputs is deterministic. The frozen current roster and personality snapshot
are reused; the dated legislative and speech coverage is expanded.

No production social-network file is changed. The current comparison context is
coarse and retrospective; no friendship probabilities or sincerity probabilities
are claimed. See the mathematics document for every rule and limitation.

## Earlier pilots (superseded)

This is an executable research prototype of the [framework](../../../research/MEMBER_PERSONAL_RELATIONSHIPS_IMPLEMENTATION.md). It extracts source candidates, accepts explicitly reviewed personal evidence, computes personality compatibility and signed personal-network features, and compares co-sponsorship with politically comparable opportunities. It produces **review candidates**, not calibrated friendship probabilities. Production ranks and network files are read-only inputs.

The first run covers the stored roster as of September 10, 2026, with a 24-month speech window and all-topic 119th-Congress House/Senate bills. It samples 160 unordered pairs and assesses both directions. No independently labeled friendship/antagonism test set exists in this pilot.

From the repository root, using Python 3.12:

```powershell
python -m fec.research.member_personal_relationships.prepare
python -m fec.research.member_personal_relationships.run
python -m fec.research.member_personal_relationships.verify
python -m fec.research.member_personal_relationships.report
```

On this workstation, the Python executable used is `C:\Users\pgoff\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe`.

Only source preparation needs PyYAML 6.0.3. Its isolated pure-Python archive is at `tmp/relationship_yaml.zip`; a normal PyYAML installation is also usable. The build and tests use the standard library. No production modules that execute builders at import are imported. Modules are import-safe; the CLIs write only their output directory. Use a fresh `--out outputs/member_personal_relationships/<run_id>` for a new preparation/build. The bundled verification/report commands target the first pilot directory.

The frozen preparation and source manifest make the existing run reproducible without querying the speech database again. `run` verifies input hashes and fails if inputs or the frozen extraction have changed. `verify` executes all tests, rebuilds the pilot, compares artifact hashes, and checks production hashes. Source updates require a fresh preparation. The reference snapshot paths are explicitly pinned in `data.py`.

**What the scores mean**

`affinity_candidate_score` is an unfitted review-priority index. It adds the number of reviewed positive episodes to three weak proxy components: 0.15 times positive personality similarity above matched peers; 0.30 times the hyperbolic tangent of positive personal-network resource allocation; and 0.30 times positive cooperation residual rate, shrunk by n/(n+20). At least two positive indirect channels nominate an `indirect_candidate`; that is not a threshold validated against friendships. Negative episodes have their own count and neither low personality similarity nor negative cooperation residual produces dislike. Both probability fields remain null.

The E/A/O similarities are exp(-absolute standardized trait distance), averaged over available traits. Matched comparisons require the same observed trait set and at least five peers. C/N and directed E-ego/A-alter values are exported but have no fitted effect in this first run. Trait priors are hypotheses transferred from the supplied friendship literature, not congressional estimates of friendship likelihood.

For work, A's signature on B's bill in days 0–30 is compared with A's support for other sponsors in the same party/state/ideological-distance/leadership stratum and policy area. All A→B observations are removed from A's baseline. Topic cells shrink toward that member's broader political stratum with 20 pseudo-observations; at least 20 non-focal comparison opportunities are required. Same-chamber dated service must cover the whole window; original co-sponsors count; withdrawals are retained in the bill audit because the outcome is first joining, not continued endorsement. Exact same-sponsor introduction-title duplicates are collapsed. A 7-day sensitivity is exported.

The baseline uses current Voteview/status snapshots and is a **retrospective descriptive comparison**. State match is a coarse geographic control. Committee service, precise district distance, donor ties, caucus membership, bill popularity, and other unmeasured incentives can still explain residuals. Sparse strata remain unavailable rather than receiving a general fallback friendship score.

Personal graph calculations remove the focal pair in both directions and its source families before constructing degrees, paths, overlap, resource allocation, and 16 directed signed motifs. Legacy public-reference graphs only help choose review strata and produce diagnostics. They never seed personal edges. Shared enemies never automatically imply friendship.

**Review and evaluation**

`review_decisions.json` contains the assistant's auditable coding of 27 deliberately selected source cases. `official_verification.json` records checks against the original Congressional Record for the four retained accounts. These are source checks, not independent gold labels. `events.ndjson` preserves accepted and rejected decisions; `review_queue.ndjson` contains the remaining retrieved candidates. Unknown means insufficient evidence, not neutrality.

Before estimating predictive accuracy: expand the dated personal seed ledger, establish independent human labels, exclude both directions and all linked source families in hidden-pair folds, rebuild personality measurements without relationship-label source material, strengthen geographic/institutional controls, and evaluate temporal/member holdouts and matched-stratum ablations. The current ablations measure changes to an exploratory index only.

Outputs: `outputs/member_personal_relationships/20260910_pilot/REPORT.md`, `PAIR_REVIEW.md`, `EVIDENCE_REVIEW.md`, `results.json`, `verification_receipt.json`, and the NDJSON ledgers and hash manifests.
# Fitted extension (second pilot, September 10, 2026)

`python -m fec.research.member_personal_relationships.verify_anchored` builds the
anchor-supervised extension, runs both versions' tests, verifies deterministic
output, and writes reports under
`outputs/member_personal_relationships/20260910_anchored`.

The editable evidence is `anchor_catalog.json`; accepted v1 evidence is retained.
`anchored_model.py` implements fitted logistic and positive-unlabeled residual
rankers. `run_anchored.py` performs pair/source-family holdouts, member-disjoint
holdouts, matched anchor recovery and ablations. The results are retrospective
and exploratory. Scores are not calibrated relationship probabilities. Read
`REPORT.md`, `ANCHOR_REVIEW.md`, `INFERRED_RELATIONSHIPS.md`, and `VALIDATION.md`
in the output folder before using the machine-readable relationships.

No production network is modified. Unknown relationships are never gold negative
labels. In the PU selection model they are explicitly an unlabeled comparison
class. All graph features use reviewed evidence and never predicted edges.
