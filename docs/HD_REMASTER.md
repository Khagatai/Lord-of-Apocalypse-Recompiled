# HD renderer and remaster work — 2026-11-15

The final archive texture coverage pass is installed in place: **28,189 PNGs,
34,071 identity/context groups, 12,706 complete-mip groups**. Strict identity
coverage is complete for all 10,713 non-portrait descriptors; the 39 dialogue
illustrations stay original. Zero catalog identities remain unmatched or
unresolved. Manifest SHA256:
`e69f5f92d52c8ba122b35d30cb74a9718824bebb375a9eb4ad4b6912b7c5c661`.
Town, sanctuary dialogue and inventory checks pass with zero texture failures
or interpreter use; 179 source tests pass. See [current coverage and exact
limits](HD_ASSET_COVERAGE.md). Full campaign visual acceptance remains open.

The sections below preserve earlier stages and their evidence. Counts, hashes,
unmatched identities and source-test totals below are historical, unless
explicitly identified as belonging to this final coverage pass.

Current requested scope: environments, every UI asset and 3D character models.
Dialogue portraits now use the original game artwork. The 39 reviewed NAMED/NPC
illustrations have been removed from the active replacement INI (312 identity/context
groups, 156 PNGs). Model atlases, dialogue frames and English text remain upgraded.
The archive and original-UI builders exclude these portrait families and their
key aliases. Normal rendering filters still apply to the original artwork.

`tools/restore-original-portraits.py` performs this metadata change in place;
it does not edit the ISO, audio or source pixels. The native sanctuary dialogue
checkpoint exits 0, loads 340 replacements, uploads 82 mip chains/246 levels,
and reports zero texture failures, rejected chains, interpreter instructions,
interpreter entries or dispatch misses. Saves, 54 fonts, settings and pack
metadata remain unchanged during the run. The actual original-portrait screenshot
was inspected. Local evidence is `private/original-portraits/`.
All five captured GPU frames differ from the prior material-pack checkpoint only
inside the portrait rectangle (x=26..471, y=562..1071 at 1920x1088); world, frame
and text pixels outside it are identical. See `frame-comparison.json` there.

Portrait-policy reproduction (the output holds only a report; PNG payloads are
left unreferenced for audited cleanup after rollback metadata no longer needs them):

```powershell
private/tools/python314/python.exe tools/restore-original-portraits.py --pack private/hd-remaster-pack --catalog private/remaster-coverage-08 --output private/original-portraits --apply
```

The original-UI scaler now explicitly admits power-of-two source sizes below
32 pixels, including button strips and loading text. It still requires complete
authored mip geometry, exact source identities and the existing PNG/INI checks.
The neural builder retains its minimum source dimension of 32. New selection
tests cover small sources, invalid dimensions and malformed mip tails.

The previous portrait-policy pack in `private/hd-remaster-pack/` contained 24,806 PNGs,
30,171 identity/context groups and 10,686 complete-mip groups. Manifest SHA256:
`de5b6db41ced79ad10d04e761b9254a01351411e9af5ba4e84688c907be42271`.
Current native town and inventory checks exit 0 with no texture failures,
interpreter instructions, interpreter entries or dispatch misses.
The later storage cleanup removes superseded copies; old versioned paths below
are historical references. Follow [the in-place storage policy](STORAGE.md) for
new work, rather than the historical full-copy reproduction commands.

The validated authored-mip renderer is now integrated into the normal release.
**Start-Game.cmd** uses it automatically with texture scaling or HD UI enabled;
Original and the GDI fallback disable it. Capture remains off in ordinary play.
The normal WIP HD toggle selects the working pack, retaining the
earlier world materials, ornaments and English UI. The separate **Start-HD-Remaster-Preview.cmd** retains its isolated saves and
eight-chain precomputed pilot pack. This is an HD rendering milestone; a full
campaign visual review remains unfinished. Translation is
paused while the requested HD artwork pass continues.

## Current sky and UI pass

The in-place update adds 36 sky/cloud source sets: 368 independently decoded
context/mip PNGs preserve the pinned alpha and invisible source RGB exactly.
Source and restored contact sheets were inspected. Cloud contrast and fine
detail still need review in the campaign scenes that use those materials.
The UI update adds 105 source sets / 420 context-level outputs using the faithful
original-art scaler. All RGBA pixels match its independent reference. Three
sets (CMN01/17/19) add missing aliases using byte-identical existing PNGs;
102 source previews and all 105 result previews were inspected. This includes
small button strips, menu headings, icons, maps, window labels and shared effects.
Existing Japanese image text is preserved for the later translation pass.

Native town loads 237 replacements and uploads 58 mip chains / 174 levels;
inventory loads 166 replacements and uploads 32 chains / 96 levels. Both pass
with unchanged source saves, fonts, preferences and pack metadata. Actual
screenshots were inspected. All 162 captured town source mip levels match the
corrected catalog. The capture does not confirm the new sky sets were drawn,
and no new matching PPSSPP campaign trace is claimed.

Evidence: `private/environment-sky-work/result.json`,
`private/environment-sky-check/result.json`, `private/ui-completion-work/result.json`,
`private/ui-completion-check/result.json`, `private/remaster-current-town/`,
`private/remaster-current-inventory/` and their contact-sheet reviews.
Validated generation scratch, duplicate preview PNGs and raw checkpoint PPMs
were pruned; compact reports, hashes, review sheets and actual screenshots remain.
There is one active pack and one compact metadata rollback.

The latest identity audit counts 9,977 fully covered descriptors, 39 deliberately
original dialogue illustrations, 675 without a pack match and 61 ambiguous or
wildcard identities still refused. These include aliases and potentially unused
assets; they are not campaign completion percentages. Remaining effects,
world-sign lettering, material variants and full campaign review remain open.
All 168 source tests pass; the index audit accepts 209 source files and two pinned
gitlinks without copyrighted or binary payloads. See `private/hd-coverage-current/`.

In-place sky reproduction (the builder can reuse its owned working folder):

```powershell
private/tools/python314/python.exe tools/build-archive-remaster.py --catalog private/remaster-coverage-08 --base-pack private/hd-remaster-pack --neural-tool private/tools/realesrgan-20220424/package --output private/environment-sky-work --pattern '.*(?:SKY|CLOUD).*' --allow-alpha
```

Already covered source sets are retained; a subsequent run can report no
admissible uncovered artwork. Independent checks require a fresh scratch output
and a batch report whose manifest matches the current pack. Historical batch
reports intentionally retain their stage's manifest hash after later updates.

## Background additions and pack verification

The default `private/hd-remaster-pack-06/` is the byte-identical copy of
`private/background-remaster-01/pack`: 22,959 unique PNGs, 28,223 identity/context
groups and 9,566 complete-mip groups. Manifest SHA256
`6f306da20a495b6757fd949bbf3110d7563380cf89ceda726f75e9709f164ad0`;
INI SHA256 `4b967fe27c6faa4bc3618d1ce1a4a48ce4dae7c6a6e5ce3a751c245b0e8fe9c3`.
All 28,111 groups of pack 05 retain their geometry, levels and PNG hashes.
The 14 added source sets include text-free backdrops, scene thumbnails, two
ruin atlases, foliage and a metal ornament. Printed world-map lettering remains
unchanged. All 112 context/mip PNGs pass the independent alpha/invisible-RGB
check; the base restoration contact sheet was viewed and hashed.

Fresh native title and town checks exit 0 without timeouts or texture failures,
with zero interpreter entries/instructions and dispatch misses. The title loads
36 replacements; town loads 235 and uploads 58 chains / 174 levels, with 56
replacement chains queued. Source saves, fonts, preferences and pack hashes
remain unchanged; actual screenshots were viewed. Evidence:
`private/background-native-title-01`, `background-native-town-01`,
`background-alpha-check-01` and `hd-pack-06-admission.json`. These compatibility
checks do not establish every new backdrop as drawn, or validate the campaign.
The sanctuary/inventory checks below certify the predecessor manifest, not 06.

The source verifier now reads each PNG once for both its SHA256 and header
checks, retaining the same path, hash, geometry and exact-INI requirements.
All 155 source tests pass, including corrupt-file and malformed-pack refusal.
This removes duplicate reads; no measured launch-speed claim is made.

Normal saved-settings preflight passes for the exact pack-06 manifest and pinned
executable (`private/hd-default-preflight-06.json`). Its offline audit finds
9,628 complete four-context descriptor identities, 1,053 without a pack identity,
61 ambiguous/wildcard-only identities and ten incomplete source decodes. There
are 3,560 unique pixel chains with all descriptor aliases covered, of 4,293.
These remain archive figures, not a campaign-completion percentage.

## Corrected 16-bit palette blocks

The ten earlier decode failures were an offline decoder bug. One GE CLUT load
block is 32 bytes: eight 32-bit colours or sixteen 16-bit colours. The decoder
and catalog identity calculation incorrectly limited a 16-bit block to eight
colours. Resource `000201fb` uses colour format 1 and indices through 15.
The native pinned `src/rt/ge.c` LOADCLUT case and the pinned
[PPSSPP getClutLoadBytes implementation](https://github.com/hrydgard/ppsspp/blob/1aebad2c651ff9d0684ee335e43aceff8fc7e3ec/GPU/GPUState.h#L309)
both confirm the 32-byte extent. The correction retains strict resource bounds;
zero-length loads still refuse to invent a retained palette.

An additional offline mismatch used arithmetic scaling for 5-/6-bit channels,
instead of the bit replication used by both pinned renderers. This is also
corrected before admitting the new material chains. `tools/check-xet-colours.py`
extracts conversion functions from the exact pinned PPSSPP Git object, compiles
them privately and compares all 196,608 possible 16-bit colours. All match.
The deliberately wrong arithmetic-scaling negative control produces 111,420
mismatches and exits 1 as expected. Evidence: `private/xet-colour-reference-01`
and `xet-colour-reference-negative-01`. The read-only usage audit finds only
these ten descriptors use the affected colour formats (`xet-16bit-usage-01.json`).

Fresh exported catalog `private/remaster-coverage-08/`, SHA256
`b9fa3212fe952b1386929c4d46a8ff3285da5ff4e55545d39359747f7c48632b`,
decodes all 10,752 descriptors with zero failed authored levels. All 162 earlier
native capture comparisons still match, with zero pixel mismatches. All 10,742
previously complete descriptors retain identical decoded-level metadata; only
the ten corrected palette descriptors change candidate keys. Evidence:
`private/hd-palette-catalog-comparison-02.json`,
`hd-colour-catalog-comparison-01.json` and
`hd-palette-span-forensics-01.json`. This does not establish the ten corrected
chains as observed in a live campaign scene. Their restoration remains separate
until artwork review and native checks pass. All 159 source tests pass,
including all three 16-bit formats and truncated/zero-load refusal.

The running 136-set material batch retains its exact catalog-06 provenance.
The comparison proves its already decoded source data unchanged; existing
inference caches and their source pins are preserved.

Catalog 07 and `gdw-remaster-01` are retained as intermediate evidence and are
not admitted: they predate the colour-expansion correction. The catalog-bound
`config/remaster-gdw-materials.json` selects nine newly decoded material chains
from catalog 08. A mixed pink light-strip pillar remains on ordinary scaling.
The corrected restoration is generated separately under `gdw-remaster-02`.

## Remaining material batch

All 23 original-art triage sheets in `private/remaining-original-sheets-05`
were viewed: 676 unique base previews across 677 eligible uncovered chains at
the pack-05 baseline. The first 14 sets were admitted above. The catalog-bound
policy `config/remaster-remaining-materials.json` now selects 136 further
material/foliage sets and 1,372 context/mip jobs against pack 06. This is a
candidate batch, not default admission or restored-art validation. Printed
artwork, UI lettering, water, glows and projectile streaks remain unchanged.

Reproduce this batch with fresh private output paths:

```powershell
$materialPolicy = Get-Content config/remaster-remaining-materials.json -Raw | ConvertFrom-Json
if ((Get-FileHash private/remaster-coverage-06/catalog.json -Algorithm SHA256).Hash.ToLowerInvariant() -ne $materialPolicy.required_catalog_sha256) { throw 'Reviewed catalog hash mismatch' }
$materialPattern = '(?:' + ($materialPolicy.include_name_patterns -join '|') + ')'
./private/tools/python314/python.exe tools/prefill-remaster-cache.py --catalog private/remaster-coverage-06 --base-pack private/hd-remaster-pack-06 --neural-tool private/tools/realesrgan-20220424/package --output private/remaining-materials-cache-batch-01 --cache private/remaster-remaining-materials-cache-01 --pattern $materialPattern --allow-alpha --limit 256
./private/tools/python314/python.exe tools/build-archive-remaster.py --catalog private/remaster-coverage-06 --base-pack private/hd-remaster-pack-06 --neural-tool private/tools/realesrgan-20220424/package --output private/remaining-materials-remaster-01 --cache private/remaster-remaining-materials-cache-01 --pattern $materialPattern --allow-alpha --skip-existing --limit 256
./private/tools/python314/python.exe tools/check-archive-remaster.py --batch private/remaining-materials-remaster-01 --catalog private/remaster-coverage-06 --output private/remaining-materials-alpha-check-01
```

Stop on any nonzero exit status. Existing output directories are deliberately
refused; inference caches are reused only after their exact identities verify.

After the material PNG check and restored-art review, the selection policy
retains 134 sets and excludes two narrow reflection panes:

```powershell
./private/tools/python314/python.exe tools/filter-archive-remaster.py --batch private/remaining-materials-remaster-01 --base-pack private/hd-remaster-pack-06 --check private/remaining-materials-alpha-check-01 --policy config/remaster-remaining-selection.json --output private/remaining-materials-selected-01
$gdwPolicy = Get-Content config/remaster-gdw-materials.json -Raw | ConvertFrom-Json
if ((Get-FileHash private/remaster-coverage-08/catalog.json -Algorithm SHA256).Hash.ToLowerInvariant() -ne $gdwPolicy.required_catalog_sha256) { throw 'Reviewed corrected catalog hash mismatch' }
$gdwPattern = '(?:' + ($gdwPolicy.include_name_patterns -join '|') + ')'
./private/tools/python314/python.exe tools/prefill-remaster-cache.py --catalog private/remaster-coverage-08 --base-pack private/hd-remaster-pack-06 --neural-tool private/tools/realesrgan-20220424/package --output private/gdw-cache-batch-02 --cache private/remaster-gdw-cache-02 --pattern $gdwPattern --allow-alpha --limit 64
./private/tools/python314/python.exe tools/build-archive-remaster.py --catalog private/remaster-coverage-08 --base-pack private/hd-remaster-pack-06 --neural-tool private/tools/realesrgan-20220424/package --output private/gdw-remaster-02 --cache private/remaster-gdw-cache-02 --pattern $gdwPattern --allow-alpha --skip-existing --limit 64
./private/tools/python314/python.exe tools/check-archive-remaster.py --batch private/gdw-remaster-02 --catalog private/remaster-coverage-08 --output private/gdw-alpha-check-02
./private/tools/python314/python.exe tools/merge-remaster-packs.py --pack private/remaining-materials-selected-01 --pack private/gdw-remaster-02/pack --output private/hd-remaster-candidate-09
```

The nine corrected-palette sets pass independent checks for all 108 PNGs, and
their restored-art sheet was viewed. The earlier material batch passes all
1,372 PNG alpha/invisible-RGB checks; all five restored-art sheets were viewed.
The merged candidate has 24,423 PNGs, 29,367 groups and 10,462 complete-mip
groups. All 28,223 base groups retain exactly the same geometry and PNG hashes
(`private/hd-pack-07-preservation.json`). Native checks still determine admission.

`config/validation-routes.json` now contains the title, town, sanctuary and
inventory input sequences. They match the earlier private routes token for
token; `--route` writes a private padscript and records both hashes. An explicit
copied-save fixture is required; missing fixtures are refused before creating
a run folder or opening the game. Route inputs are source data, not game assets.

```powershell
./private/tools/python314/python.exe tools/check-xet-colours.py --output private/xet-colour-reference-new
./private/tools/python314/python.exe tools/check-hd-ui.py --route town --pack private/hd-remaster-candidate-09 --output private/hd-materials-town-new --save-fixture private/memstick/english-text-test --mip-textures --require-mip-replacements --texture-scale 4 --quality --seconds 180
```

Use `--route sanctuary` or `--route inventory` for their separate checkpoints.
The source route chooses the corresponding bounded capture window. These
fixtures still need independent matching PPSSPP campaign-route replay; they
must not be interpreted as campaign acceptance.

## Earlier transparent character, foliage and prop admission

`private/hd-remaster-pack-05/` is the tested candidate 08 copied without changes:
22,847 unique PNGs, 28,111 identity/context groups and 9,510 complete-mip groups.
Manifest SHA256 `6349964d57b214b0df19db929fccce0c31f1e45f3f75d6827aa54109cc0e411c`;
INI SHA256 `b70c76802dee000994f5eae6c6441e8c72f2c2fa2c3d4f01c8bc4d685564daf7`.
All 20,951 groups of pack 04 preserve their geometry, mip count and PNG hashes
exactly (`private/hd-pack-05-preservation.json`). Additions are 720 selected
transparent character/equipment sets, 106 foliage sets, 42 opaque props/terrain
sets and 27 illustrated NPC cutouts. These are source-chain counts, not models.
All generated context/mip PNGs pass independent alpha/invisible-RGB checks;
all base-art contact sheets were viewed. Effects remain excluded by policy.

Fresh combined-pack native tests on the unchanged `4cfb0cfe…` executable:

| Route | Uploaded chains / levels | Replacement chains queued |
| --- | ---: | ---: |
| Town camera / movement | 58 / 174 | 56 |
| Sanctuary dialogue | 82 / 246 | 81 |
| Inventory | 32 / 96 | 31 |

All exit 0 without timeouts, texture decode/factor/upload failures or rejected
replacement chains. Interpreter entries/instructions and dispatch misses are
zero. Source saves, fonts, preferences and pack hashes remain unchanged; actual
screenshots were viewed. Evidence: `private/hd-combined-{town,sanctuary,inventory}-08`
and `hd-pack-05-admission.json`. This does not certify every newly added asset
as exercised: full campaign/combat, new matching PPSSPP route traces and sustained
performance still require validation.

The independent offline audit `private/hd-coverage-05` finds complete identities
in all four contexts for 9,614 of 10,752 descriptors, versus 6,904 for pack 04.
There are 1,067 without pack identities, 61 ambiguous/wildcard-only descriptors
and ten incomplete source decodes. Of 4,293 unique pixel chains, 3,546 have all
descriptor aliases covered. This is archive identity coverage, not a percentage
of the game visually remastered. Ordinary runtime scaling serves unmatched art.

In the older catalog 06, all ten incomplete descriptors belong to resource `000201fb`, source SHA256
`38f4ed0760912cf56daf7d45706378fc3dbae4b52b4485a27daa55e5d7777a43`:
the `BG22_GDW` ground, beam, fence and pillar families. Every one of their three
authored levels reports `Palette lookup outside allocation`. The private list
is `hd-source-decode-failures-05.json`. The later palette-block correction above
resolves their offline decoding without fabricated colours. Live binding/CLUT
capture is still needed to certify their use during campaign play.

Normal saved-settings preflight also passes with the exact pack-05 manifest and
executable (`private/hd-default-preflight-05.json`). The normal HD-toggle town
checkpoint `private/hd-default-town-05` exits 0, uploads 58 chains / 174 levels
with 56 replacement chains queued, and preserves source saves, fonts, settings
and pack hashes. Its actual screenshot was viewed. All 155 source tests pass;
the Git index audit contains 197 UTF-8 source files and two pinned framework
gitlinks, with no protected or binary payloads.

The subsequent 14-set background/prop batch is recorded above. Its original
art was reviewed in remaining-art sheets 016/021/022, with printed world-map
lettering deliberately held out.

## Earlier broad archive pack admission

The earlier WIP toggle used `private/hd-remaster-pack-04/`: 17,283 unique
PNGs, 20,951 identity/context groups and 7,822 groups with complete authored
mip chains. These counts include aliases, wrap contexts and palette variants;
they are not counts of distinct characters or locations. Manifest SHA256
`4904bde111724b085c85efc6d155c4439407066ffed8b689c1aeb4453313416b`,
INI SHA256 `fe5791d6f88e2d1aa50518d7b792a81aaf6336819106f6ed7e081f1fb624a16d`.
All 295 identity groups of the previous 411-image pack retain exactly the same
geometry, mip levels and PNG hashes: `private/hd-pack-04-preservation.json`.

This combines the 103 eligible opaque NPC/monster source sets, 1,038 opaque
player/equipment sets, 944 selected environment sets, menu artwork and faithful
original UI scaling. It includes all 91 rerendered English label atlases / 221
regions, using the existing wording. No disc image, MES script or audio changes.
The 401 further UI sets have 1,604 context PNGs whose decoded RGBA bytes exactly
match an independent pinned-scaler run. Player art's 4,152 context PNGs and
the complete environment generation's 12,744 context/mip PNGs pass independent
alpha and invisible-RGB checks. Check reports remain under
`player-alpha-check-01`, `environment-alpha-check-01`,
`hd-original-ui-check-02` and `hd-english-label-check-01`.

All 35 player, 37 environment and 14 faithful-UI base contact sheets were viewed
locally, with hashed records in their private `manual-review.json` files.
This review identified gradients, additive glows, animated water, skies and
text-bearing props mixed into the environment archive. The explicit policy in
`config/remaster-environment-selection.json` holds back 142 source sets.
`tools/filter-archive-remaster.py` requires the exact independent check and base
manifest, excludes a shared atlas if any alias is denied, and preserves every
base group. Candidate 07 is the admitted pack's byte-identical source. The
unfiltered environment candidate is retained as evidence, not the normal default.

Actual filtered native checks on executable `4cfb0cfe…`:

| Route | Loaded PNGs | Uploaded mip chains / levels | Replacement chains queued |
| --- | ---: | ---: | ---: |
| Town camera / movement, 8200–8210 | 234 | 58 / 174 | 56 |
| Sanctuary dialogue, 8900–8910 | 341 | 82 / 246 | 81 |
| Inventory, 7000–7010 | 164 | 32 / 96 | 31 |

All three exit 0 without timeouts, decode failures, factor errors, upload
failures or rejected replacement chains. Each records zero interpreter entries
and dispatch misses; copied-fixture source saves, all 54 fonts, normal preferences
and pack hashes remain unchanged. Actual screenshots were inspected. Evidence:
`private/hd-filtered-town-07`, `hd-filtered-sanctuary-07` and
`hd-filtered-inventory-07`. The earlier full candidate checks remain separately
under `hd-environment-*` and do not certify a different manifest.

The copied-save interactive session `private/hd-menu-live-04` reaches load data,
town, Options and four Status pages using real SDL key events. It exits 0 after
2,179 seconds, with zero interpreter entries, texture decode/upload failures,
or changes to source saves, fonts, preferences or pack. That session uses the
6,318-image UI candidate, so it does not certify the later environment pack or
combat performance. Audio options remain unchanged.

Full campaign replay against PPSSPP, combat visual checks, every gear/UV variant,
sustained FPS and remaining alpha/text-art coverage are still open. The catalog's
30 palette-bound decode failures and two ambiguous small-texture keys remain
explicitly refused. Neither PNG generation nor these bounded native checks
establish complete HD remaster coverage.

The same normal saved-toggle selection passes preflight and the town camera
checkpoint, `private/hd-default-preflight-04.json` and `hd-default-town-04`.
The latter exits 0 with 58 chains / 174 levels, 232 loaded replacements and
zero decode/upload failures, interpreter entries or dispatch misses. The 153
source tests pass; the Git index audit contains 194 UTF-8 source files and two
pinned framework gitlinks, with no game-derived or binary payloads.

`tools/audit-hd-coverage.py` measures offline identity coverage independently of
scene testing. `private/hd-coverage-04/result.json` counts 6,904 of 10,752
descriptors with a matching complete chain in all four contexts; 3,777 have no
pack identity, 61 have only ambiguous/wildcard identities, and ten have
incomplete source decoding. The catalog's 30 failed authored-level records
belong to those ten descriptors. Of 4,293 unique pixel-chain signatures
(including missing-source records), 2,651 have all descriptor aliases covered.
These are archive coverage figures, not distinct game objects or playable
campaign coverage. Ordinary renderer scaling still serves unmatched textures.

The next private batches select only nonopaque character/equipment chains and
named foliage, explicitly retaining every existing canonical or context key.
`--alpha-only --skip-existing` on the builder and `--alpha-only --base-pack`
on the cache producer share this selection. Generation preserves pinned-scaler
alpha and invisible RGB; separate decoding and review are still required before
admission. Preparing a cache does not install a pack.

Repeat the selection and normal-launch checks with fresh private output paths:

```powershell
./private/tools/python314/python.exe tools/filter-archive-remaster.py --batch private/environment-remaster-pack-01 --base-pack private/hd-original-ui-pack-02/pack --check private/environment-alpha-check-01 --policy config/remaster-environment-selection.json --output private/hd-selected-new
./private/tools/python314/python.exe tools/audit-hd-coverage.py --catalog private/remaster-coverage-06 --pack private/hd-remaster-pack-04 --output private/hd-coverage-new
./private/tools/python314/python.exe tools/launch-preview.py --variant saved --check
```

## Normal release integration

### Additional transparent-art candidates

The private foliage batch contains 109 nonopaque source chains / 1,228
context-and-mip PNGs. All independently decoded alpha planes and invisible RGB
bytes match the pinned scaler exactly (`foliage-alpha-check-01`). All four base
contact sheets were viewed. Three grayscale tree-card variants are held back
under `config/remaster-foliage-selection.json` until their shadow/backdrop use
is observed. The selected 106-set candidate has 18,499 unique PNGs, manifest
`6efc7e4932f355392152040e612fa60b411bb0ad1f0fc1142e2aaca71f5ea113`.
Its admitted additions are now included in pack 05.

Selected-candidate town and sanctuary checks exit 0 with zero decode/upload
failures, interpreter entries or dispatch misses, preserving saves, fonts,
preferences and pack hashes. Actual screenshots were viewed. They load 234 and
341 PNGs and upload 58/174 and 82/246 mip chains/levels, respectively. All five
paired town GPU frames and five guest snapshots are byte-identical to pack 04:
`private/foliage-town-comparison-01.json`. This demonstrates compatibility in
the existing route; it does not prove that the new unvisited foliage assets
were exercised. Evidence is under `foliage-selected-native-town-01` and
`foliage-selected-native-sanctuary-01`.

The 794-set transparent character/equipment batch has independent alpha and
invisible-RGB checks for all 4,064 context/mip PNGs. All 27 base contact sheets
were viewed. The exact-batch policy in
`config/remaster-character-transparency-selection.json` excludes 47 effect sets
by asset index, because some effect names also identify real body atlases.
Index exclusions require both the exact pack manifest and generation-report
hash; an alias match excludes the entire atlas. Another 27 illustrated NPC
cutouts use the separate anime-model batch instead of the general model.
The selected general-model batch admits 720 source sets. Its unfiltered town
and sanctuary checks pass, but do not certify a later selected or merged pack.

The 27 anime-model portraits and 42 additional opaque prop/terrain sets also
pass independent alpha/invisible-RGB checks (108 and 472 PNGs respectively).
Their one and two base contact sheets were viewed locally. Hashed review
records remain beside each private sheet set. These reviews cover base art;
they do not establish every mip, UV mapping or campaign scene as visually sound.

Repeatable combined candidate generation, after the independent checks and
selection policies have passed:

```powershell
./private/tools/python314/python.exe tools/merge-remaster-packs.py --pack private/character-transparency-selected-01 --pack private/foliage-alpha-selected-01 --pack private/additional-opaque-remaster-02/pack --pack private/npc-illustration-anime-remaster-01/pack --output private/hd-remaster-candidate-08
```

The merger refuses conflicting artwork for a shared identity. Outputs must be
fresh private directories; retained evidence is never overwritten. This
candidate passed the fresh native checks recorded above before default admission.

The pack-04 interactive session `private/hd-menu-live-05` loads the copied save,
reaches town, Mercenaries and mercenary Status, and exits 0 after 1,221 seconds.
It loads 171 replacements and uploads 32 chains / 96 levels with zero
decode/upload errors, interpreter entries or dispatch misses. Source saves,
fonts, preferences and pack hashes stay unchanged. Brief inputs during concurrent
offline inference were unreliable; longer recorded ordinary key holds reached
the menus. This is not an FPS benchmark or campaign-equivalence result.

The current release adds sampler-aware replacement selection, executable SHA256
`4cfb0cfe0931838c25a543cdebf19a0df688d650d6357e9de57022a6c5dfb41a`.
It is byte-identical to the validated sampler prototype. Four independently
restored wrap contexts can use separate host replacement keys; the renderer
selects the key from the actual GE wrap state. Original game memory, texture
identities recorded by the observer and legacy pack fallback are preserved.
The launcher rejects a sampler-aware pack with an incompatible executable.

Actual sampler integration evidence:

- Eleven synthetic Vulkan cells pass at each of two render/texture scales,
  including direct-colour and indexed palettes, four wrap states, all authored
  mip levels, resident-cache switching and legacy fallback.
  `private/sampler-gpu-check-03/result.json`.
- Deliberately wrong wrap selection and base-only mip selection are detected at
  both scales: `sampler-gpu-negative-03/` and `sampler-base-negative-03/`.
- Four shared disabled-mode startup GPU frames and five sanctuary Quality GPU
  frames are byte-identical to the previous release. The first startup frame
  falls outside the old build's capture window and is explicitly unpaired.
  All 237 captured original mip identity/level/pixel records also match exactly.
  `private/sampler-native-comparison-03.json`.
- The Quality comparison uses a fixture with identical PNG bytes under four
  tagged keys, not four independently restored contexts. It proves lookup
  integration; new artwork batches still require their own review.
- All 144 source tests pass at this integration point. Full-campaign PPSSPP
  replay, sustained performance and exhaustive visual acceptance remain open.

`tools/title.py build --profile release` generates a fingerprint-checked private
renderer copy and includes `tools/renderer-enhancements.mk`. The diagnostic
profile retains the upstream renderer. The previous executable is retained under
`private/release-backups/`, named by SHA256. No upstream file is edited.

The initial integrated executable was byte-identical to validated prototype build 04:
`f7f44dfb8d79da349a0b682e962658e9834c13f68904657632d5ebaa2b194a29`.
The guest flat image is unchanged:
`b0d370ebcfb33df3517a40c97c1b5c0ef0f6d7ed71a1efc6a4fce7e73c46dfb0`.

The later F1 label change to **HD textures / UI (WIP only)** produces executable
`a89dd400004b10647bd3ed8f38bae19d932419ddb24a3ab7db2660531b91b1ab`.
Its renderer fingerprints and guest flat image remain the same. The previous
executable is preserved in `private/release-backups/`.

Actual additional release checks:

- Town camera/movement route exits 0 at the 8200–8210 capture window, uploads
  58 chains / 174 levels, records 91,044 mip binds and zero mip-upload failures.
  UI replacements load and bind; the screenshot was inspected locally.
  `private/hd-release-native-01/summary.json`.
- Original, Balanced and Quality startup checks all pass with copied source
  saves unchanged: `private/hd-release-profiles-01/`.
- Five GPU frames with the mip extension disabled and all other Quality settings
  matched are byte-identical to the previous release. The first comparison used
  different graphics settings and differed; that invalid comparison is retained.
  Corrected evidence: `private/hd-release-off-comparison-02.json`.
- Source saves, 54 font files and preferences remain unchanged in these checks.
  All 128 source tests pass, including the later four-bit text-region test.

These bounded checks do not validate campaign completion, sustained FPS, every
streamed material or new PPSSPP trace equivalence. Runtime upscaling applies as
textures are loaded; it does not create newly authored surface detail.

## Offline restoration pilot

### Portraits and dialogue ornaments

The earlier portrait-stage WIP toggle selected `private/hd-remaster-pack-03/`: **411 PNGs**.
It retains all 355 previously admitted images and adds 12 named-character
portrait expressions plus two text-free dialogue ornament atlases, each restored
independently for all four clamp/repeat combinations. Both archive alignment
identities are mapped; 295 groups include these aliases, not 295 unique artworks.
Portraits use the pinned local x4plus-anime model after comparison with x4plus.
The text-bearing COM_WIN atlas is explicitly excluded. Japanese audio and all
translation payloads remain unchanged.

Actual evidence:

- All 12 portrait previews and the two ornament atlases were inspected.
- Independent stb PNG decoding checks all 48 portrait and eight ornament alpha
  planes against separately generated pinned-xBRZ references. Every alpha byte
  and invisible RGB byte matches. `private/portrait-alpha-check-01/` and
  `private/dialogue-frame-alpha-check-01/`.
- Native sanctuary conversation checks exit 0 with all replacements exercised,
  82 mip uploads / 246 levels, no rejected chains or decode/factor/upload errors.
  The combined pack loads 312 needed PNGs, with one worker queue-full event using
  the normal original fallback. Source saves, 54 fonts and preferences stay
  unchanged. Screenshots were inspected locally.
  `private/portrait-native-sanctuary-01/` and
  `private/dialogue-frame-native-sanctuary-01/`.
- Five portrait-only GPU frames change only the lower-left 128x128 PSP portrait
  footprint; all surrounding pixels are identical to the previous pack.
  `private/portrait-native-comparison-02.json`. The first comparison guessed a
  narrower 440-pixel region and failed; it is retained rather than overwritten.
- Cache replay uses zero new inferences, preserves every output PNG identity and
  verifies deterministic compiled helper identities.
  `private/portrait-cache-replay-01.json`. Earlier helper timestamps prevented
  reuse; private helper links now omit the PE build timestamp.
- The normal saved-toggle town camera route also exits 0: 58 mip uploads / 174
  levels, 56 replacement operations, 204 needed PNGs loaded, no rejection,
  decode/factor/upload failures. Two worker queue-full events use the original
  fallback. Saves/fonts/preferences stay unchanged; screenshot inspected.
  `private/hd-default-town-03/`. The normal saved launch preflight passes with
  the current executable and 411-image manifest, `hd-default-preflight-03.json`.

This covers the archive's NAMED portrait family, not every campaign conversation
or UI atlas. Full campaign appearance, sustained FPS and new PPSSPP trace replay
remain unvalidated. NPC/monster archive batches are still undergoing review.

Portrait-stage manifest SHA256:
`19ff221db8987e09fd9c2a94a8a91c51ed123327137a8bdf8e29b322ef9114c2`.
Portrait-stage INI SHA256:
`c0a39b48fd5377049c8ae4d188ccb67ca18c0a4b493b76073908489f8a8d87ab`.

```powershell
./private/tools/python314/python.exe tools/build-archive-remaster.py --catalog private/remaster-coverage-06 --base-pack private/hd-remaster-pack-02 --neural-tool private/tools/realesrgan-20220424/package --output private/portraits-new --cache private/remaster-inference-cache-01 --pattern 'NAMED[0-9]{3}' --allow-alpha --model realesrgan-x4plus-anime
./private/tools/python314/python.exe tools/check-archive-remaster.py --batch private/portraits-new --catalog private/remaster-coverage-06 --output private/portraits-alpha-new
```

### Faster offline archive batches

`tools/prefill-remaster-cache.py` plans the same exact padded inputs and alpha
references as the ordinary builder, then uses the official local tool's
directory mode to retain the loaded model between images. It creates no game
pack. Every generated output is independently decoded before cache admission;
the ordinary builder rechecks the cache identity, PNG hash, extent and alpha.
Failed/missing output is reported and never substituted with fabricated pixels.

Two mixed-size directory outputs are byte-identical to separate invocations,
`private/restoration-directory-check-01/result.json`. A four-context portrait
batch also matches every earlier per-image PNG exactly and is consumed by the
ordinary builder with four cache hits and zero new inferences:
`private/batch-cache-comparison-01.json`. A separate tile-size timing trial did
not show a useful speed improvement; production keeps the established 128 tile
size. This is a generation optimization, not a game FPS claim.

All **103 eligible opaque NPC/monster archive sets** are generated. The first
32 produce 272 context/mip PNG jobs; the remaining 71 produce 692. All 964
independently decoded alpha/invisible-RGB comparisons pass, and all five
base-art contact sheets were inspected. The combined candidate has 1,368 unique
PNGs and 1,119 alias/context groups. The sanctuary route exits 0, with 82 mip
uploads / 246 levels, 312 needed PNGs loaded and no rejection, decode/factor or
upload errors. All five GPU frames match the previous 411-image pack exactly;
the visible characters were already covered there. This is a pack/scene
regression check, not proof of unvisited monster appearances or combat.
These candidates await broader combined admission. Counts exclude alpha-bearing,
incomplete and unsupported-geometry textures.
`private/character-remaster-pack-01/`, `private/character-alpha-check-01/`,
`private/character-review-sheets-01/`, `private/character-batch-cache-02/`,
`private/character-remaster-pack-02/`, `private/character-alpha-check-02/`,
`private/character-review-sheets-02/`, `private/character-native-sanctuary-02/`,
`private/character-native-comparison-02.json`.

The 1,038 eligible opaque player/equipment sets are generated. Independent
decoding checks all 4,152 context PNG alpha planes and invisible RGB bytes
exactly; base-art review is in progress (35 contact sheets).
`private/player-remaster-pack-01/`, `private/player-alpha-check-01/`,
`private/player-review-sheets-01/manual-review.json`.
A further environment batch selects 1,086 opaque sets across explicit terrain,
building and prop families. Names suggesting signs, fonts, logos, lettering or
books are excluded from neural restoration; text-bearing UI uses original-only
scaling or existing vector replacements. Its 12,734 distinct inference jobs are
complete and verified in the local cache; pack assembly is in progress. Neither
bulk batch is installed yet. `private/environment-batch-cache-01/` and
`private/environment-remaster-pack-01/`.

Four text-free menu/title backgrounds have 16 independently checked context
outputs, all alpha/invisible-RGB exact. Their native title checkpoint exits 0,
loads 27 needed PNGs with no replacement errors, and displays the restored
background/clouds. `private/menu-art-remaster-pack-01/`,
`private/menu-art-alpha-check-01/`, `private/menu-art-native-title-02/`.
The first attempted checkpoint only reached the opening movie; it is retained
as `menu-art-native-title-01` and is not title-art acceptance evidence.

`tools/build-original-hd-pack.py` precomputes the pinned scaler for selected
text-bearing atlases. It performs no neural inference or translation, preserves
existing protected vector UI replacements, and supplies actual 4x PNGs for UI
bindings the runtime scaler leaves at native size. Its pixel check requires
**every RGBA byte**, not just alpha, to match a separately generated pinned
reference. The title/logo, COM_WIN and COM_NAVI candidate passes all 12 context
pixel checks and native title/main-menu checkpoints, with needed replacements
actually loaded and no replacement errors.
`private/title-ui-hd-pack-01/`, `private/title-ui-pixel-check-01/`,
`private/title-ui-native-title-01/`, `private/title-ui-native-menu-01/`.

### Existing English labels at 4x

`tools/build-hd-text-atlases.py` rerenders the **same 221 English regions in 91
atlases** from the existing pass-16 specs. It checks each spec hash, original
pixel hash, approved rectangles and current translated resource's target hash /
texture index. No new wording is translated. The two existing HD notices retain
their prior replacements. Windows Arial font-file hashes and the renderer source
hash are recorded privately. `render-texture-text.ps1 -PngOnly` avoids slow
PowerShell pixel export; its unchanged 1x output reproduces byte for byte.

All 364 generated contexts pass independent PNG checks: wording is unchanged and
every pixel outside the approved text rectangles equals the pinned 4x original.
Glyphs exceeding their approved masks are refused. Inside the masks, new
antialiased outlines intentionally change pixels. All four deduplicated label
contact sheets (96 distinct crops) were inspected, including the full trial
notice at native crop resolution.
`private/hd-english-label-pack-01/`, `private/hd-english-label-check-01/`,
`private/hd-english-label-region-sheets-01/`.

The combined player/label candidate contains 5,718 PNGs. Its native inventory
route exits 0, loads 142 needed PNGs versus the control's 140, uploads 32 mip
chains / 96 levels and records no rejection, decode/factor or upload errors.
Saves, 54 fonts and preferences stay unchanged.
`private/hd-inventory-control-01/`, `private/hd-inventory-candidate-04/`.

A further original-only UI batch adds 401 source atlas sets / 1,604 context
outputs. All decoded RGBA bytes exactly equal separately generated pinned xBRZ
references. Existing replacements are retained, including vector lettering and
restored artwork. The combined 6,318-image candidate's inventory checkpoint
exits 0, loads 164 needed PNGs and has no replacement/upload errors. Interactive
inspection has also reached the load screen, town, game menu, options and status
pages using copied saves. This is bounded menu review, not campaign acceptance.
`private/hd-original-ui-pack-02/`, `private/hd-original-ui-check-02/`,
`private/hd-ui-inventory-candidate-02/`, `private/hd-menu-live-04/`.

These candidates remain outside the normal toggle until combined review and
admission finish. Japanese audio, current ISO / message text and source saves
are unchanged. Existing English draft quality and untranslated video/art text
remain work for the later translation pass. All 151 source tests pass at this
point; the source-only index audit contains 190 UTF-8 files and two pinned
gitlinks, with no protected or binary payloads.

```powershell
./private/tools/python314/python.exe tools/build-hd-text-atlases.py --catalog private/remaster-coverage-06 --text-report private/translation/text-pass-16-archives/texture-text-report.json --base-pack private/title-ui-hd-pack-01/pack --output private/hd-labels-new
./private/tools/python314/python.exe tools/check-hd-text-atlases.py --batch private/hd-labels-new --catalog private/remaster-coverage-06 --text-report private/translation/text-pass-16-archives/texture-text-report.json --output private/hd-labels-check-new
```

```powershell
./private/tools/python314/python.exe tools/prefill-remaster-cache.py --catalog private/remaster-coverage-06 --neural-tool private/tools/realesrgan-20220424/package --output private/character-cache-new --cache private/remaster-inference-cache-01 --pattern '(NP|NPC|MS)[0-9].*' --offset 32 --limit 71
./private/tools/python314/python.exe tools/build-archive-remaster.py --catalog private/remaster-coverage-06 --base-pack private/character-remaster-pack-01/pack --neural-tool private/tools/realesrgan-20220424/package --output private/characters-new --cache private/remaster-inference-cache-01 --pattern '(NP|NPC|MS)[0-9].*' --offset 32 --limit 71
```

### Expanded world, character and alpha-preserving batch

The earlier expanded WIP pack is `private/hd-remaster-pack-02/`: 355 PNGs across
183 groups, comprising 86 world mip chains, 45 observed single-level 3D textures
and the original 52 English UI images. Of the 131 art groups, 92 use opaque
restoration, 21 restore RGB while retaining the pinned scaler's exact alpha,
and 18 retain the xBRZ fallback. This includes player/NPC bodies, faces, hair,
equipment, town buildings, sanctuary interiors, foliage and distant scenery.
The earlier pack folders below remain retained historical evidence.

Actual additional evidence:

- The read-only private observer captures 49 single-level 3D bindings / 45
  distinct keys. Every captured image matches decoded archive pixels exactly.
  `private/art-capture-sanctuary-01/archive-matches.json`.
- The expanded opaque pack passes native town and inner-sanctuary routes:
  `private/hd-expanded-town-01/`, `private/hd-expanded-sanctuary-01/`.
- The alpha-preserving pack also passes both routes:
  `private/hd-masked-town-01/`, `private/hd-masked-sanctuary-01/`. The latter
  uploads 82 mip chains / 246 levels, queues 81 replacement upload operations,
  loads 309 PNGs and records zero rejection/decode/skip/factor/upload failures.
- The independent PNG decoder checks all 49 changed images' complete alpha
  planes against the previous pack, exactly equal; 306 other PNGs are unchanged.
  `private/masked-alpha-check-01/result.json`.
- Five base-art contact sheets, the 21 changed masked-material previews and
  both actual native scenes were inspected. This is bounded visual review,
  not full campaign, exhaustive seam/LOD or sustained-performance certification.
- The binary-cutout-only pilot exercised zero eligible chains and is not
  counted as evidence of restored foliage. The admitted masked policy covers
  measured foliage and dense materials; unadmitted soft effects retain xBRZ.

This pack's admission used executable
`a89dd400004b10647bd3ed8f38bae19d932419ddb24a3ab7db2660531b91b1ab`.
The later sampler-aware integration above preserves its legacy pack behavior.
Source saves, fonts, preferences, game code and disc image are unchanged by
this texture-only update.

Manifest SHA256: `43b888d50041b584f20217bbee945b6e81df8a1f31bcb67d02974682abf62d4b`.
INI SHA256: `d6e6af48fc2184ba62e631598a701a8ea169273aa404f2eee02b6948acc32297`.

The builder can merge measured capture runs and exclude conflicting identities.
`--reuse-pack` checks exact source mip hashes, geometry, wrap, model pins and
restoration context before reusing PNGs; changed pixels or contexts are not
silently reused. `--art-capture` requires exact archive-pixel matches.

```powershell
./private/tools/python314/python.exe tools/build-mip-texture-pack.py --capture private/mip-capture-town-02/run --extra-capture private/campaign-temple-short-05/run --ui-pack private/hd-ui-expanded-pack-06 --output private/hd-expanded-new --limit 96 --reuse-pack private/neural-world-pack-05/pack --neural-tool private/tools/realesrgan-20220424/package --art-capture private/art-capture-sanctuary-01/run --catalog private/remaster-coverage-06 --restore-masked
./private/tools/python314/python.exe tools/check-pack-alpha.py --baseline private/neural-world-pack-05/pack --candidate private/hd-expanded-new/pack --output private/hd-alpha-new
```

### Admitted 32-chain batch

`private/hd-remaster-pack-01/` was selected by the existing saved HD toggle
for Vulkan/WIP English. It contains 26 locally restored opaque chains, six
transparent chains using the pinned xBRZ fallback, and the unchanged 52 UI
images: 148 PNGs, including 96 authored world-mip images. The Original preset
disables the pack. Japanese/v1.6 routing and existing save folders are unchanged.
The eight-chain pilot below remains historical evidence, not the default pack.

The expanded pack passed the native camera route before admission:
`private/neural-world-native-03/summary.json`, exit 0, 34 replacement upload
operations queued, zero rejected, 125 needed PNGs loaded, zero decode/skip/factor
failures and zero mip-upload failures. All 32 base images on two contact sheets
and the actual native scene were inspected. This is a bounded visual review,
not an exhaustive seam/LOD, FPS or campaign certification. Source saves, fonts,
preferences and pack contents remained unchanged.

Pack INI SHA256: `5eb5185551e1a07f1cab86b5f4ce459722d75c975f09a0677631ed52357da675`.
Manifest SHA256: `303e2fb95e47f8b60030cb19def94b946db04a117410d301b1a347a993c3b877`.
Reproduce the batch using the eight-chain command below with `--limit 32`, a
fresh output directory, and the same capture/UI/tool inputs. Normal pack
selection and the rebuilt menu passed their admission checks:
`private/hd-default-pack-native-01/summary.json` uses the new release and normal
saved-toggle selection, loads 125 PNGs, queues 34 replacement uploads and records
zero replacement/mip failures. The F1 persistence, High Quality preset and restart
into WIP English pass in `private/hd-default-pack-menu-01/result.json`. Both
checks exit 0 and preserve source saves, fonts, preferences and pack data.
All 131 source tests pass; both framework checkouts remain clean.

### Earlier eight-chain pilot

A separate local Real-ESRGAN pilot now restores seven opaque world chains at 4x
and retains pinned xBRZ on the eighth, which has transparency. The same 52 UI
images remain in the pack: 76 PNGs total. Every authored mip is processed
separately, with a 64-texel repeat/clamp context border followed by an exact crop.
Opaque alpha is verified unchanged. Transparency is refused by the restoration
helper rather than invented. This model can infer detail; visual review remains
necessary and this is not authored replacement art or complete game coverage.

The Windows 20220424 package is downloaded from the official
[Real-ESRGAN release](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.5.0).
`config/remaster-upscaler.json` pins the locally observed archive, executable,
runtime DLL and model hashes. This is a reproducibility pin, not an upstream
signature. Model weights, binaries, inputs and outputs remain private. Processing
uses local files only; no game image is sent to a service.

Actual checks:

- All 76 PNGs and the INI reproduce byte-for-byte in a second offline build.
  `private/neural-world-pack-repro-comparison-01.json`.
- The native camera route exits 0 with eight complete replacement chains queued,
  zero rejected chains, 53 PNGs loaded and no load/skip/factor/upload failures.
  The 58 world mip chains upload 174 levels. Source saves, fonts and preferences
  stay unchanged. `private/neural-world-native-01/summary.json`.
- The actual native scene was inspected. Broader materials, seam/LOD review,
  alpha restoration, sustained performance and campaign acceptance remain open.
- All 130 source checks pass, including repeat/clamp padding and alpha rejection.

The private pilot is `private/neural-world-pack-01/pack/`. Reproduce with fresh
output directories:

```powershell
powershell -NoProfile -File tools/fetch-remaster-upscaler.ps1
./private/tools/python314/python.exe tools/build-mip-texture-pack.py --capture private/mip-capture-town-02/run --ui-pack private/hd-ui-expanded-pack-06 --output private/neural-pack-new --neural-tool private/tools/realesrgan-20220424/package
./private/tools/python314/python.exe tools/check-hd-ui.py --output private/neural-native-new --pack private/neural-pack-new/pack --mip-textures --require-mip-replacements --texture-scale 4 --quality --padscript private/mip-camera-route-01.pad --frame-window 8200-8210 --seconds 120
```

## Archive-wide coverage and deduplication

`tools/catalog-remaster-textures.py` links a small private adapter to the pinned
runtime's actual hash functions. It inventories both alignment branches without
assuming a guest allocation address. Its keys are candidates until observed in
a real native capture. The scanner exports optional deduplicated RGBA data,
checks authored mips separately, and reports key aliases with conflicting
decoded images rather than silently choosing one.

Actual `private/remaster-coverage-03/result.json` results:

- 5,176 XET resource variants, 10,752 texture descriptors, 15,752 authored-level
  instances; 10,479 descriptors decode completely.
- 401 level instances are refused: 376 for small swizzle extents and 25 for
  palette bounds. Nothing is replaced with invented successful decoding.
- 8,590 candidate identity keys; no conflicting fully decoded key aliases found.
- 158 of 162 captured key/level pairs match decoded RGBA exactly. The remaining
  four pairs are refused small extents; there are zero decoded-pixel mismatches.
- The full preview preparation reduces 10,685 decodable base references to
  4,270 unique artwork previews. All references remain in the private inventory.
  The 143 generated review sheets are **not** all visually reviewed.

These are archive statistics, not full-game restoration or campaign passes.
Unseen materials still need restoration decisions, transparency/seam/LOD review
and in-game checks. See [campaign checkpoints](CAMPAIGN_VALIDATION.md).

### Padded-swizzle correction

The inspector now uses the pinned PSP sampler's padded subtiles for short rows
and mip levels. Synthetic tests verify distinct pixels in padded rows, truncated
data rejection and narrow-image span bounds. This changes only the read-only
asset inspector, not the game's renderer, binary or image.

The corrected decoder's final full audit (`private/remaster-coverage-06/`) matches all
162 captured key/level pairs, with zero decoded-pixel mismatches. It decodes
10,742 of 10,752 descriptors completely; 30 level instances remain refused for
palette bounds. Two small-texture key aliases resolve to conflicting decoded
chains and must be excluded from any archive-derived replacement pack until
disambiguated with runtime evidence. The current captured town pack is unaffected.

An additional diagnostic tried hashing the padded sampling span. That lost
three observed matches (`private/remaster-coverage-05/`) and was rejected. The
pinned `nk_texrepl_hash_texture` hashes logical contiguous bytes, while the
sampler reads padded tiles. The tool preserves this distinction. Do not treat
the failed diagnostic as accepted coverage evidence.

All 132 source tests pass after the padded-span regression was added. The
remaining palette failures and conflicting small keys are diagnostic gaps,
not permission to assume missing colours or install ambiguous replacements.
The refreshed review inventory (`private/remaster-review-06/`) now contains
10,742 decoded base references and 4,281 unique previews. Earlier catalog/sheet
counts above remain historical evidence. The latest previews are not all reviewed.

```powershell
./private/tools/python314/python.exe tools/catalog-remaster-textures.py --archives private/translation/text-pass-16-archives --capture private/mip-capture-town-02/run --export-rgba --output private/remaster-coverage-new
./private/tools/python314/python.exe tools/prepare-remaster-review.py --catalog private/remaster-coverage-new --output private/remaster-review-new
powershell -NoProfile -File tools/make-texture-review-sheets.ps1 -Inventory private/remaster-review-new -Output private/remaster-sheets-new
```

### Restoration work beyond the captured town

`tools/restore-archive-candidates.py` deduplicates complete opaque mip chains,
verifies exported source bytes and the local tool/model pins, and restores every
authored level independently at 4x. It writes review candidates without an INI
or pack manifest, so this output cannot be selected as a normal game pack.
The unseen materials' sampler modes are unknown: clamped context is an explicit
candidate-generation choice, not a claim about the game's sampler.

`private/archive-restoration-candidates-01/result.json` completes the first 32
of 1,121 eligible unique opaque chains in coverage catalog 03. The two base-art
review sheets were inspected: this includes skies, sanctuary surfaces, props
and boss atlases beyond the previous town batch. This does not establish native
sampling, seams, higher-mip visual quality or campaign acceptance for those
assets, and they remain uninstalled.

```powershell
./private/tools/python314/python.exe tools/restore-archive-candidates.py --catalog private/remaster-coverage-03 --neural-tool private/tools/realesrgan-20220424/package --output private/archive-candidates-new --offset 0 --limit 32
```

## Complete-chain pack update

The shortcut now selects **build 04** plus the private pilot pack
`private/mip-world-pack-01/pack/`. The pack contains eight world-material chains
at 4x (24 PNGs), plus the existing 52 UI PNGs: **76 images / 60 identities**.
Ground, stone paving, building surfaces, foliage and other captured atlas
content were inspected locally. This pilot precomputes the pinned xBRZ scaler
over original artwork. It does not add hand-authored detail.

The new path accepts a replacement only when every level the game needs exists,
decodes successfully and has the correct halved dimensions. All levels are
pinned while their data is copied, then queued as one ready chain. Replacement
factors may differ from runtime scaling; replacement-only operation also works
with xBRZ off. Incomplete, absent, corrupt or wrongly sized levels reject the
whole chain. Original art, optionally scaled by xBRZ, remains available rather
than mixing replacement level 0 with original lower levels.

Capture records use actual renderer texture identities, whole-chain content
hashes, decoded levels and wrap modes; no game allocation address is assumed.
The builder removes only the address portion of the measured pack key and
rejects aliases whose decoded contents or wrap modes differ. It excludes small
and unsupported thin-tail pilot candidates. Game-derived capture/PNG/raw data
remain under `private/`. INI mappings, each PNG hash, source dimensions, factors
and complete mip geometry are verified before use. The registered preview also
checks that the pack manifest matches its successful native test.

Build 04 SHA256:
`f7f44dfb8d79da349a0b682e962658e9834c13f68904657632d5ebaa2b194a29`.
Pilot INI SHA256:
`24fb7e9a2ef46b13d02466e912ec27f61e7c38e7c9c6604497131f0f9190f35d`.
Native pack manifest SHA256:
`fa9f9c49a48225a7fa0e72fdecf384d91d4c14fa9572da263fc206db63438cae`.

Actual additional evidence:

- **400 scaling comparisons + 400 ready-PNG round trips pass**, including
  narrow mip tails, alpha and all factors/wrap combinations.
- **Nine synthetic GPU cells pass at each of two scales.** The previous LOD,
  update and upload cells are joined by complete replacement, missing level,
  named-but-absent PNG, wrong-size PNG, corrupt PNG and pack-only cells. Bad
  chains demonstrably retain authored art at all tested LODs.
  `private/mip-replacement-gpu-02/result.json`.
- The bad base-only sampler is still detected at both scales:
  `private/mip-replacement-negative-01/result.json`.
- Native camera/movement route exits 0 with **8 replacement chains queued,
  zero chain rejections, 53 needed PNGs loaded, zero failed/skipped/bad-factor
  replacements, and zero mip-upload failures**. Total replacement bindings
  (UI and world together) are 93,746. All 58 scaled/ready chains upload 174
  levels; peak scaled GPU copies are 207 MiB, decoded pack cache 32 MiB.
  `private/mip-world-pack-native-01/summary.json`.
- Native source saves, all 54 recorded font files, normal preferences and the
  pack manifest remain unchanged. The first read-only capture run timed out
  at 60 host seconds (`mip-capture-town-01`). A fresh run with a recorded
  120-second diagnostic I/O allowance completed normally
  (`mip-capture-town-02`). The timeout remains a failed run, not a pass.
- Rebuilding the pilot reproduces **all 76 PNG hashes and the INI hash** exactly:
  `private/mip-world-pack-repro-01/`. All **127 source checks pass**.
- The launcher preflight accepts the registered build/pack and selects the
  existing separate preview save folder without writing normal preferences:
  `private/mip-world-preflight-01.json`.
- The updated interactive launcher also opens and closes normally with the
  pilot installed, using the existing preview save copy. Master saves and
  normal preferences remain unchanged:
  `private/mip-interactive-check-02/result.json`.
- The revised snapshot-first build is repeatable: build
  `private/mip-prototype-build-05-repro/` has the same executable SHA256 as
  build 04, passes both sets of 400 CPU checks, and leaves the normal exe
  unchanged. It is a build reproducibility check; the shortcut stays on the
  registered build 04.

The pack's `[games]` key identifies NPJH50503 for the native disc check. The
framework emits its existing note that per-game INI override values are not
applied; this pack uses the global hash table and relies on no override file.
The needed images demonstrably load and complete replacement chains queue.

New builds snapshot their extension sources before compilation. Existing
validated build 02's exact sources were preserved and hash-checked too, so
editing the working sources no longer invalidates that immutable executable.
The normal executable and pinned framework checkout remain unchanged.

Build a pilot from a successful private capture with:

```powershell
./private/tools/python314/python.exe tools/check-hd-ui.py --output private/mip-capture-new --probe private/mip-build-new/mip-prototype.exe --mip-textures --capture-mips --hd-ui --texture-scale 4 --quality --padscript private/mip-camera-route-01.pad --frame-window 8200-8210 --seconds 120
./private/tools/python314/python.exe tools/build-mip-texture-pack.py --capture private/mip-capture-new/run --ui-pack private/hd-ui-expanded-pack-06 --output private/mip-pack-new --factor 4 --limit 8
./private/tools/python314/python.exe tools/check-hd-ui.py --output private/mip-pack-native-new --probe private/mip-build-new/mip-prototype.exe --mip-textures --pack private/mip-pack-new/pack --require-mip-replacements --texture-scale 4 --quality --padscript private/mip-camera-route-01.pad --frame-window 8200-8210 --seconds 120
```

The input route is the existing measured private controller fixture. Add
`--pack private/mip-pack-new/pack` when registering the preview to bind it to
the exact successfully tested pack. The combined pilot replaces UI as well as
world textures; disabling its HD pack disables those replacements together.

## What changed

The pinned renderer originally limits scaling and texture replacement to
single-level textures. The title-owned experiment scales each original mip
independently, retaining its artwork, level count and sampler state. A padded
atlas lets the existing bounded worker queue process one whole chain per job.
Two-texel borders isolate each level, including wrap/clamp behavior. GPU uploads
write separate mip subresources in bands, with the original constant, automatic
and slope LOD selection. Whole-chain hashes, palette keys, content generations,
target-overlap exclusions and original-image fallback remain active.

Original images stay resident. An unfinished or stale copy cannot bind; a
changed higher mip or palette draws original current content until its new
chain is ready. Worker submission uses the packed chain's actual dimensions.
GPU accounting includes every mip. The existing 512 MiB copy budget and
per-present upload cap remain in force. Scaling can smooth existing artwork;
it cannot restore missing authored detail or increase polygon counts.

No upstream checkout is modified. `mip_runtime_patch.py` accepts only the pinned
`ge_gpu.c` SHA256
`926bec6a0e7b6622ab70d67c7703c1898c62f1a0fb0f296f065cd65843be80ab`,
and generates a modified copy under `private/`. The separate link substitutes
one private renderer object. Game code, PSP calls, measured base/entry and
Japanese audio remain unchanged. The framework stays at
`8704fba98007fff6d6f930365f2b2142af1bfbba`.

Normal executable SHA256 remains
`3b1d62c043475b2d244ace8d7c840309ed02d4b17d1fdea3e4eca194482b293c`.
Prototype build 02 is
`3bde9d9fb5e1c78c448fdf86350f4341a5e129ae58ecd9f3f3e6339efaaf86bb`.
Its build manifest fingerprints the generated source and all four extension
sources, including the synthetic GPU tests.

## Preview storage

The preview requires release/Vulkan/WIP English and verifies the executable,
source fingerprints and matching successful CPU, positive/negative GPU and
native checkpoint evidence before launch. Missing or changed evidence fails
explicitly. It uses the normal absolute project-font directory, avoiding the
earlier relocated-executable missing-font issue.

On its first interactive launch, it copies current WIP saves into
`private/memstick/hd-remaster-preview/` while holding the source's existing
writer lock. Source and copied file hashes must match. Existing preview
progress is never overwritten by reseeding. Preview saves are **separate from
normal progress** and are not copied back automatically. Its F1 preferences
live in the private prototype build folder. Normal preferences stay unchanged.
F1 restarts into WIP retain the experiment; choosing another language returns
to that language's normal executable/save namespace.

## Actual evidence

- **400 CPU comparisons pass:** each padded-atlas result exactly matches an
  independently scaled mip, across factors 2–6, alpha, repeat/clamp combinations
  and thin textures. Build 02's `selftest.log` records the result.
- **Synthetic Vulkan checks pass** at render scale 1 / texture factor 2 and
  render scale 4 / texture factor 4. Direct RGBA8888, indexed CLUT8 and large
  256x256 chains retain levels 0/1/2; constant/automatic/slope LOD select the
  right colors. Higher-level rewrites and palette changes use current original
  content while workers are held, then the correct new copy. Large chains
  exercise uploads above one staging band.
  Evidence: `private/mip-gpu-check-04/result.json`.
- **Negative control passes:** a deliberately base-only sampler causes the
  expected level-selection failure at both scales. The test detects the wrong
  green mip showing the red base level.
  Evidence: `private/mip-gpu-mutant-02/result.json`.
- **Town checkpoint, VBLANK 5500–5510:** final build exits 0 with 32 chains,
  96 mip levels uploaded, 28,519 scaled-mip bindings and zero mip-upload
  failures. All 29 needed HD UI images load without replacement errors.
  `private/mip-town-native-02/summary.json`.
- **Camera/movement checkpoint, VBLANK 8200–8210:** left/right camera input and
  two analog movement segments reach a different town viewpoint. Exit 0;
  58 chains, 174 levels, 92,082 mip bindings, zero mip-upload failures, 207 MiB
  peak scaled-copy use and zero budget shortages. Three queue-full events use
  the original fallback. Screenshot inspected, including character, buildings,
  ground, foliage and sea. `private/mip-camera-native-01/summary.json`.
- Source saves, all 54 recorded project-font files and normal preferences stay
  unchanged in both native routes. These routes use copied fixtures.
- **Interactive launcher smoke passes:** the real registered preview opens
  with copied WIP saves and absolute fonts, displays the English caution, and
  exits 0 after a normal close of its owned window. Normal saves/preferences
  remain unchanged. `private/mip-interactive-check-01/result.json`.
- All **119 source checks pass**, including source-pin refusal, repeatable
  private source generation and preview save/path isolation.
- **Disabled-mode control passes:** five matching direct GPU captures at
  VBLANKs 991, 993, 995, 997 and 999 are byte-identical between normal and
  prototype-off builds. Prototype mip counters stay zero; both exit 0.
  `private/mip-off-frame-comparison-01.json`, `mip-off-reference-01/` and
  `mip-off-prototype-01/`. This is a static checkpoint comparison, not a
  campaign-wide equivalence claim.

The first GPU harness build failed because the relocated source lacked an
include search path. This was fixed in its private recipe. An expanded test
then exceeded the legitimate per-present upload cap by asking several large
chains to become ready in one synthetic present. The test now advances
synthetic presents as the pinned upload-cap test does; the renderer cap was
not removed. Failed results remain in `mip-gpu-check-01` and `-03`.

These checks do not establish campaign-wide appearance, combat correctness,
sustained gameplay FPS, every alpha/LOD combination or new PPSSPP trace
equivalence. Enhanced frames intentionally change. This section records earlier
isolated checks; see the normal release integration above for current behavior.

## Reproduce locally

Use fresh private output directories; these contain all generated/derived data:

```powershell
./private/tools/python314/python.exe tools/build-mip-prototype.py --output private/mip-build-new
./private/tools/python314/python.exe tools/check-mip-gpu.py --output private/mip-gpu-new
./private/tools/python314/python.exe tools/check-mip-gpu.py --output private/mip-negative-new --mutant-base-only
./private/tools/python314/python.exe tools/check-hd-ui.py --output private/mip-town-new --probe private/mip-build-new/mip-prototype.exe --mip-textures --hd-ui --texture-scale 4 --quality --padscript private/translation/work/text-pass-01-route.pad --frame-window 5500-5510
./private/tools/python314/python.exe tools/mip_preview.py --build private/mip-build-new --gpu private/mip-gpu-new/result.json --negative private/mip-negative-new/result.json --native private/mip-town-new/summary.json
./private/tools/python314/python.exe tools/launch-preview.py --variant english-text-test --mip-preview private/mip-build-new --check
```

Remove `--check` from the last command for an interactive isolated preview.
The existing shortcut selects the already-built and registered build 04 and
the complete-chain pilot pack described above.

## Remaining remaster work

The upstream renderer skips mipmapped replacement packs; the title-owned
release extension now supports complete-chain replacements. Broader locations,
combat, texture streaming, seam/alpha review, additional UI font styles and
longer performance checks remain, as do higher-detail authored replacements
beyond the admitted batches above. Translation is paused for the HD pass.
