# -*- coding: utf-8 -*-
"""STEP 3: fixN12v2/v2_skipset_plus7.json = the graded skipset PLUS the 7 rows the independent
grade showed would lose the member's OWN later words.

WHICH KEYS THE TOOL ACTUALLY READS.  migrate_interview_turn_bleed.Protection.load reads exactly
two: `label_rowids_interview` (-> rule (b), reason `label_or_gold_record_points_here`) and
`cu_rowids` (-> rule (c)).  Any other key is provenance only.  The 7 go into
`label_rowids_interview` because rule (b) as the tool documents it is 'a row that ANY hand label,
gold item, identity contract or REVIEWED RECORD points at' (tool docstring, rule b) -- the
independent grade IS that reviewed record, and it points at these 7 rowids:

  105315, 106055, 106388, 109799, 110715  gradeN12v2/receipts/V3_own_member_tag_after_cut.json --
      the text AFTER the cut carries the row member's OWN turn tag (SEN. SUSAN COLLINS,
      SEN. AMY KLOBUCHAR x2, REP. ADAM SCHIFF, SEN. JOHN BARRASSO), so truncating removes
      3 / 6 / 13 / 623 / 113 words the member themself spoke.
  83061                                   gradeN12v2/receipts/V5_member_word_loss.txt + the v1
      grade's untagged-member-return finding: the member resumes after the foreign tag with no
      tag of their own, so the cut cannot see them.
  83158                                   gradeN12v2/receipts/V3_untagged_return_sweep.txt -- the
      same untagged-return shape behind a 'PROKUPECZ (voice-over)' segment.

This script only ADDS.  It never drops a rowid the graded skipset already protected, and it
recomputes the derived counts/unions so the file cannot describe itself wrongly.
"""
import hashlib
import io
import json
import os
import sys

WT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
FIX = os.path.join(WT, 'audits', 'laundry_list_closeout_20260918', 'fixN12v2')
BASE = os.path.join(FIX, 'v2_skipset.json')
DEST = os.path.join(FIX, 'v2_skipset_plus7.json')

PLUS7 = {
    105315: 'own tag SEN. SUSAN COLLINS after the cut (3 w) [V3_own_member_tag_after_cut.json]',
    106055: 'own tag SEN. AMY KLOBUCHAR after the cut (6 w) [V3_own_member_tag_after_cut.json]',
    106388: 'own tag SEN. AMY KLOBUCHAR after the cut (13 w) [V3_own_member_tag_after_cut.json]',
    109799: 'own tag REP. ADAM SCHIFF after the cut (623 w) [V3_own_member_tag_after_cut.json]',
    110715: 'own tag SEN. JOHN BARRASSO after the cut (113 w) [V3_own_member_tag_after_cut.json]',
    83061: 'untagged member return after the cut [V5_member_word_loss.txt, v1 grade]',
    83158: 'untagged member return behind PROKUPECZ (voice-over) [V3_untagged_return_sweep.txt]',
}


def sha256_file(path):
    with open(path, 'rb') as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    base_sha = sha256_file(BASE)
    with io.open(BASE, encoding='utf-8') as fh:
        d = json.load(fh)
    print('base   %s' % BASE)
    print('       sha256=%s bytes=%d' % (base_sha, os.path.getsize(BASE)))

    lab_before = list(d['label_rowids_interview'])
    cu_before = list(d['cu_rowids'])
    print('       label_rowids_interview=%d  cu_rowids=%d' % (len(lab_before), len(cu_before)))

    already = sorted(r for r in PLUS7 if r in set(lab_before) | set(cu_before))
    print('of the 7, already protected by the graded skipset: %s' % (already or 'NONE'))

    lab_after = sorted(set(lab_before) | set(PLUS7))
    assert set(lab_before) <= set(lab_after), 'the plus7 file must never drop a protected rowid'
    assert set(cu_before) == set(cu_before)
    d['label_rowids_interview'] = lab_after
    d['cu_rowids'] = sorted(set(cu_before))
    d['n_label_rowids_interview'] = len(lab_after)
    d['n_cu_rowids'] = len(d['cu_rowids'])

    union = sorted(set(lab_after) | set(d['cu_rowids']))
    d['protected_union_interview'] = union
    d['n_protected_union_interview'] = len(union)
    if 'wide_rowids_interview' in d:
        wide = sorted(set(d['wide_rowids_interview']) | set(union))
        d['protected_union_wide_interview'] = wide
        d['n_protected_union_wide_interview'] = len(wide)

    d['plus7_rowids'] = sorted(PLUS7)
    d['plus7_reasons'] = {str(k): v for k, v in sorted(PLUS7.items())}
    d['plus7_bucket'] = ('label_rowids_interview -- rule (b), the reviewed-record clause; the '
                         'residue will therefore read label_or_gold_record_points_here')
    d['plus7_added_by'] = 'audits/laundry_list_closeout_20260918/applyN12v2/a02_build_plus7_skipset.py'
    d['plus7_grade'] = 'audits/laundry_list_closeout_20260918/gradeN12v2/receipts'
    d['base_skipset_path'] = BASE
    d['base_skipset_sha256'] = base_sha

    with io.open(DEST, 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(d, fh, ensure_ascii=False, indent=1, sort_keys=True)

    print('\nwrote  %s' % DEST)
    print('       sha256=%s bytes=%d' % (sha256_file(DEST), os.path.getsize(DEST)))
    print('       label_rowids_interview %d -> %d   (+%d)'
          % (len(lab_before), len(lab_after), len(lab_after) - len(lab_before)))
    print('       cu_rowids %d -> %d' % (len(cu_before), len(d['cu_rowids'])))
    print('       protected union (interview) -> %d' % len(union))

    # read it back exactly the way the tool does, and prove the reason each of the 7 will get
    sys.path.insert(0, os.path.join(WT, 'fec'))
    from members.migrate_interview_turn_bleed import Protection
    prot = Protection.load(DEST)
    print('\nProtection.load(plus7): len=%d' % len(prot))
    for r in sorted(PLUS7):
        print('  rowid %-7d reason=%s' % (r, prot.reason(r)))
    missing = [r for r in PLUS7 if prot.reason(r) is None]
    print('rowids the loaded Protection does NOT protect: %s' % (missing or 'NONE'))
    base_prot = Protection.load(BASE)
    print('every rowid the graded skipset protected is still protected: %s'
          % all(prot.reason(r) is not None
                for r in (base_prot.label_bound | base_prot.cu_extract)))
    return 0 if not missing else 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
