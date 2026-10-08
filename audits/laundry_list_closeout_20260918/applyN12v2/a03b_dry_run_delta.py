# -*- coding: utf-8 -*-
"""STEP 3, the row-level proof: the ONLY difference between the graded dry run and the plus7 dry
run is that the 7 rows moved from truncated to skipped.  Read-only, compares the two residue
files the tool itself wrote.  Also states where rowid 245771 (the AFTER-check probe) stands.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.abspath(os.path.join(HERE, '..', 'fixN12v2'))
BASE_RES = os.path.join(FIX, 'v2_residue.jsonl')                    # graded skipset
PLUS_RES = os.path.join(HERE, 'dry_plus7', 'v2_residue.jsonl')      # plus7 skipset
BASE_SUM = os.path.join(FIX, 'v2_dry_run_summary.json')
PLUS_SUM = os.path.join(HERE, 'dry_plus7', 'v2_dry_run_summary.json')
SEVEN = [83061, 83158, 105315, 106055, 106388, 109799, 110715]
PROBE = 245771


def load(path):
    out = {}
    with io.open(path, encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                out[r['rowid']] = r
    return out


def main():
    base, plus = load(BASE_RES), load(PLUS_RES)
    b = json.load(io.open(BASE_SUM, encoding='utf-8'))
    p = json.load(io.open(PLUS_SUM, encoding='utf-8'))
    print('graded dry run  flagged=%d truncate=%d skip=%d insert=%d protection_rows=%d'
          % (b['rows_flagged'], b['rows_would_truncate'], b['rows_would_skip'],
             b['rows_would_insert'], b['protection_rows']))
    print('plus7  dry run  flagged=%d truncate=%d skip=%d insert=%d protection_rows=%d'
          % (p['rows_flagged'], p['rows_would_truncate'], p['rows_would_skip'],
             p['rows_would_insert'], p['protection_rows']))
    print('delta           flagged=%+d truncate=%+d skip=%+d protection_rows=%+d'
          % (p['rows_flagged'] - b['rows_flagged'],
             p['rows_would_truncate'] - b['rows_would_truncate'],
             p['rows_would_skip'] - b['rows_would_skip'],
             p['protection_rows'] - b['protection_rows']))
    print('both dry runs report every_row_reconstructs=%s / %s   rows_would_insert=%d / %d'
          % (b['every_row_reconstructs'], p['every_row_reconstructs'],
             b['rows_would_insert'], p['rows_would_insert']))

    added = sorted(set(plus) - set(base))
    dropped = sorted(set(base) - set(plus))
    print('\nrowids in the plus7 residue and NOT in the graded residue (%d): %s'
          % (len(added), added))
    print('rowids in the graded residue and NOT in the plus7 residue (%d): %s'
          % (len(dropped), dropped))
    print('added set == the 7: %s' % (added == sorted(SEVEN)))
    changed = sorted(r for r in set(base) & set(plus)
                     if base[r]['reason'] != plus[r]['reason']
                     or base[r]['reasons'] != plus[r]['reasons'])
    print('rows present in both whose skip reason changed (%d): %s' % (len(changed), changed))

    print('\nper-row, the 7:')
    for r in sorted(SEVEN):
        was = 'skipped(%s)' % base[r]['reason'] if r in base else 'TRUNCATED'
        now = plus.get(r)
        print('  rowid %-7d graded=%-10s plus7=%-34s member=%-22s cut_tag=%r removed=%dw'
              % (r, was, 'skipped(%s)' % now['reason'], (now['member'] or '')[:22],
                 now['cut_tag'], now['removed_nwords']))

    print('\nprobe rowid %d:' % PROBE)
    for name, res in (('graded', base), ('plus7', plus)):
        r = res.get(PROBE)
        print('  %-7s %s' % (name, ('skipped(%s) reasons=%s cut_tag=%r'
                                    % (r['reason'], r['reasons'], r['cut_tag'])) if r
                            else 'NOT in the residue'))
    ok = (added == sorted(SEVEN) and not dropped and not changed
          and p['rows_would_truncate'] == b['rows_would_truncate'] - 7
          and p['rows_would_skip'] == b['rows_would_skip'] + 7
          and p['rows_flagged'] == b['rows_flagged'] and p['rows_would_insert'] == 0)
    print('\nDELTA IS EXACTLY THE 7 AND NOTHING ELSE: %s' % ok)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
