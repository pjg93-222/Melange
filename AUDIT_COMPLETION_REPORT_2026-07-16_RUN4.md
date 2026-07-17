# Moneyball Audit Completion Report — Run 4 Follow-up

Date: 2026-07-16  
Worktree: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\moneyball-tier-option-b0ff84`  
Live data root: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`

## 80/20 tier policy

The Legislative+Press display-tier formula is now source-controlled at:

- Legislation: **80%**
- Press: **20%**

The fixed placement contract and 12/24/48 bucket sizes remain active. The full downstream pipeline was republished from stance synchronization through optimizer, dashboard, member desk, and full-body audit.

Final Tier 1 / Champion roster:

1. Andy Barr
2. Daniel Meuser
3. Tim Scott
4. Ritchie Torres
5. Young Kim
6. Bill Hagerty
7. William Timmons
8. Kevin Cramer
9. French Hill
10. Brian Fitzpatrick
11. Roger Williams
12. Katie Britt

Cynthia Lummis is Tier 2, tier rank 14, and displays as Ally.

## Press/media pipeline status

Active in the published Press/media score:

- dynamic press component from the current `cu_press_stance_tone.csv`;
- `press_stance_final.csv` stance stack;
- evidence-first press domain routing;
- exact press gold overrides;
- two-year press recency decay;
- own-domain weight 1.0 and third-party attribution weight 0.5;
- the tweet stance stack on the social half of the Press/media blend.

Published dynamic press metadata:

- routed source rows: **2,388**
- signed press articles used: **1,171**
- members with nonzero press signal: **288**
- stack-signed rows: **1,562**
- legacy DEBATE fallback rows: **0**
- exact gold overrides: **26**
- own-domain articles: **634**
- third-party articles: **537**

Integrated in code but default-off and therefore **not included** in the current published Press score:

| Channel | Artifact rows | Directional rows | Fresh | Runtime gate |
|---|---:|---:|---|---|
| Floor speech | 294 | 140 | yes | off |
| Committee hearing | 775 | 584 | yes | off |
| Interview | 37 | 25 | yes | off |

Bluesky is already consumed through `Social Master.xlsx`; the separate Bluesky channel refuses a second injection to prevent double-counting.

## Verification

- Canonical downstream pipeline: completed in **10.7 minutes**.
- Embedded full-body audit: **`ALL MODULES CLEAN.`**
- Targeted regression contracts: **36 passed, 0 failed**.
- Tier buckets: **12 / 24 / 48**.
- Overall Champion set: exactly equal to Tier 1.
- Optimizer certificate: valid; certified gain ratio **1.0**; concavity violations **0**.
