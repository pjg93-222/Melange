"""Fixture for test_mutation_check.py: a REAL check. Passes (exit 0) only when "values" is a strictly
increasing list of at least 5 numbers, each in (0, 100]. Every auto mutation of series.json breaks it."""
import json
import sys


def main(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as fh:
            values = json.load(fh)["values"]
    except (OSError, ValueError, KeyError, TypeError):
        return 1
    if not isinstance(values, list) or len(values) < 5:
        return 1
    if not all(isinstance(v, (int, float)) and 0 < v <= 100 for v in values):
        return 1
    return 0 if all(b > a for a, b in zip(values, values[1:])) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
