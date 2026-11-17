param([Parameter(Mandatory=$true)][long]$Window, [Parameter(Mandatory=$true)][uint32]$Owner, [Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference='Stop'
$privateRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../private')) + [IO.Path]::DirectorySeparatorChar
$outputPath = [IO.Path]::GetFullPath($Output)
if (-not $outputPath.StartsWith($privateRoot,[StringComparison]::OrdinalIgnoreCase)) { throw 'Captures must stay private' }
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class OwnedCapture {
 [StructLayout(LayoutKind.Sequential)] public struct Rect { public int left,top,right,bottom; }
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr w,out uint pid);
 [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr w,out Rect r);
 [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr w,IntPtr dc,uint flags);
 [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr c);
}
'@
$handle=[IntPtr]$Window
$actualOwner=[uint32]0
[void][OwnedCapture]::GetWindowThreadProcessId($handle,[ref]$actualOwner)
if ($actualOwner -ne $Owner) { throw 'Window ownership mismatch' }
$previous=[OwnedCapture]::SetThreadDpiAwarenessContext([IntPtr](-4))
try {
 $rect=New-Object OwnedCapture+Rect
 if (-not [OwnedCapture]::GetWindowRect($handle,[ref]$rect)) { throw 'Window bounds unavailable' }
 $bitmap=New-Object Drawing.Bitmap(($rect.right-$rect.left),($rect.bottom-$rect.top))
 $graphics=[Drawing.Graphics]::FromImage($bitmap)
 $dc=$graphics.GetHdc()
 try { if (-not [OwnedCapture]::PrintWindow($handle,$dc,2)) { throw 'Window capture failed' } }
 finally { $graphics.ReleaseHdc($dc); $graphics.Dispose() }
 try { $bitmap.Save($outputPath,[Drawing.Imaging.ImageFormat]::Png) }
 finally { $bitmap.Dispose() }
} finally { [void][OwnedCapture]::SetThreadDpiAwarenessContext($previous) }
