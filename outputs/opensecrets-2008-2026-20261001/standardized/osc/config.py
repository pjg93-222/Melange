"""Scope registry loading, cycle/year constants and URL builders (single place where source URL patterns live)."""
from __future__ import annotations
import json
from pathlib import Path
from urllib.parse import urlencode

from .util import BASE

PKG_DIR = Path(__file__).resolve().parent
ROOT = PKG_DIR.parent
DEFAULT_SCOPES = ROOT / 'scopes.json'
DEFAULT_OUT = ROOT / 'csv'
DEFAULT_DATA = Path('C:/melange-data/forecast-redesign-20261001-review/standardized-collector/data')
DEFAULT_STATE = Path('C:/melange-data/forecast-redesign-20261001-review/standardized-collector/state')
DEFAULT_OFFLINE_LOBBY = Path('C:/melange-data/forecast-redesign-20261001-review/source-recovery/lobbying')
DEFAULT_ROSTER = Path('C:/melange-data/forecast-redesign-20261001-review/roster-discovery/mentat_roster_organizations.csv')

FIRST_CYCLE, LAST_CYCLE = 2008, 2026
CYCLES = list(range(FIRST_CYCLE, LAST_CYCLE + 1, 2))
YEARS = list(range(FIRST_CYCLE, LAST_CYCLE + 1))
PARTIAL_CYCLE = 2026
OFFICES = ['Presidential', 'House', 'Senate']
CHAMBERS = ['House', 'Senate']

# Modern lobbying 'about this data' note lives on the top-industries page.
LOBBY_ASOF_URL = f'{BASE}/federal-lobbying/top-industries?year=2026'
TAXONOMY_URL = f'{BASE}/industries/slist'
COST_URL = f'{BASE}/elections-overview/cost-of-election?infl=N'


def is_pres_year(cycle):
    """Presidential election cycles are the multiples of 4 (2008, 2012, ... 2024, 2028)."""
    return int(cycle) % 4 == 0


def apply_periods(d):
    """Honour the registry's requested periods (scopes.json `cycles` / `lobbying_years`): rebuilds CYCLES / YEARS in place so every
    module that reads ``C.CYCLES`` / ``C.YEARS`` sees the configured range. Contribution cycles are even years (step 2 only)."""
    global FIRST_CYCLE, LAST_CYCLE, CYCLES, YEARS, PARTIAL_CYCLE
    cy, ly = d.get('cycles') or {}, d.get('lobbying_years') or {}
    first, last, step = int(cy.get('first', FIRST_CYCLE)), int(cy.get('last', LAST_CYCLE)), int(cy.get('step', 2))
    if step != 2 or first % 2 or last % 2 or first > last:
        raise ValueError(f'unsupported cycles config {cy}: election cycles are even years, step 2, first<=last')
    yf, yl = int(ly.get('first', first)), int(ly.get('last', last))
    if yf > yl:
        raise ValueError(f'unsupported lobbying_years config {ly}')
    FIRST_CYCLE, LAST_CYCLE, CYCLES = first, last, list(range(first, last + 1, 2))
    YEARS = list(range(yf, yl + 1))
    PARTIAL_CYCLE = int(cy.get('partial_cycle', last))


def load_scopes(path=None):
    d = json.loads(Path(path or DEFAULT_SCOPES).read_text(encoding='utf-8'))
    ids = [s['scope_id'] for s in d['scopes']]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate scope_id in scope registry')
    apply_periods(d)
    return d


def load_roster(path):
    """Read-only Mentat roster CSV (80 current top-10 company names per canonical workbook). [] when disabled/missing."""
    import csv
    if not path or not Path(path).exists():
        return []
    with open(path, encoding='utf-8-sig', newline='') as fh:
        return [r for r in csv.DictReader(fh) if (r.get('original_company_name') or '').strip()]


def mapped(scopes):
    """Scopes that carry a published OpenSecrets code."""
    return [s for s in scopes if s.get('opensecrets_code')]


def lobby_modern(scopes):
    return [s for s in scopes if s.get('lobby_category_id')]


# ---- URL builders -------------------------------------------------------------------------
def u_overview(cycle):
    return f'{BASE}/elections-overview?{urlencode({"cycle": cycle})}'


def u_pac_breakdown(cycle):
    return f'{BASE}/political-action-committees-pacs/industry-breakdown/{cycle}'


def u_industry_detail(code, cycle):
    return f'{BASE}/political-action-committees-pacs/industry-detail/{code}/{cycle}'


def u_pac_recipients(slug, pac_id, cycle):
    mid = f'{slug}/' if slug else ''
    return f'{BASE}/political-action-committees-pacs/{mid}{pac_id}/candidate-recipients/{cycle}'


def u_legacy_totals(code, cycle=2026):
    return f'{BASE}/industries/totals?{urlencode({"ind": code, "cycle": cycle})}'


def u_legacy_contrib(code, cycle):
    return f'{BASE}/industries/contrib?{urlencode({"ind": code, "cycle": cycle})}'


def u_legacy_summary(code, cycle, chamber):
    return f'{BASE}/industries/summary?{urlencode({"ind": code, "cycle": cycle, "mem": "N", "recipdetail": chamber[0]})}'


def u_legacy_lobbying(code, cycle):
    return f'{BASE}/industries/lobbying?{urlencode({"ind": code, "cycle": cycle})}'


def u_lobby_page(slug, category_id, year):
    return f'{BASE}/federal-lobbying/industries/{slug}?{urlencode({"category_id": category_id, "year": year})}'


def u_lobby_chunk(slug, category_id, chunk, year):
    q = {'category_id': category_id, 'chunk': chunk, 'view': 'client_parent', 'view_totals_by': 'client_parent', 'year': year}
    return f'{BASE}/federal-lobbying/industries/{slug}/summary/content?{urlencode(q)}'


def u_client_split(slug, client_id, year):
    q = {'chunk': 'cycle_snapshot', 'client_id': client_id, 'cycle': year}
    return f'{BASE}/federal-lobbying/clients/{slug}/summary/content?{urlencode(q)}'


def u_org_search(name):
    return f'{BASE}/search?{urlencode({"q": name, "type": "orgs"})}'


def u_org_totals(slug, org_id):
    return f'{BASE}/orgs/{slug}/totals?{urlencode({"id": org_id})}'
