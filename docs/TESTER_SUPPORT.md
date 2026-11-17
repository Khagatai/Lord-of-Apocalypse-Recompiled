# Testing tools and save protection

Run `LordOfApocalypse.exe`, then open **F1 → Tester support**.

- **Mark audio problem** records elapsed host time. Use it as soon as practical
  after distortion or desync; the marker does not record sound or fix playback.
- **Export bug report** writes a local ZIP under `private/bug-reports/`.
- **Open report folder** opens that directory; nothing is uploaded automatically.
- **Open save folder** opens the current language's `PSP/SAVEDATA` directory.

Reports contain exact framework/executable/guest-image hashes, startup graphics
choices, audio marker times, and allowlisted numeric telemetry from the most
recent 2 MiB of the run log (at most 2,000 samples). Raw logs, account identifiers,
paths, saves, ISOs, assets, screenshots and audio recordings are excluded. Settings
changed after startup may differ from the recorded startup profile. Describe any
such changes in the bug report. Include the location, steps, expected behaviour,
actual behaviour, and whether the issue occurred in a movie or fight.

Normal launches enable existing aggregate audio/queue and MPEG presentation
measurements plus producer-gap, PCM peak/rail, gain-clipping and pre-clamp SAS
saturation probes, without PCM capture or verbose decoder logging. Numeric frame,
GE/GPU-wait, decode and I/O counters accompany the audio windows so stalls can be
investigated. Producer `elapsed_ms` is relative to that channel's first observed
output; use `vblank` to align it with performance windows. A gap can also be an
intentional stopped sound, and a full-scale PCM sample alone is not proof of
clipping. These measurements
help distinguish queue starvation from movie presentation offset; they do not
establish correct audio. Missing samples are unavailable data, not zero errors.
After the game exits through the launcher, the last report exported in that run
is refreshed in place with available exit measurements. Wait for the launcher to
exit before sharing that report. A forced launcher termination cannot finalize it.

The performance HUD already exists at **F1 → Settings → Display** and can be
enabled while playing. No additional external launcher is needed.

## Automatic save snapshots

Before starting the native process, the launcher holds the namespace's existing
single-writer lock and makes a verified ZIP of `PSP/SAVEDATA`, if present. It keeps
five distinct snapshots per namespace under:

`private/save-backups/automatic/<language>/save-<content-hash>.zip`

Japanese, stable English and WIP English retain separate saves and backups.
Unchanged saves do not produce another ZIP. Source bytes are checked again after
copying; ZIP CRCs are checked before committing. A new verified snapshot is in
place before older owned snapshots are pruned. Recovery backups and unrelated
files are never rotated. Corrupt existing automatic backups or snapshot failures
stop startup with an error rather than silently continuing without protection.
The real save folder is never overwritten by the backup operation. Snapshots do
not include unsaved progress, settings, textures, install images or per-run logs.

To restore, close the game and launcher first. Keep the current saves separately,
then inspect the chosen backup's `backup.json`. Its other entries correspond to
paths inside that language's `PSP/SAVEDATA` directory. Restore only into the same
namespace; automatic cross-language merging/restoration is not implemented.

## Verification

Run source tests:

```powershell
./private/tools/python314/python.exe -m unittest discover -s tests
```

Build the host extension and exercise the actual F1 path with copied saves:

```powershell
./private/tools/python314/python.exe tools/title.py build --profile release --jobs 4
./private/tools/python314/python.exe tools/check-game-settings.py --support --output private/tester-support-check
```

The checker requires a fresh private output directory. It retains failed evidence
and checks that the original save fixture and normal preferences stay unchanged.
These are host-side testing tools; campaign, boss audio and shared missions still
need testing. No PSP HLE return value, game asset, Japanese audio or framework pin
is changed by these additions.
