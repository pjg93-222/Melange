# Moneyball Audit Completion Report — Run 5 Channel Publication

Date: 2026-07-16  
Worktree: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\moneyball-tier-option-b0ff84`  
Live data root: `C:\Users\pgoff\OneDrive\Desktop\Melange Systems`

## Outcome

The speech, hearing, and interview exclusion gates were removed from the normal publication path after their data passed structural integrity checks. These three channels now default **on** and populate the Press side of the Legislative+Press tier score. Each retains an emergency rollback through `CU_SPEECH_CHANNEL=0`, `CU_HEARING_CHANNEL=0`, or `CU_INTERVIEW_CHANNEL=0`.

Bluesky remains out of the Press-side injection because its events already enter through the social corpus. Enabling the separate Bluesky sidecar would double-count the same evidence.

The published display-tier weights remain **80% Legislation / 20% Press**.

## Data-integrity result

The spreadsheet/CSV integrity audit checked row count and order, `bioguide`/member/date/category identity, required values, category vocabulary, stance/tier vocabulary, dates, freshness, exact duplicates, and cross-channel text duplicates.

| Channel | Source/final rows | Gold-tier final rows | Signed rows admitted | Members reached | Publication policy |
|---|---:|---:|---:|---:|---|
| Floor speeches | 294 / 294 | 215 | 163 | 73 | Gold plus confidence-weighted learned tiers |
| Hearings | 775 / 775 | 263 | 189 | 64 | **Gold only** |
| Interviews | 37 / 37 | 37 | 25 | 16 | Gold plus confidence-weighted learned tiers |

Results: zero row-alignment errors, identity errors, invalid categories, invalid stance/tier values, invalid dates, required blanks, exact source duplicates, or cross-channel text duplicates. All final sidecars were fresh relative to their source and gold inputs.

The 512 non-gold hearing rows remain visible for review and future labeling but contribute exactly zero to scoring. This is deliberate because hearing attribution has greater witness/member collision risk. Hearing events are also normalized by member/date so passage segmentation cannot multiply one appearance's weight.

## Implemented fixes

- Added a shared `own_source_stance_model.py` reader stack: registry/rule read, local word+character TF-IDF read, transfer-gold read, grouped out-of-fold meta-reader, and gold applied last.
- Rewired the speech, hearing, interview, and Bluesky wrappers to the shared model and standardized their 11-column provenance sidecars.
- Put all own-source stance builders before `build_media_blend` in the canonical pipeline.
- Made speech, hearing, and interview default-on after validation; retained explicit fail-closed stale-artifact and unknown-tier behavior.
- Set learned-tier weights to gold `1.0`, unanimous `0.9`, majority `0.6`, and review `0.35`; hearings accept gold `1.0` only.
- Kept Bluesky single-counted in Social rather than injecting it again into Press.
- Added persistent full-audit guards for gate state, loaded state, sidecar row identity/freshness, hearing gold-only admission, and Bluesky single-counting.
- Preserved the prior 80/20 tier policy, exact placement overrides, and the rule that every Tier 1 member is automatically a Champion.

The rebuilt media blend changed 2,038 workbook cells, then the full downstream tier, optimizer, dashboard, and member-desk pipeline was republished successfully.

## Ranking impact

| Preferred-name check | Before channels | After channels | Current stance |
|---|---:|---:|---|
| Andy Barr | Tier 1 #1 | Tier 1 #1 | Champion |
| Roger Williams | Tier 1 #11 | Tier 1 #5 | Champion |
| Young Kim | Tier 1 #5 | Tier 1 #6 | Champion |
| William Timmons | Tier 1 #7 | Tier 1 #7 | Champion |
| Bill Hagerty | Tier 1 #6 | Tier 1 #9 | Champion |
| Brian Fitzpatrick | Tier 1 #10 | Tier 1 #12 | Champion |
| Tim Scott | Tier 1 #3 | Tier 2 #13 | Ally |
| Cynthia Lummis | Tier 2 #14 | Tier 2 #19 | Ally |

The explicit Tier 1 placements for Brian Fitzpatrick, Roger Williams, and Bill Hagerty remain intact, and every current Tier 1 member is a Champion.

Tim Scott is now one position below the fixed 12-member Tier 1 bucket. His admitted new evidence consists of three supportive gold speeches and no hearing/interview rows. Other members gained broader new channel coverage, and the channel/category p80 rescaling changed his relative Press score from `0.48418` to `0.37808` (`press_raw` from `0.30595` to `0.24133`). With Press limited to 20%, his strong Legislative score still places him #13, but there is no evidence-integrity defect justifying a silent placement override. Moving him back to Tier 1 would require an explicit roster decision or changing the fixed bucket size.

## Verification

- Shared learned reader, all four sidecars: regenerated successfully.
- Artifact-tool channel audit: clean.
- Focused channel, gate, and 80/20 regression suite: **61 passed**.
- New permanent-audit regression contract: **passed**.
- Canonical downstream pipeline: completed successfully in **16.9 minutes**.
- Full-body audit after publication and after adding permanent guards: **125 passed, 0 failed — ALL MODULES CLEAN**.
- No files were staged or committed; the pre-existing dirty worktree was preserved.

One first publication attempt encountered a transient Windows workbook replacement lock after channel calculation. It published no mixed downstream generation. The workbook handle subsequently tested clear, and the complete retry plus full audit succeeded.
