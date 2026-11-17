param()
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
Add-Type -AssemblyName System.Drawing
while($null -ne ($line=[Console]::In.ReadLine())) {
    $id=-1
    try {
        $request=$line | ConvertFrom-Json
        $id=[int]$request.id
        if($id -lt 1 -or $request.script -notin @('render-texture-text.ps1','render-caption-atlas.ps1')){throw 'Invalid local render request'}
        # Each renderer retains its own private-path, edit-region and source guards.
        & (Join-Path $PSScriptRoot $request.script) -Spec ([string]$request.spec) -Output ([string]$request.output) | Out-Null
        $result=@{id=$id;ok=$true}
    } catch { $result=@{id=$id;ok=$false;error=$_.Exception.Message} }
    [Console]::Out.WriteLine('LOA_RENDER_RESULT '+($result | ConvertTo-Json -Compress))
    [Console]::Out.Flush()
}
