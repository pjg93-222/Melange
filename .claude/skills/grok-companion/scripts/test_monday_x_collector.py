from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import monday_x_collector as collector


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, ensure_ascii=False)
        output.write("\n")


def read_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as source:
        return json.load(source)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise AssertionError("test catalog line was not an object")
                records.append(value)
    return records


def collection_args(
    root: Path,
    handles_path: Path,
    *,
    handles_limit: int | None = None,
    max_pages: int | None = None,
) -> argparse.Namespace:
    argv = [
        "--force",
        "--since",
        "2026-07-01",
        "--handles-file",
        str(handles_path),
        "--catalog",
        str(root / "catalog.jsonl"),
        "--state-dir",
        str(root / "state"),
    ]
    if handles_limit is not None:
        argv.extend(["--handles-limit", str(handles_limit)])
    if max_pages is not None:
        argv.extend(["--max-pages", str(max_pages)])
    return collector.build_parser().parse_args(argv)


class HandleExtractionTests(unittest.TestCase):
    def test_extracts_handles_and_counts_missing_entries(self) -> None:
        entries = [
            {
                "social": {"twitter": "alpha"},
                "id": {"bioguide": "A000001"},
            },
            {"social": {}, "id": {"bioguide": "A000002"}},
            {"social": {"twitter": "   "}, "id": {"bioguide": "A000003"}},
            {"social": {"twitter": " beta "}, "id": {}},
            "not an object",
        ]
        with tempfile.TemporaryDirectory() as temp_name:
            handles_path = Path(temp_name) / "handles.json"
            write_json(handles_path, entries)

            handles, skipped = collector.load_handles(handles_path)
            limited, limited_skipped = collector.load_handles(
                handles_path,
                limit=1,
            )

        self.assertEqual(
            handles,
            [
                collector.HandleRef("alpha", "A000001"),
                collector.HandleRef("beta", None),
            ],
        )
        self.assertEqual(skipped, 3)
        self.assertEqual(limited, [collector.HandleRef("alpha", "A000001")])
        self.assertEqual(limited_skipped, 3)

    def test_rejects_non_list_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            handles_path = Path(temp_name) / "handles.json"
            write_json(handles_path, {"social": {"twitter": "alpha"}})
            with self.assertRaises(collector.CollectorError):
                collector.load_handles(handles_path)

    def test_accepts_utf8_bom_input(self) -> None:
        entries = [
            {
                "social": {"twitter": "alpha"},
                "id": {"bioguide": "A000001"},
            }
        ]
        with tempfile.TemporaryDirectory() as temp_name:
            handles_path = Path(temp_name) / "handles.json"
            handles_path.write_bytes(
                b"\xef\xbb\xbf"
                + json.dumps(entries, ensure_ascii=False).encode("utf-8")
            )

            handles, skipped = collector.load_handles(handles_path)

        self.assertEqual(
            handles,
            [collector.HandleRef("alpha", "A000001")],
        )
        self.assertEqual(skipped, 0)


class BatchConstructionTests(unittest.TestCase):
    def test_c2_batches_use_at_most_five_handles_under_cap(self) -> None:
        handles = [
            collector.HandleRef(f"h{number}", None)
            for number in range(12)
        ]
        since = date(2026, 7, 1)
        until = date(2026, 7, 24)

        batches = collector.build_batches(handles, since, until)

        self.assertEqual(
            [len(batch.handles) for batch in batches],
            [5, 5, 2],
        )
        flattened: list[collector.HandleRef] = []
        for batch in batches:
            self.assertLessEqual(len(batch.handles), 5)
            self.assertLess(len(batch.query), 480)
            expected = (
                "("
                + " OR ".join(
                    f"from:{item.handle}" for item in batch.handles
                )
                + ") since:2026-07-01 until:2026-07-24"
            )
            self.assertEqual(batch.query, expected)
            self.assertNotIn("OR OR", batch.query)
            flattened.extend(batch.handles)
        self.assertEqual(flattened, handles)

    def test_c2_prompt_requires_exact_query_pagination_and_all_results(self) -> None:
        query = "(from:alpha) since:2026-07-01 until:2026-07-24"

        prompt = collector.build_prompt(query)

        self.assertEqual(prompt.count(query), 1)
        self.assertIn("Do not alter the query or drop any handle", prompt)
        self.assertIn("until the query window is exhausted or 10", prompt)
        self.assertIn("Aggregate ALL results", prompt)
        self.assertIn("ONLY the single JSON array", prompt)

    def test_cb2_max_pages_propagates_to_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            write_json(
                handles_path,
                [{"social": {"twitter": "alpha"}, "id": {}}],
            )
            prompts: list[str] = []

            def prompt_capturing_runner(
                _command: object,
                prompt: str,
                _state_dir: Path,
            ) -> str:
                prompts.append(prompt)
                return "[]"

            return_code = collector.run_collection(
                collection_args(
                    root,
                    handles_path,
                    max_pages=1,
                ),
                runner=prompt_capturing_runner,
                sleep_fn=lambda _seconds: None,
            )

        self.assertEqual(return_code, 0)
        self.assertEqual(len(prompts), 1)
        self.assertIn(
            "until the query window is exhausted or 1 calls have been made",
            prompts[0],
        )

    def test_saved_query_recovers_exact_handles(self) -> None:
        query = (
            "(from:Alpha OR from:beta) "
            "since:2026-07-01 until:2026-07-24"
        )
        self.assertEqual(
            collector.parse_query_handles(query),
            ("Alpha", "beta"),
        )

    def test_exact_duplicate_queries_preserve_first_occurrence(self) -> None:
        first = collector.Batch(
            "(from:alpha) since:2026-07-01 until:2026-07-24",
            (collector.HandleRef("alpha", "A000001"),),
        )
        duplicate = collector.Batch(
            first.query,
            (collector.HandleRef("alpha", None),),
        )
        second = collector.Batch(
            "(from:beta) since:2026-07-01 until:2026-07-24",
            (collector.HandleRef("beta", "B000001"),),
        )

        unique = collector.dedupe_batches([first, duplicate, second])

        self.assertEqual(unique, [first, second])


class GateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 7, 24, 15, 0, tzinfo=timezone.utc)
        self.recent = collector.iso_utc(self.now - timedelta(days=1))

    def test_monday_runs_with_recent_success(self) -> None:
        self.assertTrue(
            collector.should_run(
                today=date(2026, 7, 20),
                now_utc=self.now,
                last_success_utc=self.recent,
                force=False,
            )
        )

    def test_non_monday_with_recent_success_skips(self) -> None:
        self.assertFalse(
            collector.should_run(
                today=date(2026, 7, 24),
                now_utc=self.now,
                last_success_utc=self.recent,
                force=False,
            )
        )

    def test_stale_success_runs_but_exactly_seven_days_does_not(self) -> None:
        stale = collector.iso_utc(self.now - timedelta(days=8))
        exact = collector.iso_utc(self.now - timedelta(days=7))
        self.assertTrue(
            collector.should_run(
                today=date(2026, 7, 24),
                now_utc=self.now,
                last_success_utc=stale,
                force=False,
            )
        )
        self.assertFalse(
            collector.should_run(
                today=date(2026, 7, 24),
                now_utc=self.now,
                last_success_utc=exact,
                force=False,
            )
        )

    def test_force_and_absent_success_each_run(self) -> None:
        self.assertTrue(
            collector.should_run(
                today=date(2026, 7, 24),
                now_utc=self.now,
                last_success_utc=self.recent,
                force=True,
            )
        )
        self.assertTrue(
            collector.should_run(
                today=date(2026, 7, 24),
                now_utc=self.now,
                last_success_utc=None,
                force=False,
            )
        )

    def test_window_overlap_override_and_first_run_default(self) -> None:
        today = date(2026, 7, 24)
        last_success = "2026-07-20T18:30:00Z"
        self.assertEqual(
            collector.compute_window(
                today=today,
                last_success_utc=last_success,
                since_override=None,
            ),
            (date(2026, 7, 19), today),
        )
        self.assertEqual(
            collector.compute_window(
                today=today,
                last_success_utc=last_success,
                since_override=date(2026, 7, 3),
            ),
            (date(2026, 7, 3), today),
        )
        self.assertEqual(
            collector.compute_window(
                today=today,
                last_success_utc=None,
                since_override=None,
            ),
            (date(2026, 7, 16), today),
        )


class ResponseParsingTests(unittest.TestCase):
    def setUp(self) -> None:
        handle = collector.HandleRef("Alpha", "A000001")
        self.batch = collector.Batch(
            "(from:Alpha) since:2026-07-01 until:2026-07-24",
            (handle,),
        )
        self.payload = [
            {
                "handle": "aLPHa",
                "utc_date": "2026-07-23T10:00:00Z",
                "text": "A post",
                "url": "https://x.com/Alpha/status/1",
            }
        ]

    def test_accepts_raw_and_whole_json_fence(self) -> None:
        raw = json.dumps(self.payload)
        fenced = f"```json\n{raw}\n```"

        raw_posts = collector.parse_posts(raw, self.batch)
        fenced_posts = collector.parse_posts(fenced, self.batch)

        self.assertEqual(raw_posts, fenced_posts)
        self.assertEqual(raw_posts[0]["handle"], "Alpha")
        self.assertEqual(raw_posts[0]["bioguide"], "A000001")

    def test_c1_accepts_prose_wrapped_single_array(self) -> None:
        payload = [dict(self.payload[0], text="A [bracketed] post")]
        response = (
            "Here are the results:\n```json\n"
            + json.dumps(payload)
            + "\n```\nSearch complete."
        )

        posts = collector.parse_posts(response, self.batch)

        self.assertEqual(posts[0]["text"], "A [bracketed] post")

    def test_c1_rejects_two_parseable_arrays(self) -> None:
        response = (
            json.dumps(self.payload)
            + "\nSome prose\n"
            + json.dumps(self.payload)
        )
        with self.assertRaisesRegex(
            collector.BatchError,
            "Grok response was not one JSON array",
        ):
            collector.parse_posts(response, self.batch)

    def test_c1_rejects_prose_only(self) -> None:
        with self.assertRaisesRegex(
            collector.BatchError,
            "Grok response was not one JSON array",
        ):
            collector.parse_posts("No posts were found.", self.batch)

    def test_d1_rejects_object_wrapped_array(self) -> None:
        response = json.dumps({"results": self.payload})

        with self.assertRaisesRegex(
            collector.BatchError,
            "Grok response was not one JSON array",
        ):
            collector.parse_posts(response, self.batch)

    def test_d1_accepts_valid_array_after_unmatched_stray_bracket(self) -> None:
        response = "Unmatched sample [ then results:\n" + json.dumps(self.payload)

        posts = collector.parse_posts(response, self.batch)

        self.assertEqual(posts[0]["handle"], "Alpha")

    def test_d1_rejects_bracketed_sample_alongside_real_array(self) -> None:
        response = "For example [1], then results:\n" + json.dumps(self.payload)

        with self.assertRaisesRegex(
            collector.BatchError,
            "Grok response was not one JSON array",
        ):
            collector.parse_posts(response, self.batch)

    def test_c9_rejects_utc_date_without_date_prefix(self) -> None:
        payload = [dict(self.payload[0], utc_date="T10:00:00Z")]

        with self.assertRaisesRegex(
            collector.BatchError,
            "valid string utc_date",
        ):
            collector.parse_posts(json.dumps(payload), self.batch)

    def test_strictly_rejects_invalid_elements_and_fields(self) -> None:
        invalid_payloads = [
            {"not": "an array"},
            ["not an object"],
            [
                {
                    "handle": "other",
                    "utc_date": "2026-07-23",
                    "text": "post",
                    "url": None,
                }
            ],
            [
                {
                    "handle": " ",
                    "utc_date": "2026-07-23",
                    "text": "post",
                    "url": None,
                }
            ],
            [
                {
                    "handle": " Alpha",
                    "utc_date": "2026-07-23",
                    "text": "post",
                    "url": None,
                }
            ],
            [
                {
                    "handle": "Alpha",
                    "utc_date": "2026-07-23",
                    "text": " ",
                    "url": None,
                }
            ],
            [
                {
                    "handle": "Alpha",
                    "utc_date": None,
                    "text": "post",
                    "url": None,
                }
            ],
            [
                {
                    "handle": "Alpha",
                    "utc_date": "2026-07-23",
                    "text": "post",
                    "url": 3,
                }
            ],
            [
                {
                    "handle": "Alpha",
                    "utc_date": "2026-07-23",
                    "text": "post",
                }
            ],
            [
                {
                    "handle": "Alpha",
                    "utc_date": "2026-07-23",
                    "text": "post",
                    "url": None,
                    "extra": "not allowed",
                }
            ],
        ]
        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(collector.BatchError):
                    collector.parse_posts(json.dumps(payload), self.batch)


class DedupeTests(unittest.TestCase):
    def test_url_dedupe_wins_over_other_field_differences(self) -> None:
        posts = [
            {
                "handle": "alpha",
                "bioguide": "A000001",
                "utc_date": "2026-07-20",
                "text": "first",
                "url": "https://x.com/status/1",
            },
            {
                "handle": "beta",
                "bioguide": "B000001",
                "utc_date": "2026-07-21",
                "text": "different",
                "url": "https://x.com/status/1",
            },
        ]
        records = collector.new_catalog_records(
            posts,
            set(),
            collected_at="2026-07-24T12:00:00Z",
        )
        self.assertEqual(len(records), 1)

    def test_fallback_hash_uses_exact_concatenation(self) -> None:
        post = {
            "handle": "alpha",
            "bioguide": "A000001",
            "utc_date": "2026-07-20",
            "text": "post",
            "url": None,
        }
        records = collector.new_catalog_records(
            [post, dict(post)],
            set(),
            collected_at="2026-07-24T12:00:00Z",
        )
        expected = hashlib.sha256(
            "alpha2026-07-20post".encode("utf-8")
        ).hexdigest()
        self.assertEqual(len(records), 1)
        self.assertEqual(
            collector.catalog_key(
                handle="alpha",
                utc_date="2026-07-20",
                text="post",
                url=None,
            ),
            f"sha256:{expected}",
        )


class StateTests(unittest.TestCase):
    def test_state_round_trip_and_failed_query_carryover(self) -> None:
        query = (
            "(from:alpha OR from:beta) "
            "since:2026-07-01 until:2026-07-24"
        )
        state = {
            "batch_format_version": 2,
            "last_success_utc": "2026-07-20T12:00:00Z",
            "failed_batches": [query],
        }
        handles = [
            collector.HandleRef("alpha", "A000001"),
            collector.HandleRef("beta", "B000001"),
        ]
        with tempfile.TemporaryDirectory() as temp_name:
            state_path = Path(temp_name) / "state.json"
            collector.write_state_atomic(state_path, state)

            loaded = collector.load_state(state_path)
            restored = collector.batches_from_failed_queries(
                loaded["failed_batches"],
                collector.index_handles(handles),
            )
            raw = state_path.read_bytes()

        self.assertEqual(loaded, state)
        self.assertEqual([item.query for item in restored], [query])
        self.assertEqual(list(restored[0].handles), handles)
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))


class SuccessOrderingTests(unittest.TestCase):
    def test_success_log_failure_does_not_advance_last_success(self) -> None:
        old_success = "2026-07-20T12:00:00Z"
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            state_dir = root / "state"
            state_path = state_dir / "state.json"
            marker_path = state_dir / "FAILED.marker"
            write_json(handles_path, [])
            collector.write_state_atomic(
                state_path,
                {
                    "batch_format_version": 2,
                    "last_success_utc": old_success,
                    "failed_batches": [],
                },
            )
            marker_path.write_text(
                "stale\n",
                encoding="utf-8",
                newline="\n",
            )
            args = collector.build_parser().parse_args(
                [
                    "--force",
                    "--since",
                    "2026-07-01",
                    "--handles-file",
                    str(handles_path),
                    "--catalog",
                    str(root / "catalog.jsonl"),
                    "--state-dir",
                    str(state_dir),
                ]
            )
            real_append_log = collector.append_log

            def fail_on_success(path: Path, message: str) -> None:
                if message.startswith("run=success"):
                    raise OSError("simulated success log failure")
                real_append_log(path, message)

            with mock.patch.object(
                collector,
                "append_log",
                side_effect=fail_on_success,
            ):
                with self.assertRaises(OSError):
                    collector.run_collection(args)

            state = collector.load_state(state_path)
            marker_exists = marker_path.exists()

        self.assertEqual(state["last_success_utc"], old_success)
        self.assertFalse(marker_exists)


class LockTests(unittest.TestCase):
    def test_c9_lock_write_failure_removes_just_created_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            lock_path = Path(temp_name) / "collector.lock"

            with mock.patch.object(
                collector.os,
                "fsync",
                side_effect=OSError("simulated fsync failure"),
            ):
                with self.assertRaises(OSError):
                    collector._create_collector_lock(lock_path)

            lock_exists = lock_path.exists()

        self.assertFalse(lock_exists)

    def test_c9_handles_limit_help_documents_carried_batches(self) -> None:
        parser = collector.build_parser()
        limit_action = next(
            action
            for action in parser._actions
            if action.dest == "handles_limit"
        )

        self.assertIn(
            "carried failed batches are not limited",
            limit_action.help,
        )

    @unittest.skipUnless(os.name == "nt", "collector lock targets Windows")
    def test_live_pid_lock_exits_three_without_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            state_dir = root / "state"
            state_dir.mkdir()
            lock_path = state_dir / "collector.lock"
            lock_path.write_text(
                f"{os.getpid()}\n",
                encoding="ascii",
                newline="\n",
            )

            return_code = collector.main(
                [
                    "--force",
                    "--handles-file",
                    str(root / "unused.json"),
                    "--catalog",
                    str(root / "catalog.jsonl"),
                    "--state-dir",
                    str(state_dir),
                ]
            )
            log_text = (state_dir / "collector.log").read_text(
                encoding="utf-8"
            )
            lock_exists = lock_path.exists()
            marker_exists = (state_dir / "FAILED.marker").exists()

        self.assertEqual(return_code, 3)
        self.assertIn("run=locked exit=3", log_text)
        self.assertTrue(lock_exists)
        self.assertFalse(marker_exists)

    def test_empty_lock_is_treated_as_active(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            state_dir = root / "state"
            state_dir.mkdir()
            lock_path = state_dir / "collector.lock"
            lock_path.write_text("", encoding="ascii", newline="\n")

            return_code = collector.main(
                [
                    "--force",
                    "--handles-file",
                    str(root / "unused.json"),
                    "--catalog",
                    str(root / "catalog.jsonl"),
                    "--state-dir",
                    str(state_dir),
                ]
            )
            marker_exists = (state_dir / "FAILED.marker").exists()

        self.assertEqual(return_code, 3)
        self.assertFalse(marker_exists)

    def test_stale_lock_is_replaced_and_removed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            state_dir = root / "state"
            state_dir.mkdir()
            handles_path = root / "handles.json"
            write_json(handles_path, [])
            lock_path = state_dir / "collector.lock"
            lock_path.write_text(
                "99999999\n",
                encoding="ascii",
                newline="\n",
            )

            with mock.patch.object(
                collector,
                "pid_is_alive",
                return_value=False,
            ):
                return_code = collector.main(
                    [
                        "--force",
                        "--since",
                        "2026-07-01",
                        "--handles-file",
                        str(handles_path),
                        "--catalog",
                        str(root / "catalog.jsonl"),
                        "--state-dir",
                        str(state_dir),
                    ]
                )
            lock_exists = lock_path.exists()

        self.assertEqual(return_code, 0)
        self.assertFalse(lock_exists)


class ProcessDecodeTests(unittest.TestCase):
    def test_c8_invalid_utf8_stdout_has_its_own_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            runner_path = root / "invalid_utf8.py"
            runner_path.write_text(
                (
                    "import sys\n"
                    "sys.stdout.buffer.write(b'\\xff')\n"
                ),
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaises(collector.BatchError) as raised:
                collector.run_prompt_process(
                    [sys.executable, str(runner_path)],
                    "prompt",
                    root,
                )
            prompt_files = list(root.glob("monday-x-prompt-*.txt"))

        self.assertEqual(
            str(raised.exception),
            "Grok stdout was not valid UTF-8",
        )
        self.assertEqual(prompt_files, [])

    def test_c8_nonzero_exit_includes_decoded_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            runner_path = root / "nonzero.py"
            runner_path.write_text(
                (
                    "import sys\n"
                    "sys.stderr.write('specific stderr')\n"
                    "raise SystemExit(7)\n"
                ),
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaises(collector.BatchError) as raised:
                collector.run_prompt_process(
                    [sys.executable, str(runner_path)],
                    "prompt",
                    root,
                )

        self.assertEqual(
            str(raised.exception),
            "Grok command exited with code 7: specific stderr",
        )

    def test_c4_timeout_becomes_batch_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            runner_path = root / "sleeping.py"
            runner_path.write_text(
                "import time\ntime.sleep(1)\n",
                encoding="utf-8",
                newline="\n",
            )

            with self.assertRaises(collector.BatchError) as raised:
                collector.run_prompt_process(
                    [sys.executable, str(runner_path)],
                    "prompt",
                    root,
                    timeout_seconds=0.01,
                )
            prompt_files = list(root.glob("monday-x-prompt-*.txt"))

        self.assertEqual(
            str(raised.exception),
            "Grok dispatch timed out after 0.01s",
        )
        self.assertEqual(prompt_files, [])


class OverrideGuardTests(unittest.TestCase):
    def test_empty_or_whitespace_command_override_is_fatal(self) -> None:
        for override in ("", "   "):
            with self.subTest(override=override):
                with tempfile.TemporaryDirectory() as temp_name:
                    root = Path(temp_name)
                    handles_path = root / "handles.json"
                    state_dir = root / "state"
                    write_json(handles_path, [])

                    return_code = collector.main(
                        [
                            "--force",
                            "--since",
                            "2026-07-01",
                            "--handles-file",
                            str(handles_path),
                            "--catalog",
                            str(root / "catalog.jsonl"),
                            "--state-dir",
                            str(state_dir),
                            "--grok-command-json",
                            override,
                        ]
                    )
                    marker_text = (
                        state_dir / "FAILED.marker"
                    ).read_text(encoding="utf-8")
                    lock_exists = (
                        state_dir / "collector.lock"
                    ).exists()

                self.assertEqual(return_code, 1)
                self.assertIn("JSON array of argv strings", marker_text)
                self.assertFalse(lock_exists)


class RetrySplitTests(unittest.TestCase):
    def test_c3_second_failure_splits_to_single_handle_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            write_json(
                handles_path,
                [
                    {
                        "social": {"twitter": handle},
                        "id": {"bioguide": f"{handle[0].upper()}000001"},
                    }
                    for handle in ("alpha", "beta", "gamma")
                ],
            )
            args = collection_args(root, handles_path)
            calls: list[str] = []

            def scripted_runner(
                _command: object,
                prompt: str,
                _state_dir: Path,
            ) -> str:
                calls.append(prompt)
                if len(calls) <= 2:
                    raise collector.BatchError("scripted batch failure")
                handle = ("alpha", "beta", "gamma")[len(calls) - 3]
                return json.dumps(
                    [
                        {
                            "handle": handle,
                            "utc_date": "2026-07-23T10:00:00Z",
                            "text": f"{handle} post",
                            "url": f"https://x.example/{handle}",
                        }
                    ]
                )

            sleep = mock.Mock()
            return_code = collector.run_collection(
                args,
                runner=scripted_runner,
                sleep_fn=sleep,
            )
            state = read_json(root / "state" / "state.json")
            records = read_jsonl(root / "catalog.jsonl")
            log_text = (root / "state" / "collector.log").read_text(
                encoding="utf-8"
            )

        self.assertEqual(return_code, 0)
        self.assertEqual(len(calls), 5)
        self.assertEqual(sleep.call_count, 4)
        self.assertEqual(
            {record["handle"] for record in records},
            {"alpha", "beta", "gamma"},
        )
        self.assertIsInstance(state, dict)
        self.assertEqual(state["failed_batches"], [])
        self.assertIn("batch=split", log_text)

    def test_d3_overlapping_carried_single_is_deduped_and_reconciled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            state_path = root / "state" / "state.json"
            alpha = collector.HandleRef("alpha", "A000001")
            beta = collector.HandleRef("beta", "B000001")
            handles = [alpha, beta]
            write_json(
                handles_path,
                [
                    {
                        "social": {"twitter": item.handle},
                        "id": {"bioguide": item.bioguide},
                    }
                    for item in handles
                ],
            )
            until = datetime.now().astimezone().date()
            query_a = collector.make_query(
                [alpha],
                date(2026, 7, 1),
                until,
            )
            query_ab = collector.make_query(
                handles,
                date(2026, 7, 1),
                until,
            )
            query_b = collector.make_query(
                [beta],
                date(2026, 7, 1),
                until,
            )
            collector.write_state_atomic(
                state_path,
                {
                    "batch_format_version": 2,
                    "last_success_utc": None,
                    "failed_batches": [query_a],
                },
            )
            calls: list[str] = []
            query_counts: dict[str, int] = {}

            def overlapping_runner(
                _command: object,
                prompt: str,
                _state_dir: Path,
            ) -> str:
                query = prompt.splitlines()[1]
                calls.append(query)
                query_counts[query] = query_counts.get(query, 0) + 1
                if query == query_a:
                    if query_counts[query] == 1:
                        raise collector.BatchError("first qA failure")
                    return "[]"
                if query == query_ab:
                    raise collector.BatchError("qAB failure")
                if query == query_b:
                    return "[]"
                raise AssertionError(f"unexpected query: {query}")

            return_code = collector.run_collection(
                collection_args(root, handles_path),
                runner=overlapping_runner,
                sleep_fn=lambda _seconds: None,
            )
            state = read_json(state_path)

        self.assertEqual(return_code, 0)
        self.assertEqual(calls.count(query_a), 2)
        self.assertEqual(calls.count(query_ab), 2)
        self.assertEqual(calls.count(query_b), 1)
        self.assertIsInstance(state, dict)
        self.assertNotIn(query_a, state["failed_batches"])
        self.assertEqual(state["failed_batches"], [])


class QuotaCircuitBreakerTests(unittest.TestCase):
    def test_cb1_trips_after_two_quota_dispatches_and_finishes_partial(
        self,
    ) -> None:
        old_success = "2026-07-20T12:00:00Z"
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            state_dir = root / "state"
            state_path = state_dir / "state.json"
            handles = [
                collector.HandleRef(f"h{number}", f"B{number:06d}")
                for number in range(16)
            ]
            write_json(
                handles_path,
                [
                    {
                        "social": {"twitter": item.handle},
                        "id": {"bioguide": item.bioguide},
                    }
                    for item in handles
                ],
            )
            collector.write_state_atomic(
                state_path,
                {
                    "batch_format_version": 2,
                    "last_success_utc": old_success,
                    "failed_batches": [],
                },
            )
            expected_until = datetime.now().astimezone().date()
            expected_queries = [
                batch.query
                for batch in collector.build_batches(
                    handles,
                    date(2026, 7, 1),
                    expected_until,
                )
            ]
            calls: list[str] = []
            quota_calls: list[str] = []

            def quota_runner(
                _command: object,
                prompt: str,
                _state_dir: Path,
            ) -> str:
                quota_calls.append(prompt.splitlines()[1])
                raise collector.BatchError(
                    "Grok dispatch failed",
                    stderr=(
                        b"HTTP 402: Grok Build usage balance exhausted"
                    ),
                )

            def successful_then_quota_runner(
                command: object,
                prompt: str,
                runner_state_dir: Path,
            ) -> str:
                query = prompt.splitlines()[1]
                calls.append(query)
                if len(calls) == 1:
                    return json.dumps(
                        [
                            {
                                "handle": handles[0].handle,
                                "utc_date": "2026-07-23T10:00:00Z",
                                "text": "successful post",
                                "url": "https://x.example/success",
                            }
                        ]
                    )
                return quota_runner(command, prompt, runner_state_dir)

            return_code = collector.run_collection(
                collection_args(root, handles_path),
                runner=successful_then_quota_runner,
                sleep_fn=lambda _seconds: None,
            )
            state = read_json(state_path)
            records = read_jsonl(root / "catalog.jsonl")
            partial_text = (state_dir / "PARTIAL.marker").read_text(
                encoding="utf-8"
            )
            log_text = (state_dir / "collector.log").read_text(
                encoding="utf-8"
            )

        self.assertEqual(return_code, 2)
        self.assertEqual(len(quota_calls), 2)
        self.assertEqual(calls, expected_queries[:3])
        self.assertIsInstance(state, dict)
        self.assertEqual(state["last_success_utc"], old_success)
        self.assertEqual(state["failed_batches"], expected_queries[1:])
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["url"], "https://x.example/success")
        self.assertEqual(
            partial_text,
            (
                "appended=1\n"
                f"failed_batches={len(expected_queries) - 1}\n"
                f"first_failed_query={expected_queries[1]}\n"
            ),
        )
        self.assertNotIn("batch=retry", log_text)
        self.assertNotIn("batch=split", log_text)
        self.assertIn(
            "quota circuit breaker tripped after 3 dispatches\n",
            log_text,
        )

    def test_cb1_nonquota_failure_resets_streak_before_adjacent_trip(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            handles = [
                collector.HandleRef(f"h{number}", None)
                for number in range(21)
            ]
            write_json(
                handles_path,
                [
                    {"social": {"twitter": item.handle}, "id": {}}
                    for item in handles
                ],
            )
            expected_until = datetime.now().astimezone().date()
            expected_queries = [
                batch.query
                for batch in collector.build_batches(
                    handles,
                    date(2026, 7, 1),
                    expected_until,
                )
            ]
            calls: list[str] = []

            def mixed_failure_runner(
                _command: object,
                prompt: str,
                _state_dir: Path,
            ) -> str:
                calls.append(prompt.splitlines()[1])
                if len(calls) == 2:
                    raise collector.BatchError("ordinary batch failure")
                raise collector.BatchError(
                    "quota failure",
                    stderr=b"Payment Required",
                )

            return_code = collector.run_collection(
                collection_args(root, handles_path),
                runner=mixed_failure_runner,
                sleep_fn=lambda _seconds: None,
            )
            state = read_json(root / "state" / "state.json")
            log_text = (root / "state" / "collector.log").read_text(
                encoding="utf-8"
            )

        self.assertEqual(return_code, 2)
        self.assertEqual(calls, expected_queries[:4])
        self.assertIsInstance(state, dict)
        self.assertEqual(
            state["failed_batches"],
            [
                expected_queries[0],
                expected_queries[2],
                expected_queries[3],
                expected_queries[4],
                expected_queries[1],
            ],
        )
        self.assertIn(
            "quota circuit breaker tripped after 4 dispatches\n",
            log_text,
        )

    def test_cb1_success_post_quota_terms_are_not_classified(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            write_json(
                handles_path,
                [{"social": {"twitter": "alpha"}, "id": {}}],
            )

            def successful_runner(
                _command: object,
                _prompt: str,
                _state_dir: Path,
            ) -> str:
                return json.dumps(
                    [
                        {
                            "handle": "alpha",
                            "utc_date": "2026-07-23T10:00:00Z",
                            "text": "HTTP 402 payment required",
                            "url": "https://x.example/quota-terms",
                        }
                    ]
                )

            return_code = collector.run_collection(
                collection_args(root, handles_path),
                runner=successful_runner,
                sleep_fn=lambda _seconds: None,
            )
            records = read_jsonl(root / "catalog.jsonl")
            state = read_json(root / "state" / "state.json")
            log_text = (root / "state" / "collector.log").read_text(
                encoding="utf-8"
            )

        self.assertEqual(return_code, 0)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["text"], "HTTP 402 payment required")
        self.assertIsInstance(state, dict)
        self.assertEqual(state["failed_batches"], [])
        self.assertNotIn("quota circuit breaker tripped", log_text)


class FailureEvidenceTests(unittest.TestCase):
    def test_c5_batch_failures_write_raw_evidence_with_ordinals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            write_json(
                handles_path,
                [
                    {
                        "social": {"twitter": "alpha"},
                        "id": {"bioguide": "A000001"},
                    }
                ],
            )
            args = collection_args(root, handles_path)

            def invalid_runner(
                _command: object,
                _prompt: str,
                _state_dir: Path,
            ) -> str:
                return collector.GrokOutput(
                    "not JSON",
                    raw_stdout=b"\xffraw stdout",
                    stderr=b"stderr \xff",
                )

            return_code = collector.run_collection(
                args,
                runner=invalid_runner,
                sleep_fn=lambda _seconds: None,
            )
            evidence_paths = sorted((root / "state" / "failures").glob("*.txt"))
            evidence = [path.read_bytes() for path in evidence_paths]

        self.assertEqual(return_code, 2)
        self.assertEqual(len(evidence_paths), 2)
        self.assertTrue(any(path.name.endswith("-b1.txt") for path in evidence_paths))
        self.assertTrue(any(path.name.endswith("-b2.txt") for path in evidence_paths))
        for payload in evidence:
            self.assertFalse(payload.startswith(b"\xef\xbb\xbf"))
            self.assertIn(b"\xffraw stdout", payload)
            self.assertIn("stderr \ufffd".encode("utf-8"), payload)

    def test_c5_prunes_failure_directory_to_newest_50(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            write_json(handles_path, [])
            failures_path = root / "state" / "failures"
            failures_path.mkdir(parents=True)
            base_ns = 1_700_000_000_000_000_000
            for index in range(53):
                path = failures_path / f"failure-{index:02d}.txt"
                path.write_bytes(b"failure")
                stamp = base_ns + index * 1_000_000_000
                os.utime(path, ns=(stamp, stamp))

            return_code = collector.run_collection(
                collection_args(root, handles_path),
            )
            remaining = {path.name for path in failures_path.iterdir()}

        self.assertEqual(return_code, 0)
        self.assertEqual(len(remaining), 50)
        self.assertNotIn("failure-00.txt", remaining)
        self.assertNotIn("failure-01.txt", remaining)
        self.assertNotIn("failure-02.txt", remaining)
        self.assertIn("failure-52.txt", remaining)


class CursorAndMarkerTests(unittest.TestCase):
    def test_c6_limit_run_leaves_success_cursor_unchanged(self) -> None:
        old_success = "2026-07-20T12:00:00Z"
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            state_path = root / "state" / "state.json"
            write_json(
                handles_path,
                [
                    {"social": {"twitter": "alpha"}, "id": {}},
                    {"social": {"twitter": "beta"}, "id": {}},
                ],
            )
            collector.write_state_atomic(
                state_path,
                {
                    "batch_format_version": 2,
                    "last_success_utc": old_success,
                    "failed_batches": [],
                },
            )
            args = collection_args(root, handles_path, handles_limit=1)
            calls: list[str] = []

            def empty_runner(
                _command: object,
                prompt: str,
                _state_dir: Path,
            ) -> str:
                calls.append(prompt)
                return "[]"

            return_code = collector.run_collection(
                args,
                runner=empty_runner,
                sleep_fn=lambda _seconds: None,
            )
            state = read_json(state_path)
            log_text = (root / "state" / "collector.log").read_text(
                encoding="utf-8"
            )

        self.assertEqual(return_code, 0)
        self.assertIsInstance(state, dict)
        self.assertEqual(state["last_success_utc"], old_success)
        self.assertEqual(state["batch_format_version"], 2)
        self.assertEqual(len(calls), 1)
        self.assertIn("from:alpha", calls[0])
        self.assertNotIn("from:beta", calls[0])
        self.assertIn("limit run: success cursor unchanged\n", log_text)

    def test_c7_partial_marker_created_then_removed_by_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            state_dir = root / "state"
            write_json(
                handles_path,
                [
                    {
                        "social": {"twitter": "alpha"},
                        "id": {"bioguide": "A000001"},
                    }
                ],
            )
            args = collection_args(root, handles_path)

            def failing_runner(
                _command: object,
                _prompt: str,
                _state_dir: Path,
            ) -> str:
                raise collector.BatchError("scripted failure")

            first_code = collector.run_collection(
                args,
                runner=failing_runner,
                sleep_fn=lambda _seconds: None,
            )
            first_state = read_json(state_dir / "state.json")
            self.assertIsInstance(first_state, dict)
            failed_query = first_state["failed_batches"][0]
            partial_text = (state_dir / "PARTIAL.marker").read_text(
                encoding="utf-8"
            )
            (state_dir / "FAILED.marker").write_text(
                "stale fatal marker\n",
                encoding="utf-8",
                newline="\n",
            )

            second_code = collector.run_collection(
                args,
                runner=lambda _command, _prompt, _state_dir: "[]",
                sleep_fn=lambda _seconds: None,
            )
            partial_exists = (state_dir / "PARTIAL.marker").exists()
            failed_exists = (state_dir / "FAILED.marker").exists()

        self.assertEqual(first_code, 2)
        self.assertEqual(
            partial_text,
            (
                "appended=0\n"
                "failed_batches=1\n"
                f"first_failed_query={failed_query}\n"
            ),
        )
        self.assertEqual(second_code, 0)
        self.assertFalse(partial_exists)
        self.assertFalse(failed_exists)


class StateVersionTests(unittest.TestCase):
    def test_c10_discards_stale_format_carried_batches(self) -> None:
        stale_query = (
            "(from:stalehandle) since:2026-06-01 until:2026-06-30"
        )
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            state_path = root / "state" / "state.json"
            write_json(
                handles_path,
                [{"social": {"twitter": "alpha"}, "id": {}}],
            )
            collector.write_state_atomic(
                state_path,
                {
                    "last_success_utc": None,
                    "failed_batches": [stale_query],
                },
            )
            args = collection_args(root, handles_path)
            calls: list[str] = []

            def empty_runner(
                _command: object,
                prompt: str,
                _state_dir: Path,
            ) -> str:
                calls.append(prompt)
                return "[]"

            return_code = collector.run_collection(
                args,
                runner=empty_runner,
                sleep_fn=lambda _seconds: None,
            )
            state = read_json(state_path)
            log_text = (root / "state" / "collector.log").read_text(
                encoding="utf-8"
            )

        self.assertEqual(return_code, 0)
        self.assertEqual(len(calls), 1)
        self.assertIn("from:alpha", calls[0])
        self.assertNotIn("from:stalehandle", calls[0])
        self.assertIsInstance(state, dict)
        self.assertEqual(state["batch_format_version"], 2)
        self.assertEqual(state["failed_batches"], [])
        self.assertIn(
            "discarding 1 stale-format carried batches\n",
            log_text,
        )

    def test_d2_discards_six_handle_carried_v2_query(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            state_path = root / "state" / "state.json"
            handles = [
                collector.HandleRef(f"h{index}", None)
                for index in range(6)
            ]
            write_json(
                handles_path,
                [
                    {"social": {"twitter": item.handle}, "id": {}}
                    for item in handles
                ],
            )
            until = datetime.now().astimezone().date()
            oversized_query = collector.make_query(
                handles,
                date(2026, 7, 1),
                until,
            )
            collector.write_state_atomic(
                state_path,
                {
                    "batch_format_version": 2,
                    "last_success_utc": None,
                    "failed_batches": [oversized_query],
                },
            )
            calls: list[str] = []

            def empty_runner(
                _command: object,
                prompt: str,
                _state_dir: Path,
            ) -> str:
                calls.append(prompt.splitlines()[1])
                return "[]"

            return_code = collector.run_collection(
                collection_args(root, handles_path),
                runner=empty_runner,
                sleep_fn=lambda _seconds: None,
            )
            log_text = (root / "state" / "collector.log").read_text(
                encoding="utf-8"
            )

        self.assertEqual(return_code, 0)
        self.assertEqual(len(calls), 2)
        self.assertNotIn(oversized_query, calls)
        self.assertTrue(
            all(
                len(collector.parse_query_handles(query)) <= 5
                for query in calls
            )
        )
        self.assertIn(
            "discarding 1 stale-format carried batches\n",
            log_text,
        )


class CatalogFailureTests(unittest.TestCase):
    def test_c9_catalog_failure_saves_all_batches_without_advancing(self) -> None:
        old_success = "2026-07-20T12:00:00Z"
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            state_dir = root / "state"
            state_path = state_dir / "state.json"
            handles = [
                collector.HandleRef(f"h{index}", None)
                for index in range(6)
            ]
            write_json(
                handles_path,
                [
                    {"social": {"twitter": item.handle}, "id": {}}
                    for item in handles
                ],
            )
            collector.write_state_atomic(
                state_path,
                {
                    "batch_format_version": 2,
                    "last_success_utc": old_success,
                    "failed_batches": [],
                },
            )
            argv = [
                "--force",
                "--since",
                "2026-07-01",
                "--handles-file",
                str(handles_path),
                "--catalog",
                str(root / "catalog.jsonl"),
                "--state-dir",
                str(state_dir),
            ]
            expected_until = datetime.now().astimezone().date()
            expected_queries = [
                batch.query
                for batch in collector.build_batches(
                    handles,
                    date(2026, 7, 1),
                    expected_until,
                )
            ]

            with (
                mock.patch.object(
                    collector,
                    "run_prompt_process",
                    return_value="[]",
                ),
                mock.patch.object(
                    collector,
                    "append_catalog",
                    side_effect=OSError("simulated catalog append failure"),
                ),
                mock.patch.object(collector.time, "sleep", return_value=None),
            ):
                return_code = collector.main(argv)

            state = read_json(state_path)
            marker_text = (state_dir / "FAILED.marker").read_text(
                encoding="utf-8"
            )

        self.assertEqual(return_code, 1)
        self.assertIsInstance(state, dict)
        self.assertEqual(state["batch_format_version"], 2)
        self.assertEqual(state["last_success_utc"], old_success)
        self.assertEqual(state["failed_batches"], expected_queries)
        self.assertEqual(
            marker_text,
            "OSError: simulated catalog append failure\n",
        )


class EndToEndTests(unittest.TestCase):
    def test_fake_runner_two_batches_and_duplicate_across_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            catalog_path = root / "catalog.jsonl"
            state_dir = root / "state"
            runner_path = root / "fake_runner.py"
            counter_path = root / "counter.txt"
            state_dir.mkdir()

            handles = [
                {
                    "social": {"twitter": f"h{number:014d}"},
                    "id": {"bioguide": f"B{number:06d}"},
                }
                for number in range(10)
            ]
            write_json(handles_path, handles)
            runner_path.write_text(
                (
                    "from pathlib import Path\n"
                    "import json\n"
                    "import re\n"
                    "import sys\n"
                    "counter_path = Path(sys.argv[1])\n"
                    "prompt_index = sys.argv.index('--prompt-file')\n"
                    "prompt_path = Path(sys.argv[prompt_index + 1])\n"
                    "count = int(counter_path.read_text(encoding='utf-8')) "
                    "if counter_path.exists() else 0\n"
                    "count += 1\n"
                    "counter_path.write_text(str(count), encoding='utf-8')\n"
                    "prompt = prompt_path.read_text(encoding='utf-8')\n"
                    "handles = re.findall(r'from:([A-Za-z0-9_]+)', prompt)\n"
                    "if count in (1, 3):\n"
                    "    url = 'https://x.example/shared'\n"
                    "    text = 'shared\\u00a0post\\u6f22'\n"
                    "elif count == 2:\n"
                    "    url = 'https://x.example/second'\n"
                    "    text = 'second post'\n"
                    "else:\n"
                    "    url = 'https://x.example/third'\n"
                    "    text = 'third post'\n"
                    "payload = [{'handle': handles[0], "
                    "'utc_date': '2026-07-23T10:00:00Z', "
                    "'text': text, 'url': url}]\n"
                    "sys.stdout.buffer.write((json.dumps("
                    "payload, ensure_ascii=False) + '\\n').encode('utf-8'))\n"
                ),
                encoding="utf-8",
                newline="\n",
            )
            marker_path = state_dir / "FAILED.marker"
            marker_path.write_text(
                "stale\n",
                encoding="utf-8",
                newline="\n",
            )
            command_json = json.dumps(
                [sys.executable, str(runner_path), str(counter_path)]
            )
            argv = [
                "--force",
                "--since",
                "2026-07-01",
                "--handles-file",
                str(handles_path),
                "--catalog",
                str(catalog_path),
                "--state-dir",
                str(state_dir),
                "--grok-command-json",
                command_json,
            ]

            with mock.patch.object(
                collector.time,
                "sleep",
                return_value=None,
            ) as sleep:
                first_code = collector.main(argv)
                first_records = read_jsonl(catalog_path)
                second_code = collector.main(argv)

            records = read_jsonl(catalog_path)
            catalog_bytes = catalog_path.read_bytes()
            state = read_json(state_dir / "state.json")
            counter_value = counter_path.read_text(encoding="utf-8")
            log_text = (state_dir / "collector.log").read_text(
                encoding="utf-8"
            )
            prompt_files = list(state_dir.glob("monday-x-prompt-*.txt"))

        self.assertEqual(first_code, 0)
        self.assertEqual(second_code, 0)
        self.assertEqual(len(first_records), 2)
        self.assertEqual(len(records), 3)
        self.assertEqual(
            {record["url"] for record in records},
            {
                "https://x.example/shared",
                "https://x.example/second",
                "https://x.example/third",
            },
        )
        shared_record = next(
            record
            for record in records
            if record["url"] == "https://x.example/shared"
        )
        self.assertEqual(shared_record["text"], "shared\u00a0post\u6f22")
        self.assertIn("\u00a0".encode("utf-8"), catalog_bytes)
        self.assertIn("\u6f22".encode("utf-8"), catalog_bytes)
        self.assertIsInstance(state, dict)
        self.assertIsNotNone(state["last_success_utc"])
        self.assertEqual(state["failed_batches"], [])
        self.assertEqual(counter_value, "4")
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(log_text.count("=== run "), 2)
        self.assertFalse(marker_path.exists())
        self.assertEqual(prompt_files, [])

    def test_failed_batch_retries_carries_query_and_returns_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            catalog_path = root / "catalog.jsonl"
            state_dir = root / "state"
            runner_path = root / "failing_runner.py"
            counter_path = root / "counter.txt"
            state_dir.mkdir()
            write_json(
                handles_path,
                [
                    {
                        "social": {"twitter": "alpha"},
                        "id": {"bioguide": "A000001"},
                    }
                ],
            )
            runner_path.write_text(
                (
                    "from pathlib import Path\n"
                    "import sys\n"
                    "counter_path = Path(sys.argv[1])\n"
                    "count = int(counter_path.read_text(encoding='utf-8')) "
                    "if counter_path.exists() else 0\n"
                    "counter_path.write_text(str(count + 1), "
                    "encoding='utf-8')\n"
                    "print('not json')\n"
                ),
                encoding="utf-8",
                newline="\n",
            )
            marker_path = state_dir / "FAILED.marker"
            marker_path.write_text(
                "old fatal marker\n",
                encoding="utf-8",
                newline="\n",
            )
            argv = [
                "--force",
                "--since",
                "2026-07-01",
                "--handles-file",
                str(handles_path),
                "--catalog",
                str(catalog_path),
                "--state-dir",
                str(state_dir),
                "--grok-command-json",
                json.dumps(
                    [sys.executable, str(runner_path), str(counter_path)]
                ),
            ]
            expected_until = datetime.now().astimezone().date()

            with mock.patch.object(
                collector.time,
                "sleep",
                return_value=None,
            ) as sleep:
                return_code = collector.main(argv)

            state = read_json(state_dir / "state.json")
            counter_value = counter_path.read_text(encoding="utf-8")
            marker_text = marker_path.read_text(encoding="utf-8")
            prompt_files = list(state_dir.glob("monday-x-prompt-*.txt"))

        self.assertEqual(return_code, 2)
        self.assertIsInstance(state, dict)
        self.assertIsNone(state["last_success_utc"])
        self.assertEqual(
            state["failed_batches"],
            [
                "(from:alpha) since:2026-07-01 "
                f"until:{expected_until.isoformat()}"
            ],
        )
        self.assertEqual(counter_value, "2")
        self.assertEqual(sleep.call_count, 1)
        self.assertEqual(marker_text, "old fatal marker\n")
        self.assertFalse(catalog_path.exists())
        self.assertEqual(prompt_files, [])

    def test_fatal_error_writes_failed_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            handles_path = root / "handles.json"
            state_dir = root / "state"
            write_json(handles_path, {"not": "a list"})
            return_code = collector.main(
                [
                    "--force",
                    "--since",
                    "2026-07-01",
                    "--handles-file",
                    str(handles_path),
                    "--catalog",
                    str(root / "catalog.jsonl"),
                    "--state-dir",
                    str(state_dir),
                ]
            )
            marker_bytes = (state_dir / "FAILED.marker").read_bytes()

        self.assertEqual(return_code, 1)
        self.assertIn(b"CollectorError", marker_bytes)
        self.assertFalse(marker_bytes.startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
