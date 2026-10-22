# Registers Start-LanPublisherAtLogin.ps1 to start at login for the current user, unelevated.
# Public mode (and -AsScheduledTask) uses the scheduled task MelangeDesktopPublisher; LAN mode keeps the
# HKCU Run entry of the same name unless -AsScheduledTask is given. The two are exclusive: installing the task
# removes the owned Run entry, and the Run entry refuses to install beside the task.
# The task starts at logon and repeats every minute with MultipleInstances IgnoreNew, so a supervisor that ended
# for any reason (exception, kill, crash) is started again within a minute while the user is logged on.
# Task Scheduler's restart-on-failure (RestartCount 99, one minute) is also set but does not act on a non-zero exit
# code of the action; the repetition is what restarts it. The supervisor exits 1 on any abnormal end and 0 only when
# another supervisor already runs (supervisor.log records it; while one runs, each skipped repetition sets the task's
# Last Run Result to 0x800710E0). Restart: Stop-ScheduledTask, then Start-ScheduledTask.
# Stop for good: Disable-ScheduledTask, then Stop-ScheduledTask (a stop alone is undone by the next repetition).
[CmdletBinding()]
param(
    [ValidateSet('Install', 'Remove', 'Status')][string]$Action = 'Status',
    [string]$ListenIPAddress,
    [string]$ExpectedNetworkName,
    # Internet mode behind a local TCP pass-through relay (Tailscale Funnel); replaces the LAN address/name.
    [string]$PublicOrigin,
    [string]$PythonExecutable,
    [string]$PowerShellExecutable,
    [string]$StateDirectory = (Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Documents\MelangeDesktopAdmin'),
    [ValidateRange(1024, 65535)][int]$Port = 38443,
    # Default: on for -PublicOrigin, off for LAN mode. -AsScheduledTask:$false keeps the HKCU Run entry.
    [switch]$AsScheduledTask,
    # The supervisor the startup entry runs; default is the copy beside this script.
    [string]$SupervisorScript = (Join-Path $PSScriptRoot 'Start-LanPublisherAtLogin.ps1')
)
$ErrorActionPreference = 'Stop'
$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if ($principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'Register publisher startup from the ordinary user account, without elevation.'
}
$stateDirectory = [IO.Path]::GetFullPath($StateDirectory)
$recordPath = Join-Path $stateDirectory 'startup-registration.json'
$supervisor = (Get-Item -LiteralPath $SupervisorScript).FullName
if ([IO.Path]::GetFileName($supervisor) -cne 'Start-LanPublisherAtLogin.ps1') { throw 'SupervisorScript must be a Start-LanPublisherAtLogin.ps1.' }
$entryName = 'MelangeDesktopPublisher'
$runPath = 'Software\Microsoft\Windows\CurrentVersion\Run'
$useTask = if ($PSBoundParameters.ContainsKey('AsScheduledTask')) { [bool]$AsScheduledTask } else { [bool]$PublicOrigin }

function Quote-NativeArgument([string]$Value) {
    if ($Value -match '[\x00\r\n]') { throw 'Invalid startup argument.' }
    # CommandLineToArgvW escaping; -File receives arguments, never executable source.
    return '"' + [regex]::Replace([regex]::Replace($Value, '(\\*)"', '$1$1\"'), '(\\+)$', '$1$1') + '"'
}

function New-PublisherTask([string]$Executable, [string]$Arguments, [string]$UserId) {
    # Logon start, plus a one-minute repetition from registration time that restarts an ended supervisor
    # (IgnoreNew skips it while one runs). Priority 4 is the normal interactive level; the task default (7) left the
    # supervisor hung. No time limit, and battery state never blocks or stops it.
    $action = New-ScheduledTaskAction -Execute $Executable -Argument $Arguments
    $logon = New-ScheduledTaskTrigger -AtLogOn -User $UserId
    $repeat = New-ScheduledTaskTrigger -Once -At ([DateTime]::Now) -RepetitionInterval (New-TimeSpan -Minutes 1)
    $settings = New-ScheduledTaskSettingsSet -RestartCount 99 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit ([TimeSpan]::Zero) `
        -Priority 4 -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
    $taskPrincipal = New-ScheduledTaskPrincipal -UserId $UserId -LogonType Interactive -RunLevel Limited
    return New-ScheduledTask -Action $action -Trigger @($logon, $repeat) -Settings $settings -Principal $taskPrincipal
}

function Remove-OwnedRunEntry($Key, [string[]]$Owned) {
    # Deletes the Run value only when it is one this script wrote; anything else is left for the owner to inspect.
    $value = if ($Key) { $Key.GetValue($entryName, $null) } else { $null }
    if (-not $value) { return 'absent' }
    if ($value -cnotin $Owned) { throw 'A different startup entry already uses this name. It was not removed.' }
    $Key.DeleteValue($entryName, $false)
    return 'removed'
}

function Get-PublisherTask {
    return Get-ScheduledTask -TaskPath '\' -TaskName $entryName -ErrorAction SilentlyContinue
}

function Get-TaskCommand($Task) {
    if (-not $Task -or @($Task.Actions).Count -ne 1) { return $null }
    return (Quote-NativeArgument $Task.Actions[0].Execute) + ' ' + $Task.Actions[0].Arguments
}

$key = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($runPath, $Action -ne 'Status')
if (-not $key -and $Action -eq 'Install' -and -not $useTask) { $key = [Microsoft.Win32.Registry]::CurrentUser.CreateSubKey($runPath) }
try {
    $current = if ($key) { $key.GetValue($entryName, $null) } else { $null }
    $task = Get-PublisherTask
    $saved = if (Test-Path -LiteralPath $recordPath) { Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json } else { $null }
    if ($Action -eq 'Status') {
        $info = if ($task) { $task | Get-ScheduledTaskInfo } else { $null }
        [ordered]@{ registered = [bool]($current -or $task); entryName = $entryName; scope = 'current-user'; runEntry = [bool]$current
            scheduledTask = [bool]$task; taskState = if ($task) { [string]$task.State } else { $null }; lastTaskResult = if ($info) { $info.LastTaskResult } else { $null }
            mode = if ($saved -and $saved.mode) { $saved.mode } elseif ($saved) { 'runKey' } else { $null }
            metadataPresent = [bool]$saved; publicOrigin = if ($saved) { $saved.publicOrigin } else { $null } } | ConvertTo-Json
        return
    }
    if ($Action -eq 'Remove') {
        if (-not $current -and -not $task) { Write-Output 'Publisher login startup is already absent.'; return }
        if (-not $saved) { throw 'Registration metadata missing. Inspect the existing startup entry before removing it.' }
        if ($saved.entryName -cne $entryName -or $saved.supervisor -cne $supervisor -or
            ($current -and $saved.command -cne $current) -or ($task -and $saved.command -cne (Get-TaskCommand $task))) {
            throw 'Startup registration differs from the owned entry. It was not removed.'
        }
        if ($task) { Unregister-ScheduledTask -TaskPath '\' -TaskName $entryName -Confirm:$false }
        if ($current) { $key.DeleteValue($entryName, $false) }
        Write-Output 'Removed only the current-user publisher startup registration. Firewall, keys, releases and client data were not changed.'
        return
    }
    if ($PublicOrigin) {
        if ($ListenIPAddress -or $ExpectedNetworkName -or -not $PythonExecutable) {
            throw 'PublicOrigin startup listens on 127.0.0.1 only: pass -PublicOrigin and -PythonExecutable without -ListenIPAddress or -ExpectedNetworkName.'
        }
        if ($Port -ne 38443) { throw 'PublicOrigin startup listens on 127.0.0.1:38443, the only local port relay_tunnel.py forwards to.' }
    } elseif (-not $ListenIPAddress -or -not $ExpectedNetworkName -or -not $PythonExecutable) {
        throw 'Install requires the approved LAN address/name and explicit Python executable.'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $stateDirectory 'trust.json'))) {
        throw 'Initialize the protected publisher state first.'
    }
    if (-not $PowerShellExecutable) { $PowerShellExecutable = (Get-Process -Id $PID).Path }
    $PowerShellExecutable = (Get-Item -LiteralPath $PowerShellExecutable).FullName
    # Ask the executable itself: MSIX app-execution aliases (the stable path across updates) carry no file version.
    if ([int](& $PowerShellExecutable -NoProfile -NonInteractive -Command '$PSVersionTable.PSVersion.Major') -lt 7) {
        throw 'Publisher startup requires a PowerShell 7 executable.'
    }
    $PythonExecutable = (Get-Item -LiteralPath $PythonExecutable).FullName
    if ($PublicOrigin) {
        # desktop_admin.py applies the https_origin rules; the origin must already be canonical and a DNS name.
        $descriptor = (& $PythonExecutable (Join-Path $PSScriptRoot 'desktop_admin.py') --state $stateDirectory --public-origin $PublicOrigin access-trust --url $PublicOrigin) -join "`n"
        if ($LASTEXITCODE -ne 0 -or ($descriptor | ConvertFrom-Json).url -cne $PublicOrigin -or ([Uri]$PublicOrigin).HostNameType -ne 'Dns') {
            throw 'PublicOrigin must be a canonical https DNS origin accepted by desktop_admin.py (lowercase, no path, :443 omitted), with application access initialized.'
        }
        $mode = @('-PublicOrigin', $PublicOrigin)
    } else {
        & (Join-Path $PSScriptRoot 'Start-LanPublisher.ps1') -ListenIPAddress $ListenIPAddress `
            -ExpectedNetworkName $ExpectedNetworkName -PythonExecutable $PythonExecutable -StateDirectory $stateDirectory -Port $Port -ConfigureOnly | Out-Null
        if ($LASTEXITCODE -ne 0) { throw 'Approved LAN/firewall validation failed; startup was not registered.' }
        $mode = @('-ListenIPAddress', $ListenIPAddress, '-ExpectedNetworkName', $ExpectedNetworkName)
    }
    $arguments = @('-NoProfile', '-NonInteractive', '-WindowStyle', 'Hidden', '-File', $supervisor) + $mode +
        @('-PythonExecutable', $PythonExecutable, '-StateDirectory', $stateDirectory, '-Port', [string]$Port)
    $taskArguments = ($arguments | ForEach-Object { Quote-NativeArgument $_ }) -join ' '
    $command = (Quote-NativeArgument $PowerShellExecutable) + ' ' + $taskArguments
    $record = [ordered]@{ schemaVersion = 1; mode = if ($useTask) { 'scheduledTask' } else { 'runKey' }; entryName = $entryName
        supervisor = $supervisor; command = $command; registeredAt = [DateTime]::UtcNow.ToString('o') }
    if ($useTask) {
        # The Run entry this script wrote before (recorded command) or would write now is replaced by the task.
        $owned = @($command) + @(if ($saved -and $saved.command) { [string]$saved.command })
        if ($current -and $current -cnotin $owned) { throw 'A different startup entry already uses this name. Nothing was changed.' }
        if ($task -and (Get-TaskCommand $task) -cne $command) { throw 'A different scheduled task already uses this name. It was not overwritten.' }
        $record.taskName = $entryName
    } else {
        if ($task) { throw 'The MelangeDesktopPublisher scheduled task is registered. Remove it first; two startup entries would race.' }
        if ($current -and $current -cne $command) { throw 'A different startup entry already uses this name. It was not overwritten.' }
    }
    if ($PublicOrigin) { $record.publicOrigin = $PublicOrigin }
    $temporary = $recordPath + '.tmp'
    [IO.File]::WriteAllText($temporary, ($record | ConvertTo-Json))
    [IO.File]::Move($temporary, $recordPath, $true)
    if ($useTask) {
        $userId = [Security.Principal.WindowsIdentity]::GetCurrent().Name
        Register-ScheduledTask -TaskPath '\' -TaskName $entryName -InputObject (New-PublisherTask $PowerShellExecutable $taskArguments $userId) -Force | Out-Null
        $runEntry = Remove-OwnedRunEntry $key $owned
        Write-Output ("Registered scheduled task $entryName for the current user (starts at logon, restarts within a minute; Run entry $runEntry). It was not started: Start-ScheduledTask $entryName.")
    } else {
        $key.SetValue($entryName, $command, [Microsoft.Win32.RegistryValueKind]::String)
        Write-Output $(if ($PublicOrigin) { 'Registered publisher startup for the current user only. The listener binds 127.0.0.1 for the local relay; no LAN or firewall rule is used.' }
            else { 'Registered publisher startup for the current user only. Approved LAN and firewall checks run before every listener start.' })
    }
} finally {
    if ($key) { $key.Dispose() }
}
