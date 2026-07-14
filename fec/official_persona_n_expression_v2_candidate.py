# -*- coding: utf-8 -*-
import os as _o, sys as _s
_s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
from paths import ROOT as MB_ROOT

"""Exploratory official-facing negative-emotional-reactivity score.

This v2 engineering candidate is intentionally narrower than Big Five Neuroticism.  It reuses the
locked v1 subject/target/tone decomposition, combines three research-consistent observable aspects
with equal weights, and applies leave-member-out control adjustment.  Because v1 findings informed
the design and the same corpus is reused, this can establish engineering readiness but not a fresh
confirmatory validation claim.
"""

import argparse
import collections
import csv
import hashlib
import json
import math

import numpy as np

import official_persona_n_target_tone_candidate as v1
from moneyball_core import dump_atomic, party as party_map

_s.stdout.reconfigure(encoding="utf-8", errors="replace")

B = MB_ROOT
OUT = _o.path.join(B, "official_persona_n_expression_v2.json.candidate")
PROTOCOL = _o.path.join(B, "big5_official_persona_n_expression_v2_protocol.md")
V1_ARTIFACT = _o.path.join(B, "official_persona_n_target_tone_v1.json.candidate")
VERSION = "official-persona-n-expression-v2-2026-07-13"
ASPECTS = ("residual_tone_level", "disproportionate_intensity", "emotional_volatility")
FOLDS = 5
MIN_FULL_SENTENCES = 100
MIN_FULL_EPISODES = 5
MIN_HALF_SENTENCES = 50
MIN_HALF_EPISODES = 5


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def fold_of(member):
    return int.from_bytes(hashlib.sha256(("N-EXPR-V2\0" + member).encode("utf-8")).digest()[:4], "big") % FOLDS


def corr_maps(left, right):
    names = sorted(set(left) & set(right))
    x = np.asarray([left[n] for n in names], float)
    y = np.asarray([right[n] for n in names], float)
    good = np.isfinite(x) & np.isfinite(y)
    x, y = x[good], y[good]
    if len(x) < 5 or float(x.std()) <= 1e-12 or float(y.std()) <= 1e-12:
        return None, int(len(x))
    return float(np.corrcoef(x, y)[0, 1]), int(len(x))


def spearman_brown(r):
    return 2.0 * r / (1.0 + r) if r is not None and r > -1.0 else None


def raw_aspects(episodes, min_sentences, min_episodes):
    rows = {}
    for member, eps in v1.group_episodes(episodes).items():
        n = sum(ep["n"] for ep in eps)
        if n < min_sentences or len(eps) < min_episodes:
            continue
        episode_tone = [ep["residual"]["overall_tone"] / ep["n"] for ep in eps if ep["n"] >= 3]
        if len(episode_tone) < 5:
            continue
        rows[member] = {
            "sentences": n,
            "words": sum(ep["words"] for ep in eps),
            "episodes": len(eps),
            "date_min": min((ep["date"] for ep in eps if ep["date"]), default=None),
            "date_max": max((ep["date"] for ep in eps if ep["date"]), default=None),
            "subject_severity": sum(ep["severity_sum"] for ep in eps) / n,
            "attributed_share": sum(ep["attributed"] for ep in eps) / n,
            "aspects_raw": {
                # Signed means are used.  The v1 positive-tail transformation was repeatable but
                # reintroduced subject-severity contamination at member level.
                "residual_tone_level": sum(ep["residual"]["overall_tone"] for ep in eps) / n * 100.0,
                "disproportionate_intensity": sum(ep["residual"]["dramatic"] for ep in eps) / n * 100.0,
                "emotional_volatility": float(np.std(episode_tone, ddof=1)) * 100.0,
            },
        }
    return rows


def metadata(rows):
    roster = json.load(open(_o.path.join(B, "congestion.json"), encoding="utf-8"))
    chamber = {row["member"]: row["chamber"] for row in roster}
    p0 = party_map()
    party = {m: 1.0 if p0.get(m) == "R" else 0.0 for m in rows if p0.get(m) in ("D", "R")}
    gender = {}
    with open(_o.path.join(B, "fec", "legislators.csv"), encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            name = row.get("full_name")
            if name in rows and row.get("gender") in ("F", "M"):
                gender[name] = 1.0 if row["gender"] == "F" else 0.0
    role_doc = json.load(open(_o.path.join(B, "formal_visibility_roles.json"), encoding="utf-8"))
    role = {m: 1.0 if m in role_doc.get("members", {}) else 0.0 for m in rows}
    senate = {m: 1.0 if chamber.get(m) == "Senate" else 0.0 for m in rows if chamber.get(m) in ("House", "Senate")}
    return chamber, party, gender, role, senate


def controls_for(rows, metadata_rows):
    _chamber, party, gender, role, senate = metadata_rows
    controls = {}
    for member, row in rows.items():
        if member not in party or member not in gender or member not in role or member not in senate:
            continue
        controls[member] = np.asarray([
            1.0,
            party[member],
            gender[member],
            role[member],
            math.log1p(row["sentences"]),
            row["subject_severity"],
            senate[member],
        ], float)
    return controls


def crossfit_residual(values, controls):
    names = sorted(set(values) & set(controls))
    out = {}
    for fold in range(FOLDS):
        train = [m for m in names if fold_of(m) != fold]
        test = [m for m in names if fold_of(m) == fold]
        if len(train) < 20 or not test:
            continue
        X = np.asarray([controls[m] for m in train], float)
        y = np.asarray([values[m] for m in train], float)
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
        for member in test:
            out[member] = float(values[member] - controls[member] @ beta)
    return out


def chamber_z(values, chamber):
    out = {}
    for ch in ("House", "Senate"):
        names = [m for m in values if chamber.get(m) == ch and math.isfinite(float(values[m]))]
        if not names:
            continue
        arr = np.asarray([values[m] for m in names], float)
        sd = float(arr.std(ddof=1)) if len(arr) > 1 else 1.0
        if sd <= 1e-12:
            sd = 1.0
        mean = float(arr.mean())
        out.update({m: (float(values[m]) - mean) / sd for m in names})
    return out


def make_bundle(episodes, min_sentences, min_episodes):
    rows = raw_aspects(episodes, min_sentences, min_episodes)
    meta = metadata(rows)
    chamber = meta[0]
    controls = controls_for(rows, meta)
    adjusted = {}
    raw_z = {}
    for aspect in ASPECTS:
        values = {m: row["aspects_raw"][aspect] for m, row in rows.items()}
        raw_z[aspect] = chamber_z(values, chamber)
        adjusted[aspect] = chamber_z(crossfit_residual(values, controls), chamber)
    names = sorted(set.intersection(*(set(adjusted[a]) for a in ASPECTS))) if adjusted else []
    score0 = {m: float(np.mean([adjusted[a][m] for a in ASPECTS])) for m in names}
    score = chamber_z(score0, chamber)
    raw_names = sorted(set.intersection(*(set(raw_z[a]) for a in ASPECTS))) if raw_z else []
    raw_score = chamber_z({m: float(np.mean([raw_z[a][m] for a in ASPECTS])) for m in raw_names}, chamber)
    return {"rows": rows, "metadata": meta, "controls": controls, "adjusted_aspects": adjusted,
            "raw_aspects_z": raw_z, "score": score, "raw_score": raw_score}


def split_reliability(episodes):
    result = {"score": [], **{aspect: [] for aspect in ASPECTS}}
    for salt in v1.SPLIT_SALTS:
        halves = ([ep for ep in episodes if v1.stable_half(ep, salt) == 0],
                  [ep for ep in episodes if v1.stable_half(ep, salt) == 1])
        bundles = [make_bundle(h, MIN_HALF_SENTENCES, MIN_HALF_EPISODES) for h in halves]
        r, n = corr_maps(bundles[0]["score"], bundles[1]["score"])
        result["score"].append({"salt": salt, "r": r, "spearman_brown": spearman_brown(r), "n": n})
        for aspect in ASPECTS:
            r, n = corr_maps(bundles[0]["adjusted_aspects"][aspect], bundles[1]["adjusted_aspects"][aspect])
            result[aspect].append({"salt": salt, "r": r, "spearman_brown": spearman_brown(r), "n": n})
    summary = {}
    for name, splits in result.items():
        vals = [x["spearman_brown"] for x in splits if x["spearman_brown"] is not None]
        summary[name] = {
            "splits": splits,
            "median_spearman_brown": float(np.median(vals)) if vals else None,
            "splits_at_or_above_0_50": sum(v >= 0.50 for v in vals),
        }
    return summary


def chronological(episodes):
    early, late = [], []
    for _member, eps in v1.group_episodes(episodes).items():
        ordered = sorted(eps, key=lambda ep: (ep["date"], ep["package"]))
        mid = len(ordered) // 2
        early.extend(ordered[:mid]); late.extend(ordered[mid:])
    a = make_bundle(early, MIN_HALF_SENTENCES, MIN_HALF_EPISODES)
    b = make_bundle(late, MIN_HALF_SENTENCES, MIN_HALF_EPISODES)
    out = {}
    r, n = corr_maps(a["score"], b["score"]); out["score"] = {"r": r, "n": n}
    for aspect in ASPECTS:
        r, n = corr_maps(a["adjusted_aspects"][aspect], b["adjusted_aspects"][aspect])
        out[aspect] = {"r": r, "n": n}
    return out


def diagnostics(bundle):
    rows = bundle["rows"]
    chamber, party, gender, role, senate = bundle["metadata"]
    controls = {
        "party": party,
        "gender": gender,
        "current_formal_leadership": role,
        "log_sentences": {m: math.log1p(row["sentences"]) for m, row in rows.items()},
        "subject_severity": {m: row["subject_severity"] for m, row in rows.items()},
        "chamber_senate": senate,
    }
    confounds = {}
    for name, values in {"score": bundle["score"], **bundle["adjusted_aspects"]}.items():
        confounds[name] = {}
        for control_name, control in controls.items():
            r, n = corr_maps(values, control)
            confounds[name][control_name] = {"r": r, "n": n}
    coherence = {}
    for i, left in enumerate(ASPECTS):
        for right in ASPECTS[i + 1:]:
            r, n = corr_maps(bundle["adjusted_aspects"][left], bundle["adjusted_aspects"][right])
            coherence[left + "__" + right] = {"r": r, "n": n}
    old_n = json.load(open(_o.path.join(B, "affective_n.json"), encoding="utf-8")).get("members", {})
    old_r, old_n_count = corr_maps(bundle["score"], old_n)
    return {"confounds": confounds, "aspect_coherence": coherence,
            "old_affective_n_nonvalidation": {"r": old_r, "n": old_n_count}}


def finite_round(value, digits=6):
    if value is None:
        return None
    value = float(value)
    return round(value, digits) if math.isfinite(value) else None


def self_test(verbose=True):
    rng = np.random.default_rng(20260713)
    n = 250
    names = ["synthetic-%03d" % i for i in range(n)]
    nuisance = rng.normal(size=n)
    truth = rng.normal(size=n)
    controls = {m: np.asarray([1.0, nuisance[i]], float) for i, m in enumerate(names)}
    values = {m: float(truth[i] + 2.0 * nuisance[i]) for i, m in enumerate(names)}
    residual = crossfit_residual(values, controls)
    nuisance_map = {m: float(nuisance[i]) for i, m in enumerate(names)}
    truth_map = {m: float(truth[i]) for i, m in enumerate(names)}
    nuisance_r, _ = corr_maps(residual, nuisance_map)
    truth_r, _ = corr_maps(residual, truth_map)
    checks = {
        "fold_deterministic": fold_of("Tina Smith") == fold_of("Tina Smith"),
        "fold_range": all(0 <= fold_of(m) < FOLDS for m in names),
        "crossfit_removes_synthetic_nuisance": nuisance_r is not None and abs(nuisance_r) <= 0.10,
        "crossfit_preserves_synthetic_signal": truth_r is not None and truth_r >= 0.90,
        "v1_safeguards": v1.synthetic_battery(verbose=False),
        "v1_artifact_pinned": _o.path.exists(V1_ARTIFACT) and sha256(V1_ARTIFACT).lower() ==
                              "a6cdd20a50858aba11cb16e366931720aba42f31f2fbda3b2256d9731c72f46f",
    }
    if verbose:
        for name, ok in checks.items():
            print("%-42s %s" % (name, "PASS" if ok else "FAIL"))
        print("SELF-TEST: %s (%d/%d)" % ("PASS" if all(checks.values()) else "FAIL", sum(checks.values()), len(checks)))
    return all(checks)


def evaluate():
    untargeted, targeted, sentence_n = v1.build_context()
    episodes, topic_adjustment = v1.build_episodes(untargeted, targeted)
    bundle = make_bundle(episodes, MIN_FULL_SENTENCES, MIN_FULL_EPISODES)
    reliability = split_reliability(episodes)
    chrono = chronological(episodes)
    diag = diagnostics(bundle)
    score_confounds = [abs(x["r"]) for x in diag["confounds"]["score"].values() if x["r"] is not None]
    coherence = [x["r"] for x in diag["aspect_coherence"].values() if x["r"] is not None]
    aspect_reliable = sum((reliability[a]["median_spearman_brown"] is not None and
                           reliability[a]["median_spearman_brown"] >= 0.50) for a in ASPECTS)
    bars = {
        "coverage_at_least_200": len(bundle["score"]) >= 200,
        "score_median_split_half_sb_at_least_0_60": reliability["score"]["median_spearman_brown"] is not None and reliability["score"]["median_spearman_brown"] >= 0.60,
        "score_four_of_five_splits_at_least_0_50": reliability["score"]["splits_at_or_above_0_50"] >= 4,
        "at_least_two_aspects_median_sb_at_least_0_50": aspect_reliable >= 2,
        "chronological_score_r_at_least_0_30": chrono["score"]["r"] is not None and chrono["score"]["r"] >= 0.30,
        "aspect_pair_correlations_between_0_10_and_0_80": len(coherence) == 3 and all(0.10 <= r <= 0.80 for r in coherence),
        "max_abs_crossfit_confound_r_at_most_0_15": bool(score_confounds) and max(score_confounds) <= 0.15,
        "v1_sentence_subject_adjustment_pass": (topic_adjustment["residual_r"] is not None and
                                                  abs(topic_adjustment["residual_r"]) <= 0.10 and
                                                  abs(topic_adjustment["residual_r"]) <= max(0.01, 0.5 * abs(topic_adjustment["raw_r"]))),
    }
    ready = all(bars.values())
    members = {}
    for member in sorted(bundle["score"]):
        row = bundle["rows"][member]
        members[member] = {
            "N_official_expression": finite_round(bundle["score"][member]),
            "raw_unadjusted_score_z": finite_round(bundle["raw_score"].get(member)),
            "aspects": {
                aspect: {
                    "raw": finite_round(row["aspects_raw"][aspect]),
                    "crossfit_adjusted_within_chamber_z": finite_round(bundle["adjusted_aspects"][aspect].get(member)),
                } for aspect in ASPECTS
            },
            "coverage": {k: row[k] for k in ("sentences", "words", "episodes", "date_min", "date_max")},
            "subject_severity": finite_round(row["subject_severity"]),
            "attributed_share": finite_round(row["attributed_share"]),
        }
    return {
        "schema": "official-persona-n-expression-v2-candidate",
        "version": VERSION,
        "status": "CANDIDATE_CONSUMED_BY_NOTHING_AWAITING_USER_REVIEW",
        "construct_label": "Official-facing negative emotional reactivity (N-expression; not holistic Neuroticism)",
        "claim_status": "EXPLORATORY_ENGINEERING_RESULT_SAME_CORPUS_AS_V1_NOT_FRESH_CONFIRMATORY_VALIDATION",
        "formula": "equal mean of cross-fitted, control-adjusted, within-chamber z scores for residual tone level, disproportionate intensity, and emotional volatility; final within-chamber z",
        "controls": ["party", "gender", "current formal leadership", "log sentence coverage", "subject severity", "chamber"],
        "score_direction": "higher = more repeated negative emotional tone, dramatic amplification, and episode-to-episode affective variability beyond comparable contexts",
        "input_fingerprints": {"v1_candidate_sha256": sha256(V1_ARTIFACT), **v1.current_pins()},
        "corpus": {"sentences": sentence_n, "episodes": len(episodes), "scored_members": len(members)},
        "engineering_ready": ready,
        "engineering_bars": bars,
        "reliability": reliability,
        "chronological_stability": chrono,
        "diagnostics": diag,
        "v1_topic_adjustment": topic_adjustment,
        "future_validation_required": "A temporally new interview holdout or independent criterion is required before any validated-N claim.",
        "members": members,
    }


def print_summary(doc):
    print("corpus: %d sentences | %d episodes | %d scored members" % (
        doc["corpus"]["sentences"], doc["corpus"]["episodes"], doc["corpus"]["scored_members"]))
    for name in ("score",) + ASPECTS:
        rel = doc["reliability"][name]
        chrono = doc["chronological_stability"][name]
        print("%-29s SB=%6s split=%d/5 chrono=%6s n=%d" % (
            name, str(finite_round(rel["median_spearman_brown"], 3)),
            rel["splits_at_or_above_0_50"], str(finite_round(chrono["r"], 3)), chrono["n"]))
    print("coherence:", " ".join("%s=%s" % (k, finite_round(v["r"], 3)) for k, v in doc["diagnostics"]["aspect_coherence"].items()))
    print("score confounds:", " ".join("%s=%s" % (k, finite_round(v["r"], 3)) for k, v in doc["diagnostics"]["confounds"]["score"].items()))
    for name, ok in doc["engineering_bars"].items():
        print("BAR %-52s %s" % (name, "PASS" if ok else "MISS"))
    print("ENGINEERING RESULT:", "READY-PROVISIONAL" if doc["engineering_ready"] else "NOT READY")


def verify():
    if not _o.path.exists(OUT):
        raise SystemExit("candidate absent")
    doc = json.load(open(OUT, encoding="utf-8"))
    checks = {
        "schema": doc.get("schema") == "official-persona-n-expression-v2-candidate",
        "candidate_status": doc.get("status") == "CANDIDATE_CONSUMED_BY_NOTHING_AWAITING_USER_REVIEW",
        "narrow_construct_label": "not holistic Neuroticism" in doc.get("construct_label", ""),
        "v1_pin": doc.get("input_fingerprints", {}).get("v1_candidate_sha256", "").lower() == sha256(V1_ARTIFACT).lower(),
        "source_pins": all(doc.get("input_fingerprints", {}).get(k) == v for k, v in v1.current_pins().items()),
        "members": len(doc.get("members", {})) >= 200,
        "three_aspects": all(set(row.get("aspects", {})) == set(ASPECTS) for row in doc.get("members", {}).values()),
    }
    for name, ok in checks.items():
        print("%-30s %s" % (name, "PASS" if ok else "FAIL"))
    if not all(checks.values()):
        raise SystemExit(1)
    print("CANDIDATE QA: PASS")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        if not self_test():
            raise SystemExit(1)
        return
    if args.verify:
        verify(); return
    if not args.build:
        print("protocol:", "PRESENT" if _o.path.exists(PROTOCOL) else "ABSENT")
        print("v1 artifact pin:", "MATCH" if _o.path.exists(V1_ARTIFACT) and sha256(V1_ARTIFACT).lower() ==
              "a6cdd20a50858aba11cb16e366931720aba42f31f2fbda3b2256d9731c72f46f" else "DRIFT")
        print("candidate:", "PRESENT" if _o.path.exists(OUT) else "ABSENT")
        return
    if not _o.path.exists(PROTOCOL):
        raise SystemExit("BUILD REFUSED: protocol absent")
    if not self_test():
        raise SystemExit("BUILD REFUSED: self-test failure")
    doc = evaluate()
    dump_atomic(doc, OUT, indent=1)
    print_summary(doc)
    print("candidate written:", OUT)


if __name__ == "__main__":
    main()
