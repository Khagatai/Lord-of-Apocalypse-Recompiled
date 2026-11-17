# V1.0 release gates

## Packaging

- Include the dynamically loaded SDL3_ttf library and its entire dependency
  closure, public UI fonts and licence notices. A static PE-import scan alone
  missed this dependency in the first tester ZIP.
- Require the launcher's menu-library/font preflight to pass.
- Exercise F1 and Escape from an extracted package on a machine/environment
  without developer tools. A dark overlay without menu content is a failure.
  The user confirms the dependency repair makes the tester's menu work.
- Verify settings/networking/tester-support pages, resume and clean exit from
  the packaged build, rather than relying on the development checkout.
- Exclude original images, saves and personal preferences. Public distribution
  still needs the separate game-derived-content/licence review and local-input
  generation workflow discussed with the user; the current local tester ZIP
  is not approved for public upload.

## Open text-layout regressions reported by the user

- Character creation: source correction captured; confirm readability at the
  tester's chosen resolution. Shared settings/results labels also need field review.
- Item descriptions: all 6,077 shared table entries audited; 2,116 descriptions
  reflowed or shortened, with no over-budget descriptions remaining. Native
  inventory panels checked at 30/60. Still inspect the actual crafting/help
  panels and representative late-game equipment during normal play; the data
  audit does not replace that visual review. Turnslash is also corrected.
- Startup caution: body bounded and reviewed in a PPSSPP software reference.
- Story movies: 327 fitted plates reviewed; actual opening timing checked at
  30 and 60. Later campaign playback remains a separate acceptance gate.
- Both distribution deltas were regenerated against the current WIP image and
  independently decoded/hash-verified. The packager now refuses stale proofs.
  Existing earlier ZIPs remain unchanged; use the newly prepared beta candidate.

Retain original font style, colour and size where practical. Use shorter text
and measured line breaks before shrinking. Require actual affected-screen
captures; translated-string coverage does not establish layout correctness.

## Gameplay acceptance

Use [the separate 30/60 multiplayer matrix](MULTIPLAYER_ACCEPTANCE.md). Both modes
must pass game-room creation/join, shared quests, synchronization, rewards and
save/reload. A connected Steam lobby or matching callback alone is insufficient.

Campaign progression, save/exit/reload, boss/movie audio, long-run performance
and shared multiplayer missions remain separate acceptance gates. Lobby
membership, a compiled executable and startup checks do not establish these.
