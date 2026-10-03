"""Deterministic, offline FEC receipt cross-reference accounting.

This is an experimental view, never a production mutation. ``counted_cents``
is a provisional original-giving candidate amount, not a claim of uniqueness.
PAC activity observed on recipient receipts is reported separately. All raw
inputs and retrieved evidence remain the caller's responsibility to preserve.

Affiliations: {"records": [{company, entity_id OR entity_name,
relationship: "connected_pac"|"treasury_entity", valid_from, valid_to?,
source_url, evidence_id}]}.

Filing manifest: {"families": [{committee_id, root_file_num, latest_file_num,
complete: true, source_url, source_ids: [all current receipt IDs],
transaction_ids: [all current receipt transaction IDs]}],
"unique_origin_certificates": [{source_id, evidence_ids: [...],
filing_complete: true, origin_verified: true, routes_complete: true}]}.
The caller must establish and archive manifest/certificate evidence; these are
evidence assertions, not discovered facts or an accuracy estimate. Unsupported
certificates cannot promote a row. Collection completeness is never inferred.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
import json
import re

from pac_evidence import is_memo, name_key, receipt_role


def _text(value):
    return " ".join(str(value or "").upper().split())


def _cents(value):
    try:
        amount = Decimal(str(value)) * 100
        if not amount.is_finite() or amount != amount.to_integral_value():
            raise ValueError("Amounts must be finite whole cents")
        return int(amount)
    except InvalidOperation as exc:
        raise ValueError("Invalid monetary amount") from exc


def _integer(value):
    amount = Decimal(str(value))
    if not amount.is_finite() or amount != amount.to_integral_value():
        raise ValueError("Expected integer cents")
    return int(amount)


def _day(value):
    value = str(value or "")[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return ""
    try:
        date.fromisoformat(value)
    except ValueError:
        return ""
    return value


def _file(row):
    value = str(row.get("file_number") or row.get("file_num") or "").strip()
    return "" if value in ("0", "0.0") else value


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _identifiers(values):
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    return sorted({str(value) for value in values if value not in (None, "")})


def analyze(rows, evidence=None, headers=None, affiliations=None, filing_manifest=None):
    """Return stable decisions, supported links, review tasks and cent totals.

    Identical repeated source rows are coalesced; conflicting rows or retrieved
    identities fail closed. Missing metadata does not silently erase dollars.
    Negative receipts are signed adjustments until a compatible explicit refund
    link is supplied (adjustment_type, refund_of_sub_id, adjustment_evidence_id).
    """
    evidence, headers = evidence or {}, headers or {}
    affiliations, filing_manifest = affiliations or {}, filing_manifest or {}
    source, duplicate_count = {}, 0
    for raw in rows:
        row = dict(raw)
        sid = str(row.get("sub_id") or "")
        if not sid:
            raise ValueError("Every source row requires sub_id")
        if sid in source:
            if _json(source[sid]) != _json(row):
                raise ValueError(f"Conflicting duplicate source ID: {sid}")
            duplicate_count += 1
        else:
            source[sid] = row
    source = dict(sorted(source.items()))
    merged, decisions, reviews, links = {}, {}, [], []
    conflicted = set()
    attribution_review = set()

    def review(reason, ids, action, **context):
        reviews.append(dict(reason=reason, source_ids=sorted(set(ids)), action=action, **context))

    def reason(sid, code, support=()):
        decisions[sid]["reasons"].append(code)
        decisions[sid]["evidence_ids"].extend(str(s) for s in support if s)

    def exclude(sid, code, counterpart=None, link_evidence=(), kind="duplicate"):
        d = decisions[sid]
        d["counted_cents"] = 0
        d["pac_activity_cents"] = 0
        d["status"] = "excluded_with_evidence"
        reason(sid, code, link_evidence)
        if counterpart:
            links.append(dict(kind=kind, source_id=sid, counterpart_id=counterpart,
                              amount_cents=d["amount_cents"], evidence_ids=sorted(set(link_evidence))))

    for sid, stored in source.items():
        row = dict(stored)
        remote = evidence.get(sid)
        if remote is not None:
            if str(remote.get("sub_id") or "") != sid:
                raise ValueError(f"FEC identity conflict: {sid}, sub_id")
            for field in ("committee_id", "contributor_name", "transaction_id"):
                if stored.get(field) not in (None, "") and _text(stored[field]) != _text(remote.get(field)):
                    raise ValueError(f"FEC identity conflict: {sid}, {field}")
            if _file(stored) and _file(stored) != _file(remote):
                raise ValueError(f"FEC identity conflict: {sid}, file_number")
            if _cents(stored["contribution_receipt_amount"]) != _cents(remote["contribution_receipt_amount"]):
                raise ValueError(f"FEC amount conflict: {sid}")
            if _day(stored.get("contribution_receipt_date")) != _day(remote.get("contribution_receipt_date")):
                raise ValueError(f"FEC date conflict: {sid}")
            # Remote FEC fields may not overwrite local company/industry decisions.
            protected = {k: row[k] for k in ("company", "industry", "cycle", "current_receipt_cents",
                "company_match_status", "company_match_reason", "excluded_reason",
                "source_conflicts", "attribution_claims") if k in row}
            row.update({k: v for k, v in remote.items() if v is not None})
            row.update(protected)
        merged[sid] = row
        amount = _cents(row["contribution_receipt_amount"])
        role = receipt_role(row)
        entity = _text(row.get("entity_type"))
        donor_id = str(row.get("contributor_id") or "")
        bucket = "employee_original" if entity == "IND" else "organization_unverified" if entity == "ORG" else "funding_unverified"
        if entity in ("PAC", "COM", "CCM", "PTY") and re.fullmatch(r"C\d{8}", donor_id):
            bucket = "pac_activity"
        d = decisions[sid] = dict(source_id=sid, company=str(row.get("company") or ""),
            industry=str(row.get("industry") or ""), cycle=row.get("cycle"), amount_cents=amount,
            baseline_cents=_integer(row.get("current_receipt_cents", amount)), counted_cents=amount,
            pac_activity_cents=0, supported_unique_cents=0, bucket=bucket, receipt_role=role,
            status="provisional", reasons=[], evidence_ids=[sid, str(remote.get('_evidence_id') or sid)] if remote is not None else [sid],
            exact_fec_response_verified=remote is not None,
            funding_direction="original_donor_to_recipient", attribution_status="unverified")
        field_provenance = (remote or {}).get("_field_evidence_ids") or {}
        d["field_evidence_ids"] = {str(field): _identifiers(values) for field, values in sorted(field_provenance.items())}
        d["evidence_ids"].extend(_identifiers((remote or {}).get("_evidence_ids")))
        for ids in d["field_evidence_ids"].values():
            d["evidence_ids"].extend(ids)
        match = _text(row.get("company_match_status"))
        if (match not in ("ACCEPTED", "REJECTED", "EXCLUDED") or
                (match == "ACCEPTED" and not _text(row.get("company")))):
            attribution_review.add(sid)
            exclude(sid, "company_attribution_unresolved", link_evidence=[sid])
            d["bucket"] = "attribution_unresolved"
            review("company_attribution_unresolved", [sid],
                   "Resolve the employer/company identity and record an accepted or rejected attribution decision.",
                   company=d["company"], company_match_status=row.get("company_match_status"),
                   company_match_reason=row.get("company_match_reason") or row.get("excluded_reason") or "")
            continue
        if str(row.get("excluded_reason") or "").strip():
            # Reinterpreting a receipt is not authorization to undo a separate
            # explicit source exclusion. Preserve the decision and its reason;
            # callers may adjudicate that policy in a separately tracked change.
            exclude(sid, "preexisting_source_exclusion:" + str(row["excluded_reason"]).strip(), link_evidence=[sid])
            d["bucket"] = "excluded_source_policy"
            continue
        claims = row.get("attribution_claims") or []
        claimed_companies = {_text(c.get("company")) for c in claims if isinstance(c, dict)
                             and c.get("company") and _text(c.get("company_match_status", c.get("status", ""))) not in ("REJECTED", "EXCLUDED")}
        if row.get("source_conflicts") or len(claimed_companies | {_text(row.get('company'))}) > 1:
            conflicted.add(sid)
            d["bucket"] = "conflicting_source_evidence"
            reason(sid, "source_or_attribution_conflict")
            review("source_or_attribution_conflict", [sid],
                   "Resolve conflicting source facts or company claims against the preserved FEC evidence before applying links or certifying attribution.",
                   conflicts=row.get("source_conflicts") or [], attribution_claims=claims)
            continue
        if match and match != "ACCEPTED":
            exclude(sid, "company_attribution_not_accepted")
            d["bucket"] = "excluded_company_match"
            continue
        if role in ("other_receipt", "asset_liquidation"):
            exclude(sid, "non_giving_receipt_role:" + role, link_evidence=[sid] if remote is not None else [])
            d["bucket"] = "non_giving"
            continue
        if role not in ("contribution", "in_kind_contribution"):
            review("receipt_role_unresolved" if role != "transfer_receipt" else "original_source_of_transfer_unresolved",
                   [sid], "Retrieve the receipt and referenced original donor/transaction evidence.",
                   file_num=_file(row), transaction_id=str(row.get("transaction_id") or ""))
            reason(sid, "provisional_receipt_role:" + role)
        else:
            reason(sid, "recognized_contribution_receipt")
        if not _day(row.get("contribution_receipt_date")):
            review("receipt_date_missing", [sid], "Recover the exact FEC receipt date.")
        if entity == "IND" and match == "ACCEPTED" and row.get("company"):
            d["attribution_status"] = "accepted_reported_employer"
            reason(sid, "individual_with_accepted_employer_match")
        if bucket == "pac_activity":
            nested_id = (row.get("contributor") or {}).get("committee_id")
            if nested_id and nested_id != donor_id:
                d["bucket"] = "funding_unverified"
                review("pac_identity_conflict", [sid], "Resolve the FEC contributor committee ID conflict.")
            else:
                d["counted_cents"], d["pac_activity_cents"] = 0, amount
                d["funding_direction"] = "pac_to_recipient_observed_on_schedule_a"
                reason(sid, "separate_observed_pac_activity", [donor_id])
        elif entity not in ("IND", "ORG"):
            review("funding_identity_unresolved", [sid], "Recover the FEC contributor entity type and contributor ID.")

    affiliation_rows = affiliations.get("records", []) if isinstance(affiliations, dict) else affiliations
    for sid, row in merged.items():
        d = decisions[sid]
        if d["status"] == "excluded_with_evidence" or sid in conflicted:
            continue
        day, company = _day(row.get("contribution_receipt_date")), _text(row.get("company"))

        def affiliations_for(identifier, reported_name, relationship):
            result = []
            for a in affiliation_rows:
                start, end = _day(a.get("valid_from")), _day(a.get("valid_to"))
                identity = ((a.get("entity_id") and str(a["entity_id"]) == identifier) or
                            (not a.get("entity_id") and a.get("entity_name") and
                             name_key(a["entity_name"]) == name_key(reported_name)))
                if (_text(a.get("company")) == company and a.get("relationship") == relationship and identity
                        and day and start and start <= day and (not end or day <= end)
                        and (not a.get("valid_to") or end)
                        and a.get("source_url") and a.get("evidence_id")):
                    result.append(a)
            return result

        relationship = "connected_pac" if d["bucket"] == "pac_activity" else "treasury_entity"
        matches = affiliations_for(str(row.get("contributor_id") or ""), row.get("contributor_name"), relationship)
        if d["bucket"] in ("organization_unverified", "pac_activity"):
            if matches:
                d["attribution_status"] = "dated_affiliation_supported"
                reason(sid, relationship + "_affiliation", [a["evidence_id"] for a in matches])
                if relationship == "treasury_entity":
                    d["bucket"] = "corporate_original"
            else:
                review("treasury_ownership_unresolved" if d["bucket"] == "organization_unverified" else "company_pac_affiliation_unresolved",
                       [sid], "Establish the dated company/entity relationship with a source and evidence ID.",
                       company=d["company"], entity_id=str(row.get("contributor_id") or ""))
        if d["bucket"] == "employee_original":
            recipient_pacs = affiliations_for(str(row.get("committee_id") or ""),
                                              (row.get("committee") or {}).get("name"), "connected_pac")
            if recipient_pacs:
                d["funding_direction"] = "employee_to_company_pac"
                reason(sid, "recipient_is_dated_company_pac", [a["evidence_id"] for a in recipient_pacs])

    # Follow actual filing-family identifiers; repeated transaction IDs outside
    # the same family do not establish an amendment relationship.
    families = defaultdict(list)
    row_family = {}
    family_members = defaultdict(list)
    missing_family = defaultdict(list)
    for sid, row in merged.items():
        # An amended row reclassified as non-giving still supersedes its old
        # contribution representation. Classification cannot hide the winner.
        if is_memo(row) or sid in conflicted or sid in attribution_review:
            continue
        h = headers.get(_file(row), {})
        if (not h or h.get("relationship_evidence") is False or not row.get("transaction_id")):
            missing_family[(str(row.get("committee_id") or ""), _file(row))].append(sid)
            continue
        if (str(h.get("file_num")) != _file(row) or str(h.get("committee_id")) != str(row.get("committee_id"))
                or h.get("filing_form") != row.get("filing_form")):
            raise ValueError(f"Filing header identity conflict: {sid}")
        root = str(h.get("original_file_num") or h.get("file_num"))
        order = 0 if not h.get("original_file_num") else h.get("amendment_number")
        if not str(order).isdigit():
            missing_family[(str(row.get("committee_id") or ""), _file(row))].append(sid)
            continue
        family = (str(row["committee_id"]), root)
        row_family[sid] = family
        family_members[family].append(sid)
        families[(*family, str(row["transaction_id"]))].append((sid, int(order)))
    for group in families.values():
        if len(group) < 2:
            continue
        if len({_text(merged[sid].get("company")) for sid, _ in group}) != 1:
            review("amendment_changes_company_identity", [sid for sid, _ in group], "Resolve company attribution across the explicit filing family.")
            continue
        latest = max(order for _, order in group)
        winners = [sid for sid, order in group if order == latest]
        if len(winners) != 1:
            review("ambiguous_amendment_order", [sid for sid, _ in group], "Retrieve all versions and establish the final filing order.")
            continue
        winner = winners[0]
        for sid, _ in group:
            if sid != winner:
                exclude(sid, "superseded_in_observed_filing_family", winner,
                        [_file(merged[sid]), _file(merged[winner])], "amendment")

    complete_families = {}
    for f in filing_manifest.get("families", []):
        key = (str(f.get("committee_id") or ""), str(f.get("root_file_num") or ""))
        if not (f.get("complete") is True and f.get("source_url") and isinstance(f.get("source_ids"), list)):
            continue
        if key in complete_families and _json(complete_families[key]) != _json(f):
            raise ValueError("Conflicting complete filing manifests")
        complete_families[key] = f
    for sid, family in row_family.items():
        d, row = decisions[sid], merged[sid]
        f = complete_families.get(family)
        if not f or d["status"] == "excluded_with_evidence":
            continue
        latest_file = str(f.get("latest_file_num") or "")
        latest_header = headers.get(latest_file, {})
        latest_root = str(latest_header.get("original_file_num") or latest_header.get("file_num") or "")
        current_header = headers.get(_file(row), {})
        current_order = 0 if not current_header.get("original_file_num") else current_header.get("amendment_number")
        latest_order = 0 if not latest_header.get("original_file_num") else latest_header.get("amendment_number")
        if (latest_header.get("relationship_evidence") is False or latest_root != family[1]
                or str(latest_header.get("committee_id") or "") != family[0]
                or not str(latest_order).isdigit() or not str(current_order).isdigit()
                or int(latest_order) < int(current_order)
                or (int(latest_order) == int(current_order) and latest_file != _file(row))):
            review("latest_filing_manifest_not_corroborated", [sid], "Recover the declared latest filing header and complete transaction inventory.")
            continue
        current_ids = {str(value) for value in f["source_ids"]}
        if _file(row) != latest_file:
            # Physical source IDs change across amendments. A list of latest
            # IDs alone cannot establish transaction deletion or replacement.
            transactions = f.get("transaction_ids")
            if not current_ids or (isinstance(transactions, list) and str(row.get("transaction_id")) not in {str(t) for t in transactions}):
                exclude(sid, "absent_from_complete_latest_filing", link_evidence=[latest_file, f["source_url"]], kind="amendment")
            else:
                review("latest_filing_transaction_replacement_missing", [sid],
                       "Retrieve the latest filing transaction inventory and any current representation before removing this provisional older amount.",
                       latest_file_num=latest_file, transaction_id=str(row.get("transaction_id") or ""))
        elif sid not in current_ids:
            raise ValueError(f"Current filing manifest omits supplied current source ID: {sid}")
        else:
            reason(sid, "complete_latest_filing_inventory", [latest_file, f["source_url"]])

    # Explicit local memo references, with donor/date/sign and amount coverage.
    parent_index = defaultdict(list)
    for sid, row in merged.items():
        d = decisions[sid]
        if (sid not in conflicted and not is_memo(row) and d["status"] != "excluded_with_evidence" and
                d["receipt_role"] in ("contribution", "in_kind_contribution", "transfer_receipt")):
            parent_index[(str(row.get("committee_id") or ""), _file(row), _text(row.get("transaction_id")))].append(sid)
    for sid, row in merged.items():
        d = decisions[sid]
        if not is_memo(row) or d["status"] == "excluded_with_evidence" or sid in conflicted:
            continue
        reference = _text(row.get("back_reference_transaction_id"))
        schedule = _text(row.get("back_reference_schedule_name"))
        refs = {reference, f"{schedule}.{reference}"} if reference else set()
        if not refs:
            refs = {f"{a}.{b}" for a, b in re.findall(r"\[([A-Z0-9]+):([A-Z0-9.]+)\]",
                    _text(str(row.get("receipt_type_full") or "") + " " + str(row.get("memo_text") or "")))}
        candidates = set()
        for ref in refs:
            for parent in parent_index[(str(row.get("committee_id") or ""), _file(row), ref)]:
                p, amount = merged[parent], d["amount_cents"]
                pa = decisions[parent]["amount_cents"]
                if (parent != sid and _file(row) and _text(p.get("company")) == _text(row.get("company"))
                        and _text(p.get("contributor_name")) == _text(row.get("contributor_name"))
                        and _day(row.get("contribution_receipt_date"))
                        and _day(p.get("contribution_receipt_date")) == _day(row.get("contribution_receipt_date"))
                        and amount * pa > 0 and abs(pa) >= abs(amount)):
                    candidates.add(parent)
        if len(candidates) == 1:
            parent = next(iter(candidates))
            exclude(sid, "explicit_same_filing_memo_reference", parent, [sid, parent], "memo")
        else:
            review("memo_parent_ambiguous" if candidates else "memo_parent_not_established", [sid, *candidates],
                   "Retrieve the referenced same-filing parent and validate donor, date, sign and amount coverage.",
                   file_num=_file(row), references=sorted(refs))

    # Reciprocal earmark language creates a candidate relationship; equal
    # amounts alone never create one. One-to-one disjoint routes only.
    route_index = defaultdict(list)
    for sid, row in merged.items():
        if sid not in conflicted and decisions[sid]["counted_cents"] > 0 and not is_memo(row):
            key = (_text(row.get("company")), _text(row.get("contributor_name")),
                   _day(row.get("contribution_receipt_date")), decisions[sid]["counted_cents"])
            route_index[key].append(sid)
    proposals = []
    for origin, oe in sorted(evidence.items()):
        if origin not in decisions or origin in conflicted or decisions[origin]["counted_cents"] <= 0 or is_memo(oe):
            continue
        desc = _text(str(oe.get("receipt_type_full") or "") + " " + str(oe.get("memo_text") or ""))
        if "EARMARKED FOR" not in desc:
            continue
        ids = set(re.findall(r"\bC\d{8}\b", desc))
        if len(ids) != 1:
            review("earmark_destination_ambiguous", [origin], "Recover the explicitly designated recipient committee ID.")
            continue
        row = merged[origin]
        key = (_text(row.get("company")), _text(row.get("contributor_name")),
               _day(row.get("contribution_receipt_date")), decisions[origin]["counted_cents"])
        candidates = [s for s in route_index[key] if s != origin and str(merged[s].get("committee_id")) in ids]
        if len(candidates) != 1:
            review("earmark_counterpart_not_unique", [origin, *candidates], "Fetch the designated recipient receipt and validate the reciprocal earmark.", recipient_ids=sorted(ids))
            continue
        destination = candidates[0]
        de = evidence.get(destination)
        zip_o = re.sub(r"\D", "", str(oe.get("contributor_zip") or ""))[:5]
        zip_d = re.sub(r"\D", "", str((de or {}).get("contributor_zip") or ""))[:5]
        conduit = _text((oe.get("committee") or {}).get("name"))
        dd = _text(str((de or {}).get("receipt_type_full") or "") + " " + str((de or {}).get("memo_text") or ""))
        pattern = r"\bEARMARKED(?: \(NON-DIRECTED\))? (?:THROUGH|FROM) " + re.escape(conduit) + r"\b"
        if (not de or is_memo(de) or len(zip_o) != 5 or zip_o != zip_d or not conduit
                or not re.search(pattern, dd)):
            review("reciprocal_earmark_not_established", [origin, destination], "Retrieve both receipts and verify the stated conduit, donor, ZIP, date and amount.")
            continue
        proposals.append((origin, destination))
    usage = defaultdict(int)
    for pair in proposals:
        for sid in pair:
            usage[sid] += 1
    for origin, destination in proposals:
        if usage[origin] != 1 or usage[destination] != 1:
            review("overlapping_or_cyclic_earmark_links", [origin, destination], "Resolve the full multistage/allocated route before removing any representation.")
            continue
        exclude(destination, "same_original_gift_at_conduit_and_destination", origin, [origin, destination], "earmark")
        reason(origin, "retained_original_earmarked_receipt", [origin, destination])

    # Actual refund links are explicit evidence inputs; negative amounts and
    # promises to refund never establish returned money by themselves.
    refund_candidates = defaultdict(list)
    for sid, row in merged.items():
        d = decisions[sid]
        if d["status"] == "excluded_with_evidence" or d["amount_cents"] >= 0 or sid in conflicted:
            continue
        parent = str(row.get("refund_of_sub_id") or "")
        proof = str(row.get("adjustment_evidence_id") or "")
        p = merged.get(parent)
        valid = (_text(row.get("adjustment_type")) == "REFUND" and proof and p and parent not in conflicted
                 and decisions[parent]["counted_cents"] > 0
                 and _text(p.get("company")) == _text(row.get("company"))
                 and _text(p.get("contributor_name")) == _text(row.get("contributor_name"))
                 and p.get("committee_id") == row.get("committee_id")
                 and _day(p.get("contribution_receipt_date")) and _day(row.get("contribution_receipt_date"))
                 and _day(p["contribution_receipt_date"]) <= _day(row["contribution_receipt_date"]))
        if valid:
            refund_candidates[parent].append((sid, proof))
        else:
            review("signed_adjustment_not_linked_refund", [sid], "Identify whether this is a refund, reversal, redesignation or other correction and obtain its explicit counterpart.")
            reason(sid, "negative_amount_is_not_refund_proof")
    for parent, children in refund_candidates.items():
        if sum(abs(decisions[s]["amount_cents"]) for s, _ in children) > decisions[parent]["counted_cents"]:
            review("linked_refunds_exceed_original_gift", [parent, *(s for s, _ in children)], "Resolve duplicate or excess refund allocations before certifying the net amount.")
            continue
        for sid, proof in children:
            decisions[sid]["bucket"] = "linked_refund"
            reason(sid, "explicit_observed_refund", [parent, proof])
            links.append(dict(kind="refund", source_id=sid, counterpart_id=parent,
                              amount_cents=decisions[sid]["amount_cents"], evidence_ids=[parent, proof]))

    for (committee, file_num), ids in sorted(missing_family.items()):
        active = [s for s in ids if decisions[s]["status"] != "excluded_with_evidence"]
        if active:
            review("filing_relationship_evidence_missing", active, "Retrieve the filing header and enumerate its amendment family.", committee_id=committee, file_num=file_num)
    for family, members in sorted(family_members.items()):
        active = [s for s in members if decisions[s]["status"] != "excluded_with_evidence"]
        if active and family not in complete_families:
            review("latest_filing_completeness_unproven", active, "Establish the complete latest filing inventory, including records removed by amendment.", committee_id=family[0], root_file_num=family[1])

    # Resolved exclusions need no remaining row-specific review. Keep each
    # outstanding item actionable and deterministically deduplicate it.
    retained_reviews = []
    for item in reviews:
        active = [s for s in item["source_ids"] if s in decisions and
                  (decisions[s]["status"] != "excluded_with_evidence" or s in attribution_review)]
        if not active:
            continue
        item["source_ids"] = sorted(active)
        item["positive_cents"] = sum(max(0, decisions[s]["amount_cents"] if s in attribution_review else
                                         decisions[s]["counted_cents"] + decisions[s]["pac_activity_cents"]) for s in active)
        item["negative_cents"] = sum(min(0, decisions[s]["amount_cents"] if s in attribution_review else
                                         decisions[s]["counted_cents"] + decisions[s]["pac_activity_cents"]) for s in active)
        retained_reviews.append(item)
    reviews = sorted({_json(r): r for r in retained_reviews}.values(), key=_json)
    unresolved_ids = {s for r in reviews for s in r["source_ids"]}
    certificates = {}
    for certificate in filing_manifest.get("unique_origin_certificates", []):
        sid = str(certificate.get("source_id") or "")
        if sid in certificates and _json(certificates[sid]) != _json(certificate):
            raise ValueError(f"Conflicting unique-origin certificates: {sid}")
        certificates[sid] = certificate
    for sid, d in decisions.items():
        c = certificates.get(sid, {})
        if (sid not in unresolved_ids and sid not in conflicted and sid in evidence and d["counted_cents"] > 0
                and d["bucket"] in ("employee_original", "corporate_original")
                and "complete_latest_filing_inventory" in d["reasons"] and not is_memo(merged[sid])
                and d["receipt_role"] in ("contribution", "in_kind_contribution")
                and d["attribution_status"] != "unverified" and c.get("evidence_ids")
                and all(c.get(k) is True for k in ("filing_complete", "origin_verified", "routes_complete"))):
            d["supported_unique_cents"] = d["counted_cents"]
            d["status"] = "supported_by_supplied_completeness_evidence"
            reason(sid, "supplied_unique_origin_certificate", c["evidence_ids"])
        elif sid in attribution_review:
            d["status"] = "held_for_attribution_review"
        elif d["counted_cents"] or d["pac_activity_cents"]:
            d["status"] = "needs_review" if sid in unresolved_ids else "classified_provisional"
        d["reasons"] = sorted(set(d["reasons"]))
        d["evidence_ids"] = sorted(set(d["evidence_ids"]))

    result_rows = list(decisions.values())
    # Report the final retained representation even when a memo's immediate
    # parent was subsequently connected to an original conduit receipt.
    replacement = {link["source_id"]: link["counterpart_id"] for link in links if link["kind"] != "refund"}
    for link in links:
        current = link["counterpart_id"]
        seen = {link["source_id"]}
        while current in replacement:
            if current in seen:
                raise AssertionError("Cyclic accounting relationship")
            seen.add(current)
            current = replacement[current]
        if current in seen or current not in decisions:
            raise AssertionError("Invalid accounting counterpart")
        link["retained_source_id"] = current
        support_rows = sorted({link["source_id"], link["counterpart_id"], current})
        link["evidence_ids"] = sorted(set(link["evidence_ids"]) |
                                      {value for sid in support_rows for value in decisions[sid]["evidence_ids"]})
        link["field_evidence_ids"] = {sid: decisions[sid]["field_evidence_ids"] for sid in support_rows
                                      if decisions[sid]["field_evidence_ids"]}
        if link["kind"] in ("memo", "earmark") and not (
                decisions[current]["counted_cents"] or decisions[current]["pac_activity_cents"]):
            raise AssertionError("Duplicate exclusion lost its retained representation")
    counted = sum(d["counted_cents"] for d in result_rows)
    baseline = sum(d["baseline_cents"] for d in result_rows)
    changes = [dict(source_id=d["source_id"], baseline_cents=d["baseline_cents"], counted_cents=d["counted_cents"],
                    delta_cents=d["counted_cents"] - d["baseline_cents"], reasons=d["reasons"], evidence_ids=d["evidence_ids"])
               for d in result_rows if d["baseline_cents"] != d["counted_cents"]]
    totals = dict(baseline_receipt_cents=baseline, provisional_original_giving_cents=counted,
        observed_positive_original_candidate_cents=sum(max(0, d["counted_cents"]) for d in result_rows),
        observed_negative_adjustment_cents=sum(min(0, d["counted_cents"]) for d in result_rows),
        supported_unique_gross_cents=sum(d["supported_unique_cents"] for d in result_rows),
        pac_activity_observed_on_recipient_receipts_cents=sum(d["pac_activity_cents"] for d in result_rows),
        observed_linked_refund_cents=sum(d["counted_cents"] for d in result_rows if d["bucket"] == "linked_refund"),
        unresolved_positive_cents=sum(max(0, decisions[s]["amount_cents"] if s in attribution_review else
                                           decisions[s]["counted_cents"] + decisions[s]["pac_activity_cents"]) for s in unresolved_ids),
        unresolved_negative_cents=sum(min(0, decisions[s]["amount_cents"] if s in attribution_review else
                                           decisions[s]["counted_cents"] + decisions[s]["pac_activity_cents"]) for s in unresolved_ids),
        unresolved_source_records=len(unresolved_ids), source_records=len(result_rows))
    buckets = defaultdict(lambda: dict(counted_cents=0, pac_activity_cents=0, records=0))
    for d in result_rows:
        for field in ("counted_cents", "pac_activity_cents"):
            buckets[d["bucket"]][field] += d[field]
        buckets[d["bucket"]]["records"] += 1
    totals["by_bucket"] = dict(sorted(buckets.items()))
    arithmetic = baseline + sum(c["delta_cents"] for c in changes) == counted
    if not arithmetic:
        raise AssertionError("Integer-cent reconciliation failed")
    return dict(version=1, status="experimental_provisional", decisions=result_rows,
        links=sorted(links, key=_json), review_queue=reviews, changes=changes, totals=totals,
        checks=dict(integer_cent_reconciliation=arithmetic, unique_source_ids=True,
                    relationship_graph_acyclic=True, duplicate_exclusions_have_retained_representation=True,
                    identical_input_duplicates_coalesced=duplicate_count,
                    original_and_pac_buckets_disjoint=all(not (d["counted_cents"] and d["pac_activity_cents"]) for d in result_rows),
                    collection_completeness_established=False, overall_unique_dollars_established=False),
        scope="Stored accepted-company receipt candidates and supplied evidence only; PAC activity is recipient-reported, not a complete outgoing-spending ledger. Supported subset depends on independently established supplied certificates. No accuracy percentage is inferred.")
