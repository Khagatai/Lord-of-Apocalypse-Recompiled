# PSP Recompilation Title Intake

Copy this checklist into the new title repository and complete it with measured
evidence.

## Identity

- Title: Lord of Apocalypse
- Region: Japan designation; SFO REGION 32768
- Disc ID: NPJH50503
- Version: disc 1.01; app 01.00
- ISO byte size: 1068498944
- ISO SHA-1: e7809b45b8044aef33081a6c39ed9f1cff755eeb
- Runtime repository/commit: https://github.com/Jstar269/Nakagawa-Recomp / 8704fba98007fff6d6f930365f2b2142af1bfbba
- PPSSPP revision/settings: 1aebad2c651ff9d0684ee335e43aceff8fc7e3ec; interpreter/software; config/oracle.ini

## Executables

| Path | Plaintext/encrypted | Size | SHA-1 | Role |
|---|---|---:|---|---|
| `PSP_GAME/SYSDIR/EBOOT.BIN` | Encrypted ~PSP | 6293072 | e2d5ab63ff25253b24ee9bac4138daf68965af07 | Actual boot executable |
| `PSP_GAME/SYSDIR/BOOT.BIN` | Entirely zero-filled | 6292725 | 4008798e19e92cbb053b3b42116c7f76ab7b773c | Cannot supply code |
| Main PRX (decrypted EBOOT) | Plain ELF | 6292725 | e4bc2601c7ffb6cee292e8bd9b302f63e6bef863 | SQEX01 |

## Main module

- Module name: SQEX01
- Base: 0x08804000 (PPSSPP debugger measurement)
- Entry: 0x08be596c (ELF relative 0x003e196c plus measured base)
- GP: 0
- Text/image size: relocated image 0x005a0149; reported module extent 0x005a0200
- Argument bytes/length: disc0:/PSP_GAME/SYSDIR/EBOOT.BIN plus NUL; 33 bytes
- Start thread UID: 0x113
- Next UID:
- Priority: 0x20
- Stack size: 0x400
- Attributes:
- Initial GE list ID:
- Explicit computed entries:
- Reviewed catalog matches:
- Normalized matches awaiting review:
- Private codegen cache location: private/native-build/lordofapocalypse/

## Dynamic modules

- Module roots: PSP_GAME/USRDIR/UPDATA/MODULE/
- Plaintext PRX count: two locally decrypted execution inputs, main and LIBFONT
- Encrypted PRX count: LIBFONT.PRX plus encrypted EBOOT; updater/support inventory in SURVEY.md
- Overlay address reuse: unmeasured; archives not decoded
- Raw-LBN paths: strings and native diagnostic opens observed; oracle I/O not matched
- Import/export private libraries: main 275 function imports in 30 libraries; LIBFONT 11 imports / 28 exports

| Exact module identity | Load path/hash | Initial policy | Evidence |
|---|---|---|---|
| sceFont_Library | LIBFONT.PRX, plaintext SHA-256 c0edf06ff6ec56d2824b3fe87ed53758df741fc339c783d4085e630a874e4ffc | Runtime-placed recompiled exports; no callable start entry | Native diagnostic only; PPSSPP lifecycle pending |

## Content and storage

- Main asset archives:
- Duplicate-record semantics:
- DLC/install data:
- Writable devices and aliases:
- Save identifiers/formats:
- User-supplied external content:

## First deterministic routes

| Route | Input script | Expected checkpoint | Evidence |
|---|---|---|---|
| Boot | Neutral | | |
| Front end | | | |
| New game | | | |
| Save/load | | | |
| Movie/audio | | | |
| Vertical slice | | | |

## Initial unknowns

The unmodified dump is now surveyed. See SURVEY.md for hashes, encryption,
imports, relocations, topology and measured boot fields. Thread attributes,
next UID, initial GE list ID, PPSSPP runtime module lifecycle and overlays remain unmeasured.
The earlier English-patched image was never used for this intake.

- Unsupported instructions:
- Missing imports/HLE:
- Unresolved indirect targets:
- Unsupported module formats/relocations:
- Graphics differences:
- Audio/video differences:
- Filesystem/save differences:

## Evidence boundary

- [x] Game-derived files are ignored.
- [x] Exact hashes are tracked.
- [ ] Reduced reports are safe to publish.
- [x] Findings use stable identifiers.
- [ ] Shared candidates have a planned synthetic test.
