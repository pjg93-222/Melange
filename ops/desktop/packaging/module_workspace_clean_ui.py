"""Approved modern shell over verified native workspace inputs.

Only compiled presentation assets and typed, already verified factual roles enter
this renderer. It neither reads arbitrary files nor loads generated HTML as code.
"""
import hashlib
import json
import re

from module_workspace_clean_assets import ASSETS, SOURCE_COMMIT
from module_workspace_render import (TEMPLATES, script_json, replace_once,
    profile_loader, provenance_markup, provenance_context, safe_tree)

PREFIX = '/staffer-live/approved/'
OVERLAYS = {
    'desk': ('desk-shell', 'desk-members', 'desk-compare', 'desk-profile',
             'desk-bills', 'desk-efficiency', 'desk-coalition'),
    'industry': ('industry-ui',), 'champions': ('champions-ui',),
    'interactions': ('interactions-ui',), 'people': ('people-ui',),
}
MOUNTED = {'desk': 'body.dsk-v2', 'industry': 'html.ind-v2',
    'champions': 'html.chm-ready', 'interactions': 'html.ixt-on',
    'research-bills': '', 'cu-fintech': '', 'people': 'nav.ppl-tabs',
    'network': 'html.mlk-v8'}
COLOR_VALUE = re.compile(r'^(#[0-9a-fA-F]{3,8}|(rgba?|hsla?)\([^)]*\))$')


def css(*names):
    return ''.join('<link rel="stylesheet" href="' + PREFIX + name + '.css">' for name in names)


def scripts(*names):
    return ''.join('<script src="' + PREFIX + name + '.js" data-mlk></script>' for name in names)


def boot(document, frame):
    tag = ('<script src="' + PREFIX + 'mlk-boot.js" data-frame="' + frame +
           '" data-ready="' + MOUNTED[frame] + '"></script>')
    return replace_once(document, '<head>', '<head>' + tag)


def member_page(base):
    document = replace_once(TEMPLATES['make_member_desk_00.tpl'], '__BUNDLE__', script_json(base))
    for marker, value in (('__DSPLIT__', '1'), ('__PROFILES_TAG__', ''), ('__HONORS_GENERATION_META__', '')):
        document = replace_once(document, marker, value)
    return document


def frames(main, pages, context, derivation):
    """Apply the canonical approved overlays to the existing analytical engines."""
    network = replace_once(TEMPLATES['make_dashboard_html_00.tpl'], '__DATA__', script_json(main['network']))
    palette = {'#1D1912':'#17131d','#282113':'#342649','#2E2514':'#403153','#3B2E16':'#49385f',
        '#433317':'#645478','#564019':'#8e7b9d','#9D9784':'#d6c9dc','#A49D8A':'#d6c9dc',
        '#D2CDBC':'#f7ede4','#F3F3E6':'#f7ede4','#EECD5C':'#eca91c','#D2A63C':'#eca91c'}
    # Exactly the approved builder's palette transformation; analytical code and values remain intact.
    for old, new in palette.items():
        network = network.replace(old, new)
    network = re.sub(r"ctx.globalAlpha=0.16;ctx.fillStyle='#[A-Za-z0-9]+';ctx.beginPath\(\);ctx.arc\(sx,sy,r\+11,0,7\);ctx.fill\(\);ctx.globalAlpha=1;", '', network)
    network = replace_once(network, '</head>', css('ui-kit', 'network') + '</head>')
    network = replace_once(network, '</body>', scripts('ui-kit', 'network') + '</body>')
    network = boot(network, 'network')
    network = re.sub(r'function fit\(\)\{[^\n]*\}', lambda _: 'function fit(){if(W<=48||H<=72)return;const xs=LX.filter(Number.isFinite),ys=LY.filter(Number.isFinite);if(!xs.length||!ys.length)return;const x0=Math.min(...xs),x1=Math.max(...xs),y0=Math.min(...ys),y1=Math.max(...ys);cam.s=Math.min((W-48)/Math.max(1,x1-x0),(H-72)/Math.max(1,y1-y0));cam.tx=W/2-(x0+x1)*cam.s/2;cam.ty=H/2-(y0+y1)*cam.s/2;}', network, count=1)
    advanced = replace_once(member_page(main['members']), '</body>',
        profile_loader(main['members'], context, derivation) + '</body>')
    desk = light_template(member_page(main['members']))
    desk = replace_once(desk, '</head>', css('ui-kit', 'restored', *OVERLAYS['desk']) + '</head>')
    desk = replace_once(desk, '<body>', '<body class="restored-desk">')
    # Preserve full automatic profile loading as well as the modern dossier's lazy reads.
    desk = replace_once(desk, '</body>', profile_loader(main['members'], context, derivation) +
        scripts('restored-links', 'ui-kit', *OVERLAYS['desk'], 'restored-desk') + '</body>')
    desk = boot(desk, 'desk')
    documents = {'network.html': network, 'original-desk.html': desk, 'advanced-desk.html': advanced}
    for key, name in (('industry', 'lobby-network.html'), ('champions', 'lobby-champions.html'),
            ('research-bills', 'lobby-bills.html'), ('interactions', 'lobby-interactions.html'),
            ('cu-fintech', 'lobby-screen.html')):
        original = light_template(pages[name])
        original = replace_once(original, '<head>', '<head><base href="/">')
        original = boot(original, key)
        original = replace_once(original, '</head>', css('ui-kit', 'restored', *OVERLAYS.get(key, ())) + '</head>')
        original = replace_once(original, '</body>', scripts('restored-links', 'ui-kit', *OVERLAYS.get(key, ())) + '</body>')
        documents['original-' + key + '.html'] = original
    people = ASSETS['people-source.html']
    for asset in re.findall(r'(?:src|href)="(staffer-[a-z-]+\.(?:js|css))"', people):
        if asset not in ASSETS:
            raise RuntimeError('Compiled people presentation asset is unavailable')
        people = people.replace('"' + asset + '"', '"' + PREFIX + asset + '"')
    people = replace_once(people, '<head>', '<head><base href="/staffer-live/">')
    people = replace_once(people, '</head>', css('ui-kit', 'restored-people', *OVERLAYS['people']) + '</head>')
    people = replace_once(people, '</body>', scripts('restored-links', 'ui-kit', *OVERLAYS['people']) + '</body>')
    documents['people.html'] = boot(people, 'people')
    return documents


def catalog(base):
    rows = []
    fields = ('name', 'chamber', 'district', 'party', 'state', 'rank', 'score', 'invested', 'alloc',
        'ind_money', 'money_source_status', 'eff_value', 'opt_alloc', 'gap', 'roi', 'committee',
        'committees', 'overall_stance', 'stances', 'adjrank')
    for index, member in enumerate(base['members']):
        row = {name: member.get(name) for name in fields}
        row.update(id=str(index), bio={}, latest='', billCount=None, articleCount=None)
        rows.append(row)
    # Existing navigation uses these presentation glyphs only. No data/model meaning.
    icons = {'Members': 'M4 21v-2a4 4 0 014-4h8a4 4 0 014 4v2M16 7a4 4 0 11-8 0 4 4 0 018 0'}
    return {'members': rows, 'cats': base['cats'], 'sources': base['source_updates'], 'uiSourceCommit': SOURCE_COMMIT,
        'asOf': base.get('rank_honors', {}).get('as_of'), 'icons': icons,
        'freshness': desk_freshness(base, 'verified signed members role')}


def shell(context, member_count, analytical_date):
    """Warm the signed profile role automatically, shared by same-origin frames."""
    descriptor = {**context['roles']['member-profiles'], 'members': member_count,
                  'sourceDigest': context['sourceDigest']}
    loader = r'''<script>
(() => {
 'use strict';
 const expected=__EXPECTED__, analytic=__ANALYTIC__, uiSourceCommit=__UI_COMMIT__;
 const provenance=document.createElement('div');provenance.id='native-workspace-freshness';
 provenance.style.cssText='position:fixed;bottom:8px;left:184px;right:18px;z-index:100;background:#342649;color:#f7ede4;padding:5px 10px;border:1px solid #645478;font:12px Segoe UI,sans-serif';
 provenance.textContent='Analytical baseline: '+analytic+' · Member briefs are loading from the signed workspace…';
 document.body.append(provenance);
 window.MelangeWorkspaceProfiles=(async()=>{
  const response=await fetch('/__desktop/workspace/member-profiles.json',{credentials:'same-origin',cache:'no-store',redirect:'error',headers:{Accept:'application/json','X-Melange-Workspace':expected.sourceDigest}});
  if(!response.ok||response.headers.get('X-Melange-Role-Sha256')!==expected.sha256||Number(response.headers.get('content-length'))!==expected.bytes)throw Error('Verified member profiles are unavailable');
  const data=await response.json();
  if(!data||!Array.isArray(data.members_heavy)||data.members_heavy.length!==expected.members)throw Error('Verified member profile roster differs');
  const briefs=data.members_heavy.filter(row=>row.psy&&row.psy.brief_v3);
  window.__melangeWorkspaceStatus={sourceDigest:expected.sourceDigest,members:data.members_heavy.length,briefs:briefs.length,staleBriefs:briefs.filter(row=>row.psy.brief_v3.stale).length,ui:'approved-clean-native',uiSourceCommit};
  window.__profilesReady=true;
  const feedDate=/module-data-(\d{4})-(\d{2})-(\d{2})/.exec(__TAG__);
  const delivered=feedDate?new Date(Number(feedDate[1]),Number(feedDate[2])-1,Number(feedDate[3])).toLocaleDateString('en-US',{year:'numeric',month:'long',day:'numeric'}):'date unavailable';
  provenance.textContent='Analytical baseline: '+analytic+' · Member briefs: '+briefs.length+' delivered in signed workspace published '+delivered+'. Evidence windows appear on individual briefs.';
  window.dispatchEvent(new Event('melange-workspace-profiles-ready'));
  return data;
 })();
 window.MelangeWorkspaceProfiles.catch(()=>{window.__profilesReady=false;provenance.textContent='Analytical baseline: '+analytic+' · Member profiles could not load. Reload this workspace to retry.';});
})();
</script>'''.replace('__EXPECTED__', script_json(descriptor)).replace('__ANALYTIC__',
        script_json(analytical_date)).replace('__TAG__', script_json(context['releaseTag'])).replace('__UI_COMMIT__', script_json(SOURCE_COMMIT))
    document = ASSETS['index.html']
    return replace_once(document, '</body>', loader + '</body>')


class CleanWorkspace:
    """Closed in-memory modern routes, each bound to one verified workspace."""
    def __init__(self, main, pages, industry, context, derivation, heavy_loader):
        self.main, self.industry = main, industry
        self.context = provenance_context(context)
        self.heavy_loader = heavy_loader
        self.heavy = None
        self.documents = frames(main, pages, context, derivation)
        self.values = {'catalog': catalog(main['members']),
            'colors': colour_maps(self.documents), 'bills': main['members']['bill_live'],
            'champions': industry['champions'], 'forecasts': industry['forecast'],
            'research-bills': industry['bills'], 'cu-fintech': industry['screen'],
            'interactions': industry['interactions'], 'industry': main['industry']}
        from datetime import date
        generated = main['members'].get('freshness', {}).get('generated_at', '')
        try:
            day = date.fromisoformat(generated[:10])
            analytical_date = day.strftime('%B ') + str(day.day) + day.strftime(', %Y')
        except (ValueError, TypeError):
            analytical_date = 'Unavailable'
        self.documents['index.html'] = shell(context, len(main['members']['members']), analytical_date)

    def _heavy(self):
        if self.heavy is None:
            value = self.heavy_loader()
            if not isinstance(value, dict) or len(value.get('members_heavy', [])) != len(self.main['members']['members']):
                raise ValueError('Verified member profile roster differs')
            safe_tree(value)
            self.heavy = value
        return self.heavy

    def response(self, path):
        """No filesystem lookup, path normalization or unverified fallthrough."""
        if path == '/':
            name = 'index.html'
        elif path.startswith(PREFIX):
            name = path[len(PREFIX):]
        else:
            return None
        if not name or '\\' in name or '%' in name or any(part in ('', '.', '..') for part in name.split('/')):
            return (404, b'Not found', 'text/plain; charset=utf-8')
        if name.startswith('data/') and name.endswith('.json'):
            key = name[5:-5]
            value = self.values.get(key)
            if key == 'desk-support':
                value = self._heavy()
            elif re.fullmatch(r'member-(0|[1-9][0-9]{0,3})', key):
                index = int(key[7:])
                if index < len(self.main['members']['members']):
                    value = {**self.main['members']['members'][index], **self._heavy()['members_heavy'][index], 'id': str(index)}
            if value is not None:
                return (200, json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode(), 'application/json; charset=utf-8')
        value = self.documents.get(name)
        if value is None and name in ASSETS and name != 'people-source.html':
            value = ASSETS[name]
            if name == 'staffer-live.css':
                # The approved boot loader already loads this kit separately,
                # with a bounded render wait and local-font fallback. A CSS
                # import would also block People scripts on a stalled network.
                value = replace_once(value, '@import url("https://use.typekit.net/ayd3qhz.css");', '')
        if value is None:
            return (404, b'Not found', 'text/plain; charset=utf-8')
        content_type = 'text/css' if name.endswith('.css') else 'text/javascript' if name.endswith('.js') else 'text/html'
        return (200, value.encode(), content_type + '; charset=utf-8')
def light_template(text):
    """Recolor stylesheet literals without touching original datasets or engines."""
    colors = {'#1d1912':'#f7ede4','#282113':'#fcf7f4','#2e2514':'#eee3db',
              '#3b2e16':'#e2d5e8','#433317':'#d8cbbc','#564019':'#bcaaa0',
              '#f3f3e6':'#342649','#d2cdbc':'#51405f','#a49d8a':'#6b5e73',
              '#9d9784':'#6b5e73','#eecd5c':'#57447b','#d2a63c':'#57447b',
              '#6b4e1f':'#765399','#86efac':'#216444','#34d399':'#216444',
              '#7ee787':'#216444','#fbbf24':'#785310','#eab308':'#785310',
              '#e3b341':'#785310','#f87171':'#a12e39','#ff7b72':'#a12e39',
              '#58a6ff':'#355d92','#60a5fa':'#355d92','#8b949e':'#6b5e73',
              '#c9d1d9':'#51405f','#2a2518':'#eee3db','#211d15':'#eee3db'}
    def sheet(match):
        return re.sub(r'#[a-fA-F0-9]{6}\b', lambda c: colors.get(c[0].lower(),c[0]), match[0])
    return re.sub(r'<style[^>]*>.*?</style>', sheet, text, flags=re.S)

def js_truthy(v):
    if v is None or v is False:
        return False
    if isinstance(v, (int, float)):
        return v == v and v != 0
    if isinstance(v, str):
        return v != ''
    return True

def js_number(v):
    """Number(v)||0, as used by the desk's exclusion total."""
    if isinstance(v, bool):
        n = 1.0 if v else 0.0
    elif isinstance(v, (int, float)):
        n = float(v)
    elif v is None:
        n = 0.0
    elif isinstance(v, str):
        s = v.strip()
        try:
            n = float(s) if s else 0.0
        except ValueError:
            n = float('nan')
    elif isinstance(v, list):
        n = 0.0 if not v else js_number(v[0]) if len(v) == 1 and not isinstance(v[0], (list, dict)) else float('nan')
    else:
        n = float('nan')
    return 0 if n != n or n == 0 else n

def js_text(v):
    """esc(v) of the desk (make_member_desk_00.tpl:1862) as text: null/undefined -> ''."""
    if v is None:
        return ''
    if isinstance(v, bool):
        return 'true' if v else 'false'
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)

def en_us(n):
    """Number.prototype.toLocaleString() in en-US (the desk's reader locale): grouping, up to 3 fraction digits."""
    if float(n).is_integer():
        return f'{int(n):,}'
    return f'{n:,.3f}'.rstrip('0').rstrip('.')

def desk_freshness(D, source):
    """The desk's full-width #integritybar text, computed exactly as make_member_desk_00.tpl:446-449 and :514-518 build it."""
    fr = D.get('freshness')
    generated = fr.get('generated_at') if js_truthy(fr) and isinstance(fr, dict) else None
    generated = js_text(generated) if js_truthy(generated) else 'unknown'
    integrity = D.get('integrity')
    display = integrity.get('source_display') if js_truthy(integrity) and isinstance(integrity, dict) else None
    display = display if js_truthy(display) and isinstance(display, dict) else {}
    excluded = sum(js_number(v) for k, v in display.items() if re.search(r'(excluded|routed)', k))
    honors = D.get('rank_honors')
    honors = honors if js_truthy(honors) else None
    parts = [{'label': 'Data freshness:', 'text': f'generated {generated}'},
             {'label': 'Exclusion accounting:', 'text': f"{en_us(excluded)} source rows explicitly excluded or routed. Open a member's media sections for item-level reasons."}]
    line = f"Data freshness: generated {generated} · Exclusion accounting: {parts[1]['text']}"
    as_of = None
    if honors is not None:
        as_of = js_text(honors.get('as_of') if isinstance(honors, dict) else None)
        parts.append({'label': 'Recognition evidence:', 'text': f'through {as_of}.'})
        line += f' Recognition evidence: through {as_of}.'
    excluded = int(excluded) if float(excluded).is_integer() else excluded
    through = re.match(r'\d{4}-\d{2}-\d{2}', generated)
    return {'through': through[0] if through else None, 'generated_at': None if generated == 'unknown' else generated,
            'excluded_or_routed': excluded, 'recognition_as_of': as_of, 'parts': parts, 'line': line,
            'source': source, 'rule': 'make_member_desk_00.tpl:446-449 (freshness, exclusion accounting) and :514-518 (recognition evidence); '
                                      "the page head's chip shows the date part of generated_at as written (no time-zone conversion)"}

def js_literal_end(text, start):
    """Index just past the bracket that closes text[start] ('{' or '['); string- and comment-aware (JavaScript)."""
    depth, i, n = 0, start, len(text)
    while i < n:
        c = text[i]
        if c in '\'"`':
            q, i = c, i + 1
            while i < n and text[i] != q:
                i += 2 if text[i] == '\\' else 1
        elif text.startswith('//', i):
            nl = text.find('\n', i)
            i = n if nl < 0 else nl
            continue
        elif text.startswith('/*', i):
            e = text.find('*/', i + 2)
            i = n if e < 0 else e + 2
            continue
        elif c in '{[':
            depth += 1
        elif c in '}]':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1

def parse_js_literal(src):
    """Object/array literal with string, number or nested literal values; any other value is kept as {'$expr': text}."""
    pos = 0

    def ws():
        nonlocal pos
        while pos < len(src) and src[pos] in ' \t\r\n':
            pos += 1

    def string():
        nonlocal pos
        q, pos, out = src[pos], pos + 1, []
        while src[pos] != q:
            if src[pos] == '\\':
                out.append({'n': '\n', 't': '\t', 'r': '\r'}.get(src[pos + 1], src[pos + 1]))
                pos += 2
            else:
                out.append(src[pos])
                pos += 1
        pos += 1
        return ''.join(out)

    def value():
        nonlocal pos
        ws()
        c = src[pos]
        if c == '{':
            pos += 1
            obj = {}
            while True:
                ws()
                if src[pos] == '}':
                    pos += 1
                    return obj
                if src[pos] in '\'"':
                    key = string()
                else:
                    m = re.compile(r'[A-Za-z0-9_$\-.]+').match(src, pos)
                    key, pos = m[0], m.end()
                ws()
                pos += 1  # ':'
                obj[key] = value()
                ws()
                if src[pos] == ',':
                    pos += 1
        if c == '[':
            pos += 1
            arr = []
            while True:
                ws()
                if src[pos] == ']':
                    pos += 1
                    return arr
                arr.append(value())
                ws()
                if src[pos] == ',':
                    pos += 1
        if c in '\'"':
            return string()
        m = re.compile(r'-?\d+(\.\d+)?(?=\s*[,}\]])').match(src, pos)
        if m:
            pos = m.end()
            return float(m[0]) if '.' in m[0] else int(m[0])
        start, depth = pos, 0
        while pos < len(src) and not (depth == 0 and src[pos] in ',}]'):
            depth += src[pos] in '([{'
            depth -= src[pos] in ')]}'
            pos += 1
        return {'$expr': src[start:pos].strip()}

    return value()

def colour_leaves(obj, path=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from colour_leaves(v, path + (k,))
    elif isinstance(obj, str) and COLOR_VALUE.match(obj):
        yield path, obj

def key_pattern(key):
    """How an object key can be written in the source literal: quoted, or bare when it is an identifier or a number."""
    alts = ["'" + re.escape(key) + "'", '"' + re.escape(key) + '"']
    if re.fullmatch(r'[A-Za-z_$][\w$]*|\d+', key):
        alts.append(re.escape(key))
    return '(?:' + '|'.join(alts) + ')'

def extract_map(text, name):
    """Every occurrence of `NAME = {...}` / `NAME: {...}` (byte-exact slice), parsed; same rule as tools/colormap_check.py."""
    found = []
    for m in re.finditer(re.escape(name) + r'\s*[=:]\s*(?=[\{\[])', text):  # literal prefix: fast on 18 MB pages
        if m.start() and re.match(r'[A-Za-z0-9_$.]', text[m.start() - 1]):
            continue
        e = js_literal_end(text, m.end())
        if e > 0:
            found.append((text[m.start():e], text[m.end():e]))
    return found

def colour_maps(documents):
    """data/colors.json: the legacy data colour maps by reference, copied from the served documents and verified."""
    groups = [('desk', 'original-desk.html', 'cu-member-desk.html', 'fec/surfaces/templates/make_member_desk_00.tpl',
               ['STCOL', 'PTCOL', 'TIERCOL', 'HONOR_COLORS', 'STANDING_COLORS', 'PILL', 'POVCOL', 'RELCOL', 'TRK_COL',
                'INDUSTRY_FAMILY', 'BILL_LOBBY_SECTOR_COLORS']),
              ('influence', 'network.html', 'Moneyball Dashboard.html', 'fec/surfaces/templates/make_dashboard_html_00.tpl',
               ['STCOL', 'HONOR_COL', 'PTCOL', 'TIERCOL', 'ELCOL'])]
    out = {'schema': 'melange-colors-v1',
           'note': 'Legacy data colour maps by reference, copied byte-exactly from the served documents by build_clean_workspace.py. '
                   'Read them; never retype a value. provenance[] names the source file and variable of every map.',
           'desk': {}, 'influence': {}, 'industry': {}, 'provenance': []}
    for group, document, source, template, names in groups:
        text = documents[document]
        for name in names:
            hits = extract_map(text, name)
            record = {'map': f'{group}.{name}', 'variable': name, 'document': document, 'source': source, 'template': template,
                      'occurrences': len(hits)}
            if not hits:
                out['provenance'].append(dict(record, found=False))
                continue
            raw, literal = hits[0]
            parsed = parse_js_literal(literal)
            leaves = list(colour_leaves(parsed))
            verified = bool(leaves) and all(re.search(r'[{,\s]' + key_pattern(str(path[-1])) + r'\s*:\s*([\'"])' + re.escape(value) + r'\1', literal)
                                            for path, value in leaves)
            out[group][name] = parsed
            out['provenance'].append(dict(record, found=True, identical_occurrences=len({h[0] for h in hits}) == 1,
                                          sha256_lf=hashlib.sha256(raw.replace('\r\n', '\n').encode('utf-8')).hexdigest(),
                                          bytes=len(raw.encode('utf-8')), colours=len(leaves), verified=verified))
    # Industry tiers: TIER_COLORS in make_lobby_network_html.py, served as page-data tierMeta.colors.
    text = documents['original-industry.html']
    m = re.search(r'"colors"\s*:\s*(?=\{\s*"big")', text)
    record = {'map': 'industry.TIER_COLORS', 'variable': 'TIER_COLORS (served as page-data tierMeta.colors)',
              'document': 'original-industry.html', 'source': 'lobby-network.html', 'template': 'fec/surfaces/make_lobby_network_html.py'}
    if m:
        e = js_literal_end(text, m.end())
        raw, literal = text[m.start():e], text[m.end():e]
        parsed = json.loads(literal)
        leaves = list(colour_leaves(parsed))
        verified = bool(leaves) and all(f'"{path[-1]}":"{value}"' in literal.replace(' ', '') for path, value in leaves)
        out['industry']['TIER_COLORS'] = parsed
        out['provenance'].append(dict(record, found=True, occurrences=1, identical_occurrences=True,
                                      sha256_lf=hashlib.sha256(raw.replace('\r\n', '\n').encode('utf-8')).hexdigest(),
                                      bytes=len(raw.encode('utf-8')), colours=len(leaves), verified=verified))
    else:
        out['provenance'].append(dict(record, found=False))
    return out
