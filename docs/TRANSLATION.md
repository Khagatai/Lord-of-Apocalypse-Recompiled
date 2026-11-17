# English translation integration

## Current WIP — pass 23 English editorial review, 2026-11-16

The source-only editorial pass changes 1,543 variant-specific message blocks
(1,542 resource/message pairs across 39 bundle variants). The review pairs the
current English with the original Japanese locally. A corpus of 21,885 nonempty
message/cue blocks is scanned for draft artifacts and terminology; this scan is
not a full semantic review of those blocks.

Direct corrections cover 112 distinct source records plus 339 equipment
description families, propagated only to matching source wording. Fixes include
literal draft braces, spelling, reversed mercenary-payment notifications,
misread speakers/actions, the Lord/Road error, repeated location names and
misplaced name/colour markers in quest and help text. Arcana, Seven Worlds,
Vermilion and Kirin use the existing translated name tables. Equipment now
separates the coloured Upgrade/No upgrades label from its description and
retains every rating star and numeric quantity. Fonts are not reduced.

All 2,209 populated shared item descriptions still fit five rows and 144 pixels
of advance, with a six-pixel overhang reserve. All 274 source tests pass.
Numeric guards accept equivalent full-width/ASCII digits while rejecting changed
values. The independent v1.6 recipe reconstructs all 194 changed resource variants,
including 10,242 cumulative message blocks. Exactly the reviewed message delta
changes; every other resource remains byte-identical to the preceding WIP.
All 98 timed MES cues retain their timing. Code, Japanese audio, movie-caption
pixels/timings, portraits and the HD pack are unchanged.

Native 30/60 inventory captures show the corrected Healing Rain description
inside its panel. The copied-save session exits normally; real saves and
preferences verify unchanged. This does not validate every quest/help panel,
story route, speaker context or later movie translation. The ambiguous item
title Road Phoenix and cryptic bestiary wording still need context; original
unused development-description placeholders are not grounds to invent gameplay
effects. Full campaign editorial/layout acceptance remains open.

Private evidence and editable plans: `private/translation/english-review/`.
The full rebuild recipe is `full-messages.json` with `full-textures.json` in
that folder; use the current pass-23 commands in [UI_LAYOUT.md](UI_LAYOUT.md).
Existing active image/archive
paths are replaced in place; no old full image/archive copy is retained.
Tester ZIPs and distribution deltas are not refreshed by this source update.

Current WIP ISO: 1,258,317,824 bytes, SHA256
`4516f35b5e009ab2e9e6a302700062e673261ff89028a01c1fc64d3d3f1a203d`.
The editorial pass left the native executable at
`259a0b3eb2717a659d651756f89cf5050b8e76e1a9710d1148c717ae4ff51670`.
The later [audio diagnostic update](AUDIO_AND_UI.md) supersedes that runtime
hash without changing the translated image.

## Earlier WIP — pass 20 and campaign movie captions, 2026-11-16

Normal WIP-English launches now load **327 English story captions** across
MOVIE01/03/05/08/10/13/17/20/22/26/28/36. All were transcribed and translated
locally from the original frames; their appearance/disappearance boundaries
were measured using actual decoded pictures. The original video and Japanese
audio payloads remain byte-identical. MOVIE24 has no subtitle footer text in the
reviewed half-second samples. A separate sparse whole-picture audit checks 207
samples outside subtitle footers; its five OCR candidates were visually checked
and contain scenery rather than additional readable text. Sparse OCR is not
exhaustive proof of absence.

MOVIE33 credits use 24 static pages for the original movie duration. All 360
source text lines are retained, with 144 English role/department/known-company
labels. Credited people's names, artist aliases and unresolved company spellings
retain their original glyphs: no name readings were guessed. This is deliberately
documented original-name artwork, not an all-Latin credits claim. Heading/name
page breaks and all caption layouts were reviewed. Credits use white serif
lettering at approximately the original size; story captions retain the fixed
18-pixel white Arial footer plate described below.

Pass 20 adds nine boss-movie thumbnail translations, removes a redundant tiny
Japanese reading below an existing English movie-title logo, and translates the
two previously missed CONQ_09 quest-result headings. Concise **Quest Info** and
**Stability** retain the source yellow and ten-pixel ink height. The exact Latin
font is an approximation. The active image has 9,983 changed MES entries,
120 translated images and twelve paired boss-caption layouts.

The final MES rescan checks all 21,894 entries: 21,880 have no Japanese script,
and the remaining 14 are protected functional password keys. This is content
coverage, not semantic approval of every existing machine draft. User/save names
are preserved. A native texture OCR audit scans 4,281 distinct top-mip images
from 5,176 XET variants (6,413 duplicate pixel images skipped). All 99 OCR matches
were reviewed; it found the two CONQ_09 headings, now translated. It does not
establish an exhaustive visual audit. Original Famitsu costume branding,
decorative equipment inscriptions/calligraphy and an indeterminate tiny pale
strip in PH01_98 remain original artwork. Persisted NPC-name provenance, legacy
demo-label display routes, editorial review and full campaign layout/route
acceptance remain open. **Translation completion is still not claimed.**

Verification: all 252 source tests pass. The actual C caption writer checks all
351 cue/page records at both interval edges in 5650/5551/4444/8888 formats:
2,808 pictures pass, with stride padding and surrounding pixels preserved.
The final image plays the entire opening in the native executable, presents all
18 expected cue starts, closes the media context and exits 0 at 6,900 VBLANKs.
Its opening pixels/timings match the previously approved normally paced 30-mode
and accelerated 60-mode runs. Later story/credits routes have not been exercised
through the guest game, and no listening test is claimed. PPSSPP interpreter/
software startup exits 0 and captures nine reference images; this is not a new
campaign-wide trace comparison.

Independent archive verification finds exactly 11 changed resources versus
pass 19 and 22,252 unchanged instances. All other payloads are byte-identical.
The stable-baseline comparison verifies 126 approved text/layout instances,
22,033 non-message instances and all 98 original timed-MES cues. Promotion
replaces the one active WIP image/archive pair and caption sidecar in place,
preserving 22 protected original/runtime/save/settings files. No superseded
full image/archive/pack copy is retained. Normal saved-launch preflight passes.

Active paths remain `private/translation/text-pass-16-image/` and
`text-pass-16-archives/`; captions are `movie-captions/captions.bin`.
ISO: 1,252,712,448 bytes, SHA256
`5fe9dd7fa0d4c181f7e41d5c3b31d06567bdc8b62a52fb1188427426509f8ec6`.
RZL: `274d54fd1ad5d74cf5840b6fa3e9af4d4e46747d16c0e621645fc2c709f57c34`.
RZP: `95fd5118b3525d5f351042391855345577a95c03fe18f14e1428f912a15a4443`.
Caption bundle: `58872158f5fffeb93d7646634be10b74f928c6a953fe30e9c30ac33b0a7ee2a8`.
Runtime executable remains `59080763f0f12d3a687d1fefa38cbc52a2017a34e3c22f99407e9bc5fca2045a`.

Evidence under `private/translation/`: `text-pass-20-final-delta-check.json`,
`text-pass-20-final-timing.json`, `text-pass-20-final-native/`,
`text-pass-20-final-oracle/`, `text-pass-20-residual-audit/`,
`text-pass-20-texture-audit/`, `text-pass-20-promotion.json`, and
`movie-captions/layout-review.json`, `writer-validation-all/`, `fullframe-audit/`.
Editable source text, rendered bitmaps and local OCR output remain ignored/private.

Rebuild the small caption candidate without copying an ISO or the HD pack:

```powershell
./private/tools/python314/python.exe tools/build-movie-captions.py --collection private/translation/movie-captions/collection.json
./private/tools/python314/python.exe tools/validate-movie-captions.py private/translation/movie-captions-candidate/captions.bin --output private/translation/movie-captions/writer-validation-candidate
```

The builder never overwrites an approved active bundle. Rebuilding produces an
unapproved candidate; validation and explicit local promotion remain separate.

## Earlier WIP — pass 19 and native opening captions, 2026-11-16

The active image/archive paths remain `text-pass-16-image/` and
`text-pass-16-archives/`, updated in place. Pass 19 corrects fifteen reviewed
dialogue/item entries, including nine literal `{protected}` drafting leaks.
The festival is now **Creation Festival**, consistent with the game's explicit
explanation that it celebrates its world's creation; the older Christmas
wording was incorrect. Four legacy demo-save records now have English labels
and descriptions, bringing the manifest to 9,983 entries. Existing 109 translated
images and twelve banner layouts are unchanged.

An independent comparison with pass 18 verifies exactly nineteen changed message
blocks and 22,259 unchanged resource instances. All other payloads are
byte-identical. The stable-baseline check still verifies 116 approved text/layout
instances, 22,043 unchanged non-message instances and all 98 original timed-MES
cues. Native startup exits 0 at 1,000 VBLANKs; PPSSPP interpreter/software exits 0
and captures nine images. All 251 source tests pass, and normal saved-launch
preflight passes. Twenty-two protected save/settings/original/runtime files
stay unchanged during image promotion. No superseded full image/archive is kept.

Active ISO: 1,252,591,616 bytes, SHA256
`e908ac31d7e6450a21c45c84eb6b14ba89df80aa5a67db61a188c2c2e4369cce`.
Archives: RZL `f5d39223e916069f18806bcd96c469430bfce58599b3f8aa6065712c570194f5`,
RZP `245ab4ca3dabcaedd4d886498c1b0185272feca6145eb979e132412eea2a0247`.
Evidence is in private/translation/: `text-pass-19-delta-check.json`,
`text-pass-19-timing.json`, `text-pass-19-native/`, `text-pass-19-oracle/`,
`text-pass-19-promotion.json` and `text-pass-19-launch-preflight.json`.

The obsolete legacy glyph interpretation is recorded explicitly in
`work/text-pass-19-legacy-review.json`. The 25 obsolete first-use Kanji indices
are contiguous (551–575); the original obsolete Unicode table has not been
recovered. Kana, punctuation and ASCII remain intact, and the inferred readings
align with published [demo-title information](https://support.jp.square-enix.com/faqarticle.php?id=1400&kid=56418&la=0&ret=main)
and the publisher's [trial/carryover description](https://mantan-web.jp/article/20101027dog00m200031000c.html).
This is a documented interpretation, not proof of the original font mapping or
of those legacy fields' actual display route. No glyph tables or save files change.

### Native movie captions

`tools/movie_subtitles.c` now draws private English bitmaps only after a real
decoded picture is produced. The exact first 144 PSMF header bytes select the
movie; actual decoded-picture indices select its cue. No host FPS clock,
invented HLE return, guest-code patch, re-encoded video or edited audio is used.
PSP 5650/5551/4444/8888 formats and destination stride are checked and tested.
Missing/invalid caption data logs an error and leaves the real movie picture
unchanged. Japanese and stable-v1.6 launches explicitly disable this WIP layer.

All eighteen MOVIE01 narration cues are enabled in normal WIP-English launches.
Visibility boundaries were measured per decoded frame using original ink/outline
contrast, with source-boundary PNGs retained. All eighteen source/English layouts
were reviewed. Both the accelerated 60-gameplay-mode run and a normally paced
30-mode run present the same eighteen cue-start frame indices, complete the
movie, close its real media context and exit 0 at 6,900 VBLANKs. Source saves
remain unchanged. This does not establish a listening test or full campaign
acceptance. Caption text uses fixed 18-pixel white Arial on an opaque black
448×48 footer plate: an explicit style approximation needed to cover baked text.

Runtime executable SHA256:
`59080763f0f12d3a687d1fefa38cbc52a2017a34e3c22f99407e9bc5fca2045a`.
The pinned framework checkout and guest image remain unchanged. Working caption
data and acceptance evidence live under `private/translation/movie-captions/`.
The current separate working candidate contains MOVIE01/MOVIE03/MOVIE05, 75 cues;
only MOVIE01 is approved in the normal launcher so far. Further scripts, movie
thumbnails/inscriptions, credits and language/layout review are still in progress.
The older coverage-gap notes below are historical where superseded here.

## Boss-caption assembly — included in WIP pass 18

The local pass-18 update covers twelve boss-banner variants, including the
duplicate banner: 24 English lines, twelve XET atlases and twelve paired UNM2
caption layouts. Each heading/name pair shares a horizontal centre; split
pieces use one horizontal font scale per line. Placement uses visible ink
measured **after** native palette conversion, rather than font advance widths.
This caught and corrected a SIEGFRIED chunk overlap missed by the initial
coordinate-only check. All 24 lines now have zero-pixel baseline error,
non-overlapping chunks, at least six pixels between lines, and centre agreement
within half a pixel in the static reconstruction.

Only caption UVs and instance positions change in UNM2. Headers, transforms,
colours and animation tables stay byte-identical. White serif lettering is a
font-style approximation; the exact original Latin font is unidentified, and
some long captions require horizontal condensation to fit the original atlas.
The local assembled review sheet has been inspected. This does **not** verify
the game's viewport, animation-time placement or actual boss encounters. The
captions are now included in the active WIP image after the bounded startup
checks below; boss-encounter acceptance remains open.

Recheck the private candidate without creating another full image/archive:

```powershell
./private/tools/python314/python.exe tools/check-caption-alignment.py private/translation/text-pass-18-aligned-banners/manifest.json --archives private/translation/archives/english-v16 --output private/translation/banner-alignment-review.json
```

The independent reconstruction report is
`private/translation/text-pass-18-aligned-banners/independent-alignment-final.json`;
the assembled sheet is `alignment-contact-sheet.png` in the same folder.
All 244 source tests pass, including actual-ink baseline/spacing/centre checks
and shared font-scale rendering. Native/PPSSPP boss-animation acceptance remains
required before claiming in-game alignment. The alignment tool's report records
`installed: false` because it measures the pre-install reconstruction; promotion
is recorded separately in `text-pass-18-promotion.json`.

## Earlier WIP image — text pass 18, 2026-11-16

Pass 18 replaces the active files in place at the existing `text-pass-16-image/`
and `text-pass-16-archives/` paths. It adds the twelve assembled boss banners,
eleven Japanese labels in the mixed-language CONQ_06 quest-result atlas, and
five promotional lines in SHARE_F. Existing English quest-label pixels are
checked byte for byte; two masks were corrected before installation to avoid
touching those letters. Native atlas sizes and palettes remain unchanged.
Quest labels use fixed 10-pixel bold Arial with concise wording; promotional
lettering approximates the original italic cream/red-outline style. These are
Latin font/style approximations, not identification of the original typeface.

The cumulative manifest contains 109 translated images in 101 XET resource
variants plus twelve caption-layout resources. The previous 9,979 message edits
are unchanged. Independent reconstruction verifies 116 admitted text/layout
instances, 22,043 unchanged non-message payload instances, and byte-identical
timing for all 98 subtitle cues in eleven timed bundle instances. All 308 ISO
payloads verify, with only REGFILE.RZL/RZP replaced. Movie/video/audio payloads
remain byte-identical to the stable English baseline.

Actual checks: native release/GPU exits 0 at 1,000 VBLANKs without timeout;
the pinned PPSSPP interpreter/software run exits 0 and captures nine images.
Native VBLANK 301 and PPSSPP 5 seconds both show the translated startup warning.
These are bounded startup observations, not matched gameplay traces or actual
boss/tutorial/result-screen acceptance. All 244 tests pass. Normal saved-launch
preflight passes. Promotion verifies 22 protected original/runtime/save/settings
files remain unchanged, including the executable and the user's 60-FPS setting.

Active ISO: 1,254,991,872 bytes, SHA256
`f57fdb392219cb9245567490fcd114629f24ede7c33c72c17ea651ca797ae9b7`.
Archive hashes: `e50f5ce3e9a5f9d63dd73ce940f788bb9f10b9c4646ad417d0a61a941fefc540`
(RZL), `da94000b0d4bb27e32e0d4695d420714ad36ce5ccc3269f4106a94bde284fb94`
(RZP). Evidence: `text-pass-18-staging/full-manifest.json`,
`text-pass-18-ui-typeset/`, `text-pass-18-timing.json`, `text-pass-18-native/`,
`text-pass-18-oracle/` and `text-pass-18-promotion.json` under private/translation/.
Superseded full image/archive payloads and the rejected initial archive candidate
are not retained. The older pass-17 section below is historical.

### Baked movie-caption gap

The local read-only survey successfully decodes all fourteen PMFs through the
pinned native Media Foundation backend: 69,731 decoded frames and 1,170 sampled
bottom strips. No movie/audio extraction copies or re-encoded media were made.
The finer opening survey contains 168 half-second samples. Review confirms
Japanese baked narration in MOVIE01, story dialogue in MOVIE03, and scrolling
Japanese credits in MOVIE33. The remaining samples still need complete visual
review; decoding a clip does not establish translation coverage.

All eighteen opening narration cues now have private English drafts, including
the short transition and final negation missed by the initial three-second
survey. Input source/header hashes and observed frame brackets are recorded in
`text-pass-18-opening-timing/opening-english-draft.json`. Boundaries remain
uncertain within the 15-frame sampling step. These drafts are **not displayed
in-game yet**. A timed native text overlay, coverage of the other movie dialogue
and credits, and synchronization/layout checks remain necessary. The existing
98 MES subtitle cues do not cover all of this baked text.

Other open coverage: Japanese movie-thumbnail captions, legacy demo-save
metadata, equipment-brand/inscription classification, editorial review of
dialogue drafts, and full campaign layout/save-load acceptance. No whole-game
translation completion claim is made.

HD validation on 2026-11-15 also observes Japanese captions in the opening movie
at vblank 2200, `private/menu-art-native-title-01/run/native-4x.png`. This is an
additional video-caption coverage gap; a clean MES-script scan does not cover
it. The clip, its captions and Japanese audio remain unchanged. Translation
work was paused for the HD texture pass and resumes below. The later corrected title
checkpoint skips the movie and is recorded separately as `menu-art-native-title-02`.

The HD art audit also identifies Japanese equipment inscriptions and promotional
branding, including PS14 / PW06_12 and PB00_45 / PB01_45. These are retained for
the later text-art audit. User-entered or existing Japanese character names in
copied save data are preserved. The HD-label pass rerenders the same 221 existing
English regions at 4x and does not add translations or alter the WIP ISO.

The broader UI review also finds Japanese boss introduction banners in
`CO_BN_01` through `CO_BN_11`, and Japanese captions embedded in several
`ICO_MV` movie thumbnails. Environment atlases such as `HEI_POSTER`,
`HEI_CARPET2` and several `KOMONO` prop sets contain printed artwork. These
are added to the later text-art audit; the neural environment admission excludes
these props rather than synthesizing replacement lettering. The faithful UI
scaler retains the original banner and thumbnail text.

The copied-save Mercenaries list in `private/hd-menu-live-05/0025-circle.png`
also displays Dolphstein's name in Japanese even though his dialogue label is
English. This may be a name persisted in the Japanese-origin save fixture;
the storage source needs tracing before changing it. The save is preserved.
The battle-style descriptions on this screen also need editorial review.

The remaining-art review identifies Japanese tutorial instructions in
`AVA_LCK01` / `AVA_LCK02` and promotional text in `SHARE_F`. `CONQ_06` contains
mixed English/Japanese labels within one atlas; actual UV use still needs checking
before treating every Japanese region as visible in play. These assets remain
unchanged for the later text-art pass. The printed world-map lettering in `C_MAP`
is also excluded from unrestricted neural restoration.

## Earlier WIP image — text pass 17, 2026-11-15

The active image/archive files were replaced **in place** at the existing
`text-pass-16-image/` and `text-pass-16-archives/` paths to avoid retaining another
full game copy or changing launcher/save paths. Pass 17 adds English HOLD/TOGGLE
headings and instructions to both `AVA_LCK01`/`AVA_LCK02` lock-on tutorial cards:
two images, four bounded text regions in resource `00020e28`. Existing 9,979
message edits and the other 93 translated images remain. The cumulative text
texture manifest covers 95 images in 87 resource variants.

Typography follows the user's request to preserve fonts, colours and sizes.
Headings use the measured pale yellow `#FFFEC0`, body text stays white, original
palettes and cell bounds remain fixed, and the chosen 12/10-pixel bold sans-serif
sizes never shrink automatically. Concise English wraps within the original
caption area. Arial is a style approximation: the exact original Latin font face
has not been identified. Yellow Japanese caption ink is removed selectively to
retain underlying grey controller shading. Controller art, arrows and borders
remain outside the admitted text changes. Exported previews were inspected;
the actual tutorial screen's in-game layout still needs review.

All 308 ISO payloads verify, with only REGFILE.RZL/RZP changing. Independent
reconstruction checks 90 approved texture instances, 22,069 unchanged non-message
payload instances, and all 98 subtitle timing cues in 11 timed bundle instances.
Japanese audio/non-text assets stay byte-identical. Native release/GPU startup
exits 0 at 1,000 VBLANKs without a timeout; the pinned PPSSPP interpreter/software
startup exits 0 and captures all nine requested images. These are bounded startup
checks, not matched gameplay traces or tutorial-screen acceptance. All 238 source
tests pass, including selective caption erasure and rejection of automatic font
shrinking. Normal launch preflight passes; saves, preferences (including 60 FPS),
original ISO, modules and current executable remain unchanged.

Active ISO: 1,250,471,936 bytes, SHA256
`9c386f0d2fa44e72179c27939b0a6c2e5e9a95c2c39abaf059f4a533d540679c`.
Archive hashes are `5bd0de302d395e99b34a9db7f9e7df889721793126c6414fcbf674dcdd1c4296`
(RZL) and `b8d9efb87b75c3a4d1f6de283d13f40734e6058179f46190d4627cf6927df639`
(RZP). Evidence: `private/translation/text-pass-17-typeset/`,
`text-pass-17-timing.json`, `text-pass-17-native/`, `text-pass-17-oracle/`,
`text-pass-17-promotion.json` and `text-pass-17-launch-preflight.json`.
Superseded image/archive bytes and failed raw pixel scratch are not retained.

Rebuild content from the retained stable English archives, MES manifest and
reviewed pixel manifest; use one staging set and remove it after validated
in-place promotion. Physical archive placement can differ from the incremental
build; the independent payload checks are required:

```powershell
private/tools/python314/python.exe tools/build-translation-batch.py private/translation/work/text-pass-14-manifest.json --output private/translation/rebuild-current-messages
private/tools/python314/python.exe tools/build-texture-text-edits.py private/translation/text-pass-17-typeset/manifest.json --archives private/translation/rebuild-current-messages --output private/translation/rebuild-current-archives
private/tools/python314/python.exe tools/check-translation-timing.py private/translation/rebuild-current-archives --texture-report private/translation/rebuild-current-archives/texture-text-report.json --output private/translation/rebuild-current-timing.json
private/tools/python314/python.exe tools/build-translation-image.py private/translation/rebuild-current-archives --output private/translation/rebuild-current-image
```

Still incomplete: semantic/context review of machine drafts, boss introduction
banners and their companion glyph placement, promotional/thumbnail/environment
lettering, opening movie captions, four legacy metadata records, and full campaign
layout validation. Japanese names or comments persisted in saves are not silently
rewritten as translation assets.

## Previous WIP image — text pass 16, 2026-11-15

Normal WIP launches now select `private/translation/text-pass-16-image/`, while
retaining the existing WIP save namespace. Stable v1.6 and Japanese selections
remain separate. `tools/graphics_settings.py` owns the active WIP folder used by
the launchers and diagnostics; the text-test shortcut uses the same selection.

This update adds **221 translated pixel regions across 91 images**: 78 regions
in 16 menu/tutorial/loading textures and 143 labels in all 75 measured loading-map
variants. Compact labels use explicit abbreviations where the original UV cells
are narrow. Names on maps are matched to existing patch terminology. Including
the earlier two notices, the cumulative manifest changes 93 images in 86 XET
resource variants. The existing 9,979 message edits are retained.

Four-bit text writes now preserve the neighbouring nibble, row/tile addressing,
palettes and metadata, with a synthetic regression. Typesetting stays local and
refuses labels that do not fit at six pixels or larger. Failed fitting, the first
unbounded fitting-loop attempt and early atlas-boundary corrections are retained
under private evidence; corrected bounded rendering produced the admitted image.

Actual candidate checks:

- All 308 ISO file payloads verify; only REGFILE.RZL/RZP change.
- Independent reconstruction verifies 89 repeated approved texture instances,
  22,070 unchanged non-message payload instances, and 98 byte-identical subtitle
  timing cues in 11 timed bundle instances. Audio/non-text assets are unchanged.
- The normal HD release exits 0 on the town camera route: 58 chains / 174 mip
  levels, zero mip-upload failures; source saves, 54 fonts and prefs unchanged.
- The pass-15 predecessor also passes an actual game-menu capture after town
  loads. An earlier attempted menu capture was still in the introduction and
  correctly failed the demanded mip-draw check; it is not menu evidence.
- PPSSPP interpreter/software pass-16 startup exits 0 and captures all nine
  requested images, with the copied source save unchanged. This is startup
  evidence, not full route trace equivalence or campaign acceptance.
- All 128 source checks pass; normal-launch preflight selects the admitted image
  and the native HD executable without automatic input.

Current image SHA256:
`232119ab1d98a8c555eb650f0ea1e908755ad4f24b035be2c308a57dec768d10`
(1,249,687,552 bytes). Archive SHA256 values:
`REGFILE.RZL`: `3d7afbadec47678f170fbe1232ed9b01a9281b09f86cf2a78bb1c4626a0d9b04`;
`REGFILE.RZP`: `a9630f4f8b1f490e20a38af675673c0620c3a4ef8d5289f72824fcdc82bc0b0d`.

Evidence: `private/translation/text-pass-15-native/`, `text-pass-15-menu-02/`,
`text-pass-16-native/`, `text-pass-16-oracle/`, `text-pass-16-timing.json`,
`texture-text-map-review-16/` and `texture-text-map-sheets-16/`.

Reproduce with the private reviewed manifest and pixels present:

```powershell
./private/tools/python314/python.exe tools/build-texture-text-edits.py private/translation/text-pass-16-map-typeset-01/manifest.json --archives private/translation/text-pass-14-message-archives --output private/translation/rebuild-pass16-archives
./private/tools/python314/python.exe tools/check-translation-timing.py private/translation/rebuild-pass16-archives --texture-report private/translation/rebuild-pass16-archives/texture-text-report.json --output private/translation/rebuild-pass16-timing.json
./private/tools/python314/python.exe tools/build-translation-image.py private/translation/rebuild-pass16-archives --output private/translation/rebuild-pass16-image
```

Translation is **not complete**. The expanded review found twelve boss-banner
resource variants (including a duplicate Nidhogg image), title/promotion text,
and outstanding legacy metadata. Boss banners have individually positioned
glyphs in companion UNM2 data; replacing each atlas with a whole paragraph would
scramble its UV pieces. That layout is being measured before edits. Wider texture
coverage, embedded-text coverage, draft meaning/token placement and campaign
layout review remain open. Existing machine drafts include errors that still
need correction; absence of Japanese in normal MES strings is not quality proof.

The user supplied v1.6_2020.12.28, containing an xdelta patch, application batch
file and README. No editable message sources or extractor/repacker are bundled.
The included batch file was inspected, not executed. Credits in its README name
Serberker, Sabaku.D.Tonio, Jinouga and Square Enix. Translation content and patch
files remain private; this project's script license does not license that content.

## Exact identities

| Artifact | SHA-256 |
|---|---|
| Original Japanese ISO | 3a4d63713880dfb67ade00b6a912ac4975847cec06b1ab341b65963f328e1c93 |
| User v1.6 xdelta patch | 4f344ff39ccfea127272b32bbdf17844fdb0e1013bb2e9b40f1f3fa1c07c2ae7 |
| xdelta 3.0.11 x64 ZIP | eca90daab9cd8388ffa17fb4d6808bb0616cc5d37a7682126485dba1c79f86bf |
| Decoder executable | d81f59b2fe5e8589c0ee9782e231c805084f4d23dfade413903a4cad63b4e342 |
| Patched ISO, 969379840 bytes | 0664c2abf543e23002b2340b9e5a833dcc238420db4cd2d4781e1928ea4db3ae |

Decoder source: [official xdelta release](https://github.com/jmacd/xdelta-gpl/releases/tag/v3.0.11).
The official x64 ZIP was downloaded over HTTPS and its exact identity recorded;
no independent published checksum/signature verification is claimed.
Only its exact named decoder member was extracted to private/tools/xdelta/.
Original ISO hash was checked before and after decoding and remains unchanged.
Normal xdelta target checksums stayed enabled; no force/checksum bypass was used.

## Actual results

The output retains NPJH50503, disc 1.01 / app 01.00 and 308 file records.
Only UPDATA/REGFILE.RZL and UPDATA/REGFILE.RZP content changes; EBOOT, LIBFONT,
the install archive and other file contents are unchanged. 307 directory records
have changed placement/extent metadata, so raw-LBN behavior still needs checking.
The original static executable is reused only because executable content matches.

Native optimized/GPU capture at VBLANK 990 shows the English no-save prompt.
The pinned PPSSPP interpreter/software run of the same patched ISO shows that
prompt in English too. Native exits 0 at the explicit 1000-VBLANK diagnostic
boundary. These are bounded visual observations, not a full translation or
campaign/save/load pass. Japanese remains the default/reference launcher.

Start-English-Preview.cmd selects only the exact pinned English image. This is
the existing partial v1.6 translation; no new translation has been added yet.

## Archive investigation

The strict read-only RGF1 parser validates index bounds, resource size sums,
zlib completion/expanded lengths and distinct identifiers. Both archives contain
9807 compressed groups, 22263 descriptors and 18055 distinct resource IDs.
The comparison finds 16 changed IDs, all kind-4 .MES message bundles.
Repeated IDs are not assumed identical: the original has 13 IDs with multiple
content variants, and the English patch retains both original/patched payloads
for at least one ID. Inventory preserves each variant's hash and group membership.
Six synthetic parser checks pass, including truncation, invalid extent, wrong
expanded length, corrupt zlib and zero/nonzero alignment-tail handling.

## Message decoding and reinsertion

Resource 00050d78 is a version-1 .TTL table containing 2357 UTF-16 codepoints.
It is identical in both languages, SHA-256
2f29fa6c9691c3f055c812a3fa2a5f84f2bb52ef742ab09857581b1064e0280a.
The table decodes the Japanese text as well as the existing English translation.
MES framing contains a message offset directory, four metadata words per
message, and length-prefixed lines ending in FFFE/FFFF. The codec preserves
directory aliases, metadata, original line count and zero alignment words.

The private export proves byte-exact bundle round trips for 74 Japanese payload
variants and 73 English-v1.6 variants. Japanese has 23020 message entries:
23001 framed, 19 opaque, 19403 eligible for plain-text edits. English v1.6 has
21815 entries: 21796 framed, 19 opaque, 18547 plain-text editable. These totals
include aliases and differing resource variants; they do not measure completion
or indicate missing messages. Opaque records are preserved without modification.

9979 English-v1.6 entries across 57 resource IDs contain Japanese script; 7410
are plain-text editable. This is a review queue, not an untranslated percentage.
Some entries contain proper names or functional promotional passwords that must
not be translated indiscriminately. Inline formatting, icons, substitutions and
their operands remain unresolved by the editor: such messages are refused.

The manifest editor checks the original bundle hash, message hash and Japanese
text before applying each edit. It rejects alias conflicts, unsupported glyphs,
unresolved commands and line-count changes. The archive writer addresses an
exact (resource ID, original payload hash) pair, preserving other variants. It
appends a rebuilt compressed group and changes only that group's index fields.
Every resulting resource is independently decompressed and checked against the
expected replacement or unchanged original.

The ISO writer appends candidate archives to a separate image and updates both
endian copies of file extents/sizes and the primary volume length. It preserves
old extents and all other file contents. This intentionally increases image size;
raw-LBN access to replaced archives still needs validation. Diagnostic candidate
admission checks the full image hash and independently rejects changes to any
file outside the two archives. Stable launcher identities stay unchanged.

## First new translation batch: candidate only

Eight mercenary-help messages in resource 00040d43 have draft English wording.
The private manifest is private/translation/work/mercenary-help.json. Their
original line counts are preserved; no inline commands are involved.

| Candidate artifact | SHA-256 |
|---|---|
| Rebuilt MES | d05952695b35cee7bd9d3221073862e3cb10c7bf2b155407fb0be9544c8bb72c |
| REGFILE.RZL | d59391607a1b4e12588047a2478b67dcfebcfaa5c010681fa02e22adc0ca8082 |
| REGFILE.RZP | 12d2f30facbcf5226132e62a42b8bd0cda07c60541eddad0722914bd8087ba53 |
| WIP ISO, 1232975872 bytes | b0e133ec43126da999931508abdcb7ed283d6480b57e5e98db60aa550316630a |

Only group 380 is rebuilt, containing one matching resource instance. All 308
ISO files are checked; only the two archives differ in content. Original and
stable v1.6 images remain unchanged. Evidence directories:

- private/translation/mercenary-help-candidate/
- private/translation/mercenary-help-archives/
- private/translation/mercenary-help-image/
- private/translation/mercenary-help-native/
- private/translation/mercenary-help-oracle/

Native release/GPU exits 0 at the explicit 1000-VBLANK boundary, without timeout.
Its VBLANK-991 image and PPSSPP's 12-second image both show the saved-data-loaded
prompt using an isolated copy of the Japanese tutorial save. PPSSPP captures all
nine requested images and exits 0 at its emulated-time bound. Save sources stay
hash-identical. This establishes bounded boot/load behavior after reinsertion;
the eight changed messages have NOT yet been displayed or layout-validated.
The WIP image is not selected by Start-English-Preview.cmd.

## Text pass 01: expanded candidate

The user clarified that translation scope is text only. No voices, music or
sound effects are translated or replaced. The batch writer rejects resource
kinds other than MES (kind 4), and archive verification checks every unrelated
payload, including audio, against its original bytes.

The expanded private draft has 552 distinct messages (including the previous
eight), applied to 2949 physical message blocks/directory entries across 38
bundle variants and 38 groups. Repeated messages across chapter bundles receive
the same wording only when the entire original line array matches exactly.
The four draft sets cover NPC services and field hints, mercenary conversations,
guild induction, World Conquest help, and opening town/sanctuary dialogue.
Existing English text is retained. Functional passwords and unresolved inline
commands remain untouched. Some names and the term dark-possessed are provisional;
the private draft glossaries record these review items.

Drafts preserve original line counts and use a provisional 48-glyph line limit.
This is a conservative editing check, not measured pixel-width or layout proof.
Three initial line-count mismatches were corrected before the final manifest.
Opaque message records and messages with unresolved commands are still refused.
Remaining story chapters, item descriptions, names, command-rich messages and
any text outside MES still need translation/review. No completion percentage
or complete-story claim is made from entry counts.

| Text-pass artifact | SHA-256 |
|---|---|
| Checked batch manifest | bc5961d77e0d7d13292835246547af2da5bdabc992f148075358cf7cae23b0b7 |
| REGFILE.RZL | a75c7d593d182c35f04063e7c8517c64df5fa23a422537217798992ca8e80274 |
| REGFILE.RZP | 9b7ace353d1a3a341674fa6886a474ab52889e1b020fe7ffe860fd19f755f194 |
| WIP ISO, 1233414144 bytes | 713c3e9937a2aec75d3d8cdaf1e2de778693e5dfc924e1ebd1ea87eb388ab980 |

Private drafts are under private/translation/work/: services, town-early,
town-middle and guild-town source/draft JSON pairs. The final manifest is
text-pass-01-batch.json. Repacked archives and the image are under
private/translation/text-pass-01-archives/ and text-pass-01-image/.
Every resource and all 308 ISO files verify against expected changes; code,
fonts and non-message assets remain unchanged.

Actual diagnostics:

- text-pass-01-native-boot/: native release/GPU exits 0 at the explicit 1000
  VBLANK bound, without timeout. VBLANK-991 image says saved data auto-loaded.
- text-pass-01-oracle/: pinned PPSSPP interpreter/software captures all nine
  requested images and exits 0 at the 25-second emulated-time bound. Its
  12-second image also says saved data auto-loaded. The scripted input route
  reaches the Access Games logo by the 24-second capture.
- text-pass-01-native/: the longer scripted route hits its 30-second wall
  timeout before the requested VBLANK-3600 exit. The last capture, VBLANK 3466,
  shows a loading screen. It is not a passing route or a proved game failure;
  the terminated run and actual return code 1 are preserved.

Save fixtures stay hash-identical. These are visual boot/load observations,
not new-dialogue layout checks, trace-equivalence or campaign acceptance.
46 synthetic title checks pass, including batch alias counting, conflicting
draft refusal, stale-identity checks and rejection of audio-kind replacements.

Start-English-Text-Test.cmd explicitly selects this draft candidate with its
verified build report. Its preflight checks the full image hash and independently
rejects changes to non-message ISO files. It retains the existing right-stick
camera profile and uses its own persistent english-text-test save namespace.
Japanese and stable English launchers still select their original identities;
all three preflight commands pass without opening a window. Normal English
preview remains v1.6. See SAVE_STORAGE.md for the isolated test-save copy.

To reproduce with the private drafts present, choose fresh output paths:

```powershell
./private/tools/python314/python.exe tools/prepare-translation-batch.py --pair private/translation/work/services-source.json private/translation/work/services-english.json --pair private/translation/work/town-early-source.json private/translation/work/town-early-english.json --pair private/translation/work/town-middle-source.json private/translation/work/town-middle-english.json --pair private/translation/work/guild-town-source.json private/translation/work/guild-town-english.json --output private/translation/work/text-pass-01-batch-new.json
./private/tools/python314/python.exe tools/build-translation-batch.py private/translation/work/text-pass-01-batch-new.json --output private/translation/text-pass-01-archives-new
./private/tools/python314/python.exe tools/build-translation-image.py private/translation/text-pass-01-archives-new --output private/translation/text-pass-01-image-new
```

39 synthetic title checks pass, covering codec framing, growing edits and
aliases, stale manifests, inline-command refusal, archive variants, ISO bounds
and diagnostic rejection of non-message file changes.

Remaining work: reach the mercenary screens and compare the changed text in
native/PPSSPP; prove command operand framing; classify and translate the remaining
story/NPC/menu/tutorial text in context; check wrapping, icons, substitutions and
functional strings; test a full campaign. Full English translation is incomplete.

## Japanese audio and expanded text work — 2026-11-14

The requested output keeps the original Japanese speech, music and sound effects.
MES text resources and explicitly reviewed text-pixel regions in XET textures
may change. `check-translation-timing.py` independently compares other payloads,
including audio, against the v1.6 baseline. Its optional texture report reconstructs
approved pixel edits from source-bound private inputs, retaining palettes and metadata.
Timed subtitles retain their original clock fields, cue boundaries and line
counts. Preserving bytes and timing does not establish translation accuracy or
readability during playback.

Two additional message formats now have lossless parsers: legacy save/install
labels use CP932 byte counts, and timed subtitles contain explicit start/end
clock fields. Save metadata wording was checked against a recovered PARAM.SFO.
Four other legacy entries remain unresolved and are preserved. Functional
Japanese password strings remain unchanged because they are matching keys.

The directly authored second candidate contains 632 distinct translations,
including 76 distinct subtitle text arrays and four save/install labels. Its
private image is `text-pass-human-02-image/LordOfApocalypse-English-WIP.iso`,
SHA-256 `e4a38d6fe94ee6cddf9a557230bba5521476d618c43c8b4fdeddb522ca5f6505`.
The independent comparison verified 22,159 unchanged non-message payload
instances and 98 unchanged timed cues across repeated archive instances. All
308 ISO files were checked; only the two message-containing archives changed.
Native release/GPU diagnostics exit 0 at the explicit 1,000-VBLANK bound without
timeout. Pinned PPSSPP interpreter/software diagnostics exit 0 at the 25-second
emulated-time bound and capture all nine requested images. The PPSSPP 12- and
24-second images show the saved-data-loaded prompt; these are startup/load
observations, not cutscene subtitle-layout or full-boot acceptance. The source
save hashes remain unchanged. Private evidence is in `text-pass-human-02-native/`
and `text-pass-human-02-oracle/`. `Start-English-Text-Test.cmd` now explicitly
selects this candidate; its isolated persistent save namespace is retained.

Remaining dialogue, reference text and equipment descriptions are being drafted
locally with a hash-pinned Qwen model and llama.cpp. Model files, source passages,
drafts and local server credentials stay under ignored `private/`; no game text
is submitted to an external translation service. Failed CPU-model experiments
and rejected GPU drafts are retained as diagnostic evidence and are not accepted
translations. Protected command operands, names, numeric values and ratings are
checked before any draft can enter a private candidate. Structural checks do not
provide semantic approval: pronouns, terminology, omissions and line layout still
need review. Machine draft counts are not a completion percentage.

The inventory also needs a complete review of texture text. The two inspected
PNG icons contain the English title logo; 5,176 XET texture containers have not
received a visual text audit. The bounded embedded-string survey found no
qualifying NUL-terminated CP932/UTF-8 strings in the main ELF's allocated
non-code sections. It does not cover UTF-16 or the sectionless font PRX.
The translation remains incomplete; save namespaces remain separate pending
bidirectional compatibility testing.

## Reproduction

The latest text-test selection is **text pass 14**, built on 2026-11-14. It changes
9,979 message entries across 68 MES bundle variants, plus two notice images within
one XET resource variant. All 5,089 remaining normal-message templates now have
English drafts passing structural checks; 832 source-bound direct corrections
were applied, followed by 14 directly translated reward notifications and a
separate correction to a badge description. Most remaining model drafts have
not received a full semantic/context review. Counts are not a completion percentage.

The independent post-build MES inventory has 21,894 entries: 21,876 contain no
Japanese script, four are unresolved legacy demo-save metadata, and 14 are literal
promotional password keys. The password resource also contains display notifications;
those are now translated. The edit layer refuses password-key changes, including
attempts through aliases. Keys are functional input values rather than prose.
The four legacy records decode with inconsistent kanji. Trying the supplemental
glyph table did not resolve them; their meanings have not been guessed or replaced.
Next fix: identify the original legacy glyph mapping in the import/export path.

| Latest private artifact | SHA-256 |
|---|---|
| Combined MES manifest | 791b8ca717bfc6d35760276c7ce07a97222bc1cde462fb2c1da50cfd33d794cb |
| REGFILE.RZL, including notice textures | 562928ffcefffa71edbdbc7c35239dd34a838884ff1516104e1b9e69e08e7eab |
| REGFILE.RZP, including notice textures | f77880a936646a1f052b5f19a95ae235f5f847bc43b9e996016f23d02f9e9597 |
| WIP ISO, 1,242,513,408 bytes | af8dad2acbf5bd7b0ca37a29d5dbc058b4aa76f9712a7f38b1278dbdbeeeb978 |

The candidate is `private/translation/text-pass-14-image/`. All 308 ISO payloads
verify: only the two REGFILE archives differ. The independent resource comparison
checks 22,158 unchanged non-message payload instances, reconstructs the one
approved text-texture variant, and verifies 98 unchanged subtitle cues across
11 repeated timed bundle instances. The audio/non-text result is unchanged.
The broader non-message result is deliberately false because the two text images
were translated. No guest executable, font table, shared runtime or native binary
was changed.

XET v1 parsing now covers all 5,176 resource variants. Selected interface previews
revealed Japanese in the caution and demo-notice images. English was typeset
locally with Windows fonts; no image or text was sent to a rendering/translation
service. Only approved pixel rectangles are re-encoded, using each original palette.
Other texture pixels, palette bytes, mip descriptors and names remain unchanged.
The four-byte pixel colour and swizzle code has synthetic bounds/palette tests.
Inventory is not a visual audit: most textures remain unreviewed, and two small
interface previews were refused rather than decoded by guessing their swizzle layout.

Actual final-candidate checks: native release/GPU exits 0 at 1,000 VBLANKs without
timeout; PPSSPP interpreter/software exits 0 at its 25-second emulated bound and
captures all nine images. Native VBLANK 301 and PPSSPP 5 seconds display the
translated warning. Fixture source hashes remain unchanged. Evidence is in
`text-pass-14-native/` and `text-pass-14-oracle/`. This is visual startup evidence,
not full trace equivalence, campaign acceptance or translated-dialogue layout proof.
All 85 title checks pass. Earlier rejected numeric values, instruction leaks,
command-order errors and wrapping failures were corrected or excluded; their
private evidence is retained.

`Start-English-Text-Test.cmd` explicitly selects this verified image/report and
retains its existing isolated save namespace and controller profile. The stable
English launcher still selects original v1.6; the Japanese launcher retains the
unmodified dump. Shared saves remain deferred pending bidirectional testing.

Rebuild with the private reviewed inputs present, choosing fresh output directories:

```powershell
./private/tools/python314/python.exe tools/build-translation-batch.py private/translation/work/text-pass-14-manifest.json --output private/translation/rebuild-mes
./private/tools/python314/python.exe tools/build-texture-text-edits.py private/translation/work/texture-notices-manifest.json --archives private/translation/rebuild-mes --output private/translation/rebuild-text
./private/tools/python314/python.exe tools/check-translation-timing.py private/translation/rebuild-text --texture-report private/translation/rebuild-text/texture-text-report.json --output private/translation/rebuild-timing.json
./private/tools/python314/python.exe tools/build-translation-image.py private/translation/rebuild-text --output private/translation/rebuild-image
```

Private typesetting specs, source images, translated passages, pixel buffers and
model weights are required local inputs and are excluded from the source checkout.
Full translation acceptance remains open: resolve legacy metadata, complete the
texture and embedded-text audit, review model drafts in context, verify substitution
placement and text layout, then test the campaign and save/exit/reload milestones.

From the project root after installing the exact private decoder:

```powershell
./private/tools/python314/python.exe tools/apply-english-patch.py
./private/tools/python314/python.exe tools/inventory-translation.py --archives private/translation/v1.6/archives --output private/translation/inventory-new
./private/tools/python314/python.exe tools/launch-preview.py --language english-v16 --check
```

Message work uses local private archive copies and fresh output directories:

```powershell
./private/tools/python314/python.exe tools/export-messages.py --archives private/translation/archives --output private/translation/messages-new
./private/tools/python314/python.exe tools/build-message-edits.py private/translation/work/mercenary-help.json --source private/translation/message-corpus/00040d43-1c0e4306454e718b.bin --glyph-table private/translation/glyph-table-unicode.bin --output private/translation/mercenary-help-candidate-new
./private/tools/python314/python.exe tools/build-translation-archives.py private/translation/mercenary-help-candidate-new --output private/translation/mercenary-help-archives-new
./private/tools/python314/python.exe tools/build-translation-image.py private/translation/mercenary-help-archives-new --output private/translation/mercenary-help-image-new
```

The local manifest, extracted message corpus and glyph bytes are private inputs,
not included in a source checkout. Diagnostic tools accept an explicit
--candidate-report path to the image's result.json with --language english-v16;
the Japanese and stable English launchers retain their pinned image selection.
The separate text-test launcher uses an explicit candidate image and report.

Patch output must be fresh; existing evidence is never overwritten. The initial
session extracted archive copies to private/translation/archives/ and its final
inventory is private/translation/archive-inventory-aligned/. The first inventory
attempt lacked the portable interpreter's module path; the next identified four
zero alignment bytes after the last index record. Both failures are retained;
the final parser handles that measured padding and rejects nonzero tails.
All text, patch payloads, archives, images and game-derived resource files stay
under private/ and are never sent to external translation services or Git.
# Current language and build-input policy

The playable languages are English WIP and Japanese. Standalone v1.6 has been
removed from both launcher and F1 menus. Its full ISO, extracted baseline archive
pair and obsolete generated distribution delta were hash-checked and deleted,
reclaiming 1,234,435,618 bytes. Existing saves remain untouched. Legacy preferences
selecting v1.6 migrate to WIP in memory, preserving their other choices.

WIP startup checks every non-message file against the pinned hash manifest in
`config/translation-baseline.json`; it no longer opens or reconstructs v1.6.
Player setup uses one direct Japanese-to-WIP delta. The original upstream patch
remains a small private authoring input, with its existing attribution.
`tools/translation_baseline.py` reconstructs baseline build inputs only when a
translation tool needs them, verifies their hashes, and removes its owned
temporary ISO/archive files on exit. The existing active WIP image/archive pair
is unchanged. Earlier sections below describe historical passes and evidence.
