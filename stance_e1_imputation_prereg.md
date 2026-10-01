# PREREG DRAFT -- E1: network-KNN stance-cell imputation as a display-flagged estimate layer

STATUS: **DRAFT -- NOT LOCKED.** Written 2026-08-17 under D-010 (Paul's affirmative reading
of unified-menu item 6: the desert-fill estimate-layer precedent extends to stance '-'
cells) and D-009 item 5 sequencing (F1 locks first; this draft queues behind it). Locking
is a separate Paul-visible step; no look may be taken while this header reads DRAFT.
D-010's reversal condition stands: if Paul states he intended the NO branch, this file is
withdrawn and the 062ce9 categorical-refusal wording is reinstated.

## Claim under test

A network-KNN imputer over observed cosponsorship/committee/donor-overlap edges, weighting
neighbors by edge strength x stance-profile similarity on co-known cells (the Zhan-Cai
Eq. 11-17 shape localized), can estimate MASKED KNOWN stance cells better than all four
pre-declared baselines. A PASS licenses only a DISPLAY-FLAGGED estimate layer (IMPUTED
badge everywhere rendered, true '-' never silently overwritten, PERS_NONE pricing of '-'
in every engine untouched); it licenses NO engine consumption of imputed values.

## Design (to be frozen at lock)

- Mask-and-recover on KNOWN cells only: a pinned random mask (seed recorded at lock) hides
  20% of non-'-' cells; the imputer sees the rest plus the network; recovery error is the
  measure. The '-' cells are NEVER training or evaluation targets -- per D-010 they are the
  eventual display application, reached only through a PASS on known-cell recovery.
- Baselines (all four must be beaten, each pre-declared): (i) global mean; (ii) PARTY mean
  (the homophily-circularity gate); (iii) row/column marginal model; (iv) the existing
  pflip network-proximity prediction restricted to the masked cells (the redundancy gate --
  unified plan section 2.1 bar (ii): machinery that only rediscovers existing peer terms
  adds nothing).
- Metric: MSE on masked cells, reported per stratum (party x chamber x coverage tercile)
  with denominators; the ALL-must-hold bar binds on the pooled MSE, strata are honesty
  reporting per D-007.
- Endogeneity rule (adopted from the source paper's own flaw): every downstream figure that
  ever mixes imputed and real cells is reported real-cells-only beside augmented.
- Missingness honesty: coverage indicators enter the imputer's inputs explicitly; the
  neutral-fill masquerade documented in the collinearity audit is named as an adverse prior.

## Bars (ALL must hold; DRAFT values -- final at lock)

1. Pooled masked-cell MSE < each of the four baselines' MSE (paired on identical masks).
2. Margin over the PARTY-mean baseline >= 10% relative MSE reduction (a bare win over
   party homophily is not enough to justify an estimate layer).
3. Margin over the pflip-proximity baseline >= 10% relative (the redundancy gate has teeth).
4. Stability: across three pinned mask seeds, the baseline-beating pattern (1-3) holds in
   every replicate; any flip = FRAGILE = MISS.

## Battery (must pass before the look; refusal = RETIRED WITHOUT A LOOK)

(a) Planted signal: cells regenerated from a known network-smooth synthetic must be
    recovered (imputer beats baselines by construction on the plant).
(b) Null: with edges shuffled (degree-preserving), the imputer must NOT beat baseline (i)
    -- an imputer that wins on shuffled networks is fitting marginals, not structure.
(c) Confound: on a synthetic where party alone generates cells, the imputer must NOT beat
    baseline (ii) -- party wearing a network costume must fail here.

## Outcomes and consequences (fixed wording at lock)

- PASS -> a .candidate estimate-layer artifact consumed by nothing; display integration is
  a separate Paul-gated surface change under the mockup law; engine consumption is BARRED
  by this prereg permanently (a future engine use would need its own prereg naming this one).
- MISS or FRAGILE -> route closed; kill-ledger entry; the '-' ontology stands untouched.
- Battery refusal -> RETIRED WITHOUT A LOOK, successor gate pinned in the RESULT.

## LOCK block (empty until Paul ratifies; F1 locks first per D-009 item 5)

- [ ] Edge-source artifacts + sha256:
- [ ] Mask seeds (three):
- [ ] Stance matrix vintage sha256:
- [ ] Baseline implementations fingerprinted:
- [ ] Bars confirmed / amended by Paul:
- [ ] Lock date + Paul sign-off:

## READY-TO-LOCK ADDENDUM (2026-08-17; assembled by the coordinator, lock = Paul)

F1 locked earlier today (@5534eedd2), so the D-009 item-5 sequencing gate is satisfied.
The harness is MERGED and flag-gated: fec/tools/e1_stance_imputation_harness.py
(@a4cb54151, merged @ce592baaf, 41 tests, consumed by nothing). Its --look mode refuses
to run unless --lock-file names a prereg containing the LOCKED marker and no DRAFT
marker, and real-data runs additionally require --allow-real-data — the lock discipline
is code-enforced, not procedural. Everything below is staged for Paul's signature; the
LOCK block checkboxes above stay unchecked until he signs.

### Input pins (sha256 computed 2026-08-17 at main @ba4f19853)

| Input | Artifact | sha256 |
|---|---|---|
| Stance matrix source | category_stance.json | 412f14017cfad5cfed419b7de05482917a05d547eb0a6a2f348b37597986253e |
| Members source | data/engine/congestion.json | ddc9d746600dbdfc60b76c54537662e19c758cbfb9d7a478a71b7bf90cd727a6 |
| Edge layer 1 (cosponsorship) source | congress_cosponsor_network_AUG20260802.xlsx | 55c11019c761976c0bef4065278482cf75e1b3c30d8e274924e5af4c5b48b009 |
| pflip baseline (iv) source | per_topic_alloc.json | c18cdd0544c82ec5a7643bedb756cf46ca1f353d070827db402cad4ed3c8dcec |
| CANDIDATE edge layer 2 (hearing/press co-appearance) | data/network/co_appearance.json | fbc4bfa485ee4ad0bc4e1137624b4bd5dc20542cc82e89a4ef5367d5c2b7d1c3 |
| Baseline implementations (all four live in the harness) | fec/tools/e1_stance_imputation_harness.py | d83841cb1bafc9537d7cefacb4c560a1758793c20884cd80be10754382cafe97 |
| Harness test suite | fec/tests/tools/test_e1_stance_imputation_harness.py | ec6264de2593ea9cdfa3fc7f6d254ad4d163c71930ce106a6ab36759a90cea56 |

The cosponsorship vintage is the OPERATIVE one: select_network_file picks the newest AUG
workbook by mtime — today that is AUG20260802 — so the imputer sees exactly the network
pflip sees. Derived harness inputs are cut mechanically at lock from these pinned sources
(rules below), and their sha256s are stamped into the LOCK block at cut time.

### Derivation rules (mechanical; no judgment at cut time)

- stance matrix CSV: category_stance.json matrix -> header member_id,<category...>,
  one row per member, '-' preserved verbatim (the harness parses '-' as no-position and
  NEVER uses those cells for training or evaluation, per D-010).
- members CSV: congestion.json -> member_id,party,chamber,coverage_count.
- edge CSV per layer: source adjacency -> member_a,member_b,weight, undirected keys
  (min,max), mean-symmetrized exactly like moneyball_core.load_network, sorted rows.
- pflip predictions CSV: per_topic_alloc.json -> member_id,target,prediction restricted
  to the masked cells at evaluation time (the harness enforces the header).

### Proposed seeds (pinned at lock)

- Mask-recover replicates (three): 424242, 565656, 787878.
- Battery seed (the battery mode takes exactly one): 313131.
- Deliberately disjoint from the F1 battery seeds (535353/646464/757575) so no seed is
  ever shared across preregs.

### PAUL DECIDES AT LOCK (the one open design choice)

Edge-layer roster. The prereg names cosponsorship/committee/donor-overlap. Layer 1
(cosponsorship, weight 1.0) is pinned above. There is NO shipped donor-overlap edge
artifact — building one is an FEC export task that would delay the lock. Options:
  (a) lock 1-layer (cosponsorship only) — cleanest, weakest network;
  (b) lock 2-layer adding co_appearance.json as the committee/hearing proxy layer
      (candidate pin above; Paul sets its weight multiplier, e.g. 0.5);
  (c) hold the lock for a donor-overlap export (executor-lane task, adds days).
The choice changes what "network" means in the claim under test, so it is Paul's, not
the coordinator's. Whichever roster is chosen is written into the LOCK block verbatim.

### Bars (restated for confirmation; unchanged from the Bars section above)

1-4 as drafted: beat all four baselines on pooled masked-cell MSE; >=10% relative margin
over PARTY-mean; >=10% relative margin over pflip-proximity; stable across all three
seeds (any flip = FRAGILE = MISS). Battery (a)/(b)/(c) must pass before any look;
refusal = RETIRED WITHOUT A LOOK.

### Battery RUN (2026-08-17, official pre-look gate; Paul: "Run all")

BATTERY_PASS at the proposed battery seed 313131 -- all three probes:
PLANTED_PASS / NULL_PASS / CONFOUND_PASS. Synthetic fixtures only (zero real data
touched; nothing spent). Canonical constant-prediction pflip input generated exactly as
the suite's PASS path does. Evidence committed at audits/e1_lock_20260817/:
battery_313131.json sha256 87f9954718a0319cb1ebfd939dc4d6a7dc2dd356ad9f8f5373d496ddd437a6c8;
battery_pflip_313131.csv sha256 fcd1ed148e14a946023288a6c0cecf6fe71486e1d65babf4ad121c1f8d1d7eb3.
If Paul amends the battery seed at lock, the battery reruns at the amended seed before
any look.
