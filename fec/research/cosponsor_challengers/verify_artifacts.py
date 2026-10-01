"""Verify completed artifacts without refitting or changing frozen predictions."""
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from audit_data import OUT, digest


def verify():
    code = Path(__file__).resolve().parent
    freeze = json.loads((OUT / "final_prediction_freeze.json").read_text())
    final = json.loads((OUT / "final_results.json").read_text())
    selection = json.loads((OUT / "development_results.json").read_text())
    panel = json.loads((OUT / "panel_receipt.json").read_text())
    benchmark = json.loads((OUT / "simple_benchmark_freeze.json").read_text())
    assert digest(OUT / "development_results.json") == freeze["selection_sha256"]
    assert digest(code / "PROTOCOL.md") == freeze["protocol_sha256"]
    assert digest(code / "run_models.py") == freeze["runner_sha256"]
    assert dt.datetime.fromisoformat(selection["frozen_utc"]) < dt.datetime.fromisoformat(freeze["frozen_utc"])
    assert dt.datetime.fromisoformat(freeze["frozen_utc"]) < dt.datetime.fromisoformat(final["evaluated_utc"])
    rows = freeze["rows"]
    assert rows == panel["splits"]["119"]["mature_rows"]
    predictions = {}
    for name, expected in freeze["predictions"].items():
        path = OUT / "final_predictions" / f"{name}.npy"
        actual = digest(path)
        assert actual == expected, name
        p = np.load(path, mmap_mode="r")
        assert p.shape == (rows,), name
        assert np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all(), name
        assert final["models"][name]["rows"] == rows, name
        assert final["models"][name]["events"] == panel["splits"]["119"]["mature_events"], name
        predictions[name] = dict(sha256=actual, rows=rows, finite_bounded=True,
                                 min=float(p.min()), max=float(p.max()), matches_original_freeze=True)
    for name, rule in benchmark["rules"].items():
        path = OUT / f"simple_prediction_{name}.npy"
        assert digest(path) == rule["sha256"], name
        p = np.load(path, mmap_mode="r")
        assert p.shape == (rows,) and np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all(), name
    scored = pq.ParquetFile(OUT / "scored_final_forecasts.parquet")
    assert scored.metadata.num_rows == rows
    # Check every exported probability against its frozen array, in bounded batches.
    arrays = {name: np.load(OUT / "final_predictions" / f"{name}.npy", mmap_mode="r")
              for name in predictions}
    offset, events = 0, 0
    for batch in scored.iter_batches(batch_size=100_000, columns=["y", *predictions]):
        events += int(batch.column("y").to_numpy().sum())
        for name, p in arrays.items():
            assert np.array_equal(batch.column(name).to_numpy(), p[offset:offset+len(batch)]), name
        offset += len(batch)
    assert offset == rows and events == panel["splits"]["119"]["mature_events"]
    final_models = {name: digest(OUT / "models" / f"final_{name}.joblib") for name in predictions}
    receipts = ["REPORT.md", "data_audit.json", "panel_receipt.json", "panel_validation.json",
                "public_extended_audit.json", "public_lead_time_audit.json", "verification_receipt.json",
                "development_results.json", "final_prediction_freeze.json", "final_results.json",
                "component_diagnostics.json", "simple_benchmark_freeze.json", "simple_benchmark_results.json",
                "scored_final_forecasts.parquet", "model_run.log", "feature_names.json", "identifiers.json"]
    manifest = dict(
        verified_utc=dt.datetime.now(dt.timezone.utc).isoformat(), status="passed",
        provenance="Prediction, selection, protocol and runner hashes match the pre-evaluation freeze. "
                   "Model-file and report hashes below are recorded at completion, not claimed as earlier timestamps. "
                   "Full source/panel validation is recorded in panel_validation.json.",
        forecasts_frozen_utc=freeze["frozen_utc"], predictions=predictions,
        simple_prediction_hashes_match=True, scored_export_matches_every_frozen_probability=True,
        final_model_sha256=final_models,
        artifact_sha256={name: digest(OUT / name) for name in receipts},
        code_sha256={p.name: digest(p) for p in sorted(code.iterdir()) if p.suffix in {".py", ".md"}},
        public_stance_and_coverage_predictions_identical=(
            freeze["predictions"]["boosted_public"] == freeze["predictions"]["boosted_public_coverage"]),
        rows=rows, events=events,
    )
    path = OUT / "experiment_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": "passed", "models": len(predictions), "rows_each": rows,
                      "events": events, "export_matches": True, "manifest": str(path)}), flush=True)


if __name__ == "__main__":
    verify()
