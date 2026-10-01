"""Fixture for test_mutation_check.py: a real CSV check that deliberately ignores the id column.
Passes only with exactly 20 rows, x finite, positive and strictly increasing, and y == 2x + 1. Mutations of
x, y and the row set are killed; mutations of id survive and show up as blind spots."""
import csv
import math
import sys


def main(path: str) -> int:
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        xs = [float(r["x"]) for r in rows]
        ys = [float(r["y"]) for r in rows]
    except (OSError, KeyError, ValueError, TypeError):
        return 1
    if len(rows) != 20 or not all(math.isfinite(v) for v in xs + ys):
        return 1
    if not all(x > 0 for x in xs) or any(b <= a for a, b in zip(xs, xs[1:])):
        return 1
    return 0 if all(abs(y - (2 * x + 1)) < 1e-9 for x, y in zip(xs, ys)) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
