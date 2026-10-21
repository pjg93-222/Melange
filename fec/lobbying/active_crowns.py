# -*- coding: utf-8 -*-
"""The crown set the lobbying boards read: the ACTIVE rank_honors generation.

D-157 F-20.  ``build_rank_honors.py --publish`` runs early in the chain and
captures tier_util's board (the tier and 1-based position of every member, from
the same ``legislative_press_tiers`` call the member desk makes) in
``overall_board``.  champions_v2 and industry_tiers read that generation instead
of the previous cycle's ``member_desk_bundle.json``, whose tiers are computed
before the chain's own factor and grade refresh.

Fail closed: a missing, unreadable, schema-mismatched or stale (source hashes
changed since it was built) generation, or ``HONORS_MODE=legacy``, raises.
There is no fallback to the bundle.
"""
import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # noqa: E501,E702

from paths import ROOT
from stance.honors_views import load_honors


def active_board(root=None, expected_mode=None):
    """Return ``(tier, rank, generation_id)`` from the active generation.

    ``tier`` and ``rank`` are dicts keyed by member name: the 0-3 priority tier
    (1 is the crown set) and the 1-based board position.  ``generation_id`` is
    the generation they were read from, which callers record in their output
    receipt.  Raises ValueError when no usable generation exists or its board
    mode is not ``expected_mode``.
    """
    root = root or ROOT
    try:
        honors = load_honors(root)
        if honors is None:
            raise ValueError("HONORS_MODE=legacy selects no rank_honors generation")
        board = honors["overall_board"]
        tier, order = dict(board["priority_tiers"]), list(board["order"])
        mode = board["mode"]
        generation = str(honors["generation_id"])
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            "no usable active rank_honors generation under %s (%s: %s); "
            "run build_rank_honors.py --publish first"
            % (root, type(exc).__name__, exc)
        ) from exc
    if len(set(order)) != len(order) or set(order) != set(tier):
        raise ValueError("active rank_honors board order does not cover its tier map exactly")
    if expected_mode is not None and mode != expected_mode:
        raise ValueError(
            "active rank_honors board is %r, not the expected %r" % (mode, expected_mode)
        )
    return tier, {name: index + 1 for index, name in enumerate(order)}, generation
