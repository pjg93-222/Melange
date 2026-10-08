"""Independent semantic verifier for A7 machine-local review artifacts."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterator


EXPECTED_SCOPE = 25_340


class VerificationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def rows(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        for line_number, line in enumerate(stream, 1):
            value = json.loads(line)
            if not isinstance(value, dict):
                raise VerificationError(f"{path}:{line_number}: non-object row")
            yield value


def verify_file(root: Path, descriptor: dict[str, Any]) -> Path:
    path = root / descriptor["path"]
    if not path.is_file():
        raise VerificationError(f"missing output {path}")
    if path.stat().st_size != int(descriptor["bytes"]):
        raise VerificationError(f"byte mismatch {path}")
    if sha256_file(path) != descriptor["sha256"]:
        raise VerificationError(f"hash mismatch {path}")
    return path


def verify(root: Path, twin: Path | None = None) -> dict[str, Any]:
    receipt_path = root / "a7_build_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS":
        raise VerificationError("producer receipt is not PASS")
    if receipt.get("expected_scope_size") != EXPECTED_SCOPE:
        raise VerificationError("unexpected scope")
    if any(
        receipt.get(field) != 0
        for field in (
            "canonical_employment_promotions",
            "canonical_identity_promotions",
            "complete_history_assertions",
        )
    ):
        raise VerificationError("producer receipt contains a forbidden promotion")

    outputs = receipt["outputs"]
    paths = {role: verify_file(root, descriptor) for role, descriptor in outputs.items()}
    inventory = json.loads(paths["inventory"].read_text(encoding="utf-8"))
    if inventory["candidate_policy"]["name_only_matches"] != 0:
        raise VerificationError("name-only linkage is not zero")
    if inventory["candidate_policy"]["network_requests"] != 0:
        raise VerificationError("network request count is not zero")
    if inventory["candidate_policy"]["private_credentials_read"] != 0:
        raise VerificationError("credential read count is not zero")

    source_count = 0
    for row in rows(paths["source_file_inventory"]):
        source_count += 1
        source_path = Path(row["path"])
        if not source_path.is_file():
            raise VerificationError(f"inventoried source missing: {source_path}")
        if source_path.stat().st_size != int(row["bytes"]):
            raise VerificationError(f"inventoried source size mismatch: {source_path}")
        if sha256_file(source_path) != row["sha256"]:
            raise VerificationError(f"inventoried source hash mismatch: {source_path}")
    if source_count != int(outputs["source_file_inventory"]["rows"]):
        raise VerificationError("source-file inventory row count mismatch")

    ld203_ids: set[str] = set()
    ld203_people: Counter[str] = Counter()
    ld203_count = 0
    for row in rows(paths["ld203_candidates"]):
        ld203_count += 1
        if row["candidate_id"] in ld203_ids:
            raise VerificationError("duplicate LD-203 candidate ID")
        ld203_ids.add(row["candidate_id"])
        person_id = str(row["lda_source_person_id"])
        ld203_people[person_id] += 1
        if row["identity_anchor"] != "EXACT_LDA_NUMERIC_ID":
            raise VerificationError("LD-203 row lacks exact numeric-ID anchor")
        if person_id.rsplit(":", 1)[-1] != str(row["source_person_numeric_id"]):
            raise VerificationError("LD-203 numeric ID projection mismatch")
        if not str(row["lda_registrant_id"]).startswith("lda:registrant:"):
            raise VerificationError("LD-203 registrant namespace mismatch")
        if row["identity_status"] != "REVIEW_REQUIRED":
            raise VerificationError("LD-203 identity status is not review-only")
        if row["organization_status"] != "REVIEW_REQUIRED":
            raise VerificationError("LD-203 organization status is not review-only")
        if row["canonical_identity_promoted"] or row["canonical_employment_promoted"]:
            raise VerificationError("LD-203 row promotes a candidate")
        if row["employment_interval_asserted"] or row["complete_history_asserted"]:
            raise VerificationError("LD-203 row overclaims employment semantics")
    if ld203_count != int(outputs["ld203_candidates"]["rows"]):
        raise VerificationError("LD-203 output row count mismatch")

    fec_ids: set[str] = set()
    fec_people: Counter[str] = Counter()
    fec_count = 0
    for row in rows(paths["fec_candidates"]):
        fec_count += 1
        if row["candidate_id"] in fec_ids:
            raise VerificationError("duplicate FEC candidate ID")
        fec_ids.add(row["candidate_id"])
        person_id = str(row["lda_source_person_id"])
        fec_people[person_id] += 1
        if int(row["identity_anchor_count"]) < 3:
            raise VerificationError("FEC candidate lacks required multi-anchor evidence")
        if not row["source_name_key"] or not row["source_employer_key"]:
            raise VerificationError("FEC candidate has an empty normalized anchor")
        if not row["lda_registrant_anchors"]:
            raise VerificationError("FEC candidate has no LD-203 registrant anchor")
        if row["identity_status"] != "REVIEW_REQUIRED":
            raise VerificationError("FEC identity status is not review-only")
        if row["organization_status"] != "REVIEW_REQUIRED":
            raise VerificationError("FEC organization status is not review-only")
        if row["canonical_identity_promoted"] or row["canonical_employment_promoted"]:
            raise VerificationError("FEC row promotes a candidate")
        if row["employment_interval_asserted"] or row["complete_history_asserted"]:
            raise VerificationError("FEC row overclaims point-observation semantics")
    if fec_count != int(outputs["fec_candidates"]["rows"]):
        raise VerificationError("FEC output row count mismatch")

    coverage_count = 0
    coverage_ids: set[str] = set()
    added = 0
    for ordinal, row in enumerate(rows(paths["coverage"]), 1):
        coverage_count += 1
        person_id = str(row["lda_source_person_id"])
        if person_id in coverage_ids:
            raise VerificationError("duplicate coverage person")
        coverage_ids.add(person_id)
        if int(row["sealed_queue_ordinal"]) != ordinal:
            raise VerificationError("coverage source order is not conserved")
        if int(row["ld203_affiliation_candidate_count"]) != ld203_people[person_id]:
            raise VerificationError("coverage LD-203 count mismatch")
        if int(row["fec_employer_observation_candidate_count"]) != fec_people[person_id]:
            raise VerificationError("coverage FEC count mismatch")
        if row["canonical_identity_promoted"] or row["canonical_employment_promoted"]:
            raise VerificationError("coverage row contains a promotion")
        if row["complete_history_asserted"]:
            raise VerificationError("coverage row asserts complete history")
        added += int(bool(row["a7_adds_dated_employer_observation_beyond_baseline"]))
    if coverage_count != EXPECTED_SCOPE or coverage_count != int(outputs["coverage"]["rows"]):
        raise VerificationError("coverage does not conserve 25,340 people")
    if added != int(receipt["new_dated_employer_observation_people_beyond_baseline"]):
        raise VerificationError("baseline delta count mismatch")

    twin_equal: dict[str, bool] = {}
    if twin is not None:
        twin_receipt = json.loads((twin / "a7_build_receipt.json").read_text(encoding="utf-8"))
        if twin_receipt != receipt:
            raise VerificationError("primary/twin producer receipts differ")
        for role, descriptor in outputs.items():
            twin_path = verify_file(twin, twin_receipt["outputs"][role])
            equal = (root / descriptor["path"]).read_bytes() == twin_path.read_bytes()
            twin_equal[role] = equal
            if not equal:
                raise VerificationError(f"primary/twin output differs: {role}")

    return {
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "coverage_people": coverage_count,
        "fec_candidates": fec_count,
        "fec_people": len(fec_people),
        "ld203_candidates": ld203_count,
        "ld203_people": len(ld203_people),
        "new_dated_employer_observation_people_beyond_baseline": added,
        "schema_id": "staffer-network-a7-machine-local-verification-v1",
        "source_file_inventory_rows": source_count,
        "status": "PASS",
        "twin_byte_equal": twin_equal,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--twin-root", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    options = parser.parse_args()
    try:
        result = verify(options.root, options.twin_root)
        options.receipt.parent.mkdir(parents=True, exist_ok=True)
        options.receipt.write_text(
            json.dumps(result, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
    except Exception as error:
        print(json.dumps({"status": "FAILED", "error": f"{type(error).__name__}: {error}"}))
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
