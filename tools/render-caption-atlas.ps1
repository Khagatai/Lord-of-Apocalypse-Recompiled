param([Parameter(Mandatory=$true)][string]$Spec,[Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
$privateRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../private'))+[IO.Path]::DirectorySeparatorChar
$specPath=[IO.Path]::GetFullPath($Spec);$outputPath=[IO.Path]::GetFullPath($Output)
if (-not $specPath.StartsWith($privateRoot,[StringComparison]::OrdinalIgnoreCase) -or -not $outputPath.StartsWith($privateRoot,[StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $outputPath)) {throw 'Use a private caption specification and fresh private output'}
$plan=Get-Content -LiteralPath $specPath -Raw -Encoding utf8 | ConvertFrom-Json
if ($plan.width -lt 1 -or $plan.width -gt 1024 -or $plan.height -lt 1 -or $plan.height -gt 1024) {throw 'Invalid caption dimensions'}
$bitmap=[Drawing.Bitmap]::new($plan.width,$plan.height,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
$graphics=[Drawing.Graphics]::FromImage($bitmap)
$family=[Drawing.FontFamily]::new('Times New Roman')
$brush=[Drawing.SolidBrush]::new([Drawing.Color]::White)
$measurements=[Collections.Generic.List[object]]::new()
$groupRatios=@{}
try {
    $graphics.Clear([Drawing.Color]::Transparent)
    $graphics.SmoothingMode=[Drawing.Drawing2D.SmoothingMode]::AntiAlias
    # Split words share one horizontal scale, rather than stretching each cell
    # independently. This keeps letter proportions consistent after assembly.
    foreach ($block in $plan.blocks) {
        if (-not $block.fit_group -or -not $block.text) {continue}
        $probe=[Drawing.Drawing2D.GraphicsPath]::new();$probeFamily=$null
        try {
            $selectedFamily=$family
            if ($block.font_family) {$probeFamily=[Drawing.FontFamily]::new([string]$block.font_family);$selectedFamily=$probeFamily}
            $style=if($block.font_style){[int]$block.font_style}else{[int][Drawing.FontStyle]::Regular}
            $probe.AddString([string]$block.text,$selectedFamily,$style,64,[Drawing.PointF]::new(0,0),[Drawing.StringFormat]::GenericTypographic)
            $bounds=$probe.GetBounds()
            if ($bounds.Width -le 0 -or $bounds.Height -le 0 -or $block.height -le 0 -or $block.width -le 0) {throw 'Invalid grouped caption cell'}
            $ratio=[Math]::Min([double]1,([double]$block.width/$bounds.Width)/([double]$block.height/$bounds.Height))
            $key=[string]$block.fit_group
            if ($groupRatios.ContainsKey($key)) {$ratio=[Math]::Min($ratio,$groupRatios[$key])}
            $groupRatios[$key]=$ratio
        } finally {if($probeFamily){$probeFamily.Dispose()};$probe.Dispose()}
    }
    foreach ($block in $plan.blocks) {
        if (-not $block.text) {continue}
        $x=[double]$block.x;$y=[double]$block.y;$width=[double]$block.width;$height=[double]$block.height
        if ($x -lt 0 -or $y -lt 0 -or $width -le 0 -or $height -le 0 -or $x+$width -gt $bitmap.Width -or $y+$height -gt $bitmap.Height) {throw 'Caption cell exceeds atlas'}
        $path=[Drawing.Drawing2D.GraphicsPath]::new()
        $matrix=$null
        $localFamily=$null;$localBrush=$null;$outline=$null
        try {
            $selectedFamily=$family
            if ($block.font_family) {$localFamily=[Drawing.FontFamily]::new([string]$block.font_family);$selectedFamily=$localFamily}
            $style=if($block.font_style){[int]$block.font_style}else{[int][Drawing.FontStyle]::Regular}
            $path.AddString([string]$block.text,$selectedFamily,$style,64,[Drawing.PointF]::new(0,0),[Drawing.StringFormat]::GenericTypographic)
            $bounds=$path.GetBounds()
            if ($bounds.Width -le 0 -or $bounds.Height -le 0) {throw 'Caption has no visible glyphs'}
            $scaleY=$height/$bounds.Height
            $scaleX=[Math]::Min($scaleY,$width/$bounds.Width)
            if ($block.fit_group) {$scaleX=$scaleY*$groupRatios[[string]$block.fit_group]}
            $ratio=$scaleX/$scaleY
            if ($ratio -lt 0.25) {throw 'Caption would require excessive horizontal condensation'}
            $left=$x+($width-$bounds.Width*$scaleX)/2
            $matrix=[Drawing.Drawing2D.Matrix]::new($scaleX,0,0,$scaleY,$left-$bounds.X*$scaleX,$y-$bounds.Y*$scaleY)
            $path.Transform($matrix)
            $padding=0
            if ($block.outline_color) {
                if ($block.outline_width -le 0 -or $block.outline_width -gt 4) {throw 'Invalid caption outline width'}
                $padding=[double]$block.outline_width
                $outline=[Drawing.Pen]::new([Drawing.ColorTranslator]::FromHtml($block.outline_color),[single]$padding)
                $outline.LineJoin=[Drawing.Drawing2D.LineJoin]::Round
            }
            $graphics.SetClip([Drawing.RectangleF]::new($x-$padding,$y-$padding,$width+2*$padding,$height+2*$padding))
            if($outline){$graphics.DrawPath($outline,$path)}
            $selectedBrush=$brush
            if ($block.color) {$localBrush=[Drawing.SolidBrush]::new([Drawing.ColorTranslator]::FromHtml($block.color));$selectedBrush=$localBrush}
            $graphics.FillPath($selectedBrush,$path)
            $graphics.ResetClip()
            $measurements.Add(@{text=$block.text;ink_height=$height;ink_width=$bounds.Width*$scaleX;ink_x=$left;ink_y=$y;horizontal_ratio=$ratio;font_family=$selectedFamily.Name})
        } finally {if($matrix){$matrix.Dispose()};if($outline){$outline.Dispose()};if($localBrush){$localBrush.Dispose()};if($localFamily){$localFamily.Dispose()};$path.Dispose()}
    }
    New-Item -ItemType Directory -Path $outputPath | Out-Null
    $bitmap.Save((Join-Path $outputPath 'preview.png'),[Drawing.Imaging.ImageFormat]::Png)
    $locked=$bitmap.LockBits([Drawing.Rectangle]::new(0,0,$bitmap.Width,$bitmap.Height),[Drawing.Imaging.ImageLockMode]::ReadOnly,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
    try {
        if ($locked.Stride -ne $bitmap.Width*4) {throw 'Unsupported bitmap stride'}
        $pixels=[byte[]]::new($locked.Stride*$bitmap.Height)
        [Runtime.InteropServices.Marshal]::Copy($locked.Scan0,$pixels,0,$pixels.Length)
        for ($i=0;$i -lt $pixels.Length;$i+=4) {$red=$pixels[$i+2];$pixels[$i+2]=$pixels[$i];$pixels[$i]=$red}
        [IO.File]::WriteAllBytes((Join-Path $outputPath 'pixels.rgba'),$pixels)
    } finally {$bitmap.UnlockBits($locked)}
    @{scope='local-serif-caption-atlas';original_font_identified=$false;external_service_used=$false;cells=@($measurements.ToArray())} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $outputPath 'render.json') -Encoding utf8
} finally {$brush.Dispose();$family.Dispose();$graphics.Dispose();$bitmap.Dispose()}
