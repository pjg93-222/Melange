import gzip
import json
from collections import Counter, defaultdict

LANE_ROOT = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network"

V3_EPISODES = LANE_ROOT + r"\employment_adjudication_generation_20260901_v3_primary\provisional_employment_episodes.ndjson.gz"
V3_PERSON_SUMMARY = LANE_ROOT + r"\employment_adjudication_generation_20260901_v3_primary\employment_adjudication_person_summary_25340.ndjson.gz"
V5_EPISODES = LANE_ROOT + r"\employment_promotion_generation_20260901_v5_primary\canonical_employment_episodes.ndjson.gz"
V5_DECISIONS = LANE_ROOT + r"\employment_promotion_generation_20260901_v5_primary\employment_promotion_decisions.ndjson.gz"
LDA_SENATE_MATCHES = LANE_ROOT + r"\lda_senate_payroll_matches_2011_2026_v1\lda_senate_payroll_match_candidates.ndjson.gz"

result = {}


def stream_ndjson_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


# ---------------------------------------------------------------------------
# Step 1: V3 = distinct lda_source_person_id in v3 provisional_employment_episodes
# ---------------------------------------------------------------------------
v3_people = set()
v3_episode_count = 0
for obj in stream_ndjson_gz(V3_EPISODES):
    v3_episode_count += 1
    v3_people.add(obj["lda_source_person_id"])

result["step1_v3_provisional_episode_rows"] = v3_episode_count
result["step1_V3_distinct_people"] = len(v3_people)

# ---------------------------------------------------------------------------
# Step 2: V5 = distinct resolved_person_id in v5 canonical_employment_episodes
#         + cross-check resolved_person_id == lda_source_person_id via decisions
#         joined on episode_id
# ---------------------------------------------------------------------------
v5_people = set()
v5_episode_count = 0
episode_to_resolved_person = {}
for obj in stream_ndjson_gz(V5_EPISODES):
    v5_episode_count += 1
    v5_people.add(obj["resolved_person_id"])
    episode_to_resolved_person[obj["episode_id"]] = obj["resolved_person_id"]

result["step2_v5_canonical_episode_rows"] = v5_episode_count
result["step2_V5_distinct_people"] = len(v5_people)

# decisions: episode_id -> lda_source_person_id, source_lane
# NOTE: the decisions file is NOT guaranteed unique on episode_id (see diagnostic
# below) -- last-row-wins is used for the per-episode lookup, matching what a
# naive dict-join would do, and its effect on downstream counts is measured
# explicitly rather than silently absorbed.
episode_to_decision_person = {}
episode_to_source_lane = {}
decisions_row_count = 0
decisions_promoted_count = 0
episode_decision_rows = defaultdict(list)
for obj in stream_ndjson_gz(V5_DECISIONS):
    decisions_row_count += 1
    if obj.get("promotion_status") == "PROMOTED":
        decisions_promoted_count += 1
    episode_to_decision_person[obj["episode_id"]] = obj["lda_source_person_id"]
    episode_to_source_lane[obj["episode_id"]] = obj["source_lane"]
    episode_decision_rows[obj["episode_id"]].append(obj)

result["step2_decisions_row_count"] = decisions_row_count
result["step2_decisions_promoted_count"] = decisions_promoted_count

# Diagnostic: is the decisions file unique on episode_id?
dup_episode_ids = {ep: rows for ep, rows in episode_decision_rows.items() if len(rows) > 1}
dup_group_sizes = Counter(len(rows) for rows in dup_episode_ids.values())
dup_lane_differs = 0
for ep, rows in dup_episode_ids.items():
    lanes = {r["source_lane"] for r in rows}
    if len(lanes) > 1:
        dup_lane_differs += 1

result["diagnostic_decisions_distinct_episode_ids"] = len(episode_decision_rows)
result["diagnostic_decisions_duplicate_episode_id_count"] = len(dup_episode_ids)
result["diagnostic_decisions_duplicate_group_size_distribution"] = {
    str(k): v for k, v in dup_group_sizes.items()
}
result["diagnostic_decisions_duplicate_groups_with_differing_source_lane"] = dup_lane_differs

mismatch_count = 0
episodes_missing_decision = 0
for ep_id, resolved_person in episode_to_resolved_person.items():
    dec_person = episode_to_decision_person.get(ep_id)
    if dec_person is None:
        episodes_missing_decision += 1
        continue
    if dec_person != resolved_person:
        mismatch_count += 1

result["step2_resolved_vs_decision_person_mismatch_count"] = mismatch_count
result["step2_episodes_missing_matching_decision_row"] = episodes_missing_decision

# ---------------------------------------------------------------------------
# Step 3: set differences
# ---------------------------------------------------------------------------
v5_minus_v3 = v5_people - v3_people
v5_intersect_v3 = v5_people & v3_people
v3_minus_v5 = v3_people - v5_people

result["step3_V5_minus_V3_count"] = len(v5_minus_v3)
result["step3_V5_intersect_V3_count"] = len(v5_intersect_v3)
result["step3_V3_minus_V5_count"] = len(v3_minus_v5)

# Diagnostic continued: which population do the duplicate-episode_id decision
# rows fall into? (affects whether last-row-wins lane lookup taints step4 vs step5)
dup_in_v5_minus_v3 = 0
dup_in_v5_intersect_v3 = 0
for ep in dup_episode_ids:
    person = episode_to_resolved_person.get(ep)
    if person in v5_minus_v3:
        dup_in_v5_minus_v3 += 1
    elif person in v5_intersect_v3:
        dup_in_v5_intersect_v3 += 1

result["diagnostic_duplicate_episode_ids_in_V5_minus_V3"] = dup_in_v5_minus_v3
result["diagnostic_duplicate_episode_ids_in_V5_intersect_V3"] = dup_in_v5_intersect_v3

# ---------------------------------------------------------------------------
# Step 4: for V5-V3 people, lane distribution over ALL their episodes
# ---------------------------------------------------------------------------
def lane_distribution(person_set):
    episodes_per_lane = Counter()
    people_lanes = defaultdict(set)  # person_id -> set of lanes seen
    episodes_missing_lane = 0
    for ep_id, resolved_person in episode_to_resolved_person.items():
        if resolved_person not in person_set:
            continue
        lane = episode_to_source_lane.get(ep_id)
        if lane is None:
            episodes_missing_lane += 1
            continue
        episodes_per_lane[lane] += 1
        people_lanes[resolved_person].add(lane)

    people_per_lane = Counter()
    for person, lanes in people_lanes.items():
        for lane in lanes:
            people_per_lane[lane] += 1

    # mix combinations: exact set of lanes touched, per person
    mix_combo_counts = Counter()
    for person, lanes in people_lanes.items():
        combo = tuple(sorted(lanes))
        mix_combo_counts[combo] += 1

    # convenience buckets requested: ALL senate_payroll_split, ALL authenticated_profile, or mix
    all_senate_payroll_split = 0
    all_authenticated_profile = 0
    mixed = 0
    other_single_lane = Counter()
    for person, lanes in people_lanes.items():
        if lanes == {"senate_payroll_split"}:
            all_senate_payroll_split += 1
        elif lanes == {"authenticated_profile"}:
            all_authenticated_profile += 1
        elif len(lanes) == 1:
            other_single_lane[next(iter(lanes))] += 1
        else:
            mixed += 1

    return {
        "people_total": len(people_lanes),
        "episodes_per_lane": dict(episodes_per_lane),
        "people_per_lane": dict(people_per_lane),
        "episodes_missing_lane_lookup": episodes_missing_lane,
        "mix_combo_counts": {",".join(k) if k else "(none)": v for k, v in mix_combo_counts.items()},
        "people_all_senate_payroll_split": all_senate_payroll_split,
        "people_all_authenticated_profile": all_authenticated_profile,
        "people_other_single_lane": dict(other_single_lane),
        "people_mixed_lanes": mixed,
    }

result["step4_V5_minus_V3_lane_distribution"] = lane_distribution(v5_minus_v3)

# ---------------------------------------------------------------------------
# Step 5: same lane distribution for V5 ∩ V3 people (contrast)
# ---------------------------------------------------------------------------
result["step5_V5_intersect_V3_lane_distribution"] = lane_distribution(v5_intersect_v3)

# ---------------------------------------------------------------------------
# Step 6: cross-check against v3 person summary (third method)
# ---------------------------------------------------------------------------
person_summary_by_id = {}
for obj in stream_ndjson_gz(V3_PERSON_SUMMARY):
    person_summary_by_id[obj["lda_source_person_id"]] = obj

result["step6_person_summary_total_rows"] = len(person_summary_by_id)

v5_minus_v3_in_summary = 0
v5_minus_v3_missing_from_summary = 0
adjudication_state_counts = Counter()
provisional_episode_count_dist = Counter()
for person in v5_minus_v3:
    row = person_summary_by_id.get(person)
    if row is None:
        v5_minus_v3_missing_from_summary += 1
        continue
    v5_minus_v3_in_summary += 1
    adjudication_state_counts[row["adjudication_state"]] += 1
    provisional_episode_count_dist[row["provisional_episode_count"]] += 1

result["step6_V5_minus_V3_found_in_person_summary"] = v5_minus_v3_in_summary
result["step6_V5_minus_V3_missing_from_person_summary"] = v5_minus_v3_missing_from_summary
result["step6_V5_minus_V3_adjudication_state_counts"] = dict(adjudication_state_counts)
result["step6_V5_minus_V3_provisional_episode_count_distribution"] = {
    str(k): v for k, v in provisional_episode_count_dist.items()
}

# ---------------------------------------------------------------------------
# Step 7: lda_senate_payroll_match_candidates distinct people + intersections
# ---------------------------------------------------------------------------
lda_senate_people = set()
lda_senate_row_count = 0
for obj in stream_ndjson_gz(LDA_SENATE_MATCHES):
    lda_senate_row_count += 1
    lda_senate_people.add(obj["lda_source_person_id"])

result["step7_lda_senate_payroll_match_rows"] = lda_senate_row_count
result["step7_lda_senate_payroll_match_distinct_people"] = len(lda_senate_people)
result["step7_intersect_with_V5_minus_V3"] = len(lda_senate_people & v5_minus_v3)
result["step7_intersect_with_V5_overall"] = len(lda_senate_people & v5_people)

# ---------------------------------------------------------------------------
# Summary line vs the claim under test
# ---------------------------------------------------------------------------
result["CLAIM_UNDER_TEST"] = (
    "1,486 of the 2,672 people promoted in v5 had zero v3 provisional episodes, "
    "and they enter v5 solely through the senate_payroll_split lane."
)
result["CLAIM_CHECK_V5_total_expected_2672_actual"] = len(v5_people)
result["CLAIM_CHECK_V5_minus_V3_expected_1486_actual"] = len(v5_minus_v3)
result["CLAIM_CHECK_V5_intersect_V3_expected_1186_actual"] = len(v5_intersect_v3)
result["CLAIM_CHECK_V3_minus_V5_expected_0_actual"] = len(v3_minus_v5)
result["CLAIM_CHECK_lda_senate_matches_distinct_people_expected_2798_actual"] = len(lda_senate_people)
result["CLAIM_CHECK_all_V5_minus_V3_solely_senate_payroll_split"] = (
    result["step4_V5_minus_V3_lane_distribution"]["people_all_senate_payroll_split"]
    == result["step4_V5_minus_V3_lane_distribution"]["people_total"]
    and result["step4_V5_minus_V3_lane_distribution"]["people_mixed_lanes"] == 0
    and len(result["step4_V5_minus_V3_lane_distribution"]["people_per_lane"]) == 1
)

out_path = r"C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-employment-tenure-adjudication-e27de8\b4908000-b7b6-4df6-92e9-96e07c3b29bc\scratchpad\verify_1486.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, sort_keys=False)

print(json.dumps(result, indent=2, sort_keys=False))
