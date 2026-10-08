"""Run a command in a working directory and report its exit code, wall time and the peak resident memory of the process tree.

usage: python run_with_peak.py <cwd> <logfile> -- <command> [args...]
The command's stdout and stderr go to <logfile>. The peak is sampled every 0.1 s (private working set summed over the tree).
"""
import subprocess
import sys
import time

import psutil

cwd, log = sys.argv[1], sys.argv[2]
cmd = sys.argv[sys.argv.index('--') + 1:]
started = time.time()
with open(log, 'wb') as handle:
    proc = subprocess.Popen(cmd, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT)
    root, peak = psutil.Process(proc.pid), 0
    while proc.poll() is None:
        try:
            tree = [root] + root.children(recursive=True)
            total = 0
            for p in tree:
                try:
                    total += p.memory_info().rss
                except psutil.Error:
                    pass
            peak = max(peak, total)
        except psutil.Error:
            pass
        time.sleep(0.1)
print('exit=%s wall=%.1fs peak_tree_rss=%.0f MB  cmd=%s' % (proc.returncode, time.time() - started, peak / 2 ** 20, ' '.join(cmd)))
sys.exit(proc.returncode)
