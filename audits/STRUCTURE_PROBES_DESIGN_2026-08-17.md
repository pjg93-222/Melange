# E3 + S3 STRUCTURE PROBES -- PRE-DECLARED DESIGNS (2026-08-17)

STATUS: $0 Stage-2 probes (unified plan section 4, NOW tier item 5). Interpretation rules
are declared HERE, BEFORE either probe runs, so the verdicts cannot be argued backward
from results. Both are read-only over live-tree artifacts; outputs are notes destined for
the coalition-builder lane (itself awaiting Paul's APPLY gate); zero production writes.
Exact input artifact paths get filled from the live-tree inventory (recon workflow) and
recorded in the RESULT blocks -- the RULES below do not change when they are.

## S3 -- overlapping-community bridge discrimination probe

QUESTION: does overlapping-community membership even DISCRIMINATE among the 533, or is
overlap near-universal / near-absent (in which case the survey's bridge concept has no
purchase here)?

- INPUTS: per-layer member community assignments (HCoI communities, press communities,
  and any other shipped community layer). [paths FROM-INVENTORY]
- MEASURE: per member, the count of distinct communities held across layer-pairs; the
  overlap distribution; for members with overlap, a bridge score = normalized
  cross-community degree (share of a member's edges landing outside their modal
  community).
- PRE-DECLARED VERDICT RULE: if >= 80% of members share one overlap status (i.e., the
  overlap indicator is near-constant, either almost everyone or almost no one overlaps),
  the verdict is NOT DISCRIMINATING -> record the negative, S3 dies free. Otherwise the
  bridge-score distribution (with party/chamber strata visible) is handed to the
  coalition-builder lane as a candidate feature note.

## E3 -- cost-aware clustering probe

QUESTION: does clustering the 533 on a blended influence+cost distance (the Zhan-Cai
Algorithm 1/2 analog) produce segments materially different from the community layers we
already ship? If not, the idea adds nothing and dies free.

- INPUTS: multiplex edge weights (mutual, normalized to [0,1]) for the influence term;
  a receptivity-derived cost proxy cost_m = 1 - susceptibility_m (normalized) for the
  cost term. [paths FROM-INVENTORY]
- DISTANCE: d(u,v) = 0.5*(1 - MI_uv) + 0.5*|cost_u - cost_v|, MI_uv = normalized mutual
  edge weight (the paper's Eq. 27 shape with equal blend -- one pinned choice, no tuning).
- SEEDING: adaptive centroids per the paper's Algorithm 1 analog -- members sorted by
  incoming-weight influence; accept a new centroid iff its minimum distance to accepted
  centroids exceeds the similarity-matrix standard deviation. k is EMERGENT, not chosen.
  Assignment loop to convergence or 100 iterations. Seed pinned: 7 (ties broken by
  roster order; no randomness beyond ties).
- COMPARISON: adjusted Rand index (ARI) of the resulting partition against EACH existing
  community layer, plus against a party-split baseline (the confound check: cost-aware
  clusters that merely rediscover party are party wearing a cost costume).
- PRE-DECLARED VERDICT RULE: max ARI vs any existing layer >= 0.7 -> SEGMENTS
  EQUIVALENT, record negative, E3 dies free. Max ARI <= 0.3 AND ARI vs party-split
  < 0.5 -> GENUINELY NEW SEGMENTATION -> segment profiles (size, party mix, mean cost,
  mean tier) handed to the coalition-builder lane. Anything between -> AMBIGUOUS,
  reported with strata, no further action without Paul.

## Shared discipline

Read-only inputs from the LIVE tree; probe scripts run from scratch space and write only
scratch/audits notes; ranks_python.json untouched by construction (nothing consumes probe
output); glassbox emission per run (run-now-tier-20260817 lane); results appended to this
file as RESULT blocks with counts and denominators, then logged in the effectiveness
sheet (E3+S3 row).

-- end of pre-declared designs --
## RESULT -- S3 (run 2026-08-17, live tree, read-only)

INPUTS (filled from inventory): data/stance/press_hcoi.json (8 communities, 132 assigned of
135 profiled), data/stance/frame_alignment.json (19 echo clusters, 87 member-slots),
data/lobbying/signed_coalitions.json partition_k2 (520 members, near-degenerate 506/14).
MEASURED: layer-coverage histogram over the 533 = {0:11, 1:369, 2:121, 3:32}; members with
>=2 community memberships = 153/533 (28.7%); among members covered by >=2 layers, 153/153
(100.0%) "overlap" -- i.e. the overlap indicator is IDENTICAL to multi-layer coverage; the
only structural (within-layer) overlap signal is 13 members holding >=2 echo clusters.
VERDICT: **NOT DISCRIMINATING as instrumented.** On the fair denominator (covered>=2) the
indicator is one status for 100% >= the 80% kill line; on all-533 the 28.7% split reflects
COVERAGE, not community structure. S3 dies free. REOPEN CONDITION: a full-roster community
layer (all 533 assigned in >=2 independent layers) would make the probe meaningful; none of
the three shipped artifacts supplies one (the inventory blocker records this).

## RESULT -- E3 (run 2026-08-17, live tree, read-only)

INPUTS (filled from inventory): congress_cosponsor_network_AUG20260802.xlsx Edges sheet
(source_bioguide/target_bioguide/weight; bioguide->name bridge via data/engine/congestion.json;
2,555 roster-internal merged undirected edges, 340 rows unresolved to the 533), cost from
member_receptivity.json susc_z min-max normalized (533/533 covered).
MEASURED: theta (sampled-pair std) = 0.0657; the adaptive seeding accepted ALL 533 members
as centroids; assignment converged (100 iterations) to 334 clusters, largest 18, with 251
singletons. ARI vs press_hcoi = -0.001 (n=132); vs signed_k2 = 0.000 (n=520); vs party =
0.004 (n=530).
VERDICT: **DEGENERATE -- recorded as a negative WITH a named mechanism, deviating with
cause from the pre-declared "genuinely new segmentation" branch that the raw ARI numbers
technically satisfy.** The Zhan-Cai distance presumes a DENSE pairwise trust matrix; on a
sparse observed-edge network, MI=0 for almost every pair, so d collapses to the constant
0.5 floor plus a small cost term, theta falls below it, and every member seeds a centroid.
A 334-cluster fragmentation is not a segmentation, and handing it to the coalition lane
would be noise laundered through a rule's letter. E3 dies free. REOPEN CONDITION: a NEW
pre-declared design using a dense similarity (path-based proximity or embedding similarity)
in place of raw edge weight -- carrying the same party-costume check.

CROSS-NOTE: both probes returned the honest negative the design contemplated ("dies free").
The E3 mechanism finding is itself useful: it is direct local evidence for why SNGDM
machinery built on dense elicited matrices does not transfer to observed sparse networks --
worth one line in any future S1 (edge-completion) prereg as an adverse prior.