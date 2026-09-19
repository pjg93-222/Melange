import sys, time
from pathlib import Path
src = Path(sys.argv[1])
t0 = time.monotonic()
rows = cash = malformed = 0
first_cash_row = first_cash_off = None
last_cash_row = None
bad_prefix = 0
off = 0
types = {}
with src.open("rb") as inp:
    for line in inp:
        rows += 1
        f = line.rstrip(b"\r\n").split(b"|")
        if len(f) != 21:
            malformed += 1
            if not (len(f[0]) == 9 and f[0][:1] == b"C" and f[0][1:].isdigit()):
                bad_prefix += 1
        elif f[5] in (b"24G", b"24K"):
            cash += 1
            if first_cash_row is None:
                first_cash_row, first_cash_off = rows, off
            last_cash_row = rows
        if len(f) == 21:
            types[f[5]] = types.get(f[5], 0) + 1
        off += len(line)
t1 = time.monotonic()
top = sorted(types.items(), key=lambda kv: -kv[1])[:8]
print(f"{src.parent.name}: rows={rows} cash={cash} malformed={malformed} malformed_without_C########={bad_prefix} scan={t1-t0:.1f}s")
print(f"  first cash row={first_cash_row} at byte {first_cash_off}; last cash row={last_cash_row}; bytes={off}")
print("  top transaction types:", ", ".join(f"{k.decode()}={v}" for k, v in top))
