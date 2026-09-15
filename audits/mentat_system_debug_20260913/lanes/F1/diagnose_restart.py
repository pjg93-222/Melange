"""Reproduce the F1 restart with the launcher in the foreground, output visible."""
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

APP = Path(r"C:\Users\pgoff\Mentat\mentat\app")
PORT = 8816
BASE = f"http://127.0.0.1:{PORT}"
PROBE = APP / "_f1_stale_probe.py"


def get(path, timeout=4):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as response:
        return json.load(response)


def sweep(data_root):
    script = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and "
              "$_.CommandLine.Contains('server.py') -and $_.CommandLine.Contains(" +
              json.dumps(data_root).replace('"', "'") + ") } | "
              "ForEach-Object { Write-Output ('sweeping pid ' + $_.ProcessId); "
              "Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }")
    done = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                          capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    print((done.stdout or "").strip() or "  (nothing to sweep)")


with tempfile.TemporaryDirectory(prefix="MENTAT F1 diag ") as root:
    arguments = [str(APP / "server.py"), "--port", str(PORT), "--data-root", root]
    quoted = " ".join('"' + value + '"' for value in arguments)
    subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                    f'Start-Process -FilePath "{sys.executable}" -ArgumentList \'{quoted}\' -WindowStyle Hidden'],
                   capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
    health = None
    for _ in range(90):
        try:
            health = get("/api/health")
            break
        except OSError:
            time.sleep(0.5)
    try:
        print("running console pid", health["pid"], "port", health["port"])
        print("  data_root        :", health["data_root"])
        print("  report_directory :", health["report_directory"])
        print("  project          :", health["project"])
        print("  code_sha256      :", health["code_sha256"])
        print("  busy / read_only :", health["busy"], health["read_only"])
        PROBE.write_text("# F1 diagnostic probe\n", encoding="utf-8")
        print("  on_disk now      :", get("/api/health")["on_disk_code_sha256_now"])
        print()
        print("--- launcher output ---")
        # Disk-backed diagnostics: a detached Windows child can inherit pipe
        # handles and keep subprocess.run blocked long after the launcher exits.
        with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as output:
            done = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                   str(APP / "Start-MentatApp.ps1"), "-NoBrowser", "-Port", str(PORT),
                                   "-DataRoot", root],
                                  stdout=output, stderr=output, timeout=180, cwd=root)
            output.seek(0)
            print("exit code:", done.returncode)
            print(output.read())
        print("--- after ---")
        try:
            print("health on 8816 now:", json.dumps({k: get('/api/health')[k] for k in ('pid', 'port', 'code_sha256')}))
        except OSError as error:
            print("8816 unreachable:", error)
    finally:
        if PROBE.exists():
            PROBE.unlink()
        time.sleep(1)
        sweep(root)
        time.sleep(1)
