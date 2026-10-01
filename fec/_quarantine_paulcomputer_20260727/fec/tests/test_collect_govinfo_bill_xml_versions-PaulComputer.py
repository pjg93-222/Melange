from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


SCRIPT = (
    pathlib.Path(__file__).resolve().parents[1]
    / "collect_govinfo_bill_xml_versions.py"
)
SPEC = importlib.util.spec_from_file_location("govinfo_version_collector", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
collector = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = collector
SPEC.loader.exec_module(collector)


def version_url(canonical_key: str, version_code: str) -> str:
    congress, measure_type, number = canonical_key.split(":")
    package = f"BILLS-{congress}{measure_type}{number}{version_code}"
    return (
        f"https://www.govinfo.gov/content/pkg/{package}/xml/{package}.xml"
    )


def source_record(
    canonical_key: str, versions: list[dict[str, object]]
) -> dict[str, object]:
    congress, measure_type, number = canonical_key.split(":")
    source_url = (
        "https://www.govinfo.gov/bulkdata/BILLSTATUS/"
        f"{congress}/{measure_type}/BILLSTATUS-{congress}{measure_type}{number}.xml"
    )
    return {
        "schema": "test",
        "canonical_key": canonical_key,
        "identity": {
            "congress": int(congress),
            "type": measure_type,
            "number": int(number),
        },
        "text_versions": versions,
        "provenance": {
            "source_url": source_url,
            "source_sha256": hashlib.sha256(source_url.encode()).hexdigest(),
        },
    }


def bill_xml(canonical_key: str) -> bytes:
    congress, measure_type, number = canonical_key.split(":")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<bill><form>"
        f"<congress>{congress}th Congress</congress>"
        f"<legis-num>{measure_type.upper()}. {number}</legis-num>"
        "</form></bill>"
    ).encode()


class GovInfoCollectorTests(unittest.TestCase):
    def write_record(
        self,
        root: pathlib.Path,
        name: str,
        record: dict[str, object],
    ) -> None:
        (root / name).write_text(json.dumps(record), encoding="utf-8")

    def test_plan_binds_all_versions_and_preserves_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            self.write_record(
                root,
                "a.json",
                source_record(
                    "118:hr:42",
                    [
                        {
                            "date": "2023-01-09T05:00:00Z",
                            "type": "Introduced in House",
                            "urls": [version_url("118:hr:42", "ih")],
                        },
                        {
                            "date": "2023-03-01T05:00:00Z",
                            "type": "Engrossed in House",
                            "urls": [version_url("118:hr:42", "eh")],
                        },
                    ],
                ),
            )
            self.write_record(
                root, "b.json", source_record("118:s:7", [])
            )
            plan = collector.build_plan(root)

            self.assertEqual(len(plan.records), 2)
            self.assertEqual(len(plan.jobs), 2)
            self.assertEqual(
                {job["version_code"] for job in plan.jobs}, {"ih", "eh"}
            )
            self.assertEqual(len(plan.missing), 1)
            self.assertEqual(plan.missing[0]["canonical_key"], "118:s:7")
            self.assertEqual(plan.missing[0]["reason"], "no_text_versions")
            self.assertTrue(
                all(len(str(job["job_id"])) == 64 for job in plan.jobs)
            )

    def test_source_package_identity_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            record = source_record(
                "118:hr:42",
                [{"urls": [version_url("118:hr:42", "ih")]}],
            )
            provenance = record["provenance"]
            assert isinstance(provenance, dict)
            provenance["source_url"] = str(provenance["source_url"]).replace(
                "118hr42", "118hr43"
            )
            self.write_record(root, "record.json", record)
            with self.assertRaisesRegex(
                collector.CollectionError, "source-package identity mismatch"
            ):
                collector.build_plan(root)

    def test_version_url_identity_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            self.write_record(
                root,
                "record.json",
                source_record(
                    "118:hr:42",
                    [{"urls": [version_url("118:hr:43", "ih")]}],
                ),
            )
            with self.assertRaisesRegex(
                collector.CollectionError, "version URL identity mismatch"
            ):
                collector.build_plan(root)

    def test_xml_identity_rejects_html_and_wrong_measure(self) -> None:
        job = {"canonical_key": "118:hr:42"}
        accepted = collector.validate_xml(bill_xml("118:hr:42"), job)
        self.assertEqual(accepted["matched_measure"], "hr42")
        with self.assertRaisesRegex(collector.CollectionError, "HTML"):
            collector.validate_xml(
                b"<html><body>challenge</body></html>" + b" " * 64, job
            )
        with self.assertRaisesRegex(
            collector.CollectionError, "measure identity mismatch"
        ):
            collector.validate_xml(bill_xml("118:hr:43"), job)

    def test_accept_job_calls_fetch_once_and_content_addresses_xml(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            self.write_record(
                root,
                "record.json",
                source_record(
                    "118:hr:42",
                    [
                        {
                            "date": "2023-01-09T05:00:00Z",
                            "type": "Introduced in House",
                            "urls": [version_url("118:hr:42", "ih")],
                        }
                    ],
                ),
            )
            job = collector.build_plan(root).jobs[0]
            body = bill_xml("118:hr:42")
            calls: list[str] = []

            def fetch(url: str) -> collector.FetchResponse:
                calls.append(url)
                return collector.FetchResponse(
                    body=body,
                    status=200,
                    final_url=url,
                    headers={"content-type": "application/xml"},
                )

            receipt = collector.accept_job(job, root / "objects", fetch)
            self.assertEqual(calls, [job["url"]])
            self.assertEqual(receipt["attempts"], 1)
            self.assertEqual(receipt["retry_waits"], 0)
            self.assertEqual(
                receipt["content_sha256"], hashlib.sha256(body).hexdigest()
            )
            self.assertEqual(
                pathlib.Path(receipt["object_path"]).read_bytes(), body
            )

    def test_immutable_writer_never_replaces_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "receipt.json"
            self.assertTrue(collector.immutable_write(path, b"first"))
            self.assertFalse(collector.immutable_write(path, b"first"))
            with self.assertRaisesRegex(
                collector.CollectionError, "immutable content drift"
            ):
                collector.immutable_write(path, b"second")
            self.assertEqual(path.read_bytes(), b"first")

    def test_canary_is_deterministic_and_spans_sorted_plan(self) -> None:
        jobs = tuple(
            {"canonical_key": f"118:hr:{index + 1}", "job_id": str(index)}
            for index in range(10)
        )
        selected = collector.select_jobs(jobs, "canary", 3)
        self.assertEqual(
            [job["canonical_key"] for job in selected],
            ["118:hr:1", "118:hr:5", "118:hr:10"],
        )
        self.assertEqual(
            selected, collector.select_jobs(jobs, "canary", 3)
        )

    def test_cli_requires_explicit_plan_canary_or_full(self) -> None:
        with self.assertRaises(SystemExit):
            collector.parse_args(
                ["--input", "in", "--out", "out", "--run-id", "run"]
            )
        args = collector.parse_args(
            [
                "--input",
                "in",
                "--out",
                "out",
                "--run-id",
                "canary-1",
                "--canary",
                "5",
            ]
        )
        self.assertEqual(args.mode, "canary")
        self.assertEqual(args.workers, 16)


if __name__ == "__main__":
    unittest.main()