"""Fixture for test_mutation_check.py: a check that never finishes and leaves a grandchild behind. It starts a
child process that sleeps 30 s, writes that child's PID to argv[2], then sleeps 30 s itself. mutation_check.py
must kill the whole process tree when --timeout expires, so neither process may outlive the run."""
import subprocess
import sys
import time

if __name__ == "__main__":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    with open(sys.argv[2], "w", encoding="ascii") as fh:
        fh.write(str(child.pid))
    time.sleep(30)
