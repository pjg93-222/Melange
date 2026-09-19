import hashlib, time, sys
from pathlib import Path
link = Path(sys.argv[1]); out = Path(sys.argv[2]); n = int(sys.argv[3])
t0 = time.monotonic()
with link.open("rb") as st: d = hashlib.file_digest(st, "sha256").hexdigest()
t1 = time.monotonic()
print(f"sha256 of {link.name} ({link.stat().st_size/2**30:.2f} GiB): {t1-t0:.2f}s -> {(link.stat().st_size/2**30)/(t1-t0):.2f} GiB/s")
print("digest", d[:20])
src = Path(sys.argv[4])
t2 = time.monotonic(); written = 0
with src.open("rb") as inp, out.open("wb") as dst:
    for i, line in enumerate(inp):
        if i >= n: break
        dst.write(line); written += len(line)
t3 = time.monotonic()
print(f"prefix: {n} lines, {written} bytes ({written/2**20:.1f} MiB) in {t3-t2:.2f}s; mean {written/n:.1f} bytes/row")
