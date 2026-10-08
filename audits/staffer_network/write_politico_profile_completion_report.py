#!/usr/bin/env python3
"""Render a deterministic Markdown receipt for a completed Politico crawl.

The writer intentionally refuses partial or merely well-formed checkpoints.  Its
input must be a v2 verification receipt whose terminal 18,618-profile gate passed.
It does not rebuild or promote any bridge, graph, or canonical identity artifact.
"""

from __future__ import annotations

try:
    from .politico_completion_contract import completion_accepted, validate_browser_exception, SOURCE_EXCEPTION_POLICY
except ImportError:
    from politico_completion_contract import completion_accepted, validate_browser_exception, SOURCE_EXCEPTION_POLICY


import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


EXPECTED_CORPUS_TOTAL = 18_618
ROOT = Path(__file__).resolve().parent
DEFAULT_VERIFICATION = (
    ROOT / "politico_profile_crawl_20260903_raw" / "crawl_verification.json"
)
DEFAULT_OUTPUT = ROOT / "POLITICO_PROFILE_CRAWL_COMPLETION_20260904.md"


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_complete(receipt: dict[str, Any]) -> None:
    counts = receipt.get("counts", {})
    coverage = receipt.get("coverage", {}).get("all_profiles", {})
    gate = receipt.get("completion_gate", {})
    state = receipt.get("crawl_state", {})
    requirements = {
        "schema_id": receipt.get("schema_id")
        == "politico-profile-crawl-verification-v2",
        "status": receipt.get("status") == "PASS",
        "integrity_status": receipt.get("integrity_status") == "PASS",
        "completion_status": completion_accepted(receipt),
        "completion_gate": gate.get("status") == "PASS",
        "completion_gate_unmet": gate.get("unmet_requirement_count") == 0,
        "required_total": gate.get("required_profile_total")
        == EXPECTED_CORPUS_TOTAL,
        "directory_rows": counts.get("sealed_directory_rows")
        == EXPECTED_CORPUS_TOTAL,
        "directory_unique": counts.get("sealed_directory_unique_profiles")
        == EXPECTED_CORPUS_TOTAL,
        "profile_rows": counts.get("profile_rows") == EXPECTED_CORPUS_TOTAL,
        "profile_unique": counts.get("unique_profiles_collected")
        == EXPECTED_CORPUS_TOTAL,
        "profile_accounted": counts.get("profiles_accounted")
        == EXPECTED_CORPUS_TOTAL,
        "coverage_completed": coverage.get("completed") == EXPECTED_CORPUS_TOTAL,
        "coverage_unresolved": coverage.get("unresolved") == 0,
        "state_queue_total": state.get("queue_total") == EXPECTED_CORPUS_TOTAL,
        "state_succeeded": state.get("total_succeeded") == EXPECTED_CORPUS_TOTAL,
        "state_failed": state.get("total_failed") == 0,
        "state_remaining": state.get("remaining") == 0,
        "state_halted": state.get("halted") is False,
        "failure_rows": counts.get("hard_crawl_failures") == 0,
        "verification_failures": receipt.get("verification_failure_count") == 0,
        "content_partition": (
            counts.get("content_bearing_profiles", 0)
            + counts.get("allowed_profile_unavailable_404", 0)
            + counts.get("accepted_source_exceptions", 0)
            == EXPECTED_CORPUS_TOTAL
        ),
    }
    failed = [name for name, passed in requirements.items() if not passed]
    if failed:
        raise ValueError(
            "refusing to write a completion report; failed terminal checks: "
            + ", ".join(failed)
        )


def escape_table(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def exception_table(rows: list[dict[str, Any]], *, renamed: bool) -> list[str]:
    if renamed:
        lines = [
            "| UUID | Sealed name | Live name | Review status | Source |",
            "|---|---|---|---|---|",
        ]
        for row in rows:
            source = escape_table(row.get("source_url"))
            lines.append(
                "| "
                + " | ".join(
                    [
                        *(
                            escape_table(row.get(key))
                            for key in (
                                "profile_uuid",
                                "expected_name",
                                "verified_name",
                                "review_status",
                            )
                        ),
                        f"[profile]({source})",
                    ]
                )
                + " |"
            )
        return lines
    lines = [
        "| UUID | Sealed name | Review status | Source |",
        "|---|---|---|---|",
    ]
    for row in rows:
        source = escape_table(row.get("source_url"))
        lines.append(
            "| "
            + " | ".join(
                [
                    *(
                        escape_table(row.get(key))
                        for key in ("profile_uuid", "expected_name", "review_status")
                    ),
                    f"[profile]({source})",
                ]
            )
            + " |"
        )
    return lines


def render(receipt: dict[str, Any], verification_path: Path) -> str:
    require_complete(receipt)
    counts = receipt["counts"]
    coverage = receipt["coverage"]
    state = receipt["crawl_state"]
    exceptions = receipt["identity_exceptions"]
    unavailable = exceptions["profile_unavailable_404"]["rows"]
    renamed = exceptions["live_name_changed_same_uuid"]["rows"]
    inputs = receipt["inputs"]

    input_hash_lines: list[str] = []
    for label in ("directory", "profiles", "failures", "state"):
        raw_path = inputs.get(label)
        if raw_path is None:
            input_hash_lines.append(f"- {label}: not supplied")
            continue
        path = Path(raw_path)
        if not path.exists():
            if label == "failures" and counts["hard_crawl_failures"] == 0:
                input_hash_lines.append(
                    f"- {label}: `{path}` — absent, consistent with zero failures"
                )
                continue
            raise FileNotFoundError(path)
        input_hash_lines.append(f"- {label}: `{path}` — SHA-256 `{sha256(path)}`")
    input_hash_lines.append(
        f"- verification: `{verification_path.resolve()}` — SHA-256 "
        f"`{sha256(verification_path)}`"
    )

    lines = [
        "# Politico Profile-History Crawl — Terminal Completion Receipt",
        "",
        f"Verification generated: `{receipt['generated_at']}`",
        "",
        "## Terminal result",
        "",
        f"- **{receipt.get('completion_status')}** — all sealed directory records are accounted for; source gaps remain explicit.",
        f"- Directory rows: **{counts['sealed_directory_rows']:,} / {EXPECTED_CORPUS_TOTAL:,}**.",
        f"- Unique directory UUIDs: **{counts['sealed_directory_unique_profiles']:,} / {EXPECTED_CORPUS_TOTAL:,}**.",
        f"- Profile rows: **{counts['profile_rows']:,} / {EXPECTED_CORPUS_TOTAL:,}**.",
        f"- Unique collected UUIDs: **{counts['unique_profiles_collected']:,} / {EXPECTED_CORPUS_TOTAL:,}**.",
        f"- State successes: **{state['total_succeeded']:,} / {EXPECTED_CORPUS_TOTAL:,}**.",
        f"- Remaining/unresolved: **{state['remaining']:,} / {coverage['all_profiles']['unresolved']:,}**.",
        f"- Crawl failure rows / verifier failures: **{counts['hard_crawl_failures']:,} / {receipt['verification_failure_count']:,}**.",
        f"- Committee-priority profiles: **{coverage['committee_profiles']['completed']:,} / {coverage['committee_profiles']['expected']:,} ({coverage['committee_profiles']['percent']:.4f}%)**.",
        "",
        "## Profile content",
        "",
        f"- Content-bearing profile histories: **{counts['content_bearing_profiles']:,}**.",
        f"- Allowed live-404 UUID exceptions: **{counts['allowed_profile_unavailable_404']:,}**.",
        f"- Profiles with current positions: **{counts['profiles_with_current_positions']:,}**; position rows: **{counts['current_position_records']:,}**.",
        f"- Profiles with employment history: **{counts['profiles_with_employment_history']:,}**; employment rows: **{counts['employment_history_records']:,}**.",
        f"- Profiles with education: **{counts['profiles_with_education']:,}**; education rows: **{counts['education_records']:,}**.",
        f"- Explicit side-label rows: **{counts['explicit_side_label_records']:,}**.",
        f"- Profile issue-area rows: **{counts['profile_issue_area_records']:,}**.",
        f"- Identity statuses: `{json.dumps(counts['identity_statuses'], sort_keys=True)}`.",
        "",
        f"Release outcome: **{receipt.get('completion_status')}**. Browser-checked source omissions: **{counts.get('accepted_source_exceptions', 0)}**. These are not fully populated profiles.",
        "",
        "The content-bearing count plus validated source-omission and live-404 exception "
        f"count equals **{EXPECTED_CORPUS_TOTAL:,}**. Live 404s are UUID-accounted "
        "exceptions, not inferred identity matches and not hard crawl failures.",
        "",
        "## Browser-checked source omissions",
        "",
        "| UUID | Name | Missing collections | Browser outcome |",
        "|---|---|---|---|",
        *["| " + " | ".join(escape_table(v) for v in (r['profile_uuid'], r.get('verified_name'), ', '.join(r.get('source_missing_collections', [])), r.get('outcome'))) + " |" for r in (receipt.get('source_exception_verification') or {}).get('rows', [])],
        "",
        "## Explicit live-404 exceptions",
        "",
        *exception_table(unavailable, renamed=False),
        "",
        "## Explicit same-UUID live-name changes",
        "",
        *exception_table(renamed, renamed=True),
        "",
        "## Immutable input receipts",
        "",
        *input_hash_lines,
        "",
        "## Downstream boundary and next steps",
        "",
        "This receipt closes only the authenticated profile-history crawl. It does "
        "not itself promote identities, employment claims, or graph weights.",
        "",
        "1. Review every listed live-404 and same-UUID name-change exception.",
        "2. Rebuild the strict Politico-to-payroll bridge from this sealed crawl and reproduce its deterministic twin.",
        "3. Run the bridge verifier and require zero failures and zero canonical promotions.",
        "4. Rebuild the separated-layer staffer network and its deterministic twin using the retained modeling defaults.",
        "5. Run the independent graph verifier, named regressions, source-to-edge coverage checks, and final reconciliation report.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verification", type=Path, default=DEFAULT_VERIFICATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    try:
        receipt = read_json(args.verification)
        payload = render(receipt, args.verification)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
