# Audio investigation and visual rollback

## Quest-completion investigation — 2026-11-16

The user now reports intermittent quest-completion distortion in **both solo and
co-op**. The exact quest/result transition has not been reproduced locally.
Audio is not accepted as fixed. No limiter, guessed delay, resampling option or
game audio asset was changed to conceal the issue.

The recent normal-run log `preview-20261116-192713-yx48u1mn` contains 21 windows
with more than 40 ms of channel-8 starvation. One window at VBLANK 70,679 reports
256.884 ms total starvation across four underruns, about 805.851 ms of GE CPU work
and 19 presents/second. Other affected windows include substantial GPU readback
waits. These are correlated one-second counters, not proof that a particular
quest completed then or that rendering is the only cause. There were no user
audio markers in that run. Private numeric evidence: `audio-quest-events.json`.

The identity-checked title audio source copy now has gated observational probes
for producer gaps, original PCM peaks/rails, gain-induced clipping and pre-clamp
SAS saturation. Normal launches enable the probes and existing performance
windows. Two short numeric lines per active-channel window use one write each;
the probes never change samples, gain, queue thresholds, guest time or PSP return
values. F1 diagnostic exports include only allowlisted numeric audio and
corresponding performance fields. Normal launches do not record PCM.

| Local check | Actual observation | Limit |
|---|---|---|
| 30-mode copied-save town/NPC-dialogue route, 751.447 s | Exit 0; zero observed SAS saturation, gain clipping or postmix clipping; one 3.653 ms boot underrun | Did not complete a quest or exercise its results jingle |
| Final-runtime 60-mode opening/movie route, 46.15 s of captured device audio | Exit 0; zero clipping/dumped-frame loss; one 2.240 ms underrun; measured mean A/V offset -85.398 ms | Partial opening, not full movie/campaign or listening acceptance |
| Synthetic source tests | All 276 pass, including rail versus clipping, signed gain rounding, long producer gaps and private numeric export | Measurements are not an audio fix |

Both native checks preserve source saves, fonts and preferences. The first town
run precedes the final single-write logger and negative-sample rounding diagnostic
refinements; its normal gain is unchanged. The final movie check uses the installed
runtime SHA256
`ce7dc7e24514ec3f656f8c3e59049c64c3efee2316d10441b546ca776014706d`.
The build exits 0 with three compiler warnings about possibly uninitialized
`SasRsGrain` fields in the pinned conditional band-limited mixer. They remain
recorded in the build log; this investigation does not identify them as the
reported failure. The framework checkout and pin remain unchanged.

Private evidence is under `private/audio-quest-review/`: analysis, build/tests,
recorded input and native runs. The 529,087,148-byte eight-channel town WAV was
hash-checked and removed after retaining complete postmix counters and one
20-second excerpt. No extra full image/archive/HD pack copy was created.
Japanese voices/music, the active WIP image, real progress and user settings stay
unchanged. Existing tester ZIPs are not refreshed by this source update.

Next: reproduce the failing quest/result/reward transition at each frame rate,
mark the moment through **F1 → Tester support → Mark audio problem**, and correlate
the new PCM/SAS and rendering measurements with the actual screen. A confirmed
long render/queue stall calls for scheduling/render-work investigation; measured
saturation calls for comparison of the relevant mixer/codec path with PPSSPP.
Do not classify an intentional stopped stream as a playback failure solely from
a long producer gap. No matching PPSSPP quest-completion trace was captured here.

For local copied-save exploration with bounded private sound recording:

```powershell
private/tools/python314/python.exe tools/campaign-session.py --output private/audio-quest-next --save-fixture private/memstick/english-text-test --minutes 10 --original-graphics --audio-diagnostics --capture-audio
```

Use a fresh owned output directory. Capture is opt-in and can be large on a
surround device; retain bounded excerpts after collecting the numeric evidence.

## Earlier audio investigation — 2026-11-15

The user reports intermittent distorted/desynchronised audio in boss fights and
movies. Audio is **not accepted as fixed**. Native movie measurements improved,
but a residual offset remains and no failing boss-fight capture has been reproduced.
Japanese voice/music payloads, real saves and the game images remain unchanged.

The released private runtime corrects a five-byte read of a six-byte PSMF header
timestamp: 90,000 was read as 351. Its parser now matches the pinned PPSSPP
`Core/HW/MediaEngine.h` and the framework's own `hle_mpeg.c` parser. A compiled
comparison passes 4,104 synthetic cases. This is reference-source evidence,
**not** a matching game playback trace from PPSSPP.

The regular audio queue now releases at one guest block, matching the framework's
documented PSP-HLE-AUDIO-REST-001 measurements. The separate host hold still covers
the measured device pull plus one display period of late scheduler wake. Short
512-frame buffers retain the same minimum physical headroom; movie 2,048-frame
blocks lose the unnecessary extra queued block. This remains an approximation of
the PSP's DMA/pointer behaviour, rather than a complete DMA implementation.

Both changes are generated into identity-checked private source copies by
`tools/media_runtime_patch.py` and linked through `tools/media-runtime.mk`.
Framework revision 8704fba98007fff6d6f930365f2b2142af1bfbba is unchanged.
No unsupported PSP networking/audio call was changed to fake success.

| Normally paced movie diagnostic | 30 FPS mean A/V offset | 60 FPS mean A/V offset |
|---|---:|---:|
| Before, `private/audio-baseline-01` | -214 ms | -216 ms |
| Header correction, `audio-timestamp-fix-01` | -132 ms | -130 ms |
| Header + one guest period, `audio-one-period-01` | -96 ms | -89 ms |

Negative is video presentation time minus audio playback time on the measured
source clocks. These ~47-second captures contain about 19 seconds of the opening
movie, not the full movie/campaign. There was no postmix clipping or dumped-frame
loss. The one-period 60 run includes one underrun counter event with 0.000 ms
reported starved; do not describe it as zero underruns. The separate final-normal
60 sample `private/audio-final-01` measured -94 ms with no clipping. Source-audio
timestamp provenance also needs care: its first PES timestamp was 85,069, whereas
the header origin was 90,000. The absolute remaining offset is not independently
accepted against PPSSPP playback.

After rejecting the candidate, the restored normal executable reproduces the
previous binary exactly: SHA-256
`15ed54979675ee1ead541d7c43b6863ed48a171f5db0448aa85c07fd7d07463f`.
`private/audio-normal-restored-01` confirms ~100 ms mean offset in 60 mode,
zero postmix clipping, and one 8.012 ms channel-8 starvation event during boot
(vblank 63, before movie decode). That run is not a claim of zero underruns or
corrected boss audio. Its source saves, fonts and normal preferences were
unchanged. The rendered town/inventory evidence uses the same renderer and
retained HD pack; the current generated guest image is unchanged.

A candidate following source audio timestamps and writing the decoded AU time
back to the guest passed a compiled failing-before/passing-after unit harness but
caused native 60 FPS underruns of 521–596 ms (`private/audio-source-clock-01`).
It is **excluded from normal builds**; only the explicit
`experimental_audio_clock=True` diagnostic argument emits it. Its synthetic pass
does not establish a successful fix. `tools/check-movie-au-clock.py` preserves
that reproduction and explicitly records native rejection.

Next audio work: capture a failing boss encounter, correlate audible break-up
with channel queue starvation, PCM/SAS saturation and texture/shader load stalls,
and compare the opening's actual guest AU/presentation timing against PPSSPP.
Do not compensate with a guessed global delay or silently enable a limiter.
Co-op remains deferred until audio acceptance, as requested.

## Original UI and retained HD 3D

Normal graphics environments set `LOA_ORIGINAL_UI=1`. At binding time, the private
renderer selects the guest-resolution texture for PSP through-mode (2D) draws,
bypassing HD replacements and xBRZ. Transformed 3D draws keep their HD bindings.
This decision is per draw, so a shared atlas retains its 3D replacement. It does
not delete translated text or replace the selected language's artwork. Dialogue
portraits remain original. No settings schema/preferences were reset; the old
`hd_ui` JSON key remains for compatibility, labelled HD world/models in both UIs.

The title and inventory captures were visually inspected. The paced inventory
route retained readable English item names/descriptions and original icons,
bound original textures on 600,973 2D draws, loaded 167 HD replacements and uploaded
32 replacement mip chains/96 levels with zero texture failures. The separate
title capture finished cleanly, but its old generic checker returned failure
because that title scene used no mip chains. Keep that failed requirement result;
it is not a game crash or evidence of successful mip rendering there.

`tools/sharpen-player-textures.py` applies 25% local detail, capped at 6/255 per RGB
channel, to nine player atlas names identified from existing native 3D captures.
Eighty PNGs were updated in the one existing pack. `tools/check-player-detail.py`
verified exact alpha preservation and the RGB cap on every before/after PNG;
flat-colour/transparent/detail synthetic checks also pass. Mesh geometry is
unchanged. One scoped 53 MiB rollback is kept in `private/player-clarity/rollback`;
no whole pack/image copy was made. Repeated application is refused or a no-op,
preventing accumulated sharpening. Other outfits are not claimed sharpened.

The sharpened player/town capture was visually inspected at 4x native rendering:
`private/ui-player-final-town-01/run/native-4x.png`. It loaded 160 replacements and
32 complete mip chains with no failures, retaining the original HUD. This checks
the renderer/pack; final subjective quality and busy-combat performance still
need the user's review. Pack manifest after the detail pass:
`ca9a13ea02681e8e4f08c6c6622c9aa81026b5152ef3ec3fee95a1e53d4d43b4`.

## Local commands

Use `Start-Game.cmd` to test the updated normal game with saved preferences.
F1 opens settings. Save progress in the game before restarting.

```powershell
private/tools/python314/python.exe tools/title.py build --profile release --jobs 6
private/tools/python314/python.exe -m unittest discover -s tests
private/tools/python314/python.exe tools/check-movie-timestamps.py
private/tools/python314/python.exe tools/check-audio-quality.py --output private/audio-review-next
private/tools/python314/python.exe tools/check-player-detail.py
```

Diagnostic outputs must be fresh private folders; game windows use copied saves.
All audio/images and game-derived artifacts stay local and Git-ignored.

Final checks: 197 source tests pass; the source index audit contains 237 UTF-8
files plus two pinned gitlinks and no protected/binary paths. The framework
checkout remains clean. Removed 907,362,064 bytes of redundant trial executables,
intermediate WAVs and raw QA frames (158 individual files), with paths/hashes in
`private/audio-ui-cleanup.json`. PNG captures, all copied/real saves, reports and
logs, baseline/final/failing diagnostic WAVs and the scoped player rollback stay
available. No recursive directory deletion or full-pack duplication was used.
