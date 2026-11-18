# v0.9.0-beta.4

Testing pre-release for Windows x64. This is not full campaign acceptance.

## Changes

- Fix the Chapter 2 quest-start crash reported in issue #4. Converted companion
  names could exceed a fixed 18-byte field and corrupt a pointer. The native
  conversion now respects that field's bound, including when loading older
  saves. New English images also use shorter roster labels where necessary.
- Include the current English title, orb and item-description layout rules.
  Further visual review across the campaign is still needed.
- Keep original textures as the default and HD environments/models optional.
  Japanese audio remains unchanged. Existing render-scale, FSR and filtering
  controls remain available.

## Installation and updates

Download **Setup.exe** from this release. It downloads the matching verified
public sources/tools payload. On first Play, provide your own unmodified
Japanese PSP ISO: NPJH50503, disc 1.01. No ISO or prepared game files are supplied.

Windows 10/11 x64 and a Vulkan-capable graphics driver are required. Use a short
ASCII install path and allow about 18 GB free for installation, compilation and
optional full HD generation. No separate Git, Python, compiler or emulator
installation is required. Windows N editions need Microsoft's Media Feature
Pack for movies.

Existing compatible launchers can offer this update after publication. Setup
preserves saves, settings and ISO selection. Back up saves before beta updates.
Because native and English-image build inputs changed, expect a local rebuild
on next Play. HD remains opt-in and its first build can take hours.

## Validation and remaining issues

The quest-start fix was exercised with a copied Chapter 2 save: Poisonous
Invaders reached the playable field with both 30 and 60 FPS selected; movement
and action inputs responded after entry. These were accelerated diagnostic
routes, not performance benchmarks. All 386 public regression tests passed.

The release payload was extracted through the actual installer engine into an
empty test installation. Native code, English assets and subtitles were built
from the original ISO alone; no prepared game files were copied in. First setup
took about 8 minutes 20 seconds on the development PC, with HD disabled; this
is not a promised setup time on other PCs. Repeat setup reused completed
outputs. Both 30 and 60 FPS settings passed a 360-vblank native boot with
nonblank frames and zero interpreter entries or dispatch misses. The original
ISO and real saves were unchanged. Full optional HD generation was not repeated.

Full campaign completion, mission completion with this fix, a fresh save/load
round trip, and renewed co-op acceptance remain unverified. Intermittent audio
distortion and remaining text-container issues are still under review. This
release does not claim to resolve them.

Use GitHub issues to report location/quest, reproduction steps, solo/co-op mode
and the 30/60 FPS setting. F1 > Tester support exports a local diagnostic report;
nothing is uploaded automatically. Do not attach ISOs or other game files.
