# v0.9.0-beta.5

Testing pre-release for Windows x64. This is not full campaign acceptance.

## Changes

- Retain the Chapter 2 quest-start fix from beta.4, reported in issue #4. Converted companion
  names could exceed a fixed 18-byte field and corrupt a pointer. The native
  conversion now respects that field's bound, including when loading older
  saves. New English images also use shorter roster labels where necessary.
- Include the current English title, orb and item-description layout rules.
  Further visual review across the campaign is still needed.
- Keep original textures as the default and HD environments/models optional.
  Japanese audio remains unchanged. Existing render-scale, FSR and filtering
  controls remain available.
- Reuse verified HD texture jobs across English/archive updates. Only new,
  changed, missing or damaged jobs are generated again. Setup reports reused
  and pending counts, retains existing PNGs in place and can resume interrupted
  metadata updates. Preserve both the HD pack and its `private/local-build/HD-work`
  completion records when moving an installation.
- Fix startup failing with `Existing locally rebased HD recipe differs`.
  An update can refresh an owned generated recipe and retain compatible texture
  jobs. Unknown or manually changed files remain protected.

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
Existing verified native and English-image outputs from beta.4 can be reused;
this update changes HD setup/cache handling. Older releases may still require
a native/English rebuild. HD remains opt-in and its first build can take hours.

## Validation and remaining issues

The quest-start fix was exercised with a copied Chapter 2 save: Poisonous
Invaders reached the playable field with both 30 and 60 FPS selected; movement
and action inputs responded after entry. These were accelerated diagnostic
routes, not performance benchmarks. All 403 public regression tests passed,
including archive-change cache reuse, damaged-file repair, cancellation recovery
and full-builder checks for zero processing on a cached pack and exactly one
generated job when one is missing.

The player code passed clean ISO-only generation with HD disabled, followed by
an actual installer upgrade to beta.5. The player-stage input identities match
the clean-build candidate. No prepared game files were copied in. The upgrade
preserved native and English outputs; subsequent setup reused them. Both 30 and
60 FPS settings passed a 360-vblank native boot with nonblank frames and zero
interpreter entries or dispatch misses. The original ISO and saves were unchanged.

A read-only audit against an existing full HD installation verified 28,179 PNGs
and found all 17,039 jobs reusable against the updated archive: zero regeneration
jobs, zero neural inference and zero texture copies. That cold verification took
about 4 minutes 32 seconds here; verification speed varies by PC and storage.
The startup recipe error was checked using the existing installation's real
recipe metadata in an isolated fixture. The installed game was not modified.
Full optional HD generation was not repeated.

Full campaign completion, mission completion with this fix, a fresh save/load
round trip, and renewed co-op acceptance remain unverified. Intermittent audio
distortion and remaining text-container issues are still under review. This
release does not claim to resolve them.

Use GitHub issues to report location/quest, reproduction steps, solo/co-op mode
and the 30/60 FPS setting. F1 > Tester support exports a local diagnostic report;
nothing is uploaded automatically. Do not attach ISOs or other game files.
