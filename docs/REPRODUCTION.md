# Reproduction with the selected framework

All commands below run from the title project root. No private evidence or
game input is sent to an external service. Root private/ contains dependencies,
game modules, generated C, binaries and raw captures; none belongs in Git.

## Dependencies

Initialize pinned source submodules with `git submodule update --init`.
The active source is external/nakagawa-recomp at
8704fba98007fff6d6f930365f2b2142af1bfbba.

Download the official portable Python archive:
https://www.python.org/ftp/python/3.14.0/python-3.14.0-embed-amd64.zip.
Verify SHA-256
`8d4d3590c10449d78aa4375f534e6d5f3027d67fdc362dd1a882279db6f90fdf`
and extract it into private/tools/python314. No pip packages are needed for
these title commands.

```powershell
./private/tools/python314/python.exe tools/install-toolchain.py --mirror accum
```

The installer uses the active framework's pinned compiler, Make, SDL3 and Vulkan
package metadata. The primary MSYS2 server did not resolve in this environment,
so the working mirror route uses the official Accum mirror and its two observed
HTTPS nodes. Every upstream package size/hash remains unchanged. Python is
supplied separately at a supported version; the framework's bundled-Python
artifact is not downloaded. Packages and retained license notices stay local.
No global PATH or system installation is changed.

For initial module decryption, clone John-K/pspdecrypt into
private/tools/pspdecrypt and check out
c156627db7634d395c380c0a9589130f603307fc. With Visual Studio 2022 C++ Build Tools:

```powershell
./tools/build-decryptor.ps1
./private/tools/python314/python.exe tools/survey-disc.py '../Lord of Apocalypse (Japan).iso'
./private/tools/python314/python.exe tools/decrypt-module.py private/disc/PSP_GAME/SYSDIR/EBOOT.BIN private/modules/EBOOT.elf
./private/tools/python314/python.exe tools/decrypt-module.py private/disc/PSP_GAME/USRDIR/UPDATA/MODULE/LIBFONT.PRX private/modules/LIBFONT.elf
```

The survey validates exact size/SHA-1/SHA-256 and disc metadata before extraction.
Generation/build additionally verify the exact plaintext module hashes.

## Generate and build

```powershell
./private/tools/python314/python.exe tools/title.py generate
./private/tools/python314/python.exe tools/title.py build --jobs 4
```

These wrap the pinned upstream Makefile with explicit measured base/entry,
profile none, public runtime backends, TRACE=1, runtime -O1, generated code -O0,
500 functions per chunk
and a 2,000,000-byte chunk budget. LIBFONT is generated for runtime placement;
no address is guessed and no HST/game-specific overrides are enabled.

The title-owned tools/import_trace_codegen.py adapter adds paired instruction
trace boundaries to upstream import stubs. Its hash is pinned in the TOML.
Upstream source and actual syscall/failure behavior remain unchanged; no
generated game C is edited by hand.

All outputs and logs go to private/native-build/lordofapocalypse/. The build
checks the executable's PE machine field for AMD64. Generation rejects a
nonempty fallback report. Neither check establishes runtime correctness.

Windows sandbox execution of the newly unpacked compiler/Make was denied;
approved execution outside that sandbox was needed in this session. Normal
user-level use does not require changing the installed system toolchain.

## Pinned PPSSPP oracle

Clone hrydgard/ppsspp into private/tools/ppsspp and check out
1aebad2c651ff9d0684ee335e43aceff8fc7e3ec, then initialize its dependencies:

```powershell
git -C private/tools/ppsspp -c core.longpaths=true submodule update --init --recursive
./tools/build-oracle.ps1
./private/tools/python314/python.exe tools/capture-oracle.py '../Lord of Apocalypse (Japan).iso' --steps 1 --output private/oracle-image --dump-main-image
./private/tools/python314/python.exe tools/compare-loaded-image.py
./private/tools/python314/python.exe tools/capture-oracle.py '../Lord of Apocalypse (Japan).iso' --steps 16 --output private/oracle-prefix --record-prefix-stores
./private/tools/python314/python.exe tools/entry-trace.py private/oracle-prefix
./private/tools/python314/python.exe tools/native-prefix.py
```

Captures require fresh output directories/memsticks. Archive old runs locally.
The oracle runs interpreter/software mode with config/oracle.ini, disabled
function replacements and its executable hash recorded. Its version-generation
script warned that Git was unavailable; the embedded version string is not
accepted as provenance.

The loaded-image comparison requires every byte outside the 275 verified
syscall patch words to match. The prefix comparison checks 14 instructions,
register deltas and actual observed SW memory values, ending before the first
syscall. It refuses instruction classes outside that reviewed integer prefix.
The native child is terminated at the diagnostic checkpoint. This is not a
complete function, HLE, scheduler or standalone boot pass.

## Bounded scheduler investigation

```powershell
./private/tools/python314/python.exe tools/diagnostic-boot.py '../Lord of Apocalypse (Japan).iso' --output private/diagnostic-boot-new --io-log --seconds 30
```

Use a fresh private output directory each time. This verifies the ISO/modules,
supplies the module directory, isolates the memstick and records the native
executable hash. SR_REAL_MODULE_START=1 requests real guest linking: this font
library declares no start routine, and its exports then run recompiled code.
The run is headless, bounded to 1..30 seconds and always reports NOT_VALIDATED
for boot while the measured initial-state contract is incomplete. Child
termination after the deadline is recorded; it is not a PSP exit or pass.
I/O logs and display-flip messages alone prove no correct rendered frame.

For the current first-syscall investigation, after the validated native prefix
and associated private/diagnostic-boot-30s evidence exist:

```powershell
./private/tools/python314/python.exe tools/capture-oracle.py '../Lord of Apocalypse (Japan).iso' --steps 96 --output private/oracle-entry-96 --record-prefix-stores
./private/tools/python314/python.exe tools/compare-first-syscall.py
```

The comparison currently exits 1, recording an r4/r5 difference in
private/first-syscall-checkpoint.json. It checks only the first syscall's
GPR/HILO state; it establishes no syscall-memory, opcode, timing or scheduler
equivalence. PPSSPP's pending startup register-poisoning policy needs investigation.

## Frame diagnostics and experimental window

```powershell
./private/tools/python314/python.exe tools/diagnostic-boot.py '../Lord of Apocalypse (Japan).iso' --output private/native-frames-new --seconds 30 --offscreen-frames --frame-window 1-1800
./private/tools/python314/python.exe tools/capture-oracle-frames.py '../Lord of Apocalypse (Japan).iso' --output private/oracle-images-new
./private/tools/python314/python.exe tools/launch-preview.py --check
```

The native frame command uses the CPU offscreen presenter and writes P6 PPMs
every 30 VBLANKs inside the requested range. Its working directory is private;
PSP_VFPU_TABLES points explicitly to the pinned framework's validated assets.
These diagnostics do not claim a visible window or headless presentation pass.
The current wrapper disables automatic START pulses. Without --pad-script it
supplies neutral scripted input. Earlier captures documented in STATUS.md used
the legacy default pulses; none are identical-clock acceptance captures.

The oracle command uses the pinned interpreter/software executable, isolated
memstick and existing oracle.ini. It requests nine images at emulated times
0.5, 1, 2, 3, 5, 8, 12, 18 and 24 seconds, ending at 25 emulated/30 wall seconds.
Its exit code is recorded without being interpreted as a title pass. These
reference times are not aligned to native VBLANK indices or its initial state.

Double-click **Start-Preview.cmd**, or run tools/launch-preview.py, to open an
experimental Windows Vulkan GPU preview using the release build. It verifies the original ISO and modules,
disables automatic input and writes native.log/result.json to a fresh retained
private/preview-* directory. Arrows are D-pad; Z Circle; X Cross; Enter Start;
Escape closes. Saves persist across launches in private/memstick/japanese/ or
private/memstick/english-v16/, independently of renderer/build profile. English
and Japanese saves remain separate. A single-writer lock prevents concurrent
preview instances using the same save namespace. This launcher has passed
preflight; the recovered tutorial save auto-loads in native and PPSSPP tests.
Broader input, audio, gameplay and save/load correctness remain under validation.
See SAVE_STORAGE.md for the verified backup and copy-only migration procedure.

Release build commands and the measured boot comparison are in PERFORMANCE.md.
Start-Software-Preview.cmd selects the GDI/software fallback. Explicit
--profile diagnostic --renderer gdi selects the preserved trace build. Preview
performance reports stay private; GPU rendering needs broader visual/gameplay
validation.

The bounded script tested after the save prompt is a legacy pad table containing
`1050 UP 4`, `1080 CIRCLE 4` and `1320 CIRCLE 4`, one per line. Pass it with
--pad-script PATH to diagnostic-boot.py and capture --frame-window 900-1800.
The oracle counterpart is --press-script
'17.5:0x10:0.15,18:0x2000:0.15,22:0x2000:0.15' on capture-oracle-frames.py;
the wrapper forwards this to PPSSPP's --press option. Native widths are four
guest frames; oracle widths are 0.15 emulated seconds, so these are equivalent
intended actions, not an exact timing/duration match. Both reach the logo.

## Checks and remaining gates

```powershell
./private/tools/python314/python.exe -m unittest discover -s tests -p 'test_*.py' -v
git diff --check
git diff --cached --check
git ls-files --stage
./private/tools/python314/python.exe tools/audit-source.py
```

Nakagawa's focused tests are tools.test_prxload_relocations,
tools.test_prx_reloc_model, tools.test_elf_bounds and
tools.test_prx_loader_cleanroom. Run with the private UCRT64 bin directory
on the process PATH, from the framework root using supported Python.
The compiler-backed run passed 113 tests, including the parser mutation test.

Do not accept isolated compile success as boot/playability. Complete root
thread attributes, UID/GE state and boot writes, compare a full native function
and scheduler route, then validate first frame, menu, input, audio, gameplay and
save/load individually with deterministic scripts and software references.
