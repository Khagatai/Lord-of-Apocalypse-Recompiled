# Optional Spacewar Steam test

This is an explicitly selected **development test using App ID 480**. It is not a
production Steam release or a proven shared mission. Spacewar is Valve's sample
application identity; Steam provides lobbies and networking, not a dedicated
Spacewar server process. No game image, generated guest code, artwork or saves
are uploaded. The default independent room-service backend remains available.

## What is installed

The user supplied `steamworks_sdk_165.zip`. `tools/import-steam-sdk.py` validates
archive paths, preserves the original ZIP, and imports SDK files into ignored
`private/tools/steamworks-sdk/`. `intake.json` records the archive and file hashes.
The official SDK is not staged in Git. No account agreement was accepted by the
assistant, and no SDK substitute or ownership-check bypass is used.

Original MIT-licensed `tools/steam_bridge.cpp` and `tools/steam_flat.h` compile
against the supplied headers into a separate DLL loaded only by the owned
connection helper. The native recomp executable communicates with that helper
through its existing authenticated loopback IPC. The game CPU still runs native
recompiled code; neither PPSSPP nor EOS is used by this backend.

The first real test loaded Steam but crashed on a C++ interface call while reading
the account ID. The adapter was corrected to use Valve's flat C ABI and manual
callback dispatch instead of crossing MSVC/MinGW C++ vtables. The corrected
adapter builds without warnings and real Steam initialization/lobby tests pass.
The local bridge manifest fingerprints both original adapter sources, its DLL,
the official `steam_api64.dll`, and the SDK headers used to build it.

## Host and join test

On **both PCs**, use the matching current title build and independently supplied
game data. Sign in to separate Steam accounts and add each other as Steam friends.
Use original 30 FPS for the initial co-op test. Experimental 60 FPS is selectable
with networking enabled, but synchronized 60-FPS co-op is not yet validated.
Change FPS and restart before creating a lobby if needed.

1. Open **LordOfApocalypse.exe**, then **F1 → Networking**.
2. Select **Steam (Spacewar test)**. Provider selection is saved in
   `private/settings/online-service.json`; there is no new command launcher.
3. Host chooses **Host Steam lobby**. A successful callback is required before
   the menu reports an open lobby.
4. Friend chooses **Refresh friends' lobbies**, then **Join [host name]**.
   Only compatible friend-owned Lord of Apocalypse test lobbies are displayed.
5. Wait for **Players: 2 / 4** and **Confirmed peer connections: 1** on each PC.
   Membership alone is not a connected peer: real Steam session state plus
   protocol hello/ack messages are required. No code or IP address is exchanged.
6. Both return to the game and use its **Room Select** multiplayer flow. A shared
   room, mission, disconnect behavior and save/load still need validation.

Steam may show **Spacewar** as running. The Steam overlay is currently unavailable
in the separate connection helper, so its invite-dialog button is disabled when
Steam reports no overlay. Use the friend-lobby browser. Accepting an invitation
callback is implemented but has not been verified with two accounts. No friend
invitation was sent automatically during testing.

Lobbies are friends-only, limited to four players, and tagged with this project's
protocol identifier to exclude unrelated App ID 480 projects. Incoming sessions
are accepted only from current compatible-lobby members. Namespace, member MAC,
packet magic, channel type and handshake are checked. SDK errors remain errors.
Host migration is not implemented: if Steam changes the lobby owner, this test
backend leaves the room and reports that the host left.

## Actual validation

- The user reports a successful two-player room/lobby join at 30 FPS. The normal
  session `private/preview-20261115-232531-21jai9d3/online.log` also records an
  actual protocol hello/ack-confirmed Steam peer. This advances connection
  evidence beyond the earlier single-account tests; it does not establish a
  shared guild interior, mission, combat synchronization or save round trip.
- At the user's request, the existing saved local graphics profile now selects
  60 FPS; other graphics preferences remain unchanged. The normal cached launch
  preflight passes (`private/coop60-preflight.json`) using the existing corrected
  matching executable. This is configuration/preflight evidence, not a new
  remote 60-FPS test. Movies retain their existing media-context protection.

For the two-player 60-FPS trial, both players select **F1 → Settings → Graphics
→ Gameplay frame rate → Upgraded 60 FPS**, then apply/restart before recreating
the Steam lobby. Use the same current build and 60-FPS setting on both PCs;
mixed-rate play is unverified. First check both peers connect and the same
in-game room is visible, then compare movement, attack/animation speed, enemy
state and quest completion during a short shared mission. Verify rewards and
saves after restarting. Revert both players to 30 if synchronization differs.
Do not infer synchronized gameplay from the lobby player count or host FPS.

- `private/steam-connection-check/result.json`: real Steam account initialized;
  real friends-only App ID 480 lobby created, one member, zero connected peers;
  lobby left cleanly. No two-player claim.
- `private/steam-menu-check/result.json`: actual lobby creation and Leave through
  F1 pass in an owned native game window. Original save fixture and normal
  graphics preferences remain unchanged. The inspected capture shows one member
  and zero confirmed peers; overlay availability is false.
- `private/steam-switch-check/result.json`: the normal user path from Room service
  to Steam is exercised through F1. The provider is saved to an isolated profile,
  actual lobby Host/Leave pass, and Settings still persists its isolated graphics
  choice. Normal preferences and the source save remain unchanged.
- Offline adapter-contract tests cover handshake gating, foreign packet/identity
  rejection, explicit missing-SDK failures and saved provider configuration. They
  do not stand in for a real Steam connection test.
- Existing independent WebRTC transport and HLE matching/callback tests still pass.

Reproduction from the source project:

```powershell
private/tools/python314/python.exe tools/import-steam-sdk.py ../steamworks_sdk_165.zip
private/tools/python314/python.exe tools/build-steam-bridge.py
private/tools/python314/python.exe tools/check-steam.py --host
private/tools/python314/python.exe tools/title.py build --profile release --jobs 6
private/tools/python314/python.exe tools/check-game-settings.py --output private/steam-menu-check --steam
```

The UI check requires a fresh private output folder and uses copied saves. Normal
sessions keep helper diagnostics in `private/preview-*/online.log` and game HLE
diagnostics in `native.log`. Session tokens and SDK files stay private. Do not
upload those logs to external services automatically.

Next gates are a second account on another PC, friend discovery and Join,
actual reliable/unreliable Steam packet exchange, then a real game room/mission
and PPSSPP comparison. Internet connectivity, selected relay/direct path and
full gameplay compatibility are not accepted from the single-account lobby test.

Valve documents App ID 480 as its sample identity. It is a development route,
not an entitlement to a permanent public release under that identity:
[Spacewar example](https://partner.steamgames.com/doc/sdk/api/example),
[Steamworks SDK agreement](https://partner.steamgames.com/documentation/sdk_access_agreement/).
