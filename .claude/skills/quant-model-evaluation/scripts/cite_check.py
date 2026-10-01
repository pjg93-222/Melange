#!/usr/bin/env python3
"""Reference-integrity and currency checker (axis R and flag C of references/citation.md). Read-only: reads one
reference file, sends HTTPS GETs only to doi.org, api.crossref.org, api.openalex.org and api.datacite.org, and
writes only its run folder (plus new files in --cache DIR when given).

Per reference: identifier (DOI; arXiv id -> 10.48550/arXiv.<id>; SSRN and NBER ids or links -> their DOIs) ->
doi.org handle -> doi.org RA -> CrossRef or DataCite record -> identity against the supplied metadata (title
similarity, first-author family name, year, venue; for --text/--dois the words on the same line, see --no-context)
-> currency from that record (CrossRef updated-by/update-to/relation incl. Retraction Watch entries, DataCite
version relations), cross-checked against OpenAlex is_retracted when OpenAlex answers (--no-openalex skips it) ->
grade R, flag C, verdict (rules below). A reference without an identifier (a BibTeX or CSL-JSON entry, or a --text
line that reads like a reference-list entry) is searched by title: CrossRef query.bibliographic first, OpenAlex
search as the fallback, at most one search per second (--no-search turns this off). A BibTeX entry with unbalanced
braces is reported as malformed (UNVERIFIED-HERE), never skipped or merged into its neighbours.

Usage:
  python scripts/cite_check.py --bib refs.bib
  python scripts/cite_check.py --text notes/bibliography.md --cache .cite_cache
  python scripts/cite_check.py --dois ids.txt --offline

Exit codes: 0 all SURVIVES · 1 any WOUNDED/KILLED · 2 usage/input error · 3 UNVERIFIED-HERE present.
"""
from __future__ import annotations

import csv, hashlib, html, http.client, io, json, pathlib, re, sys, textwrap, time, unicodedata  # noqa: E401
import urllib.error, urllib.parse, urllib.request  # noqa: E401
from dataclasses import dataclass, field
from datetime import timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import (KILLED, SURVIVES, UNVERIFIED, WOUNDED, Check, Report, UsageError,  # noqa: E402
                     _redact_home, base_parser, emit, require_file, run_main, write_once)

SCRIPT = "cite_check"
UA_BASE = "quant-model-evaluation/1.0.0 (cite_check)"
ALLOWED_HOSTS = frozenset({"doi.org", "api.crossref.org", "api.openalex.org", "api.datacite.org"})
MAILTO_HOSTS = frozenset({"api.crossref.org", "api.datacite.org"})  # the only hosts where a contact picks a pool
R_OK, R_MINOR, R_CONFLICT = "R-VERIFIED", "R-MISMATCH-MINOR", "R-IDENTIFIER-CONFLICT"
R_NOTLOC, R_UNVER = "R-NOT-LOCATED", "R-UNVERIFIED-HERE"
UPDATE_FLAGS = {  # Crossmark and Retraction Watch update types -> flag C
    "retraction": "RETRACTED", "partial_retraction": "RETRACTED", "withdrawal": "WITHDRAWN",
    "removal": "WITHDRAWN", "expression_of_concern": "EOC", "correction": "CORRECTED",
    "corrigendum": "CORRECTED", "erratum": "CORRECTED", "new_version": "NEWER-VERSION",
    "new_edition": "NEWER-VERSION", "addendum": "ADDENDUM", "clarification": "ADDENDUM"}
C_ORDER = ("RETRACTED", "WITHDRAWN", "EOC", "CORRECTED", "UPDATED", "NEWER-VERSION", "ADDENDUM")
FATAL = frozenset({"RETRACTED", "WITHDRAWN"})
ADVERSE = frozenset({"EOC", "CORRECTED", "UPDATED", "NEWER-VERSION"})
SEARCHABLE = frozenset(  # entry types CrossRef/OpenAlex index; misc, online, dataset, legal items are not searched
    "article inproceedings conference incollection inbook book booklet techreport report phdthesis mastersthesis "
    "thesis unpublished proceedings article-journal paper-conference chapter manuscript".split())
STOP = frozenset("a an and the of in on for to with by at from as is are its via or".split())
NAME_PARTICLES = frozenset("and et al van von de der den da di du le la del dos das y".split())
FOLD = str.maketrans({"ø": "o", "đ": "d", "ł": "l", "æ": "ae", "œ": "oe", "þ": "th", "ð": "d", "ı": "i"})
DOI_RX = re.compile(r"10\.\d{4,9}/[^\s\"'`|]+")
ARXIV_RX = re.compile(r"arxiv(?:\.org/(?:abs|pdf)/|:\s?|\s+)(\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z]{2})?/\d{7})(v\d+)?", re.I)
SSRN_RX = re.compile(r"ssrn\.com/(?:abstract=|sol3/papers\.cfm\?abstract_id=)(\d{3,9})", re.I)
NBER_RX = re.compile(r"nber\.org/papers/(w\d{3,6})", re.I)
YEAR_RX = re.compile(r"\b(1[5-9]\d\d|20\d\d)\b")
PREFIX_RX = re.compile(r"^\s*(?:retracted(?: article)?|withdrawn|(?:replication |supplementary )?(?:data(?: and code)?"
                       r"|code|materials?|package|dataset|files)(?: and code)? for)\s*[:\-]\s*", re.I)
TEXT_REF_RX = re.compile(  # a reference-list line: [list marker] author block, then "(1990)." or ". 1990.", then title
    r"^\s*(?:[-*+]\s+|\d{1,3}[.)]\s+|\[\d{1,3}\]\s+)?(?P<authors>[^\d()\[\]{}<>|:]{2,200}?)\s*"
    r"(?:\((?P<y1>(?:1[5-9]|20)\d\d)[a-z]?\)|(?P<y2>(?:1[5-9]|20)\d\d)[a-z]?)\s*\.\s+(?P<rest>\S.*)$")
BIB_ENTRY = re.compile(r"@\s*([A-Za-z]+)\s*([{(])")
BIB_START = re.compile(r"^[ \t]*@\s*[A-Za-z]+\s*[{(]", re.M)  # an entry beginning a line bounds the one before it
BIB_LEFTOVER = re.compile(r"^\s*[A-Za-z][\w:.+-]*\s*=\s*[{\"]", re.M)  # a field line left after an entry closed
BIB_FIELD = re.compile(r"([A-Za-z][\w:.+-]*)\s*=\s*(\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}"  # braces nest 3 deep
                       r"|\"(?:[^\"{}]|\{[^{}]*\})*\"|[\w.:/-]+)")                          # "quoted" | macro/number
COLUMNS = ("id doi id_type source_line r_grade c_flag verdict needs_second_reader matched_doi matched_title "
           "matched_first_author matched_year matched_venue title_similarity supplied_title supplied_first_author "
           "supplied_year supplied_venue registration_agency endpoints notes").split()
SCOPE = ("Grade R: R-VERIFIED | R-MISMATCH-MINOR | R-IDENTIFIER-CONFLICT | R-NOT-LOCATED | R-UNVERIFIED-HERE (never "
         "R-FABRICATED). Flag C: RETRACTED, WITHDRAWN, EOC, CORRECTED, UPDATED (unknown update type), NEWER-VERSION, "
         "ADDENDUM (informational), else NONE-FOUND@<date read> or NOT-CHECKED (no registry record was read). "
         "Verdicts: R-VERIFIED with no adverse flag -> SURVIVES; R-MISMATCH-MINOR, EOC, CORRECTED, UPDATED, "
         "NEWER-VERSION -> WOUNDED; RETRACTED/WITHDRAWN with identity verified -> KILLED; R-IDENTIFIER-CONFLICT, "
         "R-NOT-LOCATED -> WOUNDED pending a second reader (every KILLED needs one too); 429, 5xx, timeouts, "
         "unreadable bodies, malformed BibTeX entries and --offline -> UNVERIFIED-HERE, never a pass. Currency is "
         "graded from the CrossRef or DataCite record; OpenAlex is_retracted is a supplementary cross-check, so an "
         "OpenAlex failure (or --no-openalex) is noted, not fatal. Identity for --text/--dois lines without other "
         "metadata comes from the words on the same line (--no-context skips it). Title search (no identifier) accepts "
         "a candidate only at title similarity >= --min-title-sim with the first-author family name and the year "
         "(within --year-tolerance) agreeing; R-NOT-LOCATED ('not located in CrossRef or OpenAlex; needs second "
         "reader') needs both indexes to answer with no candidate >= --candidate-title-sim (no domain index is "
         "searched); a nearer miss, a silent index or --no-openalex gives UNVERIFIED-HERE. Cached answers (--cache) "
         "are copies of earlier registry answers and are not re-verified: each read is logged with its file sha256, "
         "and --no-cache-read fetches fresh answers. Not checked: whether a source supports the claim citing it (axis "
         "S); NONE-FOUND@date means no notice was indexed that day. --mailto is never auto-filled, goes only to "
         "CrossRef and DataCite, and is redacted from the report.")
_clock, _sleep = time.monotonic, time.sleep  # tests replace these (and http_get)

# ----------------------------------------------------------------------------- text normalization and matching
def fold(s: Any) -> str:
    """Casefold; drop HTML tags/entities and diacritics (Müller -> muller, Sørensen -> sorensen)."""
    s = html.unescape(re.sub(r"<[^>]+>", " ", str(s or ""))).casefold().translate(FOLD)
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def words(s: Any, drop_stop: bool = True) -> list[str]:
    toks = re.findall(r"[a-z0-9]+", fold(s))
    kept = [t for t in toks if t not in STOP] if drop_stop else toks
    return kept if len(kept) >= 2 else toks

def clean_title(t: Any) -> str:
    """Strip RETRACTED:/WITHDRAWN: and dataset prefixes such as "Replication data for:" (they vary legitimately)."""
    return PREFIX_RX.sub("", PREFIX_RX.sub("", str(t or "")))

def main_title(t: str) -> str:
    """The title without any subtitle."""
    return re.split(r"[:?!]|\s[-\u2013\u2014]\s", t, maxsplit=1)[0]

def tok_sim(a: list[str], b: list[str]) -> float:
    """Sorensen-Dice on word tokens. After exact matches, leftover words of 4+ letters pair at difflib ratio >= 0.85,
    so spelling variants (modelling/modeling, behaviour/behavior) count as the same word."""
    pool, left = list(b), []
    for t in a:
        if t in pool:
            pool.remove(t)
        else:
            left.append(t)
    for t in left:
        cands = [(SequenceMatcher(None, t, u).ratio(), u) for u in pool if min(len(t), len(u)) >= 4]
        if cands and max(cands)[0] >= 0.85:
            pool.remove(max(cands)[1])
    return 2.0 * (len(b) - len(pool)) / max(1, len(a) + len(b))

def title_sims(supplied: str, variants: list[str]) -> tuple[float, float]:
    """(full, main): best similarity of the whole titles, and of the titles compared without a subtitle."""
    s, full, main = clean_title(supplied), 0.0, 0.0
    for v in map(clean_title, variants):
        full = max(full, tok_sim(words(s), words(v)))
        for x, y in ((main_title(s), v), (s, main_title(v)), (main_title(s), main_title(v))):
            if min(len(words(x)), len(words(y))) >= 3:
                main = max(main, tok_sim(words(x), words(y)))
    return full, main

def last_name(full: Any) -> str:
    """Family name from 'Family, Given' or 'Given Family' (Jr./III dropped)."""
    full = str(full or "").strip()
    if "," in full:
        return full.split(",")[0].strip()
    toks = [t for t in full.split() if fold(t).strip(".") not in ("jr", "sr", "ii", "iii", "iv")]
    return toks[-1] if toks else ""

def fam_match(a: str, b: str) -> bool:
    """Same family name: equal after folding, same last word (van Beethoven ~ Beethoven), or word containment."""
    ta, tb = words(a, False), words(b, False)
    if not ta or not tb:
        return False
    return ta[-1] == tb[-1] or set(ta) <= set(tb) or set(tb) <= set(ta)

def venue_sim(a: str, b: str) -> float:
    """Word similarity in which abbreviations and acronyms match (J. Bank. Financ.; JFE)."""
    ta, tb = words(a), words(b)
    if len(ta) == 1 and ta[0] == "".join(u[0] for u in tb):
        return 1.0
    pool = list(tb)
    for t in ta:
        u = next((u for u in pool if u.startswith(t) or t.startswith(u)), None)
        if u is not None:
            pool.remove(u)
    return 2.0 * (len(tb) - len(pool)) / max(1, len(ta) + len(tb))

# ----------------------------------------------------------------------------- identifiers
def trim_id(s: str) -> str:
    """Drop trailing sentence punctuation and unbalanced closing brackets ("10.1/x)." -> "10.1/x")."""
    pairs = {")": "(", "]": "[", "}": "{", ">": "<"}
    while s and (s[-1] in ".,;:!?*_~" or (s[-1] in pairs and s.count(s[-1]) > s.count(pairs[s[-1]]))):
        s = s[:-1]
    return s

def classify(token: str) -> tuple[str, str | None, str]:
    """(kind, DOI, note) for an identifier: arXiv -> 10.48550/arxiv.*, SSRN -> 10.2139/ssrn.*, NBER -> 10.3386/*."""
    t = re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/|^doi:\s*", "", trim_id(str(token).strip()), flags=re.I)
    if re.search(r"%[0-9A-Fa-f]{2}", t):
        t = urllib.parse.unquote(t)
    if re.fullmatch(r"10\.\d{4,9}/\S+", t):
        return "doi", t.lower(), ""
    m = re.fullmatch(r"(?:arxiv:\s?|(?:https?://)?(?:www\.)?arxiv\.org/(?:abs|pdf)/)?"
                     r"(\d{4}\.\d{4,5}|[a-z-]+(?:\.[a-z]{2})?/\d{7})(v\d+)?(?:\.pdf)?", t, re.I)
    if m:
        return "arxiv", f"10.48550/arxiv.{m.group(1).lower()}", f"arXiv {m.group(2)} cited" if m.group(2) else ""
    m = re.fullmatch(r"(?:ssrn:\s?|(?:https?://)?(?:papers\.)?ssrn\.com/(?:abstract=|sol3/papers\.cfm\?abstract_id=))"
                     r"(\d{3,9})", t, re.I)
    if m:
        return "ssrn", f"10.2139/ssrn.{m.group(1)}", "SSRN abstract id mapped to its DOI"
    m = re.fullmatch(r"(?:nber:\s?|(?:https?://)?(?:www\.)?nber\.org/papers/)(w\d{3,6})", t, re.I)
    if m:
        return "nber", f"10.3386/{m.group(1).lower()}", "NBER working-paper number mapped to its DOI"
    if t.startswith("10."):
        return "doi-invalid", None, f"DOI syntax invalid: {t[:80]}"
    return "unrecognized", None, f"not a DOI, arXiv, SSRN or NBER identifier: {t[:80]}"

@dataclass
class Ref:
    rid: str
    source: str
    kind: str = "none"
    doi: str | None = None
    title: str = ""
    authors: list = field(default_factory=list)
    year: int | None = None
    venue: str = ""
    etype: str = ""
    context: str = ""
    notes: list = field(default_factory=list)

    def identify(self, *fields: Any, strict: bool = False) -> "Ref":
        """Take the first field (doi, eprint, url...) holding a DOI or arXiv id; strict keeps an unrecognized one."""
        for tok in (str(f or "").split()[:1] for f in fields):
            kind, doi, note = classify(tok[0]) if tok else ("", None, "")
            if kind and (strict or kind != "unrecognized"):
                self.kind, self.doi = kind, doi
                self.notes += [note] if note else []
                break
        return self

# ----------------------------------------------------------------------------- input parsers
def dedupe(refs: list[Ref]) -> list[Ref]:
    """One row per identifier for --dois/--text; later sightings add their line and their context."""
    seen: dict[str, Ref] = {}
    for r in refs:
        first = seen.setdefault(r.doi or r.rid.lower(), r)
        if first is not r:
            first.notes.append(f"also at {r.source}")
            first.context += " " + r.context
    return list(seen.values())

def parse_dois(text: str) -> list[Ref]:
    """One identifier per line; words after it are context for the identity check; '#' starts a comment line."""
    refs = []
    for n, line in enumerate(text.splitlines(), 1):
        parts = line.split(None, 1)
        if parts and not parts[0].startswith("#"):
            context = parts[1].lstrip("# ") if len(parts) > 1 else ""
            refs.append(Ref(trim_id(parts[0]), f"line {n}", context=context).identify(parts[0], strict=True))
    return dedupe(refs)

def text_family(block: str) -> str:
    """First author's family name: "Hall, R. L., & Wayman", "Richard L. Hall and ...", "Hall RL, ...", "Chen et al."."""
    first = re.split(r"\s+(?:and|&)\s+|\s*;\s*|\s+et\s+al\b", block.strip(), maxsplit=1)[0].strip(" ,.")
    head = first.split(",")[0].strip()
    toks = head.split()
    if len(toks) >= 2 and re.fullmatch(r"[A-Z]{1,3}", toks[-1].replace(".", "")):
        return " ".join(toks[:-1])
    return head if "," in first else last_name(head)

def text_reference(line: str, n: int) -> Ref | None:
    """A --text line without an identifier that reads like a reference-list entry (author block of names, a year as
    "(1990)." or ". 1990.", then a title of 3+ words); prose such as "Hall (1990) shows that..." does not qualify."""
    m = TEXT_REF_RX.match(line)
    if not m:
        return None
    block = m.group("authors").strip()
    toks = re.findall(r"[^\s,;&]+", block)
    names_only = bool(toks) and toks[0][:1].isupper() and all(
        t[:1].isupper() or t.lower().rstrip(".") in NAME_PARTICLES for t in toks)
    if not names_only or (m.group("y2") and not block.endswith(".")):
        return None
    rest = re.sub(r"[*_]", "", m.group("rest")).strip()
    quoted = re.match(r"[\"\u201c]([^\"\u201d]{3,300})[\"\u201d]", rest)
    title = quoted.group(1) if quoted else re.split(r"(?<![A-Z])[.?!](?:\s|$)", rest, maxsplit=1)[0]
    if len(title.split()) < 3:
        return None
    family, year = text_family(block), int(m.group("y1") or m.group("y2"))
    web = "online" if re.search(r"https?://", line) else ""  # a web page cited without a DOI is not searched
    return Ref(f"line {n}: {family} {year}", f"line {n}", title=title.strip(), authors=[family], year=year,
               etype=web, context=line)

def parse_text(text: str) -> list[Ref]:
    """Identifiers anywhere in prose or markdown; a line without one may still be a reference-list entry."""
    refs = []
    for n, line in enumerate(text.splitlines(), 1):
        ids = [trim_id(m.group(0)) for m in DOI_RX.finditer(line)]
        ids += [f"arXiv:{m.group(1)}{m.group(2) or ''}" for m in ARXIV_RX.finditer(line)]
        ids += [f"ssrn:{m.group(1)}" for m in SSRN_RX.finditer(line)]
        ids += [f"nber:{m.group(1)}" for m in NBER_RX.finditer(line)]
        context = re.sub(r"https?://\S+|10\.\d{4,9}/\S+", " ", line)
        refs += [Ref(i, f"line {n}", context=context).identify(i, strict=True) for i in ids]
        if not ids and (ref := text_reference(line, n)) is not None:
            refs.append(ref)
    return dedupe(refs)

def _close(text: str, k: int, stop: int | None = None) -> int:
    """Index of the '}' or ')' closing a BibTeX block whose opener sits at k - 1, searched no further than `stop`;
    -1 when the block does not close there."""
    depth, closer = 0, "}" if text[k - 1] == "{" else ")"
    for j in range(k, len(text) if stop is None else stop):
        if depth == 0 and text[j] == closer:
            return j
        depth += (text[j] == "{") - (text[j] == "}")
    return -1

def delatex(s: Any) -> str:
    """Plain text from a BibTeX value: accents reduced to the base letter, commands and braces dropped."""
    s = re.sub(r"\\(ss|ae|AE|oe|OE|aa|AA|[oOlLij])(?![A-Za-z])",
               lambda m: m.group(1)[:1] if m.group(1) in ("aa", "AA") else m.group(1), str(s or ""))
    s = re.sub(r"\\(?:[`'^\"~=.]|[uvHckrbdt](?![A-Za-z]))\s*\{?\s*([A-Za-z])\s*\}?", r"\1", s)
    s = re.sub(r"\\[A-Za-z]+\*?\s*", " ", s).replace("\\&", "&").replace("\\_", "_").replace("\\%", "%")
    return re.sub(r"\s+", " ", re.sub(r"[{}]", "", s).replace("~", " ").replace("--", "-")).strip()

def bib_names(raw: str) -> list[str]:
    """Family names from a BibTeX author field; a braced {Corporate Author} stays whole, 'others' is dropped."""
    names = []
    for part in re.split(r"\s+and\s+(?![^{]*\})", raw, flags=re.I):  # an 'and' inside braces does not split
        part = part.strip()
        name = delatex(part)
        if name and fold(name).rstrip(".") not in ("others", "et al"):
            corporate = part.startswith("{") and _close(part, 1) == len(part) - 1
            names.append(name if corporate else last_name(name))
    return names

def _bib_fields(body: str, macros: dict) -> tuple[dict, list]:
    """Field name -> value ({..}, "..", number or @string macro; no # joins). A repeated field keeps its first value."""
    fields, repeated = {}, []
    for x in BIB_FIELD.finditer(body):
        name, value = x.group(1).lower(), x.group(2)
        if name in fields:
            repeated.append(name)
        else:
            fields[name] = value[1:-1] if value[0] in "{\"" else macros.get(value.lower(), value)
    return fields, repeated

def parse_bib(text: str) -> list[Ref]:
    """Simple BibTeX reader. An entry must close before the next entry that begins a line; one that does not, or that
    leaves field lines or stray braces after its closing brace, becomes a malformed entry (graded UNVERIFIED-HERE,
    never looked up), so a broken entry is never skipped and never borrows its neighbours' fields."""
    refs, macros, pos = [], {}, 0
    starts = [s.start() for s in BIB_START.finditer(text)]
    for m in BIB_ENTRY.finditer(text):
        if m.start() < pos:
            continue
        stop = next((s for s in starts if s > m.start()), len(text))
        end = _close(text, m.end(), stop)
        tail = re.sub(r"(?m)^\s*%.*$", "", text[end + 1:stop]) if end >= 0 else ""  # '%' lines are comments
        broken = end < 0 or tail.count("{") != tail.count("}") or BIB_LEFTOVER.search(tail) is not None
        kind, line = m.group(1).lower(), text.count("\n", 0, m.start()) + 1
        body, pos = text[m.end():stop if broken else end], stop if broken else end + 1
        if kind in ("string", "comment", "preamble"):
            if kind == "string" and not broken:
                macros.update(_bib_fields(body, macros)[0])
            continue
        key = (body.partition(",")[0].split() or [f"entry@{line}"])[0]
        if broken:
            why = "it does not close before the next entry" if end < 0 else "text follows its closing brace"
            refs.append(Ref(key, f"line {line}", kind="malformed", etype=kind, notes=[
                f"malformed BibTeX entry ({why}); not looked up - fix the entry and re-run"]))
            continue
        fields, repeated = _bib_fields(body.partition(",")[2], macros)
        year = YEAR_RX.search(fields.get("year") or fields.get("date") or "")
        names = bib_names(fields.get("author") or fields.get("editor") or "")
        ref = Ref(key, f"line {line}", etype=kind, authors=names,
                  title=delatex(fields.get("title")), year=int(year.group(1)) if year else None,
                  venue=delatex(fields.get("journal") or fields.get("journaltitle") or fields.get("booktitle")),
                  notes=[f"repeated field(s) {', '.join(repeated)}: the first value was used"] if repeated else [])
        refs.append(ref.identify(*(delatex(fields.get(k)) for k in ("doi", "eprint", "url"))))
    return refs

def parse_csl(text: str) -> list[Ref]:
    data = _json(text.encode("utf-8"))
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise UsageError("--csl must hold a CSL-JSON array of items (valid JSON)")
    refs = []
    for n, it in enumerate((i for i in items if isinstance(i, dict)), 1):
        issued = it.get("issued") if isinstance(it.get("issued"), dict) else {}
        year = YEAR_RX.search(json.dumps(issued.get("date-parts") or issued.get("raw") or ""))
        arx = ARXIV_RX.search(" ".join(str(it.get(k) or "") for k in ("number", "note", "archive_location", "URL")))
        authors = [str(a.get("family") or a.get("literal")) for a in it.get("author") or []
                   if isinstance(a, dict) and (a.get("family") or a.get("literal"))]
        ref = Ref(str(it.get("id") or f"item{n}"), f"item {n}", title=str(it.get("title") or ""), authors=authors,
                  venue=_first(it.get("container-title")), year=int(year.group(1)) if year else None,
                  etype=str(it.get("type") or ""))
        refs.append(ref.identify(it.get("DOI"), it.get("URL"), f"arXiv:{arx.group(1)}" if arx else ""))
    return refs

# ----------------------------------------------------------------------------- network layer (the only I/O)
class HostNotAllowed(Exception):
    """A URL outside the four allowed hosts, or not HTTPS, was about to be requested."""

def check_url(url: str) -> str:
    u = urllib.parse.urlsplit(url)
    if u.scheme != "https" or (u.hostname or "") not in ALLOWED_HOSTS:
        raise HostNotAllowed(f"refusing {u.scheme}://{u.hostname}: only {', '.join(sorted(ALLOWED_HOSTS))} (https)")
    return u.hostname

class _AllowlistRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        host, new = check_url(newurl), super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and host not in MAILTO_HOSTS:
            new.add_header("User-agent", UA_BASE)  # a contact address never follows a redirect to another host
        return new

_OPENER = urllib.request.build_opener(_AllowlistRedirect())

def http_get(url: str, headers: dict, timeout: float) -> tuple[int, dict, bytes]:
    """The only network call (tests replace it): (status, headers, body) for any HTTP answer; raises on transport."""
    try:
        with _OPENER.open(urllib.request.Request(url, headers=headers), timeout=timeout) as resp:
            return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read(8 << 20)
    except urllib.error.HTTPError as exc:
        return exc.code, {k.lower(): v for k, v in (exc.headers or {}).items()}, b""

def _json(raw: bytes) -> Any:
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None

def _key(url: str) -> str:  # cache file stem for a URL
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]

def retry_after(value: Any, now: float | None = None) -> float | None:
    """Seconds from a Retry-After header: delta-seconds ("120") or an HTTP-date (RFC 9110); None if unreadable."""
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):  # None (no header) falls through too and is rejected by the date parser
        pass
    try:
        when = parsedate_to_datetime(str(value))
    except (TypeError, ValueError, IndexError):
        return None
    when = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
    return max(0.0, when.timestamp() - (time.time() if now is None else now))

@dataclass
class Resp:
    """One lookup. status None = transport failure. Only a readable 200 or a 404 counts as an answer."""
    url: str
    endpoint: str
    status: int | None
    body: Any = None
    error: str = ""
    fetched: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    cached: bool = False
    attempts: int = 1
    pool: str = ""
    cache_file: str = ""  # the cache file read (cached) or written (fresh), with its sha256
    cache_sha256: str = ""
    gave_up: bool = False  # a Retry-After longer than --max-backoff ended the retries
    ok = property(lambda s: s.status == 200 and s.body is not None)
    missing = property(lambda s: s.status == 404)
    failed = property(lambda s: not (s.ok or s.missing))  # never a pass
    why = property(lambda s: s.error or f"HTTP {s.status}")
    tag = property(lambda s: f"{s.endpoint}:{'ERR' if s.status is None else s.status}"
                   + ("(cache)" if s.cached else f"x{s.attempts}" if s.attempts > 1 else ""))

class Net:
    """Rate-limited, retrying, cached JSON GETs; logs every lookup (endpoint, status, attempts, API pool)."""
    def __init__(self, a, run_dir: pathlib.Path):
        self.a, self.memo, self.log, self.next, self.refused = a, {}, [], {}, set()
        self.rate = {h: a.max_rps for h in ALLOWED_HOSTS}
        self.rate["api.datacite.org"] = min(a.max_rps, 3.0 if a.mailto else 1.5)  # 1000 identified / 500 per 5 min
        self.rate["search"] = min(a.max_rps, 1.0)  # CrossRef's query pool allows 1/s; OpenAlex searches are metered
        self.ua_contact = f"{UA_BASE} mailto:{a.mailto}" if a.mailto else UA_BASE
        self.cache = pathlib.Path(a.cache).expanduser().resolve() if a.cache else run_dir / "cache"

    def get(self, url: str, endpoint: str, row: dict, search: bool = False) -> Resp:
        if url not in self.memo:
            host = check_url(url)
            if (host, search) in self.refused:  # the host refused this kind of call earlier in the run: stop asking
                r = Resp(url, endpoint, None, error=f"skipped: {host} answered 429 earlier in this run")
            else:
                r = self._cached(url, endpoint) or self._fetch(url, endpoint, host, search)
                if r.status == 429 and (search or r.gave_up):  # a throttled search, or a wait we will not sit out
                    self.refused |= {(host, True), (host, False)} if r.gave_up else {(host, True)}
            self.memo[url] = r
            self.log.append({"endpoint": endpoint, "url": url, "status": r.status, "error": r.error,
                             "attempts": r.attempts, "cached": r.cached, "pool": r.pool, "fetched_utc": r.fetched,
                             "cache_file": r.cache_file, "cache_sha256": r.cache_sha256})
        row["endpoints"].append(self.memo[url].tag)
        return self.memo[url]

    def _take_turn(self, bucket: str) -> None:
        """Token bucket of capacity 1 (no bursts): at most rate[bucket] requests per second."""
        now = _clock()
        if now < self.next.get(bucket, 0.0):
            _sleep(self.next[bucket] - now)
            now = self.next[bucket]
        self.next[bucket] = now + 1.0 / self.rate[bucket]

    def _fetch(self, url: str, endpoint: str, host: str, search: bool) -> Resp:
        a = self.a
        headers = {"Accept": "application/json", "User-Agent": self.ua_contact if host in MAILTO_HOSTS else UA_BASE}
        for attempt in range(1, a.retries + 2):
            self._take_turn("search" if search else host)
            hdrs: dict = {}
            try:
                status, hdrs, raw = http_get(url, headers, a.timeout)
                error, body = f"HTTP {status}", (_json(raw) if status in (200, 404) else None)
            except HostNotAllowed as exc:  # a redirect tried to leave the allowlist
                return Resp(url, endpoint, None, error=str(exc), attempts=attempt)
            except (urllib.error.URLError, http.client.HTTPException, OSError) as exc:  # includes timeouts
                status, error, body = None, f"transport error: {getattr(exc, 'reason', None) or exc!r}", None
            if status == 404 or (status == 200 and body is not None):
                return self._store(Resp(url, endpoint, status, body, attempts=attempt, pool=hdrs.get("x-api-pool", "")))
            if status == 200:
                error += "; unreadable body"
            wait = retry_after(hdrs.get("retry-after"))
            if wait is not None and wait > a.max_backoff:
                return Resp(url, endpoint, status, error=f"{error}; Retry-After {wait:.0f}s exceeds --max-backoff",
                            attempts=attempt, gave_up=True)
            if (status is not None and status not in (200, 429) and status < 500) or attempt > a.retries:
                return Resp(url, endpoint, status, error=error, attempts=attempt)  # 4xx other than 429: no retry
            _sleep(wait if wait is not None else min(a.backoff * 2 ** (attempt - 1), a.max_backoff))

    def _cached(self, url: str, endpoint: str) -> Resp | None:
        """Newest cached 200/404 answer for this URL, at most --cache-max-age days old; none with --no-cache-read.
        A cached answer is a copy, not a fresh registry read, so the file's name and sha256 go into the request log."""
        if self.a.no_cache_read:
            return None
        hit, max_age = None, self.a.cache_max_age * 86400
        for p in sorted(self.cache.glob(f"*-{_key(url)}-*.json")):
            try:
                raw = p.read_bytes()
                d = json.loads(raw.decode("utf-8"))
                fresh = 0 <= time.time() - d["fetched_epoch"] <= max_age
                if fresh and d["url"] == url and d["status"] in (200, 404):
                    hit = (d, p.name, hashlib.sha256(raw).hexdigest())
            except (OSError, ValueError, KeyError, TypeError):
                continue
        if hit is None:
            return None
        d, name, digest = hit
        return Resp(url, endpoint, d["status"], d.get("body"), cached=True, attempts=0,
                    fetched=d.get("fetched_utc", ""), pool=d.get("pool", ""), cache_file=name, cache_sha256=digest)

    def _store(self, r: Resp) -> Resp:
        """Write a new cache file for an answer (never replacing one) and note its name and sha256."""
        self.cache.mkdir(parents=True, exist_ok=True)
        stem = f"{r.endpoint}-{_key(r.url)}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}"
        path, n = self.cache / f"{stem}.json", 0
        while path.exists():
            n += 1
            path = self.cache / f"{stem}-{n}.json"
        text = json.dumps({"url": r.url, "endpoint": r.endpoint, "status": r.status, "pool": r.pool,
                           "fetched_utc": r.fetched, "fetched_epoch": time.time(), "body": r.body}, ensure_ascii=False)
        write_once(path, text)
        r.cache_file, r.cache_sha256 = path.name, hashlib.sha256(text.encode("utf-8")).hexdigest()
        return r

# ----------------------------------------------------------------------------- registry records
@dataclass
class Rec:
    """A registry record: identity fields, plus currency flags and notes."""
    doi: str
    titles: list
    authors: list
    years: set
    venues: list
    link: str = ""
    flags: set = field(default_factory=set)
    notes: list = field(default_factory=list)

def _first(v: Any) -> str:
    return str((v[0] if v else "") if isinstance(v, list) else v or "")

def norm_doi(v: Any) -> str:
    return re.sub(r"^(?:https?://)?(?:dx\.)?doi\.org/", "", str(v or "").strip(), flags=re.I).lower()

def parse_crossref(body: Any, doi: str) -> Rec:
    m = body["message"]
    t, sub = _first(m.get("title")), _first(m.get("subtitle"))
    people = sorted((p for p in m.get("author") or m.get("editor") or [] if isinstance(p, dict)),
                    key=lambda p: p.get("sequence") != "first")
    years = set()
    for k in ("issued", "published", "published-print", "published-online", "posted"):  # print and online both count
        parts = (m.get(k) or {}).get("date-parts") or [[None]]
        if parts and parts[0] and isinstance(parts[0][0], int):
            years.add(parts[0][0])
    rec = Rec(str(m.get("DOI") or doi).lower(),
              [x for x in (t, f"{t}: {sub}" if t and sub else "", _first(m.get("original-title"))) if x],
              [str(p.get("family") or p.get("name") or "") for p in people], years,
              [v for v in (_first(m.get(k)) for k in ("container-title", "short-container-title")) if v])
    seen: set = set()  # notices are read in both directions and de-duplicated (CrossRef deposits them both ways)
    for where in ("updated-by", "update-to"):
        for u in (u for u in m.get(where) or [] if isinstance(u, dict)):
            typ = re.sub(r"[\s-]+", "_", str(u.get("type") or "").lower())
            key = (typ, str(u.get("DOI") or "").lower(), u.get("source") or "publisher")
            if key in seen:
                continue
            seen.add(key)
            rec.flags.add(UPDATE_FLAGS.get(typ, "UPDATED"))
            when = str((u.get("updated") or {}).get("date-time") or "")[:10]
            rw = f" RW {u['record-id']}" if u.get("record-id") else ""
            rec.notes.append(f"{where} {typ or '?'} ({key[2]}{rw} {when}) {key[1]}".replace(" )", ")"))
    for k in ("is-preprint-of", "is-replaced-by"):  # a published or replacing version exists
        for r in (m.get("relation") or {}).get(k) or []:
            rec.flags.add("NEWER-VERSION")
            rec.notes.append(f"relation {k} {r.get('id', '')}".rstrip())
    if re.match(r"\s*retracted\b", t, re.I):  # publishers such as Elsevier prefix the title of a retracted work
        rec.flags.add("RETRACTED")
        rec.notes.append("title carries a RETRACTED prefix")
    return rec

def parse_datacite(body: Any, doi: str) -> Rec:
    at = body["data"]["attributes"]
    ts = [x for x in at.get("titles") or [] if isinstance(x, dict) and x.get("title")]
    main = [x["title"] for x in ts if not x.get("titleType")] or [x["title"] for x in ts[:1]]
    sub = [x["title"] for x in ts if x.get("titleType") == "Subtitle"]
    names = []
    for c in (c for c in at.get("creators") or [] if isinstance(c, dict)):
        organization = c.get("nameType") == "Organizational"
        names.append(str(c.get("familyName") or (c.get("name") if organization else last_name(c.get("name"))) or ""))
    pub, year = at.get("publisher"), str(at.get("publicationYear") or "")[:4]
    rec = Rec(str(at.get("doi") or doi).lower(), main + ([f"{main[0]}: {sub[0]}"] if main and sub else []), names,
              {int(year)} if year.isdigit() else set(),
              [v for v in [str(pub.get("name") if isinstance(pub, dict) else pub or "")] if v])
    for r in (r for r in at.get("relatedIdentifiers") or [] if isinstance(r, dict)):
        if r.get("relationType") in ("IsObsoletedBy", "IsPreviousVersionOf"):  # a newer version is registered
            rec.flags.add("NEWER-VERSION")
            rec.notes.append(f"DataCite {r['relationType']} {r.get('relatedIdentifier', '')}")
    return rec

def parse_openalex(w: Any) -> Rec:
    names = [(a.get("author") or {}).get("display_name") or a.get("raw_author_name") or ""
             for a in w.get("authorships") or [] if isinstance(a, dict)]
    source = (w.get("primary_location") or {}).get("source") or {}
    year = w.get("publication_year")
    return Rec(norm_doi(w.get("doi")), [x for x in (w.get("title"), w.get("display_name")) if x],
               [last_name(x) for x in names if x], {year} if isinstance(year, int) else set(),
               [source["display_name"]] if source.get("display_name") else [], link=str(w.get("id") or ""))

# ----------------------------------------------------------------------------- grading pipeline
def new_row(ref: Ref) -> dict:
    row = dict.fromkeys(COLUMNS, "")
    row.update(id=ref.rid, doi=ref.doi or "", id_type=ref.kind, source_line=ref.source, supplied_title=ref.title,
               supplied_first_author=(ref.authors or [""])[0], supplied_year=ref.year or "", supplied_venue=ref.venue,
               endpoints=[], notes=list(ref.notes), _flags=set(), _complete=False, _date="")
    return row

def graded(row: dict, grade: str, *notes: str) -> dict:
    row["r_grade"] = grade
    row["notes"] += [n for n in notes if n]
    return row

def check(ref: Ref, net: Net, a) -> dict:
    row = new_row(ref)
    if a.offline:
        return graded(row, R_UNVER, "offline: identifier syntax only, nothing looked up")
    if ref.kind == "malformed":  # the parser's note says why; its fields cannot be trusted, so nothing is looked up
        return graded(row, R_UNVER)
    if ref.kind == "doi-invalid":
        return graded(row, R_NOTLOC, "an invalid DOI cannot be registered")
    if ref.kind == "unrecognized":
        return graded(row, R_UNVER, "identifier type not supported here")
    return check_doi(ref.doi, ref, row, net, a) if ref.doi else locate(ref, row, net, a)

def check_doi(doi: str, ref: Ref, row: dict, net: Net, a) -> dict:
    """handle -> RA -> RA record -> OpenAlex; any lookup that fails stops at R-UNVERIFIED-HERE."""
    q = urllib.parse.quote(doi, safe="/")
    row["doi"] = row["doi"] or doi
    h = net.get(f"https://doi.org/api/handles/{q}", "doi.handle", row)
    code = h.body.get("responseCode") if isinstance(h.body, dict) else None
    if h.missing or code == 100:
        return not_registered(ref, row, net, a)
    if h.failed or code not in (1, 200):
        return graded(row, R_UNVER, f"doi.org handle lookup failed ({h.why if h.failed else f'responseCode {code}'})")
    ra = net.get(f"https://doi.org/ra/{q}", "doi.ra", row)
    agency = next((str(e["RA"]) for e in (ra.body if isinstance(ra.body, list) else [])
                   if isinstance(e, dict) and e.get("RA")), "")
    row["registration_agency"] = agency
    if not ra.ok:
        return graded(row, R_UNVER, f"doi.org RA lookup failed ({ra.why})")
    if agency.lower() not in ("crossref", "datacite"):
        return graded(row, R_UNVER, f"registration agency '{agency or 'unknown'}' has no allowed metadata endpoint")
    crossref = agency.lower() == "crossref"
    m = net.get(f"https://api.crossref.org/works/{q}" if crossref else f"https://api.datacite.org/dois/{q}",
                "crossref.work" if crossref else "datacite.doi", row)
    try:
        rec = (parse_crossref if crossref else parse_datacite)(m.body, doi) if m.ok else None
    except (AttributeError, TypeError, KeyError, IndexError, ValueError):
        rec = None
    if rec is None:
        return graded(row, R_UNVER, f"{m.endpoint} record not readable ({m.why if not m.ok else 'unexpected shape'})")
    oa = None if a.no_openalex else net.get(f"https://api.openalex.org/works/doi:{q}", "openalex.work", row)
    currency(rec, m, oa, row)
    grade, sim, notes = identity(ref, rec, a)
    row.update(matched_doi=rec.doi, matched_title=(rec.titles or [""])[0], matched_venue=(rec.venues or [""])[0],
               matched_first_author=(rec.authors or [""])[0], matched_year="/".join(map(str, sorted(rec.years))),
               title_similarity="" if sim is None else round(sim, 3))
    return graded(row, grade, *notes)

def not_registered(ref: Ref, row: dict, net: Net, a) -> dict:
    """The handle does not exist. A mapped SSRN/NBER DOI may simply not exist; otherwise look for the intended work."""
    if ref.kind in ("ssrn", "nber"):
        return graded(row, R_UNVER, "the mapped DOI is not registered; the paper may exist without one")
    if not unsearchable(ref, a):
        found = search(ref, row, net, a)
        if found.rec is not None and found.rec.doi:
            row.update(matched_doi=found.rec.doi, matched_title=found.rec.titles[0])
            return graded(row, R_CONFLICT, f"DOI not registered at doi.org; the supplied metadata matches "
                                           f"{found.rec.doi} ({found.index}, title {found.sim:.2f})")
    return graded(row, R_NOTLOC, "DOI not registered at doi.org (handle 404)")

def currency(rec: Rec, m: Resp, oa: Resp | None, row: dict) -> None:
    """Flag C from the registry record: CrossRef notices (incl. Retraction Watch) and relations, or DataCite version
    relations. OpenAlex is_retracted is a supplementary cross-check: when it is skipped (None) or fails, that is
    noted and the grade rests on the registry record."""
    flags, notes = set(rec.flags), list(rec.notes)
    if oa is not None and oa.ok and isinstance(oa.body, dict) and oa.body.get("is_retracted") is True:
        flags.add("RETRACTED")
        notes.append("OpenAlex is_retracted=true")
    elif oa is None or not oa.ok:
        why = "skipped (--no-openalex)" if oa is None else "has no record" if oa.missing else f"not read ({oa.why})"
        notes.append(f"OpenAlex {why}: is_retracted not cross-checked; currency from the {m.endpoint} record")
    row.update(_flags=flags, _complete=True, _date=(min(m.fetched, oa.fetched) if oa is not None and oa.ok
                                                    else m.fetched)[:10])
    row["notes"] += notes

def identity(ref: Ref, rec: Rec, a) -> tuple[str, float | None, list[str]]:
    """R grade from the supplied metadata: identity rests on title and first author; year and venue drift is minor."""
    notes, level, sim = [], set(), None

    def note(kind: str, text: str) -> None:  # kind is "minor" or "conflict"
        level.add(kind)
        notes.append(text)
    if ref.title and rec.titles:
        full, main = title_sims(ref.title, rec.titles)
        sim = max(full, main)
        if full < a.min_title_sim <= main:
            note("minor", f"title matches only without its subtitle (full title {full:.2f})")
        elif full < a.min_title_sim and sim >= a.conflict_title_sim:
            note("minor", f"title drift: similarity {sim:.2f} < {a.min_title_sim}")
        elif full < a.min_title_sim:
            note("conflict", f"title similarity {sim:.2f} < {a.conflict_title_sim}: the identifier is another work?")
    first = (ref.authors or [""])[0]
    if first and rec.authors and not fam_match(first, rec.authors[0]):
        if any(fam_match(first, x) for x in rec.authors[1:]):
            note("minor", f"'{first}' is an author but not the first ({rec.authors[0]})")
        else:
            note("conflict", f"first author '{first}' not among the record's authors ({', '.join(rec.authors[:3])})")
    gap = min((abs(ref.year - y) for y in rec.years), default=0) if ref.year else 0
    if gap:  # a year matching the issued, print or online date is no drift
        titled = bool(ref.title and rec.titles)
        note("conflict" if gap > a.year_tolerance and not titled else "minor",
             f"year {ref.year} vs record {'/'.join(map(str, sorted(rec.years)))}")
    if ref.venue and rec.venues and max(venue_sim(ref.venue, v) for v in rec.venues) < a.min_venue_sim:
        note("minor", f"venue '{ref.venue}' vs record '{rec.venues[0]}'")
    compared = any((ref.title and rec.titles, ref.authors and rec.authors, ref.year and rec.years,
                    ref.venue and rec.venues))
    if ref.context and not compared and not a.no_context:  # --text/--dois: does the line name an author or title?
        toks, title_toks = set(words(ref.context, False)), words(clean_title((rec.titles or [""])[0]))
        named = [x for x in rec.authors if x and set(words(x, False)) <= toks]
        if len([t for t in toks if len(t) >= 3 and not t.isdigit()]) >= 4 and (rec.authors or title_toks):
            compared = True
            if named or (title_toks and sum(t in toks for t in title_toks) / len(title_toks) >= 0.6):
                notes.append(f"the line names the record's {'author ' + named[0] if named else 'title'}")
            elif rec.authors:
                note("conflict", f"the line names neither an author ({rec.authors[0]}) nor the title of the record")
    if not compared:
        notes.append("identity not compared: no metadata supplied (existence and currency only)")
    return (R_CONFLICT if "conflict" in level else R_MINOR if "minor" in level else R_OK), sim, notes

# ----------------------------------------------------------------------------- title search (no identifier)
@dataclass
class Found:
    """Outcome of a title search: the accepted candidate (if any), how many indexes answered, the best near miss."""
    rec: Rec | None = None
    index: str = ""
    sim: float = 0.0
    answered: int = 0
    near: tuple | None = None  # (similarity, record, index, reasons) of the best rejected candidate at the floor
    failures: list = field(default_factory=list)  # "index: reason" for each index that did not answer

def unsearchable(ref: Ref, a) -> str:
    """Why a reference is not searched by title ('' when it is)."""
    if a.no_search:
        return "title search is off (--no-search)"
    if len(words(ref.title)) < 2:
        return "no usable title to search"
    if ref.etype and ref.etype.lower() not in SEARCHABLE:
        return f"entry type '{ref.etype}' is not indexed by CrossRef or OpenAlex; check it at the issuing body"
    return ""

def mismatches(ref: Ref, rec: Rec, sim: float, a) -> list[str]:
    """Why a search candidate is not the cited work ([] = accept): title, first author and year must all agree."""
    out = []
    if sim < a.min_title_sim:
        out.append(f"title similarity {sim:.2f}")
    if ref.authors and rec.authors and not fam_match(ref.authors[0], rec.authors[0]):
        out.append(f"first author {rec.authors[0]}")
    if ref.year and rec.years and min(abs(ref.year - y) for y in rec.years) > a.year_tolerance:
        out.append(f"year {'/'.join(map(str, sorted(rec.years)))}")
    if not (ref.authors and rec.authors) and not (ref.year and rec.years):
        out.append("no author or year to compare")
    return out

def search(ref: Ref, row: dict, net: Net, a) -> Found:
    """CrossRef query.bibliographic, then OpenAlex search as the fallback (one shared bucket, <= 1 search/s)."""
    q = " ".join(words(ref.title, False))
    hint = " ".join(x for x in ((ref.authors or [""])[0], str(ref.year or "")) if x)
    urls = (("crossref", "https://api.crossref.org/works?rows=5&select=DOI,title,author,issued,container-title,type"
                         "&query.bibliographic=" + urllib.parse.quote(f"{q} {hint}".strip())),
            ("openalex", "https://api.openalex.org/works?per_page=5&select=id,doi,title,publication_year,authorships,"
                         "primary_location,type&search=" + urllib.parse.quote(q)))
    found = Found()
    for index, url in urls:
        if index == "openalex" and a.no_openalex:
            found.failures.append("openalex: skipped (--no-openalex)")
            continue
        r = net.get(url, f"{index}.search", row, search=True)
        if not (r.ok and isinstance(r.body, dict)):
            found.failures.append(f"{index}: {r.why}")
            continue
        found.answered += 1
        items = (r.body.get("message") or {}).get("items") if index == "crossref" else r.body.get("results")
        for item in (i for i in items or [] if isinstance(i, dict)):
            try:
                rec = parse_crossref({"message": item}, "") if index == "crossref" else parse_openalex(item)
            except (AttributeError, TypeError, KeyError, IndexError, ValueError):
                continue
            if not rec.titles:
                continue
            sim = max(title_sims(ref.title, rec.titles))
            reasons = mismatches(ref, rec, sim, a)
            if not reasons:
                found.rec, found.index, found.sim = rec, index, sim
                return found
            if sim >= a.candidate_title_sim and (found.near is None or sim > found.near[0]):
                found.near = (sim, rec, index, reasons)
    return found

def locate(ref: Ref, row: dict, net: Net, a) -> dict:
    """Grade a reference that carries no DOI or arXiv id by what the title search finds."""
    if why := unsearchable(ref, a):
        return graded(row, R_UNVER, f"no DOI or arXiv id; {why}")
    found = search(ref, row, net, a)
    if found.rec is not None:
        where = f"title search ({found.index}, similarity {found.sim:.2f})"
        if found.rec.doi:
            row["notes"].append(f"no identifier supplied; {where} located {found.rec.doi}")
            return check_doi(found.rec.doi, ref, row, net, a)
        return graded(row, R_UNVER, f"{where} located {found.rec.link or found.rec.titles[0]} but it has no DOI, "
                                    "so there is no registry record to verify it against")
    if found.near is not None:
        sim, rec, index, reasons = found.near
        return graded(row, R_UNVER, f"closest candidate {rec.doi or rec.link} ({index}, title {sim:.2f}) was not "
                                    f"accepted: {'; '.join(reasons)}; verify by hand")
    if found.answered < 2:
        return graded(row, R_UNVER, f"title search incomplete ({'; '.join(found.failures)})")
    return graded(row, R_NOTLOC, f"not located in CrossRef or OpenAlex; needs second reader (no candidate at title "
                                 f"similarity {a.candidate_title_sim} or above; no domain index was searched)")

def settle(row: dict) -> dict:
    """Flag C text, verdict and second-reader flag from the R grade and the currency flags."""
    flags, complete, date, g = row.pop("_flags"), row.pop("_complete"), row.pop("_date"), row["r_grade"]
    row["c_flag"] = ";".join(f for f in C_ORDER if f in flags) or (f"NONE-FOUND@{date}" if complete else "NOT-CHECKED")
    if g == R_UNVER:
        verdict = UNVERIFIED
    elif g in (R_CONFLICT, R_NOTLOC):
        verdict = WOUNDED
    elif flags & FATAL:
        verdict = KILLED
    elif g == R_MINOR or flags & ADVERSE:
        verdict = WOUNDED
    else:
        verdict = SURVIVES if complete else UNVERIFIED
    row.update(verdict=verdict, needs_second_reader="yes" if verdict == KILLED or g in (R_CONFLICT, R_NOTLOC) else "",
               endpoints=" ".join(row["endpoints"]), notes="; ".join(dict.fromkeys(row["notes"])))
    return row

# ----------------------------------------------------------------------------- output and CLI
def to_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for r in rows:  # registry text is untrusted: a leading = + - @ must not become a spreadsheet formula
        writer.writerow({k: "'" + str(r[k]) if str(r[k])[:1] in ("=", "+", "-", "@", "\t", "\r") else r[k]
                         for k in COLUMNS})
    return buf.getvalue()

def build_parser():
    p = base_parser(__doc__)
    p.epilog = textwrap.fill(SCOPE, 110, break_on_hyphens=False)  # keep R-NOT-LOCATED and --flag-names whole
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--dois", metavar="FILE", help="one DOI/arXiv/ssrn:/nber: id per line; later words are context")
    src.add_argument("--bib", metavar="FILE", help="BibTeX (doi, eprint, url, title, author, year, journal)")
    src.add_argument("--csl", metavar="FILE", help="CSL-JSON array (DOI, URL, title, author, issued, container-title)")
    src.add_argument("--text", metavar="FILE", help="prose/markdown: identifiers, and reference lines without one")
    p.add_argument("--mailto", metavar="EMAIL", help="contact for CrossRef/DataCite polite pools; never auto-filled")
    p.add_argument("--offline", action="store_true", help="syntax only: nothing is looked up (all UNVERIFIED-HERE)")
    p.add_argument("--no-search", action="store_true", help="no title search (unidentified entries stay unverified)")
    p.add_argument("--no-context", action="store_true", help="skip the same-line identity check for --text/--dois")
    p.add_argument("--no-openalex", action="store_true", help="CrossRef/DataCite only: no OpenAlex cross-check or "
                   "search fallback (R-NOT-LOCATED then cannot be concluded)")
    p.add_argument("--cache", metavar="DIR", help="response cache to read and add to (default: inside the run folder)")
    p.add_argument("--no-cache-read", action="store_true", help="fetch fresh answers; still add them to the cache")
    p.add_argument("--cache-max-age", type=float, default=7.0, metavar="DAYS", help="ignore older cached answers (7)")
    p.add_argument("--timeout", type=float, default=20.0, help="seconds per request (default 20)")
    p.add_argument("--max-rps", type=float, default=4.0, help="requests/s per host (4; DataCite <= 1.5, searches <= 1)")
    p.add_argument("--retries", type=int, default=3, help="retries after a 429, 5xx, timeout or unreadable body (3)")
    p.add_argument("--backoff", type=float, default=1.0, help="first back-off in seconds, doubled per retry (1.0)")
    p.add_argument("--max-backoff", type=float, default=60.0, help="longest wait; a longer Retry-After stops (60)")
    p.add_argument("--min-title-sim", type=float, default=0.90, help="title similarity for a match (default 0.90)")
    p.add_argument("--conflict-title-sim", type=float, default=0.80, help="below this: another work (default 0.80)")
    p.add_argument("--candidate-title-sim", type=float, default=0.75, help="search candidate floor (default 0.75)")
    p.add_argument("--year-tolerance", type=int, default=1, help="year gap still treated as drift (default 1)")
    p.add_argument("--min-venue-sim", type=float, default=0.60, help="venue similarity for a match (default 0.60)")
    return p

def validate(a) -> None:
    if not (0 <= a.candidate_title_sim <= a.conflict_title_sim <= a.min_title_sim <= 1 and 0 <= a.min_venue_sim <= 1
            and a.year_tolerance >= 0):
        raise UsageError("need 0 <= --candidate-title-sim <= --conflict-title-sim <= --min-title-sim <= 1, "
                         "--min-venue-sim in [0, 1] and --year-tolerance >= 0")
    if not 0 < a.max_rps <= (10 if a.mailto else 5):
        raise UsageError(f"--max-rps must be in (0, {10 if a.mailto else 5}] (the CrossRef pool limit)")
    if a.timeout <= 0 or not 0 <= a.retries <= 10 or min(a.backoff, a.max_backoff, a.cache_max_age) < 0:
        raise UsageError("need --timeout > 0, --retries 0-10 and non-negative --backoff/--max-backoff/--cache-max-age")
    if a.mailto is not None and not re.fullmatch(r"[^@\s]+@[^@\s]+\.\w+", a.mailto):
        raise UsageError("--mailto must be an email address")
    if a.cache and pathlib.Path(a.cache).expanduser().exists() and not pathlib.Path(a.cache).expanduser().is_dir():
        raise UsageError("--cache must be a directory")

def main(args, report: Report, run_dir: pathlib.Path, run_id: str) -> None:
    report.argv = ["<redacted>" if "@" in str(x) else str(x) for x in report.argv]  # --mailto never reaches a report
    validate(args)
    kind = next(k for k in ("dois", "bib", "csl", "text") if getattr(args, k))
    src = require_file(getattr(args, kind), f"--{kind}")
    report.add_input(src)
    text = src.read_text(encoding="utf-8-sig", errors="replace")  # undecodable bytes become U+FFFD, never a crash
    refs = {"dois": parse_dois, "bib": parse_bib, "csl": parse_csl, "text": parse_text}[kind](text)
    if not refs:
        raise UsageError(f"no references found in --{kind} {src.name}")
    net, rows = Net(args, run_dir), []
    criterion = (f"handle + RA record; title >= {args.min_title_sim} (drift >= {args.conflict_title_sim}); first "
                 f"author; year +/-{args.year_tolerance}; venue >= {args.min_venue_sim}; no notices; same for searches")
    for i, ref in enumerate(refs, 1):
        row = settle(check(ref, net, args))
        rows.append(row)
        shown = ref.rid if not ref.doi or ref.doi == ref.rid.lower() else f"{ref.rid} -> {ref.doi}"
        detail = "; ".join(x for x in ("needs second reader" if row["needs_second_reader"] else "", row["r_grade"],
                                       f"C={row['c_flag']}", row["notes"]) if x)
        report.add(Check(id=f"REF-{i:03d}", title=f"{shown} ({ref.source})", verdict=row["verdict"],
                         criterion=criterion, value=f"{row['r_grade']} / {row['c_flag']}", detail=detail))
        if i % 10 == 0 or i == len(refs):
            emit("stage", "running", f"checked {i}/{len(refs)} references", run_id=run_id,
                 source=f"quant-model-evaluation/{SCRIPT}", current=i, total=len(refs))
    write_once(run_dir / "references.csv", to_csv(rows))
    report.section("Scope and limits", SCOPE)
    queue = [f"- {r['id']} ({r['source_line']}): {r['r_grade']} / {r['c_flag']}: {r['notes']}"
             for r in rows if r["needs_second_reader"]]
    report.section("Second-reader queue", "\n".join(queue) or "Nothing needs a second reader.")
    agent = UA_BASE + (" mailto:<redacted>" if args.mailto else "")
    report.data.update({"input_format": kind, "references": rows, "requests": net.log, "offline": args.offline,
                        "search": not args.no_search, "openalex": not args.no_openalex, "cache_read": not
                        args.no_cache_read, "dependencies": "python standard library only", "user_agent": agent,
                        "cache_dir": _redact_home(str(net.cache)), "thresholds": {k: getattr(args, k) for k in (
                            "min_title_sim", "conflict_title_sim", "candidate_title_sim", "year_tolerance",
                            "min_venue_sim", "max_rps", "retries", "backoff", "max_backoff", "timeout")}})

if __name__ == "__main__":
    sys.exit(run_main(SCRIPT, main, build_parser()))
