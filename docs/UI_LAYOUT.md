# English text layout corrections

The source WIP image contains corrections for character creation,
settings/results labels, startup caution, Turnslash help, and the shared
equipment, consumable and material description tables. No networking executable,
audio or portrait changes are part of this update. Tester ZIPs are not refreshed
automatically.

Gold menu labels use natural glyph proportions, larger 10–11 pixel lettering,
shared baselines and the measured sprite cells. The renderer refuses a label
that needs shrinking or exceeds its cell. Concise wording is used where needed.
Full original lettering cells are cleared so Japanese edge strokes cannot mix
with English letters. Character creation was checked in a native capture;
the other affected menus still need direct visual checks during normal play.

The caution body keeps its existing 12-pixel font and wraps inside a 416-pixel
region within the visible 480-pixel frame. A pinned PPSSPP software startup
reference shows the complete warning within that area.

The item-description pass audits all 6,077 entries in `000410e8` and `00040d77`.
Of 2,209 populated descriptions, 93 already fit and 2,116 needed changes:
1,693 word-preserving reflows and 423 concise rewrites of longer wording.
The remaining entries are names, labels, blanks or unused markers and stay
unchanged. The narrow inventory panel admits five rows at the original font
size. Lines allow 144 pixels of advance with six pixels reserved for glyph
overhang. No audited description exceeds either limit.

An explicit item-layout codec updates the actual MES row-count header and line
terminators. It rejects unsupported inline commands, changed colour operands,
lost quantities and altered rating stars. It preserves message aliases and
does not shrink fonts. Native inventory captures at both 30 and 60 FPS show
wrapped descriptions inside the panel; an owned-window check also confirms
normal menu navigation and clean exit with copied saves. The equipment status
screen was reached, but crafting and every individual description have not
been visually checked. Turnslash remains a separate three-line help correction.

All 327 story-movie captions use individual black plates covering the original
Japanese lettering and the existing English ink, with small margins. Source
ink is measured on multiple actual decoded frames; OCR text length is not used
as a clipping boundary. The English 18-pixel font, wording and timing stay the
same. The combined plate area is about 61% smaller. All 24 credits pages retain
their previous pixels. Japanese voices, music and sound effects are unchanged.

## Validation and regeneration

Private evidence and editable plans are in
`private/translation/container-layout/` and
`private/translation/container-caption-masks/`. The comprehensive item pass is
in `private/translation/item-layout/`, including coverage, concise wording,
delta verification, native captures and source-only promotion reports.
The earlier layout pass passed 273 source tests. The later English editorial
pass passes 274, with all 2,209 populated item descriptions rechecked against
the same limits. Current evidence and rebuild recipes are in
`private/translation/english-review/`; see [TRANSLATION.md](TRANSLATION.md).
The archive recipe is replayed
against the independent pinned v1.6 baseline: every changed resource reconstructs
exactly. The layout pass had 10,209 edited message blocks across 68 bundle variants;
the current editorial pass has 10,242 across 71 variants.
The item delta verifies exactly 2,116 changed blocks and 22,261 other resource
instances byte-identical to the preceding active WIP. The timing check verifies 98
timed MES cues and all non-text/audio resources. This is asset validation,
not full campaign or multiplayer acceptance.

The actual C movie-caption writer checks all 351 cues in four PSP pixel formats
(2,808 writes including interval boundaries), preserving stride padding. Native
opening routes check the decoded-frame cue indices separately at 30 and 60 FPS.
The first shortened input routes did not reach the movie and are not passes;
the final routes explicitly handle the new-save prompt and avoid movie skipping.

For a clean, payload-identical rebuild from the private pinned baseline:

```powershell
private/tools/python314/python.exe tools/build-full-translation.py private/translation/english-review/full-messages.json --textures private/translation/english-review/full-textures.json --output private/translation/layout-rebuild/archives --pass-number 23
private/tools/python314/python.exe tools/build-translation-image.py private/translation/layout-rebuild/archives --output private/translation/layout-rebuild/image
private/tools/python314/python.exe tools/check-translation-timing.py private/translation/layout-rebuild/archives --texture-report private/translation/layout-rebuild/archives/texture-text-report.json --output private/translation/layout-rebuild/timing.json
```

The installed archive retains its prior append history, so a clean rebuild can
have different archive/ISO hashes while reconstructing identical resource bytes.
Do not retain both full sets after validation; promote into the existing WIP
paths and keep only compact previous metadata, as specified in STORAGE.md.

Movie masks can be regenerated locally without editing or extracting audio:

```powershell
private/tools/python314/python.exe tools/fit-movie-caption-masks.py --collection private/translation/movie-captions/collection.json --samples private/translation/text-pass-18-all-movie-captions --output private/translation/container-caption-masks --resume
private/tools/python314/python.exe tools/build-movie-captions.py --collection private/translation/container-caption-masks/collection.json --output private/translation/container-caption-bundle
```

The working caption output is distinct from the approved active bundle.
Review source/composite frames and run `tools/validate-movie-captions.py` before
admission. Replacing the active bundle/image does not create new full backups.
Before a future tester release, regenerate the WIP distribution delta and its
manifest from the new image; the older distribution ZIP remains unchanged.
