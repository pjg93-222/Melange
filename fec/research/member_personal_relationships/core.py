"""Pure relationship evidence and feature contracts. Scores are review priorities."""
from __future__ import annotations

from collections import defaultdict, deque
from datetime import date, timedelta
from math import exp, isfinite, sqrt, tanh

PERSONAL = {"personal_warmth", "personal_trust", "chosen_association",
            "personal_support", "personal_hostility", "personal_avoidance"}
REVIEWED = {"assistant_reviewed", "human_reviewed"}
ATTRIBUTED = {"direct_speaker", "attributed_quote", "named_witness"}


def parse_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def finite(value):
    return isinstance(value, (int, float)) and isfinite(value)


def accepted_events(events, as_of, start=None):
    cutoff, earliest = parse_date(as_of), parse_date(start)
    if cutoff is None:
        raise ValueError("A valid as-of date is required")
    out = []
    for e in events:
        day, published = parse_date(e.get("event_date")), parse_date(e.get("published_date"))
        if not day or not published or max(day, published) > cutoff or (earliest and day < earliest):
            continue
        if e.get("actor") == e.get("target") or not e.get("actor") or not e.get("target"):
            continue
        if e.get("category") not in PERSONAL or e.get("sign") not in {"positive", "negative"}:
            continue
        if e.get("review_status") not in REVIEWED or e.get("attribution") not in ATTRIBUTED:
            continue
        out.append(e)
    return out


def collapse_episodes(events):
    """Connected components of same episode OR source family, within pair and sign.

    Returns one representative with all original IDs retained. Repeated accounts of
    the same underlying anecdote must have the same reviewed episode ID.
    """
    events = sorted(events, key=lambda e: (e.get("event_date") or "", e.get("evidence_id") or ""))
    parent = list(range(len(events)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    seen = {}
    for i, e in enumerate(events):
        for field in ("episode_id", "source_family"):
            if not e.get(field):
                continue
            key = (e["actor"], e["target"], e["sign"], field, e[field])
            if key in seen:
                parent[find(i)] = find(seen[key])
            seen[key] = i
    groups = defaultdict(list)
    for i, e in enumerate(events):
        groups[find(i)].append(e)
    result = []
    for group in groups.values():
        item = dict(group[-1])
        item["supporting_evidence_ids"] = sorted({e["evidence_id"] for e in group if e.get("evidence_id")})
        item["deduplicated_records"] = len(group)
        item["first_observed_date"] = group[0].get("event_date")
        item["last_observed_date"] = group[-1].get("event_date")
        result.append(item)
    return result


def personality_features(a, b):
    out = {}
    sims = []
    for trait in "EAOCN":
        x, y = a.get(trait), b.get(trait)
        value = exp(-abs(x-y)) if finite(x) and finite(y) else None
        out["similarity_"+trait] = value
        if trait in "EAO" and value is not None:
            sims.append(value)
    out["personality_similarity_eao"] = sum(sims)/len(sims) if sims else None
    out["personality_traits_observed"] = len(sims)
    out["ego_extraversion"] = a.get("E") if finite(a.get("E")) else None
    out["alter_agreeableness"] = b.get("A") if finite(b.get("A")) else None
    return out


def graph_features(events, a, b, holdout_pair=True, as_of="9999-12-31", excluded_families=()):
    """Directed signed personal graph; masked BEFORE degrees, paths, or motifs.

    Positive neighbor overlap uses the undirected positive skeleton only. All
    sixteen signed two-step motifs retain their directed interpretation.
    """
    out = {s: defaultdict(set) for s in "+-"}
    inc = {s: defaultdict(set) for s in "+-"}
    blocked = set(excluded_families)
    for e in accepted_events(events, as_of):
        u, v = e["actor"], e["target"]
        if e.get("source_family") in blocked or (holdout_pair and {u, v} == {a, b}):
            continue
        s = "+" if e["sign"] == "positive" else "-"
        out[s][u].add(v)
        inc[s][v].add(u)
    na, nb = out["+"][a] | inc["+"][a], out["+"][b] | inc["+"][b]
    common = na & nb
    queue, visited, distance = deque([(a, 0)]), {a}, None
    while queue:
        u, depth = queue.popleft()
        if u == b:
            distance = depth
            break
        for v in sorted(out["+"][u] - visited):
            visited.add(v)
            queue.append((v, depth+1))
    motifs = {}
    for da, ma in (("out", out), ("in", inc)):
        for db, mb in (("out", out), ("in", inc)):
            for sa in "+-":
                for sb in "+-":
                    motifs[f"{da}_{db}_{sa}{sb}"] = len(ma[sa][a] & mb[sb][b])
    features = dict(positive_shortest_path=distance, positive_common_neighbors=len(common),
                    positive_neighbor_jaccard=len(common)/len(na | nb) if na | nb else None,
                    positive_resource_allocation=sum(1/len(out["+"][c] | inc["+"][c]) for c in common),
                    positive_intermediaries=sorted(common), signed_motifs=motifs)
    for sign, label in (("+", "positive"), ("-", "negative")):
        for who, u in (("ego", a), ("alter", b)):
            features[f"{who}_{label}_outdegree"] = len(out[sign][u])
            features[f"{who}_{label}_indegree"] = len(inc[sign][u])
    return features


def eligible_join(introduced, joined, as_of, window_days=30, service_end=None):
    start, cutoff, join = parse_date(introduced), parse_date(as_of), parse_date(joined)
    if not start or not cutoff or start > cutoff:
        return None
    end = start + timedelta(days=window_days)
    service = parse_date(service_end)
    # Require a complete common exposure window, including for early successes.
    if end > cutoff or (service and end >= service):
        return None
    return int(join is not None and start <= join <= end)


def residual_support(observed, expected):
    n = len(expected)
    if observed < 0 or observed > n or any(not 0 <= p <= 1 for p in expected):
        raise ValueError("Invalid successes or expected probabilities")
    mu = sum(expected)
    variance = sum(p*(1-p) for p in expected)
    return dict(work_observed=observed, work_expected=mu, work_opportunities=n,
                work_residual_rate=(observed-mu)/n if n else None,
                work_residual_standardized=(observed-mu)/sqrt(variance) if variance > 0 else None)


def relationship_summary(a, b, events, features):
    """Transparent exploratory priority, NOT a fitted link model or probability.

    Context fields never enter this function. In the real runner, indirect
    personality and work inputs are compared with matched political strata.
    Graph motifs have no assumed sign coefficient. Negative work is not hostility.
    """
    own = collapse_episodes([e for e in events if e["actor"] == a and e["target"] == b
                             and e.get("category") in PERSONAL and e.get("review_status") in REVIEWED
                             and e.get("attribution") in ATTRIBUTED])
    positive = [e for e in own if e["sign"] == "positive"]
    negative = [e for e in own if e["sign"] == "negative"]
    sim = features.get("personality_similarity_excess", features.get("personality_similarity_eao"))
    sim = max(0.0, sim) if finite(sim) else 0.0
    graph = max(0.0, features.get("positive_resource_allocation") or 0.0)
    work = max(0.0, features.get("work_residual_rate") or 0.0)
    nwork = features.get("work_opportunities") or 0
    work = work * nwork/(nwork+20)
    components = dict(personality=0.15*sim, personal_network=0.3*tanh(graph),
                      distinctive_work=0.3*work, direct_episodes=float(len(positive)))
    indirect_channels = sum([sim > 0, graph > 0, work > 0])
    evidence = "contested_or_mixed" if positive and negative else (
        "corroborated_provisional" if max(len(positive),len(negative)) >= 2 else
        "direct_provisional" if own else "none")
    return dict(actor=a, target=b,
                affinity="documented_provisional" if positive else "indirect_candidate" if indirect_channels >= 2 else "unknown",
                antagonism="documented_provisional" if negative else "unknown",
                affinity_probability=None, antagonism_probability=None,
                affinity_candidate_score=round(sum(components.values()), 8),
                antagonism_candidate_score=float(len(negative)),
                score_components=components, evidence_status=evidence,
                positive_episodes=len(positive), negative_episodes=len(negative),
                evidence_ids=sorted({i for e in own for i in e["supporting_evidence_ids"]}),
                mutual_friendship=False, model_status="exploratory_unfitted",
                source_review="human" if own and all(e["review_status"] == "human_reviewed" for e in own) else
                              "assistant" if own else "none")
