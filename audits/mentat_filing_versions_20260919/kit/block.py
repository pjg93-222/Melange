import sys, time
from pathlib import Path
src = Path(sys.argv[1]); out = Path(sys.argv[2]); start = int(sys.argv[3])
t0 = time.monotonic(); rows = written = 0
with src.open("rb") as inp, out.open("wb") as dst:
    for i, line in enumerate(inp, 1):
        if i < start: continue
        dst.write(line); rows += 1; written += len(line)
print(f"block: rows={rows} bytes={written} ({written/2**20:.1f} MiB) in {time.monotonic()-t0:.1f}s")
