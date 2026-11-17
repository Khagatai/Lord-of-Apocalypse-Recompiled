# Credits and licensing

Active framework: Jstar269/Nakagawa-Recomp, GPL-3.0-or-later, pinned to
`8704fba98007fff6d6f930365f2b2142af1bfbba`. See its LICENSE, NOTICE.md, CREDITS.md
and third-party notices. Root LICENSE is GPLv3; redistributed combined
executables require corresponding source and applicable notices. No title
executable is approved for redistribution.

The original Tzeentchnet/psp-recomp gitlink (GPL-2.0-or-later) remains for
historical reproduction. It is no longer the active title runtime.

Original title-project scripts and documentation are GPL-2.0-or-later.
The title-owned `tools/in-game-settings.c` host overlay extension was written
with Codex and is GPL-3.0-or-later, as marked in that file.
Game content is user-supplied and is not distributed by this project.

Optional online networking loads native libdatachannel v0.24.6 at
`6b1e2e620f1e37f0eafeee702eaea0043cb305fd` (MPL-2.0), its pinned libjuice
(MPL-2.0), usrsctp (BSD) and plog (MIT) dependencies, and Mbed TLS 3.6.5 at
`e185d7fd85499c8ce5ca2a54f5cf8fe7dbe3f8df` (Apache-2.0 or GPL-2.0-or-later).
Their sources, licenses and binaries remain in ignored `private/`; keep their
upstream notices with any separately packaged native dependency. Reproduction
pins are in `config/online-dependencies.json`. The title-owned IPC/transport C
sources are GPL-3.0-or-later. No Epic Online Services SDK is installed.

The user supplied the official Steamworks SDK 1.65 ZIP for App ID 480 development
testing. SDK files, headers and `steam_api64.dll` remain ignored under `private/`
and are not bundled in the Git source tree. Original `tools/steam_bridge.cpp`
and `tools/steam_flat.h` are MIT-licensed adapter code and compile into a separate
helper-loaded DLL, not the native recomp executable. SDK use and any distribution
of its redistributables are governed by Valve's SDK agreement. Intake and build
fingerprints are retained privately. No endorsement by Valve is implied.

The user's local English v1.6 package credits Serberker, Sabaku.D.Tonio, Jinouga
and Square Enix. Its patch and translated game content remain private and are
not covered by this project's script license. Local patch decoding uses the
official GPL xdelta 3.0.11 utility; see docs/TRANSLATION.md for source and hashes.

Local analysis uses John-K/pspdecrypt, revision
`c156627db7634d395c380c0a9589130f603307fc` (project GPLv3, with PPSSPP/libkirk
notices in its source), and a separate PPSSPP headless oracle, revision
`1aebad2c651ff9d0684ee335e43aceff8fc7e3ec` (GPL-2.0-or-later and its dependency
licenses). These downloaded trees and compiled tools remain in ignored
`private/tools/`; they are not linked into a title executable or redistributed.
Portable CPython 3.14.0 is now used locally under its bundled Python license;
3.12.8 remains for historical reproduction. MSYS2 GCC 16.2.0-6 and SDL/Vulkan
dependencies were installed privately from the active framework's hash-pinned
manifest through an official MSYS2 mirror. Dependencies and retained notices
are not added to the title repository's Git tree.

Optional local texture-restoration experiments use the official
[Real-ESRGAN ncnn Vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan)
Windows 20220424 tool and Real-ESRGAN x4plus / x4plus-anime models from the
[v0.2.5.0 release](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0).
Keep its upstream licenses/notices with the private tool. Neither this tool,
its model weights nor restored game images are distributed in this source tree.
