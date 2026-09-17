"""Serve the real cross-reference state read-only on a throwaway port and read the dwarfed route.

Starts `python server.py --port 8836 --read-only` from mentat/app, polls until it answers,
fetches /api/cross-reference?industry=Banking, ?industry=Fintech and the pointer path,
prints the top-level keys and digest counts, asserts no total-like key exists anywhere,
then terminates the server. Reads only; the server is read-only.
"""
import json, subprocess, sys, time, urllib.request, urllib.error

APP = r"C:\Users\pgoff\Mentat\mentat\app"
PORT = 8836
BANNED = {"observed_original_giving", "baseline_amount", "amount_change", "pac_outgoing",
          "employee_giving", "corporate_giving", "unverified_funding", "partisan_breakdowns",
          "unresolved_reasons", "review_queue", "coverage_reasons", "changes", "summary"}

def walk(value, path=""):
    hits = []
    if isinstance(value, dict):
        for k, v in value.items():
            if k in BANNED:
                hits.append(path + "/" + k)
            hits += walk(v, path + "/" + k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            hits += walk(v, f"{path}[{i}]")
    return hits

proc = subprocess.Popen([sys.executable, "server.py", "--port", str(PORT), "--read-only"], cwd=APP,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    ready = False
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=2).read()
            ready = True
            break
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.5)
    print("server ready:", ready)
    for query in ("?industry=Banking", "?industry=Fintech", "?industry=Credit%20Union", ""):
        url = f"http://127.0.0.1:{PORT}/api/cross-reference{query}"
        try:
            with urllib.request.urlopen(url, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                status = resp.status
        except urllib.error.HTTPError as e:
            print(query or "(pointer)", "HTTP", e.code, e.read()[:200])
            continue
        report = body.get("report") or {}
        digest = report.get("digest") or {}
        print(f"\n{query or '(pointer)'} -> {status} available={body.get('available')} selected_by={body.get('selected_by')} industry={body.get('industry')} run={body.get('run_id')}")
        print("  top keys:", sorted(body.keys()))
        print("  report keys:", sorted(report.keys()))
        if digest:
            r, o = digest.get("refunds", {}), digest.get("outliers", {})
            print(f"  digest: linked {r.get('linked_count')} ({r.get('linked_amount')}), unlinked {r.get('unlinked_count')} ({r.get('unlinked_amount')}), "
                  f"non_giving {o.get('non_giving_count')} ({o.get('non_giving_amount')}), large {o.get('large_count')} ({o.get('large_amount')})")
            print("  first non_giving row:", (o.get("non_giving") or [{}])[0])
            print("  first large row:", (o.get("large") or [{}])[0])
            print("  basis:", digest.get("basis"))
        else:
            print("  digest_available:", report.get("digest_available"), report.get("digest_message"), body.get("message"))
        print("  banned keys present:", walk(body) or "none")
finally:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("\nserver stopped, returncode", proc.returncode)
