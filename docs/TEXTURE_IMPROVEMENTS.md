# Texture improvements and remaining remaster work — 2026-11-14

Update 2026-11-15: a separate [HD remaster prototype](HD_REMASTER.md) now scales
authored mip chains and has passed synthetic GPU and native movement checks.
The original renderer limitations below still apply to normal launchers and
to mipmapped replacement packs. The prototype does not modify upstream or the
normal executable, and uses separate saves/preferences for interactive testing.

Open **Start-Game.cmd → F1 → Settings → Advanced**. Texture smoothing (xBRZ)
offers Off and 2x–6x. HD English UI selects the locally generated 52-image pack
for WIP English. Save progress in-game, choose **Apply and restart game**, then
confirm. As of 2026-11-15, fresh profiles enable HD UI and 4x smoothing along
with all other implemented quality effects. Higher values use more memory and
can soften small details. Original and Balanced reset both.

These settings use the existing pinned Nakagawa renderer. No upstream source,
guest instructions, PSP return values, timing or Japanese audio were changed.
The title's host settings extension changed; the 2026-11-15 preset/recovery
build is SHA256
`3b1d62c043475b2d244ace8d7c840309ed02d4b17d1fdea3e4eca194482b293c`.
The flat game image remains SHA256
`b0d370ebcfb33df3517a40c97c1b5c0ef0f6d7ed71a1efc6a4fce7e73c46dfb0`.

## What texture scaling covers

xBRZ scales host copies after the actual palette decode. Two workers prepare
copies asynchronously; the renderer uses the original until a matching scaled
copy is available. The configured GPU copy budget is 512 MiB. Copies whose
source/palette changed are invalidated. Render targets and textures overlapping
them are excluded. Single-level textures are eligible; original textures with
multiple mip levels are excluded. Factors reduce when a side would exceed
2048 pixels. The smart 2D filter stays off because it can harm softened fonts.

Further source inspection on 2026-11-15 confirms **replacement packs also skip
multiple-level textures** in this pinned renderer: `tex_xs_offer` calls
`tex_repl_find` only for `levels == 1`, and `tex_xs_eligible` rejects other level
counts. Generating more PNGs alone cannot bypass that limitation. Improving
those textures needs mip-aware renderer support with correct LOD selection,
palette/content invalidation and GPU lifetime tests. This investigation did
not remove the guard, drop the game's mip levels or modify the framework.

The existing read-only XET inventory contains 5,176 resource variants and 10,752
texture descriptors: 8,310 single-level and 2,442 with multiple levels. There
are 3,016 distinct texture names. These include repeated resource variants;
they are not a count of unique pieces of art, nor proof that every single-level
texture will be eligible at runtime. Evidence: local
`private/translation/texture-audit-03/` and `private/graphics-coverage-01.json`.

Scaling is available throughout eligible gameplay scenes, including character
and environment textures. It smooths existing artwork; it does not create
authored high-resolution detail, raise polygon counts, remaster movies, or
replace all game textures. A full replacement-art remaster remains unfinished.

## Actual checks

- The complete ASCII atlas reproduces all 19 captured reference pages exactly
  before rebuilding 94 printable glyphs. The resulting 52-image pack includes
  previous prompts, two notices and four numeral styles. The full glyph contact
  sheet and save-loaded message were inspected locally.
- Startup, 2x texture scaling: exit 0; 23 needed pack images loaded, 46 scaled
  uploads, 57,270 scaled bindings, no replacement failures or budget shortages.
  `private/hd-ascii-native-01/summary.json`.
- Route to VBLANK 3500–3510, 2x scaling: exit 0; 29 replacements loaded, 127
  scaled uploads, 107,854 scaled bindings. The checkpoint is a loading screen,
  not gameplay validation. `private/hd-ascii-route-xbrz2-01/summary.json`.
- Route to VBLANK 5500–5510 reaches the player in town by a save point. With
  4x internal resolution, xBRZ 4x, AF16, host mipmaps, full colour and SSAA2:
  exit 0; 29 replacements loaded, 137 scaled uploads and 124,711 scaled binds;
  no failed/skipped/bad-factor replacements or budget shortages. Scaled-copy
  peak was 154 MiB. 54 stale-copy events invalidate changing sources; this
  counter is not a claim that old content was drawn. The screenshot was
  inspected. `private/hd-ascii-route-xbrz4-01/summary.json`.
- All fourteen Windows panel controls and Balanced reset passed; screenshot
  inspected. `private/texture-settings-panel-01/result.json`.
- The final F1 route saved xBRZ 2x and HD UI On, changed language, reset both
  enhancements through Balanced, required separate restart confirmation and
  restarted WIP English successfully. `private/texture-settings-native-03/`.
- A separate town comparison holds all other options fixed with xBRZ off/4x:
  `private/hd-ascii-route-baseline-01/` and
  `private/hd-ascii-route-xbrz4-only-01/`. Both exit 0 with 29 pack images loaded
  and zero replacement errors. Changes to the world are limited; this does not
  restore missing texture detail. The 4x run has three queue-full events, for
  which the renderer keeps original textures while workers catch up.
- Maximum-factor startup with the saved-toggle HD UI selection also passes:
  `private/hd-ascii-xbrz6-01/summary.json` reports actual scaled draws, 23 needed
  pack images loaded and zero replacement errors/budget shortages. 6x is not a
  campaign performance recommendation.
- All 113 source checks pass, including larger pack integrity, saved-toggle
  language routing, legacy preferences and transient sharing-error recovery.
- Source saves, all 54 recorded font files and global preferences remained
  unchanged in native graphics checks. The F1 test used isolated preferences.

An initial final-menu test hit a genuine Windows acknowledgement sharing
violation (`texture-settings-native-02`). Native reads now allow delete-sharing
so atomic replacement can succeed; the supervisor retries transient permission
errors for a bounded 180 ms. The failure and successful rerun are retained.

These are bounded rendering/menu checks, not a full campaign, gameplay FPS
benchmark, every NPC/layout review, save-conversion test or new PPSSPP trace
equivalence claim. Enhancement frames are intentionally changed. The native
runtime explicitly labels these enhancements as guest-visible.

## Repeat

Use fresh private output directories. Commands operate on copied save fixtures:

```powershell
./private/tools/python314/python.exe tools/title.py build --profile release --jobs 4
./private/tools/python314/python.exe tools/build-settings-menu.py
./private/tools/python314/python.exe -m unittest discover -s tests
./private/tools/python314/python.exe tools/check-game-settings.py --output private/texture-menu-new --restart
powershell -NoProfile -File tools/check-settings-menu.ps1 -Output private/texture-panel-new
./private/tools/python314/python.exe tools/check-hd-ui.py --output private/texture-town-new --pack private/hd-ui-expanded-pack-06 --texture-scale 4 --quality --padscript private/translation/work/text-pass-01-route.pad --frame-window 5500-5510
```

The route is a private, measured input fixture, not an invented PSP API result.
For a fair xBRZ comparison keep other options fixed; `--quality` adds several
effects and cannot isolate xBRZ by itself. Further authored-art work needs a
verified replacement for each chosen texture, review at its in-game UV seams,
alpha/palette and mip behavior, and coverage in actual locations and quests.
Unseen layouts and mipmapped world textures are the next concrete coverage gaps.
