"""
Registrant-side confirmation ladder measurement (READ-ONLY).
Writes results to <scratchpad>\\ladder_registrant.json and prints report tables.
"""
import gzip, json, re, os, sys
from collections import defaultdict, Counter

BASE = "C:/Users/pgoff/OneDrive/Desktop/Melange Systems/audits/staffer_network"
APPDATA = "C:/Users/pgoff/AppData/Local/Melange/staffer_network"
SCRATCH = r"C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-employment-tenure-adjudication-e27de8\b4908000-b7b6-4df6-92e9-96e07c3b29bc\scratchpad"
OUT_PATH = os.path.join(SCRATCH, "ladder_registrant.json")

DECISIONS_PATH = f"{BASE}/employment_adjudication_generation_20260901_v3_primary/candidate_adjudication_decisions.ndjson.gz"
EPISODES_PATH = f"{BASE}/lda_registrant_employment_20260831/lda_registrant_employment_episodes.ndjson.gz"
PEOPLE_PATH = f"{BASE}/lda_registrant_employment_20260831/lda_registrant_employment_people.ndjson.gz"
LOOKUP_PATH = f"{APPDATA}/employment-lookup/generation-20260831T050000Z/employment_lookup_queue.ndjson.gz"
LD203_PATH = f"{BASE}/a7_machine_local_source_inventory_20260901_primary/a7_ld203_affiliation_candidates.ndjson.gz"
FEC_PATH = f"{BASE}/a7_machine_local_source_inventory_20260901_primary/a7_fec_employment_observation_candidates.ndjson.gz"
LITTLESIS_RECEIPT = f"{BASE}/littlesis_lda_history_candidates_20260831/littlesis_lda_history_candidate_receipt.json"
LITTLESIS_PATH = f"{BASE}/littlesis_lda_history_candidates_20260831/littlesis_lda_history_candidates.ndjson.gz"
HOUSE_SOD_PATH = f"{BASE}/house_sod_pdf_lda_name_matches_2009Q3_2015Q4_20260831_generation2_personnel_only/house_sod_pdf_lda_name_match_candidates.ndjson.gz"
HOUSE_PAYROLL_PATH = f"{BASE}/lda_house_payroll_matches_2016_2026/lda_house_payroll_match_candidates.ndjson.gz"
SENATE_PAYROLL_PATH = f"{BASE}/lda_senate_payroll_matches_2011_2026_v1/lda_senate_payroll_match_candidates.ndjson.gz"


def norm_name(s):
    """Normalization rule for name equality: casefold, strip all non-alphanumeric
    characters to single spaces, collapse whitespace."""
    if not s:
        return ""
    s = s.casefold()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def iter_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def pct(n, d):
    if not d:
        return None
    return round(100.0 * n / d, 2)


report = {}
log = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    log.append(s)


# =========================================================================
# STEP 1: LDA registrant association baseline
# =========================================================================
say("\n=== STEP 1: LDA registrant association baseline ===")

first_decision_lda_assoc = None
lane_row_count = 0
for rec in iter_gz(DECISIONS_PATH):
    if rec.get("lane") == "lda_registrant_association":
        lane_row_count += 1
        if first_decision_lda_assoc is None:
            first_decision_lda_assoc = rec

say("candidate_adjudication_decisions.ndjson.gz rows with lane == lda_registrant_association:", lane_row_count)
say("First record (decision lane, does NOT itself carry registrant id or years):")
say(json.dumps(first_decision_lda_assoc, indent=2))

first_episode = None
person_episodes = defaultdict(list)
for rec in iter_gz(EPISODES_PATH):
    if first_episode is None:
        first_episode = rec
    person_episodes[rec["lda_source_person_id"]].append(rec)

say("\nUpstream lda_registrant_employment_episodes.ndjson.gz (candidate_id of the decision row")
say("== episode_id here, verified 1:1, 25469==25469, 0 mismatches) DOES carry registrant id + years.")
say("First episode record:")
say(json.dumps(first_episode, indent=2))

# per-person registrant ids and year spans, from the episode-level source
person_registrant_ids = {}
person_year_span = {}
person_lda_names_by_year = defaultdict(lambda: defaultdict(set))  # pid -> year -> set(norm employer name)
person_lda_names_any_year = defaultdict(set)  # pid -> set(norm employer name), any year

for pid, eps in person_episodes.items():
    reg_ids = set(e["registrant_source_org_id"] for e in eps)
    person_registrant_ids[pid] = reg_ids
    years = []
    for e in eps:
        nm = norm_name(e.get("employer_name"))
        person_lda_names_any_year[pid].add(nm)
        fy = e.get("filing_years") or []
        sy, ey = e.get("start_year"), e.get("end_year")
        yrs_this_ep = set(fy)
        if sy is not None and ey is not None:
            yrs_this_ep.update(range(sy, ey + 1))
        elif sy is not None:
            yrs_this_ep.add(sy)
        elif ey is not None:
            yrs_this_ep.add(ey)
        for y in yrs_this_ep:
            person_lda_names_by_year[pid][y].add(nm)
        years.extend(fy)
        if sy is not None:
            years.append(sy)
        if ey is not None:
            years.append(ey)
    if years:
        person_year_span[pid] = (min(years), max(years))

n_people_step1 = len(person_episodes)
one_reg = sum(1 for v in person_registrant_ids.values() if len(v) == 1)
multi_reg = sum(1 for v in person_registrant_ids.values() if len(v) >= 2)
reg_count_dist = Counter(len(v) for v in person_registrant_ids.values())

span_len_dist = Counter()
for pid, (mn, mx) in person_year_span.items():
    span_len_dist[mx - mn + 1] += 1

say(f"\nPeople with an LDA registrant-association episode: {n_people_step1}")
say(f"People with exactly one distinct registrant (registrant_source_org_id): {one_reg} ({pct(one_reg, n_people_step1)}%)")
say(f"People with >=2 distinct registrants: {multi_reg} ({pct(multi_reg, n_people_step1)}%)")
say("Distinct-registrant-count distribution (registrants -> #people):")
for k in sorted(reg_count_dist):
    say(f"  {k} registrant(s): {reg_count_dist[k]} people")
say("\nFiling-year span length (max-min+1) distribution, from episode start_year/end_year/filing_years:")
for k in sorted(span_len_dist):
    say(f"  span={k} year(s): {span_len_dist[k]} people")

# also cross-check against the lookup queue's filing_years (person-level, coarser annual resolution requested by the task)
person_lookup = {}
first_lookup = None
for rec in iter_gz(LOOKUP_PATH):
    if first_lookup is None:
        first_lookup = rec
    person_lookup[rec["lda_source_person_id"]] = rec

say(f"\n(Lookup queue loaded: {len(person_lookup)} people; used as fallback/cross-check for filing_years.)")
lookup_span_len_dist = Counter()
covered_in_lookup = 0
for pid in person_episodes:
    lr = person_lookup.get(pid)
    if lr and lr.get("filing_years"):
        covered_in_lookup += 1
        fy = lr["filing_years"]
        lookup_span_len_dist[max(fy) - min(fy) + 1] += 1
say(f"People from step-1 lane also present in lookup queue with filing_years: {covered_in_lookup}/{n_people_step1}")
say("Lookup-queue-based filing-year span length distribution (cross-check, coarser/independent source):")
for k in sorted(lookup_span_len_dist):
    say(f"  span={k} year(s): {lookup_span_len_dist[k]} people")

report["step1_lda_registrant_association"] = {
    "note": (
        "The candidate_adjudication_decisions.ndjson.gz row for lane=lda_registrant_association does NOT "
        "itself carry a registrant id or filing years (verified: single uniform key-set across all 25469 rows). "
        "Its candidate_id is identical to the episode_id in the upstream "
        "lda_registrant_employment_20260831/lda_registrant_employment_episodes.ndjson.gz file (verified 1:1, "
        "25469/25469 match, 0 mismatches either direction), which DOES carry registrant_source_org_id, "
        "employer_name, start_year, end_year, and filing_years. That episode-level file is used below as "
        "'the row' registrant id/year source; the lookup queue's filing_years is reported separately as the "
        "person-level fallback/cross-check the task also asked for."
    ),
    "lane_row_count": lane_row_count,
    "first_decision_record": first_decision_lda_assoc,
    "first_episode_record": first_episode,
    "people_with_registrant_association": n_people_step1,
    "people_one_registrant": one_reg,
    "people_multi_registrant": multi_reg,
    "registrant_count_distribution": dict(sorted(reg_count_dist.items())),
    "filing_year_span_length_distribution_from_episodes": dict(sorted(span_len_dist.items())),
    "people_also_in_lookup_queue_with_filing_years": covered_in_lookup,
    "filing_year_span_length_distribution_from_lookup_queue": dict(sorted(lookup_span_len_dist.items())),
}

# =========================================================================
# STEP 2: LD-203 affiliations (A7)
# =========================================================================
say("\n=== STEP 2: LD-203 affiliation candidates (A7) ===")

first_ld203 = None
ld203_rows = 0
person_ld203_years = defaultdict(set)
person_ld203_names_any = defaultdict(set)
person_ld203_names_by_year = defaultdict(lambda: defaultdict(set))

for rec in iter_gz(LD203_PATH):
    ld203_rows += 1
    if first_ld203 is None:
        first_ld203 = rec
    pid = rec["lda_source_person_id"]
    y = rec.get("filing_year")
    nm = norm_name(rec.get("lda_registrant_name"))
    person_ld203_years[pid].add(y)
    person_ld203_names_any[pid].add(nm)
    person_ld203_names_by_year[pid][y].add(nm)

say(f"a7_ld203_affiliation_candidates.ndjson.gz rows: {ld203_rows}, distinct people: {len(person_ld203_years)}")
say("First record:")
say(json.dumps(first_ld203, indent=2))

same_year_match = 0
extend_earlier = 0
extend_later = 0
extend_either = 0
new_org_people = 0
intersection_people = 0
extension_amount_dist_earlier = Counter()
extension_amount_dist_later = Counter()

for pid, ld_years in person_ld203_years.items():
    if pid not in person_episodes:
        continue
    intersection_people += 1
    # same-year name-equal corroboration
    hit = False
    for y in ld_years:
        if y in person_lda_names_by_year.get(pid, {}):
            if person_ld203_names_by_year[pid][y] & person_lda_names_by_year[pid][y]:
                hit = True
                break
    if hit:
        same_year_match += 1

    # year extension
    lda_min, lda_max = person_year_span[pid]
    ld_min, ld_max = min(ld_years), max(ld_years)
    ext_e = lda_min - ld_min if ld_min < lda_min else 0
    ext_l = ld_max - lda_max if ld_max > lda_max else 0
    if ext_e > 0:
        extend_earlier += 1
        extension_amount_dist_earlier[ext_e] += 1
    if ext_l > 0:
        extend_later += 1
        extension_amount_dist_later[ext_l] += 1
    if ext_e > 0 or ext_l > 0:
        extend_either += 1

    # organizations never seen in LDA associations (any year)
    if person_ld203_names_any[pid] - person_lda_names_any_year[pid]:
        new_org_people += 1

say(f"\nPeople present in BOTH step-1 (LDA registrant association) and LD-203: {intersection_people}")
say(f"  of those, with >=1 SAME-YEAR name-equal corroboration: {same_year_match} ({pct(same_year_match, intersection_people)}%)")
say(f"  of those, whose LD-203 years extend the LDA span EARLIER: {extend_earlier} ({pct(extend_earlier, intersection_people)}%)")
say(f"  of those, whose LD-203 years extend the LDA span LATER: {extend_later} ({pct(extend_later, intersection_people)}%)")
say(f"  of those, extended EITHER direction: {extend_either} ({pct(extend_either, intersection_people)}%)")
say(f"  of those, with an LD-203 organization name never seen in their LDA associations (any year): {new_org_people} ({pct(new_org_people, intersection_people)}%)")
say("Earlier-extension amount (years before LDA min) distribution:")
for k in sorted(extension_amount_dist_earlier):
    say(f"  +{k}yr earlier: {extension_amount_dist_earlier[k]} people")
say("Later-extension amount (years after LDA max) distribution:")
for k in sorted(extension_amount_dist_later):
    say(f"  +{k}yr later: {extension_amount_dist_later[k]} people")

report["step2_ld203"] = {
    "rows": ld203_rows,
    "distinct_people": len(person_ld203_years),
    "first_record": first_ld203,
    "intersection_with_step1_people": intersection_people,
    "same_year_name_equal_corroboration_people": same_year_match,
    "extend_earlier_people": extend_earlier,
    "extend_later_people": extend_later,
    "extend_either_people": extend_either,
    "new_organization_people": new_org_people,
    "extension_amount_years_earlier_distribution": dict(sorted(extension_amount_dist_earlier.items())),
    "extension_amount_years_later_distribution": dict(sorted(extension_amount_dist_later.items())),
}

# =========================================================================
# STEP 3: FEC employer observations (A7)
# =========================================================================
say("\n=== STEP 3: FEC employment observation candidates (A7) ===")

first_fec = None
fec_rows = 0
person_fec = defaultdict(list)
for rec in iter_gz(FEC_PATH):
    fec_rows += 1
    if first_fec is None:
        first_fec = rec
    pid = rec["lda_source_person_id"]
    person_fec[pid].append(rec)

say(f"a7_fec_employment_observation_candidates.ndjson.gz rows: {fec_rows}, distinct people: {len(person_fec)}")
say("First record:")
say(json.dumps(first_fec, indent=2))

fec_same_year_match = 0
fec_any_year_match = 0
fec_people_in_step1 = 0
fec_rows_same_year_match = 0
fec_rows_any_year_match = 0

for pid, rows in person_fec.items():
    if pid not in person_episodes:
        continue
    fec_people_in_step1 += 1
    person_hit_same_year = False
    person_hit_any_year = False
    for r in rows:
        emp_norm = norm_name(r.get("raw_employer"))
        obs_date = r.get("observation_date") or ""
        try:
            obs_year = int(obs_date[:4])
        except ValueError:
            obs_year = None
        if emp_norm in person_lda_names_any_year.get(pid, set()):
            person_hit_any_year = True
            fec_rows_any_year_match += 1
        if obs_year is not None and emp_norm in person_lda_names_by_year.get(pid, {}).get(obs_year, set()):
            person_hit_same_year = True
            fec_rows_same_year_match += 1
    if person_hit_same_year:
        fec_same_year_match += 1
    if person_hit_any_year:
        fec_any_year_match += 1

say(f"\nFEC people also present in step-1 (LDA registrant association): {fec_people_in_step1}/{len(person_fec)}")
say(f"  of those, with >=1 row whose employer name-matches an LDA registrant of the SAME YEAR: {fec_same_year_match} ({pct(fec_same_year_match, fec_people_in_step1)}%)")
say(f"  of those, with >=1 row whose employer name-matches an LDA registrant in ANY year: {fec_any_year_match} ({pct(fec_any_year_match, fec_people_in_step1)}%)")
say(f"  row-level: {fec_rows_same_year_match}/{fec_rows} rows same-year match, {fec_rows_any_year_match}/{fec_rows} rows any-year match")
say("  (Note: every row in this A7 file already carries >=1 lda_registrant_anchors entry by construction --")
say("   the anchor_policy requires the FEC employer name to equal a registrant name AND that the person filed")
say("   >=1 LD-203 under that registrant at some point, with no year constraint. The same-year figures above")
say("   are an independent, stricter re-check against the step-1 episode-level per-year registrant record.)")

report["step3_fec"] = {
    "rows": fec_rows,
    "distinct_people": len(person_fec),
    "first_record": first_fec,
    "people_in_step1": fec_people_in_step1,
    "people_same_year_match": fec_same_year_match,
    "people_any_year_match": fec_any_year_match,
    "rows_same_year_match": fec_rows_same_year_match,
    "rows_any_year_match": fec_rows_any_year_match,
}

# =========================================================================
# STEP 4: LittleSis
# =========================================================================
say("\n=== STEP 4: LittleSis materialized employment/education candidates ===")

with open(LITTLESIS_RECEIPT, "r", encoding="utf-8") as f:
    littlesis_receipt = json.load(f)
say("Receipt (verbatim), materialize_littlesis_employment_candidates.py output at")
say(f"  {BASE}/littlesis_lda_history_candidates_20260831/littlesis_lda_history_candidate_receipt.json :")
say(json.dumps(littlesis_receipt, indent=2, sort_keys=True))

HILL_START_RE = re.compile(r"^(u\.?s\.?\s+)?(house|senate)\b")
HILL_ANY_RE = re.compile(r"house of representatives|u\.?s\.?\s*senate|united states senate|joint committee|select committee on")

def classify_ls_container(name, types):
    types = set(types or [])
    nrm = (name or "").strip().casefold()
    if "Elected Representative" in types:
        return "HILL_MEMBER_OR_PRESIDENT_PERSON"  # see caveat in report
    if "Government Body" in types:
        if HILL_START_RE.match(nrm) or HILL_ANY_RE.search(nrm):
            return "HILL_CHAMBER_OR_COMMITTEE"
        return "OTHER_GOVERNMENT_BODY"
    return "FIRM_OR_ORGANIZATION"


first_ls = None
ls_rows = 0
person_ls_rows = defaultdict(list)
for rec in iter_gz(LITTLESIS_PATH):
    ls_rows += 1
    if first_ls is None:
        first_ls = rec
    person_ls_rows[rec["lda_source_person_id"]].append(rec)

say(f"\nlittlesis_lda_history_candidates.ndjson.gz rows: {ls_rows}, distinct people: {len(person_ls_rows)}")
say("First candidate record:")
say(json.dumps(first_ls, indent=2))

dated_rows = bounded_rows = undated_rows = 0
container_class_counts = Counter()
person_ls_employer_names = defaultdict(set)  # EMPLOYMENT fact_type only
person_ls_years_hint = defaultdict(set)  # best-effort year extraction from raw_start/end_date "YYYY-.."
hill_member_rows = []  # rows classified HILL_MEMBER_OR_PRESIDENT_PERSON, for payroll cross-check

for pid, rows in person_ls_rows.items():
    for r in rows:
        sd, ed = r.get("raw_start_date"), r.get("raw_end_date")
        if sd and ed:
            bounded_rows += 1
            dated_rows += 1
        elif sd or ed:
            dated_rows += 1
        else:
            undated_rows += 1
        for dstr in (sd, ed):
            if dstr and len(dstr) >= 4 and dstr[:4].isdigit():
                person_ls_years_hint[pid].add(int(dstr[:4]))

        cls = classify_ls_container(r.get("container_display_name"), r.get("container_source_types"))
        container_class_counts[cls] += 1
        if r.get("fact_type") == "EMPLOYMENT":
            person_ls_employer_names[pid].add(norm_name(r.get("container_display_name")))
        if cls == "HILL_MEMBER_OR_PRESIDENT_PERSON" and r.get("fact_type") == "EMPLOYMENT":
            hill_member_rows.append((pid, r))

say(f"\nRow date-completeness: dated (start and/or end)={dated_rows} ({pct(dated_rows, ls_rows)}%), "
    f"bounded (both)={bounded_rows} ({pct(bounded_rows, ls_rows)}%), "
    f"undated={undated_rows} ({pct(undated_rows, ls_rows)}%)")
say("Container classification (Hill office [member/committee] vs firm/organization vs other government body):")
for k, v in container_class_counts.most_common():
    say(f"  {k}: {v} ({pct(v, ls_rows)}%)")
say("(Caveat: HILL_MEMBER_OR_PRESIDENT_PERSON = LittleSis container_source_types contains 'Elected Representative';")
say(" this bucket names a specific individual as employer -- e.g. 'Chuck Schumer' -- but LittleSis's type also")
say(" covers presidents/governors, so it is an upper bound on true Hill-member personal-office employment, not")
say(" a verified one. HILL_CHAMBER_OR_COMMITTEE = Government Body whose name matches House/Senate/committee")
say(" patterns (excludes state legislatures like 'Texas Senate', which fall into OTHER_GOVERNMENT_BODY along")
say(" with executive agencies, foreign/state government, and military academies.)")

# organization name matches an LDA registrant of the same person (EMPLOYMENT rows, any year, same normalization)
ls_org_match_people = 0
ls_people_in_step1 = 0
for pid, names in person_ls_employer_names.items():
    if pid not in person_episodes:
        continue
    ls_people_in_step1 += 1
    if names & person_lda_names_any_year.get(pid, set()):
        ls_org_match_people += 1

say(f"\nLittleSis EMPLOYMENT-row people also present in step-1 (LDA registrant association): {ls_people_in_step1}")
say(f"  of those, with an EMPLOYMENT container name matching an LDA registrant of that person (any year): "
    f"{ls_org_match_people} ({pct(ls_org_match_people, ls_people_in_step1)}%)")

# Hill-office rows agreeing with House/Senate payroll office, same person, member-surname whole-word casefolded match
def load_payroll(path, office_field, kind):
    rows = []
    for rec in iter_gz(path):
        pid = rec["lda_source_person_id"]
        office = (rec.get(office_field) or "")
        rows.append((pid, office))
    return rows

say("\nLoading House/Senate payroll match files for member-surname cross-check ...")
payroll_by_person = defaultdict(list)  # pid -> list of (office_raw, source_kind)
for pid, office in load_payroll(HOUSE_SOD_PATH, "employing_office_raw", "house_sod_2009_2015"):
    payroll_by_person[pid].append((office, "house_sod_2009q3_2015q4"))
for pid, office in load_payroll(HOUSE_PAYROLL_PATH, "employing_office_candidate", "house_payroll_2016_2026"):
    payroll_by_person[pid].append((office, "house_payroll_2016_2026"))
for pid, office in load_payroll(SENATE_PAYROLL_PATH, "employing_office_candidate", "senate_payroll_2011_2026"):
    payroll_by_person[pid].append((office, "senate_payroll_2011_2026"))
say(f"Payroll-matched people across all 3 files: {len(payroll_by_person)}")


def surname_of(display_name):
    # strip common suffixes, take last token
    toks = [t for t in re.split(r"\s+", display_name.strip()) if t]
    suffixes = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv"}
    while toks and toks[-1].strip(".").casefold() in suffixes:
        toks.pop()
    return toks[-1] if toks else ""


hill_agree_pairs = 0
hill_agree_people = set()
hill_member_people = set(pid for pid, r in hill_member_rows)
for pid, r in hill_member_rows:
    offices = payroll_by_person.get(pid)
    if not offices:
        continue
    surname = surname_of(r.get("container_display_name") or "")
    if not surname:
        continue
    pat = re.compile(r"\b" + re.escape(surname.casefold()) + r"\b")
    for office, kind in offices:
        if pat.search((office or "").casefold()):
            hill_agree_pairs += 1
            hill_agree_people.add(pid)
            break

say(f"\nHILL_MEMBER_OR_PRESIDENT_PERSON EMPLOYMENT rows: {len(hill_member_rows)}, covering {len(hill_member_people)} people")
say(f"  of those people, also present in a House/Senate payroll match file: "
    f"{sum(1 for p in hill_member_people if p in payroll_by_person)}")
say(f"  of those, with the LittleSis member surname appearing as a whole word (casefolded) in a payroll "
    f"employing-office field for the SAME person: {len(hill_agree_people)} people "
    f"({hill_agree_pairs} row-level agreements)")

report["step4_littlesis"] = {
    "receipt": littlesis_receipt,
    "rows": ls_rows,
    "distinct_people": len(person_ls_rows),
    "first_record": first_ls,
    "row_dated": dated_rows,
    "row_bounded_both": bounded_rows,
    "row_undated": undated_rows,
    "container_classification_counts": dict(container_class_counts),
    "employment_people_in_step1": ls_people_in_step1,
    "employment_org_name_match_people": ls_org_match_people,
    "hill_member_employment_rows": len(hill_member_rows),
    "hill_member_people": len(hill_member_people),
    "hill_member_people_in_payroll": sum(1 for p in hill_member_people if p in payroll_by_person),
    "hill_member_people_surname_agrees_with_payroll_office": len(hill_agree_people),
    "hill_member_row_level_agreements": hill_agree_pairs,
}

# =========================================================================
# STEP 5: Summary table
# =========================================================================
say("\n=== STEP 5: Summary across registrant-side sources ===")

# unify per-person "any-year normalized name" sets for a generic corroboration check
source_names = {
    "lda_association": person_lda_names_any_year,
    "ld203": person_ld203_names_any,
    "fec": defaultdict(set),
    "littlesis": person_ls_employer_names,
}
for pid, rows in person_fec.items():
    for r in rows:
        source_names["fec"][pid].add(norm_name(r.get("raw_employer")))


def corroborated_by_other(source_key, pid):
    mine = source_names[source_key].get(pid, set())
    if not mine:
        return False
    others = set()
    for k, d in source_names.items():
        if k == source_key:
            continue
        others |= d.get(pid, set())
    return bool(mine & others)


summary_rows = []
for key, people_dict, dated_share, bounded_share in [
    ("lda_association", person_episodes, 100.0, None),
    ("ld203", person_ld203_years, 100.0, "n/a (semi-annual filing periods, not tenure bounds)"),
    ("fec", person_fec, 100.0, "n/a (single-day point observations, not tenure bounds)"),
    ("littlesis", person_ls_rows, pct(dated_rows, ls_rows), pct(bounded_rows, ls_rows)),
]:
    people = list(people_dict.keys())
    n = len(people)
    corrob = sum(1 for pid in people if corroborated_by_other(key, pid))
    row = {
        "source": key,
        "people_covered": n,
        "dated_share_pct": dated_share,
        "bounded_share_pct": bounded_share,
        "corroborated_by_another_source_people": corrob,
        "corroborated_by_another_source_pct": pct(corrob, n),
    }
    summary_rows.append(row)
    say(f"{key:16s} people={n:6d}  dated%={str(dated_share):>6s}  bounded%={str(bounded_share):>30s}  "
        f"corroborated={corrob} ({pct(corrob, n)}%)")

# minimum-evidence revolving-door path: BOTH a Hill payroll observation AND a dated registrant-side employer
def year_from_iso(s):
    if not s:
        return None
    m = re.match(r"(\d{4})", s)
    return int(m.group(1)) if m else None


def build_payroll_span():
    span = defaultdict(lambda: [None, None])

    def upd(pid, y0, y1):
        if y0 is None and y1 is None:
            return
        cur = span[pid]
        ys = [y for y in (y0, y1) if y is not None]
        lo, hi = min(ys), max(ys)
        cur[0] = lo if cur[0] is None else min(cur[0], lo)
        cur[1] = hi if cur[1] is None else max(cur[1], hi)

    for rec in iter_gz(HOUSE_SOD_PATH):
        pid = rec["lda_source_person_id"]
        y0 = year_from_iso(rec.get("service_start_date_candidate_iso")) or year_from_iso(rec.get("period_start"))
        y1 = year_from_iso(rec.get("service_end_date_candidate_iso")) or year_from_iso(rec.get("period_end"))
        upd(pid, y0, y1)
    for rec in iter_gz(HOUSE_PAYROLL_PATH):
        pid = rec["lda_source_person_id"]
        y0 = year_from_iso(rec.get("service_start_date_candidate"))
        y1 = year_from_iso(rec.get("service_end_date_candidate"))
        upd(pid, y0, y1)
    for rec in iter_gz(SENATE_PAYROLL_PATH):
        pid = rec["lda_source_person_id"]
        intervals = rec.get("observed_report_intervals") or []
        ys = []
        for iv in intervals:
            y0 = year_from_iso(iv.get("start"))
            y1 = year_from_iso(iv.get("end"))
            if y0 is not None:
                ys.append(y0)
            if y1 is not None:
                ys.append(y1)
        if ys:
            upd(pid, min(ys), max(ys))
    return span


payroll_span = build_payroll_span()
say(f"\nPeople with a Hill payroll observation (any of the 3 payroll match files): {len(payroll_span)}")

both_count = 0
ordered = 0
overlap = 0
reversed_order = 0
undetermined = 0
for pid, (hill_lo, hill_hi) in payroll_span.items():
    if pid not in person_year_span:
        continue
    both_count += 1
    reg_lo, reg_hi = person_year_span[pid]
    if hill_lo is None or hill_hi is None:
        undetermined += 1
        continue
    if hill_hi < reg_lo:
        ordered += 1
    elif reg_hi < hill_lo:
        reversed_order += 1
    elif hill_lo <= reg_hi and reg_lo <= hill_hi:
        overlap += 1
    else:
        undetermined += 1

say(f"People with BOTH a Hill payroll observation AND a dated registrant-side (LDA association) employer: {both_count}")
say(f"  Hill span ends before registrant span starts (ORDERED, revolving-door pattern): {ordered} ({pct(ordered, both_count)}%)")
say(f"  Registrant span ends before Hill span starts (REVERSED order): {reversed_order} ({pct(reversed_order, both_count)}%)")
say(f"  Spans OVERLAP (same year(s) in both, at year resolution): {overlap} ({pct(overlap, both_count)}%)")
say(f"  UNDETERMINED (missing/unparseable year on one side): {undetermined} ({pct(undetermined, both_count)}%)")

report["step5_summary"] = {
    "per_source": summary_rows,
    "people_with_hill_payroll_observation": len(payroll_span),
    "people_with_both_hill_payroll_and_dated_registrant_employer": both_count,
    "ordered_hill_before_registrant": ordered,
    "reversed_registrant_before_hill": reversed_order,
    "overlap": overlap,
    "undetermined": undetermined,
}

report["normalization_rule"] = (
    "norm_name(s): s.casefold(); replace every run of characters that is not "
    "[a-z0-9] with a single space; strip leading/trailing space and collapse "
    "internal whitespace. Applied identically to LDA registrant employer_name, "
    "LD-203 lda_registrant_name, FEC raw_employer, and LittleSis container_display_name "
    "before any equality comparison."
)

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, default=str)

say(f"\nWrote full results to {OUT_PATH}")
