---
name: moneyball-congress-rollover-campaign
description: The executable, decision-gated campaign for surviving the 119th -> 120th Congress rollover (new Congress seats 2027-01-03). Load this when anyone asks "what happens when the new Congress starts", "how do we rebuild congestion.json", "where does the roster come from", "how do we add the freshmen / remove departed members", "the FEC money data is stale", "we need HS120 / new voteview rosters / new legislators.csv", or when an audit fails on roster counts (533), pinned industry totals, or workbook row drift after a member change. It owns ONLY this campaign — the congestion.json producer resurrection, roster-swap sequencing, freshman impact per layer, and the rollover validation bars. It does NOT cover general chain operation (moneyball-run-and-operate), the change-control rules themselves (moneyball-change-control), day-to-day debugging (moneyball-debugging-playbook), or dial reference (moneyball-config-and-flags).
---

# Congress rollover campaign (119th -> 120th)

This is the campaign plan for the project's hardest known live problem (designated by Paul, 2026-07-09): the entire Moneyball model is anchored to a 533-member roster of the 119th Congress, and on 2027-01-03 the 120th Congress seats with roughly 60–90 brand-new members ("freshmen") who have zero history in every data layer. The root roster artifact, `congestion.json`, has **no live producer** — its builders were retired to `fec/attic/` on 2026-07-02 (in-repo evidence: `AUDIT_FINDINGS_2026-07-02.md:134` "congestion.json genuinely has no live producer") — and its raw inputs are 2024-election-cycle FEC bulk files. This skill reconstructs the producer pipeline, sequences the swap, states the expected numbers at every gate, and defines measurable success. Nothing here is "run it and see": every phase has a pass bar and a branch for failure.

## When NOT to use this skill

- Running the normal weekly chain, collectors, or dashboards → **moneyball-run-and-operate**.
- The rules for what needs Paul's sign-off and how changes are verified → **moneyball-change-control** (this campaign routes through it; it does not replace it).
- A failing audit check unrelated to roster/member-count/money-total pins → **moneyball-debugging-playbook**.
- Adding or changing a dial → **moneyball-config-and-flags**.
- Prereg / one-look research discipline questions → **moneyball-research-methodology** (but read the "prereg fingerprint" fence below before touching any roster file).

## Quick reference

**Current state, all verified in-repo/live-tree as of 2026-07-09:**

| Fact | Value | Where verified |
|---|---|---|
| Roster size | 533 = 433 House + 100 Senate (2 House vacancies) | `congestion.json` (live root), `fec/audit/legacy_workbook_audit.py:26` |
| congestion.json shape | LIST of 533 dicts, 17 keys each (schema below) | live artifact + `fec/attic/full_congestion.py:50-64` |
| Canonical producer (retired) | `fec/attic/full_congestion.py` (attic'd @16f6413, 2026-07-02) | `AUDIT_ROADMAP.md:24,92` ("use full_congestion.py") |
| Pinned industry totals | CU $2,670,800 / Banks $7,795,150 / FinSvc $3,363,600 (±$2,000) | `fec/audit/legacy_workbook_audit.py:60` (check E3) |
| Members with no FEC money record | total==0: 63; receipts==0: 18 | live artifact; `AUDIT_ROADMAP.md:26` |
| FEC bulk inputs (2024 cycle) | `fec/ccl24.zip cm24.zip cn24.zip pas224.zip weball24.zip` (git-tracked); extracted `ccl.txt cm.txt cn.txt itpas2.txt weball24.txt` in live `fec/` (mtimes Jun 26) | `git ls-files fec/*.zip`; live `fec/` dir |
| Voteview rosters | `votes/HS117..119_members.csv` + `HSall_members.csv` (max congress = 119); live tree only (gitignored) | live `votes/` dir |
| Member-ID join hub | `fec/legislators.csv` (36 cols incl. bioguide_id, fec_ids, votesmart_id, icpsr_id, type) — unitedstates/congress-legislators "current" export | live `fec/legislators.csv` header |
| Workbook roster capacity | member rows 3..535 (exactly 533 rows) on Blended Model / Rank & Allocation; press weights live AT row 535 of the Normalized press sheet | `fec/audit/audit_full.py:252-258`, `fec/moneyball_core.py:63,72` |
| Electoral forecast input | `Ballotpedia_119th_CU_Influence_*.xlsx` — filename glob hardcodes "119th" | `fec/engine/build_electoral.py:21` |
| Hardcoded congress tuple `(119,118,117)` | 9 live scripts + kernel (list in Phase 4) | grep, see Provenance |
| Kernel tests / audit size | counts grow — trust the run's own tail (dated last-measured counts: see Provenance) | `fec/tests/run_tests.py`; `fec/audit/audit_full.py` |

**congestion.json row schema (all 17 keys; every consumer depends on this exact shape):**
`member` (display name, THE key everything joins on), `bioguide`, `chamber` ("House"/"Senate"), `cu`, `banks`, `finserv` (PAC dollars from tracked committees), `receipts` (total campaign receipts), `total` (cu+banks+finserv), `saturation`, `cu_pct/banks_pct/finserv_pct` (raw shares), `cu_adj/banks_adj/finserv_adj` (capacity-adjusted shares), `industry_adj`, `net_lean` (cu_adj − industry_adj; + = credit-union-leaning, − = bank-captured). Consumed keys across ~40 live scripts: `member`/`bioguide`/`chamber` everywhere; `cu`,`banks`,`finserv` (all flip/frontier/coalition engines, e.g. `fec/engine/flip_model.py:29`), `receipts` (median-imputation logic, `fec/engine/flip_model.py:26-28`), `net_lean` (`fec/surfaces/build_dashboard_bundle.py:133,235`, `fec/engine/lt_priming.py:71`), `total` + share keys (`fec/audit/legacy_workbook_audit.py:59-68`, `fec/engine/sna_layout.py:30`).

**Run the readiness gate check any time (read-only, stdlib-only, writes nothing):**
```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
python ".claude\skills\moneyball-congress-rollover-campaign\scripts\rollover_gate_check.py"
python ".claude\skills\moneyball-congress-rollover-campaign\scripts\rollover_gate_check.py" --online   # also probes voteview + fec.gov for 120th/2026 files
```

## Glossary (zero-context definitions)

- **Congress numbering**: the 119th Congress sits 2025-01-03 → 2027-01-03; the **120th** seats 2027-01-03, elected in the November 2026 midterms. Every House seat and ~1/3 of Senate seats turn over.
- **Rollover**: this project's word for migrating every roster-anchored artifact from the 119th to the 120th membership.
- **Freshman**: a member new to Congress — zero press history, zero cosponsorships, zero interview corpus, zero incumbent record in our layers.
- **bioguide**: the official Congressional Biographical Directory ID (e.g. `B001314`) — the cross-dataset join key.
- **FEC bulk files**: the Federal Election Commission's pipe-delimited campaign-finance dumps, published per 2-year cycle at fec.gov. The five we use: `cn` (candidate master), `cm` (committee master), `ccl` (candidate–committee linkage), `pas2` (itemized committee→candidate contributions; extracts as `itpas2.txt`), `weball` (all-candidates financial summary).
- **PAC**: Political Action Committee — an entity that donates to candidates, identified by committee IDs like `C00007880`. The congestion builder tracks 44 hand-pinned PAC IDs (23 bank + 10 finserv + 11 credit-union; `fec/attic/full_congestion.py:4-6`).
- **Voteview**: voteview.com, the academic roll-call database; `HS<congress>_members.csv` = House+Senate roster with party codes and NOMINATE ideology scores.
- **congestion.json**: this project's root roster+money artifact (the name means "how congested a member's funding is with industry money" — nothing to do with networks).
- **'—' (em-dash) cell**: the stance matrix's "no signal at all" value — deliberately distinct from Neutral. It carries its own calibrated constants (persuadability 0.45, seed gate 0.85) and is EXCLUDED from tier averaging (`fec/moneyball_core.py:430-434` PERS, `:486-490` SGATE, `:539-543` tier averaging; cites corrected 2026-09-30).
- **Zero-rank-delta**: the project's standard proof that a change didn't move member ranks: rerun the chain, diff `ranks_python.json`, expect 0 members moved.

---

## Phase 0 — What you can do TODAY (no gates, read-only)

1. **Run the gate-check script** (command above). Expected today: HS120 roster = PENDING (voteview publishes it after the 120th's first recorded votes, early Jan 2027); FEC 2026-cycle bulk files = likely AVAILABLE mid-cycle (the FEC publishes and refreshes `weball26.zip`/`pas226.zip` etc. DURING the 2025-26 cycle) — a mid-cycle pull enables the Phase 3 dry run now.
2. **Record the green baseline.** With no live jobs of Paul's running (check running python processes and fresh artifact mtimes first; see moneyball-run-and-operate):
```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
python "fec\tests\run_tests.py"    # expect: KERNEL TESTS — N passed, 0 FAILED (count grows — trust the run's own tail)
python "fec\audit\audit_full.py"         # expect: FULL-BODY AUDIT — N passed, 0 FAILED (count grows — trust the run's own tail)
```
3. **Copy the current `congestion.json` and `ranks_python.json` somewhere safe** (e.g. your scratch dir) — they are the regression references for Phases 3 and 6.
4. **Read the fences section** at the bottom before doing anything else.

## Phase 1 — The user-domain inventory (Paul's decisions; present, don't act)

These are Paul's alone. Present this checklist to him when rollover planning starts; none of the later phases can complete without them. (Domain boundaries: see moneyball-change-control.)

| # | Item | Why needed | Owner action |
|---|---|---|---|
| 1 | **Workbook roster rows** — Blended Model / Rank & Allocation / Normalized / Centrality / Congestion sheets, member rows 3..535 | The workbook IS the roster source of truth: the congestion builder reads member names from Blended Model col A and name→bioguide from the Centrality sheet (`fec/attic/full_congestion.py:32-34`) | Paul edits the workbook (his domain; Excel closed for any scripted write) |
| 2 | **Roster capacity decision** | Rows 3..535 hold exactly 533 members; a full 120th = 435+100 = 535 members does NOT fit. Press weights sit AT row 535 of the Normalized press sheet (`fec/moneyball_core.py:72`), and 20+ scripts hardcode `range(3,536)` (`fec/audit/audit_full.py:252-253` documents this as a standing guard). Growing past 533 = workbook restructure + coordinated code change | Paul decides layout; engineering follows with a change-controlled window update |
| 3 | **New Ballotpedia export** `Ballotpedia_120th_CU_Influence_*.xlsx` (Members sheet: Member/State/Chamber/Election_Average) | `build_electoral.py` needs next-election averages; the glob hardcodes 119th (`fec/engine/build_electoral.py:21`) | Paul produces/exports |
| 4 | **Quorum re-exports**: cosponsor network base `congress_cosponsor_network_*.xlsx` (bioguide-keyed Edges sheet; current base files are external exports, newest Jun 25), `congress_bills_archive_*.xlsx`, `Quorum Master.xlsx` (social), staffer exports | No in-repo fetcher exists for any of these (verified by grep — consumers only) | Paul re-exports from the licensed vendor |
| 5 | **Stance dispositions for departed members** | Stance/press classification is Paul's domain (session-ratified, 2026-07); departed members leave the matrix, freshmen enter as '—' | Paul reviews the post-swap matrix |
| 6 | **`fec/retiring_members.txt` reset** | Currently 69 names of 2026-cycle retirees (live file, validated 2026-07-03); after the rollover the retirees are GONE and the file must be re-seeded for the 2028 cycle | Paul (or engineer with Paul's list) |
| 7 | **Committee seats** — workbook 'Committee Data' sheet + Congestion sheet rebuild | Committee assignments reorganize every Congress; the Congestion sheet writer is a COM-era one-shot (`fec/attic/write_congestion_sheet.py` — dangerous, Excel closed, backup-first) | Paul gates; engineer executes only on his go |
| 8 | **Open prereg disposition** (see fence F8) | Refreshing `fec/legislators.csv` or `votes/HSall_members.csv` breaks the SHA-256 fingerprints pinned by the locked Vote Smart ES prereg (`fec/members/b5_es_votesmart_look.py:157`) | Paul decides: complete the look first, or accept a documented addendum |

## Phase 2 — Data acquisition (engineer-safe downloads; nothing runs against fec/ yet)

Do these only AFTER Phase 1 item 8 is resolved (fingerprint fence). Every download goes to a staging folder first (e.g. your scratchpad), then is placed with the old file renamed `<name>.PRE-120TH-<date>`, never deleted.

**2a. Voteview 120th roster → `votes\HS120_members.csv`**
Expected URL pattern (matches how the HS119 file is laid out; verify at voteview.com/data if 404): `https://voteview.com/static/data/out/members/HS120_members.csv`. Also refresh `HSall_members.csv` (same directory). Expected shape: same 22 columns as HS119 (`congress,chamber,icpsr,...,bioguide_id,...,party_code,...`); note HS119 has 554 rows (1 President row + mid-congress replacements; 450 House + 103 Senate rows — MORE rows than seats is normal). Gate: `bioguide_id` non-empty for ≥99% of member rows (voteview backfills freshman bioguides with a lag — if many are blank, wait a few weeks; the `party()` loader joins on bioguide, so blanks become party '?').

**2b. legislators.csv refresh → `fec\legislators.csv`**
Source: `https://unitedstates.github.io/congress-legislators/legislators-current.csv` (same project whose social-media registry `fec/tweet_collector.py:69` already downloads). Gate: header must still contain `last_name, first_name, nickname, full_name, type, state, bioguide_id, fec_ids, votesmart_id` (the congestion builder indexes these BY NAME, `fec/attic/full_congestion.py:12`; the Vote Smart collector needs votesmart_id). Expected: ~535-545 rows (sitting members only). If the header changed upstream → STOP; the builder resurrection must be adapted and the divergence noted in the promotion PR.

**2c. FEC 2026-cycle bulk files → staging, then `fec\`**
Expected URLs (FEC's documented cycle-suffix pattern; browse fec.gov/data/browse-data?tab=bulk-data if 404):
```
https://www.fec.gov/files/bulk-downloads/2026/ccl26.zip      -> ccl.txt        (linkage; NO live consumer — provenance only)
https://www.fec.gov/files/bulk-downloads/2026/cm26.zip       -> cm.txt         (committee master; attic diagnostics only)
https://www.fec.gov/files/bulk-downloads/2026/cn26.zip       -> cn.txt         (candidate master; attic diagnostics only)
https://www.fec.gov/files/bulk-downloads/2026/pas226.zip     -> itpas2.txt     (THE money input: committee->candidate contributions)
https://www.fec.gov/files/bulk-downloads/2026/weball26.zip   -> weball26.txt   (THE receipts input)
```
Do NOT overwrite the 24-cycle files — the pas2 zip's inner file is cycle-less and collides with the existing `fec/itpas2.txt`. Stage the 2026 extractions as `fec/itpas2_26.txt` / `fec/weball26.txt` and let the resurrected builder take input paths as parameters (Phase 3). Keep the 2024 `itpas2.txt` in place: `fec/engine/method_audit.py:67` and the Phase 3 regression proof still read it. Size sanity: the 2024 pas2 zip was 24.7 MB / 122 MB extracted; a complete-cycle 2026 file should be the same order of magnitude (a tiny file = you got a partial slice).
Field meanings the builder relies on (pipe-split index → FEC data-dictionary name): itpas2 `p[0]`=CMTE_ID, `p[5]`=TRANSACTION_TP (keep only `24K` direct + `24Z` in-kind), `p[14]`=TRANSACTION_AMT, `p[16]`=CAND_ID, `p[19]`=MEMO_CD (`X` = memo row, excluded); weball `p[0]`=CAND_ID, `p[5]`=TTL_RECEIPTS (`fec/attic/full_congestion.py:19-30`, `fec/attic/saturation.py:14`).

**2d. Social-handle registry refresh (defer execution to Phase 4)**
`tweet_collector.py init` seeds handles from a LOCAL cache `legislators_social_media.json` and only downloads it if absent (`fec/tweet_collector.py:67-70`). At rollover: rename the stale cache aside so init re-downloads — but running init is a collector action; schedule it in Phase 4 ops, not now.

## Phase 3 — The congestion producer (the hard core)

### Solution menu, ranked

**Option A (RECOMMENDED): resurrect `fec/attic/full_congestion.py` as a new live, parameterized producer.**
`AUDIT_ROADMAP.md:92` names it canonical ("`final_congestion.py` (use `full_congestion.py`)"), and it provably wrote the live artifact's exact 17-key schema. Its unique advantage: **it can be regression-proven against reality** — run the resurrected copy on the UNCHANGED 2024 inputs and it must reproduce the live `congestion.json` value-for-value before you ever point it at 2026 data. Option B can never get a proof that strong.
Derivation obligations (all three required before promotion):
1. **Schema-diff proof**: output keys per row == the 17 keys above, same types, same rounding (`round()` sites at `full_congestion.py:50-64`).
2. **Roster-join validation**: member count == workbook roster count; unresolved == 0 (the builder prints them); `bioguide` non-null for every row; chamber counts == the HS120-derived expectation; the three historically fragile name classes still resolve (compound surnames "Debbie Wasserman Schultz", late-seated specials "Matt Van Epps", accented "Pablo Hernández Rivera" — pinned by `fec/audit/legacy_workbook_audit.py:71` E6 and `fec/attic/final_table.py:60-62`).
3. **Money-total reconciliation**: per-bucket totals reconciled against an independent source before the new pins land (recipe below).

**Option B (fallback): write a fresh minimal producer emitting only the consumed keys.**
Choose only if the attic code cannot run (e.g. the workbook layout changed fundamentally). Obligations: everything in Option A **plus** you must first reproduce the live 2024 artifact from 2024 inputs with your new code (same regression bar — if your fresh code can't reproduce the known-good artifact, it is wrong, not "different"), and document every intentional divergence in the promotion PR.

**Explicitly rejected options**: hand-editing `congestion.json` forward (fence F1); adapting `final.py`/`final_table.py`/`makeup*.py` (they write SUPERSEDED schemas — a name-keyed dict or partial key sets — which would instantly crash ~40 consumers at `m['member']`); buying a third-party money API (an unauditable dependency; the FEC bulk files are free and citable).

### Resurrection procedure (Option A)

1. **Copy, never run in place**: `fec/attic/full_congestion.py` writes the LIVE `congestion.json` via a hardcoded absolute path (`full_congestion.py:65`) and reads inputs relative to cwd. Copy it to `fec/build_congestion.py` (a new file; goes through change control like any new producer; follow the new-code conventions in moneyball-build-and-env).
2. **Required edits to the copy** (keep the diff minimal and reviewable):
   - Route roots through `paths.py` (`from paths import ROOT`) like every live script.
   - Parameterize the data inputs: `CONG_PAS = os.environ.get('CONG_PAS', <fec>/itpas2.txt)`, `CONG_WEBALL = os.environ.get('CONG_WEBALL', <fec>/weball24.txt)`, and read `legislators.csv` from `fec/` by absolute path (no cwd dependence).
   - Parameterize the output: `CONG_OUT = os.environ.get('CONG_OUT', <ROOT>/congestion.json)` — and during ALL testing set `CONG_OUT` to a scratch path. The live path is only ever written by the promotion run.
   - Keep the 44 PAC committee-ID sets byte-identical (fence F7).
   - Keep the workbook row window `range(3,536)` unless Phase 1 item 2 changed the layout.
3. **Gate P3-A — regression proof on 2024 inputs** (check for Paul's live jobs first):
```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec"
$env:CONG_OUT="$env:TEMP\congestion_regress.json"; python "build_congestion.py"
```
   **Expected stdout**: `members: 533 | industry totals CU $2,670,800 Banks $7,795,150 FinSvc $3,363,600`. Then value-diff `%TEMP%\congestion_regress.json` against the live `congestion.json`: expected **0 differing rows** on all 17 keys.
   - **If totals match but a handful of member rows differ** → the workbook roster moved since the Jun-26 build (special elections). Verify each differing name against a real seat change; if confirmed, the regression is a PASS-with-note (the rebuild is MORE current than the artifact); list the names in the PR.
   - **If totals differ** → your itpas2/weball files are not the Jun-26 vintage (the FEC re-publishes cycle files with late amendments). Do NOT chase pennies against a newer 2024 file; re-run against the git-tracked zips' extractions (unzip `fec/pas224.zip`/`weball24.zip` to scratch and point `CONG_PAS`/`CONG_WEBALL` there) — those are frozen in git and must reproduce exactly.
   - **If any unresolved member prints** → name resolution changed; stop and debug (usually a legislators.csv header/vintage mismatch) before proceeding.
4. **Gate P3-B — 2026 dry run (safe TODAY, mid-cycle)**: same command with `CONG_PAS`/`CONG_WEBALL` pointed at the staged 2026 extractions, `CONG_OUT` still in scratch. Expected: `members: 533` (roster unchanged until Phase 4); all three bucket totals positive but well BELOW the 2024 numbers mid-cycle (money accumulates over a cycle — the exact fraction doesn't gate, positivity and non-degeneracy do); more zero-money members than 2024's 63 is normal mid-cycle. Record the numbers; they seed the Phase 6 re-pins.
5. **Gate P3-C — money-total reconciliation** (`fec/engine/method_audit.py:62-74` is the in-repo recipe): for ≥5 marquee PACs (ABA `C00004275`, JPMorgan `C00104299+C00128512`, Wells Fargo, BofA, Citi — IDs at `method_audit.py:63-65`), sum your 2026 itpas2 24K/24Z rows per committee and compare to OpenSecrets' "contributions to candidates" figures for the 2026 cycle. Expected: our PAC-only number ≤ OpenSecrets (theirs adds individual-earmarked money); trade associations (ABA) reconcile near 100%, corporate PACs lower — both documented as expected in the recipe. A tracked PAC at $0 in a complete cycle file = wrong committee ID or a dead PAC → flag to Paul (PAC-set changes are a separate, user-gated change; fence F7).

## Phase 4 — Roster swap sequencing (order is load-bearing)

Nothing in this phase runs until: Phase 1 items 1-2 done by Paul, Phase 2 files staged, Phase 3 gates A-C green, and HS120 exists. Steps, in order:

1. **Paul updates the workbook roster rows** (departed out, freshmen in, Centrality name→bioguide filled). Engineer verifies: typed names in Rank & Allocation rows 3..535 == intended roster size (`fec/audit/audit_full.py:257` logic).
2. **Place `votes/HS120_members.csv`** (+ refreshed HSall) and the refreshed `fec/legislators.csv` (old files renamed aside; fence F8 already cleared).
3. **Congress-constant code change** (one change-controlled commit; the complete verified list of `(119,118,117)`-tuple and 119th-literal sites):
   - `fec/moneyball_core.py:32` — kernel `party()` tuple → `(120,119,118)`
   - `fec/surfaces/build_dashboard_bundle.py:69` — bundle party loader; and `:263` `EXECP` (executive party for the going-public cue — set to the sitting president's party)
   - `fec/engine/build_electoral_plays.py:10` — plays party loader
   - `fec/members/behavior_panel.py:93` — voteview votes/ideology loop `(119,)` → `(120,)` (freshmen have no 119th rows)
   - `fec/members/agency_communion_llm.py:167`, `fec/members/big5_llm.py:162`, `fec/members/big5_traits.py:249`, `fec/members/fit_smoreg_rkh.py:33`, `fec/members/validate_big5.py:54` — party joins in the psych stack
   - `fec/members/fetch_interviews.py:140-142` — the LEADERSHIP floor-leadership singletons ("refresh alongside [the roster] at the next Congress" is the code's own comment at `:138-139`)
   - `fec/engine/build_electoral.py:21` + `fec/engine/build_electoral_history.py:28` — Ballotpedia glob `119th` → `120th`
   - `fec/stance/say_do_gap.py:12`, `fec/members/lep_criterion.py:41` — 119th mentions in prose only.
4. **Rebuild congestion for real**: promotion run of `fec/build_congestion.py` with 2026 inputs and `CONG_OUT` unset (live path), immediately followed by Phase 6 Bar-2 checks. Copy the displaced live `congestion.json` aside first (`backups/` convention).
5. **Reset `fec/retiring_members.txt`** (Paul's list; keep the header-comment format of the live file).
6. **Collector onboarding**: rename `legislators_social_media.json` aside → `python "fec\tweet_collector.py" init` (re-seeds handles; stdout `seeded <N>/533 members ...` — the `/533` literal is cosmetic, N is what matters) → `discover-bluesky` for freshmen. Interview/CREC collectors need no config: they attribute against `congestion.json` (drop-never-guess) and pick freshmen up automatically once step 4 lands.
7. **External re-exports land** (Paul: cosponsor network base, bills archive, Quorum social, staff exports, Ballotpedia 120th) → run their builders per moneyball-run-and-operate.
8. **Full chain + audit**, with Phase 5/6 expectations in hand:
```powershell
cd "C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
python "fec\run_pipeline.py"
```

## Phase 5 — Freshman impact survey: what to EXPECT per layer

Sixty-to-ninety members with zero history is not an error state; each layer has a designed behavior. Deviations from THIS table are bugs; matching it is success.

| Layer | Expected behavior with freshmen | Verified mechanism |
|---|---|---|
| Stance matrix | Every freshman cell = `'—'` (em-dash, "no signal"), NOT Neutral, NOT 0. Overall tier = 'Neutral' via the si==0 branch. Cut calibration unaffected (no-signal members are excluded from the cut pools) | `fec/stance/per_category_stance.py:86,106` (`hassig` guard); `fec/moneyball_core.py:163` |
| Persuadability / seeding | `'—'` carries PERS 0.45 (user-ratified Ally parity, `PERS_NONE`) and SGATE 0.85 — freshmen are lobbyable by design, at calibrated rates. The code has Ally = 0.40 (`fec/moneyball_core.py:430-431`), so parity does not currently hold — open ruling N6, Paul's; do not change either value in code (corrected 2026-09-30; verified against `fec/moneyball_core.py:430-434,486-490`) | `fec/moneyball_core.py:430-434` (PERS), `:486-490` (SGATE) |
| Receptivity / psych | No text & no behavior → fully NEUTRAL multipliers + `lowconf` (never an invented personality). z-scores are cohort-relative, so RETURNING members' multipliers drift slightly as freshmen gain coverage — expected, not a regression | `fec/members/receptivity_layer.py:35-38,105-155` |
| Say-do gate | Fails OPEN: no bills/votes → no caps. Freshmen can't reach Champion without signal anyway. V-path evidence (`vote_category_lean.json`) goes progressively stale: its upstream roll-call CSV is an external, severed input (2026-07-08 network/vote audit, finding V-1) | `fec/moneyball_core.py:221-224` |
| Cosponsor network | Freshmen enter as isolated nodes (`adj[m]={}` contract) until the new network export lands; ~41 members were already network-isolated pre-rollover | `fec/moneyball_core.py:116`; `AUDIT_ROADMAP.md:29` |
| Money (congestion) | Freshmen HAVE FEC records (they just ran campaigns): expect real `receipts`, usually small `cu/banks/finserv`; the `total==0` cohort (63 today) shifts composition | Phase 3 build |
| Electoral history / LEP | Empty for freshmen — already the documented steady state ("119th freshmen have no LEP history", `fec/members/lep_criterion.py:41`); the desk simply shows no history rows | `fec/engine/build_electoral_history.py:75` (skips empty) |
| Member desk narratives | Freshmen lack Fable briefs; the weekly refresh generates only MISSING briefs, capped `NARR_MAX=15`/week (~$0.10/member) → 60-90 freshmen ≈ 4-6 weeks to coverage, or raise the cap for one run with Paul's OK. Narratives are the ONLY permitted Fable spend (hard cost rule); every other LLM step is Haiku 4.5 | `fec/weekly_refresh.py:94-108` |
| Collectors | Attribution is roster-driven (drop-never-guess): freshman speeches/interviews attach automatically post-swap; refresh the LEADERSHIP singletons (Phase 4.3) or references to new floor leaders drop silently | `fec/members/fetch_interviews.py:128-142` |
| Preregs / research routes | Frozen-roster preregs (the b5 rounds; DATA-GATED MEM_N≥250 etc.) do NOT transfer: their fingerprints pin the OLD roster files. Successor preregs need fresh locks on the new roster — see moneyball-research-methodology. Never "helpfully" re-run a look on the new roster | `fec/members/b5_es_votesmart_look.py:157,165-169` |

## Phase 6 — Validation and promotion protocol (routed through moneyball-change-control)

Success is measured, never eyeballed. Two distinct bars, because two distinct changes are being made:

**Bar 1 — producer-swap proof (roster UNCHANGED).** Before any 120th data enters the tree: with `build_congestion.py` promoted but still fed 2024 inputs, the full chain must be a no-op. Measure: rerun `python "fec\run_pipeline.py"`; diff `ranks_python.json` pre/post → **0/533 members moved**; `audit_full.py` all green with UNCHANGED pins. This proves the resurrection introduced zero drift. (Standard verification ladder: run_tests → run_pipeline → zero rank delta → audit clean, `fec/tests/run_tests.py:6`.)

**Bar 2 — roster-swap acceptance (the real rollover).** Absolute ranks necessarily change (freshmen insert into the ordering), so the measurable bar is on RETURNING members:
- **Score invariance where inputs are unchanged**: for every returning member whose raw inputs did not change in the swap window, `score` in `ranks_python.json` is identical pre/post. (Press normalization is pos/neg-max over the roster — freshmen contribute no press rows on day 1, so the maxima are untouched; a returning member whose score moved has a REAL input diff you must be able to name.)
- **Order preservation**: filter both rank lists to the intersection roster; the relative order of returning members is unchanged except for pairs with named input diffs. Report format: "N returning members; K order inversions; each inversion attributed to <input>".
- **Roster-diff report** (attached to the promotion PR): departed list + count, freshman list + count, counts cross-checked three ways (workbook typed rows == congestion.json length == HS120-derived seat count).
- **Audit re-pins land in the SAME commit as the swap**, each a one-line change to the new measured value, never loosened to a range: `fec/audit/legacy_workbook_audit.py:26` (A4 member count), `:57` (E2 Congestion-sheet rows), `:60` (E3 industry totals — from the Phase 3C reconciled build), `:71` (E6 edge-case names — pick three current members covering the same fragile classes), `:73` (F1), `fec/audit/audit_full.py:189` (receptivity coverage), `:241-248` (reactivity/dispositions coverage floors — these WILL drop with freshmen; if below floor, that is a data-gated fact to surface to Paul, not a constant to quietly lower), `:257` (row window, if capacity changed), `fec/tests/run_tests.py:41` (member count).
- **Full audit green after re-pins**; kernel tests green; one weekly_refresh cycle completes with no new failures.
- **User sign-off gates**: Paul signs (a) the roster-diff report, (b) the stance-matrix review (his domain), (c) the audit re-pin diff, (d) the Congestion-sheet workbook write. No promotion without all four.

**If Bar 2's score invariance fails broadly** (many returning members moved with no nameable input): STOP, re-pin nothing, restore the displaced `congestion.json`, and bisect — rerun the chain with OLD congestion + NEW roster files, then NEW congestion + OLD roster files, to isolate which artifact injected the drift. moneyball-debugging-playbook owns the triage patterns.

## Fenced wrong paths (each has drawn blood or provably would)

- **F1 — NEVER hand-edit or hand-extend `congestion.json`** (or any generated JSON). Incident: the hand-added 18th stance category was silently clobbered by its producer (documented at `fec/stance/per_category_stance.py:21-24`). The fix for a stale artifact is always its producer.
- **F2 — NEVER run attic scripts in place.** Import == execution; `fec/attic/full_congestion.py:65`, `final.py:48`, `final_table.py:71`, `makeup.py:50`, `makeup2.py:49` ALL write the live `congestion.json` at import — and final/makeup write SUPERSEDED schemas (name-keyed dict / partial keys) that would crash ~40 consumers on the next chain step. Copy out, parameterize the output, then run.
- **F3 — NEVER touch the workbook roster rows yourself.** They are Paul's (roster/stance = his domain; session-ratified, 2026-07). Also: Excel must be CLOSED for any scripted workbook write, and the one-shot `apply_*`/COM tools are dangerous by default (see moneyball-run-and-operate).
- **F4 — NEVER map freshman no-signal cells to 0 or "Neutral".** The ontology forbids it: `'—'` is a distinct value with user-ratified constants (PERS 0.45 = Ally parity — "silence never outranks a declared Ally", `fec/moneyball_core.py:430`; the code has Ally = 0.40 (`fec/moneyball_core.py:430-431`), so parity does not currently hold — open ruling N6, Paul's; do not change either value in code; corrected 2026-09-30, verified against `fec/moneyball_core.py:430-434`). A producer that emits 0/Neutral for freshmen silently corrupts persuadability, seeding, and tier math.
- **F5 — NEVER "fix" the audit by loosening pins.** A4=533, the E3 dollar pins, coverage floors: every re-pin is a measured, one-line, same-commit-as-cause change with Paul's sign-off (Phase 6). An audit constant that no longer matches reality is a *finding*, not an obstacle.
- **F6 — Git worktrees isolate DATA — which makes them the WRONG place to run data-dependent work.** `fec/paths.py:7-8` defaults ROOT to the parent of the imported paths.py, so a script run from a worktree targets its EMPTY data plane: reads die on missing inputs and writes land as throwaway worktree artifacts. Run data-dependent work from the live tree, or set `MONEYBALL_ROOT` to it — and then writes DO hit live. Check for Paul's live jobs before ANY run; port 8802 for previews (8801 is Paul's own server). (Corrected 2026-07-19; the previous version asserted the opposite. Verified against `fec/paths.py:7-8`.)
- **F7 — NEVER change the 44 PAC committee-ID sets inside the rollover change.** Same-commit set edits confound the money reconciliation (cycle drift becomes indistinguishable from definition drift). New/dead PACs go in a separate, Paul-gated follow-up with its own E3 re-pin.
- **F8 — NEVER overwrite `fec/legislators.csv` or `votes/HSall_members.csv` while a LOCKED prereg pins their hashes.** The Vote Smart ES look fingerprints both (`fec/members/b5_es_votesmart_look.py:157`); drift makes the look refuse (safely — no look consumed) and strands a user-gated route. Resolve Phase 1 item 8 first.
- **F9 — NEVER re-run frozen-roster looks or "refresh" preregs onto the new roster.** Retired-without-a-look routes (DATA-GATED / DIAGNOSTIC-GATED) keep their pinned successor conditions; new-roster work needs NEW preregs (moneyball-research-methodology).
- **F10 — Do not delete the 2024-cycle zips or extracted txt files.** `fec/*.zip` are git-tracked provenance; the extracted 24-cycle files are the regression-proof inputs (Gate P3-A) and `method_audit.py`'s data. Disk is cheap; proofs are not.

## Provenance and maintenance

Written 2026-07-09 against the live tree and worktree @88a7048 (branch claude/nifty-cray-f6d053). Volatile facts and one-line re-verification commands (run from repo root `"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"`; all read-only):

- Roster size / schema / totals / zero-money counts:
  `python -c "import json,collections;d=json.load(open('congestion.json'));print(len(d),dict(collections.Counter(m['chamber'] for m in d)),sorted(d[0]),sum(m['cu'] for m in d),sum(m['banks'] for m in d),sum(m['finserv'] for m in d),sum(1 for m in d if m['total']==0),sum(1 for m in d if m['receipts']==0))"`
- congestion.json still has no live producer: `git grep -n "congestion.json" -- fec | grep -v attic | grep -i "dump\|,'w'"` (expect empty)
- Canonical-producer designation: `git grep -n "full_congestion" -- AUDIT_ROADMAP.md`
- Pinned audit constants: `git grep -n "533\|2_670_800\|7_795_150" -- fec/audit/legacy_workbook_audit.py fec/audit/audit_full.py fec/tests/run_tests.py`
- Congress-tuple hardcode list: `git grep -n "(119,118,117)\|(119, 118, 117)\|(119,)" -- fec` and `git grep -n "119th" -- fec`
- Ballotpedia glob: `git grep -n "Ballotpedia_119th" -- fec`
- FEC zips tracked + inner names: `git ls-files fec/*.zip` then `python -c "import zipfile;print({z:zipfile.ZipFile('fec/'+z).namelist() for z in ['ccl24.zip','cm24.zip','cn24.zip','pas224.zip','weball24.zip']})"`
- Voteview vintage: `python -c "import csv;print(max(int(r['congress']) for r in csv.DictReader(open('votes/HSall_members.csv',encoding='utf-8',errors='replace'))))"` (expect 119 until the 120th publishes)
- Workbook row-window guard + press weights row: `git grep -c "range(3,536)" -- fec` (20+ sites) and `git grep -n "cell(535" -- fec/moneyball_core.py fec/audit/audit_full.py`
- '—' ontology constants: `git grep -n "PERS_NONE" -- fec/moneyball_core.py fec/tests/run_tests.py`
- Prereg fingerprints on roster files: `git grep -n "leg_sha\|hs_sha" -- fec/members/b5_es_votesmart_look.py`
- Retiring-list size: `python -c "print(sum(1 for l in open('fec/retiring_members.txt',encoding='utf-8') if l.strip() and not l.startswith('#')))"` (69 as of 2026-07-09)
- Weekly narrative cap: `git grep -n "NARR_MAX" -- fec/weekly_refresh.py`
- Gate script self-test: `python ".claude\skills\moneyball-congress-rollover-campaign\scripts\rollover_gate_check.py"` (prints a checklist, exits 0, writes nothing)

UNVERIFIED items a maintainer should confirm before relying on them: the exact voteview per-congress URL (`HS120_members.csv`) and the fec.gov 2026 bulk URL pattern (both marked "expected pattern" above; the gate script's `--online` mode probes them and reports); the producer of the base `congress_cosponsor_network_*.xlsx` exports (external — only consumers exist in-repo; ask Paul which vendor/export produces them before the 120th network refresh).

Last measured (dated — counts drift, so trust each run's own tail): `fec/tests/run_tests.py` 247 passed / 2 FAILED in LIVE on 2026-09-20 (standing reds `test_bill_collision_guards`, `test_make_staffer_network_html`); `fec/audit/audit_full.py` 559 passed / 9 FAILED in LIVE on 2026-09-19 (after that day's membership refresh) (both recorded in the Project Brain STATE); the chain has 80 `CHAIN` entries, 79 run by default (`fec/run_pipeline.py:45-302`), counted 2026-09-30 at main 25eefa3fc.
