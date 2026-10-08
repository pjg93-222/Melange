"""Rebuild the audited spine from pinned inputs; never promote title-only identity.

Stages: delta, primary, twin, verify, review. Run in that order. Outputs are
generation artifacts, not committed source. The v7->v8 relation is explicitly
one-to-many where v7 merged two undated payee records.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from fec.staffer_network import name_standard as ns
import verify_hill_personnel_spine as verifier

V7 = HERE / "hill_personnel_spine_20260907_v7_primary"
V6 = HERE / "hill_personnel_spine_20260903_v6_primary"
PREFIX = "hill_personnel_spine_20260908_v8"
REVIEW = HERE / "spine_identity_adjudication_20260908"
DELTA = REVIEW / "name_standard_delta_v1_2.json"
STAMP = "2026-09-08T00:00:00Z"


def rows(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_rows(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as stream:
            for value in values:
                stream.write((json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode())


def inputs():
    receipt = json.loads((V7 / "hill_personnel_spine_receipt.json").read_text())
    result = receipt["inputs"]
    for label, binding in result.items():
        if label in {"name_standard_module", "name_standard_delta_report"}:
            continue
        if sha(binding["path"]) != binding["sha256"]:
            raise ValueError("Audited input changed: " + label)
    return result


def corpora(bindings):
    yield "house", Path(bindings["house_personnel_observations"]["path"])
    for label, binding in sorted(bindings.items()):
        if label.startswith("senate_payroll_candidates_"):
            yield "senate", Path(binding["path"])


def delta(bindings):
    """Independent v6/triple census, before building the new generation."""
    table, loaded = ns.load_class_table()
    if not loaded:
        raise ValueError("Missing nickname class table")

    @lru_cache(maxsize=None)
    def parsed(chamber, raw):
        return ns.name_key(ns.parse_name(raw, verifier.name_standard_source(chamber, raw)), table=table)

    keys = defaultdict(Counter)
    n = 0
    for chamber, path in corpora(bindings):
        for row in rows(path):
            raw = str(row.get("payee_raw") or row.get("payee_name_raw") or "").strip()
            triple = verifier.payroll_payee_key(raw)
            if triple is not None:
                keys[triple][parsed(chamber, raw)] += 1
                n += 1
    resolved = {triple: min(counts, key=lambda k: (k.split("|")[2] == "", -counts[k], k))
                for triple, counts in keys.items()}
    causes = Counter()
    changed = 0
    for row in rows(V6 / "hill_person_spine.ndjson.gz"):
        key = row["payee_key"]
        triple = (key["last"], key["first"], key["middle_initial"])
        after = resolved[triple]
        reasons, before, _ = verifier.name_standard_causes(triple, after, ns, table)
        causes.update(reasons)
        changed += after != before
    report = {
        "name_standard_version": ns.NAME_STANDARD_VERSION,
        "key_change": {"cause_histogram": dict(causes), "changed_v1_1_raw_route": changed},
        "payroll_rows": n,
        "method": "v6 spine census and raw payroll triple reconstruction; verifier parser route",
        "sources": [{"path": str(p), "sha256": sha(p)} for _, p in corpora(bindings)],
        "name_standard_sha256": sha(ns.__file__),
    }
    write_json(DELTA, report)
    print(json.dumps(report["key_change"]), flush=True)


def build(bindings, suffix):
    import build_hill_personnel_spine as builder
    report = json.loads(DELTA.read_text())
    if report["name_standard_sha256"] != sha(ns.__file__):
        raise ValueError("Name standard changed after delta; regenerate the census")
    argv = ["--house-ledger-root", str(Path(bindings["house_personnel_observations"]["path"]).parent),
            "--roster-dir", str(Path(bindings["roster:legislators-current.yaml"]["path"]).parent),
            "--sidecar-root", str(Path(bindings["part_a_v2:tiered_person_summary_25340.ndjson.gz"]["path"]).parent),
            "--name-standard", "--name-standard-baseline", str(V6),
            "--name-standard-delta-report", str(DELTA),
            "--output-root", str(HERE / (PREFIX + "_" + suffix)),
            "--generated-at", STAMP, "--rule-version", "hill-personnel-spine-v8",
            # Replicas share the primary batch ID: receipt bytes are also
            # part of the existing deterministic-twin contract.
            "--run-id", "run-20260908-spine-v8-primary", "--no-glassbox"]
    for label in ("nickname_table", "h1_matches", "h2_matches", "senate_matches",
                  "staff_directory", "congestion", "registrant_episodes"):
        argv.extend(["--" + label.replace("_", "-"), bindings[label]["path"]])
    for label, binding in sorted(bindings.items()):
        if label.startswith("senate_payroll_candidates_"):
            argv.extend(["--senate-candidates", binding["path"]])
    return builder.main(argv)


ANNOTATED_TITLE = re.compile(
    r"\b(?:FROM|TO)\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
    r"[A-Z]*\.?\s+(?:[1-9]|[12][0-9]|3[01])\b", re.I)
SUSPECT_PAYROLL_SURNAME = re.compile(
    r"^(?:ADVISOR|ANALYST|ASSISTANT|DIRECTOR|D IRECTOR|MEMBER-REPUBLICAN|"
    r"OF STAFF|OFFICE OF|ROOM DIRECTOR|SECRETARY[.-]|SERGEANT AT ARMS)", re.I)


def senate_signatures(observations, owners):
    """Candidate evidence only; exact source titles paired with their own period.

    owners is keyed by source row id, never a name. The returned groups do not
    change person ids, employment dates, co-tenure edges or canonical flags.
    """
    signatures = defaultdict(list)
    for row in observations:
        owner = owners.get(row.get("candidate_id"))
        title = row.get("title_raw") or ""
        period = row.get("report_period_start")
        if not owner or not period or not ANNOTATED_TITLE.search(title):
            continue
        ident, key, office = owner
        signatures[(key, period, title)].append({
            "spine_person_id": ident, "office_key": office,
            "source_row_id": row["candidate_id"], "payee_raw": row.get("payee_name_raw"),
            "source_pdf_url": row.get("source_pdf_url"), "source_pdf_sha256": row.get("source_pdf_sha256"),
            "page_number": row.get("page_number"), "row_ordinal_on_page": row.get("row_ordinal_on_page"),
            "evidence_quote": row.get("evidence_quote"),
            "parse_status": row.get("parse_status"),
        })
    result = []
    for (key, period, title), evidence in sorted(signatures.items()):
        ids = sorted({e["spine_person_id"] for e in evidence})
        if len(ids) < 2 or len({e["office_key"] for e in evidence}) < 2:
            continue
        result.append({"name_key": key, "report_period_start": period, "title_raw": title,
                       "spine_person_ids": ids, "evidence": sorted(evidence, key=lambda e: e["source_row_id"]),
                       "review_status": "REVIEW_REQUIRED", "identity_merge_authorized": False,
                       "canonical_eligible": False,
                       "basis": "SENATE_EXACT_ANNOTATED_TITLE_SAME_REPORT_PERIOD"})
    return result


def migration_map(old, new):
    legacy_to_new = {}
    for row in new.values():
        for legacy in row["legacy_person_ids"]:
            if legacy in legacy_to_new:
                raise ValueError("Repeated v6 source identity")
            legacy_to_new[legacy] = row["spine_person_id"]
    mapping = []
    source_legacy_ids = [i for row in old.values() for i in row["legacy_person_ids"]]
    if len(source_legacy_ids) != len(set(source_legacy_ids)) or set(source_legacy_ids) != set(legacy_to_new):
        raise ValueError("Migration inputs do not cover the same unique v6 identities")
    for ident, row in sorted(old.items()):
        targets = sorted({legacy_to_new[i] for i in row["legacy_person_ids"]})
        mapping.append({"source_person_id": ident, "target_person_ids": targets,
                        "relation": "SPLIT_REQUIRES_SOURCE_ROW" if len(targets) > 1 else
                                    "UNCHANGED" if targets == [ident] else "REKEYED",
                        "source_generation": V7.name, "target_generation": PREFIX + "_primary",
                        "canonical_eligible": False})
    if {t for r in mapping for t in r["target_person_ids"]} != set(new):
        raise ValueError("Migration map is not total")
    return mapping


def legacy_bridge_handoff(new):
    """Bind the graph's actual Politico inputs to their native v6 identities.

    This bypasses the lossy intermediate v7 merges. It is not a guess about
    which split target inherits an already merged v7 source link.
    """
    mapping = {legacy: r["spine_person_id"] for r in new.values() for legacy in r["legacy_person_ids"]}
    map_path = REVIEW / "spine_id_map_v6_to_v8.ndjson.gz"
    write_rows(map_path, [{"legacy_person_id": legacy, "person_id": target,
                           "reason": "EXACT_V6_OBSERVATION_PARTITION",
                           "source_generation": V6.name, "target_generation": PREFIX + "_primary",
                           "canonical_eligible": False}
                          for legacy, target in sorted(mapping.items())])
    graph_path = HERE / "staffer_social_network_20260907_v6_primary" / "staffer_social_network_receipt.json"
    graph = json.loads(graph_path.read_text())
    bindings = [b for b in graph["inputs"] if b["role"].startswith("politico_")]
    referenced = set()
    def visit(value):
        if isinstance(value, dict):
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
        elif isinstance(value, str) and re.fullmatch(r"hill:person:[0-9a-f]{64}", value):
            referenced.add(value)
    bridge_receipt = None
    for binding in bindings:
        path = Path(binding["path"])
        if sha(path) != binding["sha256"]:
            raise ValueError("Graph-bound Politico input changed: " + str(path))
        if binding["role"] == "politico_direct_link_receipt":
            bridge_receipt = json.loads(path.read_text())
        elif path.suffix == ".gz":
            for row in rows(path):
                visit(row)
    source_sha = sha(V6 / "hill_person_spine.ndjson.gz")
    source_bound = (bridge_receipt is not None and bridge_receipt.get("status") == "PASS"
                    and not bridge_receipt.get("failures") and any(
        Path(path).name == "hill_person_spine.ndjson.gz" and b["sha256"] == source_sha
        for path, b in bridge_receipt["inputs"].items()))
    missing = sorted(referenced - set(mapping))
    proof = {"status": "PASS" if source_bound and not missing else "HOLD",
             "native_source_spine_hash_matches_v6": source_bound,
             "referenced_native_person_ids": len(referenced), "missing_native_person_ids": missing,
             "native_map_rows": len(mapping), "all_referenced_ids_have_one_target": not missing,
             "target_generation": PREFIX + "_primary", "target_person_count": len(new),
             "map_path": str(map_path), "map_sha256": sha(map_path),
             "source_spine_sha256": source_sha, "graph_receipt_sha256": sha(graph_path),
             "politico_inputs": bindings,
             "instruction": "Rebuild graph scores using this native v6-to-v8 map. Do not compose via v7 or copy scores."}
    proof_path = REVIEW / "source_link_remap_receipt.json"
    write_json(proof_path, proof)
    return map_path, proof_path, proof


def review(bindings):
    primary = HERE / (PREFIX + "_primary")
    verified_path = HERE / (PREFIX + "_verification") / verifier.VERIFICATION_FILE
    verification = json.loads(verified_path.read_text())
    if verification["status"] != "PASS" or verification.get("failures") or not all(verification["assertions"].values()):
        raise ValueError("Cannot release unverified spine")
    attestation_path = REVIEW / "verified_release_bindings.json"
    attestation = json.loads(attestation_path.read_text())
    verify_bindings(attestation["files"])
    old = {r["spine_person_id"]: r for r in rows(V7 / "hill_person_spine.ndjson.gz")}
    new = {r["spine_person_id"]: r for r in rows(primary / "hill_person_spine.ndjson.gz")}
    mapping = migration_map(old, new)
    map_path = REVIEW / "spine_id_map_v7_to_v8.ndjson.gz"
    write_rows(map_path, mapping)
    native_map_path, bridge_proof_path, bridge_proof = legacy_bridge_handoff(new)
    owners = {}
    span_count = observations = 0
    for span in rows(primary / "hill_person_office_spans.ndjson.gz"):
        span_count += 1
        observations += span["observation_count"]
        if span["chamber"] != "senate":
            continue
        ident = span["spine_person_id"]
        for row_id in span["source_row_ids"]:
            if row_id in owners:
                raise ValueError("Senate source observation assigned twice")
            owners[row_id] = (ident, new[ident]["name_key"], span["office_key"])
    candidates = senate_signatures((r for chamber, path in corpora(bindings)
                                   if chamber == "senate" for r in rows(path)), owners)
    candidate_path = REVIEW / "senate_title_identity_review.ndjson.gz"
    write_rows(candidate_path, candidates)
    # Suffix conflicts remain explicitly unresolved. No automatic JR/SR split
    # from source text alone: column-shift artifacts also produce suffix conflicts.
    suffixes = [{"spine_person_id": r["spine_person_id"], "name_key": r["name_key"],
                 "suffix_observed": r["suffix_observed"], "payee_raw_examples": r["payee_raw_examples"],
                 "review_status": "REVIEW_REQUIRED", "canonical_eligible": False}
                for r in new.values() if len(r.get("suffix_observed", [])) > 1]
    suffix_path = REVIEW / "suffix_identity_review.ndjson.gz"
    write_rows(suffix_path, sorted(suffixes, key=lambda r: r["spine_person_id"]))
    # These patterns nominate source-parse review, not automatic exclusions.
    # A job-title fragment may have become a surname; preserve the record until
    # its original page is checked instead of stripping arbitrary role words.
    name_issues = [{"spine_person_id": r["spine_person_id"], "name_key": r["name_key"],
                    "payee_raw": r["payee_raw"], "name_standard_parts": r["name_standard_parts"],
                    "review_status": "REVIEW_REQUIRED", "canonical_eligible": False,
                    "basis": "SUSPECT_PAYROLL_TITLE_CONTAMINATION"}
                   for r in new.values()
                   if SUSPECT_PAYROLL_SURNAME.search(r["name_standard_parts"]["last"])]
    name_issues_path = REVIEW / "name_parse_review.ndjson.gz"
    write_rows(name_issues_path, sorted(name_issues, key=lambda r: r["spine_person_id"]))
    def census(people):
        counts = Counter(r["name_key"] for r in people.values())
        return {"people": len(people), "shared_name_keys": sum(n > 1 for n in counts.values()),
                "people_on_shared_name_keys": sum(n for n in counts.values() if n > 1)}
    receipt = {"status": "PASS", "policy": "BOUNDED_NAME_REPAIR_FAIL_CLOSED_UNDATED_MERGES",
               "v7": census(old), "v8": census(new), "office_spans": span_count,
               "source_observations": observations,
               "migration_relations": dict(Counter(r["relation"] for r in mapping)),
               "senate_title_review_groups": len(candidates),
               "senate_title_review_person_ids": len({p for r in candidates for p in r["spine_person_ids"]}),
               "suffix_conflict_review_rows": len(suffixes), "automatic_title_merges": 0,
               "suspect_name_parse_review_rows": len(name_issues),
               "native_source_link_remap_status": bridge_proof["status"],
               "canonical_promotions": 0,
               "sources": [{"path": str(p), "sha256": sha(p)} for p in
                           [V7 / "hill_person_spine.ndjson.gz", primary / "hill_person_spine.ndjson.gz",
                            primary / "hill_personnel_spine_receipt.json", verified_path,
                            map_path, candidate_path, suffix_path, name_issues_path, attestation_path,
                            native_map_path, bridge_proof_path]],
               "generation": primary.name, "verification_generation": PREFIX + "_verification"}
    write_json(REVIEW / "identity_release_receipt.json", receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != "sources"}, indent=2), flush=True)


def verify_bindings(files):
    for path, expected in files.items():
        if sha(path) != expected:
            raise ValueError("Verified artifact changed: " + path)


def verify_release():
    paths = [Path(verifier.__file__), Path(ns.__file__)]
    for suffix in ("primary", "twin"):
        generation = HERE / (PREFIX + "_" + suffix)
        receipt_path = generation / "hill_personnel_spine_receipt.json"
        receipt = json.loads(receipt_path.read_text())
        paths += [receipt_path] + [generation / name for name in receipt["files"]]
    before = {str(path): sha(path) for path in paths}
    result = verifier.main(["--primary-root", str(HERE / (PREFIX + "_primary")),
                            "--twin-root", str(HERE / (PREFIX + "_twin")),
                            "--report-root", str(HERE / (PREFIX + "_verification")),
                            "--run-id", "run-20260908-spine-v8-verification", "--no-glassbox"])
    verify_bindings(before)
    if result == 0:
        proof = HERE / (PREFIX + "_verification") / verifier.VERIFICATION_FILE
        before[str(proof)] = sha(proof)
        write_json(REVIEW / "verified_release_bindings.json", {"status": "PASS", "files": before})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["delta", "primary", "twin", "verify", "review"])
    stage = parser.parse_args().stage
    bindings = inputs()
    if stage == "delta":
        delta(bindings)
    elif stage in {"primary", "twin"}:
        return build(bindings, stage)
    elif stage == "verify":
        return verify_release()
    else:
        review(bindings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
