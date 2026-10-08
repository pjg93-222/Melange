#!/usr/bin/env python3
"""Extract source-native employment mentions from LDA covered-position claims.

This is deliberately a candidate-mention layer, not a canonical employment
layer. It records exact text spans for role/title, office/employer, and date
range mentions without assigning them to a canonical person, organization,
episode, title, or temporal interval.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import re
from time import perf_counter
from typing import Any, Iterable


DEFAULT_INPUT = Path(
    "audits/staffer_network/lda_employment_materialization_20260831/"
    "lda_employment_claims.ndjson.gz"
)
DEFAULT_OUTPUT_ROOT = Path(
    "audits/staffer_network/lda_employment_claim_normalization_20260831"
)

OUTPUT_NAME = "lda_employment_claim_mentions.ndjson.gz"
RECEIPT_NAME = "lda_employment_claim_normalization_receipt.json"


# The title lexicon is intentionally finite. Each match remains an exact raw
# mention; pattern IDs describe the acquisition rule, not a normalized title.
ROLE_PATTERNS: list[tuple[str, str, str, bool, bool]] = [
    ("ROLE_DEPUTY_CHIEF_OF_STAFF", r"deputy\s+chief\s+of\s+staff", "HIGH", False, False),
    ("ROLE_ASSISTANT_CHIEF_OF_STAFF", r"assistant\s+chief\s+of\s+staff", "HIGH", False, False),
    ("ROLE_CHIEF_OF_STAFF", r"chief\s+of\s+staff", "HIGH", False, False),
    ("ROLE_DEPUTY_LEGISLATIVE_DIRECTOR", r"deputy\s+legislative\s+director", "HIGH", False, False),
    ("ROLE_LEGISLATIVE_DIRECTOR_COUNSEL", r"legislative\s+director\s+(?:and|&)\s+counsel", "HIGH", False, False),
    ("ROLE_LEGISLATIVE_DIRECTOR", r"legislative\s+director", "HIGH", False, False),
    ("ROLE_SENIOR_LEGISLATIVE_ASSISTANT", r"senior\s+legislative\s+assistant", "HIGH", False, False),
    ("ROLE_MILITARY_LEGISLATIVE_ASSISTANT", r"military\s+legislative\s+assistant", "HIGH", False, False),
    ("ROLE_LEGISLATIVE_ASSISTANT", r"legislative\s+assistant", "HIGH", False, False),
    ("ROLE_LEGISLATIVE_CORRESPONDENT", r"legislative\s+correspondent", "HIGH", False, False),
    ("ROLE_LEGISLATIVE_COUNSEL", r"legislative\s+counsel", "HIGH", False, False),
    ("ROLE_LEGISLATIVE_AIDE", r"legislative\s+aide", "HIGH", False, False),
    ("ROLE_LEGISLATIVE_FELLOW", r"legislative\s+fellow", "HIGH", False, False),
    ("ROLE_LEGISLATIVE_INTERN", r"legislative\s+intern", "HIGH", False, False),
    ("ROLE_SENIOR_PROFESSIONAL_STAFF_MEMBER", r"senior\s+professional\s+staff\s+member", "HIGH", False, False),
    ("ROLE_PROFESSIONAL_STAFF_MEMBER", r"professional\s+staff\s+member", "HIGH", False, False),
    ("ROLE_SENIOR_PROFESSIONAL_STAFF", r"senior\s+professional\s+staff", "HIGH", False, False),
    ("ROLE_PROFESSIONAL_STAFF", r"professional\s+staff", "HIGH", False, False),
    ("ROLE_SUBCOMMITTEE_STAFF_DIRECTOR", r"subcommittee\s+staff\s+director", "HIGH", False, False),
    ("ROLE_COMMITTEE_STAFF_DIRECTOR", r"committee\s+staff\s+director", "HIGH", False, False),
    ("ROLE_MINORITY_STAFF_DIRECTOR", r"minority\s+staff\s+director", "HIGH", False, False),
    ("ROLE_MAJORITY_STAFF_DIRECTOR", r"majority\s+staff\s+director", "HIGH", False, False),
    ("ROLE_DEPUTY_STAFF_DIRECTOR", r"deputy\s+staff\s+director", "HIGH", False, False),
    ("ROLE_STAFF_DIRECTOR", r"staff\s+director", "HIGH", False, False),
    ("ROLE_STAFF_ASSISTANT", r"staff\s+assistant", "HIGH", False, False),
    ("ROLE_SPECIAL_ASSISTANT_TO_PRESIDENT", r"special\s+assistant\s+to\s+the\s+president", "HIGH", False, False),
    ("ROLE_SPECIAL_ASSISTANT", r"special\s+assistant", "HIGH", False, False),
    ("ROLE_EXECUTIVE_ASSISTANT", r"executive\s+assistant", "HIGH", False, False),
    ("ROLE_RESEARCH_ASSISTANT", r"research\s+assistant", "HIGH", False, False),
    ("ROLE_ADMINISTRATIVE_ASSISTANT", r"administrative\s+assistant", "HIGH", False, False),
    ("ROLE_NATIONAL_SECURITY_ADVISOR", r"national\s+security\s+advis(?:or|er)", "HIGH", False, False),
    ("ROLE_HEALTH_POLICY_ADVISOR", r"health\s+policy\s+advis(?:or|er)", "HIGH", False, False),
    ("ROLE_DEFENSE_POLICY_ADVISOR", r"defen[sc]e\s+policy\s+advis(?:or|er)", "HIGH", False, False),
    ("ROLE_SENIOR_POLICY_ADVISOR", r"senior\s+policy\s+advis(?:or|er)", "HIGH", False, False),
    ("ROLE_POLICY_ADVISOR", r"policy\s+advis(?:or|er)", "HIGH", False, False),
    ("ROLE_POLICY_DIRECTOR", r"policy\s+director", "HIGH", False, False),
    ("ROLE_POLICY_ANALYST", r"policy\s+analyst", "HIGH", False, False),
    ("ROLE_POLICY_ASSISTANT", r"policy\s+assistant", "HIGH", False, False),
    ("ROLE_RESEARCH_ANALYST", r"research\s+analyst", "HIGH", False, False),
    ("ROLE_DEPUTY_GENERAL_COUNSEL", r"deputy\s+general\s+counsel", "HIGH", False, False),
    ("ROLE_GENERAL_COUNSEL", r"general\s+counsel", "HIGH", False, False),
    ("ROLE_DEPUTY_CHIEF_COUNSEL", r"deputy\s+chief\s+counsel", "HIGH", False, False),
    ("ROLE_CHIEF_COUNSEL", r"chief\s+counsel", "HIGH", False, False),
    ("ROLE_SENIOR_COUNSEL", r"senior\s+counsel", "HIGH", False, False),
    ("ROLE_TAX_COUNSEL", r"tax\s+counsel", "HIGH", False, False),
    ("ROLE_LEGAL_COUNSEL", r"legal\s+counsel", "HIGH", False, False),
    ("ROLE_COUNSEL", r"counsel", "MEDIUM", False, False),
    ("ROLE_LAW_CLERK", r"law\s+clerk", "HIGH", False, False),
    ("ROLE_CLERK", r"clerk", "MEDIUM", False, False),
    ("ROLE_DEPUTY_FLOOR_DIRECTOR", r"deputy\s+floor\s+director", "HIGH", False, False),
    ("ROLE_FLOOR_DIRECTOR", r"floor\s+director", "HIGH", False, False),
    ("ROLE_FLOOR_ASSISTANT", r"floor\s+assist(?:ant|\.)", "HIGH", False, False),
    ("ROLE_COMMUNICATIONS_DIRECTOR", r"communications?\s+director", "HIGH", False, False),
    ("ROLE_PRESS_SECRETARY", r"press\s+secretary", "HIGH", False, False),
    ("ROLE_PRESS_ASSISTANT", r"press\s+assistant", "HIGH", False, False),
    ("ROLE_SCHEDULER", r"scheduler", "HIGH", False, False),
    ("ROLE_CASEWORKER", r"case\s*worker", "HIGH", False, False),
    ("ROLE_FIELD_REPRESENTATIVE", r"field\s+representative", "HIGH", False, False),
    ("ROLE_DISTRICT_DIRECTOR", r"district\s+director", "HIGH", False, False),
    ("ROLE_STATE_DIRECTOR", r"state\s+director", "HIGH", False, False),
    ("ROLE_DIRECTOR_LEGISLATIVE_AFFAIRS", r"director\s+of\s+legislative\s+affairs", "HIGH", False, False),
    ("ROLE_DIRECTOR_CONGRESSIONAL_AFFAIRS", r"director\s+of\s+congressional\s+affairs", "HIGH", False, False),
    ("ROLE_DIRECTOR_GOVERNMENT_AFFAIRS", r"director\s+of\s+government\s+affairs", "HIGH", False, False),
    ("ROLE_DIRECTOR_GOVERNMENT_RELATIONS", r"director\s+of\s+government\s+relations", "HIGH", False, False),
    ("ROLE_DEPUTY_ASSISTANT_SECRETARY", r"deputy\s+assistant\s+secretary", "HIGH", False, False),
    ("ROLE_ASSISTANT_SECRETARY", r"assistant\s+secretary", "HIGH", False, False),
    ("ROLE_UNDER_SECRETARY", r"under\s+secretary", "HIGH", False, False),
    ("ROLE_ASSOCIATE_ADMINISTRATOR", r"associate\s+administrator", "HIGH", False, False),
    ("ROLE_ADMINISTRATOR", r"administrator", "MEDIUM", False, False),
    ("ROLE_COMMISSIONER", r"commissioner", "MEDIUM", False, False),
    ("ROLE_WHITE_HOUSE_LIAISON", r"white\s+house\s+liaison", "HIGH", False, False),
    ("ROLE_PRESIDENTIAL_APPOINTEE", r"presidential\s+appointee", "HIGH", False, False),
    ("ROLE_MEMBER_OF_CONGRESS", r"(?:former\s+)?member\s+of\s+(?:the\s+)?(?:u\.?s\.?\s+)?congress", "HIGH", False, False),
    ("ROLE_EXECUTIVE_DIRECTOR", r"executive\s+director", "MEDIUM", False, True),
    ("ROLE_SENIOR_DIRECTOR", r"senior\s+director", "MEDIUM", False, True),
    ("ROLE_DEPUTY_DIRECTOR", r"deputy\s+director", "MEDIUM", False, True),
    ("ROLE_ASSOCIATE_DIRECTOR", r"associate\s+director", "MEDIUM", False, True),
    ("ROLE_DIRECTOR", r"director", "LOW", False, True),
    ("ROLE_CHIEF_EXECUTIVE_OFFICER", r"chief\s+executive\s+officer", "MEDIUM", False, True),
    ("ROLE_VICE_PRESIDENT", r"vice\s+president", "MEDIUM", False, True),
    ("ROLE_PRESIDENT", r"president", "LOW", False, True),
    ("ROLE_MANAGING_PARTNER", r"managing\s+partner", "MEDIUM", False, True),
    ("ROLE_PARTNER", r"partner", "LOW", False, True),
    ("ROLE_PRINCIPAL", r"principal", "LOW", False, True),
    ("ROLE_CONSULTANT", r"consultant", "LOW", False, True),
    ("ROLE_LOBBYIST", r"lobbyist", "LOW", False, True),
    ("ROLE_INTERN", r"intern", "MEDIUM", False, False),
    ("ROLE_FELLOW", r"fellow", "MEDIUM", False, False),
    ("ROLE_STAFF", r"staff", "LOW", False, True),
    ("ROLE_CEO_ABBREVIATION", r"(?<!\w)CEO(?!\w)", "MEDIUM", True, True),
    ("ROLE_COS_ABBREVIATION", r"(?<!\w)(?:COS|CoS)(?!\w)", "MEDIUM", True, False),
    ("ROLE_MLA_ABBREVIATION", r"(?<!\w)MLA(?!\w)", "MEDIUM", True, False),
    ("ROLE_LD_ABBREVIATION", r"(?<!\w)LD(?!\w)", "MEDIUM", True, False),
    ("ROLE_LC_ABBREVIATION", r"(?<!\w)LC(?!\w)", "LOW", True, False),
    ("ROLE_LA_ABBREVIATION", r"(?<![-\w])LA(?!-\d|\w)", "LOW", True, False),
    ("ROLE_LEG_DIR_ABBREVIATION", r"leg(?:is)?\.?\s+dir(?:ector)?\.?(?!\w)", "MEDIUM", True, False),
    ("ROLE_LEG_ASST_ABBREVIATION", r"leg(?:is)?\.?\s+ass(?:is)?t(?:ant|'t)?\.?(?!\w)", "MEDIUM", True, False),
    ("ROLE_LEG_CORR_ABBREVIATION", r"leg(?:is)?\.?\s+corr(?:espondent)?\.?(?!\w)", "MEDIUM", True, False),
    ("ROLE_LEG_AIDE_ABBREVIATION", r"leg(?:is)?\.?\s+aide\.?(?!\w)", "MEDIUM", True, False),
    ("ROLE_PROF_STAFF_ABBREVIATION", r"prof\.?\s+staff(?:\s+member)?", "MEDIUM", True, False),
    ("ROLE_STAFF_ASST_ABBREVIATION", r"staff\s*asst\.?", "MEDIUM", True, False),
    ("ROLE_STAFF_DIR_ABBREVIATION", r"staff\s+dir\.?(?!\w)", "MEDIUM", True, False),
    ("ROLE_DEP_COS_ABBREVIATION", r"dep(?:uty)?\.?\s+(?:COS|CoS)(?!\w)", "MEDIUM", True, False),
    ("ROLE_SENIOR_LA_ABBREVIATION", r"(?:senior|sr\.?)\s+LA(?!-\d|\w)", "MEDIUM", True, False),
    ("ROLE_COUNSEL_ABBREVIATION", r"(?<!\w)(?:cnsl|coun)\.?(?!\w)", "LOW", True, False),
]


def compile_named(patterns: list[tuple[str, str, str, bool, bool]]) -> tuple[re.Pattern[str], dict[str, tuple[str, str, bool, bool]]]:
    ordered = sorted(patterns, key=lambda item: len(item[1]), reverse=True)
    metadata: dict[str, tuple[str, str, bool, bool]] = {}
    branches = []
    for index, (pattern_id, pattern, confidence, ambiguous, generic) in enumerate(ordered):
        group = f"R{index:03d}"
        branches.append(f"(?<!\\w)(?P<{group}>{pattern})(?!\\w)")
        metadata[group] = (pattern_id, confidence, ambiguous, generic)
    return re.compile("|".join(branches), re.I), metadata


ROLE_RE, ROLE_METADATA = compile_named(ROLE_PATTERNS)

ENTITY_STOP_WORD = (
    r"(?:Senior|Policy|Advisor|Adviser|Counsel|Staff|Director|Senator|Representative|"
    r"Congressman|Congresswoman|Chief|Deputy|Legislative|Professional|Assistant|Former|"
    r"Special|Intern|Fellow|Clerk|Press|Scheduler|Caseworker|Principal|Acting|General|Legal|Managing|"
    r"President|Commissioner|Administrator|Attorney|Atty|Communications?)"
)
ENTITY_NAME_WORD = rf"(?!(?:{ENTITY_STOP_WORD})\b)[A-Z][A-Za-z'’./\-]*"
ENTITY_CONNECTOR = r"(?:and|of|the|for|on|&|Affairs|Relations|Services|Resources|Development|Management|Security|Commerce|Finance|Labor|Education|Transportation|Judiciary|Appropriations|Intelligence)"

MEMBER_OFFICE_RE = re.compile(
    r"(?:Office\s+of\s+)?(?:U\.?S\.?\s+)?(?:Sen(?:ator)?|Rep(?:resentative)?|Congress(?:man|woman))\.?\s+"
    rf"{ENTITY_NAME_WORD}(?:\s+(?:{ENTITY_NAME_WORD}|Jr\.?|Sr\.?|II|III)){{0,3}}",
)
COMMITTEE_RE = re.compile(
    r"(?:"
    r"(?:(?:U\.?S\.?|United\s+States)\s+)?(?:House|Senate)?\s*"
    r"(?:Committee|Cmte\.?|Subcommittee|Subcmte\.?)"
    rf"(?:\s+on)?(?:\s+(?:{ENTITY_NAME_WORD}|{ENTITY_CONNECTOR})){{0,8}}"
    r"|"
    r"(?:(?:U\.?S\.?|United\s+States)\s+)?(?:House|Senate)"
    rf"(?:\s+(?:{ENTITY_NAME_WORD}|{ENTITY_CONNECTOR})){{1,6}}\s+(?:Committee|Cmte\.?)"
    r")",
)
DEPARTMENT_RE = re.compile(
    r"(?:(?:U\.?S\.?|United\s+States)\s+)?Department\s+of"
    rf"(?:\s+(?:{ENTITY_NAME_WORD}|{ENTITY_CONNECTOR})){{1,8}}",
)
OFFICE_OF_RE = re.compile(
    r"Office\s+of\s+(?:the\s+)?(?:U\.?S\.?\s+)?"
    rf"(?:{ENTITY_NAME_WORD}|{ENTITY_CONNECTOR})(?:\s+(?:{ENTITY_NAME_WORD}|{ENTITY_CONNECTOR})){{0,7}}",
)
ORG_SUFFIX_RE = re.compile(
    rf"{ENTITY_NAME_WORD}(?:\s+(?:{ENTITY_NAME_WORD}|{ENTITY_CONNECTOR})){{0,7}}\s+"
    r"(?:Association|Administration|Agency|Board|Bureau|Commission|Council|Corporation|"
    r"Company|Foundation|Institute|University)\b",
)
KNOWN_BODY_RE = re.compile(
    r"\b(?:U\.?S\.?\s+House\s+of\s+Representatives|US\s+House\s+of\s+Representatives|"
    r"House\s+of\s+Representatives|U\.?S\.?\s+Senate|US\s+Senate|United\s+States\s+Congress|"
    r"Executive\s+Office\s+of\s+the\s+President|Office\s+of\s+the\s+Vice\s+President|"
    r"The\s+White\s+House|White\s+House|National\s+Security\s+Council|"
    r"Office\s+of\s+Management\s+and\s+Budget|OMB|USTR|USAID|USDA|HUD|HHS|CMS|EPA|FCC|"
    r"CFTC|DOD|DOJ|DHS|NSC)\b",
    re.I,
)

ENTITY_PATTERNS: list[tuple[str, str, re.Pattern[str]]] = [
    ("MEMBER_OFFICE_CANDIDATE", "ENTITY_MEMBER_OFFICE_SHAPE", MEMBER_OFFICE_RE),
    ("COMMITTEE_CANDIDATE", "ENTITY_COMMITTEE_SHAPE", COMMITTEE_RE),
    ("FEDERAL_DEPARTMENT_CANDIDATE", "ENTITY_DEPARTMENT_SHAPE", DEPARTMENT_RE),
    ("GOVERNMENT_OFFICE_CANDIDATE", "ENTITY_OFFICE_OF_SHAPE", OFFICE_OF_RE),
    ("GOVERNMENT_BODY_CANDIDATE", "ENTITY_KNOWN_BODY", KNOWN_BODY_RE),
    ("ORGANIZATION_CANDIDATE", "ENTITY_ORGANIZATION_SUFFIX", ORG_SUFFIX_RE),
]

MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
DATE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "DATE_MONTH_YEAR_RANGE",
        re.compile(
            rf"(?<!\w){MONTH}\s*(?:19|20)?\d{{2}}\s*(?:-|–|—|to|through|until)\s*"
            rf"(?:{MONTH}\s*(?:19|20)?\d{{2}}|present|current)(?!\w)",
            re.I,
        ),
    ),
    (
        "DATE_NUMERIC_MONTH_YEAR_RANGE",
        re.compile(
            r"(?<!\d)\d{1,2}/(?:19|20)?\d{2}\s*(?:-|–|—|to|through|until)\s*"
            r"(?:\d{1,2}/(?:19|20)?\d{2}|present|current)(?!\d)",
            re.I,
        ),
    ),
    (
        "DATE_EXPLICIT_YEAR_RANGE",
        re.compile(
            r"(?<!\d)(?:19|20)\d{2}\s*(?:-|–|—|to|through|until)\s*"
            r"(?:(?:19|20)\d{2}|present|current)(?!\d)",
            re.I,
        ),
    ),
    (
        "DATE_APOSTROPHE_YEAR_RANGE",
        re.compile(
            r"(?<!\w)['’]\d{2}\s*(?:-|–|—|to|through|until)\s*['’]?\d{2}(?!\d)",
            re.I,
        ),
    ),
]
EXPLICIT_YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
REFERENCE_ONLY_RE = re.compile(r"\b(?:see|refer\s+to)\s+(?:prior|previous)\s+filing\b", re.I)
PUNCTUATION_ONLY_RE = re.compile(r"^[\s,;:./()\-–—]*$")


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def span_record(text: str, match: re.Match[str], pattern_id: str, confidence: str, ambiguous: bool, generic: bool) -> dict[str, Any]:
    return {
        "text": match.group(0),
        "span_start": match.start(),
        "span_end": match.end(),
        "pattern_id": pattern_id,
        "confidence": confidence,
        "ambiguous_abbreviation": ambiguous,
        "generic_title_risk": generic,
        "canonical_title": None,
        "promotion_status": "RAW_MENTION_ONLY",
    }


def nonoverlapping(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(records, key=lambda row: (row["span_start"], -(row["span_end"] - row["span_start"]), row["pattern_id"]))
    kept = []
    last_end = -1
    for row in ordered:
        if row["span_start"] < last_end:
            continue
        kept.append(row)
        last_end = row["span_end"]
    return kept


def extract_roles(text: str) -> list[dict[str, Any]]:
    records = []
    for match in ROLE_RE.finditer(text):
        pattern_id, confidence, ambiguous, generic = ROLE_METADATA[match.lastgroup or ""]
        prefix = text[max(0, match.start() - 32):match.start()]
        suffix = text[match.end():match.end() + 24]
        if pattern_id == "ROLE_PRESIDENT":
            # "the President", "President Obama", and "President Pro Tempore"
            # identify an officeholder/employer context, not the claimant's title.
            if re.search(
                r"(?:to|of|for|as|assistant|asst\.?|assist\.?)\s+(?:the\s+)?$", prefix, re.I
            ) or re.match(
                r"(?:['’]s|\s+(?:pro\s*[- ]?tempore|[A-Z](?:[A-Za-z.'’\-]*|\.)|management\s+fellow))",
                suffix,
                re.I,
            ):
                continue
        if pattern_id == "ROLE_VICE_PRESIDENT" and (
            re.search(r"(?:office\s*of|office|to|for)\s+(?:the\s+)?$", prefix, re.I)
            or re.match(r"\s+[A-Z][a-z]+", suffix)
        ):
            continue
        if pattern_id == "ROLE_DIRECTOR" and re.search(r"of\s+(?:the\s+)?$", prefix, re.I):
            continue
        if pattern_id == "ROLE_PRINCIPAL" and re.match(r"\s+deputy\b", suffix, re.I):
            continue
        records.append(span_record(text, match, pattern_id, confidence, ambiguous, generic))
    return records


def extract_entities(text: str) -> list[dict[str, Any]]:
    candidates = []
    for entity_class, pattern_id, pattern in ENTITY_PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(0).strip()
            raw = re.sub(r"\s+(?:and|of|the|for|on|&)\s*$", "", raw, flags=re.I)
            if not raw:
                continue
            start = match.start() + (len(match.group(0)) - len(match.group(0).lstrip()))
            end = start + len(raw)
            candidates.append({
                "text": raw,
                "span_start": start,
                "span_end": end,
                "pattern_id": pattern_id,
                "entity_class": entity_class,
                "confidence": "HIGH" if entity_class != "ORGANIZATION_CANDIDATE" else "MEDIUM",
                "canonical_employer_id": None,
                "promotion_status": "RAW_MENTION_ONLY",
            })
    return nonoverlapping(candidates)


def extract_dates(text: str) -> list[dict[str, Any]]:
    candidates = []
    for pattern_id, pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(0)
            years = [int(value) for value in EXPLICIT_YEAR_RE.findall(raw)]
            open_ended = bool(re.search(r"\b(?:present|current)\b", raw, re.I))
            review_flags = []
            if len(years) >= 2 and years[-1] < years[0]:
                review_flags.append("REVERSED_EXPLICIT_YEAR_RANGE")
            if not years:
                review_flags.append("NO_EXPLICIT_FOUR_DIGIT_YEAR")
            candidates.append({
                "text": raw,
                "span_start": match.start(),
                "span_end": match.end(),
                "pattern_id": pattern_id,
                "explicit_start_year": years[0] if years else None,
                "explicit_end_year": years[-1] if len(years) >= 2 else None,
                "open_ended_text": open_ended,
                "review_flags": review_flags,
                "canonical_date_range": None,
                "promotion_status": "RAW_MENTION_ONLY",
            })
    return nonoverlapping(candidates)


def normalize_text(text: str) -> dict[str, Any]:
    roles = extract_roles(text)
    entities = extract_entities(text)
    dates = extract_dates(text)
    flags = []
    if PUNCTUATION_ONLY_RE.fullmatch(text):
        flags.append("PUNCTUATION_ONLY_CLAIM_TEXT")
    if REFERENCE_ONLY_RE.search(text):
        flags.append("REFERENCE_TO_PRIOR_FILING_NOT_EMPLOYMENT_FACT")
    if any(row["ambiguous_abbreviation"] for row in roles):
        flags.append("AMBIGUOUS_ROLE_ABBREVIATION")
    if roles and not entities and all(row["generic_title_risk"] for row in roles):
        flags.append("GENERIC_ROLE_WITHOUT_OFFICE_OR_EMPLOYER")
    if dates:
        flags.append("DATE_RANGE_NOT_LINKED_TO_SPECIFIC_EPISODE")
    if roles and entities:
        flags.append("ROLE_EMPLOYER_BOUNDARY_NOT_ADJUDICATED")
    return {"roles": roles, "entities": entities, "dates": dates, "flags": flags}


def build_output(source_claim_row_ordinal: int, claim: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    explicit_no_position = bool(claim["explicit_no_position"])
    extracted = bool(parsed["roles"] or parsed["entities"] or parsed["dates"])
    status = "EXPLICIT_NO_POSITION" if explicit_no_position else "MENTIONS_EXTRACTED" if extracted else "NO_CONSERVATIVE_MENTION_EXTRACTED"
    return {
        "schema_id": "staffer-network-lda-employment-mention-normalization-v1",
        "source_claim_row_ordinal": source_claim_row_ordinal,
        "claim_id": claim["claim_id"],
        "lda_source_person_id": claim["lda_source_person_id"],
        "claim_text": claim["claim_text"],
        "raw_covered_position_literal": claim["raw_covered_position_literal"],
        "fragment_ordinal": claim["fragment_ordinal"],
        "explicit_no_position": explicit_no_position,
        "normalization_status": status,
        "role_title_mentions": parsed["roles"],
        "office_employer_mentions": parsed["entities"],
        "date_range_mentions": parsed["dates"],
        "normalization_review_flags": parsed["flags"],
        "identity_status": "LDA_SOURCE_IDENTITY_ONLY",
        "canonical_identity_decision": "NOT_ADJUDICATED",
        "canonical_employment_fact": False,
        "canonical_role_title_promotions": 0,
        "canonical_office_employer_promotions": 0,
        "canonical_date_range_promotions": 0,
        "complete_employment_history_asserted": False,
    }


def write_gzip(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            for row in rows:
                stream.write(canonical_bytes(row))
                count += 1
    return count


def validate_spans(rows: list[dict[str, Any]]) -> None:
    for row in rows:
        text = row["claim_text"]
        for field in ("role_title_mentions", "office_employer_mentions", "date_range_mentions"):
            for mention in row[field]:
                assert text[mention["span_start"]:mention["span_end"]] == mention["text"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")

    started = perf_counter()
    with gzip.open(args.input, "rt", encoding="utf-8") as stream:
        claims = [json.loads(line) for line in stream if line.strip()]
    loaded = perf_counter()
    assert len(claims) == 41680
    claim_id_counts = Counter(row["claim_id"] for row in claims)
    duplicate_claim_id_rows = sum(count - 1 for count in claim_id_counts.values())
    duplicated_claim_ids = sum(count > 1 for count in claim_id_counts.values())
    assert all(row["canonical_identity_decision"] == "NOT_ADJUDICATED" for row in claims)
    assert not any(row["canonical_employment_fact"] for row in claims)

    unique_texts = list(dict.fromkeys(row["claim_text"] for row in claims))
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        parsed_values = list(executor.map(normalize_text, unique_texts))
    parsed_by_text = dict(zip(unique_texts, parsed_values, strict=True))
    outputs = [
        build_output(ordinal, row, parsed_by_text[row["claim_text"]])
        for ordinal, row in enumerate(claims, 1)
    ]
    normalized = perf_counter()

    assert len(outputs) == len(claims)
    assert all(row["canonical_identity_decision"] == "NOT_ADJUDICATED" for row in outputs)
    assert not any(row["canonical_employment_fact"] for row in outputs)
    assert not any(row["complete_employment_history_asserted"] for row in outputs)
    assert not any(row["canonical_role_title_promotions"] for row in outputs)
    assert not any(row["canonical_office_employer_promotions"] for row in outputs)
    assert not any(row["canonical_date_range_promotions"] for row in outputs)
    validate_spans(outputs)

    output_path = args.output_root / OUTPUT_NAME
    receipt_path = args.output_root / RECEIPT_NAME
    expected = {output_path.name, receipt_path.name}
    if args.output_root.exists():
        unexpected = {path.name for path in args.output_root.iterdir()} - expected
        if unexpected:
            raise SystemExit(f"output root has unexpected files: {sorted(unexpected)}")
        if any((args.output_root / name).exists() for name in expected) and not args.overwrite:
            raise SystemExit("output files already exist; pass --overwrite for the two fixed targets")
    args.output_root.mkdir(parents=True, exist_ok=True)
    output_count = write_gzip(output_path, outputs)
    written = perf_counter()

    status_counts = Counter(row["normalization_status"] for row in outputs)
    role_pattern_counts = Counter(item["pattern_id"] for row in outputs for item in row["role_title_mentions"])
    entity_class_counts = Counter(item["entity_class"] for row in outputs for item in row["office_employer_mentions"])
    date_pattern_counts = Counter(item["pattern_id"] for row in outputs for item in row["date_range_mentions"])
    flag_counts = Counter(flag for row in outputs for flag in row["normalization_review_flags"])
    position_rows = [row for row in outputs if not row["explicit_no_position"]]
    role_rows = sum(bool(row["role_title_mentions"]) for row in position_rows)
    entity_rows = sum(bool(row["office_employer_mentions"]) for row in position_rows)
    date_rows = sum(bool(row["date_range_mentions"]) for row in position_rows)
    any_rows = sum(bool(row["role_title_mentions"] or row["office_employer_mentions"] or row["date_range_mentions"]) for row in position_rows)
    receipt = {
        "schema_id": "staffer-network-lda-employment-mention-normalization-receipt-v1",
        "status": "PASS",
        "workers": args.workers,
        "input": {"path": str(args.input), "bytes": args.input.stat().st_size, "sha256": sha256_file(args.input)},
        "input_claim_rows": len(claims),
        "distinct_input_claim_ids": len(claim_id_counts),
        "duplicated_input_claim_ids": duplicated_claim_ids,
        "duplicate_input_claim_id_rows_preserved": duplicate_claim_id_rows,
        "unique_claim_texts_normalized": len(unique_texts),
        "output_claim_rows": output_count,
        "normalization_status_counts": dict(sorted(status_counts.items())),
        "coverage": {
            "position_claim_rows": len(position_rows),
            "rows_with_role_title_mentions": role_rows,
            "rows_with_office_employer_mentions": entity_rows,
            "rows_with_date_range_mentions": date_rows,
            "rows_with_any_conservative_mention": any_rows,
            "rows_without_conservative_mention": len(position_rows) - any_rows,
            "role_title_row_coverage_basis_points": round(10000 * role_rows / len(position_rows)),
            "office_employer_row_coverage_basis_points": round(10000 * entity_rows / len(position_rows)),
            "date_range_row_coverage_basis_points": round(10000 * date_rows / len(position_rows)),
            "any_mention_row_coverage_basis_points": round(10000 * any_rows / len(position_rows)),
        },
        "mention_counts": {
            "role_title_mentions": sum(len(row["role_title_mentions"]) for row in outputs),
            "office_employer_mentions": sum(len(row["office_employer_mentions"]) for row in outputs),
            "date_range_mentions": sum(len(row["date_range_mentions"]) for row in outputs),
        },
        "role_pattern_counts": dict(sorted(role_pattern_counts.items())),
        "office_employer_class_counts": dict(sorted(entity_class_counts.items())),
        "date_pattern_counts": dict(sorted(date_pattern_counts.items())),
        "false_positive_review_signal_counts": dict(sorted(flag_counts.items())),
        "risk_notes": [
            "All matches are exact source-text candidates; none is a canonical title, employer, office, person, episode, or date range.",
            "Finite title and entity patterns favor precision and therefore under-recall novel, misspelled, or unusually abbreviated disclosures.",
            "Short role abbreviations such as LA, LC, LD, MLA, and COS are retained but explicitly flagged as ambiguous.",
            "Generic titles such as president, director, partner, principal, consultant, lobbyist, and staff can describe non-covered or malformed disclosures and receive lower confidence or review flags.",
            "Organization-suffix matching can include adjacent capitalized words; entity boundaries remain unadjudicated.",
            "Date ranges are not linked to a particular title or employer, and two-digit years are not century-expanded.",
            "Reference-only and punctuation-only claims are retained and flagged rather than interpreted as employment facts.",
            "The source contains duplicate claim IDs; all physical rows are preserved and distinguished only by a stable source-row ordinal.",
        ],
        "validation": {
            "claim_id_uniqueness": "SOURCE_DUPLICATES_PRESERVED",
            "exact_span_round_trip": "PASS",
            "input_order_preserved": "PASS",
            "canonical_identity_promotions": 0,
            "canonical_employment_promotions": 0,
            "canonical_role_title_promotions": 0,
            "canonical_office_employer_promotions": 0,
            "canonical_date_range_promotions": 0,
            "complete_history_assertions": 0,
        },
        "output": {"path": output_path.name, "bytes": output_path.stat().st_size, "sha256": sha256_file(output_path)},
        "determinism": "Canonical sorted-key JSON, source order, stable first-seen text cache, executor.map order, and gzip mtime=0. Runtime observations are printed only and excluded from this receipt.",
    }
    receipt_path.write_bytes(canonical_bytes(receipt))
    finished = perf_counter()
    benchmark = {
        "workers": args.workers,
        "claims": len(claims),
        "unique_texts": len(unique_texts),
        "load_seconds": round(loaded - started, 6),
        "normalize_seconds": round(normalized - loaded, 6),
        "write_and_hash_seconds": round(finished - normalized, 6),
        "total_seconds": round(finished - started, 6),
        "normalization_claims_per_second": round(len(claims) / (normalized - loaded), 2),
        "end_to_end_claims_per_second": round(len(claims) / (finished - started), 2),
        "receipt_sha256": sha256_file(receipt_path),
    }
    print(json.dumps({"receipt": receipt, "benchmark_observation": benchmark}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
