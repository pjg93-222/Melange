# Moneyball Audit Completion Report — Run 2

Date: 2026-07-16  
Worktree: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\moneyball-tier-option-b0ff84`  
Live data root: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`

## Executive result

The interrupted audit has been completed, the optimized fixes have been applied, and the full canonical downstream pipeline has been republished.

- Canonical pipeline: completed successfully in 10.3 minutes after the final band correction.
- Full-body audit: **118 passed, 0 failed — `ALL MODULES CLEAN.`**
- Kernel regression suite: **72 passed, 0 failed.**
- Targeted TDD contracts: **33 passed, 0 failed.**
- Final pipeline lock: absent.
- Production optimizer certificate: valid, exact on its stated fixed-state discrete-concave scope.

## Findings and fixes

### 1. Tweet-image analysis and sentiment integration

Implemented a separate, auditable image-evidence reader instead of concatenating assumed image meaning into tweet text:

- Images are keyed by exact Quorum ID.
- An annotation must contain stance/CU alignment, confidence, provenance, media URL, and `review_status=approved`.
- High-confidence image evidence may resolve weak neutral/unrelated text.
- Image evidence cannot silently reverse a clear directional text read; disagreement is retained as `conflict-review`.
- Exact user-ratified tweet overrides remain the final authority.
- The X collector now requests and stores attachment/media metadata in `media_json`.
- `tweet_image_review_queue.csv` contains **275** historical candidates.

Important limitation: no historical tweet images were actually classified in this run. The current collector database contains **0 X posts from 0 members**, and the Quorum export does not contain resolvable attachment metadata. The pipeline now preserves and consumes image evidence correctly when media or approved annotations are available, but it does not invent image content.

This design follows the supplied Twitter-as-data excerpt's core evidentiary principle: preserve the original post and metadata, and treat non-text media as a distinct source with its own provenance.

### 2. Press domain labeling

Press routing was changed from permissive tag trust to evidence-first routing:

1. exact API article target;
2. title evidence;
3. body confirmation of declared categories;
4. residual General Credit Union only when no specific policy domain is established.

False-positive guards now block highway “interchange,” generic non-CU tax-exempt content, and community-bank mentions that lack competitive-policy content.

Final press ledger:

- Source rows: **2,388**
- Rows with unsupported declared categories discarded: **1,168**
- Unsupported declared tags discarded: **1,748**
- Residual General Credit Union rows: **505**
- Rows mixing General Credit Union with a policy domain: **0**
- No-policy-domain rows: **25**
- Unresolved-member rows: **2**, explicitly retained in the ledger rather than hidden

The two unresolved rows are James Moylan's shutdown resource guide and Stacey Plaskett's wastewater-system release.

### 3. Young Kim and CDFI

Young Kim is the unique member with a final CDFI score of **1.000**, so the category rank of #1 is correct.

Her category result has two layers:

- Raw CDFI stance: **Champion**
- Displayed CDFI stance: **Ally**
- Reason: the say/do gate found no accepted authored/original-cosponsored CDFI bill or aligned recorded final-passage vote for the category.

Her public CDFI advocacy is real, including the CDFI Fund support letter and Treasury questioning:

- https://youngkim.house.gov/2025/10/24/100-republicans-join-kim-crapo-in-support-of-cdfi-fund/
- https://youngkim.house.gov/wp-content/uploads/Kim-Crapo-CDFI-Letter.pdf
- https://youngkim.house.gov/2025/05/08/rep-young-kim-questions-treasury-secretary-bessent-at-financial-services-hearing/

Those actions are scored as advocacy evidence, but the ratified category Champion/Defender gate currently accepts only authored legislation or an aligned recorded vote. Expanding that gate to led letters or hearing advocacy would be a substantive policy change, so it was not done silently.

Young Kim is nevertheless an **overall Champion** because she is Legislative+Press Tier 1, tier rank **#7**.

### 4. General Credit Union score dispersion

The General Credit Union score is now handled correctly, but “dispersion” is deliberately fail-closed:

- When evidence names a real policy subject, it is routed to the corresponding policy column.
- Residual general CU support stays visible in the General Credit Union ledger.
- Residual General Credit Union evidence is not projected indiscriminately across all policy domains.

This prevents a generic CU mention from inflating unrelated issue scores. The final ledger has **505** residual General rows and **0** General-plus-policy mixed rows.

### 5. Andy Barr and the credit-card late-fee rule

Barr's actions opposing the CFPB late-fee cap are now treated as pro-CU support.

Exact support gold is applied to Quorum IDs:

- `511658226`
- `511657485`
- `498264314`
- `458365083`

The press item “House, Senate resolutions would void CFPB credit card late fees rule” is routed to both CFPB and Credit Card Mandates and scored as support.

Final Barr results:

- Credit Card Mandates score: **0.948**
- Credit Card Mandates stance: **Defender**
- CFPB score: **1.000**
- CFPB stance: **Champion**
- Legislative+Press tier rank: **#1**
- Overall display: **Champion**

Official corroboration:

- https://barr.house.gov/2024/4/barr-s-cra-to-nullify-credit-card-late-fee-rule-advances-out-of-committee
- https://barr.house.gov/2023/3/barr-mchenry-fsc-republicans-fire-shot-at-cfpb-over-credit-card-late-fee-proposal
- https://www.congress.gov/bill/118th-congress/house-joint-resolution/122/all-actions
- https://www.congress.gov/committee-report/118th-congress/house-report/618/1

### 6. Legislation sorting and hidden-row audit

The legislation scorer now selects one effective member/bill/Congress/domain event using the strongest role:

`sponsor > original cosponsor > cosponsor`

All source rows remain visible in `legislation_routing_audit.json`, including duplicates, exclusions, neutral overrides, and unmatched members.

Final legislation ledger:

- Source rows: **10,987**
- Ledger rows: **10,987**
- Selected scoring events: **7,560**
- Duplicate lower-role rows: **2,708**
- Duplicate same-role rows: **9**
- CDFI effective rows: **18**
- Data Privacy & Cyber effective rows: **528**
- Unmatched-member rows: **10**, explicitly listed as Stacey Plaskett (8) and James Moylan (2)

Pinned corrections:

- H.R. 7733 / 117 → CDFI Fund
- S. 869 / 118 → CDFI Fund
- H.R. 7036 / 118 → Data Privacy & Cyber
- H.R. 7022 / 117 → Data Privacy & Cyber
- S. 4698 / 117 → Data Privacy & Cyber

No legislation row is silently hidden; every input row has an auditable disposition.

### 7. Daniel Meuser's tier position

Root cause: Legislative and Press pillars were already normalized, but the tier display percentile-ranked them a second time. That second transformation exaggerated narrow differences and promoted Meuser to #1.

Fix: the tier now directly blends the existing normalized Legislative and Press pillar values using the live 30%/25% weights.

Final result:

- Legislative+Press tier rank: **#5**
- Overall rank authority: **#8**
- Overall display: **Champion**, because #5 remains inside Tier 1

Meuser is no longer #1.

### 8. Tier 1 automatically becomes Champion

The rule is now explicit and shared by the dashboard, workbook, and member desk:

> Legislative+Press Tier 1 is the complete and sufficient qualification for the overall Champion label.

The audit proves that the Champion set exactly equals the 12 Tier 1 members:

1. Andy Barr
2. Katie Britt
3. French Hill
4. Tim Scott
5. Daniel Meuser
6. Alex Padilla
7. Young Kim
8. Ritchie Torres
9. Bill Hagerty
10. Zachary Nunn
11. Kevin Cramer
12. William Timmons

### 9. Overall stance bands

The final v5 bands are fixed semantic prototype midpoints, not percentile/population quotas:

| Minimum | Base label |
|---:|---|
| 2.50 | Ally |
| 1.50 | Highly Persuadable |
| 0.75 | Persuadable |
| 0.25 | Lean Persuadable |
| -0.25 | True Neutral |
| -0.75 | Lean Skeptic |
| -1.50 | Skeptic |
| -3.00 | Highly Skeptical |
| below -3.00 | Opponent |

Champion is not a score band; it is the Tier 1 overlay.

This fixes the prior semantic inversion where positive records could land in skeptical labels. Katie Britt's score-only base is now **Ally**, and her final display is **Champion** because she is Tier 1.

Final overall display counts:

- Champion: 12
- Ally: 239
- Highly Persuadable: 137
- Persuadable: 76
- Lean Persuadable: 27
- True Neutral: 21
- Lean Skeptic: 3
- Skeptic: 2
- Highly Skeptical: 3
- Missing: 13

### 10. Defenders

Defenders were not removed. The final result distinguishes surviving Defenders from raw Defenders that lack accepted say/do corroboration:

Surviving:

- Andy Barr — Credit Card Mandates
- Andrew Ogles — Credit Card Mandates

Raw Defender, capped to Ally:

- Jason Smith — CU Tax Status
- Katie Britt — Interchange
- Ted Cruz — Interchange

The raw label and cap reason remain preserved in the category stance gate ledger.

## Additional audit findings

### CBDC polarity

The CBDC target had an inverted CU valence in the registry. It is now `-1`: CBDC development threatens CU deposit intermediation, so opposing or banning a CBDC composes to pro-CU support.

The tweet stack now enforces three-reader unanimity before manual gold. Warren Davidson Quorum IDs `620647802` and `615403327` now resolve to unanimous support across the registry, classical, and API readers.

### Max route versus flip route

The dashboard's Max route is now a closed-network cascade route using PageRank-style network importance, edge activation, out-degree effects, and cumulative path probability. It no longer reuses the direct-only flip-star logic.

The Flip route remains the direct conversion path. The two routes now answer different questions:

- Max: which network-edge cascade produces the strongest closed-network spread?
- Flip: which direct targets produce the best modeled conversions?

### Optimizer

Final production result:

- Mode: `fixed_state_lazy_greedy`
- Budget: **$2,500,000**
- Spent: **$2,500,000**
- Base objective: **109.083542**
- Final objective: **127.148916**
- Exact bound: **127.149**
- Certificate valid: **true**
- Fixed-state concavity verified: **true**
- Concavity violations: **0**
- Certified gain ratio: **1.0**
- Allocation recipients: **383**
- Conversion reachable: **false** under the current fixed stance state

The optimizer no longer overspends, no longer claims an adaptive guarantee, and reports its guarantee scope honestly.

### Config layering

The worktree code and live data root are separate. A deterministic layered-config loader now preserves live-only user rows while allowing matching worktree corrections to win by stable identity. This applies to tweet gold, press gold, image annotations, and the CU valence registry.

### Speech precision orphans

Two neutral speech-gold rows became unbound after the precision router correctly rejected their false domains:

- Kevin Kiley — high-speed rail
- Mariannette Miller-Meeks — concrete bridge

They are now retired only through a narrow `retired_precision_orphan` rule. Directional orphan gold still fails the audit.

## Rank-change report

Compared with the saved pre-audit rank-authority snapshot:

- Members whose overall rank changed: **479**
- Maximum absolute rank change: **140**

Largest changes:

| Member | Before | After | Delta |
|---|---:|---:|---:|
| Jack Reed | 365 | 225 | -140 |
| Sheldon Whitehouse | 193 | 298 | +105 |
| Keith Self | 435 | 348 | -87 |
| Troy Downing | 118 | 49 | -69 |
| Josh Hawley | 395 | 343 | -52 |
| John Hoeven | 132 | 181 | +49 |
| Russ Fulcher | 206 | 161 | -45 |
| Pete Aguilar | 173 | 212 | +39 |
| James Walkinshaw | 254 | 293 | +39 |
| Adelita Grijalva | 441 | 480 | +39 |

Named members:

| Member | Before | After | Delta |
|---|---:|---:|---:|
| Young Kim | 7 | 15 | +8 |
| Daniel Meuser | 10 | 8 | -2 |
| Andy Barr | 5 | 3 | -2 |
| Katie Britt | 9 | 6 | -3 |
| Warren Davidson | 58 | 75 | +17 |

The broad movement is expected because the correction re-routed the full live Press corpus, deduplicated the full legislation corpus by effective role, corrected registry polarity, and republished the dynamic Press pillar. Tier rank is a separate Legislative+Press display rank and should not be confused with the four-pillar overall rank authority.

## Key output artifacts

- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\category_stance.json`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\ranks_python.json`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\member_desk_bundle.json`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\dashboard_data.json`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Dashboard.html`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\cu-member-desk.html`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\optimize_result.json`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\press_domain_routing_audit.json`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\legislation_routing_audit.json`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\tweet_stance_final.csv`
- `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\tweet_image_review_queue.csv`

## Final disposition

All requested model, routing, band, tier, Defender, legislation, Barr, CBDC, dashboard-route, and optimizer corrections are implemented and published. The only unresolved capability is historical tweet-image acquisition: the analysis/fusion system is in place, but the current source data contains no X attachment records to analyze.
