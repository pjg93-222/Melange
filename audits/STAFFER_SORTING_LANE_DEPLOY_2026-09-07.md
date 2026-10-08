# Staffer sorting lane — DEPLOY PASS, 2026-09-07

Deploy executed in the LIVE tree (`C:\Users\pgoff\OneDrive\Desktop\Melange Systems`) under the
owner's ship authorisation (D-022 item 6, "You can ship once prepared"). No git action was taken:
the commit is a separate step and remains the owner's. Every file overwritten was copied first to
`backups\staffer_sorting_20260907\<relative path>.<HHMMSS>.pre` and each backup was verified
byte-identical to its source before the write.

Sole-writer precondition was checked before starting: no `build_*`, `verify_*`, `run_pipeline` or
`make_combined` python process was running. Only the 8841 staffer-live sidecar (PID 8168) and two
static `http.server` instances were up; none was stopped or restarted.

---

## 1. What shipped

### The three generations (all verified independently for this record, not taken on report)

| generation | receipt | sha256 | bytes | verifier |
|---|---|---|---|---|
| `hill_personnel_spine_20260907_v7_primary` | `hill_personnel_spine_receipt.json` | `915C367ECA8487AFF897D8807C42C3180DDF57070BF7C36A4F861333CF3810EF` | 51,984 | `status PASS`, `failures []` |
| `staffer_social_network_20260907_v6_primary` | `staffer_social_network_receipt.json` | `A6FBB2ED356335522090CB7CAC8B33E1F0EEB905588EC36B14CC59E02885DD16` | 71,175 | `status PASS`; `person_nodes 144,690`, `components 14,502` |
| `tiered_corroboration_sidecar_20260907_v3_primary` | `tiered_corroboration_receipt.json` | `BE4B7B8DB143BF0F8718B0AE7EA4CDE1EDBA70E07A02972E80CAFEF6A3D53C5A` | 20,192 | `status PASS`, `failures []`; `LINKED 17,831` |

The three matching `*_verification` receipts all read `status PASS` with empty failure arrays.

### The pin that was still on the old sidecar

`fec\surfaces\build_staffer_groups_section.py:254`
`SIDECAR_GENERATION`: `tiered_corroboration_sidecar_20260902_v2_primary` → `..._20260907_v3_primary`.

Its own contract suite passed **313 / 0** after the change, including the real-generation build.

**The "tiers are unchanged from v2" claim was tested rather than assumed.** The organisations part
was rebuilt against the v2 sidecar into a scratchpad and diffed against the shipped v3 build: the
body (everything except `meta`) is **canonically identical**, and both measure the same 3,939,678
bytes. Exactly three meta keys differ — `built_at`, `inputs` (the sidecar files' sha256 bindings)
and `sidecar_generation`. **There are no count changes of any kind.**

### Artifacts written to `data\engine\` (all four landed together, all inside the 5,000,000-byte pin)

| artifact | bytes | headline counts |
|---|---|---|
| `staffer_network_section.json` | 4,989,264 | members 533, roster 533; members with any staff 515, with shared staff 514; zero-overlap pairs rejected 10,471,278 |
| `staffer_offices_section.json` | 4,132,633 | offices 721, people listed 19,161, office-people total 129,997, `offices_unnamed` 0, HON-ledger resolved 8 |
| `staffer_organisations_section.json` | 3,939,678 | organisations 6,817, listed in full 3,574, singleton registrants 3,243, lobbyist rows 15,699; lobbyists total 25,340, none with no registrant on file; contract 11,021 / in-house 14,319 |
| `staffer_clients_section.json` | 3,892,167 | client organisations 41,203, contract filers 11,021, filer-client ties 132,738, dropped 0; name rows 55,447 |

All four carry `meta.generation = staffer_social_network_20260907_v6_primary`; the organisations
artifact additionally carries `meta.sidecar_generation = tiered_corroboration_sidecar_20260907_v3_primary`.

### Pages

| file | before | after | delta |
|---|---|---|---|
| `staffer-network.html` | 5,010,928 | 12,110,165 | +7,099,237 |
| `Moneyball.html` | 81,000,148 | 88,099,504 | +7,099,356 |
| `Moneyball_Email.html` | 75,988,893 | 75,988,893 | 0 — byte-identical (sha unchanged; the email variant excludes the staffer surface by design) |

`Moneyball.html` verification: `id=app-staffer` ×1; the v6 generation string ×9; the **v5 string ×0**
(fully repointed); `launch.js` ×0; sidecar v3 string ×4; spine v7 string ×2; the `_01` heading
"Melange — Staffer groups" ×1; GDATA/ODATA/CDATA islands all present; `#stf-main` skip target ×1;
and **no** orphaned `stf-desk` / `stf-indlink` anchors.

---

## 2. Rulings implemented

Citation discipline: each ruling below is quoted to the effect the code actually enforces, with a
`path:line` citation found in this tree. **D-018 is recorded as uncited** — no citation for it exists
in `fec\`, in `audits\staffer_network\*.py`, or in this lane's worktree, and its content is
deliberately not inferred from its neighbours.

- **D-018** — *no citation found in this tree.* Not implemented or verified by this pass; if it
  carries an obligation, it is unrecorded here rather than silently assumed satisfied.
- **D-019 — zero-overlap rejection.** No person-person edge without concurrent service; sequence is
  trajectory, never a social tie. `audits\staffer_network\build_staffer_social_network.py:1327`,
  `audits\staffer_network\verify_staffer_social_network.py:1427`. This deploy carries it as
  10,471,278 zero-overlap pairs rejected in the shipped section.
- **D-020 — a name is an identity only within an office.** Two or more distinct people sharing a
  name across offices may not be merged into one id; the day-level guard enforces it.
  `audits\staffer_network\build_hill_personnel_spine.py:356` and `:1913`,
  `audits\staffer_network\build_tiered_corroboration_sidecar.py:2972`,
  `audits\staffer_network\verify_hill_personnel_spine.py:1188`.
- **D-021 — no employment claim.** Employment tenure is not established for anyone here; canonical
  and operator flags stay `False` and the promotion counter stays 0.
  `fec\staffer_network\lda_employment.py:71`, `fec\staffer_network\lda_status_labels.py:28`,
  `audits\staffer_network\build_tiered_corroboration_sidecar.py:4005`. Gated by
  `fec\tests\surfaces\test_staffer_groups_section.py:32`.
- **D-022 — persons-only network; containers out to Groups.** The node universe *is* the person
  universe; organisations, offices and policy areas left the people network for the Groups surface.
  `audits\staffer_network\build_staffer_social_network.py:29`,
  `fec\surfaces\build_staffer_groups_section.py:8`. Items observed in code and honoured by this
  deploy: **item 1** current-day offices only, every current person named and everyone earlier
  counted as `earlier_count` (`build_staffer_groups_section.py:52`); **item 2** groups indexed away
  from the people (`fec\tests\surfaces\test_staffer_network_explorer.py:178`,
  `fec\tests\surfaces\test_staffer_source_catalog.py:50`); **item 3** the LDA status vocabulary in
  the owner's own words, verbatim (`fec\staffer_network\lda_status_labels.py:3`,
  `fec\surfaces\build_staffer_groups_section.py:358`); **item 6** ship authorisation, which is the
  basis for this pass.
- **D-023 — client ties are total.** A contract filer is tied to *every* client organisation on
  filings that name them. `fec\surfaces\build_staffer_groups_section.py:1734`. Shipped whole:
  41,203 client organisations and 132,738 ties, **0 dropped**, which is why the client data is a
  third normalized artifact rather than cards (as cards it measured 21,012,744 bytes).

---

## 3. Chain wiring

`fec\run_pipeline.py`, minimal diff, two hunks:

1. `('build_staffer_groups_section.py',['--part','both','--max-bytes','5000000'])` inserted
   immediately before the page builder and after the section producer. `--part both` writes all
   three Groups artifacts (`BOTH_PARTS = ('offices','organisations','clients')`), so no separate
   `--part clients` run is needed. The producer's all-or-nothing cap rule means a part that refuses
   the cap leaves the whole set alone.
2. `build_staffer_groups_section.py` added to `OPTIONAL_INPUTS` with four paths — the v6 generation
   directory, its verification receipt, the v3 sidecar directory, and the **off-repo** LDA
   source-native corpus under `%LOCALAPPDATA%\Melange\staffer_network\normalized\lda-source-native\generation-20260830T231200Z`.
   Without this a tree lacking the machine-local corpus would hard-fail the chain instead of
   clean-skipping. All four resolve on this box.

Chain now has 70 steps and the three staffer steps run in the right order. Neither
`test_combined_staffer_section.py` nor `test_staffer_surface_import_modes.py` pins the step list, so
**no test edits were required**; both were run anyway and pass (46/0 and 10/0), as does
`test_make_staffer_network_html.py` (218/0), `test_pipeline_producer_scope.py` and
`test_run_pipeline_tolerance.py`.

---

## 4. Page render check

`staffer-network.html` rendered in headless Chrome 152 at 1280×900 (CDP over Node's built-in
WebSocket; no packages installed). PNG: `scratchpad\deploy\staffer-network-final.png`, 83,487 bytes.

- document scroll height **1032**, visible text **1,653 characters**
- **0 console errors** (Runtime.consoleAPICalled/exceptionThrown and Log.entryAdded all empty, with
  the domains enabled *before* navigation so load-time errors could not be missed)
- data islands live in the page: SDATA generation = v6, GDATA 721 offices, ODATA 6,817
  organisations, CDATA 41,203 clients / 132,738 ties
- footer line: `721 offices · 6,817 organisations · 41,203 client organisations · 34,860 people listed`
- provenance flag renders `EXPLORATORY · REVIEW REQUIRED`

Spot-checks, all against the page's own data:

| check | result |
|---|---|
| office card | `COMMITTEE ON APPROPRIATIONS — 1,000 people · 202 current` |
| employer card | `CHAMBER OF COMMERCE OF THE U.S.A. — 158 people · in-house` |
| client card | `LOUISIANA CREDIT UNION LEAGUE — client · 4 lobbyists represent it` |
| search hit | `COMMITTEE ON APPROPRIATIONS` → "16 offices, 1 organisations and 4 client organisations match" |
| search miss | `zzzqqxx-no-such-thing-9713` → "0 offices, 0 organisations and 0 client organisations match" |

---

## 5. Audit and kernel tails

### `fec\audit\audit_full.py` — **573 passed, 13 FAILED**

`[STAFF]` block, verbatim:

```
[STAFF] Staffer network section
  OK   staffer_section_present
FAIL  staffer_section_inputs_current :: house_member_quarters missing (C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\staffer_social_network_20260907_v6_primary\audits/staffer_network/house_personnel_ledger_20260903_v5_primary/house_member_quarters.ndjson.gz); house_personnel_ledger_receipt missing (C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\staffer_social_network_20260907_v6_primary\a
  OK   staffer_surface_embeds_section
```

Overall tail:

```
  manifest agreement: 329 checks, 8 failed, 6 skipped, 9 notices
  OK   system manifest section emitted checks
FULL-BODY AUDIT — 573 passed, 13 FAILED
  FAILURES: ['every member holding verified audio evidence publishes an audio layer (no silent blindness)', 'the two audio layers stay on separately labelled scales (no false equivalence)', 'published profile prose never denies audio the member holds', 'email delivery packages are current, hash-bound, and within the attachment budget', 'staffer_section_inputs_current', 'A2b repo.data_legislation sentinels unchanged', 'A2b repo.data_lobbying sentinels unchanged', 'A2b repo.data_members sentinels unchanged', 'A2b repo.data_money sentinels unchanged', 'A2b repo.data_engine sentinels unchanged', 'A2b repo.outputs sentinels unchanged', 'A2b repo.fec_code sentinels unchanged', 'A2b repo.git sentinels unchanged']
```

**None of the 13 was caused by this deploy.** Diagnosis of the one in this lane:

`staffer_section_inputs_current` — `fec\audit\audit_full.py` re-hashes bound inputs with
`os.path.join(B, generation_root, rec['path'])`, which assumes every entry in `meta.inputs` is
*generation-relative*. The two HON-ledger inputs live in a **different** generation directory, so the
producer records them repo-relative; the join then produces the impossible doubled path visible in
the message. Running that exact join against the **pre-deploy v5 artifact** (kept at
`backups\staffer_sorting_20260907\data\engine\staffer_network_section.json.190725.pre`) yields the
**same two missing roles**, so the check fails identically before and after this pass. It is
nonetheless a real defect introduced by today's earlier HON-ledger binding work (owner ruling
2026-09-07 item 2), and it needs a ruling — see §7.

The 8 `A2b ... sentinels unchanged` rows are the known per-chain-run sentinel churn against a
2026-09-06 manifest. One names this lane's artifact (`staffer_network_section.json size:
manifest=4,400,802 / disk=4,989,264`) and is the expected consequence of rebuilding it. The audio,
profile-prose and email-package failures are other-lane and pre-existing; `Moneyball_Email.html` is
byte-identical to its backup, so nothing in this pass touched that path.

### `fec\tests\run_tests.py` — **189 passed, 2 FAILED**

```
FAIL  test_primacy_tier suite clean  :: FAILED (failures=1)
FAIL  audit_stale_imports suite clean  :: stale imports: 0 passed, 2 failed
KERNEL TESTS — 189 passed, 2 FAILED
```

`test_primacy_tier` is the standing board-ordering pin — known and expected.

`audit_stale_imports` is **a real finding and is NOT expected**, so it is written up rather than
waved through:

```
STALE bare-import    fec\tests\staffer_network\test_lda_employment.py:37  [lda_employment]  import lda_employment
STALE bare-import    fec\tests\surfaces\test_staffer_groups_index.py:39  [staffer_groups_index]  import staffer_groups_index
```

Both lines are the *deliberate* fallback arm of a `try: from fec.<pkg> import X / except ImportError:
import X` dual-mode bootstrap — legitimate code. `fec\audit\audit_stale_imports.py:87-92` provides
the escape hatch for exactly this case and its own comment names it ("a script-execution branch that
inserts its own directory before a bare sibling import"): the line must carry `# stale-ok: <reason>`.
These two files instead carry `# noqa: F401`, which is a flake8 pragma for unused imports and means
nothing to this audit. The established wording is in
`fec\audit\audit_postrefresh_downstream_drift.py:38` — `# stale-ok: guarded script-execution
fallback after explicit dir insert`.

Neither file was touched by this pass (mtimes 18:35:55 and 17:06:41, both before this session began
at ~19:02), and neither ever carried the pragma — both pre-existing backups already show
`# noqa: F401`. So this is an authoring omission from earlier lane work today, not a regression.
**The one-comment-per-line fix was deliberately NOT applied** — it is not required for this deploy
and the apply gate is the owner's.

---

## 6. Files changed, and their backups

| file | change | backup |
|---|---|---|
| `fec\surfaces\build_staffer_groups_section.py` | sidecar pin v2 → v3 (1 line) | `...\build_staffer_groups_section.py.190214.pre` |
| `fec\surfaces\make_combined.py` | staffer cross-surface link anchor taught both templates | `...\make_combined.py.192632.pre` |
| `fec\run_pipeline.py` | groups producer step + `OPTIONAL_INPUTS` entry + page step names its surface | `...\run_pipeline.py.193214.pre` |

Artifacts/pages overwritten, each backed up first:
`data\engine\staffer_network_section.json.190725.pre`, `staffer-network.html.192050.pre`,
`Moneyball.html.192050.pre`, `Moneyball_Email.html.192050.pre`. The three Groups artifacts had never
existed on disk, so they are new files with no prior version to preserve.

### The one change beyond the brief, and why it was unavoidable

`make_combined.py` was hard-bound to the `_00` template's markup and **failed outright** on the `_01`
Groups page:

```
AssertionError: navigation shell: expected exactly 1 occurrence of the staffer cross-surface links anchor, found 0.
```

`_00` emits three cross-surface links (`stf-netlink`, `stf-desk`, `stf-indlink`); `_01` emits only
"Main dashboard", because the merged shell already carries the other two. Until this was fixed the
Groups surface could not reach `Moneyball.html` at all, so the assigned deploy could not complete.

The fix keeps the guard strict rather than relaxing it, which the original comment explicitly warns
against: two **exact** anchors, each still required to match exactly once, the longer run tried
first, and an abort naming both counts if neither matches. Longest-first ordering is load-bearing —
the `_01` anchor is a prefix of the `_00` run, so the opposite order would cut a `_00` page short and
leave two dangling links. This was negative-controlled before rebuilding: the `_00` template still
selects the `_00` anchor and its post-cut residue is `['stf-livelink']` only (which must stay); `_01`
selects `_01` with the same residue; unfamiliar markup selects nothing and trips the assert. The
failed first run wrote nothing — `Moneyball.html` still matched its backup sha afterwards.

---

## 7. What the owner must do next

1. **Restart the scheduled task `MelangeStafferLiveSidecar`** so the 8841 sidecar reloads v7/v6/v3.
   It is still serving the previous generations. No process was stopped or restarted by this pass,
   by instruction.
2. **The web publish step remains the owner's** and was not performed.
3. **Commit.** No git action was taken; all of the above is uncommitted in the LIVE tree, which is
   single-disk and outside both backup systems.
4. **Rule on `staffer_section_inputs_current`** (§5). Either `audit_full.py` should resolve an input
   whose recorded path is already repo-relative against the repo root rather than the generation
   root, or the producer should record HON-ledger inputs generation-relatively. Until one of them
   changes, this gate cannot pass and the lane's own artifact re-hash is effectively unguarded for
   those two files. Worth noting: a third input, `hill_person_spine_display_names`, is recorded as an
   *absolute* path and passes only because `os.path.join` discards the prefix when its later
   argument is absolute — it works by accident, and the same fix should cover it.
5. **Rule on `audit_stale_imports`** (§5). The fix is one comment appended to each of two lines.
6. **Rule on `DEFAULT_TEMPLATE`.** `fec\surfaces\make_staffer_network_html.py:77` still names
   `make_staffer_network_html_00.tpl`, so a bare `python fec/surfaces/make_staffer_network_html.py`
   rebuilds the **old network surface** — demonstrated in this pass: `template=..._00.tpl sdata=full`,
   5,026,769 bytes. The chain step now names `--template make_staffer_network_html_01.tpl --sdata
   provenance` so a chain run cannot silently revert the shipped page, and a bare run still works
   unchanged for other lanes. Switching the module default is a decision with reach beyond this lane
   (it would also want `--sdata` to follow the template) and was left alone.
7. **Note the staleness guard.** `fec\surfaces\make_combined.py:171` watches
   `make_staffer_network_html_00.tpl` for staleness while `_01` is what ships, so an edit to `_01`
   would not mark `Moneyball.html` stale. Left unchanged; pairs naturally with item 6.

---

## 8. Explicitly NOT shipped

- **Decay** — still pending a ruling. No decay term is applied anywhere in the shipped artifacts.
- **`container_size_normalisation`** — still pending a ruling. Not applied.
- **The 8841 sidecar restart** — pending, item 1 above. Until it happens the live sidecar and the
  shipped page disagree about which generation they are showing.
- **The web publish** — the owner's step.
- **The commit** — not taken.
- **The two `audit_stale_imports` pragmas** and the `staffer_section_inputs_current` path fix —
  identified and diagnosed, deliberately not applied.
- **Audit coverage for the Groups artifacts** — the `[STAFF]` audit block gates the network section
  and the page embedding, but nothing gates `staffer_offices_section.json`,
  `staffer_organisations_section.json` or `staffer_clients_section.json`. They can now go stale or
  vanish without any gate noticing. Recommended as a follow-up; not built here.
