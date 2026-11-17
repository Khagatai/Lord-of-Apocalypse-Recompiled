# First HD UI sample — 2026-11-14

The optional shortcut now selects the [expanded HD UI sample](HD_UI_EXPANDED.md):
seven prompt labels and two existing English startup notices. The one-label
proof below records the original version and its retained evidence.

The original sample opens WIP English with one experimental replacement:
the **NEXT** prompt label. Set F1 > Settings > Graphics > Internal resolution
to 4x, then Apply and restart, to see the new detail at its intended scale.
The sample stays enabled across graphics restarts into WIP English, and is
dropped if restarting into another language/version. It does not save a global
texture-pack preference. `Start-Game.cmd` keeps the original artwork.

This is a one-label proof, not an HD edition of the game. Other prompt labels,
body text, decorative borders, environments, characters and movies are still
the original assets. Japanese audio and the game image are unchanged. The
interactive sample uses the existing WIP save folder and backup/locking policy;
automated checks use copied saves and never write the original save fixture.

## What was built

The existing renderer supports content-keyed PNG texture replacements. A
separate diagnostic executable observes actual texture lookups, records their
keys and decodes their images using the existing GE viewer decoder. Its lookup
wrapper always delegates to the real function; it makes no PSP API substitutions.
It is never linked into the normal release. The normal executable SHA256 stayed
`cb6ac96bb71b12dcc7f21b35f2cfc0071b35c3ddc4e5ddccc1319ea63302b594`.

35 distinct texture identities were captured at the save-loaded prompt. The
small prompt-label atlas was selected by local inspection. A private job redraws
only NEXT with vector font outlines using Windows System.Drawing, at 4x scale.
The 64x128 atlas becomes 256x512. The rest is exact pixel replication; the
builder checks **zero changed pixels outside the selected text rectangle**.
This preserves source pixels there but adds no detail to their artwork.
The word's new serif type differs slightly in shape and weight; it is a draft
for visual review. No original texture was sent to an external image service.

The replacement key omits the address while retaining the palette/dimension
identity and content hash, using the reader's existing wildcard lookup. It
targets the observed atlas rather than a presumed memory address. The optional
launcher verifies the exact PNG, INI and sample-manifest hashes, enforces private
storage, requires Vulkan/WIP English and logs the selected pack. Unknown or
modified sample files fail preflight rather than silently applying.

The PNG and INI are under `private/hd-ui-next-pack-01/`; source game images,
decoded atlases, sample job, captures and diagnostic binaries remain private.
No game-derived artwork is staged or redistributed.

## Actual results

- Diagnostic build: exit 0; original game executable unchanged. Evidence:
  `private/hd-ui-probe-build-01/build.json`.
- Texture identification: exit 0, 35 identities, zero replacements with the empty
  pack, source saves/preferences unchanged (`private/hd-ui-identities-02/`).
  The first attempt timed out waiting for frame 991 despite successful captures
  at frames 990/992; the gate was corrected to accept a successful GPU capture
  anywhere within VBLANK 990–1000. No failure was counted as success.
- Local sample builder: output 256x512, zero changed pixels outside the selected
  rectangle; PNG SHA256
  `003db9d839cbe0f8212270b1d754e09768ed7be559c215f4778db771ea2aec06`.
  Its first C# compile lacked the System.Drawing reference; the corrected build
  succeeded. Original bitmaps and font files are not included in source control.
- **Normal executable**, real texture reader: exit 0, one replacement loaded,
  one lookup hit, **256 bound draws**, zero failed loads, skipped textures or
  bad factors. Evidence: `private/hd-ui-next-native-01/summary.json` and native
  log. The reader emits one note that INI per-game overrides are not applied;
  the launcher's WIP-only gate remains explicit.
- The captured 1920x1088 client image was inspected: NEXT uses the new, sharper
  lettering in the expected location; paragraph text and borders retain their
  original appearance. Automated reports leave broad visual-quality acceptance
  false; this inspection covers only the sampled label/screen.
- Sample launcher preflight passes. All 98 title source tests pass, including
  modified-file rejection and preservation of audio/other enhancement choices.
  No gameplay FPS, campaign, full texture coverage or new PPSSPP trace claim.

## Reproduce locally

```powershell
./private/tools/python314/python.exe tools/build-texture-probe.py --output private/hd-probe-new
./private/tools/python314/python.exe tools/check-hd-ui.py --output private/hd-identities-new --probe private/hd-probe-new/texture-probe.exe
powershell -NoProfile -File tools/build-ui-font-sample.ps1 -Job private/hd-ui-next-job.json -Output private/hd-pack-new
./private/tools/python314/python.exe tools/check-hd-ui.py --output private/hd-native-new --pack private/hd-pack-new
./private/tools/python314/python.exe -m unittest discover -s tests
```

Use fresh private output directories. The private job records the selected
source PNG, texture key, font, changed rectangle and ink bounds. It is game-
derived configuration, so it is not committed. The source tooling is generic.

The remaining prompt labels and startup notices are now rebuilt in the expanded
sample. Paragraph/conversation fonts remain under investigation. Environment
and character textures are later, separate samples.
