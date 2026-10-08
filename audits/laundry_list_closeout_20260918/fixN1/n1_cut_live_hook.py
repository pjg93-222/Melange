# -*- coding: utf-8 -*-
"""Cut the N1a live hook against the LIVE BYTES.

Bytes-safe: the live files are read and written as bytes and nothing crosses a text-mode pipe
on this cp1252 console.  LINE-WISE, not string-replace: fec/audit/dashboard_integrity.py has
MIXED line endings in the live tree (the DESK_MEDIA_CAP line ends with a bare LF inside an
otherwise CRLF file), so every anchor is matched on its line content with the terminator
stripped, and each inserted line is given the terminator its own anchor line uses.

Run with --probe to report anchor occurrences without writing anything.
"""
import difflib
import io
import os
import sys

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
WT = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\unfinished-work-handoff-a3bbad'
OUT = os.path.join(WT, 'audits', 'laundry_list_closeout_20260918', 'patches',
                   'N1a_desk_press_source_live_hook.patch')
PROBE = '--probe' in sys.argv
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DESK = r'fec\surfaces\make_member_desk.py'
INTEG = r'fec\audit\dashboard_integrity.py'
RUNNER = r'fec\tests\run_tests.py'
SPEC = r'MATHEMATICAL_SPECIFICATION.md'
SKILL = r'.claude\skills\moneyball-config-and-flags\SKILL.md'

DPS_IMPORT = ("import surfaces.desk_press_source as DPS   "
              "# DESK_PRESS_SOURCE: the desk's press stream (N1a)")
LOOP_BLOCK = [
    "    # N1a (2026-09-19, packet audits/laundry_list_closeout_20260918 FINDINGS.md A1): the rows",
    "    # walked below are the UNION of this sheet and the press stream the RANKING ENGINE reads",
    "    # (fec/press_stream.py). No script in the chain writes 'Press Release Articles' \u2014 it comes",
    "    # from the external R pipeline \u2014 so the desk showed a frozen corpus: 291 engine rows had no",
    "    # sheet row, 221 of them SCORING (receipt laneA/receipts/r9_engine_only_press.out.txt).",
    "    # The helper only SELECTS rows and hands them back in this sheet's own tuple shape, so",
    "    # every rule below \u2014 billstatus routing, the stance_src=='bill' sign branch, the",
    "    # press_stance_overrides correction, PDATE recovery, norm_cats, graded_label \u2014 runs over an",
    "    # added row exactly as over a sheet row, and the press_source_rows census that",
    "    # dashboard_integrity reconciles still counts every row walked.",
    "    # DESK_PRESS_SOURCE=sheet restores this loop's pre-2026-09-19 input byte for byte.",
    "    _press_rows, _press_source_ledger = DPS.desk_press_rows(",
    "        pw.iter_rows(min_row=2, values_only=True), ph)",
    "    for r in _press_rows:",
]
LEDGER_KEY = [
    "                   # N1a: which source each walked press row came from, plus the A5 ingest",
    "                   # ledger, so the press census chains from the tone files to this payload.",
    "                   'press_source_ledger':_press_source_ledger,",
]
DESK_INPUTS = [
    "# N1a 2026-09-19: under DESK_PRESS_SOURCE=engine the desk's press rows are the union of",
    "# 'Press Release Articles' and the tone stream fec/press_stream.py returns, so the refresh tone",
    "# file and the receipt that hash-binds it are desk INPUTS. Registering them is the same lesson",
    "# the bill-lobbying sidecar taught on 08-06: an unregistered dependency makes the first",
    "# refresh-only change look like same-input/different-bundle corruption. They are hashed under",
    "# either dial position \u2014 a declared input that is not read can only relax this check, while an",
    "# undeclared one that IS read breaks it.",
    "        'data/stance/press_refresh_tone.csv','data/stance/press_refresh_feed_receipt.json',",
    "        os.path.join('fec','press_stream.py'),",
    "        os.path.join('fec','surfaces','desk_press_source.py'),",
]
BASE_TONE_HASH = [
    "    # The HISTORICAL half of the desk's press stream lives OUTSIDE the project root (the R",
    "    # pipeline's Draft Systems tree), so it cannot be expressed as a root-relative entry like",
    "    # every other source above. Hash it by the constant press_stream itself resolves, which is",
    "    # also what MONEYBALL_DRAFT relocates. press_stream has no top-level I/O.",
    "    import press_stream as PS",
    "    source_state['press_stream:BASE_TONE_PATH']=_file_sha(PS.BASE_TONE_PATH)",
]
DIAL_INPUT = [
    "    # N1a: which press corpus the desk read is the largest single determinant of its press rows.",
    "    source_state['env:DESK_PRESS_SOURCE']=os.environ.get('DESK_PRESS_SOURCE','engine')",
]
REGISTRATION = [
    "               # N1a (Paul-approved 2026-09-19, packet",
    "               # audits/laundry_list_closeout_20260918 FINDINGS.md A1): the member desk",
    "               # now reads the same press stream as the ranking engine, unioned with the",
    "               # workbook sheet. DESK_PRESS_SOURCE=sheet must restore the pre-change",
    "               # input byte for byte, so the suite pins both dial positions, the release",
    "               # identity the union keys on (A5's), the field map, and the ledger that",
    "               # keeps the desk's press census closed. Registered beside the other dial",
    "               # suites. The producer cannot be imported -- import == execution:",
    "               # make_member_desk.py runs its whole body and overwrites the live desk --",
    "               # so the rules live in the pure fec/surfaces/desk_press_source.py and the",
    "               # wiring is pinned as text. Synthetic fixtures only: no workbook, no",
    "               # corpus, no artifact.",
    "               'test_desk_press_source',",
]

# (rel, op, anchor line WITHOUT its terminator, lines to place)
# 'after' inserts below the anchor, 'before' above it, 'replace' swaps the anchor out.
# Anchors are chosen to exist in the LIVE tree, which is BEHIND this branch: the live
# run_tests.py has no 'test_reference_admission_filters' row and the live spec has no
# REF_PRESS_OWN_DOMAIN line, so those hunks anchor one row earlier, on text both trees carry.
OPS = [
    (DESK, 'after', "from surfaces.honors_publication import compact_honor_cell", [DPS_IMPORT]),
    (DESK, 'replace', "    for r in pw.iter_rows(min_row=2, values_only=True):", LOOP_BLOCK),
    (DESK, 'after',
     "                   'press_billstatus_rows_routed_to_legislation':press_billstatus_excluded,",
     LEDGER_KEY),
    (INTEG, 'after',
     "        'data/engine/pillar_inputs_snapshot.json','data/stance/press_date_overrides.json',"
     "'data/stance/press_stance_overrides.json',", DESK_INPUTS),
    (INTEG, 'before',
     "    # the footprint display dials shape the bundle, so they are inputs to the same-input check",
     BASE_TONE_HASH),
    (INTEG, 'after',
     "    source_state['env:DESK_MEDIA_STANCE']=os.environ.get('DESK_MEDIA_STANCE','1')",
     DIAL_INPUT),
    (RUNNER, 'after', "               'test_desk_responsiveness_dial',", REGISTRATION),
]
NEW_FILES = [r'fec\surfaces\desk_press_source.py',
             r'fec\tests\surfaces\test_desk_press_source.py']
# The two catalogue files: lift this lane's own added line out of the worktree and place it at
# an anchor the live tree carries.
DOC_OPS = [(SPEC, 'before', 'MONEYBALL_ROOT / MONEYBALL_DRAFT (paths.py)'),
           (SKILL, 'before', '| `DESK_B5_FALLBACK` |')]


def read(path):
    with io.open(path, 'rb') as handle:
        return handle.read().decode('utf-8')


def split(text):
    return text.splitlines(keepends=True)


def term(line):
    if line.endswith('\r\n'):
        return '\r\n'
    if line.endswith('\n'):
        return '\n'
    return ''


def locate(lines, anchor, contains=False):
    if contains:
        return [i for i, ln in enumerate(lines) if anchor in ln]
    return [i for i, ln in enumerate(lines) if ln.rstrip('\r\n') == anchor]


edited = {}
report = []
for rel, op, anchor, block in OPS:
    lines = edited.get(rel) or split(read(os.path.join(LIVE, rel)))
    hits = locate(lines, anchor)
    report.append('%-34s %-8s hits=%d  %s' % (os.path.basename(rel), op, len(hits),
                                              anchor.strip()[:62]))
    if len(hits) != 1:
        raise SystemExit('ANCHOR NOT UNIQUE (%d) in %s: %r' % (len(hits), rel, anchor))
    at = hits[0]
    ending = term(lines[at]) or '\r\n'
    payload = [ln + ending for ln in block]
    if op == 'after':
        lines = lines[:at + 1] + payload + lines[at + 1:]
    elif op == 'before':
        lines = lines[:at] + payload + lines[at:]
    else:
        lines = lines[:at] + payload + lines[at + 1:]
    edited[rel] = lines

for rel, op, anchor in DOC_OPS:
    lines = split(read(os.path.join(LIVE, rel)))
    wt_added = [ln for ln in split(read(os.path.join(WT, rel)))
                if 'DESK_PRESS_SOURCE' in ln]
    if len(wt_added) != 1:
        raise SystemExit('expected 1 DESK_PRESS_SOURCE line in worktree %s, got %d'
                         % (rel, len(wt_added)))
    hits = locate(lines, anchor, contains=True)
    report.append('%-34s %-8s hits=%d  %s' % (os.path.basename(rel), op, len(hits), anchor[:62]))
    if len(hits) != 1:
        raise SystemExit('ANCHOR NOT UNIQUE (%d) in %s: %r' % (len(hits), rel, anchor))
    at = hits[0]
    ending = term(lines[at]) or '\r\n'
    payload = [wt_added[0].rstrip('\r\n') + ending]
    edited[rel] = lines[:at] + payload + lines[at:]

print('\n'.join(report))
if PROBE:
    raise SystemExit('\nprobe only; nothing written')


def unified(rel, before_lines, after_lines, new_file=False):
    slash = rel.replace('\\', '/')
    out = ['diff --git a/%s b/%s\n' % (slash, slash)]
    if new_file:
        out += ['new file mode 100644\n', '--- /dev/null\n', '+++ b/%s\n' % slash,
                '@@ -0,0 +1,%d @@\n' % len(after_lines)]
        for line in after_lines:
            out.append('+' + (line if line.endswith('\n') else line + '\n'))
        return out
    for line in difflib.unified_diff(before_lines, after_lines,
                                     'a/' + slash, 'b/' + slash, n=3, lineterm=''):
        out.append(line if line.endswith('\n') else line + '\n')
    return out


chunks = []
for rel in (DESK, INTEG, RUNNER, SPEC, SKILL):
    chunks += unified(rel, split(read(os.path.join(LIVE, rel))), edited[rel])
for rel in NEW_FILES:
    chunks += unified(rel, [], split(read(os.path.join(WT, rel))), new_file=True)

with io.open(OUT, 'wb') as handle:
    handle.write(''.join(chunks).encode('utf-8'))
print('\nwrote %s (%d bytes)' % (OUT, os.path.getsize(OUT)))
