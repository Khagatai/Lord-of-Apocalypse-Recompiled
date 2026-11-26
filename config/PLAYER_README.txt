Lord of Apocalypse Recompiled - Windows x64

Beta.8 English main-menu password codes are listed in config\Passwords.txt.
Smooth 360 camera is available in F1 > Controls > Camera rotation settings.

1. Download Setup.exe from the matching GitHub release and run it. It downloads
   verified public build tools and generation instructions, without game files.
   Use an ASCII-only install path, e.g. C:\Games\LordOfApocalypse-Recomp.
2. Open LordOfApocalypse.exe and click Play. On first launch select your own
   unmodified Japanese PSP ISO (NPJH50503, disc 1.01). No ISO is supplied.
   You can also drag the ISO onto the EXE, then click Play.
3. First launch compiles the native Windows game and generates the WIP English
   image and subtitles locally. Original textures are the default. Render scale,
   FSR, filtering and real-time 3D texture smoothing are still available.
   Progress appears in the launcher; completed generation stages can resume.
   Keep the launcher running. The original ISO is unchanged. Python, the portable
   compiler and runtime dependencies are included; no separate Git, compiler or
   emulator installation is required. All processing stays on your PC.
   No manual PowerShell command or saved execution-policy change is required
   for normal Windows first setup; the launcher handles its own render scripts.
4. To enable the optional English HD world/model pack, open Settings > Advanced,
   set Local HD pack (English) to On, save and click Play. You can also change
   it from F1 > Settings > Advanced and restart. The first HD build may take
   hours and downloads a verified public texture tool. Allow about 18 GB free
   disk space for installation and full HD setup. Completed batches resume.

Settings > Build controls first-run resource use. Set a maximum of 1-16 compiler
jobs, leave Auto to size the workload for this PC, or set a Windows memory cap.
The cap applies to each build stage's process tree and is separate from graphics
card memory. The launcher reports peak committed memory during setup.
Choose Fast HD processing for larger batches or Low memory for smaller batches
and fewer GPU workers. All profiles use the same texture quality.

When you click Play, the launcher checks for newer supported GitHub releases.
You can update or continue playing your installed version. Setup checks the
package files and keeps your saves, settings and ISO selection. A launcher-only
update can reuse a verified native build. A change to native build inputs can
require local recompilation. The first update from an older beta may also need
one build to establish the build fingerprint.

Required ISO SHA256:
3a4d63713880dfb67ade00b6a912ac4975847cec06b1ab341b65963f328e1c93

Windows 10/11 x64 and a Vulkan-capable graphics driver are required. Windows N
editions need Microsoft's Media Feature Pack for movies. Direct Japanese play
also requires an ASCII-only original ISO path; English uses the prepared images.

F1 or Escape opens settings, networking, controls and tester support.
Change gamepad bindings in F1 > Controls or Launcher Settings > Controls.
Camera rotation settings offer experimental smooth horizontal right-stick
rotation and adjustable speed. Vertical movement keeps the PSP camera positions.
Original PSP camera behaviour remains the default. Changes persist locally.
Launcher Settings > Locations can select a different original ISO or an existing
game installation folder. It remembers these choices without moving or copying
files. The selected installation's saves and settings are used. Select its root
folder containing tools, config and private. Empty folders are not installations.
Xbox and PlayStation controllers use SDL gamepad input. DualSense supports USB
and Bluetooth; pair it in Windows before playing. The launcher Controls page
shows both button layouts. Right stick controls the camera; D-pad keeps menus.
Graphics, language and controller choices save automatically. Some changes
require restarting; save in-game first. The launcher's basic-graphics checkbox
offers a troubleshooting preset. Open launcher log shows setup/startup errors.

Saves: private/memstick. Preferences: private/settings.
No saves or personal preferences are included. Language versions keep separate
save folders. Back up your saves before replacing an existing installation.

WIP English is the default; Japanese audio stays unchanged. For optional Steam
multiplayer both players need Steam running on separate accounts. Choose Steam
development test in F1 -> Networking. App ID 480 is a development identity.

This is a beta. Intermittent audio distortion, full campaign review and 60-FPS
co-op acceptance remain open. F1 -> Tester support can export a local bug report;
nothing is uploaded automatically. Include location, steps and 30/60-FPS choice.

Keep licence notices and the included public framework/build sources with the
installation. Do not upload the locally generated game executable, modules,
English ISO, subtitle bitmaps, HD textures, saves or personal settings to GitHub.
