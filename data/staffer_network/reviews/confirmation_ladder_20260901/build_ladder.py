"""
Confirmation ladder for House payroll lanes H1/H2 vs LDA covered-position text,
name uniqueness, and chronology. Read-only measurement script.
Writes results to ladder_house.json in this scratchpad.
"""
import gzip
import json
import re
import unicodedata
from collections import defaultdict, Counter
from pathlib import Path

LANE_ROOT = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network"
LOOKUP = (r"C:\Users\pgoff\AppData\Local\Melange\staffer_network\employment-lookup"
          r"\generation-20260831T050000Z\employment_lookup_queue.ndjson.gz")
H1_PATH = LANE_ROOT + (r"\house_sod_pdf_lda_name_matches_2009Q3_2015Q4_20260831_generation2_personnel_only"
                       r"\house_sod_pdf_lda_name_match_candidates.ndjson.gz")
H2_PATH = LANE_ROOT + r"\lda_house_payroll_matches_2016_2026\lda_house_payroll_match_candidates.ndjson.gz"
V3_DECISIONS = (LANE_ROOT + r"\employment_adjudication_generation_20260901_v3_primary"
                r"\candidate_adjudication_decisions.ndjson.gz")
PROVISIONAL_EPISODES = (LANE_ROOT + r"\employment_adjudication_generation_20260901_v3_primary"
                         r"\provisional_employment_episodes.ndjson.gz")

OUT_PATH = str(Path(__file__).parent / "ladder_house.json")

# ---------------------------------------------------------------------------
# Shared tokenization helpers, reproduced verbatim (same regex/logic) from
# audits/staffer_network/match_lda_house_payroll.py so the N-tier "equivalent"
# computation for H1 uses the identical rule the H2 lane's own
# queue_candidate_count_for_name / queue_display_name_count_for_name fields
# were built with.
# ---------------------------------------------------------------------------
TOKEN_RE = re.compile(r"[A-Z0-9]+")
SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}


def tokens(value: str):
    normalized = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    result = TOKEN_RE.findall(normalized.upper())
    while result and result[-1] in SUFFIXES:
        result.pop()
    return tuple(result)


def queue_name(value: str):
    values = tokens(value)
    if len(values) < 2:
        return None
    return values[0], values[-1], values[1:-1]


def payroll_name(value: str):
    # House SOD / payroll names are stored SURNAME GIVEN [MIDDLE/SUFFIX]
    values = tokens(value)
    if len(values) < 2:
        return None
    surname, given = values[0], values[1]
    middle = tuple(item for item in values[2:] if item not in SUFFIXES)
    return given, surname, middle


def middle_compatible(left, right):
    if not left or not right:
        return True
    return left[0][0] == right[0][0]


def read_gzip(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


# ---------------------------------------------------------------------------
# Office-string normalization + O-tier corroboration rule
# ---------------------------------------------------------------------------
YEAR_PREFIX_RE = re.compile(r"^\s*(19|20)\d{2}\s+")
WORD_TOKEN_RE = re.compile(r"[A-Za-z0-9']+(?:-[A-Za-z0-9']+)*")


def strip_year(s):
    return YEAR_PREFIX_RE.sub("", s or "")


def normalize_office(raw):
    """Strip a leading H1 year prefix, the House SOD U+2014(em dash)+'Con.'
    (Continued) row-continuation suffix, normalize the U+2019 right single
    quotation mark to a plain apostrophe, collapse '&'->'AND', collapse
    whitespace, upper. (Verified via ord() inspection of raw bytes: the
    mangled glyph that renders as an unprintable box in this console is
    U+2019 where it substitutes for an apostrophe (e.g. VETERANS' AFFAIRS)
    and U+2014 where it separates a name from a trailing 'Con.' marker.)"""
    s = strip_year(raw or "").strip()
    s = s.replace("\u2019", "'")
    # strip trailing "<em-dash>Con." / "'Con." / " Con." row-continuation marker
    s = re.sub(r"[\u2014']?\s*Con\.?\s*$", "", s, flags=re.IGNORECASE).strip()
    s = s.replace("&", " AND ")
    s = re.sub(r"\s+", " ", s).strip()
    return s.upper()


def is_hon_office(normalized):
    return normalized.startswith("HON.") or normalized.startswith("HON ")


def extract_surname_forms(normalized):
    """From a normalized 'HON. ...' string, return candidate surname forms
    (whole word / hyphen-part variants) to search for in covered_position text."""
    rest = normalized.split(".", 1)[1] if normalized.startswith("HON.") else normalized[3:]
    raw_tokens = WORD_TOKEN_RE.findall(rest)
    # drop bare single-letter initials (e.g. "F", "A") which are not surnames
    cleaned = []
    for t in raw_tokens:
        t2 = t.strip(".").strip(",")
        if not t2:
            continue
        if t2.upper() in SUFFIXES:
            continue
        cleaned.append(t2)
    if not cleaned:
        return []
    surname = cleaned[-1]
    forms = {surname.upper()}
    if "-" in surname:
        for part in surname.split("-"):
            if len(part) > 2:
                forms.add(part.upper())
    return sorted(forms)


def office_group_key(office_raw):
    """Grouping key for (person, office) spans that is invariant to the
    inconsistent middle-initial punctuation the House SOD PDF extraction
    leaves behind (e.g. 'HON. STENY H HOYER' vs 'HON. STENY H. HOYER' across
    different quarters for the same member). HON. offices group by surname
    only; committee/leadership offices group by their normalized family
    string (already deduped by normalize_office's Con./& handling)."""
    norm = normalize_office(office_raw)
    if is_hon_office(norm):
        forms = extract_surname_forms(norm)
        # use the un-split (possibly hyphenated) surname as the canonical key
        primary = max(forms, key=len) if forms else norm
        return f"HON:{primary}"
    return norm


# Committee / leadership office family -> list of distinctive phrases (any
# one matching, case-insensitive, whole-word/phrase) counts as corroboration.
# Built from the full enumeration of non-HON. office-family strings observed
# in both lanes (102 in H1, 72 in H2) after normalize_office(). Rare/obscure
# families with no safely distinctive phrase are left unmapped (=> never
# corroborated by this rule; a conservative, honest non-match).
COMMITTEE_KEYWORDS = {
    "TRANSPORTATION-INFRASTRUCTURE": ["transportation and infrastructure"],
    "COMMITTEE ON WAYS AND MEANS": ["ways and means"],
    "COMMITTEE ON JUDICIARY": ["judiciary"],
    "HOMELAND SECURITY": ["homeland security"],
    "COMMITTEE ON APPROPRIATIONS": ["appropriations"],
    "COMMITTEE ON ENERGY AND COMMERCE": ["energy and commerce"],
    "COMMITTEE ON FINANCIAL SERVICE": ["financial services"],
    "COMMITTEE ON FINANCIAL SERVICES": ["financial services"],
    "COMMITTEE ON AGRICULTURE": ["agriculture"],
    "OFFICE OF THE MAJORITY LEADER": ["majority leader"],
    "COMMITTEE ON NATURAL RESOURCES": ["natural resources"],
    "COMMITTEE ON BUDGET": ["committee on budget", "budget committee"],
    "COMMITTEE ON FOREIGN AFFAIRS": ["foreign affairs"],
    "ARMED SERVICES COMMITTEE": ["armed services"],
    "COMM ON EDUCATION AND WORKFORCE": ["education and workforce"],
    "COMMITTEE ON EDUCATION AND WORKFORCE": ["education and workforce"],
    "COMM-EDUCATION AND WORKFORCE-MIN": ["education and workforce"],
    "COMM ON EDUCATION AND LABOR": ["education and labor"],
    "EDUCATION AND LABOR": ["education and labor"],
    "OFFICE OF THE MAJORITY WHIP": ["majority whip"],
    "OFFICE OF THE MINORITY WHIP": ["minority whip"],
    "COMMITTEE ON RULES": ["committee on rules", "rules committee"],
    "OFFICE OF THE SPEAKER": ["office of the speaker", "speaker of the house"],
    "COMM ON SCIENCE, SPACE AND TECH": ["science, space", "science and technology"],
    "COMM ON SCIENCE AND TECHNOLOGY": ["science and technology"],
    "SCIENCE AND TECHNOLOGY": ["science and technology"],
    "COMM ON SCIENCE SPACE AND TECH": ["science, space", "science and technology"],
    "COMM ON SCIENCE SPACE AND TECH MAJ": ["science, space", "science and technology"],
    "HOUSE ADMINISTRATION": ["house administration"],
    "VETERANS' AFFAIRS": ["veterans affairs", "veterans' affairs"],
    "VETERANS AFFAIRS": ["veterans affairs", "veterans' affairs"],
    "COMMITTEE ON VETERANS AFFAIRS": ["veterans affairs", "veterans' affairs"],
    "REPUBLICAN CONFERENCE": ["republican conference"],
    "DEMOCRATIC CAUCUS": ["democratic caucus"],
    "COMMITTEE ON SMALL BUSINESS": ["small business"],
    "OFFICE OF THE MINORITY LEADER": ["minority leader"],
    "OFFICE OF THE PARLIAMENTARIAN": ["parliamentarian"],
    "INTELLIGENCE": ["intelligence committee", "select committee on intelligence",
                      "permanent select committee on intelligence"],
    "COMM ON OVRSIGHT AND GOVT REFORM": ["oversight and government reform", "oversight and reform"],
    "OVERSIGHT AND GOVERNMENT REFORM": ["oversight and government reform", "oversight and reform"],
    "COMM ON OVERSIGHT AND REFORM": ["oversight and government reform", "oversight and reform"],
    "COMM-OVERSIGHT AND ACCOUNTABILITY": ["oversight and accountability"],
    "COMMITTEE ON OVERSIGHT AND ACCOUNTABILITY": ["oversight and accountability"],
    "SERGEANT AT ARMS": ["sergeant at arms"],
    "COMMITTEE ON ETHICS": ["committee on ethics"],
    "CHIEF ADMIN OFCR OF THE HOUSE": ["chief administrative officer"],
    "JOINT COMMMITTEE ON TAXATION": ["joint committee on taxation"],
    "REPUBLICAN STEERING COMMITTEE": ["republican steering committee"],
    "REPUBLICAN STUDY COMMITTEE": ["republican study committee"],
    "REPUBLICAN POLICY COMMITTEE": ["republican policy committee"],
    "OFFICE OF INSPECTOR GENERAL": ["inspector general"],
    "COMMITTEE ON BENGHAZI": ["benghazi"],
    "DEMOCRATIC STEERING AND POLICY": ["democratic steering"],
    "HOUSE CHILD CARE CENTER": ["child care center"],
    "LEGISLATIVE COUNSEL": ["legislative counsel"],
    "CLERK OF THE HOUSE": ["clerk of the house"],
    "ENERGY INDEP AND GLOBAL WARMING": ["global warming", "energy independence"],
    "ENERGY INDEPEN AND GLB WARMING": ["global warming", "energy independence"],
    "STANDARDS OF OFFICIAL CONDUCT": ["standards of official conduct"],
    "OFFICE OF THE HISTORIAN": ["office of the historian"],
    "OFFICE OF THE DEMOCRATIC WHIP": ["democratic whip"],
    "SELECT COMM ON JANUARY 6TH": ["january 6th", "select committee to investigate the january 6"],
    "SELECT COMMITTEE COMPETITION US AND CHINA": ["strategic competition", "chinese communist party"],
    "SEL COMM-COMPETITION US AND CHINA": ["strategic competition", "chinese communist party"],
    "INTERPARLIAMENTARY AFFAIRS": ["interparliamentary"],
    "SELECT COMM - CLIMATE CRISIS": ["climate crisis"],
    "SELECT COMM-CLIMATE CRISIS": ["climate crisis"],
    "SELECT COMM - MODERNIZATION": ["modernization of congress"],
    "DIVERSITY AND INCLUSION": ["diversity and inclusion"],
    "CONGRESSIONAL BLACK CAUCUS": ["congressional black caucus"],
    "ASIAN PACIFIC AMERICAN CAUCUS": ["asian pacific american"],
    "NEW DEMOCRAT COALITION": ["new democrat coalition"],
    "OFFICE OF CONGRESSIONAL ETHICS": ["office of congressional ethics"],
    "CONGRESSIONAL HISPANIC CAUCUS": ["congressional hispanic caucus"],
    "CONGRESSIONAL PROGRESSIVE CAUCUS": ["congressional progressive caucus"],
    "EQUALITY CAUCUS": ["equality caucus"],
    "CONGRESSIONAL WESTERN CAUCUS": ["congressional western caucus"],
    "DEMOCRATIC WOMENS CAUCUS": ["democratic women's caucus", "democratic womens caucus"],
    "CONGRESSIONAL LABOR CAUCUS": ["congressional labor caucus"],
}


def word_present(blob_cf, phrase_cf):
    """Whole-word/phrase containment check on a casefolded blob."""
    pattern = r"(?<![a-z0-9])" + re.escape(phrase_cf) + r"(?![a-z0-9])"
    return re.search(pattern, blob_cf) is not None


def check_office_corroboration(office_raw, covered_blob_cf):
    """Returns (corroborated: bool, method: str, family_or_surname: str)."""
    norm = normalize_office(office_raw)
    if not norm:
        return False, "EMPTY_OFFICE", ""
    if is_hon_office(norm):
        forms = extract_surname_forms(norm)
        if not forms:
            return False, "HON_NO_SURNAME_PARSED", norm
        for form in forms:
            if word_present(covered_blob_cf, form.lower()):
                return True, "MEMBER_SURNAME_MATCH", form
        return False, "MEMBER_SURNAME_NOT_FOUND", "/".join(forms)
    keywords = COMMITTEE_KEYWORDS.get(norm)
    if not keywords:
        return False, "COMMITTEE_FAMILY_UNMAPPED", norm
    for kw in keywords:
        if word_present(covered_blob_cf, kw.lower()):
            return True, "COMMITTEE_KEYWORD_MATCH", kw
    return False, "COMMITTEE_KEYWORD_NOT_FOUND", norm


# ---------------------------------------------------------------------------
# 1) Load lookup queue
# ---------------------------------------------------------------------------
print("Loading lookup queue...", flush=True)
queue_by_person = {}
queue_by_key = defaultdict(list)  # (given, surname) -> [(person_id, middle, display_name)]
n_queue = 0
for row in read_gzip(LOOKUP):
    n_queue += 1
    pid = row["lda_source_person_id"]
    cpv = row.get("covered_position_values") or []
    blob_cf = " | ".join(cpv).casefold()
    queue_by_person[pid] = {
        "display_name": row.get("display_name"),
        "filing_years": row.get("filing_years") or [],
        "covered_position_blob_cf": blob_cf,
        "covered_position_count": len(cpv),
        "government_term_hit": row.get("government_term_hit"),
        "priority": row.get("priority"),
    }
    parsed = queue_name(row.get("display_name") or "")
    if parsed:
        given, surname, middle = parsed
        queue_by_key[(given, surname)].append((pid, middle, row.get("display_name")))
print(f"  queue rows: {n_queue}")

# ---------------------------------------------------------------------------
# 2) N-tier equivalent for H1 (per H1 row): parse payroll_payee_raw same as
#    match_lda_house_payroll.py parses its payee_raw, look up queue_by_key at
#    (given, surname), filter by middle_compatible, count candidates and
#    distinct display names. This reproduces the exact construction used to
#    create H2's own queue_candidate_count_for_name / queue_display_name_count_for_name.
# ---------------------------------------------------------------------------


def h1_name_uniqueness(payee_raw):
    parsed = payroll_name(payee_raw or "")
    if not parsed:
        return None, None
    given, surname, middle = parsed
    candidates = [
        (pid, dname) for pid, qmiddle, dname in queue_by_key.get((given, surname), [])
        if middle_compatible(qmiddle, middle)
    ]
    if not candidates:
        return None, None
    cand_count = len(candidates)
    disp_count = len(set(dname for _, dname in candidates))
    return cand_count, disp_count


# ---------------------------------------------------------------------------
# 3) Stream H1, build per-person and per-(person,office) aggregates
# ---------------------------------------------------------------------------
print("Streaming H1...", flush=True)


def quarter_key(q):
    # 'YYYYQn' -> (YYYY, n)
    m = re.match(r"^(\d{4})Q(\d)$", q)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def quarters_contiguous(qkeys):
    qkeys = sorted(qkeys)
    if len(qkeys) <= 1:
        return True
    def to_ordinal(yq):
        return yq[0] * 4 + (yq[1] - 1)
    ords = [to_ordinal(q) for q in qkeys]
    return all(ords[i + 1] - ords[i] == 1 for i in range(len(ords) - 1))


class PersonAgg:
    __slots__ = ("rows", "office_rows")

    def __init__(self):
        self.rows = []  # list of dict per row: {n_ok, o_ok, office_family, end_year, title, period}
        self.office_rows = defaultdict(list)  # office_family -> list of period/enddate info


h1_person = defaultdict(PersonAgg)
h1_row_count = 0
h1_person_ids = set()

for rec in read_gzip(H1_PATH):
    h1_row_count += 1
    pid = rec["lda_source_person_id"]
    h1_person_ids.add(pid)
    qinfo = queue_by_person.get(pid)
    cand_count, disp_count = h1_name_uniqueness(rec.get("payroll_payee_raw"))
    n_ok = (cand_count == 1 and disp_count == 1) if cand_count is not None else False
    office_raw = rec.get("employing_office_raw") or ""
    office_family = normalize_office(office_raw)
    group_key = office_group_key(office_raw)
    blob_cf = qinfo["covered_position_blob_cf"] if qinfo else ""
    o_ok, o_method, o_detail = check_office_corroboration(office_raw, blob_cf) if qinfo else (False, "NO_QUEUE_ROW", "")
    end_iso = rec.get("service_end_date_candidate_iso")
    end_year = None
    if end_iso:
        m = re.match(r"^(\d{4})-", end_iso)
        if m:
            end_year = int(m.group(1))
    title = (rec.get("title_description_raw") or "").strip()
    t_ok = bool(title) and title.upper() not in {"N/A", "NA", "UNKNOWN", "-", "NONE"}
    period = rec.get("period")

    h1_person[pid].rows.append({
        "n_ok": n_ok, "n_cand_count": cand_count, "n_disp_count": disp_count,
        "o_ok": o_ok, "o_method": o_method, "o_detail": o_detail, "office_family": office_family,
        "end_year": end_year, "t_ok": t_ok, "period": period,
    })
    h1_person[pid].office_rows[group_key].append({"period": period, "end_year": end_year, "o_ok": o_ok})

print(f"  H1 rows: {h1_row_count}, people: {len(h1_person_ids)}")

# ---------------------------------------------------------------------------
# 4) Stream H2
# ---------------------------------------------------------------------------
print("Streaming H2...", flush=True)
h2_person = defaultdict(PersonAgg)
h2_row_count = 0
h2_person_ids = set()

for rec in read_gzip(H2_PATH):
    h2_row_count += 1
    pid = rec["lda_source_person_id"]
    h2_person_ids.add(pid)
    qinfo = queue_by_person.get(pid)
    cand_count = rec.get("queue_candidate_count_for_name")
    disp_count = rec.get("queue_display_name_count_for_name")
    n_ok = (cand_count == 1 and disp_count == 1)
    office_raw = rec.get("employing_office_candidate") or ""
    office_family = normalize_office(office_raw)
    group_key = office_group_key(office_raw)
    blob_cf = qinfo["covered_position_blob_cf"] if qinfo else ""
    o_ok, o_method, o_detail = check_office_corroboration(office_raw, blob_cf) if qinfo else (False, "NO_QUEUE_ROW", "")
    end_date = rec.get("service_end_date_candidate")
    end_year = None
    if end_date:
        m = re.match(r"^(\d{4})-", end_date)
        if m:
            end_year = int(m.group(1))
    title = (rec.get("title_candidate") or "").strip()
    t_ok = bool(title) and title.upper() not in {"N/A", "NA", "UNKNOWN", "-", "NONE"}
    supported_quarters = rec.get("supported_quarters") or []

    h2_person[pid].rows.append({
        "n_ok": n_ok, "n_cand_count": cand_count, "n_disp_count": disp_count,
        "o_ok": o_ok, "o_method": o_method, "o_detail": o_detail, "office_family": office_family,
        "end_year": end_year, "t_ok": t_ok, "supported_quarters": supported_quarters,
    })
    h2_person[pid].office_rows[group_key].append({
        "supported_quarters": supported_quarters, "end_year": end_year, "o_ok": o_ok,
    })

print(f"  H2 rows: {h2_row_count}, people: {len(h2_person_ids)}")

# ---------------------------------------------------------------------------
# 5) Person-level tier computation
# ---------------------------------------------------------------------------


def person_tiers(pid, agg, qinfo):
    rows = agg.rows
    n_tier = any(r["n_ok"] for r in rows)
    corroborated_offices = sorted({r["office_family"] for r in rows if r["o_ok"]})
    o_tier = len(corroborated_offices) > 0
    rows_corroborated = sum(1 for r in rows if r["o_ok"])
    rows_not_corroborated = len(rows) - rows_corroborated

    filing_years = (qinfo or {}).get("filing_years") or []
    threshold = (min(filing_years) + 1) if filing_years else None
    end_years = [r["end_year"] for r in rows if r.get("end_year") is not None]
    max_end_year = max(end_years) if end_years else None
    if threshold is None or max_end_year is None:
        c_class = "UNKNOWN"
    elif max_end_year <= threshold:
        c_class = "CONSISTENT"
    else:
        c_class = "INCONSISTENT"
    c_tier = c_class == "CONSISTENT"

    t_tier = any(r["t_ok"] for r in rows)

    return {
        "n_tier": n_tier,
        "o_tier": o_tier,
        "o_corroborated_offices": corroborated_offices,
        "o_rows_corroborated": rows_corroborated,
        "o_rows_not_corroborated": rows_not_corroborated,
        "c_class": c_class,
        "c_tier": c_tier,
        "max_end_year": max_end_year,
        "chronology_threshold": threshold,
        "t_tier": t_tier,
        "row_count": len(rows),
    }


def summarize_lane(person_dict, label):
    summary = {}
    counts = Counter()
    c_class_counts = Counter()
    combo_counts = Counter()
    for pid, agg in person_dict.items():
        qinfo = queue_by_person.get(pid)
        t = person_tiers(pid, agg, qinfo)
        summary[pid] = t
        counts["N"] += int(t["n_tier"])
        counts["O"] += int(t["o_tier"])
        counts["C"] += int(t["c_tier"])
        counts["T"] += int(t["t_tier"])
        c_class_counts[t["c_class"]] += 1
        combo = (
            ("N" if t["n_tier"] else "n")
            + ("O" if t["o_tier"] else "o")
            + ("C" if t["c_tier"] else "c")
        )
        combo_counts[combo] += 1
    total = len(person_dict)
    print(f"--- {label}: total people = {total} ---")
    for k in ("N", "O", "C", "T"):
        print(f"  {k}-tier people: {counts[k]}  ({counts[k]/total:.1%})")
    print(f"  C-class breakdown: {dict(c_class_counts)}")
    n_and_o = sum(1 for t in summary.values() if t["n_tier"] and t["o_tier"])
    n_and_o_and_c = sum(1 for t in summary.values() if t["n_tier"] and t["o_tier"] and t["c_tier"])
    n_and_c = sum(1 for t in summary.values() if t["n_tier"] and t["c_tier"])
    o_and_c = sum(1 for t in summary.values() if t["o_tier"] and t["c_tier"])
    none_tier = sum(1 for t in summary.values() if not t["n_tier"] and not t["o_tier"] and not t["c_tier"])
    print(f"  N.O: {n_and_o}   N.O.C: {n_and_o_and_c}   N.C: {n_and_c}   O.C: {o_and_c}   none: {none_tier}")
    print(f"  combo distribution (NOC letters, upper=tier held): {dict(combo_counts.most_common())}")
    print()
    return summary, {
        "total_people": total,
        "N": counts["N"], "O": counts["O"], "C": counts["C"], "T": counts["T"],
        "c_class_breakdown": dict(c_class_counts),
        "N_and_O": n_and_o, "N_and_O_and_C": n_and_o_and_c, "N_and_C": n_and_c,
        "O_and_C": o_and_c, "none": none_tier,
        "combo_distribution": dict(combo_counts),
    }


print("=" * 70)
print("PER-PERSON TIER SUMMARY")
print("=" * 70)
h1_summary, h1_stats = summarize_lane(h1_person, "H1 (house_sod_pdf_lda 2009Q3-2015Q4)")
h2_summary, h2_stats = summarize_lane(h2_person, "H2 (lda_house_payroll 2016-2026)")

# Union: merge rows by person across both lanes
print("Building union (H1 u H2 rows merged per person)...", flush=True)
union_person = defaultdict(PersonAgg)
for pid, agg in h1_person.items():
    union_person[pid].rows.extend(agg.rows)
    for fam, lst in agg.office_rows.items():
        union_person[pid].office_rows[fam].extend(lst)
for pid, agg in h2_person.items():
    union_person[pid].rows.extend(agg.rows)
    for fam, lst in agg.office_rows.items():
        union_person[pid].office_rows[fam].extend(lst)

union_summary, union_stats = summarize_lane(union_person, "UNION (H1 u H2)")

# ---------------------------------------------------------------------------
# 6) Step 4: partial tenure bounds for N.O.C people, at (person, office) level
#    Restricted to office pairs where: person is N-tier, this office is
#    O-corroborated, and THIS OFFICE PAIR's own chronology is consistent.
# ---------------------------------------------------------------------------


def person_office_spans(person_dict, lane_name, quarter_field_is_supported_quarters):
    spans = []
    for pid, agg in person_dict.items():
        qinfo = queue_by_person.get(pid)
        filing_years = (qinfo or {}).get("filing_years") or []
        threshold = (min(filing_years) + 1) if filing_years else None
        t = person_tiers(pid, agg, qinfo)
        if not t["n_tier"]:
            continue
        for office_family, rows in agg.office_rows.items():
            corroborated = any(r["o_ok"] for r in rows)
            if not corroborated:
                continue
            end_years = [r["end_year"] for r in rows if r.get("end_year") is not None]
            max_end_year = max(end_years) if end_years else None
            if threshold is None or max_end_year is None:
                continue  # unknown chronology, excluded from the guaranteed core
            if max_end_year > threshold:
                continue  # inconsistent, excluded
            # collect quarters
            qset = set()
            if quarter_field_is_supported_quarters:
                for r in rows:
                    for q in r.get("supported_quarters", []):
                        qk = quarter_key(q)
                        if qk:
                            qset.add(qk)
            else:
                for r in rows:
                    qk = quarter_key(r.get("period"))
                    if qk:
                        qset.add(qk)
            if not qset:
                continue
            qsorted = sorted(qset)
            first_q, last_q = qsorted[0], qsorted[-1]
            span_years = (last_q[0] + (last_q[1] - 1) / 4.0) - (first_q[0] + (first_q[1] - 1) / 4.0)
            spans.append({
                "lane": lane_name,
                "lda_source_person_id": pid,
                "office_family": office_family,
                "n_quarters_observed": len(qsorted),
                "first_quarter": f"{first_q[0]}Q{first_q[1]}",
                "last_quarter": f"{last_q[0]}Q{last_q[1]}",
                "contiguous": quarters_contiguous(qsorted),
                "span_years": round(span_years, 3),
            })
    return spans


h1_spans = person_office_spans(h1_person, "H1", quarter_field_is_supported_quarters=False)
h2_spans = person_office_spans(h2_person, "H2", quarter_field_is_supported_quarters=True)
all_spans = h1_spans + h2_spans


def span_stats(spans, label):
    n = len(spans)
    if n == 0:
        print(f"{label}: no spans")
        return {}
    quarters_counts = sorted(s["n_quarters_observed"] for s in spans)
    median_q = quarters_counts[n // 2] if n % 2 == 1 else (quarters_counts[n // 2 - 1] + quarters_counts[n // 2]) / 2
    contiguous_share = sum(1 for s in spans if s["contiguous"]) / n
    span_years_list = [s["span_years"] for s in spans]
    print(f"--- {label}: person-office spans = {n} ---")
    print(f"  median quarters observed: {median_q}")
    print(f"  share contiguous: {contiguous_share:.1%}")
    print(f"  span_years min/max: {min(span_years_list):.3f} / {max(span_years_list):.3f}")
    print()
    return {
        "count": n, "median_quarters_observed": median_q, "share_contiguous": contiguous_share,
        "span_years_min": min(span_years_list), "span_years_max": max(span_years_list),
    }


print("=" * 70)
print("STEP 4: N.O.C PARTIAL TENURE BOUNDS (person-office spans)")
print("=" * 70)
h1_span_stats = span_stats(h1_spans, "H1 N.O.C spans")
h2_span_stats = span_stats(h2_spans, "H2 N.O.C spans")
all_span_stats = span_stats(all_spans, "H1+H2 combined N.O.C spans")

# ---------------------------------------------------------------------------
# 7) Step 5: missed / unconsumed confirmations
# ---------------------------------------------------------------------------
print("=" * 70)
print("STEP 5: MISSED / UNCONSUMED CONFIRMATIONS")
print("=" * 70)

provisional_people = set()
for rec in read_gzip(PROVISIONAL_EPISODES):
    pid = rec.get("lda_source_person_id")
    if pid:
        provisional_people.add(pid)
print(f"Provisional episode people (v3, all lanes): {len(provisional_people)}")

h1_review_required_people = h1_person_ids - provisional_people
print(f"H1 people NOT among provisional (i.e. review-required or otherwise unconfirmed): {len(h1_review_required_people)}")

n_and_o_missed = 0
n_and_o_and_c_missed = 0
for pid in h1_review_required_people:
    t = h1_summary[pid]
    if t["n_tier"] and t["o_tier"]:
        n_and_o_missed += 1
        if t["c_tier"]:
            n_and_o_and_c_missed += 1
print(f"H1 'missed partial confirmations': N.O = {n_and_o_missed}, N.O.C = {n_and_o_and_c_missed}")
print()

h2_n_and_o = sum(1 for t in h2_summary.values() if t["n_tier"] and t["o_tier"])
h2_n_and_o_and_c = sum(1 for t in h2_summary.values() if t["n_tier"] and t["o_tier"] and t["c_tier"])
print(f"H2 'unconsumed confirmations' (never adjudicated): N.O = {h2_n_and_o}, N.O.C = {h2_n_and_o_and_c}")
print()

# ---------------------------------------------------------------------------
# 8) Write full JSON output
# ---------------------------------------------------------------------------
output = {
    "schema_id": "ladder-house-confirmation-measurement-v1",
    "sources": {
        "H1": H1_PATH, "H2": H2_PATH, "lookup_queue": LOOKUP,
        "v3_decisions": V3_DECISIONS, "provisional_episodes": PROVISIONAL_EPISODES,
    },
    "row_counts": {"H1": h1_row_count, "H2": h2_row_count, "queue": n_queue},
    "person_counts": {"H1": len(h1_person_ids), "H2": len(h2_person_ids), "union": len(union_person)},
    "lane_stats": {"H1": h1_stats, "H2": h2_stats, "union": union_stats},
    "noc_span_stats": {"H1": h1_span_stats, "H2": h2_span_stats, "combined": all_span_stats},
    "missed_confirmations": {
        "provisional_people_total": len(provisional_people),
        "h1_review_required_people": len(h1_review_required_people),
        "h1_missed_N_and_O": n_and_o_missed,
        "h1_missed_N_and_O_and_C": n_and_o_and_c_missed,
        "h2_unconsumed_N_and_O": h2_n_and_o,
        "h2_unconsumed_N_and_O_and_C": h2_n_and_o_and_c,
    },
    "noc_spans_sample": all_spans[:50],
}
Path(OUT_PATH).write_text(json.dumps(output, indent=2), encoding="utf-8")
print(f"Wrote {OUT_PATH}")
