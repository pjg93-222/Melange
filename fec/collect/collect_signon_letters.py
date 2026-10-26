# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))));from paths import ROOT as MB_ROOT
"""SIGN-ON LETTER COLLECTOR (brain D-263, lane L). Finds member sign-on letters on official .gov sites, reads the
exact signatory list out of the letter's own PDF, and STAGES it. It never writes manual_bill_evidence.csv: the
promoter (legislation/promote_staged_letters.py) owns that, and only after Gate C (classification) as well.

Gate E (evidence, mechanical): the PDF has a text layer and a signature block after its last closing phrase; every
name-shaped line in the block is a roster member (fail-closed members.member_identity.Resolver) or carries its own
office line ("Member of Congress", "United States Senator", ...), so nothing is left unaccounted; a stated signer
count in the release (if any) reconciles; the document is on an official host. Everything else is NOT_EXACT:<reason>
and stays visible in staging.

Legs:   --committee  walk House Financial Services (majority + minority) and Senate Banking release listings
        --from-press scan the newest press_refresh_*/press_delta_fulltext.csv for CU-domain letter announcements
        --backfill   one-time, resumable committee crawl back to the 117th Congress (cursor in the staging dir)
Politeness: honest UA, robots.txt once per host per run, 2 s per-host spacing, 300 requests per run, 20 MB per PDF,
public-address-only fetches (the SSRF guard below is a verbatim copy of fetch_press_text.py's, because that script
runs at import and cannot be imported; a test pins the two together).
A designed stop (host refused, cap hit, unreadable PDF) is PARTIAL and exits 0; only an unusable input is FAIL.
Usage: python fec/collect/collect_signon_letters.py [--committee] [--from-press] [--backfill] [--max-requests N]
                                                    [--root DIR] [--letters-dir DIR]"""
import argparse, collections, csv, datetime as dt, hashlib, html as _html, io, json, os, re, socket
import sys, tempfile, time, unicodedata, urllib.error, urllib.parse, urllib.request, urllib.robotparser
from collect.public_fetch_guard import require_public, PublicOnlyRedirects

UA = 'MelangeSystemsResearchCollector/1.0 (public-records research)'
SPACING, REQUEST_CAP, PDF_CAP, HTML_CAP, TIMEOUT = 2.0, 300, 20_000_000, 8_000_000, 25
LETTERS_RELATIVE = os.path.join('data', 'legislation', 'letters')
# Bump RULES_VERSION whenever extraction, subject or Gate E rules change: staging outlives code, and the promoter holds
# any EXACT record written under other rules (v1 = the first live dry run, which mis-filed a CRA letter under CDFI Fund).
RULES_VERSION = 'signature-block-v4'   # v3: body kept to BODY_CAP (adverse-cue screen); v4: per-page text layer, review rulings of 2026-10-20
BODY_CAP = 60000
NOPDF_RETRY_DAYS = 7
EXTRACTION = 'pypdf-%s:' + RULES_VERSION
SOURCE_KINDS = ('member_press', 'committee_site', 'regs_gov')
OFFICIAL_SUFFIXES = ('.house.gov', '.senate.gov')
OFFICIAL_HOSTS = ('downloads.regulations.gov',)
BACKFILL_FLOOR = dt.date(2021, 1, 3)          # first day of the 117th Congress
# Senate Banking (banking.senate.gov, majority + minority newsrooms) is deliberately NOT listed: it answered 410 to every path,
# robots.txt included, on 2026-10-20, so it would show PARTIAL every day, and its listing URLs were never verified. Re-add it
# here once the host serves again and its listing URLs have been fetched and checked (parse_listing reads <article> blocks with
# <time datetime>; confirm the Senate markup does too). Add listings here, not elsewhere.
COMMITTEE_LISTINGS = (
    ('fs_minority', 'https://democrats-financialservices.house.gov/news/documentquery.aspx?DocumentTypeID=2636', True),
    ('fs_majority', 'https://financialservices.house.gov/news/documentquery.aspx?DocumentTypeID=2092', True),
)   # (key, first listing page, paginates with &Page=N)

LETTER_RE = re.compile(r'\b(letters?|wrote|writes?|urg(?:e|es|ed|ing)|demand(?:s|ed|ing)?|call(?:s|ed|ing)? (?:on|upon))\b', re.I)
CU_RE = re.compile(r'credit unions?\b|\bncua\b|\bcdfi|community development financial|\bcfpb\b|consumer financial protection|'
                   r'interchange|swipe fee|share insurance|field of membership|member business lending|\btcpa\b', re.I)
# A subject must open the letter (first 400 chars incl. the release title) or recur densely (3+ hits, 1.5+ per 1000 chars):
# measured 2026-10-20, the real CDFI Fund letter has 32 hits in 4.8k chars (6.7/1k); a 15k-char CRA letter mentions CDFIs 3 times (0.2/1k).
PROMINENT, DENSITY = 400, 1.5
# (category, cue, also required) -> the subject categories a letter's own text names; CATCODES builds its evidence id
CATEGORY_CUES = (
    ('CDFI Fund', re.compile(r'\bcdfi|community development financial', re.I), None),
    ('CU Tax Status', re.compile(r'tax[- ]exempt|tax exemption|tax status', re.I), re.compile(r'credit union', re.I)),
    ('CFPB', re.compile(r'\bcfpb\b|consumer financial protection bureau', re.I), None),
    ('Credit Card Mandates', re.compile(r'credit card competition|late[- ]fee', re.I), None),
    ('Interchange', re.compile(r'interchange|swipe fee', re.I), None),
    ('NCUA Budget & Insurance', re.compile(r'\bncua\b|share insurance', re.I), None),
    ('Field of Membership', re.compile(r'field of membership', re.I), None),
    ('Member Business Lending', re.compile(r'member business lending', re.I), None),
    ('TCPA', re.compile(r'\btcpa\b|telephone consumer protection', re.I), None),
)
CATCODES = {'CDFI Fund': 'CDFI', 'CU Tax Status': 'CUTAX', 'CFPB': 'CFPB', 'Credit Card Mandates': 'CCM', 'Interchange': 'INTCH',
            'NCUA Budget & Insurance': 'NCUA', 'Field of Membership': 'FOM', 'Member Business Lending': 'MBL', 'TCPA': 'TCPA'}

# The public-address guard is shared with fetch_press_text.py (one copy; see collect/public_fetch_guard.py).


# ---- pure extraction --------------------------------------------------------------------------------

def official_host(url):
    """The Gate E host allowlist: official congressional hosts and the regulations.gov attachment host, https/http only."""
    p = urllib.parse.urlparse(str(url or ''))
    host = (p.hostname or '').lower()
    return p.scheme in ('http', 'https') and (host in OFFICIAL_HOSTS or host.endswith(OFFICIAL_SUFFIXES))


def canonical_url(url):
    """The page identity of a URL: no fragment (#bioguide anchors in the press feed) and no tracking parameters (utm_*, fbclid)."""
    p = urllib.parse.urlsplit(str(url or '').strip())
    query = [(k, v) for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')]
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, urllib.parse.urlencode(query), ''))


def congress_of(d):
    year = d.year if d >= dt.date(d.year, 1, 3) else d.year - 1
    return (year - 1789) // 2 + 1


def _prominent(pattern, text):
    hits = len(pattern.findall(text))
    return bool(pattern.search(text[:PROMINENT])) or (hits >= 3 and 1000.0 * hits / max(len(text), 1) >= DENSITY)


def cu_relevant(text):
    return _prominent(CU_RE, text or '')


def subject_categories(title, body):
    """The categories a letter is ABOUT (cue prominent in title+opening, or recurring), in CATEGORY_CUES order."""
    text = title + ' ' + body
    return [c for c, cue, need in CATEGORY_CUES if _prominent(cue, text) and (need is None or need.search(text))]


def _words(text):
    return re.sub(r'\s+', ' ', _html.unescape(re.sub(r'<[^>]+>', ' ', text or ''))).strip()


def parse_stated_count(text):
    """{'n': N, 'min': bool} from release wording such as 'led 86 of their colleagues' or 'signed by over 110 Democrats';
    only an exact or lower-bound count counts (nearly/about/roughly is ignored). None when the release gives none."""
    who = r'(?:\w+\s+){0,2}?(?:colleagues|members|lawmakers|senators|representatives|democrats|republicans)'
    for pat in (r'\bled\s+(over|more than|at least)?\s*(\d{1,3})\s+(?:of\s+(?:their|his|her)\s+)?' + who,
                r'\b(?:signed|joined|co-?signed|backed|supported)\s+by\s+(over|more than|at least)?\s*(\d{1,3})\s+' + who,
                r'\b(over|more than|at least)?\s*(\d{1,3})\s+' + who + r'\s+(?:signed|joined|co-?signed)\b'):
        m = re.search(pat, _words(text), re.I)
        if m:
            return {'n': int(m.group(2)), 'min': bool(m.group(1))}
    return None


def parse_release(html, base_url):
    """Title, date, plain text, letter PDF links (letter-ish anchors first) and stated signer count of a release page."""
    if isinstance(html, bytes):
        html = html.decode('utf-8', 'replace')
    title = re.search(r'<title[^>]*>(.*?)</title>', html, re.S | re.I)
    when = (re.search(r'<time[^>]+datetime="(\d{4}-\d{2}-\d{2})', html) or
            re.search(r'article:published_time"?\s+content="(\d{4}-\d{2}-\d{2})', html) or
            re.search(r'content="(\d{4}-\d{2}-\d{2})[^"]*"\s+property="article:published_time', html))
    body = re.sub(r'<(script|style|nav|footer|header)\b.*?</\1>', ' ', html, flags=re.S | re.I)
    links = []
    for href, label in re.findall(r'<a\b[^>]*?href="([^"]+)"[^>]*>(.*?)</a>', body, re.S | re.I):
        url = urllib.parse.urljoin(base_url, _html.unescape(href))
        if re.search(r'\.pdf(?:$|[?#])', url, re.I) and url not in [u for _, u in links]:
            links.append((0 if re.search(r'letter|full copy|here', _words(label), re.I) else 1, url))
    text = _words(body)
    return {'title': _words(title.group(1)) if title else '', 'published': when.group(1) if when else None, 'text': text,
            'pdf_links': [u for _, u in sorted(links, key=lambda p: p[0])], 'stated_count': parse_stated_count(text)}


def parse_listing(html, base_url):
    """[{url, title, date, snippet}] from a committee/Senate release listing (every <article> block)."""
    if isinstance(html, bytes):
        html = html.decode('utf-8', 'replace')
    items = []
    for block in re.findall(r'<article\b.*?</article>', html, re.S | re.I):
        head = re.search(r'<h[1-4][^>]*>.*?<a\b[^>]*?href="([^"]+)"[^>]*>(.*?)</a>', block, re.S | re.I) or \
            re.search(r'<a\b[^>]*?href="([^"]+)"[^>]*>(.*?)</a>', block, re.S | re.I)
        if not head:
            continue
        when = re.search(r'<time[^>]+datetime="(\d{4}-\d{2}-\d{2})', block)
        snippet = re.search(r'newsbody[^>]*>(.*?)</div>', block, re.S) or re.search(r'<p\b.*?</p>', block, re.S)
        items.append({'url': urllib.parse.urljoin(base_url, _html.unescape(head.group(1))), 'title': _words(head.group(2)),
                      'date': when.group(1) if when else None, 'snippet': _words(snippet.group(0) if snippet else '')})
    return items


def extract_pdf(raw):
    """(text, pages, method, page_texts) or (None, pages, reason, []). Image-only PDFs are not OCR'd: no text layer -> 'no_text_layer'."""
    import logging, pypdf
    logging.getLogger('pypdf').setLevel(logging.ERROR)    # stripped-image XObjects log a warning per page
    try:
        reader = pypdf.PdfReader(io.BytesIO(raw))
        page_texts = [(page.extract_text() or '') for page in reader.pages]
    except Exception:
        return None, 0, 'pdf_unreadable', []
    text = '\n'.join(page_texts)
    if len(text.strip()) < 200:
        return None, len(reader.pages), 'no_text_layer', []
    return text, len(reader.pages), EXTRACTION % pypdf.__version__, page_texts


MIN_PAGE_CHARS = 40    # a page with less text than one signer's name and office is a scan (or a bare page number)


def blank_pages_from_closing(page_texts, text):
    """1-based pages, from the page holding the LAST closing phrase to the end, whose text layer is empty: signatures may be images there."""
    closings = list(CLOSING.finditer(text))
    if not closings:
        return []
    start, first = 0, 0
    for index, page in enumerate(page_texts):
        if start <= closings[-1].start() <= start + len(page):
            first = index
            break
        start += len(page) + 1
    return [index + 1 for index in range(first, len(page_texts)) if len(page_texts[index].strip()) < MIN_PAGE_CHARS]


MONTHS = '|'.join(['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
                   'November', 'December'])
CLOSING = re.compile(r'(?im)^[ \t]*(?:Sincerely|Respectfully(?: yours| submitted)?|Very respectfully|Yours truly|'
                     r'Thank you for your (?:attention|consideration)[^\n]*)[,.]?[ \t]*$')
OFFICE_RE = re.compile(r'^(?:Member of Congress|(?:United States|U\.?\s?S\.?) Senator|Senator|Delegate|Resident Commissioner|'
                       r'Ranking Member\b.*|Chair(?:man|woman|person)?\b.*|Vice Chair\b.*)$', re.I)
NONNAME = {'committee', 'subcommittee', 'caucus', 'congress', 'senate', 'house', 'member', 'chair', 'chairman', 'chairwoman',
           'ranking', 'page', 'representatives', 'services', 'task', 'force', 'cc', 'enclosure', 'united', 'states',
           # wrapped subcommittee names ("... Subcommittee on Capital / Markets"): never part of a member's name
           'markets', 'capital', 'housing', 'insurance', 'financial', 'oversight', 'investigations', 'institutions', 'development',
           'inclusion', 'digital', 'assets', 'monetary', 'policy', 'opportunity', 'community', 'consumer', 'protection', 'banking',
           'urban', 'affairs', 'finance'}
SALUTATION = re.compile(r'(?im)^[ \t]*Dear\b')
HONORIFIC = re.compile(r'^(?:The Honorable|Honorable|Hon\.|Senator|Sen\.|Representative|Rep\.|Congressman|Congresswoman|'
                       r'Member of Congress|Dr\.)\s+', re.I)
TRAIL = re.compile(r',?\s*(?:Ph\.?D\.?|M\.?D\.?|D\.?D\.?S\.?|J\.?D\.?|Esq\.?|Member of Congress|United States Senator|'
                   r'U\.S\. Senator|Senator|M\.C\.)\s*$', re.I)


def clean_query(line):
    q = re.sub(r'["“”][^"“”]*["“”]', ' ', line)
    for _ in range(2):
        q = TRAIL.sub('', HONORIFIC.sub('', q.strip())).strip(' ,')
    return re.sub(r'\s+', ' ', q)


def _person_shaped(line):
    toks = line.split()
    return (2 <= len(toks) <= 5 and all(re.match(r"^[A-Z][\w.'\-]*,?$", t) for t in toks)
            and not {re.sub(r'\W', '', t).lower() for t in toks} & NONNAME)


def parse_signature_block(text, resolver, bio):
    """Signatories after the LAST closing phrase. Every name-shaped line is roster (Resolver), off_roster (its own office
    line follows) or unaccounted; titles, page markers, footnotes with digits and wrapped committee lines are ignored."""
    closings = list(CLOSING.finditer(text))
    if not closings:
        return {'closing_found': False, 'signatories': [], 'unaccounted_lines': []}
    # pypdf >= 6.21 splits a kerned capital from its word ("V argas"); a lone capital before a lowercase word is not an initial unless that word is a name particle ("A de la Cruz")
    lines = [re.sub(r'\b([A-Z]) (?=[a-z])(?!(?:de|del|della|der|di|da|das|do|dos|du|la|le|van|von|y|e)\b)', r'\1', re.sub(r'\s+', ' ', l)).strip() for l in text[closings[-1].end():].split('\n')]
    lines = [l for l in lines if l]
    stop = next((i for i, l in enumerate(lines) if re.match(r'(?i)(cc\b|copies to|enclosures?\b)', l)), len(lines))
    lines = lines[:stop]   # a cc: list is a distribution list, not signatures
    out, unaccounted, seen = [], [], set()
    for i, line in enumerate(lines):
        if len(line) > 60 or re.search(r'\d', line) or not line[0].isupper() or OFFICE_RE.match(line):
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ''
        office = nxt if OFFICE_RE.match(nxt) else None
        query = clean_query(line)
        member = resolver.resolve(query) if len(query.split()) >= 2 else None
        if member:
            if bio.get(member) not in seen:
                seen.add(bio.get(member))
                out.append({'line': line, 'query': query, 'member': member, 'bioguide': bio.get(member), 'status': 'roster',
                            'office': office})
        elif office and _person_shaped(query):
            out.append({'line': line, 'query': query, 'member': None, 'bioguide': None, 'status': 'off_roster', 'office': office})
        elif not ({w.lower().strip('.,') for w in line.split()} & NONNAME):
            unaccounted.append(line)
    return {'closing_found': True, 'signatories': out, 'unaccounted_lines': unaccounted, 'block': text[closings[-1].end():]}


def parse_letter_head(text):
    """(date or None, recipients, body) of a letter's text: the first 'Month D, YYYY' in the head, the addressee block
    (address lines dropped), and the body between 'Dear ...:' and the last closing phrase."""
    m = re.search(r'(%s)\s+(\d{1,2}),\s+(\d{4})' % MONTHS, text[:800])
    when = dt.datetime.strptime('%s %s %s' % m.groups(), '%B %d %Y').date() if m else None
    dear = re.search(r'(?im)^[ \t]*Dear\b[^\n]*$', text)
    head = text[m.end():dear.start()] if m and dear and dear.start() > m.end() else ''
    chunks = []
    for line in (re.sub(r'\s+', ' ', l).strip() for l in head.split('\n')):
        if not line or re.search(r'\d', line):
            continue
        if not chunks or re.match(r'(The )?Honorable\b', line):
            chunks.append([line])
        else:
            chunks[-1].append(line)
    closing = list(CLOSING.finditer(text))
    body = text[dear.end():closing[-1].start()] if dear and closing else text
    return when, [', '.join(c) for c in chunks], re.sub(r'\s+', ' ', body).strip()


def find_leads(text, signatories):
    """Bioguides of signers named before a lead verb ('X and Y led 86 colleagues') or after 'led by' ('Z joined a letter led by X and Y')
    in the release; more than 4 is no lead."""
    for sentence in re.split(r'(?<=[.!?])\s+', text or ''):
        by = re.search(r'\b(?:led|lead|co-led|spearheaded|authored|penned|written|organized|initiated)\s+by\b', sentence, re.I)
        verb = by or re.search(r'\b(led|leads|lead|leading|co-led|spearheaded|authored|penned|sent|wrote)\b', sentence, re.I)
        if not verb:
            continue
        head, found = (sentence[by.end():] if by else sentence[:verb.start()]), []
        roster = [s for s in signatories if s['bioguide']]
        for s in roster:
            first, last = s['member'].split()[0], s['member'].split()[-1]
            if re.search(r'\b%s\b' % re.escape(last), head) and (re.search(r'\b%s\b' % re.escape(first), head) or
                                                                 sum(1 for r in roster if r['member'].split()[-1] == last) == 1):
                found.append(s['bioguide'])
        if found:
            return found if len(found) <= 4 else []
    return []


def _ascii_upper(text):
    return re.sub(r'[^A-Z]', '', unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().upper())


def analyze_letter(raw, *, document_url, source_url, source_kind, release, resolver, bio, now):
    """The staging record of one letter PDF (Gate E applied; de-duplication and id collisions are stage_record's job)."""
    digest = hashlib.sha256(raw).hexdigest()
    text, pages, method, page_texts = extract_pdf(raw)
    rec = {'letter_id': None, 'status': 'STAGED', 'source_kind': source_kind, 'source_url': source_url, 'source_urls': [source_url],
           'document_url': document_url, 'retrieved_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'sha256': digest,
           'page_sha256': release.get('sha256') if release else None, 'extraction_method': method if text else None,
           'pages': pages, 'congress': None, 'letter_date': None, 'recipients': [], 'subject': '', 'body': '',
           'title': release['title'] if release else '', 'stated_count': release['stated_count'] if release else None,
           'closing_found': False, 'blank_pages': [], 'signatories': [], 'unaccounted_lines': [], 'leads': [], 'subject_categories': [],
           'classification': None, 'dedupe': {'matched_existing': None, 'method': None, 'jaccard': None}}
    if text is None:
        rec['status'] = 'NOT_EXACT:' + method
        rec['letter_id'] = 'UNPARSED-' + digest[:12]
        return rec
    when, recipients, body = parse_letter_head(text)
    if when is None and release and release.get('published'):
        when = dt.date.fromisoformat(release['published'])
    block = parse_signature_block(text, resolver, bio)
    rec.update(letter_date=when.isoformat() if when else None, congress=congress_of(when) if when else None,
               recipients=recipients, subject=body[:300], body=body[:BODY_CAP], closing_found=block['closing_found'], blank_pages=blank_pages_from_closing(page_texts, text),
               signatories=block['signatories'], unaccounted_lines=block['unaccounted_lines'])
    names = rec['signatories']
    rec['leads'] = find_leads(release['text'] if release else '', names) or [
        s['bioguide'] for s in names if s['bioguide'] and re.match(r'(Ranking Member|Chair)', s.get('office') or '', re.I)][:2]
    for s in names:
        s['role'] = 'sponsor' if s['bioguide'] and s['bioguide'] in rec['leads'] else 'original-cosponsor'
    haystack = ' '.join([rec['title'], body])
    rec['subject_categories'] = subject_categories(rec['title'], body)
    rec['cu_relevant'] = cu_relevant(haystack)
    rec['is_letter'] = bool(SALUTATION.search(text))     # a bill text or resolution linked from a release has no salutation
    code = CATCODES.get(rec['subject_categories'][0], 'UNCAT') if rec['subject_categories'] else 'UNCAT'
    lead_names = [s['member'] for s in names if s['bioguide'] in rec['leads']][:2] or [names[0]['query']] if names else []
    rec['letter_id'] = 'LTR-%s-%s-%s' % (rec['congress'], code, '+'.join(_ascii_upper(n.split()[-1]) for n in lead_names) or 'UNKNOWN')
    rec['status'] = gate_e(rec)
    return rec


def gate_e(rec):
    """EXACT or NOT_EXACT:<reason>. Mechanical evidence only: classification (Gate C) is the promoter's."""
    if rec['source_kind'] not in SOURCE_KINDS:
        return 'NOT_EXACT:source_kind'
    if not official_host(rec['document_url']):
        return 'NOT_EXACT:host_not_official'
    if not rec['closing_found']:
        return 'NOT_EXACT:no_signature_block'
    if rec.get('blank_pages'):
        return 'NOT_EXACT:page_without_text_layer'
    if not rec['signatories']:
        return 'NOT_EXACT:no_signatories'
    if rec['unaccounted_lines']:
        return 'NOT_EXACT:unaccounted'
    if not any(s['status'] == 'roster' for s in rec['signatories']):
        return 'NOT_EXACT:no_roster_signatory'
    if not rec['letter_date']:
        return 'NOT_EXACT:no_date'
    stated, total = rec.get('stated_count'), len(rec['signatories'])
    if stated and not (total >= stated['n'] if stated['min'] else total in (stated['n'], stated['n'] + len(rec['leads']))):
        return 'NOT_EXACT:stated_count_mismatch'
    return 'EXACT'


# ---- politeness layer -------------------------------------------------------------------------------

CSV_COLUMNS = ('Member', 'Role', 'Bill', 'Title', 'Sponsor', 'Congress', 'Category', 'Direction', 'DecayWeight', 'LastAction',
               'DetailLink', 'Summary', 'Note')


class FetchRefused(Exception):
    """robots.txt, a non-public address or an unusable host: do not ask this host again this run."""


class FetchFailed(Exception):
    """One URL failed (HTTP error, timeout, oversize): counted as an error, retried on the next run."""


class CapReached(Exception):
    """The per-run request cap: a designed stop."""


_opener = urllib.request.build_opener(PublicOnlyRedirects)


def _urlopen(url, max_bytes):
    try:
        with _opener.open(urllib.request.Request(url, headers={'User-Agent': UA}), timeout=TIMEOUT) as resp:
            return resp.status, resp.read(max_bytes + 1)
    except urllib.error.HTTPError as e:
        return e.code, b''
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise FetchFailed(repr(e)[:80])


class Fetcher:
    """Honest UA, public addresses only, robots.txt once per host per run, per-host spacing, a hard request cap
    (robots.txt requests count). get() returns the body or raises FetchRefused / FetchFailed / CapReached."""

    def __init__(self, cap=REQUEST_CAP, spacing=SPACING, opener=_urlopen, sleep=time.sleep, clock=time.monotonic):
        self.cap, self.spacing, self.opener, self.sleep, self.clock = cap, spacing, opener, sleep, clock
        self.requests, self.robots, self.last, self.delay = [], {}, {}, {}

    def _raw(self, url, max_bytes):
        if len(self.requests) >= self.cap:
            raise CapReached()
        try:
            require_public(url)
        except ValueError as e:
            raise FetchRefused('non_public: %s' % e)
        host = urllib.parse.urlparse(url).hostname
        wait = self.delay.get(host, self.spacing) - (self.clock() - self.last.get(host, -1e9))
        if wait > 0:
            self.sleep(wait)
        self.last[host] = self.clock()
        self.requests.append(url)
        return self.opener(url, max_bytes)

    def _robots(self, url):
        p = urllib.parse.urlparse(url)
        base = '%s://%s' % (p.scheme, p.netloc)
        if base not in self.robots:
            rp = urllib.robotparser.RobotFileParser()
            try:
                status, body = self._raw(base + '/robots.txt', 1_000_000)
            except FetchFailed:
                rp = None
            else:
                if status in (401, 403):
                    rp.disallow_all = True
                elif 400 <= status < 500:
                    rp.allow_all = True      # no robots.txt (404/410): everything is allowed
                elif status == 200:
                    rp.parse(body.decode('utf-8', 'replace').splitlines())
                    self.delay[p.hostname] = max(self.spacing, float(rp.crawl_delay(UA) or 0))
                else:
                    rp = None
            self.robots[base] = rp
        return self.robots[base]

    def get(self, url, max_bytes=HTML_CAP):
        rp = self._robots(url)
        if rp is None:     # network error or 5xx on robots.txt: the host is down, not refusing us (and nothing is fetched blind)
            raise FetchFailed('robots_unavailable')
        if not rp.can_fetch(UA, url):
            raise FetchRefused('robots.txt')
        status, body = self._raw(url, max_bytes)
        if len(body) > max_bytes:
            raise FetchFailed('response too large')
        if status != 200:
            raise FetchFailed('HTTP %d' % status)
        return body


# ---- staging ------------------------------------------------------------------------------------------

def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _atomic_write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def load_roster(root):
    from members.member_identity import Resolver
    with open(os.path.join(root, 'data', 'engine', 'congestion.json'), encoding='utf-8') as handle:
        bio = {r['member']: r['bioguide'] for r in json.load(handle) if r.get('bioguide')}
    if not bio:
        raise ValueError('roster is empty')
    return Resolver(list(bio), bio), bio


def load_existing_letters(csv_path, bio):
    """The hand-ingested LTR- letters in manual_bill_evidence.csv (read only): id, congress, date and roster bioguides."""
    letters = {}
    if csv_path and os.path.exists(csv_path):
        with open(csv_path, encoding='utf-8-sig', newline='') as handle:
            for row in csv.DictReader(handle):
                bill = (row.get('Bill') or '').strip()
                if not bill.upper().startswith('LTR-'):
                    continue
                one = letters.setdefault(bill, {'id': bill, 'congress': int(float(row.get('Congress') or 0)), 'date': None, 'bios': set()})
                sent = re.search(r'Letter sent (\d{4}-\d{2}-\d{2})', row.get('LastAction') or '')
                if sent and not one['date']:
                    one['date'] = dt.date.fromisoformat(sent.group(1))
                if bio.get(row.get('Member')):
                    one['bios'].add(bio[row['Member']])
    return {'letters': list(letters.values()), 'ids': set(letters)}


def _bios(rec):
    return {s['bioguide'] for s in rec['signatories'] if s['bioguide']}


def _jaccard(a, b):
    return len(a & b) / len(a | b) if a | b else 0.0


def stage_record(staging, rec, refs):
    """Upsert one analyzed letter: same PDF bytes -> 'seen'; same letter re-posted with other bytes, or already hand-ingested,
    -> a DUPLICATE_OF / conflicts_existing record kept for provenance; id collisions get -2, -3. Returns 'new' or 'seen'."""
    for old in staging.values():
        if old['sha256'] == rec['sha256']:
            old['source_urls'] = sorted(set(old['source_urls']) | set(rec['source_urls']))
            return 'seen'
    if rec['status'] == 'EXACT':
        when, mine, best = dt.date.fromisoformat(rec['letter_date']), _bios(rec), None
        for old in staging.values():
            if old['status'] in ('EXACT', 'PROMOTED') and old['congress'] == rec['congress'] and \
                    abs((dt.date.fromisoformat(old['letter_date']) - when).days) <= 3 and _jaccard(mine, _bios(old)) >= 0.9:
                best = ('signer_overlap', old['letter_id'], _jaccard(mine, _bios(old)))
                rec['status'] = 'DUPLICATE_OF:' + old['letter_id']
                break
        else:
            for ref in refs['letters']:
                j = _jaccard(mine, ref['bios'])
                if ref['congress'] == rec['congress'] and ref['date'] and abs((ref['date'] - when).days) <= 3 and j >= 0.3 and \
                        (best is None or j > best[2]):
                    best = ('existing_letter', ref['id'], j)
            if best:
                rec['status'] = ('DUPLICATE_OF:' if best[2] >= 0.8 else 'NOT_EXACT:conflicts_existing:') + best[1]
        if best:
            rec['dedupe'] = {'matched_existing': best[1], 'method': best[0], 'jaccard': round(best[2], 4)}
    base, n = rec['letter_id'], 2
    while rec['letter_id'] in staging or rec['letter_id'] in refs['ids']:
        rec['letter_id'] = '%s-%d' % (base, n)
        n += 1
    staging[rec['letter_id']] = rec
    return 'new'


def error_stub(raw, document_url, source_url, kind, now, error_type):
    """An analysis crash keeps the PDF's identity and the error type, visible, and is retried a day later."""
    digest = _sha(raw)
    return {'letter_id': 'ANALYZE-ERROR-' + digest[:12], 'status': 'NOT_EXACT:analyze_error:' + error_type, 'source_kind': kind,
            'source_url': source_url, 'source_urls': [source_url], 'document_url': document_url, 'sha256': digest,
            'retrieved_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'retry_after': (now.date() + dt.timedelta(days=1)).isoformat(),
            'signatories': [], 'congress': None, 'letter_date': None, 'extraction_method': None}


def to_stub(rec):
    """An off-topic letter keeps its identity (so it is never refetched) and nothing else."""
    return dict(rec, status='OFF_TOPIC', letter_id='OFFTOPIC-' + rec['sha256'][:12], signatories=[], unaccounted_lines=[], leads=[],
                subject_categories=[], recipients=[], subject='', body='')


def load_staging(letters_dir):
    path = os.path.join(letters_dir, 'letter_staging.jsonl')
    if not os.path.exists(path):
        return {}
    with open(path, encoding='utf-8') as handle:
        recs = [json.loads(line) for line in handle if line.strip()]
    return {r['letter_id']: r for r in recs}


def save_staging(letters_dir, staging):
    data = ''.join(json.dumps(staging[k], sort_keys=True, ensure_ascii=True) + '\n' for k in sorted(staging)).encode('utf-8')
    _atomic_write(os.path.join(letters_dir, 'letter_staging.jsonl'), data)
    return _sha(data)


# ---- the legs ---------------------------------------------------------------------------------------

class _Stop(Exception):
    pass


def exit_code(receipt):
    return 1 if receipt['status'] == 'FAIL' else 0


def collect(*, root, letters_dir, legs, fetcher, now, listings=COMMITTEE_LISTINGS, pages=2):
    """Run the legs ('committee', 'press', 'backfill'), stage what they find, write the receipt. Never raises on a designed stop."""
    r = {'schema': 'signon-letters-collector-v1', 'started_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'legs': list(legs),
         'status': 'PASS', 'staged_new': 0, 'errors': 0, 'unparsed': 0, 'cap_hit': False, 'hosts_refused': {}, 'hosts_failed': {},
         'gaps': [], 'skipped_not_letter': 0, 'skipped_known': 0, 'listing_pages': 0, 'releases': 0, 'pdfs': 0}
    try:
        resolver, bio = load_roster(root)
        staging = load_staging(letters_dir)
        refs = load_existing_letters(os.path.join(root, 'manual_bill_evidence.csv'), bio)
    except (OSError, ValueError, KeyError) as e:
        r.update(status='FAIL', error=repr(e)[:200])
        try:
            _atomic_write(os.path.join(letters_dir, 'collector_receipt.json'), json.dumps(r, indent=1, sort_keys=True).encode())
        except OSError:
            pass
        return r
    today = now.date().isoformat()
    # A stub with retry_after is retried once that day has come (a release that gained its PDF, a bug since fixed).
    known = {u for rec in staging.values() if not (rec.get('retry_after') and rec['retry_after'] <= today) for u in rec['source_urls']}
    cursor_path = os.path.join(letters_dir, 'backfill_cursor.json')
    cursor = json.load(open(cursor_path, encoding='utf-8')) if os.path.exists(cursor_path) else {}

    def fetch(url, limit):
        host = urllib.parse.urlparse(url).hostname
        if host in r['hosts_refused']:
            return None
        try:
            return fetcher.get(url, limit)
        except CapReached:
            r['cap_hit'] = True
            raise _Stop()
        except FetchRefused as e:
            r['hosts_refused'][host] = str(e)[:80]
        except FetchFailed as e:
            r['errors'] += 1
            entry = r['hosts_failed'].setdefault(host, {'count': 0, 'last': '', 'urls': []})
            entry['count'] += 1
            entry['last'] = str(e)[:80]
            entry['urls'] = (entry['urls'] + [url])[:5]
        return None

    def release(url, kind):
        """One release page -> its (up to two) official letter PDFs -> staged records. A fetch failure leaves it unstaged: retried."""
        html = fetch(url, HTML_CAP)
        if html is None:
            return
        r['releases'] += 1
        for key in [k for k, v in staging.items() if url in v['source_urls'] and v.get('retry_after')]:
            del staging[key]      # a due stub is replaced by whatever this fetch finds
        rel = parse_release(html, url)
        rel['sha256'] = _sha(html)
        links = [u for u in rel['pdf_links'] if official_host(u)][:2]    # ponytail: a 2nd PDF failing leaves this release 'known'
        if not links:
            staging['NOPDF-' + _sha(url.encode())[:12]] = {'letter_id': 'NOPDF-' + _sha(url.encode())[:12], 'status': 'NOT_EXACT:no_pdf_link',
                'source_kind': kind, 'source_url': url, 'source_urls': [url], 'document_url': None, 'sha256': rel['sha256'],
                'retrieved_at': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'signatories': [], 'congress': None, 'letter_date': None,
                'retry_after': (now.date() + dt.timedelta(days=NOPDF_RETRY_DAYS)).isoformat()}   # a statement may gain its letter later
            known.add(url)
            return
        for pdf in links:
            raw = fetch(pdf, PDF_CAP)
            if raw is None:
                continue
            r['pdfs'] += 1
            try:
                rec = analyze_letter(raw, document_url=pdf, source_url=url, source_kind=kind, release=rel, resolver=resolver, bio=bio, now=now)
            except Exception as e:     # one malformed PDF must not cost the rest of the run
                r['errors'] += 1
                rec = error_stub(raw, pdf, url, kind, now, type(e).__name__)
                r['staged_new'] += stage_record(staging, rec, refs) == 'new'
                continue
            if rec['status'].startswith('NOT_EXACT:') and rec['extraction_method'] is None:
                r['unparsed'] += 1
            elif not (rec['cu_relevant'] and rec['is_letter']):
                rec = to_stub(rec)
            if rec['status'] != 'OFF_TOPIC':
                _atomic_write(os.path.join(letters_dir, 'pdf', rec['sha256'] + '.pdf'), raw)
            r['staged_new'] += stage_record(staging, rec, refs) == 'new'
        known.add(url)

    def committee(backfill):
        for key, first, paginates in listings:
            state = cursor.get(key, {'next_page': 1, 'done': False}) if backfill else {'next_page': 1, 'done': False}
            if state['done']:
                continue
            page, past = state['next_page'], False
            for _ in range(pages):
                if page > 1 and not paginates:
                    state['done'] = True
                    break
                html = fetch(first if page == 1 else '%s&Page=%d' % (first, page), HTML_CAP)
                if html is None:
                    break
                r['listing_pages'] += 1
                items = parse_listing(html, first)
                if page == 1 and not items:    # the listing's first page always has releases: 0 means the markup changed, not "the end"
                    r['gaps'].append('listing_unparsed:' + key)
                    break
                for item in items:
                    item_url = canonical_url(item['url'])
                    if backfill and item['date'] and dt.date.fromisoformat(item['date']) < BACKFILL_FLOOR:
                        past = True
                    elif item_url in known:
                        r['skipped_known'] += 1
                    elif not LETTER_RE.search(item['title'] + ' ' + item['snippet']):
                        r['skipped_not_letter'] += 1
                    else:
                        release(item_url, 'committee_site')
                page += 1
                if backfill:
                    state.update(next_page=page, done=past or not items)
                    cursor[key] = state
                if past or not items:
                    break

    def press():
        tried = set()
        found = sorted(glob_press(root))
        if not found:
            r['gaps'].append('press_source_missing')
            return
        csv.field_size_limit(2 ** 27)
        with open(found[-1], encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            if not {'url', 'title', 'body'} <= set(reader.fieldnames or []):
                r['gaps'].append('press_schema')     # a renamed column must not read as "no letters today"
                return
            for row in reader:
                url, text = canonical_url(row.get('url')), (row.get('title') or '') + ' ' + (row.get('body') or '')[:3000]
                if not url or url in known or url in tried:
                    r['skipped_known'] += bool(url)
                elif LETTER_RE.search(text) and cu_relevant(text) and official_host(url):
                    tried.add(url)
                    release(url, 'member_press')
                else:
                    r['skipped_not_letter'] += 1

    try:
        for leg in legs:
            try:
                {'committee': lambda: committee(False), 'backfill': lambda: committee(True), 'press': press}[leg]()
            except _Stop:
                break
            except Exception as e:      # a surprise in one leg must not lose the other legs or what was already staged
                r['errors'] += 1
                r['gaps'].append('leg_crashed:%s:%s' % (leg, type(e).__name__))
    finally:
        r['staging_sha256'] = save_staging(letters_dir, staging)
    r['requests'] = len(fetcher.requests)
    if cursor:
        _atomic_write(cursor_path, json.dumps(cursor, indent=1, sort_keys=True).encode())
    r['by_status'] = dict(collections.Counter(rec['status'].split(':')[0] for rec in staging.values()))
    r['by_reason'] = dict(collections.Counter(rec['status'] for rec in staging.values() if rec['status'].startswith('NOT_EXACT')))
    if r['hosts_refused'] or r['hosts_failed'] or r['errors'] or r['cap_hit'] or r['unparsed'] or r['gaps']:
        r['status'] = 'PARTIAL'
    _atomic_write(os.path.join(letters_dir, 'collector_receipt.json'), json.dumps(r, indent=1, sort_keys=True).encode())
    return r


def glob_press(root):
    base = os.path.join(root, 'outputs')
    if not os.path.isdir(base):
        return []
    return [os.path.join(base, d, 'press_delta_fulltext.csv') for d in os.listdir(base)
            if d.startswith('press_refresh_') and os.path.exists(os.path.join(base, d, 'press_delta_fulltext.csv'))]


def main(argv=None):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser(description='Stage member sign-on letters (exact signatories) from official .gov sources.')
    ap.add_argument('--committee', action='store_true', help='House Financial Services + Senate Banking release listings')
    ap.add_argument('--from-press', action='store_true', help='newest press_delta_fulltext.csv, CU-domain letter announcements')
    ap.add_argument('--backfill', action='store_true', help='one-time resumable committee crawl back to the 117th Congress')
    ap.add_argument('--max-requests', type=int, default=REQUEST_CAP)
    ap.add_argument('--pages', type=int, default=0, help='listing pages per listing per run (default 2; 50 for --backfill)')
    ap.add_argument('--root', default=MB_ROOT)
    ap.add_argument('--letters-dir', default=None)
    a = ap.parse_args(argv)
    legs = [leg for leg, on in (('committee', a.committee), ('press', a.from_press), ('backfill', a.backfill)) if on]
    if not legs:
        ap.error('choose --committee, --from-press and/or --backfill')
    receipt = collect(root=a.root, letters_dir=a.letters_dir or os.path.join(a.root, LETTERS_RELATIVE), legs=legs,
                      fetcher=Fetcher(cap=a.max_requests), now=dt.datetime.now(dt.timezone.utc),
                      pages=a.pages or (50 if 'backfill' in legs else 2))
    print('letters collector %s: requests %s, staged_new %s, by_status %s, errors %s, refused %s, cap_hit %s' % (
        receipt['status'], receipt.get('requests'), receipt['staged_new'], receipt.get('by_status'), receipt['errors'],
        sorted(receipt['hosts_refused']), receipt['cap_hit']))
    return exit_code(receipt)


if __name__ == '__main__':
    sys.exit(main())
