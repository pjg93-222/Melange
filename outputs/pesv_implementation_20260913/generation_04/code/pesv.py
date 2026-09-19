"""Pure P / five-stage effectiveness / average substance / engagement-volume candidate.

No filesystem access, production imports, forecasting, or institutional-power terms.
The five-stage results follow the supplied plan; participation and half-life credits
are the explicitly identified Melange extensions to the sponsor-only reference.
"""
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date
import math
import re

STAGES = ("BILL", "AIC", "ABC", "PASS", "LAW")
ROLE_WEIGHTS = {"sponsor": 1.0, "original": .5, "cosponsor": .25}
LAWFUL = frozenset(("hr", "s", "hjres", "sjres"))


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parsed_date(value):
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def chamber(value):
    return {"h": "house", "rep": "house", "s": "senate", "sen": "senate"}.get(
        str(value).lower(), str(value).lower())


@dataclass(frozen=True)
class Policy:
    cosponsor_half_life_days: float = 180.0

    def __post_init__(self):
        if not finite(self.cosponsor_half_life_days) or self.cosponsor_half_life_days <= 0:
            raise ValueError("cosponsor_half_life_days must be positive and finite")

    def receipt(self):
        return dict(asdict(self), policy_id="primacy_effectiveness_substance_volume_v1",
                    status="isolated_candidate_not_predictively_validated",
                    ordering="P, chamber effectiveness percentile, chamber mean-substance percentile, chamber engagement-volume percentile; descending; stop after unavailable dimension; bioguide",
                    efficiency="N/5 * sum of five full-chamber impact-weighted stage shares with signed tensor CU participation credit",
                    efficiency_label="relative realized legislative effectiveness; not own-attempt conversion rate",
                    substance="role/timing/positive-CU-weighted mean impact over distinct beneficial law-capable engagements",
                    volume="sum role * timing * positive tensor CU over distinct beneficial law-capable engagements; no impact weight",
                    role_weights=dict(ROLE_WEIGHTS),
                    timing="2**(-introduction_to_first_cosponsor_join_days/H), later cosponsors only; original/sponsor timing=1",
                    participation="join must occur during verified service; active official role earns later milestone credit without an additional service-exit discount; attribution is not causation",
                    pre_introduction_actions="observed official pre-introduction milestones remain in chamber denominators; no member earns milestones before joining",
                    closing_day="canonical Congress controls membership on its January 3 closing date; noon cannot be resolved from date-only records; closing-day introductions/joins are retained and flagged",
                    half_life_status="180-day original-plan illustrative candidate; uncalibrated",
                    stages=list(STAGES), stage_weights="five additive shares; no extra stage multipliers",
                    missingness="unknown remains unavailable; denominator uncertainty blocks chamber effectiveness",
                    institutional_power="excluded from scoring and ordering",
                    significance="use recorded impact 1/5/10; no invented significant class or publication multiplier",
                    limitations="retrospective accepted selection; participation attribution is not causal credit; no term pooling")


def percentiles(values):
    known = {key: value for key, value in values.items() if value is not None}
    if any(not finite(value) for value in known.values()):
        raise ValueError("nonfinite percentile input")
    first = {}
    for index, value in enumerate(sorted(known.values())):
        first.setdefault(value, index)
    return {key: math.floor(first[value] / max(1, len(known)-1) * 100000) / 100000
            for key, value in known.items()}


def intervals(row):
    raw = row.get("service_periods") or [{"start": row.get("service_start"), "end": row.get("service_end")}]
    spans = []
    for item in raw:
        start, end = parsed_date(item.get("start")), parsed_date(item.get("end"))
        if start is None or end is None or end <= start:
            return []
        spans.append((start, end))
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def served(spans, when):
    return any(start <= when < end for start, end in spans)


def unique_map(rows, field):
    out = {}
    for row in rows:
        key = str(row.get(field) or "")
        if not key:
            raise ValueError("missing " + field)
        if key in out and out[key] != row:
            raise ValueError("conflicting duplicate " + field + ": " + key)
        out[key] = dict(row)
    return out


def measure_parts(mid):
    match = re.fullmatch(r"(\d+):([a-z]+):(.+)", str(mid))
    if not match:
        raise ValueError("invalid canonical measure: " + str(mid))
    return int(match[1]), match[2]


def blank_member(bio, c, person):
    return dict(bioguide_id=bio, chamber=c, name=person.get("name", bio),
                efficiency_raw=None, efficiency_score=None, efficiency_status="no_verified_selected_activity",
                substance_raw=None, substance_score=None, substance_status="no_verified_beneficial_activity",
                volume_raw=None, volume_score=None, volume_status="no_verified_selected_activity",
                useful_volume=0, useful_measures=0, harmful_volume=0, neutral_volume=0, unknown_volume=0,
                harmful_weighted_volume=0., roles={role: {"measures": 0, "weighted_volume": 0., "results": 0.}
                                                  for role in ROLE_WEIGHTS},
                stages={s: {"credited_measures": 0, "observed_net": 0.} for s in STAGES},
                coverage=Counter(), _results=[], _volume=[], _harm=[], _substance=[], _seen=0)


def compute_metrics(bills, roles, signals, roster, impacts, *, congress, as_of, policy=None):
    policy = policy or Policy()
    cutoff = parsed_date(as_of)
    if isinstance(congress, bool) or not isinstance(congress, int) or congress < 1 or cutoff is None:
        raise ValueError("valid congress and as_of required")
    start, stop = date(1789 + 2*(congress-1), 1, 3), date(1789 + 2*congress, 1, 3)
    if cutoff < start:
        raise ValueError("cutoff precedes Congress")
    members, service = {}, {}
    for person in roster:
        if int(person.get("congress", congress)) != congress:
            continue
        bio, c = str(person.get("bioguide_id") or person.get("bioguide") or ""), chamber(person.get("chamber"))
        if not bio or c not in ("house", "senate"):
            raise ValueError("invalid roster identity/chamber")
        key = bio + "|" + c
        if key in members:
            raise ValueError("duplicate roster identity: " + key)
        spans = intervals(person)
        if spans and not any(a <= cutoff and a < stop and b > start for a, b in spans):
            continue
        members[key], service[key] = blank_member(bio, c, person), spans
    terms = {c: {"population": sum(row["chamber"] == c for row in members.values()),
                 "denominators": dict.fromkeys(STAGES, 0.), "coverage": Counter(),
                 "impact_weights": Counter()} for c in ("house", "senate")}
    bill_map = unique_map((b for b in bills if int(b.get("congress", congress)) == congress), "measure_id")
    impact_map = unique_map((i for i in impacts if measure_parts(i.get("measure_id"))[0] == congress), "measure_id")
    prepared = {}
    for mid, bill in sorted(bill_map.items()):
        term, kind = measure_parts(mid)
        c, declared_kind = chamber(bill.get("chamber")), str(bill.get("measure_type") or "").lower()
        if term != congress or c not in terms or declared_kind != kind:
            raise ValueError("bill identity/type/chamber mismatch: " + mid)
        if kind != "letter" and ((kind.startswith("h") and c != "house") or (kind.startswith("s") and c != "senate")):
            raise ValueError("bill kind/chamber mismatch: " + mid)
        termrow = terms[c]
        termrow["coverage"]["source_measures"] += 1
        intro = parsed_date(bill.get("introduced_date"))
        if intro and intro > cutoff:
            prepared[mid] = {"status": "future_introduction", "chamber": c}
            continue
        if kind not in LAWFUL or bill.get("eligible") is False:
            prepared[mid] = {"status": "nonlaw_measure", "chamber": c}
            continue
        errors = []
        if bill.get("eligible") is not True:
            errors.append("invalid_bill_eligibility")
        if intro is None or not start <= intro <= stop:
            errors.append("invalid_introduction")
        elif intro == stop:
            termrow["coverage"]["closing_day_introduction"] += 1
        snapshot = parsed_date(bill.get("as_of"))
        if snapshot is None or snapshot < cutoff:
            errors.append("incomplete_bill_snapshot")
        impact = impact_map.get(mid, {})
        impact_time = parsed_date(impact.get("effective_date"))
        weight = impact.get("weight")
        impact_valid = (finite(weight) and weight in (1, 5, 10)
                        and (not impact.get("effective_date") or impact_time is not None)
                        and (impact_time is None or impact_time <= cutoff))
        if impact.get("class") is not None and {"C": 1, "S": 5, "SS": 10}.get(str(impact["class"]).upper()) != weight:
            impact_valid = False
        impact_snapshot = parsed_date(impact.get("as_of"))
        if impact.get("as_of") and (impact_snapshot is None or impact_snapshot < cutoff):
            impact_valid = False
        if not impact_valid:
            weight = None
            errors.append("unknown_impact")
        else:
            weight = float(weight)
            termrow["impact_weights"][str(int(weight))] += 1
        dated = {}
        for stage in STAGES:
            event = bill.get("milestones", {}).get(stage, {})
            reached, state = event.get("reached"), event.get("state")
            when = parsed_date(event.get("date"))
            valid = (isinstance(reached, bool) and state in ("observed", "inferred")
                     and ((reached is True and when is not None and intro is not None)
                          or (reached is False and not event.get("date"))))
            if stage == "BILL" and (reached is not True or when != intro):
                valid = False
            if not valid:
                errors.append("unknown_milestone_" + stage)
            elif reached and when <= cutoff:
                if when < intro:
                    termrow["coverage"]["pre_introduction_" + stage] += 1
                dated[stage] = when
                if weight is not None:
                    termrow["denominators"][stage] += weight
        termrow["coverage"]["eligible_measures"] += 1
        for error in errors:
            termrow["coverage"][error] += 1
        if errors:
            termrow["coverage"]["unknown_denominator_measures"] += 1
        prepared[mid] = {"status": "eligible", "chamber": c, "introduced": intro,
                         "weight": weight, "dated": dated, "errors": errors,
                         "impact_provisional": ("provisional" in str(impact.get("coverage_status", ""))
                                                or "default" in str(impact.get("basis", "")))}
    for c, term in terms.items():
        term["zero_denominator_stages"] = [s for s in STAGES if term["denominators"][s] == 0]
        term["denominators_available"] = (term["population"] > 0 and not term["zero_denominator_stages"]
                                          and not term["coverage"]["unknown_denominator_measures"])
        term["uniform_impact_weight"] = (float(next(iter(term["impact_weights"])))
                                          if len(term["impact_weights"]) == 1 else None)
    accepted, role_groups = defaultdict(list), defaultdict(list)
    for s in signals:
        if s.get("accepted") is not True:
            continue
        mid = str(s.get("measure_id") or "")
        if measure_parts(mid)[0] != congress:
            continue
        effective = parsed_date(s.get("effective_date"))
        if effective and effective > cutoff:
            continue
        accepted[mid].append(s)
    for r in roles:
        mid, bio = str(r.get("measure_id") or ""), str(r.get("bioguide_id") or "")
        if mid in accepted and bio:
            role_groups[(mid, bio)].append(r)
    scopes = set(role_groups)
    for mid, rows in accepted.items():
        scopes.update((mid, str(s["bioguide_id"])) for s in rows if s.get("bioguide_id"))
    contributions = []
    for mid, bio in sorted(scopes):
        selected = [s for s in accepted[mid] if not s.get("bioguide_id") or str(s["bioguide_id"]) == bio]
        if not selected:
            continue
        record = prepared.get(mid)
        if record:
            c = record["chamber"]
        else:
            _, kind = measure_parts(mid)
            c = "house" if kind.startswith("h") else "senate" if kind.startswith("s") else None
            if c is None:
                # Unverified non-bill records have no invented chamber or roles.
                for row in members.values():
                    if row["bioguide_id"] == bio:
                        row["coverage"]["excluded_nonlaw_or_letter"] += 1
                continue
        key = bio + "|" + c
        if key not in members:
            continue
        row = members[key]
        row["coverage"]["accepted_unique_measures"] += 1
        if record and record["status"] != "eligible":
            row["coverage"][record["status"]] += 1
            continue
        if record and "invalid_bill_eligibility" in record["errors"]:
            row["unknown_volume"] += 1
            row["coverage"]["unknown_selected_scope"] += 1
            contributions.append(dict(kind="unavailable", measure_id=mid, bioguide_id=bio, chamber=c,
                                      status="invalid_bill_eligibility"))
            continue
        values = [s.get("tensor_cu") for s in selected]
        valid_dates = all(not s.get("effective_date") or parsed_date(s["effective_date"]) for s in selected)
        sign = float(values[0]) if (valid_dates and all(finite(v) and -1 <= v <= 1 for v in values)
                                    and len(set(values)) == 1) else None
        if sign is None or record is None:
            row["unknown_volume"] += 1
            row["coverage"]["unknown_selected_scope"] += 1
            contributions.append(dict(kind="unavailable", measure_id=mid, bioguide_id=bio, chamber=c,
                                      status="unknown_alignment" if sign is None else "missing_bill"))
            continue
        raw_roles = role_groups[(mid, bio)]
        if raw_roles and all(parsed_date(r.get("joined_date")) and parsed_date(r["joined_date"]) > cutoff for r in raw_roles):
            row["coverage"]["future_participation"] += 1
            continue
        episodes, ends, bad = set(), {}, False
        intro = record["introduced"]
        for r in raw_roles:
            joined, withdrawn = parsed_date(r.get("joined_date")), parsed_date(r.get("withdrawn_date"))
            if joined and joined > cutoff:
                continue
            role = str(r.get("role") or "").lower()
            joined_in_service = (joined is not None and (served(service[key], joined)
                                  or (joined == stop and any(a <= joined == b for a, b in service[key]))))
            if (intro is None or joined is None or joined < intro or not start <= joined <= stop
                    or role not in ROLE_WEIGHTS or r.get("chronology_status") not in ("verified", "verified_same_day")
                    or (role in ("sponsor", "original") and joined != intro)
                    or (r.get("withdrawn_date") and withdrawn is None)
                    or (withdrawn and withdrawn < joined) or not joined_in_service):
                bad = True
                continue
            ident = (role, joined)
            if ident in ends and ends[ident] != withdrawn:
                bad = True
            ends[ident] = withdrawn
            episodes.add((role, joined, withdrawn))
        episode_list = sorted(episodes, key=lambda e: (e[1], e[0], e[2] or date.max))
        for previous, current in zip(episode_list, episode_list[1:]):
            if previous[2] is None or previous[2] > current[1]:
                bad = True
        if bad or not episodes:
            row["unknown_volume"] += 1
            row["coverage"]["unknown_selected_scope"] += 1
            contributions.append(dict(kind="unavailable", measure_id=mid, bioguide_id=bio, chamber=c,
                                      status="unverified_role_or_service"))
            continue
        first_late = min((joined for role, joined, _ in episodes if role == "cosponsor"), default=None)
        delay = (first_late - intro).days if first_late else 0
        late_multiplier = 2 ** (-delay / policy.cosponsor_half_life_days)
        credit = lambda episode: ROLE_WEIGHTS[episode[0]] * (late_multiplier if episode[0] == "cosponsor" else 1.)
        strongest = max(episode_list, key=lambda e: (credit(e), -e[1].toordinal(), e[0]))
        engagement = credit(strongest)
        role = strongest[0]
        row["_seen"] += 1
        if any(e[1] == stop for e in episodes):
            row["coverage"]["closing_day_participation_date_uncertainty"] += 1
        row["roles"][role]["measures"] += 1
        weight, term = record["weight"], terms[c]
        if sign > 0:
            row["useful_volume"] += 1
            row["_volume"].append(engagement * sign)
            row["roles"][role]["weighted_volume"] += engagement * sign
            if weight is None:
                row["coverage"]["unknown_substance"] += 1
            else:
                row["_substance"].append((engagement * sign, weight))
                if record["impact_provisional"]:
                    row["coverage"]["provisional_substance_measures"] += 1
        elif sign < 0:
            row["harmful_volume"] += 1
            row["_harm"].append(-engagement * sign)
        else:
            row["neutral_volume"] += 1
        contributions.append(dict(kind="engagement", measure_id=mid, bioguide_id=bio, chamber=c,
                                  role=role, first_join=min(e[1] for e in episodes).isoformat(),
                                  introduction=intro.isoformat(), timing_multiplier=late_multiplier if role == "cosponsor" else 1.,
                                  base_role_credit=ROLE_WEIGHTS[role], role_credit=engagement, tensor_cu=sign,
                                  impact_weight=weight, beneficial_volume=engagement * max(sign, 0.)))
        if record["errors"]:
            row["coverage"]["unknown_results_scope"] += 1
        for stage in STAGES:
            when = record["dated"].get(stage)
            if when is None:
                continue
            active = [e for e in episode_list if e[1] <= when and (e[2] is None or when < e[2])]
            if not active:
                continue
            episode = max(active, key=credit)
            denominator = term["denominators"][stage]
            amount = (term["population"] / 5 * weight / denominator * credit(episode) * sign
                      if term["denominators_available"] and weight is not None else None)
            row["stages"][stage]["credited_measures"] += 1
            if amount is not None:
                row["_results"].append(amount)
                row["stages"][stage]["observed_net"] += amount
                row["roles"][episode[0]]["results"] += amount
            contributions.append(dict(kind="stage", measure_id=mid, bioguide_id=bio, chamber=c,
                                      stage=stage, date=when.isoformat(), role=episode[0],
                                      timing_multiplier=late_multiplier if episode[0] == "cosponsor" else 1.,
                                      base_role_credit=ROLE_WEIGHTS[episode[0]], role_credit=credit(episode),
                                      tensor_cu=sign, impact_weight=weight, denominator=denominator,
                                      population=term["population"], contribution=amount))
    for row in members.values():
        cov, term = row["coverage"], terms[row["chamber"]]
        unknown = bool(cov["unknown_selected_scope"])
        if not term["denominators_available"]:
            row["efficiency_status"] = "unavailable_chamber_denominator"
        elif unknown or cov["unknown_results_scope"]:
            row["efficiency_status"] = "partial_unknown"
        elif row["_seen"]:
            row["efficiency_raw"] = math.fsum(row["_results"])
            row["efficiency_status"] = "observed_five_stage_results"
        if unknown or cov["unknown_substance"]:
            row["substance_status"] = "partial_unknown"
        elif row["_substance"]:
            unique_weights = {weight for _, weight in row["_substance"]}
            row["substance_raw"] = (next(iter(unique_weights)) if len(unique_weights) == 1 else
                                     math.fsum(v*w for v, w in row["_substance"]) /
                                     math.fsum(v for v, _ in row["_substance"]))
            row["substance_status"] = ("provisional_recorded_impact" if cov["provisional_substance_measures"]
                                        else "observed_recorded_impact")
        if unknown:
            row["volume_status"] = "partial_unknown"
        elif row["_seen"]:
            row["volume_raw"] = math.fsum(row["_volume"])
            row["volume_status"] = "observed_beneficial_engagement"
        row["harmful_weighted_volume"] = math.fsum(row["_harm"])
        row["useful_measures"] = row["useful_volume"]
        row["coverage"] = dict(sorted(cov.items()))
        for key in list(row):
            if key.startswith("_"):
                del row[key]
    for c, term in terms.items():
        for dimension in ("efficiency", "substance", "volume"):
            values = {key: row[dimension+"_raw"] for key, row in members.items() if row["chamber"] == c}
            ranks = percentiles(values)
            for key in values:
                members[key][dimension+"_score"] = ranks.get(key)
                members[key][dimension+"_peer_count"] = len(ranks)
            term[dimension+"_peer_count"] = len(ranks)
            term[dimension+"_discriminating"] = len(set(ranks.values())) > 1
        term["coverage"] = dict(sorted(term["coverage"].items()))
        term["impact_weights"] = dict(sorted(term["impact_weights"].items()))
    return {"schema": "pesv-metrics-v1", "congress": congress, "as_of": cutoff.isoformat(),
            "policy": policy.receipt(), "members": members, "contributions": contributions,
            "terms": terms, "chamber_diagnostics": terms}


def rank_members(rows):
    result, seen = [], set()
    dimensions = ("efficiency_score", "substance_score", "volume_score")
    for item in rows:
        row = dict(item)
        bio = str(row.get("bioguide_id") or "")
        if not bio or bio in seen:
            raise ValueError("missing or duplicate ranking identity")
        seen.add(bio)
        if row.get("P") is not None and not finite(row["P"]):
            raise ValueError("invalid P")
        for field in dimensions:
            if row.get(field) is not None and (not finite(row[field]) or not 0 <= row[field] <= 1):
                raise ValueError("invalid " + field)
        result.append(row)
    def key(row):
        parts = [row.get("P") is None, -(row.get("P") or 0)]
        blocked = row.get("P") is None
        for field in dimensions:
            value = None if blocked else row.get(field)
            parts.extend((value is None, -(value or 0)))
            blocked = blocked or value is None
        return (*parts, str(row["bioguide_id"]))
    result.sort(key=key)
    ordinal = 0
    for row in result:
        if row.get("P") is None:
            row["candidate_rank"] = None
        else:
            ordinal += 1
            row["candidate_rank"] = ordinal
    return result
