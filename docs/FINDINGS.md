# Findings

Current backend selection and loader validation are recorded in LOA-F-005.
LOA-F-001 through LOA-F-004 retain the initial framework/oracle observations.

## LOA-F-001 — Encrypted EBOOT; zero-filled BOOT

**Status:** Confirmed for the pinned image.
**Inputs:** ISO SHA-1 e7809b45b8044aef33081a6c39ed9f1cff755eeb; framework
b56ff30ef5997b9f168209df8c33156e82402e7b; pspdecrypt
c156627db7634d395c380c0a9589130f603307fc.
**Observation:** EBOOT decrypts to SQEX01; BOOT has 6292725 zero bytes. LIBFONT's
64-byte SCE wrapper contains an encrypted module that decrypts locally.
**Evidence:** Survey/decrypt commands and [numeric report](SURVEY.md).
**Interpretation:** BOOT cannot supply instructions; PPSSPP boots EBOOT.
**Impact:** Title identity configuration.
**Validation:** Exact-input rejection and repeat module hashes.

## LOA-F-002 — Offline analysis silently emits an empty inventory

**Status:** Confirmed.
**Inputs:** Main ELF SHA-1 e4bc2601c7ffb6cee292e8bd9b302f63e6bef863; same framework.
**Observation:** 62 section headers, entirely zero-filled section-name table.
Module info is available through p_paddr. Unmodified analyze.py exits 0 with no
functions; imports.py cannot find .rodata.sceModuleInfo.
**Evidence:** private/unpatched-analysis.toml and eboot-survey.json;
title generate.py rejects the inventory with exit 1.
**Interpretation:** Named-section assumptions prevent translation.
**Impact:** Generic parser candidate and strict title gate.
**Validation:** Future fixes require synthetic stripped-name/named-section
regressions, shared tests and affected-title build/trace evidence. No framework
fix or runtime pin update is included yet.

## LOA-F-003 — Boot contract partially measured

**Status:** Partial.
**Inputs:** Same disc/module, PPSSPP 1aebad2c651ff9d0684ee335e43aceff8fc7e3ec,
MSVC x64 Release, interpreter, software, oracle.ini and isolated memstick.
**Observation:** Base 0x08804000, entry 0x08be596c, GP 0, root UID 0x113,
priority 0x20, stack 0x400; exact argument and 16 debugger steps captured.
PPSSPP selected HLE font behavior because firmware fonts were absent.
**Evidence:** private/oracle initial-state.json, debugger-steps.json and log.
**Interpretation:** These values inform config; they do not prove native execution.
**Impact:** Title boot contract and diagnostics.
**Validation:** Repeat oracle sampling, measure thread attributes, UID/GE
counters and memory deltas, then compare native traces.

## LOA-F-004 — Sectionless font uses type-B relocations

**Status:** Confirmed structure; runtime lifecycle unknown.
**Inputs:** Font ELF SHA-1 02fe0271ee235a7b0cdfc0cb2ea69b30bed5221b; same pins.
**Observation:** No sections, 1958-byte type-B relocation stream. Offline Elf
raises IndexError. PPSSPP's standalone loader resolves 11 imports and 28 exports
without executing instructions.
**Evidence:** private/libfont-survey.json and private/libfont-oracle/.
**Interpretation:** Exact-identity policy requires real HLE or actual loader support.
The separate loader report does not establish game runtime behavior.
**Impact:** Title module policy and possible generic loader work.
**Validation:** Trace load/start/unload and font/menu checkpoints; reject
unsupported loading explicitly.

## LOA-F-005 — Nakagawa selected after exact-input comparison

**Status:** Confirmed for loading and generation; execution gates separate.
**Inputs:** Same ISO/main/font hashes; Nakagawa
8704fba98007fff6d6f930365f2b2142af1bfbba; same pinned PPSSPP interpreter.
**Observation:** The selected loader resolves 275 main imports and 11 font
imports, supporting stripped names and sectionless/type-B metadata. All
5,898,569 main image bytes match the oracle except bytes in 275 individually
verified syscall patch words. Zero other differences. Main and runtime-placed
font generate with an empty fallback report.
**Evidence:** FRAMEWORK_EVALUATION.md and private/evaluation numeric reports;
tools/compare-loaded-image.py, tools/title.py generate.
**Interpretation:** This removes the initial static-analysis blocker without
editing the dump or disabling strict failure behavior. It proves no graphics,
scheduler or gameplay milestone.
**Impact:** Active framework pin, source-only title manifest and build wrappers.
**Validation:** Preserve exact-image comparison and loader regressions, then
compare the bounded native entry trace, full function and scheduler route.

## LOA-F-006 — Import tracing repaired; bounded prefix matches

**Status:** Prefix passed; full function and host-return behavior unresolved.
**Inputs:** Same exact game/module/oracle identities; active Nakagawa pin.
**Observation:** Initial native trace step 13 reused the preceding delay-slot
snapshot because the upstream import emitter called sr_end without sr_begin.
A title-owned, hash-pinned CODEGEN_TOOL adapter adds paired JR/syscall trace
boundaries while preserving syscall dispatch and LLE failure propagation.
The regenerated AMD64 executable matches all 14 pre-syscall instructions,
register deltas and actual SW values with zero divergences.
**Evidence:** private/native-prefix-before-trace-fix/ and
private/native-prefix/; tools/import_trace_codegen.py and three synthetic tests.
**Interpretation:** This is trace instrumentation evidence, not HLE validation.
The direct route also records AOT_RETURN_TARGET_MISMATCH after the compared
prefix; it is unresolved, and process termination is not a successful exit.
**Impact:** Repeatable native prefix command and diagnostic build flags.
**Validation:** 11 title checks passed; complete a full function and its return
contract before claiming CPU or boot correctness beyond the bounded prefix.

## LOA-F-007 — Guest font linking reached; boot remains unvalidated

**Status:** Native diagnostic observation; no matched scheduler or frame gate.
**Inputs:** Same pins, verified ISO and plaintext modules, isolated memstick,
TRACE build with runtime -O1 and generated code -O0.
**Observation:** Missing SR_MODULE_DIR originally caused a real refusal. With
the directory supplied, default uppercase LIBFONT path handling left host HLE
in control. Explicit SR_REAL_MODULE_START=1 uses the existing guest linking
route: the library declares no start routine, and recompiled font creation,
info, glyph, close and cleanup exports subsequently execute. No ELF entry is
invented. The 30-second headless probe logs one display-buffer flip, raw-LBN
opens, sleep/wakeup activity and a spin warning; later reads continue. The
harness terminates the child at its deadline. Several HLE calls are unverified.
**Evidence:** private/diagnostic-boot-modules/, private/diagnostic-boot-guest-link/,
private/diagnostic-boot-io/ and private/diagnostic-boot-30s/. Latest result records
executable SHA-256 51706bfa48c045cec0a389e00e3faa7da37eff515e9cea104dfce0bd0a46651a.
**Interpretation:** The spin warning alone establishes no deadlock. A flip
establishes no correct displayed image. Substitute fonts, runtime placement,
module/async-I/O results and scheduler state are not compared against PPSSPP.
The native root UID 0x110 already differs from the oracle's 0x113.
**Impact:** Strictly diagnostic launcher; no unsupported-call success shim.
**Validation:** Measure and reproduce the full boot contract, then match a
function, scheduler/module/I/O route and rendered frame before later milestones.

## LOA-F-008 — User test reproduced; first syscall checkpoint differs

**Status:** Register mismatch reproduced; cause not yet confirmed by a targeted probe.
**Inputs:** Same exact ISO, native executable SHA-256 and pinned PPSSPP binary.
**Observation:** The user's private/test-20261113-221429/ run reaches guest font
exports, raw-LBN reads and SAS pause handlers before the harness's 30-second
termination. It establishes no frame/menu pass and no proven crash/deadlock.
A fresh 96-step PPSSPP sample reaches the first thread creation and root
return. After the first syscall at 0x08cbbcfc, PPSSPP keeps r4=0x06030510 and
r5=0x09fffed0; the native trace writes 0xdeadbeef to both. Other GPR/HILO
checkpoint values agree. The first 14 instruction register states still agree.
**Evidence:** private/oracle-entry-96/, private/first-syscall-checkpoint.json;
tools/compare-first-syscall.py exits 1 for the actual difference. This is a
single GPR/HILO checkpoint check, not a normalized full syscall/CPU comparison.
**Interpretation:** PPSSPP's __KernelLoadExec implementation calls hleSkipDeadbeef
after boot setup; hleFinishSyscall skips register poisoning while that pending
flag is set. This suggests inherited reference startup state rather than a
property of this one SDK-version NID. Targeted confirmation is still needed.
The sample also contains an idle-thread detour after CreateThread, so simply
aligning later records by instruction index would be invalid.
**Impact:** Extends the diagnostic boundary without changing game/runtime code.
**Validation:** Measure inherited boot flags and scheduler state; reject a
title-specific register restoration or fake success as an unexplained workaround.

## LOA-F-009 — Native images captured; experimental window launcher added

**Status:** Real CPU-presenter images observed, no synchronized visual/input pass.
**Inputs:** Same pinned ISO/framework/native/oracle executable identities.
**Observation:** A private offscreen capture emitted an initial black frame and
then stopped with an explicit missing assets/vfpu lookup table message and exit
0xc0000409. The title environment now supplies an absolute PSP_VFPU_TABLES
path; the existing runtime table length/hash checks remain enabled. Repeats
capture loading, warning, media-check and no-save-data screens. The latest
native no-save prompt is recognizable in the PPSSPP software references, with
different fonts/timing. No rendered picture, RAM dump or preview PNG enters Git.
**Evidence:** private/native-offscreen-frames/ (failed),
private/native-offscreen-tables/, private/native-offscreen-later/ and
private/oracle-boot-images/. Nine oracle software images were captured before
its emulated-time bound. Native runs ended at their 30-second harness bound.
**Interpretation:** The earlier no-window probes could not establish missing
graphics. Offscreen pixels demonstrate progress, not actual-window correctness.
Headless default START pulses were present, so do not label them neutral input.
**Impact:** tools/title.py now resolves VFPU tables independently of working
directory. Start-Preview.cmd and tools/launch-preview.py provide an experimental
GDI window, explicit manual controls, disabled automatic input and isolated logs
and memstick. Their input/module/AMD64 preflight passed; interactive execution
has not yet been tested.
**Validation:** Align deterministic input and frame timing against PPSSPP,
measure image differences, then validate real-window input, audio and gameplay.

## LOA-F-010 — Explicit pad route reaches the publisher logo

**Status:** Bounded native/oracle progression observed; broad input/playability open.
**Observation:** With automatic pad pulses disabled, Up at native VBLANK 1050
and Circle at 1080 advance to the media-check-completed dialog. Circle at 1320
advances to the Square Enix logo. Native ctrl_latch logs contain the scheduled
transitions. PPSSPP presses at 17.5, 18 and 22 emulated seconds reach the same
screens. Font output and logo fade brightness differ; no image pass is claimed.
**Evidence:** private/native-scripted-confirm/, private/native-scripted-next/,
private/oracle-scripted-confirm-fixed/ and private/oracle-scripted-next/.
Native input table hashes and disabled automatic input are recorded in result.json.
**Interpretation:** This establishes progression for one explicit input route,
not keyboard/controller correctness, exact timings, title menu or gameplay.
Native runs end at the harness deadline. Oracle runs end at the emulated bound.
**Impact:** Diagnostic launcher accepts an explicit pad script and records its
hash. Oracle capture accepts a press schedule and forwards the supported --press
option. The rejected initial --press-script attempt remains retained as failure.
**Validation:** Eleven title checks and preview hash/AMD64 preflight pass.
Continue with synchronized deterministic input/frames, actual-window controls,
title menu, audio, gameplay and save/load as separate gates.

## LOA-F-011 — Low-FPS report; software GE dominates boot workload

**Status:** Optimized/GPU previews available; gameplay speed and GPU fidelity open.
**Observation:** User reports the visible preview works but is slow. Its log
records GDI/software, WASAPI initialization and ordinary exit 0. A separate
TRACE=0/-O2 build succeeds. Runtime at 1,000 deterministic VBLANKs is 23.091 s
diagnostic/software, 22.175 s release/software and 7.105 s release/GPU.
Software frames match exactly; the GPU save-prompt frame has 13,706 differing
pixels. Software GE costs 20.475 s of the release/software run.
**Evidence:** PERFORMANCE.md and its private runs. The first 1,500-VBLANK
comparison timed out and was rejected. A GPU input route reaches the Access
Games logo and exits 0 at the explicit 1800-VBLANK diagnostic boundary.
Release executable SHA-256 b2572a0b8dfce0527ecb5fd5b747311f1b0a0ac19cbd1ec6c67fe8aa698ca19a.
**Impact:** Preview defaults to optimized/Vulkan GPU with a software fallback.
No fast-math, skipped game instructions, frame skipping or fake PSP success.
**Validation:** Actual-scene FPS, synchronized GPU/software/PPSSPP graphics,
input, audio, gameplay and save/load remain separate checks.

## LOA-F-012 — Existing English patch integrated; remaining text not translated

**Status:** Bounded English preview verified, full translation still open.
**Inputs:** User v1.6 patch SHA-256 4f344ff39ccfea127272b32bbdf17844fdb0e1013bb2e9b40f1f3fa1c07c2ae7;
Japanese disc and framework/oracle pins unchanged. Exact decoder and output hashes
are in TRANSLATION.md and config/lordofapocalypse.toml.
**Observation:** Normal xdelta decode succeeds, preserves the source hash and
changes only the two UPDATA archive contents. 307 file records have changed
extent/placement metadata. Both native/GPU and PPSSPP software reach the English
no-save prompt. Six strict archive parser regressions pass; all 9807 groups per
variant decompress and validate size sums, yielding 18055 distinct IDs and 22263
descriptors. Only 16 IDs change payloads, all .MES bundles. Aliases are preserved.
**Evidence:** private/translation/v1.6/, native-v16-1000/, oracle-v16/ and
archive-inventory-aligned/. Three synthetic disc-identity regressions ensure
English selection does not weaken the exact Japanese gate. Total 20 checks pass.
**Interpretation:** Resource changes are not a completion percentage. The
custom glyph/control encoding must be decoded before safe message-level editing;
the package has no editable text sources or repacker. No new text is translated.
**Impact:** Separate English preview launcher and exact variant configuration;
no executable/codegen/shared runtime changes, game-data commits or uploads.
**Validation:** Decode messages/glyph mapping, prove lossless text round trips,
inventory untranslated content and validate translations in game context.

## LOA-F-013 — Per-run save isolation hid intact tutorial progress

**Status:** Tutorial recovery and initial auto-load confirmed; broad save testing open.
**Observation:** The user's Japanese tutorial save existed in an earlier preview
memstick; later previews used empty directories. DATA.BIN, PARAM.SFO and ICON0.PNG
were independently backed up and copied into persistent Japanese storage, with
source and destination hashes verified. No save was deleted or overwritten.
The launcher now reuses per-language memsticks across runs/renderers/builds.
An exclusive byte-range lock prevents simultaneous writers of one namespace.
**Evidence:** SAVE_STORAGE.md, private/save-backups/, tutorial-save-load-check/
and tutorial-save-oracle/. Native and PPSSPP images both display successful
auto-load of the recovered save. Test sources remain unchanged.
**Interpretation:** The missing startup progress was caused by launcher storage
selection. The observed auto-load does not establish the exact resumed character
state or another save–exit–reload cycle. English compatibility is not inferred.
**Validation:** Four save-storage regressions pass; total suite 24 checks.
