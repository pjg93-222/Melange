"""Drift guard: every --flag the PS1 passes to the R collector must be accepted by its parse_args."""
import re
from pathlib import Path

FEC = Path(__file__).resolve().parents[2]


def test_ps1_flags_are_accepted_by_collector():
    ps1 = (FEC / "run_congress_fulltext_pipeline.ps1").read_text(encoding="utf-8")
    r = (FEC / "harvest_congress_text_httr.R").read_text(encoding="utf-8")
    passed = set(re.findall(r"\$argList\.Add\('--([a-z_]+)'\)", ps1)) - {"no-echo", "no-restore", "args"}
    body = r[r.index("parse_args <- function"):]
    body = body[: body.index("\n}\n")]
    defaults = body[body.index("out <- list("): body.index("i <- 1L")]
    accepted = set(re.findall(r"\b([a-z_]+)\s*=", defaults)) | set(re.findall(r'"--([a-z_]+)"', body))
    assert passed, "no flags extracted from PS1"
    assert {"records", "out", "resume"} <= accepted, accepted
    assert passed <= accepted, f"PS1 passes flags the collector rejects: {sorted(passed - accepted)}"
    # -MinDelay is wired to the collector's --delay (clamped 0-60 to match R's bound).
    assert "delay" in passed
    assert re.search(r"\$argList\.Add\('--delay'\);\s*\$argList\.Add\(.*\$MinDelay", ps1)
    assert "Math]::Min(60.0" in ps1 and "Math]::Max(0.0" in ps1
