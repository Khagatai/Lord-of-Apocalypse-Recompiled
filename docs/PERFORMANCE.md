# Runtime performance changes

The beta.7 candidate adds two output-preserving host optimizations. The pinned
framework checkout remains unchanged; the native build generates private source
copies and verifies their original hashes before applying either change.

## Texture lookup indices

The renderer remembers texture-array indices in a 4 KiB table. A hit must match
the full texture key and every byte of the mip key. A moved, removed or reused
slot that fails validation falls back to the original complete search. Texture
content hashes, byte shadows, palette identity, dirty notifications, replacement
selection, pixel uploads and eviction behaviour still run as before. Entries
remain unique by the exact key/mip pair because creation follows a complete
search and existing pairs update in place.

A bounded native route recorded 404,201 searches and 65,702,757 comparisons with
the original lookup. Cached selection recorded 372,711 direct hits, 32,138
searches and 5,946,178 comparisons: approximately 91% fewer comparisons. The
routes close at slightly different final vblank counts. Overall FPS improvement
has not been established; these are lookup-work measurements.

For diagnosis, `LOA_TEXTURE_LOOKUP=linear` selects the original search;
`LOA_TEXTURE_LOOKUP=cached` is the default. Defining
`LOA_TEXTURE_LOOKUP_VERIFY=1` compares each cached selection with the original
search and aborts explicitly if the indices disagree. These are developer
controls, not graphics-quality settings. Normal exit logs lookup counters.
`SR_GPU_CPU_PROFILE=1` additionally logs aggregate renderer phase counters.
Hard `_Exit` diagnostic paths may skip these normal-shutdown reports.

## Routine scheduler logging

Only the unconditional `DEBUG_SLEEP` and `DEBUG_WAKEUP` prints are now gated by
`SR_WAKELOG`, matching the existing callback-sleep diagnostic switch. Define
`SR_WAKELOG=1` before launch to restore them. Clock, scheduling priorities,
wakeup counts, guest register/state changes and error returns are unchanged.
Fatal errors and useful startup/performance diagnostics remain enabled.

On the tested route the log shrank from 767,000 to 83,197 bytes, approximately
89%, with 11,722 routine sleep/wakeup lines removed.

## Validation

446 title regressions pass, including the pinned native scheduler suite with
logging both off and on, mutation tests against the original texture search,
and explicit refusal of unknown source identities. Real Vulkan authored-mip
checks pass at 1x and 4x, including sampler namespaces, replacement uploads and
cache switches. All 13 captured frames match the pre-change native build byte
for byte across the original-search, cached and verification runs. Original
saves and the flat guest image remain unchanged. A further 30-FPS native route
with the existing real HD pack completes with every cached hit checked against
the original search, actual replacement hits and mip binds, and no reported
lookup divergence. HD inference was not repeated. Evidence stays local under
`private/performance-review/`.

These checks do not establish full campaign, physical-controller, audio-quality
or 60-FPS co-op stability. The multiplayer loading crash remains unresolved.
HD pixel-processing recipes and models are unchanged: verified existing texture
jobs can be reused when the native runtime updates. No HD inference is required
because of these runtime optimizations.
