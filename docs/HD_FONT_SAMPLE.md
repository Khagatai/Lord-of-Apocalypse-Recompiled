# HD numeral and English body-font sample — 2026-11-14

`Start-HD-UI-Sample.cmd` now selects `private/hd-ui-expanded-pack-06/`: the
previous prompts/notices, 40 UI numeral glyphs in four styles, and 48 measured
English character-pair textures covering all 94 printable ASCII glyphs. Use 4x
internal resolution to inspect the new detail. F1 Settings → Advanced →
**HD English UI** enables this pack for normal WIP launches after a restart.
The 2026-11-15 quality defaults enable the pack for WIP English. The earlier
atlas work left preferences unchanged; the subsequent defaults update backed
up and updated the user's profile at their request.

The save-loaded message is now visibly sharper. Its wording, line breaks and
placement stay the same. Character metrics and guest font code are unchanged:
the renderer replaces matching texture content with higher-resolution images.
This does not complete all fonts or NPC dialogue styles. Non-ASCII characters,
unmatched palettes, glyph combinations and other fonts retain their original
images. Japanese voices, music and sound effects are unchanged.

## Complete ASCII atlas pass

The diagnostic observer anchors to an actually drawn R/S texture identity and
copies the adjacent 48-page atlas read-only using the framework's checked guest
memory reader. It does not assume a PSP memory base or change guest state.
Every page is hashed with the pinned native texture hasher. An independent
Python check derives all 16 palette values from the observed anchor and exactly
reproduces the RGBA bytes of all 19 previously drawn pages. This establishes the
character-pair layout before preparing unseen replacements. Space and DEL stay
blank/original; 94 printable characters are typeset inside measured cells.

The 52-image pack has INI SHA256
`2cbe89e2cd4bbb5461cd35995cbfdac4af765fb731ac2bebeeca8ee1953fe6e0`.
All glyphs were inspected on a private contact sheet. Native startup loads the
23 needed images, and the town route loads 29, with no failed, skipped or bad-
factor replacements. Other entries remain available when their text is used;
this does not mean all glyphs have been observed in every dialogue layout.

Repeat the measured generation without relying on private helper scripts:

```powershell
./private/tools/python314/python.exe tools/build-texture-probe.py --output private/ascii-probe-new
./private/tools/python314/python.exe tools/check-hd-ui.py --output private/ascii-capture-new --probe private/ascii-probe-new/texture-probe.exe --gpu-font-upload
./private/tools/python314/python.exe tools/build-ascii-font-pack.py --capture private/ascii-capture-new/run --output private/ascii-rebuild-new --base-samples private/hd-ui-prompts-pack-01 private/hd-ui-caution-pack-02 private/hd-ui-demo-notice-pack-02 private/hd-ui-numerals-pack-02
```

The rebuilt pack is under `private/ascii-rebuild-new/pack`. All sources, jobs,
captures and generated PNGs stay private. Below is retained evidence from the
earlier 19-page sample, superseded in coverage by the 48-page pass above.
The checked-in rebuild command was executed as `private/ascii-repro-complete-01`:
all 52 PNG hashes and the INI hash exactly match pack 06.

## Font observation correction

The earlier relocated diagnostic executables lacked the sibling `font/` assets
present beside the normal game executable. Their logs explicitly reported
missing project fonts. Their transparent glyph previews are not evidence that
the visible paragraph font has no texture representation. Those observations
are superseded by the matched-assets experiment below.

`runtime_assets.configure_fonts` now supplies the normal release's absolute font
directory to relocated diagnostics, preserves a valid explicit configuration,
rejects missing/relative/empty font roots, and records every font-file hash.
No fake font return or synthetic PSP success was introduced. The actual project
font files and guest font routines are still used. New tests cover this missing-
asset regression. Diagnostics check that the font files remain unchanged.

The separate observer wraps `ge_decode_tex_rgba` to record its actual output to
the GPU cache. It calls the real decoder first and changes no output pixels.
It is not linked into the normal release. With matching fonts it captured
nonempty 32x16 character-pair textures. The private contact sheet on a black
background made their white, alpha-covered letters visible for inspection.

## Asset construction

The numeral atlas contains four styles of digits 0–9. The private job replaces
their measured ink boxes inside 40 disjoint cells. The body-font jobs replace
37 identified English characters/punctuation across 19 two-character pages;
blank or unidentified cells are retained. The private mapping and game-derived
PNGs are not committed.

Arial regular outlines were used for the body-text sample, with no added outline;
bold/italic styles are available for numeral samples. Every job preserves cell
coordinates and verifies zero pixel changes outside its selected regions. Font
shapes differ from the source bitmap face, so this is a legibility prototype,
not recovery of an original high-resolution font. No font files are redistributed.
All typesetting is local; no game image was uploaded to an external service.

Replacement keys retain the real palette/dimension identity and content hash,
with the address wildcarded through the supported reader. Duplicate identities
are rejected by the merger. The optional launcher verifies all 23 PNGs and the
INI against the private manifest. Unlisted textures use the renderer's original
path. The source image, game dump, translation image and save files are not
patched by the pack.

## Actual checks

- Four-atlas numeral candidate: exit 0, 4 textures loaded, 1,332 replacement
  draws; no failed/skipped/bad-factor images. Evidence:
  `private/hd-ui-numerals-native-02/summary.json`.
- Matched-font GPU observation: exit 0; actual nonempty glyph uploads captured
  in `private/hd-ui-gpu-font-upload-02/`. Earlier `*-01/` observations without
  fonts are retained as invalid-environment evidence.
- Standard 4x body-font check: exit 0, all 23 textures loaded, 34 lookup hits,
  45,620 bound replacement draws; zero failed/skipped/bad-factor images.
  Evidence: `private/hd-body-font-native-01/summary.json` and inspected screenshot.
- Enhanced check: 4x rendering, 16x anisotropy, mipmaps, full colour and 2x
  supersampling; exit 0, all 23 loaded, 43,810 replacement draws, zero failures.
  All 54 recorded font files, source saves and preferences stayed unchanged.
  Evidence: `private/hd-body-font-quality-native-01/summary.json`; the actual
  save-loaded message was inspected. These are not gameplay FPS benchmarks.
- All 107 source tests pass. The normal executable remained SHA256
  `cb6ac96bb71b12dcc7f21b35f2cfc0071b35c3ddc4e5ddccc1319ea63302b594`.
  The pinned observer build regenerated 112 private game/library compilation
  units after the earlier checkout restoration; its generation fallback report
  remained empty. No generated C or binary is staged.

The first private body-font job preparation placed the blank/bang pair in the
wrong half; the empty-cell check refused it. The corrected job uses the right
cell. A nested PowerShell process also lacked Get-FileHash autoloading; hashing
now uses .NET SHA256 directly. Failed partial outputs are retained separately.

Broad visual-quality and gameplay-FPS fields remain false in automated reports.
This validation covers the sampled message and pack loading, not a campaign,
all NPCs, physical input, save conversion or new PPSSPP trace equivalence.

## Repeat locally

```powershell
./private/tools/python314/python.exe tools/build-texture-probe.py --output private/font-probe-new
./private/tools/python314/python.exe tools/check-hd-ui.py --output private/font-observation-new --probe private/font-probe-new/texture-probe.exe --font-scene --gpu-font-upload
./private/tools/python314/python.exe tools/check-hd-ui.py --output private/font-sample-new --hd-ui
./private/tools/python314/python.exe tools/check-hd-ui.py --output private/font-quality-new --hd-ui --quality
./private/tools/python314/python.exe -m unittest discover -s tests
```

Use fresh private output directories. Private glyph jobs can be rebuilt using
`build-ui-font-sample.ps1` and combined with `merge-ui-samples.py`. Their source
PNGs, measured cells and character assignments remain local. Next work is to
extend capture/review to non-ASCII characters, other palettes/styles and gameplay
dialogue, then test other resolutions and actual reading conditions.
