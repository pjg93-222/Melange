# -*- coding: utf-8 -*-
"""Read-only coverage / orphan audit for the legislative plane (2026-07-19).

Answers: is every bill sorted into a slot, and is any bill missing or orphaned?

Nothing here mutates state. The script reads the routing ledger, the archive
workbook, and the config CSVs, then prints an ASCII report. It writes a file
only when --json <path> is passed explicitly.

Import-safe (unlike most of fec/) -- the body is under a __main__ guard.
Only bill_rules and paths are imported; both are pure. moneyball_core is
parsed with ast rather than imported, because importing it executes it.

Run against live data from a worktree:
    set MONEYBALL_ROOT=C:\\Users\\pgoff\\OneDrive\\Desktop\\Melange Systems
    python fec/bill_coverage_audit.py
"""
import argparse
import ast
import collections
import csv
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bill_rules as BR  # noqa: E402  (pure module: constants + defs only)
import paths as P        # noqa: E402

PASS, FAIL, WARN = [], [], []
ROLE_RANK = {'other': 0, 'cosponsor': 1, 'original-cosponsor': 2, 'sponsor': 3}


def emit(status, name, detail=''):
    (PASS if status == 'PASS' else FAIL if status == 'FAIL' else WARN).append(name)
    print('  [%s] %s%s' % (status, name, (' -- ' + detail) if detail else ''))


def head(title):
    print('')
    print(title)
    print('-' * len(title))


def clip(text, n=120):
    text = re.sub(r'\s+', ' ', str(text or '')).strip()
    return text if len(text) <= n else text[:n - 3] + '...'


def ascii_only(text):
    return str(text).encode('ascii', 'replace').decode('ascii')


def load_archive(root):
    """Return {source_row: {col: value}} for the newest bills archive."""
    import openpyxl
    hits = sorted(glob.glob(os.path.join(root, 'congress_bills_archive_*.xlsx')))
    if not hits:
        return None, {}
    path = hits[-1]
    book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = book['All Bills']
    rows, header = {}, None
    for idx, raw in enumerate(sheet.iter_rows(values_only=True), start=1):
        if idx == 1:
            header = [str(c or '').strip() for c in raw]
            continue
        rows[idx] = dict(zip(header, raw))
    book.close()
    return os.path.basename(path), rows


def parse_block_table(fec_dir):
    """Extract `blocks` and `BLOCKCAT` from moneyball_core.py WITHOUT importing it."""
    with open(os.path.join(fec_dir, 'moneyball_core.py'), encoding='utf-8') as handle:
        tree = ast.parse(handle.read())
    blocks, blockcat = None, None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            name = getattr(target, 'id', None)
            if name == 'blocks' and blocks is None:
                try:
                    blocks = ast.literal_eval(node.value)
                except Exception:
                    pass
            elif name == 'BLOCKCAT' and blockcat is None:
                try:
                    blockcat = ast.literal_eval(node.value)
                except Exception:
                    pass
    return blocks, blockcat


def read_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', dest='json_out', default=None,
                    help='optional explicit path for a machine-readable report')
    args = ap.parse_args()

    root = P.ROOT
    print('BILL COVERAGE / ORPHAN AUDIT')
    print('resolved ROOT: %s' % root)

    ledger_path = os.path.join(root, 'legislation_routing_audit.json')
    required = [ledger_path, os.path.join(root, 'archive_leg.json'),
                os.path.join(root, 'congestion.json')]
    # the archive workbook is required too: without it C6 flags every config row dead and C8
    # degrades into a vacuous PASS derived from zero rows
    if not glob.glob(os.path.join(root, 'congress_bills_archive_*.xlsx')):
        required.append(os.path.join(root, 'congress_bills_archive_*.xlsx'))
    missing = [p for p in required if not os.path.exists(p)]
    if missing:
        print('')
        print('ABORT: inputs not found under the resolved ROOT:')
        for p in missing:
            print('  missing: %s' % p)
        print('Set MONEYBALL_ROOT to the live tree -- worktrees do not carry data.')
        return 2

    ledger = json.load(open(ledger_path, encoding='utf-8'))
    rows = ledger['rows']
    summary = ledger['summary']
    dispositions = summary['dispositions']
    print('ledger source: %s   schema: %s' % (ledger.get('source'), ledger.get('schema')))

    archive_name, archive = load_archive(root)
    print('archive read : %s (%d data rows)' % (archive_name, len(archive)))

    report = {'root': root, 'source': ledger.get('source')}

    # ---------------------------------------------------------------- C1
    head('C1  Row conservation')
    n_src, n_rows = ledger['source_rows'], len(rows)
    disp_sum = sum(dispositions.values())
    if n_src == n_rows == disp_sum:
        emit('PASS', 'every source row appears exactly once in the ledger',
             '%d rows, dispositions sum %d' % (n_rows, disp_sum))
    else:
        emit('FAIL', 'row conservation broken',
             'source_rows=%d len(rows)=%d disposition_sum=%d' % (n_src, n_rows, disp_sum))
    for key in sorted(dispositions, key=lambda k: -dispositions[k]):
        print('        %-24s %6d' % (key, dispositions[key]))
    report['dispositions'] = dispositions

    # ---------------------------------------------------------------- C2
    head('C2  Orphaned bills (routed to no slot)')
    orphans = [r for r in rows if r['disposition'] == 'unknown-section']
    if not orphans:
        emit('PASS', 'no bill failed to resolve a category', 'unknown-section = 0')
    else:
        emit('FAIL', 'bills with no canonical slot', '%d rows' % len(orphans))
        seen = {}
        for r in orphans:
            seen.setdefault((r['bill'], r['congress'], r.get('source_section')), r)
        for (bill, cong, sec), r in sorted(seen.items()):
            print('        %-12s %-4s section=%-40s %s' %
                  (bill, cong, ascii_only(clip(sec, 38)), ascii_only(clip(r.get('title'), 50))))
    report['orphan_rows'] = len(orphans)

    # ---------------------------------------------------------------- C3
    head('C3  All 18 slots occupied')
    eff = summary.get('effective_categories', {})
    canon = set(BR.CATEGORIES)
    absent = sorted(canon - set(eff))
    stray = sorted(set(eff) - canon)
    if not absent and not stray:
        emit('PASS', 'all 18 canonical categories present, none stray',
             '%d categories' % len(eff))
    else:
        emit('FAIL', 'category set mismatch',
             'absent=%s stray=%s' % (absent or 'none', stray or 'none'))
    sel_by_cat = collections.Counter(
        r['effective_category'] for r in rows if r['disposition'] == 'selected')
    print('        %-28s %8s %8s' % ('slot', 'rows', 'scored'))
    for cat in sorted(eff, key=lambda c: -eff[c]):
        # NOTE: summary.effective_categories counts every row that RESOLVED to the
        # slot, including deduped duplicates -- it is not the scored-event count.
        print('        %-28s %8d %8d' % (cat, eff[cat], sel_by_cat[cat]))
    report['effective_categories'] = eff
    report['selected_by_category'] = dict(sel_by_cat)

    # ---------------------------------------------------------------- C4
    head('C4  Unmatched members (evidence dropped on the floor)')
    unmatched = summary.get('unmatched_members', {})
    known = {'Stacey Plaskett', 'James Moylan'}
    lost = collections.defaultdict(set)
    for r in rows:
        if r['disposition'] == 'unmatched-member':
            lost[r['member_source']].add('%s (%s)' % (r['bill'], r['congress']))
    total_lost = sum(unmatched.values())
    unexpected = sorted(set(unmatched) - known)
    if unexpected:
        emit('FAIL', 'member outside the known non-voting-delegate set',
             ', '.join(unexpected))
    elif total_lost > 10:
        emit('FAIL', 'unmatched row count grew past the known baseline',
             '%d rows > 10' % total_lost)
    else:
        emit('WARN', 'known non-voting delegates only', '%d rows dropped' % total_lost)
    for name in sorted(unmatched):
        print('        %-22s %2d rows   %s' %
              (name, unmatched[name], ascii_only(clip(', '.join(sorted(lost[name])), 70))))
    report['unmatched_members'] = unmatched

    # ---------------------------------------------------------------- C5
    head('C5  Members with zero bill evidence')
    arch_leg = json.load(open(os.path.join(root, 'archive_leg.json'), encoding='utf-8'))
    roster = [m['member'] for m in json.load(open(os.path.join(root, 'congestion.json'),
                                                 encoding='utf-8'))]
    zero = sorted(set(roster) - set(arch_leg))
    emit('WARN' if zero else 'PASS', 'roster coverage',
         '%d of %d members carry >=1 bill; %d carry none' %
         (len(set(roster) & set(arch_leg)), len(roster), len(zero)))
    for i in range(0, len(zero), 3):
        print('        ' + '  '.join('%-24s' % ascii_only(n) for n in zero[i:i + 3]))
    report['members_zero_evidence'] = zero

    # ---------------------------------------------------------------- C6
    head('C6  Dead config rows (match no archive bill)')
    archive_keys = set()
    for r in archive.values():
        key = BR.bill_key(r.get('Name'))
        if key:
            archive_keys.add(key)
    dead = []
    for fname, billcol in (('bill_overrides.csv', 'Bill'),
                           ('bill_directions.csv', 'Bill'),
                           ('manual_bill_evidence.csv', 'Bill')):
        for row in read_csv(os.path.join(root, fname)):
            bill = row.get(billcol)
            if BR.is_letter_evidence(bill):
                continue
            key = BR.bill_key(bill)
            if key is None or key not in archive_keys:
                dead.append((fname, bill, row.get('Category', ''), clip(row.get('Note', ''), 44)))
    if not dead:
        emit('PASS', 'every config row matches a live archive bill')
    else:
        emit('WARN', 'config rows matching no archive bill', '%d rows' % len(dead))
        for fname, bill, cat, note in dead:
            print('        %-26s %-12s %-24s %s' %
                  (fname, ascii_only(str(bill)), ascii_only(cat), ascii_only(note)))
    report['dead_config_rows'] = [list(d) for d in dead]

    # ---------------------------------------------------------------- C7
    head('C7  Exclusion forensics -- title match vs summary-only match')
    print('  Exclusions are deliberate and user-directed (bill_rules.py:59-60).')
    print('  This REPORTS them for adjudication; nothing is changed.')
    excluded = [r for r in rows if r['disposition'] == 'excluded-title']
    per_bill, summary_only = {}, []
    for r in excluded:
        src = archive.get(r['source_row'], {})
        title = str(src.get('Title') or r.get('title') or '')
        blurb = str(src.get('bill_summary') or '')
        phrase = r.get('reason', '')
        in_title = phrase and phrase.lower() in title.lower()
        in_blurb = phrase and phrase.lower() in blurb.lower()
        key = (r['bill'], r['congress'])
        if key in per_bill:
            continue
        would_be = BR.canonical_category(r.get('source_section'))
        per_bill[key] = {'phrase': phrase, 'title': title, 'in_title': bool(in_title),
                         'in_summary_only': bool(in_blurb and not in_title),
                         'would_be_slot': would_be, 'section': r.get('source_section'),
                         'summary': blurb}
        if in_blurb and not in_title:
            summary_only.append((key, per_bill[key]))

    by_phrase = collections.Counter(v['phrase'] for v in per_bill.values())
    print('')
    print('  distinct bills excluded, by phrase:')
    for phrase, n in by_phrase.most_common():
        print('        %-38s %3d bills' % (ascii_only(phrase), n))

    by_slot = collections.Counter(v['would_be_slot'] or '(no slot)' for v in per_bill.values())
    print('')
    print('  slot those excluded bills WOULD have occupied:')
    for slot, n in by_slot.most_common():
        print('        %-28s %3d bills' % (slot, n))

    if not summary_only:
        emit('PASS', 'no exclusion fired on summary text alone',
             '%d distinct bills excluded, all matched on title' % len(per_bill))
    else:
        emit('WARN', 'exclusions fired on SUMMARY text only (over-exclusion risk)',
             '%d bills' % len(summary_only))
        for (bill, cong), v in summary_only:
            print('')
            print('        %s (%s) -> would be %s' % (bill, cong, v['would_be_slot']))
            print('          title  : %s' % ascii_only(clip(v['title'], 90)))
            print('          phrase : "%s" (summary only)' % ascii_only(v['phrase']))
            low = v['summary'].lower()
            at = low.find(v['phrase'].lower())
            ctx = v['summary'][max(0, at - 60):at + len(v['phrase']) + 60]
            print('          context: ...%s...' % ascii_only(clip(ctx, 130)))

    privacy = [(k, v) for k, v in per_bill.items() if v['would_be_slot'] == 'Data Privacy & Cyber']
    print('')
    if privacy:
        emit('WARN', 'excluded bills whose slot would be Data Privacy & Cyber',
             '%d bills' % len(privacy))
        for (bill, cong), v in sorted(privacy):
            print('        %-12s %-4s %-34s %s' %
                  (bill, cong, ascii_only(clip(v['phrase'], 32)),
                   ascii_only(clip(v['title'], 46))))
    else:
        emit('PASS', 'no excluded bill would have landed in Data Privacy & Cyber')
    report['excluded_by_phrase'] = dict(by_phrase)
    report['excluded_by_would_be_slot'] = dict(by_slot)
    report['summary_only_exclusions'] = [
        {'bill': k[0], 'congress': k[1], 'phrase': v['phrase'],
         'title': v['title'], 'would_be_slot': v['would_be_slot']}
        for k, v in summary_only]

    # ---------------------------------------------------------------- C8
    head('C8  bill_key collisions (H.R.N vs H.Res.N vs H.J.Res.N)')
    print('  bill_key() keeps only (chamber, number) and discards the R/J/Res segment')
    print('  (bill_rules.py:129-132), so distinct bill types can collapse to one key.')
    groups = collections.defaultdict(set)
    for r in archive.values():
        name = str(r.get('Name') or '').strip()
        key = BR.bill_key(name)
        if key:
            groups[(key, str(r.get('Congress') or '').strip())].add(name)
    collisions = {k: v for k, v in groups.items() if len(v) > 1}
    selected_names = set()
    for r in rows:
        if r['disposition'] == 'selected':
            selected_names.add((BR.bill_key(r['bill']), str(r['congress']), r['bill']))
    hot = []
    for (key, cong), names in collisions.items():
        involved = {n for n in names if (key, cong, n) in selected_names}
        if len(involved) > 1:
            hot.append(((key, cong), names))
    if not collisions:
        emit('PASS', 'no two distinct bill ids share a key within a Congress')
    elif hot:
        emit('FAIL', 'colliding ids BOTH reached the selected set (evidence merged)',
             '%d keys' % len(hot))
        for (key, cong), names in hot:
            print('        %s/%s  <-  %s' % (key, cong, ', '.join(sorted(names))))
    else:
        emit('WARN', 'collisions exist but not among selected rows',
             '%d keys' % len(collisions))
        for (key, cong), names in sorted(collisions.items())[:20]:
            print('        %s/%s  <-  %s' % (key, cong, ', '.join(sorted(names))))
    report['bill_key_collisions'] = {'total': len(collisions), 'in_selected': len(hot)}

    # ---------------------------------------------------------------- C9
    head('C9  Slot -> workbook block integrity')
    blocks, blockcat = parse_block_table(os.path.join(root, 'fec'))
    if not blocks or not blockcat:
        emit('FAIL', 'could not parse blocks/BLOCKCAT from moneyball_core.py')
    else:
        blockcat = {int(k): v for k, v in blockcat.items()}
        no_entry = [b for b in blocks if b not in blockcat]
        bad_cat = sorted({v for v in blockcat.values()} - canon)
        covered = {v for v in blockcat.values()}
        uncovered = sorted(canon - covered)
        if no_entry or bad_cat or uncovered:
            emit('FAIL', 'block table does not cleanly cover the 18 slots',
                 'no_entry=%s not_a_category=%s uncovered=%s' % (no_entry, bad_cat, uncovered))
        else:
            emit('PASS', 'every block maps to a canonical slot; all 18 slots covered',
                 '%d blocks -> %d categories' % (len(blocks), len(covered)))
        folded = collections.defaultdict(list)
        for b in blocks:
            folded[blockcat[b]].append(b)
        for cat in sorted(folded):
            cols = folded[cat]
            print('        %-28s cols %s%s' % (cat, cols, '   <- folded' if len(cols) > 1 else ''))
    report['blocks'] = blocks

    # --------------------------------------------------------------- C10
    head('C10 Dedup kept the strongest role')
    best_selected = {}
    for r in rows:
        if r['disposition'] == 'selected':
            key = (r['member'], r['bill'], r['congress'], r['effective_category'])
            best_selected[key] = ROLE_RANK.get(BR.canonical_role(r['effective_role']), 0)
    violations = []
    for r in rows:
        if not r['disposition'].startswith('duplicate'):
            continue
        key = (r.get('member') or r.get('member_source'), r['bill'], r['congress'],
               r.get('effective_category'))
        dropped = ROLE_RANK.get(BR.canonical_role(r['source_role']), 0)
        kept = best_selected.get(key)
        if kept is not None and dropped > kept:
            violations.append((key, r['source_role'], kept))
    if not violations:
        emit('PASS', 'no duplicate group kept a weaker role than one it dropped',
             '%d duplicate rows checked' %
             sum(1 for r in rows if r['disposition'].startswith('duplicate')))
    else:
        emit('FAIL', 'weaker role survived dedup', '%d groups' % len(violations))
        for key, role, kept in violations[:20]:
            print('        %s  dropped=%s kept_rank=%s' % (key, role, kept))

    # --------------------------------------------------------------- C11
    head('C11 Slot-vs-title signal mismatch (soft heuristic, for adjudication)')
    print('  Flags SELECTED bills whose title carries another slot\'s keyword.')
    print('  The Section comes from the upstream archive export, so a hit here is')
    print('  an upstream filing question, not a routing bug. Reported, not changed.')
    kw = {cat: k for cat, k in BR.SECTION_KEYWORDS}
    privacy_kw = ('privacy', 'cyber', 'data security', 'data breach', 'surveillance')
    mismatch = collections.defaultdict(list)
    seen_bill = set()
    for r in rows:
        if r['disposition'] != 'selected':
            continue
        key = (r['bill'], r['congress'])
        if key in seen_bill:
            continue
        seen_bill.add(key)
        title = str(r.get('title') or '').lower()
        slot = r['effective_category']
        if slot != 'Data Privacy & Cyber' and any(p in title for p in privacy_kw):
            mismatch[slot].append((r['bill'], r['congress'], r.get('title')))
    total_mm = sum(len(v) for v in mismatch.values())
    if not total_mm:
        emit('PASS', 'no privacy-titled bill sits outside Data Privacy & Cyber')
    else:
        emit('WARN', 'privacy/cyber-titled bills filed under another slot',
             '%d bills' % total_mm)
        for slot in sorted(mismatch, key=lambda s: -len(mismatch[s])):
            print('')
            print('        %s  (%d)' % (slot, len(mismatch[slot])))
            for bill, cong, title in sorted(mismatch[slot])[:12]:
                print('          %-12s %-4s %s' % (bill, cong, ascii_only(clip(title, 66))))
            if len(mismatch[slot]) > 12:
                print('          ... and %d more' % (len(mismatch[slot]) - 12))
    report['slot_title_mismatch'] = {k: len(v) for k, v in mismatch.items()}

    # ------------------------------------------------------------ proposals
    head('PROPOSED AUDIT CHECKS (NOT APPLIED)')
    print('  audit_full.py currently asserts only row conservation and the 5 pinned')
    print('  bills. These would close real gaps -- a human decides whether to add them:')
    print('    C2  assert dispositions.get("unknown-section", 0) == 0')
    print('    C3  assert set(effective_categories) == set(bill_rules.CATEGORIES)')
    print('    C4  assert set(unmatched_members) <= {"Stacey Plaskett","James Moylan"}')
    print('    C5  assert len(archive_leg) >= 516   (floor, so silent coverage loss trips)')
    print('    C8  assert no bill_key collision among selected rows')

    # ---------------------------------------------------------------- tail
    print('')
    print('=' * 66)
    print('COVERAGE AUDIT - %d passed, %d FAILED, %d WARN' % (len(PASS), len(FAIL), len(WARN)))
    if FAIL:
        print('  FAILURES: %s' % FAIL)
    else:
        print('  NO STRUCTURAL FAILURES. Warnings above are for adjudication.')

    if args.json_out:
        with open(args.json_out, 'w', encoding='utf-8') as handle:
            json.dump(report, handle, indent=1)
        print('  report written: %s' % args.json_out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
