$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$framework = Join-Path $root 'external/nakagawa-recomp'
$expected = '8704fba98007fff6d6f930365f2b2142af1bfbba'
$actual = & git -c "safe.directory=$($framework.Replace('\','/'))" -C $framework rev-parse HEAD
if ($LASTEXITCODE -ne 0 -or $actual -ne $expected) {
    throw "Framework revision mismatch: expected $expected; actual $actual"
}
Write-Output "Framework pin PASS: $actual"
$portablePython = Join-Path $root 'private/tools/python314/python.exe'
if (Test-Path -LiteralPath $portablePython) {
    & $portablePython --version
    if ($LASTEXITCODE -ne 0) { throw 'Portable Python failed to execute' }
}
foreach ($name in @('python', 'py', 'bash', 'gcc', 'g++', 'make', 'ld.lld', 'PPSSPPWindows64')) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if ($command) { Write-Output "$name PATH candidate: $($command.Source)" }
    else { Write-Output "$name missing from PATH" }
}
Write-Output 'PATH candidates are not native title toolchain validation. See docs/STATUS.md for actual evidence.'
