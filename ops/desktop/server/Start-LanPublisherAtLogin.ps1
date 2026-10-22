# Login supervisor for the desktop update/access publisher and its tray notifier.
# Exit codes: 0 only when another supervisor for this Windows user already holds the mutex (this one stands down);
# 1 on any terminating error (bad arguments or state, a failed publisher start, an exception in the loop).
# There is no in-script stop. To stop it, Disable-ScheduledTask then Stop-ScheduledTask MelangeDesktopPublisher (a stop alone
# is undone by the next repetition); to restart, Stop-ScheduledTask then Start-ScheduledTask.
# Task Scheduler's restart-on-failure setting does not restart a task whose action merely exits non-zero, so the
# MelangeDesktopPublisher task (Register-LanPublisherStartup.ps1) also repeats every minute with IgnoreNew: a new
# instance starts only when this one is gone, however it ended. Read exit codes in supervisor.log: while this runs,
# each skipped repetition sets the task's Last Run Result to 0x800710E0.
# Logs in the state directory: supervisor.log (this script), publisher.log/.err and notifier.log/.err (child
# stdout/stderr). Every line is timestamped and masked for credentials; each file rotates to <name>.1 above 10 MB.
[CmdletBinding(DefaultParameterSetName = 'Lan')]
param(
    [Parameter(Mandatory = $true, ParameterSetName = 'Lan')][string]$ListenIPAddress,
    [Parameter(Mandatory = $true, ParameterSetName = 'Lan')][string]$ExpectedNetworkName,
    # Internet mode behind a local TCP pass-through relay (Tailscale Funnel): listens on 127.0.0.1 only.
    [Parameter(Mandatory = $true, ParameterSetName = 'Public')][string]$PublicOrigin,
    [Parameter(Mandatory = $true)][string]$PythonExecutable,
    [Parameter(Mandatory = $true)][string]$StateDirectory,
    [ValidateRange(1024, 65535)][int]$Port = 38443
)
$ErrorActionPreference = 'Stop'
$logSource = @'
using System;
using System.IO;
using System.Text.RegularExpressions;
using System.Threading;
public static class MelangeLog {
    const long Limit = 10L * 1024 * 1024;
    static readonly object Gate = new object();
    // Credentials the access server creates are token_urlsafe values (43+ characters) or named key=value/bearer fields.
    static readonly Regex Secret = new Regex(@"(?i)\b(bearer\s+|(?:bootstrap|token|code|invite|key|secret|password|credential|authorization)\w*[""']?\s*[:=]\s*[""']?)[^\s""',;&]+|[A-Za-z0-9_\-]{32,}");
    public static string Mask(string line) {
        return Secret.Replace(line, m => m.Groups[1].Success ? m.Groups[1].Value + "[masked]" : "[masked]");
    }
    public static void Append(string path, string line) {
        try {
            lock (Gate) {
                var info = new FileInfo(path);
                if (info.Exists && info.Length > Limit) File.Move(path, path + ".1", true);
                File.AppendAllText(path, DateTime.UtcNow.ToString("o") + " " + Mask(line) + Environment.NewLine);
            }
        } catch { }  // A full disk or locked log must never end supervision or stop a pipe from draining.
    }
    // The .NET process-exit event also fires under pwsh -File, where PowerShell.Exiting engine events never do.
    // It records how a normal exit ended even if a finally block was skipped; a killed process logs nothing.
    public static void LogProcessExit(string path) {
        int pid = Environment.ProcessId;
        AppDomain.CurrentDomain.ProcessExit += (sender, e) => Append(path, "[" + pid + "] process exiting with code " + Environment.ExitCode);
    }
    // Drains a child's redirected stream on a background thread until the child (and any inheritor) closes it;
    // an undrained pipe would block the child. The caller joins the thread before exiting so final lines are kept.
    public static Thread Pump(StreamReader reader, string path) {
        var thread = new Thread(() => { try { string line; while ((line = reader.ReadLine()) != null) Append(path, line); } catch { } });
        thread.IsBackground = true;
        thread.Start();
        return thread;
    }
}
'@
$supervisorLog = Join-Path $StateDirectory 'supervisor.log'
function Write-SupervisorLog([string]$Message) {
    try { [MelangeLog]::Append($supervisorLog, ('[' + $PID + '] ' + $Message)) } catch { }
}
trap {
    Write-SupervisorLog ('terminating error: ' + $_.Exception.Message + ' | ' + ($_.ScriptStackTrace -replace '\r?\n', ' <- '))
    Write-SupervisorLog 'exiting with code 1'
    exit 1
}
Add-Type -TypeDefinition $logSource
[MelangeLog]::LogProcessExit($supervisorLog)
Write-SupervisorLog ('start: pwsh ' + $PSVersionTable.PSVersion + ' ' + (($PSBoundParameters.GetEnumerator() | ForEach-Object { '-' + $_.Key + ' ' + $_.Value }) -join ' '))
if ($PublicOrigin -and $Port -ne 38443) {
    throw 'PublicOrigin mode listens on 127.0.0.1:38443, the only local port relay_tunnel.py forwards to.'
}
if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw 'The publisher supervisor requires PowerShell 7 or later.'
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'The login publisher must run without elevation.'
}
$ownedMutex = $false
$mutex = [Threading.Mutex]::new($false, ('Local\MelangeDesktopPublisher-' + $identity.User.Value))
$publisherProcess = $null
$notifierProcess = $null
$publisherJob = $null
$pumps = [Collections.Generic.List[Threading.Thread]]::new()
$exitCode = 1
$stateDirectory = (Get-Item -LiteralPath $StateDirectory -ErrorAction Stop).FullName
$statusFile = Join-Path $stateDirectory 'listener-status.json'
$launchScript = Join-Path $PSScriptRoot 'Start-LanPublisher.ps1'
$serverScript = Join-Path $PSScriptRoot 'desktop_admin.py'
$notifierScript = Join-Path $PSScriptRoot 'Start-AccessNotifier.ps1'
if (-not (Test-Path -LiteralPath (Join-Path $stateDirectory 'trust.json'))) {
    throw 'Initialize the protected publisher state before enabling login startup.'
}
$serverArguments = @($serverScript, '--state', $stateDirectory)
if ($PublicOrigin) {
    # desktop_admin.py applies the https_origin rules; the origin must already be canonical and a DNS name.
    $descriptor = (& $PythonExecutable $serverScript --state $stateDirectory --public-origin $PublicOrigin access-trust --url $PublicOrigin) -join "`n"
    if ($LASTEXITCODE -ne 0 -or ($descriptor | ConvertFrom-Json).url -cne $PublicOrigin -or ([Uri]$PublicOrigin).HostNameType -ne 'Dns') {
        throw 'PublicOrigin must be a canonical https DNS origin accepted by desktop_admin.py, with application access initialized.'
    }
    $ListenIPAddress = '127.0.0.1'
    $serverArguments += @('--public-origin', $PublicOrigin)
}
$serverArguments += @('serve', '--listen', $ListenIPAddress, '--port', [string]$Port)
function Get-InviteRequired {
    # Same values as desktop_admin.py invite_env(); the publisher child inherits this environment. $null = unreadable value, so the publisher refuses to start.
    $raw = ([string]$env:MELANGE_ACCESS_REQUIRE_INVITE).Trim().ToLowerInvariant()
    if ($raw -in '1', 'true', 'yes', 'on') { return $true }
    if ($raw -in '', '0', 'false', 'no', 'off') { return $false }
    return $null
}
function Write-ListenerStatus([string]$Status) {
    # Fixed status values only: never write enrollment codes, credentials or request data.
    # Start-AccessNotifier.ps1 writes no status file of its own; this is its only liveness record.
    $record = [ordered]@{ status = $Status; checkedAt = [DateTime]::UtcNow.ToString('o'); supervisorPid = $PID; publisherPid = if ($publisherProcess) { $publisherProcess.Id } else { $null }
        notifierPid = if ($notifierProcess) { $notifierProcess.Id } else { $null }; inviteRequired = Get-InviteRequired }
    $temporary = $statusFile + '.' + $PID + '.tmp'
    try {
        [IO.File]::WriteAllText($temporary, ($record | ConvertTo-Json))
        [IO.File]::Move($temporary, $statusFile, $true)
    } catch {
        # A reader holding listener-status.json makes the replace fail (access denied). That must not end
        # supervision and take the publisher down with it; the next pass writes the status again.
        Write-SupervisorLog ('status write failed: ' + $_.Exception.Message)
        try { [IO.File]::Delete($temporary) } catch { }
    }
}
function Start-LoggedChild([string]$Name, [string]$Executable, [string[]]$Arguments) {
    # The child's stdout/stderr go to <Name>.log/.err in the state directory through MelangeLog (masked, rotated).
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $Executable
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    foreach ($argument in $Arguments) { $start.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::Start($start)
    foreach ($done in @($pumps | Where-Object { -not $_.IsAlive })) { [void]$pumps.Remove($done) }
    $pumps.Add([MelangeLog]::Pump($process.StandardOutput, (Join-Path $stateDirectory ($Name + '.log'))))
    $pumps.Add([MelangeLog]::Pump($process.StandardError, (Join-Path $stateDirectory ($Name + '.err'))))
    try {
        [MelangePublisherJob]::Assign($publisherJob, $process)
    } catch {
        # A child outside the job would outlive the supervisor.
        try { $process.Kill($true) } catch { }
        $process.Dispose()
        throw
    }
    Write-SupervisorLog ('started ' + $Name + ' pid ' + $process.Id + ': ' + $Executable + ' ' + ($Arguments -join ' '))
    return $process
}
function Test-ChildExited([string]$Name, $Process) {
    # True once the child has exited: logs its exit code and disposes the handle.
    if (-not $Process.HasExited) { return $false }
    Write-SupervisorLog ($Name + ' pid ' + $Process.Id + ' exited with code ' + $Process.ExitCode)
    $Process.Dispose()
    return $true
}
function Start-AccessNotifierProcess([string]$Executable) {
    # A failed tray must not end this loop: the supervisor's exit closes the job and takes the
    # publisher down with it. Return $null so the status records notifierPid null and the next pass retries.
    # Start-LoggedChild stops a started notifier it could not put in the job, so none outlives the supervisor.
    try {
        return Start-LoggedChild 'notifier' $Executable @('-NoProfile','-NonInteractive','-STA','-WindowStyle','Hidden','-File', $notifierScript, '-PythonExecutable',$PythonExecutable,'-StateDirectory',$stateDirectory)
    } catch {
        Write-SupervisorLog ('notifier start failed: ' + $_.Exception.Message)
        return $null
    }
}
try {
    try { $ownedMutex = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $ownedMutex = $true }
    if (-not $ownedMutex) {
        Write-SupervisorLog 'another supervisor for this user holds the mutex; standing down'
        $exitCode = 0
        exit 0
    }
    # Closing this OS handle kills only children explicitly assigned to this job,
    # including when the supervisor crashes or is terminated without its finally block.
    Add-Type -TypeDefinition @'
using System;
using System.Diagnostics;
using System.ComponentModel;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;
public static class MelangePublisherJob {
    [StructLayout(LayoutKind.Sequential)] struct BasicLimits {
        public long ProcessTime, JobTime;
        public uint Flags;
        public UIntPtr MinWorkingSet, MaxWorkingSet;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass, SchedulingClass;
    }
    [StructLayout(LayoutKind.Sequential)] struct IoCounters {
        public ulong ReadOps, WriteOps, OtherOps, ReadBytes, WriteBytes, OtherBytes;
    }
    [StructLayout(LayoutKind.Sequential)] struct ExtendedLimits {
        public BasicLimits Basic;
        public IoCounters Io;
        public UIntPtr ProcessMemory, JobMemory, PeakProcessMemory, PeakJobMemory;
    }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern SafeFileHandle CreateJobObject(IntPtr attributes, string name);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool SetInformationJobObject(SafeFileHandle job, int informationClass, ref ExtendedLimits limits, uint length);
    [DllImport("kernel32.dll", SetLastError=true)]
    static extern bool AssignProcessToJobObject(SafeFileHandle job, IntPtr process);
    public static SafeFileHandle Create() {
        var job=CreateJobObject(IntPtr.Zero,null);
        if(job.IsInvalid) throw new Win32Exception(Marshal.GetLastWin32Error());
        var limits=new ExtendedLimits(); limits.Basic.Flags=0x2000;
        if(!SetInformationJobObject(job,9,ref limits,(uint)Marshal.SizeOf<ExtendedLimits>())) {
            var error=Marshal.GetLastWin32Error(); job.Dispose(); throw new Win32Exception(error);
        }
        return job;
    }
    public static void Assign(SafeFileHandle job, Process process) {
        if(!AssignProcessToJobObject(job,process.Handle)) throw new Win32Exception(Marshal.GetLastWin32Error());
    }
}
'@
    $publisherJob = [MelangePublisherJob]::Create()
    while ($true) {
        # The local tray works independently of LAN reachability and app windows.
        # Its own SID mutex prevents duplicate notifiers after supervisor restart.
        if ($notifierProcess -and (Test-ChildExited 'notifier' $notifierProcess)) { $notifierProcess = $null }
        if (-not $notifierProcess -and (Test-Path -LiteralPath (Join-Path $stateDirectory 'access.sqlite3'))) {
            $notifierProcess = Start-AccessNotifierProcess (Get-Process -Id $PID).Path
        }
        $networkReady = $false
        try {
            # Loopback relay mode has no LAN adapter or inbound firewall rule to validate.
            if (-not $PublicOrigin) {
                & $launchScript -ListenIPAddress $ListenIPAddress -ExpectedNetworkName $ExpectedNetworkName `
                    -PythonExecutable $PythonExecutable -StateDirectory $stateDirectory -Port $Port -ConfigureOnly | Out-Null
                if ($LASTEXITCODE -ne 0) { throw 'Network validation failed.' }
            }
            $networkReady = $true
        } catch {
            $networkReady = $false
        }
        if ($publisherProcess -and (Test-ChildExited 'publisher' $publisherProcess)) { $publisherProcess = $null }
        if (-not $networkReady) {
            if ($publisherProcess) {
                Write-SupervisorLog ('stopping publisher pid ' + $publisherProcess.Id + ': approved LAN unavailable')
                $publisherProcess.Kill($true)
                $publisherProcess.WaitForExit()
                $publisherProcess.Dispose()
                $publisherProcess = $null
            }
            Write-ListenerStatus 'waiting-for-approved-lan'
        } elseif (-not $publisherProcess) {
            $publisherProcess = Start-LoggedChild 'publisher' $PythonExecutable $serverArguments
            Write-ListenerStatus 'starting'
        } else {
            Write-ListenerStatus 'running'
        }
        Start-Sleep -Seconds 30
    }
} catch {
    Write-SupervisorLog ('terminating error: ' + $_.Exception.Message + ' | ' + ($_.ScriptStackTrace -replace '\r?\n', ' <- '))
    $exitCode = 1
} finally {
    if ($publisherJob) { $publisherJob.Dispose() }
    try {
        if ($publisherProcess -and -not $publisherProcess.HasExited) {
            $publisherProcess.Kill($true)
            $publisherProcess.WaitForExit()
        }
    } catch { }
    if ($publisherProcess) { $publisherProcess.Dispose() }
    if ($notifierProcess) { $notifierProcess.Dispose() }
    # The job is closed, so every child has ended and its pipes reach end of file: let the drains write the last
    # lines, but never hold the exit for more than three seconds.
    $drainUntil = [DateTime]::UtcNow.AddSeconds(3)
    foreach ($pump in $pumps) {
        $left = [int]($drainUntil - [DateTime]::UtcNow).TotalMilliseconds
        if ($left -le 0) { break }
        [void]$pump.Join($left)
    }
    if ($ownedMutex) { $mutex.ReleaseMutex() }
    $mutex.Dispose()
    Write-SupervisorLog ('exiting with code ' + $exitCode)
}
exit $exitCode
