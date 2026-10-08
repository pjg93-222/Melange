All eight evidence items are read. Here is the adjudication.

# Ruling: PROCEED — with the mandatory safeguards below

The plan is structurally conservative: it grants no new redistribution, no cross-source merges, no analytical enablement, and it excludes the PII-bearing raw workbooks. Nothing in it contradicts the adjudicated spec (§4–§10) or the diagnostic's Phase 1 backlog (§7). The issues I found are binding conditions, not structural flaws. One conditional downgrade: if safeguard S-1 (A-0 provenance) cannot be satisfied, the legacy-seed portion alone drops to BLOCK while items 2–4 of the plan still proceed.

## Question 1 — Is the narrow legacy A-0 interpretation defensible?

**Yes, as an interim scope — because it is the minimal reading, and because the artifact is already Paul's internal data.** `data/members/staff_directory.json` has shipped in the repo and fed the member desk for months; restricted-local, source-native re-ingestion of the contact-free version claims nothing that wasn't already occurring, and the interpretation deliberately withholds every expansion a broad reading might permit (workbooks, merges, analysis, publication). If the interpretation errs, it errs narrow, which is the safe failure direction.

But an authority ruling must carry its provenance. Under the project's own data-rules-provenance discipline, a verbatim Paul quote and a session interpretation are different evidence classes, and the A-0 manifest as proposed would seal a *session interpretation* of "corpus completion." That is acceptable only if the manifest says so explicitly (S-1 below). An A-0 that silently presents interpreted scope as user-ruled scope would be a provenance defect worse than the gap it fills.

## Question 2 — May `source_manifest.enabled` mean source-native ingest without analytical enablement?

**Yes, but only with the overload contained.** The code and the prose currently use "enabled" for two different gates: in `fec/staffer_network/legacy_seed.py:24`, `manifest.enabled` is the *ingest* gate (the file cannot be opened without it), while the spec and diagnostic use "source enabled" to mean *analysis/canonical* eligibility ("keep the source quarantined unless C-5 passes," "the Politico source stays disabled"). Setting `enabled=true` to permit the seed import is fine **if and only if**:

- `authority_scope` carries the exact restricted scope string (`restricted-local source-native seed only`, plus the provenance statement from S-1), so the boolean is never read without its scope;
- analysis/canonical eligibility is governed exclusively by the separate `STAFF_NET` dial and per-source enablement receipts, and a negative-control test proves no analysis-plane consumer keys off `manifest.enabled` (S-4);
- the schema stays v1 — do not add fields; `validate_source_manifest` rejects extras, and the `authority_scope` string is the sanctioned carrier for scope semantics.

One code-level tightening is mandatory here: `legacy_seed._authorize` (`legacy_seed.py:26-29`) accepts `public` and `public-safe-derived-only` redistribution classes. The narrow A-0 authorizes only `restricted-local-only`. As written, a mis-sealed manifest claiming `public` would pass the seed's own gate. Tighten the seed gate (or pin the sealed manifest's class with a test) before the import runs.

## Question 3 — Adjudication of the five plan items

**Item 1 (legacy seed):** Approved under S-1/S-2. The existing conservation logic is sound — `expected_rows` checks both observed and accepted counts (`legacy_seed.py:75-78`), which forces zero rejects, and `assert_public_safe` runs per row. Keeping the raw Quorum workbooks quarantined is correct and required; the diagnostic (§5, §7) demands a separate A-0/A-1 for them.

**Item 2 (LDA immutable-generation sweep):** Approved under S-3. I verified the premise: `_run_sweep` in `collect_lda_filings.py:757-820` writes into a fixed `sweeps/<year>/` directory and resumes from the prior manifest, so it genuinely cannot establish a frozen new inventory or safely disposition the 88 duplicates. An immutable-generation *mode of the same module* honors the "no parallel collector" ruling. The 15/min anonymous rate matches the collector's existing `LDA_RPM` default of 15. Note the cost: a full recollect is roughly 21,600+ pages ≈ 24 hours at 15/min; a registered key (120/min) would cut that to ~3 hours — registering is Paul's call, flag it as an option, don't wait on it.

**Item 3 (LittleSis):** Approved under S-5, with one wording correction. The fresh relationship-file hash being byte-identical to the audited 2026-08-29 dump is strong pairing evidence, but it proves hash identity, not that the site published the two files as one vintage — record the pairing basis in the manifest rather than asserting "same vintage." And "100% endpoint referential integrity" must mean 100% *over the accepted set* with dangling relationships explicitly reason-coded and rejected — spec §5.5 anticipates rejects ("reject/quarantine dangling relationships"); an absolute-100% bar would let a handful of curated-data dangling edges permanently quarantine the source in a way the contract never intended.

**Items 4 and 5:** Approved as written. They restate adjudicated rulings (no historical committee back-projection; no merges, weighted edges, temporal weight from undated evidence, or influence claims) and add nothing new.

## Mandatory safeguards

**S-1 — A-0 provenance.** The sealed A-0 manifest must embed, in `authority_scope`, either Paul's verbatim corpus-completion request text with date, or an explicit statement that the scope is a session interpretation of that request pending ratification. The receipt records which. If neither can be produced, the legacy seed is BLOCKED; the rest of P1 proceeds.

**S-2 — Legacy seed input pinning.** Before ingest, verify the input file's SHA-256 equals the remediated hash `7abfbc9e…d179df3b52` from `legacy_artifact_registry_20260829.json` and refuse anything else — in particular the original `8b2457…f8b4ba`. `strip_document` would happen to strip the original's contact fields, but the PII-bearing bytes must never enter the processing path at all; hash-pin, don't rely on stripping. Tighten `_authorize` to `restricted-local-only` per Question 2. Negative-control tests: disabled manifest refused, non-AUTHORIZED refused, wrong redistribution class refused, wrong input hash refused, contact-bearing row fails `assert_public_safe`.

**S-3 — LDA generation contract.** (a) New generations write to their own dated root; the mode refuses to run into an existing nonempty generation directory. (b) A before/after hash inventory proves the 2026-08-29 sweeps are byte-untouched. (c) The drift-disposition rule is frozen *before* the run, not improvised after: page-1 count captured at start and end; if end > start (expected for live 2026 — a 2,250-page year takes ~2.5 hours at 15/min), every excess UUID must be dispositioned as posted-during-sweep with timestamp evidence inside the run window, or the year re-sweeps. C-5 verdict computed fail-closed by the existing `lda_contract` audit against the generation root. (d) Rate receipt records `LDA_RPM=15`, anonymous, terms-checked date.

**S-4 — Enablement containment.** A registered test asserts no module outside `fec/staffer_network` ingest paths reads `manifest["enabled"]`; `STAFF_NET` stays `off`; the analysis branch stays unarmed.

**S-5 — LittleSis contract.** Manifest records both file hashes/bytes, `license` = CC BY-SA with `terms_uri` and `terms_checked_at`, the pairing basis (hash identity to the audited dump plus both download timestamps), and streaming census counts. Conservation is exact (`observed = accepted + rejected`, reasons enumerated); enablement requires zero dangling among accepted relationships. Raw gzips stay machine-local; only the manifest/aggregate receipt is repo-visible. Share-alike implications arise only if derived aggregates are ever published — that adjudication is deferred, and the manifest should say so.

**S-6 — Test registration and paths.** All new test modules registered explicitly in the `fec/tests/run_tests.py` lane (the diagnostic warns unregistered tests don't run), and any new roots added to `fec/paths.py` plus the path-resolution audit.

Remaining risk after safeguards: the A-0 provenance question is the only item that could retroactively invalidate work — everything else fails closed. Nothing in this P1 scope touches canonical facts, published surfaces, or the 200-row identity adjudication queue, which remain Paul-gated exactly as the diagnostic leaves them.
