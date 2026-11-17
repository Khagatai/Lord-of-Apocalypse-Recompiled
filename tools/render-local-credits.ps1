param([Parameter(Mandatory=$true)][string]$Plan,[Parameter(Mandatory=$true)][string]$Lines,[Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../private'))+[IO.Path]::DirectorySeparatorChar
foreach($path in @($Plan,$Lines,$Output)){if(-not [IO.Path]::GetFullPath($path).StartsWith($root,[StringComparison]::OrdinalIgnoreCase)){throw 'Credit input/output must remain private'}}
if(Test-Path -LiteralPath $Output){throw 'Use a fresh credit output'}
New-Item -ItemType Directory -Path $Output -Force|Out-Null
$planData=Get-Content -LiteralPath $Plan -Raw -Encoding utf8|ConvertFrom-Json
$font=[Drawing.Font]::new('Times New Roman',11,[Drawing.FontStyle]::Bold,[Drawing.GraphicsUnit]::Pixel)
$format=[Drawing.StringFormat]::GenericTypographic.Clone();$format.FormatFlags=[Drawing.StringFormatFlags]::NoWrap
try{
 for($page=0;$page -lt $planData.pages.Count;$page++){
  $bitmap=[Drawing.Bitmap]::new(480,272,[Drawing.Imaging.PixelFormat]::Format32bppArgb);$g=[Drawing.Graphics]::FromImage($bitmap)
  try{
   $g.Clear([Drawing.Color]::Black);$g.TextRenderingHint=[Drawing.Text.TextRenderingHint]::AntiAliasGridFit
   foreach($row in $planData.pages[$page]){
    $original=[Drawing.Image]::FromFile((Join-Path $Lines ('line-{0:D3}.png' -f [int]$row.id)))
    try{$g.DrawImageUnscaled($original,0,[int]$row.page_y)}finally{$original.Dispose()}
    if($row.translation){
     $limit=if($row.mode -eq 'center'){480}else{242};$g.FillRectangle([Drawing.Brushes]::Black,0,[int]$row.page_y,$limit,[int]$row.height)
     $size=$g.MeasureString($row.translation,$font,[int]::MaxValue,$format)
     if($size.Width -gt $limit-8){throw 'Credit label exceeds its measured width'}
     $x=if($row.mode -eq 'center'){(480-$size.Width)/2}else{238-$size.Width}
     $g.DrawString($row.translation,$font,[Drawing.Brushes]::White,[single]$x,[single]($row.page_y-2),$format)
    }
   }
   $lock=$bitmap.LockBits([Drawing.Rectangle]::new(0,0,480,272),[Drawing.Imaging.ImageLockMode]::ReadOnly,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
   try{
    $pixels=[byte[]]::new(480*272*4);[Runtime.InteropServices.Marshal]::Copy($lock.Scan0,$pixels,0,$pixels.Length)
    for($i=0;$i -lt $pixels.Length;$i+=4){$r=$pixels[$i+2];$pixels[$i+2]=$pixels[$i];$pixels[$i]=$r}
    [IO.File]::WriteAllBytes((Join-Path $Output ('cue-{0:D4}.rgba' -f ($page+1))),$pixels)
   }finally{$bitmap.UnlockBits($lock)}
  }finally{$g.Dispose();$bitmap.Dispose()}
 }
}finally{$font.Dispose();$format.Dispose()}
