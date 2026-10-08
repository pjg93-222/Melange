# Congress Speech and Audio Corpus Inventory

Generated: 2026-08-31 (America/New_York)  
Scope: the Congress speech, transcript, source-media, anchor, canonical-audio, exact-window, and recovery artifacts currently present in the Melange workspace and `C:\melange-data`.

## Executive snapshot

| Layer | Current holdings |
|---|---:|
| Official named-member universe | **537** |
| General verified audio profiles | **500 (93.1%)** |
| Strict identity-prerequisite profiles | **416 (77.5%)** |
| Non-floor descriptive profiles | **244 (45.4%)** |
| Remaining general-profile gap | **37** |
| Speech database rows | **269,585** |
| Speech database words | **57,765,095** |
| Source-media inventory packages | **52,311** |
| Source-media inventory turns / words | **153,063 / 12,460,346** |
| Accepted anchor recordings | **1,512 across 431 members** |
| Anchor audio | **119.255 hours** |
| Canonical manifest rows | **6,911 across 425 members** |
| Canonical manifest audio | **95.558 hours** |
| Logical exact non-floor windows | **24,524 / 54.498 hours** |
| Downloaded YouTube recovery recordings | **96 across 61 members / 11.165 hours** |
| Physical audio/video under `C:\melange-data` | **17,282 files / 58.852 GiB** |

These counts describe different layers and are not additive. A transcript package is not verified audio; a raw recording is not a labeled speaker cut; an anchor and canonical clip may represent overlapping speech; and logical exact windows usually point into immutable parent audio rather than duplicating the PCM into another file.

## 1. Roster universe

The reconciliation artifact currently names **537 people**. It is built from 533 local roster rows, five official additions, and one removal. The five additions are Aumua Amata Coleman Radewagen, Darline Graham, James C. Moylan, Kimberlyn King-Hinds, and Stacey E. Plaskett; Lindsey Graham is removed from this House-focused local roster reconciliation.

This is why a request for exactly 536 requires a named exclusion. The current reports do not silently discard a member to force the total to 536.

## 2. Full speech database

The read-only `social_media.db` inventory contains:

| Speech source | Rows | Distinct member labels | Words |
|---|---:|---:|---:|
| Interviews | 153,170 | 518 | 12,468,169 |
| Congressional Record | 106,107 | 509 | 43,721,108 |
| Hearings | 10,308 | 198 | 1,575,818 |
| **Total** | **269,585** | **532** | **57,765,095** |

The database has 53,696 distinct package identifiers. These are transcript/speech rows, not all current-member verified speaker-audio observations, and the distinct member strings may include historical or naming variants.

## 3. Source-media package inventory

`source_media_inventory_cumulative_current_snapshot.jsonl` contains **52,311 packages, 153,063 turns, and 12,460,346 words**:

| Source family | Packages | Turns | Words |
|---|---:|---:|---:|
| CNN | 33,785 | 67,603 | 4,927,030 |
| Fox | 7,081 | 30,203 | 2,367,926 |
| MSNOW/MSNBC | 5,721 | 16,112 | 1,284,679 |
| NPR | 2,013 | 6,147 | 381,273 |
| PBS | 1,809 | 6,241 | 476,550 |
| C-SPAN | 512 | 7,076 | 1,044,472 |
| NBC Meet the Press | 477 | 6,846 | 585,094 |
| ABC This Week | 299 | 1,673 | 123,783 |
| CBS Face the Nation | 294 | 6,366 | 436,023 |
| Hugh Hewitt | 220 | 2,573 | 294,631 |
| CSIS | 48 | 692 | 186,995 |
| CFR | 43 | 1,206 | 304,831 |
| CNN Axe Files | 6 | 251 | 32,999 |
| Aspen | 3 | 74 | 14,060 |

Discovery status across the snapshot:

| Status | Packages |
|---|---:|
| Needs probe | 42,464 |
| Blocked: no exact media | 7,642 |
| Blocked: no public media ID | 1,407 |
| Prepared | 733 |
| Exact-episode ASR required | 21 |
| No media | 21 |
| Candidate ASR required | 11 |
| Ambiguous | 11 |
| Exact timed captions | 1 |

Only 330 package rows currently carry an `acquired` acquisition status in this snapshot. The large remaining inventory is evidence of search opportunity, not accepted identity-bound audio.

## 4. Accepted anchor vault

The current accepted anchor vault contains:

- **1,512 recordings**;
- **431 distinct member labels**;
- **119.255 hours** of retained audio;
- 4,536 exact 8-second held-out calibration windows in the associated vector/calibration layer.

The anchor manifest SHA-256 is:

`199ae5cf0a845d8fc1c8d611831139dbfa12e8b47b948f23ed332f8d25b7c297`

The profile census accounts for 1,507 in-universe anchor events; the five-row difference from the 1,512-row vault reflects roster/universe reconciliation rather than lost physical audio.

## 5. Canonical audio corpus

The physical canonical manifest at `C:\melange-data\member_clips\clips_manifest.jsonl` contains:

| Outlet class | Rows | Hours |
|---|---:|---:|
| NPR | 2,642 | 24.207 |
| HouseLive | 1,680 | 35.197 |
| Sunday programs | 1,578 | 17.528 |
| C-SPAN | 859 | 16.203 |
| CNN | 152 | 2.421 |
| **Total** | **6,911** | **95.558** |

All 6,911 manifest paths currently exist and all 6,911 rows carry SHA-256 values. The census counts **6,809 active parent clips** after excluding superseded rows. The manifest spans **425 member labels**.

The census derives 39,147 canonical 8-second equivalents from active material. That number is a logical accounting measure and should not be added to the 52,702 anchor-window equivalents because the admission rule uses the larger eligible source per member rather than summing possible overlap.

## 6. Exact-window lineage ledger

`canonical_exact_windows_v1.jsonl` contains:

- **24,524 exact windows**;
- **267 member labels**;
- **196,192 seconds / 54.498 hours**;
- all rows marked `ACCOUNTED`;
- all rows marked `non_house_floor`;
- exact 8-second geometry and parent/source lineage hashes.

These are logical windows into immutable accepted parent clips. Their `output_wav` is intentionally null, so the ledger does not create 24,524 redundant physical WAV files.

## 7. Current member-profile coverage

| Coverage category | Members |
|---|---:|
| Meets general profile floor via both ledgers | 330 |
| Meets floor through anchors only | 100 |
| Meets floor through canonical material only | 70 |
| Does not yet meet the general floor | 37 |
| **Total** | **537** |

The current profile census also accounts for:

- 52,702 anchor 8-second equivalents and 426,575.117 anchor seconds;
- 39,147 canonical 8-second equivalents and 339,462.626 canonical seconds;
- 24,365 active non-floor exact-window equivalents;
- 416 members satisfying the three-event/180-second strict identity prerequisite;
- 244 members satisfying the five-window non-floor descriptive floor.

The seconds and window-equivalent totals overlap across representations and must not be summed into a unique-audio total without a source-frame deduplication pass.

## 8. YouTube recovery lane

The raw YouTube recovery pool now contains:

| Stage | Rows / members | Meaning |
|---|---:|---|
| Downloaded full recordings | **96 / 61** | 11.165 hours; hash-bound local WAVs, initially title-match-only. |
| Timestamped ASR holdings | **32 / 22** | Localization evidence only; not speaker identity authority. |
| Hard-signal turn candidates | **18 / 16** | Literal-name screening produced 852 prospective exact windows. |
| Exact verification rows | **72 / 9** | 31 accepted exact windows and 41 refused windows. |
| Newly completed profiles | **9** | Raised general coverage from 491 to 500. |

The downloaded pool includes 59 Forbes Breaking News recordings, 13 C-SPAN recordings, five PBS NewsHour recordings, four Fox Business recordings, and smaller official/news-channel holdings. The title and channel fields remain routing metadata until in-band evidence and exact verification succeed.

## 9. Physical storage inventory

A literal recursive scan of `C:\melange-data` found **66,654 files totaling 120.539 GiB**. Of those, **17,282 are audio/video files totaling 58.852 GiB**:

| Extension | Files | GiB |
|---|---:|---:|
| WAV | 17,124 | 58.789 |
| MP4 | 93 | 0.063 |
| TS | 65 | less than 0.001 |

Largest relevant top-level holdings:

| Folder | Files | Audio files | GiB |
|---|---:|---:|---:|
| `sunday_audio` | 144 | 141 | 12.187 |
| `houselive` | 90 | 12 | 10.280 |
| `member_clips` | 6,257 | 6,249 | 8.844 |
| `npr_audio` | 678 | 677 | 6.740 |
| `source_audio` | 7,633 | 3,700 | 6.548 |
| `axe_audio` | 54 | 51 | 5.305 |
| `wj_audio` | 1,243 | 1,235 | 2.596 |
| `source_audio_abc_only_current` | 1,934 | 1,313 | 1.208 |
| `youtube_audio` | 104 | 96 | 1.198 |

The total includes raw recordings, anchors, canonical clips, candidates, verified mirrors, quarantined evidence, and workflow copies. It is a physical storage inventory, not a unique accepted-speech count. The separate `bicam_snapshot` folder accounts for 60.137 GiB of non-audio snapshot data.

Inside the repository, `data/speech` now contains 224 files totaling 0.873 GiB: 105 JSONL artifacts, 96 receipt JSON files, and three Markdown reports. Most of the size comes from versioned 57–58 MiB source-inventory snapshots. Those snapshots preserve provenance and state transitions but substantially duplicate logical package content across generations.

## 10. Remaining 37-member gap

Every remaining member currently needs the full five-window general floor. The recovery ledger has **413 local transcript packages, 739 turns, and 95,045 words for 28 of the 37 members**.

Residual package routing is concentrated in:

| Source | Packages |
|---|---:|
| CNN | 313 |
| MSNOW/MSNBC | 26 |
| NPR | 22 |
| Fox | 21 |
| C-SPAN | 14 |
| PBS | 11 |
| NBC Meet the Press | 3 |
| CSIS | 2 |
| ABC This Week | 1 |

The 413 packages currently break down as 376 needing probe, 29 blocked for no exact media, four blocked for no public media ID, and four prepared.

Seven residual members already have 13 downloaded YouTube recordings totaling 1.232 hours:

| Member | Videos | Minutes |
|---|---:|---:|
| LaMonica McIver | 3 | 18.3 |
| Morgan Luttrell | 3 | 21.2 |
| Derek Tran | 2 | 9.2 |
| Vince Fong | 2 | 10.1 |
| Jake Ellzey | 1 | 4.9 |
| Mary Miller | 1 | 5.2 |
| Sheri Biggs | 1 | 5.1 |

Nine residual members have no local transcript package in the source-media recovery ledger. Eight of them also have no current YouTube recovery holding: Aumua Amata Coleman Radewagen, Brian Jack, Darline Graham, Frank Lucas, James C. Moylan, Kimberlyn King-Hinds, Pablo Hernández Rivera, and Stacey E. Plaskett. Vince Fong is the ninth package-less member, but he does have two downloaded YouTube recordings.

The complete residual list is:

Abraham Hamadeh; Adam Gray; Alan Armstrong; Analilia Mejia; Anna Luna; Aumua Amata Coleman Radewagen; Brian Jack; Clay Fuller; Darline Graham; David Valadao; Derek Tran; Dwight Evans; Frank Lucas; Jake Ellzey; James C. Moylan; Jefferson Van Drew; John Carter; Johnny Olszewski; Julia Brownley; Kimberlyn King-Hinds; LaMonica McIver; Linda Sánchez; Maggie Goodlander; Mark Harris; Mary Miller; Mike Carey; Mike Kennedy; Mike Levin; Morgan Luttrell; Pablo Hernández Rivera; Pat Harrigan; Ryan Mackenzie; Scott Franklin; Sean Casten; Sheri Biggs; Stacey E. Plaskett; Vince Fong.

## 11. Highest-yield next work

The next recovery order supported by the inventory is:

1. re-evaluate the 14 already-downloaded residual YouTube recordings with the repaired transcript-start logic, prioritizing literal introductions and uninterrupted five-window runs;
2. probe the four prepared source packages and the highest-duration C-SPAN/PBS/NPR residual packages before broad CNN search;
3. use the 314 CNN packages as a localization index, deduplicating by physical episode before ASR;
4. perform official-uploader search for the nine members with no source-media package, especially delegates and newly seated members;
5. continue to refuse title-only attribution and preserve every failed row with an explicit reason.

The bottleneck is no longer a shortage of text or candidate media. It is converting existing holdings into exact, identity-bound, speech-pure audio without relaxing the evidence standard.

## Authoritative current artifacts

- `social_media.db`: full speech-row store.
- `source_media_inventory_cumulative_current_snapshot.jsonl`: current package-level source inventory.
- `speaker_anchor_vault_all_verified_v3.jsonl` and receipt: accepted anchor vault.
- `C:\melange-data\member_clips\clips_manifest.jsonl`: physical canonical audio manifest.
- `canonical_exact_windows_v1.jsonl`: exact-window lineage ledger.
- `congress_audio_profile_census_full_v1.jsonl` and receipt: current 537-member coverage census.
- `congress_audio_profile_recovery_gap_general_v1.jsonl` and receipt: current residual routing ledger.
- `C:\melange-data\youtube_audio\youtube_manifest.jsonl`: downloaded raw YouTube holdings.
- `local_youtube_holdings_asr_v1.jsonl`, `local_youtube_turn_candidates_v1.jsonl`, and `local_youtube_exact_window_verification_v1.jsonl`: current recovery pipeline ledgers.
