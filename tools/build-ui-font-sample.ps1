param([Parameter(Mandatory=$true)][string]$Job,[Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
function Get-SampleHash([string]$Path) {
 $sha=[Security.Cryptography.SHA256]::Create()
 try { return [BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($Path))).Replace('-','').ToLowerInvariant() }
 finally { $sha.Dispose() }
}
$privateRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../private'))+[IO.Path]::DirectorySeparatorChar
$jobPath=[IO.Path]::GetFullPath($Job)
$outputPath=[IO.Path]::GetFullPath($Output)
if (-not $jobPath.StartsWith($privateRoot,[StringComparison]::OrdinalIgnoreCase) -or
    -not $outputPath.StartsWith($privateRoot,[StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $outputPath)) { throw 'Use a private job and fresh private output directory' }
$specification=Get-Content -LiteralPath $jobPath -Raw | ConvertFrom-Json
$sourcePath=[IO.Path]::GetFullPath($specification.source)
if (-not $sourcePath.StartsWith($privateRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'Source texture must be private' }
$factor=[int]$specification.factor
if ($factor -lt 2 -or $factor -gt 4 -or $specification.key -notmatch '^[0-9a-fA-F]{24}$') { throw 'Invalid factor or texture key' }
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing @'
using System;
using System.Drawing;
public static class AtlasSample {
 public static Bitmap Replicate(Bitmap source,int factor) {
  var image=new Bitmap(source.Width*factor,source.Height*factor,System.Drawing.Imaging.PixelFormat.Format32bppArgb);
  for(int y=0;y<source.Height;y++) for(int x=0;x<source.Width;x++) {
   Color color=source.GetPixel(x,y);
   for(int dy=0;dy<factor;dy++) for(int dx=0;dx<factor;dx++) image.SetPixel(x*factor+dx,y*factor+dy,color);
  }
  return image;
 }
 public static int VerifyOutside(Bitmap source,Bitmap image,int factor,Rectangle[] changed) {
  int differences=0;
  for(int y=0;y<image.Height;y++) for(int x=0;x<image.Width;x++) {
   bool inside=false;
   foreach(var rectangle in changed) if(rectangle.Contains(x,y)) { inside=true; break; }
   if(!inside && image.GetPixel(x,y).ToArgb()!=source.GetPixel(x/factor,y/factor).ToArgb()) differences++;
  }
  return differences;
 }
}
'@
$source=[Drawing.Bitmap]::FromFile($sourcePath)
$image=$null
$graphics=$null
try {
 if ($source.Width*$factor -gt 2048 -or $source.Height*$factor -gt 2048) { throw 'Replacement exceeds renderer limit' }
 $image=[AtlasSample]::Replicate($source,$factor)
 $graphics=[Drawing.Graphics]::FromImage($image)
 $regions=@(if($specification.regions){$specification.regions}else{$specification})
 if($regions.Count -lt 1 -or $regions.Count -gt 64) { throw 'Use 1 to 64 explicit text regions' }
 $rectangles=[Collections.Generic.List[Drawing.Rectangle]]::new()
 foreach($entry in $regions) {
 $region=$entry.region
 $ink=$entry.ink
 $rectangle=[Drawing.Rectangle]::new([int]($region.x*$factor),[int]($region.y*$factor),[int]($region.width*$factor),[int]($region.height*$factor))
 if ($rectangle.Width -le 0 -or $rectangle.Height -le 0 -or $rectangle.X -lt 0 -or $rectangle.Y -lt 0 -or $rectangle.Right -gt $image.Width -or $rectangle.Bottom -gt $image.Height) { throw 'Changed region outside atlas' }
 if(-not $entry.paragraphs -and ($ink.width -le 0 -or $ink.height -le 0 -or $ink.x -lt $region.x -or $ink.y -lt $region.y -or $ink.x+$ink.width -gt $region.x+$region.width -or $ink.y+$ink.height -gt $region.y+$region.height)) { throw 'Text ink bounds outside selected region' }
 $rectangles.Add($rectangle)
 $graphics.SetClip($rectangle)
 $graphics.CompositingMode=[Drawing.Drawing2D.CompositingMode]::SourceCopy
 $graphics.FillRectangle([Drawing.Brushes]::Transparent,$rectangle)
 $graphics.CompositingMode=[Drawing.Drawing2D.CompositingMode]::SourceOver
 $graphics.SmoothingMode=[Drawing.Drawing2D.SmoothingMode]::AntiAlias
 $face=if($entry.font){[string]$entry.font}else{[string]$specification.font}
 $family=[Drawing.FontFamily]::new($face)
 $path=[Drawing.Drawing2D.GraphicsPath]::new()
 $matrix=[Drawing.Drawing2D.Matrix]::new()
 $stroke=if($null -ne $entry.outline_pixels){[single]$entry.outline_pixels}else{[single]0.6}
 if($stroke -lt 0 -or $stroke -gt 2){throw 'Outline width must be within 0 to 2 source pixels'}
 $pen=[Drawing.Pen]::new([Drawing.Color]::Black,[single]([Math]::Max(0.01,$stroke)*$factor))
 try {
  if($entry.paragraphs) {
   $wrapWidth=if($entry.wrap_width){[single]$entry.wrap_width}else{[single]$region.width}
   if($wrapWidth -le 0 -or $wrapWidth -gt $region.width){throw 'Paragraph wrap width exceeds cleared region'}
   $style=if($entry.bold){[Drawing.FontStyle]::Bold}else{[Drawing.FontStyle]::Regular}
   $font=[Drawing.Font]::new($family,[single]$entry.font_pixels,$style,[Drawing.GraphicsUnit]::Pixel)
   $layout=[Drawing.Graphics]::FromImage($source)
   $brush=[Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml([string]$entry.color))
   $format=[Drawing.StringFormat]::GenericTypographic.Clone()
   $format.FormatFlags=[Drawing.StringFormatFlags]::NoWrap
   try {
    $layout.TextRenderingHint=[Drawing.Text.TextRenderingHint]::SingleBitPerPixelGridFit
    $lines=[Collections.Generic.List[string]]::new()
    foreach($paragraph in $entry.paragraphs) {
     if($lines.Count -gt 0){$lines.Add('')}
     $line=''
     foreach($word in ($paragraph -split '\s+')) {
      $candidate=if($line){$line+' '+$word}else{$word}
      if($layout.MeasureString($candidate,$font,[int]::MaxValue,$format).Width -gt $wrapWidth) {
       if(-not $line){throw 'Unbreakable word outside text region'}
       $lines.Add($line);$line=$word
      }else{$line=$candidate}
     }
     $lines.Add($line)
    }
    if($entry.line_height -le 0 -or $lines.Count*$entry.line_height -gt $region.height){throw 'Paragraph layout exceeds text region'}
    $lineY=[single]$region.y
    foreach($line in $lines) {
     if($line){$path.AddString($line,$family,[int]$style,[single]$entry.font_pixels,[Drawing.PointF]::new([single]$region.x,$lineY),$format)}
     $lineY += [single]$entry.line_height
    }
    $matrix.Scale($factor,$factor)
    $path.Transform($matrix)
    $graphics.FillPath($brush,$path)
   }finally{$format.Dispose();$brush.Dispose();$layout.Dispose();$font.Dispose()}
  }else{
  $textStyle=if($entry.bold -eq $false){[int][Drawing.FontStyle]::Regular}else{[int][Drawing.FontStyle]::Bold}
  if($entry.italic){$textStyle=$textStyle -bor [int][Drawing.FontStyle]::Italic}
  $path.AddString([string]$entry.text,$family,$textStyle,[single]100,[Drawing.PointF]::new(0,0),[Drawing.StringFormat]::GenericTypographic)
  $bounds=$path.GetBounds()
  if ($bounds.Width -le 0 -or $bounds.Height -le 0) { throw 'No text outline generated' }
  $matrix.Translate(-$bounds.X,-$bounds.Y,[Drawing.Drawing2D.MatrixOrder]::Append)
  $matrix.Scale([single]($ink.width*$factor/$bounds.Width),[single]($ink.height*$factor/$bounds.Height),[Drawing.Drawing2D.MatrixOrder]::Append)
  $matrix.Translate([single]($ink.x*$factor),[single]($ink.y*$factor),[Drawing.Drawing2D.MatrixOrder]::Append)
  $path.Transform($matrix)
  if($stroke -gt 0){$graphics.DrawPath($pen,$path)}
  $graphics.FillPath([Drawing.Brushes]::White,$path)
  }
 } finally { $pen.Dispose();$matrix.Dispose();$path.Dispose();$family.Dispose() }
 }
 $graphics.Dispose();$graphics=$null
 $outside=[AtlasSample]::VerifyOutside($source,$image,$factor,$rectangles.ToArray())
 if ($outside -ne 0) { throw "Unexpected pixel changes outside selected region: $outside" }
 New-Item -ItemType Directory -Path $outputPath | Out-Null
 $target=Join-Path $outputPath 'ui-sample.png'
 $image.Save($target,[Drawing.Imaging.ImageFormat]::Png)
 @("[options]","hash = quick","[games]","NPJH50503 = Lord of Apocalypse","[hashes]","$($specification.key) = ui-sample.png") |
   Set-Content -LiteralPath (Join-Path $outputPath 'textures.ini') -Encoding ascii
 $scope=if($regions.Count -eq 1){'one-region-vector-typeset-ui-sample'}else{'multi-region-vector-typeset-ui-sample'}
 @{scope=$scope;region_count=$regions.Count;source_sha256=(Get-SampleHash $sourcePath);
   png_sha256=(Get-SampleHash $target);
   ini_sha256=(Get-SampleHash (Join-Path $outputPath 'textures.ini'));
   width=$image.Width;height=$image.Height;factor=$factor;outside_region_changed_pixels=$outside;source_job_sha256=(Get-SampleHash $jobPath);
   complete_hd_pack=$false;visual_quality_validated=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputPath 'sample.json') -Encoding utf8
 Get-Content -LiteralPath (Join-Path $outputPath 'sample.json')
} finally { if($graphics){$graphics.Dispose()}; if($image){$image.Dispose()};$source.Dispose() }
