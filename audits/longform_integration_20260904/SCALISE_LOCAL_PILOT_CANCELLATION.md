# Redundant local classifier stopped

September 4, 2026, approximately 17:35 ET. The scoped local Qwen text-classification worker (PID 29376) was stopped only after its actual process command was verified to name `fec.speech.classify_member_longform_full_turns_local` and the immutable `scalise-20260904/ready_sources.jsonl` input.

The worker remained compute-active but had not produced a completed classification artifact. It was superseded by two separately performed internal full-transcript annotation passes and exact-boundary reconciliation: 32 candidate intervals, 20.657 minutes, longest 134.9 seconds. No Qwen success or failure of the source itself is inferred from cancellation. The source files and model files were not deleted or altered.

The real acoustic continuity worker for the reconciled intervals and the separate transcript-repair worker were not targeted. No human review, profile admission, or publication was performed by this cancellation.
