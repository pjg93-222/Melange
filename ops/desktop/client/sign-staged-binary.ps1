#requires -Version 5.1
param(
  [Parameter(Mandatory=$true)][string]$File,
  [Parameter(Mandatory=$true)][string]$Root,
  [ValidateSet('Sign','Verify')][string]$Mode = 'Sign',
  [switch]$RequirePublisher
)
$ErrorActionPreference = 'Stop'
function Test-PortableExecutableFile([string]$Path) {
  $stream = [IO.File]::OpenRead($Path)
  try {
    $header = [byte[]]::new(64)
    if ($stream.Read($header, 0, 64) -ne 64 -or $header[0] -ne 77 -or $header[1] -ne 90) { return $false }
    $offset = [BitConverter]::ToUInt32($header, 60)
    if ($offset -gt $stream.Length - 4) { return $false }
    $stream.Position = $offset
    $signature = [byte[]]::new(4)
    return $stream.Read($signature, 0, 4) -eq 4 -and $signature[0] -eq 80 -and $signature[1] -eq 69 -and $signature[2] -eq 0 -and $signature[3] -eq 0
  } finally { $stream.Dispose() }
}
if ($PSHOME -ne 'C:\Windows\System32\WindowsPowerShell\v1.0' -or $PSVersionTable.PSEdition -ne 'Desktop' -or $PSVersionTable.PSVersion.Major -ne 5 -or $PSVersionTable.PSVersion.Minor -ne 1) { throw 'Fixed WindowsPowerShell 5.1 host required' }
Import-Module -Name ($PSHOME + '\Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1') -ErrorAction Stop
Import-Module -Name ($PSHOME + '\Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1') -ErrorAction Stop
function Assert-ReleaseBuiltinCommand([string]$Name, [string]$Module, [string]$ModuleFile, [string]$Type) {
  $command = Get-Command -Name ($Module + '\' + $Name) -ErrorAction Stop
  $expected = [IO.Path]::Combine($PSHOME, 'Modules', $Module, $ModuleFile)
  if (-not $command.Module -or $command.ModuleName -cne $Module -or [string]$command.CommandType -cne $Type -or -not [string]::Equals([IO.Path]::GetFullPath($command.Module.Path), $expected, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected builtin signing command origin' }
}
Assert-ReleaseBuiltinCommand 'Get-FileHash' 'Microsoft.PowerShell.Utility' 'Microsoft.PowerShell.Utility.psm1' 'Function'
Assert-ReleaseBuiltinCommand 'ConvertTo-Json' 'Microsoft.PowerShell.Utility' 'Microsoft.PowerShell.Utility.psd1' 'Cmdlet'
Assert-ReleaseBuiltinCommand 'Get-AuthenticodeSignature' 'Microsoft.PowerShell.Security' 'Microsoft.PowerShell.Security.psd1' 'Cmdlet'
$thumbprint = '0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30'
$subject = 'CN=Melange Systems Desktop Release (self-signed)'
$signtool = 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.28000.0\x64\signtool.exe'
$filePath = [IO.Path]::GetFullPath($File)
$rootPath = [IO.Path]::GetFullPath($Root).TrimEnd('\')
if (-not $filePath.StartsWith($rootPath + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Signing target is outside the private build root' }
$item = Get-Item -LiteralPath $filePath
if ($item.PSIsContainer) { throw 'Signing target is not an executable binary' }
if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Signing target is a reparse point' }
for ($parent = $item.Directory; $null -ne $parent; $parent = $parent.Parent) {
  if ($parent.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Signing target traverses a reparse point' }
}
$links = @(& fsutil.exe hardlink list $filePath)
if ($LASTEXITCODE -ne 0 -or $links.Count -ne 1) { throw 'Signing target must have exactly one hard link' }
if ($item.Extension.ToLowerInvariant() -notin @('.exe','.dll','.pyd','.node','.ocx') -and -not (Test-PortableExecutableFile $filePath)) { throw 'Signing target is not an executable binary' }
$before = (Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
$signature = Microsoft.PowerShell.Security\Get-AuthenticodeSignature -LiteralPath $filePath
$signed = $false
if ($signature.Status -eq 'NotSigned' -and $Mode -eq 'Sign') {
  $certificate = Get-Item -LiteralPath ('Cert:\CurrentUser\My\' + $thumbprint)
  if (-not $certificate.HasPrivateKey -or $certificate.Subject -cne $subject -or $certificate.NotAfter -le (Microsoft.PowerShell.Utility\Get-Date)) { throw 'Approved release certificate is unavailable' }
  & $signtool sign /sha1 $thumbprint /s My /fd sha256 /tr http://timestamp.digicert.com /td sha256 $filePath | Out-Null
  if ($LASTEXITCODE -ne 0) { throw 'Release signing failed' }
  $signed = $true
  $signature = Microsoft.PowerShell.Security\Get-AuthenticodeSignature -LiteralPath $filePath
}
if ($signature.Status -ne 'Valid') { throw ('Binary signature is not Valid: ' + $signature.Status) }
if ($signed -or $RequirePublisher) {
  if ($signature.SignerCertificate.Thumbprint -cne $thumbprint -or $signature.SignerCertificate.Subject -cne $subject -or -not $signature.TimeStamperCertificate) { throw 'Owned binary does not have the approved timestamped release signature' }
}
$after = (Microsoft.PowerShell.Utility\Get-FileHash -LiteralPath $filePath -Algorithm SHA256).Hash.ToLowerInvariant()
if (-not $signed -and $before -cne $after) { throw 'Existing vendor binary changed while verifying' }
[ordered]@{path=$filePath;sha256=$after;beforeSha256=$before;status='Valid';thumbprint=$signature.SignerCertificate.Thumbprint;timestamped=[bool]$signature.TimeStamperCertificate;signed=$signed;preserved=(-not $signed)} | Microsoft.PowerShell.Utility\ConvertTo-Json -Compress
