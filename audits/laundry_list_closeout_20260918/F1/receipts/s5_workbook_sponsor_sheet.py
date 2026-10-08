# -*- coding: utf-8 -*-
"""Lane F1 / S5 : how the workbook sheet 'Sponsor Interactions' is populated, and therefore why it
can name a sponsor the archive has no row for.

Part 1  TEXT SEARCH (no imports, no execution) of every source file under LIVE\\fec and
        WORKTREE\\fec for the sheet name, for writers of the blended workbook, and for the
        openpyxl/artifact-tool write verbs that could produce it.
Part 2  CONTENT COMPARISON of the sheet against the selected archive, the older archive, the
        Sentinel ledger and manual_bill_evidence.csv -- which source, if any, it agrees with.
Part 3  the three Tim Scott MBL bills traced through every local sponsor-bearing source, plus
        whether the Sentinel collector ever saw them (including non-verified / pending rows).

Writes s5_workbook_sponsor_sheet.txt.
"""
import collections, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f1_lib as L

P = print
LIVE_FEC = os.path.join(L.ROOT, 'fec')
WT_FEC = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\unfinished-work-handoff-a3bbad\fec"
EXT = {'.py', '.cjs', '.js', '.mjs', '.json', '.R', '.r', '.md', '.ps1', '.bat', '.sh', '.txt'}


def bar(t):
    P('\n' + '=' * 100)
    P(t)
    P('=' * 100)


def walk(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in {'__pycache__', '.git'}]
        for fn in filenames:
            if os.path.splitext(fn)[1] in EXT:
                yield os.path.join(dirpath, fn)


def scan(root, patterns):
    hits = collections.defaultdict(list)
    for path in walk(root):
        try:
            with open(path, encoding='utf-8', errors='replace') as fh:
                lines = fh.read().splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            for label, rx in patterns:
                if rx.search(line):
                    hits[label].append((os.path.relpath(path, root), n, line.strip()[:150]))
    return hits


PATTERNS = [
    ("sheet name 'Sponsor Interactions'", re.compile(r"Sponsor Interactions")),
    ("names the blended workbook", re.compile(r"Moneyball Main Version", re.I)),
    ("openpyxl write-mode load (no read_only)", re.compile(r"load_workbook\((?![^)]*read_only\s*=\s*True)")),
    ("workbook .save(", re.compile(r"\.save\(")),
    ("artifact-tool helper invocation", re.compile(r"artifact[-_]tool", re.I)),
]

bar('S5-1  TEXT SEARCH  (files read as text only; nothing under fec/ imported or executed)')
for label, root in (('LIVE', LIVE_FEC), ('WORKTREE', WT_FEC)):
    P('\n--- %s  %s' % (label, root))
    if not os.path.isdir(root):
        P('    (absent)')
        continue
    hits = scan(root, PATTERNS)
    for name, _ in PATTERNS:
        rows = hits.get(name, [])
        P('\n  [%s]  %d hit(s)' % (name, len(rows)))
        shown = rows if name.startswith('sheet name') or name.startswith('names the') else rows[:14]
        for rel, n, txt in shown:
            P('     %s:%d  %s' % (rel, n, txt))
        if len(rows) > len(shown):
            P('     ... %d more' % (len(rows) - len(shown)))

bar('S5-2  CANDIDATE ADJUDICATION : for every file that names the sheet, what is it allowed to write?')
CANDIDATES = [
    ('legislation/build_accepted_legislation_workbook.py',
     r'LEGISLATION_SHADOW_MODE|must be a child of|production_artifacts_written|'
     r'production_written.*False|TARGET_MODEL_SHEETS|allowed_root'),
    ('legislation/sync_sentinel_bill_ledger.py',
     r'^WORKBOOK|LEDGER_BASENAME|refuse anything but the ledger|args\.workbook'),
    ('legislation/run_greenlit_legislation_rank_shadow.py',
     r'shadow_recompute|must be a child|Worksheets\("Sponsor'),
    ('legislation/extract_legislation_workbook_audited_layout.py',
     r'production_written|WORKBOOK_BASENAME'),
    ('legislation/leg_evidence_recompute.py',
     r'workbook save|production-artifact\s*$|production-artifact|APPROVED_OUT|INTERACTION_SHEETS'),
    ('sync_sentinel_bill_ledger_artifact.cjs', r'Sponsor Interactions|LEDGER|ledger|workbook'),
    ('moneyball_core.py', r'def bill_corroboration|load_workbook'),
    ('surfaces/make_member_desk.py', r'ROLEMAP'),
]
for rel, rx in CANDIDATES:
    path = os.path.join(LIVE_FEC, *rel.split('/'))
    P('\n--- LIVE fec\\%s' % rel.replace('/', '\\'))
    if not os.path.isfile(path):
        P('    (absent)')
        continue
    pat = re.compile(rx)
    with open(path, encoding='utf-8', errors='replace') as fh:
        for n, line in enumerate(fh.read().splitlines(), 1):
            if pat.search(line):
                P('    %5d | %s' % (n, line.rstrip()[:140]))

bar('S5-2b  LIVE vs WORKTREE drift among the files that name the sheet')
def files_naming(root):
    out = set()
    if not os.path.isdir(root):
        return out
    for path in walk(root):
        try:
            with open(path, encoding='utf-8', errors='replace') as fh:
                if 'Sponsor Interactions' in fh.read():
                    out.add(os.path.relpath(path, root).replace('\\', '/'))
        except OSError:
            pass
    return out


a, b = files_naming(LIVE_FEC), files_naming(WT_FEC)
P('files naming the sheet: LIVE=%d  WORKTREE=%d  shared=%d' % (len(a), len(b), len(a & b)))
P('LIVE only ....... %s' % sorted(a - b))
P('WORKTREE only ... %s' % sorted(b - a))

bar('S5-2c  READING OF THE ABOVE')
P("""Reading the hits above:

  fec\\legislation\\build_accepted_legislation_workbook.py  builds all five role sheets
      (TARGET_MODEL_SHEETS, line 182-188) and routes every XLSX mutation through
      @oai/artifact-tool.  It is SHADOW-ONLY and fail-closed: validate_shadow_context()
      requires LEGISLATION_SHADOW_MODE=1, requires LEGISLATION_SHADOW_RUN_DIR and
      MONEYBALL_ROOT to equal the run directory, and requires that directory to be a
      CHILD of audits\\legfix5\\shadow_recompute.  Its outputs land in the run dir, and
      its receipt asserts production_written=False.  It cannot write the root workbook.

  fec\\legislation\\sync_sentinel_bill_ledger.py  DOES append a 'Sponsor Interactions' tab
      (line 1072) and DOES replace a workbook on disk (line 1316) -- but WORKBOOK is
      ROOT / LEDGER_BASENAME (line 36) and line 1219 records that it refuses any target
      but the ledger.  It writes 'Sentinel Bill Ledger.xlsx' (14 rows), not the blended
      workbook.  fec\\sync_sentinel_bill_ledger_artifact.cjs is its artifact-tool helper.

  fec\\legislation\\run_greenlit_legislation_rank_shadow.py  names the blended workbook and
      opens Worksheets('Sponsor Interactions') via Excel COM (line 611), but its output must
      be a child of audits\\legfix5\\shadow_recompute (lines 288-297) and it READS the sheet
      to compare ranks.

  fec\\legislation\\extract_legislation_workbook_audited_layout.py  and
  fec\\legislation\\leg_evidence_recompute.py  are verifiers: the first asserts
      production_written=False throughout, the second states in its module docstring that
      no workbook save or production-artifact write is performed.  Both READ the sheet.

  fec\\moneyball_core.py bill_corroboration() and fec\\surfaces\\make_member_desk.py
      READ 'Sponsor Interactions'.  Neither writes it.

So no shipped production producer writes 'Sponsor Interactions' in
'Moneyball Main Version - Blended.xlsx'.  The census below tests that claim against the
sheet's contents rather than resting on the search.""")

# ------------------------------------------------------------------ content
bar('S5-3  CONTENT CENSUS : what the sheet holds vs every local sponsor-bearing source')
WBS = L.xl(L.WORKBOOK, 'Sponsor Interactions')
ARCH = L.xl(L.SEL_ARCHIVE, 'All Bills')
OLD = L.xl(L.OLD_ARCHIVE, 'All Bills')
SENT_ALL = L.xl(L.SENTINEL, 'Sentinel Bill Ledger')
SENT = L.sentinel_scoring_rows()
MAN = L.manual_rows()
NAMES, BIOS = L.roster()
RES = L.Resolver(NAMES, BIOS)


def trip(member, bill, congress, section):
    """(member, bill, Congress, canonical category) -- the sheet's own natural key."""
    return (str(member or '').strip(), L.bill_ident(bill, congress),
            L.canonical_category(section))


wb_keys = {trip(r['Member'], r['Name'], r['Congress'], r['Section']) for r in WBS}
ar_keys = {trip(r['Member'], r['Name'], r['Congress'], r['Section'])
           for r in ARCH if L.canonical_role(r['Role']) == 'sponsor'}
ol_keys = {trip(r['Member'], r['Name'], r['Congress'], r['Section'])
           for r in OLD if L.canonical_role(r['Role']) == 'sponsor'}
se_keys = {trip(r.get('Member'), r.get('Bill'), r.get('Congress'), r.get('Section'))
           for r in SENT if L.canonical_role(r.get('Role')) == 'sponsor'}
ma_keys = {trip(r.get('Member'), r.get('Bill'), r.get('Congress'), r.get('Category'))
           for r in MAN if L.canonical_role(r.get('Role')) == 'sponsor'}
P("workbook 'Sponsor Interactions' rows ......................... %d  (distinct keys %d)"
  % (len(WBS), len(wb_keys)))
P('selected archive sponsor-role rows .......................... %d  (distinct keys %d)'
  % (sum(1 for r in ARCH if L.canonical_role(r['Role']) == 'sponsor'), len(ar_keys)))
P('older archive 20260624 sponsor-role rows .................... %d  (distinct keys %d)'
  % (sum(1 for r in OLD if L.canonical_role(r['Role']) == 'sponsor'), len(ol_keys)))
P('Sentinel VERIFIED scoring sponsor rows ...................... %d' % len(se_keys))
P('manual_bill_evidence.csv sponsor rows ....................... %d' % len(ma_keys))
frame = ar_keys | se_keys | ma_keys
P('\nworkbook vs the SELECTED archive:')
P('   in both ................................................. %d' % len(wb_keys & ar_keys))
P('   workbook only ........................................... %d' % len(wb_keys - ar_keys))
P('   selected archive only ................................... %d' % len(ar_keys - wb_keys))
P('workbook vs the OLDER archive (20260624):')
P('   in both ................................................. %d' % len(wb_keys & ol_keys))
P('   workbook only ........................................... %d' % len(wb_keys - ol_keys))
P('workbook vs the FULL scored frame (archive + sentinel + manual):')
P('   in both ................................................. %d' % len(wb_keys & frame))
P('   workbook only (no row anywhere in the scored frame) ..... %d' % len(wb_keys - frame))
P('   frame only (never reached the workbook sheet) ........... %d' % len(frame - wb_keys))

P('\nthe workbook-only keys, by Congress:')
for c, n in sorted(collections.Counter(k[1][1] for k in (wb_keys - frame)).items()):
    P('   C=%-5s %d' % (c, n))
P('the workbook-only keys, by member (top 15):')
for m, n in collections.Counter(k[0] for k in (wb_keys - frame)).most_common(15):
    P('   %-24s %d' % (m, n))
P('\nsample workbook-only keys:')
for k in sorted(wb_keys - frame, key=lambda k: (k[0], k[1]))[:20]:
    P('   %-22s %-16s C=%-5s %s' % (k[0], k[1][0], k[1][1], k[2]))

P('\nfile mtimes (a sheet older than the archive cannot have been derived from it):')
for rel in (L.WORKBOOK, L.SEL_ARCHIVE, L.OLD_ARCHIVE, L.SENTINEL, 'archive_leg.json',
            'legislation_routing_audit.json', 'manual_bill_evidence.csv'):
    p = os.path.join(L.ROOT, rel)
    import datetime
    P('   %-46s %s' % (rel, datetime.datetime.fromtimestamp(os.path.getmtime(p))))

# ------------------------------------------------------------------ trace
bar('S5-4  the three Tim Scott Member-Business-Lending bills, through every local source')
for bill, cong in (('S.3382', '117'), ('S.3992', '118'), ('S.762', '117')):
    k = L.bill_ident(bill, cong)
    P('\n-- %s (%sth)' % (bill, cong))
    P('   selected archive rows for this bill ...... %d ; roles = %s'
      % (sum(1 for r in ARCH if L.bill_ident(r['Name'], r['Congress']) == k),
         sorted({L.canonical_role(r['Role']) for r in ARCH
                 if L.bill_ident(r['Name'], r['Congress']) == k})))
    P('   selected archive Sponsor column .......... %s'
      % sorted({str(r.get('Sponsor')) for r in ARCH
                if L.bill_ident(r['Name'], r['Congress']) == k}))
    P('   selected archive Tim Scott rows .......... %s'
      % [(r['Section'], r['Role']) for r in ARCH
         if L.bill_ident(r['Name'], r['Congress']) == k and RES.resolve(r['Member']) == 'Tim Scott'])
    P("   workbook 'Sponsor Interactions' rows ..... %s"
      % [(r['Member'], r['Section']) for r in WBS if L.bill_ident(r['Name'], r['Congress']) == k])
    P('   older archive sponsor rows ............... %s'
      % [(r['Member'], r['Section']) for r in OLD
         if L.bill_ident(r['Name'], r['Congress']) == k and L.canonical_role(r['Role']) == 'sponsor'])
    sent_any = [r for r in SENT_ALL if L.bill_ident(r.get('Bill'), r.get('Congress')) == k]
    P('   Sentinel ledger rows (ANY status) ........ %d' % len(sent_any))
    if sent_any:
        P('      record types / statuses ............... %s'
          % sorted({(str(r.get('Record Type')), str(r.get('Review Status')),
                     str(r.get('Scoring Eligible'))) for r in sent_any}))
        P('      rows naming Tim Scott ................. %s'
          % [(r.get('Role'), r.get('Review Status'), r.get('Scoring Eligible'),
              r.get('Pending Reason')) for r in sent_any
             if str(r.get('Member') or '').strip() == 'Tim Scott'])
        P('      sponsor-role rows ..................... %s'
          % [(r.get('Member'), r.get('Review Status')) for r in sent_any
             if L.canonical_role(r.get('Role')) == 'sponsor'])
    P('   manual_bill_evidence rows ................ %s'
      % [(r.get('Member'), r.get('Role'), r.get('Category')) for r in MAN
         if L.bill_ident(r.get('Bill'), r.get('Congress')) == k])

bar('S5-5  contrast: the two Anna Luna bills the same census flagged, which DID get repaired')
for bill, cong in (('H.R.4686', '118'), ('H.R.6410', '118')):
    k = L.bill_ident(bill, cong)
    P('\n-- %s (%sth)' % (bill, cong))
    P('   selected archive roles ................... %s'
      % sorted({L.canonical_role(r['Role']) for r in ARCH
                if L.bill_ident(r['Name'], r['Congress']) == k}))
    P('   Sentinel VERIFIED scoring rows for it .... %s'
      % [(r.get('Member'), r.get('Role'), r.get('Section')) for r in SENT
         if L.bill_ident(r.get('Bill'), r.get('Congress')) == k])
    P('   manual_bill_evidence rows ................ %s'
      % [(r.get('Member'), r.get('Role'), r.get('Category')) for r in MAN
         if L.bill_ident(r.get('Bill'), r.get('Congress')) == k])
P('\n(these two are why the DEFECT population is 5 cells but the missing weight is only 3 cells:')
P(' the sentinel/manual lane already supplies Anna Luna\'s sponsor rows at frame source_row')
P(' 10190 and 10192, so her credit is complete in archive_leg.json.)')
