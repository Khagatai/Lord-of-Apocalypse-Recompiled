# Controllers and camera

Open `LordOfApocalypse.exe` to launch the game. The standard Vulkan renderer
uses SDL3 gamepads, including Xbox, DualSense (PS5) and DualShock 4 controllers.
The launcher Controls page shows PlayStation and Xbox button names and opens
a binding editor. F1 or Escape opens the in-game host menu; settings save
automatically. See [graphics](GRAPHICS.md) for display options.

## Connect a DualSense

For USB, connect the controller with a USB cable that supports data. For
Bluetooth, disconnect USB and turn the controller off, then hold Create and
PS until the light bar flashes. In Windows Bluetooth settings, add the
controller. See [Sony's connection guide](https://www.playstation.com/en-us/support/hardware/pair-dualsense-controller-bluetooth/).

Connect or pair before starting your first test. SDL also handles connection
and removal while the game runs. Controller removal can open the pause menu;
resume after reconnecting. The runtime selects the first available gamepad,
so disconnect other gamepads when checking which controller is active.

Direct SDL input does not require a controller remapper. If Steam Input or a
remapper exposes a virtual Xbox controller, its layout is also supported. Use
one input path when testing to avoid duplicate devices; this does not require
closing Steam used for multiplayer.

## Default mapping

| DualSense input | Game input |
|---|---|
| Cross / Circle / Square / Triangle | PSP Cross / Circle / Square / Triangle |
| Left stick | PSP analog movement |
| Right stick | Camera through PSP D-pad directions |
| D-pad | Original D-pad, including menus |
| L1 or L2 | PSP L |
| R1 or R2 | PSP R |
| Options | PSP Start |
| Create (Share on PS4) | PSP Select |
| PS button | Host pause menu, if not intercepted by another application |

Both language variants start from `config/controller-camera.json` and use a
personal profile through the pinned framework's `NK_INPUT_PROFILE` loader.
Right-stick directions activate beyond
magnitude 12000, approximately 37% of the SDL signed axis range, to avoid drift.
This sends digital camera directions as on PSP. The right stick can therefore
also navigate game menus; the physical D-pad remains available throughout.
The GDI/software fallback has keyboard input only.

## Change controller bindings

Use **Launcher Settings > Controls > Edit controller bindings**, or **F1 >
Controls**. Each PSP button has primary and secondary input slots. Assigning an
input already used by another PSP control releases its previous slot. Left-stick
movement and the host-menu bindings remain available. Restore defaults resets
the bindings and camera options. Preferences are stored in
`private/settings/controller.json`; the generated input profile is beside it.
Launcher edits apply on the next launch. F1 edits apply after the supervisor
acknowledges the save and reloads the real native input profile.

## Optional smooth camera

**F1 > Controls > Camera rotation settings** and the launcher binding editor
offer **Smooth 360 camera (experimental)** and five rotation speeds from beta.8.
The right stick controls continuous horizontal rotation and vertical tilt before
the original orbit and collision calculations. Velocity eases in and out; the
elapsed PSP display time controls rotation at both frame-rate settings. Releasing
the stick holds the chosen tilt. Vertical pitch stops at 80 degrees either side
of level to prevent flipping over; horizontal rotation wraps freely. Original
PSP mode remains the default and retains the original stepped camera.

Smooth rotation applies only to the free camera. While locked on, the right
stick sends the original PSP direction inputs for enemy and weak-point switching,
using the game's own selection rules and selected Hold/Toggle lock-on mode.
Unlocking clears the smooth camera's previous tilt and velocity before free
rotation resumes. Physical D-pad bindings and keyboard controls remain available.

The saved input profile retains the selected bindings in both camera modes. A
title-owned runtime wrapper filters only right-stick axis bindings to PSP D-pad
directions while the measured active player camera has no lock-on target. This
prevents simultaneous PSP camera steps during smooth rotation. Inactive,
scripted and locked cameras keep the original direction inputs. Custom right-stick
bindings to other PSP actions and host-menu navigation stay unchanged. Use the
physical D-pad for game menus.

This is an experimental camera enhancement. Physical controller,
camera collision, target lock, scripted scene and campaign acceptance must be
reported separately from mathematical timing checks and bounded native tests.
The beta.8 native virtual-controller routes at 30 and 60 FPS each cover more than
one horizontal revolution, both vertical limits, partial deflection and neutral
hold. Their direction follows the original interpreter-observed D-pad movement.
The 60 FPS repeat disables host pacing; it verifies motion, not FPS performance.
The real native profile evaluator checks free-camera filtering, locked-camera
direction inputs, simultaneous physical D-pad input and custom action bindings.
A production-helper test with an SDL virtual gamepad checks that lock-on performs
no camera/pose writes and unlocking at neutral does not restore stale smooth
motion, at both 30 and 60 FPS. These tests do not establish physical-controller
or multiplayer campaign acceptance.

The launcher sets SDL's general, PS4 and PS5 HIDAPI driver defaults before the
game process starts. Explicit environment overrides remain respected. The
selected hints are included in the private launch result for troubleshooting.
The camera and F1 binding editor require a native game rebuild when upgrading
from earlier builds. HD recipes and upscaler models are unchanged; keep `private` to reuse
existing textures.

## Validation

```powershell
./private/tools/python314/python.exe -m unittest discover -s tests -p test_playstation_support.py -v
./private/tools/python314/python.exe tools/check-controls.py
```

The first test compiles against the bundled SDL3 and actual pinned native input
profile evaluator. Virtual DualSense, DualShock 4 and Xbox devices exercise face
buttons, shoulder buttons, triggers, Start/Select, physical D-pad, both sticks,
button labels and disconnect/reconnect. The second checks the camera profile
against the framework defaults. Neither test substitutes PSP handlers.

Physical DualSense USB and Bluetooth acceptance remains pending: test movement,
camera, menu navigation, Options/Create and reconnect with each connection.
Virtual devices verify SDL normalization and game mapping, not the physical
USB/Bluetooth driver transport or controller firmware.
