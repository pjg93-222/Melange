"""Pure native-bound UI rendering over an already verified workspace lease.

No generated/downloaded HTML is source authority, and this module performs no
file/network I/O. Callers verify signed role bytes, ownership and the current
workspace lease before supplying decoded objects and source provenance.
"""
import hashlib
import html
import json
import math
import re

from module_workspace_ui_templates import TEMPLATES
from module_workspace_combined_ui import prepare, assemble
import module_workspace_industry_ui as industry_ui

MAIN_ROLES = frozenset(('network', 'members', 'industry', 'staffer-summary',
                        'staffer-offices', 'staffer-organisations', 'staffer-clients'))
PAGES = frozenset(('champions', 'forecast', 'bills', 'screen', 'interactions'))
PROFILES_PATH = '/__desktop/workspace/member-profiles.json'
PROFILE_FIELDS = frozenset(('articles', 'bills', 'bio', 'community', 'cook_pvi', 'district_brief',
                           'electoral', 'employers', 'financial', 'industry', 'partners', 'personal',
                           'psy', 'refs', 'staffdir'))
HEX = re.compile('[0-9a-f]{64}')


class WorkspaceRenderDataError(ValueError):
    """Closed factual-input failure, distinct from a broken compiled template."""


def require(value, message):
    if not value:
        raise WorkspaceRenderDataError(message)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def script_json(value):
    text = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    return text.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def safe_tree(value):
    stack = [(value, 0)]
    count = 0
    while stack:
        item, depth = stack.pop()
        count += 1
        require(count <= 8_000_000 and depth <= 64, 'Workspace UI data exceeds its structural bound')
        if type(item) is dict:
            require(all(type(key) is str and key not in ('__proto__', 'constructor', 'prototype') for key in item),
                    'Workspace UI object has an unsafe field')
            stack.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            stack.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            require(len(item) <= 8 * 1024 ** 2, 'Workspace UI string exceeds its bound')
        elif type(item) is float:
            require(math.isfinite(item), 'Workspace UI number is not finite')
        else:
            require(type(item) in (int, bool, type(None)), 'Workspace UI value is not JSON data')


def provenance_context(value):
    require(type(value) is dict and set(value) == {'schemaVersion', 'appId', 'contractId', 'sourceDigest', 'releaseTag', 'roles'},
            'Workspace UI provenance fields differ')
    require(type(value['schemaVersion']) is int and value['schemaVersion'] == 1 and value['appId'] == 'melange' and
            value['contractId'] == 'melange.workspace.v1' and type(value['sourceDigest']) is str and HEX.fullmatch(value['sourceDigest']) and
            type(value['releaseTag']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9._-]{0,127}', value['releaseTag']),
            'Workspace UI provenance identity differs')
    require(type(value['roles']) is dict and set(value['roles']) == MAIN_ROLES | {'member-profiles', 'industry-pages'},
            'Workspace UI role provenance differs')
    for row in value['roles'].values():
        require(type(row) is dict and set(row) == {'sha256', 'bytes'} and type(row['sha256']) is str and HEX.fullmatch(row['sha256']) and
                type(row['bytes']) is int and 0 < row['bytes'] <= 2 * 1024 ** 3, 'Workspace UI role descriptor is invalid')
    return value


def replace_once(text, marker, value):
    if text.count(marker) != 1:
        raise RuntimeError('Compiled workspace template marker changed: ' + marker)
    return text.replace(marker, value, 1)


def provenance_markup(context, *, industry=False):
    identity = 'desktop-workspace-industry-provenance' if industry else 'desktop-workspace-provenance'
    return ('<aside id="' + identity + '" style="padding:6px 18px;background:#282113;color:#D2CDBC;font:12px Segoe UI,sans-serif">'
            'Using verified GitHub data cache · ' + html.escape(context['releaseTag']) +
            ' <details style="display:inline"><summary style="display:inline;cursor:pointer">Source details</summary>'
            '<span>Current signed workspace ' + context['sourceDigest'] +
            '. Historical analytical receipts below retain their original source context.</span></details></aside>'
            '<script id="' + identity + '-json" type="application/json">' + script_json(context) + '</script>')


PROFILE_LOADER = r"""<script>
(function(){
 'use strict';
 const EXPECTED=__PROFILE_CONTEXT__, ALLOWED=new Set(__PROFILE_FIELDS__);
 let pending=null;
 function note(message,retry){
  let box=document.getElementById('desktop-workspace-profile-status');
  if(!box){box=document.createElement('div');box.id='desktop-workspace-profile-status';box.style.cssText='padding:6px 18px;background:#282113;color:#D2CDBC;font:12px Segoe UI,sans-serif';const bar=document.getElementById('desktop-workspace-provenance');if(bar)bar.after(box);else document.body.prepend(box);}
  box.replaceChildren(document.createTextNode(message));
  if(retry){const button=document.createElement('button');button.type='button';button.id='desktop-workspace-profile-retry';button.textContent='Retry profiles';button.addEventListener('click',()=>load());box.append(' ',button);}
 }
 async function load(){
  if(window.__profilesReady)return;
  if(pending)return pending;
  note('Loading member profiles from the verified local GitHub cache…',false);
  pending=(async()=>{
   const response=await fetch('/__desktop/workspace/member-profiles.json',{credentials:'same-origin',cache:'no-store',redirect:'error',headers:{Accept:'application/json','X-Melange-Workspace':EXPECTED.sourceDigest}});
   if(!response.ok||!(response.headers.get('content-type')||'').toLowerCase().startsWith('application/json'))throw new Error('Profile response unavailable');
   if(response.headers.get('X-Melange-Role-Sha256')!==EXPECTED.sha256)throw new Error('Profile workspace differs');
   const length=response.headers.get('content-length');if(length!==null&&(!/^[0-9]+$/.test(length)||Number(length)!==EXPECTED.bytes))throw new Error('Profile byte count differs');
   const payload=await response.json();
   if(!payload||Object.keys(payload).sort().join('|')!=='bill_lobbying|members_heavy'||!Array.isArray(payload.members_heavy)||payload.members_heavy.length!==EXPECTED.members)throw new Error('Profile roster differs');
   for(const row of payload.members_heavy)if(!row||typeof row!=='object'||Array.isArray(row)||Object.keys(row).some(key=>!ALLOWED.has(key)))throw new Error('Profile fields differ');
   if(typeof window.__melangeProfileMerge!=='function')throw new Error('Profile merge is unavailable');
   window.__melangeProfileMerge(payload);
   if(window.__profilesReady!==true)throw new Error('Profile merge did not finish');
   note('Member profiles are ready from the verified local GitHub cache.',false);
   window.dispatchEvent(new Event('melange-workspace-profiles-ready'));
  })().catch(()=>{window.__profilesReady=false;note('Member profiles are not ready. Profile actions are waiting; retry when the workspace is available.',true);}).finally(()=>{pending=null;});
  return pending;
 }
 window.__melangeLoadWorkspaceProfiles=load;
 load();
})();
</script>"""


def profile_loader(members, context, derivation):
    merge = derivation.get('memberProfileMerge')
    require(type(merge) is dict and merge.get('fields') == ['name', 'state', 'district', 'sna_idx'], 'Profile roster field contract differs')
    roster = [[row.get(field) for field in merge['fields']] for row in members['members']]
    require(len(roster) == merge.get('members') == merge.get('membersHeavy') and merge.get('orderedRoster') == roster and
            hashlib.sha256(canonical(roster)).hexdigest() == merge.get('orderedRosterSha256'), 'Profile positional identity roster differs')
    require(merge.get('membersSha256') == context['roles']['members']['sha256'] and
            merge.get('memberProfilesSha256') == context['roles']['member-profiles']['sha256'], 'Profile/base role binding differs')
    descriptor = {**context['roles']['member-profiles'], 'members': len(roster), 'sourceDigest': context['sourceDigest']}
    return replace_once(replace_once(PROFILE_LOADER, '__PROFILE_CONTEXT__', script_json(descriptor)),
                        '__PROFILE_FIELDS__', script_json(sorted(PROFILE_FIELDS)))


def industry_documents(main_inputs, page_inputs, context, derivation):
    require(type(page_inputs) is dict and set(page_inputs) == PAGES, 'Industry page role set differs')
    for page in PAGES:
        require(type(page_inputs[page]) is dict, 'Industry page is not a data object')
        safe_tree(page_inputs[page])
    landing = main_inputs['industry']
    require(landing.get('page') == 'landing' and all(page_inputs[page].get('page') == page for page in PAGES - {'interactions'}),
            'Industry page data identity differs')
    payload = dict(landing)
    for target, source in (('company_bills', 'companyBills'), ('company_members', 'companyMembers'), ('org_mentions', 'orgMentions')):
        payload[target] = landing[source]
    payload.update({'champions_v2': page_inputs['champions']['championsV2'],
                    'bills': page_inputs['bills']['bills'], 'bill_sectors': page_inputs['bills']['bill_sectors']})
    forecast = {**derivation['forecastContext'], **page_inputs['forecast']}
    screen = {**derivation['screenContext'], **page_inputs['screen']}
    cards = industry_ui._industry_cards({row['sector']: row['spend'] for row in landing['industries']}, landing['tierMeta'])
    footer = provenance_markup(context, industry=True)
    family = industry_ui._document(cards, payload, forecast, screen, footer)
    family['interactions'] = industry_ui._interactions_document(page_inputs['interactions'], footer, page_inputs['interactions']['receipts'])
    require(all(len(value.encode('utf-8')) <= 32 * 1024 ** 2 for value in family.values()), 'Industry view exceeds its bound')
    return family


def render_pages(inputs, industry_inputs, *, provenance, derivation):
    """Return exactly Moneyball plus the complete six-file industry family."""
    context = provenance_context(provenance)
    require(type(inputs) is dict and set(inputs) == MAIN_ROLES, 'Initial renderer requires seven main roles; bulk profiles stay lazy')
    for value in inputs.values():
        require(type(value) is dict, 'Workspace main role is not a data object')
        safe_tree(value)
    require(type(derivation) is dict and derivation.get('schemaVersion') == 1, 'Signed rendering derivation is missing')
    safe_tree(derivation)
    family = industry_documents(inputs, industry_inputs, context, derivation)
    network = replace_once(TEMPLATES['make_dashboard_html_00.tpl'], '__DATA__', script_json(inputs['network']))
    members = replace_once(TEMPLATES['make_member_desk_00.tpl'], '__BUNDLE__', script_json(inputs['members']))
    members = replace_once(replace_once(replace_once(members, '__DSPLIT__', '1'), '__PROFILES_TAG__', ''), '__HONORS_GENERATION_META__', '')
    staffer = TEMPLATES['make_staffer_network_html_01.tpl']
    for marker, role in (('__DATA__', 'staffer-summary'), ('__OFFICES__', 'staffer-offices'),
                         ('__ORGS__', 'staffer-organisations'), ('__CLIENTS__', 'staffer-clients')):
        staffer = replace_once(staffer, marker, script_json(inputs[role]))
    loader = profile_loader(inputs['members'], context, derivation)
    pieces = prepare(network, members, family['landing'], staffer,
                     TEMPLATES['network-bridge.js'], TEMPLATES['desk-bridge.js'], loader)
    moneyball = assemble(pieces, True)
    moneyball = replace_once(moneyball, '<body class=netmode>', '<body class=netmode>' + provenance_markup(context))
    require(len(moneyball.encode('utf-8')) <= 128 * 1024 ** 2, 'Initial workspace shell exceeds its bound')
    output = {'Moneyball.html': moneyball, 'lobby-network.html': family['landing']}
    output.update({'lobby-' + page + '.html': family[page] for page in PAGES})
    return output


def render_moneyball(inputs, *, industry_inputs, provenance, derivation):
    return render_pages(inputs, industry_inputs, provenance=provenance, derivation=derivation)['Moneyball.html']


def render_industry(page, data, *, provenance, derivation, inputs, industry_inputs):
    require(page in PAGES | {'landing'}, 'Unknown compiled industry page')
    require(data == (inputs['industry'] if page == 'landing' else industry_inputs[page]), 'Industry role does not match the selected page')
    return industry_documents(inputs, industry_inputs, provenance_context(provenance), derivation)[page]
