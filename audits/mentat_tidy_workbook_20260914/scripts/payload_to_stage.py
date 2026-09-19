"""MOCK-ONLY shim: build a tidy staging SQLite from an existing export cache.

THIS SCRIPT IS NOT THE PRODUCTION PATH. In production `R/tidy_stage.R`
(Lane B) writes the staging store directly from the exporter's live frames,
between `export_phase("payload_assembled")` and `write_payload_json`, where
every column of `raw_export` is still in scope. This shim exists only so Lane A
can build a real mock workbook today from the Credit Union export cache that is
already on disk, using the SAME contract (`STAGING_CONTRACT.md`, `tidy-1`).

Consequences of reading the cache instead of the live frames, all recorded in
the workbook's `About` sheet as blank columns:

* the cached Sept-8 payload's `raw_rows` carries 34 of the contract's 56
  contribution columns, so the receipt-level FEC detail added later (transaction
  id, receipt role/type, filing form, line number, memo text, source URL, ...)
  is NULL here and present in production;
* `funding_cohorts`, `state_destinations`, `recipient_locations` and
  `accounting_basis` are not in this payload at all and are listed as absent;
* `transfer_records` (Downstream Activity) has no payload key in this cache.

Everything else is derived exactly as the contract specifies: `analysis_amount`
from `include_in_analysis` (exporter :572), `zip5` by the `R/report.R`:1885-1886
rule, FEC committee type and designation labels from the 16 + 6 maps copied from
`R/report.R`:1747-1780, and the five fact tables by SQL over the receipt rows.

The payload is streamed one array element at a time (the technique of
`app/contribution_data._payload_rows` :120-149): it is 225 MB and must never be
`json.load`ed whole. Every input is opened read-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

CACHE = Path(r"C:\Users\pgoff\Mentat\mentat\.cache\industry-report\credit_union")
STAGE_DIR = CACHE / "stage-all_cycles"

# Copied verbatim from R/report.R:1747-1780. An unknown or blank code resolves
# to NULL, never to a guess: an invented label makes an unclassified committee
# look classified.
COMMITTEE_TYPE_LABELS = {
    "C": "Communication cost", "D": "Delegate committee",
    "E": "Electioneering communication", "H": "House",
    "I": "Independent expenditor (person or group)", "N": "PAC - nonqualified",
    "O": "Independent expenditure-only (Super PAC)", "P": "Presidential",
    "Q": "PAC - qualified", "S": "Senate",
    "U": "Single-candidate independent expenditure",
    "V": "Hybrid PAC (Carey) - nonqualified", "W": "Hybrid PAC (Carey) - qualified",
    "X": "Party - nonqualified", "Y": "Party - qualified",
    "Z": "National party nonfederal account",
}

COMMITTEE_DESIGNATION_LABELS = {
    "A": "Authorized by a candidate", "B": "Lobbyist/Registrant PAC",
    "D": "Leadership PAC", "J": "Joint fundraiser",
    "P": "Principal campaign committee", "U": "Unauthorized",
}

INCUMBENT_STATUS = {"I": "Incumbent", "C": "Challenger", "O": "Open seat"}

ACCOUNTING_NOTE = ("Analysis Amount is the reported Amount for receipts included in "
                   "the industry summaries and 0 for rows excluded as memo, conduit, "
                   "duplicate, superseded, out-of-cycle or non-accepted company matches.")


# --------------------------------------------------------------------------
# Streaming payload reader
# --------------------------------------------------------------------------
def payload_rows(path, name):
    """Stream one top-level payload array without materializing the rest."""
    decoder = json.JSONDecoder()
    pattern = re.compile(r'"' + re.escape(name) + r'"\s*:\s*\[')
    with Path(path).open(encoding="utf-8-sig") as stream:
        buffer = ""
        while True:
            chunk = stream.read(1 << 16)
            if not chunk:
                return
            buffer += chunk
            match = pattern.search(buffer)
            if match:
                buffer = buffer[match.end():]
                break
            buffer = buffer[-256:]
        while True:
            buffer = buffer.lstrip(" \r\n\t,")
            if buffer.startswith("]"):
                return
            try:
                item, end = decoder.raw_decode(buffer)
            except json.JSONDecodeError:
                chunk = stream.read(1 << 16)
                if not chunk:
                    raise ValueError(f"payload array '{name}' is incomplete")
                buffer += chunk
                continue
            yield item
            buffer = buffer[end:]


def payload_metadata(path):
    with Path(path).open(encoding="utf-8-sig") as stream:
        head = stream.read(2_000_000)
    match = re.search(r'"metadata"\s*:\s*', head)
    if not match:
        raise ValueError("the payload has no metadata object")
    return json.JSONDecoder().raw_decode(head[match.end():])[0]


def file_sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


# --------------------------------------------------------------------------
# Value helpers
# --------------------------------------------------------------------------
def text(value):
    """Empty strings from R become SQL NULL (contract section 1)."""
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def flag(value):
    if value in (None, ""):
        return None
    if isinstance(value, str):
        return 1 if value.strip().lower() in ("1", "y", "yes", "true", "t") else 0
    return 1 if int(value) else 0


def number(value):
    if value in (None, ""):
        return None
    return float(value)


def integer(value):
    if value in (None, ""):
        return None
    return int(value)


def cycle_label(cycle):
    return f"{int(cycle) - 1}-{int(cycle)}"


def zip5(zipcode):
    """R/report.R:1885-1886 - the first five characters, only when all digits."""
    head = str(zipcode or "").strip()[:5]
    return head if re.fullmatch(r"[0-9]{5}", head) else None


def label(code, book):
    return book.get(str(code or "").strip().upper()) or None


def committee_url(committee_id):
    identifier = text(committee_id)
    return f"https://www.fec.gov/data/committee/{identifier}/" if identifier else None


def candidate_url(candidate_id):
    identifier = text(candidate_id)
    return f"https://www.fec.gov/data/candidate/{identifier}/" if identifier else None


def single_valued(value):
    """A ';'-joined set collapses to "Multiple"; the bridge sheet keeps the detail."""
    result = text(value)
    if result is None:
        return None
    return "Multiple" if ";" in result else result


def tokens(value):
    return [t.strip() for t in str(value or "").split(";") if t.strip()]


def snake(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")


# --------------------------------------------------------------------------
# Store construction
# --------------------------------------------------------------------------
def create(connection, table, columns):
    body = ", ".join(f'"{name}" {kind}' for name, kind in columns)
    connection.execute(f'CREATE TABLE "{table}" ({body})')


def insert_many(connection, table, columns, rows):
    fields = ", ".join(f'"{c}"' for c in columns)
    marks = ", ".join("?" * len(columns))
    connection.executemany(f'INSERT INTO "{table}" ({fields}) VALUES ({marks})', rows)


CONTRIBUTION_COLUMNS = (
    ("source_id", "TEXT"), ("transaction_id", "TEXT"),
    ("back_reference_transaction_id", "TEXT"), ("cycle_label", "TEXT"),
    ("cycle", "INTEGER"), ("source_cycle", "INTEGER"), ("cycle_alignment", "TEXT"),
    ("company", "TEXT"), ("contributor", "TEXT"), ("person_key", "TEXT"),
    ("identity_basis", "TEXT"), ("employee_tier", "TEXT"), ("employer", "TEXT"),
    ("occupation", "TEXT"), ("city", "TEXT"), ("state", "TEXT"), ("zip5", "TEXT"),
    ("zipcode", "TEXT"), ("date", "TEXT"), ("amount", "REAL"),
    ("analysis_amount", "REAL"), ("include_in_analysis", "INTEGER"),
    ("inclusion_reason", "TEXT"), ("company_match_status", "TEXT"),
    ("recipient", "TEXT"), ("committee_id", "TEXT"), ("recipient_key", "TEXT"),
    ("recipient_category", "TEXT"), ("category_source", "TEXT"), ("party", "TEXT"),
    ("party_source", "TEXT"), ("committee_type_code", "TEXT"), ("committee_type", "TEXT"),
    ("committee_designation_code", "TEXT"), ("committee_designation", "TEXT"),
    ("record_type", "TEXT"), ("source_table", "TEXT"), ("funding_direction", "TEXT"),
    ("is_memo_leg", "INTEGER"), ("is_conduit_leg", "INTEGER"),
    ("superseded_by_amendment", "INTEGER"), ("duplicate_filing_version", "INTEGER"),
    ("duplicate_memo", "INTEGER"), ("duplicate_of_sub_id", "TEXT"),
    ("duplicate_reason", "TEXT"),
)


def load_committee_labels(payload):
    """(cycle, committee_id) -> FEC master type and designation codes."""
    labels = {}
    for row in payload_rows(payload, "committee_map"):
        labels[(row.get("cycle"), text(row.get("committee_id")))] = (
            text(row.get("master_committee_type")), text(row.get("master_designation")))
    return labels


def write_contributions(connection, payload, labels):
    create(connection, "contributions", CONTRIBUTION_COLUMNS)
    names = [name for name, _ in CONTRIBUTION_COLUMNS]
    batch, total = [], 0
    for row in payload_rows(payload, "raw_rows"):
        cycle = integer(row.get("cycle"))
        committee_id = text(row.get("committee_id"))
        type_code, designation_code = labels.get((cycle, committee_id), (None, None))
        included = 1 if str(row.get("include_in_analysis", "")).strip() == "Yes" else 0
        amount = number(row.get("amount")) or 0.0
        category = text(row.get("recipient_category"))
        values = {
            "source_id": text(row.get("source_id")),
            "transaction_id": text(row.get("transaction_id")),
            "back_reference_transaction_id": text(row.get("back_reference_transaction_id")),
            "cycle_label": text(row.get("cycle_label")) or cycle_label(cycle),
            "cycle": cycle, "source_cycle": integer(row.get("source_cycle")),
            "cycle_alignment": text(row.get("cycle_alignment")),
            "company": text(row.get("company")), "contributor": text(row.get("contributor")),
            "person_key": text(row.get("person_key")),
            "identity_basis": text(row.get("identity_basis")),
            "employee_tier": text(row.get("employee_tier")),
            "employer": text(row.get("employer")),
            "occupation": text(row.get("occupation")), "city": text(row.get("city")),
            "state": text(row.get("state")), "zip5": zip5(row.get("zipcode")),
            "zipcode": text(row.get("zipcode")), "date": text(row.get("date")),
            "amount": amount, "analysis_amount": amount if included else 0.0,
            "include_in_analysis": included,
            "inclusion_reason": text(row.get("inclusion_reason")),
            "company_match_status": text(row.get("company_match_status")),
            "recipient": text(row.get("recipient")), "committee_id": committee_id,
            "recipient_key": text(row.get("recipient_key")), "recipient_category": category,
            "category_source": text(row.get("category_source")),
            "party": text(row.get("party")), "party_source": text(row.get("party_source")),
            "committee_type_code": type_code,
            "committee_type": label(type_code, COMMITTEE_TYPE_LABELS),
            "committee_designation_code": designation_code,
            "committee_designation": label(designation_code, COMMITTEE_DESIGNATION_LABELS),
            "record_type": text(row.get("record_type")),
            "source_table": text(row.get("source_table")),
            # Exporter rule, export_crypto_spending_data.R :525.
            "funding_direction": ("Into company PAC" if category == "Company PAC"
                                  else "To named recipient"),
            "is_memo_leg": flag(row.get("is_memo_leg")),
            "is_conduit_leg": flag(row.get("is_conduit_leg")),
            "superseded_by_amendment": flag(row.get("superseded_by_amendment")),
            "duplicate_filing_version": flag(row.get("duplicate_filing_version")),
            "duplicate_memo": flag(row.get("duplicate_memo")),
            "duplicate_of_sub_id": text(row.get("duplicate_of_sub_id")),
            "duplicate_reason": text(row.get("duplicate_reason")),
        }
        batch.append([values[name] for name in names])
        total += 1
        if len(batch) >= 5000:
            insert_many(connection, "contributions", names, batch)
            batch = []
    if batch:
        insert_many(connection, "contributions", names, batch)
    connection.commit()
    return total


FACT_SQL = {
    "giving_facts": """
        CREATE TABLE giving_facts AS
        SELECT cycle_label, cycle, company, employee_tier, recipient_category, party,
               ROUND(SUM(analysis_amount), 2) AS giving,
               COUNT(*) AS gift_count,
               COUNT(DISTINCT person_key) AS distinct_contributors,
               COUNT(DISTINCT committee_id) AS distinct_recipients
        FROM contributions WHERE include_in_analysis = 1
        GROUP BY cycle_label, cycle, company, employee_tier, recipient_category, party""",
    "location_facts": """
        CREATE TABLE location_facts AS
        SELECT cycle_label, cycle, company, state, city, zip5,
               ROUND(SUM(analysis_amount), 2) AS giving,
               COUNT(*) AS gift_count,
               COUNT(DISTINCT person_key) AS distinct_contributors
        FROM contributions WHERE include_in_analysis = 1
        GROUP BY cycle_label, cycle, company, state, city, zip5""",
}

MODAL_ATTRIBUTES = ("contributor", "employee_tier", "identity_basis", "city", "state",
                    "zip5", "employer", "occupation")


def write_facts(connection):
    for statement in FACT_SQL.values():
        connection.execute(statement)
    # Modal attribute per person x cycle x company: most frequent spelling, ties
    # broken alphabetically, exactly as the contract's contributor_facts says.
    for attribute in MODAL_ATTRIBUTES:
        connection.execute(f"""
            CREATE TEMP TABLE modal_{attribute} AS
            SELECT cycle_label, company, person_key, "{attribute}" AS value FROM (
                SELECT cycle_label, company, person_key, "{attribute}",
                       ROW_NUMBER() OVER (PARTITION BY cycle_label, company, person_key
                                          ORDER BY COUNT(*) DESC, "{attribute}") AS rank
                FROM contributions
                WHERE include_in_analysis = 1 AND person_key IS NOT NULL
                GROUP BY cycle_label, company, person_key, "{attribute}") WHERE rank = 1""")
    joins = " ".join(
        f'LEFT JOIN modal_{a} AS m_{a} ON m_{a}.cycle_label = g.cycle_label '
        f'AND m_{a}.company = g.company AND m_{a}.person_key = g.person_key'
        for a in MODAL_ATTRIBUTES)
    selects = ", ".join(f'm_{a}.value AS "{a}"' for a in MODAL_ATTRIBUTES)
    connection.execute(f"""
        CREATE TABLE contributor_facts AS
        SELECT g.cycle_label, g.cycle, g.company, g.person_key, g.party, {selects},
               (SELECT COUNT(DISTINCT COALESCE(c.city,'') || '|' || COALESCE(c.state,'')
                       || '|' || COALESCE(c.zip5,''))
                FROM contributions c
                WHERE c.include_in_analysis = 1 AND c.person_key = g.person_key
                  AND c.cycle_label = g.cycle_label AND c.company = g.company)
               AS distinct_addresses,
               g.giving, g.gift_count
        FROM (SELECT cycle_label, cycle, company, person_key, party,
                     ROUND(SUM(analysis_amount), 2) AS giving, COUNT(*) AS gift_count
              FROM contributions
              WHERE include_in_analysis = 1 AND person_key IS NOT NULL
              GROUP BY cycle_label, cycle, company, person_key, party) AS g {joins}""")
    connection.commit()


def write_recipient_facts(connection):
    connection.execute("""
        CREATE TABLE recipient_facts AS
        SELECT f.cycle_label, f.cycle, f.company, f.committee_id, f.employee_tier,
               f.recipient, cm.recipient_category, f.category_source, f.party,
               f.party_source, cm.committee_type_code, cm.committee_type,
               cm.committee_designation_code, cm.committee_designation,
               CASE WHEN cm.sponsor_count = 1 THEN
                    (SELECT s.candidate_id FROM committee_sponsors s
                     WHERE s.committee_id = f.committee_id
                       AND s.cycle_label = f.cycle_label) END AS sponsor_candidate_id,
               NULL AS sponsor_candidate, NULL AS sponsor_office, NULL AS sponsor_state,
               NULL AS sponsor_district, COALESCE(cm.sponsor_count, 0) AS sponsor_count,
               cm.connected_organization, cm.committee_relationship, cm.ownership_status,
               f.giving, f.gift_count, f.distinct_contributors,
               f.first_gift_date, f.last_gift_date, f.fec_committee_url
        FROM (SELECT cycle_label, cycle, company, committee_id, employee_tier,
                     MAX(recipient) AS recipient, MAX(category_source) AS category_source,
                     MAX(party) AS party, MAX(party_source) AS party_source,
                     ROUND(SUM(analysis_amount), 2) AS giving, COUNT(*) AS gift_count,
                     COUNT(DISTINCT person_key) AS distinct_contributors,
                     MIN(date) AS first_gift_date, MAX(date) AS last_gift_date,
                     'https://www.fec.gov/data/committee/' || committee_id || '/'
                     AS fec_committee_url
              FROM contributions WHERE include_in_analysis = 1
              GROUP BY cycle_label, cycle, company, committee_id, employee_tier) AS f
        LEFT JOIN committees cm ON cm.committee_id = f.committee_id
                               AND cm.cycle_label = f.cycle_label""")
    connection.execute("""
        UPDATE recipient_facts SET
            sponsor_candidate = (SELECT c.candidate FROM candidates c
                                 WHERE c.candidate_id = recipient_facts.sponsor_candidate_id),
            sponsor_office = (SELECT c.office FROM candidates c
                              WHERE c.candidate_id = recipient_facts.sponsor_candidate_id),
            sponsor_state = (SELECT c.state FROM candidates c
                             WHERE c.candidate_id = recipient_facts.sponsor_candidate_id),
            sponsor_district = (SELECT c.district FROM candidates c
                                WHERE c.candidate_id = recipient_facts.sponsor_candidate_id)
        WHERE sponsor_candidate_id IS NOT NULL""")
    connection.commit()


def write_committees(connection, payload):
    create(connection, "committees", (
        ("committee_id", "TEXT"), ("cycle_label", "TEXT"), ("cycle", "INTEGER"),
        ("committee_name", "TEXT"), ("committee_type_code", "TEXT"),
        ("committee_type", "TEXT"), ("committee_designation_code", "TEXT"),
        ("committee_designation", "TEXT"), ("party", "TEXT"),
        ("party_affiliation", "TEXT"), ("committee_state", "TEXT"),
        ("recipient_category", "TEXT"), ("category_source", "TEXT"),
        ("party_source", "TEXT"), ("connected_organization", "TEXT"),
        ("ownership_status", "TEXT"), ("committee_relationship", "TEXT"),
        ("mapping_source", "TEXT"), ("sponsor_count", "INTEGER"),
        ("top_downstream_candidate_id", "TEXT"), ("top_downstream_candidate", "TEXT"),
        ("top_downstream_activity", "REAL"), ("fec_committee_url", "TEXT")))
    universe = {(row[0], row[1]) for row in connection.execute(
        "SELECT committee_id, cycle_label FROM contributions "
        "WHERE committee_id IS NOT NULL GROUP BY 1, 2")}
    seen, rows = set(), []
    for row in payload_rows(payload, "committee_map"):
        cycle = integer(row.get("cycle"))
        committee_id = text(row.get("committee_id"))
        key = (committee_id, cycle_label(cycle) if cycle else None)
        if key not in universe or key in seen:
            continue
        seen.add(key)
        type_code = text(row.get("master_committee_type"))
        designation_code = text(row.get("master_designation"))
        rows.append([committee_id, key[1], cycle, text(row.get("master_committee_name"))
                     or text(row.get("committee_name")), type_code,
                     label(type_code, COMMITTEE_TYPE_LABELS), designation_code,
                     label(designation_code, COMMITTEE_DESIGNATION_LABELS),
                     None, None, None, text(row.get("recipient_category")), None, None,
                     text(row.get("connected_organization")),
                     text(row.get("ownership_status")),
                     single_valued(row.get("relationship")),
                     single_valued(row.get("mapping_source")), 0,
                     text(row.get("top_downstream_candidate_id")),
                     text(row.get("top_downstream_person")),
                     number(row.get("preliminary_top_downstream_amount")),
                     committee_url(committee_id)])
    # Committees seen in the receipts but absent from committee_map still need a row.
    for committee_id, label_text, cycle in connection.execute(
            "SELECT committee_id, cycle_label, cycle FROM contributions "
            "WHERE committee_id IS NOT NULL GROUP BY 1, 2, 3"):
        if (committee_id, label_text) in seen:
            continue
        seen.add((committee_id, label_text))
        rows.append([committee_id, label_text, cycle, None, None, None, None, None,
                     None, None, None, None, None, None, None, None, None, None, 0,
                     None, None, None, committee_url(committee_id)])
    insert_many(connection, "committees",
                [c[1] for c in connection.execute('PRAGMA table_info("committees")')],
                rows)
    connection.execute("""
        UPDATE committees SET
            party = (SELECT MAX(party) FROM contributions c
                     WHERE c.committee_id = committees.committee_id
                       AND c.cycle_label = committees.cycle_label),
            category_source = (SELECT MAX(category_source) FROM contributions c
                               WHERE c.committee_id = committees.committee_id
                                 AND c.cycle_label = committees.cycle_label),
            party_source = (SELECT MAX(party_source) FROM contributions c
                            WHERE c.committee_id = committees.committee_id
                              AND c.cycle_label = committees.cycle_label),
            recipient_category = COALESCE(recipient_category,
                (SELECT MAX(recipient_category) FROM contributions c
                 WHERE c.committee_id = committees.committee_id
                   AND c.cycle_label = committees.cycle_label)),
            committee_name = COALESCE(committee_name,
                (SELECT MAX(recipient) FROM contributions c
                 WHERE c.committee_id = committees.committee_id
                   AND c.cycle_label = committees.cycle_label)),
            committee_type_code = COALESCE(committee_type_code,
                (SELECT MAX(committee_type_code) FROM contributions c
                 WHERE c.committee_id = committees.committee_id
                   AND c.cycle_label = committees.cycle_label)),
            committee_designation_code = COALESCE(committee_designation_code,
                (SELECT MAX(committee_designation_code) FROM contributions c
                 WHERE c.committee_id = committees.committee_id
                   AND c.cycle_label = committees.cycle_label))""")
    # Re-label after the COALESCE fallbacks above filled codes from the receipts.
    connection.executemany(
        "UPDATE committees SET committee_type = ?, committee_designation = ? "
        "WHERE committee_id = ? AND cycle_label IS ?",
        [(label(type_code, COMMITTEE_TYPE_LABELS),
          label(designation_code, COMMITTEE_DESIGNATION_LABELS), committee_id, label_text)
         for committee_id, label_text, type_code, designation_code in connection.execute(
            "SELECT committee_id, cycle_label, committee_type_code, "
            "committee_designation_code FROM committees").fetchall()])
    connection.commit()
    return len(rows)


def write_sponsors(connection, payload):
    create(connection, "committee_sponsors", (
        ("committee_id", "TEXT"), ("candidate_id", "TEXT"), ("cycle_label", "TEXT"),
        ("cycle", "INTEGER"), ("relationship", "TEXT"), ("link_source", "TEXT"),
        ("candidate", "TEXT"), ("source_url", "TEXT")))
    universe = {(row[0], row[1]) for row in connection.execute(
        "SELECT committee_id, cycle_label FROM committees")}
    seen, rows = set(), []
    for row in payload_rows(payload, "candidate_committee_links"):
        cycle = integer(row.get("cycle"))
        committee_id = text(row.get("committee_id"))
        candidate_id = text(row.get("candidate_id"))
        label_text = cycle_label(cycle) if cycle else None
        key = (committee_id, candidate_id, label_text, "FEC ccl")
        if (committee_id, label_text) not in universe or key in seen:
            continue
        seen.add(key)
        rows.append([committee_id, candidate_id, label_text, cycle,
                     text(row.get("relationship")), "FEC ccl", None,
                     text(row.get("source_url"))])
    insert_many(connection, "committee_sponsors",
                ["committee_id", "candidate_id", "cycle_label", "cycle", "relationship",
                 "link_source", "candidate", "source_url"], rows)
    connection.execute("""
        UPDATE committees SET sponsor_count = (
            SELECT COUNT(*) FROM committee_sponsors s
            WHERE s.committee_id = committees.committee_id
              AND s.cycle_label = committees.cycle_label)""")
    connection.commit()
    return len(rows)


def write_candidates(connection, payload, referenced):
    create(connection, "candidates", (
        ("candidate_id", "TEXT"), ("candidate", "TEXT"), ("party", "TEXT"),
        ("party_affiliation", "TEXT"), ("office_code", "TEXT"), ("office", "TEXT"),
        ("state", "TEXT"), ("district", "TEXT"), ("incumbent_status", "TEXT"),
        ("principal_committee_id", "TEXT"), ("fec_candidate_url", "TEXT"),
        ("source_url", "TEXT")))
    best = {}
    for row in payload_rows(payload, "candidate_master"):
        candidate_id = text(row.get("candidate_id"))
        if candidate_id not in referenced:
            continue
        cycle = integer(row.get("cycle")) or 0
        if candidate_id in best and best[candidate_id][0] >= cycle:
            continue
        best[candidate_id] = (cycle, [
            candidate_id, text(row.get("candidate_name")), text(row.get("candidate_party")),
            text(row.get("party_affiliation")), text(row.get("office")),
            text(row.get("office_label")), text(row.get("office_state")),
            text(row.get("district")),
            INCUMBENT_STATUS.get(str(row.get("incumbent_challenger") or "").strip().upper()),
            text(row.get("principal_committee_id")), candidate_url(candidate_id),
            text(row.get("source_url"))])
    insert_many(connection, "candidates",
                [c[1] for c in connection.execute('PRAGMA table_info("candidates")')],
                [value for _, value in sorted(best.values(), key=lambda p: p[1][0])])
    connection.execute("""
        UPDATE committee_sponsors SET candidate = (
            SELECT c.candidate FROM candidates c
            WHERE c.candidate_id = committee_sponsors.candidate_id)""")
    connection.commit()
    return len(best)


def write_downstream(connection, payload):
    columns = (("cycle_label", "TEXT"), ("cycle", "INTEGER"), ("source_committee", "TEXT"),
               ("source_committee_id", "TEXT"), ("source_recipient_category", "TEXT"),
               ("candidate", "TEXT"), ("candidate_id", "TEXT"),
               ("candidate_party", "TEXT"), ("office", "TEXT"), ("state", "TEXT"),
               ("district", "TEXT"), ("activity_type", "TEXT"),
               ("support_oppose", "TEXT"), ("transaction_type", "TEXT"),
               ("first_activity_date", "TEXT"), ("last_activity_date", "TEXT"),
               ("source_rows", "INTEGER"), ("included_rows", "INTEGER"),
               ("excluded_rows", "INTEGER"), ("superseded_rows", "INTEGER"),
               ("memo_rows", "INTEGER"), ("duplicate_rows", "INTEGER"),
               ("reported_amount", "REAL"), ("excluded_amount", "REAL"),
               ("net_included_amount", "REAL"), ("fec_committee_url", "TEXT"),
               ("fec_candidate_url", "TEXT"), ("source_url", "TEXT"))
    create(connection, "downstream_activity", columns)
    names = [name for name, _ in columns]
    batch, total, candidates = [], 0, set()
    for row in payload_rows(payload, "downstream_activity"):
        cycle = integer(row.get("cycle"))
        candidate_id = text(row.get("candidate_id"))
        candidates.add(candidate_id)
        batch.append([
            cycle_label(cycle) if cycle else None, cycle,
            text(row.get("source_committee")), text(row.get("source_committee_id")),
            text(row.get("source_recipient_category")), text(row.get("candidate_name")),
            candidate_id, text(row.get("candidate_party")), text(row.get("office_label")),
            text(row.get("office_state")), text(row.get("district")),
            text(row.get("activity_type")), text(row.get("support_oppose")),
            text(row.get("transaction_type")), text(row.get("first_activity_date")),
            text(row.get("last_activity_date")), integer(row.get("source_rows")),
            integer(row.get("included_rows")), integer(row.get("excluded_rows")),
            integer(row.get("superseded_rows")), integer(row.get("memo_rows")),
            integer(row.get("exact_duplicate_rows")), number(row.get("reported_amount")),
            number(row.get("excluded_amount")),
            number(row.get("preliminary_included_amount")),
            committee_url(row.get("source_committee_id")), candidate_url(candidate_id),
            text(row.get("source_url"))])
        total += 1
        if len(batch) >= 5000:
            insert_many(connection, "downstream_activity", names, batch)
            batch = []
    if batch:
        insert_many(connection, "downstream_activity", names, batch)
    connection.commit()
    return total, candidates


def write_bridge(connection, payload):
    """Company-view rows only; the ';'-joined token sets become boolean flags."""
    rows, vocabulary = [], []
    for row in payload_rows(payload, "beneficiary_bridge"):
        if str(row.get("view") or "").strip() != "Company":
            continue
        marks = tokens(row.get("activity_relationships")) + tokens(row.get("directions"))
        for token in marks:
            if token not in vocabulary:
                vocabulary.append(token)
        rows.append((row, set(marks)))
    vocabulary.sort()
    flags = [(f"has_{snake(token)}", token) for token in vocabulary]
    columns = (("bridge_key", "TEXT"), ("cycle_label", "TEXT"), ("cycle", "INTEGER"),
               ("company", "TEXT"), ("source_committee", "TEXT"),
               ("source_committee_id", "TEXT"), ("source_recipient_category", "TEXT"),
               ("candidate", "TEXT"), ("candidate_id", "TEXT"),
               ("candidate_party", "TEXT"), ("office", "TEXT"), ("state", "TEXT"),
               ("district", "TEXT"), ("transaction_count", "INTEGER"),
               ("first_activity_date", "TEXT"), ("last_activity_date", "TEXT"),
               ("downstream_activity", "REAL"), ("associated_funding", "REAL")
               ) + tuple((name, "INTEGER") for name, _ in flags)
    create(connection, "beneficiary_bridge", columns)
    payloads, candidates = [], set()
    for row, marks in rows:
        cycle = integer(row.get("cycle"))
        candidate_id = text(row.get("candidate_id"))
        candidates.add(candidate_id)
        payloads.append([
            text(row.get("bridge_key")), cycle_label(cycle) if cycle else None, cycle,
            text(row.get("company")), text(row.get("source_committee")),
            text(row.get("source_committee_id")),
            text(row.get("source_recipient_category")), text(row.get("candidate_name")),
            candidate_id, text(row.get("candidate_party")), text(row.get("office_label")),
            text(row.get("office_state")), text(row.get("district")),
            integer(row.get("transaction_count")), text(row.get("first_activity_date")),
            text(row.get("last_activity_date")),
            number(row.get("preliminary_downstream_amount")),
            number(row.get("preliminary_crypto_funding")),
        ] + [1 if token in marks else 0 for _, token in flags])
    insert_many(connection, "beneficiary_bridge", [name for name, _ in columns], payloads)
    connection.commit()
    return len(payloads), [token for _, token in flags], candidates


CARRY_THROUGH = {
    "transfer_paths": (
        (("cycle_label", "TEXT"), ("cycle", "INTEGER"), ("funded_committee", "TEXT"),
         ("source_committee", "TEXT"), ("destination_committee", "TEXT"),
         ("reported_net_transfer", "REAL"), ("depth", "INTEGER"),
         ("representative_path", "TEXT"), ("traversal_status", "TEXT")),
        lambda row, c: [cycle_label(c) if c else None, c, text(row.get("root")),
                        text(row.get("source")), text(row.get("destination")),
                        number(row.get("amount")), integer(row.get("depth")),
                        text(row.get("path")), text(row.get("status"))]),
    "allocation_estimates": (
        (("cycle_label", "TEXT"), ("cycle", "INTEGER"), ("funded_committee", "TEXT"),
         ("candidate_id", "TEXT"), ("candidate", "TEXT"), ("direction", "TEXT"),
         ("conditional_estimate", "REAL")),
        lambda row, c: [cycle_label(c) if c else None, c, text(row.get("root")),
                        text(row.get("candidate_id")), text(row.get("candidate_name")),
                        text(row.get("direction")),
                        number(row.get("estimated_amount"))]),
    "allocation_coverage": (
        (("cycle_label", "TEXT"), ("cycle", "INTEGER"), ("funded_committee", "TEXT"),
         ("net_input_funding", "REAL"), ("nonnegative_model_funding", "REAL"),
         ("estimated_candidate_activity", "REAL"), ("unresolved", "REAL"),
         ("negative_net_funding", "REAL"), ("unresolved_reasons", "TEXT")),
        lambda row, c: [cycle_label(c) if c else None, c, text(row.get("root")),
                        number(row.get("input_net_funding")),
                        number(row.get("model_funding")),
                        number(row.get("estimated_candidate_activity")),
                        number(row.get("unresolved")),
                        number(row.get("negative_net_funding_excluded")),
                        json.dumps(row.get("unresolved_reasons"), sort_keys=True)
                        if row.get("unresolved_reasons") else None]),
    "source_freshness": (
        (("cycle_label", "TEXT"), ("cycle", "INTEGER"), ("fec_dataset", "TEXT"),
         ("checked_at", "TEXT"), ("server_last_modified", "TEXT"), ("sha256", "TEXT"),
         ("source_url", "TEXT")),
        lambda row, c: [cycle_label(c) if c else None, c, text(row.get("source")),
                        text(row.get("checked_at")), text(row.get("last_modified")),
                        text(row.get("sha256")), text(row.get("url"))]),
    "classification_review": (
        (("cycle_label", "TEXT"), ("cycle", "INTEGER"), ("committee_id", "TEXT"),
         ("committee", "TEXT"), ("official_type", "TEXT"),
         ("reporting_category", "TEXT"), ("included_funding", "REAL")),
        lambda row, c: [cycle_label(c) if c else None, c, text(row.get("committee_id")),
                        text(row.get("committee_name")), text(row.get("official_type")),
                        text(row.get("reporting_category")),
                        number(row.get("included_funding"))]),
}


def write_carry_throughs(connection, payload):
    counts = {}
    for table, (columns, build) in CARRY_THROUGH.items():
        create(connection, table, columns)
        rows = [build(row, integer(row.get("cycle"))) for row in payload_rows(payload, table)]
        insert_many(connection, table, [name for name, _ in columns], rows)
        counts[table] = len(rows)
    connection.commit()
    return counts


def write_quality(connection, payload):
    create(connection, "data_quality", (
        ("check_id", "TEXT"), ("source", "TEXT"), ("severity", "TEXT"),
        ("passed", "INTEGER"), ("detail", "TEXT"), ("metric", "TEXT")))
    rows = []
    for row in payload_rows(payload, "quality_checks"):
        metric = row.get("metric")
        rows.append([text(row.get("id")), "r_guard", text(row.get("severity")),
                     flag(row.get("passed")), text(row.get("detail")),
                     None if metric in (None, "", {}, [])
                     else (json.dumps(metric, sort_keys=True)
                           if isinstance(metric, (dict, list)) else str(metric))])
    insert_many(connection, "data_quality",
                ["check_id", "source", "severity", "passed", "detail", "metric"], rows)
    connection.commit()
    return len(rows)


def write_metadata(connection, metadata, manifest, database, blank):
    create(connection, "metadata", (("key", "TEXT"), ("value", "TEXT")))
    cycles = sorted({int(row[0]) for row in connection.execute(
        "SELECT DISTINCT cycle FROM contributions WHERE cycle IS NOT NULL")})
    rows = {
        "schema_version": "tidy-1",
        "industry": metadata.get("industry") or "Credit Union",
        "industry_slug": "credit_union",
        "cycle_label": manifest.get("cycle_label") or "",
        "supported_cycles": json.dumps(cycles),
        "cycle_labels": json.dumps([cycle_label(c) for c in cycles]),
        "database_path": str(database) if database else metadata.get("database_path"),
        "database_sha256": manifest.get("database_sha256"),
        "generated_at": manifest.get("generated_at") or metadata.get("generated_at"),
        "exporter_version": "cache mock via payload_to_stage.py (not the R writer)",
        "expected_cycle_totals": json.dumps(metadata.get("expected_cycle_totals") or {}),
        "accounting_note": ACCOUNTING_NOTE,
        "blank_columns": json.dumps(blank),
    }
    insert_many(connection, "metadata", ["key", "value"],
                [[k, None if v is None else str(v)] for k, v in rows.items()])
    connection.commit()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--payload", default=str(CACHE / "industry_data-f9e956354525acb0.json"))
    parser.add_argument("--manifest", default=str(CACHE / "manifest-f9e956354525acb0.json"))
    parser.add_argument("--out", default=str(Path(__file__).parent / "stage" / "tidy-cu.sqlite"))
    parser.add_argument("--database",
                        default=r"C:\Users\pgoff\Mentat\mentat\.cache"
                                r"\repair-20260908-databases\credit_union.db")
    arguments = parser.parse_args(argv if argv is not None else sys.argv[1:])

    payload = Path(arguments.payload)
    manifest = json.loads(Path(arguments.manifest).read_text(encoding="utf-8-sig"))
    metadata = payload_metadata(payload)
    out = Path(arguments.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pending = out.with_name(out.name + f".pending-{os.getpid()}")
    pending.unlink(missing_ok=True)

    connection = sqlite3.connect(pending)
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    try:
        labels = load_committee_labels(payload)
        print(f"committee_map labels: {len(labels):,}")
        print(f"contributions: {write_contributions(connection, payload, labels):,}")
        print(f"committees: {write_committees(connection, payload):,}")
        print(f"committee_sponsors: {write_sponsors(connection, payload):,}")
        downstream, downstream_candidates = write_downstream(connection, payload)
        print(f"downstream_activity: {downstream:,}")
        bridge, vocabulary, bridge_candidates = write_bridge(connection, payload)
        print(f"beneficiary_bridge: {bridge:,} rows, flags {vocabulary}")
        referenced = {row[0] for row in connection.execute(
            "SELECT DISTINCT candidate_id FROM committee_sponsors")}
        referenced |= {row[0] for row in connection.execute(
            "SELECT DISTINCT top_downstream_candidate_id FROM committees")}
        referenced |= downstream_candidates | bridge_candidates
        referenced.discard(None)
        print(f"candidates: {write_candidates(connection, payload, referenced):,}")
        write_facts(connection)
        write_recipient_facts(connection)
        for table in ("giving_facts", "recipient_facts", "contributor_facts",
                      "location_facts"):
            count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"{table}: {count:,}")
        print(f"carry-throughs: {write_carry_throughs(connection, payload)}")
        print(f"data_quality: {write_quality(connection, payload):,}")
        blank = ["Contributions / " + h for h in (
            "Transaction ID", "Back Reference Transaction ID", "Company Match Reason",
            "Matched Alias", "Funding Source Type", "Receipt Role", "Receipt Type",
            "Filing Form", "Line Number", "Memo Text", "Recipient State",
            "Represented State", "Source URL")]
        write_metadata(connection, metadata, manifest, arguments.database, blank)
        connection.execute("VACUUM")
        connection.commit()
    finally:
        connection.close()
    os.replace(pending, out)
    print(f"Wrote {out} ({out.stat().st_size:,} bytes, "
          f"sha256 {file_sha256(out)[:16]}...)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
