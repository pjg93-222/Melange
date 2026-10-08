#!/usr/bin/env python3
"""Independent verifier for the direct Politico-to-payroll bridge."""

from __future__ import annotations

try:
    from .politico_completion_contract import completion_accepted, validate_browser_exception, SOURCE_EXCEPTION_POLICY
except ImportError:
    from politico_completion_contract import completion_accepted, validate_browser_exception, SOURCE_EXCEPTION_POLICY


import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable


def rows(path: Path) -> Iterable[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def tokens(value: Any) -> list[str]:
    folded = unicodedata.normalize("NFKD", str(value or ""))
    folded = folded.encode("ascii", "ignore").decode().upper().replace("&", " AND ")
    return re.findall(r"[A-Z0-9]+", folded)


def card_key(name: str) -> tuple[str, str] | None:
    parts = [part for part in tokens(name) if part not in {"JR", "SR", "II", "III", "IV"}]
    return (parts[0].casefold(), parts[-1].casefold()) if len(parts) >= 2 else None


def spine_key(value: dict[str, Any]) -> tuple[str, str] | None:
    first, last = tokens(value.get("first")), tokens(value.get("last"))
    return (first[0].casefold(), last[-1].casefold()) if first and last else None


def committee_key(value: str) -> str:
    raw = str(value or "")
    parent = re.match(
        r"^(.*?\bCommittee)\b.*\b(?:Subcommittee|Task Force|Working Group)\b", raw, re.I
    )
    if parent:
        raw = parent.group(1)
    text = " ".join(tokens(raw))
    text = re.sub(r"^FISCAL YEAR \d{4} ", "", text)
    text = re.sub(r"^(HOUSE|SENATE) ", "", text)
    text = re.sub(r"\b(PERMANENT|SELECT|SPECIAL|COMMITTEE|COMM|ON|THE)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return {
        "OVERSIGHT AND GOVERNMENT REFORM": "OVERSIGHT AND ACCOUNTABILITY",
        "TRANSPORTATION AND INFRASTRUCTURE": "TRANSPORTATION INFRASTRUCTURE",
        "SCIENCE SPACE AND TECHNOLOGY": "SCIENCE SPACE AND TECH",
        "STRATEGIC COMPETITION BETWEEN UNITED STATES AND CHINESE COMMUNIST PARTY":
            "COMPETITION US AND CHINA",
    }.get(text, text)


def source_side(value: Any) -> str | None:
    label = " ".join(tokens(value))
    if "BIPARTISAN" in label or "NONPARTISAN" in label:
        return "BIPARTISAN"
    if "MAJORITY" in label or label == "MAJ":
        return "MAJ"
    if "MINORITY" in label or label == "MIN":
        return "MIN"
    return None


def main(args: argparse.Namespace) -> int:
    generation = Path(args.generation).resolve()
    twin = Path(args.twin).resolve()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    raw = Path(args.raw_directory).resolve()
    spine = Path(args.spine).resolve()
    spans = Path(args.spans).resolve()
    roster_path = Path(args.roster).resolve()
    profiles_path = Path(args.profile_histories).resolve() if args.profile_histories else None
    verification_path = (
        Path(args.profile_crawl_verification).resolve()
        if args.profile_crawl_verification
        else None
    )
    failures: list[str] = []
    if bool(profiles_path) != bool(verification_path):
        failures.append("profile histories and crawl verification must be supplied together")
    if args.require_complete_profile_crawl and profiles_path is None:
        failures.append("terminal profile crawl requested without profile inputs")

    names = [
        "politico_payroll_direct_links.ndjson.gz",
        "politico_policy_memberships.ndjson.gz",
        "politico_current_committee_assertions.ndjson.gz",
        "politico_payroll_direct_link_receipt.json",
    ]
    if profiles_path is not None:
        names.extend(
            [
                "politico_profile_employment_assertions.ndjson.gz",
                "politico_profile_education_assertions.ndjson.gz",
                "politico_profile_policy_deltas.ndjson.gz",
                "politico_explicit_committee_side_assertions.ndjson.gz",
            ]
        )
    twin_matches = {}
    for name in names:
        left, right = generation / name, twin / name
        same = left.exists() and right.exists() and left.read_bytes() == right.read_bytes()
        twin_matches[name] = same
        if not same:
            failures.append(f"twin mismatch: {name}")

    person_names: dict[str, tuple[str, str]] = {}
    for row in rows(spine):
        key = spine_key(row.get("payee_key") or {})
        if key:
            person_names[str(row["spine_person_id"])] = key

    member_index: dict[tuple[str, tuple[str, str]], set[str]] = defaultdict(set)
    committee_index: dict[tuple[str, str, tuple[str, str]], set[str]] = defaultdict(set)
    committee_offices: dict[tuple[str, str, tuple[str, str], str], set[str]] = defaultdict(set)
    for row in rows(spans):
        if row.get("status") != "current":
            continue
        pid = str(row["spine_person_id"])
        key = person_names.get(pid)
        if not key:
            continue
        if row.get("container_kind") == "member_office" and row.get("member_bioguide"):
            member_index[(str(row["member_bioguide"]), key)].add(pid)
        elif row.get("container_kind") == "committee":
            chamber = str(row["chamber"])
            signature = committee_key(row["office_key"])
            committee_index[(chamber, signature, key)].add(pid)
            committee_offices[(chamber, signature, key, pid)].add(str(row["office_key"]))

    marker_rows = []
    for row in json.loads(roster_path.read_text(encoding="utf-8")):
        chamber = str(row.get("chamber") or "").casefold()
        prefix = "Rep." if chamber == "house" else "Sen." if chamber == "senate" else ""
        if prefix and row.get("member") and row.get("bioguide"):
            marker_rows.append((prefix, str(row["member"]), str(row["bioguide"])))
    marker_rows.sort(key=lambda value: (-len(value[1]), value[2]))

    source = {str(row["profile_uuid"]): row for row in rows(raw)}
    emitted = list(rows(generation / "politico_payroll_direct_links.ndjson.gz"))
    if len(emitted) != len(source):
        failures.append(f"link row census {len(emitted)} != source census {len(source)}")
    if len({row["source_profile_uuid"] for row in emitted}) != len(emitted):
        failures.append("duplicate profile UUID in link output")

    linked: dict[str, str] = {}
    expected_committee: set[tuple[str, str, str, str, tuple[str, ...]]] = set()
    status_counts = Counter()
    for link in emitted:
        uuid = str(link["source_profile_uuid"])
        profile = source.get(uuid)
        if profile is None:
            failures.append(f"unknown source profile {uuid}")
            continue
        key = card_key(profile["name"])
        candidates: set[str] = set()
        member_roles = []
        committee_roles = []
        for role in profile.get("roles") or []:
            role = str(role)
            if re.search(r"\bfor\s+(?:Rep\.|Sen\.)\s+", role, re.I):
                for prefix, member, bioguide in marker_rows:
                    if f"for {prefix} {member}" in role:
                        member_roles.append((bioguide, role))
                        break
            match = re.search(
                r"\bfor\s+((?:House|Senate)\s+.*(?:Committee|Commission).*)$", role, re.I
            )
            if match:
                employer = match.group(1).strip()
                chamber = "house" if employer.casefold().startswith("house ") else "senate"
                committee_roles.append((chamber, committee_key(employer), role))
        if key:
            for bioguide, _role in member_roles:
                candidates.update(member_index.get((bioguide, key), set()))
            for chamber, committee, _role in committee_roles:
                candidates.update(committee_index.get((chamber, committee, key), set()))
        expected_status = (
            "NAME_UNUSABLE" if not key else
            "LINKED" if len(candidates) == 1 else
            "AMBIGUOUS" if len(candidates) > 1 else
            "NOT_ON_CURRENT_PAYROLL" if member_roles or committee_roles else
            "NO_SUPPORTED_CURRENT_ROLE"
        )
        if link.get("status") != expected_status:
            failures.append(f"status mismatch for {uuid}: {link.get('status')} != {expected_status}")
        expected_pid = next(iter(candidates)) if expected_status == "LINKED" else None
        if link.get("spine_person_id") != expected_pid:
            failures.append(f"person mismatch for {uuid}")
        status_counts[expected_status] += 1
        if expected_pid:
            linked[uuid] = expected_pid
            for chamber, committee, role in committee_roles:
                if expected_pid in committee_index.get((chamber, committee, key), set()):
                    expected_committee.add(
                        (
                            uuid,
                            expected_pid,
                            chamber,
                            committee + "\0" + role,
                            tuple(sorted(committee_offices.get((chamber, committee, key, expected_pid), set()))),
                        )
                    )

    expected_policy = {
        (uuid, pid, str(issue).strip())
        for uuid, pid in linked.items()
        for issue in source[uuid].get("issue_areas") or []
    }
    actual_policy = {
        (str(row["source_profile_uuid"]), str(row["spine_person_id"]), str(row["issue_area"]))
        for row in rows(generation / "politico_policy_memberships.ndjson.gz")
    }
    if actual_policy != expected_policy:
        failures.append(
            f"policy membership mismatch: actual={len(actual_policy)} expected={len(expected_policy)}"
        )

    actual_committee_rows = list(
        rows(generation / "politico_current_committee_assertions.ndjson.gz")
    )
    actual_committee = {
        (
            str(row["source_profile_uuid"]), str(row["spine_person_id"]), str(row["chamber"]),
            str(row["committee_signature"]) + "\0" + str(row["role"]),
            tuple(sorted(str(value) for value in row.get("payroll_office_keys") or [])),
        )
        for row in actual_committee_rows
    }
    if actual_committee != expected_committee:
        failures.append(
            f"committee assertion mismatch: actual={len(actual_committee)} expected={len(expected_committee)}"
        )

    profile_counts = {
        "profile_history_rows": 0,
        "profile_employment_assertions": 0,
        "profile_education_assertions": 0,
        "profile_policy_deltas": 0,
        "explicit_committee_side_assertions": 0,
    }
    if profiles_path is not None and verification_path is not None:
        if not profiles_path.exists() or not verification_path.exists():
            failures.append("profile history input is missing")
        else:
            profiles_list = list(rows(profiles_path))
            profiles = {str(row.get("profile_uuid") or ""): row for row in profiles_list}
            if "" in profiles or len(profiles) != len(profiles_list):
                failures.append("profile histories contain missing or duplicate UUIDs")
            unexpected = sorted(set(profiles) - set(source))
            if unexpected:
                failures.append(f"profile UUID outside sealed directory: {unexpected[:5]}")
            verification = json.loads(verification_path.read_text(encoding="utf-8"))
            coverage = (verification.get("coverage") or {}).get("all_profiles") or {}
            crawl_state = verification.get("crawl_state") or {}
            integrity_status = verification.get(
                "integrity_status",
                "PASS" if verification.get("status") == "PASS" else verification.get("status"),
            )
            if (
                integrity_status != "PASS"
                or verification.get("status") not in {"PASS", "IN_PROGRESS"}
                or int(verification.get("verification_failure_count") or 0)
            ):
                failures.append("profile crawl verification is not clean PASS")
            declared = verification.get("counts") or {}
            if int(declared.get("profile_rows") or 0) != len(profiles_list):
                failures.append("profile crawl receipt row count mismatch")
            if int(declared.get("unique_profiles_collected") or 0) != len(profiles):
                failures.append("profile crawl receipt unique count mismatch")
            if args.require_complete_profile_crawl:
                expected_n = int(coverage.get("expected") or 0)
                if not (
                    expected_n
                    and verification.get("status") == "PASS"
                    and completion_accepted(verification, legacy_default=True)
                    and (verification.get("completion_gate") or {}).get("status", "PASS")
                    == "PASS"
                    and int(coverage.get("completed") or 0) == expected_n
                    and int(coverage.get("unresolved") or 0) == 0
                    and int(crawl_state.get("queue_total") or 0) == expected_n
                    and int(crawl_state.get("total_succeeded") or 0) == expected_n
                    and int(crawl_state.get("total_failed") or 0) == 0
                    and int(crawl_state.get("remaining") or 0) == 0
                    and not bool(crawl_state.get("halted"))
                    and set(profiles) == set(source)
                ):
                    failures.append("terminal full-profile completion gate failed")

            actual_employment = list(
                rows(generation / "politico_profile_employment_assertions.ndjson.gz")
            )
            actual_education = list(
                rows(generation / "politico_profile_education_assertions.ndjson.gz")
            )
            actual_deltas = list(rows(generation / "politico_profile_policy_deltas.ndjson.gz"))
            actual_sides = list(
                rows(generation / "politico_explicit_committee_side_assertions.ndjson.gz")
            )
            profile_counts.update(
                {
                    "profile_history_rows": len(profiles),
                    "profile_employment_assertions": len(actual_employment),
                    "profile_education_assertions": len(actual_education),
                    "profile_policy_deltas": len(actual_deltas),
                    "explicit_committee_side_assertions": len(actual_sides),
                }
            )
            expected_employment = {
                (
                    uuid,
                    ordinal,
                    str(item.get("employer") or "").strip(),
                    str(item.get("title") or "").strip(),
                    str(item.get("date_text") or "").strip(),
                    linked.get(uuid),
                )
                for uuid, profile in profiles.items()
                for ordinal, item in enumerate(profile.get("employment_history") or [], 1)
            }
            observed_employment = {
                (
                    str(row.get("source_profile_uuid")),
                    int(row.get("history_ordinal") or 0),
                    str(row.get("employer") or ""),
                    str(row.get("title") or ""),
                    str(row.get("date_text") or ""),
                    row.get("spine_person_id"),
                )
                for row in actual_employment
            }
            if observed_employment != expected_employment or len(actual_employment) != len(expected_employment):
                failures.append(
                    "employment history mismatch: "
                    f"actual={len(actual_employment)} expected={len(expected_employment)}"
                )
            expected_education = {
                (
                    uuid,
                    ordinal,
                    str(item.get("institution") or "").strip(),
                    str(item.get("degree") or "").strip(),
                    str(item.get("date_text") or "").strip(),
                    linked.get(uuid),
                )
                for uuid, profile in profiles.items()
                for ordinal, item in enumerate(profile.get("education") or [], 1)
            }
            observed_education = {
                (
                    str(row.get("source_profile_uuid")),
                    int(row.get("history_ordinal") or 0),
                    str(row.get("institution") or ""),
                    str(row.get("degree") or ""),
                    str(row.get("date_text") or ""),
                    row.get("spine_person_id"),
                )
                for row in actual_education
            }
            if observed_education != expected_education or len(actual_education) != len(expected_education):
                failures.append(
                    f"education history mismatch: actual={len(actual_education)} expected={len(expected_education)}"
                )

            expected_deltas = set()
            for uuid, profile in profiles.items():
                if profile.get("identity_status") == "PROFILE_UNAVAILABLE_404":
                    continue
                card_issues = {str(x).strip() for x in source[uuid].get("issue_areas") or [] if str(x).strip()}
                live_issues = {
                    str(x).strip() for x in profile.get("profile_issue_areas") or [] if str(x).strip()
                }
                expected_deltas.update((uuid, issue, "PROFILE_ONLY_ADDITION") for issue in live_issues - card_issues)
                expected_deltas.update((uuid, issue, "CARD_ONLY_REMOVAL") for issue in card_issues - live_issues)
            observed_deltas = {
                (str(row.get("source_profile_uuid")), str(row.get("issue_area")), str(row.get("delta")))
                for row in actual_deltas
            }
            if observed_deltas != expected_deltas or len(actual_deltas) != len(expected_deltas):
                failures.append(
                    f"policy delta mismatch: actual={len(actual_deltas)} expected={len(expected_deltas)}"
                )

            committee_by_uuid: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in actual_committee_rows:
                committee_by_uuid[str(row["source_profile_uuid"])].append(row)
            expected_sides = set()
            for uuid, profile in profiles.items():
                labels = sorted({str(x).strip() for x in profile.get("explicit_side_labels") or [] if str(x).strip()})
                if not labels:
                    continue
                mapped = sorted({side for side in (source_side(x) for x in labels) if side})
                assertions = committee_by_uuid.get(uuid, [])
                if len(mapped) == 1 and assertions:
                    for row in assertions:
                        expected_sides.add(
                            (
                                uuid,
                                str(row["chamber"]),
                                str(row["committee_signature"]),
                                str(row["role"]),
                                mapped[0],
                                "PROFILE_SINGLE_SIDE_TO_MATCHED_CURRENT_COMMITTEE",
                            )
                        )
                else:
                    expected_sides.add(
                        (
                            uuid,
                            "",
                            "",
                            "",
                            mapped[0] if len(mapped) == 1 else "",
                            "NO_MATCHED_CURRENT_COMMITTEE"
                            if not assertions
                            else "AMBIGUOUS_OR_UNCLASSIFIED_PROFILE_SIDE_LABEL",
                        )
                    )
            observed_sides = {
                (
                    str(row.get("source_profile_uuid")),
                    str(row.get("chamber") or ""),
                    str(row.get("committee_signature") or ""),
                    str(row.get("role") or ""),
                    str(row.get("explicit_side") or ""),
                    str(row.get("mapping_status")),
                )
                for row in actual_sides
            }
            if observed_sides != expected_sides or len(actual_sides) != len(expected_sides):
                failures.append(
                    f"explicit side mismatch: actual={len(actual_sides)} expected={len(expected_sides)}"
                )
            for row in actual_employment + actual_education + actual_deltas + actual_sides:
                if (
                    row.get("canonical_eligible") is not False
                    or row.get("canonical_identity_promoted") is not False
                    or row.get("canonical_employment_promoted") is not False
                ):
                    failures.append("profile review layer promotion tripwire fired")
                    break

    receipt = json.loads((generation / "politico_payroll_direct_link_receipt.json").read_text(encoding="utf-8"))
    for name, metadata in receipt.get("files", {}).items():
        path = generation / name
        if digest(path) != metadata.get("sha256"):
            failures.append(f"receipt hash mismatch: {name}")
    if receipt.get("canonical_identity_promotions") != 0 or receipt.get("canonical_employment_promotions") != 0:
        failures.append("promotion tripwire fired")
    if receipt.get("counts", {}).get("status") != dict(sorted(status_counts.items())):
        failures.append("receipt status counts do not rederive")
    for key, expected_value in profile_counts.items():
        if int(receipt.get("counts", {}).get(key) or 0) != expected_value:
            failures.append(
                f"receipt {key} mismatch: {receipt.get('counts', {}).get(key)} != {expected_value}"
            )
    declared_inputs = receipt.get("inputs") or {}
    for path in (profiles_path, verification_path):
        if path is None:
            continue
        metadata = declared_inputs.get(str(path))
        if not metadata or metadata.get("sha256") != digest(path):
            failures.append(f"receipt profile input hash mismatch: {path}")

    report = {
        "schema_id": "staffer-network-politico-payroll-direct-link-verification-v2",
        "status": "PASS" if not failures else "FAIL",
        "generation": str(generation),
        "twin": str(twin),
        "twin_byte_identical": twin_matches,
        "profiles_rederived": len(source),
        "linked_profiles_rederived": len(linked),
        "policy_memberships_rederived": len(expected_policy),
        "committee_assertions_rederived": len(expected_committee),
        "profile_review_layers_rederived": profile_counts,
        "promotion_tripwire": 0,
        "failures": failures[:100],
    }
    report_path = out / "verification_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--generation", required=True)
    ap.add_argument("--twin", required=True)
    ap.add_argument("--raw-directory", required=True)
    ap.add_argument("--spine", required=True)
    ap.add_argument("--spans", required=True)
    ap.add_argument("--roster", required=True)
    ap.add_argument("--profile-histories")
    ap.add_argument("--profile-crawl-verification")
    ap.add_argument("--require-complete-profile-crawl", action="store_true")
    ap.add_argument("--output", required=True)
    return ap


if __name__ == "__main__":
    raise SystemExit(main(parser().parse_args()))
