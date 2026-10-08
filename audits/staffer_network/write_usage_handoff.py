#!/usr/bin/env python3
"""Write a deterministic low-usage handoff for the Politico/network build."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CRAWL = ROOT / "politico_profile_crawl_20260903_raw"
BRIDGE = ROOT / "politico_payroll_direct_links_20260903_v3_primary"
BRIDGE_VERIFY = ROOT / "politico_payroll_direct_links_20260903_v3_verification"
GRAPH = ROOT / "staffer_social_network_20260903_v4_primary"
GRAPH_VERIFY = ROOT / "staffer_social_network_20260903_v4_verification"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--usage-remaining", type=float, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "STAFFER_SOCIAL_NETWORK_USAGE_HANDOFF_20260904.md",
    )
    args = parser.parse_args()

    state_path = CRAWL / "state.json"
    crawl_verify_path = CRAWL / "crawl_verification.json"
    bridge_receipt_path = BRIDGE / "politico_payroll_direct_link_receipt.json"
    bridge_verify_path = BRIDGE_VERIFY / "verification_report.json"
    graph_receipt_path = GRAPH / "staffer_social_network_receipt.json"
    graph_verify_path = GRAPH_VERIFY / "staffer_social_network_verification_receipt.json"

    state = read_json(state_path)
    crawl_verify = read_json(crawl_verify_path)
    bridge = read_json(bridge_receipt_path)
    bridge_verify = read_json(bridge_verify_path)
    graph = read_json(graph_receipt_path)
    graph_verify = read_json(graph_verify_path)

    counts = crawl_verify["counts"]
    coverage = crawl_verify["coverage"]
    bridge_counts = bridge["counts"]
    nodes = graph["node_universe"]
    edges = graph["edge_counts"]
    identities = counts.get("identity_statuses", {})
    completion_gate = crawl_verify.get("completion_gate", {})
    rate_control = crawl_verify.get("rate_control_contract", {})
    allowed_404 = counts.get(
        "allowed_profile_unavailable_404",
        identities.get("PROFILE_UNAVAILABLE_404", 0),
    )
    content_bearing = counts.get(
        "content_bearing_profiles",
        counts.get("profile_rows", 0) - allowed_404,
    )
    checkpoint_status = crawl_verify["status"]
    if not completion_gate and coverage["all_profiles"]["unresolved"]:
        checkpoint_status = "IN_PROGRESS"
    generated_at = datetime.now(timezone.utc).isoformat()

    lines = [
        "# Staffer Social Network — Usage Threshold Handoff",
        "",
        f"Generated: `{generated_at}`  ",
        f"Codex usage remaining at handoff: **{args.usage_remaining:g}%**  ",
        f"Crawl phase: `{state.get('scope')}`",
        "",
        "## Current checkpoint",
        "",
        f"- Politico directory roster: **{counts['sealed_directory_unique_profiles']:,} / {counts['sealed_directory_unique_profiles']:,} unique staffers known**.",
        f"- Profile histories accounted for: **{coverage['all_profiles']['completed']:,} / {coverage['all_profiles']['expected']:,} ({coverage['all_profiles']['percent']:.4f}%)**.",
        f"- Profiles remaining: **{coverage['all_profiles']['unresolved']:,}**.",
        f"- Committee-priority coverage: **{coverage['committee_profiles']['completed']:,} / {coverage['committee_profiles']['expected']:,} ({coverage['committee_profiles']['percent']:.4f}%)**.",
        f"- Employment-history rows collected: **{counts['employment_history_records']:,}**.",
        f"- Education rows collected: **{counts['education_records']:,}**.",
        f"- Content-bearing profiles / allowed live-404 exceptions: **{content_bearing:,} / {allowed_404:,}**.",
        f"- Crawl hard failures: **{counts['hard_crawl_failures']:,}**.",
        f"- Crawl checkpoint status: **{checkpoint_status}**; integrity **{crawl_verify.get('integrity_status', crawl_verify['status'])}**; terminal gate **{completion_gate.get('status', 'NOT_AVAILABLE')}**.",
        f"- Verification failures / unmet terminal requirements: **{crawl_verify['verification_failure_count']} / {completion_gate.get('unmet_requirement_count', 'not available')}**.",
        f"- Rate control: **{rate_control.get('contract', 'LEGACY_FIXED_40')}** at **{rate_control.get('current_requests_per_minute', state.get('max_requests_per_minute', 40))} requests/minute**; authorized hard ceiling **250**.",
        f"- Identity statuses: `{json.dumps(identities, sort_keys=True)}`.",
        "",
        "## Existing reconciliation and graph",
        "",
        f"- Strict Politico/payroll bridge: **{bridge['status']}**; {bridge_counts['status']['LINKED']:,} linked profiles, {bridge_counts['unique_linked_spine_people']:,} unique payroll people, and {bridge_counts['policy_memberships']:,} policy memberships.",
        f"- Independent bridge verifier: **{bridge_verify['status']}**.",
        f"- Social graph: **{graph['status']}**; {nodes['total']:,} nodes and {edges['total_rows_emitted']:,} edge rows.",
        f"- Independent graph verifier: **{graph_verify['status']}**.",
        f"- Gordon Holzberg regression: **{graph['named_regression_checks']['Gordon_Holzberg']['status']}**.",
        f"- Stephanie Belk regression: **{graph['named_regression_checks']['Stephanie_Belk']['status']}**.",
        "- Canonical identity and employment promotions remain **zero**; current modeling defaults are preserved.",
        "",
        "## Integrity receipts",
        "",
        f"- `{crawl_verify_path}` — SHA-256 `{sha256(crawl_verify_path)}`",
        f"- `{bridge_receipt_path}` — SHA-256 `{sha256(bridge_receipt_path)}`",
        f"- `{bridge_verify_path}` — SHA-256 `{sha256(bridge_verify_path)}`",
        f"- `{graph_receipt_path}` — SHA-256 `{sha256(graph_receipt_path)}`",
        f"- `{graph_verify_path}` — SHA-256 `{sha256(graph_verify_path)}`",
        "",
        "## Resume and completion steps",
        "",
        "1. Resume `ALL_CURRENT_PROFILES` from `politico_profile_crawl_20260903_raw/state.json`; completed UUIDs are skipped automatically.",
        "2. Use authenticated crawler tabs. The legacy fixed rate of 40 requests/minute remains valid. The authorized gentle ramp is 60 → 80 → 100 → 120 → 150 → 200 → 250 when `state.rate_control.mode` is `AUTHORIZED_GENTLE_RAMP`; each step requires sustained clean evidence and adaptive backoff remains active. Never exceed 250.",
        "3. At every authorized ramp rate, require `state.rate_control.current_requests_per_minute` to equal `state.max_requests_per_minute` and persist nonnegative `state.rate_control.last_batch.attempted`, `succeeded`, `retryable_failures`, and `hard_failures` counters. Continued ramping requires zero hard failures.",
        "4. Immediately back off on any 401, 429, authentication or challenge surface, render degradation, or navigation degradation. Halt and report on authentication/challenge loss or any hard failure. Do not extract credentials, multiply sessions, or bypass challenges.",
        "5. After each sustained segment, run `verify_politico_profile_crawl.py`; require `integrity_status=PASS`. An incomplete clean checkpoint is deliberately labeled `IN_PROGRESS`.",
        "6. At 18,618 accounted UUIDs, rerun the verifier with `--require-complete`; only `status=PASS`, `completion_status=COMPLETE`, zero verification failures, and zero unmet gate requirements close the crawl.",
        "7. Generate the crawl receipt with `write_politico_profile_completion_report.py` and independently review every `LIVE_NAME_CHANGED_SAME_UUID` and `PROFILE_UNAVAILABLE_404` exception it lists.",
        "8. Rebuild the strict bridge with `build_politico_payroll_direct_links.py`, reproduce its twin, and run `verify_politico_payroll_direct_links.py`.",
        "9. Rebuild the separated-layer network with `build_staffer_social_network.py`, reproduce its twin, and run `verify_staffer_social_network.py`.",
        "10. Update `STAFFER_SOCIAL_NETWORK_COMPLETION_20260903_V4.md` and write `STAFFER_SOCIAL_NETWORK_FINAL_RECONCILIATION_20260904.md` with final coverage, hashes, limitations, and next steps.",
        "",
        "## Known limitations",
        "",
        "- The authenticated Politico API returns 401 outside the signed-in browser session.",
        "- The tested history-only bulk PDF export consumed quota but did not complete.",
        "- Live 404s and same-UUID name changes are accounted exceptions, not inferred identity merges.",
        "- Politico directory cards are current-snapshot evidence; undated policy memberships remain a separate analysis layer.",
        "",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
