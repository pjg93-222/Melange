from pathlib import Path

p = Path(__file__).resolve().parents[1] / 'osc' / 'validate.py'
s = p.read_text(encoding='utf-8')
mA = '    # --- national vs independent browser evidence'
mB = '    # --- PAC vectors'
mC = '    # --- legacy / old-collector baseline'
mD = '    # --- outputs'
a, b, c, d = (s.index(m) for m in (mA, mB, mC, mD))
head, nat, pac, rest, tail = s[:a], s[a:b], s[b:c], s[c:d], s[d:]
call = ('    national_checks(ck, t)\n    pac_checks(ck, t)\n    rest_checks(ck, t, ex)\n')
funcs = ('\n\ndef national_checks(ck, t):\n' + nat.rstrip() + '\n'
         '\n\ndef pac_checks(ck, t):\n' + pac.rstrip() + '\n'
         '\n\ndef rest_checks(ck, t, ex):\n' + rest.rstrip() + '\n')
nat_only = '''

def run_national_validation(tables, out_dir):
    """Standalone national-only validation (offline): writes national_crosschecks.csv next to the national CSVs."""
    ck = Checks()
    national_checks(ck, tables)
    out = Path(out_dir)
    atomic_write_csv(out / 'national_crosschecks.csv', ['check_id', 'description', 'status', 'expected', 'actual', 'detail'], ck.rows)
    print(f"[validate-national] {dict(Counter(r['status'] for r in ck.rows))}; failed={[r['check_id'] for r in ck.rows if r['status'] == 'FAIL']}", flush=True)
    return ck
'''
# tail = outputs part of run_validation + following helper functions; keep run_validation's tail then append new functions after it
end_run = tail.index('\n\ndef write_census_gaps')
new = head + call + tail[:end_run] + nat_only + funcs + tail[end_run:]
p.write_text(new, encoding='utf-8')
print('split ok')
