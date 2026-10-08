# -*- coding: utf-8 -*-
"""LANE A / R1 -- PRESS channel census (read-only).

Reproduces the LIVE press ingest chain exactly, without importing anything under fec\:
hash-verified copies of fec\press_stream.py, fec\stance\media_rules.py and
fec\members\member_identity.py live under SCRATCH\lib with a paths.py stub pointing at the
same live roots.  Nothing is written outside PACKET/SCRATCH.

Closes: rows in -> rows ingested -> rows scored, every drop attributed to a quoted rule.
"""
import os, sys, io, csv, json, hashlib, collections, datetime

LIB = r'C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneA\lib'
sys.path.insert(0, LIB)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import press_stream as PS
import media_rules as MR
from member_identity import Resolver

ROOT = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DRAFT = r'C:\Users\pgoff\OneDrive\Desktop\Draft Systems'


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def rd(p):
    if not os.path.exists(p):
        return []
    with io.open(p, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


print('=' * 100)
print('R1  PRESS CHANNEL CENSUS   run', datetime.datetime.now().isoformat(timespec='seconds'))
print('=' * 100)

BASE = PS.BASE_TONE_PATH
REFR = PS.REFRESH_TONE_PATH
for p in (BASE, REFR):
    print('input  %-64s %12d bytes  mtime %s' % (
        os.path.relpath(p, ROOT).replace('\\', '/') if p.startswith(ROOT) else p,
        os.path.getsize(p), datetime.datetime.fromtimestamp(os.path.getmtime(p)).isoformat(sep=' ')))
    print('       sha256 %s' % sha(p))

# ---- 1. INGEST ACCOUNTING: replicate press_stream.load_tone_rows() drop by drop --------------
base_rows, refr_rows = rd(BASE), rd(REFR)
print('\n-- 1. INGEST (fec/press_stream.py:98 load_tone_rows) --')
print('rows in  cu_press_stance_tone.csv (historical)          : %6d' % len(base_rows))
print('rows in  data/stance/press_refresh_tone.csv (supplement): %6d' % len(refr_rows))
print('rows in  TOTAL                                          : %6d' % (len(base_rows) + len(refr_rows)))

drop_om = collections.Counter()
drop_url = collections.Counter()
drop_dup = collections.Counter()
dup_examples = []
kept, seen = [], set()
for tag, rows in (('base', base_rows), ('refresh', refr_rows)):
    for r in rows:
        if (r.get('source') or '').strip().upper() == 'OFFICIAL_MENTION':
            drop_om[tag] += 1
            continue
        key = PS.tone_turn_key(r)
        if not key[0]:
            drop_url[tag] += 1
            continue
        if key in seen:
            drop_dup[tag] += 1
            if len(dup_examples) < 10:
                dup_examples.append((tag, key[1], (r.get('title') or '')[:70], key[0][:90]))
            continue
        seen.add(key)
        r['_src'] = tag
        kept.append(r)

print("\nRULE (press_stream.py:111)  if (row.get('source') or '').strip().upper() == 'OFFICIAL_MENTION': continue")
print('   dropped: base %d, refresh %d, total %d' % (drop_om['base'], drop_om['refresh'], sum(drop_om.values())))
print("RULE (press_stream.py:114)  if not key[0] or key in seen: continue     [not key[0] = empty canonical url]")
print('   dropped empty-url: base %d, refresh %d, total %d' % (drop_url['base'], drop_url['refresh'], sum(drop_url.values())))
print('   dropped duplicate (url,identity) turn key: base %d, refresh %d, total %d'
      % (drop_dup['base'], drop_dup['refresh'], sum(drop_dup.values())))
print('ROWS INGESTED (load_tone_rows return)                   : %6d' % len(kept))
print('   of which historical %d / refresh %d' % (sum(1 for r in kept if r['_src'] == 'base'),
                                                  sum(1 for r in kept if r['_src'] == 'refresh')))
tot_in = len(base_rows) + len(refr_rows)
acct = len(kept) + sum(drop_om.values()) + sum(drop_url.values()) + sum(drop_dup.values())
print('CLOSES? %d in = %d ingested + %d OFFICIAL_MENTION + %d empty-url + %d dup-turn  -> %s'
      % (tot_in, len(kept), sum(drop_om.values()), sum(drop_url.values()), sum(drop_dup.values()),
         'YES' if acct == tot_in else 'NO  unaccounted=%d' % (tot_in - acct)))
if dup_examples:
    print('\n  duplicate-turn examples (rule: historical wins):')
    for t, ident, title, u in dup_examples:
        print('    [%s] %-22s %-70s %s' % (t, ident, title, u))

# ---- 2. SCORING ACCOUNTING: replicate the live build_media_blend press loop ------------------
print('\n-- 2. SCORING (fec/stance/build_media_blend.py press block, LIVE version) --')
ORIG = json.load(io.open(os.path.join(ROOT, 'data', 'stance', 'press_raw_original.json'), encoding='utf-8'))
print('press_raw_original.json category keys (the `if c in ORIG` gate) : %d' % len(ORIG))

roster = json.load(io.open(os.path.join(ROOT, 'data', 'engine', 'congestion.json'), encoding='utf-8'))
resolver = Resolver([x['member'] for x in roster], {x['member']: x.get('bioguide') for x in roster})

api_target = {}
api_path = os.path.join(ROOT, 'data', 'stance', 'api_press_stance.csv')
for r in rd(api_path):
    api_target[(r.get('url') or '').strip().rstrip('/')] = (r.get('api_target') or '').strip()
fulltext = PS.load_fulltext()
print('api_press_stance.csv url->api_target entries: %d | fulltext cache urls: %d'
      % (len(api_target), len(fulltext)))

stk = {}
sfp = os.path.join(ROOT, 'press_stance_final.csv')
for r in rd(sfp):
    k = (PS.canonical_url(r.get('url'), keep_fragment=True),
         (r.get('bioguide') or r.get('member') or '').strip().upper())
    stk[k] = ((r.get('stack_label') or '').strip().lower(), (r.get('tier') or '').strip().lower())
print('press_stance_final.csv stack keys (url,identity): %d' % len(stk))

# press_stance_overrides.json 'corrections' -- read directly (config_overlay merge is a
# .candidate/base merge; only the base file exists here, verified below).
pov_doc = json.load(io.open(os.path.join(ROOT, 'data', 'stance', 'press_stance_overrides.json'), encoding='utf-8'))
pov = pov_doc.get('corrections') or []
cand = os.path.join(ROOT, 'data', 'stance', 'press_stance_overrides.json.candidate')
print('press_stance_overrides.json corrections: %d  (.candidate present: %s)'
      % (len(pov), os.path.exists(cand)))

SIGN = {'support': 1.0, 'oppose': -1.0, 'neutral': 0.0}
TW = {'unanimous': 1.0, 'majority': 0.7, 'review': 0.35}
TODAY = datetime.date.today()


def press_gold(url, title):
    ul = (url or '').strip().rstrip('/')
    tl = (title or '').lower()
    for g in pov:
        st = (g.get('stance') or '').strip().lower()
        if st not in SIGN:
            continue
        if g.get('url') and (g.get('url') or '').strip().rstrip('/') == ul:
            return st
        if g.get('title_contains') and (g.get('title_contains') or '').lower() in tl:
            return st
    return None


def pdate(s):
    for f in ('%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y'):
        try:
            return datetime.datetime.strptime((s or '').strip(), f).date()
        except ValueError:
            pass
    return None


disp = collections.Counter()
basis = collections.Counter()
effcat = collections.Counter()
declared_lost = collections.Counter()
routed_not_in_orig = collections.Counter()
n_used = 0
members_nz = set()
rows_audit = []
for r in kept:
    uk = PS.canonical_url(r.get('url'), keep_fragment=True)
    turn = (uk, (r.get('bioguide') or r.get('member') or '').strip().upper())
    declared = [c.strip() for c in (r.get('categories') or '').split(';') if c.strip()]
    route = MR.press_routing_decision(api_target.get(uk, ''), r.get('title') or '', declared,
                                      fulltext.get(uk, ''))
    cats = [c for c in route['categories'] if c in ORIG]
    for c in route['categories']:
        if c not in ORIG:
            routed_not_in_orig[c] += 1
    basis[route['basis']] += 1
    for c in cats:
        effcat[c] += 1
    for c in route['discarded_declared']:
        declared_lost[c] += 1
    d = 'pending'
    m = resolver.resolve(r.get('member'), r.get('bioguide'))
    hit = stk.get(turn)
    if hit is not None:
        lab, tier = hit
        if lab == 'unrelated':
            sg = 0.0
            d = 'unrelated-zeroed'
        else:
            sg = SIGN.get(lab, 0.0) * TW.get(tier, 0.7)
    else:
        sg = SIGN.get((r.get('stance') or '').lower(), 0.0)
    g = press_gold(r.get('url'), r.get('title'))
    if g is not None:
        sg = SIGN[g]
    if not m:
        d = 'unresolved-member'
    elif sg == 0.0:
        if d != 'unrelated-zeroed':
            d = 'neutral-zeroed'
    else:
        try:
            pv = min(3.0, abs(float(r.get('press_value'))))
        except (TypeError, ValueError):
            pv = 0.0
        if pv == 0.0:
            d = 'zero-intensity'
        elif not cats:
            d = 'no-policy-domain'
        else:
            d = 'used'
            n_used += 1
            members_nz.add(m)
    disp[d] += 1
    rows_audit.append({'url': r.get('url'), 'member_source': r.get('member'), 'src': r['_src'],
                       'declared': declared, 'effective': cats, 'basis': route['basis'],
                       'disposition': d})

print('\nrows scored / disposition (my replication):')
for k, v in sorted(disp.items(), key=lambda kv: -kv[1]):
    print('   %-22s %6d' % (k, v))
print('   %-22s %6d   <- must equal rows ingested' % ('TOTAL', sum(disp.values())))
print('members with nonzero press signal: %d' % len(members_nz))

print('\nrouting basis (my replication):')
for k, v in sorted(basis.items(), key=lambda kv: -kv[1]):
    print('   %-26s %6d' % (k, v))

# ---- 3. CROSS-CHECK against the engine's own persisted ledger --------------------------------
print('\n-- 3. CROSS-CHECK vs the engine-written ledgers --')
meta = json.load(io.open(os.path.join(ROOT, 'data', 'stance', 'press_component_meta.json'), encoding='utf-8'))
aud = json.load(io.open(os.path.join(ROOT, 'data', 'stance', 'press_domain_routing_audit.json'), encoding='utf-8'))
print('press_component_meta.json  tone_rows=%s  articles_used=%s  members_nonzero=%s'
      % (meta.get('tone_rows'), meta.get('articles_used'), meta.get('members_nonzero')))
print('press_domain_routing_audit.json rows=%d' % len(aud.get('rows') or []))
eng_disp = collections.Counter(x['scoring_disposition'] for x in aud['rows'])
eng_basis = collections.Counter(x['routing_basis'] for x in aud['rows'])
print('\n%-22s %10s %10s %8s' % ('disposition', 'engine', 'mine', 'delta'))
for k in sorted(set(eng_disp) | set(disp)):
    print('%-22s %10d %10d %8d' % (k, eng_disp.get(k, 0), disp.get(k, 0), disp.get(k, 0) - eng_disp.get(k, 0)))
print('\n%-26s %10s %10s %8s' % ('routing basis', 'engine', 'mine', 'delta'))
for k in sorted(set(eng_basis) | set(basis)):
    print('%-26s %10d %10d %8d' % (k, eng_basis.get(k, 0), basis.get(k, 0), basis.get(k, 0) - eng_basis.get(k, 0)))

print('\ninput sha256 recorded in press_component_meta.json vs live files NOW:')
for rel, h in (meta.get('inputs_sha256') or {}).items():
    p = os.path.normpath(os.path.join(ROOT, rel))
    if os.path.exists(p):
        now = sha(p)
        print('   %-60s %s' % (rel, 'MATCH' if now == h else 'CHANGED  receipt=%s now=%s' % (h[:12], now[:12])))
    else:
        print('   %-60s MISSING ON DISK' % rel)

# ---- 4. ROUTING: categories routed but not writable ------------------------------------------
print('\n-- 4. ROUTING / DISPLAY-COLUMN CHECK --')
print('categories the router produced that press_raw_original.json has no key for'
      ' (dropped by `_cats=[c for c in _route["categories"] if c in ORIG]`):')
if routed_not_in_orig:
    for k, v in sorted(routed_not_in_orig.items(), key=lambda kv: -kv[1]):
        print('   %-34s %6d rows' % (k, v))
else:
    print('   (none)')
print('\neffective category -> rows (only `used`+non-used alike, counted on every ingested row):')
for k, v in sorted(effcat.items(), key=lambda kv: -kv[1]):
    print('   %-34s %6d' % (k, v))
print('\ndeclared categories DISCARDED by the router (declared_specific not confirmed):')
for k, v in sorted(declared_lost.items(), key=lambda kv: -kv[1]):
    print('   %-34s %6d' % (k, v))

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r1_press_rows.json')
json.dump({'schema': 'laneA-press-row-census-v1', 'rows': rows_audit}, io.open(OUT, 'w', encoding='utf-8'))
print('\nwrote per-row census: %s (%d rows)' % (os.path.basename(OUT), len(rows_audit)))
print('DONE R1')
