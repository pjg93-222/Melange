#!/usr/bin/env python3
"""Read-only shadow probes for the primacy/orientation reconciliation."""
from __future__ import annotations

import copy
import json
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "fec"))

import moneyball_core as MC  # noqa: E402
import primacy_factors as PF  # noqa: E402
import tier_util as TU  # noqa: E402


def load_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def board(names, ranks, factor_rows):
    scores = TU.primacy_scores(
        ranks["pcts"],
        {
            name: values["factor_shrunk"]
            for name, values in factor_rows.items()
        },
    )
    order = sorted(names, key=lambda name: (-scores[name], name))
    final, _ = TU.apply_conduct_ladder(
        order,
        TU.load_open_breaches(str(ROOT)),
        TU.load_delivery_credit(str(ROOT)),
        buckets=TU.BUCKETS,
    )
    return scores, final, {
        name: index + 1 for index, name in enumerate(final)
    }


def orientation(scores, excluded=None):
    weights = {
        category: weight
        for category, weight in MC.IMP.items()
        if category != excluded
    }
    denominator = sum(weights.values())
    if denominator <= 0:
        return 0.0
    return max(
        -1.0,
        min(
            1.0,
            sum(
                weight * float(scores.get(category, 0.0) or 0.0)
                for category, weight in weights.items()
            )
            / denominator,
        ),
    )


def main():
    bundle = load_json("member_desk_bundle.json")
    ranks = load_json("ranks_python.json")
    stance = load_json("category_stance.json")
    tags = PF.load_tags(ROOT / "bill_beneficiary_tags.ndjson")
    credits = PF.load_adjudicated_credits(
        ROOT / PF.ADJUDICATION_LEDGER
    )
    names = [row["name"] for row in bundle["members"]]

    current_rows, _ = PF.compute(bundle, tags, credits)
    class_priced_tags = copy.deepcopy(tags)
    changed_letters = []
    for key, tag in class_priced_tags.items():
        if not PF.is_letter(key):
            continue
        proposed = PF.ACT_W[tag["class"]]
        current = PF.act_weight(tag, key)
        if tag.get(PF.LETTER_OVERRIDE_FIELD) is None:
            tag[PF.LETTER_OVERRIDE_FIELD] = proposed
        if abs(proposed - current) > 1e-12:
            changed_letters.append({
                "key": key,
                "class": tag["class"],
                "current": current,
                "proposed": proposed,
            })
    proposed_rows, _ = PF.compute(bundle, class_priced_tags, credits)
    _, current_order, current_rank = board(
        names, ranks, current_rows
    )
    _, proposed_order, proposed_rank = board(
        names, ranks, proposed_rows
    )

    tier, _, tier_priority = MC.primacy_engine_state(names)
    orientation_full = {
        name: orientation((stance.get("scores") or {}).get(name) or {})
        for name in names
    }
    flip_priority = {
        name: max(
            0.0,
            min(1.0, tier_priority[name] + 0.15 * orientation_full[name]),
        )
        for name in names
    }
    coalition_priority = {
        name: max(
            0.0,
            min(1.0, tier_priority[name] + 0.25 * orientation_full[name]),
        )
        for name in names
    }
    targets = (
        "Alex Padilla",
        "Vicente Gonzalez",
        "Brian Fitzpatrick",
        "Kevin Cramer",
        "William Timmons",
        "Tim Scott",
        "Bill Huizenga",
        "Scott Fitzgerald",
        "Juan Vargas",
        "Dan Sullivan",
        "Young Kim",
        "Brad Sherman",
        "Catherine Cortez Masto",
        "Maxine Waters",
    )
    moved = sorted(
        (
            {
                "member": name,
                "current": current_rank[name],
                "proposed": proposed_rank[name],
                "delta": proposed_rank[name] - current_rank[name],
            }
            for name in names
            if current_rank[name] != proposed_rank[name]
        ),
        key=lambda row: (-abs(row["delta"]), row["member"]),
    )
    result = {
        "letter_class_pricing": {
            "changed_letters": changed_letters,
            "top13_before": current_order[:13],
            "top13_after": proposed_order[:13],
            "top13_same": current_order[:13] == proposed_order[:13],
            "moved_members": len(moved),
            "max_abs_rank_delta": max(
                (abs(row["delta"]) for row in moved), default=0
            ),
            "largest_deltas": moved[:20],
            "targets": {
                name: {
                    "before": current_rank[name],
                    "after": proposed_rank[name],
                    "delta": proposed_rank[name] - current_rank[name],
                }
                for name in targets
            },
        },
        "orientation_probe": {
            "formula": (
                "fixed-IMP weighted category stance scores; missing=0; "
                "priority=clip(tier+alpha*orientation,0,1)"
            ),
            "flip_alpha": 0.15,
            "coalition_alpha": 0.25,
            "targets": {
                name: {
                    "tier": tier[name],
                    "tier_priority": round(tier_priority[name], 6),
                    "orientation": round(orientation_full[name], 6),
                    "flip_priority": round(flip_priority[name], 6),
                    "coalition_priority": round(
                        coalition_priority[name], 6
                    ),
                }
                for name in targets
            },
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
