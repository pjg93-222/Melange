# -*- coding: utf-8 -*-
"""Shared media category routing, normalization, and General-CU exclusion accounting.

All media producers and consumers use these names and word rules.  Text is routed to a policy
domain when the item itself supplies a subject.  Residual General Credit Union evidence remains
visible in an exclusion ledger, but is not projected into policy domains from a member's existing
profile: doing so would manufacture specificity and reinforce the score it was meant to measure.
"""
import re

RAW_TO_STANCE = {
    'Examination & Supervision': 'Examination & Supervision',
    'Credit Union Capital Requirements': 'CU Capital Requirements',
    'NCUA Budget & Share Insurance Fund': 'NCUA Budget & Insurance',
    'Interchange': 'Interchange',
    'Payments': 'Payments',
    'Technology & Emerging Issues': 'Technology & Emerging',
    'Fraud Prevention': 'Fraud Prevention',
    'Data Privacy & Cybersecurity': 'Data Privacy & Cyber',
    'Charter Modernization & Governance': 'Charter Modernization',
    'Defense Credit Union Issues': 'Defense CU Issues',
    'Field of Membership': 'Field of Membership',
    'Credit Union Tax Status': 'CU Tax Status',
    'CDFI Fund': 'CDFI Fund',
    'CFPB Issues & Structural Reform': 'CFPB',
    'Credit Card & Consumer-Fee Mandates': 'Credit Card Mandates',
    'Telephone Consumer Protection Act': 'TCPA',
    'Member Business Lending': 'Member Business Lending',
    'Mortgage Lending & Housing': 'Mortgage & Housing',
}
STANCE_TO_RAW = {v: k for k, v in RAW_TO_STANCE.items()}
GENERAL = 'General Credit Union'
COMPETITIVE = 'CU-Bank Competitive Dynamics'

RAW_PATTERNS = {
    'Examination & Supervision': r'\bncua\b|examination|supervis|regulatory burden|call report',
    'Credit Union Capital Requirements': r'capital requirement|risk.?based capital|net worth ratio',
    'NCUA Budget & Share Insurance Fund': r'share insurance|ncusif|ncua budget|central liquidity',
    'Interchange': r'interchange|swipe fee|routing mandate|durbin',
    'Payments': r'fednow|real.?time payments|faster payments|payments system|stablecoin|digital dollar|\bcbdc\b|earned wage',
    'Technology & Emerging Issues': r'fintech|artificial intelligence|\bai\b|crypto|digital asset|innovation',
    'Fraud Prevention': r'fraud|scam|elder financial|regulation e\b|zelle|p2p payment',
    'Data Privacy & Cybersecurity': r'data breach|data privacy|data security|cyber|gramm.?leach',
    'Charter Modernization & Governance': r'charter|de novo|governance',
    'Defense Credit Union Issues': r'military lending|defense credit union|military banking|military installation|servicemember',
    'Field of Membership': r'field of membership|common bond|underserved area',
    'CDFI Fund': r'\bcdfi\b|community development financial',
    'CFPB Issues & Structural Reform': r'\bcfpb\b|consumer financial protection|section 1071|section 1033|small business lending rule|open banking|overdraft|(?:bank|card|cfpb|financial|lender|account|deposit)[\s\S]{0,80}(?:junk|late) fees?|(?:junk|late) fees?[\s\S]{0,80}(?:bank|card|cfpb|financial|lender|account|deposit)',
    'Credit Card & Consumer-Fee Mandates': r'credit card competition|\bccca\b|credit card fee|credit card mandate|card late fee',
    'Telephone Consumer Protection Act': r'\btcpa\b|telephone consumer protection|robocall',
    'Member Business Lending': r'member business lending|mbl cap|small.?dollar loan|business loan',
    'Mortgage Lending & Housing': r'mortgage|housing|trigger lead|\bhmda\b|federal home loan bank|gse',
    'Credit Union Tax Status': r'tax.?exempt|tax exemption|tax status|credit union tax|don.?t tax my credit union',
    COMPETITIVE: r'big bank|megabank|wall street bank|community bank|bank consolidation|industrial loan|de novo charter|bank lobby',
    GENERAL: r'credit union',
}
_RX = {k: re.compile(v, re.I) for k, v in RAW_PATTERNS.items()}

# Applied only to an otherwise-General item, so these broad words retain a CU
# context and do not turn generic congressional content into policy evidence.
_GENERAL_SUBJECT = {
    'Field of Membership': re.compile(r'underserved|financial inclusion|financial access|access to financial services|rural communit', re.I),
    'Member Business Lending': re.compile(r'small business|entrepreneur|business owner|commercial lending', re.I),
    'Mortgage Lending & Housing': re.compile(r'homebuyer|homeownership|home owner|affordable housing|housing market', re.I),
    'Fraud Prevention': re.compile(r'fraud|scam|identity theft', re.I),
    'Data Privacy & Cybersecurity': re.compile(r'privacy|cyber|data security|data breach', re.I),
    'Payments': re.compile(r'payment|transaction|money transfer', re.I),
    'Credit Union Tax Status': re.compile(r'tax', re.I),
}


def normalized_text(text):
    text = re.sub(r'https?://\S+', '', str(text or '').lower())
    return re.sub(r'[^a-z0-9]', '', text)[:120]


def route_raw_categories(text, declared=None):
    """Route an item to raw-sheet categories using one shared rule set."""
    text = str(text or '')
    declared = [str(c).strip() for c in (declared or []) if str(c).strip()]
    specific_declared = [c for c in declared if c in RAW_TO_STANCE or c == COMPETITIVE]
    if specific_declared:
        return list(dict.fromkeys(specific_declared))
    strict = [c for c, rx in _RX.items() if c not in (GENERAL,) and rx.search(text)]
    if strict:
        return list(dict.fromkeys(strict))
    general_context = GENERAL in declared or _RX[GENERAL].search(text)
    if not general_context:
        return []
    broad = [c for c, rx in _GENERAL_SUBJECT.items() if rx.search(text)]
    return list(dict.fromkeys(broad)) if broad else [GENERAL]


def normalize_signed_extrema(values):
    """Normalize one policy domain while retaining relative magnitude on each side of zero.

    The media blend's p80 scaling makes press and social components commensurable.  This second,
    domain-level transform has a different job: it maps the strongest observed pro/anti values to
    +1/-1 without saturating every already-large raw value at those endpoints.
    """
    clean = {member: float(value or 0.0) for member, value in values.items()}
    pmax = max((value for value in clean.values() if value > 0.0), default=0.0)
    nmax = abs(min((value for value in clean.values() if value < 0.0), default=0.0))
    return {
        member: (value / pmax if value > 0.0 and pmax
                 else value / nmax if value < 0.0 and nmax
                 else 0.0)
        for member, value in clean.items()
    }


def general_exclusion_ledger(values):
    """Return nonzero General-CU evidence as an explicit, non-scoring audit ledger."""
    return {
        member: {
            'general': float(value),
            'applied_to_policy_domains': False,
            'reason': 'residual General Credit Union evidence has no evidenced policy domain',
        }
        for member, value in values.items() if abs(float(value or 0.0)) > 1e-12
    }
