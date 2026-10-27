<# Signs the domain-separated ZIP identity with the existing non-exportable
code-signing key. The output contains only the public certificate and signature.
This does not sign, run, publish, or alter the application ZIP itself. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$PayloadFile,
    [Parameter(Mandatory)][string]$OutputFile
)
$ErrorActionPreference = 'Stop'
function Test-CodeSigningEku([Security.Cryptography.X509Certificates.X509Certificate2]$Certificate) {
    foreach ($extension in $Certificate.Extensions) {
        if ($extension.Oid.Value -ceq '2.5.29.37') {
            $eku = [Security.Cryptography.X509Certificates.X509EnhancedKeyUsageExtension]::new($extension, $extension.Critical)
            return @($eku.EnhancedKeyUsages | ForEach-Object { $_.Value }) -contains '1.3.6.1.5.5.7.3.3'
        }
    }
    return $false
}
$publisherPin = '0EBC9AD04E929CDD731EDB5D278A4143BC3D3D30'
$payloadPath = (Resolve-Path -LiteralPath $PayloadFile).Path
$payloadInfo = Get-Item -LiteralPath $payloadPath
if ($payloadInfo.PSIsContainer -or $payloadInfo.Length -gt 65536) { throw 'Invalid signing payload size or type.' }
$payloadBytes = [IO.File]::ReadAllBytes($payloadPath)
$utf8 = [Text.UTF8Encoding]::new($false, $true)
$payloadText = $utf8.GetString($payloadBytes)
$domain = "MELANGE-DESKTOP-DIRECTORY-ZIP-V1`n"
if (-not $payloadText.StartsWith($domain, [StringComparison]::Ordinal)) { throw 'Invalid ZIP signing domain.' }
$identity = $payloadText.Substring($domain.Length) | ConvertFrom-Json
$expectedKeys = 'appId|version|platform|arch|format|entrypoint|name|size|sha256|sha512'
if (($identity.PSObject.Properties.Name -join '|') -cne $expectedKeys) { throw 'Unexpected package signing fields or order.' }
$products = @{melange='Melange'; mentat='Mentat'; terrier='Terrier'}
if (-not $products.ContainsKey($identity.appId) -or $identity.platform -cne 'win32' -or $identity.arch -cne 'x64' -or
    $identity.format -cne 'windows-directory-zip-v1' -or $identity.version -cnotmatch '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$' -or
    $identity.entrypoint -cne ($products[$identity.appId] + '.exe') -or $identity.name -cne ($identity.appId + '-' + $identity.version + '-win32-x64.zip') -or
    $identity.size -le 0 -or $identity.size -gt 21474836480 -or $identity.sha256 -cnotmatch '^[a-f0-9]{64}$' -or
    [Convert]::FromBase64String($identity.sha512).Length -ne 64) { throw 'Invalid ZIP package identity.' }
$certificate = Get-Item -LiteralPath ('Cert:\CurrentUser\My\' + $publisherPin)
if (-not $certificate.HasPrivateKey -or $certificate.Thumbprint -cne $publisherPin -or
    -not (Test-CodeSigningEku $certificate)) { throw 'Pinned code-signing certificate is unavailable.' }
$privateKey = [Security.Cryptography.X509Certificates.RSACertificateExtensions]::GetRSAPrivateKey($certificate)
if ($null -eq $privateKey) { throw 'Pinned certificate does not expose an RSA signing key.' }
try {
    $signature = $privateKey.SignData($payloadBytes, [Security.Cryptography.HashAlgorithmName]::SHA256, [Security.Cryptography.RSASignaturePadding]::Pkcs1)
    if (-not $privateKey.VerifyData($payloadBytes, $signature, [Security.Cryptography.HashAlgorithmName]::SHA256, [Security.Cryptography.RSASignaturePadding]::Pkcs1)) { throw 'ZIP signature self-verification failed.' }
    $proof = [ordered]@{
        schemaVersion = 1
        algorithm = 'rsa-sha256'
        certificateDer = [Convert]::ToBase64String($certificate.Export([Security.Cryptography.X509Certificates.X509ContentType]::Cert))
        signature = [Convert]::ToBase64String($signature)
    }
    $outputPath = [IO.Path]::GetFullPath($OutputFile)
    $stream = [IO.File]::Open($outputPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $encoded = $utf8.GetBytes(($proof | ConvertTo-Json -Compress)); $stream.Write($encoded, 0, $encoded.Length); $stream.Flush($true) }
    finally { $stream.Dispose() }
    Write-Output ('Publisher proof written: ' + $outputPath)
} finally { $privateKey.Dispose() }
