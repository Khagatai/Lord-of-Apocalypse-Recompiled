# Ordered gates

1. Inspect the local image read-only. Record byte size, SHA-1/SHA-256,
   PARAM.SFO disc ID/version and region evidence. Inventory files and modules,
   including EBOOT.BIN versus BOOT.BIN and nested archive candidates.
2. Hash every executable. Identify plaintext/encrypted formats. With lawful
   local decryption where needed, inspect imports/exports, relocations, ELF
   entry, GP, segment bounds and module metadata. Record unavailable fields
   explicitly; encrypted headers cannot establish plaintext import coverage.
3. Pin a trace-capable PPSSPP revision and interpreter/software-renderer
   settings. Measure actual load base, entry, stack, GP, arguments, thread/UID
   and GE state. Trace module load/start/unload and reused address ranges;
   a static PRX list alone cannot establish absence of overlays.
4. Add exact-identity rejection before extraction/generation. Establish
   title-owned generation/build commands with explicit addresses and strict
   runtime dispatch. Analyze translation traps before claiming coverage.
5. Match one function then bounded scheduler boot traces. Fix the first
   observed divergence with evidence and appropriate regression coverage.
6. Validate first displayed frame, menu, input, audio, gameplay, then save/load
   as independent milestones. Pin pad scripts, presentation indices, measured
   thresholds and isolated memstick fixtures before declaring passes.
7. Expand to stage completion, media, soak and release matrix. Audit protected
   content and reproduce from a clean recursive clone before distribution.

Unsupported behavior must produce a diagnostic or real PSP error. Never use
fake success, permissive dispatch or broad module replacement to pass a gate.
