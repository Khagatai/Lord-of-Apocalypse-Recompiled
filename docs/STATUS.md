# Validation status — 2026-11-16

Quest-completion audio investigation: the user confirms distortion in both solo
and co-op. Recent normal-run logs contain real channel-8 underruns associated
with some high GE CPU/readback windows, but have no quest-phase markers. The
source runtime now measures producer gaps, PCM/gain clipping and pre-clamp SAS
saturation, with numeric-only performance context in F1 reports. All 276 tests
and native 30-mode town/dialogue and 60-mode partial opening checks pass their
diagnostic gates. Neither local run completes a quest; the failure is not fixed
or independently reproduced. Japanese audio, WIP assets, saves/settings and the
framework pin are unchanged. The final diagnostic executable is `ce7dc7e`;
existing tester ZIPs are unchanged. See [actual measurements and limits](AUDIO_AND_UI.md).

English editorial pass 23 is installed in the source project: 1,543 message
variants corrected, including 339 equipment description families and 112 other
distinct Japanese source records. It fixes spelling/draft artifacts, Lord/Road
and other terminology, notification meaning, repeated names, quest instructions
and colour-marker placement. All 2,209 populated shared item descriptions remain
within their layout limits. All 274 tests, independent reconstruction and native
30/60 inventory checks pass. Runtime, Japanese audio, movie captions, real saves
and preferences are unchanged. Full campaign semantic/context and affected-screen
acceptance remain open; existing tester ZIPs are unchanged. See
[the review scope and evidence](TRANSLATION.md).

The source WIP image now includes a comprehensive shared item-description pass:
all 6,077 entries in the equipment and consumable/material tables audited,
2,116 descriptions reflowed or shortened, and no descriptions over the measured
five-line/144-pixel advance limit. Original font size, colours, quantities,
ratings and aliases are preserved. Native inventory captures pass at 30 and
60 FPS; all 273 source tests and independent cumulative reconstruction of
10,209 changed message blocks pass. Actual crafting panels and individual
late-game equipment still need visual field review. The runtime, captions,
Japanese audio, source saves and preferences are unchanged. This source-only
update does not refresh tester packages.

The earlier reported text-layout corrections remain installed:
natural-proportion gold labels with shared baselines, full source-lettering
cleanup, a bounded caution body, and short Turnslash/Obsidian Sword description
lines. The 327 story-movie plates are individually fitted, reducing their total
area by about 61% while preserving all English glyph pixels and decoded-frame
intervals. The 24 credit pages and Japanese audio remain unchanged. Native
character creation and all 18 opening cues pass at both movie test settings;
all 351 cues pass the actual four-format writer check. The warning has a pinned
PPSSPP software reference. Specific crafting/results/settings screens still
need field review; no full-campaign layout acceptance is claimed. Source saves,
preferences and runtime are unchanged; tester packages are not refreshed.
See [the layout evidence and regeneration commands](UI_LAYOUT.md).

Guild-entry starvation correction is installed in the source runtime, with
separate low-priority host I/O and event-driven guest callback workers. Clock-only
and single-handoff attempts failed native checks and are superseded. Candidate
stress checks retain frames through guild room creation at both 30/60; real
native pairs also establish matching and exchange game data at both settings.
All 266 source tests and two-process direct/WebRTC HLE checks passed that runtime
change. The user now reports connecting with another player and completing one
mission. The frame-rate combination was not recorded; separate 30/60 gameplay,
rewards/save round trips and longer-session performance remain open. See
[the full matrix](MULTIPLAYER_ACCEPTANCE.md).

Packaged pause-menu correction: the tester reports a dark overlay with no menu
after F1/Escape. The ZIP omitted dynamically loaded `SDL3_ttf.dll`; the previous
PE-import scan could not discover it and also failed to add sibling dependency
files to the package. Explicit dynamic roots and recursive sibling dependencies
now include its complete 17-DLL closure, licence notices and public UI fonts.
The dependency-only `LordOfApocalypse-Menu-Fix.zip` is 10,148,741 bytes and contains
no game executable, game assets, saves, settings or ISO. The full package also
checks menu DLL loading and eight font files before starting the game.
All 265 source tests pass. A relocated native F1/settings/support/export/resume
check exits 0 without development Git metadata or developer tools on PATH,
with no overlay failure and unchanged source saves/preferences. Its first
capture attempt lacked stock Windows PowerShell on the artificially reduced
PATH; that harness failure is retained and the corrected check passes.
Evidence: `private/distribution-test/packaged-menu-evidence/`. These host
packaging changes leave the framework pin and native game executable unchanged.

Tester-support additions are documented in [TESTER_SUPPORT.md](TESTER_SUPPORT.md):
F1 diagnostic export/audio markers, aggregate audio telemetry, and five distinct
verified pre-launch save snapshots per namespace. Reports exclude raw logs and
protected payloads; no upload is performed. Host tooling does not fix the remaining
boss/movie audio issue or establish campaign/co-op acceptance. The user reports
two members in a Steam lobby; this is separate from a verified shared mission.
All 262 source tests pass. `private/tester-support-check/` retains the first
failed focus/export check; the focus jump during pending actions was fixed.
`private/tester-support-check-02/` then passes actual F1 marking/export,
readable window capture, resume, settings persistence and clean exit (0), with
original saves/preferences unchanged. Two relocated normal launcher runs without
developer tools on PATH both exit 0: the first creates a verified three-file
snapshot and the second reports unchanged, with no duplicate snapshot. Numeric
audio summaries are produced on exit. Evidence:
`private/distribution-test/launcher-backup-result.json`. Guest image and framework
pin remain unchanged; no new PPSSPP campaign/audio comparison is claimed.

Translation pass 20 is installed in place: 9,983 changed messages, 120 translated
images, 327 frame-timed captions across all twelve story movies, and 24 credits
pages with English roles and original credited-name glyphs. All 252 source tests,
2,808 actual native caption-writer checks, the complete native opening and
saved-launch preflight pass. Nine PPSSPP software startup images match pass 19
byte-for-byte. Saves, preferences and Japanese audio stay unchanged. The normal
MES audit has no remaining Japanese script outside fourteen functional password
keys. Editorial quality, persisted-name provenance, decorative artwork and full
campaign layout/routes remain unapproved; this is still WIP English.
See [current translation evidence and limits](TRANSLATION.md).

Steam development backend: the user supplied Steamworks SDK 1.65 and authorized
App ID 480 testing. Actual Steam initialization and friends-only lobby creation
and leave pass. In a copied-save native game-window check, F1 switches live to
Steam, saves the isolated provider choice, hosts a real lobby and leaves it.
One local member, **zero connected peers**; no second account or shared mission
has been tested. The unavailable helper overlay is represented by a disabled
invite button; friend-lobby browsing/join is implemented but needs a second PC.
226 regressions pass; existing WebRTC/HLE tests still pass. The original framework
pin and source save/preferences stay unchanged. [Steam instructions and evidence](STEAM_TEST.md).

Current networking pass: server-issued five-digit rooms and native WebRTC are
implemented. Two independent processes pass direct and forced local TURN tests,
including datagrams and reliable streams. Real HLE matching callbacks and PDP
pass through this transport against synthetic guest RAM. F1 creates a real room
and connects a separate native client in a copied-save game-window test. 221
Python tests, release build and launch preflight pass. **No shared game mission
or independent-internet connection is validated.** No public endpoint is deployed;
the user has no server/domain and selected the optional Steam development test
described above. See [current co-op evidence](COOP.md).

Launcher cleanup: only `Start-Game.cmd` and `Start-Safe-Graphics.cmd` remain.
Eight duplicate/obsolete preview, sample and settings command files were removed.
Networking is a separate **F1 → Networking** page, no longer a Settings tab or
an external direct-IP form. Create/join by five-digit code is explicitly
unavailable until a room-service endpoint is configured.

Native networking: an opt-in Windows lobby/PDP/PTP/matching prototype now passes
two-process synthetic transport and HLE/callback tests. Normal network settings
remain off. A copied-save game session reaches town, but no game room/mission or
internet co-op has been validated. The user selected a five-digit room-code UX
with P2P-first internet connections, superseding manual IP/port-forwarding as the
intended player flow. This earlier direct-backend evidence is superseded by the
current native WebRTC local results above. See [co-op status and acceptance gates](COOP.md).

Current correction pass: original 2D title/menu/item/UI bindings are restored
while retaining English text and HD 3D. Title, inventory and sharpened player/town
captures were inspected; 80 observed-player PNGs have verified unchanged alpha
and bounded detail. Movie header timestamp and audio queue corrections reduce
the measured opening A/V offset from ~215 ms to ~90–100 ms, but audio is **not
fully fixed** and boss-fight distortion has not been reproduced. A source-AU clock
candidate caused >500 ms native underruns and is excluded from normal builds.
The user authorized networking work while audio testing is pending. These findings supersede older
all-UI-remaster and movie-clock-only acceptance statements below. See
[current evidence, commands and remaining work](AUDIO_AND_UI.md).

Launcher startup: normal HD verification now caches unchanged PNGs using
Windows file identities/change times, retaining full metadata/INI validation
and rehashing changed files. Explicit `--check` always bypasses the cache.
Measured pre-launch checks improve from 35.3 seconds profiled to 4.5 seconds on
a warm normal cached preflight; 28,189 unchanged PNGs are reused. The first
cache-building pass remains slower and CMD now displays progress immediately.
193 source tests pass, including edits with restored modification timestamps,
missing images, changed manifest/INI, corrupt caches, reparse points, concurrent
changes and cache-write/query failures. Runtime executable, game assets, saves
and normal graphics preferences are not modified by this launcher change.
See [graphics/startup details](GRAPHICS.md).

Frame-rate selection is installed in F1 Graphics and the separate settings
panel: original 30 (default) or experimental 60, applied after restarting.
Native paced town samples measure 29.970 / 59.940 FPS with equal game-time
progression. The final 60-mode HD checkpoint also measures 59.940 FPS, loads
162 replacements and uploads 32 replacement mip chains / 96 levels, with zero
texture or interpreter failures. Recorded movie contexts restore original
timing, including creation during an update callback; sampled video timestamps
and audio clocks remain unchanged. 186 source tests pass, as do synthetic media
tracking and pinned PPSSPP timestep-instruction checks. Failed deterministic
and earlier movie-boundary attempts remain recorded. Combat/campaign-wide 60
acceptance and in-engine cinematic classification remain open. See
[frame-rate evidence and limits](FRAME_RATE.md).

Current HD asset coverage is complete for all scanned non-portrait archive
identities: 10,713 descriptors covered across all required alignment identities
and sampler wraps, 39 original dialogue portraits, zero unmatched or unresolved.
The single active pack contains 28,189 PNGs / 34,071 groups / 12,706 authored-mip
groups, manifest `e69f5f92d52c8ba122b35d30cb74a9718824bebb375a9eb4ad4b6912b7c5c661`.
392 new neural outputs preserve alpha/invisible RGB; all 3,617 new faithful
outputs match the pinned scaler byte for byte. Native town, sanctuary dialogue
and inventory checks pass with zero replacement failures, mip rejections or
interpreter instructions/entries/dispatch misses. All 162 captured town source
mip levels match corrected catalog 08. The source suite passes 179 tests.

This establishes static texture coverage, not a full campaign or high-polygon
mesh remaster. Full campaign visual review, combat/boss coverage, sustained
performance and matching PPSSPP campaign traces remain open. Japanese audio is
unchanged. See [current evidence](HD_ASSET_COVERAGE.md) and
[campaign acceptance](CAMPAIGN_VALIDATION.md).

A subsequent 1,188-second copied-save session closes normally, loads 377
replacements and uploads 97 replacement mip chains / 291 levels with zero
texture or interpreter failures. It checks Time Rift exchange UI, another NPC
dialogue, and an in-process save/return-to-title/Continue round trip. No combat
mission is completed. Four ad-hoc networking cleanup calls return actual
unsupported errors; these remain unfaked. All 87 protected-file hashes match.
Validated scratch cleanup removes 140.427 MiB; private development storage is
approximately 30.775 GiB, with one active HD pack.

## Earlier stage results

The previous HD pass had 24,806 PNGs / 30,171 identity-context groups,
with original dialogue portraits. Added 36 sky/cloud source sets and 105 faithful
UI/effect sets in place. All 368 new sky context/mip levels pass alpha and
invisible-RGB checks; all 420 UI outputs match the pinned scaler pixel for pixel.
Current native town and inventory checks pass with zero texture failures or
interpreter instructions/entries/dispatch misses. Source saves, fonts and
settings remain unchanged. All 162 captured town source mip levels match catalog
08; that capture does not establish new sky use or a matching PPSSPP campaign
trace. Full campaign visual validation remains open.

The latest archive audit records 9,977 fully covered descriptors, 39 intentionally
original portraits, 675 unmatched and 61 ambiguous/wildcard identities. Original
fallbacks remain for unresolved art. Private working storage is approximately
30.375 GiB after removing obsolete builds, unused portrait PNGs and validated
scratch. All 87 protected-file hashes still match. See [HD evidence](HD_REMASTER.md).

Storage cleanup: the single working HD pack is `private/hd-remaster-pack/`.
A second cleanup removed 2.490 GiB of obsolete diagnostic/prototype builds and
framework evaluation checkouts. All 87 protected files remain byte-identical.
The original dialogue-portrait policy removes 312 replacement groups covering
39 reviewed illustrations; a native sanctuary dialogue check passes with the
original artwork, upgraded frame/text and zero texture or interpreter errors.
Both artwork builders now exclude these illustrations and key aliases.
168 source tests pass, including explicit small-UI admission and retained mip
geometry guards. Remaining art and campaign review are still required.
The latest combined material candidate passed separate native town,
sanctuary and inventory checks with zero texture failures, interpreter entries
or dispatch misses. The 187.411-GiB cleanup preserves all 87 protected-file
hashes. Builders now update the working pack in place by default, and launcher
logs no longer duplicate the full pack inventory. See [storage policy](STORAGE.md).

The offline 16-bit palette block and colour-expansion bugs are corrected: the rebuilt catalog decodes
all 10,752 descriptors with zero decode failures, retaining all 162 matching
native capture comparisons and unchanged data for the previous 10,742 complete
descriptors. Only ten corrected palette identities change. All 159 source tests
pass, as do exhaustive checks of all 196,608 16-bit colours against the pinned
PPSSPP conversion code. A deliberately wrong decoder is correctly refused.
These are decoder/catalog results; live campaign use of the ten newly
decoded chains is not yet established. The next material candidate remains
separate from the default until its checks and review finish.

2026-11-15 background HD update: the default pack has 22,959 unique PNGs,
adding 14 reviewed background/prop/tree source sets to pack 05 and preserving
every previous group exactly. All 112 added context/mip PNGs pass independent
alpha/invisible-RGB checks. Fresh native title and town checks exit 0 without
texture failures, interpreter entries or dispatch misses; source saves, fonts,
settings and pack hashes remain unchanged. Actual screenshots were viewed.
These checks establish compatibility, not that every added backdrop was drawn.
The verifier also removes duplicate PNG reads while retaining integrity checks;
155 source tests pass. Full campaign and remaining-art review remain open.
See [HD evidence](HD_REMASTER.md).

Earlier 2026-11-15 transparent-art HD update: the default pack had 22,847 unique PNGs,
including 720 selected transparent character/equipment source sets, 106 foliage
sets, 42 further props/terrain sets and 27 illustrated NPC cutouts. Every prior
pack-04 group is preserved exactly. Independent PNG alpha checks and base-art
review pass. Fresh town, sanctuary and inventory native checks exit 0 with no
texture failures, interpreter entries or dispatch misses and unchanged source
saves/fonts/preferences. Offline identities cover 9,614 of 10,752 descriptors;
this does not establish complete visual or campaign coverage. Full campaign,
combat, matching new PPSSPP traces and sustained performance remain open.
See [HD evidence](HD_REMASTER.md).

Earlier 2026-11-15 broad archive HD update: the WIP HD toggle selected
17,283 unique PNGs, including selected player/equipment, NPC/monster and
environment variants, sharper existing English labels and faithful UI scaling.
All prior 295 pack identity groups are preserved. Independent actual-PNG alpha
and UI pixel checks pass; all base contact sheets were reviewed. Review holds
back 142 environment sets containing effects or text artwork. Filtered town,
sanctuary and inventory checks exit 0 with no decode/upload failures, interpreter
entries or dispatch misses; source saves/fonts/preferences remain unchanged.
Full campaign, combat and sustained FPS validation remain open. This is not a
full-remaster completion claim. See [HD evidence](HD_REMASTER.md).

Earlier 2026-11-15 portrait/dialogue HD update:
411 PNGs, retaining the prior 355 images plus 12 named-character portrait
expressions and two text-free ornament atlases in all four sampling contexts.
Independent PNG checks verify all 56 added alpha planes and invisible RGB bytes
exactly. Native sanctuary checks exit 0 without replacement or upload errors;
saves/fonts/preferences stay unchanged. Five portrait-only GPU frames differ
only in the portrait footprint. NPC/monster batches continue; full HD/campaign
completion is not claimed. See [HD evidence](HD_REMASTER.md).

2026-11-15 sampler-aware renderer is integrated into the normal release,
SHA256 4cfb0cfe0931838c25a543cdebf19a0df688d650d6357e9de57022a6c5dfb41a.
Eleven real Vulkan cells at each of two scales pass; wrong-wrap and wrong-mip
negative controls are detected. Four shared disabled-mode and five Quality
sanctuary GPU frames match the previous build exactly, as do all 237 original
captured mip records. The normal 355-image pack remains compatible. Portrait
and ornament admission is recorded above; further archive batches are in progress. Translation is paused
for the requested HD pass. See [current HD evidence](HD_REMASTER.md).

2026-11-15 expanded HD pack: the normal WIP toggle selects 355 PNGs with 86
world mip chains, 45 archive-matched single-level 3D textures and 52 UI images.
92 opaque and 21 alpha-constrained materials are restored; 18 soft/other alpha
materials retain xBRZ. Town and sanctuary native checks pass with no replacement
or upload failures. Independent decoding verifies all 49 changed PNG alpha
planes exactly; 306 other PNGs stay unchanged. Source saves/fonts/preferences,
Japanese audio, disc image and guest code remain unchanged. This pack admission
used a89dd400; the later sampler integration is recorded above. No full
campaign or full-art completion is claimed. See [current HD evidence](HD_REMASTER.md).

2026-11-15 broader remaster coverage: the read-only archive catalog enumerates
10,752 descriptors and exports deduplicated art for batch review. 158 of 162
captured mip identity/level pairs decode identically; four small-layout pairs
are refused, with zero decoded-pixel mismatches. The 32-chain expanded pack
passes the native camera route and is admitted through the normal WIP HD toggle.
Its 148 images include the existing 52 English UI images. The host menu label is
now HD textures / UI; guest code/image and framework pins are unchanged.
All 132 source checks pass after the later padded-swizzle inspector correction.
Its final audit matches all 162 observed mip identity/level pairs; 30 palette
bound failures and two ambiguous small-texture keys remain explicit gaps.
Broader art review and campaign completion remain
open. A copied-save live session reached the inner sanctuary and found a still-
Japanese floating NPC name; it closed normally without changing source saves,
fonts or preferences. See [HD evidence](HD_REMASTER.md) and
[campaign checkpoint limits](CAMPAIGN_VALIDATION.md).

The shortened native route now independently reaches the inner sanctuary and
English story dialogue at vblank 8900–8910, exit 0, with 82 mip uploads / 246
levels and no upload/replacement failures. Its execution report records zero
interpreter instructions and dispatch misses. Matching PPSSPP replay and later
quests/bosses remain outstanding. The separate offline archive batch produces
32 further artwork candidates / 111 mip images; these are not installed until
native sampling and visual checks are completed.

2026-11-15 text-image pass 16 is admitted to normal WIP launches, retaining WIP
saves. It adds 221 translated regions across 91 images, including all 75 measured
loading-map variants. Audio/non-text payloads and 98 subtitle timing cues verify
unchanged. Native town and independent PPSSPP startup checks exit 0; 128 source
checks pass. Boss banners, title/promotion text, legacy metadata, draft quality
and campaign acceptance remain open. See [current translation evidence](TRANSLATION.md).

2026-11-15 normal HD release: the identity-checked private renderer extension is
now part of the normal release build and enabled by texture scaling or HD UI.
The executable matches validated prototype 04 exactly; the guest image and
upstream checkout remain unchanged. The town camera/movement route exits 0,
uploads 58 mip chains / 174 levels and records zero mip-upload failures.
Original, Balanced and Quality startup checks pass. Five Quality GPU frames with
the extension disabled match the prior release exactly. Source saves, fonts and
preferences remain unchanged. All 128 source checks pass. This establishes the
bounded renderer integration, not campaign-wide art, performance or playability.
Text-image translation has resumed; full translation and an authored HD art
remaster remain incomplete. See [current HD evidence](HD_REMASTER.md).

2026-11-15 complete-chain replacement update: isolated build 04 accepts verified
PNG mip chains and rejects incomplete/missing/wrong-size/corrupt chains whole.
The local eight-world-chain pilot plus base UI has 76 images; the town camera
route exits 0 with 8 replacement chains queued, 53 needed images loaded and no
rejected chains or upload/decode/factor failures. Source data and normal prefs
remain unchanged. 400 scaling comparisons, 400 ready-PNG round trips and nine
GPU cells at each of two scales pass; the wrong-sampler negative control is
detected. All 127 source tests pass, and all 76 PNG hashes reproduce exactly.
The remaster shortcut selects the registered build/pack with the existing
separate preview saves. This pilot scales original art; the full remaster and
campaign/FPS review are unfinished. Translation is still deferred.
See [complete-chain pack evidence](HD_REMASTER.md).

2026-11-15 remaster prototype: a separate, identity-checked private renderer
copy scales authored mip chains without modifying upstream or the normal exe.
400 CPU comparisons pass. Synthetic Vulkan tests verify constant/auto/slope
LOD, higher-mip rewrites, palette updates, fallback and banded large uploads at
two scales; a base-only sampler negative control fails as expected. The town
and camera/movement routes exit 0; the latter uploads 58 chains / 174 levels
with zero mip-upload failures. All 119 source checks pass. A dedicated
interactive preview opens and closes normally using copied WIP saves and
isolated preferences. Master saves, fonts, normal preferences and the normal
executable remain unchanged. This is original-art scaling, not finished
replacement-art coverage, campaign/FPS validation or a new PPSSPP equivalence
claim. Translation work is deferred. See [HD remaster evidence](HD_REMASTER.md).

2026-11-15 preset/recovery update: High Quality is available in the F1 Language
tab and Windows panel. Native navigation restores all eight effects, retains
the language, resets to Balanced and cleanly restarts WIP English. All fourteen
panel controls pass both presets; screenshots inspected. The new safe graphics
shortcut selects Original for one run without altering saved preferences,
verified by comparing safe and normal launcher preflights. Original, Balanced
and Quality startup checks all exit 0 with unchanged source saves/preferences.
All 115 source tests pass. Evidence: `private/quality-preset-native-01/`,
`private/quality-preset-panel-01/`, `private/quality-recovery-native-01/` and
`private/quality-recovery-preflight-01.json`. These are bounded startup/menu
checks, not a campaign/FPS claim. Mipmapped texture replacement remains a
renderer limitation; no unsupported call was hidden or framework guard removed.

2026-11-15: all implemented graphics quality effects are now enabled for fresh
profiles. At the user's request, the existing profile was backed up and updated
while keeping language, fullscreen/window size and VSync choices. All 113 source
tests pass. The combined FSR 1 / 4x rendering / AF16 / mipmaps / full colour /
SSAA2 / xBRZ4 / HD UI town checkpoint exits 0, loads 29 needed pack images with
zero replacement failures, and preserves source saves, fonts and preferences.
Evidence: `private/quality-defaults-native-01/summary.json`. This is a bounded
checkpoint, not a full campaign or gameplay FPS benchmark.

Graphics update: F1 Advanced now saves xBRZ texture smoothing (Off/2x–6x)
and HD English UI. The local pack covers all 94 printable ASCII glyphs across
48 pages, plus previous prompts/notices/numerals (52 images). The town save-point
route draws real scaled textures at 4x/AF16/SSAA2 and exits 0 without replacement
failures. All 14 panel controls and the complete F1/save/reset/restart route pass.
All 113 source checks pass, and the public rebuild command reproduces all 52
PNG hashes and the INI hash. A Windows acknowledgement sharing race found by
the test was fixed. This is
not a finished replacement-art remaster or full-campaign/FPS validation.
See [texture evidence and remaining coverage](TEXTURE_IMPROVEMENTS.md).

Latest HD font sample: 40 numeral glyphs and 19 observed English character-pair
textures added to the optional pack. The save-loaded message is visibly sharper;
full dialogue coverage remains unvalidated. Standard and enhanced 4x checks load
all 23 replacements with zero failures. All 107 source tests pass. A diagnostic
font-directory mismatch was corrected before creating the body-font sample.
See [font evidence and limitations](HD_FONT_SAMPLE.md).

HD UI update: the optional sample now contains seven rebuilt prompt labels and
two 4x English startup notices. Three real replacements load without failure;
viewport wrapping was corrected after native capture inspection. Paragraph/NPC
fonts remain unchanged and under investigation. All 103 source tests pass.
See [expanded UI evidence](HD_UI_EXPANDED.md). No campaign/FPS claim is added.

Graphics update: title-owned native Windows settings panel, persistent profiles,
1x–4x rendering and optional supported filtering/upscaling are implemented.
All 12 panel controls and three bounded graphics startup profiles pass; physical
1280x720 window sizing and host pause/resume verified with copied saves.
Campaign graphics quality/FPS and trace equivalence remain unvalidated.
See [graphics evidence and commands](GRAPHICS.md).

F1 integration: all twelve launcher graphics/language choices, presets and logs
are accessible in the host overlay. Changes persist; live fullscreen/scaling/HUD
use the existing presenter. A confirmed clean restart applies startup-only
settings and language. `Start-Game.cmd` and `Start-Launcher.cmd` enter the game
directly, defaulting to WIP English in a fresh configuration. Saves remain
separate by version. The full isolated menu/restart route passes, followed by
WIP startup using saved Balanced settings; all 95 source tests pass. Framework
sources/revision and guest instructions are unchanged; title-owned link wrappers
and executable identity are recorded in `host-ui-build.json`.

Active backend: Nakagawa Recomp 8704fba98007fff6d6f930365f2b2142af1bfbba.
See [framework evaluation](FRAMEWORK_EVALUATION.md) for actual candidate tests.
Input remains NPJH50503, disc 1.01 / app 01.00; no patched image was used.

| Gate | Actual evidence/result |
|---|---|
| Input/module survey | Exact disc and module hashes, encryption, imports and relocations recorded |
| Main loading | 5,898,569 bytes match PPSSPP outside 275 individually verified syscall patch words; zero unexpected differences |
| Generation | Main and runtime-placed LIBFONT generated; 111 primary chunks, empty fallback report; static coverage only |
| Windows x64 build | Linked successfully; PE machine AMD64 verified; diagnostic executable 197,180,205 bytes |
| Native integer entry prefix | PASS: all 14 instructions before first syscall match PPSSPP register and observed SW deltas; zero divergences |
| First syscall register checkpoint | DIFFERENT: at 0x08cbbcfc PPSSPP preserves r4/r5 while native writes deadbeef; boot-state cause under investigation |
| Full function / scheduler boot | NOT VALIDATED: direct route logs AOT_RETURN_TARGET_MISMATCH after the compared prefix; scheduler probe terminated after its 30-second bound |
| Runtime LIBFONT | Native probe places exact decrypted image and calls recompiled font exports; oracle lifecycle/placement/output not matched |
| First displayed frame | Native offscreen captures now show loading emblem, warning and save-data prompt; nine PPSSPP software reference images collected; synchronized image/window validation pending |
| Menu | No-save-data prompt observed in native and PPSSPP images; navigation/title menu not validated |
| Input | Explicit Up/Circle scripts advance native and PPSSPP from save prompt through media-check completion to Square Enix logo; keyboard/controller and full input correctness unvalidated |
| Audio | Not run |
| Gameplay | Not run |
| Save/load | Tutorial save recovered with verified backup; native and PPSSPP both report auto-load success from isolated copies; another save/exit/reload and gameplay state verification pending |

Tests: 11 title intake/import-tracing checks passed; 113 selected-framework loader/relocation/bounds
tests passed with GCC/Python 3.14, including the mutation test. PSPRecomp passed
1/1 and Yakumo passed 3/3 core CTest targets. Earlier compiler-unavailable,
sandbox-denied and overlapping-temp-directory test attempts were not accepted
as passes. Historical Tzeentchnet Python suite: 43 passed.

Environment: portable Python 3.14.0, pinned MSYS2 UCRT64 GCC 16.2.0-6, Make,
SDL3/SDL3_ttf and Vulkan headers/loader are installed privately. MSVC remains
available for PPSSPP and candidate-tool builds. No global toolchain or PATH
installation was changed. Sandbox exceptions were needed to execute unpacked
compiler binaries.

PPSSPP is source-pinned to 1aebad2c651ff9d0684ee335e43aceff8fc7e3ec with
interpreter CPU, software GPU and disabled function replacements. Captures use
isolated memsticks and record the executable hash. Its build warned that the
version-generation script could not find Git; the embedded version string is
not accepted as provenance.

The original empty-inventory and sectionless parser blockers are bypassed by
selecting a framework that actually supports those formats, without patching
the game or faking module success. No shared runtime source was modified.
The title-owned, hash-pinned import-trace emitter adapter corrected an observed
stale trace snapshot, preserving syscall effects and failure flow. The original
failed comparison remains private; the regenerated build passes the prefix.

The first scheduler probe correctly refused missing module input. The launcher
now supplies SR_MODULE_DIR and explicitly requests SR_REAL_MODULE_START=1.
LIBFONT declares no start routine; its recompiled sceFontNewLib, font-info,
glyph-rendering, close and cleanup exports are reached. Its ELF entry sentinel
is never called. The default route had kept host HLE instead; that run is not
accepted as guest font execution. Font files currently come from the framework's
substitute-font policy, so visual fidelity is unvalidated.

The latest headless 30-second probe reached raw-LBN opens and font calls, then
was terminated by the harness. A spin diagnostic appears, but later reads
continue: no deadlock or specific I/O implementation fault is established.
Several thread/SAS/cache HLE calls report unverified coverage. These logs are
diagnostic evidence, not passes. No audible output, input, gameplay or
save/load result was observed or accepted.

Evidence: private/native-prefix/result.json and comparison.log;
private/diagnostic-boot-30s/result.json and native.log. The latter records the
native executable SHA-256, framework pin, input hash and exact command.
Raw evidence, generated code and binaries stay outside Git.

The user's local test private/test-20261113-221429/ reproduced the same native
executable and input hashes, reached guest font calls and additional SAS pause
handlers, and was terminated at the configured 30-second limit. Its exit code 1
records harness termination, not an independently diagnosed game crash.

A fresh 96-step PPSSPP sample now covers the first thread creation and root
return. tools/compare-first-syscall.py reports an actual r4/r5 difference at the
first syscall, after the passing prefix. PPSSPP's LoadExec path calls
hleSkipDeadbeef and its first syscall consumes that pending flag; source review
suggests this inherited startup state explains the register preservation.
That interpretation is not hardware evidence and does not justify a title NID
special case or fake return. No runtime behavior was changed to hide the difference.
See LOA-F-008 for the exact scope.

Follow-up offscreen capture now provides real pixels. The first capture's
private working directory exposed a missing relative VFPU-table dependency
(process exit 0xc0000409, explicit fatal table-open message). The launcher now
supplies the absolute PSP_VFPU_TABLES path; runtime size/hash validation stays
enabled. The repeat runs to its 30-second bound and captures the loading
emblem, warning screen, media check and no-save-data prompt. The first CPU
frame itself is black. Native and PPSSPP reach the same no-save prompt, but
timing/fonts differ and no synchronized pixel or actual-window pass is claimed.
The legacy default START pulses were still enabled in these headless captures;
they are not neutral-input acceptance evidence.

Evidence: private/native-offscreen-frames/ retains the fatal run;
private/native-offscreen-tables/ and private/native-offscreen-later/ retain
CPU-presenter PPMs and lossless PNG previews. private/oracle-boot-images/
contains nine interpreter/software PNG references and their provenance.
PPSSPP ended at its emulated-time bound, returning 0; that is not a title pass.

Start-Preview.cmd now invokes tools/launch-preview.py for an experimental real
Windows GDI window with keyboard mapping and a fresh private memstick/log.
Full input/module hash and AMD64 preflight passed. The interactive window and
its keyboard controls/audio have not been tested; no playability claim is made.

Explicit scripted input now advances both native and oracle past the no-save
prompt to the media-check-completed message, and a further Circle press reaches
the Square Enix logo. Native ctrl_latch logs record the Up/Circle transitions.
These runs disable automatic pulses and use fresh isolated memsticks. They
prove this bounded route advances, not synchronized pixels or gameplay.
Native logo brightness differs because capture times are not aligned.
Evidence: private/native-scripted-confirm/, private/native-scripted-next/,
private/oracle-scripted-confirm-fixed/ and private/oracle-scripted-next/.
The first oracle input attempt rejected --press-script; the wrapper was corrected
to the verified --press option and rerun successfully. No failed run is a pass.

Next gates: measure root attributes, next UID, initial GE counter and complete
boot memory writes in PPSSPP; seed the scheduler with that measured contract
(native default root UID 0x110 differs from oracle 0x113); compare a full function
and resolve the direct host-return boundary. Then compare bounded scheduler,
LIBFONT and raw-LBN I/O sequences, including async descriptors/results, before
validating first frame, menu, input, audio, gameplay and save/load independently.
Neither a successful build nor static coverage makes the title playable.

Performance follow-up: the user reports the visible preview works with low FPS.
The examined GDI/software run initializes WASAPI audio and exits normally (0).
A separate TRACE=0/-O2 release executable now builds; the diagnostic build stays
available. Both flat image hashes agree. Runtime at 1,000 deterministic VBLANKs
is 23.091 s diagnostic/software, 22.175 s release/software and 7.105 s release/GPU.
The software captures match exactly. GPU output reaches the same save-data
prompt but differs in pixels; this is not an exact visual pass. A further
scripted GPU route reaches the Access Games logo and exits at VBLANK 1800.
Start-Preview.cmd now uses release/GPU; Start-Software-Preview.cmd selects the
software fallback. PERFORMANCE.md records commands, limits and private evidence.
No gameplay FPS or save/load claim is inferred from these boot measurements.

English v1.6 integration: the user-supplied patch decodes successfully into a
separate private image; the Japanese source remains hash-identical. Only the two
UPDATA REGFILE archives change content. Main executable and LIBFONT stay exact,
so the existing native code is reused. Native/GPU and PPSSPP software captures
both show the English no-save prompt. Start-English-Preview.cmd selects the
explicit hash-pinned English variant; Japanese remains the default/reference.
Read-only archive comparison covers 9807 groups and 18055 distinct resource IDs,
finding 16 changed message-bundle IDs. The message glyph/control encoding and
safe text reinsertion are still unresolved; no new translations have been added.
This integrates the existing partial patch, not a complete English translation.
See TRANSLATION.md. Total project checks: 20 passing after parser/identity additions.

Save recovery follow-up: the user's tutorial save was found in an earlier
per-run memstick, backed up and copied to private/memstick/japanese/. The
launcher now uses persistent per-language save storage, with a single-writer
lock. Japanese and English remain separate. Isolated native/GPU and PPSSPP
interpreter/software tests both show the game's successful auto-load message,
with fixture source hashes unchanged. Total project checks now pass 24.
See SAVE_STORAGE.md for exact evidence, backup and remaining validation limits.

Controller change: Vulkan previews now explicitly load the title camera profile.
Right-stick directions are secondary PSP D-pad bindings with threshold 12000;
the physical D-pad remains bound and other defaults are retained. The compiled
native profile/evaluator check passes all directions, deadzone and unchanged
mapping checks. No game executable, shared runtime or save files changed.
Actual controller camera feel remains for user testing; see CONTROLS.md.

Translation follow-up: the genuine 2357-codepoint glyph table now decodes Japanese
messages. Every exported MES bundle round-trips exactly (74 Japanese variants,
73 English variants). Plain-text editing, exact-variant RGF reinsertion and
candidate ISO generation are implemented; unknown inline commands remain refused.
Eight mercenary-help messages are translated in a private WIP candidate only.
All resource payloads and 308 ISO files verify against expected changes. Native
and PPSSPP both reach the saved-data-loaded prompt with copied Japanese saves;
the changed dialogue itself still requires an in-game layout/context check.
The stable English launcher remains pinned to the original partial v1.6 image.
39 title checks pass. Full English translation and bidirectional save validation
are incomplete. Shared storage is deferred until translation and compatibility
testing are complete, as requested. See TRANSLATION.md and SAVE_STORAGE.md.

Text-only translation pass 01 expands the private draft to 552 distinct messages,
covering 2949 repeated entries across 38 bundle variants. All resource payloads
verify, including unchanged audio. A separate Start-English-Text-Test.cmd selects
the candidate and a backed-up, independent tutorial-save copy; existing launchers
and their saves retain their original selection. Native bounded boot and PPSSPP
show the copied save auto-loaded. The extended native input route times out at
30 seconds while loading, before its requested VBLANK-3600 boundary; it is not a
passed route. New dialogue layout/context review, remaining text and full campaign
validation are incomplete. Text outside the decoded MES format remains in scope
for investigation; voices/audio are excluded at the user's request. 46 title
checks pass. A locked-source recovery regression is fixed by excluding the
runtime lock metadata from saved-game hashes and backup copying.

Text-only follow-up, 2026-11-14: measured command operands, legacy CP932-counted
save/install labels and timed subtitle records now have lossless codecs. The
text-test launcher selects the second directly authored candidate with 632
distinct translations, including 76 distinct subtitle arrays. Independent checks
verify 22,159 unchanged non-message payload instances, including Japanese audio,
and 98 unchanged timed cues across repeated archive instances. Native diagnostics
exit 0 at 1,000 VBLANKs; PPSSPP software diagnostics exit 0 at the 25-second
emulated bound and produce nine images. Saved-data-loaded prompts are observed;
cutscene layout, complete translation and campaign acceptance remain unvalidated.
The remaining text is being drafted locally with rejected records kept separate.
Four legacy entries and image-based text review remain unresolved. Machine draft
structure checks are not semantic approval. Original Japanese voices, music and
effects remain unchanged. Stable launchers and save namespaces remain separate.
See TRANSLATION.md for the candidate identity, scope and reproduction tools.

Expanded text pass 14: the test launcher now selects 9,979 changed message entries
across 68 MES variants, plus translated caution/demo-notice text in one bounded
XET variant. A rebuilt-archive scan finds zero ordinary MES translation jobs;
four legacy demo-save records remain unresolved and 14 literal password keys are
preserved. The adjacent 14 reward notifications are translated. Japanese audio
and non-text resources compare unchanged; subtitle clocks and cue boundaries
remain exact. All 308 ISO payloads verify. Native startup exits 0 at 1,000 VBLANKs;
PPSSPP exits 0 at 25 emulated seconds with nine captures. Both show the English
warning; source saves remain unchanged. All 85 title checks pass. Model-draft
semantic review, full texture audit, campaign layout/playthrough and bidirectional
save validation remain incomplete. These results do not establish 100% translation.
