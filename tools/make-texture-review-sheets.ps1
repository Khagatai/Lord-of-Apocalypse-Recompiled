param(
    [Parameter(Mandatory=$true)][string]$Inventory,
    [Parameter(Mandatory=$true)][string]$Output,
    [string[]]$ExcludeReview = @()
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$privateRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../private')) + [IO.Path]::DirectorySeparatorChar
$inventoryRoot = (Resolve-Path -LiteralPath $Inventory).Path
$outputRoot = [IO.Path]::GetFullPath($Output)
if (-not $inventoryRoot.StartsWith($privateRoot, [StringComparison]::OrdinalIgnoreCase) -or
    -not $outputRoot.StartsWith($privateRoot, [StringComparison]::OrdinalIgnoreCase) -or
    (Test-Path -LiteralPath $outputRoot)) { throw 'Use an existing private inventory and fresh private output folder' }
$rows = Get-Content -LiteralPath (Join-Path $inventoryRoot 'textures.json') -Raw | ConvertFrom-Json
$seen = @{}
$excluded = @{}
foreach ($reviewPath in $ExcludeReview) {
    $resolved = (Resolve-Path -LiteralPath $reviewPath).Path
    if (-not $resolved.StartsWith($privateRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Review references must remain private' }
    $review = Get-Content -LiteralPath $resolved -Raw | ConvertFrom-Json
    foreach ($entry in $review.images) { $excluded[$entry.png_sha256] = $true }
}
$images = [Collections.Generic.List[object]]::new()
foreach ($row in $rows) {
    foreach ($texture in $row.textures) {
        if (-not $texture.preview) { continue }
        $path = [IO.Path]::GetFullPath((Join-Path $inventoryRoot $texture.preview))
        if (-not $path.StartsWith($inventoryRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw 'Preview escapes inventory' }
        $hasher = [Security.Cryptography.SHA256]::Create()
        try { $hash = [BitConverter]::ToString($hasher.ComputeHash([IO.File]::ReadAllBytes($path))).Replace('-','').ToLowerInvariant() }
        finally { $hasher.Dispose() }
        if ($excluded.ContainsKey($hash)) { continue }
        $reference = @{resource_id=$row.resource_id; resource_sha256=$row.sha256; name=$texture.name; preview=$texture.preview}
        if ($seen.ContainsKey($hash)) { $seen[$hash].references.Add($reference); continue }
        $entry = @{number=$images.Count; png_sha256=$hash; references=[Collections.Generic.List[object]]::new(); review='unreviewed'}
        $entry.references.Add($reference)
        $seen[$hash]=$entry
        $images.Add($entry)
    }
}
New-Item -ItemType Directory -Path $outputRoot | Out-Null
$font = [Drawing.Font]::new('Arial',10)
$brush = [Drawing.SolidBrush]::new([Drawing.Color]::White)
try {
    for ($start=0; $start -lt $images.Count; $start+=30) {
        $bitmap = [Drawing.Bitmap]::new(1280,1740)
        $graphics = [Drawing.Graphics]::FromImage($bitmap)
        try {
            $graphics.Clear([Drawing.Color]::FromArgb(50,50,50))
            $graphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::NearestNeighbor
            for ($cell=0; $cell -lt 30 -and $start+$cell -lt $images.Count; $cell++) {
                $entry=$images[$start+$cell]
                $reference=$entry.references[0]
                $x=($cell%5)*256; $y=[Math]::Floor($cell/5)*290
                $graphics.DrawString(('{0}: {1}' -f $entry.number,$reference.name),$font,$brush,$x+4,$y+3)
                $graphics.DrawString($reference.resource_id,$font,$brush,$x+4,$y+20)
                $source=[Drawing.Image]::FromFile((Join-Path $inventoryRoot $reference.preview))
                try {
                    $scale=[Math]::Min(240.0/$source.Width,240.0/$source.Height)
                    $graphics.DrawImage($source,[Drawing.Rectangle]::new($x+8,$y+44,[int]($source.Width*$scale),[int]($source.Height*$scale)))
                } finally { $source.Dispose() }
                $entry.sheet=('sheet-{0:D3}.png' -f [int]($start/30))
            }
            $bitmap.Save((Join-Path $outputRoot ('sheet-{0:D3}.png' -f [int]($start/30))),[Drawing.Imaging.ImageFormat]::Png)
        } finally { $graphics.Dispose(); $bitmap.Dispose() }
    }
} finally { $font.Dispose(); $brush.Dispose() }
@{scope='private-texture-review-sheets'; inventory=$inventoryRoot; unique_images=$images.Count; visual_audit_complete=$false; images=@($images.ToArray())} |
    ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $outputRoot 'review.json') -Encoding utf8
Write-Output ('Prepared {0} unique private images; visual review remains required.' -f $images.Count)
