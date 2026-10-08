<#
Commit plan of lane V2 (2026-09-26 afternoon) for C:\Users\pgoff\Mentat (branch codex/mentat-crypto at fadd2c751).

Makes three commits whose trees are exactly the trees lane V2 built in a throwaway clone, exported
(git -c core.autocrlf=false -c core.eol=lf archive) and tested (cPlan.bundle, beside this script):
  C7  Count money unless it is proven counted twice                              (lanes J2, J3; 19 files)
  C8  Name split workbook sheets by election year                                (lane S2; 7 files)
  C9  Fix the Alaska and Hawaii map insets, the busy canvas and test temp folders (lanes L2, L3, J3; 49 files)
The commits are authored by this repository's configured user with the messages in messages\C7..C9.txt.
Everything is read from the folder this script is in (-Kit), so the kit can be moved as one folder.
Plumbing only (git commit-tree, update-ref, read-tree): no hook runs, and NO working-tree file is written.
Nothing is pushed; push the mirror by hand afterwards.

Default is CHECK ONLY (read-only: every git call runs with --no-optional-locks). Add -Execute to write.

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
$base = 'fadd2c751e1936c8924cab8c060d28f54837909b'
$tip = 'f20e502e211738072171509896c7925301f76c40'   # the tested C9 (laneV2\pm\clone, branch cPlan)
$names = @('C7', 'C8', 'C9')
$bundle = Join-Path $Kit 'cPlan.bundle'
$failed = $false
function Say($ok, $text) { if ($ok) { Write-Output ('OK    ' + $text) } else { Write-Output ('FAIL  ' + $text); $script:failed = $true } }
function Note($text) { Write-Output ('NOTE  ' + $text) }
function G { $out = & git --no-optional-locks -C $Repo @args; $script:rc = $LASTEXITCODE; return $out }   # read-only calls
function W { $out = & git -C $Repo @args; $script:rc = $LASTEXITCODE; return $out }                        # writes (-Execute only)

# ---- preconditions (read-only)
$branchNow = G rev-parse --abbrev-ref HEAD
Say ($branchNow -eq $Branch) "branch is $Branch (found $branchNow)"
$headNow = G rev-parse HEAD
Say ($headNow -eq $base) "HEAD is $base (found $headNow)"
$gitDir = G rev-parse --absolute-git-dir
Say (-not (Test-Path (Join-Path $gitDir 'index.lock'))) 'no index.lock'
G diff --cached --quiet | Out-Null
Say ($rc -eq 0) 'nothing is staged'
G bundle verify -q $bundle 2>$null | Out-Null
Say ($rc -eq 0) "bundle verifies against this repository ($bundle)"
$plan = Get-Content -Raw -Encoding UTF8 (Join-Path $Kit 'commit_set.json') | ConvertFrom-Json
$set = $plan.files
$drift = @()
foreach ($p in $set.PSObject.Properties) {
  $file = Join-Path $Repo ($p.Name -replace '/', '\')
  if (-not (Test-Path -LiteralPath $file)) { $drift += "missing $($p.Name)"; continue }
  $h = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower()
  if ($h -ne $p.Value.sha256) { $drift += "changed $($p.Name)" }
}
$count = @($set.PSObject.Properties).Count
Say ($drift.Count -eq 0) ("the {0} files lane V2 tested are unchanged on disk" -f $count)
$drift | Select-Object -First 20 | ForEach-Object { Write-Output ('      ' + $_) }
$status = @(G -c core.quotepath=false status --porcelain=v1 -uall)
$scoped = @($status | Where-Object { $_.Substring(3) -like 'mentat/*' -or $_.Substring(3) -like 'audits/mentat_failings_20260915/contracts/*' })
$planned = @($set.PSObject.Properties.Name)
$inStatus = @{}
foreach ($line in $scoped) { $inStatus[$line.Substring(3)] = $line.Substring(0, 2) }
$extra = @($scoped | Where-Object { $planned -notcontains $_.Substring(3) })
$absent = @($planned | Where-Object { -not $inStatus.ContainsKey($_) })
Say ($absent.Count -eq 0) ("every planned file shows as changed or new in git status ({0} of {1})" -f ($planned.Count - $absent.Count), $planned.Count)
$absent | Select-Object -First 20 | ForEach-Object { Write-Output ('      not changed: ' + $_) }
if ($extra.Count -eq 0) { Write-Output ('OK    git status under mentat/ and the contracts lists nothing outside the plan') }
else { Note ("{0} status entries under mentat/ or the contracts are NOT in this plan (another session's work?); they stay uncommitted:" -f $extra.Count); $extra | Select-Object -First 20 | ForEach-Object { Write-Output ('      ' + $_) } }
foreach ($k in $names) { Say (Test-Path (Join-Path $Kit "messages\$k.txt")) "message messages\$k.txt exists" }
if ($failed) { Write-Output 'Stopped: a precondition failed. Nothing was written.'; exit 1 }
if (-not $Execute) { Write-Output 'Checks passed. Re-run with -Execute to make the three commits.'; exit 0 }

# ---- write
W fetch --no-tags $bundle cPlan 2>$null | Out-Null
$fetched = G rev-parse FETCH_HEAD
Say ($fetched -eq $tip) "fetched the tested commits ($fetched)"
if ($failed) { exit 1 }
$chain = @(G rev-list --reverse "$base..$tip")
Say ($chain.Count -eq 3) "three tested commits on top of $base"
if ($failed) { exit 1 }
$parent = $base
for ($i = 0; $i -lt 3; $i++) {
  $tree = G rev-parse "$($chain[$i])^{tree}"
  Say ($tree -eq $plan.trees.($names[$i])) ("{0} tree {1} is the tested tree" -f $names[$i], $tree)
  if ($failed) { Write-Output 'Stopped before making any commit; nothing else changed.'; exit 1 }
  $msg = Join-Path $Kit ("messages\{0}.txt" -f $names[$i])
  $new = W commit-tree $tree -p $parent -F $msg
  Say ($rc -eq 0 -and $new) ("{0} {1} (tree {2})" -f $names[$i], $new, $tree)
  if ($failed) { Write-Output 'Stopped before moving the branch; nothing else changed.'; exit 1 }
  $parent = $new
}
Say ((G rev-parse "$parent^{tree}") -eq (G rev-parse "$tip^{tree}")) 'final tree equals the tested tree'
if ($failed) { exit 1 }
W update-ref "refs/heads/$Branch" $parent $base | Out-Null
Say ($rc -eq 0) "moved $Branch to $parent"
W read-tree $parent | Out-Null
Say ($rc -eq 0) 'index now matches the new HEAD (working tree untouched)'
W update-index -q --refresh | Out-Null
$status = @(G -c core.quotepath=false status --porcelain=v1 -uall)
$ours = @($status | Where-Object { $_.Substring(3) -like 'mentat/*' -or $_.Substring(3) -like 'audits/mentat_failings_20260915/contracts/*' })
Say ($ours.Count -eq 0) ("no status entry left under mentat/ or the contracts ({0} entries elsewhere: other owners' untracked files)" -f ($status.Count - $ours.Count))
$ours | Select-Object -First 20 | ForEach-Object { Write-Output ('      ' + $_) }
G log --oneline -4
Write-Output "Push the mirror by hand (hooks did not run): git -C $Repo push mirror $Branch"
