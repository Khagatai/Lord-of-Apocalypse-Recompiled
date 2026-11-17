# Room service deployment package

This is a **prepared server component**, not an already hosted online service.
The Windows client now has working local room-code and native WebRTC transport
tests. No internet game mission has passed. A public HTTPS endpoint plus an
authenticated TURN/UDP relay must be configured before inviting internet players.
No game image, asset, generated game code, save or capture belongs on this server.

Build the small source-only archive with:

```powershell
private/tools/python314/python.exe tools/package-online-service.py
```

The archive contains only `room_service.py`, this guide and an example
configuration. It does not include the game's `private/` directory or any client
files. The archive manifest lists SHA-256 fingerprints of its exact contents.

## Server configuration

Use a server with a public address and a domain with HTTPS. The current process
needs Python 3.11 or newer and has no third-party Python dependencies. For example,
put the extracted `room_service.py` in `/opt/loa-rooms/`, run it as a dedicated
unprivileged service account, and bind the HTTP listener to loopback:

```sh
python3 /opt/loa-rooms/room_service.py --listen 127.0.0.1 --port 8741
```

Have the HTTPS reverse proxy forward `/v1/*` to `127.0.0.1:8741`. Use a valid
certificate, a 64 KiB maximum request body, a connection limit, and a request
timeout of 10 seconds. Do not expose 8741 directly. Disable request-body and
Authorization-header logging. The service's own access logging is disabled.
Do not trust a client-supplied forwarded IP: unless you configure a trusted proxy
boundary separately, the service's built-in admission limiter sees the proxy IP.
The proxy must limit create/join guesses by real client IP as well. Room codes
have only 100,000 possibilities; invitation guesses are limited, but a five-digit
code is not a strong password or an account identity.

Set the service environment:

```text
LOA_STUN_URL=stun:YOUR_RELAY_DOMAIN:3478
LOA_TURN_URL=turn:YOUR_RELAY_DOMAIN:3478
LOA_TURN_SECRET=YOUR_RANDOM_OPERATOR_SECRET
```

Configure your authenticated TURN implementation (for example coturn) with the
same secret using its REST/shared-secret authentication mode. The service issues
hour-long HMAC credentials; the operator secret is never returned to a client.
Bind the relay to its public interface, set its external address correctly, use
per-user and total allocation quotas, and permit only its configured UDP relay
port range in the server firewall. Deny relay access to the server's loopback,
private, multicast and other internal networks. An unauthenticated open relay is
not an acceptable substitute. Consult the TURN implementation's current official
configuration documentation when setting these values.

The integrated libjuice backend currently uses TURN over UDP. Networks that block
all UDP still need another transport implementation; TURN/TCP/TLS has **not** been
integrated or tested. Connection failure must be shown in that case. Direct P2P
is preferred; the game shows when a selected connection uses a relay.

Rooms expire after 60 seconds without client heartbeats, or after six hours.
Host departure closes the room; host migration is not implemented. In-memory
rooms are lost when the service restarts. The service supports at most 1,000
active rooms, four players per room and 32 simultaneous HTTP requests. Deploy one
instance for this initial version: horizontal scaling needs shared room state.

## Client configuration

Create `private/settings/online-service.json` on each client:

```json
{"url":"https://YOUR_ROOM_SERVICE_DOMAIN"}
```

Only an HTTPS origin is accepted for a public service. Plain HTTP is accepted
only on loopback for owned tests. Requests do not follow redirects. This setup is
an operator/developer step; players use **F1 → Networking → Create room** or
**Join room** and never enter an IP address or forward router ports. The five-digit
code is shown only after the server confirms creation. Codes are session-only
and are not saved as permanent user preferences.

Start using `Start-Game.cmd`. The launcher owns a hidden local connection helper
and shuts it down when the game exits. Its loopback IPC requires a random token
unique to that launch. Only the helper loads the pinned native WebRTC library;
no PPSSPP process is used. The helper never reads game files or real saves.

## Required acceptance before public play

The synthetic two-process direct and forced local relay tests are reproducible:

```powershell
private/tools/python314/python.exe tools/build-online-deps.py
private/tools/python314/python.exe tools/check-online.py
private/tools/python314/python.exe tools/check-online.py --local-relay
private/tools/python314/python.exe tools/check-coop-hle.py --online
```

These tests use no public STUN/TURN service or game payloads. The local relay is
an owned, loopback-only test fixture and is not a production server. Next verify
two native game instances in Room Select, matching PPSSPP traces, a shared
mission, disconnect behavior, and save/load. Then repeat across two independent
internet connections and verify the selected direct/relay paths. Use original
30 FPS first; co-op at experimental 60 FPS remains unverified.
