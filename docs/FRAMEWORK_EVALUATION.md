# Framework selection for NPJH50503

Decision: use **Nakagawa Recomp**, pinned to
`8704fba98007fff6d6f930365f2b2142af1bfbba`. This is the best fit of the four
framework revisions evaluated against this exact dump, not a universal ranking.
No framework's marketing or other game's playability was accepted as title proof.

The input remains ISO SHA-1 `e7809b45b8044aef33081a6c39ed9f1cff755eeb` and
main ELF SHA-256 `e2199a4797680f5956f357757bf9987c592f1ea002001a7a9557a36ecf51fb5f`.
The measured base/entry stay `0x08804000` / `0x08be596c`.

| Framework | Revision | EBOOT result | Sectionless LIBFONT result |
|---|---|---|---|
| Tzeentchnet/psp-recomp | b56ff30ef5997b9f168209df8c33156e82402e7b | 0 discovered functions; missing module info/import table | Offline parser IndexError; unsupported type-B |
| jessicanataliagta/PSPRecomp | f6e7d415c7f447b934cc3865a31eb725f353d659 | Relocations applied; module null and 0 imports | 0 relocations, 0 functions, 0 imports |
| TeamGDB/Yakumo | 0a506b81af44f4c70a3a197e81795891f5567968 | Relocations applied; module null and 0 imports | 0 relocations, 0 functions, 0 imports |
| Jstar269/Nakagawa-Recomp | 8704fba98007fff6d6f930365f2b2142af1bfbba | Entry matches oracle; 275 imports; nonempty discovered code | Type-B loading; 11 imports; nonempty discovered code |

The two C++ candidates returned exit 0 despite missing module metadata/imports.
Their large function counts therefore do not constitute a viable title build.
Both also rebase LIBFONT's `0xffffffff` entry sentinel to `0x08803fff`; that value
must never be used as a real callable entry. The title uses runtime library
placement and exports, without inventing a LIBFONT start address.

## Independent loader comparison

At the real main entry, a fresh PPSSPP interpreter session captured the full
5,898,569-byte main image before execution. Nakagawa's image applied all
135,579 type-A relocations and matched every byte outside the explicitly
identified 275 import-stub syscall words. The only 752 differing bytes were
inside those words, where PPSSPP installs its own HLE syscall encodings.
No other mismatch was ignored. This validates that main load/relocation boundary;
it does not validate execution, scheduler, graphics or gameplay.

PPSSPP source: `1aebad2c651ff9d0684ee335e43aceff8fc7e3ec` with the existing
interpreter/software configuration. Private evidence:
`private/oracle-image/`, `private/evaluation/nakagawa-image-comparison.json`.

## Tests and limitations

- PSPRecomp: Windows/MSVC core/tools build and 1/1 CTest target passed.
- Yakumo: Windows/MSVC core/tools build and 3/3 CTest targets passed.
- Nakagawa: 113 focused loader/relocation/bounds tests passed under Python 3.14
  with GCC available, including a 10,000-mutation parser fuzz test.
- Main plus runtime-placed LIBFONT generated 111 primary chunks with an empty
  fallback report. The generator reports 1,244,921 owned words translated and
  zero interpreter words. These are static reports, not proof of dynamic coverage.
- No commercial title corpus from another project was used, downloaded as game
  input or redistributed. Other titles' gameplay/release tests were not run.

Initial C++ CTest runs overlapped a shared temporary fixture directory; those
results were discarded and each suite was run separately. The first Nakagawa
test run lacked a compiler and skipped checks; the supported compiler-backed
run above supersedes it. Sandbox execution denials were resolved using approved
local-tool execution, rather than treating skipped or denied checks as passes.

Raw reports, traces, generated game code and native binaries remain private.
The earlier framework gitlink remains for historical reproduction; it is no
longer the active title backend. Shared source is unmodified.

## Import-trace defect found by native execution

The initial executable linked as an AMD64 Windows PE. The first 14-instruction
comparison failed at step 13: the default upstream import emitter has sr_end
without sr_begin, reusing the prior delay-slot snapshot. The failed run is
preserved in private/native-prefix-before-trace-fix/.

The title-owned CODEGEN_TOOL adapter tools/import_trace_codegen.py adds trace
boundaries for the import JR and syscall word, preserving the original syscall
call and LLE failure propagation. It reads live instruction words for tracing;
it changes no guest instruction effect or game input. Its SHA-256 is pinned in
config/lordofapocalypse.toml. Three synthetic regressions verify the defect,
paired boundaries and preserved failure flow. Upstream source remains unchanged.
This fixes tracing, not any scheduler or host-return contract.

The diagnostic generated-code optimization level is now -O0 (runtime remains
-O1), reducing repeated trace-build cost without unsafe floating-point flags.
The changed generation/compiler profiles invalidate prior objects normally.

The regenerated/rebuilt executable passed all 14 entry-prefix steps with zero
register or observed memory-write divergences. The direct diagnostic also logs
AOT_RETURN_TARGET_MISMATCH after the compared prefix; this is unresolved and
the prefix result does not establish a complete function or host-return pass.

Scheduler diagnostics initially omitted SR_MODULE_DIR and correctly received
a missing-input refusal. Supplying it placed the exact font image. The default
case-sensitive libfont path policy treated the uppercase path as host-served;
the title launcher now explicitly requests SR_REAL_MODULE_START=1. This library
has no start routine; actual recompiled sceFont exports were subsequently
called, without guessing an entry or synthesizing readiness. Oracle module
lifecycle, font output and scheduler correctness remain separate open gates.
