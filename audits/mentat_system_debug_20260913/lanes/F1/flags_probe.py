"""Which creationflags let a detached PowerShell actually run?"""
import os
import subprocess
import tempfile
import time
from pathlib import Path

root = Path(tempfile.mkdtemp(prefix="F1 flags "))
cases = {
    "DETACHED_PROCESS|CREATE_NEW_PROCESS_GROUP":
        subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
    "CREATE_NO_WINDOW|CREATE_NEW_PROCESS_GROUP":
        subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP,
    "CREATE_NO_WINDOW":
        subprocess.CREATE_NO_WINDOW,
}
for label, flags in cases.items():
    marker = root / (label.replace("|", "_") + ".txt")
    script = "[IO.File]::WriteAllText('" + str(marker).replace("\\", "\\\\") + "', 'ran at ' + (Get-Date).ToString())"
    process = subprocess.Popen(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                              close_fds=True, creationflags=flags)
    deadline = time.time() + 20
    while time.time() < deadline and not marker.exists():
        time.sleep(0.25)
    code = process.poll()
    for _ in range(40):
        if code is not None:
            break
        time.sleep(0.25)
        code = process.poll()
    print("%-46s ran=%-6s exit=%s" % (label, marker.exists(), code))
print("probe directory:", root)
