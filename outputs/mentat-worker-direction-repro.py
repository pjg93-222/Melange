"""Offline review examples; imports current code and uses temporary/synthetic data only."""
from pathlib import Path
import json
import hashlib
from datetime import datetime, timezone
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[1] / "mentat"
sys.path[:0] = [str(PROJECT / "tools"), str(PROJECT / "tests")]

from pac_cash_model import estimate_snapshots
from pac_evidence import receipt_role
from fec_transfer_graph import allocate, transfer_index
from test_pac_cash_model import snapshot
from enrich_downstream import enrich


def ambiguous_cash_receipt():
    data = snapshot()
    data["receipts"][0].update(line_number="17", receipt_type_full="OTHER FEDERAL RECEIPTS")
    result = estimate_snapshots([data], "Acme", ["Acme Inc"])["cycles"][0]
    return {
        "case": "unresolved_receipt_is_allowed_into_cash_estimate",
        "input_receipt_role": receipt_role(data["receipts"][0]),
        "expected": "withheld pending transaction classification",
        "actual_status": result["status"],
        "issues": result["issues"],
        "allocations": result["allocations"],
        "company_amount_displayed_by_current_ui": sum(r["estimated_funding"].get("Acme", 0) for r in result["allocations"]) if result["status"] == "estimated" else None,
        "company_display_state": "Estimated" if result["status"] == "estimated" else "Awaiting reconciliation",
    }


def unmatched_candidate_transfer():
    assigned, coverage = allocate(
        {"PAC": 100},
        [{"source": "PAC", "destination": "CANDIDATE_COMMITTEE", "amount": 90}],
        [{"source": "PAC", "candidate": "OTHER_CANDIDATE", "direction": "Oppose", "amount": 10}],
        stop_nodes={"CANDIDATE_COMMITTEE"},
    )
    payload = {
        "metadata": {"industry": "Fixture", "transfer_coverage": [{"cycle": 2024, "status": "indexed", "counts": {}}]},
        "cycles": [{"cycle": 2024}], "committee_map": [],
        "raw_rows": [{"cycle": 2024, "committee_id": "PAC", "amount": 100,
                      "include_in_analysis": "Yes", "receipt_role": "contribution"}],
        "candidate_committee_links": [{"cycle": 2024, "committee_id": "CANDIDATE_COMMITTEE",
                                       "designation": "P", "candidate_id": "INTENDED_CANDIDATE"}],
        "transfer_edges": [{"cycle": 2024, "source": "PAC", "destination": "CANDIDATE_COMMITTEE", "amount": 90}],
        "downstream_activity": [{"cycle": 2024, "source_committee_id": "PAC", "candidate_id": "OTHER_CANDIDATE",
                                 "support_oppose": "Oppose", "preliminary_included_amount": 10}],
    }
    with tempfile.TemporaryDirectory(prefix="mentat-review-enrichment-") as directory:
        report = enrich(payload, Path(directory))
    return {
        "case": "candidate_transfer_removed_without_activity_counterpart",
        "expected": "Preserve the 90-dollar route or its unresolved share; do not assign all 100 to the separate 10-dollar opposition activity",
        "actual_allocations": assigned,
        "actual_coverage": coverage,
        "report_attribution_summary": report["attribution_summary"],
        "report_quality_checks": report["quality_checks"],
    }


def transfer_row(date, sub, file_num, amendment, kind="24K", value="100"):
    fields = [""] * 21
    for index, text in {0: "C00000001", 1: amendment, 2: "Q1", 5: kind,
                        13: date, 14: value, 15: "C00000002", 16: "TRANSFER1",
                        17: str(file_num), 20: sub}.items():
        fields[index] = text
    return "|".join(fields)


def redated_transfer():
    with tempfile.TemporaryDirectory(prefix="mentat-review-transfer-") as directory:
        path = Path(directory) / "itoth.txt"
        path.write_text("\n".join([
            transfer_row("12312023", "original", 10, "N"),
            transfer_row("01012024", "amendment", 11, "A"),
        ]), encoding="utf-8")
        result = transfer_index(path, 2024)
        return {
            "case": "amendment_date_crosses_calendar_year",
            "fixture_meaning": "One 100-dollar transfer whose amended record corrects the transaction date across New Year, within the same election cycle",
            "expected": "100 dollars if the amendment relationship is established; otherwise unresolved linkage",
            "actual_edges": result["edges"],
            "actual_counts": result["counts"],
            "unresolved_sources": result.get("unresolved_sources", []),
        }


def reclassified_transfer():
    with tempfile.TemporaryDirectory(prefix="mentat-review-transfer-role-") as directory:
        path = Path(directory) / "itoth.txt"
        path.write_text("\n".join([
            transfer_row("01012024", "original", 10, "N"),
            transfer_row("01012024", "amendment", 11, "A", kind="24Z"),
        ]), encoding="utf-8")
        result = transfer_index(path, 2024)
        return {
            "case": "amendment_reclassifies_cash_transfer_as_in_kind",
            "fixture_meaning": "A 100-dollar transfer corrected from cash code 24K to in-kind code 24Z in a later filing",
            "expected": "No cash edge from the superseded record, or unresolved amendment classification",
            "actual_edges": result["edges"],
            "actual_counts": result["counts"],
            "unresolved_sources": result.get("unresolved_sources", []),
        }


if __name__ == "__main__":
    paths = ["tools/fec_transfer_graph.py", "tools/pac_cash_model.py", "tools/pac_evidence.py",
             "tools/enrich_downstream.py", "tools/api_company_cycle_fanout.py", "app/app.js"]
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_hashes": {p: hashlib.sha256((PROJECT / p).read_bytes()).hexdigest() for p in paths},
        "cases": [ambiguous_cash_receipt(), unmatched_candidate_transfer(),
                  redated_transfer(), reclassified_transfer()],
    }
    output = json.dumps(result, indent=2)
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(output + "\n", encoding="utf-8")
        print(f"Saved {len(result['cases'])} offline reproductions to {sys.argv[1]}")
    else:
        print(output)
