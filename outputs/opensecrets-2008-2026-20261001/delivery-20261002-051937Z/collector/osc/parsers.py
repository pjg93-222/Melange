"""Pure parsers: raw page bytes/text -> plain dicts. No network, no file writes.

Pitfalls handled (each has a unit test):
* Paginated DataTables render ~10/25 rows but carry the FULL set in the ``data-collection`` JSON attribute.
* Cell HTML contains hidden sort labels (<span class="hiddentext">Surname, First</span>) and <b> tags.
* Header keys can have trailing whitespace ("To Democrats ").
* Counts arrive as int or '2,795'; money may be negative (refund nets) and is never coerced to zero.
* Missing/blank cells -> None, never 0. A published "$0" stays 0.
* Served cycle is read from the page (selected menu option / heading), never assumed from the request.
"""
from __future__ import annotations
import html as htmllib
import json, re
from bs4 import BeautifulSoup

from .util import count, money, normalized, pct

MONTHS = 'January|February|March|April|May|June|July|August|September|October|November|December'
RELEASE_RE = re.compile(r'released\b[^.]{0,90}?\bon\s+((?:%s)\s+\d{1,2},\s+\d{4})' % MONTHS)
HIDDEN_RE = re.compile(r'<span[^>]*class="[^"]*hiddentext[^"]*"[^>]*>.*?</span>', re.S | re.I)
PARTY_RE = re.compile(r'\(([A-Za-z0-9]+)(?:-([A-Za-z .]+))?\)\s*$')


def soup_of(body) -> BeautifulSoup:
    if isinstance(body, bytes):
        body = body.decode('utf-8', errors='replace')
    return BeautifulSoup(body, 'html.parser')


def clean_text(cell) -> str:
    """Cell (possibly HTML) -> visible text without hidden sort labels or tags."""
    if cell is None:
        return ''
    s = str(cell)
    if '<' in s:
        s = HIDDEN_RE.sub('', s)
        s = BeautifulSoup(s, 'html.parser').get_text(' ', strip=True)
    return re.sub(r'\s+', ' ', htmllib.unescape(s)).strip()


def hidden_label(cell) -> str:
    m = re.search(r'class="[^"]*hiddentext[^"]*"[^>]*>(.*?)</span>', str(cell or ''), re.S | re.I)
    return htmllib.unescape(m.group(1)).strip() if m else ''


def first_href(cell) -> str:
    m = re.search(r'href="([^"]+)"', str(cell or ''))
    return htmllib.unescape(m.group(1)) if m else ''


def party_from_label(label: str):
    """'Tony Gonzales (R-Texas)' -> ('R','Texas'); '(3-UT)' -> ('3','UT'); no suffix -> ('','')."""
    m = PARTY_RE.search(label or '')
    return (m.group(1), (m.group(2) or '').strip()) if m else ('', '')


def party_group(code: str) -> str:
    c = (code or '').upper()
    return 'D' if c == 'D' else 'R' if c == 'R' else ('Unclassified' if c == '' else 'Other')


# ---- generic page metadata ------------------------------------------------------------------
def page_meta(soup: BeautifulSoup) -> dict:
    text = soup.get_text(' ', strip=True)
    sel_cycle, menu = '', []
    for sel in soup.select('select'):
        key = (sel.get('name') or '') + ' ' + (sel.get('id') or '')
        if re.search(r'cycle|year', key):
            opt = sel.select_one('option[selected]')
            if opt:
                sel_cycle = opt.get_text(strip=True)
                menu = [o.get_text(strip=True) for o in sel.select('option')]
                break
    dates = RELEASE_RE.findall(text)
    h1s = [h.get_text(' ', strip=True) for h in soup.select('h1')]
    m = (re.search(r'(?:Based on|All the numbers)[^.]{0,200}?released\b[^.]{0,120}?\bon\s+(?:%s)\s+\d{1,2},\s+\d{4}' % MONTHS, text)
         or re.search(r'released\b[^.]{0,120}?\bon\s+(?:%s)\s+\d{1,2},\s+\d{4}' % MONTHS, text))
    cov = re.search(r'cycle runs from ((?:%s)\s+\d{1,2},\s+\d{4}) to ((?:%s)\s+\d{1,2},\s+\d{4})' % (MONTHS, MONTHS), text)
    title = soup.title.get_text(' ', strip=True) if soup.title else ''
    return {
        'title': title,
        'h1': h1s[-1] if h1s else '',
        'selected_cycle': sel_cycle,
        'cycle_menu': menu,
        'release_dates': list(dict.fromkeys(dates)),
        'release_text': m.group(0).strip() if m else '',
        'cycle_coverage': f'{cov.group(1)} to {cov.group(2)}' if cov else '',
        'soft_block': bool(re.search(r'just a moment|access denied|attention required', title, re.I)),
    }


def iso_date(text: str) -> str:
    from datetime import datetime
    try:
        return datetime.strptime(text.strip(), '%B %d, %Y').date().isoformat()
    except (ValueError, AttributeError):
        return ''


def extract_tables(soup: BeautifulSoup) -> list:
    """Every <table> as {index, heading, header, rows(list of dict), source, html_rows, collection_rows}.
    The data-collection JSON (full data) wins over the visible, paginated tbody."""
    out = []
    for i, t in enumerate(soup.find_all('table')):
        head = t.find_previous(['h1', 'h2', 'h3', 'h4'])
        heading = head.get_text(' ', strip=True) if head else ''
        trs = t.select('tbody tr') or t.select('tr')
        html_header = [c.get_text(' ', strip=True) for c in t.select('thead th')]
        if not html_header and t.select('tr'):
            first = t.select('tr')[0]
            if first.select('th'):
                html_header = [c.get_text(' ', strip=True) for c in first.select('th')]
        info = {'index': i, 'heading': heading, 'header': [h.strip() for h in html_header], 'rows': [], 'source': 'html',
                'html_rows': len(trs), 'collection_rows': None, 'classes': t.get('class') or []}
        raw = t.get('data-collection')
        parsed = None
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                info['collection_error'] = 'unparseable_data_collection'
        if isinstance(parsed, list):
            info['source'] = 'data-collection'
            info['collection_rows'] = len(parsed)
            info['rows'] = [{(k or '').strip(): v for k, v in r.items()} for r in parsed if isinstance(r, dict)]
            if not info['header'] and info['rows']:
                info['header'] = list(info['rows'][0].keys())
        else:
            rows = []
            hdr = info['header']
            for tr in trs:
                cells = tr.select('th,td')
                if not cells:
                    continue
                vals = [c.decode_contents() if c.find('a') else c.get_text(' ', strip=True) for c in cells]
                rows.append(dict(zip(hdr, vals)) if hdr and len(vals) == len(hdr) else {f'col{j}': v for j, v in enumerate(vals)})
            info['rows'] = rows
        out.append(info)
    return out


def _col(row: dict, *names):
    for n in names:
        if n in row:
            return row[n]
    low = {k.lower().strip(): v for k, v in row.items()}
    for n in names:
        if n.lower().strip() in low:
            return low[n.lower().strip()]
    return None


def _headline_total(soup):
    """The big '$x' h2 that sits directly above the 'Total ...' caption h3 (the page also has an unrelated donate-banner h2.f-strata-title)."""
    for h3 in soup.find_all('h3'):
        if re.match(r'Total\b', h3.get_text(' ', strip=True)):
            h2 = h3.find_previous_sibling('h2')
            if h2 is not None and re.fullmatch(r'-?\$[\d,]+', h2.get_text(strip=True)):
                return money(h2.get_text(strip=True))
    return None


def _served(meta: dict):
    return int(meta['selected_cycle']) if meta['selected_cycle'].isdigit() else None


# ---- national overview ---------------------------------------------------------------------
OFFICE_RE = re.compile(r'^(Presidential|House|Senate)\b')


def selected_option(sel):
    """Selected option of a single-select <select>: the option with `selected`, else the first enabled option (HTML default for a
    single select with size 1). Returns label/value/how so the caller can corroborate - never a hard-coded assumption."""
    opts = sel.select('option')
    chosen = next((o for o in opts if o.has_attr('selected')), None)
    how = 'selected_attribute'
    if chosen is None:
        chosen = next((o for o in opts if not o.has_attr('disabled')), None)
        how = 'first_enabled_option_default'
    if chosen is None:
        return {'label': '', 'value': '', 'how': 'no_options', 'labels': []}
    return {'label': chosen.get_text(' ', strip=True), 'value': chosen.get('value', ''), 'how': how,
            'labels': [o.get_text(' ', strip=True) for o in opts]}


def _query_param(value, key):
    m = re.search(r'[?&]%s=([^&#]*)' % re.escape(key), value or '')
    return m.group(1) if m else ''




def parse_overview(body, requested_cycle: int) -> dict:
    soup = soup_of(body)
    meta = page_meta(soup)
    text = soup.get_text(' ', strip=True)
    served = meta['selected_cycle']
    if not served:
        m = re.search(r'numbers on this page are for the (\d{4}) election cycle', text)
        served = m.group(1) if m else ''
    # actual controls: candidate-universe (select_type) and display (display_type) as served, with default fallback + caption corroboration
    ctl = {}
    for key, name in (('type', 'select_type'), ('display', 'display_type')):
        sel = soup.select_one(f'select[name={name}]')
        ctl[key] = selected_option(sel) if sel is not None else {'label': '', 'value': '', 'how': 'control_absent', 'labels': []}
    type_code = _query_param(ctl['type']['value'], 'type')
    display_code = _query_param(ctl['display']['value'], 'display')
    # the option VALUE is a navigation URL (it encodes display=T&type=A for the first option, which is both menus' served default)
    rows, offices, captions = [], [], {}
    for h in soup.find_all('h2'):
        hm = OFFICE_RE.match(h.get_text(' ', strip=True))
        if hm and h.get_text(' ', strip=True) in ('Presidential', 'House', 'Senate'):
            p = h.find_next('p')
            captions[hm.group(1)] = p.get_text(' ', strip=True) if p is not None else ''
    for t in extract_tables(soup):
        om = OFFICE_RE.match(t['heading'] or '')
        if not om or 'Total From PACs' not in ' '.join(t['header']):
            continue
        office = om.group(1)
        offices.append(office)
        for r in t['rows']:
            rows.append({'office': office, 'party': (_col(r, 'Party') or '').strip(),
                         'n_candidates': count(_col(r, 'No. of Cands')),
                         'total_raised_usd': money(_col(r, 'Total Raised')), 'total_spent_usd': money(_col(r, 'Total Spent')),
                         'cash_on_hand_usd': money(_col(r, 'Total Cash on Hand')),
                         'from_pacs_usd': money(_col(r, 'Total From PACs')), 'from_individuals_usd': money(_col(r, 'Total From Individuals')),
                         'table_source': t['source']})
    caption_all = {o: bool(re.match(r'Financial activity for all\s', c, re.I)) for o, c in captions.items()}
    universe_ok = (type_code == 'A' and display_code == 'T' and bool(offices) and all(caption_all.get(o) for o in offices))
    reasons = []
    if type_code != 'A':
        reasons.append(f"candidate universe control is {ctl['type']['label']!r} (type={type_code!r}), not All candidates")
    if display_code != 'T':
        reasons.append(f"display control is {ctl['display']['label']!r} (display={display_code!r}), not Display totals")
    for o in offices:
        if not caption_all.get(o):
            reasons.append(f"{o} caption does not read 'for all ... candidates': {captions.get(o, '')[:60]!r}")
    return {'meta': meta, 'requested_cycle': requested_cycle, 'served_cycle': int(served) if served.isdigit() else None,
            'offices': offices, 'rows': rows, 'controls': ctl, 'type_code': type_code, 'display_code': display_code,
            'captions': captions, 'universe_ok': universe_ok, 'universe_reject_reason': '; '.join(reasons),
            'type_selected': ctl['type']['label'], 'display_selected': ctl['display']['label'],
            'controls_basis': f"type:{ctl['type']['how']}; display:{ctl['display']['how']}"}


def parse_cost_of_election(body) -> dict:
    soup = soup_of(body)
    infl = soup.select_one('input[name=infl]')
    nominal = bool(infl is not None and infl.get('value') == 'N' and not infl.has_attr('checked'))
    rows = []
    for t in extract_tables(soup):
        if [h.strip() for h in t['header'][:4]] != ['Cycle', 'Total Cost of Election', 'Congressional Races', 'Presidential Race']:
            continue
        for r in t['rows']:
            m = re.fullmatch(r'(\d{4})(\*?)', clean_text(_col(r, 'Cycle')))
            if not m:
                continue
            total, cong, pres = (money(_col(r, k)) for k in ('Total Cost of Election', 'Congressional Races', 'Presidential Race'))
            rows.append({'cycle': int(m.group(1)), 'asterisk': bool(m.group(2)), 'total_usd': total, 'congressional_usd': cong, 'presidential_usd': pres})
    return {'meta': page_meta(soup), 'has_infl_input': infl is not None, 'infl_value': infl.get('value') if infl is not None else None,
            'infl_checked': bool(infl is not None and infl.has_attr('checked')), 'nominal_verified': nominal, 'rows': rows}


# ---- PAC pages -----------------------------------------------------------------------------
def parse_pac_breakdown(body, requested_cycle: int) -> dict:
    soup = soup_of(body)
    meta = page_meta(soup)
    rows = []
    for t in extract_tables(soup):
        if 'Total to Democrats' not in ' '.join(t['header']):
            continue
        for r in t['rows']:
            cell = _col(r, 'Name')
            href = first_href(cell)
            hm = re.search(r'industry-detail/([A-Za-z0-9]+)/(\d{4})', href)
            tot, d, rep = money(_col(r, 'Total')), money(_col(r, 'Total to Democrats')), money(_col(r, 'Total to Republicans'))
            rows.append({'code': hm.group(1) if hm else '', 'name': clean_text(cell), 'classification': clean_text(_col(r, 'Classification')),
                         'href_cycle': int(hm.group(2)) if hm else None, 'detail_url': href,
                         'total_usd': tot, 'to_democrats_usd': d, 'to_republicans_usd': rep,
                         'other_party_residual_usd': (tot - d - rep) if None not in (tot, d, rep) else None})
    return {'meta': meta, 'requested_cycle': requested_cycle, 'served_cycle': _served(meta), 'rows': rows}


def parse_industry_detail(body, code: str, requested_cycle: int) -> dict:
    soup = soup_of(body)
    meta = page_meta(soup)
    head = {}
    for title, key in (('Number of PACs', 'n_pacs'), ('To Democrats', 'to_democrats_usd'), ('To Republicans', 'to_republicans_usd')):
        for h in soup.find_all(['h2', 'h3']):
            if h.get_text(' ', strip=True) == title:
                val = h.find_previous_sibling(['h2', 'h3'])
                if val is not None:
                    head[key] = count(val.get_text(strip=True)) if key == 'n_pacs' else money(val.get_text(strip=True))
                break
    head['total_usd'] = _headline_total(soup)
    pacs = []
    for t in extract_tables(soup):
        if 'PAC Name' not in ' '.join(t['header']):
            continue
        for r in t['rows']:
            cell = _col(r, 'PAC Name')
            href = first_href(cell)
            hm = re.search(r'/political-action-committees-pacs/(?:([^/]+)/)?(C\d{8})/summary/(\d{4})', href)   # category pages omit the slug
            pacs.append({'pac_name': clean_text(cell), 'pac_id': hm.group(2) if hm else '', 'slug': (hm.group(1) or '') if hm else '',
                         'href_cycle': int(hm.group(3)) if hm else None, 'summary_url': href,
                         'affiliate': clean_text(_col(r, 'Affiliate')), 'lean': clean_text(_col(r, 'Lean')),
                         'total_usd': money(_col(r, 'Total')), 'to_democrats_usd': money(_col(r, 'To Democrats')),
                         'to_republicans_usd': money(_col(r, 'To Republicans')), 'table_source': t['source']})
        break
    return {'meta': meta, 'code': code, 'requested_cycle': requested_cycle, 'served_cycle': _served(meta),
            'headline': head, 'pacs': pacs, 'detail_title': meta['title']}


def parse_pac_recipients(body, pac_id: str, requested_cycle: int) -> dict:
    soup = soup_of(body)
    meta = page_meta(soup)
    head = {'total_usd': _headline_total(soup)}
    for cls, key in (('democrat', 'to_democrats_usd'), ('republican', 'to_republicans_usd')):
        h3 = soup.select_one(f'h3.f-strata-title.{cls}')
        head[key] = money(h3.get_text(strip=True)) if h3 else None
    chamber_summary, recipients, tables_seen = {}, [], []
    for t in extract_tables(soup):
        hm = re.match(r'(House|Senate|Presidential|President)\b', t['heading'] or '')
        chamber = ('Presidential' if hm.group(1).startswith('President') else hm.group(1)) if hm else ''
        if not chamber:
            continue
        if 'Candidate' in ' '.join(t['header']) and 'Total' in ' '.join(t['header']):
            tables_seen.append(chamber)
            for r in t['rows']:
                cell = _col(r, 'Candidate')
                name = clean_text(cell)
                code, state = party_from_label(name)
                recipients.append({'chamber': chamber, 'candidate': name, 'sort_name': hidden_label(cell), 'party_code': code,
                                   'party_group': party_group(code), 'state': state, 'candidate_url': first_href(cell),
                                   'amount_usd': money(_col(r, 'Total')), 'table_source': t['source'],
                                   'html_rows_visible': t['html_rows'], 'collection_rows': t['collection_rows']})
        else:  # small 'Republicans $x pct / Democrats $y pct' summary table
            for r in t['rows']:
                vals = [clean_text(v) for v in r.values()]
                if len(vals) >= 2 and re.match(r'(Republicans?|Democrats?|Others?|Independents?)', vals[0], re.I):
                    grp = 'R' if vals[0].lower().startswith('rep') else 'D' if vals[0].lower().startswith('dem') else 'Other'
                    chamber_summary[f'{chamber}|{grp}'] = money(vals[1])
    return {'meta': meta, 'pac_id': pac_id, 'requested_cycle': requested_cycle, 'served_cycle': _served(meta),
            'headline': head, 'chamber_summary': chamber_summary, 'recipients': recipients, 'tables_seen': tables_seen,
            'pac_title': meta['title']}


# ---- legacy industry pages --------------------------------------------------------------------
def parse_legacy_totals(body, code: str) -> dict:
    soup = soup_of(body)
    meta = page_meta(soup)
    rows = []
    for t in extract_tables(soup):
        if t['header'][:1] != ['Election Cycle'] or 'Total Contributions' not in ' '.join(t['header']):
            continue
        for r in t['rows']:
            cy = clean_text(_col(r, 'Election Cycle'))
            if not cy.isdigit():
                continue
            rows.append({'cycle': int(cy), 'total_usd': money(_col(r, 'Total Contributions')),
                         'individual_usd': money(_col(r, 'Contributions from Individuals')),
                         'pac_usd': money(_col(r, 'Contributions from PACs')), 'soft_outside_usd': money(_col(r, 'Soft/Outside Money')),
                         'democrat_usd': money(_col(r, 'Contributions to Democrats')), 'republican_usd': money(_col(r, 'Contributions to Republicans')),
                         'democrat_pct': pct(_col(r, 'Percentage to Democrats')), 'republican_pct': pct(_col(r, 'Percentage to Republicans'))})
    return {'meta': meta, 'code': code, 'rows': rows, 'title': meta['title'], 'latest_cycle': max((r['cycle'] for r in rows), default=None)}


def parse_legacy_contrib(body, code: str, requested_cycle: int) -> dict:
    soup = soup_of(body)
    meta = page_meta(soup)
    text = soup.get_text(' ', strip=True)
    tm = re.search(r'Total Contributions, \d{4}-(\d{4}):\s*(\$[\d,]+)', text)
    rows = []
    for t in extract_tables(soup):
        if t['header'][:2] != ['Rank', 'Contributor']:
            continue
        for r in t['rows']:
            rank = count(_col(r, 'Rank'))
            if rank is None:
                continue
            name = clean_text(_col(r, 'Contributor'))
            rows.append({'rank': rank, 'organisation': name, 'organisation_normalized': normalized(name),
                         'total_usd': money(clean_text(_col(r, 'Grand Total'))),
                         'candidates_parties_usd': money(clean_text(_col(r, 'Total to Candidates & Parties'))),
                         'democrat_usd': money(clean_text(_col(r, 'Dems'))), 'republican_usd': money(clean_text(_col(r, 'Repubs'))),
                         'outside_groups_usd': money(clean_text(_col(r, 'Total to Outside Spending Groups'))),
                         'liberal_groups_usd': money(clean_text(_col(r, 'Liberal Groups'))),
                         'conservative_groups_usd': money(clean_text(_col(r, 'Conservative Groups'))),
                         'lean': clean_text(_col(r, 'Lean')), 'table_source': t['source']})
    return {'meta': meta, 'code': code, 'requested_cycle': requested_cycle,
            'served_cycle': _served(meta) or (int(tm.group(1)) if tm else None),
            'industry_total_usd': money(tm.group(2)) if tm else None, 'rows': rows, 'title': meta['title']}


def parse_legacy_summary(body, code: str, requested_cycle: int, chamber: str) -> dict:
    soup = soup_of(body)
    meta = page_meta(soup)
    rows = []
    for t in extract_tables(soup):
        if t['header'][-2:] != ['State', 'Amount']:
            continue
        for r in t['rows']:
            cell = _col(r, 'Representative') or next(iter(r.values()), '')
            label = clean_text(cell)
            pcode, st = party_from_label(label)
            rows.append({'recipient': label, 'party_code': pcode, 'party_group': party_group(pcode), 'state_label': clean_text(_col(r, 'State')),
                         'state_code': st, 'amount_usd': money(_col(r, 'Amount')), 'recipient_url': first_href(cell),
                         'table_source': t['source'], 'html_rows_visible': t['html_rows'], 'collection_rows': t['collection_rows']})
        break
    # served chamber / candidate universe: URL parameters are NOT proof. Evidence = the cycle menu's option values (they carry the served
    # mem/recipdetail), the recipient-type menu when an option is marked selected, and the table heading 'to US <chamber> candidates'.
    cyc_val, type_val, type_label = '', '', ''
    for sel in soup.select('select'):
        opts = sel.select('option')
        if not any('recipdetail=' in (o.get('value') or '') for o in opts):
            continue
        chosen = next((o for o in opts if o.has_attr('selected')), None)
        if all(re.fullmatch(r'\d{4}|All', o.get_text(strip=True)) for o in opts):
            cyc_val = chosen.get('value', '') if chosen is not None else ''
        elif chosen is not None:
            type_val, type_label = chosen.get('value', ''), chosen.get_text(' ', strip=True)
    served_mem = _query_param(cyc_val, 'mem') or _query_param(type_val, 'mem')
    served_recip = _query_param(cyc_val, 'recipdetail') or _query_param(type_val, 'recipdetail')
    hm = re.search(r'to US (House|Senate) candidates', ' '.join(h.get_text(' ', strip=True) for h in soup.select('h3')))
    menu_chamber = {'H': 'House', 'S': 'Senate'}.get(served_recip)
    served_chamber = menu_chamber or (hm.group(1) if hm else None)
    if not type_label and menu_chamber:   # no option marked selected in the server HTML: label the served universe from the matching menu option
        for sel in soup.select('select'):
            for o in sel.select('option'):
                v = o.get('value') or ''
                if f'recipdetail={served_recip}' in v and f'mem={served_mem}' in v and not re.fullmatch(r'\d{4}|All', o.get_text(strip=True)):
                    type_label = o.get_text(' ', strip=True)
    agree = bool(menu_chamber and hm and menu_chamber == hm.group(1))
    return {'meta': meta, 'code': code, 'requested_cycle': requested_cycle, 'chamber': chamber, 'served_cycle': _served(meta),
            'rows': rows, 'title': meta['title'], 'served_chamber': served_chamber, 'served_mem': served_mem, 'served_recipdetail': served_recip,
            'served_universe_label': type_label, 'heading_chamber': hm.group(1) if hm else None, 'chamber_evidence_agrees': agree}


def parse_legacy_lobbying(body, code: str, requested_cycle: int) -> dict:
    """Legacy /industries/lobbying: annual chart (FusionChart data-source) + client table for the served cycle."""
    soup = soup_of(body)
    meta = page_meta(soup)
    annual = {}
    for el in soup.select('[data-source]'):
        try:
            data = json.loads(el['data-source'])
        except json.JSONDecodeError:
            continue
        for p in data.get('data', []):
            m = re.fullmatch(r"'(\d{2})", p.get('label', '') or '')
            if m:
                yy = int(m.group(1))
                annual[1900 + yy if yy >= 90 else 2000 + yy] = money(p.get('value'))
    text = soup.get_text(' ', strip=True)
    cm = re.search(r'([\d,]+)\s+Number of Clients', text) or re.search(r'Number of Clients\s+([\d,]+)', text)
    clients = []
    for t in extract_tables(soup):
        if t['header'][:2] != ['Client/Parent Organization', 'Total']:
            continue
        for r in t['rows']:
            clients.append({'client': clean_text(_col(r, 'Client/Parent Organization')), 'spend_usd': money(clean_text(_col(r, 'Total'))),
                            'table_source': t['source']})
        break
    ym = re.search(r'(\d{4}) Total for', text)
    return {'meta': meta, 'code': code, 'requested_cycle': requested_cycle, 'annual': annual,
            'served_year': int(ym.group(1)) if ym else None, 'n_clients': count(cm.group(1)) if cm else None,
            'clients': clients, 'title': meta['title']}


# ---- modern lobbying ---------------------------------------------------------------------------
def parse_lobby_annual(body) -> dict:
    """annual_trends chunk: line-chart options JSON with one value per year (1998-present)."""
    soup = soup_of(body)
    series, out = [], {}
    for el in soup.select('[data-charts--line-chart-options-value]'):
        try:
            opts = json.loads(el['data-charts--line-chart-options-value'])
        except json.JSONDecodeError:
            continue
        series.extend(opts.get('series', []))
    for s in series:
        for p in s.get('data', []):
            cat = str(p.get('category', ''))
            if cat.isdigit():
                out[int(cat)] = money(p.get('value'))
    return {'annual': out, 'series_names': [s.get('name') for s in series], 'series_count': len(series)}


def parse_lobby_main(body, category_id: str, year: int) -> dict:
    """main chunk: headline cards + the Client/Parent table (all clients, plain HTML, no pagination)."""
    soup = soup_of(body)
    text = soup.get_text(' ', strip=True)
    spend = re.search(r'(?:Industry|Sector) spending\s+(\$[\d,]+)', text)
    active = re.search(r'Clients active\s+([\d,]+)', text)
    hy = re.search(r'clients by Client/Parent,\s*(\d{4})', text)
    clients, widget = [], {}
    for t in soup.select('table'):
        trs_all = t.select('tr')
        header = [c.get_text(' ', strip=True) for c in trs_all[0].select('th,td')] if trs_all else []
        trs = t.select('tbody tr') or trs_all[1:]
        if header[:2] == ['Client/Parent', 'Total']:
            for tr in trs:
                tds = tr.select('td,th')
                if len(tds) < 2:
                    continue
                a = tds[0].select_one('a[href]')
                href = a['href'] if a else ''
                cid = re.search(r'client_id=(\d+)', href)
                slug = re.search(r'/federal-lobbying/clients/([^/?]+)', href)
                clients.append({'client': tds[0].get_text(' ', strip=True), 'spend_usd': money(tds[1].get_text(' ', strip=True)),
                                'client_id': cid.group(1) if cid else '', 'client_slug': slug.group(1) if slug else '', 'client_url': href})
        elif header[:2] == ['Client', 'Total spending']:
            tds = trs[0].select('td,th') if trs else []
            if len(tds) >= 2:
                widget = {'label': tds[0].get_text(' ', strip=True), 'spend_usd': money(tds[1].get_text(' ', strip=True))}
    return {'category_id': category_id, 'requested_year': year, 'served_year': int(hy.group(1)) if hy else None,
            'industry_spend_usd': money(spend.group(1)) if spend else None,
            'clients_active': count(active.group(1)) if active else None,
            'clients': clients, 'top_client_widget': widget}


def parse_lobby_heading(body) -> dict:
    """Base industry page: title/h1, selected year and the turbo-frame content URLs the page itself links."""
    text = body.decode('utf-8', 'replace') if isinstance(body, bytes) else body
    soup = BeautifulSoup(text, 'html.parser')
    sel = soup.select_one('select#industry-summary-year option[selected]') or soup.select_one('select[name=year] option[selected]')
    h1 = soup.select_one('h1')
    return {'title': soup.title.get_text(' ', strip=True) if soup.title else '', 'h1': h1.get_text(' ', strip=True) if h1 else '',
            'selected_year': sel.get_text(strip=True) if sel else '',
            'chunk_urls': [htmllib.unescape(u) for u in re.findall(r'<turbo-frame[^>]*\ssrc="([^"]+)"', text)]}


def parse_client_split(body) -> dict:
    """client cycle_snapshot chunk: explicit in-house vs outside-firm values (exact dollars in chart JSON)."""
    text = body.decode('utf-8', errors='replace') if isinstance(body, bytes) else body
    out = {'in_house_usd': None, 'outside_firms_usd': None, 'client_year_total_usd': None, 'split_found': False}
    m = re.search(r"data-charts--single-stacked-bar-options-value='(\{.*?\})'", text, re.S)
    if m:
        try:
            opts = json.loads(htmllib.unescape(m.group(1)))
            for s in opts.get('series', []):
                if s.get('category') == 'In-house operations':
                    out['in_house_usd'] = money(s.get('value'))
                elif s.get('category') == 'Outside firms':
                    out['outside_firms_usd'] = money(s.get('value'))
            out['split_found'] = out['in_house_usd'] is not None or out['outside_firms_usd'] is not None
        except json.JSONDecodeError:
            pass
    t = BeautifulSoup(text, 'html.parser').get_text(' ', strip=True)
    tm = re.search(r'(\d{4}) total\s+(\$[\d,]+)', t)
    out['client_year_total_usd'] = money(tm.group(2)) if tm else None
    out['served_year'] = int(tm.group(1)) if tm else None   # the year the page itself reports; never inferred from the request
    return out


# ---- organisation search / totals (coordinator-verified route) -------------------------------------
def parse_org_search(body, query: str) -> dict:
    """/search?q=<name>&type=orgs -> exact-normalised-name Organization candidates only (never first-result guessing)."""
    soup = soup_of(body)
    qn = normalized(query)
    cands = []
    for tr in soup.select('table tr'):
        tds = tr.select('td')
        if len(tds) < 2 or tds[0].get_text(strip=True) != 'Organization':
            continue
        a = tds[1].select_one('a[href]')
        href = a['href'] if a else ''
        m = re.search(r'/orgs/([^/]+)/summary\?id=(D\d+)', href)
        name = tds[1].get_text(' ', strip=True)
        cands.append({'name': name, 'name_normalized': normalized(name), 'href': href, 'org_id': m.group(2) if m else '',
                      'slug': m.group(1) if m else ''})
    exact = [c for c in cands if c['name_normalized'] == qn and c['org_id']]
    ids = list(dict.fromkeys(c['org_id'] for c in exact))
    status = 'matched_exact' if len(ids) == 1 else ('ambiguous_exact' if len(ids) > 1 else ('no_exact_match' if cands else 'no_organization_rows'))
    return {'query': query, 'status': status, 'candidates': cands, 'exact': exact, 'org_id': ids[0] if len(ids) == 1 else '',
            'slug': exact[0]['slug'] if len(ids) == 1 else '', 'meta': page_meta(soup)}


def parse_org_totals(body) -> dict:
    """/orgs/<slug>/totals?id=D...: ONE page holds the whole 1990-latest history in two tables (party of recipient; source of funds)."""
    soup = soup_of(body)
    meta = page_meta(soup)
    by_party, by_source, affiliates = {}, {}, []
    for t in extract_tables(soup):
        hdr = ' '.join(t['header'])
        if t['header'][:1] == ['Cycle'] and 'Democrats' in hdr and 'Republicans' in hdr:
            for r in t['rows']:
                cy = clean_text(_col(r, 'Cycle'))
                if cy.isdigit():
                    by_party[int(cy)] = {'total_usd': money(_col(r, 'Total')), 'democrat_usd': money(_col(r, 'Democrats')),
                                         'republican_usd': money(_col(r, 'Republicans')), 'democrat_pct': pct(_col(r, '% to Dems')),
                                         'republican_pct': pct(_col(r, '% to Repubs'))}
        elif t['header'][:1] == ['Cycle'] and 'PACs' in hdr and 'Individuals' in hdr:
            for r in t['rows']:
                cy = clean_text(_col(r, 'Cycle'))
                if cy.isdigit():
                    by_source[int(cy)] = {'individual_usd': money(_col(r, 'Individuals')), 'pac_usd': money(_col(r, 'PACs')),
                                          'soft_individual_usd': money(_col(r, 'Soft (Individuals)')),
                                          'soft_organization_usd': money(_col(r, 'Soft (Organization)'))}
        elif t['header'][:1] == ['Affiliate']:
            for r in t['rows']:
                affiliates.append({'affiliate': clean_text(_col(r, 'Affiliate')), 'total_usd': money(_col(r, 'Total')),
                                   'pac_usd': money(_col(r, 'PACs')), 'individual_usd': money(_col(r, 'Individuals'))})
    text = soup.get_text(' ', strip=True)
    note = re.search(r'Contributions to 527s are not included[^.]*\.[^.]*\.', text)
    h1 = soup.select_one('h1:nth-of-type(2)') or None
    return {'meta': meta, 'by_party': by_party, 'by_source': by_source, 'affiliates': affiliates,
            'affiliates_cycle': meta['selected_cycle'], 'note_527': note.group(0) if note else '',
            'org_name': meta['h1'], 'title': meta['title']}
