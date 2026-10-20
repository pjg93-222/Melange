"""WJ scraper: a transient chromote timeout must be retried, and a persistent one must fail soft.

Incident 2026-10-18: the weekly Washington Journal search died with exit 1 because the is_blocked() and
load-more chromote calls had no tryCatch.  The R fixtures run offline (no Chrome, no network)."""
from pathlib import Path
import subprocess
import sys

FEC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FEC))
from collect.refresh_press_stream import find_rscript


def test_transient_chromote_timeouts_are_retried_and_exhaustion_fails_soft():
    result = subprocess.run([
        find_rscript(), str(Path(__file__).with_suffix('.R')),
        str(FEC.parent / 'cspan' / 'cspan_scrape.R'),
    ], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PASS: cspan chromote retry' in result.stdout
