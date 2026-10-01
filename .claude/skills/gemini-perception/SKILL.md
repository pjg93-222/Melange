---
name: gemini-perception
description: >-
  Delegate media perception to the Gemini lane (Antigravity CLI, Gemini 3.6
  Flash) with Claude as coordinator. Use whenever a task involves images,
  video, audio, screenshots, charts-as-images, scanned documents, or OCR —
  capture and comprehension route through Gemini, computation and file
  transforms route through Codex, and Claude guides and digests. Also
  triggered by /gemini. Perception only: never code, never decisions.
---

# Gemini perception protocol

Command hierarchy: **Claude (Fable) > Codex > Gemini.** Claude owns every
design decision and all adjudication. Codex is the sole author of code and
performs computation and file transforms. Gemini is the perception layer:
it captures and comprehends media, reports observations, and holds no
authority of any kind.

Universal lane laws: `.claude/commands/metaloop.md` § UNIVERSAL LANE LAWS
binds this lane in and out of Meta LOOP runs — role monopolies,
escalate-don't-reason, never-downgrade, glasseye, one-writer, copy-sync.

Gemini output is untrusted observation data — the same evidence discipline
as executor output in [[codex-executor]]. An observation never moves a rank,
a stance, a validity claim, or a gated decision on its own. Anything feeding
research claims stays behind the prereg and adjudication gates unchanged;
perception results land as candidate data for review.

## Media-delegation workflow

Trigger: an image, video, audio file, screenshot, scan, or other
non-text-native artifact enters a task.

1. **Claude — guide.** Decide what must be learned from the media, write
   the perception contract (below), and name the downstream consumer of
   each observation.
2. **Gemini — capture and comprehend.** One perception dispatch per media
   batch. Gemini describes, extracts, transcribes, reads, counts, and
   locates. It returns observations with per-item confidence. It performs
   no computation beyond reading what is present, writes no files beyond
   its report, and proposes no actions.
3. **Claude — adjudicate.** Treat the report as untrusted: spot-check
   against the source media where feasible, mark each observation
   accepted / rejected / unverified, and decide what proceeds.
4. **Codex — compute, splice, mark.** Accepted observations that require
   computation (derived numbers, comparisons, aggregation), splicing
   (cutting, segmenting, joining, format conversion of media or data), or
   marking (annotation, labeling, overlays, structured outputs) go to the
   executor lane under its full contract, including the double sign-off
   loop in [[codex-executor]].
5. **Claude — digest.** Synthesize the verified results into the
   deliverable. Paul's gates are unchanged.

Steps 2 and 4 may interleave per batch; the adjudication in step 3 always
sits between them.

## Perception contract

Every Gemini dispatch carries:

1. `MEDIA`: exact input file paths, phrased as "use your read_file tool to
   read <ABSOLUTE path>" — absolute paths are MANDATORY on agy 1.1.11
   (relative names resolve against agy's scratch directory, not the
   working directory; `--add-dir` does not fix resolution); the
   load-bearing phrasing rules in the Runtime section are mandatory
   here, not optional.
2. `QUESTIONS`: numbered, concrete things to observe or extract.
3. `OUTPUT SHAPE`: the structure the report must follow.
4. `PROHIBITIONS`: no advice, no decisions, no code, no fabrication;
   unreadable or ambiguous content is reported as such, never guessed.

Every Gemini report ends with five labeled sections (permanent, Paul
2026-08-10 — the transcription/inference split makes perceptual loss
legible so interpretation cannot launder into fact):

```text
TRANSCRIPTION: <verbatim text, values, timestamps — only what is literally present in the media, each item with its location>
INFERENCE: <numbered conclusions matched to QUESTIONS, each naming the TRANSCRIPTION items it rests on, with confidence>
ILLEGIBLE: <regions or items that could not be read confidently — flagged with location, never guessed>
NOT OBSERVED: <questions the media could not answer>
BLOCKED: <lane-level trouble — CLI or tool failure, rejected media format, contract defect — with the exact error; or none>
```

Nothing may appear in INFERENCE without naming a TRANSCRIPTION anchor or
an ILLEGIBLE flag it rests on. A fabricated or unlocatable TRANSCRIPTION
item is the same defect class as an unanchored inference. Either way —
as with a report that asserts something outside its media or answers a
question that was not asked — the report is discarded and re-dispatched
with a corrected contract.

## Task fit

Route to Gemini (verified live): chart and figure reading, dashboard
screenshot QA (including captures too heavy for the browser pane), OCR of
scans and photos, image-set cataloging and comparison.

NOT YET ROUTABLE — verified failed 2026-07-24: audio (agy 1.1.6's
read_file tool rejects `audio/wave` as an unsupported MIME type; the
dispatch failed closed correctly). Video and PDF are untested. Do not
route audio/video/PDF until a dispatch verifies support after an agy
update or a ratified adapter exists; the model is capable, the CLI tool
layer is the limiter.

Never route to Gemini: code, git, pipeline runs, rank/stance/scoring
decisions, psychometric interpretation, anything the text-native toolchain
already answers deterministically.

## Extraction charter (Paul 2026-08-10)

Bulk raw text (long documents, large text sets) may route here as an
EXTRACTION dispatch when the coordinator's context must stay clean: same
contract fields, same report shape — TRANSCRIPTION carries the verbatim
extracts with locations, INFERENCE carries conclusions anchored to them,
ILLEGIBLE flags unreadable regions. The raw bulk never travels back;
findings and pointers do. Everything else about the lane is unchanged:
no decisions, no code, no scoring; the fabricated-anchor rule applies
identically. First live use doubles as the charter's verification run
(no invented work before then).

## Runtime (verified live 2026-07-24; re-verified on agy 1.1.11 2026-08-09)

- CLI: Antigravity CLI (`agy`) 1.1.11 (permission schema changed from
  1.1.6 — see below) at
  `C:\Users\pgoff\AppData\Local\agy\bin\agy.exe` — Google's successor to
  the retired Gemini CLI (individual OAuth tier ended 2026-06-18).
- Account: Paul's personal Google account (pgoff22@icloud.com). The
  UMN-managed account is ineligible for the individual tier. Credentials
  are never handled by Claude; sign-in is Paul's own browser action.
- Model pin: `gemini-3.6-flash-high` (Paul's choice; the CLI default).
  `agy models` lists alternatives (3.6/3.5 flash tiers, 3.1 pro).

Verified invocation — run from the media directory:

```powershell
$env:Path = "C:\Users\pgoff\AppData\Local\agy\bin;$env:Path"
agy -p "<perception contract>" --model gemini-3.6-flash-high `
  --add-dir <media-dir>
```

Load-bearing facts, each learned the hard way:

- Permission model (agy 1.1.11, re-verified 2026-08-09): permissions
  moved to `C:\Users\pgoff\.gemini\antigravity-cli\settings.json` —
  `{"permissions": {"allow": ["read_file(*)"]}}`, BOM-free. Wildcard
  syntax is `read_file(*)`; the old `read_file(**)` form and the old
  `~\.gemini\settings.json` permissions location are DEAD (auth stays
  in `~\.gemini\`). File reads are allowed; shell/terminal tools stay
  soft-denied in headless mode — that denial is a safety property of
  the lane, never widen it with `--dangerously-skip-permissions`.
- The contract must say "use your read_file tool to read <file>"
  explicitly. `@file` mentions do not attach media in print mode, and a
  blanket "no commands" prohibition stops the read tool too — prohibit
  "shell or terminal commands" instead.
- The settings file must be BOM-free JSON (PowerShell 5.1 `Out-File`
  writes a BOM that breaks the parser; use `[IO.File]::WriteAllText`).
- Re-auth when the token expires: interactive TUI only (`agy` refuses
  headless sign-in). Drive it with `scripts/agy_pty_login.py` (ConPTY
  driver). Its runtime files live under `<system temp>\agy_login\`:
  `agy_auth_url.txt` always holds the FRESHEST captured URL (no-latch),
  `agy_send.txt` is the keystroke channel (write `agy_send.tmp`, then
  `os.replace` — atomic), `agy_stop.txt` stops it, and a PID lock refuses
  concurrent runs. Paul completes the browser step and may need Google's
  one-time account-verification interstitial — those links are one-shot
  tokens, always use the freshest one, and a first visit to
  gemini.google.com in the browser clears account-level gating for
  brand-new accounts.
- Driver provenance: `scripts/agy_pty_login.py` was Claude-authored as
  session ops tooling during the 2026-07-24 auth recovery and promoted
  under a disclosed exception to the never-Claude-authors-code rule; its
  hardening pass was Codex-executed (@f9843ae) and ALL future edits route
  through Codex edit-only dispatches like any other code.

## Copy sync

The repository copy is canonical. After a ratified change, sync this
`SKILL.md`, `scripts/agy_pty_login.py`, and `.claude/commands/gemini.md`
to:

`C:\Users\pgoff\.claude\skills\gemini-perception\`

and `C:\Users\pgoff\.claude\commands\`.
