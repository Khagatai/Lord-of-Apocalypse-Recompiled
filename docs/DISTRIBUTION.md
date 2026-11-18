# Source and installer layout

The release target is `v0.9.0-beta.1`, a pre-release for testing. It does not
represent complete campaign, audio or 30/60 FPS multiplayer acceptance.

Under the requested Finished folder:

- `Lord-of-Apocalypse-Recompiled` is the source-only Git export. Its existing
  README is preserved. Project agent instructions and planning/status notes
  are excluded; framework revisions remain exact gitlinks.
- `Release` holds the small `Setup.exe`, its setup-source archive and checksums.
- `Setup Files For Github` holds the single ISO-builder payload ZIP, the
  corresponding public tool-source archive and payload checksums.

Upload installer, payload and accompanying source archives as GitHub **release
assets**, not into the source branch. The checksum files have distinct names.
Players download Setup.exe; the tool-source archive is optional for players
but should remain available alongside the release's compiler/library binaries.

## What the payload contains

The ISO-only payload contains public sources, the portable compiler/Python,
runtime dependencies and text/layout/HD processing recipes. It contains no
prepared game executable, decrypted module, flat game-memory image, ISO,
original/restored game texture or caption bitmap. Saves and preferences are
excluded. Do not publish locally generated outputs from `private/`.

First Play asks for the exact original NPJH50503 Japanese ISO. It compiles the
native executable, reconstructs the English image, renders subtitles and builds
HD textures locally. The original ISO, game code, movie/audio files and user
saves are protected. The texture tool is downloaded directly from its publisher,
with pinned archive/member hashes; all game processing remains local.
See [ISO_BUILD.md](ISO_BUILD.md) for commands, requirements and verification limits.

## Installer behaviour

Setup.exe pins payload names, sizes and SHA256. URLs target the matching tag in
`Khagatai/Lord-of-Apocalypse-Recompiled`. A draft release is not a public download
location. Keep asset names unchanged unless the installer is rebuilt.

Verified local payload ZIPs beside Setup.exe, or in the sibling `Setup Files For
Github` folder, are used without a download. Extraction verifies every listed
file, rejects unsafe paths and nonempty installation targets, supports resumable
downloads and cancellation, and offers a desktop shortcut. Use a short ASCII
path. Allow about 18 GB free for compilation and generated game/HD files.

Normal startup reuses prepared files. The launcher shows first-setup progress,
including HD job counts. HD processing can take many minutes to several hours
depending on CPU/GPU. Japanese remains selectable; standalone English v1.6 is
retired. Networking and tester support remain in F1.

## Preparation and gates

Use `tools/prepare-iso-release.py --version 0.9.0-beta.2 --output <payload-folder>`
to inventory and verify the ISO-only payload. Specify the version without the
leading `v`. The build report supplies the installer version and URL. Publish
each update under its new `v<version>` tag. Editing the files on an existing tag
does not trigger an update prompt.
Use `tools/build-online-setup.py --report <verified ISO release report>` only
after complete first-run generation, installer extraction and native boot checks
pass. Its publication guard does not accept a partial HD run as complete.
Attach `Launcher-Update-v1.txt` from the installer output beside the matching
`Setup.exe` and payload. It marks the release as supporting in-place updates.
Allow GitHub to calculate the installer digest before testing the update prompt.
Use `tools/export-github-source.py` for the source export. It preserves README
and Git history, stages source changes, and does not commit or push them.

`tools/prepare-github-assets.py --local-tester-candidate` is the historical private
tester packager and includes game-derived outputs. It is **not** the public
release workflow. Superseded private tester ZIPs must not be uploaded.

The exact compiler/library source archives and their hash manifest accompany
the release. Keep project and third-party notices. Passing these technical
inventory/install checks does not establish complete gameplay acceptance.

## Uploading the beta.3 pre-release to GitHub

1. Export the current source to the GitHub checkout with
   `tools/export-github-source.py --destination <GitHub checkout>`. In GitHub
   Desktop, review the changes, commit, and push the release branch. Keep the
   ISO, generated game files, HD textures, saves, and release archives out of the
   source commit.
2. Open the repository's **Releases** page and click **Draft a new release**.
   Create `v0.9.0-beta.3` from the commit you just pushed. Use the title
   `Lord of Apocalypse — v0.9.0-beta.3` and select **Pre-release**. The tag and
   filenames are part of the installer's download URL. [GitHub release instructions](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository#creating-a-release)
3. Paste these notes into the draft.

   > New in beta.3: Settings → Build lets you choose compiler jobs, set a Windows
   > build memory cap, and pick Standard, Fast, or Low memory HD processing.
   > Original textures are the default. Run Setup.exe and provide your own
   > unmodified Japanese PSP ISO (NPJH50503, disc 1.01).

4. Keep the release as a draft until the beta.3 clean first-run checks pass and
   the public installer is built. The local `Setup-QA.exe` is the test build. The
   completed upgrade test verified package replacement, Build settings, and the
   unchanged native build fingerprint. A clean ISO build and native boot for
   this candidate are still pending.
5. Attach the following individual files from the matching release output.
   Keep the filenames as generated.

   | Files | Where they come from |
   | --- | --- |
   | `Setup.exe`, `Launcher-Update-v1.txt`, `LordOfApocalypse-Setup-Source.zip` | Final beta.3 installer build |
   | `Lord-of-Apocalypse-Recompiled-v0.9.0-beta.3-ISO-Builder-part01-of01.zip` | Beta.3 source and tools payload |
   | `LordOfApocalypse-Tool-Sources.zip` | Matching compiler and library source archive |
   | `Setup-SHA256SUMS.txt`, `Payload-SHA256SUMS.txt` | Checksums for the exact files being uploaded |

6. Wait for the uploads to finish, then click **Publish release**. From an empty
   folder, download just `Setup.exe` and confirm it can fetch the published
   payload. Separately, click **Play** in an installed beta.2 launcher and
   confirm it offers `v0.9.0-beta.3`. The update check uses the new tag, installer
   digest, and update marker. Beta.1 players can start with the new `Setup.exe`.
