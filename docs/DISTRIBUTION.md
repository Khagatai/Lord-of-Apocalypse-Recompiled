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

Use `tools/prepare-iso-release.py` to inventory and verify the ISO-only payload.
Use `tools/build-online-setup.py --report <verified ISO release report>` only
after complete first-run generation, installer extraction and native boot checks
pass. Its publication guard does not accept a partial HD run as complete.
Use `tools/export-github-source.py` for the source export. It preserves README
and Git history, stages source changes, and does not commit or push them.

`tools/prepare-github-assets.py --local-tester-candidate` is the historical private
tester packager and includes game-derived outputs. It is **not** the public
release workflow. Superseded private tester ZIPs must not be uploaded.

The exact compiler/library source archives and their hash manifest accompany
the release. Keep project and third-party notices. Passing these technical
inventory/install checks does not establish complete gameplay acceptance.
