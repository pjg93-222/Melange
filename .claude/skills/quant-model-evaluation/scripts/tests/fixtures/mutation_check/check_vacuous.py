"""Fixture for test_mutation_check.py: a VACUOUS check. It never looks at its input and always passes,
so no mutant can kill it; mutation_check.py must record KILLED ("vacuous check")."""
import sys

if __name__ == "__main__":
    sys.exit(0)
