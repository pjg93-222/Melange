from __future__ import annotations

from pathlib import Path
import subprocess
import sys

FEC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FEC))
from collect.refresh_press_stream import find_rscript


def test_terminal_nonarticle_rules_against_real_failed_urls():
    result = subprocess.run(
        [find_rscript(), str(Path(__file__).with_suffix(".R")), str(FEC / "collect/refresh_press_delta.R")],
        capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: terminal non-article rules" in result.stdout
