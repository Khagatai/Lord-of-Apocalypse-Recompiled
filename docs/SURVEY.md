# NPJH50503 intake

This records initial input analysis and the first framework's limitations.
The active backend has since changed to Nakagawa; see
[framework evaluation](FRAMEWORK_EVALUATION.md) for measured improvements.

Observed from the user-supplied unmodified ISO on 2026-11-13. The original
image was opened read-only and was not changed. This is an exact local input
pin, not independent authentication against a preservation database.

## Disc

- `DISC_ID`: `NPJH50503` (`UMD_DATA.BIN`: `NPJH-50503`).
- `DISC_VERSION`: `1.01`; `APP_VER`: `01.00`; title: `LORD of APOCALYPSE`.
- Region: Japan image designation; SFO `REGION`: `32768`.
- Required PSP system version: `6.60`.
- Size: `1068498944` bytes; 308 filesystem files in the ISO9660 survey.
- SHA-1: `e7809b45b8044aef33081a6c39ed9f1cff755eeb`.
- SHA-256: `3a4d63713880dfb67ade00b6a912ac4975847cec06b1ab341b65963f328e1c93`.

## Module and support-file inventory

All paths below are relative to `PSP_GAME/`. Update payloads are inventoried
separately from game runtime modules; they have not been executed.

| Path | Bytes | SHA-1 | Observed format |
|---|---:|---|---|
| `SYSDIR/EBOOT.BIN` | 6293072 | `e2d5ab63ff25253b24ee9bac4138daf68965af07` | Encrypted `~PSP`, tag D91613F0 |
| `SYSDIR/BOOT.BIN` | 6292725 | `4008798e19e92cbb053b3b42116c7f76ab7b773c` | Entirely zero-filled |
| `SYSDIR/OPNSSMP.BIN` | 880 | `5fdaae055b65fc92ed9e90ed1167a5542abc2798` | `~PSP` header; not decrypted |
| `SYSDIR/UPDATE/EBOOT.BIN` | 5718512 | `d04fbcc6a94240a268b68e8016d2594efc6c365f` | `~PSP` header; not decrypted |
| `SYSDIR/UPDATE/DATA.BIN` | 26876352 | `515b4a379307a48174602ecece55e1f6b195b1eb` | Unclassified update payload |
| `USRDIR/UPDATA/MODULE/LIBFONT.PRX` | 20736 | `4577f580720d2a239defab390bd26b9fdb1088cb` | `~SCE` 64-byte wrapper, encrypted `~PSP`, tag 457B06F0 |

The ISO file tree exposes one `.PRX`. This does not exclude modules or overlays
inside archives or code loaded without a `.PRX` suffix.

Decryption with pinned pspdecrypt's type-2 implementation succeeded locally:

| Plaintext module | Bytes | SHA-1 | SHA-256 |
|---|---:|---|---|
| EBOOT / `SQEX01` | 6292725 | `e4bc2601c7ffb6cee292e8bd9b302f63e6bef863` | `e2199a4797680f5956f357757bf9987c592f1ea002001a7a9557a36ecf51fb5f` |
| LIBFONT / `sceFont_Library` | 35302 | `02fe0271ee235a7b0cdfc0cb2ea69b30bed5221b` | `c0edf06ff6ec56d2824b3fe87ed53758df741fc339c783d4085e630a874e4ffc` |

Original and plaintext modules remain ignored under `private/`.

## EBOOT structure and imports

ELF32 MIPS `ET_SCE_PRX` (`0xffa0`), module `SQEX01`, version 1.1, attributes 0.
There are 62 section headers but the 1183-byte section-name string table is
entirely zero-filled. Module info is found via the first program header's
`p_paddr` file offset `0x004b85c8`, not a named section.

ELF entry offset: `0x003e196c`. Load segments cover relative ranges
`[0, 0x004f3cfc)` and `[0x004f3d00, 0x005a0149)`. Segment flags are 7 and 6;
the module extent reported by PPSSPP is `0x005a0200` bytes.

135579 type-A relocation entries occur in ten sections, also covered by the
`0x700000a0` program segment (1084632 bytes). Count them once:

| Type | Count |
|---|---:|
| R_MIPS_32 (2) | 20111 |
| R_MIPS_26 (4) | 92144 |
| R_MIPS_HI16 (5) | 10537 |
| R_MIPS_LO16 (6) | 12787 |

275 function-import stubs across 30 libraries were parsed from module info.
The diagnostic parser used relative base zero only to inspect offsets. It did
not choose the runtime base. Exact NIDs and relative stub locations are in
ignored `private/eboot-survey.json`.

| Library | Function imports | Library | Function imports |
|---|---:|---|---:|
| sceLibFont | 9 | sceUmdUser | 5 |
| scePower | 3 | sceNetAdhocMatching | 12 |
| sceNetAdhoc | 13 | sceNetAdhocctl | 13 |
| sceNetAdhocDiscover | 4 | sceNet | 3 |
| sceUtility | 21 | sceWlanDrv | 2 |
| sceDisplay | 8 | sceAudio | 13 |
| sceCcc | 3 | sceMpeg | 25 |
| sceRtc | 1 | sceImpose | 1 |
| InterruptManager | 3 | IoFileMgrForUser | 16 |
| Kernel_Library | 8 | LoadExecForUser | 2 |
| ModuleMgrForUser | 7 | StdioForUser | 3 |
| SysMemUserForUser | 6 | ThreadManForUser | 36 |
| UtilsForUser | 4 | sceSuspendForUser | 3 |
| sceCtrl | 3 | sceGe_user | 8 |
| sceSasCore | 27 | sceAtrac3plus | 13 |

An import appearing in this list does not establish runtime HLE support.

## LIBFONT

Sectionless ELF32 MIPS PRX, attributes 6, version 1.1. Its ELF entry is
`0xffffffff`; do not use that as a callable module entry. It has a 1958-byte
type-B relocation stream (`PT 0x700000a1`). The pinned offline tools do not
support this sectionless/type-B combination.

PPSSPP's separate `--re-module` loader successfully resolved 28 function exports
in `sceLibFont` and 11 function imports: six from `sceReg` and five from
`IoFileMgrForUser`. Its report and NID listing remain in
`private/libfont-oracle/`. That tool's chosen standalone address is not evidence
for the address of LIBFONT during game execution. This operation executes no
module instructions.

## Dynamic loading, archives and writable content

The main ELF contains the exact LIBFONT disc path and imports
`sceKernelLoadModule`, `sceKernelStartModule`, and `sceKernelUnloadModule`.
The native scheduler diagnostic now reaches load/start and actual recompiled
font exports with explicit guest linking; see STATUS.md. PPSSPP runtime
load/start/unload, matching placement and overlay reuse remain unmeasured.

The executable also contains `disc0:/sce_lbn0x%X_size0x%X` format strings and a
`/PSP/SAVEDATA/NPJH50503GAMEDATA/REGFILE.RZP` path. These are static candidates,
not proof that a particular file operation or save route has executed.

Archives: `USRDIR/UPDATA/REGFILE.RZL` (374784 bytes), corresponding `REGFILE.RZP`
(263157760 bytes), and `INSDIR/REGFILE.RZP` (267269744 bytes). Their contents and
physical-record semantics remain unclassified. Runtime overlays, reused address
ranges, DLC and installation behavior remain unknown.

## Measured PPSSPP boot state

PPSSPP source revision `1aebad2c651ff9d0684ee335e43aceff8fc7e3ec`, MSVC x64
Release headless build, interpreter CPU, software renderer, function replacements
disabled, isolated memstick. Raw snapshots and 16 debugger steps are private.

| Field | Observed value |
|---|---|
| Main base | `0x08804000` |
| Native entry PC | `0x08be596c` |
| GP | `0` |
| Root thread UID | `0x113` |
| Priority | `0x20` |
| Stack allocation size / base | `0x400` / `0x09fffc00` |
| Initial SP | `0x09fffe90` |
| Initial RA | `0x08000030` |
| Argument / byte count | `disc0:/PSP_GAME/SYSDIR/EBOOT.BIN` plus NUL / 33 |
| Argument pointer | `0x09fffed0` |

The oracle log explicitly selected HLE sceFont because firmware fonts were
absent. This is part of the captured oracle configuration; it does not prove
the on-disc LIBFONT ran. Thread attributes, next UID counter, initial GE list
counter, and a complete memory-write/patch comparison still require direct
evidence. Native standalone boot remains gated on those measurements.
