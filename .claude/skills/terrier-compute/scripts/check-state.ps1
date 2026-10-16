# PowerShell 5.1. Metadata-only diagnostic; never a readiness or authorization gate.
# Usage: powershell -NoProfile -File check-state.ps1 -Repo <absolute-project-root>
# No network, Docker, application, task, process enumeration or configuration writes.
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string]$Repo
)

$savedErrorAction = $ErrorActionPreference
$priorOptionalLocks = [Environment]::GetEnvironmentVariable('GIT_OPTIONAL_LOCKS', 'Process')
$priorTerminalPrompt = [Environment]::GetEnvironmentVariable('GIT_TERMINAL_PROMPT', 'Process')
try {
    $ErrorActionPreference = 'Stop'
    [Environment]::SetEnvironmentVariable('GIT_OPTIONAL_LOCKS', '0', 'Process')
    [Environment]::SetEnvironmentVariable('GIT_TERMINAL_PROMPT', '0', 'Process')
    if ($Repo -notmatch '^[A-Za-z]:[\\/]' -or $Repo -match '[\r\n"]') {
        throw 'Repo must be an explicit absolute local-drive directory.'
    }
    function Get-LocalMetadata([string]$Path) {
        # Walk each lexical component before touching the next. Never follow a
        # junction/symlink or ask a cloud provider to hydrate an offline item.
        $full = [IO.Path]::GetFullPath($Path)
        if ($full -notmatch '^[A-Za-z]:[\\/]') { throw 'Non-local route refused.' }
        $driveRoot = [IO.Path]::GetPathRoot($full)
        $driveInfo = New-Object System.IO.DriveInfo -ArgumentList $driveRoot
        if ($driveInfo.DriveType -notin @([IO.DriveType]::Fixed, [IO.DriveType]::Removable)) {
            throw 'Non-local drive route refused.'
        }
        $parts = @($full.Substring($driveRoot.Length) -split '[\\/]' | Where-Object { $_ })
        $routes = @($driveRoot)
        $cursor = $driveRoot
        foreach ($part in $parts) { $cursor = Join-Path $cursor $part; $routes += $cursor }
        $item = $null
        foreach ($route in $routes) {
            try { $item = Get-Item -LiteralPath $route -Force -ErrorAction Stop }
            catch [System.Management.Automation.ItemNotFoundException] { return $null }
            if ($item.PSProvider.Name -ne 'FileSystem') { throw 'Non-filesystem route refused.' }
            # ReparsePoint, Offline, RecallOnOpen/EA, RecallOnDataAccess. The last
            # two are rejected conservatively even when provider meaning differs.
            if (([int64]$item.Attributes -band 0x441400) -ne 0) { throw 'Reparse/offline/recall route refused.' }
            if ($route -ne $routes[-1] -and -not $item.PSIsContainer) { throw 'Non-directory ancestor refused.' }
        }
        return $item
    }
    function Read-LocalGitText([string]$Path, [int64]$MaxBytes) {
        $item = Get-LocalMetadata $Path
        if ($null -eq $item) { return $null }
        if ($item.PSIsContainer -or $item.Length -gt $MaxBytes) { throw 'Unsupported Git metadata file.' }
        return [IO.File]::ReadAllText($item.FullName)
    }
    $rootItem = Get-LocalMetadata $Repo
    if ($null -eq $rootItem) { throw 'Selected root is absent or inaccessible.' }
    if (-not $rootItem.PSIsContainer -or $rootItem.PSProvider.Name -ne 'FileSystem') {
        throw 'Repo must be a filesystem directory.'
    }
    $repoFull = $rootItem.FullName
    $gitRoot = Join-Path $repoFull '.git'
    $gitItem = Get-LocalMetadata $gitRoot
    if ($null -eq $gitItem -or -not $gitItem.PSIsContainer) {
        throw 'A direct .git directory is required; linked-worktree/gitfile routing is unverified.'
    }
    if ($null -ne (Get-LocalMetadata (Join-Path $gitRoot 'commondir'))) {
        throw 'Common-directory Git redirection is not supported by this diagnostic.'
    }
    # Refuse local config includes/extensions rather than following private/network
    # config or alternate ref-storage routes. Do not print the config contents.
    foreach ($configName in 'config', 'config.worktree') {
        $configText = Read-LocalGitText (Join-Path $gitRoot $configName) 1048576
        if ($configText -match '(?im)^\s*\[\s*(include(?:if)?|extensions)\b') {
            throw 'Git config include/extension routing is unsupported; metadata unverified.'
        }
    }
    # HEAD/ref reads are Git metadata, not tracked working-tree content. Validate
    # every referenced ancestor before Git resolves HEAD. Refuse unusual chains.
    $refText = Read-LocalGitText (Join-Path $gitRoot 'HEAD') 4096
    if ($null -eq $refText) { throw 'HEAD metadata is absent.' }
    for ($depth = 0; $depth -lt 8; $depth++) {
        if ($refText.Trim() -match '^[0-9a-fA-F]{40,64}$') { break }
        if ($refText.Trim() -notmatch '^ref: (refs/[A-Za-z0-9._/-]+)$') { throw 'Unsupported HEAD/ref syntax.' }
        $refPath = $Matches[1]
        if ($refPath.Contains('..') -or $refPath.Contains('//') -or $refPath.EndsWith('/')) {
            throw 'Unsupported HEAD/ref route.'
        }
        $refText = Read-LocalGitText (Join-Path $gitRoot $refPath) 4096
        if ($null -eq $refText) { break } # May be packed; validate that file below.
    }
    if ($depth -ge 8) { throw 'HEAD/ref chain exceeds diagnostic bound.' }
    $packedRefs = Get-LocalMetadata (Join-Path $gitRoot 'packed-refs')
    if ($null -ne $packedRefs -and ($packedRefs.PSIsContainer -or $packedRefs.Length -gt 33554432)) {
        throw 'Unsupported packed-ref metadata.'
    }
    $gitCommand = Get-Command git.exe -CommandType Application -ErrorAction Stop | Select-Object -First 1

    function Show([string]$Name, $Value) { '{0,-34} {1}' -f $Name, $Value }
    function Invoke-ReadOnlyGit([string[]]$Arguments) {
        # Arguments below are fixed internal tokens, never user-provided shell text.
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $gitCommand.Source
        $psi.WorkingDirectory = $repoFull
        $psi.Arguments = '--no-optional-locks --git-dir=.git --work-tree=. -c core.fsmonitor=false -c core.untrackedCache=false ' + ($Arguments -join ' ')
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
        # Clear ALL ambient Git selectors/config/namespace/object/ref overrides in
        # the child only; then bind it to the validated explicit .git and root.
        foreach ($name in @($psi.EnvironmentVariables.Keys)) {
            if ($name -like 'GIT_*') { $psi.EnvironmentVariables.Remove($name) }
        }
        $psi.EnvironmentVariables['GIT_OPTIONAL_LOCKS'] = '0'
        $psi.EnvironmentVariables['GIT_TERMINAL_PROMPT'] = '0'
        $psi.EnvironmentVariables['GIT_CONFIG_NOSYSTEM'] = '1'
        $psi.EnvironmentVariables['GIT_CONFIG_SYSTEM'] = 'NUL'
        $psi.EnvironmentVariables['GIT_CONFIG_GLOBAL'] = 'NUL'
        $psi.EnvironmentVariables['GIT_CEILING_DIRECTORIES'] = $repoFull
        $psi.EnvironmentVariables['GIT_DISCOVERY_ACROSS_FILESYSTEM'] = '0'
        $psi.EnvironmentVariables['GIT_NO_LAZY_FETCH'] = '1'
        $psi.EnvironmentVariables['GIT_NO_REPLACE_OBJECTS'] = '1'
        $p = New-Object System.Diagnostics.Process
        $p.StartInfo = $psi
        try {
            if (-not $p.Start()) { return @{ Ok = $false; Output = ''; Note = 'probe did not start' } }
            $stdout = $p.StandardOutput.ReadToEndAsync()
            $stderr = $p.StandardError.ReadToEndAsync()
            if (-not $p.WaitForExit(30000)) {
                # Only this exact owned read-only Git probe, never any process tree.
                try { $p.Kill() } catch { }
                return @{ Ok = $false; Output = ''; Note = 'probe timed out; state unverified' }
            }
            $drained = [Threading.Tasks.Task]::WaitAll([Threading.Tasks.Task[]]@($stdout, $stderr), 1000)
            if (-not $drained) { return @{ Ok = $false; Output = ''; Note = 'probe output did not close; state unverified' } }
            $output = $stdout.GetAwaiter().GetResult()
            $null = $stderr.GetAwaiter().GetResult() # Do not publish raw stderr/paths.
            if ($p.ExitCode -ne 0) { return @{ Ok = $false; Output = ''; Note = ('probe exit ' + $p.ExitCode) } }
            if ($output.Length -gt 1048576) { return @{ Ok = $false; Output = ''; Note = 'output exceeds diagnostic bound' } }
            return @{ Ok = $true; Output = $output.Trim(); Note = '' }
        } catch {
            return @{ Ok = $false; Output = ''; Note = 'probe failed; raw error withheld' }
        } finally { $p.Dispose() }
    }

    function Show-FileMetadata([string]$RelativePath) {
        # Fixed relative paths below; no contents, hashes or recursive traversal.
        $path = Join-Path $repoFull $RelativePath
        try {
            $item = Get-LocalMetadata $path
            if ($null -eq $item) {
                Show $RelativePath 'absent; unverified'
            } elseif ($item.PSIsContainer) {
                Show $RelativePath 'directory present; contents uninspected'
            } else {
                Show $RelativePath ('present; bytes={0}; mtimeUtc={1}' -f $item.Length, $item.LastWriteTimeUtc.ToString('o'))
            }
        } catch { Show $RelativePath 'unsafe/unsupported/inaccessible route; blocked, unverified' }
    }

    Show 'application' 'Terrier'
    Show 'observed UTC' ([DateTime]::UtcNow.ToString('o'))
    Show 'scope' 'explicit local checkout; metadata only'
    $r = Invoke-ReadOnlyGit @('rev-parse', '--show-toplevel')
    if (-not $r.Ok -or -not [string]::Equals(
        [IO.Path]::GetFullPath($r.Output).TrimEnd([char[]]'\/'),
        [IO.Path]::GetFullPath($repoFull).TrimEnd([char[]]'\/'),
        [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Git top-level does not match the selected root; metadata unverified.'
    }
    $r = Invoke-ReadOnlyGit @('rev-parse', '--verify', 'HEAD')
    if ($r.Ok -and $r.Output -match '^[0-9a-f]{40,64}$') { Show 'HEAD' $r.Output }
    else { Show 'HEAD' ('unverified: ' + $r.Note) }
    # No git status/diff: they may read/hydrate tracked content or run filters.
    # Do not print branch names, commit subjects, remotes or paths from Git.
    Show 'dirty/staged/untracked state' 'UNVERIFIED; working-tree/index content not inspected'
    Show 'ignored/submodules' 'UNVERIFIED; no cleanliness claim'

    foreach ($relative in @('COMPUTE.md', 'HOSTED.md', 'compute.compose.yaml', 'tools/compute_build.py', 'tools/compute_parity.py', '.local', '_build', '_build/run_nowithhold.ps1', '_build/run_remaining.ps1', '_build/run_fast.ps1', '_build/run_nowithhold.status.jsonl')) { Show-FileMetadata $relative }
    foreach ($name in @('TERRIER_COMPUTE', 'TERRIER_BUILD_IMAGE', 'TERRIER_SCORE_IMAGE')) {
        foreach ($scope in 'Process', 'User', 'Machine') {
            $value = [Environment]::GetEnvironmentVariable($name, $scope)
            Show ($name + ' [' + $scope + ']') $(if ([string]::IsNullOrEmpty($value)) { 'unset/empty' } else { 'set; value withheld' })
        }
    }
    $reserveBytes = [int64]35000000000
    Show 'C: reserve bytes' $reserveBytes
    try {
        $drive = New-Object System.IO.DriveInfo -ArgumentList 'C:\'
        if (-not $drive.IsReady) { throw 'Drive unavailable' }
        $freeBytes = [int64]$drive.AvailableFreeSpace
        Show 'C: available bytes' $freeBytes
        Show 'C: reserve observation' $(if ($freeBytes -lt $reserveBytes) { 'below reserve; no new heavy allocation' } else { 'reserve currently met; projected allocations still unverified' })
    } catch { Show 'C: available bytes' 'unverified' }
    Show 'other target volumes' 'not inspected; establish their reserves separately'
    Show 'readiness gates' 'Docker, writers, trust, evidence contents, data and tasks NOT VERIFIED'
    Show 'result' 'metadata only; no build, cutover or publication authorized'
} finally {
    [Environment]::SetEnvironmentVariable('GIT_OPTIONAL_LOCKS', $priorOptionalLocks, 'Process')
    [Environment]::SetEnvironmentVariable('GIT_TERMINAL_PROMPT', $priorTerminalPrompt, 'Process')
    $ErrorActionPreference = $savedErrorAction
}
