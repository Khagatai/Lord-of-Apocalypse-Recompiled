# Complete archive texture identity coverage — 2026-11-15

The active in-place pack is `private/hd-remaster-pack/`: 28,189 unique PNGs,
34,071 identity/context groups and 12,706 complete-mip groups. Manifest SHA256:
`e69f5f92d52c8ba122b35d30cb74a9718824bebb375a9eb4ad4b6912b7c5c661`.
No full pack or ISO copy was made for this pass. Japanese audio is unchanged.

The strict audit of corrected catalog 08 covers all 10,713 non-portrait
descriptors across all four sampler wraps and every eligible alignment identity.
The remaining 39 descriptors are deliberately original dialogue illustrations.
There are zero unmatched, partial or unresolved catalog identities. Counts include
aliases and potentially unused artwork; they are not campaign completion counts.

This is complete coverage of the scanned archive texture identities, not a claim
that every scene has been played or every image was rebuilt with a neural model.
The pack combines reviewed neural restoration with faithful 4x original-art
scaling. UI lettering, maps and effects use the faithful scaler where restoration
could alter their meaning or transparency. Model textures are upgraded; meshes,
animation, lighting and cinematics are not rebuilt into new high-polygon assets.
Procedural or runtime-generated imagery is outside the static archive audit.
Existing Japanese image text remains for the separate translation pass.

## Identity fixes

Address 0/1 in catalog hashing denotes alignment classes, not measured guest
load addresses. A zero source quick-hash is admitted only through the verified
sampler namespace: XOR with its nonzero wrap tag produces an exact nonzero INI
key. No raw zero/wildcard identity is emitted. Default neural selection still
refuses zero hashes unless explicitly enabled by a suitable caller.

The reported conflicting white 8x8 identities have identical overlapping RGBA
pixels and dimensions, but one source has one authored level and the other has
three. The builder selects the longest chain only when all overlapping levels
match exactly. The pinned reader already consumes the requested level prefix.
Actual differing pixels or dimensions remain conflicts. Alias extension reuses
only an identical source chain and wrap, without copying PNGs or overwriting
existing replacements. Existing canonical fallbacks are preserved when completing
missing sampler variants.

`tools/check-source-aliases.py` builds the pinned native pack reader against
synthetic, locally generated pixels. All four namespaced zero-source identities,
one/three-level reads and the unrelated-hash negative control pass. This check
does not exercise a GPU draw or establish correctness for every possible hash.
Evidence: `private/source-alias-reader-check/`.

## Generation and validation

| Batch | New source sets | Outputs checked | Result |
|---|---:|---:|---|
| Remaining material restoration | 23 | 244 context/mip images | Exact alpha and invisible RGB |
| Missing sampler restoration | 17 | 148 context/mip images | Exact alpha and invisible RGB |
| Remaining faithful original art | 462 | 3,617 context/mip images | Every RGBA byte matches pinned scaler |
| Exact aliases | — | 50 added groups | Zero PNG copies or writes |

All 17 source contact sheets (500 distinct base previews), both neural result
sheets and all 16 faithful result sheets (460 distinct base previews) were
visually inspected. This does not inspect every mip/context separately in game.
The independent checks decode every output level. Reports retain each batch's
then-current manifest, so earlier stage hashes intentionally differ from the
final manifest above. New files deduplicate against existing payloads.

Private evidence: `hd-final-art-work/`, `hd-final-art-check/`,
`hd-final-context-work/`, `hd-final-context-check/`, `hd-final-faithful-work/`,
`hd-final-faithful-check/`, `hd-final-aliases/`, `hd-full-coverage-strict/`
and the manual contact-sheet record `hd-full-review.json`.

Current-pack native checkpoints all exit 0, preserve source saves, fonts,
preferences and pack metadata, and report zero texture failures, rejected mip
chains or interpreter instructions/entries/dispatch misses:

| Checkpoint | Replacements loaded | Authored mip uploads / levels |
|---|---:|---:|
| Town | 247 | 58 / 174 |
| Sanctuary dialogue | 345 | 82 / 246 |
| Inventory | 169 | 32 / 96 |

All queued authored chains use replacement art. All 162 town source mip captures
match catalog 08. That capture does not establish use of the new sky textures or
a matching PPSSPP campaign trace. Evidence: `private/hd-full-native-*/` and
`hd-full-native-town/capture-comparison.json`. Normal launcher preflight passes in
`private/hd-full-preflight.json`. The source suite passes 179 tests.

The later 1,188-second copied-save exploration loads 377 replacements and uploads
97 replacement mip chains / 291 levels with zero texture/interpreter failures.
It displays the exchange UI and town dialogue, then saves the QA copy, returns
to title and loads that copy back into town within the same process. Four
unsupported ad-hoc cleanup errors remain recorded. No combat mission is
completed. See the campaign document for the exact scope and screenshots.

## Reproduction and acceptance

Use the generation, independent checks and bounded native checkpoint commands in
[HD renderer work](HD_REMASTER.md). `build-archive-remaster.py --complete-contexts`
explicitly fills only missing tagged sampler keys. `build-original-hd-pack.py`
fills remaining eligible sizes and contexts while retaining installed artwork.
`extend-remaster-aliases.py` updates metadata only. Run
`audit-hd-coverage.py --help` for strict audit arguments. Follow the
[storage policy](STORAGE.md); retain compact reports instead of full pack copies.

Restart through **Start-Game.cmd** to use the updated default pack. Full campaign
visual acceptance, combat/boss coverage and sustained performance remain open;
see [campaign evidence](CAMPAIGN_VALIDATION.md). No new matching PPSSPP campaign
trace or performance acceptance is claimed by these image/checkpoint results.
