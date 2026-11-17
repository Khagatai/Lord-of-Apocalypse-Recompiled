# Windows graphics settings

Source-launch repair: an observed launch stopped before opening the runtime
because the HD validator detected changing file identities. A read-only check
subsequently verified all 28,189 PNG hashes with stable metadata; the exact
writer responsible for the earlier change was not observed. Cached validation
now retries once after that specific race, discarding all cached hits and
rehashing every PNG. A second race, corrupt PNG or other validation failure
still stops startup. This does not bypass asset integrity checks.

The source EXE passes actual startup, visible F1 and clean exit with the saved
graphics profile; warm startup checks took 5.4 seconds. Saved preferences and
save files remain hash-identical. All 284 source tests pass, including recovery
from one metadata race and refusal of corruption or persistent changes.
Evidence stays local in `private/source-launch-repair/`. Distribution work is
paused; existing player archives/installers need this repair incorporated and
revalidated before release.

Current visual policy: original title/menu/item/UI artwork, with English text
retained, and HD environments/models. 2D draws bypass HD replacements/xBRZ;
the F1 toggle is now labelled **HD world / models (WIP only)**. A restrained
detail pass covers the observed player atlases; dialogue portraits stay original.
This supersedes older all-UI/HD-font recommendations below. See the
[audio and visual validation record](AUDIO_AND_UI.md).

Normal launches cache successful HD PNG verification in
`private/settings/hd-verification-cache.json`. Manifest structure, every mip
identity/dimension, INI contents, game images, executable and framework identity
are still checked. Unchanged PNGs reuse their verified hash/header only when
Windows file ID, creation/write/change times, size and attributes match. Changed
files are rehashed; reparse points are refused. A second directory snapshot
rejects concurrent changes. Missing/corrupt caches or unsupported directory
queries fall back to hashing. Validator changes invalidate the cache. This is a
local build-style cache, not a signed security boundary or a claim to detect
silent storage corruption without metadata changes.

The measured pre-launch checks took 35.3 seconds before this change (profiled),
then 4.5 seconds on a normal warm cached preflight. The first cache-building
pass takes longer; subsequent launches reuse unchanged files. Startup progress
now appears in the launcher details box. No game binaries/assets are copied,
and the currently running game is unaffected. Full explicit validation remains:

```powershell
private/tools/python314/python.exe tools/launch-preview.py --variant saved --check
```

`--check-cached` exercises the normal cached checks without opening a game.
Local evidence: `private/startup-before.prof`, `startup-final-warm.json` and
`startup-source-tests.log` (193 passing tests, including seven cache regressions).
The metadata API is documented by
[Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_both_dir_info).

The Graphics tab also offers **Gameplay frame rate: Original 30 FPS / Upgraded
60 FPS (experimental)**. It defaults to 30 and requires a restart. Decoded movies
retain original timing in both modes. See [frame-rate evidence](FRAME_RATE.md).

The next text-quality experiment is documented in [TEXT_QUALITY.md](TEXT_QUALITY.md).
The existing glyph-reconstruction filter rebuilt zero glyphs at the sampled
English save-loaded prompt, so no sharpening option was added to the menu.
The optional [HD font pack](HD_FONT_SAMPLE.md) replaces seven prompt labels,
two English startup notices, 40 numeral glyphs and all 94 printable ASCII body
characters at 4x. Enable **HD English UI** in Advanced for normal WIP launches,
or use `Start-HD-UI-Sample.cmd`. Other fonts/palettes retain their original art.
See [texture scaling and current remaster coverage](TEXTURE_IMPROVEMENTS.md).

Open `LordOfApocalypse.exe` and click **Play** to enter the game.
A fresh configuration defaults to **English WIP**, the expanded translation.
Press **F1** or **Escape**, then choose **Settings**. The Graphics, Display,
Advanced and Language tabs contain fifteen choices, plus
presets and access to the current run's logs. Arrows navigate, Left/Right or
Enter changes choices; controller navigation uses the existing host bindings.

Changes save automatically. Fullscreen, image scaling and the performance HUD
apply live. Internal resolution, window size, VSync, filtering, upscaling,
advanced effects and language changes apply after restarting. Choose **Apply
and restart game**, then confirm. Save your progress through the game first:
this action restarts from boot and does not create a save. Restart is disabled
while the PSP savedata UI reports an active save. Language/version choices keep
separate saves; this feature does not merge or convert them.

Under Language, **Balanced** selects 2x resolution, 4x anisotropic filtering,
Sharp presentation and VSync. **Original** restores PSP-resolution rendering
and disables enhancements. Both retain the selected language. Later direct
launches use the saved language selection. The legacy language-specific preview
shortcuts still explicitly select their original versions. The separate panel
is optional at `Start-Graphics-Settings.cmd`.

**High Quality** on the Language tab (or at the top of the separate panel)
restores all eight implemented effects: 4x rendering, FSR 1, AF16, mipmaps,
full colour, SSAA2, xBRZ4 and HD UI. It preserves language and display choices.
As with other startup settings, save progress first and confirm a restart.

If the quality profile is too demanding, the launcher's **basic graphics** checkbox temporarily
starts the saved language windowed at 960x544, 1x rendering, no HD pack and no
GPU enhancements. It uses the same verified image, controller mapping and save
namespace. It does not write preferences by launching. A normal launch returns
to the saved profile; saving an F1 change during recovery persists that run's
displayed settings. The equivalent CLI is
`tools/launch-preview.py --variant saved --graphics-preset original`.
The CLI also accepts `balanced` and `quality` as per-run presets.

Preferences persist in ignored `private/settings/graphics.json`. The existing
direct preview launchers also read these graphics preferences, preserving their
original language/save selection. **Internal resolution** increases rendered
3D resolution: 1x = 480x272, 2x = 960x544, 3x = 1440x816, 4x = 1920x1088.
Low-resolution textures, text sprites and movies retain their source detail.
Increasing the window size alone does not recreate this detail.

| Setting | Effect |
|---|---|
| Windowed / borderless fullscreen | Borderless fills the desktop resolution |
| Window size | Sets the actual client area, independently of internal rendering |
| Sharp / Integer / Smooth | Controls presentation filtering and scaling |
| VSync | Synchronises presentation to the monitor |
| Performance display | Shows the runtime HUD |
| FSR 1 | Optional spatial presentation upscaler |
| Anisotropic filtering | Improves texture filtering on angled surfaces |
| Host mipmaps | Experimental distance-filtering enhancement |
| Full-colour rendering | Experimental higher-precision host colour target |
| 2x supersampling | Extra rendering in both axes then downsampling; expensive |
| Texture smoothing (xBRZ) | Off / 2x–6x scaling of eligible decoded textures; original fallback while copies are prepared |
| HD English UI | Verified local 52-image pack for WIP English/Vulkan; restart to apply |

As of 2026-11-15, fresh profiles enable all implemented quality effects:
4x internal resolution, FSR 1, 16x anisotropy, mipmaps, full colour, 2x
supersampling, 4x xBRZ and HD English UI. The user's existing profile was backed
up and updated to these effects, preserving display, VSync and language choices.
Original and Balanced remain lower-cost presets. The effects initialise on the local NVIDIA GPU,
but campaign-wide appearance and performance are not validated. Disable an
effect or select Original if it introduces artifacts or slows gameplay.
No frame-generation, widescreen, animation, timing or audio changes are enabled.
Japanese voices, music and sound effects remain unchanged.

Both new controls persist and require restarting. Missing or modified HD pack
files produce a verification error. The saved HD UI toggle is ignored for
Japanese/v1.6 and GDI, retaining the preference for WIP/Vulkan. Original and
Balanced disable both new effects. Existing twelve-choice preferences migrate
in memory without writing or losing any choice. Windows acknowledgement reads
allow atomic replacement; the supervisor retries transient sharing violations.

Frame pacing remains a live, current-run option; it returns to PSP timing on
restart. F3's temporary HUD shortcut does not edit the saved HUD preference.
This is a host pause overlay; the PSP game's own settings screen is unchanged.
Source artwork and Japanese audio remain unchanged when switching versions.
The overlay does not implement runtime text swapping: each version loads text
and resources from a different image, so language changes require restarting.

The software/GDI fallback explicitly disables GPU enhancements while retaining
saved preferences for future Vulkan runs. Launch errors are recorded in
`private/settings/launcher.log`; each game run also has its own
`private/preview-*` report and native log.

## Build and validation

The panel and extended overlay are title-owned host code. Framework source and
revision remain unchanged. `tools/overlay-settings.mk` links the overlay into
the local native executable with two GNU ld wrappers: the Settings page and its
host redraw timer. It changes no guest instructions or PSP calls. The build
records extension-source and executable hashes in ignored `host-ui-build.json`.
The supervisor validates menu choices, writes preferences atomically and
acknowledges saves. Restart requires an acknowledged settings request, a
separate confirmed runtime marker, and exit code 0 before starting another run.
Failed saves and missing acknowledgements are displayed as errors.

Rebuild and check locally:

```powershell
./private/tools/python314/python.exe tools/build-settings-menu.py
./private/tools/python314/python.exe tools/title.py build --profile release --jobs 4
./private/tools/python314/python.exe -m unittest discover -s tests
powershell -NoProfile -File tools/check-settings-menu.ps1 -Output private/settings-ui-check-new
./private/tools/python314/python.exe tools/check-graphics.py --output private/graphics-check-new
./private/tools/python314/python.exe tools/check-game-settings.py --output private/game-settings-check-new
./private/tools/python314/python.exe tools/check-game-settings.py --output private/game-settings-restart-new --restart
```

Use fresh private output directories. Runtime tests use copied save fixtures
and check their sources and preferences remain unchanged. The pause check
briefly focuses its own game window and captures it privately. Frame-exit
automation deliberately refuses manual pause; the pause check uses host timeouts.

Actual local evidence (2026-11-14): all 12 panel controls and Balanced preset
passed (`private/settings-ui-check-04/result.json`); screenshot inspected.
Original, Balanced and 4x/16x AF/FSR/mipmaps/full-colour/2x supersampling startup
profiles exited 0 without timeout, with requested features confirmed in logs
(`private/graphics-check-01/summary.json`). This checks startup, not gameplay
quality or FPS. A 1280x720 physical client area and pause/resume were verified;
initial tests with frame-exit automation correctly refused pause. UI navigation
checks retain their private screenshots and results in `game-settings-check-*`.
Final live Settings check `private/game-settings-check-06/result.json` passed:
frame pacing changed to No extra cap and back to PSP timing, the guest resumed
at the same VBLANK, exit code was 0, and saves/preferences stayed unchanged.
The Settings-page screenshot was inspected locally. Earlier navigation checks
were corrected after their screenshots exposed missing Win32 extended-key flags.
All 90 source tests pass. The Git-index audit passes with 116 UTF-8 source files
and two pinned gitlinks; both framework working trees remain clean.

These checks add no PPSSPP trace-equivalence or full-game playability claim.
Existing measured base/entry, native/PPSSPP evidence and unresolved milestones
remain in `STATUS.md`. No game data or screenshots are committed or uploaded.

### Integrated F1 menu results

The panel-only results above are the earlier baseline. The extended in-game
menu passes 95 source tests, including rejected settings, failed preference
writes and strict restart confirmation. The native release executable now
includes the title-owned host overlay; its exact identity is recorded in
`private/native-release/lordofapocalypse/host-ui-build.json`.

`private/game-settings-integrated-06/result.json` passes the actual Win32 route:
1280x720 client size; F1 Settings; 3x internal resolution saved; Integer scaling
applied live; advanced mipmaps saved; Japanese to v1.6 to WIP language choices;
Balanced preset preserving WIP; separate restart confirmation; clean exit 0;
then WIP startup with saved 2x rendering and exit 0. The Language-page screenshot
was inspected locally. Earlier attempts exposed spatial-navigation test errors
and motivated consistent full-width action buttons; failed evidence is retained.
All preferences and source saves remained unchanged in the final isolated test.

Startup-only graphics checks on the extended executable are recorded under
`private/graphics-check-integrated-01/`. These remain bounded startup checks,
not campaign, physical-controller, save-conversion or performance acceptance.

Current shared settings validation (2026-11-17): the native launcher and F1 use
the same preference file, option definitions and presets. Both expose only English
WIP and Japanese. Networking and tester reporting remain exclusive to F1.
The launcher uses the same slate/gold palette as F1. All 290 source tests pass;
real launcher save/cancel/conflict handling, F1 save/restart, two DPI layouts and
source EXE startup passed. These checks do not establish campaign or co-op acceptance.
