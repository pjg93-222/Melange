import contextlib
import csv
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

import desktop_admin
import relay_monitor
from relay_monitor import check, probe, status


def certificate(directory, name):
    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - dt.timedelta(days=1))
            .not_valid_after(now + dt.timedelta(days=1)).sign(key, hashes.SHA256()))
    cert_path, key_path = Path(directory) / (name + '.crt'), Path(directory) / (name + '.key')
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))
    return cert_path, key_path, hashlib.sha256(cert.public_bytes(serialization.Encoding.DER)).hexdigest()


@contextlib.contextmanager
def tls_server(cert_path, key_path):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_path, key_path)
    listener = socket.create_server(('127.0.0.1', 0))
    stop = threading.Event()

    def serve():
        listener.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = listener.accept()
            except OSError:
                continue
            try:
                with context.wrap_socket(conn, server_side=True):
                    pass
            except OSError:
                conn.close()
    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1]
    finally:
        stop.set(); thread.join(2); listener.close()


class Sequence:
    """A fake probe that returns the scripted results in order."""
    def __init__(self, results):
        self.results = list(results)

    def __call__(self, host, port, fingerprint):
        return self.results.pop(0)


class RelayMonitorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cert, self.key, self.fingerprint = certificate(self.root, 'server')
        shutil.copy(self.cert, self.root / 'tls.crt')
        (self.root / 'startup-registration.json').write_text(json.dumps({'publicOrigin': 'https://bore.pub:38443'}))

    def run_sequence(self, results, start=1_800_000_000, interval=100):
        fake = Sequence(results)
        return [check(self.root, start + i * interval, fake) for i in range(len(results))]

    def outages(self):
        path = self.root / 'relay-outages.csv'
        return list(csv.reader(path.open(newline=''))) if path.exists() else None

    def test_target_is_registered_origin_and_tls_crt_fingerprint(self):
        self.assertEqual(relay_monitor.target(self.root), ('bore.pub', 38443, self.fingerprint))

    def test_down_up_sequence_gives_exactly_one_alert_and_one_recovery(self):
        results = self.run_sequence(['refused'] * 6 + [None] * 3)
        events = [r['event'] for r in results]
        self.assertEqual(events, ['none', 'none', 'alert', 'none', 'none', 'none', 'recovered', 'none', 'none'])
        self.assertEqual(results[2], {'event': 'alert', 'kind': 'refused', 'durationS': 200})
        self.assertEqual(results[6], {'event': 'recovered', 'kind': 'refused', 'durationS': 600})
        self.assertEqual(self.outages(), [['start', 'end', 'duration_s', 'failure_kind'],
                                          ['2027-01-15T08:00:00Z', '2027-01-15T08:10:00Z', '600', 'refused']])
        log = (self.root / 'relay-monitor.log').read_text().splitlines()
        self.assertEqual(len(log), 2)
        self.assertTrue(log[0].startswith('2027-01-15T08:03:20Z ALERT relay bore.pub:38443 down since 2027-01-15T08:00:00Z'))
        self.assertTrue(log[1].startswith('2027-01-15T08:10:00Z RECOVERED relay bore.pub:38443'))
        self.assertIn('duration 600 s', log[1])

    def test_one_or_two_transient_failures_never_alert(self):
        results = self.run_sequence(['timeout', None, 'refused', 'error', None, None])
        self.assertEqual({r['event'] for r in results}, {'none'})
        self.assertIsNone(self.outages())
        self.assertFalse((self.root / 'relay-monitor.log').exists())
        self.assertEqual(status(self.root, 1_800_000_500)['state'], 'up')

    def test_two_outages_append_two_rows_with_mixed_kinds(self):
        self.run_sequence(['timeout', 'refused', 'refused', None, 'wrong_cert'] + ['wrong_cert'] * 2 + [None])
        rows = self.outages()
        self.assertEqual([row[2:] for row in rows[1:]], [['300', 'timeout|refused'], ['300', 'wrong_cert']])

    def test_dashboard_status_down_then_up_then_stale_unknown(self):
        start = 1_800_000_000
        self.run_sequence(['refused'] * 3)
        self.assertEqual(status(self.root, start + 250), {'state': 'down', 'since': start, 'kind': 'refused', 'checkedAt': start + 200})
        check(self.root, start + 300, Sequence([None]))
        self.assertEqual(status(self.root, start + 350)['state'], 'up')
        self.assertEqual(status(self.root, start + 300 + relay_monitor.STALE + 1)['state'], 'unknown')

    def test_corrupt_state_starts_a_fresh_count(self):
        (self.root / 'relay-monitor.json').write_text('{"failures": "x"}')
        self.assertEqual(check(self.root, 1_800_000_000, Sequence(['refused']))['event'], 'none')
        self.assertEqual(json.loads((self.root / 'relay-monitor.json').read_text())['failures'], 1)

    def test_changed_target_starts_a_fresh_count(self):
        self.run_sequence(['refused'] * 3)  # alerted outage on bore.pub:38443
        (self.root / 'startup-registration.json').write_text(json.dumps({'publicOrigin': 'https://relay.example:443'}))
        result = check(self.root, 1_800_000_300, Sequence([None]))
        self.assertEqual(result['event'], 'none')  # no false recovery for the old relay
        self.assertIsNone(self.outages())
        self.assertEqual(check(self.root, 1_800_000_400, Sequence(['refused']))['event'], 'none')

    def test_alerted_state_without_outage_fields_is_rejected(self):
        target = list(relay_monitor.target(self.root))
        (self.root / 'relay-monitor.json').write_text(json.dumps({'failures': 0, 'alerted': True, 'checkedAt': 1_800_000_000, 'target': target}))
        self.assertEqual(status(self.root, 1_800_000_010)['state'], 'unknown')
        self.assertEqual(check(self.root, 1_800_000_100, Sequence([None]))['event'], 'none')  # no KeyError, no false recovery

    def test_lan_mode_is_disabled_and_writes_nothing(self):
        (self.root / 'startup-registration.json').unlink()
        self.assertEqual(check(self.root, 1, Sequence([])), {'event': 'disabled', 'kind': None, 'durationS': None})
        self.assertFalse((self.root / 'relay-monitor.json').exists())

    def test_probe_matching_certificate_passes(self):
        with tls_server(self.cert, self.key) as port:
            self.assertIsNone(probe('127.0.0.1', port, self.fingerprint, timeout=3))

    def test_wrong_certificate_is_a_failure_and_alerts(self):
        # Another bore client holding the port answers TLS with its own certificate.
        other_cert, other_key, _ = certificate(self.root, 'squatter')
        with tls_server(other_cert, other_key) as port:
            real = lambda host, _port, fingerprint: probe('127.0.0.1', port, fingerprint, timeout=3)
            results = [check(self.root, 1_800_000_000 + i * 100, real) for i in range(3)]
        self.assertEqual([r['event'] for r in results], ['none', 'none', 'alert'])
        self.assertEqual(results[2]['kind'], 'wrong_cert')

    def test_probe_refused_on_closed_port(self):
        with socket.create_server(('127.0.0.1', 0)) as spare:
            port = spare.getsockname()[1]
        self.assertEqual(probe('127.0.0.1', port, self.fingerprint, timeout=3), 'refused')

    def test_probe_timeout_when_handshake_never_answers(self):
        with socket.create_server(('127.0.0.1', 0)) as silent:  # accepts TCP in the backlog, never speaks TLS
            self.assertEqual(probe('127.0.0.1', silent.getsockname()[1], self.fingerprint, timeout=0.5), 'timeout')

    def test_cli_prints_one_json_result(self):
        out = io.StringIO()
        with patch('relay_monitor.probe', Sequence(['refused'])), contextlib.redirect_stdout(out):
            desktop_admin.main(['--state', str(self.root), 'relay-check'])
        self.assertEqual(json.loads(out.getvalue()), {'event': 'none', 'kind': 'refused', 'durationS': None})


@unittest.skipUnless(os.name == 'nt' and shutil.which('pwsh'), 'Windows PowerShell 7 notifier')
class NotifierRelayNoticeTests(unittest.TestCase):
    """Runs only Get-RelayNotice from Start-AccessNotifier.ps1; never starts the tray."""
    def notice(self, output):
        command = ("$ErrorActionPreference='Stop';Add-Type -AssemblyName System.Windows.Forms;"
                   "$ast=[Management.Automation.Language.Parser]::ParseFile($env:FIXTURE_SCRIPT,[ref]$null,[ref]$null);"
                   "foreach($f in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)){"
                   "if($f.Name -eq 'Get-RelayNotice'){Invoke-Expression $f.Extent.Text}};"
                   "$n=Get-RelayNotice $env:FIXTURE_OUTPUT; if($n){@{title=$n[0];text=$n[1];icon=[string]$n[2]}|ConvertTo-Json -Compress}else{'null'}")
        env = dict(os.environ, FIXTURE_SCRIPT=str(Path(__file__).with_name('Start-AccessNotifier.ps1')), FIXTURE_OUTPUT=output)
        done = subprocess.run([shutil.which('pwsh'), '-NoProfile', '-NonInteractive', '-Command', command],
                              env=env, check=True, capture_output=True, text=True, timeout=60)
        return json.loads(done.stdout)

    def test_alert_recovery_and_quiet_results(self):
        alert = self.notice('{"event": "alert", "kind": "refused|timeout", "durationS": 200}')
        self.assertEqual((alert['title'], alert['icon']), ('Public access relay down', 'Warning'))
        self.assertIn('(refused|timeout) for about 3 min', alert['text'])
        recovered = self.notice('{"event": "recovered", "kind": "refused", "durationS": 600}')
        self.assertEqual(recovered['title'], 'Public access relay restored')
        self.assertIn('about 10 min (600 s)', recovered['text'])
        for quiet in ('{"event": "none", "kind": "refused", "durationS": null}',
                      '{"event": "disabled", "kind": null, "durationS": null}',
                      '{"event": "alert", "kind": "<script>", "durationS": 200}',
                      '{"event": "alert", "kind": "refused", "durationS": 200, "extra": 1}'):
            self.assertIsNone(self.notice(quiet), quiet)


if __name__ == '__main__':
    unittest.main()
