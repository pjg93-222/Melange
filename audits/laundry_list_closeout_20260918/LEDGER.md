# Laundry-list handoff (2026-07-16) -- reconciliation ledger

Written 2026-09-19 from worktree unfinished-work-handoff-a3bbad @776ce0d3a (== main).
Read-only pass: no source edited, no artifact regenerated, nothing committed.

Evidence grades
- [V]   verified directly by the coordinating session (file read, grep, git, or a run in the published page)
- [L-x] measured by lane x; scripts + raw outputs saved under this packet (laneA..laneE, F1..F3)
- [S]   scout census, spot-checked by the coordinating session

HEADLINE. The handoff's "NOTHING has been applied" is superseded. The lane landed the same night:
commit 391a4a8b5 (2026-07-16 22:02 -0500), merged e58a807da; record = AUDIT_COMPLETION_REPORT_2026-07-16.md. [V]

| #  | Handoff item | Status today | Receipt |
|----|--------------|--------------|---------|
| 1  | Stance bands / Champion crown | LANDED 07-16, SUPERSEDED by brain D-031 (e3e5ece7c, 2026-09-16), and PUBLISHED: overall Champion = 13 == honors_meta.overall_board.top13; Champion 0 in the three defend fields, Defender 0 in the 15 offence fields; dials HONORS_LADDER='g', OVERALL_LABEL='analytic'. CLOSED -- not reopened. | brain D-031 [V]; laneC q7_d031_labels.txt [L-C] |
| 2  | Network deselect | LANDED. On the published page a blank click gives sel=-1, panels reset, search cleared, camera == fit(), route=null; identical for the Targets button, a touch tap, after a Max route, and for the coalition (?coal=) view, which July called un-clearable. NOT implemented: re-clicking the selected node does not toggle it off. Logic-level only (browser pane hidden, requestAnimationFrame frozen): appearance and animation unverified. | browser/deselect_logic.json [V]; template lines ~527 / ~1104 [V] |
| 3  | Kennedy max route | LANDED as closedCascadeRoute(sel,6,2) with stance and system-skeptic gates. All-seed replay in the published page, 5 issues: the legacy budgetRecruit still returns ONE recruit set for 98.9% of seeds (July defect reproduced on today's data); the new route returns 121-195 distinct sets over 484-497 viable seeds; John Kennedy in 19-21% of routes (was ~99%); mean pairwise Jaccard 0.30-0.43. RESIDUAL: a hub core persists on every issue -- French Hill 64-89%, Tom Emmer 72-82%, Andy Barr 65-78% of all routes; the largest identical set covers 72-106 seeds. | browser/route_replay.json [V] |
| 4a | CU Tax Status dashboard column | FIXED. On every surface: dashboard issue index 17, per_topic_alloc 19 keys, workbook block col 153, frontier topics. | laneC q1_topic_keysets.txt [L-C]; DATA.issues probe [V] |
| 4b | Bill-universe fork (Tim Scott MBL rows) | PARTLY OPEN. The say-do gate no longer forks (reads the routing audit first). The desk still reads the workbook role sheets: 627 keys workbook-only, 258 archive-only. Tim Scott: +6.24 of 12.24 MBL sponsor weight reaches the stance matrix nowhere (58.0% of his published +10.76 cell), 3 cells. He is the ONLY member affected: 53 sponsor-less bills = 49 sponsor not in the roster + 4 defect (Anna Luna's two are covered by sentinel rows). Not a regression (absent from the 0624 archive too). The producer never reads the archive's bill-level Sponsor column, which is populated on 10,181 of 10,181 rows. | laneC q2*.txt [L-C]; F1 s1..s6 [L-F1] |
| 4c | Domain placements | S.869/118 and H.R.7733/117 now route to CDFI Fund (hard-coded overrides in bill_rules.py) -- RESOLVED. H.J.Res.59 and S.J.Res.18 (119th) now route to CFPB (bill_overrides.csv) -- RESOLVED. H.R.3009/117 still sits under MBL for 2 of its 4 rows -- UNMOVED (owner's label call). CDFI Fund now has evidence: 265 rows / 239 members, of which 244 rows are letters. | laneC q2_q6_bill_universe.txt [L-C] |
| 4d | Original-cosponsor double count | FIXED. 0 role twins; archive_leg.json rebuilt 3,395 of 3,395 cells with 0 mismatches. | [L-C] |
| 4e | bill_key() ignores bill type | LATENT and guarded. 0 live collisions in both scopes; Congress is part of every outcome-changing lookup; the legacy path cannot run. No action needed. | laneC q4_bill_key_call_sites.txt [L-C] |
| 4f | '+1' registry-direction parse | UNREACHABLE today. bill_directions.csv literals: '1' 107, '-1' 12, '0' 7, nothing else; no writer emits into that file; the manual and override files use a float parse. No action needed. | [L-C] |
| 4g | Media / press half (lost in the July crash) | DELIVERED now: FINDINGS sections A and F3. | laneA, F3 |
| 5  | Cross-reference layer | OPEN, and larger than July measured: FINDINGS section B. | laneB, F2 |
| 6  | sna_layout | Producer FIXED (kernel loader, deterministic order, atomic write). sna_compact.json still has no reader: 8 grep hits = 1 writer, 1 print, 6 prose. Attic-or-wire is still the owner's call. | laneD E7 [L-D] |
| 7  | Base branch | MOOT. claude/cfpb-sentiment-recorrection no longer exists; 35b8a09 and 391a4a8b5 are ancestors of main; main == HEAD. | [S] + [V] |
| s7 | Engine deep audit (9 pending auditors) | COMPLETED by the 07-16 lane (completion report sections 2-6, 8, 9). Residue measured today: FINDINGS section D. | [V]; laneD |
| s8 | In-flight workflows and results JSON | DEAD. They stopped at the account spend boundary (completion report line 7). The companion results JSON is absent from the live root; the old worktree's session directory (workflow scripts + journals) no longer exists. | [V] |
| s9 | Decision list | 1 closed by D-031; 2 landed; 3 landed (residual = hub core); 4 see 4a-4g; 5 open; 6 open; 7 moot. | -- |

Corrections to the handoff's own project-law digest
- "audit_full.py exit code is ALWAYS 0" is stale: it exits 1 on failure today (laneE).
- "Verification: kernel tests" cannot be run validly from a worktree: run_tests.py sub-suites resolve the data root from __file__, so 35 suites fail by construction (laneE).
- "chain not yet run" on brain D-031 and D-034 is stale: a full chain published both on 2026-09-18 (~02:36 local).