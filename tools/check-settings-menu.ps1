param([Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$privateRoot = (Join-Path $projectRoot 'private') + [IO.Path]::DirectorySeparatorChar
$outputPath = [IO.Path]::GetFullPath($Output)
if (-not $outputPath.StartsWith($privateRoot, [StringComparison]::OrdinalIgnoreCase) -or (Test-Path -LiteralPath $outputPath)) { throw 'Use a fresh private output directory' }
$preferences = Join-Path $privateRoot 'settings/graphics.json'
$before = if (Test-Path -LiteralPath $preferences) { (Get-FileHash -LiteralPath $preferences -Algorithm SHA256).Hash } else { '' }
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class MenuCheck {
    public delegate bool Visit(IntPtr window, IntPtr parameter);
    [StructLayout(LayoutKind.Sequential)] public struct Rect { public int left, top, right, bottom; }
    [DllImport("user32.dll")] public static extern bool EnumWindows(Visit visit, IntPtr p);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr w, out uint pid);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr w, StringBuilder name, int max);
    [DllImport("user32.dll")] public static extern IntPtr GetDlgItem(IntPtr w, int id);
    [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr w, uint m, IntPtr a, IntPtr b);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr w, out Rect r);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr w, IntPtr dc, uint flags);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr w, int mode);
    [DllImport("user32.dll")] public static extern bool RedrawWindow(IntPtr w, IntPtr rect, IntPtr region, uint flags);
    [DllImport("user32.dll")] public static extern IntPtr SetThreadDpiAwarenessContext(IntPtr context);
    public static IntPtr Find(uint pid) {
        IntPtr found = IntPtr.Zero;
        EnumWindows((w,p) => { uint owner; GetWindowThreadProcessId(w,out owner); var name=new StringBuilder(128); GetClassName(w,name,128); if(owner==pid && name.ToString()=="LordOfApocalypseGraphicsMenu") { found=w; return false; } return true; }, IntPtr.Zero);
        return found;
    }
}
'@
$oldDpi = [MenuCheck]::SetThreadDpiAwarenessContext([IntPtr](-4))
$program = Join-Path $privateRoot 'launcher/LordOfApocalypse-Launcher.exe'
$process = Start-Process -FilePath $program -WindowStyle Hidden -PassThru
try {
    if (-not $process.WaitForInputIdle(25000)) { throw 'Settings window did not become ready' }
    $window = [MenuCheck]::Find([uint32]$process.Id)
    if ($window -eq [IntPtr]::Zero) { throw 'Settings window was not found' }
    $checkboxes = @(5,6,7,9,10,13)
    $original = @()
    for ($index = 0; $index -lt 15; $index++) {
        $control = [MenuCheck]::GetDlgItem($window,200+$index)
        if ($control -eq [IntPtr]::Zero) { throw "Missing settings control $index" }
        $message = if ($checkboxes -contains $index) { 0xF0 } else { 0x147 }
        $original += [MenuCheck]::SendMessage($control,$message,[IntPtr]::Zero,[IntPtr]::Zero).ToInt32()
    }
    [void][MenuCheck]::SendMessage($window,0x111,[IntPtr]403,[IntPtr]::Zero)
    $expected = $original.Clone()
    $expected[1]=1; $expected[4]=0; $expected[5]=1; $expected[7]=0; $expected[8]=2
    $expected[9]=0; $expected[10]=0; $expected[11]=0; $expected[12]=0; $expected[13]=0
    $actual = @()
    for ($index = 0; $index -lt 15; $index++) {
        $control = [MenuCheck]::GetDlgItem($window,200+$index)
        $message = if ($checkboxes -contains $index) { 0xF0 } else { 0x147 }
        $actual += [MenuCheck]::SendMessage($control,$message,[IntPtr]::Zero,[IntPtr]::Zero).ToInt32()
        if ($actual[$index] -ne $expected[$index]) { throw "Balanced preset failed for control $index" }
    }
    New-Item -ItemType Directory -Path $outputPath | Out-Null
    [void][MenuCheck]::SendMessage($window,0x111,[IntPtr]405,[IntPtr]::Zero)
    $expected[1]=3; $expected[7]=1; $expected[8]=4
    $expected[9]=1; $expected[10]=1; $expected[11]=1; $expected[12]=3; $expected[13]=1
    for ($index = 0; $index -lt 15; $index++) {
        $control = [MenuCheck]::GetDlgItem($window,200+$index)
        $message = if ($checkboxes -contains $index) { 0xF0 } else { 0x147 }
        $value = [MenuCheck]::SendMessage($control,$message,[IntPtr]::Zero,[IntPtr]::Zero).ToInt32()
        if ($value -ne $expected[$index]) { throw "High Quality preset failed for control $index" }
    }
    # Hidden windows can report a successful PrintWindow with blank pixels.
    # Briefly show this owned menu without activating it before capturing.
    [void][MenuCheck]::ShowWindow($window,4)
    [void][MenuCheck]::RedrawWindow($window,[IntPtr]::Zero,[IntPtr]::Zero,0x581)
    $rect = New-Object MenuCheck+Rect
    if (-not [MenuCheck]::GetWindowRect($window,[ref]$rect)) { throw 'Could not read settings window bounds' }
    $bitmap = New-Object Drawing.Bitmap(($rect.right-$rect.left),($rect.bottom-$rect.top))
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    $dc = $graphics.GetHdc()
    try { if (-not [MenuCheck]::PrintWindow($window,$dc,2)) { throw 'Could not capture the real settings window' } }
    finally { $graphics.ReleaseHdc($dc); $graphics.Dispose() }
    try { $bitmap.Save((Join-Path $outputPath 'settings-menu.png'),[Drawing.Imaging.ImageFormat]::Png) }
    finally { $bitmap.Dispose() }
    [void][MenuCheck]::SendMessage($window,0x10,[IntPtr]::Zero,[IntPtr]::Zero)
    if (-not $process.WaitForExit(5000)) { throw 'Settings window did not close' }
    $after = if (Test-Path -LiteralPath $preferences) { (Get-FileHash -LiteralPath $preferences -Algorithm SHA256).Hash } else { '' }
    if ($before -ne $after) { throw 'UI preview changed saved preferences' }
    @{scope='native-settings-ui';controls_checked=15;balanced_preset='PASS';quality_preset='PASS';preferences_unchanged=$true;returncode=$process.ExitCode;balanced_codes=$actual;quality_codes=$expected} |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $outputPath 'result.json') -Encoding utf8
    Get-Content -LiteralPath (Join-Path $outputPath 'result.json')
} finally {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id }
    [void][MenuCheck]::SetThreadDpiAwarenessContext($oldDpi)
}
