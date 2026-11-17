# Native co-op: Steam development test and independent transport

Current guild-entry correction and separate 30/60 acceptance gates are tracked
in [MULTIPLAYER_ACCEPTANCE.md](MULTIPLAYER_ACCEPTANCE.md). Two actual local native
game pairs now establish matching and exchange game data at both configured
frame rates; shared missions and independent-internet gameplay remain open.
The historical single-account checks below do not cover these later results.

The user selected an optional **Spacewar / Steam App ID 480 development test**:
host a friends-only lobby, refresh compatible friend lobbies and join. Five-digit
codes are no longer required for this mode. Manual IP entry and router port
forwarding are not the intended player workflow. The earlier independent
room-code/WebRTC backend remains selectable.

The user-supplied Steamworks 1.65 SDK is imported privately and the original
standalone adapter builds. Actual Steam initialization, friends-only lobby
creation and leaving pass. F1 live provider selection persists in an isolated
test profile; F1 Host and Leave work in a real native game window. **These tests
have one actual account/member and zero confirmed peers.** Two-account friend
discovery/Join, Steam packet exchange and a shared game mission remain unverified.
The separate helper has no usable Steam overlay, so the invite dialog button is
disabled; use the friend-lobby browser. See [Steam setup and test instructions](STEAM_TEST.md).

This is **not ready for an internet co-op play test**. The room-code service and
native ICE/DTLS/SCTP transport are implemented and pass local direct and forced
TURN tests. There is no deployed public service or completed two-player game
mission. The user has no public server/domain and prefers P2P gameplay; managed
matchmaking was evaluated and the user authorized the Steam development backend.
No Epic Online Services integration or public room-service endpoint is configured.

The current player interface is **F1 → Networking**, a separate pause-menu button,
not a Settings tab. It has no IP-address fields. Create room and join by code are
disabled with an explicit message when no room service is configured. With an
explicit service configuration, Create issues a real HTTP request and shows a
code only after confirmation. Join accepts five digits with digit controls or
clipboard paste. Connected-peer count and Direct/Relayed state come from the
native connections. The old direct-IP dialog is not opened by the game; its CLI
remains for developer tests only. No locally invented code is presented as a
reachable room.

The normal launcher owns a hidden local Python connection helper with per-launch
authenticated loopback IPC. The selected backend loads either the separately
built Steam adapter or pinned native libdatachannel library;
game CPU execution is still the static native recompilation, with no PPSSPP
process. In independent room-service mode, while no room is active no public
service is contacted. Steam mode initializes the local Steam client and its
services only after selection. In room-service mode, creating or joining starts
HTTPS signalling; explicit multiplayer packets use native
encrypted WebRTC channels, never the HTTP signalling service. PSP datagrams use
unordered channels without retransmission; PTP streams use ordered reliable
channels with bounded receive windows and explicit accept acknowledgements.

Current local evidence (all using synthetic network payloads or copied saves):

- `private/online-check/result.json`: two independent native WebRTC processes,
  server-issued five-digit code, join/discovery, 8192-byte datagram, preserved
  short-buffer packet, reliable stream accept/partial reads/reply, host leave.
- `private/online-relay-check/result.json`: the same checks with forced relay
  policy through an owned loopback-only TURN fixture; both clients report Relayed.
- `private/coop-hle-online/result.json`: real HLE ABI, matching callbacks,
  receipt ACK and bidirectional PDP pass through the new native WebRTC backend
  against synthetic guest RAM. This is not MIPS/gameplay validation.
- `private/online-room-menu-check/result.json`: F1 creates a server-confirmed room
  in a real native game window; a separate native client joins and connects.
  Menu navigation and isolated graphics persistence pass; real preferences and
  the source save remain unchanged. Captures were inspected. No shared mission.
- 226 Python regressions pass. The Windows release rebuild and normal launcher
  preflight pass. The framework revision remains unchanged.

See [prepared server package, configuration and limits](ONLINE_SERVER.md).
The integrated libjuice backend currently supports TURN/UDP; all-UDP-blocked
networks remain unsupported. Direct P2P and a local relay test do not prove
connectivity across independent internet NATs.

The bounded native check `tools/check-game-settings.py --network --output
private/coop-menu-layout-check` passes: standalone Networking opens from F1, Back
returns to the menu, Settings still persists an isolated resolution change, and
the process closes cleanly. The original save fixture and real preferences remain
unchanged. The pause, networking and four-tab settings captures were inspected.
This verifies menu behavior, not internet room creation or co-op gameplay.

## Implemented and tested locally

The framework remains pinned at
`8704fba98007fff6d6f930365f2b2142af1bfbba`, with no checkout edits. Title-owned
`tools/coop-runtime.mk` links the new Windows networking code and the pinned
framework's lobby serializer/parser. It does not launch PPSSPP or change the
game binary, translation, textures, audio payloads, or real saves.

`tools/coop_transport.c` implements the framework's `NkAdhocTransport` interface
using a TCP lobby and direct peer UDP. Native PTP streams use real TCP sockets.
`tools/coop_lobby.py` hosts an explicit product-isolated discovery lobby; it
never relays gameplay packets or reads game files. Its default bind is loopback.
The normal launcher only starts a listener when an explicit Host profile is used.
There is no public-server lookup, automatic router configuration or telemetry.

`tools/coop_hle.c` supplies opt-in game-facing lobby, PDP, PTP lifecycle and
matching handlers. Callback work runs asynchronously on runtime service threads;
normal unsupported handlers remain active when the profile is off. Matching
data confirmation follows an actual received acknowledgement. Native matching
uses a private `LOAM` protocol; **PPSSPP/PSP matching interoperability is not
claimed**. The current discovery mapping uses actual group peers; radio WOL mode
is explicitly unsupported rather than returning a fabricated peer-found result.
Argument checking, event order, timing, timeout behavior and full PSP fidelity
still need broader oracle coverage.

The initial framework supplied only an in-process transport simulation and lone-console
HLE; the title's initial survey found unsupported PDP/PTP/matching APIs. Exact
local import results are recorded in `private/network-survey.json`, not inferred
from the presence of imports alone.

Earlier direct-backend local results (retained for regression):

- `private/coop-transport/result.json`: two independent native processes discover
  each other and exchange synthetic UDP data and TCP streams. Tests cover MAC/IP
  addressing, short receive-buffer retention, TCP connect/accept, partial reads,
  replies and socket cleanup. This is not a game session.
- `private/coop-hle/result.json`: two independent processes run the actual HLE
  functions against synthetic guest RAM and a test fiber driver. EABI marshalling,
  152-byte guest peer lists, asynchronous matching callbacks, join/accept,
  receipt-based data confirmation, bidirectional PDP and cleanup pass. The test
  driver is not the real PSP scheduler or a MIPS execution oracle.
- A matching retry attempt initially failed: Windows reported an ICMP port
  unreachable when the other player's matching socket had not opened yet. With
  `MSG_PEEK` the socket could keep returning that reset instead of receiving the
  join. The UDP sockets now disable propagation with the SDK's
  `SIO_UDP_CONNRESET`. The before-fix failure is preserved at
  `private/coop-hle/retry-failure.json`; the repaired native HLE test passes.
- `private/coop-menu/result.json`: the owned configuration dialog saves an
  isolated profile, with actual visible Save/Cancel controls and unchanged real
  graphics/network preferences. Its direct-IP fields are the temporary prototype,
  to be replaced by the room-code flow.
- `private/coop-game-01-a/result.json`: a copied-save native session boots, loads
  the user's chapter-2 character, reaches town/camp menus and exits cleanly. Source
  saves, fonts, normal preferences and the HD pack stay unchanged. **No actual
  multiplayer room or mission was reached**, so this is boot/configuration
  evidence only. The separately owned lobby was loopback-only and was shut down.

## What five-digit codes require

A code is an invitation lookup, not an address traversal mechanism. The public
service must allocate a unique active five-digit code (including leading zeroes),
expire stale rooms, rate-limit guesses, issue separate unguessable session/host
tokens, and exchange connection metadata between the invited peers. Codes must
come from the service only after successful room creation; failures must be
visible rather than displaying a disconnected "working" room.

The native transport then needs ICE/STUN to attempt direct connections across
routers. A TURN/relay fallback is needed for networks that block direct paths;
otherwise those players must receive an explicit connection failure. The menu
should show whether a connection is direct or relayed. Prefer P2P first; a relay
must not silently be presented as P2P. This follows the
[IETF ICE protocol](https://www.rfc-editor.org/info/rfc8445/) and
[TURN protocol](https://www.rfc-editor.org/rfc/rfc8656.html).

[libdatachannel](https://github.com/paullouisageneau/libdatachannel) and
[libjuice](https://github.com/paullouisageneau/libjuice) are candidates for the
native connection layer. Their official descriptions cover Windows and ICE;
libdatachannel additionally offers reliable data channels for the PTP stream
boundary. The current native dependency is libdatachannel v0.24.6 at
`6b1e2e620f1e37f0eafeee702eaea0043cb305fd`, using its pinned libjuice/usrsctp/plog
submodules and Mbed TLS 3.6.5 at `e185d7fd85499c8ce5ca2a54f5cf8fe7dbe3f8df`.
Rebuild with `tools/build-online-deps.py`; dependency source, libraries and build
outputs remain ignored. The DLL fingerprint and parent source revisions are
checked before loading. NAT traversal is not claimed from the direct Winsock tests.

The small public room service and relay infrastructure are not configured or
deployed. No hosting account, credentials, public connection tests or external
deployment was used. Before public deployment, prepare and review a concrete
server package and hosting configuration; game binaries/assets must never be
sent to that service. Only connection metadata and, if a relay is needed,
explicit multiplayer packets belong on the network.

## Next acceptance gates

### Guild hall failure investigated on 2026-11-15

- Input: the normal WIP-English Steam session in
  `private/preview-20261115-225204-6m0omq8q/`. The helper created a real lobby
  with one member; no remote peer handshake is recorded.
- Observation: after a matching-create call, the game eventually spins at
  `0x08c009cc`; its last matching-init result is `0x80410812` (already
  initialized). Presentation stops while the scheduler/audio continue.
- Inspection: the guest's matching setup requests a 32,768-byte pool and
  maxnum=5 in both parent and child modes. The title implementation previously
  rejected maxnum above four. Pinned PPSSPP `sceNetAdhocMatching.cpp` accepts
  2..16, citing PSP matching autotests. The create rejection is a concrete
  incompatibility; the later repeated-init error is not evidence of NAT failure.
- Change: accept the PSP matching range and size matching peer storage/member
  lists accordingly. Steam lobby capacity remains four. Initialization still
  rejects duplicate initialization; unsupported calls retain their errors.
  Successful context creation now logs its mode, capacity, port and receive size.
- Regression: the two-process native and online/WebRTC HLE tests pass with
  five-slot contexts. Both host/client modes test 1/2/5/16/17 boundaries, a full
  synthetic sixteen-member list, and the game's pool/port/interval arguments.
  Receipt ACK, data transfer and cleanup pass; five offline Steam contract tests
  also pass. Results are in `private/coop-hle/result.json` and
  `private/coop-hle-online/result.json`.
- Limit: this is local HLE evidence plus comparison to pinned PPSSPP source,
  not a new matching PPSSPP execution trace or successful guild hall/mission.
  Retest the rebuilt game on both PCs with confirmed Steam peers, initially at
  30 FPS. Capture the next failure's `native.log` and `online.log` locally.

The subsequent 30-FPS failure in
`private/preview-20261115-231024-2aemy0k1/` successfully creates the five-slot
context but fails after `sceNetAdhocMatchingStart`. The guest passes event
priority 16, event stack 7,168, input priority 8, **input stack 0**, and 768
option bytes. The previous native handler rejected that zero input stack;
pinned PPSSPP polls input on the host and creates only the event guest thread,
accepting this request. Our transport also polls input on the host. It now
allows the zero input-stack request while still creating the actual event
service thread and returning its real allocation/start failures. Positive
undersized stack requests and duplicate starts still fail.

Both native and WebRTC two-process HLE regressions now exercise those start
arguments, full option copying, matching callbacks/data and cleanup. All 236
Python regressions pass. The in-place release executable is SHA256
`6ee9f06e05f781ee2990737e36185642fa4a7127cef1afed8eb0ed3c7bdb3a88`;
launcher preflight passes. A real copied-save, original-graphics 30-FPS test in
`private/guild-hall-solo-01/run/` reaches matching start via the door left of
the save crystal and exits cleanly at its four-minute limit. Source saves,
fonts and normal preferences remain unchanged. Its final capture is still a
loading screen: this first route does not certify completed guild hall entry
or working room input. No second player or internet connection was involved.

The follow-up `private/guild-hall-solo-02/run/` reaches the actual Room Select
screen, accepts Down input and creates room 2 with the local chapter-2 character
and three empty slots. Circle opens the "Close the recruitment?" prompt. Captures
`003-enter.png`, `004-down.png`, `005-create.png` and `006-confirm.png` record
these states. The three-minute bounded test exits cleanly with source saves,
fonts and preferences unchanged. This verifies responsive solo room selection
and recruitment, not the subsequent guild interior, a second player joining,
Steam gameplay traffic, a shared mission or a matching PSP execution trace.
The native and WebRTC HLE tests additionally verify every one of the 768 option
bytes delivered to the discovery callback. Repeat the updated executable test
through the user's Steam lobby before accepting the Steam gameplay route.

1. Local native ICE/data-channel integration and direct/forced-relay tests pass.
   Broader timing/error equivalence still needs a PSP oracle.
2. Bounded room-code service and real Create/Join outcomes pass locally; select
   and configure the public matchmaking infrastructure before internet tests.
3. Create/copy-code/join-code UI is integrated. F1 Create and peer connection pass;
   complete UI Join/paste and four-player game-session validation remain open.
4. Reach the original game's room selector with two copied-save native instances;
   validate callbacks and traffic against matching PPSSPP traces.
5. Verify shared town/mission state, combat, disconnect/rejoin and post-co-op
   save/load. Start with original 30 FPS; 60-mode co-op has no acceptance evidence.
6. Test two independent internet connections, including a restrictive NAT and a
   relay fallback. A compiled executable or room code alone does not pass.

Reproduction (local development only):

```powershell
private/tools/python314/python.exe tools/survey-network.py
private/tools/python314/python.exe tools/check-coop-transport.py
private/tools/python314/python.exe tools/check-coop-hle.py
private/tools/python314/python.exe tools/check-network-menu.py
private/tools/python314/python.exe -m unittest discover -s tests
private/tools/python314/python.exe tools/title.py build --profile release --jobs 6
```

The direct-IP prototype can be configured with `tools/network-settings.py` and
an explicit private `--profile`. It requires matching game builds, unique console
identities and reachable peer ports, and currently assumes one console per
advertised IPv4 address. It is not a no-port-forwarding internet solution.

Audio investigation remains open as documented in [AUDIO_AND_UI.md](AUDIO_AND_UI.md).
The user explicitly authorized proceeding with networking while they test later.
