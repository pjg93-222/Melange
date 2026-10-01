"""Throwaway ops driver: run Antigravity CLI (agy) sign-in inside a ConPTY.

Runtime files are stored in ``<system temp>/agy_login``. Coordinators must
write agy_send.tmp and then use os.replace to rename it to agy_send.txt
(atomic on the same volume).

Captures output to a log, auto-captures the Google auth URL, and exposes a
send-channel: whatever appears in agy_send.txt is written to the PTY (with
Enter) and the file is deleted. No credentials are ever handled here — the
human completes the browser sign-in.
"""
import argparse
import ctypes
import os
import re
import sys
import tempfile
import time
import threading

from winpty import PtyProcess

SCRATCH = os.path.dirname(os.path.abspath(__file__))
RUNDIR = os.path.join(tempfile.gettempdir(), "agy_login")
os.makedirs(RUNDIR, exist_ok=True)

LOG = os.path.join(RUNDIR, "agy_pty.log")
URL_FILE = os.path.join(RUNDIR, "agy_auth_url.txt")
URL_TMP = os.path.join(RUNDIR, "agy_auth_url.tmp")
STATUS = os.path.join(RUNDIR, "agy_pty_status.txt")
SEND = os.path.join(RUNDIR, "agy_send.txt")
STOP = os.path.join(RUNDIR, "agy_stop.txt")
LOCK = os.path.join(RUNDIR, "agy_pty.lock")

ANSI = re.compile(
    r"\x1b\[[0-9;?]*[A-Za-z]"
    r"|\x1b\](?:[^\x07\x1b]|\x1b(?!\\))*(?:\x07|\x1b\\)"
    r"|\x1b[=>]"
)

def note(msg):
    try:
        with open(STATUS, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")
    except Exception as exc:
        print(f"status note failed ({msg!r}): {exc}", file=sys.stderr)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
URL = re.compile(
    r"https://accounts\.google\.com"
    r"[A-Za-z0-9%._~:/?#\[\]@!$&'()*+,;=\-]*"
)
URL_FRAGMENT = re.compile(
    r"^[A-Za-z0-9%._~:/?#\[\]@!$&'()*+,;=\-]+$"
)


def extract_latest_auth_url(text):
    marker = "https://accounts.google.com"
    cleaned = ANSI.sub("", text)
    cleaned = re.sub(r"[\u2500-\u257F]+", "", cleaned)
    lines = [line.strip() for line in cleaned.splitlines()]
    latest = None

    for index, line in enumerate(lines):
        marker_index = line.find(marker)
        if marker_index < 0:
            continue
        candidate = line[marker_index:]
        next_index = index + 1
        while (
            next_index < len(lines)
            and lines[next_index]
            and URL_FRAGMENT.fullmatch(lines[next_index])
            and (
                len(lines[next_index]) >= 40
                or any(char in lines[next_index] for char in "%&=?/")
            )
        ):
            candidate += lines[next_index]
            next_index += 1
        match = URL.match(candidate)
        if match:
            latest = match.group(0)

    return latest


def pid_is_alive(pid):
    if pid <= 0:
        return False
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.argtypes = [
        ctypes.c_uint32,
        ctypes.c_int,
        ctypes.c_uint32,
    ]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    handle = kernel32.OpenProcess(
        PROCESS_QUERY_LIMITED_INFORMATION, False, pid
    )
    if not handle:
        return False
    try:
        return True
    finally:
        kernel32.CloseHandle(handle)


def acquire_lock():
    pid = os.getpid()
    try:
        with open(LOCK, "x", encoding="utf-8") as f:
            f.write(str(pid))
        return True
    except FileExistsError:
        try:
            with open(LOCK, encoding="utf-8") as f:
                lock_contents = f.read().strip()
        except (OSError, UnicodeError) as exc:
            note(f"refusing to start: lock file unreadable: {exc}")
            return False
        if not lock_contents:
            note("refusing to start: lock file is empty")
            return False
        try:
            existing_pid = int(lock_contents)
        except ValueError:
            note("refusing to start: lock file contains an invalid PID")
            return False
        if existing_pid <= 0:
            note("refusing to start: lock file contains an invalid PID")
            return False
        if pid_is_alive(existing_pid):
            note(f"refusing to start: active instance pid={existing_pid}")
            return False
        with open(LOCK, "w", encoding="utf-8") as f:
            f.write(str(pid))
        return True


def write_run_headers():
    header = (
        f"=== run start pid={os.getpid()} "
        f"{time.strftime('%Y-%m-%d %H:%M:%S')} ===\n"
    )
    for path in (STATUS, LOG):
        with open(path, "a", encoding="utf-8") as f:
            f.write(header)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--deadline-seconds", type=int, default=1200)
    args = parser.parse_args()

    if not acquire_lock():
        return 1

    proc = None
    reader_thread = None
    try:
        for path in (SEND, STOP, URL_FILE):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
            except OSError as exc:
                note(
                    "startup cleanup: could not remove "
                    f"{os.path.basename(path)}: {exc}"
                )
        write_run_headers()

        env = dict(os.environ)
        env["PATH"] = (
            r"C:\Users\pgoff\AppData\Local\agy\bin;" + env.get("PATH", "")
        )

        cmd = [r"C:\Users\pgoff\AppData\Local\agy\bin\agy.exe"]
        note("spawning agy interactive")
        proc = PtyProcess.spawn(cmd, dimensions=(40, 140), env=env, cwd=SCRATCH)

        buf_lock = threading.Lock()
        buf = []

        def reader():
            log_write_failed = False
            while True:
                try:
                    chunk = proc.read(4096)
                except EOFError:
                    note("reader: EOF")
                    break
                except Exception as exc:
                    note(f"reader: {type(exc).__name__}: {exc}")
                    break
                if chunk:
                    with buf_lock:
                        buf.append(chunk)
                    if not log_write_failed:
                        try:
                            with open(
                                LOG, "a", encoding="utf-8", errors="replace"
                            ) as f:
                                f.write(chunk)
                        except Exception as exc:
                            note(
                                "reader: log write failed: "
                                f"{exc}; draining without log"
                            )
                            log_write_failed = True

        reader_thread = threading.Thread(target=reader, daemon=True)
        reader_thread.start()

        last_written_url = None
        url_updates = 0
        deadline = time.time() + args.deadline_seconds
        while time.time() < deadline:
            time.sleep(1.0)
            if os.path.exists(STOP):
                note("stop requested")
                break
            if os.path.exists(SEND):
                try:
                    with open(SEND, encoding="utf-8") as f:
                        payload = f.read().rstrip("\n")
                    os.remove(SEND)
                    proc.write(payload + "\r")
                    note(f"sent payload ({len(payload)} chars)")
                except Exception as exc:
                    note(f"send failed: {exc}")
            with buf_lock:
                text = ANSI.sub("", "".join(buf))
                if len(text) > 512_000:
                    buf[:] = [text[-256_000:]]
            latest_url = extract_latest_auth_url(text)
            if latest_url is not None and latest_url != last_written_url:
                last_written_url = latest_url
                with open(URL_TMP, "w", encoding="utf-8") as f:
                    f.write(last_written_url)
                os.replace(URL_TMP, URL_FILE)
                url_updates += 1
                note(f"AUTH URL UPDATED (#{url_updates})")
            low = text[-4000:].lower()
            if any(k in low for k in (
                "signed in as",
                "successfully signed in",
                "login successful",
                "authentication successful",
            )):
                note("SIGN-IN SUCCESS MARKER SEEN")
                time.sleep(3)
                break
            if not proc.isalive():
                note("process exited")
                break
        else:
            note(f"deadline expired after {args.deadline_seconds}s")
    finally:
        note("driver ending")
        try:
            try:
                if proc is not None:
                    proc.terminate()
            except Exception as exc:
                note(f"terminate failed: {exc}")
            if reader_thread is not None:
                reader_thread.join(timeout=10)
                if reader_thread.is_alive():
                    note("reader thread did not exit within 10s")
        finally:
            try:
                os.remove(LOCK)
            except FileNotFoundError:
                pass
            except Exception as exc:
                note(f"lock removal failed: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
