"""Section-aware evidence selection for sentinel admissions (M5a: D-366 design, approved as D-369).

A bill whose complete official evidence would fail the admission envelope -- more than STATUTE_LIMIT cited U.S. Code
sections, or more than CHAR_LIMIT characters -- is no longer turned away whole. Fixed rules, applied in a fixed order,
stop at the first step that fits:

  S1  statute notes: each cited section keeps its operative text, source credit and footnotes; its Editorial and
      Statutory Notes are omitted. A section the bill cites as "N U.S.C. X note" keeps its notes.
  S2  statute selection: keep a cited section only when it is on the CU statute map, or a bill section matching the
      NARROW vocabulary cites it. Run before any fetch when the citation count trips the gate.
  S3  bill sections: keep the first section, any Definitions section and every top-level section matching the WIDE
      vocabulary; every other top-level section is replaced in place by a marker naming it.

No step fills up to a budget: each is a rule over whole documents or whole sections, so nothing is cut mid-document
and the result does not depend on how close a bill sits to the limit. Every omitted part is named, with its reason,
in the manifest that travels with the evidence, the decision and the run receipt. A bill still too big after S3
raises EvidenceEnvelopeExceeded and is FAILED, never held.

A bill that fits the envelope never reaches this module: its evidence, prompt and fingerprint are byte-identical to
what they were before selection existed. The vocabularies are a negative screen over what the classifier is shown,
never a relevance score (DE-001).
"""
from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from paths import to_host

# Replay re-runs this code over sealed evidence. A behaviour change to selection must bump VERSION, and a bump makes every
# sealed selected verdict non-reusable (reclassified on its next selection); SA.load refuses a generation whose admitted
# include cannot be replayed, so a bump lands only with those includes reclassified.
VERSION = 'sentinel-evidence-selection-v1'
CHAR_LIMIT = 400000
STATUTE_LIMIT = 24
CONFIG_PATH = Path(__file__).resolve().parents[1] / 'config' / 'sentinel_evidence_selection.json'
MARKER_PREFIX = '[SECTION OMITTED UNDER EVIDENCE SELECTION'
NOTE_HEAD = b'<h4 class="note-head">'
_OPERATIVE_END = (b'<!-- field-end:sourcecredit -->', b'<!-- field-end:statute -->')
_FOOTNOTE = re.compile(rb'<!-- field-start:footnote -->.*?<!-- field-end:footnote -->', re.S)
_DASHES = str.maketrans({char: '-' for char in '‐‑‒–—−'})
_NOTE_CITE = re.compile(r'\b(\d+)\s+U\.S\.C\.\s*(\d+[a-z]*(?:-\d+[a-z]*)*)\s+note\b', re.I)
_WORD = re.compile(r'[a-z0-9-]+')
_BODY_TAGS = ('legis-body', 'resolution-body', 'engrossed-amendment-body')
NO_CU_TERM = 'no credit-union term in the section (wide vocabulary)'
STATUTE_OMITTED = 'not on the CU statute map and not cited from a CU-relevant bill section'
_MARKER = re.compile(re.escape(MARKER_PREFIX) + r'[^\]]*\]')   # a marker never holds a ']' before its end (see select_sections)


def quote_overlaps_marker(text, quote):
    """Does every occurrence of `quote` in `text` touch an omission marker? A marker is not official text, so a quote that
    starts, ends or runs inside one quotes nothing. False for any text without a marker (every unselected document)."""
    if not quote or MARKER_PREFIX not in text:
        return False
    spans = [m.span() for m in _MARKER.finditer(text)]
    start = text.find(quote)
    if start < 0:
        return False
    while start >= 0:
        if not any(a < start + len(quote) and start < b for a, b in spans):
            return False
        start = text.find(quote, start + 1)
    return True


class EvidenceEnvelopeExceeded(ValueError):
    """The evidence is still over the envelope after every selection step. The bill is FAILED (D-366), never held and
    never clipped; the manifest names every step tried and everything omitted."""

    def __init__(self, gate, manifest):
        ValueError.__init__(self, f'evidence exceeds the envelope after section-aware selection ({gate})')
        self.gate = gate
        self.manifest = manifest


class SelectionReplayUnavailable(OSError):
    """A verdict sealed under another selector version cannot be replayed. Like unreadable cached evidence (an OSError,
    which the reuse paths already treat as 'not reusable'), the key is classified afresh; it is not an integrity alarm."""


def statute_id(title, section):
    return f'{title} USC {section}'


def load_config(path=None):
    """(config, raw bytes, sha256) of the selection config."""
    raw = Path(path or CONFIG_PATH).read_bytes()
    return json.loads(raw), raw, hashlib.sha256(raw).hexdigest()


def snapshot_config(raw, sha, directory):
    """Content-address the config beside the evidence, so a sealed verdict replays under the rules it was selected by."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (sha + '.json')
    if not path.exists():
        path.write_bytes(raw)
    return {'path': str(path.resolve()), 'sha256': sha}


def _phrase_hits(low, terms):
    return [term for term in terms if term in low]


def matches(text, config, vocabulary):
    """Sorted labels of what makes `text` CU-relevant under 'narrow' or 'wide': phrase terms (substring of the lowered,
    whitespace-collapsed text) and registry identifiers (every token within identifier_window words of the first)."""
    low = ' '.join(text.lower().split())
    hits = set(_phrase_hits(low, config[vocabulary + '_terms']))
    words = _WORD.findall(low)
    where = {}
    for index, word in enumerate(words):
        where.setdefault(word, []).append(index)
    window = int(config['identifier_window'])
    for identifier in config['identifiers']:
        tokens = identifier['tokens']
        if not all(token in where for token in tokens):
            continue
        if any(all(any(abs(j - i) <= window for j in where[token]) for token in tokens[1:]) for i in where[tokens[0]]):
            hits.add('%s: %s' % (identifier['category'], ' '.join(tokens)))
    return sorted(hits)


def map_label(config, title, section):
    found = re.match(r'\d+', str(section))
    number = int(found.group(0)) if found else -1
    for row in config['statute_map']:
        if int(title) == int(row['title']) and int(row['from']) <= number <= int(row['to']):
            return row['label']
    return None


def note_citations(texts):
    lookup = ' '.join(texts).translate(_DASHES)
    return {statute_id(title, section) for title, section in _NOTE_CITE.findall(lookup)}


# ---- bill sections -----------------------------------------------------------------------------------------------

def _text_parts(element, omit):
    """ElementTree.itertext, except that an omitted element yields its marker instead of its text (its tail still
    belongs to the parent and is kept)."""
    if id(element) in omit:
        yield omit[id(element)]
        return
    tag = element.tag
    if not isinstance(tag, str) and tag is not None:
        return
    if element.text:
        yield element.text
    for child in element:
        yield from _text_parts(child, omit)
        if child.tail:
            yield child.tail


def _join(parts):
    # The same join govinfo_discovery_fallback._parse_bill_text uses for the complete text.
    return ' '.join(part.strip() for part in parts if part.strip())


def bill_sections(raw):
    """(root, [(label, element, text)]) for the top-level sections of a bill version; sections inside a quoted block are
    amendatory text and stay with the section that inserts them. (None, []) when the XML has no section structure."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return None, []
    body = next((found for tag in _BODY_TAGS for found in [root.find('.//' + tag)] if found is not None), None)
    if body is None:
        return root, []
    out = []

    def walk(element):
        for child in element:
            if child.tag == 'quoted-block':
                continue
            if child.tag == 'section':
                enum = ''.join(child.find('enum').itertext()).strip() if child.find('enum') is not None else ''
                header = ' '.join(''.join(child.find('header').itertext()).split()) if child.find('header') is not None else ''
                label = ('Sec. %s %s' % (enum.rstrip('.'), header)).strip()
                out.append((label, child, _join(_text_parts(child, {}))))
            else:
                walk(child)
    walk(body)
    return root, out


def relevant_statutes(config, raw_bills, bill_texts, cited, references):
    """Which cited sections S2 keeps: {id: reason} kept and {id: reason} omitted. `references` is the production
    statute_references (one regex for citations everywhere); `bill_texts` backs bills without section structure."""
    citing = {}
    for url, raw in sorted(raw_bills.items()):
        _, sections = bill_sections(raw)
        units = [(label, text) for label, _, text in sections] or [('whole text', bill_texts.get(url, ''))]
        for label, text in units:
            if matches(text, config, 'narrow'):
                for title, section in references({url: text}):
                    citing.setdefault(statute_id(title, section), '%s (%s)' % (label, url.rsplit('/', 1)[-1]))
    kept, omitted = {}, {}
    for title, section in sorted(cited):
        identity = statute_id(title, section)
        label = map_label(config, title, section)
        if label:
            kept[identity] = 'on the CU statute map: ' + label
        elif identity in citing:
            kept[identity] = 'cited from a CU-relevant bill section: ' + citing[identity]
        else:
            omitted[identity] = STATUTE_OMITTED
    return kept, omitted


def operative_html(raw):
    """A statute page cut at its first note heading AFTER the end of its operative text (source credit, else statute
    field), with its trailing footnotes kept. None when the page marks no operative end or has no note heading after it --
    the caller keeps the whole page and records it as not separable."""
    ends = [raw.find(marker) for marker in _OPERATIVE_END if raw.find(marker) >= 0]
    if not ends:
        return None
    cut = raw.find(NOTE_HEAD, ends[0])
    if cut < 0:
        return None
    return raw[:cut] + b' '.join(_FOOTNOTE.findall(raw[cut:]))


def strip_notes(texts, statutes, bill_texts, parse):
    """S1 over `statutes` [(url, raw, source)]: texts with notes-free statute text, and the record of what was omitted."""
    texts = dict(texts)
    noted = note_citations(bill_texts)
    record = {'omitted': [], 'kept_for_note_citation': [], 'not_separable': []}
    for url, raw, source in statutes:
        identity = statute_id(source['title'], source['section'])
        if identity in noted:
            record['kept_for_note_citation'].append(identity)
            continue
        cut = operative_html(raw)
        if cut is None:
            record['not_separable'].append(identity)
            continue
        operative = parse(cut, source)
        record['omitted'].append({'id': identity, 'url': url, 'chars_omitted': len(texts[url]) - len(operative),
                                  'reason': 'Editorial and Statutory Notes (amendment history, effective dates, codified '
                                            'notes): not operative law of the section'})
        texts[url] = operative
    return texts, record


def select_sections(config, texts, raw_bills):
    """S3: texts with off-topic top-level sections of each bill version replaced by markers, and the record. A version
    whose rebuilt complete text does not equal the text the classifier would otherwise see is left whole (recorded)."""
    texts = dict(texts)
    record = {'omitted': [], 'kept': 0, 'not_separable': []}
    for url, raw in sorted(raw_bills.items()):
        root, sections = bill_sections(raw)
        if root is None or not sections or _join(_text_parts(root, {})) != texts.get(url):
            record['not_separable'].append(url)
            continue
        omit = {}
        for index, (label, element, text) in enumerate(sections):
            if index == 0 or 'definition' in label.lower() or matches(text, config, 'wide'):
                record['kept'] += 1
                continue
            omit[id(element)] = '%s v1: %s, %d chars, reason: %s]' % (MARKER_PREFIX, label.replace(']', ')'), len(text), NO_CU_TERM)
            record['omitted'].append({'url': url, 'index': index, 'section': label, 'chars': len(text), 'reason': NO_CU_TERM})
        if omit:
            texts[url] = _join(_text_parts(root, omit))
    return texts, record


def new_manifest(trigger, config_ref, *, cited):
    # chars_before is the evidence as fetched: complete for the char gate; after S2 for the statute gate, whose omitted
    # sections were never fetched (their size is unknown, and named in statutes.omitted).
    return {'version': VERSION, 'config': config_ref, 'trigger': trigger,
            'limits': {'chars': CHAR_LIMIT, 'statutes': STATUTE_LIMIT}, 'steps': [], 'cited_statutes': cited,
            'statutes': {'kept': {}, 'omitted': []}, 'notes': None, 'bill_sections': None,
            'chars_before': None, 'chars_before_scope': 'complete evidence' if trigger == 'chars'
            else 'after S2: omitted statutes were never fetched', 'chars_after': None}


def fingerprint_view(manifest):
    """What a selected verdict's evidence fingerprint adds: the rules (version, config) and what they omitted."""
    return {'version': manifest['version'], 'config_sha256': manifest['config']['sha256'], 'steps': manifest['steps'],
            'omitted_statutes': [row['id'] for row in manifest['statutes']['omitted']],
            'omitted_notes': [row['id'] for row in (manifest['notes'] or {}).get('omitted', [])],
            'omitted_sections': [[row['url'], row['index']] for row in (manifest['bill_sections'] or {}).get('omitted', [])]}


def prompt_note(manifest):
    """The block a selected bill's classifier prompt carries. The system prompt is unchanged."""
    return {
        'notice': ('Parts of the complete official evidence were omitted by deterministic section-aware selection because '
                   'the complete evidence exceeds the classifier envelope. Omitted text was not supplied. If a defensible '
                   'decision depends on it, hold.'),
        'steps': manifest['steps'],
        'omitted_statutes': [{'statute': row['id'], 'reason': row['reason']} for row in manifest['statutes']['omitted']],
        'omitted_statute_notes': [row['id'] for row in (manifest['notes'] or {}).get('omitted', [])],
        'omitted_bill_sections': [{'source_url': row['url'], 'section': row['section'], 'reason': row['reason']}
                                  for row in (manifest['bill_sections'] or {}).get('omitted', [])],
    }


def replay(manifest, texts, raw_bills, statutes, *, parse, references, bill_text_of):
    """Re-apply a sealed manifest to its sha-verified evidence and return the texts the classifier saw. Raises
    SelectionReplayUnavailable for another selector version (or OSError for a missing config snapshot) and ValueError
    when the evidence no longer reproduces the recorded selection (the integrity alarm)."""
    if manifest.get('version') != VERSION:
        raise SelectionReplayUnavailable('evidence selected under %r cannot be replayed by %s' % (manifest.get('version'), VERSION))
    config_path = Path(to_host(manifest['config']['path']))
    config, _, sha = load_config(config_path)
    if sha != manifest['config']['sha256']:
        raise ValueError('cached evidence selection config hash mismatch: ' + str(config_path))
    held = sorted(statute_id(source['title'], source['section']) for _, _, source in statutes)
    if 'S2' in manifest['steps']:
        bill_texts = {url: bill_text_of(url) for url in raw_bills}
        kept, _ = relevant_statutes(config, raw_bills, bill_texts,
                                    {tuple(row.split(' USC ')) for row in list(manifest['statutes']['kept'])
                                     + [r['id'] for r in manifest['statutes']['omitted']]}, references)
        if sorted(kept) != held or kept != manifest['statutes']['kept']:
            raise ValueError('cached evidence selection does not replay: statute selection differs')
    if 'S1' in manifest['steps']:
        texts, notes = strip_notes(texts, statutes, [bill_text_of(url) for url in raw_bills], parse)
        if notes != manifest['notes']:
            raise ValueError('cached evidence selection does not replay: statute notes differ')
    if 'S3' in manifest['steps']:
        texts, sections = select_sections(config, texts, raw_bills)
        if sections != manifest['bill_sections']:
            raise ValueError('cached evidence selection does not replay: bill sections differ')
    return texts


def prune_notes(record, kept_ids):
    """S1 ran over every fetched statute; once S2 drops some, the notes record names only the statutes still kept."""
    if record is None:
        return None
    return {'omitted': [row for row in record['omitted'] if row['id'] in kept_ids],
            'kept_for_note_citation': [i for i in record['kept_for_note_citation'] if i in kept_ids],
            'not_separable': [i for i in record['not_separable'] if i in kept_ids]}
