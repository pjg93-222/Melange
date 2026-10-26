"""Public relay outage monitor. One probe per call; the outage state lives in the protected state directory.

The tray notifier (Start-AccessNotifier.ps1) runs `desktop_admin.py relay-check` about every 100 s. Each call
opens TCP and TLS to the public origin the clients use (startup-registration.json `publicOrigin`) and compares
the certificate it receives with this server's tls.crt. ALERT_AFTER failures in a row raise one alert; the
first passing check after an alert raises one recovery, logs the duration and appends one CSV row."""
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import socket
import ssl
import time
from urllib.parse import urlsplit

ALERT_AFTER = 3     # about 5 minutes at the notifier's 100 s interval
TIMEOUT = 6         # connect and handshake each; the notifier kills a check after 30 s
STALE = 600         # no check for this long: the dashboard reports unknown, not up
KINDS = ('timeout', 'refused', 'wrong_cert', 'error')
STATE, LOG, OUTAGES = 'relay-monitor.json', 'relay-monitor.log', 'relay-outages.csv'


def probe(host, port, fingerprint, timeout=TIMEOUT):
    """None when host:port completes a TLS handshake with the expected certificate, else a KINDS entry."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # self-signed: the fingerprint below is the check
    try:
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with context.wrap_socket(raw, server_hostname=host) as tls:
                der = tls.getpeercert(binary_form=True)
    except TimeoutError:
        return 'timeout'
    except ConnectionRefusedError:
        return 'refused'
    except OSError:  # DNS, reset, handshake failure (ssl.SSLError is an OSError)
        return 'error'
    return None if der and hashlib.sha256(der).hexdigest() == fingerprint else 'wrong_cert'


def iso(epoch):
    return dt.datetime.fromtimestamp(epoch, dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def step(state, failure, now):
    """Pure state machine. Returns (state, event); event is None, 'alert' or 'recovered'."""
    if failure:
        state = dict(state) if state.get('failures') else {'failures': 0, 'since': now, 'kinds': []}
        state['failures'] += 1
        state['kinds'] = state['kinds'] + [failure] if failure not in state['kinds'] else state['kinds']
        state['checkedAt'] = now
        if state['failures'] >= ALERT_AFTER and not state.get('alerted'):
            state['alerted'] = True
            return state, 'alert'
        return state, None
    return {'failures': 0, 'checkedAt': now}, 'recovered' if state.get('alerted') else None


def _read(path):
    try:
        value = json.loads(Path(path).read_text(encoding='utf-8'))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(path, value):
    temporary = Path(str(path) + '.' + str(os.getpid()) + '.tmp')
    temporary.write_text(json.dumps(value), encoding='utf-8')
    os.replace(temporary, path)


def target(root):
    """(host, port, sha256 hex) from the registered public origin and this server's certificate, or None."""
    origin = _read(Path(root) / 'startup-registration.json').get('publicOrigin')
    if not isinstance(origin, str) or not origin.startswith('https://'):
        return None  # LAN mode: no public relay to watch
    parts = urlsplit(origin)
    pem = (Path(root) / 'tls.crt').read_text(encoding='ascii')
    return parts.hostname, parts.port or 443, hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest()


def check(root, now=None, prober=None):
    root = Path(root)
    where = target(root)
    if not where:
        return {'event': 'disabled', 'kind': None, 'durationS': None}
    now = int(time.time() if now is None else now)
    failure = (prober or probe)(*where)  # looked up per call so tests can patch relay_monitor.probe
    before = _read(root / STATE)
    if not _valid(before) or before.get('target') != list(where):
        before = {}  # unreadable, foreign shape or another relay/certificate: start a fresh count
    state, event = step(before, failure, now)
    state['target'] = list(where)
    relay = f'{where[0]}:{where[1]}'
    duration = None
    if event == 'alert':
        duration = now - state['since']
        _log(root, now, f"ALERT relay {relay} down since {iso(state['since'])}: {state['failures']} failed checks in a row "
                        f"over {duration} s ({'|'.join(state['kinds'])})")
    elif event == 'recovered':
        duration = now - before['since']
        joined = '|'.join(before['kinds'])
        _log(root, now, f"RECOVERED relay {relay} reachable again; outage {iso(before['since'])} to {iso(now)}, "
                        f"duration {duration} s ({joined})")
        new = not (root / OUTAGES).exists()
        with open(root / OUTAGES, 'a', newline='', encoding='utf-8') as stream:
            writer = csv.writer(stream)
            if new:
                writer.writerow(['start', 'end', 'duration_s', 'failure_kind'])
            writer.writerow([iso(before['since']), iso(now), duration, joined])
    _write(root / STATE, state)
    kinds = state.get('kinds') if event == 'alert' else before.get('kinds') if event == 'recovered' else [failure] if failure else []
    return {'event': event or 'none', 'kind': '|'.join(kinds) or None, 'durationS': duration}


def _valid(state):
    if not isinstance(state.get('failures', 0), int):
        return False
    return not state.get('failures') or (isinstance(state.get('since'), int) and isinstance(state.get('kinds'), list)
                                         and all(kind in KINDS for kind in state['kinds']))


def _log(root, now, message):
    with open(Path(root) / LOG, 'a', encoding='utf-8') as stream:
        stream.write(f'{iso(now)} {message}\n')


def status(root, now=None):
    """Dashboard field: state 'down' only while an alerted outage is open; 'unknown' when no recent check."""
    state = _read(Path(root) / STATE)
    now = time.time() if now is None else now
    checked = state.get('checkedAt')
    if not isinstance(checked, int) or now - checked > STALE:
        return {'state': 'unknown', 'since': None, 'kind': None, 'checkedAt': checked if isinstance(checked, int) else None}
    if state.get('alerted'):
        return {'state': 'down', 'since': state['since'], 'kind': '|'.join(state['kinds']), 'checkedAt': checked}
    return {'state': 'up', 'since': None, 'kind': None, 'checkedAt': checked}
