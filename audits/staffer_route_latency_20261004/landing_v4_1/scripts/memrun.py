"""Run a command, poll the RSS of its whole process tree, kill it above a cap, and write the output to a log.

usage: python memrun.py <log> <cap_mb> -- <command...>
Prints one line at the end: exit code, wall seconds, peak RSS (MB), and whether the cap killed it.
"""
import subprocess
import sys
import time

import psutil


def main():
    log, cap_mb = sys.argv[1], float(sys.argv[2])
    command = sys.argv[sys.argv.index('--') + 1:]
    started = time.time()
    peak, killed = 0, False
    with open(log, 'wb') as out:
        proc = subprocess.Popen(command, stdout=out, stderr=subprocess.STDOUT)
        root = psutil.Process(proc.pid)
        while proc.poll() is None:
            try:
                total = sum(p.memory_info().rss for p in [root, *root.children(recursive=True)] if p.is_running())
            except psutil.Error:
                total = 0
            peak = max(peak, total)
            if total > cap_mb * 1024 * 1024:
                killed = True
                for p in [root, *root.children(recursive=True)]:
                    try:
                        p.kill()
                    except psutil.Error:
                        pass
                break
            time.sleep(0.2)
        proc.wait()
    print('exit=%s wall=%.1fs peak_rss=%.0fMB cap_killed=%s' % (proc.returncode, time.time() - started, peak / 1048576, killed))


if __name__ == '__main__':
    main()
