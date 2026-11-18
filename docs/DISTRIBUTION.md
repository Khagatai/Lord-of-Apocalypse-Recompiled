# Source and installer distribution

The release candidate is `v0.9.0-beta.5`. Full campaign, intermittent audio
distortion and 30/60 FPS multiplayer acceptance remain open; use a pre-release.

## Files and destinations

Under `Finished/Lord Of Apocalypse Recomp`, `Lord-of-Apocalypse-Recompiled` is
the source-only Git checkout. Its existing README is preserved. Agent notes,
game files and personal data are excluded; framework pins remain exact gitlinks.

`Release v0.9.0-beta.5` contains all seven release assets. Upload the individual
files without renaming them or zipping the folder:

| Asset | Purpose |
| --- | --- |
| `Setup.exe` | Online installer; the only download most players need |
| `Launcher-Update-v1.txt` | Discovery marker for compatible installed launchers |
| `LordOfApocalypse-Setup-Source.zip` | Installer source and embedded manifest |
| `Lord-of-Apocalypse-Recompiled-v0.9.0-beta.5-ISO-Builder-part01-of01.zip` | Public build sources, dependencies and generation recipes |
| `LordOfApocalypse-Tool-Sources.zip` | Corresponding compiler/library sources |
| `Setup-SHA256SUMS.txt` | Installer, update marker and installer-source checksums |
| `Payload-SHA256SUMS.txt` | Player-payload and tool-source checksums |

These are release assets, not source-branch files. Do not upload older private
tester packs or locally generated game files. Keep corresponding sources and
licence notices available alongside their binaries.

## Player installation

First Play requires the player's own unmodified NPJH50503 Japanese PSP ISO,
disc 1.01. Its exact SHA256 is enforced before generation. The payload contains
no prepared game executable, generated game C, decrypted module, game-memory
image, ISO, game textures, subtitle bitmaps, saves or personal preferences.

The native executable, WIP English image and subtitles are generated locally.
Japanese audio remains unchanged. Original textures are the default; render
scale, FSR and filtering remain available. HD environments/models are optional
and generated locally, which can take hours. See [ISO_BUILD.md](ISO_BUILD.md).

Players need Windows x64, a Vulkan driver and about 18 GB free for installation,
compilation and optional full HD generation. Use a short ASCII install path.
Python and the compiler are bundled; no separate emulator or Git is required.

## Preparation and checks

Build the launcher with `tools/build-windows-launcher.py`, then inventory with
`tools/prepare-iso-release.py --version 0.9.0-beta.5 --output <folder>`.
The report starts with publication gates unset. Exercise the installer engine
in an empty short path, run first setup from the original ISO alone, check
repeat setup and boot at 30 and 60 FPS with isolated saves. Run regression tests
and audit the complete archive before recording those checks as passed.
An unfinished optional HD run must never be reported as a completed HD build.

Only then run `tools/build-online-setup.py --report <verified report> --output
<Setup.exe>` with its publication guard enabled. Generate matching checksums and
update `config/release-download.json`. Export source with
`tools/export-github-source.py --destination <GitHub checkout>`; it preserves
README and Git history, stages changes, and does not commit or push.

Never use the historical `prepare-github-assets.py --local-tester-candidate`
for public uploads: that private packager includes game-derived output.

## Publishing beta.5

1. Review, commit and push the prepared source checkout in GitHub Desktop.
2. In Releases, choose **Draft a new release**. Create **v0.9.0-beta.5** from
   the pushed commit and select **Pre-release**.
3. Paste the prepared release notes and attach all seven files listed above.
   Keep filenames unchanged: Setup pins the tag, payload filename, size and hash.
4. Wait for uploads to finish, then publish. Draft assets are unavailable at
   public download URLs. A new tag is required for the update prompt; replacing
   beta.4 assets does not trigger one.
5. Download just the published Setup.exe into an empty folder and test that it
   fetches the payload. Check an existing compatible launcher offers beta.5 on
   Play. These live-publication checks remain pending until the release exists.

Setup verifies every managed file and preserves saves, settings and ISO selection
during updates. Beta.5 can reuse verified native and English-image outputs from
beta.4; older releases may require a rebuild. HD remains opt-in. Existing HD jobs are verified by their
source pixels and processing identity: only new, changed, missing or damaged
jobs are regenerated. Keep the HD pack and its HD-work completion records;
normal in-place updates preserve both. Back up saves before beta updates.
Verified payload ZIPs beside Setup.exe can be used without downloading them.

[GitHub release instructions](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository#creating-a-release)
