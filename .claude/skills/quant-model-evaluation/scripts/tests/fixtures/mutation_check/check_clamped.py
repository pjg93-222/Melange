"""Fixture for test_mutation_check.py: a CLAMPED check with a planted blind spot. It checks range, then
tests monotonicity on the running maximum of the series instead of the series itself. A running max is
always non-decreasing, so reversed or locally swapped (non-monotone) series pass; mutation_check.py must
report them as surviving mutants (WOUNDED) while range-breaking mutants are killed."""
import json
import sys


def main(path: str) -> int:
    try:
        with open(path, encoding="utf-8") as fh:
            values = json.load(fh)["values"]
    except (OSError, ValueError, KeyError, TypeError):
        return 1
    if not values or not all(isinstance(v, (int, float)) and 0 < v <= 100 for v in values):
        return 1
    running, clamped = float("-inf"), []
    for v in values:  # the bug: monotonicity is tested on max-so-far, which can never decrease
        running = max(running, v)
        clamped.append(running)
    return 0 if all(b >= a for a, b in zip(clamped, clamped[1:])) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
