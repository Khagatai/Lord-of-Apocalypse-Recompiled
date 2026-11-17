# Expanded HD UI sample — 2026-11-14

The optional shortcut now selects the later [HD font sample](HD_FONT_SAMPLE.md),
which adds UI numerals and observed English character pairs. This document
records the earlier three-atlas pack and its retained evidence.

`Start-HD-UI-Sample.cmd` selects WIP English with the expanded private pack.
Use 4x internal resolution for its intended detail. Normal `Start-Game.cmd`
launches retain the original artwork. No global texture-pack preference is saved.

The pack contains three 4x replacements:

| Atlas | Improvements | Dimensions |
|---|---|---|
| Prompt labels | SKIP, TALK, NEXT, CLOSE, CANCEL, the Start-button SKIP label, WAIT | 256x512 |
| Existing English caution notice | Sharper header/body lettering; viewport-safe word wrapping | 2048x1024 |
| Existing English trial notice | Sharper body lettering; viewport-safe word wrapping | 2048x512 |

Controller symbols, borders and other artwork keep their source pixels. The
paragraphs on the save-loaded screen and NPC/conversation fonts are not replaced.
Environment, character, weapon and movie assets are unchanged. This remains a
small UI sample, not a completed HD pack. Japanese audio is unchanged.

## Build and integrity

`build-ui-font-sample.ps1` now accepts multiple text regions and paragraph blocks,
including optional viewport wrap widths. It measures wrapping locally, fills
font outlines at the target scale, rejects layouts outside their regions and
checks every pixel outside the union of edited regions against an exact source
replication. All three atlas builders reported zero outside-region differences.
The original single-label job also rebuilds to its exact previous PNG hash.

Private jobs preserve the existing English wording. Game-derived PNGs, jobs,
sample manifests and captures stay under ignored `private/`; no external image
service was used. Source tooling contains no extracted game assets.

`merge-ui-samples.py` combines individually verified atlases into a fresh pack,
rejecting duplicate texture keys and existing/non-private output directories.
The launcher verifies each image hash, its dimensions and the INI hash. Unsafe
or duplicate filenames, modified images and modified INI files are rejected.
The merged INI uses the real reader's supported content-key matching; it carries
no unsupported per-game override entries.

Selected candidate: `private/hd-ui-expanded-pack-02/`. Candidate 01 is retained
as rejected visual-test evidence: a notice line extended beyond the game's
visible 480-pixel picture despite fitting its 512-pixel source texture. Candidate
02 wraps body lines to 432 pixels while clearing the entire old text region.
The corrected direct 1920x1088 framebuffer capture was inspected: complete lines
fit inside the picture. A Windows PrintWindow capture omitted a line that was
present in the direct framebuffer; that window capture is not used to judge
content completeness.

## Actual validation

- Expanded prompt atlas: normal executable, exit 0, one loaded replacement,
  264 bound draws, zero failed/skipped/bad-factor textures. Evidence:
  `private/hd-ui-prompts-native-01/summary.json`.
- First combined candidate: all three loaded, 572 bound draws, exit 0; visual
  notice clipping was found separately, so this was not promoted.
- Corrected notice checkpoint (VBLANK 300–310): exit 0, both notice textures
  loaded, 198 bound draws, zero failed/skipped/bad-factor textures. Evidence:
  `private/hd-ui-expanded-caution-native-02/`; direct `frame_v309.png` inspected.
- Corrected combined pack: all three loaded, 562 bound draws, exit 0 and zero
  failed/skipped/bad-factor textures through the save-loaded prompt under
  `private/hd-ui-expanded-native-02/`. Automated quality/FPS fields remain false:
  runtime acceptance is not campaign, typography or performance acceptance.
- All 103 source tests pass, including multi-region compatibility, merged-pack
  integrity, duplicate-key refusal and private output protections. Existing
  saves/preferences were unchanged in isolated native checks.
- The normal executable remains SHA256
  `cb6ac96bb71b12dcc7f21b35f2cfc0071b35c3ddc4e5ddccc1319ea63302b594`.
  Framework remains pinned to `8704fba98007fff6d6f930365f2b2142af1bfbba`. A transient
  checkout change triggered the existing pin refusal; the original pin was
  restored before final checks. The guard was not relaxed.

## Paragraph-font investigation

The diagnostic-only observer now optionally reads one late frame through the
framework's existing read-only GE scene callback. A run at frame 970 captures
the actual sprite/triangle metadata and texture previews, rather than only the
cache's first upload. Evidence: `private/hd-ui-font-scene-01/` and
`private/hd-ui-probe-build-02/`. The normal executable does not link this observer.

The first 32x16 text previews were transparent because the relocated probe
executable lacked the normal release's project font directory. That environment
error was subsequently corrected; the previews are not valid evidence about
the visible paragraph font. Matched-asset GPU upload observations now identify
real character pairs, and the later sample sharpens the save-loaded message.
See the correction and coverage limits in HD_FONT_SAMPLE.md. The separate
early glyph-reconstruction filter test is still not treated as an improvement.

## Repeat locally

```powershell
powershell -NoProfile -File tools/build-ui-font-sample.ps1 -Job private/hd-ui-prompts-job.json -Output private/prompts-new
powershell -NoProfile -File tools/build-ui-font-sample.ps1 -Job private/hd-ui-caution-job-02.json -Output private/caution-new
powershell -NoProfile -File tools/build-ui-font-sample.ps1 -Job private/hd-ui-demo-notice-job-02.json -Output private/notice-new
./private/tools/python314/python.exe tools/merge-ui-samples.py --samples private/prompts-new private/caution-new private/notice-new --output private/expanded-new
./private/tools/python314/python.exe tools/check-hd-ui.py --output private/expanded-notice-check-new --pack private/expanded-new --frame-window 300-310
./private/tools/python314/python.exe tools/check-hd-ui.py --output private/expanded-save-check-new --pack private/expanded-new
./private/tools/python314/python.exe -m unittest discover -s tests
```

Use fresh private directories. To investigate fonts, build the separate probe
with `build-texture-probe.py`, then run `check-hd-ui.py --probe <private exe>
--font-scene --output <fresh private directory>`. No game data is uploaded.
