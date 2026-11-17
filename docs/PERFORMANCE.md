# Performance investigation

The user reported that the visible preview works but has low FPS. The examined
preview log records GDI with software GE rendering, SDL3 WASAPI audio initialization
and an ordinary exit code 0. This is a manual report, not a repeatable gameplay or
save/load pass. The diagnostic executable uses TRACE=1, generated code -O0 and
runtime -O1; those settings prioritize tracing and rebuild speed.

An independent release profile uses TRACE=0, generated code -O2 and runtime -O2.
It preserves the original diagnostic outputs, strict failures, input identities,
module policy, compiler floating-point defaults and software renderer. No fast-math,
instruction skipping, frame skipping or compatibility success shims are enabled.

```powershell
./private/tools/python314/python.exe tools/title.py generate --profile release
./private/tools/python314/python.exe tools/title.py build --profile release --jobs 4
```

Outputs stay under private/native-release/lordofapocalypse/. The launcher supports
--profile diagnostic and --profile release; its private result records the selected
profile and exact executable hash. Performance JSON is enabled for interactive
previews. The diagnostic launcher additionally supports --perf, recording private
per-frame CSV data. Completed-build and runtime results belong in STATUS.md;
these commands alone assert no speed improvement.

Compare the same route and renderer with automatic input disabled. Distinguish
host presents, guest flips and elapsed VBLANKs; a held boot dialog is not a gameplay
FPS benchmark. Confirm matching checkpoints against PPSSPP before accepting an
optimization. GPU rendering remains experimental and needs broader visual/gameplay checks.

## Measured results

Sequential deterministic tests, no automatic input, hidden/offscreen presenters:

| Build / renderer | Runtime to 1,000 VBLANKs |
|---|---:|
| Diagnostic / software | 23.091 seconds |
| Release / software | 22.175 seconds |
| Release / Vulkan GPU | 7.105 seconds |

The two software runs capture identical P6 frames at VBLANK 990. The GPU image
shows the same no-save prompt, but 13,706 of 130,560 pixels differ; no exact
visual-match gate is claimed. Software GE accounts for 20.475 seconds of the
release/software run. All runs exit at the explicit diagnostic boundary with
zero interpreter entries. This is one boot workload, not gameplay FPS.
The earlier 1,500-VBLANK comparison exceeded 30 seconds and was rejected.

Evidence: private/boot-profile-comparison-1000/ and private/release-gpu-1000/.
A further GPU input route to VBLANK 1800 reaches the Access Games logo and
exits 0; private/release-gpu-scripted-next/ retains captures and input records.

Start-Preview.cmd now selects release + Vulkan GPU by default.
Start-Software-Preview.cmd selects release + GDI/software if the GPU path has a
visual issue. The original trace build remains available through
tools/launch-preview.py --profile diagnostic --renderer gdi. Every interactive
preview writes perf.json on a normal exit and records its build/renderer/hash.
