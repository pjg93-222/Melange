# -*- coding: utf-8 -*-
"""Shared, auditable legislation routing rules.

The archive scorer, Champion corroboration gate, member desk, and audit console
must agree on category names and exclusions. Keep user-editable bill-specific
decisions in ``bill_overrides.csv``; keep only cross-cutting rules here.
"""
import csv
import os
import re

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

# Broad NDAA records are intentionally INCLUDED at the user's direction
# (2026-07-14). The remaining phrases are known keyword-scraper false positives.
EXCLUDED_TITLE_PHRASES = (
    'george floyd', 'save money on auto repair', 'auto repair transportation',
    'accessible, affordable internet', 'affordable internet for all',
    'health and location data', 'fourth amendment is not for sale',
    'app store accountability', 'safer gaming',
    'protecting military servicemembers', 'data from foreign adversaries',
    'cease orwellian surveillance',
)

# Some source rows carry only the ambiguous short title "SMART Act" and omit the
# disambiguating summary. Pin the two auto-repair bills by bill + Congress so
# every role row is excluded while financial/regulatory SMART Acts remain live.
EXCLUDED_BILL_CONGRESSES = {
    (('H', 3664), '117'): 'auto repair SMART Act',
    (('H', 1707), '118'): 'auto repair SMART Act',
}


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


def excluded_title(title, summary=''):
    text = (str(title or '') + ' ' + str(summary or '')).lower()
    return next((phrase for phrase in EXCLUDED_TITLE_PHRASES if phrase in text), None)


def excluded_bill(bill, congress, title='', summary=''):
    pinned = EXCLUDED_BILL_CONGRESSES.get((bill_key(bill), _congress(congress)))
    return pinned or excluded_title(title, summary)


def bill_key(value):
    """Return the legacy-compatible (H|S, number) key used by bill_directions.csv."""
    match = re.match(r'\s*([HS])\.?\s*([RJ]?\.?\s*(?:Res\.?)?)\s*(\d+)', str(value or ''), re.I)
    return (match.group(1).upper(), int(match.group(3))) if match else None


def role_weight(role):
    value = str(role or '').lower()
    if 'original' in value:
        return 2.0
    if 'cosponsor' in value or 'co-spons' in value:
        return 1.0
    if 'sponsor' in value:
        return 3.0
    return 1.0


def _congress(value):
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value or '').strip()


def load_overrides(path):
    """Load {(bill_key, congress|'*'): row}; missing/empty files are valid."""
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, encoding='utf-8-sig', newline='') as handle:
        for row in csv.DictReader(handle):
            key = bill_key(row.get('Bill'))
            if not key:
                continue
            congress = _congress(row.get('Congress')) or '*'
            out[(key, congress)] = {k: (v or '').strip() for k, v in row.items()}
    return out


def override_for(overrides, bill, congress):
    key = bill_key(bill)
    if not key:
        return None
    return overrides.get((key, _congress(congress))) or overrides.get((key, '*'))


def override_included(row):
    value = str((row or {}).get('Include', '')).strip().lower()
    return value not in {'0', 'false', 'no', 'exclude', 'excluded'}
