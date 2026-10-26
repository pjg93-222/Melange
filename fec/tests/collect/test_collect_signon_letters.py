"""Sign-on letter collector (D-263, lane L): extraction, Gate E, de-duplication, staging.

Every case runs on recorded public .gov documents (fixtures/letters/MANIFEST.txt) and a fake fetcher:
nothing here touches the network.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import sys
from pathlib import Path

import pytest

FEC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FEC))
from collect import collect_signon_letters as C          # noqa: E402
from members.member_identity import Resolver              # noqa: E402

FX = Path(__file__).resolve().parent / "fixtures" / "letters"
DINGELL_URL = "https://debbiedingell.house.gov/UploadedFiles/8.31.26_US_Canada_Trump_Letter.pdf"
KAPTUR_URL = "https://kaptur.house.gov/media-center/press-releases/kaptur-dingell-lead-colleagues-letter-urging-president-recognize"
CDFI_URL = "https://democrats-financialservices.house.gov/UploadedFiles/04.21.2025_Ltr.SecCDFI_EO.pdf"
MURRAY_URL = "https://www.murray.senate.gov/wp-content/uploads/2026/08/Pediatric-Trials-Network-POPS-Cancellation-Letter-Signed.pdf"
NOW = dt.datetime(2026, 10, 20, 19, 0, 0, tzinfo=dt.timezone.utc)


def fx(name):
    return (FX / name).read_bytes()


@pytest.fixture(scope="module")
def roster():
    rows = json.loads(fx("roster_slice.json"))
    bio = {r["member"]: r["bioguide"] for r in rows}
    return Resolver(list(bio), bio), bio


@pytest.fixture(scope="module")
def dingell(roster):
    return C.analyze_letter(fx("dingell_canada_letter.pdf"), document_url=DINGELL_URL, source_url=KAPTUR_URL,
                            source_kind="member_press", release=C.parse_release(fx("kaptur_release.html"), KAPTUR_URL),
                            resolver=roster[0], bio=roster[1], now=NOW)


@pytest.fixture(scope="module")
def cdfi(roster):
    return C.analyze_letter(fx("fs_dems_cdfi_letter.pdf"), document_url=CDFI_URL, source_url="https://democrats-financialservices.house.gov/news/documentsingle.aspx?DocumentID=1",
                            source_kind="committee_site", release=None, resolver=roster[0], bio=roster[1], now=NOW)


# ---- Gate E on the three recorded PDFs ------------------------------------------------------------

def test_dingell_pdf_88_signers_reconcile_with_the_release_count(dingell):
    assert dingell["status"] == "EXACT"
    assert len(dingell["signatories"]) == 88 and dingell["unaccounted_lines"] == []
    assert all(s["status"] == "roster" and s["bioguide"] for s in dingell["signatories"])
    assert dingell["stated_count"] == {"n": 86, "min": False}      # "led 86 of their House colleagues" + 2 leads = 88
    assert sorted(dingell["leads"]) == sorted(s["bioguide"] for s in dingell["signatories"]
                                              if s["member"] in ("Marcy Kaptur", "Debbie Dingell"))
    assert dingell["letter_date"] == "2026-08-31" and dingell["congress"] == 119
    assert dingell["sha256"] == hashlib.sha256(fx("dingell_canada_letter.pdf")).hexdigest()


def test_murray_pdf_five_of_five_and_page_lines_are_not_names(roster):
    rec = C.analyze_letter(fx("murray_pediatric_letter.pdf"), document_url=MURRAY_URL, source_url="https://www.murray.senate.gov/x/",
                           source_kind="member_press", release=C.parse_release(fx("murray_release.html"), "https://www.murray.senate.gov/x/"),
                           resolver=roster[0], bio=roster[1], now=NOW)
    assert rec["status"] == "EXACT"
    assert [s["member"] for s in rec["signatories"]] == ["Patty Murray", "Jack Reed", "Chris Van Hollen", "Cory Booker", "Adam Schiff"]
    assert rec["leads"] == [rec["signatories"][0]["bioguide"]]          # "Murray ... led her colleagues"
    assert rec["unaccounted_lines"] == [] and rec["recipients"][0].startswith("The Honorable Dr. Jay Bhattacharya")


def test_cdfi_pdf_89_roster_plus_one_attested_off_roster_member(cdfi):
    assert cdfi["status"] == "EXACT"
    assert len(cdfi["signatories"]) == 90
    off = [s for s in cdfi["signatories"] if s["status"] == "off_roster"]
    assert [s["line"] for s in off] == ["Sheila Cherfilus-McCormick"] and off[0]["bioguide"] is None
    assert cdfi["unaccounted_lines"] == []                              # "Ranking Member, Committee / on Financial Services" are titles
    assert cdfi["letter_date"] == "2025-04-21" and cdfi["congress"] == 119
    assert cdfi["subject_categories"] == ["CDFI Fund"]
    assert cdfi["leads"] and cdfi["signatories"][0]["member"] == "Maxine Waters"   # Ranking Member office line
    assert cdfi["letter_id"] == "LTR-119-CDFI-WATERS"


# ---- Gate E refusals --------------------------------------------------------------------------------

BLOCK = "Dear Sir:\nWe write about credit unions.\nSincerely,\n%s"


def sig(roster, tail, **kw):
    return C.parse_signature_block(BLOCK % tail, roster[0], roster[1], **kw)


def test_a_name_with_no_office_line_and_no_roster_match_is_unaccounted(roster):
    out = sig(roster, "Patty Murray\nUnited States Senator\nJane Q Public\nPage 2\n")
    assert [s["member"] for s in out["signatories"]] == ["Patty Murray"]
    assert out["unaccounted_lines"] == ["Jane Q Public"]


def test_a_kerning_split_capital_is_rejoined_but_a_middle_initial_is_not(roster):
    # pypdf >= 6.21 emits "V argas" for a kerned capital V; "Jane Q Public" keeps its initial (capital follows)
    out = sig(roster, "Juan V argas\nMember of Congress\nJane Q Public\n")
    assert [s["member"] for s in out["signatories"]] == ["Juan Vargas"]
    assert out["unaccounted_lines"] == ["Jane Q Public"]
    # a period-less initial before a lowercase name particle is kept apart, while "V argas" still rejoins
    out = sig(roster, "Juan A de la Cruz\nMember of Congress\nJuan V argas\nMember of Congress\n")
    assert [s["line"] for s in out["signatories"] if s["status"] != "roster"] + out["unaccounted_lines"] == ["Juan A de la Cruz"]
    assert [s["member"] for s in out["signatories"] if s["status"] == "roster"] == ["Juan Vargas"]


def test_a_non_roster_name_is_off_roster_only_when_its_own_office_line_attests_it(roster):
    out = sig(roster, "Michael Barr\nMember of Congress\nPatty Murray\nUnited States Senator\n")
    barr = out["signatories"][0]
    assert barr["status"] == "off_roster" and barr["member"] is None        # never Andy Barr
    assert out["unaccounted_lines"] == []
    assert sig(roster, "Michael Barr\nPatty Murray\nUnited States Senator\n")["unaccounted_lines"] == ["Michael Barr"]


def test_no_closing_phrase_means_no_signature_block(roster):
    assert C.parse_signature_block("Dear Sir:\nPatty Murray\nUnited States Senator\n", roster[0], roster[1])["closing_found"] is False


def test_stated_count_mismatch_is_not_exact(roster, dingell):
    rec = dict(dingell, stated_count={"n": 50, "min": False})
    assert C.gate_e(rec) == "NOT_EXACT:stated_count_mismatch"
    assert C.gate_e(dict(dingell, stated_count={"n": 88, "min": False})) == "EXACT"      # reading: n is the total
    assert C.gate_e(dict(dingell, stated_count={"n": 90, "min": True})) == "NOT_EXACT:stated_count_mismatch"
    assert C.gate_e(dict(dingell, stated_count={"n": 80, "min": True})) == "EXACT"


@pytest.mark.parametrize("change, reason", [
    ({"unaccounted_lines": ["X Y"]}, "NOT_EXACT:unaccounted"),
    ({"signatories": []}, "NOT_EXACT:no_signatories"),
    ({"closing_found": False}, "NOT_EXACT:no_signature_block"),
    ({"letter_date": None}, "NOT_EXACT:no_date"),
    ({"document_url": "https://evil.example.com/a.pdf"}, "NOT_EXACT:host_not_official"),
    ({"source_kind": "trade_press"}, "NOT_EXACT:source_kind"),
])
def test_gate_e_refusals(dingell, change, reason):
    assert C.gate_e(dict(dingell, **change)) == reason


def test_a_pdf_without_a_text_layer_is_not_exact(roster):
    import pypdf
    w = pypdf.PdfWriter()
    w.add_blank_page(612, 792)
    buf = io.BytesIO()
    w.write(buf)
    rec = C.analyze_letter(buf.getvalue(), document_url=DINGELL_URL, source_url=KAPTUR_URL, source_kind="member_press",
                           release=None, resolver=roster[0], bio=roster[1], now=NOW)
    assert rec["status"] == "NOT_EXACT:no_text_layer"


def test_an_unreadable_pdf_is_not_exact(roster):
    rec = C.analyze_letter(b"%PDF-1.4 garbage", document_url=DINGELL_URL, source_url=KAPTUR_URL, source_kind="member_press",
                           release=None, resolver=roster[0], bio=roster[1], now=NOW)
    assert rec["status"] in ("NOT_EXACT:pdf_unreadable", "NOT_EXACT:no_text_layer")


# ---- helpers ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("d, congress", [
    ("2023-01-02", 117), ("2023-01-03", 118), ("2025-01-02", 118), ("2025-01-03", 119), ("2022-09-01", 117), ("2026-10-20", 119),
])
def test_congress_of_follows_the_january_3_boundary(d, congress):
    assert C.congress_of(dt.date.fromisoformat(d)) == congress


@pytest.mark.parametrize("text, want", [
    ("led 86 of their House colleagues in urging", {"n": 86, "min": False}),
    ("a letter signed by over 110 House Democrats", {"n": 110, "min": True}),
    ("joined by 36 colleagues", {"n": 36, "min": False}),
    ("signed by more than 40 members", {"n": 40, "min": True}),
    ("no number here", None),
])
def test_stated_count(text, want):
    assert C.parse_stated_count(text) == want


def test_release_parse_finds_the_letter_pdf_and_date():
    rel = C.parse_release(fx("fs_dems_hud_release.html"), "https://democrats-financialservices.house.gov/news/documentsingle.aspx?DocumentID=415382")
    assert rel["pdf_links"] == ["https://democrats-financialservices.house.gov/UploadedFiles/HUD_Equal_Access_Proposed_Rule.pdf"]
    assert rel["stated_count"] == {"n": 110, "min": True}
    assert "HUD" in rel["title"] or rel["text"]


def test_listing_parse_yields_dated_items_and_the_next_page():
    url = "https://democrats-financialservices.house.gov/news/documentquery.aspx?DocumentTypeID=2636"
    items = C.parse_listing(fx("fs_dems_listing.html"), url)
    assert len(items) >= 20
    hud = [i for i in items if i["url"].endswith("DocumentID=415382")][0]
    assert hud["date"] == "2026-09-" + hud["date"][-2:] or hud["date"].startswith("2026-")
    assert hud["url"].startswith("https://democrats-financialservices.house.gov/news/documentsingle.aspx")
    assert C.LETTER_RE.search(hud["title"] + " " + hud["snippet"])
    floor = [i for i in items if "Floor Statement" in i["title"]][0]
    assert not C.LETTER_RE.search(floor["title"] + " " + floor["snippet"])


def test_official_host_allowlist():
    assert C.official_host("https://democrats-financialservices.house.gov/UploadedFiles/a.pdf")
    assert C.official_host("https://www.murray.senate.gov/wp-content/uploads/a.pdf")
    assert C.official_host("https://downloads.regulations.gov/CFPB-2023-0047-0033/attachment_1.pdf")
    for bad in ("https://house.gov.evil.com/a.pdf", "https://evilhouse.gov/a.pdf", "https://example.com/a.pdf", "ftp://x.house.gov/a.pdf",
                "https://www.house.gov.example/a.pdf"):
        assert not C.official_host(bad), bad


def test_cu_relevance_screen():
    assert C.cu_relevant("a letter urging protection of the CDFI Fund")
    assert C.cu_relevant("preserve the credit union tax exemption")
    assert not C.cu_relevant("Canada is a close friend, neighbor, ally")



# ======================================================================================================
# Part 2: politeness layer, staging, de-duplication, the three legs, receipt
# ======================================================================================================

import csv                                                      # noqa: E402
import socket                                                   # noqa: E402
from urllib.parse import urlparse                               # noqa: E402

LIST_URL = "https://democrats-financialservices.house.gov/news/documentquery.aspx?DocumentTypeID=2636"
REL_URL = "https://democrats-financialservices.house.gov/news/documentsingle.aspx?DocumentID=900001"
CDFI_PDF = "https://democrats-financialservices.house.gov/UploadedFiles/04.21.2025_Ltr.SecCDFI_EO.pdf"


def listing_html(items):
    """items: [(href, title, iso date, snippet)] in the markup of the committee ASPX listing."""
    body = "".join('<article class="newsblocker"><h2 class="newsie-titler"><a href="%s">%s</a></h2>'
                   '<time datetime="%s">x</time><div class="newsbody"><p>%s</p></div></article>' % i for i in items)
    return ("<html><body><div id='newsdoclist'>%s</div></body></html>" % body).encode()


def release_html(pdf=CDFI_PDF, text="Ranking Member Waters and Democrats sent a letter urging Treasury to protect the CDFI Fund.",
                 title="Waters urges Treasury on CDFI Fund"):
    return ('<html><head><title>%s</title></head><body><time datetime="2025-04-21">April 21</time>'
            '<p>%s <a href="%s">letter</a></p></body></html>' % (title, text, pdf)).encode()


class FakeFetcher:
    """Fetcher's contract (get -> bytes; FetchRefused / FetchFailed / CapReached) over a url -> bytes dict."""

    def __init__(self, pages, cap=300, refuse=()):
        self.pages, self.cap, self.refuse, self.requests = dict(pages), cap, set(refuse), []

    def get(self, url, max_bytes=C.HTML_CAP):
        if urlparse(url).hostname in self.refuse:
            raise C.FetchRefused("robots")
        if len(self.requests) >= self.cap:
            raise C.CapReached()
        self.requests.append(url)
        if url not in self.pages:
            raise C.FetchFailed("HTTP 404")
        return self.pages[url]


@pytest.fixture
def root(tmp_path):
    rows = json.loads(fx("roster_slice.json"))
    (tmp_path / "data" / "engine").mkdir(parents=True)
    (tmp_path / "data" / "engine" / "congestion.json").write_text(json.dumps(rows), encoding="utf-8")
    (tmp_path / "manual_bill_evidence.csv").write_bytes((",".join(C.CSV_COLUMNS) + "\r\n").encode())
    return tmp_path


def run(root, fetcher, legs=("committee",), **kw):
    kw.setdefault("listings", (("fs_test", LIST_URL, True),))
    kw.setdefault("pages", 1)
    return C.collect(root=str(root), letters_dir=str(root / "letters"), legs=list(legs), fetcher=fetcher, now=NOW, **kw)


def staged(root):
    path = root / "letters" / "letter_staging.jsonl"
    return {r["letter_id"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines())} if path.exists() else {}


LETTER_ITEM = ("documentsingle.aspx?DocumentID=900001", "Waters Urges Treasury to Protect the CDFI Fund", "2025-04-21", "sent a letter")


def cdfi_pages(**extra):
    pages = {LIST_URL: listing_html([LETTER_ITEM, ("documentsingle.aspx?DocumentID=900002", "Floor Statement on Housing", "2025-04-20", "Today")]),
             REL_URL: release_html(), CDFI_PDF: fx("fs_dems_cdfi_letter.pdf")}
    pages.update(extra)
    return pages


# ---- politeness layer -------------------------------------------------------------------------------

@pytest.fixture
def net(monkeypatch):
    """A Fetcher over a scripted opener with a fake clock: (make, calls, sleeps, served)."""
    monkeypatch.setattr(C.socket, "getaddrinfo", lambda host, port, *a, **k: [(socket.AF_INET, 0, 0, "", ("93.184.216.34", port))])
    calls, sleeps, served, clock = [], [], {}, [1000.0]

    def opener(url, max_bytes):
        calls.append(url)
        return served.get(url, (200, b"x"))

    def sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds

    def make(**kw):
        return C.Fetcher(opener=opener, sleep=sleep, clock=lambda: clock[0], **kw)

    return make, calls, sleeps, served


ROBOTS = "https://democrats-financialservices.house.gov/robots.txt"
DOC = "https://democrats-financialservices.house.gov/UploadedFiles/a.pdf"


def test_robots_disallow_refuses_before_the_document_is_requested(net):
    make, calls, sleeps, served = net
    served[ROBOTS] = (200, b"User-agent: *\nDisallow: /UploadedFiles/\n")
    with pytest.raises(C.FetchRefused):
        make().get(DOC)
    assert calls == [ROBOTS]


@pytest.mark.parametrize("status, allowed", [(404, True), (410, True), (403, False), (401, False)])
def test_robots_status_rules(net, status, allowed):
    make, calls, sleeps, served = net
    served[ROBOTS] = (status, b"")
    served[DOC] = (200, b"%PDF")
    if allowed:
        assert make().get(DOC) == b"%PDF"
    else:
        with pytest.raises(C.FetchRefused):
            make().get(DOC)


def test_robots_is_fetched_once_per_host_and_requests_to_a_host_are_spaced_two_seconds(net):
    make, calls, sleeps, served = net
    served[ROBOTS] = (200, b"User-agent: *\nDisallow: /private/\n")
    f = make()
    f.get(DOC)
    f.get(DOC + "?2")
    assert calls.count(ROBOTS) == 1 and len(calls) == 3
    assert len(sleeps) == 2 and all(abs(s - 2.0) < 1e-6 for s in sleeps)               # robots->doc, doc->doc
    served["https://www.murray.senate.gov/robots.txt"] = (404, b"")
    f.get("https://www.murray.senate.gov/a.pdf")
    assert len(sleeps) == 3                                                             # only the new host's robots->doc gap, never a wait for the old host


def test_request_cap_counts_robots_and_stops_with_cap_reached(net):
    make, calls, sleeps, served = net
    served[ROBOTS] = (404, b"")
    f = make(cap=2)
    f.get(DOC)
    with pytest.raises(C.CapReached):
        f.get(DOC + "?2")
    assert len(calls) == 2


def test_oversize_bodies_and_http_errors_are_failures(net):
    make, calls, sleeps, served = net
    served[ROBOTS] = (404, b"")
    served[DOC] = (200, b"x" * 11)
    with pytest.raises(C.FetchFailed):
        make().get(DOC, max_bytes=10)
    served[DOC] = (500, b"")
    with pytest.raises(C.FetchFailed):
        make().get(DOC)


def test_private_targets_are_refused_before_any_request(net):
    make, calls, sleeps, served = net
    for url in ("http://127.0.0.1/x.pdf", "http://169.254.169.254/latest/", "file:///etc/passwd"):
        with pytest.raises(C.FetchRefused):
            make().get(url)
    assert calls == []


# ---- staging and de-duplication --------------------------------------------------------------------

def hand_csv(root, bill, date, members, congress=119):
    rows = [dict(Member=m, Role="original-cosponsor", Bill=bill, Title="t", Sponsor="x", Congress=str(congress), Category="CDFI Fund",
                 Direction="+1", DecayWeight="1.0", LastAction="Letter sent %s to Treasury" % date, DetailLink="", Summary="s", Note="n")
            for m in members]
    path = root / "manual_bill_evidence.csv"
    with open(path, "w", encoding="utf-8", newline="") as h:
        w = csv.DictWriter(h, fieldnames=C.CSV_COLUMNS, lineterminator="\r\n")
        w.writeheader()
        w.writerows(rows)
    return path


def test_the_same_pdf_from_two_offices_is_one_letter(cdfi):
    staging = {}
    refs = C.load_existing_letters(None, {})
    second = dict(cdfi, source_url="https://other.house.gov/x", source_urls=["https://other.house.gov/x"])
    assert C.stage_record(staging, dict(cdfi), refs) == "new"
    assert C.stage_record(staging, second, refs) == "seen"
    assert len(staging) == 1 and len(next(iter(staging.values()))["source_urls"]) == 2


def test_a_reposted_copy_with_different_bytes_is_caught_by_signer_overlap(cdfi):
    staging = {}
    refs = C.load_existing_letters(None, {})
    C.stage_record(staging, dict(cdfi), refs)
    copy = dict(cdfi, sha256="f" * 64, letter_date="2025-04-22", source_url="https://o.house.gov/y", source_urls=["https://o.house.gov/y"])
    C.stage_record(staging, copy, refs)
    dup = [r for r in staging.values() if r["sha256"] == "f" * 64][0]
    assert dup["status"] == "DUPLICATE_OF:LTR-119-CDFI-WATERS" and dup["dedupe"]["method"] == "signer_overlap"


def test_a_hand_ingested_letter_is_recognised_and_never_rewritten(cdfi, roster, root):
    members = [s["member"] for s in cdfi["signatories"] if s["member"]]
    path = hand_csv(root, "LTR-119-CDFI-HAND", "2025-04-23", members[:-8])        # 81 of 89 members, 2 days off
    before = path.read_bytes()
    refs = C.load_existing_letters(str(path), roster[1])
    staging = {}
    C.stage_record(staging, dict(cdfi), refs)
    rec = staging["LTR-119-CDFI-WATERS"]
    assert rec["status"] == "DUPLICATE_OF:LTR-119-CDFI-HAND" and rec["dedupe"]["matched_existing"] == "LTR-119-CDFI-HAND"
    assert rec["dedupe"]["jaccard"] >= 0.8 and path.read_bytes() == before


def test_partial_overlap_with_a_hand_letter_goes_to_review(cdfi, roster, root):
    members = [s["member"] for s in cdfi["signatories"] if s["member"]]
    refs = C.load_existing_letters(str(hand_csv(root, "LTR-119-CDFI-HAND", "2025-04-21", members[:45])), roster[1])
    staging = {}
    C.stage_record(staging, dict(cdfi), refs)
    assert staging["LTR-119-CDFI-WATERS"]["status"] == "NOT_EXACT:conflicts_existing:LTR-119-CDFI-HAND"


def test_an_id_already_taken_by_another_letter_gets_a_suffix(cdfi, roster, root):
    refs = C.load_existing_letters(str(hand_csv(root, "LTR-119-CDFI-WATERS", "2025-10-27", ["Maxine Waters"])), roster[1])
    staging = {}
    C.stage_record(staging, dict(cdfi), refs)
    assert list(staging) == ["LTR-119-CDFI-WATERS-2"] and staging["LTR-119-CDFI-WATERS-2"]["letter_id"] == "LTR-119-CDFI-WATERS-2"


# ---- legs ---------------------------------------------------------------------------------------------

def test_committee_leg_stages_the_exact_cdfi_letter_and_keeps_the_pdf(root):
    ff = FakeFetcher(cdfi_pages())
    receipt = run(root, ff)
    rec = staged(root)["LTR-119-CDFI-WATERS"]
    assert rec["status"] == "EXACT" and rec["source_kind"] == "committee_site" and rec["source_url"] == REL_URL
    assert rec["document_url"] == CDFI_PDF and len(rec["signatories"]) == 90
    assert (root / "letters" / "pdf" / (rec["sha256"] + ".pdf")).read_bytes() == fx("fs_dems_cdfi_letter.pdf")
    assert ff.requests == [LIST_URL, REL_URL, CDFI_PDF]                      # the floor statement is not a letter: never fetched
    assert receipt["status"] == "PASS" and receipt["staged_new"] == 1 and receipt["by_status"] == {"EXACT": 1}
    assert json.loads((root / "letters" / "collector_receipt.json").read_text(encoding="utf-8"))["staging_sha256"]


def test_a_second_run_changes_nothing_and_refetches_no_staged_release(root):
    run(root, FakeFetcher(cdfi_pages()))
    before = (root / "letters" / "letter_staging.jsonl").read_bytes()
    ff = FakeFetcher(cdfi_pages())
    receipt = run(root, ff)
    assert (root / "letters" / "letter_staging.jsonl").read_bytes() == before
    assert ff.requests == [LIST_URL] and receipt["staged_new"] == 0


def test_a_non_cu_letter_is_kept_only_as_an_off_topic_stub(root):
    pages = cdfi_pages()
    pages[REL_URL] = release_html(pdf=MURRAY_URL, text="Murray led colleagues in a letter urging NIH to restore research.", title="Murray urges NIH")
    pages[MURRAY_URL] = fx("murray_pediatric_letter.pdf")
    receipt = run(root, FakeFetcher(pages))
    (rec,) = staged(root).values()
    assert rec["status"] == "OFF_TOPIC" and rec["signatories"] == [] and rec["sha256"] and rec["source_url"] == REL_URL
    assert receipt["by_status"] == {"OFF_TOPIC": 1}
    again = FakeFetcher(pages)
    run(root, again)
    assert again.requests == [LIST_URL]


def test_from_press_fetches_only_cu_letter_rows_of_the_newest_run(root):
    old = root / "outputs" / "press_refresh_20261001"
    new = root / "outputs" / "press_refresh_20261018"
    for d in (old, new):
        d.mkdir(parents=True)
    cols = ["title", "url", "date_final", "bioguide", "member", "body"]

    def write(path, rows):
        with open(path, "w", encoding="utf-8", newline="") as h:
            w = csv.DictWriter(h, fieldnames=cols)
            w.writeheader()
            w.writerows(rows)

    write(old / "press_delta_fulltext.csv", [dict(title="old", url="https://old.house.gov/a", date_final="2026-10-01", bioguide="W000187",
                                                  member="Maxine Waters", body="a letter about the CDFI Fund")])
    cu = "https://waters.house.gov/media/press-releases/cdfi-letter"
    write(new / "press_delta_fulltext.csv", [
        dict(title="Waters urges Treasury to protect CDFI Fund", url=cu, date_final="2026-10-17", bioguide="W000187", member="Maxine Waters",
             body="Today Waters sent a letter to Treasury about the CDFI Fund."),
        dict(title="Waters celebrates credit unions", url="https://waters.house.gov/b", date_final="2026-10-17", bioguide="W000187",
             member="Maxine Waters", body="credit union week is here"),
        dict(title="Waters urges Canada policy change", url="https://waters.house.gov/c", date_final="2026-10-17", bioguide="W000187",
             member="Maxine Waters", body="a letter to the president on Canada"),
    ])
    ff = FakeFetcher({cu: release_html(), CDFI_PDF: fx("fs_dems_cdfi_letter.pdf")})
    receipt = run(root, ff, legs=("press",))
    assert ff.requests == [cu, CDFI_PDF]
    assert staged(root)["LTR-119-CDFI-WATERS"]["source_kind"] == "member_press" and receipt["status"] == "PASS"


def test_a_refusing_host_makes_the_run_partial_not_fatal(root):
    receipt = run(root, FakeFetcher(cdfi_pages(), refuse={"democrats-financialservices.house.gov"}))
    assert receipt["status"] == "PARTIAL" and "democrats-financialservices.house.gov" in receipt["hosts_refused"]
    assert C.exit_code(receipt) == 0


def test_the_request_cap_is_a_designed_partial_stop(root):
    receipt = run(root, FakeFetcher(cdfi_pages(), cap=2))
    assert receipt["status"] == "PARTIAL" and receipt["cap_hit"] is True and staged(root) == {}


def test_a_failed_pdf_is_an_error_and_is_retried_next_run(root):
    pages = cdfi_pages()
    del pages[CDFI_PDF]
    receipt = run(root, FakeFetcher(pages))
    assert receipt["status"] == "PARTIAL" and receipt["errors"] == 1 and staged(root) == {}
    run(root, FakeFetcher(cdfi_pages()))
    assert staged(root)["LTR-119-CDFI-WATERS"]["status"] == "EXACT"


def test_an_unusable_roster_is_fail(tmp_path):
    receipt = run(tmp_path, FakeFetcher({}))
    assert receipt["status"] == "FAIL" and C.exit_code(receipt) == 1


def test_backfill_walks_back_to_the_117th_congress_and_remembers_where_it_stopped(root):
    p1 = listing_html([("documentsingle.aspx?DocumentID=900001", "Waters Urges Treasury to Protect the CDFI Fund", "2021-02-01", "a letter")])
    p2 = listing_html([("documentsingle.aspx?DocumentID=900009", "Old letter urging action", "2020-12-01", "a letter")])
    pages = {LIST_URL: p1, LIST_URL + "&Page=2": p1, LIST_URL + "&Page=3": p2, REL_URL: release_html(), CDFI_PDF: fx("fs_dems_cdfi_letter.pdf")}
    first = run(root, FakeFetcher(pages, cap=3), legs=("backfill",), pages=10)
    cursor = json.loads((root / "letters" / "backfill_cursor.json").read_text(encoding="utf-8"))
    assert first["status"] == "PARTIAL" and cursor["fs_test"]["done"] is False and cursor["fs_test"]["next_page"] >= 1
    ff = FakeFetcher(pages)
    second = run(root, ff, legs=("backfill",), pages=10)
    cursor = json.loads((root / "letters" / "backfill_cursor.json").read_text(encoding="utf-8"))
    assert cursor["fs_test"]["done"] is True and second["status"] == "PASS"
    assert LIST_URL + "&Page=4" not in ff.requests                       # stopped at the first page older than 2021-01-03
    assert "LTR-119-CDFI-WATERS" in staged(root)


# ---- findings from the first live dry run (2026-10-20): each of these produced a wrong or noisy record before ------------------

def text_pdf(lines, *more_pages):
    """A minimal PDF whose pages' text layers are `lines`, then each of `more_pages` ([] = a page with no text), with a valid xref."""
    pages = [lines, *more_pages]
    objs = {1: "<</Type/Catalog/Pages 2 0 R>>", 3: "<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
            2: "<</Type/Pages/Kids[%s]/Count %d>>" % (" ".join("%d 0 R" % (4 + 2 * i) for i in range(len(pages))), len(pages))}
    for i, page in enumerate(pages):
        ops = "BT /F1 9 Tf 40 760 Td 11 TL " + " ".join("(%s) '" % l.replace("(", "").replace(")", "") for l in page) + " ET"
        objs[4 + 2 * i] = "<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents %d 0 R/Resources<</Font<</F1 3 0 R>>>>>>" % (5 + 2 * i)
        objs[5 + 2 * i] = "<</Length %d>>\nstream\n%s\nendstream" % (len(ops), ops)
    out, offsets = "%PDF-1.4\n", []
    for number in sorted(objs):
        offsets.append(len(out))
        out += "%d 0 obj\n%s\nendobj\n" % (number, objs[number])
    xref = len(out)
    out += "xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + "".join("%010d 00000 n \n" % o for o in offsets)
    return (out + "trailer\n<</Root 1 0 R/Size %d>>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)).encode("latin-1")


def test_a_passing_mention_is_not_a_subject():
    filler = "The agencies proposed changes to the Community Reinvestment Act rules. " * 8
    assert C.subject_categories("", filler + "We recommend you consider comments from CDFIs.") == []
    assert C.subject_categories("", "We urge Treasury to protect the CDFI Fund. " + filler) == ["CDFI Fund"]
    assert C.subject_categories("", filler + "CDFI one. CDFI two. CDFI three.") == ["CDFI Fund"]          # dense recurrence
    assert C.subject_categories("", filler * 40 + "CDFI one. CDFI two. CDFI three.") == []                 # three mentions in a 22k-char CRA-style letter
    assert C.subject_categories("Waters urges Treasury on CDFI Fund", filler) == ["CDFI Fund"]
    assert not C.cu_relevant(filler + "credit union")
    assert C.cu_relevant("Tax-exempt status of donor-advised funds") is False


def test_wrapped_subcommittee_names_are_not_unaccounted_names(roster):
    out = sig(roster, "Maxine Waters\nRanking Member, Committee\non Financial Services\nBrad Sherman\nMember of Congress\n"
                      "Subcommittee on Capital\nMarkets\n")
    assert [s["member"] for s in out["signatories"]] == ["Maxine Waters", "Brad Sherman"] and out["unaccounted_lines"] == []


def test_a_bill_text_linked_from_a_release_is_not_staged_as_a_letter(root):
    bill = text_pdf(["119TH CONGRESS 2D SESSION H. RES. 1234 Providing for consideration of the bill relating to credit unions and the CDFI Fund.",
                     "Resolved, That upon adoption of this resolution the House shall consider the credit union provisions as amended."] * 3)
    pages = cdfi_pages()
    pages[CDFI_PDF] = bill
    run(root, FakeFetcher(pages))
    (rec,) = staged(root).values()
    assert rec["status"] == "OFF_TOPIC" and rec["signatories"] == []


def test_a_text_pdf_round_trips_through_extraction_and_the_gates(roster):
    lines = (["April 21, 2025", "The Honorable Scott Bessent", "Secretary", "1500 Pennsylvania Ave NW", "Dear Secretary Bessent:",
              "We urge you to protect the CDFI Fund and the credit unions it supports. " * 3, "Sincerely,",
              "Maxine Waters", "Ranking Member, Committee", "on Financial Services", "Brad Sherman", "Member of Congress"])
    rec = C.analyze_letter(text_pdf(lines), document_url=CDFI_URL, source_url=KAPTUR_URL, source_kind="committee_site", release=None,
                           resolver=roster[0], bio=roster[1], now=NOW)
    assert rec["status"] == "EXACT" and rec["is_letter"] and rec["subject_categories"] == ["CDFI Fund"]
    assert [s["member"] for s in rec["signatories"]] == ["Maxine Waters", "Brad Sherman"] and rec["leads"] == [rec["signatories"][0]["bioguide"]]


# ---- finding from measuring the press leg on the real newest press run (23,333 rows, 26 candidates) ------------------------------

def test_canonical_url_drops_fragments_and_tracking_but_keeps_the_page_identity():
    assert C.canonical_url("https://www.hydesmith.senate.gov/crapo-encourages#C000880") == "https://www.hydesmith.senate.gov/crapo-encourages"
    assert C.canonical_url("https://democrats-financialservices.house.gov/news/documentsingle.aspx?DocumentID=415374&utm_source=Sailthru&utm_term=x") \
        == "https://democrats-financialservices.house.gov/news/documentsingle.aspx?DocumentID=415374"
    assert C.canonical_url("https://x.house.gov/a?id=1&fbclid=z") == "https://x.house.gov/a?id=1"


def test_from_press_skips_non_official_hosts_and_fetches_a_page_once(root):
    new = root / "outputs" / "press_refresh_20261018"
    new.mkdir(parents=True)
    cols = ["title", "url", "date_final", "bioguide", "member", "body"]
    page = "https://waters.house.gov/media/press-releases/cdfi-letter"
    rows = [dict(title="Waters urges Treasury to protect CDFI Fund", url=u, date_final="2026-10-17", bioguide="W000187", member="Maxine Waters",
                 body="Waters sent a letter to Treasury about the CDFI Fund.")
            for u in (page, page + "#W000187", page + "?utm_source=email", "https://www.americascreditunions.org/news/cdfi-letter")]
    with open(new / "press_delta_fulltext.csv", "w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    ff = FakeFetcher({page: release_html(), CDFI_PDF: fx("fs_dems_cdfi_letter.pdf")})
    run(root, ff, legs=("press",))
    assert ff.requests == [page, CDFI_PDF]


def test_the_stored_body_keeps_a_cue_far_down_a_long_letter(roster):
    """The promoter screens the stored body for adverse cues, so a 6,000-char cap would hide a cue in the back half."""
    filler = ["We urge Treasury to protect the CDFI Fund and the credit unions it supports. " * 2] * 55
    lines = (["April 21, 2025", "The Honorable Scott Bessent", "Dear Secretary Bessent:"] + filler
             + ["Congress should repeal the exemption.", "Sincerely,", "Maxine Waters", "Ranking Member, Committee", "on Financial Services"])
    rec = C.analyze_letter(text_pdf(lines), document_url=CDFI_URL, source_url=KAPTUR_URL, source_kind="committee_site", release=None,
                           resolver=roster[0], bio=roster[1], now=NOW)
    assert len(rec["body"]) > 6000 and "repeal the exemption" in rec["body"]


def test_the_default_committee_list_has_only_verified_hosts():
    """banking.senate.gov answered 410 to every path on 2026-10-20; its listing URLs were never verified and it would show PARTIAL daily."""
    assert [key for key, _, _ in C.COMMITTEE_LISTINGS] == ["fs_minority", "fs_majority"]
    assert not [url for _, url, _ in C.COMMITTEE_LISTINGS if "banking.senate.gov" in url]


# ---- review ruling 1: every page at or after the closing page needs a text layer -----------------------------------------------

LETTER_BODY = ["April 21, 2025", "The Honorable Scott Bessent", "Dear Secretary Bessent:",
               "We urge you to protect the CDFI Fund and the credit unions it supports. " * 3, "Sincerely,",
               "Maxine Waters", "Ranking Member, Committee", "on Financial Services"]
SIGNERS_P2 = ["Brad Sherman", "Member of Congress", "Page 2 of the letter signatures"]


def analyze_pdf(roster, raw):
    return C.analyze_letter(raw, document_url=CDFI_URL, source_url=KAPTUR_URL, source_kind="committee_site", release=None,
                            resolver=roster[0], bio=roster[1], now=NOW)


def test_a_signature_page_without_a_text_layer_makes_the_letter_not_exact(roster):
    """Signatures on an image-only page would be silently missing: the earlier pages' names would still look complete."""
    rec = analyze_pdf(roster, text_pdf(LETTER_BODY, SIGNERS_P2, []))
    assert rec["status"] == "NOT_EXACT:page_without_text_layer" and rec["blank_pages"] == [3]
    assert [s["member"] for s in rec["signatories"]] == ["Maxine Waters", "Brad Sherman"]


def test_a_page_holding_only_a_page_number_is_without_text(roster):
    assert analyze_pdf(roster, text_pdf(LETTER_BODY, SIGNERS_P2, ["Page 3"]))["status"] == "NOT_EXACT:page_without_text_layer"


def test_a_blank_page_before_the_closing_page_does_not_matter(roster):
    rec = analyze_pdf(roster, text_pdf([], LETTER_BODY, SIGNERS_P2))
    assert rec["status"] == "EXACT" and rec["blank_pages"] == []


# ---- review ruling 2: "joined a letter led by X" names X, not the joiner ------------------------------------------------------

def signers(roster, *names):
    return [{"member": n, "bioguide": roster[1][n], "status": "roster"} for n in names]


def test_find_leads_reads_the_names_after_led_by(roster):
    sig = signers(roster, "Brad Sherman", "Maxine Waters", "Bill Foster")
    text = "Representative Brad Sherman joined a letter led by Maxine Waters and Bill Foster urging Treasury to act."
    assert C.find_leads(text, sig) == [roster[1]["Maxine Waters"], roster[1]["Bill Foster"]]
    assert C.find_leads("Brad Sherman signed a letter authored by Maxine Waters.", sig) == [roster[1]["Maxine Waters"]]
    assert C.find_leads("Brad Sherman joined a letter spearheaded by Bill Foster.", sig) == [roster[1]["Bill Foster"]]


def test_find_leads_still_reads_the_names_before_an_active_verb(roster):
    sig = signers(roster, "Brad Sherman", "Maxine Waters", "Bill Foster")
    assert C.find_leads("Maxine Waters and Bill Foster led 86 of their colleagues in urging Treasury.", sig) == \
        [roster[1]["Maxine Waters"], roster[1]["Bill Foster"]]


# ---- review ruling 7: a listing's first page with 0 items is a parse failure, never "the end" ----------------------------------

def test_an_unparsable_first_listing_page_is_a_gap_and_never_completes_the_backfill(root):
    pages = {LIST_URL: b"<html><body><div>site redesigned, no articles here</div></body></html>"}
    receipt = run(root, FakeFetcher(pages), legs=("backfill",), pages=10)
    cursor_path = root / "letters" / "backfill_cursor.json"
    cursor = json.loads(cursor_path.read_text(encoding="utf-8")) if cursor_path.exists() else {}
    assert "listing_unparsed:fs_test" in receipt["gaps"] and receipt["status"] == "PARTIAL"
    assert not cursor.get("fs_test", {}).get("done", False)


def test_the_daily_committee_leg_also_reports_an_unparsable_first_page(root):
    receipt = run(root, FakeFetcher({LIST_URL: b"<html></html>"}))
    assert receipt["gaps"] == ["listing_unparsed:fs_test"] and receipt["status"] == "PARTIAL"


def test_an_empty_later_page_still_ends_the_backfill(root):
    p1 = listing_html([("documentsingle.aspx?DocumentID=900009", "Floor statement", "2022-02-01", "Today")])
    receipt = run(root, FakeFetcher({LIST_URL: p1, LIST_URL + "&Page=2": b"<html></html>"}), legs=("backfill",), pages=10)
    cursor = json.loads((root / "letters" / "backfill_cursor.json").read_text(encoding="utf-8"))
    assert cursor["fs_test"]["done"] is True and receipt["gaps"] == []


# ---- review ruling 9: one bad PDF must not lose the run; a crash must not lose what was staged ------------------------------------

def test_an_exception_while_analyzing_one_pdf_is_staged_as_an_analyze_error_and_the_rest_continue(root, monkeypatch):
    real = C.analyze_letter
    second_url = "https://democrats-financialservices.house.gov/UploadedFiles/second.pdf"

    def flaky(raw, **kw):
        if kw["document_url"] == CDFI_PDF:
            raise ValueError("boom")
        return real(raw, **kw)

    monkeypatch.setattr(C, "analyze_letter", flaky)
    pages = cdfi_pages()
    pages[REL_URL] = release_html(text="Waters sent a letter on the CDFI Fund. Second letter: " + second_url).replace(
        b"</p>", ('<a href="%s">second letter</a></p>' % second_url).encode())
    pages[second_url] = text_pdf(LETTER_BODY, SIGNERS_P2)
    receipt = run(root, FakeFetcher(pages))
    records = staged(root)
    bad = [r for r in records.values() if r["status"] == "NOT_EXACT:analyze_error:ValueError"]
    assert len(bad) == 1 and bad[0]["document_url"] == CDFI_PDF and bad[0]["sha256"]
    assert receipt["errors"] == 1 and receipt["status"] == "PARTIAL"
    assert any(r["status"] == "EXACT" for r in records.values())            # the other PDF was analyzed and staged


def test_a_crashing_leg_keeps_what_was_staged_and_reports_a_gap(root, monkeypatch):
    real = C.parse_listing
    calls = []

    def crash_on_second(html, url):
        calls.append(url)
        if len(calls) == 2:
            raise RuntimeError("markup surprise")
        return real(html, url)

    monkeypatch.setattr(C, "parse_listing", crash_on_second)
    pages = cdfi_pages()
    pages[LIST_URL + "&Page=2"] = b"<html></html>"
    receipt = run(root, FakeFetcher(pages), pages=3)
    assert "leg_crashed:committee:RuntimeError" in receipt["gaps"] and receipt["status"] == "PARTIAL"
    assert "LTR-119-CDFI-WATERS" in staged(root)
    assert json.loads((root / "letters" / "collector_receipt.json").read_text(encoding="utf-8"))["status"] == "PARTIAL"


def test_an_analyze_error_is_retried_after_a_day_and_replaced_by_the_real_record(root, monkeypatch):
    real = C.analyze_letter
    monkeypatch.setattr(C, "analyze_letter", lambda raw, **kw: (_ for _ in ()).throw(KeyError("x")))
    run(root, FakeFetcher(cdfi_pages()))
    (stub,) = staged(root).values()
    assert stub["status"] == "NOT_EXACT:analyze_error:KeyError" and stub["retry_after"] == "2026-10-21"
    monkeypatch.setattr(C, "analyze_letter", real)
    same_day = FakeFetcher(cdfi_pages())
    run(root, same_day)
    assert same_day.requests == [LIST_URL]                                   # not due yet: the release is still 'known'
    later = dt.datetime(2026, 10, 22, 9, 0, 0, tzinfo=dt.timezone.utc)
    C.collect(root=str(root), letters_dir=str(root / "letters"), legs=["committee"], fetcher=FakeFetcher(cdfi_pages()), now=later,
              listings=(("fs_test", LIST_URL, True),), pages=1)
    records = staged(root)
    assert list(records) == ["LTR-119-CDFI-WATERS"] and records["LTR-119-CDFI-WATERS"]["status"] == "EXACT"


# ---- review ruling 12: hosts_failed shape, robots outage is a failure not a refusal ---------------------------------------------

def test_hosts_failed_records_a_count_the_last_error_and_a_few_urls(root):
    pages = cdfi_pages()
    del pages[CDFI_PDF]
    receipt = run(root, FakeFetcher(pages))
    assert receipt["hosts_failed"] == {"democrats-financialservices.house.gov": {"count": 1, "last": "HTTP 404", "urls": [CDFI_PDF]}}


def test_hosts_failed_keeps_only_five_urls_but_counts_them_all(root):
    items = [("documentsingle.aspx?DocumentID=%d" % (910000 + i), "Waters urges action %d" % i, "2026-01-01", "a letter") for i in range(7)]
    receipt = run(root, FakeFetcher({LIST_URL: listing_html(items)}))
    entry = receipt["hosts_failed"]["democrats-financialservices.house.gov"]
    assert entry["count"] == 7 and len(entry["urls"]) == 5


@pytest.mark.parametrize("status", [500, 503])
def test_a_robots_outage_is_a_fetch_failure_not_a_refusal(net, status):
    make, calls, sleeps, served = net
    served[ROBOTS] = (status, b"")
    with pytest.raises(C.FetchFailed, match="robots_unavailable"):
        make().get(DOC)


def test_a_robots_network_error_is_a_fetch_failure_not_a_refusal(net):
    make, calls, sleeps, served = net

    def broken(url, max_bytes):
        raise C.FetchFailed("timed out")

    fetcher = C.Fetcher(opener=broken, sleep=lambda s: None, clock=lambda: 0.0)
    with pytest.raises(C.FetchFailed, match="robots_unavailable"):
        fetcher.get(DOC)


def test_an_outage_marks_the_run_partial_through_errors_not_hosts_refused(root):
    class Outage(FakeFetcher):
        def get(self, url, max_bytes=C.HTML_CAP):
            raise C.FetchFailed("robots_unavailable")

    receipt = run(root, Outage({}))
    assert receipt["status"] == "PARTIAL" and receipt["hosts_refused"] == {} and receipt["errors"] == 1


def test_a_release_without_a_pdf_is_retried_after_seven_days_and_replaced_when_the_letter_appears(root):
    no_pdf = b"<html><head><title>Waters statement</title></head><body><p>A statement, no letter yet.</p></body></html>"
    pages = cdfi_pages()
    pages[REL_URL] = no_pdf
    run(root, FakeFetcher(pages))
    (stub,) = staged(root).values()
    assert stub["status"] == "NOT_EXACT:no_pdf_link" and stub["retry_after"] == "2026-10-27"
    soon = FakeFetcher(cdfi_pages())
    run(root, soon)
    assert soon.requests == [LIST_URL]                                       # not due: no refetch
    due = dt.datetime(2026, 10, 28, 9, 0, 0, tzinfo=dt.timezone.utc)
    C.collect(root=str(root), letters_dir=str(root / "letters"), legs=["committee"], fetcher=FakeFetcher(cdfi_pages()), now=due,
              listings=(("fs_test", LIST_URL, True),), pages=1)
    records = staged(root)
    assert list(records) == ["LTR-119-CDFI-WATERS"] and records["LTR-119-CDFI-WATERS"]["status"] == "EXACT"


def test_a_still_pdfless_release_gets_a_fresh_retry_date(root):
    no_pdf = b"<html><head><title>Waters statement</title></head><body><p>No letter.</p></body></html>"
    pages = cdfi_pages()
    pages[REL_URL] = no_pdf
    run(root, FakeFetcher(pages))
    due = dt.datetime(2026, 10, 28, 9, 0, 0, tzinfo=dt.timezone.utc)
    C.collect(root=str(root), letters_dir=str(root / "letters"), legs=["committee"], fetcher=FakeFetcher(pages), now=due,
              listings=(("fs_test", LIST_URL, True),), pages=1)
    (stub,) = staged(root).values()
    assert stub["retry_after"] == "2026-11-04"


# ---- review ruling 12: the press leg refuses a feed whose columns are missing -------------------------------------------------

def test_a_press_feed_without_the_expected_columns_is_a_schema_gap_not_zero_letters(root):
    new = root / "outputs" / "press_refresh_20261018"
    new.mkdir(parents=True)
    (new / "press_delta_fulltext.csv").write_text("link,headline,text\nhttps://waters.house.gov/x,Waters urges CDFI Fund letter,body\n", encoding="utf-8")
    ff = FakeFetcher({})
    receipt = run(root, ff, legs=("press",))
    assert "press_schema" in receipt["gaps"] and receipt["status"] == "PARTIAL" and ff.requests == []


# ---- review ruling 12: an interrupted atomic write must not leave an untracked, committable temp file -------------------------------

def test_atomic_write_temp_files_match_an_ignored_pattern(tmp_path, monkeypatch):
    import subprocess
    import tempfile
    seen = []
    real = tempfile.mkstemp

    def spy(*a, **k):
        fd, name = real(*a, **k)
        seen.append(name)
        return fd, name

    monkeypatch.setattr(tempfile, "mkstemp", spy)
    C._atomic_write(str(tmp_path / "x.json"), b"{}")
    assert seen and seen[0].endswith(".tmp")
    repo = Path(__file__).resolve().parents[3]
    if not (repo / ".gitignore").is_file():   # the public source export ships no .gitignore; the private repo does and is checked there
        pytest.skip("no .gitignore in this checkout")
    probe = repo / "data" / "legislation" / "letters" / Path(seen[0]).name
    try:
        ignored = subprocess.run(["git", "check-ignore", "-q", str(probe)], cwd=str(repo), capture_output=True).returncode
    except OSError:
        pytest.skip("git is not available")
    assert ignored == 0, "temp files from _atomic_write are not git-ignored: %s" % probe
