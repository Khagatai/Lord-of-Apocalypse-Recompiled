# ISO-only Windows build

Use Windows x64 and a current Vulkan driver. The original Japanese NPJH50503
disc 1.01 ISO is required. Its SHA256 is recorded in the title configuration.
No decrypted module, generated game C, game executable or game artwork belongs
in the source repository or public payload.

## Player installation

Run the matching release's Setup.exe. It downloads the source/tools payload,
verifies its SHA256 and every installed file, and creates the launcher.
On first Play, choose the original ISO. Setup performs these local stages:

1. Verify the original ISO and pinned public source trees; decrypt and hash
   the measured EBOOT/LIBFONT inputs locally.
2. Generate C and compile the native x64 executable using the portable GCC.
3. Render English UI from original textures and text/layout instructions;
   rebuild the translated archives and English ISO. Non-archive ISO files,
   including game code and audio, are independently checked against retail JP.
4. Render subtitles locally; recover original credit name glyphs from the ISO.
   Exercise the actual caption writer in all four PSP pixel formats.
5. Generate the HD environment/model texture pack locally, in bounded batches.
   Original 2D UI and dialogue portraits remain in use. No movie/audio files
   are rewritten. Only successful owned checkpoints can resume.

Allow approximately 18 GB of free disk space. First setup is much longer than
normal startup; HD generation can take many minutes to several hours depending
on CPU/GPU. The launcher reports progress. Keep it running; after an error,
retrying preserves successful stages and reports the failing stage.
The pinned Real-ESRGAN tool is downloaded directly from its publisher during
first HD setup; the archive and individual required files are hash-verified.
Game data never leaves the PC. Internet access is needed for this tool download.

## Source checkout

Clone recursively and check out the exact framework gitlinks. With Python 3.14
available, import the matching release's public dependencies and recipes:

```powershell
py -3.14 tools/import-release-tools.py
```

An already downloaded payload can be supplied with `--archive <zip>`. The
source repository's `config/release-download.json` pins its size and SHA256.
The importer refuses differing existing dependencies and never imports game
outputs, saves or settings. Use a fresh clone for a different release.

Then run the same first-run build used by the launcher:

```powershell
private/tools/python314/python.exe tools/local_player_setup.py --image "C:/Games/MyOriginalDump.iso"
```

Developer stages remain individually available through `iso_local_setup.py`,
`title.py`, `build-local-text-images.py`, `build-iso-english.py`,
`build-local-movie-captions.py` and `build-local-hd-pack.py`. See their `--help`.
The text/HD recipe files are included in the ISO-only release payload.

## Verification limits

Windows font rasterization can vary by a few pixels. Local UI generation records
actual output hashes and reports differences from reference rendering. Source
identity, approved edit regions, message commands, movie identity/timing and
non-text ISO file hashes remain enforced. If UI pixels differ, the HD mappings
are rebound to the current English archive; unexplained missing world/model
source pixels are a build failure.

An installed `private/local-build/ready.json` is written only after all stages
complete. It is not evidence of complete campaign testing. Full campaign,
intermittent boss/quest/movie audio and comprehensive 30/60 FPS co-op acceptance
remain separate beta test work. GitHub issues should identify release version,
location/quest, frame-rate setting, solo/co-op mode and reproduction steps.

The clean-install boot check exercises 360 native vblanks with isolated empty
saves at each frame-rate setting and rejects interpreter execution or dispatch
misses. It does not establish gameplay speed or audio correctness. Exact timed
PPSSPP frame equivalence remains unverified; a previous reference comparison had
a one-vblank phase difference. That comparison is not recorded as a pass.
