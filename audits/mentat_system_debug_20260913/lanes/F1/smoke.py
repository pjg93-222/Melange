"""F1 smoke on port 8816 only. Never touches another console.

Part A: read-only console - /api/health carries the build block, /api/restart 403.
Part B: writable console on a throwaway data root - a new module in mentat/app
makes the running process stale, POST /api/restart hands the port back to the
launcher, and the console returns on the SAME port with a new pid.

Windows SO_REUSEADDR lets a second process bind a port that is already in use,
so each part waits for 8816 to be genuinely free before it starts anything.
"""
import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

APP = Path(r"C:\Users\pgoff\Mentat\mentat\app")
PORT = 8816
BASE = "http://127.0.0.1:%d" % PORT
PROBE = APP / "_f1_stale_probe.py"
failures = []


def check(label, condition, detail=""):
    print(("  PASS  " if condition else "  FAIL  ") + label + (" :: " + str(detail) if detail else ""))
    if not condition:
        failures.append(label)


def get(path, timeout=4):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as response:
        return json.load(response)


def post(path, token, payload=None, timeout=25):
    request = urllib.request.Request(BASE + path, method="POST",
                                     data=json.dumps(payload or {}).encode(),
                                     headers={"Content-Type": "application/json",
                                              "X-Mentat-Token": token or "",
                                              "Origin": "http://127.0.0.1:%d" % PORT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def port_answers():
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
            return True
    except OSError:
        return False


def wait_until_free(seconds=30):
    deadline = time.time() + seconds
    while time.time() < deadline and port_answers():
        time.sleep(0.5)
    return not port_answers()


def wait_for_health(seconds, other_than=None):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            health = get("/api/health", timeout=3)
            if other_than is None or health.get("pid") != other_than:
                return health
        except (urllib.error.URLError, OSError, ValueError):
            pass
        time.sleep(0.5)
    return None


def powershell(script):
    return subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                          capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)


def sweep(tag):
    """Stop every console this script started, identified by its data root."""
    script = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and "
              "$_.CommandLine.Contains('mentat\\app\\server.py') -and $_.CommandLine.Contains('" + tag + "') } | "
              "ForEach-Object { Write-Output ('  swept pid ' + $_.ProcessId); "
              "Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }")
    print((powershell(script).stdout or "").rstrip() or "  (nothing left to sweep)")


def live_consoles():
    script = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and "
              "$_.CommandLine.Contains('mentat\\app\\server.py') } | "
              "ForEach-Object { Write-Output ('  live: ' + $_.ProcessId + ' ' + $_.CommandLine) }")
    print((powershell(script).stdout or "").rstrip() or "  (no console running)")


def start_console(data_root, read_only):
    arguments = [str(APP / "server.py"), "--port", str(PORT), "--data-root", data_root]
    if read_only:
        arguments.append("--read-only")
    quoted = " ".join('"' + value + '"' for value in arguments)
    powershell('Start-Process -FilePath "%s" -ArgumentList \'%s\' -WindowStyle Hidden' % (sys.executable, quoted))
    return wait_for_health(60)


print("Pre-flight")
check("port 8816 is free before the smoke", wait_until_free(20))

print()
print("Part A - read-only console on 8816")
with tempfile.TemporaryDirectory(prefix="MENTAT F1a ") as root:
    health = start_console(root, read_only=True)
    try:
        check("read-only console answered /api/health", bool(health))
        if health:
            for field in ("git_sha", "code_sha256", "assets_sha256", "on_disk_code_sha256_now",
                          "on_disk_assets_sha256_now", "started_at", "port", "pid", "busy"):
                check("health carries " + field, field in health, health.get(field))
            check("health reports read_only", health.get("read_only") is True)
            check("health reports this port", health.get("port") == PORT, health.get("port"))
            check("health reports idle", health.get("busy") is False)
            check("part A data root", Path(health["data_root"]) == Path(root), health.get("data_root"))
            check("code hash matches disk", health["code_sha256"] == health["on_disk_code_sha256_now"])
            light = get("/api/session?light=1")
            check("light session carries the build block",
                  light.get("build", {}).get("code_sha256") == health["code_sha256"])
            check("light session repeats the fields flat", light.get("code_sha256") == health["code_sha256"])
            status, body = post("/api/restart", light.get("token"))
            check("POST /api/restart is 403 on a read-only console", status == 403, body)
            check("the 403 names the read-only preview", "read-only" in str(body.get("error", "")), body)
    finally:
        sweep("MENTAT F1a ")
        check("port 8816 released after part A", wait_until_free(25))

print()
print("Part B - writable console on 8816 replaced on the same port")
with tempfile.TemporaryDirectory(prefix="MENTAT F1b ") as root:
    health = start_console(root, read_only=False)
    first = health and health.get("pid")
    try:
        check("writable console answered /api/health", bool(health))
        if health:
            check("part B data root", Path(health["data_root"]) == Path(root), health.get("data_root"))
            PROBE.write_text("# F1 smoke probe; removed by smoke.py\n", encoding="utf-8")
            fresh = get("/api/health")
            check("a new module in mentat/app makes the running build stale",
                  fresh["on_disk_code_sha256_now"] != fresh["code_sha256"])
            check("assets are unaffected by a python-only change",
                  fresh["on_disk_assets_sha256_now"] == fresh["assets_sha256"])
            token = get("/api/session?light=1")["token"]
            status, body = post("/api/restart", token)
            check("POST /api/restart accepted", (status, body.get("restarting")) == (200, True), body)
            after = wait_for_health(240, other_than=first)
            second = after and after.get("pid")
            check("the console came back on the SAME port with a new pid",
                  bool(after) and second != first, "%s -> %s" % (first, second))
            if after:
                check("the returned console is current",
                      after["code_sha256"] == after["on_disk_code_sha256_now"])
                check("the returned console kept the data root", Path(after["data_root"]) == Path(root))
                check("the returned console is writable", after.get("read_only") is False)
            else:
                live_consoles()
                log = Path(root) / ("server-%d.stderr.log" % PORT)
                if log.exists():
                    print("  launcher server log:", log.read_text(encoding="utf-8", errors="replace")[:1200])
    finally:
        if PROBE.exists():
            PROBE.unlink()
            print("  removed", PROBE)
        sweep("MENTAT F1b ")
        wait_until_free(25)

print()
print("stray files in mentat/app:", [p.name for p in APP.glob("_f1*")] or "none")
print("FAILURES:", failures if failures else "none")
sys.exit(1 if failures else 0)
