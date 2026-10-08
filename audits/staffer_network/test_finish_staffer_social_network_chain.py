#!/usr/bin/env python3
"""Unit tests for the post-crawl finishing chain runner.

Covered:
  * command resolution from receipts (fixture receipts in a temp tree)
  * gate evaluation (PASS/COMPLETE vs IN_PROGRESS, and each individual failure mode)
  * twin byte-identity checking, including the generation_id manifest exemption
  * halt-file writing

Nothing here touches the live tree: every module path constant is redirected into a
temporary directory for the duration of each test.
"""

from __future__ import annotations

import argparse
import contextlib
import gzip
import json
import os
import tempfile
import unittest
from pathlib import Path

import finish_staffer_social_network_chain as chain_mod


# --------------------------------------------------------------------------- helpers


@contextlib.contextmanager
def redirected_tree(root: Path):
    """Point every module path constant at a temporary tree."""
    names = {
        "LT": root,
        "SN": root / "audits" / "staffer_network",
        "RAW": root / "audits" / "staffer_network" / "raw",
        "CRAWL_VERIFICATION": root / "audits" / "staffer_network" / "raw" / "crawl_verification.json",
        "STATE_JSON": root / "audits" / "staffer_network" / "raw" / "state.json",
        "BRIDGE_V3_RECEIPT": root / "bridge_v3" / "politico_payroll_direct_link_receipt.json",
        "NETWORK_V4_RECEIPT": root / "network_v4" / "staffer_social_network_receipt.json",
        "NETWORK_V4_MANIFEST": root / "network_v4" / "staffer_social_network_manifest.json",
        "V4_COMPLETION_DOC": root / "audits" / "staffer_network" / "V4.md",
        "VERIFY_CRAWL": root / "tools" / "verify_politico_profile_crawl.py",
        "WRITE_COMPLETION_REPORT": root / "tools" / "write_politico_profile_completion_report.py",
        "BUILD_BRIDGE": root / "tools" / "build_politico_payroll_direct_links.py",
        "VERIFY_BRIDGE": root / "tools" / "verify_politico_payroll_direct_links.py",
        "BUILD_NETWORK": root / "tools" / "build_staffer_social_network.py",
        "VERIFY_NETWORK": root / "tools" / "verify_staffer_social_network.py",
        "DASHBOARD_SECTION": root / "fec" / "surfaces" / "build_staffer_network_section.py",
        "RUN_PIPELINE": root / "fec" / "run_pipeline.py",
        "PIPELINE_LOCK": root / ".pipeline_run.lock",
        "EMIT_PS1": root / "no_such_emit.ps1",
    }
    saved = {name: getattr(chain_mod, name) for name in names}
    try:
        for name, value in names.items():
            setattr(chain_mod, name, value)
        for key in ("SN", "RAW"):
            names[key].mkdir(parents=True, exist_ok=True)
        yield names
    finally:
        for name, value in saved.items():
            setattr(chain_mod, name, value)


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def flag_value(command, flag: str):
    """Return the value that follows ``flag`` in a resolved command, else None."""
    for index, token in enumerate(command):
        if token == flag:
            return command[index + 1] if index + 1 < len(command) else ""
    return None


DIR_ROWS = r"C:\melange\raw\politico\crawl-x\directory_rows.ndjson"
CRAWL_RECEIPT = r"C:\melange\raw\politico\crawl-x\crawl_receipt.json"
SPINE = r"C:\melange\audits\staffer_network\hill_personnel_spine_20260903_v6_primary\hill_person_spine.ndjson.gz"
SPANS = r"C:\melange\audits\staffer_network\hill_personnel_spine_20260903_v6_primary\hill_person_office_spans.ndjson.gz"
ROSTER = r"C:\melange\data\engine\congestion.json"
HOUSE_SPANS = r"C:\melange\audits\staffer_network\house_personnel_ledger_20260903_v5_primary\house_person_office_spans.ndjson.gz"
SENATE_CANDIDATES = r"C:\melange\audits\staffer_network\senate_committee_payroll_20260903_v3_primary\senate_committee_payroll_candidates_2011_2026.ndjson.gz"
REVOLVING = r"C:\melange\audits\staffer_network\exploratory_temporal_tier_20260902_v1_primary\exploratory_temporal_edges.ndjson.gz"


def seed_receipts(names, *, drop_network_role: str | None = None,
                  drop_bridge_input: str | None = None) -> None:
    crawl_inputs = {
        "directory": DIR_ROWS,
        "profiles": str(names["RAW"] / "profiles.ndjson"),
        "failures": str(names["RAW"] / "failures.ndjson"),
        "state": str(names["RAW"] / "state.json"),
    }
    write_json(names["CRAWL_VERIFICATION"], {"inputs": crawl_inputs, "status": "IN_PROGRESS"})

    bridge_inputs = {
        DIR_ROWS: {"bytes": 1, "sha256": "a"},
        CRAWL_RECEIPT: {"bytes": 1, "sha256": "b"},
        SPINE: {"bytes": 1, "sha256": "c"},
        SPANS: {"bytes": 1, "sha256": "d"},
        ROSTER: {"bytes": 1, "sha256": "e"},
    }
    if drop_bridge_input:
        bridge_inputs.pop(drop_bridge_input)
    write_json(names["BRIDGE_V3_RECEIPT"], {"inputs": bridge_inputs, "status": "PASS"})

    network_inputs = [
        {"role": "hill_person_spine", "path": SPINE},
        {"role": "house_person_office_spans", "path": HOUSE_SPANS},
        {"role": "senate_committee_payroll_candidates", "path": SENATE_CANDIDATES},
        {"role": "exploratory_revolving_edges", "path": REVOLVING},
        {"role": "roster_congestion", "path": ROSTER},
    ]
    if drop_network_role:
        network_inputs = [row for row in network_inputs if row["role"] != drop_network_role]
    write_json(names["NETWORK_V4_RECEIPT"], {
        "inputs": network_inputs,
        "config_name": "staffer_social_network_20260903_v3",
        "vintage": "20260903",
        "status": "PASS",
    })
    write_json(names["NETWORK_V4_MANIFEST"], {"config_name": "staffer_social_network_20260903_v3"})


# --------------------------------------------------------------------------- tests


class CommandResolutionTests(unittest.TestCase):
    def test_crawl_verifier_is_argument_identical_to_the_recorded_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                res = chain_mod.Resolution("20260910", "py.exe", "2026-09-10T00:00:00Z")
                out = names["RAW"] / "crawl_verification.json"
                cmd = res.cmd_verify_crawl(out, require_complete=False)
                self.assertEqual(flag_value(cmd, "--directory"), DIR_ROWS)
                self.assertEqual(flag_value(cmd, "--profiles"), str(names["RAW"] / "profiles.ndjson"))
                self.assertEqual(flag_value(cmd, "--failures"), str(names["RAW"] / "failures.ndjson"))
                self.assertEqual(flag_value(cmd, "--state"), str(names["RAW"] / "state.json"))
                self.assertEqual(flag_value(cmd, "--output"), str(out))
                self.assertNotIn("--require-complete", cmd)
                self.assertIn("--require-complete", res.cmd_verify_crawl(out, require_complete=True))

    def test_failures_flag_is_omitted_when_the_receipt_records_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                payload = json.loads(names["CRAWL_VERIFICATION"].read_text(encoding="utf-8"))
                payload["inputs"]["failures"] = None
                write_json(names["CRAWL_VERIFICATION"], payload)
                res = chain_mod.Resolution("20260910", "py.exe", "2026-09-10T00:00:00Z")
                cmd = res.cmd_verify_crawl(names["RAW"] / "out.json", require_complete=False)
                self.assertIsNone(flag_value(cmd, "--failures"))
                self.assertTrue(any("did NOT pass --failures" in note for note in res.notes))

    def test_bridge_inputs_map_by_filename_to_the_right_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                res = chain_mod.Resolution("20260910", "py.exe", "2026-09-10T00:00:00Z")
                cmd = res.cmd_build_bridge(res.bridge_primary)
                self.assertEqual(flag_value(cmd, "--raw-directory"), DIR_ROWS)
                self.assertEqual(flag_value(cmd, "--crawl-receipt"), CRAWL_RECEIPT)
                self.assertEqual(flag_value(cmd, "--spine"), SPINE)
                self.assertEqual(flag_value(cmd, "--spans"), SPANS)
                self.assertEqual(flag_value(cmd, "--roster"), ROSTER)
                self.assertIn("--require-complete-profile-crawl", cmd)
                self.assertEqual(flag_value(cmd, "--output"), str(res.bridge_primary))
                self.assertTrue(res.bridge_primary.name.endswith("_20260910_v4_primary"))
                self.assertTrue(res.bridge_twin.name.endswith("_20260910_v4_twin"))

    def test_a_missing_bridge_input_is_an_owner_decision_not_a_guess(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names, drop_bridge_input=ROSTER)
                res = chain_mod.Resolution("20260910", "py.exe", "2026-09-10T00:00:00Z")
                cmd = res.cmd_build_bridge(res.bridge_primary)
                self.assertIsNone(flag_value(cmd, "--roster"))
                self.assertTrue(any("--roster" in item for item in res.owner_decisions))

    def test_bridge_verifier_output_is_a_directory_not_a_file(self):
        """verify_politico_payroll_direct_links.py does out.mkdir(exist_ok=False) and then
        writes out/'verification_report.json' itself.  Passing the file path would create a
        directory named verification_report.json."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                res = chain_mod.Resolution("20260910", "py.exe", "2026-09-10T00:00:00Z")
                out = flag_value(res.cmd_verify_bridge(), "--output")
                self.assertEqual(out, str(res.bridge_verification))
                self.assertNotIn("verification_report.json", out)
                self.assertEqual(flag_value(res.cmd_verify_bridge(), "--generation"),
                                 str(res.bridge_primary))
                self.assertEqual(flag_value(res.cmd_verify_bridge(), "--twin"),
                                 str(res.bridge_twin))
                # the bridge verifier has no --crawl-receipt flag
                self.assertIsNone(flag_value(res.cmd_verify_bridge(), "--crawl-receipt"))

    def test_network_verifier_output_is_the_verification_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                res = chain_mod.Resolution("20260910", "py.exe", "2026-09-10T00:00:00Z")
                cmd = res.cmd_verify_network()
                self.assertEqual(flag_value(cmd, "--output"), str(res.network_verification))
                self.assertEqual(flag_value(cmd, "--expected-vintage"), "20260910")
                self.assertEqual(flag_value(cmd, "--expected-config-name"),
                                 "staffer_social_network_20260903_v3")

    def test_network_roots_come_from_the_v4_input_roles(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                res = chain_mod.Resolution("20260910", "py.exe", "2026-09-10T00:00:00Z")
                cmd = res.cmd_build_network(res.network_primary)
                self.assertEqual(flag_value(cmd, "--hill-spine-root"), str(Path(SPINE).parent))
                self.assertEqual(flag_value(cmd, "--house-ledger-root"), str(Path(HOUSE_SPANS).parent))
                self.assertEqual(flag_value(cmd, "--senate-committee-root"),
                                 str(Path(SENATE_CANDIDATES).parent))
                self.assertEqual(flag_value(cmd, "--exploratory-revolving-edges"), REVOLVING)
                self.assertEqual(flag_value(cmd, "--config-name"),
                                 "staffer_social_network_20260903_v3")
                self.assertEqual(flag_value(cmd, "--vintage"), "20260910")
                self.assertEqual(flag_value(cmd, "--generated-at"), "2026-09-10T00:00:00Z")
                self.assertIn("--no-glassbox", cmd)
                self.assertIn("--require-complete-politico-profile-crawl", cmd)

    def test_all_five_politico_review_inputs_point_at_the_new_bridge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                res = chain_mod.Resolution("20260910", "py.exe", "2026-09-10T00:00:00Z")
                cmd = res.cmd_build_network(res.network_primary)
                for flag, expected_name in (
                    ("--politico-current-committee-assertions",
                     "politico_current_committee_assertions.ndjson.gz"),
                    ("--politico-profile-employment-assertions",
                     "politico_profile_employment_assertions.ndjson.gz"),
                    ("--politico-profile-education-assertions",
                     "politico_profile_education_assertions.ndjson.gz"),
                    ("--politico-profile-policy-deltas",
                     "politico_profile_policy_deltas.ndjson.gz"),
                    ("--politico-explicit-committee-side-assertions",
                     "politico_explicit_committee_side_assertions.ndjson.gz"),
                ):
                    value = flag_value(cmd, flag)
                    self.assertIsNotNone(value, flag)
                    self.assertEqual(Path(value).name, expected_name)
                    self.assertEqual(Path(value).parent, res.bridge_primary)

    def test_primary_and_twin_share_one_generated_at_instant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                res = chain_mod.Resolution("20260910", "py.exe", "2026-09-10T00:00:00Z")
                primary = res.cmd_build_network(res.network_primary)
                twin = res.cmd_build_network(res.network_twin)
                self.assertEqual(flag_value(primary, "--generated-at"),
                                 flag_value(twin, "--generated-at"))
                self.assertNotEqual(flag_value(primary, "--output"), flag_value(twin, "--output"))

    def test_a_missing_network_role_is_an_owner_decision_not_a_guess(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names, drop_network_role="house_person_office_spans")
                res = chain_mod.Resolution("20260910", "py.exe", "2026-09-10T00:00:00Z")
                cmd = res.cmd_build_network(res.network_primary)
                self.assertIsNone(flag_value(cmd, "--house-ledger-root"))
                self.assertTrue(any("--house-ledger-root" in item for item in res.owner_decisions))


class GateTests(unittest.TestCase):
    @staticmethod
    def complete_receipt():
        return {
            "status": "PASS",
            "integrity_status": "PASS",
            "completion_status": "COMPLETE",
            "verification_failure_count": 0,
            "counts": {"profiles_accounted": 18618},
            "completion_gate": {"status": "PASS", "unmet_requirements": [],
                                "unmet_requirement_count": 0},
        }

    def test_partial_gate_accepts_integrity_pass_while_in_progress(self):
        receipt = {"status": "IN_PROGRESS", "integrity_status": "PASS",
                   "completion_status": "INCOMPLETE"}
        ok, reason = chain_mod.gate_partial_verification(receipt)
        self.assertTrue(ok)
        self.assertIn("PASS", reason)

    def test_partial_gate_rejects_integrity_fail(self):
        ok, reason = chain_mod.gate_partial_verification({"integrity_status": "FAIL"})
        self.assertFalse(ok)
        self.assertIn("required PASS", reason)

    def test_terminal_gate_accepts_a_fully_complete_receipt(self):
        ok, reason = chain_mod.gate_complete_verification(self.complete_receipt(), 0)
        self.assertTrue(ok, reason)

    def test_terminal_gate_rejects_an_in_progress_receipt(self):
        receipt = {
            "status": "IN_PROGRESS", "integrity_status": "PASS",
            "completion_status": "INCOMPLETE", "verification_failure_count": 0,
            "counts": {"profiles_accounted": 8138},
            "completion_gate": {"status": "INCOMPLETE",
                                "unmet_requirements": ["profiles_accounted"],
                                "unmet_requirement_count": 1},
        }
        ok, reason = chain_mod.gate_complete_verification(receipt, 2)
        self.assertFalse(ok)
        self.assertIn("exit code 2", reason)
        self.assertIn("completion_status", reason)
        self.assertIn("unmet_requirements", reason)
        self.assertIn("profiles_accounted", reason)

    def test_terminal_gate_rejects_each_single_defect(self):
        for mutate, fragment in (
            (lambda r: r.update(status="IN_PROGRESS"), "status="),
            (lambda r: r.update(completion_status="INCOMPLETE"), "completion_status="),
            (lambda r: r.update(verification_failure_count=1), "verification_failure_count="),
            (lambda r: r["counts"].update(profiles_accounted=18617), "profiles_accounted="),
            (lambda r: r["completion_gate"].update(unmet_requirements=["x"]), "unmet_requirements="),
            (lambda r: r["completion_gate"].update(unmet_requirement_count=1),
             "unmet_requirement_count="),
        ):
            receipt = self.complete_receipt()
            mutate(receipt)
            ok, reason = chain_mod.gate_complete_verification(receipt, 0)
            self.assertFalse(ok, fragment)
            self.assertIn(fragment, reason)

    def test_terminal_gate_rejects_a_nonzero_exit_even_when_the_receipt_looks_clean(self):
        ok, reason = chain_mod.gate_complete_verification(self.complete_receipt(), 2)
        self.assertFalse(ok)
        self.assertIn("exit code 2", reason)


class TwinIdentityTests(unittest.TestCase):
    @staticmethod
    def make_pair(tmp: Path, manifest_primary=None, manifest_twin=None,
                  payload_twin: bytes | None = None):
        primary = tmp / "gen_primary"
        twin = tmp / "gen_twin"
        primary.mkdir()
        twin.mkdir()
        payload = gzip.compress(b'{"row":1}\n', mtime=0)
        (primary / "edges.ndjson.gz").write_bytes(payload)
        (twin / "edges.ndjson.gz").write_bytes(payload_twin if payload_twin else payload)
        if manifest_primary is not None:
            write_json(primary / chain_mod.NETWORK_MANIFEST_NAME, manifest_primary)
            write_json(twin / chain_mod.NETWORK_MANIFEST_NAME, manifest_twin)
        return primary, twin

    def test_identical_pair_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            primary, twin = self.make_pair(Path(tmp))
            result = chain_mod.compare_generation(primary, twin, None)
            self.assertTrue(result["ok"], result)
            self.assertTrue(result["files"]["edges.ndjson.gz"]["identical"])

    def test_differing_payload_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            primary, twin = self.make_pair(Path(tmp), payload_twin=b"different")
            result = chain_mod.compare_generation(primary, twin, None)
            self.assertFalse(result["ok"])
            self.assertEqual(result["failures"][0]["check"], "twin_not_byte_identical")

    def test_manifest_may_differ_only_in_generation_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            primary, twin = self.make_pair(
                Path(tmp),
                manifest_primary={"generation_id": "gen_primary", "vintage": "20260910"},
                manifest_twin={"generation_id": "gen_twin", "vintage": "20260910"})
            result = chain_mod.compare_generation(primary, twin, chain_mod.NETWORK_MANIFEST_NAME)
            self.assertTrue(result["ok"], result)
            entry = result["files"][chain_mod.NETWORK_MANIFEST_NAME]
            self.assertEqual(entry["allowed_difference"], ["generation_id"])

    def test_manifest_differing_beyond_generation_id_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            primary, twin = self.make_pair(
                Path(tmp),
                manifest_primary={"generation_id": "gen_primary", "canonical_output_hash": "aaa"},
                manifest_twin={"generation_id": "gen_twin", "canonical_output_hash": "bbb"})
            result = chain_mod.compare_generation(primary, twin, chain_mod.NETWORK_MANIFEST_NAME)
            self.assertFalse(result["ok"])
            self.assertEqual(result["failures"][0]["check"],
                             "manifest_differs_beyond_generation_id")
            self.assertIn("canonical_output_hash", result["failures"][0]["differing_keys"])

    def test_a_manifest_exemption_is_not_granted_to_other_files(self):
        """The bridge has no manifest; a differing receipt there must still fail."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            primary = root / "b_primary"
            twin = root / "b_twin"
            primary.mkdir()
            twin.mkdir()
            write_json(primary / chain_mod.BRIDGE_RECEIPT_NAME, {"generation_id": "b_primary"})
            write_json(twin / chain_mod.BRIDGE_RECEIPT_NAME, {"generation_id": "b_twin"})
            result = chain_mod.compare_generation(primary, twin, None)
            self.assertFalse(result["ok"])
            self.assertEqual(result["failures"][0]["check"], "twin_not_byte_identical")

    def test_extra_file_in_one_generation_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            primary, twin = self.make_pair(Path(tmp))
            (primary / "stray.ndjson.gz").write_bytes(b"x")
            result = chain_mod.compare_generation(primary, twin, None)
            self.assertFalse(result["ok"])
            self.assertEqual(result["failures"][0]["check"], "file_set")
            self.assertEqual(result["failures"][0]["only_in_primary"], ["stray.ndjson.gz"])


class HaltFileTests(unittest.TestCase):
    @staticmethod
    def make_chain(names):
        args = argparse.Namespace(
            execute=False, dry_run=True, wait=False, frm=None, once=False,
            date="20260910", generated_at="2026-09-10T00:00:00Z", python="py.exe",
            verification_output=None, allow_overwrite_reports=False,
            no_glassbox=True, list_steps=False)
        return chain_mod.Chain(args)

    def test_halt_file_records_reason_and_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                chain = self.make_chain(names)
                path = chain.write_halt_file("step 5b terminal gate unmet: completion_status",
                                             {"step": "verify_complete", "accounted": 8138})
                self.assertTrue(path.exists())
                self.assertTrue(path.name.startswith("FINISH_CHAIN_HALT_"))
                self.assertTrue(path.name.endswith(".json"))
                self.assertEqual(path.parent, names["SN"])
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["schema_id"], "staffer-network-finish-chain-halt-v1")
                self.assertIn("completion_status", payload["reason"])
                self.assertEqual(payload["detail"]["step"], "verify_complete")
                self.assertEqual(payload["detail"]["accounted"], 8138)
                self.assertEqual(payload["review_status"], "REVIEW_REQUIRED")
                self.assertEqual(payload["date"], "20260910")
                self.assertTrue(payload["run_id"].endswith("-finish"))

    def test_chain_halt_exception_produces_a_halt_file_and_exit_3(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                chain = self.make_chain(names)
                try:
                    chain.halt("crawl has not reached terminal state", {"remaining": 10480})
                except chain_mod.ChainHalt as exc:
                    path = chain.write_halt_file(exc.reason, exc.detail)
                else:  # pragma: no cover
                    self.fail("halt() did not raise")
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(payload["detail"]["remaining"], 10480)

    def test_two_halts_do_not_overwrite_each_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                chain = self.make_chain(names)
                first = chain.write_halt_file("a", {})
                second = chain.write_halt_file("b", {})
                self.assertNotEqual(first, second)
                self.assertEqual(json.loads(first.read_text(encoding="utf-8"))["reason"], "a")
                self.assertEqual(json.loads(second.read_text(encoding="utf-8"))["reason"], "b")


class StaleHaltFileTests(unittest.TestCase):
    """A watchdog halt file only blocks while it is CURRENT.

    If the crawler wrote state.json again after the halt file's mtime, the
    crawler recovered from that transient abort on its own and the halt file
    is stale -- it must be ignored, not block the chain forever.  A halt file
    newer than state.json (or written while no fresher state exists) is still
    current and must keep blocking.
    """

    @staticmethod
    def make_chain(names):
        args = argparse.Namespace(
            execute=False, dry_run=True, wait=False, frm=None, once=False,
            date="20260910", generated_at="2026-09-10T00:00:00Z", python="py.exe",
            verification_output=None, allow_overwrite_reports=False,
            no_glassbox=True, list_steps=False)
        return chain_mod.Chain(args)

    def test_halt_file_older_than_state_json_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                chain = self.make_chain(names)
                halt_path = names["RAW"] / "WATCHDOG_HALT_20260905T021449Z.json"
                halt_path.write_text("{}", encoding="utf-8")
                os.utime(halt_path, (1_000_000, 1_000_000))
                write_json(names["STATE_JSON"], {"halted": False, "remaining": 0})
                os.utime(names["STATE_JSON"], (2_000_000, 2_000_000))
                self.assertEqual(chain.current_halt_files(), [])
                self.assertTrue(any("ignoring stale watchdog halt file" in line
                                    for line in chain.log.lines))

    def test_halt_file_newer_than_state_json_still_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                chain = self.make_chain(names)
                write_json(names["STATE_JSON"], {"halted": True, "remaining": 5})
                os.utime(names["STATE_JSON"], (1_000_000, 1_000_000))
                halt_path = names["RAW"] / "WATCHDOG_HALT_20260905T021449Z.json"
                halt_path.write_text("{}", encoding="utf-8")
                os.utime(halt_path, (2_000_000, 2_000_000))
                self.assertEqual(chain.current_halt_files(), [halt_path])

    def test_wait_for_crawl_skips_a_stale_halt_and_returns_on_terminal_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                chain = self.make_chain(names)
                halt_path = names["RAW"] / "WATCHDOG_HALT_20260905T021449Z.json"
                halt_path.write_text("{}", encoding="utf-8")
                os.utime(halt_path, (1_000_000, 1_000_000))
                write_json(names["STATE_JSON"], {"halted": False, "remaining": 0})
                os.utime(names["STATE_JSON"], (2_000_000, 2_000_000))
                chain.wait_for_crawl()  # must return quietly, never raise or poll-sleep
                self.assertTrue(any("ignoring stale watchdog halt file" in line
                                    for line in chain.log.lines))

    def test_wait_for_crawl_still_halts_on_a_current_halt_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with redirected_tree(root) as names:
                seed_receipts(names)
                chain = self.make_chain(names)
                write_json(names["STATE_JSON"], {"halted": True, "remaining": 5})
                os.utime(names["STATE_JSON"], (1_000_000, 1_000_000))
                halt_path = names["RAW"] / "WATCHDOG_HALT_20260905T021449Z.json"
                halt_path.write_text("{}", encoding="utf-8")
                os.utime(halt_path, (2_000_000, 2_000_000))
                with self.assertRaises(chain_mod.ChainHalt) as ctx:
                    chain.wait_for_crawl()
                self.assertEqual(ctx.exception.detail["halt_files"], [halt_path.name])


class AtomicWriteTests(unittest.TestCase):
    def test_atomic_write_replaces_and_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "sub" / "doc.md"
            chain_mod.atomic_write_text(target, "first")
            chain_mod.atomic_write_text(target, "second")
            self.assertEqual(target.read_text(encoding="utf-8"), "second")
            self.assertEqual([p.name for p in target.parent.iterdir()], ["doc.md"])

    def test_atomic_append_adds_a_trailing_newline_before_appending(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "doc.md"
            chain_mod.atomic_write_text(target, "head")
            chain_mod.atomic_append_text(target, "tail")
            self.assertEqual(target.read_text(encoding="utf-8"), "head\ntail")


if __name__ == "__main__":
    unittest.main(verbosity=2)
