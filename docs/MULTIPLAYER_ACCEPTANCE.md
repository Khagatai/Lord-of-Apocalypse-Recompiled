# Multiplayer validation matrix

The guild-hall starvation correction is installed in the source project. The source
project's normal Start-Game.cmd uses the rebuilt networking runtime; tester
installation folders are not modified automatically. A separate local candidate
update is available for the other PC. Saves, language images and preferences
remain separate from that update.

## Guild-entry regression

The host's `private/preview-20261116-184737-lc1_vxb9/` log confirms a Steam peer,
matching client creation (mode 2, maximum 5, port 1, 4096-byte RX buffer), and
matching start at callback priority 16. Frames then stop while render-thread
wakeups accumulate. This is consistent with host polling starving game threads.

Two attempted partial remedies (refreshing the clock before 2 ms delays and
forcing a single handoff) passed a narrow synthetic wait test but still failed
native delayed-IPC checks. Those intermediate executables are not the candidate.
The final change separates I/O polling from callbacks. Shared host input runs at
priority 119; adhocctl and matching callback workers retain the requested guest
priorities and park until real events are queued. No unsupported PSP call is
changed to fake success. The framework stays at
`8704fba98007fff6d6f930365f2b2142af1bfbba`.

Candidate executable SHA256:
`259a0b3eb2717a659d651756f89cf5050b8e76e1a9710d1148c717ae4ff51670`.
The guest image remains
`b0d370ebcfb33df3517a40c97c1b5c0ef0f6d7ed71a1efc6a4fce7e73c46dfb0`.

## Results and limits

| Gate | 30 FPS | 60 FPS | Evidence / limit |
|---|---|---|---|
| Source tests and native callback ABI/packet checks | Pass | Common host code | 266 source tests; real two-process direct and WebRTC HLE tests |
| Guild entry / room creation with connected transport peer and artificial 5 ms IPC delay | Pass | Pass | Both native runs exit 0, keep presenting, join the peer and reach matching parent mode; peer is a synthetic transport participant |
| Two actual native games join a room and exchange game payloads | Pass | Pass | Both pairs receive established callbacks and exchange hundreds of 768-byte matching messages with real receipt ACKs; all four processes exit 0 |
| Two-PC Steam guild creation/join | User reports success; mode unrecorded | User reports success; mode unrecorded | 2026-11-16: user connected with another player and completed one mission |
| Shared guild/quest transition | User reports mission reached; mode unrecorded | User reports mission reached; mode unrecorded | The separate automated close-recruitment route returned the host to town; it does not establish shared 3D hall entry |
| Shared quest completion | User reports one mission completed; mode unrecorded | User reports one mission completed; mode unrecorded | Further playtesting continues; this is not independent acceptance at both frame rates |
| Movement, combat and enemy synchronization details | Pending | Pending | No detailed observations supplied for the completed mission |
| Rewards and independent save–exit–reload | Pending | Pending | Never run this acceptance on the only copy of progress |
| Disconnect/rejoin and opening F1 during a mission | Pending | Pending | Local host pause can affect game-facing network timing |
| Mixed 30/60 participants | Pending | Pending | No cross-mode synchronization claim |

The delayed-IPC run is a starvation stress test, not a performance pass: its
late 30-mode samples are about 23–26 FPS and 60-mode samples about 31–34 FPS.
Four simultaneous native game processes in the first real-pair check also fall
below their configured targets. Do not infer steady 30/60 gameplay performance
from those checks. Each frame rate needs a separate normal two-PC mission test.

Evidence stays private:
`guild-peer-wait-check/`, `guild-peer-wait-check-02/` (rejected attempts),
`guild-peer-wait-check-03/` (candidate stress check), and
`two-native-guild-check/` (real native-pair matching).

## Manual two-PC route

1. Close both games and install the same candidate runtime. Start normally.
2. Select 30 FPS on both PCs and restart before hosting/joining the Steam lobby.
3. Confirm one connected peer on each PC, then close both F1 menus.
4. Enter the guild hall, create/join the same game room and close recruitment.
5. Start a shared quest; verify both players see movement, attacks, enemies,
   damage, completion and rewards consistently. Note any stalls or audio breakup.
6. Save independently, exit and confirm the earned progress reloads on each PC.
7. Repeat at 60 FPS on both PCs after restart. Record disconnect/rejoin separately.

Keep each run's native.log, online.log and result.json locally if a gate fails.
Do not share online-ready.json, which contains a private local session token.
Full multiplayer acceptance remains open until the shared mission gates pass.

The user's successful mission is recorded as manual evidence, separately from
local automation. The frame-rate combination, rewards persistence, reconnect
behaviour and longer-session stability have not yet been reported.
