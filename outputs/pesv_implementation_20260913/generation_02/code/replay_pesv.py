"""Build an isolated, receipted P/E/S/V comparison from frozen local evidence.

This command never imports the production pipeline or writes its source tree.
The only production helpers executed are copied tier_util/paths modules, loaded
against a copied baseline in the generation's staging directory.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import date, datetime, timezone
import hashlib
import html
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
CODE_ROOT = Path(__file__).resolve().parent
BASELINE_FILES = (
    "fec/tier_util.py", "fec/paths.py", "tier_overrides.json",
    "ranks_python.json", "data/engine/primacy_factors.json",
    "data/lobbying/industry_tiers.json", "grievance_ledger.ndjson",
    "delivery_ledger.ndjson",
)
TERM_FILES = (
    "data/legislation/bill_milestones.ndjson",
    "data/legislation/member_measure_roles.ndjson",
    "data/legislation/member_population.ndjson",
    "data/legislation/accepted_signals.ndjson",
    "data/legislation/bill_impact.ndjson",
    "data/legislation/congressional_letter_coverage.ndjson",
    "data/legislation/effectiveness_universe_manifest.json",
    "data/legislation/population_receipt.json",
    "data/legislation/accepted_evidence_coverage.json",
    "data/engine/legislative_effectiveness_comparison_v1.json",
)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def iter_rows(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        for number, line in enumerate(handle, 1):
            if line.strip():
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(f"Expected object at {path}:{number}")
                yield row


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                    sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def inside(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def validate_output(output, source, shadow, code_root=CODE_ROOT):
    """Reject overlapping roots before creating any output or staging directory."""
    output = Path(output).resolve()
    for root in (source, shadow, code_root):
        if inside(output, root) or inside(root, output):
            raise ValueError(f"Output must not overlap source, shadow, or code root: {root}")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output already exists and is not an empty directory: " + str(output))
    staging = output.with_name(output.name + ".building")
    if staging.exists():
        raise ValueError("Staging directory already exists; choose a new output: " + str(staging))
    return output, staging


def hashes(paths):
    return {str(Path(path).resolve()): sha256(path) for path in sorted(set(paths), key=str)}


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def chamber(value):
    return {"h": "house", "rep": "house", "s": "senate", "sen": "senate"}.get(
        str(value).lower(), str(value).lower())


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError("Cannot load isolated module: " + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@contextmanager
def copied_helpers(baseline):
    """Keep all module defaults and environment paths inside the snapshot."""
    settings = {"MONEYBALL_ROOT": str(baseline), "PRIMACY_BOARD": "factor",
                "PRIMACY_MIN_CUPRIM": "0.75"}
    old_env = {key: os.environ.get(key) for key in settings}
    old_modules = {key: sys.modules.get(key) for key in ("paths", "_pesv_snapshot_tier_util")}
    old_path = list(sys.path)
    try:
        os.environ.update(settings)
        paths = load_module("paths", baseline / "fec/paths.py")
        helper = load_module("_pesv_snapshot_tier_util", baseline / "fec/tier_util.py")
        observed = {"paths_module": paths.__file__, "tier_module": helper.__file__,
                    "root": helper._ROOT, "override_path": helper._OVERRIDE_PATH}
        if not all(inside(path, baseline) for path in observed.values()):
            raise RuntimeError("Copied helper import escaped snapshot: " + repr(observed))
        if tuple(helper.BUCKETS) != (13, 24, 48) or helper.PRIMACY_MIN_CUPRIM != .75:
            raise RuntimeError("Unexpected copied tier policy constants")
        yield helper, observed
    finally:
        sys.path[:] = old_path
        for key, value in old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        for key, value in old_modules.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


def tier_mapping(order, buckets):
    first, second, third = buckets[0], sum(buckets[:2]), sum(buckets)
    return {name: {"rank": index + 1,
                   "tier": 1 if index < first else 2 if index < second else 3 if index < third else 0}
            for index, name in enumerate(order)}


def apply_policy(helper, order, baseline):
    policy_path = baseline / "tier_overrides.json"
    overrides = helper.load_tier_overrides(path=str(policy_path))
    positions = helper.load_tier_positions(path=str(policy_path))
    credits = helper.load_primacy_cu_credit(str(baseline))
    after_overrides = helper.apply_tier_overrides(order, overrides, positions=positions)
    after_evidence = helper.apply_evidence_floor(after_overrides, credits, minimum=.75,
                                                exempt=set(overrides))
    final, conduct = helper.apply_conduct_ladder(
        after_evidence, helper.load_open_breaches(str(baseline)),
        helper.load_delivery_credit(str(baseline)), buckets=helper.BUCKETS)
    mapping = tier_mapping(final, helper.BUCKETS)
    violations = []
    for name, seat in mapping.items():
        if seat["tier"] and name not in overrides and credits.get(name, 0) < .75:
            violations.append({"member": name, "rule": "evidence_floor", "tier": seat["tier"]})
        ceiling = conduct.get(name, {}).get("tier_ceiling", 1)
        if seat["tier"] and (ceiling == 0 or seat["tier"] < ceiling):
            violations.append({"member": name, "rule": "conduct_ceiling", "tier": seat["tier"],
                               "ceiling": ceiling})
    if len(final) != len(set(final)) or set(final) != set(order):
        violations.append({"rule": "policy_changed_roster"})
    return mapping, conduct, violations, {
        "minimum_cu_primary_credit": .75, "buckets": list(helper.BUCKETS),
        "override_count": len(overrides), "floor_qualified_count": sum(
            credits.get(name, 0) >= .75 or name in overrides for name in order),
        "order": "score order; overrides; evidence floor; conduct ladder; fixed tier buckets",
    }


def reproduce_baseline(helper, baseline):
    published = read_json(baseline / "data/lobbying/industry_tiers.json")["industries"]["credit_union"]["rows"]
    rows = {str(row["member"]): row for row in published}
    factors = helper.load_primacy_ranked(str(baseline))
    factor_doc = read_json(baseline / "data/engine/primacy_factors.json")
    ranks = read_json(baseline / "ranks_python.json")
    errors = []
    if len(rows) != 533 or len(published) != 533:
        errors.append({"rule": "published_roster_533_unique", "observed": len(rows)})
    bios = [str(row.get("bioguide") or "") for row in published]
    if any(not bio for bio in bios) or len(bios) != len(set(bios)):
        errors.append({"rule": "published_bioguide_uniqueness"})
    for name in rows:
        p = factor_doc.get("members", {}).get(name, {}).get("factor_ranked")
        if not finite(p):
            errors.append({"rule": "finite_authoritative_factor_ranked", "member": name})
    scores = helper.primacy_scores(ranks.get("pcts", {}), factors, mode="factor")
    rankable = [name for name in rows if name in scores]
    order = sorted(rankable, key=lambda name: (-scores[name], name))
    computed, conduct, violations, policy = apply_policy(helper, order, baseline)
    errors.extend(violations)
    for name, row in rows.items():
        expected = {"rank": row.get("tierrank"), "tier": row.get("tier")}
        if computed.get(name) != expected:
            errors.append({"rule": "published_tier_rank_parity", "member": name,
                           "published": expected, "recomputed": computed.get(name)})
        if finite(factors.get(name)) and row.get("score") != factors[name]:
            errors.append({"rule": "published_factor_parity", "member": name,
                           "published": row.get("score"), "factor": factors[name]})
    return {"rows": rows, "factors": factors, "rankable": set(rankable), "computed": computed,
            "conduct": conduct, "policy": policy, "errors": errors,
            "passed": not errors, "status": "reproduced" if not errors else "baseline_stale_or_invalid"}


def reserved_number_exclusion(source, selected):
    """Narrow, receipted correction of five documented 119th House placeholders."""
    mid = str(source.get("measure_id"))
    known = {"119:hr:" + str(n) for n in (2, 3, 5, 8, 10)}
    if (mid in known and source.get("title") == "Reserved for the Speaker."
            and source.get("actions") == [] and source.get("eligible") is True):
        if mid in selected:
            raise ValueError("Reserved bill has accepted scoring evidence: " + mid)
        return "documented_reserved_house_bill_number_with_no_actions"
    return None


def compact_term(term_root, congress, as_of):
    """Retain the entire chamber bill/impact universe; restrict only numerator roles."""
    evidence = term_root / "data/legislation"
    signals = list(iter_rows(evidence / "accepted_signals.ndjson"))
    selected = {str(s.get("measure_id")) for s in signals if s.get("accepted") is True}
    member_scopes = {(str(s.get("measure_id")), str(s.get("bioguide_id"))) for s in signals
                     if s.get("accepted") is True and s.get("bioguide_id")}
    global_scopes = {str(s.get("measure_id")) for s in signals
                     if s.get("accepted") is True and not s.get("bioguide_id")}
    bill_keys = ("measure_id", "congress", "chamber", "eligible", "measure_type", "introduced_date", "as_of", "exclusion_reason")
    bills, exclusions, pre_introduction = [], [], []
    for source in iter_rows(evidence / "bill_milestones.ndjson"):
        if not source.get("as_of") or str(source["as_of"]) < as_of:
            raise ValueError("Requested cutoff exceeds bill evidence vintage: " + str(source.get("measure_id")))
        row = {key: source.get(key) for key in bill_keys}
        row["milestones"] = {stage: {key: value.get(key) for key in ("reached", "state", "date", "basis")}
                             for stage, value in source.get("milestones", {}).items()}
        for stage, event in source.get("milestones", {}).items():
            if (event.get("date") and source.get("introduced_date")
                    and event["date"] < source["introduced_date"]):
                pre_introduction.append({"measure_id": row["measure_id"], "stage": stage,
                                         "date": event["date"], "introduced_date": source["introduced_date"],
                                         "basis": event.get("basis"), "evidence": event.get("evidence", []),
                                         "treatment": "preserved official chamber activity; no retroactive member credit"})
        reason = reserved_number_exclusion(source, selected)
        if reason:
            row.update(eligible=False, exclusion_reason=reason)
            exclusions.append({"measure_id": row["measure_id"], "reason": reason,
                               "source_record_sha256": source.get("source", {}).get("record_sha256")})
        bills.append(row)
    role_keys = ("measure_id", "bioguide_id", "role", "introduced_date", "joined_date",
                 "withdrawn_date", "chronology_status")
    roles, role_rows = [], 0
    for source in iter_rows(evidence / "member_measure_roles.ndjson"):
        role_rows += 1
        mid, bio = str(source.get("measure_id")), str(source.get("bioguide_id"))
        if mid in selected and (mid in global_scopes or (mid, bio) in member_scopes):
            roles.append({key: source.get(key) for key in role_keys})
    impact_keys = ("measure_id", "weight", "class", "baseline_class", "basis", "coverage_status",
                   "as_of", "effective_date", "policy")
    impacts = [{key: row.get(key) for key in impact_keys}
               for row in iter_rows(evidence / "bill_impact.ndjson")]
    roster = list(iter_rows(evidence / "member_population.ndjson"))
    letters = list(iter_rows(evidence / "congressional_letter_coverage.ndjson"))
    comparison = read_json(term_root / "data/engine/legislative_effectiveness_comparison_v1.json")
    if int(comparison.get("congress", -1)) != congress or str(comparison.get("as_of") or "") < as_of:
        raise ValueError("Comparison congress/cutoff does not cover requested replay")
    summary = {
        "source_bill_rows": len(bills), "retained_bill_rows": len(bills),
        "retained_selected_bill_rows": sum(b["measure_id"] in selected for b in bills),
        "source_role_rows": role_rows, "retained_selected_role_rows": len(roles),
        "accepted_signal_rows": len(signals), "accepted_unique_measures": len(selected),
        "historical_roster_rows": len(roster), "letter_documents": len(letters),
        "letter_rows_not_merged": sum(len(row.get("accepted_rows", [])) for row in letters),
        "letter_verification": dict(Counter(str(row.get("verification_status")) for row in letters)),
        "letter_policy": "Coverage receipts only; no invented signatures or law milestones.",
        "impact_rows": len(impacts),
        "selected_impact_weights": dict(Counter(str(i.get("weight")) for i in impacts if i["measure_id"] in selected)),
        "selected_impact_coverage": dict(Counter(str(i.get("coverage_status")) for i in impacts if i["measure_id"] in selected)),
        "impact_policy": "1/5/10 source weights. Provisional baseline is disclosed. No inferred significance upgrades.",
        "reserved_number_exclusions": exclusions,
        "pre_introduction_milestones": pre_introduction,
        "accepted_scope": read_json(evidence / "accepted_evidence_coverage.json"),
        "population": read_json(evidence / "population_receipt.json"),
    }
    return bills, roles, signals, roster, impacts, comparison, summary


def priority_key(row):
    """Independent adapter audit of the engine's priority ordering."""
    values = [-row["P"]]
    stopped = False
    for field in ("efficiency_score", "substance_score", "volume_score"):
        value = row.get(field) if not stopped else None
        stopped = stopped or value is None
        values.extend((int(value is None), -value if value is not None else 0))
    return tuple(values) + (row["bioguide_id"],)


def term_board(engine, metrics, comparison, base, helper, baseline):
    identities = comparison.get("members", {})
    identity_errors, metric_errors = [], []
    if set(identities) != set(base["rows"]):
        identity_errors.append({"rule": "comparison_roster_parity",
                                "missing": sorted(set(base["rows"]) - set(identities)),
                                "extra": sorted(set(identities) - set(base["rows"]))})
    records = []
    for name, published in base["rows"].items():
        identity = identities.get(name, {})
        bio = str(identity.get("bioguide") or "")
        valid_identity = bool(bio) and bio == str(published.get("bioguide") or "")
        if not valid_identity:
            identity_errors.append({"rule": "bioguide_parity", "member": name,
                                    "comparison": bio, "published": published.get("bioguide")})
        term_chamber = chamber(identity.get("chamber"))
        metric = metrics["members"].get(bio + "|" + term_chamber, {}) if valid_identity else {}
        row = {"name": name, "bioguide_id": str(published.get("bioguide") or ""),
               "chamber": published.get("chamber"), "term_chamber": term_chamber,
               "P": base["factors"].get(name),
               "legacy_rank": published.get("tierrank"), "legacy_tier": published.get("tier"),
               "legacy_rankable": name in base["rankable"],
               "strict_rank": None, "candidate_rank": None, "candidate_tier": None,
               "coverage": metric.get("coverage", {"historical_member_term_not_covered": 1}),
               "roles": metric.get("roles", {}), "stages": metric.get("stages", {})}
        for criterion in ("efficiency", "substance", "volume"):
            score, raw = metric.get(criterion + "_score"), metric.get(criterion + "_raw")
            if ((score is not None and (not finite(score) or not 0 <= score <= 1))
                    or (raw is not None and not finite(raw))
                    or (score is not None and raw is None)
                    or (criterion == "substance" and raw is not None and not 1 <= raw <= 10)
                    or (criterion == "volume" and raw is not None and raw < 0)):
                metric_errors.append({"rule": "invalid_metric", "member": name, "field": criterion})
                score = None
                if not finite(raw):
                    raw = None
            row.update({criterion + "_raw": raw, criterion + "_score": score,
                        criterion + "_status": metric.get(criterion + "_status", "historical_member_term_not_covered"),
                        criterion + "_peer_count": metric.get(criterion + "_peer_count")})
        for field in ("useful_volume", "harmful_volume", "neutral_volume", "unknown_volume"):
            row[field] = metric.get(field, 0)
        records.append(row)
    ranked = engine.rank_members(row for row in records if row["legacy_rankable"])
    strict_by_name = {row["name"]: row["candidate_rank"] for row in ranked}
    strict_order = [row["name"] for row in ranked if row["candidate_rank"] is not None]
    candidate, conduct, violations, policy = apply_policy(helper, strict_order, baseline)
    eligible_ranked = [row for row in ranked if row["candidate_rank"] is not None]
    strict_errors = []
    for left, right in zip(eligible_ranked, eligible_ranked[1:]):
        if priority_key(left) > priority_key(right):
            strict_errors.append({"rule": "four_priority_precedence", "left": left["name"], "right": right["name"]})
    permitted = base["passed"] and not (identity_errors or metric_errors or violations or strict_errors)
    for row in records:
        row["strict_rank"] = strict_by_name.get(row["name"])
        row["conduct"] = conduct.get(row["name"], {})
        if permitted and row["name"] in candidate:
            row["candidate_rank"] = candidate[row["name"]]["rank"]
            row["candidate_tier"] = candidate[row["name"]]["tier"]
    records.sort(key=lambda row: (row["candidate_rank"] or row["strict_rank"] or 10**9, row["name"]))
    summary = {"members": len(records), "useful_measures": sum(row["useful_volume"] for row in records),
               "tier_changes": sum(row["candidate_tier"] != row["legacy_tier"] for row in records) if permitted else None,
               "rank_changes": sum(row["candidate_rank"] != row["legacy_rank"] for row in records) if permitted else None}
    for criterion in ("efficiency", "substance", "volume"):
        summary[criterion + "_observed"] = sum(row[criterion + "_score"] is not None for row in records)
        summary[criterion + "_unknown"] = sum(row[criterion + "_score"] is None for row in records)
    return {"congress": metrics["congress"], "as_of": metrics["as_of"], "policy": metrics["policy"],
            "candidate_tiers_available": permitted, "members": records, "tier_policy": policy,
            "gates": {"identity_parity": not identity_errors, "valid_normalized_metrics": not metric_errors,
                      "four_priority_precedence": not strict_errors, "final_tier_constraints": not violations,
                      "baseline_reproduced": base["passed"]},
            "gate_errors": identity_errors + metric_errors + violations + strict_errors, "summary": summary}


def reporting_module():
    return load_module("_pesv_reporting", CODE_ROOT / "reporting.py")


def markdown_report(board):
    return reporting_module().markdown_report(board)


def review_html(board):
    return reporting_module().review_html(board)


def run(args):
    source, shadow = Path(args.source_root).resolve(), Path(args.shadow_root).resolve()
    output, staging = validate_output(args.output_root, source, shadow)
    cutoff = date.fromisoformat(args.as_of).isoformat()
    congresses = list(dict.fromkeys(args.congress))
    source_paths = [source / relative for relative in BASELINE_FILES]
    evidence_paths = [shadow / str(term) / relative for term in congresses for relative in TERM_FILES]
    code_paths = [Path(__file__).resolve(), CODE_ROOT / "pesv.py", CODE_ROOT / "reporting.py"]
    all_paths = source_paths + evidence_paths + code_paths
    for path in all_paths:
        if not path.is_file():
            raise FileNotFoundError("Required local input missing: " + str(path))
    initial = hashes(all_paths)
    staging.mkdir(parents=True, exist_ok=False)
    baseline = staging / "baseline"
    receipt = {"schema": "pesv-replay-receipt-v1", "status": "building", "production_activation": False,
               "as_of": cutoff, "congresses": congresses, "inputs_sha256": initial,
               "output_root": str(output), "source_root": str(source), "shadow_root": str(shadow)}
    write_json(staging / "receipt.json", receipt)
    try:
        for relative in BASELINE_FILES:
            target = baseline / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source / relative, target)
            if sha256(target) != initial[str((source / relative).resolve())]:
                raise RuntimeError("Source changed while taking snapshot: " + relative)
        for path in code_paths:
            target = staging / "code" / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
            if sha256(target) != initial[str(path.resolve())]:
                raise RuntimeError("Candidate source changed during snapshot: " + str(path))
        engine = load_module("_pesv_replay_engine", staging / "code/pesv.py")
        renderer = load_module("_pesv_snapshot_reporting", staging / "code/reporting.py")
        board = {"schema": "pesv-board-v1", "status": "candidate", "production_activation": False,
                 "as_of": cutoff, "default_congress": congresses[0], "terms": {}}
        with copied_helpers(baseline) as (helper, helper_paths):
            base = reproduce_baseline(helper, baseline)
            board["baseline"] = {"status": base["status"], "passed": base["passed"],
                                 "member_count": len(base["rows"]), "rankable_count": len(base["rankable"]),
                                 "errors": base["errors"], "tier_policy": base["policy"]}
            receipt["helper_paths_at_execution"] = helper_paths
            with (staging / "contributions.ndjson").open("w", encoding="utf-8", newline="\n") as traces:
                for congress in congresses:
                    print(f"PESV {congress}: reading frozen evidence", flush=True)
                    bills, roles, signals, roster, impacts, comparison, coverage = compact_term(shadow / str(congress), congress, cutoff)
                    metrics = engine.compute_metrics(bills, roles, signals, roster, impacts, congress=congress,
                                                     as_of=cutoff, policy=engine.Policy(
                                                         cosponsor_half_life_days=args.cosponsor_half_life_days))
                    result = term_board(engine, metrics, comparison, base, helper, baseline)
                    result["input_coverage"] = coverage
                    result["historical_metrics"] = metrics["members"]
                    result["chamber_terms"] = metrics.get("terms", {})
                    result["chamber_diagnostics"] = metrics.get("chamber_diagnostics", {})
                    board["terms"][str(congress)] = result
                    for row in metrics["contributions"]:
                        traces.write(json.dumps(dict(row, congress=congress), ensure_ascii=False,
                                                sort_keys=True, allow_nan=False) + "\n")
                    print(f"PESV {congress}: {result['summary']['efficiency_observed']}/533 observed; "
                          f"candidate tiers {'available' if result['candidate_tiers_available'] else 'withheld'}", flush=True)
                    del bills, roles, signals, roster, impacts, comparison, metrics
        complete = all(term["candidate_tiers_available"] for term in board["terms"].values())
        board["status"] = "complete_candidate" if complete else "failed_candidate_gates"
        write_json(staging / "board.json", board)
        (staging / "report.md").write_text(renderer.markdown_report(board), encoding="utf-8")
        (staging / "review.html").write_text(renderer.review_html(board), encoding="utf-8")
        final = hashes(all_paths)
        drift = [path for path in initial if initial[path] != final[path]]
        if drift:
            receipt.update(status="failed", source_hashes_unchanged=False, drifted_paths=drift,
                           final_inputs_sha256=final)
            raise RuntimeError("Read-only source or candidate code changed during replay: " + ", ".join(drift))
        receipt.update(status="complete" if complete else "failed", source_hashes_unchanged=True,
                       baseline_reproduced=base["passed"],
                       completed_utc=datetime.now(timezone.utc).isoformat(),
                       gates={term: result["gates"] for term, result in board["terms"].items()},
                       outputs_sha256={str(path.relative_to(staging)).replace("\\", "/"): sha256(path)
                                       for path in sorted(staging.rglob("*")) if path.is_file() and path.name != "receipt.json"})
        write_json(staging / "receipt.json", receipt)
        if output.exists():
            output.rmdir()  # Validation allowed only an empty, dedicated output directory.
        os.replace(staging, output)
        print(f"PESV {'COMPLETE CANDIDATE' if complete else 'FAILED GATES'}: {output}", flush=True)
        return 0 if complete else 2
    except Exception as exc:
        receipt.update(status="failed", error=f"{type(exc).__name__}: {exc}", production_activation=False)
        write_json(staging / "receipt.json", receipt)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, help="Read-only production root")
    parser.add_argument("--shadow-root", required=True, help="Frozen shadow root containing Congress directories")
    parser.add_argument("--output-root", required=True, help="Dedicated new isolated generation directory")
    parser.add_argument("--congress", nargs="+", type=int, default=[118], choices=(118, 119))
    parser.add_argument("--as-of", default="2026-09-06")
    parser.add_argument("--cosponsor-half-life-days", type=float, default=180.,
                        help="Illustrative source policy, not empirically calibrated (default: 180)")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Exception as exc:
        print(f"PESV FAILED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
