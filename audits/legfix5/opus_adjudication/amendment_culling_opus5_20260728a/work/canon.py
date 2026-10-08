#!/usr/bin/env python3
"""The canonical nineteen category IDs, derived rather than declared.

This lane originally validated category IDs against a hand-written list copied
out of query_guard_registry_v2.json. That registry carries two NONCANONICAL
source aliases, so the copied list embedded them and the receipt's
`categories_are_canonical_19` assertion proved only that the lane agreed with
itself:

    ncua_budget_share_insurance_fund      -> ncua_budget_share_insurance
    telephone_consumer_protection_act_issues -> telephone_consumer_protection_act

The mapping is not invented here. fec/legislation_original_method_evidence.py is
the production module that builds this very frozen bundle, and it canonicalizes
those two IDs on the way in via CATEGORY_ID_ALIASES while still requiring
nineteen categories. That literal is read out of the production source by AST,
never executed and never retyped, so this lane cannot drift from it.

Three independent local sources must agree or nothing is returned:

  1. query_guard_registry_v2.json      the frozen registry bound in the manifest
  2. CATEGORY_ID_ALIASES               the production canonicalization
  3. category_review_queue manifests   receipt.category_registry, the nineteen
                                       IDs production feeds to OriginalMethodEvidence

Read-only. Raises rather than guessing.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib

EV = pathlib.Path(
    r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\legfix5\opus_adjudication\original_method_evidence")
PROD = pathlib.Path(
    r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\fec\legislation_original_method_evidence.py")
QUEUES = pathlib.Path(
    r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\legfix5\category_review_queue\queues")
EXPECTED_CATEGORY_COUNT = 19


class CanonError(RuntimeError):
    """The canonical vocabulary could not be derived from local evidence."""


def _sha(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_aliases() -> dict[str, str]:
    """CATEGORY_ID_ALIASES lifted from the production source without executing it."""
    tree = ast.parse(PROD.read_text(encoding="utf-8"), filename=str(PROD))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "CATEGORY_ID_ALIASES":
                value = ast.literal_eval(node.value)
                if not isinstance(value, dict) or not value:
                    raise CanonError("CATEGORY_ID_ALIASES is not a non-empty dict")
                return {str(k): str(v) for k, v in value.items()}
    raise CanonError(f"CATEGORY_ID_ALIASES not found in {PROD}")


def registry_source_ids() -> list[str]:
    guards = json.loads((EV / "query_guard_registry_v2.json").read_bytes().decode("utf-8-sig"))
    ids = [str(c.get("category_id") or "") for c in guards["categories"]]
    if len(ids) != EXPECTED_CATEGORY_COUNT or any(not i for i in ids):
        raise CanonError(f"frozen guard registry does not carry {EXPECTED_CATEGORY_COUNT} usable IDs")
    return ids


def queue_registry_ids() -> tuple[list[list[str]], list[pathlib.Path]]:
    found, paths = [], []
    if not QUEUES.is_dir():
        return found, paths
    for man in sorted(QUEUES.glob("*/manifest.json")):
        try:
            reg = (json.loads(man.read_text(encoding="utf-8")).get("receipt")
                   or {}).get("category_registry") or []
        except (json.JSONDecodeError, OSError):
            continue
        ids = [str(r.get("category_id") or "") for r in reg]
        if len(ids) == EXPECTED_CATEGORY_COUNT and all(ids):
            found.append(sorted(ids))
            paths.append(man)
    return found, paths


def canonical() -> dict:
    aliases = load_aliases()
    source_ids = registry_source_ids()
    canon = [aliases.get(i, i) for i in source_ids]

    if len(set(canon)) != EXPECTED_CATEGORY_COUNT:
        raise CanonError("canonicalisation collapsed two source IDs onto one")
    leftover = sorted(set(canon) & set(aliases))
    if leftover:
        raise CanonError(f"noncanonical alias survived canonicalisation: {leftover}")

    corroborating, paths = queue_registry_ids()
    agree = [sorted(canon) == c for c in corroborating]
    if corroborating and not all(agree):
        raise CanonError("derived canonical set disagrees with a category_review_queue registry")

    return {
        "canonical_ids": sorted(canon),
        "count": len(canon),
        "source_registry": str(EV / "query_guard_registry_v2.json"),
        "source_registry_sha256": _sha(EV / "query_guard_registry_v2.json"),
        "source_registry_ids": sorted(source_ids),
        "alias_map": aliases,
        "alias_source": str(PROD),
        "alias_source_sha256": _sha(PROD),
        "corroborating_registries": [
            {"path": str(p), "sha256": _sha(p), "agrees": a}
            for p, a in zip(paths, agree)
        ],
        "aliases_applied": sorted(set(source_ids) & set(aliases)),
    }


CANON = canonical()
CANONICAL_IDS: set[str] = set(CANON["canonical_ids"])
ALIASES: dict[str, str] = CANON["alias_map"]


def canonicalise(category_id: str) -> str:
    return ALIASES.get(category_id, category_id)


def canonicalise_all(ids) -> list[str]:
    return [canonicalise(i) for i in ids]


if __name__ == "__main__":
    print(json.dumps(CANON, indent=1))
