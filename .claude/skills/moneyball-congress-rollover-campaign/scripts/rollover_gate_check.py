# -*- coding: utf-8 -*-
"""120th-Congress rollover readiness gate check (moneyball-congress-rollover-campaign skill).

READ-ONLY. Stdlib-only. No fec/ imports (import == execution over there). Prints a
readiness checklist and exits 0 (informational) or 1 with --strict if anything is BLOCKED.

Usage (from the repo root, path quoted because it contains spaces):
    cd "C:\\Users\\pgoff\\OneDrive\\Desktop\\Melange Systems"
    python ".claude\\skills\\moneyball-congress-rollover-campaign\\scripts\\rollover_gate_check.py"
    python ".claude\\skills\\moneyball-congress-rollover-campaign\\scripts\\rollover_gate_check.py" --online
    python ".claude\\skills\\moneyball-congress-rollover-campaign\\scripts\\rollover_gate_check.py" --strict

Root resolution: env MONEYBALL_ROOT, else the hard-coded live-tree path at ROOT below, so this
read-only tool checks the live tree even when run from a worktree. It does NOT mirror
fec/paths.py:7-8, which sets ROOT to MONEYBALL_ROOT when set, else to the parent of the imported
paths.py (a script run from a git worktree then targets that worktree's EMPTY data plane); see
moneyball-change-control law 7. paths.py is never imported here. (Corrected 2026-09-30; verified
against fec/paths.py:7-8.) --online adds availability probes for the voteview HS120 roster and
the FEC 2026-cycle bulk zips (HEAD-style requests; nothing is downloaded).
"""
import os, sys, json, csv, glob, argparse, datetime

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # Windows console convention
except Exception:
    pass

ROOT = os.environ.get('MONEYBALL_ROOT', r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems')
NEW_CONGRESS = int(os.environ.get('ROLLOVER_CONGRESS', '120'))
NEW_CYCLE = int(os.environ.get('ROLLOVER_CYCLE', '2026'))     # FEC 2-year cycle label (2025-26)
CY2 = str(NEW_CYCLE)[-2:]                                      # '26'

READY, PENDING, BLOCKED, INFO = 'READY  ', 'PENDING', 'BLOCKED', 'INFO   '
_rows = []
def row(status, name, detail=''):
    _rows.append((status, name, detail))
    print(' [%s] %-52s %s' % (status, name, detail))

def main():
    ap = argparse.ArgumentParser(description='120th-Congress rollover readiness check (read-only)')
    ap.add_argument('--online', action='store_true', help='probe voteview + fec.gov for new-congress files')
    ap.add_argument('--strict', action='store_true', help='exit 1 if anything is BLOCKED')
    a = ap.parse_args()

    print('ROLLOVER GATE CHECK — %sth Congress / %d FEC cycle — %s' % (
        NEW_CONGRESS, NEW_CYCLE, datetime.date.today().isoformat()))
    print('root: %s\n' % ROOT)

    # ---- 1. Root + core artifacts -------------------------------------------------
    if not os.path.isdir(ROOT):
        row(BLOCKED, 'live data tree exists', ROOT + ' NOT FOUND (set MONEYBALL_ROOT)')
        return finish(a)
    row(READY, 'live data tree exists', ROOT)

    cong_p = os.path.join(ROOT, 'congestion.json')
    n = house = senate = nobio = 0
    keys17 = None
    if os.path.exists(cong_p):
        try:
            d = json.load(open(cong_p, encoding='utf-8'))
            n = len(d)
            house = sum(1 for m in d if m.get('chamber') == 'House')
            senate = sum(1 for m in d if m.get('chamber') == 'Senate')
            nobio = sum(1 for m in d if not m.get('bioguide'))
            keys17 = sorted(d[0]) if d else []
            ok_schema = len(keys17) == 17 and 'member' in keys17 and 'net_lean' in keys17
            row(READY if ok_schema else BLOCKED, 'congestion.json shape',
                '%d members (%dH/%dS), %d keys, %d missing bioguide' % (n, house, senate, len(keys17), nobio))
        except Exception as e:
            row(BLOCKED, 'congestion.json parses', str(e)[:80])
    else:
        row(BLOCKED, 'congestion.json present', 'missing from live root')

    wb = os.path.join(ROOT, 'Moneyball Main Version - Blended.xlsx')
    row(READY if os.path.exists(wb) else BLOCKED, 'workbook present', os.path.basename(wb))

    # ---- 2. Roster capacity math ---------------------------------------------------
    # Workbook member rows 3..535 hold exactly 533 members; a full new Congress is 535.
    row(INFO, 'workbook roster capacity', 'rows 3..535 = 533 slots; full Congress = 535 -> '
        'if new roster > 533, workbook restructure + range(3,536) window change (Paul + change control)')

    # ---- 3. Voteview rosters -------------------------------------------------------
    votes = os.path.join(ROOT, 'votes')
    hs_new = os.path.join(votes, 'HS%d_members.csv' % NEW_CONGRESS)
    hs_cur = os.path.join(votes, 'HS119_members.csv')
    row(READY if os.path.exists(hs_cur) else BLOCKED, 'votes/HS119_members.csv (current)', '')
    if os.path.exists(hs_new):
        try:
            rows_ = list(csv.DictReader(open(hs_new, encoding='utf-8', errors='replace')))
            memb = [r for r in rows_ if r.get('chamber') in ('House', 'Senate')]
            blank = sum(1 for r in memb if not (r.get('bioguide_id') or '').strip())
            uniq = len({(r.get('bioguide_id') or '').strip() for r in memb} - {''})
            status = READY if (memb and blank / max(1, len(memb)) < 0.01) else PENDING
            row(status, 'votes/HS%d_members.csv' % NEW_CONGRESS,
                '%d member rows, %d unique bioguides, %d blank bioguides' % (len(memb), uniq, blank))
            if uniq > 533:
                row(INFO, 'new roster exceeds 533-slot workbook capacity',
                    '%d unique members > 533 — Phase 1 item 2 (capacity) is MANDATORY' % uniq)
        except Exception as e:
            row(PENDING, 'votes/HS%d_members.csv parses' % NEW_CONGRESS, str(e)[:80])
    else:
        row(PENDING, 'votes/HS%d_members.csv' % NEW_CONGRESS,
            'not yet placed (voteview publishes after the new Congress first votes)')

    hsall = os.path.join(votes, 'HSall_members.csv')
    if os.path.exists(hsall):
        try:
            mx = 0
            for r in csv.DictReader(open(hsall, encoding='utf-8', errors='replace')):
                c = int(r.get('congress') or 0)
                if c > mx: mx = c
            row(READY if mx >= NEW_CONGRESS else PENDING, 'HSall_members.csv vintage',
                'max congress = %d (need %d for new-roster tenure joins)' % (mx, NEW_CONGRESS))
        except Exception as e:
            row(PENDING, 'HSall_members.csv parses', str(e)[:80])
    else:
        row(BLOCKED, 'votes/HSall_members.csv present', 'missing')

    # ---- 4. legislators.csv --------------------------------------------------------
    leg = os.path.join(ROOT, 'fec', 'legislators.csv')
    if os.path.exists(leg):
        try:
            f = open(leg, encoding='utf-8'); hdr = next(csv.reader(f))
            need = ['last_name', 'first_name', 'nickname', 'full_name', 'type', 'state',
                    'bioguide_id', 'fec_ids', 'votesmart_id']
            missing = [c for c in need if c not in hdr]
            nrows = sum(1 for _ in f)
            age_d = (datetime.date.today() -
                     datetime.date.fromtimestamp(os.path.getmtime(leg))).days
            row(READY if not missing else BLOCKED, 'fec/legislators.csv header + rows',
                '%d rows, %d days old%s' % (nrows, age_d,
                ('; MISSING cols: %s' % missing) if missing else ''))
            if age_d > 200:
                row(INFO, 'legislators.csv is stale', 'refresh from unitedstates legislators-current.csv '
                    'at rollover — but check prereg fingerprints FIRST (fence F8)')
        except Exception as e:
            row(BLOCKED, 'fec/legislators.csv parses', str(e)[:80])
    else:
        row(BLOCKED, 'fec/legislators.csv present', 'missing')

    # ---- 5. FEC bulk files: current-cycle extractions + new-cycle staging ----------
    fecdir = os.path.join(ROOT, 'fec')
    for fn, why in [('itpas2.txt', '2024 money input (regression-proof input — keep)'),
                    ('weball24.txt', '2024 receipts input (regression-proof input — keep)')]:
        p = os.path.join(fecdir, fn)
        row(READY if os.path.exists(p) else BLOCKED, 'fec/' + fn, why)
    staged = 0
    for fn in ('itpas2_%s.txt' % CY2, 'weball%s.txt' % CY2, 'pas2%s.zip' % CY2, 'weball%s.zip' % CY2):
        p = os.path.join(fecdir, fn)
        if os.path.exists(p):
            staged += 1
            row(READY, 'fec/%s staged (%d-cycle)' % (fn, NEW_CYCLE),
                '%.1f MB' % (os.path.getsize(p) / 1e6))
    if staged == 0:
        row(PENDING, '%d-cycle FEC files staged' % NEW_CYCLE,
            'none found (expected e.g. fec/itpas2_%s.txt, fec/weball%s.txt)' % (CY2, CY2))

    # ---- 6. External exports (Paul's) ----------------------------------------------
    bp_new = (glob.glob(os.path.join(ROOT, 'Ballotpedia_%dth_CU_Influence_*.xlsx' % NEW_CONGRESS)) +
              glob.glob(os.path.join(ROOT, 'archive', 'Ballotpedia_%dth_CU_Influence_*.xlsx' % NEW_CONGRESS)))
    row(READY if bp_new else PENDING, 'Ballotpedia_%dth export' % NEW_CONGRESS,
        (os.path.basename(bp_new[-1]) if bp_new else "awaiting Paul's export (glob also needs the code change)"))
    nets = [p for p in glob.glob(os.path.join(ROOT, 'congress_cosponsor_network_*.xlsx'))
            if 'AUG' not in os.path.basename(p)]
    if nets:
        newest = max(nets, key=os.path.getmtime)
        age_d = (datetime.date.today() - datetime.date.fromtimestamp(os.path.getmtime(newest))).days
        row(READY if age_d < 60 else PENDING, 'cosponsor network base export',
            '%s (%d days old%s)' % (os.path.basename(newest), age_d,
                                    '; STALE — new-Congress export needed' if age_d >= 60 else ''))
    else:
        row(BLOCKED, 'cosponsor network base export', 'no non-AUG congress_cosponsor_network_*.xlsx found')

    # ---- 7. Rollover housekeeping files ---------------------------------------------
    ret = os.path.join(fecdir, 'retiring_members.txt')
    if os.path.exists(ret):
        names = [l for l in open(ret, encoding='utf-8') if l.strip() and not l.startswith('#')]
        row(INFO, 'fec/retiring_members.txt', '%d names (must be RESET for the new cycle at rollover)' % len(names))
    else:
        row(PENDING, 'fec/retiring_members.txt', 'missing (hook file)')
    smj = os.path.join(ROOT, 'legislators_social_media.json')
    if os.path.exists(smj):
        age_d = (datetime.date.today() - datetime.date.fromtimestamp(os.path.getmtime(smj))).days
        row(INFO, 'legislators_social_media.json cache', '%d days old (rename aside at rollover so '
            'tweet_collector init re-downloads)' % age_d)

    # ---- 8. Online probes (optional) ------------------------------------------------
    if a.online:
        print('\nonline probes (nothing downloaded):')
        import urllib.request
        def probe(url):
            req = urllib.request.Request(url, method='HEAD',
                                         headers={'User-Agent': 'moneyball-rollover-gate-check'})
            try:
                with urllib.request.urlopen(req, timeout=20) as r:
                    return r.status, r.headers.get('Content-Length')
            except Exception as e:
                code = getattr(e, 'code', None)
                return code if code else str(e)[:40], None
        urls = ['https://voteview.com/static/data/out/members/HS%d_members.csv' % NEW_CONGRESS,
                'https://unitedstates.github.io/congress-legislators/legislators-current.csv'] + \
               ['https://www.fec.gov/files/bulk-downloads/%d/%s%s.zip' % (NEW_CYCLE, base, CY2)
                for base in ('ccl', 'cm', 'cn', 'pas2', 'weball')]
        for u in urls:
            st, ln = probe(u)
            ok = (st == 200)
            row(READY if ok else PENDING, 'online: ' + u.split('/')[-1],
                'HTTP %s%s%s' % (st, (' %.1f MB' % (int(ln) / 1e6)) if (ok and ln) else '',
                                 '' if ok else ' (if persistent, the URL pattern may have changed - check the site)'))

    return finish(a)

def finish(a):
    nb = sum(1 for s, _, _ in _rows if s == BLOCKED)
    np_ = sum(1 for s, _, _ in _rows if s == PENDING)
    nr = sum(1 for s, _, _ in _rows if s == READY)
    print('\nSUMMARY: %d READY | %d PENDING | %d BLOCKED' % (nr, np_, nb))
    print('Next steps live in the skill: .claude/skills/moneyball-congress-rollover-campaign/SKILL.md')
    return 1 if (a.strict and nb) else 0

if __name__ == '__main__':
    sys.exit(main())
