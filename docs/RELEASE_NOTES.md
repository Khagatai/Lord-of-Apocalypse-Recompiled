# v0.9.0-beta.8 — testing pre-release

- Extend the optional smooth camera to continuous vertical tilt and unrestricted
  horizontal rotation. Release holds the selected tilt; vertical limits prevent
  inversion. Smooth mode no longer sends right-stick PSP D-pad steps alongside
  camera movement. Physical D-pad menu controls are retained.
- Add English main-menu password aliases using the original live matching keys.
  Read `config/Passwords.txt`. Original unlock and duplicate-entry checks remain
  active; Japanese passwords and existing unlock flags are preserved.
- Native executable rebuild required. HD textures, recipes, original game image,
  saves and settings do not need regeneration.
- Validation: 449 project tests; bounded native camera routes at 30/60 FPS;
  English password unlock, incorrect-code notification, visible keyboard entry
  and save/restart/duplicate rejection. Physical hardware and campaign acceptance
  are pending. No beta.8 installer or release archive has been published.
- Release acceptance is pending. These changes do not establish a fix for the
  existing multiplayer loading or audio reports.

# v0.9.0-beta.7

Windows x64 testing pre-release.

## Changes

- Add **Launcher Settings > Locations** to select the original Japanese ISO or
  an existing game installation. Choices persist; files are not moved or copied.
- Add editable controller bindings in **Launcher Settings > Controls > Edit
  controller bindings** and **F1 > Controls**. Settings persist, and F1 changes
  apply after the launcher confirms saving. Reassigning an input releases its
  previous binding. Host-menu navigation remains available.
- Add optional **Smooth horizontal rotation (experimental)** and camera speeds
  from 0.5x to 2x in both control editors. The right stick rotates continuously
  with eased acceleration and stopping. Vertical camera positions retain PSP
  behaviour. Original PSP rotation remains the default.
- Fix six delivery-request conversations whose inserted item names and quantities
  could exceed the dialogue panel. Reserve space for runtime substitutions while
  preserving command order, font and colour controls.
- Cache validated texture lookup indices while retaining full identity/content
  checks and the original-search fallback. A bounded native route performs
  about 91% fewer texture-search comparisons. Overall FPS gains need gameplay
  measurement; this does not change texture quality or HD processing.
- Gate routine sleep/wakeup debug output behind `SR_WAKELOG=1`; retain all
  scheduler behaviour and error reporting. The tested route produces 89% smaller
  logs. Native scheduler tests pass with logging both off and on.
- Reduce local multiplayer helper overhead by fetching lobby events and room
  health together, and socket port/pending-byte information together. The tested
  metadata cycle uses two IPC round trips instead of four. Guest packets, PSP
  timeouts and 30/60-FPS game timing are unchanged.
- Add numeric IPC latency/failure and null-callback context to local diagnostics.
  Bug reports now include `network-diagnostics.json`, excluding raw memory,
  identities, tokens and logs. A detected null-callback fatal error automatically
  creates a local report after exit; nothing is uploaded.
- Retain PlayStation SDL driver defaults and PlayStation/Xbox input labels.
  Physical DualSense USB/Bluetooth acceptance remains pending.
- Retain beta.6's PowerShell rendering fix and beta.5's incremental HD reuse.
  This update rebuilds the native game and refreshes the translated image once.
  HD recipes, models and texture inputs are unchanged: keep the installation's
  private folder to reuse existing verified texture jobs.

Provide your own unmodified Japanese NPJH50503 disc 1.01 ISO. The installer
contains public source and build tools; it supplies no ISO, generated game
executable, game assets, HD textures, saves or personal settings. Use a short
ASCII Windows install path and a Vulkan-capable driver. Selecting a different
installation uses that folder's progress without transferring saves.

## Validation and remaining work

446 automated regressions pass. Vulkan mip tests pass at 1x/4x; all 13 captured frames match the pre-optimization
native build across original-search, cached and verification runs. See
`docs/PERFORMANCE.md` for scope and measurements. Native launcher controls and F1 binding/camera
save, reload and reset checks pass. Native 30/60-FPS tests using a real SDL
virtual controller record continuous rotation of the final camera view, bounded
angular steps and onset, including simultaneous PSP D-pad input. Original PSP
camera layout and behaviour were inspected with the pinned PPSSPP oracle.
These bounded tests do not establish physical-controller, collision/lock-on,
scripted-camera, full-campaign or co-op camera acceptance.

Two native networking-HLE processes pass real local WebRTC exchange, matching
callbacks and receipt acknowledgements with synthetic guest fixtures. Three real
local WebRTC helpers exchange all 3,240 synthetic datagrams at nominal 30/60-Hz
schedules, including controlled 200-ms outbound handoff delay and up to 40-ms
jitter, with zero observed queue drops or lost peer connections. Scheduling
lateness was recorded; this is not a Steam/internet or game mission test.
The metadata-only IPC benchmark approximately halves its wall time; no game-FPS
or crash-reduction claim follows from it. Bounded native boot passes at 30/60 FPS.

The native game was regenerated and rebuilt with zero interpreter fallbacks;
all 103 English recipe bundles reproduce the working archive and 6,411 recorded
panel occurrences pass layout checks. The six changed NPC conversations still
need visual review during play. Installer extraction and beta.6 upgrade checks
cover preservation of private files; unchanged extraction/texture/caption stages
retain beta.6 first-run evidence. Full HD inference was not repeated.

Audio stutter/desync (#8), shield-removal/crafting freeze (#9), 60-FPS co-op
mission-loading crashes/freezes and international co-op slowdown remain under
investigation. No verified fix for #8 or #9 is included. Report reproduction
steps, location, frame-rate setting, save and a fresh diagnostic report.
Public installer download/update URLs require a check after publication.

---

# v0.9.0-beta.6

Windows x64 testing pre-release.

## Changes

- Fix first setup stopping with `render-text-worker.ps1 cannot be loaded because
  running scripts is disabled` after native compilation finishes. The launcher
  now handles the execution setting for its own UI, subtitle and credit renderer
  processes. Users do not need to enter a PowerShell command or change saved
  Windows execution policies for normal first setup.
- Keep renderer processes noninteractive and hidden. Text-source, private-path
  and layout checks remain enabled; failed stages still report their errors.
- Keep completed native compilation when retrying setup or updating from beta.5.
  Existing players should update the installed folder and retain `private`.
- Retain beta.5's HD checkpoint reuse and recipe-refresh fixes. HD processing
  code, recipes and models are unchanged. Existing verified texture jobs are
  reused; only new, changed, missing or damaged jobs need generation.

## Installation and updates

Download **Setup.exe** from this release. It downloads the verified public build
tools and source payload. On first Play, provide your own unmodified Japanese
NPJH50503 disc 1.01 ISO. No ISO, prepared game executable or HD textures are supplied.

Use Windows 10/11 x64, a Vulkan-capable driver and a short ASCII install path.
Allow about 18 GB free for compilation, translated data and optional full HD
generation. Python and the portable compiler are included. Windows N editions
need Microsoft's Media Feature Pack for movies.

If setup previously failed after compilation, keep the existing installation
and its `private` folder. After updating, click Play to continue. Existing text
and caption stages may be refreshed; the completed native build can be reused.
HD remains opt-in, and first-time HD generation can still take hours.

The automatic fix is limited to application-owned child processes. Administrator-
enforced Group Policy remains in effect. Managed PCs may still require approval
from their administrator; the application does not disable that policy.

## Validation and remaining work

All 407 regressions pass, including reproduction of Restricted-policy failures,
successful UI/subtitle rendering, unchanged saved Windows policy settings and
preserved renderer bounds checks.

An isolated installation of published beta.5 compiled from the original ISO and
reproduced the blocked-script failure. The actual beta.6 installer then upgraded
that installation, and setup completed under the same Restricted process policy.
Native executable/image hashes and timestamps were preserved: no native rebuild
was needed. Repeat setup reused completed output. Synthetic existing HD cache
files were preserved, and HD processing/recipe identities match beta.5; full HD
inference was not repeated. Both 30 and 60 FPS settings passed 360-vblank native
boot checks with displayed frames and zero interpreter entries/dispatch misses.

This is still a beta. Full campaign, intermittent audio distortion, remaining
text-layout review and comprehensive 30/60 FPS co-op acceptance remain open.
Report the version, quest/location, solo/co-op mode, FPS setting and reproduction
steps in GitHub issues. F1 > Tester support exports local diagnostics; nothing
is uploaded automatically. Do not attach ISOs or other game files.
