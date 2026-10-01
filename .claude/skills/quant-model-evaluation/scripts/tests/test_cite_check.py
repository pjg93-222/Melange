# -*- coding: utf-8 -*-
"""Tests for scripts/cite_check.py.

No test touches the network: cite_check.http_get (the script's only network call) is replaced by FakeNet, which
answers from canned registry records (exact URLs) and canned search results (by index and query words) and records
every request; cite_check._sleep is replaced by a recorder so back-off and Retry-After waits cost nothing. The single
live test is skipped unless QME_LIVE=1.
"""
from __future__ import annotations

import csv
import json
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import formatdate
from pathlib import Path

import pytest

from conftest import latest_report, latest_run_dir, sha256

import cite_check as cc

FIX = Path(__file__).resolve().parent / "fixtures" / "cite_check"
NONE_FOUND = re.compile(r"^NONE-FOUND@\d{4}-\d{2}-\d{2}$")
SEARCH_PREFIX = {"crossref": "https://api.crossref.org/works?", "openalex": "https://api.openalex.org/works?"}


# ----------------------------------------------------------------------------- canned registry answers
def cr(doi, title, authors, year, venue="", subtitle=None, online=None, **extra):
    """A CrossRef /works/<doi> envelope (its ["message"] is also a search item)."""
    msg = {"DOI": doi, "type": "journal-article", "title": [title], "issued": {"date-parts": [[year]]},
           "author": [{"family": f, "given": "A.", "sequence": "first" if i == 0 else "additional"}
                      for i, f in enumerate(authors)],
           "container-title": [venue] if venue else []}
    if subtitle:
        msg["subtitle"] = [subtitle]
    if online:
        msg["published-online"] = {"date-parts": [[online, 6, 1]]}
    msg.update(extra)
    return {"status": "ok", "message-type": "work", "message": msg}


def dc(doi, title, family, year, publisher="arXiv", related=()):
    """A DataCite /dois/<doi> document."""
    return {"data": {"id": doi, "type": "dois", "attributes": {
        "doi": doi, "titles": [{"title": title}], "publicationYear": year, "publisher": publisher,
        "creators": [{"name": f"{family}, A.", "nameType": "Personal", "familyName": family}],
        "types": {"resourceTypeGeneral": "Text"}, "relatedIdentifiers": list(related)}}}


def oa(doi, retracted=False):
    """An OpenAlex /works/doi:<doi> record."""
    return {"id": "https://openalex.org/W1", "doi": f"https://doi.org/{doi}", "is_retracted": retracted}


def items(*works):
    """A CrossRef search answer holding the given /works envelopes as items."""
    return 200, {"status": "ok", "message-type": "work-list", "message": {"items": [w["message"] for w in works]}}


class FakeNet:
    """Stands in for cite_check.http_get: canned answers (the last one repeats), every call recorded."""

    def __init__(self):
        self.routes, self.searches, self.calls, self.sleeps = {}, [], [], []

    def add(self, url, *answers):
        self.routes[url] = list(answers)

    def search(self, index, needle, *answers):
        """Answer searches on one index whose decoded URL contains `needle` (first match in the order added)."""
        self.searches.append((SEARCH_PREFIX[index], needle.lower(), list(answers)))

    def searched(self, index):
        return [u for u, _ in self.calls if u.startswith(SEARCH_PREFIX[index])]

    def doi(self, doi, ra="Crossref", record=None, openalex=None, registered=True):
        q = urllib.parse.quote(doi, safe="/")
        self.add(f"https://doi.org/api/handles/{q}", (200, {"responseCode": 1, "handle": doi}) if registered
                 else (404, {"responseCode": 100, "handle": doi}))
        self.add(f"https://doi.org/ra/{q}", (200, [{"DOI": doi, "RA": ra}]))
        base = "https://api.crossref.org/works/" if ra == "Crossref" else "https://api.datacite.org/dois/"
        if record is not None:
            self.add(base + q, *(record if isinstance(record, list) else [record if isinstance(record, tuple)
                                                                          else (200, record)]))
        self.add(f"https://api.openalex.org/works/doi:{q}",
                 (200, openalex) if openalex is not None else (404, {"error": "not found"}))

    def __call__(self, url, headers, timeout):
        self.calls.append((url, dict(headers)))
        answers = self.routes.get(url)
        if answers is None:
            text = urllib.parse.unquote(url).lower()
            answers = next((a for prefix, needle, a in self.searches if url.startswith(prefix) and needle in text), None)
        if answers is None:
            raise AssertionError(f"unexpected URL {url}")
        status, body, *hdrs = answers.pop(0) if len(answers) > 1 else answers[0]
        if isinstance(body, Exception):
            raise body
        return status, (hdrs[0] if hdrs else {}), body if isinstance(body, bytes) else json.dumps(body).encode()


@pytest.fixture
def fake(monkeypatch):
    f = FakeNet()
    monkeypatch.setattr(cc, "http_get", f)
    monkeypatch.setattr(cc, "_sleep", f.sleeps.append)
    return f


def run_inproc(tmp_path, *args):
    """Run cite_check in this process (so the fake network applies); each call gets its own --out folder."""
    out = tmp_path / f"out{len(list(tmp_path.glob('out*')))}"
    code = cc.run_main(cc.SCRIPT, cc.main, cc.build_parser(),
                       [str(a) for a in args] + ["--no-glassbox", "--quiet", "--out", str(out)])
    return code, out


def rows_of(out):
    with open(latest_run_dir(out) / "references.csv", encoding="utf-8", newline="") as fh:
        return {r["id"]: r for r in csv.DictReader(fh)}


def known_routes(fake):
    """Mocks behind fixtures/cite_check/known.bib: one planted case per grade and currency flag."""
    fake.doi("10.5555/qme.verified", openalex=oa("10.5555/qme.verified"), record=cr(
        "10.5555/qme.verified", "Campaign contributions and roll-call votes", ["Müller", "Smith"], 2020,
        "Journal of Financial Economics", subtitle="A panel study", online=2019))
    fake.doi("10.5555/qme.yeardrift", openalex=oa("10.5555/qme.yeardrift"), record=cr(
        "10.5555/qme.yeardrift", "Lobbying intensity and bank capital", ["García"], 2019, "The Review of Financial Studies"))
    fake.doi("10.5555/qme.hijack", openalex=oa("10.5555/qme.hijack"), record=cr(
        "10.5555/qme.hijack", "Weather forecasting with neural networks", ["Zhang"], 2021, "Atmospheric Research"))
    fake.doi("10.5555/qme.retracted", openalex=oa("10.5555/qme.retracted", retracted=True), record=cr(
        "10.5555/qme.retracted", "RETRACTED: Donor networks predict legislative success", ["Lee"], 2019,
        "American Political Science Review", **{"updated-by": [
            {"type": "retraction", "source": "retraction-watch", "record-id": 12345, "DOI": "10.5555/qme.notice",
             "updated": {"date-time": "2024-02-01T00:00:00Z"}},
            {"type": "retraction", "source": "publisher", "DOI": "10.5555/qme.notice"}]}))
    fake.doi("10.5555/qme.corrected", openalex=oa("10.5555/qme.corrected"), record=cr(
        "10.5555/qme.corrected", "Regulatory shocks and fintech entry", ["Okafor"], 2018, "The Journal of Finance",
        **{"updated-by": [{"type": "correction", "source": "publisher", "DOI": "10.5555/qme.erratum"}]}))
    fake.doi("10.5555/qme.ratelimited", record=(429, {"message": "rate limited"}, {"retry-after": "2"}))
    fake.doi("10.5555/qme.missing", registered=False)
    fake.doi("10.48550/arxiv.2106.07039", ra="DataCite", record=dc(
        "10.48550/arxiv.2106.07039", "Scalable influence maximization under uncertainty", "Chen", 2021))
    fake.search("crossref", "", items())  # anything else searched finds nothing in either index
    fake.search("openalex", "", (200, {"meta": {}, "results": []}))


def search_routes(fake):
    """Mocks behind fixtures/cite_check/search.bib: found by title, not found anywhere, and a near miss."""
    found = cr("10.5555/qme.found", "Moneyed interests and committee attention", ["Halloran", "Whitby"], 2011,
               "Legislative Studies Quarterly", subtitle="A panel of House markups")
    fake.search("crossref", "moneyed interests", items(cr("10.5555/qme.other", "Committee seats and fundraising",
                                                          ["Stone"], 2009), found))
    fake.doi("10.5555/qme.found", record=found, openalex=oa("10.5555/qme.found"))
    fake.search("crossref", "lobbying returns", items(cr("10.5555/qme.unrelated", "Weather forecasting with neural "
                                                         "networks", ["Zhang"], 2023)))
    fake.search("openalex", "lobbying returns", (200, {"meta": {}, "results": []}))
    fake.search("crossref", "deposit pricing", items(cr("10.5555/qme.near", "Deposit pricing and market power in "
                                                        "rural banking", ["Adeyemi"], 2016)))
    fake.search("openalex", "deposit pricing", (200, {"meta": {}, "results": []}))


# ----------------------------------------------------------------------------- known answers
def test_known_answers_one_per_grade(tmp_path, fake):
    known_routes(fake)
    code, out = run_inproc(tmp_path, "--bib", FIX / "known.bib")
    rows = rows_of(out)
    expect = {  # id: (R grade, C flag or None for NONE-FOUND@date, verdict, needs second reader)
        "verified2020": ("R-VERIFIED", None, "SURVIVES", ""),
        "yeardrift2020": ("R-MISMATCH-MINOR", None, "WOUNDED", ""),
        "hijack2021": ("R-IDENTIFIER-CONFLICT", None, "WOUNDED", "yes"),
        "retracted2019": ("R-VERIFIED", "RETRACTED", "KILLED", "yes"),
        "corrected2018": ("R-VERIFIED", "CORRECTED", "WOUNDED", ""),
        "ratelimited2022": ("R-UNVERIFIED-HERE", "NOT-CHECKED", "UNVERIFIED-HERE", ""),
        "unregistered2023": ("R-NOT-LOCATED", "NOT-CHECKED", "WOUNDED", "yes"),
        "chen2021arxiv": ("R-VERIFIED", None, "SURVIVES", ""),
        "nodoi2019": ("R-UNVERIFIED-HERE", "NOT-CHECKED", "UNVERIFIED-HERE", ""),
    }
    assert set(rows) == set(expect)
    for rid, (grade, flag, verdict, second) in expect.items():
        row = rows[rid]
        assert (row["r_grade"], row["verdict"], row["needs_second_reader"]) == (grade, verdict, second), rid
        assert NONE_FOUND.match(row["c_flag"]) if flag is None else row["c_flag"] == flag, (rid, row["c_flag"])
    assert code == 1  # WOUNDED/KILLED present
    rep = latest_report(out)
    assert rep["counts"] == {"SURVIVES": 2, "WOUNDED": 4, "KILLED": 1, "UNVERIFIED-HERE": 2}
    details = {c["title"].split(" ")[0]: c["detail"] for c in rep["checks"]}
    assert details["hijack2021"].startswith("needs second reader") and "another work" in details["hijack2021"]
    assert details["unregistered2023"].startswith("needs second reader")
    assert "year 2020 vs record 2019" in rows["yeardrift2020"]["notes"]
    assert "retraction-watch RW 12345" in rows["retracted2019"]["notes"] and "OpenAlex is_retracted" in rows[
        "retracted2019"]["notes"]
    assert rows["verified2020"]["matched_year"] == "2019/2020" and rows["verified2020"]["title_similarity"] == "1.0"
    assert rows["chen2021arxiv"]["registration_agency"] == "DataCite"
    assert "crossref.work:429x4" in rows["ratelimited2022"]["endpoints"]
    assert fake.sleeps.count(2.0) == 3  # Retry-After: 2 honoured before each of the three retries
    unregistered = rows["unregistered2023"]  # the unregistered DOI's title was searched: nothing matched
    assert "crossref.search:200" in unregistered["endpoints"] and "DOI not registered" in unregistered["notes"]
    assert "entry type 'misc' is not indexed" in rows["nodoi2019"]["notes"]
    assert all(not u.startswith(("https://api.crossref.org/works/10.5555/qme.missing", "https://api.openalex.org"
                                 "/works/doi:10.5555/qme.ratelimited")) for u, _ in fake.calls)
    run = latest_run_dir(out)
    assert {p.name for p in run.iterdir()} == {"report.json", "report.md", "references.csv", "cache"}
    assert len(list((run / "cache").glob("*.json"))) >= 20  # raw answers kept as receipts inside the run folder


def test_negative_control_nothing_flagged(tmp_path, fake):
    """Spelling variants, diacritics, print-vs-online year, abbreviated venue, dataset title prefixes and an
    addendum must not be flagged."""
    fake.doi("10.5555/qme.clean1", openalex=oa("10.5555/qme.clean1"), record=cr(
        "10.5555/qme.clean1", "Modeling the Behavior of Credit Unions", ["Sorensen"], 2022,
        "Journal of Banking & Finance", subtitle="Evidence from call reports", online=2021))
    fake.doi("10.5555/qme.dataset", ra="DataCite", record=dc(
        "10.5555/qme.dataset", "Replication data for: Lobbying disclosure and stock returns", "Vilhuber", 2022,
        publisher="Zenodo"))
    fake.doi("10.5555/qme.addendum", openalex=oa("10.5555/qme.addendum"), record=cr(
        "10.5555/qme.addendum", "The FAIR Guiding Principles for scientific data management and stewardship",
        ["Wilkinson"], 2016, "Scientific Data",
        **{"updated-by": [{"type": "addendum", "source": "publisher", "DOI": "10.5555/qme.add1"}]}))
    code, out = run_inproc(tmp_path, "--csl", FIX / "clean.json")
    rows = rows_of(out)
    assert [rows[k]["verdict"] for k in ("sorensen2021", "vilhuber2022", "wilkinson2016")] == ["SURVIVES"] * 3
    assert all(r["r_grade"] == "R-VERIFIED" for r in rows.values())
    assert rows["wilkinson2016"]["c_flag"] == "ADDENDUM" and NONE_FOUND.match(rows["vilhuber2022"]["c_flag"])
    assert code == 0 and latest_report(out)["counts"]["SURVIVES"] == 3


def test_context_line_catches_a_hijacked_doi(tmp_path, fake):
    known_routes(fake)
    md = tmp_path / "bib.md"
    md.write_text("- Muller and Smith (2020). Campaign contributions and roll-call votes. "
                  "https://doi.org/10.5555/qme.verified\n"
                  "- Nguyen (2021). Deposit insurance and credit union lending. doi:10.5555/qme.hijack\n",
                  encoding="utf-8")
    code, out = run_inproc(tmp_path, "--text", md)
    rows = rows_of(out)
    assert rows["10.5555/qme.verified"]["verdict"] == "SURVIVES"
    assert "names the record's author" in rows["10.5555/qme.verified"]["notes"]
    hijack = rows["10.5555/qme.hijack"]
    assert (hijack["r_grade"], hijack["verdict"], hijack["needs_second_reader"]) == (
        "R-IDENTIFIER-CONFLICT", "WOUNDED", "yes")
    assert code == 1
    code, out = run_inproc(tmp_path, "--text", md, "--no-context")  # without the context check: existence only
    assert rows_of(out)["10.5555/qme.hijack"]["r_grade"] == "R-VERIFIED" and code == 0


def test_mapped_ids_and_version_relations(tmp_path, fake):
    fake.doi("10.2139/ssrn.1234567", registered=False)
    fake.doi("10.3386/w31161", openalex=oa("10.3386/w31161"), record=cr(
        "10.3386/w31161", "Working papers and their published versions", ["Nakamura"], 2023))
    fake.doi("10.5555/qme.v1", ra="DataCite", record=dc(
        "10.5555/qme.v1", "Panel data release one", "Ruiz", 2021, publisher="Zenodo", related=[
            {"relationType": "IsObsoletedBy", "relatedIdentifier": "10.5555/qme.v2", "relatedIdentifierType": "DOI"}]))
    ids = tmp_path / "ids.txt"
    ids.write_text("ssrn:1234567\nhttps://www.nber.org/papers/w31161\n10.5555/qme.v1\n", encoding="utf-8")
    code, out = run_inproc(tmp_path, "--dois", ids)
    rows = {r["doi"]: r for r in rows_of(out).values()}
    ssrn = rows["10.2139/ssrn.1234567"]  # a mapped DOI that is not registered is not evidence of fabrication
    assert (ssrn["r_grade"], ssrn["id_type"]) == ("R-UNVERIFIED-HERE", "ssrn") and "may exist" in ssrn["notes"]
    assert (rows["10.3386/w31161"]["verdict"], rows["10.3386/w31161"]["id_type"]) == ("SURVIVES", "nber")
    v1 = rows["10.5555/qme.v1"]
    assert (v1["c_flag"], v1["verdict"]) == ("NEWER-VERSION", "WOUNDED") and "IsObsoletedBy" in v1["notes"]
    assert code == 1


# ----------------------------------------------------------------------------- title search (no identifier)
def test_title_search_grades_entries_without_identifiers(tmp_path, fake):
    search_routes(fake)
    code, out = run_inproc(tmp_path, "--bib", FIX / "search.bib")
    rows = rows_of(out)
    found = rows["found2011"]  # accepted in CrossRef, then graded through the DOI pipeline like any other DOI
    assert (found["r_grade"], found["verdict"], found["doi"]) == ("R-VERIFIED", "SURVIVES", "10.5555/qme.found")
    assert "title search (crossref, similarity 1.00) located 10.5555/qme.found" in found["notes"]
    assert not [u for u in fake.searched("openalex") if "moneyed" in urllib.parse.unquote(u).lower()]  # no fallback
    phantom = rows["phantom2024"]  # neither index has a candidate at 0.75: R-NOT-LOCATED, never auto-FABRICATED
    assert (phantom["r_grade"], phantom["verdict"], phantom["needs_second_reader"]) == ("R-NOT-LOCATED", "WOUNDED",
                                                                                        "yes")
    assert "not located in CrossRef or OpenAlex; needs second reader" in phantom["notes"]
    assert "fabricat" not in phantom["notes"] and "openalex.search:200" in phantom["endpoints"]
    detail = next(c["detail"] for c in latest_report(out)["checks"] if c["title"].startswith("phantom2024"))
    assert detail.startswith("needs second reader")
    near = rows["nearmiss2016"]  # same title, different first author: not accepted, not "not located" either
    assert near["verdict"] == "UNVERIFIED-HERE" and "closest candidate 10.5555/qme.near" in near["notes"]
    assert "first author Adeyemi" in near["notes"]
    web = rows["webpage2025"]
    assert web["verdict"] == "UNVERIFIED-HERE" and "entry type 'misc' is not indexed" in web["notes"]
    assert code == 1


def test_search_429_is_unverified_and_the_index_is_left_alone(tmp_path, fake):
    bib = tmp_path / "two.bib"
    bib.write_text("@article{a1, author = {Quill, Imogen}, title = {Lobbying returns across credit unions},\n"
                   "  year = {2024}}\n@article{a2, author = {Stone, Eli}, title = {Committee attention and campaign "
                   "money}, year = {2019}}\n", encoding="utf-8")
    fake.search("crossref", "", (429, {}, {"retry-after": "1"}))
    fake.search("openalex", "", (429, {}, {"retry-after": "1"}))
    code, out = run_inproc(tmp_path, "--bib", bib)
    rows = rows_of(out)
    assert code == 3 and {r["verdict"] for r in rows.values()} == {"UNVERIFIED-HERE"}
    assert "title search incomplete (crossref: HTTP 429; openalex: HTTP 429)" in rows["a1"]["notes"]
    assert "skipped: api.openalex.org answered 429" in rows["a2"]["notes"]  # the throttled index is not asked again
    assert len(fake.searched("crossref")) == len(fake.searched("openalex")) == 4  # a1 only: 1 try + 3 retries
    calls = len(fake.calls)
    code, out = run_inproc(tmp_path, "--bib", bib, "--no-search")
    assert code == 3 and len(fake.calls) == calls and "title search is off" in rows_of(out)["a1"]["notes"]


def test_reference_lines_in_text_are_searched(tmp_path, fake):
    search_routes(fake)
    md = tmp_path / "refs.md"
    md.write_text("- Halloran, R., & Whitby, S. (2011). Moneyed interests and committee attention: A panel of House "
                  "markups. *Legislative Studies Quarterly*, 36(2), 1-20.\n"
                  "Halloran and Whitby (2011) show that money buys committee attention.\n"
                  "- Federal Election Commission (2025). Bulk data downloads. https://www.fec.gov/data/browse-data/\n",
                  encoding="utf-8")
    code, out = run_inproc(tmp_path, "--text", md)
    rows = rows_of(out)
    assert set(rows) == {"line 1: Halloran 2011", "line 3: Commission 2025"}  # the prose citation is not a reference
    apa = rows["line 1: Halloran 2011"]
    assert (apa["r_grade"], apa["verdict"], apa["doi"]) == ("R-VERIFIED", "SURVIVES", "10.5555/qme.found")
    web = rows["line 3: Commission 2025"]
    assert web["verdict"] == "UNVERIFIED-HERE" and "is not indexed" in web["notes"] and code == 3


# ----------------------------------------------------------------------------- transport failures never pass
def test_429_with_retry_after_is_unverified_never_a_pass(tmp_path, fake):
    fake.doi("10.5555/qme.ratelimited", record=(429, {}, {"retry-after": "2"}))
    ids = tmp_path / "ids.txt"
    ids.write_text("10.5555/qme.ratelimited\n", encoding="utf-8")
    code, out = run_inproc(tmp_path, "--dois", ids)
    row = rows_of(out)["10.5555/qme.ratelimited"]
    assert (row["r_grade"], row["verdict"], code) == ("R-UNVERIFIED-HERE", "UNVERIFIED-HERE", 3)
    assert fake.sleeps.count(2.0) == 3 and "HTTP 429" in row["notes"]  # --retries 3 by default


def test_retry_recovers_and_long_retry_after_stops(tmp_path, fake):
    fake.doi("10.5555/qme.flaky", openalex=oa("10.5555/qme.flaky"),
             record=[(503, {}), (200, cr("10.5555/qme.flaky", "Flaky servers", ["Ito"], 2020))])
    fake.doi("10.5555/qme.throttled", record=(429, {}, {"retry-after": "3600"}))
    ids = tmp_path / "ids.txt"
    ids.write_text("10.5555/qme.flaky\n10.5555/qme.throttled\n", encoding="utf-8")
    code, out = run_inproc(tmp_path, "--dois", ids)
    rows = rows_of(out)
    assert rows["10.5555/qme.flaky"]["r_grade"] == "R-VERIFIED"
    assert "crossref.work:200x2" in rows["10.5555/qme.flaky"]["endpoints"] and 1.0 in fake.sleeps  # --backoff 1.0
    throttled = rows["10.5555/qme.throttled"]
    assert throttled["verdict"] == "UNVERIFIED-HERE" and "exceeds --max-backoff" in throttled["notes"]
    assert "crossref.work:429" in throttled["endpoints"] and 3600.0 not in fake.sleeps and code == 3


def test_retry_flags_and_http_date_retry_after(tmp_path, fake):
    soon, later = formatdate(time.time() + 30, usegmt=True), formatdate(time.time() + 3600, usegmt=True)
    fake.doi("10.5555/qme.twice", openalex=oa("10.5555/qme.twice"),
             record=[(503, {}), (503, {}), (200, cr("10.5555/qme.twice", "Twice failing servers", ["Ito"], 2020))])
    fake.doi("10.5555/qme.dated", openalex=oa("10.5555/qme.dated"),
             record=[(503, {}, {"retry-after": soon}), (200, cr("10.5555/qme.dated", "Dated headers", ["Ito"], 2020))])
    fake.doi("10.5555/qme.later", record=(429, {}, {"retry-after": later}))
    ids = tmp_path / "ids.txt"
    ids.write_text("10.5555/qme.twice\n10.5555/qme.dated\n10.5555/qme.later\n", encoding="utf-8")
    code, out = run_inproc(tmp_path, "--dois", ids, "--retries", "1", "--backoff", "0.5", "--max-backoff", "45")
    rows = rows_of(out)
    twice = rows["10.5555/qme.twice"]  # --retries 1: one retry after a 0.5 s back-off, then give up
    assert twice["verdict"] == "UNVERIFIED-HERE" and "crossref.work:503x2" in twice["endpoints"] and 0.5 in fake.sleeps
    assert rows["10.5555/qme.dated"]["r_grade"] == "R-VERIFIED"
    assert any(25 <= s <= 31 for s in fake.sleeps)  # the HTTP-date Retry-After (30 s ahead) was honoured
    later_row = rows["10.5555/qme.later"]  # an HTTP-date an hour ahead is beyond --max-backoff: not retried
    assert "exceeds --max-backoff" in later_row["notes"] and "crossref.work:429" in later_row["endpoints"]
    assert all(s <= 45 for s in fake.sleeps) and code == 3


def test_retry_after_forms():
    now = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    assert cc.retry_after("120") == 120.0 and cc.retry_after("-3") == 0.0
    assert cc.retry_after("Wed, 30 Sep 2026 12:00:30 GMT", now=now) == 30.0
    assert cc.retry_after("Wed, 30 Sep 2026 11:00:00 GMT", now=now) == 0.0  # a date already past: no wait
    assert cc.retry_after(None) is None and cc.retry_after("soon") is None


def test_offline_and_transport_errors_never_pass(tmp_path, fake):
    for fixture in ("known.bib", "search.bib", "malformed.bib"):
        code, out = run_inproc(tmp_path, "--bib", FIX / fixture, "--offline")
        assert code == 3 and not fake.calls
        assert {r["r_grade"] for r in rows_of(out).values()} == {"R-UNVERIFIED-HERE"}
    fake.add("https://doi.org/api/handles/10.5555/qme.verified", (None, urllib.error.URLError("no route to host")))
    fake.doi("10.5555/qme.html", record=(200, b"<html>captive portal</html>"))
    fake.doi("10.5555/qme.oadown", record=cr("10.5555/qme.oadown", "Open indexes go down", ["Ito"], 2020))
    fake.add("https://api.openalex.org/works/doi:10.5555/qme.oadown", (503, {}))
    ids = tmp_path / "ids.txt"
    ids.write_text("10.5555/qme.verified\n10.5555/qme.html\n10.5555/qme.oadown\n", encoding="utf-8")
    code, out = run_inproc(tmp_path, "--dois", ids)
    rows = rows_of(out)
    assert code == 3 and [r["verdict"] for r in rows.values()] == ["UNVERIFIED-HERE", "UNVERIFIED-HERE", "SURVIVES"]
    assert "no route to host" in rows["10.5555/qme.verified"]["notes"]  # the registry itself failed: never a pass
    assert "unreadable body" in rows["10.5555/qme.html"]["notes"]
    down = rows["10.5555/qme.oadown"]  # OpenAlex is supplementary: its failure is noted, the CrossRef record decides
    assert down["r_grade"] == "R-VERIFIED" and NONE_FOUND.match(down["c_flag"])
    assert "OpenAlex not read (HTTP 503): is_retracted not cross-checked" in down["notes"]
    assert "openalex.work:503x4" in down["endpoints"]


def test_openalex_is_supplementary_and_can_be_skipped(tmp_path, fake):
    for doi in ("10.5555/qme.oa1", "10.5555/qme.oa2"):
        fake.doi(doi, record=cr(doi, f"Registry records and index outages {doi[-1]}", ["Ito"], 2020))
    fake.add("https://api.openalex.org/works/doi:10.5555/qme.oa1", (429, {}, {"retry-after": "63059"}))
    ids = tmp_path / "ids.txt"
    ids.write_text("10.5555/qme.oa1\n10.5555/qme.oa2\n", encoding="utf-8")
    code, out = run_inproc(tmp_path, "--dois", ids)  # the dry run's case: OpenAlex out of budget for 17 hours
    rows = rows_of(out)
    assert code == 0 and all(r["verdict"] == "SURVIVES" and NONE_FOUND.match(r["c_flag"]) for r in rows.values())
    assert "OpenAlex not read (HTTP 429; Retry-After 63059s exceeds --max-backoff)" in rows["10.5555/qme.oa1"]["notes"]
    assert "skipped: api.openalex.org answered 429" in rows["10.5555/qme.oa2"]["notes"]  # not asked again this run
    assert len([u for u, _ in fake.calls if u.startswith("https://api.openalex.org")]) == 1
    fake.calls.clear()
    code, out = run_inproc(tmp_path, "--dois", ids, "--no-openalex")
    assert code == 0 and not [u for u, _ in fake.calls if "openalex" in u]
    assert "OpenAlex skipped (--no-openalex)" in rows_of(out)["10.5555/qme.oa1"]["notes"]
    search_routes(fake)
    code, out = run_inproc(tmp_path, "--bib", FIX / "search.bib", "--no-openalex")
    rows = rows_of(out)
    assert rows["found2011"]["verdict"] == "SURVIVES"  # CrossRef alone can finish a title search
    phantom = rows["phantom2024"]  # but one index cannot establish R-NOT-LOCATED
    assert phantom["verdict"] == "UNVERIFIED-HERE" and "openalex: skipped (--no-openalex)" in phantom["notes"]
    assert code == 3 and not [u for u, _ in fake.calls if "openalex" in u]


def test_malformed_bibtex_entry_is_reported_not_merged(tmp_path, fake):
    titles = {1: "campaign money", 3: "lobbying ties", 4: "credit unions", 5: "bank capital"}
    for i, family in ((1, "Ames"), (3, "Cole"), (4, "Diaz"), (5, "Evans")):
        fake.doi(f"10.5555/qme.{i}", openalex=oa(f"10.5555/qme.{i}"),
                 record=cr(f"10.5555/qme.{i}", f"Title number {i} about {titles[i]}", [family], 2010 + i))
    code, out = run_inproc(tmp_path, "--bib", FIX / "malformed.bib")
    rows = rows_of(out)
    assert list(rows) == ["k1", "k2", "k3", "k4", "k5"]  # nothing skipped, nothing merged
    k2 = rows["k2"]  # the unclosed entry: reported, never looked up, and it borrows no later entry's fields
    assert (k2["r_grade"], k2["verdict"], k2["doi"], k2["supplied_title"]) == ("R-UNVERIFIED-HERE", "UNVERIFIED-HERE",
                                                                              "", "")
    assert "malformed BibTeX entry" in k2["notes"] and not [u for u, _ in fake.calls if "qme.2" in u]
    assert [rows[k]["verdict"] for k in ("k1", "k3", "k4", "k5")] == ["SURVIVES"] * 4
    assert [rows[k]["doi"] for k in ("k3", "k4", "k5")] == ["10.5555/qme.3", "10.5555/qme.4", "10.5555/qme.5"]
    assert code == 3


# ----------------------------------------------------------------------------- cache, privacy, allowlist
def test_cache_is_reused_logged_and_never_overwritten(tmp_path, fake):
    known_routes(fake)
    ids, cache = tmp_path / "ids.txt", tmp_path / "cache"
    ids.write_text("10.5555/qme.verified\n", encoding="utf-8")
    code, out = run_inproc(tmp_path, "--dois", ids, "--cache", cache)
    first = {p.name: p.stat().st_mtime_ns for p in cache.iterdir()}
    calls = len(fake.calls)
    assert code == 0 and len(first) == 4 == calls
    written = latest_report(out)["data"]["requests"]  # every answer written is logged with its file and sha256
    assert all(not e["cached"] and e["cache_sha256"] == sha256(cache / e["cache_file"]) for e in written)
    code, out = run_inproc(tmp_path, "--dois", ids, "--cache", cache)
    row = rows_of(out)["10.5555/qme.verified"]
    assert code == 0 and len(fake.calls) == calls and row["r_grade"] == "R-VERIFIED" and "(cache)" in row["endpoints"]
    read = latest_report(out)["data"]["requests"]  # a cached answer is a copy: which file, and its sha256 (CR-28)
    assert len(read) == 4 and all(e["cached"] and e["cache_sha256"] == sha256(cache / e["cache_file"]) for e in read)
    assert {p.name: p.stat().st_mtime_ns for p in cache.iterdir()} == first
    code, out = run_inproc(tmp_path, "--dois", ids, "--cache", cache, "--no-cache-read")  # fresh answers, cache grows
    assert code == 0 and len(fake.calls) == 2 * calls
    assert "(cache)" not in rows_of(out)["10.5555/qme.verified"]["endpoints"] and len(list(cache.iterdir())) == 8
    code, _ = run_inproc(tmp_path, "--dois", ids, "--cache", cache, "--cache-max-age", "0")  # stale: fetch again
    now = {p.name: p.stat().st_mtime_ns for p in cache.iterdir()}
    assert len(fake.calls) == 3 * calls and len(now) == 12 and all(now[k] == v for k, v in first.items())


def test_mailto_goes_only_to_crossref_and_datacite_and_is_redacted(tmp_path, fake):
    known_routes(fake)
    ids = tmp_path / "ids.txt"
    ids.write_text("10.5555/qme.verified\narXiv:2106.07039\n", encoding="utf-8")
    code, out = run_inproc(tmp_path, "--dois", ids)
    assert code == 0 and all(h["User-Agent"] == cc.UA_BASE for _, h in fake.calls)  # nothing identifies the user
    fake.calls.clear()
    code, out = run_inproc(tmp_path, "--dois", ids, "--mailto", "qme-test@example.org")
    assert code == 0 and fake.calls
    for url, headers in fake.calls:
        host = urllib.parse.urlsplit(url).hostname
        want = f"{cc.UA_BASE} mailto:qme-test@example.org" if host in cc.MAILTO_HOSTS else cc.UA_BASE
        assert headers["User-Agent"] == want, url
    run = latest_run_dir(out)
    for name in ("report.json", "report.md", "references.csv"):
        assert "qme-test@example.org" not in (run / name).read_text(encoding="utf-8")


def test_only_allowlisted_https_hosts():
    for bad in ("http://api.crossref.org/works/10.1/x", "https://example.org/x", "https://api.crossref.org.evil.test/",
                "ftp://doi.org/x"):
        with pytest.raises(cc.HostNotAllowed):
            cc.check_url(bad)
    assert cc.check_url("https://api.openalex.org/works/doi:10.1/x") == "api.openalex.org"
    handler = cc._AllowlistRedirect()
    req = urllib.request.Request("https://api.crossref.org/works/10.1/x",
                                 headers={"User-Agent": f"{cc.UA_BASE} mailto:someone@example.org"})
    with pytest.raises(cc.HostNotAllowed):
        handler.redirect_request(req, None, 302, "Found", {}, "https://tracker.example.com/x")
    moved = handler.redirect_request(req, None, 302, "Found", {}, "https://api.openalex.org/works/x")
    assert moved.get_header("User-agent") == cc.UA_BASE  # the contact address does not follow the redirect


# ----------------------------------------------------------------------------- parsers and matching
def test_parse_bib():
    refs = {r.rid: r for r in cc.parse_bib((FIX / "known.bib").read_text(encoding="utf-8"))}
    assert list(refs) == ["verified2020", "yeardrift2020", "hijack2021", "retracted2019", "corrected2018",
                          "ratelimited2022", "unregistered2023", "chen2021arxiv", "nodoi2019"]  # @comment skipped
    v = refs["verified2020"]
    assert (v.kind, v.doi, v.year, v.venue) == ("doi", "10.5555/qme.verified", 2020, "Journal of Financial Economics")
    assert v.title == "Campaign Contributions and Roll-Call Votes: A Panel Study" and v.authors == ["Muller", "Smith"]
    assert (refs["chen2021arxiv"].kind, refs["chen2021arxiv"].doi) == ("arxiv", "10.48550/arxiv.2106.07039")
    assert refs["chen2021arxiv"].authors == ["Chen"] and refs["corrected2018"].title == "Regulatory Shocks and Fintech Entry"
    nodoi = refs["nodoi2019"]  # a non-DOI url is not an identifier
    assert (nodoi.kind, nodoi.authors, nodoi.year, nodoi.etype) == ("none", ["World Bank"], 2019, "misc")
    paren = cc.parse_bib('@article(p1, title = "A {Nested} Title", author = "{Barnes and Noble} and Ito, K.", '
                         'doi = "10.5555/qme.paren")')
    assert (paren[0].rid, paren[0].title, paren[0].authors, paren[0].doi) == (
        "p1", "A Nested Title", ["Barnes and Noble", "Ito"], "10.5555/qme.paren")
    odd = cc.parse_bib("@article{a1, title = {First}, doi = {10.5555/qme.a}, doi = {10.5555/qme.b}}\n"
                       "@article{a2, title = {Closed too early}}, doi = {10.5555/qme.c}}\n"
                       "@article{a3, title = {Fine}, doi = {10.5555/qme.d}}\n")
    assert [(r.rid, r.kind, r.doi) for r in odd] == [("a1", "doi", "10.5555/qme.a"), ("a2", "malformed", None),
                                                    ("a3", "doi", "10.5555/qme.d")]
    assert "repeated field(s) doi: the first value was used" in odd[0].notes  # first value wins, and it is said
    assert "text follows its closing brace" in odd[1].notes[0]


def test_parse_text():
    refs = cc.parse_text((FIX / "refs.md").read_text(encoding="utf-8"))
    assert [r.doi for r in refs] == ["10.5555/qme.verified", "10.5555/qme.hijack", "10.48550/arxiv.2106.07039",
                                     "10.5555/qme.corrected", "10.5555/qme(x).enc", "10.48550/arxiv.hep-th/9901001"]
    assert "also at line 5" in refs[0].notes and "arXiv v2 cited" in refs[2].notes
    assert "Muller and Smith" in refs[0].context and "doi.org" not in refs[0].context


def test_parse_text_reference_lines():
    refs = cc.parse_text(
        "- Halloran, R., & Whitby, S. (2011). Moneyed interests and committee attention: A panel. *LSQ*, 36(2).\n"
        'Halloran, Ruth, and Sam Whitby. 2011. "Moneyed Interests and Committee Attention." LSQ 36 (2): 1-20.\n'
        "[4] Chen et al. (2021). Scalable influence maximization under uncertainty. Proceedings of UAI.\n"
        "Halloran and Whitby (2011) show that money buys committee attention.\n"
        "As shown by Halloran (2011). Money buys attention in committees.\n"
        "## 2020. The year in review of campaign finance\n"
        "- Federal Election Commission (2025). Bulk data downloads. https://www.fec.gov/data/browse-data/\n"
        "SSRN https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1234567 and https://www.nber.org/papers/w31161\n")
    lines = {r.source: r for r in refs}
    assert set(lines) == {"line 1", "line 2", "line 3", "line 7", "line 8"}  # prose, lead-ins and headings skipped
    assert (lines["line 1"].authors, lines["line 1"].year, lines["line 1"].kind) == (["Halloran"], 2011, "none")
    assert lines["line 1"].title == "Moneyed interests and committee attention: A panel"
    assert lines["line 2"].title.startswith("Moneyed Interests and Committee Attention")  # Chicago, quoted title
    assert lines["line 3"].authors == ["Chen"] and lines["line 7"].etype == "online"  # a web page is not searched
    assert [r.doi for r in refs if r.source == "line 8"] == ["10.2139/ssrn.1234567", "10.3386/w31161"]


def test_parse_dois():
    refs = cc.parse_dois((FIX / "ids.txt").read_text(encoding="utf-8"))
    assert [(r.kind, r.doi) for r in refs] == [("doi", "10.5555/qme.verified"), ("doi", "10.5555/qme.yeardrift"),
                                               ("arxiv", "10.48550/arxiv.2106.07039"), ("doi-invalid", None),
                                               ("unrecognized", None)]
    assert refs[0].context.startswith("Muller Smith 2020") and "also at line 3" in refs[0].notes
    assert cc.classify("ssrn:1234567")[:2] == ("ssrn", "10.2139/ssrn.1234567")
    assert cc.classify("nber:w31161")[:2] == ("nber", "10.3386/w31161")


def test_parse_csl():
    refs = {r.rid: r for r in cc.parse_csl((FIX / "clean.json").read_text(encoding="utf-8"))}
    s, v = refs["sorensen2021"], refs["vilhuber2022"]
    assert (s.doi, s.year, s.venue, s.authors) == ("10.5555/qme.clean1", 2021, "J. Bank. Financ.", ["Sørensen"])
    assert (v.doi, v.year, v.etype) == ("10.5555/qme.dataset", 2022, "dataset")  # DOI taken from the URL field


def test_matching_helpers():
    full, _ = cc.title_sims("Modelling the behaviour of credit unions", ["Modeling the Behavior of Credit Unions"])
    assert full >= 0.9  # spelling variants
    full, main = cc.title_sims("Making sense of sensitivity", ["Making sense of sensitivity: extending omitted variable bias"])
    assert full < 0.9 <= main  # subtitle drift is detected as such
    assert max(cc.title_sims("Deposit insurance and credit union lending", ["Weather forecasting with neural nets"])) < 0.8
    assert cc.clean_title("Replication data for: Voting") == cc.clean_title("Data and Code for: Voting") == "Voting"
    assert cc.clean_title("RETRACTED: Voting") == "Voting"
    assert cc.fam_match("van Beethoven", "Beethoven") and cc.fam_match("Müller", "Muller")
    assert not cc.fam_match("Smith", "Smithers")
    assert cc.venue_sim("J. Bank. Financ.", "Journal of Banking & Finance") == 1.0
    assert cc.venue_sim("JFE", "Journal of Financial Economics") == 1.0
    assert cc.venue_sim("Journal of Finance", "Atmospheric Research") < 0.6
    assert cc.trim_id("10.1/x).") == "10.1/x" and cc.trim_id("10.1016/S0140-6736(20)31180-6") == "10.1016/S0140-6736(20)31180-6"
    assert [cc.text_family(b) for b in ("Hall, R. L., & Wayman, F. W.", "Richard L. Hall and Frank W. Wayman",
                                        "Hall RL, Wayman FW", "Chen et al.")] == ["Hall", "Hall", "Hall", "Chen"]


# ----------------------------------------------------------------------------- CLI contract (subprocess)
def test_help_lists_every_flag_and_token():
    text = cc.build_parser().format_help()
    flags = ("--dois --bib --csl --text --mailto --offline --no-search --no-context --no-openalex --cache "
             "--no-cache-read --cache-max-age --timeout --max-rps --retries --backoff --max-backoff --min-title-sim "
             "--conflict-title-sim --candidate-title-sim --year-tolerance --min-venue-sim").split()
    tokens = ("R-VERIFIED R-MISMATCH-MINOR R-IDENTIFIER-CONFLICT R-NOT-LOCATED R-UNVERIFIED-HERE RETRACTED WITHDRAWN "
              "EOC CORRECTED UPDATED NEWER-VERSION ADDENDUM NONE-FOUND@ NOT-CHECKED").split()
    phrases = ("title search", "same line", "not re-verified", "sha256", "malformed bibtex", "second reader",
               "no domain index", "supplementary")
    assert [t for t in flags + tokens if t not in text] == []
    assert [p for p in phrases if p not in " ".join(text.split()).lower()] == []
    assert "fabricated" not in text.replace("R-FABRICATED", "")  # the script never labels a reference fabricated


def test_usage_errors_exit_2(run_script, tmp_path):
    assert run_script("cite_check.py", "--offline").returncode == 2  # no input given
    missing = run_script("cite_check.py", "--bib", tmp_path / "nope.bib", "--offline")
    assert missing.returncode == 2 and "usage error" in missing.stderr
    empty = run_script("cite_check.py", "--text", FIX / "no_ids.md", "--offline")
    assert empty.returncode == 2 and "no references found" in empty.stderr
    bad_mail = run_script("cite_check.py", "--dois", FIX / "ids.txt", "--offline", "--mailto", "not-an-address")
    assert bad_mail.returncode == 2
    assert run_script("cite_check.py", "--dois", FIX / "ids.txt", "--offline", "--max-rps", "50").returncode == 2


def test_usage_errors_in_process(tmp_path):
    with pytest.raises(SystemExit) as two_inputs:
        cc.build_parser().parse_args(["--bib", "a.bib", "--text", "b.md"])
    assert two_inputs.value.code == 2
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert run_inproc(tmp_path, "--csl", bad, "--offline")[0] == 2
    for flags in (("--candidate-title-sim", "0.95"), ("--retries", "11"), ("--max-backoff", "-1")):
        assert run_inproc(tmp_path, "--dois", FIX / "ids.txt", "--offline", *flags)[0] == 2, flags


def test_run_dir_only_and_inputs_unchanged(run_script, tmp_path):
    src = tmp_path / "input" / "known.bib"
    src.parent.mkdir()
    shutil.copyfile(FIX / "known.bib", src)
    before, fixture_before = sha256(src), sha256(FIX / "known.bib")
    res = run_script("cite_check.py", "--bib", src, "--offline")
    assert res.returncode == 3, res.stderr
    run = latest_run_dir(tmp_path)
    assert {p.name for p in tmp_path.iterdir()} == {"input", run.name}  # nothing written outside the run folder
    assert {p.name for p in run.iterdir()} == {"report.json", "report.md", "references.csv"}
    assert sha256(src) == before and sha256(FIX / "known.bib") == fixture_before
    rep = latest_report(tmp_path)
    assert rep["counts"]["UNVERIFIED-HERE"] == 9 and rep["provenance"]["inputs"][0]["sha256"] == before


# ----------------------------------------------------------------------------- live (opt-in: QME_LIVE=1)
@pytest.mark.live
def test_live_registries(tmp_path):
    ids = tmp_path / "live.txt"
    ids.write_text("10.1038/s41598-023-41032-5 Walters Wilder fabrication errors bibliographic citations ChatGPT\n"
                   "10.1016/S0140-6736(20)31180-6\narXiv:2106.07039\n", encoding="utf-8")
    code, out = run_inproc(tmp_path, "--dois", ids)
    rows = {r["doi"]: r for r in rows_of(out).values()}
    walters = rows["10.1038/s41598-023-41032-5"]
    assert walters["r_grade"] == "R-VERIFIED" and "names the record's author" in walters["notes"]
    mehra = rows["10.1016/s0140-6736(20)31180-6"]
    assert mehra["verdict"] == "KILLED" and "RETRACTED" in mehra["c_flag"]
    chen = rows["10.48550/arxiv.2106.07039"]
    assert chen["r_grade"] == "R-VERIFIED" and chen["registration_agency"] == "DataCite"
    bib = tmp_path / "nodoi.bib"  # the same Walters & Wilder paper cited without its DOI: found by title search
    bib.write_text("@article{walters2023, author = {Walters, William H. and Wilder, Esther Isabelle}, title = "
                   "{Fabrication and errors in the bibliographic citations generated by ChatGPT}, journal = "
                   "{Scientific Reports}, year = {2023}}\n", encoding="utf-8")
    code, out = run_inproc(tmp_path, "--bib", bib)
    found = rows_of(out)["walters2023"]
    assert (found["r_grade"], found["doi"]) == ("R-VERIFIED", "10.1038/s41598-023-41032-5"), found["notes"]
    assert "title search (crossref" in found["notes"]
