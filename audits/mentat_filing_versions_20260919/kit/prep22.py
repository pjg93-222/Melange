import time, sys
from pathlib import Path
src = Path(sys.argv[1]); out = Path(sys.argv[2]); n = int(sys.argv[3])
t2 = time.monotonic(); written = 0; cash = 0
with src.open("rb") as inp, out.open("wb") as dst:
    for i, line in enumerate(inp):
        if i >= n: break
        dst.write(line); written += len(line)
        f = line.split(b"|")
        if len(f) == 21 and f[5] in (b"24G", b"24K"): cash += 1
t3 = time.monotonic()
print(f"prefix: {n} lines, {written} bytes ({written/2**20:.1f} MiB), {cash} cash rows ({100*cash/n:.2f}%) in {t3-t2:.2f}s")
