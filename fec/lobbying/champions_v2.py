# -*- coding: utf-8 -*-
"""Build direction-aware, mutually exclusive lobbying champion boards.

The artifact is descriptive and display-only.  It replaces direction-blind
residual attention as the champions-family headline without becoming an
engine, rank, or receptivity input.
Tier-1 crowns are never eligible for any sector's threat board, and a member
on any retained threat board holds no champions seat (the champion seat
yields, Paul 2026-08-09).  The crown set is the ACTIVE rank_honors generation's
(D-157 F-20), never the previous cycle's member_desk_bundle.json tiers; the
build fails closed when that generation is absent.

The CU "O" component is the live legislative score the rank path uses: the
``legislative_pillar.pillar`` that compute_pillars.py --write records in
ranks_python.json (D-362, Paul 2026-10-27).  The 2026-09-03
pillar_inputs_snapshot.json is never read; with no live pillar in the rank
authority the build fails closed.  Each run also writes a diff against the
previous run's boards (who entered, who left, tier moves, with reasons) into
the boards receipt, a dated file under diffs/, and standing.json for the next
run's reasons.
"""

import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # noqa: E501,E702

import argparse
import collections
import csv
import json
import math
import os
import re
import sys
from datetime import datetime, timezone

from paths import ROOT as MB_ROOT, LOCAL_MELANGE
from lobbying.active_crowns import active_board
import members.historical_member_names as identity
import members.member_identity as desk_identity

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


SCHEMA = "champions-v2-v1"
SECTORS = ("credit_union", "bank", "crypto", "fintech", "telecom")
CHAMBERS = ("House", "Senate")
SIGN_SOURCES = ("canonical", "kim", "prior")
SIGN_AUTHORITY = {source: index for index, source in enumerate(SIGN_SOURCES)}
SUPPORT_THRESHOLD = 0.7
OPPOSITION_THRESHOLD = 0.3
CHAMPION_LIMIT_PER_CHAMBER = 25
THREAT_LIMIT = 25

CU_COMPONENTS = (
    "log1p_supportive_att",
    "net_directional",
    "O",
    "log1p_invested",
    "rapport",
)
OTHER_COMPONENTS = ("log1p_supportive_att", "rapport")

VETO_RULE = (
    "VETO: opposition_att > supportive_att -> never a champion. OPPOSITION "
    "LEADERSHIP: sponsoring >= 1 corroborated-opposed bill, or cosponsoring "
    ">= 2, forces the THREAT board regardless of supportive profile, except "
    "for the Tier-1 crown rule in CHAMPION EXCLUSIVITY "
    "(2026-08-06 routing fix - the CCCA author and its Senate lead "
    "cosponsor are opposition leadership, not mixed dockets)."
)
MIXED_RULE = (
    "MIXED: not vetoed AND not opposition leadership AND "
    "opposition_att >= 3 -> issue-specific board. Tier-1 crown demotions under "
    "CHAMPION EXCLUSIVITY also land on mixed when opposition_att >= 3."
)
CHAMPION_EXCLUSIVITY_RULE = (
    "CHAMPION EXCLUSIVITY (crown supremacy, Paul 2026-08-09): a Tier-1 crown "
    "(overall display Champion) never appears on any sector's threat board. "
    "A crown whose docket would force the threat board is demoted to the mixed "
    "board when opposition_att >= 3, and is otherwise omitted and receipted "
    "under crown_threat_exclusions. Uniform across every sector."
)
CROSS_SECTOR_RULE = (
    "CROSS-SECTOR EXCLUSIVITY (champion seat yields, Paul 2026-08-09): a "
    "member on any sector's RETAINED threat board holds no champions seat in "
    "any sector - the threat seat stands (the 2026-08-06 Durbin routing fix "
    "is ratified truth) and the champions seat yields, receipted under "
    "cross_sector_exclusions. Crowns resolve the other way first (crown "
    "supremacy): they never appear as threats, so their champions seats "
    "never yield. Uniform across every sector."
)
CORROBORATION_RULE = (
    "opp_sponsored/opp_cosponsored(m) = bills m sponsors/cosponsors whose "
    "sector-oppose signal is CORROBORATED (>= 2 oppose-signed orgs of that "
    "sector on the bill). Threat = z(log1p opposition_att) + opp_sponsored "
    "+ 0.5 * opp_cosponsored."
)
METHOD_NOTE = (
    "Signed attention is inferred (leads, not disclosures) except canonical "
    "rows, which carry Paul's marks; boards are DESCRIPTIVE decision aids - "
    "no engine, rank, or receptivity input reads them."
)

BILL_TYPE_ALIASES = {
    "HR": "hr",
    "HRES": "hres",
    "HJRES": "hjres",
    "HCONRES": "hconres",
    "S": "s",
    "SRES": "sres",
    "SJRES": "sjres",
    "SCONRES": "sconres",
}
BILL_KEY_RE = re.compile(r"^\d{3}:[a-z]+:\d+$")


class ChampionsV2Error(RuntimeError):
    """An input or structural contract failed; publish no partial artifact."""


def _derived_dir():
    return os.path.join(LOCAL_MELANGE, "lda_rebuild", "derived")


def _default_paths():
    derived = _derived_dir()
    return {
        "signed_attention_path": os.path.join(
            derived, "stance_priors", "signed_attention.csv"
        ),
        "interactions_path": os.path.join(
            derived, "interactions", "interaction_bill_members.csv"
        ),
        "panel_path": os.path.join(
            derived, "member_congress_panel", "panel.csv"
        ),
        "ranks_path": os.path.join(MB_ROOT, "ranks_python.json"),
        "member_bundle_path": os.path.join(MB_ROOT, "member_desk_bundle.json"),
        "titles_path": os.path.join(derived, "bill_titles", "titles.json"),
        "bill_directions_path": os.path.join(
            MB_ROOT, "data", "legislation", "bill_directions.csv"
        ),
    }


def _iter_csv(path, label, required_fields):
    try:
        handle = open(path, "r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise ChampionsV2Error(f"cannot read {label} {path}: {exc}") from exc
    with handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        missing = sorted(set(required_fields) - fields)
        if missing:
            raise ChampionsV2Error(
                f"{label} lacks required columns: {', '.join(missing)}"
            )
        try:
            for row_number, row in enumerate(reader, start=2):
                yield row_number, row
        except csv.Error as exc:
            raise ChampionsV2Error(f"cannot parse {label} {path}: {exc}") from exc


def _load_json(path, label):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError) as exc:
        raise ChampionsV2Error(f"cannot read {label} {path}: {exc}") from exc


def _number(value, label, minimum=None, maximum=None):
    if isinstance(value, bool):
        raise ChampionsV2Error(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ChampionsV2Error(f"{label} must be numeric") from exc
    if not math.isfinite(number):
        raise ChampionsV2Error(f"{label} must be finite")
    if minimum is not None and number < minimum:
        raise ChampionsV2Error(f"{label} must be at least {minimum}")
    if maximum is not None and number > maximum:
        raise ChampionsV2Error(f"{label} must be at most {maximum}")
    return number


def _integer(value, label):
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ChampionsV2Error(f"{label} must be an integer") from exc
    return number


def _bill_key(value, label):
    key = (value or "").strip().lower()
    if not BILL_KEY_RE.match(key):
        raise ChampionsV2Error(f"{label} has invalid bill_key {value!r}")
    return key


def _load_signed_attention(path):
    required = (
        "lob_id", "client_name", "bill_key", "org_sector",
        "sign_source", "p_support", "label",
    )
    rows = []
    seen = set()
    sign_coverage = {
        sector: {source: 0 for source in SIGN_SOURCES} for sector in SECTORS
    }
    for row_number, row in _iter_csv(path, "signed attention", required):
        lob_id = (row.get("lob_id") or "").strip()
        if not lob_id:
            raise ChampionsV2Error(
                f"signed attention row {row_number} has blank lob_id"
            )
        bill = _bill_key(
            row.get("bill_key"), f"signed attention row {row_number}"
        )
        sectors = tuple(
            sector for sector in SECTORS
            if sector in {
                token.strip()
                for token in (row.get("org_sector") or "").split("|")
                if token.strip()
            }
        )
        source = (row.get("sign_source") or "").strip().casefold()
        raw_probability = (row.get("p_support") or "").strip()
        probability = None
        if raw_probability:
            probability = _number(
                raw_probability,
                f"signed attention row {row_number} p_support",
                minimum=0.0,
                maximum=1.0,
            )
            if source not in SIGN_AUTHORITY:
                raise ChampionsV2Error(
                    f"signed attention row {row_number} has a probability but "
                    f"unsupported sign_source {source!r}"
                )
        identity_key = (lob_id, bill)
        if identity_key in seen:
            raise ChampionsV2Error(
                f"signed attention repeats org-bill pair {lob_id} / {bill}"
            )
        seen.add(identity_key)
        for sector in sectors:
            if probability is not None and source in SIGN_AUTHORITY:
                sign_coverage[sector][source] += 1
        rows.append(
            {
                "lob_id": lob_id,
                "bill_key": bill,
                "sectors": sectors,
                "sign_source": source,
                "p_support": probability,
            }
        )
    if not rows:
        raise ChampionsV2Error("signed attention has no rows")
    return rows, sign_coverage


def _load_interactions(path):
    required = ("bill_key", "bioguide_id", "role")
    members_by_bill = collections.defaultdict(dict)
    rows = 0
    for row_number, row in _iter_csv(path, "interaction bill members", required):
        rows += 1
        bill = _bill_key(row.get("bill_key"), f"interaction row {row_number}")
        bioguide = (row.get("bioguide_id") or "").strip()
        role = (row.get("role") or "").strip().casefold()
        if not bioguide:
            raise ChampionsV2Error(f"interaction row {row_number} has blank bioguide")
        if role not in {"sponsor", "cosponsor"}:
            raise ChampionsV2Error(
                f"interaction row {row_number} has unsupported role {role!r}"
            )
        previous = members_by_bill[bill].get(bioguide)
        if previous is not None and previous != role:
            raise ChampionsV2Error(
                f"interaction bill {bill} maps {bioguide} to two roles"
            )
        members_by_bill[bill][bioguide] = role
    if not rows:
        raise ChampionsV2Error("interaction bill members has no rows")
    return members_by_bill, rows


def _load_panel(path):
    required = ("bioguide", "congress", "chamber", "net_directional")
    net_by_member = collections.defaultdict(float)
    seen = set()
    rows = 0
    for row_number, row in _iter_csv(path, "member-congress panel", required):
        congress = _integer(
            row.get("congress"), f"member-congress panel row {row_number} congress"
        )
        if congress not in {117, 118, 119}:
            continue
        rows += 1
        bioguide = (row.get("bioguide") or "").strip()
        if not bioguide:
            raise ChampionsV2Error(
                f"member-congress panel row {row_number} has blank bioguide"
            )
        key = (bioguide, congress)
        if key in seen:
            raise ChampionsV2Error(
                f"member-congress panel repeats {bioguide} / {congress}"
            )
        seen.add(key)
        net_by_member[bioguide] += _number(
            row.get("net_directional"),
            f"member-congress panel row {row_number} net_directional",
        )
    if not rows:
        raise ChampionsV2Error("member-congress panel has no 117-119 rows")
    return dict(net_by_member), rows


LIVE_PILLAR_SCHEMA = "live-legislative-pillar-v1"


def _load_o(path):
    """O = the rank authority's live legislative pillar (D-362); no snapshot fallback."""
    payload = _load_json(path, "rank authority")
    pillar = payload.get("legislative_pillar") if isinstance(payload, dict) else None
    if not isinstance(pillar, dict):
        raise ChampionsV2Error(
            f"rank authority {path} carries no live legislative pillar "
            "(sentinel_admission_policy live_legislative_pillar is off or the "
            "ranks predate it); champions will not fall back to "
            "pillar_inputs_snapshot.json -- run compute_pillars.py --write"
        )
    if pillar.get("schema") != LIVE_PILLAR_SCHEMA:
        raise ChampionsV2Error(
            f"rank authority legislative pillar schema {pillar.get('schema')!r} "
            f"is not {LIVE_PILLAR_SCHEMA!r}"
        )
    values = pillar.get("pillar")
    if not isinstance(values, dict) or not values:
        raise ChampionsV2Error("rank authority legislative pillar is empty")
    o_by_name = {
        str(name): _number(value, f"live legislative pillar for {name}", 0.0, 1.0)
        for name, value in values.items()
    }
    source = {
        "path": os.path.basename(path),
        "field": "legislative_pillar.pillar",
        "schema": LIVE_PILLAR_SCHEMA,
        "members": len(o_by_name),
        "inputs_sha256": pillar.get("inputs_sha256"),
    }
    return o_by_name, source


def _load_member_bundle(path):
    payload = _load_json(path, "member desk bundle")
    members = payload.get("members") if isinstance(payload, dict) else None
    if not isinstance(members, list) or not members:
        raise ChampionsV2Error("member desk bundle lacks non-empty members list")
    by_name = {}
    name_to_bioguide = {}
    for index, row in enumerate(members):
        if not isinstance(row, dict):
            raise ChampionsV2Error(f"member desk bundle row {index} is not an object")
        missing = {
            field for field in ("name", "chamber", "invested")
            if field not in row
        }
        if missing:
            raise ChampionsV2Error(
                f"member desk bundle row {index} lacks {', '.join(sorted(missing))}"
            )
        name = str(row.get("name") or "").strip()
        chamber = str(row.get("chamber") or "").strip()
        if not name or chamber not in CHAMBERS:
            raise ChampionsV2Error(
                f"member desk bundle row {index} has invalid name/chamber"
            )
        if name in by_name:
            raise ChampionsV2Error(f"member desk bundle repeats member name {name!r}")
        by_name[name] = {
            "chamber": chamber,
            "invested": _number(
                row.get("invested"), f"member desk bundle invested for {name}", minimum=0
            ),
        }
        bio = row.get("bio")
        bioguide = (bio.get("bioguide") or "").strip() if isinstance(bio, dict) else ""
        if bioguide:
            name_to_bioguide[name] = bioguide
    return (
        by_name,
        desk_identity.Resolver(by_name, name_to_bioguide=name_to_bioguide),
        len(members),
    )


def _load_crown_tiers():
    """(tier, board seat, generation id) by desk name from the ACTIVE rank_honors generation; fails closed."""
    try:
        return active_board(MB_ROOT)
    except ValueError as exc:
        raise ChampionsV2Error(f"crown set unavailable: {exc}") from exc


def _load_titles(path):
    payload = _load_json(path, "bill title cache")
    schema = payload.get("schema") if isinstance(payload, dict) else None
    if not isinstance(payload, dict) or payload.get("schema") != "bill-titles-v1":
        raise ChampionsV2Error(f"bill title cache schema mismatch: {schema!r}")
    titles = payload.get("titles")
    if not isinstance(titles, dict):
        raise ChampionsV2Error("bill title cache lacks titles mapping")
    return {
        _bill_key(key, "bill title cache"): str(value or "").strip()
        for key, value in titles.items()
    }


def _direction_bill_key(bill, congress, label):
    normalized = re.sub(r"[^A-Z0-9]", "", str(bill or "").upper())
    match = re.match(r"^([A-Z]+)(\d+)$", normalized)
    if not match or match.group(1) not in BILL_TYPE_ALIASES:
        raise ChampionsV2Error(f"{label} has unsupported Bill value {bill!r}")
    congress_number = _integer(congress, f"{label} Congress")
    return f"{congress_number}:{BILL_TYPE_ALIASES[match.group(1)]}:{int(match.group(2))}"


def _load_bill_directions(path):
    required = ("Bill", "Congress", "Category")
    categories = {}
    rows = 0
    for row_number, row in _iter_csv(path, "bill directions", required):
        rows += 1
        # Coordinator fix 2026-08-06: the canonical file carries rows with a
        # blank Congress (14, known-unjoinable) and rows with a blank
        # Category (optional issue label).  Both fall through: the issue
        # string falls back to the title cache downstream.
        congress_raw = (row.get("Congress") or "").strip()
        category = (row.get("Category") or "").strip()
        if not congress_raw or not category:
            continue
        key = _direction_bill_key(
            row.get("Bill"), congress_raw, f"bill directions row {row_number}"
        )
        previous = categories.get(key)
        if previous is not None and previous != category:
            raise ChampionsV2Error(
                f"bill directions maps {key} to two categories"
            )
        categories[key] = category
    if not rows:
        raise ChampionsV2Error("bill directions has no rows")
    return categories, rows


def _z_scores(rows, value):
    if not rows:
        return {}
    values = [float(value(row)) for row in rows]
    mean = sum(values) / len(values)
    variance = sum((item - mean) ** 2 for item in values) / len(values)
    scale = math.sqrt(variance)
    if scale <= 1e-12:
        return {row["bioguide"]: 0.0 for row in rows}
    return {
        row["bioguide"]: (item - mean) / scale
        for row, item in zip(rows, values)
    }


def _driving_bills(
    member,
    sector,
    opposed_bills,
    opposed_sponsored,
    oppose_orgs_by_bill,
    oppose_sources_by_bill,
    titles,
    categories,
):
    sponsored = opposed_sponsored.get(member, set())
    if sponsored:
        bills = sorted(
            sponsored,
            key=lambda bill: (-len(oppose_orgs_by_bill[sector][bill]), bill),
        )
    else:
        bills = sorted(
            opposed_bills.get(member, set()),
            key=lambda bill: (-len(oppose_orgs_by_bill[sector][bill]), bill),
        )[:3]
    driving = []
    issues = []
    for bill in bills:
        source_counts = oppose_sources_by_bill[sector].get(bill, {})
        source = min(source_counts, key=lambda item: SIGN_AUTHORITY[item])
        title = titles.get(bill) or bill
        category = categories.get(bill) or ""
        driving.append(
            {
                "bill_key": bill,
                "title": title,
                "category": category,
                "sign_source": source,
            }
        )
        issues.append(category or title or bill)
    return issues, driving


def _score_rows(rows, sector):
    component_names = CU_COMPONENTS if sector == "credit_union" else OTHER_COMPONENTS
    feature_getters = {
        "log1p_supportive_att": lambda row: math.log1p(row["components"]["supportive_att"]),
        "net_directional": lambda row: row["components"]["net_directional"],
        "O": lambda row: row["components"]["O"],
        "log1p_invested": lambda row: math.log1p(row["components"]["invested"]),
        "rapport": lambda row: row["components"]["rapport"],
    }
    for chamber in CHAMBERS:
        chamber_rows = [row for row in rows if row["chamber"] == chamber]
        component_z = [
            _z_scores(chamber_rows, feature_getters[name]) for name in component_names
        ]
        opposition_z = _z_scores(
            chamber_rows,
            lambda row: math.log1p(row["components"]["opposition_att"]),
        )
        for row in chamber_rows:
            bioguide = row["bioguide"]
            composite = sum(values[bioguide] for values in component_z) / len(component_z)
            threat = (
                opposition_z[bioguide]
                + row["components"]["opp_sponsored"]
                + 0.5 * row["components"]["opp_cosponsored"]
            )
            if not math.isfinite(composite) or not math.isfinite(threat):
                raise ChampionsV2Error(
                    f"non-finite score for {sector} / {bioguide}"
                )
            row["composite"] = round(composite, 6)
            row["threat"] = round(threat, 6)


def _row_sort(row, score_field):
    return (-row[score_field], row["name"].casefold(), row["bioguide"])


def _assert_boards(sector, boards, crown_bioguides, threat_bioguides):
    memberships = {}
    for board_name in ("champions", "threats", "mixed"):
        for row in boards[board_name]:
            bioguide = row["bioguide"]
            if bioguide in memberships:
                raise ChampionsV2Error(
                    f"{sector} board overlap: {bioguide} appears on "
                    f"{memberships[bioguide]} and {board_name}"
                )
            memberships[bioguide] = board_name
            if board_name == "threats" and bioguide in crown_bioguides:
                raise ChampionsV2Error(
                    f"{sector} champion exclusivity failure: "
                    f"{bioguide} Tier-1 crown reached threats"
                )
            if board_name == "champions" and bioguide in threat_bioguides:
                raise ChampionsV2Error(
                    f"{sector} cross-sector exclusivity failure: "
                    f"{bioguide} holds a champions seat while on a threat board"
                )
            if not math.isfinite(row["composite"]):
                raise ChampionsV2Error(
                    f"{sector} {board_name} row {bioguide} has non-finite composite"
                )
    for row in boards["champions"]:
        components = row["components"]
        if components["opposition_att"] > components["supportive_att"]:
            raise ChampionsV2Error(
                f"{sector} veto failure: {row['bioguide']} reached champions"
            )


BOARD_NAMES = ("champions", "threats", "mixed")
DIFF_SCHEMA = "champions-v2-run-diff-v1"
STANDING_SCHEMA = "champions-v2-standing-v1"
DIFF_COMPONENTS = (
    "O", "supportive_att", "opposition_att", "net_directional", "invested",
    "rapport", "opp_sponsored", "opp_cosponsored",
)
PLACEMENT_TEXT = {
    "champions": "a champions seat",
    "threats": "the threat board",
    "mixed": "the mixed board",
    "below_cut": "below the champions cut",
    "cross_sector_excluded": "champions class, but the seat yields to a retained threat seat",
    "threat_cut": "beyond the 25-seat threat cap",
    "crown_omitted": "omitted as a Tier-1 crown (crown law; opposition below the mixed threshold)",
    "former": "a former member",
    "desk_unavailable": "not on the member desk",
    "absent": "no signed lobbying attention in this sector",
    "off_board": "off the boards (the previous run kept no detail)",
}


def _standing_entry(row, placement, tier_seat=(None, None), **extra):
    components = row.get("components") or {}
    entry = {
        "name": row.get("name"),
        "chamber": row.get("chamber"),
        "placement": placement,
        "composite": row.get("composite"),
        "threat": row.get("threat"),
        "crown_tier": tier_seat[0],
        "primacy_seat": tier_seat[1],
        "components": {
            key: components.get(key) for key in DIFF_COMPONENTS if key in components
        },
    }
    entry.update(extra)
    return entry


def _sector_standing(staged, boards, cross_sector_exclusions, tier_by_bioguide):
    """Where every candidate of one sector landed this run, and on what inputs."""
    placement = {}
    for board_name in BOARD_NAMES:
        for row in boards[board_name]:
            placement[row["bioguide"]] = board_name
    yielded = {item["bioguide"]: item["threat_sectors"] for item in cross_sector_exclusions}
    capped = {row["bioguide"] for row in staged["threat_cut"]}
    omitted = {
        item["bioguide"] for item in staged["crown_threat_exclusions"]
        if item["routed_to"] == "omitted"
    }
    out = {}
    for row in staged["rows"]:
        bioguide = row["bioguide"]
        extra = {}
        if bioguide in placement:
            where = placement[bioguide]
        elif bioguide in yielded:
            where, extra = "cross_sector_excluded", {"threat_sectors": yielded[bioguide]}
        elif bioguide in capped:
            where = "threat_cut"
        elif bioguide in omitted:
            where = "crown_omitted"
        else:
            where = "below_cut"
        out[bioguide] = _standing_entry(
            row, where, tier_by_bioguide.get(bioguide, (None, None)), **extra
        )
    for bioguide in staged["former_members"]:
        out[bioguide] = {"name": None, "placement": "former"}
    for bioguide in staged["desk_unavailable_members"]:
        out[bioguide] = {"name": None, "placement": "desk_unavailable"}
    return out


def _standing_from_payload(payload):
    """Best-effort standing for a previous run that wrote no standing.json."""
    out = {}
    receipts = (payload.get("receipt") or {}).get("sectors") or {}
    for sector in SECTORS:
        boards = (payload.get("sectors") or {}).get(sector) or {}
        receipt = receipts.get(sector) or {}
        sector_out = {}
        for bioguide in receipt.get("former_bioguides") or ():
            sector_out[bioguide] = {"name": None, "placement": "former"}
        for item in receipt.get("crown_threat_exclusions") or ():
            if item.get("routed_to") == "omitted":
                sector_out[item["bioguide"]] = {
                    "name": item.get("name"), "chamber": item.get("chamber"),
                    "placement": "crown_omitted", "crown_tier": 1,
                }
        for item in receipt.get("cross_sector_exclusions") or ():
            sector_out[item["bioguide"]] = {
                "name": item.get("name"), "chamber": item.get("chamber"),
                "placement": "cross_sector_excluded", "composite": item.get("composite"),
                "threat_sectors": item.get("threat_sectors"),
            }
        for board_name in BOARD_NAMES:
            for row in boards.get(board_name) or ():
                sector_out[row["bioguide"]] = _standing_entry(
                    row, board_name, (row.get("tier"), None)
                )
        out[sector] = sector_out
    return out


def _fmt(value):
    if isinstance(value, float) and not value.is_integer():
        return f"{value:.4f}"
    if isinstance(value, float):
        return str(int(value))
    return str(value)


def _champion_cuts(boards):
    """Composite of the last retained champion per chamber when the board is full."""
    cuts = {}
    for chamber in CHAMBERS:
        rows = [row for row in boards["champions"] if row["chamber"] == chamber]
        if len(rows) >= CHAMPION_LIMIT_PER_CHAMBER:
            cuts[chamber] = min(row["composite"] for row in rows)
    return cuts


def _seat(boards, board_name, bioguide):
    rows = boards[board_name]
    chamber = next(row["chamber"] for row in rows if row["bioguide"] == bioguide)
    same = [row["bioguide"] for row in rows if row["chamber"] == chamber]
    return same.index(bioguide) + 1


def _move_reason(old, new, boards, bioguide, cuts):
    old_place = (old or {}).get("placement", "absent")
    new_place = (new or {}).get("placement", "absent")
    from_text = PLACEMENT_TEXT.get(old_place, old_place)
    to_text = PLACEMENT_TEXT.get(new_place, new_place)
    if new_place == "cross_sector_excluded":
        to_text += " in " + ", ".join(new.get("threat_sectors") or ())
    parts = [f"{from_text} -> {to_text}"]
    chamber = (new or old or {}).get("chamber")
    score = "threat" if new_place == "threats" else "composite"
    value = (new or {}).get(score)
    if new_place in BOARD_NAMES:
        seat = _seat(boards, new_place, bioguide)
        parts.append(f"{score} {_fmt(value)}, {chamber} seat {seat}")
    elif new_place == "below_cut" and value is not None and chamber in cuts:
        parts.append(
            f"composite {_fmt(value)} is below the {chamber} cut {_fmt(cuts[chamber])}"
        )
    old_value = (old or {}).get(score)
    if value is not None and old_value is not None:
        parts.append(f"{score} was {_fmt(old_value)}")
    old_components = (old or {}).get("components") or {}
    new_components = (new or {}).get("components") or {}
    changed = {
        key: [old_components[key], new_components[key]]
        for key in DIFF_COMPONENTS
        if key in old_components and key in new_components
        and old_components[key] is not None and new_components[key] is not None
        and abs(float(old_components[key]) - float(new_components[key])) > 1e-9
    }
    if changed:
        parts.append("inputs changed: " + ", ".join(
            f"{key} {_fmt(pair[0])} -> {_fmt(pair[1])}" for key, pair in changed.items()
        ))
    # The cause, most specific first; the generic displacement text only when nothing else applies.
    old_tier, new_tier = (old or {}).get("crown_tier"), (new or {}).get("crown_tier")
    crown_routed = {old_place, new_place} & {"threats", "threat_cut", "crown_omitted"}
    if (old_tier is not None and new_tier is not None
            and (old_tier == 1) != (new_tier == 1) and crown_routed):
        # Only gaining or losing the crown re-routes a member (crown law); other tier moves do not.
        parts.append(f"moved because it {'gained' if new_tier == 1 else 'lost'} the crown "
                     f"(tier {old_tier} -> {new_tier}; crown law)")
    elif new_place == "cross_sector_excluded":
        parts.append(
            "its champions seat yields to its retained threat seat in "
            + ", ".join(new.get("threat_sectors") or ())
        )
    elif old_place == "cross_sector_excluded":
        parts.append(
            "its threat seat in " + ", ".join(old.get("threat_sectors") or ())
            + " is no longer retained"
        )
    elif (new_place == "champions" and old_place == "below_cut"
          and value is not None and old_value is not None and value <= old_value):
        parts.append("its score did not rise; members above it left the board or fell below the cut")
    elif (old_place == "champions" and new_place == "below_cut"
          and value is not None and old_value is not None and value >= old_value):
        parts.append("its score did not fall; displaced by members now ranked above it")
    elif not changed and old_components and new_components:
        parts.append("own inputs unchanged; moved because other members' scores changed")
    return "; ".join(parts), changed


def champions_diff(previous, previous_standing, payload, standing):
    """Seat-level diff of this run's boards against the previous run's, with reasons."""
    baseline = "previous boards.json"
    unknown_old = None    # a member missing from a full previous standing had no attention
    if previous is None:
        baseline = "none: no previous boards.json, so every seat is new"
        previous_standing = {}
    elif previous_standing is None:
        baseline = "previous boards.json (no matching standing.json; reasons use board rows only)"
        previous_standing = _standing_from_payload(previous)
        unknown_old = {"placement": "off_board"}    # off the old boards, placement unrecorded
    previous_receipt = (previous or {}).get("receipt") or {}
    sectors = {}
    lines = []
    tier_moves = {}
    for sector in SECTORS:
        boards = payload["sectors"][sector]
        old_boards = ((previous or {}).get("sectors") or {}).get(sector) or {}
        old = previous_standing.get(sector) or {}
        new = standing.get(sector) or {}
        cuts = _champion_cuts(boards)
        sector_diff = {}
        counts = []
        for board_name in BOARD_NAMES:
            old_set = {row["bioguide"] for row in old_boards.get(board_name) or ()}
            new_set = {row["bioguide"] for row in boards[board_name]}
            moves = {"entered": [], "left": []}
            for key, members in (("entered", new_set - old_set), ("left", old_set - new_set)):
                for bioguide in sorted(members):
                    before, after = old.get(bioguide, unknown_old), new.get(bioguide)
                    reason, changed = _move_reason(before, after, boards, bioguide, cuts)
                    moves[key].append({
                        "bioguide": bioguide,
                        "name": (after or {}).get("name") or (before or {}).get("name"),
                        "chamber": (after or {}).get("chamber") or (before or {}).get("chamber"),
                        "from": (before or {}).get("placement", "absent"),
                        "to": (after or {}).get("placement", "absent"),
                        "inputs_changed": changed,
                        "reason": reason,
                    })
            sector_diff[board_name] = moves
            counts.append(f"{board_name} +{len(moves['entered'])}/-{len(moves['left'])}")
        sector_diff["champion_cut"] = cuts
        sectors[sector] = sector_diff
        lines.append(f"{sector}: " + ", ".join(counts))
        for bioguide, after in new.items():
            before = old.get(bioguide) or {}
            if (
                bioguide in tier_moves
                or before.get("crown_tier") is None
                or after.get("crown_tier") is None
                or before["crown_tier"] == after["crown_tier"]
            ):
                continue
            reason = f"tier {before['crown_tier']} -> {after['crown_tier']} on the rank_honors board"
            if unknown_old is not None:
                reason += " (the previous tier is read from the previous boards' rows)"
            if before.get("primacy_seat") and after.get("primacy_seat"):
                reason += f", primacy seat {before['primacy_seat']} -> {after['primacy_seat']}"
            if after["crown_tier"] == 1:
                reason += "; gains the crown (crown law: never on a threat board)"
            elif before["crown_tier"] == 1:
                reason += "; loses the crown (no longer protected from threat boards)"
            tier_moves[bioguide] = {
                "bioguide": bioguide,
                "name": after.get("name"),
                "from_tier": before["crown_tier"],
                "to_tier": after["crown_tier"],
                "reason": reason,
            }
    moved = sum(
        len(sectors[sector][board][key])
        for sector in SECTORS for board in BOARD_NAMES for key in ("entered", "left")
    )
    changed = bool(moved or tier_moves)
    summary = (
        "; ".join(lines) + f"; tier moves {len(tier_moves)}"
        if changed else
        "No champions, threat or mixed seat changed and no tier moved since the previous run."
    )
    return {
        "schema": DIFF_SCHEMA,
        "baseline": baseline,
        "previous_generated_utc": (previous or {}).get("generated_utc"),
        "generated_utc": payload.get("generated_utc"),
        "previous_honors_generation": previous_receipt.get("honors_generation"),
        "honors_generation": payload["receipt"].get("honors_generation"),
        "previous_o_source": previous_receipt.get(
            "o_source",
            None if previous is None else
            "not recorded: runs before D-362 read data/engine/pillar_inputs_snapshot.json",
        ),
        "o_source": payload["receipt"].get("o_source"),
        "changed": changed,
        "summary": summary,
        "sectors": sectors,
        "tier_moves": sorted(
            tier_moves.values(), key=lambda item: (item["name"] or "", item["bioguide"])
        ),
    }


def _load_previous(out_path):
    """(previous boards payload or None, its standing or None, note)."""
    if not os.path.exists(out_path):
        return None, None, None
    try:
        previous = _load_json(out_path, "previous champions boards")
    except ChampionsV2Error as exc:
        return None, None, str(exc)
    if not isinstance(previous, dict) or previous.get("schema") != SCHEMA:
        return None, None, "previous boards.json has another schema"
    standing_path = os.path.join(os.path.dirname(os.path.abspath(out_path)), "standing.json")
    try:
        standing = _load_json(standing_path, "previous standing")
    except ChampionsV2Error:    # absent or unreadable: reasons fall back to board rows
        return previous, None, None
    if (
        isinstance(standing, dict)
        and standing.get("schema") == STANDING_SCHEMA
        and standing.get("boards_generated_utc") == previous.get("generated_utc")
        and isinstance(standing.get("sectors"), dict)
    ):
        return previous, standing.get("sectors"), None
    return previous, None, None


def build_payload(
    signed_attention_path=None,
    interactions_path=None,
    panel_path=None,
    ranks_path=None,
    member_bundle_path=None,
    titles_path=None,
    bill_directions_path=None,
    resolver=None,
    crown_tiers=None,
    standing=None,
):
    """Build the boards.  ``standing``, when a dict, is filled with every
    candidate's placement and inputs per sector (the next run's diff reasons)."""
    honors_generation = None    # None: the caller passed crown_tiers itself
    crown_seats = {}
    if crown_tiers is None:
        crown_tiers, crown_seats, honors_generation = _load_crown_tiers()
    defaults = _default_paths()
    signed_attention_path = signed_attention_path or defaults["signed_attention_path"]
    interactions_path = interactions_path or defaults["interactions_path"]
    panel_path = panel_path or defaults["panel_path"]
    ranks_path = ranks_path or defaults["ranks_path"]
    member_bundle_path = member_bundle_path or defaults["member_bundle_path"]
    titles_path = titles_path or defaults["titles_path"]
    bill_directions_path = bill_directions_path or defaults["bill_directions_path"]

    signed_rows, sign_coverage = _load_signed_attention(signed_attention_path)
    members_by_bill, interaction_rows = _load_interactions(interactions_path)
    net_by_member, panel_rows = _load_panel(panel_path)
    o_by_name, o_source = _load_o(ranks_path)
    desk_by_name, desk_resolver, desk_members = _load_member_bundle(member_bundle_path)
    titles = _load_titles(titles_path)
    categories, direction_rows = _load_bill_directions(bill_directions_path)
    if resolver is None:
        try:
            resolver = identity.MemberNameResolver.from_paths()
        except identity.IdentityError as exc:
            raise ChampionsV2Error(f"member-name resolver unavailable: {exc}") from exc

    support = {sector: collections.Counter() for sector in SECTORS}
    opposition = {sector: collections.Counter() for sector in SECTORS}
    support_congresses = {
        sector: collections.defaultdict(set) for sector in SECTORS
    }
    opposed_bills = {
        sector: collections.defaultdict(set) for sector in SECTORS
    }
    member_oppose_sources = {
        sector: collections.defaultdict(collections.Counter) for sector in SECTORS
    }
    oppose_orgs_by_bill = {
        sector: collections.defaultdict(set) for sector in SECTORS
    }
    oppose_sources_by_bill = {
        sector: collections.defaultdict(collections.Counter) for sector in SECTORS
    }
    signed_bills_without_members = set()

    for signed in signed_rows:
        probability = signed["p_support"]
        if probability is None:
            continue
        bill = signed["bill_key"]
        bill_members = members_by_bill.get(bill, {})
        if not bill_members:
            signed_bills_without_members.add(bill)
            continue
        congress = _integer(bill.split(":", 1)[0], f"bill congress for {bill}")
        for sector in signed["sectors"]:
            if probability >= SUPPORT_THRESHOLD:
                for member in bill_members:
                    support[sector][member] += 1
                    support_congresses[sector][member].add(congress)
            elif probability <= OPPOSITION_THRESHOLD:
                oppose_orgs_by_bill[sector][bill].add(signed["lob_id"])
                oppose_sources_by_bill[sector][bill][signed["sign_source"]] += 1
                for member in bill_members:
                    opposition[sector][member] += 1
                    opposed_bills[sector][member].add(bill)
                    member_oppose_sources[sector][member][signed["sign_source"]] += 1

    opposed_sponsored = {
        sector: collections.defaultdict(set) for sector in SECTORS
    }
    # Coordinator routing fix (2026-08-06, the Durbin/Marshall acceptance
    # probe): corroborated opposed COSPONSORSHIP also counts - the CCCA's
    # Senate lead cosponsor is opposition leadership, not a mixed docket.
    opposed_cosponsored = {
        sector: collections.defaultdict(set) for sector in SECTORS
    }
    for sector in SECTORS:
        for bill, orgs in oppose_orgs_by_bill[sector].items():
            if len(orgs) < 2:
                continue
            for member, role in members_by_bill.get(bill, {}).items():
                if role == "sponsor":
                    opposed_sponsored[sector][member].add(bill)
                else:
                    opposed_cosponsored[sector][member].add(bill)

    sectors_payload = {}
    sector_receipts = {}
    staged_sectors = {}
    all_formers = set()
    all_desk_unavailable = set()
    crown_bioguides = set()
    crown_tier_by_bioguide = {}
    for sector in SECTORS:
        candidates = sorted(set(support[sector]) | set(opposition[sector]))
        rows = []
        former_members = []
        desk_unavailable_members = []
        for bioguide in candidates:
            try:
                record = resolver.resolve(bioguide)
            except identity.IdentityError as exc:
                raise ChampionsV2Error(
                    f"cannot resolve member {bioguide}: {exc}"
                ) from exc
            if record["is_former"]:
                former_members.append(bioguide)
                all_formers.add(bioguide)
                continue
            if record["status"] == identity.STATUS_UNRESOLVED:
                raise ChampionsV2Error(
                    f"current-board candidate {bioguide} has no resolvable name"
                )
            resolved_name = record["name"]
            name = desk_resolver.resolve(name=resolved_name, bioguide=bioguide)
            if name is None:
                desk_unavailable_members.append(bioguide)
                all_desk_unavailable.add(bioguide)
                continue
            desk = desk_by_name[name]
            if name not in crown_tiers:
                raise ChampionsV2Error(
                    f"desk member {name!r} ({sector} / {bioguide}) is absent "
                    "from the active rank_honors generation"
                )
            desk_tier = crown_tiers[name]
            crown_tier_by_bioguide[bioguide] = (desk_tier, crown_seats.get(name))
            if desk_tier == 1:
                crown_bioguides.add(bioguide)
            supportive_att = int(support[sector][bioguide])
            opposition_att = int(opposition[sector][bioguide])
            components = {
                "supportive_att": supportive_att,
                "opposition_att": opposition_att,
                "opp_sponsored": len(opposed_sponsored[sector].get(bioguide, set())),
                "opp_cosponsored": len(opposed_cosponsored[sector].get(bioguide, set())),
                "rapport": len(support_congresses[sector].get(bioguide, set())),
                "net_directional": None,
                "O": None,
                "invested": None,
                "sign_source_counts": {
                    source: int(member_oppose_sources[sector][bioguide][source])
                    for source in SIGN_SOURCES
                },
            }
            if sector == "credit_union":
                if bioguide not in net_by_member:
                    raise ChampionsV2Error(
                        f"CU candidate {bioguide} is absent from the 117-119 panel"
                    )
                if name not in o_by_name:
                    raise ChampionsV2Error(
                        f"CU candidate {bioguide} / {name} is absent from the live legislative pillar"
                    )
                components.update(
                    {
                        "net_directional": net_by_member[bioguide],
                        "O": o_by_name[name],
                        "invested": desk["invested"],
                    }
                )
            rows.append(
                {
                    "bioguide": bioguide,
                    "name": name,
                    "chamber": desk["chamber"],
                    "tier": desk_tier if sector == "credit_union" else None,
                    "components": components,
                    "composite": 0.0,
                    "threat": 0.0,
                    "issues": [],
                    "driving_bills": [],
                }
            )

        _score_rows(rows, sector)
        champions = []
        threats = []
        mixed = []
        crown_threat_exclusions = []
        for row in rows:
            components = row["components"]
            vetoed = components["opposition_att"] > components["supportive_att"]
            # Opposition LEADERSHIP forces the threat board regardless of the
            # member's supportive profile (2026-08-06 routing fix): sponsoring
            # any corroborated-opposed bill, or cosponsoring two or more.
            opposition_leader = (
                components["opp_sponsored"] >= 1
                or components["opp_cosponsored"] >= 2
            )
            is_mixed = (
                not vetoed
                and not opposition_leader
                and components["opposition_att"] >= 3
            )
            if vetoed or opposition_leader:
                row["issues"], row["driving_bills"] = _driving_bills(
                    row["bioguide"], sector, opposed_bills[sector],
                    opposed_sponsored[sector], oppose_orgs_by_bill,
                    oppose_sources_by_bill, titles, categories,
                )
                if row["bioguide"] in crown_bioguides:
                    routed_to = (
                        "mixed" if components["opposition_att"] >= 3 else "omitted"
                    )
                    if routed_to == "mixed":
                        mixed.append(row)
                    crown_threat_exclusions.append(
                        {
                            "bioguide": row["bioguide"],
                            "name": row["name"],
                            "chamber": row["chamber"],
                            "tier": 1,
                            "threat": row["threat"],
                            "opposition_att": components["opposition_att"],
                            "opp_sponsored": components["opp_sponsored"],
                            "opp_cosponsored": components["opp_cosponsored"],
                            "routed_to": routed_to,
                        }
                    )
                else:
                    threats.append(row)
            elif is_mixed:
                row["issues"], row["driving_bills"] = _driving_bills(
                    row["bioguide"], sector, opposed_bills[sector],
                    opposed_sponsored[sector], oppose_orgs_by_bill,
                    oppose_sources_by_bill, titles, categories,
                )
                mixed.append(row)
            else:
                champions.append(row)

        threats.sort(key=lambda row: _row_sort(row, "threat"))
        threat_cut = threats[THREAT_LIMIT:]
        threats = threats[:THREAT_LIMIT]
        mixed.sort(key=lambda row: _row_sort(row, "composite"))
        staged_sectors[sector] = {
            "champions_class": champions,
            "threats": threats,
            "mixed": mixed,
            "candidate_members": len(candidates),
            "eligible_current_members": len(rows),
            "former_members": former_members,
            "desk_unavailable_members": desk_unavailable_members,
            "crown_threat_exclusions": crown_threat_exclusions,
            "rows": rows,
            "threat_cut": threat_cut,
        }

    # CROSS-SECTOR EXCLUSIVITY (champion seat yields, Paul 2026-08-09): the
    # champions cut must see every sector's RETAINED threat board, so champion
    # retention runs as a second pass over the staged sectors.
    threat_sectors_by_bioguide = {}
    for sector in SECTORS:
        for row in staged_sectors[sector]["threats"]:
            threat_sectors_by_bioguide.setdefault(
                row["bioguide"], []
            ).append(sector)
    threat_bioguides = set(threat_sectors_by_bioguide)
    for sector in SECTORS:
        staged = staged_sectors[sector]
        cross_sector_exclusions = []
        eligible_champions = []
        for row in staged["champions_class"]:
            threat_sectors = sorted(
                threat_sectors_by_bioguide.get(row["bioguide"], ())
            )
            if threat_sectors:
                cross_sector_exclusions.append(
                    {
                        "bioguide": row["bioguide"],
                        "name": row["name"],
                        "chamber": row["chamber"],
                        "composite": row["composite"],
                        "threat_sectors": threat_sectors,
                        "routed_to": "omitted",
                    }
                )
            else:
                eligible_champions.append(row)
        retained_champions = []
        for chamber in CHAMBERS:
            retained_champions.extend(
                sorted(
                    (row for row in eligible_champions
                     if row["chamber"] == chamber),
                    key=lambda row: _row_sort(row, "composite"),
                )[:CHAMPION_LIMIT_PER_CHAMBER]
            )
        retained_champions.sort(key=lambda row: _row_sort(row, "composite"))
        boards = {
            "champions": retained_champions,
            "threats": staged["threats"],
            "mixed": staged["mixed"],
        }
        _assert_boards(sector, boards, crown_bioguides, threat_bioguides)
        sectors_payload[sector] = boards
        if standing is not None:
            standing[sector] = _sector_standing(
                staged, boards, cross_sector_exclusions, crown_tier_by_bioguide
            )
        sector_receipts[sector] = {
            "composite_components": list(
                CU_COMPONENTS if sector == "credit_union" else OTHER_COMPONENTS
            ),
            "row_counts": {
                "candidate_members": staged["candidate_members"],
                "eligible_current_members": staged["eligible_current_members"],
                "champions": len(retained_champions),
                "threats": len(staged["threats"]),
                "mixed": len(staged["mixed"]),
            },
            "sign_coverage": sign_coverage[sector],
            "former_members_excluded": len(staged["former_members"]),
            "former_bioguides": staged["former_members"],
            "desk_members_excluded": len(staged["desk_unavailable_members"]),
            "desk_unavailable_bioguides": staged["desk_unavailable_members"],
            "crown_threat_exclusions": staged["crown_threat_exclusions"],
            "cross_sector_exclusions": cross_sector_exclusions,
        }

    payload = {
        "schema": SCHEMA,
        "method_note": METHOD_NOTE,
        "sectors": sectors_payload,
        "receipt": {
            "sector_order": list(SECTORS),
            "sectors": sector_receipts,
            "ladder": "canonical > kim > prior",
            "honors_generation": honors_generation,
            "o_source": o_source,
            "rules": {
                "veto": VETO_RULE,
                "mixed": MIXED_RULE,
                "corroboration": CORROBORATION_RULE,
                "champion_exclusivity": CHAMPION_EXCLUSIVITY_RULE,
                "cross_sector": CROSS_SECTOR_RULE,
            },
            "method_note": METHOD_NOTE,
            "thresholds": {
                "support_at_or_above": SUPPORT_THRESHOLD,
                "oppose_at_or_below": OPPOSITION_THRESHOLD,
            },
            "limits": {
                "champions_per_chamber": CHAMPION_LIMIT_PER_CHAMBER,
                "threats": THREAT_LIMIT,
                "mixed": None,
            },
            "former_members_excluded": len(all_formers),
            "former_bioguides": sorted(all_formers),
            "desk_members_excluded": len(all_desk_unavailable),
            "desk_unavailable_bioguides": sorted(all_desk_unavailable),
            "identity_resolution": resolver.receipt(),
            "input_rows": {
                "signed_attention": len(signed_rows),
                "interaction_bill_members": interaction_rows,
                "member_congress_panel_117_119": panel_rows,
                "member_desk_bundle_members": desk_members,
                "bill_directions": direction_rows,
            },
            "signed_bills_without_member_roster": len(signed_bills_without_members),
        },
    }
    for sector, boards in payload["sectors"].items():
        _assert_boards(sector, boards, crown_bioguides, threat_bioguides)
    return payload


def _write_json_atomic(payload, path):
    parent = os.path.dirname(os.path.abspath(path))
    os.makedirs(parent, exist_ok=True)
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=1) + "\n"
    temporary = f"{path}.tmp.{os.getpid()}"
    try:
        with open(temporary, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
        os.replace(temporary, path)
    except BaseException:
        try:
            os.remove(temporary)
        except OSError:
            pass
        raise
    return len(body.encode("utf-8"))


def main(argv=None):
    defaults = _default_paths()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--signed-attention", default=defaults["signed_attention_path"])
    parser.add_argument("--interactions", default=defaults["interactions_path"])
    parser.add_argument("--panel", default=defaults["panel_path"])
    parser.add_argument("--ranks", default=defaults["ranks_path"])
    parser.add_argument("--member-bundle", default=defaults["member_bundle_path"])
    parser.add_argument("--titles", default=defaults["titles_path"])
    parser.add_argument("--bill-directions", default=defaults["bill_directions_path"])
    parser.add_argument(
        "--out",
        default=os.path.join(_derived_dir(), "champions_v2", "boards.json"),
    )
    args = parser.parse_args(argv)
    previous, previous_standing, baseline_note = _load_previous(args.out)
    standing = {}
    payload = build_payload(
        signed_attention_path=args.signed_attention,
        interactions_path=args.interactions,
        panel_path=args.panel,
        ranks_path=args.ranks,
        member_bundle_path=args.member_bundle,
        titles_path=args.titles,
        bill_directions_path=args.bill_directions,
        standing=standing,
    )
    now = datetime.now(timezone.utc)
    payload["generated_utc"] = now.isoformat()
    diff = champions_diff(previous, previous_standing, payload, standing)
    if baseline_note:
        diff["baseline"] += f" ({baseline_note})"
    if not diff["changed"] and previous is not None:
        # A no-change run (a rerun after a failed chain, say) keeps the last real change visible.
        prior = (previous.get("receipt") or {}).get("run_diff")
        prior = prior if isinstance(prior, dict) else {}
        carried = prior if prior.get("changed") else prior.get("last_change")
        if isinstance(carried, dict):
            diff["last_change"] = {key: value for key, value in carried.items() if key != "last_change"}
    payload["receipt"]["run_diff"] = diff
    out_dir = os.path.dirname(os.path.abspath(args.out))
    size = _write_json_atomic(payload, args.out)
    _write_json_atomic(
        {
            "schema": STANDING_SCHEMA,
            "boards_generated_utc": payload["generated_utc"],
            "sectors": standing,
        },
        os.path.join(out_dir, "standing.json"),
    )
    diff_path = os.path.join(
        out_dir, "diffs", "champions_diff_%s.json" % now.strftime("%Y%m%dT%H%M%S%fZ")
    )
    _write_json_atomic(diff, diff_path)
    counts = {
        board: sum(len(payload["sectors"][sector][board]) for sector in SECTORS)
        for board in ("champions", "threats", "mixed")
    }
    print(
        "champions v2: %d champions | %d threats | %d mixed | %d bytes -> %s"
        % (
            counts["champions"], counts["threats"], counts["mixed"], size,
            os.path.abspath(args.out),
        )
    )
    print("champions diff: %s -> %s" % (diff["summary"], diff_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
