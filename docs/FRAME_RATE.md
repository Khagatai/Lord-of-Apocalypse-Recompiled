# Gameplay frame-rate selection

Open **Start-Game.cmd**, then **F1 → Settings → Graphics → Gameplay frame rate**.
Choose **Original 30 FPS** or **Upgraded 60 FPS (experimental)**, save game
progress, then use **Apply and restart game** and its separate confirmation.
The external graphics panel exposes the same choice. Existing profiles migrate
to 30 without being rewritten; 30 is the default. Balanced/High Quality preserve
the selected rate. Original graphics restores 30.

This is a title timing enhancement, not a presentation-cap or turbo setting.
The PSP vblank clock, audio sample rates and movie timestamps are unchanged.
Decoded movies keep original timing in both modes. Movie context lifetimes
conservatively block the enhancement. This does not classify in-engine cinematic
scenes from their visuals.

## Implementation

The two original instructions match the timing sites identified by
[LunaMoo's NPJH-50503 patch, post #297](https://forums.ppsspp.org/showthread.php?pid=104163&tid=4799).
That author explicitly says to disable the patch for movies. The native title
extension adds automatic media protection rather than installing it unconditionally.

`frame_rate_codegen.py` verifies the exact instruction and control-flow shape at
the pinned sites and emits conditional timing seams during generation. Generated
C is never hand-edited. The 30 mode selects original instruction semantics.
The 60 mode changes the update floor from two tick units to one and changes the
alternate-frame sleep branch as in the cited patch. The existing elapsed-time
calculation remains responsible for movement/animation speed. The floor restores
to two before updates while media is active; enhancement resumes after teardown.

`gameplay_fps.c` observes registration of the real MPEG create/delete and PSMF
start/stop/delete handlers. Each real handler executes and retains its actual
return value; only successful calls change tracking. Multiple contexts remain
protected until all close. Untrackable or overflowing context sets conservatively
keep original timing. No PSP errors are replaced with success. All code is
title-owned; framework pin `8704fba98007fff6d6f930365f2b2142af1bfbba` is unchanged.

The ISO, executable module and flat guest image remain unchanged. The rebuilt
Windows executable contains an optional guest-timing enhancement, recorded
explicitly in `host-ui-build.json` with hashes of the timing/UI/renderer sources.

## Reproduction

```powershell
private/tools/python314/python.exe tools/title.py generate --profile release --jobs 6
private/tools/python314/python.exe tools/title.py build --profile release --jobs 6
private/tools/python314/python.exe -m unittest discover -s tests
private/tools/python314/python.exe tools/check-game-settings.py --output private/fps-menu-check --fps
private/tools/python314/python.exe tools/check-gameplay-fps.py --output private/fps-cadence-check
```

Checkers require fresh private report folders and use copied saves/isolated
preferences. The cadence check uses normal pacing at 2x with HD art off to
isolate timing. It measures new game-frame vblank gaps, not repeated host
presents. It does not establish performance with the full HD profile. The original baseline sometimes needs
three vblanks per frame. The gate requires the expected dominant period in at
least 85% of samples and a mean within 10%; stored timestep accumulation must
agree across modes within 3%. Actual movie-context samples must retain the
original update floor with enhancement off.

## Validation limits

186 source tests pass. Production media tracking passes synthetic tests in both
modes for simultaneous contexts, original errors, stop/delete, restoration and
conservative overflow (`private/fps-synthetic/`). Native F1 persistence passes
30 → 60 → 30 without changing normal saves/preferences
(`private/fps-in-game-settings-02/`). All 15 external panel controls and presets
pass (`private/fps-launcher-check/`). The first sandboxed F1 attempt could not
load the existing SDL font DLL; rerunning with DLL access passes.

The pinned PPSSPP interpreter independently confirms the original NOP retains
2.0 and the optional DIV produces 1.0 from both 2.0 and 1.0. Evidence:
`private/fps-instruction-oracle/result.json`. Those synthetic register-state
steps are not a matched gameplay/scheduler trace.

Two short deterministic boot routes failed to reach the intended gameplay
checkpoint in 60 mode. A longer deterministic route played the full opening
and reached town, with equal accumulated game time and protected movie timing,
but its rendering cadence failed. Its result remains **FAIL** in
`private/fps-complete-opening/result.json`; it is not a hardware FPS result.
The normal paced route is the acceptance path for the player-facing mode.

The paced town comparison measures **29.970 / 59.940 FPS** (151 / 301 new
frames in the five-second sample), with stored update time advancing exactly
one unit per vblank in both modes. Its raw report remains FAIL because it exposed
the original movie-start boundary and initially misaligned sparse audio logs
across restarted movies. The latter is fixed by comparing sampled AU intervals
within each context. Reviewed video PTS agree at 28 shared sampled frames;
audio start PTS and sampled per-AU clock agree across 23 / 8 observations.
No failed attempt is overwritten with a pass.

The final build additionally restores the original floor at the callback
boundary if that update created a movie. Its native HD town check measures
**59.940 FPS**, with every one of 301 sampled frame gaps equal to one vblank,
using 4x rendering, the HD pack, AF16, full colour and 2x supersampling. It loads
162 replacements and uploads 32 replacement mip chains / 96 levels, with zero
texture failures, mip rejections or interpreter instructions/entries/dispatch
misses. The movie-start sample has enhancement off and the original 2.0 floor
before the first decode. Source saves, fonts, normal preferences and pack
metadata remain unchanged. All 86 protected inputs/data files match their
baseline; the remaining protected file is the intentionally rebuilt executable.

Current executable SHA256:
`3429e2ea36906b790f92dc7ba5f7de9aeef502f9e95ab62e19e7291788ae747b`.
Evidence: `private/fps-final-review.json`, `fps-hd-paced/summary.json`,
`fps-hd-paced/run/frames.csv`, `fps-protected-files.json` and
`fps-final-preflight.json`. The review links the earlier comparator build and
the final corrected movie-boundary build explicitly. Both town screenshots
and the actual HD scene were inspected. These are short samples, not a soak.

HD check reproduction (use a reviewed private boot script):

```powershell
private/tools/python314/python.exe tools/check-hd-ui.py --output private/fps-hd-check --save-fixture private/memstick/english-text-test --padscript private/fps-native-wide-input/route.pad --frame-window 5500-5510 --seconds 180 --pack private/hd-remaster-pack --hd-ui --texture-scale 4 --quality --mip-textures --require-mip-replacements --gameplay-fps 60 --paced
```

Native cadence/update-speed evidence is recorded separately. Combat, full
campaign acceptance and every movie/cinematic route remain unverified, so 60
stays experimental. Hardware load can reduce achieved FPS with HD art, 4x
rendering and supersampling; the timing check does not measure that load.
