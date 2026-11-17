$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$pins = Get-Content -LiteralPath (Join-Path $projectRoot 'config/remaster-upscaler.json') -Raw | ConvertFrom-Json
$dependencyRoot = Join-Path $projectRoot 'private/tools/realesrgan-20220424'
$archive = Join-Path $dependencyRoot 'windows.zip'
$package = Join-Path $dependencyRoot 'package'
function Get-LocalSHA256([string]$Path) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash([IO.File]::ReadAllBytes($Path))).Replace('-','').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}
if (-not (Test-Path -LiteralPath $dependencyRoot)) { New-Item -ItemType Directory -Path $dependencyRoot | Out-Null }
if (-not (Test-Path -LiteralPath $archive)) {
    Invoke-WebRequest -Uri $pins.archive_url -OutFile $archive -TimeoutSec 60
}
if ((Get-LocalSHA256 $archive) -ne $pins.archive_sha256) { throw 'Official archive differs from the pinned downloaded bytes' }
if (-not (Test-Path -LiteralPath $package)) {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($archive)
    try {
        foreach ($entry in $zip.Entries) {
            $destination = [IO.Path]::GetFullPath((Join-Path $package $entry.FullName))
            if (-not $destination.StartsWith($package + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Archive entry escapes the private package' }
        }
    } finally { $zip.Dispose() }
    [IO.Compression.ZipFile]::ExtractToDirectory($archive,$package)
}
foreach ($entry in $pins.files.PSObject.Properties) {
    if ((Get-LocalSHA256 (Join-Path $package $entry.Name)) -ne $entry.Value) { throw ('Dependency identity differs: ' + $entry.Name) }
}
Write-Output ('Verified private offline upscaler: ' + $pins.release)
