"""Freeze dated observed language/exposure; no personality model or outcome access.

Run from any directory: python universe_psychology_features.py [--self-test-only].
The only writable paths are the CSV and receipt in the designated research output.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import html
import json
import math
from pathlib import Path
import re
import sqlite3
import unicodedata

import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs/cosponsor_universe_20260905"
REFERENCE = ROOT / "data/staffer_network/reference/congress-legislators/750c0608efb6ef1fc3257ba72c99af3771d35088"
SOURCES = ("CREC", "INTERVIEW")
CUTOFFS = {117: dt.date(2021, 1, 3), 118: dt.date(2023, 1, 3)}
WORD = re.compile(r"[a-z]+(?:'[a-z]+)?")
LEXICONS = {
    "self_i": set("i me my mine myself i'm i've i'll i'd".split()),
    "collective_we": set("we us our ours ourselves we're we've we'll we'd".split()),
    "negation": set("no not never none neither nor nobody nothing nowhere cannot can't don't doesn't didn't isn't aren't wasn't weren't won't wouldn't couldn't shouldn't hasn't haven't hadn't".split()),
    "uncertainty": set("maybe perhaps possibly probably might may could uncertain uncertainty unsure unclear tentative apparently seems seem suggests suggest".split()),
}
STAT_NAMES = ["log_turns", "log_words", "log_packages", "words_per_turn", "cutoff_share",
              "questions_per_1000_words", "self_i_per_1000_words", "collective_we_per_1000_words",
              "negation_per_1000_words", "uncertainty_per_1000_words", "missing", "thin_under_800_words"]
FEATURES = ["psych_" + source.lower() + "_" + stat for source in SOURCES for stat in STAT_NAMES]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def name_key(value):
    # Full-name equality only. Never infer nickname, surname, or first initial.
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode().casefold()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def clean_text(value):
    return " ".join(html.unescape(str(value or "")).replace("’", "'").replace("‘", "'").split())


def parse_day(value):
    text = str(value or "")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return None
    try:
        return dt.date.fromisoformat(text)
    except ValueError:
        return None


def in_window(day, cutoff):
    return day is not None and cutoff.replace(year=cutoff.year - 2) <= day < cutoff


def is_cutoff(text):
    return bool(text) and (text.endswith(("--", "—", "…", "...")) or text[-1] not in ".!?\"')”")


def resolve(alias_map, name):
    matches = alias_map.get(name_key(name), set())
    return next(iter(matches)) if len(matches) == 1 else None


def identities():
    members = {}
    aliases = collections.defaultdict(set)
    paths = [REFERENCE / name for name in ("legislators-current.yaml", "legislators-historical.yaml")]
    paths += [ROOT / "data/engine/congestion.json", ROOT / "fec/legislators.csv"]
    for path in paths[:2]:
        for row in yaml.load(path.read_bytes(), Loader=yaml.CSafeLoader):
            mid = row.get("id", {}).get("bioguide")
            if not mid:
                continue
            terms = [(parse_day(t["start"]), parse_day(t["end"]), t["type"])
                     for t in row.get("terms", []) if t.get("type") in ("rep", "sen")]
            if not terms:
                continue
            if any(a is None or b is None for a, b, _ in terms):
                raise ValueError("Malformed reference term: " + mid)
            members.setdefault(mid, set()).update(terms)
            person = row.get("name", {})
            names = [person.get("official_full"), " ".join(filter(None, [person.get("first"), person.get("last")])),
                     " ".join(filter(None, [person.get("first"), person.get("middle"), person.get("last")]))]
            if person.get("nickname"):
                names.append(person["nickname"] + " " + person.get("last", ""))
            for value in names:
                if value and len(name_key(value).split()) >= 2:
                    aliases[name_key(value)].add(mid)
    for row in json.loads(paths[2].read_text(encoding="utf-8")):
        if row.get("bioguide") in members:
            aliases[name_key(row["member"])].add(row["bioguide"])
    with paths[3].open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("bioguide_id") in members:
                aliases[name_key(row["full_name"])].add(row["bioguide_id"])
    return members, aliases, paths


class Aggregate:
    def __init__(self):
        self.turns = self.words = self.cutoffs = self.questions = 0
        self.lex = collections.Counter()
        self.packages = set()
        self.days = set()

    def add(self, text, package, day):
        words = WORD.findall(text.casefold())
        if not words:
            return False
        self.turns += 1
        self.words += len(words)
        self.cutoffs += is_cutoff(text)
        self.questions += text.count("?")
        self.packages.add(package)
        self.days.add(day.isoformat())
        counts = collections.Counter(words)
        for label, lexicon in LEXICONS.items():
            self.lex[label] += sum(counts[word] for word in lexicon)
        return True

    def values(self):
        # Counts really are zero if there are no retained rows; undefined rates are blank.
        rates = [self.words / self.turns, self.cutoffs / self.turns,
                 1000 * self.questions / self.words] if self.words else [None] * 3
        rates += [1000 * self.lex[key] / self.words if self.words else None for key in LEXICONS]
        return [math.log1p(self.turns), math.log1p(self.words), math.log1p(len(self.packages)),
                *rates, int(not self.words), int(self.words < 800)]


def self_test():
    cutoff = CUTOFFS[117]
    assert in_window(dt.date(2019, 1, 3), cutoff)
    assert in_window(dt.date(2021, 1, 2), cutoff)
    assert not in_window(dt.date(2019, 1, 2), cutoff)
    assert not in_window(cutoff, cutoff)
    assert parse_day("2020-02-30") is None and parse_day("2020") is None
    assert resolve({"alex smith": {"A", "B"}}, "Alex Smith") is None
    assert resolve({"alex smith": {"A"}}, "Smith") is None
    empty = Aggregate().values()
    assert empty[:3] == [0, 0, 0] and empty[3:10] == [None] * 7 and empty[10:] == [1, 1]
    a = Aggregate()
    a.add("I might not agree. We ask why?", "P", dt.date(2020, 1, 1))
    assert a.words == 7 and a.questions == 1 and a.lex == dict(self_i=1, collective_we=1, negation=1, uncertainty=1)
    assert len(a.values()) == len(STAT_NAMES)
    assert clean_text("A &amp; B\nC") == "A & B C"
    assert is_cutoff("I think --") and not is_cutoff("I think.")
    # Exact-content dedup excludes rebroadcasts inside each member/source/window.
    keys = {("A", "INTERVIEW", clean_text(t).casefold()) for t in ["I agree.", "I  agree."]}
    assert len(keys) == 1
    return 13


def build():
    csv_path, receipt_path = OUT / "psychology_history.csv", OUT / "psychology_history_receipt.json"
    if csv_path.exists() or receipt_path.exists():
        raise RuntimeError("Frozen output already exists; do not silently regenerate")
    checks = self_test()
    members, aliases, id_paths = identities()
    db = ROOT / "social_media.db"
    sources = [db, *id_paths, Path(__file__).resolve()]
    before = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    aggregates = collections.defaultdict(Aggregate)
    counts = collections.Counter()
    rejected_names = collections.Counter()
    selected_hash = hashlib.sha256()
    unique = set()
    eligible = {}
    for congress, cutoff in CUTOFFS.items():
        end = cutoff.replace(year=cutoff.year + 2)
        eligible[congress] = {mid for mid, terms in members.items()
                              if any(a < end and b > cutoff for a, b, _ in terms)}
    con = sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=60)
    con.execute("PRAGMA query_only=1")
    con.execute("BEGIN")
    query = "SELECT rowid,member,date,source,chamber,package,text FROM speeches WHERE source IN ('CREC','INTERVIEW') ORDER BY rowid"
    for rowid, name, date_value, source, chamber, package, raw in con.execute(query):
        counts["source_rows_" + source] += 1
        day = parse_day(date_value)
        if day is None:
            counts["invalid_date_" + source] += 1
            continue
        congresses = [cg for cg, cutoff in CUTOFFS.items() if in_window(day, cutoff)]
        if not congresses:
            counts["outside_both_windows_" + source] += 1
            continue
        mid = resolve(aliases, name)
        if mid is None:
            reason = "ambiguous" if len(aliases.get(name_key(name), set())) > 1 else "unmatched"
            counts[reason + "_identity_" + source] += 1
            rejected_names[reason + ":" + str(name)] += 1
            continue
        # Interview 'chamber' actually stores show names in many rows: never use it as office.
        required = {"house": "rep", "senate": "sen"}.get(str(chamber).casefold()) if source == "CREC" else None
        if source == "CREC" and required is None:
            counts["invalid_crec_chamber"] += 1
            continue
        if not any(a <= day < b and (required is None or kind == required) for a, b, kind in members[mid]):
            counts["no_matching_federal_service_on_source_date_" + source] += 1
            continue
        text = clean_text(raw)
        if not text or not package:
            counts["empty_text_or_package_" + source] += 1
            continue
        text_hash = hashlib.sha256(text.casefold().encode("utf-8")).hexdigest()
        for cg in congresses:
            if mid not in eligible[cg]:
                counts[f"{cg}_not_serving_anytime_in_target_congress_{source}"] += 1
                continue
            key = (cg, mid, source, text_hash)
            if key in unique:
                counts[f"{cg}_duplicate_text_{source}"] += 1
                continue
            unique.add(key)
            if not aggregates[(cg, mid, source)].add(text, str(package), day):
                counts[f"{cg}_no_word_tokens_{source}"] += 1
                continue
            selected_hash.update((json.dumps([cg, mid, day.isoformat(), source, package, rowid, text_hash],
                                             ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
            counts[f"{cg}_retained_{source}"] += 1
    con.rollback()
    con.close()
    after = {str(p.relative_to(ROOT)): sha(p) for p in sources}
    if after != before:
        raise RuntimeError("Source changed during extraction; output not written")
    OUT.mkdir(parents=True, exist_ok=True)
    metadata_cols = ["congress", "member", "feature_cutoff", "window_start"]
    report = {}
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(metadata_cols + FEATURES)
        for cg, cutoff in CUTOFFS.items():
            for mid in sorted(eligible[cg]):
                values = [value for source in SOURCES for value in aggregates[(cg, mid, source)].values()]
                assert len(values) == len(FEATURES)
                writer.writerow([cg, mid, cutoff.isoformat(), cutoff.replace(year=cutoff.year - 2).isoformat()] + values)
            report[str(cg)] = {"roster_ids": len(eligible[cg]), "sources": {}}
            for source in SOURCES:
                aa = [aggregates[(cg, mid, source)] for mid in eligible[cg]]
                days = [day for a in aa for day in a.days]
                report[str(cg)]["sources"][source] = dict(covered_members=sum(a.words > 0 for a in aa),
                    members_ge800_words=sum(a.words >= 800 for a in aa), turns=sum(a.turns for a in aa),
                    words=sum(a.words for a in aa), member_packages=sum(len(a.packages) for a in aa),
                    min_source_date=min(days) if days else None, max_source_date=max(days) if days else None)
    definitions = {
        "log_turns": "log1p retained attributed transcript turns after exact-content dedup; a turn is not a speech or interview",
        "log_words": "log1p regex word-token count from retained HTML-decoded member text",
        "log_packages": "log1p distinct nonempty original source package IDs represented by retained turns",
        "words_per_turn": "word tokens / retained turns; undefined if none",
        "cutoff_share": "fraction of turns ending --, em dash, ellipsis or lacking final punctuation; transcript formatting proxy",
        "questions_per_1000_words": "1000 * count of question-mark characters / word tokens",
        "self_i_per_1000_words": "1000 * frozen first-person-singular lexicon hits / word tokens",
        "collective_we_per_1000_words": "1000 * frozen first-person-plural lexicon hits / word tokens",
        "negation_per_1000_words": "1000 * frozen negation lexicon hits / word tokens",
        "uncertainty_per_1000_words": "1000 * frozen tentative-language lexicon hits / word tokens; includes modal may/could, not a latent trait",
        "missing": "1 iff no retained word tokens in this venue/window; rate fields blank/NaN, count fields zero",
        "thin_under_800_words": "1 iff fewer than 800 retained words, including missing; does not erase measured rates",
    }
    receipt = dict(schema="cosponsor-observed-style-history-v1", generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        scope="Observed text/style and source coverage only; no personality/psychological validity or causal persuasion claim",
        source_sha256_before=before, source_sha256_after=after, source_unchanged=True,
        selected_rows_sha256=selected_hash.hexdigest(), output_sha256=sha(csv_path), feature_count=len(FEATURES),
        feature_columns=FEATURES, metadata_columns=metadata_cols, feature_definitions=definitions,
        lexicons={key: sorted(values) for key, values in LEXICONS.items()}, token_regex=WORD.pattern,
        windows={str(cg): {"start_inclusive": cutoff.replace(year=cutoff.year - 2).isoformat(), "cutoff_exclusive": cutoff.isoformat()}
                 for cg, cutoff in CUTOFFS.items()}, populations=report, row_decisions=dict(counts),
        identity={"rule": "normalized full-name equality across pinned reference names and explicit canonical display-name aliases; refuse all multi-ID collisions",
                  "ambiguous_aliases": {key: sorted(ids) for key, ids in aliases.items() if len(ids) > 1},
                  "rejected_in_window_names": dict(rejected_names), "federal_service_required_on_document_date": True,
                  "crec_same_chamber_required": True, "interview_chamber_column_is_show_label_and_ignored": True,
                  "output_roster": "all Bioguide IDs with rep/sen term overlap anywhere in target Congress, including later entrants; no future traits/features used"},
        dedup="Within congress/member/source, casefolded whitespace-normalized HTML-decoded exact text SHA256; first source rowid wins. Cross-source texts remain separate venue evidence.",
        missingness="Blank rate fields mean unavailable, never zero trait. Any learner imputation must use training data only and retain missing flags.",
        normalization="Raw interpretable rates and log1p counts only; no cohort scaling, fitted model, future z-score, labels, 119 outcomes, or current personality artifacts read.",
        verification={"self_test_assertions": checks, "strict_window_and_full_name_tests": True, "source_hashes_stable": True},
        limitations=["2026-acquired reconstruction of source event/publication dates; no historical observation-time proof",
                     "Speech collection largely selected around current roster; historical departed members may be structurally missing",
                     "Exact source member name and service checks cannot independently recertify every collector attribution",
                     "Generic CHRG excluded; interviews before federal service excluded; no current LLM/Big5/behavioral calibration used",
                     "Full exact-content dedup can remove genuine repeated wording; remaining cross-package paraphrases may duplicate content",
                     "118 outcomes are already development data; this does not create an independent test; September5 forecasts unchanged"])
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(csv_path), "rows": sum(len(v) for v in eligible.values()), "features": len(FEATURES), "populations": report}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test-only", action="store_true")
    args = parser.parse_args()
    if args.self_test_only:
        print("boundary checks passed:", self_test())
    else:
        build()
