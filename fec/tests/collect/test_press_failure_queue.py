"""D-294: one press site failing never fails the weekly; it is queued for Claude and counted.

Offline only: the R collector is never run here (the R side is pinned by
test_press_wordpress_custom_posts.R and test_press_official_dated_listings.R).  This file pins the
queue upsert, the per-run receipt, the stream wrapper hook and the weekly status accounting.
"""
from __future__ import annotations

import ast
import datetime
import json
import os
import sys
import time
from pathlib import Path

import pytest

FEC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FEC))
from collect import press_failure_queue as q  # noqa: E402
from collect import refresh_press_stream as stream  # noqa: E402

ROW = {"member_id": "O000174", "source": "official_wordpress_custom_post",
       "url": "https://www.ossoff.senate.gov/wp-json/wp/v2/types", "error_class": "http_403",
       "http_status": "403",
       "last_error": "official WordPress endpoint unavailable (403): https://www.ossoff.senate.gov/wp-json/wp/v2/types"}
NOW = datetime.datetime(2026, 10, 25, 12, 0, tzinfo=datetime.timezone.utc)


def rows(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_run(tmp_path, name, failures):
    run = tmp_path / "outputs" / name
    run.mkdir(parents=True)
    (run / "press_site_failures.json").write_text(
        json.dumps({"schema": "press-site-failures-v1", "failures": failures}), encoding="utf-8")
    return run


def test_first_failure_writes_one_open_row_with_the_full_schema(tmp_path):
    queue = tmp_path / "queue.ndjson"
    q.upsert([ROW], "press_refresh_20261025", NOW, queue)
    (row,) = rows(queue)
    assert row["status"] == "open" and row["consecutive_runs"] == 1
    assert row["first_seen"] == row["last_seen"] == NOW.isoformat()
    assert row["run_id"] == "press_refresh_20261025" and row["http_status"] == "403"
    assert (row["member_id"], row["url"], row["error_class"]) == (ROW["member_id"], ROW["url"], "http_403")
    assert len(row["last_error"]) <= 300


def test_second_run_upserts_the_same_key_to_consecutive_runs_2_and_keeps_first_seen(tmp_path):
    queue = tmp_path / "queue.ndjson"
    q.upsert([ROW], "press_refresh_20261018", NOW - datetime.timedelta(days=7), queue)
    q.upsert([ROW], "press_refresh_20261025", NOW, queue)
    (row,) = rows(queue)
    assert row["consecutive_runs"] == 2 and row["run_id"] == "press_refresh_20261025"
    assert row["first_seen"] == (NOW - datetime.timedelta(days=7)).isoformat()
    assert row["last_seen"] == NOW.isoformat()


def test_recording_the_same_run_twice_does_not_double_count(tmp_path):
    queue = tmp_path / "queue.ndjson"
    q.upsert([ROW], "press_refresh_20261025", NOW, queue)
    q.upsert([ROW], "press_refresh_20261025", NOW, queue)
    assert rows(queue)[0]["consecutive_runs"] == 1


def test_a_clean_reseal_of_the_same_run_recovers_the_failure_it_no_longer_has(tmp_path):
    # FIX77 (CodeRabbit PR #77): same run_id recorded with a failure, then resealed clean in that folder.
    queue = tmp_path / "queue.ndjson"
    q.upsert([ROW], "press_refresh_20261025", NOW, queue)
    q.upsert([], "press_refresh_20261025", NOW, queue)
    (row,) = rows(queue)
    assert row["status"] == "recovered" and row["consecutive_runs"] == 0
    q.upsert([ROW], "press_refresh_20261025", NOW, queue)     # a key still present keeps once-per-run counting
    q.upsert([ROW], "press_refresh_20261025", NOW, queue)
    assert rows(queue)[0]["status"] == "open" and rows(queue)[0]["consecutive_runs"] == 1


def test_a_different_error_class_is_a_different_key_and_history_is_never_dropped(tmp_path):
    queue = tmp_path / "queue.ndjson"
    q.upsert([ROW], "press_refresh_20261018", NOW, queue)
    q.upsert([dict(ROW, error_class="timeout", http_status=None)], "press_refresh_20261025", NOW, queue)
    got = rows(queue)
    assert len(got) == 2
    # the 403 row was not seen this run: recovered, history kept, no longer counted open
    old = next(r for r in got if r["error_class"] == "http_403")
    assert old["status"] == "recovered" and old["consecutive_runs"] == 0
    assert q.open_count(queue) == 1


def test_adjusted_rows_stay_in_the_file_and_reopen_if_the_site_fails_again(tmp_path):
    queue = tmp_path / "queue.ndjson"
    q.upsert([ROW], "press_refresh_20261018", NOW, queue)
    data = rows(queue)
    data[0].update(status="adjusted", note="moved to /news")
    queue.write_text("\n".join(json.dumps(r) for r in data) + "\n", encoding="utf-8")
    q.upsert([], "press_refresh_20261025", NOW, queue)         # clean run: adjusted row is untouched
    assert rows(queue)[0]["status"] == "adjusted" and q.open_count(queue) == 0
    q.upsert([ROW], "press_refresh_20261101", NOW, queue)
    (row,) = rows(queue)
    assert row["status"] == "open" and row["note"] == "moved to /news" and row["consecutive_runs"] == 1


def test_record_run_ingests_the_collector_file_and_writes_the_receipt(tmp_path):
    run = write_run(tmp_path, "press_refresh_20261025", [ROW])
    queue = tmp_path / "queue.ndjson"
    receipt = q.record_run(run, queue, now=NOW)
    assert receipt["status"] == "PARTIAL" and receipt["failures_this_run"] == 1
    assert receipt["press_failures_open"] == 1 and receipt["queue_path"] == str(queue)
    assert json.loads((run / "press_site_failure_receipt.json").read_text(encoding="utf-8")) == receipt
    # a second sealed run with the same failure -> consecutive_runs=2
    run2 = write_run(tmp_path, "press_refresh_20261101", [ROW])
    assert q.record_run(run2, queue, now=NOW)["press_failures_open"] == 1
    assert rows(queue)[0]["consecutive_runs"] == 2


def test_record_run_on_a_clean_run_is_not_partial(tmp_path):
    run = write_run(tmp_path, "press_refresh_20261025", [])
    receipt = q.record_run(run, tmp_path / "queue.ndjson", now=NOW)
    assert receipt["status"] == "CLEAN" and receipt["failures_this_run"] == 0


def test_a_run_without_the_collector_file_changes_nothing(tmp_path):
    run = tmp_path / "outputs" / "press_refresh_20261025"
    run.mkdir(parents=True)
    queue = tmp_path / "queue.ndjson"
    assert q.record_run(run, queue, now=NOW) is None
    assert not queue.exists()


def test_the_stream_hook_never_raises(tmp_path, capsys):
    run = tmp_path / "outputs" / "press_refresh_20261025"
    run.mkdir(parents=True)
    (run / "press_site_failures.json").write_text("{not json", encoding="utf-8")
    stream.record_site_failures(run)                            # corrupt input: logged, not raised
    assert "non-fatal" in capsys.readouterr().out


def test_the_stream_records_failures_after_a_sealed_walk_and_not_after_a_fatal_one():
    source = (FEC / "collect" / "refresh_press_stream.py").read_text(encoding="utf-8")
    block = source[source.index("code = run_collector"):source.index("if code:\n        return code")]
    assert "record_site_failures(run_root)" in block
    assert block.index("code in (0, 3)") < block.index("record_site_failures(run_root)")


def test_a_reused_same_day_run_retries_the_queue_update():
    # FIX77 (CodeRabbit PR #77): record_site_failures is idempotent, so the reuse path calls it too.
    source = (FEC / "collect" / "refresh_press_stream.py").read_text(encoding="utf-8")
    reuse = source[source.index("elif current_source_run(run_root, sources):"):source.index("script = Path(__file__)")]
    assert reuse.index("record_site_failures(run_root)") < reuse.index("return 0")


def weekly_function(name):
    source = (FEC / "weekly_refresh.py").read_text(encoding="utf-8")
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(source, node)


def weekly_namespace(tmp_path, started):
    logs, status, emits = [], {}, []
    ns = {"os": os, "json": json, "datetime": datetime, "MB_ROOT": str(tmp_path),
          "_started_at": started, "_RUN_LOG_DIR": str(tmp_path / "audits"),
          "_STATUS": status, "log": logs.append,
          "_write_status": lambda **kw: status.update(kw),
          "_emit": lambda *a, **kw: emits.append((a, kw)),
          }
    (tmp_path / "audits").mkdir()
    exec(weekly_function("_press_failure_status"), ns)
    return ns, logs, status, emits


TODAY_RUN = "press_refresh_" + datetime.date.today().strftime("%Y%m%d")


def test_weekly_records_press_partial_not_pass_and_counts_open_failures(tmp_path, monkeypatch):
    queue = tmp_path / "queue.ndjson"
    monkeypatch.setattr(q, "QUEUE_PATH", str(queue))
    started = datetime.datetime.now()
    run = write_run(tmp_path, TODAY_RUN, [ROW])
    q.record_run(run, queue, now=NOW)
    ns, logs, status, emits = weekly_namespace(tmp_path, started - datetime.timedelta(seconds=5))
    ns["_press_failure_status"]()
    assert status["press_status"] == "PARTIAL"
    assert status["press_failures_open"] == 1 and status["press_failure_queue"] == str(queue)
    assert any("PARTIAL" in line for line in logs) and emits[0][0][1] == "partial"
    assert (tmp_path / "audits" / "press_site_failure_receipt.json").is_file()


def test_weekly_reports_pass_only_for_a_clean_run_folder_and_unknown_without_one(tmp_path, monkeypatch):
    queue = tmp_path / "queue.ndjson"
    monkeypatch.setattr(q, "QUEUE_PATH", str(queue))
    ns, logs, status, emits = weekly_namespace(tmp_path, datetime.datetime.now())
    ns["_press_failure_status"]()
    assert status["press_status"] == "UNKNOWN" and status["press_failures_open"] == 0   # no run folder: not PASS
    write_run(tmp_path, TODAY_RUN, [])
    ns["_press_failure_status"]()
    assert status["press_status"] == "PASS"


def old_mtime(*paths):
    old = time.time() - 86400
    for path in paths:
        os.utime(str(path), (old, old))


def test_weekly_reads_the_receipts_of_a_reused_same_day_run_whatever_their_mtime(tmp_path, monkeypatch):
    # FIX77 (CodeRabbit PR #77): the reused run's files predate this weekly's start.
    queue = tmp_path / "queue.ndjson"
    monkeypatch.setattr(q, "QUEUE_PATH", str(queue))
    run = write_run(tmp_path, TODAY_RUN, [ROW])
    q.record_run(run, queue, now=NOW)
    old_mtime(*run.iterdir())
    ns, logs, status, emits = weekly_namespace(tmp_path, datetime.datetime.now())
    ns["_press_failure_status"]()
    assert status["press_status"] == "PARTIAL"
    assert (tmp_path / "audits" / "press_site_failure_receipt.json").is_file()
    # a reused run whose only PARTIAL signal is the sealed walk receipt (PS: skipped sites, or pending bodies)
    run2 = tmp_path / "outputs" / TODAY_RUN
    for name in ("press_site_failures.json", "press_site_failure_receipt.json"):
        (run2 / name).unlink()
    (run2 / "press_network_retry_receipt.json").write_text(json.dumps({"status": "PARTIAL"}), encoding="utf-8")
    old_mtime(run2 / "press_network_retry_receipt.json")
    ns["_press_failure_status"]()
    assert status["press_status"] == "PARTIAL"


def test_weekly_never_says_pass_when_the_queue_receipt_is_missing_over_a_nonempty_failures_file(tmp_path, monkeypatch):
    # FIX77 (CodeRabbit PR #77): record_site_failures() swallowed its error, so no receipt exists.
    monkeypatch.setattr(q, "QUEUE_PATH", str(tmp_path / "queue.ndjson"))
    write_run(tmp_path, TODAY_RUN, [ROW])
    ns, logs, status, emits = weekly_namespace(tmp_path, datetime.datetime.now())
    ns["_press_failure_status"]()
    assert status["press_status"] == "PARTIAL" and any("no queue receipt" in line for line in logs)
    (tmp_path / "outputs" / TODAY_RUN / "press_site_failures.json").write_text("{bad", encoding="utf-8")
    ns["_press_failure_status"]()
    assert status["press_status"] == "PARTIAL"       # unreadable artifact is unknown, never PASS


def test_weekly_ignores_run_folders_older_than_this_weekly(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "QUEUE_PATH", str(tmp_path / "queue.ndjson"))
    stale = "press_refresh_" + (datetime.date.today() - datetime.timedelta(days=9)).strftime("%Y%m%d")
    write_run(tmp_path, stale, [ROW])
    write_run(tmp_path, TODAY_RUN, [])
    ns, logs, status, emits = weekly_namespace(tmp_path, datetime.datetime.now())
    ns["_press_failure_status"]()
    assert status["press_status"] == "PASS"


def test_weekly_reports_partial_when_the_walk_receipt_is_partial_even_with_no_site_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(q, "QUEUE_PATH", str(tmp_path / "queue.ndjson"))
    run = tmp_path / "outputs" / TODAY_RUN
    run.mkdir(parents=True)
    (run / "press_network_retry_receipt.json").write_text(json.dumps({"status": "PARTIAL"}), encoding="utf-8")
    ns, logs, status, emits = weekly_namespace(tmp_path, datetime.datetime.now() - datetime.timedelta(seconds=5))
    ns["_press_failure_status"]()
    assert status["press_status"] == "PARTIAL" and status["press_failures_open"] == 0


def test_the_weekly_calls_the_status_hook_right_after_the_press_step_and_adds_no_step():
    tree = ast.parse((FEC / "weekly_refresh.py").read_text(encoding="utf-8"))
    names = [n.value.func.id for n in tree.body
             if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)]
    steps = [n.value.args[0].value for n in tree.body
             if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name)
             and n.value.func.id == "step" and n.value.args and isinstance(n.value.args[0], ast.Constant)]
    at = names.index("_press_failure_status")
    assert steps[steps.index("press delta refresh") + 1] == "press intake audit"
    assert names[at - 1] == "step" and names[at + 1] == "step"


def test_the_collector_wrapper_writes_the_failure_file_then_fails_only_when_every_member_failed():
    text = (FEC / "collect" / "refresh_press_delta.R").read_text(encoding="utf-8")
    main = text[text.index("exit_code <- tryCatch({"):]
    order = [main.index(token) for token in (
        "stage_index(members, discovery, FALSE)", "press_site_failures_snapshot()",
        "press_site_failures.json", "press_site_all_failed(site_failures, members$bioguide)",
        'stop("every member failed', "read.csv(")]
    assert order == sorted(order)
    assert "PRESS REFRESH FAILED" in main and main.rstrip().endswith("quit(save = \"no\", status = exit_code)")


def test_weekly_still_writes_press_status_when_a_receipt_is_unreadable(tmp_path, monkeypatch):
    # FIX77b (CodeRabbit PR #77): a corrupt queue or walk receipt must not skip _write_status().
    queue = tmp_path / "queue.ndjson"
    monkeypatch.setattr(q, "QUEUE_PATH", str(queue))
    run = write_run(tmp_path, TODAY_RUN, [ROW])
    q.record_run(run, queue, now=NOW)
    (run / q.RECEIPT_ARTIFACT).write_text("{bad", encoding="utf-8")
    ns, logs, status, emits = weekly_namespace(tmp_path, datetime.datetime.now())
    ns["_press_failure_status"]()
    assert status["press_status"] == "PARTIAL"            # the collector artifact still records the skip
    assert status["press_failures_open"] == 1 and status["press_failure_queue"] == str(queue)
    assert any("unreadable" in line for line in logs)
    # clean failures artifact but a corrupt walk receipt: status cannot be established, never PASS
    (run / q.FAILURES_ARTIFACT).write_text(json.dumps({"schema": q.FAILURES_SCHEMA, "failures": []}), encoding="utf-8")
    (run / q.RECEIPT_ARTIFACT).unlink()
    (run / "press_network_retry_receipt.json").write_text("not json", encoding="utf-8")
    status.clear()
    ns["_press_failure_status"]()
    assert status["press_status"] == "UNKNOWN" and "press_failures_open" in status
    # a receipt that parses but is not an object, or lacks the field the status reads, is treated the same way
    for wrong in ("[]", "{}", '{"status": null}', '{"status": "DONE"}'):
        (run / "press_network_retry_receipt.json").write_text(wrong, encoding="utf-8")
        status.clear()
        ns["_press_failure_status"]()
        assert status["press_status"] == "UNKNOWN", wrong
    # a failures artifact without a "failures" list is never PASS
    (run / "press_network_retry_receipt.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")
    for wrong in ("{}", '{"failures": null}', '{"failures": "x"}'):
        (run / q.FAILURES_ARTIFACT).write_text(wrong, encoding="utf-8")
        status.clear()
        ns["_press_failure_status"]()
        assert status["press_status"] != "PASS", wrong
    # and a well-formed clean run is still PASS
    (run / q.FAILURES_ARTIFACT).write_text(json.dumps({"schema": q.FAILURES_SCHEMA, "failures": []}), encoding="utf-8")
    status.clear()
    ns["_press_failure_status"]()
    assert status["press_status"] == "PASS"
