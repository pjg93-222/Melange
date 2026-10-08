#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit the four immutable proposal artifacts plus the receipt.

Adjudication of the 23 absent measures is authored by the Opus 5 lane and
carried here as a table; this module does the mechanical work only -- it maps
the Quorum floor onto discovery, partitions all 465 legacy rows into exactly
one accounting state each, hashes every input and output, and refuses to write
if any coverage identity fails.

Nothing here integrates, promotes, scores, or recomputes ranks.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys

OUT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(OUT, "..", "..", "..", ".."))
sys.path.insert(0, OUT)

from reconcile_recall_floor import (  # noqa: E402
    LEGACY, QUORUM, RECEIPT_IN, RECORDS, MEMBERSHIPS,
    legacy_canonical_key, load_discovery, load_quorum, sha256_file,
)

RUN_ID = "bill_recall_culling_opus5_20260728a"

ARCHIVE_XLSX = os.path.abspath(os.path.join(REPO, "..", "Draft Systems",
                                            "congress_bills_archive_20260624_115822.xlsx"))
ROUTING_AUDIT = os.path.join(REPO, "legislation_routing_audit.json")
CATEGORY_REGISTRY = os.path.join(REPO, "audits", "legfix5", "opus_adjudication",
                                 "original_method_evidence", "acu_category_registry.json")
SEARCH_REGISTRY = os.path.join(REPO, "source_data", "legislation",
                               "acu_legislation_search_registry.json")
METHOD_MANIFEST = os.path.join(REPO, "audits", "legfix5", "opus_adjudication",
                               "original_method_evidence", "manifest.json")
ACU_LETTERS = os.path.join(REPO, "audits", "legfix5", "opus_adjudication",
                           "original_method_evidence", "acu_letters_snapshot_20260725.json")
PRESS_CACHE = os.path.join(REPO, "audits", "legfix5", "opus_adjudication",
                           "original_method_evidence", "press_text_cache.jsonl")
PROBE_LEDGER = os.path.join(REPO, "audits", "legfix5",
                            "historical_probe_outstanding_identifiers_20260727.ndjson")
OUTLINE_DOCX = os.path.join(REPO, "source_data", "legislation",
                            "Moneyball_ACU_Search_Outline.docx")

# The nineteen canonical category ids, taken from the search registry, which is
# derived from the outline. Assignments below may only use these.
CANONICAL_19 = None  # filled at run time from the registry


# --------------------------------------------------------------------------
# The adjudication. One entry per absent legacy key; authored from the
# official surfaces named in `evidence_ids`. No entry decides anything
# finally -- every row carries automated_final_decision=false.
# --------------------------------------------------------------------------
SMALL_LENDER_EVIDENCE = [
    "archive.title",
    "archive.bill_summary",
    "archive.committee",
    "discovery.sibling_membership.118:hr:1806",
    "discovery.sibling_membership.119:hr:941",
    "discovery.rule_class_precedent.118:hjres:50",
    "discovery.rule_class_precedent.118:sjres:32",
    "acu_letters.1591",
    "acu_letters.3441",
    "press_text_cache.small_lender",
]
BNPL_EVIDENCE = [
    "archive.title",
    "archive.committee",
    "acu_letters.1126",
    "acu_letters.396",
    "acu_letters.1581",
    "discovery.rule_class_precedent.118:hjres:121",
    "discovery.rule_class_precedent.118:sjres:70",
    "discovery.rule_class_precedent.119:sjres:167",
    "registry.payments_boundary",
]
SBA_EVIDENCE = ["archive.title", "archive.bill_summary", "archive.committee",
                "registry.member_business_lending_boundary", "probe_ledger.uncollected"]
NSBW_EVIDENCE = ["archive.title", "archive.bill_summary.crs",
                 "registry.member_business_lending_boundary",
                 "prior_art.legfix2_audit_20260724.F2"]

SMALL_LENDER_REASON = (
    "Official short title 'Small LENDER Act' and official long title 'Small Lenders "
    "Exempt from New Data and Excessive Reporting Act' state the operative effect: "
    "exempting smaller lenders from the CFPB small-business-lending data collection "
    "under ECOA/Dodd-Frank section 1071. Credit unions are covered financial "
    "institutions under that rule, so the measure carries a material credit-union "
    "policy nexus. Category is corroborated inside the north-star corpus itself: the "
    "same bill family in other Congresses (118:hr:1806, 119:hr:941, same sponsor and "
    "same official title) is held in discovery under member_business_lending and "
    "cfpb_issues_structural_reform, and discovery routes CFPB section 1071 "
    "Regulation B rule disapprovals (118:hjres:50, 118:sjres:32) to "
    "member_business_lending. ACU's own advocacy record files section 1071 both as "
    "Consumer Protection (letter 1591 on S.557) and as Lending (letter 3441 on the "
    "CFPB 1071 rule). The legacy Member Business Lending category is therefore "
    "retained and cfpb_issues_structural_reform is added, not substituted. "
    "Operative bill text was not reviewed: no BillStatus receipt, GovInfo object or "
    "discovery record for this key is held locally and network collection is barred."
)
BNPL_REASON = (
    "Official title is dispositive of subject: congressional disapproval under 5 "
    "U.S.C. ch. 8 of a Bureau of Consumer Financial Protection rule under Truth in "
    "Lending (Regulation Z) governing use of digital user accounts to access Buy Now, "
    "Pay Later loans. Credit unions are Regulation Z creditors, and America's Credit "
    "Unions filed its own comment letter on this exact rule (letter 1126, 'Comment "
    "Letter to CFPB on BNPL Digital User Accounts', 2024-07-31), which ACU classifies "
    "under its Consumer Protection issue area -- establishing the credit-union policy "
    "nexus and placing the measure in the outline's Consumer Protection section, not "
    "Payment & Technology. The legacy 'Payments' category is unsupported: the "
    "north-star Payments boundary is real-time payments, FedNow, instant payment "
    "fraud, payment system access, ACH payment, faster payments and payment "
    "stablecoin, none of which a Regulation Z consumer-credit rule touches; the "
    "legacy retrieval URL shows the measure was pulled in by a legacy Payments query "
    "containing a loose 'buy now pay later' term that the outline-derived Payments "
    "query does not carry. Discovery's own routing of CFPB rule disapprovals by the "
    "rule's subject (Regulation Z credit card penalty fees -> "
    "credit_card_consumer_fee_mandates at 118:hjres:121 and 118:sjres:70) and ACU's "
    "parallel disapproval letters (396, 1581) fix the corrected categories. "
    "Operative text was not reviewed: no BillStatus receipt, GovInfo object or "
    "discovery record for this key is held locally."
)
NSBW_REASON = (
    "The official CRS summary states the measure's complete operative content: the "
    "resolution celebrates the contributions of small businesses and supports the "
    "designation of National Small Business Week, and supports efforts to provide "
    "small businesses with aid and assistance through certain programs and "
    "initiatives. A simple House resolution expressing support for a commemorative "
    "designation carries no operative policy effect on any regulated institution, so "
    "it cannot fall inside any of the nineteen policy categories; in particular it "
    "touches none of the member-business-lending identifiers, every one of which is "
    "credit-union or MBL specific. This is affirmative official evidence of falling "
    "outside the nineteen categories rather than mere absence from discovery. It is "
    "also the largest scoring artifact in this group: the two National Small Business "
    "Week resolutions together account for 93 selected member-bill contributions in "
    "the live archive under Member Business Lending. Independent prior art agrees: "
    "the 2026-07-24 legislative audit named these two resolutions among the bills "
    "with no credit-union nexus on their face, a finding that survived adversarial "
    "review, though that audit is corroborating prior art and the exclusion here "
    "rests on the official CRS summary."
)


def sba_reason(title, committee, extra=""):
    return (
        "Official review order could not be completed. The only official surfaces held "
        "locally for this key are the official title (%s) and the official committee "
        "referral (%s); no official summary and no operative bill text exist in any "
        "local store -- there is no BillStatus receipt, no GovInfo object and no "
        "discovery record for it, and the historical probe ledger records the "
        "identifier as outstanding and uncollected. The title states a Small Business "
        "Act / SBA-program subject and carries no credit-union, NCUA, Federal Credit "
        "Union Act or depository term, so nothing affirmatively establishes the "
        "material credit-union policy nexus an inclusion requires. Equally, nothing "
        "affirmatively establishes that the measure falls outside all nineteen "
        "categories: committee referral to the Small Business committees is not "
        "disqualifying, because America's Credit Unions files its own advocacy under "
        "the outline's Lending section with those same committees (letters 341, 346 on "
        "SBA oversight, 3416 on veteran entrepreneurs). Absence from discovery is "
        "neutral and is not used here as exclusion evidence. Uncertainty therefore "
        "remains flagged.%s" % (title, committee, (" " + extra) if extra else "")
    )


ADJUDICATIONS = [
    # ---- include_candidate: Small LENDER Act family (section 1071) ----------
    {"canonical_key": "117:hr:6732", "legacy_category": "Member Business Lending",
     "disposition": "include_candidate",
     "category_ids": ["member_business_lending", "cfpb_issues_structural_reform"],
     "category_change": "retain_and_cross_list",
     "official_title": "Small LENDER Act",
     "official_long_title": "Small Lenders Exempt from New Data and Excessive Reporting Act or the Small LENDER Act",
     "official_committee": "House - Financial Services",
     "official_summary_status": "title_echo_only_no_crs_summary_held",
     "title_reviewed": True, "operative_text_reviewed": False,
     "evidence_ids": SMALL_LENDER_EVIDENCE, "reason": SMALL_LENDER_REASON,
     "confidence": "high"},
    {"canonical_key": "117:s:4004", "legacy_category": "Member Business Lending",
     "disposition": "include_candidate",
     "category_ids": ["member_business_lending", "cfpb_issues_structural_reform"],
     "category_change": "retain_and_cross_list",
     "official_title": "Small LENDER Act",
     "official_long_title": "Small Lenders Exempt from New Data and Excessive Reporting Act or the Small LENDER Act",
     "official_committee": "Senate - Banking, Housing, and Urban Affairs",
     "official_summary_status": "title_echo_only_no_crs_summary_held",
     "title_reviewed": True, "operative_text_reviewed": False,
     "evidence_ids": SMALL_LENDER_EVIDENCE, "reason": SMALL_LENDER_REASON,
     "confidence": "high"},
    {"canonical_key": "118:s:1159", "legacy_category": "Member Business Lending",
     "disposition": "include_candidate",
     "category_ids": ["member_business_lending", "cfpb_issues_structural_reform"],
     "category_change": "retain_and_cross_list",
     "official_title": "Small LENDER Act",
     "official_long_title": "Small Lenders Exempt from New Data and Excessive Reporting Act or the Small LENDER Act",
     "official_committee": "Senate - Banking, Housing, and Urban Affairs",
     "official_summary_status": "title_echo_only_no_crs_summary_held",
     "title_reviewed": True, "operative_text_reviewed": False,
     "evidence_ids": SMALL_LENDER_EVIDENCE, "reason": SMALL_LENDER_REASON,
     "confidence": "high"},

    # ---- include_candidate: CFPB Regulation Z BNPL rule disapprovals -------
    {"canonical_key": "118:hjres:190", "legacy_category": "Payments",
     "disposition": "include_candidate",
     "category_ids": ["cfpb_issues_structural_reform", "credit_card_consumer_fee_mandates"],
     "category_change": "corrected_from_legacy",
     "official_title": ('Providing for congressional disapproval under chapter 8 of title 5, '
                        'United States Code, of the rule submitted by the Bureau of Consumer '
                        'Financial Protection relating to "Truth in Lending (Regulation Z); Use '
                        'of Digital User Accounts to Access Buy Now, Pay Later Loans".'),
     "official_committee": "House - Financial Services",
     "official_summary_status": "no_official_summary_held",
     "title_reviewed": True, "operative_text_reviewed": False,
     "evidence_ids": BNPL_EVIDENCE, "reason": BNPL_REASON, "confidence": "medium-high"},
    {"canonical_key": "118:hjres:195", "legacy_category": "Payments",
     "disposition": "include_candidate",
     "category_ids": ["cfpb_issues_structural_reform", "credit_card_consumer_fee_mandates"],
     "category_change": "corrected_from_legacy",
     "official_title": ('Providing for congressional disapproval under chapter 8 of title 5, '
                        'United States Code, of the rule submitted by the Bureau of Consumer '
                        'Financial Protection relating to "Truth in Lending (Regulation Z); Use '
                        'of Digital User Accounts to Access Buy Now, Pay Later Loans".'),
     "official_committee": "House - Financial Services",
     "official_summary_status": "no_official_summary_held",
     "title_reviewed": True, "operative_text_reviewed": False,
     "evidence_ids": BNPL_EVIDENCE, "reason": BNPL_REASON, "confidence": "medium-high"},
    {"canonical_key": "119:sjres:134", "legacy_category": "Payments",
     "disposition": "include_candidate",
     "category_ids": ["cfpb_issues_structural_reform", "credit_card_consumer_fee_mandates"],
     "category_change": "corrected_from_legacy",
     "official_title": ('A joint resolution providing for congressional disapproval under chapter '
                        '8 of title 5, United States Code, of the rule submitted by the Bureau of '
                        'Consumer Financial Protection relating to the withdrawal of the rule '
                        'relating to "Truth in Lending (Regulation Z); Use of Digital User '
                        'Accounts to Access Buy Now, Pay Later Loans".'),
     "official_committee": "Senate - Banking, Housing, and Urban Affairs",
     "official_summary_status": "no_official_summary_held",
     "title_reviewed": True, "operative_text_reviewed": False,
     "evidence_ids": BNPL_EVIDENCE + ["discovery.rule_class_precedent.withdrawal_form"],
     "reason": BNPL_REASON + (" This instance disapproves the Bureau's withdrawal of the same "
                              "rule; discovery holds the identical withdrawal-form construction "
                              "at 119:sjres:167, so the form itself is within the corpus."),
     "confidence": "medium-high"},

    # ---- exclude_false_positive: ceremonial designation resolutions --------
    {"canonical_key": "117:hres:634", "legacy_category": "Member Business Lending",
     "disposition": "exclude_false_positive", "category_ids": [],
     "category_change": "none_measure_outside_all_19",
     "official_title": ('Expressing support for the designation of the week of September 13, 2021, '
                        'through September 17, 2021, as "National Small Business Week" to celebrate '
                        'the contributions of small businesses and entrepreneurs in every community '
                        'in the United States.'),
     "official_committee": "House - Small Business",
     "official_summary_status": "official_crs_summary_held",
     "title_reviewed": True, "operative_text_reviewed": False,
     "evidence_ids": NSBW_EVIDENCE, "reason": NSBW_REASON, "confidence": "high"},
    {"canonical_key": "117:hres:1076", "legacy_category": "Member Business Lending",
     "disposition": "exclude_false_positive", "category_ids": [],
     "category_change": "none_measure_outside_all_19",
     "official_title": ('Expressing support for the designation of the week of May 2, 2022, through '
                        'May 5, 2022, as "National Small Business Week" to celebrate the '
                        'contributions of small businesses and entrepreneurs in every community in '
                        'the United States.'),
     "official_committee": "House - Small Business",
     "official_summary_status": "official_crs_summary_held",
     "title_reviewed": True, "operative_text_reviewed": False,
     "evidence_ids": NSBW_EVIDENCE, "reason": NSBW_REASON, "confidence": "high"},
]

# ---- flagged: official review order incomplete ----------------------------
FLAGGED = [
    ("117:hr:3155", "Member Business Lending", "Small Business Child Care Investment Act",
     "House - Small Business", "title_echo_only_no_crs_summary_held", ""),
    ("117:s:1587", "Member Business Lending", "Small Business Child Care Investment Act",
     "Senate - Small Business and Entrepreneurship", "title_echo_only_no_crs_summary_held", ""),
    ("118:s:673", "Member Business Lending", "Small Business Child Care Investment Act",
     "Senate - Small Business and Entrepreneurship", "title_echo_only_no_crs_summary_held", ""),
    ("118:hr:2602", "Member Business Lending", "Small Business Child Care Investment Act",
     "House - Small Business", "no_official_summary_held", ""),
    ("119:s:273", "Member Business Lending", "Small Business Child Care Investment Act",
     "Senate - Small Business and Entrepreneurship", "no_official_summary_held", ""),
    ("117:s:5076", "Member Business Lending",
     "Service-Disabled Veteran Opportunities in Small Business Act",
     "Senate - Small Business and Entrepreneurship", "title_echo_only_no_crs_summary_held",
     "The north-star member-business-lending boundary does carry veteran-specific identifiers "
     "('MBL veteran', 'exempt loan credit union veteran') because the outline's flagship MBL bill "
     "is the Veterans Member Business Loan Act, so a veteran small-business measure is the exact "
     "near-miss neighbour and must not be culled on the title alone."),
    ("118:hr:3511", "Member Business Lending",
     "Service-Disabled Veteran Opportunities in Small Business Act",
     "House - Small Business | Senate - Small Business and Entrepreneurship",
     "title_echo_only_no_crs_summary_held",
     "Official status is Passed House, so this instance carries more scoring weight than its "
     "companions and warrants the summary fetch before any cull."),
    ("118:s:3302", "Member Business Lending", "Heroes Business Opportunity Act of 2023",
     "Senate - Small Business and Entrepreneurship", "no_official_summary_held",
     "Veteran/servicemember small-business subject; same near-miss neighbourhood as the "
     "Veterans Member Business Loan Act."),
    ("119:s:3136", "Member Business Lending", "Heroes Business Opportunity Act of 2025",
     "Senate - Small Business and Entrepreneurship", "no_official_summary_held",
     "Veteran/servicemember small-business subject; same near-miss neighbourhood as the "
     "Veterans Member Business Loan Act."),
    ("119:s:3171", "Member Business Lending", "Veteran Entrepreneurship Empowerment Act",
     "Senate - Small Business and Entrepreneurship", "no_official_summary_held",
     "America's Credit Unions letter 3416 (2025-12-08, Lending) addresses a House Small Business "
     "Committee veteran-entrepreneurs hearing, so the subject is inside ACU's Lending advocacy "
     "even though this bill is not named in it; that is a reason to fetch the summary, not to cull."),
    ("117:s:63", "Member Business Lending", "Unlocking Opportunities in Emerging Markets Act of 2021",
     "Senate - Small Business and Entrepreneurship", "title_echo_only_no_crs_summary_held",
     "The title's underserved/emerging-markets subject plausibly overlaps the CDFI Fund boundary "
     "(minority depository institution, MDI, underserved community lending), so the operative text "
     "could place it inside a category other than the legacy one."),
    ("117:s:1690", "Member Business Lending", "Keeping Our Promise to Small Businesses Act",
     "Senate - Appropriations", "title_echo_only_no_crs_summary_held",
     "Referral to Appropriations rather than a small-business or banking committee leaves the "
     "operative vehicle unidentified from the title."),
    ("117:hr:3854", "Fraud Prevention", "Small Business Credit Protection Act of 2021",
     "House - Small Business", "title_echo_only_no_crs_summary_held",
     "The legacy Fraud Prevention placement is not supported by the north-star fraud boundary, "
     "every identifier of which is credit-union or payment-fraud specific; but a small-business "
     "credit-reporting measure could fall under Data Privacy & Cybersecurity ('data breach "
     "notification'), so this is a category question the summary must settle, not a cull."),
    ("117:s:2034", "Fraud Prevention", "Small Business Credit Protection Act",
     "Senate - Small Business and Entrepreneurship", "no_official_summary_held",
     "Senate companion of 117:hr:3854; the legacy retrieval URL shows it was pulled in by a loose "
     "legacy Fraud Prevention term bag ending in the bare token 'identity'."),
    ("117:hr:474", "Fraud Prevention", "Protecting Consumer Information Act of 2021",
     "House - Financial Services; Energy and Commerce", "title_echo_only_no_crs_summary_held",
     "Referral to House Financial Services means the measure does reach financial institutions, "
     "and the title's consumer-information subject plausibly falls under Data Privacy & "
     "Cybersecurity rather than the legacy Fraud Prevention; this is the strongest inclusion "
     "candidate among the flagged rows and must not be culled. The archive stores this title "
     "truncated as 'Protecting Consumer Information Act of 20'; the full title is recovered from "
     "the archive summary field."),
]

URL_TYPE = {"hr": "hr", "s": "s", "hres": "hres", "sres": "sres",
            "hjres": "hjres", "sjres": "sjres", "hconres": "hconres", "sconres": "sconres"}


def billstatus_url(key):
    congress, mtype, number = key.split(":")
    return ("https://www.govinfo.gov/bulkdata/BILLSTATUS/%s/%s/BILLSTATUS-%s%s%s.xml"
            % (congress, URL_TYPE[mtype], congress, URL_TYPE[mtype], number))


for key, legacy_cat, title, cmte, sumstat, extra in FLAGGED:
    ADJUDICATIONS.append({
        "canonical_key": key, "legacy_category": legacy_cat, "disposition": "flagged",
        "category_ids": [], "category_change": "undetermined_pending_official_summary",
        "official_title": title, "official_committee": cmte,
        "official_summary_status": sumstat,
        "title_reviewed": True, "operative_text_reviewed": False,
        "evidence_ids": SBA_EVIDENCE, "reason": sba_reason(title, cmte, extra),
        "confidence": "insufficient_evidence",
        "resolution_artifact_required": billstatus_url(key),
    })


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_ndjson(path, rows):
    buf = io.StringIO()
    for row in rows:
        buf.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
        buf.write("\n")
    data = buf.getvalue()
    with io.open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(data)
    return sha256_text(data), len(rows)


def live_footprint():
    """How many rows each absent key currently occupies in the live scoring archive.

    Read-only. These 23 measures are not hypothetical: every one of them is
    already scoring today via congress_bills_archive -> archive_leg.json, so the
    proposals below are corrections to a live plane, not additions to an empty one.
    """
    audit = json.load(io.open(ROUTING_AUDIT, encoding="utf-8"))
    disp = {"hr": "H.R.", "s": "S.", "hres": "H.Res.",
            "hjres": "H.J.Res.", "sjres": "S.J.Res.", "sres": "S.Res."}
    out = {}
    for row in audit["rows"]:
        congress, name = str(row["congress"]), row["bill"]
        m = re.match(r"^([A-Za-z\.]+?)\s*([0-9]+)$", name.strip())
        if not m:
            continue
        inv = {v: k for k, v in disp.items()}
        mtype = inv.get(m.group(1))
        if not mtype:
            continue
        key = "%s:%s:%s" % (congress, mtype, m.group(2))
        rec = out.setdefault(key, {"archive_rows": 0, "selected_rows": 0})
        rec["archive_rows"] += 1
        if row.get("disposition") == "selected":
            rec["selected_rows"] += 1
    return out


def main():
    reg = json.load(io.open(SEARCH_REGISTRY, encoding="utf-8"))
    canonical_19 = [c["id"] for c in reg["categories"]]
    assert len(canonical_19) == 19, canonical_19
    label_of = {c["id"]: c["label"] for c in reg["categories"]}

    receipt_in = json.load(io.open(RECEIPT_IN, encoding="utf-8"))
    expected_missing = sorted(m["canonical_key"] for m in receipt_in["legacy_floor_missing"])

    discovery = load_discovery()
    legacy = json.load(io.open(LEGACY, encoding="utf-8"))

    blockers = []

    # ---------------- legacy partition (465) -------------------------------
    adj_by_key = {}
    for a in ADJUDICATIONS:
        if a["canonical_key"] in adj_by_key:
            blockers.append("duplicate adjudication row for %s" % a["canonical_key"])
        for cid in a["category_ids"]:
            if cid not in canonical_19:
                blockers.append("non-canonical category id %r on %s" % (cid, a["canonical_key"]))
        adj_by_key[a["canonical_key"]] = a

    legacy_rows = []
    absent_keys = []
    for cite, row in legacy.items():
        ckey, err = legacy_canonical_key(cite, row["congress"])
        if err:
            blockers.append("legacy key parse failure: %s (%s)" % (cite, err))
        present = bool(ckey and ckey in discovery)
        if present:
            state = "covered_in_discovery"
            adj = None
        else:
            absent_keys.append(ckey)
            adj = adj_by_key.get(ckey)
            state = adj["disposition"] if adj else "MISSING_ADJUDICATION"
            if adj is None:
                blockers.append("absent legacy key with no adjudication: %s" % ckey)
        entry = {
            "schema": "acu-legacy-recall-partition-v1",
            "run_id": RUN_ID,
            "legacy_cite": cite,
            "canonical_key": ckey,
            "congress": row.get("congress"),
            "legacy_title": row.get("title", ""),
            "legacy_category": row.get("section", ""),
            "present_in_discovery": present,
            "accounting_state": state,
            "proposed_category_ids": (adj or {}).get("category_ids", []),
            "automated_final_decision": False,
            "human_ratification_required": True,
        }
        legacy_rows.append(entry)

    if sorted(absent_keys) != expected_missing:
        blockers.append("absent set does not equal the frozen receipt's 23-key list")

    # ---------------- quorum partition (44) --------------------------------
    qrows = load_quorum()
    header = qrows[0]
    hdr = {col: (header.get(col) or "").strip() for col in header}
    URL_RE = re.compile(
        r"congress\.gov/bill/(\d+)[a-z]{2}-congress/"
        r"(house-bill|senate-bill|house-resolution|senate-resolution|"
        r"house-joint-resolution|senate-joint-resolution|"
        r"house-concurrent-resolution|senate-concurrent-resolution)/(\d+)")
    URL_MAP = {"house-bill": "hr", "senate-bill": "s", "house-resolution": "hres",
               "senate-resolution": "sres", "house-joint-resolution": "hjres",
               "senate-joint-resolution": "sjres",
               "house-concurrent-resolution": "hconres",
               "senate-concurrent-resolution": "sconres"}

    quorum_rows = []
    for raw in qrows[1:]:
        rec = {hdr.get(col, col): (val or "") for col, val in raw.items()}
        if not any(v.strip() for v in rec.values()):
            continue
        src = rec.get("Source Link", "")
        m = URL_RE.search(src)
        if not m:
            ckey = None
            blockers.append("quorum row without a resolvable congress.gov source link: %r"
                            % rec.get("Label"))
        else:
            ckey = "%s:%s:%s" % (m.group(1), URL_MAP[m.group(2)], m.group(3))
        present = bool(ckey and ckey in discovery)
        if not present:
            blockers.append("quorum row absent from discovery: %s (%s)" % (ckey, rec.get("Label")))
        quorum_rows.append({
            "schema": "acu-quorum-recall-partition-v1",
            "run_id": RUN_ID,
            "quorum_id": rec.get("Quorum ID"),
            "label": rec.get("Label"),
            "title": rec.get("Title"),
            "session": rec.get("Session"),
            "source_link": src,
            "canonical_key": ckey,
            "present_in_discovery": present,
            "accounting_state": "covered_in_discovery" if present else "fail_closed",
            "recall_evidence_only": True,
            "disposition_assigned_from_quorum": False,
            "automated_final_decision": False,
            "human_ratification_required": True,
        })

    seen = {}
    for q in quorum_rows:
        seen.setdefault(q["canonical_key"], 0)
        seen[q["canonical_key"]] += 1

    # ---------------- proposal rows (23) -----------------------------------
    foot = live_footprint()
    proposals = []
    for a in ADJUDICATIONS:
        key = a["canonical_key"]
        proposals.append({
            "live_scoring_footprint": foot.get(key, {"archive_rows": 0, "selected_rows": 0}),
            "schema": "acu-bill-recall-proposal-adjudication-v1",
            "run_id": RUN_ID,
            "canonical_key": key,
            "legacy_category": a["legacy_category"],
            "disposition": a["disposition"],
            "category_ids": a["category_ids"],
            "category_labels": [label_of[c] for c in a["category_ids"]],
            "category_change": a["category_change"],
            "official_title": a["official_title"],
            "official_long_title": a.get("official_long_title"),
            "official_committee": a["official_committee"],
            "official_summary_status": a["official_summary_status"],
            "title_reviewed": a["title_reviewed"],
            "operative_text_reviewed": a["operative_text_reviewed"],
            "evidence_ids": a["evidence_ids"],
            "evidence_sources": EVIDENCE_SOURCES,
            "resolution_artifact_required": a.get("resolution_artifact_required"),
            "official_source_url": billstatus_url(key),
            "reason": a["reason"],
            "confidence": a["confidence"],
            "absence_from_discovery_used_as_exclusion_evidence": False,
            "role_or_direction_assigned": False,
            "automated_final_decision": False,
            "human_ratification_required": True,
        })

    if len(proposals) != 23:
        blockers.append("proposal count is %d, not 23" % len(proposals))
    if len({p["canonical_key"] for p in proposals}) != 23:
        blockers.append("proposal canonical keys are not unique")
    if len(legacy_rows) != 465:
        blockers.append("legacy partition count is %d, not 465" % len(legacy_rows))
    if len({r["canonical_key"] for r in legacy_rows}) != 465:
        blockers.append("legacy partition canonical keys are not unique")
    if len(quorum_rows) != 44:
        blockers.append("quorum partition count is %d, not 44" % len(quorum_rows))

    hard = [b for b in blockers if not b.startswith("NOTE")]
    if hard:
        print("FAIL CLOSED -- coverage identity not proven:")
        for b in hard:
            print("  -", b)
        return 2

    p1 = os.path.join(OUT, "proposal_adjudications_23.ndjson")
    p2 = os.path.join(OUT, "legacy_recall_partition_465.ndjson")
    p3 = os.path.join(OUT, "quorum_recall_partition_44.ndjson")
    h1, n1 = write_ndjson(p1, proposals)
    h2, n2 = write_ndjson(p2, legacy_rows)
    h3, n3 = write_ndjson(p3, quorum_rows)

    BLOCKERS.extend([
        "BLOCKER (binds all 23): no official summary and no operative bill text is held "
        "locally for any of the twenty-three absent measures. None has a BillStatus "
        "receipt (the 14,854-record fetch was scoped to discovery), a GovInfo object "
        "(all eight runs are scoped to the same 18,440 jobs), or a discovery record, and "
        "the historical probe ledger records all twenty-three identifiers as outstanding "
        "with probe_collected=false. operative_text_reviewed is therefore false on every "
        "row. The single artifact that closes this per key is its GovInfo BILLSTATUS XML, "
        "named on each row as resolution_artifact_required / official_source_url; "
        "fetching it is network collection, which this lane is barred from performing.",

        "BLOCKER (15 rows): fifteen measures remain flagged because the official review "
        "order stops at the title. Neither an inclusion (which needs affirmative official "
        "evidence of a material credit-union nexus) nor an exclusion (which needs "
        "affirmative official evidence of falling outside all nineteen categories) is "
        "supported on a title alone, and absence from discovery is neutral by rule.",

        "NOTE (path resolution): the lane brief binds "
        "'original_method_evidence/category_method_registry.json', which does not exist. "
        "The method_boundary registry in the frozen manifest is "
        "'original_method_evidence/acu_category_registry.json' "
        "(sha256 f95c092d3a594bf4..., role method_boundary); that file was bound instead, "
        "together with source_data/legislation/acu_legislation_search_registry.json, which "
        "carries the nineteen canonical category ids used in category_ids.",

        "NOTE (input outside the frozen bundle): the only local holder of official titles, "
        "committee referrals and CRS summaries for the twenty-three is "
        "'Draft Systems/congress_bills_archive_20260624_115822.xlsx', the original "
        "method's own collection surface. It sits outside both the recovered input root "
        "and the frozen evidence manifest and is a live, mutable file; it has been hashed "
        "here so the adjudication is pinned to the bytes actually read.",

        "NOTE (title defect): the archive stores 117:hr:474 with a truncated title, "
        "'Protecting Consumer Information Act of 20'. The full title is recovered from the "
        "archive's own summary field and is recorded on that row.",

        "NOTE (BNPL category is contestable): the three Regulation Z Buy Now, Pay Later "
        "disapproval resolutions are proposed as cfpb_issues_structural_reform plus "
        "credit_card_consumer_fee_mandates on the strength of the official title and "
        "America's Credit Unions' own Consumer Protection classification of its comment "
        "letter on that rule. Discovery routes substantive BNPL bills "
        "(119:hr:6891, 119:s:3561) to technology_emerging_issues instead, so a ratifier "
        "may prefer that cross-listing; the one thing the evidence does not support is the "
        "legacy 'Payments' label.",

        "NOTE (live footprint, nothing changed): the twenty-three measures currently "
        "occupy %d rows in the live scoring archive, of which %d are selected "
        "contributions. The two proposed exclusions alone account for %d selected rows. "
        "No archive, workbook, ledger, rank or score was touched by this run."
        % (sum(foot.get(p["canonical_key"], {}).get("archive_rows", 0) for p in proposals),
           sum(foot.get(p["canonical_key"], {}).get("selected_rows", 0) for p in proposals),
           sum(foot.get(p["canonical_key"], {}).get("selected_rows", 0) for p in proposals
               if p["disposition"] == "exclude_false_positive")),
    ])

    counts_by_state = {}
    for r in legacy_rows:
        counts_by_state[r["accounting_state"]] = counts_by_state.get(r["accounting_state"], 0) + 1
    disp_counts = {}
    for p in proposals:
        disp_counts[p["disposition"]] = disp_counts.get(p["disposition"], 0) + 1

    receipt = {
        "schema": "acu-bill-recall-culling-proposal-receipt-v1",
        "run_id": RUN_ID,
        "status": "PROPOSAL_ONLY_AWAITING_HUMAN_RATIFICATION",
        "model": "claude-opus-5",
        "network_collection_performed": False,
        "delegated_semantic_decisions": False,
        "method": {
            "north_star": "Moneyball ACU Search Outline (19 categories)",
            "review_order": ["official_title", "official_summary_or_status", "operative_bill_text"],
            "recall_files_are_not_disposition_evidence": True,
            "absence_from_discovery_is_neutral": True,
            "inclusion_requires_affirmative_official_cu_nexus": True,
            "exclusion_requires_affirmative_official_out_of_scope_evidence": True,
            "category_follows_operative_policy_effect_not_legacy_label": True,
            "no_role_direction_or_scoring_assigned_from_letters_press_or_recall_files": True,
        },
        "inputs": INPUT_HASHES,
        "outputs": {
            "proposal_adjudications_23.ndjson": {"sha256": h1, "records": n1},
            "legacy_recall_partition_465.ndjson": {"sha256": h2, "records": n2},
            "quorum_recall_partition_44.ndjson": {"sha256": h3, "records": n3},
        },
        "coverage_identities": {
            "discovery_records": len(discovery),
            "legacy_floor_rows": len(legacy_rows),
            "legacy_floor_present_in_discovery": counts_by_state.get("covered_in_discovery", 0),
            "legacy_floor_absent_from_discovery": len(absent_keys),
            "legacy_absent_equals_frozen_receipt_list": sorted(absent_keys) == expected_missing,
            "legacy_canonical_keys_unique": len({r["canonical_key"] for r in legacy_rows}) == 465,
            "legacy_partition_states_sum_to_465":
                sum(counts_by_state.values()) == 465,
            "proposal_rows": len(proposals),
            "proposal_keys_unique": len({p["canonical_key"] for p in proposals}) == 23,
            "proposal_keys_equal_absent_set":
                sorted(p["canonical_key"] for p in proposals) == expected_missing,
            "quorum_floor_rows": len(quorum_rows),
            "quorum_floor_present_in_discovery":
                sum(1 for q in quorum_rows if q["present_in_discovery"]),
            "quorum_floor_fail_closed":
                sum(1 for q in quorum_rows if not q["present_in_discovery"]),
            "quorum_distinct_canonical_keys": len(seen),
            "quorum_duplicate_canonical_keys":
                sorted(k for k, v in seen.items() if v > 1),
        },
        "counts": {
            "legacy_accounting_states": counts_by_state,
            "proposal_dispositions": disp_counts,
            "category_corrections_proposed":
                sum(1 for p in proposals if p["category_change"] == "corrected_from_legacy"),
            "cross_listings_proposed":
                sum(1 for p in proposals if p["category_change"] == "retain_and_cross_list"),
        },
        "canonical_19_category_ids": canonical_19,
        "local_evidence_sweep": SWEEP_SUMMARY,
        "blocker_semantics": (
            "A coverage-identity failure fails this run closed and writes nothing; none "
            "occurred. The entries below are the disclosed limits of the adjudication "
            "itself -- what evidence was unavailable, what a ratifier should contest, and "
            "what remains untouched."),
        "blockers": BLOCKERS,
        "integration_performed": False,
        "production_write_performed": False,
        "scoring_performed": False,
        "rank_recompute_performed": False,
        "discovery_mutated": False,
        "manual_bill_evidence_mutated": False,
        "workbook_written": False,
        "junk_ledger_written": False,
        "recovered_input_root_mutated": False,
    }
    rpath = os.path.join(OUT, "receipt.json")
    text = json.dumps(receipt, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    with io.open(rpath, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)

    print("WROTE")
    print("  proposal_adjudications_23.ndjson    ", n1, h1)
    print("  legacy_recall_partition_465.ndjson  ", n2, h2)
    print("  quorum_recall_partition_44.ndjson   ", n3, h3)
    print("  receipt.json                        ", sha256_text(text))
    print("legacy states :", counts_by_state)
    print("dispositions  :", disp_counts)
    print("quorum present:", sum(1 for q in quorum_rows if q["present_in_discovery"]), "/", len(quorum_rows))
    return 0


# Filled by the caller before main() -- kept out of the adjudication body so the
# hashes in the receipt are computed from the files themselves, not restated.
INPUT_HASHES = {}
EVIDENCE_SOURCES = {}
BLOCKERS = []
SWEEP_SUMMARY = {}


def build_input_hashes():
    files = {
        "recall_floor_evidence/receipt.json": RECEIPT_IN,
        "recall_floor_evidence/legacy_collection_floor_465.json": LEGACY,
        "recall_floor_evidence/quorum_recall_floor_44.xlsx": QUORUM,
        "original_method_evidence/manifest.json": METHOD_MANIFEST,
        "original_method_evidence/acu_category_registry.json": CATEGORY_REGISTRY,
        "original_method_evidence/acu_letters_snapshot_20260725.json": ACU_LETTERS,
        "original_method_evidence/press_text_cache.jsonl": PRESS_CACHE,
        "congress_advanced_pages_20260725/congress_advanced_records.ndjson": RECORDS,
        "congress_advanced_pages_20260725/congress_advanced_memberships.ndjson": MEMBERSHIPS,
        "historical_probe_outstanding_identifiers_20260727.ndjson": PROBE_LEDGER,
        "source_data/legislation/acu_legislation_search_registry.json": SEARCH_REGISTRY,
        "source_data/legislation/Moneyball_ACU_Search_Outline.docx": OUTLINE_DOCX,
        "legislation_routing_audit.json": ROUTING_AUDIT,
        "Draft Systems/congress_bills_archive_20260624_115822.xlsx": ARCHIVE_XLSX,
    }
    out = {}
    for label, path in files.items():
        if not os.path.exists(path):
            BLOCKERS.append("bound input missing on disk: %s" % label)
            continue
        out[label] = {"path": path.replace("\\", "/"),
                      "bytes": os.path.getsize(path),
                      "sha256": sha256_file(path)}
    return out


if __name__ == "__main__":
    INPUT_HASHES = build_input_hashes()
    EVIDENCE_SOURCES = {
        "archive.title": "Draft Systems/congress_bills_archive_20260624_115822.xlsx :: 'All Bills'.Title",
        "archive.bill_summary": "Draft Systems/congress_bills_archive_20260624_115822.xlsx :: 'All Bills'.bill_summary",
        "archive.bill_summary.crs": "same column, holding a genuine CRS summary rather than a title echo",
        "archive.committee": "Draft Systems/congress_bills_archive_20260624_115822.xlsx :: 'All Bills'.Committee",
        "discovery.sibling_membership": "audits/legfix5/congress_advanced_pages_20260725/congress_advanced_memberships.ndjson",
        "discovery.rule_class_precedent": "audits/legfix5/congress_advanced_pages_20260725/congress_advanced_records.ndjson",
        "acu_letters": "audits/legfix5/opus_adjudication/original_method_evidence/acu_letters_snapshot_20260725.json :: letters[].id",
        "press_text_cache": "audits/legfix5/opus_adjudication/original_method_evidence/press_text_cache.jsonl",
        "registry.payments_boundary": "source_data/legislation/acu_legislation_search_registry.json :: categories[id=payments].advanced_search_query",
        "registry.member_business_lending_boundary": "source_data/legislation/acu_legislation_search_registry.json :: categories[id=member_business_lending].advanced_search_query",
        "probe_ledger.uncollected": "audits/legfix5/historical_probe_outstanding_identifiers_20260727.ndjson :: probe_collected=false",
        "prior_art.legfix2_audit_20260724.F2": "audits/legfix2/audit_sp_reference/LEGISLATIVE_AUDIT_2026-07-24.md :: PART 4 finding F2",
    }
    _sweep_path = os.path.join(OUT, "_local_evidence_sweep.json")
    if os.path.exists(_sweep_path):
        _s = json.load(io.open(_sweep_path, encoding="utf-8"))
        SWEEP_SUMMARY = {
            "files_scanned": _s["files_scanned"],
            "files_skipped": _s["files_skipped"],
            "roots": [r.replace("\\", "/") for r in _s["roots"]],
            "excluded_trees": ["objects (govinfo content-addressed store)",
                               "sha256 (billstatus content-addressed store)",
                               ".git", "node_modules", "__pycache__"],
            "surface_hit_counts": _s["hit_counts"],
            "sha256": sha256_file(_sweep_path),
            "note": ("Raw substring hit counts include worktree duplicates, rendered HTML and "
                     "numeric collisions; the dispositive reads were done by hand against the "
                     "surfaces named in evidence_sources."),
        }
    else:
        BLOCKERS.append("local evidence sweep artifact missing; sweep coverage unproven")
    sys.exit(main())
