#!/usr/bin/env python3
"""Assemble, per amendment, every local evidence surface needed to adjudicate it.

Decides nothing. Re-runs the query guard from query_guard_registry_v2.json using
the EXACT operator semantics of fec/match_with_query_guards.py -- windowed
containsAll, the domain-anchor requirement for generic terms, bill-number
suppression, and notContains exclusions -- and keeps a context window around
every hit so the reader can tell an operative statutory reference from an
incidental co-occurrence.

Two differences from the original producer, both required by the binding method:

  * the amendment's OWN official purpose line (congress.gov "Purpose:") joins
    the operative-text surface. The original producer read `declared_purpose`,
    a field amendment_content_v2.ndjson does not carry, so that surface was
    silently empty in the v2 run.
  * floor remarks are scanned but recorded on a SEPARATE surface. The original
    producer let a remarks-only hit establish domain (18 of its 170). Rule 3
    says remarks are context, never a substitute for operative text, so here a
    remarks-only hit routes to review, not to inclusion.

Read-only over every input. Writes one NDJSON under this directory.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from collections import Counter, defaultdict

OUT_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(OUT_DIR))
from canon import CANONICAL_IDS, canonicalise  # noqa: E402
EV = pathlib.Path(
    r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\legfix5\opus_adjudication\original_method_evidence"
)
SIDE = pathlib.Path(
    r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\legfix5\short_act_collision_sidecar"
)
IN = pathlib.Path(r"C:\Users\pgoff\AppData\Local\Temp\claude\cxwt-acu-registry")

WORD_RE = re.compile(r"[A-Za-z0-9']+")
SHORT_SURFACE_TOKENS = 400
CONTAINS_ALL_WINDOW = 30

SPECIFIC_RE = re.compile(
    r"credit union|ncua|share insurance|federal credit union act|cdfi"
    r"|community development financial|cfpb|consumer financial protection"
    r"|interchange|durbin|field of membership|member business|overdraft"
    r"|bank secrecy|call report|ffiec|camels|truth in lending|gramm-leach"
    r"|home mortgage disclosure|regulation e|regulation z|stablecoin"
    r"|central bank digital|telephone consumer protection|tcpa"
    r"|military lending|share draft|usury|payday", re.I)
BILL_NUMBER_ONLY_RE = re.compile(
    r"^(?:H\.?\s?R\.?|S\.?|H\.?J\.?\s?Res\.?|S\.?J\.?\s?Res\.?)\s*\d+$", re.I)


def load_json(path: pathlib.Path):
    return json.loads(path.read_bytes().decode("utf-8-sig"))


def load_ndjson(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def _stem(tok: str) -> str:
    if len(tok) > 3 and tok.endswith("ies"):
        return tok[:-3] + "y"
    if len(tok) > 3 and tok.endswith("ses"):
        return tok[:-2]
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def tokenize_spans(text: str, *, lower: bool, stem: bool):
    toks, spans = [], []
    for m in WORD_RE.finditer(text or ""):
        t = m.group(0)
        if lower:
            t = t.lower()
        if stem:
            t = _stem(t)
        toks.append(t)
        spans.append((m.start(), m.end()))
    return toks, spans


class Surface:
    def __init__(self, text: str) -> None:
        self.text = text
        self.stem_lower, self.sp_stem = tokenize_spans(text, lower=True, stem=True)
        self.nostem_lower, self.sp_nostem = tokenize_spans(text, lower=True, stem=False)
        self.case, self.sp_case = tokenize_spans(text, lower=False, stem=False)
        self.stem_lower_set = set(self.stem_lower)
        self.nostem_lower_set = set(self.nostem_lower)
        self.case_set = set(self.case)

    def view(self, term):
        if term["case_sensitive"]:
            return self.case, self.case_set, self.sp_case
        if not term["stem"]:
            return self.nostem_lower, self.nostem_lower_set, self.sp_nostem
        return self.stem_lower, self.stem_lower_set, self.sp_stem


def contiguous_at(hay, needle):
    n = len(needle)
    if not n or n > len(hay):
        return -1
    first = needle[0]
    for i, tok in enumerate(hay):
        if tok == first and hay[i:i + n] == needle:
            return i
    return -1


def all_within_window(hay, needle, window):
    """Returns the anchor index of a satisfying window, or -1."""
    positions = []
    for term in needle:
        idx = [i for i, tok in enumerate(hay) if tok == term]
        if not idx:
            return -1
        positions.append(idx)
    anchors = min(positions, key=len)
    for start in anchors:
        lo, hi = start - window, start + window
        if all(any(lo <= i <= hi for i in idx) for idx in positions):
            return start
    return -1


def window_text(surface: Surface, spans, i_lo: int, i_hi: int, pad: int = 150) -> str:
    if not spans:
        return ""
    i_lo = max(0, min(i_lo, len(spans) - 1))
    i_hi = max(0, min(i_hi, len(spans) - 1))
    a = max(0, spans[i_lo][0] - pad)
    b = min(len(surface.text), spans[i_hi][1] + pad)
    return " ".join(surface.text[a:b].split())


def term_hit(surface: Surface, term: dict):
    """(hit, window) with the producer's exact acceptance rule."""
    seq, bag, spans = surface.view(term)
    needle, _ = tokenize_spans(
        term["value"], lower=not term["case_sensitive"], stem=term["stem"])
    if not needle:
        return False, ""
    if term["contiguous"]:
        i = contiguous_at(seq, needle)
        if i < 0:
            return False, ""
        return True, window_text(surface, spans, i, i + len(needle) - 1)
    if not all(t in bag for t in needle):
        return False, ""
    if len(needle) == 1 or len(seq) <= SHORT_SURFACE_TOKENS:
        i = seq.index(needle[0])
        return True, window_text(surface, spans, i, i)
    i = all_within_window(seq, needle, CONTAINS_ALL_WINDOW)
    if i < 0:
        return False, ""
    return True, window_text(surface, spans, max(0, i - CONTAINS_ALL_WINDOW),
                             min(len(spans) - 1, i + CONTAINS_ALL_WINDOW), pad=0)


def term_is_specific(term: dict) -> bool:
    if BILL_NUMBER_ONLY_RE.match(term["value"].strip()):
        return False
    return bool(SPECIFIC_RE.search(term["value"]))


def scan(surface: Surface | None, cats, has_anchor: bool):
    """{category_id: {'terms': [...], 'excluded': bool}} for one surface.

    Category IDs are emitted in the CANONICAL vocabulary. The frozen guard
    registry carries two noncanonical source aliases, and canonicalising here --
    at the only point where a category ID enters this lane -- is what keeps the
    aliases out of every downstream artifact.
    """
    got: dict[str, dict] = {}
    if surface is None:
        return got
    for cat in cats:
        cid = canonicalise(cat["category_id"])
        if cid not in CANONICAL_IDS:
            raise SystemExit(f"guard registry category {cat['category_id']!r} is not canonical")
        hits = []
        for term in cat["terms"]:
            if BILL_NUMBER_ONLY_RE.match(term["value"].strip()):
                continue
            if not term_is_specific(term) and not has_anchor:
                continue
            ok, win = term_hit(surface, term)
            if ok:
                hits.append({"term": term["value"], "operator": term["operator"],
                             "specific": term_is_specific(term), "window": win[:420]})
        if not hits:
            continue
        blocked = None
        for term in cat.get("exclusions") or []:
            probe = dict(term)
            probe["contiguous"] = False
            ok, _ = term_hit(surface, probe)
            if ok:
                blocked = term["value"]
                break
        got[cid] = {"terms": hits, "excluded_by": blocked}
    return got


def main() -> int:
    content = load_ndjson(EV / "amendment_content_v2.ndjson")
    queue = {r["canonical_key"]: r for r in load_ndjson(EV / "amendment_review_queue.ndjson")}
    meta = load_json(IN / "audits_out" / "media_link" / "amend_meta.json")
    guards = load_json(EV / "query_guard_registry_v2.json")
    cats = guards["categories"]
    press_pairs = load_json(EV / "press_amendment_pairs.json")
    strict = set(load_json(EV / "press_strict_union_keys.json"))
    rescue = {r["canonical_key"]: r for r in load_json(EV / "floor_speech_rescue_310.json")}
    sidecar = load_ndjson(SIDE / "short_act_collision_sidecar.ndjson")

    side_by_key = defaultdict(list)
    for r in sidecar:
        side_by_key[r["canonical_key"]].append(
            {"query_id": r["query_id"], "probe_alias": r.get("probe_alias")})

    press_by_key = defaultdict(list)
    for row in press_pairs:
        if isinstance(row, list) and row:
            press_by_key[row[0]].append({
                "parent": row[1] if len(row) > 1 else None,
                "url": row[2] if len(row) > 2 else None,
                "title": row[3] if len(row) > 3 else None,
                "article_date": row[4] if len(row) > 4 else None,
                "amendment_date": row[5] if len(row) > 5 else None,
                "article_label": row[6] if len(row) > 6 else None,
            })

    out_path = OUT_DIR / "evidence_index.ndjson"
    tally = Counter()
    with open(out_path, "w", encoding="utf-8", newline="\n") as sink:
        for rec in content:
            key = rec["canonical_key"]
            raw_text = rec.get("amendment_text") or ""
            m = meta.get(key, {})
            purpose = re.sub(r"^Purpose:\s*", "", (m.get("purpose") or "").strip()).strip()
            purpose = re.sub(r"\s*\|\s*View Text\s*$", "", purpose).strip()
            placeholder = (
                not purpose
                or purpose.lower().startswith("purpose displays after")
                or purpose.lower().rstrip(".") == "in the nature of a substitute"
            )
            remarks = rec.get("floor_remarks") or ""

            operative = " ".join(x for x in (raw_text, purpose) if x)
            has_anchor_op = bool(SPECIFIC_RE.search(operative))
            has_anchor_rm = bool(SPECIFIC_RE.search(remarks))

            s_op = Surface(operative) if operative.strip() else None
            s_rm = Surface(remarks) if remarks.strip() else None
            hit_op = scan(s_op, cats, has_anchor_op)
            hit_rm = scan(s_rm, cats, has_anchor_rm)

            live_op = sorted(c for c, v in hit_op.items() if not v["excluded_by"])
            live_rm = sorted(c for c, v in hit_rm.items() if not v["excluded_by"])

            text_available = bool(raw_text.strip())
            tally["text_available" if text_available else "text_missing"] += 1
            if live_op:
                tally["guard_hit_operative"] += 1
            if live_rm and not live_op:
                tally["guard_hit_remarks_only"] += 1
            if not text_available and purpose and not placeholder:
                tally["no_text_but_substantive_purpose"] += 1

            q = queue.get(key)
            sink.write(json.dumps({
                "canonical_key": key,
                "congress": rec.get("congress"),
                "measure_type": rec.get("measure_type"),
                "number": rec.get("number"),
                "sponsor": rec.get("sponsor"),
                "amends": rec.get("amends") or m.get("amends"),
                "latest_action": rec.get("latest_action") or m.get("latest_action"),
                "action_date": m.get("date"),
                "official_purpose": purpose,
                "purpose_is_placeholder": placeholder,
                "text_available": text_available,
                "text_len": rec.get("amendment_text_len") or 0,
                "text_sha256": rec.get("amendment_text_sha256"),
                "text_unresolved_reason": rec.get("text_unresolved_reason"),
                "text_head": " ".join(raw_text.split())[:1600],
                "operative_anchor_present": has_anchor_op,
                "guard_operative": hit_op,
                "guard_operative_categories": live_op,
                "guard_remarks": hit_rm,
                "guard_remarks_categories": live_rm,
                "in_review_queue": q is not None,
                "review_tier": (q or {}).get("review_tier"),
                "prior_queue_guarded_categories": (q or {}).get("guarded_categories") or [],
                "in_strict_sweep": key in strict,
                "floor_rescue_tier": (rescue.get(key) or {}).get("tier"),
                "floor_remarks_len": rec.get("floor_remarks_len") or 0,
                "floor_remarks_head": " ".join(remarks.split())[:1200],
                "press_direct": press_by_key.get(key, []),
                "sidecar_collisions": side_by_key.get(key, []),
                "speech_cell_size": (q or {}).get("speech_cell_size"),
                "speech_attributable": (q or {}).get("speech_attributable"),
            }, ensure_ascii=False) + "\n")

    print(json.dumps(dict(tally), indent=1))
    print("wrote", out_path, out_path.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
