# -*- coding: utf-8 -*-
"""Build the LIVE-patched producer in SCRATCH and cut a byte-exact unified patch.

Read-only against LIVE. Everything is done in BYTES so the file's CRLF line endings and
cp1252-hostile characters survive: no text-mode pipe, no newline translation.
"""
import difflib
import os
import py_compile
import sys

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
WORKTREE = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
            r'\unfinished-work-handoff-a3bbad')
HERE = os.path.dirname(os.path.abspath(__file__))
REL = 'fec/legislation/build_archive_legislative.py'
WIRING_REL = 'fec/tests/legislation/test_sponsor_column_producer_wiring.py'
OUT = os.path.join(WORKTREE, 'audits', 'laundry_list_closeout_20260918', 'patches',
                   'N4_sponsor_column_live_hook.patch')

EOL = b'\r\n'


def edit(blob, anchor, addition, where='after'):
    """Insert `addition` immediately after (or before) the single line `anchor`."""
    assert blob.count(anchor + EOL) == 1, (anchor[:60], blob.count(anchor + EOL))
    if where == 'after':
        return blob.replace(anchor + EOL, anchor + EOL + addition + EOL, 1)
    return blob.replace(anchor + EOL, addition + EOL + anchor + EOL, 1)


original = open(os.path.join(LIVE, REL.replace('/', os.sep)), 'rb').read()
assert original.count(b'\r\n') == original.count(b'\n'), 'mixed line endings in LIVE'
patched = original

# 1. the import, among the other `from legislation import ...` lines
patched = edit(
    patched,
    b'from legislation.congress_bill_repository import parse_bill_identity',
    b'from legislation import sponsor_column as SC')

# 2. remember how much of the frame carries the bill-level Sponsor column
patched = edit(
    patched,
    b"A=pd.read_excel(sorted(glob.glob(MB_ROOT+r'\\congress_bills_archive_*.xlsx'))[-1],sheet_name='All Bills')",
    b'_archive_rows=len(A)   # only the archive rows carry the bill-level Sponsor column;'
    + EOL +
    b'                       # sentinel and manual evidence arrive with that cell blank.')

# 3. the hook: synthesise the missing sponsor rows into the frame BEFORE the row loop, so
#    every gate below adjudicates them unchanged.
HOOK = EOL.join((
    b"# 2026-09-19 (Paul-approved): the archive names a bill-level Sponsor on EVERY row and this",
    b"# producer never read it, so a named sponsor who holds no member row in a scoring cell",
    b"# reached the stance matrix nowhere -- Tim Scott x Member Business Lending was published at",
    b"# 10.76 with +6.24 missing, 58% of the cell (F1 receipt",
    b"# audits/laundry_list_closeout_20260918/F1/receipts/s3_s4_missing_weight.txt). The rows are",
    b"# injected HERE, before the loop, so official-membership eligibility, category routing,",
    b"# sign, decay and strongest-role-wins all judge them unchanged: a sponsor the sentinel",
    b"# already supplies dedups away instead of double-counting. LEG_SPONSOR_FROM_COLUMN=0",
    b"# restores the pre-fix behaviour exactly (nothing synthesised, nothing appended).",
    b"_sponsor_column_rows=SC.sponsor_rows_from_column(",
    b"    A.iloc[:_archive_rows].to_dict('records'),matchmember,seccat,BR._congress)",
    b"if _sponsor_column_rows:",
    b"    A=pd.concat([A,pd.DataFrame(_sponsor_column_rows)],ignore_index=True)",
    b"print('archive Sponsor-column sponsor rows synthesised: %d (LEG_SPONSOR_FROM_COLUMN)'"
    b"%len(_sponsor_column_rows))",
))
patched = edit(patched, b'for _idx,r in A.iterrows():', HOOK, where='before')

# 4. the routing audit carries the provenance, and ONLY on the synthesised rows, so an audit
#    written with the dial off stays byte-identical to the pre-fix one.
patched = edit(
    patched,
    b"           'source_role':_clean(r.get('Role')),'tracker_status':_clean(r.get('LastAction'))}",
    b"    _evidence_source=_clean(r.get(SC.SOURCE_COLUMN))   # set only on synthesised rows"
    + EOL +
    b"    if _evidence_source: audit['evidence_source']=_evidence_source")

assert patched != original
scratch_copy = os.path.join(HERE, 'build_archive_legislative.PATCHED.py')
with open(scratch_copy, 'wb') as handle:
    handle.write(patched)
with open(os.path.join(HERE, 'build_archive_legislative.LIVE.py'), 'wb') as handle:
    handle.write(original)

# The patched producer must at least compile; compiling never executes it.
py_compile.compile(scratch_copy, cfile=os.path.join(HERE, 'patched.pyc'), doraise=True)
print('patched copy compiles:', scratch_copy)

# The pinned source strings other suites assert on must survive.
text = patched.decode('utf-8')
for pinned in ("A=pd.concat([A,_verified[A.columns]],ignore_index=True)",
               "sheet_name='Sentinel Bill Ledger'", "'Scoring Eligible'",
               "sentinel_scoring_mask(_sentinel)",
               "text_column('Review Status').eq('verified')",
               "text_column('Record Type').eq('membership')", "_sentinel[_eligible]",
               "_LTR_MIN_ROWS, _LTR_MIN_IDS, _LTR_MIN_MEMBERS = 296, 7, 251"):
    assert pinned in text, pinned
print('pinned source strings survive: 8/8')

wiring = open(os.path.join(HERE, 'wiring_test.py'), 'rb').read()
assert wiring.count(b'\r\n') == wiring.count(b'\n'), 'wiring test must be CRLF'


def unified(rel, before, after, new_file=False):
    left = before.decode('utf-8').splitlines(keepends=True)
    right = after.decode('utf-8').splitlines(keepends=True)
    fromfile = '/dev/null' if new_file else 'a/' + rel
    diff = list(difflib.unified_diff(left, right, fromfile=fromfile, tofile='b/' + rel,
                                     lineterm='\n'))
    head = ['diff --git a/%s b/%s\n' % (rel, rel)]
    if new_file:
        head.append('new file mode 100644\n')
    return head + diff


pieces = unified(REL, original, patched) + unified(WIRING_REL, b'', wiring, new_file=True)
body = ''.join(pieces)
# difflib emits '\n' for its own control lines; the payload lines keep whatever the files
# had. Write with newline='' so nothing is translated on the way out.
with open(OUT, 'w', encoding='utf-8', newline='') as handle:
    handle.write(body)
raw = open(OUT, 'rb').read()
print('patch bytes:', len(raw), 'lines:', body.count('\n'))
print('patch written:', OUT)
sys.stdout.flush()
