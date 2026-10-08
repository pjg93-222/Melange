# Gemini Flash audiovisual interview pilot

## Outcome

- Real stored C-SPAN interview clips tested: **30/30**
- Flash mode verified at submission/result: **30/30**
- Local media SHA-256 verified: **30/30**
- HLS segment arithmetic and media hashes verified: **30/30**
- Independent stored-turn semantic alignment: **22/30 (73.3%)**
- Manifest speaker name matched: **30/30**
- Identity status `confirmed`: **30/30**
- Mean identity confidence: **0.861**
- Audio observable coverage: **30/30**
- Visual observable coverage: **30/30**
- At least one in-bounds audio and visual citation: **27/30**
- Fully schema/timestamp clean: **28/30 (93.3%)**
- Timestamp-bounded evidence: **28/30 (93.3%)**

## Interpretation

This establishes that Gemini Flash can process the actual audio and visual
tracks, populate both behavior modalities, and sort the sample against the
permitted private identity manifest. It is a manifest-assisted consistency
test, not a blind face/voice identification benchmark.

The repaired HLS clipper improved independent stored-turn alignment from 2/30
in the failed first pass to 22/30. Eight cases remain unresolved or contradicted
(F004, F006, F008, F011, F013, F018, F020, F025).

2 receipts contain at least one evidence timestamp beyond the end of the
clip. Those observations remain preserved as model errors. The behavior labels
also do not yet have independent human ground truth, so they are feasibility
signals rather than validated Big Five or behavioral measurements.

## Decision

- **Conditional go** for a larger research-only perception validation phase,
  only with fail-closed semantic alignment.
- **Hard no** for updating production Big Five, behavioral criteria, or
  cross-reference scores from these outputs.

Before any larger run, reject or rerender unresolved cases, fail every
out-of-bounds receipt, require both in-bounds modalities, normalize evidence
modality values, add repeated and human-coded ratings, and add mismatch/decoy
identity controls. Keep production consumers at zero.

## Reproducibility

- Frozen sample: `pilot_manifest_30_fable_temporally_verified.json`
- Per-interview receipts: `results_web_v2/F001.json` through `F030.json`
- Machine summary: `pilot_summary_v2.json`
- Independent review: `FABLE_V2_AUDIT.md`
- Flash-only CLI fallback: `run_flash_av_pilot.py`
