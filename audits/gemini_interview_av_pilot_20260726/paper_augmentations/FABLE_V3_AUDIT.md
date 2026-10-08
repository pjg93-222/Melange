# Fable v3 terminal audit

Fable ran as the requested `gpt-5.6-sol` read-only reviewer after all model
calls and scoring were complete.

## Verified

- 32 expected tasks and 32 result wrappers exist.
- Task IDs, conditions, manifest hashes, actual media hashes, Flash labels,
  and 32 unique conversation URLs reconcile.
- The central result is reproducible: seven of eight selected v2 grounding
  failures repaired, both sentinels retained, one of two hidden mismatches
  detected, and one nominal source pair marked mismatched.
- F004's actual A/V derivative is 85.8 seconds with both streams; its
  116.5–125-second evidence is genuinely out of bounds.

## Priority findings

1. **F018 is a source-label defect.** Its stored turn is assigned to Jamie
   Raskin but contains the host introduction and caller speech. The case must
   be relabeled or split before performance interpretation.
2. **M002 is a decisive integration failure.** Flash labeled deliberately
   crossed F018 video/F025 audio as matched and synchronized with 0.95
   confidence, including unsupported phoneme/lip-alignment claims.
3. **M001 was an easy identity-text shortcut.** Visible lower-third text named
   Adriano Espaillat while the audio named Buddy Carter, so its detection does
   not demonstrate general synchronization ability.
4. **The original scorer under-enforced the protocol.** The terminal pass was
   expanded to validate all enums, types, confidence, excerpt length,
   event-order references, single-modality consistency, and core receipt
   fields. This newly rejected F020 because `displayed_text` used objects
   instead of required strings, lowering clean primary receipts from 29/30 to
   28/30.
5. **The post-repair preflight was stale.** It is now always regenerated and
   records `PASS` with zero invalid selected sources.
6. **The comparison is an engineering before/after, not a controlled model
   effect.** It jointly changes media repair, target trimming, prompting,
   schema, and backend run. Single excerpts are not ASR WER or
   speaker-attribution accuracy.
7. There is no human event/speaker/synchronization ground truth, no repeated
   ratings, only two mismatch controls, and no immutable backend version
   beyond the Gemini web `Flash` label.

## Verdict

- **No-go** for a larger perception-only validation in the current state.
- **Absolute no-go** for production, Big Five, behavioral criteria, or
  production cross-reference updates.
- **Go only as a remedial debugging harness** after F018 relabeling, human
  event/speaker/synchronization gold, independently verified A/V alignment,
  normal offscreen-speech controls, harder mismatch controls, repeated runs,
  and a larger control set.
