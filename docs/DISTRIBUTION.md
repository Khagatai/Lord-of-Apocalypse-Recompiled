# Source and installer layout

Under the requested Finished folder, Lord-of-Apocalypse-Recompiled is the
source-only Git export. Release/Setup.exe is the small installer and
Setup Files For Github holds its five payload ZIPs. The version remains
v0.9.0-beta.1. No commit, push, release or upload is performed.

The source export preserves the destination README, or copies the development
README unchanged into an empty folder. Agent instructions and planning/status/
finding histories are excluded. Development tools, tests, technical references,
licence notices and exact framework gitlinks remain. After cloning, initialise
frameworks with git submodule update --init. Game data, SDKs, toolchains, saves,
personal preferences and local logo artwork stay out of the source export.

Setup.exe pins ZIP names, sizes and SHA256. Its URLs target the GitHub release
Khagatai/Lord-of-Apocalypse-Recompiled, tag v0.9.0-beta.1. Local files do not
publish those URLs. Payloads must eventually be uploaded as RELEASE ASSETS,
not committed to Git. Each ZIP is below 2 GiB. Do not rename files without
rebuilding the installer. Players download Setup.exe; it retrieves the parts.

For local testing, matching ZIPs beside Setup.exe or in the sibling
Setup Files For Github folder are used without downloading. Installation
verifies every manifest-listed file, refuses nonempty targets, supports
resumable downloads and cancellation, and offers a desktop shortcut.
Use a short ASCII installation path, e.g. C:/Games/LordOfApocalypse-Recomp.
Too-long paths are rejected before downloads.

First Play asks for the exact unmodified NPJH50503 Japanese ISO and constructs
only the current English WIP image locally. The original ISO remains unchanged.
No ISO, saves or personal settings are included. Japanese stays selectable;
standalone v1.6 is retired. Networking and tester support remain in F1.

Publication is unresolved: the player payload still contains decrypted modules,
a flat memory image, compiled guest code and restored textures. An ISO requirement
does not remove those bundled inputs. The original instruction excludes
copyrighted binaries/assets from external uploads, so these files are a LOCAL
TESTER CANDIDATE, not cleared for public upload. Audio and complete campaign/
30/60-FPS multiplayer acceptance also remain open.

Repeatable preparation uses tools/export-github-source.py,
tools/prepare-github-assets.py --local-tester-candidate, and
tools/build-online-setup.py. See each script's --help for destination arguments.
Payload parts are written directly, with at most one temporary ZIP part during
replacement. No full HD pack or oversized combined ZIP is duplicated.
