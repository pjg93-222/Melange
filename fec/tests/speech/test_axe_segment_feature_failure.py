import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

_P = Path(__file__).resolve().parents[2] / "speech" / "axe_segment.py"
_spec = importlib.util.spec_from_file_location("axe_segment_under_test", _P)
axe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(axe)


class _Smile:
    def __init__(self, fail_on):
        self.calls = 0
        self.fail_on = fail_on

    def process_signal(self, signal, sr):
        self.calls += 1
        if self.calls == self.fail_on:
            raise RuntimeError("boom")
        return pd.DataFrame([{v: 1.0 for v in axe.FEATURE_COLUMNS.values()}])


def _run(fail_on):
    ep = {"guid": "g", "sid": "s", "member": "m", "package": "p", "date": "d",
          "source_audio_sha256": "a", "source_manifest_sha256": "b",
          "turns": [{"rowid": 1, "text": "t"}]}
    audio = np.zeros(16000 * 30, dtype="float32")
    spans = [(0.0, 10.0, 1.0, 0, 1, 0), (10.0, 20.0, 1.0, 0, 1, 0)]
    return axe.feature_records(ep, audio, 16000, [], ["a", "b"], spans, _Smile(fail_on))


def test_feature_failure_is_counted():
    records, failed = _run(2)
    assert failed == 1 and len(records) == 1
    records, failed = _run(None)
    assert failed == 0 and len(records) == 2
