Lord of Apocalypse Recompiled - v0.9.0-beta.1 - Windows x64

1. Download Setup.exe from the matching GitHub release and run it. It downloads
   verified public build tools and generation instructions, without game files.
   Use an ASCII-only install path, e.g. C:\Games\LordOfApocalypse-Recomp.
2. Open LordOfApocalypse.exe and click Play. On first launch select your own
   unmodified Japanese PSP ISO (NPJH50503, disc 1.01). No ISO is supplied.
   You can also drag the ISO onto the EXE, then click Play.
3. First launch compiles the native Windows game and generates the WIP English
   image, subtitles and HD textures locally. Allow about 18 GB free disk space.
   This takes substantially longer than later launches: HD processing can take
   many minutes to several hours depending on your CPU and Vulkan graphics card.
   Progress appears in the launcher; completed generation stages can resume.
   Keep the launcher running. The original ISO is unchanged. Python, the portable
   compiler and runtime dependencies are included; no separate Git, compiler or
   emulator installation is required. All processing stays on your PC.
   First HD setup also downloads a hash-verified public texture tool directly
   from its publisher. Keep an internet connection available for this step.

Required ISO SHA256:
3a4d63713880dfb67ade00b6a912ac4975847cec06b1ab341b65963f328e1c93

Windows 10/11 x64 and a Vulkan-capable graphics driver are required. Windows N
editions need Microsoft's Media Feature Pack for movies. Direct Japanese play
also requires an ASCII-only original ISO path; English uses the prepared images.

F1 or Escape opens settings, networking, controls and tester support.
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
