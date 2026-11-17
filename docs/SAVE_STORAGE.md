# Persistent preview saves and tutorial recovery

The current launcher also makes up to five distinct verified automatic snapshots
per language before play. Unchanged saves are deduplicated; original recovery
backups remain protected. **F1 → Tester support → Open save folder** opens the
active language's directory. See [backup policy and restoration](TESTER_SUPPORT.md).
The historical recovery evidence below does not establish a full save round trip.

The user completed the tutorial in the Japanese preview, saved, and found no
progress on the next launch. The launcher had selected a new per-run memstick
for every preview. The save remained intact in the earlier run; later runs used
empty folders. This was a launcher storage issue, not evidence of lost save bytes.

Interactive previews now reuse:

- Japanese: private/memstick/japanese/
- English v1.6: private/memstick/english-v16/
- Draft English text test: private/memstick/english-text-test/

GDI/Vulkan and diagnostic/release builds share their language's namespace.
Each launch still gets separate private logs. A Windows byte-range lock prevents
two preview processes writing the same memstick concurrently. Different language
namespaces stay separate until cross-patch compatibility is tested.

## Recovered tutorial save

Source: private/preview-20261114-001221-4w7ckoco/memstick/.
Its PSP/SAVEDATA/NPJH50503USERID_0000/ contains DATA.BIN (914316 bytes),
PARAM.SFO (4912 bytes) and ICON0.PNG (20000 bytes).

The recovery tool first made an independent, hash-verified backup under
private/save-backups/recovery-20261114-002254-nbdrg515/memstick/, then copied
those files to private/memstick/japanese/. The source was preserved and all
three copies matched. recovery.json beside that backup records each hash.
The tool refuses any existing persistent destination instead of overwriting it.
No personal save files or decoded content are committed or sent externally.

```powershell
./private/tools/python314/python.exe tools/recover-preview-save.py private/preview-20261114-001221-4w7ckoco/memstick --language japanese
```

This was already run successfully; do not repeat it over the populated folder.
Other migrations must use an explicitly selected source and an empty destination.
The launcher itself never silently selects or merges older saves.

## Actual validation

Native release/GPU testing used a separate copy of the recovered master:
private/tutorial-save-load-check/. At the bounded checkpoint, the game displays
the Japanese message stating that saved data was auto-loaded, rather than the
no-save prompt. It exits 0 at the explicit 1800-VBLANK diagnostic boundary.

PPSSPP interpreter/software testing used another isolated copy in
private/tutorial-save-oracle/. The 12-second reference image also states that
saved data was auto-loaded. Its emulated-time bound is not a gameplay exit/pass.
Both reports confirm the fixture source remained hash-identical. Neither test
wrote the persistent master. No PSP call or save result was replaced or patched.

Four synthetic checks cover stable language paths, independent verified backup,
refusal to overwrite saves, and concurrent-writer refusal/lock reuse. The whole
title suite passes 24 checks. This confirms recovery and initial auto-load; the
character's exact post-tutorial location, another save–exit–reload cycle, and
broader save/campaign/cross-language behavior still require in-game validation.

## Cross-language follow-up

The user requested shared storage after the English translation is finished.
That migration has not been performed: both persistent language folders remain
separate, and the recovered Japanese master and recovery backup are retained.

A copy of the Japanese tutorial save was supplied to unchanged English v1.6:
private/translation/japanese-save-in-v16/ (native release/GPU, bounded at 1000
VBLANKs) and private/translation/japanese-save-in-v16-oracle/ (PPSSPP interpreter/
software). The native VBLANK-991 and PPSSPP 12-second images both explicitly say
saved data was automatically loaded. Source hashes remain unchanged. This is a
positive initial-load result in one direction, not bidirectional compatibility.

The new eight-message translation candidate repeats that same initial-load result
in native and PPSSPP; see TRANSLATION.md. Before sharing storage: verify character
and quest state, save in English to an isolated fixture, restart English, then
load that saved fixture in Japanese and verify state again. Only then migrate
to one backed-up storage root and retain the single-writer lock across launchers.
Do not merge competing save files or replace the master with a diagnostic copy.

## Isolated translation text-test storage

Start-English-Text-Test.cmd uses english-text-test exclusively. A protected,
copy-only recovery initialized it from the Japanese tutorial master and made
another independent backup at
private/save-backups/recovery-20261114-015747-6pzzyq60/memstick/.
All three game files match the recovered tutorial hashes above; source hashes
remain unchanged. The source namespace was locked for a consistent snapshot.
This is a separate copy, not shared storage or a bidirectional-save pass.

The first protected copy hit PermissionError while trying to hash the locked
.preview.lock coordination byte, before creating a destination or backup.
Recovery now excludes the root runtime lock from game-data hashes and backup
copying. A regression test performs recovery while the source lock is held,
checks unchanged data and ensures neither backup nor destination inherits the
lock. The corrected copy succeeds. Launchers continue to acquire their own
single-writer locks normally. Total title checks: 46 passing.

The second directly authored text candidate retains this same test namespace;
no new recovery or overwrite was performed. Its isolated native/PPSSPP startup
checks also show the saved-data-loaded prompt with source fixture hashes unchanged.
Original Japanese audio is retained. Translation completion and English-save to
Japanese-load compatibility still precede any shared-storage migration.
