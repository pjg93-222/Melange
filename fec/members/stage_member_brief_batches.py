# -*- coding: utf-8 -*-
"""Stage v3 member brief packets into writer batches (one batch file per Haiku writer call).

    python fec/members/stage_member_brief_batches.py [--packets data/members/member_brief_packets_v3.json]
        [--staging C:/melange-data/member_briefs_v3_staging] [--batch-size 15] [--only-ready] [--force]
        [--batch N] [--exemplars fec/members/member_briefs_v3_exemplars.json]
        [--prompt fec/members/member_briefs_v3_writer_prompt.md] [--exclude-same-animal-exemplars] [--frozen-registry PATH]

Writes ``<staging>/batches/batch_NNN.json`` ({"items": [{"name", "packet_sha256", "packet"}]}), the shared
``<staging>/avoid_phrases.json`` ({"avoid_phrases": [...]}), and ``<staging>/manifest.json`` (every member and its
batch, any skipped member and why, the writer prompt's sha256 and, per batch, the registry, avoid_phrases and prompt
hashes that batch's packets carried: ``batch_runs``).  Members are dealt round-robin from a (chamber, party, name)
sort, so every batch mixes chambers and parties and holds at most ``--batch-size`` members.  Each staged packet keeps
its ``avoid_phrases`` as a list that starts with the style guide's seed lines.  The writers save
``<staging>/out/batch_NNN.json`` (a JSON object keyed by member display name); ``assemble_member_briefs_v3.py`` merges,
stamps and validates them, and restages every batch that has no output yet (``restage_unwritten``).

``--exclude-same-animal-exemplars`` (R10) adds ``"exemplars": {member: [gold exemplar names]}`` to each batch file: for
every member, the gold exemplars whose animal differs from that member's animal.  A member's animal is the registry
match when there is one, nothing (so every exemplar is offered) when the packet recommends a coin, else the suggested
animal.  The option is recorded in the manifest, so a restaged batch keeps its lists, recomputed for the restaged packets.

With the option, each batch also gets ``<staging>/batches/exemplars_NNN.json``: the exemplars file with only the gold
exemplars every member of the batch may see (the intersection of the per-member lists), so the writers' spawner hands a batch
one file.  A restaged batch rewrites it.

``--frozen-registry PATH`` (guide 8.4): the pre-coined registry the orchestrator froze (status FROZEN: animals in priority
order, signature rows, and assignments).  Every packet gets its assigned animal (a coin-recommended member the registry lacks
fails the run, naming them all), the packets carry the registry as ``coined_animals``, the manifest records the file's sha256
and the registry hash (``frozen_registry``, and per batch in ``batch_runs``), a copy of the file goes to
``<staging>/frozen_registry.json``, and any assignment that breaks the current registry-match rule is listed (not changed).
Nothing is coined or grown, so batches may be assembled in any order or in parallel and nothing is restaged; the assembler
refuses a brief whose animal is not the assigned (or suggested) one.

Exit 2 (nothing written): the packets file is missing or the wrong schema, any packet is not
ready_for_writing (unless ``--only-ready``, which stages the rest and lists the skipped), a packet's
stored packet_sha256 does not match its content, the writer prompt is missing, or ``<staging>/out`` already holds
writer output (written against an earlier staging; move it aside, or ``--force``).

Series mode, ``--batch N``: rewrites only ``batches/batch_NNN.json`` from the same packets file, with the coined-animal
registry that assemble_member_briefs_v3.py grew into ``<staging>/registry.json`` (the exemplars' ``coined_registry`` when
there is no file yet): each packet's ``coined_animals`` is the registry and ``apply_registry`` re-decides
``coin_recommended``, so a coin from an earlier batch is offered to this one as a ``registry_match``.  The assembler does
this for every unwritten batch after each run; the command stays for a manual restage.  The registry is not part of the
packet hash, so ``packet_sha256`` (and every earlier brief's stamp) is unchanged.  Exit 2 also when the batch is not in
the manifest, an earlier batch has not been assembled (``--force`` stages it anyway), or the packets carry coined animals
the registry lacks (the packets were built from other briefs; rebuild them without ``--briefs``).
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fec.members import build_member_brief_packets as P  # noqa: E402

STAGING = Path("C:/melange-data/member_briefs_v3_staging")
REGISTRY_FILE = "registry.json"
PROMPT_PATH = Path(__file__).with_name("member_briefs_v3_writer_prompt.md")
BATCH_SCHEMA = "member-brief-batch-v1"
MANIFEST_SCHEMA = "member-brief-batch-manifest-v1"


def party_of(packet: dict) -> str:
    return (packet["member"].get("bio") or {}).get("party") or ""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_sha(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def registry_sha256(registry) -> str:
    return canonical_sha(list(registry or []))


def avoid_list(*sources) -> list[str]:
    """The seed lines first, then every source's phrases, once each."""
    return list(dict.fromkeys([*P.SEED_AVOID_PHRASES, *(a for source in sources for a in source or [])]))


def member_animal(packet: dict):
    """The animal this member's brief will carry: the registry match; None when a coin is recommended; else the suggested animal."""
    coin = packet.get("coin_recommended") or {}
    if coin.get("registry_match"):
        return coin["registry_match"].get("animal")
    return None if coin.get("value") else packet.get("suggested_animal")


def exemplar_source(path) -> dict:
    """The exemplars file as a dict ({} when there is none)."""
    return P.load_json(path) if path and Path(path).is_file() else {}


def exemplar_rows(path) -> list[tuple[str, str]]:
    """[(display name, animal)] of the gold exemplars, in file order."""
    rows = exemplar_source(path).get("exemplars") or []
    return [(r["display_name"], (r.get("archetype") or {}).get("animal")) for r in rows if isinstance(r, dict) and r.get("display_name")]


def write_exemplar_file(staging, bid, batch_doc, source: dict) -> None:
    """``batches/exemplars_NNN.json``: the exemplars file with only the gold every member of the batch may see (R10)."""
    lists = [set(v) for v in (batch_doc.get("exemplars") or {}).values()]
    allowed = set.intersection(*lists) if lists else set()
    out = {**source, "exemplars": [r for r in source.get("exemplars") or [] if r.get("display_name") in allowed], "batch": bid,
           "selection": "%s: the gold exemplars whose animal differs from every member's animal in this batch (style guide 12, R10)" % bid}
    P.dump_atomic(out, Path(staging) / "batches" / ("exemplars_%s.json" % bid[-3:]))


def exemplar_lists(packets: dict, rows) -> dict:
    """{member: [exemplar names whose animal differs from the member's animal]} (R10)."""
    return {n: [name for name, animal in rows if animal != member_animal(p)] for n, p in packets.items()}


def batch_document(bid, names, ready, registry, avoid, rows, *, rebuild):
    """One batch file's content.  ``rebuild`` re-decides each coin against ``registry`` (what a full rebuild with it would say)."""
    items = []
    for n in names:
        packet = copy.deepcopy(ready[n])
        packet["avoid_phrases"] = list(avoid)
        if rebuild:
            packet["coined_animals"] = copy.deepcopy(registry)
            coin = packet["coin_recommended"]
            coin["registry_match"], coin["value"] = None, coin.get("template_coin", coin["value"])
            packet["signature_items"] = [] if coin["value"] else P.signature_items(packet)   # the builder's pre-registry items, not an old match's
            P.apply_registry(packet, registry)             # changes coin_recommended.value/registry_match, which are not hashed
            if P.content_sha256(packet) != ready[n]["packet_sha256"]:
                raise ValueError("the registry changed the packet hash of %s" % n)
        items.append({"name": n, "packet_sha256": ready[n]["packet_sha256"], "packet": packet})
    doc = {"schema": BATCH_SCHEMA, "batch": bid, "items": items}
    if rows is not None:
        doc["exemplars"] = exemplar_lists({i["name"]: i["packet"] for i in items}, rows)
    return doc


def run_record(registry, avoid, prompt_sha, **extra) -> dict:
    return {"registry_sha256": registry_sha256(registry), "avoid_phrases_sha256": canonical_sha(list(avoid)),
            "writer_prompt_sha256": prompt_sha, **extra}


def restage_unwritten(staging, ready, registry, avoid, prompt_sha, exemplars_path=None):
    """Rewrite every manifest batch that has no writer output yet with ``registry`` and ``avoid``; record what each saw.

    Returns (restaged batch ids, {batch id: why it was left as it was})."""
    staging = Path(staging)
    manifest = P.load_json(staging / "manifest.json")
    if manifest.get("frozen_registry"):
        return [], {}                                          # the registry never changes in a frozen run
    exclude = manifest.get("exclude_same_animal_exemplars")
    rows = exemplar_rows(exemplars_path) if exclude else None
    known = {e["animal"] for e in registry}
    done, skipped = [], {}
    for bid, names in manifest["batches"].items():
        if (staging / "out" / (bid + ".json")).is_file():
            continue                                         # a writer may be working from, or has written, this staging
        absent = [n for n in names if n not in ready]
        ghosts = {e["animal"] for n in names if n in ready for e in ready[n].get("coined_animals") or []} - known
        if absent or ghosts:
            skipped[bid] = ("members that are not ready packets any more: " + ", ".join(absent[:10])) if absent else (
                "the packets carry coined animals the registry lacks (%s)" % ", ".join(sorted(ghosts)))
            continue
        doc = batch_document(bid, names, ready, registry, avoid, rows, rebuild=True)
        P.dump_atomic(doc, staging / "batches" / (bid + ".json"))
        if exclude:
            write_exemplar_file(staging, bid, doc, exemplar_source(exemplars_path))
        manifest.setdefault("batch_runs", {})[bid] = run_record(registry, avoid, prompt_sha, restaged_utc=utc_now())
        done.append(bid)
    if done:
        P.dump_atomic(manifest, staging / "manifest.json")
    return done, skipped


def restage_batch(args, ready: dict) -> int:
    """Series mode: rewrite one batch file with the registry grown so far (see the module docstring)."""
    staging = Path(args.staging)
    if not (staging / "manifest.json").is_file():
        print("FAIL CLOSED: no %s; stage all batches first (without --batch)" % (staging / "manifest.json"), file=sys.stderr)
        return 2
    manifest = P.load_json(staging / "manifest.json")
    if manifest.get("frozen_registry"):
        print("frozen registry %s: the registry never changes, so there is nothing to restage" % manifest["frozen_registry"]["sha256"][:12])
        return 0
    batches = manifest["batches"]
    bid = "batch_%03d" % args.batch
    if bid not in batches:
        print("FAIL CLOSED: %s is not in the manifest (%s)" % (bid, ", ".join(batches)), file=sys.stderr)
        return 2
    held = P.load_json(staging / REGISTRY_FILE) if (staging / REGISTRY_FILE).is_file() else None
    pending = [b for b in batches if b < bid and b not in ((held or {}).get("assembled_batches") or [])]
    if pending and not args.force:
        print("FAIL CLOSED: %s not assembled yet, so its coined animals are not in the registry; assemble %s first (or --force)" % (
            ", ".join(pending), "it" if len(pending) == 1 else "them"), file=sys.stderr)
        return 2
    try:
        registry = held["coined_animals"] if held else (
            P.registry_seed(P.load_json(args.exemplars)) if Path(args.exemplars).is_file() else [])
    except ValueError as error:
        print("FAIL CLOSED: %s" % error, file=sys.stderr)
        return 2
    absent = [n for n in batches[bid] if n not in ready]
    ghosts = {e["animal"] for n in batches[bid] if n in ready for e in ready[n].get("coined_animals") or []} - {e["animal"] for e in registry}
    if absent or ghosts:
        print("FAIL CLOSED: %s" % (("%s lists members that are not ready packets any more: %s" % (bid, ", ".join(absent[:20]))) if absent else
              "the packets carry coined animals the registry lacks (%s); rebuild the packets without --briefs" % ", ".join(sorted(ghosts))), file=sys.stderr)
        return 2
    avoid_path = staging / "avoid_phrases.json"
    avoid = avoid_list(P.load_json(avoid_path).get("avoid_phrases") if avoid_path.is_file() else [], *[ready[n].get("avoid_phrases") for n in batches[bid]])
    rows = exemplar_rows(args.exemplars) if manifest.get("exclude_same_animal_exemplars") else None
    try:
        doc = batch_document(bid, batches[bid], ready, registry, avoid, rows, rebuild=True)
    except ValueError as error:
        print("FAIL CLOSED: %s" % error, file=sys.stderr)
        return 2
    P.dump_atomic(doc, staging / "batches" / (bid + ".json"))
    if rows is not None:
        write_exemplar_file(staging, bid, doc, exemplar_source(args.exemplars))
    manifest.setdefault("batch_runs", {})[bid] = run_record(registry, avoid, manifest.get("writer_prompt_sha256"), restaged_utc=utc_now())
    P.dump_atomic(manifest, staging / "manifest.json")
    print("restaged %s: %d members, registry of %d coined animals" % (bid, len(doc["items"]), len(registry)))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--packets", type=Path, default=P.PACKETS_PATH)
    ap.add_argument("--staging", type=Path, default=STAGING)
    ap.add_argument("--batch-size", type=int, default=15, help="most members in one batch (default 15)")
    ap.add_argument("--only-ready", action="store_true", help="skip packets that are not ready_for_writing instead of refusing")
    ap.add_argument("--force", action="store_true", help="stage even though <staging>/out already holds writer output "
                                                         "(or, with --batch, an earlier batch is not assembled)")
    ap.add_argument("--batch", type=int, help="series mode: rewrite only this batch, with the registry grown so far")
    ap.add_argument("--exemplars", type=Path, default=P.EXEMPLARS_PATH, help="registry seed for --batch before any assemble; the gold exemplars")
    ap.add_argument("--prompt", type=Path, default=PROMPT_PATH, help="the writer prompt every batch is written with; its sha256 goes in the manifest")
    ap.add_argument("--frozen-registry", type=Path, default=None,
                    help="the pre-coined registry (status FROZEN): every packet gets its assigned animal; nothing is coined, grown or restaged")
    ap.add_argument("--exclude-same-animal-exemplars", action="store_true",
                    help="R10: list for each member, per batch, the gold exemplars whose animal differs from the member's animal")
    args = ap.parse_args(argv)
    if args.batch_size < 1:
        ap.error("--batch-size must be at least 1")
    if not Path(args.packets).is_file():
        print("FAIL CLOSED: missing %s" % args.packets, file=sys.stderr)
        return 2
    if not Path(args.prompt).is_file():
        print("FAIL CLOSED: missing writer prompt %s" % args.prompt, file=sys.stderr)
        return 2
    doc = P.load_json(args.packets)
    if doc.get("schema") != P.SCHEMA or not isinstance(doc.get("members"), dict):
        print("FAIL CLOSED: %s is not a %s file" % (args.packets, P.SCHEMA), file=sys.stderr)
        return 2
    packets = doc["members"]

    skipped = {n: p.get("not_ready_reasons") or ["not ready_for_writing"] for n, p in packets.items() if not p.get("ready_for_writing")}
    if skipped and not args.only_ready:
        print("FAIL CLOSED: %d packet(s) are not ready_for_writing (--only-ready stages the rest):" % len(skipped), file=sys.stderr)
        for name in sorted(skipped)[:20]:
            print("  %s: %s" % (name, "; ".join(skipped[name])), file=sys.stderr)
        return 2
    ready = {n: p for n, p in packets.items() if n not in skipped}
    stale = sorted(n for n, p in ready.items() if p.get("packet_sha256") != P.content_sha256(p))
    if stale or not ready:
        print("FAIL CLOSED: %s" % ("packet_sha256 does not match the packet content for: " + ", ".join(stale[:20]) if stale else "no ready packet to stage"),
              file=sys.stderr)
        return 2

    if args.batch is not None:
        return restage_batch(args, ready)
    staging = Path(args.staging)
    earlier = sorted(p.name for p in (staging / "out").glob("batch_*.json"))
    if earlier and not args.force:       # the assembler stamps outputs with THIS staging's hashes, so old ones would lie
        print("FAIL CLOSED: %s holds writer output from an earlier staging (%s); move it aside, or pass --force" % (
            staging / "out", ", ".join(earlier[:5])), file=sys.stderr)
        return 2

    frozen, frozen_info = None, None
    if args.frozen_registry:
        try:
            frozen = P.load_frozen_registry(args.frozen_registry)
        except (OSError, ValueError, KeyError) as error:
            print("FAIL CLOSED: %s" % error, file=sys.stderr)
            return 2
        report = P.apply_frozen_registry(ready, frozen)
        if report["unassigned"]:
            print("FAIL CLOSED: %d coin-recommended member(s) the frozen registry lacks: %s" % (len(report["unassigned"]), ", ".join(report["unassigned"])), file=sys.stderr)
            return 2
        violations = P.audit_frozen_registry(ready, frozen)
        for v in violations:
            print("VIOLATION %(member)s -> %(animal)s (%(source)s): %(problem)s" % v)
        frozen_info = {"path": frozen["path"], "sha256": frozen["sha256"], "registry_sha256": registry_sha256(P.frozen_animals(frozen)),
                       "animals": len(frozen["animals"]), "assignments": len(frozen["assignments"]), "violations": violations,
                       "stale_assignments": report["stale"]}

    ordered = sorted(ready, key=lambda n: (ready[n]["member"]["chamber"], party_of(ready[n]), n))
    count = math.ceil(len(ordered) / args.batch_size)
    batches = {"batch_%03d" % (i + 1): ordered[i::count] for i in range(count)}     # deal, so each batch samples every group

    # The registry the packets carry is the one every batch starts from; the seed lines and the packets' own avoid_phrases go
    # in every staged packet, and phrases an earlier assemble wrote back stay too.
    registry = next(iter(ready.values())).get("coined_animals") or []
    avoid_path = staging / "avoid_phrases.json"
    avoid = avoid_list(P.load_json(avoid_path).get("avoid_phrases") if avoid_path.is_file() else [], *[p.get("avoid_phrases") for p in ready.values()])
    rows = exemplar_rows(args.exemplars) if args.exclude_same_animal_exemplars else None
    source = exemplar_source(args.exemplars) if args.exclude_same_animal_exemplars else None
    prompt_sha, staged_utc = P.sha256_file(args.prompt), utc_now()

    members, runs = {}, {}
    for bid, names in batches.items():
        doc = batch_document(bid, names, ready, registry, avoid, rows, rebuild=False)
        P.dump_atomic(doc, staging / "batches" / (bid + ".json"))
        if source is not None:
            write_exemplar_file(staging, bid, doc, source)
        runs[bid] = run_record(registry, avoid, prompt_sha, staged_utc=staged_utc)
        for n in names:
            members[n] = {"batch": bid, "packet_sha256": ready[n]["packet_sha256"], "chamber": ready[n]["member"]["chamber"],
                          "party": party_of(ready[n])}
    P.dump_atomic({"avoid_phrases": avoid}, avoid_path)

    (staging / "out").mkdir(parents=True, exist_ok=True)
    if frozen:
        shutil.copyfile(args.frozen_registry, staging / "frozen_registry.json")
    P.dump_atomic({
        "schema": MANIFEST_SCHEMA, "created_utc": staged_utc,
        "packets": str(Path(args.packets).resolve()), "packets_sha256": P.sha256_file(args.packets), "batch_size": args.batch_size,
        "writer_prompt": str(Path(args.prompt).resolve()), "writer_prompt_sha256": prompt_sha,
        "exclude_same_animal_exemplars": bool(args.exclude_same_animal_exemplars), "frozen_registry": frozen_info, "batch_runs": runs,
        "counts": {"staged": len(ready), "skipped": len(skipped), "batches": count},
        "batches": batches, "members": members, "skipped": skipped}, staging / "manifest.json")
    print("staged %d members in %d batches (%s) under %s" % (len(ready), count, ", ".join(str(len(v)) for v in batches.values()), staging))
    for name in sorted(skipped):
        print("skipped %s: %s" % (name, "; ".join(skipped[name])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
