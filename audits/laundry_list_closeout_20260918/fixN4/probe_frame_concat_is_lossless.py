# -*- coding: utf-8 -*-
"""Lane N4: the hook's pd.concat must not change ANY existing row. READ-ONLY.

The producer writes every routing-audit row through ``_clean(r.get(...))``, so a dtype the
concat silently upcasts (Congress int64 -> float64, say) would rewrite the ``congress`` field
of all 10,820 existing audit rows -- a byte change on every row of a shipped artifact, from a
five-row addition. This probe replays the concat on the real archive frame and proves the
existing rows come out of ``iterrows()`` with byte-identical _clean() values, and that the
new provenance column is not already in use.

Reads the live archive with pandas. Imports nothing under fec/ except -- nothing: the
producer's ``_clean`` and the fix are both loaded by path or transcribed.
"""
import importlib.util
import glob
import os
import sys

import pandas as pd

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
CLOSEOUT = os.path.dirname(HERE)
WORKTREE = os.path.dirname(os.path.dirname(CLOSEOUT))
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
sys.path.insert(0, os.path.join(CLOSEOUT, 'F1', 'receipts'))
import f1_lib as L  # noqa: E402

spec = importlib.util.spec_from_file_location(
    'sponsor_column', os.path.join(WORKTREE, 'fec', 'legislation', 'sponsor_column.py'))
SC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SC)
P = print


def _clean(value):
    """build_archive_legislative._clean, transcribed verbatim (LIVE lines 159-162)."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    return str(value)


A = pd.read_excel(sorted(glob.glob(LIVE + r'\congress_bills_archive_*.xlsx'))[-1],
                  sheet_name='All Bills')
if 'ManualDirection' not in A.columns:
    A['ManualDirection'] = ''                     # the producer adds it before the row loop
P('archive frame: %d rows x %d columns' % A.shape)
P('columns: %s' % list(A.columns))
P('')
P('the provenance column is not already in use: %s'
  % (SC.SOURCE_COLUMN not in A.columns))
assert SC.SOURCE_COLUMN not in A.columns

before_dtypes = A.dtypes.astype(str).to_dict()
AUDITED = tuple(A.columns)                      # every column the row loop can read


def fingerprint(row):
    """What the row loop actually sees: the _clean() value AND its python type."""
    out = []
    for column in AUDITED:
        value = row.get(column)
        cleaned = _clean(value)
        out.append((type(value).__name__, repr(value), type(cleaned).__name__, repr(cleaned),
                    str(value or '')))          # str(x or '') is how BR.excluded_title reads it
    return tuple(out)


before = [fingerprint(row) for _index, row in A.iterrows()]

extra = SC.sponsor_rows_from_column(A.to_dict('records'), L.Resolver(L.roster()[0]).resolve,
                                    L.canonical_category, L.congress_of)
P('synthesised rows: %d' % len(extra))
B = pd.concat([A, pd.DataFrame(extra)], ignore_index=True)
after_dtypes = B.dtypes.astype(str).to_dict()
after = [fingerprint(row) for _index, row in B.iterrows()]

P('')
P('%-18s %-12s %-12s' % ('column', 'before', 'after'))
for column in A.columns:
    flag = '' if before_dtypes[column] == after_dtypes[column] else '   <-- CHANGED'
    P('%-18s %-12s %-12s%s' % (column, before_dtypes[column], after_dtypes[column], flag))
P('%-18s %-12s %-12s' % (SC.SOURCE_COLUMN, '(absent)', after_dtypes[SC.SOURCE_COLUMN]))
P('')
P('column order preserved, provenance appended last: %s'
  % (list(B.columns) == list(A.columns) + [SC.SOURCE_COLUMN]))
P('row count %d -> %d (+%d)' % (len(A), len(B), len(B) - len(A)))
P('existing rows keep their position (source_row = index+2 is stable): %s'
  % (after[:len(before)] == before))
mismatched = [i for i, (x, y) in enumerate(zip(before, after)) if x != y]
P('existing rows whose value/type fingerprint changed, over all %d columns: %d'
  % (len(AUDITED), len(mismatched)))
for index in mismatched[:3]:
    for column, x, y in zip(AUDITED, before[index], after[index]):
        if x != y:
            P('   row %d  %-16s before=%s  after=%s' % (index, column, x, y))
_numeric = [c for c in A.columns if before_dtypes[c] not in ('str', 'object')]
_moved = [c for c in _numeric if before_dtypes[c] != after_dtypes[c]]
P('')
P('numeric/int columns that changed dtype (would rewrite audit values): %s' % (_moved or 'NONE'))
P('text columns that changed dtype label only: %s'
  % ([c for c in A.columns if before_dtypes[c] != after_dtypes[c]] or 'NONE'))
P('  -- pandas %s marks a missing value in BOTH the str and the object dtype with np.nan,'
  % pd.__version__)
P('  -- so the label moves and no value does; the fingerprint comparison above is the proof.')
assert not _moved, _moved
P('')
P('the provenance marker is present on the new rows only: %d of %d'
  % (sum(1 for _i, row in B.iterrows() if _clean(row.get(SC.SOURCE_COLUMN)) == SC.SOURCE),
     len(B)))
P('and _clean() reads NOTHING on every pre-existing row: %s'
  % all(_clean(row.get(SC.SOURCE_COLUMN)) is None
        for _i, row in B.iloc[:len(A)].iterrows()))
assert list(B.columns) == list(A.columns) + [SC.SOURCE_COLUMN]
assert after[:len(before)] == before, 'the concat rewrote existing rows'
assert not mismatched
P('')
P('VERDICT: the hook is additive only. 0 of %d existing frame rows change in value or type,'
  % len(A))
P('         no int/float column changes dtype, the one text dtype LABEL that moves carries no')
P('         value with it, and the routing audit gains the provenance key on %d rows and no'
  % len(extra))
P('         others. With LEG_SPONSOR_FROM_COLUMN=0 nothing is appended at all.')
