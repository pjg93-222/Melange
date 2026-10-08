# Identity-Collision Findings — repo-wide sweep, 2026-08-18

**Status:** FINDINGS ONLY. Nothing here is fixed. Every remediation is Paul-gated; several touch stance,
press, and rank-feeding artifacts, which are his domain.
**Trigger:** Paul, 2026-08-18 — "Also check for collisions", after the holistic lane found the production
CU cosponsor graph crediting Sen. Robert Menendez's (`M000639`, departed 2024, absent from the 533)
sponsorships to his son Rep. Robert Menendez (`M001226`).
**Method:** a five-surface adversarial sweep (identity-resolver core · stance/press/social · legislation and
external producers · data artifacts · roster and rollover), each finding then put to a refutation-biased
verifier. 41 findings, 10 put to refuters, 9 surviving, 9 judged capable of moving ranks or engine outputs.
**Then independently re-verified by this session before anything was written down** — because three
earlier claims in this arc were wrong until measured. What follows separates what I measured myself from
what I am relaying.

---

## 1. The shared identity Resolver is not fail-closed — VERIFIED BY EXECUTION

`fec/members/member_identity.py`. Its docstring calls it *"Fail-closed member identity resolution shared by
pipeline joins."* I executed the shipped class against the live 533-row `congestion.json`. Three distinct
fail-open paths:

**(a) A bare surname returns a guess instead of refusing.** The first-initial narrowing compares the
query's *first token's* initial — but on a bare surname there is only one token, so it compares the
surname's own initial against candidates' first names:

| query | returns | should be |
|---|---|---|
| `Johnson` | **Julie Johnson** | refusal (5 Johnsons) |
| `Lee` | **Laurel Lee** | refusal (4 Lees) |
| `Jackson` | **Jonathan Jackson** | refusal (2) |
| `Joyce` | **John Joyce** | refusal (2) |
| `Meeks` | **Mariannette Miller-Meeks** | refusal |
| `Moran` / `Smith` / `Scott` | None ✓ | (refuse only because no twin's first name starts with M/S) |

The refusals are accidental: the guard holds only when no colliding member's first name happens to start
with the same letter as the surname.

**(b) A unique surname matches with no first-name check, absorbing non-roster people.**

`John Smith` → **Jason Smith** · `Jessica Johnson` → **Julie Johnson** · `Robert Kelly` → **Robin Kelly** ·
`Michael Barr` → **Andy Barr** · `Travis Hill` → **French Hill** · `Jane Waters` → **Maxine Waters**

`fec/stance/extract_cu_hearings.py` names the "Gov. Michael Barr testifying vs Rep. Andy Barr on the panel"
case in its own docstring as the risk the Resolver mitigates. It does not mitigate it.

**(c) `"Last, First"` input silently returns a *different member*.** The raw comma form is tried before
reordering, so its last token is the *first* name while the index is keyed on surnames. **23 of 533
members** misresolve to somebody else:

`Masto, Catherine Cortez` → **Alexandria Ocasio-Cortez** · `Clyburn, James` → **John James** ·
`Reed, Jack` → **Brian Jack** · `Goldman, Craig` → **Angie Craig** · `Delaney, April McClain` →
**Lisa McClain** · `Bergman, Jack` → **Brian Jack** · `Baird, James` / `Comer, James` → **John James**

**Why it was never caught:** the only kernel assertion (`fec/tests/run_tests.py:153-157`) uses a three-name
toy roster in which none of the three modes is reachable. The test passes and proves nothing.

## 2. Hearing speaker attribution — VERIFIED, and larger than the sweep reported

`fec/collect/fetch_hearings_seq.py` resolves speaker labels with a private Senate-first chamber loop rather
than the shared Resolver, and calls it with no chamber. Measured across the shipped `hearings_seq.db`
(7,174 packages, **679,221 attributed turns**):

| package chamber | speaker chamber | turns |
|---|---|---|
| House (`hhrg`) | House | 411,434 |
| House (`hhrg`) | **Senate** | **46,190** |
| Senate (`shrg`) | House | **19,722** |
| Senate (`shrg`) | Senate | 195,655 |

**65,912 cross-chamber turns, 9.7% of all attributed speech.** The signature is unambiguous — in every
colliding surname group the senator takes everything and the House members get exactly zero:

| Senate | turns | House twins | turns |
|---|---|---|---|
| Jerry Moran | 4,571 | Nathaniel Moran | **0** |
| Tina Smith | 9,109 | Adam / Adrian / Christopher / Jason Smith | **0 each** |
| Mike Lee | 7,090 | Laurel / Summer / Susie Lee | **0 each** |

A visible instance sits in the first sampled row: Senate hearing `CHRG-118shrg56749` attributes turns to
**Kevin Mullin** (House, CA-15) where the speaker is plainly Sen. Markwayne Mullin — and Markwayne Mullin
is **absent from the 533**, so his speech has nowhere to land but the House member. That is the Menendez
class again: a non-roster member colliding with a sitting one.

Sibling file `fec/collect/fetch_congressional_record.py:110-121` carries an explicit comment that this bug
was fixed there ("never restore the legacy Senate-first guess"). The fix was never propagated to
`fetch_hearings_seq.py`, and only partly to `fetch_hearings_antag.py`.

## 3. `electoral_history.json` carries live identity swaps — VERIFIED, and rank-adjacent

`data/money/electoral_history.json`, produced by `fec/engine/build_electoral_history.py`, resolves
candidate rows by name with no bioguide.

- **Adelita Grijalva** (won an AZ special in 2025, succeeding her late father Raul) carries general-election
  results for **2016, 2018, 2020, 2022 and 2024** and primaries 2016–2022. Those are **Raul Grijalva's**
  elections. Raul appears in neither the roster nor the artifact — his record was absorbed by his daughter.
- **Mary Miller** (IL-15) carries `state: "OH"`. Ohio is **Max Miller's**. **Max Miller has no entry at
  all** — his record was absorbed into hers.

This matters more than the other two because the artifact is read by `fec/members/behavior_panel.py`
(behavioral basis) and `fec/surfaces/make_member_desk.py`, so a wrong electoral history is not display-only.
Blast radius on ranks is **not** measured here and should not be assumed either way — measuring it is a
follow-on, and any correction is Paul-gated.

Note for the fix, whenever it is ruled: `congestion.json` does **not** populate a usable `state` field
(reads `?` for every member checked), so the state-based disambiguation the builder relies on cannot work
from that source.

## 4. NOT REPRODUCED — recorded so it does not travel

The press/social lens reported a live wrong record in `data/stance/press_engagement.json`:
`{'author':'Katie Britt','named':'Craig Goldman'}`, said to be minted from a headline containing **Goldman
Sachs**. I searched the shipped artifact: **0 records naming any Goldman, 0 records pairing Britt with
Goldman.** The claim does not reproduce against the current file. The *structural* finding behind it —
that `fec/network/press_engagement_layer.py:36` builds its ambiguous-surname set from the ~385 press-corpus
authors rather than the 533-member roster, so roster-colliding surnames are treated as unambiguous — was
not disproved and is worth a look. But the cited instance is withdrawn.

## 5. What is clean (checked, so the census has a denominator)

Verified sound and not findings: `congestion.json` display names are **unique across all 533** (533 names,
533 bioguides, 0 missing), so `moneyball_core`'s `name2bio`/`bio2name` are bijective and not themselves a
collision source; `social_media.db` carries 502 Twitter handles with **zero duplicates**, so the
handle→member map in `social_interaction_layer.py` is safe; `fec/network/build_holistic_base.py` is
bioguide-native throughout. `fec/network/process_quorum.py`'s `matchname()` requires first *and* last
agreement even when the surname is roster-unique and refuses otherwise — it is the strongest resolver in
the repo and the right model for the others. `fec/members/cspan_identity.py` and
`fec/legislation/collect_official_rollcall_events.py` are also genuinely fail-closed.

## 6. Suggested order of work — all Paul-gated, none started

1. **Fix the Resolver** (`member_identity.py`) — remove the first-initial narrowing, require first+last
   agreement even on a unique surname, and try the reordered `"First Last"` form before the raw comma form.
   `process_quorum.matchname()` is the working model. Then **replace the toy-roster kernel test** with one
   built on the real 533 — the current test is why this survived.
2. **Propagate the congressional-record chamber fix** to `fetch_hearings_seq.py` and finish it in
   `fetch_hearings_antag.py`. Re-derive the affected hearing signals afterwards.
3. **Re-derive `electoral_history.json`** with bioguide-keyed joins, and measure whether ranks move.
4. **Arm `fec/tools/identity_collision_census.py` as a gate** once the CU scraper defect is fixed — today
   it fails by design, and encoding a known-failure exception into a gate is a ratification, not a tool
   decision (change-control law 7).
5. **Before the 120th rollover:** every one of these defects gets worse when members depart and freshmen
   arrive sharing surnames. The across-boundary case — a departed member colliding with a sitting one — is
   invisible to any within-roster check, which is precisely why it survived here.
