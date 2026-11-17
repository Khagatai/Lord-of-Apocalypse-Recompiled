param(
    [Parameter(Mandatory = $true)][string]$ImagePath
)
$ErrorActionPreference = 'Stop'
$image = Get-Item -LiteralPath $ImagePath
if ($image.PSIsContainer) { throw 'Expected a disc-image file.' }
if ($image.Extension.ToLowerInvariant() -notin @('.iso', '.cso')) {
    throw 'Expected an unmodified ISO or CSO; content inspection remains pending.'
}
$initialSize = $image.Length
$initialWrite = $image.LastWriteTimeUtc
$sha1 = (Get-FileHash -LiteralPath $image.FullName -Algorithm SHA1).Hash.ToLowerInvariant()
$sha256 = (Get-FileHash -LiteralPath $image.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
$after = Get-Item -LiteralPath $image.FullName
if ($after.Length -ne $initialSize -or $after.LastWriteTimeUtc -ne $initialWrite) {
    throw 'Image changed during hashing; discard identity and retry with a stable file.'
}
$privateRoot = Join-Path $PSScriptRoot '../private'
New-Item -ItemType Directory -Path $privateRoot -Force | Out-Null
$report = [ordered]@{
    size = $initialSize
    sha1 = $sha1
    sha256 = $sha256
    status = 'hashed-only-disc-identity-and-module-survey-pending'
}
$json = $report | ConvertTo-Json
$json | Set-Content -LiteralPath (Join-Path $privateRoot 'image-hashes.json') -Encoding utf8
$json
