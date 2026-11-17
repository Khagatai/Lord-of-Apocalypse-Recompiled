# Framework boundary

Active framework: Jstar269/Nakagawa-Recomp,
8704fba98007fff6d6f930365f2b2142af1bfbba (unmodified source).
The prior Tzeentchnet/psp-recomp pin
b56ff30ef5997b9f168209df8c33156e82402e7b remains for historical reproduction.

The user authorized framework evaluation and selection. See
FRAMEWORK_EVALUATION.md for title-specific tests and why Nakagawa was selected.
No upstream issue, message, commit, PR, push, release or publication was made.

Title addresses, identities, guest module policy and diagnostic routes live
in this project. Any future shared source changes need synthetic regressions
and an explicit patch/revision record. No proprietary game data may be sent
to an upstream tracker or CI service.

The F1 settings extension is title-owned host code in `tools/in-game-settings.c`,
linked by `tools/overlay-settings.mk` using GNU ld wrappers for the Settings page
and its redraw timer. No upstream file or gitlink is changed. Local executable
identity changes and is recorded with extension-source hashes in the build's
private `host-ui-build.json`. Guest instructions, loading and PSP calls are
unmodified. Settings persistence/restart tests use synthetic requests and copied
save fixtures; game-derived captures remain private.
