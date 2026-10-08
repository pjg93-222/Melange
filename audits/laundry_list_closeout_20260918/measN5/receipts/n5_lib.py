# -*- coding: utf-8 -*-
"""N5 shared read-only loaders.  Nothing under fec/ is imported (import == execution).

Rule transcriptions are REUSED from lane F1's already-self-checked f1_lib.py
(WORKTREE\\audits\\laundry_list_closeout_20260918\\F1\\receipts\\f1_lib.py, byte-compared
against LIVE\\fec\\bill_rules.py and LIVE\\fec\\members\\member_identity.py by
F1\\receipts\\f1_selfcheck.py).
"""
import os, sys, json, csv, collections
import openpyxl

F1 = (r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees"
      r"\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\F1\receipts")
if F1 not in sys.path:
    sys.path.insert(0, F1)
import f1_lib as F  # noqa: E402

ROOT = F.ROOT
P = lambda *a: os.path.join(ROOT, *a)
SCRATCH = (r"C:\Users\pgoff\AppData\Local\Temp\claude"
           r"\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad"
           r"\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\measN5")

ROLE_SHEETS = ('Sponsor Interactions', 'Original Co-Sponsor Interaction', 'Co-Sponsor Interactions')
SEL_ARCHIVE = 'congress_bills_archive_20260825_115305.xlsx'
OLD_ARCHIVE = 'congress_bills_archive_20260624_115822.xlsx'


def norm_bill(v):
    """laneC q2b_fork_size.norm: strip ALL whitespace, uppercase."""
    import re
    return re.sub(r'\s+', '', str(v or '')).upper()


def cong(v):
    return F.congress_of(v)


def role(v):
    return F.canonical_role(v)


def key4(member, bill, congress, rolev):
    """laneC q2b_fork_size.key -- RAW member string, NOT resolved."""
    return (str(member or '').strip(), norm_bill(bill), cong(congress), role(rolev))


def sheet_rows(path, sheet):
    """Rows as dicts PLUS the 1-based worksheet row number (append-order evidence)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[sheet]
    it = ws.iter_rows(values_only=True)
    hdr = [str(h) if h is not None else '' for h in next(it)]
    out = []
    n = 1
    for r in it:
        n += 1
        d = dict(zip(hdr, r))
        d['__row__'] = n
        d['__sheet__'] = sheet
        out.append(d)
    wb.close()
    return out


def workbook_role_rows():
    out = []
    for sn in ROLE_SHEETS:
        out.extend(sheet_rows(P('Moneyball Main Version - Blended.xlsx'), sn))
    return out


def archive_rows(which='sel'):
    return sheet_rows(P(SEL_ARCHIVE if which == 'sel' else OLD_ARCHIVE), 'All Bills')


def sentinel_all_rows():
    return sheet_rows(P('Sentinel Bill Ledger.xlsx'), 'Sentinel Bill Ledger')


def sentinel_verified_rows():
    """build_archive_legislative.sentinel_scoring_mask applied row-wise."""
    def t(r, n):
        return str(r.get(n) or '').strip().lower()
    return [r for r in sentinel_all_rows()
            if t(r, 'Scoring Eligible') in {'true', '1', 'yes'}
            and t(r, 'Review Status') == 'verified'
            and t(r, 'Record Type') == 'membership']


def manual_rows():
    with open(P('manual_bill_evidence.csv'), encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def roster():
    data = json.load(open(P('data', 'engine', 'congestion.json'), encoding='utf-8'))
    names = [m['member'] for m in data]
    bios = {m['member']: m.get('bioguide') for m in data}
    return names, bios


def resolver():
    names, bios = roster()
    return F.Resolver(names, bios), names, bios


def routing_audit():
    return json.load(open(P('legislation_routing_audit.json'), encoding='utf-8'))


def bill_live():
    return json.load(open(P('bill_repository_live.json'), encoding='utf-8'))


def repo_key(bill, congress):
    """Same identity the desk template's billIdentity() and the repository use:
    '<congress>:<type>:<number>'.  Transcribed from
    LIVE\\fec\\surfaces\\templates\\make_member_desk_00.tpl:1951-1956 (billIdentity)."""
    import re
    raw = norm_bill(bill).replace('.', '')
    raw = re.sub(r'[^A-Z0-9]', '', raw)
    m = re.match(r'^(HCONRES|SCONRES|HJRES|SJRES|HRES|SRES|HR|S)(\d+)$', raw)
    if not m:
        return None
    c = cong(congress)
    if not c:
        return None
    return '%s:%s:%d' % (c, m.group(1).lower(), int(m.group(2)))


def shipped_desk_ledger():
    with open(os.path.join(SCRATCH, 'desk_ledger_shipped.json'), encoding='utf-8') as fh:
        return json.load(fh)
