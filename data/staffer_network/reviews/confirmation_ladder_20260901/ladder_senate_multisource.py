"""
Read-only measurement script: Confirmation ladder (Senate) + multi-source overlap.
Streams .ndjson.gz line by line. Writes results to ladder_senate_multisource.json
in the same scratchpad directory. Does not import fec, does not write anywhere
outside the scratchpad.
"""
import gzip
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from statistics import median

LANE_ROOT = Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network")
LOOKUP_QUEUE = Path(
    r"C:\Users\pgoff\AppData\Local\Melange\staffer_network\employment-lookup"
    r"\generation-20260831T050000Z\employment_lookup_queue.ndjson.gz"
)
OUT_PATH = Path(__file__).with_name("ladder_senate_multisource.json")


def read_ndjson_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_ndjson(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def trunc(v, n=80):
    if isinstance(v, str):
        s = v
    else:
        s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= n else s[: n - 3] + "..."


result = {}
methodology = {}

# =====================================================================
# PART A -- Senate ladder
# =====================================================================

senate_path = LANE_ROOT / "lda_senate_payroll_matches_2011_2026_v1" / "lda_senate_payroll_match_candidates.ndjson.gz"

senate_rows = list(read_ndjson_gz(senate_path))
first_record = senate_rows[0]

result["A1_row_count"] = len(senate_rows)
result["A1_distinct_people"] = len({r["lda_source_person_id"] for r in senate_rows})
result["A1_first_record_truncated"] = {k: trunc(v) for k, v in first_record.items()}
result["A1_field_identification"] = {
    "employing_office_senator": "employing_office_candidate",
    "observation_periods_semiannual": "observed_report_intervals (list of {start,end,basis}; Senate SOD semiannual reports run Oct1-Mar31 and Apr1-Sep30)",
    "title": "title_candidate",
    "name_collision_counts": "queue_candidate_count_for_name (distinct LDA queue person-IDs matching the payroll given/surname), queue_display_name_count_for_name (distinct display names among those candidates)",
    "support_row_counts": "payroll_row_support_count",
}

# ---- A2: rationale_codes distribution for v3 senate_payroll_corroborated decisions ----
decisions_path = (
    LANE_ROOT / "employment_adjudication_generation_20260901_v3_primary" / "candidate_adjudication_decisions.ndjson.gz"
)

acc_rationale = Counter()
rev_rationale = Counter()
decision_counts = Counter()
legilist_accepted_people = set()

for rec in read_ndjson_gz(decisions_path):
    lane = rec.get("lane")
    if lane == "senate_payroll_corroborated":
        decision_counts[rec["decision"]] += 1
        codes = tuple(sorted(rec.get("rationale_codes") or []))
        if rec["decision"] == "PROVISIONALLY_ACCEPTED":
            acc_rationale[codes] += 1
        elif rec["decision"] == "REVIEW_REQUIRED":
            rev_rationale[codes] += 1
    if lane == "legilist_source_binding" and rec.get("decision") == "ACCEPTED_SOURCE_BINDING":
        legilist_accepted_people.add(rec["lda_source_person_id"])

result["A2_decision_counts"] = dict(decision_counts)
result["A2_provisionally_accepted_rationale_distribution"] = [
    {"rationale_codes": list(k), "count": v} for k, v in acc_rationale.most_common()
]
result["A2_review_required_rationale_distribution"] = [
    {"rationale_codes": list(k), "count": v} for k, v in rev_rationale.most_common()
]

# ---- Load lookup queue: person -> covered_position_values, filing_years ----
lookup_by_person = {}
for rec in read_ndjson_gz(LOOKUP_QUEUE):
    pid = rec.get("lda_source_person_id")
    lookup_by_person[pid] = {
        "covered_position_values": rec.get("covered_position_values") or [],
        "filing_years": rec.get("filing_years") or [],
    }

# ---- A3/A4: per-person tiers ----

SUFFIX_RE = re.compile(r",?\s*(JR\.?|SR\.?|III|II|IV)\.?\s*$", re.IGNORECASE)
SENATOR_RE = re.compile(r"^SENATOR\s+(.+)$", re.IGNORECASE)
INTERN_RE = re.compile(r"^INTERN COMPENSATION\s*-\s*(.+)$", re.IGNORECASE)
COMMITTEE_STOPWORDS = {
    "JOINT", "SELECT", "SPECIAL", "STANDING", "SUB", "SUBCOMMITTEE",
    "COMMITTEE", "ON", "OF", "THE", "AND",
}


def office_token_senate(office):
    """Exact O-rule token extraction for a Senate payroll office string.
    1. 'SENATOR <name>' -> the surname (last whitespace token of the name,
       after stripping a trailing generational suffix JR/SR/II/III/IV).
    2. 'INTERN COMPENSATION - <name>' -> that name, treated as a surname.
    3. Any other office string containing the word COMMITTEE -> the longest
       remaining content word after removing JOINT/SELECT/SPECIAL/STANDING/
       SUB/SUBCOMMITTEE/COMMITTEE/ON/OF/THE/AND.
    4. The bare token 'APPROPRIATIONS' -> itself.
    5. Everything else (Sergeant-at-Arms lines, Reserve/Accessibility/
       Consultants/leadership-title administrative payroll buckets) -> no
       token; these are payroll administrative categories, not a person or
       a formally named committee, so no covered-position corroboration is
       attempted for them.
    """
    su = office.strip().upper()
    m = SENATOR_RE.match(su)
    if m:
        remainder = SUFFIX_RE.sub("", m.group(1)).strip()
        tokens = [t.strip(".,") for t in remainder.split() if t.strip(".,")]
        return tokens[-1] if tokens else None
    m2 = INTERN_RE.match(su)
    if m2:
        surname = m2.group(1).strip().strip(".,")
        return surname or None
    if "COMMITTEE" in su:
        words = [w for w in re.findall(r"[A-Z]+", su) if w not in COMMITTEE_STOPWORDS]
        return max(words, key=len) if words else None
    if su == "APPROPRIATIONS":
        return su
    return None


def whole_word_in(token, text_upper):
    if not token:
        return False
    return re.search(r"\b" + re.escape(token) + r"\b", text_upper) is not None


def parse_iso(d):
    if not d:
        return None
    try:
        y, m, dd = map(int, d.split("-"))
        return date(y, m, dd)
    except Exception:
        return None


def periods_contiguous(period_pairs):
    """period_pairs: sorted list of (start_date, end_date) as date objects.
    Contiguous run of semiannual periods with no gap == every period's start
    equals the prior period's end + 1 day. A single period is trivially
    contiguous (there is no adjacent gap to have)."""
    for i in range(1, len(period_pairs)):
        prev_end = period_pairs[i - 1][1]
        cur_start = period_pairs[i][0]
        if prev_end is None or cur_start is None:
            return False
        if cur_start != prev_end + timedelta(days=1):
            return False
    return True


methodology["O_rule"] = (
    "O (office-corroborated): the person's lookup-queue covered_position_values "
    "(joined, casefolded to upper) contain, as a whole word, the token extracted "
    "from at least one of the person's Senate-payroll employing_office_candidate "
    "values by office_token_senate() -- see rule docstring: SENATOR <name> yields "
    "the surname; INTERN COMPENSATION - <name> yields that name; any other office "
    "string containing COMMITTEE yields its longest non-stopword content word; the "
    "bare token APPROPRIATIONS yields itself; all other administrative payroll "
    "buckets (Sergeant-at-Arms, Reserve, Accessibility Services, Consultants, "
    "leadership-title lines, etc.) yield no token and cannot satisfy O."
)
methodology["C_rule"] = (
    "C (chronology-consistent): max(end year across all of the person's "
    "observed_report_intervals, across every office row) <= min(filing_years) + 1, "
    "using the person's filing_years from the employment-lookup queue. A person "
    "absent from the lookup queue, or with an empty filing_years list, cannot be "
    "evaluated and is scored False."
)
methodology["S_rule"] = (
    "S (split cleanliness): group the person's Senate-payroll rows by "
    "employing_office_candidate (merging across title_candidate values within the "
    "same office), take the union of that office's observed_report_intervals as "
    "(start,end) date pairs, sort them, and require every period's start date to "
    "equal the immediately preceding period's end date + 1 day (a single-period "
    "office trivially satisfies this -- there is no adjacent period to gap "
    "against). A person passes S only if EVERY office they appear under passes "
    "this contiguity check."
)
methodology["N_rule"] = (
    "N (name-unique): queue_candidate_count_for_name == 1 (i.e. no other LDA "
    "queue person shares this payroll name) on every one of the person's Senate-"
    "payroll match rows."
)

person_rows = defaultdict(list)
for r in senate_rows:
    person_rows[r["lda_source_person_id"]].append(r)

person_tier = {}
person_office_spans = defaultdict(list)  # pid -> list of (office, [ (start,end) ... ])

for pid, rows in person_rows.items():
    # N
    n_ok = all((r.get("queue_candidate_count_for_name") == 1) for r in rows)

    # group by office for S and for span reporting
    office_periods = defaultdict(set)
    for r in rows:
        office = r["employing_office_candidate"]
        for iv in r.get("observed_report_intervals") or []:
            office_periods[office].add((iv.get("start"), iv.get("end")))

    s_ok = True
    max_end_year = None
    for office, periods in office_periods.items():
        parsed = []
        ok_dates = True
        for start, end in periods:
            sd, ed = parse_iso(start), parse_iso(end)
            if sd is None or ed is None:
                ok_dates = False
            else:
                if max_end_year is None or ed.year > max_end_year:
                    max_end_year = ed.year
            parsed.append((sd, ed))
        parsed.sort(key=lambda t: (t[0] is None, t[0]))
        office_contig = ok_dates and periods_contiguous(parsed)
        if not office_contig:
            s_ok = False
        person_office_spans[pid].append((office, parsed, office_contig))

    lookup = lookup_by_person.get(pid)
    covered_text = ""
    filing_years = []
    if lookup:
        covered_text = " ".join(lookup["covered_position_values"]).upper()
        filing_years = lookup["filing_years"]

    offices = sorted(office_periods.keys())
    o_ok = False
    for office in offices:
        tok = office_token_senate(office)
        if whole_word_in(tok, covered_text):
            o_ok = True
            break

    c_ok = False
    if filing_years and max_end_year is not None:
        c_ok = max_end_year <= (min(filing_years) + 1)

    person_tier[pid] = {"N": n_ok, "O": o_ok, "C": c_ok, "S": s_ok}

# ---- A3 tallies ----
N = sum(1 for v in person_tier.values() if v["N"])
O = sum(1 for v in person_tier.values() if v["O"])
C = sum(1 for v in person_tier.values() if v["C"])
S = sum(1 for v in person_tier.values() if v["S"])
NO = sum(1 for v in person_tier.values() if v["N"] and v["O"])
NOC = sum(1 for v in person_tier.values() if v["N"] and v["O"] and v["C"])
NOCS = sum(1 for v in person_tier.values() if v["N"] and v["O"] and v["C"] and v["S"])
NONE = sum(1 for v in person_tier.values() if not (v["N"] or v["O"] or v["C"] or v["S"]))

result["A3_total_people"] = len(person_tier)
result["A3_tier_counts"] = {
    "N": N, "O": O, "C": C, "S": S,
    "N_and_O": NO, "N_and_O_and_C": NOC, "N_and_O_and_C_and_S": NOCS,
    "none_of_NOCS": NONE,
}

# ---- A4: per person-office spans for N&O&C&S people ----
qualifying = [pid for pid, v in person_tier.items() if v["N"] and v["O"] and v["C"] and v["S"]]

span_rows = []
for pid in qualifying:
    for office, parsed, contig in person_office_spans[pid]:
        parsed_valid = [p for p in parsed if p[0] is not None and p[1] is not None]
        if not parsed_valid:
            continue
        first_start = min(p[0] for p in parsed_valid)
        last_end = max(p[1] for p in parsed_valid)
        span_rows.append(
            {
                "lda_source_person_id": pid,
                "office": office,
                "first_period_start": first_start.isoformat(),
                "last_period_end": last_end.isoformat(),
                "periods_observed": len(parsed_valid),
                "span_years": round((last_end - first_start).days / 365.25, 2),
            }
        )

result["A4_person_office_span_count"] = len(span_rows)
result["A4_median_periods_observed"] = (
    median(r["periods_observed"] for r in span_rows) if span_rows else None
)
result["A4_person_office_spans"] = span_rows

# =====================================================================
# PART B -- Multi-source overlap
# =====================================================================

house1_path = (
    LANE_ROOT
    / "house_sod_pdf_lda_name_matches_2009Q3_2015Q4_20260831_generation2_personnel_only"
    / "house_sod_pdf_lda_name_match_candidates.ndjson.gz"
)
house2_path = LANE_ROOT / "lda_house_payroll_matches_2016_2026" / "lda_house_payroll_match_candidates.ndjson.gz"
politico_path = LANE_ROOT / "politico_lda_employment_candidates_20260831" / "politico_lda_employment_candidates.ndjson.gz"
profile_inv_path = (
    LANE_ROOT / "profile_evidence_inventory_20260901_v4_primary" / "profile_evidence_inventory_25340.ndjson.gz"
)

HOUSE1 = {r["lda_source_person_id"] for r in read_ndjson_gz(house1_path)}
HOUSE2 = {r["lda_source_person_id"] for r in read_ndjson_gz(house2_path)}
HOUSE = HOUSE1 | HOUSE2

SENATE = set(person_rows.keys())

LEGILIST = legilist_accepted_people

POLITICO = {r["lda_source_person_id"] for r in read_ndjson_gz(politico_path)}

profile_records = list(read_ndjson_gz(profile_inv_path))
PROFILE = {
    r["lda_source_person_id"]
    for r in profile_records
    if (r.get("source_profile_employment_assertion_count") or 0) > 0
}

cp_nonempty = {
    pid
    for pid, v in lookup_by_person.items()
    if v["covered_position_values"]
}
cp_nonblank_text = {
    pid
    for pid, v in lookup_by_person.items()
    if any((s or "").strip() for s in v["covered_position_values"])
}

result["B_set_sizes"] = {
    "HOUSE1_house_sod_pdf": len(HOUSE1),
    "HOUSE2_house_payroll": len(HOUSE2),
    "HOUSE": len(HOUSE),
    "SENATE": len(SENATE),
    "LEGILIST": len(LEGILIST),
    "POLITICO": len(POLITICO),
    "PROFILE": len(PROFILE),
    "CP_TEXT_nonempty_list": len(cp_nonempty),
    "CP_TEXT_nonblank_text": len(cp_nonblank_text),
}

# Determine which CP_TEXT figure matches expectation (report both regardless)
CP_TEXT = cp_nonempty  # nonempty list is the literal covered_position_values presence rule

result["B_pairwise"] = {
    "HOUSE_and_SENATE": len(HOUSE & SENATE),
    "HOUSE_and_LEGILIST": len(HOUSE & LEGILIST),
    "SENATE_and_LEGILIST": len(SENATE & LEGILIST),
    "HOUSE_and_POLITICO": len(HOUSE & POLITICO),
    "SENATE_and_POLITICO": len(SENATE & POLITICO),
    "HOUSE_and_PROFILE": len(HOUSE & PROFILE),
    "SENATE_and_PROFILE": len(SENATE & PROFILE),
    "HOUSEorSENATE_and_CPTEXT_nonempty_list": len((HOUSE | SENATE) & cp_nonempty),
    "HOUSEorSENATE_and_CPTEXT_nonblank_text": len((HOUSE | SENATE) & cp_nonblank_text),
    "HOUSEorSENATE_and_LEGILIST_and_CPTEXT_nonempty_list": len((HOUSE | SENATE) & LEGILIST & cp_nonempty),
    "HOUSEorSENATE_and_LEGILIST_and_CPTEXT_nonblank_text": len((HOUSE | SENATE) & LEGILIST & cp_nonblank_text),
}

sets_named = {
    "HOUSE": HOUSE,
    "SENATE": SENATE,
    "LEGILIST": LEGILIST,
    "POLITICO": POLITICO,
    "PROFILE": PROFILE,
    "CP_TEXT": CP_TEXT,
}
all_people = set()
for s in sets_named.values():
    all_people |= s

membership_count = Counter()
for pid in all_people:
    n = sum(1 for s in sets_named.values() if pid in s)
    membership_count[n] += 1

result["B_multiplicity"] = {
    "people_in_ge2_of_6_sets": sum(v for k, v in membership_count.items() if k >= 2),
    "people_in_ge3_of_6_sets": sum(v for k, v in membership_count.items() if k >= 3),
    "people_in_ge4_of_6_sets": sum(v for k, v in membership_count.items() if k >= 4),
    "distribution_by_exact_count": dict(sorted(membership_count.items())),
    "sets_considered": list(sets_named.keys()),
}

# ---- Cross-source office confirmation for HOUSE/SENATE ∩ PROFILE ----

STOPWORDS_HOUSE = {
    "COMMITTEE", "COMM", "ON", "OF", "THE", "AND", "OFFICE", "CHIEF", "ADMIN",
    "ADMINISTRATION", "OFCR", "HOUSE", "SPEAKER", "SERVICE", "SERVICES",
}
YEAR_PREFIX_RE = re.compile(r"^(19|20)\d{2}\s+")


def office_token_house(office):
    """Generalized office-token rule for House offices (mostly committee
    names, occasionally year-prefixed as in the 2009Q3-2015Q4 House SOD PDF
    matches). Strip a leading 4-digit year token if present, then take every
    remaining content word of length >= 4 that is not in STOPWORDS_HOUSE.
    Any one of those words matching whole-word in the profile employer text
    counts as a hit (unlike the stricter single-longest-word Senate committee
    rule, since House offices are almost entirely multi-word committee names
    with no single obviously dominant word)."""
    su = office.strip().upper()
    su = YEAR_PREFIX_RE.sub("", su)
    words = [w for w in re.findall(r"[A-Z]+", su) if w not in STOPWORDS_HOUSE and len(w) >= 4]
    return words


methodology["cross_source_office_confirmation_rule"] = (
    "For each person in HOUSE-or-SENATE intersected with PROFILE, build the "
    "person's payroll office-token set (Senate: office_token_senate() per "
    "office row; House: office_token_house() per office row -- all "
    "non-stopword content words length>=4, after stripping a leading "
    "4-digit-year prefix) and the person's profile-employer text (union of "
    "working_history_corpus employment_episodes[].employer, "
    "rapid_structured_profile_evidence employment[].employer, and "
    "linkedin_authenticated_evidence candidate_facts[fact_type==EMPLOYMENT]."
    "employer_raw, casefolded). A person counts as cross-source office-"
    "confirmed if any office token is found as a whole word in the employer "
    "text."
)

# person -> office token sets, from payroll rows
person_office_tokens = defaultdict(set)
for pid, rows in person_rows.items():  # Senate
    for r in rows:
        tok = office_token_senate(r["employing_office_candidate"])
        if tok:
            person_office_tokens[pid].add(tok)

for r in read_ndjson_gz(house1_path):
    pid = r["lda_source_person_id"]
    office = r.get("employing_office_raw") or ""
    for tok in office_token_house(office):
        person_office_tokens[pid].add(tok)

for r in read_ndjson_gz(house2_path):
    pid = r["lda_source_person_id"]
    office = r.get("employing_office_candidate") or ""
    for tok in office_token_house(office):
        person_office_tokens[pid].add(tok)

# person -> profile employer text (union of the three raw ledgers)
person_profile_employer_text = defaultdict(list)

working_path = LANE_ROOT / "working_history_corpus_20260831T180000Z_8workers" / "working_history_corpus.ndjson.gz"
for r in read_ndjson_gz(working_path):
    pid = r.get("lda_source_person_id")
    for ep in r.get("employment_episodes") or []:
        emp = ep.get("employer")
        if emp:
            person_profile_employer_text[pid].append(emp)

rapid_path = LANE_ROOT / "rapid_structured_profile_evidence_20260901_current" / "rapid_structured_profile_evidence.ndjson"
for r in read_ndjson(rapid_path):
    pid = r.get("lda_source_person_id")
    for ep in r.get("employment") or []:
        emp = ep.get("employer")
        if emp:
            person_profile_employer_text[pid].append(emp)

auth_path = LANE_ROOT / "linkedin_authenticated_evidence_20260901" / "linkedin_authenticated_evidence.ndjson"
for r in read_ndjson(auth_path):
    pid = r.get("lda_source_person_id")
    for fact in r.get("candidate_facts") or []:
        if fact.get("fact_type") == "EMPLOYMENT":
            emp = fact.get("employer_raw")
            if emp:
                person_profile_employer_text[pid].append(emp)


def cross_confirmed(pid):
    toks = person_office_tokens.get(pid)
    if not toks:
        return False
    employers = person_profile_employer_text.get(pid)
    if not employers:
        return False
    text = " ".join(employers).upper()
    for tok in toks:
        if whole_word_in(tok, text):
            return True
    return False


house_profile = HOUSE & PROFILE
senate_profile = SENATE & PROFILE

house_profile_confirmed = sum(1 for pid in house_profile if cross_confirmed(pid))
senate_profile_confirmed = sum(1 for pid in senate_profile if cross_confirmed(pid))
house_profile_with_employer_text = sum(1 for pid in house_profile if person_profile_employer_text.get(pid))
senate_profile_with_employer_text = sum(1 for pid in senate_profile if person_profile_employer_text.get(pid))

result["B_cross_source_office_confirmation"] = {
    "HOUSE_and_PROFILE_count": len(house_profile),
    "HOUSE_and_PROFILE_with_profile_employer_text": house_profile_with_employer_text,
    "HOUSE_and_PROFILE_office_surname_confirmed": house_profile_confirmed,
    "SENATE_and_PROFILE_count": len(senate_profile),
    "SENATE_and_PROFILE_with_profile_employer_text": senate_profile_with_employer_text,
    "SENATE_and_PROFILE_office_surname_confirmed": senate_profile_confirmed,
}

result["methodology"] = methodology

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print("WROTE", OUT_PATH)
print(json.dumps({k: v for k, v in result.items() if k not in ("A4_person_office_spans",)}, indent=2)[:6000])
