param([Parameter(Mandatory=$true)][string]$Frames,[Parameter(Mandatory=$true)][string]$Output,[switch]$Update)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$privateRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../private'))+[IO.Path]::DirectorySeparatorChar
$inputPath=[IO.Path]::GetFullPath($Frames);$out=[IO.Path]::GetFullPath($Output)
if(-not $inputPath.StartsWith($privateRoot,[StringComparison]::OrdinalIgnoreCase) -or -not $out.StartsWith($privateRoot,[StringComparison]::OrdinalIgnoreCase) -or ((Test-Path -LiteralPath $out) -and -not $Update)){throw 'Use private frames and explicit -Update for an existing review'}
if(Test-Path -LiteralPath $out){
    if(([IO.File]::GetAttributes($out) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Review output cannot be a link'}
    foreach($item in Get-ChildItem -LiteralPath $out){if($item.Name -notmatch '^sheet-[0-9]{3}\.png$|^review\.json$' -or $item.PSIsContainer){throw 'Output contains files not owned by this reviewer'}}
}
$plan=Get-Content -LiteralPath $inputPath -Raw -Encoding utf8 | ConvertFrom-Json
New-Item -ItemType Directory -Path $out -Force | Out-Null
$root=Split-Path -Parent $inputPath
$font=[Drawing.Font]::new('Arial',11)
try {
    for($start=0;$start -lt $plan.frames.Count;$start+=32){
        $count=[Math]::Min(32,$plan.frames.Count-$start)
        $sheet=[Drawing.Bitmap]::new(1920,([int][Math]::Ceiling($count/4.0)*88))
        $g=[Drawing.Graphics]::FromImage($sheet)
        try {
            $g.Clear([Drawing.Color]::Black)
            for($j=0;$j -lt $count;$j++){
                $row=$plan.frames[$start+$j];$x=($j%4)*480;$y=[Math]::Floor($j/4)*88
                $g.DrawString(('frame {0}, {1:N2}s' -f $row.frame,(($row.frame-1)*1001/30000)),$font,[Drawing.Brushes]::Yellow,$x,$y)
                if([IO.Path]::GetFileName([string]$row.file) -ne [string]$row.file){throw 'Invalid sample filename'}
                $im=[Drawing.Image]::FromFile((Join-Path $root $row.file))
                try {$g.DrawImageUnscaled($im,$x,$y+22)} finally {$im.Dispose()}
            }
            $sheet.Save((Join-Path $out ('sheet-{0:D3}.png' -f ([int]($start/32)))),[Drawing.Imaging.ImageFormat]::Png)
        } finally {$g.Dispose();$sheet.Dispose()}
    }
    @{scope='local-caption-review-sheets';frames_sha256=(Get-FileHash -LiteralPath $inputPath -Algorithm SHA256).Hash.ToLowerInvariant();samples=$plan.frames.Count} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $out 'review.json') -Encoding utf8
} finally {$font.Dispose()}
