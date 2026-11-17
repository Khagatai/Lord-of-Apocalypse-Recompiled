param([Parameter(Mandatory=$true)][string]$Draft,[Parameter(Mandatory=$true)][string]$Samples,[Parameter(Mandatory=$true)][string]$Bitmaps,[Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop';Add-Type -AssemblyName System.Drawing
$private=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../private'))+[IO.Path]::DirectorySeparatorChar
foreach($path in @($Draft,$Samples,$Bitmaps,$Output)){if(-not [IO.Path]::GetFullPath($path).StartsWith($private,[StringComparison]::OrdinalIgnoreCase)){throw 'Review inputs must remain private'}}
$out=[IO.Path]::GetFullPath($Output);if(Test-Path -LiteralPath $out){throw 'Use fresh private review output'}
New-Item -ItemType Directory -Path $out | Out-Null
$plan=Get-Content -LiteralPath $Draft -Raw -Encoding utf8 | ConvertFrom-Json
$assets=@{}
foreach($asset in (Get-Content -LiteralPath (Join-Path $Bitmaps 'render.json') -Raw -Encoding utf8 | ConvertFrom-Json).cues){$assets[[int]$asset.id]=$asset}
$sourceFrames=(Get-Content -LiteralPath (Join-Path $Samples 'frames.json') -Raw -Encoding utf8 | ConvertFrom-Json).frames
$font=[Drawing.Font]::new('Arial',10)
try {
 for($start=0;$start -lt $plan.cues.Count;$start+=6){
  $count=[Math]::Min(6,$plan.cues.Count-$start);$sheet=[Drawing.Bitmap]::new(960,$count*90);$g=[Drawing.Graphics]::FromImage($sheet)
  try {
   $g.Clear([Drawing.Color]::Black)
   for($j=0;$j -lt $count;$j++){
    $cue=$plan.cues[$start+$j];$y=$j*90
    $g.DrawString(('cue {0}: decoded frames {1}..{2}' -f $cue.id,$cue.first_frame,($cue.end_frame-1)),$font,[Drawing.Brushes]::Yellow,0,$y)
    $middle=([int]$cue.first_frame+[int]$cue.end_frame)/2
    $sample=$sourceFrames | Where-Object {$_.frame -ge $cue.first_frame -and $_.frame -lt $cue.end_frame} | Sort-Object { [Math]::Abs($_.frame-$middle) } | Select-Object -First 1
    if(-not $sample -or [IO.Path]::GetFileName([string]$sample.file) -ne [string]$sample.file){throw 'No valid source sample within caption interval'}
    $original=[Drawing.Image]::FromFile([IO.Path]::GetFullPath((Join-Path $Samples $sample.file)))
    $english=[Drawing.Image]::FromFile([IO.Path]::GetFullPath((Join-Path $Bitmaps ('cue-{0:D4}.png' -f [int]$cue.id))))
    $asset=$assets[[int]$cue.id]
    if(-not $asset -or $asset.y -lt 208 -or $asset.x -lt 0 -or $asset.x+$asset.width -gt 480 -or $asset.y+$asset.height -gt 272){throw 'Invalid caption plate placement'}
    try {$g.DrawImageUnscaled($original,0,$y+22);$g.DrawImageUnscaled($original,480,$y+22);$g.DrawImageUnscaled($english,480+[int]$asset.x,$y+22+[int]$asset.y-208)}finally{$original.Dispose();$english.Dispose()}
   }
   $sheet.Save((Join-Path $out ('sheet-{0:D3}.png' -f [int]($start/6))),[Drawing.Imaging.ImageFormat]::Png)
  }finally{$g.Dispose();$sheet.Dispose()}
 }
}finally{$font.Dispose()}
