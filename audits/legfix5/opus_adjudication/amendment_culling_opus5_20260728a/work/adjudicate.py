#!/usr/bin/env python3
"""Apply the adjudication to all 3,703 amendments and emit the immutable outputs.

Every row lands on a NAMED rule. Rows that reach a pool default are printed so
they can be pulled back into an individual ruling; the run is not finished while
any carded row is sitting on an unreviewed default.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent
EV = pathlib.Path(
    r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\legfix5\opus_adjudication\original_method_evidence")
SIDE = pathlib.Path(
    r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\legfix5\short_act_collision_sidecar")
IN = pathlib.Path(r"C:\Users\pgoff\AppData\Local\Temp\claude\cxwt-acu-registry")

sys.path.insert(0, str(HERE))
from decisions import PER_KEY, FAMILY_SIGNATURES, INC, EXC, FLG  # noqa: E402

from canon import CANONICAL_IDS, canonicalise_all  # noqa: E402

# The canonical nineteen are DERIVED in canon.py from the frozen guard registry
# plus the production alias map, never retyped here. A hand-written copy is what
# let two noncanonical aliases into this lane in the first place.
CANON19 = sorted(CANONICAL_IDS)

VAGUE_PURPOSE = re.compile(
    r"^(to improve the bill|to modify the bill|of a perfecting nature"
    r"|to provide for a complete substitute|in the nature of a substitute"
    r"|purpose displays after)", re.I)

# Vocabulary that a purely positional edit is made of. An amendment whose whole
# text is exhausted by this vocabulary states no subject of its own: "Page 24,
# line 6, after the dollar amount, insert ``(increased by $5,000,000)''" does
# not say which account it moves. Text being present does not make it readable,
# so such a row is preserved for review, never culled.
EDIT_VOCAB = set("""page pages line lines strike striking insert inserting insertion add adding added
redesignate redesignating following follows all that after before through end beginning at in on of to
a an the and or by as is are be shall section sections subsection subsections paragraph paragraphs
subparagraph subparagraphs clause clauses item items period semicolon comma colon quotation mark marks
dollar amount amounts first second third each place places appropriate matter preceding reduced increased
respectively such this act bill division title titles s h r amdt sec no not it its part parts chapter
united states code public law stat note et seq also may with for from where under text word words figure
figures number numbers new same other so designated redesignated""".split())
NUMERIC = re.compile(r"^[\divxlcIVXLC.,$%()\-–—/]+$")
BRACKET = re.compile(r"\[\[.*?\]\]")
TOKEN = re.compile(r"[A-Za-z][A-Za-z'\-]*|\d[\d,.]*")


def content_tokens(text: str) -> list[str]:
    out = []
    for w in TOKEN.findall(BRACKET.sub(" ", text or "")):
        if w.lower() in EDIT_VOCAB or NUMERIC.match(w):
            continue
        out.append(w)
    return out


def is_pointer_edit(rec: dict) -> bool:
    if not rec["text_available"] or rec["text_len"] > 1600:
        return False
    if rec["guard_operative_categories"] or rec["operative_anchor_present"]:
        return False
    return len(content_tokens(rec.get("text_head") or "")) <= 3


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rule_for(rec: dict, pool: str | None) -> tuple:
    """(disposition, categories, direction, confidence, rule_id, reason, is_default)"""
    key = rec["canonical_key"]
    if key in PER_KEY:
        d, c, dr, cf, rid, why = PER_KEY[key]
        return d, c, dr, cf, rid, why, False

    head = (rec.get("text_head") or "") + " " + (rec.get("official_purpose") or "")
    for rx, d, c, dr, cf, rid, why in FAMILY_SIGNATURES:
        if re.search(rx, head, re.I):
            return d, c, dr, cf, rid, why, False

    text_ok = rec["text_available"]
    gcats = rec["guard_operative_categories"]
    purpose = rec["official_purpose"]
    vague = (not purpose) or bool(VAGUE_PURPOSE.match(purpose))
    parent = re.sub(r"^Amends Bill:\s*", "", rec.get("amends") or "").strip()

    # An internal edit to a single-subject bill: the amendment's own operative
    # effect is a change to that subject, but reading its text alone cannot say
    # so. Parent text is used to CONSTRUE the edit, never to inherit the
    # parent's relevance or direction, which stays barred by rule 1.
    if text_ok and parent == "S.1582" and not gcats:
        return (FLG, ["payments", "technology_emerging_issues"], None, "low", "D-GENIUS-INTERNAL",
                "internal edit to the GENIUS Act payment-stablecoin statute; the payments and "
                "technology domain connection is real once the edit is construed against the "
                "measure it operates on, but ACU's recorded amendment-level positions on this "
                "vehicle name only the Marshall interchange and Hawley rate-cap amendments, so "
                "this amendment's own direction is unresolved", True)

    if is_pointer_edit(rec):
        return (FLG, [], None, "low", "D-POINTER-UNRESOLVED",
                "the amendment's entire operative text is a positional edit — a page-and-line "
                "pointer, a dollar-figure adjustment or a bare section strike — that states no "
                "subject of its own; text being present does not make it readable, so the row is "
                "preserved for review rather than culled on an absence of signal", True)

    # ---- pool defaults, each with its own named rule ----
    if pool is None:
        if text_ok:
            return (EXC, [], None, "medium", "D-NOSIGNAL",
                    "official amendment text is on file and carries no operative connection to any "
                    "of the 19 ACU categories: no query-guard identifier on its own text or purpose, "
                    "no credit-union domain anchor, no broad financial-regulatory sweep phrase, no "
                    "short-act collision flag and no ACU press identification", True)
        if not vague:
            return (EXC, [], None, "medium", "D-PURPOSE-OFFDOMAIN",
                    "amendment text is unavailable, but the amendment's own official congress.gov "
                    "purpose statement resolves its subject and places it outside all 19 ACU "
                    "categories; this is an evidence-based exclusion, not an absence-based one", True)
        return (FLG, [], None, "low", "D-NOTEXT",
                "amendment text is unavailable and no amendment-specific official or press evidence "
                "resolves it, so it is preserved for review rather than excluded", True)

    if pool == "P4_notext_substantive_purpose":
        if vague:
            return (FLG, [], None, "low", "D-VAGUE-PURPOSE",
                    "amendment text is unavailable and the official purpose statement is a "
                    "non-substantive formula, so the amendment's effect is unresolved", True)
        return (EXC, [], None, "medium", "D-PURPOSE-OFFDOMAIN",
                "amendment text is unavailable, but the amendment's own official congress.gov "
                "purpose statement resolves its subject and places it outside all 19 ACU "
                "categories; this is an evidence-based exclusion, not an absence-based one", True)

    if pool == "P6_sidecar_collision" and not text_ok:
        return (FLG, [], None, "low", "D-SIDECAR-NOTEXT",
                "carries a short-act-collision sidecar flag and has no recoverable amendment text; "
                "the collision is a reason to doubt the membership, never a reason to cull it "
                "without text", True)

    if not text_ok:
        return (FLG, [], None, "low", "D-NOTEXT-QUEUE",
                "queued for review but the amendment text is unavailable; floor remarks are "
                "sponsor context and cannot substitute for operative text, so the row is "
                "preserved for review rather than resolved", True)

    if pool in ("P1_press_direct", "P2_guard_operative") and gcats:
        fired = " ".join(t["term"] for v in rec["guard_operative"].values() for t in v["terms"])
        stable = re.search(r"payment stablecoin|GENIUS Act", fired + " " + head, re.I)
        if stable:
            return (FLG, sorted(set(canonicalise_all(gcats)) & CANONICAL_IDS), None, "low", "D-STABLE-OPEN",
                    "operatively amends payment-stablecoin provisions, so the payments and "
                    "technology domain connection is direct and real; ACU's only recorded "
                    "amendment-level positions on this vehicle name two other amendments, and a "
                    "preference for a clean bill is a statement about the vehicle, which rule 1 "
                    "bars from transferring direction to this amendment", True)
        return (FLG, sorted(set(canonicalise_all(gcats)) & CANONICAL_IDS), None, "low", "D-GUARD-UNRULED",
                "query-guard identifier fires on the amendment's own operative text but the row "
                "was not individually ruled; preserved for review", True)

    if pool == "P1_press_direct":
        return (EXC, [], None, "medium", "D-PRESS-NOTNAMED",
                "the press pairing is a parent-bill plus sponsor plus thirty-day proximity link, "
                "not a direct identification of this amendment, so under rule 4 it establishes "
                "nothing; the amendment's own text carries no category connection", True)

    return (EXC, [], None, "medium", "D-QUEUE-NOSIGNAL",
            "queued by the broad financial-regulatory sweep or the floor-speech rescue, but the "
            "amendment's own operative text carries no connection to any of the 19 ACU "
            "categories", True)


def main() -> int:
    rows = [json.loads(l) for l in open(HERE / "evidence_index.ndjson", encoding="utf-8")]
    pools = json.loads((HERE / "cards" / "_pools.json").read_text(encoding="utf-8"))["assigned"]
    queue_keys = [json.loads(l)["canonical_key"]
                  for l in open(EV / "amendment_review_queue.ndjson", encoding="utf-8") if l.strip()]

    decided, defaults_hit = {}, defaultdict(list)
    for rec in rows:
        key = rec["canonical_key"]
        d, cats, direction, conf, rid, why, is_default = rule_for(rec, pools.get(key))
        cats = [c for c in canonicalise_all(cats) if c in CANONICAL_IDS]
        if d == INC and direction not in (1, -1):
            d = FLG
            rid += "+NODIR"
        if d == FLG:
            direction = None
        if d == EXC:
            cats, direction = [], None
        decided[key] = {
            "disposition": d, "category_ids": cats, "ultimate_direction": direction,
            "confidence": conf, "rule_id": rid, "reason": why, "rec": rec,
        }
        if is_default and key in pools:
            defaults_hit[rid].append(key)

    print("=== carded rows resting on a pool default ===")
    for rid, ks in sorted(defaults_hit.items(), key=lambda kv: -len(kv[1])):
        print(f"  {rid:24s} {len(ks):4d}  {ks[:8]}")
    print()

    # ---------------- evidence binding ----------------
    ev_files = sorted(p for p in EV.iterdir() if p.is_file())
    side_files = sorted(p for p in SIDE.iterdir() if p.is_file())
    meta_file = IN / "audits_out" / "media_link" / "amend_meta.json"
    src_files = [IN / "fec" / n for n in (
        "build_amendment_review_queue.py", "adjudicate_amendment_queue.py",
        "decide_amendment_domain.py", "match_with_query_guards.py")]
    prior = [IN / "audits_out" / "amendments" / n for n in (
        "amendment_domain_verdict_v2.json", "amendment_guarded_v2.json",
        "amendment_adjudicated.ndjson")]

    inputs = {}
    for p in ev_files + side_files + [meta_file] + src_files + prior:
        inputs[str(p)] = {"bytes": p.stat().st_size, "sha256": sha256(p)}

    ev_ids = {p.name: f"sha256:{inputs[str(p)]['sha256']}" for p in ev_files}
    ev_ids["amend_meta.json"] = f"sha256:{inputs[str(meta_file)]['sha256']}"
    ev_ids["short_act_collision_sidecar.ndjson"] = (
        f"sha256:{inputs[str(SIDE / 'short_act_collision_sidecar.ndjson')]['sha256']}")

    def evidence_for(rec: dict) -> tuple[list, list]:
        ids, paths = [], []
        ids.append("amendment_content_v2.ndjson#" + rec["canonical_key"])
        paths.append({"artifact": "amendment_content_v2.ndjson",
                      "sha256": ev_ids["amendment_content_v2.ndjson"].split(":")[1],
                      "path": str(EV / "amendment_content_v2.ndjson")})
        if rec["text_available"]:
            ids.append("amendment_text_sha256:" + (rec["text_sha256"] or ""))
        if rec["official_purpose"]:
            ids.append("amend_meta.json#" + rec["canonical_key"] + "/purpose")
            paths.append({"artifact": "amend_meta.json",
                          "sha256": ev_ids["amend_meta.json"].split(":")[1],
                          "path": str(meta_file)})
        if rec["guard_operative_categories"]:
            ids.append("query_guard_registry_v2.json#" + ",".join(rec["guard_operative_categories"]))
            paths.append({"artifact": "query_guard_registry_v2.json",
                          "sha256": ev_ids["query_guard_registry_v2.json"].split(":")[1],
                          "path": str(EV / "query_guard_registry_v2.json")})
        if rec["press_direct"]:
            for e in rec["press_direct"]:
                ids.append("press_amendment_pairs.json#" + (e.get("url") or ""))
            paths.append({"artifact": "press_amendment_pairs.json",
                          "sha256": ev_ids["press_amendment_pairs.json"].split(":")[1],
                          "path": str(EV / "press_amendment_pairs.json")})
            paths.append({"artifact": "press_text_cache.jsonl",
                          "sha256": ev_ids["press_text_cache.jsonl"].split(":")[1],
                          "path": str(EV / "press_text_cache.jsonl")})
        if rec["sidecar_collisions"]:
            ids.append("short_act_collision_sidecar.ndjson#" + rec["canonical_key"])
            paths.append({"artifact": "short_act_collision_sidecar.ndjson",
                          "sha256": ev_ids["short_act_collision_sidecar.ndjson"].split(":")[1],
                          "path": str(SIDE / "short_act_collision_sidecar.ndjson")})
        if rec["floor_remarks_len"]:
            ids.append("amendment_content_v2.ndjson#" + rec["canonical_key"] + "/floor_remarks")
        ids.append("acu_category_registry.json#positions")
        paths.append({"artifact": "acu_category_registry.json",
                      "sha256": ev_ids["acu_category_registry.json"].split(":")[1],
                      "path": str(EV / "acu_category_registry.json")})
        return ids, paths

    def row_for(key: str) -> dict:
        d = decided[key]
        rec = d["rec"]
        ids, paths = evidence_for(rec)
        press_used = d["rule_id"] in ("R-CCCA-PRESS", "R-RATECAP-PRESS")
        return {
            "canonical_key": key,
            "disposition": d["disposition"],
            "category_ids": d["category_ids"],
            "ultimate_direction": d["ultimate_direction"],
            "amendment_weight": 0.5,
            "evidence_ids": ids,
            "evidence_paths": paths,
            "reason": d["reason"],
            "rule_id": d["rule_id"],
            "confidence": d["confidence"],
            "text_available": rec["text_available"],
            "floor_evidence_used": False,
            "press_evidence_used": press_used,
            "parent_context_used": d["rule_id"] in ("D-GENIUS-INTERNAL", "F-OMNIBUS-SUB"),
            "parent_relevance_transferred": False,
            "automated_final_decision": False,
            "human_ratification_required": True,
            "measure_type": rec["measure_type"],
            "congress": rec["congress"],
            "sponsor": rec["sponsor"],
            "parent_measure_context_only": re.sub(r"^Amends Bill:\s*", "", rec["amends"] or ""),
            "review_pool": pools.get(key),
            "prior_original_method_verdict": "IN" if rec["guard_operative_categories"] or
                                                     rec["guard_remarks_categories"] else "OUT",
        }

    OUT.mkdir(parents=True, exist_ok=True)
    p419 = OUT / "proposal_adjudications_419.ndjson"
    with open(p419, "w", encoding="utf-8", newline="\n") as fh:
        for k in queue_keys:
            fh.write(json.dumps(row_for(k), ensure_ascii=False) + "\n")

    p3703 = OUT / "amendment_partition_3703.ndjson"
    with open(p3703, "w", encoding="utf-8", newline="\n") as fh:
        for rec in rows:
            r = row_for(rec["canonical_key"])
            r["in_review_queue"] = rec["in_review_queue"]
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    pflag = OUT / "flagged_amendments.ndjson"
    nflag = 0
    with open(pflag, "w", encoding="utf-8", newline="\n") as fh:
        for rec in rows:
            if decided[rec["canonical_key"]]["disposition"] != FLG:
                continue
            r = row_for(rec["canonical_key"])
            r["flag_class"] = r["rule_id"]
            r["unavailable_text_subset"] = not rec["text_available"]
            r["official_purpose"] = rec["official_purpose"]
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
            nflag += 1

    disp = Counter(d["disposition"] for d in decided.values())
    print("partition:", dict(disp), "flagged file rows:", nflag)
    stats = {
        "decided": decided, "inputs": inputs, "queue_keys": queue_keys,
        "disp": dict(disp), "outputs": [p419, p3703, pflag],
    }
    json.dump({k: v for k, v in stats.items() if k in ("inputs", "disp")},
              open(HERE / "_run_stats.json", "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
