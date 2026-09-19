"""Build an isolated, receipted P/E/V comparison from frozen local evidence.

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
    old_modules = {key: sys.modules.get(key) for key in ("paths", "_pev_snapshot_tier_util")}
    old_path = list(sys.path)
    try:
        os.environ.update(settings)
        paths = load_module("paths", baseline / "fec/paths.py")
        helper = load_module("_pev_snapshot_tier_util", baseline / "fec/tier_util.py")
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


def compact_term(term_root, congress, as_of):
    """Read large NDJSON files linewise, retaining only selected compact records."""
    evidence = term_root / "data/legislation"
    signals = list(iter_rows(evidence / "accepted_signals.ndjson"))
    selected = {str(s.get("measure_id")) for s in signals if s.get("accepted") is True}
    member_scopes = {(str(s.get("measure_id")), str(s.get("bioguide_id"))) for s in signals
                     if s.get("accepted") is True and s.get("bioguide_id")}
    global_scopes = {str(s.get("measure_id")) for s in signals
                     if s.get("accepted") is True and not s.get("bioguide_id")}
    bill_keys = ("measure_id", "congress", "chamber", "eligible", "measure_type", "introduced_date", "as_of")
    bills = []
    bill_rows = 0
    for source in iter_rows(evidence / "bill_milestones.ndjson"):
        bill_rows += 1
        if source.get("measure_id") not in selected:
            continue
        frozen_cutoff = source.get("as_of")
        if not frozen_cutoff or str(frozen_cutoff) < as_of:
            raise ValueError("Requested cutoff exceeds selected bill evidence vintage: " + str(source.get("measure_id")))
        row = {key: source.get(key) for key in bill_keys}
        row["milestones"] = {stage: {key: value.get(key) for key in ("reached", "state", "date")}
                             for stage, value in source.get("milestones", {}).items()}
        bills.append(row)
    role_keys = ("measure_id", "bioguide_id", "role", "introduced_date", "joined_date",
                 "withdrawn_date", "chronology_status")
    roles = []
    role_rows = 0
    for source in iter_rows(evidence / "member_measure_roles.ndjson"):
        role_rows += 1
        mid, bio = str(source.get("measure_id")), str(source.get("bioguide_id"))
        if mid in selected and (mid in global_scopes or (mid, bio) in member_scopes):
            roles.append({key: source.get(key) for key in role_keys})
    roster = list(iter_rows(evidence / "member_population.ndjson"))
    letters = list(iter_rows(evidence / "congressional_letter_coverage.ndjson"))
    comparison = read_json(term_root / "data/engine/legislative_effectiveness_comparison_v1.json")
    if int(comparison.get("congress", -1)) != congress or str(comparison.get("as_of") or "") < as_of:
        raise ValueError("Comparison congress/cutoff does not cover requested replay")
    summary = {
        "source_bill_rows": bill_rows, "retained_selected_bill_rows": len(bills),
        "source_role_rows": role_rows, "retained_selected_role_rows": len(roles),
        "accepted_signal_rows": len(signals), "accepted_unique_measures": len(selected),
        "historical_roster_rows": len(roster), "letter_documents": len(letters),
        "letter_rows_not_merged": sum(len(row.get("accepted_rows", [])) for row in letters),
        "letter_verification": dict(Counter(str(row.get("verification_status")) for row in letters)),
        "letter_policy": "Coverage receipts only; no invented signatures, opportunities or law milestones.",
        "impact_policy": "Impact artifact hashed for provenance; no impact/media multiplier in this P/E/V candidate.",
        "accepted_scope": read_json(evidence / "accepted_evidence_coverage.json"),
        "population": read_json(evidence / "population_receipt.json"),
    }
    return bills, roles, signals, roster, comparison, summary


def term_board(engine, metrics, comparison, base, helper, baseline):
    identities = comparison.get("members", {})
    identity_errors = []
    if set(identities) != set(base["rows"]):
        identity_errors.append({"rule": "comparison_roster_parity",
                                "missing": sorted(set(base["rows"]) - set(identities)),
                                "extra": sorted(set(identities) - set(base["rows"]))})
    records = []
    metric_errors = []
    for name, published in base["rows"].items():
        identity = identities.get(name, {})
        bio = str(identity.get("bioguide") or "")
        valid_identity = bool(bio) and bio == str(published.get("bioguide") or "")
        if not valid_identity:
            identity_errors.append({"rule": "bioguide_parity", "member": name,
                                    "comparison": bio, "published": published.get("bioguide")})
        term_chamber = chamber(identity.get("chamber"))
        metric = metrics["members"].get(bio + "|" + term_chamber, {}) if valid_identity else {}
        lower = metric.get("efficiency_score")
        percentile = metric.get("efficiency_percentile")
        if lower is not None and percentile is None:
            metric_errors.append({"rule": "missing_chamber_percentile", "member": name})
        for field, value in (("efficiency_lower", lower), ("efficiency_score", percentile)):
            if value is not None and (not finite(value) or not 0 <= value <= 1):
                metric_errors.append({"rule": "invalid_metric", "member": name, "field": field})
        records.append({
            "name": name, "bioguide_id": str(published.get("bioguide") or ""),
            "chamber": published.get("chamber"), "term_chamber": term_chamber,
            "P": base["factors"].get(name), "efficiency_raw": metric.get("efficiency_raw"),
            "efficiency_lower": lower, "efficiency_score": percentile,
            "efficiency_percentile": percentile,
            "efficiency_peer_count": metric.get("efficiency_peer_count", metric.get("percentile_peer_count")),
            "eligible_attempts": metric.get("eligible_attempts", 0), "successes": metric.get("successes", 0),
            "useful_volume": metric.get("useful_volume", 0),
            "harmful_volume": metric.get("harmful_volume", 0),
            "neutral_volume": metric.get("neutral_volume", 0),
            "unknown_volume": metric.get("unknown_volume", 0),
            "efficiency_status": metric.get("efficiency_status", "historical_member_term_not_covered"),
            "coverage": metric.get("coverage", {"historical_member_term_not_covered": 1}),
            "roles": metric.get("roles", {}), "stages": metric.get("stages", {}),
            "legacy_rank": published.get("tierrank"), "legacy_tier": published.get("tier"),
            "legacy_rankable": name in base["rankable"],
            "strict_rank": None, "candidate_rank": None, "candidate_tier": None,
        })
    ranked = engine.rank_members(row for row in records if row["legacy_rankable"])
    strict_by_name = {row["name"]: row["candidate_rank"] for row in ranked}
    strict_order = [row["name"] for row in ranked if row["candidate_rank"] is not None]
    candidate, conduct, violations, policy = apply_policy(helper, strict_order, baseline)
    strict_errors = []
    for left, right in zip(ranked, ranked[1:]):
        if left["P"] is not None and right["P"] is not None and left["P"] < right["P"]:
            strict_errors.append({"rule": "primacy_precedence", "left": left["name"], "right": right["name"]})
    permitted = base["passed"] and not (identity_errors or metric_errors or violations or strict_errors)
    for row in records:
        row["strict_rank"] = strict_by_name.get(row["name"])
        row["conduct"] = conduct.get(row["name"], {})
        if permitted and row["name"] in candidate:
            row["candidate_rank"] = candidate[row["name"]]["rank"]
            row["candidate_tier"] = candidate[row["name"]]["tier"]
    records.sort(key=lambda row: (row["candidate_rank"] or row["strict_rank"] or 10**9, row["name"]))
    return {"congress": metrics["congress"], "as_of": metrics["as_of"], "policy": metrics["policy"],
            "candidate_tiers_available": permitted, "members": records, "tier_policy": policy,
            "gates": {"identity_parity": not identity_errors, "valid_normalized_metrics": not metric_errors,
                      "strict_primacy_precedence": not strict_errors, "final_tier_constraints": not violations,
                      "baseline_reproduced": base["passed"]},
            "gate_errors": identity_errors + metric_errors + violations + strict_errors,
            "summary": {"members": len(records),
                        "efficiency_observed": sum(row["efficiency_score"] is not None for row in records),
                        "efficiency_unknown": sum(row["efficiency_score"] is None for row in records),
                        "matched_opportunities": sum(row["eligible_attempts"] for row in records),
                        "successful_opportunities": sum(row["successes"] for row in records),
                        "tier_changes": sum(row["candidate_tier"] != row["legacy_tier"] for row in records) if permitted else None,
                        "rank_changes": sum(row["candidate_rank"] != row["legacy_rank"] for row in records) if permitted else None}}


def markdown_report(board):
    lines = ["# Primacy / Efficiency / Volume candidate replay", "",
             "This is an isolated, reviewable candidate. It does not change the live board or reporting ranks.", "",
             f"Baseline: **{board['baseline']['status']}**. Cutoff: {board['as_of']}.", "",
             "The comparison preserves the published primacy factor and the existing board's eligibility, evidence floor, overrides and conduct rules. Efficiency is the within-chamber percentile of the Wilson-adjusted observed conversion rate, calculated across all available historical roster records. Volume breaks remaining known-efficiency ties. Terms are separate; no term pooling is introduced.", "",
             "Conversion means any additional stage reached while the member is signed on, during a fully observed 180-day window after joining. These are retrospective descriptive measures, not validated predictions or causal credit. Missing coverage stays unavailable; letters without verified dated signatures stay outside the opportunities.", ""]
    if board["baseline"]["errors"]:
        lines += ["Baseline parity failed. Candidate tier assignments are withheld.", "",
                  "```json", json.dumps(board["baseline"]["errors"][:30], indent=2), "```", ""]
    for term in board["terms"].values():
        summary = term["summary"]
        lines += [f"## Congress {term['congress']}", "",
                  f"Candidate tiers available: **{term['candidate_tiers_available']}**. "
                  f"Observed efficiency: {summary['efficiency_observed']}/{summary['members']}; "
                  f"unavailable: {summary['efficiency_unknown']}. "
                  f"Successful / fully observed opportunities: {summary['successful_opportunities']}/{summary['matched_opportunities']}.", "",
                  f"Ranks changed: {summary['rank_changes']}; tiers changed: {summary['tier_changes']}.", "",
                  "| Member | P | E percentile | Wilson lower | k/n | Volume | Legacy rank/tier | Candidate rank/tier |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for row in term["members"][:20]:
            number = lambda value: "unavailable" if value is None else f"{value:.6f}"
            lines.append(f"| {row['name']} | {number(row['P'])} | {number(row['efficiency_score'])} | {number(row['efficiency_lower'])} | {row['successes']}/{row['eligible_attempts']} | {row['useful_volume']} | {row['legacy_rank']}/{row['legacy_tier']} | {row['candidate_rank']}/{row['candidate_tier']} |")
        lines += ["", "These are the first 20 rows of the candidate order, or the analytical strict order if tier publication is withheld. Full member records, coverage and traces are in board.json and opportunities.ndjson.", ""]
        if term["gate_errors"]:
            lines += ["Gate failures:", "", "```json", json.dumps(term["gate_errors"][:30], indent=2), "```", ""]
    return "\n".join(lines)


def review_html(board):
    payload = json.dumps(board, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    return """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Primacy / Efficiency / Volume review</title><style>
:root{font-family:Segoe UI,Arial,sans-serif;color:#172b40;background:#f2f5f8}*{box-sizing:border-box}body{margin:0}header{padding:32px max(24px,4vw);background:#152f49;color:white}h1{font-size:28px;margin:0 0 8px}p{line-height:1.55}header p{max-width:1000px;margin:8px 0;color:#dbe6ef}main{padding:24px max(24px,4vw)}.controls{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}input,select{font:inherit;padding:10px 12px;border:1px solid #b6c5d2;border-radius:6px}input{flex:1;min-width:240px}.cards{display:flex;gap:14px;flex-wrap:wrap}.card{background:white;padding:18px;border:1px solid #d8e1e9;border-radius:8px;min-width:190px}.card strong{display:block;font-size:24px;margin-bottom:4px}.note{background:#fff8df;border-left:4px solid #ae8734;padding:14px 18px}.table{overflow:auto;border:1px solid #d8e1e9;border-radius:8px;background:white}table{border-collapse:collapse;width:100%;font-size:13px;white-space:nowrap}th,td{text-align:right;padding:11px 10px;border-bottom:1px solid #e5eaf0}th{background:#e8eff5;position:sticky;top:0}td:nth-child(2),th:nth-child(2),td:nth-child(9),th:nth-child(9){text-align:left}tbody tr:hover{background:#f1f6fb}.muted{color:#52677a;font-size:13px}.changed{background:#f8ecd1}details{margin:20px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#075eaa}</style>
<header><h1>Primacy → Efficiency → Volume</h1><p>Isolated candidate review · preserved primacy, observed conversion, useful legislative volume.</p><p>Efficiency percentile ranks the Wilson lower score within the member's historical chamber. Raw rate and k/n remain visible. Terms are shown separately.</p></header>
<main><div id="notice" class="note"></div><div class="controls"><select id="term" aria-label="Congress"></select><input id="search" placeholder="Search member, chamber or coverage status" aria-label="Search members"></div><div class="cards" id="cards"></div><p class="muted" id="count"></p>
<div class="table"><table><thead><tr><th>Strict rank</th><th>Member / chamber</th><th>P</th><th>E percentile</th><th>Raw rate</th><th>Wilson lower</th><th>k / n</th><th>Volume</th><th>Coverage</th><th>Legacy rank / tier</th><th>Candidate rank / tier</th></tr></thead><tbody id="rows"></tbody></table></div>
<p class="muted">P always takes precedence. Known efficiency precedes unavailable efficiency only at equal P; useful volume breaks remaining known-efficiency ties. Existing tier rules may subsequently move a member. “Unavailable” is not an observed failure.</p>
<details><summary>Method, coverage and audit gates</summary><p>Any advancement beyond the stage reached before joining counts once per positive CU member–measure in a fully observed 180-day horizon. Unknown alignment, chronology or service is retained in coverage; unverified letters are excluded. This is a retrospective comparison, not a predictive validation or an estimate of lobbying return on investment.</p><pre id="audit"></pre></details>
<p><a href="board.json">Full board data</a> · <a href="opportunities.ndjson">Opportunity traces</a> · <a href="receipt.json">Generation receipt</a> · <a href="report.md">Report</a></p></main>
<script id="data" type="application/json">""" + payload + """</script><script>
const data=JSON.parse(document.getElementById('data').textContent), term=document.getElementById('term'), search=document.getElementById('search');
Object.keys(data.terms).forEach(k=>{const o=document.createElement('option');o.value=k;o.textContent='Congress '+k;term.append(o)});term.value=String(data.default_congress);
const fmt=(v,p=5)=>v==null?'—':Number(v).toFixed(p), pct=v=>v==null?'—':(v*100).toFixed(1)+'%';
function draw(){const t=data.terms[term.value],q=search.value.toLowerCase(),rows=t.members.filter(r=>(r.name+' '+r.chamber+' '+r.term_chamber+' '+r.efficiency_status).toLowerCase().includes(q));
document.getElementById('notice').textContent=t.candidate_tiers_available?'Candidate only. Live production is unchanged. Baseline tiers and ranks reproduce the frozen published board.':'Candidate tier assignments withheld: baseline parity or an audit gate failed. The table retains the analytical strict order and evidence.';
const cards=document.getElementById('cards');cards.replaceChildren();[['Members',t.summary.members],['Observed efficiency',t.summary.efficiency_observed],['Tier changes',t.summary.tier_changes??'Withheld'],['Rank changes',t.summary.rank_changes??'Withheld']].forEach(([label,value])=>{const c=document.createElement('div');c.className='card';const v=document.createElement('strong');v.textContent=value;c.append(v,document.createTextNode(label));cards.append(c)});
document.getElementById('count').textContent=rows.length+' members shown · cutoff '+t.as_of+' · ordered by candidate rank, then analytical strict rank';const tbody=document.getElementById('rows');tbody.replaceChildren();
rows.forEach(r=>{const tr=document.createElement('tr');[r.strict_rank??'—',r.name+' / '+r.term_chamber,fmt(r.P,6),pct(r.efficiency_score),pct(r.efficiency_raw),pct(r.efficiency_lower),r.successes+' / '+r.eligible_attempts,r.useful_volume,r.efficiency_status.replaceAll('_',' '),(r.legacy_rank??'—')+' / '+(r.legacy_tier??'—'),(r.candidate_rank??'—')+' / '+(r.candidate_tier??'—')].forEach((value,i)=>{const td=document.createElement('td');td.textContent=value;if(i===10&&r.candidate_tier!=null&&r.candidate_tier!==r.legacy_tier)td.className='changed';tr.append(td)});tr.title=JSON.stringify(r.coverage);tbody.append(tr)});
document.getElementById('audit').textContent=JSON.stringify({baseline:data.baseline,policy:t.policy,gates:t.gates,errors:t.gate_errors,coverage:t.input_coverage},null,2)}
term.addEventListener('change',draw);search.addEventListener('input',draw);draw();</script></html>"""


def run(args):
    source, shadow = Path(args.source_root).resolve(), Path(args.shadow_root).resolve()
    output, staging = validate_output(args.output_root, source, shadow)
    cutoff = date.fromisoformat(args.as_of).isoformat()
    congresses = list(dict.fromkeys(args.congress))
    source_paths = [source / relative for relative in BASELINE_FILES]
    evidence_paths = [shadow / str(term) / relative for term in congresses for relative in TERM_FILES]
    code_paths = [Path(__file__).resolve(), CODE_ROOT / "pev.py"]
    all_paths = source_paths + evidence_paths + code_paths
    for path in all_paths:
        if not path.is_file():
            raise FileNotFoundError("Required local input missing: " + str(path))
    initial = hashes(all_paths)
    staging.mkdir(parents=True, exist_ok=False)
    baseline = staging / "baseline"
    receipt = {"schema": "pev-replay-receipt-v1", "status": "building", "production_activation": False,
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
        engine = load_module("_pev_replay_engine", staging / "code/pev.py")
        board = {"schema": "pev-board-v1", "status": "candidate", "production_activation": False,
                 "as_of": cutoff, "default_congress": congresses[0], "terms": {}}
        with copied_helpers(baseline) as (helper, helper_paths):
            base = reproduce_baseline(helper, baseline)
            board["baseline"] = {"status": base["status"], "passed": base["passed"],
                                 "member_count": len(base["rows"]), "rankable_count": len(base["rankable"]),
                                 "errors": base["errors"], "tier_policy": base["policy"]}
            receipt["helper_paths_at_execution"] = helper_paths
            with (staging / "opportunities.ndjson").open("w", encoding="utf-8", newline="\n") as traces:
                for congress in congresses:
                    print(f"PEV {congress}: reading frozen evidence", flush=True)
                    bills, roles, signals, roster, comparison, coverage = compact_term(shadow / str(congress), congress, cutoff)
                    metrics = engine.compute_metrics(bills, roles, signals, roster, congress=congress,
                                                     as_of=cutoff, policy=engine.Policy())
                    result = term_board(engine, metrics, comparison, base, helper, baseline)
                    result["input_coverage"] = coverage
                    result["historical_metrics"] = metrics["members"]
                    board["terms"][str(congress)] = result
                    for row in metrics["opportunities"]:
                        traces.write(json.dumps(dict(row, congress=congress), ensure_ascii=False,
                                                sort_keys=True, allow_nan=False) + "\n")
                    print(f"PEV {congress}: {result['summary']['efficiency_observed']}/533 observed; "
                          f"candidate tiers {'available' if result['candidate_tiers_available'] else 'withheld'}", flush=True)
                    del bills, roles, signals, roster, comparison, metrics
        complete = all(term["candidate_tiers_available"] for term in board["terms"].values())
        board["status"] = "complete_candidate" if complete else "failed_candidate_gates"
        write_json(staging / "board.json", board)
        (staging / "report.md").write_text(markdown_report(board), encoding="utf-8")
        (staging / "review.html").write_text(review_html(board), encoding="utf-8")
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
        print(f"PEV {'COMPLETE CANDIDATE' if complete else 'FAILED GATES'}: {output}", flush=True)
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
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Exception as exc:
        print(f"PEV FAILED: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
