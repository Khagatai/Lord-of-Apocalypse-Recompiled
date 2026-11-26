param([Parameter(Mandatory=$true)][string]$SchemaFile)
$ErrorActionPreference = 'Stop'
if (-not (Get-Command Test-Json -ErrorAction SilentlyContinue)) {
    throw 'Run this check in PowerShell 7, which supplies the JSON Schema validator.'
}
$manifest = Join-Path (Split-Path $PSScriptRoot -Parent) 'recomplauncher.json'
if (-not (Test-Json -LiteralPath $manifest -SchemaFile $SchemaFile -ErrorAction Stop)) {
    throw 'recomplauncher.json does not match the upstream schema.'
}
Write-Output 'PASS: recomplauncher.json matches the upstream JSON Schema.'
