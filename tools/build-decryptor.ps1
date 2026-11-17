param([string]$DeveloperCommand = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\Tools\VsDevCmd.bat')
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$source = Join-Path $root 'private/tools/pspdecrypt'
$pin = 'c156627db7634d395c380c0a9589130f603307fc'
$actual = & git -c "safe.directory=$($source.Replace('\','/'))" -C $source rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $actual -ne $pin) { throw 'pspdecrypt revision mismatch' }
if (-not (Test-Path -LiteralPath $DeveloperCommand)) { throw 'Visual Studio C++ developer command unavailable' }
$output = Join-Path $root 'private/tools/decrypt-build'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$bridge = Join-Path $PSScriptRoot 'prx-decrypt.cpp'
$batch = @"
@echo off
call "$DeveloperCommand" -arch=x64 -host_arch=x64
if errorlevel 1 exit /b 1
cd /d "$output"
cl /nologo /O2 /MD /c "$source\libkirk\AES.c" "$source\libkirk\SHA1.c" "$source\libkirk\bn.c" "$source\libkirk\ec.c" "$source\libkirk\kirk_engine.c"
if errorlevel 1 exit /b 1
cl /nologo /O2 /MD /EHsc /std:c++17 /LD /I"$source" "$bridge" "$source\PrxDecrypter.cpp" AES.obj SHA1.obj bn.obj ec.obj kirk_engine.obj /link /OUT:prx-decrypt.dll
exit /b %errorlevel%
"@
$batchPath = Join-Path $output 'build.cmd'
[IO.File]::WriteAllText($batchPath, $batch, [Text.Encoding]::ASCII)
& cmd.exe /d /c $batchPath
if ($LASTEXITCODE -ne 0) { throw 'Local PRX decryptor build failed' }
