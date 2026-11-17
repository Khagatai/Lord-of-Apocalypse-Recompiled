# Working storage

Use one active texture pack: `private/hd-remaster-pack/`. Update generated files
in this working set. Do not retain a full pack, ISO, extracted archive or model
input/output tree for every change. Original game dumps, original patch files,
real saves and editable translation work remain protected.

## Latest approved cleanup

The native-launcher packaging pass removes 192 byte-identical QA frames and
source-backed Python caches (24,310,041 bytes), keeping one canonical frame
per duplicate group. All 41,191 protected image, texture, translation, model,
save, settings and runtime files verify unchanged. Compact per-file SHA256 and
canonical-path records remain at `private/launcher-cleanup/completed.json`.
The two superseded command shortcuts are replaced by `LordOfApocalypse.exe`.

Re-encoding the two local image deltas with a full source window reduces their
combined size from 1,159,711,437 to 25,940,237 bytes: 1,133,771,200 bytes saved.
Both reconstructed outputs match the expected SHA256, including the current
WIP image. Packaging refuses stale delta proofs. Original dumps and active
English images are unchanged. Evidence: `private/distribution-test/patch-verification.json`.
The release ZIP is streamed directly to its destination; no second full HD pack
is retained. Relocation QA uses read-only hardlinks and isolated generated state.

The audio quest investigation retains one 20-second town excerpt after saving
the complete numeric device counters and original WAV hash. The owned
529,087,148-byte raw eight-channel recording and the temporary 6.3 MB historical
frame extraction were path/hash-checked and removed. The shorter 46-second
movie reference remains private. No ISO, archive or HD pack was duplicated.
Evidence: `private/audio-quest-review/recording-cleanup.json` and
`old-frame-cleanup.json`. Real saves/settings and source audio are unchanged.

English editorial pass 23 also moves its checked staging files into the same
active WIP image/archive paths. The 39 generated MES scratch files are individually
path/hash-checked and removed after promotion. Only compact metadata, editable
wording plans and bounded review evidence stay in `private/translation/english-review/`.
No superseded full image/archive copy remains. Original inputs, captions, runtime,
real saves, preferences and tester packages are unchanged.

The comprehensive item-description pass replaces the same active WIP image and
archive pair in place. The earlier uninstalled equipment-only staging image was
hash-checked and removed before rebuilding the combined item/material pass.
Successful staging files are moved into the active paths; no full old image or
archive copy is retained. Captions and the HD pack are unchanged. Only compact
previous metadata, editable plans and bounded validation evidence remain in
`private/translation/item-layout/`. Source saves/settings are read-only guards;
existing tester packages remain unchanged. The cumulative recipe reconstructs
all changed resources from v1.6 without writing another full archive.

The container-layout correction replaces the same active WIP image/archive pair
and movie-caption bundle. Superseded uninstalled candidates were hash-checked
and removed before regeneration. No full prior image/archive or HD pack was
retained. Compact previous JSON metadata and changed-asset authoring plans stay
private. The installed caption plates occupy about 61% less pixel area; the
source saves, preferences, original images and co-op runtime verify unchanged.
Evidence: `private/translation/container-layout/promotion.json`. Existing tester
ZIPs are unchanged. The cumulative recipe independently reconstructs every
changed resource from the pinned v1.6 baseline without creating another archive.

Pass 20 again replaces the active image/archive pair in place. The first
uninstalled staging payloads were removed before rebuilding the additional
quest headings, after checking their hashes and protecting the active install.
Successful final payloads were moved into the stable active paths. The caption
candidate was also moved into the one active sidecar; no old caption binary is
retained. Compact previous JSON metadata remains. Evidence:
`private/translation/text-pass-20-promotion.json`. Caption edits do not require
rebuilding or duplicating the 8 GiB HD pack. The native texture OCR scan retains
only its 99 candidate previews and compact reports, rather than another full
texture export. Movie diagnostics read the ISO directly; no PMF/audio copies
were extracted or uploaded.

Pass 19 builds all reviewed MES and texture/layout edits together with
`tools/build-full-translation.py`, using one staging archive pair rather than
copying it again for each text layer. Validated payloads replace the same active
WIP paths in place. Only compact previous metadata remains. Native movie captions
are small private sidecar data; updating their scripts requires no ISO/executable
copy per edit. One reviewed active caption bundle and one working candidate are
kept. Evidence: `private/translation/text-pass-19-promotion.json`.

Translation pass 18 also replaces the one active WIP image/archive pair in
place. Its rejected initial archive payloads were removed before rebuilding;
only compact reports remain. Successful staging payloads were moved into the
stable active paths, with no old full image/archive retained. Twenty-two
protected original/runtime/save/settings files verify unchanged. Evidence:
`private/translation/text-pass-18-promotion.json`. Movie-caption inspection reads
directly from the original local image and retains cropped PNG samples and
review sheets, rather than extracted or re-encoded movie/audio copies.

Before translation pass 17, the workspace measured 30.430 GiB. The large
redundancies from the earlier pass were already absent; one recovery executable
remains. A narrow authorized cleanup removed 136 source-backed Python bytecode
caches (1,202,233 bytes), checking 21 protected current-game/save/settings files.
These caches can regenerate normally. After typesetting review, 1,048,576 bytes
of unreferenced failed raw pixels were also removed; compact failed previews and
logs remain. Evidence: `private/cleanup-records/translation-resume-cache-cleanup.json`
and `translation-pass17-scratch.json`.

The verified pass-17 WIP image/archive candidate was promoted by replacing the
existing active files at their stable paths. The superseded full image/archive
bytes are not retained; no HD pack or original dump copy was created. Its
promotion report verifies 22 protected inputs/runtime/save/settings files stay
unchanged. Temporary staging folders contain no remaining full candidate payloads.
Evidence: `private/translation/text-pass-17-promotion.json`.

### Earlier storage pass

The approved cleanup reclaimed **2.418 GiB** (2,596,127,719 bytes): 18 obsolete
test executables/extra backups were removed, and 875 historical raw QA frames
were archived losslessly in 83 ZIPs. Each archive was read back and checked
against its per-file SHA256 manifest before its source frames were removed.
One recovery executable remains. All **40,182 protected files** matched their
before-cleanup hashes, including the original dump/patch, active HD pack,
translation work/models, saves, settings, current executable and Steam runtime.

The outer workspace measured **30.379 GiB** after cleanup (logical file sizes,
including development tools). The subsequent launcher preflight passed with
the existing executable and saved configuration; it did not open a game window
or validate gameplay/networking. No Git commit was created. Local evidence:
`private/storage-cleanup-proposal.json`, `storage-cleanup-completed.json`,
`storage-protected-before.json` and `storage-after-cleanup.json`.

Historical frames live in `private/historical-frame-archives/`. To verify one
archive without restoring files, run from the project root:

```powershell
private/tools/python314/python.exe tools/restore-qa-frames.py hd-default-town-04
```

Add `--restore` only when those original raw frames are needed. Restoration
checks hashes, refuses to overwrite different files and retains the ZIP.
The cleanup safety tests cover protected paths, changed files and corrupt
archives; all four passed. The independent restore verifier also passed.

The measurements below describe earlier cleanup stages.

The frame-rate settings pass updates the existing executable and keeps the same
HD pack and images. After successful reviewed checks, 276.073 MiB of raw QA
frames and two superseded trial executables was removed. Actual PNG screenshots,
logs, CSV timings, failed/successful reports and copied QA saves remain. One
pre-change executable is retained for recovery. All 86 protected inputs/data
files match the baseline; the other protected file is the intentionally rebuilt
game executable. Evidence: `private/fps-cleanup.json`, `fps-protected-files.json`
and `fps-final-review.json`.

After the final archive coverage pass, private working data is approximately
**30.775 GiB** (including development tools and local translation models).
The active pack contains 28,189 unique PNGs. Generation added 3,383 unique PNGs
in place, reused exact aliases without copying files, and retained no full pack
or ISO duplicate for this pass. A further 140.427 MiB of validated temporary
scaler/inference data, duplicate previews and raw checkpoint PPMs was removed.
Contact sheets, actual screenshots, source captures and compact reports remain.
All 87 protected files still match their original hashes. Evidence:
`private/cleanup-records/full-coverage-scratch-completed.json`,
`storage-full-coverage.json` and `protected-files-full-coverage.json`.

The measurements below describe earlier cleanup stages.

The 2026-11-15 cleanup removed 187.411 GiB of superseded generated data, reducing
private working data from 220.114 GiB to approximately 32.767 GiB. All 87 hashed
protected files stayed byte-identical. This includes the original dump, current
images, executable, fonts, settings and saves. The current HD pack is about
7.94 GiB; development tools/local translation models account for about 11.94 GiB.
Development storage is not the size of a distributable game.

A second audited pass removed another 2.490 GiB (2,673,988,662 bytes) of old
diagnostic builds, prototype executables and framework comparison checkouts.
Compact comparison reports, the current release and required preview builds
are retained. All 87 protected files again match their original hashes.
Local evidence: `private/cleanup-records/additional-completed.json` and
`protected-files-additional.json`. Local translation models and installer
archives remain: the translation tool verifies these pinned artifacts before use.

After the following in-place sky/UI update, the final working-data measurement
is approximately 30.375 GiB. The old full-inventory preflight report was compacted
from 46,666,295 to 3,277 bytes, keeping its result and manifest identity. Another
188.596 MiB of validated inference/scaler scratch, duplicate result previews,
raw checkpoint PPMs and unreferenced HD portrait PNGs was removed. All 87 protected
files again match their original hashes. The active pack contains 24,806 PNGs;
its metadata rollback references no deleted portrait images. Final local evidence:
`cleanup-records/remaster-scratch-completed.json`, `storage-final-remaster.json`
and `protected-files-final-remaster.json`. Raw captured mip source data and
compact comparison reports remain available for validation.

The promoted pre-portrait-policy pack contained 24,423 PNGs, manifest SHA256
`8f975c85c3402ad5decde60391e63b9de059b6eece56e2656403a5234d94ff54`.
It was moved into its permanent directory without making another full copy.
Original Japanese and stable-English images, the current WIP image, current
release build, toolchain, source, models and corrected catalog 08 are retained.

Superseded pack/candidate folders, inference input/output caches, historical WIP
images, old rebuilt archives and obsolete raw catalog exports were removed.
Small available reports and manifest hashes are retained in
`private/cleanup-records/`. Some older HD documentation paths are historical
evidence references whose generated payloads were deliberately pruned.

## Updating the working set

The archive, original-UI and existing-English UI builders now update their
`--base-pack` in place by default. They reuse unchanged PNG files. Their output
folder holds reports and scratch work, not a full baseline-pack copy. The archive
builder can reuse its owned report/work folder on subsequent runs and does not
retain new inference-cache PNGs unless `--keep-cache` is explicitly requested.

`tools/pack_update.py` validates new metadata/INI and all referenced PNGs before
activation. It retains one metadata-only rollback, without copying PNG assets;
a failed metadata promotion restores the previous active metadata. An unchanged
update creates no snapshot. Corrupt new data and stale baselines are refused.
This validates file integrity; artwork and native validation remain required.

`--copy-base` is an explicit legacy/export option. Do not use it for ordinary
remaster edits. Likewise, avoid the older bulk-prefill/merge/candidate-copy
workflow during routine work. Keep only changed-asset scratch data while it is
needed, then remove it after validation. Do not accumulate full versioned trees.

For translation work, retain one current WIP image and its current archive pair;
replace the working output after validation and discard the superseded generated
image/archive data. Preserve original/baseline inputs and editable translation
specifications. Temporary staging is not a reason to retain another full version.

Normal launcher records now contain a compact pack summary and manifest hash,
rather than repeating the full texture inventory on every launch.

Standalone English v1.6 was retired on 2026-11-17. Its generated ISO, extracted
archives and old distribution delta were removed after hash checks, reclaiming
1,234,435,618 bytes. Keep the small original upstream patch and pinned baseline
hash manifest for reproducible translation builds. Build-only legacy inputs are
reconstructed temporarily and cleaned on exit; normal WIP play needs no legacy ISO.
The active WIP image, archives, original dump and real saves were preserved.
