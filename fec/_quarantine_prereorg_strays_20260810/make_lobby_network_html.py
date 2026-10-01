# -*- coding: utf-8 -*-
"""Build the standalone bill, industry, champion, and forecast dashboard."""

import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__))); from paths import ROOT as MB_ROOT

import argparse
import csv
import hashlib
import heapq
import html
import json
import math
import os
import re
import sys
import unicodedata
from collections import defaultdict

import historical_member_names as identity
import lobby_posture as posture

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


YEARS = tuple(range(2021, 2027))
CHAMPION_LEADER_LIMIT = 50
FORECAST_LEADER_LIMIT = 10
MAX_DOCUMENT_BYTES = 5 * 1024 * 1024

BILL_TYPE_LABELS = {
    "hr": "H.R.",
    "s": "S.",
    "hjres": "H.J.Res.",
    "sjres": "S.J.Res.",
    "hconres": "H.Con.Res.",
    "sconres": "S.Con.Res.",
    "hres": "H.Res.",
    "sres": "S.Res.",
    "hamdt": "H.Amdt.",
    "samdt": "S.Amdt.",
}
BILL_CHANNEL_ORDER = {
    "formal_strict": 0,
    "both_strict": 1,
    "title_strict": 2,
    "title_generous_only": 3,
}

ATTENTION_NOTE = (
    "Attention means the organization lobbied a bill this member sponsored or "
    "cosponsored. It is NOT evidence of contact, agreement, or a relationship."
)
CITATION_NOTE = (
    "Only ~23% of lobbying activities cite a bill number, so member-level "
    "attention rests on that 23% and it is not a random sample "
    "(better-resourced filers cite bills more)."
)
CHAMPION_NOTE = (
    "Champion scores are DESCRIPTIVE residuals, not a hypothesis test, with no p-value."
)
WORKS_NOTE = (
    "Attention measures who an org WORKS, not who agrees with it — organizations "
    "lobby adversaries as hard as allies."
)
SPEND_NOTE = (
    "Sector spend LEVELS depend on roster choice; the SHAPES are the defensible claim."
)
SPEND_PRECISION_NOTE = (
    "In-house figures are self-reported and rounded to a $10k threshold, so the "
    "total mixes a contract price with a self-estimated budget and should be read "
    "as approximate."
)
FORECAST_NOTE = (
    "The forecast is descriptive, not causal, and its headline is judged against "
    "the BEST baseline."
)
FORMER_MEMBER_NOTE = (
    "This page spans the 117th–119th Congresses, so some members shown have "
    "since left office; every one of them is marked FORMER. A member shown as "
    "NAME UNRESOLVED could not be named from any roster and is displayed by "
    "bioguide ID rather than guessed at."
)
POSITION_NOTE = (
    "The LD-2 form has NO position field. Nothing in a lobbying filing says "
    "whether the filer supported or opposed the bill, so position reads “Not "
    "disclosed” on every row — that is the disclosure regime, not a gap in this "
    "build. What the lobbyist actually wrote is shown verbatim instead."
)
INTERACTION_NOTE = (
    "An interaction is one disclosed lobbying activity that cited a bill this "
    "member sponsored or cosponsored. It records that the organization worked "
    "the bill, never that it contacted this member, and never that the member "
    "responded."
)

# ---------------------------------------------------------------- bank tier
# `bank_tier` labels organizations that are ALREADY in the bank sector.  It never
# changes who is in that sector, so no published bank number is redefined by it.
BANK_TIER_ORDER = ("big", "community", "mixed", "unclassified")
BANK_TIER_LABELS = {
    "big": "Big",
    "community": "Community + mid-size regional",
    "mixed": "Mixed · represents both",
    "unclassified": "Unclassified",
}
BANK_TIER_SHORT = {
    "big": "Big",
    "community": "Community",
    "mixed": "Mixed",
    "unclassified": "Unclassified",
}
# Evidence strength is STRUCTURAL, never colour alone.  The share of a tier-year's
# dollars that reached the tier by DEFAULT rather than by a positive
# identification picks the fill, and the fill is a hatch, so the uncertainty
# survives a screenshot of the chart.  The share is read off `by_basis` rather
# than hardcoded, so the treatment stays correct when the ratio moves.
EVIDENCE_LEVELS = (
    (0.25, "documented", "Documented"),
    (0.60, "part-inferred", "Part inferred"),
    (1.01, "mostly-inferred", "Mostly inferred"),
)
# A basis whose name marks it as a fallback is the inference; everything else is
# a positive identification.  Derived from the shipped basis names and then
# CROSS-CHECKED against the JSON's own defaulted_* totals, so a renamed basis
# fails the build loudly instead of silently un-hatching an inferred series.
DEFAULT_BASIS_MARKER = "default"

TIER_ROSTER_LINE_NOTE = (
    "The roster line is roughly $100bn — the BPI board, the FSB G-SIB list and the "
    "Federal Reserve tailoring categories. The documented POLICY line is $10bn: the "
    "CFPB's supervision authority and the Durbin amendment's interchange exemption "
    "both switch there. Banks between $10bn and $100bn are therefore large for "
    "policy purposes but are NOT on the big roster and fall into community by "
    "default, so the community series is really COMMUNITY PLUS MID-SIZE REGIONAL."
)
TIER_FLOOR_NOTE = (
    "BPI does not publish its membership: the membership section of bpi.com is "
    "empty in the live page and roughly 15 members are unnamed by any vouchable "
    "source. What is published is the board of directors, a strict subset. The big "
    "roster is therefore a FLOOR, not a census — it under-identifies big banks, and "
    "each unidentified one lands in the defaulted community bucket, which is "
    "exactly why that bucket is marked as inference."
)
TIER_MIXED_NOTE = (
    "AMERICAN BANKERS ASSOCIATION and CONSUMER BANKERS ASSOCIATION are deliberately "
    "UNASSIGNED as mixed because they genuinely represent both sizes. Mixed is never "
    "dropped from a stacked view: big and community alone are not the whole sector, "
    "and a stack that omitted mixed would make them look like it."
)
TIER_SERIES_NOTE = (
    "Hired-firm fees and in-house spend are different units and are never added. "
    "The tier is a further breakdown INSIDE each series, never a third series."
)
TIER_ROSTER_LABEL_NOTE = (
    "Tier badges in this table are FAMILY-level labels from the pinned roster. The "
    "money above is resolved per filing year, so a family that held different tiers "
    "at different times is money-correct on both sides of the change while its badge "
    "shows every tier it ever held. Do not sum this table to reproduce the money."
)
YEAR_FILTER_NOTE = (
    "Selecting a year applies the identity resolver as of that filing year, so this "
    "list is the entities that existed then, under the names they filed under then. "
    "A range that spans a merger boundary is marked rather than smoothed."
)


class IngestError(Exception):
    """Expected builder failure that must exit 2 without replacing output."""


def _default_data_root():
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise IngestError("LOCALAPPDATA is not set; pass --data-root")
    return os.path.join(local_appdata, "Melange", "lda_rebuild", "derived")


def _input_paths(
    data_root,
    bill_directions_path=None,
    bills_audit_path=None,
    congestion_path=None,
    legislators_path=None,
    voteview_path=None,
):
    champions = os.path.join(data_root, "champions_fullscope")
    spend = os.path.join(data_root, "sector_spend")
    forecast = os.path.join(data_root, "cosponsor_sc")
    paths = [
        (f"network_{year}", os.path.join(
            data_root, f"our_network_fullscope_{year}_strict.csv"
        ))
        for year in YEARS
    ]
    paths.extend(
        [
            ("fullscope_org_roster", os.path.join(data_root, "fullscope_org_roster.csv")),
            ("champions_csv", os.path.join(champions, "champions.csv")),
            ("champions_json", os.path.join(champions, "champions.json")),
            ("sector_spend_json", os.path.join(spend, "sector_spend.json")),
            ("sector_spend_csv", os.path.join(spend, "sector_spend.csv")),
            ("sector_roster", os.path.join(spend, "sector_roster.csv")),
            ("cosponsor_report", os.path.join(forecast, "cosponsor_forecast_report.json")),
            ("cosponsor_scores", os.path.join(forecast, "cosponsor_scores.csv")),
        ]
    )
    paths.extend(
        (
            f"bill_index_{year}",
            os.path.join(data_root, f"our_bill_lobby_index_{year}.csv"),
        )
        for year in YEARS
    )
    paths.extend(
        [
            (
                "bill_index_manifest",
                os.path.join(data_root, "our_bill_lobby_index_manifest.json"),
            ),
            (
                "bill_repository_join",
                os.path.join(data_root, "our_bill_repository_join.csv"),
            ),
            (
                "bill_directions",
                bill_directions_path or os.path.join(MB_ROOT, "bill_directions.csv"),
            ),
            (
                "bills_audit",
                bills_audit_path or os.path.join(MB_ROOT, "bills_audit.csv"),
            ),
            # Member-name sources.  The network, champions, and forecast inputs
            # all carry bare bioguides for members of the 117th-119th, so the
            # page cannot name them from a current roster alone.
            (
                "congestion_roster",
                congestion_path or identity.DEFAULT_CONGESTION_PATH,
            ),
            (
                "legislators_roster",
                legislators_path or identity.DEFAULT_LEGISLATORS_PATH,
            ),
            (
                "voteview_members",
                voteview_path or identity.DEFAULT_VOTEVIEW_PATH,
            ),
        ]
    )
    return paths


def _write_text_atomic(text, path):
    temp_path = path + ".tmp." + str(os.getpid())
    try:
        with open(temp_path, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(temp_path, path)
    except BaseException:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        raise


def _sha256(path, label):
    if not os.path.isfile(path):
        raise IngestError(f"{label} not found: {path}")
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as handle:
            while True:
                block = handle.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
    except OSError as exc:
        raise IngestError(f"{label} unreadable: {exc}")
    return digest.hexdigest()


def _load_json(path, label):
    if not os.path.isfile(path):
        raise IngestError(f"{label} not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        raise IngestError(f"{label} unreadable: {exc}")


def _iter_csv(path, label, required_fields):
    if not os.path.isfile(path):
        raise IngestError(f"{label} not found: {path}")
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            fields = set(reader.fieldnames or ())
            missing = sorted(set(required_fields) - fields)
            if missing:
                raise IngestError(
                    f"{label} lacks required columns: {', '.join(missing)}"
                )
            for row_number, row in enumerate(reader, start=2):
                yield row_number, row
    except IngestError:
        raise
    except (OSError, csv.Error) as exc:
        raise IngestError(f"{label} unreadable: {exc}")


def _integer(value, label, minimum=0):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise IngestError(f"{label} must be an integer")
    if number < minimum:
        raise IngestError(f"{label} must be at least {minimum}")
    return number


def _number(value, label, allow_null=False):
    if value is None or str(value).strip() == "":
        if allow_null:
            return None
        raise IngestError(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise IngestError(f"{label} must be numeric")
    if not math.isfinite(number):
        raise IngestError(f"{label} must be finite")
    return number


def _boolean(value, label):
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().casefold()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise IngestError(f"{label} must be boolean")


def _normalize_name(value):
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character for character in text if not unicodedata.combining(character)
    )
    text = text.replace("&", " AND ").replace("’", "'").replace("`", "'")
    text = re.sub(r"[^A-Z0-9']+", " ", text.upper())
    return re.sub(r"\s+", " ", text).strip()


def _split_roster_values(value):
    return [item.strip() for item in re.split(r"\s+\|\s+", value or "") if item.strip()]


def _load_org_roster(path):
    fields = (
        "lob_id_or_client_id",
        "client_name",
        "source_flags",
        "first_year_seen",
        "last_year_seen",
    )
    organizations = {}
    for row_number, row in _iter_csv(path, "full-scope organization roster", fields):
        lob_id = (row["lob_id_or_client_id"] or "").strip()
        name = (row["client_name"] or "").strip()
        if not lob_id or not name:
            raise IngestError(f"organization roster row {row_number} has blank identity")
        if lob_id in organizations:
            raise IngestError(f"organization roster repeats {lob_id}")
        organizations[lob_id] = {
            "name": name,
            "flags": row["source_flags"],
            "first": row["first_year_seen"],
            "last": row["last_year_seen"],
        }
    if not organizations:
        raise IngestError("organization roster is empty")
    return organizations


def _split_tier_token(token):
    """``community:defaulted`` -> ``("community", "defaulted")``."""
    tier, _, basis = str(token or "").partition(":")
    return tier.strip(), basis.strip()


def _load_sector_roster(path, organizations):
    # `bank_tiers` rides alongside `sector`; it is a LABEL on organizations that
    # are already in the bank sector, never a second sector.  Reading it here is
    # what stops the tier from being dropped between the canonical roster and the
    # page: the old fixed field list silently discarded it.
    fields = (
        "sector",
        "canonical_family",
        "bank_tiers",
        "raw_name_variants",
        "normalized_name_variants",
        "matched_pattern",
        "client_ids",
        "collapse_rules",
        "first_year_seen",
        "last_year_seen",
    )
    id_index = {}
    name_index = {}
    id_conflicts = set()
    name_conflicts = set()
    tier_id_index = {}
    tier_name_index = {}
    tier_id_conflicts = set()
    tier_name_conflicts = set()
    sectors = set()
    families = defaultdict(list)
    tiered_families = 0

    def add(index, conflicts, key, value):
        if not key or value is None:
            return
        previous = index.get(key)
        if previous is not None and previous != value:
            conflicts.add(key)
        else:
            index[key] = value

    for row_number, row in _iter_csv(path, "sector roster", fields):
        sector = (row["sector"] or "").strip()
        family = (row["canonical_family"] or "").strip()
        if not sector or not family:
            raise IngestError(f"sector roster row {row_number} has blank sector/family")
        sectors.add(sector)

        # A family can legitimately carry MORE than one tier when a date-gated
        # entity sat in different tiers at different times (First Republic was
        # big while it existed).  The tokens are a SET, not positionally aligned
        # with client_ids, so no single tier may be picked for such a family.
        tiers = []
        defaulted = False
        for token in _split_roster_values(row["bank_tiers"]):
            tier, basis = _split_tier_token(token)
            if not tier:
                continue
            if tier not in BANK_TIER_ORDER:
                raise IngestError(
                    f"sector roster row {row_number} has unknown bank tier {tier!r}"
                )
            if tier not in tiers:
                tiers.append(tier)
            if basis == "defaulted":
                defaulted = True
        tiers = tuple(name for name in BANK_TIER_ORDER if name in tiers)
        if tiers:
            tiered_families += 1

        client_ids = _split_roster_values(row["client_ids"])
        for client_id in client_ids:
            add(id_index, id_conflicts, client_id, sector)
            add(tier_id_index, tier_id_conflicts, client_id, tiers or None)
        aliases = [family]
        aliases.extend(_split_roster_values(row["raw_name_variants"]))
        aliases.extend(_split_roster_values(row["normalized_name_variants"]))
        for alias in aliases:
            key = _normalize_name(alias)
            add(name_index, name_conflicts, key, sector)
            add(tier_name_index, tier_name_conflicts, key, tiers or None)

        first = _integer(row["first_year_seen"], f"sector roster row {row_number} first year")
        last = _integer(row["last_year_seen"], f"sector roster row {row_number} last year")
        if last < first:
            raise IngestError(f"sector roster row {row_number} has inverted year window")
        families[sector].append(
            {
                "f": family,
                "t": list(tiers),
                "d": defaulted,
                "y0": first,
                "y1": last,
                "c": (row["collapse_rules"] or "").strip(),
                "n": len(client_ids),
            }
        )

    for key in id_conflicts:
        id_index.pop(key, None)
    for key in name_conflicts:
        name_index.pop(key, None)
    for key in tier_id_conflicts:
        tier_id_index.pop(key, None)
    for key in tier_name_conflicts:
        tier_name_index.pop(key, None)

    sector_by_org = {}
    tier_by_org = {}
    for lob_id, organization in organizations.items():
        normalized = _normalize_name(organization["name"])
        sector = id_index.get(lob_id)
        if sector is None:
            sector = name_index.get(normalized)
        if sector is not None:
            sector_by_org[lob_id] = sector
        tiers = tier_id_index.get(lob_id)
        if tiers is None:
            tiers = tier_name_index.get(normalized)
        if tiers:
            tier_by_org[lob_id] = tuple(tiers)

    for sector in families:
        families[sector].sort(key=lambda item: (item["f"], item["y0"]))
    return sector_by_org, sorted(sectors), {
        "ambiguous_ids": len(id_conflicts),
        "ambiguous_names": len(name_conflicts),
        "tiered_families": tiered_families,
        "ambiguous_tier_ids": len(tier_id_conflicts),
        "ambiguous_tier_names": len(tier_name_conflicts),
    }, tier_by_org, dict(families)


def _evidence_level(share):
    for ceiling, key, label in EVIDENCE_LEVELS:
        if share < ceiling:
            return key, label
    return EVIDENCE_LEVELS[-1][1], EVIDENCE_LEVELS[-1][2]


def _tier_evidence(basis, json_field, declared_defaulted, context):
    """Read the evidence ladder off ``by_basis`` and verify it against the JSON.

    The treatment is driven by the SHARE of a tier-year's dollars that arrived by
    default rather than by a positive identification, so it stays correct if the
    ratio moves.  The share is derived from the basis names and then checked
    against the producer's own ``defaulted_*_total``: a renamed basis therefore
    fails the build instead of silently un-hatching an inferred series.
    """
    total = 0.0
    defaulted = 0.0
    for name, entry in basis.items():
        value = _number(entry.get(json_field), f"{context} {name} {json_field}")
        total += value
        if DEFAULT_BASIS_MARKER in name.casefold():
            defaulted += value
    if abs(defaulted - declared_defaulted) > 0.5:
        raise IngestError(
            f"{context}: by_basis default total {defaulted:,.0f} disagrees with "
            f"declared defaulted total {declared_defaulted:,.0f}; a basis name "
            "changed and the evidence treatment can no longer be derived"
        )
    share = (defaulted / total) if total else 0.0
    key, label = _evidence_level(share)
    return {"share": share, "level": key, "label": label, "total": total}


def _load_spend(json_path, csv_path, roster_sectors):
    payload = _load_json(json_path, "sector spend JSON")
    if not isinstance(payload, dict):
        raise IngestError("sector spend JSON must be an object")
    selected = payload.get("selected_sectors")
    if not isinstance(selected, list) or not all(isinstance(item, str) for item in selected):
        raise IngestError("sector spend JSON lacks selected_sectors")

    receipts = payload.get("receipts") or {}
    honesty = payload.get("honesty") or {}
    tier_receipt = receipts.get("bank_tier") or {}
    # The gate is DERIVED from the producer's own switch, not asserted here: if a
    # future vintage ships without tiers the page degrades to the untiered view
    # rather than failing, but while tiers ARE enabled every column is required.
    tier_enabled = bool(tier_receipt.get("enabled"))
    tier_names = tuple(tier_receipt.get("tiers") or ()) if tier_enabled else ()
    for name in tier_names:
        if name not in BANK_TIER_ORDER:
            raise IngestError(f"sector spend JSON declares unknown bank tier {name!r}")

    fields = (
        "sector",
        "year",
        "period",
        "is_partial_year",
        "distinct_organizations",
        "filings",
        "income_total",
        "expenses_total",
        "distinct_registrants",
        "distinct_named_lobbyists",
        "top_1_income_share",
        "top_3_income_share",
        "top_10_income_share",
        "income_hhi",
    ) + tuple(
        f"tier_{name}_{suffix}"
        for name in tier_names
        for suffix in ("organizations", "income_total", "expenses_total")
    )
    annual = defaultdict(dict)
    csv_tiers = defaultdict(dict)
    for row_number, row in _iter_csv(csv_path, "sector spend CSV", fields):
        if (row["period"] or "").strip().casefold() != "annual":
            continue
        sector = (row["sector"] or "").strip()
        year = _integer(row["year"], f"sector spend row {row_number} year")
        if year not in YEARS:
            continue
        if year in annual[sector]:
            raise IngestError(f"sector spend repeats {sector} annual {year}")
        hired_firms = _number(
            row["income_total"], f"sector spend row {row_number} hired firms"
        )
        in_house = _number(
            row["expenses_total"], f"sector spend row {row_number} in-house"
        )
        annual[sector][year] = {
            "year": year,
            "partial": _boolean(
                row["is_partial_year"], f"sector spend row {row_number} partial flag"
            ),
            "orgs": _integer(
                row["distinct_organizations"], f"sector spend row {row_number} orgs"
            ),
            "filings": _integer(row["filings"], f"sector spend row {row_number} filings"),
            "hired_firms": hired_firms,
            "in_house": in_house,
            "total": hired_firms + in_house,
            "registrants": _integer(
                row["distinct_registrants"],
                f"sector spend row {row_number} registrants",
            ),
            "lobbyists": _integer(
                row["distinct_named_lobbyists"],
                f"sector spend row {row_number} lobbyists",
            ),
        }
        # Tier columns are blank for every sector that is not the bank sector.
        for name in tier_names:
            raw = row[f"tier_{name}_income_total"]
            if raw is None or str(raw).strip() == "":
                continue
            csv_tiers[sector].setdefault(year, {})[name] = {
                "hired_firms": _number(raw, f"sector spend row {row_number} {name} fees"),
                "in_house": _number(
                    row[f"tier_{name}_expenses_total"],
                    f"sector spend row {row_number} {name} in-house",
                ),
                "orgs": _integer(
                    row[f"tier_{name}_organizations"],
                    f"sector spend row {row_number} {name} orgs",
                ),
            }

    sectors = sorted(set(selected) | set(roster_sectors) | set(annual))
    for sector in sectors:
        missing = [year for year in YEARS if year not in annual.get(sector, {})]
        if missing:
            raise IngestError(
                f"sector spend lacks {sector} annual years: "
                + ", ".join(str(year) for year in missing)
            )
        if not annual[sector][2026]["partial"]:
            raise IngestError(f"sector spend does not mark {sector} 2026 partial")

    tier_sectors = []
    if tier_enabled:
        json_sectors = payload.get("sectors") or {}
        for sector in sectors:
            years = (json_sectors.get(sector) or {}).get("years") or []
            by_year = {
                entry.get("year"): entry for entry in years if isinstance(entry, dict)
            }
            if not any("bank_tier" in (by_year.get(year) or {}) for year in YEARS):
                continue
            tier_sectors.append(sector)
            for index, year in enumerate(YEARS):
                source = (by_year.get(year) or {}).get("bank_tier")
                if not isinstance(source, dict):
                    raise IngestError(f"{sector} {year} lacks a bank_tier block")
                row = annual[sector][year]
                csv_row = csv_tiers.get(sector, {}).get(year, {})
                rendered = {}
                sum_hired = 0.0
                sum_in_house = 0.0
                for name in tier_names:
                    block = source.get(name)
                    if not isinstance(block, dict):
                        raise IngestError(f"{sector} {year} lacks bank_tier.{name}")
                    basis = block.get("by_basis")
                    if not isinstance(basis, dict) or not basis:
                        raise IngestError(f"{sector} {year} {name} lacks by_basis")
                    context = f"{sector} {year} {name}"
                    hired = _number(block.get("income_total"), f"{context} fees")
                    in_house = _number(block.get("expenses_total"), f"{context} in-house")
                    orgs = _integer(
                        block.get("distinct_organizations"), f"{context} orgs"
                    )
                    # The CSV and the JSON are two independent renderings of the
                    # same split; disagreement means one of them is stale.
                    mirror = csv_row.get(name)
                    if mirror is not None and (
                        abs(mirror["hired_firms"] - hired) > 0.5
                        or abs(mirror["in_house"] - in_house) > 0.5
                        or mirror["orgs"] != orgs
                    ):
                        raise IngestError(
                            f"{context}: sector_spend.csv tier columns disagree with "
                            "sector_spend.json bank_tier block"
                        )
                    sum_hired += hired
                    sum_in_house += in_house
                    rendered[name] = {
                        "hired_firms": hired,
                        "in_house": in_house,
                        "orgs": orgs,
                        "filings": _integer(block.get("filings"), f"{context} filings"),
                        "defaulted_orgs": _integer(
                            block.get("defaulted_organizations"),
                            f"{context} defaulted orgs",
                        ),
                        "evidence": {
                            "hired_firms": _tier_evidence(
                                basis,
                                "income_total",
                                _number(
                                    block.get("defaulted_income_total"),
                                    f"{context} defaulted fees",
                                ),
                                f"{context} fees",
                            ),
                            "in_house": _tier_evidence(
                                basis,
                                "expenses_total",
                                _number(
                                    block.get("defaulted_expenses_total"),
                                    f"{context} defaulted in-house",
                                ),
                                f"{context} in-house",
                            ),
                        },
                    }
                # The stack must be the whole sector.  If the tiers did not sum to
                # the published sector total, a stacked chart would quietly show
                # two tiers as if they were everything.
                if (
                    abs(sum_hired - row["hired_firms"]) > 0.5
                    or abs(sum_in_house - row["in_house"]) > 0.5
                ):
                    raise IngestError(
                        f"{sector} {year}: bank tiers do not sum to the sector total "
                        f"(fees {sum_hired:,.0f} vs {row['hired_firms']:,.0f}; "
                        f"in-house {sum_in_house:,.0f} vs {row['in_house']:,.0f})"
                    )
                row["tiers"] = rendered

    meta = {
        "enabled": tier_enabled,
        "order": [name for name in BANK_TIER_ORDER if name in tier_names],
        "labels": {name: BANK_TIER_LABELS[name] for name in tier_names},
        "short": {name: BANK_TIER_SHORT[name] for name in tier_names},
        "sectors": tier_sectors,
        # The evidence ladder and the tier palette ship as DATA so the page has
        # one copy of each.  A JavaScript re-statement of either would be a
        # mirror free to drift from the fill the builder actually drew.
        "levels": [list(level) for level in EVIDENCE_LEVELS],
        "colors": dict(TIER_COLORS),
        "glyphs": dict(EVIDENCE_GLYPHS),
        "honesty": {
            key: honesty[key]
            for key in (
                "bank_tier",
                "bank_tier_roster_line_is_not_the_policy_line",
                "entity_identity",
                "entity_identity_not_exhaustive",
            )
            if isinstance(honesty.get(key), str)
        },
        "threshold_note": tier_receipt.get("threshold_note"),
        "bpi_gap": tier_receipt.get("bpi_membership_gap"),
        "roster_nesting": tier_receipt.get("roster_nesting"),
        "provenance": _tier_provenance(tier_receipt),
    }
    return (
        {sector: [annual[sector][year] for year in YEARS] for sector in sectors},
        meta,
        receipts.get("entity_identity") or {},
    )


def _tier_provenance(tier_receipt):
    provenance = tier_receipt.get("provenance") or {}
    by_source = provenance.get("parents_by_source") or {}
    sources = tier_receipt.get("sources") or {}
    rows = []
    for key in sorted(by_source):
        entry = by_source[key] or {}
        rows.append(
            {
                "k": key,
                "l": (sources.get(key) or {}).get("label") or key,
                "n": _integer(entry.get("count", 0), f"tier provenance {key} count"),
            }
        )
    return {
        "parents": _integer(
            provenance.get("distinct_parents", 0), "tier provenance parents"
        ),
        "date_gated": list(provenance.get("date_gated_parents") or ()),
        "sources": rows,
    }


def _merger_boundaries(entity_receipt, families_by_sector):
    """Attach declared merger boundaries to the roster families they moved.

    The receipts name boundary participants by SYMBOLIC key (``CUNA``), and the
    roster names them by canonical family, so the link has to be established
    rather than assumed.  It is established by year window — the roster is
    date-gated, so a predecessor's window ends the year before the boundary and
    the successor's begins on it — and then VERIFIED against the declared
    predecessor and successor counts.  A boundary that does not verify ships as a
    banner with no per-row badges instead of a guessed linkage.
    """
    declared = entity_receipt.get("merger_boundaries_inside_window") or {}
    boundaries = []
    for key in sorted(declared):
        record = declared[key] or {}
        year = record.get("effective_filing_year")
        if year not in YEARS:
            continue
        predecessors = list(record.get("predecessors") or ())
        successor = record.get("successor")
        matches = {}
        for sector, families in families_by_sector.items():
            gated = [item for item in families if "entity_identity" in item["c"]]
            before = [item["f"] for item in gated if item["y1"] == year - 1]
            after = [item["f"] for item in gated if item["y0"] == year]
            if len(before) == len(predecessors) and len(after) == 1 and predecessors:
                matches[sector] = {"before": sorted(before), "after": after[0]}
        # One sector must own the boundary.  Two would mean the year-window test
        # is not discriminating and the linkage is not evidence.
        linked = matches if len(matches) == 1 else {}
        sector = next(iter(linked), None)
        boundaries.append(
            {
                "k": key,
                "y": year,
                "d": record.get("effective_date") or "",
                "r": record.get("relation") or "merger",
                "c": record.get("confidence") or "",
                "e": record.get("evidence") or "",
                "s": sector,
                "before": linked.get(sector, {}).get("before", []),
                "after": linked.get(sector, {}).get("after"),
                "np": len(predecessors),
                "successor_key": successor,
            }
        )
    return boundaries


def _load_network(paths_by_label, organizations, sector_by_org):
    fields = ("lob_id", "bioguide_id", "year", "n_bills")
    attention = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    # Posture on the champions board is per ORGANIZATION and member, not per
    # sector: "BECU is cultivating Comer" is a different claim from "credit
    # unions are cultivating Comer", and the board makes the first one.
    org_attention = defaultdict(lambda: defaultdict(int))
    active_orgs = set()
    orgs_by_sector = defaultdict(set)
    rows_read = 0
    for year in YEARS:
        path = paths_by_label[f"network_{year}"]
        seen = set()
        for row_number, row in _iter_csv(path, f"{year} strict network", fields):
            rows_read += 1
            lob_id = (row["lob_id"] or "").strip()
            member = (row["bioguide_id"] or "").strip()
            row_year = _integer(row["year"], f"network row {row_number} year")
            count = _integer(row["n_bills"], f"network row {row_number} n_bills")
            if row_year != year:
                raise IngestError(f"{year} network row {row_number} has year {row_year}")
            if lob_id not in organizations:
                raise IngestError(f"network organization absent from roster: {lob_id}")
            if not member:
                raise IngestError(f"network row {row_number} has blank member")
            key = (lob_id, member)
            if key in seen:
                raise IngestError(f"{year} network repeats organization/member {key}")
            seen.add(key)
            active_orgs.add(lob_id)
            org_attention[(lob_id, member)][year] += count
            sector = sector_by_org.get(lob_id)
            if sector is not None:
                orgs_by_sector[sector].add(lob_id)
                attention[sector][member][year] += count
    return attention, org_attention, active_orgs, orgs_by_sector, rows_read


def _normalize_bill_type(value):
    normalized = re.sub(r"[^a-z]", "", str(value or "").casefold())
    return normalized if normalized in BILL_TYPE_LABELS else None


def _canonical_bill_key(congress, bill_type, bill_number):
    return f"{int(congress)}:{bill_type}:{int(bill_number)}"


def _bill_display(bill_type, bill_number):
    return f"{BILL_TYPE_LABELS[bill_type]}{int(bill_number)}"


def _bill_key_from_display(display, congress):
    congress_text = str(congress or "").strip()
    if not congress_text:
        return None
    try:
        congress_number = _integer(congress_text, "bill metadata congress", minimum=1)
    except IngestError:
        return None
    token = re.sub(r"[^a-z0-9]", "", str(display or "").casefold())
    for bill_type in sorted(BILL_TYPE_LABELS, key=len, reverse=True):
        if not token.startswith(bill_type):
            continue
        number_text = token[len(bill_type):]
        if number_text.isdigit() and int(number_text) > 0:
            return _canonical_bill_key(congress_number, bill_type, int(number_text))
    return None


def _load_bill_titles(path):
    fields = ("bill", "title", "congresses")
    candidates = defaultdict(set)
    rows_read = 0
    unparseable = 0
    for _row_number, row in _iter_csv(path, "bills audit", fields):
        rows_read += 1
        title = (row["title"] or "").strip()
        for congress in str(row["congresses"] or "").split(";"):
            key = _bill_key_from_display(row["bill"], congress)
            if key is None:
                unparseable += 1
                continue
            if title:
                candidates[key].add(title)
    titles = {
        key: sorted(values, key=lambda value: (-len(value), value.casefold(), value))[0]
        for key, values in candidates.items()
        if values
    }
    return titles, {
        "rows": rows_read,
        "distinct_keys": len(titles),
        "unparseable": unparseable,
        "conflicting_titles": sum(len(values) > 1 for values in candidates.values()),
    }


def _load_bill_markings(path):
    fields = ("Bill", "Congress", "Category", "Direction", "Note")
    markings = {}
    rows_read = 0
    unjoinable = 0
    for row_number, row in _iter_csv(path, "bill directions", fields):
        rows_read += 1
        key = _bill_key_from_display(row["Bill"], row["Congress"])
        if key is None:
            unjoinable += 1
            continue
        direction = _integer(
            row["Direction"], f"bill directions row {row_number} direction", minimum=-1
        )
        if direction not in (-1, 0, 1):
            raise IngestError(
                f"bill directions row {row_number} direction must be -1, 0, or 1"
            )
        if key in markings:
            raise IngestError(f"bill directions repeats canonical bill {key}")
        state = {1: "support", -1: "oppose", 0: "neutral"}[direction]
        markings[key] = {
            "direction": direction,
            "state": state,
            "category": (row["Category"] or "").strip(),
        }
    return markings, {
        "rows": rows_read,
        "joinable": len(markings),
        "unjoinable": unjoinable,
    }


def _load_bill_repository_receipt(path):
    fields = ("bill_key", "canonical_key", "bill_type", "join_status")
    rows_read = 0
    matched = 0
    repository_only = 0
    repository_only_amendments = 0
    for row_number, row in _iter_csv(path, "bill repository join", fields):
        rows_read += 1
        key = (row["bill_key"] or row["canonical_key"] or "").strip()
        status = (row["join_status"] or "").strip()
        if not key:
            raise IngestError(f"bill repository join row {row_number} has blank key")
        if status == "matched":
            matched += 1
        elif status == "repository_only":
            repository_only += 1
            if _normalize_bill_type(row["bill_type"]) in {"hamdt", "samdt"}:
                repository_only_amendments += 1
        elif status != "lobbying_only":
            raise IngestError(
                f"bill repository join row {row_number} has unknown join_status {status!r}"
            )
    return {
        "rows": rows_read,
        "matched": matched,
        "repository_only": repository_only,
        "repository_only_amendments": repository_only_amendments,
    }


def _load_bill_manifest(path):
    manifest = _load_json(path, "bill index manifest")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("years"), dict):
        raise IngestError("bill index manifest lacks years")
    corpus_basis = str(manifest.get("CORPUS_BASIS") or "").strip()
    if not corpus_basis:
        raise IngestError("bill index manifest lacks CORPUS_BASIS")
    for year in YEARS:
        entry = manifest["years"].get(str(year))
        if not isinstance(entry, dict):
            raise IngestError(f"bill index manifest lacks {year}")
        if str(entry.get("CORPUS_BASIS") or "").strip() != corpus_basis:
            raise IngestError(f"bill index manifest violates CORPUS_BASIS in {year}")
    repository_join = manifest.get("repository_join")
    if not isinstance(repository_join, dict):
        raise IngestError("bill index manifest lacks repository_join")
    expected_bills = _integer(
        repository_join.get("lobbied_distinct_bills"),
        "bill index manifest lobbied_distinct_bills",
        minimum=1,
    )
    return manifest, expected_bills


def _load_bills(paths_by_label, organizations):
    manifest, expected_bills = _load_bill_manifest(
        paths_by_label["bill_index_manifest"]
    )
    titles, title_receipt = _load_bill_titles(paths_by_label["bills_audit"])
    markings, marking_input_receipt = _load_bill_markings(
        paths_by_label["bill_directions"]
    )
    repository_receipt = _load_bill_repository_receipt(
        paths_by_label["bill_repository_join"]
    )
    bills = {}
    input_rows = 0
    for filing_year in YEARS:
        fields = (
            "congress",
            "bill_type",
            "bill_number",
            "bill_key",
            "lob_id",
            "client_name",
            "org_sector",
            "n_filings",
            "n_activities",
            "first_filing_period",
            "last_filing_period",
            "channel",
        )
        seen_links = set()
        year_bills = set()
        year_orgs = set()
        year_rows = 0
        for row_number, row in _iter_csv(
            paths_by_label[f"bill_index_{filing_year}"],
            f"{filing_year} bill index",
            fields,
        ):
            input_rows += 1
            year_rows += 1
            congress = _integer(
                row["congress"], f"bill index row {row_number} congress", minimum=1
            )
            bill_type = _normalize_bill_type(row["bill_type"])
            if bill_type is None or bill_type in {"hamdt", "samdt"}:
                raise IngestError(
                    f"bill index row {row_number} has unsupported bill type {row['bill_type']!r}"
                )
            bill_number = _integer(
                row["bill_number"],
                f"bill index row {row_number} bill_number",
                minimum=1,
            )
            key = _canonical_bill_key(congress, bill_type, bill_number)
            if (row["bill_key"] or "").strip() != key:
                raise IngestError(
                    f"bill index row {row_number} key does not match canonical parts"
                )
            lob_id = (row["lob_id"] or "").strip()
            if lob_id not in organizations:
                raise IngestError(
                    f"bill index organization absent from full-scope roster: {lob_id}"
                )
            link_key = (key, lob_id)
            if link_key in seen_links:
                raise IngestError(
                    f"{filing_year} bill index repeats bill/organization {link_key}"
                )
            seen_links.add(link_key)
            year_bills.add(key)
            year_orgs.add(lob_id)
            channel = (row["channel"] or "").strip()
            if channel not in BILL_CHANNEL_ORDER:
                raise IngestError(
                    f"bill index row {row_number} has unknown extraction channel {channel!r}"
                )
            raw_sector = (row["org_sector"] or "").strip() or "unclassified"
            bill = bills.setdefault(
                key,
                {
                    "key": key,
                    "congress": congress,
                    "bill_type": bill_type,
                    "bill_number": bill_number,
                    "bill": _bill_display(bill_type, bill_number),
                    "years": set(),
                    "organizations": {},
                },
            )
            bill["years"].add(filing_year)
            link = bill["organizations"].setdefault(
                lob_id,
                {
                    "id": lob_id,
                    "name": organizations[lob_id]["name"],
                    "sectors": set(),
                    "sector_values": set(),
                    "n_filings": 0,
                    "n_activities": 0,
                    "years": set(),
                    "channels": set(),
                },
            )
            link["sector_values"].add(raw_sector)
            link["sectors"].update(
                part.strip() for part in raw_sector.split("|") if part.strip()
            )
            link["n_filings"] += _integer(
                row["n_filings"], f"bill index row {row_number} n_filings"
            )
            link["n_activities"] += _integer(
                row["n_activities"], f"bill index row {row_number} n_activities"
            )
            link["years"].add(filing_year)
            link["channels"].add(channel)

        manifest_year = manifest["years"][str(filing_year)]
        expected = {
            "rows": year_rows,
            "distinct_bills": len(year_bills),
            "distinct_orgs": len(year_orgs),
        }
        for field, observed in expected.items():
            declared = _integer(
                manifest_year.get(field),
                f"bill index manifest {filing_year} {field}",
            )
            if observed != declared:
                raise IngestError(
                    f"bill index {filing_year} {field} is {observed:,}; "
                    f"manifest declares {declared:,}"
                )

    if len(bills) != expected_bills:
        raise IngestError(
            f"bill index contains {len(bills):,} distinct bills; "
            f"manifest declares {expected_bills:,}"
        )

    payload = []
    directional = 0
    neutral = 0
    link_count = 0
    sectors = set()
    for key, bill in bills.items():
        organizations_payload = []
        for link in bill["organizations"].values():
            sectors.update(link["sectors"])
            organizations_payload.append(
                {
                    "id": link["id"],
                    "name": link["name"],
                    "sector": " | ".join(sorted(link["sector_values"])),
                    "sectors": sorted(link["sectors"]),
                    "n_filings": link["n_filings"],
                    "n_activities": link["n_activities"],
                    "years": sorted(link["years"]),
                    "channels": sorted(
                        link["channels"], key=lambda item: BILL_CHANNEL_ORDER[item]
                    ),
                }
            )
        organizations_payload.sort(
            key=lambda item: (-item["n_filings"], item["name"].casefold(), item["id"])
        )
        link_count += len(organizations_payload)
        marking = markings.get(key)
        if marking is not None:
            if marking["direction"] == 0:
                neutral += 1
            else:
                directional += 1
        payload.append(
            {
                "key": key,
                "congress": bill["congress"],
                "bill_type": bill["bill_type"],
                "bill_number": bill["bill_number"],
                "bill": bill["bill"],
                "title": titles.get(key, ""),
                "years": sorted(bill["years"]),
                "sectors": sorted(
                    set().union(
                        *(set(item["sectors"]) for item in organizations_payload)
                    )
                    if organizations_payload
                    else set()
                ),
                "marking": marking,
                "organizations": organizations_payload,
            }
        )
    payload.sort(
        key=lambda item: (
            -len(item["organizations"]),
            -item["congress"],
            item["bill_type"],
            item["bill_number"],
        )
    )
    marked = directional + neutral
    return payload, sorted(sectors), {
        "bills": len(payload),
        "links": link_count,
        "input_rows": input_rows,
        "marked": marked,
        "directional": directional,
        "neutral": neutral,
        "unmarked": len(payload) - marked,
        "manifest_bills": expected_bills,
        "truncated_links": 0,
        "marking_input": marking_input_receipt,
        "titles": title_receipt,
        "repository": repository_receipt,
    }


def _champion_metadata(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("per_org"), list):
        raise IngestError("champions JSON lacks per_org list")
    metadata = {}
    for index, entry in enumerate(payload["per_org"], start=1):
        if not isinstance(entry, dict):
            raise IngestError(f"champions JSON per_org item {index} is not an object")
        lob_id = str(entry.get("lob_id") or "").strip()
        if not lob_id or lob_id in metadata:
            raise IngestError(f"champions JSON has invalid/repeated lob_id at item {index}")
        metadata[lob_id] = entry
    return metadata


def _member_flag(record):
    """Return the display flag for a member, or None when they are serving."""
    if record["status"] == identity.STATUS_FORMER:
        return "former"
    if record["status"] == identity.STATUS_UNRESOLVED:
        return "unresolved"
    return None


def _load_champions(
    csv_path,
    json_path,
    organizations,
    sector_by_org,
    orgs_by_sector,
    resolver,
    org_attention=None,
    postures=None,
):
    metadata = _champion_metadata(_load_json(json_path, "champions JSON"))
    fields = (
        "lob_id",
        "org_name",
        "org_side",
        "covered_years",
        "controls_used",
        "bioguide_id",
        "member_name",
        "party",
        "chamber",
        "champion_rank",
        "champion_score",
        "sector_relative_score",
        "sector_rank",
        "raw_n_bills",
        "years_present",
        "direction_of_travel",
        "r2",
        "n_members_modeled",
    )
    kept = defaultdict(list)
    totals = defaultdict(int)
    total_bills = defaultdict(int)
    kept_bills = defaultdict(int)
    member_names = {}
    member_flags = {}
    csv_rows = 0
    eligible_rows = 0
    eligible_orgs = set().union(*orgs_by_sector.values()) if orgs_by_sector else set()
    for row_number, row in _iter_csv(csv_path, "champions CSV", fields):
        csv_rows += 1
        lob_id = (row["lob_id"] or "").strip()
        member = (row["bioguide_id"] or "").strip()
        if not lob_id or not member:
            raise IngestError(f"champions row {row_number} has blank identity")
        record = resolver.resolve(member)
        member_name = (row["member_name"] or "").strip()
        # A champions row whose member_name is blank or is just the bioguide
        # again (legislators.csv carries at least one roster row with no
        # full_name) must NOT reach the page as a raw identifier.
        if not member_name or member_name == member:
            member_name = record["name"]
        if lob_id not in metadata:
            raise IngestError(f"champions CSV organization absent from JSON: {lob_id}")
        previous = member_names.get(member)
        if previous is not None and previous != member_name:
            raise IngestError(f"champions CSV gives conflicting names for {member}")
        member_names[member] = member_name
        member_flags[member] = _member_flag(record)
        raw_bills = _integer(row["raw_n_bills"], f"champions row {row_number} raw_n_bills")
        totals[lob_id] += 1
        total_bills[lob_id] += raw_bills
        if lob_id not in eligible_orgs:
            continue
        eligible_rows += 1
        raw_rank = _integer(
            row["champion_rank"], f"champions row {row_number} champion_rank", minimum=1
        )
        sector_rank = None
        if (row["sector_rank"] or "").strip():
            sector_rank = _integer(
                row["sector_rank"], f"champions row {row_number} sector_rank", minimum=1
            )
        if raw_rank > CHAMPION_LEADER_LIMIT and (
            sector_rank is None or sector_rank > CHAMPION_LEADER_LIMIT
        ):
            continue
        kept_bills[lob_id] += raw_bills
        # Posture here is this ORGANISATION's trajectory with this member, read
        # off the same strict network series the attention table ranks on.
        org_series = (org_attention or {}).get((lob_id, member), {})
        org_verdict = postures.encode(
            [org_series.get(year, 0) for year in YEARS]
        )
        kept[lob_id].append(
            {
                "i": member,
                "n": member_name,
                "f": member_flags[member],
                "g": org_verdict,
                "p": (row["party"] or "").strip(),
                "h": (row["chamber"] or "").strip(),
                "r": raw_rank,
                "c": _number(
                    row["champion_score"], f"champions row {row_number} champion_score"
                ),
                "s": _number(
                    row["sector_relative_score"],
                    f"champions row {row_number} sector_relative_score",
                    allow_null=True,
                ),
                "q": sector_rank,
                "b": raw_bills,
                "y": _integer(
                    row["years_present"], f"champions row {row_number} years_present"
                ),
                "d": (row["direction_of_travel"] or "").strip() or "—",
            }
        )

    organizations_payload = {}
    for sector in sorted(orgs_by_sector):
        values = []
        for lob_id in sorted(
            orgs_by_sector[sector], key=lambda item: (organizations[item]["name"], item)
        ):
            meta = metadata.get(lob_id)
            if meta is None:
                raise IngestError(f"active organization absent from champions JSON: {lob_id}")
            controls = meta.get("controls_used")
            years = meta.get("covered_years")
            if not isinstance(controls, list) or not isinstance(years, list):
                raise IngestError(f"champions JSON metadata malformed for {lob_id}")
            retained = sorted(kept.get(lob_id, ()), key=lambda row: (row["r"], row["i"]))
            omitted = max(0, totals[lob_id] - len(retained))
            values.append(
                {
                    "id": lob_id,
                    "name": organizations[lob_id]["name"],
                    "years": years,
                    "r2": meta.get("r2"),
                    "controls": ", ".join(str(item) for item in controls),
                    "skipped": meta.get("skipped_reason"),
                    "modeled": meta.get("n_members_modeled"),
                    "rows": retained,
                    "total": totals[lob_id],
                    "omitted": omitted,
                    "omitted_bills": max(0, total_bills[lob_id] - kept_bills[lob_id]),
                }
            )
        organizations_payload[sector] = values
    retained_rows = sum(len(rows) for rows in kept.values())
    return organizations_payload, member_names, {
        "input_rows": csv_rows,
        "sector_eligible_rows": eligible_rows,
        "retained_rows": retained_rows,
        "long_tail_rows": eligible_rows - retained_rows,
        "unmatched_sector_rows": csv_rows - eligible_rows,
        "omitted_rows": csv_rows - retained_rows,
        "leader_limit": CHAMPION_LEADER_LIMIT,
    }


class PostureTable:
    """Classifies attention series and interns the result.

    The RULE lives in lobby_posture and runs here, at build time -- there is no
    JavaScript copy of it to drift.  What ships per row is five values,
    ``[stateIndex, recent, prior, partial, delta]``; the words belonging to each
    state ship once in ``payload()``.  Carrying the full derivation sentence on
    every row instead cost 3.4 MB on these two pages and pushed both over their
    size guards.
    """

    LAYOUT = ("state", "recent", "prior", "partial", "delta")

    def __init__(self):
        self.names = []
        self._index = {}
        self.counts = {}

    def encode(self, values):
        verdict = posture.classify_values(list(values), first_year=YEARS[0])
        name = verdict["state"]
        index = self._index.get(name)
        if index is None:
            index = len(self.names)
            self._index[name] = index
            self.names.append(name)
        self.counts[name] = self.counts.get(name, 0) + 1
        return [
            index,
            verdict["recent"],
            verdict["prior"],
            verdict["partial"],
            verdict["delta"],
        ]

    def payload(self):
        return [
            {
                "n": name,
                "b": posture.STATES[name][0],
                "p": posture.STATES[name][1],
                "t": posture.STATES[name][2],
                "m": posture.STATES[name][3],
            }
            for name in self.names
        ]

    def receipt(self):
        return posture.summarize_counts(self.counts)


def _attention_payload(
    attention,
    member_names,
    spend,
    organizations_payload,
    resolver,
    postures,
    roster_families,
):
    industries = []
    for sector in sorted(spend):
        members = []
        for bioguide, by_year in attention.get(sector, {}).items():
            values = [by_year.get(year, 0) for year in YEARS]
            # The network spans 2021-2026, so most of these bioguides are NOT on
            # the current roster and champions.csv cannot name them.  Resolving
            # here is what stops "M001156" from being the printed name.
            record = resolver.resolve(bioguide)
            verdict = postures.encode(values)
            members.append(
                {
                    "id": bioguide,
                    "name": member_names.get(bioguide) or record["name"],
                    "flag": _member_flag(record),
                    "values": values,
                    "total": sum(values),
                    "change": values[-1] - values[-2],
                    "posture": verdict,
                }
            )
        members.sort(key=lambda row: (-row["total"], row["name"], row["id"]))
        industries.append(
            {
                "sector": sector,
                "members": members,
                "organizations": organizations_payload.get(sector, []),
                # The annual series travels with the sector so the level-2 tier
                # view reads the same numbers the level-1 card was drawn from.
                "spend": spend.get(sector, []),
                "roster": roster_families.get(sector, []),
            }
        )
    return industries


def _defensible_configuration(report):
    configurations = report.get("candidate_configurations") if isinstance(report, dict) else None
    if not isinstance(configurations, dict):
        raise IngestError("cosponsor report lacks candidate_configurations")
    marked = [
        (name, value)
        for name, value in configurations.items()
        if isinstance(value, dict) and value.get("role") == "defensible_headline"
    ]
    if len(marked) == 1:
        return marked[0]
    preferred = report.get("headline_candidate_configuration")
    if preferred in configurations and isinstance(configurations[preferred], dict):
        return preferred, configurations[preferred]
    raise IngestError("cosponsor report does not identify one defensible headline configuration")


def _forecast_metrics(configuration_name, configuration):
    splits = configuration.get("per_split")
    if not isinstance(splits, list) or not splits:
        raise IngestError("defensible forecast configuration lacks per_split")
    primary = next(
        (split for split in splits if isinstance(split, dict) and split.get("role") == "primary"),
        splits[0],
    )
    metrics = primary.get("metrics") if isinstance(primary, dict) else None
    if not isinstance(metrics, dict):
        raise IngestError("defensible forecast primary split lacks metrics")
    model = metrics.get("model")
    baselines = metrics.get("baselines")
    if not isinstance(model, dict) or not isinstance(baselines, dict):
        raise IngestError("defensible forecast metrics lack model/baselines")
    required_baselines = (
        "B1_member_propensity",
        "B2_sponsor_affinity",
        "B3_party_match",
    )
    if any(name not in baselines for name in required_baselines):
        raise IngestError("defensible forecast metrics do not contain all three baselines")
    metric_fields = (
        "auc",
        "average_precision",
        "precision_at_10",
        "precision_at_25",
        "precision_at_50",
    )

    def metric_row(name, label, values):
        return {
            "name": name,
            "label": label,
            **{
                field: _number(values.get(field), f"forecast {name} {field}")
                for field in metric_fields
            },
        }

    rows = [metric_row("model", "Model", model)]
    labels = {
        "B1_member_propensity": "B1 · member propensity",
        "B2_sponsor_affinity": "B2 · sponsor affinity",
        "B3_party_match": "B3 · party match",
    }
    rows.extend(metric_row(name, labels[name], baselines[name]) for name in required_baselines)
    verdict = configuration.get("verdict")
    if not isinstance(verdict, dict) or not verdict.get("headline"):
        raise IngestError("defensible forecast configuration lacks verdict headline")
    return {
        "configuration": configuration_name,
        "train": primary.get("train_congress"),
        "test": primary.get("test_congress"),
        "base_rate": _number(metrics.get("base_rate"), "forecast base_rate"),
        "rows": rows,
        "verdict": str(verdict["headline"]),
        "comparison_rule": str(verdict.get("comparison_rule") or ""),
    }


def _bill_label(congress, bill):
    label = re.sub(r"\s+", " ", bill.strip().upper())
    replacements = {
        "HCONRES": "H.Con.Res.",
        "HJRES": "H.J.Res.",
        "HRES": "H.Res.",
        "SCONRES": "S.Con.Res.",
        "SJRES": "S.J.Res.",
        "SRES": "S.Res.",
        "HR": "H.R.",
        "S": "S.",
    }
    parts = label.split(" ", 1)
    if parts and parts[0] in replacements:
        label = replacements[parts[0]] + (" " + parts[1] if len(parts) > 1 else "")
    return f"{congress} · {label}"


def _load_forecast(report_path, scores_path, member_names, resolver):
    report = _load_json(report_path, "cosponsor forecast report")
    configuration_name, configuration = _defensible_configuration(report)
    metrics = _forecast_metrics(configuration_name, configuration)
    fields = (
        "candidate_configuration",
        "congress",
        "bill",
        "member",
        "predicted_probability",
        "actual",
        "baseline_member_propensity",
        "baseline_member_propensity_probability",
        "baseline_sponsor_affinity",
        "baseline_sponsor_affinity_probability",
        "baseline_party_match",
    )
    heaps = defaultdict(list)
    input_rows = 0
    configuration_rows = 0
    missing_member_names = set()
    for row_number, row in _iter_csv(scores_path, "cosponsor scores", fields):
        input_rows += 1
        if (row["candidate_configuration"] or "").strip() != configuration_name:
            continue
        configuration_rows += 1
        congress = _integer(row["congress"], f"cosponsor score row {row_number} congress")
        bill = (row["bill"] or "").strip()
        member = (row["member"] or "").strip()
        if not bill or not member:
            raise IngestError(f"cosponsor score row {row_number} has blank bill/member")
        probability = _number(
            row["predicted_probability"],
            f"cosponsor score row {row_number} predicted_probability",
        )
        if probability < 0.0 or probability > 1.0:
            raise IngestError(f"cosponsor score row {row_number} probability outside [0,1]")
        actual = None
        if (row["actual"] or "").strip():
            actual = _integer(row["actual"], f"cosponsor score row {row_number} actual")
            if actual not in (0, 1):
                raise IngestError(f"cosponsor score row {row_number} actual must be 0/1")
        if member not in member_names:
            missing_member_names.add(member)
        key = (congress, bill)
        item = (probability, member, -1 if actual is None else actual)
        heap = heaps[key]
        if len(heap) < FORECAST_LEADER_LIMIT:
            heapq.heappush(heap, item)
        elif item > heap[0]:
            heapq.heapreplace(heap, item)
    if not heaps:
        raise IngestError("cosponsor scores contain no rows for defensible configuration")
    bills = []
    for (congress, bill), heap in sorted(heaps.items(), key=lambda item: item[0]):
        rows = []
        for probability, member, actual_code in sorted(
            heap, key=lambda item: (-item[0], item[1])
        ):
            record = resolver.resolve(member)
            rows.append(
                {
                    "member": member,
                    "name": member_names.get(member) or record["name"],
                    "flag": _member_flag(record),
                    "probability": probability,
                    "actual": None if actual_code < 0 else actual_code,
                }
            )
        bills.append(
            {
                "key": f"{congress}|{bill}",
                "label": _bill_label(congress, bill),
                "rows": rows,
            }
        )
    kept_rows = sum(len(bill["rows"]) for bill in bills)
    metrics["bills"] = bills
    metrics["receipt"] = {
        "input_rows": input_rows,
        "configuration_rows": configuration_rows,
        "retained_rows": kept_rows,
        "omitted_rows": configuration_rows - kept_rows,
        "leader_limit": FORECAST_LEADER_LIMIT,
        "bills": len(bills),
        "missing_member_names": len(missing_member_names),
    }
    return metrics


def _display_sector(sector):
    return sector.replace("_", " ").title()


def _money(value):
    absolute = abs(value)
    if absolute >= 1_000_000_000:
        amount, suffix = value / 1_000_000_000, "B"
    elif absolute >= 1_000_000:
        amount, suffix = value / 1_000_000, "M"
    elif absolute >= 1_000:
        amount, suffix = value / 1_000, "k"
    else:
        return f"${value:,.0f}"
    compact = f"{amount:.1f}"
    if compact.endswith(".0"):
        compact = compact[:-2]
    return f"${compact}{suffix}"


def _spend_series_markup(label, css_class, field, rows, maximum, headline=False):
    points = []
    labels = []
    for index, row in enumerate(rows):
        x = 8.0 + index * 48.0
        y = 48.0 - (40.0 * row[field] / maximum if row[field] else 0.0)
        points.append(f"{x:.1f},{y:.1f}")
        year_label = "2026 partial year" if row["year"] == 2026 else str(row["year"])
        value_label = _money(row[field])
        labels.append(f"{year_label}: {value_label}")
    solid_points = " ".join(points[:5])
    first_x, first_y = points[0].split(",")
    fifth_x, fifth_y = points[4].split(",")
    last_x, last_y = points[5].split(",")
    area = f"M8 48 L{first_x} {first_y} " + " ".join(
        f"L{point.replace(',', ' ')}" for point in points[1:5]
    ) + f" L{fifth_x} 48 Z"
    partial_area = (
        f"M{fifth_x} 48 L{fifth_x} {fifth_y} "
        f"L{last_x} {last_y} L{last_x} 48 Z"
    )
    class_names = "series headline-series" if headline else "series"
    return (
        f"<div class=\"{class_names}\"><span class=seriesname>{html.escape(label)}</span>"
        f"<svg class=money-spark data-series={css_class} viewBox=\"0 0 256 56\" "
        f"role=img aria-label=\"{html.escape(label)}. "
        f"Shared dollar scale within this sector. 2026 partial year is dashed. "
        f"{html.escape('; '.join(labels))}\">"
        f"<title>{html.escape(label)} — shared dollar scale within this sector — "
        f"{html.escape('; '.join(labels))}</title>"
        "<path class=sparkbase d=\"M8 48H248\"></path>"
        f"<path class=sparkarea d=\"{area}\"></path>"
        f"<path class=\"sparkarea partial-area\" d=\"{partial_area}\"></path>"
        f"<polyline class=sparkline points=\"{solid_points}\"></polyline>"
        f"<line class=partial-segment x1={fifth_x} y1={fifth_y} "
        f"x2={last_x} y2={last_y}></line>"
        f"<circle class=last-dot cx={last_x} cy={last_y} r=3.5></circle></svg>"
        f"<strong class=seriesvalue>{html.escape(_money(rows[-1][field]))}</strong>"
        "</div>"
    )


TIER_COLORS = {
    "big": "#58a6ff",
    "community": "#7ee787",
    "mixed": "#e3b341",
    "unclassified": "#8b949e",
}
EVIDENCE_GLYPHS = {
    "documented": "■",      # filled square: solid fill
    "part-inferred": "▤",   # ruled square: light hatch
    "mostly-inferred": "▥",  # cross-ruled square: dense hatch
}


def _hatch_defs():
    """One SVG sprite of hatch patterns, emitted once for the whole page.

    Evidence strength has to survive a screenshot, so it is carried by the FILL
    itself rather than by a caption or a colour: solid means documented, a hatch
    means default-classified.  Patterns need explicit colours (a pattern does not
    reliably inherit currentColor), so there is one per tier per density.
    """
    patterns = []
    for name in BANK_TIER_ORDER:
        color = TIER_COLORS[name]
        for level, size, width in (("light", 8, 1.2), ("dense", 5, 2.0)):
            patterns.append(
                f'<pattern id="hx-{name}-{level}" width="{size}" height="{size}" '
                'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                f'<rect width="{size}" height="{size}" fill="{color}" opacity=".16"></rect>'
                f'<line x1="0" y1="0" x2="0" y2="{size}" stroke="{color}" '
                f'stroke-width="{width}" opacity=".9"></line></pattern>'
            )
    return (
        '<svg class=svgdefs width=0 height=0 aria-hidden=true focusable=false>'
        "<defs>" + "".join(patterns) + "</defs></svg>"
    )


def _tier_fill(name, level):
    if level == "documented":
        return TIER_COLORS[name]
    suffix = "light" if level == "part-inferred" else "dense"
    return f"url(#hx-{name}-{suffix})"


def _tier_stack_markup(label, field, rows, maximum, order):
    """Stacked bars, one column per year, EVERY tier present.

    A stack that dropped `mixed` would show big and community as if they were the
    whole sector; they are not, so all four ride in every column and the columns
    sum to the published sector total.
    """
    bars = []
    captions = []
    for index, row in enumerate(rows):
        center = 8.0 + index * 48.0
        x = center - 15.0
        baseline = 48.0
        segments = []
        year_label = "2026 partial year" if row["year"] == 2026 else str(row["year"])
        pieces = []
        for name in order:
            tier = row["tiers"][name]
            value = tier[field]
            evidence = tier["evidence"][field]
            if value <= 0:
                continue
            height = 40.0 * value / maximum
            baseline -= height
            segments.append(
                f'<rect class="tierseg" x="{x:.1f}" y="{baseline:.2f}" width="30" '
                f'height="{height:.2f}" fill="{_tier_fill(name, evidence["level"])}">'
                f"<title>{html.escape(year_label)} · {html.escape(BANK_TIER_LABELS[name])}"
                f" · {html.escape(_money(value))} · {html.escape(evidence['label'])}"
                f" ({evidence['share']:.0%} default-classified)</title></rect>"
            )
            pieces.append(
                f"{BANK_TIER_SHORT[name]} {_money(value)} ({evidence['label']})"
            )
        bars.append("".join(segments))
        captions.append(f"{year_label}: " + ", ".join(pieces))
    total = sum(row["tiers"][name][field] for name in order for row in rows[-1:])
    return (
        '<div class="series tierseries">'
        f"<span class=seriesname>{html.escape(label)}</span>"
        '<svg class="money-spark tier-stack" viewBox="0 0 256 56" role=img '
        f'aria-label="{html.escape(label)}. Stacked by bank tier on the same dollar '
        "scale as the series above. Solid fill is documented; a diagonal hatch means "
        "the dollars were default-classified rather than positively identified. "
        f'{html.escape("; ".join(captions))}">'
        f"<title>{html.escape(label)} — {html.escape('; '.join(captions))}</title>"
        '<path class=sparkbase d="M8 48H248"></path>'
        + "".join(bars)
        + "</svg>"
        f"<strong class=seriesvalue>{html.escape(_money(total))}</strong></div>"
    )


def _tier_legend(rows, order):
    latest_full = rows[4]
    swatches = []
    for name in order:
        evidence = latest_full["tiers"][name]["evidence"]
        level = max(
            (evidence[field]["level"] for field in ("in_house", "hired_firms")),
            key=lambda value: [item[1] for item in EVIDENCE_LEVELS].index(value),
        )
        swatches.append(
            f'<span class="tierkey"><span class="tierswatch t-{name} ev-{level}" '
            f"aria-hidden=true></span>{html.escape(BANK_TIER_SHORT[name])}</span>"
        )
    return "<span class=tierlegend>" + "".join(swatches) + "</span>"


def _tier_evidence_note(rows, order):
    """Name the inferred series in words as well as in fill."""
    latest_full = rows[4]
    year = latest_full["year"]
    inferred = []
    solid = []
    for name in order:
        tier = latest_full["tiers"][name]
        for field, field_label in (("in_house", "in-house"), ("hired_firms", "fees")):
            evidence = tier["evidence"][field]
            if not evidence["total"]:
                continue
            phrase = (
                f"{BANK_TIER_SHORT[name].casefold()} {field_label} "
                f"{evidence['share']:.0%} default-classified"
            )
            if evidence["level"] == "documented":
                solid.append((name, field, phrase, evidence))
            else:
                inferred.append(phrase)
    sentences = []
    if inferred:
        sentences.append(
            "Hatched fills are inference: " + "; ".join(inferred) + "."
        )
    # The contrast is the point: the two community series are not equally
    # trustworthy, so the solid one is named as positively identified.
    for name, field, _phrase, evidence in solid:
        if name == "community":
            sentences.append(
                f"Solid fills are positive identifications: community "
                f"{'in-house' if field == 'in_house' else 'fees'} is "
                f"{1 - evidence['share']:.0%} positively identified."
            )
    sentences.append(f"Shares shown for {year}, the latest full year.")
    return "<span class=tiernote>" + html.escape(" ".join(sentences)) + "</span>"


def _industry_cards(spend, tier_meta):
    cards = []
    tier_sectors = set(tier_meta.get("sectors") or ())
    order = tier_meta.get("order") or []
    for index, sector in enumerate(sorted(spend)):
        rows = spend[sector]
        latest = rows[-1]
        maximum = max((row["total"] for row in rows), default=0.0) or 1.0
        tier_block = ""
        if sector in tier_sectors and order:
            tier_block = (
                "<span class=breakdown-label>Bank tier · within each series</span>"
                + _tier_stack_markup(
                    "Hired firms by tier", "hired_firms", rows, maximum, order
                )
                + _tier_stack_markup(
                    "In-house by tier", "in_house", rows, maximum, order
                )
                + _tier_legend(rows, order)
                + _tier_evidence_note(rows, order)
            )
        cards.append(
            f"<button class=industry-card type=button data-sector=\"{html.escape(sector)}\" "
            f"aria-pressed=false aria-label=\"Open {_display_sector(sector)} industry; "
            f"latest total lobbying spend {_money(latest['total'])}\">"
            f"<span class=cardname><span class=\"sector-dot dot-{index % 6}\" "
            f"aria-hidden=true></span>{html.escape(_display_sector(sector))}</span>"
            + _spend_series_markup(
                "Total lobbying spend", "total", "total", rows, maximum, headline=True
            )
            + "<span class=breakdown-label>Breakdown</span>"
            + _spend_series_markup(
                "Hired firms", "hired", "hired_firms", rows, maximum
            )
            + _spend_series_markup(
                "In-house", "inhouse", "in_house", rows, maximum
            )
            + tier_block
            + "<span class=yeargrid><span>2021</span><span>2022</span><span>2023</span>"
            "<span>2024</span><span>2025</span><span>2026 partial</span></span>"
            f"<span class=cardcounts>{latest['orgs']:,} organizations · "
            f"{latest['lobbyists']:,} named lobbyists</span>"
            "<span class=partial>2026 · PARTIAL YEAR through Q2</span>"
            "</button>"
        )
    return "".join(cards)


def _metric_table(forecast):
    rows = []
    for row in forecast["rows"]:
        cells = "".join(
            f"<td class=num>{row[field]:.3f}</td>"
            for field in (
                "auc",
                "average_precision",
                "precision_at_10",
                "precision_at_25",
                "precision_at_50",
            )
        )
        rows.append(f"<tr><th scope=row>{html.escape(row['label'])}</th>{cells}</tr>")
    return (
        "<div class=tablewrap><table class=metrics><thead><tr><th>Predictor</th>"
        "<th class=num>AUC</th><th class=num>Average precision</th><th class=num>Precision@10</th>"
        "<th class=num>Precision@25</th><th class=num>Precision@50</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _json_for_script(payload):
    text = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return (
        text.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _hash_footer(input_paths, hashes):
    items = []
    for label, path in input_paths:
        items.append(
            "<li><code>"
            + html.escape(os.path.basename(path))
            + "</code><span>SHA-256 "
            + hashes[label]
            + "</span></li>"
        )
    return "".join(items)


def _document(cards, payload, forecast, hashes_markup):
    forecast_receipt = forecast["receipt"]
    champion_receipt = payload["receipts"]["champions"]
    sector_receipt = payload["receipts"]["sectors"]
    bill_receipt = payload["receipts"]["bills"]
    repository_receipt = bill_receipt["repository"]
    data_json = _json_for_script(payload)
    style = """
<style>
:root{color-scheme:dark;--bg:#0d1117;--bar:#11161d;--panel:#161b22;--panel-hover:#1b2230;--text:#e6edf3;--text-soft:#c9d1d9;--muted:#8b949e;--faint:#6e7681;--border:#30363d;--rule:#21262d;--blue:#1f6feb;--blue-bright:#58a6ff;--blue-hover:#388bfd;--green:#16a34a;--green-text:#7ee787;--red:#dc2626;--red-text:#ff7b72;--amber:#d29922;--amber-text:#e3b341;--purple:#bc8cff;--teal:#39d0d8;--radius:6px;--radius-sm:4px;--shadow:0 8px 24px rgba(0,0,0,.24)}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;overflow-x:hidden;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
button,input,select{font:inherit}
a{color:inherit}
.skiplink{position:fixed;z-index:100;background:var(--blue);color:#fff}
.product-header{display:flex;align-items:center;background:var(--bar);border-bottom:1px solid var(--border)}
.product-title{min-width:0;flex:1}
.desklink{border:1px solid var(--border);border-radius:var(--radius-sm);color:var(--text-soft);text-decoration:none}
.sitenav{display:flex;flex-wrap:wrap;align-items:center}
/* Surface tabs. The three Moneyball surfaces are separate documents, so these
   are anchors wearing a tab's clothes: the current one is marked aria-current
   and is not a link, which is what makes "you are here" legible. */
.tabstrip{display:flex;flex-wrap:wrap;align-items:flex-end;border-bottom:1px solid var(--border)}
.tab{position:relative;display:inline-flex;align-items:center;border:1px solid transparent;border-bottom:0;color:var(--muted);text-decoration:none;white-space:nowrap}
.tab:hover{color:var(--text)}
.tab[aria-current=page]{background:var(--panel);border-color:var(--border);color:#fff}
.tab[aria-current=page]::after{content:"";position:absolute;left:0;right:0;top:-1px;height:2px;background:var(--accent-bright)}
.postbadge{display:inline-flex;align-items:center;border:1px solid transparent;border-radius:999px;white-space:nowrap;font-weight:700}
.postbadge .pdot{border-radius:50%;flex:0 0 auto}
.postbadge.cultivating{border-color:rgba(126,231,135,.42);background:rgba(22,163,74,.14);color:var(--green-text)}
.postbadge.cultivating .pdot{background:var(--green-text)}
.postbadge.maintaining{border-color:rgba(88,166,255,.40);background:rgba(31,111,235,.14);color:var(--blue-bright)}
.postbadge.maintaining .pdot{background:var(--blue-bright)}
.postbadge.disengaging{border-color:rgba(255,123,114,.44);background:rgba(220,38,38,.14);color:var(--red-text)}
.postbadge.disengaging .pdot{background:var(--red-text)}
.postbadge.unknown{border-color:var(--border);background:rgba(139,148,158,.12);color:var(--muted)}
.postbadge.unknown .pdot{background:var(--faint)}
.postdelta{color:var(--muted);font-variant-numeric:tabular-nums}
.memberlink{color:inherit;text-decoration:none;border-bottom:1px dotted #3d6ea8}
.memberlink:hover{color:#fff;border-bottom-color:var(--accent)}
.section-nav{position:sticky;top:0;z-index:40;display:flex;overflow-x:auto;background:rgba(13,17,23,.96);border-bottom:1px solid var(--border)}
main{margin:0 auto}
.num,.money,.stat strong,.rowcount,.metric,.count{font-variant-numeric:tabular-nums}
.hero{display:grid;align-items:stretch}
.banner,.hero-stats,.panel{border:1px solid var(--border);border-radius:var(--radius);background:var(--panel)}
.banner{background:linear-gradient(135deg,rgba(31,111,235,.2),rgba(188,140,255,.08));border-color:rgba(88,166,255,.42)}
.hero-stats{display:grid}
.stat{display:flex;flex-direction:column;border-right:1px solid var(--rule)}
.stat:last-child{border-right:0}
.section-head,.panelhead{display:flex;align-items:end;justify-content:space-between}
.panel{box-shadow:var(--shadow)}
.honesty{border:1px solid rgba(227,179,65,.32);border-radius:var(--radius-sm);background:rgba(210,153,34,.08);color:var(--text-soft)}
.industry-picker{display:grid}
.industry-card{position:relative;min-width:0;text-align:left;color:var(--text);border:1px solid var(--border);border-radius:var(--radius);background:var(--panel);cursor:pointer}
.series{display:grid;align-items:center}
.money-spark{display:block;width:100%;overflow:visible}
.yeargrid{display:grid}
.cardcounts,.partial{display:block}
.toggle{display:flex;width:max-content;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg)}
.toggle button{border:0;border-radius:var(--radius-sm);background:transparent;color:var(--text-soft);cursor:pointer}
.subsection{border:1px solid var(--rule);border-radius:var(--radius-sm)}
.tabletop{display:flex;align-items:center;justify-content:space-between}
.rowcount{margin:0;font-variant-numeric:tabular-nums}
.tablewrap{max-width:100%;overflow:auto;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--bg)}
table{width:100%;border-collapse:separate;border-spacing:0}
th,td{border-bottom:1px solid var(--rule);color:var(--text-soft);white-space:nowrap}
thead th{position:sticky;top:0;z-index:2;background:#151b23;color:var(--muted);text-align:left}
td.num,th.num{text-align:right}
tbody tr:nth-child(even){background:rgba(255,255,255,.018)}
tbody tr:hover{background:rgba(88,166,255,.075)}
.member{white-space:normal}
button{color:inherit}
.sortbtn,.disclosure{border:0;background:transparent;cursor:pointer}
.sortbtn{text-align:left}
.detailrow td{white-space:normal;background:#10151c}
.detailbox{border-left:2px solid var(--blue)}
.chip{display:inline-flex;align-items:center;border:1px solid transparent;border-radius:999px;white-space:nowrap}
.chip.support{border-color:rgba(126,231,135,.42);background:rgba(22,163,74,.14);color:var(--green-text)}
.chip.oppose{border-color:rgba(255,123,114,.44);background:rgba(220,38,38,.14);color:var(--red-text)}
.chip.neutral{border-color:rgba(227,179,65,.48);background:rgba(210,153,34,.13);color:var(--amber-text)}
.legend{display:flex;flex-wrap:wrap}
.bill-summary{display:grid}
.filters{display:grid}
.field input,.field select{width:100%;border:1px solid var(--border);border-radius:var(--radius-sm);background:#0b1016;color:var(--text)}
.clearbutton{border:1px solid var(--border);border-radius:var(--radius-sm);background:#151b23;cursor:pointer}
.empty{border:1px dashed var(--border);border-radius:var(--radius-sm);color:var(--muted);text-align:center}
.hidden{display:none!important}
.orgmeta{display:grid}
.metabox{border:1px solid var(--rule);border-radius:var(--radius-sm)}
.forecastgrid{display:grid}
.verdict{border-left:2px solid var(--purple);background:rgba(188,140,255,.08)}
.bill-picker{width:100%;border:1px solid var(--border);border-radius:var(--radius-sm);background:#0b1016;color:var(--text)}
footer{border-top:1px solid var(--border);color:var(--muted)}
.hashes{overflow:auto;border:1px solid var(--border);border-radius:var(--radius-sm);background:#090d12;color:var(--text-soft);white-space:pre-wrap;word-break:break-all}
.pos{color:var(--green-text)}.neg{color:var(--red-text)}.zero{color:var(--amber-text)}
/* ---- bank tier ----------------------------------------------------------
   Tier colour identifies WHICH tier; tier FILL identifies how well evidenced it
   is.  The two are independent channels on purpose: colour alone would be lost
   to a colour-blind reader and to a greyscale print, and a caption alone would
   be lost the moment somebody screenshots the chart.  Hatch travels with the
   pixels. */
.svgdefs{position:absolute;width:0;height:0;overflow:hidden}
.tier-stack .tierseg{stroke:var(--panel);stroke-width:.5}
.tierlegend,.tierevidence{display:flex;flex-wrap:wrap}
.tierkey{display:inline-flex;align-items:center}
.tierswatch{flex:0 0 auto;border-radius:2px;border:1px solid rgba(255,255,255,.18)}
.tierswatch.t-big{background:#58a6ff}.tierswatch.t-community{background:#7ee787}
.tierswatch.t-mixed{background:#e3b341}.tierswatch.t-unclassified{background:#8b949e}
/* The legend swatch wears the same fill the chart does, so the legend teaches
   the hatch rather than merely naming it. */
.tierswatch.ev-part-inferred{background-image:repeating-linear-gradient(45deg,rgba(13,17,23,.85) 0 1.5px,transparent 1.5px 5px)}
.tierswatch.ev-mostly-inferred{background-image:repeating-linear-gradient(45deg,rgba(13,17,23,.85) 0 2px,transparent 2px 4px)}
.tiernote{display:block;color:var(--muted)}
.evchip{display:inline-flex;align-items:center;border:1px solid transparent;border-radius:999px;white-space:nowrap;font-weight:700}
.evchip.documented{border-color:rgba(126,231,135,.42);background:rgba(22,163,74,.14);color:var(--green-text)}
.evchip.part-inferred{border-color:rgba(227,179,65,.48);background:rgba(210,153,34,.13);color:var(--amber-text)}
.evchip.mostly-inferred{border-color:rgba(255,123,114,.5);background:rgba(220,38,38,.14);color:var(--red-text);background-image:repeating-linear-gradient(45deg,rgba(255,123,114,.16) 0 3px,transparent 3px 7px)}
.tierbadge{display:inline-flex;align-items:center;border:1px solid var(--border);border-radius:var(--radius-sm);white-space:nowrap;font-weight:700;text-transform:uppercase}
.tierbadge .tdot{border-radius:50%;flex:0 0 auto}
.tierbadge.t-big .tdot{background:#58a6ff}.tierbadge.t-community .tdot{background:#7ee787}
.tierbadge.t-mixed .tdot{background:#e3b341}.tierbadge.t-unclassified .tdot{background:#8b949e}
.tierbadge.multi{border-style:dashed}
.boundary{border:1px solid rgba(188,140,255,.45);border-radius:var(--radius-sm);background:rgba(188,140,255,.10);color:var(--text-soft)}
.boundary b{color:#fff}
.mergebadge{display:inline-flex;align-items:center;border:1px dashed var(--purple);border-radius:var(--radius-sm);color:var(--purple);white-space:nowrap;font-weight:700;text-transform:uppercase}
.tierchart{display:grid}
.tiercol{min-width:0}
.tiercol svg{display:block;width:100%;overflow:visible}
.asof{display:inline-flex;align-items:center;border:1px solid var(--border);border-radius:999px;background:var(--bg);color:var(--text-soft);white-space:nowrap;font-weight:700}
@media(max-width:900px){.hero{grid-template-columns:1fr}.hero-stats{grid-template-columns:1fr}.stat{border-right:0;border-bottom:1px solid var(--rule)}.stat:last-child{border-bottom:0}.filters{grid-template-columns:1fr}.filters .searchfield{grid-column:auto}.bill-summary{grid-template-columns:1fr}.tabletop{align-items:start;flex-direction:column}}
</style>
"""

    style += """
<style>
/* Visual system: the 8px grid governs layout; table density has one documented exception below. */
:root{--fs-label:12px;--fs-body:14px;--fs-card:16px;--fs-section:22px;--fs-page:32px;--accent:#1f6feb;--accent-bright:#58a6ff;--accent-hover:#388bfd}
body{font-size:var(--fs-body)}.skiplink{left:16px;top:-64px;padding:8px 16px}.skiplink:focus{top:16px}
.product-header{flex-direction:column;align-items:stretch;gap:16px;padding:16px max(24px,calc((100vw - 1400px)/2 + 24px)) 0}.product-titlerow{display:flex;align-items:center;gap:16px}.product-title h1{font-size:var(--fs-page);font-weight:800;line-height:1.2}.product-title p{margin:8px 0 0}.desklink{padding:8px 16px;font-size:var(--fs-label);font-weight:700;transition:background 140ms ease-out,border-color 140ms ease-out,color 140ms ease-out}.desklink:hover{border-color:var(--accent)}.sitenav{gap:8px}
.tabstrip{gap:4px;margin-top:8px}.tab{gap:8px;padding:12px 24px;border-radius:var(--radius-sm) var(--radius-sm) 0 0;font-size:var(--fs-body);font-weight:700;transition:background 140ms ease-out,color 140ms ease-out}.tab .tabicon{font-size:var(--fs-label)}
.postbadge{gap:8px;padding:4px 12px;font-size:var(--fs-label)}.postbadge .pdot{width:8px;height:8px}.postdelta{margin-left:8px;font-size:var(--fs-label);font-weight:400}
.section-nav{gap:8px;padding:8px max(24px,calc((100vw - 1400px)/2 + 24px));backdrop-filter:blur(16px)}.section-nav .desklink:first-child{border-color:var(--border)}.section-nav .desklink.current{border-color:var(--accent);background:var(--accent);color:#fff}
main{width:min(100%,1400px);padding:32px 24px 64px}section{padding:32px 0}section[id],footer[id]{scroll-margin-top:64px}.eyebrow,.field label,.breakdown-label,.seriesname{font-size:var(--fs-label);font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}h2{font-size:var(--fs-section);font-weight:750;line-height:1.3}h3{margin:0 0 8px;font-size:var(--fs-card);font-weight:700;line-height:1.4}.subtle,.receipt,.rowcount{font-size:var(--fs-label)}
.hero{gap:16px}.banner{padding:24px}.stat{padding:16px}.stat strong{font-size:var(--fs-section);font-weight:800}.stat span{margin-top:8px;font-size:var(--fs-label);font-weight:700;letter-spacing:.06em;text-transform:uppercase}.section-head,.panelhead{gap:16px}.section-head{margin:0 0 16px}.panel{margin-top:32px;padding:32px}.honesty{margin:16px 0;padding:16px}.honesty p{margin:8px 0}
.figure-notes{margin:16px 0 0;padding:16px 0 0;border-top:1px solid var(--rule);color:var(--muted);font-size:var(--fs-label)}.figure-notes p{margin:0}.figure-notes p+p{margin-top:8px}.industry-picker{grid-template-columns:repeat(auto-fit,minmax(min(100%,400px),1fr));gap:16px;margin-top:16px}.industry-card{padding:24px;transition:background 140ms ease-out,border-color 140ms ease-out,box-shadow 140ms ease-out,transform 140ms ease-out}.industry-card:hover{background:var(--panel-hover);transform:translateY(-2px);box-shadow:var(--shadow)}.industry-card.active{border-color:var(--accent);background:var(--panel);box-shadow:inset 0 0 0 1px var(--accent)}
.cardname{display:flex;align-items:center;gap:8px;margin-bottom:16px;font-size:var(--fs-card);font-weight:700;text-transform:none;letter-spacing:0}.sector-dot{width:8px;height:8px;flex:0 0 8px;border-radius:50%;background:var(--accent-bright)}.dot-1{background:var(--purple)}.dot-2{background:var(--green-text)}.dot-3{background:var(--amber)}.dot-4{background:var(--red-text)}.dot-5{background:#2dd4bf}
.series{grid-template-columns:112px minmax(0,1fr) 72px;gap:8px;margin:8px 0}.headline-series{margin:0 0 16px;padding:16px 0;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}.headline-series .seriesname{color:var(--text-soft)}.headline-series .seriesvalue{font-size:var(--fs-section)}.seriesvalue{color:#fff;font-size:var(--fs-card);font-weight:800;font-variant-numeric:tabular-nums;text-align:right}.breakdown-label{display:block;margin:16px 0 8px}.money-spark{height:56px}.money-spark .sparkbase{fill:none;stroke:var(--rule);stroke-width:1}.money-spark .sparkline,.money-spark .partial-segment{fill:none!important;stroke:currentColor;stroke-width:2.5;stroke-linecap:round;stroke-linejoin:round}.money-spark .sparkarea{fill:currentColor;opacity:.13}.money-spark .partial-area{opacity:.05}.money-spark .partial-segment{stroke-dasharray:5 5;opacity:.7}.money-spark .last-dot{fill:var(--panel);stroke:currentColor;stroke-width:3}.money-spark[data-series=total]{color:var(--accent-bright)}.money-spark[data-series=hired]{color:var(--muted)}.money-spark[data-series=inhouse]{color:var(--purple)}.yeargrid{margin:8px 72px 0 120px;font-size:var(--fs-label);font-variant-numeric:tabular-nums}.cardcounts{margin-top:16px;font-variant-numeric:tabular-nums}.partial{margin-top:8px;font-size:var(--fs-label)}
.attention-spark-wrap{display:inline-flex;align-items:center;gap:8px}.attention-spark{color:var(--accent-bright);overflow:visible}.attention-spark .sparkline,.attention-spark .partial-segment{fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.attention-spark .sparkarea{fill:currentColor;opacity:.13}.attention-spark .partial-area{opacity:.05}.attention-spark .partial-segment{stroke-dasharray:4 4;opacity:.7}.attention-spark .last-dot{fill:var(--panel);stroke:currentColor;stroke-width:2}.attention-spark-wrap strong{color:#fff;font-variant-numeric:tabular-nums}
.toggle{gap:0;padding:0;overflow:hidden}.toggle button{padding:8px 16px;transition:background 140ms ease-out,color 140ms ease-out}.toggle button.active{background:var(--accent)}.subsection{margin-top:32px;padding-top:32px}.tabletop{gap:16px;margin:16px 0 8px}.tablewrap.subtable{max-height:320px;margin-top:8px}
/* Deliberate 4px-sub-grid exception: 12px vertical table padding optimizes scan-rate across thousands of rows; 16px horizontal padding remains on the 8px layout grid. */
th,td{padding:12px 16px}thead th{font-size:var(--fs-label);font-weight:700;letter-spacing:.06em;text-transform:uppercase}.titlecell{min-width:256px;max-width:480px}.orgbutton,.billbutton,.sortbutton{color:var(--accent-bright)}.billbutton{gap:8px}.billbutton::before{content:"▸";width:8px;transition:color 140ms ease-out,transform 140ms ease-out}.billbutton[aria-expanded=true]::before{content:"▸";transform:rotate(90deg)}.sort-indicator{width:16px;margin-left:8px}.bill-detail{padding:24px 32px 32px;transform-origin:top;animation:expand-row 140ms ease-out}.detail-head{gap:16px}.detail-title{font-size:var(--fs-card)}.channel{margin:0 8px 0 0;padding:0 8px;font-size:var(--fs-label)}.memberflag{display:inline-block;margin-left:8px;padding:0 8px;border:1px solid var(--amber);border-radius:4px;color:var(--amber);font-size:var(--fs-label);font-weight:700;letter-spacing:.06em;text-transform:uppercase;white-space:nowrap}.memberflag.unresolved{border-color:var(--red-text);color:var(--red-text)}@keyframes expand-row{from{opacity:0;transform:scaleY(.96) translateY(-8px)}to{opacity:1;transform:scaleY(1) translateY(0)}}
.chip{gap:8px;max-width:272px;padding:8px;font-size:var(--fs-label)}.chip-shape{font-size:var(--fs-label)}.legend-row{gap:8px 16px;margin:16px 0}.legend-unmarked{gap:8px;font-size:var(--fs-label)}.bill-summary{gap:16px;margin:16px 0;padding:16px}.bill-summary strong{font-size:var(--fs-card)}.bill-summary span{font-size:var(--fs-label)}.filters{grid-template-columns:minmax(224px,1.5fr) repeat(3,minmax(160px,.6fr)) auto;gap:8px;margin:16px 0}.field label{margin:0 0 8px}.field input,.field select{height:40px;padding:8px 16px}.clearbutton{height:40px;padding:8px 16px;transition:background 140ms ease-out,border-color 140ms ease-out,color 140ms ease-out}.empty{padding:32px 16px}.orgmeta{grid-template-columns:repeat(auto-fit,minmax(184px,1fr));gap:8px;margin:16px 0}.metabox{padding:16px}.forecastgrid{gap:16px}.verdict{margin:16px 0;padding:16px}.base{font-size:var(--fs-page)}#bill-picker{padding:8px 16px}
.tierseries{margin:4px 0 8px}.tierseries .seriesname{font-size:11px;letter-spacing:.04em;color:var(--faint)}.tierseries .seriesvalue{font-size:var(--fs-body);font-weight:700;color:var(--text-soft)}
.tierlegend{gap:8px 16px;margin:8px 0 0 120px;font-size:var(--fs-label);color:var(--muted)}.tierkey{gap:8px}.tierswatch{width:12px;height:12px}
.tiernote{margin:8px 0 0 120px;font-size:var(--fs-label);line-height:1.5}
.evchip{gap:8px;padding:2px 8px;font-size:11px;letter-spacing:.04em;text-transform:uppercase}
.tierbadge{gap:8px;padding:2px 8px;font-size:11px;letter-spacing:.06em}.tierbadge .tdot{width:8px;height:8px}
.boundary{margin:16px 0;padding:16px}.boundary p{margin:0}.boundary p+p{margin-top:8px}
.mergebadge{margin-left:8px;padding:0 8px;font-size:11px;letter-spacing:.06em}
.tierchart{grid-template-columns:repeat(auto-fit,minmax(min(100%,344px),1fr));gap:32px;margin:16px 0}.tiercol h4{margin:0 0 8px;font-size:var(--fs-card);font-weight:700}.tiercol .subtle{display:block;margin-bottom:8px}.tiercol svg{height:200px}
.asof{gap:8px;padding:4px 12px;font-size:var(--fs-label)}
.tiercontrols{display:flex;flex-wrap:wrap;align-items:end;gap:16px;margin:16px 0}.tiercontrols .field{min-width:160px}.tiercontrols .toggle{align-self:end}
footer{margin-top:32px;padding-top:32px;font-size:var(--fs-label)}footer h3{font-size:var(--fs-card)}.hashes li{grid-template-columns:minmax(208px,.8fr) minmax(384px,1.2fr);gap:16px;padding:8px 0}:where(button,select,input,a):focus-visible{outline:2px solid var(--accent);outline-offset:2px}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{animation-duration:1ms!important;transition-duration:1ms!important}}@media(max-width:900px){.section-nav{padding-inline:16px}main{padding:32px 16px 48px}.panel{padding:32px}.industry-picker{grid-template-columns:repeat(2,minmax(0,1fr))}.series{grid-template-columns:104px minmax(0,1fr) 64px}.yeargrid{margin-inline:112px 64px}.filters{grid-template-columns:repeat(2,minmax(0,1fr))}.titlecell{min-width:224px}}@media(max-width:720px){.industry-picker{grid-template-columns:1fr}}
</style>
"""
    body = f"""
</head><body>{_hatch_defs()}<a class=skiplink href=#main>Skip to content</a>
<header class=product-header><div class=product-titlerow><div class=product-title><div class=eyebrow>Moneyball · Industry intelligence</div><h1>Lobbying attention network</h1><p>Bill-level lobbying, industry attention, descriptive champions, and cosponsorship forecast · 2021–2026</p></div><nav class=sitenav aria-label="Page shortcuts"><a class=desklink href=#bills>Open bill explorer ▾</a></nav></div>
<nav class=tabstrip aria-label="Moneyball surfaces"><a class=tab href="Moneyball Dashboard.html"><span class=tabicon aria-hidden=true>◧</span>Main dashboard</a><a class=tab href="cu-member-desk.html"><span class=tabicon aria-hidden=true>▤</span>Member desk</a><a class=tab aria-current=page href="lobby-network.html"><span class=tabicon aria-hidden=true>◈</span>Industry</a></nav></header>
<nav class=section-nav aria-label=Dashboard sections><a class=desklink href=#industries>Industries</a><a class=desklink href=#champions>Champions</a><a class=desklink href=#bills>Bills</a><a class=desklink href=#forecast>Forecast</a></nav>
<main id=main>
<div class=hero><div class=banner><b>Coverage 2021–2026 from complete LDA sweeps (~540,000 filings)</b><br>This replaces the stale 2000–2022 LobbyView view. <b>2026 is a PARTIAL YEAR through Q2.</b></div><div class=hero-stats aria-label=Coverage summary><div class=stat><strong>{bill_receipt['bills']:,}</strong><span>lobbied bills</span></div><div class=stat><strong>{bill_receipt['links']:,}</strong><span>bill–organization links</span></div><div class=stat><strong>{bill_receipt['marked']:,}</strong><span>CU-marked bills</span></div></div></div>
<section id=industries aria-labelledby=picker-title><div class=section-head><div><div class=eyebrow>Level 1 · industries</div><h2 id=picker-title>Lobbying spend by industry</h2></div><span class=subtle>Total lobbying spend leads; hired firms and in-house operations show the mix beneath it.</span></div><div class=industry-picker>{cards}</div><div class=figure-notes><p><b>Hired firms</b> is money paid to outside lobbying firms the organizations retained; <b>In-house</b> is what they spent running their own lobbying operations.</p><p>All three lines share one dollar scale within each sector; the dashed final segment is partial-year 2026.</p><p>{html.escape(SPEND_PRECISION_NOTE)}</p><p>{html.escape(SPEND_NOTE)}</p></div></section>
<section class=panel id=industry-panel aria-labelledby=industry-title><div class=panelhead><div><div class=eyebrow>Level 2 · industry</div><h2 id=industry-title></h2><div class=subtle>2021–2026 (2026 partial year)</div></div><div><span class=eyebrow>Posture wording</span><div class=toggle aria-label="Posture wording"><button type=button data-posture-mode=posture class=active aria-pressed=true>Cultivating / Maintaining / Disengaging</button><button type=button data-posture-mode=trend aria-pressed=false>Rising / Steady / Falling</button></div></div></div>
<div class=honesty><p>{html.escape(ATTENTION_NOTE)}</p><p>{html.escape(CITATION_NOTE)}</p><p>{html.escape(WORKS_NOTE)}</p><p>{html.escape(FORMER_MEMBER_NOTE)}</p><p>Each network row counts distinct bills for one organization and member in one year. Industry totals sum those organization-level counts, so a bill cited by two organizations contributes once to each organization.</p><p><b>Posture.</b> {html.escape(posture.POSTURE_HONESTY_NOTE)}</p><p>{html.escape(posture.POSTURE_RULE_NOTE)}</p></div>
<div class=tabletop><div><h3>Member attention</h3><p class=subtle>Ranked by six-year bill-attention count; change is 2026 partial year versus full-year 2025. Open a member to read the filings behind the count.</p></div><p id=attention-count class=rowcount aria-live=polite></p></div><div class=tablewrap><table><thead><tr><th scope=col>Rank</th><th scope=col>Member</th><th scope=col>Posture</th><th scope=col class=num>2021–2026 count</th><th scope=col class=num>2026 partial Δ</th><th scope=col>2021–2026 sparkline</th><th scope=col>Filings</th></tr></thead><tbody id=attention-body></tbody></table></div>
<div class=subsection id=tier-roster><div class=panelhead><div><div class=eyebrow>As-of view · organizations</div><h3 id=roster-title>Who was on the roster</h3><div class=subtle id=roster-sub></div></div><span class=asof id=asof-chip></span></div>
<div class=tiercontrols><div class=field><label for=year-filter>Filing year</label><select id=year-filter></select></div><div class="field hidden" id=tier-filter-field><label for=tier-filter>Bank tier</label><select id=tier-filter><option value="">All tiers</option></select></div><div class="hidden" id=tier-view-field><span class=eyebrow>Tier chart</span><div class=toggle aria-label="Tier chart view"><button type=button data-tier-view=stacked class=active aria-pressed=true>Stacked</button><button type=button data-tier-view=grouped aria-pressed=false>Side by side</button></div></div></div>
<div class=honesty><p>{html.escape(YEAR_FILTER_NOTE)}</p><p>{html.escape(SPEND_NOTE)}</p></div>
<div id=boundary-note></div>
<div id=tier-block class=hidden>
<div class=honesty><p><b>Bank tier.</b> {html.escape(TIER_SERIES_NOTE)}</p><p>{html.escape(TIER_ROSTER_LINE_NOTE)}</p><p>{html.escape(TIER_FLOOR_NOTE)}</p><p>{html.escape(TIER_MIXED_NOTE)}</p></div>
<div class=tierchart><div class=tiercol><h4>Hired firms by tier</h4><span class=subtle>Fees paid to outside registrants · 2021–2026 (2026 partial)</span><div id=chart-hired></div></div><div class=tiercol><h4>In-house by tier</h4><span class=subtle>Self-reported in-house lobbying expenses · 2021–2026 (2026 partial)</span><div id=chart-inhouse></div></div></div>
<div class=tabletop><div><h4>Money and organization counts by tier</h4><p class=subtle>Evidence column reports the share of that tier-year's dollars that reached the tier by DEFAULT rather than by a positive identification.</p></div><p id=tier-count class=rowcount aria-live=polite></p></div>
<div class=tablewrap><table><thead><tr><th scope=col>Bank tier</th><th scope=col class=num>Organizations</th><th scope=col class=num>Hired firms</th><th scope=col>Fee evidence</th><th scope=col class=num>In-house</th><th scope=col>In-house evidence</th></tr></thead><tbody id=tier-body></tbody></table></div>
<p class=receipt id=tier-provenance></p></div>
<div class=tabletop><div><h4>Roster organizations</h4><p class=subtle id=roster-note></p></div><p id=roster-count class=rowcount aria-live=polite></p></div>
<div class=tablewrap><table><thead><tr><th scope=col>Organization</th><th scope=col id=roster-tier-head class=hidden>Bank tier</th><th scope=col>Years on the roster</th><th scope=col class=num>Client IDs</th><th scope=col>Identity basis</th></tr></thead><tbody id=roster-body></tbody></table></div>
<p class=receipt>{html.escape(TIER_ROSTER_LABEL_NOTE)}</p></div>
<div class=subsection id=champions><div class=panelhead><div><div class=eyebrow>Centerpiece</div><h3>The champions board</h3><div class=subtle>Raw shows whom an organization works hardest by champion_score; org-specific uses sector_relative_score, net of what other finance organizations in its champion comparison pool do.</div></div><div class=toggle aria-label="Champion score mode"><button type=button data-mode=raw class=active aria-pressed=true>Raw</button><button type=button data-mode=sector aria-pressed=false>Org-specific</button></div></div>
<div class=honesty><p>{html.escape(CHAMPION_NOTE)}</p><p>{html.escape(WORKS_NOTE)}</p><p>{html.escape(FORMER_MEMBER_NOTE)}</p><p>Raw ranks use champion_score; org-specific ranks use sector_relative_score, net of the comparison sector. A missing sector comparison is shown as “—”, never zero. Raw bill counts, years present, and direction of travel remain visible in both modes.</p></div>
<div class=tabletop><span class=subtle>Top three members per organization in the selected mode</span><p id=champion-count class=rowcount aria-live=polite></p></div><div class=tablewrap><table><thead><tr><th scope=col>Organization</th><th scope=col>Top member</th><th scope=col>Posture</th><th scope=col class=num id=score-heading>Champion score</th><th scope=col class=num>Raw n_bills</th><th scope=col class=num>Years present</th><th scope=col>Direction</th><th scope=col>Filings</th></tr></thead><tbody id=champion-body></tbody></table></div></div></section>
<section class="panel hidden" id=organization-panel aria-labelledby=organization-title><div class=panelhead><div><div class=eyebrow>Level 3 · organization</div><h2 id=organization-title></h2></div><button type=button id=close-org class=clearbutton>← Back to industry</button></div><div id=organization-meta class=orgmeta></div><p id=organization-receipt class=receipt></p><div class=honesty><p>{html.escape(CHAMPION_NOTE)}</p><p>{html.escape(WORKS_NOTE)}</p></div><div class=tabletop><span class=subtle>Retained champion leaders</span><p id=organization-count class=rowcount aria-live=polite></p></div><div class=tablewrap><table><thead><tr><th scope=col class=num>Raw rank</th><th scope=col>Member</th><th scope=col>Posture</th><th scope=col>Party / chamber</th><th scope=col class=num>Champion score</th><th scope=col class=num>Org-specific score</th><th scope=col class=num>Raw n_bills</th><th scope=col class=num>Years present</th><th scope=col>Direction</th><th scope=col>Filings</th></tr></thead><tbody id=organization-body></tbody></table></div></section>
<section class=panel id=bills aria-labelledby=bills-title><div class=panelhead><div><div class=eyebrow>Headline view · bill centric</div><h2 id=bills-title>Who lobbied each bill—and how CU marked it</h2><div class=subtle>All lobbying-index bills, with adjudicated CU direction overlaid where available</div></div></div>
<div class=honesty><p>An organization–bill row means the organization’s filing named that bill. It is not evidence that the organization supported or opposed it.</p><p>The curated 19-category repository is not a gate: its join yields only {repository_receipt['matched']:,} matched bills, and {repository_receipt['repository_only_amendments']:,} of its {repository_receipt['repository_only']:,} unmatched repository entries are amendments (H.Amdt./S.Amdt.) that lobbying filings essentially never cite.</p><p>The <code>bill_directions.csv</code> marking layer is broader than the 19-category repository: it independently overlays {bill_receipt['marked']:,} lobbied bills. Both layers are shown for what they are; neither limits this bill-centric view.</p></div>
<div class=legend-row aria-label="CU marking legend"><span class="chip support"><span class=chip-shape aria-hidden=true>▲</span>Support · category</span><span class="chip oppose"><span class=chip-shape aria-hidden=true>▼</span>Oppose · category</span><span class="chip neutral"><span class=chip-shape aria-hidden=true>◆</span>Neutral · category</span><span class=legend-unmarked><b aria-hidden=true>—</b> Unmarked</span></div>
<div class=bill-summary><div><strong>{bill_receipt['marked']:,} of {bill_receipt['bills']:,} bills carry a CU marking ({bill_receipt['directional']:,} directional, {bill_receipt['neutral']:,} neutral)</strong><span>Neutral means adjudicated neutral; an em dash means no adjudication row.</span></div><div id=bill-shown class=num aria-live=polite>{bill_receipt['bills']:,} bills shown</div></div>
<div class=filters aria-label="Bill filters"><div class="field searchfield"><label for=bill-search>Bill number or title</label><input id=bill-search type=search placeholder="Try H.R.1181 or a title" autocomplete=off></div><div class=field><label for=congress-filter>Congress</label><select id=congress-filter><option value="">All congresses</option></select></div><div class=field><label for=sector-filter>Sector</label><select id=sector-filter><option value="">All sectors</option></select></div><div class=field><label for=marking-filter>CU marking</label><select id=marking-filter><option value="">All states</option><option value=marked>Has a CU marking</option><option value=directional>Directional only</option><option value=support>Support</option><option value=oppose>Oppose</option><option value=neutral>Neutral</option><option value=unmarked>Unmarked</option></select></div><button type=button id=clear-bill-filters class=clearbutton>Clear filters</button></div>
<div class=tabletop><span class=subtle>Select a bill to disclose every organization link.</span><p id=bill-count class=rowcount aria-live=polite>{bill_receipt['bills']:,} bill rows</p></div><div class="tablewrap billtable"><table id=bill-table><thead><tr><th scope=col data-sort=bill aria-sort=none><button class=sortbutton type=button data-sort=bill>Bill<span class=sort-indicator aria-hidden=true>↕</span></button></th><th scope=col data-sort=title aria-sort=none><button class=sortbutton type=button data-sort=title>Title<span class=sort-indicator aria-hidden=true>↕</span></button></th><th scope=col class=num data-sort=congress aria-sort=none><button class=sortbutton type=button data-sort=congress>Congress<span class=sort-indicator aria-hidden=true>↕</span></button></th><th scope=col class=num data-sort=organizations aria-sort=descending><button class=sortbutton type=button data-sort=organizations>Organizations<span class=sort-indicator aria-hidden=true>↓</span></button></th><th scope=col data-sort=years aria-sort=none><button class=sortbutton type=button data-sort=years>Years active<span class=sort-indicator aria-hidden=true>↕</span></button></th><th scope=col data-sort=marking aria-sort=none><button class=sortbutton type=button data-sort=marking>CU marking<span class=sort-indicator aria-hidden=true>↕</span></button></th></tr></thead><tbody id=bill-body></tbody></table></div>
<p class=receipt>Bill payload receipt: all {bill_receipt['links']:,} distinct bill–organization links across all {bill_receipt['bills']:,} manifest bills are rendered in full; {bill_receipt['truncated_links']:,} links truncated.</p></section>
<section class=panel id=forecast aria-labelledby=forecast-title><div class=panelhead><div><div class=eyebrow>Separate analysis</div><h2 id=forecast-title>Cosponsorship forecast</h2><div class=subtle>Defensible headline configuration · same-chamber restriction · train Congress {html.escape(str(forecast['train']))}, test Congress {html.escape(str(forecast['test']))}</div></div><div><span class=subtle>Base rate</span><div class=base>{forecast['base_rate']:.1%}</div></div></div><div class=honesty><p>{html.escape(FORECAST_NOTE)}</p></div><div class=tabletop><span class=subtle>Model and baseline comparison</span><p class=rowcount>4 predictor rows</p></div>{_metric_table(forecast)}<div class=verdict>{html.escape(forecast['verdict'])}</div><p class=receipt>{html.escape(forecast['comparison_rule'])}</p>
<div class=forecastgrid><div><h3>Likely cosponsors</h3><label for=bill-picker class=subtle>Bill</label><br><select id=bill-picker></select><p class=receipt>Ranked by predicted probability. Actual outcome is shown where known.</p></div><div><p class=receipt>To stay self-contained, this view retains the top {forecast_receipt['leader_limit']} predicted members per bill for {forecast_receipt['bills']:,} bills in the defensible configuration: {forecast_receipt['retained_rows']:,} of {forecast_receipt['configuration_rows']:,} score rows retained; {forecast_receipt['omitted_rows']:,} lower-ranked rows aggregated. {forecast_receipt['missing_member_names']:,} retained-universe member IDs lacked a name in the champion corpus and render as IDs.</p></div></div><div class=tabletop><span class=subtle>Selected bill ranking</span><p id=forecast-count class=rowcount aria-live=polite></p></div><div class=tablewrap><table><thead><tr><th scope=col class=num>Rank</th><th scope=col>Member</th><th scope=col class=num>Predicted probability</th><th scope=col>Actual cosponsor</th></tr></thead><tbody id=forecast-body></tbody></table></div></section>
<footer id=receipts><h3>Build receipts</h3><p>Bill payload: {bill_receipt['links']:,} of {bill_receipt['links']:,} distinct bill–organization links rendered across {bill_receipt['bills']:,} of {bill_receipt['manifest_bills']:,} manifest bills; nothing was truncated. The canonical marking overlay found {bill_receipt['marked']:,} marked lobbying bills ({bill_receipt['directional']:,} directional and {bill_receipt['neutral']:,} neutral); {bill_receipt['unmarked']:,} render as em dashes. {bill_receipt['marking_input']['unjoinable']:,} direction rows lacked canonical congress/bill parts and could not be overlaid.</p><p>Champion payload: {champion_receipt['retained_rows']:,} of {champion_receipt['sector_eligible_rows']:,} sector-eligible CSV rows retained from the union of each organization’s top {champion_receipt['leader_limit']} raw and top {champion_receipt['leader_limit']} org-specific ranks; {champion_receipt['long_tail_rows']:,} lower-ranked rows aggregated with per-organization omitted counts and raw bill-attention totals. Another {champion_receipt['unmatched_sector_rows']:,} of the {champion_receipt['input_rows']:,} input rows belong to sector-unmatched organizations and follow the sector exclusion receipt.</p><p>Sector join: {sector_receipt['matched_active_orgs']:,} active full-scope organizations matched the sector roster; {sector_receipt['unmatched_active_orgs']:,} active organizations had no unambiguous sector-roster ID/name alias and are excluded from sector drill-downs, not silently relabeled. Ambiguous aliases removed: {sector_receipt['ambiguous_ids']:,} IDs and {sector_receipt['ambiguous_names']:,} names.</p><p>Network receipt: {payload['receipts']['network_rows']:,} strict annual organization-member rows read across 2021–2026 (2026 partial year). Forecast score receipt: {forecast_receipt['input_rows']:,} total rows read fresh, including contextual configurations.</p><h3>Input SHA-256</h3><ul class=hashes>{hashes_markup}</ul></footer>
<script id=page-data type=application/json>{data_json}</script>
"""
    script = r"""
<script>
"use strict";
const DATA=JSON.parse(document.getElementById("page-data").textContent);
const EM_DASH="—";
let currentSector=DATA.industries[0]?.sector||"";
let championMode="raw";
let openBillKey=null;
let billSort={key:"organizations",direction:"desc"};
const esc=value=>String(value??"").replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch]));
const number=value=>Number(value).toLocaleString("en-US");
// A member's profile lives in the member desk, addressed by name through ?m=<name>. This is the
// only place that mints that address, so every member name on this page is a real anchor to the
// same profile the network dashboard links to.
const DESK_FILE="cu-member-desk.html";
// The interaction ledger is its own surface, addressed by sector + bioguide so a
// link survives a member being renamed or leaving office.
const INTERACTIONS_FILE="lobby-interactions.html";
// Paul's wording is the default; the toggle swaps the vocabulary over an
// IDENTICAL computation -- both labels are precomputed in Python, so switching
// modes can never change which bucket a pair is in.
let postureMode="posture";
// A posture arrives as [stateIndex, recent, prior, partial, delta]. The state
// decision was made in Python; this only re-renders the sentence describing it
// from the same numbers, so the page carries one copy of the words rather than
// one per row.
const P_STATE=0,P_RECENT=1,P_PRIOR=2,P_PARTIAL=3,P_DELTA=4;
const plural=(count,word)=>`${count} ${word}${count===1?"":"s"}`;
function postureDetail(verdict){
  const state=DATA.postureStates[verdict[P_STATE]];
  return `2024–2025: ${plural(verdict[P_RECENT],"bill")} vs 2022–2023: ${plural(verdict[P_PRIOR],"bill")} (${verdict[P_DELTA]}); 2026 partial year: ${verdict[P_PARTIAL]}. ${state.m}`;
}
function postureBadge(verdict){
  if(!verdict)return EM_DASH;
  const state=DATA.postureStates[verdict[P_STATE]];
  const label=postureMode==="posture"?state.p:state.t;
  return `<span class="postbadge ${esc(state.b)}" title="${esc(postureDetail(verdict))}"><span class=pdot aria-hidden=true></span>${esc(label)}</span><span class=postdelta>${esc(verdict[P_DELTA])}</span>`;
}
function interactionLink(bioguide,label){
  if(!bioguide)return EM_DASH;
  const url=`${INTERACTIONS_FILE}?sector=${encodeURIComponent(currentSector)}&b=${encodeURIComponent(bioguide)}`;
  return `<a class=memberlink href="${url}" title="Every disclosed filing behind this count">${esc(label||"Open filings")}</a>`;
}
const memberLink=(name,bioguide,flag)=>{const text=esc(name??"");if(!text)return EM_DASH;
  // a former member, or one no roster names, has no current member-desk profile: the name is
  // badged and stays plain text rather than becoming a link that lands nowhere.
  if(flag)return text+memberFlag(flag);
  // an unresolved retained-universe row renders the bioguide ID as its name; the desk cannot
  // address that, so it stays plain text rather than becoming a link that lands nowhere.
  if(bioguide!=null&&String(name)===String(bioguide))return text;
  return `<a class=memberlink href="${DESK_FILE}?m=${encodeURIComponent(name)}" title="Open ${text} in the member desk">${text}</a>`;};
const score=value=>value===null||value===undefined?EM_DASH:Number(value).toFixed(3);
const displaySector=value=>String(value||"unclassified").replaceAll("_"," ").replaceAll(" | "," / ").split(" ").map(word=>word?word[0].toUpperCase()+word.slice(1):word).join(" ");
const yearText=values=>values.map(value=>value===2026?"2026 (partial year)":value).join(", ");
function lineSpark(values){
  const maximum=Math.max(1,...values),coordinates=values.map((value,index)=>[4+index*20,32-24*value/maximum]),points=coordinates.map(point=>point.join(","));
  const label=values.map((value,index)=>`${2021+index}${index===5?" partial year":""}: ${number(value)}`).join("; ");
  const area=`M4 32 L${coordinates.slice(0,5).map(point=>point.join(" ")).join(" L")} L84 32 Z`,partialArea=`M84 32 L84 ${coordinates[4][1]} L104 ${coordinates[5][1]} L104 32 Z`;
  return `<span class=attention-spark-wrap><svg class=attention-spark viewBox="0 0 108 36" width=108 height=36 role=img aria-label="${esc(label)}"><path class=sparkarea d="${area}"></path><path class="sparkarea partial-area" d="${partialArea}"></path><polyline class=sparkline points="${points.slice(0,5).join(" ")}"></polyline><line class=partial-segment x1=84 y1="${coordinates[4][1]}" x2=104 y2="${coordinates[5][1]}"></line><circle class=last-dot cx=104 cy="${coordinates[5][1]}" r=3></circle></svg><strong>${number(values[5])}</strong></span>`;
}
function industry(){return DATA.industries.find(item=>item.sector===currentSector);}
const MEMBER_FLAG_LABELS={former:"Former",unresolved:"Name unresolved"};
function memberFlag(flag){
  if(!flag)return "";
  const label=MEMBER_FLAG_LABELS[flag]||flag;
  const title=flag==="former"?"No longer serving in Congress":"No roster or Voteview record names this bioguide";
  return `<span class="memberflag ${esc(flag)}" title="${esc(title)}">${esc(label)}</span>`;
}
function setRowCount(id,count,label){document.getElementById(id).textContent=`${number(count)} ${label}`;}
function renderAttention(){
  const item=industry();
  document.getElementById("industry-title").textContent=displaySector(item.sector);
  document.querySelectorAll(".industry-card").forEach(card=>{const active=card.dataset.sector===item.sector;card.classList.toggle("active",active);card.setAttribute("aria-pressed",active?"true":"false");});
  document.getElementById("attention-body").innerHTML=item.members.length?item.members.map((row,index)=>`<tr><td class="rank num">${index+1}</td><td class="member left">${memberLink(row.name,row.id,row.flag)} <span class=subtle>${esc(row.id)}</span></td><td>${postureBadge(row.posture)}</td><td class=num>${number(row.total)}</td><td class="num ${row.change>0?"pos":row.change<0?"neg":"zero"}">${row.change>0?"+":""}${number(row.change)}</td><td>${lineSpark(row.values)}</td><td>${interactionLink(row.id)}</td></tr>`).join(""):`<tr><td colspan=7><div class=empty>No sector-matched network attention rows.</div></td></tr>`;
  setRowCount("attention-count",item.members.length,item.members.length===1?"member row":"member rows");
}
function sortedChampions(org){
  return [...org.rows].sort((a,b)=>{if(championMode==="sector"){if(a.s===null&&b.s!==null)return 1;if(a.s!==null&&b.s===null)return -1;if(a.s!==null&&b.s!==null&&b.s!==a.s)return b.s-a.s;}else if(b.c!==a.c)return b.c-a.c;return a.n.localeCompare(b.n)||a.i.localeCompare(b.i);});
}
function renderBoard(){
  const item=industry(),rows=[];
  document.getElementById("score-heading").textContent=championMode==="raw"?"Champion score":"Org-specific score";
  item.organizations.forEach(org=>{const leaders=sortedChampions(org).slice(0,3);if(!leaders.length){rows.push(`<tr><td><button type=button class=orgbutton data-org="${esc(org.id)}" aria-expanded=false>${esc(org.name)}</button>${tierBadge(org.tier)}</td><td colspan=7 class=null>${esc(org.skipped||"No scored champion model")}</td></tr>`);return;}leaders.forEach((row,index)=>rows.push(`<tr><td>${index===0?`<button type=button class=orgbutton data-org="${esc(org.id)}" aria-expanded=false>${esc(org.name)}</button>${tierBadge(org.tier)}`:""}</td><td class="member left">${memberLink(row.n,row.i,row.f)} <span class=subtle>${esc(row.p)} · ${esc(row.h)}</span></td><td>${postureBadge(row.g)}</td><td class="num ${championMode==="sector"&&row.s===null?"null":""}">${score(championMode==="raw"?row.c:row.s)}</td><td class=num>${number(row.b)}</td><td class=num>${number(row.y)}</td><td>${esc(row.d)}</td><td>${interactionLink(row.i)}</td></tr>`));});
  document.getElementById("champion-body").innerHTML=rows.join("")||`<tr><td colspan=8><div class=empty>No sector-matched organizations.</div></td></tr>`;
  setRowCount("champion-count",rows.length,rows.length===1?"leader row":"leader rows");
}
function openOrganization(orgId,scroll=true){
  const org=industry().organizations.find(item=>item.id===orgId);if(!org)return;
  document.querySelectorAll("[data-org]").forEach(button=>button.setAttribute("aria-expanded",button.dataset.org===orgId?"true":"false"));
  document.getElementById("organization-title").textContent=org.name;
  document.getElementById("organization-meta").innerHTML=(org.tier&&org.tier.length?`<div class=metabox><span class=subtle>Bank tier</span><b>${tierBadge(org.tier)}</b></div>`:"")+`<div class=metabox><span class=subtle>Covered years</span><b>${esc(yearText(org.years))}</b></div><div class=metabox><span class=subtle>R²</span><b>${score(org.r2)}</b></div><div class=metabox><span class=subtle>Controls used</span><b>${esc(org.controls||EM_DASH)}</b></div><div class=metabox><span class=subtle>Members modeled</span><b>${org.modeled===null?EM_DASH:number(org.modeled)}</b></div>`;
  document.getElementById("organization-receipt").textContent=`Size receipt: ${number(org.rows.length)} leaders retained from ${number(org.total)} scored members; ${number(org.omitted)} lower-ranked members aggregated, representing ${number(org.omitted_bills)} raw bill-attention counts. Retention is the union of the top ${DATA.receipts.champions.leader_limit} raw and org-specific ranks.`;
  const rows=[...org.rows].sort((a,b)=>a.r-b.r||a.i.localeCompare(b.i));
  document.getElementById("organization-body").innerHTML=rows.length?rows.map(row=>`<tr><td class=num>${row.r}</td><td class="member left">${memberLink(row.n,row.i,row.f)} <span class=subtle>${esc(row.i)}</span></td><td>${postureBadge(row.g)}</td><td>${esc(row.p)} / ${esc(row.h)}</td><td class=num>${score(row.c)}</td><td class="num ${row.s===null?"null":""}">${score(row.s)}</td><td class=num>${number(row.b)}</td><td class=num>${number(row.y)}</td><td>${esc(row.d)}</td><td>${interactionLink(row.i,"Open filings")}</td></tr>`).join(""):`<tr><td colspan=10><div class=empty>${esc(org.skipped||"No scored champion model")}</div></td></tr>`;
  setRowCount("organization-count",rows.length,rows.length===1?"leader row":"leader rows");
  const panel=document.getElementById("organization-panel");panel.classList.remove("hidden");if(scroll)panel.scrollIntoView({behavior:"smooth",block:"start"});
}
// ------------------------------------------------------------- bank tier
// Palette, evidence ladder and glyphs all arrive in the payload, so the fill a
// bar gets here is decided by the same table the Python builder drew the level-1
// card with. There is no second copy of the rule to drift.
const TIER_META=DATA.tierMeta||{enabled:false,order:[],labels:{},short:{},sectors:[],levels:[],colors:{},glyphs:{}};
const TIER_ORDER=TIER_META.order||[];
const ALL_YEARS="all";
let activeYear=DATA.years.includes(2025)?2025:DATA.years[DATA.years.length-1];
let tierFilter="";
let tierView="stacked";
const PARTIAL_YEAR=DATA.years[DATA.years.length-1];
function money(value){
  const absolute=Math.abs(value);let amount,suffix;
  if(absolute>=1e9){amount=value/1e9;suffix="B";}
  else if(absolute>=1e6){amount=value/1e6;suffix="M";}
  else if(absolute>=1e3){amount=value/1e3;suffix="k";}
  else return `$${number(Math.round(value))}`;
  let compact=amount.toFixed(1);
  if(compact.endsWith(".0"))compact=compact.slice(0,-2);
  return `$${compact}${suffix}`;
}
function evidenceLevel(share){
  for(const [ceiling,key,label] of TIER_META.levels){if(share<ceiling)return {level:key,label:label,share:share};}
  const last=TIER_META.levels[TIER_META.levels.length-1];
  return {level:last[1],label:last[2],share:share};
}
const tierFill=(name,level)=>level==="documented"?TIER_META.colors[name]:`url(#hx-${name}-${level==="part-inferred"?"light":"dense"})`;
function evidenceChip(evidence){
  const glyph=TIER_META.glyphs[evidence.level]||"";
  const pct=Math.round(100*evidence.share);
  return `<span class="evchip ${esc(evidence.level)}" title="${pct}% of these dollars reached the tier by DEFAULT rather than by a positive identification; the rest were positively identified"><span aria-hidden=true>${glyph}</span>${esc(evidence.label)} · ${pct}% default-classified</span>`;
}
function tierBadge(tiers){
  if(!tiers||!tiers.length)return "";
  if(tiers.length>1){
    // A family that sat in different tiers at different times is shown wearing
    // ALL of them rather than being collapsed to a guess.
    return `<span class="tierbadge multi" title="Date-gated: this family held more than one tier inside the window, so no single tier is asserted">${tiers.map(t=>esc(TIER_META.short[t]||t)).join(" / ")}</span>`;
  }
  const name=tiers[0];
  return `<span class="tierbadge t-${esc(name)}"><span class=tdot aria-hidden=true></span>${esc(TIER_META.short[name]||name)}</span>`;
}
function yearRows(item){
  const rows=item.spend||[];
  return activeYear===ALL_YEARS?rows:rows.filter(row=>row.year===activeYear);
}
// Money sums across the window; ORGANIZATION COUNTS DO NOT. A distinct-org count
// is per year, so adding six of them would count the same bank six times.
function tierTotals(item){
  const rows=yearRows(item),out={};
  TIER_ORDER.forEach(name=>{
    let hired=0,inHouse=0,hiredDefault=0,inHouseDefault=0,orgs=null;
    rows.forEach(row=>{
      const tier=row.tiers&&row.tiers[name];if(!tier)return;
      hired+=tier.hired_firms;inHouse+=tier.in_house;
      hiredDefault+=tier.evidence.hired_firms.share*tier.evidence.hired_firms.total;
      inHouseDefault+=tier.evidence.in_house.share*tier.evidence.in_house.total;
      orgs=rows.length===1?tier.orgs:null;
    });
    out[name]={hired:hired,in_house:inHouse,orgs:orgs,
      evidence:{hired_firms:evidenceLevel(hired?hiredDefault/hired:0),
                in_house:evidenceLevel(inHouse?inHouseDefault/inHouse:0)}};
  });
  return out;
}
function tierChart(item,field,titleText){
  const rows=item.spend||[],order=TIER_ORDER;
  const W=560,H=200,padL=56,padR=8,padT=12,padB=30;
  const plotW=W-padL-padR,plotH=H-padT-padB;
  let maximum=0;
  rows.forEach(row=>{
    if(tierView==="stacked"){let sum=0;order.forEach(name=>sum+=row.tiers[name][field]);maximum=Math.max(maximum,sum);}
    else order.forEach(name=>maximum=Math.max(maximum,row.tiers[name][field]));
  });
  maximum=maximum||1;
  const y=value=>padT+plotH-plotH*value/maximum;
  const grid=[0,.25,.5,.75,1].map(fraction=>{
    const yy=y(maximum*fraction);
    return `<line x1=${padL} y1="${yy.toFixed(1)}" x2=${W-padR} y2="${yy.toFixed(1)}" stroke="#21262d" stroke-width=1></line>`+
      `<text x="${padL-8}" y="${(yy+4).toFixed(1)}" text-anchor=end fill="#6e7681" font-size=10>${esc(money(maximum*fraction))}</text>`;
  }).join("");
  const columnWidth=plotW/rows.length;
  const bars=rows.map((row,index)=>{
    const left=padL+index*columnWidth;
    const partial=row.year===PARTIAL_YEAR;
    let shapes="";
    if(tierView==="stacked"){
      const barWidth=Math.min(46,columnWidth*.56),x=left+(columnWidth-barWidth)/2;
      let baseline=padT+plotH;
      order.forEach(name=>{
        const tier=row.tiers[name],value=tier[field];if(value<=0)return;
        const height=plotH*value/maximum;baseline-=height;
        const dim=tierFilter&&tierFilter!==name?' opacity=".26"':"";
        shapes+=`<rect x="${x.toFixed(1)}" y="${baseline.toFixed(2)}" width="${barWidth.toFixed(1)}" height="${height.toFixed(2)}" fill="${tierFill(name,tier.evidence[field].level)}" stroke="#161b22" stroke-width=".5"${dim}><title>${esc(row.year)}${partial?" (partial year)":""} · ${esc(TIER_META.labels[name])} · ${esc(money(value))} · ${esc(tier.evidence[field].label)} (${Math.round(100*tier.evidence[field].share)}% default-classified)</title></rect>`;
      });
    }else{
      const slot=columnWidth*.86/order.length,barWidth=Math.min(18,slot*.82),start=left+columnWidth*.07;
      order.forEach((name,slotIndex)=>{
        const tier=row.tiers[name],value=tier[field];if(value<=0)return;
        const height=plotH*value/maximum,x=start+slotIndex*slot+(slot-barWidth)/2;
        const dim=tierFilter&&tierFilter!==name?' opacity=".26"':"";
        shapes+=`<rect x="${x.toFixed(1)}" y="${(padT+plotH-height).toFixed(2)}" width="${barWidth.toFixed(1)}" height="${height.toFixed(2)}" fill="${tierFill(name,tier.evidence[field].level)}" stroke="#161b22" stroke-width=".5"${dim}><title>${esc(row.year)}${partial?" (partial year)":""} · ${esc(TIER_META.labels[name])} · ${esc(money(value))} · ${esc(tier.evidence[field].label)} (${Math.round(100*tier.evidence[field].share)}% default-classified)</title></rect>`;
      });
    }
    const selected=activeYear!==ALL_YEARS&&row.year===activeYear;
    const marker=selected?`<rect x="${left.toFixed(1)}" y="${padT}" width="${columnWidth.toFixed(1)}" height="${plotH}" fill="rgba(88,166,255,.08)" stroke="rgba(88,166,255,.45)" stroke-width=1></rect>`:"";
    const label=`<text x="${(left+columnWidth/2).toFixed(1)}" y="${H-10}" text-anchor=middle fill="${selected?"#e6edf3":"#8b949e"}" font-size=10${partial?' font-style=italic':""}>${row.year}${partial?"*":""}</text>`;
    return marker+shapes+label;
  }).join("");
  const readout=rows.map(row=>`${row.year}${row.year===PARTIAL_YEAR?" partial":""}: `+order.map(name=>`${TIER_META.short[name]} ${money(row.tiers[name][field])}`).join(", ")).join("; ");
  return `<svg viewBox="0 0 ${W} ${H}" role=img aria-label="${esc(titleText)}. ${tierView==="stacked"?"Stacked":"Side by side"} by bank tier; every tier including mixed is shown. Solid fill is documented, diagonal hatch means default-classified. ${esc(readout)}"><title>${esc(titleText)} — ${esc(readout)}</title>${grid}${bars}</svg>`;
}
function sectorBoundaries(sector){return (DATA.boundaries||[]).filter(item=>item.s===sector);}
function boundaryBanner(item){
  const linked=sectorBoundaries(item.sector);
  const spans=activeYear===ALL_YEARS
    ?linked
    :linked.filter(boundary=>boundary.y===activeYear);
  if(!linked.length)return "";
  const lines=[];
  if(activeYear===ALL_YEARS&&linked.length){
    lines.push(`<p><b>This range spans ${plural(linked.length,"merger boundary").replace("boundarys","boundaries")}.</b> ${esc(DATA.boundaryRule)}</p>`);
  }else if(spans.length){
    lines.push(`<p><b>${activeYear} is a merger boundary year.</b> ${esc(DATA.boundaryRule)}</p>`);
  }
  linked.forEach(boundary=>{
    const after=activeYear===ALL_YEARS||activeYear>=boundary.y;
    const state=activeYear===ALL_YEARS
      ?`spans this boundary`
      :(after?`as of ${activeYear} this is the successor`:`as of ${activeYear} the predecessors still filed separately`);
    lines.push(`<p>${esc(boundary.before.join(" + "))} → <b>${esc(boundary.after)}</b>, effective ${esc(boundary.d)} — ${esc(state)}.</p>`);
  });
  return lines.length?`<div class=boundary>${lines.join("")}</div>`:"";
}
function mergeBadge(item,family){
  const badges=sectorBoundaries(item.sector).map(boundary=>{
    if(boundary.after===family)return `<span class=mergebadge title="${esc(boundary.e)}">Formed ${esc(boundary.d)} from ${esc(boundary.before.join(" + "))}</span>`;
    if(boundary.before.includes(family))return `<span class=mergebadge title="${esc(boundary.e)}">Merged into ${esc(boundary.after)} ${esc(boundary.d)}</span>`;
    return "";
  }).filter(Boolean);
  return badges.join("");
}
function renderTierRoster(){
  const item=industry(),order=TIER_ORDER;
  const hasTier=!!TIER_META.enabled&&(TIER_META.sectors||[]).includes(item.sector);
  const asOf=activeYear===ALL_YEARS?`All years ${DATA.years[0]}–${PARTIAL_YEAR}`:`As of ${activeYear}`;
  document.getElementById("asof-chip").textContent=asOf+(activeYear===PARTIAL_YEAR?" · partial year through Q2":"");
  document.getElementById("roster-title").textContent=hasTier?`${displaySector(item.sector)} organizations and bank tier`:`${displaySector(item.sector)} organizations`;
  document.getElementById("roster-sub").textContent=`Pinned roster resolved as of the selected filing year · ${DATA.years[0]}–${PARTIAL_YEAR}`;
  document.getElementById("tier-filter-field").classList.toggle("hidden",!hasTier);
  document.getElementById("tier-view-field").classList.toggle("hidden",!hasTier);
  document.getElementById("tier-block").classList.toggle("hidden",!hasTier);
  document.getElementById("roster-tier-head").classList.toggle("hidden",!hasTier);
  document.getElementById("boundary-note").innerHTML=boundaryBanner(item);

  if(hasTier){
    document.getElementById("chart-hired").innerHTML=tierChart(item,"hired_firms","Hired firms by bank tier");
    document.getElementById("chart-inhouse").innerHTML=tierChart(item,"in_house","In-house by bank tier");
    const totals=tierTotals(item);
    document.getElementById("tier-body").innerHTML=order.map(name=>{
      const row=totals[name];
      const orgCell=row.orgs===null
        ?`<td class=num title="Distinct-organization counts are per year and are never summed across a window">${EM_DASH}</td>`
        :`<td class=num>${number(row.orgs)}</td>`;
      const gloss=TIER_META.labels[name]===TIER_META.short[name]?"":` <span class=subtle>${esc(TIER_META.labels[name])}</span>`;
      return `<tr><td>${tierBadge([name])}${gloss}</td>${orgCell}<td class=num>${esc(money(row.hired))}</td><td>${row.hired?evidenceChip(row.evidence.hired_firms):EM_DASH}</td><td class=num>${esc(money(row.in_house))}</td><td>${row.in_house?evidenceChip(row.evidence.in_house):EM_DASH}</td></tr>`;
    }).join("");
    setRowCount("tier-count",order.length,"tier rows");
    const provenance=TIER_META.provenance||{sources:[],date_gated:[]};
    document.getElementById("tier-provenance").textContent=
      `Big roster provenance: ${number(provenance.parents)} distinct parent institutions from `+
      provenance.sources.map(source=>`${source.l} (${source.n})`).join("; ")+
      `. ${provenance.date_gated.length} are date-gated because they ceased to exist inside the window: ${provenance.date_gated.join(", ")}.`;
  }

  let families=item.roster||[];
  if(activeYear!==ALL_YEARS)families=families.filter(row=>row.y0<=activeYear&&activeYear<=row.y1);
  if(tierFilter)families=families.filter(row=>(row.t||[]).includes(tierFilter));
  document.getElementById("roster-body").innerHTML=families.length?families.map(row=>{
    const window=row.y0===row.y1?`${row.y0}`:`${row.y0}–${row.y1}`;
    const tierCell=hasTier?`<td>${tierBadge(row.t)}${row.d?` <span class=subtle title="This family reached its tier by DEFAULT rather than by a positive identification">defaulted</span>`:""}</td>`:"";
    return `<tr><td class="member left">${esc(row.f)}${mergeBadge(item,row.f)}</td>${tierCell}<td>${esc(window)}</td><td class=num>${number(row.n)}</td><td>${esc(row.c||EM_DASH)}</td></tr>`;
  }).join(""):`<tr><td colspan=${hasTier?5:4}><div class=empty><b>No roster organizations match this combination.</b><br>${activeYear===ALL_YEARS?"":`No entity in this sector was on the roster in ${activeYear} under the selected tier.`}</div></td></tr>`;
  setRowCount("roster-count",families.length,families.length===1?"organization":"organizations");
  const unlinked=(DATA.boundaries||[]).filter(boundary=>!boundary.s).length;
  document.getElementById("roster-note").textContent=
    `Entity identity is resolved as of the filing year, so a predecessor and its successor are separate rows with separate windows.`+
    (unlinked?` ${unlinked} declared merger boundary${unlinked===1?"":"ies"} could not be tied to specific roster families by year window and therefore carries no row badge.`:"");
}
function setupTierControls(){
  const yearSelect=document.getElementById("year-filter");
  yearSelect.innerHTML=DATA.years.map(year=>`<option value="${year}"${year===activeYear?" selected":""}>${year}${year===PARTIAL_YEAR?" (partial)":""}</option>`).join("")+
    `<option value="${ALL_YEARS}">All years ${DATA.years[0]}–${PARTIAL_YEAR}</option>`;
  yearSelect.addEventListener("change",()=>{
    activeYear=yearSelect.value===ALL_YEARS?ALL_YEARS:Number(yearSelect.value);
    renderTierRoster();
  });
  const tierSelect=document.getElementById("tier-filter");
  tierSelect.insertAdjacentHTML("beforeend",TIER_ORDER.map(name=>`<option value="${esc(name)}">${esc(TIER_META.labels[name])}</option>`).join(""));
  tierSelect.addEventListener("change",()=>{tierFilter=tierSelect.value;renderTierRoster();});
  document.querySelectorAll("[data-tier-view]").forEach(button=>button.addEventListener("click",()=>{
    tierView=button.dataset.tierView;
    document.querySelectorAll("[data-tier-view]").forEach(item=>{item.classList.toggle("active",item===button);item.setAttribute("aria-pressed",item===button?"true":"false");});
    renderTierRoster();
  }));
}
function markingChip(marking){
  if(!marking)return `<span class=unmarked aria-label="Unmarked">${EM_DASH}</span>`;
  const meta={support:["▲","Support"],oppose:["▼","Oppose"],neutral:["◆","Neutral"]}[marking.state];
  const category=marking.category?` · ${esc(marking.category)}`:"";
  return `<span class="chip ${marking.state}" aria-label="${meta[1]}${marking.category?`, ${esc(marking.category)}`:""}"><span class=chip-shape aria-hidden=true>${meta[0]}</span>${meta[1]}${category}</span>`;
}
const CHANNEL_LABELS={formal_strict:"Formal citation · strict",both_strict:"Formal citation + title match · strict",title_strict:"Title match · strict",title_generous_only:"Title match · generous"};
function billDetail(bill){
  const id=`bill-detail-${bill.key.replaceAll(":","-")}`;
  const rows=bill.organizations.map(org=>`<tr><td class="member left">${esc(org.name)}</td><td>${esc(displaySector(org.sector))}</td><td class=num>${number(org.n_filings)}</td><td>${esc(yearText(org.years))}</td><td>${org.channels.map(channel=>`<span class=channel>${esc(CHANNEL_LABELS[channel]||channel)}</span>`).join("")}</td></tr>`).join("");
  return `<tr class=detail-row><td colspan=6><div class=bill-detail id="${id}"><div class=detail-head><div><div class=detail-title>${esc(bill.bill)} · ${esc(bill.title||"Title unavailable")}</div><div class=subtle>${number(bill.organizations.length)} organizations · ${esc(yearText(bill.years))} · extraction channels shown per organization</div></div>${markingChip(bill.marking)}</div><div class=tabletop><span class=subtle>Complete organization list</span><p class=rowcount>${number(bill.organizations.length)} organization rows</p></div><div class="tablewrap subtable"><table><thead><tr><th scope=col>Organization</th><th scope=col>Sector</th><th scope=col class=num>Filings</th><th scope=col>Years</th><th scope=col>Extraction channel</th></tr></thead><tbody>${rows||`<tr><td colspan=5><div class=empty>No organization links for this bill.</div></td></tr>`}</tbody></table></div></div></td></tr>`;
}
function billSortValue(bill,key){if(key==="organizations")return bill.organizations.length;if(key==="years")return Math.max(...bill.years);if(key==="marking")return bill.marking?({support:3,neutral:2,oppose:1}[bill.marking.state]||0):0;if(key==="bill")return `${bill.bill_type}:${String(bill.bill_number).padStart(8,"0")}`;return bill[key]||"";}
function visibleBills(){
  const query=document.getElementById("bill-search").value.trim().toLocaleLowerCase(),congress=document.getElementById("congress-filter").value,sector=document.getElementById("sector-filter").value,marking=document.getElementById("marking-filter").value;
  const rows=DATA.bills.filter(bill=>{if(congress&&String(bill.congress)!==congress)return false;if(sector&&!bill.sectors.includes(sector))return false;if(query&&!`${bill.bill} ${bill.title} ${bill.key}`.toLocaleLowerCase().includes(query))return false;if(!marking)return true;if(marking==="marked")return !!bill.marking;if(marking==="directional")return !!bill.marking&&bill.marking.direction!==0;if(marking==="unmarked")return !bill.marking;return !!bill.marking&&bill.marking.state===marking;});
  const multiplier=billSort.direction==="asc"?1:-1;
  rows.sort((a,b)=>{const av=billSortValue(a,billSort.key),bv=billSortValue(b,billSort.key);let comparison=typeof av==="number"&&typeof bv==="number"?av-bv:String(av).localeCompare(String(bv));return multiplier*comparison||a.key.localeCompare(b.key);});
  return rows;
}
function renderBills(){
  const bills=visibleBills();
  document.getElementById("bill-shown").textContent=`${number(bills.length)} bills shown`;
  setRowCount("bill-count",bills.length,bills.length===1?"bill row":"bill rows");
  document.getElementById("bill-body").innerHTML=bills.length?bills.map(bill=>{const expanded=openBillKey===bill.key,id=`bill-detail-${bill.key.replaceAll(":","-")}`;const row=`<tr><td><button type=button class=billbutton data-bill="${esc(bill.key)}" aria-expanded="${expanded}" aria-controls="${id}">${esc(bill.bill)}</button></td><td class="left titlecell" title="${esc(bill.title||"Title unavailable")}">${esc(bill.title||EM_DASH)}</td><td class=num>${number(bill.congress)}</td><td class=num>${number(bill.organizations.length)}</td><td>${esc(yearText(bill.years))}</td><td>${markingChip(bill.marking)}</td></tr>`;return row+(expanded?billDetail(bill):"");}).join(""):`<tr><td colspan=6><div class=empty><b>No bills match this filter combination.</b><br>Clear one or more filters to return to the full lobbying-index universe.</div></td></tr>`;
}
function updateBillSortHeaders(){document.querySelectorAll("#bill-table thead th[data-sort]").forEach(th=>{const active=th.dataset.sort===billSort.key,direction=active?billSort.direction:"none";th.setAttribute("aria-sort",direction==="asc"?"ascending":direction==="desc"?"descending":"none");th.querySelector(".sort-indicator").textContent=active?(direction==="asc"?"↑":"↓"):"↕";});}
function setupBillControls(){
  const congresses=[...new Set(DATA.bills.map(bill=>bill.congress))].sort((a,b)=>b-a),sectors=DATA.bill_sectors;
  document.getElementById("congress-filter").insertAdjacentHTML("beforeend",congresses.map(value=>`<option value="${value}">${value}th Congress</option>`).join(""));
  document.getElementById("sector-filter").insertAdjacentHTML("beforeend",sectors.map(value=>`<option value="${esc(value)}">${esc(displaySector(value))}</option>`).join(""));
  document.getElementById("bill-search").addEventListener("input",renderBills);
  ["congress-filter","sector-filter","marking-filter"].forEach(id=>document.getElementById(id).addEventListener("change",renderBills));
  document.getElementById("clear-bill-filters").addEventListener("click",()=>{document.getElementById("bill-search").value="";["congress-filter","sector-filter","marking-filter"].forEach(id=>document.getElementById(id).value="");openBillKey=null;renderBills();document.getElementById("bill-search").focus();});
  document.querySelectorAll("#bill-table .sortbutton").forEach(button=>button.addEventListener("click",()=>{const key=button.dataset.sort;if(billSort.key===key)billSort.direction=billSort.direction==="asc"?"desc":"asc";else{billSort.key=key;billSort.direction=["organizations","congress","years","marking"].includes(key)?"desc":"asc";}updateBillSortHeaders();renderBills();}));
  document.getElementById("bill-body").addEventListener("click",event=>{const button=event.target.closest("[data-bill]");if(!button)return;openBillKey=openBillKey===button.dataset.bill?null:button.dataset.bill;renderBills();if(openBillKey){const detail=document.getElementById(`bill-detail-${openBillKey.replaceAll(":","-")}`);detail?.scrollIntoView({behavior:"smooth",block:"nearest"});}});
  updateBillSortHeaders();renderBills();
}
function renderForecast(index){
  const bill=DATA.forecast.bills[index]||DATA.forecast.bills[0],body=document.getElementById("forecast-body");
  if(!bill){body.innerHTML=`<tr><td colspan=4><div class=empty>No forecast bills are available.</div></td></tr>`;setRowCount("forecast-count",0,"prediction rows");return;}
  body.innerHTML=bill.rows.length?bill.rows.map((row,rank)=>`<tr><td class="rank num">${rank+1}</td><td class="member left">${memberLink(row.name,row.member,row.flag)} <span class=subtle>${esc(row.member)}</span></td><td class=num>${(100*row.probability).toFixed(1)}%</td><td>${row.actual===null?EM_DASH:row.actual===1?"Yes":"No"}</td></tr>`).join(""):`<tr><td colspan=4><div class=empty>No predicted members for this bill.</div></td></tr>`;
  setRowCount("forecast-count",bill.rows.length,bill.rows.length===1?"prediction row":"prediction rows");
}
function setupSectionNav(){
  const links=[...document.querySelectorAll(".section-nav a")],byId=new Map(links.map(link=>[link.getAttribute("href").slice(1),link]));
  const activate=id=>links.forEach(link=>{const current=link===byId.get(id);link.classList.toggle("current",current);if(current)link.setAttribute("aria-current","location");else link.removeAttribute("aria-current");});
  links.forEach(link=>link.addEventListener("click",()=>activate(link.getAttribute("href").slice(1))));
  if("IntersectionObserver" in window){const observer=new IntersectionObserver(entries=>{const visible=entries.filter(entry=>entry.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];if(visible)activate(visible.target.id);},{rootMargin:"-20% 0px -65% 0px",threshold:[0,.15,.4]});["industries","champions","bills","forecast"].forEach(id=>{const section=document.getElementById(id);if(section)observer.observe(section);});}
  activate("industries");
}
document.querySelectorAll(".industry-card").forEach(card=>card.addEventListener("click",()=>{currentSector=card.dataset.sector;document.getElementById("organization-panel").classList.add("hidden");renderAttention();renderTierRoster();renderBoard();document.getElementById("industry-panel").scrollIntoView({behavior:"smooth",block:"start"});}));
document.querySelectorAll("[data-mode]").forEach(button=>button.addEventListener("click",()=>{championMode=button.dataset.mode;document.querySelectorAll("[data-mode]").forEach(item=>{item.classList.toggle("active",item===button);item.setAttribute("aria-pressed",item===button?"true":"false");});renderBoard();}));
// Wording only. The bucket, the colour and the tooltip all come from the same
// precomputed verdict, so no row can change meaning when the label changes.
document.querySelectorAll("[data-posture-mode]").forEach(button=>button.addEventListener("click",()=>{postureMode=button.dataset.postureMode;document.querySelectorAll("[data-posture-mode]").forEach(item=>{item.classList.toggle("active",item===button);item.setAttribute("aria-pressed",item===button?"true":"false");});renderAttention();renderBoard();if(!document.getElementById("organization-panel").classList.contains("hidden")){const open=document.querySelector("[data-org][aria-expanded=true]");if(open)openOrganization(open.dataset.org,false);}}));
document.getElementById("champion-body").addEventListener("click",event=>{const button=event.target.closest("[data-org]");if(button)openOrganization(button.dataset.org);});
document.getElementById("close-org").addEventListener("click",()=>{document.getElementById("organization-panel").classList.add("hidden");document.querySelectorAll("[data-org]").forEach(button=>button.setAttribute("aria-expanded","false"));document.getElementById("champions").scrollIntoView({behavior:"smooth",block:"start"});});
const billPicker=document.getElementById("bill-picker");billPicker.innerHTML=DATA.forecast.bills.map((bill,index)=>`<option value="${index}">${esc(bill.label)}</option>`).join("");billPicker.addEventListener("change",()=>renderForecast(Number(billPicker.value)));
setupSectionNav();setupBillControls();setupTierControls();renderAttention();renderTierRoster();renderBoard();renderForecast(0);
</script></main></body></html>
"""
    return "".join(
        (
            "<!doctype html><html lang=en><head><meta charset=utf-8>",
            '<meta name=viewport content="width=device-width,initial-scale=1">',
            "<title>Moneyball · Lobbying attention network</title>",
            style,
            body,
            script,
        )
    )


def build(
    data_root,
    out,
    bill_directions_path=None,
    bills_audit_path=None,
    congestion_path=None,
    legislators_path=None,
    voteview_path=None,
):
    data_root = os.path.abspath(data_root)
    input_paths = _input_paths(
        data_root,
        bill_directions_path=bill_directions_path,
        bills_audit_path=bills_audit_path,
        congestion_path=congestion_path,
        legislators_path=legislators_path,
        voteview_path=voteview_path,
    )
    paths_by_label = dict(input_paths)
    hashes = {label: _sha256(path, label) for label, path in input_paths}

    try:
        resolver = identity.MemberNameResolver.from_paths(
            congestion_path=paths_by_label["congestion_roster"],
            legislators_path=paths_by_label["legislators_roster"],
            voteview_path=paths_by_label["voteview_members"],
        )
    except identity.IdentityError as exc:
        raise IngestError(f"member name resolution unavailable: {exc}") from exc

    organizations = _load_org_roster(paths_by_label["fullscope_org_roster"])
    bills, bill_sectors, bill_receipt = _load_bills(paths_by_label, organizations)
    (
        sector_by_org,
        roster_sectors,
        sector_join_receipt,
        tier_by_org,
        roster_families,
    ) = _load_sector_roster(paths_by_label["sector_roster"], organizations)
    spend, tier_meta, entity_receipt = _load_spend(
        paths_by_label["sector_spend_json"],
        paths_by_label["sector_spend_csv"],
        roster_sectors,
    )
    boundaries = _merger_boundaries(entity_receipt, roster_families)
    attention, org_attention, active_orgs, orgs_by_sector, network_rows = _load_network(
        paths_by_label, organizations, sector_by_org
    )
    posture_states = PostureTable()
    champions, member_names, champion_receipt = _load_champions(
        paths_by_label["champions_csv"],
        paths_by_label["champions_json"],
        organizations,
        sector_by_org,
        orgs_by_sector,
        resolver,
        org_attention=org_attention,
        postures=posture_states,
    )
    # The tier is a LABEL on an organization already placed in a sector, so it is
    # attached after the sector join rather than inside it.
    for sector_orgs in champions.values():
        for org in sector_orgs:
            tiers = tier_by_org.get(org["id"])
            if tiers:
                org["tier"] = list(tiers)
    industries = _attention_payload(
        attention,
        member_names,
        spend,
        champions,
        resolver,
        posture_states,
        roster_families,
    )
    forecast = _load_forecast(
        paths_by_label["cosponsor_report"],
        paths_by_label["cosponsor_scores"],
        member_names,
        resolver,
    )
    matched_active = len(active_orgs & set(sector_by_org))
    sector_join_receipt.update(
        {
            "matched_active_orgs": matched_active,
            "unmatched_active_orgs": len(active_orgs) - matched_active,
        }
    )
    posture_receipt = posture_states.receipt()
    payload = {
        "industries": industries,
        "bills": bills,
        "bill_sectors": bill_sectors,
        "forecast": {"bills": forecast["bills"]},
        "postureStates": posture_states.payload(),
        "postureRule": posture.POSTURE_RULE_NOTE,
        "tierMeta": tier_meta,
        "boundaries": boundaries,
        "boundaryRule": entity_receipt.get("boundary_rule") or "",
        "years": list(YEARS),
        "receipts": {
            "bills": bill_receipt,
            "champions": champion_receipt,
            "sectors": sector_join_receipt,
            "network_rows": network_rows,
            "posture": posture_receipt,
            "member_names": resolver.receipt(),
        },
    }
    document = _document(
        _industry_cards(spend, tier_meta),
        payload,
        forecast,
        _hash_footer(input_paths, hashes),
    )
    document_bytes = len(document.encode("utf-8"))
    if document_bytes >= MAX_DOCUMENT_BYTES:
        raise IngestError(
            f"generated page is {document_bytes:,} bytes; limit is "
            f"{MAX_DOCUMENT_BYTES - 1:,}; lower retention constants explicitly"
        )
    out_path = os.path.abspath(out)
    out_dir = os.path.dirname(out_path)
    if out_dir and not os.path.isdir(out_dir):
        raise IngestError(f"output directory not found: {out_dir}")
    _write_text_atomic(document, out_path)
    print(f"industry HTML: {out_path} ({document_bytes:,} bytes)")
    return document


def _build_parser():
    parser = argparse.ArgumentParser(
        description="Build the standalone LDA bill and industry dashboard"
    )
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--out", default=os.path.join(MB_ROOT, "lobby-network.html"))
    parser.add_argument(
        "--bill-directions",
        default=os.path.join(MB_ROOT, "bill_directions.csv"),
    )
    parser.add_argument(
        "--bills-audit",
        default=os.path.join(MB_ROOT, "bills_audit.csv"),
    )
    parser.add_argument("--congestion", default=identity.DEFAULT_CONGESTION_PATH)
    parser.add_argument("--legislators", default=identity.DEFAULT_LEGISLATORS_PATH)
    parser.add_argument("--voteview", default=identity.DEFAULT_VOTEVIEW_PATH)
    return parser


def main():
    args = _build_parser().parse_args()
    try:
        build(
            args.data_root or _default_data_root(),
            args.out,
            bill_directions_path=args.bill_directions,
            bills_audit_path=args.bills_audit,
            congestion_path=args.congestion,
            legislators_path=args.legislators,
            voteview_path=args.voteview,
        )
        return 0
    except IngestError as exc:
        print(f"ERROR: {exc}")
        return 2
    except Exception as exc:
        print(f"ERROR: industry HTML build failed: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
