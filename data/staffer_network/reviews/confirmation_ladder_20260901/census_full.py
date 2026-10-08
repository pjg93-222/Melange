import gzip, json, hashlib
from collections import Counter, defaultdict

AUD = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network"
V3 = AUD + r"\employment_adjudication_generation_20260901_v3_primary"
V3T = AUD + r"\employment_adjudication_generation_20260901_v3_twin"
A9 = AUD + r"\a9_a7_a8_priority_sidecar_20260901_primary\a9_a7_a8_priority_sidecar_25340.ndjson.gz"
V5 = AUD + r"\employment_promotion_generation_20260901_v5_primary"

out = {}

def stream(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)

def sha256_file(path, bufsize=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return h.hexdigest()

def top_n(counter, n=15):
    return counter.most_common(n)

# ---------------------------------------------------------------
# A.1 twin sha256 verification for v3 adjudication generation
# ---------------------------------------------------------------
twin_files = ["candidate_adjudication_decisions.ndjson.gz", "provisional_employment_episodes.ndjson.gz",
              "employment_adjudication_person_summary_25340.ndjson.gz",
              "covered_position_parser_gold_sample_100.ndjson.gz", "identity_rule_gold_sample_200.ndjson.gz"]
twin_check = {}
for fn in twin_files:
    p_sha = sha256_file(V3 + "\\" + fn)
    t_sha = sha256_file(V3T + "\\" + fn)
    twin_check[fn] = {"primary_sha256": p_sha, "twin_sha256": t_sha, "match": p_sha == t_sha}
out["A1_twin_check"] = twin_check

# ---------------------------------------------------------------
# A.2 candidate_adjudication_decisions.ndjson.gz
# ---------------------------------------------------------------
path = V3 + r"\candidate_adjudication_decisions.ndjson.gz"
total = 0
by_decision = Counter()
by_lane = Counter()
decision_lane = Counter()
distinct_person = set()
distinct_person_by_decision = defaultdict(set)
rationale_codes = Counter()
for rec in stream(path):
    total += 1
    d = rec.get("decision")
    l = rec.get("lane")
    pid = rec.get("lda_source_person_id")
    by_decision[d] += 1
    by_lane[l] += 1
    decision_lane[(d, l)] += 1
    if pid is not None:
        distinct_person.add(pid)
        distinct_person_by_decision[d].add(pid)
    for code in (rec.get("rationale_codes") or []):
        rationale_codes[code] += 1

out["A2_candidate_adjudication_decisions"] = {
    "field_names_used": {"decision": "decision", "lane": "lane", "person_id": "lda_source_person_id",
                          "blocker_reason_field": "rationale_codes (list)"},
    "total_rows": total,
    "by_decision": dict(by_decision),
    "by_lane": dict(by_lane),
    "decision_x_lane": {f"{d}||{l}": c for (d, l), c in decision_lane.items()},
    "distinct_lda_source_person_id_overall": len(distinct_person),
    "distinct_lda_source_person_id_by_decision": {d: len(s) for d, s in distinct_person_by_decision.items()},
    "top15_rationale_codes": top_n(rationale_codes, 15),
    "distinct_rationale_code_count": len(rationale_codes),
}

# ---------------------------------------------------------------
# A.3 provisional_employment_episodes.ndjson.gz
# ---------------------------------------------------------------
path = V3 + r"\provisional_employment_episodes.ndjson.gz"
total = 0
distinct_person = set()
by_evidence_lane = Counter()
by_temporal_semantics = Counter()
by_identity_status = Counter()
bounded_earliest = 0
start_only_earliest = 0
end_only_earliest = 0
neither_earliest = 0
bounded_latest = 0
start_only_latest = 0
end_only_latest = 0
neither_latest = 0
start_precision_c = Counter()
end_precision_c = Counter()
min_start = None
max_start = None
min_end = None
max_end = None
promotion_blockers_c = Counter()

for rec in stream(path):
    total += 1
    pid = rec.get("lda_source_person_id")
    if pid is not None:
        distinct_person.add(pid)
    for lane in (rec.get("evidence_lanes") or []):
        by_evidence_lane[lane] += 1
    by_temporal_semantics[rec.get("temporal_semantics")] += 1
    by_identity_status[rec.get("identity_status")] += 1

    se = rec.get("valid_start_earliest")
    sl = rec.get("valid_start_latest")
    ee = rec.get("valid_end_earliest")
    el = rec.get("valid_end_latest")

    if se is not None and ee is not None:
        bounded_earliest += 1
    elif se is not None:
        start_only_earliest += 1
    elif ee is not None:
        end_only_earliest += 1
    else:
        neither_earliest += 1

    if sl is not None and el is not None:
        bounded_latest += 1
    elif sl is not None:
        start_only_latest += 1
    elif el is not None:
        end_only_latest += 1
    else:
        neither_latest += 1

    start_precision_c[rec.get("start_precision")] += 1
    end_precision_c[rec.get("end_precision")] += 1

    if se is not None:
        if min_start is None or se < min_start:
            min_start = se
        if max_start is None or se > max_start:
            max_start = se
    if ee is not None:
        if min_end is None or ee < min_end:
            min_end = ee
        if max_end is None or ee > max_end:
            max_end = ee

    for code in (rec.get("promotion_blockers") or []):
        promotion_blockers_c[code] += 1

out["A3_provisional_employment_episodes"] = {
    "field_names_used": {
        "person_id": "lda_source_person_id",
        "evidence_lanes_field": "evidence_lanes (list)",
        "temporal_semantics_field": "temporal_semantics",
        "identity_status_field": "identity_status",
        "start_date_fields": ["valid_start_earliest", "valid_start_latest"],
        "end_date_fields": ["valid_end_earliest", "valid_end_latest"],
        "start_precision_field": "start_precision",
        "end_precision_field": "end_precision",
        "promotion_blockers_field": "promotion_blockers (list)",
    },
    "total_rows": total,
    "distinct_lda_source_person_id": len(distinct_person),
    "by_evidence_lanes": dict(by_evidence_lane),
    "by_temporal_semantics": dict(by_temporal_semantics),
    "by_identity_status": dict(by_identity_status),
    "bounded_using_earliest_fields": {"bounded": bounded_earliest, "start_only": start_only_earliest,
                                       "end_only": end_only_earliest, "neither": neither_earliest},
    "bounded_using_latest_fields": {"bounded": bounded_latest, "start_only": start_only_latest,
                                     "end_only": end_only_latest, "neither": neither_latest},
    "start_precision_distribution": dict(start_precision_c),
    "end_precision_distribution": dict(end_precision_c),
    "min_start_earliest": min_start,
    "max_start_earliest": max_start,
    "min_end_earliest": min_end,
    "max_end_earliest": max_end,
    "promotion_blockers_frequency": dict(promotion_blockers_c),
}

# ---------------------------------------------------------------
# A.4 employment_adjudication_person_summary_25340.ndjson.gz
# ---------------------------------------------------------------
path = V3 + r"\employment_adjudication_person_summary_25340.ndjson.gz"
total = 0
by_state = Counter()
by_native_status = Counter()
open_gate_codes_c = Counter()
cnt_canonical_promoted_gt0 = 0
cnt_final_episode_gt0 = 0
cnt_primary_temporal_eligible_gt0 = 0
cnt_provisional_episode_gt0 = 0
cnt_decision_counts_sum_gt0 = 0
person_summary_ids = set()

for rec in stream(path):
    total += 1
    pid = rec.get("lda_source_person_id")
    if pid is not None:
        person_summary_ids.add(pid)
    by_state[rec.get("adjudication_state")] += 1
    by_native_status[rec.get("source_native_identity_status")] += 1
    for code in (rec.get("open_gate_codes") or []):
        open_gate_codes_c[code] += 1
    if (rec.get("canonical_employment_promoted_count") or 0) > 0:
        cnt_canonical_promoted_gt0 += 1
    if (rec.get("final_episode_count") or 0) > 0:
        cnt_final_episode_gt0 += 1
    if (rec.get("primary_temporal_eligible_episode_count") or 0) > 0:
        cnt_primary_temporal_eligible_gt0 += 1
    if (rec.get("provisional_episode_count") or 0) > 0:
        cnt_provisional_episode_gt0 += 1
    dc = rec.get("decision_counts") or {}
    if sum(dc.values()) > 0:
        cnt_decision_counts_sum_gt0 += 1

out["A4_person_summary"] = {
    "note": "No literal field named 'candidate_count' exists on this schema. Candidate/episode count fields present are: canonical_employment_promoted_count, final_episode_count, primary_temporal_eligible_episode_count, provisional_episode_count, and the per-lane:status dict decision_counts.",
    "total_rows": total,
    "distinct_lda_source_person_id": len(person_summary_ids),
    "by_adjudication_state": dict(by_state),
    "by_source_native_identity_status": dict(by_native_status),
    "open_gate_codes_frequency": dict(open_gate_codes_c),
    "rows_with_canonical_employment_promoted_count_gt0": cnt_canonical_promoted_gt0,
    "rows_with_final_episode_count_gt0": cnt_final_episode_gt0,
    "rows_with_primary_temporal_eligible_episode_count_gt0": cnt_primary_temporal_eligible_gt0,
    "rows_with_provisional_episode_count_gt0": cnt_provisional_episode_gt0,
    "rows_with_sum_decision_counts_gt0": cnt_decision_counts_sum_gt0,
}

# ---------------------------------------------------------------
# A.5 cross-tab: person_summary.adjudication_state x a9.revised_priority.priority_bucket
# ---------------------------------------------------------------
person_state = {}
for rec in stream(path):
    person_state[rec.get("lda_source_person_id")] = rec.get("adjudication_state")

a9_bucket = {}
a9_ids = set()
for rec in stream(A9):
    pid = rec.get("lda_source_person_id")
    a9_ids.add(pid)
    rp = rec.get("revised_priority") or {}
    a9_bucket[pid] = rp.get("priority_bucket")

ps_ids = set(person_state.keys())
cross = Counter()
for pid, state in person_state.items():
    bucket = a9_bucket.get(pid, "__NOT_IN_A9__")
    cross[(state, bucket)] += 1

out["A5_person_summary_x_a9_priority_bucket"] = {
    "join_key": "lda_source_person_id",
    "a9_field_used_for_revised_priority_bucket": "revised_priority.priority_bucket (nested object)",
    "person_summary_distinct_ids": len(ps_ids),
    "a9_distinct_ids": len(a9_ids),
    "ids_identical_sets": ps_ids == a9_ids,
    "ids_only_in_person_summary": len(ps_ids - a9_ids),
    "ids_only_in_a9": len(a9_ids - ps_ids),
    "cross_tab_adjudication_state_x_revised_priority_bucket": {f"{s}||{b}": c for (s, b), c in cross.items()},
}

# ---------------------------------------------------------------
# B.2 canonical_employment_episodes.ndjson.gz (v5 primary)
# ---------------------------------------------------------------
path = V5 + r"\canonical_employment_episodes.ndjson.gz"
total = 0
distinct_resolved_person = set()
by_container_kind = Counter()
by_identity_status = Counter()
by_container_status = Counter()
by_episode_status = Counter()
bounded_e = start_only_e = end_only_e = neither_e = 0
start_prec_c = Counter()
end_prec_c = Counter()
min_start = max_start = min_end = max_end = None
cnt_source_as_of_nonnull = 0
has_promotion_blockers_field = False
identity_decision_ids = set()
container_decision_ids = set()
episode_id_to_identity_decision = {}
episode_id_to_container_decision = {}

for rec in stream(path):
    total += 1
    rp = rec.get("resolved_person_id")
    if rp is not None:
        distinct_resolved_person.add(rp)
    by_container_kind[rec.get("container_kind")] += 1
    by_identity_status[rec.get("identity_status")] += 1
    by_container_status[rec.get("container_status")] += 1
    by_episode_status[rec.get("episode_status")] += 1

    se = rec.get("start_earliest")
    ee = rec.get("end_earliest")
    if se is not None and ee is not None:
        bounded_e += 1
    elif se is not None:
        start_only_e += 1
    elif ee is not None:
        end_only_e += 1
    else:
        neither_e += 1

    start_prec_c[rec.get("start_precision")] += 1
    end_prec_c[rec.get("end_precision")] += 1

    if se is not None:
        if min_start is None or se < min_start:
            min_start = se
        if max_start is None or se > max_start:
            max_start = se
    if ee is not None:
        if min_end is None or ee < min_end:
            min_end = ee
        if max_end is None or ee > max_end:
            max_end = ee

    if rec.get("source_as_of") is not None:
        cnt_source_as_of_nonnull += 1
    if "promotion_blockers" in rec:
        has_promotion_blockers_field = True

    eid = rec.get("episode_id")
    idd = rec.get("identity_decision_id")
    cdd = rec.get("container_decision_id")
    if idd is not None:
        identity_decision_ids.add(idd)
        episode_id_to_identity_decision[eid] = idd
    if cdd is not None:
        container_decision_ids.add(cdd)
        episode_id_to_container_decision[eid] = cdd

# start_precision x end_precision table
start_end_precision_table = Counter()
for rec in stream(path):
    start_end_precision_table[(rec.get("start_precision"), rec.get("end_precision"))] += 1

out["B2_canonical_employment_episodes"] = {
    "field_names_used": {
        "person_id_field": "resolved_person_id (NOTE: field is resolved_person_id, not lda_source_person_id)",
        "source_lane_field": "NOT PRESENT on this file; source_lane lives on employment_promotion_decisions.ndjson.gz, joinable via episode_id",
        "current_as_of_field": "NOT PRESENT; closest analog is source_as_of",
        "promotion_blockers_field_present": has_promotion_blockers_field,
        "start_date_field": "start_earliest / start_latest",
        "end_date_field": "end_earliest / end_latest",
    },
    "total_rows": total,
    "distinct_resolved_person_id": len(distinct_resolved_person),
    "by_container_kind": dict(by_container_kind),
    "by_identity_status": dict(by_identity_status),
    "by_container_status": dict(by_container_status),
    "by_episode_status": dict(by_episode_status),
    "bounded_start_end_earliest": {"bounded": bounded_e, "start_only": start_only_e, "end_only": end_only_e, "neither": neither_e},
    "start_precision_distribution": dict(start_prec_c),
    "end_precision_distribution": dict(end_prec_c),
    "start_precision_x_end_precision": {f"{s}||{e}": c for (s, e), c in start_end_precision_table.items()},
    "min_start_earliest": min_start,
    "max_start_earliest": max_start,
    "min_end_earliest": min_end,
    "max_end_earliest": max_end,
    "rows_with_source_as_of_nonnull": cnt_source_as_of_nonnull,
    "rows_with_promotion_blockers_nonempty": "FIELD DOES NOT EXIST on canonical_employment_episodes records" if not has_promotion_blockers_field else "see field",
}

# ---------------------------------------------------------------
# B.3 employment_promotion_decisions.ndjson.gz
# ---------------------------------------------------------------
path = V5 + r"\employment_promotion_decisions.ndjson.gz"
total = 0
by_promotion_status = Counter()
by_identity_gate = Counter()
by_container_gate = Counter()
by_external_review_gate = Counter()
decision_id_prefixes = Counter()
decision_ids = set()
distinct_person_promotion = defaultdict(set)  # promotion_status -> set of person ids
episode_to_source_lane = {}
episode_to_person = {}

for rec in stream(path):
    total += 1
    ps = rec.get("promotion_status")
    by_promotion_status[ps] += 1
    by_identity_gate[rec.get("identity_gate")] += 1
    by_container_gate[rec.get("container_gate")] += 1
    by_external_review_gate[rec.get("external_review_gate")] += 1
    did = rec.get("decision_id")
    if did:
        decision_ids.add(did)
        parts = did.split(":")
        prefix = ":".join(parts[:2]) if len(parts) >= 2 else did
        decision_id_prefixes[prefix] += 1
    pid = rec.get("lda_source_person_id")
    if pid is not None:
        distinct_person_promotion[ps].add(pid)
    eid = rec.get("episode_id")
    if eid is not None:
        episode_to_source_lane[eid] = rec.get("source_lane")
        episode_to_person[eid] = pid

# matched-count check: identity_decision_id / container_decision_id from episodes vs decision_id in decisions
matched_identity = identity_decision_ids & decision_ids
matched_container = container_decision_ids & decision_ids

out["B3_employment_promotion_decisions"] = {
    "total_rows": total,
    "by_promotion_status": dict(by_promotion_status),
    "by_identity_gate": dict(by_identity_gate),
    "by_container_gate": dict(by_container_gate),
    "by_external_review_gate": dict(by_external_review_gate),
    "decision_id_namespace_prefixes": dict(decision_id_prefixes),
    "distinct_person_count_by_promotion_status": {k: len(v) for k, v in distinct_person_promotion.items()},
    "distinct_decision_ids": len(decision_ids),
    "episodes_identity_decision_ids_count": len(identity_decision_ids),
    "episodes_container_decision_ids_count": len(container_decision_ids),
    "identity_decision_id_values_matching_a_decision_id": len(matched_identity),
    "container_decision_id_values_matching_a_decision_id": len(matched_container),
}

# ---------------------------------------------------------------
# B.2 (continued) episodes-by-source_lane via join on episode_id -> decisions.source_lane
# ---------------------------------------------------------------
by_source_lane_joined = Counter()
for rec in stream(V5 + r"\canonical_employment_episodes.ndjson.gz"):
    eid = rec.get("episode_id")
    lane = episode_to_source_lane.get(eid, "__NO_MATCHING_DECISION__")
    by_source_lane_joined[lane] += 1
out["B2_canonical_employment_episodes"]["by_source_lane_via_join_on_episode_id"] = dict(by_source_lane_joined)

# ---------------------------------------------------------------
# B.4 employment_promotion_blocked.ndjson.gz
# ---------------------------------------------------------------
path = V5 + r"\employment_promotion_blocked.ndjson.gz"
total = 0
by_gate = Counter()
for rec in stream(path):
    total += 1
    by_gate[rec.get("gate")] += 1

out["B4_employment_promotion_blocked"] = {
    "field_names_used": {"blocker_reason_field": "gate", "other_field": "source_id"},
    "total_rows": total,
    "by_gate": dict(by_gate),
}

# ---------------------------------------------------------------
# B.5 cross-tabs: distinct promoted people x A9 bucket; distinct promoted people x person_summary adjudication_state
# ---------------------------------------------------------------
promoted_people = distinct_person_promotion.get("PROMOTED", set())

cross_a9 = Counter()
for pid in promoted_people:
    bucket = a9_bucket.get(pid, "__NOT_IN_A9__")
    cross_a9[bucket] += 1

cross_ps = Counter()
for pid in promoted_people:
    state = person_state.get(pid, "__NOT_IN_PERSON_SUMMARY__")
    cross_ps[state] += 1

out["B5_promoted_people_crosstabs"] = {
    "definition_used_for_promoted_people": "distinct lda_source_person_id in employment_promotion_decisions.ndjson.gz where promotion_status == 'PROMOTED'",
    "distinct_promoted_people": len(promoted_people),
    "promoted_people_x_a9_revised_priority_bucket": dict(cross_a9),
    "promoted_people_x_person_summary_adjudication_state": dict(cross_ps),
}

with open(r"C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-employment-tenure-adjudication-e27de8\b4908000-b7b6-4df6-92e9-96e07c3b29bc\scratchpad\census_v3_v5.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False, sort_keys=False)

print("DONE")
print(json.dumps({k: "OK" for k in out.keys()}, indent=2))
