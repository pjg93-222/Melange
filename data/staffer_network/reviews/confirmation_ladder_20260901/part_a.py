# -*- coding: utf-8 -*-
"""
PART A -- covered_position text yield measurement (read-only).
Writes results into ladder_cp_a6.json (part_a key) and prints tables.
"""
import gzip, json, re, collections, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

QUEUE_PATH = r"C:\Users\pgoff\AppData\Local\Melange\staffer_network\employment-lookup\generation-20260831T050000Z\employment_lookup_queue.ndjson.gz"
LEGIS_DIR = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\data\staffer_network\reference\congress-legislators\750c0608efb6ef1fc3257ba72c99af3771d35088"
HOUSE_SOD = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\house_sod_pdf_lda_name_matches_2009Q3_2015Q4_20260831_generation2_personnel_only\house_sod_pdf_lda_name_match_candidates.ndjson.gz"
HOUSE_LDA = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\lda_house_payroll_matches_2016_2026\lda_house_payroll_match_candidates.ndjson.gz"
SENATE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network\lda_senate_payroll_matches_2011_2026_v1\lda_senate_payroll_match_candidates.ndjson.gz"
OUT_JSON = r"C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-employment-tenure-adjudication-e27de8\b4908000-b7b6-4df6-92e9-96e07c3b29bc\scratchpad\ladder_cp_a6.json"

# ---------------------------------------------------------------------------
# Regexes (verbatim -- also echoed in the final report)
# ---------------------------------------------------------------------------
NONE_LIKE_RE = re.compile(r'^\s*(none|n/?a|no covered position(s)?\.?|not applicable)\.?\s*$', re.IGNORECASE)

CLASS_A_TITLE_RE = re.compile(
    r'\b(?:Rep\.?|Sen\.?|Senator|Representative|Congressman|Congresswoman|Cong\.|Hon\.?)\s+'
    r'([A-Z][A-Za-z\'\.-]*(?:\s+[A-Z][A-Za-z\'\.-]*){0,3})'
)
CLASS_A_OFFICE_RE = re.compile(
    r'\bOffice of(?:\s+(?:Sen\.?|Senator|Rep\.?|Representative|Congressman|Congresswoman))?\s+'
    r'([A-Z][A-Za-z\'\.-]*(?:\s+[A-Z][A-Za-z\'\.-]*){0,3})'
)

CLASS_B_RE = re.compile(r'\b(Committee on\b|Subcommittee\b|Select Committee\b|Cmte\.?\b|Subcmte\.?\b|Committee\b)', re.IGNORECASE)

CLASS_C_RE = re.compile(
    r'\b(Department|Agency|White House|Treasury|CFPB|FDIC|Federal Reserve|SEC|OCC|USAID|EPA|FTC|FCC|DOJ|HUD|USDA|FEMA|NASA|OMB)\b'
)

CLASS_D_TITLES_RE = re.compile(
    r'\b(Legislative (Assistant|Director|Correspondent|Aide|Counsel)|Chief of Staff|Deputy Chief of Staff|'
    r'Counsel|Staff Assistant|Communications Director|Press Secretary|Scheduler|Office Manager|'
    r'Policy (Advisor|Analyst|Director)|Senior (Advisor|Policy Advisor)|Professional Staff( Member)?)\b',
    re.IGNORECASE
)

SUFFIX_TOKENS = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def is_initial(tok):
    return len(tok.replace('.', '')) <= 1


def extract_surname_first(captured):
    """Given a captured name span like 'Joseph R. Biden Jr.', return (first, surname)."""
    toks = captured.strip().rstrip('.,;').split()
    cleaned = []
    for t in toks:
        tt = t.strip().rstrip('.,;')
        if tt.lower() in SUFFIX_TOKENS:
            continue
        if is_initial(tt):
            continue
        cleaned.append(tt)
    if not cleaned:
        return None, None
    surname = cleaned[-1]
    first = cleaned[0] if len(cleaned) >= 2 else None
    return first, surname


def classify_value(v):
    """Return dict of booleans for one covered_position_values string."""
    a = bool(CLASS_A_TITLE_RE.search(v) or CLASS_A_OFFICE_RE.search(v))
    b = bool(CLASS_B_RE.search(v))
    c = bool(CLASS_C_RE.search(v))
    e = bool(NONE_LIKE_RE.match(v.strip()))
    d = bool(CLASS_D_TITLES_RE.search(v)) and not (a or b or c)
    return {'a': a, 'b': b, 'c': c, 'd': d, 'e': e}


def extract_class_a_names(v):
    """Return list of (first, surname) tuples for all class-(a) matches in one string."""
    out = []
    for m in CLASS_A_TITLE_RE.finditer(v):
        f, s = extract_surname_first(m.group(1))
        if s:
            out.append((f, s))
    for m in CLASS_A_OFFICE_RE.finditer(v):
        f, s = extract_surname_first(m.group(1))
        if s:
            out.append((f, s))
    return out


# ---------------------------------------------------------------------------
# Load member roster (legislators-current + legislators-historical)
# ---------------------------------------------------------------------------
import yaml

def load_roster():
    legis = []
    for fn in ('legislators-current.yaml', 'legislators-historical.yaml'):
        with open(LEGIS_DIR + '\\' + fn, 'r', encoding='utf-8') as f:
            legis.extend(yaml.safe_load(f))
    by_surname = collections.defaultdict(list)
    for person in legis:
        bioguide = person.get('id', {}).get('bioguide')
        if not bioguide:
            continue
        last = (person.get('name', {}) or {}).get('last', '')
        first = (person.get('name', {}) or {}).get('first', '')
        terms = person.get('terms', []) or []
        years = []
        for t in terms:
            try:
                sy = int(t['start'][:4])
                ey = int(t['end'][:4])
                years.append((sy, ey))
            except Exception:
                pass
        if not years:
            continue
        min_y = min(y[0] for y in years)
        max_y = max(y[1] for y in years)
        by_surname[last.upper()].append({
            'bioguide': bioguide, 'first': first, 'last': last,
            'min_year': min_y, 'max_year': max_y,
        })
    return by_surname


# Common American-political-first-name nicknames. NOT applied to the primary step-3/4 counts --
# applied only in a clearly-labeled supplementary pass, because plain substring/startswith matching
# (e.g. 'JOSEPH'.startswith('JOE') is False) misses real people like Rep. Joe Heck (roster first
# name 'Joseph'), so a chunk of the 'surname_ambiguous' bucket is a nickname-matching artifact,
# not genuine ambiguity.
NICKNAME_MAP = {
    'bill': 'william', 'billy': 'william', 'will': 'william',
    'joe': 'joseph', 'joey': 'joseph',
    'mike': 'michael', 'mikey': 'michael',
    'bob': 'robert', 'bobby': 'robert', 'rob': 'robert', 'robbie': 'robert',
    'jim': 'james', 'jimmy': 'james',
    'tom': 'thomas', 'tommy': 'thomas',
    'dave': 'david', 'davey': 'david',
    'chuck': 'charles', 'charlie': 'charles', 'chick': 'charles',
    'ted': 'edward', 'eddie': 'edward', 'ed': 'edward',
    'rich': 'richard', 'rick': 'richard', 'ricky': 'richard', 'dick': 'richard',
    'dan': 'daniel', 'danny': 'daniel',
    'ken': 'kenneth', 'kenny': 'kenneth',
    'greg': 'gregory',
    'steve': 'steven',
    'pat': 'patrick',
    'tony': 'anthony',
    'nick': 'nicholas',
    'andy': 'andrew', 'drew': 'andrew',
    'matt': 'matthew',
    'chris': 'christopher',
    'sam': 'samuel',
    'alex': 'alexander',
    'ben': 'benjamin',
    'gene': 'eugene',
    'larry': 'lawrence',
    'jerry': 'gerald',
    'ron': 'ronald', 'ronnie': 'ronald',
    'russ': 'russell',
    'walt': 'walter',
    'nate': 'nathan',
    'liz': 'elizabeth', 'beth': 'elizabeth',
    'kathy': 'katherine', 'kate': 'katherine', 'katie': 'katherine',
    'debbie': 'deborah', 'deb': 'deborah',
    'sue': 'susan', 'suzy': 'susan',
}


def normalize_first_name(name):
    n = name.lower().strip('.')
    return NICKNAME_MAP.get(n, n)


def resolve_person(name_candidates, roster_by_surname, use_nicknames=False):
    """
    name_candidates: list of (first, surname) extracted from a person's covered_position_values.
    Candidates are first grouped BY SURNAME so that a redundant, under-specified duplicate
    mention of the same position (e.g. 'Aide to Rep. Heck' alongside 'Aide to Rep. Joe Heck'
    for the same person) does not by itself force an ambiguous verdict when a first-name-bearing
    mention of the *same surname* already disambiguates it.

    Returns (status, bioguide_info, diagnostics) where status in
    {'resolved', 'ambiguous', 'unresolved'} and diagnostics reports WHY a person was ambiguous:
      - 'surname_ambiguous': >=1 surname's own roster matches could not be narrowed to one person
      - 'multi_member_named': >=1 distinct members were each cleanly resolved (career spanned >1 office)
    """
    surnames = collections.defaultdict(set)  # SURNAME_UPPER -> set of first names seen (may include None)
    for first, surname in name_candidates:
        if not surname:
            continue
        surnames[surname.upper()].add(first)

    resolved_bioguides = {}
    surname_ambiguous = False
    any_candidates_found = False

    for surname_upper, firsts in surnames.items():
        cands = roster_by_surname.get(surname_upper, [])
        if not cands:
            continue
        any_candidates_found = True
        if len(cands) == 1:
            resolved_bioguides[cands[0]['bioguide']] = cands[0]
            continue
        # multiple roster people share this surname -- try every first-name variant seen
        # for this surname (skip None) to see if they agree on a single person
        matched_for_this_surname = {}
        had_first_name = False
        for first in firsts:
            if not first:
                continue
            had_first_name = True
            if use_nicknames:
                nf = normalize_first_name(first)
                filt = [c for c in cands if normalize_first_name(c['first']) == nf]
            else:
                filt = [c for c in cands if c['first'].upper() == first.upper() or c['first'].upper().startswith(first.upper())]
            if len(filt) == 1:
                matched_for_this_surname[filt[0]['bioguide']] = filt[0]
        if len(matched_for_this_surname) == 1:
            resolved_bioguides.update(matched_for_this_surname)
        else:
            # either no first name was ever given for this ambiguous surname, or the
            # first-name variants seen do not converge on one roster person
            surname_ambiguous = True

    if surname_ambiguous:
        return 'ambiguous', None, 'surname_ambiguous'
    if len(resolved_bioguides) == 1:
        return 'resolved', list(resolved_bioguides.values())[0], None
    elif len(resolved_bioguides) > 1:
        return 'ambiguous', None, 'multi_member_named'
    elif any_candidates_found:
        # unreachable given the branches above, kept for safety
        return 'ambiguous', None, 'surname_ambiguous'
    else:
        return 'unresolved', None, None


# ---------------------------------------------------------------------------
# Load payroll lanes indexed by lda_source_person_id
# ---------------------------------------------------------------------------
def load_payroll():
    idx = collections.defaultdict(list)  # lda_source_person_id -> list of (office_text, year_start, year_end)

    with gzip.open(HOUSE_SOD, 'rt', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            pid = rec.get('lda_source_person_id')
            office = rec.get('employing_office_raw', '') or ''
            sy = ey = None
            try:
                sy = int(rec.get('service_start_date_candidate_iso', '')[:4])
            except Exception:
                pass
            try:
                ey = int(rec.get('service_end_date_candidate_iso', '')[:4])
            except Exception:
                pass
            idx[pid].append({'office': office, 'start_year': sy, 'end_year': ey, 'lane': 'house_sod_2009q3_2015q4'})

    with gzip.open(HOUSE_LDA, 'rt', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            pid = rec.get('lda_source_person_id')
            office = rec.get('employing_office_candidate', '') or ''
            sy = ey = None
            try:
                sy = int(rec.get('service_start_date_candidate', '')[:4])
            except Exception:
                pass
            try:
                ey = int(rec.get('service_end_date_candidate', '')[:4])
            except Exception:
                pass
            idx[pid].append({'office': office, 'start_year': sy, 'end_year': ey, 'lane': 'house_lda_2016_2026'})

    with gzip.open(SENATE, 'rt', encoding='utf-8') as f:
        for line in f:
            rec = json.loads(line)
            pid = rec.get('lda_source_person_id')
            office = rec.get('employing_office_candidate', '') or ''
            intervals = rec.get('observed_report_intervals', []) or []
            for iv in intervals:
                sy = ey = None
                try:
                    sy = int((iv.get('start') or '')[:4])
                except Exception:
                    pass
                try:
                    ey = int((iv.get('end') or '')[:4])
                except Exception:
                    pass
                idx[pid].append({'office': office, 'start_year': sy, 'end_year': ey, 'lane': 'senate_2011_2026'})
            if not intervals:
                idx[pid].append({'office': office, 'start_year': None, 'end_year': None, 'lane': 'senate_2011_2026'})

    return idx


def surname_in_office_wholeword(surname, office_text):
    if not surname or not office_text:
        return False
    pat = r'\b' + re.escape(surname.upper()) + r'\b'
    return re.search(pat, office_text.upper()) is not None


def main():
    roster_by_surname = load_roster()
    print("Roster: distinct surnames indexed:", len(roster_by_surname))
    total_legis_entries = sum(len(v) for v in roster_by_surname.values())
    print("Roster: total legislator-entries indexed (current+historical):", total_legis_entries)

    payroll_idx = load_payroll()
    print("Payroll: distinct lda_source_person_id keys indexed:", len(payroll_idx))

    # ---- Step 1: 15 diverse examples ----
    examples = []
    n_seen_substantive = 0
    substantive_all = []  # collect (display_name, values) for stratified sampling

    class_counts = collections.Counter()
    n_total = 0
    n_with_values = 0
    n_substantive = 0

    # per-person data needed for steps 3/4/5
    class_a_people = []  # list of dicts

    with gzip.open(QUEUE_PATH, 'rt', encoding='utf-8') as f:
        for line in f:
            n_total += 1
            rec = json.loads(line)
            vals = rec.get('covered_position_values') or []
            if not vals:
                continue
            n_with_values += 1
            subst_vals = [v for v in vals if not NONE_LIKE_RE.match(v.strip())]
            if subst_vals:
                n_substantive += 1
                substantive_all.append((rec['display_name'], vals))

            per_value_flags = [classify_value(v) for v in vals]
            person_flags = {
                'a': any(pf['a'] for pf in per_value_flags),
                'b': any(pf['b'] for pf in per_value_flags),
                'c': any(pf['c'] for pf in per_value_flags),
                'd': any(pf['d'] for pf in per_value_flags),
                'e': any(pf['e'] for pf in per_value_flags),
            }
            for k, v_ in person_flags.items():
                if v_:
                    class_counts[k] += 1

            if person_flags['a']:
                name_candidates = []
                for v in vals:
                    name_candidates.extend(extract_class_a_names(v))
                status, info, ambig_reason = resolve_person(name_candidates, roster_by_surname)
                year_tokens = rec.get('covered_position_year_tokens') or []
                class_a_people.append({
                    'lda_source_person_id': rec.get('lda_source_person_id'),
                    'display_name': rec.get('display_name'),
                    'values': vals,
                    'name_candidates': name_candidates,
                    'resolve_status': status,
                    'ambiguous_reason': ambig_reason,
                    'resolved_bioguide': info['bioguide'] if info else None,
                    'resolved_min_year': info['min_year'] if info else None,
                    'resolved_max_year': info['max_year'] if info else None,
                    'year_tokens': year_tokens,
                })

    # stratified 15 diverse examples from substantive_all
    step = max(1, len(substantive_all) // 15)
    for i in range(0, len(substantive_all), step):
        if len(examples) >= 15:
            break
        name, vals = substantive_all[i]
        examples.append({'display_name': name, 'covered_position_values_truncated': [v[:120] for v in vals]})

    print("\n=== STEP 1: 15 diverse covered_position_values examples ===")
    for ex in examples:
        print(ex['display_name'], '->', ex['covered_position_values_truncated'])

    print("\n=== STEP 2: person counts per class (person can be in several) ===")
    print("n_total_records:", n_total)
    print("n_people_with_covered_position_values (respondents):", n_with_values)
    print("n_people_substantive (>=1 non-none-like value):", n_substantive)
    for k in ['a', 'b', 'c', 'd', 'e']:
        print(f"class ({k}): {class_counts[k]} people")

    print("\n=== STEP 3: class (a) surname resolution against roster ===")
    resolve_counter = collections.Counter(p['resolve_status'] for p in class_a_people)
    print("class (a) total people:", len(class_a_people))
    for k in ['resolved', 'ambiguous', 'unresolved']:
        print(f"  {k}: {resolve_counter[k]}")
    ambig_reason_counter = collections.Counter(
        p['ambiguous_reason'] for p in class_a_people if p['resolve_status'] == 'ambiguous'
    )
    print("  -- ambiguous breakdown --")
    print("     surname_ambiguous (roster surname collision, first name did not disambiguate):",
          ambig_reason_counter['surname_ambiguous'])
    print("     multi_member_named (>=2 DIFFERENT members each cleanly resolved, e.g. multi-office career):",
          ambig_reason_counter['multi_member_named'])

    print("\n=== STEP 3 SUPPLEMENT: nickname-normalized resolution pass (NOT part of the headline count) ===")
    print("Plain first-name matching is exact-or-startswith, which misses common nicknames")
    print("(e.g. 'JOSEPH'.startswith('JOE') is False, so Rep. Joe Heck / roster 'Joseph Heck' fails to")
    print("disambiguate against Rep. Denny Heck and gets bucketed as surname_ambiguous).")
    print("Re-running step 3 with a documented NICKNAME_MAP (see script) instead of startswith:")
    nick_status_for = {}
    for p in class_a_people:
        status2, info2, reason2 = resolve_person(p['name_candidates'], roster_by_surname, use_nicknames=True)
        nick_status_for[id(p)] = (status2, info2, reason2)
    resolve_counter_nick = collections.Counter(v[0] for v in nick_status_for.values())
    for k in ['resolved', 'ambiguous', 'unresolved']:
        print(f"  {k}: {resolve_counter_nick[k]}  (was {resolve_counter[k]})")
    newly_resolved = sum(
        1 for p in class_a_people
        if p['resolve_status'] != 'resolved' and nick_status_for[id(p)][0] == 'resolved'
    )
    print("  people who move INTO 'resolved' once nicknames are normalized:", newly_resolved)

    print("\n=== STEP 4: year-token consistency (class a, resolved, with year tokens) ===")
    consistent = inconsistent = unknown = 0
    people_with_year_tokens_resolved = 0
    for p in class_a_people:
        if p['resolve_status'] != 'resolved':
            continue
        if not p['year_tokens']:
            continue
        people_with_year_tokens_resolved += 1
        min_y, max_y = p['resolved_min_year'], p['resolved_max_year']
        if min_y is None or max_y is None:
            unknown += 1
            continue
        try:
            toks = [int(t) for t in p['year_tokens']]
        except Exception:
            unknown += 1
            continue
        if all(min_y <= t <= max_y for t in toks):
            consistent += 1
        else:
            inconsistent += 1
    print("class (a) resolved people with >=1 year token:", people_with_year_tokens_resolved)
    print("  consistent (all tokens within roster service years):", consistent)
    print("  inconsistent (>=1 token outside roster service years):", inconsistent)
    print("  roster years unknown:", unknown)

    print("\n=== STEP 5: payroll cross-check for class (a) people ===")
    n_class_a_in_payroll = 0
    n_office_surname_match = 0
    n_office_surname_match_and_year_consistent = 0
    examples_step5 = []
    for p in class_a_people:
        pid = p['lda_source_person_id']
        rows = payroll_idx.get(pid, [])
        if not rows:
            continue
        n_class_a_in_payroll += 1
        # gather all surnames extracted for this person
        surnames = set(s for (f, s) in p['name_candidates'] if s)
        matched_rows = []
        for row in rows:
            for sn in surnames:
                if surname_in_office_wholeword(sn, row['office']):
                    matched_rows.append(row)
                    break
        if matched_rows:
            n_office_surname_match += 1
            # check year token consistency against matched rows' observed years
            year_consistent = False
            toks = []
            try:
                toks = [int(t) for t in (p['year_tokens'] or [])]
            except Exception:
                toks = []
            if toks:
                for row in matched_rows:
                    sy, ey = row['start_year'], row['end_year']
                    if sy is not None and ey is not None:
                        if any(sy <= t <= ey for t in toks):
                            year_consistent = True
                            break
            if year_consistent:
                n_office_surname_match_and_year_consistent += 1
            if len(examples_step5) < 10:
                examples_step5.append({
                    'display_name': p['display_name'],
                    'surnames_extracted': list(surnames),
                    'matched_rows': matched_rows[:3],
                    'year_tokens': p['year_tokens'],
                })

    print("class (a) people also present in payroll lanes (by lda_source_person_id):", n_class_a_in_payroll)
    print("  of those, payroll office surname matches text-named surname (whole word, casefolded):", n_office_surname_match)
    print("  of those, ALSO has a year token inside the matching payroll row's observed years:", n_office_surname_match_and_year_consistent)

    result = {
        'part_a': {
            'n_total_records': n_total,
            'n_with_values': n_with_values,
            'n_substantive': n_substantive,
            'step1_examples': examples,
            'step2_class_counts': dict(class_counts),
            'step3_resolve_counts': dict(resolve_counter),
            'step3_ambiguous_breakdown': dict(ambig_reason_counter),
            'step3_nickname_supplement': {
                'resolve_counts': dict(resolve_counter_nick),
                'newly_resolved_via_nicknames': newly_resolved,
            },
            'step4': {
                'resolved_with_year_tokens': people_with_year_tokens_resolved,
                'consistent': consistent,
                'inconsistent': inconsistent,
                'unknown': unknown,
            },
            'step5': {
                'class_a_in_payroll': n_class_a_in_payroll,
                'office_surname_match': n_office_surname_match,
                'office_surname_match_and_year_consistent': n_office_surname_match_and_year_consistent,
                'examples': examples_step5,
            },
        }
    }
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=str)
    print("\nWrote:", OUT_JSON)


if __name__ == '__main__':
    main()
