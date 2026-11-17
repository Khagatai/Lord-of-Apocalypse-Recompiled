# Controller camera mapping

F1 or Escape opens the host pause menu; choose Settings for graphics, display,
advanced effects, language and presets. Arrows navigate, Left/Right or Enter
changes choices, and Escape goes back. Choices save automatically. Startup-only
changes require a confirmed restart; save progress first. `Start-Game.cmd` opens
the game directly, defaulting to WIP English. See [graphics](GRAPHICS.md).

On compact keyboards, F1 may require Fn. Escape also opens the menu. A darkened
frozen frame without menu text means the pause input was accepted; check the run
log for `SR_PAUSE: the overlay pages are unavailable`. The first tester package
omitted dynamically loaded SDL3_ttf and its dependencies. Apply the menu-fix ZIP
or use the corrected full package. The launcher now checks the library and UI
fonts before starting. Do not change PSP control bindings to address this symptom.

The Vulkan preview uses config/controller-camera.json through the existing
NK_INPUT_PROFILE loader. Both Japanese and English launchers select it. The
profile is based on the pinned framework's defaults, adding only four secondary
PSP D-pad bindings:

| Physical input | PSP signal |
|---|---|
| Right stick up / down | D-pad up / down |
| Right stick left / right | D-pad left / right |
| Physical D-pad | Original D-pad directions |
| Left stick | Original analog nub |

Each right-stick direction activates beyond magnitude 12000 on the SDL signed
axis range. This approximately 37% threshold avoids small drift. This is digital
camera control, matching the game's PSP D-pad camera, rather than a new variable
camera-speed implementation. Since the game receives D-pad signals, the right
stick can also navigate in-game menus. The physical D-pad remains available in
both gameplay and menus. Host pause-menu navigation bindings are unchanged.
Face buttons, shoulder/trigger bindings, keyboard, left-stick calibration and
all other default settings are unchanged. Restart the preview to load the file.
The GDI/software fallback has keyboard input only and does not gain gamepad
support from this configuration.

No existing user profile was found at the standard Windows location. The
title-owned profile does not edit the system/global profile. Each preview's
private result records its selected profile path and hash. Saves are unaffected.

```powershell
./private/tools/python314/python.exe tools/check-controls.py
```

This compiles a synthetic test against the actual pinned native profile parser
and evaluator. It checks four axis directions, neutral/deadzone behavior,
physical D-pad buttons and host navigation, unchanged left analog, and equality
to the complete native default profile except for those four secondary bindings.
The first link attempt omitted Windows platform dependencies; the corrected
test links the real platform implementation and passes. No fake platform or PSP
handlers are used. Physical controller camera feel still needs user testing.
