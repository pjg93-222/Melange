# -*- coding: utf-8 -*-
"""Render accepted Big Five weights; explicitly audit corrections without refitting.

Routine builds never consult gold values or select weights. The 2026-07 accepted
specification is a versioned source resource. --audit evaluates those frozen,
historically criterion-fitted weights descriptively; it is NOT new OOF evidence.
Legacy fitting helpers remain for archived, separately guarded research scripts.
"""
from __future__ import annotations

import itertools
import argparse
import copy
import hashlib
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from members.b5_external_gold_validate import map_gold, name_key, one_sided_permutation_p
from moneyball_core import dump_atomic
from paths import ROOT


OUT = os.path.join(ROOT, "data", "stance", "big5_gold_anchored.json")
TRAITS = ("O", "C", "E", "A", "N")
PANEL_NAMES = ("senate_insiders", "academic_experts")
MIN_PANEL_N = 30
MIN_PANEL_R = .20
MAX_P = .10
GRID_STEP = .10
SPEC_PATH = Path(__file__).resolve().parents[2] / "source_data/big5/frozen_accepted_spec.json"
INPUT_FILES = (
    "data/engine/roster.json", "data/members/big5_blue_validated.json",
    "data/members/big5_llm_opus.json", "behavioral_dispositions.json",
    "data/members/behavioral_roles_v2_candidate.json", "communication_style.json",
    "data/stance/big5_senate_expert_gold.json",
)


def frozen_spec():
    raw = SPEC_PATH.read_bytes()
    spec = json.loads(raw)
    if spec.get("schema") != "big5-frozen-accepted-spec-v1" or set(spec.get("traits", {})) != set(TRAITS):
        raise ValueError("invalid frozen Big Five specification")
    for trait, row in spec["traits"].items():
        weights = row["selected_weights"]
        if (not weights or any(not math.isfinite(float(w)) or w < 0 for w in weights.values())
                or not math.isclose(sum(weights.values()), 1.0, abs_tol=1e-12)
                or not set(row["required_channels"]).issubset(weights)):
            raise ValueError("invalid frozen weights/required channels: " + trait)
    return spec, hashlib.sha256(raw).hexdigest()


def input_hashes():
    return {name: hashlib.sha256(Path(ROOT, name).read_bytes()).hexdigest() for name in INPUT_FILES}


def code_hashes():
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ("b5_gold_multitrait_validate.py", "b5_external_gold_validate.py",
                         "b5_gold_identity.py", "b5_gold_identity_registry.py")}


def complete_diagnostic(document):
    for trait in TRAITS:
        record = document.get("traits", {}).get(trait) or {}
        value = record.get("validation") or {}
        if (value.get("evaluation_kind") != "fixed_accepted_weight_correction_audit" or
                value.get("diagnostic_only") is not True or value.get("predictions_are_out_of_fold") is not False or
                set(value.get("panels", {})) != set(PANEL_NAMES)):
            return False
        for panel in value["panels"].values():
            required = {"n", "r", "member_names", "permutation_p_one_sided", "max_abs_heterotrait",
                        "diagonal_dominant", "discrimination_n", "gold_row"}
            names = panel.get("member_names")
            n = panel.get("n")
            if (not required.issubset(panel) or not isinstance(n, int) or isinstance(n, bool) or n < 0 or
                    not isinstance(names, list) or not all(isinstance(name, str) for name in names) or
                    len(names) != n or len(set(names)) != n or not set(names).issubset(record.get("members", {})) or
                    not isinstance(panel.get("diagonal_dominant"), bool)):
                return False
            for key in ("r", "permutation_p_one_sided", "max_abs_heterotrait"):
                number = panel[key]
                if number is not None and (not isinstance(number, (int, float)) or isinstance(number, bool) or
                                           not math.isfinite(number) or not (-1 if key == "r" else 0) <= number <= 1):
                    return False
    return True


def eligible_members(channels, required, roster):
    """Identical primary-channel eligibility for scoring and panel evaluation."""
    return sorted(name for name in roster if all(
        name in channels.get(channel, {}) and math.isfinite(float(channels[channel][name]))
        for channel in required))


def fixed_scores(channels, weights, required, roster):
    members = eligible_members(channels, required, roster)
    selected = {name: channels[name] for name in weights}
    return score_members(selected, tuple(weights.values()), members)


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
        return json.load(handle)


def corr(x, y):
    pairs = [(float(a), float(b)) for a, b in zip(x, y)
             if a is not None and b is not None and math.isfinite(float(a)) and math.isfinite(float(b))]
    if len(pairs) < 5:
        return None, len(pairs)
    a, b = map(np.asarray, zip(*pairs))
    if a.std() == 0 or b.std() == 0:
        return None, len(pairs)
    return float(np.corrcoef(a, b)[0, 1]), len(pairs)


def zmap(values):
    if not values:
        return {}
    names = sorted(values)
    vector = np.asarray([float(values[name]) for name in names])
    sd = float(vector.std(ddof=1)) if len(vector) > 1 else 1.0
    sd = sd or 1.0
    mean = float(vector.mean())
    return {name: (float(values[name]) - mean) / sd for name in names}


def percentiles(values):
    import bisect
    ordered = sorted(values.values())
    denominator = max(1, len(ordered) - 1)
    return {name: round(bisect.bisect_left(ordered, value) / denominator, 3)
            for name, value in values.items()}


def simplex_weights(channel_names, minima=None):
    minima = minima or {}
    units = int(round(1 / GRID_STEP))
    minimum_units = [int(round(minima.get(name, 0) / GRID_STEP)) for name in channel_names]
    remaining = units - sum(minimum_units)
    if remaining < 0:
        return []
    out = []
    for cuts in itertools.combinations_with_replacement(range(len(channel_names)), remaining):
        counts = list(minimum_units)
        for index in cuts:
            counts[index] += 1
        out.append(tuple(round(count / units, 6) for count in counts))
    return sorted(set(out))


def gold_value(row, trait):
    value = row.get("ES" if trait == "N" else trait)
    if value is None:
        return None
    return -float(value) if trait == "N" else float(value)


def averaged_gold(panels, trait):
    values = {}
    for name in sorted(set().union(*(set(panel) for panel in panels.values()))):
        seen = [gold_value(panel[name], trait) for panel in panels.values()
                if name in panel and gold_value(panel[name], trait) is not None]
        if seen:
            values[name] = float(np.mean(seen))
    return values


def score_members(channels, weights, members):
    names = list(channels)
    return {member: sum(weights[i] * channels[name].get(member, 0.0)
                        for i, name in enumerate(names))
            for member in members}


def choose_weights(channels, target, training, minima=None):
    names = list(channels)
    candidates = simplex_weights(names, minima)
    best = None
    for weights in candidates:
        predicted = score_members(channels, weights, training)
        r, n = corr([predicted[name] for name in training], [target[name] for name in training])
        if r is None:
            continue
        # Stable deterministic tie-break: prefer higher validity, then more balanced, then lexical order.
        balance = -sum(weight * weight for weight in weights)
        key = (round(r, 12), round(balance, 12), tuple(-weight for weight in weights))
        if best is None or key > best[0]:
            best = (key, weights, r, n)
    if best is None:
        raise ValueError("no valid gold-weight solution")
    return best[1], best[2], best[3]


def oof_variant(channels, panels, trait, minima=None):
    target = averaged_gold(panels, trait)
    eligible = sorted(target)
    predictions = {}
    fold_weights = []
    for held_out in eligible:
        training = [name for name in eligible if name != held_out]
        weights, _, _ = choose_weights(channels, target, training, minima)
        predictions[held_out] = score_members(channels, weights, [held_out])[held_out]
        fold_weights.append(weights)
    final_weights, fit_r, fit_n = choose_weights(channels, target, eligible, minima)
    panel_results = {}
    for panel_index, panel_name in enumerate(PANEL_NAMES):
        panel = panels[panel_name]
        members = [name for name in panel if name in predictions and gold_value(panel[name], trait) is not None]
        same, n = corr([predictions[name] for name in members],
                       [gold_value(panel[name], trait) for name in members])
        row = {}
        for other in TRAITS:
            values = [gold_value(panel[name], other) for name in members]
            row[other] = corr([predictions[name] for name in members], values)[0]
        hetero = max(abs(value) for key, value in row.items() if key != trait and value is not None)
        if trait == "N":
            # N is the reverse pole of the appendix's ES column; row['N'] is already direction-correct.
            pass
        p = one_sided_permutation_p(
            [predictions[name] for name in members],
            [gold_value(panel[name], trait) for name in members],
            20260715 + panel_index + 17 * TRAITS.index(trait),
        )[1]
        panel_results[panel_name] = {
            "r": same, "n": n, "permutation_p_one_sided": p,
            "gold_row": row, "max_abs_heterotrait": hetero,
            "diagonal_dominant": same is not None and same > hetero,
        }
    worst = min(row["r"] if row["r"] is not None else -1 for row in panel_results.values())
    mean_r = float(np.mean([row["r"] for row in panel_results.values() if row["r"] is not None]))
    return {
        "channels": list(channels),
        "selected_weights": {name: final_weights[i] for i, name in enumerate(channels)},
        "full_gold_fit_r": fit_r, "full_gold_fit_n": fit_n,
        "fold_weight_mode": {name: Counter(fold_weights).most_common(1)[0][0][i]
                             for i, name in enumerate(channels)},
        "panels": panel_results, "worst_panel_r": worst, "mean_panel_r": mean_r,
        "predictions_are_out_of_fold": True,
    }, predictions


def raw_channels(roster=None):
    blue = load("data/members/big5_blue_validated.json").get("traits") or {}
    pink = load("data/members/big5_llm_opus.json").get("traits") or {}
    dispositions = load("behavioral_dispositions.json").get("members") or {}
    roles = load("data/members/behavioral_roles_v2_candidate.json").get("members") or {}
    style = load("communication_style.json").get("members") or {}

    def blue_trait(key):
        return {name: row[key] for name, row in blue.items() if row.get(key) is not None}

    def pink_trait(key, reverse=False):
        out = {}
        for name, row in pink.items():
            value = (row.get("raw_z") or {}).get(key)
            if row.get("n_chunks", 0) > 0 and value is not None:
                out[name] = -float(value) if reverse else float(value)
        return out

    def disposition(key):
        return {name: row[key] for name, row in dispositions.items() if row.get(key) is not None}

    def role(key):
        return {name: row[key] for name, row in roles.items() if row.get(key) is not None}

    def exposure():
        return {name: row["public_exposure"]["role_adjusted_visibility_z"]
                for name, row in style.items() if (row.get("public_exposure") or {}).get("role_adjusted_visibility_z") is not None}

    raw = {
        "O": {"blue_text_o": blue_trait("O"), "pink_observer_o": pink_trait("O"),
              "legislative_breadth": disposition("breadth_z")},
        "C": {"blue_text_c": blue_trait("C"), "pink_observer_c": pink_trait("C"),
              "legislative_follow_through": disposition("diligence_z")},
        "E": {"blue_visibility_calibrated_e": blue_trait("E"), "pink_observer_e": pink_trait("E"),
              "interaction_dominance": role("dominance_v2"), "role_adjusted_visibility": exposure()},
        "A": {"blue_low_antagonism_a": blue_trait("A"), "pink_observer_a": pink_trait("A"),
              "cross_party_cooperation": disposition("cooperation_z")},
        "N": {"affective_content_n": blue_trait("N"), "pink_observer_n": pink_trait("ES", reverse=True),
              "behavioral_reactivity": disposition("reactivity_z")},
    }
    # Current membership is applied BEFORE channel standardization, so departed
    # members cannot affect means, scales, or the final percentile population.
    return {trait: {name: zmap({member: value for member, value in values.items()
                               if (roster is None or member in roster) and math.isfinite(float(value))})
                    for name, values in channels.items()}
            for trait, channels in raw.items()}


def variants_for(trait, channels, panels):
    names = list(channels)
    baseline_names = names[:2]
    primary_minima = {name: .10 for name in baseline_names}
    baseline, baseline_predictions = oof_variant(
        {name: channels[name] for name in baseline_names}, panels, trait, primary_minima)
    extended, extended_predictions = oof_variant(channels, panels, trait, primary_minima)
    variants = {"blue_pink_baseline": baseline, "all_channels": extended}
    predictions = {"blue_pink_baseline": baseline_predictions, "all_channels": extended_predictions}
    if trait == "E":
        constrained, constrained_predictions = oof_variant(
            channels, panels, trait,
            {**primary_minima, "interaction_dominance": .10, "role_adjusted_visibility": .10},
        )
        variants["all_channels_both_behavioral_min_10pct"] = constrained
        predictions["all_channels_both_behavioral_min_10pct"] = constrained_predictions
        # Prefer a both-channel E only if it keeps the worst-panel OOF validity within .02 of baseline.
        selected = ("all_channels_both_behavioral_min_10pct"
                    if constrained["worst_panel_r"] >= baseline["worst_panel_r"] - .02
                    else max(variants, key=lambda key: (variants[key]["worst_panel_r"], variants[key]["mean_panel_r"])))
    else:
        selected = max(variants, key=lambda key: (variants[key]["worst_panel_r"], variants[key]["mean_panel_r"]))
    return selected, variants, predictions[selected]


def evaluate_fixed(scores, panels, trait):
    """Descriptive correction audit; coefficients were historically gold-fitted."""
    results = {}
    for index, panel_name in enumerate(PANEL_NAMES):
        panel = panels[panel_name]
        names = sorted(name for name in panel if name in scores and gold_value(panel[name], trait) is not None)
        x = [scores[name] for name in names]
        y = [gold_value(panel[name], trait) for name in names]
        same, n = corr(x, y)
        # Compare all traits on the SAME people. Pairwise deletion can otherwise
        # manufacture diagonal dominance from different missing-label cohorts.
        complete = [name for name in names if all(gold_value(panel[name], other) is not None for other in TRAITS)]
        dx = [scores[name] for name in complete]
        row = {other: corr(dx, [gold_value(panel[name], other) for name in complete])[0] for other in TRAITS}
        discrimination_r = row[trait]
        hetero = max((abs(value) for key, value in row.items() if key != trait and value is not None), default=None)
        p = one_sided_permutation_p(x, y, 20261027 + index + 17 * TRAITS.index(trait))[1] if same is not None else None
        results[panel_name] = {
            "r": same, "n": n, "member_names": names,
            "excluded_missing_required_channels": sorted(set(panel) - set(scores)),
            "excluded_missing_gold_trait": sorted(name for name in panel if name in scores and gold_value(panel[name], trait) is None),
            "permutation_p_one_sided": p,
            "p_value_scope": "descriptive only; ignores historical fitting/selection, not confirmatory",
            "gold_row": row, "max_abs_heterotrait": hetero,
            "gold_row_n": {other: len(complete) for other in TRAITS},
            "discrimination_r": discrimination_r, "discrimination_n": len(complete),
            "discrimination_members": complete,
            "diagonal_dominant": discrimination_r is not None and hetero is not None and discrimination_r > hetero,
            "discrimination_margin": discrimination_r - hetero if discrimination_r is not None and hetero is not None else None,
        }
    return {"evaluation_kind": "fixed_accepted_weight_correction_audit", "diagnostic_only": True,
            "predictions_are_out_of_fold": False, "historical_gold_used_to_fit_weights": True,
            "panels": results}


def build(audit=False, previous=None):
    from members.b5_gold_identity import map_gold_with_receipt, roster_records, registry_sha256
    spec, spec_hash = frozen_spec()
    registry_hash = registry_sha256()
    code_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    dependencies = code_hashes()
    hashes = input_hashes()
    records = roster_records(load("data/engine/roster.json"))
    roster = {row["member"] for row in records}
    channels_by_trait = raw_channels(roster)
    panels = None
    identity = None
    if audit:
        gold = load("data/stance/big5_senate_expert_gold.json")
        if gold.get("schema") != "big5-senate-expert-gold-v1" or gold.get("status") != "FROZEN_EXTERNAL_GOLD":
            raise ValueError("invalid external gold")
        panels, _, identity = map_gold_with_receipt(gold, records)
    # Only carry an explicit correction audit if the exact inputs AND frozen
    # specification remain unchanged. Never relabel old numbers as current.
    previous = previous or {}
    reusable = (previous.get("inputs_sha256") == hashes and
                previous.get("design", {}).get("frozen_spec_sha256") == spec_hash and
                previous.get("design", {}).get("identity_registry_sha256") == registry_hash and
                previous.get("design", {}).get("score_code_sha256") == code_hash and
                previous.get("design", {}).get("code_dependencies_sha256") == dependencies and
                previous.get("validation_status") == "CURRENT_FIXED_DIAGNOSTIC" and complete_diagnostic(previous))
    if reusable and not audit:
        identity = previous.get("identity_audit")
    output_traits = {}
    for trait in TRAITS:
        accepted = spec["traits"][trait]
        channels = channels_by_trait[trait]
        weights = accepted["selected_weights"]
        raw = fixed_scores(channels, weights, accepted["required_channels"], roster)
        standardized = zmap(raw)
        pcts = percentiles(standardized)
        member_rows = {name: {trait: round(standardized[name], 6), "percentile": pcts[name]}
                       for name in sorted(standardized)}
        if audit:
            validation = evaluate_fixed(raw, panels, trait)
        elif reusable:
            validation = copy.deepcopy(previous["traits"][trait]["validation"])
        else:
            validation = {"evaluation_kind": "not_reaudited", "diagnostic_only": True,
                          "predictions_are_out_of_fold": False, "panels": {}}
        diagnostic_gates = {}
        for panel_name, row in validation["panels"].items():
            association = (row["n"] >= MIN_PANEL_N and row["r"] is not None and row["r"] >= MIN_PANEL_R and
                           row["permutation_p_one_sided"] is not None and row["permutation_p_one_sided"] < MAX_P)
            diagnostic_gates[panel_name] = {"association": association,
                                           "discriminant": association and row["diagonal_dominant"],
                                           "may_change_accepted_status": False}
        result = {
            "status": accepted["status"], "status_basis": "historical_accepted_status_not_new_validation",
            "scope": "public expert-perceived Big Five estimate; frozen accepted coefficients; correction audit is descriptive",
            "candidate_channels": list(channels), "selected_variant": accepted["selected_variant"],
            "selected_weights": copy.deepcopy(weights), "required_channels": accepted["required_channels"],
            "coverage_n": len(member_rows), "members": member_rows,
            "validation": validation, "diagnostic_gates": diagnostic_gates,
            "historical_validation": accepted["historical_validation"],
            "historical_validation_caveat": accepted["historical_validation_caveat"],
            "historical_ablation": accepted["historical_ablation"],
            "gates": accepted["gates"], "association_gates": accepted["association_gates"],
            "supporting_panels": accepted["supporting_panels"],
            "strict_discriminant_panels": accepted["strict_discriminant_panels"],
            "gold_direction": "negative_expert_emotional_stability" if trait == "N" else "same_named_appendix_trait",
            "eligibility": {"missing_required_channels": sorted(roster - set(member_rows)),
                            "optional_missing_counts": {channel: sum(name not in channels[channel] for name in member_rows)
                                                        for channel in weights if channel not in accepted["required_channels"]}},
        }
        if trait == "E":
            result["uses_interaction_dominance"] = weights.get("interaction_dominance", 0) > 0
            result["uses_role_adjusted_visibility"] = weights.get("role_adjusted_visibility", 0) > 0
        output_traits[trait] = result
    # A concurrent collector/build must not produce scores under an earlier receipt.
    if (input_hashes() != hashes or code_hashes() != dependencies or
            frozen_spec()[1] != spec_hash or registry_sha256() != registry_hash):
        raise RuntimeError("Big Five inputs or implementation changed during build; no artifact written")
    return {
        "schema": "big5-gold-anchored-v2", "status": "ACTIVE_WITH_TRAIT_LEVEL_GATES",
        "validation_status": "CURRENT_FIXED_DIAGNOSTIC" if audit or reusable else "NOT_REAUDITED_INPUTS_CHANGED",
        "design": {
            "validation": "fixed_accepted_weight_correction_audit", "predictions_are_out_of_fold": False,
            "historical_gold_used_to_fit_weights": True, "routine_build_uses_gold_values": False,
            "production_weights": "frozen_accepted_weights", "frozen_spec_sha256": spec_hash,
            "identity_registry_sha256": registry_hash, "score_code_sha256": code_hash,
            "code_dependencies_sha256": dependencies,
            "frozen_spec_path": "source_data/big5/frozen_accepted_spec.json",
            "accepted_vintage": spec["accepted_vintage"],
            "activation_gates": {"minimum_panel_n": MIN_PANEL_N, "minimum_panel_r": MIN_PANEL_R,
                                 "maximum_one_sided_permutation_p": MAX_P,
                                 "trait_activation_rule": "historical accepted statuses frozen; diagnostics cannot promote or demote"},
            "optional_channel_missingness": "current-roster-centered zero contribution; required primaries never imputed",
            "percentile_reference": "current eligible roster only",
        },
        "inputs_sha256": hashes, "identity_audit": identity,
        "coverage": {"roster_n": len(roster), "panel_n": {name: len(panel) for name, panel in panels.items()} if panels else
                     (previous.get("coverage", {}).get("panel_n", {}) if reusable else {})},
        "traits": output_traits,
    }


def self_test():
    weights = simplex_weights(("a", "b", "c"), {"b": .1})
    assert weights and all(abs(sum(row) - 1) < 1e-9 and row[1] >= .1 for row in weights)
    assert gold_value({"ES": 6}, "N") == -6
    assert abs(sum(zmap({"a": 1, "b": 2, "c": 3}).values())) < 1e-9
    print("b5_gold_multitrait_validate self-test: 3 passed, 0 failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--audit", action="store_true", help="Explicit fixed-weight correction diagnostic; no fitting")
    parser.add_argument("--out", default=OUT, help="Output artifact path; source inputs remain under MONEYBALL_ROOT")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    previous = json.loads(Path(args.out).read_text(encoding="utf-8")) if Path(args.out).exists() else None
    doc = build(audit=args.audit, previous=previous)
    dump_atomic(doc, args.out, indent=1)
    print("gold frozen weights: " + doc["validation_status"])
    for trait, row in doc["traits"].items():
        print("  %s %s n=%d weights=%s" % (trait, row["status"], row["coverage_n"], row["selected_weights"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
