"""Bounded policy and owned-process tests; never start the real publisher/tray."""
import copy
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import uuid

import windows_admin_supervisor as supervisor
from desktop_admin import Refused


def config(root):
    python = Path(sys.executable).resolve()
    return supervisor.Config(Path(root), python, python.with_name('pythonw.exe'), '192.168.45.83', 'Fixture LAN', 38443)


def approved(config):
    return {
        'addresses': [{'ip': config.listen, 'index': 9, 'state': 'Preferred'}],
        'profiles': [{'name': config.network, 'category': 'Private', 'index': 9, 'alias': 'Wi-Fi'}],
        'rules': [{'enabled': 'True', 'direction': 'Inbound', 'action': 'Allow', 'profile': 'Private'}],
        'addressesFilter': [{'local': [config.listen], 'remote': ['LocalSubnet']}],
        'ports': [{'protocol': 'TCP', 'local': [str(config.port)]}],
        'applications': [{'program': str(config.python)}],
        'interfaces': [{'aliases': ['Wi-Fi']}],
    }


class Child:
    def __init__(self, command):
        self.command, self.pid, self.exited, self.closed = command, 1234, False, False
    def poll(self): return 2 if self.exited else None
    def close(self): self.closed = True


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = config(self.temp.name)

    def test_policy_requires_exact_assigned_private_expected_lan_and_firewall(self):
        good = approved(self.config)
        self.assertTrue(supervisor.network_permitted(self.config, good))
        changes = [
            ('addresses', 'ip', '192.168.45.84'), ('addresses', 'state', 'Tentative'),
            ('addresses', 'index', 8), ('profiles', 'name', 'Fixture lan'),
            ('profiles', 'category', 'Public'), ('profiles', 'category', 'DomainAuthenticated'),
            ('rules', 'enabled', 'False'), ('rules', 'direction', 'Outbound'),
            ('rules', 'action', 'Block'), ('rules', 'profile', 'Any'),
            ('addressesFilter', 'local', ['Any']), ('addressesFilter', 'remote', ['Any']),
            ('ports', 'protocol', 'UDP'), ('ports', 'local', ['Any']),
            ('applications', 'program', 'Any'), ('interfaces', 'aliases', ['Any']),
        ]
        for key, field, value in changes:
            with self.subTest(key=key, field=field):
                altered = copy.deepcopy(good); altered[key][0][field] = value
                self.assertFalse(supervisor.network_permitted(self.config, altered))
        for key in good:
            with self.subTest(ambiguous=key):
                altered = copy.deepcopy(good); altered[key].append(copy.deepcopy(altered[key][0]))
                self.assertFalse(supervisor.network_permitted(self.config, altered))
                altered[key] = []
                self.assertFalse(supervisor.network_permitted(self.config, altered))
        self.assertFalse(supervisor.network_permitted(self.config, None))

    def test_lan_loss_stops_only_owned_publisher_and_retains_notifier(self):
        children = []
        def spawn(command):
            child = Child(command); children.append(child); return child
        ready = [False]
        service = supervisor.Supervisor(self.config, check=lambda _: ready[0], spawn=spawn, protect=lambda _: None)
        self.addCleanup(service.close)
        service.tick()
        self.assertEqual(len(children), 1)
        notifier = service.notifier
        self.assertEqual(Path(notifier.command[3]).name, 'windows_admin_notifier.py')
        self.assertEqual(notifier.command[1:3], ['-E', '-s'])
        self.assertIsNone(service.publisher)
        ready[0] = True; service.tick()
        publisher = service.publisher
        self.assertEqual(Path(publisher.command[3]).name, 'desktop_admin.py')
        self.assertIn('serve', publisher.command)
        service.tick(); self.assertEqual(len(children), 2)
        ready[0] = False; service.tick()
        self.assertTrue(publisher.closed)
        self.assertIsNone(service.publisher)
        self.assertIs(service.notifier, notifier)
        self.assertFalse(notifier.closed)
        status = json.loads((self.config.state/'listener-status.json').read_text())
        self.assertEqual(status['status'], 'waiting-for-approved-lan')
        self.assertEqual(set(status), {'schemaVersion', 'status', 'checkedAt', 'supervisorPid', 'publisherPid', 'notifierPid', 'inviteRequired'})
        ready[0] = True; service.tick()
        self.assertEqual(len(children), 3)

    def test_status_reports_invite_enforcement_from_the_environment_the_publisher_inherits(self):
        service = supervisor.Supervisor(self.config, check=lambda _: True, spawn=Child, protect=lambda _: None)
        self.addCleanup(service.close)
        for raw, expected in (('', False), ('0', False), ('1', True), (' TRUE ', True), ('on', True), ('enabled', None)):
            with self.subTest(raw=raw), patch.dict(os.environ, {'MELANGE_ACCESS_REQUIRE_INVITE': raw}):
                service.tick()
                self.assertIs(json.loads((self.config.state/'listener-status.json').read_text())['inviteRequired'], expected)
        with patch.dict(os.environ):
            os.environ.pop('MELANGE_ACCESS_REQUIRE_INVITE', None)
            service.tick()
            self.assertIs(json.loads((self.config.state/'listener-status.json').read_text())['inviteRequired'], False)

    def test_exited_children_restart_once_per_tick_and_policy_errors_fail_closed(self):
        children = []
        def spawn(command):
            child = Child(command); children.append(child); return child
        service = supervisor.Supervisor(self.config, check=lambda _: True, spawn=spawn, protect=lambda _: None)
        self.addCleanup(service.close)
        service.tick(); old_notifier, old_publisher = children
        old_notifier.exited = old_publisher.exited = True
        service.tick()
        self.assertTrue(old_notifier.closed and old_publisher.closed)
        self.assertEqual(len(children), 4)
        service.check = lambda _: (_ for _ in ()).throw(TimeoutError())
        service.tick()
        self.assertTrue(children[3].closed)
        self.assertFalse(children[2].closed)
        self.assertEqual(len(children), 4)

    def test_notifier_failure_does_not_block_listener_but_invalid_state_stops_loop(self):
        def spawn(command):
            if Path(command[3]).name == 'windows_admin_notifier.py': raise OSError('fixture')
            return Child(command)
        service = supervisor.Supervisor(self.config, check=lambda _: True, spawn=spawn, protect=lambda _: None)
        self.addCleanup(service.close)
        service.tick(); self.assertIsNotNone(service.publisher); self.assertIsNone(service.notifier)
        service.tick()
        self.assertEqual(json.loads((self.config.state/'listener-status.json').read_text())['status'], 'running-notifier-deferred')
        service.protect = lambda _: (_ for _ in ()).throw(Refused('fixture'))
        with self.assertRaises(Refused): service.tick()

    def test_network_query_is_fixed_read_only_no_script_or_policy_override(self):
        good = approved(self.config)
        result = subprocess.CompletedProcess([], 0, json.dumps(good).encode(), b'')
        with patch.object(supervisor.subprocess, 'run', return_value=result) as run:
            self.assertTrue(supervisor.query_network(self.config))
        arguments = run.call_args.args[0]
        self.assertEqual(arguments[-1], supervisor.NETWORK_QUERY)
        self.assertNotIn('-File', arguments)
        self.assertNotIn('-EncodedCommand', arguments)
        self.assertNotIn('-ExecutionPolicy', arguments)
        self.assertEqual(run.call_args.kwargs['timeout'], 20)
        self.assertEqual(json.loads(run.call_args.kwargs['input']), {'ip': self.config.listen, 'port': self.config.port})
        for forbidden in ('Set-Net', 'New-Net', 'Remove-Net', 'Start-Process', 'Invoke-Expression'):
            self.assertNotIn(forbidden, supervisor.NETWORK_QUERY)

    def test_input_validation_no_public_loopback_wildcard_or_missing_python(self):
        for address in ('0.0.0.0', '127.0.0.1', '8.8.8.8', '::1', '192.168.1.001'):
            with self.subTest(address=address), self.assertRaises(Refused):
                supervisor.validate_inputs(self.temp.name, self.config.python, address, 'Fixture', 38443)
        with patch.object(supervisor, 'assert_protected_state', return_value=self.config.state):
            (self.config.state/'trust.json').write_text('{}')
            valid = supervisor.validate_inputs(self.temp.name, self.config.python, self.config.listen, 'Fixture', 38443)
            self.assertEqual(valid.python, self.config.python)


@unittest.skipUnless(os.name == 'nt', 'native Windows ownership proof')
class NativeJobTests(unittest.TestCase):
    def test_duplicate_mutex_other_process_refuses_and_releases_after_owner_exit(self):
        sid = 'fixture-' + uuid.uuid4().hex
        source = ("import time,windows_admin_supervisor as m; m.windows_sid=lambda:" + repr(sid) +
                  "; x=m.SupervisorMutex(); print(x.acquired,flush=True); time.sleep(20)")
        child = subprocess.Popen([sys.executable, '-E', '-s', '-c', source], cwd=Path(supervisor.__file__).parent,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                 creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'True')
            with patch.object(supervisor, 'windows_sid', return_value=sid):
                second = supervisor.SupervisorMutex()
                try: self.assertFalse(second.acquired)
                finally: second.close()
            child.terminate(); child.wait(timeout=5)
            with patch.object(supervisor, 'windows_sid', return_value=sid):
                recovered = supervisor.SupervisorMutex()
                try: self.assertTrue(recovered.acquired)
                finally: recovered.close()
        finally:
            if child.poll() is None: child.terminate(); child.wait(timeout=5)
            child.stdout.close(); child.stderr.close()

    def test_owned_job_closes_its_parent_and_descendant_only(self):
        with tempfile.TemporaryDirectory() as directory:
            pid_file = Path(directory)/'descendant.pid'
            inner = 'import time; time.sleep(60)'
            outer = ('import pathlib,subprocess,sys,time; p=subprocess.Popen([sys.executable,"-c",' + repr(inner) +
                     '],creationflags=subprocess.CREATE_NO_WINDOW); pathlib.Path(' + repr(str(pid_file)) +
                     ').write_text(str(p.pid)); time.sleep(60)')
            child = supervisor.OwnedChild([sys.executable, '-E', '-s', '-c', outer])
            other = supervisor.OwnedChild([sys.executable, '-E', '-s', '-c', inner])
            kernel = C.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]; kernel.OpenProcess.restype = W.HANDLE
            kernel.WaitForSingleObject.argtypes = [W.HANDLE, W.DWORD]; kernel.WaitForSingleObject.restype = W.DWORD
            kernel.CloseHandle.argtypes = [W.HANDLE]
            descendant = None
            try:
                deadline = time.monotonic()+10
                while not pid_file.exists() and time.monotonic()<deadline: time.sleep(.05)
                self.assertTrue(pid_file.exists())
                descendant = kernel.OpenProcess(0x100000, False, int(pid_file.read_text()))
                self.assertTrue(descendant)
                self.assertIsNone(child.poll()); self.assertIsNone(other.poll())
                child.close()
                self.assertEqual(kernel.WaitForSingleObject(descendant, 5000), 0)
                self.assertIsNone(other.poll())
            finally:
                child.close(); other.close()
                if descendant: kernel.CloseHandle(descendant)


@unittest.skipUnless(shutil.which('pwsh'), 'PowerShell 7 unavailable')
class LoginSupervisorStatusTests(unittest.TestCase):
    def test_login_supervisor_status_names_its_notifier(self):
        # Runs only Write-ListenerStatus from the login script, never its supervision loop.
        with tempfile.TemporaryDirectory() as root:
            status = Path(root) / 'listener-status.json'
            command = (
                "$ast=[Management.Automation.Language.Parser]::ParseFile($env:FIXTURE_SCRIPT,[ref]$null,[ref]$null);"
                "foreach($f in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)){"
                "if($f.Name -in 'Get-InviteRequired','Write-ListenerStatus'){Invoke-Expression $f.Extent.Text}}; $statusFile=$env:FIXTURE_STATUS; $publisherProcess=$null;"
                "$notifierProcess=[pscustomobject]@{Id=4321}; Write-ListenerStatus 'running'")
            env = dict(os.environ, FIXTURE_SCRIPT=str(Path(__file__).with_name('Start-LanPublisherAtLogin.ps1')),
                       FIXTURE_STATUS=str(status))
            subprocess.run([shutil.which('pwsh'), '-NoProfile', '-NonInteractive', '-Command', command],
                           env=env, check=True, capture_output=True, timeout=60)
            record = json.loads(status.read_text())
        self.assertEqual((record['status'], record['publisherPid'], record['notifierPid']), ('running', None, 4321))

    def test_login_supervisor_survives_failed_notifier_launch(self):
        # Runs only the notifier launcher with an executable that cannot start; never starts the real tray.
        with tempfile.TemporaryDirectory() as root:
            status = Path(root) / 'listener-status.json'
            command = (
                "$ErrorActionPreference='Stop';"
                "$ast=[Management.Automation.Language.Parser]::ParseFile($env:FIXTURE_SCRIPT,[ref]$null,[ref]$null);"
                "foreach($f in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)){"
                "if($f.Name -in 'Start-AccessNotifierProcess','Start-LoggedChild','Write-SupervisorLog','Get-InviteRequired','Write-ListenerStatus'){Invoke-Expression $f.Extent.Text}};"
                "$statusFile=$env:FIXTURE_STATUS; $publisherProcess=[pscustomobject]@{Id=8765}; $publisherJob=$null;"
                "$notifierScript='Start-AccessNotifier.ps1'; $PythonExecutable='python.exe'; $stateDirectory=$env:FIXTURE_ROOT;"
                "$notifierProcess=Start-AccessNotifierProcess (Join-Path $env:FIXTURE_ROOT 'missing.exe');"
                "Write-ListenerStatus 'running'")
            env = dict(os.environ, FIXTURE_SCRIPT=str(Path(__file__).with_name('Start-LanPublisherAtLogin.ps1')),
                       FIXTURE_STATUS=str(status), FIXTURE_ROOT=root)
            subprocess.run([shutil.which('pwsh'), '-NoProfile', '-NonInteractive', '-Command', command],
                           env=env, check=True, capture_output=True, timeout=60)
            record = json.loads(status.read_text())
        self.assertEqual((record['status'], record['publisherPid'], record['notifierPid']), ('running', 8765, None))


    def run_pwsh(self, command, **env):
        result = subprocess.run([shutil.which('pwsh'), '-NoProfile', '-NonInteractive', '-Command', command],
                                env=dict(os.environ, **env), capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    @unittest.skipUnless(os.name == 'nt', 'Windows identity, mutex and job APIs')
    def test_login_supervisor_logs_start_terminating_error_and_exit(self):
        # Uninitialized state stops the script before its mutex, job or children: nothing real starts.
        with tempfile.TemporaryDirectory() as root:
            result = subprocess.run([shutil.which('pwsh'), '-NoProfile', '-NonInteractive', '-File', str(SUPERVISOR_SCRIPT),
                                     '-PublicOrigin', 'https://updates.example.com', '-PythonExecutable', sys.executable, '-StateDirectory', root],
                                    capture_output=True, text=True, timeout=120)
            log = (Path(root) / 'supervisor.log').read_text()
        self.assertEqual(result.returncode, 1)
        lines = log.splitlines()
        self.assertIn('start: pwsh', lines[0])
        self.assertIn('-PublicOrigin https://updates.example.com', lines[0])
        self.assertIn('terminating error: Initialize the protected publisher state', log)
        self.assertIn('exiting with code 1', lines[-2])
        self.assertIn('process exiting with code 1', lines[-1])

    @unittest.skipUnless(os.name == 'nt', 'Windows job objects')
    def test_login_supervisor_logs_child_output_masked_and_exit_code(self):
        # Runs the logging, child-start and exit-check functions with a Python child that crashes; never the loop.
        secret = 'Zq3' + 'x' * 40
        child = ("import os,sys; print('Authenticated update service: https://updates.example.com; invite codes not required', flush=True);"
                 "s=os.environ['FIXTURE_SECRET']; sys.stderr.write('Refused: bearer ' + s + ' token=' + s[:8] + ' ' + s + chr(10)); sys.exit(7)")
        command = (
            "$ErrorActionPreference='Stop';"
            "$ast=[Management.Automation.Language.Parser]::ParseFile($env:FIXTURE_SCRIPT,[ref]$null,[ref]$null);"
            "Invoke-Expression $ast.Find({param($n) $n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$logSource'},$true).Extent.Text;"
            "Add-Type -TypeDefinition $logSource;"
            "Invoke-Expression $ast.Find({param($n) $n -is [Management.Automation.Language.CommandAst] -and $n.GetCommandName() -eq 'Add-Type' -and $n.Extent.Text -match 'MelangePublisherJob'},$true).Extent.Text;"
            "foreach($f in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)){"
            "if($f.Name -in 'Write-SupervisorLog','Start-LoggedChild','Test-ChildExited'){Invoke-Expression $f.Extent.Text}};"
            "$stateDirectory=$env:FIXTURE_ROOT; $supervisorLog=Join-Path $stateDirectory 'supervisor.log'; $publisherJob=[MelangePublisherJob]::Create();"
            "$pumps=[Collections.Generic.List[Threading.Thread]]::new();"
            "$p=Start-LoggedChild 'publisher' $env:FIXTURE_PYTHON @('-c',$env:FIXTURE_CHILD); $id=$p.Id; $deadline=(Get-Date).AddSeconds(30);"
            "while(-not (Test-ChildExited 'publisher' $p)){ if((Get-Date) -gt $deadline){throw 'child did not exit'}; Start-Sleep -Milliseconds 100 };"
            "$joined=@($pumps | ForEach-Object { $_.Join(10000) }); $publisherJob.Dispose(); @{pid=$id; joined=$joined} | ConvertTo-Json")
        with tempfile.TemporaryDirectory() as root:
            out = self.run_pwsh(command, FIXTURE_SCRIPT=str(SUPERVISOR_SCRIPT), FIXTURE_ROOT=root, FIXTURE_PYTHON=sys.executable,
                                FIXTURE_CHILD=child, FIXTURE_SECRET=secret)
            supervisor_log = (Path(root) / 'supervisor.log').read_text()
            stdout_log = (Path(root) / 'publisher.log').read_text()
            stderr_log = (Path(root) / 'publisher.err').read_text()
        self.assertIn(f"started publisher pid {out['pid']}: {sys.executable} -c", supervisor_log)
        self.assertEqual(out['joined'], [True, True])
        self.assertIn(f"publisher pid {out['pid']} exited with code 7", supervisor_log)
        self.assertIn('Authenticated update service: https://updates.example.com; invite codes not required', stdout_log)
        self.assertNotIn(secret, stderr_log)
        self.assertNotIn(secret[:8], stderr_log)
        self.assertIn('Refused: bearer [masked] token=[masked] [masked]', stderr_log)


    @unittest.skipUnless(os.name == 'nt', 'Windows file-sharing semantics')
    def test_login_supervisor_survives_a_reader_holding_the_status_file(self):
        # A reader without delete sharing makes the atomic replace fail; before, that error ended the supervisor.
        command = (
            "$ErrorActionPreference='Stop';"
            "$ast=[Management.Automation.Language.Parser]::ParseFile($env:FIXTURE_SCRIPT,[ref]$null,[ref]$null);"
            "Invoke-Expression $ast.Find({param($n) $n -is [Management.Automation.Language.AssignmentStatementAst] -and $n.Left.Extent.Text -eq '$logSource'},$true).Extent.Text;"
            "Add-Type -TypeDefinition $logSource;"
            "foreach($f in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)){"
            "if($f.Name -in 'Write-SupervisorLog','Get-InviteRequired','Write-ListenerStatus'){Invoke-Expression $f.Extent.Text}};"
            "$supervisorLog=Join-Path $env:FIXTURE_ROOT 'supervisor.log'; $statusFile=Join-Path $env:FIXTURE_ROOT 'listener-status.json';"
            "$publisherProcess=$null; $notifierProcess=$null; Write-ListenerStatus 'running';"
            "@{temporaryLeft=@(Get-ChildItem -LiteralPath $env:FIXTURE_ROOT -Filter '*.tmp').Count} | ConvertTo-Json")
        with tempfile.TemporaryDirectory() as root:
            status = Path(root) / 'listener-status.json'
            status.write_text('{"status": "previous"}')
            with open(status) as reader:
                out = self.run_pwsh(command, FIXTURE_SCRIPT=str(SUPERVISOR_SCRIPT), FIXTURE_ROOT=root)
                self.assertEqual(json.loads(reader.read())['status'], 'previous')
            log = (Path(root) / 'supervisor.log').read_text()
        self.assertEqual(out['temporaryLeft'], 0)
        self.assertIn('status write failed:', log)

@unittest.skipUnless(os.name == 'nt' and shutil.which('pwsh'), 'Windows Task Scheduler and PowerShell 7')
class StartupRegistrationTests(unittest.TestCase):
    # Builds the task in memory only (New-ScheduledTask registers nothing) and drives the Run-entry removal with a fake key.
    def run_functions(self, body):
        command = (
            "$ErrorActionPreference='Stop';"
            "$ast=[Management.Automation.Language.Parser]::ParseFile($env:FIXTURE_SCRIPT,[ref]$null,[ref]$null);"
            "foreach($f in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)){"
            "if($f.Name -in 'Quote-NativeArgument','New-PublisherTask','Remove-OwnedRunEntry'){Invoke-Expression $f.Extent.Text}};"
            "$entryName='MelangeDesktopPublisher';" + body)
        result = subprocess.run([shutil.which('pwsh'), '-NoProfile', '-NonInteractive', '-Command', command],
                                env=dict(os.environ, FIXTURE_SCRIPT=str(Path(__file__).with_name('Register-LanPublisherStartup.ps1'))),
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_task_definition_restarts_unelevated_without_limits(self):
        task = self.run_functions(
            "$t=New-PublisherTask 'C:\\fixture\\pwsh.exe' ((@('-File','C:\\fixture dir\\Start-LanPublisherAtLogin.ps1') | ForEach-Object { Quote-NativeArgument $_ }) -join ' ') 'FIXTURE\\user';"
            "$s=$t.Settings; @{execute=$t.Actions[0].Execute; arguments=$t.Actions[0].Arguments; actions=@($t.Actions).Count;"
            "triggers=@($t.Triggers | ForEach-Object { @{kind=$_.CimClass.CimClassName; user=$_.UserId; interval=$_.Repetition.Interval; duration=$_.Repetition.Duration} });"
            "restartCount=$s.RestartCount; restartInterval=$s.RestartInterval; limit=$s.ExecutionTimeLimit; priority=$s.Priority;"
            "noBatteryBlock=-not $s.DisallowStartIfOnBatteries; noBatteryStop=-not $s.StopIfGoingOnBatteries; instances=[string]$s.MultipleInstances;"
            "logon=[string]$t.Principal.LogonType; runLevel=[string]$t.Principal.RunLevel; principal=$t.Principal.UserId} | ConvertTo-Json -Depth 4")
        self.assertEqual((task['execute'], task['actions']), ('C:\\fixture\\pwsh.exe', 1))
        self.assertEqual(task['arguments'], '"-File" "C:\\fixture dir\\Start-LanPublisherAtLogin.ps1"')
        kinds = {t['kind']: t for t in task['triggers']}
        self.assertEqual(set(kinds), {'MSFT_TaskLogonTrigger', 'MSFT_TaskTimeTrigger'})
        self.assertEqual(kinds['MSFT_TaskLogonTrigger']['user'], 'FIXTURE\\user')
        self.assertEqual(kinds['MSFT_TaskTimeTrigger']['interval'], 'PT1M')
        self.assertIn(kinds['MSFT_TaskTimeTrigger']['duration'], (None, ''))  # repeats indefinitely
        self.assertEqual((task['restartCount'], task['restartInterval'], task['limit'], task['priority']), (99, 'PT1M', 'PT0S', 4))
        self.assertTrue(task['noBatteryBlock'] and task['noBatteryStop'])
        self.assertEqual((task['instances'], task['logon'], task['runLevel'], task['principal']), ('IgnoreNew', 'Interactive', 'Limited', 'FIXTURE\\user'))

    def test_run_entry_removed_only_when_owned(self):
        result = self.run_functions(
            "function New-FakeKey($value){ $k=[pscustomobject]@{Store=@{}}; if($value){$k.Store[$entryName]=$value};"
            "$k | Add-Member ScriptMethod GetValue { param($n,$d) if($this.Store.ContainsKey($n)){$this.Store[$n]}else{$d} };"
            "$k | Add-Member ScriptMethod DeleteValue { param($n,$t) $this.Store.Remove($n) }; $k };"
            "$owned=New-FakeKey 'old-cmd'; $foreign=New-FakeKey 'other-cmd'; $empty=New-FakeKey $null;"
            "$a=Remove-OwnedRunEntry $owned @('new-cmd','old-cmd');"
            "try { Remove-OwnedRunEntry $foreign @('new-cmd','old-cmd') | Out-Null; $refused=$false } catch { $refused=$true };"
            "@{owned=$a; ownedLeft=$owned.Store.Count; refused=$refused; foreignLeft=$foreign.Store[$entryName]; empty=(Remove-OwnedRunEntry $empty @('new-cmd'))} | ConvertTo-Json")
        self.assertEqual(result, {'owned': 'removed', 'ownedLeft': 0, 'refused': True, 'foreignLeft': 'other-cmd', 'empty': 'absent'})


SUPERVISOR_SCRIPT = Path(__file__).with_name('Start-LanPublisherAtLogin.ps1')


if __name__ == '__main__': unittest.main()
