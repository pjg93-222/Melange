#!/usr/bin/env python3
"""Build a strict current-snapshot Politico Pro -> payroll-spine bridge.

The original Politico policy layer reached the payroll spine through the much
smaller legacy staff directory.  This builder uses the source-native Politico
card itself: an exact normalized first/last name must agree with a current
payroll person in the exact Member office or exact committee employer printed
on the card.  Ambiguity fails closed.  The result remains review-only and the
current directory observation is never promoted into a historical interval.
"""

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


SCHEMA_ID = "staffer-network-politico-payroll-direct-link-v1"
RECEIPT_SCHEMA_ID = "staffer-network-politico-payroll-direct-link-receipt-v2"
RULE_VERSION = "politico-payroll-exact-name-office-v2"
EMPLOYMENT_SCHEMA_ID = "staffer-network-politico-profile-employment-assertion-v1"
EDUCATION_SCHEMA_ID = "staffer-network-politico-profile-education-assertion-v1"
POLICY_DELTA_SCHEMA_ID = "staffer-network-politico-profile-policy-delta-v1"
EXPLICIT_SIDE_SCHEMA_ID = "staffer-network-politico-explicit-committee-side-v1"

SUFFIXES = {"JR", "SR", "II", "III", "IV"}
PERSONAL_ROLE_RE = re.compile(r"\bfor\s+(Rep\.|Sen\.)\s+", re.I)
COMMITTEE_ROLE_RE = re.compile(
    r"\bfor\s+((?:House|Senate)\s+.*(?:Committee|Commission).*)$", re.I
)


class BuildError(RuntimeError):
    pass


def ascii_tokens(value: Any) -> list[str]:
    folded = unicodedata.normalize("NFKD", str(value or ""))
    folded = folded.encode("ascii", "ignore").decode().upper().replace("&", " AND ")
    return re.findall(r"[A-Z0-9]+", folded)


def display_name_key(value: str) -> tuple[str, str] | None:
    tokens = [token for token in ascii_tokens(value) if token not in SUFFIXES]
    if len(tokens) < 2:
        return None
    return tokens[0].casefold(), tokens[-1].casefold()


def payee_name_key(payee_key: dict[str, Any]) -> tuple[str, str] | None:
    first = ascii_tokens(payee_key.get("first"))
    last = ascii_tokens(payee_key.get("last"))
    if not first or not last:
        return None
    return first[0].casefold(), last[-1].casefold()


def committee_signature(value: str) -> str:
    """Normalize only source-documented committee vocabulary differences."""
    raw = str(value or "")
    parent = re.match(
        r"^(.*?\bCommittee)\b.*\b(?:Subcommittee|Task Force|Working Group)\b",
        raw,
        re.I,
    )
    if parent:
        raw = parent.group(1)
    text = " ".join(ascii_tokens(raw))
    text = re.sub(r"^FISCAL YEAR \d{4} ", "", text)
    text = re.sub(r"^(HOUSE|SENATE) ", "", text)
    # A subcommittee card is paid through its parent committee in the payroll.
    text = re.split(
        r" (?:SUBCOMMITTEE|TASK FORCE|WORKING GROUP|INVESTIGATIVE SUBCOMMITTEE)\b",
        text,
    )[0]
    text = re.sub(r"\b(PERMANENT|SELECT|SPECIAL)\b", " ", text)
    text = re.sub(r"\b(COMMITTEE|COMM)\b", " ", text)
    text = re.sub(r"\b(ON|THE)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    aliases = {
        # The committee changed its display name between payroll vintages.
        "OVERSIGHT AND GOVERNMENT REFORM": "OVERSIGHT AND ACCOUNTABILITY",
        # Punctuation/abbreviation differences in the official House lane.
        "TRANSPORTATION AND INFRASTRUCTURE": "TRANSPORTATION INFRASTRUCTURE",
        "SCIENCE SPACE AND TECHNOLOGY": "SCIENCE SPACE AND TECH",
        # Politico and payroll use different shortened names for this select panel.
        "STRATEGIC COMPETITION BETWEEN UNITED STATES AND CHINESE COMMUNIST PARTY":
            "COMPETITION US AND CHINA",
    }
    return aliases.get(text, text)


def canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def read_rows(path: Path) -> Iterable[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                raise BuildError(f"blank line in {path}:{line_number}")
            row = json.loads(line)
            if not isinstance(row, dict):
                raise BuildError(f"non-object in {path}:{line_number}")
            yield row


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def explicit_side(value: Any) -> str | None:
    """Map a source-visible profile label without inferring from party.

    These values are deliberately kept separate from the existing party-derived
    point-observation side.  Unknown labels remain unclassified rather than being
    silently forced into a side.
    """
    label = " ".join(ascii_tokens(value))
    if "BIPARTISAN" in label or "NONPARTISAN" in label:
        return "BIPARTISAN"
    if "MAJORITY" in label or label == "MAJ":
        return "MAJ"
    if "MINORITY" in label or label == "MIN":
        return "MIN"
    return None


def validate_profile_crawl(
    profiles: dict[str, dict[str, Any]], verification: dict[str, Any], *, require_complete: bool
) -> dict[str, Any]:
    """Validate the independently written crawl receipt before consuming histories."""
    status = verification.get("status")
    integrity_status = verification.get("integrity_status", "PASS" if status == "PASS" else status)
    if integrity_status != "PASS" or status not in {"PASS", "IN_PROGRESS"}:
        raise BuildError("profile crawl verification integrity is not PASS")
    if int(verification.get("verification_failure_count") or 0) != 0:
        raise BuildError("profile crawl verification contains failures")
    counts = verification.get("counts") or {}
    coverage = (verification.get("coverage") or {}).get("all_profiles") or {}
    state = verification.get("crawl_state") or {}
    declared_rows = int(counts.get("profile_rows") or 0)
    declared_unique = int(counts.get("unique_profiles_collected") or 0)
    if declared_rows != len(profiles) or declared_unique != len(profiles):
        raise BuildError(
            "profile crawl receipt census disagrees with profiles input: "
            f"rows={declared_rows} unique={declared_unique} actual={len(profiles)}"
        )
    if require_complete:
        expected = int(coverage.get("expected") or 0)
        completed = int(coverage.get("completed") or 0)
        unresolved = int(coverage.get("unresolved") or 0)
        if not expected or completed != expected or unresolved != 0:
            raise BuildError(
                "full profile crawl required: "
                f"completed={completed} expected={expected} unresolved={unresolved}"
            )
        if (
            status != "PASS"
            or not completion_accepted(verification, legacy_default=True)
            or (verification.get("completion_gate") or {}).get("status", "PASS") != "PASS"
        ):
            raise BuildError("full profile crawl verification completion gate is not PASS")
        if (
            int(state.get("queue_total") or 0) != expected
            or int(state.get("total_succeeded") or 0) != expected
            or int(state.get("total_failed") or 0) != 0
            or int(state.get("remaining") or 0) != 0
            or bool(state.get("halted"))
        ):
            raise BuildError("full profile crawl state does not satisfy the terminal completion gate")
    return {
        "status": status,
        "integrity_status": integrity_status,
        "completion_status": verification.get("completion_status"),
        "source_exception_verification": verification.get("source_exception_verification"),
        "profile_rows": declared_rows,
        "expected_profiles": int(coverage.get("expected") or 0),
        "completed_profiles": int(coverage.get("completed") or 0),
        "unresolved_profiles": int(coverage.get("unresolved") or 0),
        "verification_failure_count": int(verification.get("verification_failure_count") or 0),
        "terminal_completion_required": require_complete,
    }


def write_gzip(path: Path, rows: Iterable[dict[str, Any]]) -> tuple[int, str, int]:
    count = 0
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            for row in rows:
                zipped.write(canonical_json(row))
                count += 1
    return count, sha256_file(path), path.stat().st_size


def roster_markers(roster: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    markers: list[tuple[str, str, str]] = []
    for row in roster:
        chamber = str(row.get("chamber") or "").casefold()
        prefix = "Rep." if chamber == "house" else "Sen." if chamber == "senate" else ""
        member = str(row.get("member") or "").strip()
        bioguide = str(row.get("bioguide") or "").strip()
        if prefix and member and bioguide:
            markers.append((prefix, member, bioguide))
    # Longest first prevents a short display name from shadowing a longer one.
    markers.sort(key=lambda item: (-len(item[1]), item[2]))
    return markers


def member_bioguides_from_roles(
    roles: list[str], markers: list[tuple[str, str, str]]
) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for role in roles:
        if not PERSONAL_ROLE_RE.search(role):
            continue
        for prefix, member, bioguide in markers:
            if f"for {prefix} {member}" in role:
                found.append((bioguide, role))
                break
    return found


def committees_from_roles(roles: list[str]) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    for role in roles:
        match = COMMITTEE_ROLE_RE.search(role)
        if not match:
            continue
        employer = match.group(1).strip()
        chamber = "house" if employer.casefold().startswith("house ") else "senate"
        found.append((chamber, committee_signature(employer), role))
    return found


def run(args: argparse.Namespace) -> dict[str, Any]:
    out = Path(args.output).resolve()
    if out.exists() and any(out.iterdir()):
        raise BuildError(f"output directory is not empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    raw_directory = Path(args.raw_directory).resolve()
    crawl_receipt_path = Path(args.crawl_receipt).resolve()
    spine_path = Path(args.spine).resolve()
    spans_path = Path(args.spans).resolve()
    roster_path = Path(args.roster).resolve()
    profiles_path = Path(args.profile_histories).resolve() if args.profile_histories else None
    profile_verification_path = (
        Path(args.profile_crawl_verification).resolve()
        if args.profile_crawl_verification
        else None
    )
    if bool(profiles_path) != bool(profile_verification_path):
        raise BuildError(
            "--profile-histories and --profile-crawl-verification must be supplied together"
        )
    if args.require_complete_profile_crawl and profiles_path is None:
        raise BuildError("--require-complete-profile-crawl requires profile crawl inputs")
    required_paths = [raw_directory, crawl_receipt_path, spine_path, spans_path, roster_path]
    if profiles_path is not None and profile_verification_path is not None:
        required_paths.extend((profiles_path, profile_verification_path))
    for path in required_paths:
        if not path.exists():
            raise BuildError(f"missing input: {path}")

    crawl_receipt = json.loads(crawl_receipt_path.read_text(encoding="utf-8"))
    observed_at = str(crawl_receipt.get("generated_at") or "")
    roster = json.loads(roster_path.read_text(encoding="utf-8"))
    if not isinstance(roster, list):
        raise BuildError("roster must be a JSON list")
    markers = roster_markers(roster)

    profiles: dict[str, dict[str, Any]] = {}
    profile_crawl_gate: dict[str, Any] | None = None
    if profiles_path is not None and profile_verification_path is not None:
        for profile in read_rows(profiles_path):
            uuid = str(profile.get("profile_uuid") or "")
            if not uuid:
                raise BuildError("profile history row missing profile_uuid")
            if uuid in profiles:
                raise BuildError(f"duplicate profile history UUID: {uuid}")
            profiles[uuid] = profile
        verification = json.loads(profile_verification_path.read_text(encoding="utf-8"))
        profile_crawl_gate = validate_profile_crawl(
            profiles, verification, require_complete=bool(args.require_complete_profile_crawl)
        )

    person_name: dict[str, tuple[str, str]] = {}
    for row in read_rows(spine_path):
        key = payee_name_key(row.get("payee_key") or {})
        if key:
            person_name[str(row["spine_person_id"])] = key

    member_index: dict[tuple[str, tuple[str, str]], set[str]] = defaultdict(set)
    committee_index: dict[tuple[str, str, tuple[str, str]], set[str]] = defaultdict(set)
    committee_offices: dict[tuple[str, str, tuple[str, str], str], set[str]] = defaultdict(set)
    current_member_offices: set[str] = set()
    current_committee_signatures: set[tuple[str, str]] = set()
    for row in read_rows(spans_path):
        if row.get("status") != "current":
            continue
        person_id = str(row["spine_person_id"])
        key = person_name.get(person_id)
        if not key:
            continue
        kind = row.get("container_kind")
        if kind == "member_office" and row.get("member_bioguide"):
            bioguide = str(row["member_bioguide"])
            member_index[(bioguide, key)].add(person_id)
            current_member_offices.add(bioguide)
        elif kind == "committee":
            chamber = str(row["chamber"])
            signature = committee_signature(str(row["office_key"]))
            committee_index[(chamber, signature, key)].add(person_id)
            committee_offices[(chamber, signature, key, person_id)].add(str(row["office_key"]))
            current_committee_signatures.add((chamber, signature))

    member_control_order = sorted(current_member_offices)
    member_control_pos = {value: index for index, value in enumerate(member_control_order)}
    committee_control_order: dict[str, list[str]] = defaultdict(list)
    for chamber, signature in sorted(current_committee_signatures):
        committee_control_order[chamber].append(signature)
    committee_control_pos = {
        (chamber, signature): index
        for chamber, values in committee_control_order.items()
        for index, signature in enumerate(values)
    }

    link_rows: list[dict[str, Any]] = []
    policy_rows: list[dict[str, Any]] = []
    committee_rows: list[dict[str, Any]] = []
    employment_rows: list[dict[str, Any]] = []
    education_rows: list[dict[str, Any]] = []
    policy_delta_rows: list[dict[str, Any]] = []
    explicit_side_rows: list[dict[str, Any]] = []
    status_counts = Counter()
    method_counts = Counter()
    party_counts = Counter()
    profile_count = 0
    issue_profile_count = 0
    issue_assertion_count = 0
    ambiguous_examples: list[dict[str, Any]] = []
    control_eligible_profiles = 0
    control_hit_profiles = 0
    source_cards: dict[str, dict[str, Any]] = {}
    link_status_by_uuid: dict[str, tuple[str, str | None]] = {}
    committee_assertions_by_uuid: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for profile in read_rows(raw_directory):
        profile_count += 1
        uuid = str(profile["profile_uuid"])
        if uuid in source_cards:
            raise BuildError(f"duplicate source directory UUID: {uuid}")
        source_cards[uuid] = profile
        display_name = str(profile["name"])
        roles = [str(value) for value in profile.get("roles") or []]
        issues = sorted({str(value).strip() for value in profile.get("issue_areas") or []})
        if issues:
            issue_profile_count += 1
            issue_assertion_count += len(issues)
        name_key = display_name_key(display_name)
        member_evidence = member_bioguides_from_roles(roles, markers)
        committee_evidence = committees_from_roles(roles)

        candidates: set[str] = set()
        evidence_by_person: dict[str, list[dict[str, str]]] = defaultdict(list)
        if name_key:
            for bioguide, role in member_evidence:
                for person_id in member_index.get((bioguide, name_key), set()):
                    candidates.add(person_id)
                    evidence_by_person[person_id].append(
                        {"basis": "EXACT_NAME_MEMBER_OFFICE", "office_key": bioguide, "role": role}
                    )

        if name_key and (member_evidence or committee_evidence):
            control_eligible_profiles += 1
            control_candidates: set[str] = set()
            if len(member_control_order) > 1:
                for bioguide, _role in member_evidence:
                    position = member_control_pos.get(bioguide)
                    if position is None:
                        continue
                    false_bioguide = member_control_order[(position + 1) % len(member_control_order)]
                    control_candidates.update(member_index.get((false_bioguide, name_key), set()))
            for chamber, signature, _role in committee_evidence:
                order = committee_control_order.get(chamber, [])
                position = committee_control_pos.get((chamber, signature))
                if position is None or len(order) <= 1:
                    continue
                false_signature = order[(position + 1) % len(order)]
                control_candidates.update(
                    committee_index.get((chamber, false_signature, name_key), set())
                )
            if control_candidates:
                control_hit_profiles += 1
            for chamber, signature, role in committee_evidence:
                for person_id in committee_index.get((chamber, signature, name_key), set()):
                    candidates.add(person_id)
                    evidence_by_person[person_id].append(
                        {
                            "basis": "EXACT_NAME_COMMITTEE_EMPLOYER",
                            "office_key": f"{chamber}:{signature}",
                            "role": role,
                        }
                    )

        if not name_key:
            status = "NAME_UNUSABLE"
        elif len(candidates) == 1:
            status = "LINKED"
        elif len(candidates) > 1:
            status = "AMBIGUOUS"
        elif member_evidence or committee_evidence:
            status = "NOT_ON_CURRENT_PAYROLL"
        else:
            status = "NO_SUPPORTED_CURRENT_ROLE"
        status_counts[status] += 1

        person_id = next(iter(candidates)) if status == "LINKED" else None
        link_status_by_uuid[uuid] = (status, person_id)
        evidence = sorted(
            evidence_by_person.get(person_id, []),
            key=lambda item: (item["basis"], item["office_key"], item["role"]),
        )
        methods = sorted({item["basis"] for item in evidence})
        for method in methods:
            method_counts[method] += 1
        if status == "AMBIGUOUS" and len(ambiguous_examples) < 25:
            ambiguous_examples.append(
                {"source_profile_uuid": uuid, "display_name": display_name, "candidate_count": len(candidates)}
            )

        link_rows.append(
            {
                "schema_id": SCHEMA_ID,
                "rule_version": RULE_VERSION,
                "source_profile_uuid": uuid,
                "display_name": display_name,
                "party_partition": profile.get("partition"),
                "observed_at": observed_at,
                "status": status,
                "spine_person_id": person_id,
                "candidate_count": len(candidates),
                "match_methods": methods,
                "evidence": evidence,
                "review_status": "REVIEW_REQUIRED",
                "canonical_identity_promoted": False,
                "canonical_employment_promoted": False,
            }
        )

        if status != "LINKED" or person_id is None:
            continue
        for issue in issues:
            policy_rows.append(
                {
                    "source_profile_uuid": uuid,
                    "spine_person_id": person_id,
                    "issue_area": issue,
                    "observed_at": observed_at,
                    "duration_weight": 0.0,
                    "membership_weight": 1.0,
                    "review_status": "REVIEW_REQUIRED",
                }
            )
        for chamber, signature, role in committee_evidence:
            matching = committee_index.get((chamber, signature, name_key), set())
            if person_id not in matching:
                continue
            party = str(profile.get("partition") or "Unknown")
            party_counts[party] += 1
            side = "MAJ" if party == "Republican" else "MIN" if party == "Democratic" else "UNKNOWN"
            committee_rows.append(
                {
                    "source_profile_uuid": uuid,
                    "spine_person_id": person_id,
                    "chamber": chamber,
                    "committee_signature": signature,
                    "role": role,
                    "party_partition": party,
                    "side_at_observation": side,
                    "side_basis": "119TH_CONGRESS_PARTY_AT_CURRENT_SNAPSHOT",
                    "payroll_office_keys": sorted(
                        committee_offices.get((chamber, signature, name_key, person_id), set())
                    ),
                    "observed_at": observed_at,
                    "temporal_scope": "POINT_OBSERVATION_ONLY",
                    "review_status": "REVIEW_REQUIRED",
                }
            )
            committee_assertions_by_uuid[uuid].append(committee_rows[-1])

    if profiles:
        unexpected = sorted(set(profiles) - set(source_cards))
        if unexpected:
            raise BuildError(f"profile histories contain UUIDs outside sealed directory: {unexpected[:5]}")
        if args.require_complete_profile_crawl and set(profiles) != set(source_cards):
            missing = sorted(set(source_cards) - set(profiles))
            raise BuildError(f"terminal profile crawl is missing sealed directory UUIDs: {missing[:5]}")

        for uuid in sorted(profiles):
            profile = profiles[uuid]
            card = source_cards[uuid]
            link_status, person_id = link_status_by_uuid[uuid]
            common = {
                "source_profile_uuid": uuid,
                "display_name": profile.get("verified_name") or profile.get("expected_name") or card.get("name"),
                "spine_person_id": person_id,
                "link_status": link_status,
                "identity_status": profile.get("identity_status"),
                "observed_at": profile.get("observed_at"),
                "source_url": profile.get("source_url"),
                "review_status": "REVIEW_REQUIRED",
                "canonical_eligible": False,
                "canonical_identity_promoted": False,
                "canonical_employment_promoted": False,
            }
            for ordinal, item in enumerate(profile.get("employment_history") or [], 1):
                employment_rows.append(
                    {
                        "schema_id": EMPLOYMENT_SCHEMA_ID,
                        **common,
                        "history_ordinal": ordinal,
                        "employer": str(item.get("employer") or "").strip(),
                        "title": str(item.get("title") or "").strip(),
                        "date_text": str(item.get("date_text") or "").strip(),
                        "temporal_scope": "SOURCE_TEXT_ONLY_NO_INTERVAL_PROMOTION",
                    }
                )
            for ordinal, item in enumerate(profile.get("education") or [], 1):
                education_rows.append(
                    {
                        "schema_id": EDUCATION_SCHEMA_ID,
                        **common,
                        "history_ordinal": ordinal,
                        "institution": str(item.get("institution") or "").strip(),
                        "degree": str(item.get("degree") or "").strip(),
                        "date_text": str(item.get("date_text") or "").strip(),
                        "temporal_scope": "SOURCE_TEXT_ONLY_NO_INTERVAL_PROMOTION",
                    }
                )

            # A 404 supplies no live profile policy observation; treating its empty
            # list as removals would manufacture a delta.
            if profile.get("identity_status") != "PROFILE_UNAVAILABLE_404":
                card_issues = {str(x).strip() for x in card.get("issue_areas") or [] if str(x).strip()}
                live_issues = {
                    str(x).strip() for x in profile.get("profile_issue_areas") or [] if str(x).strip()
                }
                for issue in sorted(live_issues - card_issues):
                    policy_delta_rows.append(
                        {
                            "schema_id": POLICY_DELTA_SCHEMA_ID,
                            **common,
                            "issue_area": issue,
                            "delta": "PROFILE_ONLY_ADDITION",
                            "source_card_present": False,
                            "live_profile_present": True,
                        }
                    )
                for issue in sorted(card_issues - live_issues):
                    policy_delta_rows.append(
                        {
                            "schema_id": POLICY_DELTA_SCHEMA_ID,
                            **common,
                            "issue_area": issue,
                            "delta": "CARD_ONLY_REMOVAL",
                            "source_card_present": True,
                            "live_profile_present": False,
                        }
                    )

            labels = sorted({str(x).strip() for x in profile.get("explicit_side_labels") or [] if str(x).strip()})
            mapped = sorted({side for side in (explicit_side(x) for x in labels) if side})
            assertions = committee_assertions_by_uuid.get(uuid, [])
            if labels:
                if len(mapped) == 1 and assertions:
                    for assertion in assertions:
                        explicit_side_rows.append(
                            {
                                "schema_id": EXPLICIT_SIDE_SCHEMA_ID,
                                **common,
                                "chamber": assertion["chamber"],
                                "committee_signature": assertion["committee_signature"],
                                "payroll_office_keys": assertion["payroll_office_keys"],
                                "role": assertion["role"],
                                "explicit_side_labels": labels,
                                "explicit_side": mapped[0],
                                "party_derived_side": assertion["side_at_observation"],
                                "agrees_with_party_derived_side": mapped[0] == assertion["side_at_observation"],
                                "mapping_status": "PROFILE_SINGLE_SIDE_TO_MATCHED_CURRENT_COMMITTEE",
                                "temporal_scope": "POINT_OBSERVATION_ONLY",
                            }
                        )
                else:
                    explicit_side_rows.append(
                        {
                            "schema_id": EXPLICIT_SIDE_SCHEMA_ID,
                            **common,
                            "chamber": None,
                            "committee_signature": None,
                            "payroll_office_keys": [],
                            "role": None,
                            "explicit_side_labels": labels,
                            "explicit_side": mapped[0] if len(mapped) == 1 else None,
                            "party_derived_side": None,
                            "agrees_with_party_derived_side": None,
                            "mapping_status": (
                                "NO_MATCHED_CURRENT_COMMITTEE"
                                if not assertions
                                else "AMBIGUOUS_OR_UNCLASSIFIED_PROFILE_SIDE_LABEL"
                            ),
                            "temporal_scope": "POINT_OBSERVATION_ONLY",
                        }
                    )

    link_rows.sort(key=lambda row: row["source_profile_uuid"])
    policy_rows.sort(key=lambda row: (row["spine_person_id"], row["issue_area"], row["source_profile_uuid"]))
    committee_rows.sort(
        key=lambda row: (
            row["spine_person_id"], row["chamber"], row["committee_signature"], row["source_profile_uuid"]
        )
    )
    employment_rows.sort(
        key=lambda row: (row["source_profile_uuid"], row["history_ordinal"])
    )
    education_rows.sort(
        key=lambda row: (row["source_profile_uuid"], row["history_ordinal"])
    )
    policy_delta_rows.sort(
        key=lambda row: (row["source_profile_uuid"], row["issue_area"], row["delta"])
    )
    explicit_side_rows.sort(
        key=lambda row: (
            row["source_profile_uuid"],
            row.get("chamber") or "",
            row.get("committee_signature") or "",
            row.get("role") or "",
        )
    )

    link_meta = write_gzip(out / "politico_payroll_direct_links.ndjson.gz", link_rows)
    policy_meta = write_gzip(out / "politico_policy_memberships.ndjson.gz", policy_rows)
    committee_meta = write_gzip(out / "politico_current_committee_assertions.ndjson.gz", committee_rows)
    optional_file_meta: dict[str, tuple[int, str, int]] = {}
    if profiles:
        for name, values in (
            ("politico_profile_employment_assertions.ndjson.gz", employment_rows),
            ("politico_profile_education_assertions.ndjson.gz", education_rows),
            ("politico_profile_policy_deltas.ndjson.gz", policy_delta_rows),
            ("politico_explicit_committee_side_assertions.ndjson.gz", explicit_side_rows),
        ):
            optional_file_meta[name] = write_gzip(out / name, values)
    unique_linked_people = len({row["spine_person_id"] for row in link_rows if row["status"] == "LINKED"})
    unique_policy_people = len({row["spine_person_id"] for row in policy_rows})
    unique_policy_pairs = len({(row["spine_person_id"], row["issue_area"]) for row in policy_rows})

    receipt = {
        "schema_id": RECEIPT_SCHEMA_ID,
        "rule_version": RULE_VERSION,
        "status": "PASS",
        "review_status": "REVIEW_REQUIRED",
        "canonical_identity_promotions": 0,
        "canonical_employment_promotions": 0,
        "observed_at": observed_at,
        "counts": {
            "politico_profiles": profile_count,
            "profiles_with_issue_areas": issue_profile_count,
            "issue_assertions": issue_assertion_count,
            "status": dict(sorted(status_counts.items())),
            "match_methods": dict(sorted(method_counts.items())),
            "unique_linked_spine_people": unique_linked_people,
            "policy_memberships": len(policy_rows),
            "unique_person_policy_pairs": unique_policy_pairs,
            "unique_policy_spine_people": unique_policy_people,
            "current_committee_assertions": len(committee_rows),
            "committee_assertions_by_party": dict(sorted(party_counts.items())),
            "profile_history_rows": len(profiles),
            "profile_employment_assertions": len(employment_rows),
            "profile_education_assertions": len(education_rows),
            "profile_policy_deltas": len(policy_delta_rows),
            "explicit_committee_side_assertions": len(explicit_side_rows),
            "explicit_committee_side_mapped": sum(
                row["mapping_status"] == "PROFILE_SINGLE_SIDE_TO_MATCHED_CURRENT_COMMITTEE"
                for row in explicit_side_rows
            ),
            "explicit_side_disagreements_with_party": sum(
                row.get("agrees_with_party_derived_side") is False for row in explicit_side_rows
            ),
            "current_member_offices_indexed": len(current_member_offices),
            "current_committee_signatures_indexed": len(current_committee_signatures),
        },
        "identity_rule": (
            "Exact normalized first and last name plus an exact current Member bioguide "
            "or allowlisted-normalized current committee employer. A profile links only "
            "when the union of supported office candidates contains exactly one spine person."
        ),
        "temporal_rule": (
            "Politico cards are a current point observation. They add categorical policy and "
            "committee assertions with duration_weight 0 and do not widen payroll tenure."
        ),
        "profile_history_rule": (
            "Verified Politico profile employment and education rows are emitted as "
            "source-text assertions only. Dates are not parsed into canonical intervals, "
            "no identity or employment is promoted, and profile/card policy differences "
            "and explicit committee-side labels remain separate review-only layers."
        ),
        "profile_crawl_gate": profile_crawl_gate,
        "negative_control": {
            "method": (
                "For every profile with supported office evidence, rotate each Member or "
                "committee to the next sorted current office in the same class and rerun "
                "the exact name lookup. This preserves the name distribution while making "
                "the stated employer false."
            ),
            "eligible_profiles": control_eligible_profiles,
            "profiles_matching_a_rotated_false_office": control_hit_profiles,
            "rate": round(control_hit_profiles / control_eligible_profiles, 8)
            if control_eligible_profiles
            else None,
            "acceptance_bar_lt_0_01": (
                control_hit_profiles / control_eligible_profiles < 0.01
                if control_eligible_profiles
                else None
            ),
        },
        "ambiguous_examples": ambiguous_examples,
        "files": {
            "politico_payroll_direct_links.ndjson.gz": {
                "rows": link_meta[0], "sha256": link_meta[1], "bytes": link_meta[2]
            },
            "politico_policy_memberships.ndjson.gz": {
                "rows": policy_meta[0], "sha256": policy_meta[1], "bytes": policy_meta[2]
            },
            "politico_current_committee_assertions.ndjson.gz": {
                "rows": committee_meta[0], "sha256": committee_meta[1], "bytes": committee_meta[2]
            },
            **{
                name: {"rows": meta[0], "sha256": meta[1], "bytes": meta[2]}
                for name, meta in sorted(optional_file_meta.items())
            },
        },
        "inputs": {
            str(path): {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in required_paths
        },
        "failures": [],
    }
    receipt_path = out / "politico_payroll_direct_link_receipt.json"
    receipt_path.write_bytes(canonical_json(receipt))
    return receipt


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-directory", required=True)
    ap.add_argument("--crawl-receipt", required=True)
    ap.add_argument("--spine", required=True)
    ap.add_argument("--spans", required=True)
    ap.add_argument("--roster", required=True)
    ap.add_argument(
        "--profile-histories",
        help="Verified Politico profiles.ndjson; requires --profile-crawl-verification",
    )
    ap.add_argument(
        "--profile-crawl-verification",
        help="Independent crawl_verification.json paired with --profile-histories",
    )
    ap.add_argument(
        "--require-complete-profile-crawl",
        action="store_true",
        help="Fail unless the verified profile crawl has terminal 100%% coverage",
    )
    ap.add_argument("--output", required=True)
    return ap


if __name__ == "__main__":
    result = run(parser().parse_args())
    print(json.dumps(result["counts"], indent=2, sort_keys=True))
