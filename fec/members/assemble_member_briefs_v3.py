# -*- coding: utf-8 -*-
"""Assemble v3 member briefs from the writers' batch outputs, validate them, and route failures back.

    python fec/members/assemble_member_briefs_v3.py [--staging C:/melange-data/member_briefs_v3_staging]
        [--packets data/members/member_brief_packets_v3.json] [--briefs data/members/member_briefs_v3.json]
        [--prompt fec/members/member_briefs_v3_writer_prompt.md] [--exemplars fec/members/member_briefs_v3_exemplars.json]
        [--batch N] [--write-receipt] [--receipt PATH] [--packet-receipt PATH] [--ledger PATH]

Reads ``<staging>/manifest.json`` (from stage_member_brief_batches.py) and, per batch, the staged
``batches/batch_NNN.json`` and the writer's ``out/batch_NNN.json`` (an object keyed by member display name).
Every brief is stamped with the packet_sha256 of the STAGED input; whatever the writer put there is replaced.
The brief gets no other key (the validator allows none), so the model, effort, prompt_sha256 and written_at
(the output file's time) go in the document's ``writer`` map, keyed by member.

The merge starts from the existing briefs file: members the writers returned this round replace their old
brief, everyone else is kept, so a rewrite round may return only the failed members.  A changed briefs file is
backed up to ``<staging>/backups/`` first.  The merged set is then run through validate_member_briefs_v3, each
member against the packet its writer was staged with (the registry offer in series mode) plus the packets file's
avoid_phrases, and ``<staging>/issues/batch_NNN.json`` records, per batch, who passed, who failed (with issues and
warnings), who is missing, and any unstaged name or unreadable output.  ``<staging>/avoid_phrases.json`` is
overwritten with the six-word runs now shared by many briefs, for the next round.

``<staging>/registry.json`` is rewritten every run: the coined-animal registry (the exemplars' ``coined_registry``
grown by ``grow_registry`` over every merged brief, in name order, exactly as the packet builder grows it from the
briefs file; a new coin needs an image from ``<staging>/registry_images.json``, else it is listed in ``pending_images``),
its sha256, and ``assembled_batches``, the batches whose output has been read.  It does not depend on a brief passing: a
rewrite that drops a coin drops its registry entry at the next run.

In a frozen run (``--frozen-registry`` at staging) the registry never grows and nothing is restaged, batches may be assembled in
any order, and a brief whose animal is not the packet's assigned (or suggested) animal, which includes any new coin, is refused:
not merged, listed under ``refused`` in the batch's issues file, and the member counts as missing.

After every run the assembler restages each batch that has no writer output yet (``restage_unwritten``), so a later
batch's packets carry every earlier coin as ``coined_animals`` and every earlier ``avoid_phrases`` entry (the seed lines,
then what earlier runs wrote to ``<staging>/avoid_phrases.json``, then the six-word runs now shared by many briefs; the
file only grows).  The manifest's ``batch_runs`` records, per batch, the registry, avoid_phrases and writer-prompt hashes
it saw.

Fail closed (exit 2, before anything is written): a full run when any manifest batch has no ``out`` file (every member of
it is listed as missing; a series run with ``--batch N`` may leave later batches unwritten); a writer prompt whose sha256
differs from the one the batch was staged with; briefs that would mix writer prompts in one file; a bad registry image.

Series mode, ``--batch N``: merge and read only batch N's output, and judge only batch N (the other batches may not
be written yet).  The registry still grows over every merged brief.  ``--write-receipt`` is not allowed with it.

``--write-receipt`` hands over to the validator (which writes the receipt, judging against the packets file) only
when every staged member is present and passes and no output was unreadable.  Exit 0 = clean, 1 = failures or
missing members, 2 = fail closed on bad inputs.
"""
from __future__ import annotations

import argparse
import datetime as dt
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fec.members import build_member_brief_packets as P  # noqa: E402
from fec.members import validate_member_briefs_v3 as V  # noqa: E402
from fec.members import stage_member_brief_batches as S  # noqa: E402
from fec.members.stage_member_brief_batches import PROMPT_PATH, REGISTRY_FILE, STAGING  # noqa: E402

MODEL, EFFORT = "claude-haiku-5-5", "high"
ISSUES_SCHEMA = "member-brief-issues-v1"
REGISTRY_SCHEMA = "member-brief-registry-v1"


def utc(ts: float | None = None) -> str:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat().replace("+00:00", "Z") if ts is not None else \
        dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--staging", type=Path, default=STAGING)
    ap.add_argument("--packets", type=Path, default=P.PACKETS_PATH)
    ap.add_argument("--briefs", type=Path, default=P.BRIEFS_PATH)
    ap.add_argument("--prompt", type=Path, default=PROMPT_PATH, help="writer prompt file; its sha256 is recorded per brief")
    ap.add_argument("--exemplars", type=Path, default=P.EXEMPLARS_PATH, help="registry seed (its coined_registry)")
    ap.add_argument("--registry-images", type=Path, default=None,
                    help="JSON {animal: image}: the 3 to 8 word image the orchestrator sets when a new coin is registered "
                         "(default <staging>/registry_images.json); a coin without one is listed as pending and not offered")
    ap.add_argument("--batch", type=int, help="series mode: merge and judge only this batch")
    ap.add_argument("--write-receipt", action="store_true")
    ap.add_argument("--receipt", type=Path, default=V.RECEIPT_PATH)
    ap.add_argument("--packet-receipt", type=Path, default=P.RECEIPT_PATH)
    ap.add_argument("--ledger", type=Path, default=P.LEDGER_PATH)
    args = ap.parse_args(argv)
    if args.batch is not None and args.write_receipt:
        ap.error("--write-receipt needs every batch; run it without --batch")
    staging = Path(args.staging)

    for path in (staging / "manifest.json", args.packets, args.prompt):
        if not Path(path).is_file():
            print("FAIL CLOSED: missing %s" % path, file=sys.stderr)
            return 2
    manifest = P.load_json(staging / "manifest.json")
    batch_ids = list(manifest["batches"])
    selected = ["batch_%03d" % args.batch] if args.batch is not None else batch_ids
    if selected[0] not in batch_ids:
        print("FAIL CLOSED: %s is not in the manifest (%s)" % (selected[0], ", ".join(batch_ids)), file=sys.stderr)
        return 2
    out_file = lambda bid: staging / "out" / (bid + ".json")
    if args.batch is None:       # a full run needs every batch written; a series run (--batch N) may leave the later ones for later
        unwritten = [b for b in batch_ids if not out_file(b).is_file()]
        for bid in unwritten:
            print("FAIL CLOSED: %s has no writer output (%s); all %d of its members are missing: %s" % (
                bid, out_file(bid), len(manifest["batches"][bid]), ", ".join(sorted(manifest["batches"][bid]))), file=sys.stderr)
        if unwritten:
            return 2
    packets = P.load_json(args.packets).get("members") or {}
    prompt_sha = P.sha256_file(args.prompt)
    frozen_info, frozen = manifest.get("frozen_registry"), None
    if frozen_info:
        try:
            frozen = P.load_frozen_registry(staging / "frozen_registry.json")
        except (OSError, ValueError, KeyError) as error:
            print("FAIL CLOSED: the frozen registry copy in %s is unusable: %s" % (staging, error), file=sys.stderr)
            return 2
        if frozen["sha256"] != frozen_info["sha256"]:
            print("FAIL CLOSED: %s no longer has the sha256 the manifest recorded for the frozen registry" % (staging / "frozen_registry.json"), file=sys.stderr)
            return 2
    runs = manifest.get("batch_runs") or {}
    staged_with = {b: (runs.get(b) or {}).get("writer_prompt_sha256") or manifest.get("writer_prompt_sha256") for b in selected if out_file(b).is_file()}
    changed = {b: sha for b, sha in staged_with.items() if sha and sha != prompt_sha}
    if changed:
        print("FAIL CLOSED: the writer prompt changed since staging (%s were staged under %s, %s is %s): one run, one frozen prompt" % (
            ", ".join(changed), ", ".join(sorted({s[:12] for s in changed.values()})), args.prompt, prompt_sha[:12]), file=sys.stderr)
        return 2
    try:
        seed = P.registry_seed(P.load_json(args.exemplars)) if Path(args.exemplars).is_file() else []
    except ValueError as error:
        print("FAIL CLOSED: %s" % error, file=sys.stderr)
        return 2

    base_doc = P.load_json(args.briefs) if Path(args.briefs).is_file() else None
    if base_doc is not None and (base_doc.get("schema") != V.BRIEFS_SCHEMA or not isinstance(base_doc.get("briefs"), dict)):
        print("FAIL CLOSED: %s is not a %s file" % (args.briefs, V.BRIEFS_SCHEMA), file=sys.stderr)
        return 2
    base = (base_doc or {}).get("briefs") or {}
    briefs, writer = dict(base), dict((base_doc or {}).get("writer") or {})

    names, errors, extras, read, found, refused = {}, {}, {}, set(), False, {}
    for bid in batch_ids:
        batch_path, out_path = staging / "batches" / (bid + ".json"), staging / "out" / (bid + ".json")
        items = P.load_json(batch_path)["items"]
        staged = {i["name"]: i["packet_sha256"] for i in items}
        names[bid] = sorted(staged)
        for item in items:       # judge each member against what its writer saw; avoid_phrases stay the packets file's
            packets[item["name"]] = {**packets.get(item["name"], {}), **item["packet"]}
        if bid not in selected or not out_path.is_file():
            continue
        found = True
        try:
            written = P.load_json(out_path)
            if not isinstance(written, dict):
                raise ValueError("expected a JSON object keyed by member name")
        except (OSError, ValueError) as error:
            errors[bid] = "%s: %s" % (out_path.name, error)
            continue
        read.add(bid)
        extras[bid] = sorted(set(written) - set(staged))
        for name in sorted(set(written) & set(staged)):
            brief = written[name]
            if frozen and isinstance(brief, dict):      # a frozen run only accepts the assigned or suggested animal
                expected = S.member_animal(packets[name])
                arch = brief.get("archetype")
                got = arch.get("animal") if isinstance(arch, dict) else None
                if expected is not None and got != expected:
                    kind = "assigned" if (packets[name].get("coin_recommended") or {}).get("registry_match") else "suggested"
                    refused.setdefault(bid, {})[name] = "animal %r is not the %s animal %r" % (got, kind, expected)
                    continue
            brief = {**brief, "packet_sha256": staged[name]} if isinstance(brief, dict) else brief   # never the writer's value
            if briefs.get(name) != brief:
                briefs[name] = brief
                writer[name] = {"model": MODEL, "effort": EFFORT, "prompt_sha256": prompt_sha, "written_at": utc(out_path.stat().st_mtime)}
    if not found:
        print("FAIL CLOSED: no writer output under %s" % (staging / "out"), file=sys.stderr)
        return 2

    mixed = sorted({w.get("prompt_sha256") for w in writer.values() if isinstance(w, dict) and w.get("prompt_sha256")})
    if len(mixed) > 1:
        print("FAIL CLOSED: the briefs would mix writer prompts (%s); one pilot runs under one frozen writer prompt" % ", ".join(s[:12] for s in mixed),
              file=sys.stderr)
        return 2
    images_path = args.registry_images or staging / "registry_images.json"
    images = P.load_json(images_path) if Path(images_path).is_file() else None
    pending = []
    try:        # before anything is written: a bad registry image stops the run
        registry = P.frozen_animals(frozen) if frozen else P.grow_registry(seed, dict(sorted(briefs.items())), packets, images=images, pending=pending)
    except ValueError as error:
        print("FAIL CLOSED: %s" % error, file=sys.stderr)
        return 2

    if briefs != base:
        if Path(args.briefs).is_file():
            backup = staging / "backups" / ("%s.%s.json" % (Path(args.briefs).stem, dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")))
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(args.briefs, backup)
        P.dump_atomic({**(base_doc or {}), "schema": V.BRIEFS_SCHEMA, "count": len(briefs), "writer": writer,
                       "briefs": dict(sorted(briefs.items()))}, args.briefs)

    expected = {n for v in names.values() for n in v}
    scope = {n for b in selected for n in names[b]}
    report = V.validate_all(briefs, packets, expected=expected, require_binding=True)
    results = report["members"]
    missing = set(report["missing"]) & scope
    failed = [n for n in report["failed"] if n in scope or args.batch is None]
    for bid in selected:
        P.dump_atomic({
            "schema": ISSUES_SCHEMA, "batch": bid, "error": errors.get(bid), "missing": [n for n in names[bid] if n in missing],
            "unexpected_in_output": extras.get(bid, []), "refused": refused.get(bid, {}),
            "passed": [n for n in names[bid] if n in results and results[n]["pass"]],
            "failed": {n: {"issues": results[n]["issues"], "warnings": results[n]["warnings"]}
                       for n in names[bid] if n in results and not results[n]["pass"]}}, staging / "issues" / (bid + ".json"))
    clean = {n: b for n, b in briefs.items() if not any(i["kind"] == "schema" for i in results[n]["issues"])}
    avoid_path = staging / "avoid_phrases.json"
    avoid = S.avoid_list(P.load_json(avoid_path).get("avoid_phrases") if avoid_path.is_file() else [], P.compute_avoid_phrases(clean))
    P.dump_atomic({"avoid_phrases": avoid}, avoid_path)

    registry_path = staging / REGISTRY_FILE
    before = (P.load_json(registry_path).get("assembled_batches") or []) if registry_path.is_file() else []
    P.dump_atomic({"schema": REGISTRY_SCHEMA, "coined_animals": registry, "registry_sha256": S.registry_sha256(registry), "frozen": bool(frozen),
                   "pending_images": pending, "assembled_batches": sorted(set(before) | read)}, registry_path)
    for entry in pending:
        print("PENDING IMAGE %s (first used by %s): %s" % (entry["animal"], entry["first_member"], entry["reason"]))

    # every batch with no writer output yet gets the registry and avoid_phrases so far (the packets file's packets, not the staged copies)
    ready = {n: p for n, p in (P.load_json(args.packets).get("members") or {}).items() if p.get("ready_for_writing")}
    restaged, left = ([], {}) if frozen else S.restage_unwritten(staging, ready, registry, avoid, prompt_sha, args.exemplars)
    if restaged:
        print("restaged %s with %d coined animals" % (", ".join(restaged), len(registry)))
    for bid, why in left.items():
        print("NOT RESTAGED %s: %s" % (bid, why), file=sys.stderr)

    print("staged %d  merged %d  passed %d  failed %d  missing %d  registry %d" % (
        len(scope), len(briefs), len([n for n in scope if n in results and results[n]["pass"]]), len(failed), len(missing), len(registry)))
    for name in failed[:20]:
        print("FAIL %s: %d issue(s)" % (name, len(results[name]["issues"])))
    for bid, why in refused.items():
        for name, reason in sorted(why.items()):
            print("REFUSED %s: %s" % (name, reason))
    if missing:
        print("MISSING %s" % ", ".join(sorted(missing)))
    for bid, error in errors.items():
        print("UNREADABLE %s: %s" % (bid, error), file=sys.stderr)
    for bid, extra in extras.items():
        if extra:
            print("UNSTAGED NAMES in %s (not merged): %s" % (bid, ", ".join(extra)), file=sys.stderr)

    ok = not (failed or missing or errors or refused or (args.batch is None and report["unexpected"]))
    if args.write_receipt:
        if not ok:
            print("not writing receipt: every staged member must be present and pass", file=sys.stderr)
            return 1
        return V.main(["--briefs", str(args.briefs), "--packets", str(args.packets), "--packet-receipt", str(args.packet_receipt),
                       "--ledger", str(args.ledger), "--receipt", str(args.receipt), "--write-receipt"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

