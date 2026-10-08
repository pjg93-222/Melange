<#
Commit plan of lanes Z and T for C:\Users\pgoff\Mentat (branch codex/mentat-crypto at 3cec98524).

Makes six commits whose trees are exactly the trees lanes Z and T built in a throwaway clone, exported
(git -c core.autocrlf=false -c core.eol=lf archive) and tested (zPlan.bundle, beside this script). The
commits are authored by this repository's configured user with the messages in messages\Z1..Z6.txt.
Everything is read from the folder this script is in (-Kit), so the kit can be moved as one folder.
No working-tree file is rewritten except mentat/app/geo/.gitignore (lane G's three ignore lines).
Nothing is pushed; post-commit hooks do not run (git commit-tree), so push the mirror by hand after.

Default is CHECK ONLY. Add -Execute to write.

  powershell -NoProfile -ExecutionPolicy Bypass -File apply_plan.ps1            # checks
  powershell -NoProfile -ExecutionPolicy Bypass -File apply_plan.ps1 -Execute   # commits
#>
param(
  [string]$Repo = 'C:\Users\pgoff\Mentat',
  [string]$Kit = $PSScriptRoot,
  [string]$Branch = 'codex/mentat-crypto',
  [switch]$Execute
)
$ErrorActionPreference = 'Continue'
$base = '3cec985249b098478868b8729e33b5b4ab31752e'
$tip = '6c12b631f897d595601d6e33ab373a0290e1875e'   # the rehearsed Z6 (laneT\clone zPlan)
$bundle = Join-Path $Kit 'zPlan.bundle'
$failed = $false
function Say($ok, $text) { if ($ok) { Write-Output ('OK    ' + $text) } else { Write-Output ('FAIL  ' + $text); $script:failed = $true } }
function G { $out = & git -C $Repo @args; $script:rc = $LASTEXITCODE; return $out }

# ---- preconditions (read-only)
$branchNow = G rev-parse --abbrev-ref HEAD
Say ($branchNow -eq $Branch) "branch is $Branch (found $branchNow)"
$headNow = G rev-parse HEAD
Say ($headNow -eq $base) "HEAD is $base (found $headNow)"
$gitDir = G rev-parse --absolute-git-dir
Say (-not (Test-Path (Join-Path $gitDir 'index.lock'))) 'no index.lock'
G diff --cached --quiet | Out-Null
Say ($rc -eq 0) 'nothing is staged'
G diff --quiet -- 'mentat/app/geo/.gitignore' | Out-Null
Say ($rc -eq 0) 'mentat/app/geo/.gitignore is unedited (the apply rewrites it from the commit)'
G bundle verify $bundle | Out-Null
Say ($rc -eq 0) "bundle verifies against this repository ($bundle)"
$set = (Get-Content -Raw -Encoding UTF8 (Join-Path $Kit 'commit_set.json') | ConvertFrom-Json).files
$drift = @()
foreach ($p in $set.PSObject.Properties) {
  if ($p.Name -eq 'mentat/app/geo/.gitignore') { continue }
  $file = Join-Path $Repo ($p.Name -replace '/', '\')
  if (-not (Test-Path -LiteralPath $file)) { $drift += "missing $($p.Name)"; continue }
  $h = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower()
  if ($h -ne $p.Value.sha256) { $drift += "changed $($p.Name)" }
}
Say ($drift.Count -eq 0) ("the {0} files lanes Z and T tested are unchanged on disk" -f ($set.PSObject.Properties.Name.Count - 1))
$drift | Select-Object -First 20 | ForEach-Object { Write-Output ('      ' + $_) }
foreach ($k in 1..6) { Say (Test-Path (Join-Path $Kit "messages\Z$k.txt")) "message messages\Z$k.txt exists" }
if ($failed) { Write-Output 'Stopped: a precondition failed. Nothing was written.'; exit 1 }
if (-not $Execute) { Write-Output 'Checks passed. Re-run with -Execute to make the six commits.'; exit 0 }

# ---- write
G fetch --no-tags $bundle zPlan | Out-Null
$fetched = G rev-parse FETCH_HEAD
Say ($fetched -eq $tip) "fetched the rehearsed commits ($fetched)"
if ($failed) { exit 1 }
$chain = @(G rev-list --reverse "$base..$tip")
Say ($chain.Count -eq 6) "six rehearsed commits on top of $base"
if ($failed) { exit 1 }
$parent = $base
for ($i = 0; $i -lt 6; $i++) {
  $tree = G rev-parse "$($chain[$i])^{tree}"
  $msg = Join-Path $Kit ("messages\Z{0}.txt" -f ($i + 1))
  $new = G commit-tree $tree -p $parent -F $msg
  Say ($rc -eq 0 -and $new) ("Z{0} {1} (tree {2})" -f ($i + 1), $new, $tree)
  if ($failed) { Write-Output 'Stopped before moving the branch; nothing else changed.'; exit 1 }
  $parent = $new
}
Say ((G rev-parse "$parent^{tree}") -eq (G rev-parse "$tip^{tree}")) 'final tree equals the tested tree'
if ($failed) { exit 1 }
G update-ref "refs/heads/$Branch" $parent $base | Out-Null
Say ($rc -eq 0) "moved $Branch to $parent"
G read-tree $parent | Out-Null
Say ($rc -eq 0) 'index now matches the new HEAD (working tree untouched)'
G checkout -- 'mentat/app/geo/.gitignore' | Out-Null
Say ($rc -eq 0) 'wrote mentat/app/geo/.gitignore from the commit (the only working-tree write)'
G update-index -q --refresh | Out-Null
$status = @(G -c core.quotepath=false status --porcelain=v1 -uall)
$ours = @($status | Where-Object { $_.Substring(3) -like 'mentat/*' -or $_.Substring(3) -like 'audits/mentat_failings_20260915/contracts/*' })
Say ($ours.Count -eq 0) ("no status entry left under mentat/ or the contracts ({0} entries elsewhere: other owners' untracked files)" -f ($status.Count - $ours.Count))
$ours | Select-Object -First 20 | ForEach-Object { Write-Output ('      ' + $_) }
G log --oneline -7
