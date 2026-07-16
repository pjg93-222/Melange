# Audio Speaker-Identity Layer — Pre-Registration

**STATUS: DRAFT (PRE-LOCK) — this document is explicitly NOT LOCKED.**

audio-identity design 2026-07-16 (user-directed build). No pilot below (P1 onward) may run a
"look" and no bar may be judged until this document is locked. It **must not be locked** until all
three of the following happen, in order:

1. **The user approves the one-time model downloads.** No network access, no model download, and
   no LLM call exists anywhere in the identity code path today; the real embedding backends and whisper
   aligner hard-refuse (`BackendRefused`) without a complete LOCAL model directory. The three
   downloads awaiting approval, with sources and approximate sizes:
   - **facebook/wav2vec2-base** (the exact 768-dimensional embedding family used by Mestre and
     Ryan for speaker classification) — Hugging Face `facebook/wav2vec2-base`, approx. 360 MB.
   - **silero-vad** (voice-activity model, replaces the interim RMS gate in the diarizer) —
     GitHub `snakers4/silero-vad` (JIT export), approx. 2 MB.
   - **faster-whisper small** (CTranslate2 Whisper for word-level timestamps) — Hugging Face
     `Systran/faster-whisper-small`, approx. 465 MB.
   - **Aeneas + eSpeak local toolchain** (paper-faithful MFCC/dynamic-time-warp transcript
     boundaries) — exact package/binary versions and every executable hash must be pinned before
     a real sync map is generated; the alignment module only ingests the resulting JSON and never
     discovers or downloads this toolchain at runtime.
   ECAPA-VoxCeleb remains implemented only as a separately labeled engineering comparator; it is
   not the paper-faithful primary and may not silently replace Wav2Vec2.
   At lock time the SHA-256 of every downloaded model file gets pinned HERE, in this section, and
   the backends run `local_files_only` against those pinned files forever after.
2. **Input fingerprints are taken at a quiescent moment** (no live pipeline/collector jobs): the
   SHA-256 manifest of every enrollment clip, calibration wav, caption-MISMATCH negative, and
   curated hearing enters this document before any P1 trial runs.
3. **The user rules on the open design decisions D1/D2/D7** (contract Mode A vs B, venue
   amendment, hearings scope — see the decision list below).

Do not add a lock line to this file until all three are satisfied and the user says lock.

## Scope and standing rules

- **Verification, never identification.** Every acoustic check compares a unit against the ONE
  member the transcript/caption evidence claims (check T), and the acoustic layer (check A) may
  only AGREE or EXCLUDE. There is no argmax over the bank, no "best-matching member", and no
  reassignment of a rejected unit to a better-scoring member — a disagreement excludes the unit,
  period. `fec/b5_audio_verify2.py` exposes no identification API and its test suite asserts that
  at the source level.
- **Research candidates only.** Every artifact ends in `.json.candidate` with
  `status: RESEARCH_CANDIDATE_NOT_CONSUMED` and is consumed by nothing (traits, narratives,
  weekly refresh, receptivity) until user ratification; `fec/audit_full.py` enforces this.
- **The cosine threshold is never a code literal.** theta_accept, theta_enroll, and theta_eer live only in
  `b5_audio_identity_thresholds.json.candidate` (schema `b5-audio-identity-thresholds-v1`);
  EER itself is separately stored as the error-rate field `eer_rate`. Every consumer refuses to
  run (SystemExit code 2, message containing "thresholds artifact") when the artifact is absent,
  malformed, above the 5% stop bar, or not status `CALIBRATION_PASS`. Enrollment reads
  theta_enroll from this artifact and records its SHA-256; it has no free threshold CLI parameter.
- **Local model files are hash-pinned.** A real Wav2Vec2 or ECAPA backend refuses unless a
  `b5-audio-model-manifest-v1` with status `PINNED_LOCAL_MODEL` names the backend and matches every
  file in the local model directory byte-for-byte. Unlisted and modified files both refuse.
- **Enrollment floors** (from `fec/audio_rules.py`, the single source): ENROLL_MIN_CLIPS=3,
  ENROLL_MIN_EVENTS=2 (a voiceprint never rests on one recording's channel), ENROLL_MIN_SEC=180.0,
  plus a leave-one-clip-out integrity gate at theta_enroll; floors re-checked after quarantine.
  Verification gates: IDENTITY_MIN_COVERAGE=0.85, IDENTITY_MIN_MARGIN=0.10,
  IDENTITY_TURN_TRIM_SEC=0.5. Alignment gates: ALIGN_MIN_TURN_WORD_MATCH=0.80,
  ALIGN_MIN_HEARING_WORD_MATCH=0.70.
- **Identity evidence is hard evidence** (chyron/roll-call regex hits, reviewer confirmations) —
  never an LLM label; enrollment hard-refuses empty evidence strings.

## The two contract modes (user decision D1 — default fail-closed MODE B)

- **MODE A (substitutive):** a passing acoustic verification may stand in for ONE of the two human
  target-only reviews in the `b5_audio_reviews_v2` contract, halving reviewer load. Requires
  explicit user ratification; NOT active.
- **MODE B (additive, fail-closed — THE DEFAULT):** the acoustic check is an additional exclusion
  gate layered on top of the unchanged two-human-review contract. It can only EXCLUDE units; it
  never admits a unit, never substitutes for a human review, never relabels a speaker. MODE B is
  in force unless and until the user rules otherwise under D1.

## Pilot ladder P0-P5 (numeric bars — locked wording; above-bar = stop-and-report, never tune past)

- **P0 — synthetic/planted battery** (no downloads needed; spectral-test backend): label-swapped
  planted clips detected **>= 99 percent**; null (honest-label) false-rejection **<= 15 percent**;
  the whole battery byte-identical across two runs (determinism).
- **P1 — calibration DET/EER:** trials built from the **148 caption-MISMATCH negatives** +
  held-out MATCH positives + all-vs-all impostor trials. Bars: **EER <= 5 percent per corpus**
  (above = stop-and-report, never tune past); **>= 99 percent of the 148 negatives rejected at
  theta_accept**; a sex-parity FAR/FRR ratio **> 2x is a reported red flag, never silently
  recalibrated**; the thresholds artifact (`b5_audio_identity_thresholds.json.candidate`) is
  written. `fec/b5_audio_calibrate.py` is the deterministic score-level producer; it writes a
  non-consumable stop-bar artifact on a miss and never uses sex labels to tune thresholds.
- **P2 — cross-channel hard gate:** the **5 SHA-pinned Chip Roy HouseLive units** verified against
  a YouTube-legacy-enrolled print; bar **5/5 accepted**. Pre-declared remedy on failure:
  per-channel z-norm, then re-run P1. No other remedy may be invented after the look.
- **P3 — HouseLive dual-check** over **5 archive days**: a **100-unit human listen-check** with
  bar **0/100 false attribution** (binomial 95 percent upper bound 3.6 percent); a **20
  rejected-unit sensibleness sample**; and **byte-identical reproduction of the Chip Roy units**.
- **P4 — hearings:** **3 curated hearings**, hand-label one **30-minute stretch each**. Bars:
  **DER <= 10 percent**; **word-match >= 80 percent for >= 90 percent of member turns**; **median
  turn-boundary error <= 1.0 s**; **0 member false attributions**; **every witness turn lands in
  NONMEMBER clusters**.
- **P5 — WJ (Washington Journal) smoke**, recorded: run the chain end-to-end on one WJ program and
  record the outcome here; no numeric bar beyond completion + the standing exclusion rules.

## User decisions (open; none may be assumed)

- **D1** — Contract mode: MODE A (acoustic check substitutes for one human review) vs **MODE B
  (additive exclusion gate — the fail-closed default in force)**.
- **D2** — Venue amendment: whether the audio v2 contract's `on_air_interview`-only venue
  restriction is amended to admit identity-verified floor/HouseLive/hearing units.
- **D3** — Approval of the three one-time model downloads (names/sources/sizes above) and the
  SHA-256 pinning that follows.
- **D4** — Enrollment evidence standard: which identity_evidence classes qualify (chyron regex,
  roll-call, human reviewer) and who ratifies each member's bank entry (the bank's `ratified`
  field stays empty until then).
- **D5** — Thresholds ratification: accept the P1-calibrated theta_accept/theta_enroll/theta_eer
  and the separately reported EER rate, or
  order recalibration; disposition when a corpus EER exceeds the 5 percent stop-bar.
- **D6** — Cross-channel remedy: if P2 fails, apply the pre-declared per-channel z-norm (then
  re-run P1) or drop the cross-channel corpus.
- **D7** — Hearings scope: which hearing corpora enter (finance-only CHRG vs all-committee), and
  whether a witness-member collision poisons the whole hearing (current fail-closed behavior) or
  only the colliding turns.
- **D8** — Interviews corpus: whether multi-speaker interview audio enters the identity layer this
  round or stays deferred.
- **D9** — P3 listen-check staffing: who performs the 100-unit human listen-check and the
  20-unit reject sample (user or a user-designated delegate).
- **D10** — Storage/retention: where downloaded audio, models, and embeddings live (disk budget,
  outside OneDrive), and how long raw audio is retained after embedding.
- **D11** — Promotion gate: the exact conditions under which any `.json.candidate` identity
  artifact may be consumed (which pilots must have passed + explicit user ratification recorded).
- **D12** — WJ scope: whether the P5 smoke expands into a scored WJ corpus or remains a recorded
  smoke only.

## Module inventory (built 2026-07-16, TDD; all suites pass without torch/transformers/speechbrain/faster-whisper)

- `fec/b5_audio_embed.py` — embedding backend contract (`get_backend(name, model_dir,
  model_manifest)`, `cosine`, `BackendRefused`; `spectral-test` deterministic test backend;
  paper-faithful `wav2vec2` plus separately labeled `ecapa` comparator; both real backends refuse
  without a complete hash-pinned local model directory).
- `fec/b5_audio_calibrate.py` — deterministic labeled-score DET/EER calibration; separates
  `theta_eer` from `eer_rate`, applies the 148-negative/99% and per-corpus 5% bars, reports
  sex-parity diagnostics without retuning, and writes the only thresholds artifact consumers use.
- `fec/b5_audio_enroll.py` — enrollment bank builder (floors + leave-one-out gate) ->
  `b5_audio_enroll_bank.json.candidate` (schema `b5-audio-enroll-bank-v1`).
- `fec/b5_audio_verify2.py` — verification-only decisions (ACCEPT/REJECT/INDETERMINATE, margin,
  coverage; thresholds-artifact refusal, SystemExit 2); unratified enrollment entries are absent
  by default and require an explicit pilot-only override.
- `fec/b5_audio_diarize.py` — VAD + windowed embeddings + agglomerative clustering ->
  `{start,end,cluster,overlap}` segments; overlap = excluded, drop-never-repair.
- `fec/b5_audio_align_turns.py` — standard Aeneas fragment JSON supplies the primary MFCC/DTW
  per-turn boundaries, while an independently aligned local-ASR word stream supplies word-match;
  fragment count/text/time mismatch fails the whole hearing closed. The ASR-only monotonic path is
  retained as an explicitly labeled fallback/test route.
- `fec/b5_audio_attrib.py` — dual-check attribution verdicts (check T + check A must agree;
  fail-closed precedence) -> `b5_audio_attrib_<corpus>.json.candidate` + rejects/mismatch ledgers;
  runtime + source guards against the protected live artifacts.
- `fec/fetch_hearings_media.py` + `hearings_media_map.csv` (worktree root) — hearings media
  acquisition, fail-closed: the shipped map holds placeholder rows only (empty video_url), rows
  must be hand-curated by the user, packages are verified against the hearings db, `--dry-run` is
  the default, and real fetching requires the explicit `--fetch` flag (user-gated; verified
  packages only; yt-dlp download-archive plus `--no-overwrites` prevents replacement).
- Tests: `fec/tests/test_audio_calibrate.py` (5), `fec/tests/test_audio_identity.py` (23),
  `fec/tests/test_audio_diarize.py` (5),
  `fec/tests/test_audio_align.py` (8), `fec/tests/test_audio_attrib.py` (17),
  `fec/tests/test_hearings_media.py` (5) — all registered in `fec/tests/run_tests.py`; audit
  guards live in `fec/audit_full.py`.

## Open items

- The real **P1 labeled-trial artifact is not yet assembled**. The calibration producer exists,
  but it may not see the 148 negatives or any real embedding score until this document is locked
  with the input fingerprint manifest.
- silero-VAD swap-in for the diarizer's interim RMS gate is documented behind the same
  `(samples, sr) -> bool-mask` interface; blocked on D3.
- The Aeneas sync-map adapter is wired and tested, but the local Aeneas/eSpeak toolchain is not yet
  version/hash-pinned and no real sync map has been generated. That toolchain pin plus the
  preregistered human boundary-validation pilot remain mandatory before scoring.
- Input fingerprint manifest: to be inserted at a quiescent moment (pre-lock requirement 2).
