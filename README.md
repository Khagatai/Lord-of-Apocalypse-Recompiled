# Lord Of Apocalypse

A native port of the japanese game Lord Of Apocalypse which was never brought to the west. This game has english translations and should run natively on your PC without the need of emulators.

## Project Status

**Experimental Windows x64 port — current local candidate: v0.9.0-beta.1.**
Boot, menus and selected gameplay routes have been tested. A complete campaign
playthrough, wider hardware testing and release acceptance are still in progress.
This is not a finished V1.0 release.

| What | Status |
| --- | --- |
| Native Windows startup, first frame and menus | ✅  |
| Keyboard and controller input | ✅  |
| Launcher and F1 settings | ✅  |
| Save/load | ✅ |
| Solo gameplay | ✅  |
| Online co-op | ⚠️ Only one mission completed together. Need more testing. |
| 30 / 60 FPS gameplay | ⚠️ Both modes are implemented. Can interchange and shouldn't be an issue but needs more testing. |
| Audio and movies | ⚠️ Available, with intermittent distortion reported during bosses, movies and quest completion in solo and co-op. |
| English text | ⚠️ Expanded English WIP is the default. Japanese is selectable; editorial and campaign layout review remain. Japanese audio is unchanged. |
| HD visuals | ⚠️ World and character textures are available. Original model geometry, 2D UI artwork and dialogue portraits are preserved; campaign visual review remains. |

## How to build

This is the **developer build workflow**. Cloning this repository and supplying
an ISO is not yet a complete automated setup for the current English/HD build.
Private translation authoring inputs, generated textures and captured validation
data are not included in Git.

### Requirements

- Windows x64, Git and a Vulkan-capable graphics driver for the current player runtime.
- Your own unmodified Japanese PSP dump: **NPJH50503**, disc **1.01**, app **01.00**.
- Portable **Python 3.14.0**, extracted to `private/tools/python314/`.
- The pinned framework's local GCC/Make/SDL/Vulkan toolchain.
- Visual Studio 2022 C++ Build Tools for the local module-decryption helper.
- The additional pinned tools and measured boot-prefix input described in the
  [reproduction guide](docs/REPRODUCTION.md).

Required ISO size: **1,068,498,944 bytes**. Required SHA256:

```text
3a4d63713880dfb67ade00b6a912ac4975847cec06b1ab341b65963f328e1c93
```

Use a short ASCII-only project path, such as `C:\Games\Lord-of-Apocalypse-Recompiled`.
Keep the original ISO outside the repository. The commands below expect it in
the parent directory, named `Lord of Apocalypse (Japan).iso`.

### Get the source and dependencies

```powershell
git clone --recurse-submodules https://github.com/Khagatai/Lord-of-Apocalypse-Recompiled.git
cd Lord-of-Apocalypse-Recompiled
```

Download the official [portable Python archive](https://www.python.org/ftp/python/3.14.0/python-3.14.0-embed-amd64.zip)
and verify its SHA256 before extracting it to `private/tools/python314/`:

```text
8d4d3590c10449d78aa4375f534e6d5f3027d67fdc362dd1a882279db6f90fdf
```

From the project root in PowerShell:

```powershell
./private/tools/python314/python.exe tools/install-toolchain.py --mirror accum

git clone https://github.com/John-K/pspdecrypt.git private/tools/pspdecrypt
git -C private/tools/pspdecrypt checkout c156627db7634d395c380c0a9589130f603307fc
./tools/build-decryptor.ps1
```

The active framework is **Nakagawa Recomp**, pinned to
`8704fba98007fff6d6f930365f2b2142af1bfbba`. Do not replace the pinned checkout
with the latest upstream revision while reproducing this build.

### Prepare modules, generate and compile

```powershell
./private/tools/python314/python.exe tools/survey-disc.py '../Lord of Apocalypse (Japan).iso'
./private/tools/python314/python.exe tools/decrypt-module.py private/disc/PSP_GAME/SYSDIR/EBOOT.BIN private/modules/EBOOT.elf
./private/tools/python314/python.exe tools/decrypt-module.py private/disc/PSP_GAME/USRDIR/UPDATA/MODULE/LIBFONT.PRX private/modules/LIBFONT.elf

./private/tools/python314/python.exe tools/title.py generate --profile release
./private/tools/python314/python.exe tools/title.py build --profile release --jobs 4
./private/tools/python314/python.exe tools/build-windows-launcher.py
```

The native game output is under `private/native-release/lordofapocalypse/`.
The separate front end is `LordOfApocalypse.exe` in the project root. A compiled
EXE alone is not a complete playable installation: prepare the measured boot
prefix and required runtime inputs using the reproduction guide. The WIP English
image, subtitle bundle and HD pack require their separate private build inputs.

To run the source checks:

```powershell
./private/tools/python314/python.exe -m unittest discover -s tests -p 'test_*.py'
git diff --check
```

The reproduction guide also contains historical diagnostic commands. Current
player launch uses **LordOfApocalypse.exe**; the old command-file shortcuts are
retired. Existing prepared test installations can use the launcher and **F1** or
**Escape** for settings. Networking and tester support are in the in-game menu.

## How it works

1. **Identify the game.** Local tools verify the disc metadata and hashes before
   extracting and decrypting the required modules. The original ISO stays unchanged.
2. **Translate the code.** The pinned framework translates the PSP's Allegrex MIPS
   code into C, which is compiled into a Windows x64 executable. Title configuration
   records the measured memory base, entry point and module identities.
3. **Provide PSP services.** A native runtime supplies the required threading,
   filesystem, graphics, audio and input support. The current graphics path uses
   Vulkan. Unsupported behavior must produce an explicit error, not fake success.
4. **Load local content.** The runtime reads the selected local game image. Optional
   English text and HD texture replacements are prepared separately. Japanese voices,
   music and sound effects remain unchanged.
5. **Check against a reference.** PPSSPP is used during development for traces and
   visual comparisons. It is not the emulator running the player executable.

The launcher and F1 menu read the same saved preferences. Generated game code,
images, modules, textures, captures and saves stay outside the source repository.

## Want to help

Testing on more PCs and playing through later quests are especially useful.
Help is welcome with English proofreading, text layout, graphics comparisons,
audio diagnostics, controller behavior, save/load and multiplayer at 30 and 60 FPS.

[Open an issue](https://github.com/Khagatai/Lord-of-Apocalypse-Recompiled/issues)
with:

- Your build/version, Windows version, CPU, GPU and graphics driver.
- The quest, location or menu, with steps to reproduce the problem.
- Your frame-rate mode and graphics preset, and whether you were playing solo or co-op.
- What you expected and what happened. For co-op, include the build and FPS mode on both PCs.

**F1 → Tester support** can export a local diagnostic report; it does not upload
anything automatically. Review attachments before sharing. Do not attach ISOs,
modules, generated game code, assets, saves or credentials.

For code contributions, keep changes focused, preserve the framework pins and
run the relevant checks. Keep game content and private development outputs out
of commits. Translation changes should preserve the original font style, colours
and layout wherever possible.

## Credits

- **Square Enix** and the original game's creators and credited contributors.
- **[Jstar269 / Nakagawa Recomp](https://github.com/Jstar269/Nakagawa-Recomp)** — active recompilation framework and runtime.
- **[Tzeentchnet / psp-recomp](https://github.com/Tzeentchnet/psp-recomp)** — original framework used during the project's initial work.
- **[John-K / pspdecrypt](https://github.com/John-K/pspdecrypt)** and **[PPSSPP](https://github.com/hrydgard/ppsspp)** — local module preparation and development reference tools.
- **Serberker, Sabaku.D.Tonio and Jinouga** — upstream English v1.6 translation work used as a baseline. Its standalone play option is retired; the original contributors remain credited.
- The authors of **SDL, Python, xdelta, libdatachannel, Real-ESRGAN** and the other dependencies listed in [CREDITS.md](CREDITS.md).
- The testers and contributors helping with gameplay, translation, graphics and multiplayer reports.

The optional Steam development integration uses Valve's Steamworks SDK under
its own terms. SDK files are not included in the source repository. See
[CREDITS.md](CREDITS.md) for dependency licences and provenance.

## License

See [LICENSE](LICENSE) for the project's **GNU GPL version 3** licence.
Individual files and third-party components retain the licences stated in their
headers and notices; see [CREDITS.md](CREDITS.md).

The source licence does not grant rights to the original game, its artwork,
audio, trademarks or upstream translated assets. You must supply your own game
dump. This is an independent fan project, not affiliated with or endorsed by
Square Enix, Sony or Valve.
