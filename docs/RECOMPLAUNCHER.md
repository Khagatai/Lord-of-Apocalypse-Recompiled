# RecompLauncher integration

The root `recomplauncher.json` follows the upstream [support guide](https://github.com/elripalda/RecompLauncher/blob/main/docs/ADD-SUPPORT.md).
The guide, full developer documentation, named-input guide, examples and schema
were reviewed at revision `f3caf970975df3fe789ff203f4b93ecab9cb9fff`.
No game files, save files, keys or personal settings belong in this integration.

## Player setup

Install the Windows x64 player ZIP, then select your own unmodified Japanese
NPJH50503 disc 1.01. ISO, CSO and DVD-layout CHD are accepted by the integration;
compressed images use the pinned framework's existing decoder and are expanded
locally once. The expanded ISO must pass the same exact size/SHA256 check as an
ordinary ISO. CD-layout CHDs are refused by the decoder.

RecompLauncher runs the same shipped `LordOfApocalypse.exe` for preparation and
play. `--recomplauncher --prepare --game=<path>` runs the existing local build
without a launcher window, translates setup progress and preserves failures.
`--recomplauncher --play --game=<path>` supervises the normal game launch directly.
Without `--recomplauncher`, the program retains its existing GUI and behaviour.

The optional HD build starts unchecked and discloses its upscaler download and
potentially long build. Stage fingerprints and existing HD completion records
continue to control reuse. Setting local HD textures on before building them
asks the player to run Set Up Again. Movies and Japanese audio are unchanged.

All 15 graphics/language settings use the existing
`private/settings/graphics.json` and its existing schema. F1 changes are read back
by RecompLauncher after play. Networking and bug reporting remain in game.
RecompLauncher owns updates during these sessions; the standalone update prompt
is suppressed when `RECOMPLAUNCHER=1`.

Save declarations cover only `DATA.BIN` and `PARAM.SFO` for the English and
Japanese namespaces. They exclude game icon artwork, ISOs, builds, caches and
network settings. Folder buttons open English saves, settings and adapter logs.

## Dump verification provenance

The following values were measured locally from the user's original ISO and
checked against the previously recorded SHA256 in `config/lordofapocalypse.toml`:

| Field | Value |
| --- | --- |
| Disc | NPJH50503, Japan, disc 1.01 |
| Bytes | 1068498944 |
| CRC32 | `a0ea68dd` |
| SHA256 | `3a4d63713880dfb67ade00b6a912ac4975847cec06b1ab341b65963f328e1c93` |

The manifest's CRC32 badge describes this exact ISO, not every compressed
container or every Japanese pressing. Compressed input still receives the exact
expanded-ISO SHA256 check. The upstream fast ID reader does not currently identify
PSP disc IDs; no unsupported ID check is declared. These are locally measured
values, not a claim of independent Redump certification.

## Packaging and checks

`tools/prepare-iso-release.py --version <version> --output <folder>` always
includes the manifest alongside the launcher and names the player archive
`Lord-of-Apocalypse-Recompiled-v<version>-Windows-x64.zip`. Its single top folder
is supported by RecompLauncher. Installer and tool-source assets remain separate.
The manifest is also included by the source exporter. Existing published release
assets do not acquire support until a new player ZIP is built and published.

Build the GUI entry point with `python tools/build-windows-launcher.py` and run
`python -m unittest discover -s tests -p "test_*.py"`.
Download the schema for the reviewed revision, then validate with PowerShell 7:

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/elripalda/RecompLauncher/f3caf970975df3fe789ff203f4b93ecab9cb9fff/docs/recomplauncher.schema.json -OutFile $env:TEMP/loa-recomplauncher.schema.json
pwsh -NoProfile -File tools/check-recomplauncher.ps1 -SchemaFile $env:TEMP/loa-recomplauncher.schema.json
```

For a built developer checkout, preparation reuses the normal cached preflight;
fresh builds follow the project's existing build instructions. Player release
preparation uses `local_player_setup.py`. The readiness marker is written only
after successful preparation and required-output checks. Changed disc identity
or timestamps require setup again. No title or framework revision is changed.

In RecompLauncher, enable Developer tools and choose Add a build. Select the
folder containing both the EXE and manifest, check the Developer tab, then test
Easy Setup, a settings change, Play, controller navigation, quit and save backup.
No launcher-specific manifest can replace that final application-level test.

For review, keep the optional CLI/input/update code and its tests in one commit;
put the manifest, packaging/export changes, documentation and badge in a second
commit. The exporter stages files but does not commit, push or publish.

### Local validation

The integration passed the official JSON Schema check and all 457 project tests.
The Windows x64 launcher was rebuilt and tested with no developer SDK environment:
unattended preparation and the Play preflight returned zero, and ordinary startup
opened its normal launcher window. The Play preflight does not establish gameplay
or acceptance inside RecompLauncher. Synthetic CSO and CHD inputs decoded to the
expected bytes and reused their existing expanded files on a second call; a real
compressed game dump was not tested. The original ISO's size, SHA256 and CRC32
were verified locally. These checks do not replace a fresh player installation
and the application-level checks described above.

## Standards audit and remaining work

- **One movable data root (medium):** the existing `private/` layout stays under
  the install and is portable with it, but does not yet relocate every output to
  `RECOMPLAUNCHER_DATA`. Doing that safely needs coordinated path/ownership checks
  across the build pipeline. No saves or config formats are migrated here.
- **Cache layout (medium):** existing native/HD work is kept in its established
  private folders; moving all caches to `{data}/cache` needs the same migration.
  The manifest's save list already excludes those large outputs.
- **Linux/macOS releases (large):** only Windows x64 is packaged. Native builds
  and complete Proton/Steam Deck operation are not claimed.
- **Big Picture and prompts (small/medium):** saved display choices are honoured;
  automatic mode-dependent fullscreen and Xbox/Deck glyphs throughout the
  original PSP UI are not implemented. Physical controller acceptance inside
  RecompLauncher remains a tester check.
- **Original-look defaults (small):** existing enhanced resolution/filter defaults
  are preserved, as previously requested. Native 30 FPS and original graphics
  choices remain available.
- **Recomp Achievements (large):** achievements, Beaten/Mastered tracking and
  leaderboards are not implemented; see
  [RecompAchievements](https://github.com/elripalda/RecompAchievements).
- **Release/application acceptance (small validation task):** publish a new tested
  player ZIP and exercise it through RecompLauncher's Developer tools. The old
  beta.8 downloads contain neither the new manifest nor the new CLI entry point.

The project was not found by repository in the catalog snapshot used for this
change, so the standard README badge links to the launcher homepage. Listing,
claim approval, real-game CSO/CHD inputs and launcher/cloud-save round trips are
not established by synthetic decoder tests or native preflight checks.
The [free developer account](https://recomplauncher.com/dev) uses GitHub sign-in
to claim the project, request listing and manage its page; account approval is a
maintainer action, not something these files perform.
