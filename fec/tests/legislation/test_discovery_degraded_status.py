"""Discovery's verdict: PASS only when Congress.gov served the pages; a fallback exits 0 but is DEGRADED.

DEVIATIONS-A #1 (2026-10-27): since 09-13 every scheduled run took the GovInfo fallback, exited 0 and was
sealed PASS. The wrapper now names the source from the checkpoint manifest's primary_instrument (the same
field the weekly reads) in discovery_status.json, and exits non-zero only when there is no usable data.
"""
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from legislation import refresh_legislation_discovery as REFRESH


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def world(tmp_path, monkeypatch):
    out = tmp_path / "current"
    registry = tmp_path / "registry.json"
    write(registry, {"categories": [{"id": "payments"}]})
    monkeypatch.setattr(REFRESH, "REGISTRY", registry)
    monkeypatch.setattr(sys, "argv", ["discovery", "--out", str(out)])
    monkeypatch.setattr(REFRESH, "node_runtime", lambda: ("node", {}))
    monkeypatch.setattr(REFRESH, "PIPELINE_LOCK", tmp_path / ".pipeline_run.lock")
    monkeypatch.delenv("MELANGE_PIPELINE_LOCK_TOKEN", raising=False)
    monkeypatch.delenv("MELANGE_PIPELINE_LOCK_OWNER_PID", raising=False)
    calls = []

    def install(collector=None, fallback=None):
        def run(command, **kwargs):
            calls.append(command)
            if command[1] == str(REFRESH.COLLECTOR):
                return collector(out)
            assert command[1] == str(REFRESH.GOVINFO_FALLBACK)
            return fallback(out)
        monkeypatch.setattr(REFRESH.subprocess, "run", run)
    return SimpleNamespace(out=out, calls=calls, install=install, monkeypatch=monkeypatch)


def complete(out, instrument, **extra):
    write(out / "manifest.json", {"schema": "acu-congress-advanced-pages-manifest-v1", "status": "complete",
                                  "primary_instrument": instrument, "completed_at": "now", **extra})
    (out / "congress_advanced_records.ndjson").write_text('{"canonical_key":"119:hr:1"}\n', encoding="utf-8")
    return SimpleNamespace(returncode=0)


def hand_solve_timeout(out):
    # What collect_congress_member_pages.mjs writes when nobody solves the check within 20 min.
    write(out / "manifest.partial.4242.json", {
        "schema": "acu-congress-advanced-pages-manifest-v1", "status": "failed",
        "error": {"name": "HandSolveTimeoutError", "code": "CONGRESS_AUTOMATIC_VERIFICATION_TIMEOUT"},
        "automatic_verification_timeout": {"classification": "automatic_verification_timeout",
                                           "cause": "hand_solve_timeout",
                                           "collection_stopped_without_result_acceptance": True}})
    return SimpleNamespace(returncode=1)


def status(out):
    return json.loads((out / REFRESH.STATUS_FILE).read_text(encoding="utf-8"))


def test_unattended_hand_solve_timeout_falls_back_exit_0_and_is_degraded_never_pass(world):
    world.install(collector=hand_solve_timeout,
                  fallback=lambda out: complete(out, REFRESH.GOVINFO_SOURCE, discovery_status="DEGRADED"))
    assert REFRESH.main() == 0
    verdict = status(world.out)
    assert verdict["status"] == "DEGRADED" and verdict["status"] != "PASS"
    assert verdict["source"] == REFRESH.GOVINFO_SOURCE
    assert verdict["reason"] == "CONGRESS_AUTOMATIC_VERIFICATION_TIMEOUT"
    assert verdict["browser_failure"].endswith("manifest.partial.4242.json")
    cycle = json.loads((world.out / REFRESH.CYCLE_FILE).read_text())
    assert cycle["outcome"] == "DEGRADED" and cycle["outcome_source"] == REFRESH.GOVINFO_SOURCE
    assert len(world.calls) == 2


def test_congress_gov_run_is_pass(world):
    world.install(collector=lambda out: complete(out, REFRESH.CONGRESS_SOURCE))
    assert REFRESH.main() == 0
    assert status(world.out)["status"] == "PASS"
    assert status(world.out)["source"] == "Congress.gov Advanced Search - Legislation"


def test_congress_gov_run_with_uncollected_pages_is_degraded_and_still_exits_0(world):
    instrument = REFRESH.CONGRESS_SOURCE + " (incomplete: 3 page(s) not collected)"
    world.install(collector=lambda out: complete(out, instrument, coverage_gaps=3))
    assert REFRESH.main() == 0
    verdict = status(world.out)
    assert verdict["status"] == "DEGRADED" and verdict["source"] == instrument
    assert verdict["reason"] == "3 page(s) not collected"


def test_a_true_failure_with_no_usable_data_exits_non_zero(world):
    world.install(collector=lambda out: SimpleNamespace(returncode=1))
    with pytest.raises(SystemExit) as raised:
        REFRESH.main()
    assert raised.value.code == 1
    assert not (world.out / REFRESH.STATUS_FILE).exists()


def test_stale_status_from_an_earlier_run_is_removed_before_the_walk(world):
    write(world.out / REFRESH.STATUS_FILE, {"schema": REFRESH.STATUS_SCHEMA, "status": "PASS"})
    world.install(collector=lambda out: SimpleNamespace(returncode=1))
    with pytest.raises(SystemExit):
        REFRESH.main()
    assert REFRESH.read_discovery_status(world.out)["status"] == "DEGRADED"


# --- shared writer lease: a standalone walk vs a daily/weekly chain (coordinator 2026-10-27) ---------

def _lock_payload(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_a_standalone_walk_holds_the_pipeline_lease_for_its_whole_run(world):
    seen = {}

    def collector(out):
        seen["lease"] = _lock_payload(REFRESH.PIPELINE_LOCK)
        return complete(out, REFRESH.CONGRESS_SOURCE)

    world.install(collector=collector)
    environments = []
    real_run = REFRESH.subprocess.run

    def run(command, **kwargs):
        environments.append(kwargs.get("env") or {})
        return real_run(command, **kwargs)

    world.monkeypatch.setattr(REFRESH.subprocess, "run", run)
    assert REFRESH.main() == 0
    import os
    assert seen["lease"]["owner_kind"] == "congress_discovery" and seen["lease"]["pid"] == os.getpid()
    # The collector gets the lease token, so it can refuse to write if the lease is no longer its own.
    assert environments[0]["MELANGE_PIPELINE_LOCK_TOKEN"] == seen["lease"]["token"]
    assert not REFRESH.PIPELINE_LOCK.exists()   # released at the end


def test_a_chain_starting_mid_walk_refuses_and_writes_nothing(world):
    """What the daily's congress pipeline does at its first line while a walk holds the lease."""
    import os
    from pipeline_lock import pipeline_run_lock

    def collector(out):
        with pytest.raises(RuntimeError, match="already running"):
            with pipeline_run_lock(REFRESH.PIPELINE_LOCK, owner_kind="congress_pipeline"):
                pass
        return complete(out, REFRESH.CONGRESS_SOURCE)

    world.install(collector=collector)
    assert REFRESH.main() == 0


def test_a_standalone_discovery_refuses_while_a_chain_holds_the_lease_and_touches_nothing(world):
    from pipeline_lock import pipeline_run_lock
    world.install(collector=lambda out: pytest.fail("the collector must not start"))
    with pipeline_run_lock(REFRESH.PIPELINE_LOCK, owner_kind="congress_pipeline"):
        with pytest.raises(RuntimeError, match="already running"):
            REFRESH.main()
    assert not world.out.exists() and world.calls == []


def test_inside_the_pipeline_the_inherited_lease_is_used_not_a_second_one(world, monkeypatch):
    import os
    from pipeline_lock import pipeline_run_lock, child_lock_environment
    seen = {}

    def collector(out):
        seen["lease"] = _lock_payload(REFRESH.PIPELINE_LOCK)
        return complete(out, REFRESH.CONGRESS_SOURCE)

    world.install(collector=collector)
    with pipeline_run_lock(REFRESH.PIPELINE_LOCK, owner_kind="congress_pipeline") as lease:
        for key, value in child_lock_environment(lease).items():
            monkeypatch.setenv(key, value)
        assert REFRESH.main() == 0
        assert seen["lease"]["owner_kind"] == "congress_pipeline" and seen["lease"]["token"] == lease["token"]
        assert REFRESH.PIPELINE_LOCK.exists()   # the pipeline's lease is untouched


def test_collector_manifest_names_the_exact_primary_the_weekly_compares():
    """lane/gates-to-rulings 98e0e7318 weekly_refresh.py: DISCOVERY_PRIMARY='Congress.gov Advanced Search -
    Legislation', compared to manifest.json primary_instrument; anything else is DEGRADED, source named."""
    import re
    source = REFRESH.COLLECTOR.read_text(encoding="utf-8")
    constant = re.search(r'const PRIMARY_INSTRUMENT = "([^"]+)";', source).group(1)
    weekly = (Path(__file__).resolve().parents[2] / "weekly_refresh.py").read_text(encoding="utf-8")
    weekly_primary = re.search(r"^DISCOVERY_PRIMARY\s*=\s*'([^']+)'", weekly, re.M).group(1)   # read, not restated
    assert constant == REFRESH.CONGRESS_SOURCE == weekly_primary
    assert "primary_instrument: PRIMARY_INSTRUMENT," in source
    fallback = (REFRESH.GOVINFO_FALLBACK).read_text(encoding="utf-8")
    assert '"primary_instrument": "GovInfo BILLSTATUS/BILLS official bulk fallback"' in fallback
