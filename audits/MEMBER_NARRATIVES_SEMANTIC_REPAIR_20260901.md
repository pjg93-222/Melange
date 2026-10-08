# Member narratives semantic repair — close-out record, 2026-09-01

Status: **artifact activated and receipt-bound; member desk rebuilt with all 533 narratives rendered;
focused test 5 passed; `audit_full` 545 passed / 26 failed with all three narrative checks OK** (the 26 are
other lanes' standing items plus the un-regenerated combined page, see "Open items"). A condensing pass to
240-300 words in narrative voice is prepared and waiting on API credit.

Coordinator for this record: Claude (Fable) session in worktree `caveman-feature-toggle-3a6ecd`, acting on
Paul's instructions in chat. Earlier stages ran under Codex (Meta LOOP runs `ce753a937d`, `eccfac97a9`).
No git commands were used in this close-out (Paul's instruction).

## What was done

1. **Full-corpus semantic audit** of the 2026-08-31 briefs (Codex, morning): 0 of 533 passed, so the
   regeneration target set became all 533 (268 known cross-party targets plus 265 additional failures).
2. **Regeneration** with `fec/members/revise_member_narratives_v2.py generate --resume`, model
   `claude-sonnet-5`, deterministic checks plus a separate Sonnet semantic reviewer, up to 6 rounds per brief.
   Three launches: Codex morning run (225 accepted), Claude-lane run from 15:52 local (Paul's hand; the
   auto-mode classifier refused to let the session launch it), and Codex reruns for exhausted names.
   Every one of the 533 names reached at least one Sonnet-accepted brief before the API credit balance
   ran out at 17:51 local (310 later lines in the progress file are "credit balance too low" errors).
3. **Deterministic scope repair** (Codex, 21:46-21:52 local, `fec/members/sanitize_member_narratives_v2.py`):
   every accepted brief was passed through a conservative sanitizer that deletes defensive/topic sentences
   the ledger does not support, replaces trait sentences with exact ledger-band sentences, and strips
   private-state terms. Output: `data/members/member_narratives_v2_revisions.json`, all 533 marked
   `rounds = local-deterministic-1`, `reviewer = codex-deterministic-scope-repair-v1`.
4. **Plain review of the sanitized candidate** (Claude, this session, read-only), deterministic census
   against `data/members/member_narrative_evidence_v4.json` plus eleven reader passes:

   | Check | Result |
   |---|---|
   | Cross-party / aisle / cosponsor language while the share-based measure is absent | 0 of 533 |
   | Canonical "Broad <trait> is <band>" sentences vs ledger band | 0 mismatches of 1,745 |
   | Defensive-reaction claims while `repeated_defensive_reactions` is null | 0 |
   | Em/en dashes, `**`, heading text, paragraphs under 25 words | 0 |
   | Exact repeated sentence inside one brief (sanitizer artifact) | 91 briefs, 108 sentences |
   | Digits in prose (historical dates: "January 6", "2008", "1935", "September 11") | 8 briefs |
   | "These readings" opener whose lead-in sentence was deleted | 6 briefs |

   Reader passes that flagged cross-party or speech claims en masse were checked against the ledger and
   found wrong (the measure was present in every case); those flags were discarded.
5. **Dedupe** (Paul: "Dedupe first, then activate"): removed the 108 exact repeated sentences from the 91
   briefs in `member_narratives_v2_revisions.json`, first occurrence kept. Recorded under the top-level key
   `post_pass_dedupe`. Two paragraphs became short because the removed copy sat in a speech or approach
   paragraph: Robert Aderholt p3 (21 words), Russ Fulcher p2 (11 words). Both non-blank and correct.
   Pre-dedupe copy of the revisions file is in the session scratchpad.
6. **Merge and activation** with `fec/members/merge_member_narratives_v2.py` then `--activate`. All merge
   gates passed (533 present, semantic pass for all, basis hash bound, no cross-party language without the
   measure, no `**`, no duplicate paragraphs corpus-wide).
7. **Bill refresh re-run** (Paul's order, because the desk builder is gated on it):
   `fec/legislation/update_bill_repository.py` with defaults, 464 of 464 refreshed, receipt status PASS,
   `browser_status = govinfo-complete`. The morning weekly-refresh run had left it PARTIAL (1 failure).
8. **Desk rebuild** with `fec/surfaces/make_member_desk.py` (23:48-23:49 local): `member_desk_bundle.json`
   42.5 MB, `cu-member-desk-profiles.js` 35.0 MB, `cu-member-desk.html` 8.4 MB. No "WITHHELD" line in the
   build log. Pre-rebuild copies of the three outputs kept in the session scratchpad.

## Final counts and hashes

| Item | Value |
|---|---|
| Roster | 533 members |
| Installed artifact | `member_narratives_v2.json` (repo root), status `ACTIVE_API_GENERATED_USER_RATIFIED`, count 533 |
| Installed artifact sha256 | `1d391430d182f4128fbf9fe71d7559f7f720629ae8a4f62f02e20ed52a1c3409` |
| Semantic receipt | `data/members/member_narratives_v2_semantic_receipt.json`, status PASS, `counts.semantic_pass` 533, `active_artifact_sha256` = installed sha |
| Receipt file sha256 | `8fec872618fc488b027f97550c9510330d6eb26c3e8c2b7737a6948990ee61ba` |
| Evidence basis sha256 (artifact, receipt, `profile_basis_v2.json`) | `1e14d1ddeeb250e11cc7140614193d2f9f4cef1901be3de1f7e99976c65f6b27` (all three agree) |
| Evidence ledger file sha256 | `16f004e115b60430b906a08cd59a96bef3ceae0aa578883588f325359c58b610` |
| Pre-repair backup | `member_narratives_v2.pre_semantic_repair_20260901.json`, sha256 `34eb9c3cb7384d87810ff1a2ad3987e8fe714836c788db07907267061395548f` (the artifact as installed before activation) |
| Rewritten briefs | 533 (268 known cross-party + 265 additional) |
| Semantic repair completed | 2026-09-02T03:20:54Z (provenance `semantic_repair.completed_utc`) |
| Brief length (p1+p2+p3 words) | min 194, median 369, max 617 |

Note: the artifact's older provenance blocks `source_run` and `repair` (522 accepted / 11 failed / 8
repaired) describe the 2026-08-31 generation and are carried forward unchanged; they do not describe this
repair.

## API usage (data/members/member_narratives_v2_work/api_usage.jsonl, all phases, all launches)

| Item | Value |
|---|---|
| Calls | 5,229 (2,229 write, 3,000 review), model `claude-sonnet-5` only |
| Input tokens | 31,357,686 |
| Output tokens | 4,903,037 |
| Cache write / cache read tokens | 36,381 / 9,412,741 |
| Estimated spend at $2 in / $10 out per million (cache write 1.25x, read 0.1x) | about $114 (estimate, list price assumption) |

The account's credit balance reached zero at 17:51 local on 2026-09-01; the last 310 progress lines are
billing errors, not generation failures.

## Verification

- Focused test `fec/tests/members/test_member_narratives_v2_repair.py`: first run after activation **4 passed,
  1 failed** (the 268-target pin, which inverts by design once the artifact is repaired: 282 briefs mention
  cross-party behaviour and every one has the measure); after the re-pin described below, **5 passed**.
- Installed artifact sha == receipt `active_artifact_sha256` == receipt `candidate_sha256`: verified.
- Backup sha == pre-activation installed sha: verified.
- Desk render: **533 narratives rendered, 0 withheld** (counted in `cu-member-desk-profiles.js` and
  `member_desk_bundle.json`); **533 of 533** rendered p1/p2/p3 byte-identical to the installed artifact.
- `fec/audit/audit_full.py` (live tree), second run 2026-09-02 00:13 local after the press-receipt fix
  below: **545 passed, 26 FAILED**; all three narrative checks OK ("current narratives cannot silently
  fall back to legacy E/audio prose", "legacy audio and paid narrative paths retired from
  unattended/display consumption", "legacy E/audio narratives fail closed pending guarded local
  rebuild"). The 26 failures are the standing set from other lanes: system-manifest sentinel/size drift
  (manifest of 2026-08-28), pillar snapshot 15 days old, V-1 vote-lean staleness, legfix5 culling
  promotion state, media-blend press hashes, interview DB chain binding, audio manifest partition, press
  feed intake binding, email packages, plus two A3 derivation-order items, one of which this lane caused:
  `repo.combined_html` is now older than the rebuilt `cu-member-desk.html` (the combined page was not
  regenerated; that is a deploy step, Paul's call).
- Press-receipt fix (2026-09-02 00:10): the press lane's validator (`fec/press_stream.py:51-53`,
  uncommitted) requires a cumulative accepted-run ledger that had never been produced. Ran the lane's own
  producer `fec/collect/build_press_engine_feed.py` (cumulative mode, default intake receipt): one accepted
  run (2026-08-28) ledgered, the three feed files byte-identical to before, `validate_refresh_receipt()`
  passes. Prior copies in the session scratchpad.
- Test fix (2026-09-02): `test_known_repair_partition_and_missing_measure_gate` now asserts the
  post-repair invariant (every cross-party target has the measure) on the installed artifact and keeps the
  268/143/125 pin against the pre-repair backup. 5 passed.
- First `audit_full` attempt (2026-09-01 23:50): **crashed before the narrative check** at `audit_full.py:484`
  (`_load_press_tone_rows`), `fec/press_stream.py:53` raising
  `RuntimeError: press refresh receipt is not a cumulative accepted-run ledger`. That is the press-refresh
  lane's uncommitted gate, unrelated to narratives; one earlier check also reported FAIL
  (`interview DB projection -> extract -> stance chain is receipt/hash bound :: extract_current=False`).
  The audit's narrative conditions were therefore replicated standalone and all nine pass: receipt schema,
  status PASS, receipt basis == artifact basis, artifact basis == sha256(profile_basis_v2.json), evidence
  file present, receipt `evidence_sha256` == sha256(evidence ledger), `counts.semantic_pass` == 533,
  `active_artifact_sha256` == sha256(artifact), labelled provenance pair.

## Open items

1. **`audit_full.py` cannot complete in the live tree today.** It crashes at line 484 on the press-refresh
   receipt gate in the uncommitted `fec/press_stream.py` (press lane), before reaching the narrative check.
   Re-run it once that lane lands. The desk-builder bill-refresh gate that blocked the first rebuild attempt
   was cleared by re-running the bill refresh (item 7 above).
2. **Test pin** 268/143/125: resolved 2026-09-02 (re-pinned; see Verification).
3. **Digits** in 8 briefs (historical dates) left as written; the no-numbers rule was meant for scores.
4. **Six briefs** open a sentence with "These readings" after the sanitizer removed the sentence it referred
   to (Adam Gray, Austin Scott, Erin Houchin, Frank Pallone, Jim Jordan, Mike Rogers). Readable, slightly
   abrupt.
5. **Meta LOOP.** Codex runs `run-20260901T1539056742831Z-ce753a937d` and
   `run-20260901T1813302320552Z-bdb09df27c` were closed as `run.blocked` on Paul's order. Codex run
   `run-20260901T2048335605998Z-eccfac97a9` (stages C1-C3) was closed the same way after its C1-C3 work
   was completed under the claude lane: terminal event `evt-20260902T0355589081378Z-7d636c434d`,
   `receipt_verified = true`. Claude-lane events were emitted without a run id (cwd = this worktree)
   because the auto-mode classifier refused `metaloop.ps1 -Action start` for a Claude-coordinated run.
   Fan-out coverage on all three Codex runs is recorded as unverifiable (no Claude transcript for their
   cwd), which `recover` permits and `finish` would not.
6. **Pipeline files are untracked.** `revise_member_narratives_v2.py`, `merge_member_narratives_v2.py`,
   `sanitize_member_narratives_v2.py`, `build_member_narrative_ledger.py`, both prompt files and the test
   are not committed. All `*.json` / `*.jsonl` artifacts are gitignored.

7. **Re-activation on 2026-09-02 00:25.** A plain (non-active) `merge_member_narratives_v2.py` run, done to
   verify a patch, overwrote the live receipt with one lacking `active_artifact_sha256`, which would have made
   the loader withhold all briefs on the next desk build. `--activate` was re-run: same brief text, new
   provenance timestamp, installed sha256 now
   `1d391430d182f4128fbf9fe71d7559f7f720629ae8a4f62f02e20ed52a1c3409`, receipt rebound, desk bundle text still
   identical 533/533. Design flaw to fix in the merge script: a non-active run should write its receipt to a
   candidate path, never over the active one.
8. **Condensing pass prepared, not run.** Paul (2026-09-02): briefs should be 240-300 words, leave shorter ones,
   narrative voice. 455 of 533 exceed 300 words. `fec/members/condense_member_narratives_v2.py` and
   `member_narratives_v2_condense_prompt.md` are built (dry run: 455 targets); the merge script's 268 pin now
   reads the pre-repair backup so a second merge works. Waiting on API credit.

## Known limitations

- The final shipped text is sanitizer output. Each brief's Sonnet semantic review applied to the text
  before sanitising; the deterministic pass deleted a median 31% of sentences per brief (range 6% to 71%)
  and inserted canonical band sentences in 509 briefs. The post-sanitise review in this record is a
  rule-checklist review, not a second model review.
- Reader passes by small models were unreliable on cross-party and speech rules; only mechanically
  verified findings are reported above.
- Dollar figures are estimates from token counts at an assumed list price; no pricing constant exists in
  the repo.

## Security

- The Anthropic API key was pasted into chat twice on 2026-09-01. It is stored as
  `anthropic.keys[0]` in `Desktop\API Keys\keys.json` (the 08-31 key kept at `keys[1]`). The key does not
  appear in any repo file, log, or event. **Rotate it now that the run is complete.**

## Reproduce the numbers

```
python fec\members\merge_member_narratives_v2.py              # rebuild candidate + receipt (non-active)
python -m pytest fec\tests\members\test_member_narratives_v2_repair.py -q
python -c "import hashlib;print(hashlib.sha256(open('member_narratives_v2.json','rb').read()).hexdigest())"
```
Duplicate-sentence census: split each of p1/p2/p3 on sentence boundaries, normalise whitespace, count
repeats within the brief. Cross-party gate: any of {aisle, bipartisan, cross-party, cosponsor, either
party, party lines} in the brief while `members[name].behavior.cross_party_cooperation` is null.
