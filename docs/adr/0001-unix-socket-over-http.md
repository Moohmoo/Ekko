# ADR 0001: UNIX Domain Socket Over HTTP for Local IPC

## Status
Accepted

## Context
Communication between the Electron desktop shell and the background Python daemon requires low latency and high security. Standard HTTP or WebSocket servers on `localhost` risk TCP port collisions and expose local endpoints to browser tabs.

## Decision
We communicate exclusively through a local UNIX domain socket at `/tmp/ekko.sock` using JSON-RPC 2.0 framing and NDJSON streaming. This removes the need for local network ports and isolates communication to the operating system session.

## Consequences
- Eliminates TCP port clashes, firewall warnings, and unauthorized local network access.
- Delivers sub-millisecond round-trip times and streaming token delivery without HTTP overhead.
- Requires Named Pipes fallback (`\\.\pipe\ekko`) on Windows platforms.
