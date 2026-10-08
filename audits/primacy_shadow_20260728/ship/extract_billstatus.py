#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EXTRACT_BILLSTATUS — mine the staged GovInfo BILLSTATUS store for three things
the primacy framework currently lacks.

    python extract_billstatus.py                                  # auto-locate everything
    python extract_billstatus.py --root "C:\\...\\Melange Systems"
    python extract_billstatus.py --all                            # every bill in the store, not just our universe

WHY THIS EXISTS
---------------
`audits/legfix5/billstatus_bulk_enrichment/fetch_runs/<run>/` holds **14,854 parsed
GovInfo BILLSTATUS records** (fetched 2026-07-26, HTTP 200, sha256-addressed, with a
`receipts/{congress}_{type}_{number}.json` index). Each record carries CRS summaries,
full title lists, sponsors, every cosponsor with `is_original_cosponsor`, all actions
with official action codes, and recorded votes.

That is an order of magnitude more than `member_desk_bundle.json` exposes — the bundle's
`summary` field maxes out at 221 characters and is mostly just the title. Three flags in
`FLAGS.md` are answerable from this store and from nothing else we have:

  F3  ~38% of role weight rests on title regexes  -> CRS summaries give operative text
  F5  the delivery ledger cannot see `reported_out` -> committee-report actions are here
  F8  no `floor_manager` role                       -> action code H30300 names the member

RUN IT ON THE MACHINE THAT HOLDS THE FILES. Over the Cowork device mount, OneDrive
hydrates cold files on demand and blocks in uninterruptible I/O; a full pass is not
feasible remotely. Locally it is a few minutes.

OUTPUTS (written next to this script unless --out is given)
    crs_universe.ndjson        {key, class, crs, titles, sponsor, ncos, norig}
    delivery_candidates.ndjson {key, class, instrument, member_surname, state, date, text}
    cosponsor_role_audit.csv   bundle role coding vs BILLSTATUS is_original_cosponsor
    extract_summary.txt        coverage report — read this first
"""
from __future__ import annotations
import argparse, csv, html, json, os, re, sys

TYPES = [('H.R.', 'hr'), ('S.J.Res.', 'sjres'), ('H.J.Res.', 'hjres'),
         ('H.Con.Res.', 'hconres'), ('S.Con.Res.', 'sconres'),
         ('H.Res.', 'hres'), ('S.Res.', 'sres'), ('S.', 's')]

# "Mr. Hill (AR) moved to suspend the rules and pass the bill."  — official action code H30300
MOVED = re.compile(r'(?:Mr\.|Mrs\.|Ms\.|Miss)\s+([A-Z][A-Za-z\'\-]+)'
                   r'(?:\s+\(([A-Z]{2})\))?\s+moved to suspend the rules', re.I)
REPORTED = re.compile(r'^Reported\b.*?by the (Committee on [^.]+)', re.I)
ORDERED = re.compile(r'^Ordered to be Reported', re.I)
CU = re.compile(r'credit union|National Credit Union|Federal Credit Union Act|\bNCUA\b', re.I)


def strip_html(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', ' ', s or ''))).strip()


def receipt_key(bill, congress):
    for prefix, slug in TYPES:
        if bill.upper().startswith(prefix.upper()):
            num = bill[len(prefix):].strip()
            if num.isdigit():
                return '%s_%s_%s' % (congress, slug, num)
    return None                      # amendments have no top-level BILLSTATUS package


def find_root(explicit):
    if explicit:
        return explicit
    here = os.path.dirname(os.path.abspath(__file__))
    for cand in (os.environ.get('MELANGE_ROOT'),
                 os.path.abspath(os.path.join(here, '..', '..', '..')),
                 os.path.abspath(os.path.join(here, '..', '..')),
                 os.path.expanduser('~/OneDrive/Desktop/Melange Systems'),
                 os.getcwd()):
        if cand and os.path.exists(os.path.join(cand, 'member_desk_bundle.json')):
            return cand
    return None


def find_run(root, explicit):
    if explicit:
        return explicit
    base = os.path.join(root, 'audits', 'legfix5', 'billstatus_bulk_enrichment', 'fetch_runs')
    if not os.path.isdir(base):
        return None
    runs = [os.path.join(base, d) for d in os.listdir(base)
            if os.path.isdir(os.path.join(base, d, 'receipts'))]
    runs.sort(key=os.path.getmtime)
    return runs[-1] if runs else None


def load_record(run, rk):
    with open(os.path.join(run, 'receipts', rk + '.json'), encoding='utf-8') as fh:
        rc = json.load(fh)
    with open(os.path.join(run, 'parsed', 'sha256', rc['parsed_sha256'] + '.json'),
              encoding='utf-8') as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--root'); ap.add_argument('--run'); ap.add_argument('--out')
    ap.add_argument('--tags', help='bill_beneficiary_tags.ndjson (default: next to this script)')
    ap.add_argument('--all', action='store_true',
                    help='every bill in the store, not just the tagged universe')
    a = ap.parse_args(argv)

    root = find_root(a.root)
    if not root:
        print('Cannot find the Melange Systems root. Pass --root.'); return 1
    run = find_run(root, a.run)
    if not run:
        print('Cannot find a BILLSTATUS fetch run under audits/legfix5/'
              'billstatus_bulk_enrichment/fetch_runs/. Pass --run.'); return 1
    out = a.out or os.path.dirname(os.path.abspath(__file__))
    os.makedirs(out, exist_ok=True)

    tags_path = a.tags or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       'bill_beneficiary_tags.ndjson')
    cls_of, jobs = {}, []
    if os.path.exists(tags_path):
        with open(tags_path, encoding='utf-8') as fh:
            for line in fh:
                if not line.strip():
                    continue
                t = json.loads(line)
                bill, cong = str(t['bill']).strip(), str(t['congress']).strip()
                key = '%s|%s' % (bill, cong)
                cls_of[key] = t['class']
                if 'Amdt' in bill:
                    continue
                rk = receipt_key(bill, cong)
                if rk:
                    jobs.append((key, rk))
    elif not a.all:
        print('No tag file at %s — rerun with --all or pass --tags.' % tags_path); return 1

    if a.all:
        seen = {rk for _, rk in jobs}
        for name in sorted(os.listdir(os.path.join(run, 'receipts'))):
            rk = name[:-5]
            if name.endswith('.json') and rk not in seen:
                jobs.append(('STORE:' + rk, rk))

    print('root : %s\nrun  : %s\njobs : %d\n' % (root, run, len(jobs)))

    crs_fh = open(os.path.join(out, 'crs_universe.ndjson'), 'w', encoding='utf-8')
    dl_fh = open(os.path.join(out, 'delivery_candidates.ndjson'), 'w', encoding='utf-8')
    cos_rows, stats = [], {'ok': 0, 'err': 0, 'crs': 0, 'moved': 0, 'reported': 0, 'cu_hits': 0}

    for i, (key, rk) in enumerate(jobs):
        if i % 250 == 0:
            print('  %d/%d' % (i, len(jobs)), flush=True)
        cls = cls_of.get(key, 'out_of_universe')
        try:
            d = load_record(run, rk)
        except Exception as exc:
            stats['err'] += 1
            crs_fh.write(json.dumps({'key': key, 'rk': rk, 'class': cls,
                                     'err': type(exc).__name__}) + '\n')
            continue
        stats['ok'] += 1
        crs = strip_html(' '.join(s.get('text') or '' for s in (d.get('summaries') or [])))
        if crs:
            stats['crs'] += 1
        if crs and CU.search(crs):
            stats['cu_hits'] += 1
        cos = d.get('cosponsors') or []
        norig = sum(1 for c in cos
                    if c.get('is_original_cosponsor') in (True, 'True', 'true'))
        crs_fh.write(json.dumps({
            'key': key, 'rk': rk, 'class': cls, 'crs': crs,
            'cu_in_crs': bool(crs and CU.search(crs)),
            'titles': [t.get('title') or '' for t in (d.get('titles') or [])][:4],
            'sponsor': ((d.get('sponsors') or [{}])[0]).get('full_name'),
            'ncos': len(cos), 'norig': norig,
        }) + '\n')
        cos_rows.append({'key': key, 'class': cls, 'cosponsors': len(cos),
                         'original_cosponsors': norig,
                         'later_cosponsors': len(cos) - norig,
                         'sponsor': ((d.get('sponsors') or [{}])[0]).get('full_name') or ''})

        for act in (d.get('actions') or []):
            text = strip_html(act.get('text'))
            code = act.get('action_code') or ''
            ev = None
            m = MOVED.search(text)
            if code in ('H30300', 'S30300') or m:
                ev = {'instrument': 'floor_managed',
                      'member_surname': m.group(1) if m else None,
                      'state': m.group(2) if m else None}
            elif REPORTED.search(text):
                ev = {'instrument': 'reported_out',
                      'committee': REPORTED.search(text).group(1)}
            elif ORDERED.search(text):
                ev = {'instrument': 'ordered_reported', 'committee': None}
            if ev:
                ev.update({'key': key, 'class': cls, 'date': act.get('action_date'),
                           'action_code': code, 'text': text[:240]})
                dl_fh.write(json.dumps(ev) + '\n')
                stats['moved' if ev['instrument'] == 'floor_managed' else 'reported'] += 1

    crs_fh.close(); dl_fh.close()
    with open(os.path.join(out, 'cosponsor_role_audit.csv'), 'w', newline='',
              encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=['key', 'class', 'sponsor', 'cosponsors',
                                           'original_cosponsors', 'later_cosponsors'])
        w.writeheader(); w.writerows(cos_rows)

    report = [
        'BILLSTATUS extraction — %d jobs' % len(jobs),
        '  records read            : %d' % stats['ok'],
        '  read errors             : %d' % stats['err'],
        '  with a CRS summary      : %d   (CRS does not summarise every bill —'
        ' an empty summary is normal, not a fetch failure)' % stats['crs'],
        '  CRS text mentions CUs   : %d' % stats['cu_hits'],
        '  floor_managed events    : %d' % stats['moved'],
        '  reported/ordered events : %d' % stats['reported'],
        '',
        'NEXT STEPS',
        '  1. crs_universe.ndjson  -> re-screen every `shared` act against operative text,',
        '     not titles. Anything with cu_in_crs=true needs a human look; note that a bill',
        '     naming "banks, credit unions, and payment card networks" together is CORRECTLY',
        '     shared — the test is primacy, not mention.',
        '  2. delivery_candidates.ndjson -> feed the delivery ledger. `floor_managed` rows',
        '     name the member directly. `reported_out` rows name only the COMMITTEE, so',
        '     attributing them to a chair needs a historical chair roster keyed by congress —',
        '     McHenry chaired Financial Services in the 118th, Hill in the 119th. Do NOT',
        '     attribute a 118th-Congress report to the current chair.',
        '  3. cosponsor_role_audit.csv -> compare original_cosponsors against how many members',
        '     the bundle codes `original` on the same act. Nothing currently validates that',
        '     coding, and the whole primacy ratio is weighted by it.',
    ]
    text = '\n'.join(report)
    with open(os.path.join(out, 'extract_summary.txt'), 'w', encoding='utf-8') as fh:
        fh.write(text + '\n')
    print('\n' + text + '\n\nwrote 4 files to %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
