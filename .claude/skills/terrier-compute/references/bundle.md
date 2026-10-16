# Deterministic bundles and Terrier parity

Prepared 2026-10-16 from the 2026-10-14 procedure. Historical D-177/D-198/D-201/D-202
labels explain the retained gates; they do not authorize new builds or deletion.

## Bundle identity

Keep the bundle ZIP byte-identical across the compared Windows/container runs.
The source procedure's `tools/build_bundle_v4.py` canonical form uses:

- Every polygon ring starts at its smallest `(x, y)` after six-decimal rounding;
  preserve orientation, closing point, precision and key order.
- Holes sorted by their start vertex; exterior first.
- ZIP `create_system=3` on every platform and LF for the `.sha256` sidecar.
- Non-polygon geometry passed through unchanged.

Verify these properties in the selected source. If the bytes differ, diagnose the
writer/input differences; do not loosen the gate. The historical v4 key appends
`geom-canonical-1` only when `row_framework.geometry_form` records it; preserve
legacy keys/imports and reject unknown forms. Do not rewrite existing data merely
to update a version label or satisfy documentation.

## Comparison procedure

From the explicit Terrier checkout, validate these command shapes against the
selected tool before a separately authorized run:

```text
python tools/compute_parity.py --steps bundle --inputs-from <private-input-root> --link-inputs --single-reference --negative-control
python tools/compute_parity.py --reuse-windows --reuse-container --negative-control
```

The reuse form requires matching recorded source, image and input identities; it
does not create missing evidence. `--single-reference` must be supported by the
accepted contract. Do not emulate it by passing the same reference twice.

`--link-inputs` is unsafe for in-place writers and historically refused for
`contacts`, which changes `street.sqlite3`. Never hard-link a mutable live store.
Retain these comparison gates:

- SQLite content: every required table exact; FTS5 shadow tables compared after
  accepted same-library rebuild plus 400 MATCH queries; contentless tables exact.
- Bundle ZIP exact. Other ZIP member/field normalization only where independently
  established by the accepted Windows variance contract, never by blanket masking.
- `density.json`, ingest receipt and bundle `.sha256` byte identity.
- Named historical variance only: `street.metadata[created_at_utc]`,
  `scores.metadata[built_utc,w1.seconds]`,
  `walk.meta[built_utc,qa.peak_memory_mb,qa.timing]`; verify applicability and do not
  expand the list to hide a failing semantic value.
- Each required negative control detected; record actual compared steps/districts
  and counts in `parity_report.json`.

Keep voter-derived comparison copies private. Retain required recovery evidence,
then dispose only of exact owned copies under the applicable retention decision.
One district's pass is not proof that every other district or hosted mode passed.
