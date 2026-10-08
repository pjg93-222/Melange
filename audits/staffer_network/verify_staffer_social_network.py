#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Independent verifier for a receipt-declared staffer social-network generation.

This is a SECOND implementation. It does not import the builder and it does not use
the builder's sweep-line pair enumeration. It re-derives the headline counts by a
different algorithm - full per-container pair enumeration with numpy run-level
broadcasting - and it re-derives the component structure from the emitted edge file
with scipy.csgraph rather than from the builder's in-memory operator.

Read-only on every input and on the primary/twin generations.
"""

from __future__ import annotations

import argparse
import fnmatch
import gzip
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterator, Mapping

import numpy as np
from scipy import sparse
from scipy.sparse import csgraph

RECEIPT_SCHEMA_ID = "staffer-network-social-verification-receipt-v1"
SAMPLE_SEED = 20260903
SAMPLE_SIZE = 2000

# Mirrors build_staffer_social_network.CO_TENURE_EXCLUDED_CONTAINER_KINDS (owner ruling
# 2026-09-07: chamber-wide administrative payroll headers are paymasters, not
# workplaces, so they enumerate no person-person pair). It is hard-coded here rather
# than read out of the receipt on purpose: a verifier that took the builder's word for
# its own candidate universe could never disagree with it. The receipt's declared set
# is cross-checked against this constant instead, so a divergence fails.
CO_TENURE_EXCLUDED_CONTAINER_KINDS = frozenset({"admin"})

# Explicit publication consumers introduced after the original isolated artifact
# audit. Unknown references still fail, and these paths get NO glob exemption.
RECEIPT_CONSUMERS = frozenset({
    'fec/run_pipeline.py', 'fec/surfaces/build_staffer_network_section.py',
    'fec/surfaces/repin_staffer_live.py', 'fec/surfaces/staffer_graph_snapshot.py',
    'fec/surfaces/staffer_person_inventory.py', 'fec/surfaces/staffer_routing_evidence.py',
    'audits/staffer_network/finish_staffer_social_network_chain.py',
    # Lane-owned consumers, authorised 2026-09-07 (D-022).
    'fec/surfaces/build_staffer_groups_section.py', 'fec/surfaces/staffer_live_service.py',
    'fec/surfaces/staffer_outreach_ranking.py',
    'audits/staffer_ranking_math_20260908/build_candidate.py',
    'audits/staffer_ranking_math_20260908/analyze_candidate.py',
    # Coordinated spine release reads a pinned graph receipt to bind native IDs.
    'audits/staffer_network/rebuild_spine_identity.py',
    'audits/dashboard_repair_20260905/validate_staffer_preservation.py',
})
REFERENCE_TESTS = frozenset({
    'fec/surfaces/test_repin_staffer_live.py', 'fec/surfaces/test_staffer_graph_snapshot.py',
    'fec/tests/surfaces/test_make_staffer_network_html.py',
    'fec/tests/surfaces/test_staffer_network_section.py',
    'fec/tests/surfaces/test_staffer_person_inventory.py',
    'audits/staffer_network/test_finish_staffer_social_network_chain.py',
    'audits/staffer_network/test_sna_audit_repairs.py',
    'audits/staffer_network/test_spine_identity_release.py',
    # The kernel test REGISTRY, not a consumer: it names the persons-only suite in a
    # tuple of basenames and explains in a comment why that suite is a gate. It reads
    # no artifact and selects no file. Added 2026-09-07 when that suite was registered.
    'fec/tests/run_tests.py',
    # Lane-owned consumers, authorised 2026-09-07 (D-022).
    'fec/tests/surfaces/test_staffer_groups_section.py',
    'fec/tests/surfaces/test_staffer_automatic_service.py',
    'fec/tests/staffer_network/test_ranking_math.py',
})


def reference_scope(relative_path):
    """Classify direct references; never exempts a live ingestion selector."""
    path = str(relative_path).replace('\\', '/')
    if path in RECEIPT_CONSUMERS:
        return 'explicit_receipt_consumer'
    if path in REFERENCE_TESTS:
        return 'regression_test'
    if path.startswith(('audits/staffer_live_runtime/backups/',
                        'audits/staffer_network/sna_review_20260905/')):
        return 'retained_audit_or_backup'
    # Ruling 2026-09-07 (lane owner): frozen audit records are not live consumers.
    # A path under audits/ is retained_audit_or_backup - never a live selector hit -
    # when it carries a "/before/" snapshot segment, is a seal.py integrity stamp, or
    # sits under a dated lane snapshot directory (audits/staffer_network/*_2026MMDD/,
    # e.g. person_overlap_20260905, unified_people_20260905, balanced_latency_20260905,
    # route_office_ux_20260905, deep_identity_adjudication_20260906) or under
    # audits/dashboard_repair_20260905/. Gated on audits/ only: this must never reach
    # fec/, where live code stays subject to the law.
    if path.startswith('audits/'):
        segments = path.split('/')
        if 'before' in segments[:-1]:
            return 'retained_audit_or_backup'
        if segments[-1] == 'seal.py':
            return 'retained_audit_or_backup'
        if (len(segments) > 2 and segments[1] == 'staffer_network'
                and re.match(r'.*_2026\d{4}$', segments[2])):
            return 'retained_audit_or_backup'
        if path.startswith('audits/dashboard_repair_20260905/'):
            return 'retained_audit_or_backup'
    return 'unexpected_reference'


def rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def k64(text: str) -> int:
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "big", signed=False) >> 1


def union_runs(rs):
    rs = sorted((s, e) for s, e in rs if e > s)
    if not rs:
        return []
    out = [list(rs[0])]
    for s, e in rs[1:]:
        if s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(a, b) for a, b in out]


QUARTER_TOKEN_RE = re.compile(r"^(\d{4})Q([1-4])$")


def period_window(chamber: str, token: Any) -> tuple[int, int]:
    """Half-open [start, end) ORDINALS of one reporting period, re-derived here.

    Independent of the builder's period_bounds: House quarters are built from the
    month arithmetic directly, Senate semiannual windows from the token's own month.
    A disagreement between the two implementations shows up as a co-tenure count
    mismatch, which fails.
    """
    text = str(token or "").strip()
    if chamber == "house":
        match = QUARTER_TOKEN_RE.match(text.upper())
        if not match:
            raise ValueError("unparseable house period token %r" % (token,))
        year, quarter = int(match.group(1)), int(match.group(2))
        start = date(year, 3 * quarter - 2, 1)
        end = date(year + 1, 1, 1) if quarter == 4 else date(year, 3 * quarter + 1, 1)
        return start.toordinal(), end.toordinal()
    day = date.fromisoformat(text[:10])
    if day.month >= 10:
        return date(day.year, 10, 1).toordinal(), date(day.year + 1, 4, 1).toordinal()
    if day.month <= 3:
        return date(day.year - 1, 10, 1).toordinal(), date(day.year, 4, 1).toordinal()
    return date(day.year, 4, 1).toordinal(), date(day.year, 10, 1).toordinal()


def span_runs(row: Mapping[str, Any], chamber: str, core_s: int, core_e: int):
    """One half-open run per contiguous_runs entry (owner ruling 2026-09-07).

    Same rule as the builder's span_core_runs, written independently: the outer
    endpoints come from the row's own core dates so a single-run span is unchanged,
    interior endpoints come from period arithmetic, and every run is clamped into the
    row's core so this path can only narrow a calendar.  Returns (runs, basis).
    """
    raw = row.get("contiguous_runs")
    if not isinstance(raw, (list, tuple)) or not raw:
        return [(core_s, core_e)], "span_min_to_max"
    out = []
    for index, item in enumerate(raw):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("contiguous_runs entry %d is malformed: %r" % (index, item))
        lo = core_s if index == 0 else period_window(chamber, item[0])[0]
        hi = core_e if index == len(raw) - 1 else period_window(chamber, item[1])[1]
        lo = lo if lo > core_s else core_s
        hi = hi if hi < core_e else core_e
        if hi > lo:
            out.append((lo, hi))
    if not out:
        return [(core_s, core_e)], "span_min_to_max"
    return union_runs(out), "contiguous_runs"


def normalized_container(office_key: str) -> str:
    """Independent implementation of the closed year-prefix normalization rule."""
    prefix = "FISCAL YEAR "
    if (office_key.startswith(prefix) and len(office_key) > len(prefix) + 5
            and office_key[len(prefix):len(prefix) + 4].isdigit()
            and office_key[len(prefix) + 4] == " "):
        return office_key[len(prefix) + 5:]
    if len(office_key) > 5 and office_key[:4].isdigit() and office_key[4] == " ":
        return office_key[5:]
    return office_key


def independent_transition(n, endpoints_a, endpoints_b, weights, layers):
    """Reconstruct layer-normalized bidirectional probabilities from emitted rows.

    No builder/network_math import; each layer's row sums are counted directly.
    Duplicate positive pairs within a layer are rejected instead of summed.
    """
    u, v = np.asarray(endpoints_a), np.asarray(endpoints_b)
    w, layer = np.asarray(weights), np.asarray(layers)
    active = np.zeros(n, dtype=np.int32)
    strengths = {}
    for value in np.unique(layer):
        mask = layer == value
        strength = np.bincount(u[mask], weights=w[mask], minlength=n)
        strength += np.bincount(v[mask], weights=w[mask], minlength=n)
        strengths[value] = strength
        active += strength > 0
    transition = sparse.csr_matrix((n, n), dtype=np.float64)
    for value, strength in strengths.items():
        mask = layer == value
        a, b, weight = u[mask], v[mask], w[mask]
        forward = sparse.coo_matrix((weight / strength[a] / active[a], (a, b)), shape=(n, n)).tocsr()
        reverse = sparse.coo_matrix((weight / strength[b] / active[b], (b, a)), shape=(n, n)).tocsr()
        combined = forward + reverse
        if combined.nnz != 2*int(mask.sum()):
            raise ValueError('duplicate positive endpoint pair within a layer')
        transition += combined
    return transition


def attribution_valid(e, factor):
    """Independent scalar check, active under python -O as well as normal runs."""
    try:
        days = e['container_guaranteed_days']
        shared = e['container_shared_role']
        shares = e['container_mass_shares']
        containers = e['container_ids']
        if not (len(days) == len(shared) == len(shares) == len(containers) > 0
                and len(set(containers)) == len(containers)
                and factor == .05 and e['shared_role_factor'] == factor
                and all(isinstance(d, int) and not isinstance(d, bool) and d > 0 for d in days)
                and all(isinstance(s, bool) for s in shared)
                and all(math.isfinite(s) and s > 0 for s in shares)):
            return False
        effective = [d * (factor if s else 1) for d, s in zip(days, shared)]
        total = sum(effective)
        attenuation = total / sum(days)
        expected = e['kappa'] * e['tier_strength'] * (-math.expm1(-e['guaranteed_days'] / 365.2425)) * attenuation
        return (math.isfinite(e['w_tiered_lower']) and math.isfinite(e['shared_role_attenuation'])
                and abs(expected - e['w_tiered_lower']) <= 1e-12
                and abs(attenuation - e['shared_role_attenuation']) <= 1e-12
                and all(abs(x - d / total) <= 1e-12 for x, d in zip(shares, effective))
                and abs(sum(shares) - 1) <= 1e-12
                and all(not re.search(r':INTERN\s+COMPENSATION(?:\s|[-:–—]|$)', c.upper()) for c in containers))
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return False


def independent_office_diversity(n_people, n_containers, edge_a, edge_b, weight, container_lists,
                               container_shares, return_mass=False):
    """Second implementation of office_diversity, from the EMITTED edge rows.

    The builder attributes tie mass through a chunked scipy accumulation over a CSR-style
    container listing built inside the sweep.  This walks the emitted rows in Python and
    accumulates into plain dictionaries - a different code path, same answer required.
    """
    strength = [0.0] * n_people
    for a, b, w in zip(edge_a, edge_b, weight):
        strength[a] += w
        strength[b] += w
    mass: dict[int, dict[int, float]] = defaultdict(dict)
    for a, b, w, containers, shares in zip(edge_a, edge_b, weight, container_lists, container_shares):
        if not containers:
            continue
        for endpoint in (a, b):
            if strength[endpoint] <= 0:
                continue
            row = mass[endpoint]
            for container, share in zip(containers, shares):
                value = w * share / strength[endpoint]
                row[container] = row.get(container, 0.0) + value
    diversity = np.zeros(n_people, dtype=np.float64)
    distinct = np.zeros(n_people, dtype=np.int64)
    if n_containers > 1:
        scale = 1.0 - 1.0 / float(n_containers)
        for person, row in mass.items():
            squared = sum(value * value for value in row.values())
            diversity[person] = min(max((1.0 - squared) / scale, 0.0), 1.0)
            distinct[person] = len(row)
    else:
        for person, row in mass.items():
            distinct[person] = len(row)
    if return_mass:
        return diversity, distinct, mass, strength
    return diversity, distinct


def independent_score_checks(transition, kinds, pageranks, eigenvector):
    """Test score equations, normalization and published diagnostics independently.

    The v4 operator is PERSONS ONLY with a UNIFORM restart, so the teleport vector is
    rebuilt here as 1/n rather than from node kinds.  A non-person node in the published
    node file is a separate, hard failure raised by the caller.
    """
    n = transition.shape[0]
    kinds = np.asarray(kinds)
    teleport = np.full(n, 1.0 / float(n), dtype=np.float64)
    dangling = np.asarray(transition.sum(axis=1)).ravel() == 0
    failures, page_details = [], []
    for alpha, values in sorted(pageranks.items()):
        values = np.asarray(values, dtype=float)
        valid = np.isfinite(values).all() and np.all(values >= 0) and abs(values.sum() - 1) <= 1e-10
        updated = alpha * (transition.T @ values) + ((1-alpha) + alpha * values[dangling].sum()) * teleport
        residual = float(np.linalg.norm(updated-values, ord=1))
        if not valid or not np.isfinite(residual) or residual > 1e-10:
            failures.append('pagerank_stationarity_' + str(alpha))
        page_details.append({'alpha': alpha, 'stationary_residual_l1': residual if np.isfinite(residual) else None,
                             'error_bound_l1': residual/(1-alpha) if np.isfinite(residual) else None,
                             'normalized_nonnegative': bool(valid)})
    components, labels = csgraph.connected_components(transition, directed=False)
    x = np.asarray(eigenvector, dtype=float)
    missing = ~np.isfinite(x)
    if missing.any():
        failures.append('eigenvector_missing_or_nonfinite')
    x = np.nan_to_num(x)
    ax = (transition @ x + transition.T @ x) * .5
    norm2 = np.bincount(labels, weights=x*x, minlength=components)
    rayleigh = np.divide(np.bincount(labels, weights=x*ax, minlength=components), norm2,
                         out=np.zeros(components), where=norm2>0)
    errors = ax - rayleigh[labels]*x
    numerator = np.bincount(labels, weights=errors*errors, minlength=components)
    denominator = np.bincount(labels, weights=ax*ax, minlength=components)
    relative = np.sqrt(np.divide(numerator, denominator, out=np.zeros(components), where=denominator>0))
    sums = np.bincount(labels, weights=x, minlength=components)
    active_components = np.bincount(labels, weights=(~dangling).astype(float), minlength=components)>0
    normalization = float(np.max(np.abs(sums[active_components]-1))) if active_components.any() else 0.0
    max_residual = float(relative.max()) if relative.size else 0.0
    if np.any(x < 0) or np.any(x[dangling] != 0) or normalization > 1e-8 or max_residual > 1e-7:
        failures.append('component_eigenpair')
    return {'pagerank': page_details,
            'teleport': 'uniform over persons, rebuilt independently as 1/n',
            'eigenvector_max_component_relative_residual_l2': max_residual,
            'eigenvector_component_l1_normalization_error': normalization,
            'eigenvector_relative_residual_tolerance': 1e-7,
            'scope': 'stationary equations and eigenpair residuals; no claim of per-entry relative accuracy',
            'failures': failures}


def by_container_keys(cells):
    """Container indices that hold at least one person-container cell."""
    return {c for (_p, c) in cells}


def component_count_check(graph, expected):
    components, labels = csgraph.connected_components(graph, directed=False)
    sizes = np.bincount(labels, minlength=components)
    isolated = np.asarray(graph.getnnz(axis=1)).ravel() == 0
    result = {'nodes': graph.shape[0], 'components': int(components),
              'isolates': int(isolated.sum()), 'largest_component': int(sizes.max()) if sizes.size else 0,
              'scope': 'all published nodes, including isolates'}
    result['match'] = all(result[name] == expected[name] for name in ('nodes','components','isolates','largest_component'))
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--primary", required=True)
    ap.add_argument("--twin", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--repository-root", default=str(Path(__file__).resolve().parents[2]))
    ap.add_argument("--expected-config-name")
    ap.add_argument("--expected-vintage")
    args = ap.parse_args(argv)

    root = Path(args.repository_root).resolve()
    primary = Path(args.primary).resolve()
    twin = Path(args.twin).resolve()
    out = Path(args.output).resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"output directory is not empty: {out}")
    out.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {"schema_id": RECEIPT_SCHEMA_ID, "failures": [],
                              "primary": str(primary), "twin": str(twin),
                              "verifier_implementation": {"path": str(Path(__file__).resolve()),
                                                          "sha256": sha256_file(Path(__file__))}}

    def fail(check: str, detail: Any) -> None:
        result["failures"].append({"check": check, "detail": detail})

    receipt = json.loads((primary / "staffer_social_network_receipt.json").read_text(encoding="utf-8"))
    manifest = json.loads((primary / "staffer_social_network_manifest.json").read_text(encoding="utf-8"))
    result["metadata"] = {
        "receipt_config_name": receipt.get("config_name"),
        "manifest_config_name": manifest.get("config_name"),
        "receipt_vintage": receipt.get("vintage"),
        "manifest_vintage": manifest.get("vintage"),
        "generated_at": receipt.get("generated_at"),
        "expected_config_name": args.expected_config_name,
        "expected_vintage": args.expected_vintage,
    }
    if receipt.get("config_name") != manifest.get("config_name"):
        fail("metadata_config_receipt_manifest", result["metadata"])
    if receipt.get("vintage") != manifest.get("vintage"):
        fail("metadata_vintage_receipt_manifest", result["metadata"])
    if args.expected_config_name and receipt.get("config_name") != args.expected_config_name:
        fail("metadata_expected_config", result["metadata"])
    if args.expected_vintage and str(receipt.get("vintage")) != str(args.expected_vintage):
        fail("metadata_expected_vintage", result["metadata"])

    # ---------------------------------------------------------------- file integrity
    file_checks = []
    for entry in receipt["files"]:
        p = primary / entry["path"]
        actual = sha256_file(p)
        ok = actual == entry["sha256"] and p.stat().st_size == entry["bytes"]
        file_checks.append({"path": entry["path"], "receipt_sha256": entry["sha256"],
                            "recomputed_sha256": actual, "match": ok})
        if not ok:
            fail("primary_file_sha256", entry["path"])
    result["primary_file_integrity"] = file_checks

    # ---------------------------------------------------------------- twin identity
    twin_checks = []
    for entry in receipt["files"] + [{"path": "staffer_social_network_receipt.json"},
                                     {"path": "staffer_social_network_manifest.json"}]:
        a = primary / entry["path"]
        b = twin / entry["path"]
        if not b.exists():
            twin_checks.append({"path": entry["path"], "identical": False, "reason": "missing in twin"})
            fail("twin_missing_file", entry["path"])
            continue
        ha, hb = sha256_file(a), sha256_file(b)
        same = ha == hb
        note = None
        # TWIN IDENTITY IS BYTE IDENTITY EXCLUDING generated_at (and, in the manifest,
        # generation_id - the output DIRECTORY NAME, which must differ by construction,
        # and the receipt hash that carries generated_at forward). Nothing else may
        # differ: the tolerance is enumerated, never a general "close enough".
        if not same and entry["path"] == "staffer_social_network_receipt.json":
            ja = json.loads(a.read_text(encoding="utf-8"))
            jb = json.loads(b.read_text(encoding="utf-8"))
            diff = {k for k in set(ja) | set(jb) if ja.get(k) != jb.get(k)}
            if diff and diff <= {"generated_at"}:
                same = True
                note = "differs only in generated_at, which is excluded from twin identity"
            else:
                note = f"differs in {sorted(diff)}"
        if not same and entry["path"] == "staffer_social_network_manifest.json":
            ja = json.loads(a.read_text(encoding="utf-8"))
            jb = json.loads(b.read_text(encoding="utf-8"))
            diff = {k for k in set(ja) | set(jb) if ja.get(k) != jb.get(k)}
            allowed = {"generation_id", "generated_at", "receipt"}
            if diff and diff <= allowed and ja.get("canonical_output_hash") == jb.get("canonical_output_hash"):
                same = True
                note = ("differs only in " + ", ".join(sorted(diff)) + "; generation_id is "
                        "the output directory name by design and receipt carries "
                        "generated_at forward; canonical_output_hash matches")
            else:
                note = f"differs in {sorted(diff)}"
        twin_checks.append({"path": entry["path"], "primary_sha256": ha,
                            "twin_sha256": hb, "identical": same, "note": note})
        if not same:
            fail("twin_not_byte_identical", entry["path"])
    result["twin_byte_identity"] = twin_checks

    # ---------------------------------------------------------------- independent rebuild
    declared_inputs = {entry["role"]: Path(entry["path"]) for entry in receipt["inputs"]}
    input_integrity = []
    for entry in receipt["inputs"]:
        path = Path(entry["path"])
        actual = sha256_file(path) if path.exists() else None
        match = (
            path.exists()
            and actual == entry.get("sha256")
            and path.stat().st_size == entry.get("bytes")
        )
        input_integrity.append(
            {
                "role": entry["role"],
                "path": str(path),
                "declared_sha256": entry.get("sha256"),
                "recomputed_sha256": actual,
                "match": match,
            }
        )
        if not match:
            fail("declared_input_integrity", entry["role"])
    result["declared_input_integrity"] = input_integrity
    spans_path = declared_inputs["hill_person_office_spans"]
    obs_path = declared_inputs["house_personnel_observations"]

    # day-precision lookup, built as a plain dict here (the builder used sorted arrays)
    day_map: dict[int, tuple[int, int]] = {}
    for r in rows(obs_path):
        sf, ri = r.get("source_file"), r.get("source_row_index")
        s, e = r.get("service_start"), r.get("service_end")
        if not isinstance(sf, str) or ri is None or not s or not e:
            continue
        so = date.fromisoformat(s).toordinal()
        eo = date.fromisoformat(e).toordinal() + 1
        if eo > so:
            day_map[k64(f"house-ledger:{sf}#{ri}")] = (so, eo)

    # A LIMITED RUN declares its own person prefix; the verifier re-applies the SAME
    # documented rule from the receipt rather than trusting the builder's person list.
    limited_block = receipt.get("limited_run") or {}
    limit_persons = int(limited_block.get("limit_persons") or 0)
    limited_run = bool(limited_block.get("limited_run"))
    if limited_run != bool(limit_persons):
        fail("limited_run_declaration", limited_block)

    persons: dict[str, int] = {}
    containers: dict[str, int] = {}
    pc_core: dict[tuple[int, int], list] = defaultdict(list)
    pc_env: dict[tuple[int, int], list] = defaultdict(list)
    pc_shared = set()
    ep_prec: dict[int, set] = defaultdict(set)
    n_spans = 0
    n_spans_skipped = 0
    # ---- independent stint census (owner ruling 2026-09-07) ----------------------
    v_stints = 0
    v_spans_multi_run = 0
    v_spans_with_runs = 0
    v_spans_without_runs = 0
    v_max_run_days = 0
    v_max_span_days = 0
    v_run_basis = Counter()
    for r in rows(spans_path):
        n_spans += 1
        if limit_persons and r["spine_person_id"] not in persons and len(persons) >= limit_persons:
            n_spans_skipped += 1
            continue
        p = persons.setdefault(r["spine_person_id"], len(persons))
        cid_key = f"{r['chamber']}\x00{normalized_container(r['office_key'])}"
        c = containers.setdefault(cid_key, len(containers))
        if ' '.join(str(r.get('title_last') or '').upper().split()) in {
                'SHARED EMPLOYEE', 'SHARED EMPLOYEE (OTHER COMPENSATION)'}:
            pc_shared.add((p, c))
        cs = date.fromisoformat(r["core"]["start_latest"]).toordinal()
        ce = date.fromisoformat(r["core"]["end_earliest"]).toordinal() + 1
        es = date.fromisoformat(r["envelope"]["start_earliest"]).toordinal()
        ee = date.fromisoformat(r["envelope"]["end_latest"]).toordinal() + 1
        core, basis = span_runs(r, r["chamber"], cs, ce)
        if basis == "contiguous_runs":
            v_spans_with_runs += 1
        else:
            v_spans_without_runs += 1
        env = [(es, ee)]
        prec = "REPORT_PERIOD"
        if r["chamber"] == "house":
            got, miss = [], 0
            for rid in r["source_row_ids"]:
                v = day_map.get(k64(rid))
                if v is None:
                    miss += 1
                else:
                    got.append(v)
            if got and miss == 0:
                core = union_runs(got)
                basis = "day_intervals"
                env = list(core)
                prec = "DAY"
        v_run_basis[basis] += 1
        v_stints += len(core)
        if len(core) > 1:
            v_spans_multi_run += 1
        v_max_span_days = max(v_max_span_days, int(ce - cs))
        v_max_run_days = max(v_max_run_days, max(int(hi - lo) for lo, hi in core))
        pc_core[(p, c)].extend(core)
        pc_env[(p, c)].extend(env)
        ep_prec[p].add(prec)

    NP = len(persons)
    NC = len(containers)
    # Unioned per (person, container) core calendar, built ONCE and consumed by both
    # the co-tenure recomputation and the stint containment check below.
    pc_union: dict[tuple[int, int], list] = {
        key: union_runs(runs) for key, runs in pc_core.items()
    }
    # lda_source_person_id per spine person; the person-registrant grouping rows join
    # through it, so the verifier re-derives that join from the declared spine input.
    spine_lda: dict[str, str] = {}
    spine_rows_read = 0
    for r in rows(declared_inputs["hill_person_spine"]):
        spine_rows_read += 1
        value = r.get("lda_source_person_id")
        if isinstance(value, str) and value:
            spine_lda[r["spine_person_id"]] = value
    result["independent_universe"] = {
        "spans_read": n_spans, "spans_skipped_by_limit": n_spans_skipped,
        "persons": NP, "containers": NC,
        "person_container_cells": len(pc_core),
        "spine_rows_read": spine_rows_read,
        "limited_run": limited_run, "limit_persons": limit_persons or None,
    }
    if receipt["node_universe"]["person"] != NP:
        fail("person_node_count", {"receipt": receipt["node_universe"]["person"], "verifier": NP})
    if receipt["node_universe"].get("total") != NP:
        fail("node_universe_total_is_not_the_person_count",
             {"receipt": receipt["node_universe"].get("total"), "verifier": NP})
    for absent in ("container", "organization", "policy_area"):
        if absent in receipt["node_universe"]:
            fail("node_universe_declares_a_non_person_kind", absent)
    group_universe = receipt.get("group_universe") or {}
    if group_universe.get("container") != NC:
        fail("container_group_count", {"receipt": group_universe.get("container"), "verifier": NC})
    if limited_run and n_spans_skipped != int(limited_block.get("spans_rows_skipped_by_limit") or -1):
        fail("limited_run_skipped_rows",
             {"receipt": limited_block.get("spans_rows_skipped_by_limit"),
              "verifier": n_spans_skipped})

    # ---- co-tenure container eligibility, re-derived from member_office_index ------
    # Independent of the builder's in-memory container_meta: the index rows are re-read
    # here, merged under the same closed year-prefix normalization, and a container's
    # kind is the single specific kind its fragments agree on.
    container_kind: dict[str, str] = {}
    kind_conflicts: list[str] = []
    for r in rows(declared_inputs["hill_member_office_index"]):
        key = f"{r['chamber']}\x00{normalized_container(r['office_key'])}"
        specific = {value for value in (container_kind.get(key), r.get("container_kind"))
                    if value not in (None, "unresolved")}
        if len(specific) > 1:
            kind_conflicts.append(key)
        container_kind[key] = next(iter(sorted(specific)), "unresolved")
    if kind_conflicts:
        fail("container_kind_conflict", kind_conflicts[:5])
    eligible_containers = {
        index for key, index in containers.items()
        if container_kind.get(key, "unresolved") not in CO_TENURE_EXCLUDED_CONTAINER_KINDS
        and not re.match(r'^INTERN\s+COMPENSATION(?:\s|[-:–—]|$)', key.split('\x00', 1)[1].upper())
    }
    declared_eligibility = receipt.get("co_tenure_container_eligibility") or {}
    result["co_tenure_container_eligibility_recheck"] = {
        "verifier_excluded_kinds": sorted(CO_TENURE_EXCLUDED_CONTAINER_KINDS),
        "receipt_excluded_kinds": declared_eligibility.get("excluded_container_kinds"),
        "verifier_containers_with_people": len(by_container_keys(pc_union)),
        "verifier_containers_eligible": len(
            eligible_containers & by_container_keys(pc_union)
        ),
        "receipt_containers_eligible": declared_eligibility.get(
            "containers_eligible_for_co_tenure"),
        "match": (
            declared_eligibility.get("excluded_container_kinds")
            == sorted(CO_TENURE_EXCLUDED_CONTAINER_KINDS)
            and declared_eligibility.get("containers_eligible_for_co_tenure")
            == len(eligible_containers & by_container_keys(pc_union))
        ),
    }
    if not result["co_tenure_container_eligibility_recheck"]["match"]:
        fail("co_tenure_container_eligibility",
             result["co_tenure_container_eligibility_recheck"])

    by_container: dict[int, list] = defaultdict(list)
    for (p, c), runs in pc_union.items():
        if c not in eligible_containers:
            continue
        by_container[c].append((p, runs, union_runs(pc_env[(p, c)])))

    # ---- full per-container pair enumeration with numpy run-level broadcasting -----
    guar_chunks: list[np.ndarray] = []
    poss_chunks: list[np.ndarray] = []
    cocont_chunks: list[np.ndarray] = []
    for c, people in by_container.items():
        if len(people) < 2:
            continue
        ids = np.asarray([p for p, _, _ in people], dtype=np.int64)
        n = ids.size
        i, j = np.triu_indices(n, 1)
        cocont_chunks.append(np.minimum(ids[i], ids[j]) * NP + np.maximum(ids[i], ids[j]))
        del i, j
        for which, sink in (("core", guar_chunks), ("env", poss_chunks)):
            starts, ends, owner = [], [], []
            for k, (p, core, env) in enumerate(people):
                for s, e in (core if which == "core" else env):
                    starts.append(s); ends.append(e); owner.append(k)
            S = np.asarray(starts, dtype=np.int64)
            E = np.asarray(ends, dtype=np.int64)
            O = np.asarray(owner, dtype=np.int64)
            # block the O(m^2) broadcast so a 4k-run container cannot spike memory
            BL = 2048
            for b0 in range(0, S.size, BL):
                b1 = min(b0 + BL, S.size)
                lo = np.maximum(S[b0:b1, None], S[None, :])
                hi = np.minimum(E[b0:b1, None], E[None, :])
                hit = (hi > lo) & (O[b0:b1, None] != O[None, :])
                ai, bi = np.nonzero(hit)
                if ai.size:
                    pa = ids[O[ai + b0]]
                    pb = ids[O[bi]]
                    keep = pa != pb
                    if keep.any():
                        pa, pb = pa[keep], pb[keep]
                        sink.append(np.minimum(pa, pb) * NP + np.maximum(pa, pb))
                del lo, hi, hit, ai, bi

    def uniq(chunks):
        if not chunks:
            return np.zeros(0, dtype=np.int64)
        a = np.concatenate(chunks)
        a.sort()
        return a[np.r_[True, a[1:] != a[:-1]]]

    guar = uniq(guar_chunks); del guar_chunks
    poss = uniq(poss_chunks); del poss_chunks
    cocont = uniq(cocont_chunks); del cocont_chunks
    poss_only = poss[~np.isin(poss, guar)]
    zero = int(cocont.size) - int(guar.size) - int(poss_only.size)

    rc = receipt["co_tenure_status_counts"]
    result["independent_co_tenure_counts"] = {
        "candidate_same_container_pairs_distinct": int(cocont.size),
        "GUARANTEED": int(guar.size),
        "POSSIBLE_ONLY": int(poss_only.size),
        "ZERO_OVERLAP_rejected": zero,
        "receipt_GUARANTEED": rc["GUARANTEED"],
        "receipt_POSSIBLE_ONLY": rc["POSSIBLE_ONLY"],
        "receipt_ZERO_OVERLAP": rc["ZERO_OVERLAP"],
        "match": (int(guar.size) == rc["GUARANTEED"] and int(poss_only.size) == rc["POSSIBLE_ONLY"]
                  and zero == rc["ZERO_OVERLAP"]),
        "algorithm": "full C(n,2) per container, run-level numpy broadcasting; the builder "
                     "used an interval sweep line - different code path, same answer required",
    }
    if not result["independent_co_tenure_counts"]["match"]:
        fail("co_tenure_counts", result["independent_co_tenure_counts"])

    # ---- edge file invariants + independent components ---------------------------
    edges_path = primary / "staffer_social_edges.ndjson.gz"
    layer_counts = Counter()
    status_counts = Counter()
    prec_counts = Counter()
    self_loops = 0
    bad_weight = 0
    bad_flags = 0
    bad_policy_overlay = 0
    bad_revolving_overlay = 0
    seq_edges = 0
    member_member = 0
    node_ix: dict[str, int] = {}
    node_kinds, published_eigen = [], []
    published_office, published_office_distinct = [], []
    published_office_strengths = []
    non_person_nodes: list[str] = []
    legacy_bridging_fields = 0
    published_pr = defaultdict(list)
    for node in rows(primary / 'staffer_social_node_scores.ndjson.gz'):
        if node['node_id'] in node_ix:
            fail('duplicate_published_node', node['node_id'])
            continue
        node_ix[node['node_id']] = len(node_ix)
        node_kinds.append(node['node_kind'])
        # INV: node_scores is PERSONS ONLY (D-022).
        if node['node_kind'] != 'person' or not str(node['node_id']).startswith('person:'):
            non_person_nodes.append(node['node_id'])
        if 'bridging_diversity_exploratory' in node:
            legacy_bridging_fields += 1
        published_eigen.append(node['eigenvector_component_local_exploratory'])
        published_office.append(node['office_diversity_exploratory'])
        published_office_distinct.append(node['office_diversity_distinct_offices'])
        published_office_strengths.append(node.get('office_connection_strengths'))
        values = {float(value['alpha']): value['score'] for value in node['connectedness_pagerank_exploratory']}
        for alpha in (.7, .85, .95):
            published_pr[alpha].append(values.get(alpha, float('nan')))
    result['node_scores_are_persons_only'] = {
        'published_nodes': len(node_ix),
        'non_person_rows': len(non_person_nodes),
        'non_person_examples': non_person_nodes[:5],
        'rows_still_carrying_bridging_diversity_exploratory': legacy_bridging_fields,
        'verifier_person_universe': NP,
        'match': (not non_person_nodes and not legacy_bridging_fields
                  and len(node_ix) == NP),
    }
    if non_person_nodes:
        fail('node_scores_contains_a_non_person_row', non_person_nodes[:5])
    if legacy_bridging_fields:
        fail('node_scores_still_carries_bridging_diversity', legacy_bridging_fields)
    if len(node_ix) != NP:
        fail('node_scores_row_count', {'published': len(node_ix), 'verifier': NP})
    from array import array as _arr
    eu, ev = _arr("l"), _arr("l")
    ew = _arr("d")
    elayer = _arr('b')
    layer_codes = {'co_tenure': 0, 'revolving': 1, 'membership': 2, 'policy_area': 3}
    # independent ablation bookkeeping, driven off the EMITTED container_kinds field
    # rather than the builder's internal bucket bitmask
    pu, pv = _arr("l"), _arr("l")
    p_has_comm, p_has_member, p_has_noncomm = _arr("b"), _arr("b"), _arr("b")
    person_ix: dict[str, int] = {}
    side_values_seen: set = set()
    emitted_policy_source_assertions: set[tuple[str, str, str]] = set()
    emitted_pairs: set[int] = set()
    guar_sample_target = {}
    rnd = random.Random(SAMPLE_SEED)
    reservoir: list[dict[str, Any]] = []
    seen_guar = 0
    possible_sample, seen_possible = [], 0
    possible_random = random.Random(SAMPLE_SEED + 1)
    non_person_endpoints = 0
    non_co_tenure_rows = 0
    operator_containers: list[tuple] = []
    operator_container_shares = []
    attribution_failures = 0
    for e in rows(edges_path):
        layer_counts[e["layer"]] += 1
        status_counts[(e["layer"], e.get("status"))] += 1
        if e.get("date_precision"):
            prec_counts[e["date_precision"]] += 1
        if e["subject_id"] == e["object_id"]:
            self_loops += 1
        if e["review_status"] != "REVIEW_REQUIRED" or e["canonical_employment_promoted"] is not False \
                or e["canonical_eligible"] is not False:
            bad_flags += 1
        if e["layer"] == "sequence" or e.get("direction") == "directed":
            seq_edges += 1
        if e["subject_kind"] == "container" and e["object_kind"] == "container":
            member_member += 1
        # INV: the edges file is the operator, and the operator is person-person only.
        if e["layer"] != "co_tenure":
            non_co_tenure_rows += 1
        if not (
            e.get("subject_kind") == "person"
            and e.get("object_kind") == "person"
            and str(e["subject_id"]).startswith("person:")
            and str(e["object_id"]).startswith("person:")
        ):
            non_person_endpoints += 1
        if e["layer"] == "co_tenure":
            if e["status"] == "GUARANTEED":
                if not (e["guaranteed_days"] > 0 and e["w_lower"] > 0):
                    bad_weight += 1
                seen_guar += 1
                factor = (receipt.get('ranking_math') or {}).get('shared_role_factor')
                if not attribution_valid(e, factor):
                    attribution_failures += 1
                if len(reservoir) < SAMPLE_SIZE:
                    reservoir.append(e)
                else:
                    r = rnd.randrange(seen_guar)
                    if r < SAMPLE_SIZE:
                        reservoir[r] = e
            elif e["status"] == "POSSIBLE_ONLY":
                seen_possible += 1
                slot = len(possible_sample) if len(possible_sample) < SAMPLE_SIZE else possible_random.randrange(seen_possible)
                if len(possible_sample) < SAMPLE_SIZE:
                    possible_sample.append(e)
                elif slot < SAMPLE_SIZE:
                    possible_sample[slot] = e
                if e["guaranteed_days"] != 0 or e["w_lower"] != 0.0 or e["w_tiered_lower"] != 0.0:
                    bad_weight += 1
        if e['subject_id'] not in node_ix or e['object_id'] not in node_ix:
            fail('edge_endpoint_absent_from_node_universe', e['edge_id'])
            continue
        a, b = node_ix[e['subject_id']], node_ix[e['object_id']]
        w = e["w_tiered_lower"]
        if w > 0:
            eu.append(a); ev.append(b); ew.append(w)
            elayer.append(layer_codes[e['layer']])
            if e["layer"] == "co_tenure" and e["status"] == "GUARANTEED":
                kinds = set(e.get("container_kinds") or ())
                operator_containers.append(tuple(e.get("container_ids") or ()))
                operator_container_shares.append(tuple(e.get('container_mass_shares') or ()))
                pa = person_ix.setdefault(e["subject_id"], len(person_ix))
                pb = person_ix.setdefault(e["object_id"], len(person_ix))
                pu.append(pa); pv.append(pb)
                p_has_comm.append(1 if "committee" in kinds else 0)
                p_has_member.append(1 if "member_office" in kinds else 0)
                p_has_noncomm.append(1 if (kinds - {"committee"}) else 0)

    result["edge_file_invariants"] = {
        "duration_attribution_or_weight_failures": attribution_failures,
        "layer_counts": dict(layer_counts),
        "status_counts": {f"{k[0]}/{k[1]}": v for k, v in status_counts.items()},
        "date_precision_counts": dict(prec_counts),
        "self_loops": self_loops,
        "rows_with_bad_weight_for_status": bad_weight,
        "rows_with_non_review_or_promoted_flags": bad_flags,
        "person_person_SEQUENCE_edges": seq_edges,
        "container_container_member_member_edges": member_member,
        "rows_in_a_layer_other_than_co_tenure": non_co_tenure_rows,
        "rows_with_a_non_person_endpoint": non_person_endpoints,
        "scope": ("the edges file is the OPERATOR plus its zero-weight POSSIBLE_ONLY "
                  "companions; grouping layers live in their own files"),
    }
    expected_layer_counts = {
        "co_tenure": (
            receipt["edge_counts"]["co_tenure_guaranteed"]
            + receipt["edge_counts"]["co_tenure_possible_only_zero_weight"]
        ),
    }
    result["edge_file_invariants"]["expected_layer_counts"] = expected_layer_counts
    result["edge_file_invariants"]["layer_counts_match_receipt"] = (
        dict(layer_counts) == expected_layer_counts
    )
    for name, value in (("self_loops", self_loops), ("bad_weight", bad_weight),
                        ("duration_attribution_or_weight", attribution_failures),
                        ("bad_flags", bad_flags), ("sequence_person_person_edges", seq_edges),
                        ("member_member_edges", member_member),
                        ("edges_file_contains_a_non_co_tenure_layer", non_co_tenure_rows),
                        ("operator_edge_with_a_non_person_endpoint", non_person_endpoints)):
        if value:
            fail(name, value)
    if dict(layer_counts) != expected_layer_counts:
        fail("layer_counts", {"observed": dict(layer_counts), "expected": expected_layer_counts})

    # ---- grouping layers: separate files, none of them in the operator -------------
    grouping_files = {
        "membership_layer": "staffer_social_membership_layer.ndjson.gz",
        "revolving_layer": "staffer_social_revolving_layer.ndjson.gz",
        "policy_layer": "staffer_social_policy_layer.ndjson.gz",
    }
    grouping_counts = Counter()
    grouping_kind_counts = Counter()
    grouping_operator_rows = 0
    grouping_bad_flags = 0
    membership_cells_emitted: set[tuple[str, str]] = set()
    policy_pairs_emitted: set[tuple[str, str]] = set()
    registrant_pairs_emitted: set[tuple[str, str, str]] = set()
    revolving_container_org_emitted: set[tuple[str, str, str]] = set()
    emitted_group_person_ids: set[str] = set()
    for role, name in grouping_files.items():
        path = primary / name
        if not path.exists():
            fail("grouping_layer_missing", name)
            continue
        for row in rows(path):
            grouping_counts[role] += 1
            grouping_kind_counts[(row.get("layer"), row.get("record_kind"))] += 1
            if row.get("operator_included") is not False or row.get("operator_weight") != 0.0:
                grouping_operator_rows += 1
            if (row.get("review_status") != "REVIEW_REQUIRED"
                    or row.get("canonical_eligible") is not False
                    or row.get("canonical_employment_promoted") is not False):
                grouping_bad_flags += 1
            if str(row.get("subject_id", "")).startswith("person:"):
                emitted_group_person_ids.add(str(row["subject_id"]))
            if row.get("record_kind") == "person_container":
                membership_cells_emitted.add((row["subject_id"], row["object_id"]))
            elif row.get("record_kind") == "person_policy_area":
                policy_pairs_emitted.add((row["subject_id"], row["object_id"]))
                source_uuids = row.get("source_profile_uuids") or [row.get("source_profile_uuid")]
                for source_uuid in source_uuids:
                    if source_uuid:
                        emitted_policy_source_assertions.add(
                            (
                                str(row["subject_id"]),
                                " ".join(str(row.get("issue_area") or "").casefold().split()),
                                str(source_uuid),
                            )
                        )
                if not (
                    row.get("subject_kind") == "person"
                    and row.get("object_kind") == "policy_area"
                    and row.get("status") == "CURRENT_SNAPSHOT_UNDATED"
                    and row.get("duration_weight") == 0.0
                    and row.get("categorical_membership_weight") == 1.0
                ):
                    bad_policy_overlay += 1
            elif row.get("record_kind") == "person_registrant":
                registrant_pairs_emitted.add(
                    (row["subject_id"], row["object_id"], str(row.get("status")))
                )
            elif row.get("record_kind") == "container_organization":
                revolving_container_org_emitted.add(
                    (row["subject_id"], row["object_id"], str(row.get("status")))
                )
                if not (
                    row.get("subject_kind") == "container"
                    and row.get("object_kind") == "organization"
                ):
                    bad_revolving_overlay += 1
            else:
                fail("grouping_layer_unknown_record_kind", row.get("record_kind"))

    # membership conservation: recomputed from the SPANS file, not from the receipt
    membership_conserved = (
        grouping_counts["membership_layer"] == len(pc_core)
        and len(membership_cells_emitted) == len(pc_core)
    )
    # policy conservation: recomputed from the Politico source restricted to the universe
    result["grouping_layer_conservation"] = {
        "rows_by_file": dict(grouping_counts),
        "rows_by_layer_and_record_kind": {
            f"{k[0]}/{k[1]}": v for k, v in sorted(grouping_kind_counts.items(), key=str)
        },
        "rows_declaring_operator_inclusion": grouping_operator_rows,
        "rows_with_non_review_or_promoted_flags": grouping_bad_flags,
        "membership_rows": grouping_counts["membership_layer"],
        "membership_expected_person_container_cells": len(pc_core),
        "membership_distinct_pairs_emitted": len(membership_cells_emitted),
        "membership_conserved": membership_conserved,
        "policy_rows": grouping_counts["policy_layer"],
        "policy_distinct_pairs_emitted": len(policy_pairs_emitted),
        "revolving_rows": grouping_counts["revolving_layer"],
        "revolving_container_organization_rows": len(revolving_container_org_emitted),
        "revolving_person_registrant_rows": len(registrant_pairs_emitted),
        "receipt_declared": receipt.get("grouping_layers"),
        "method": (
            "membership is recomputed from hill_person_office_spans (the same source the "
            "person and container universes come from); policy is recomputed from the "
            "Politico bridge input below; revolving source rows are recounted from the "
            "exploratory tier file and the receipt's own mapped/orphan accounting is "
            "required to close against that recount"
        ),
    }
    if grouping_operator_rows:
        fail("grouping_layer_row_declares_operator_inclusion", grouping_operator_rows)
    if grouping_bad_flags:
        fail("grouping_layer_flags", grouping_bad_flags)
    if not membership_conserved:
        fail("grouping_layer_membership_not_conserved",
             {"rows": grouping_counts["membership_layer"], "cells": len(pc_core)})
    if bad_policy_overlay:
        fail("policy_area_overlay_violations", bad_policy_overlay)
    if bad_revolving_overlay:
        fail("revolving_overlay_violations", bad_revolving_overlay)

    # revolving source-side recount, independent of the builder's resolution
    revolving_source_rows = 0
    for row in rows(declared_inputs["exploratory_revolving_edges"]):
        if row.get("layer") == "revolving":
            revolving_source_rows += 1
    declared_revolving = receipt.get("revolving_resolution") or {}
    mapped_by_method = sum((declared_revolving.get("mapped_source_rows_by_resolution_method") or {}).values())
    accounting_closes = (
        declared_revolving.get("source_rows") == revolving_source_rows
        and mapped_by_method + int(declared_revolving.get("orphan_source_rows") or 0)
        == revolving_source_rows
    )
    result["revolving_source_accounting"] = {
        "verifier_source_rows": revolving_source_rows,
        "receipt_source_rows": declared_revolving.get("source_rows"),
        "receipt_mapped_source_rows": mapped_by_method,
        "receipt_orphan_source_rows": declared_revolving.get("orphan_source_rows"),
        "closes": bool(accounting_closes),
    }
    if not accounting_closes:
        fail("revolving_source_accounting", result["revolving_source_accounting"])

    # person-registrant rows re-derived from the emitted container->organization rows
    lda_people: dict[str, list[str]] = defaultdict(list)
    for spine_id, lda_id in spine_lda.items():
        if spine_id in persons:
            lda_people[lda_id].append(f"person:{spine_id}")
    expected_registrant: set[tuple[str, str, str]] = set()
    for row in rows(primary / "staffer_social_revolving_layer.ndjson.gz"):
        if row.get("record_kind") != "container_organization":
            continue
        for lda_id in row.get("contributing_lda_people") or []:
            for node_id in lda_people.get(str(lda_id), ()):
                expected_registrant.add((node_id, row["object_id"], str(row.get("status"))))
    result["person_registrant_reconciliation"] = {
        "expected": len(expected_registrant),
        "emitted": len(registrant_pairs_emitted),
        "missing": len(expected_registrant - registrant_pairs_emitted),
        "extra": len(registrant_pairs_emitted - expected_registrant),
        "match": expected_registrant == registrant_pairs_emitted,
        "method": ("re-joined from the emitted container->organization rows' "
                   "contributing_lda_people through hill_person_spine.lda_source_person_id"),
    }
    if expected_registrant != registrant_pairs_emitted:
        fail("person_registrant_rows", result["person_registrant_reconciliation"])

    # ---- groups roster ------------------------------------------------------------
    groups_by_kind = Counter()
    group_ids: set[str] = set()
    group_side_violations = []
    duplicate_groups = 0
    committee_sides_seen: set = set()
    groups_missing_fields = 0
    for row in rows(primary / "staffer_social_groups.ndjson.gz"):
        if row["group_id"] in group_ids:
            duplicate_groups += 1
        group_ids.add(row["group_id"])
        groups_by_kind[row["group_kind"]] += 1
        if row.get("operator_included") is not False:
            fail("groups_row_declares_operator_inclusion", row["group_id"])
        for field in ("group_id", "group_kind", "name", "member_bioguide", "people_count"):
            if field not in row:
                groups_missing_fields += 1
        if row["group_kind"] == "container":
            side = row.get("container_side")
            if row.get("container_kind") == "committee":
                committee_sides_seen.add(side)
                if side not in ("MAJ", "MIN", "BIPARTISAN", "UNKNOWN"):
                    group_side_violations.append({"group_id": row["group_id"], "side": side})
            elif side is not None:
                group_side_violations.append(
                    {"group_id": row["group_id"], "side": side,
                     "why": "side set on a non-committee container"})
    expected_groups = {
        "container": NC,
        "organization": group_universe.get("organization"),
        "policy_area": group_universe.get("policy_area"),
    }
    result["groups_roster"] = {
        "rows_by_kind": dict(groups_by_kind),
        "expected_rows_by_kind": expected_groups,
        "duplicate_group_ids": duplicate_groups,
        "rows_missing_a_required_field": groups_missing_fields,
        "committee_sides_seen": sorted(x for x in committee_sides_seen if x),
        "side_violations": group_side_violations[:10],
        "match": (
            groups_by_kind.get("container") == NC
            and dict(groups_by_kind) == {k: v for k, v in expected_groups.items() if v is not None}
            and not duplicate_groups
            and not groups_missing_fields
            and not group_side_violations
        ),
    }
    if not result["groups_roster"]["match"]:
        fail("groups_roster", result["groups_roster"])

    # ---- spine id namespace: re-derive the builder's remap decision ---------------
    # Independent of the builder: read the bridge receipt's bound spine sha256 directly,
    # compare it to the spine this generation declares, and rebuild the map if one was
    # used.  A receipt that claims no remap while the shas differ is a hard failure.
    link_receipt_path = declared_inputs.get("politico_direct_link_receipt")
    link_receipt = json.loads(Path(link_receipt_path).read_text(encoding="utf-8")) if link_receipt_path else {}
    spine_roles = {"hill_person_spine.ndjson.gz": "hill_person_spine",
                   "hill_person_office_spans.ndjson.gz": "hill_person_office_spans"}
    binding_rows, binding_matches = [], True
    for raw_path, meta in (link_receipt.get("inputs") or {}).items():
        name = str(raw_path).replace("\\", "/").rsplit("/", 1)[-1]
        if name not in spine_roles or not isinstance(meta, dict):
            continue
        current = declared_inputs.get(spine_roles[name])
        current_sha = sha256_file(Path(current)) if current and Path(current).exists() else None
        same = meta.get("sha256") == current_sha
        binding_matches = binding_matches and same
        binding_rows.append({"file": name, "links_bound_sha256": meta.get("sha256"),
                             "build_spine_sha256": current_sha, "same_generation": bool(same)})
    id_map: dict[str, str] = {}
    map_path = declared_inputs.get("spine_id_map")
    if map_path is not None and Path(map_path).exists():
        for row in rows(Path(map_path)):
            id_map[row["legacy_person_id"]] = row["person_id"]
    remap_active = bool(id_map) and not binding_matches
    declared_binding = receipt.get("spine_id_binding") or {}
    result["spine_id_binding_recheck"] = {
        "verifier_bindings": binding_rows,
        "verifier_links_bind_this_spine": bool(binding_matches),
        "receipt_links_bind_this_spine": declared_binding.get("links_bind_the_spine_being_built_against"),
        "verifier_remap_active": remap_active,
        "receipt_remap_applied": declared_binding.get("remap_applied"),
        "id_map_rows": len(id_map),
        "match": (
            bool(binding_rows)
            and declared_binding.get("links_bind_the_spine_being_built_against") == bool(binding_matches)
            and bool(declared_binding.get("remap_applied")) == remap_active
        ),
    }
    if not result["spine_id_binding_recheck"]["match"]:
        fail("spine_id_binding", result["spine_id_binding_recheck"])

    def remap(value):
        if remap_active and isinstance(value, str) and value in id_map:
            return id_map[value]
        return value

    # ---- exact Politico policy source -> emitted-row reconciliation --------------
    expected_policy_source_assertions: set[tuple[str, str, str]] = set()
    policy_source_path = declared_inputs.get("politico_direct_policy_memberships")
    if policy_source_path is None:
        fail("politico_policy_source_input", "missing declared input")
    else:
        for row in rows(policy_source_path):
            spine_id = remap(row.get("spine_person_id"))
            issue = row.get("issue_area")
            source_uuid = row.get("source_profile_uuid")
            if (
                isinstance(spine_id, str)
                and spine_id in persons
                and isinstance(issue, str)
                and issue.strip()
                and source_uuid
            ):
                expected_policy_source_assertions.add(
                    (
                        f"person:{spine_id}",
                        " ".join(issue.casefold().split()),
                        str(source_uuid),
                    )
                )
    missing_policy = expected_policy_source_assertions - emitted_policy_source_assertions
    extra_policy = emitted_policy_source_assertions - expected_policy_source_assertions
    result["politico_policy_source_to_edge_reconciliation"] = {
        "source_assertions": len(expected_policy_source_assertions),
        "emitted_edge_source_assertions": len(emitted_policy_source_assertions),
        "missing": len(missing_policy),
        "extra": len(extra_policy),
        "missing_examples": sorted(missing_policy)[:5],
        "extra_examples": sorted(extra_policy)[:5],
        "match": not missing_policy and not extra_policy,
        "method": (
            "independently expand each emitted person-policy edge by its bound "
            "source_profile_uuids and compare the exact triples to the bridge input"
        ),
    }
    if missing_policy or extra_policy:
        fail(
            "politico_policy_source_to_edge",
            {"missing": len(missing_policy), "extra": len(extra_policy)},
        )

    # ---- exact, separate Politico review-layer reconciliation -------------------
    review_file_entry = next(
        (
            entry
            for entry in receipt.get("files", [])
            if entry.get("role") == "staffer_social_politico_review_layers"
        ),
        None,
    )
    review_roles = {
        "politico_current_committee_assertions",
        "politico_profile_employment_assertions",
        "politico_profile_education_assertions",
        "politico_profile_policy_deltas",
        "politico_explicit_committee_side_assertions",
    }
    review_inputs_present = review_roles <= set(declared_inputs)

    projection_fields = (
        "layer",
        "source_profile_uuid",
        "spine_person_id",
        "subject_id",
        "subject_kind",
        "object_id",
        "object_kind",
        "history_ordinal",
        "employer",
        "title",
        "date_text",
        "institution",
        "degree",
        "issue_area",
        "delta",
        "source_card_present",
        "live_profile_present",
        "chamber",
        "committee_signature",
        "payroll_office_key",
        "role",
        "party_derived_side",
        "explicit_side",
        "agrees_with_party_derived_side",
        "mapping_status",
    )

    def subject_projection(row):
        spine_id = remap(row.get("spine_person_id"))
        if isinstance(spine_id, str) and spine_id in persons:
            return f"person:{spine_id}", "person"
        return f"politico-profile:{row.get('source_profile_uuid')}", "source_profile"

    def projected(row):
        return tuple(row.get(field) for field in projection_fields)

    expected_review: set[tuple] = set()
    source_review_counts = Counter()
    if review_inputs_present:
        for row in rows(declared_inputs["politico_profile_employment_assertions"]):
            subject_id, subject_kind = subject_projection(row)
            employer = str(row.get("employer") or "")
            expected_review.add(
                projected(
                    {
                        "layer": "politico_employment_history",
                        "source_profile_uuid": row.get("source_profile_uuid"),
                        "spine_person_id": remap(row.get("spine_person_id")),
                        "subject_id": subject_id,
                        "subject_kind": subject_kind,
                        "object_id": "politico-employer:"
                        + hashlib.sha256(employer.casefold().encode("utf-8")).hexdigest()[:24],
                        "object_kind": "source_employer",
                        "history_ordinal": row.get("history_ordinal"),
                        "employer": employer,
                        "title": row.get("title"),
                        "date_text": row.get("date_text"),
                    }
                )
            )
            source_review_counts["politico_employment_history"] += 1
        for row in rows(declared_inputs["politico_profile_education_assertions"]):
            subject_id, subject_kind = subject_projection(row)
            institution = str(row.get("institution") or "")
            expected_review.add(
                projected(
                    {
                        "layer": "politico_education_history",
                        "source_profile_uuid": row.get("source_profile_uuid"),
                        "spine_person_id": remap(row.get("spine_person_id")),
                        "subject_id": subject_id,
                        "subject_kind": subject_kind,
                        "object_id": "politico-institution:"
                        + hashlib.sha256(institution.casefold().encode("utf-8")).hexdigest()[:24],
                        "object_kind": "source_institution",
                        "history_ordinal": row.get("history_ordinal"),
                        "institution": institution,
                        "degree": row.get("degree"),
                        "date_text": row.get("date_text"),
                    }
                )
            )
            source_review_counts["politico_education_history"] += 1
        for row in rows(declared_inputs["politico_profile_policy_deltas"]):
            subject_id, subject_kind = subject_projection(row)
            issue = str(row.get("issue_area") or "")
            normalized_issue = " ".join(issue.casefold().split())
            expected_review.add(
                projected(
                    {
                        "layer": "politico_policy_delta",
                        "source_profile_uuid": row.get("source_profile_uuid"),
                        "spine_person_id": remap(row.get("spine_person_id")),
                        "subject_id": subject_id,
                        "subject_kind": subject_kind,
                        "object_id": "policy:politico:"
                        + hashlib.sha256(normalized_issue.encode("utf-8")).hexdigest()[:24],
                        "object_kind": "policy_area",
                        "issue_area": issue,
                        "delta": row.get("delta"),
                        "source_card_present": row.get("source_card_present"),
                        "live_profile_present": row.get("live_profile_present"),
                    }
                )
            )
            source_review_counts["politico_policy_delta"] += 1

        def add_expected_committee(row, layer):
            subject_id, subject_kind = subject_projection(row)
            chamber = str(row.get("chamber") or "")
            office_keys = [str(value) for value in row.get("payroll_office_keys") or []]
            for office_key in office_keys or [""]:
                normalized = normalized_container(office_key) if office_key else ""
                resolved = f"{chamber}\x00{normalized}" in containers if normalized else False
                object_id = (
                    f"container:office:{chamber}:{normalized}"
                    if resolved
                    else "politico-committee:"
                    + hashlib.sha256(
                        f"{chamber}\x00{row.get('committee_signature')}".encode("utf-8")
                    ).hexdigest()[:24]
                )
                expected_review.add(
                    projected(
                        {
                            "layer": layer,
                            "source_profile_uuid": row.get("source_profile_uuid"),
                            "spine_person_id": remap(row.get("spine_person_id")),
                            "subject_id": subject_id,
                            "subject_kind": subject_kind,
                            "object_id": object_id,
                            "object_kind": "container" if resolved else "source_committee",
                            "chamber": row.get("chamber"),
                            "committee_signature": row.get("committee_signature"),
                            "payroll_office_key": office_key or None,
                            "role": row.get("role"),
                            "party_derived_side": row.get("party_derived_side")
                            or row.get("side_at_observation"),
                            "explicit_side": row.get("explicit_side"),
                            "agrees_with_party_derived_side": row.get(
                                "agrees_with_party_derived_side"
                            ),
                            "mapping_status": row.get("mapping_status")
                            or ("EXACT_PAYROLL_CONTAINER" if resolved else "UNRESOLVED_CONTAINER"),
                        }
                    )
                )
                source_review_counts[layer] += 1

        for row in rows(declared_inputs["politico_current_committee_assertions"]):
            add_expected_committee(row, "politico_current_committee")
        for row in rows(declared_inputs["politico_explicit_committee_side_assertions"]):
            add_expected_committee(row, "politico_committee_side_explicit")

    actual_review: set[tuple] = set()
    actual_review_counts = Counter()
    bad_review_flags = 0
    duplicate_review_ids = 0
    review_ids = set()
    if review_file_entry is not None:
        for row in rows(primary / review_file_entry["path"]):
            actual_review_counts[str(row.get("layer"))] += 1
            actual_review.add(projected(row))
            assertion_id = row.get("assertion_id")
            if assertion_id in review_ids:
                duplicate_review_ids += 1
            review_ids.add(assertion_id)
            if not (
                row.get("operator_included") is False
                and row.get("operator_weight") == 0.0
                and row.get("w_tiered_lower") == 0.0
                and row.get("review_status") == "REVIEW_REQUIRED"
                and row.get("canonical_eligible") is False
                and row.get("canonical_identity_promoted") is False
                and row.get("canonical_employment_promoted") is False
            ):
                bad_review_flags += 1
    missing_review = expected_review - actual_review
    extra_review = actual_review - expected_review
    history_assertions = (
        actual_review_counts["politico_employment_history"]
        + actual_review_counts["politico_education_history"]
    )
    declared_review_block = receipt.get("politico_review_layer_resolution") or {}
    result["politico_review_layer_reconciliation"] = {
        "inputs_present": review_inputs_present,
        "artifact_present": review_file_entry is not None,
        "source_counts": dict(sorted(source_review_counts.items())),
        "artifact_counts": dict(sorted(actual_review_counts.items())),
        "expected_distinct_assertions": len(expected_review),
        "actual_distinct_assertions": len(actual_review),
        "missing": len(missing_review),
        "extra": len(extra_review),
        "duplicate_assertion_ids": duplicate_review_ids,
        "bad_review_or_operator_flags": bad_review_flags,
        "receipt_complete_history_assertions": receipt.get("complete_history_assertions"),
        "rederived_complete_history_assertions": history_assertions,
        "match": (
            review_inputs_present == (review_file_entry is not None)
            and not missing_review
            and not extra_review
            and source_review_counts == actual_review_counts
            and not duplicate_review_ids
            and not bad_review_flags
            and receipt.get("complete_history_assertions") == history_assertions
            and declared_review_block.get("rows_by_layer", {})
            == dict(sorted(actual_review_counts.items()))
            and receipt.get("edge_counts", {}).get("politico_review_only", 0)
            == sum(actual_review_counts.values())
        ),
    }
    if not result["politico_review_layer_reconciliation"]["match"]:
        fail(
            "politico_review_layers",
            {
                "missing": len(missing_review),
                "extra": len(extra_review),
                "duplicate_ids": duplicate_review_ids,
                "bad_flags": bad_review_flags,
            },
        )

    named_checks = receipt.get("named_regression_checks", {})
    result["named_regression_checks"] = named_checks
    result["named_regression_gate_scope"] = (
        "SKIPPED - this generation declares limited_run, so the named people are outside "
        "the person prefix by construction; the gate is hard for any unlimited build"
        if limited_run else "enforced"
    )
    if not limited_run:
        for name in ("Gordon_Holzberg", "Stephanie_Belk"):
            if named_checks.get(name, {}).get("status") != "PASS":
                fail("named_regression", name)
    if receipt.get("status") != "PASS" or receipt.get("failures"):
        fail("builder_receipt_status", {
            "status": receipt.get("status"), "failures": receipt.get("failures")
        })

    # ---- INV: the overlap test fires -------------------------------------------
    rejected = int(receipt["edge_counts"]["co_tenure_zero_overlap_REJECTED_never_emitted"])
    result["zero_overlap_rejection_is_live"] = {
        "pairs_REJECTED_for_no_overlap": rejected,
        "candidate_same_container_pairs_distinct": (
            receipt.get("overlap_rule_check", {}).get("candidate_same_container_pairs_distinct")
        ),
        "rule": "D-019 - zero means the overlap test is not firing",
        "match": rejected > 0,
    }
    if rejected <= 0:
        fail("zero_overlap_rejected_count_is_zero", rejected)

    # ---- INV: the component histogram is present and closes on the person count --
    op_block = receipt.get("operator") or {}
    histogram = op_block.get("component_size_histogram")
    histogram_ok = isinstance(histogram, dict) and bool(histogram)
    histogram_total = (
        sum(int(size) * int(count) for size, count in histogram.items())
        if histogram_ok else None
    )
    result["component_histogram"] = {
        "present": histogram_ok,
        "distinct_sizes": len(histogram) if histogram_ok else 0,
        "receipt_distinct_component_sizes": op_block.get("distinct_component_sizes"),
        "persons_covered": histogram_total,
        "person_nodes": NP,
        "components": op_block.get("components"),
        "component_count_matches_histogram": (
            sum(int(count) for count in histogram.values()) == op_block.get("components")
            if histogram_ok else False
        ),
        "match": bool(
            histogram_ok
            and histogram_total == NP
            and len(histogram) == op_block.get("distinct_component_sizes")
            and sum(int(count) for count in histogram.values()) == op_block.get("components")
        ),
    }
    if not result["component_histogram"]["match"]:
        fail("component_size_histogram", result["component_histogram"])

    # ---- INV: the restart distribution is uniform over persons -------------------
    teleport_block = op_block.get("teleport") or {}
    result["uniform_teleport"] = {
        "declared": teleport_block,
        "expected_mass_per_person": 1.0 / float(NP) if NP else None,
        "match": (
            teleport_block.get("kind") == "uniform_over_persons"
            and NP > 0
            and abs(float(teleport_block.get("mass_per_person") or 0.0) - 1.0 / float(NP)) <= 1e-15
        ),
    }
    if not result["uniform_teleport"]["match"]:
        fail("teleport_is_not_uniform_over_persons", result["uniform_teleport"])

    # ---- exact re-derivation of guaranteed_days on the sample --------------------
    inv_person = {v: k for k, v in persons.items()}
    pid_of = {k: v for k, v in persons.items()}
    # Only ELIGIBLE containers can contribute guaranteed overlap days to an edge, so the
    # naive re-computation must see the same universe the sweep did.
    per_person_containers: dict[int, dict[int, list]] = defaultdict(dict)
    for (p, c), runs in pc_core.items():
        if c not in eligible_containers:
            continue
        per_person_containers[p][c] = union_runs(runs)
    mismatch = []
    for e in reservoir:
        a = pid_of[e["subject_id"].split("person:", 1)[1]]
        b = pid_of[e["object_id"].split("person:", 1)[1]]
        segs = []
        shared = set(per_person_containers[a]) & set(per_person_containers[b])
        for c in shared:
            ua, ub = per_person_containers[a][c], per_person_containers[b][c]
            container_segments = []
            for s1, e1 in ua:
                for s2, e2 in ub:
                    lo, hi = max(s1, s2), min(e1, e2)
                    if hi > lo:
                        segs.append((lo, hi))
                        container_segments.append((lo, hi))
            container_days = sum(hi - lo for lo, hi in union_runs(container_segments))
            if container_days:
                cid_key = next(key for key, value in containers.items() if value == c)
                chamber, office_key = cid_key.split('\x00', 1)
                cid = f'container:office:{chamber}:{office_key}'
                if cid not in e['container_ids']:
                    mismatch.append({'edge_id': e['edge_id'], 'missing_container': cid})
                else:
                    offset = e['container_ids'].index(cid)
                    if (e['container_guaranteed_days'][offset] != container_days or
                            e['container_shared_role'][offset] != ((a, c) in pc_shared or (b, c) in pc_shared)):
                        mismatch.append({'edge_id': e['edge_id'], 'container_support_mismatch': cid})
        days = sum(hi - lo for lo, hi in union_runs(segs))
        if days != e["guaranteed_days"]:
            mismatch.append({"edge_id": e["edge_id"], "emitted": e["guaranteed_days"], "verifier": days})
    result["guaranteed_days_sample_recomputation"] = {
        "sample_size": len(reservoir), "seed": SAMPLE_SEED,
        "mismatches": len(mismatch), "examples": mismatch[:5],
        "method": "naive O(runs_a x runs_b) intersection then union, no sweep line",
    }
    if mismatch:
        fail("guaranteed_days_sample", len(mismatch))

    envelope_by_person = defaultdict(dict)
    for (person, container), runs in pc_env.items():
        if container not in eligible_containers:
            continue
        envelope_by_person[person][container] = union_runs(runs)
    mismatch = []
    for edge in possible_sample:
        a = pid_of[edge['subject_id'].removeprefix('person:')]
        b = pid_of[edge['object_id'].removeprefix('person:')]
        intervals = []
        for container in envelope_by_person[a].keys() & envelope_by_person[b].keys():
            for start_a, end_a in envelope_by_person[a][container]:
                for start_b, end_b in envelope_by_person[b][container]:
                    lo, hi = max(start_a, start_b), min(end_a, end_b)
                    if hi > lo:
                        intervals.append((lo, hi))
        days = sum(hi-lo for lo, hi in union_runs(intervals))
        if days != edge['possible_days']:
            mismatch.append({'edge_id': edge['edge_id'], 'emitted': edge['possible_days'], 'verifier': days})
    result['possible_days_sample_recomputation'] = {
        'sample_size': len(possible_sample), 'seed': SAMPLE_SEED + 1,
        'mismatches': len(mismatch), 'examples': mismatch[:5],
        'method': 'source-envelope pairwise intersection then union across every shared container'}
    if mismatch:
        fail('possible_days_sample', len(mismatch))
    del envelope_by_person

    # ---- independent connected components from the emitted edges -----------------
    NN = len(node_ix)
    if eu:
        g = sparse.coo_matrix((np.ones(len(eu)), (np.asarray(eu), np.asarray(ev))),
                              shape=(NN, NN)).tocsr()
        ncomp, labels = csgraph.connected_components(g, directed=False)
        sizes = np.sort(np.bincount(labels))[::-1]
    else:
        g = sparse.csr_matrix((NN, NN))
        ncomp, sizes = NN, np.ones(NN, dtype=np.int64)
    op = receipt["operator"]
    result["independent_components_over_weight_bearing_edges"] = {
        "published_nodes_including_isolates": NN,
        "components_including_isolates": int(ncomp),
        "largest_component": int(sizes[0]) if sizes.size else 0,
        "largest_component_share_of_published_nodes": round(float(sizes[0]) / NN, 6) if sizes.size else None,
        "largest_component_share_of_all_nodes": round(float(sizes[0]) / op["nodes"], 6) if sizes.size else None,
        "component_sizes_top20": [int(x) for x in sizes[:20]],
        "receipt_largest_component": op["largest_component"],
        "receipt_components_including_isolates": op["components"],
        "note": "all published nodes are included; positive edges determine connectivity and zero-degree nodes remain isolates.",
    }
    # The emitted support is stored in one direction; symmetrize for isolate counts.
    component_check = component_count_check(g + g.T, op)
    result['independent_component_counts'] = component_check
    if not component_check['match']:
        fail('component_counts_disagreement', component_check)
    del g
    transition_check = independent_transition(NN, eu, ev, ew, elayer)
    score_check = independent_score_checks(transition_check, node_kinds, published_pr,
                                           published_eigen)
    result['independent_score_equations'] = score_check
    for issue in score_check['failures']:
        fail('score_equation', issue)
    del transition_check

    # ---- office_diversity, re-derived from the emitted rows ----------------------
    if len(operator_containers) != len(pu):
        fail("operator_container_bookkeeping",
             {"containers": len(operator_containers), "edges": len(pu)})
    container_index = {name: i for i, name in enumerate(sorted({
        cid for containers_of_edge in operator_containers for cid in containers_of_edge
    }))}
    verifier_office, verifier_distinct, verifier_mass, verifier_strength = independent_office_diversity(
        max(len(person_ix), 1),
        NC,
        list(pu), list(pv), [float(x) for x in list(ew)[:len(pu)]],
        [tuple(container_index[cid] for cid in row) for row in operator_containers],
        operator_container_shares,
        return_mass=True,
    )
    published_office_array = np.asarray(published_office, dtype=float)
    published_distinct_array = np.asarray(published_office_distinct, dtype=np.int64)
    # pu/pv index the PERSON order of first appearance in the edge file; map back.
    person_order = [0] * len(person_ix)
    for node_id, index in person_ix.items():
        person_order[index] = node_ix[node_id]
    person_order_array = np.asarray(person_order, dtype=np.int64)
    aligned_office = np.zeros(NN, dtype=float)
    aligned_distinct = np.zeros(NN, dtype=np.int64)
    if person_order_array.size:
        aligned_office[person_order_array] = verifier_office[:person_order_array.size]
        aligned_distinct[person_order_array] = verifier_distinct[:person_order_array.size]
    office_error = (
        float(np.max(np.abs(aligned_office - published_office_array))) if NN else 0.0
    )
    distinct_mismatch = int(np.count_nonzero(aligned_distinct != published_distinct_array))
    reverse_containers = {index: key for key, index in container_index.items()}
    expected_strengths = [{} for _ in range(NN)]
    for person, mass_row in verifier_mass.items():
        expected_strengths[person_order[person]] = {
            reverse_containers[c]: share * verifier_strength[person]
            for c, share in mass_row.items()}
    strength_mismatches = sum(
        not isinstance(actual, dict) or set(actual) != set(expected)
        or any(not isinstance(actual[c], (int, float)) or not math.isfinite(actual[c])
               or abs(actual[c] - value) > 1e-8 for c, value in expected.items())
        for actual, expected in zip(published_office_strengths, expected_strengths))
    result['independent_office_diversity'] = {
        'max_absolute_error': office_error,
        'distinct_office_mismatches': distinct_mismatch,
        'office_connection_strength_mismatches': strength_mismatches,
        'tolerance': 1e-9,
        'group_count_K': NC,
        'receipt_group_count_K': (receipt.get('office_diversity') or {}).get(
            'group_count_K_distinct_containers'),
        'method': ('dictionary accumulation over the emitted co-tenure rows container_ids; '
                   'the builder used a chunked scipy sparse accumulation'),
        'match': office_error <= 1e-9 and distinct_mismatch == 0 and strength_mismatches == 0,
    }
    if not result['independent_office_diversity']['match']:
        fail('office_diversity', result['independent_office_diversity'])

    # ---- independent committee bridge ablation -----------------------------------
    NPn = len(person_ix)
    au = np.asarray(pu, dtype=np.int64)
    av = np.asarray(pv, dtype=np.int64)
    hc = np.asarray(p_has_comm, dtype=bool)
    hm = np.asarray(p_has_member, dtype=bool)
    hnc = np.asarray(p_has_noncomm, dtype=bool)

    def comps(sel):
        n = int(sel.sum())
        if n == 0 or NPn == 0:
            return {"edges": 0, "largest_component": 0}
        gm = sparse.coo_matrix((np.ones(n, dtype=np.int8), (au[sel], av[sel])),
                               shape=(NPn, NPn)).tocsr()
        k, lab = csgraph.connected_components(gm, directed=False)
        sizes = np.sort(np.bincount(lab))[::-1]
        deg = np.bincount(np.concatenate((au[sel], av[sel])), minlength=NPn)
        touched = int((deg > 0).sum())
        return {"edges": n, "people_touched": touched,
                "largest_component": int(sizes[0]),
                "largest_component_share_of_touched": (
                    round(float(sizes[0]) / touched, 6) if touched else None)}

    ab = receipt.get("committee_bridge_ablation", {})
    verifier_ab = {
        "all_edges": comps(np.ones(au.size, dtype=bool)),
        "committee_derived_REMOVED": comps(hnc),
        "ONLY_committee_derived": comps(hc),
        "ONLY_member_office_derived": comps(hm),
        "basis": "recomputed from the emitted container_kinds field with scipy.csgraph; "
                 "the builder used an internal bucket bitmask - different path",
    }
    result["independent_committee_bridge_ablation"] = {
        "verifier": verifier_ab,
        "receipt_all_edges_largest_component":
            ab.get("person_only_graph_all_co_tenure_edges", {}).get("largest_component"),
        "receipt_only_committee_largest_component":
            ab.get("ONLY_committee_derived_edges", {}).get("largest_component"),
        "all_edges_match": (
            verifier_ab["all_edges"]["largest_component"]
            == ab.get("person_only_graph_all_co_tenure_edges", {}).get("largest_component")
        ),
        "only_committee_match": (
            verifier_ab["ONLY_committee_derived"]["largest_component"]
            == ab.get("ONLY_committee_derived_edges", {}).get("largest_component")
        ),
    }
    if not result["independent_committee_bridge_ablation"]["all_edges_match"]:
        fail("committee_ablation_all_edges", result["independent_committee_bridge_ablation"])
    if not result["independent_committee_bridge_ablation"]["only_committee_match"]:
        fail("committee_ablation_only_committee", result["independent_committee_bridge_ablation"])

    # ---- side field is four-valued -----------------------------------------------
    # Containers left node_scores in v4, so the side field is read from the GROUPS roster.
    SIDE_VALUES = ("MAJ", "MIN", "BIPARTISAN", "UNKNOWN")
    side_values_seen |= committee_sides_seen
    bad_side = list(group_side_violations)
    c8c = receipt.get("C8c_committee_side_coverage", {})
    result["side_field_is_four_valued"] = {
        "allowed": list(SIDE_VALUES),
        "read_from": "staffer_social_groups.ndjson.gz",
        "values_seen_on_committee_containers": sorted(x for x in side_values_seen if x),
        "violations": bad_side[:10],
        "receipt_declares_four_valued": c8c.get("side_is_four_valued") == list(SIDE_VALUES),
        "bipartisan_populated": c8c.get("bipartisan_populated"),
        "share_unknown": c8c.get("share_unknown"),
    }
    if bad_side:
        fail("side_field_values", bad_side[:5])
    if c8c.get("side_is_four_valued") != list(SIDE_VALUES):
        fail("side_field_not_declared_four_valued", c8c.get("side_is_four_valued"))
    if "unreachable" in json.dumps(receipt).lower():
        fail("receipt_claims_kappa_row_unreachable",
             "the 0.40 opposite-side row is reachable; the limit is data coverage")

    # ---- trajectory / moves cross-check ------------------------------------------
    traj_moves = 0
    traj_rows_n = 0
    move_pairs = set()
    # ---- stint runs (owner ruling 2026-09-07) ------------------------------------
    # Every stint must sit inside ONE contiguous run of its own person-container
    # calendar, the run indices of a span must be 0..run_count-1 in order, and the
    # total stint count must equal the run count re-derived from the SPANS file above.
    CID_PREFIX = "container:office:"
    traj_stints = 0
    traj_spans = 0
    stint_not_in_a_run: list[dict[str, Any]] = []
    stint_index_violations: list[dict[str, Any]] = []
    stint_empty_intervals = 0
    stint_multi_run_spans = 0
    stint_max_run_days = 0
    stint_declared_counts = Counter()
    for t in rows(primary / "staffer_trajectories.ndjson.gz"):
        traj_rows_n += 1
        traj_moves += t["move_count"]
        traj_spans += int(t.get("span_count") or 0)
        for m in t["moves"]:
            move_pairs.add((m["from_container_id"], m["to_container_id"]))
        p = persons.get(t["spine_person_id"])
        expect_index = None
        expect_count = None
        expect_cid = None
        for stint in t.get("stints", []):
            traj_stints += 1
            stint_declared_counts[stint.get("run_basis")] += 1
            cid = str(stint.get("container_id") or "")
            index = stint.get("stint_run_index")
            count = stint.get("run_count_for_span")
            # run indices must restart at 0 per span and advance by one within it
            if index == 0:
                expect_index, expect_count, expect_cid = 0, count, cid
                if isinstance(count, int) and count > 1:
                    stint_multi_run_spans += 1
            elif (index != (expect_index + 1 if isinstance(expect_index, int) else None)
                  or count != expect_count or cid != expect_cid):
                if len(stint_index_violations) < 10:
                    stint_index_violations.append(
                        {"spine_person_id": t["spine_person_id"], "container_id": cid,
                         "stint_run_index": index, "run_count_for_span": count})
            if isinstance(index, int):
                expect_index = index
            if not isinstance(count, int) or not isinstance(index, int) or not (
                    0 <= index < count):
                if len(stint_index_violations) < 10:
                    stint_index_violations.append(
                        {"spine_person_id": t["spine_person_id"], "container_id": cid,
                         "stint_run_index": index, "run_count_for_span": count,
                         "why": "index outside [0, run_count_for_span)"})
            start = date.fromisoformat(stint["core_start"]).toordinal()
            end = date.fromisoformat(stint["core_end_exclusive"]).toordinal()
            if end <= start:
                stint_empty_intervals += 1
            stint_max_run_days = max(stint_max_run_days, int(end - start))
            if p is None or not cid.startswith(CID_PREFIX):
                if len(stint_not_in_a_run) < 10:
                    stint_not_in_a_run.append(
                        {"spine_person_id": t["spine_person_id"], "container_id": cid,
                         "why": "unknown person or malformed container id"})
                continue
            chamber_office = cid[len(CID_PREFIX):].split(":", 1)
            key = "\x00".join(chamber_office) if len(chamber_office) == 2 else None
            c = containers.get(key) if key else None
            runs = pc_union.get((p, c)) if c is not None else None
            if not runs or not any(lo <= start and end <= hi for lo, hi in runs):
                if len(stint_not_in_a_run) < 10:
                    stint_not_in_a_run.append({
                        "spine_person_id": t["spine_person_id"], "container_id": cid,
                        "core_start": stint["core_start"],
                        "core_end_exclusive": stint["core_end_exclusive"],
                        "person_container_runs": [
                            [date.fromordinal(lo).isoformat(), date.fromordinal(hi).isoformat()]
                            for lo, hi in (runs or [])[:6]],
                        "why": "stint is not contained in any single contiguous run",
                    })
    census = receipt.get("stint_census") or {}
    verifier_flag = bool(v_spans_without_runs == 0 and v_spans_with_runs > 0)
    result["stint_runs"] = {
        "ruling": "owner ruling 2026-09-07: a REPORT_PERIOD stint is the union of the "
                  "periods observed, one stint per contiguous run",
        "verifier_spans": n_spans - n_spans_skipped,
        "verifier_stints_from_spans_file": int(v_stints),
        "trajectory_stint_rows": int(traj_stints),
        "trajectory_span_rows": int(traj_spans),
        "receipt_stints": census.get("stints"),
        "receipt_spans": census.get("spans"),
        "verifier_spans_with_multiple_runs": int(v_spans_multi_run),
        "receipt_spans_with_multiple_runs": census.get("spans_with_multiple_runs"),
        "verifier_max_run_days": int(v_max_run_days),
        "receipt_max_run_days": census.get("max_run_days"),
        "verifier_max_span_days": int(v_max_span_days),
        "receipt_max_span_days": census.get("max_span_days"),
        "verifier_run_basis_counts": dict(sorted(v_run_basis.items())),
        "receipt_run_basis_counts": census.get("run_basis_counts"),
        "trajectory_spans_with_multiple_runs": int(stint_multi_run_spans),
        "trajectory_longest_stint_days": int(stint_max_run_days),
        "trajectory_stint_run_basis_counts": dict(sorted(
            (str(k), int(v)) for k, v in stint_declared_counts.items())),
        "verifier_stints_from_contiguous_runs": verifier_flag,
        "receipt_stints_from_contiguous_runs": receipt.get("stints_from_contiguous_runs"),
        "spans_carrying_contiguous_runs": int(v_spans_with_runs),
        "spans_without_contiguous_runs": int(v_spans_without_runs),
        "stints_outside_any_contiguous_run": len(stint_not_in_a_run),
        "stint_index_violations": len(stint_index_violations),
        "empty_stint_intervals": int(stint_empty_intervals),
        "examples_outside_a_run": stint_not_in_a_run[:5],
        "examples_index_violations": stint_index_violations[:5],
        "algorithm": "runs re-derived from hill_person_office_spans with an independent "
                     "period_window implementation, then every emitted stint is tested "
                     "for containment in one run of its own person-container calendar",
    }
    if traj_stints != v_stints:
        fail("stint_count_is_not_the_sum_of_run_counts",
             {"trajectories": traj_stints, "verifier_from_spans": v_stints})
    if census.get("stints") != v_stints:
        fail("receipt_stint_census_stints", {"receipt": census.get("stints"),
                                             "verifier": v_stints})
    if census.get("spans") != (n_spans - n_spans_skipped):
        fail("receipt_stint_census_spans", {"receipt": census.get("spans"),
                                            "verifier": n_spans - n_spans_skipped})
    if census.get("spans_with_multiple_runs") != v_spans_multi_run:
        fail("receipt_stint_census_multi_run",
             {"receipt": census.get("spans_with_multiple_runs"), "verifier": v_spans_multi_run})
    if census.get("max_run_days") != v_max_run_days or census.get("max_span_days") != v_max_span_days:
        fail("receipt_stint_census_max_days",
             {"receipt": [census.get("max_run_days"), census.get("max_span_days")],
              "verifier": [v_max_run_days, v_max_span_days]})
    if receipt.get("stints_from_contiguous_runs") != verifier_flag:
        fail("stints_from_contiguous_runs_flag",
             {"receipt": receipt.get("stints_from_contiguous_runs"), "verifier": verifier_flag})
    if stint_multi_run_spans != v_spans_multi_run:
        fail("trajectory_multi_run_span_count",
             {"trajectories": stint_multi_run_spans, "verifier_from_spans": v_spans_multi_run})
    if stint_max_run_days != v_max_run_days:
        fail("longest_stint_is_not_the_longest_run",
             {"trajectories": stint_max_run_days, "verifier_from_spans": v_max_run_days})
    if stint_not_in_a_run:
        fail("stint_outside_its_contiguous_run", stint_not_in_a_run[:5])
    if stint_index_violations:
        fail("stint_run_index_sequence", stint_index_violations[:5])
    if stint_empty_intervals:
        fail("empty_stint_interval", stint_empty_intervals)
    if traj_spans != receipt.get("trajectories", {}).get("span_rows"):
        fail("trajectory_span_row_count",
             {"trajectories": traj_spans,
              "receipt": receipt.get("trajectories", {}).get("span_rows")})
    if traj_stints != receipt.get("trajectories", {}).get("stint_rows"):
        fail("trajectory_stint_row_count",
             {"trajectories": traj_stints,
              "receipt": receipt.get("trajectories", {}).get("stint_rows")})
    moves_file = list(rows(primary / "staffer_office_moves.ndjson.gz"))
    result["trajectory_cross_check"] = {
        "trajectory_rows": traj_rows_n,
        "receipt_trajectory_rows": receipt["trajectories"]["person_rows"],
        "total_moves_from_trajectories": traj_moves,
        "receipt_total_moves": receipt["trajectories"]["total_directed_office_moves"],
        "distinct_directed_pairs_from_trajectories": len(move_pairs),
        "office_move_rows": len(moves_file),
        "receipt_distinct_directed_office_pairs": receipt["trajectories"]["distinct_directed_office_pairs"],
        "people_sum_matches": traj_moves == sum(m["people"] for m in moves_file),
    }
    if traj_rows_n != receipt["trajectories"]["person_rows"]:
        fail("trajectory_row_count", traj_rows_n)
    if traj_moves != receipt["trajectories"]["total_directed_office_moves"]:
        fail("trajectory_move_count", traj_moves)
    if len(move_pairs) != len(moves_file):
        fail("office_move_pair_count", {"trajectories": len(move_pairs), "file": len(moves_file)})

    # ---- NAMING LAW: emitted family must fail every live selector -----------------
    # A pattern can only ingest this family if BOTH (a) it matches one of our names and
    # (b) its glob ROOT can reach our directory. The first version of this check ignored
    # (b) and therefore flagged every bare "*" directory walk in the repo. That is a
    # false alarm, not a naming violation - but the fix must not weaken the bar, so the
    # check is split into a HARD bar and a scoped bar.
    star_lit = re.compile(r"""["']([^"'
]*\*[^"'
]*)["']""")
    call_re = re.compile(r"(?:(\w+)\s*\.\s*r?glob|glob\.(?:i?glob))\s*\(")
    sites: list[dict] = []
    scanned_files = 0
    for pyroot in (root / "fec", root / "audits" / "staffer_network"):
        for py in sorted(pyroot.rglob("*.py")):
            try:
                lines = py.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            scanned_files += 1
            rel = str(py.relative_to(root))
            dead = "_quarantine" in rel
            for i, line in enumerate(lines):
                window = " ".join(lines[max(0, i - 1):i + 2])
                if "glob" not in window:
                    continue
                m = call_re.search(window)
                receiver = m.group(1) if m and m.group(1) else "glob.glob"
                for lit in star_lit.finditer(line):
                    sites.append({"pattern": lit.group(1), "file": rel, "line": i + 1,
                                  "root_expr": receiver, "dead_code": dead})
    assert sites, "no glob call sites found - the check would be vacuous"

    emitted = [f["path"] for f in receipt["files"]] + [
        "staffer_social_network_receipt.json", "staffer_social_network_manifest.json"]
    targets = emitted + [primary.name]

    def literal_prefix(pat: str) -> str:
        return pat.replace("\\", "/").rsplit("/", 1)[-1].split("*")[0]

    # ---- HARD BAR: any selector with a distinctive literal prefix ------------------
    hard_hits = []
    distinctive = 0
    for site in sites:
        base = site["pattern"].replace("\\", "/").rsplit("/", 1)[-1]
        if len(literal_prefix(site["pattern"])) < 3:
            continue
        distinctive += 1
        for name in targets:
            if fnmatch.fnmatch(name, base):
                hard_hits.append({**site, "matched": name})

    # ---- SCOPED BAR: bare traversals only matter if rooted at our tree -------------
    scoped_hits = []
    bare_sites = [x for x in sites if len(literal_prefix(x["pattern"])) < 3]
    for site in bare_sites:
        if site["dead_code"]:
            continue
        base = site["pattern"].replace("\\", "/").rsplit("/", 1)[-1]
        if not any(fnmatch.fnmatch(n, base) for n in targets):
            continue
        # does the glob root reach audits/staffer_network?
        try:
            text = (root / site["file"]).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            text = ""
        rootvar = site["root_expr"]
        assign = re.search(rf"^\s*{re.escape(rootvar)}\s*=\s*(.+)$", text, re.M)
        rootdef = assign.group(1).strip() if assign else "UNRESOLVED_PARAMETER"
        reaches = ("staffer_network" in rootdef) or ("audits" in rootdef)
        scoped_hits.append({**site, "root_definition": rootdef[:160],
                            "root_reaches_our_tree": reaches})
    scoped_real = [h for h in scoped_hits if h["root_reaches_our_tree"]]

    # ---- DIRECT REFERENCE: does anything already name this family? -----------------
    referencing, authorized_references = [], []
    for pyroot in (root / "fec", root / "audits", root / "data"):
        if not pyroot.exists():
            continue
        for f in pyroot.rglob("*.py"):
            if f.name.startswith(("build_staffer_social", "verify_staffer_social",
                                  "test_staffer_social")) or f.name == "write_usage_handoff.py":
                # This operational status writer reports this generation's progress;
                # it is not an ingestion selector or downstream data consumer.
                continue
            try:
                if "staffer_social" in f.read_text(encoding="utf-8", errors="ignore"):
                    relative = f.relative_to(root).as_posix()
                    scope = reference_scope(relative)
                    if scope == 'unexpected_reference':
                        referencing.append(relative)
                    else:
                        authorized_references.append({'path': relative, 'scope': scope,
                                                      'sha256': sha256_file(f)})
            except Exception:
                continue

    result["naming_law"] = {
        "python_files_scanned": scanned_files,
        "glob_call_sites_found": len(sites),
        "distinctive_prefix_selectors_checked": distinctive,
        "hard_bar_hits": hard_hits,
        "bare_traversal_sites_matching_a_name": len(scoped_hits),
        "bare_traversal_sites_rooted_in_our_tree": scoped_real,
        "bare_traversal_examples_out_of_scope": [
            {k: h[k] for k in ("pattern", "file", "line", "root_expr", "root_definition")}
            for h in scoped_hits[:6]
        ],
        "files_already_referencing_staffer_social": referencing,
        "authorized_direct_references": authorized_references,
        "emitted_filenames": emitted,
        "generation_directory": primary.name,
        "method": (
            "A selector can ingest this family only if its pattern matches one of our "
            "names AND its glob root can reach our directory. Distinctive-prefix "
            "selectors (>=3 literal chars before the first wildcard) are barred "
            "outright. Bare traversals ('*', '*.json') are directory walks, not name "
            "selectors, and are failed only when rooted in our tree; quarantine paths "
            "are excluded as dead code. Explicit receipt consumers and retained "
            "audit/test files are inventoried with hashes; unexpected direct "
            "references still fail. Authorized references receive no glob exemption."
        ),
        "verdict": ("PASS - no unintended selector; direct consumers explicitly inventoried"
                    if not hard_hits and not scoped_real and not referencing
                    else "FAIL - a live selector matches"),
    }
    if hard_hits:
        fail("naming_law_distinctive_selector", hard_hits[:5])
    if scoped_real:
        fail("naming_law_traversal_rooted_in_our_tree", scoped_real[:5])
    if referencing:
        fail("naming_law_existing_reference", referencing[:5])

    # ---- promotion tripwire -------------------------------------------------------
    tripwire = {
        "receipt_canonical_employment_promotions": receipt["canonical_employment_promotions"],
        "receipt_canonical_identity_promotions": receipt["canonical_identity_promotions"],
        "manifest_canonical_employment_promotions": manifest["canonical_employment_promotions"],
        "receipt_review_status": receipt["review_status"],
        "receipt_primary_weights_emitted": receipt["primary_weights_emitted"],
        "edge_rows_with_promoted_flags": bad_flags,
    }
    result["promotion_tripwire"] = tripwire
    for key in ("receipt_canonical_employment_promotions", "receipt_canonical_identity_promotions",
                "manifest_canonical_employment_promotions", "receipt_primary_weights_emitted"):
        if tripwire[key] != 0:
            fail("promotion_tripwire", key)
    if tripwire["receipt_review_status"] != "REVIEW_REQUIRED":
        fail("promotion_tripwire", "review_status")

    result["status"] = "PASS" if not result["failures"] else "FAIL"
    payload = json.dumps(result, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    (out / "staffer_social_network_verification_receipt.json").write_bytes(payload + b"\n")
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("naming_law", "primary_file_integrity", "twin_byte_identity")},
                     indent=1, default=str))
    print("NAMING LAW:", result["naming_law"]["verdict"],
          "| glob call sites:", result["naming_law"]["glob_call_sites_found"])
    print("STATUS:", result["status"], "| failures:", len(result["failures"]))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
