# -*- coding: utf-8 -*-
"""STEP 1 + STEP 2 of the N12 v2 LIVE apply: preconditions, then BEFORE fingerprints.

Read-only.  Opens the live database with mode=ro and query_only=ON, touches nothing else.
Everything it prints is the receipt; it also writes a01_before.json for the verifier to compare.
"""
import glob
import hashlib
import io
import json
import os
import subprocess
import sqlite3
import sys

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = os.path.join(LIVE, 'social_media.db')
STANCE = os.path.join(LIVE, 'data', 'stance')
OUT = os.path.dirname(os.path.abspath(__file__))
PROBE_ROWID = 245771


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for block in iter(lambda: fh.read(chunk), b''):
            h.update(block)
    return h.hexdigest()


def sha256_text(s):
    return hashlib.sha256((s or '').encode('utf-8')).hexdigest()


def open_ro(path):
    con = sqlite3.connect('file:%s?mode=ro' % path.replace('\\', '/'), uri=True, timeout=300)
    con.execute('PRAGMA query_only=ON')
    return con


def main():
    rec = {}
    print('=' * 78)
    print('STEP 1  PRECONDITIONS')
    print('=' * 78)

    locks = sorted(glob.glob(os.path.join(LIVE, '.pipeline_run.lock*')))
    rec['pipeline_run_locks'] = locks
    print('pipeline_run_lock glob (%s):' % os.path.join(LIVE, '.pipeline_run.lock*'))
    print('  %s' % (locks if locks else 'NONE -- precondition met'))

    other = sorted(os.path.basename(p) for p in glob.glob(os.path.join(LIVE, '*.lock')))
    rec['other_lock_files_at_root'] = other
    print('other *.lock files at the live root (not the pipeline lock, informational): %s' % other)

    # process census: every python/R/Excel process, with its command line
    ps = ('Get-CimInstance Win32_Process -Filter "Name like \'%python%\' or '
          "Name like '%Rscript%' or Name like '%EXCEL%' or Name like '%R.exe%'\" | "
          'Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Depth 3 -Compress')
    raw = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', ps],
                         capture_output=True, text=True, timeout=120).stdout
    procs = json.loads(raw) if raw.strip() else []
    if isinstance(procs, dict):
        procs = [procs]
    keep = [p for p in procs
            if (p.get('CommandLine') or '') and
            ('python' in (p.get('Name') or '').lower() or 'excel' in (p.get('Name') or '').lower()
             or (p.get('Name') or '').lower().startswith('r'))]
    rec['python_r_excel_processes_with_cmdline'] = keep
    print('\npython / Rscript / R / EXCEL processes carrying a command line: %d' % len(keep))
    for p in keep:
        print('  pid=%-7s %-12s %s' % (p.get('ProcessId'), p.get('Name'),
                                       (p.get('CommandLine') or '')[:190]))
    bad = [p for p in keep
           if any(t in (p.get('CommandLine') or '').lower()
                  for t in ('run_pipeline', 'refresh', 'collector', 'collect_'))]
    rec['forbidden_processes'] = bad
    print('run_pipeline / refresh / collector among them: %s'
          % (bad if bad else 'NONE -- precondition met'))
    excel = [p for p in procs if 'excel' in (p.get('Name') or '').lower()]
    rec['excel_processes'] = excel
    print('EXCEL processes: %s' % (excel if excel else 'NONE -- precondition met'))

    for suffix in ('', '-wal', '-shm'):
        p = DB + suffix
        exists = os.path.exists(p)
        size = os.path.getsize(p) if exists else None
        rec['sidecar' + (suffix or '-main')] = {'exists': exists, 'bytes': size}
        print('%-24s exists=%-5s bytes=%s' % (os.path.basename(p), exists, size))
    wal = DB + '-wal'
    wal_ok = (not os.path.exists(wal)) or os.path.getsize(wal) == 0
    rec['wal_zero_or_absent'] = wal_ok
    print('-wal absent or 0 bytes: %s%s' % (wal_ok, '  -- precondition met' if wal_ok else ''))

    print('\n' + '=' * 78)
    print('STEP 2  BEFORE FINGERPRINTS')
    print('=' * 78)
    rec['db_path'] = DB
    rec['db_bytes'] = os.path.getsize(DB)
    rec['db_sha256'] = sha256_file(DB)
    rec['db_mtime'] = os.path.getmtime(DB)
    print('social_media.db  bytes=%d' % rec['db_bytes'])
    print('social_media.db  sha256=%s' % rec['db_sha256'])

    con = open_ro(DB)
    rec['journal_mode'] = con.execute('PRAGMA journal_mode').fetchone()[0]
    rec['speeches_rows'] = con.execute('SELECT COUNT(*) FROM speeches').fetchone()[0]
    rec['interview_rows'] = con.execute(
        "SELECT COUNT(*) FROM speeches WHERE source='INTERVIEW'").fetchone()[0]
    print('journal_mode=%s   speeches rows=%d   INTERVIEW rows=%d'
          % (rec['journal_mode'], rec['speeches_rows'], rec['interview_rows']))

    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    counts = {}
    for t in tables:
        counts[t] = con.execute('SELECT COUNT(*) FROM "%s"' % t).fetchone()[0]
    rec['table_row_counts'] = counts
    print('tables: %d' % len(tables))
    for t in tables:
        print('  %-44s %d' % (t, counts[t]))

    row = con.execute('SELECT rowid,member,date,source,chamber,package,nwords,text FROM speeches '
                      'WHERE rowid=?', (PROBE_ROWID,)).fetchone()
    if row is None:
        rec['probe_row'] = None
        print('\nPROBE rowid %d: ABSENT' % PROBE_ROWID)
    else:
        rec['probe_row'] = {'rowid': row[0], 'member': row[1], 'date': row[2], 'source': row[3],
                           'chamber': row[4], 'package': row[5], 'nwords': row[6],
                           'text_chars': len(row[7] or ''), 'text_sha256': sha256_text(row[7]),
                           'text_words': len((row[7] or '').split()), 'text': row[7]}
        pr = rec['probe_row']
        print('\nPROBE rowid %d  member=%r date=%s source=%s' % (row[0], row[1], row[2], row[3]))
        print('  nwords=%d  len(text.split())=%d  text_chars=%d'
              % (pr['nwords'], pr['text_words'], pr['text_chars']))
        print('  text sha256=%s' % pr['text_sha256'])
        print('  text: %s' % (row[7] or ''))
    con.close()

    print('\nstance / interview-extract files (NOT touched by this lane):')
    rec['stance_files'] = {}
    for name in ('interviews_cu.csv', 'interviews_cu.receipt.json', 'press_component_meta.json'):
        p = os.path.join(STANCE, name)
        if os.path.exists(p):
            e = {'path': p, 'bytes': os.path.getsize(p), 'sha256': sha256_file(p),
                 'mtime': os.path.getmtime(p)}
        else:
            e = {'path': p, 'bytes': None, 'sha256': None, 'mtime': None}
        rec['stance_files'][name] = e
        print('  %-30s bytes=%-9s sha256=%s' % (name, e['bytes'], e['sha256']))
    # prove there is not a second copy of the extract somewhere else under the live tree
    hits = sorted(glob.glob(os.path.join(LIVE, 'data', '**', 'interviews_cu.*'), recursive=True))
    rec['interviews_cu_glob_under_data'] = hits
    print('  every interviews_cu.* under %s: %s'
          % (os.path.join(LIVE, 'data'), [os.path.relpath(h, LIVE) for h in hits]))

    with io.open(os.path.join(OUT, 'a01_before.json'), 'w', encoding='utf-8', newline='\n') as fh:
        json.dump(rec, fh, ensure_ascii=False, indent=1, sort_keys=True)
    print('\nwrote %s' % os.path.join(OUT, 'a01_before.json'))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
