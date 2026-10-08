# -*- coding: utf-8 -*-
"""FIX R1: end-to-end exercise of the WIRED producer on a SYNTHETIC root, both dial positions.

Nothing here touches the live tree. MONEYBALL_ROOT and MONEYBALL_DRAFT are pointed at a
throwaway directory under this session's scratchpad, the whole synthetic world is built there,
and member_reference_layer.py is run as a subprocess (never imported) exactly the way
fec/tests/infra/test_reference_extraction.py and test_reference_cache.py run it. The classifier
is a test double, so no API call is made and no key is read.

WHY IT IS NOT A REGISTERED TEST. Line 245 of the producer imports members.reference_cache,
which exists ONLY as an untracked file in the live tree (FINDINGS.md section X: "main cannot
run the reference layer"). This script borrows it by putting the live fec/ LAST on PYTHONPATH,
so the namespace package `members` spans both trees: reference_cache resolves from LIVE while
member_reference_layer and reference_filters resolve from the worktree. A kernel suite cannot
depend on an untracked file, so the registered suite
(fec/tests/members/test_reference_admission_filters.py) tests the pure rules plus the wiring
as text, and this receipt is the end-to-end evidence."""
import io, json, os, shutil, sqlite3, subprocess, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
WORK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
        r'\unfinished-work-handoff-a3bbad')
SCRATCH = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
           r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad'
           r'\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\fixR1')
SCRIPT = os.path.join(WORK, 'fec', 'members', 'member_reference_layer.py')

ROSTER = ['Ada Alpher', 'Ben Bravo', 'Cy Charlie', 'Dee Delta', 'Eli Echo', 'Fay Foxtrot',
          'Gus Golf', 'Hal Hotel', 'Ida India', 'Jay Juliet', 'Kim Kilo', 'Lou Lima']
SPEAKER = 'Ada Alpher'
DUPE = ('I am proud to partner with Ben Bravo on this legislation and I think his leadership '
        'is great for our credit unions.')
ROLL = ('Ben Bravo, Cy Charlie, Dee Delta, Eli Echo, Fay Foxtrot, Gus Golf, Hal Hotel, '
        'Ida India, Jay Juliet, Kim Kilo, Lou Lima, and Ada Alpher.')
THIRD_PARTY = ('https://www.americascreditunions.org/news/x', 'Cy Charlie and Alpher spar over interchange')
OWN_DOMAIN = ('https://alpher.house.gov/media/y', 'Dee Delta joins Alpher on a great bill')

DOUBLE = """import runpy, sys, types
fake = types.ModuleType('classifier_runtime')
fake.classify_json = lambda *a: ({'cls': 'positive', 'reason': 'synthetic support'},
                                 {'transport': 'test-double'})
sys.modules['classifier_runtime'] = fake
sys.argv = [sys.argv[1], '--score', '--go']
runpy.run_path(sys.argv[0], run_name='__main__')
"""


def build_world(root, draft):
    for d in (root, draft):
        if os.path.isdir(d): shutil.rmtree(d)
    os.makedirs(os.path.join(root, 'data', 'engine'))
    os.makedirs(os.path.join(root, 'data', 'members'))
    os.makedirs(draft)
    io.open(os.path.join(root, 'data', 'engine', 'congestion.json'), 'w', encoding='utf-8').write(
        json.dumps([{'member': m, 'bioguide': 'T%02d' % i,
                     'chamber': 'Senate' if i % 2 else 'House'} for i, m in enumerate(ROSTER)]))
    io.open(os.path.join(root, 'data', 'engine', 'sentinel_admission_policy.json'), 'w',
            encoding='utf-8').write(json.dumps({'reference_transport': 'claude-cli',
                                                'reference_model': 'test-only',
                                                'reference_batch_limit': 64}))
    db = sqlite3.connect(os.path.join(root, 'social_media.db'))
    try:
        db.execute('CREATE TABLE speeches(member,date,source,text)')
        db.execute('CREATE TABLE members(bioguide,twitter)')
        # the SAME window twice, from two feeds: n_raw must keep both, n_scored must count one
        db.execute('INSERT INTO speeches VALUES (?,?,?,?)', (SPEAKER, '2026-09-01', 'CREC', DUPE))
        db.execute('INSERT INTO speeches VALUES (?,?,?,?)', (SPEAKER, '2026-09-02', 'INTERVIEW', DUPE))
        # a roll-call roster: eleven colleagues named, none of them referenced
        db.execute('INSERT INTO speeches VALUES (?,?,?,?)', (SPEAKER, '2026-09-03', 'CREC', ROLL))
        db.commit()
    finally:
        db.close()   # 'with sqlite3.connect(...)' commits but does NOT close: the file stays locked
    with io.open(os.path.join(draft, 'cu_press_stance_tone.csv'), 'w', encoding='utf-8', newline='') as f:
        f.write('member,url,title,date,source\n')
        for url, title in (THIRD_PARTY, OWN_DOMAIN):
            f.write('%s,%s,%s,2026-09-04,PRESS\n' % (SPEAKER, url, title))


def run(dials):
    root = os.path.join(SCRATCH, 'e2e_root'); draft = os.path.join(SCRATCH, 'e2e_draft')
    build_world(root, draft)
    env = dict(os.environ)
    env['MONEYBALL_ROOT'] = root
    env['MONEYBALL_DRAFT'] = draft
    # members.reference_cache lives only in the live tree; borrow it without copying it.
    env['PYTHONPATH'] = os.path.join(LIVE, 'fec')
    env.pop('REF_PRESS_OWN_DOMAIN', None); env.pop('REF_ROSTER_FILTER', None)
    env.pop('REF_IDENTICAL_ONCE', None)
    env.update(dials)
    r = subprocess.run([sys.executable, '-c', DOUBLE, SCRIPT], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env, timeout=180)
    art = json.load(io.open(os.path.join(root, 'member_references.json'), encoding='utf-8'))
    return r, art


def show(label, dials):
    r, art = run(dials)
    print('=' * 92)
    print('%s   env=%s' % (label, dials or '{} (shipped defaults)'))
    print('=' * 92)
    print('producer exit=%d' % r.returncode)
    for line in (r.stdout or '').strip().splitlines():
        print('   | %s' % line)
    if r.returncode != 0:
        print(r.stderr[-2000:]); sys.exit(1)
    print('artifact top-level keys : %s' % sorted(art))
    print('admission_filters       : %s' % json.dumps(art.get('admission_filters'), sort_keys=True))
    print('edges (%d):' % len(art['edges']))
    for e in sorted(art['edges'], key=lambda x: (x['a'], x['b'])):
        print('   %-12s -> %-12s n_raw=%-2d n_scored=%-2d pos=%-2d neg=%-2d neu=%-2d form=%-2d net=%+0.2f %s'
              % (e['a'], e['b'], e['n_raw'], e['n_scored'], e['pos'], e['neg'], e['neu'],
                 e.get('formality_dropped', 0), e['net'], e.get('sources')))
    print()
    return art


ON = show('ALL THREE FILTERS ON (the shipped default)', {})
OFF = show('ALL THREE FILTERS OFF (the documented rollback)',
           {'REF_PRESS_OWN_DOMAIN': '0', 'REF_ROSTER_FILTER': '0', 'REF_IDENTICAL_ONCE': '0'})
ONLY_DUP = show('ONLY REF_IDENTICAL_ONCE ON', {'REF_PRESS_OWN_DOMAIN': '0', 'REF_ROSTER_FILTER': '0'})

print('=' * 92)
print('ASSERTIONS')
print('=' * 92)
P = F = 0
def ok(name, cond, detail=''):
    global P, F
    if cond: P += 1; print('  OK   ' + name)
    else:    F += 1; print('  FAIL ' + name + ('  :: ' + str(detail) if detail else ''))

EON = {(e['a'], e['b']): e for e in ON['edges']}
EOFF = {(e['a'], e['b']): e for e in OFF['edges']}
EDUP = {(e['a'], e['b']): e for e in ONLY_DUP['edges']}
bravo = (SPEAKER, 'Ben Bravo')
ok('the duplicated window is two raw mentions and one scored window',
   EON[bravo]['n_raw'] == 2 and EON[bravo]['n_scored'] == 1 and EON[bravo]['pos'] == 1, EON.get(bravo))
# With the other two dials off this edge carries THREE windows (two copies of DUPE plus the
# roster window), so REF_IDENTICAL_ONCE alone must take n_scored from 3 to 2 and leave n_raw at 3.
ok('REF_IDENTICAL_ONCE removes exactly the repeat, and only from n_scored',
   EOFF[bravo]['n_raw'] == EDUP[bravo]['n_raw'] == 3 and
   EOFF[bravo]['n_scored'] == 3 and EDUP[bravo]['n_scored'] == 2,
   (EOFF.get(bravo), EDUP.get(bravo)))
ok('net is unchanged by the collapse (identical windows carry one label)',
   EON[bravo]['net'] == EDUP[bravo]['net'] == EOFF[bravo]['net'] == 1.0)
ok('the third-party PRESS article mints no edge',
   (SPEAKER, 'Cy Charlie') not in EON and (SPEAKER, 'Cy Charlie') in EOFF)
ok('the own-domain PRESS article still does',
   EON[(SPEAKER, 'Dee Delta')]['sources'] == {'PRESS': 1})
ok('the roll-call roster mints no edge at all',
   not any(ab for ab in EON if ab[1] in ('Eli Echo', 'Fay Foxtrot', 'Gus Golf', 'Hal Hotel',
                                         'Ida India', 'Jay Juliet', 'Kim Kilo', 'Lou Lima')))
ok('with both dials off every roster name is an edge again',
   sum(1 for ab in EOFF if ab[1] in ('Eli Echo', 'Fay Foxtrot', 'Gus Golf', 'Hal Hotel',
                                     'Ida India', 'Jay Juliet', 'Kim Kilo', 'Lou Lima')) == 8)
ok('the edge set shrinks from 11 to 2', len(EOFF) == 11 and len(EON) == 2, (len(EOFF), len(EON)))
ok('the census closes: 1 press + 11 roster + 1 repeat',
   ON['admission_filters']['excluded'] == {'press_third_party_domain': 1, 'roster_list_window': 11,
                                           'identical_window_repeat': 1},
   ON['admission_filters']['excluded'])
ok('the rollback census is empty and the block still reports the dials',
   OFF['admission_filters']['excluded_total'] == 0 and
   OFF['admission_filters']['dials'] == {'REF_PRESS_OWN_DOMAIN': '0', 'REF_ROSTER_FILTER': '0',
                                         'REF_IDENTICAL_ONCE': '0'})
ok('the block is ADDITIVE: every pre-existing top-level key survives',
   set(OFF) - {'admission_filters'} == {'edges', 'dyad_cap', 'model', 'provenance'}, sorted(OFF))
ok('audit_full\'s edge invariant holds in both positions (n_scored >= pos+neg)',
   all(e['n_scored'] >= e['pos'] + e['neg'] for e in ON['edges'] + OFF['edges']))
# The three consumers read only doc['edges'] and per-edge keys; prove the extra key is inert.
for name, reader in (('build_dashboard_bundle.py:236', lambda d: [e for e in d['edges'] if e.get('n_scored', 0) >= 2]),
                     ('make_member_desk.py:403', lambda d: (d or {}).get('edges', [])),
                     ('audit_full.py:1147', lambda d: d.get('edges', []))):
    try:
        reader(ON); good = True
    except Exception as exc:
        good = False; print(exc)
    ok('consumer read pattern %s tolerates the extra key' % name, good)
print()
print('END-TO-END SYNTHETIC \u2014 %d passed, %d FAILED' % (P, F))
sys.exit(1 if F else 0)
