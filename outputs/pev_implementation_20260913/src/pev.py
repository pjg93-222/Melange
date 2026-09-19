"""Pure candidate: primacy, observed conversion, useful volume. No I/O/import side effects.

Conversion is ANY advancement beyond the highest stage observed before joining,
within one fully observed fixed window. Wilson scores are descriptive reliability
adjustments, not validated forecasts or confidence statements for dependent bills.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, timedelta
import math

STAGES = ("AIC", "ABC", "PASS", "LAW")
LAWFUL = frozenset(("hr", "s", "hjres", "sjres"))
ROLES = frozenset(("sponsor", "original", "cosponsor"))


@dataclass(frozen=True)
class Policy:
    horizon_days: int = 180
    wilson_z: float = 1.96

    def __post_init__(self):
        if isinstance(self.horizon_days, bool) or not isinstance(self.horizon_days, int) or self.horizon_days < 1:
            raise ValueError("horizon_days must be a positive integer")
        if not _finite(self.wilson_z) or self.wilson_z <= 0:
            raise ValueError("wilson_z must be positive and finite")

    def receipt(self):
        return dict(asdict(self), policy_id="primacy_efficiency_volume_v1",
                    status="candidate_not_predictively_validated",
                    ordering="P descending, known E before unknown at equal P, E descending, V descending only with known E, bioguide",
                    efficiency="within-chamber first-tie percentile of Wilson lower endpoint of any post-join advancement within complete fixed horizon",
                    attribution="unique positive tensor CU member-measure, unweighted Bernoulli attempt; role-stratified diagnostics",
                    volume="distinct verified positive tensor CU law-capable measures",
                    weights="no additional scalar blend or publication attention reward",
                    limitation="retrospective accepted selection; correlated bills; conventional horizon and reliability policy, not empirical optimum")


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _date(value):
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10]) if value else None
    except ValueError:
        return None


def _chamber(value):
    value = str(value).lower()
    return {"h": "house", "rep": "house", "s": "senate", "sen": "senate"}.get(value, value)


def wilson_lower(successes, attempts, z=1.96):
    if (any(isinstance(v, bool) or not isinstance(v, int) for v in (successes, attempts))
            or attempts < 0 or not 0 <= successes <= attempts or not _finite(z) or z <= 0):
        raise ValueError("invalid Wilson counts or z")
    if attempts == 0:
        return None
    p = successes / attempts
    z2 = z * z
    return max(0., min(1., (p + z2 / (2 * attempts) - z * math.sqrt(
        p * (1-p) / attempts + z2 / (4 * attempts**2))) / (1 + z2 / attempts)))


def percentiles(values):
    """Observed-only repository convention: first tie, denominator n-1, truncate5."""
    known = {key: value for key, value in values.items() if value is not None}
    if any(not _finite(value) for value in known.values()):
        raise ValueError("nonfinite percentile input")
    first = {}
    for index, value in enumerate(sorted(known.values())):
        first.setdefault(value, index)
    return {key: math.floor(first[value] / max(1, len(known)-1) * 100000) / 100000
            for key, value in known.items()}


def _intervals(member):
    raw = member.get("service_periods") or [{"start": member.get("service_start"), "end": member.get("service_end")}]
    spans = []
    for item in raw:
        start, end = _date(item.get("start")), _date(item.get("end"))
        if start is None or end is None or end <= start:
            return []
        spans.append((start, end))
    # Adjacent service records constitute a continuous observed service window.
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def _in_service(spans, when):
    return any(start <= when < end for start, end in spans)


def _blank(bio, chamber, member):
    return {"bioguide_id": bio, "chamber": chamber, "name": member.get("name", bio),
            "useful_volume": 0, "harmful_volume": 0, "neutral_volume": 0, "unknown_volume": 0,
            "eligible_attempts": 0, "successes": 0, "efficiency_raw": None, "efficiency_score": None,
            "efficiency_status": "no_observed_opportunities", "coverage": Counter(),
            "stages": {s: {"attempts": 0, "successes": 0} for s in STAGES},
            "roles": {r: {"volume": 0, "attempts": 0, "successes": 0} for r in sorted(ROLES)}}


def compute_metrics(bills, roles, signals, roster, *, congress, as_of, policy=None):
    """Return all roster records plus one auditable row per accepted member-measure.

    No unknown observation is converted to failure. One unknown accepted scope
    quarantines a member's efficiency ranking score while preserving observed
    numerator/denominator diagnostics. Immature windows remain explicitly separate.
    """
    policy = policy or Policy()
    cutoff = _date(as_of)
    if cutoff is None or isinstance(congress, bool) or not isinstance(congress, int):
        raise ValueError("valid as_of date and integer congress required")
    term_start = date(1789 + 2 * (congress - 1), 1, 3)
    term_end = date(term_start.year + 2, 1, 3)
    if cutoff < term_start:
        raise ValueError("cutoff precedes Congress")
    members, services = {}, {}
    for person in roster:
        if int(person.get("congress", congress)) != congress:
            continue
        bio = str(person.get("bioguide_id") or person.get("bioguide") or "")
        chamber = _chamber(person.get("chamber"))
        if not bio or chamber not in ("house", "senate"):
            raise ValueError("invalid roster identity/chamber")
        key = bio + "|" + chamber
        if key in members:
            raise ValueError("duplicate member/chamber roster record: " + key)
        members[key] = _blank(bio, chamber, person)
        services[key] = _intervals(person)
    bill_map = {}
    for bill in bills:
        if int(bill.get("congress", congress)) != congress:
            continue
        mid = str(bill["measure_id"])
        parts = mid.split(":")
        kind = str(bill.get("measure_type", "")).lower()
        chamber = _chamber(bill.get("chamber"))
        if (len(parts) != 3 or parts[0] != str(congress) or parts[1] != kind or not parts[2]
                or chamber not in ("house", "senate")
                or (kind.startswith("h") and chamber != "house")
                or (kind.startswith("s") and chamber != "senate")):
            raise ValueError("invalid or inconsistent bill identity/type/chamber: " + mid)
        if mid in bill_map and bill_map[mid] != bill:
            raise ValueError("conflicting duplicate bill: " + mid)
        bill_map[mid] = bill
    accepted = defaultdict(list)
    for signal in signals:
        if signal.get("accepted") is not True:
            continue
        effective = _date(signal.get("effective_date"))
        if effective and effective > cutoff:
            continue
        mid = str(signal.get("measure_id") or "")
        if mid.split(":", 1)[0] != str(congress):
            continue
        accepted[mid].append(signal)
    groups = defaultdict(list)
    for role in roles:
        mid, bio = str(role.get("measure_id") or ""), str(role.get("bioguide_id") or "")
        if mid in accepted and bio:
            groups[(mid, bio)].append(role)
    scopes = set(groups)
    for mid, rows in accepted.items():
        scopes.update((mid, str(s["bioguide_id"])) for s in rows if s.get("bioguide_id"))
    opportunity_rows = []
    for mid, bio in sorted(scopes):
        bill = bill_map.get(mid)
        chamber = _chamber(bill.get("chamber")) if bill else ("house" if mid.split(":")[1].startswith("h") else "senate")
        key = bio + "|" + chamber
        if key not in members:
            continue
        row = members[key]
        selected = [s for s in accepted[mid] if not s.get("bioguide_id") or str(s["bioguide_id"]) == bio]
        if not selected:
            continue
        trace = {"bioguide_id": bio, "chamber": chamber, "measure_id": mid, "status": None}
        opportunity_rows.append(trace)
        row["coverage"]["accepted_unique_measures"] += 1
        values = [s.get("tensor_cu") for s in selected]
        valid_dates = all(not s.get("effective_date") or _date(s["effective_date"]) for s in selected)
        sign = float(values[0]) if (valid_dates and all(_finite(v) and -1 <= v <= 1 for v in values) and len(set(values)) == 1) else None
        trace["tensor_cu"] = sign
        if sign is None:
            row["unknown_volume"] += 1
            row["coverage"]["unknown_attempts"] += 1
            trace["status"] = "unknown_or_conflicting_alignment"
            continue
        if sign <= 0:
            row["harmful_volume" if sign < 0 else "neutral_volume"] += 1
            trace["status"] = "harmful" if sign < 0 else "neutral"
            continue
        if bill is None:
            row["unknown_volume"] += 1
            row["coverage"]["unknown_attempts"] += 1
            trace["status"] = "missing_bill"
            continue
        if not isinstance(bill.get("eligible"), bool):
            row["unknown_volume"] += 1
            row["coverage"]["unknown_attempts"] += 1
            trace["status"] = "invalid_bill_eligibility"
            continue
        if bill.get("eligible") is False or str(bill.get("measure_type")).lower() not in LAWFUL:
            row["coverage"]["positive_nonlaw_measures"] += 1
            trace["status"] = "nonlaw_measure"
            continue
        intro = _date(bill.get("introduced_date"))
        if intro and intro > cutoff:
            row["coverage"]["future_introductions"] += 1
            trace["status"] = "future_introduction"
            continue
        role_rows = groups[(mid, bio)]
        if role_rows and all(_date(r.get("joined_date")) and _date(r["joined_date"]) > cutoff for r in role_rows):
            row["coverage"]["future_participation"] += 1
            trace["status"] = "future_participation"
            continue
        episodes, ends, bad = set(), {}, False
        for item in groups[(mid, bio)]:
            joined, withdrawn = _date(item.get("joined_date")), _date(item.get("withdrawn_date"))
            if joined and joined > cutoff:
                continue
            role = str(item.get("role", "")).lower()
            if (intro is None or not term_start <= intro < term_end or joined is None or joined < intro
                    or not term_start <= joined < term_end or role not in ROLES
                    or str(item.get("chronology_status", "")).lower() not in ("verified", "verified_same_day")
                    or (item.get("withdrawn_date") and withdrawn is None)
                    or (withdrawn and withdrawn < joined)
                    or (role in ("sponsor", "original") and joined != intro)
                    or not _in_service(services[key], joined)):
                bad = True
                continue
            episode_key = (role, joined)
            if episode_key in ends and ends[episode_key] != withdrawn:
                bad = True
            ends[episode_key] = withdrawn
            episodes.add((role, joined, withdrawn))
        if bad or not episodes:
            row["unknown_volume"] += 1
            row["coverage"]["unknown_attempts"] += 1
            trace["status"] = "unverified_role_or_service"
            continue
        joined = min(e[1] for e in episodes)
        role = min(episodes, key=lambda e: (("sponsor", "original", "cosponsor").index(e[0]), e[1]))[0]
        end = joined + timedelta(days=policy.horizon_days)
        row["useful_volume"] += 1
        row["roles"][role]["volume"] += 1
        trace.update(first_join=joined.isoformat(), horizon_end=end.isoformat(), role=role,
                     episodes=[{"role": r, "joined": j.isoformat(), "withdrawn": w.isoformat() if w else None}
                               for r, j, w in sorted(episodes, key=lambda e: (e[1], e[0], e[2] or date.max))])
        if end > cutoff or end >= term_end:
            row["coverage"]["immature_horizon"] += 1
            trace["status"] = "immature_horizon"
            continue
        if not any(start <= joined and end < stop for start, stop in services[key]):
            row["coverage"]["service_window_incomplete"] += 1
            trace["status"] = "service_window_incomplete"
            continue
        observed_through = _date(bill.get("as_of"))
        if observed_through is None or observed_through < end:
            row["coverage"]["unknown_attempts"] += 1
            trace["status"] = "milestone_observation_window_incomplete"
            continue
        dates, unknown = {}, False
        for stage in STAGES:
            item = bill.get("milestones", {}).get(stage, {})
            reached, state, event = item.get("reached"), item.get("state"), _date(item.get("date"))
            if (state not in ("observed", "inferred") or not isinstance(reached, bool)
                    or (reached is True and (event is None or event < intro))
                    or (reached is False and item.get("date"))):
                unknown = True
            dates[stage] = event if reached is True and event and event <= cutoff else None
        if unknown:
            row["coverage"]["unknown_attempts"] += 1
            trace["status"] = "unknown_milestone_history"
            continue
        baseline = max((i for i, s in enumerate(STAGES) if dates[s] and dates[s] < joined), default=-1)
        if baseline == len(STAGES)-1:
            row["coverage"]["already_enacted_before_join"] += 1
            trace["status"] = "already_enacted_before_join"
            continue
        active = lambda when: any(j <= when and (w is None or when < w) for _, j, w in episodes)
        advanced = [s for i, s in enumerate(STAGES) if i > baseline and dates[s]
                    and joined <= dates[s] <= end and active(dates[s]) and _in_service(services[key], dates[s])]
        row["eligible_attempts"] += 1
        row["successes"] += bool(advanced)
        row["roles"][role]["attempts"] += 1
        row["roles"][role]["successes"] += bool(advanced)
        for stage in STAGES:
            if dates[stage] and dates[stage] < joined:
                continue
            row["stages"][stage]["attempts"] += 1
            row["stages"][stage]["successes"] += bool(dates[stage] and joined <= dates[stage] <= end and active(dates[stage]))
        trace.update(status="observed_success" if advanced else "observed_no_advancement",
                     baseline=STAGES[baseline] if baseline >= 0 else "BILL", advanced_stages=advanced)
    for row in members.values():
        n, k = row["eligible_attempts"], row["successes"]
        row["efficiency_raw"] = k/n if n else None
        if row["coverage"]["unknown_attempts"]:
            row["efficiency_status"] = "partial_unknown"
        elif n:
            row["efficiency_status"] = "observed_matched_horizon"
            row["efficiency_score"] = wilson_lower(k, n, policy.wilson_z)
        for counts in row["stages"].values():
            k, n = counts["successes"], counts["attempts"]
            counts.update(raw=k/n if n else None, lower=wilson_lower(k, n, policy.wilson_z))
        row["coverage"] = dict(sorted(row["coverage"].items()))
    for chamber in ("house", "senate"):
        peers = {key: row["efficiency_score"] for key, row in members.items() if row["chamber"] == chamber}
        normalized = percentiles(peers)
        for key in peers:
            members[key]["efficiency_percentile"] = normalized.get(key)
            members[key]["efficiency_peer_count"] = len(normalized)
    return {"schema": "pev-metrics-v1", "congress": congress, "as_of": cutoff.isoformat(),
            "policy": policy.receipt(), "members": members, "opportunities": opportunity_rows}


def rank_members(rows):
    """Strict total order; missingness cannot supply a best-case efficiency score."""
    seen, result = set(), []
    for item in rows:
        row = dict(item)
        bio = str(row.get("bioguide_id") or "")
        if not bio or bio in seen:
            raise ValueError("missing or duplicate ranking identity")
        seen.add(bio)
        for field in ("P", "efficiency_score"):
            value = row.get(field)
            if value is not None and not _finite(value):
                raise ValueError("invalid " + field)
        e, volume = row.get("efficiency_score"), row.get("useful_volume")
        if e is not None and not 0 <= e <= 1:
            raise ValueError("efficiency score outside [0,1]")
        if isinstance(volume, bool) or not isinstance(volume, int) or volume < 0:
            raise ValueError("invalid useful volume")
        result.append(row)
    result.sort(key=lambda r: (r.get("P") is None, -(r.get("P") or 0),
                              r.get("efficiency_score") is None, -(r.get("efficiency_score") or 0),
                              -r["useful_volume"] if r.get("efficiency_score") is not None else 0,
                              r["bioguide_id"]))
    ordinal = 0
    for row in result:
        if row.get("P") is None:
            row["candidate_rank"] = None
        else:
            ordinal += 1
            row["candidate_rank"] = ordinal
    return result
