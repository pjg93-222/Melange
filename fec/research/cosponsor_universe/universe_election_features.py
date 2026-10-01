"""Retrospective pre-Congress election context; no current scores or 119 outcomes.

Only writes election_history.csv and election_history.receipt.json to the new
research output. Source versions were observed later: this is explicitly not
an archived observation-time replay. Candidate identity is never inferred from
party. Unknowns remain blank, with reasons and a numeric missing indicator.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata
import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs/cosponsor_universe_20260905"
REF = ROOT / "data/staffer_network/reference/congress-legislators/750c0608efb6ef1fc3257ba72c99af3771d35088"
CUTOFFS = {117: dt.date(2021, 1, 3), 118: dt.date(2023, 1, 3)}
FEATURES = [
    "election_share", "election_margin", "election_log_total_votes",
    "election_uncontested", "election_years_ago", "election_missing",
    "prior_service_years", "prior_service_missing",
]
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
NONVOTE = re.compile(r"overvote|undervote|exhausted|^blank$|^void$")


def valid_candidate_counts(race):
    return {name: votes for name, votes in race["candidates"].items()
            if not NONVOTE.search(name)}


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def norm(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z]+", text.lower()))


def candidate_tokens(text):
    # Comma-format ballots are LAST, FIRST; suffix-only commas are different.
    bits = str(text).split(",")
    if len(bits) > 1 and any(t not in SUFFIXES for t in norm(bits[1]).split()):
        text = " ".join(bits[1:] + bits[:1])
    return [t for t in norm(text).split() if t not in SUFFIXES]


def name_matches(text, person):
    tokens = candidate_tokens(text)
    for names in [person["name"]] + person.get("other_names", []):
        # Explicit complete official names allow recorded initialisms such as
        # G.K. Butterfield and J.D. Vance; partial initials still fail below.
        if names.get("official_full") and tokens == candidate_tokens(names["official_full"]):
            return True
        last = norm(names.get("last", person["name"]["last"])).split()
        if not last or tokens[-len(last):] != last:
            continue
        given = tokens[:-len(last)]
        # Full given name or a source-recorded nickname, never an initial alone.
        aliases = set()
        for key in ("first", "nickname"):
            aliases.update(t for t in norm(names.get(key)).split() if len(t) > 1)
        for alias in person.get("_given_aliases", []):
            aliases.update(t for t in norm(alias).split() if len(t) > 1)
        if aliases.intersection(given):
            return True
    return False


def date(value):
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(value)


def district(value):
    value = str("" if value is None else value).strip().lower()
    if value in {"statewide", "at-large", "at large"}:
        return "0"
    try:
        return str(int(float(value)))
    except ValueError:
        return value


def boolval(value):
    return str(value).strip().lower() in {"true", "1", "yes"}


def prior_service(person, cutoff):
    intervals = sorted(
        (date(t["start"]), min(date(t["end"]), cutoff))
        for t in person.get("terms", [])
        if date(t["start"]) < cutoff and t.get("type") in {"rep", "sen"}
    )
    merged = []
    for start, end in intervals:
        if start >= end:
            continue
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return sum((end - start).days for start, end in merged) / 365.25


def relevant_term(person, chamber, state, year, cd):
    # Only a term beginning in the election year or following year can establish
    # the candidate's election/office identity. This prevents reusing a former
    # House race for a senator and disambiguates relatives with similar names.
    kind = {"House": "rep", "Senate": "sen"}[chamber]
    return any(
        t.get("type") == kind and t.get("state") == state
        and year <= date(t["start"]).year <= year + 1
        and (chamber == "Senate" or district(t.get("district")) == cd)
        for t in person.get("terms", [])
    )


def aggregate_race(rows, chamber):
    totals = set()
    candidates = collections.defaultdict(float)
    parties = collections.defaultdict(set)
    originals = collections.defaultdict(set)
    reasons = set()
    for row in rows:
        if boolval(row.get("unofficial")):
            reasons.add("unofficial_source_race")
        try:
            votes, total = float(row["candidatevotes"]), float(row["totalvotes"])
            if not math.isfinite(votes + total) or votes < 0 or total <= 0 or votes > total:
                raise ValueError
        except (ValueError, TypeError):
            reasons.add("invalid_numeric_race")
            continue
        totals.add(total)
        key = " ".join(candidate_tokens(row["candidate"]))
        candidates[key] += votes  # Fusion-ticket votes are summed by candidate.
        originals[key].add(row["candidate"])
        parties[key].add(row.get("party_simplified", row.get("party", "")))
    if len(totals) != 1:
        reasons.add("inconsistent_race_total")
    total = next(iter(totals)) if len(totals) == 1 else 0
    # Whole-race conservation protects against mixing ballots or duplicate modes.
    if total and abs(sum(candidates.values()) - total) > max(2, total * 0.00001):
        reasons.add("race_vote_sum_mismatch")
    if any(v > total for v in candidates.values()) and total:
        reasons.add("candidate_fusion_sum_exceeds_total")
    return dict(total=total, candidates=dict(candidates), parties=parties,
                originals=originals, reasons=sorted(reasons))


def ballot_reason(chamber, year, state, cd, stage, special, race, runoff_keys):
    reasons = list(race["reasons"])
    if stage not in {"GEN", "RUNOFF", "GEN RUNOFF"}:
        reasons.append("not_general_or_final_runoff")
    if chamber == "House" and cd in {"", "99", "100"}:
        reasons.append("unsupported_multimember_or_unknown_district")
    if state == "AK" and year == 2022:
        reasons.append("alaska_2022_first_round_not_final_rcv")
    if any("exhausted" in name for name in race["candidates"]):
        reasons.append("rcv_exhausted_ballot_round_unverified")
    if chamber == "House" and state == "NY" and year == 2020 and cd == "22":
        reasons.append("ny22_2020_result_unresolved_at_2021_cutoff")
    if chamber == "Senate" and state == "GA" and year == 2020 and stage == "GEN":
        reasons.append("georgia_runoff_completed_after_2021_cutoff")
    if stage == "GEN" and (chamber, year, state, cd, special) in runoff_keys:
        reasons.append("superseded_by_same_year_runoff")
    if state in {"GA", "LA"} and stage == "GEN" and race["total"]:
        valid = valid_candidate_counts(race)
        if max(valid.values(), default=0) / max(sum(valid.values()), 1) <= .5:
            reasons.append("majority_required_final_ballot_unverified")
    # Specials lack actual election dates and race IDs; the MEDSL year is not
    # enough to order multiple specials. Regular ballots take priority below.
    if special:
        reasons.append("special_election_exact_date_unverified")
    return sorted(set(reasons))


def load_people():
    people = {}
    for name in ("legislators-historical.yaml", "legislators-current.yaml"):
        rows = yaml.load((REF / name).read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
        for row in rows:
            bio = row.get("id", {}).get("bioguide")
            if bio:
                people[bio] = row
    roster = collections.defaultdict(dict)
    with (ROOT / "votes/HSall_members.csv").open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            cg = int(row["congress"])
            bio = row["bioguide_id"]
            if cg not in CUTOFFS or row["chamber"] not in {"House", "Senate"} or not bio:
                continue
            member = roster[cg].setdefault(bio, dict(chambers=set(), states=set()))
            member["chambers"].add(row["chamber"])
            member["states"].add(row["state_abbrev"])
            # Voteview bioname is another public identity alias, never a label.
            if bio in people and "," in row["bioname"]:
                people[bio].setdefault("_given_aliases", []).append(row["bioname"].split(",", 1)[1])
    return people, roster


def build():
    people, roster = load_people()
    paths = {
        "house": ROOT.parent / "Draft Systems/medsl_house.csv",
        "senate": ROOT.parent / "Draft Systems/medsl_senate.csv",
        "current_identities": REF / "legislators-current.yaml",
        "historical_identities": REF / "legislators-historical.yaml",
        "roster": ROOT / "votes/HSall_members.csv",
    }
    source_hashes = {key: dict(path=str(p), sha256=sha256(p), bytes=p.stat().st_size)
                     for key, p in paths.items()}
    groups = collections.defaultdict(list)
    source_versions = {}
    source_counts = {}
    for key, chamber in [("house", "House"), ("senate", "Senate")]:
        with paths[key].open(encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        source_counts[key] = len(rows)
        source_versions[key] = dict(collections.Counter(r["version"] for r in rows))
        for row in rows:
            year = int(row["year"])
            # Final119 and2024 rows are never considered; retain older Senate
            # rows for latest completed election, House only2020/2022.
            if year > 2022 or (chamber == "House" and year not in {2020, 2022}):
                continue
            if row["mode"].upper() != "TOTAL":
                continue
            group = (chamber, year, row["state_po"], district(row["district"]),
                     row["stage"].upper(), boolval(row["special"]))
            groups[group].append(row)
    runoff_keys = {key[:4] + (key[5],) for key in groups if "RUNOFF" in key[4]}
    all_target_ids = set().union(*(set(rows) for rows in roster.values()))
    scoped_people = collections.defaultdict(list)
    for bio in all_target_ids:
        if bio not in people:
            continue
        for t in people[bio].get("terms", []):
            if t.get("type") in {"rep", "sen"}:
                scoped_people[("House" if t["type"] == "rep" else "Senate", t["state"])].append(bio)
    scoped_people = {key: sorted(set(ids)) for key, ids in scoped_people.items()}
    matches = collections.defaultdict(list)
    ambiguous = []
    race_rejections = collections.Counter()
    for key, source_rows in groups.items():
        chamber, year, state, cd, stage, special = key
        race = aggregate_race(source_rows, chamber)
        reasons = ballot_reason(chamber, year, state, cd, stage, special, race, runoff_keys)
        race_rejections.update(reasons)
        for cand, votes in race["candidates"].items():
            candidate_ids = [bio for bio in scoped_people.get((chamber, state), [])
                             if name_matches(cand, people[bio])
                             and relevant_term(people[bio], chamber, state, year, cd)]
            if len(candidate_ids) > 1:
                ambiguous.append(dict(race=list(key), candidate=cand, bioguides=candidate_ids))
                for bio in candidate_ids:
                    matches[bio].append(dict(key=key, candidate=cand, reasons=["ambiguous_candidate_identity"],
                                             race=race, votes=votes))
            elif len(candidate_ids) == 1:
                reasons2 = list(reasons)
                other = max((v for name, v in valid_candidate_counts(race).items() if name != cand), default=0)
                if votes <= other:
                    reasons2.append("candidate_not_unique_winner")
                matches[candidate_ids[0]].append(dict(key=key, candidate=cand, reasons=reasons2,
                                                     race=race, votes=votes))
    output = []
    for cg, members in sorted(roster.items()):
        cutoff = CUTOFFS[cg]
        for bio, identity in sorted(members.items()):
            row = dict(congress=cg, memberBioguide=bio, as_of=cutoff.isoformat(),
                       chamber="|".join(sorted(identity["chambers"])),
                       state="|".join(sorted(identity["states"])),
                       election_share=None, election_margin=None, election_log_total_votes=None,
                       election_uncontested=None, election_years_ago=None, election_missing=1,
                       prior_service_years=None, prior_service_missing=int(bio not in people),
                       election_year=None, election_stage="", election_special=None,
                       election_candidate="", election_candidate_party="",
                       election_votes=None, election_total_votes=None, election_margin_votes=None,
                       election_valid_vote_total=None,
                       availability_upper_bound="", availability_verified=0,
                       temporal_basis="retrospective_event_reconstruction; certification_date_unverified",
                       identity_basis="unique_full_given_or_source_nickname+surname+state+office+term+district",
                       missing_reason="")
            if bio in people:
                row["prior_service_years"] = round(prior_service(people[bio], cutoff), 6)
            if len(identity["chambers"]) != 1 or len(identity["states"]) != 1:
                row["missing_reason"] = "multiple_chambers_or_states_in_congress"
                output.append(row)
                continue
            # No current party/district is used. Actual matched ballot party is
            # exported as provenance only, never guessed for unmatched members.
            choices = [m for m in matches.get(bio, []) if m["key"][0] == row["chamber"]
                       and m["key"][2] == row["state"] and m["key"][1] < cutoff.year
                       and (row["chamber"] == "Senate" or m["key"][1] == cutoff.year - 1)]
            if row["chamber"] == "Senate" and bio in people:
                terms = [t for t in people[bio].get("terms", [])
                         if t.get("type") == "sen" and t.get("state") == row["state"]
                         and date(t["start"]) <= cutoff]
                if terms:
                    latest_start = max(date(t["start"]) for t in terms)
                    expected_year = latest_start.year - int((latest_start.month, latest_start.day) == (1, 3))
                    # A failed newer name match cannot silently restore an
                    # election from six years earlier. Nonstandard term starts
                    # require an election in their actual calendar year.
                    choices = [m for m in choices if m["key"][1] >= expected_year]
            if not choices:
                row["missing_reason"] = "no_unique_matching_pre_cutoff_election"
                output.append(row)
                continue
            # Latest year, then regular term over concurrent special, final
            # runoff over general. Reject tied distinct ballots, never max votes.
            score = lambda m: (m["key"][1], not m["key"][5], "RUNOFF" in m["key"][4])
            best_score = max(map(score, choices))
            best = [m for m in choices if score(m) == best_score]
            if len(best) != 1:
                row["missing_reason"] = "multiple_same_priority_ballots"
                output.append(row)
                continue
            m = best[0]
            chamber, year, state, cd, stage, special = m["key"]
            row.update(election_year=year, election_stage=stage, election_special=int(special),
                       election_candidate=m["candidate"],
                       election_candidate_party="|".join(sorted(m["race"]["parties"][m["candidate"]])),
                       availability_upper_bound=f"{year}-12-31")
            if m["reasons"]:
                row["missing_reason"] = ";".join(sorted(set(m["reasons"])))
                output.append(row)
                continue
            total, votes = m["race"]["total"], m["votes"]
            valid = valid_candidate_counts(m["race"])
            valid_total = sum(valid.values())
            other = max((v for name, v in valid.items() if name != m["candidate"]), default=0)
            named_opponents = [name for name, v in valid.items()
                               if name != m["candidate"] and v > 0
                               and name and not re.search(r"write\s*in|overvote|undervote|scattering|blank", name)]
            row.update(election_share=round(votes / valid_total, 8),
                       election_margin=round((votes - other) / valid_total, 8),
                       election_log_total_votes=round(math.log1p(total), 8),
                       election_uncontested=int(not named_opponents),
                       election_years_ago=cutoff.year - 1 - year,
                       election_missing=0, election_votes=votes,
                       election_total_votes=total, election_valid_vote_total=valid_total,
                       election_margin_votes=votes - other)
            output.append(row)
    assert len({(r["congress"], r["memberBioguide"]) for r in output}) == len(output)
    assert all(r["election_year"] is None or r["election_year"] < CUTOFFS[r["congress"]].year for r in output)
    assert all(r["election_missing"] or (0 <= r["election_share"] <= 1 and 0 < r["election_margin"] <= 1) for r in output)
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "election_history.csv"
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    receipt = dict(schema="cosponsor-universe-election-v1", generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
                   code_sha256=sha256(__file__), source_hashes=source_hashes,
                   source_counts=source_counts, source_versions=source_versions,
                   rows=len(output), features=FEATURES,
                   row_counts={str(cg): sum(r["congress"] == cg for r in output) for cg in CUTOFFS},
                   complete_elections={str(cg): sum(r["congress"] == cg and not r["election_missing"] for r in output) for cg in CUTOFFS},
                   missing_reasons=dict(collections.Counter(r["missing_reason"] for r in output if r["missing_reason"])),
                   ambiguous_candidate_joins=ambiguous, rejected_race_reason_counts=dict(race_rejections),
                   output=dict(path=str(target), sha256=sha256(target)),
                   constraints=["No Congress119/2024 election rows entered feature construction.",
                                "House uses2020 for117 and2022 for118; Senate latest matched prior completed ballot; unsupported latest ballot remains missing rather than falling back.",
                                "Year-end availability is a conservative event-order proxy, NOT a verified source publication date; all availability_verified=0.",
                                "MEDSL records are later source versions. This is retrospective reconstruction, not observation-time evidence. FEC books normally publish the following summer.",
                                "Alaska2022 source first-round votes excluded; GA2020 general cannot stand in for January2021 runoff. Same-year final runoff preferred. Specials lacking exact dates excluded.",
                                "No generic nickname/party/surname-only guesses. Fusion lines summed by normalized full candidate; all source ballots must conserve votes.",
                                "Share and margin use valid candidate votes, including write-ins but excluding over/under/blank/void ballots. Log total votes retains the raw reported turnout denominator. Unverified exhausted-ballot RCV totals excluded.",
                                "Failed latest Senate election identity cannot fall back to an older six-year cycle: choices must match the latest pre-cutoff term-start election year.",
                                "Term tenure clips pre-cutoff service; future term ends never add service time. Candidate party is provenance, not a model feature."],
                   publication_references=["https://www.fec.gov/press/resources-journalists/elections/",
                       "https://results.sos.ga.gov/results/public/Georgia",
                       "https://www.elections.alaska.gov/election-results/e/?id=22genr",
                       "https://www.nycourts.gov/REPORTER/3dseries/2021/2021_21022.htm",
                       "https://www.congress.gov/117/crec/2021/02/11/CREC-2021-02-11-pt1-PgH492-3.pdf"])
    (OUT / "election_history.receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in ["rows", "complete_elections", "missing_reasons"]}, indent=2))


def self_test():
    person = {"name": {"first": "Henry", "last": "Johnson", "nickname": "Hank"},
              "terms": [{"type": "rep", "state": "GA", "district": 4,
                         "start": "2007-01-03", "end": "2030-01-03"}]}
    assert name_matches('HENRY C. "HANK" JOHNSON JR', person)
    assert name_matches("JOHNSON, HANK", person)
    assert not name_matches("H. JOHNSON", person)
    assert not name_matches("MIKE JOHNSON", person)
    assert district(0) == "0"
    assert abs(prior_service(person, dt.date(2008, 1, 3)) - 365 / 365.25) < 1e-9
    assert not relevant_term(person, "Senate", "GA", 2006, "0")
    base = dict(candidate="SMITH, JOHN", candidatevotes="40", totalvotes="100", unofficial="FALSE", party="D")
    fusion = aggregate_race([base, dict(base, candidatevotes="20", party="W"), dict(base, candidate="JONES, JANE", candidatevotes="40")], "House")
    assert fusion["candidates"]["john smith"] == 60 and not fusion["reasons"]
    duplicate = aggregate_race([base, base, dict(base, candidate="JONES, JANE", candidatevotes="40")], "House")
    assert "race_vote_sum_mismatch" in duplicate["reasons"]
    invalid = aggregate_race([dict(base, candidatevotes="-1")], "House")
    assert "invalid_numeric_race" in invalid["reasons"]
    assert "undervotes" not in valid_candidate_counts(dict(candidates={"john smith": 50, "undervotes": 60}))
    assert "alaska_2022_first_round_not_final_rcv" in ballot_reason("House", 2022, "AK", "0", "GEN", False, fusion, set())
    assert "georgia_runoff_completed_after_2021_cutoff" in ballot_reason("Senate", 2020, "GA", "0", "GEN", False, fusion, set())
    print("election boundary self-tests passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    self_test() if args.self_test else build()
