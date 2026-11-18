param(
    [string]$Recipes = (Join-Path $PSScriptRoot '../private/local-build/portable-text-recipes.json'),
    [string]$Output = (Join-Path $PSScriptRoot '../private/panel-layout-audit/lettering.json')
)
$ErrorActionPreference = 'Stop'
$privateRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../private')) + [IO.Path]::DirectorySeparatorChar
$outputPath = [IO.Path]::GetFullPath($Output)
if (-not $outputPath.StartsWith($privateRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Lettering reports must stay private' }
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
public static class LetteringInk {
    public static Rectangle Bounds(Bitmap bitmap) {
        var data = bitmap.LockBits(new Rectangle(0, 0, bitmap.Width, bitmap.Height), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
        try {
            var pixels = new byte[data.Stride * bitmap.Height];
            Marshal.Copy(data.Scan0, pixels, 0, pixels.Length);
            int left = bitmap.Width, top = bitmap.Height, right = 0, bottom = 0;
            for (int y = 0; y < bitmap.Height; y++) {
                for (int x = 0; x < bitmap.Width; x++) {
                    if (pixels[y * data.Stride + x * 4 + 3] == 0) continue;
                    left = System.Math.Min(left, x); top = System.Math.Min(top, y);
                    right = System.Math.Max(right, x + 1); bottom = System.Math.Max(bottom, y + 1);
                }
            }
            return right == 0 ? Rectangle.Empty : Rectangle.FromLTRB(left, top, right, bottom);
        } finally { bitmap.UnlockBits(data); }
    }
}
'@
$recipePlan = Get-Content -LiteralPath $Recipes -Raw -Encoding utf8 | ConvertFrom-Json
$records = [Collections.Generic.List[object]]::new()
$probe = [Drawing.Bitmap]::new(1, 1)
$measure = [Drawing.Graphics]::FromImage($probe)
$format = [Drawing.StringFormat]::GenericTypographic.Clone()
$format.FormatFlags = [Drawing.StringFormatFlags]::NoWrap
try {
    foreach ($job in $recipePlan.render_jobs.PSObject.Properties) {
        $definition = $job.Value
        $captionMetrics = @{}
        $groupRatios = @{}
        if ($definition.renderer -eq 'caption') {
            $captionIndex = 0
            foreach ($block in $definition.plan.blocks) {
                $familyName = if ($block.font_family) { [string]$block.font_family } else { 'Times New Roman' }
                $family = [Drawing.FontFamily]::new($familyName)
                $path = [Drawing.Drawing2D.GraphicsPath]::new()
                try {
                    if ($block.text) {
                        $style = if ($block.font_style) { [int]$block.font_style } else { 0 }
                        $path.AddString([string]$block.text,$family,$style,64,[Drawing.PointF]::new(0,0),[Drawing.StringFormat]::GenericTypographic)
                        $bounds=$path.GetBounds()
                        if ($bounds.Width -le 0 -or $bounds.Height -le 0 -or $block.width -le 0 -or $block.height -le 0) { throw 'Invalid caption diagnostic cell' }
                        $ratio=[Math]::Min([double]1,([double]$block.width/$bounds.Width)/([double]$block.height/$bounds.Height))
                        $captionMetrics[$captionIndex]=@{width=$bounds.Width;height=$bounds.Height;ratio=$ratio}
                        if ($block.fit_group) {
                            $key=[string]$block.fit_group
                            if ($groupRatios.ContainsKey($key)) { $ratio=[Math]::Min($ratio,$groupRatios[$key]) }
                            $groupRatios[$key]=$ratio
                        }
                    }
                } finally { $path.Dispose(); $family.Dispose() }
                $captionIndex++
            }
        }
        $blockIndex = 0
        foreach ($block in $definition.plan.blocks) {
            $record = [ordered]@{ job=$job.Name; block=$blockIndex; renderer=$definition.renderer }
            $blockIndex++
            if ($definition.renderer -ne 'regular') {
                $record.status = 'empty'
                if ($captionMetrics.ContainsKey($record.block)) {
                    $metrics=$captionMetrics[$record.block]
                    $ratio=if($block.fit_group){$groupRatios[[string]$block.fit_group]}else{$metrics.ratio}
                    $inkWidth=$metrics.width*$block.height/$metrics.height*$ratio
                    $record.horizontal_ratio=$ratio
                    $record.cell=@($block.x,$block.y,$block.width,$block.height)
                    $record.ink_width=$inkWidth
                    $outside=$block.x -lt 0 -or $block.y -lt 0 -or $block.x+$block.width -gt $definition.plan.width -or $block.y+$block.height -gt $definition.plan.height
                    $record.status=if($outside){'graphic-cell-exceeds-atlas'}elseif($ratio -lt 0.8){'horizontal-compression-needs-review'}else{'fits-graphic-cell'}
                }
                $records.Add([pscustomobject]$record)
                continue
            }
            $family = if ($block.font_family) { [string]$block.font_family } else { 'Arial' }
            $style = if ($block.bold) { [Drawing.FontStyle]::Bold } else { [Drawing.FontStyle]::Regular }
            $font = [Drawing.Font]::new($family, [single]$block.font_pixels, $style, [Drawing.GraphicsUnit]::Pixel)
            try {
                $record.requested_font_pixels = [double]$block.font_pixels
                if ($block.fit_single_line -and -not $block.ink_align) {
                    for ($size=[double]$block.font_pixels; $size -gt 6 -and $measure.MeasureString($block.paragraphs[0], $font, [int]::MaxValue, $format).Width -gt $block.width; $size-=0.25) {
                        $font.Dispose()
                        $font = [Drawing.Font]::new($family, [single]($size-0.25), $style, [Drawing.GraphicsUnit]::Pixel)
                    }
                }
                $record.actual_font_pixels = [double]$font.Size
                $lines = [Collections.Generic.List[string]]::new()
                foreach ($paragraph in $block.paragraphs) {
                    if ($lines.Count -gt 0) { $lines.Add('') }
                    $line = ''
                    foreach ($word in ($paragraph -split '\s+')) {
                        $candidate = if ($line) { $line+' '+$word } else { $word }
                        if (-not $block.ink_align -and $measure.MeasureString($candidate, $font, [int]::MaxValue, $format).Width -gt $block.width -and $line) {
                            $lines.Add($line); $line = $word
                        } else { $line = $candidate }
                    }
                    $lines.Add($line)
                }
                $maximumWidth = [double]$block.width
                foreach ($line in $lines) { $maximumWidth=[Math]::Max($maximumWidth,$measure.MeasureString($line,$font,[int]::MaxValue,$format).Width) }
                $canvasWidth = [int][Math]::Ceiling($maximumWidth+64)
                $canvasHeight = [int][Math]::Ceiling([Math]::Max($block.height,($lines.Count-1)*$block.line_height+$font.Height*3)+64)
                if ($canvasWidth -gt 8192 -or $canvasHeight -gt 8192) { throw 'Lettering probe exceeds diagnostic bounds' }
                $canvas = [Drawing.Bitmap]::new($canvasWidth,$canvasHeight,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
                $draw = [Drawing.Graphics]::FromImage($canvas)
                try {
                    $draw.TextRenderingHint = if ($definition.plan.hd_antialias) { [Drawing.Text.TextRenderingHint]::AntiAliasGridFit } else { [Drawing.Text.TextRenderingHint]::SingleBitPerPixelGridFit }
                    $row = 0
                    foreach ($line in $lines) {
                        $draw.DrawString($line,$font,[Drawing.Brushes]::White,[single]16,[single](16+$row*$block.line_height),$format)
                        $row++
                    }
                    $ink = [LetteringInk]::Bounds($canvas)
                    $left=$ink.Left-16; $top=$ink.Top-16
                    if ($block.ink_align) {
                        $left=0; $top=[int][Math]::Floor(($block.height-$ink.Height)/2)
                        if ($block.ink_align -eq 'baseline-left') {
                            $draw.Clear([Drawing.Color]::Transparent)
                            $draw.DrawString('H',$font,[Drawing.Brushes]::White,[single]4,[single]0,$format)
                            $baseline=[LetteringInk]::Bounds($canvas).Bottom
                            $wanted=if($null -ne $block.baseline){[int]$block.baseline}else{$block.height-3}
                            $top=$wanted-$baseline+$ink.Top-16
                        }
                    }
                    $record.rows=$lines.Count
                    $record.cell=@([int]$block.width,[int]$block.height)
                    $record.ink=@($left,$top,($left+$ink.Width),($top+$ink.Height))
                    $record.status=if($ink.IsEmpty){'empty'}elseif($left -lt 0 -or $top -lt 0 -or $left+$ink.Width -gt $block.width -or $top+$ink.Height -gt $block.height){'ink-exceeds-cell'}elseif($font.Size -lt $block.font_pixels){'font-reduction-needs-review'}else{'fits-cell'}
                } finally { $draw.Dispose(); $canvas.Dispose() }
                $records.Add([pscustomobject]$record)
            } finally { $font.Dispose() }
        }
    }
} finally { $format.Dispose(); $measure.Dispose(); $probe.Dispose() }
$summary = [ordered]@{}
foreach ($group in ($records | Group-Object status)) { $summary[$group.Name]=$group.Count }
$report = [ordered]@{ scope='UI lettering at recorded atlas cells'; recipe_sha256=(Get-FileHash -LiteralPath $Recipes -Algorithm SHA256).Hash.ToLowerInvariant(); summary=$summary; complete_visual_validation=$false; blocks=@($records) }
[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($outputPath)) | Out-Null
$report | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $outputPath -Encoding utf8
$summary | ConvertTo-Json
