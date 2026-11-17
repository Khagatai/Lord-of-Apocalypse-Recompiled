param([string]$MSBuild = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\MSBuild\Current\Bin\MSBuild.exe')
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$source = Join-Path $root 'private/tools/ppsspp'
$pin = '1aebad2c651ff9d0684ee335e43aceff8fc7e3ec'
$actual = & git -c "safe.directory=$($source.Replace('\','/'))" -C $source rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $actual -ne $pin) { throw 'PPSSPP revision mismatch' }
if (-not (Test-Path -LiteralPath $MSBuild)) { throw 'Visual Studio MSBuild unavailable' }
$log = Join-Path $root 'private/ppsspp-build.log'
Push-Location $source
try {
    & $MSBuild Windows/PPSSPP.sln /t:PPSSPPHeadless /p:Configuration=Release /p:Platform=x64 /p:PreferredToolArchitecture=x64 /p:CL_MPCount=4 /m:4 /verbosity:minimal /nologo *> $log
    if ($LASTEXITCODE -ne 0) { throw "PPSSPP build failed; see $log" }
} finally { Pop-Location }
Write-Output "PPSSPP headless oracle built; log: $log"
