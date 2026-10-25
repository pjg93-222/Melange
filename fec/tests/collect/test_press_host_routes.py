from __future__ import annotations

from pathlib import Path
import subprocess
import sys

FEC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FEC))
from collect.refresh_press_stream import find_rscript


def test_host_routes_against_recorded_official_site_fixtures():
    result = subprocess.run(
        [find_rscript(), str(Path(__file__).with_suffix(".R")),
         str(FEC / "collect/press_host_routes.R"),
         str(FEC / "collect/press_wordpress_custom_posts.R"),
         str(FEC / "collect/press_backlog.R"),
         str(Path(__file__).with_name("fixtures") / "press_host_routes")],
        capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: press host routes" in result.stdout
