# Fable v2 adversarial audit

Fable ran as a `gpt-5.6-sol` review role and inspected the corrected manifest,
media receipts, all 30 Gemini web receipts, and the stored C-SPAN turn data.

## Verdict

- **Conditional go** for a larger research-only perception validation phase,
  with semantic transcript-to-window alignment enforced as a fail-closed gate.
- **Hard no** for Big Five, durable behavioral criteria, or production
  cross-reference updates.

## Findings

- Integrity is complete: 30 manifest items, 30 corrected media receipts, and
  30 Flash web results with exact ID sets and matching media hashes.
- HLS segment arithmetic is correct in 30/30.
- Independent transcript-to-stored-turn alignment improved from 2/30 in the
  failed first pass to 22/30 in v2.
- Unresolved or contradicted target alignment: F004, F006, F008, F011, F013,
  F018, F020, and F025.
- Timestamp-clean receipts: 28/30. F015 and F026 contain out-of-bounds
  evidence; all model `quality_flags` arrays remained empty.
- Cases with at least one in-bounds audio-side and visual-side citation: 27/30.
- Identity is manifest-assisted: 30/30 are consistency confirmations, not a
  blind or open-set identification-accuracy estimate.
- Output distributions remain highly homogeneous and are confounded by the
  Washington Journal camera and interview format.
- No direct personality, mental-state, health, protected-attribute, honesty,
  intelligence, or character claims appeared in the result bodies.

## Required admission gates

1. Map local ASR/caption text to the selected program, turn, and source window
   above a preregistered threshold.
2. Reject or rerender every semantic mismatch and every out-of-bounds
   timestamp.
3. Require at least one valid audio and one valid visual citation.
4. Normalize evidence modality values.
5. Add repeated ratings, a human-coded subset, and mismatch/decoy identity
   controls.
6. Keep production consumers at zero until construct validity and reliability
   are demonstrated.
