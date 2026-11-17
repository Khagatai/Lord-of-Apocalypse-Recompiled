# Text sharpening experiment — 2026-11-14

Result: no demonstrated improvement at the WIP English save-loaded prompt.
No graphics preference, menu option, executable, game image, translation or
audio was changed by this experiment. The next useful asset experiment is an
HD font/UI replacement sample, rather than enabling this filter globally.

The pinned renderer has an optional `glyphs=on` key in `SR_ACE`. It reconstructs
eligible small text sprites at 2x–4x rendering resolution. It refuses rectangles
with multiple ink colours, among other source formats. It can modify the guest
framebuffer where it applies, so this is an enhancement experiment, not native/
PPSSPP correctness evidence. The production graphics menu leaves it off.

## Actual checks

- Pinned renderer CPU self-test: PASS, 1,057 checks; GCC compilation and test
  exited 0. Private build/test logs: `private/text-sharpening-cpu-01/`.
- Native 4x A/B: same WIP image, executable, save fixture and Enhanced settings,
  changing only `glyphs=off` to `glyphs=on`. Both windowed runs exited 0.
- Enabled run reported `bound=0`, `tiles_built=0`, `page_decodes=8`, `images=0`
  and `colour=23` refusals. The filter rebuilt no text in this sampled route.
  This does not prove every font or conversation in the game is ineligible.
- Matching framebuffer files have identical hashes. One swapchain snapshot
  was absent from the enabled run; unequal file sets are not a pixel difference.
- Full-resolution window captures were attempted at a measured 1920x1088 client
  area. The enabled run's Win32 PrintWindow capture was black despite a success
  return. Both PNGs were inspected; `capture-sanity.json` records 0 nonblack
  samples out of 7,973 in that image. The full-resolution visual comparison is
  therefore inconclusive, and no improvement or renderer failure is inferred
  from that window capture.
- Original save fixture and saved graphics preferences stayed unchanged. All
  game data, screenshots and logs remained local in ignored `private/`.

Evidence: `private/text-sharpening-check-02/comparison.json`, per-run logs and
`capture-sanity.json`. The initial frame-exit diagnostic in
`private/text-sharpening-check-01/` skipped GPU cleanup and therefore omitted
usage counters. Its initial report's zero usage was not supported by counters;
the normal-close second experiment established the actual zero result.

## Reproduce

```powershell
./private/tools/python314/python.exe tools/check-text-sharpening.py --output private/text-quality-new --windowed
```

Use a fresh private output directory. This briefly opens two game windows with
copied saves, captures the save-loaded prompt, and closes each normally. The
non-windowed mode uses frame-exit diagnostics and can lack shutdown statistics;
missing counters are reported as unknown. A successful startup is separate from
feature usage, visual quality and gameplay FPS; none implies another.

To repeat the synthetic test, compile the pinned framework's
`src/rt/gpu_sdl3vk/glyph_recon_selftest.c` together with `glyph_recon.c`, using
the project's private GCC with `-O2 -std=c11 -Wall -Wextra -lm`, writing the
executable under `private/`, then run it. No game inputs are used by that test.

For an HD sample, first identify the font atlas and UI textures actually used
by the target screen, then author a replacement at a whole-number scale and
validate the renderer's pack hash/lookup, transparency, UV alignment and text
layout. Keep original textures available as the fallback. The existing local
archive inventory parses 5,176 resource variants, but inventory coverage is not
proof of replacement coverage or a completed HD pack.
