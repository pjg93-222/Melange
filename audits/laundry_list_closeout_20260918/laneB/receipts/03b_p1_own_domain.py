# -*- coding: utf-8 -*-
"""LANE B P1: the PRESS passes carry no own-domain gate.

RATIFIED RULE (fec/stance/resolve_attribution_domain.py:45-47, verbatim):
    def domain_class(url):
        ul = url.lower()
        return 'own' if ('.house.gov' in ul or '.senate.gov' in ul) else 'thirdparty'

Measured two ways:
  R1  ratified 2-class rule exactly as written (chamber-generic).
  R2  stricter per-member check (my extension, labelled as such): does the URL host's leading
      label match the SPEAKING member's own surname?  house.gov/senate.gov member sites are
      <surname>.house.gov / <surname>.senate.gov, so R1 'own' + R2 mismatch = another member's
      official site, which is not the speaker's own domain either.
READ-ONLY.  Consumes SCRATCH/refs.jsonl produced by 02c_rederive.py."""
import collections, io, json, os, re, sys, unicodedata
from urllib.parse import urlsplit
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
SCRATCH = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
           r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad'
           r'\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneB')

refs = [json.loads(l) for l in io.open(os.path.join(SCRATCH, 'refs.jsonl'), encoding='utf-8')]
art = json.load(io.open(LIVE + r'\member_references.json', encoding='utf-8'))
AE = {(e['a'], e['b']): e for e in art['edges']}
print('refs %d | artifact edges %d' % (len(refs), len(AE)))

# official_mentions.jsonl carries article_url; graft it onto the POM refs by (host,mentioned,date,title)
om_idx = {}
for ln in io.open(os.path.join(LIVE, 'data', 'press', 'official_mentions.jsonl'), encoding='utf-8'):
    try: r = json.loads(ln)
    except ValueError: continue
    om_idx.setdefault((r.get('host_member'), r.get('mentioned_member'), r.get('date') or '',
                       ((r.get('evidence') or r.get('title') or '')[:1200])), r.get('article_url') or '')
graft = 0
for r in refs:
    if r['src'] == 'PRESS_OFFICIAL_MENTION':
        u = om_idx.get((r['a'], r['b'], r['date'], r['w']))
        if u: r['_url'] = u; graft += 1
print('POM refs with article_url grafted: %d of %d' % (graft, sum(1 for r in refs if r['src'] == 'PRESS_OFFICIAL_MENTION')))


def domain_class(url):                      # resolve_attribution_domain.py:45-47 VERBATIM
    ul = (url or '').lower()
    return 'own' if ('.house.gov' in ul or '.senate.gov' in ul) else 'thirdparty'


def nrm(s):
    s = unicodedata.normalize('NFD', s or ''); s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z]', '', s.lower())


def host_of(u):
    try: return urlsplit(u or '').netloc.lower().lstrip('.')
    except ValueError: return ''


def own_member_domain(url, member):
    """R2 (my extension): leading host label vs the speaking member's surname / full-name joins."""
    h = host_of(url)
    if h.startswith('www.'): h = h[4:]
    if not ('.house.gov' in h or '.senate.gov' in h): return False
    lead = h.split('.')[0]
    parts = [p for p in re.split(r'[^A-Za-z]+', member) if p]
    if not parts: return False
    sur = nrm(parts[-1]); first = nrm(parts[0])
    cands = {sur, first + sur, sur + first, nrm(''.join(parts)), nrm(''.join(parts[1:])),
             first[:1] + sur, nrm(parts[-2]) + sur if len(parts) > 2 else ''}
    cands.discard('')
    return nrm(lead) in cands or any(nrm(lead).startswith(c) and len(c) >= 5 for c in cands)


print()
print('=' * 78)
print('P1 : PRESS pass (src=PRESS, headline of a tone-csv article)')
print('=' * 78)
P = [r for r in refs if r['src'] == 'PRESS']
print('re-derived PRESS mentions : %d   (artifact PRESS counter 32; delta sits on dropped dyads)' % len(P))
cls = collections.Counter(domain_class(r.get('_url')) for r in P)
print('R1 ratified rule  : %s' % dict(cls))
r2 = collections.Counter('own_member' if own_member_domain(r.get('_url'), r['a']) else
                         ('other_member_gov' if domain_class(r.get('_url')) == 'own' else 'thirdparty') for r in P)
print('R2 per-member     : %s' % dict(r2))
hosts = collections.Counter(host_of(r.get('_url')) for r in P)
print('hosts:')
for h, n in hosts.most_common():
    print('   %-46s %4d   [%s]' % (h[:46], n, domain_class('https://' + h)))
in_art = [r for r in P if (r['a'], r['b']) in AE]
third = [r for r in P if domain_class(r.get('_url')) == 'thirdparty']
third_art = [r for r in third if (r['a'], r['b']) in AE]
print()
print('PRESS mentions landing on a shipped edge      : %d' % len(in_art))
print('PRESS mentions from a NON-own domain (R1)     : %d  (%.0f%% of PRESS)' % (len(third), 100.0 * len(third) / max(1, len(P))))
print('  ...of which land on a shipped edge          : %d' % len(third_art))
print('shipped edges touched by a thirdparty PRESS row: %d' % len({(r['a'], r['b']) for r in third_art}))
e_press_only = {(r['a'], r['b']) for r in third_art
                if (AE[(r['a'], r['b'])].get('sources') or {}).get('PRESS', 0) == sum((AE[(r['a'], r['b'])].get('sources') or {}).values())}
print('shipped edges whose ENTIRE raw support is PRESS and thirdparty: %d' % len(e_press_only))
for k in sorted(e_press_only):
    e = AE[k]
    print('    %-30s -> %-30s n_raw=%d n_scored=%d net=%+0.2f' % (k[0][:30], k[1][:30], e['n_raw'], e['n_scored'], e['net']))
print()
print('every thirdparty PRESS mention (speaker -> target | host | title):')
for r in third:
    print('   %-26s -> %-26s | %-34s | %s' % (r['a'][:26], r['b'][:26], host_of(r.get('_url'))[:34],
                                              (r.get('_title') or r['w'])[:86]))

print()
print('=' * 78)
print('P1 : PRESS_OFFICIAL_MENTION pass (typed press-body feed)')
print('=' * 78)
Q = [r for r in refs if r['src'] == 'PRESS_OFFICIAL_MENTION']
print('re-derived POM mentions : %d   (artifact POM counter 2538)' % len(Q))
q1 = collections.Counter(domain_class(r.get('_url')) for r in Q)
print('R1 ratified rule : %s' % dict(q1))
q2 = collections.Counter('own_member' if own_member_domain(r.get('_url'), r['a']) else
                         ('other_member_gov' if domain_class(r.get('_url')) == 'own' else 'thirdparty') for r in Q)
print('R2 per-member    : %s' % dict(q2))
qt = [r for r in Q if domain_class(r.get('_url')) == 'thirdparty']
print('POM mentions from a NON-own domain (R1) : %d' % len(qt))
print('  hosts: %s' % collections.Counter(host_of(r.get('_url')) for r in qt).most_common(20))
qo = [r for r in Q if domain_class(r.get('_url')) == 'own' and not own_member_domain(r.get('_url'), r['a'])]
print('POM mentions on ANOTHER member\'s .gov site (R1 own, R2 mismatch): %d' % len(qo))
print('  first 15 (speaker -> target | host):')
for r in qo[:15]:
    print('     %-26s -> %-26s | %s' % (r['a'][:26], r['b'][:26], host_of(r.get('_url'))))
print('  distinct speakers affected: %d' % len({r['a'] for r in qo}))
print('  shipped edges touched     : %d' % len({(r['a'], r['b']) for r in qo if (r['a'], r['b']) in AE}))
print()
print('POM edges in artifact                    : %d' % len({(r['a'], r['b']) for r in Q if (r['a'], r['b']) in AE}))
pom_only = [k for k in AE if set((AE[k].get('sources') or {})) == {'PRESS_OFFICIAL_MENTION'}]
print('shipped edges supported ONLY by POM      : %d' % len(pom_only))
print('  of those with n_scored>=2 (drawn)      : %d' % sum(1 for k in pom_only if AE[k]['n_scored'] >= 2))

print()
print('=' * 78)
print('JULY "MAGAZINER CLUSTER" — still present?')
print('=' * 78)
mag = [r for r in refs if 'magaziner' in (r['a'] + ' ' + r['b']).lower()]
print('total re-derived mentions touching Magaziner (either end): %d' % len(mag))
print('by source: %s' % dict(collections.Counter(r['src'] for r in mag)))
magp = [r for r in mag if r['src'] in ('PRESS', 'PRESS_OFFICIAL_MENTION')]
print('press-family mentions touching Magaziner: %d' % len(magp))
for r in magp[:40]:
    print('   [%s] %-24s -> %-24s | host=%-30s | %s' % (r['src'][:4], r['a'][:24], r['b'][:24],
                                                        host_of(r.get('_url'))[:30], (r.get('_title') or r['w'])[:70]))
mage = [k for k in AE if 'magaziner' in (k[0] + ' ' + k[1]).lower()]
print()
print('shipped edges touching Magaziner: %d' % len(mage))
for k in sorted(mage):
    e = AE[k]
    print('   %-28s -> %-28s n_raw=%-3d n_scored=%-3d net=%+0.2f sources=%s' %
          (k[0][:28], k[1][:28], e['n_raw'], e['n_scored'], e['net'], e.get('sources')))
print()
print('--- thirdparty-press article fan-out census (any single article -> N distinct targets) ---')
fan = collections.defaultdict(set)
for r in refs:
    if r['src'] in ('PRESS', 'PRESS_OFFICIAL_MENTION') and domain_class(r.get('_url')) == 'thirdparty':
        fan[(r['a'], r.get('_url') or r.get('_title') or r['w'][:120])].add(r['b'])
big = sorted(fan.items(), key=lambda kv: -len(kv[1]))
print('thirdparty press (speaker,article) groups: %d | with >=2 distinct targets: %d | >=5: %d' %
      (len(fan), sum(1 for k, v in fan.items() if len(v) >= 2), sum(1 for k, v in fan.items() if len(v) >= 5)))
for (spk, u), tg in big[:12]:
    print('   %-24s x%-2d %-44s -> %s' % (spk[:24], len(tg), str(u)[:44], sorted(tg)[:6]))
print('DONE 03b')
