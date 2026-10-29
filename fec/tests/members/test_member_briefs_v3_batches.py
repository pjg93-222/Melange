"""v3 member brief batch staging and assembly: batch mixing, hash binding, merge, issue routing, receipt gate.

Stage tests use fake packets (only the fields staging reads).  Assemble tests reuse the synthetic
three-member ledger and the Alex Rich gold-shaped brief from test_member_briefs_v3, so the real
validator judges them.  Nothing here touches real data.
"""
import copy

import pytest

from fec.members import assemble_member_briefs_v3 as A
from fec.members import build_member_brief_packets as P
from fec.members import stage_member_brief_batches as S
from fec.members import validate_member_briefs_v3 as V
from fec.tests.members import test_member_briefs_v3 as T


def fake(name, chamber, party, ready=True):
    packet = {"member": {"display_name": name, "chamber": chamber, "bio": {"party": party}}, "evidence_tier": "rich",
              "evidence": [], "gates": {}, "appeals": None, "public_sensibilities": [], "longform": [],
              "archetype_candidates": [], "suggested_animal": None, "coin_recommended": {"value": False},
              "avoid_phrases": ["shared six word phrase one"], "ready_for_writing": ready,
              "not_ready_reasons": [] if ready else ["no speech basis counts row"]}
    packet["packet_sha256"] = P.content_sha256(packet)
    return packet


def fixture_packets(*names):
    packets, _ = T.build()
    return {n: packets[n] for n in names} if names else packets


class Env:
    """Staging dir, packets file and briefs file under tmp_path, with the stage/assemble CLIs wired to them."""

    def __init__(self, tmp_path):
        self.stg = tmp_path / "stg"
        self.packets_path = tmp_path / "packets.json"
        self.briefs_path = tmp_path / "data" / "member_briefs_v3.json"
        self.receipt = tmp_path / "data" / "member_briefs_v3.receipt.json"
        self.prompt = tmp_path / "writer_prompt.md"
        self.prompt.write_text("writer prompt v1", encoding="utf-8")
        self.packet_receipt = tmp_path / "packets.receipt.json"
        P.dump_atomic({"status": "READY", "allow_partial_longform": False}, self.packet_receipt)
        self.ledger = tmp_path / "ledger.json"
        self.ledger.write_text("{}", encoding="utf-8")
        self.exemplars = tmp_path / "exemplars.json"
        self.seed([])

    def seed(self, entries, exemplars=()):
        P.dump_atomic({"coined_registry": entries, "exemplars": list(exemplars)}, self.exemplars)

    def images(self, mapping):
        P.dump_atomic(mapping, self.stg / "registry_images.json")

    def stage(self, packets, *extra):
        P.dump_atomic({"schema": P.SCHEMA, "status": "PACKETS", "count": len(packets), "ledger_sha256": "x",
                       "members": packets}, self.packets_path)
        return S.main(["--packets", str(self.packets_path), "--staging", str(self.stg), "--exemplars", str(self.exemplars),
                       "--prompt", str(self.prompt), *map(str, extra)])

    def out(self, batch, mapping):
        P.dump_atomic(mapping, self.stg / "out" / (batch + ".json"))

    def assemble(self, *extra):
        return A.main(["--staging", str(self.stg), "--packets", str(self.packets_path), "--briefs", str(self.briefs_path),
                       "--prompt", str(self.prompt), "--receipt", str(self.receipt), "--packet-receipt", str(self.packet_receipt),
                       "--ledger", str(self.ledger), "--exemplars", str(self.exemplars), *map(str, extra)])

    def issues(self, batch="batch_001"):
        return P.load_json(self.stg / "issues" / (batch + ".json"))

    def briefs(self):
        return P.load_json(self.briefs_path)

    def batch_item(self, batch, name):
        return next(i for i in P.load_json(self.stg / "batches" / (batch + ".json"))["items"] if i["name"] == name)


@pytest.fixture
def env(tmp_path):
    return Env(tmp_path)


def broken(brief=None):
    """A schema failure (do needs 4 items); it stays out of the cross-member repetition check."""
    b = dict(brief or T.good_brief())
    b["do"] = b["do"][:3]
    return b


# ----------------------------------------------------------------------------------- staging ----
def test_batches_mix_chambers_and_parties_and_hold_about_fifteen(env):
    packets = {}
    for i in range(40):
        name = "M%02d" % i
        packets[name] = fake(name, "House" if i < 25 else "Senate", "Democrat" if i % 2 else "Republican")
    assert env.stage(packets) == 0
    manifest = P.load_json(env.stg / "manifest.json")
    sizes = [len(v) for v in manifest["batches"].values()]
    assert len(sizes) == 3 and max(sizes) <= 15 and max(sizes) - min(sizes) <= 1
    for names in manifest["batches"].values():
        assert {packets[n]["member"]["chamber"] for n in names} == {"House", "Senate"}
        assert {packets[n]["member"]["bio"]["party"] for n in names} == {"Democrat", "Republican"}
    assert sorted(manifest["members"]) == sorted(packets)
    for batch_id, names in manifest["batches"].items():
        doc = P.load_json(env.stg / "batches" / (batch_id + ".json"))
        assert [i["name"] for i in doc["items"]] == names
        for item in doc["items"]:
            assert item["packet_sha256"] == packets[item["name"]]["packet_sha256"] == manifest["members"][item["name"]]["packet_sha256"]
            assert manifest["members"][item["name"]]["batch"] == batch_id
            assert item["packet"]["member"]["display_name"] == item["name"]
            assert item["packet"]["avoid_phrases"] == [*P.SEED_AVOID_PHRASES, "shared six word phrase one"]       # a list, seed lines first
    assert P.load_json(env.stg / "avoid_phrases.json") == {"avoid_phrases": [*P.SEED_AVOID_PHRASES, "shared six word phrase one"]}
    assert manifest["writer_prompt_sha256"] == P.sha256_file(env.prompt)
    for batch_id in manifest["batches"]:
        run = manifest["batch_runs"][batch_id]
        assert run["writer_prompt_sha256"] == manifest["writer_prompt_sha256"] and len(run["registry_sha256"]) == 64 and len(run["avoid_phrases_sha256"]) == 64


def test_unready_packets_refuse_unless_only_ready_which_lists_the_skipped(env, capsys):
    packets = {"A": fake("A", "House", "Democrat"), "B": fake("B", "Senate", "Republican", ready=False)}
    assert env.stage(packets) == 2
    err = capsys.readouterr().err
    assert "B" in err and "no speech basis counts row" in err
    assert not (env.stg / "batches").exists() and not (env.stg / "manifest.json").exists()
    assert env.stage(packets, "--only-ready") == 0
    manifest = P.load_json(env.stg / "manifest.json")
    assert manifest["skipped"] == {"B": ["no speech basis counts row"]}
    assert list(manifest["members"]) == ["A"] and manifest["batches"] == {"batch_001": ["A"]}


def test_a_packet_whose_stored_hash_does_not_match_its_content_is_refused(env, capsys):
    packets = {"A": fake("A", "House", "Democrat")}
    packets["A"]["packet_sha256"] = "0" * 64
    assert env.stage(packets) == 2
    assert "packet_sha256" in capsys.readouterr().err and not (env.stg / "batches").exists()


# ---------------------------------------------------------------------------------- assembly ----
def test_the_hash_is_stamped_from_the_staged_input_never_from_the_writer(env):
    packets = fixture_packets("Alex Rich")
    assert env.stage(packets) == 0
    env.out("batch_001", {"Alex Rich": {**T.good_brief(), "packet_sha256": "f" * 64}})
    assert env.assemble() == 0
    doc = env.briefs()
    brief = doc["briefs"]["Alex Rich"]
    assert brief["packet_sha256"] == packets["Alex Rich"]["packet_sha256"] != "f" * 64
    assert set(brief) == set(V.KEYS) | {"packet_sha256"}            # the validator rejects any other brief key
    meta = doc["writer"]["Alex Rich"]
    assert (meta["model"], meta["effort"]) == ("claude-haiku-5-5", "high")
    assert meta["prompt_sha256"] == P.sha256_file(env.prompt) and meta["written_at"].endswith("Z")
    assert doc["schema"] == V.BRIEFS_SCHEMA
    assert env.issues()["failed"] == {} and env.issues()["passed"] == ["Alex Rich"] and env.issues()["missing"] == []
    assert not (env.stg / "backups").exists()                        # nothing existed to back up


def test_a_member_the_writer_did_not_return_is_reported_missing_and_blocks_the_receipt(env, capsys):
    assert env.stage(fixture_packets()) == 0
    env.out("batch_001", {"Alex Rich": T.good_brief()})
    assert env.assemble("--write-receipt") == 1
    assert env.issues()["missing"] == ["Beth Thin", "Cam Floor"]
    out = capsys.readouterr().out
    assert "Beth Thin" in out and "Cam Floor" in out
    assert not env.receipt.exists()


def test_validator_failures_are_routed_to_the_issues_file_of_their_batch(env):
    assert env.stage(fixture_packets(), "--batch-size", "2") == 0
    where = {n: m["batch"] for n, m in P.load_json(env.stg / "manifest.json")["members"].items()}
    assert len(set(where.values())) == 2
    writes = {"Alex Rich": T.good_brief(), "Beth Thin": broken(), "Cam Floor": {k: v for k, v in T.good_brief().items() if k != "evidence_refs"}}
    for batch in set(where.values()):
        env.out(batch, {n: b for n, b in writes.items() if where[n] == batch})
    assert env.assemble() == 1
    failed = {b: env.issues(b)["failed"] for b in set(where.values())}
    for name in ("Beth Thin", "Cam Floor"):
        assert {i["kind"] for i in failed[where[name]][name]["issues"]} == {"schema"}
        assert all(name not in f for b, f in failed.items() if b != where[name])      # only in its own batch's file
    assert failed[where["Alex Rich"]] == {} and env.issues(where["Alex Rich"])["passed"] == ["Alex Rich"]


def test_an_existing_briefs_file_is_backed_up_before_it_is_overwritten(env):
    env.briefs_path.parent.mkdir(parents=True)
    P.dump_atomic({"schema": V.BRIEFS_SCHEMA, "briefs": {}, "note": "old"}, env.briefs_path)
    before = env.briefs_path.read_bytes()
    assert env.stage(fixture_packets("Alex Rich")) == 0
    env.out("batch_001", {"Alex Rich": T.good_brief()})
    assert env.assemble() == 0
    backups = list((env.stg / "backups").glob("member_briefs_v3.*.json"))
    assert len(backups) == 1 and backups[0].read_bytes() == before
    assert env.briefs_path.read_bytes() != before and "Alex Rich" in env.briefs()["briefs"]


def test_receipt_is_written_only_when_every_member_passes(env):
    assert env.stage(fixture_packets("Alex Rich")) == 0
    env.out("batch_001", {"Alex Rich": broken()})
    assert env.assemble("--write-receipt") == 1 and not env.receipt.exists()
    assert list(env.issues()["failed"]) == ["Alex Rich"]
    env.out("batch_001", {"Alex Rich": T.good_brief()})                # the rewrite replaces the failed brief
    assert env.assemble("--write-receipt") == 0
    receipt = P.load_json(env.receipt)
    assert receipt["status"] == "PASS" and receipt["counts"] == {"briefs": 1, "passed": 1, "failed": 0}
    assert env.issues()["failed"] == {} and len(list((env.stg / "backups").glob("*.json"))) == 1


def test_an_unreadable_output_is_reported_and_blocks_the_receipt_even_if_earlier_briefs_pass(env):
    assert env.stage(fixture_packets("Alex Rich")) == 0
    env.out("batch_001", {"Alex Rich": T.good_brief()})
    assert env.assemble() == 0
    (env.stg / "out" / "batch_001.json").write_text('{"Alex Rich": {', encoding="utf-8")   # a writer died mid-file
    assert env.assemble("--write-receipt") == 1 and not env.receipt.exists()
    assert "batch_001.json" in env.issues()["error"] and env.issues()["passed"] == ["Alex Rich"]


def test_restaging_refuses_while_writer_output_from_an_earlier_staging_exists(env, capsys):
    packets = fixture_packets("Alex Rich")
    assert env.stage(packets) == 0
    env.out("batch_001", {"Alex Rich": T.good_brief()})               # assembling would stamp this with the new hashes
    assert env.stage(packets) == 2
    assert "earlier staging" in capsys.readouterr().err
    assert env.stage(packets, "--force") == 0


def test_members_already_merged_are_not_missing_when_a_later_round_omits_them(env):
    assert env.stage(fixture_packets()) == 0
    env.out("batch_001", {"Alex Rich": T.good_brief()})
    assert env.assemble() == 1
    env.out("batch_001", {"Beth Thin": broken()})
    assert env.assemble() == 1
    assert env.issues()["missing"] == ["Cam Floor"]
    assert set(env.briefs()["briefs"]) == {"Alex Rich", "Beth Thin"}


def test_a_writer_name_that_was_not_staged_is_reported_and_not_merged(env):
    assert env.stage(fixture_packets("Alex Rich")) == 0
    env.out("batch_001", {"Alex Rich": T.good_brief(), "Alex Richh": T.good_brief()})
    assert env.assemble() == 0
    assert env.issues()["unexpected_in_output"] == ["Alex Richh"] and list(env.briefs()["briefs"]) == ["Alex Rich"]


def test_phrases_shared_by_many_briefs_are_written_back_for_the_next_round(env):
    assert env.stage(fixture_packets()) == 0
    env.out("batch_001", {n: T.good_brief() for n in ("Alex Rich", "Beth Thin", "Cam Floor")})
    assert env.assemble() == 1                                         # identical text: names, pronouns and repetition fail
    phrases = P.load_json(env.stg / "avoid_phrases.json")["avoid_phrases"]
    computed = P.compute_avoid_phrases(env.briefs()["briefs"])
    assert computed and phrases[:len(P.SEED_AVOID_PHRASES)] == list(P.SEED_AVOID_PHRASES) and [p for p in phrases if p in computed] == computed       # seed, then what the briefs share
    env.out("batch_001", {n: broken() for n in ("Alex Rich", "Beth Thin", "Cam Floor")})
    env.assemble()
    assert set(computed) <= set(P.load_json(env.stg / "avoid_phrases.json")["avoid_phrases"])                  # earlier entries are kept, never dropped


# ------------------------------------------------------------------------- series (--batch N) ----
def coin_inputs():
    """Two thin House members with the same profile (practical, wide-ranging) that no template animal fits, so each is a coin."""
    names = ("Dana Coin", "Eli Coin")

    def rec(name):
        r = T.record(traits={"Openness": "well below most"}, behavior={"policy_breadth": "well above most"},
                     frame=T.MIXED[0], supported=T.MIXED[1])
        r["name"], r["chamber"] = name, "House"
        return r
    return dict(
        ledger_doc={"schema": "member-narrative-evidence-v4", "status": "ACTIVE_FAIL_CLOSED_INPUT", "sources_sha256": {},
                    "members": {n: rec(n) for n in names}},
        legislators=[{"bioguide_id": "D1", "gender": "F", "party": "Democrat", "last_name": "Coin"},
                     {"bioguide_id": "E1", "gender": "M", "party": "Republican", "last_name": "Coin"}],
        congestion=[{"member": "Dana Coin", "bioguide": "D1", "chamber": "House"}, {"member": "Eli Coin", "bioguide": "E1", "chamber": "House"}],
        model_bio={}, desk_src={"members": [{"name": n, "district": "Oklahoma"} for n in names]}, wiki={},
        basis_counts={n: T.COUNTS["Alex Rich"] for n in names},
        levels_doc={"status": "FINAL", "generated_at": "x", "census": {}, "members": {n: T.level(n) for n in names}})


def coin_packets(**kw):
    packets, problems = P.build_all(**{**coin_inputs(), "coined": [], **kw})
    assert problems == []
    return packets


def coin_brief(animal="Beaver"):
    """Schema-shaped, not validator-clean: the registry grows from the archetype alone."""
    b = T.good_brief()
    b["archetype"] = {"animal": animal, "descriptor": "practical and wide-ranging",
                      "justification": "She is practical and her bills cover a wide range of issues."}
    b["evidence_refs"]["archetype"] = ["BH.breadth", "TR.O"]
    return b


BEAVER_IMAGE = "a beaver that builds with others"


def series_after_batch_one(env):
    """Stage Dana (batch_001) and Eli (batch_002), have the writer return Dana's coin, assemble batch 1 (which restages batch 2)."""
    packets = coin_packets()
    assert env.stage(packets, "--batch-size", "1") == 0
    where = {n: m["batch"] for n, m in P.load_json(env.stg / "manifest.json")["members"].items()}
    assert where == {"Dana Coin": "batch_001", "Eli Coin": "batch_002"}
    env.images({"Beaver": BEAVER_IMAGE})
    env.out("batch_001", {"Dana Coin": coin_brief()})
    env.assemble("--batch", "1")                              # the brief fails content checks; its coin still registers
    return packets


def test_a_coin_in_batch_one_is_offered_as_a_registry_match_in_batch_two(env):
    packets = coin_packets()
    assert env.stage(packets, "--batch-size", "1") == 0
    before = env.batch_item("batch_002", "Eli Coin")
    assert before["packet"]["coin_recommended"]["value"] and not before["packet"]["coin_recommended"]["registry_match"]
    env.images({"Beaver": BEAVER_IMAGE})
    env.out("batch_001", {"Dana Coin": coin_brief()})
    env.assemble("--batch", "1")
    registry = P.load_json(env.stg / "registry.json")
    assert [e["animal"] for e in registry["coined_animals"]] == ["Beaver"] and registry["assembled_batches"] == ["batch_001"]
    assert registry["coined_animals"][0]["signature"] == [["BH.breadth", "HI"], ["TR.O", "LO"]] and registry["coined_animals"][0]["image"] == BEAVER_IMAGE
    batch_one = (env.stg / "batches" / "batch_001.json").read_bytes()
    assert env.stage(packets, "--batch", "2") == 0                  # the manual command still works; the assembler had already done it
    item = env.batch_item("batch_002", "Eli Coin")
    assert item["packet"]["coin_recommended"]["registry_match"]["animal"] == "Beaver" and item["packet"]["coin_recommended"]["value"]
    assert [e["animal"] for e in item["packet"]["coined_animals"]] == ["Beaver"]
    # the registry is not part of the hash: the staged hash is unchanged and still matches the packet content
    assert item["packet_sha256"] == before["packet_sha256"] == packets["Eli Coin"]["packet_sha256"] == P.content_sha256(item["packet"])
    assert (env.stg / "batches" / "batch_001.json").read_bytes() == batch_one        # only batch 2 was rebuilt


def test_earlier_briefs_are_not_stale_after_the_registry_grows(env):
    series_after_batch_one(env)
    briefs = env.briefs()["briefs"]
    fresh = coin_packets(finished=briefs, registry_images={"Beaver": BEAVER_IMAGE})      # what the desk recomputes: a whole build with the grown registry
    assert briefs["Dana Coin"]["packet_sha256"] == fresh["Dana Coin"]["packet_sha256"]       # not stale
    assert fresh["Eli Coin"]["coin_recommended"]["registry_match"]["animal"] == "Beaver"     # and the registry did grow
    staged = env.batch_item("batch_002", "Eli Coin")["packet"]
    assert staged["coin_recommended"] == fresh["Eli Coin"]["coin_recommended"]               # restaging equals a full rebuild
    assert staged["coined_animals"] == fresh["Eli Coin"]["coined_animals"]


def test_assemble_judges_a_batch_against_the_registry_offer_its_writer_saw(env):
    series_after_batch_one(env)
    env.out("batch_002", {"Eli Coin": coin_brief("Otter")})   # the file's packet offers no match; the staged one says Beaver
    assert env.assemble("--batch", "2") == 1
    details = [i["detail"] for i in env.issues("batch_002")["failed"]["Eli Coin"]["issues"] if i["kind"] == "archetype_misfit"]
    assert any("animal must be Beaver" in d for d in details), details


def test_batch_two_is_refused_until_batch_one_has_been_assembled(env, capsys):
    packets = coin_packets()
    assert env.stage(packets, "--batch-size", "1") == 0
    assert env.stage(packets, "--batch", "2") == 2 and "batch_001" in capsys.readouterr().err
    assert env.stage(packets, "--batch", "2", "--force") == 0
    assert env.stage(packets, "--batch", "1") == 0            # nothing precedes batch 1
    assert env.stage(packets, "--batch", "9") == 2 and "batch_009" in capsys.readouterr().err


def test_the_exemplars_seed_is_offered_from_batch_one(env):
    seed = [{"animal": "Marten", "descriptor": "practical and wide-ranging", "image": "a marten in the high branches", "first_member": "Gold",
             "signature": [["BH.breadth", "hi"], ["TR.O", "lo"]]}]
    env.seed(seed)
    packets = coin_packets(coined=P.registry_seed({"coined_registry": seed}))
    assert env.stage(packets, "--batch-size", "1") == 0 and env.stage(packets, "--batch", "1") == 0
    packet = env.batch_item("batch_001", "Dana Coin")["packet"]
    assert packet["coin_recommended"]["registry_match"]["animal"] == "Marten"
    assert [e["animal"] for e in packet["coined_animals"]] == ["Marten"]


def test_batch_mode_refuses_packets_built_with_a_registry_the_series_does_not_have(env, capsys):
    ghost = [{"animal": "Ghost", "descriptor": "x and y", "image": None, "first_member": None,
              "signature": [["TR.O", "lo"], ["BH.breadth", "lo"]]}]
    packets = coin_packets(coined=ghost)                      # e.g. the builder was run with --briefs on an older briefs file
    assert env.stage(packets, "--batch-size", "1") == 0
    assert env.stage(packets, "--batch", "1") == 2 and "Ghost" in capsys.readouterr().err


def test_series_assemble_judges_only_its_batch_and_never_writes_a_receipt(env):
    assert env.stage(fixture_packets(), "--batch-size", "2") == 0
    alex = P.load_json(env.stg / "manifest.json")["members"]["Alex Rich"]["batch"]
    env.out(alex, {"Alex Rich": T.good_brief()})              # the other batch has not been written yet
    assert env.assemble("--batch", str(int(alex[-3:]))) == 0
    assert env.issues(alex)["passed"] == ["Alex Rich"]
    assert len(list((env.stg / "issues").glob("*.json"))) == 1
    with pytest.raises(SystemExit):
        env.assemble("--batch", str(int(alex[-3:])), "--write-receipt")


# ------------------------------------------------------------------ pilot 2 review: the harness ----
def two_batches(env):
    """Alex Rich, Beth Thin and Cam Floor in two batches; returns {batch: [members]}."""
    assert env.stage(fixture_packets(), "--batch-size", "2") == 0
    return P.load_json(env.stg / "manifest.json")["batches"]


def test_a_full_run_fails_closed_when_a_batch_has_no_out_file_and_lists_its_members(env, capsys):
    batches = two_batches(env)
    done, absent = list(batches)
    env.out(done, {n: T.good_brief() for n in batches[done] if n == "Alex Rich"})
    assert env.assemble() == 2
    err = capsys.readouterr().err
    assert "FAIL CLOSED" in err and absent in err and all(n in err for n in batches[absent])
    assert not env.briefs_path.exists() and not (env.stg / "registry.json").exists()           # nothing was merged
    env.out(absent, {})
    assert env.assemble() in (0, 1)                                                           # present, if empty: the run goes on and reports missing
    assert set(env.issues(absent)["missing"]) == set(batches[absent])


def test_a_series_run_may_leave_the_later_batches_unwritten(env):
    batches = two_batches(env)
    first = list(batches)[0]
    env.out(first, {n: T.good_brief() for n in batches[first] if n == "Alex Rich"})
    assert env.assemble("--batch", str(int(first[-3:]))) in (0, 1)


def test_assembling_restages_every_later_batch_with_the_registry_and_avoid_phrases_so_far(env):
    packets = series_after_batch_one(env)
    item = env.batch_item("batch_002", "Eli Coin")
    assert item["packet"]["coin_recommended"]["registry_match"]["animal"] == "Beaver" and item["packet"]["coin_recommended"]["value"]
    assert [e["animal"] for e in item["packet"]["coined_animals"]] == ["Beaver"] and item["packet"]["avoid_phrases"][:len(P.SEED_AVOID_PHRASES)] == list(P.SEED_AVOID_PHRASES)
    assert item["packet_sha256"] == packets["Eli Coin"]["packet_sha256"] == P.content_sha256(item["packet"])
    manifest = P.load_json(env.stg / "manifest.json")
    registry = P.load_json(env.stg / "registry.json")
    first, second = manifest["batch_runs"]["batch_001"], manifest["batch_runs"]["batch_002"]
    assert second["registry_sha256"] == S.registry_sha256(registry["coined_animals"]) != first["registry_sha256"]
    assert second["writer_prompt_sha256"] == first["writer_prompt_sha256"] == P.sha256_file(env.prompt) and second["restaged_utc"]
    assert registry["registry_sha256"] == second["registry_sha256"]


def test_a_batch_that_has_writer_output_is_not_restaged(env):
    packets = coin_packets()
    assert env.stage(packets, "--batch-size", "1") == 0
    env.out("batch_002", {"Eli Coin": coin_brief("Otter")})                      # batch 2 is already written
    before = (env.stg / "batches" / "batch_002.json").read_bytes()
    env.images({"Beaver": BEAVER_IMAGE})
    env.out("batch_001", {"Dana Coin": coin_brief()})
    env.assemble("--batch", "1")
    assert (env.stg / "batches" / "batch_002.json").read_bytes() == before


def test_the_run_is_refused_when_the_writer_prompt_changed_after_staging(env, capsys):
    assert env.stage(fixture_packets("Alex Rich")) == 0
    env.out("batch_001", {"Alex Rich": T.good_brief()})
    env.prompt.write_text("writer prompt v2", encoding="utf-8")
    assert env.assemble() == 2
    err = capsys.readouterr().err
    assert "FAIL CLOSED" in err and "prompt" in err and not env.briefs_path.exists()


def test_the_run_is_refused_when_it_would_mix_prompt_shas_in_the_briefs_file(env, capsys):
    assert env.stage(fixture_packets("Alex Rich")) == 0
    env.briefs_path.parent.mkdir(parents=True)
    P.dump_atomic({"schema": V.BRIEFS_SCHEMA, "briefs": {"Old Member": {"x": 1}},
                   "writer": {"Old Member": {"model": "m", "effort": "e", "prompt_sha256": "a" * 64, "written_at": "x"}}}, env.briefs_path)
    env.out("batch_001", {"Alex Rich": T.good_brief()})
    assert env.assemble() == 2 and "prompt" in capsys.readouterr().err
    assert "Alex Rich" not in env.briefs()["briefs"]


def gold_rows():
    return [{"display_name": "Hakeem Jeffries", "archetype": {"animal": "Bull"}}, {"display_name": "Mike Johnson", "archetype": {"animal": "Terrier"}},
            {"display_name": "Brian Fitzpatrick", "archetype": {"animal": "Beaver"}}]


def animal_fake(name, *, suggested=None, coin=False, match=None):
    packet = fake(name, "House", "Democrat")
    packet["suggested_animal"] = suggested
    packet["packet_sha256"] = P.content_sha256(packet)
    packet["coin_recommended"] = {"value": coin or bool(match), "registry_match": {"animal": match} if match else None}
    return packet


def test_exclude_same_animal_exemplars_lists_the_gold_of_other_animals_per_member(env):
    env.seed([], gold_rows())
    packets = {"A Bull": animal_fake("A Bull", suggested="Bull"), "B Coin": animal_fake("B Coin", suggested="Bull", coin=True),
               "C Beaver": animal_fake("C Beaver", suggested="Owl", match="Beaver"), "D Terrier": animal_fake("D Terrier", suggested="Terrier")}
    assert env.stage(packets, "--exclude-same-animal-exemplars") == 0
    doc = P.load_json(env.stg / "batches" / "batch_001.json")
    assert doc["exemplars"] == {"A Bull": ["Mike Johnson", "Brian Fitzpatrick"],
                                "B Coin": ["Hakeem Jeffries", "Mike Johnson", "Brian Fitzpatrick"],          # a new animal: nothing shares it
                                "C Beaver": ["Hakeem Jeffries", "Mike Johnson"], "D Terrier": ["Hakeem Jeffries", "Brian Fitzpatrick"]}
    assert P.load_json(env.stg / "manifest.json")["exclude_same_animal_exemplars"] is True


def test_without_the_option_no_exemplar_lists_are_written(env):
    env.seed([], gold_rows())
    assert env.stage({"A Bull": animal_fake("A Bull", suggested="Bull")}) == 0
    assert "exemplars" not in P.load_json(env.stg / "batches" / "batch_001.json")
    assert P.load_json(env.stg / "manifest.json")["exclude_same_animal_exemplars"] is False


def test_a_restaged_batch_keeps_its_exemplar_lists(env):
    env.seed([], gold_rows())
    packets = coin_packets()
    assert env.stage(packets, "--batch-size", "1", "--exclude-same-animal-exemplars") == 0
    assert P.load_json(env.stg / "batches" / "batch_002.json")["exemplars"] == {"Eli Coin": ["Hakeem Jeffries", "Mike Johnson", "Brian Fitzpatrick"]}
    env.images({"Beaver": BEAVER_IMAGE})
    env.out("batch_001", {"Dana Coin": coin_brief()})
    env.assemble("--batch", "1")                                                                 # restages batch 2, now with a Beaver registry match
    assert P.load_json(env.stg / "batches" / "batch_002.json")["exemplars"] == {"Eli Coin": ["Hakeem Jeffries", "Mike Johnson"]}


def test_a_new_coin_without_an_image_is_listed_not_offered_and_a_bad_image_fails_closed(env, capsys):
    packets = coin_packets()
    assert env.stage(packets, "--batch-size", "1") == 0
    env.out("batch_001", {"Dana Coin": coin_brief()})
    env.assemble("--batch", "1")
    registry = P.load_json(env.stg / "registry.json")
    assert registry["coined_animals"] == [] and [x["animal"] for x in registry["pending_images"]] == ["Beaver"]
    assert "PENDING IMAGE" in capsys.readouterr().out
    assert P.load_json(env.stg / "batches" / "batch_002.json")["items"][0]["packet"]["coined_animals"] == []
    env.images({"Beaver": "a beaver that builds with others, always, in every kind of weather"})
    assert env.assemble("--batch", "1") == 2 and "image" in capsys.readouterr().err


def test_a_restaged_packet_is_what_a_rebuild_with_that_registry_would_say():
    packet = animal_fake("X", suggested="Bull")
    packet["coin_recommended"] = {"value": True, "template_coin": False, "registry_match": {"animal": "Beaver"}}      # decided against an older registry
    packet["packet_sha256"] = P.content_sha256(packet)
    rebuilt = S.batch_document("batch_001", ["X"], {"X": packet}, [], [], None, rebuild=True)["items"][0]["packet"]["coin_recommended"]
    assert rebuilt["value"] is False and rebuilt["registry_match"] is None
    first = S.batch_document("batch_001", ["X"], {"X": packet}, [], [], None, rebuild=False)["items"][0]["packet"]["coin_recommended"]
    assert first["value"] is True and first["registry_match"] == {"animal": "Beaver"}                                  # the first staging keeps the builder's call


def test_a_restaged_packet_drops_the_signature_items_of_an_older_registry_match():
    packet = animal_fake("X", suggested="Bull")
    template = P.signature_items(packet)
    packet["coin_recommended"] = {"value": True, "template_coin": False, "registry_match": {"animal": "Beaver"}}
    packet["signature_items"] = ["STALE.a", "STALE.b"]                    # the old Beaver row's items (check 26 would demand them)
    packet["packet_sha256"] = P.content_sha256(packet)
    rebuilt = S.batch_document("batch_001", ["X"], {"X": packet}, [], [], None, rebuild=True)["items"][0]["packet"]
    assert rebuilt["signature_items"] == template
    packet["coin_recommended"]["template_coin"] = True                    # a template coin with no registry match has no items yet
    packet["packet_sha256"] = P.content_sha256(packet)
    rebuilt = S.batch_document("batch_001", ["X"], {"X": packet}, [], [], None, rebuild=True)["items"][0]["packet"]
    assert rebuilt["signature_items"] == []


# ----------------------------------------------------------------- pilot 3: binding, frozen registry, per-batch exemplar files ----
def second_rich(packets):
    """A second member with Alex Rich's evidence (same surname, so the same good brief fits both)."""
    clone = copy.deepcopy(packets["Alex Rich"])
    clone["member"]["display_name"] = "Bo Rich"
    clone["packet_sha256"] = P.content_sha256(clone)
    return {"Alex Rich": packets["Alex Rich"], "Bo Rich": clone}


def test_a_write_receipt_run_on_the_series_output_passes_binding(env):
    packets = second_rich(fixture_packets("Alex Rich"))
    assert env.stage(packets, "--batch-size", "1") == 0
    where = {n: m["batch"] for n, m in P.load_json(env.stg / "manifest.json")["members"].items()}
    staged = {n: env.batch_item(where[n], n)["packet_sha256"] for n in packets}
    for name in ("Alex Rich", "Bo Rich"):                                             # one batch at a time, as the series run goes
        env.out(where[name], {name: T.good_brief()})                                  # the writer's output carries no packet_sha256
        assert env.assemble("--batch", str(int(where[name][-3:]))) == 0
    briefs = env.briefs()["briefs"]
    assert {n: b["packet_sha256"] for n, b in briefs.items()} == staged == {n: packets[n]["packet_sha256"] for n in packets}     # stamped from the staged item
    assert all("packet_sha256" not in P.load_json(env.stg / "out" / (b + ".json"))[n] for n, b in where.items())
    assert env.assemble("--write-receipt") == 0
    receipt = P.load_json(env.receipt)
    assert receipt["status"] == "PASS" and receipt["counts"] == {"briefs": 2, "passed": 2, "failed": 0}
    assert V.validate_all(briefs, packets, require_binding=True)["failed"] == []      # require_binding: every brief names the packet it was written against


MARTEN = {"animal": "Marten", "descriptor": "practical and wide-ranging", "image": "climbs high and hunts alone", "priority": 1, "seed": False,
          "signatures": [[["BH.breadth", "HI"], ["TR.O", "LO"]]]}


def frozen_file(tmp_path, members=("Dana Coin", "Eli Coin"), animals=(MARTEN,)):
    path = tmp_path / "frozen.json"
    P.dump_atomic({"schema": "member-briefs-v3-coined-registry", "status": "FROZEN", "frozen_at": "2026-10-21", "source_packets_sha256": "ab" * 32,
                   "animals": list(animals), "assignments": {m: {"animal": "Marten", "source": "precoin", "matched_signature": [["BH.breadth", "HI"], ["TR.O", "LO"]]}
                                                              for m in members}}, path)
    return path


def test_a_frozen_registry_assigns_every_packet_its_animal_and_records_its_hash(env, tmp_path):
    packets = coin_packets()
    frozen = frozen_file(tmp_path)
    assert env.stage(packets, "--batch-size", "1", "--frozen-registry", frozen) == 0
    manifest = P.load_json(env.stg / "manifest.json")
    sha = S.registry_sha256(P.frozen_animals(P.load_frozen_registry(frozen)))
    assert manifest["frozen_registry"]["sha256"] == P.sha256_file(frozen) and manifest["frozen_registry"]["registry_sha256"] == sha
    assert {r["registry_sha256"] for r in manifest["batch_runs"].values()} == {sha} and (env.stg / "frozen_registry.json").is_file()
    for name, bid in (("Dana Coin", "batch_001"), ("Eli Coin", "batch_002")):
        item = env.batch_item(bid, name)
        assert item["packet"]["coin_recommended"]["registry_match"]["animal"] == "Marten" and item["packet"]["signature_items"]
        assert [e["animal"] for e in item["packet"]["coined_animals"]] == ["Marten"]
        assert item["packet_sha256"] == packets[name]["packet_sha256"] == P.content_sha256(item["packet"])


def test_a_frozen_run_fails_closed_on_a_coin_member_the_registry_lacks(env, tmp_path, capsys):
    assert env.stage(coin_packets(), "--batch-size", "1", "--frozen-registry", frozen_file(tmp_path, members=("Dana Coin",))) == 2
    err = capsys.readouterr().err
    assert "Eli Coin" in err and "Dana Coin" not in err and not (env.stg / "batches").exists()
    assert env.stage(coin_packets(), "--frozen-registry", tmp_path / "missing.json") == 2


def test_in_a_frozen_run_batches_assemble_in_any_order_nothing_grows_and_nothing_is_restaged(env, tmp_path):
    packets = coin_packets()
    assert env.stage(packets, "--batch-size", "1", "--frozen-registry", frozen_file(tmp_path)) == 0
    later = (env.stg / "batches" / "batch_002.json").read_bytes()
    assert S.restage_unwritten(env.stg, packets, [], [], P.load_json(env.stg / "manifest.json")["writer_prompt_sha256"], env.exemplars) == ([], {})
    assert (env.stg / "batches" / "batch_002.json").read_bytes() == later              # nothing is unwritten that a frozen run would restage
    env.out("batch_002", {"Eli Coin": coin_brief("Marten")})                           # batch 2 first: no serial requirement
    env.assemble("--batch", "2")
    env.out("batch_001", {"Dana Coin": coin_brief("Marten")})
    env.assemble("--batch", "1")
    registry = P.load_json(env.stg / "registry.json")
    assert [e["animal"] for e in registry["coined_animals"]] == ["Marten"] and registry["pending_images"] == [] and registry["frozen"] is True
    assert registry["registry_sha256"] == P.load_json(env.stg / "manifest.json")["frozen_registry"]["registry_sha256"]
    assert (env.stg / "batches" / "batch_002.json").read_bytes() == later
    assert env.stage(packets, "--batch", "2") == 0 and (env.stg / "batches" / "batch_002.json").read_bytes() == later         # the manual restage has nothing to do


def test_a_frozen_run_refuses_a_brief_whose_animal_is_not_the_assigned_or_suggested_one(env, tmp_path, capsys):
    packets = coin_packets()
    assert env.stage(packets, "--batch-size", "2", "--frozen-registry", frozen_file(tmp_path)) == 0
    env.out("batch_001", {"Dana Coin": coin_brief("Marten"), "Eli Coin": coin_brief("Otter")})            # a new coin for Eli
    assert env.assemble("--batch", "1") == 1
    briefs = env.briefs()["briefs"]
    assert list(briefs) == ["Dana Coin"]                                                  # the refused brief was not merged
    issues = env.issues("batch_001")
    assert list(issues["refused"]) == ["Eli Coin"] and "Marten" in issues["refused"]["Eli Coin"] and "Otter" in issues["refused"]["Eli Coin"]
    assert "REFUSED Eli Coin" in capsys.readouterr().out and issues["missing"] == ["Eli Coin"]
    env.out("batch_001", {"Dana Coin": coin_brief("Marten"), "Eli Coin": coin_brief("Marten")})
    env.assemble("--batch", "1")
    assert set(env.briefs()["briefs"]) == {"Dana Coin", "Eli Coin"} and env.issues("batch_001")["refused"] == {}


def test_a_frozen_run_holds_a_template_member_to_the_suggested_animal(env, tmp_path):
    packets = fixture_packets("Alex Rich")                                             # Bull, no coin
    assert env.stage(packets, "--frozen-registry", frozen_file(tmp_path, members=())) == 0
    wrong = T.good_brief()
    wrong["archetype"]["animal"] = "Owl"
    env.out("batch_001", {"Alex Rich": wrong})
    assert env.assemble() == 1
    assert list(env.issues()["refused"]) == ["Alex Rich"] and "Bull" in env.issues()["refused"]["Alex Rich"]
    env.out("batch_001", {"Alex Rich": T.good_brief()})
    assert env.assemble() == 0 and env.issues()["refused"] == {}


def test_per_batch_exemplar_files_hold_the_gold_every_member_of_the_batch_may_see(env):
    rows = [{**r, "do": ["x"], "dont": ["y"]} for r in gold_rows()]
    env.seed([], rows)
    packets = {"A Bull": animal_fake("A Bull", suggested="Bull"), "B Terrier": animal_fake("B Terrier", suggested="Terrier"),
               "C Owl": animal_fake("C Owl", suggested="Owl")}
    assert env.stage(packets, "--exclude-same-animal-exemplars") == 0
    doc = P.load_json(env.stg / "batches" / "exemplars_001.json")
    assert [r["display_name"] for r in doc["exemplars"]] == ["Brian Fitzpatrick"]         # Jeffries (Bull) and Johnson (Terrier) are someone's animal
    assert doc["exemplars"][0]["do"] == ["x"] and doc["batch"] == "batch_001" and doc["coined_registry"] == []
    assert P.load_json(env.stg / "batches" / "batch_001.json")["exemplars"]["A Bull"] == ["Mike Johnson", "Brian Fitzpatrick"]       # the per-member lists stay


def test_exemplar_files_are_written_per_batch_and_only_when_asked(env, tmp_path):
    rows = [{**r, "do": ["x"], "dont": ["y"]} for r in gold_rows()]
    env.seed([], rows)
    packets = {n: animal_fake(n, suggested="Bull") for n in ("A", "B", "C")}
    assert env.stage(packets, "--batch-size", "2", "--exclude-same-animal-exemplars") == 0
    names = {b: [r["display_name"] for r in P.load_json(env.stg / "batches" / ("exemplars_%s.json" % b[-3:]))["exemplars"]] for b in ("batch_001", "batch_002")}
    assert names == {"batch_001": ["Mike Johnson", "Brian Fitzpatrick"], "batch_002": ["Mike Johnson", "Brian Fitzpatrick"]}
    (tmp_path / "other").mkdir()
    other = Env(tmp_path / "other")
    other.seed([], rows)
    assert other.stage(packets) == 0 and not list((other.stg / "batches").glob("exemplars_*.json"))


def test_a_restaged_batch_rewrites_its_exemplar_file(env):
    rows = [{**r, "do": ["x"], "dont": ["y"]} for r in gold_rows()]
    env.seed([], rows)
    assert env.stage(coin_packets(), "--batch-size", "1", "--exclude-same-animal-exemplars") == 0
    assert len(P.load_json(env.stg / "batches" / "exemplars_002.json")["exemplars"]) == 3          # a coin: no gold shares its animal
    env.images({"Beaver": BEAVER_IMAGE})
    env.out("batch_001", {"Dana Coin": coin_brief()})
    env.assemble("--batch", "1")                                                                    # Eli is now Beaver's: Fitzpatrick leaves the file
    assert [r["display_name"] for r in P.load_json(env.stg / "batches" / "exemplars_002.json")["exemplars"]] == ["Hakeem Jeffries", "Mike Johnson"]
