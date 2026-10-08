# -*- coding: utf-8 -*-
"""Lane F1 shared read-only helpers.

NOTHING under fec/ is imported here (import == execution: those modules overwrite
production artifacts).  The four rule functions below are VERBATIM RE-IMPLEMENTATIONS
of the LIVE producer's rules, transcribed from:

  LIVE\\fec\\bill_rules.py:211-219   role_weight   (sponsor 3.0 / original-cosponsor 2.0 / cosponsor 1.0 / else 1.0)
  LIVE\\fec\\bill_rules.py:222-230   canonical_role
  LIVE\\fec\\bill_rules.py:233-237   preferred_role
  LIVE\\fec\\bill_rules.py:240-244   _congress
  LIVE\\fec\\bill_rules.py:110-122   canonical_category
  LIVE\\fec\\bill_rules.py:135-138   bill_key
  LIVE\\fec\\bill_rules.py:141-154   bill_type_key
  LIVE\\fec\\members\\member_identity.py:51-177  Resolver (normalize_name / first_names_agree / resolve)

Every transcription is byte-compared against the LIVE source by f1_selfcheck.py.
"""
import os
import re
import json
import unicodedata
import collections
import openpyxl

ROOT = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
SEL_ARCHIVE = "congress_bills_archive_20260825_115305.xlsx"
OLD_ARCHIVE = "congress_bills_archive_20260624_115822.xlsx"
WORKBOOK = "Moneyball Main Version - Blended.xlsx"
SENTINEL = "Sentinel Bill Ledger.xlsx"


# ---------------------------------------------------------------- bill_rules.py
CATEGORIES = (
    'Examination & Supervision', 'CU Capital Requirements',
    'NCUA Budget & Insurance', 'Interchange', 'Payments',
    'Technology & Emerging', 'Fraud Prevention', 'Data Privacy & Cyber',
    'Charter Modernization', 'Defense CU Issues', 'Field of Membership',
    'CU Tax Status', 'CDFI Fund', 'CFPB', 'Credit Card Mandates', 'TCPA',
    'Member Business Lending', 'Mortgage & Housing',
)
LABEL_TO_CANONICAL = {
    'CFPB Issues & Structural Reform': 'CFPB',
    'Charter Modernization & Governance': 'Charter Modernization',
    'Credit Union Capital Requirements': 'CU Capital Requirements',
    'Credit Card & Consumer-Fee Mandates': 'Credit Card Mandates',
    'Credit Union Tax Status': 'CU Tax Status',
    'Data Privacy & Cybersecurity': 'Data Privacy & Cyber',
    'Defense Credit Union Issues': 'Defense CU Issues',
    'Mortgage Lending & Housing': 'Mortgage & Housing',
    'NCUA Budget & Share Insurance Fund': 'NCUA Budget & Insurance',
    'Technology & Emerging Issues': 'Technology & Emerging',
    'Telephone Consumer Protection Act Issues': 'TCPA',
}
SECTION_KEYWORDS = (
    ('Examination & Supervision', 'examination'),
    ('CU Capital Requirements', 'capital'),
    ('NCUA Budget & Insurance', 'ncua'),
    ('Interchange', 'interchange'),
    ('Payments', 'payments'),
    ('Technology & Emerging', 'technology'),
    ('Fraud Prevention', 'fraud'),
    ('Data Privacy & Cyber', 'data privacy'),
    ('Charter Modernization', 'charter'),
    ('Defense CU Issues', 'defense'),
    ('Field of Membership', 'field of membership'),
    ('CU Tax Status', 'tax status'),
    ('CDFI Fund', 'cdfi'),
    ('CFPB', 'cfpb'),
    ('Credit Card Mandates', 'credit card'),
    ('TCPA', 'telephone'),
    ('Member Business Lending', 'member business'),
    ('Mortgage & Housing', 'mortgage'),
)


def canonical_category(value):
    raw = str(value or '').strip()
    if not raw:
        return None
    if raw in CATEGORIES:
        return raw
    if raw in LABEL_TO_CANONICAL:
        return LABEL_TO_CANONICAL[raw]
    low = raw.lower()
    for category, keyword in SECTION_KEYWORDS:
        if keyword in low:
            return category
    return None


def bill_key(value):
    match = re.match(r'\s*([HS])\.?\s*([RJ]?\.?\s*(?:Res\.?)?)\s*(\d+)', str(value or ''), re.I)
    return (match.group(1).upper(), int(match.group(3))) if match else None


def bill_type_key(value):
    match = re.match(
        r'\s*([HS])\.?\s*(?:(R|J\.?\s*Res|Con\.?\s*Res|Res)\.?\s*)?(\d+)',
        str(value or ''), re.I)
    if not match:
        return None
    type_token = re.sub(r'[^A-Za-z]', '', match.group(2) or 'R').upper()
    return (match.group(1).upper(), type_token, int(match.group(3)))


def role_weight(role):
    value = canonical_role(role)
    if value == 'original-cosponsor':
        return 2.0
    if value == 'cosponsor':
        return 1.0
    if value == 'sponsor':
        return 3.0
    return 1.0


def canonical_role(role):
    value = str(role or '').strip().lower()
    if 'original' in value:
        return 'original-cosponsor'
    if 'cosponsor' in value or 'co-spons' in value:
        return 'cosponsor'
    if 'sponsor' in value:
        return 'sponsor'
    return value or 'other'


def preferred_role(roles):
    priority = {'other': 0, 'cosponsor': 1, 'original-cosponsor': 2, 'sponsor': 3}
    canonical = [canonical_role(role) for role in roles]
    return max(canonical, key=lambda role: (priority.get(role, 0), role)) if canonical else 'other'


def congress_of(value):
    """bill_rules._congress"""
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value or '').strip()


# ------------------------------------------------------- member_identity.py
_SUFFIXES = {'jr', 'sr', 'ii', 'iii', 'iv'}
_FIRST_EQUIV = [
    {'richard', 'dick', 'rick', 'rich'}, {'charles', 'chuck'}, {'william', 'bill', 'billy'},
    {'michael', 'mike'}, {'robert', 'bob', 'bobby', 'rob'}, {'edward', 'ed', 'eddie'},
    {'james', 'jim', 'jimmy'}, {'thomas', 'tom', 'tommy'}, {'john', 'jack', 'johnny'},
    {'joseph', 'joe'}, {'gerald', 'jerry'}, {'jerrold', 'jerry'}, {'daniel', 'dan'},
    {'donald', 'don'}, {'ronald', 'ron'}, {'andrew', 'andy'}, {'kenneth', 'ken'},
    {'benjamin', 'ben'}, {'nicholas', 'nick'}, {'christopher', 'chris'},
    {'stephen', 'steve'}, {'timothy', 'tim'}, {'matthew', 'matt'}, {'david', 'dave'},
    {'samuel', 'sam'}, {'patrick', 'pat'}, {'anthony', 'tony'}, {'alexander', 'alex'},
    {'katherine', 'katie', 'kate'}, {'elizabeth', 'liz', 'beth'}, {'margaret', 'maggie'},
    {'cynthia', 'cindy'}, {'earl', 'buddy'}, {'addison', 'mitch'}, {'rafael', 'ted'},
    {'louis', 'lou'}, {'luis', 'lou'}, {'francis', 'frank'}, {'rebecca', 'becca'},
    {'abraham', 'abe'}, {'gregory', 'greg'}, {'douglas', 'doug'}, {'raymond', 'ray'},
    {'harold', 'hal'}, {'zachary', 'zach'}, {'janice', 'jan'}, {'bernard', 'bernie'},
    {'jennifer', 'jen'}, {'elijah', 'eli'}, {'henry', 'hank'}, {'bradley', 'brad'},
]
_FIRST_GROUPS = {}
for _i, _g in enumerate(_FIRST_EQUIV):
    for _n in _g:
        _FIRST_GROUPS.setdefault(_n, set()).add(_i)
_MEMBER_ALIASES = {'rick crawford': 'eric crawford'}


def normalize_name(value):
    text = unicodedata.normalize('NFKD', str(value or '')).encode('ascii', 'ignore').decode('ascii').casefold()
    text = re.sub(r"[^a-z0-9]+", ' ', text).strip()
    parts = [p for p in text.split() if p not in _SUFFIXES]
    return ' '.join(parts)


def first_names_agree(query_first, candidate_first):
    if not query_first or not candidate_first:
        return False
    if query_first == candidate_first:
        return True
    if len(query_first) == 1:
        return candidate_first.startswith(query_first)
    if len(candidate_first) == 1:
        return query_first.startswith(candidate_first)
    if query_first.startswith(candidate_first) or candidate_first.startswith(query_first):
        return True
    return bool(_FIRST_GROUPS.get(query_first, set()) & _FIRST_GROUPS.get(candidate_first, set()))


class Resolver:
    def __init__(self, names, name_to_bioguide=None):
        self.names = list(names)
        self.name_set = set(self.names)
        self.by_norm = collections.defaultdict(list)
        self.by_last = collections.defaultdict(list)
        for name in self.names:
            norm = normalize_name(name)
            self.by_norm[norm].append(name)
            if norm:
                self.by_last[norm.split()[-1]].append(name)
        self.by_bio = {bio: name for name, bio in (name_to_bioguide or {}).items()
                       if name in self.name_set and bio}

    def resolve(self, name=None, bioguide=None):
        if bioguide and bioguide in self.by_bio:
            return self.by_bio[bioguide]
        if name in self.name_set:
            return name
        raw = str(name or '').strip()
        _alias = _MEMBER_ALIASES.get(normalize_name(raw))
        if _alias:
            for _n in self.names:
                if normalize_name(_n) == _alias:
                    return _n
        variants = []
        if ',' in raw:
            left, right = raw.split(',', 1)
            variants.append((right + ' ' + left).strip())
        variants.append(raw)
        for variant in variants:
            norm = normalize_name(variant)
            exact = self.by_norm.get(norm, [])
            if len(exact) == 1:
                return exact[0]
            if len(exact) > 1:
                return None
            toks = norm.split()
            if not toks:
                continue
            candidates = self.by_last.get(toks[-1], [])
            if not candidates:
                continue
            if len(toks) == 1:
                if len(candidates) == 1:
                    return candidates[0]
                continue
            firsts = {c: normalize_name(c).split()[0] for c in candidates}
            matched = [c for c in candidates if first_names_agree(toks[0], firsts[c])]
            if len(matched) == 1:
                return matched[0]
            if not matched and len(toks) > 2:
                matched = [c for c in candidates
                           if any(first_names_agree(t, firsts[c]) for t in toks[1:-1])]
            if len(matched) == 1:
                return matched[0]
        return None


# ------------------------------------------------------------------- loaders
def xl(relpath, sheet):
    wb = openpyxl.load_workbook(os.path.join(ROOT, relpath), read_only=True, data_only=True)
    ws = wb[sheet]
    it = ws.iter_rows(values_only=True)
    head = [str(x) if x is not None else '' for x in next(it)]
    out = [dict(zip(head, r)) for r in it]
    wb.close()
    return out


def jload(relpath):
    with open(os.path.join(ROOT, relpath), encoding='utf-8') as fh:
        return json.load(fh)


def roster():
    """The producer's roster: [m['member'] for m in data/engine/congestion.json]."""
    data = jload(r'data\engine\congestion.json')
    return [m['member'] for m in data], {m['member']: m.get('bioguide') for m in data}


def sentinel_scoring_rows():
    """LIVE build_archive_legislative.sentinel_scoring_mask, applied row-wise."""
    out = []
    for r in xl(SENTINEL, 'Sentinel Bill Ledger'):
        def t(name):
            return str(r.get(name) or '').strip().lower()
        if (t('Scoring Eligible') in {'true', '1', 'yes'}
                and t('Review Status') == 'verified'
                and t('Record Type') == 'membership'):
            out.append(r)
    return out


def manual_rows():
    import csv
    with open(os.path.join(ROOT, 'manual_bill_evidence.csv'), encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


# ------------------------------------------------------------------ grains
def bill_ident(name, congress):
    """Producer dedup grain for the bill half of event_key:
    str(Name).strip().lower() plus BR._congress(Congress)   (producer line 251)."""
    return (str(name or '').strip().lower(), congress_of(congress))


def chamber(name):
    key = bill_type_key(name)
    if key is None:
        return 'UNKNOWN'
    return {'H': 'House', 'S': 'Senate'}[key[0]]


_HON = re.compile(r'^\s*(?:rep|sen|del|res\.?\s*comm|commissioner)\.?\s+', re.I)


def clean_sponsor_cell(value):
    """Strip the Congress.gov party/state bracket and a leading chamber honorific.

    'Rep. Ogles, Andrew [R-TN-5]'   -> 'Ogles, Andrew'
    'Hagerty, Bill [Sen.-R-TN]'     -> 'Hagerty, Bill'
    'Sen. Feinstein, Dianne [D-CA]' -> 'Feinstein, Dianne'
    """
    text = str(value or '').strip()
    if not text or text.lower() in ('nan', 'none'):
        return ''
    text = re.sub(r'\[[^\]]*\]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip().strip(',').strip()
    text = _HON.sub('', text).strip()
    return text
