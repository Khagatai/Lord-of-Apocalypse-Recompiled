param([Parameter(Mandatory=$true)][string]$Draft,[Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$privateRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../private'))+[IO.Path]::DirectorySeparatorChar
$draftPath=[IO.Path]::GetFullPath($Draft);$out=[IO.Path]::GetFullPath($Output)
if(-not $draftPath.StartsWith($privateRoot,[StringComparison]::OrdinalIgnoreCase) -or -not $out.StartsWith($privateRoot,[StringComparison]::OrdinalIgnoreCase)){throw 'Caption drafts and bitmaps must remain private'}
if(Test-Path -LiteralPath $out){
    $old=Get-Content -LiteralPath (Join-Path $out 'render.json') -Raw | ConvertFrom-Json
    if($old.scope -ne 'local-movie-caption-bitmaps'){throw 'Output is not an owned caption bitmap folder'}
} else {New-Item -ItemType Directory -Path $out | Out-Null}
$plan=Get-Content -LiteralPath $draftPath -Raw -Encoding utf8 | ConvertFrom-Json
$font=[Drawing.Font]::new('Arial',18,[Drawing.FontStyle]::Regular,[Drawing.GraphicsUnit]::Pixel)
$format=[Drawing.StringFormat]::GenericTypographic.Clone();$format.FormatFlags=[Drawing.StringFormatFlags]::NoWrap
$records=[Collections.Generic.List[object]]::new()
try {
    foreach($cue in $plan.cues){
        if($cue.id -lt 1 -or $cue.id -gt 2048 -or $cue.english_lines.Count -lt 1 -or $cue.english_lines.Count -gt 2){throw 'Invalid caption id or line count'}
        $bitmap=[Drawing.Bitmap]::new(448,48,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $g=[Drawing.Graphics]::FromImage($bitmap)
        try {
            $g.Clear([Drawing.Color]::Black);$g.TextRenderingHint=[Drawing.Text.TextRenderingHint]::AntiAliasGridFit
            $top=(48-$cue.english_lines.Count*22)/2
            foreach($line in $cue.english_lines){
                $size=$g.MeasureString($line,$font,[int]::MaxValue,$format)
                if($size.Width -gt 432){throw ('Caption needs shorter wording at fixed font size: '+$line)}
                $g.DrawString($line,$font,[Drawing.Brushes]::White,[single]((448-$size.Width)/2),[single]$top,$format)
                $top+=22
            }
            $stem='cue-{0:D4}' -f [int]$cue.id
            $bitmap.Save((Join-Path $out ($stem+'.png')),[Drawing.Imaging.ImageFormat]::Png)
            $lock=$bitmap.LockBits([Drawing.Rectangle]::new(0,0,448,48),[Drawing.Imaging.ImageLockMode]::ReadOnly,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
            try {
                if($lock.Stride -ne 448*4){throw 'Unsupported bitmap stride'}
                $pixels=[byte[]]::new(448*48*4);[Runtime.InteropServices.Marshal]::Copy($lock.Scan0,$pixels,0,$pixels.Length)
                for($i=0;$i -lt $pixels.Length;$i+=4){$r=$pixels[$i+2];$pixels[$i+2]=$pixels[$i];$pixels[$i]=$r}
                [IO.File]::WriteAllBytes((Join-Path $out ($stem+'.rgba')),$pixels)
            } finally {$bitmap.UnlockBits($lock)}
            $records.Add(@{id=[int]$cue.id;file=$stem+'.rgba';lines=$cue.english_lines;x=16;y=224;width=448;height=48})
        }finally{$g.Dispose();$bitmap.Dispose()}
    }
    @{scope='local-movie-caption-bitmaps';font_family=$font.FontFamily.Name;font_pixels=18;auto_shrink=$false;plate='opaque black to cover baked text';cues=@($records.ToArray())} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $out 'render.json') -Encoding utf8
} finally {$font.Dispose();$format.Dispose()}
