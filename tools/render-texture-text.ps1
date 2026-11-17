param([Parameter(Mandatory=$true)][string]$Spec, [Parameter(Mandatory=$true)][string]$Output, [switch]$PngOnly, [switch]$Update)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$privateRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'private')) + [IO.Path]::DirectorySeparatorChar
$specPath = [IO.Path]::GetFullPath($Spec)
$outputPath = [IO.Path]::GetFullPath($Output)
if (-not $specPath.StartsWith($privateRoot, [StringComparison]::OrdinalIgnoreCase) -or
    -not $outputPath.StartsWith($privateRoot, [StringComparison]::OrdinalIgnoreCase) -or
    ((Test-Path -LiteralPath $outputPath) -and -not $Update)) { throw 'Use private paths and a fresh output, or explicit -Update' }
if(Test-Path -LiteralPath $outputPath) {
    if(([IO.File]::GetAttributes($outputPath) -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw 'Output cannot be a link'}
    $prior=Get-Content -LiteralPath (Join-Path $outputPath 'render.json') -Raw | ConvertFrom-Json
    if($prior.scope -ne 'local-text-typesetting'){throw 'Existing output is not owned by this renderer'}
    foreach($item in Get-ChildItem -LiteralPath $outputPath){if($item.PSIsContainer -or $item.Name -notin @('preview.png','pixels.rgba','render.json') -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Unexpected file in renderer output'}}
}
$plan = Get-Content -LiteralPath $specPath -Raw -Encoding utf8 | ConvertFrom-Json
$sourcePath = [IO.Path]::GetFullPath((Join-Path $projectRoot $plan.source_png))
if (-not $sourcePath.StartsWith($privateRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Source image must remain private' }
Add-Type -AssemblyName System.Drawing
function Get-LocalSHA256([string]$Path) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash([IO.File]::ReadAllBytes($Path))).Replace('-','').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}
$source = [Drawing.Bitmap]::FromFile($sourcePath)
$bitmap = New-Object Drawing.Bitmap($source.Width, $source.Height, [Drawing.Imaging.PixelFormat]::Format32bppArgb)
$graphics = [Drawing.Graphics]::FromImage($bitmap)
try {
    $graphics.DrawImageUnscaled($source, 0, 0)
    $graphics.TextRenderingHint = if ($plan.hd_antialias) { [Drawing.Text.TextRenderingHint]::AntiAliasGridFit } else { [Drawing.Text.TextRenderingHint]::SingleBitPerPixelGridFit }
    foreach ($block in $plan.blocks) {
        $rect = New-Object Drawing.Rectangle([int]$block.x, [int]$block.y, [int]$block.width, [int]$block.height)
        if ($rect.X -lt 0 -or $rect.Y -lt 0 -or $rect.Right -gt $bitmap.Width -or $rect.Bottom -gt $bitmap.Height) { throw 'Text region exceeds image' }
        $eraseRect=$rect
        if($block.erase_region) {
            if($block.erase_region.Count -ne 4){throw 'Invalid source lettering region'}
            $eraseRect=[Drawing.Rectangle]::new([int]$block.erase_region[0],[int]$block.erase_region[1],[int]$block.erase_region[2],[int]$block.erase_region[3])
            if($eraseRect.X -lt 0 -or $eraseRect.Y -lt 0 -or $eraseRect.Width -le 0 -or $eraseRect.Height -le 0 -or $eraseRect.Right -gt $bitmap.Width -or $eraseRect.Bottom -gt $bitmap.Height){throw 'Source lettering region exceeds image'}
        }
        $graphics.CompositingMode = [Drawing.Drawing2D.CompositingMode]::SourceCopy
        $background = if ($block.background) { [Drawing.ColorTranslator]::FromHtml($block.background) } else { [Drawing.Color]::Transparent }
        if ($block.erase_yellow_ink) {
            # Remove only measured caption ink over an illustration. Preserve
            # the source shading instead of clearing the whole caption cell.
            for ($eraseY=$rect.Y; $eraseY -lt $rect.Bottom; $eraseY++) {
                for ($eraseX=$rect.X; $eraseX -lt $rect.Right; $eraseX++) {
                    $pixel=$bitmap.GetPixel($eraseX,$eraseY)
                    $captionYellow=$pixel.R -ge 10 -and $pixel.G -ge $pixel.R*0.85 -and $pixel.B -lt $pixel.R*0.94
                    if ($captionYellow) {
                        $bitmap.SetPixel($eraseX,$eraseY,$background)
                    }
                }
            }
        } else {
            $clear = New-Object Drawing.SolidBrush($background)
            $graphics.FillRectangle($clear, $eraseRect)
            $clear.Dispose()
        }
        $graphics.CompositingMode = [Drawing.Drawing2D.CompositingMode]::SourceOver
        $style = if ($block.bold) { [Drawing.FontStyle]::Bold } else { [Drawing.FontStyle]::Regular }
        $family = if ($block.font_family) { [string]$block.font_family } else { 'Arial' }
        $font = New-Object Drawing.Font($family, [single]$block.font_pixels, $style, [Drawing.GraphicsUnit]::Pixel)
        $brush = New-Object Drawing.SolidBrush([Drawing.ColorTranslator]::FromHtml($block.color))
        $format = [Drawing.StringFormat]::GenericTypographic.Clone()
        $format.FormatFlags = [Drawing.StringFormatFlags]::NoWrap
        try {
            if ($block.ink_align) {
                if ($block.ink_align -notin @('centre-left','baseline-left') -or $block.paragraphs.Count -ne 1) { throw 'Ink alignment requires one explicitly positioned label' }
                # Place actual glyph ink, including overhangs, inside the measured
                # sprite cell. Never stretch a label or silently reduce its font.
                $measure=$graphics.MeasureString($block.paragraphs[0],$font,[int]::MaxValue,$format)
                $scratch=[Drawing.Bitmap]::new([int][Math]::Ceiling($measure.Width+12),[int][Math]::Ceiling($font.Height*3),[Drawing.Imaging.PixelFormat]::Format32bppArgb)
                $sg=[Drawing.Graphics]::FromImage($scratch)
                try {
                    $sg.TextRenderingHint=$graphics.TextRenderingHint
                    $sg.DrawString($block.paragraphs[0],$font,$brush,[single]4,[single]0,$format)
                    $left=$scratch.Width;$top=$scratch.Height;$right=0;$bottom=0
                    for($sy=0;$sy -lt $scratch.Height;$sy++) { for($sx=0;$sx -lt $scratch.Width;$sx++) {
                        if($scratch.GetPixel($sx,$sy).A -gt 0) {
                            $left=[Math]::Min($left,$sx);$top=[Math]::Min($top,$sy)
                            $right=[Math]::Max($right,$sx+1);$bottom=[Math]::Max($bottom,$sy+1)
                        }
                    }}
                    $iw=$right-$left;$ih=$bottom-$top
                    if($iw -le 0 -or $ih -le 0 -or $iw -gt $rect.Width -or $ih -gt $rect.Height) { throw ('Label needs a wider measured cell or shorter wording: '+$block.paragraphs[0]) }
                    $destY=$rect.Y+[int][Math]::Floor(($rect.Height-$ih)/2)
                    if($block.ink_align -eq 'baseline-left') {
                        # A shared baseline must not depend on whether a word
                        # contains descenders (Hair / Style, for example).
                        $reference=[Drawing.Bitmap]::new($scratch.Width,$scratch.Height,[Drawing.Imaging.PixelFormat]::Format32bppArgb)
                        $rg=[Drawing.Graphics]::FromImage($reference)
                        try {
                            $rg.TextRenderingHint=$graphics.TextRenderingHint
                            $rg.DrawString('H',$font,$brush,[single]4,[single]0,$format)
                            $baseline=0
                            for($ry=0;$ry -lt $reference.Height;$ry++){for($rx=0;$rx -lt $reference.Width;$rx++){if($reference.GetPixel($rx,$ry).A -gt 0){$baseline=[Math]::Max($baseline,$ry+1)}}}
                            $wanted=if($null -ne $block.baseline){[int]$block.baseline}else{$rect.Height-3}
                            $destY=$rect.Y+$wanted-$baseline+$top
                            if($destY -lt $rect.Y -or $destY+$ih -gt $rect.Bottom){throw ('Label baseline exceeds measured cell: '+$block.paragraphs[0])}
                        } finally {$rg.Dispose();$reference.Dispose()}
                    }
                    $destination=[Drawing.Rectangle]::new($rect.X,$destY,$iw,$ih)
                    $graphics.DrawImage($scratch,$destination,$left,$top,$iw,$ih,[Drawing.GraphicsUnit]::Pixel)
                } finally { $sg.Dispose();$scratch.Dispose() }
                continue
            }
            if ($block.fit_single_line) {
                if ($block.paragraphs.Count -ne 1) { throw 'Single-line fitting requires exactly one line' }
                if ($block.preserve_font_size -and $graphics.MeasureString($block.paragraphs[0], $font, [int]::MaxValue, $format).Width -gt $rect.Width) {
                    throw ('Translated label needs shorter wording at the original size: ' + $block.paragraphs[0])
                }
                for ($fitSize = [double]$block.font_pixels - 0.25; $fitSize -ge 6.0 -and $graphics.MeasureString($block.paragraphs[0], $font, [int]::MaxValue, $format).Width -gt $rect.Width; $fitSize -= 0.25) {
                    $font.Dispose()
                    $font = [Drawing.Font]::new($family, [single]$fitSize, $style, [Drawing.GraphicsUnit]::Pixel)
                }
                if ($graphics.MeasureString($block.paragraphs[0], $font, [int]::MaxValue, $format).Width -gt $rect.Width) { throw ('Translated label does not fit at the minimum readable size: ' + $block.paragraphs[0]) }
            }
            $lines = [Collections.Generic.List[string]]::new()
            foreach ($paragraph in $block.paragraphs) {
                if ($lines.Count -gt 0) { $lines.Add('') }
                $line = ''
                foreach ($word in ($paragraph -split '\s+')) {
                    $candidate = if ($line) { $line + ' ' + $word } else { $word }
                    if ($graphics.MeasureString($candidate, $font, [int]::MaxValue, $format).Width -gt $rect.Width) {
                        if (-not $line) { throw 'Unbreakable word exceeds pixel width' }
                        $lines.Add($line)
                        $line = $word
                    } else { $line = $candidate }
                }
                $lines.Add($line)
            }
            if ($lines.Count * [int]$block.line_height -gt $rect.Height) { throw 'Translated text exceeds its pixel-height region' }
            $lineY = $rect.Y
            foreach ($line in $lines) {
                $graphics.DrawString($line, $font, $brush, [single]$rect.X, [single]$lineY, $format)
                $lineY += [int]$block.line_height
            }
        } finally { $font.Dispose(); $brush.Dispose(); $format.Dispose() }
    }
    New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
    $bitmap.Save((Join-Path $outputPath 'preview.png'), [Drawing.Imaging.ImageFormat]::Png)
    if (-not $PngOnly) {
    $bounds = New-Object Drawing.Rectangle(0, 0, $bitmap.Width, $bitmap.Height)
    $locked = $bitmap.LockBits($bounds, [Drawing.Imaging.ImageLockMode]::ReadOnly, [Drawing.Imaging.PixelFormat]::Format32bppArgb)
    try {
        if ($locked.Stride -ne $bitmap.Width * 4) { throw 'Unsupported bitmap stride' }
        $pixels = [byte[]]::new($locked.Stride * $bitmap.Height)
        [Runtime.InteropServices.Marshal]::Copy($locked.Scan0, $pixels, 0, $pixels.Length)
        for ($index = 0; $index -lt $pixels.Length; $index += 4) {
            $red = $pixels[$index+2]; $pixels[$index+2] = $pixels[$index]; $pixels[$index] = $red
        }
        [IO.File]::WriteAllBytes((Join-Path $outputPath 'pixels.rgba'), $pixels)
    } finally { $bitmap.UnlockBits($locked) }
    }
    [ordered]@{scope='local-text-typesetting'; source_png_sha256=(Get-LocalSHA256 $sourcePath); spec_sha256=(Get-LocalSHA256 $specPath); width=$bitmap.Width; height=$bitmap.Height; external_service_used=$false} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputPath 'render.json') -Encoding utf8
} finally { $graphics.Dispose(); $bitmap.Dispose(); $source.Dispose() }
