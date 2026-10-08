<#
Commit plan of lanes Z and T, porcelain route: git add + git update-index --cacheinfo + git commit, six
times. Everything is read from the folder this script is in (-Kit), so the kit can be moved as one folder.
Same six trees as apply_plan.ps1 (checked after every commit); git commit runs the repository's hooks
(the post-commit hook pushes to the mirror). Default is CHECK ONLY; add -Execute to write.

Per commit k:
  git add -f --pathspec-from-file=plan_add_k.nul --pathspec-file-nul     (files whose commit-k content
                                                                            is their final working-tree content)
  git update-index --add --cacheinfo <mode>,<blob>,<path>                   (plan_cacheinfo_k.txt: files whose
                                                                            commit-k content is an earlier real
                                                                            state; blobs come from zPlan.bundle)
  git commit -F messages\Zk.txt
  git rev-parse HEAD^{tree}  ==  the tree in plan_trees.txt
#>
param(
  [string]$Repo = 'C:\Users\pgoff\Mentat',
  [string]$Kit = $PSScriptRoot,
  [string]$Branch = 'codex/mentat-crypto',
  [switch]$Execute
)
$ErrorActionPreference = 'Continue'
$base = '3cec985249b098478868b8729e33b5b4ab31752e'
$tip = '6c12b631f897d595601d6e33ab373a0290e1875e'
$bundle = Join-Path $Kit 'zPlan.bundle'
$failed = $false
function Say($ok, $text) { if ($ok) { Write-Output ('OK    ' + $text) } else { Write-Output ('FAIL  ' + $text); $script:failed = $true } }
function G { $out = & git -C $Repo @args; $script:rc = $LASTEXITCODE; return $out }

$branchNow = G rev-parse --abbrev-ref HEAD
Say ($branchNow -eq $Branch) "branch is $Branch (found $branchNow)"
Say ((G rev-parse HEAD) -eq $base) "HEAD is $base"
Say (-not (Test-Path (Join-Path (G rev-parse --absolute-git-dir) 'index.lock'))) 'no index.lock'
G diff --cached --quiet | Out-Null
Say ($rc -eq 0) 'nothing is staged'
G diff --quiet -- 'mentat/app/geo/.gitignore' | Out-Null
Say ($rc -eq 0) 'mentat/app/geo/.gitignore is unedited (the apply rewrites it from the commit)'
G bundle verify $bundle | Out-Null
Say ($rc -eq 0) 'bundle verifies against this repository'
$set = (Get-Content -Raw -Encoding UTF8 (Join-Path $Kit 'commit_set.json') | ConvertFrom-Json).files
$drift = @()
foreach ($p in $set.PSObject.Properties) {
  if ($p.Name -eq 'mentat/app/geo/.gitignore') { continue }
  $file = Join-Path $Repo ($p.Name -replace '/', '\')
  if (-not (Test-Path -LiteralPath $file)) { $drift += "missing $($p.Name)"; continue }
  if ((Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLower() -ne $p.Value.sha256) { $drift += "changed $($p.Name)" }
}
Say ($drift.Count -eq 0) 'the files lanes Z and T tested are unchanged on disk'
$drift | Select-Object -First 20 | ForEach-Object { Write-Output ('      ' + $_) }
$trees = @{}
Get-Content (Join-Path $Kit 'plan_trees.txt') | ForEach-Object { $f = $_ -split ' '; $trees[$f[0]] = $f[2] }
if ($failed) { Write-Output 'Stopped: a precondition failed. Nothing was written.'; exit 1 }
if (-not $Execute) { Write-Output 'Checks passed. Re-run with -Execute to make the six commits.'; exit 0 }

G fetch --no-tags $bundle zPlan | Out-Null
Say ((G rev-parse FETCH_HEAD) -eq $tip) 'fetched the rehearsed objects (blobs for the earlier states)'
if ($failed) { exit 1 }
foreach ($k in 1..6) {
  $addList = Join-Path $Kit "plan_add_$k.nul"
  if ((Get-Item $addList).Length -gt 0) {
    G -c core.autocrlf=true add -f "--pathspec-from-file=$addList" --pathspec-file-nul | Out-Null
    Say ($rc -eq 0) "Z$k git add -f (plan_add_$k.nul)"
  }
  foreach ($line in Get-Content (Join-Path $Kit "plan_cacheinfo_$k.txt")) {
    if (-not $line) { continue }
    G update-index --add --cacheinfo $line | Out-Null
    Say ($rc -eq 0) "Z$k update-index --cacheinfo $line"
  }
  if ($failed) { Write-Output "Stopped while staging Z$k; run 'git reset -q' to unstage (the working tree was not touched)."; exit 1 }
  G commit -q -F (Join-Path $Kit "messages\Z$k.txt") | Out-Null
  $tree = G rev-parse 'HEAD^{tree}'
  Say ($rc -eq 0 -and $tree -eq $trees["Z$k"]) ("Z{0} committed {1}, tree {2} (expected {3})" -f $k, (G rev-parse --short HEAD), $tree, $trees["Z$k"])
  if ($failed) { Write-Output "Stopped after Z${k}, whose tree is not the tested tree. Inspect before continuing."; exit 1 }
}
G checkout -- 'mentat/app/geo/.gitignore' | Out-Null
Say ($rc -eq 0) 'wrote mentat/app/geo/.gitignore from HEAD (the only working-tree write)'
G update-index -q --refresh | Out-Null
$status = @(G -c core.quotepath=false status --porcelain=v1 -uall)
$ours = @($status | Where-Object { $_.Substring(3) -like 'mentat/*' -or $_.Substring(3) -like 'audits/mentat_failings_20260915/contracts/*' })
Say ($ours.Count -eq 0) ("no status entry left under mentat/ or the contracts ({0} entries elsewhere)" -f ($status.Count - $ours.Count))
$ours | Select-Object -First 20 | ForEach-Object { Write-Output ('      ' + $_) }
G log --oneline -7
