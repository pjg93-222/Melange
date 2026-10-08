#!/usr/bin/env python3
"""Turn the evidence index into human/Opus-readable review cards.

One card per amendment that needs a semantic ruling. Cards are grouped into
review pools by the STRONGEST evidence surface present, because different
surfaces need different things read: a guard hit needs its context window, a
press pair needs the article framing, a no-text row needs its official purpose.

Also recomputes the broad strict-sweep families (the ~40%-precision review net
from audits_out/press_sweep/refine.py) so a sweep-only row carries the reason it
was ever queued instead of arriving as a bare key.

Read-only over evidence_index.ndjson. Writes card files under ./cards/.
"""
from __future__ import annotations

import json
import pathlib
import re
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
CARDS = HERE / "cards"
I = re.IGNORECASE

STRICT_FAMILIES = [
    ("CU_CORE", [(r"\bcredit\s+unions?\b", I), (r"\bNCUA\b", 0), (r"\bshare\s+insurance\b", I),
                 (r"\bFederal\s+Credit\s+Union\s+Act\b", I), (r"\bmember\s+business\s+loans?\b", I),
                 (r"\bfield\s+of\s+membership\b", I)]),
    ("CFPB", [(r"\bCFPB\b", 0), (r"\bConsumer\s+Financial\s+Protection\s+(Act|Bureau)\b", I),
              (r"\bBureau\s+of\s+Consumer\s+Financial\s+Protection\b", I)]),
    ("INTERCHANGE", [(r"\bpayment\s+card\s+network", I), (r"\bswipe\s+fees?\b", I),
                     (r"\bDurbin\s+amendment\b", I), (r"\binterchange\s+(fee|transaction\s+fee|rate)", I),
                     (r"\bCredit\s+Card\s+Competition\s+Act\b", I)]),
    ("BSA_AML_FI", [(r"\bBank\s+Secrecy\s+Act\b", I), (r"\bsuspicious\s+activity\s+reports?\b", I),
                    (r"\bcurrency\s+transaction\s+reports?\b", I),
                    (r"\bbeneficial\s+ownership\s+(information|report)", I)]),
    ("CDFI", [(r"\bCDFIs?\b", 0), (r"\bcommunity\s+development\s+financial\s+institution", I),
              (r"\bminority\s+depository\s+institution", I)]),
    ("STABLECOIN_CBDC", [(r"\bpayment\s+stablecoin", I), (r"\bstablecoins?\b", I), (r"\bCBDC\b", 0),
                         (r"\bcentral\s+bank\s+digital\s+currency\b", I)]),
    ("TILA_REGZ", [(r"\bTruth\s+in\s+Lending\b", I), (r"\bRegulation\s+Z\b", I), (r"\bTILA\b", 0)]),
    ("REG_E_EFTA", [(r"\bRegulation\s+E\b", I), (r"\bElectronic\s+Fund(s)?\s+Transfer\s+Act\b", I),
                    (r"\bEFTA\b", 0), (r"\bremittance\s+transfer", I)]),
    ("HMDA", [(r"\bHMDA\b", 0), (r"\bHome\s+Mortgage\s+Disclosure\b", I)]),
    ("GLBA", [(r"\bGLBA\b", 0), (r"\bGramm[- ]Leach[- ]Bliley\b", I)]),
    ("FHLB", [(r"\bFHLBank?s?\b", I), (r"\bFederal\s+Home\s+Loan\s+Bank", I)]),
    ("OVERDRAFT_CONSUMER_FEE", [(r"\boverdraft\s+(fee|protection|program|charge)", I),
                                (r"\bpayday\s+(loan|lend|lender)", I), (r"\bsmall[- ]dollar\s+loan", I),
                                (r"\busury\b", I), (r"\bcredit\s+card\s+late\s+fee", I),
                                (r"\bjunk\s+fees?\b", I)]),
    ("TCPA", [(r"\bTCPA\b", 0), (r"\bTelephone\s+Consumer\s+Protection\s+Act\b", I), (r"\brobocall", I),
              (r"\bautomatic\s+telephone\s+dialing", I)]),
    ("DATA_FIN", [(r"\bdata\s+brokers?\b", I), (r"\btrigger\s+leads?\b", I),
                  (r"\bFair\s+Credit\s+Reporting\s+Act\b", I), (r"\bconsumer\s+report(ing)?\s+agenc", I),
                  (r"\bdata\s+breach\s+notification\b", I)]),
    ("FLOOD_NFIP", [(r"\bNFIP\b", 0), (r"\bNational\s+Flood\s+Insurance\b", I), (r"\bflood\s+insurance\b", I)]),
    ("MLA_SCRA_FIN", [(r"\bMilitary\s+Lending\s+Act\b", I),
                      (r"\bServicemembers?\s+Civil\s+Relief\s+Act\b", I)]),
]
SC = [(n, [re.compile(p, f) for p, f in ps]) for n, ps in STRICT_FAMILIES]

ANCHOR_RE = re.compile(
    r"credit union|ncua|share insurance|federal credit union act|cdfi"
    r"|community development financial|cfpb|consumer financial protection"
    r"|interchange|durbin|field of membership|member business|overdraft"
    r"|bank secrecy|call report|ffiec|camels|truth in lending|gramm-leach"
    r"|home mortgage disclosure|regulation e|regulation z|stablecoin"
    r"|central bank digital|telephone consumer protection|tcpa"
    r"|military lending|share draft|usury|payday", re.I)

FULL_TEXT: dict[str, str] = {}


def load_full_text() -> None:
    p = pathlib.Path(
        r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\legfix5\opus_adjudication"
        r"\original_method_evidence\amendment_content_v2.ndjson")
    for line in open(p, encoding="utf-8"):
        if line.strip():
            j = json.loads(line)
            FULL_TEXT[j["canonical_key"]] = j.get("amendment_text") or ""


def windows(text: str, rx: re.Pattern, pad: int = 130, limit: int = 3) -> list[str]:
    out = []
    for m in rx.finditer(text or ""):
        a, b = max(0, m.start() - pad), min(len(text), m.end() + pad)
        out.append(" ".join(text[a:b].split()))
        if len(out) >= limit:
            break
    return out


def strict_hits(text: str) -> dict[str, list[str]]:
    got = {}
    for name, pats in SC:
        wins = []
        for p in pats:
            wins += windows(text, p, limit=1)
            if wins:
                break
        if wins:
            got[name] = wins
    return got


def short_action(s: str) -> str:
    s = re.sub(r"^Latest Action:\s*", "", s or "")
    s = re.sub(r"\s*\(All Actions\)\s*$", "", s)
    return " ".join(s.split())[:150]


def card(r: dict, pool: str) -> dict:
    key = r["canonical_key"]
    text = FULL_TEXT.get(key, "")
    c = {
        "k": key,
        "pool": pool,
        "type": r["measure_type"],
        "sponsor": (r["sponsor"] or "")[:48],
        "amends": re.sub(r"^Amends Bill:\s*", "", r["amends"] or "")[:40],
        "action": short_action(r["latest_action"]),
        "tier": r["review_tier"],
        "textlen": r["text_len"],
    }
    if r["official_purpose"]:
        c["purpose"] = r["official_purpose"][:400]
    if r["guard_operative_categories"] or r["guard_operative"]:
        g = {}
        for cid, v in r["guard_operative"].items():
            g[cid + ("  [EXCLUDED:" + v["excluded_by"] + "]" if v["excluded_by"] else "")] = [
                {"t": t["term"], "op": t["operator"][:4], "spec": t["specific"], "w": t["window"][:300]}
                for t in v["terms"][:3]
            ]
        c["guard_text"] = g
    if r["guard_remarks_categories"]:
        c["guard_remarks"] = {
            cid: [t["term"] for t in v["terms"][:4]]
            for cid, v in r["guard_remarks"].items() if not v["excluded_by"]
        }
    if r["press_direct"]:
        c["press"] = [{"title": e["title"], "label": e["article_label"], "url": (e["url"] or "")[:95],
                       "adate": e["article_date"], "amdate": e["amendment_date"]}
                      for e in r["press_direct"]]
    if r["sidecar_collisions"]:
        c["sidecar"] = [f'{e["query_id"]}<-{e["probe_alias"]}' for e in r["sidecar_collisions"]]
    if r["in_strict_sweep"]:
        c["strict"] = strict_hits(text)
    if r["operative_anchor_present"] and not r["guard_operative_categories"]:
        c["anchor_windows"] = windows(text + " " + (r["official_purpose"] or ""), ANCHOR_RE, limit=3)
    if text:
        c["head"] = " ".join(text.split())[:900]
    if not r["text_available"] and r["floor_remarks_len"]:
        c["remarks"] = r["floor_remarks_head"][:700]
    return c


def main() -> int:
    load_full_text()
    rows = [json.loads(l) for l in open(HERE / "evidence_index.ndjson", encoding="utf-8")]
    idx = {r["canonical_key"]: r for r in rows}

    queue = {r["canonical_key"] for r in rows if r["in_review_queue"]}
    press = {r["canonical_key"] for r in rows if r["press_direct"]}
    gop = {r["canonical_key"] for r in rows if r["guard_operative_categories"]}
    grm = {r["canonical_key"] for r in rows
           if r["guard_remarks_categories"] and not r["guard_operative_categories"]}
    nosub = {r["canonical_key"] for r in rows
             if not r["text_available"] and not r["purpose_is_placeholder"]}
    anch = {r["canonical_key"] for r in rows
            if r["operative_anchor_present"] and not r["guard_operative_categories"]}
    side = {r["canonical_key"] for r in rows if r["sidecar_collisions"]}

    pools = [
        ("P1_press_direct", press),
        ("P2_guard_operative", gop),
        ("P3_guard_remarks_only", grm),
        ("P4_notext_substantive_purpose", nosub),
        ("P5_anchor_no_guard", anch),
        ("P6_sidecar_collision", side),
        ("P7_queue_residue", queue),
    ]
    assigned: dict[str, str] = {}
    for name, s in pools:
        for k in sorted(s):
            assigned.setdefault(k, name)

    CARDS.mkdir(exist_ok=True)
    by_pool = defaultdict(list)
    for k, pool in assigned.items():
        by_pool[pool].append(card(idx[k], pool))

    order = [p for p, _ in pools]
    manifest = {}
    for pool in order:
        cs = sorted(by_pool[pool], key=lambda c: (c["k"].split(":")[0], c["k"]))
        path = CARDS / f"{pool}.json"
        path.write_text(json.dumps(cs, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
        manifest[pool] = {"n": len(cs), "bytes": path.stat().st_size}
        print(f"{pool:34s} {len(cs):5d}  {path.stat().st_size:9d} bytes")
    (CARDS / "_pools.json").write_text(
        json.dumps({"assigned": assigned, "manifest": manifest}, ensure_ascii=False, indent=1),
        encoding="utf-8", newline="\n")
    print("TOTAL cards:", len(assigned))
    print("not carded (deterministic remainder):", len(rows) - len(assigned))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
